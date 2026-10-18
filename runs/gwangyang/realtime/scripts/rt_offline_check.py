#!/usr/bin/env python
# rt_offline_check.py -- step 10 cross-check, OFFLINE (no messaging, no network): relocate the very origin that the
# real-time scrtdd relocated, with 'scrtdd --ep' and the same profile and reference catalog, in two variants:
#   P   : the scautoloc origin exactly as stored in the run's database (P arrivals only, as in real time).
#         Expected to reproduce the real-time RTDD origin; differences would come from the real-time path itself.
#   PS  : the same origin plus the DL S picks (SDL3C) of the same stations as S arrivals. scautoloc never
#         associates S picks (its phase list has no S: scautoloc/associator.cpp:41-51), so this variant shows what
#         the real-time chain loses by relocating with P picks only.
#   P_nodw (diagnostic, only with --variants): P only, with solver.downWeightingByResidual = "0, 0" instead of the
#         profile's "10, 5", i.e. no residual down-weighting at all (libhdd interpolates the factor linearly over the
#         iterations, so "0, 5" would give very aggressive factors 0.26, 0.53, ... early on). libhdd weights each double
#         difference by (1 - (r / (alpha*MAD/0.6745))^2)^2 with r measured from ZERO (solver.cpp:554-584), so a
#         common ~1 s origin-time error of the starting origin can zero nearly all weights (run RT5). This variant
#         only tests that explanation; it is not a proposed setting.
# --origins selects the input origins (default: every origin the real-time scrtdd tried, including failures).
# All variants use a COPY of the run's database (inventory + the run's picks/origins; scrtdd --ep only reads it: md5
# checked) and their own SEISCOMP_LOCAL_CONFIG / HOME / waveform cache inside <run>/offline_check/.
#
# Script provenance (added 2026-10-17; the checks of RT2 and RT5 were made before it): every --apply run appends the
# md5 of each driver script on disk (rt_chain.py, rt_options.py, rt_offline_check.py, rt_analyze.py), the md5 of this
# script as loaded, the stage (offline_check<tag>), time and argv to <run>/options/script_provenance.json, and keeps a
# copy of this script as <run>/options/scripts/rt_offline_check.<md5>.py (copied only if absent).
#
# Usage (after 'source install/env_seiscomp.sh'; dry run by default):
#     python rt_offline_check.py --run RT2_filefeed            # shows what it would do
#     python rt_offline_check.py --run RT2_filefeed --apply

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
RTROOT = f"{PROJECT}/runs/gwangyang/realtime"
LOGDIR = f"{PROJECT}/logs"
S1_EVENT_CSV = f"{PROJECT}/runs/gwangyang/scrtdd/S1/work/reloc-event.csv"
REPLAY = {"20210827220322": 3, "20260202194119": 9}
KMA_OT = {"20210827220322": "2021-08-27 22:03:22", "20260202194119": "2026-02-02 19:41:19"}
S_WINDOW_S = (0.0, 40.0)    # S picks taken from origin time + 0..40 s (S at 99 km arrives ~29 s after origin)
NICE = 10
TIMEOUT_S = 300
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_SCRIPTS = ["rt_chain.py", "rt_options.py", "rt_offline_check.py", "rt_analyze.py"]
SCRIPT_BYTES = open(os.path.abspath(__file__), "rb").read()            # this script as loaded (copied for provenance)
SCRIPT_MD5 = hashlib.md5(SCRIPT_BYTES).hexdigest()


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def record_provenance(rdir, stage, log):
    """Append one entry to <run>/options/script_provenance.json (md5 of every driver script on disk, md5 of this
    script as loaded, stage, time, argv) and keep a copy of this script as <run>/options/scripts/<name>.<md5>.py."""
    opt = f"{rdir}/options"
    os.makedirs(f"{opt}/scripts", exist_ok=True)
    name = os.path.basename(os.path.abspath(__file__))
    copy = f"{opt}/scripts/{name[:-3]}.{SCRIPT_MD5}.py"
    if not os.path.exists(copy):
        with open(copy, "wb") as f:
            f.write(SCRIPT_BYTES)
    on_disk = {s: (md5(f"{SCRIPT_DIR}/{s}") if os.path.exists(f"{SCRIPT_DIR}/{s}") else None) for s in DRIVER_SCRIPTS}
    entry = dict(time=now_iso(), stage=stage, script=name, script_md5_as_loaded=SCRIPT_MD5, script_copy=copy,
                 argv=list(sys.argv), python=sys.executable, cwd=os.getcwd(), host=os.uname().nodename.split(".")[0],
                 driver_scripts_md5_on_disk=on_disk, recorded_at="start of the stage")
    path = f"{opt}/script_provenance.json"
    entries = json.load(open(path)) if os.path.exists(path) else []
    entries.append(entry)
    with open(path + ".tmp", "w") as f:
        json.dump(entries, f, indent=1)
    os.replace(path + ".tmp", path)
    log(f"# provenance: {stage} by {name} md5 {SCRIPT_MD5} -> {path} (entry {len(entries)}); driver scripts on disk: "
        f"{on_disk}")


class Tee:
    def __init__(self, path):
        self.f = open(path, "a")
        self.path = path

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        self.f.write(s + "\n")
        self.f.flush()


def env_for(check, cfgdir=None):
    env = dict(os.environ)
    env["SEISCOMP_LOCAL_CONFIG"] = cfgdir or f"{check}/seiscomp_user"
    env["HOME"] = f"{check}/home"
    env["ORT_DISABLE_TELEMETRY"] = "1"
    return env


def run(argv, check, log, cwd, stdout_path=None, stdin=None, cfgdir=None):
    full = ["nice", "-n", str(NICE), "/usr/bin/timeout", str(TIMEOUT_S)] + argv
    log("  $", " ".join(full) + (f" > {stdout_path}" if stdout_path else ""))
    t0 = time.time()
    fo = open(stdout_path, "wb") if stdout_path else subprocess.PIPE
    p = subprocess.run(full, cwd=cwd, env=env_for(check, cfgdir), stdout=fo, stderr=subprocess.PIPE, stdin=stdin)
    if stdout_path:
        fo.close()
    log(f"    exit {p.returncode} ({time.time() - t0:.1f} s)" + (f"; stderr tail: {p.stderr.decode(errors='replace').strip()[-400:]}"
                                                                 if p.returncode else ""))
    return p.returncode, (p.stdout.decode(errors="replace") if not stdout_path else "")


def add_s_arrivals(xml_in, xml_s_picks, xml_out, log):
    """Origin XML (scxmldump -O -P) + S picks XML -> origin with one S arrival per S pick (phase S, weight 1)."""
    import seiscomp.datamodel as dm
    import seiscomp.io as scio
    ar = scio.XMLArchive()
    ar.open(xml_in)
    ep = dm.EventParameters.Cast(ar.readObject())
    ar.close()
    ar = scio.XMLArchive()
    ar.open(xml_s_picks)
    eps = dm.EventParameters.Cast(ar.readObject())
    ar.close()
    org = ep.origin(0)
    n_added = 0
    for i in range(eps.pickCount()):
        pk = dm.Pick.Cast(eps.pick(i).clone())
        ep.add(pk)
        arr = dm.Arrival()
        arr.setPickID(pk.publicID())
        arr.setPhase(dm.Phase("S"))
        arr.setWeight(1.0)
        arr.setTimeUsed(True)
        org.add(arr)
        n_added += 1
    ar = scio.XMLArchive()
    ar.create(xml_out)
    ar.setFormattedOutput(True)
    ar.writeObject(ep)
    ar.close()
    log(f"    {xml_out}: {org.arrivalCount()} arrivals ({n_added} S added), {ep.pickCount()} picks")
    return n_added


def read_relocated(xml):
    import seiscomp.datamodel as dm
    import seiscomp.io as scio
    if not os.path.exists(xml) or os.path.getsize(xml) == 0:
        return None
    ar = scio.XMLArchive()
    if not ar.open(xml):
        return None
    ep = dm.EventParameters.Cast(ar.readObject())
    ar.close()
    if ep is None:
        return None
    for i in range(ep.originCount()):
        o = ep.origin(i)
        if o.methodID() == "RTDD":
            n_p = sum(1 for k in range(o.arrivalCount()) if o.arrival(k).phase().code() == "P")
            n_s = sum(1 for k in range(o.arrivalCount()) if o.arrival(k).phase().code() == "S")
            return dict(publicID=o.publicID(), lat=o.latitude().value(), lon=o.longitude().value(),
                        depth_km=o.depth().value(), time=o.time().value().iso(), n_arr_P=n_p, n_arr_S=n_s)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="RT2_filefeed")
    ap.add_argument("--variants", default="P,PS")
    ap.add_argument("--origins", default="", help="comma-separated input origin IDs (default: all tried)")
    ap.add_argument("--tag", default="", help="suffix of the output folder offline_check<tag>")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    rdir = f"{RTROOT}/{a.run}"
    check = f"{rdir}/offline_check{a.tag}"
    variants = a.variants.split(",")
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    log = Tee(f"{LOGDIR}/10_gwangyang_realtime_{a.run}_offline_check_{'apply' if a.apply else 'dryrun'}_{stamp}.log")
    log(f"# rt_offline_check.py --run {a.run} {'APPLY' if a.apply else 'DRY RUN'} {now_iso()}; script md5 (as loaded) "
        f"{SCRIPT_MD5}")
    relocs = list(csv.DictReader(open(f"{rdir}/results/scrtdd_relocations.csv")))
    if a.origins:
        want = a.origins.split(",")
        relocs = [r for r in relocs if r["input_origin"] in want]
    origins = list(csv.DictReader(open(f"{rdir}/results/origins.csv")))
    picks = list(csv.DictReader(open(f"{rdir}/db_dump/sql_picks.csv")))
    arrivals = list(csv.DictReader(open(f"{rdir}/db_dump/sql_arrivals.csv")))
    db = f"{rdir}/db/seiscomp.sqlite"
    if not a.apply:
        for r in relocs:
            log(f"  would relocate {r['input_origin']} offline (variants {', '.join(variants)}) with a copy of {db}")
        return
    if os.path.exists(check):
        sys.exit(f"{check} exists; remove it by hand to re-run")
    record_provenance(rdir, f"offline_check{a.tag}", log)
    os.makedirs(f"{check}/home")
    shutil.copytree(f"{rdir}/seiscomp_user", f"{check}/seiscomp_user")
    # own waveform cache for this check (the template line is replaced, everything else identical)
    p = f"{check}/seiscomp_user/scrtdd.cfg"
    txt = open(p).read()
    txt = re.sub(r"^performance.cacheDirectory = .*$", f"performance.cacheDirectory = {check}/rtdd_cache", txt, flags=re.M)
    open(p, "w").write(txt + "\n# rt_offline_check.py: cacheDirectory moved into offline_check/\n")
    if "P_nodw" in variants:   # a second config folder, identical except the one solver key
        shutil.copytree(f"{check}/seiscomp_user", f"{check}/seiscomp_user_nodw")
        q = f"{check}/seiscomp_user_nodw/scrtdd.cfg"
        t = open(q).read()
        t2 = re.sub(r"^profile.gwangyang.solver.downWeightingByResidual = .*$",
                    "profile.gwangyang.solver.downWeightingByResidual = 0, 0", t, flags=re.M)
        if t2 == t:
            sys.exit("solver.downWeightingByResidual line not found in scrtdd.cfg")
        open(q, "w").write(t2 + "\n# rt_offline_check.py DIAGNOSTIC: residual down-weighting off in every iteration\n")
    dbc = f"{check}/db_copy.sqlite"
    shutil.copyfile(db, dbc)
    md5_before = md5(dbc)
    rows = []
    s1 = {int(r["id"]): r for r in csv.DictReader(open(S1_EVENT_CSV))}
    for r in relocs:
        oid = r["input_origin"]
        org = [o for o in origins if o["publicID"] == oid][0]
        kma = org["kma_id"]
        wd = f"{check}/{kma}"
        if os.path.exists(wd):   # a second origin of the same event
            wd = f"{check}/{kma}_{oid.split('/')[-1]}"
        os.makedirs(wd)
        run(["scxmldump", "--core.plugins=dbsqlite3", "-d", f"sqlite3://{dbc}", "-O", oid, "-P", "-f", "-o",
             f"{wd}/origin_P.xml"], check, log, wd)
        # S picks of the same stations as the origin's P arrivals, origin time + 0..40 s
        p_ids = {x["pickID"] for x in arrivals if x["originID"] == oid}
        p_sta = {x["waveformID_stationCode"] for x in picks if x["publicID"] in p_ids}
        ot = datetime.datetime.fromisoformat(KMA_OT[kma])
        s_ids = []
        for x in picks:
            if x["methodID"] != "SDL3C" or x["waveformID_stationCode"] not in p_sta:
                continue
            t = datetime.datetime.fromisoformat(x["time_value"]) + datetime.timedelta(microseconds=int(x["time_value_ms"]))
            if S_WINDOW_S[0] <= (t - ot).total_seconds() <= S_WINDOW_S[1]:
                s_ids.append(x["publicID"])
        with open(f"{wd}/s_pick_ids.txt", "w") as f:
            f.write("\n".join(s_ids) + "\n")
        with open(f"{wd}/s_pick_ids.txt") as fin:
            run(["scxmldump", "--core.plugins=dbsqlite3", "-d", f"sqlite3://{dbc}", "--pick", "-", "-f", "-o",
                 f"{wd}/s_picks.xml"], check, log, wd, stdin=fin)
        n_s = add_s_arrivals(f"{wd}/origin_P.xml", f"{wd}/s_picks.xml", f"{wd}/origin_PS.xml", log)
        for var in variants:
            vd = f"{wd}/{var}"
            os.makedirs(vd)
            t0 = time.time()
            xml_in = f"{wd}/origin_PS.xml" if var == "PS" else f"{wd}/origin_P.xml"
            cfgdir = f"{check}/seiscomp_user_nodw" if var == "P_nodw" else f"{check}/seiscomp_user"
            rc, _ = run(["scrtdd", "--ep", xml_in, "--profile", "gwangyang", "--core.plugins=dbsqlite3",
                         "-d", f"sqlite3://{dbc}", "--verbosity=3", "--log-file", f"{vd}/scrtdd.log", "--dump-diagnostics"],
                        check, log, vd, stdout_path=f"{vd}/relocated.xml", cfgdir=cfgdir)
            res = read_relocated(f"{vd}/relocated.xml") or {}
            txt = open(f"{vd}/scrtdd.log", errors="replace").read() if os.path.exists(f"{vd}/scrtdd.log") else ""
            cc = {}
            for ph in ("P", "S"):
                m = re.findall(rf"Total {ph} phases CC attempted (\d+) failures \S+ \((\d+)\)\s+Above coeff threshold "
                               rf"\(([\d.]+)\) \S+ \((\d+)\)", txt)
                if m:
                    cc[f"cc_{ph}_attempted"], cc[f"cc_{ph}_above"] = int(m[-1][0]), int(m[-1][3])
            m1 = re.search(r"Step 1 relocation successful, new location: lat (\S+) lon (\S+) depth (\S+)", txt)
            cc["step1_location"] = " ".join(m1.groups()) if m1 else ""
            cc["failure_lines"] = " | ".join(l.strip()[20:] for l in txt.splitlines()
                                             if re.search(r"Insufficient|Failed to perform|Cannot relocate", l))[:300]
            row = dict(run=a.run, kma_id=kma, rtdd_id=REPLAY[kma], variant=var, input_origin=oid, n_S_added=n_s if var == "PS" else 0,
                       exit_code=rc, wall_s=round(time.time() - t0, 1), step1_ok="Step 1 relocation successful" in txt,
                       step2_ok="Step 2 relocation successful" in txt, messaging_disabled_logged="Disable messaging" in txt,
                       **cc, **{f"reloc_{k}": v for k, v in res.items()},
                       realtime_RTDD_origin=r.get("output_origin"))
            rows.append(row)
            log(f"    {kma} {var}: {res}")
    md5_after = md5(dbc)
    log(f"  database copy md5 before {md5_before} after {md5_after} (unchanged: {md5_before == md5_after})")
    with open(f"{check}/offline_check.csv", "w", newline="") as f:
        keys = sorted({k for r in rows for k in r})
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with open(f"{check}/offline_check.json", "w") as f:
        json.dump(dict(generated=now_iso(), db_copy_md5_before=md5_before, db_copy_md5_after=md5_after, rows=rows,
                       s1_positions={k: s1[v] for k, v in REPLAY.items()}), f, indent=1)
    log(f"# done {now_iso()}: {check}/offline_check.csv")


if __name__ == "__main__":
    main()
