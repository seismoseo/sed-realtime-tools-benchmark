#!/usr/bin/env python
# scrtdd_note_tables.py -- prints the tables of docs/results/08_gwangyang_scrtdd.md (sections 4.1-4.5) as
# Markdown, straight from runs/gwangyang/scrtdd/comparison/ (written by scrtdd_compare.py), so every number in
# the note can be regenerated. Added 2026-10-17 after the independent verification; before, the tables were
# copied by hand. Read-only; prints to stdout.
# Usage (env pyrtdd): python -I scrtdd_note_tables.py [> tables.md]

import pandas as pd

C = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/gwangyang/scrtdd/comparison"
NAME = {"R1f_xcorr_like_reference_hypodd_like_filtered": "pyrtdd R1f",
        "R1_xcorr_like_reference_hypodd_like": "pyrtdd R1 (unfiltered)",
        "START_hypoinverse": "HYPOINVERSE start", "hypodd_dtct": "HypoDD 01.dt.ct",
        "R6tf_single_event_loo_scrtdd_two_step_automatic_filtered": "R6tf",
        "R6f_single_event_loo_one_step_filtered": "R6f", "R6_single_event_loo_one_step": "R6",
        "R6p_single_event_loo_one_step_padded": "R6p", "R6t_single_event_loo_scrtdd_two_step_automatic": "R6t",
        "R6tp_single_event_loo_scrtdd_two_step_automatic_padded": "R6tp"}


def table(head, rows):
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join(str(c) for c in r) + " |")
    print()


def pct(x):
    return f"{100 * x:.1f} %"


def main():
    m = pd.read_csv(f"{C}/metrics_vs_hypodd.csv")
    for versus, title, sols in (
            ("hypodd_dtcc", "4.2 Against HypoDD 02.dt.cc",
             ["S0", "S0h", "S1", "S1h", "S2", "S2sc", "R1f_xcorr_like_reference_hypodd_like_filtered",
              "R1_xcorr_like_reference_hypodd_like", "START_hypoinverse", "hypodd_dtct"]),
            ("hypodd_dtct", "4.2 Against HypoDD 01.dt.ct", ["S0", "S0h", "S1", "S2"])):
        print(f"## {title}\n")
        rows = []
        for sname in sols:
            r = m[(m.solution == sname) & (m.versus == versus)].iloc[0]
            box = f"{int(r.n_inside_boot95)}/11 ({r.max_ratio_boot95:.2f}, ev {int(r.max_ratio_boot95_event)})"
            if versus == "hypodd_dtct":
                box += f"; own dt.ct box {int(r.n_inside_boot_own95)}/11 ({r.max_ratio_boot_own95:.2f})"
            rows.append([NAME.get(sname, sname), f"{r.rms_h_m:.1f} / {r.max_h_m:.1f}", f"{r.rms_v_m:.1f} / {r.max_v_m:.1f}",
                         f"{r.max_3d_m:.1f}",
                         f"{r.centroid_shift_E_m:+.0f}, {r.centroid_shift_N_m:+.0f}, {r.centroid_shift_U_m:+.0f}", box,
                         f"{r.interevent_pearson_r:.3f} / {r.interevent_rms_diff_m:.1f}",
                         f"{r.origin_time_rms_ms:.1f} / {r.origin_time_max_ms:.1f}"])
        table(["run", "(a) horizontal RMS / max (m)", "(a) vertical RMS / max (m)", "(a) 3-D max (m)",
               "(b) centroid shift E, N, U (m)", "(c) inside dt.cc 95 % (largest ratio, event)", "(d) r / RMS (m)",
               "(e) RMS / max (ms)"], rows)

    print("## 4.3 S1 event by event against HypoDD dt.cc\n")
    p = pd.read_csv(f"{C}/per_event_vs_hypodd.csv")
    p = p[(p.solution == "S1") & (p.versus == "hypodd_dtcc")].sort_values("id")
    b = pd.read_csv("/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/reference/gwangyang_pnplus/"
                    "2.HypoDD/02.dt.cc/bootstrap_errors.csv", comment="#")
    b["id"] = b.id - 199999
    p = p.merge(b, on="id")
    rows = []
    for r in p.itertuples():
        out = [c for c, d, h in (("E", r.dE_m, r.ex95), ("N", r.dN_m, r.ey95), ("U", r.dU_m, r.ez95)) if abs(d) > h]
        rows.append([r.id, f"{r.dE_m:.1f}", f"{r.dN_m:.1f}", f"{r.dU_m:.1f}", f"{r.d3_m:.1f}", f"{r.dt_ms_demeaned:.1f}",
                     "yes" if r.inside_boot95 else f"no ({', '.join(out)})", f"{r.max_ratio_boot95:.2f}",
                     f"{r.ex95:.2f} / {r.ey95:.2f} / {r.ez95:.2f}"])
    table(["event", "dE", "dN", "dU", "3-D", "origin time (ms, mean removed)", "inside 95 %",
           "largest abs(d) / half-width", "half-widths E/N/U"], rows)

    print("## 4.3b scrtdd run against run (shape, metric a)\n")
    rv = pd.read_csv(f"{C}/run_vs_run.csv")
    table(["pair", "what changes", "horizontal RMS / max (m)", "vertical RMS / max (m)", "inter-event RMS diff (m)",
           "origin time RMS (ms)"],
          [[f"{r.other} vs {r.base}", r.what_changes, f"{r.rms_h_m:.2f} / {r.max_h_m:.2f}",
            f"{r.rms_v_m:.2f} / {r.max_v_m:.2f}", f"{r.interevent_rms_diff_m:.2f}", f"{r.origin_time_rms_ms:.2f}"]
           for r in rv.itertuples()])

    print("## 4.4 Cross-correlation against the reference dt.cc (fractions on the 1-ms grid)\n")
    x = pd.read_csv(f"{C}/xcorr_vs_reference.csv").set_index("run")
    rows = []
    for run in ["S1", "S2", "S2sc", "R1f_xcorr_like_reference_hypodd_like_filtered", "R1_xcorr_like_reference_hypodd_like"]:
        r = x.loc[run]
        nP = int(r.P_attempted_valid)
        nS = int(r.S_attempted_valid)
        rows.append([NAME.get(run, run), f"{int(r.P_abs_cc_ge_0p7)} ({int(r.P_pos_cc_ge_0p7)} + {int(r.P_neg_cc_le_m0p7)}) of {nP}",
                     f"{int(r.S_abs_cc_ge_0p7)} ({int(r.S_pos_cc_ge_0p7)} + {int(r.S_neg_cc_le_m0p7)}) of {nS}",
                     f"{int(r.both_used_P_n)} / {int(r.both_used_S_n)}",
                     f"{r.both_used_all_median_ms:.0f} / {r.both_used_all_mad_ms:.0f}",
                     f"{pct(r.both_used_P_frac_within_2ms)} / {pct(r.both_used_S_frac_within_2ms)}",
                     f"{pct(r.both_used_P_frac_within_5ms)} / {pct(r.both_used_S_frac_within_5ms)}",
                     f"{r.both_used_P_cc_pearson_r:.2f} / {r.both_used_P_abs_cc_pearson_r:.2f} / {r.both_used_S_cc_pearson_r:.2f}",
                     f"{r.all_measured_P_cc_pearson_r:.2f} / {r.all_measured_P_abs_cc_pearson_r:.2f} / {r.all_measured_S_cc_pearson_r:.2f}"])
    table(["run", "P: abs(CC) >= 0.7 (positive + negative) of measured", "S: abs(CC) >= 0.7 of measured",
           "pairs where both passed (P / S)", "difference median / MAD (ms)", "within 2 ms (P / S)",
           "within 5 ms (P / S)", "CC r, both passed: P signed / P abs / S", "CC r, all measured: P signed / P abs / S"], rows)
    r = x.loc["S1"]
    table(["subset (S1, both passed)", "n", "within 2 ms", "within 5 ms", "95th percentile of the difference"],
          [["all", int(r.both_used_all_n), pct(r.both_used_all_frac_within_2ms), pct(r.both_used_all_frac_within_5ms),
            f"{r.both_used_all_p95_abs_ms:.0f} ms"],
           ["kept by HypoDD in its final iteration", int(r.both_used_kept_by_hypodd_n),
            pct(r.both_used_kept_by_hypodd_frac_within_2ms), pct(r.both_used_kept_by_hypodd_frac_within_5ms),
            f"{r.both_used_kept_by_hypodd_p95_abs_ms:.0f} ms"],
           ["rejected by HypoDD's outlier test", int(r.both_used_rejected_by_hypodd_n),
            pct(r.both_used_rejected_by_hypodd_frac_within_2ms), pct(r.both_used_rejected_by_hypodd_frac_within_5ms),
            f"{r.both_used_rejected_by_hypodd_p95_abs_ms:.0f} ms"],
           ["all measured triplets (any CC)", int(r.all_measured_all_n), pct(r.all_measured_all_frac_within_2ms),
            pct(r.all_measured_all_frac_within_5ms), f"{r.all_measured_all_p95_abs_ms:.0f} ms"]])

    print("## 4.5 Single event against S1 (summary)\n")
    s = pd.read_csv(f"{C}/single_event_vs_S1_summary.csv").set_index("mode")
    print(s.round(2).to_string(), "\n")
    print("## 4.5 Single event: scrtdd vs pyrtdd and each run vs its own reference catalog\n")
    c = pd.read_csv(f"{C}/single_event_context.csv")
    rows = []
    for r in c.itertuples():
        rows.append([NAME.get(r.single_event_run, r.single_event_run), NAME.get(r.versus, r.versus), r.kind,
                     f"{r.median_3d_m:.2f} / {r.max_3d_m:.2f} (ev {int(r.max_3d_event)})",
                     f"{r.median_3d_without_event3_m:.2f}",
                     "" if pd.isna(r.after_removing_catalog_offset_median_3d_m) else
                     f"{r.after_removing_catalog_offset_median_3d_m:.2f} / {r.after_removing_catalog_offset_max_3d_m:.2f}"])
    table(["solution", "versus", "what", "3-D median / max (m)", "median without event 3 (m)",
           "after removing S1 minus R1f at the same event: median / max (m)"], rows)


if __name__ == "__main__":
    main()
