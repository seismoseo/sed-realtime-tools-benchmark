#!/usr/bin/env python
# print_note_tables.py
#
# WHAT: prints the tables of docs/results/07_gwangyang_pyrtdd.md (sections 4-9) as Markdown, straight from the
# result files written by analyze_pyrtdd_gwangyang.py and diag_centroid_drift.py, so that every number in the
# note can be regenerated (added 2026-10-17 after the independent verification; before, the tables were copied
# by hand). Read-only; prints to stdout. Usage (env pyrtdd): python -I print_note_tables.py [> tables.md]

import numpy as np
import pandas as pd

D = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/gwangyang/pyrtdd"
SHORT = {  # run folder -> name used in the note
    "R0_catalog_only_hypodd_like": "R0", "R1_xcorr_like_reference_hypodd_like": "R1",
    "R1f_xcorr_like_reference_hypodd_like_filtered": "R1f",
    "R1fz_xcorr_like_reference_hypodd_like_filtered_zerophase": "R1fz",
    "R1fw_xcorr_like_reference_hypodd_like_filtered_xcorrweight100": "R1fw",
    "R2_xcorr_default_rtdd_default": "R2", "R2f_xcorr_default_rtdd_default_filtered": "R2f",
    "R3a_catalog_only_hypodd_like_hypoinverse_start": "R3a",
    "R3b_xcorr_like_reference_hypodd_like_hypoinverse_start": "R3b",
    "R3bf_xcorr_like_reference_hypodd_like_hypoinverse_start_filtered": "R3bf",
    "R4_xcorr_like_reference_hypodd_like_no_outlier_picks": "R4",
    "R4f_xcorr_like_reference_hypodd_like_no_outlier_picks_filtered": "R4f",
    "R5_xcorr_like_reference_hypodd_like_homogeneous": "R5",
    "R5f_xcorr_like_reference_hypodd_like_homogeneous_filtered": "R5f",
    "R6_single_event_loo_one_step": "R6", "R6t_single_event_loo_scrtdd_two_step_automatic": "R6t",
    "R6p_single_event_loo_one_step_padded": "R6p",
    "R6tp_single_event_loo_scrtdd_two_step_automatic_padded": "R6tp",
    "R6f_single_event_loo_one_step_filtered": "R6f",
    "R6tf_single_event_loo_scrtdd_two_step_automatic_filtered": "R6tf",
    "V0_stock_no_disk_cache": "V0", "V1_port_check_preprocess_nofilter": "V1",
    "REF_hypodd_dtct": "HypoDD dt.ct (for scale)", "REF_hypoinverse_kim1983": "HYPOINVERSE (for scale)",
}
ORDER = ["REF_hypodd_dtct", "REF_hypoinverse_kim1983"] + [k for k in SHORT if not k.startswith("REF_")]


def pct(x):
    return f"{100 * x:.1f} %"


def f(x, n=1):
    return "-" if pd.isna(x) else f"{x:.{n}f}"


def table(head, rows):
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join(str(c) for c in r) + " |")
    print()


def box(r, tag=""):
    return f"{int(r['c_n_inside_boot95' + tag])}/11 ({f(r['c_max_ratio' + tag], 2)}, ev {int(r['c_max_ratio_event' + tag])})"


def main():
    sm = pd.read_csv(f"{D}/summary_metrics.csv")
    pe = pd.read_csv(f"{D}/per_event_vs_reference.csv")
    rr = pd.read_csv(f"{D}/run_vs_run_metrics.csv")
    xc = pd.read_csv(f"{D}/xcorr_comparison.csv")
    rs = pd.read_csv(f"{D}/residual_stats.csv")
    dr = pd.read_csv(f"{D}/diag_centroid_drift/diag_centroid_drift.csv")
    pr = pd.read_csv(f"{D}/per_event_run_vs_run.csv")

    for ref, title, runs in (("hypodd_dtcc", "4. Against HypoDD 02.dt.cc", ORDER),
                             ("hypodd_dtct", "4. Against HypoDD 01.dt.ct",
                              ["R0_catalog_only_hypodd_like", "R3a_catalog_only_hypodd_like_hypoinverse_start",
                               "R1_xcorr_like_reference_hypodd_like", "R1f_xcorr_like_reference_hypodd_like_filtered",
                               "R2f_xcorr_default_rtdd_default_filtered",
                               "R5f_xcorr_like_reference_hypodd_like_homogeneous_filtered",
                               "R6_single_event_loo_one_step"])):
        print(f"## {title}\n")
        rows = []
        for run in runs:
            q = sm[(sm.run == run) & (sm.reference == ref)]
            if not len(q):
                continue
            r = q.iloc[0]
            rows.append([SHORT[run], f"{f(r.a_rel_rms_h_m)} / {f(r.a_rel_rms_v_m)}", f"{f(r.a_rel_max_h_m)} / {f(r.a_rel_max_v_m)}",
                         f"{r.b_centroid_shift_e_m:.0f} / {r.b_centroid_shift_n_m:.0f} / {r.b_centroid_shift_u_m:.0f}",
                         box(r), f"{r.d_interevent_pearson_r:.3f} / {f(r.d_interevent_rms_diff_m)}",
                         f"{f(r.e_ot_rms_demeaned_ms)} / {f(r.e_ot_max_demeaned_ms)}"])
        table(["run", "shape RMS H / V (m)", "shape max H / V (m)", "centroid shift E / N / U (m)",
               "inside box (largest ratio, event)", "inter-event r / RMS diff (m)", "origin time RMS / max (ms)"], rows)

    print("## 4. Per event, R1f against dt.cc\n")
    q = pe[(pe.run == "R1f_xcorr_like_reference_hypodd_like_filtered") & (pe.reference == "hypodd_dtcc")].sort_values("event_id")
    rows = []
    for r in q.itertuples():
        out = [c for c, d, b in (("E", r.dE_rel_m, r.boot_ex95_m), ("N", r.dN_rel_m, r.boot_ey95_m),
                                 ("U", r.dU_rel_m, r.boot_ez95_m)) if abs(d) > b]
        rows.append([r.event_id, f"{r.dE_rel_m:+.1f} / {r.dN_rel_m:+.1f} / {r.dU_rel_m:+.1f}",
                     f"{r.boot_ex95_m:.2f} / {r.boot_ey95_m:.2f} / {r.boot_ez95_m:.2f}",
                     "yes" if r.inside_boot95 else f"no ({', '.join(out)})", f"{r.boot95_max_ratio:.2f}"])
    table(["event", "dE / dN / dU (m)", "bootstrap E / N / U (m)", "inside", "largest abs(d) / half-width"], rows)

    print("## 5. Run against run\n")
    rows = []
    for r in rr.itertuples():
        if r.status != "ok" or "R6" in r.other:
            continue
        rows.append([f"{SHORT[r.other]} vs {SHORT[r.base]}", r.what_changes, f"{f(r.a_rel_rms_h_m)} / {f(r.a_rel_rms_v_m)}",
                     f"{f(r.a_rel_max_h_m)} / {f(r.a_rel_max_v_m)}",
                     f"{r.b_centroid_shift_e_m:.0f} / {r.b_centroid_shift_n_m:.0f} / {r.b_centroid_shift_u_m:.0f}",
                     f(r.d_interevent_rms_diff_m), f(r.e_ot_rms_demeaned_ms)])
    table(["pair", "what changes", "shape RMS H / V (m)", "shape max H / V (m)", "centroid shift E / N / U (m)",
           "inter-event RMS diff (m)", "origin time RMS (ms)"], rows)

    print("## 6. Drift diagnostic (one row per variant)\n")
    rows = []
    for r in dr.itertuples():
        rows.append([SHORT.get(r.base, r.base), r.algoIterations, f"{r.dampingFactor:g}",
                     f"{r.centroid_minus_start_e_m:.0f} / {r.centroid_minus_start_n_m:.0f} / {r.centroid_minus_start_u_m:.0f}",
                     f"{f(r.a_rel_rms_h_m)} / {f(r.a_rel_rms_v_m)}", f"{int(r.c_n_inside_boot95)}/11 ({f(r.c_max_ratio, 2)})",
                     f"{f(r.shape_vs_base_rms_h_m)} / {f(r.shape_vs_base_rms_v_m)} (max {f(r.shape_vs_base_max_h_m)} / {f(r.shape_vs_base_max_v_m)})"])
    table(["base", "iterations", "damping", "center minus start E / N / U (m)", "shape RMS vs dt.cc H / V (m)",
           "inside box (largest ratio)", "shape vs base run RMS H / V (max) (m)"], rows)

    print("## 7. Single event vs multi-event position, 3-D distance (m)\n")
    cols = ["R6", "R6p", "R6tp", "R6f", "R6tf", "R6t"]
    piv = {}
    for c in cols:
        full = [k for k, v in SHORT.items() if v == c][0]
        piv[c] = pr[pr.other == full].set_index("event_id").d3D_abs_m
    rows = [[k] + [f(piv[c].get(k)) for c in cols] for k in range(1, 12)]
    rows.append(["RMS / max"] + [f"{np.sqrt(np.mean(piv[c] ** 2)):.1f} / {piv[c].max():.1f}" for c in cols])
    table(["event"] + cols, rows)

    print("## 8. Cross-correlation vs the reference dt.cc (fractions on the 1-ms grid)\n")
    rows = []
    for run in ["R1_xcorr_like_reference_hypodd_like", "R1f_xcorr_like_reference_hypodd_like_filtered",
                "R1fz_xcorr_like_reference_hypodd_like_filtered_zerophase", "R2_xcorr_default_rtdd_default",
                "R2f_xcorr_default_rtdd_default_filtered", "R4_xcorr_like_reference_hypodd_like_no_outlier_picks",
                "R4f_xcorr_like_reference_hypodd_like_no_outlier_picks_filtered"]:
        r = sm[(sm.run == run) & (sm.reference == "hypodd_dtcc")].iloc[0]
        rows.append([SHORT[run], f"{int(r.f_n_measured_P)} / {int(r.f_n_measured_S)}",
                     f"{int(r.f_n_abscc07_P)} / {int(r.f_n_abscc07_S)}", f"{int(r.f_n_negcc07_P)} / {int(r.f_n_negcc07_S)}",
                     f"{int(r.f_n_poscc07_P)} / {int(r.f_n_poscc07_S)}", int(r.f_n_common_cc07),
                     f"{r.f_dt_diff_median_ms:.1f} / {r.f_dt_diff_mad_ms:.1f}",
                     f"{pct(r.f_frac_within_2ms)} / {pct(r.f_frac_within_5ms)}",
                     f"{r.f_cc_pearson_r:.2f} / {r.f_cc_abs_pearson_r:.2f}"])
    table(["run", "measured P / S", "abs(CC) >= 0.7 P / S", "of these CC <= -0.7 P / S", "CC >= +0.7 P / S",
           "in both (CC >= 0.7)", "dt difference median / MAD (ms)", "within 2 / 5 ms", "CC r signed / abs"], rows)
    rows = []
    for run, sub in (("R1", "without_event3"), ("R1", "event3_pairs_only"), ("R1", "rtdd_cc_negative"),
                     ("R1f", "without_event3"), ("R1f", "event3_pairs_only"), ("R1f", "P"), ("R1f", "S"),
                     ("R1f", "rtdd_cc_negative"), ("R1fz", "without_event3"), ("R2f", "without_event3")):
        full = [k for k, v in SHORT.items() if v == run][0]
        r = xc[(xc.run == full) & (xc.triplets == "both_cc07") & (xc.subset == sub)].iloc[0]
        rows.append([run, sub, int(r.n), f"{r.dt_diff_median_ms:.1f} / {r.dt_diff_mad_ms:.1f}", f(r.dt_diff_rms_ms),
                     f"{pct(r.frac_within_2ms)} / {pct(r.frac_within_5ms)}",
                     f"{r.cc_pearson_r:.2f} / {r.cc_abs_pearson_r:.2f}", f"{r.cc_rtdd_median:.2f} / {r.cc_ref_median:.2f}"])
    table(["run", "subset", "n", "median / MAD (ms)", "RMS (ms)", "within 2 / 5 ms", "CC r signed / abs",
           "median CC rtDD / reference"], rows)
    rows = []
    for run in ["R1_xcorr_like_reference_hypodd_like", "R1f_xcorr_like_reference_hypodd_like_filtered"]:
        r = xc[(xc.run == run) & (xc.triplets == "both_measured") & (xc.subset == "all")].iloc[0]
        rows.append([SHORT[run], int(r.n), f"{pct(r.frac_within_2ms)} / {pct(r.frac_within_5ms)}",
                     f"{r.dt_diff_grid_dev_max_ms:.1e}"])
    table(["run", "all measured triplets", "within 2 / 5 ms", "largest distance from the 1-ms grid (ms)"], rows)

    print("## 9. Residuals\n")
    rows = []
    for r in rs.itertuples():
        if not str(r.run).startswith(("R", "V")) or str(r.run).startswith("REF"):
            continue
        rows.append([SHORT.get(r.run, r.run), int(r.initial_n_dd), f"{int(r.final_n_dd_weight_gt0)} ({int(r.final_n_dd_xcorr_weight_gt0)})",
                     f"{f(r.final_rms_ms_weight_gt0)} / {f(r.final_rms_ms_xcorr_weight_gt0)} / {f(r.final_rms_ms_catalog_weight_gt0)}",
                     f(r.final_weighted_rms_ms), f"{f(r.log_last_dd_median_ms, 2)} / {f(r.log_last_dd_mad_ms)}",
                     (f"{r.wall_time_s:.1f}" if r.wall_time_s < 1 else f"{r.wall_time_s:.0f}") if not pd.isna(r.wall_time_s) else "-"])
    table(["run", "double differences (initial)", "weight > 0 at the end (of which cc)",
           "final RMS, weight > 0: all / cc / catalog (ms)", "final weighted RMS (ms)",
           "last-iteration median / MAD (ms)", "wall time (s)"], rows)


if __name__ == "__main__":
    main()
