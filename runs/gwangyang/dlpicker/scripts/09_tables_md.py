# 09_tables_md.py -- step 09 helper (run in conda env 'pyrtdd': pandas). Prints the markdown tables used in
# docs/results/09_gwangyang_dlpicker.md, read ONLY from the result files of this run folder, so that every
# number in the notes can be traced to a file:
#   analysis/summary_by_model.csv, by_magnitude.csv, by_distance.csv, by_sensor.csv, outside_window.csv,
#   unmatched_in_window.csv, missed_reference_diagnosis.csv, cost.csv, summary.json (fast vs reliable),
#   seisbench/compare_seisbench_summary.json, seisbench/weights_check.json, seisbench/*_settings.json,
#   seisbench/threads1/*_settings.json, reloc/compare_pairs.csv, reloc/centroid_shift_from_start.csv,
#   reloc/reloc_summary.json
# Fractions of pick-time differences are counted in whole samples (n = round(dt * 100 Hz)): identical
# |n| == 0, within 0.02 s |n| <= 2, within 0.05 s |n| <= 5 (09_compare.py, 09_compare_seisbench.py).
# Usage: python 09_tables_md.py --run-dir <runs/gwangyang/dlpicker> > tables.md

import argparse
import json

import pandas as pd

ORDER = ["phasenet_original", "phasenet_instance", "eqtransformer_stead", "phasenet_stead", "phasenet_instance_fast"]


def md(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def f(x, n=3):
    return "" if pd.isna(x) else f"{x:.{n}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    R = a.run_dir

    s = pd.read_csv(f"{R}/analysis/summary_by_model.csv")
    s["o"] = s["variant"].map(ORDER.index)
    s = s.sort_values(["o", "phase"])
    t = pd.DataFrame(dict(model=s["variant"], phase=s["phase"],
                          recall=[f"{m}/{n} = {f(r, 2)}" for m, n, r in zip(s.n_matched, s.n_ref, s.recall)],
                          recall_wo_ref_outliers=s.recall_without_ref_outliers.map(lambda x: f(x, 2)),
                          precision=[f"{m}/{n} = {f(p, 2)}" for m, n, p in zip(s.n_dl_matched, s.n_dl_in_window, s.precision)],
                          precision_counting_plausible=s.precision_counting_plausible.map(lambda x: f(x, 2)),
                          F1=s.f1.map(lambda x: f(x, 3)),
                          median_abs_dt=s.median_abs_dt_s.map(lambda x: f(x, 3)), MAD=s.mad_dt_s.map(lambda x: f(x, 3)),
                          p95_abs_dt=s.p95_abs_dt_s.map(lambda x: f(x, 3)), mean_dt=s.mean_dt_s.map(lambda x: f"{x:+.3f}")))
    print("### T1 per model and phase\n")
    print(md(t))

    for name in ("by_magnitude", "by_distance", "by_sensor"):
        b = pd.read_csv(f"{R}/analysis/{name}.csv")
        b = b[b["phase"] != "P+S"]
        rows = []
        for v in ORDER:
            for ph in ("P", "S"):
                q = b[(b["variant"] == v) & (b["phase"] == ph)]
                d = dict(model=v, phase=ph)
                for _, r in q.iterrows():
                    d[f"{r['value']} recall"] = f"{f(r['recall'], 2)} ({r['n_matched']}/{r['n_ref']})"
                    d[f"{r['value']} prec."] = f(r["precision"], 2)
                    d[f"{r['value']} p95|dt|"] = f(r["p95_abs_dt_s"], 3)
                rows.append(d)
        print(f"\n### T2 {name}\n")
        print(md(pd.DataFrame(rows)))

    o = pd.read_csv(f"{R}/analysis/outside_window.csv")
    rows = []
    for v in ORDER:
        q = o[o["variant"] == v].set_index("phase")
        nf = {ph: int(q.loc[ph, "n_coincident"] + q.loc[ph, "n_isolated"]) for ph in ("P", "S")}
        rows.append(dict(model=v, P_outside=int(q.loc["P", "n_outside"]), S_outside=int(q.loc["S", "n_outside"]),
                         other_catalog_event=int(q["n_other_catalog_event"].sum()),
                         coincident=int(q["n_coincident"].sum()), isolated=int(q["n_isolated"].sum()),
                         station_hours=f(q.loc["P", "station_hours_searchable"], 1),
                         P_per_station_hour=f(nf["P"] / q.loc["P", "station_hours_searchable"], 2),
                         S_per_station_hour=f(nf["S"] / q.loc["S", "station_hours_searchable"], 2),
                         isolated_P_per_station_hour=f(q.loc["P", "isolated_per_station_hour_searchable"], 2)))
    print("\n### T3 outside the event windows\n")
    print(md(pd.DataFrame(rows)))

    u = pd.read_csv(f"{R}/analysis/unmatched_in_window.csv", dtype={"kma_id": str})
    c = u.groupby(["variant", "phase", "class"]).size().unstack(fill_value=0).reset_index()
    c["o"] = c["variant"].map(ORDER.index)
    print("\n### T4 unmatched DL picks inside the windows, by class (all 11 events)\n")
    print(md(c.sort_values(["o", "phase"]).drop(columns="o")))
    for k in ("20210828133922", "20260203021535"):
        cc = u[u["kma_id"] == k].groupby(["variant", "phase", "class"]).size().unstack(fill_value=0).reset_index()
        print(f"\n#### T4b event {k}\n")
        print(md(cc))

    m = pd.read_csv(f"{R}/analysis/missed_reference_diagnosis.csv")
    c = m.groupby(["variant", "phase", "why_missed"]).size().unstack(fill_value=0).reset_index()
    c["o"] = c["variant"].map(ORDER.index)
    print("\n### T5 why reference picks were missed\n")
    print(md(c.sort_values(["o", "phase"]).drop(columns="o")))

    k = pd.read_csv(f"{R}/analysis/cost.csv")
    k["o"] = k["variant"].map(ORDER.index)
    k = k.sort_values("o")
    print("\n### T6 cost (scautopick + plugin; ONNX Runtime single-threaded)\n")
    print(md(pd.DataFrame(dict(model=k.variant, station_hours=k.station_hours.map(lambda x: f(x, 1)),
                               cpu_s=k.cpu_s_total.map(lambda x: f(x, 2)), wall_s=k.wall_s_total.map(lambda x: f(x, 2)),
                               cpu_s_per_station_hour=k.cpu_s_per_station_hour.map(lambda x: f(x, 3)),
                               startup_cpu_s=k.startup_probe_cpu_s.map(lambda x: f(x, 2)),
                               triggers=k.triggers, P_windows=k.p_windows, S_windows=k.s_windows,
                               ms_per_window=k.cpu_ms_per_window.map(lambda x: f(x, 2)),
                               max_rss_MB=k.max_rss_mb.map(lambda x: f(x, 0))))))
    rows = []
    for sub, label in (("", "4 threads"), ("threads1/", "1 thread")):
        for mdl in ("phasenet_instance", "eqtransformer_stead"):
            j = json.load(open(f"{R}/seisbench/{sub}{mdl}_settings.json"))
            rows.append(dict(model=mdl, torch_threads=label, cpu_classify_s=f(j["cpu_classify_s"], 1),
                             wall_classify_s=f(j["wall_classify_s"], 1), station_hours=f(j["station_hours_Z"], 1),
                             cpu_s_per_station_hour=f(j["cpu_s_per_station_hour"], 3)))
    print("\n### T6b SeisBench continuous classify() on the same data\n")
    print(md(pd.DataFrame(rows)))

    sj = json.load(open(f"{R}/analysis/summary.json"))
    fr = sj["fast_vs_reliable"]
    print("\n### T7 fast vs reliable (phasenet_instance P picks; dt = fast - reliable; fractions in whole samples)\n")
    rows = []
    for lab, pre, dpre, npairs in (("all paired", "", "dt_", fr["n_paired"]),
                                   ("inside the event windows", "in_window_", "dt_in_window_", fr["n_paired_in_window"])):
        rows.append(dict(pairs=lab, n=npairs, median_abs_dt=f(fr[f"{dpre}median_abs_dt_s"], 3),
                         identical=f(fr[f"{pre}identical_fraction"], 2),
                         within_2_samples=f(fr[f"{pre}within_2_samples_fraction"], 2),
                         within_5_samples=f(fr[f"{pre}within_5_samples_fraction"], 2),
                         p95_abs_dt=f(fr[f"{dpre}p95_abs_dt_s"], 3), max_abs_dt=f(fr[f"{dpre}max_abs_dt_s"], 3),
                         mean_dt=f"{fr[f'{dpre}mean_dt_s']:+.4f}"))
    print(md(pd.DataFrame(rows)))
    print("\n```\n" + json.dumps(fr, indent=1) + "\n```")

    cs = json.load(open(f"{R}/seisbench/compare_seisbench_summary.json"))["models"]
    sm = pd.read_csv(f"{R}/analysis/summary_by_model.csv")
    sm = sm[sm["group"] == "all"].set_index(["variant", "phase"])
    rows = []
    for mdl, v in cs.items():
        for ph, q in v.items():
            al, w, r = q["all"], q["in_windows"], q["seisbench_vs_reference"]
            rows.append(dict(model=mdl, phase=ph, plugin_picks=q["n_plugin_picks"], seisbench_picks=q["n_seisbench_picks"],
                             pairs=al["n_pairs"], median_abs_dt=f(al["median_abs_dt_s"], 3),
                             within_2_samples=f(al["frac_within_2_samples"], 2),
                             within_5_samples=f(al["frac_within_5_samples"], 2),
                             identical=f(al["frac_identical_0_samples"], 2), p95=f(al["p95_abs_dt_s"], 3),
                             max=f(al["max_abs_dt_s"], 2), mean_dt_plugin_minus_SB=f"{al['mean_dt_s']:+.4f}",
                             SB_recall=f(r["recall"], 3), SB_precision=f(r["precision"], 3),
                             plugin_recall=f(sm.loc[(mdl, ph), "n_matched"] / sm.loc[(mdl, ph), "n_ref"], 3),
                             plugin_precision=f(sm.loc[(mdl, ph), "n_dl_matched"] / sm.loc[(mdl, ph), "n_dl_in_window"], 3),
                             ref_only_SB=q["reference_found_only_by_seisbench"],
                             ref_only_plugin=q["reference_found_only_by_plugin"],
                             ref_neither=q["reference_found_by_neither"]))
    print("\n### T8 plugin vs SeisBench (same weights; dt = plugin - SeisBench; fractions in whole samples)\n")
    print(md(pd.DataFrame(rows)))
    wc = json.load(open(f"{R}/seisbench/weights_check.json"))
    for mdl, v in wc.items():
        print(f"\nweights {mdl}: same_weights={v['same_weights']}; " + "; ".join(
            f"{ph}: same-input max|diff| {x['same_input_max_abs_diff']:.1e}, plugin-input max|diff| {x['plugin_input_max_abs_diff']:.1e}, argmax shift {x['plugin_input_argmax_shift_samples']}"
            for ph, x in v["phases"].items()) + f"; input diff {v['input_max_abs_diff_plugin_vs_seisbench']:.2e}")

    p = pd.read_csv(f"{R}/reloc/compare_pairs.csv")
    print("\n### T9 relocation: metric (a) relative geometry RMS (m), own centroid removed; metric (b) centroid "
          "shift (m), solution centroid - reference centroid\n")
    print(md(p.assign(**{c: p[c].map(lambda x: f(x, 1)) for c in p.columns if c.endswith("_m")})))
    cd = pd.read_csv(f"{R}/reloc/centroid_shift_from_start.csv")
    print("\n### T9c relocation: centroid of each solution - its starting centroid (event_centroid_start.csv = HypoDD ISTART=1 centroid), m\n")
    print(md(cd.assign(**{c: cd[c].map(lambda x: f(x, 1)) for c in cd.columns if c.endswith("_m")})))
    rs = json.load(open(f"{R}/reloc/reloc_summary.json"))
    rows = []
    for k2, v in rs["solutions"].items():
        rows.append(dict(solution=k2, P=v["picks"]["P"], S=v["picks"]["S"],
                         not_matching_phasenet_plus=v.get("picks_not_matching_phasenet_plus", ""),
                         used_P=v["phases_used"]["P"], used_S=v["phases_used"]["S"],
                         events_relocated=v["n_events_relocated"], final_rms_median_s=f(v["final_rms_median_s"], 3)))
    print("\n### T9b relocation inputs\n")
    print(md(pd.DataFrame(rows)))
    print("\nreference bootstrap 95% (median over events, m):", json.dumps(rs["reference_bootstrap_95_median_m"]))


if __name__ == "__main__":
    main()
