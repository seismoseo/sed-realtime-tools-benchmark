#!/usr/bin/env python
# rt_analyze.py -- step 10: what the real-time chain wrote into its database, compared with the offline results.
#
# Usage (env pyrtdd; read-only on every input; writes only <run>/results/ and realtime/comparison/):
#     source /home/msseo/miniforge3/etc/profile.d/conda.sh; conda activate pyrtdd
#     python -I rt_analyze.py --runs RT2_filefeed,RT3_paced            # dry run: lists the inputs it found
#     python -I rt_analyze.py --runs RT2_filefeed,RT3_paced --apply    # writes the tables
#
# Inputs per run (all produced by rt_chain.py):
#   db_dump/sql_*.csv      tables read back from <run>/db/seiscomp.sqlite (picks, amplitudes, origins, arrivals,
#                          events, origin references); db_dump/event_*.xml = scxmldump of each event (cross-check)
#   logs/scrtdd.log, scautoloc.log, scevent.log (SeisComP logs; their clock is LOCAL time = KST = UTC+9)
#   work/scrtdd/singleevent_*/step{1,2}/ (scrtdd --dump-diagnostics), logs/msrtsimul_<ev>.stderr (paced feed)
#   replays.json, network/after_stop.json, logs/scautopick_<ev>_<feed>.time.txt
# Reference positions (local east/north/up about 35.0000 N 127.7286 E with obspy gps2dist_azimuth, as steps 07/08):
#   S1  = scrtdd multi-event run (the reference catalog of this test minus the replayed events)
#   R1f = pyrtdd, same settings, band-pass really applied; R1 = stock pyrtdd (unfiltered cross-correlation)
#   HypoDD 02.dt.cc (origin_time_pha_datum); SEa / SEm = scrtdd offline single-event runs (leave-one-out catalogs,
#   PhaseNet+ P and S picks, HYPOINVERSE start) of step 08
# "Absolute" differences compare positions directly. "Catalog-relative" differences first subtract, in every
# solution, the centroid of the 9 reference events; this removes each solution's own frame shift (S1 sits 317 m W,
# 34 m N, 171 m deeper than HypoDD's centroid; R1 differs from S1 by about 0.5 km), so only the placement of the
# replayed event relative to its neighbours is compared.
# Paced-feed latencies (delays.csv), two sets of columns (added 2026-10-17 after the independent verification):
#   latency_<x>_after_origin_time_s                      (original) from the FINAL scautoloc (LOCSAT) origin time,
#                                                        mapped to wall time with median(wall release - next record
#                                                        begin) of msrtsimul's verbose record list;
#   latency_<x>_after_S1_origin_time_msrtsimul_clock_s   from S1's origin time, on msrtsimul's own clock: rt_simul
#                                                        starts its simulated clock at etime = end time of the FIRST
#                                                        record of <run>/data/<kma>_sorted.mseed, truncated to whole
#                                                        seconds, at wall time rtime ~ 'Starting msrtsimul at'; data
#                                                        time T is reached at wall time T + (rtime - etime).
#   Records are released when that clock reaches their end time truncated to whole seconds, i.e. 0-1 s before the
#   clock reaches the true record end; the median-release offset therefore sits ~0.5 s below the clock offset.
# summary.json records the md5 of this script (rt_analyze_md5).

import argparse
import glob
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from obspy import UTCDateTime
from obspy.geodetics import gps2dist_azimuth

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
REFT = f"{DATA}/reference_tables"
RTROOT = f"{PROJECT}/runs/gwangyang/realtime"
OUT_COMBINED = f"{RTROOT}/comparison"
ORIGIN = (35.0000, 127.7286)
REPLAY = {"20210827220322": 3, "20260202194119": 9}       # kma_id -> rtdd_id
KMA_OT = {"20210827220322": "2021-08-27T22:03:22Z", "20260202194119": "2026-02-02T19:41:19Z"}
REF_IDS = [i for i in range(1, 12) if i not in REPLAY.values()]
LOCAL_TZ = timezone(timedelta(hours=9))                  # SeisComP logs use local time (KST, no DST)
SOLUTIONS = {
    "S1": (f"{PROJECT}/runs/gwangyang/scrtdd/S1/work/reloc-event.csv", "id"),
    "R1f": (f"{PROJECT}/runs/gwangyang/pyrtdd/R1f_xcorr_like_reference_hypodd_like_filtered/relocated-event.csv", "id"),
    "R1": (f"{PROJECT}/runs/gwangyang/pyrtdd/R1_xcorr_like_reference_hypodd_like/relocated-event.csv", "id"),
    "HypoDD_dtcc": (f"{REFT}/hypodd_dtcc.csv", "rtdd_id"),
    "HYPOINVERSE": (f"{REFT}/hypoinverse_kim1983.csv", "rtdd_id"),
}
SE_RESULTS = {"SEa": f"{PROJECT}/runs/gwangyang/scrtdd/SEa/single_event_results.csv",
              "SEm": f"{PROJECT}/runs/gwangyang/scrtdd/SEm/single_event_results.csv"}
DL_OFFLINE = f"{PROJECT}/runs/gwangyang/dlpicker/analysis/dl_picks_all.csv"     # step 09 picks (all variants)
PICK_MATCH_S = 0.5


# ----------------------------------------------------------------------------- helpers
def enu(lat, lon, depth_km):
    e, n = [], []
    for la, lo in zip(np.atleast_1d(lat), np.atleast_1d(lon)):
        d, az, _ = gps2dist_azimuth(ORIGIN[0], ORIGIN[1], float(la), float(lo))
        e.append(d * np.sin(np.radians(az)))
        n.append(d * np.cos(np.radians(az)))
    return np.column_stack([e, n, -np.asarray(np.atleast_1d(depth_km), float) * 1000.0])


def t_sql(s, us):
    """SeisComP SQLite datetime + '_ms' column (microseconds) -> UTCDateTime."""
    return UTCDateTime(str(s).replace(" ", "T") + "Z") + (0 if pd.isna(us) else int(us) / 1e6)


def t_log(line):
    """'2026/10/17 17:49:43 [...' (local time) -> UTCDateTime."""
    m = re.match(r"(\d{4})/(\d\d)/(\d\d) (\d\d):(\d\d):(\d\d)", line)
    if not m:
        return None
    dt = datetime(*[int(x) for x in m.groups()], tzinfo=LOCAL_TZ).astimezone(timezone.utc)
    return UTCDateTime(dt)


def load_solution(name):
    path, idcol = SOLUTIONS[name]
    df = pd.read_csv(path)
    if name in ("HypoDD_dtcc",):
        lat, lon, dep, t = df.latitude, df.longitude, df.depth_km, df.origin_time_pha_datum
    elif name == "HYPOINVERSE":
        lat, lon, dep, t = df.latitude, df.longitude, df.depth_km, df.origin_time
    else:
        lat, lon, dep, t = df.latitude, df.longitude, df.depth, df.isotime
    out = pd.DataFrame({"id": df[idcol].astype(int), "lat": lat, "lon": lon, "depth_km": dep,
                        "time": [UTCDateTime(x) for x in t]})
    xyz = enu(out.lat, out.lon, out.depth_km)
    out["E"], out["N"], out["U"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    return out.set_index("id")


def load_se(name):
    df = pd.read_csv(SE_RESULTS[name])
    out = pd.DataFrame({"id": df.event_id.astype(int), "lat": df.reloc_latitude, "lon": df.reloc_longitude,
                        "depth_km": df.reloc_depth_km, "time": [UTCDateTime(x) for x in df.reloc_time]})
    xyz = enu(out.lat, out.lon, out.depth_km)
    out["E"], out["N"], out["U"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    return out.set_index("id")


def diff_row(a, b):
    """a, b: dicts with E, N, U (m) and time (UTCDateTime). a minus b."""
    d = np.array([a["E"] - b["E"], a["N"] - b["N"], a["U"] - b["U"]])
    return dict(dE_m=d[0], dN_m=d[1], dU_m=d[2], dH_m=float(np.hypot(d[0], d[1])), d3D_m=float(np.linalg.norm(d)),
                dT_ms=(a["time"] - b["time"]) * 1000.0)


# ----------------------------------------------------------------------------- per run
def parse_scrtdd_log(path):
    """One block per relocation, from 'Relocating origin' to 'Sending origin' / 'Cannot relocate'."""
    blocks, cur = [], None
    other = dict(ignored_author=0, skipped_nonpreferred=0, errors=[])
    for line in open(path, errors="replace"):
        if "[error" in line.lower():
            other["errors"].append(line.strip()[:300])
        if "whose author is not accepted" in line:
            other["ignored_author"] += 1
        if "Skipping non-preferred origin" in line:
            other["skipped_nonpreferred"] += 1
        m = re.search(r"Relocating origin (\S+) using profile (\S+)", line)
        if m:
            cur = dict(input_origin=m.group(1), profile=m.group(2), t_start=t_log(line), neighbours=[])
            blocks.append(cur)
            continue
        if cur is None:
            continue
        m = re.search(r"Found (\d+) neighbouring events", line)
        if m:
            cur["neighbours"].append(int(m.group(1)))
        for k in (1, 2):
            m = re.search(rf"Step {k} relocation successful, new location: lat (\S+) lon (\S+) depth (\S+) time (\S+)", line)
            if m:
                cur.update({f"step{k}_lat": float(m.group(1)), f"step{k}_lon": float(m.group(2)),
                            f"step{k}_depth_km": float(m.group(3)), f"step{k}_time": m.group(4)})
            if f"Failed to perform step {k}" in line:
                cur[f"step{k}_failed"] = line.strip()[:200]
        for ph in ("P", "S"):
            m = re.search(rf"Total {ph} phases CC attempted (\d+) failures \S+ \((\d+)\)\s+Above coeff threshold "
                          rf"\(([\d.]+)\) \S+ \((\d+)\)", line)
            if m:
                cur[f"cc_{ph}_attempted"], cur[f"cc_{ph}_failures"], cur[f"cc_{ph}_above"] = (
                    int(m.group(1)), int(m.group(2)), int(m.group(4)))
        m = re.search(r"Sending origin (\S+)", line)
        if m:
            cur["output_origin"], cur["t_sent"] = m.group(1), t_log(line)
        if "Cannot relocate origin" in line:
            cur["cannot_relocate"] = True
    return blocks, other


def diag_counts(run):
    """scrtdd --dump-diagnostics: per relocation folder, double differences by step, phase, xcorr use."""
    rows = []
    for d in sorted(glob.glob(f"{run}/work/scrtdd/singleevent_*")):
        for step in ("step1", "step2"):
            f = f"{d}/{step}/final-double-difference.csv"
            if not os.path.exists(f):
                continue
            df = pd.read_csv(f)
            for ph, g in df.groupby("phaseType"):
                xc = g.xcorrUsed.astype(str).str.lower().eq("true")
                rows.append(dict(folder=os.path.basename(d), step=step, phase=ph, n_dd=len(g),
                                 n_weight_gt0=int((g.weight > 0).sum()), n_xcorr_used=int(xc.sum()),
                                 n_xcorr_negative_cc=int((xc & (g.xcorrCoefficient < 0)).sum()),
                                 n_neighbours=g.eventId2.nunique(),
                                 median_abs_residual_ms=float(np.median(np.abs(g.doubleDifferenceResidual)) * 1000)
                                 if len(g) else np.nan,
                                 median_abs_residual_ms_weighted=float(np.median(np.abs(
                                     g.doubleDifferenceResidual[g.weight > 0])) * 1000) if (g.weight > 0).any() else np.nan))
    return pd.DataFrame(rows)


def step1_weighting(run):
    """For every relocation attempt: step 1's first-iteration residuals and libhdd's cut-off
    alpha*MAD/0.6745 (alpha = 10, the first value of solver.downWeightingByResidual), measured from ZERO as in
    solver.cpp:554-584; how many residuals lie beyond it and the summed weight scrtdd actually used."""
    rows = []
    for d in sorted(glob.glob(f"{run}/work/scrtdd/singleevent_*")):
        f = f"{d}/step1/initial-double-difference.csv"
        if not os.path.exists(f):
            continue
        df = pd.read_csv(f)
        r = df.doubleDifferenceResidual.to_numpy()
        med = float(np.median(r))
        mad = float(np.median(np.abs(r - med)))
        cut = 10 * mad / 0.67449
        step2 = os.path.exists(f"{d}/step2/final-double-difference.csv")
        rows.append(dict(folder=os.path.basename(d), n_dd=len(r), median_residual_ms=med * 1000, MAD_ms=mad * 1000,
                         cutoff_ms=cut * 1000, n_beyond_cutoff=int(np.sum(np.abs(r) > cut)),
                         n_weight_gt0=int((df.weight > 0).sum()), sum_weight=float(df.weight.sum()),
                         step2_completed=step2))
    return pd.DataFrame(rows)


def msrtsimul_offset(path):
    """Paced feed: wall-clock time minus data time for released records ('Starting msrtsimul at' + per-record
    seconds since start). A record is released once the simulated clock passes its last sample, so wall - end time
    of record ~ constant; the record end is taken as the next record's begin time on the same channel."""
    if not os.path.exists(path):
        return None
    start, recs = None, []
    for line in open(path, errors="replace"):
        m = re.match(r"Starting msrtsimul at (\S+ \S+)", line)
        if m:
            start = UTCDateTime(m.group(1).replace("+00:00", ""))
            continue
        p = line.split()
        if len(p) == 5 and p[0].count(".") == 3:
            recs.append((p[0], float(p[1]), UTCDateTime(f"{p[2]}T{p[3]}")))
    if start is None or not recs:
        return None
    df = pd.DataFrame(recs, columns=["nslc", "t_since_start", "begin"])
    df["wall"] = [start + x for x in df.t_since_start]
    df["next_begin"] = df.groupby("nslc").begin.shift(-1)
    ok = df.dropna(subset=["next_begin"])
    off = np.array([w - e for w, e in zip(ok.wall, ok.next_begin)])
    return dict(start=start, n_records=len(df), offset_median_s=float(np.median(off)),
                offset_p05_s=float(np.percentile(off, 5)), offset_p95_s=float(np.percentile(off, 95)), records=df)


def msrtsimul_clock(mseed_path, start):
    """msrtsimul's own simulated clock (software/seiscomp/bin/msrtsimul, rt_simul): etime = calendar.timegm of the
    END time of the first record (mseedlite: begin + nsamp/fsamp), i.e. truncated to whole seconds, set at wall time
    rtime (just after 'Starting msrtsimul at' = start). Data time T is reached at wall time T + (rtime - etime)."""
    from obspy.io.mseed.util import get_record_information
    info = get_record_information(mseed_path, offset=0)
    end_first = info["starttime"] + info["npts"] / info["samp_rate"]
    etime = UTCDateTime(int(end_first.timestamp))
    return dict(first_record_end=end_first, etime=etime, offset_s=float(start - etime))


def md5_file(path, block=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(block), b""):
            h.update(b)
    return h.hexdigest()


SCRIPT_MD5 = md5_file(os.path.abspath(__file__))   # this script as loaded (written into every summary.json)


def analyze_run(name, refs, se, apply):
    run = f"{RTROOT}/{name}"
    dd = f"{run}/db_dump"
    res = f"{run}/results"
    need = [f"{dd}/sql_{t}.csv" for t in ("picks", "amplitudes", "origins", "arrivals", "events", "origin_references")]
    missing = [p for p in need if not os.path.exists(p)]
    print(f"== {name}: inputs {'ok' if not missing else 'MISSING ' + str(missing)}")
    if missing or not apply:
        return None
    os.makedirs(res, exist_ok=True)
    picks = pd.read_csv(f"{dd}/sql_picks.csv")
    amps = pd.read_csv(f"{dd}/sql_amplitudes.csv")
    orgs = pd.read_csv(f"{dd}/sql_origins.csv")
    arrs = pd.read_csv(f"{dd}/sql_arrivals.csv")
    evs = pd.read_csv(f"{dd}/sql_events.csv")
    oref = pd.read_csv(f"{dd}/sql_origin_references.csv")
    picks["t"] = [t_sql(a, b) for a, b in zip(picks.time_value, picks.time_value_ms)]
    picks["created"] = [t_sql(a, b) for a, b in zip(picks.creationInfo_creationTime, picks.creationInfo_creationTime_ms)]
    orgs["t"] = [t_sql(a, b) for a, b in zip(orgs.time_value, orgs.time_value_ms)]
    orgs["created"] = [t_sql(a, b) for a, b in zip(orgs.creationInfo_creationTime, orgs.creationInfo_creationTime_ms)]
    evs["created"] = [t_sql(a, b) for a, b in zip(evs.creationInfo_creationTime, evs.creationInfo_creationTime_ms)]
    xyz = enu(orgs.latitude_value, orgs.longitude_value, orgs.depth_value)
    orgs["E"], orgs["N"], orgs["U"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    org_event = dict(zip(oref.originID, oref.eventID))
    orgs["eventID"] = orgs.publicID.map(org_event)

    # scxmldump cross-check: every origin of every dumped event is in the SQL table with the same coordinates
    xml_check = []
    for f in sorted(glob.glob(f"{dd}/event_*.xml")):
        root = ET.parse(f).getroot()
        ns = root.tag.split("}")[0] + "}"
        for o in root.iter(f"{ns}origin"):
            pid = o.get("publicID")
            lat = float(o.find(f"{ns}latitude/{ns}value").text)
            row = orgs[orgs.publicID == pid]
            xml_check.append(dict(file=os.path.basename(f), origin=pid, in_sql=len(row) == 1,
                                  same_lat=bool(len(row) == 1 and abs(row.latitude_value.iloc[0] - lat) < 1e-9),
                                  methodID=(o.find(f"{ns}methodID").text if o.find(f"{ns}methodID") is not None else None),
                                  n_arrivals_xml=len(o.findall(f"{ns}arrival"))))
    xml_check = pd.DataFrame(xml_check)

    # map DB events to the replayed KMA events by origin time
    kma_of_event = {}
    for _, e in evs.iterrows():
        pref = orgs[orgs.publicID == e.preferredOriginID]
        if len(pref):
            for k, ot in KMA_OT.items():
                if abs(pref.t.iloc[0] - UTCDateTime(ot)) < 30:
                    kma_of_event[e.publicID] = k
    orgs["kma_id"] = orgs.eventID.map(kma_of_event)

    # arrivals per origin
    arr_n = arrs.groupby(["originID", "phase_code"]).size().unstack(fill_value=0)
    arr_used = arrs[arrs.weight > 0].groupby("originID").size()
    orgs["n_arr_P"] = orgs.publicID.map(arr_n["P"] if "P" in arr_n else {}).fillna(0).astype(int)
    orgs["n_arr_S"] = orgs.publicID.map(arr_n["S"] if "S" in arr_n else {}).fillna(0).astype(int)
    orgs["n_arr_weight_gt0"] = orgs.publicID.map(arr_used).fillna(0).astype(int)

    # picks per replay: real-time DL picks vs the offline step-09 picks of the same model and file
    off = pd.read_csv(DL_OFFLINE)
    off = off[off.variant == "phasenet_original"]
    pick_rows = []
    for kma, rid in REPLAY.items():
        ot = UTCDateTime(KMA_OT[kma])
        rt = picks[(picks.t > ot - 200) & (picks.t < ot + 400)]
        of = off[off.kma_id.astype(str) == kma]
        oft = [UTCDateTime(str(x).replace(" ", "T").replace("+00:00", "Z")) for x in of.time]
        n_match, dts = 0, []
        for _, p in rt.iterrows():
            cand = [(abs(t - p.t), t - p.t) for t, s, m in zip(oft, of.station, of.method)
                    if s == p.waveformID_stationCode and m == p.methodID]
            if cand:
                best = min(cand)
                if best[0] <= PICK_MATCH_S:
                    n_match += 1
                    dts.append(best[1])
        amp_ev = amps[amps.pickID.isin(rt.publicID)]
        pick_rows.append(dict(kma_id=kma, rtdd_id=rid, n_rt_picks=len(rt), n_rt_DL3C=int((rt.methodID == "DL3C").sum()),
                              n_rt_SDL3C=int((rt.methodID == "SDL3C").sum()), n_offline_step09=len(of),
                              n_matched_within_0p5s=n_match,
                              max_abs_dt_s=float(np.max(np.abs(dts))) if dts else np.nan,
                              n_identical_times=int(np.sum(np.abs(dts) < 1e-6)) if dts else 0,
                              amplitudes=json.dumps(amp_ev.type.value_counts().to_dict()),
                              first_pick_created=min(rt.created) if len(rt) else None,
                              last_pick_created=max(rt.created) if len(rt) else None))
    pick_tab = pd.DataFrame(pick_rows)

    # origins table
    org_tab = orgs[["publicID", "eventID", "kma_id", "creationInfo_author", "methodID", "evaluationMode", "created", "t",
                    "latitude_value", "longitude_value", "depth_value", "depthType", "quality_usedPhaseCount",
                    "quality_associatedPhaseCount", "quality_standardError", "quality_azimuthalGap",
                    "quality_minimumDistance", "n_arr_P", "n_arr_S", "n_arr_weight_gt0"]].copy()
    org_tab = org_tab.sort_values("created")
    org_tab["is_preferred"] = org_tab.publicID.isin(evs.preferredOriginID)

    # scrtdd: one log block per relocation (input origin -> output origin)
    blocks, other = parse_scrtdd_log(f"{run}/logs/scrtdd.log")
    blk = pd.DataFrame(blocks)
    input_of = {b.get("output_origin"): b.get("input_origin") for b in blocks if b.get("output_origin")}

    # positions vs references
    pos_rows = []
    for kma, rid in REPLAY.items():
        sub = orgs[orgs.kma_id == kma].sort_values("created")
        loc = sub[sub.creationInfo_author.str.startswith("scautoloc")]
        rtdd = sub[sub.methodID == "RTDD"]
        cands = []
        if len(loc):
            cands += [("scautoloc_first", loc.iloc[0]), ("scautoloc_final", loc.iloc[-1])]
        for i, (_, r) in enumerate(rtdd.iterrows()):
            cands.append((f"RTDD_{i + 1}", r))
        for label, r in cands:
            a = dict(E=r.E, N=r.N, U=r.U, time=r.t)
            if r.publicID in input_of:   # how far scrtdd moved the scautoloc origin it relocated
                src = orgs[orgs.publicID == input_of[r.publicID]]
                if len(src):
                    row = dict(kma_id=kma, rtdd_id=rid, solution=label, origin=r.publicID, versus="scautoloc_input",
                               kind="absolute", input_origin=input_of[r.publicID])
                    row.update(diff_row(a, dict(E=src.E.iloc[0], N=src.N.iloc[0], U=src.U.iloc[0], time=src.t.iloc[0])))
                    pos_rows.append(row)
            for sname, sol in refs.items():
                if rid not in sol.index:
                    continue
                b = sol.loc[rid]
                row = dict(kma_id=kma, rtdd_id=rid, solution=label, origin=r.publicID, versus=sname, kind="absolute")
                row.update(diff_row(a, dict(E=b.E, N=b.N, U=b.U, time=b.time)))
                pos_rows.append(row)
                if sname in ("S1", "R1f", "R1", "HypoDD_dtcc"):
                    c_ref = sol.loc[REF_IDS, ["E", "N", "U"]].mean()     # centroid of the 9 reference events
                    c_cat = refs["S1"].loc[REF_IDS, ["E", "N", "U"]].mean()   # the reference catalog of this run = S1
                    ra = dict(E=a["E"] - c_cat.E, N=a["N"] - c_cat.N, U=a["U"] - c_cat.U, time=a["time"])
                    rb = dict(E=b.E - c_ref.E, N=b.N - c_ref.N, U=b.U - c_ref.U, time=b.time)
                    row = dict(kma_id=kma, rtdd_id=rid, solution=label, origin=r.publicID, versus=sname,
                               kind="catalog_relative")
                    row.update(diff_row(ra, rb))
                    row["dT_ms"] = np.nan
                    pos_rows.append(row)
            for sname, sol in se.items():
                if rid in sol.index:
                    b = sol.loc[rid]
                    row = dict(kma_id=kma, rtdd_id=rid, solution=label, origin=r.publicID, versus=sname, kind="absolute")
                    row.update(diff_row(a, dict(E=b.E, N=b.N, U=b.U, time=b.time)))
                    pos_rows.append(row)
    # offline cross-check (rt_offline_check.py): the same scautoloc origin relocated with scrtdd --ep, P only and P+S
    oc_path = f"{run}/offline_check/offline_check.csv"
    if os.path.exists(oc_path):
        oc = pd.read_csv(oc_path)
        for _, r in oc.iterrows():
            if pd.isna(r.get("reloc_lat")):
                continue
            rid = int(r.rtdd_id)
            xyz = enu([r.reloc_lat], [r.reloc_lon], [r.reloc_depth_km])[0]
            a = dict(E=xyz[0], N=xyz[1], U=xyz[2], time=UTCDateTime(r.reloc_time))
            label = f"offline_ep_{r.variant}"
            for sname, sol in list(refs.items()) + list(se.items()):
                if rid not in sol.index:
                    continue
                b = sol.loc[rid]
                row = dict(kma_id=str(r.kma_id), rtdd_id=rid, solution=label, origin=r.reloc_publicID, versus=sname,
                           kind="absolute")
                row.update(diff_row(a, dict(E=b.E, N=b.N, U=b.U, time=b.time)))
                pos_rows.append(row)
            rt = orgs[orgs.publicID == r.realtime_RTDD_origin]
            if len(rt):
                row = dict(kma_id=str(r.kma_id), rtdd_id=rid, solution=label, origin=r.reloc_publicID,
                           versus="realtime_RTDD", kind="absolute")
                row.update(diff_row(a, dict(E=rt.E.iloc[0], N=rt.N.iloc[0], U=rt.U.iloc[0], time=rt.t.iloc[0])))
                pos_rows.append(row)
    pos_tab = pd.DataFrame(pos_rows)

    diag = diag_counts(run)
    weighting = step1_weighting(run)

    # scautoloc: what happened to the picks
    al = open(f"{run}/logs/scautoloc.log", errors="replace").read()
    autoloc = dict(picks_processed=al.count("Processing pick "), xx_rejected=al.count("XX pick SNR"),
                   too_many_recent=len(re.findall(r"_tooManyRecentPicks: \S+\s+pick SNR", al)),
                   waiting_for_amplitude_lines=al.count("waiting for amplitude"),
                   low_snr_ignored=al.count("with low SNR"), origins_reported=al.count("Reported origin"),
                   origins_not_sent_no_improvement=al.count("not sent (no improvement)"))

    # scevent: preferred-origin decisions about the RTDD origins
    sev = open(f"{run}/logs/scevent.log", errors="replace").read().splitlines()
    rt_ids = set(orgs[orgs.methodID == "RTDD"].publicID)
    sev_lines = [l.strip()[:250] for l in sev if any(i in l for i in rt_ids) and
                 re.search(r"preferred|associated|cannot|rejected|priority|score", l, re.I)]
    sev_pref = [l.strip()[:250] for l in sev if re.search(r"[Pp]referred origin|set preferred|new preferred", l)]

    # delays from the creation times (UTC, database) and, for the paced feed, relative to the simulated real time
    del_rows = []
    for kma, rid in REPLAY.items():
        ot = UTCDateTime(KMA_OT[kma])
        sub = orgs[orgs.kma_id == kma].sort_values("created")
        if not len(sub):
            del_rows.append(dict(kma_id=kma, note="no origin in the database"))
            continue
        evid = sub.eventID.iloc[0]
        ev_created = evs[evs.publicID == evid].created.iloc[0]
        loc = sub[sub.creationInfo_author.str.startswith("scautoloc")]
        rtdd = sub[sub.methodID == "RTDD"]
        pref = evs[evs.publicID == evid].preferredOriginID.iloc[0]
        final_loc = loc.iloc[-1]
        used = arrs[arrs.originID == final_loc.publicID].pickID
        pk = picks[picks.publicID.isin(used)]
        rt = picks[(picks.t > ot - 200) & (picks.t < ot + 400)]
        row = dict(kma_id=kma, rtdd_id=rid, eventID=evid, preferred_origin=pref,
                   preferred_is_RTDD=bool(pref in set(rtdd.publicID)), n_scautoloc_origins=len(loc), n_RTDD_origins=len(rtdd),
                   first_DL_pick_created=min(rt.created), first_used_pick_created=min(pk.created),
                   last_used_pick_created=max(pk.created), first_origin_created=loc.created.iloc[0],
                   final_scautoloc_origin_created=final_loc.created, event_created=ev_created,
                   RTDD_created=(rtdd.created.iloc[0] if len(rtdd) else None))
        for i, (_, ro) in enumerate(rtdd.iterrows()):   # every relocated origin, with the origin it came from
            src = input_of.get(ro.publicID)
            srow = orgs[orgs.publicID == src]
            row[f"RTDD_{i + 1}_created"] = ro.created
            row[f"RTDD_{i + 1}_input_origin"] = src
            row[f"RTDD_{i + 1}_input_n_P"] = int(srow.n_arr_P.iloc[0]) if len(srow) else None
            row[f"RTDD_{i + 1}_minus_input_created_s"] = (ro.created - srow.created.iloc[0]) if len(srow) else None
        att = [b for b in blocks if b.get("input_origin") in set(sub.publicID)]
        row["scrtdd_attempts"] = len(att)
        row["scrtdd_failed_attempts"] = sum(1 for b in att if b.get("cannot_relocate"))
        row["scrtdd_failed_inputs"] = "/".join(b["input_origin"] for b in att if b.get("cannot_relocate"))
        row["scautoloc_versions_n_P"] = "/".join(str(x) for x in loc.n_arr_P)
        row["scautoloc_versions_created"] = "/".join(str(x)[11:23] for x in loc.created)
        row["final_origin_minus_last_used_pick_s"] = final_loc.created - max(pk.created)
        row["event_minus_first_origin_s"] = ev_created - loc.created.iloc[0]
        if len(rtdd):
            row["RTDD_minus_final_scautoloc_s"] = rtdd.created.iloc[0] - final_loc.created
            row["RTDD_minus_first_DL_pick_s"] = rtdd.created.iloc[0] - min(rt.created)
            b = [x for x in blocks if x.get("input_origin") == final_loc.publicID]
            if b and b[0].get("t_sent") and b[0].get("t_start"):
                row["scrtdd_relocation_log_s"] = b[0]["t_sent"] - b[0]["t_start"]
                row["scrtdd_wait_before_start_log_s"] = b[0]["t_start"] - final_loc.created
        # paced feed: the simulated clock of msrtsimul says when the origin time 'happened'
        ms = msrtsimul_offset(f"{run}/logs/msrtsimul_{kma}.stderr")
        if ms:
            ot_wall = ot + ms["offset_median_s"]
            hyp_ot = loc.t.iloc[-1]
            hyp_wall = hyp_ot + ms["offset_median_s"]
            row.update(msrtsimul_offset_median_s=ms["offset_median_s"], msrtsimul_offset_p05_p95_s=(
                round(ms["offset_p05_s"], 2), round(ms["offset_p95_s"], 2)), origin_time_wall=hyp_wall)
            for k in ["first_DL_pick_created", "first_used_pick_created", "last_used_pick_created",
                      "first_origin_created", "final_scautoloc_origin_created", "event_created", "RTDD_created"] + \
                     [f"RTDD_{i + 1}_created" for i in range(len(rtdd))]:
                if row.get(k) is not None:
                    row[f"latency_{k}_after_origin_time_s"] = row[k] - hyp_wall
            # per-pick latency: creation minus the release of the record that holds the pick time (same channel)
            rec = ms["records"]
            lat = []
            for _, p in rt.iterrows():
                nslc = f"{p.waveformID_networkCode}.{p.waveformID_stationCode}..{p.waveformID_channelCode}"
                r = rec[(rec.nslc == nslc) & (rec.begin <= p.t)]
                if len(r):
                    lat.append((p.methodID, p.created - r.wall.iloc[-1], p.created - (p.t + ms["offset_median_s"])))
            if lat:
                lt = pd.DataFrame(lat, columns=["method", "after_record", "after_pick_time"])
                for mth, g in lt.groupby("method"):
                    row[f"{mth}_latency_after_pick_time_median_s"] = float(g.after_pick_time.median())
                    row[f"{mth}_latency_after_pick_time_p90_s"] = float(g.after_pick_time.quantile(0.9))
                    row[f"{mth}_latency_after_pick_record_median_s"] = float(g.after_record.median())
            # the same latencies counted from S1's origin time on msrtsimul's own clock (see the header); the columns
            # above are kept unchanged (final scautoloc origin time, median-release offset)
            clk = msrtsimul_clock(f"{run}/data/{kma}_sorted.mseed", ms["start"])
            s1_ot = refs["S1"].loc[rid].time
            s1_wall = s1_ot + clk["offset_s"]
            row.update(latency_after_origin_time_reference="final scautoloc (LOCSAT) origin time + median(wall release "
                                                           "- next record begin) of msrtsimul's record list",
                       latency_after_S1_origin_time_reference="S1 origin time + msrtsimul clock offset (rtime - etime, "
                                                              "etime = first record end truncated to whole seconds)",
                       msrtsimul_start_wall=ms["start"], msrtsimul_first_record_end=clk["first_record_end"],
                       msrtsimul_clock_etime=clk["etime"], msrtsimul_clock_offset_s=clk["offset_s"],
                       msrtsimul_clock_offset_minus_median_offset_s=clk["offset_s"] - ms["offset_median_s"],
                       final_scautoloc_origin_time=hyp_ot, S1_origin_time=s1_ot,
                       final_scautoloc_origin_time_minus_S1_s=hyp_ot - s1_ot,
                       S1_origin_time_wall_msrtsimul_clock=s1_wall)
            for k in ["first_DL_pick_created", "first_used_pick_created", "last_used_pick_created",
                      "first_origin_created", "final_scautoloc_origin_created", "event_created", "RTDD_created"] + \
                     [f"RTDD_{i + 1}_created" for i in range(len(rtdd))]:
                if row.get(k) is not None:
                    row[f"latency_{k}_after_S1_origin_time_msrtsimul_clock_s"] = row[k] - s1_wall
            if lat:   # per pick: creation minus pick time, pick time mapped to wall time with msrtsimul's clock
                d_off = clk["offset_s"] - ms["offset_median_s"]
                for mth, g in lt.groupby("method"):
                    row[f"{mth}_latency_after_pick_time_msrtsimul_clock_median_s"] = float((g.after_pick_time - d_off).median())
                    row[f"{mth}_latency_after_pick_time_msrtsimul_clock_p90_s"] = float(
                        (g.after_pick_time - d_off).quantile(0.9))
        del_rows.append(row)
    del_tab = pd.DataFrame(del_rows)

    # cost
    stop = json.load(open(f"{run}/network/after_stop.json")) if os.path.exists(f"{run}/network/after_stop.json") else {}
    cost = {m: d.get("cpu_s") for m, d in stop.get("stop", {}).items()}
    for f in glob.glob(f"{run}/logs/scautopick_*.time.txt"):
        txt = open(f).read()
        u = float(re.search(r"User time \(seconds\): ([\d.]+)", txt).group(1))
        s = float(re.search(r"System time \(seconds\): ([\d.]+)", txt).group(1))
        w = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)", txt).group(1)
        cost[os.path.basename(f).replace(".time.txt", "")] = dict(cpu_s=round(u + s, 2), wall=w)

    # write
    pick_tab.to_csv(f"{res}/picks_vs_offline.csv", index=False)
    org_tab.to_csv(f"{res}/origins.csv", index=False)
    pos_tab.to_csv(f"{res}/positions_vs_reference.csv", index=False, float_format="%.3f")
    blk.to_csv(f"{res}/scrtdd_relocations.csv", index=False)
    diag.to_csv(f"{res}/scrtdd_diagnostics_dd_counts.csv", index=False)
    weighting.to_csv(f"{res}/scrtdd_step1_weighting.csv", index=False, float_format="%.2f")
    del_tab.to_csv(f"{res}/delays.csv", index=False)
    xml_check.to_csv(f"{res}/scxmldump_vs_sql.csv", index=False)
    summary = dict(run=name, generated=str(UTCDateTime()), db_counts=json.load(open(f"{dd}/db_counts.json")),
                   events=evs[["publicID", "preferredOriginID"]].to_dict("records"), kma_of_event=kma_of_event,
                   scxmldump_origins_checked=len(xml_check), scxmldump_all_in_sql_same_lat=bool(
                       len(xml_check) and xml_check.in_sql.all() and xml_check.same_lat.all()),
                   autoloc=autoloc, scrtdd_other=other, scevent_lines_about_RTDD=sev_lines[:40],
                   scevent_preferred_lines=sev_pref[:40], cost_cpu_s=cost,
                   rt_analyze_script=os.path.abspath(__file__), rt_analyze_md5=SCRIPT_MD5)
    with open(f"{res}/summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=str)
    print(f"   wrote {res}/: picks_vs_offline, origins, positions_vs_reference, scrtdd_relocations, "
          f"scrtdd_diagnostics_dd_counts, delays, scxmldump_vs_sql (.csv), summary.json")
    return dict(picks=pick_tab, origins=org_tab, positions=pos_tab, relocs=blk, diag=diag, delays=del_tab,
                summary=summary)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", default="RT2_filefeed,RT3_paced")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    refs = {k: load_solution(k) for k in SOLUTIONS}
    se = {k: load_se(k) for k in SE_RESULTS}
    print(f"reference solutions: { {k: len(v) for k, v in refs.items()} }; single-event offline: "
          f"{ {k: len(v) for k, v in se.items()} }")
    out = {}
    for r in a.runs.split(","):
        out[r] = analyze_run(r, refs, se, a.apply)
    if not a.apply:
        return
    os.makedirs(OUT_COMBINED, exist_ok=True)
    parts = [v["positions"].assign(run=k) for k, v in out.items() if v is not None and len(v["positions"])]
    if not parts:
        print("no positions in these runs (no origins); combined tables not written")
        return
    pos = pd.concat(parts)
    pos.to_csv(f"{OUT_COMBINED}/positions_vs_reference_all_runs.csv", index=False, float_format="%.3f")
    dl = pd.concat([v["delays"].assign(run=k) for k, v in out.items() if v is not None])
    dl.to_csv(f"{OUT_COMBINED}/delays_all_runs.csv", index=False)
    # compact view: RTDD and final scautoloc vs the main references
    key = pos[(pos.versus.isin(["S1", "R1f", "R1", "HypoDD_dtcc", "SEa", "SEm", "HYPOINVERSE"])) &
              (pos.solution.isin(["scautoloc_final", "RTDD_1"]))]
    key = key[["run", "kma_id", "rtdd_id", "solution", "versus", "kind", "dE_m", "dN_m", "dU_m", "dH_m", "d3D_m", "dT_ms"]]
    key.to_csv(f"{OUT_COMBINED}/key_position_differences.csv", index=False, float_format="%.2f")
    # context: how far the offline solutions themselves are from S1 / from each other for the two replayed events
    ctx = []
    for rid in REPLAY.values():
        a = refs["S1"].loc[rid]
        for sname in ("R1f", "R1", "HypoDD_dtcc", "SEa", "SEm"):
            sol = refs.get(sname, se.get(sname))
            b = sol.loc[rid]
            for kind in ("absolute", "catalog_relative"):
                if kind == "catalog_relative" and sname in ("SEa", "SEm"):
                    continue
                if kind == "absolute":
                    ra, rb = dict(a), dict(b)
                else:
                    ca = refs["S1"].loc[REF_IDS, ["E", "N", "U"]].mean()
                    cb = sol.loc[REF_IDS, ["E", "N", "U"]].mean()
                    ra = dict(E=a.E - ca.E, N=a.N - ca.N, U=a.U - ca.U, time=a.time)
                    rb = dict(E=b.E - cb.E, N=b.N - cb.N, U=b.U - cb.U, time=b.time)
                row = dict(rtdd_id=rid, solution="S1", versus=sname, kind=kind)
                row.update(diff_row(ra, rb))
                ctx.append(row)
    pd.DataFrame(ctx).to_csv(f"{OUT_COMBINED}/context_S1_vs_other_offline_solutions.csv", index=False, float_format="%.2f")
    # one machine-readable summary: per run and event, the key numbers of the notes
    summ = {}
    for k, v in out.items():
        if v is None:
            continue
        ev = {}
        for kma, rid in REPLAY.items():
            p_ = v["positions"]
            p_ = p_[(p_.kma_id.astype(str) == kma) & (p_.kind == "absolute")] if len(p_) else p_
            d_ = v["delays"][v["delays"].kma_id.astype(str) == kma]
            e = dict(rtdd_id=rid)
            pk = v["picks"][v["picks"].kma_id.astype(str) == kma]
            if len(pk):
                e.update(n_DL3C=int(pk.n_rt_DL3C.iloc[0]), n_SDL3C=int(pk.n_rt_SDL3C.iloc[0]),
                         picks_identical_to_step09=bool(pk.n_identical_times.iloc[0] == pk.n_rt_picks.iloc[0]
                                                        == pk.n_offline_step09.iloc[0]))
            for lab in sorted(set(p_.solution)) if len(p_) else []:
                for ref in ("S1", "R1f", "R1", "HypoDD_dtcc", "SEa", "scautoloc_input"):
                    r = p_[(p_.solution == lab) & (p_.versus == ref)]
                    if len(r):
                        e[f"{lab}_vs_{ref}_3D_m"] = round(float(r.d3D_m.iloc[0]), 2)
            if len(d_):
                for c in d_.columns:
                    if c.startswith(("n_", "scrtdd_", "latency_", "preferred_is", "RTDD_minus", "event_minus",
                                     "final_origin_minus", "DL3C_", "SDL3C_", "msrtsimul_clock_offset",
                                     "final_scautoloc_origin_time_minus_S1")):
                        val = d_[c].iloc[0]
                        if hasattr(val, "item"):   # numpy scalar -> plain Python value (json would write a string)
                            val = val.item()
                        if isinstance(val, (float, np.floating)) and not np.isnan(val):
                            val = round(float(val), 3)
                        e[c] = None if (isinstance(val, float) and np.isnan(val)) else val
            ev[kma] = e
        summ[k] = dict(events=ev, db_counts=v["summary"]["db_counts"], cost_cpu_s=v["summary"]["cost_cpu_s"],
                       scrtdd_ignored_own_origin=v["summary"]["scrtdd_other"]["ignored_author"],
                       scautoloc=v["summary"]["autoloc"])
    with open(f"{OUT_COMBINED}/summary_all_runs.json", "w") as f:
        json.dump(summ, f, indent=1, default=str)
    print(f"wrote {OUT_COMBINED}/positions_vs_reference_all_runs.csv, delays_all_runs.csv, key_position_differences.csv, "
          f"context_S1_vs_other_offline_solutions.csv, summary_all_runs.json")


if __name__ == "__main__":
    main()
