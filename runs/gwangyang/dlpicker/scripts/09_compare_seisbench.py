# 09_compare_seisbench.py -- step 09 helper (run in conda env 'pyrtdd': pandas).
#
# Compares, for the same weight set, the pick times of the scdlrtpicker plugin (scautopick runs of stage
# pick, as tabulated by 09_compare.py in analysis/dl_picks_all.csv) with SeisBench's continuous picking
# (09_seisbench_run.py: <model>_picks.csv), at the same event file, station and phase.
#
# Pairing rule: as for the reference comparison (functions match and read logic as in step T's
# 05_compare_picks.py): one-to-one, closest first, P within --p-tol, S within --s-tol.
# Sign: match(ref, sc) returns dt = sc time - ref time. The plugin-vs-SeisBench pairs are formed with
# match(plugin, seisbench), which returns SeisBench - plugin; that value is NEGATED before it is stored, so
# dt_plugin_minus_seisbench_s (compare_seisbench_pairs.csv) and every dt statistic of 'all' / 'in_windows'
# (compare_seisbench_summary.json) really are plugin time - SeisBench time. (Up to 2026-10-17 the stored
# value was SeisBench - plugin under this name; found by the independent verification.)
# Whole samples: pick times lie on the 100 Hz sample grid but differ from it by a few microseconds, so a
# cut such as |dt| <= 0.02 s is ill-defined at exactly 2 samples. Differences are therefore also counted in
# whole samples, n = round(dt * --sampling-rate) (dt_samples in compare_seisbench_pairs.csv), and the
# fractions are: identical |n| == 0, within 2 samples (0.02 s) |n| <= 2, within 5 samples (0.05 s) |n| <= 5.
# Reported: number of pairs, median |dt|, these three fractions, 95th percentile |dt|, mean signed dt,
# max |dt|; for all picks of the files and for picks inside the event windows (HYPOINVERSE origin
# -5 s .. +60 s).
# Also: SeisBench's own recall / precision against PhaseNet+ with the same rules as 09_compare.py (so the
# two ways of running the same weights can be compared), and how many reference picks only one of the
# two found. There dt = SeisBench time - PhaseNet+ time (match(PhaseNet+, SeisBench), as dt = DL -
# PhaseNet+ in 09_compare.py): column sb_dt_s of compare_seisbench_vs_reference.csv and
# seisbench_vs_reference.median_abs_dt_s / mean_dt_s in the summary.
#
# Outputs (in --out-dir): compare_seisbench_pairs.csv, compare_seisbench_vs_reference.csv,
# compare_seisbench_summary.json

import argparse
import json

import numpy as np
import pandas as pd

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"


def match(ref, sc, tol):
    # copied unchanged from install/05_compare_picks.py:
    # all candidate pairs within tolerance, smallest |dt| first, each pick used once
    pairs = []
    for i, r in ref.iterrows():
        cand = sc[sc["station"] == r["station"]]
        for j, s in cand.iterrows():
            dt = (s["time"] - r["time"]).total_seconds()
            if abs(dt) <= tol:
                pairs.append((abs(dt), dt, i, j))
    pairs.sort()
    used_r, used_s, out = set(), set(), {}
    for adt, dt, i, j in pairs:
        if i in used_r or j in used_s:
            continue
        used_r.add(i)
        used_s.add(j)
        out[i] = (j, dt)
    return out


def dstats(d, sr):
    # d: plugin - SeisBench [s]; sr: sampling rate [Hz]; fractions counted in whole samples (header)
    d = np.asarray(d, dtype=float)
    if len(d) == 0:
        return dict(n_pairs=0)
    ad = np.abs(d)
    an = np.abs(np.rint(d * sr).astype(int))
    return dict(n_pairs=int(len(d)), median_abs_dt_s=float(np.median(ad)),
                frac_identical_0_samples=float(np.mean(an == 0)),
                frac_within_2_samples=float(np.mean(an <= 2)),
                frac_within_5_samples=float(np.mean(an <= 5)),
                p95_abs_dt_s=float(np.percentile(ad, 95)), mean_dt_s=float(d.mean()), max_abs_dt_s=float(ad.max()),
                max_abs_dt_samples=int(an.max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--p-tol", type=float, default=0.5)
    ap.add_argument("--s-tol", type=float, default=1.0)
    ap.add_argument("--win-before", type=float, default=5.0)
    ap.add_argument("--win-after", type=float, default=60.0)
    ap.add_argument("--sampling-rate", type=float, default=100.0,
                    help="sample rate of the data and of both pickers [Hz], for dt in whole samples")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    tol = {"P": a.p_tol, "S": a.s_tol}

    idm = pd.read_csv(f"{DATA}/reference_tables/event_id_map.csv", dtype={"kma_id": str})
    ev = pd.read_csv(f"{DATA}/inputs/rtdd_catalog/event.csv").rename(columns={"id": "rtdd_id"}).merge(
        idm[["rtdd_id", "kma_id", "kma_ml"]], on="rtdd_id").set_index("kma_id")
    ev["origin"] = pd.to_datetime(ev["isotime"], utc=True)
    ref = pd.read_csv(f"{DATA}/reference_tables/picks_phasenet_plus.csv", dtype={"kma_id": str})
    ref["time"] = pd.to_datetime(ref["time"], utc=True)
    dl = pd.read_csv(f"{a.run_dir}/analysis/dl_picks_all.csv", dtype={"kma_id": str})
    dl["time"] = pd.to_datetime(dl["time"], utc=True)
    rvd = pd.read_csv(f"{a.run_dir}/analysis/reference_vs_dl.csv", dtype={"kma_id": str})

    pairs_all, refrows, summ = [], [], {}
    for m in a.models:
        sb = pd.read_csv(f"{a.out_dir}/{m}_picks.csv", dtype={"kma_id": str})
        sb["time"] = pd.to_datetime(sb["peak_time"], utc=True)
        pl = dl[dl["variant"] == m].copy()
        s = dict()
        for kma, e in ev.iterrows():
            w0 = e["origin"] - pd.Timedelta(seconds=a.win_before)
            w1 = e["origin"] + pd.Timedelta(seconds=a.win_after)
            P_, S_ = pl[pl["kma_id"] == kma], sb[sb["kma_id"] == kma]
            for ph in ("P", "S"):
                pp, ss = P_[P_["phase"] == ph], S_[S_["phase"] == ph]
                mm = match(pp, ss, tol[ph])            # returns SeisBench - plugin
                for i, (j, dt_sb_minus_plugin) in mm.items():
                    dt = 0.0 - dt_sb_minus_plugin          # plugin - SeisBench (0.0 - x: no negative zero)
                    pairs_all.append(dict(model=m, kma_id=kma, station=pp.loc[i, "station"], phase=ph,
                                          plugin_time=pp.loc[i, "time"], seisbench_time=ss.loc[j, "time"],
                                          dt_plugin_minus_seisbench_s=dt, plugin_conf=pp.loc[i, "confidence"],
                                          seisbench_peak=ss.loc[j, "peak_value"],
                                          in_window=bool(w0 <= pp.loc[i, "time"] <= w1),
                                          plugin_matched_ref=bool(pp.loc[i, "matched"]),
                                          dt_samples=int(np.rint(dt * a.sampling_rate))))
                # SeisBench vs PhaseNet+ (same rule as 09_compare.py): match(PhaseNet+, SeisBench) returns
                # dt = SeisBench - PhaseNet+, the same sign convention as dt = DL - PhaseNet+ there
                rr = ref[(ref["kma_id"] == kma) & (ref["phase"] == ph)]
                mr = match(rr, ss, tol[ph])
                sbw = ss[(ss["time"] >= w0) & (ss["time"] <= w1)]
                s.setdefault(ph, dict(n_ref=0, sb_matched=0, sb_in_window=0, sb_matched_in_window=0,
                                      sb_total=0, sb_outside_windows=0, dts=[]))
                d = s[ph]
                d["n_ref"] += len(rr)
                d["sb_matched"] += len(mr)
                d["sb_in_window"] += len(sbw)
                d["sb_matched_in_window"] += sum(1 for (j, _) in mr.values() if j in sbw.index)
                d["sb_total"] += len(ss)
                d["sb_outside_windows"] += len(ss) - len(sbw)
                d["dts"] += [dt for (_, dt) in mr.values()]
                for i in rr.index:
                    refrows.append(dict(model=m, kma_id=kma, station=rr.loc[i, "station"], phase=ph,
                                        sb_matched=i in mr, sb_dt_s=mr[i][1] if i in mr else np.nan))
        pa = pd.DataFrame([p for p in pairs_all if p["model"] == m])
        out = {}
        for ph in ("P", "S"):
            q = pa[pa["phase"] == ph]
            n_plugin = int((pl["phase"] == ph).sum())
            n_plugin_win = 0
            for kma, e in ev.iterrows():
                w0 = e["origin"] - pd.Timedelta(seconds=a.win_before)
                w1 = e["origin"] + pd.Timedelta(seconds=a.win_after)
                n_plugin_win += int(((pl["kma_id"] == kma) & (pl["phase"] == ph) & (pl["time"] >= w0) & (pl["time"] <= w1)).sum())
            d = s[ph]
            r_sb = d["sb_matched"] / d["n_ref"]
            p_sb = d["sb_matched_in_window"] / d["sb_in_window"] if d["sb_in_window"] else np.nan
            out[ph] = dict(n_plugin_picks=n_plugin, n_seisbench_picks=d["sb_total"],
                           n_plugin_picks_in_windows=n_plugin_win, n_seisbench_picks_in_windows=d["sb_in_window"],
                           all=dstats(q["dt_plugin_minus_seisbench_s"], a.sampling_rate),
                           in_windows=dstats(q.loc[q["in_window"], "dt_plugin_minus_seisbench_s"], a.sampling_rate),
                           plugin_picks_with_seisbench_partner_frac=len(q) / n_plugin if n_plugin else np.nan,
                           seisbench_vs_reference=dict(
                               recall=r_sb, precision=p_sb, f1=2 * r_sb * p_sb / (r_sb + p_sb),
                               n_ref=d["n_ref"], n_matched=d["sb_matched"],
                               seisbench_picks_outside_windows=d["sb_outside_windows"],
                               median_abs_dt_s=float(np.median(np.abs(d["dts"]))) if d["dts"] else np.nan,
                               mean_dt_s=float(np.mean(d["dts"])) if d["dts"] else np.nan))
            # reference picks found by only one of the two
            rp = pd.DataFrame([r for r in refrows if r["model"] == m and r["phase"] == ph])
            pv = rvd[(rvd["variant"] == m) & (rvd["phase"] == ph)][["kma_id", "station", "matched"]]
            j = rp.merge(pv, on=["kma_id", "station"], how="left")
            out[ph]["reference_found_by_both"] = int((j["sb_matched"] & j["matched"]).sum())
            out[ph]["reference_found_only_by_seisbench"] = int((j["sb_matched"] & ~j["matched"]).sum())
            out[ph]["reference_found_only_by_plugin"] = int((~j["sb_matched"] & j["matched"]).sum())
            out[ph]["reference_found_by_neither"] = int((~j["sb_matched"] & ~j["matched"]).sum())
        summ[m] = out
        for ph in ("P", "S"):
            o = out[ph]
            print(f"{m} {ph}: plugin {o['n_plugin_picks']} picks, SeisBench {o['n_seisbench_picks']}; "
                  f"pairs {o['all']['n_pairs']} ({o['plugin_picks_with_seisbench_partner_frac']:.2f} of plugin picks); "
                  f"|dt| median {o['all'].get('median_abs_dt_s', np.nan):.3f} s, <=2 samples {o['all'].get('frac_within_2_samples', np.nan):.2f}, "
                  f"<=5 samples {o['all'].get('frac_within_5_samples', np.nan):.2f}, identical {o['all'].get('frac_identical_0_samples', np.nan):.2f}, "
                  f"p95 {o['all'].get('p95_abs_dt_s', np.nan):.3f}, mean (plugin - SeisBench) {o['all'].get('mean_dt_s', np.nan):+.4f} | "
                  f"SeisBench vs PhaseNet+: recall {o['seisbench_vs_reference']['recall']:.3f}, precision "
                  f"{o['seisbench_vs_reference']['precision']:.3f}; only SeisBench {o['reference_found_only_by_seisbench']}, "
                  f"only plugin {o['reference_found_only_by_plugin']}, neither {o['reference_found_by_neither']}")
    pd.DataFrame(pairs_all).to_csv(f"{a.out_dir}/compare_seisbench_pairs.csv", index=False, float_format="%.4f")
    pd.DataFrame(refrows).to_csv(f"{a.out_dir}/compare_seisbench_vs_reference.csv", index=False, float_format="%.4f")
    with open(f"{a.out_dir}/compare_seisbench_summary.json", "w") as f:
        json.dump(dict(p_tol_s=a.p_tol, s_tol_s=a.s_tol, sampling_rate_hz=a.sampling_rate,
                       definitions=dict(
                           dt_all_and_in_windows="plugin time - SeisBench time [s] (dt_plugin_minus_seisbench_s)",
                           dt_seisbench_vs_reference="SeisBench time - PhaseNet+ time [s] (sb_dt_s)",
                           dt_samples="round(dt * sampling_rate)",
                           frac_identical_0_samples="|dt_samples| == 0",
                           frac_within_2_samples="|dt_samples| <= 2 (0.02 s)",
                           frac_within_5_samples="|dt_samples| <= 5 (0.05 s)"),
                       models=summ), f, indent=1, default=str)


if __name__ == "__main__":
    main()
