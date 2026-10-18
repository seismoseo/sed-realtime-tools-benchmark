#!/usr/bin/env python
# scrtdd_multievent.py -- multi-event relocations of the 11 Gwangyang events with the SeisComP module scrtdd.
#
# Usage (after 'source install/env_seiscomp.sh'; dry run by default):
#     python scrtdd_multievent.py                    # show what would be written and run
#     python scrtdd_multievent.py --apply            # run all runs below
#     python scrtdd_multievent.py --apply --runs S0,S0n
#
# Each run gets its own folder runs/gwangyang/scrtdd/<RUN>/ with
#   seiscomp_user/{global.cfg,scrtdd.cfg}  private SeisComP configuration (SEISCOMP_LOCAL_CONFIG points here)
#   home/                                  HOME of the scrtdd process (nothing may go to the real ~/.seiscomp)
#   work/                                  scrtdd's working folder: reloc-{event,phase,station}.csv, the
#                                          --dump-diagnostics folder, relocated.xml (--xmlout), console log
#   run_options.json                       EVERY option value scrtdd used (set or default), the command line,
#                                          versions and input checksums
#   run_summary.json                       exit code, run time, counts from the log
#
# Runs (shared settings: see scrtdd_common.py; S0/S1/S2 mirror the pyrtdd runs R0/R1/R2):
#   S0   catalog differential times only; clustering + solver 'hypodd_like'; start = centroid (HypoDD ISTART=1)
#   S1   S0 + cross-correlation 'like_reference'
#   S2   cross-correlation 'xcorr_default' + solver 'rtdd_default' (absolute-location constraint 0.3);
#        clustering 'hypodd_like' (the only clustering block of the shared settings)
#   S0h, S1h  as S0, S1 but starting from the HYPOINVERSE locations (sensitivity to the start)
#   S0n  as S0 but with scrtdd's built-in NonLinLoc reader ('Native:NLLGrid') instead of the SeisComP
#        tttnll plugin: isolates any effect of the plugin/adapter path from the relocation itself
#   S2sc out-of-the-box scrtdd profile: only velocity model, phase names, cross-correlation on, filter and
#        resampling are set; every other option keeps scrtdd's own profile default (these differ from the
#        libhdd/pyrtdd defaults: e.g. cross-correlation only to 60 km and for events < 2 km apart,
#        minNumNeighbours 4, minNumPhases 8, maxNumNeighbours 40, maxNeighbourDistance 5 km)
#
# Why the command looks like this:
#   --reloc-catalog station.csv,event.csv,phase.csv   the CSV triplet (no database needed)
#   --inventory-db file://inventory_sc.xml            channel orientation for the L2 S component; the
#                                                     database connection is then switched off by scrtdd
#   -I sdsarchive://...                               the waveform archive (also set as recordstream)
#   --dump-diagnostics                                pair.csv, xcorr.csv, initial/final-double-difference.csv
#   --xmlout                                          relocated origins as SCML on stdout (-> relocated.xml)
#   --verbosity=3 --console=1                         info-level log on the console (stderr -> scrtdd.log)

import argparse
import glob
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrtdd_common as C  # noqa: E402

# ----------------------------------------------------------------------------- parameters
NATIVE_TABLEMODEL = f"{os.path.dirname(C.NLL_TABLEPATH)};kim1983;0.1;noSwapBytes;512;KeepOpen"

RUNS = {
    "S0": dict(start=C.EVENT_CENTROID_CSV,
               profile={**C.COMMON, **C.CLUSTERING_HYPODD_LIKE, **C.SOLVER_HYPODD_LIKE, **C.XCORR_OFF},
               what="catalog dt only; clustering+solver hypodd_like; centroid start"),
    "S1": dict(start=C.EVENT_CENTROID_CSV,
               profile={**C.COMMON, **C.CLUSTERING_HYPODD_LIKE, **C.SOLVER_HYPODD_LIKE, **C.XCORR_LIKE_REFERENCE},
               what="xcorr like_reference; clustering+solver hypodd_like; centroid start"),
    "S2": dict(start=C.EVENT_CENTROID_CSV,
               profile={**C.COMMON, **C.CLUSTERING_HYPODD_LIKE, **C.SOLVER_RTDD_DEFAULT, **C.XCORR_DEFAULT},
               what="xcorr_default + solver rtdd_default; clustering hypodd_like; centroid start"),
    "S0h": dict(start=C.EVENT_HYPOINV_CSV,
                profile={**C.COMMON, **C.CLUSTERING_HYPODD_LIKE, **C.SOLVER_HYPODD_LIKE, **C.XCORR_OFF},
                what="as S0, HYPOINVERSE start"),
    "S1h": dict(start=C.EVENT_HYPOINV_CSV,
                profile={**C.COMMON, **C.CLUSTERING_HYPODD_LIKE, **C.SOLVER_HYPODD_LIKE, **C.XCORR_LIKE_REFERENCE},
                what="as S1, HYPOINVERSE start"),
    "S0n": dict(start=C.EVENT_CENTROID_CSV,
                profile={**C.COMMON, **C.CLUSTERING_HYPODD_LIKE, **C.SOLVER_HYPODD_LIKE, **C.XCORR_OFF,
                         "tableType": "Native:NLLGrid", "tableModel": f'"{NATIVE_TABLEMODEL}"'},
                what="as S0, scrtdd's built-in NLLGrid reader instead of the tttnll plugin"),
    "S2sc": dict(start=C.EVENT_CENTROID_CSV,
                 profile={k: C.COMMON[k] for k in ("tableType", "tableModel", "P-Phases", "S-Phases")}
                 | {"crossCorrelation.enable": "true"} | C.WF_FILTER,
                 what="scrtdd profile defaults (only model, phases, xcorr on, filter/resampling set); centroid start"),
}
DEFAULT_RUNS = ["S0", "S0n", "S0h", "S1", "S1h", "S2", "S2sc"]


def count_log(path):
    """A few numbers from the scrtdd console log (info level), to be checked against the CSV outputs."""
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
    rms = re.findall(r"Event RMS \[msec\]: (.*)", txt)
    out["event_rms_lines"] = rms
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="really write configs and run scrtdd")
    ap.add_argument("--runs", default=",".join(DEFAULT_RUNS))
    ap.add_argument("--force", action="store_true", help="re-run a run whose work/ folder exists")
    a = ap.parse_args()
    stamp = C.now_iso().replace(":", "")[:15]
    log = C.Tee(f"{C.LOGDIR}/08_gwangyang_scrtdd_multievent_{'apply' if a.apply else 'dryrun'}_{stamp}.log")
    log(f"# scrtdd_multievent.py {'APPLY' if a.apply else 'DRY RUN'} {C.now_iso()}  runs={a.runs}")
    for name in a.runs.split(","):
        spec = RUNS[name]
        run_dir = f"{C.RUNROOT}/{name}"
        work = f"{run_dir}/work"
        log(f"\n== {name}: {spec['what']}")
        log(f"   start catalog {spec['start']}")
        if os.path.exists(work) and not a.force:
            log(f"   {work} exists: skipped (use --force to redo)")
            continue
        args = ["--reloc-catalog", f"{C.STATION_CSV},{spec['start']},{C.PHASE_CSV}",
                "--profile", C.PROFILE,
                "--inventory-db", f"file://{C.INVENTORY_XML}",
                "-I", f"sdsarchive://{C.SDS_DIR}",
                "--dump-diagnostics", "--xmlout", "--verbosity=3", "--console=1"]
        if not a.apply:
            for k, v in spec["profile"].items():
                log(f"   profile.{C.PROFILE}.{k} = {v}")
            log("   would run: scrtdd " + " ".join(args))
            continue
        if os.path.exists(work):
            shutil.rmtree(work)
        for sub in ("wfcache",):
            if os.path.exists(f"{run_dir}/{sub}"):
                shutil.rmtree(f"{run_dir}/{sub}")
        os.makedirs(work, exist_ok=True)
        C.write_config(run_dir, spec["profile"], header=f"run {name}: {spec['what']}\nwritten by scrtdd_multievent.py {C.now_iso()}")
        t_start = C.now_iso()
        rc, wall, argv = C.run_scrtdd(args, run_dir, work, f"{work}/relocated.xml", f"{work}/scrtdd.log", log)
        names, rc_pcv = C.print_config_vars(run_dir)
        resolved = C.resolve_options(run_dir, extra={
            "run": name, "description": spec["what"], "start_catalog": spec["start"],
            "command": {"argv": argv, "cwd": work, "stdout": f"{work}/relocated.xml", "stderr": f"{work}/scrtdd.log",
                        "env": {k: C.run_env(run_dir)[k] for k in ("SEISCOMP_ROOT", "SEISCOMP_LOCAL_CONFIG", "HOME", "ORT_DISABLE_TELEMETRY")}},
            "versions": C.scrtdd_version(run_dir),
            "inputs_md5": {p: C.md5(p) for p in (C.STATION_CSV, spec["start"], C.PHASE_CSV, C.INVENTORY_XML)},
            "print_config_vars": [f"{n} {t}" for n, t in names],
            "started": t_start, "finished": C.now_iso()})
        missing = C.check_print_config_vars(names, resolved)
        resolved["print_config_vars_not_in_dump"] = missing
        C.dump_json(f"{run_dir}/run_options.json", resolved)
        if missing:
            log("   WARNING: variables scrtdd reads but the dump does not cover:", missing)
        diag = sorted(glob.glob(f"{work}/multievent_*"))
        summ = {"run": name, "exit_code": rc, "wall_s": round(wall, 1),
                "outputs": sorted(os.listdir(work)), "diagnostics_dirs": diag,
                "log": count_log(f"{work}/scrtdd.log")}
        if os.path.exists(f"{work}/reloc-event.csv"):
            with open(f"{work}/reloc-event.csv") as f:
                summ["reloc_event_rows"] = sum(1 for _ in f) - 1
        C.dump_json(f"{run_dir}/run_summary.json", summ)
        log(f"   outputs: {summ['outputs']}")
        log(f"   relocated events (log): {summ['log']['successfully_relocated']}; reloc-event rows: {summ.get('reloc_event_rows')}")
        for k in ("cc_P_line", "cc_S_line", "waveform_line"):
            if summ["log"].get(k):
                log(f"   {k}: {summ['log'][k]}")
        if summ["log"]["errors"]:
            log("   log error lines:", *summ["log"]["errors"][:5])
    log(f"\n# done {C.now_iso()}")


if __name__ == "__main__":
    main()
