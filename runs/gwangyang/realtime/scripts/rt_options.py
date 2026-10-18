#!/usr/bin/env python
# rt_options.py -- step 10: one JSON per real-time run with every option value used (project rule 5).
#
# Usage (after 'source install/env_seiscomp.sh'; dry run by default):
#     python rt_options.py --run RT2_filefeed            # lists what it would collect
#     python rt_options.py --run RT2_filefeed --apply    # writes <run>/options/run_options.json
#
# Collected, per run:
#   * config_stack_per_module : <run>/options/<module>.config.json written by 'rt_chain.py prepare' (every key set in
#                               defaults/global.cfg, defaults/<m>.cfg, etc/global.cfg, etc/<m>.cfg, the run's global.cfg
#                               and <m>.cfg, with file:line; plus the documented defaults of every unset parameter);
#   * scrtdd_resolved         : step 08's resolver (runs/gwangyang/scrtdd/scripts/scrtdd_common.py resolve_options, used
#                               read-only) applied to this run's configuration: the values scrtdd uses where a key is
#                               unset (its built-in defaults, rtddtool.cpp line numbers) and the libhdd structures;
#   * scrtdd_vs_S1            : every profile / libhdd value that differs from run S1's run_options.json;
#   * scautoloc_runtime       : the 'Configuration:' block scautoloc printed at start-up (its resolved values);
#   * scautopick_dump_config  : scautopick --dump-config (module values + the stream setup read from the database);
#   * command_lines           : argv of every process (pids.json) and of every replay (replays.json).
#   (added 2026-10-17, after the independent verification:)
#   * scautoloc_timing_argument : the '--timing' value on scautoloc's command line (pids.json), or that none was given
#                               (then scautoloc uses its default pickTime, scautoloc/app.h:82);
#   * script_provenance       : the entries of <run>/options/script_provenance.json (written by every --apply stage of
#                               rt_chain.py and rt_offline_check.py), or an explicit 'not recorded' statement;
#   * driver_scripts_on_disk_when_run_options_written : md5 and modification time (KST) of rt_chain.py,
#                               rt_options.py, rt_offline_check.py and rt_analyze.py when this file is written.
# This script itself does not append to script_provenance.json; its own md5 is in the last item above.

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
RTROOT = f"{PROJECT}/runs/gwangyang/realtime"
SCRTDD_SCRIPTS = f"{PROJECT}/runs/gwangyang/scrtdd/scripts"
S1_OPTIONS = f"{PROJECT}/runs/gwangyang/scrtdd/S1/run_options.json"
MODULES = ["scmaster", "scautopick", "scautoloc", "scevent", "scrtdd"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_SCRIPTS = ["rt_chain.py", "rt_options.py", "rt_offline_check.py", "rt_analyze.py"]
KST = datetime.timezone(datetime.timedelta(hours=9))
# Runs made before provenance recording existed (2026-10-17). What is known about their scripts comes from file
# modification times only (checked against the stage log names in logs/10_gwangyang_realtime_*).
PRE_PROVENANCE_RUNS = ["RT1_filefeed", "RT2_filefeed", "RT3_paced", "RT4_filefeed_prefer_rtdd", "RT5_paced_creationtime"]
PRE_PROVENANCE_NOTE = ("not recorded: run made before provenance recording; scripts edited later: rt_chain.py 18:27 KST "
                       "during RT5, rt_offline_check.py 18:37 KST after its last --apply at 18:36")
PRE_PROVENANCE_DETAILS = {
    "versions_on_disk_before_the_provenance_fix": {
        "rt_chain.py": dict(md5="7062425225c77eb99ca5309fa53d3ced", modified_kst="2026-10-17 18:27:10"),
        "rt_options.py": dict(md5="e9c0cf0193b6b09d78ea014d0b94f370", modified_kst="2026-10-17 18:04:48"),
        "rt_offline_check.py": dict(md5="fa320d50b01c43ee568423f854f98841", modified_kst="2026-10-17 18:37:31"),
        "rt_analyze.py": dict(md5="05fd10a758c01cac1c07c74dec0ad1ec", modified_kst="2026-10-17 18:34:34"),
    },
    "what_ran_which_version": [
        "rt_chain.py: every stage of RT1-RT4 and RT5's prepare, start and both replays started before 18:27:10 KST, so "
        "their version is not on disk; RT5's stop (18:36:07) and dump (18:36:09) ran the 18:27 version",
        "rt_offline_check.py: its --apply runs (RT2 18:01:53, RT5 18:36:29 KST) both started before 18:37:31, so "
        "neither version is on disk",
        "rt_options.py: run_options.json of RT1-RT4 (18:28:03) and RT5 (18:36:09) were written by the 18:04 version",
        "rt_analyze.py: the results tables of 18:36 KST were written by the 18:34 version",
    ],
}


def flat(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flat(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = d
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    run = f"{RTROOT}/{a.run}"
    print(f"# rt_options.py --run {a.run} {'APPLY' if a.apply else 'DRY RUN'}")
    if not a.apply:
        print(f"  would read {run}/options/*.config.json, {run}/logs/scautoloc.log, {run}/pids.json, "
              f"{run}/replays.json and resolve scrtdd options with {SCRTDD_SCRIPTS}/scrtdd_common.py")
        return
    sys.path.insert(0, SCRTDD_SCRIPTS)
    import scrtdd_common as C   # noqa: E402  (read-only use of step 08's resolver)
    doc = dict(run=a.run, generated=datetime.datetime.now(datetime.timezone.utc).isoformat())
    doc["config_stack_per_module"] = {m: json.load(open(f"{run}/options/{m}.config.json")) for m in MODULES}
    res = C.resolve_options(run)
    doc["scrtdd_resolved"] = res
    s1 = json.load(open(S1_OPTIONS))
    diffs = {}
    for part in ("profile_options", "module_options", "global_options", "libhdd_equivalent"):
        fa, fb = flat(res.get(part, {})), flat(s1.get(part, {}))
        for k in sorted(set(fa) | set(fb)):
            if k.endswith(".set_in"):
                continue
            if fa.get(k) != fb.get(k):
                diffs[f"{part}.{k}"] = dict(realtime=fa.get(k), S1=fb.get(k))
    doc["scrtdd_vs_S1"] = diffs
    txt = open(f"{run}/logs/scautoloc.log", errors="replace").read().splitlines()
    block, on = [], False
    for line in txt:
        body = re.sub(r"^\S+ \S+ \[[^\]]+\] ", "", line)
        if body.startswith("Configuration:"):
            on = True
            continue
        if on:
            if not body.startswith("  "):
                break
            block.append(body.rstrip())
    doc["scautoloc_runtime"] = block
    doc["scautopick_dump_config"] = open(f"{run}/options/scautopick.dump-config.txt", errors="replace").read().splitlines()
    doc["dump_settings_files"] = sorted(f for f in os.listdir(f"{run}/options") if f.endswith("dump-settings.txt"))
    doc["command_lines"] = dict(processes=json.load(open(f"{run}/pids.json")) if os.path.exists(f"{run}/pids.json") else {},
                                replays=json.load(open(f"{run}/replays.json")) if os.path.exists(f"{run}/replays.json") else [])
    argv = doc["command_lines"]["processes"].get("scautoloc", {}).get("argv", [])
    doc["scautoloc_timing_argument"] = (argv[argv.index("--timing") + 1] if "--timing" in argv[:-1] else
                                        "not given (scautoloc default pickTime, scautoloc/app.h:82)" if argv else
                                        "unknown (no scautoloc entry in pids.json)")
    prov = f"{run}/options/script_provenance.json"
    if os.path.exists(prov):
        doc["script_provenance"] = json.load(open(prov))
    elif a.run in PRE_PROVENANCE_RUNS:
        doc["script_provenance"] = PRE_PROVENANCE_NOTE
        doc["script_provenance_known_from_file_times"] = PRE_PROVENANCE_DETAILS
    else:
        doc["script_provenance"] = f"not recorded: {prov} does not exist"
    disk = {}
    for s in DRIVER_SCRIPTS:
        p = f"{SCRIPT_DIR}/{s}"
        if os.path.exists(p):
            disk[s] = dict(md5=hashlib.md5(open(p, "rb").read()).hexdigest(),
                           modified_kst=datetime.datetime.fromtimestamp(os.path.getmtime(p), KST).strftime("%Y-%m-%d %H:%M:%S"))
    doc["driver_scripts_on_disk_when_run_options_written"] = disk
    with open(f"{run}/options/run_options.json", "w") as f:
        json.dump(doc, f, indent=1, default=str)
    print(f"  wrote {run}/options/run_options.json; scrtdd values differing from S1: {len(diffs)}; scautoloc --timing: "
          f"{doc['scautoloc_timing_argument']}; script provenance: "
          f"{doc['script_provenance'] if isinstance(doc['script_provenance'], str) else str(len(doc['script_provenance'])) + ' entries'}")
    for k, v in diffs.items():
        print(f"    {k}: realtime={v['realtime']!r} S1={v['S1']!r}")


if __name__ == "__main__":
    main()
