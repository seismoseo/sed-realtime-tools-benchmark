#!/usr/bin/env python
# scrtdd_common_sanramon.py -- shared helpers for the scrtdd (SeisComP module) runs of the San Ramon 2015
# benchmark. A copy of runs/gwangyang/scrtdd/scripts/scrtdd_common.py (helper functions unchanged) with the
# San Ramon inputs and the San Ramon settings blocks (rtDD/libhdd DEFAULT clustering and solver, written out
# as scrtdd keys, and the P1 cross-correlation settings), so that pyrtdd runs P0/P1 and scrtdd runs S0/S1 use
# the same numbers. scrtdd's own PROFILE defaults differ from libhdd's in several places (minNumNeighbours 4 vs
# 8, multiEvent.numEllipsoids 0 vs 5, crossCorrelation.maxStationDistance 60 km vs none,
# maxInterEventDistance 2 km vs none), so every value is written explicitly.
#
# Imported by scrtdd_sanramon.py (same folder). It must run with the Python of conda env 'seiscomp' after
# 'source install/env_seiscomp.sh', because it uses SeisComP's own configuration reader (seiscomp.config) to
# report what scrtdd reads.
#
# What is here:
#   1. Paths of the inputs (catalog CSVs, SeisComP inventory, SDS archive, NonLinLoc TRANS_MERC grids).
#   2. The settings blocks as scrtdd profile keys.
#   3. PROFILE_OPTIONS: every option the scrtdd v2.0.10 module reads for a profile, with its fallback value and
#      the line of apps/scrtdd/rtddtool.cpp; resolve_options() dumps EVERY value the module uses (set or
#      default) and translates it into the libhdd structures named as in pyrtdd.
#   4. write_config() writes a private SEISCOMP_LOCAL_CONFIG folder (global.cfg + scrtdd.cfg) per run.
#   5. run_scrtdd() runs one scrtdd command with SEISCOMP_LOCAL_CONFIG and HOME inside the run folder, niced,
#      under 'prlimit --as' (60 GB), timed by /usr/bin/time -v, with /usr/bin/timeout (SeisComP ships its own
#      bin/timeout, so the full path is used).

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
DATA = f"{PROJECT}/data/sanramon_2015"
CAT = f"{DATA}/inputs/rtdd_catalog"
STATION_CSV = f"{CAT}/station.csv"
EVENT_CSV = f"{CAT}/event.csv"                           # NCSS routine locations (start of every run)
PHASE_CSV = f"{CAT}/phase.csv"                           # 25,684 NCSS analyst picks
STATIONXML = f"{DATA}/inputs/stations.xml"
RUNROOT = f"{PROJECT}/runs/sanramon/scrtdd"
INVENTORY_XML = f"{RUNROOT}/inputs/inventory_sc.xml"     # fdsnxml2inv of stations.xml (channel orientation)
SDS_DIR = f"{DATA}/inputs/sds"
TABLE = "sanramon_con"
NLL_TABLEPATH = f"{DATA}/inputs/nll_con_tm/time/{TABLE}"  # folder + model name, as the tttnll plugin wants it
LOGDIR = f"{PROJECT}/logs"
PROFILE = "sanramon"
SCRTDD_SRC = f"{PROJECT}/software/src/seiscomp/src/extras/scrtdd"

NICE = 10              # Server A is shared
TIMEOUT_S = 6 * 3600   # the cross-correlation run S1 may take hours (685 events, ~360k phase pairs)
AS_LIMIT_BYTES = 60_000_000_000   # prlimit --as

# ----------------------------------------------------------------------------- shared settings
# Global configuration (global.cfg of the run). tttnll is scrtdd's plugin that exposes NonLinLoc grids to
# SeisComP under the travel-time interface name "NLLGrid". maxSearchDistance is in metres; 0.1 m is the libhdd /
# pyrtdd default (libs/hdd/ttt/nllgrid.h:47) and all 528 station/phase grids are found with it (checked with
# pyrtdd), so both programs use the same tolerance (the plugin's own default would be 10 m). maxOpenFiles 512
# is the plugin and pyrtdd default, written explicitly.
GLOBAL_CFG = {
    "plugins": "tttnll",
    f"ttt.NLLGrid.tables": TABLE,
    f"ttt.NLLGrid.{TABLE}.tablePath": NLL_TABLEPATH,
    f"ttt.NLLGrid.{TABLE}.maxSearchDistance": "0.1",
    f"ttt.NLLGrid.{TABLE}.maxOpenFiles": "512",
    "recordstream": f"sdsarchive://{SDS_DIR}",
}

# Profile keys common to every run (written as profile.sanramon.<key>).
COMMON = {
    # region is used only in real time to pick a profile for an incoming origin; --profile overrides it.
    "regionType": "CIRCULAR",
    "region": "37.7860, -121.9630, 30",
    "methodID": "RTDD",
    "tableType": "NLLGrid",
    "tableModel": TABLE,
    "PSTableOnly": "true",
    # the catalog uses plain P and S (pyrtdd: validPphases ['P'], validSphases ['S'])
    "P-Phases": "P",
    "S-Phases": "S",
    "pickUncertaintyClasses": "0.000, 0.025, 0.050, 0.100, 0.200, 0.400",   # rtDD default; unused (usePickUncertainties false)
}

# Clustering 'rtdd_default' = libhdd ClusteringOptions() (libs/hdd/dd.h:70-93): ellipsoids (numEllipsoids 5),
# maxNeighbourDist 5 km, minNumNeigh 8, maxNumNeigh 40, minNumPhases 8, minEvStaToInterEvRatio 3, no station
# distance limits. minNumPhases and minNumNeighbours are ONE setting each in scrtdd, used for both multi- and
# single-event clustering (rtddtool.cpp:566-589). The single-event block is not used (multi-event runs only)
# and is written with libhdd's values for completeness.
CLUSTERING_RTDD_DEFAULT = {
    "doubleDifferenceSystem.eventFiltering.minNumPhases": "8",
    "doubleDifferenceSystem.eventFiltering.minNumNeighbours": "8",
    "doubleDifferenceSystem.phaseFiltering.minStationToEventPairDistRatio": "3",
    "doubleDifferenceSystem.phaseFiltering.minStationDistance": "0",
    "doubleDifferenceSystem.phaseFiltering.maxStationDistance": "-1",
    "doubleDifferenceSystem.eventPairSelection.multiEvent.maxNumNeighbours": "40",
    "doubleDifferenceSystem.eventPairSelection.multiEvent.maxNeighbourDistance": "5",
    "doubleDifferenceSystem.eventPairSelection.multiEvent.numEllipsoids": "5",
    "doubleDifferenceSystem.eventPairSelection.singleEvent.maxNumNeighbours": "40",
    "doubleDifferenceSystem.eventPairSelection.singleEvent.maxNeighbourDistance": "5",
    "doubleDifferenceSystem.eventPairSelection.singleEvent.numEllipsoids": "5",
}
# Nearest-neighbour variant (sensitivity runs P0n/P1n of pyrtdd; S0n/S1n here if run).
CLUSTERING_NEAREST_NEIGHBOUR = dict(CLUSTERING_RTDD_DEFAULT, **{
    "doubleDifferenceSystem.eventPairSelection.multiEvent.numEllipsoids": "0"})

# Solver 'rtdd_default' = libhdd SolverOptions() (libs/hdd/dd.h:116-130).
SOLVER_RTDD_DEFAULT = {
    "solver.solverType": "LSMR",
    "solver.algoIterations": "20",
    "solver.downWeightingByResidual": "10, 5",
    "solver.dampingFactor": "0.01",
    "solver.absoluteLocationConstraint": "0.3",
    "solver.xcorrWeightScaler": "2.0",
    "solver.usePickUncertainties": "false",
}

# Waveform processing of S1 (= pyrtdd P1): 1000 Hz resampling (libhdd's own windowed-sinc resampler) and a
# 4-pole causal Butterworth band-pass 1.5-15 Hz (SeisComP BW(4,1.5,15) = ObsPy bandpass corners=4, one pass).
# The value must be quoted: a bare comma would turn it into a list.
WF_FILTER = {
    "crossCorrelation.waveformFiltering.filterString": '"BW(4,1.5,15)"',
    "crossCorrelation.waveformFiltering.margin": "1",
    "crossCorrelation.waveformFiltering.resampling": "1000",
}
# Cross-correlation of S1 (= pyrtdd P1): libhdd's default windows (dd.h:93-114) and no station or inter-event
# distance limit (libhdd default -1; scrtdd's profile defaults would be 60 km and 2 km); P components Z then 1
# (vertical of the 1/2/3 borehole sensors), S on L2.
XCORR_P1 = dict({
    "crossCorrelation.enable": "true",
    "crossCorrelation.minStationDistance": "0",
    "crossCorrelation.maxStationDistance": "-1",
    "crossCorrelation.maxInterEventDistance": "-1",
    "crossCorrelation.p-phase.minCCCoef": "0.7",
    "crossCorrelation.p-phase.winStart": "-0.5",
    "crossCorrelation.p-phase.winEnd": "0.5",
    "crossCorrelation.p-phase.winScaling": "0.02",
    "crossCorrelation.p-phase.maxDelay": "0.5",
    "crossCorrelation.p-phase.components": "Z, 1",
    "crossCorrelation.s-phase.minCCCoef": "0.7",
    "crossCorrelation.s-phase.winStart": "-0.5",
    "crossCorrelation.s-phase.winEnd": "1.0",
    "crossCorrelation.s-phase.winScaling": "0.04",
    "crossCorrelation.s-phase.maxDelay": "0.5",
    "crossCorrelation.s-phase.components": "L2",
}, **WF_FILTER)
XCORR_OFF = {"crossCorrelation.enable": "false"}

# Module (not profile) settings. The waveform disk cache (scrtdd default: on, 10 s of raw data per phase in
# $SEISCOMP_ROOT/var/lib/rtdd) is switched OFF here, because the pyrtdd run P1 cannot use one (its filtering
# proxy must see exactly the window libhdd processes); so both programs read every trace straight from the SDS
# archive. The cache directory is still pointed into the run folder, so nothing can be written elsewhere.
def module_cfg(run_dir):
    return {
        "performance.cacheWaveforms": "false",
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
    (f"ttt.NLLGrid.{TABLE}.tablePath", "path", None),
    (f"ttt.NLLGrid.{TABLE}.maxSearchDistance", "double", 10.0),   # plugins/ttt/nll/nll_ttt.cpp:142
    (f"ttt.NLLGrid.{TABLE}.swapBytes", "bool", False),            # nll_ttt.cpp:143
    (f"ttt.NLLGrid.{TABLE}.accessMethod", "str", "KeepOpen"),     # nll_ttt.cpp:144
    (f"ttt.NLLGrid.{TABLE}.maxOpenFiles", "int", 512),            # nll_ttt.cpp:145
    (f"ttt.NLLGrid.{TABLE}.P-Phases", "strings", ["P", "Pg", "Pn"]),
    (f"ttt.NLLGrid.{TABLE}.S-Phases", "strings", ["S", "Sg", "Sn"]),
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
    """Run 'scrtdd <args>' niced, under prlimit --as, timed by /usr/bin/time -v (written to
    <run_dir>/time_v.txt: peak RSS, CPU), with /usr/bin/timeout, in cwd. Returns (exit code, wall seconds, argv)."""
    argv = ["nice", "-n", str(NICE), "prlimit", f"--as={AS_LIMIT_BYTES}", "/usr/bin/time", "-v", "-o",
            f"{run_dir}/time_v.txt", "/usr/bin/timeout", str(timeout), "scrtdd"] + list(args)
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
            "plugin_tablePath": glo[f"ttt.NLLGrid.{TABLE}.tablePath"]["value"],
            "maxSearchDistance_m": glo[f"ttt.NLLGrid.{TABLE}.maxSearchDistance"]["value"],
            "swapBytes": glo[f"ttt.NLLGrid.{TABLE}.swapBytes"]["value"],
            "accessMethod": glo[f"ttt.NLLGrid.{TABLE}.accessMethod"]["value"],
            "maxOpenFiles": glo[f"ttt.NLLGrid.{TABLE}.maxOpenFiles"]["value"],
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
