#!/usr/bin/env python
# scrtdd_compare.py -- compares the scrtdd (SeisComP module) runs of the Gwangyang benchmark with
#                      HypoDD (02.dt.cc and 01.dt.ct), with the pyrtdd runs, and the single-event runs with S1.
#
# Usage (env pyrtdd, read-only on every input; writes only runs/gwangyang/scrtdd/comparison/):
#     source /home/msseo/miniforge3/etc/profile.d/conda.sh; conda activate pyrtdd
#     python -I scrtdd_compare.py            # dry run: lists the inputs it found
#     python -I scrtdd_compare.py --apply    # computes and writes the tables
#
# Metrics (all in metres / milliseconds; local east/north/up about 35.0000 N 127.7286 E; east/north from
# obspy gps2dist_azimuth on WGS84, the method of the reference tables; up = -depth):
#   (a) relative geometry: for each event, (position - own 11-event centroid) of the solution minus the same
#       for HypoDD; per event (dE, dN, dU, horizontal, 3-D) and RMS / max over the 11 events
#   (b) centroid shift: solution centroid minus HypoDD centroid (E, N, U)
#   (c) fraction of events whose (a) lies inside HypoDD dt.cc's bootstrap 95% half-widths
#       (|dE| <= ex95, |dN| <= ey95, |dU| <= ez95; for the dt.ct comparison also with dt.ct's own half-widths),
#       and the largest ratio |d| / half-width over events and components (max_ratio_boot95*).
#   HypoDD convention (shared with runs/gwangyang/pyrtdd/analyze_pyrtdd_gwangyang.py since 2026-10-17, after the
#   independent verification): HypoDD positions = hypoDD.reloc X/Y/Z (0.1 m; X east, Y north, Z down) added to
#   the 'Cluster centroid at:' point of hypoDD.log (the ISTART=1 start that X/Y/Z refer to); bootstrap half-widths
#   unrounded from <branch>/bootstrap_errors.csv. Before, this script used the 1-m DEPTH column and the
#   0.1-m-rounded half-widths of reference_tables/, which moved (c) by +-1 event against pyrtdd's numbers.
#   (d) inter-event 3-D distances over the 55 pairs: Pearson r and RMS of the difference
#   (e) origin times: solution minus HypoDD (origin_time_pha_datum), after removing the mean over the events
#   (f) cross-correlation runs: number of P and S differential times with |CC| >= 0.7 (rtDD's test uses the
#       absolute value, dd.cpp:918) versus the reference (1017 P + 1509 S of 1226 P + 1575 S); and for
#       pair/station/phase triplets in both, rtDD's corrected differential time (catalog dt - lag) minus the
#       reference dt.cc value: median, MAD, fraction within 2 ms and 5 ms, and the correlation of the CCs
#       (signed rtDD CC and |rtDD CC|, both for the pairs where both passed and for all measured pairs).
#       Both programs' differential times lie on a 1-ms grid, so the fractions are counted on the grid:
#       |round(diff_ms)| <= 2 (or 5). The float test |diff_ms| <= 2.0 used before 2026-10-17 dropped about half of
#       the exact-2-ms differences through rounding noise (independent verification).
# Also: scrtdd vs pyrtdd per event (same settings), scrtdd vs pyrtdd cross-correlation per triplet, scrtdd run
# vs run (shape differences, run_vs_run.csv), and the single-event (leave-one-out) results vs the S1 multi-event
# positions, vs pyrtdd's single-event runs, and each single-event run vs its own reference catalog.

import argparse
import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd
from obspy import UTCDateTime
from obspy.geodetics import gps2dist_azimuth

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
REFT = f"{DATA}/reference_tables"
CAT = f"{DATA}/inputs/rtdd_catalog"
SC = f"{PROJECT}/runs/gwangyang/scrtdd"
PY = f"{PROJECT}/runs/gwangyang/pyrtdd"
OUT = f"{SC}/comparison"
ORIGIN = (35.0000, 127.7286)          # local frame origin given by the task
CC_MIN = 0.7
REFRUN = f"{DATA}/reference/gwangyang_pnplus/2.HypoDD"
HYPODD_BRANCH = {"hypodd_dtcc": "02.dt.cc", "hypodd_dtct": "01.dt.ct"}
HYPODD_ID_OFFSET = 199999                  # hypoDD id = rtdd_id + 199999 (reference_tables/event_id_map.csv)
RELOC_COLS = ["id", "lat", "lon", "depth", "x", "y", "z", "ex", "ey", "ez", "yr", "mo", "dy", "hr", "mi", "sc",
              "mag", "nccp", "nccs", "nctp", "ncts", "rcc", "rct", "cid"]   # hypoDD.reloc columns
RUN_VS_RUN = [("S0n", "S0", "built-in NonLinLoc reader instead of the tttnll plugin"),
              ("S0h", "S0", "HYPOINVERSE start (catalog only)"), ("S1h", "S1", "HYPOINVERSE start"),
              ("S2", "S1", "rtdd_default solver (absolute equations 0.3) + default cross-correlation windows"),
              ("S2sc", "S1", "scrtdd profile defaults"), ("S1", "S0", "adding cross-correlation")]
SE_PARTNERS = [("SEa", "R6tf_single_event_loo_scrtdd_two_step_automatic_filtered"),
               ("SEm", "R6f_single_event_loo_one_step_filtered")]   # closest pyrtdd single-event partners
REF_CC_COUNTS = {"P": (1017, 1226), "S": (1509, 1575)}   # dt.cc_0.7_combined used / measured

SC_RUNS = ["S0", "S0n", "S0h", "S1", "S1h", "S2", "S2sc"]
# pyrtdd run with the same settings (task: R0, R1, R2). The pyrtdd agent found that the stock pyrtdd ObsPy proxy
# never band-passes the traces (its 'R1'/'R2' are resampled but unfiltered); its 'f' runs pre-process with the
# requested filter and are the like-for-like partner of the scrtdd runs (SeisComP's filter does reach the data).
PAIRS = [("S0", "R0_catalog_only_hypodd_like"), ("S0n", "R0_catalog_only_hypodd_like"),
         ("S0h", "R3a_catalog_only_hypodd_like_hypoinverse_start"),
         ("S1", "R1f_xcorr_like_reference_hypodd_like_filtered"), ("S1", "R1_xcorr_like_reference_hypodd_like"),
         ("S1h", "R3bf_xcorr_like_reference_hypodd_like_hypoinverse_start_filtered"),
         ("S1h", "R3b_xcorr_like_reference_hypodd_like_hypoinverse_start"),
         ("S2", "R2f_xcorr_default_rtdd_default_filtered"), ("S2", "R2_xcorr_default_rtdd_default")]
SE_MODES = ["SEa", "SEm"]


# ----------------------------------------------------------------------------- helpers
def enu(lat, lon, depth_km):
    e, n = [], []
    for la, lo in zip(lat, lon):
        d, az, _ = gps2dist_azimuth(ORIGIN[0], ORIGIN[1], la, lo)
        e.append(d * np.sin(np.radians(az)))
        n.append(d * np.cos(np.radians(az)))
    return np.column_stack([e, n, -np.asarray(depth_km, float) * 1000.0])


def load_reloc(path, lat="latitude", lon="longitude", dep="depth", t="isotime", idcol="id"):
    df = pd.read_csv(path).sort_values(idcol).reset_index(drop=True)
    out = pd.DataFrame({"id": df[idcol].astype(int), "lat": df[lat], "lon": df[lon], "depth_km": df[dep],
                        "time": [UTCDateTime(x) for x in df[t]]})
    if "relocated" in df:
        out["relocated"] = df["relocated"].astype(str).str.lower().eq("true")
    xyz = enu(out.lat, out.lon, out.depth_km)
    out["E"], out["N"], out["U"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    return out


def load_hypodd(name):
    """HypoDD solution in the shared convention (see header) + its unrounded bootstrap half-widths."""
    branch = HYPODD_BRANCH[name]
    t = pd.read_csv(f"{REFT}/{name}.csv").sort_values("rtdd_id").reset_index(drop=True)
    r = pd.read_csv(f"{REFRUN}/{branch}/hypoDD.reloc", sep=r"\s+", header=None, names=RELOC_COLS)
    r = r.set_index("id").loc[t.rtdd_id.values + HYPODD_ID_OFFSET].reset_index()
    assert np.allclose(r[["x", "y", "z"]].values, t[["x_m", "y_m", "z_m"]].values), "hypoDD.reloc != reference table"
    txt = open(f"{REFRUN}/{branch}/hypoDD.log", errors="replace").read()
    m = re.search(r"Cluster centroid at:\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", txt)
    clat, clon, cdep = float(m.group(1)), float(m.group(2)), float(m.group(3))
    c = enu([clat], [clon], [cdep])[0]
    out = pd.DataFrame({"id": t.rtdd_id.astype(int), "lat": t.latitude, "lon": t.longitude,
                        "depth_km": cdep + r.z.values / 1000.0,
                        "time": [UTCDateTime(x) for x in t.origin_time_pha_datum]})
    out["E"], out["N"], out["U"] = c[0] + r.x.values, c[1] + r.y.values, c[2] - r.z.values
    b = pd.read_csv(f"{REFRUN}/{branch}/bootstrap_errors.csv", comment="#")
    boot = pd.DataFrame({"id": b.id - HYPODD_ID_OFFSET, "ex95": b.ex95, "ey95": b.ey95, "ez95": b.ez95})
    return out, boot, (clat, clon, cdep)


def compare(sol, ref, boot=None, boot_alt=None):
    """Metrics (a)-(e) of solution 'sol' against reference 'ref' (both per-event frames with id/E/N/U/time)."""
    m = sol.merge(ref, on="id", suffixes=("", "_ref"))
    if len(m) != 11:
        raise ValueError(f"expected 11 common events, got {len(m)}")
    X = m[["E", "N", "U"]].to_numpy()
    Y = m[["E_ref", "N_ref", "U_ref"]].to_numpy()
    cx, cy = X.mean(0), Y.mean(0)
    d = (X - cx) - (Y - cy)
    per = pd.DataFrame({"id": m.id, "dE_m": d[:, 0], "dN_m": d[:, 1], "dU_m": d[:, 2],
                        "dH_m": np.hypot(d[:, 0], d[:, 1]), "d3_m": np.linalg.norm(d, axis=1)})
    dt = np.array([(a - b) for a, b in zip(m.time, m.time_ref)])
    per["dt_ms_demeaned"] = (dt - dt.mean()) * 1000.0
    s = {"rms_h_m": float(np.sqrt(np.mean(d[:, 0] ** 2 + d[:, 1] ** 2))), "max_h_m": float(per.dH_m.max()),
         "rms_v_m": float(np.sqrt(np.mean(d[:, 2] ** 2))), "max_v_m": float(per.dU_m.abs().max()),
         "rms_3d_m": float(np.sqrt(np.mean(np.sum(d ** 2, 1)))), "max_3d_m": float(per.d3_m.max()),
         "centroid_shift_E_m": float(cx[0] - cy[0]), "centroid_shift_N_m": float(cx[1] - cy[1]),
         "centroid_shift_U_m": float(cx[2] - cy[2])}
    for name, b in (("boot", boot), ("boot_own", boot_alt)):
        if b is None:
            continue
        bb = m[["id"]].merge(b, on="id")
        inside = ((per.dE_m.abs().values <= bb.ex95.values) & (per.dN_m.abs().values <= bb.ey95.values)
                  & (per.dU_m.abs().values <= bb.ez95.values))
        ratio = np.max(np.abs(per[["dE_m", "dN_m", "dU_m"]].values) / bb[["ex95", "ey95", "ez95"]].values, axis=1)
        per[f"inside_{name}95"] = inside
        per[f"max_ratio_{name}95"] = ratio
        s[f"frac_inside_{name}95"] = float(inside.mean())
        s[f"n_inside_{name}95"] = int(inside.sum())
        s[f"max_ratio_{name}95"] = float(ratio.max())
        s[f"max_ratio_{name}95_event"] = int(per.id.values[np.argmax(ratio)])
    # (d) inter-event distances
    iu = np.triu_indices(11, 1)
    DX = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)[iu]
    DY = np.linalg.norm(Y[:, None, :] - Y[None, :, :], axis=2)[iu]
    s["interevent_pairs"] = int(len(DX))
    s["interevent_pearson_r"] = float(np.corrcoef(DX, DY)[0, 1])
    s["interevent_rms_diff_m"] = float(np.sqrt(np.mean((DX - DY) ** 2)))
    s["interevent_mean_diff_m"] = float(np.mean(DX - DY))
    s["origin_time_rms_ms"] = float(np.sqrt(np.mean(per.dt_ms_demeaned ** 2)))
    s["origin_time_max_ms"] = float(per.dt_ms_demeaned.abs().max())
    s["origin_time_mean_offset_ms"] = float(dt.mean() * 1000.0)
    return s, per


def catalog_dt():
    """Catalog differential travel time (t1-ot1)-(t2-ot2) for every event pair/station/phase of the rtDD catalog."""
    ev = pd.read_csv(f"{CAT}/event.csv")
    ev2 = pd.read_csv(f"{CAT}/event_centroid_start.csv")
    assert (ev.isotime == ev2.isotime).all(), "start catalogs differ in origin time"
    ot = {int(i): UTCDateTime(t) for i, t in zip(ev.id, ev.isotime)}
    ph = pd.read_csv(f"{CAT}/phase.csv")
    ph["tt"] = [UTCDateTime(t) - ot[int(e)] for t, e in zip(ph.isotime, ph.eventId)]
    return {(int(e), s, p): tt for e, s, p, tt in zip(ph.eventId, ph.stationCode, ph.type, ph.tt)}


def rtdd_xcorr_table(path, tt):
    """rtDD xcorr.csv -> one row per triplet, normalised to id1 < id2, with rtDD's corrected dt."""
    x = pd.read_csv(path)
    rows = []
    for r in x.itertuples(index=False):
        e1, e2 = int(r.eventId1), int(r.eventId2)
        sta, ph = r.stationCode, r.phaseType
        lag = float(r.lag)
        dtcat = tt[(e1, sta, ph)] - tt[(e2, sta, ph)]
        dt = dtcat - lag                      # dd.cpp:897 + 921
        if e1 > e2:                           # reverse: dt(e2,e1) = -dt(e1,e2), lag(e2,e1) = -lag
            e1, e2, dt, dtcat, lag = e2, e1, -dt, -dtcat, -lag
        rows.append(dict(id1=e1, id2=e2, station=sta, phase=ph, valid=str(r.valid).lower() == "true",
                         cc=float(r.coefficient), lag_s=lag, dt_cat_s=dtcat, dt_s=dt))
    return pd.DataFrame(rows)


def ref_dtcc(path):
    d = pd.read_csv(path)
    out = pd.DataFrame({"id1": d.rtdd_id_1, "id2": d.rtdd_id_2, "station": d.station, "phase": d.phase,
                        "dt_s": d.dt_s, "cc": d.cc, "dt_cat_s": d.dt_catalog_s})
    if "kept_in_final_iteration" in d:      # dtcc_used.csv: did HypoDD keep it in its last iteration (hypoDD.res)?
        out["kept_final"] = d.kept_in_final_iteration.astype(str).str.lower().eq("true")
    flip = out.id1 > out.id2
    out.loc[flip, ["id1", "id2"]] = out.loc[flip, ["id2", "id1"]].values
    out.loc[flip, ["dt_s", "dt_cat_s"]] = -out.loc[flip, ["dt_s", "dt_cat_s"]].values
    return out


def dt_stats(diff_ms):
    diff_ms = np.asarray(diff_ms, float)
    if len(diff_ms) == 0:
        return {"n": 0}
    med = float(np.median(diff_ms))
    grid = np.round(diff_ms)                   # both data sets are on a 1-ms grid: compare on the grid
    return {"n": int(len(diff_ms)), "median_ms": med, "mad_ms": float(np.median(np.abs(diff_ms - med))),
            "frac_within_2ms": float(np.mean(np.abs(grid) <= 2)),
            "frac_within_5ms": float(np.mean(np.abs(grid) <= 5)),
            "grid_dev_max_ms": float(np.max(np.abs(diff_ms - grid))),
            "p95_abs_ms": float(np.percentile(np.abs(diff_ms), 95)), "max_abs_ms": float(np.max(np.abs(diff_ms)))}


def xcorr_vs_reference(run, xc, meas, used):
    key = ["id1", "id2", "station", "phase"]
    out = {"run": run}
    for ph in ("P", "S"):
        sub = xc[xc.phase == ph]
        out[f"{ph}_attempted_valid"] = int(sub.valid.sum())
        out[f"{ph}_abs_cc_ge_0p7"] = int((sub.valid & (sub.cc.abs() >= CC_MIN)).sum())
        out[f"{ph}_pos_cc_ge_0p7"] = int((sub.valid & (sub.cc >= CC_MIN)).sum())
        out[f"{ph}_neg_cc_le_m0p7"] = int((sub.valid & (sub.cc <= -CC_MIN)).sum())
        out[f"{ph}_reference_used_of_measured"] = f"{REF_CC_COUNTS[ph][0]} of {REF_CC_COUNTS[ph][1]}"
    # both passed their threshold: rtDD |cc| >= 0.7 and the triplet is in dt.cc_0.7_combined
    a = xc[xc.valid & (xc.cc.abs() >= CC_MIN)].merge(used, on=key, suffixes=("", "_ref"))
    a["diff_ms"] = (a.dt_s - a.dt_s_ref) * 1000.0
    a["dtcat_check_ms"] = (a.dt_cat_s - a.dt_cat_s_ref) * 1000.0
    for ph in ("P", "S", "all"):
        sub = a if ph == "all" else a[a.phase == ph]
        for k, v in dt_stats(sub.diff_ms).items():
            out[f"both_used_{ph}_{k}"] = v
        if len(sub) > 2:   # CC correlation on the pairs where both passed (reference CC is always >= 0.7)
            out[f"both_used_{ph}_cc_pearson_r"] = float(np.corrcoef(sub.cc, sub.cc_ref)[0, 1])
            out[f"both_used_{ph}_abs_cc_pearson_r"] = float(np.corrcoef(sub.cc.abs(), sub.cc_ref)[0, 1])
    out["both_used_catalog_dt_max_abs_diff_ms"] = float(a.dtcat_check_ms.abs().max()) if len(a) else None
    # split by whether HypoDD kept the reference value in its final iteration (its own outlier test)
    if "kept_final" in a:
        for lab, sub in (("kept_by_hypodd", a[a.kept_final]), ("rejected_by_hypodd", a[~a.kept_final])):
            for k, v in dt_stats(sub.diff_ms).items():
                out[f"both_used_{lab}_{k}"] = v
    # every triplet measured by both (any coefficient)
    b = xc[xc.valid].merge(meas, on=key, suffixes=("", "_ref"))
    b["diff_ms"] = (b.dt_s - b.dt_s_ref) * 1000.0
    for ph in ("P", "S", "all"):
        sub = b if ph == "all" else b[b.phase == ph]
        for k, v in dt_stats(sub.diff_ms).items():
            out[f"all_measured_{ph}_{k}"] = v
        if len(sub) > 2:
            out[f"all_measured_{ph}_cc_pearson_r"] = float(np.corrcoef(sub.cc, sub.cc_ref)[0, 1])
            out[f"all_measured_{ph}_abs_cc_pearson_r"] = float(np.corrcoef(sub.cc.abs(), sub.cc_ref)[0, 1])
    # reference lags beyond rtDD's search: |dt_ref - dt_cat| > maxDelay cannot be reproduced
    b["ref_lag_equiv_s"] = b.dt_cat_s_ref - b.dt_s_ref
    out["all_measured_ref_lag_beyond_0p5s"] = int((b.ref_lag_equiv_s.abs() > 0.5).sum())
    return out, a, b


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    found_sc = [r for r in SC_RUNS if os.path.exists(f"{SC}/{r}/work/reloc-event.csv")]
    found_py = sorted(os.path.basename(p) for p in glob.glob(f"{PY}/*") if os.path.exists(f"{p}/relocated-event.csv"))
    print("scrtdd runs found:", found_sc)
    print("pyrtdd runs found:", found_py)
    print("single-event results:", [m for m in SE_MODES if os.path.exists(f"{SC}/{m}/single_event_results.csv")])
    if not args.apply:
        print("dry run: nothing written (use --apply)")
        return
    os.makedirs(OUT, exist_ok=True)

    # ---------------------------------------------------------------- references
    refs = {}
    boots = {}
    centroids = {}
    for name in ("hypodd_dtcc", "hypodd_dtct"):
        d = pd.read_csv(f"{REFT}/{name}.csv")
        refs[name], boots[name], centroids[name] = load_hypodd(name)
        # sanity: our east/north/up vs the table's (own centroid) after removing the means
        own = d.sort_values("rtdd_id")[["east_m", "north_m", "up_m"]].to_numpy()
        mine = refs[name][["E", "N", "U"]].to_numpy()
        print(f"{name}: ENU check vs table columns, max |diff| after removing means: "
              f"{np.abs((mine - mine.mean(0)) - (own - own.mean(0))).max():.2f} m (table rounded to 0.1 m)")
    hyp = pd.read_csv(f"{REFT}/hypoinverse_kim1983.csv")
    starts = {"START_hypoinverse": load_reloc(f"{REFT}/hypoinverse_kim1983.csv", dep="depth_km", t="origin_time",
                                              idcol="rtdd_id")}

    # ---------------------------------------------------------------- solutions
    sols = {r: load_reloc(f"{SC}/{r}/work/reloc-event.csv") for r in found_sc}
    pys = {r: load_reloc(f"{PY}/{r}/relocated-event.csv") for r in found_py}
    allpos = []
    for src, dd in (("scrtdd", sols), ("pyrtdd", pys), ("reference", refs), ("start", starts)):
        for r, df in dd.items():
            t = df.copy()
            t.insert(0, "solution", r)
            t.insert(0, "program", src)
            t["time"] = [x.isoformat() for x in t.time]
            allpos.append(t)
    pd.concat(allpos).to_csv(f"{OUT}/positions_enu.csv", index=False, float_format="%.4f")

    # ---------------------------------------------------------------- (a)-(e) vs HypoDD
    summ, pers = [], []
    targets = [("scrtdd", r, df) for r, df in sols.items()] + [("pyrtdd", r, df) for r, df in pys.items()] + \
              [("start", r, df) for r, df in starts.items()] + [("reference", "hypodd_dtct", refs["hypodd_dtct"])]
    for prog, r, df in targets:
        for refname in ("hypodd_dtcc", "hypodd_dtct"):
            if prog == "reference" and refname == "hypodd_dtct":
                continue
            s, per = compare(df, refs[refname], boot=boots["hypodd_dtcc"],
                             boot_alt=boots[refname] if refname == "hypodd_dtct" else None)
            s.update(program=prog, solution=r, versus=refname,
                     n_relocated=int(df.relocated.sum()) if "relocated" in df else None)
            summ.append(s)
            per.insert(0, "versus", refname)
            per.insert(0, "solution", r)
            per.insert(0, "program", prog)
            pers.append(per)
    S = pd.DataFrame(summ)
    lead = ["program", "solution", "versus", "n_relocated"]
    S = S[lead + [c for c in S.columns if c not in lead]]
    S.to_csv(f"{OUT}/metrics_vs_hypodd.csv", index=False, float_format="%.4f")
    pd.concat(pers).to_csv(f"{OUT}/per_event_vs_hypodd.csv", index=False, float_format="%.4f")

    # ---------------------------------------------------------------- scrtdd vs pyrtdd, per event
    pair_rows, pair_sum = [], []
    for s_run, p_run in PAIRS:
        if s_run not in sols or p_run not in pys:
            pair_sum.append(dict(scrtdd=s_run, pyrtdd=p_run, available=False))
            continue
        m = sols[s_run].merge(pys[p_run], on="id", suffixes=("_s", "_p"))
        d = m[["E_s", "N_s", "U_s"]].to_numpy() - m[["E_p", "N_p", "U_p"]].to_numpy()
        dt = np.array([(a - b) for a, b in zip(m.time_s, m.time_p)]) * 1000.0
        for i, r in enumerate(m.id):
            pair_rows.append(dict(scrtdd=s_run, pyrtdd=p_run, id=int(r), dE_m=d[i, 0], dN_m=d[i, 1], dU_m=d[i, 2],
                                  d3_m=float(np.linalg.norm(d[i])), dt_ms=dt[i],
                                  dlat_deg=m.lat_s[i] - m.lat_p[i], dlon_deg=m.lon_s[i] - m.lon_p[i],
                                  ddepth_km=m.depth_km_s[i] - m.depth_km_p[i]))
        rel = (d - d.mean(0))
        pair_sum.append(dict(scrtdd=s_run, pyrtdd=p_run, available=True, n=len(m),
                             max_abs_position_diff_m=float(np.abs(d).max()),
                             max_3d_diff_m=float(np.linalg.norm(d, axis=1).max()),
                             rms_3d_diff_m=float(np.sqrt(np.mean(np.sum(d ** 2, 1)))),
                             centroid_diff_E_m=float(d[:, 0].mean()), centroid_diff_N_m=float(d[:, 1].mean()),
                             centroid_diff_U_m=float(d[:, 2].mean()),
                             relative_geometry_max_3d_m=float(np.linalg.norm(rel, axis=1).max()),
                             relative_geometry_rms_3d_m=float(np.sqrt(np.mean(np.sum(rel ** 2, 1)))),
                             max_abs_time_diff_ms=float(np.abs(dt).max()),
                             identical_as_written=bool((np.abs(m.lat_s - m.lat_p).max() == 0)
                                                       and (np.abs(m.lon_s - m.lon_p).max() == 0)
                                                       and (np.abs(m.depth_km_s - m.depth_km_p).max() == 0))))
    pd.DataFrame(pair_rows).to_csv(f"{OUT}/scrtdd_vs_pyrtdd_per_event.csv", index=False, float_format="%.6f")
    pd.DataFrame(pair_sum).to_csv(f"{OUT}/scrtdd_vs_pyrtdd_summary.csv", index=False, float_format="%.4f")

    # ---------------------------------------------------------------- scrtdd run vs run (shape, metric a-e)
    rvr = []
    for other, base, why in RUN_VS_RUN:
        if other in sols and base in sols:
            s_, per_ = compare(sols[other], sols[base], boot=boots["hypodd_dtcc"])
            rvr.append(dict(other=other, base=base, what_changes=why, **s_))
    pd.DataFrame(rvr).to_csv(f"{OUT}/run_vs_run.csv", index=False, float_format="%.4f")

    # ---------------------------------------------------------------- (f) cross-correlation
    tt = catalog_dt()
    meas, used = ref_dtcc(f"{REFT}/dtcc_measured.csv"), ref_dtcc(f"{REFT}/dtcc_used.csv")
    xrows = []
    xc_tables = {}
    for r in found_sc:
        f = glob.glob(f"{SC}/{r}/work/multievent_*/xcorr.csv")
        if not f or r.startswith("S0"):        # S0* runs have cross-correlation disabled (empty xcorr.csv)
            continue
        xc = rtdd_xcorr_table(f[0], tt)
        if len(xc) == 0 or not xc.valid.any():
            continue
        xc_tables[r] = xc
        o, a, b = xcorr_vs_reference(r, xc, meas, used)
        o["program"] = "scrtdd"
        xrows.append(o)
        b.to_csv(f"{OUT}/xcorr_triplets_{r}_vs_reference.csv", index=False, float_format="%.6f")
    for r in found_py:
        f = f"{PY}/{r}/xcorr_cache.csv"
        if not os.path.exists(f) or r.startswith("R6"):
            continue
        xc = rtdd_xcorr_table(f, tt)
        xc_tables[r] = xc
        o, a, b = xcorr_vs_reference(r, xc, meas, used)
        o["program"] = "pyrtdd"
        xrows.append(o)
    X = pd.DataFrame(xrows)
    if len(X):
        X = X[["program", "run"] + [c for c in X.columns if c not in ("program", "run")]]
    X.to_csv(f"{OUT}/xcorr_vs_reference.csv", index=False, float_format="%.4f")

    # scrtdd vs pyrtdd cross-correlation, per triplet
    xs = []
    key = ["id1", "id2", "station", "phase"]
    for s_run, p_run in PAIRS:
        if s_run not in xc_tables or p_run not in xc_tables:
            continue
        m = xc_tables[s_run].merge(xc_tables[p_run], on=key, suffixes=("_s", "_p"))
        m = m[m.valid_s & m.valid_p]
        o = dict(scrtdd=s_run, pyrtdd=p_run, n_common_valid=int(len(m)),
                 n_scrtdd=int(xc_tables[s_run].valid.sum()), n_pyrtdd=int(xc_tables[p_run].valid.sum()))
        for ph in ("P", "S", "all"):
            sub = m if ph == "all" else m[m.phase == ph]
            dl = (sub.lag_s_s - sub.lag_s_p) * 1000.0
            dc = sub.cc_s - sub.cc_p
            o.update({f"{ph}_n": int(len(sub)), f"{ph}_lag_identical": int((dl.abs() < 1e-6).sum()),
                      f"{ph}_lag_diff_median_ms": float(dl.median()) if len(sub) else None,
                      f"{ph}_lag_diff_frac_within_1ms": float((dl.abs() <= 1.0 + 1e-9).mean()) if len(sub) else None,
                      f"{ph}_lag_diff_frac_within_2ms": float((dl.abs() <= 2.0 + 1e-9).mean()) if len(sub) else None,
                      f"{ph}_lag_diff_max_abs_ms": float(dl.abs().max()) if len(sub) else None,
                      f"{ph}_cc_diff_median": float(dc.median()) if len(sub) else None,
                      f"{ph}_cc_diff_max_abs": float(dc.abs().max()) if len(sub) else None,
                      f"{ph}_cc_pearson_r": float(np.corrcoef(sub.cc_s, sub.cc_p)[0, 1]) if len(sub) > 2 else None,
                      f"{ph}_pass_0p7_agree": float(((sub.cc_s.abs() >= CC_MIN) == (sub.cc_p.abs() >= CC_MIN)).mean()) if len(sub) else None})
        xs.append(o)
        m.to_csv(f"{OUT}/xcorr_triplets_{s_run}_vs_{p_run.split('_')[0]}.csv", index=False, float_format="%.6f")
    pd.DataFrame(xs).to_csv(f"{OUT}/xcorr_scrtdd_vs_pyrtdd.csv", index=False, float_format="%.4f")

    # ---------------------------------------------------------------- option values: scrtdd runs and pyrtdd partners
    def flat(x, p=""):
        out = {}
        if isinstance(x, dict):
            for k, v in x.items():
                out.update(flat(v, f"{p}.{k}" if p else k))
        else:
            out[p] = x
        return out

    def sc_opts(run):
        d = json.load(open(f"{SC}/{run}/run_options.json"))["libhdd_equivalent"]
        f = flat({"Config": d["Config"], "SolverOptions": d["SolverOptions"], "XcorrOptions": d["XcorrOptions"],
                  "ClusteringOptions": {k: v for k, v in d["ClusteringOptions_multiEvent"].items() if k != "note"}})
        f["travel_time_table.maxSearchDistance"] = d["TravelTimeTable"]["maxSearchDistance_m"]
        return f

    opt_rows = []
    for r in found_sc:
        f = sc_opts(r)
        f["run"] = r
        opt_rows.append(f)
    pd.DataFrame(opt_rows).set_index("run").T.to_csv(f"{OUT}/options_by_run.csv")
    cmp_rows = []
    for s_run, p_run in PAIRS:
        pf = f"{PY}/{p_run}/options.json"
        if s_run not in found_sc or not os.path.exists(pf):
            continue
        a_ = sc_opts(s_run)
        b_ = flat({k: v for k, v in json.load(open(pf)).items()
                   if k in ("Config", "SolverOptions", "XcorrOptions", "ClusteringOptions")})
        b_["travel_time_table.maxSearchDistance"] = json.load(open(pf)).get("travel_time_table", {}).get("maxSearchDistance")
        xcorr_on = bool(a_.get("XcorrOptions.enable"))
        for k in sorted(set(a_) | set(b_)):
            va, vb = a_.get(k, "(absent)"), b_.get(k, "(absent)")
            same = (va == vb) or (isinstance(va, (int, float)) and isinstance(vb, (int, float)) and float(va) == float(vb))
            if not xcorr_on and k.startswith(("XcorrOptions.", "Config.wfFilter")) and k != "XcorrOptions.enable":
                note = "irrelevant: cross-correlation disabled"
            elif k.startswith("Config.wfFilter") and not same and isinstance(vb, str) and vb:
                note = ("pyrtdd stock ObsPy proxy: filter string set but the band-pass never reaches the traces "
                        "(pyrtdd step finding); traces only demeaned + resampled")
            elif k.startswith("Config.wfFilter") and not same:
                note = "filtering done in the pyrtdd proxy instead (see its options.json waveform_proxy)"
            else:
                note = ""
            cmp_rows.append(dict(scrtdd=s_run, pyrtdd=p_run, option=k, scrtdd_value=va, pyrtdd_value=vb,
                                 same=same, note=note))
    C_ = pd.DataFrame(cmp_rows)
    C_.to_csv(f"{OUT}/options_scrtdd_vs_pyrtdd.csv", index=False)
    if len(C_):
        print("option differences that matter (same=False, no note):")
        print(C_[(~C_.same) & (C_.note == "")][["scrtdd", "pyrtdd", "option", "scrtdd_value", "pyrtdd_value"]].to_string())

    # ---------------------------------------------------------------- final double-difference residuals per event
    # (cluster-1-final-double-difference.csv of --dump-diagnostics; residual in seconds; weight 0 = discarded
    # by the residual down-weighting of the last iteration)
    rres = []
    for r in found_sc:
        f = glob.glob(f"{SC}/{r}/work/multievent_*/cluster-1-final-double-difference.csv")
        if not f:
            continue
        dd = pd.read_csv(f[0])
        for k in range(1, 12):
            sub = dd[(dd.eventId1 == k) | (dd.eventId2 == k)]
            w = sub[sub.weight > 0]
            rres.append(dict(run=r, id=k, n_dd=len(sub), n_weight0=int((sub.weight == 0).sum()),
                             n_xcorr_used=int(sub.xcorrUsed.astype(str).str.lower().eq("true").sum()),
                             median_abs_res_ms_weighted=float(w.doubleDifferenceResidual.abs().median() * 1000) if len(w) else None,
                             mad_res_ms_weighted=float((w.doubleDifferenceResidual - w.doubleDifferenceResidual.median()).abs().median() * 1000) if len(w) else None))
    pd.DataFrame(rres).to_csv(f"{OUT}/final_dd_residuals_by_event.csv", index=False, float_format="%.3f")

    # ---------------------------------------------------------------- single event vs S1
    se_rows = []
    if "S1" in sols:
        s1 = sols["S1"].set_index("id")
        for mode in SE_MODES:
            f = f"{SC}/{mode}/single_event_results.csv"
            if not os.path.exists(f):
                continue
            se = pd.read_csv(f)
            for r in se.itertuples(index=False):
                k = int(r.event_id)
                row = dict(mode=mode, evaluation_mode=r.evaluation_mode, id=k, exit_code=int(r.exit_code),
                           step1_ok=bool(r.step1_ok), step2_ok=bool(r.step2_ok), neighbours=str(r.neighbours_found),
                           cc_P=f"{getattr(r, 'cc_P_above', '')}/{getattr(r, 'cc_P_attempted', '')}",
                           cc_S=f"{getattr(r, 'cc_S_above', '')}/{getattr(r, 'cc_S_attempted', '')}")
                ref = s1.loc[k]
                for step, (la, lo, de, t) in (("step1", ("step1_lat", "step1_lon", "step1_depth", "step1_time")),
                                              ("final", ("reloc_latitude", "reloc_longitude", "reloc_depth_km", "reloc_time"))):
                    if pd.isna(getattr(r, la, np.nan)):
                        continue
                    p = enu([getattr(r, la)], [getattr(r, lo)], [getattr(r, de)])[0]
                    q = np.array([ref.E, ref.N, ref.U])
                    d = p - q
                    row.update({f"{step}_dE_m": d[0], f"{step}_dN_m": d[1], f"{step}_dU_m": d[2],
                                f"{step}_d3_m": float(np.linalg.norm(d)),
                                f"{step}_dt_ms": (UTCDateTime(getattr(r, t)) - ref.time) * 1000.0})
                # step-2 double differences that came from cross-correlation (final system of step 2): shows
                # that scrtdd's single-event mode really cross-correlates with SeisComP's record stream
                f2 = glob.glob(f"{SC}/{mode}/ev{k}/work/singleevent_*/step2/final-double-difference.csv")
                if f2:
                    d2 = pd.read_csv(f2[0])
                    row["step2_dd_total"] = int(len(d2))
                    row["step2_dd_from_xcorr"] = int(d2.xcorrUsed.astype(str).str.lower().eq("true").sum())
                # how far the HYPOINVERSE start was from S1 (what the relocation had to fix)
                h = starts["START_hypoinverse"].set_index("id").loc[k]
                row["start_d3_m"] = float(np.linalg.norm(np.array([h.E, h.N, h.U]) - np.array([ref.E, ref.N, ref.U])))
                se_rows.append(row)
    SE = pd.DataFrame(se_rows)
    SE.to_csv(f"{OUT}/single_event_vs_S1.csv", index=False, float_format="%.3f")
    se_sum = []
    for mode, g in SE.groupby("mode") if len(SE) else []:
        o = dict(mode=mode, n=len(g), step1_ok=int(g.step1_ok.sum()), step2_ok=int(g.step2_ok.sum()))
        for step in ("step1", "final"):
            if f"{step}_d3_m" in g:
                o[f"{step}_rms_h_m"] = float(np.sqrt(np.mean(g[f"{step}_dE_m"] ** 2 + g[f"{step}_dN_m"] ** 2)))
                o[f"{step}_rms_v_m"] = float(np.sqrt(np.mean(g[f"{step}_dU_m"] ** 2)))
                o[f"{step}_max_3d_m"] = float(g[f"{step}_d3_m"].max())
                o[f"{step}_median_3d_m"] = float(g[f"{step}_d3_m"].median())
                o[f"{step}_rms_dt_ms"] = float(np.sqrt(np.mean(g[f"{step}_dt_ms"] ** 2)))
        o["start_median_3d_m"] = float(g.start_d3_m.median())
        se_sum.append(o)
    pd.DataFrame(se_sum).to_csv(f"{OUT}/single_event_vs_S1_summary.csv", index=False, float_format="%.3f")

    # pyrtdd single-event (R6*) vs scrtdd single-event, per event, when available. Closest partners:
    # SEa (scrtdd two steps, automatic) <-> R6tf (pyrtdd replica of scrtdd's two steps, automatic, filtered);
    # SEm (two steps, manual) <-> R6f (ONE step with cross-correlation, manual, filtered). The pyrtdd single-event
    # clustering is scrtdd's single-event default (5 ellipsoids, 5 km, >= 4 neighbours, >= 8 phases), ours the
    # 'hypodd_like' block; with 10 reference events < 0.2 km away both select all of them (see pair.csv).
    r6, r6rows = [], []
    for p in sorted(glob.glob(f"{PY}/R6*")):
        f = f"{p}/relocated-event.csv"
        if not os.path.exists(f):
            continue
        r6.append(os.path.basename(p))
        py6 = load_reloc(f)
        for mode in SE_MODES:
            g = SE[SE["mode"] == mode] if len(SE) else pd.DataFrame()
            if not len(g):
                continue
            ser = pd.read_csv(f"{SC}/{mode}/single_event_results.csv").sort_values("event_id")
            sc6 = pd.DataFrame({"id": ser.event_id, "E": 0.0, "N": 0.0, "U": 0.0})
            xyz = enu(ser.reloc_latitude, ser.reloc_longitude, ser.reloc_depth_km)
            sc6["E"], sc6["N"], sc6["U"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
            m = sc6.merge(py6, on="id", suffixes=("_s", "_p"))
            d = m[["E_s", "N_s", "U_s"]].to_numpy() - m[["E_p", "N_p", "U_p"]].to_numpy()
            d3 = np.linalg.norm(d, axis=1)
            r6rows.append(dict(scrtdd=mode, pyrtdd=os.path.basename(p), n=len(m), median_3d_m=float(np.median(d3)),
                               max_3d_m=float(d3.max()), max_3d_event=int(m.id[int(np.argmax(d3))]),
                               rms_3d_m=float(np.sqrt(np.mean(d3 ** 2)))))
    pd.DataFrame(r6rows).to_csv(f"{OUT}/single_event_scrtdd_vs_pyrtdd.csv", index=False, float_format="%.3f")

    # context for the cross-tool comparison: each single-event run against its OWN reference catalog
    # (scrtdd: S1; pyrtdd R6f/R6tf: R1f; R6/R6p/R6tp/R6t: R1), and the scrtdd-pyrtdd single-event difference
    # after removing the difference of the two reference catalogs at the same event (S1 minus R1f)
    ctx_rows = []
    own = {"SEa": "S1", "SEm": "S1"}
    se_pos = {}
    for mode in SE_MODES:
        f = f"{SC}/{mode}/single_event_results.csv"
        if os.path.exists(f):
            ser = pd.read_csv(f).sort_values("event_id")
            xyz = enu(ser.reloc_latitude, ser.reloc_longitude, ser.reloc_depth_km)
            se_pos[mode] = pd.DataFrame({"id": ser.event_id.values, "E": xyz[:, 0], "N": xyz[:, 1], "U": xyz[:, 2]})
    for p in sorted(glob.glob(f"{PY}/R6*")):
        if os.path.exists(f"{p}/relocated-event.csv"):
            nm = os.path.basename(p)
            se_pos[nm] = pys[nm][["id", "E", "N", "U"]] if nm in pys else load_reloc(f"{p}/relocated-event.csv")[["id", "E", "N", "U"]]
            own[nm] = "R1f_xcorr_like_reference_hypodd_like_filtered" if "filtered" in nm else "R1_xcorr_like_reference_hypodd_like"
    allsol = dict(sols, **pys)
    for nm, P_ in se_pos.items():
        if own.get(nm) not in allsol:
            continue
        m = P_.merge(allsol[own[nm]][["id", "E", "N", "U"]], on="id", suffixes=("", "_c"))
        d3 = np.linalg.norm(m[["E", "N", "U"]].to_numpy() - m[["E_c", "N_c", "U_c"]].to_numpy(), axis=1)
        ctx_rows.append(dict(single_event_run=nm, versus=own[nm], kind="own reference catalog", n=len(m),
                             median_3d_m=float(np.median(d3)), max_3d_m=float(d3.max()),
                             max_3d_event=int(m.id[int(np.argmax(d3))]),
                             median_3d_without_event3_m=float(np.median(d3[m.id.values != 3]))))
    if "S1" in sols and "R1f_xcorr_like_reference_hypodd_like_filtered" in pys:
        cat = sols["S1"][["id", "E", "N", "U"]].merge(pys["R1f_xcorr_like_reference_hypodd_like_filtered"][["id", "E", "N", "U"]],
                                                      on="id", suffixes=("_s", "_p"))
        dcat = cat[["E_s", "N_s", "U_s"]].to_numpy() - cat[["E_p", "N_p", "U_p"]].to_numpy()
        d3c = np.linalg.norm(dcat, axis=1)
        ctx_rows.append(dict(single_event_run="S1", versus="R1f_xcorr_like_reference_hypodd_like_filtered",
                             kind="the two reference catalogs (multi-event)", n=len(cat), median_3d_m=float(np.median(d3c)),
                             max_3d_m=float(d3c.max()), max_3d_event=int(cat.id[int(np.argmax(d3c))]),
                             median_3d_without_event3_m=float(np.median(d3c[cat.id.values != 3])),
                             mean_dE_m=float(dcat[:, 0].mean()), mean_dN_m=float(dcat[:, 1].mean()),
                             mean_dU_m=float(dcat[:, 2].mean())))
        catd = pd.DataFrame({"id": cat.id.values, "cE": dcat[:, 0], "cN": dcat[:, 1], "cU": dcat[:, 2]})
        for sm_, pm_ in SE_PARTNERS:
            if sm_ not in se_pos or pm_ not in se_pos:
                continue
            a_ = se_pos[sm_].rename(columns={"E": "Es", "N": "Ns", "U": "Us"})
            b_ = se_pos[pm_].rename(columns={"E": "Ep", "N": "Np", "U": "Up"})
            m = a_.merge(b_, on="id").merge(catd, on="id")
            d = m[["Es", "Ns", "Us"]].to_numpy() - m[["Ep", "Np", "Up"]].to_numpy()
            dres = d - m[["cE", "cN", "cU"]].to_numpy()     # minus (S1 - R1f) at the same event
            n3, r3 = np.linalg.norm(d, axis=1), np.linalg.norm(dres, axis=1)
            ctx_rows.append(dict(single_event_run=sm_, versus=pm_, kind="scrtdd vs pyrtdd single event", n=len(m),
                                 median_3d_m=float(np.median(n3)), max_3d_m=float(n3.max()),
                                 max_3d_event=int(m.id[int(np.argmax(n3))]),
                                 median_3d_without_event3_m=float(np.median(n3[m.id.values != 3])),
                                 mean_dE_m=float(d[:, 0].mean()), mean_dN_m=float(d[:, 1].mean()),
                                 mean_dU_m=float(d[:, 2].mean()),
                                 after_removing_catalog_offset_median_3d_m=float(np.median(r3)),
                                 after_removing_catalog_offset_max_3d_m=float(r3.max()),
                                 after_removing_catalog_offset_max_event=int(m.id[int(np.argmax(r3))])))
    pd.DataFrame(ctx_rows).to_csv(f"{OUT}/single_event_context.csv", index=False, float_format="%.3f")
    with open(f"{OUT}/summary.json", "w") as fo:
        json.dump({"scrtdd_runs": found_sc, "pyrtdd_runs_found": found_py, "pyrtdd_single_event_runs_found": r6,
                   "metrics_vs_hypodd": S.to_dict(orient="records"),
                   "scrtdd_vs_pyrtdd": pair_sum, "xcorr_vs_reference": X.to_dict(orient="records"),
                   "xcorr_scrtdd_vs_pyrtdd": xs, "single_event_summary": se_sum,
                   "single_event_scrtdd_vs_pyrtdd": r6rows, "single_event_context": ctx_rows,
                   "run_vs_run": rvr,
                   "hypodd_convention": "hypoDD.log 'Cluster centroid at' + hypoDD.reloc X/Y/Z (0.1 m); bootstrap "
                                        "half-widths unrounded from bootstrap_errors.csv",
                   "hypodd_log_centroid": centroids,
                   "f_within_fractions": "counted on the 1-ms grid: |round(diff_ms)| <= 2 / <= 5",
                   "pyrtdd_inputs_mtime_kst": {r: pd.Timestamp(os.path.getmtime(f"{PY}/{r}/relocated-event.csv"), unit="s",
                                                              tz="UTC").tz_convert("Asia/Seoul").isoformat()
                                               for r in found_py}}, fo, indent=1, default=str)
    print("written:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
