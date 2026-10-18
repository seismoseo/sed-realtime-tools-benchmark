# v09_pick_stats.py -- independent verifier of step 09 (DL picker on the 11 Gwangyang events), part 1.
# Env: pyrtdd (numpy, pandas, scipy, obspy, lxml). Run with 'python -I'.
#
# Written from scratch for the verification. It does NOT import or copy any step-09 helper. It reads only
# raw inputs: the picks.xml files written by scautopick, the PhaseNet+ reference table, the HYPOINVERSE
# catalog, the bindings XML and the headers of the sorted playback miniSEED files. Step-09 result tables
# (dl_picks_all.csv, summary_by_model.csv, by_magnitude.csv) are read ONLY at the end, to compare numbers.
#
# What it recomputes, and why:
#   1. Recall, precision, F1 and pick-time statistics per variant and phase (the claim to verify).
#      Matching: same event run, same station, same phase, |dt| <= tolerance (P 0.5 s, S 1.0 s), one-to-one.
#      Two one-to-one rules, so that the result does not hinge on one implementation:
#        greedy  : candidate pairs taken in order of increasing |dt| (the rule the step-09 notes state);
#        optimal : the largest number of pairs, then the smallest total |dt| (scipy linear_sum_assignment).
#      Two DL sets for the matching: all picks of the run (as the step-09 notes do) and only the picks inside
#      the event window (consistent with the precision denominator).
#   2. Windows and tolerances: event window = HYPOINVERSE origin - WIN_BEFORE .. + WIN_AFTER. The origin is
#      read from reference_tables/hypoinverse_kim1983.csv; inputs/rtdd_catalog/event.csv (which step 09 used)
#      is compared with it.
#   3. Denominators: every reference pick must sit at a station that is bound for scautopick
#      (bindings_config.xml: setup 'scautopick' enabled, detecStream) AND whose bound sensor has Z, N and E
#      data in that event's playback file. DL picks must come only from bound stations.
#   4. Sensitivity (disclosed, not used to judge the claim): the same numbers with tighter tolerances.
#
# Time arithmetic is done in integer nanoseconds (obspy UTCDateTime.ns), so tolerance tests are exact.
# Usage: python -I v09_pick_stats.py            # dry run: compute and print, write nothing
#        python -I v09_pick_stats.py --apply    # also write CSV/JSON into OUT_DIR

import argparse
import glob
import json
import os
import sys

import numpy as np
import obspy
import pandas as pd
from lxml import etree
from scipy.optimize import linear_sum_assignment

# ------------------------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
RUN09 = f"{PROJECT}/runs/gwangyang/dlpicker"                 # step-09 run folder (read only)
OUT_DIR = f"{PROJECT}/runs/verify_gwangyang_dl/out/picks"    # this verifier's output
VARIANTS = ["phasenet_original", "phasenet_instance", "eqtransformer_stead", "phasenet_stead",
            "phasenet_instance_fast"]
MAIN_MODELS = ["phasenet_original", "phasenet_instance", "eqtransformer_stead", "phasenet_stead"]
TOL = {"P": 0.5, "S": 1.0}               # matching tolerances stated in the step-09 notes [s]
WIN_BEFORE, WIN_AFTER = 5.0, 60.0         # event window stated in the step-09 notes [s]
SENS_TOL = [(0.3, 0.6), (0.2, 0.4), (0.1, 0.2)]   # tighter (P, S) tolerances for the sensitivity table
ML_SPLIT = 1.5                            # magnitude classes as in the notes (ML < 1.5 / >= 1.5)
NS = 1_000_000_000


def ns(t):
    return obspy.UTCDateTime(t).ns


# ------------------------------------------------------------------------------------------- readers
def read_picks_xml(path):
    """All <pick> elements of an SCML file -> list of dicts (own parser, lxml)."""
    tree = etree.parse(path)
    rows = []
    for p in tree.iter("{*}pick"):
        wf = p.find("{*}waveformID")
        com = {}
        for c in p.findall("{*}comment"):
            com[c.findtext("{*}id")] = c.findtext("{*}text")
        # P picks carry the model value in 'confidence' (and the same number in 'SNR'); S picks only in 'SNR'
        # (extraPickComments = true). conf = 'confidence' if present, else 'SNR'.
        conf_c = float(com["confidence"]) if "confidence" in com else np.nan
        snr_c = float(com["SNR"]) if "SNR" in com else np.nan
        rows.append(dict(pick_id=p.get("publicID"), t_ns=ns(p.find("{*}time/{*}value").text),
                         net=wf.get("networkCode"), sta=wf.get("stationCode"), cha=wf.get("channelCode"),
                         method=p.findtext("{*}methodID"), phase=p.findtext("{*}phaseHint"),
                         conf=conf_c if np.isfinite(conf_c) else snr_c, conf_comment=conf_c, snr_comment=snr_c,
                         ref_pick_id=com.get("RefPickID", "")))
    return rows


def read_bindings(path):
    """station -> dict(scautopick_enabled, detecStream) from a SeisComP config XML (bindings2cfg output)."""
    tree = etree.parse(path)
    psets = {}
    for ps in tree.iter("{*}parameterSet"):
        d = {}
        for par in ps.findall("{*}parameter"):
            d[par.findtext("{*}name")] = par.findtext("{*}value")
        psets[ps.get("publicID")] = dict(params=d, base=ps.findtext("{*}baseID"))
    out = {}
    for st in tree.iter("{*}station"):
        if st.get("stationCode") is None:
            continue
        setups = {s.get("name"): (s.get("enabled") == "true", s.findtext("{*}parameterSetID"))
                  for s in st.findall("{*}setup")}
        det = None
        if "default" in setups and setups["default"][1] in psets:
            det = psets[setups["default"][1]]["params"].get("detecStream")
        out[st.get("stationCode")] = dict(net=st.get("networkCode"), station_enabled=st.get("enabled") == "true",
                                          scautopick_enabled=setups.get("scautopick", (False, None))[0],
                                          detecStream=det)
    return out


# ------------------------------------------------------------------------------------------- matching
def match_greedy(ref_t, dl_t, tol_ns):
    """ref_t, dl_t: int ns arrays of ONE station/phase. Pairs in order of increasing |dt| (ties: signed dt,
    then indices), each pick used once. Returns list of (i_ref, j_dl, dt_ns)."""
    cand = []
    for i, r in enumerate(ref_t):
        for j, s in enumerate(dl_t):
            d = int(s) - int(r)
            if abs(d) <= tol_ns:
                cand.append((abs(d), d, i, j))
    cand.sort()
    ui, uj, out = set(), set(), []
    for _, d, i, j in cand:
        if i in ui or j in uj:
            continue
        ui.add(i)
        uj.add(j)
        out.append((i, j, d))
    return out


def match_optimal(ref_t, dl_t, tol_ns):
    """Maximum number of pairs within tolerance, then minimum total |dt| (Hungarian, big-M for forbidden)."""
    if len(ref_t) == 0 or len(dl_t) == 0:
        return []
    d = np.subtract.outer(np.asarray(dl_t, dtype=np.int64), np.asarray(ref_t, dtype=np.int64)).T  # [ref, dl]
    ok = np.abs(d) <= tol_ns
    if not ok.any():
        return []
    big = 1e6
    cost = np.where(ok, np.abs(d) / NS, big)
    ri, cj = linear_sum_assignment(cost)
    return [(int(i), int(j), int(d[i, j])) for i, j in zip(ri, cj) if ok[i, j]]


def dt_stats(dts_s):
    a = np.asarray(dts_s, dtype=float)
    if len(a) == 0:
        return dict(n_pairs=0)
    ad = np.abs(a)
    return dict(n_pairs=int(len(a)), median_abs_dt_s=float(np.median(ad)),
                mad_s=float(np.median(np.abs(a - np.median(a)))),
                p95_abs_dt_s=float(np.percentile(ad, 95)),
                p95_abs_dt_s_nearest_rank=float(np.sort(ad)[int(np.ceil(0.95 * len(ad))) - 1]),
                mean_dt_s=float(a.mean()), median_dt_s=float(np.median(a)), max_abs_dt_s=float(ad.max()))


def prf(n_ref, n_m_ref, n_dl, n_m_dl):
    r = n_m_ref / n_ref if n_ref else np.nan
    p = n_m_dl / n_dl if n_dl else np.nan
    f = 2 * r * p / (r + p) if (n_ref and n_dl and r + p > 0) else np.nan
    return r, p, f


# ------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write CSV/JSON to OUT_DIR (default: dry run)")
    a = ap.parse_args()

    settings = dict(script=os.path.abspath(__file__), PROJECT=PROJECT, DATA=DATA, RUN09=RUN09, OUT_DIR=OUT_DIR,
                    VARIANTS=VARIANTS, MAIN_MODELS=MAIN_MODELS, TOL=TOL, WIN_BEFORE=WIN_BEFORE,
                    WIN_AFTER=WIN_AFTER, SENS_TOL=SENS_TOL, ML_SPLIT=ML_SPLIT,
                    versions=dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__,
                                  obspy=obspy.__version__, lxml=".".join(map(str, etree.LXML_VERSION))))
    checks = {}

    # --- catalog: HYPOINVERSE origins (reference table) and the event.csv step 09 used
    hyp = pd.read_csv(f"{DATA}/reference_tables/hypoinverse_kim1983.csv", dtype={"kma_id": str})
    idm = pd.read_csv(f"{DATA}/reference_tables/event_id_map.csv", dtype={"kma_id": str})
    evcsv = pd.read_csv(f"{DATA}/inputs/rtdd_catalog/event.csv")
    ev = hyp[["rtdd_id", "kma_id", "origin_time"]].merge(idm[["rtdd_id", "kma_ml"]], on="rtdd_id")
    ev = ev.merge(evcsv[["id", "isotime"]].rename(columns={"id": "rtdd_id"}), on="rtdd_id")
    ev["o_ns"] = [ns(t) for t in ev["origin_time"]]
    ev["o_evcsv_ns"] = [ns(t) for t in ev["isotime"]]
    checks["origin_hypoinverse_vs_eventcsv_max_abs_s"] = float(np.abs(ev["o_ns"] - ev["o_evcsv_ns"]).max() / NS)
    ev["w0"] = ev["o_ns"] - int(WIN_BEFORE * NS)
    ev["w1"] = ev["o_ns"] + int(WIN_AFTER * NS)
    ev = ev.set_index("kma_id")
    kmas = list(ev.index)

    # --- reference picks
    ref = pd.read_csv(f"{DATA}/reference_tables/picks_phasenet_plus.csv", dtype={"kma_id": str})
    ref["t_ns"] = [ns(t) for t in ref["time"]]
    ref["rel_origin_s"] = [(t - ev.loc[k, "o_ns"]) / NS for k, t in zip(ref["kma_id"], ref["t_ns"])]
    ref["in_window"] = [(ev.loc[k, "w0"] <= t <= ev.loc[k, "w1"]) for k, t in zip(ref["kma_id"], ref["t_ns"])]
    checks["reference_counts"] = dict(total=len(ref), P=int((ref.phase == "P").sum()), S=int((ref.phase == "S").sum()),
                                      stations=int(ref.station.nunique()),
                                      outside_event_window=int((~ref["in_window"]).sum()),
                                      rel_origin_range_s=[float(ref.rel_origin_s.min()), float(ref.rel_origin_s.max())],
                                      duplicates_event_station_phase=int(ref.duplicated(["kma_id", "station", "phase"]).sum()))

    # --- bindings and data availability
    bnd = read_bindings(f"{RUN09}/config/bindings_config.xml")
    sta_csv = pd.read_csv(f"{DATA}/inputs/rtdd_catalog/station.csv")
    bound = {s: d["detecStream"] for s, d in bnd.items() if d["station_enabled"] and d["scautopick_enabled"]}
    sb_csv = pd.read_csv(f"{RUN09}/config/stations_bound.csv")
    avail = {}            # (kma, station) -> set of channel codes in the sorted playback file
    stations_in_data = set()
    for k in kmas:
        st = obspy.read(f"{RUN09}/input/{k}_sorted.mseed", headonly=True)
        for tr in st:
            avail.setdefault((k, tr.stats.station), set()).add(tr.stats.channel)
            stations_in_data.add(tr.stats.station)
    sensor_mismatch, no_data_ref, partial = [], [], []
    for r in ref.itertuples():
        sen = bound.get(r.station)
        if sen is None:
            continue
        chans = avail.get((r.kma_id, r.station), set())
        if not {sen + c for c in "ZNE"} <= chans:
            no_data_ref.append((r.kma_id, r.station, r.phase, sorted(chans)))
        if r.channel[:2] != sen:
            sensor_mismatch.append((r.kma_id, r.station, r.phase, r.channel, sen))
    for (k, s), chans in avail.items():
        sen = bound.get(s)
        if sen is not None and not {sen + c for c in "ZNE"} <= chans:
            partial.append((k, s, sorted(chans)))
    checks["bindings"] = dict(
        n_station_elements=len(bnd), n_bound_scautopick=len(bound),
        detecStream_counts=pd.Series(list(bound.values())).value_counts().to_dict(),
        stations_in_station_csv=int(len(sta_csv)),
        station_csv_not_bound=sorted(set(sta_csv.stationCode) - set(bound)),
        bound_not_in_station_csv=sorted(set(bound) - set(sta_csv.stationCode)),
        stations_in_data_not_bound=sorted(stations_in_data - set(bound)),
        bound_without_any_data=sorted(set(bound) - stations_in_data),
        stations_bound_csv_agrees=bool(set(sb_csv.loc[sb_csv.bound == 1, "station"]) == set(bound) and all(
            bound[s] == sen for s, sen in zip(sb_csv.station, sb_csv.sensor) if s in bound)),
        reference_picks_at_unbound_stations=int((~ref.station.isin(list(bound))).sum()),
        reference_picks_without_bound_ZNE_data=no_data_ref,
        reference_pick_channel_sensor_differs_from_bound_sensor=sensor_mismatch,
        station_event_files_with_incomplete_bound_ZNE=partial,
        station_event_pairs_with_data=len(avail),
        other_channels_present=sorted({c for (k, s), cs in avail.items() for c in cs
                                       if bound.get(s) is None or c[:2] != bound.get(s)}))

    # --- DL picks
    rows = []
    for v in VARIANTS:
        for k in kmas:
            for p in read_picks_xml(f"{RUN09}/output/{v}/{k}/picks.xml"):
                p.update(variant=v, kma_id=k)
                rows.append(p)
    dl = pd.DataFrame(rows)
    dl["in_window"] = [(ev.loc[k, "w0"] <= t <= ev.loc[k, "w1"]) for k, t in zip(dl["kma_id"], dl["t_ns"])]
    dl["rel_origin_s"] = [(t - ev.loc[k, "o_ns"]) / NS for k, t in zip(dl["kma_id"], dl["t_ns"])]
    checks["dl_picks"] = dict(
        total=len(dl), methods=dl.groupby(["method", "phase"]).size().rename("n").reset_index().to_dict("records"),
        at_unbound_station=int((~dl.sta.isin(list(bound))).sum()),
        channel_not_bound_sensor_Z=int(sum(c != bound.get(s, "??") + "Z" for s, c in zip(dl.sta, dl.cha))),
        P_confidence_equals_SNR_comment=bool(np.allclose(dl.loc[dl.phase == "P", "conf_comment"],
                                                         dl.loc[dl.phase == "P", "snr_comment"])),
        S_picks_with_confidence_comment=int(dl.loc[dl.phase == "S", "conf_comment"].notna().sum()),
        picks_without_any_value=int(dl.conf.isna().sum()),
        within_1s_of_window_edge=int(sum(min(abs(t - ev.loc[k, "w0"]), abs(t - ev.loc[k, "w1"])) <= NS
                                         for k, t in zip(dl.kma_id, dl.t_ns))))
    dl["dl_idx"] = np.arange(len(dl))

    # --- matching: rule x DL set, for the stated tolerances and the sensitivity tolerances
    def run_matching(rule, dlset, tol):
        f = match_greedy if rule == "greedy" else match_optimal
        recs = []
        for v in VARIANTS:
            for k in kmas:
                for ph in ("P", "S"):
                    R = ref[(ref.kma_id == k) & (ref.phase == ph)]
                    D = dl[(dl.variant == v) & (dl.kma_id == k) & (dl.phase == ph)]
                    if dlset == "in_window":
                        D = D[D.in_window]
                    for s in sorted(set(R.station) | set(D.sta)):
                        Rs, Ds = R[R.station == s], D[D.sta == s]
                        for i, j, d in f(Rs.t_ns.to_numpy(), Ds.t_ns.to_numpy(), int(round(tol[ph] * NS))):
                            recs.append(dict(variant=v, kma_id=k, phase=ph, station=s, ref_row=int(Rs.index[i]),
                                             dl_idx=int(Ds.dl_idx.iloc[j]), dt_s=d / NS))
        return pd.DataFrame(recs, columns=["variant", "kma_id", "phase", "station", "ref_row", "dl_idx", "dt_s"])

    def summarize(m, label):
        out = []
        for v in VARIANTS:
            mv = m[m.variant == v]
            for ph in ("P", "S", "P+S"):
                phs = ["P", "S"] if ph == "P+S" else [ph]
                n_ref = int(ref.phase.isin(phs).sum())
                mm = mv[mv.phase.isin(phs)]
                dv = dl[(dl.variant == v) & dl.phase.isin(phs)]
                n_dl_win = int(dv.in_window.sum())
                n_dl_win_m = int(dl.loc[mm.dl_idx, "in_window"].sum())
                r, p, f = prf(n_ref, len(mm), n_dl_win, n_dl_win_m)
                d = dict(rule=label, variant=v, phase=ph, n_ref=n_ref, n_matched_ref=len(mm), recall=r,
                         n_dl_total=len(dv), n_dl_in_window=n_dl_win, n_dl_in_window_matched=n_dl_win_m,
                         precision=p, f1=f)
                d.update(dt_stats(mm.dt_s))
                out.append(d)
        return out

    rows_sum, matches = [], {}
    for rule in ("greedy", "optimal"):
        for dlset in ("all", "in_window"):
            m = run_matching(rule, dlset, TOL)
            matches[(rule, dlset)] = m
            rows_sum += summarize(m, f"{rule}|{dlset}")
    summ = pd.DataFrame(rows_sum)
    for ptol, stol in SENS_TOL:
        m = run_matching("greedy", "all", {"P": ptol, "S": stol})
        summ = pd.concat([summ, pd.DataFrame(summarize(m, f"greedy|all|P{ptol}|S{stol}"))], ignore_index=True)

    # magnitude classes (stated rule: greedy, all DL picks)
    m0 = matches[("greedy", "all")]
    mag_rows = []
    for v in VARIANTS:
        for cls, sel in (("ML<1.5", ev.kma_ml < ML_SPLIT), ("ML>=1.5", ev.kma_ml >= ML_SPLIT)):
            kk = list(ev.index[sel])
            for ph in ("P", "S"):
                n_ref = int(((ref.phase == ph) & ref.kma_id.isin(kk)).sum())
                n_m = int(((m0.variant == v) & (m0.phase == ph) & m0.kma_id.isin(kk)).sum())
                dv = dl[(dl.variant == v) & (dl.phase == ph) & dl.kma_id.isin(kk) & dl.in_window]
                n_dl_m = int(dl.loc[m0[(m0.variant == v) & (m0.phase == ph) & m0.kma_id.isin(kk)].dl_idx, "in_window"].sum())
                mag_rows.append(dict(variant=v, mag_class=cls, n_events=len(kk), phase=ph, n_ref=n_ref, n_matched=n_m,
                                     recall=n_m / n_ref, n_dl_in_window=len(dv),
                                     precision=n_dl_m / len(dv) if len(dv) else np.nan))
    mag = pd.DataFrame(mag_rows)

    # pooled F1 ranking (stated rule)
    pooled = summ[(summ.rule == "greedy|all") & (summ.phase == "P+S")][["variant", "f1", "recall", "precision",
                                                                        "p95_abs_dt_s"]]

    # --- comparison with the step-09 tables (only now)
    claimed = pd.read_csv(f"{RUN09}/analysis/summary_by_model.csv")
    cmp_rows = []
    mine = summ[summ.rule == "greedy|all"]
    for c in claimed.itertuples():
        x = mine[(mine.variant == c.variant) & (mine.phase == c.phase)]
        if len(x) != 1:
            continue
        x = x.iloc[0]
        cmp_rows.append(dict(variant=c.variant, phase=c.phase,
                             claimed_recall=c.recall, mine_recall=x.recall,
                             claimed_n_matched=c.n_matched, mine_n_matched=x.n_matched_ref,
                             claimed_precision=c.precision, mine_precision=x.precision,
                             claimed_n_dl_in_window=c.n_dl_in_window, mine_n_dl_in_window=x.n_dl_in_window,
                             claimed_f1=c.f1, mine_f1=x.f1,
                             claimed_median_abs_dt_s=c.median_abs_dt_s, mine_median_abs_dt_s=x.median_abs_dt_s,
                             claimed_mad_s=c.mad_dt_s, mine_mad_s=x.mad_s,
                             claimed_p95_abs_dt_s=c.p95_abs_dt_s, mine_p95_abs_dt_s=x.p95_abs_dt_s,
                             claimed_mean_dt_s=c.mean_dt_s, mine_mean_dt_s=x.mean_dt_s))
    cmpdf = pd.DataFrame(cmp_rows)
    # pick-level comparison with step 09's dl_picks_all.csv (in_window, matched flags)
    old = pd.read_csv(f"{RUN09}/analysis/dl_picks_all.csv", dtype={"kma_id": str})
    old = old[["variant", "kma_id", "pick_id", "in_window", "matched"]].rename(
        columns={"in_window": "in_window_09", "matched": "matched_09"})
    mm = dl[["variant", "kma_id", "pick_id", "in_window", "dl_idx"]].rename(columns={"in_window": "in_window_mine"})
    mm["matched_mine"] = mm.dl_idx.isin(set(m0.dl_idx))
    j = mm.merge(old, on=["variant", "kma_id", "pick_id"], how="outer", indicator=True)
    checks["pick_level_vs_step09"] = dict(
        rows_only_mine=int((j["_merge"] == "left_only").sum()), rows_only_step09=int((j["_merge"] == "right_only").sum()),
        in_window_disagree=int((j["in_window_mine"].astype(bool) != j["in_window_09"].astype(bool)).sum()),
        matched_disagree=int((j["matched_mine"].astype(bool) != j["matched_09"].astype(bool)).sum()))
    # rule sensitivity: do greedy/optimal and all/in-window give the same counts?
    rs = summ[summ.rule.isin(["greedy|all", "greedy|in_window", "optimal|all", "optimal|in_window"])]
    checks["rule_sensitivity_n_matched"] = rs.pivot_table(index=["variant", "phase"], columns="rule",
                                                          values="n_matched_ref").reset_index().to_dict("records")
    # extra cross-checks of other step-09 numbers (cheap): picks outside the windows, raw station-hours of the
    # bound vertical channels, and recall without the 17 reference outliers (|PhaseNet+ - kim1983 grid| > 1 s)
    zh = 0.0
    for k in kmas:
        for tr in obspy.read(f"{RUN09}/input/{k}_sorted.mseed", headonly=True):
            if bound.get(tr.stats.station) == tr.stats.channel[:2] and tr.stats.channel[2] == "Z":
                zh += (tr.stats.endtime - tr.stats.starttime) / 3600.0
    checks["raw_station_hours_bound_Z"] = zh
    checks["dl_picks_outside_event_window"] = {f"{v}|{ph}": int(((dl.variant == v) & (dl.phase == ph) & ~dl.in_window).sum())
                                               for v in VARIANTS for ph in ("P", "S")}
    val = pd.read_csv(f"{DATA}/inputs/nll_kim1983/validation_picks.csv", dtype={"Event_ID": str})
    out_keys = {(e, s, p) for e, s, p, r in zip(val.Event_ID, val.Station, val.Phase, val.res_obs_minus_grid_s) if abs(r) > 1.0}
    ref["outlier"] = [(k, s, p) in out_keys for k, s, p in zip(ref.kma_id, ref.station, ref.phase)]
    checks["reference_outliers"] = dict(n=int(ref.outlier.sum()), P=int((ref.outlier & (ref.phase == "P")).sum()),
                                        S=int((ref.outlier & (ref.phase == "S")).sum()))
    rwo = {}
    for v in VARIANTS:
        for ph in ("P", "S"):
            ok = ref[(ref.phase == ph) & ~ref.outlier]
            mm_ = m0[(m0.variant == v) & (m0.phase == ph)]
            n_ok_m = int(mm_.ref_row.isin(ok.index).sum())
            rwo[f"{v}|{ph}"] = dict(recall_all=len(mm_) / int((ref.phase == ph).sum()), recall_without_outliers=n_ok_m / len(ok),
                                    n_without_outliers=len(ok))
    checks["recall_without_reference_outliers"] = rwo
    checks["max_abs_dt_matched_s"] = {f"{v}|{ph}": float(m0[(m0.variant == v) & (m0.phase == ph)].dt_s.abs().max())
                                      for v in VARIANTS for ph in ("P", "S")}
    checks["n_S_pairs_with_abs_dt_gt_0p5"] = {v: int(((m0.variant == v) & (m0.phase == "S") & (m0.dt_s.abs() > 0.5)).sum())
                                             for v in VARIANTS}

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print("checks:", json.dumps(checks, indent=1, default=str)[:6000])
    show = ["rule", "variant", "phase", "n_ref", "n_matched_ref", "recall", "n_dl_in_window", "n_dl_in_window_matched",
            "precision", "f1", "median_abs_dt_s", "mad_s", "p95_abs_dt_s", "mean_dt_s", "max_abs_dt_s"]
    print(summ[summ.rule == "greedy|all"][show].round(4).to_string(index=False))
    print(cmpdf.round(4).to_string(index=False))
    print(mag.round(3).to_string(index=False))
    print(pooled.round(4).to_string(index=False))
    print(summ[summ.rule.str.contains(r"\|P0")][show].round(3).to_string(index=False))

    if a.apply:
        os.makedirs(OUT_DIR, exist_ok=True)
        summ.to_csv(f"{OUT_DIR}/my_summary_by_model.csv", index=False, float_format="%.5f")
        cmpdf.to_csv(f"{OUT_DIR}/claimed_vs_mine.csv", index=False, float_format="%.5f")
        mag.to_csv(f"{OUT_DIR}/my_by_magnitude.csv", index=False, float_format="%.4f")
        m0.to_csv(f"{OUT_DIR}/my_matches_greedy_all.csv", index=False, float_format="%.5f")
        dl.drop(columns=["dl_idx"]).to_csv(f"{OUT_DIR}/my_dl_picks.csv", index=False)
        json.dump(dict(settings=settings, checks=checks), open(f"{OUT_DIR}/pick_checks.json", "w"), indent=1, default=str)
        json.dump(settings, open(f"{OUT_DIR}/settings_v09_pick_stats.json", "w"), indent=1, default=str)
        print("written:", OUT_DIR)
    else:
        print("dry run: nothing written (use --apply)")


if __name__ == "__main__":
    main()
