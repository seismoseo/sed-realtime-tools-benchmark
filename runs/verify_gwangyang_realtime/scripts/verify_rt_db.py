#!/usr/bin/env python3
# verify_rt_db.py -- INDEPENDENT VERIFIER of step 10 (real-time chain test in runs/gwangyang/realtime).
#
# What it checks, and why:
#   1. Database contents. Each run's SQLite database is COPIED into OUT/db_copies/<run>/ (the originals are only
#      read for an md5 before and after), and only the copy is queried, opened read-only and immutable (the WAL
#      files of the originals are empty, so the main file holds everything). Row counts, picks per method,
#      origins per author/method, events with their preferred origin, arrivals per phase.
#   2. Relocated origins. Every RTDD origin must carry author scrtdd@<host> and methodID RTDD. Its input origin
#      comes from scrtdd.log ('Relocating origin X' ... 'Sending origin Y') and must be a scautoloc origin of the
#      same event.
#   3. Positions. The final RTDD origin of each event against S1, R1f, R1 and HypoDD dt.cc, directly ("absolute")
#      and after removing each solution's centroid of the 9 reference events ("relative"); the RTDD origin against
#      the scautoloc origin it was made from; the final scautoloc origin against S1.
#      OWN conversion: a local tangent plane on WGS84 (meridian and prime-vertical radii of curvature at the mean
#      latitude of each pair). rt_analyze.py uses obspy gps2dist_azimuth from 35.0000/127.7286 instead, so these
#      numbers are recomputed by a different route. dU > 0 means the first solution is SHALLOWER (the rule used in
#      the notes).
#   4. Offline cross-check: scrtdd --ep outputs (RT2 offline_check/<kma>/{P,PS}/relocated.xml) parsed directly.
#   5. Picks: database picks against step 09's raw picks.xml (phasenet_original), compared on exact time strings.
#   6. Leakage: no origin made by the offline check (run while RT3 was live on the same port) is in RT3's database.
#
# Usage (any python3 >= 3.9, standard library only):
#     python3 -I verify_rt_db.py            # dry run: lists the inputs, writes nothing
#     python3 -I verify_rt_db.py --apply    # copies the databases, writes OUT/*.csv and OUT/verify_summary.json

import argparse
import csv
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import statistics
import xml.etree.ElementTree as ET

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
RTROOT = f"{PROJECT}/runs/gwangyang/realtime"
RUNS = ["RT1_filefeed", "RT2_filefeed", "RT3_paced", "RT4_filefeed_prefer_rtdd", "RT5_paced_creationtime"]
OUT = f"{PROJECT}/runs/verify_gwangyang_realtime"
LOGDIR = f"{PROJECT}/logs"
ORIGIN = (35.0000, 127.7286)                 # only for centroids; pairwise differences do not depend on it
REPLAY = {"20210827220322": 3, "20260202194119": 9}
KMA_OT = {"20210827220322": "2021-08-27T22:03:22", "20260202194119": "2026-02-02T19:41:19"}
REF_IDS = [1, 2, 4, 5, 6, 7, 8, 10, 11]      # the 9 catalog events (rtdd ids)
PICK_WINDOW_S = (-200, 400)                  # picks of one replay: origin time -200 s .. +400 s (files are ~9 min)
SOL_FILES = {
    "S1": (f"{PROJECT}/runs/gwangyang/scrtdd/S1/work/reloc-event.csv", "id", "latitude", "longitude", "depth", "isotime"),
    "R1f": (f"{PROJECT}/runs/gwangyang/pyrtdd/R1f_xcorr_like_reference_hypodd_like_filtered/relocated-event.csv",
            "id", "latitude", "longitude", "depth", "isotime"),
    "R1": (f"{PROJECT}/runs/gwangyang/pyrtdd/R1_xcorr_like_reference_hypodd_like/relocated-event.csv",
           "id", "latitude", "longitude", "depth", "isotime"),
    "HypoDD_dtcc": (f"{PROJECT}/data/gwangyang_11ev/reference_tables/hypodd_dtcc.csv",
                    "rtdd_id", "latitude", "longitude", "depth_km", "origin_time_pha_datum"),
    "SEa": (f"{PROJECT}/runs/gwangyang/scrtdd/SEa/single_event_results.csv",
            "event_id", "reloc_latitude", "reloc_longitude", "reloc_depth_km", "reloc_time"),
    "SEm": (f"{PROJECT}/runs/gwangyang/scrtdd/SEm/single_event_results.csv",
            "event_id", "reloc_latitude", "reloc_longitude", "reloc_depth_km", "reloc_time"),
}
STEP09 = f"{PROJECT}/runs/gwangyang/dlpicker/output/phasenet_original"      # <kma>/picks.xml
OFFLINE_RT2 = f"{RTROOT}/RT2_filefeed/offline_check"
OFFLINE_RT5_FAILED = f"{RTROOT}/RT5_paced_creationtime/offline_check_failed"

# The claims under test (from the step-10 report), compared below with tolerances
CLAIM_COUNTS = {"RT2_filefeed": dict(Pick=197, Amplitude=374, Origin=9, Arrival=308, Event=2),
                "RT1_filefeed": dict(Pick=112, Amplitude=219, Origin=0)}
CLAIM_POS = {   # (event rtdd id, versus, kind): (dE, dN, dU, d3D, dT_ms or None)
    (3, "scautoloc_input", "absolute"): (-314, -239, -2747, 2775, 827),
    (3, "S1", "absolute"): (-45.0, -16.0, -38.0, 61.1, -0.8),
    (3, "R1f", "absolute"): (-45.0, -17.4, -37.1, 60.8, -0.7),
    (3, "R1", "relative"): (-38.1, -9.4, -46.2, 60.6, None),
    (3, "R1", "absolute"): (None, None, None, 459, 1.8),
    (3, "HypoDD_dtcc", "relative"): (-43.9, -16.9, -27.7, 54.6, None),
    (3, "HypoDD_dtcc", "absolute"): (None, None, None, 413, -12.6),
    (9, "scautoloc_input", "absolute"): (-458, -227, -3886, 3920, 690),
    (9, "S1", "absolute"): (-1.5, -1.0, -4.9, 5.2, -0.9),
    (9, "R1f", "absolute"): (-1.6, -2.5, -4.1, 5.1, -1.0),
    (9, "R1", "relative"): (2.3, -1.5, 3.1, 4.2, None),
    (9, "R1", "absolute"): (None, None, None, 497, -4.5),
    (9, "HypoDD_dtcc", "relative"): (-1.5, 5.2, -6.9, 8.8, None),
    (9, "HypoDD_dtcc", "absolute"): (None, None, None, 368, -18.1),
}
CLAIM_OFFLINE_PS = {3: dict(S1=(-21.8, 8.9, -33.4, 40.9, -2.5), SEa_3D=5.4),
                    9: dict(S1=(-0.4, -0.9, -0.7, 1.2, 0.1), SEa_3D=2.2)}
CLAIM_SCAUTOLOC_FINAL_VS_S1 = {3: (349, 2709, -830), 9: (510, 3881, -690)}   # horizontal m, too shallow m, dT ms
TOL_M_SMALL, TOL_M_LARGE, TOL_MS = 0.15, 1.5, 0.15   # tolerances: 1-decimal metre claims, integer claims, ms claims

# WGS84
A_WGS, F_WGS = 6378137.0, 1 / 298.257223563
E2 = F_WGS * (2 - F_WGS)


# ----------------------------------------------------------------------------- helpers
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def radii(lat_deg):
    s = math.sin(math.radians(lat_deg))
    w = 1 - E2 * s * s
    return A_WGS * (1 - E2) / w ** 1.5, A_WGS / math.sqrt(w)      # meridian M, prime vertical N


def d_enu(a, b):
    """a minus b (dicts with lat, lon, depth_km): east, north, up in metres on the local tangent plane."""
    lat_m = 0.5 * (a["lat"] + b["lat"])
    m, n = radii(lat_m)
    de = math.radians(a["lon"] - b["lon"]) * n * math.cos(math.radians(lat_m))
    dn = math.radians(a["lat"] - b["lat"]) * m
    du = -(a["depth_km"] - b["depth_km"]) * 1000.0
    return de, dn, du


def parse_t(s):
    """ISO time (with or without 'Z', ' ' or 'T') -> naive UTC datetime with microseconds."""
    s = str(s).strip().replace("Z", "").replace(" ", "T")
    if "+" in s[10:]:
        s = s[:10] + s[10:].split("+")[0]
    if "." in s:
        head, frac = s.split(".")
        frac = (frac + "000000")[:6]
        s = f"{head}.{frac}"
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")


def t_sql(value, us):
    t = parse_t(value)
    return t + dt.timedelta(microseconds=int(us or 0))


def diff(a, b):
    de, dn, du = d_enu(a, b)
    out = dict(dE_m=de, dN_m=dn, dU_m=du, dH_m=math.hypot(de, dn), d3D_m=math.sqrt(de * de + dn * dn + du * du))
    out["dT_ms"] = (a["time"] - b["time"]).total_seconds() * 1000.0 if a.get("time") and b.get("time") else None
    return out


def load_solution(name):
    path, idc, la, lo, de, tc = SOL_FILES[name]
    out = {}
    for r in csv.DictReader(open(path)):
        out[int(r[idc])] = dict(lat=float(r[la]), lon=float(r[lo]), depth_km=float(r[de]), time=parse_t(r[tc]))
    return out


def centroid_enu(sol):
    o = dict(lat=ORIGIN[0], lon=ORIGIN[1], depth_km=0.0)
    xs = [d_enu(sol[i], o) for i in REF_IDS]
    return tuple(statistics.fmean(x[k] for x in xs) for k in range(3))


def rel_diff(a, sol_a_frame, b, sol_b):
    """(a - centroid of its frame) minus (b - centroid of b's solution), east/north/up."""
    o = dict(lat=ORIGIN[0], lon=ORIGIN[1], depth_km=0.0)
    ca, cb = centroid_enu(sol_a_frame), centroid_enu(sol_b)
    pa, pb = d_enu(a, o), d_enu(b, o)
    d = [(pa[k] - ca[k]) - (pb[k] - cb[k]) for k in range(3)]
    return dict(dE_m=d[0], dN_m=d[1], dU_m=d[2], dH_m=math.hypot(d[0], d[1]), d3D_m=math.sqrt(sum(x * x for x in d)),
                dT_ms=None)


def q(con, sql):
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def parse_scrtdd_log(path):
    """Relocation blocks: input origin -> output origin, or failure."""
    blocks, cur, ignored = [], None, []
    for line in open(path, errors="replace"):
        m = re.search(r"Relocating origin (\S+) using profile (\S+)", line)
        if m:
            cur = dict(input=m.group(1), profile=m.group(2), output=None, failed=False, log_time=line[:19])
            blocks.append(cur)
            continue
        m = re.search(r"Ingoring origin (\S+) whose author is not accepted", line)
        if m:
            ignored.append(m.group(1))
        if cur is None:
            continue
        m = re.search(r"Sending origin (\S+)", line)
        if m and cur["output"] is None:
            cur["output"] = m.group(1)
        if "Cannot relocate origin" in line:
            cur["failed"] = True
    return blocks, ignored


def xml_ns(root):
    return root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""


def xml_rtdd_origin(path):
    """First RTDD origin of a SCML file: lat, lon, depth, time, phases of its arrivals."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    root = ET.parse(path).getroot()
    ns = xml_ns(root)
    for o in root.iter(f"{ns}origin"):
        mid = o.find(f"{ns}methodID")
        if mid is None or mid.text != "RTDD":
            continue
        ph = [a.find(f"{ns}phase").text for a in o.findall(f"{ns}arrival")]
        return dict(publicID=o.get("publicID"), lat=float(o.find(f"{ns}latitude/{ns}value").text),
                    lon=float(o.find(f"{ns}longitude/{ns}value").text),
                    depth_km=float(o.find(f"{ns}depth/{ns}value").text), time=parse_t(o.find(f"{ns}time/{ns}value").text),
                    n_P=ph.count("P"), n_S=ph.count("S"),
                    author=(o.find(f"{ns}creationInfo/{ns}author").text if o.find(f"{ns}creationInfo/{ns}author") is not None else None))
    return None


def xml_picks(path):
    root = ET.parse(path).getroot()
    ns = xml_ns(root)
    out = []
    for p in root.iter(f"{ns}pick"):
        w = p.find(f"{ns}waveformID")
        out.append(dict(publicID=p.get("publicID"), time=p.find(f"{ns}time/{ns}value").text,
                        sta=w.get("stationCode"), cha=w.get("channelCode"), method=p.find(f"{ns}methodID").text,
                        phase=(p.find(f"{ns}phaseHint").text if p.find(f"{ns}phaseHint") is not None else None)))
    return out


def check(label, got, claim, tol):
    if claim is None or got is None:
        return None
    ok = abs(got - claim) <= tol
    return dict(item=label, computed=round(got, 3), claimed=claim, tolerance=tol, agrees=ok)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    logpath = f"{LOGDIR}/verify_gwangyang_realtime_db_{'apply' if a.apply else 'dryrun'}_{stamp}.log"
    logf = open(logpath, "a")

    def log(*x):
        s = " ".join(str(v) for v in x)
        print(s, flush=True)
        logf.write(s + "\n")
        logf.flush()

    log(f"# verify_rt_db.py {'APPLY' if a.apply else 'DRY RUN'} {dt.datetime.now(dt.timezone.utc).isoformat()}; out {OUT}")
    for r in RUNS:
        db = f"{RTROOT}/{r}/db/seiscomp.sqlite"
        sizes = {s: (os.path.getsize(db + s) if os.path.exists(db + s) else None) for s in ("", "-wal", "-shm")}
        log(f"  {r}: {db} sizes {sizes}")
    if not a.apply:
        log("  dry run: nothing copied or written")
        return

    settings = dict(script=os.path.abspath(__file__), script_md5=md5(os.path.abspath(__file__)), runs=RUNS,
                    origin_for_centroids=ORIGIN, replay=REPLAY, ref_ids=REF_IDS, pick_window_s=PICK_WINDOW_S,
                    solutions={k: v[0] for k, v in SOL_FILES.items()}, step09=STEP09,
                    tolerances=dict(m_small=TOL_M_SMALL, m_large=TOL_M_LARGE, ms=TOL_MS),
                    conversion="local tangent plane on WGS84, radii of curvature at the mean latitude of each pair",
                    db_open="copy, sqlite URI mode=ro&immutable=1")
    json.dump(settings, open(f"{OUT}/verify_settings.json", "w"), indent=1)

    sols = {k: load_solution(k) for k in SOL_FILES}
    checks, count_rows, origin_rows, pos_rows, pick_rows, md5_rows = [], [], [], [], [], []
    per_run = {}

    for run in RUNS:
        rdir = f"{RTROOT}/{run}"
        db = f"{rdir}/db/seiscomp.sqlite"
        before = {s: (md5(db + s) if os.path.exists(db + s) else None) for s in ("", "-wal")}
        wal_size = os.path.getsize(db + "-wal") if os.path.exists(db + "-wal") else 0
        cdir = f"{OUT}/db_copies/{run}"
        os.makedirs(cdir, exist_ok=True)
        cpy = f"{cdir}/seiscomp.sqlite"
        shutil.copyfile(db, cpy)
        if wal_size:
            raise SystemExit(f"{run}: WAL file not empty ({wal_size} bytes): immutable read would miss data")
        con = sqlite3.connect(f"file:{cpy}?mode=ro&immutable=1", uri=True)
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("Pick", "Amplitude", "Origin", "Arrival", "Event", "OriginReference", "Magnitude")}
        picks = q(con, """SELECT po.publicID, p.time_value, p.time_value_ms, p.waveformID_stationCode AS sta,
                          p.waveformID_channelCode AS cha, p.methodID, p.phaseHint_code, p.creationInfo_author AS author
                          FROM Pick p JOIN PublicObject po ON po._oid = p._oid""")
        amps = q(con, "SELECT a.type, a.pickID FROM Amplitude a")
        origins = q(con, """SELECT po.publicID, o.time_value, o.time_value_ms, o.latitude_value AS lat,
                            o.longitude_value AS lon, o.depth_value AS depth_km, o.methodID, o.earthModelID,
                            o.evaluationMode, o.creationInfo_author AS author, o.creationInfo_creationTime AS ct,
                            o.creationInfo_creationTime_ms AS ct_ms, o.quality_usedPhaseCount AS used_phases,
                            o.quality_associatedPhaseCount AS assoc_phases
                            FROM Origin o JOIN PublicObject po ON po._oid = o._oid""")
        arr = q(con, """SELECT po.publicID AS originID, a.pickID, a.phase_code, a.weight
                        FROM Arrival a JOIN PublicObject po ON po._oid = a._parent_oid""")
        events = q(con, """SELECT po.publicID, e.preferredOriginID FROM Event e JOIN PublicObject po ON po._oid = e._oid""")
        orefs = q(con, """SELECT po.publicID AS eventID, r.originID FROM OriginReference r
                          JOIN PublicObject po ON po._oid = r._parent_oid""")
        con.close()
        after = {s: (md5(db + s) if os.path.exists(db + s) else None) for s in ("", "-wal")}
        md5_rows.append(dict(run=run, original_md5_before=before[""], original_md5_after=after[""],
                             copy_md5=md5(cpy), wal_bytes=wal_size, unchanged=before == after))

        for o in origins:
            o["time"] = t_sql(o["time_value"], o["time_value_ms"])
            o["created"] = t_sql(o["ct"], o["ct_ms"])
            ph = [x["phase_code"] for x in arr if x["originID"] == o["publicID"]]
            o["n_arr"], o["n_P"], o["n_S"] = len(ph), ph.count("P"), sum(1 for p in ph if p.startswith("S"))
            o["events"] = sorted({x["eventID"] for x in orefs if x["originID"] == o["publicID"]})
        for p in picks:
            p["t"] = t_sql(p["time_value"], p["time_value_ms"])
        by_author = {}
        for o in origins:
            k = f"{o['author']}|{o['methodID']}"
            by_author[k] = by_author.get(k, 0) + 1
        crow = dict(run=run, **counts, origins_by_author_method=json.dumps(by_author, sort_keys=True),
                    pick_methods=json.dumps({m: sum(1 for p in picks if p["methodID"] == m)
                                             for m in sorted({p["methodID"] for p in picks})}),
                    amplitude_types=json.dumps({t: sum(1 for x in amps if x["type"] == t)
                                                for t in sorted({x["type"] for x in amps})}),
                    events=json.dumps({e["publicID"]: e["preferredOriginID"] for e in events}))
        count_rows.append(crow)
        if run in CLAIM_COUNTS:
            for k, v in CLAIM_COUNTS[run].items():
                checks.append(dict(item=f"{run} {k} rows", computed=counts[k], claimed=v, tolerance=0,
                                   agrees=counts[k] == v))

        # relocation blocks from scrtdd.log
        blocks, ignored = parse_scrtdd_log(f"{rdir}/logs/scrtdd.log")
        out_to_in = {b["output"]: b["input"] for b in blocks if b["output"]}
        org = {o["publicID"]: o for o in origins}
        rtdd = [o for o in origins if o["methodID"] == "RTDD"]
        scrtdd_auth = [o for o in origins if str(o["author"]).startswith("scrtdd@")]
        problems = []
        if {o["publicID"] for o in rtdd} != {o["publicID"] for o in scrtdd_auth}:
            problems.append("RTDD methodID set differs from scrtdd-author set")
        for o in rtdd:
            src = out_to_in.get(o["publicID"])
            if src is None:
                problems.append(f"{o['publicID']}: no 'Sending origin' block in scrtdd.log")
                continue
            s = org.get(src)
            if s is None:
                problems.append(f"{o['publicID']}: input {src} not in database")
            elif not str(s["author"]).startswith("scautoloc@"):
                problems.append(f"{o['publicID']}: input author {s['author']}")
            elif s["events"] != o["events"]:
                problems.append(f"{o['publicID']}: event {o['events']} != input event {s['events']}")
        sent = [b for b in blocks if b["output"]]
        db_ids = {o["publicID"] for o in origins}
        problems += [f"sent {b['output']} not in database" for b in sent if b["output"] not in db_ids]
        inputs = [b["input"] for b in blocks]
        dup_inputs = sorted({x for x in inputs if inputs.count(x) > 1})

        # per event
        ev_info = {}
        for kma, rid in REPLAY.items():
            ot = parse_t(KMA_OT[kma])
            ev_org = [o for o in origins if o["time"] and abs((o["time"] - ot).total_seconds()) < 30]
            evids = sorted({e for o in ev_org for e in o["events"]})
            loc = sorted([o for o in ev_org if str(o["author"]).startswith("scautoloc@")], key=lambda o: o["created"])
            rt = sorted([o for o in ev_org if o["methodID"] == "RTDD"], key=lambda o: o["created"])
            pref = [e["preferredOriginID"] for e in events if e["publicID"] in evids]
            pref_kind = ["RTDD" if org[p]["methodID"] == "RTDD" else org[p]["methodID"] for p in pref if p in org]
            win = [p for p in picks if PICK_WINDOW_S[0] <= (p["t"] - ot).total_seconds() <= PICK_WINDOW_S[1]]
            ev_info[kma] = dict(rtdd_id=rid, events=evids, n_scautoloc=len(loc),
                                scautoloc_nP=[o["n_P"] for o in loc], scautoloc_nS=[o["n_S"] for o in loc],
                                n_RTDD=len(rt), RTDD_nP=[o["n_P"] for o in rt], RTDD_nS=[o["n_S"] for o in rt],
                                RTDD_authors=sorted({o["author"] for o in rt}),
                                RTDD_earthModel=sorted({str(o["earthModelID"]) for o in rt}),
                                preferred=pref, preferred_kind=pref_kind,
                                n_picks=len(win), n_DL3C=sum(1 for p in win if p["methodID"] == "DL3C"),
                                n_SDL3C=sum(1 for p in win if p["methodID"] == "SDL3C"))
            for o in loc + rt:
                origin_rows.append(dict(run=run, kma_id=kma, publicID=o["publicID"], author=o["author"],
                                        methodID=o["methodID"], earthModelID=o["earthModelID"],
                                        created=o["created"].isoformat(), time=o["time"].isoformat(), lat=o["lat"],
                                        lon=o["lon"], depth_km=o["depth_km"], n_arr=o["n_arr"], n_P=o["n_P"],
                                        n_S=o["n_S"], events="/".join(o["events"]),
                                        is_preferred=o["publicID"] in pref,
                                        relocated_from=out_to_in.get(o["publicID"], "")))
            # positions: the final RTDD origin of this event, plus the first one (paced runs)
            if rt:
                for label, o in (("RTDD_final", rt[-1]), ("RTDD_first", rt[0])):
                    a_ = dict(lat=o["lat"], lon=o["lon"], depth_km=o["depth_km"], time=o["time"])
                    src = org.get(out_to_in.get(o["publicID"]))
                    if src:
                        d = diff(a_, dict(lat=src["lat"], lon=src["lon"], depth_km=src["depth_km"], time=src["time"]))
                        pos_rows.append(dict(run=run, kma_id=kma, rtdd_id=rid, solution=label, origin=o["publicID"],
                                             versus="scautoloc_input", kind="absolute", input_nP=src["n_P"], **d))
                    for sname in ("S1", "R1f", "R1", "HypoDD_dtcc", "SEa", "SEm"):
                        b = sols[sname][rid]
                        d = diff(a_, b)
                        pos_rows.append(dict(run=run, kma_id=kma, rtdd_id=rid, solution=label, origin=o["publicID"],
                                             versus=sname, kind="absolute", **d))
                        if sname in ("R1f", "R1", "HypoDD_dtcc"):
                            d = rel_diff(a_, sols["S1"], b, sols[sname])
                            pos_rows.append(dict(run=run, kma_id=kma, rtdd_id=rid, solution=label,
                                                 origin=o["publicID"], versus=sname, kind="relative", **d))
            if loc:
                o = loc[-1]
                d = diff(dict(lat=o["lat"], lon=o["lon"], depth_km=o["depth_km"], time=o["time"]), sols["S1"][rid])
                pos_rows.append(dict(run=run, kma_id=kma, rtdd_id=rid, solution="scautoloc_final", origin=o["publicID"],
                                     versus="S1", kind="absolute", **d))

            # picks vs step 09 (exact time strings, same station / channel / method)
            p09 = xml_picks(f"{STEP09}/{kma}/picks.xml")
            key09 = sorted((p["sta"], p["cha"], p["method"], parse_t(p["time"]).isoformat()) for p in p09)
            keydb = sorted((p["sta"], p["cha"], p["methodID"], p["t"].isoformat()) for p in win)
            pick_rows.append(dict(run=run, kma_id=kma, n_db=len(keydb), n_step09=len(key09),
                                  identical_multiset=key09 == keydb,
                                  n_db_distinct=len(set(keydb)), n_step09_distinct=len(set(key09)),
                                  only_in_db=len(set(keydb) - set(key09)), only_in_step09=len(set(key09) - set(keydb)),
                                  n_DL3C=sum(1 for k in keydb if k[2] == "DL3C"),
                                  n_SDL3C=sum(1 for k in keydb if k[2] == "SDL3C")))
        per_run[run] = dict(counts=counts, by_author_method=by_author, relocation_blocks=blocks,
                            n_blocks=len(blocks), n_sent=len(sent), n_failed=sum(1 for b in blocks if b["failed"]),
                            ignored_own_origins=ignored, duplicate_inputs=dup_inputs, problems=problems,
                            n_RTDD_in_db=len(rtdd), events=ev_info)
        log(f"== {run}: counts {counts}; origins by author|method {by_author}")
        log(f"   scrtdd blocks {len(blocks)} (sent {len(sent)}, failed {per_run[run]['n_failed']}); "
            f"ignored own origins {len(ignored)}; duplicate inputs {dup_inputs}; problems {problems or 'none'}")
        for kma, e in ev_info.items():
            log(f"   {kma}: {e}")

    # claims on positions (RT2 = main run), plus 'identical in RT3/RT4/RT5'
    for (rid, versus, kind), cl in CLAIM_POS.items():
        r = [p for p in pos_rows if p["run"] == "RT2_filefeed" and p["rtdd_id"] == rid and p["solution"] == "RTDD_final"
             and p["versus"] == versus and p["kind"] == kind]
        if not r:
            checks.append(dict(item=f"RT2 ev{rid} vs {versus} {kind}", computed=None, claimed=cl, agrees=False))
            continue
        r = r[0]
        big = versus == "scautoloc_input" or (kind == "absolute" and cl[0] is None)
        tol = TOL_M_LARGE if big else TOL_M_SMALL
        for i, k in enumerate(("dE_m", "dN_m", "dU_m", "d3D_m")):
            c = check(f"RT2 ev{rid} RTDD_final vs {versus} {kind} {k}", r[k], cl[i], tol)
            if c:
                checks.append(c)
        if cl[4] is not None and r["dT_ms"] is not None:
            checks.append(check(f"RT2 ev{rid} RTDD_final vs {versus} {kind} dT_ms", r["dT_ms"], cl[4],
                                1.0 if versus == "scautoloc_input" else TOL_MS))
    for rid, (h, shallow, dtms) in CLAIM_SCAUTOLOC_FINAL_VS_S1.items():
        r = [p for p in pos_rows if p["run"] == "RT2_filefeed" and p["rtdd_id"] == rid and p["solution"] == "scautoloc_final"][0]
        checks.append(check(f"RT2 ev{rid} scautoloc_final vs S1 horizontal", r["dH_m"], h, TOL_M_LARGE))
        checks.append(check(f"RT2 ev{rid} scautoloc_final vs S1 too shallow", r["dU_m"], shallow, TOL_M_LARGE))
        checks.append(check(f"RT2 ev{rid} scautoloc_final vs S1 dT_ms", r["dT_ms"], dtms, 10.0))
    finals = {}
    for p in pos_rows:
        if p["solution"] == "RTDD_final" and p["versus"] == "S1":
            finals.setdefault(p["rtdd_id"], []).append((p["run"], round(p["d3D_m"], 3), p["origin"]))
    for rid, lst in finals.items():
        same = len({x[1] for x in lst}) == 1
        checks.append(dict(item=f"ev{rid} final RTDD vs S1 identical in all runs", computed=json.dumps(lst),
                           claimed="identical in RT3/RT4/RT5", tolerance=0.001, agrees=same))

    # offline --ep (RT2): P must equal the real-time RTDD origin; PS vs S1 and SEa
    off_rows = []
    for kma, rid in REPLAY.items():
        rt_final = [o for o in origin_rows if o["run"] == "RT2_filefeed" and o["kma_id"] == kma and o["methodID"] == "RTDD"]
        rtf = rt_final[-1]
        rta = dict(lat=rtf["lat"], lon=rtf["lon"], depth_km=rtf["depth_km"], time=parse_t(rtf["time"]))
        for var in ("P", "PS"):
            x = xml_rtdd_origin(f"{OFFLINE_RT2}/{kma}/{var}/relocated.xml")
            if x is None:
                off_rows.append(dict(kma_id=kma, variant=var, note="no RTDD origin in relocated.xml"))
                continue
            d_rt = diff(x, rta)
            d_s1 = diff(x, sols["S1"][rid])
            d_sea = diff(x, sols["SEa"][rid])
            off_rows.append(dict(kma_id=kma, rtdd_id=rid, variant=var, publicID=x["publicID"], author=x["author"],
                                 n_P=x["n_P"], n_S=x["n_S"], lat=x["lat"], lon=x["lon"], depth_km=x["depth_km"],
                                 time=x["time"].isoformat(), vs_realtime_3D_m=d_rt["d3D_m"], vs_realtime_dT_ms=d_rt["dT_ms"],
                                 vs_S1_dE=d_s1["dE_m"], vs_S1_dN=d_s1["dN_m"], vs_S1_dU=d_s1["dU_m"],
                                 vs_S1_3D=d_s1["d3D_m"], vs_S1_dT_ms=d_s1["dT_ms"], vs_SEa_3D=d_sea["d3D_m"]))
            if var == "P":
                checks.append(check(f"offline P ev{rid} vs real-time RTDD 3D m", d_rt["d3D_m"], 0.0, 0.005))
                checks.append(check(f"offline P ev{rid} vs real-time RTDD dT ms", d_rt["dT_ms"], 0.0, 0.0005))
            else:
                cl = CLAIM_OFFLINE_PS[rid]
                for i, k in enumerate(("dE_m", "dN_m", "dU_m", "d3D_m")):
                    checks.append(check(f"offline PS ev{rid} vs S1 {k}", d_s1[k], cl["S1"][i], TOL_M_SMALL))
                checks.append(check(f"offline PS ev{rid} vs S1 dT_ms", d_s1["dT_ms"], cl["S1"][4], TOL_MS))
                checks.append(check(f"offline PS ev{rid} vs SEa 3D", d_sea["d3D_m"], cl["SEa_3D"], TOL_M_SMALL))

    # leakage: offline-check origins (RT2 offline check ran 18:01-18:02 KST while RT3 was live) not in RT3's db
    off_ids = set()
    for f in glob.glob(f"{OFFLINE_RT2}/*/*/relocated.xml") + glob.glob(f"{OFFLINE_RT5_FAILED}/*/*/relocated.xml"):
        root = ET.parse(f).getroot() if os.path.getsize(f) else None
        if root is not None:
            ns = xml_ns(root)
            off_ids |= {o.get("publicID") for o in root.iter(f"{ns}origin")}
    rt3_ids = {o["publicID"] for o in origin_rows if o["run"] == "RT3_paced"}
    con3 = sqlite3.connect(f"file:{OUT}/db_copies/RT3_paced/seiscomp.sqlite?mode=ro&immutable=1", uri=True)
    all3 = {r[0] for r in con3.execute("SELECT po.publicID FROM Origin o JOIN PublicObject po ON po._oid = o._oid")}
    con3.close()
    leak = sorted(off_ids & all3)
    checks.append(dict(item="offline-check origins found in RT3 database", computed=len(leak), claimed=0, tolerance=0,
                       agrees=len(leak) == 0, detail=json.dumps(leak)))

    # picks claims
    for r in pick_rows:
        checks.append(dict(item=f"{r['run']} {r['kma_id']} picks identical to step 09 (multiset)",
                           computed=f"{r['n_db']} db / {r['n_step09']} step09; DL3C {r['n_DL3C']} SDL3C {r['n_SDL3C']}",
                           claimed="identical (112 / 85)", tolerance=0, agrees=bool(r["identical_multiset"])))

    # write
    def wcsv(name, rows):
        keys = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(f"{OUT}/{name}", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
            w.writeheader()
            for r in rows:
                w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})

    wcsv("verify_db_md5.csv", md5_rows)
    wcsv("verify_db_counts.csv", count_rows)
    wcsv("verify_origins.csv", origin_rows)
    wcsv("verify_positions.csv", pos_rows)
    wcsv("verify_picks_vs_step09.csv", pick_rows)
    wcsv("verify_offline_check.csv", off_rows)
    checks = [c for c in checks if c]
    wcsv("verify_checks.csv", checks)
    json.dump(dict(per_run=per_run, checks=checks, n_checks=len(checks), n_agree=sum(1 for c in checks if c["agrees"]),
                   offline=off_rows), open(f"{OUT}/verify_summary.json", "w"), indent=1, default=str)
    log(f"== md5: {md5_rows}")
    for r in pick_rows:
        log(f"   picks {r}")
    for r in off_rows:
        log(f"   offline {r}")
    bad = [c for c in checks if not c["agrees"]]
    log(f"== checks: {len(checks)}, agree {len(checks) - len(bad)}, disagree {len(bad)}")
    for c in bad:
        log(f"   DISAGREES: {c}")
    log(f"# done; log {logpath}")


if __name__ == "__main__":
    main()
