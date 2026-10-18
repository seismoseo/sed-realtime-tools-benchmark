# 14_side_by_side.py -- step 14 helper (conda env 'pyrtdd': pandas). New in step 14 (no step-12 counterpart).
# Builds the 2015 (step 12) vs 2025-26 (step 14) side-by-side table of docs/results/14_sanramon2026_dlpicker.md
# ONLY from the result files of the two run folders, which were made by the same code with the same settings:
#   <run>/config/stations_bound.csv, coverage_bound.csv; <run>/analysis/reference_picks.csv, summary_by_model.csv,
#   by_neighbour.csv, by_event.csv, accelerometer_vs_velocity.csv, outside_window.csv, cost.csv, summary.json,
#   best_model.json, missed_reference_diagnosis.csv, polarity_reference_check.json
# Output: <out>.csv (one row per quantity, columns 2015 / 2025-26) and the same table in markdown on stdout.
# Usage: python 14_side_by_side.py --run-2015 runs/sanramon/dlpicker --run-2026 runs/sanramon2026/dlpicker
#            --overlap-2015 72540760 --overlap-2026 75283011 --out analysis/side_by_side_2015_vs_2026.csv

import argparse
import json

import pandas as pd

MAIN = ["phasenet_instance", "phasenet_original", "phasenet_scedc", "eqtp_ncedc"]


def frac(m, n):
    return f"{int(m)}/{int(n)} = {m / n:.2f}" if n else "n/a"


def load(R):
    A = f"{R}/analysis"
    d = dict(
        bound=pd.read_csv(f"{R}/config/stations_bound.csv", dtype=str).fillna(""),
        cov=pd.read_csv(f"{R}/config/coverage_bound.csv", dtype={"event_id": str, "location": str}),
        ref=pd.read_csv(f"{A}/reference_picks.csv", dtype={"event_id": str}),
        s=pd.read_csv(f"{A}/summary_by_model.csv"),
        nb=pd.read_csv(f"{A}/by_neighbour.csv", dtype={"value": str}),
        ev=pd.read_csv(f"{A}/by_event.csv", dtype={"value": str}),
        acc=pd.read_csv(f"{A}/accelerometer_vs_velocity.csv"),
        ow=pd.read_csv(f"{A}/outside_window.csv"),
        cost=pd.read_csv(f"{A}/cost.csv"),
        summ=json.load(open(f"{A}/summary.json")),
        best=json.load(open(f"{A}/best_model.json")),
        miss=pd.read_csv(f"{A}/missed_reference_diagnosis.csv", dtype={"event_id": str}),
        prc=json.load(open(f"{A}/polarity_reference_check.json")),
    )
    return d


def rows_for(d, overlap):
    out = []

    def add(section, item, val):
        out.append((section, item, val))

    b, cov, ref, s = d["bound"], d["cov"], d["ref"], d["s"]
    main = cov[cov["role"] == "main"]
    add("data", "stations with data in the playback files", str(len(b)))
    add("data", "stations bound (main set)", str(int((b["bound"] == "1").sum())))
    bs = b[b["bound"] == "1"]["main_sensor"].value_counts()
    add("data", "main set by sensor", ", ".join(f"{k} {v}" for k, v in bs.items()))
    add("data", "stations not bound (no usable 3-C sensor)", str(int((b["bound"] != "1").sum())))
    add("data", "hn set (accelerometer at velocity-sensor stations)", str(int((b["hn_sensor"] != "").sum())))
    add("data", "main-set station-event records complete", frac(main["complete"].sum(), len(main)))
    add("data", "station-hours (main set, all records)", f"{d['cost'][d['cost']['variant'] == 'phasenet_instance']['station_hours'].iloc[0]:.1f}")
    for ph in ("P", "S"):
        r = ref[ref["phase"] == ph]
        t = r["tier"].value_counts()
        add("reference", f"usable analyst {ph} picks (weight 0-3)", str(len(r)))
        add("reference", f"  {ph}: no waveform / no 3-C sensor / 3-C triggered / 3-C complete",
            " / ".join(str(int(t.get(k, 0))) for k in ("no_data", "no_3c_sensor", "3c_incomplete", "3c_complete")))
    for v in MAIN:
        for ph in ("P", "S"):
            x = s[(s["variant"] == v) & (s["phase"] == ph)].iloc[0]
            if ph == "P":
                add(v, "P recall: all / with data / 3-C / complete",
                    f"{x.recall_all:.2f} / {x.recall_with_data:.2f} / {x.recall_3c:.2f} / {x.recall_3c_complete:.2f}")
                add(v, "P precision / counting plausible", f"{x.precision:.2f} / {x.precision_counting_plausible:.2f}")
                add(v, "P median |dt| / p95 |dt| / mean dt (s)",
                    f"{x.median_abs_dt_s:.3f} / {x.p95_abs_dt_s:.3f} / {x.mean_dt_s:+.3f}")
            else:
                add(v, "S recall: 3-C / complete", f"{x.recall_3c:.2f} / {x.recall_3c_complete:.2f}")
                add(v, "S precision", f"{x.precision:.2f}")
        x = s[(s["variant"] == v) & (s["phase"] == "P+S")].iloc[0]
        add(v, "pooled P+S F1", f"{x.f1:.3f}")
        nb = d["nb"][(d["nb"]["variant"] == v) & (d["nb"]["phase"] == "P")].set_index("value")
        add(v, "P recall complete: no event within 120 s / nearest <= 15 s",
            " / ".join(f"{nb.loc[k, 'recall_3c_complete']:.2f} ({int(nb.loc[k, 'n_ref_3c_complete'])})"
                       if k in nb.index and nb.loc[k, "n_ref_3c_complete"] > 0 else "n/a"
                       for k in ("none within 120 s", "nearest <= 15 s")))
        e = d["ev"][(d["ev"]["variant"] == v) & (d["ev"]["phase"] == "P") & d["ev"]["value"].str.startswith(overlap)]
        if len(e):
            e = e.iloc[0]
            add(v, f"overlap-test event P recall (complete)", frac(e.n_matched_3c_complete, e.n_ref_3c_complete))
        ow = d["ow"][(d["ow"]["variant"] == v) & (d["ow"]["phase"] == "P")].iloc[0]
        add(v, "false P picks per station-hour (noise span)",
            f"{ow.false_per_station_hour_searchable:.2f} ({int(ow.n_false_in_searchable_span)} in {ow.station_hours_searchable:.1f} h)")
        c = d["cost"][d["cost"]["variant"] == v].iloc[0]
        add(v, "CPU s per station-hour / ms per window", f"{c.cpu_s_per_station_hour:.3f} / {c.cpu_ms_per_window:.1f}")
        a = d["acc"][(d["acc"]["model"] == v) & (d["acc"]["phase"] == "P")]
        if len(a) == 2:
            vel = a[a["binding_set"].str.startswith("main")].iloc[0]
            acc = a[a["binding_set"].str.startswith("hn")].iloc[0]
            add(v, "P recall at hn stations: velocity / accelerometer",
                f"{vel.recall_with_data:.2f} / {acc.recall_with_data:.2f} (n {int(vel.n_ref_with_data)})")
        m = d["miss"][(d["miss"]["variant"] == v) & (d["miss"]["tier"] == "3c_complete") & (d["miss"]["phase"] == "P")]
        vc = m["why_missed"].value_counts()
        add(v, "missed P at complete records: below minConf / no trigger / other window picked",
            f"{int(vc.get('model_below_minConfidence', 0))} / {int(vc.get('no_detector_trigger', 0))} / "
            f"{int(vc.get('window_picked_other_time', 0))} (of {len(m)})")
    add("ranking", "best model by the fixed rule (pooled F1)",
        ", ".join(f"{r['variant']} {r['f1']:.3f}" for r in d["best"]["ranking"]))
    pol = d["summ"]["polarity"].get("eqtp_ncedc")
    if pol:
        for thr in ("0.5", "0.7"):
            t = pol[f"thr_{thr}"]
            add("polarity (eqtp_ncedc)", f"threshold {thr}: coverage / agreement, all",
                f"{t['all']['coverage']:.2f} / {t['all']['agreement']:.2f} (n {t['all']['n_matched_with_analyst_fm']})")
            add("polarity (eqtp_ncedc)", f"threshold {thr}: agreement normal / inverted channels",
                f"{t['direct_sense']['agreement']:.2f} (n {t['direct_sense']['n_matched_with_analyst_fm']}) / "
                + (f"{t['inverted_sense']['agreement']:.2f} (n {t['inverted_sense']['n_matched_with_analyst_fm']})"
                   if t["inverted_sense"]["n_matched_with_analyst_fm"] else "n/a (0)"))
            add("polarity (eqtp_ncedc)", f"threshold {thr}: agreement impulsive / emergent",
                f"{t['onset_I']['agreement']:.2f} / {t['onset_E']['agreement']:.2f}")
    p = d["prc"]
    add("polarity reference check", "analyst first motions on inverted channels same as similar rays",
        f"{p['inverted_frac_same']:.2f} ({p['inverted_tests']} tests); control {p['control_frac_same']:.2f} ({p['control_tests']})"
        if p["inverted_tests"] else "no tests")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-2015", required=True)
    ap.add_argument("--run-2026", required=True)
    ap.add_argument("--overlap-2015", default="72540760")
    ap.add_argument("--overlap-2026", default="75283011")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r15 = rows_for(load(a.run_2015), a.overlap_2015)
    r26 = rows_for(load(a.run_2026), a.overlap_2026)
    k15 = {(s, i): v for s, i, v in r15}
    keys = [(s, i) for s, i, _ in r26] + [(s, i) for s, i, _ in r15 if (s, i) not in {(s2, i2) for s2, i2, _ in r26}]
    k26 = {(s, i): v for s, i, v in r26}
    df = pd.DataFrame([dict(section=s, quantity=i, sanramon_2015=k15.get((s, i), ""), sanramon_2025_26=k26.get((s, i), ""))
                       for s, i in keys])
    df.to_csv(a.out, index=False)
    print("| section | quantity | 2015 (step 12) | 2025-26 (step 14) |\n|---|---|---|---|")
    for r in df.itertuples():
        esc = [str(x).replace("|", "\\|") for x in (r.section, r.quantity, r.sanramon_2015, r.sanramon_2025_26)]
        print("| " + " | ".join(esc) + " |")


if __name__ == "__main__":
    main()
