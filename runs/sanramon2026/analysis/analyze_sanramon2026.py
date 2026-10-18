#!/usr/bin/env python
# analyze_sanramon2026.py -- comparisons of the San Ramon 2025-26 rtDD relocations (pyrtdd P0/P1, scrtdd S0/S1) with
# the reference catalogs, and of the runs with each other. Read-only on the run folders; writes
# runs/sanramon2026/analysis/.
#
# COPY (2026-10-18) of runs/sanramon/analysis/analyze_sanramon.py (2015; not modified). The metric code (compare,
# plane_fit, dd_stats, xcorr_stats, xcorr_log_summary, run vs run, P1 vs S1 triplets) is unchanged. Changed:
#   * paths (data/sanramon_2026, runs/sanramon2026) and the projection centre (2025-26 swarm centre 37.757 N,
#     -121.940 E); only the runs of this case (P0, P1, S0, S1) and their pairs;
#   * references: LDEO = the LDEO real-time DD catalog NCAeqDDRT.v202201 (DDRT-3.0 rows only; geoid depths; formal
#     95 % errors ex/ey/ez) = PRIMARY (2015: the LDEO base catalog NCAeqDD.v202112.1); NCEDC = NCEDC DD (DD-RT), depths
#     converted to sea level with each event's NCSS datum, as in 2015 = SECONDARY;
#   * dropped_events(): the shared-phase count now applies the clustering's station filters (station <= 120 km from
#     the neighbour, maxEvStaDist of this case; station / inter-event distance >= 3; 3-D distances as libhdd's
#     computeDistance, station depth = -elevation), and every row carries the NCSS review flag;
#   * NEW (g): metrics split by NCSS review status (event_id_map.csv review_version: 'F' analyst-reviewed, 'A'/'H'
#     automatic picks only, 'I'); computed from the per-event errors of the full comparison (centroids and reference
#     neighbours from all common events), so the groups are directly comparable with the full-set numbers;
#   * NEW (h): events that left the travel-time grid in some iteration (libhdd "TTT: n/n queries failed for Event")
#     and events whose final depth is above sea level or that moved > 5 km from the start;
#   * NEW: the 2015 P1 and the 2025-26 P1 in one frame (compare_with_2015()): each P1 catalog is shifted by its own
#     centroid offset against its LDEO reference on the common events (2015: LDEO NCAeqDD.v202112.1; 2025-26: LDEO
#     DD-RT, whose real-time solutions are tied to the same DD202112.1 base catalog and the same geoid datum), then
#     both are projected into this script's frame; the 2015 P1 plane (SVD) defines along-strike / fault-normal axes.
#     The same is done with the two LDEO catalogs themselves as a check, and with NCEDC DD-based offsets as a second
#     check of the frame.
#
# Solutions read (each only if it exists):
#   NCSS     NCSS routine locations = rtDD start (inputs/rtdd_catalog/event.csv; geoid depth)
#   P0 P1    runs/sanramon2026/pyrtdd/<run>/relocated-event.csv
#   S0 S1    runs/sanramon2026/scrtdd/<run>/work/reloc-event.csv
# References:
#   LDEO     LDEO DD-RT NCAeqDDRT.v202201 (reference_tables/ldeo_ddrt_catalog.csv, is_dd rows), geoid depths (PRIMARY)
#   NCEDC    NCEDC DD = DD-RT (reference_tables/dd_catalog.csv); depths are below the local model surface: converted
#            to sea level with each event's NCSS datum (ncss_catalog.csv depth_datum_m), depth_sl = depth - datum/1000
#            (docs/sanramon2026_inputs.md 2.1, 3.3) (SECONDARY)
# All depths compared are km below sea level (rtDD depths are relative to the NLL grids, whose z = 0 is sea level).
# Positions -> local metres (E, N, U = -depth) with a transverse Mercator projection centred on the swarm
# (37.757 N, -121.940 E, WGS-84), so horizontal distances are true to < 1 mm over the swarm.
#
# Metrics per (solution, reference), on a COMMON event set (events relocated by every main solution
# P0, P1, S0, S1 that exist AND present in the reference), so all solutions are judged on the same events:
#   (a) relative geometry: d_i = (x_i - mean x) - (r_i - mean r); median and 90th percentile of |d_h| and |d_v|
#       (and 3-D); also a robust variant with the median offset removed instead of the means. Local relative
#       geometry: for each event, the vectors to its K=10 nearest neighbours IN THE REFERENCE (3-D), ours vs
#       reference; per event the median |difference| (horizontal, vertical); then the median and 90th percentile
#       over events.
#   (b) centroid shift: mean x - mean r (E, N, U), and the median per-event absolute offset.
#   (c) improvement ratio: metric(NCSS start) / metric(solution) for the medians of (a); > 1 means the solution is
#       closer to the reference than the start; and the fraction of events whose (a) 3-D error is smaller than
#       NCSS's.
#   (d) fault structure: plane fit by SVD of the centred coordinates of the common events (normal = smallest
#       singular vector): strike (right-hand rule) / dip, RMS distance from the plane ("thickness"), median absolute
#       distance, and the RMS spreads along strike and down dip. Also on each catalog's own full event set.
#   (e) events relocated / dropped and why (reconstructed for the dropped events: picks and candidate neighbours).
#   (f) cross-correlation statistics and double-difference residuals (initial / final) from libhdd's own files.
#   (g) the per-event numbers of (a)-(c) split by NCSS review status.
#   (h) grid escapes and large moves.
# Run against run (relative = median offset removed; absolute 3-D distance): P0 vs S0, P1 vs S1, P0 vs P1, S0 vs
# S1, NCSS vs P0/P1, and P1 vs S1 cross-correlation measurements triplet by triplet.
# Runtime / memory of every run from run_info.json / run_summary.json and the /usr/bin/time logs.
#
# Usage (env pyrtdd): python -I analyze_sanramon2026.py

import glob
import json
import os
import re

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
SR = f"{PROJECT}/data/sanramon_2026"
TAB = f"{SR}/reference_tables"
RUNS = f"{PROJECT}/runs/sanramon2026"
OUT = f"{RUNS}/analysis"
LOGS = f"{PROJECT}/logs"
LAT0, LON0 = 37.757, -121.940                 # 2025-26 swarm centre (sr_common.LAT0, LON0)
MAX_EVSTA_KM = 120.0                          # clustering maxEvStaDist of this case
RATIO = 3.0                                   # clustering minEvStaToInterEvRatio (libhdd default)
SR2015 = f"{PROJECT}/data/sanramon_2015"
RUNS2015 = f"{PROJECT}/runs/sanramon"
K_NEIGH = 10
MAIN = ["P0", "P1", "S0", "S1"]               # the common event set is built from these (those that exist)
PY_RUNS = ["P0", "P1"]
SC_RUNS = ["S0", "S1"]
PAIRS = [("P0", "S0"), ("P1", "S1"), ("P0", "P1"), ("S0", "S1"), ("NCSS", "P0"), ("NCSS", "P1"), ("NCSS", "S0"),
         ("NCSS", "S1")]
TM = Transformer.from_crs("EPSG:4326", f"+proj=tmerc +lat_0={LAT0} +lon_0={LON0} +k=1 +x_0=0 +y_0=0 +ellps=WGS84",
                          always_xy=True)


def enu(df):
    e, n = TM.transform(df.longitude.values, df.latitude.values)
    out = df.copy()
    out["E"], out["N"], out["U"] = e, n, -df.depth.values * 1000.0
    return out


def load_solutions():
    sols = {}
    ev = pd.read_csv(f"{SR}/inputs/rtdd_catalog/event.csv")
    sols["NCSS"] = enu(ev[["id", "isotime", "latitude", "longitude", "depth"]])
    for r in PY_RUNS:
        f = f"{RUNS}/pyrtdd/{r}/relocated-event.csv"
        if os.path.exists(f):
            sols[r] = enu(pd.read_csv(f))
    for r in SC_RUNS:
        f = f"{RUNS}/scrtdd/{r}/work/reloc-event.csv"
        if os.path.exists(f):
            sols[r] = enu(pd.read_csv(f))
    return sols


def load_references():
    ldeo = pd.read_csv(f"{TAB}/ldeo_ddrt_catalog.csv")
    ldeo = ldeo[ldeo.is_dd]                                   # DDRT-3.0 rows only (2 'HINV' rows = NCSS copies)
    ldeo = ldeo.rename(columns={"event_id": "id", "depth_km": "depth"})
    nc = pd.read_csv(f"{TAB}/dd_catalog.csv").rename(columns={"event_id": "id", "depth_km": "depth_model"})
    ncss = pd.read_csv(f"{TAB}/ncss_catalog.csv")
    nc = nc.merge(ncss[["event_id", "depth_datum_m"]].rename(columns={"event_id": "id"}), on="id", how="left")
    nc["depth"] = nc.depth_model - nc.depth_datum_m / 1000.0
    n_nodatum = int(nc.depth_datum_m.isna().sum())
    nc = nc[nc.depth.notna()]
    refs = {"LDEO": enu(ldeo[["id", "latitude", "longitude", "depth", "ex_km", "ey_km", "ez_km"]]),
            "NCEDC": enu(nc[["id", "latitude", "longitude", "depth", "depth_model", "depth_datum_m"]])}
    return refs, n_nodatum


def plane_fit(xyz):
    """SVD plane: strike (RHR), dip, RMS / median abs distance from plane, RMS spread along strike / dip."""
    c = xyz - xyz.mean(axis=0)
    u, s, vt = np.linalg.svd(c, full_matrices=False)
    n = vt[2].copy()
    if n[2] < 0:
        n = -n                                   # upward normal; its horizontal part points down-dip
    dip = float(np.degrees(np.arccos(min(1.0, abs(n[2])))))
    dipdir = float(np.degrees(np.arctan2(n[0], n[1])) % 360)
    strike = (dipdir - 90.0) % 360
    dist = c @ n
    # in-plane axes: strike direction (horizontal) and down-dip direction
    sv = np.array([np.sin(np.radians(strike)), np.cos(np.radians(strike)), 0.0])
    dv = np.cross(n, sv)
    if dv[2] > 0:
        dv = -dv
    return dict(strike=round(strike, 1), dip=round(dip, 1), dip_direction=round(dipdir, 1),
                thickness_rms_m=float(np.sqrt(np.mean(dist ** 2))), median_abs_dist_m=float(np.median(np.abs(dist))),
                p90_abs_dist_m=float(np.quantile(np.abs(dist), 0.9)),
                spread_along_strike_rms_m=float(np.sqrt(np.mean((c @ sv) ** 2))),
                spread_down_dip_rms_m=float(np.sqrt(np.mean((c @ dv) ** 2))), n=int(len(xyz)))


def compare(sol, ref, ids):
    """(a)-(c) inputs for one solution against one reference on the event ids 'ids'. Returns summary dict and
    per-event frame."""
    a = sol.set_index("id").loc[ids, ["E", "N", "U"]].values
    r = ref.set_index("id").loc[ids, ["E", "N", "U"]].values
    cen = a.mean(axis=0) - r.mean(axis=0)
    d = (a - a.mean(axis=0)) - (r - r.mean(axis=0))
    dm = (a - r) - np.median(a - r, axis=0)          # robust variant: median offset removed instead of the means
    dh = np.hypot(d[:, 0], d[:, 1])
    dv = np.abs(d[:, 2])
    d3 = np.sqrt(dh ** 2 + dv ** 2)
    absd = a - r
    tree = cKDTree(r)
    _, nb = tree.query(r, k=K_NEIGH + 1)
    nb = nb[:, 1:]
    va = a[nb] - a[:, None, :]
    vr = r[nb] - r[:, None, :]
    dvv = va - vr
    lh = np.median(np.hypot(dvv[..., 0], dvv[..., 1]), axis=1)
    lv = np.median(np.abs(dvv[..., 2]), axis=1)
    nbd = np.median(np.linalg.norm(vr, axis=2), axis=1)
    per = pd.DataFrame(dict(id=ids, dE_rel_m=d[:, 0], dN_rel_m=d[:, 1], dU_rel_m=d[:, 2], dh_rel_m=dh, dv_rel_m=dv,
                            d3_rel_m=d3, dE_abs_m=absd[:, 0], dN_abs_m=absd[:, 1], dU_abs_m=absd[:, 2],
                            local_dh_med_m=lh, local_dv_med_m=lv, ref_neighbour_dist_med_m=nbd))
    q = lambda x, p: float(np.quantile(x, p))
    summ = dict(n=len(ids),
                rel_h_median_m=q(dh, .5), rel_h_p90_m=q(dh, .9), rel_v_median_m=q(dv, .5), rel_v_p90_m=q(dv, .9),
                rel_3d_median_m=q(d3, .5), rel_3d_p90_m=q(d3, .9),
                rel_h_median_m_mediancentred=q(np.hypot(dm[:, 0], dm[:, 1]), .5),
                rel_v_median_m_mediancentred=q(np.abs(dm[:, 2]), .5),
                local_h_median_m=q(lh, .5), local_h_p90_m=q(lh, .9), local_v_median_m=q(lv, .5),
                local_v_p90_m=q(lv, .9), ref_neighbour_dist_median_m=q(nbd, .5),
                centroid_shift_E_m=float(cen[0]), centroid_shift_N_m=float(cen[1]), centroid_shift_U_m=float(cen[2]),
                centroid_shift_h_m=float(np.hypot(cen[0], cen[1])),
                abs_h_median_m=q(np.hypot(absd[:, 0], absd[:, 1]), .5), abs_v_median_m=q(np.abs(absd[:, 2]), .5))
    return summ, per


def dd_stats(path):
    """libhdd double-difference file -> statistics (residuals in ms)."""
    if not path or not os.path.exists(path):
        return {}
    d = pd.read_csv(path, dtype={"locationCode": str}, keep_default_na=False)
    d["xc"] = d.xcorrUsed.astype(str).str.lower() == "true"
    d["res_ms"] = d.doubleDifferenceResidual.astype(float) * 1000.0
    out = {}
    for name, g in (("all", d), ("xcorr", d[d.xc]), ("catalog", d[~d.xc])):
        w = g[g.weight.astype(float) > 0]
        rms = lambda x: float(np.sqrt(np.mean(x ** 2))) if len(x) else np.nan
        out[name] = dict(n=int(len(g)), n_weight_gt0=int(len(w)), rms_ms=rms(g.res_ms), rms_weight_gt0_ms=rms(w.res_ms),
                         median_ms=float(g.res_ms.median()) if len(g) else np.nan,
                         mad_ms=float((g.res_ms - g.res_ms.median()).abs().median()) if len(g) else np.nan,
                         weighted_rms_ms=float(np.sqrt(np.sum(w.weight.astype(float) * w.res_ms ** 2) /
                                                       np.sum(w.weight.astype(float)))) if len(w) else np.nan)
        for ph in ("P", "S"):
            gp = g[g.phaseType == ph]
            out[name][f"n_{ph}"] = int(len(gp))
            out[name][f"rms_{ph}_ms"] = rms(gp.res_ms)
    return out


def xcorr_stats(path, minc=0.7):
    if not path or not os.path.exists(path):
        return {}
    x = pd.read_csv(path, dtype={"locationCode": str}, keep_default_na=False)
    x["valid"] = x.valid.astype(str).str.lower() == "true"
    out = {}
    for ph, g in list(x.groupby("phaseType")) + [("all", x)]:
        v = g[g.valid]
        out[ph] = dict(entries=int(len(g)), valid=int(len(v)),
                       abs_cc_ge=int((v.coefficient.abs() >= minc).sum()),
                       cc_ge_pos=int((v.coefficient >= minc).sum()), cc_le_neg=int((v.coefficient <= -minc).sum()),
                       frac_abs_cc_ge_of_valid=float((v.coefficient.abs() >= minc).mean()) if len(v) else np.nan,
                       median_abs_cc_valid=float(v.coefficient.abs().median()) if len(v) else np.nan,
                       lag_abs_median_ms_ge=float((v[v.coefficient.abs() >= minc].lag.abs() * 1000).median())
                       if len(v) else np.nan,
                       lag_abs_p95_ms_ge=float((v[v.coefficient.abs() >= minc].lag.abs() * 1000).quantile(.95))
                       if len(v) else np.nan)
    return out


def xcorr_log_summary(path):
    """libhdd's own cross-correlation summary lines (console.log / scrtdd.log)."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    txt = open(path, errors="replace").read()
    m = re.findall(r"Catalog waveform data: waveforms downloaded (\d+), not available (\d+), loaded from disk cache (\d+)", txt)
    if m:
        out.update(waveforms_loaded=int(m[-1][0]), waveforms_not_available=int(m[-1][1]),
                   waveforms_from_disk_cache=int(m[-1][2]))
    for ph in ("P", "S"):
        m = re.findall(rf"Total {ph} phases CC attempted (\d+) failures ([\d.]+)% \((\d+)\) Above coeff threshold "
                       rf"\(([\d.]+)\) ([\d.]+)% \((\d+)\)", txt)
        if m:
            a = m[-1]
            out.update({f"{ph}_cc_attempted": int(a[0]), f"{ph}_cc_failed": int(a[2]),
                        f"{ph}_cc_above_threshold": int(a[5]), f"{ph}_cc_above_threshold_pct": float(a[4])})
    return out


def run_files(run):
    if run.startswith("P"):
        d = f"{RUNS}/pyrtdd/{run}"
        return dict(initial=f"{d}/processing/cluster-1-initial-double-difference.csv",
                    final=f"{d}/processing/cluster-1-final-double-difference.csv",
                    xcorr=f"{d}/xcorr_cache.csv" if os.path.exists(f"{d}/xcorr_cache.csv") else None,
                    pair=f"{d}/processing/cluster-1-pair.csv", log=f"{d}/console.log",
                    ncl=len(glob.glob(f"{d}/processing/cluster-*-pair.csv")))
    g = glob.glob(f"{RUNS}/scrtdd/{run}/work/multievent_*")
    d = g[0] if g else ""
    return dict(initial=f"{d}/cluster-1-initial-double-difference.csv", final=f"{d}/cluster-1-final-double-difference.csv",
                xcorr=f"{d}/xcorr.csv", pair=f"{d}/cluster-1-pair.csv", log=f"{RUNS}/scrtdd/{run}/work/scrtdd.log",
                ncl=len(glob.glob(f"{d}/cluster-*-pair.csv")))


def runtime(run):
    out = dict(run=run)
    if run.startswith("P"):
        f = f"{RUNS}/pyrtdd/{run}/run_info.json"
        if os.path.exists(f):
            j = json.load(open(f))
            out.update(wall_s=j.get("wall_time_s"), clustering_s=j.get("clustering_s"),
                       relocation_incl_xcorr_s=j.get("relocation_incl_xcorr_s"),
                       proxy_traces_processed=j.get("proxy_traces_processed"),
                       proxy_traces_failed=j.get("proxy_traces_failed"))
        t = f"{LOGS}/13_sanramon2026_pyrtdd_{run}_console.log"
        if os.path.exists(t):
            txt = open(t).read()
            m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", txt)
            out["peak_rss_mb"] = round(int(m.group(1)) / 1024, 1) if m else None
            m = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)", txt)
            out["process_wall"] = m.group(1) if m else None
            m = re.search(r"User time \(seconds\): ([\d.]+)", txt)
            out["cpu_user_s"] = float(m.group(1)) if m else None
    else:
        f = f"{RUNS}/scrtdd/{run}/run_summary.json"
        if os.path.exists(f):
            j = json.load(open(f))
            tv = j.get("time_v", {})
            out.update(wall_s=j.get("wall_s"), exit_code=j.get("exit_code"),
                       peak_rss_mb=round(int(tv["max_rss_kb"]) / 1024, 1) if tv.get("max_rss_kb") else None,
                       process_wall=tv.get("wall"), cpu_user_s=float(tv["user_s"]) if tv.get("user_s") else None)
    return out


def review_map():
    """NCSS review flag per event (event_id_map.csv): 'F' analyst-reviewed, 'A'/'H' automatic picks only, 'I'."""
    m = pd.read_csv(f"{TAB}/event_id_map.csv")
    m["review_group"] = m.review_version.map({"F": "F (analyst)", "A": "A/H (automatic only)",
                                              "H": "A/H (automatic only)", "I": "I"})
    return m.set_index("rtdd_id")


def station_enu():
    sta = pd.read_csv(f"{SR}/inputs/rtdd_catalog/station.csv", dtype={"locationCode": str}, keep_default_na=False)
    e, n = TM.transform(sta.longitude.values, sta.latitude.values)
    sid = sta.networkCode + "." + sta.stationCode + "." + sta.locationCode
    return {k: np.array([x, y, z]) for k, x, y, z in zip(sid, e, n, sta.elevation.values.astype(float))}


def dropped_events(sols, run, clustering):
    """Events of the input catalog not relocated by 'run', with the facts needed to say why. Shared phases are
    counted as libhdd's clustering counts them (clustering.cpp selectNeighbouringEvents): a phase (station, type)
    of the event and of a candidate neighbour within 5 km counts if the station is <= MAX_EVSTA_KM from both events
    and station distance / inter-event distance >= RATIO for both (3-D distances at the NCSS start positions,
    station depth = -elevation, as libhdd computeDistance)."""
    ph = pd.read_csv(f"{SR}/inputs/rtdd_catalog/phase.csv", dtype=str, keep_default_na=False)
    used = pd.read_csv(f"{SR}/inputs/nll_con_tm/stations_used.csv", dtype={"locationCode": str}, keep_default_na=False)
    ingrid = set(used.networkCode + "." + used.stationCode + "." + used.locationCode)
    spos = station_enu()
    rv = review_map()
    ev = sols["NCSS"].set_index("id")
    rel = set(sols[run].id)
    out = []
    ph["sid"] = ph.networkCode + "." + ph.stationCode + "." + ph.locationCode
    byev = {int(k): set(zip(g.sid, g.type)) for k, g in ph.groupby("eventId")}
    xyz = ev[["E", "N", "U"]]

    def sdist(eid, sid):
        return float(np.linalg.norm(xyz.loc[eid].values - spos[sid])) / 1000.0

    for eid in sorted(set(ev.index) - rel):
        mine = byev.get(eid, set())
        d = np.sqrt(((xyz - xyz.loc[eid]) ** 2).sum(axis=1)) / 1000.0
        cand = d[(d > 0) & (d <= 5.0)].index
        n_120 = sum(1 for s_, t in mine if sdist(eid, s_) <= MAX_EVSTA_KM)
        shared = []
        for c in cand:
            dd = float(d.loc[c])
            k = 0
            for s_, t in mine & byev.get(int(c), set()):
                a_, b_ = sdist(eid, s_), sdist(int(c), s_)
                if a_ <= MAX_EVSTA_KM and b_ <= MAX_EVSTA_KM and a_ / dd >= RATIO and b_ / dd >= RATIO:
                    k += 1
            shared.append(k)
        nb8 = int(sum(x >= 8 for x in shared))
        out.append(dict(run=run, id=int(eid), review=rv.loc[eid, "review_version"], magnitude=rv.loc[eid, "pref_mag"],
                        n_P=sum(1 for s_, t in mine if t == "P"),
                        n_S=sum(1 for s_, t in mine if t == "S"),
                        n_auto_R=int(rv.loc[eid, "n_auto_R_in_phase_csv"]),
                        n_phases_with_grid=sum(1 for s_, t in mine if s_ in ingrid),
                        n_phases_within_120km=int(n_120),
                        in_LDEO=bool(rv.loc[eid, "in_ldeo_dd"]), in_NCEDC=bool(rv.loc[eid, "in_ncedc_dd"]),
                        events_within_5km=int(len(cand)),
                        neighbours_sharing_ge8_phases=nb8,
                        max_shared_phases=int(max(shared) if shared else 0),
                        reason=("fewer than 8 picks: cannot share minNumPhases=8 phases with any neighbour"
                                if len(mine) < 8 else
                                "fewer than 8 picks within 120 km (maxEvStaDist)" if n_120 < 8 else
                                "fewer than minNumNeigh=8 neighbours sharing >= 8 phases" if nb8 < 8
                                else "other (ellipsoid selection / removed with its neighbours)")))
    return out


def grid_escapes(sols, run):
    """Events for which libhdd's travel-time lookup failed for all their phases in some iteration (event outside
    the grids: 'TTT: n/n queries failed for Event ...'), and events that end above sea level or whose move from the
    NCSS start differs by > 5 km from the run's median move (i.e. after removing the common shift of the cluster).
    One row per event."""
    f = run_files(run)["log"]
    txt = open(f, errors="replace").read() if f and os.path.exists(f) else ""
    fails = re.findall(r"TTT: (\d+)/(\d+) queries failed for Event (\d+) at lat ([-\d.]+) lon ([-\d.]+) depth ([-\d.]+)",
                       txt)
    nfail = {}
    worst = {}
    for a_, b_, eid, la, lo, de in fails:
        eid = int(eid)
        nfail[eid] = nfail.get(eid, 0) + 1
        worst.setdefault(eid, []).append(float(de))
    s0 = sols["NCSS"].set_index("id")
    s1 = sols[run].set_index("id")
    ids = s1.index.intersection(s0.index)
    dmv = s1.loc[ids, ["E", "N", "U"]].values - s0.loc[ids, ["E", "N", "U"]].values
    move = pd.Series(np.linalg.norm(dmv, axis=1) / 1000, index=ids)
    move_rel = pd.Series(np.linalg.norm(dmv - np.median(dmv, axis=0), axis=1) / 1000, index=ids)
    rv = review_map()
    sel = set(nfail) | set(s1.index[s1.depth < 0]) | set(move_rel.index[move_rel > 5.0])
    out = []
    for eid in sorted(sel):
        r = s1.loc[eid] if eid in s1.index else None
        out.append(dict(run=run, id=int(eid), review=rv.loc[eid, "review_version"], magnitude=rv.loc[eid, "pref_mag"],
                        n_P=int(rv.loc[eid, "n_P_in_phase_csv"]), n_S=int(rv.loc[eid, "n_S_in_phase_csv"]),
                        iterations_with_all_ttt_failed=int(nfail.get(eid, 0)),
                        depths_when_failed_km=";".join(f"{x:.1f}" for x in worst.get(eid, [])),
                        start_depth_km=float(s0.loc[eid, "depth"]),
                        final_lat=float(r.latitude) if r is not None else np.nan,
                        final_lon=float(r.longitude) if r is not None else np.nan,
                        final_depth_km=float(r.depth) if r is not None else np.nan,
                        moved_from_start_km=float(move.get(eid, np.nan)),
                        moved_rel_to_median_move_km=float(move_rel.get(eid, np.nan)),
                        run_median_move_ENU_m=";".join(f"{x:.0f}" for x in np.median(dmv, axis=0)),
                        above_sea_level=bool(r is not None and r.depth < 0)))
    return out


def review_split(per_all):
    """(g) medians of the per-event errors of (a)-(c) by NCSS review group; same per-event numbers as the full-set
    table (centroids and reference neighbours from all common events)."""
    rv = review_map()
    per = per_all.copy()
    per["review_group"] = per.id.map(rv.review_group)
    # robust variant as in (a): the solution's MEDIAN offset (over all common events) removed instead of the means
    med = per.groupby(["solution", "reference"])[["dE_abs_m", "dN_abs_m", "dU_abs_m"]].transform("median")
    per["dh_relmed_m"] = np.hypot(per.dE_abs_m - med.dE_abs_m, per.dN_abs_m - med.dN_abs_m)
    per["dv_relmed_m"] = (per.dU_abs_m - med.dU_abs_m).abs()
    base = per[per.solution == "NCSS"].set_index(["reference", "id"])
    rows = []
    for (sol, ref, grp), g in per.groupby(["solution", "reference", "review_group"]):
        b = base.loc[ref].reindex(g.id)
        q = lambda x: float(np.median(x)) if len(x) else np.nan
        loc = np.hypot(g.local_dh_med_m.values, g.local_dv_med_m.values)
        locb = np.hypot(b.local_dh_med_m.values, b.local_dv_med_m.values)
        rows.append(dict(solution=sol, reference=ref, review_group=grp, n=int(len(g)),
                         rel_h_median_m=q(g.dh_rel_m), rel_v_median_m=q(g.dv_rel_m), rel_3d_median_m=q(g.d3_rel_m),
                         rel_h_median_m_mediancentred=q(g.dh_relmed_m), rel_v_median_m_mediancentred=q(g.dv_relmed_m),
                         local_h_median_m=q(g.local_dh_med_m), local_v_median_m=q(g.local_dv_med_m),
                         abs_dU_median_m=q(g.dU_abs_m), abs_h_median_m=q(np.hypot(g.dE_abs_m, g.dN_abs_m)),
                         ref_neighbour_dist_median_m=q(g.ref_neighbour_dist_med_m),
                         improvement_rel_3d=q(b.d3_rel_m) / q(g.d3_rel_m) if sol != "NCSS" else 1.0,
                         frac_events_closer_than_NCSS_rel3d=float((g.d3_rel_m.values < b.d3_rel_m.values).mean())
                         if sol != "NCSS" else np.nan,
                         frac_events_closer_than_NCSS_local=float((loc < locb).mean()) if sol != "NCSS" else np.nan))
    return pd.DataFrame(rows)


def compare_with_2015(sols, refs, ids_common):
    """The 2015 P1 and the 2025-26 P1 in one frame (see header). Returns (summary dict, positions, segments)."""
    # --- 2015: P1 (runs/sanramon), LDEO base NCAeqDD.v202112.1, NCEDC DD (datum-converted, as the 2015 script)
    p15 = enu(pd.read_csv(f"{RUNS2015}/pyrtdd/P1/relocated-event.csv"))
    l15 = pd.read_csv(f"{SR2015}/reference_tables/ldeo_dd_catalog.csv").rename(
        columns={"event_id": "id", "depth_km": "depth"})
    n15 = pd.read_csv(f"{SR2015}/reference_tables/dd_catalog.csv").rename(columns={"event_id": "id", "depth_km": "depth_model"})
    c15 = pd.read_csv(f"{SR2015}/reference_tables/ncss_catalog.csv")
    n15 = n15.merge(c15[["event_id", "depth_datum_m"]].rename(columns={"event_id": "id"}), on="id", how="left")
    n15["depth"] = n15.depth_model - n15.depth_datum_m / 1000.0
    n15 = n15[n15.depth.notna()]
    l15, n15 = enu(l15), enu(n15)
    # 2015 common set as in the 2015 analysis: events relocated by P0, P1, S0, S1 and present in the reference
    com15 = set(p15.id)
    for f in (f"{RUNS2015}/pyrtdd/P0/relocated-event.csv", f"{RUNS2015}/scrtdd/S0/work/reloc-event.csv",
              f"{RUNS2015}/scrtdd/S1/work/reloc-event.csv"):
        com15 &= set(pd.read_csv(f).id)
    p26 = sols["P1"]
    l26, n26 = refs["LDEO"], refs["NCEDC"]

    def offset(sol, ref, ids):
        ids = sorted(set(ids) & set(ref.id) & set(sol.id))
        a = sol.set_index("id").loc[ids, ["E", "N", "U"]].values
        r = ref.set_index("id").loc[ids, ["E", "N", "U"]].values
        return (a.mean(axis=0) - r.mean(axis=0)), len(ids)

    off = {}
    off["2015_LDEO"], n_a = offset(p15, l15, com15)
    off["2015_NCEDC"], n_b = offset(p15, n15, com15)
    off["2026_LDEO"], n_c = offset(p26, l26, ids_common)
    off["2026_NCEDC"], n_d = offset(p26, n26, ids_common)
    summ = {"method": "each P1 catalog minus its own mean offset against its LDEO reference on the common events "
                      "(2015: LDEO NCAeqDD.v202112.1; 2025-26: LDEO DD-RT v202201, tied to base DD202112.1); "
                      "both then in one TM frame (37.757 N, -121.940 E); axes from the SVD plane of the shifted 2015 P1",
            "offset_events": {"2015_LDEO": n_a, "2015_NCEDC": n_b, "2026_LDEO": n_c, "2026_NCEDC": n_d},
            "offsets_m_E_N_U": {k: [round(float(x), 1) for x in v] for k, v in off.items()}}
    X = {"P1_2015": p15[["id", "E", "N", "U"]].copy(), "P1_2026": p26[["id", "E", "N", "U"]].copy()}
    X["P1_2015"][["E", "N", "U"]] -= off["2015_LDEO"]
    X["P1_2026"][["E", "N", "U"]] -= off["2026_LDEO"]
    Xn = {"P1_2015": p15[["id", "E", "N", "U"]].copy(), "P1_2026": p26[["id", "E", "N", "U"]].copy()}
    Xn["P1_2015"][["E", "N", "U"]] -= off["2015_NCEDC"]
    Xn["P1_2026"][["E", "N", "U"]] -= off["2026_NCEDC"]
    # LDEO catalogs themselves as the check, on each year's BENCHMARK events (as the P1 sets and tool 21; the
    # catalogs' own in_box flags would drop the 2015 benchmark events south of the 2015 box, next to 2025-26)
    lb15 = pd.read_csv(f"{SR2015}/inputs/rtdd_catalog/event.csv").id
    lb26 = pd.read_csv(f"{SR}/inputs/rtdd_catalog/event.csv").id
    X["LDEO_2015"] = l15[l15.id.isin(lb15)][["id", "E", "N", "U"]].copy()
    X["LDEO_2026"] = l26[l26.id.isin(lb26)][["id", "E", "N", "U"]].copy()
    # axes: SVD plane of the shifted 2015 P1
    xyz15 = X["P1_2015"][["E", "N", "U"]].values
    pf15 = plane_fit(xyz15)
    cen15 = xyz15.mean(axis=0)
    c = xyz15 - cen15
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    nrm = vt[2].copy()
    if nrm[2] < 0:
        nrm = -nrm
    sv = np.array([np.sin(np.radians(pf15["strike"])), np.cos(np.radians(pf15["strike"])), 0.0])
    dv = np.cross(nrm, sv)
    if dv[2] > 0:
        dv = -dv
    # fault-normal axis pointing to the dip direction (horizontal part of the upward normal): + = toward ~E
    pos = []
    for k, d in X.items():
        v = d[["E", "N", "U"]].values - cen15
        t = d[["id"]].copy()
        t["set"] = k
        t["E"], t["N"], t["U"] = d.E.values, d.N.values, d.U.values
        t["along_strike_m"], t["normal_m"], t["down_dip_m"] = v @ sv, v @ nrm, v @ dv
        pos.append(t)
    pos = pd.concat(pos, ignore_index=True)
    summ["plane_2015_P1_shifted"] = pf15
    summ["plane_2026_P1_shifted"] = plane_fit(X["P1_2026"][["E", "N", "U"]].values)
    summ["plane_LDEO_2015_benchmark"] = plane_fit(X["LDEO_2015"][["E", "N", "U"]].values)
    summ["plane_LDEO_2026_benchmark"] = plane_fit(X["LDEO_2026"][["E", "N", "U"]].values)
    summ["axes"] = dict(strike_unit_ENU=sv.round(4).tolist(), normal_unit_ENU=nrm.round(4).tolist(),
                        down_dip_unit_ENU=dv.round(4).tolist(), origin_ENU_m=cen15.round(1).tolist(),
                        origin_note="centroid of the shifted 2015 P1")

    def nn_stats(a, b):
        tree = cKDTree(b)
        dist, _ = tree.query(a, k=1)
        return dict(n=int(len(a)), nearest_median_m=float(np.median(dist)), nearest_p05_m=float(np.quantile(dist, .05)),
                    nearest_p95_m=float(np.quantile(dist, .95)),
                    within_250m=int((dist <= 250).sum()), within_500m=int((dist <= 500).sum()),
                    within_1km=int((dist <= 1000).sum()), within_2km=int((dist <= 2000).sum())), dist

    g = {k: d[["E", "N", "U"]].values for k, d in X.items()}
    summ["nearest_2015_event_P1frame"], d_p1 = nn_stats(g["P1_2026"], g["P1_2015"])
    summ["nearest_2015_event_LDEO"], d_l = nn_stats(g["LDEO_2026"], g["LDEO_2015"])
    gn = {k: d[["E", "N", "U"]].values for k, d in Xn.items()}
    summ["nearest_2015_event_P1frame_NCEDCoffsets"], _ = nn_stats(gn["P1_2026"], gn["P1_2015"])
    pos.loc[pos.set == "P1_2026", "nearest_2015_P1_m"] = d_p1
    pos.loc[pos.set == "LDEO_2026", "nearest_2015_LDEO_m"] = d_l
    for k in X:
        cen = g[k].mean(axis=0)
        summ[f"centroid_{k}_ENU_m"] = cen.round(1).tolist()
    sh = g["P1_2026"].mean(axis=0) - g["P1_2015"].mean(axis=0)
    shl = g["LDEO_2026"].mean(axis=0) - g["LDEO_2015"].mean(axis=0)
    shn = gn["P1_2026"].mean(axis=0) - gn["P1_2015"].mean(axis=0)
    for name, v in (("P1frame", sh), ("LDEO_benchmark", shl), ("P1frame_NCEDCoffsets", shn)):
        summ[f"centroid_shift_2026_minus_2015_{name}"] = dict(
            E_m=float(v[0]), N_m=float(v[1]), U_m=float(v[2]), h_km=float(np.hypot(v[0], v[1]) / 1000),
            azimuth_deg=float(np.degrees(np.arctan2(v[0], v[1])) % 360))
    # along-strike extent and segments (500 m bins along the 2015 strike)
    a15 = pos[pos.set == "P1_2015"].along_strike_m
    lo, hi = np.quantile(a15, [.05, .95])
    a26 = pos[pos.set == "P1_2026"]
    summ["along_strike_2015_P1_p05_p95_m"] = [float(lo), float(hi)]
    summ["n_2026_P1_within_2015_along_strike_p05_p95"] = int(((a26.along_strike_m >= lo) & (a26.along_strike_m <= hi)).sum())
    summ["along_strike_2026_P1_p05_p95_m"] = [float(np.quantile(a26.along_strike_m, .05)),
                                              float(np.quantile(a26.along_strike_m, .95))]
    edges = np.arange(np.floor(pos.along_strike_m.min() / 500) * 500, pos.along_strike_m.max() + 500, 500)
    seg = []
    for i in range(len(edges) - 1):
        r = dict(along_from_m=float(edges[i]), along_to_m=float(edges[i + 1]))
        for k in ("P1_2015", "P1_2026", "LDEO_2015", "LDEO_2026"):
            t = pos[(pos.set == k) & (pos.along_strike_m >= edges[i]) & (pos.along_strike_m < edges[i + 1])]
            r[f"n_{k}"] = int(len(t))
            r[f"normal_median_m_{k}"] = float(t.normal_m.median()) if len(t) else np.nan
            r[f"normal_p10_m_{k}"] = float(t.normal_m.quantile(.1)) if len(t) else np.nan
            r[f"normal_p90_m_{k}"] = float(t.normal_m.quantile(.9)) if len(t) else np.nan
            r[f"depth_median_km_{k}"] = float(-t.U.median() / 1000) if len(t) else np.nan
        seg.append(r)
    seg = pd.DataFrame(seg)
    seg = seg[(seg[[c for c in seg.columns if c.startswith("n_")]].sum(axis=1)) > 0]
    # fault-normal position of the 2026 events relative to the 2015 plane, inside / outside the 2015 strike range
    ins = a26[(a26.along_strike_m >= lo) & (a26.along_strike_m <= hi)]
    out = a26[(a26.along_strike_m < lo) | (a26.along_strike_m > hi)]
    p15n = pos[pos.set == "P1_2015"].normal_m
    summ["normal_offset_from_2015_plane_m"] = {
        "P1_2015_median_abs": float(p15n.abs().median()),
        "P1_2026_inside_2015_strike_range": dict(n=int(len(ins)), median=float(ins.normal_m.median()),
                                                  median_abs=float(ins.normal_m.abs().median()),
                                                  p10=float(ins.normal_m.quantile(.1)), p90=float(ins.normal_m.quantile(.9))),
        "P1_2026_outside_2015_strike_range": dict(n=int(len(out)), median=float(out.normal_m.median()),
                                                   median_abs=float(out.normal_m.abs().median()),
                                                   p10=float(out.normal_m.quantile(.1)), p90=float(out.normal_m.quantile(.9)))}
    return summ, pos, seg


def main():
    os.makedirs(OUT, exist_ok=True)
    sols = load_solutions()
    refs, n_nodatum = load_references()
    # positions table
    pos = []
    for name, s in list(sols.items()) + [(f"REF_{k}", v) for k, v in refs.items()]:
        t = s[["id", "latitude", "longitude", "depth", "E", "N", "U"]].copy()
        t.insert(0, "solution", name)
        pos.append(t)
    pd.concat(pos).to_csv(f"{OUT}/positions_enu.csv", index=False, float_format="%.6f")

    main_present = [m for m in MAIN if m in sols]
    common_rt = set.intersection(*[set(sols[m].id) for m in main_present])
    summary = dict(solutions=list(sols), main_solutions_present=main_present,
                   n_relocated={k: int(len(v)) for k, v in sols.items()}, n_common_main=len(common_rt),
                   ncedc_events_without_datum=n_nodatum)
    rows, per_rows = [], []
    for rname, ref in refs.items():
        ids = sorted(common_rt & set(ref.id))
        summary[f"n_common_{rname}"] = len(ids)
        base = None
        for sname in ["NCSS"] + [k for k in sols if k != "NCSS"]:
            s = sols[sname]
            ids_s = ids if set(ids) <= set(s.id) else sorted(set(ids) & set(s.id))
            summ, per = compare(s, ref, ids_s)
            summ.update(solution=sname, reference=rname, same_event_set=len(ids_s) == len(ids))
            if sname == "NCSS":
                base = (summ, per)
            elif base is not None and len(ids_s) == len(ids):
                b = base[0]
                for k in ("rel_h_median_m", "rel_v_median_m", "rel_3d_median_m", "local_h_median_m", "local_v_median_m"):
                    summ[f"improvement_{k.replace('_median_m', '')}"] = b[k] / summ[k] if summ[k] > 0 else np.nan
                pb = base[1].set_index("id").loc[ids_s]
                summ["frac_events_closer_than_NCSS_rel3d"] = float((per.set_index("id").d3_rel_m < pb.d3_rel_m).mean())
                summ["frac_events_closer_than_NCSS_local"] = float(
                    (np.hypot(per.set_index("id").local_dh_med_m, per.set_index("id").local_dv_med_m) <
                     np.hypot(pb.local_dh_med_m, pb.local_dv_med_m)).mean())
            rows.append(summ)
            per.insert(0, "reference", rname)
            per.insert(0, "solution", sname)
            per_rows.append(per)
        # the other reference as a "solution" (reference uncertainty)
        other = "NCEDC" if rname == "LDEO" else "LDEO"
        ids_o = sorted(set(ids) & set(refs[other].id))
        summ, per = compare(refs[other], ref, ids_o)
        summ.update(solution=f"REF_{other}", reference=rname, same_event_set=len(ids_o) == len(ids))
        b = compare(sols["NCSS"], ref, ids_o)[0]
        for k in ("rel_h_median_m", "rel_v_median_m", "rel_3d_median_m", "local_h_median_m", "local_v_median_m"):
            summ[f"improvement_{k.replace('_median_m', '')}"] = b[k] / summ[k]
        rows.append(summ)
        per.insert(0, "reference", rname)
        per.insert(0, "solution", f"REF_{other}")
        per_rows.append(per)
    M = pd.DataFrame(rows)
    first = ["solution", "reference", "n", "same_event_set"]
    M = M[first + [c for c in M.columns if c not in first]]
    M.to_csv(f"{OUT}/metrics_vs_reference.csv", index=False, float_format="%.4f")
    per_all = pd.concat(per_rows)
    rvm = review_map()
    per_all.insert(3, "review", per_all.id.map(rvm.review_version))
    per_all.to_csv(f"{OUT}/per_event_vs_reference.csv", index=False, float_format="%.3f")
    # (g) split by NCSS review status
    RS = review_split(per_all)
    RS.to_csv(f"{OUT}/review_split.csv", index=False, float_format="%.4f")
    summary["review_split"] = RS.to_dict(orient="records")
    summary["review_counts_input"] = rvm.review_version.value_counts().to_dict()
    summary["review_counts_relocated"] = {k: rvm.loc[sorted(set(v.id) & set(rvm.index)), "review_version"]
                                          .value_counts().to_dict() for k, v in sols.items()}

    # (d) plane fits: on the common event set (LDEO ∩ main) and on each catalog's own full set
    pf = []
    ids_l = sorted(common_rt & set(refs["LDEO"].id))
    for name, s in list(sols.items()) + [(f"REF_{k}", v) for k, v in refs.items()]:
        ss = s.set_index("id")
        if set(ids_l) <= set(ss.index):
            pf.append(dict(catalog=name, event_set="common (LDEO and all main runs)", **plane_fit(ss.loc[ids_l, ["E", "N", "U"]].values)))
        own = s
        if name.startswith("REF_"):
            if name == "REF_LDEO":
                own = s[s.id.isin(pd.read_csv(f"{TAB}/ldeo_ddrt_catalog.csv").query("in_box").event_id)]
            else:
                own = s[s.id.isin(pd.read_csv(f"{TAB}/dd_catalog.csv").query("in_box").event_id)]
        pf.append(dict(catalog=name, event_set="own (all events of the catalog; references: in the box)",
                       **plane_fit(own[["E", "N", "U"]].values)))
    P = pd.DataFrame(pf)
    P.to_csv(f"{OUT}/plane_fit.csv", index=False, float_format="%.2f")

    # run vs run
    rv = []
    for a, b in PAIRS:
        if a not in sols or b not in sols:
            continue
        ids = sorted(set(sols[a].id) & set(sols[b].id))
        A = sols[a].set_index("id").loc[ids, ["E", "N", "U"]].values
        B = sols[b].set_index("id").loc[ids, ["E", "N", "U"]].values
        d = A - B
        d3 = np.linalg.norm(d, axis=1)
        # relative difference: remove the MEDIAN offset (robust: one unstable event, e.g. 72544210 which is 6.3 km
        # apart in P1 and S1, would otherwise shift every event by ~9 m through the mean)
        dr = d - np.median(d, axis=0)
        dr3 = np.linalg.norm(dr, axis=1)
        drh = np.hypot(dr[:, 0], dr[:, 1])
        ta = pd.to_datetime(sols[a].set_index("id").loc[ids, "isotime"], format="ISO8601")
        tb = pd.to_datetime(sols[b].set_index("id").loc[ids, "isotime"], format="ISO8601")
        dt = (ta - tb).dt.total_seconds().values * 1000
        rv.append(dict(a=a, b=b, n_a=len(sols[a]), n_b=len(sols[b]), n_common=len(ids),
                       abs3d_median_m=float(np.median(d3)), abs3d_p90_m=float(np.quantile(d3, .9)),
                       abs3d_max_m=float(d3.max()), centroid_dE_m=float(d[:, 0].mean()),
                       centroid_dN_m=float(d[:, 1].mean()), centroid_dU_m=float(d[:, 2].mean()),
                       rel3d_median_m=float(np.median(dr3)), rel3d_p90_m=float(np.quantile(dr3, .9)),
                       rel3d_max_m=float(dr3.max()), relh_median_m=float(np.median(drh)),
                       relv_median_m=float(np.median(np.abs(dr[:, 2]))),
                       n_rel3d_gt_1m=int((dr3 > 1).sum()), n_rel3d_gt_10m=int((dr3 > 10).sum()),
                       n_rel3d_gt_100m=int((dr3 > 100).sum()), id_max=int(np.array(ids)[np.argmax(dr3)]),
                       origin_time_abs_median_ms=float(np.median(np.abs(dt))), origin_time_abs_max_ms=float(np.abs(dt).max())))
    pd.DataFrame(rv).to_csv(f"{OUT}/run_vs_run.csv", index=False, float_format="%.4f")

    # (e) dropped events, (f) xcorr and residual statistics, runtime
    dr_rows, xs_rows, res_rows, rt_rows = [], [], [], []
    for run in [r for r in sols if r != "NCSS"]:
        dr_rows += dropped_events(sols, run, None)
        f = run_files(run)
        xs = xcorr_stats(f["xcorr"]) if f["xcorr"] else {}
        xl = xcorr_log_summary(f["log"]) if xs else {}
        for ph, v in xs.items():
            extra = {f"log_{k.split('_', 1)[1]}": x for k, x in xl.items() if k.startswith(f"{ph}_")}
            extra.update({f"log_{k}": x for k, x in xl.items() if k.startswith("waveforms")})
            xs_rows.append(dict(run=run, phase=ph, **v, **extra))
        for stage in ("initial", "final"):
            st = dd_stats(f[stage])
            for sub, v in st.items():
                res_rows.append(dict(run=run, stage=stage, subset=sub, **v))
        r = runtime(run)
        r["n_clusters"] = f["ncl"]
        r["n_relocated"] = len(sols[run])
        # absolute travel-time RMS of the events (rtDD startRms/finalRms columns, s)
        if "startRms" in sols[run]:
            r["event_startRms_median_ms"] = float(sols[run].startRms.median() * 1000)
            r["event_finalRms_median_ms"] = float(sols[run].finalRms.median() * 1000)
        rt_rows.append(r)
    pd.DataFrame(dr_rows).to_csv(f"{OUT}/dropped_events.csv", index=False)
    esc = []
    for run in [r for r in sols if r != "NCSS"]:
        esc += grid_escapes(sols, run)
    pd.DataFrame(esc).to_csv(f"{OUT}/grid_escapes.csv", index=False, float_format="%.4f")
    summary["grid_escapes"] = esc
    summary["dropped_events"] = dr_rows
    pd.DataFrame(xs_rows).to_csv(f"{OUT}/xcorr_stats.csv", index=False, float_format="%.4f")
    pd.DataFrame(res_rows).to_csv(f"{OUT}/residual_stats.csv", index=False, float_format="%.4f")
    pd.DataFrame(rt_rows).to_csv(f"{OUT}/runtime.csv", index=False)

    # P1 vs S1 cross-correlation, triplet by triplet
    xc_cmp = {}
    for a, b in (("P1", "S1"),):
        fa, fb = run_files(a)["xcorr"], run_files(b)["xcorr"]
        if not (fa and fb and os.path.exists(fa) and os.path.exists(fb)):
            continue
        def norm(path):
            x = pd.read_csv(path, dtype={"locationCode": str}, keep_default_na=False)
            sw = x.eventId1 > x.eventId2
            x.loc[sw, ["eventId1", "eventId2"]] = x.loc[sw, ["eventId2", "eventId1"]].values
            x.loc[sw, "lag"] = -x.loc[sw, "lag"]
            x["valid"] = x.valid.astype(str).str.lower() == "true"
            return x
        A, B = norm(fa), norm(fb)
        k = ["eventId1", "eventId2", "networkCode", "stationCode", "locationCode", "phaseType"]
        m = A.merge(B, on=k, suffixes=("_py", "_sc"), how="outer", indicator=True)
        both = m[(m._merge == "both") & m.valid_py & m.valid_sc]
        dl = (both.lag_py - both.lag_sc).abs() * 1000
        dc = (both.coefficient_py - both.coefficient_sc).abs()
        side = ((both.coefficient_py.abs() >= .7) != (both.coefficient_sc.abs() >= .7))
        res = dict(entries_py=int(len(A)), entries_sc=int(len(B)), only_py=int((m._merge == "left_only").sum()),
                   only_sc=int((m._merge == "right_only").sum()), both_valid=int(len(both)),
                   valid_py_not_sc=int(((m._merge == "both") & m.valid_py & ~m.valid_sc.fillna(False).astype(bool)).sum()),
                   valid_sc_not_py=int(((m._merge == "both") & ~m.valid_py.fillna(False).astype(bool) & m.valid_sc).sum()),
                   lag_identical=int((dl < 0.5).sum()), lag_diff_gt_1ms=int((dl > 1.5).sum()),
                   lag_diff_gt_10ms=int((dl > 10.5).sum()), coef_absdiff_median=float(dc.median()),
                   coef_absdiff_p99=float(dc.quantile(.99)), coef_absdiff_max=float(dc.max()),
                   threshold_side_differs=int(side.sum()))
        for ph, g in both.groupby("phaseType"):
            dlg = (g.lag_py - g.lag_sc).abs() * 1000
            res[f"{ph}_both_valid"] = int(len(g))
            res[f"{ph}_lag_identical"] = int((dlg < 0.5).sum())
            res[f"{ph}_lag_diff_gt_10ms"] = int((dlg > 10.5).sum())
            res[f"{ph}_coef_absdiff_median"] = float((g.coefficient_py - g.coefficient_sc).abs().median())
            res[f"{ph}_threshold_side_differs"] = int(((g.coefficient_py.abs() >= .7) != (g.coefficient_sc.abs() >= .7)).sum())
        xc_cmp[f"{a}_vs_{b}"] = res
        m.drop(columns=["_merge"]).assign(source=m._merge.astype(str)).to_csv(
            f"{OUT}/xcorr_triplets_{a}_vs_{b}.csv", index=False, float_format="%.6f")
    summary["xcorr_pyrtdd_vs_scrtdd"] = xc_cmp
    # the 2015 P1 and the 2025-26 P1 in one frame
    if "P1" in sols:
        ids_l = sorted(common_rt & set(refs["LDEO"].id))
        c15, pos15, seg15 = compare_with_2015(sols, refs, ids_l)
        pos15.to_csv(f"{OUT}/comparison_2015_positions.csv", index=False, float_format="%.2f")
        seg15.to_csv(f"{OUT}/comparison_2015_segments.csv", index=False, float_format="%.1f")
        summary["comparison_2015"] = c15
        print(json.dumps(c15, indent=1, default=float))
        print(seg15.round(0).to_string())
    summary["metrics_vs_reference"] = M.to_dict(orient="records")
    summary["plane_fit"] = P.to_dict(orient="records")
    summary["run_vs_run"] = rv
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1, default=float)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    cols = ["solution", "reference", "n", "rel_h_median_m", "rel_h_p90_m", "rel_v_median_m", "rel_v_p90_m",
            "local_h_median_m", "local_v_median_m", "centroid_shift_E_m", "centroid_shift_N_m", "centroid_shift_U_m",
            "improvement_rel_3d", "improvement_local_h", "improvement_local_v", "frac_events_closer_than_NCSS_rel3d"]
    print(M[[c for c in cols if c in M]].round(3).to_string())
    print(P.round(2).to_string())
    print(pd.DataFrame(rv).round(3).to_string())
    print(json.dumps(xc_cmp, indent=1))
    print(pd.DataFrame(rt_rows).to_string())


if __name__ == "__main__":
    main()
