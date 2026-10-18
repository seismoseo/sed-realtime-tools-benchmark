#!/usr/bin/env python
# analyze_sanramon.py -- comparisons of the San Ramon 2015 rtDD relocations (pyrtdd P*, scrtdd S*) with the
# reference catalogs, and of the runs with each other. Read-only on the run folders; writes runs/sanramon/analysis/.
#
# Solutions read (each only if it exists):
#   NCSS     NCSS routine locations = rtDD start (inputs/rtdd_catalog/event.csv; geoid depth)
#   P0 P1 P0n P1n P0a0 P1a0 P0d1 P1d1 P1pos P0rep  runs/sanramon/pyrtdd/<run>/relocated-event.csv
#   S0 S1 S0n S1n S0rep S0nat               runs/sanramon/scrtdd/<run>/work/reloc-event.csv
# References:
#   LDEO     LDEO NCAeqDD.v202112.1 (reference_tables/ldeo_dd_catalog.csv), geoid depths (PRIMARY)
#   NCEDC    NCEDC DD = DD-RT for 2015 (reference_tables/dd_catalog.csv); depths are below the local model
#            surface: converted to sea level with each event's NCSS datum (ncss_catalog.csv depth_datum_m),
#            depth_sl = depth - datum/1000 (docs/sanramon_inputs.md 1.1, 3.1) (SECONDARY)
# All depths compared are km below sea level (rtDD depths are relative to the NLL grids, whose z = 0 is sea level).
# Positions -> local metres (E, N, U = -depth) with a transverse Mercator projection centred on the swarm
# (37.786 N, -121.963 E, WGS-84), so horizontal distances are true to < 1 mm over the swarm.
#
# Metrics per (solution, reference), on a COMMON event set (events relocated by every main solution
# P0, P1, S0, S1 that exist AND present in the reference), so all solutions are judged on the same events:
#   (a) relative geometry: d_i = (x_i - mean x) - (r_i - mean r); median and 90th percentile of |d_h| and |d_v|
#       (and 3-D); also a robust variant with the median offset removed instead of the means. Local relative geometry: for each event, the vectors to its K=10 nearest neighbours IN THE
#       REFERENCE (3-D), ours vs reference; per event the median |difference| (horizontal, vertical); then the
#       median and 90th percentile over events.
#   (b) centroid shift: mean x - mean r (E, N, U), and the median per-event absolute offset.
#   (c) improvement ratio: metric(NCSS start) / metric(solution) for the medians of (a); > 1 means the solution is
#       closer to the reference than the start; and the fraction of events whose (a) 3-D error is smaller than
#       NCSS's.
#   (d) fault structure: plane fit by SVD of the centred coordinates of the common events (normal = smallest
#       singular vector): strike (right-hand rule) / dip, RMS distance from the plane ("thickness"), median absolute
#       distance, and the RMS spreads along strike and down dip. Also on each catalog's own full event set.
#   (e) events relocated / dropped and why (reconstructed for the dropped events: picks and candidate neighbours).
#   (f) cross-correlation statistics and double-difference residuals (initial / final) from libhdd's own files.
# Run against run (relative = median offset removed; absolute 3-D distance): P0 vs S0, P1 vs S1, P0 vs P0rep, S0 vs S0rep, P0 vs P0n, P1 vs P1n, P0n vs S0n, P1n vs S1n
# (absolute 3-D and relative differences), and P1 vs S1 cross-correlation measurements triplet by triplet.
# Runtime / memory of every run from run_info.json / run_summary.json and the /usr/bin/time logs.
#
# Usage (env pyrtdd): python -I analyze_sanramon.py

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
SR = f"{PROJECT}/data/sanramon_2015"
TAB = f"{SR}/reference_tables"
RUNS = f"{PROJECT}/runs/sanramon"
OUT = f"{RUNS}/analysis"
LOGS = f"{PROJECT}/logs"
LAT0, LON0 = 37.786, -121.963
K_NEIGH = 10
MAIN = ["P0", "P1", "S0", "S1"]               # the common event set is built from these (those that exist)
PY_RUNS = ["P0", "P1", "P0n", "P1n", "P0a0", "P1a0", "P0d1", "P1d1", "P1pos", "P0rep"]
SC_RUNS = ["S0", "S1", "S0n", "S1n", "S0rep", "S0nat"]
PAIRS = [("P0", "S0"), ("P0", "S0nat"), ("S0", "S0nat"), ("P1", "S1"), ("P0", "P0rep"), ("S0", "S0rep"), ("P0n", "S0n"), ("P1n", "S1n"),
         ("P0", "P0n"), ("P1", "P1n"), ("P0", "P0a0"), ("P1", "P1a0"), ("P0", "P1"), ("S0", "S1"), ("P0a0", "P1a0"),
         ("NCSS", "P0"), ("NCSS", "P1"), ("NCSS", "P0a0"), ("NCSS", "P1a0"),
         ("P0", "P0d1"), ("P1", "P1d1"), ("NCSS", "P0d1"), ("NCSS", "P1d1"), ("P0a0", "P0d1"), ("P1a0", "P1d1"),
         ("P1", "P1pos"), ("NCSS", "P1pos")]
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
    ldeo = pd.read_csv(f"{TAB}/ldeo_dd_catalog.csv")
    ldeo = ldeo.rename(columns={"event_id": "id", "depth_km": "depth"})
    nc = pd.read_csv(f"{TAB}/dd_catalog.csv").rename(columns={"event_id": "id", "depth_km": "depth_model"})
    ncss = pd.read_csv(f"{TAB}/ncss_catalog.csv")
    nc = nc.merge(ncss[["event_id", "depth_datum_m"]].rename(columns={"event_id": "id"}), on="id", how="left")
    nc["depth"] = nc.depth_model - nc.depth_datum_m / 1000.0
    n_nodatum = int(nc.depth_datum_m.isna().sum())
    nc = nc[nc.depth.notna()]
    refs = {"LDEO": enu(ldeo[["id", "latitude", "longitude", "depth", "eh1_km", "eh2_km", "ez_km"]]),
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
        t = f"{LOGS}/11_sanramon_pyrtdd_{run}_console.log"
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


def dropped_events(sols, run, clustering):
    """Events of the input catalog not relocated by 'run', with the facts needed to say why."""
    ph = pd.read_csv(f"{SR}/inputs/rtdd_catalog/phase.csv", dtype=str, keep_default_na=False)
    sta = pd.read_csv(f"{SR}/inputs/rtdd_catalog/station.csv", dtype={"locationCode": str}, keep_default_na=False)
    used = pd.read_csv(f"{SR}/inputs/nll_con_tm/stations_used.csv", dtype={"locationCode": str}, keep_default_na=False)
    ingrid = set(used.networkCode + "." + used.stationCode + "." + used.locationCode)
    ev = sols["NCSS"].set_index("id")
    rel = set(sols[run].id)
    out = []
    ph["sid"] = ph.networkCode + "." + ph.stationCode + "." + ph.locationCode
    byev = {int(k): set(zip(g.sid, g.type)) for k, g in ph.groupby("eventId")}
    xyz = ev[["E", "N", "U"]]
    for eid in sorted(set(ev.index) - rel):
        mine = byev.get(eid, set())
        p = ev.loc[eid]
        d = np.sqrt(((xyz - xyz.loc[eid]) ** 2).sum(axis=1)) / 1000.0
        cand = d[(d > 0) & (d <= 5.0)].index
        shared = [len(mine & byev.get(int(c), set())) for c in cand]
        out.append(dict(run=run, id=int(eid), n_P=sum(1 for s, t in mine if t == "P"),
                        n_S=sum(1 for s, t in mine if t == "S"),
                        n_phases_with_grid=sum(1 for s, t in mine if s in ingrid),
                        events_within_5km=int(len(cand)),
                        neighbours_sharing_ge8_phases=int(sum(x >= 8 for x in shared)),
                        max_shared_phases=int(max(shared) if shared else 0),
                        reason=("fewer than 8 picks: cannot share minNumPhases=8 phases with any neighbour"
                                if len(mine) < 8 else
                                "fewer than minNumNeigh=8 neighbours sharing >= 8 phases" if sum(x >= 8 for x in shared) < 8
                                else "other (ellipsoid/ratio selection)")))
    return out


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
    pd.concat(per_rows).to_csv(f"{OUT}/per_event_vs_reference.csv", index=False, float_format="%.3f")

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
                own = s[s.id.isin(pd.read_csv(f"{TAB}/ldeo_dd_catalog.csv").query("in_box").event_id)]
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
    pd.DataFrame(xs_rows).to_csv(f"{OUT}/xcorr_stats.csv", index=False, float_format="%.4f")
    pd.DataFrame(res_rows).to_csv(f"{OUT}/residual_stats.csv", index=False, float_format="%.4f")
    pd.DataFrame(rt_rows).to_csv(f"{OUT}/runtime.csv", index=False)

    # P1 vs S1 cross-correlation, triplet by triplet
    xc_cmp = {}
    for a, b in (("P1", "S1"), ("P1n", "S1n")):
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
