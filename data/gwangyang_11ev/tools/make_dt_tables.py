#!/usr/bin/env python
# make_dt_tables.py  --  step Prep (install/06_gwangyang_prep.sh, stage dtables)
#
# Tidy CSV copies of the reference HypoDD differential times (reference/gwangyang_pnplus/2.HypoDD/02.dt.cc/):
#   dtcc_measured.csv  every cross-correlation measurement in dt.cc_P/dt.cc_P_<e1>_<e2> and dt.cc_S/... (55 + 55
#                      pair files), INCLUDING coefficients below 0.7 (and any outside 0..1)
#   dtcc_used.csv      dt.cc_0.7_combined, the file hypoDD.inp reads (cc >= 0.7; P blocks then S blocks)
#   dtct.csv           dt.ct, the catalog differential times of the same HypoDD run (TT1, TT2 and their difference)
# First columns (as specified): kma_id_1, kma_id_2, rtdd_id_1, rtdd_id_2, network, station, phase, dt_s, cc
# (dtct: weight instead of cc). Extra columns: HypoDD ids, file and line of origin, catalog/SAC travel times,
# the implied cross-correlation shift, the rtDD-equivalent lag, and whether HypoDD kept the observation in its
# final iteration (02.dt.cc/hypoDD.res).
#
# SIGN CONVENTION (HypoDD; Waldhauser 2001, hypoDD manual, dt.cc and dt.ct formats):
#   for a pair line "# ID1 ID2" and a station, dt = T1 - T2 = (t1 - ot1) - (t2 - ot2)
#   t = arrival time at the station, ot = origin time of that event; i.e. the travel time of event 1 minus the
#   travel time of event 2. dt.ct writes TT1 and TT2 separately; dt.cc writes the difference directly.
#   The reference cross-correlation wrote diff = (t1 + shift - ot1) - (t2 - ot2)
#   (reference/pipeline_code/core/xcorr.py:138-140 for P, 164-166 for S; header "# id(e1) id(e2) 0.0" with e1 the
#   earlier event folder, xcorr.py:126-127, pairs from itertools.combinations in sorted order), where t1/t2 are the
#   SAC header picks and 'shift' is the measured correction of event 1's pick. OTC (3rd header value) is 0.0.
#   rtDD uses the same sign: libhdd dd.cpp:878-897 diffTime = (t_ref - ot_ref) - (t_ev - ot_ev) for the pair
#   (eventId1 = ref, eventId2 = ev), then dd.cpp:921 diffTime -= lag when the correlation passes; a reversed pair
#   gets the opposite lag (xcorrcache.h:129-137). So rtDD's corrected differential time for (ev1, ev2) is
#   dt_catalog(ev1, ev2) - lag(ev1, ev2), directly comparable with dt_s here; for a pair stored as (ev2, ev1)
#   flip the sign of both dt and lag.
#
# Run with env pyrtdd:  python make_dt_tables.py --outdir <reference_tables> --summary <json> --options-json <json>

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
HDD = f"{DATA}/reference/gwangyang_pnplus/2.HypoDD"
DTCC_DIR = f"{HDD}/02.dt.cc"
DTCC_P_GLOB = f"{DTCC_DIR}/dt.cc_P/dt.cc_P_*_*"
DTCC_S_GLOB = f"{DTCC_DIR}/dt.cc_S/dt.cc_S_*_*"
DTCC_USED = f"{DTCC_DIR}/dt.cc_0.7_combined"          # hypoDD.inp line 4 (02.dt.cc)
DTCC_P07, DTCC_S07 = f"{DTCC_DIR}/dt.cc_P_0.7", f"{DTCC_DIR}/dt.cc_S_0.7"
DTCT = f"{DTCC_DIR}/dt.ct"                            # hypoDD.inp line 6 (02.dt.cc)
DTCT_COPIES = [f"{HDD}/00.ph2dt/dt.ct", f"{HDD}/01.dt.ct/dt.ct"]   # compared byte for byte
HYPODD_INP = f"{DTCC_DIR}/hypoDD.inp"
HYPODD_RES = f"{DTCC_DIR}/hypoDD.res"                  # final-iteration residuals of the reference run
ID_MAP = f"{DATA}/inputs/rtdd_catalog/event_id_map.csv"
EVENT_CSV = f"{DATA}/inputs/rtdd_catalog/event.csv"   # origin times = .pha headers = re-referenced SAC origins
PHASE_CSV = f"{DATA}/inputs/rtdd_catalog/phase.csv"   # catalog pick times (= .pha travel times + origin)
PHASE_EXTRA = f"{DATA}/inputs/rtdd_catalog/phase_extra.csv"  # SAC header pick times (used by the cross-correlation)
STATION_CSV = f"{DATA}/inputs/rtdd_catalog/station.csv"
CC_THRESHOLD = (0.7, 1.0)                              # reference: keep threshold <= cc <= 1.0 (core/xcorr.py:186-191)
RES_IDX = {1: ("cc", "P"), 2: ("cc", "S"), 3: ("ct", "P"), 4: ("ct", "S")}   # hypoDD.res IDX column
KEY = ["hypodd_id_1", "hypodd_id_2", "network", "station", "phase"]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_dt(path, kind, sta_map):
    # kind 'cc': "# ID1 ID2 OTC" then "STA DT WGHT PHA"; kind 'ct': "# ID1 ID2" then "STA TT1 TT2 WGHT PHA"
    rows, cur = [], None
    for ln, line in enumerate(open(path), start=1):
        if not line.strip():
            continue
        tok = line.split()
        if line.startswith("#"):
            tok = line[1:].split()
            cur = (int(tok[0]), int(tok[1]), float(tok[2]) if len(tok) > 2 else np.nan)
            continue
        if cur is None:
            raise ValueError(f"{path}:{ln}: data line before the first header")
        if tok[0] not in sta_map:
            raise ValueError(f"{path}:{ln}: unknown station label {tok[0]}")
        net, sta = sta_map[tok[0]]
        r = dict(hypodd_id_1=cur[0], hypodd_id_2=cur[1], network=net, station=sta, source_file=os.path.relpath(path, DATA),
                 line_no=ln, raw_line=line.rstrip("\n"))
        if kind == "cc":
            r.update(phase=tok[3], dt_s=float(tok[1]), cc=float(tok[2]), otc_s=cur[2])
        else:
            tt1, tt2 = float(tok[1]), float(tok[2])
            r.update(phase=tok[4], dt_s=round(tt1 - tt2, 6), weight=float(tok[3]), tt1_s=tt1, tt2_s=tt2)
        rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=f"{DATA}/reference_tables")
    ap.add_argument("--summary", required=True)
    ap.add_argument("--options-json", default=None)
    args = ap.parse_args()
    problems, S = [], {}

    idm = pd.read_csv(ID_MAP, dtype={"kma_id": str})
    h2k = dict(zip(idm.hypodd_id, idm.kma_id))
    h2r = dict(zip(idm.hypodd_id, idm.rtdd_id))
    st = pd.read_csv(STATION_CSV, dtype=str, keep_default_na=False)
    sta_map = {n + s: (n, s) for n, s in zip(st.networkCode, st.stationCode)}
    if len(sta_map) != len(st):
        sys.exit("ERROR: NET+STA labels are not unique")

    # ------------------------------------------------------------------ parse
    meas = []
    for g, ph in ((DTCC_P_GLOB, "P"), (DTCC_S_GLOB, "S")):
        files = sorted(glob.glob(g))
        for f in files:
            m = re.search(r"dt\.cc_([PS])_(\d{14})_(\d{14})$", f)
            rows = parse_dt(f, "cc", sta_map)
            for r in rows:
                # the file name carries the KMA ids of the pair: must match the header's HypoDD ids
                if (h2k[r["hypodd_id_1"]], h2k[r["hypodd_id_2"]]) != (m.group(2), m.group(3)) or r["phase"] != m.group(1):
                    problems.append(f"{f}:{r['line_no']}: header ids/phase do not match the file name")
            meas.extend(rows)
        S[f"dtcc_{ph}_pair_files"] = len(files)
    meas = pd.DataFrame(meas)
    used = pd.DataFrame(parse_dt(DTCC_USED, "cc", sta_map))
    ct = pd.DataFrame(parse_dt(DTCT, "ct", sta_map))
    for name, df in (("measured", meas), ("used", used), ("dtct", ct)):
        dup = df.duplicated(KEY).sum()
        if dup:
            problems.append(f"{name}: {dup} duplicated (pair, station, phase) keys")
    # the two dt.cc_<P|S>_0.7 files and the combined file
    comb_equal = open(DTCC_USED, "rb").read() == open(DTCC_P07, "rb").read() + open(DTCC_S07, "rb").read()
    S["dtcc_used_is_P07_then_S07_bytes"] = comb_equal
    S["dtct_copies_identical"] = {p: md5(p) == md5(DTCT) for p in DTCT_COPIES}
    S["hypoDD_inp_reads"] = [l.strip() for l in open(HYPODD_INP).read().splitlines()[3:6:2]]

    # ------------------------------------------------------------------ add ids, catalog and SAC travel times
    ev = pd.read_csv(EVENT_CSV)
    ot = {r.id: pd.Timestamp(r.isotime) for r in ev.itertuples()}
    ph = pd.read_csv(PHASE_CSV, dtype=str, keep_default_na=False)
    pe = pd.read_csv(PHASE_EXTRA, dtype=str, keep_default_na=False)
    tt_cat = {(int(r.eventId), r.networkCode, r.stationCode, r.type): (pd.Timestamp(r.isotime) - ot[int(r.eventId)]).total_seconds()
              for r in ph.itertuples()}
    tt_sac = {(int(r.eventId), r.networkCode, r.stationCode, r.type): (pd.Timestamp(r.sac_header_time) - ot[int(r.eventId)]).total_seconds()
              for r in pe.itertuples()}

    def enrich(df):
        df.insert(0, "kma_id_1", df.hypodd_id_1.map(h2k))
        df.insert(1, "kma_id_2", df.hypodd_id_2.map(h2k))
        df.insert(2, "rtdd_id_1", df.hypodd_id_1.map(h2r))
        df.insert(3, "rtdd_id_2", df.hypodd_id_2.map(h2r))
        k1 = list(zip(df.rtdd_id_1, df.network, df.station, df.phase))
        k2 = list(zip(df.rtdd_id_2, df.network, df.station, df.phase))
        df["tt1_catalog_s"] = [tt_cat.get(k, np.nan) for k in k1]
        df["tt2_catalog_s"] = [tt_cat.get(k, np.nan) for k in k2]
        df["dt_catalog_s"] = (df.tt1_catalog_s - df.tt2_catalog_s).round(6)
        return df

    for df in (meas, used, ct):
        enrich(df)
    for df in (meas, used):
        df["tt1_sac_s"] = [tt_sac.get(k, np.nan) for k in zip(df.rtdd_id_1, df.network, df.station, df.phase)]
        df["tt2_sac_s"] = [tt_sac.get(k, np.nan) for k in zip(df.rtdd_id_2, df.network, df.station, df.phase)]
        # reference: dt = (t1 + shift - ot1) - (t2 - ot2) with the SAC header picks -> shift = dt - (tt1_sac - tt2_sac)
        df["xcorr_shift_s"] = (df.dt_s - (df.tt1_sac_s - df.tt2_sac_s)).round(6)
        # rtDD: dt = dt_catalog - lag  ->  the lag rtDD would need (same event order) to give this dt
        df["rtdd_equivalent_lag_s"] = (df.dt_catalog_s - df.dt_s).round(6)
        df["cc_passes_0p7"] = (df.cc >= CC_THRESHOLD[0]) & (df.cc <= CC_THRESHOLD[1])

    # ------------------------------------------------------------------ cross-links between the tables
    um = meas.merge(used[KEY + ["dt_s", "cc"]], on=KEY, how="left", suffixes=("", "_used"), indicator=True)
    meas["in_dtcc_used"] = (um["_merge"] == "both").values
    same_vals = (um.loc[um["_merge"] == "both", "dt_s"] == um.loc[um["_merge"] == "both", "dt_s_used"]).all() and \
                (um.loc[um["_merge"] == "both", "cc"] == um.loc[um["_merge"] == "both", "cc_used"]).all()
    used_not_in_meas = len(used.merge(meas[KEY], on=KEY, how="left", indicator=True).query("_merge == 'left_only'"))
    filt_equal = (meas.in_dtcc_used == meas.cc_passes_0p7).all()
    S["used_equals_measured_filtered"] = bool(filt_equal and same_vals and used_not_in_meas == 0)
    if not S["used_equals_measured_filtered"]:
        problems.append(f"dt.cc_0.7_combined is not exactly the measured lines with {CC_THRESHOLD[0]} <= cc <= "
                        f"{CC_THRESHOLD[1]} (filter equal {filt_equal}, values equal {same_vals}, extra {used_not_in_meas})")
    for df in (meas, used):
        m = df.merge(ct[KEY + ["dt_s"]].rename(columns={"dt_s": "dt_ct_s"}), on=KEY, how="left")
        df["in_dtct"] = m.dt_ct_s.notna().values
        df["dt_ct_s"] = m.dt_ct_s.values
    # dt.ct travel times vs the catalog (pick - origin), 3 decimals in the file
    ct["tt_file_minus_catalog_max_abs_s"] = np.maximum((ct.tt1_s - ct.tt1_catalog_s).abs(), (ct.tt2_s - ct.tt2_catalog_s).abs()).round(6)
    # final iteration of the reference HypoDD run
    res = pd.read_csv(HYPODD_RES, sep=r"\s+", skiprows=1, header=None,
                      names=["sta", "DT", "C1", "C2", "IDX", "QUAL", "RES_ms", "WT", "OFFS_m"])
    res["kind"] = res.IDX.map(lambda i: RES_IDX[i][0])
    res["phase"] = res.IDX.map(lambda i: RES_IDX[i][1])
    res["network"] = res.sta.map(lambda x: sta_map[x][0])
    res["station"] = res.sta.map(lambda x: sta_map[x][1])
    res = res.rename(columns={"C1": "hypodd_id_1", "C2": "hypodd_id_2"})
    for name, df, kind in (("used", used, "cc"), ("dtct", ct, "ct")):
        r = res[res.kind == kind][KEY + ["DT", "RES_ms", "WT"]]
        m = df.merge(r, on=KEY, how="left")
        df["kept_in_final_iteration"] = m.DT.notna().values
        df["final_residual_ms"] = m.RES_ms.values
        df["final_weight"] = m.WT.values
        both = m.DT.notna()
        d = (m.DT[both] - m.dt_s[both]).abs()
        S[f"hypodd_res_{name}"] = dict(rows_in_res=int((res.kind == kind).sum()), matched=int(both.sum()),
                                       max_abs_DT_minus_dt_s=float(d.max()) if len(d) else None)
        # tolerance 1e-5 s: hypoDD.res prints DT with fewer digits than dt.ct (1.8e-6 s rounding seen);
        # the differential times themselves are given to 1 ms, so 10 microseconds is still 100x finer
        if both.sum() != (res.kind == kind).sum() or (len(d) and d.max() > 1e-5):
            problems.append(f"hypoDD.res {kind} rows do not all match {name} with the same DT")

    # ------------------------------------------------------------------ sign checks
    both = meas[meas.in_dtct]
    S["sign_check_measured_vs_dtct"] = dict(
        n=len(both), pearson_r=float(np.corrcoef(both.dt_s, both.dt_ct_s)[0, 1]),
        median_abs_dtcc_minus_dtct_ms=float((both.dt_s - both.dt_ct_s).abs().median() * 1000),
        median_abs_dtcc_plus_dtct_ms=float((both.dt_s + both.dt_ct_s).abs().median() * 1000),
        fraction_closer_with_same_sign=float(((both.dt_s - both.dt_ct_s).abs() < (both.dt_s + both.dt_ct_s).abs()).mean()))
    for name, df in (("measured", meas), ("used", used)):
        sh = df.xcorr_shift_s.abs()
        S[f"xcorr_shift_{name}"] = dict(n=int(sh.notna().sum()), median_abs_ms=float(sh.median() * 1000),
                                        p95_abs_ms=float(sh.quantile(0.95) * 1000), max_abs_ms=float(sh.max() * 1000),
                                        on_1ms_grid_within_0p02ms=float(((df.xcorr_shift_s * 1000 - (df.xcorr_shift_s * 1000).round()).abs() < 0.02).mean()),
                                        missing_sac_pick=int(df.xcorr_shift_s.isna().sum()))

    # ------------------------------------------------------------------ counts and value ranges
    for name, df in (("measured", meas), ("used", used)):
        S[f"dtcc_{name}"] = dict(rows=len(df), P=int((df.phase == "P").sum()), S=int((df.phase == "S").sum()),
                                 pairs=int(df[["hypodd_id_1", "hypodd_id_2"]].drop_duplicates().shape[0]),
                                 stations=int(df.station.nunique()), cc_min=float(df.cc.min()), cc_max=float(df.cc.max()),
                                 cc_below_0p7=int((df.cc < 0.7).sum()), cc_negative=int((df.cc < 0).sum()),
                                 cc_above_1=int((df.cc > 1).sum()), dt_min_s=float(df.dt_s.min()), dt_max_s=float(df.dt_s.max()),
                                 otc_values=sorted(set(df.otc_s.astype(float))))
    S["dtcc_used"]["kept_in_final_iteration"] = int(used.kept_in_final_iteration.sum())
    S["dtct"] = dict(rows=len(ct), P=int((ct.phase == "P").sum()), S=int((ct.phase == "S").sum()),
                     pairs=int(ct[["hypodd_id_1", "hypodd_id_2"]].drop_duplicates().shape[0]), stations=int(ct.station.nunique()),
                     weights=sorted(set(ct.weight)), dt_min_s=float(ct.dt_s.min()), dt_max_s=float(ct.dt_s.max()),
                     tt_vs_catalog_max_abs_s=float(ct.tt_file_minus_catalog_max_abs_s.max()),
                     kept_in_final_iteration=int(ct.kept_in_final_iteration.sum()))
    if S["dtct"]["tt_vs_catalog_max_abs_s"] > 0.0005:
        problems.append("dt.ct travel times differ from the catalog (phase.csv - event.csv) by more than 0.5 ms")
    S["first_pair_order_hypodd_ids_increasing"] = bool(((meas.hypodd_id_1 < meas.hypodd_id_2).all()
                                                        and (ct.hypodd_id_1 < ct.hypodd_id_2).all()))

    # ------------------------------------------------------------------ write
    lead = ["kma_id_1", "kma_id_2", "rtdd_id_1", "rtdd_id_2", "network", "station", "phase", "dt_s"]
    cc_cols = lead + ["cc", "hypodd_id_1", "hypodd_id_2", "otc_s", "cc_passes_0p7", "tt1_catalog_s", "tt2_catalog_s",
                      "dt_catalog_s", "tt1_sac_s", "tt2_sac_s", "xcorr_shift_s", "rtdd_equivalent_lag_s", "in_dtct", "dt_ct_s"]
    out_meas = meas[cc_cols + ["in_dtcc_used", "source_file", "line_no"]]
    out_used = used[cc_cols + ["kept_in_final_iteration", "final_residual_ms", "final_weight", "source_file", "line_no"]]
    out_ct = ct[lead + ["weight", "hypodd_id_1", "hypodd_id_2", "tt1_s", "tt2_s", "tt1_catalog_s", "tt2_catalog_s",
                        "dt_catalog_s", "tt_file_minus_catalog_max_abs_s", "kept_in_final_iteration", "final_residual_ms",
                        "final_weight", "source_file", "line_no"]]
    os.makedirs(args.outdir, exist_ok=True)
    paths = {n: os.path.join(args.outdir, n) for n in ("dtcc_measured.csv", "dtcc_used.csv", "dtct.csv")}
    out_meas.to_csv(paths["dtcc_measured.csv"], index=False)
    out_used.to_csv(paths["dtcc_used.csv"], index=False)
    out_ct.to_csv(paths["dtct.csv"], index=False)
    S["outputs"] = {p: md5(p) for p in paths.values()}
    S["problems"] = problems
    S["sign_convention"] = ("dt_s = (t1 - ot1) - (t2 - ot2): travel time of event 1 (kma_id_1/rtdd_id_1) minus travel "
                            "time of event 2 at that station; HypoDD dt.cc/dt.ct convention; rtDD: dt = dt_catalog - lag")
    S["column_descriptions"] = {
        "dt_s": "differential travel time (s), event 1 minus event 2 (dt.cc: as written; dt.ct: TT1 - TT2)",
        "cc": "cross-correlation coefficient written by the reference (also HypoDD's weight)",
        "weight": "dt.ct weight (mean of the two .pha pick weights)",
        "tt1_catalog_s/tt2_catalog_s": "catalog travel time = phase.csv pick - event.csv origin (= .pha travel time)",
        "dt_catalog_s": "tt1_catalog_s - tt2_catalog_s (what dt.ct holds for this station/phase if ph2dt kept it)",
        "tt1_sac_s/tt2_sac_s": "SAC header pick (phase_extra.sac_header_time) - origin: the picks the reference correlated around",
        "xcorr_shift_s": "implied correction of event 1's pick by the reference cross-correlation: dt_s - (tt1_sac_s - tt2_sac_s)",
        "rtdd_equivalent_lag_s": "the rtDD lag (xcorr.csv, same event order) that gives the same dt from the catalog picks: dt_catalog_s - dt_s",
        "in_dtct/dt_ct_s": "the same pair/station/phase exists in dt.ct, and its TT1 - TT2",
        "cc_passes_0p7": "0.7 <= cc <= 1.0 (the reference threshold)",
        "in_dtcc_used": "the line is in dt.cc_0.7_combined",
        "kept_in_final_iteration/final_residual_ms/final_weight": "listed in 02.dt.cc/hypoDD.res (the last of 28 iterations): kept, its residual (ms) and weight",
        "source_file/line_no": "where the value was read (relative to data/gwangyang_11ev)"}
    with open(args.summary, "w") as fo:
        json.dump(S, fo, indent=1, default=str)

    print(f"[dtcc measured] {len(meas)} lines (P {S['dtcc_measured']['P']}, S {S['dtcc_measured']['S']}) from "
          f"{S['dtcc_P_pair_files']} + {S['dtcc_S_pair_files']} pair files; cc {S['dtcc_measured']['cc_min']:.3f}.."
          f"{S['dtcc_measured']['cc_max']:.3f}; below 0.7: {S['dtcc_measured']['cc_below_0p7']}; negative: "
          f"{S['dtcc_measured']['cc_negative']}; above 1: {S['dtcc_measured']['cc_above_1']}; OTC values {S['dtcc_measured']['otc_values']}")
    print(f"[dtcc used]     {len(used)} lines (P {S['dtcc_used']['P']}, S {S['dtcc_used']['S']}); == measured lines with "
          f"0.7 <= cc <= 1.0, same values: {S['used_equals_measured_filtered']}; file == dt.cc_P_0.7 + dt.cc_S_0.7: {comb_equal}; "
          f"kept by HypoDD in its last iteration: {S['dtcc_used']['kept_in_final_iteration']}")
    print(f"[dtct]          {len(ct)} lines (P {S['dtct']['P']}, S {S['dtct']['S']}), {S['dtct']['pairs']} pairs, "
          f"{S['dtct']['stations']} stations; TT1/TT2 vs catalog (pick - origin): max |diff| {S['dtct']['tt_vs_catalog_max_abs_s']} s; "
          f"identical to {', '.join(os.path.relpath(p, HDD) for p, v in S['dtct_copies_identical'].items() if v)}; "
          f"kept in last iteration: {S['dtct']['kept_in_final_iteration']}")
    sc = S["sign_check_measured_vs_dtct"]
    print(f"[sign] {sc['n']} measured cc values that also have a dt.ct line: Pearson r(dt.cc, dt.ct) = {sc['pearson_r']:.4f}; "
          f"median |dt.cc - dt.ct| = {sc['median_abs_dtcc_minus_dtct_ms']:.1f} ms vs median |dt.cc + dt.ct| = "
          f"{sc['median_abs_dtcc_plus_dtct_ms']:.1f} ms; same-sign closer in {100 * sc['fraction_closer_with_same_sign']:.1f} %")
    for name in ("measured", "used"):
        x = S[f"xcorr_shift_{name}"]
        print(f"[sign] implied reference shift ({name}): median |shift| {x['median_abs_ms']:.1f} ms, 95 % {x['p95_abs_ms']:.1f} ms, "
              f"max {x['max_abs_ms']:.1f} ms; on the 1 ms grid: {100 * x['on_1ms_grid_within_0p02ms']:.1f} %; "
              f"missing SAC pick: {x['missing_sac_pick']}")
    for name in ("used", "dtct"):
        x = S[f"hypodd_res_{name}"]
        print(f"[hypoDD.res] {name}: {x['matched']}/{x['rows_in_res']} final-iteration rows found with the same pair order; "
              f"max |DT - dt_s| {x['max_abs_DT_minus_dt_s']}")
    print(f"[write] {', '.join(paths.values())}")
    if args.options_json:
        json.dump(dict(script=os.path.abspath(__file__), run_time=datetime.datetime.now().astimezone().isoformat(),
                       argv=sys.argv, args=vars(args), CC_THRESHOLD=CC_THRESHOLD, RES_IDX=RES_IDX,
                       inputs={p: md5(p) for p in [DTCC_USED, DTCC_P07, DTCC_S07, DTCT, *DTCT_COPIES, HYPODD_INP, HYPODD_RES,
                                                    ID_MAP, EVENT_CSV, PHASE_CSV, PHASE_EXTRA, STATION_CSV]},
                       pair_file_globs=[DTCC_P_GLOB, DTCC_S_GLOB],
                       versions=dict(python=sys.version.split()[0], pandas=pd.__version__, numpy=np.__version__),
                       n_problems=len(problems)), open(args.options_json, "w"), indent=1, default=str)
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("[ok] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
