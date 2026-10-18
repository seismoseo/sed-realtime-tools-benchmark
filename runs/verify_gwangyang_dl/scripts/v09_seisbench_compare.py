# v09_seisbench_compare.py -- independent verifier of step 09, part 3 (plugin vs SeisBench pick times).
# Env: pyrtdd (numpy, pandas, obspy, lxml). Run with 'python -I'.
#
# Why: step 09 claims, for phasenet_instance, plugin-minus-SeisBench pick times with median |dt| 0.010 s,
# 80 % within 0.02 s and 94 % within 0.05 s (P), 63 % / 94 % (S), mean offsets within +-0.005 s.
# This script recomputes those statistics for the 3 events I re-ran SeisBench on (v09_seisbench_rerun.py),
# from the raw plugin picks.xml (own parser) and MY SeisBench picks, and compares with
#   (a) step 09's own SeisBench picks for the same 3 events (were they reproducible?),
#   (b) step 09's pairs table restricted to the same 3 events (same subset, apples to apples),
#   (c) step 09's all-event summary (the claim).
# Pairing: same event file, station and phase; |dt| <= tolerance (P 0.5 s, S 1.0 s); one-to-one in order of
# increasing |dt|. dt = plugin - SeisBench. "identical" = |dt| <= 1 ms; "within x" = |dt| <= x + 1e-6 s.
# Usage: python -I v09_seisbench_compare.py [--apply]

import argparse
import json
import os
import sys

import numpy as np
import obspy
import pandas as pd
from lxml import etree

# ------------------------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
RUN09 = f"{PROJECT}/runs/gwangyang/dlpicker"
VDIR = f"{PROJECT}/runs/verify_gwangyang_dl"
MY_SB = f"{VDIR}/seisbench/phasenet_instance_picks_3events.csv"
SB09 = f"{RUN09}/seisbench/phasenet_instance_picks.csv"
PAIRS09 = f"{RUN09}/seisbench/compare_seisbench_pairs.csv"
SUMMARY09 = f"{RUN09}/seisbench/compare_seisbench_summary.json"
VARIANT = "phasenet_instance"
EVENTS = ["20210827220322", "20210828234556", "20260203021535"]
TOL = {"P": 0.5, "S": 1.0}
WIN_BEFORE, WIN_AFTER = 5.0, 60.0
OUT_DIR = f"{VDIR}/out/seisbench"
NS = 1_000_000_000


def ns(t):
    return obspy.UTCDateTime(t).ns


def read_picks_xml(path):
    rows = []
    for p in etree.parse(path).iter("{*}pick"):
        wf = p.find("{*}waveformID")
        rows.append(dict(t_ns=ns(p.find("{*}time/{*}value").text), station=wf.get("stationCode"),
                         phase=p.findtext("{*}phaseHint")))
    return pd.DataFrame(rows)


def pair(a_t, b_t, tol_ns):
    cand = sorted((abs(int(b) - int(a)), int(a) - int(b), i, j) for i, a in enumerate(a_t) for j, b in enumerate(b_t)
                  if abs(int(a) - int(b)) <= tol_ns)
    ui, uj, out = set(), set(), []
    for _, d, i, j in cand:
        if i not in ui and j not in uj:
            ui.add(i)
            uj.add(j)
            out.append((i, j, d))
    return out


def stats(d):
    d = np.asarray(d, float)
    if len(d) == 0:
        return dict(n_pairs=0)
    ad = np.abs(d)
    return dict(n_pairs=int(len(d)), median_abs_dt_s=float(np.median(ad)),
                frac_within_0p02_s=float(np.mean(ad <= 0.02 + 1e-6)), frac_within_0p05_s=float(np.mean(ad <= 0.05 + 1e-6)),
                frac_identical_1ms=float(np.mean(ad <= 0.001)), p95_abs_dt_s=float(np.percentile(ad, 95)),
                mean_dt_s=float(d.mean()), max_abs_dt_s=float(ad.max()))


def compare(plugin, sb, origins, events):
    rows = []
    for k in events:
        for ph in ("P", "S"):
            P = plugin[(plugin.kma_id == k) & (plugin.phase == ph)]
            S = sb[(sb.kma_id == k) & (sb.phase == ph)]
            for s in sorted(set(P.station) & set(S.station)):
                Ps, Ss = P[P.station == s], S[S.station == s]
                for i, j, d in pair(Ps.t_ns.to_numpy(), Ss.t_ns.to_numpy(), int(TOL[ph] * NS)):
                    t = int(Ps.t_ns.iloc[i])
                    rows.append(dict(kma_id=k, phase=ph, station=s, dt_s=d / NS,
                                     in_window=bool(origins[k] - WIN_BEFORE * NS <= t <= origins[k] + WIN_AFTER * NS)))
    return pd.DataFrame(rows, columns=["kma_id", "phase", "station", "dt_s", "in_window"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    hyp = pd.read_csv(f"{DATA}/reference_tables/hypoinverse_kim1983.csv", dtype={"kma_id": str})
    origins = {k: ns(t) for k, t in zip(hyp.kma_id, hyp.origin_time)}

    plugin = []
    for k in EVENTS:
        d = read_picks_xml(f"{RUN09}/output/{VARIANT}/{k}/picks.xml")
        d["kma_id"] = k
        plugin.append(d)
    plugin = pd.concat(plugin, ignore_index=True)
    mine = pd.read_csv(MY_SB, dtype={"kma_id": str})
    mine["t_ns"] = [ns(t) for t in mine.peak_time]
    old = pd.read_csv(SB09, dtype={"kma_id": str})
    old = old[old.kma_id.isin(EVENTS)].copy()
    old["t_ns"] = [ns(t) for t in old.peak_time]

    # (a) my SeisBench picks vs step 09's SeisBench picks, same 3 events
    key = ["kma_id", "station", "phase", "t_ns"]
    j = mine[key + ["peak_value"]].merge(old[key + ["peak_value"]], on=key, how="outer", indicator=True,
                                         suffixes=("_mine", "_09"))
    both = j[j["_merge"] == "both"]
    repro = dict(n_mine=len(mine), n_step09=len(old), identical_time_rows=int(len(both)),
                 only_mine=int((j["_merge"] == "left_only").sum()), only_step09=int((j["_merge"] == "right_only").sum()),
                 max_abs_peak_value_diff=float((both.peak_value_mine - both.peak_value_09).abs().max()) if len(both) else None)

    # plugin vs my SeisBench, plugin vs step-09 SeisBench (same 3 events)
    res = {}
    for label, sb in (("plugin_vs_my_seisbench", mine), ("plugin_vs_step09_seisbench", old)):
        c = compare(plugin, sb, origins, EVENTS)
        res[label] = {ph: dict(all=stats(c[c.phase == ph].dt_s), in_window=stats(c[(c.phase == ph) & c.in_window].dt_s),
                               n_plugin=int((plugin.phase == ph).sum()), n_seisbench=int((sb.phase == ph).sum()))
                      for ph in ("P", "S")}
        if label == "plugin_vs_my_seisbench":
            mypairs = c
    # (b) step 09's pairs table, same 3 events
    p09 = pd.read_csv(PAIRS09, dtype={"kma_id": str})
    p09 = p09[(p09.model == VARIANT) & p09.kma_id.isin(EVENTS)]
    res["step09_pairs_table_same_3_events"] = {ph: stats(p09[p09.phase == ph].dt_plugin_minus_seisbench_s)
                                                for ph in ("P", "S")}
    # (c) the all-event claim
    s09 = json.load(open(SUMMARY09))["models"][VARIANT]
    res["step09_claim_all_11_events"] = {ph: s09[ph]["all"] for ph in ("P", "S")}

    # recall of MY SeisBench picks vs PhaseNet+ for the 3 events (claim for all 11: P 0.864, S 0.797)
    ref = pd.read_csv(f"{DATA}/reference_tables/picks_phasenet_plus.csv", dtype={"kma_id": str})
    ref = ref[ref.kma_id.isin(EVENTS)].copy()
    ref["t_ns"] = [ns(t) for t in ref.time]
    rec = {}
    for label, sb in (("my_seisbench", mine), ("step09_seisbench", old), ("plugin", plugin)):
        for ph in ("P", "S"):
            n = 0
            for k in EVENTS:
                R = ref[(ref.kma_id == k) & (ref.phase == ph)]
                S = sb[(sb.kma_id == k) & (sb.phase == ph)]
                for s in set(R.station):
                    n += len(pair(R[R.station == s].t_ns.to_numpy(), S[S.station == s].t_ns.to_numpy(), int(TOL[ph] * NS)))
            rec[f"{label}|{ph}"] = dict(n_ref=int((ref.phase == ph).sum()), n_matched=n,
                                        recall=n / int((ref.phase == ph).sum()))
    res["recall_vs_phasenet_plus_3_events"] = rec
    res["seisbench_reproducibility_3_events"] = repro

    # (d) all 11 events with step 09's SeisBench picks (shown above to be reproduced exactly by my re-run on 3
    # events): the full-set claim, recomputed with my pairing. Also: sign convention of step 09's pairs table,
    # and how much "within 0.02 s" depends on the few-microsecond offsets between the two time grids.
    all_ev = sorted(origins)
    sb_all = pd.read_csv(SB09, dtype={"kma_id": str})
    sb_all["t_ns"] = [ns(t) for t in sb_all.peak_time]
    pl_all = []
    for k in all_ev:
        d = read_picks_xml(f"{RUN09}/output/{VARIANT}/{k}/picks.xml")
        d["kma_id"] = k
        pl_all.append(d)
    pl_all = pd.concat(pl_all, ignore_index=True)
    c_all = compare(pl_all, sb_all, origins, all_ev)
    full = {}
    for ph in ("P", "S"):
        d = c_all[c_all.phase == ph].dt_s.to_numpy()
        ad = np.abs(d)
        full[ph] = dict(stats(d), frac_within_0p02_s_tol_1e4=float(np.mean(ad <= 0.02 + 1e-4)),
                        frac_within_0p02_s_tol_1e6=float(np.mean(ad <= 0.02 + 1e-6)),
                        n_abs_dt_between_0p020001_and_0p0201=int(((ad > 0.02 + 1e-6) & (ad <= 0.0201)).sum()))
    res["all_11_events_plugin_vs_step09_seisbench_my_pairing"] = full
    # recall vs PhaseNet+ over all 11 events (claimed: SeisBench P 0.864 / S 0.797, plugin 0.842 / 0.757)
    ref_all = pd.read_csv(f"{DATA}/reference_tables/picks_phasenet_plus.csv", dtype={"kma_id": str})
    ref_all["t_ns"] = [ns(t) for t in ref_all.time]
    rec_all = {}
    for label, sbx in (("step09_seisbench", sb_all), ("plugin", pl_all)):
        for ph in ("P", "S"):
            n = 0
            for k in all_ev:
                R = ref_all[(ref_all.kma_id == k) & (ref_all.phase == ph)]
                S = sbx[(sbx.kma_id == k) & (sbx.phase == ph)]
                for s in set(R.station):
                    n += len(pair(R[R.station == s].t_ns.to_numpy(), S[S.station == s].t_ns.to_numpy(), int(TOL[ph] * NS)))
            nr = int((ref_all.phase == ph).sum())
            rec_all[f"{label}|{ph}"] = dict(n_ref=nr, n_matched=n, recall=n / nr)
    res["recall_vs_phasenet_plus_all_11_events"] = rec_all
    # sign: join my signed dt (plugin - SeisBench) with step 09's column for the same (event, station, phase)
    p09a = pd.read_csv(PAIRS09, dtype={"kma_id": str})
    p09a = p09a[p09a.model == VARIANT]
    jj = c_all.merge(p09a[["kma_id", "station", "phase", "dt_plugin_minus_seisbench_s"]], on=["kma_id", "station", "phase"])
    jj = jj[jj.dt_s.abs() > 0.004]                     # pairs with a real difference
    res["sign_check_step09_pairs_column"] = dict(
        n_compared=int(len(jj)),
        same_sign=int((np.sign(jj.dt_s) == np.sign(jj.dt_plugin_minus_seisbench_s)).sum()),
        opposite_sign=int((np.sign(jj.dt_s) == -np.sign(jj.dt_plugin_minus_seisbench_s)).sum()),
        my_mean_plugin_minus_seisbench={ph: float(c_all[c_all.phase == ph].dt_s.mean()) for ph in ("P", "S")})

    print(json.dumps(res, indent=1))
    if a.apply:
        os.makedirs(OUT_DIR, exist_ok=True)
        mypairs.to_csv(f"{OUT_DIR}/plugin_vs_my_seisbench_pairs.csv", index=False, float_format="%.6f")
        json.dump(dict(settings=dict(script=os.path.abspath(__file__), MY_SB=MY_SB, SB09=SB09, PAIRS09=PAIRS09,
                                     VARIANT=VARIANT, EVENTS=EVENTS, TOL=TOL, WIN_BEFORE=WIN_BEFORE, WIN_AFTER=WIN_AFTER,
                                     identical="|dt| <= 1 ms", within="|dt| <= x + 1e-6 s",
                                     versions=dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__)),
                       results=res), open(f"{OUT_DIR}/seisbench_compare.json", "w"), indent=1)
        print("written:", OUT_DIR)
    else:
        print("dry run: nothing written (use --apply)")


if __name__ == "__main__":
    main()
