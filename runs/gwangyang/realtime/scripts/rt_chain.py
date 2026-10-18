#!/usr/bin/env python
# rt_chain.py -- step 10: a SHORT REAL-TIME CHAIN TEST of SeisComP on Server A, loopback interface only:
#
#     waveform file --> scautopick (DL3C / SDL3C, phasenet_original) --PICK, AMPLITUDE--> scmaster (127.0.0.1:28180)
#        --> scautoloc (LOCSAT, local grid) --LOCATION--> scevent --EVENT--> scrtdd (single-event, profile gwangyang)
#        --RELOCATION--> scevent;   scmaster's dbstore writes every object into <run>/db/seiscomp.sqlite
#
# Usage (after 'source install/env_seiscomp.sh'; every stage is a DRY RUN unless --apply is given):
#     python rt_chain.py prepare --run RT1_filefeed [--apply]     # configs, reference catalog, sorted data, database
#            run variants (prepare only, stored in <run>/run_variant.json and used by 'start'):
#            --autoloc-timing creationTime : scautoloc --timing creationTime (default pickTime)
#            --prefer-rtdd                 : scevent prefers scrtdd's origins (AUTHOR priority) - loop-protection test
#     python rt_chain.py start   --run RT1_filefeed [--apply]     # scmaster, scevent, scautoloc, scrtdd (background)
#     python rt_chain.py replay  --run RT1_filefeed --event 20210827220322 [--feed file|paced] [--apply]
#     python rt_chain.py stop    --run RT1_filefeed [--apply]     # stop every module of this run, prove it
#     python rt_chain.py dump    --run RT1_filefeed [--apply]     # read the database back (scevtls, scxmldump, SQL)
#     python rt_chain.py status  --run RT1_filefeed               # which of our processes are alive, what listens
#
# Why the data feed is a file and not SeedLink: SeisComP's seedlink server always binds its listening socket to
# INADDR_ANY (software/src/seiscomp/src/base/seedlink/apps/seedlink/iosystem.cc:2788, no bind-address option), so
# it cannot be restricted to localhost and is NOT started (network rule). scautopick instead runs in normal
# messaging mode (no --offline, no --ep) and reads the time-sorted miniSEED file as its record stream:
#   --feed file  : '-I file://<sorted.mseed>' read at full speed (feed B of the task);
#   --feed paced : 'msrtsimul -c -m historic' writes the same sorted records to scautopick's stdin ('-I file://-')
#                  at the pace of the original record times (original timestamps, speed factor PACE_SPEED), so the
#                  creation times show real-time latencies. No network socket is involved in either feed.
# '--playback' is needed in both feeds: without it scautopick requests data from "now - leadTime" only
# (scautopick/picker.cpp:416-423), which would drop all historic records.
#
# Network rule: scmaster is the only server. Its interface.bind is 127.0.0.1:28180 (non-default port, checked free
# with 'ss -ltnp' first), SSL is off, queue ACLs are 127.0.0.1. After every start the listening sockets of all our
# PIDs are listed (TCP and UDP) and the run is stopped at once if anything else listens. 'stop' ends every process
# by PID (never by pattern) and proves with /proc, 'pgrep -x' and 'ss' that nothing of ours is left.
#
# Settings that differ from the offline steps, and why, are written as comments into each generated .cfg file and
# collected in <run>/options/*.json (every key set in the configuration stack with its source file:line, plus the
# documented defaults of every unset parameter of each module, plus the command lines actually run).
#
# Script provenance (added 2026-10-17, after the independent verification; runs RT1-RT5 were made before it): every
# --apply stage appends the md5 of each driver script on disk (rt_chain.py, rt_options.py, rt_offline_check.py,
# rt_analyze.py), the md5 of this script as loaded, the stage, time and argv to <run>/options/script_provenance.json,
# and keeps a copy of this script as <run>/options/scripts/rt_chain.<md5>.py (copied only if absent). It is recorded
# at the start of the stage, so a stage that stops at one of its own checks is listed too.

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import time

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
SDS_DIR = f"{DATA}/inputs/sds"
PLAYBACK_DIR = f"{DATA}/inputs/playback"                 # <kma_id>.mseed, unsorted, 512-byte records
INVENTORY_XML = f"{DATA}/inputs/inventory_sc.xml"       # SeisComP inventory of step Prep (coordinates = station.csv)
STATION_CSV = f"{DATA}/inputs/rtdd_catalog/station.csv"
NLL_TABLEPATH = f"{DATA}/inputs/nll_kim1983/time/kim1983"
RTROOT = f"{PROJECT}/runs/gwangyang/realtime"
LOGDIR = f"{PROJECT}/logs"
DLSTEP = f"{PROJECT}/runs/gwangyang/dlpicker"
DL_CFG = f"{DLSTEP}/config/scautopick_phasenet_original.cfg"   # best model of step 09 (rule fixed before results)
BINDINGS_XML = f"{DLSTEP}/config/bindings_config.xml"          # 54 stations, detecStream = catalog sensor code
DL_SORTED_DIR = f"{DLSTEP}/input"                               # step 09's sorted files (only for an md5 check)
SCRTDD_STEP = f"{PROJECT}/runs/gwangyang/scrtdd"
TEMPLATE_DIR = f"{SCRTDD_STEP}/templates"                      # scrtdd.cfg = run S1's profile (step 08)
TEMPLATE_CATALOG = f"{TEMPLATE_DIR}/reference_catalog"         # S1 positions of the 11 events + 763 picks

REPLAY_EVENTS = {"20210827220322": 3, "20260202194119": 9}     # kma_id -> rtdd_id (ML 2.2 and ML 1.6)
CATALOG_ID_OFFSET = 100   # reference-catalog id = rtdd_id + 100: avoids scrtdd's step-1 id clash with id 1
                          # (catalog.cpp:389-394 + clustering.cpp:342, found in step 08), keeps ids traceable

BIND_IP = "127.0.0.1"
SCMASTER_PORT = 28180      # non-default (default 18180); checked free before start
HOSTURL = f"{BIND_IP}:{SCMASTER_PORT}/production"
NICE = 10                  # Server A is shared (project rule 3)
PACE_SPEED = 1.0           # msrtsimul speed factor of the paced feed (1 = real time)
REPLAY_TIMEOUT_S = 900     # hard limit for one scautopick replay
WAIT_RELOC_S = 240         # how long 'replay' waits for scrtdd's result after scautopick has finished
GRACE_S = 35               # after the relocation: time for scevent + scrtdd's reaction (delayTime 10 s) = loop check
HOSTNAME = os.uname().nodename.split(".")[0]                   # SeisComP author = <module>@<hostname>

# scautoloc for this local network (a priori choices, written once before any result; reasons in the .cfg)
AUTOLOC = {
    "grid_lat": [round(34.70 + 0.1 * i, 2) for i in range(7)],          # 34.7 ... 35.3
    "grid_lon": [round(127.4286 + 0.1 * i, 4) for i in range(7)],       # 127.43 ... 128.03 (centred on 127.7286)
    "grid_depths_km": [5, 10, 15, 20, 25],
    "grid_radius_deg": 0.1, "grid_maxdist_deg": 1.0,
    "min_phase_count": 8,
}
MODULE_ORDER = ["scmaster", "scevent", "scautoloc", "scrtdd"]          # start order; stop is the reverse
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_SCRIPTS = ["rt_chain.py", "rt_options.py", "rt_offline_check.py", "rt_analyze.py"]
SCRIPT_BYTES = open(os.path.abspath(__file__), "rb").read()            # this script as loaded (copied for provenance)
SCRIPT_MD5 = hashlib.md5(SCRIPT_BYTES).hexdigest()


# ----------------------------------------------------------------------------- small helpers
def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def md5(path, block=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(block), b""):
            h.update(b)
    return h.hexdigest()


class Tee:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = open(path, "a")
        self.path = path

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        self.f.write(s + "\n")
        self.f.flush()


def dump_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=str)


def run_dir(name):
    return f"{RTROOT}/{name}"


def record_provenance(run, stage, log):
    """Append one entry to <run>/options/script_provenance.json (md5 of every driver script on disk, md5 of this
    script as loaded, stage, time, argv) and keep a copy of this script as <run>/options/scripts/<name>.<md5>.py."""
    opt = f"{run}/options"
    os.makedirs(f"{opt}/scripts", exist_ok=True)
    name = os.path.basename(os.path.abspath(__file__))
    copy = f"{opt}/scripts/{name[:-3]}.{SCRIPT_MD5}.py"
    if not os.path.exists(copy):
        with open(copy, "wb") as f:
            f.write(SCRIPT_BYTES)
    on_disk = {s: (md5(f"{SCRIPT_DIR}/{s}") if os.path.exists(f"{SCRIPT_DIR}/{s}") else None) for s in DRIVER_SCRIPTS}
    entry = dict(time=now_iso(), stage=stage, script=name, script_md5_as_loaded=SCRIPT_MD5, script_copy=copy,
                 argv=list(sys.argv), python=sys.executable, cwd=os.getcwd(), host=HOSTNAME,
                 driver_scripts_md5_on_disk=on_disk, recorded_at="start of the stage")
    path = f"{opt}/script_provenance.json"
    entries = json.load(open(path)) if os.path.exists(path) else []
    entries.append(entry)
    with open(path + ".tmp", "w") as f:
        json.dump(entries, f, indent=1)
    os.replace(path + ".tmp", path)
    log(f"# provenance: {stage} by {name} md5 {SCRIPT_MD5} -> {path} (entry {len(entries)}); driver scripts on disk: "
        f"{on_disk}")


def sc_env(run):
    """Environment of every SeisComP call of this run: env_seiscomp.sh + a private config folder and HOME."""
    if "SEISCOMP_ROOT" not in os.environ:
        sys.exit("SEISCOMP_ROOT is not set: 'source install/env_seiscomp.sh' first")
    env = dict(os.environ)
    env["SEISCOMP_LOCAL_CONFIG"] = f"{run}/seiscomp_user"
    env["HOME"] = f"{run}/home"
    env["ORT_DISABLE_TELEMETRY"] = "1"
    return env


def sh(argv, log, run, cwd=None, timeout=600, stdout_path=None, check=False, stdin=None):
    """Run one short command (niced, /usr/bin/timeout) and log it; returns (exit code, stdout text)."""
    full = ["nice", "-n", str(NICE), "/usr/bin/timeout", str(timeout)] + list(argv)
    log("  $", " ".join(full) + (f" > {stdout_path}" if stdout_path else ""))
    t0 = time.time()
    if stdout_path:
        with open(stdout_path, "wb") as fo:
            p = subprocess.run(full, cwd=cwd or run, env=sc_env(run), stdout=fo, stderr=subprocess.PIPE, stdin=stdin)
        out = ""
    else:
        p = subprocess.run(full, cwd=cwd or run, env=sc_env(run), capture_output=True, stdin=stdin)
        out = p.stdout.decode(errors="replace")
    err = p.stderr.decode(errors="replace")
    log(f"    exit {p.returncode} ({time.time() - t0:.1f} s)" + (f"; stderr tail: {err.strip()[-600:]}" if err.strip() else ""))
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(full)}")
    return p.returncode, out


def listening(pids=None, port=None):
    """Listening TCP and UDP sockets (ss -ltnp / -lunp), optionally only those of the given PIDs or port."""
    rows = []
    for proto, flag in (("tcp", "-ltnp"), ("udp", "-lunp")):
        out = subprocess.run(["ss", "-H", flag], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if pids is not None and not any(f"pid={p}," in line for p in pids):
                continue
            if port is not None and f":{port} " not in line + " ":
                continue
            rows.append(f"{proto} {line.strip()}")
    return rows


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return os.path.exists(f"/proc/{pid}")


def proc_comm(pid):
    try:
        return open(f"/proc/{pid}/comm").read().strip()
    except OSError:
        return None


def proc_cpu(pid):
    """utime+stime in seconds and peak resident memory (VmHWM, kB) of a live process."""
    try:
        f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        tck = os.sysconf("SC_CLK_TCK")
        cpu = (int(f[11]) + int(f[12])) / tck
        hwm = None
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmHWM:"):
                hwm = int(line.split()[1])
        return cpu, hwm
    except OSError:
        return None, None


def write_cfg(path, header, items):
    """items: list of (key, value, why). 'why' becomes a comment above the line."""
    lines = [f"# {h}" if h else "#" for h in header.strip().splitlines()] + [""]
    for key, value, why in items:
        if why:
            lines += [f"# {w}" for w in why.strip().splitlines()]
        lines.append(f"{key} = {value}")
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


def parse_simple_cfg(path):
    """'key = value' lines of a flat SeisComP cfg (the step-08 template has no blocks), in file order."""
    out = []
    for line in open(path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        k, v = s.split("=", 1)
        out.append((k.strip(), v.strip()))
    return out


# ----------------------------------------------------------------------------- stage: prepare
def stage_prepare(a, log):
    run = run_dir(a.run)
    for sub in ("seiscomp_user", "home", "config", "data", "db", "logs", "rtdd_cache", "reference_catalog",
                "work/scmaster", "work/scevent", "work/scautoloc", "work/scrtdd", "work/scautopick", "network",
                "options", "db_dump", "results"):
        log(f"  mkdir {run}/{sub}")
        if a.apply:
            os.makedirs(f"{run}/{sub}", exist_ok=True)
    db = f"{run}/db/seiscomp.sqlite"

    # 1. sorted playback files: scmssort -u -E as SeisComP recommends for file playback (records sorted by end
    #    time, duplicates removed); md5 compared with step 09's sorted files = the same input as the offline picks
    for ev in REPLAY_EVENTS:
        out = f"{run}/data/{ev}_sorted.mseed"
        if a.apply:
            sh(["scmssort", "-u", "-E", "-v", "-o", out, f"{PLAYBACK_DIR}/{ev}.mseed"], log, run, check=True)
            ref = f"{DL_SORTED_DIR}/{ev}_sorted.mseed"
            same = os.path.exists(ref) and md5(ref) == md5(out)
            log(f"    {out}: md5 {md5(out)}; identical to step 09's {ref}: {same}")
        else:
            log(f"  would sort {PLAYBACK_DIR}/{ev}.mseed -> {out}")

    # 2. reference catalog = multi-event run S1 WITHOUT the replayed events (positions and picks removed, as
    #    step 08's leave-one-out catalogs), ids + CATALOG_ID_OFFSET
    drop = set(REPLAY_EVENTS.values())
    ev_rows = list(csv.DictReader(open(f"{TEMPLATE_CATALOG}/event.csv")))
    ph_rows = list(csv.DictReader(open(f"{TEMPLATE_CATALOG}/phase.csv")))
    keep_ev = [r for r in ev_rows if int(r["id"]) not in drop]
    keep_ph = [r for r in ph_rows if int(r["eventId"]) not in drop]
    log(f"  reference catalog: {len(keep_ev)} of {len(ev_rows)} events, {len(keep_ph)} of {len(ph_rows)} picks "
        f"(dropped rtdd ids {sorted(drop)}), ids +{CATALOG_ID_OFFSET}")
    if a.apply:
        for rows, name, idk in ((keep_ev, "event.csv", "id"), (keep_ph, "phase.csv", "eventId")):
            with open(f"{run}/reference_catalog/{name}", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
                w.writeheader()
                for r in rows:
                    r = dict(r)
                    r[idk] = str(int(r[idk]) + CATALOG_ID_OFFSET)
                    w.writerow(r)
        shutil.copyfile(f"{TEMPLATE_CATALOG}/station.csv", f"{run}/reference_catalog/station.csv")

    # 3. scautoloc nucleation grid and station list for this local network
    stations = list(csv.DictReader(open(STATION_CSV)))
    grid = [(la, lo, d) for d in AUTOLOC["grid_depths_km"] for la in AUTOLOC["grid_lat"] for lo in AUTOLOC["grid_lon"]]
    log(f"  scautoloc grid: {len(grid)} points ({len(AUTOLOC['grid_lat'])} lat x {len(AUTOLOC['grid_lon'])} lon x "
        f"{len(AUTOLOC['grid_depths_km'])} depths); station list: {len(stations)} stations")
    if a.apply:
        with open(f"{run}/config/scautoloc_grid.conf", "w") as f:
            f.write("# scautoloc nucleation grid for the Gwangyang test (rt_chain.py). Columns: latitude longitude\n"
                    "# depth(km) radius(deg) maxStationDistance(deg) minPickCount (nucleator.cpp:785-820).\n"
                    "# 0.1-degree spacing within +-0.3 degree (+-33 km) of 35.0 N 127.7286 E, depths 5-25 km; radius 0.1\n"
                    "# degree covers one cell; 1.0 degree reaches all 54 stations (7-99 km); a nucleation needs 8\n"
                    "# picks (with ~40-50 stations per event, 8 coincident false picks are very unlikely).\n")
            for la, lo, d in grid:
                f.write(f"{la:7.2f} {lo:9.4f} {d:5.1f} {AUTOLOC['grid_radius_deg']:5.2f} "
                        f"{AUTOLOC['grid_maxdist_deg']:5.2f} {AUTOLOC['min_phase_count']}\n")
        with open(f"{run}/config/scautoloc_station.conf", "w") as f:
            f.write("# scautoloc station configuration (rt_chain.py): network station usage maxNucleationDistance(deg)\n"
                    "# all 54 KS stations of inputs/rtdd_catalog/station.csv may nucleate up to 1.0 degree; any other\n"
                    "# station is disabled (last line). Parsing stops at the first malformed line (stationconfig.cpp).\n")
            for s in stations:
                f.write(f"{s['networkCode']} {s['stationCode']} 1 1.0\n")
            f.write("* * 0 0\n")

    # 4. configuration files (SEISCOMP_LOCAL_CONFIG = <run>/seiscomp_user) + the run variant (read by 'start')
    variant = dict(prefer_rtdd=a.prefer_rtdd, autoloc_timing=a.autoloc_timing)
    log(f"  run variant: {variant}")
    if a.apply:
        dump_json(f"{run}/run_variant.json", variant)
        write_configs(run, db, log, prefer_rtdd=a.prefer_rtdd)
    else:
        log(f"  would write global.cfg, scmaster.cfg, scautopick.cfg, scautoloc.cfg, scevent.cfg, scrtdd.cfg in {run}/seiscomp_user")

    # 5. database: SeisComP schema, WAL journal, inventory and the scautopick bindings
    log(f"  database {db}: schema {os.environ.get('SEISCOMP_ROOT')}/share/db/sqlite3.sql; journal_mode WAL (readers "
        f"never wait for scmaster's writes: the SeisComP SQLite driver sets no busy timeout); then scdb -i inventory "
        f"and bindings")
    if a.apply:
        if os.path.exists(db):
            sys.exit(f"{db} exists: use a new --run name (never overwrite a run's database)")
        con = sqlite3.connect(db)
        con.executescript(open(f"{os.environ['SEISCOMP_ROOT']}/share/db/sqlite3.sql").read())
        jm = con.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        con.commit()
        con.close()
        log(f"    schema loaded; journal_mode = {jm}")
        sh(["scdb", "-i", INVENTORY_XML, "-d", f"sqlite3://{db}"], log, run, check=True)
        sh(["scdb", "-i", BINDINGS_XML, "-d", f"sqlite3://{db}"], log, run, check=True)
        counts = db_counts(db)
        log(f"    rows after import: {counts}")
        shutil.copyfile(db, f"{run}/db/seiscomp_after_import.sqlite")
        dump_json(f"{run}/db/db_info.json", dict(created=now_iso(), schema=f"{os.environ['SEISCOMP_ROOT']}/share/db/sqlite3.sql",
                                                 journal_mode=jm, inventory_xml=INVENTORY_XML, inventory_md5=md5(INVENTORY_XML),
                                                 bindings_xml=BINDINGS_XML, bindings_md5=md5(BINDINGS_XML),
                                                 row_counts_after_import=counts,
                                                 snapshot_after_import=f"{run}/db/seiscomp_after_import.sqlite"))

    # 6. option dumps of the configuration as written (runtime dumps are added by 'start' and 'stop')
    if a.apply:
        static_option_dumps(run, db, log)


def db_counts(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = {}
    for t in ("Network", "Station", "SensorLocation", "Stream", "ConfigModule", "ConfigStation", "ParameterSet",
              "Parameter", "Pick", "Amplitude", "Origin", "Arrival", "Event", "OriginReference"):
        out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    con.close()
    return out


def write_configs(run, db, log, prefer_rtdd=False):
    u = f"{run}/seiscomp_user"
    hdr = (f"Generated by runs/gwangyang/realtime/scripts/rt_chain.py on {now_iso()} for run {os.path.basename(run)}.\n"
           f"SEISCOMP_LOCAL_CONFIG of this run (never ~/.seiscomp). Read after $SEISCOMP_ROOT/etc/defaults and etc/\n"
           f"(etc/global.cfg sets core.plugins = dbsqlite3, the only database driver of this build).")
    write_cfg(f"{u}/global.cfg", hdr, [
        ("connection.server", HOSTURL,
         "the private scmaster of this run: loopback interface, non-default port"),
        ("recordstream", f"sdsarchive://{SDS_DIR}",
         "scrtdd reads the reference-catalog waveforms AND the new event's waveforms from the SDS archive\n"
         "(all 1656 traces are there). scautopick overrides it with -I on its command line."),
    ])
    groups = ("AMPLITUDE, PICK, LOCATION, RELOCATION, MAGNITUDE, FOCMECH, EVENT, QC, PUBLICATION, GUI, INVENTORY, "
              "ROUTING, CONFIG, LOGGING, IMPORT_GROUP, SERVICE_REQUEST, SERVICE_PROVIDE")
    write_cfg(f"{u}/scmaster.cfg", hdr, [
        ("interface.bind", f"{BIND_IP}:{SCMASTER_PORT}",
         "network rule: loopback only, non-default port (default 0.0.0.0:18180 would listen on every interface)"),
        ("interface.acl", BIND_IP, "only local clients"),
        ("interface.ssl.bind", f"{BIND_IP}:-1", "SSL listener disabled (port -1), and loopback even if it were not"),
        ("queues", "production", "one queue; the default second queue 'playback' is not needed"),
        ("defaultGroups", groups, "default groups + RELOCATION (scrtdd's output group, singleevent.rst)"),
        ("queues.production.groups", groups,
         "RELOCATION is not a default group; scrtdd sends there and scevent listens there (loop protection)"),
        ("queues.production.acl", BIND_IP, "only local clients may join the queue"),
        ("queues.production.plugins", "dbstore", "store every message in the database"),
        ("queues.production.processors.messages", "dbstore", ""),
        ("queues.production.processors.messages.dbstore.driver", "sqlite3", "dbmysql is not built"),
        ("queues.production.processors.messages.dbstore.read", db,
         "clients get sqlite3://<this path> as their (read) database"),
        ("queues.production.processors.messages.dbstore.write", db, ""),
        ("queues.production.processors.messages.dbstore.strictVersionMatch", "true",
         "schema made from this build's share/db/sqlite3.sql"),
    ])
    # scautopick: the best model's configuration of step 09, unchanged
    dl = open(DL_CFG).read()
    with open(f"{u}/scautopick.cfg", "w") as f:
        f.write(f"# {hdr.splitlines()[0]}\n# scautopick.cfg = {DL_CFG} copied UNCHANGED (best model of step 09,\n"
                f"# phasenet_original). Bindings (detecStream per station) come from the database: {BINDINGS_XML}\n"
                f"# imported with scdb. In step 09 the same file was given with --config-file; here it is the normal\n"
                f"# module configuration, so etc/defaults/scautopick.cfg is read first (the file repeats those defaults).\n"
                f"# ---------------------------------------------------------------------------------------------\n" + dl)
    write_cfg(f"{u}/scautoloc.cfg", hdr, [
        ("autoloc.grid", f"{run}/config/scautoloc_grid.conf",
         "local nucleation grid around 35.0 N 127.73 E, depths 5-25 km (see the file header)"),
        ("autoloc.stationConfig", f"{run}/config/scautoloc_station.conf", "the 54 KS stations, nucleation <= 1.0 deg"),
        ("autoloc.minPhaseCount", str(AUTOLOC["min_phase_count"]),
         "reporting threshold for ~40-50 stations per event (default 6)"),
        ("autoloc.maxStationDistance", "1.5", "local network: all stations are within 1 degree (default 180)"),
        ("autoloc.maxRMS", "1.0", "local network (default 3.5 s is meant for teleseismic use)"),
        ("autoloc.maxResidual", "1.5",
         "local network (default 7 s). The smallest S-P time here is about 1.9 s (nearest station 7 km, depth\n"
         "~14 km), so an S wave picked as P cannot be used as P; LOCSAT iasp91 P residuals are a few 0.1 s."),
        ("autoloc.minPickSNR", "0",
         "the DL picker writes its model confidence (0-1, not a signal-to-noise ratio) into the 'snr' amplitude\n"
         "(scdlrtpicker README 'What ends up on the pick'); scautoloc's default minimum of 3 would reject every\n"
         "pick. The confidence threshold is already applied by the picker (minConfidence P 0.4, S 0.3)."),
        ("autoloc.dynamicPickThresholdInterval", "0",
         "0 switches off the 'dynamic pick threshold' (autoloc.cpp _tooManyRecentPicks: 'if timeSpan <= 0 return\n"
         "false'). Run RT1_filefeed (default 3600 s) proved it rejects EVERY DL pick: the new pick is already in the\n"
         "pick pool, so it is compared with itself (dt = 0); the old pick's SNR is clamped to at least 3, giving a\n"
         "threshold of 3, while the DL 'snr' (confidence) is at most 1 -> 55 of 56 P picks logged 'XX pick SNR\n"
         "0.75 < 3.00' and no origin was made. The check guards against bursts of noise picks at one station; it\n"
         "assumes STA/LTA ratios and cannot work with 0-1 confidences."),
        ("autoloc.pickLogEnable", "true", "log every pick scautoloc processes (diagnostics)"),
        ("autoloc.pickLog", f"{run}/logs/scautoloc_picklog", ""),
    ])
    sev = [
        ("connection.subscriptions", "LOCATION, RELOCATION, MAGNITUDE, FOCMECH, EVENT",
         "default + RELOCATION: scrtdd's origins arrive there (singleevent.rst 'Avoiding Relocation Loops')"),
        ("eventAssociation.minimumDefiningPhases", str(AUTOLOC["min_phase_count"]),
         "same threshold as scautoloc's minPhaseCount (default 10), so every reported origin can form an event"),
    ]
    if prefer_rtdd:   # run variant: make scrtdd's origin preferred, so that the loop protection is exercised
        sev += [
            ("eventAssociation.priorities", "AUTHOR, STATUS, PHASES_AUTOMATIC, TIME_AUTOMATIC",
             "VARIANT --prefer-rtdd: AUTHOR first (default AGENCY, STATUS, PHASES_AUTOMATIC, TIME_AUTOMATIC). With the\n"
             "default list the RTDD origin never became preferred in run RT2 ('phaseCount too low': it uses one P\n"
             "arrival less), so scrtdd never met its own origin and acceptedOriginAuthors was never tested."),
            ("eventAssociation.authors", f"scrtdd@{HOSTNAME}, scautoloc@{HOSTNAME}",
             "first = highest priority (scevent util.cpp:596-605)"),
        ]
    write_cfg(f"{u}/scevent.cfg", hdr, sev)
    # scrtdd: the step-08 template (= run S1's profile), with the run-specific changes below
    tpl = parse_simple_cfg(f"{TEMPLATE_DIR}/scrtdd.cfg")
    override = {
        "acceptedOriginAuthors": (f"scautoloc@{HOSTNAME}",
                                  "loop protection 1: relocate only scautoloc's origins (author = module@host). scrtdd\n"
                                  "has no other guard: with onlyPreferredOrigins it would relocate its own origin again\n"
                                  "if scevent made it preferred (rtddtool.cpp:1566-1700)."),
        "connection.primaryGroup": ("RELOCATION", "loop protection 2: scrtdd sends to RELOCATION, not LOCATION"),
        "performance.cacheDirectory": (f"{run}/rtdd_cache", "inside the run folder"),
        f"profile.gwangyang.catalog.eventFile": (f"{run}/reference_catalog/event.csv",
                                                 "S1 multi-event positions WITHOUT the replayed events (ids + 100)"),
        f"profile.gwangyang.catalog.phaFile": (f"{run}/reference_catalog/phase.csv", ""),
        f"profile.gwangyang.catalog.stationFile": (f"{run}/reference_catalog/station.csv", ""),
    }
    items = [
        ("plugins", "tttnll", "NonLinLoc grid travel times (template had these 4 lines in global.cfg; only scrtdd\n"
                              "needs them, so they are module settings here)"),
        ("ttt.NLLGrid.tables", "kim1983", ""),
        ("ttt.NLLGrid.kim1983.tablePath", NLL_TABLEPATH, ""),
        ("ttt.NLLGrid.kim1983.maxSearchDistance", "0.1", "metres, as in steps 07/08"),
    ]
    seen = set()
    for k, v in tpl:
        if k in override:
            nv, why = override[k]
            tag = "KEPT (same as template)" if nv == v else f"CHANGED from template value '{v}'"
            items.append((k, nv, f"{tag}: {why}" if why else tag))
        else:
            items.append((k, v, ""))
        seen.add(k)
    missing = [k for k in override if k not in seen]
    if missing:
        raise RuntimeError(f"template lacks keys {missing}")
    write_cfg(f"{u}/scrtdd.cfg", hdr + f"\nscrtdd.cfg = {TEMPLATE_DIR}/scrtdd.cfg (run S1 profile) with the CHANGED lines.", items)
    log(f"  wrote {u}/{{global,scmaster,scautopick,scautoloc,scevent,scrtdd}}.cfg")


# ----------------------------------------------------------------------------- option dumps
MODULES_ALL = ["scmaster", "scautopick", "scautoloc", "scevent", "scrtdd"]
DESCRIPTIONS = {   # description files whose parameters a module reads (module file first)
    "scmaster": ["scmaster.xml"],
    "scautopick": ["scautopick.xml", "global_dlrtpicker.xml", "global_mlv.xml", "global_mb.xml"],
    "scautoloc": ["scautoloc.xml", "global_locsat.xml"],
    "scevent": ["scevent.xml"],
    "scrtdd": ["scrtdd.xml", "global_nllttt.xml"],
}


def config_stack(run, module):
    import seiscomp.config as scconfig
    root = os.environ["SEISCOMP_ROOT"]
    files = [f"{root}/etc/defaults/global.cfg", f"{root}/etc/defaults/{module}.cfg", f"{root}/etc/global.cfg",
             f"{root}/etc/{module}.cfg", f"{run}/seiscomp_user/global.cfg", f"{run}/seiscomp_user/{module}.cfg"]
    cfg = scconfig.Config()
    used = []
    for f in files:
        if os.path.exists(f):
            if not cfg.readConfig(f):
                raise RuntimeError(f"cannot parse {f}")
            used.append(dict(file=f, md5=md5(f)))
    return cfg, used


def described_parameters(module):
    """name -> documented default (None if the description gives none) from the module's description files."""
    import xml.etree.ElementTree as ET
    root = os.environ["SEISCOMP_ROOT"]
    out = {}
    for fname in DESCRIPTIONS[module] + ["global.xml"]:
        p = f"{root}/etc/descriptions/{fname}"
        if not os.path.exists(p):
            continue
        tree = ET.parse(p)

        def walk(node, prefix):
            for ch in node:
                tag = ch.tag
                if tag in ("module", "plugin", "configuration", "binding", "extends"):
                    walk(ch, prefix)
                elif tag == "group":
                    walk(ch, prefix + ch.get("name") + ".")
                elif tag == "struct":
                    walk(ch, prefix + "$" + (ch.get("type") or "struct") + ".")
                elif tag == "parameter":
                    out.setdefault(prefix + ch.get("name"), dict(default=ch.get("default"), unit=ch.get("unit"),
                                                                 type=ch.get("type"), described_in=fname))
        for top in tree.getroot():
            if top.tag == "module" and fname.startswith(module):
                walk(top, "")
            elif top.tag == "plugin":
                walk(top, "")
            elif top.tag == "module" and fname == "global.xml":
                walk(top, "")
            elif top.tag == "binding" and module == "scautopick":
                walk(top, "binding:")
    return out


def static_option_dumps(run, db, log):
    """<run>/options/<module>.config.json: every key set in the stack (value, file:line) + unset documented defaults."""
    for m in MODULES_ALL:
        cfg, used = config_stack(run, m)
        st = cfg.symbolTable()
        setv = {}
        for name in cfg.names():
            sym = st.get(name)
            setv[name] = dict(values=[str(v) for v in sym.values], source=f"{sym.uri}:{sym.line}")
        desc = described_parameters(m)
        unset = {k: v for k, v in desc.items() if k not in setv and "$" not in k}
        dump_json(f"{run}/options/{m}.config.json",
                  dict(module=m, generated=now_iso(), files_read_in_order=used, n_set=len(setv), set=setv,
                       n_documented_unset=len(unset), documented_defaults_of_unset_parameters=unset,
                       note="values as the SeisComP configuration parser reads them; a module may still apply its "
                            "own built-in default where the description gives none (runtime dumps in this folder)"))
        log(f"  options/{m}.config.json: {len(setv)} keys set, {len(unset)} documented parameters left at default")
    # scautopick: its own resolution of module config + per-stream bindings (from the database), and app settings
    for flag, name in (("--dump-config", "scautopick.dump-config.txt"), ("--dump-settings", "scautopick.dump-settings.txt")):
        sh(["scautopick", "--offline", "--playback", "-d", f"sqlite3://{db}", flag], log, run, timeout=120,
           stdout_path=f"{run}/options/{name}")
    for m in ("scautoloc", "scevent", "scrtdd", "scmaster"):
        sh([m, "--dump-settings", "-d", f"sqlite3://{db}"] if m != "scmaster" else [m, "--dump-settings"],
           log, run, timeout=120, stdout_path=f"{run}/options/{m}.dump-settings.txt")


# ----------------------------------------------------------------------------- stage: start
def load_pids(run):
    p = f"{run}/pids.json"
    return json.load(open(p)) if os.path.exists(p) else {}


def save_pids(run, pids):
    dump_json(f"{run}/pids.json", pids)


def module_argv(run, m):
    log_file = f"{run}/logs/{m}.log"
    base = ["nice", "-n", str(NICE), m, "--log-file", log_file]
    if m == "scmaster":
        return base + ["--verbosity=3"]
    if m == "scevent":
        return base + ["--verbosity=4", "-H", HOSTURL]
    if m == "scautoloc":
        # --playback: autoloc's clock follows the picks (autoloc.cpp:640-658). Without it every pick older than
        # buffer.pickKeep (6 h) is ignored (autoloc.cpp _store) - i.e. all historic picks.
        # --timing: 'pickTime' (default) = clock is the latest pick TIME; 'creationTime' = the latest pick/amplitude
        # CREATION time (= wall clock here), which keeps origin-update intervals in real time (run RT3 showed that
        # with pickTime a pending update waits until a later pick arrives).
        timing = "pickTime"
        vf = f"{run}/run_variant.json"
        if os.path.exists(vf):
            timing = json.load(open(vf)).get("autoloc_timing", "pickTime")
        return base + ["--verbosity=4", "-H", HOSTURL, "--playback", "--timing", timing]
    if m == "scrtdd":
        # --dump-diagnostics: per relocation a folder with the double-difference tables (cwd = work/scrtdd)
        return base + ["--verbosity=4", "-H", HOSTURL, "--dump-diagnostics"]
    raise ValueError(m)


def stage_start(a, log):
    run = run_dir(a.run)
    if not os.path.exists(f"{run}/db/seiscomp.sqlite"):
        sys.exit("run 'prepare --apply' first")
    pids = load_pids(run)
    running = {m: d for m, d in pids.items() if d.get("pid") and alive(d["pid"]) and proc_comm(d["pid"]) == m}
    if running:
        sys.exit(f"modules of this run are still running: {running}; use 'stop' first")
    pre = listening(port=SCMASTER_PORT)
    other = {name: subprocess.run(["pgrep", "-x", "-u", str(os.getuid()), name], capture_output=True, text=True).stdout.split()
             for name in MODULE_ORDER + ["scautopick", "seedlink", "msrtsimul"]}
    log(f"  before start: sockets on port {SCMASTER_PORT}: {pre or 'none'}; processes of this user with module "
        f"names: {other}")
    with open(f"{run}/network/before_start.txt", "w") as f:
        f.write(f"# {now_iso()} ss -ltnp/-lunp, port {SCMASTER_PORT}\n" + "\n".join(pre) + "\n")
        f.write(f"# pgrep -x -u {os.getuid()} <name>: {json.dumps(other)}\n")
        f.write("# full ss -ltnp (all users; process column only for our own processes)\n")
        f.write(subprocess.run(["ss", "-ltnp"], capture_output=True, text=True).stdout)
    if pre:
        sys.exit(f"port {SCMASTER_PORT} is in use: {pre}")
    if any(other[n] for n in MODULE_ORDER):
        sys.exit(f"other processes with module names exist for this user: {other} (not ours to touch)")
    if not a.apply:
        for m in MODULE_ORDER:
            log("  would start:", " ".join(module_argv(run, m)), f"(cwd {run}/work/{m})")
        return
    pids = {}
    for m in MODULE_ORDER:
        argv = module_argv(run, m)
        out = open(f"{run}/logs/{m}.stdout", "ab")
        t0 = now_iso()
        p = subprocess.Popen(argv, cwd=f"{run}/work/{m}", env=sc_env(run), stdout=out, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        out.close()
        pids[m] = dict(pid=p.pid, argv=argv, cwd=f"{run}/work/{m}", started=t0)
        save_pids(run, pids)
        log(f"  started {m}: pid {p.pid}: {' '.join(argv)}")
        if m == "scmaster":
            ok = False
            for _ in range(60):   # up to 30 s for the listening socket
                time.sleep(0.5)
                rows = listening(pids=[p.pid])
                if any(f"{BIND_IP}:{SCMASTER_PORT}" in r for r in rows):
                    ok = True
                    break
                if p.poll() is not None:
                    break
            log(f"    scmaster listening: {rows}")
            if not ok:
                log("    scmaster did not come up; stopping")
                stop_all(run, log)
                sys.exit(1)
        else:
            time.sleep(3)
            if p.poll() is not None:
                log(f"    {m} exited with {p.returncode} right after start; stopping everything")
                stop_all(run, log)
                sys.exit(1)
    time.sleep(5)
    check_network(run, log, "after_start")
    for m in MODULE_ORDER:
        txt = open(f"{run}/logs/{m}.log", errors="replace").read() if os.path.exists(f"{run}/logs/{m}.log") else ""
        conn = [l.strip() for l in txt.splitlines() if re.search(r"onnect", l)][:3]
        errs = [l.strip() for l in txt.splitlines() if "[error]" in l.lower() or " error " in l.lower()][:5]
        log(f"  {m}: alive={alive(pids[m]['pid'])}; connection lines: {conn}; error lines: {errs}")


def check_network(run, log, tag):
    pids = load_pids(run)
    ours = [d["pid"] for d in pids.values() if d.get("pid") and alive(d["pid"])]
    rows = listening(pids=ours)
    port_rows = listening(port=SCMASTER_PORT)
    bad = [r for r in rows if f"{BIND_IP}:{SCMASTER_PORT} " not in r + " " or not r.startswith("tcp")]
    with open(f"{run}/network/{tag}.txt", "w") as f:
        f.write(f"# {now_iso()} listening sockets of our PIDs {ours} (ss -ltnp/-lunp)\n" + "\n".join(rows) + "\n")
        f.write(f"# everything on port {SCMASTER_PORT}\n" + "\n".join(port_rows) + "\n")
        f.write(f"# sockets other than {BIND_IP}:{SCMASTER_PORT}/tcp: {bad}\n")
    log(f"  network check '{tag}': our listening sockets {rows}; unexpected: {bad or 'none'}")
    if bad:
        log("  UNEXPECTED LISTENING SOCKET -> stopping everything (network rule)")
        stop_all(run, log)
        sys.exit(2)


# ----------------------------------------------------------------------------- stage: replay
def count_reloc_lines(path):
    if not os.path.exists(path):
        return 0
    txt = open(path, errors="replace").read()
    return len(re.findall(r"has been relocated|Cannot relocate origin", txt))


def stage_replay(a, log):
    run = run_dir(a.run)
    ev = a.event
    if ev not in REPLAY_EVENTS:
        sys.exit(f"--event must be one of {list(REPLAY_EVENTS)}")
    data = f"{run}/data/{ev}_sorted.mseed"
    pids = load_pids(run)
    dead = [m for m in MODULE_ORDER if not (m in pids and alive(pids[m]["pid"]))]
    log_pick = f"{run}/logs/scautopick_{ev}_{a.feed}.log"
    pick_argv = ["scautopick", "-H", HOSTURL, "--playback", "--verbosity=4", "--log-file", log_pick]
    if a.feed == "file":
        pick_argv += ["-I", f"file://{data}"]
        feed_argv = None
    else:
        pick_argv += ["-I", "file://-"]
        feed_argv = ["nice", "-n", str(NICE), "msrtsimul", "-c", "-m", "historic", "-s", str(PACE_SPEED), "-v", data]
    # /usr/bin/time -v measures scautopick's own CPU time and peak memory (the PID we hold is the timeout wrapper)
    time_file = f"{run}/logs/scautopick_{ev}_{a.feed}.time.txt"
    full_pick = (["nice", "-n", str(NICE), "/usr/bin/timeout", str(REPLAY_TIMEOUT_S), "/usr/bin/time", "-v", "-o",
                  time_file] + pick_argv)
    log(f"  replay {ev} (rtdd id {REPLAY_EVENTS[ev]}) feed={a.feed}")
    if feed_argv:
        log("  $", " ".join(feed_argv), "|", " ".join(full_pick))
    else:
        log("  $", " ".join(full_pick))
    if not a.apply:
        return
    if dead:
        sys.exit(f"modules not running: {dead}; run 'start --apply' first")
    rtdd_log = f"{run}/logs/scrtdd.log"
    n0 = count_reloc_lines(rtdd_log)
    rec = dict(event=ev, feed=a.feed, data=data, data_md5=md5(data), pick_argv=full_pick, feed_argv=feed_argv,
               wall_start=now_iso())
    t0 = time.time()
    so = open(f"{run}/logs/scautopick_{ev}_{a.feed}.stdout", "wb")
    if feed_argv:
        fe = open(f"{run}/logs/msrtsimul_{ev}.stderr", "wb")
        pf = subprocess.Popen(feed_argv, cwd=f"{run}/work/scautopick", env=sc_env(run), stdout=subprocess.PIPE,
                              stderr=fe, start_new_session=True)
        pids[f"msrtsimul_{ev}"] = dict(pid=pf.pid, argv=feed_argv, started=now_iso())
        pp = subprocess.Popen(full_pick, cwd=f"{run}/work/scautopick", env=sc_env(run), stdin=pf.stdout, stdout=so,
                              stderr=subprocess.STDOUT, start_new_session=True)
        pf.stdout.close()
    else:
        pf = None
        pp = subprocess.Popen(full_pick, cwd=f"{run}/work/scautopick", env=sc_env(run), stdin=subprocess.DEVNULL,
                              stdout=so, stderr=subprocess.STDOUT, start_new_session=True)
    pids[f"scautopick_{ev}"] = dict(pid=pp.pid, argv=full_pick, started=now_iso())
    save_pids(run, pids)
    rc = pp.wait()
    if pf is not None:
        pf.wait(timeout=60)
    so.close()
    rec.update(scautopick_exit=rc, scautopick_wall_s=round(time.time() - t0, 2), scautopick_time_file=time_file,
               msrtsimul_exit=(pf.returncode if pf is not None else None), wall_scautopick_end=now_iso())
    log(f"  scautopick exit {rc} after {time.time() - t0:.1f} s" + (f"; msrtsimul exit {pf.returncode}" if pf else ""))
    # wait for scrtdd's result (scautoloc -> scevent -> delayTime 10 s -> two-step relocation)
    t1 = time.time()
    got = False
    while time.time() - t1 < WAIT_RELOC_S:
        if count_reloc_lines(rtdd_log) > n0:
            got = True
            break
        time.sleep(2)
    rec["relocation_logged_after_s"] = round(time.time() - t1, 1) if got else None
    log(f"  scrtdd result line {'seen' if got else 'NOT seen'} {time.time() - t1:.1f} s after scautopick ended")
    time.sleep(GRACE_S)   # let scevent take the relocated origin and scrtdd react to the event update (loop check)
    rec["wall_end"] = now_iso()
    rec["alive_after"] = {m: alive(pids[m]["pid"]) for m in MODULE_ORDER}
    rec["db_counts_after"] = db_counts(f"{run}/db/seiscomp.sqlite")
    log(f"  modules alive: {rec['alive_after']}; database rows: {rec['db_counts_after']}")
    reps = json.load(open(f"{run}/replays.json")) if os.path.exists(f"{run}/replays.json") else []
    reps.append(rec)
    dump_json(f"{run}/replays.json", reps)
    check_network(run, log, f"after_replay_{ev}")


# ----------------------------------------------------------------------------- stage: stop
def stop_all(run, log):
    pids = load_pids(run)
    final = {}
    for m in list(reversed(MODULE_ORDER)) + [k for k in pids if k not in MODULE_ORDER]:
        d = pids.get(m)
        if not d or not d.get("pid"):
            continue
        pid = d["pid"]
        if not alive(pid):
            final[m] = dict(pid=pid, state="already gone")
            continue
        comm = proc_comm(pid)
        expect = m.split("_")[0]
        try:   # msrtsimul is a Python script: its comm is 'python3.x', so also accept a matching command line
            cmdline = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            cmdline = ""
        if comm not in (expect, "nice", "timeout") and f"/{expect} " not in cmdline:
            final[m] = dict(pid=pid, state=f"NOT TOUCHED: /proc/{pid}/comm is '{comm}', not ours")
            log(f"  {m}: pid {pid} is now '{comm}' -> not touched")
            continue
        cpu, hwm = proc_cpu(pid)
        os.kill(pid, signal.SIGTERM)
        t0 = time.time()
        while alive(pid) and time.time() - t0 < 20:
            time.sleep(0.2)
        state = "terminated (SIGTERM)"
        if alive(pid):
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
            state = "killed (SIGKILL after 20 s)"
        final[m] = dict(pid=pid, state=state, cpu_s=cpu, vmhwm_kB=hwm, stop_s=round(time.time() - t0, 2))
        log(f"  {m}: pid {pid} {state} after {time.time() - t0:.1f} s; CPU {cpu} s, peak RSS {hwm} kB")
    return final


def stage_stop(a, log):
    run = run_dir(a.run)
    pids = load_pids(run)
    log(f"  processes of this run: { {m: d['pid'] for m, d in pids.items()} }")
    if not a.apply:
        return
    final = stop_all(run, log)
    time.sleep(1)
    gone = {m: (not alive(d["pid"])) for m, d in pids.items()}
    pg = {name: subprocess.run(["pgrep", "-x", "-u", str(os.getuid()), name], capture_output=True, text=True).stdout.split()
          for name in MODULE_ORDER + ["scautopick", "msrtsimul", "seedlink"]}
    port_rows = listening(port=SCMASTER_PORT)
    our_rows = listening(pids=[d["pid"] for d in pids.values()])
    home_sc = os.path.exists(os.path.expanduser("~msseo/.seiscomp"))
    proof = dict(time=now_iso(), stop=final, pid_gone=gone, pgrep_x_this_user=pg, ss_port=port_rows,
                 ss_our_pids=our_rows, user_dot_seiscomp_exists=home_sc)
    dump_json(f"{run}/network/after_stop.json", proof)
    with open(f"{run}/network/after_stop.txt", "w") as f:
        f.write(f"# {now_iso()} after stop\n# ss -ltnp/-lunp port {SCMASTER_PORT}: {port_rows}\n"
                f"# ss rows of our former PIDs: {our_rows}\n# pgrep -x -u {os.getuid()}: {json.dumps(pg)}\n"
                f"# /proc/<pid> gone: {json.dumps(gone)}\n# ~/.seiscomp exists: {home_sc}\n")
        f.write(subprocess.run(["ss", "-ltnp"], capture_output=True, text=True).stdout)
    log(f"  after stop: all PIDs gone {all(gone.values())}; pgrep -x {pg}; port {SCMASTER_PORT}: {port_rows or 'free'}; "
        f"~/.seiscomp exists: {home_sc}")


# ----------------------------------------------------------------------------- stage: dump
def stage_dump(a, log):
    run = run_dir(a.run)
    db = f"{run}/db/seiscomp.sqlite"
    pids = load_pids(run)
    still = [m for m, d in pids.items() if alive(d["pid"])]
    if still:
        log(f"  note: still running: {still} (dump reads the database anyway; WAL mode)")
    dbu = f"sqlite3://{db}"
    out = f"{run}/db_dump"
    if not a.apply:
        log(f"  would run scevtls/scxmldump on {dbu} into {out}")
        return
    common = ["--core.plugins=dbsqlite3", "-d", dbu]
    rc, txt = sh(["scevtls"] + common + ["--begin", "2021-01-01 00:00:00", "--end", "2027-01-01 00:00:00", "-p", "-c"],
                 log, run, timeout=120)
    open(f"{out}/scevtls.txt", "w").write(txt)
    events = [l.split()[0] for l in txt.splitlines() if l.strip()]
    log(f"  scevtls: {len(events)} events: {txt.strip()}")
    for e in events:
        sh(["scxmldump"] + common + ["-E", e, "-P", "-A", "-f", "-o", f"{out}/event_{e.replace('/', '_')}.xml"],
           log, run, timeout=120)
    # every pick and amplitude, associated or not (the S picks are not in any scautoloc origin)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    pick_ids = [r[0] for r in con.execute("SELECT po.publicID FROM Pick p JOIN PublicObject po ON po._oid = p._oid")]
    con.close()
    with open(f"{out}/pick_ids.txt", "w") as f:
        f.write("\n".join(pick_ids) + "\n")
    with open(f"{out}/pick_ids.txt") as fin:
        sh(["scxmldump"] + common + ["--pick", "-", "-f", "-o", f"{out}/picks_all.xml"], log, run, timeout=300, stdin=fin)
    sql_tables(db, out, log)


SQL = {
    "picks": """SELECT po.publicID, p.time_value, p.time_value_ms, p.waveformID_networkCode, p.waveformID_stationCode,
                p.waveformID_locationCode, p.waveformID_channelCode, p.methodID, p.phaseHint_code, p.evaluationMode,
                p.creationInfo_author, p.creationInfo_creationTime, p.creationInfo_creationTime_ms, o._timestamp
                FROM Pick p JOIN PublicObject po ON po._oid = p._oid JOIN Object o ON o._oid = p._oid""",
    "amplitudes": """SELECT po.publicID, a.type, a.amplitude_value, a.snr, a.pickID, a.waveformID_stationCode,
                a.waveformID_channelCode, a.creationInfo_author, a.creationInfo_creationTime, a.creationInfo_creationTime_ms
                FROM Amplitude a JOIN PublicObject po ON po._oid = a._oid""",
    "origins": """SELECT po.publicID, o.time_value, o.time_value_ms, o.latitude_value, o.longitude_value, o.depth_value,
                o.depthType, o.methodID, o.earthModelID, o.evaluationMode, o.quality_associatedPhaseCount,
                o.quality_usedPhaseCount, o.quality_usedStationCount, o.quality_standardError, o.quality_azimuthalGap,
                o.quality_minimumDistance, o.quality_maximumDistance, o.creationInfo_author, o.creationInfo_agencyID,
                o.creationInfo_creationTime, o.creationInfo_creationTime_ms, ob._timestamp
                FROM Origin o JOIN PublicObject po ON po._oid = o._oid JOIN Object ob ON ob._oid = o._oid""",
    "arrivals": """SELECT po.publicID AS originID, a.pickID, a.phase_code, a.distance, a.azimuth, a.timeResidual,
                a.timeUsed, a.weight FROM Arrival a JOIN PublicObject po ON po._oid = a._parent_oid""",
    "events": """SELECT po.publicID, e.preferredOriginID, e.type, e.creationInfo_author, e.creationInfo_creationTime,
                e.creationInfo_creationTime_ms, e.creationInfo_modificationTime, e.creationInfo_modificationTime_ms
                FROM Event e JOIN PublicObject po ON po._oid = e._oid""",
    "origin_references": """SELECT po.publicID AS eventID, r.originID, ob._timestamp FROM OriginReference r
                JOIN PublicObject po ON po._oid = r._parent_oid JOIN Object ob ON ob._oid = r._oid""",
}


def sql_tables(db, out, log):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    for name, q in SQL.items():
        cur = con.execute(q)
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        with open(f"{out}/sql_{name}.csv", "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(cols)
            w.writerows(rows)
        log(f"  sql_{name}.csv: {len(rows)} rows")
    con.close()
    dump_json(f"{out}/db_counts.json", db_counts(db))


# ----------------------------------------------------------------------------- stage: status
def stage_status(a, log):
    run = run_dir(a.run)
    pids = load_pids(run)
    for m, d in pids.items():
        log(f"  {m}: pid {d['pid']} alive={alive(d['pid'])} comm={proc_comm(d['pid'])}")
    log(f"  listening sockets of these PIDs: {listening(pids=[d['pid'] for d in pids.values()])}")
    log(f"  port {SCMASTER_PORT}: {listening(port=SCMASTER_PORT)}")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=["prepare", "start", "replay", "stop", "dump", "status", "options"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--event", default=None)
    ap.add_argument("--feed", choices=["file", "paced"], default="file")
    ap.add_argument("--autoloc-timing", choices=["pickTime", "creationTime"], default="pickTime",
                    help="prepare only: scautoloc playback clock (--timing)")
    ap.add_argument("--prefer-rtdd", action="store_true",
                    help="prepare only: scevent prefers scrtdd's origins (tests the relocation-loop protection)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    log = Tee(f"{LOGDIR}/10_gwangyang_realtime_{a.run}_{a.stage}_{'apply' if a.apply else 'dryrun'}_{stamp}.log")
    log(f"# rt_chain.py {a.stage} --run {a.run} {'APPLY' if a.apply else 'DRY RUN'} {now_iso()} host {HOSTNAME}")
    log(f"# SEISCOMP_ROOT={os.environ.get('SEISCOMP_ROOT')}; run folder {run_dir(a.run)}")
    if os.path.exists(os.path.expanduser("~msseo/.seiscomp")):
        sys.exit("~/.seiscomp exists: refusing to run (it must not exist)")
    if a.apply and a.stage != "status":
        if a.stage == "prepare" or os.path.isdir(run_dir(a.run)):
            record_provenance(run_dir(a.run), a.stage, log)
        else:
            log(f"# provenance not recorded: {run_dir(a.run)} does not exist (run 'prepare --apply' first)")
    else:
        log(f"# script md5 (as loaded) {SCRIPT_MD5}; dry run or status: nothing recorded")
    if a.stage == "prepare":
        stage_prepare(a, log)
    elif a.stage == "start":
        stage_start(a, log)
    elif a.stage == "replay":
        stage_replay(a, log)
    elif a.stage == "stop":
        stage_stop(a, log)
    elif a.stage == "dump":
        stage_dump(a, log)
    elif a.stage == "status":
        stage_status(a, log)
    elif a.stage == "options":
        if a.apply:
            static_option_dumps(run_dir(a.run), f"{run_dir(a.run)}/db/seiscomp.sqlite", log)
    log(f"# done {now_iso()}; log {log.path}")


if __name__ == "__main__":
    main()
