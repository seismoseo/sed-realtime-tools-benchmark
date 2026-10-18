#!/usr/bin/env python
# scrtdd_singleevent.py -- real-time style (single-event) scrtdd relocation of the 11 Gwangyang events, offline.
#
# Usage (after 'source install/env_seiscomp.sh'; dry run by default):
#     python scrtdd_singleevent.py                         # show what would be written and run
#     python scrtdd_singleevent.py --apply                 # both modes, all 11 events
#     python scrtdd_singleevent.py --apply --modes SEa --events 1,3
#
# What it does, and why:
#   * Reference catalog = the multi-event result of run S1 (cross-correlation 'like_reference', solver and
#     clustering 'hypodd_like', centroid start). LEAVE-ONE-OUT: for event k the reference catalog is S1
#     without event k (its relocated position and its picks are removed), so an event is never paired with
#     itself. The 11 catalogs are written to SE*/catalogs/loo_<k>/{event,phase,station}.csv.
#   * The event to relocate is one SCML origin (seiscomp.datamodel, written with seiscomp.io.XMLArchive):
#     the HYPOINVERSE kim1983 location and origin time (inputs/rtdd_catalog/event.csv), one pick per row of
#     phase.csv (the same 763 picks the catalog uses; full stream id NET.STA..CHA) and one arrival per pick
#     (weight 1, timeUsed true). SE*/origins/origin_<k>.xml, plus origins_all.xml with all 11.
#   * scrtdd --ep origin_<k>.xml --profile gwangyang relocates it in single-event mode (singleevent.rst
#     "Relocate an XML file"): step 1 = catalog differential times only, step 2 = from the step-1 location
#     again, with cross-correlation. The output SCML (stdout) holds the relocated origin (methodID RTDD).
#   * Two modes, because rtDD treats automatic and manual picks differently in cross-correlation
#     (libhdd dd.cpp:1572-1585: a manual pick is "trusted" like a catalog pick; for an automatic pick the
#     real-time trace is the long window). Origin and picks get evaluationMode
#       SEa = automatic  (what a real-time scautoloc origin looks like)
#       SEm = manual     (same treatment as the catalog picks in the multi-event run)
#   * Profile settings: identical to run S1 (scrtdd_common.py), plus profile.gwangyang.catalog.* pointing
#     to the leave-one-out catalog. The single-event clustering block of 'hypodd_like' applies
#     (no neighbour limit, 10 km, minNumNeighbours 1, minNumPhases 1).
#   * WORKAROUND for a crash in scrtdd v2.0.10: 'scrtdd --ep ... --inventory-db file://...' dies with a
#     segmentation fault right after "Starting process" (found 2026-10-17, runs/gwangyang/scrtdd/SEa/ev1/work/
#     scrtdd_debug_crash.log). With the inventory read from a file, scrtdd switches the database off
#     (apps/scrtdd/rtddtool.cpp:1029-1035) and then calls query()->getEvent() on the missing database
#     (rtddtool.cpp:1586). The documented command has "[db options]". So the inventory is imported once
#     (scdb -i inventory_sc.xml) into a private SQLite database (SeisComP schema share/db/sqlite3.sql) in
#     runs/gwangyang/scrtdd/se_inventory_db/, and scrtdd gets '-d sqlite3://...' instead of --inventory-db.
#     The database holds only the inventory; scrtdd does not write to it in --ep mode (checked by md5).
#
# Outputs per mode: SE*/ev<k>/{seiscomp_user,home,work,run_options.json}, SE*/single_event_results.csv
# (relocated origin per event + which steps succeeded, from the log), SE*/single_event_results.json.

import argparse
import csv
import glob
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrtdd_common as C  # noqa: E402

# ----------------------------------------------------------------------------- parameters
REF_RUN = "S1"
REF_EVENT_CSV = f"{C.RUNROOT}/{REF_RUN}/work/reloc-event.csv"
START_EVENT_CSV = C.EVENT_HYPOINV_CSV           # HYPOINVERSE location = the "real-time" starting origin
MODES = {"SEa": "automatic", "SEm": "manual"}
AGENCY = "GWYTEST"                              # labels only (no messaging, no database)
AUTHOR = "hypoinverse_kim1983"
PROFILE_SE = {**C.COMMON, **C.CLUSTERING_HYPODD_LIKE, **C.SOLVER_HYPODD_LIKE, **C.XCORR_LIKE_REFERENCE}
DB_DIR = f"{C.RUNROOT}/se_inventory_db"
DB_FILE = f"{DB_DIR}/inventory.sqlite"
DB_URL = f"sqlite3://{DB_FILE}"


def make_inventory_db(log):
    """Private SQLite database with the SeisComP schema and only the Gwangyang inventory in it."""
    import sqlite3
    import subprocess
    # reuse an existing database when it was made from the same inventory and is unchanged since (the import
    # takes about 2 minutes on /home, one SQLite transaction per object)
    if os.path.exists(f"{DB_DIR}/db_info.json") and os.path.exists(DB_FILE):
        info = json.load(open(f"{DB_DIR}/db_info.json"))
        if (info.get("inventory_md5") == C.md5(C.INVENTORY_XML) and info.get("db_md5_after_import") == C.md5(DB_FILE)
                and info.get("scdb_exit") == 0 and info.get("row_counts", {}).get("Station") == 54):
            log(f"   inventory database {DB_FILE} reused (same inventory md5, unchanged since import)")
            return info
    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)
    os.makedirs(f"{DB_DIR}/seiscomp_user", exist_ok=True)
    os.makedirs(f"{DB_DIR}/home", exist_ok=True)
    schema = f"{os.environ['SEISCOMP_ROOT']}/share/db/sqlite3.sql"
    con = sqlite3.connect(DB_FILE)
    con.executescript(open(schema).read())
    con.commit()
    con.close()
    argv = ["nice", "-n", str(C.NICE), "/usr/bin/timeout", "300", "scdb", "-d", DB_URL, "-i", C.INVENTORY_XML,
            "--verbosity=3", "--console=1"]
    p = subprocess.run(argv, env=C.run_env(DB_DIR), cwd=DB_DIR, capture_output=True, text=True)
    with open(f"{DB_DIR}/scdb_import.log", "w") as f:
        f.write(" ".join(argv) + "\n" + p.stdout + p.stderr)
    con = sqlite3.connect(DB_FILE)
    counts = {t: con.execute(f"select count(*) from {t}").fetchone()[0]
              for t in ("Network", "Station", "SensorLocation", "Stream", "Origin", "Pick", "Event")}
    con.close()
    info = {"schema": schema, "schema_md5": C.md5(schema), "import_cmd": argv, "scdb_exit": p.returncode,
            "row_counts": counts, "db_md5_after_import": C.md5(DB_FILE), "inventory_md5": C.md5(C.INVENTORY_XML)}
    C.dump_json(f"{DB_DIR}/db_info.json", info)
    log(f"   inventory database {DB_FILE}: scdb exit {p.returncode}, rows {counts}")
    if p.returncode != 0 or counts["Station"] != 54:
        sys.exit("inventory import failed: see " + f"{DB_DIR}/scdb_import.log")
    return info


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_loo_catalogs(mode_dir, ids, log):
    ref = read_csv(REF_EVENT_CSV)
    pha = read_csv(C.PHASE_CSV)
    with open(C.PHASE_CSV) as f:
        pha_fields = f.readline().strip().split(",")
    out = {}
    for k in ids:
        d = f"{mode_dir}/catalogs/loo_{k}"
        os.makedirs(d, exist_ok=True)
        evs = [r for r in ref if int(r["id"]) != k]
        # only the standard catalog columns; relocated/startRms/finalRms are outputs, not inputs
        write_csv(f"{d}/event.csv", evs, ["id", "isotime", "latitude", "longitude", "depth", "magnitude"])
        write_csv(f"{d}/phase.csv", [r for r in pha if int(r["eventId"]) != k], pha_fields)
        shutil.copyfile(C.STATION_CSV, f"{d}/station.csv")
        out[k] = d
        log(f"   loo_{k}: {len(evs)} events, {sum(1 for r in pha if int(r['eventId']) != k)} picks")
    return out


def build_scml(mode_dir, ids, evaluation_mode, log):
    """One SCML file per event (and one with all of them) with origin, picks and arrivals."""
    import seiscomp.core as SC
    import seiscomp.datamodel as DM
    import seiscomp.io as IO

    em = DM.AUTOMATIC if evaluation_mode == "automatic" else DM.MANUAL
    start = {int(r["id"]): r for r in read_csv(START_EVENT_CSV)}
    idmap = {int(r["rtdd_id"]): r["kma_id"] for r in read_csv(f"{C.CAT}/event_id_map.csv")}
    pha = read_csv(C.PHASE_CSV)
    os.makedirs(f"{mode_dir}/origins", exist_ok=True)
    now = SC.Time.UTC() if hasattr(SC.Time, "UTC") else SC.Time.GMT()

    def make_ep(evlist):
        ep = DM.EventParameters()
        for k in evlist:
            e = start[k]
            kma = idmap[k]
            ci = DM.CreationInfo()
            ci.setAgencyID(AGENCY)
            ci.setAuthor(AUTHOR)
            ci.setCreationTime(now)
            org = DM.Origin.Create(f"Origin/gwangyang/{kma}/hypoinverse")
            org.setCreationInfo(ci)
            org.setTime(DM.TimeQuantity(SC.Time.FromString(e["isotime"], "%FT%T.%fZ")))
            org.setLatitude(DM.RealQuantity(float(e["latitude"])))
            org.setLongitude(DM.RealQuantity(float(e["longitude"])))
            org.setDepth(DM.RealQuantity(float(e["depth"])))
            org.setEvaluationMode(em)
            org.setMethodID("HYPOINVERSE")
            org.setEarthModelID("kim1983")
            for r in (r for r in pha if int(r["eventId"]) == k):
                pid = f"Pick/gwangyang/{kma}/{r['networkCode']}.{r['stationCode']}.{r['locationCode']}.{r['channelCode']}/{r['type']}"
                p = DM.Pick.Create(pid)
                p.setCreationInfo(ci)
                p.setTime(DM.TimeQuantity(SC.Time.FromString(r["isotime"], "%FT%T.%fZ")))
                p.setWaveformID(DM.WaveformStreamID(r["networkCode"], r["stationCode"], r["locationCode"],
                                                    r["channelCode"], ""))
                p.setPhaseHint(DM.Phase(r["type"]))
                p.setEvaluationMode(em)
                p.setMethodID("PhaseNet+")
                ep.add(p)
                a = DM.Arrival()
                a.setPickID(pid)
                a.setPhase(DM.Phase(r["type"]))
                a.setWeight(1.0)
                a.setTimeUsed(True)
                org.add(a)
            ep.add(org)
        return ep

    files = {}
    for k in ids:
        path = f"{mode_dir}/origins/origin_{k}.xml"
        ar = IO.XMLArchive()
        ar.create(path)
        ar.setFormattedOutput(True)
        ar.writeObject(make_ep([k]))
        ar.close()
        files[k] = path
    ar = IO.XMLArchive()
    ar.create(f"{mode_dir}/origins/origins_all.xml")
    ar.setFormattedOutput(True)
    ar.writeObject(make_ep(sorted(start)))
    ar.close()
    log(f"   SCML written: {len(files)} single-origin files + origins_all.xml ({evaluation_mode})")
    return files


def parse_output(xml_path):
    """The relocated origin (methodID RTDD) in scrtdd's SCML output."""
    import seiscomp.datamodel as DM
    import seiscomp.io as IO
    if not os.path.exists(xml_path) or os.path.getsize(xml_path) == 0:
        return None
    ar = IO.XMLArchive()
    if not ar.open(xml_path):
        return None
    obj = ar.readObject()
    ar.close()
    ep = DM.EventParameters.Cast(obj)
    if ep is None:
        return None
    out = []
    for i in range(ep.originCount()):
        o = ep.origin(i)
        try:
            mid = o.methodID()
        except Exception:
            mid = ""
        if mid != "RTDD":
            continue
        q = {}
        try:
            oq = o.quality()
            for f in ("usedPhaseCount", "associatedPhaseCount", "usedStationCount", "standardError", "azimuthalGap"):
                try:
                    q[f] = getattr(oq, f)()
                except Exception:
                    q[f] = None
        except Exception:
            pass
        n_used = sum(1 for j in range(o.arrivalCount()) if _safe(o.arrival(j).timeUsed))
        src = ""
        for j in range(o.commentCount()):
            if o.comment(j).id() == "relocation::sourceOrigin":
                src = o.comment(j).text()
        out.append({"publicID": o.publicID(), "time": o.time().value().iso(),
                    "latitude": o.latitude().value(), "longitude": o.longitude().value(),
                    "depth_km": o.depth().value(), "arrivals": o.arrivalCount(), "arrivals_used": n_used,
                    "sourceOrigin": src, **{f"quality_{k}": v for k, v in q.items()}})
    return out


def _safe(f):
    try:
        return bool(f())
    except Exception:
        return False


def parse_log(path):
    txt = open(path, errors="replace").read() if os.path.exists(path) else ""
    r = {}
    m = re.search(r"Step 1 relocation successful, new location: lat (\S+) lon (\S+) depth (\S+) time (\S+)", txt)
    r["step1_ok"] = bool(m)
    if m:
        r.update(step1_lat=float(m.group(1)), step1_lon=float(m.group(2)), step1_depth=float(m.group(3)), step1_time=m.group(4))
    m = re.search(r"Step 2 relocation successful, new location: lat (\S+) lon (\S+) depth (\S+) time (\S+)", txt)
    r["step2_ok"] = bool(m)
    if m:
        r.update(step2_lat=float(m.group(1)), step2_lon=float(m.group(2)), step2_depth=float(m.group(3)), step2_time=m.group(4))
    r["step1_failed_msg"] = "Failed to perform step 1" in txt
    r["step2_failed_msg"] = "Failed to perform step 2" in txt
    r["neighbours_found"] = ",".join(re.findall(r"Found (\d+) neighbouring events", txt))
    r["cannot_relocate"] = "Cannot relocate origin" in txt
    for ph in ("P", "S"):
        m = re.findall(rf"Total {ph} phases CC attempted (\d+) failures ([\d.]+)% \((\d+)\)\s+Above coeff threshold \(([\d.]+)\) ([\d.]+)% \((\d+)\)", txt)
        if m:
            r[f"cc_{ph}_attempted"], r[f"cc_{ph}_above"] = int(m[-1][0]), int(m[-1][5])
    r["error_lines"] = " | ".join(l.strip() for l in txt.splitlines() if "[error]" in l)[:500]
    r["log_lines"] = txt.count("\n")
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--events", default=",".join(str(i) for i in range(1, 12)))
    a = ap.parse_args()
    ids = [int(x) for x in a.events.split(",")]
    stamp = C.now_iso().replace(":", "")[:15]
    log = C.Tee(f"{C.LOGDIR}/08_gwangyang_scrtdd_singleevent_{'apply' if a.apply else 'dryrun'}_{stamp}.log")
    log(f"# scrtdd_singleevent.py {'APPLY' if a.apply else 'DRY RUN'} {C.now_iso()} modes={a.modes} events={ids}")
    log(f"# reference catalog: {REF_EVENT_CSV} (leave-one-out); start origins: {START_EVENT_CSV}")
    if not os.path.exists(REF_EVENT_CSV):
        sys.exit(f"missing {REF_EVENT_CSV}: run scrtdd_multievent.py --apply --runs {REF_RUN} first")
    if a.apply:
        dbinfo = make_inventory_db(log)
    for mode in a.modes.split(","):
        evmode = MODES[mode]
        mode_dir = f"{C.RUNROOT}/{mode}"
        log(f"\n== {mode}: origins and picks '{evmode}'")
        if not a.apply:
            log(f"   would write {mode_dir}/catalogs/loo_<k>, {mode_dir}/origins/origin_<k>.xml and run, per event:")
            log(f"   scrtdd --ep origin_<k>.xml --profile {C.PROFILE} -d {DB_URL} "
                f"-I sdsarchive://{C.SDS_DIR} --dump-diagnostics --verbosity=3 --console=1 > relocated.xml")
            continue
        os.makedirs(mode_dir, exist_ok=True)
        cats = write_loo_catalogs(mode_dir, ids, log)
        xmls = build_scml(mode_dir, ids, evmode, log)
        rows = []
        for k in ids:
            run_dir = f"{mode_dir}/ev{k}"
            work = f"{run_dir}/work"
            for sub in ("work", "wfcache"):
                if os.path.exists(f"{run_dir}/{sub}"):
                    shutil.rmtree(f"{run_dir}/{sub}")
            os.makedirs(work, exist_ok=True)
            prof = dict(PROFILE_SE)
            prof["catalog.eventFile"] = f"{cats[k]}/event.csv"
            prof["catalog.phaFile"] = f"{cats[k]}/phase.csv"
            prof["catalog.stationFile"] = f"{cats[k]}/station.csv"
            C.write_config(run_dir, prof, header=f"{mode} event {k}: single-event relocation against S1 without event {k}\n"
                                                 f"written by scrtdd_singleevent.py {C.now_iso()}")
            args = ["--ep", xmls[k], "--profile", C.PROFILE,
                    "-d", DB_URL, "-I", f"sdsarchive://{C.SDS_DIR}",
                    "--dump-diagnostics", "--verbosity=3", "--console=1"]
            log(f"-- {mode} event {k}")
            rc, wall, argv = C.run_scrtdd(args, run_dir, work, f"{work}/relocated.xml", f"{work}/scrtdd.log", log)
            names, _ = C.print_config_vars(run_dir)
            resolved = C.resolve_options(run_dir, extra={
                "run": f"{mode}_ev{k}", "mode": evmode, "reference_catalog": cats[k], "origin_xml": xmls[k],
                "command": {"argv": argv, "cwd": work},
                "versions": C.scrtdd_version(run_dir),
                "inputs_md5": {p: C.md5(p) for p in (xmls[k], f"{cats[k]}/event.csv", f"{cats[k]}/phase.csv",
                                                     f"{cats[k]}/station.csv", C.INVENTORY_XML, DB_FILE)},
                "inventory_database": DB_URL,
                "print_config_vars": [f"{n} {t}" for n, t in names]})
            resolved["print_config_vars_not_in_dump"] = C.check_print_config_vars(names, resolved)
            C.dump_json(f"{run_dir}/run_options.json", resolved)
            parsed = parse_output(f"{work}/relocated.xml") or []
            lg = parse_log(f"{work}/scrtdd.log")
            row = {"mode": mode, "evaluation_mode": evmode, "event_id": k, "exit_code": rc, "wall_s": round(wall, 1),
                   "n_relocated_origins": len(parsed), **lg}
            if parsed:
                row.update({f"reloc_{kk}": vv for kk, vv in parsed[-1].items()})
            row["diagnostics_dirs"] = ";".join(os.path.basename(p) for p in sorted(glob.glob(f"{work}/singleevent_*")))
            rows.append(row)
            log(f"   step1 {'ok' if lg['step1_ok'] else 'FAILED'}, step2 {'ok' if lg['step2_ok'] else 'FAILED'}, "
                f"neighbours {lg['neighbours_found']}, CC P {lg.get('cc_P_above')}/{lg.get('cc_P_attempted')} "
                f"S {lg.get('cc_S_above')}/{lg.get('cc_S_attempted')}, relocated origins in XML: {len(parsed)}")
            if lg["error_lines"]:
                log("   errors:", lg["error_lines"][:300])
        fields = sorted({f for r in rows for f in r}, key=lambda x: (not x.startswith(("mode", "evaluation", "event", "exit", "wall", "n_", "step")), x))
        write_csv(f"{mode_dir}/single_event_results.csv", rows, fields)
        C.dump_json(f"{mode_dir}/single_event_results.json", rows)
        log(f"   results: {mode_dir}/single_event_results.csv")
    if a.apply:
        after = C.md5(DB_FILE)
        log(f"   inventory database md5 after the runs {after} "
            f"({'unchanged' if after == dbinfo['db_md5_after_import'] else 'CHANGED'})")
    log(f"\n# done {C.now_iso()}")


if __name__ == "__main__":
    main()
