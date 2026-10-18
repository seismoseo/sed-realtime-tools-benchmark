#!/usr/bin/env python
# verify_extra_checks.py
#
# Independent verifier checks that complement verify_metrics.py / verify_xcorr.py / verify_singleevent.py.
# Each block prints its evidence; with --apply the tables are also written next to this file.
#
#   1. sensitivity of metric (c) "inside bootstrap box" and of (a) to the HypoDD representation
#      (LAT/LON/DEPTH columns [1 m depth] vs HypoDD X/Y/Z [0.1 m] vs the pyrtdd mix) and to rounding of
#      the bootstrap half-widths (raw bootstrap_errors.csv vs 0.1 m final_locations.csv)
#   2. the "fraction within 2 ms / 5 ms" of metric (f): raw float comparison (what both agents coded) versus
#      comparison on the 1 ms grid both data sets sit on
#   3. stock pyrtdd filter: R1 (stock, filter requested) vs V1 (own proxy, filter explicitly off) vs R1f
#   4. single-event cross-tool agreement with the CURRENT files: scrtdd SEa/SEm vs pyrtdd R6f/R6tf
#   5. drift diagnostic: shape after n iterations vs the 20-iteration shape (R1f, damping 0.01) and damping-1 variant
#   6. HypoDD centroid movement read from hypoDD.log (does HypoDD "pin" its centroid?)
#   7. run-vs-run shape differences quoted in the notes (S2 vs S1 etc.)
#
# WHY: these are the places where the agents' numbers depend on a convention or were read from files that
# changed later. Run (env pyrtdd):  python -I verify_extra_checks.py [--apply]

import argparse
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_gwangyang_reloc"
sys.path.insert(0, HERE)
import verify_metrics as vm                      # noqa: E402  (own helper, same folder)
from verify_xcorr import RUNS, rtdd_table, read_hypodd_cc, read_res, REF as REFCC   # noqa: E402

G = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/gwangyang"


def shape_diff(PA, PB):
    D = (PA - PA.mean(0)) - (PB - PB.mean(0))
    h = np.hypot(D[:, 0], D[:, 1])
    return D, np.sqrt(np.mean(h ** 2)), h.max(), np.sqrt(np.mean(D[:, 2] ** 2)), np.abs(D[:, 2]).max()


def pos(path):
    s = vm.read_rtdd(path)
    return vm.enu_tm(s.latitude, s.longitude, s.depth)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
    out = {}
    # ------------------------------------------------------------------ 1
    pha = vm.read_pha_origins(f"{vm.REF}/00.ph2dt/Gwangyang_mod.pha"); evd = vm.read_evdat_origins(f"{vm.REF}/02.dt.cc/event.dat")
    shift = {k: round(float(evd[k] - pha[k]), 6) for k in pha}
    r = vm.read_hypodd("02.dt.cc", shift)
    half_raw = r[["ex95", "ey95", "ez95"]].to_numpy(); half_r01 = np.round(half_raw, 1)
    QA = vm.hypodd_positions(r, "02.dt.cc", "latlon"); QB = vm.hypodd_positions(r, "02.dt.cc", "xyz")
    QM = QA.copy(); QM[:, 2] = QB[:, 2]
    rows = []
    for run in ["R1", "R1f", "R1fz", "R2f", "S1", "S2"]:
        P = pos(vm.SOLUTIONS[run])
        for rep, Q in [("latlon_depthcol", QA), ("hypodd_xyz", QB), ("mix_latlon_Z", QM)]:
            D, hr, hm, vr, vmx = shape_diff(P, Q)
            for hn, hw in [("raw", half_raw), ("round0.1", half_r01)]:
                ins = np.all(np.abs(D) <= hw, axis=1)
                rows.append(dict(run=run, hypodd_rep=rep, half=hn, h_rms=round(hr, 2), h_max=round(hm, 2), v_rms=round(vr, 2),
                                 v_max=round(vmx, 2), n_inside=int(ins.sum()), inside_ids=" ".join(str(i + 1) for i in np.where(ins)[0]),
                                 max_ratio=round(float(np.max(np.abs(D) / hw)), 3)))
    t1 = pd.DataFrame(rows); out["c_sensitivity"] = t1
    print("== 1. (a)/(c) vs HypoDD dt.cc under different reference representations"); print(t1.to_string(index=False))

    # ------------------------------------------------------------------ 2
    used = read_hypodd_cc([f"{REFCC}/dt.cc_0.7_combined"]); kept = read_res()
    rows = []
    for run in ["S1", "R1f", "R1", "S2", "R2f"]:
        x = rtdd_table(RUNS[run]); x = x[x.cc.abs() >= 0.7]
        m = x.merge(used, on=["e1", "e2", "station", "phase"], suffixes=("_r", "_ref"))
        m["kept"] = [k in kept for k in zip(m.e1, m.e2, m.station, m.phase)]
        m["ev3"] = (m.e1 == 3) | (m.e2 == 3)
        d_s = m.dt_r - m.dt_ref
        for sub, mask in [("all", np.ones(len(m), bool)), ("P", m.phase == "P"), ("S", m.phase == "S"), ("without_ev3", ~m.ev3),
                          ("kept_by_hypodd", m.kept), ("rejected_by_hypodd", ~m.kept)]:
            d = d_s[mask]; dms = np.round(d * 1000.0)
            rows.append(dict(run=run, subset=sub, n=int(mask.sum()),
                             float_le2ms=round(float(np.mean(np.abs(d * 1000.0) <= 2.0)), 3), grid_le2ms=round(float(np.mean(np.abs(dms) <= 2)), 3),
                             float_le5ms=round(float(np.mean(np.abs(d * 1000.0) <= 5.0)), 3), grid_le5ms=round(float(np.mean(np.abs(dms) <= 5)), 3),
                             n_exact2ms=int((np.abs(dms) == 2).sum()), n_exact2ms_failing_float=int(((np.abs(dms) == 2) & (np.abs(d * 1000.0) > 2.0)).sum())))
    t2 = pd.DataFrame(rows); out["f_within_fractions"] = t2
    print("\n== 2. (f) fraction within 2 / 5 ms: float comparison vs 1-ms grid"); print(t2.to_string(index=False))

    # ------------------------------------------------------------------ 3
    def xc(run):
        x = pd.read_csv(f"{G}/pyrtdd/{run}/processing/xcorr.csv", keep_default_na=False)
        x = x[x.valid.astype(str).str.lower() == "true"]
        sg = np.where(x.eventId1 < x.eventId2, 1, -1)
        k = [tuple(sorted((p, q))) + (s, f) for p, q, s, f in zip(x.eventId1, x.eventId2, x.stationCode, x.phaseType)]
        return pd.DataFrame(dict(cc=x.coefficient.values, lag=x.lag.values * sg, ph=x.phaseType.values), index=k)
    R1, V1, R1f = xc("R1_xcorr_like_reference_hypodd_like"), xc("V1_port_check_preprocess_nofilter"), xc("R1f_xcorr_like_reference_hypodd_like_filtered")
    print("\n== 3. stock pyrtdd filter check (P phases)")
    for na, A, nb, B in [("R1(stock, bandpass requested)", R1, "V1(proxy, filter OFF)", V1), ("R1(stock)", R1, "R1f(proxy, bandpass ON)", R1f)]:
        j = A.join(B, lsuffix="_a", rsuffix="_b", how="inner"); p = j.ph_a == "P"
        same = np.round((j.lag_a - j.lag_b) * 1000) == 0
        print(f"   {na} vs {nb}: P n {int(p.sum())}, identical lags {int((same & p).sum())}, max |dCC| {np.abs(j.cc_a - j.cc_b)[p].max():.6f}")

    # ------------------------------------------------------------------ 4
    rows = []
    for mode in ["SEa", "SEm"]:
        s = pd.read_csv(f"{G}/scrtdd/{mode}/single_event_results.csv").set_index("event_id").sort_index()
        A = vm.enu_tm(s.reloc_latitude, s.reloc_longitude, s.reloc_depth_km)
        for run in ["R6f_single_event_loo_one_step_filtered", "R6tf_single_event_loo_scrtdd_two_step_automatic_filtered"]:
            b = pd.read_csv(f"{G}/pyrtdd/{run}/single_event_results.csv").set_index("event_id").sort_index()
            B = vm.enu_tm(b.latitude, b.longitude, b.depth); d = np.linalg.norm(A - B, axis=1)
            rows.append(dict(scrtdd=mode, pyrtdd=run.split("_")[0], median_3d_m=round(float(np.median(d)), 2), max_3d_m=round(float(d.max()), 2),
                             max_event=int(b.index[np.argmax(d)]), pyrtdd_results_mtime=pd.Timestamp(os.path.getmtime(f"{G}/pyrtdd/{run}/single_event_results.csv"), unit="s", tz="UTC").tz_convert("Asia/Seoul").strftime("%H:%M")))
    t4 = pd.DataFrame(rows); out["single_event_cross_tool"] = t4
    stale = pd.read_csv(f"{G}/scrtdd/comparison/single_event_scrtdd_vs_pyrtdd.csv")
    print("\n== 4. single-event scrtdd vs pyrtdd with the CURRENT files"); print(t4.to_string(index=False))
    print("   scrtdd's own comparison file (written",
          pd.Timestamp(os.path.getmtime(f"{G}/scrtdd/comparison/single_event_scrtdd_vs_pyrtdd.csv"), unit="s", tz="UTC").tz_convert("Asia/Seoul").strftime("%H:%M"), "KST):")
    print(stale[stale.pyrtdd.str.startswith(("R6f", "R6tf"))].to_string(index=False))

    # ------------------------------------------------------------------ 5
    D0 = f"{G}/pyrtdd/diag_centroid_drift"
    PR = pos(vm.SOLUTIONS["R1f"]); rows = []
    for f in sorted(glob.glob(f"{D0}/R1f_*/relocated-event.csv")):
        P = pos(f); _, hr, hm, vr, vmx = shape_diff(P, PR)
        rows.append(dict(variant=os.path.basename(os.path.dirname(f)).split("__")[1], shape_vs_R1f_h_rms=round(hr, 2), shape_vs_R1f_v_rms=round(vr, 2),
                         shape_vs_R1f_h_max=round(hm, 2), shape_vs_R1f_v_max=round(vmx, 2)))
    t5 = pd.DataFrame(rows); out["drift_shape_vs_final"] = t5
    print("\n== 5. R1f drift variants: shape vs the 20-iteration, damping-0.01 R1f shape"); print(t5.to_string(index=False))

    # ------------------------------------------------------------------ 6
    print("\n== 6. HypoDD cumulative centroid shift (x, y, z[down], t) from hypoDD.log, last iteration")
    for b in ["01.dt.ct", "02.dt.cc"]:
        txt = open(f"{vm.REF}/{b}/hypoDD.log").read().splitlines()
        vals = [txt[i + 1].split() for i, l in enumerate(txt) if "mean centroid (origin) shift" in l]
        print(f"   {b}: {vals[-1]}  (m, m, m, ms)")

    # ------------------------------------------------------------------ 7
    print("\n== 7. run-vs-run shape (RMS / max, m)")
    for x, y in [("S2", "S1"), ("R2f", "R1f"), ("R1fz", "R1f"), ("S1h", "S1"), ("R1", "R1f")]:
        _, hr, hm, vr, vmx = shape_diff(pos(vm.SOLUTIONS[x]), pos(vm.SOLUTIONS[y]))
        print(f"   {x} vs {y}: H {hr:.2f}/{hm:.2f}  V {vr:.2f}/{vmx:.2f}")

    if a.apply:
        for k, t in out.items():
            t.to_csv(f"{HERE}/extra_{k}.csv", index=False)
        print("\nwritten:", [f"{HERE}/extra_{k}.csv" for k in out])
    else:
        print("\n(dry run: nothing written; use --apply)")


if __name__ == "__main__":
    main()
