#!/usr/bin/env python
# scrtdd_common.py -- shared helpers for the scrtdd (SeisComP module) runs of the Gwangyang benchmark.
#
# Imported by scrtdd_multievent.py and scrtdd_singleevent.py (same folder). It must run with the Python of
# conda env 'seiscomp' after 'source install/env_seiscomp.sh', because it uses SeisComP's own configuration
# reader (seiscomp.config) to report what scrtdd reads.
#
# What is here, and why:
#   1. Paths of the shared inputs (catalog CSVs, inventory, SDS archive, NonLinLoc grids).
#   2. The "shared settings" blocks of the benchmark (clustering 'hypodd_like', solver 'hypodd_like' and
#      'rtdd_default', cross-correlation 'like_reference' and 'xcorr_default'), written as scrtdd profile
#      keys, so that pyrtdd and scrtdd runs use the same numbers.
#   3. PROFILE_OPTIONS: every option the scrtdd v2.0.10 module reads for a profile, with the value it falls
#      back to when the option is not set and the line of apps/scrtdd/rtddtool.cpp where that happens.
#      resolve_options() uses it to dump EVERY value the module actually uses (set or default), and to
#      translate it into the libhdd structures (Config, ClusteringOptions, XcorrOptions, SolverOptions)
#      that pyrtdd exposes under the same names.
#   4. write_config() writes a private SEISCOMP_LOCAL_CONFIG folder (global.cfg + scrtdd.cfg) per run.
#   5. run_scrtdd() runs one scrtdd command with SEISCOMP_LOCAL_CONFIG and HOME inside the run folder,
#      niced, with /usr/bin/timeout (SeisComP ships its own bin/timeout, so the full path is used).

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time

# ----------------------------------------------------------------------------- paths
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
CAT = f"{DATA}/inputs/rtdd_catalog"
STATION_CSV = f"{CAT}/station.csv"
EVENT_CENTROID_CSV = f"{CAT}/event_centroid_start.csv"   # HypoDD ISTART=1 start (all events at the centroid)
EVENT_HYPOINV_CSV = f"{CAT}/event.csv"                   # HYPOINVERSE kim1983 start (sensitivity runs)
PHASE_CSV = f"{CAT}/phase.csv"                           # the 763 picks ph2dt used
INVENTORY_XML = f"{DATA}/inputs/inventory_sc.xml"       # SeisComP inventory made by step Prep (coordinates = station.csv)
SDS_DIR = f"{DATA}/inputs/sds"
NLL_TABLEPATH = f"{DATA}/inputs/nll_kim1983/time/kim1983"  # folder + model name, as the tttnll plugin wants it
RUNROOT = f"{PROJECT}/runs/gwangyang/scrtdd"
LOGDIR = f"{PROJECT}/logs"
PROFILE = "gwangyang"
SCRTDD_SRC = f"{PROJECT}/software/src/seiscomp/src/extras/scrtdd"

NICE = 10              # Server A is shared (project rule 3)
TIMEOUT_S = 570        # one scrtdd call must finish inside one tool call

# ----------------------------------------------------------------------------- shared settings
# Global configuration (global.cfg of the run). tttnll is scrtdd's plugin that exposes NonLinLoc grids to
# SeisComP under the travel-time interface name "NLLGrid". maxSearchDistance is in metres; 0.1 m is the
# pyrtdd default (libs/hdd/ttt/nllgrid.h:47) and every one of the 108 station/phase lookups succeeds with it
# (step Prep), so both programs use the same tolerance (the plugin's own default would be 10 m).
GLOBAL_CFG = {
    "plugins": "tttnll",
    "ttt.NLLGrid.tables": "kim1983",
    "ttt.NLLGrid.kim1983.tablePath": NLL_TABLEPATH,
    "ttt.NLLGrid.kim1983.maxSearchDistance": "0.1",
    "recordstream": f"sdsarchive://{SDS_DIR}",
}

# Profile keys common to every run (written as profile.gwangyang.<key>).
COMMON = {
    # region is used only in real time to pick a profile for an incoming origin; --profile overrides it.
    "regionType": "CIRCULAR",
    "region": "35.0000, 127.7286, 30",
    "methodID": "RTDD",
    "tableType": "NLLGrid",
    "tableModel": "kim1983",
    "PSTableOnly": "true",
    # the catalog uses plain P and S (shared setting validPphases ['P'], validSphases ['S'])
    "P-Phases": "P",
    "S-Phases": "S",
    "pickUncertaintyClasses": "0.000, 0.025, 0.050, 0.100, 0.200, 0.400",   # rtDD default; unused (usePickUncertainties false)
}

# Clustering 'hypodd_like' mirrors ph2dt: nearest neighbour (numEllipsoids 0) within 10 km (MAXSEP), no
# neighbour limit (MAXNGH 200 > 10), one shared phase is enough (MINLNK 1, MINOBS 1), no station-distance
# cut (MAXDIST 200 km > all stations). minStationToEventPairDistRatio stays at the rtDD default 3.
# minNumPhases and minNumNeighbours are ONE setting each in scrtdd, used for both multi- and single-event
# clustering (rtddtool.cpp:566-589). The single-event block is used only by the --ep runs.
CLUSTERING_HYPODD_LIKE = {
    "doubleDifferenceSystem.eventFiltering.minNumPhases": "1",
    "doubleDifferenceSystem.eventFiltering.minNumNeighbours": "1",
    "doubleDifferenceSystem.phaseFiltering.minStationToEventPairDistRatio": "3",
    "doubleDifferenceSystem.phaseFiltering.minStationDistance": "0",
    "doubleDifferenceSystem.phaseFiltering.maxStationDistance": "-1",
    "doubleDifferenceSystem.eventPairSelection.multiEvent.maxNumNeighbours": "0",
    "doubleDifferenceSystem.eventPairSelection.multiEvent.maxNeighbourDistance": "10",
    "doubleDifferenceSystem.eventPairSelection.multiEvent.numEllipsoids": "0",
    "doubleDifferenceSystem.eventPairSelection.singleEvent.maxNumNeighbours": "0",
    "doubleDifferenceSystem.eventPairSelection.singleEvent.maxNeighbourDistance": "10",
    "doubleDifferenceSystem.eventPairSelection.singleEvent.numEllipsoids": "5",
}

# Solver 'hypodd_like': pure double difference (no absolute travel-time equations), rtDD's default damping,
# residual down-weighting, iterations and cross-correlation weight.
SOLVER_HYPODD_LIKE = {
    "solver.solverType": "LSMR",
    "solver.algoIterations": "20",
    "solver.downWeightingByResidual": "10, 5",
    "solver.dampingFactor": "0.01",
    "solver.absoluteLocationConstraint": "0",
    "solver.xcorrWeightScaler": "2.0",
    "solver.usePickUncertainties": "false",
}
# Solver 'rtdd_default': the full rtDD default (absolute-location constraint 0.3).
SOLVER_RTDD_DEFAULT = dict(SOLVER_HYPODD_LIKE, **{"solver.absoluteLocationConstraint": "0.3"})

# Waveform processing shared by both cross-correlation blocks: 1000 Hz resampling (libhdd's own windowed-sinc
# resampler, the same code in pyrtdd) and a 4-pole (8 poles in total, like ObsPy corners=4) causal
# Butterworth band-pass 5-20 Hz. SeisComP filter strings have no zero-phase option, and the pyrtdd ObsPy
# proxy cannot pass zerophase=True either, so both programs filter one way only (the reference filtered
# forward and backward). The value must be quoted: a bare comma would turn it into a list.
WF_FILTER = {
    "crossCorrelation.waveformFiltering.filterString": '"BW(4,5,20)"',
    "crossCorrelation.waveformFiltering.margin": "1",
    "crossCorrelation.waveformFiltering.resampling": "1000",
}
# Cross-correlation 'like_reference': windows -0.5..+0.5 s around the pick, fixed length (winScaling 0),
# lag search +-0.5 s, CC >= 0.7, P on Z, S on L2 (orientation-free; the reference used the better of N/E).
# No station-distance or inter-event-distance limit (the reference correlated all stations and all pairs);
# -1 is also what libhdd/pyrtdd XcorrOptions use by default, while scrtdd's own profile defaults are 60/2 km.
XCORR_LIKE_REFERENCE = dict({
    "crossCorrelation.enable": "true",
    "crossCorrelation.minStationDistance": "0",
    "crossCorrelation.maxStationDistance": "-1",
    "crossCorrelation.maxInterEventDistance": "-1",
    "crossCorrelation.p-phase.minCCCoef": "0.7",
    "crossCorrelation.p-phase.winStart": "-0.5",
    "crossCorrelation.p-phase.winEnd": "0.5",
    "crossCorrelation.p-phase.winScaling": "0",
    "crossCorrelation.p-phase.maxDelay": "0.5",
    "crossCorrelation.p-phase.components": "Z",
    "crossCorrelation.s-phase.minCCCoef": "0.7",
    "crossCorrelation.s-phase.winStart": "-0.5",
    "crossCorrelation.s-phase.winEnd": "0.5",
    "crossCorrelation.s-phase.winScaling": "0",
    "crossCorrelation.s-phase.maxDelay": "0.5",
    "crossCorrelation.s-phase.components": "L2",
}, **WF_FILTER)
# Cross-correlation 'xcorr_default': libhdd's XcorrOptions defaults (libs/hdd/dd.h:93-110, = pyrtdd
# XcorrOptions()) with the same filter and resampling.
XCORR_DEFAULT = dict({
    "crossCorrelation.enable": "true",
    "crossCorrelation.minStationDistance": "0",
    "crossCorrelation.maxStationDistance": "-1",
    "crossCorrelation.maxInterEventDistance": "-1",
    "crossCorrelation.p-phase.minCCCoef": "0.7",
    "crossCorrelation.p-phase.winStart": "-0.5",
    "crossCorrelation.p-phase.winEnd": "0.5",
    "crossCorrelation.p-phase.winScaling": "0.02",
    "crossCorrelation.p-phase.maxDelay": "0.5",
    "crossCorrelation.p-phase.components": "Z",
    "crossCorrelation.s-phase.minCCCoef": "0.7",
    "crossCorrelation.s-phase.winStart": "-0.5",
    "crossCorrelation.s-phase.winEnd": "1.0",
    "crossCorrelation.s-phase.winScaling": "0.04",
    "crossCorrelation.s-phase.maxDelay": "0.5",
    "crossCorrelation.s-phase.components": "L2",
}, **WF_FILTER)
XCORR_OFF = {"crossCorrelation.enable": "false"}

# Module (not profile) settings. The waveform disk cache is scrtdd's default behaviour; it is kept on but
# moved into the run folder so that runs never share cached traces (default would be $SEISCOMP_ROOT/var/lib/rtdd).
def module_cfg(run_dir):
    return {
        "performance.cacheWaveforms": "true",
        "performance.cacheDirectory": f"{run_dir}/wfcache",
        "performance.cachedWaveformLength": "10",
    }

# ----------------------------------------------------------------------------- what scrtdd reads
# (key under profile.<name>., type, value used when the key is not set, rtddtool.cpp line of that fallback)
# Types: str, bool, int, double, strings (list), doubles (list), path.
PROFILE_OPTIONS = [
    ("regionType", "str", "CIRCULAR", "425-433 (anything but RECTANGULAR -> CIRCULAR)"),
    ("region", "doubles", [], "160-176 (empty -> no region limit)"),
    ("methodID", "str", "RTDD", "452-457"),
    ("tableType", "str", "LOCSAT", "461-466"),
    ("tableModel", "str", "iasp91", "470-475"),
    ("PSTableOnly", "bool", True, "479-484"),
    ("P-Phases", "strings", ["P", "Pg", "Pn"], "488-493"),
    ("S-Phases", "strings", ["S", "Sg", "Sn"], "497-502"),
    ("automaticOriginP", "str", "", "505-508"),
    ("automaticOriginS", "str", "", "512-515"),
    ("pickUncertaintyClasses", "doubles", [0.0, 0.025, 0.05, 0.1, 0.2, 0.4], "519-538"),
    ("catalog.stationFile", "path", None, "545-560"),
    ("catalog.phaFile", "path", None, "545-560"),
    ("catalog.eventFile", "path", None, "545-560"),
    ("doubleDifferenceSystem.eventFiltering.minNumPhases", "int", 8, "566-577 (single AND multi)"),
    ("doubleDifferenceSystem.eventFiltering.minNumNeighbours", "int", 4, "579-589 (single AND multi)"),
    ("doubleDifferenceSystem.phaseFiltering.minStationDistance", "double", 0.0, "595-605"),
    ("doubleDifferenceSystem.phaseFiltering.maxStationDistance", "double", 0.0, "608-618 (<=0 disables)"),
    ("doubleDifferenceSystem.phaseFiltering.minStationToEventPairDistRatio", "double", 3.0, "621-631"),
    ("doubleDifferenceSystem.eventPairSelection.singleEvent.maxNumNeighbours", "int", 80, "637-645"),
    ("doubleDifferenceSystem.eventPairSelection.singleEvent.numEllipsoids", "int", 5, "647-655"),
    ("doubleDifferenceSystem.eventPairSelection.singleEvent.maxNeighbourDistance", "double", 5.0, "657-665"),
    ("doubleDifferenceSystem.eventPairSelection.multiEvent.maxNumNeighbours", "int", 40, "669-677"),
    ("doubleDifferenceSystem.eventPairSelection.multiEvent.numEllipsoids", "int", 0, "679-687"),
    ("doubleDifferenceSystem.eventPairSelection.multiEvent.maxNeighbourDistance", "double", 5.0, "689-697"),
    ("crossCorrelation.enable", "bool", False, "701-708"),
    ("crossCorrelation.minStationDistance", "double", 0.0, "710-718"),
    ("crossCorrelation.maxStationDistance", "double", 60.0, "720-728 (<0 disables)"),
    ("crossCorrelation.maxInterEventDistance", "double", 2.0, "730-738 (<0 disables)"),
    ("crossCorrelation.p-phase.winStart", "double", -0.5, "741-749"),
    ("crossCorrelation.p-phase.winEnd", "double", 0.5, "751-759"),
    ("crossCorrelation.p-phase.winScaling", "double", 0.02, "761-769"),
    ("crossCorrelation.p-phase.maxDelay", "double", 0.5, "771-779"),
    ("crossCorrelation.p-phase.minCCCoef", "double", 0.7, "781-789"),
    ("crossCorrelation.p-phase.components", "strings", ["Z"], "790-797"),
    ("crossCorrelation.s-phase.winStart", "double", -0.5, "801-809"),
    ("crossCorrelation.s-phase.winEnd", "double", 1.0, "811-819"),
    ("crossCorrelation.s-phase.winScaling", "double", 0.04, "821-829"),
    ("crossCorrelation.s-phase.maxDelay", "double", 0.5, "831-839"),
    ("crossCorrelation.s-phase.minCCCoef", "double", 0.7, "841-849"),
    ("crossCorrelation.s-phase.components", "strings", ["L2"], "851-858"),
    ("crossCorrelation.waveformFiltering.filterString", "str", "", "863-870"),
    ("crossCorrelation.waveformFiltering.margin", "double", 1.0, "872-879"),
    ("crossCorrelation.waveformFiltering.resampling", "double", 0.0, "881-889"),
    ("solver.solverType", "str", "LSMR", "893-900"),
    ("solver.algoIterations", "int", 20, "902-909"),
    ("solver.downWeightingByResidual", "doubles", [10.0, 5.0], "911-940 (1 value: start=end)"),
    ("solver.dampingFactor", "doubles", [0.01], "942-968 (1 value: start=end)"),
    ("solver.absoluteLocationConstraint", "doubles", [0.3], "970-997 (1 value: start=end)"),
    ("solver.xcorrWeightScaler", "double", 2.0, "998-1006"),
    ("solver.usePickUncertainties", "bool", False, "1008-1015"),
]
MODULE_OPTIONS = [
    ("automaticOrigins", "bool", True), ("manualOrigins", "bool", True), ("onlyPreferredOrigins", "bool", True),
    ("activeProfiles", "strings", []), ("acceptedOriginAuthors", "strings", []),
    ("performance.delayTime", "int", 10), ("performance.profileTimeAlive", "int", 600),
    ("performance.cacheWaveforms", "bool", True), ("performance.cacheDirectory", "path", "@ROOTDIR@/var/lib/rtdd"),
    ("performance.cachedWaveformLength", "double", 10.0),
    ("connection.primaryGroup", "str", None), ("connection.subscriptions", "strings", None),
]
GLOBAL_OPTIONS = [
    ("core.plugins", "strings", None), ("plugins", "strings", None), ("recordstream", "str", None),
    ("ttt.NLLGrid.tables", "strings", None),
    ("ttt.NLLGrid.kim1983.tablePath", "path", None),
    ("ttt.NLLGrid.kim1983.maxSearchDistance", "double", 10.0),   # plugins/ttt/nll/nll_ttt.cpp:142
    ("ttt.NLLGrid.kim1983.swapBytes", "bool", False),            # nll_ttt.cpp:143
    ("ttt.NLLGrid.kim1983.accessMethod", "str", "KeepOpen"),     # nll_ttt.cpp:144
    ("ttt.NLLGrid.kim1983.maxOpenFiles", "int", 512),            # nll_ttt.cpp:145
    ("ttt.NLLGrid.kim1983.P-Phases", "strings", ["P", "Pg", "Pn"]),
    ("ttt.NLLGrid.kim1983.S-Phases", "strings", ["S", "Sg", "Sn"]),
    ("logging.level", "int", None),
]


# ----------------------------------------------------------------------------- small utilities
def now_iso():
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def md5(path, block=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(block), b""):
            h.update(b)
    return h.hexdigest()


class Tee:
    """Write messages to stdout and to a log file in logs/."""

    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.f = open(path, "a")

    def __call__(self, *msg):
        line = " ".join(str(m) for m in msg)
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()


def write_cfg(path, values, header):
    """Write a SeisComP .cfg file: one 'name = value' line per entry, with a comment header."""
    with open(path, "w") as f:
        for line in header.strip().splitlines():
            f.write(f"# {line}\n")
        f.write("\n")
        for k, v in values.items():
            f.write(f"{k} = {v}\n")


def write_config(run_dir, profile_values, module_values=None, global_values=None, header=""):
    """Create <run_dir>/seiscomp_user/{global,scrtdd}.cfg and <run_dir>/home. Returns the config folder."""
    cfgdir = f"{run_dir}/seiscomp_user"
    os.makedirs(cfgdir, exist_ok=True)
    os.makedirs(f"{run_dir}/home", exist_ok=True)
    gv = dict(GLOBAL_CFG if global_values is None else global_values)
    write_cfg(f"{cfgdir}/global.cfg", gv, header + "\n(global.cfg of this run; SEISCOMP_LOCAL_CONFIG points here)")
    mv = dict(module_cfg(run_dir) if module_values is None else module_values)
    for k, v in profile_values.items():
        mv[f"profile.{PROFILE}.{k}"] = v
    write_cfg(f"{cfgdir}/scrtdd.cfg", mv, header + "\n(scrtdd.cfg of this run; SEISCOMP_LOCAL_CONFIG points here)")
    return cfgdir


def run_env(run_dir):
    """Environment for one scrtdd call: everything from env_seiscomp.sh, plus a private config folder and HOME."""
    if "SEISCOMP_ROOT" not in os.environ:
        sys.exit("SEISCOMP_ROOT is not set: 'source install/env_seiscomp.sh' first")
    env = dict(os.environ)
    env["SEISCOMP_LOCAL_CONFIG"] = f"{run_dir}/seiscomp_user"
    env["HOME"] = f"{run_dir}/home"
    env["ORT_DISABLE_TELEMETRY"] = "1"
    return env


def run_scrtdd(args, run_dir, cwd, stdout_path, stderr_path, log, timeout=TIMEOUT_S):
    """Run 'scrtdd <args>' niced, with /usr/bin/timeout, in cwd. Returns (exit code, wall seconds, argv)."""
    argv = ["nice", "-n", str(NICE), "/usr/bin/timeout", str(timeout), "scrtdd"] + list(args)
    log("  $ (cd", cwd, ";", " ".join(argv), ">", os.path.basename(stdout_path), "2>", os.path.basename(stderr_path), ")")
    t0 = time.time()
    with open(stdout_path, "wb") as fo, open(stderr_path, "wb") as fe:
        p = subprocess.run(argv, cwd=cwd, env=run_env(run_dir), stdout=fo, stderr=fe)
    dt = time.time() - t0
    log(f"  exit code {p.returncode}, {dt:.1f} s")
    return p.returncode, dt, argv


def print_config_vars(run_dir):
    """The configuration variables scrtdd itself reports it reads (names and types, no values)."""
    p = subprocess.run(["/usr/bin/timeout", "60", "scrtdd", "--print-config-vars", "--profile", PROFILE],
                       env=run_env(run_dir), cwd=run_dir, capture_output=True, text=True)
    names = []
    for line in p.stdout.splitlines():
        m = re.match(r"^\s+(\S+)\s+(\S+)\s*$", line)
        if m:
            names.append((m.group(1), m.group(2)))
    return names, p.returncode


def scrtdd_version(run_dir):
    p = subprocess.run(["/usr/bin/timeout", "60", "scrtdd", "--version"], env=run_env(run_dir), cwd=run_dir,
                       capture_output=True, text=True)
    return (p.stdout + p.stderr).strip()


# ----------------------------------------------------------------------------- option resolution
def _config_stack(run_dir):
    """Read the configuration files in SeisComP's order (later files override earlier ones) for module scrtdd."""
    import seiscomp.config as scconfig
    root = os.environ["SEISCOMP_ROOT"]
    local = f"{run_dir}/seiscomp_user"
    files = [f"{root}/etc/defaults/global.cfg", f"{root}/etc/defaults/scrtdd.cfg",
             f"{root}/etc/global.cfg", f"{root}/etc/scrtdd.cfg",
             f"{local}/global.cfg", f"{local}/scrtdd.cfg"]
    cfg = scconfig.Config()
    used = []
    for f in files:
        if os.path.exists(f):
            cfg.readConfig(f)
            used.append(f)
    return cfg, used


def _get(cfg, name, typ):
    """(is_set, value, source file:line) for one variable, parsed like Application::configGet<type>()."""
    st = cfg.symbolTable()
    sym = st.get(name)
    if sym is None:
        return False, None, None
    vals = [str(v) for v in sym.values]
    src = f"{sym.uri}:{sym.line}"
    try:
        if typ in ("str", "path"):
            v = cfg.getString(name)
        elif typ == "bool":
            v = bool(cfg.getBool(name))
        elif typ == "int":
            v = int(cfg.getInt(name))
        elif typ == "double":
            v = float(cfg.getDouble(name))
        elif typ == "strings":
            v = [str(x) for x in cfg.getStrings(name)]
        elif typ == "doubles":
            v = [float(x) for x in vals]
        else:
            v = vals
    except Exception as e:  # a set but unparsable value: the module would fall back to its default
        return True, f"UNPARSABLE {vals} ({e})", src
    return True, v, src


def resolve_options(run_dir, extra=None):
    """Every value scrtdd uses for this run: set in a config file, or the module's fallback default.

    Returns a dict with the raw per-key view and the libhdd structures as scrtdd fills them
    (apps/scrtdd/rtddtool.cpp:340-1028), named like the pyrtdd/libhdd fields.
    """
    cfg, files = _config_stack(run_dir)
    prof = {}
    for key, typ, default, line in PROFILE_OPTIONS:
        is_set, val, src = _get(cfg, f"profile.{PROFILE}.{key}", typ)
        prof[key] = {"value": val if is_set else default, "set_in": src if is_set else
                     f"not set -> scrtdd default (rtddtool.cpp:{line})"}
    mod = {}
    for key, typ, default in MODULE_OPTIONS:
        is_set, val, src = _get(cfg, key, typ)
        mod[key] = {"value": val if is_set else default, "set_in": src if is_set else "not set -> default"}
    glo = {}
    for key, typ, default in GLOBAL_OPTIONS:
        is_set, val, src = _get(cfg, key, typ)
        glo[key] = {"value": val if is_set else default, "set_in": src if is_set else "not set -> default"}

    v = {k: d["value"] for k, d in prof.items()}

    def two(vals, name):
        if isinstance(vals, list) and len(vals) == 1:
            return vals[0], vals[0]
        if isinstance(vals, list) and len(vals) == 2:
            return vals[0], vals[1]
        raise ValueError(f"{name}: needs 1 or 2 values, got {vals}")

    dw = two(v["solver.downWeightingByResidual"], "downWeightingByResidual")
    dmp = two(v["solver.dampingFactor"], "dampingFactor")
    alc = two(v["solver.absoluteLocationConstraint"], "absoluteLocationConstraint")
    ddp = "doubleDifferenceSystem."
    common_clust = dict(
        minEvStaToInterEvRatio=v[ddp + "phaseFiltering.minStationToEventPairDistRatio"],
        minEvStaDist=v[ddp + "phaseFiltering.minStationDistance"],
        maxEvStaDist=v[ddp + "phaseFiltering.maxStationDistance"],
        minNumNeigh=v[ddp + "eventFiltering.minNumNeighbours"],
        minNumPhases=v[ddp + "eventFiltering.minNumPhases"],
        maxNumPhases=0,   # hard-coded in scrtdd (rtddtool.cpp:1020-1021)
    )
    libhdd = {
        "Config": {
            "validPphases": v["P-Phases"], "validSphases": v["S-Phases"],
            "pickUncertaintyClasses": v["pickUncertaintyClasses"], "PSTableOnly": v["PSTableOnly"],
            "wfFilter": {"filterStr": v["crossCorrelation.waveformFiltering.filterString"],
                         "resampleFreq": v["crossCorrelation.waveformFiltering.resampling"],
                         "extraTraceLen": v["crossCorrelation.waveformFiltering.margin"]},
        },
        "ClusteringOptions_multiEvent": dict(common_clust,
            maxNumNeigh=v[ddp + "eventPairSelection.multiEvent.maxNumNeighbours"],
            maxNeighbourDist=v[ddp + "eventPairSelection.multiEvent.maxNeighbourDistance"],
            numEllipsoids=v[ddp + "eventPairSelection.multiEvent.numEllipsoids"]),
        "ClusteringOptions_singleEvent": dict(common_clust,
            maxNumNeigh=v[ddp + "eventPairSelection.singleEvent.maxNumNeighbours"],
            maxNeighbourDist=v[ddp + "eventPairSelection.singleEvent.maxNeighbourDistance"],
            numEllipsoids=v[ddp + "eventPairSelection.singleEvent.numEllipsoids"],
            note=("single-event step 1 uses minEvStaToInterEvRatio=1 and no cross-correlation; step 2 uses "
                  "numEllipsoids=1 (rtddtool.cpp:2075-2112). libhdd sets numEllipsoids=0 whenever "
                  "maxNumNeigh<=0 (clustering.cpp:311-314)")),
        "XcorrOptions": {
            "enable": v["crossCorrelation.enable"],
            "minEvStaDist": v["crossCorrelation.minStationDistance"],
            "maxEvStaDist": v["crossCorrelation.maxStationDistance"],
            "maxInterEvDist": v["crossCorrelation.maxInterEventDistance"],
            "phase": {ph: {"minCoef": v[f"crossCorrelation.{p}-phase.minCCCoef"],
                           "startOffset": v[f"crossCorrelation.{p}-phase.winStart"],
                           "endOffset": v[f"crossCorrelation.{p}-phase.winEnd"],
                           "winScaling": v[f"crossCorrelation.{p}-phase.winScaling"],
                           "maxDelay": v[f"crossCorrelation.{p}-phase.maxDelay"],
                           "components": v[f"crossCorrelation.{p}-phase.components"]}
                      for ph, p in (("P", "p"), ("S", "s"))},
        },
        "SolverOptions": {
            "type": v["solver.solverType"], "L2normalization": True, "solverIterations": 0,   # hard-coded (rtddtool.cpp:1022-1023)
            "algoIterations": v["solver.algoIterations"],
            "absLocConstraintStart": alc[0], "absLocConstraintEnd": alc[1],
            "dampingFactorStart": dmp[0], "dampingFactorEnd": dmp[1],
            "downWeightingByResidualStart": dw[0], "downWeightingByResidualEnd": dw[1],
            "usePickUncertainties": v["solver.usePickUncertainties"],
            "xcorrWeightScaler": v["solver.xcorrWeightScaler"],
        },
        "TravelTimeTable": {
            "tableType": v["tableType"], "tableModel": v["tableModel"],
            "plugin_tablePath": glo["ttt.NLLGrid.kim1983.tablePath"]["value"],
            "maxSearchDistance_m": glo["ttt.NLLGrid.kim1983.maxSearchDistance"]["value"],
            "swapBytes": glo["ttt.NLLGrid.kim1983.swapBytes"]["value"],
            "accessMethod": glo["ttt.NLLGrid.kim1983.accessMethod"]["value"],
            "maxOpenFiles": glo["ttt.NLLGrid.kim1983.maxOpenFiles"]["value"],
        },
        "waveform_disk_cache": {
            "enabled": mod["performance.cacheWaveforms"]["value"],
            "directory": f'{mod["performance.cacheDirectory"]["value"]}/{PROFILE}/wfcache',
            "cachedWaveformLength_s": mod["performance.cachedWaveformLength"]["value"],
        },
    }
    out = {"config_files_read_in_order": files, "profile": PROFILE, "profile_options": prof,
           "module_options": mod, "global_options": glo, "libhdd_equivalent": libhdd}
    if extra:
        out.update(extra)
    return out


def check_print_config_vars(names, resolved):
    """Every profile.* and ttt.* variable scrtdd reports reading must be in the dump."""
    covered = set(f"profile.{PROFILE}.{k}" for k in resolved["profile_options"])
    covered |= set(resolved["module_options"]) | set(resolved["global_options"])
    missing = [n for n, _ in names if (n.startswith(f"profile.{PROFILE}.") or n.startswith("ttt.")
                                       or n.startswith("performance.")) and n not in covered]
    return missing


def dump_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=str)
