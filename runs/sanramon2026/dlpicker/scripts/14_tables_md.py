# 14_tables_md.py -- step 14 copy of runs/sanramon/dlpicker/scripts/12_tables_md.py (San Ramon 2015, step 12; not
# modified). Changed: the SeisBench/normalisation tables (T14, T15) are printed only if their files exist (step 14
# skips that cross-check by default); the station count in the T1/T7 titles is read from stations_bound.csv;
# T13 also prints the analyst-only ('J') variant of the polarity reference check. Everything else unchanged.
#
# 12_tables_md.py -- step 12 helper (conda env 'pyrtdd': pandas). Prints the markdown tables used in
# docs/results/12_sanramon_dlpicker.md, read ONLY from the result files of this run folder, so that every
# number in the note can be traced to a file:
#   analysis/summary_by_model.csv, by_tier.csv, by_bound_sensor.csv, by_analyst_channel.csv, by_distance.csv,
#   by_magnitude.csv, by_neighbour.csv, by_weight_code.csv, accelerometer_vs_velocity.csv,
#   missed_reference_diagnosis.csv, unmatched_in_window.csv, outside_window.csv, cost.csv, summary.json,
#   reference_picks.csv, polarity_reference_check.json, seisbench/compare_seisbench_summary.json,
#   seisbench/weights_check.json, seisbench/eqtp_ncedc_settings.json, analysis/normalization_test.json
# Usage: python 12_tables_md.py --run-dir <runs/sanramon/dlpicker> > analysis/tables.md

import argparse
import json
import os

import pandas as pd

MAIN = ["phasenet_instance", "phasenet_original", "phasenet_scedc", "eqtp_ncedc"]


def md(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def f(x, n=2):
    return "" if pd.isna(x) else f"{x:.{n}f}"


def frac(m, n, r, k=2):
    return "" if not n or pd.isna(r) else f"{int(m)}/{int(n)} = {r:.{k}f}"


def pivot(df, value_col, fmt, ncol=None, models=MAIN):
    rows = []
    for val in df["value"].drop_duplicates():
        q = df[df["value"] == val]
        d = {"group": val}
        if ncol:
            d["n"] = int(q[ncol].iloc[0])
        for m in models:
            x = q[q["variant"] == m]
            d[m] = fmt(x.iloc[0]) if len(x) else ""
        rows.append(d)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    a = ap.parse_args()
    R = a.run_dir
    A = f"{R}/analysis"
    summ = json.load(open(f"{A}/summary.json"))
    bnd = pd.read_csv(f"{R}/config/stations_bound.csv", dtype=str).fillna("")
    n_hn = int((bnd["hn_sensor"] != "").sum())

    # ---- reference tiers
    ref = pd.read_csv(f"{A}/reference_picks.csv", dtype={"event_id": str})
    t = ref.groupby(["phase", "tier"]).size().unstack(fill_value=0)
    t = t[["no_data", "no_3c_sensor", "3c_incomplete", "3c_complete"]].reset_index()
    t["total"] = t[["no_data", "no_3c_sensor", "3c_incomplete", "3c_complete"]].sum(axis=1)
    print("### R1 analyst picks (weight 0-3) of the 26 events by tier\n")
    print(md(t))
    q = ref[ref["phase"] == "P"].groupby(["ch_type", "tier"]).size().unstack(fill_value=0).reset_index()
    print("\n### R2 analyst P picks by the analyst's channel type and tier\n")
    print(md(q))
    print(f"\nprediction check (analyst minus ray1d CON): {json.dumps(summ['pred_check'])}")

    # ---- main table
    s = pd.read_csv(f"{A}/summary_by_model.csv")
    rows = []
    for v in MAIN + [m + "_hn" for m in MAIN]:
        for ph in ("P", "S", "P+S"):
            x = s[(s["variant"] == v) & (s["phase"] == ph)]
            if not len(x):
                continue
            x = x.iloc[0]
            rows.append(dict(model=v, phase=ph,
                             recall_all=frac(x.n_matched_all, x.n_ref_all, x.recall_all),
                             recall_with_data=f(x.recall_with_data),
                             recall_3C=frac(x.n_matched_3c, x.n_ref_3c, x.recall_3c),
                             recall_3C_complete=frac(x.n_matched_3c_complete, x.n_ref_3c_complete, x.recall_3c_complete),
                             precision=frac(x.n_dl_matched_any_event, x.n_dl_in_window, x.precision),
                             precision_counting_plausible=f(x.precision_counting_plausible), F1=f(x.f1, 3),
                             median_abs_dt=f(x.median_abs_dt_s, 3), MAD=f(x.mad_dt_s, 3), p95_abs_dt=f(x.p95_abs_dt_s, 3),
                             mean_dt=f"{x.mean_dt_s:+.3f}"))
    print(f"\n### T1 per model and phase (main binding set; _hn = accelerometer binding set, {n_hn} stations)\n")
    print(md(pd.DataFrame(rows)))

    # ---- breakdowns
    def rec(x, col="recall_3c_complete", ncol="n_ref_3c_complete", mcol="n_matched_3c_complete"):
        return frac(x[mcol], x[ncol], x[col])

    for name, title, ph, fn, ncol in (
            ("by_bound_sensor", "T2a P recall at complete records, by the bound sensor type", "P",
             lambda x: rec(x), "n_ref_3c_complete"),
            ("by_bound_sensor", "T2b P recall at 3-C stations (complete + triggered records), by bound sensor", "P",
             lambda x: rec(x, "recall_3c", "n_ref_3c", "n_matched_3c"), "n_ref_3c"),
            ("by_bound_sensor", "T2c P precision by bound sensor (DL picks in window)", "P",
             lambda x: f"{f(x.precision)} ({int(x.n_dl_in_window)})", None),
            ("by_analyst_channel", "T2d P recall over picks WITH DATA, by the analyst's channel type", "P",
             lambda x: frac(x.n_matched_with_data, x.n_ref_with_data, x.recall_with_data), "n_ref_with_data"),
            ("by_distance", "T3a P recall at complete records by epicentral distance", "P", lambda x: rec(x),
             "n_ref_3c_complete"),
            ("by_distance", "T3b P precision by distance", "P", lambda x: f"{f(x.precision)} ({int(x.n_dl_in_window)})", None),
            ("by_distance", "T3c S recall at complete records by distance", "S", lambda x: rec(x), "n_ref_3c_complete"),
            ("by_magnitude", "T4a P recall at complete records by magnitude", "P", lambda x: rec(x), "n_ref_3c_complete"),
            ("by_magnitude", "T4b S recall at complete records by magnitude", "S", lambda x: rec(x), "n_ref_3c_complete"),
            ("by_magnitude", "T4c P precision by magnitude", "P", lambda x: f"{f(x.precision)} ({int(x.n_dl_in_window)})", None),
            ("by_neighbour", "T5a P recall at complete records by time to the nearest other catalog event", "P",
             lambda x: rec(x), "n_ref_3c_complete"),
            ("by_neighbour", "T5b S recall at complete records by time to the nearest other catalog event", "S",
             lambda x: rec(x), "n_ref_3c_complete"),
            ("by_weight_code", "T6a P recall at 3-C stations by analyst weight code", "P",
             lambda x: frac(x.n_matched_3c, x.n_ref_3c, x.recall_3c), "n_ref_3c"),
            ("by_weight_code", "T6b P median |dt| / p95 |dt| (s) by analyst weight code", "P",
             lambda x: f"{f(x.median_abs_dt_s, 3)} / {f(x.p95_abs_dt_s, 3)}", None),
            ("by_weight_code", "T6c S median |dt| / p95 |dt| (s) by analyst weight code", "S",
             lambda x: f"{f(x.median_abs_dt_s, 3)} / {f(x.p95_abs_dt_s, 3)}", None)):
        b = pd.read_csv(f"{A}/{name}.csv", dtype={"value": str})
        b = b[(b["phase"] == ph) & b["variant"].isin(MAIN)]
        if name == "by_bound_sensor":
            b = b[b["value"] != "(none)"]
        print(f"\n### {title}\n")
        print(md(pivot(b, None, fn, ncol)))

    # ---- accelerometer vs velocity
    h = pd.read_csv(f"{A}/accelerometer_vs_velocity.csv")
    rows = []
    for _, x in h.iterrows():
        rows.append(dict(model=x.model, sensor=x.binding_set, phase=x.phase,
                         recall_all_records=frac(x.n_matched_with_data, x.n_ref_with_data, x.recall_with_data),
                         recall_complete=frac(x.n_matched_3c_complete, x.n_ref_3c_complete, x.recall_3c_complete),
                         precision=frac(x.n_dl_matched_any_event, x.n_dl_in_window, x.precision),
                         median_abs_dt=f(x.median_abs_dt_s, 3), p95_abs_dt=f(x.p95_abs_dt_s, 3), mean_dt=f"{x.mean_dt_s:+.3f}"))
    print(f"\n### T7 velocity sensor vs accelerometer at the same {n_hn} stations\n")
    print(md(pd.DataFrame(rows)))

    # ---- why missed
    m = pd.read_csv(f"{A}/missed_reference_diagnosis.csv", dtype={"event_id": str})
    for tier in ("3c_complete", "3c_incomplete"):
        q = m[m["tier"] == tier].groupby(["variant", "phase", "why_missed"]).size().unstack(fill_value=0).reset_index()
        q["o"] = q["variant"].map(MAIN.index)
        q = q.sort_values(["o", "phase"]).drop(columns="o")
        print(f"\n### T8 missed analyst picks at {tier} records, by reason\n")
        print(md(q))
    q = m[(m["tier"] == "3c_complete") & (m["why_missed"] == "model_below_minConfidence") & (m["phase"] == "P")]
    q = q.groupby(["variant", pd.cut(q["best_value_in_covering_windows"], [0, 0.1, 0.2, 0.3, 0.4])], observed=False
                  ).size().unstack(fill_value=0).reset_index()
    q.columns = [str(c) for c in q.columns]
    print("\n### T8c P misses below minConfidence at complete records: best model value in the covering windows\n")
    print(md(q))

    # ---- unmatched in window
    u = pd.read_csv(f"{A}/unmatched_in_window.csv", dtype={"event_id": str})
    q = u[u["variant"].isin(MAIN)].groupby(["variant", "phase", "class"]).size().unstack(fill_value=0).reset_index()
    q["o"] = q["variant"].map(MAIN.index)
    print("\n### T9 unmatched DL picks inside the event windows, by class\n")
    print(md(q.sort_values(["o", "phase"]).drop(columns="o")))

    # ---- outside
    o = pd.read_csv(f"{A}/outside_window.csv")
    o = o[o["variant"].isin(MAIN)]
    rows = []
    for v in MAIN:
        for ph in ("P", "S"):
            x = o[(o["variant"] == v) & (o["phase"] == ph)].iloc[0]
            rows.append(dict(model=v, phase=ph, outside_window=int(x.n_outside),
                             other_catalog_event=int(x.n_other_catalog_event),
                             in_common_noise_span=f"{int(x.n_false_in_searchable_span)} ({int(x.n_coincident_in_span)} coincident)",
                             station_hours=f(x.station_hours_searchable, 1),
                             false_per_station_hour=f(x.false_per_station_hour_searchable),
                             HH=f(x.get("false_per_station_hour_HH")), HN=f(x.get("false_per_station_hour_HN")),
                             EH=f(x.get("false_per_station_hour_EH")), EP=f(x.get("false_per_station_hour_EP"))))
    print("\n### T10 DL picks outside the event windows\n")
    print(md(pd.DataFrame(rows)))

    # ---- cost
    c = pd.read_csv(f"{A}/cost.csv")
    c = c[c["variant"].isin(MAIN)].copy()
    c["o"] = c["variant"].map(MAIN.index)
    c = c.sort_values("o")
    print("\n### T11 cost (whole scautopick process, /usr/bin/time; 26 runs per variant)\n")
    print(md(pd.DataFrame(dict(model=c.variant, cpu_s=c.cpu_s_total.map(lambda x: f(x, 1)),
                               station_hours=c.station_hours.map(lambda x: f(x, 1)),
                               cpu_s_per_station_hour=c.cpu_s_per_station_hour.map(lambda x: f(x, 3)),
                               triggers=c.triggers, P_windows=c.p_windows, S_windows=c.s_windows,
                               ms_per_window=c.cpu_ms_per_window.map(lambda x: f(x, 1)),
                               peak_MB=c.max_rss_mb.map(lambda x: f(x, 0)),
                               startup_probe_cpu_s=c.startup_probe_cpu_s.map(lambda x: f(x, 2))))))

    # ---- polarity
    pol = summ["polarity"]
    for v in ("eqtp_ncedc", "eqtp_ncedc_hn"):
        if v not in pol:
            continue
        rows = []
        for g in pol[v]["thr_0.5"]:
            d5, d7 = pol[v]["thr_0.5"][g], pol[v]["thr_0.7"][g]
            if not d5["n_matched_with_analyst_fm"]:
                continue
            rows.append(dict(group=g, n=d5["n_matched_with_analyst_fm"],
                             coverage_0p5=f(d5["coverage"]), agree_0p5=f(d5["agreement"]),
                             agree_raw_counts_0p5=f(d5["agreement_raw_counts"]),
                             coverage_0p7=f(d7["coverage"]), agree_0p7=f(d7["agreement"]),
                             agree_raw_counts_0p7=f(d7["agreement_raw_counts"])))
        print(f"\n### T12 {v}: P polarity vs analyst first motion (matched P picks with analyst U/D)\n")
        print(f"analyst first motions: {pol[v]['analyst_fm_total']} in total, {pol[v]['analyst_fm_at_3c']} at 3-C "
              f"stations, {pol[v]['analyst_fm_matched']} matched; stations with >= 3 comparisons: {pol[v]['n_stations_ge3']}; "
              f"of those always opposite: {[(x['nsta'], x['n'], x['sense']) for x in pol[v]['stations_ge3_disagree_ge80pct']]}\n")
        print(md(pd.DataFrame(rows)))
    pr = json.load(open(f"{A}/polarity_reference_check.json"))
    print(f"\n### T13 analyst first motions on inverted channels vs similar rays on direct channels\n")
    print(f"{pr['rule']}; inverted-channel picks {pr['n_inverted_channel_picks']}, tested {pr['inverted_tests']}, "
          f"same as neighbours {f(pr['inverted_frac_same'])}; control (direct channels) {pr['control_tests']} tests, "
          f"{f(pr['control_frac_same'])}\n")
    if "analyst_only" in pr:
        aj = pr["analyst_only"]
        print(f"analyst ('J') picks only: inverted-channel picks {aj['n_inverted_channel_picks']}, tested "
              f"{aj['inverted_tests']}, same as neighbours {f(aj['inverted_frac_same'])}; control {aj['control_tests']} "
              f"tests, {f(aj['control_frac_same'])}; picks without an open epoch: {pr.get('n_unknown_sense')}\n")
    pc = pd.DataFrame(pr["per_channel"])
    if len(pc):
        pc = pc[pc["n_tests"] >= 4]
        print(md(pc.assign(frac_same_as_direct_neighbours=pc.frac_same_as_direct_neighbours.map(f))))

    # ---- seisbench
    if not os.path.exists(f"{R}/seisbench/compare_seisbench_summary.json"):
        print("\n(SeisBench cross-check not run in this step: no seisbench/compare_seisbench_summary.json)")
        return
    sb = json.load(open(f"{R}/seisbench/compare_seisbench_summary.json"))
    wc = json.load(open(f"{R}/seisbench/weights_check.json"))
    st = json.load(open(f"{R}/seisbench/eqtp_ncedc_settings.json"))
    print(f"\n### T14 SeisBench EQTP('ncedc') v{st['weights_version']} vs the plugin, events {sb['events']}\n")
    print(f"same weights: {wc['same_weights']} (max |ONNX - torch| on identical input: "
          f"{max(wc['same_input'].values()):.1e}); plugin normalisation changes outputs by <= "
          f"{max(wc['plugin_input'].values()):.2f}; P peak shifts {[w['P_shift_samples'] for w in wc['per_window']]} samples; "
          f"same polarity in {sum(w['same_polarity'] for w in wc['per_window'])}/{len(wc['per_window'])} windows; "
          f"SeisBench classify CPU {st['cpu_classify_s']:.1f} s for {st['station_hours_Z']:.2f} station-hours "
          f"({st['cpu_s_per_station_hour']:.2f} per station-hour, {st['threads']} thread)\n")
    rows = []
    for ph in ("P", "S"):
        pv = sb["plugin_vs_seisbench"][ph]
        for meth in ("plugin", "seisbench"):
            x = sb["vs_reference"][ph][meth]
            rows.append(dict(phase=ph, method=meth, picks=pv[f"n_{meth}"],
                             recall_3C=frac(x["n_matched_3c"], x["n_ref_3c"], x["recall_3c"]),
                             recall_complete=f(sb["vs_reference"][ph]["recall_3c_complete"][meth]),
                             recall_triggered=f(sb["vs_reference"][ph]["recall_3c_incomplete"][meth]),
                             precision=f(x["precision"]), median_abs_dt=f(x["median_abs_dt_s"], 3),
                             polarity_coverage=f(x.get("polarity_coverage")), polarity_agree=f(x.get("polarity_agreement"))))
    print(md(pd.DataFrame(rows)))
    if not os.path.exists(f"{A}/normalization_test.json"):
        print("\n(normalisation test not run in this step)")
        return
    nt = json.load(open(f"{A}/normalization_test.json"))
    print("\n### T15 the plugin's own eqtp_ncedc windows re-run with SeisBench's normalisation\n")
    rows = []
    for kind in ("missed", "matched"):
        x = nt[kind]
        rows.append(dict(windows=kind, n=x["n"], reach_0p4_plugin_norm=x["reach_min_conf_plugin_norm"],
                         reach_0p4_seisbench_norm=x["reach_min_conf_seisbench_norm"],
                         median_P_plugin_norm=f(x["median_P_plugin_norm"], 3),
                         median_P_seisbench_norm=f(x["median_P_seisbench_norm"], 3),
                         n_100Hz=x["n_100hz"], reach_100Hz_plugin=x["reach_100hz_plugin"],
                         reach_100Hz_seisbench=x["reach_100hz_seisbench"]))
    print(md(pd.DataFrame(rows)))
    print(f"\nreproduction check (logged best P vs recomputed, 100 Hz windows): max |diff| "
          f"{nt['reproduction_max_abs_diff_logged_vs_recomputed_bestP_100hz']:.4f}")
    for ph in ("P", "S"):
        pv = sb["plugin_vs_seisbench"][ph]
        print(f"\n{ph}: {pv['n_pairs']} plugin-SeisBench pairs; median |dt| {f(pv['median_abs_dt_s'], 3)} s; within 0.02 s "
              f"{f(pv['frac_within_0p02_s'])}; within 0.05 s {f(pv['frac_within_0p05_s'])}; p95 {f(pv['p95_abs_dt_s'], 3)}; "
              f"mean {pv['mean_dt_s']:+.3f}; max {f(pv['max_abs_dt_s'], 2)}"
              + (f"; polarity both set {pv['polarity_both_set']}, agree {f(pv['polarity_agree'])}" if ph == "P" else ""))
        print(f"   analyst picks found only by SeisBench / only by the plugin / neither: "
              f"{sb['found_by_only_one'][ph]['only_seisbench']} / {sb['found_by_only_one'][ph]['only_plugin']} / "
              f"{sb['found_by_only_one'][ph]['neither']}; only-SeisBench by tier | plugin reason: "
              f"{sb['found_by_only_one'][ph]['only_seisbench_by_tier_and_plugin_reason']}")


if __name__ == "__main__":
    main()
