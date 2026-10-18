#!/usr/bin/env python
# scrtdd_sanramon.py -- multi-event relocations of the 685 San Ramon 2015 events with the SeisComP module
# scrtdd (v2.0.10, SeisComP 7.4.0), mirroring the pyrtdd runs of runs/sanramon/pyrtdd/run_pyrtdd_sanramon.py.
#
# Usage (after 'source install/env_seiscomp.sh'; dry run by default):
#     python scrtdd_sanramon.py                    # show what would be written and run
#     python scrtdd_sanramon.py --apply --runs S0  # run S0
#
# Each run gets its own folder runs/sanramon/scrtdd/<RUN>/ with
#   seiscomp_user/{global.cfg,scrtdd.cfg}  private SeisComP configuration (SEISCOMP_LOCAL_CONFIG points here)
#   home/                                  HOME of the scrtdd process
#   work/                                  scrtdd's working folder: reloc-{event,phase,station}.csv, the
#                                          --dump-diagnostics folder multievent_*/, relocated.xml, scrtdd.log
#   run_options.json                       EVERY option value scrtdd used (set or default), command, versions,
#                                          input checksums
#   run_summary.json                       exit code, run time, peak memory, counts from the log
#   time_v.txt                             /usr/bin/time -v of the scrtdd process
#
# Runs:
#   S0   = pyrtdd P0: catalog differential times only; libhdd default clustering (ellipsoids) and default
#        solver (absoluteLocationConstraint 0.3), every value written explicitly (scrtdd's own profile
#        defaults differ, see scrtdd_common_sanramon.py)
#   S1   = pyrtdd P1: S0 + cross-correlation, default windows, P Z/1, S L2, BW(4,1.5,15) at 1000 Hz
#   S0n, S1n  nearest-neighbour clustering variants (= P0n, P1n), only if run explicitly
#   S0rep  check: identical repeat of S0 (run-to-run determinism, the noise floor for S0 vs P0)
#   S0nat  check: S0 with scrtdd's built-in NonLinLoc reader ('Native:NLLGrid') instead of the tttnll plugin
#
# Command (cwd = <run>/work; SEISCOMP_LOCAL_CONFIG = <run>/seiscomp_user; HOME = <run>/home):
#   nice -n 10 prlimit --as=60G /usr/bin/time -v -o ../time_v.txt /usr/bin/timeout 21600 \
#   scrtdd --reloc-catalog station.csv,event.csv,phase.csv --profile sanramon \
#          --inventory-db file://inputs/inventory_sc.xml -I sdsarchive://.../sds \
#          --dump-diagnostics --xmlout --verbosity=3 --console=1  > relocated.xml 2> scrtdd.log

import argparse
import glob
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrtdd_common_sanramon as C  # noqa: E402

# ----------------------------------------------------------------------------- parameters
BASE = {**C.COMMON, **C.CLUSTERING_RTDD_DEFAULT, **C.SOLVER_RTDD_DEFAULT}
# scrtdd's built-in NonLinLoc reader (same format as runs/gwangyang/scrtdd/scripts/scrtdd_multievent.py)
NATIVE_TABLEMODEL = f"{os.path.dirname(C.NLL_TABLEPATH)};{C.TABLE};0.1;noSwapBytes;512;KeepOpen"
RUNS = {
    "S0": dict(profile={**BASE, **C.XCORR_OFF},
               what="= P0: catalog dt only; libhdd default clustering (ellipsoids) + solver (absLoc 0.3)"),
    "S1": dict(profile={**BASE, **C.XCORR_P1},
               what="= P1: S0 + cross-correlation (default windows, P Z/1, S L2, BW(4,1.5,15), 1000 Hz)"),
    "S0rep": dict(profile={**BASE, **C.XCORR_OFF},
                  what="check: identical repeat of S0 (is scrtdd deterministic run to run?)"),
    "S0nat": dict(profile={**BASE, **C.XCORR_OFF, "tableType": "Native:NLLGrid", "tableModel": f'"{NATIVE_TABLEMODEL}"'},
                  what="check: S0 with scrtdd's built-in NonLinLoc reader instead of the tttnll plugin"),
    "S0n": dict(profile={**BASE, **C.CLUSTERING_NEAREST_NEIGHBOUR, **C.XCORR_OFF},
                what="= P0n: S0 with nearest-neighbour clustering"),
    "S1n": dict(profile={**BASE, **C.CLUSTERING_NEAREST_NEIGHBOUR, **C.XCORR_P1},
                what="= P1n: S1 with nearest-neighbour clustering (no xcorr re-use)"),
}
DEFAULT_RUNS = ["S0", "S1"]


def count_log(path):
    """A few numbers from the scrtdd console log (info level), to be checked against the CSV outputs
    (as in runs/gwangyang/scrtdd/scripts/scrtdd_multievent.py)."""
    txt = open(path, errors="replace").read() if os.path.exists(path) else ""
    out = {"n_lines": txt.count("\n"),
           "errors": [l for l in txt.splitlines() if re.search(r"\[(error|ERROR)\]| ERROR |Cannot |cannot ", l)][:20],
           "warnings_n": len(re.findall(r"\[warning\]", txt))}
    m = re.findall(r"Successfully relocated (\d+) events", txt)
    out["successfully_relocated"] = int(m[-1]) if m else None
    m = re.findall(r"Found (\d+) event clusters", txt)
    out["clusters"] = int(m[-1]) if m else None
    for ph in ("P", "S"):
        m = re.findall(rf"Total {ph} phases CC attempted (\d+) failures ([\d.]+)% \((\d+)\)(.*)", txt)
        if m:
            out[f"cc_{ph}_line"] = " ".join(m[-1])
    m = re.findall(r"Catalog waveform data: (.*)", txt)
    out["waveform_line"] = m[-1] if m else None
    its = re.findall(r"Iteration (\d+) num events (\d+)\. Parameters: (.*)", txt)
    out["iterations_logged"] = len(its)
    out["iteration_lines"] = [" ".join(x) for x in its]
    out["event_rms_lines"] = re.findall(r"Event RMS \[msec\]: (.*)", txt)
    out["dd_residual_lines"] = re.findall(r"Total dd (\d+), dd-residual \[msec\] (.*)", txt)
    return out


def parse_time_v(path):
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path):
        line = line.strip()
        for key, name in (("Maximum resident set size (kbytes)", "max_rss_kb"), ("User time (seconds)", "user_s"),
                          ("System time (seconds)", "sys_s"), ("Elapsed (wall clock) time", "wall"),
                          ("Percent of CPU this job got", "cpu_percent"), ("Exit status", "exit_status")):
            if line.startswith(key):
                out[name] = line.split(": ", 1)[1]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="really write configs and run scrtdd")
    ap.add_argument("--runs", default=",".join(DEFAULT_RUNS))
    ap.add_argument("--force", action="store_true", help="re-run a run whose work/ folder exists")
    a = ap.parse_args()
    stamp = C.now_iso().replace(":", "")[:15]
    log = C.Tee(f"{C.LOGDIR}/11_sanramon_scrtdd_{'apply' if a.apply else 'dryrun'}_{stamp}.log")
    log(f"# scrtdd_sanramon.py {'APPLY' if a.apply else 'DRY RUN'} {C.now_iso()}  runs={a.runs}")
    for name in a.runs.split(","):
        spec = RUNS[name]
        run_dir = f"{C.RUNROOT}/{name}"
        work = f"{run_dir}/work"
        log(f"\n== {name}: {spec['what']}")
        if os.path.exists(work) and not a.force:
            log(f"   {work} exists: skipped (use --force to redo)")
            continue
        args = ["--reloc-catalog", f"{C.STATION_CSV},{C.EVENT_CSV},{C.PHASE_CSV}",
                "--profile", C.PROFILE,
                "--inventory-db", f"file://{C.INVENTORY_XML}",
                "-I", f"sdsarchive://{C.SDS_DIR}",
                "--dump-diagnostics", "--xmlout", "--verbosity=3", "--console=1"]
        if not a.apply:
            for k, v in spec["profile"].items():
                log(f"   profile.{C.PROFILE}.{k} = {v}")
            for k, v in C.GLOBAL_CFG.items():
                log(f"   global: {k} = {v}")
            for k, v in C.module_cfg(run_dir).items():
                log(f"   module: {k} = {v}")
            log("   would run: scrtdd " + " ".join(args))
            continue
        for sub in ("work", "wfcache", "seiscomp_user", "home"):
            if os.path.exists(f"{run_dir}/{sub}"):
                shutil.rmtree(f"{run_dir}/{sub}")
        os.makedirs(work, exist_ok=True)
        C.write_config(run_dir, spec["profile"], header=f"run {name}: {spec['what']}\nwritten by scrtdd_sanramon.py {C.now_iso()}")
        t_start = C.now_iso()
        rc, wall, argv = C.run_scrtdd(args, run_dir, work, f"{work}/relocated.xml", f"{work}/scrtdd.log", log)
        names, rc_pcv = C.print_config_vars(run_dir)
        resolved = C.resolve_options(run_dir, extra={
            "run": name, "description": spec["what"], "start_catalog": C.EVENT_CSV,
            "command": {"argv": argv, "cwd": work, "stdout": f"{work}/relocated.xml", "stderr": f"{work}/scrtdd.log",
                        "env": {k: C.run_env(run_dir)[k] for k in ("SEISCOMP_ROOT", "SEISCOMP_LOCAL_CONFIG", "HOME", "ORT_DISABLE_TELEMETRY")}},
            "versions": C.scrtdd_version(run_dir),
            "inputs_md5": {p: C.md5(p) for p in (C.STATION_CSV, C.EVENT_CSV, C.PHASE_CSV, C.INVENTORY_XML)},
            "print_config_vars": [f"{n} {t}" for n, t in names],
            "started": t_start, "finished": C.now_iso()})
        missing = C.check_print_config_vars(names, resolved)
        resolved["print_config_vars_not_in_dump"] = missing
        C.dump_json(f"{run_dir}/run_options.json", resolved)
        if missing:
            log("   WARNING: variables scrtdd reads but the dump does not cover:", missing)
        diag = sorted(glob.glob(f"{work}/multievent_*"))
        summ = {"run": name, "exit_code": rc, "wall_s": round(wall, 1), "time_v": parse_time_v(f"{run_dir}/time_v.txt"),
                "outputs": sorted(os.listdir(work)), "diagnostics_dirs": diag,
                "log": count_log(f"{work}/scrtdd.log")}
        if os.path.exists(f"{work}/reloc-event.csv"):
            with open(f"{work}/reloc-event.csv") as f:
                summ["reloc_event_rows"] = sum(1 for _ in f) - 1
        C.dump_json(f"{run_dir}/run_summary.json", summ)
        log(f"   outputs: {summ['outputs']}")
        log(f"   relocated events (log): {summ['log']['successfully_relocated']}; reloc-event rows: {summ.get('reloc_event_rows')}; "
            f"peak RSS {summ['time_v'].get('max_rss_kb')} kB; wall {summ['wall_s']} s")
        for k in ("cc_P_line", "cc_S_line", "waveform_line"):
            if summ["log"].get(k):
                log(f"   {k}: {summ['log'][k]}")
        if summ["log"]["errors"]:
            log("   log error lines:", *summ["log"]["errors"][:5])
    log(f"\n# done {C.now_iso()}")


if __name__ == "__main__":
    main()
