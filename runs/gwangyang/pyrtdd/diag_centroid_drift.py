#!/usr/bin/env python
# diag_centroid_drift.py
#
# WHAT: diagnostic of the cluster-centroid drift seen in the 'hypodd_like' runs (absLocConstraint 0).
# R0 moved the cluster centroid ~1.7 km east, R1 ~0.65 km down, while HypoDD's SVD keeps the mean shift of
# the cluster at zero in every iteration. rtDD has no such constraint; only the damping (dampingFactor 0.01,
# applied to the column-normalised system) restrains the common shift of all events, and the rtDD manual warns
# that low damping "risks large cluster shifts" (scrtdd doc/base/multievent.rst).
# This script re-runs a base run with the SAME inputs and the SAME cross-correlation results (the base run's
# xcorr_cache.csv is read back, so no waveform is touched), changing only:
#   - algoIterations 1, 2, 3, 5, 10, 20, 40 (dampingFactor 0.01): how the drift grows with the iterations
#     (note: downWeightingByResidual is interpolated 10 -> 5 over however many iterations are run);
#   - dampingFactor 0.01, 0.1, 1.0 (20 iterations): whether stronger damping holds the centroid and whether the
#     relative geometry changes.
# These are diagnostics, not tuned settings: every variant is reported.
# Outputs: runs/gwangyang/pyrtdd/diag_centroid_drift/<base>__it<N>_damp<D>/ (relocated catalog, options.json,
# console.log) and diag_centroid_drift/diag_centroid_drift.csv. The table also holds, per variant, the shape
# difference from its base run's final solution (20 iterations, damping 0.01; same metric (a) as against HypoDD:
# shape_vs_base_*), i.e. how much the cluster shape still changes after N iterations or with more damping.
# --metrics-only (added 2026-10-17 after the independent verification): recompute the table from the relocated
# catalogs already on disk, with the current analyze_pyrtdd_gwangyang.py metrics (shared HypoDD convention,
# unrounded bootstrap half-widths), without relocating anything; wall_s is copied from the existing table.
# Usage (env pyrtdd): python -I diag_centroid_drift.py [--apply] [--metrics-only]

import argparse
import importlib.util
import json
import os
import shutil
import time

import numpy as np
import pandas as pd

OUTROOT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/gwangyang/pyrtdd"
OUT = f"{OUTROOT}/diag_centroid_drift"
BASES = ["R0_catalog_only_hypodd_like", "R1_xcorr_like_reference_hypodd_like",
         "R1f_xcorr_like_reference_hypodd_like_filtered"]
ITERATIONS = [1, 2, 3, 5, 10, 20, 40]
DAMPINGS = [0.01, 0.1, 1.0]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--metrics-only", action="store_true",
                    help="recompute diag_centroid_drift.csv from the relocated catalogs on disk (no relocation)")
    args = ap.parse_args()
    variants = [(b, it, 0.01) for b in BASES for it in ITERATIONS] + \
               [(b, 20, d) for b in BASES for d in DAMPINGS if d != 0.01]
    if not args.apply:
        print(f"[dry run] {len(variants)} variants{' (metrics only)' if args.metrics_only else ''}:", variants)
        return
    ana = load_module("ana", f"{OUTROOT}/analyze_pyrtdd_gwangyang.py")
    if args.metrics_only:
        ref = ana.load_reference("dtcc")
        old = pd.read_csv(f"{OUT}/diag_centroid_drift.csv").set_index("variant")
        rows = []
        for base, it, damp in variants:
            name = f"{base}__it{it}_damp{damp:g}"
            rows.append(metrics_row(ana, ref, base, it, damp, name, old.loc[name, "wall_s"]))
        pd.DataFrame(rows).to_csv(f"{OUT}/diag_centroid_drift.csv", index=False, float_format="%.6g")
        print(f"rewrote {OUT}/diag_centroid_drift.csv from {len(rows)} relocated catalogs (no relocation)")
        return
    drv = load_module("drv", f"{OUTROOT}/run_pyrtdd_gwangyang.py")
    from pyrtdd.hdd import Catalog, DD, XCorrCache, Logger
    Logger.setLevel(Logger.Level.info)
    os.makedirs(OUT, exist_ok=True)
    ref = ana.load_reference("dtcc")
    rows = []
    for base, it, damp in variants:
        r = drv.resolve(base)
        cfg, co, so, xo, wf = drv.build_options(r)
        so.algoIterations = it
        so.dampingFactorStart = so.dampingFactorEnd = damp
        name = f"{base}__it{it}_damp{damp:g}"
        d = f"{OUT}/{name}"
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        bd = f"{OUTROOT}/{base}"
        files = (f"{bd}/inputs/station.csv", f"{bd}/inputs/event.csv", f"{bd}/inputs/phase.csv")
        cat = Catalog(*files)
        ttt, ttt_desc = drv.make_ttt(r)
        dd = DD(cat, cfg, ttt)       # no waveform proxy: every cross-correlation comes from the base cache
        xcd = XCorrCache.readFromFile(cat, f"{bd}/xcorr_cache.csv") if xo.enable else XCorrCache()
        json.dump(dict(variant=name, base=base, changed=dict(algoIterations=it, dampingFactorStart=damp,
                                                             dampingFactorEnd=damp),
                       SolverOptions=drv.to_jsonable(so), ClusteringOptions=drv.to_jsonable(co),
                       XcorrOptions=drv.to_jsonable(xo), Config=drv.to_jsonable(cfg), travel_time_table=ttt_desc,
                       xcorr_source=f"{bd}/xcorr_cache.csv (read back; no waveforms)" if xo.enable else "off",
                       catalog_files=files), open(f"{d}/options.json", "w"), indent=1, default=str)
        t0 = time.perf_counter()
        with drv.redirect_fd2(f"{d}/console.log"):
            clusters = dd.findClusters(co)
            if xo.enable:
                new = dd.relocateMultiEvents(clusters, xcd, xo, so, False, "")
            else:
                new = dd.relocateMultiEvents(clusters, so, False, "")
        new.writeToFile(f"{d}/relocated-station.csv", f"{d}/relocated-event.csv", f"{d}/relocated-phase.csv")
        row = metrics_row(ana, ref, base, it, damp, name, round(time.perf_counter() - t0, 2))
        rows.append(row)
        print(f"{name}: centroid - start = {row['centroid_minus_start_e_m']:.1f} / {row['centroid_minus_start_n_m']:.1f}"
              f" / {row['centroid_minus_start_u_m']:.1f} m; rel RMS H {row['a_rel_rms_h_m']:.1f} "
              f"V {row['a_rel_rms_v_m']:.1f} m; inside {row['c_n_inside_boot95']}/11", flush=True)
    pd.DataFrame(rows).to_csv(f"{OUT}/diag_centroid_drift.csv", index=False, float_format="%.6g")


def metrics_row(ana, ref, base, it, damp, name, wall_s):
    """One table row: centroid drift from the start, metrics (a)-(d) against HypoDD dt.cc, and the shape
    difference (a) from the base run's own final solution (20 iterations, damping 0.01)."""
    A = ana.load_run(f"diag_centroid_drift/{name}")
    st = pd.read_csv(f"{OUTROOT}/{base}/inputs/event.csv")
    start = ana.enu(st.latitude, st.longitude, st.depth).mean(0)
    s, pe = ana.compare(A, ref, ref["boot"])
    sb, _ = ana.compare(A, ana.load_run(base))
    c = A["X"].mean(0)
    return dict(variant=name, base=base, algoIterations=it, dampingFactor=damp, wall_s=wall_s,
                n_relocated=len(A["ids"]),
                centroid_minus_start_e_m=c[0] - start[0], centroid_minus_start_n_m=c[1] - start[1],
                centroid_minus_start_u_m=c[2] - start[2],
                **{k: v for k, v in s.items() if k[:2] in ("a_", "b_", "c_", "d_")},
                shape_vs_base_rms_h_m=sb["a_rel_rms_h_m"], shape_vs_base_max_h_m=sb["a_rel_max_h_m"],
                shape_vs_base_rms_v_m=sb["a_rel_rms_v_m"], shape_vs_base_max_v_m=sb["a_rel_max_v_m"])


if __name__ == "__main__":
    main()
