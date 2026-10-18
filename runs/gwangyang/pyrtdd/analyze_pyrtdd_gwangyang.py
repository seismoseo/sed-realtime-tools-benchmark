#!/usr/bin/env python
# analyze_pyrtdd_gwangyang.py
#
# WHAT: comparison metrics for every finished pyrtdd run in runs/gwangyang/pyrtdd/<run>/ against the HypoDD
# reference relocations (02.dt.cc and 01.dt.ct), run-vs-run differences, and residual statistics.
#
# Metrics (all distances in metres; local east/north/up about 35.0000 N 127.7286 E, computed with
# obspy gps2dist_azimuth exactly like data/gwangyang_11ev/tools/make_reference_tables.py):
#   (a) relative geometry: per event, (position - own 11-event centroid) of the run minus the same for the
#       reference; RMS and max over events, horizontal and vertical separately (plus 3-D RMS).
#   (b) centroid shift: centroid(run) - centroid(reference), E/N/U.
#   (c) fraction of events with |dE| <= ex95, |dN| <= ey95, |dU| <= ez95 (the reference's own 1000-sample
#       bootstrap 95% half-widths, UNROUNDED from <branch>/bootstrap_errors.csv; dt.cc's for the dt.cc rows,
#       dt.ct's for the dt.ct rows; the dt.cc bootstrap is also given for the dt.ct rows), plus the largest
#       ratio |d| / half-width over events and components (c_max_ratio) and the event it belongs to.
#       Convention (shared with runs/gwangyang/scrtdd/scripts/scrtdd_compare.py since 2026-10-17, after the
#       independent verification): HypoDD positions = HypoDD's own X/Y/Z columns of hypoDD.reloc (0.1 m; X east,
#       Y north, Z down) added to the cluster centroid printed in hypoDD.log ('Cluster centroid at:', the ISTART=1
#       start point that X/Y/Z refer to). Before, east/north came from the LAT/LON columns and the half-widths from
#       the 0.1-m-rounded table, which moved (c) by +-1 event for some runs.
#   (d) the 55 inter-event 3-D distances: Pearson r and RMS difference (and mean difference = bias).
#   (e) origin-time differences after removing the mean difference: RMS and max (ms). HypoDD origin times
#       have 0.01 s resolution (origin_time_pha_datum), so values below ~3 ms are rounding.
#   (f) cross-correlation runs: counts of differential times with |CC| >= 0.7 (rtDD's own criterion) and with
#       CC >= +0.7 (the reference criterion), per phase; and for event-pair/station/phase triplets present in
#       both rtDD (|CC| >= 0.7) and the reference dt.cc_0.7_combined, the difference of the differential times
#       (rtDD dt = catalog dt - lag, see make_dt_tables.py) median / MAD / fraction within 2 ms and 5 ms, and
#       the Pearson correlation of the two CC values (signed rtDD CC, and |rtDD CC|; the reference CC is always
#       positive). Pairs with the ML 2.2 event (id 3) are also shown separately: the reference used a +-0.05 s
#       window and a 1-40 Hz band for them.
#       Both sets of differential times lie on a 1-ms grid (rtDD lags at 1000 Hz, reference values written to
#       1 ms), so the fractions are counted ON THE GRID: |round(diff_ms)| <= 2 (or 5). The float test
#       |diff_ms| <= 2.0 used before 2026-10-17 dropped about half of the exact-2-ms differences through
#       rounding noise (independent verification). dt_diff_grid_dev_max_ms reports how far the differences are
#       from the grid (must be ~0).
# HypoDD depth = the hypoDD.log cluster-centroid depth + Z (hypoDD.reloc Z, 0.1 m resolution) instead of the
# 1 m-resolution DEPTH column.
#
# Outputs (in runs/gwangyang/pyrtdd/):
#   summary_metrics.csv          one row per run x reference (a)-(f)
#   per_event_vs_reference.csv   one row per run x reference x event
#   run_vs_run_metrics.csv       one row per run pair (a, b, d, e + absolute per-event distance)
#   per_event_run_vs_run.csv     one row per run pair x event
#   xcorr_comparison.csv         (f) in detail: per run, per subset (all / without event 3 / P / S)
#   residual_stats.csv           rtDD's own residual statistics per run + HypoDD's RCC/RCT (reference rows)
#   positions_enu.csv            every run's (and the references') event positions in local ENU
#   analysis_summary.json        what was compared, versions, notes
# Usage (env pyrtdd): python -I analyze_pyrtdd_gwangyang.py [--apply]   (dry run lists the runs found)

import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd
from obspy.geodetics import gps2dist_azimuth

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
REFT = f"{DATA}/reference_tables"
REFRUN = f"{DATA}/reference/gwangyang_pnplus/2.HypoDD"
OUTROOT = f"{PROJECT}/runs/gwangyang/pyrtdd"
LAT0, LON0 = 35.0000, 127.7286
HYPODD_BRANCH = {"dtcc": "02.dt.cc", "dtct": "01.dt.ct"}   # reference name -> HypoDD run folder
HYPODD_ID_OFFSET = 199999                    # hypoDD id = rtdd_id + 199999 (reference_tables/event_id_map.csv)
RELOC_COLS = ["id", "lat", "lon", "depth", "x", "y", "z", "ex", "ey", "ez", "yr", "mo", "dy", "hr", "mi", "sc",
              "mag", "nccp", "nccs", "nctp", "ncts", "rcc", "rct", "cid"]   # hypoDD.reloc columns (HypoDD 1.3 manual)
CC_MIN = 0.7
SPECIAL_EVENT = 3                            # ML 2.2: reference used +-0.05 s, 1-40 Hz for its pairs
RUN_PAIRS = [   # (base, other, why)
    ("R0_catalog_only_hypodd_like", "R3a_catalog_only_hypodd_like_hypoinverse_start", "start position (catalog only)"),
    ("R1_xcorr_like_reference_hypodd_like", "R3b_xcorr_like_reference_hypodd_like_hypoinverse_start", "start position"),
    ("R1f_xcorr_like_reference_hypodd_like_filtered", "R3bf_xcorr_like_reference_hypodd_like_hypoinverse_start_filtered", "start position (filtered)"),
    ("R1_xcorr_like_reference_hypodd_like", "R4_xcorr_like_reference_hypodd_like_no_outlier_picks", "17 outlier picks removed"),
    ("R1f_xcorr_like_reference_hypodd_like_filtered", "R4f_xcorr_like_reference_hypodd_like_no_outlier_picks_filtered", "17 outlier picks removed (filtered)"),
    ("R1_xcorr_like_reference_hypodd_like", "R5_xcorr_like_reference_hypodd_like_homogeneous", "homogeneous velocity"),
    ("R1f_xcorr_like_reference_hypodd_like_filtered", "R5f_xcorr_like_reference_hypodd_like_homogeneous_filtered", "homogeneous velocity (filtered)"),
    ("R1_xcorr_like_reference_hypodd_like", "R6_single_event_loo_one_step", "single-event leave-one-out, one step"),
    ("R1_xcorr_like_reference_hypodd_like", "R6t_single_event_loo_scrtdd_two_step_automatic", "single-event, scrtdd two-step, automatic"),
    ("R1_xcorr_like_reference_hypodd_like", "R6p_single_event_loo_one_step_padded", "single-event, one step, batch-loading fixed (unfiltered)"),
    ("R1_xcorr_like_reference_hypodd_like", "R6tp_single_event_loo_scrtdd_two_step_automatic_padded", "single-event, scrtdd two-step, automatic, batch-loading fixed (unfiltered)"),
    ("R1f_xcorr_like_reference_hypodd_like_filtered", "R6f_single_event_loo_one_step_filtered", "single-event, one step (filtered)"),
    ("R1f_xcorr_like_reference_hypodd_like_filtered", "R6tf_single_event_loo_scrtdd_two_step_automatic_filtered", "single-event, scrtdd two-step, automatic (filtered)"),
    ("R1_xcorr_like_reference_hypodd_like", "R1f_xcorr_like_reference_hypodd_like_filtered", "band-pass actually applied vs not"),
    ("R1f_xcorr_like_reference_hypodd_like_filtered", "R1fz_xcorr_like_reference_hypodd_like_filtered_zerophase", "causal vs zero-phase band-pass"),
    ("R1f_xcorr_like_reference_hypodd_like_filtered", "R1fw_xcorr_like_reference_hypodd_like_filtered_xcorrweight100", "xcorrWeightScaler 2 vs 100"),
    ("R1_xcorr_like_reference_hypodd_like", "R2_xcorr_default_rtdd_default", "rtDD default solver + xcorr"),
    ("R1f_xcorr_like_reference_hypodd_like_filtered", "R2f_xcorr_default_rtdd_default_filtered", "rtDD default solver + xcorr (filtered)"),
    ("R0_catalog_only_hypodd_like", "R1_xcorr_like_reference_hypodd_like", "adding cross-correlation"),
    ("R1_xcorr_like_reference_hypodd_like", "V0_stock_no_disk_cache", "waveform disk cache on vs off"),
    ("V0_stock_no_disk_cache", "V1_port_check_preprocess_nofilter", "libhdd resampler vs numpy port (validation)"),
]


# ----------------------------------------------------------------------------- helpers
def enu(lat, lon, dep_km):
    e, n = [], []
    for la, lo in zip(lat, lon):
        d, az, _ = gps2dist_azimuth(LAT0, LON0, float(la), float(lo))
        e.append(d * np.sin(np.radians(az)))
        n.append(d * np.cos(np.radians(az)))
    return np.c_[e, n, -np.asarray(dep_km, dtype=float) * 1000.0]


def hypodd_log_centroid(branch):
    """First 'Cluster centroid at:' line of hypoDD.log: the point hypoDD.reloc X/Y/Z refer to (ISTART=1 start)."""
    txt = open(f"{REFRUN}/{branch}/hypoDD.log", errors="replace").read()
    m = re.search(r"Cluster centroid at:\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", txt)
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def hypodd_log_centroid_shift(branch):
    """Last 'mean centroid (origin) shift in x,y,z,t [m,ms]' of hypoDD.log (cumulative; z positive down)."""
    lines = open(f"{REFRUN}/{branch}/hypoDD.log", errors="replace").read().splitlines()
    vals = [lines[i + 1].split() for i, l in enumerate(lines) if "mean centroid (origin) shift" in l]
    return [float(v) for v in vals[-1]] if vals else None


def load_reference(name):
    """HypoDD solution in the shared convention: centroid (hypoDD.log) + X/Y/Z (hypoDD.reloc, 0.1 m); bootstrap
    95% half-widths unrounded from bootstrap_errors.csv; origin times from the reference table (.pha datum)."""
    branch = HYPODD_BRANCH[name]
    t = pd.read_csv(f"{REFT}/hypodd_{name}.csv").sort_values("rtdd_id").reset_index(drop=True)
    r = pd.read_csv(f"{REFRUN}/{branch}/hypoDD.reloc", sep=r"\s+", header=None, names=RELOC_COLS)
    r = r.set_index("id").loc[t.rtdd_id.values + HYPODD_ID_OFFSET].reset_index()
    assert np.allclose(r[["x", "y", "z"]].values, t[["x_m", "y_m", "z_m"]].values), "hypoDD.reloc != reference table"
    clat, clon, cdep = hypodd_log_centroid(branch)
    c = enu([clat], [clon], [cdep])[0]
    X = np.c_[c[0] + r.x.values, c[1] + r.y.values, c[2] - r.z.values]
    dep = cdep + r.z.values / 1000.0
    b = pd.read_csv(f"{REFRUN}/{branch}/bootstrap_errors.csv", comment="#").set_index("id")
    boot = b.loc[t.rtdd_id.values + HYPODD_ID_OFFSET, ["ex95", "ey95", "ez95"]].values
    ot = pd.to_datetime(t.origin_time_pha_datum)
    return dict(ids=t.rtdd_id.values, X=X, ot=ot, lat=t.latitude.values, lon=t.longitude.values, dep=dep,
                boot=boot, table=t, centroid=(clat, clon, cdep), log_centroid_shift=hypodd_log_centroid_shift(branch))


def load_run(run):
    ev = pd.read_csv(f"{OUTROOT}/{run}/relocated-event.csv").sort_values("id").reset_index(drop=True)
    X = enu(ev.latitude, ev.longitude, ev.depth)
    return dict(ids=ev.id.values, X=X, ot=pd.to_datetime(ev.isotime, format="ISO8601"), lat=ev.latitude.values,
                lon=ev.longitude.values, dep=ev.depth.values, table=ev)


def compare(A, B, bootB=None, boot_alt=None):
    """A = solution, B = yardstick. Returns summary dict and per-event DataFrame (common ids only)."""
    common = np.intersect1d(A["ids"], B["ids"])
    ia = np.searchsorted(A["ids"], common)
    ib = np.searchsorted(B["ids"], common)
    XA, XB = A["X"][ia], B["X"][ib]
    ra, rb = XA - XA.mean(0), XB - XB.mean(0)
    d = ra - rb
    h = np.hypot(d[:, 0], d[:, 1])
    s = dict(n_events=len(common),
             a_rel_rms_h_m=np.sqrt(np.mean(h ** 2)), a_rel_max_h_m=h.max(),
             a_rel_rms_v_m=np.sqrt(np.mean(d[:, 2] ** 2)), a_rel_max_v_m=np.abs(d[:, 2]).max(),
             a_rel_rms_3d_m=np.sqrt(np.mean(np.sum(d ** 2, 1))))
    c = XA.mean(0) - XB.mean(0)
    s.update(b_centroid_shift_e_m=c[0], b_centroid_shift_n_m=c[1], b_centroid_shift_u_m=c[2],
             b_centroid_shift_3d_m=float(np.linalg.norm(c)))
    pe = pd.DataFrame(dict(event_id=common, dE_rel_m=d[:, 0], dN_rel_m=d[:, 1], dU_rel_m=d[:, 2], dH_rel_m=h,
                           d3D_rel_m=np.linalg.norm(d, axis=1),
                           dE_abs_m=XA[:, 0] - XB[:, 0], dN_abs_m=XA[:, 1] - XB[:, 1], dU_abs_m=XA[:, 2] - XB[:, 2]))
    pe["d3D_abs_m"] = np.linalg.norm(pe[["dE_abs_m", "dN_abs_m", "dU_abs_m"]].values, axis=1)
    for tag, boot in (("", bootB), ("_dtccboot", boot_alt)):
        if boot is None:
            continue
        bb = boot[ib]
        inside = (np.abs(d[:, 0]) <= bb[:, 0]) & (np.abs(d[:, 1]) <= bb[:, 1]) & (np.abs(d[:, 2]) <= bb[:, 2])
        ratio = (np.abs(d) / bb).max(1)          # largest |d| / half-width over E, N, U, per event
        s[f"c_n_inside_boot95{tag}"] = int(inside.sum())
        s[f"c_frac_inside_boot95{tag}"] = float(inside.mean())
        s[f"c_max_ratio{tag}"] = float(ratio.max())
        s[f"c_max_ratio_event{tag}"] = int(common[np.argmax(ratio)])
        pe[f"inside_boot95{tag}"] = inside
        pe[f"boot95_max_ratio{tag}"] = ratio
        if tag == "":
            pe["boot_ex95_m"], pe["boot_ey95_m"], pe["boot_ez95_m"] = bb[:, 0], bb[:, 1], bb[:, 2]
    # (d) inter-event distances
    iu = np.triu_indices(len(common), 1)
    DA = np.linalg.norm(XA[:, None, :] - XA[None, :, :], axis=2)[iu]
    DB = np.linalg.norm(XB[:, None, :] - XB[None, :, :], axis=2)[iu]
    s.update(d_n_pairs=len(DA), d_interevent_pearson_r=float(np.corrcoef(DA, DB)[0, 1]),
             d_interevent_rms_diff_m=float(np.sqrt(np.mean((DA - DB) ** 2))),
             d_interevent_mean_diff_m=float(np.mean(DA - DB)),
             d_interevent_median_ref_m=float(np.median(DB)))
    # (e) origin times
    dt = (A["ot"].values[ia] - B["ot"].values[ib]).astype("timedelta64[ns]").astype(np.int64) / 1e6
    dt0 = dt - dt.mean()
    s.update(e_ot_mean_offset_ms=float(dt.mean()), e_ot_rms_demeaned_ms=float(np.sqrt(np.mean(dt0 ** 2))),
             e_ot_max_demeaned_ms=float(np.abs(dt0).max()))
    pe["dOT_demeaned_ms"] = dt0
    return s, pe


def norm_pairs(df, e1, e2, dtcol, extra):
    """Normalise event order to (low id, high id); negate dt/lag when swapped."""
    sw = df[e1] > df[e2]
    out = pd.DataFrame({"ev_lo": np.where(sw, df[e2], df[e1]), "ev_hi": np.where(sw, df[e1], df[e2]),
                        "station": df["station"].values, "phase": df["phase"].values,
                        "dt_s": np.where(sw, -df[dtcol], df[dtcol])})
    for c in extra:
        out[c] = df[c].values
    return out


def catalog_dt_table(run):
    """Catalog differential time per (ev1, ev2, station, phase) from the run's INPUT picks and origins."""
    ph = pd.read_csv(f"{OUTROOT}/{run}/inputs/phase.csv", dtype=str, keep_default_na=False)
    ev = pd.read_csv(f"{OUTROOT}/{run}/inputs/event.csv")
    ot = {int(r.id): pd.Timestamp(r.isotime) for r in ev.itertuples()}
    return {(int(r.eventId), r.stationCode, r.type): (pd.Timestamp(r.isotime) - ot[int(r.eventId)]).total_seconds()
            for r in ph.itertuples()}


def xcorr_metrics(run, meas, used):
    p = f"{OUTROOT}/{run}/xcorr_cache.csv"
    if not os.path.exists(p):
        return None, None
    x = pd.read_csv(p, keep_default_na=False)
    x = x.rename(columns={"stationCode": "station", "phaseType": "phase"})
    x["valid"] = x.valid.astype(str).str.lower() == "true"
    tt = catalog_dt_table(run)
    x["dt_catalog_s"] = [tt.get((a, s_, ph), np.nan) - tt.get((b, s_, ph), np.nan)
                         for a, b, s_, ph in zip(x.eventId1, x.eventId2, x.station, x.phase)]
    x["dt_rtdd_s"] = x.dt_catalog_s - x.lag
    out = {}
    for ph in ("P", "S"):
        xv = x[x.valid & (x.phase == ph)]
        out[f"f_n_measured_{ph}"] = int(len(xv))
        out[f"f_n_abscc07_{ph}"] = int((xv.coefficient.abs() >= CC_MIN).sum())
        out[f"f_n_poscc07_{ph}"] = int((xv.coefficient >= CC_MIN).sum())
        out[f"f_n_negcc07_{ph}"] = int((xv.coefficient <= -CC_MIN).sum())
        out[f"f_n_invalid_{ph}"] = int((~x.valid & (x.phase == ph)).sum())
        out[f"f_ref_n_measured_{ph}"] = int((meas.phase == ph).sum())
        out[f"f_ref_n_cc07_{ph}"] = int((used.phase == ph).sum())
    R = norm_pairs(x[x.valid].rename(columns={"eventId1": "e1", "eventId2": "e2"}), "e1", "e2", "dt_rtdd_s",
                   ["coefficient"])
    M = norm_pairs(meas.rename(columns={"rtdd_id_1": "e1", "rtdd_id_2": "e2"}), "e1", "e2", "dt_s", ["cc"])
    U = norm_pairs(used.rename(columns={"rtdd_id_1": "e1", "rtdd_id_2": "e2"}), "e1", "e2", "dt_s", ["cc"])
    key = ["ev_lo", "ev_hi", "station", "phase"]
    rows = []
    for subset, ref, rmask in (("both_cc07", U, lambda d: d.coefficient.abs() >= CC_MIN),
                               ("both_measured", M, lambda d: np.ones(len(d), bool))):
        j = R[rmask(R)].merge(ref, on=key, suffixes=("_rtdd", "_ref"))
        for sub2, mask in (("all", np.ones(len(j), bool)),
                           ("without_event3", (j.ev_lo != SPECIAL_EVENT) & (j.ev_hi != SPECIAL_EVENT)),
                           ("event3_pairs_only", (j.ev_lo == SPECIAL_EVENT) | (j.ev_hi == SPECIAL_EVENT)),
                           ("P", j.phase == "P"), ("S", j.phase == "S"),
                           # rtDD accepts |CC| >= minCoef, i.e. also anti-correlated windows; the reference
                           # kept only CC >= +0.7
                           ("rtdd_cc_positive", j.coefficient > 0), ("rtdd_cc_negative", j.coefficient < 0),
                           ("P_rtdd_cc_negative", (j.phase == "P") & (j.coefficient < 0))):
            jj = j[mask]
            if len(jj) == 0:
                continue
            diff = (jj.dt_s_rtdd - jj.dt_s_ref) * 1000.0
            grid = np.round(diff)                # both data sets are on a 1-ms grid: compare on the grid
            med = float(np.median(diff))
            rows.append(dict(run=run, triplets=subset, subset=sub2, n=int(len(jj)),
                             n_P=int((jj.phase == "P").sum()), n_S=int((jj.phase == "S").sum()),
                             dt_diff_median_ms=med, dt_diff_mad_ms=float(np.median(np.abs(diff - med))),
                             dt_diff_rms_ms=float(np.sqrt(np.mean(diff ** 2))),
                             frac_within_2ms=float(np.mean(np.abs(grid) <= 2)),
                             frac_within_5ms=float(np.mean(np.abs(grid) <= 5)),
                             dt_diff_grid_dev_max_ms=float(np.abs(diff - grid).max()),
                             cc_pearson_r=float(np.corrcoef(jj.coefficient, jj.cc)[0, 1]) if len(jj) > 2 else np.nan,
                             cc_abs_pearson_r=float(np.corrcoef(jj.coefficient.abs(), jj.cc)[0, 1]) if len(jj) > 2 else np.nan,
                             cc_rtdd_median=float(jj.coefficient.median()), cc_ref_median=float(jj.cc.median())))
    det = pd.DataFrame(rows)
    p = det[(det.triplets == "both_cc07") & (det.subset == "all")]
    if len(p):
        p = p.iloc[0]
        out.update(f_n_common_cc07=int(p.n), f_dt_diff_median_ms=p.dt_diff_median_ms, f_dt_diff_mad_ms=p.dt_diff_mad_ms,
                   f_frac_within_2ms=p.frac_within_2ms, f_frac_within_5ms=p.frac_within_5ms,
                   f_cc_pearson_r=p.cc_pearson_r, f_cc_abs_pearson_r=p.cc_abs_pearson_r)
    return out, det


def dd_stats(paths_initial, paths_final):
    """rtDD's own double-difference residual statistics from the saved initial/final DD files."""
    def load(paths):
        fs = [pd.read_csv(p) for p in paths if os.path.exists(p)]
        return pd.concat(fs) if fs else None
    ini, fin = load(paths_initial), load(paths_final)
    out = {}
    for tag, d in (("initial", ini), ("final", fin)):
        if d is None:
            continue
        d = d.copy()
        d["xc"] = d.xcorrUsed.astype(str).str.lower() == "true"
        r = d.doubleDifferenceResidual * 1000.0
        w = d.weight
        out[f"{tag}_n_dd"] = int(len(d))
        out[f"{tag}_n_dd_xcorr"] = int(d.xc.sum())
        out[f"{tag}_rms_ms_all"] = float(np.sqrt(np.mean(r ** 2)))
        pos = w > 0
        out[f"{tag}_n_dd_weight_gt0"] = int(pos.sum())
        out[f"{tag}_rms_ms_weight_gt0"] = float(np.sqrt(np.mean(r[pos] ** 2))) if pos.any() else np.nan
        out[f"{tag}_weighted_rms_ms"] = float(np.sqrt(np.sum(w * r ** 2) / np.sum(w))) if w.sum() > 0 else np.nan
        for kind, m in (("xcorr", d.xc), ("catalog", ~d.xc)):
            mm = m & pos
            out[f"{tag}_rms_ms_{kind}_weight_gt0"] = float(np.sqrt(np.mean(r[mm] ** 2))) if mm.any() else np.nan
            out[f"{tag}_n_dd_{kind}_weight_gt0"] = int(mm.sum())
    return out


def log_stats(console):
    tot = re.findall(r"Total dd (\d+), dd-residual \[msec\] median ([-\d.]+) MedianAbsoluteDeviation ([-\d.]+)",
                     open(console).read()) if os.path.exists(console) else []
    if not tot:
        return {}
    return dict(log_first_total_dd=int(tot[0][0]), log_first_dd_median_ms=float(tot[0][1]),
                log_first_dd_mad_ms=float(tot[0][2]), log_last_total_dd=int(tot[-1][0]),
                log_last_dd_median_ms=float(tot[-1][1]), log_last_dd_mad_ms=float(tot[-1][2]),
                log_n_total_dd_lines=len(tot))


def hypodd_log_stats(path):
    txt = open(path).read()
    blocks = txt.split("===ITERATION")
    last = blocks[-1]
    g = lambda pat, t: (float(re.findall(pat, t)[-1]) if re.findall(pat, t) else np.nan)
    ini = txt.split("Residual summary of initial data:")[1].split("~")[0] if "Residual summary of initial data" in txt else ""
    return dict(initial_abs_cc_rms_ms=g(r"absolute cc rms \[s\] =\s+([-\d.]+)", ini) * 1000,
                initial_abs_ct_rms_ms=g(r"absolute ct rms \[s\] =\s+([-\d.]+)", ini) * 1000,
                final_abs_cc_rms_ms=g(r"absolute cc rms \[s\] =\s+([-\d.]+)", last) * 1000,
                final_weighted_cc_rms_ms=g(r"weighted cc rms \[s\] =\s+([-\d.]+)", last) * 1000,
                final_abs_ct_rms_ms=g(r"absolute ct rms \[s\] =\s+([-\d.]+)", last) * 1000,
                final_weighted_ct_rms_ms=g(r"weighted ct rms \[s\] =\s+([-\d.]+)", last) * 1000,
                final_n_obs_cc=g(r"# obs cc =\s+(\d+)", last), final_n_obs_ct=g(r"# obs ct =\s+(\d+)", last),
                n_iterations=len(blocks) - 1)


def expected_pairs(run):
    """Number of event-pair/station/phase combinations the input picks allow (what ph2dt with MINOBS 1 forms)."""
    ph = pd.read_csv(f"{OUTROOT}/{run}/inputs/phase.csv", dtype=str, keep_default_na=False)
    n = ph.groupby(["stationCode", "type"]).size()
    return int((n * (n - 1) // 2).sum())


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    runs = []
    for d in sorted(glob.glob(f"{OUTROOT}/*/run_info.json")):
        info = json.load(open(d))
        if info.get("status") == "ok" and os.path.exists(os.path.join(os.path.dirname(d), "relocated-event.csv")):
            runs.append(info["run"])
    if not args.apply:
        print(f"[dry run] {len(runs)} finished runs: {runs}")
        return
    refs = {"hypodd_dtcc": load_reference("dtcc"), "hypodd_dtct": load_reference("dtct")}
    meas = pd.read_csv(f"{REFT}/dtcc_measured.csv", keep_default_na=False)
    used = pd.read_csv(f"{REFT}/dtcc_used.csv", keep_default_na=False)
    summ, pevs, xdet, resid, pos = [], [], [], [], []
    for rn, R in refs.items():
        pos.append(pd.DataFrame(dict(solution=rn, event_id=R["ids"], east_m=R["X"][:, 0], north_m=R["X"][:, 1],
                                     up_m=R["X"][:, 2], latitude=R["lat"], longitude=R["lon"], depth_km=R["dep"],
                                     origin_time=R["ot"].astype(str))))
    # scale rows: how different are the reference solutions themselves (same metrics, run name REF_*)
    hi = pd.read_csv(f"{REFT}/hypoinverse_kim1983.csv").sort_values("rtdd_id").reset_index(drop=True)
    extra = {"REF_hypodd_dtct": refs["hypodd_dtct"],
             "REF_hypoinverse_kim1983": dict(ids=hi.rtdd_id.values, X=enu(hi.latitude, hi.longitude, hi.depth_km),
                                             ot=pd.to_datetime(hi.origin_time), lat=hi.latitude.values,
                                             lon=hi.longitude.values, dep=hi.depth_km.values, table=hi)}
    for name, A in extra.items():
        s, pe = compare(A, refs["hypodd_dtcc"], refs["hypodd_dtcc"]["boot"])
        summ.append(dict(run=name, reference="hypodd_dtcc", **s))
        pevs.append(pe.assign(run=name, reference="hypodd_dtcc"))
    pos.append(pd.DataFrame(dict(solution="hypoinverse_kim1983", event_id=hi.rtdd_id, east_m=extra["REF_hypoinverse_kim1983"]["X"][:, 0],
                                 north_m=extra["REF_hypoinverse_kim1983"]["X"][:, 1], up_m=extra["REF_hypoinverse_kim1983"]["X"][:, 2],
                                 latitude=hi.latitude, longitude=hi.longitude, depth_km=hi.depth_km,
                                 origin_time=hi.origin_time.astype(str))))
    for run in runs:
        A = load_run(run)
        pos.append(pd.DataFrame(dict(solution=run, event_id=A["ids"], east_m=A["X"][:, 0], north_m=A["X"][:, 1],
                                     up_m=A["X"][:, 2], latitude=A["lat"], longitude=A["lon"], depth_km=A["dep"],
                                     origin_time=A["ot"].astype(str))))
        xm, xd = xcorr_metrics(run, meas, used)
        if xd is not None:
            xdet.append(xd)
        for rn, R in refs.items():
            s, pe = compare(A, R, R["boot"], refs["hypodd_dtcc"]["boot"] if rn == "hypodd_dtct" else None)
            row = dict(run=run, reference=rn, **s)
            if xm:
                row.update(xm)
            summ.append(row)
            pevs.append(pe.assign(run=run, reference=rn))
        # residual statistics
        rd = f"{OUTROOT}/{run}"
        info = json.load(open(f"{rd}/run_info.json"))
        if os.path.exists(f"{rd}/processing/cluster-1-final-double-difference.csv"):
            st = dd_stats(sorted(glob.glob(f"{rd}/processing/cluster-*-initial-double-difference.csv")),
                          sorted(glob.glob(f"{rd}/processing/cluster-*-final-double-difference.csv")))
            st.update(log_stats(f"{rd}/console.log"))
            st["expected_pairs_from_picks"] = expected_pairs(run)
        else:   # single-event runs: aggregate the 11 single-event systems (step 2 for the two-step runs)
            ini = sorted(glob.glob(f"{rd}/processing/ev*/initial-double-difference.csv") +
                         glob.glob(f"{rd}/processing/ev*/step2/initial-double-difference.csv"))
            fin = sorted(glob.glob(f"{rd}/processing/ev*/final-double-difference.csv") +
                         glob.glob(f"{rd}/processing/ev*/step2/final-double-difference.csv"))
            st = dd_stats(ini, fin)
            st["note"] = "aggregated over the 11 single-event systems (step 2 for two-step runs)"
        ev = A["table"]
        st.update(run=run, wall_time_s=info.get("wall_time_s"), n_relocated=info.get("n_relocated"),
                  event_rms_start_median_ms=float(ev.startRms.median() * 1000) if "startRms" in ev else np.nan,
                  event_rms_final_median_ms=float(ev.finalRms.median() * 1000) if "finalRms" in ev else np.nan)
        resid.append(st)
    # HypoDD reference rows
    for rn, sub in (("hypodd_dtcc", "02.dt.cc"), ("hypodd_dtct", "01.dt.ct")):
        st = hypodd_log_stats(f"{REFRUN}/{sub}/hypoDD.log")
        t = refs[rn]["table"]
        st.update(run=rn, rcc_median_ms=float(t.rcc_s[t.rcc_s >= 0].median() * 1000) if (t.rcc_s >= 0).any() else np.nan,
                  rct_median_ms=float(t.rct_s.median() * 1000),
                  note="hypoDD.log last iteration; RCC/RCT = per-event rms from hypoDD.reloc (median over events)")
        resid.append(st)
    # run vs run
    rvr, rvr_pe = [], []
    loaded = {r: load_run(r) for r in runs}
    for a, b, why in RUN_PAIRS:
        if a not in loaded or b not in loaded:
            rvr.append(dict(base=a, other=b, what_changes=why, status="missing run"))
            continue
        s, pe = compare(loaded[b], loaded[a], refs["hypodd_dtcc"]["boot"])
        s = {k.replace("c_", "c_vs_dtccboot_", 1) if k.startswith("c_") else k: v for k, v in s.items()}
        s.update(abs_rms_3d_m=float(np.sqrt(np.mean(pe.d3D_abs_m ** 2))), abs_max_3d_m=float(pe.d3D_abs_m.max()),
                 abs_rms_h_m=float(np.sqrt(np.mean(pe.dE_abs_m ** 2 + pe.dN_abs_m ** 2))),
                 abs_rms_v_m=float(np.sqrt(np.mean(pe.dU_abs_m ** 2))))
        rvr.append(dict(base=a, other=b, what_changes=why, status="ok", **s))
        rvr_pe.append(pe.assign(base=a, other=b))
    W = lambda df, n: df.to_csv(f"{OUTROOT}/{n}", index=False, float_format="%.6g")
    W(pd.DataFrame(summ), "summary_metrics.csv")
    W(pd.concat(pevs), "per_event_vs_reference.csv")
    W(pd.DataFrame(rvr), "run_vs_run_metrics.csv")
    W(pd.concat(rvr_pe), "per_event_run_vs_run.csv")
    if xdet:
        W(pd.concat(xdet), "xcorr_comparison.csv")
    W(pd.DataFrame(resid), "residual_stats.csv")
    W(pd.concat(pos), "positions_enu.csv")
    json.dump(dict(runs=runs, origin=[LAT0, LON0],
                   hypodd_convention="hypoDD.log 'Cluster centroid at' + hypoDD.reloc X/Y/Z (0.1 m); bootstrap "
                                     "half-widths unrounded from bootstrap_errors.csv",
                   hypodd_log_centroid={k: v["centroid"] for k, v in refs.items()},
                   hypodd_log_final_centroid_shift_x_y_zdown_t_m_ms={k: v["log_centroid_shift"] for k, v in refs.items()},
                   f_within_fractions="counted on the 1-ms grid: |round(diff_ms)| <= 2 / <= 5",
                   run_pairs=RUN_PAIRS, cc_min=CC_MIN, special_event=SPECIAL_EVENT),
              open(f"{OUTROOT}/analysis_summary.json", "w"), indent=1)
    print(f"analysed {len(runs)} runs")


if __name__ == "__main__":
    main()
