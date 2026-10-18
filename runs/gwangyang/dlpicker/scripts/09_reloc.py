# 09_reloc.py -- step 09 helper (run in conda env 'pyrtdd': pyrtdd (libhdd = scrtdd v2.0.9 relocation
# code), pandas, numpy).
#
# End-to-end chain check: are the deep-learning picks of scautopick + scdlrtpicker good enough for
# double-difference relocation? Catalog-only (no cross-correlation) relocation with pyrtdd of
#   (1) an rtDD catalog built from the DL picks of each main model (the best model, from
#       analysis/best_model.json, is the main result; the others are reported too), and
#   (2) a CONTROL: the reference catalog (inputs/rtdd_catalog/phase.csv = the 763 PhaseNet+ picks HypoDD's
#       ph2dt used), relocated with exactly the same settings. (1) vs (2) isolates the effect of the picks
#       from the effect of the relocation program (pyrtdd vs HypoDD).
# The results are compared in metres with HypoDD 01.dt.ct (catalog only) and 02.dt.cc
# (reference_tables/hypodd_dtct.csv, hypodd_dtcc.csv).
#
# Catalog from the DL picks ("associate picks to the 11 known events by time window"):
#   - window: HYPOINVERSE origin (inputs/rtdd_catalog/event.csv) - 5 s .. + 60 s (as in 09_compare.py);
#   - per event, station and phase one pick: the most confident one (ties: the earlier); in 'window_tt'
#     the travel-time check below is applied first, then the most confident remaining pick is kept;
#   - association 'window' (the main one, exactly the rule asked for): nothing else;
#   - association 'window_tt' (a variant, reported as such): additionally the pick must lie within
#     --tt-tol s of the kim1983 travel time (NLL grids) from the common starting location
#     (event_centroid_start.csv, the same for all events) and the HYPOINVERSE origin time. Every
#     non-flagged PhaseNet+ pick lies within 0.94 s (P) / 0.89 s (S) of the grid times, so 1.0 s keeps
#     real arrivals and removes e.g. S waves picked as P;
#   - phase.csv follows the reference catalog's conventions: P on <sensor>Z, S on <sensor>N, no
#     uncertainties (so all picks have equal weight, usePickUncertainties = False);
#   - stations: inputs/rtdd_catalog/station.csv; starting locations: event_centroid_start.csv (all 11
#     events at HypoDD's ISTART=1 centroid, origin times from HYPOINVERSE).
#
# 'hypodd_like' settings (task definition; everything not listed stays at the pyrtdd default, and EVERY
# value actually used is introspected from the option objects and saved to settings.json):
#   ClusteringOptions: numEllipsoids 0, maxNeighbourDist 10 km, minNumNeigh 1, maxNumNeigh 0 (no limit),
#                      minNumPhases 1;
#   SolverOptions: absLocConstraintStart/End 0 (no absolute-location equations), dampingFactorStart/End
#                  0.01, downWeightingByResidualStart/End default (10 -> 5);
#   travel times: NLLGrid(gridPath=inputs/nll_kim1983/time, gridModel='kim1983', maxSearchDistance=0.1 m).
#
# Diagnostic pair (best model only, reported as variants): 'dl_<best>_matched_only' = only the DL picks that
# matched a PhaseNet+ pick, with their DL times; 'control_phasenet_plus_same_subset' = the PhaseNet+ picks of
# exactly the same (event, station, phase) set. Same observations, different pick times.
#
# Comparison ("relative geometry"): every solution is converted to east/north/up metres on a local
# tangent plane (WGS84 radii of curvature at a common point); over the events present in both solutions
# each solution's own centroid is removed; then per event the 3-D difference vector, and the RMS over
# events (3-D and per component). The baseline 'all_at_centroid' (no relocation: every event at the
# start point) shows the size of the reference geometry itself. This is metric (a).
#
# Metric (b), absolute position of the cluster (added 2026-10-17 after the independent verification):
#   - per compared pair, the centroid shift = centroid of the solution - centroid of the reference over
#     the same events (east / north / up / 3-D, m; columns centroid_shift_* of compare_pairs.csv). Metric
#     (a) removes exactly this shift, so (a) and (b) together describe the full difference;
#   - per solution, its centroid - its starting centroid (event_centroid_start.csv, the common start point
#     of all events = HypoDD's ISTART=1 centroid, so also the start of the two HypoDD solutions) over the
#     relocated events (centroid_shift_from_start.csv and reloc_summary.json -> centroid_shift_from_start;
#     the HypoDD rows come from reference_tables/hypodd_*.csv). Catalog-only rtDD with absLocConstraint 0 and
#     damping 0.01 lets the whole cluster drift (note 07, section 6); a catalog-only solution's absolute
#     position is not meaningful, only its relative geometry.
#
# Outputs (in --out-dir): <solution>/{station,event,phase}.csv (input catalog), <solution>/relocated-*.csv,
# <solution>/processing/, <solution>/settings.json, positions.csv, compare_pairs.csv,
# compare_per_event.csv, centroid_shift_from_start.csv, reloc_summary.json

import argparse
import json
import os
import shutil

import numpy as np
import pandas as pd

import pyrtdd.hdd as hdd

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
CAT = f"{DATA}/inputs/rtdd_catalog"
NLL_PATH = f"{DATA}/inputs/nll_kim1983/time"


def options_dict(o):
    d = {}
    for k in dir(o):
        if k.startswith("_"):
            continue
        v = getattr(o, k)
        if callable(v):
            continue
        d[k] = v if isinstance(v, (int, float, str, bool, list)) else str(v)
    return d


def enu(lat, lon, depth_km, lat0, lon0, dep0):
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    p = np.radians(lat0)
    M = a * (1 - e2) / (1 - e2 * np.sin(p) ** 2) ** 1.5
    N = a / np.sqrt(1 - e2 * np.sin(p) ** 2)
    n = M * np.radians(np.asarray(lat) - lat0)
    e = N * np.cos(p) * np.radians(np.asarray(lon) - lon0)
    u = -(np.asarray(depth_km) - dep0) * 1000.0
    return e, n, u


def build_dl_catalog(dl, ev, sensor_of, start, ttt, assoc, tt_tol, outdir):
    rows, kept = [], []
    for _, e in ev.iterrows():
        w0 = e["origin"] - pd.Timedelta(seconds=e["win_before"])
        w1 = e["origin"] + pd.Timedelta(seconds=e["win_after"])
        q = dl[(dl["kma_id"] == e["kma_id"]) & (dl["time"] >= w0) & (dl["time"] <= w1)].copy()
        q["tt"] = np.nan
        if assoc == "window_tt":
            # the travel-time check comes BEFORE choosing one pick per station and phase, so that a station
            # whose most confident 'P' is really its S wave can still keep a plausible weaker P pick
            for i, x in q.iterrows():
                s = start.loc[x["station"]]
                q.loc[i, "tt"] = ttt.compute(e["lat0"], e["lon0"], e["dep0"], s["latitude"], s["longitude"],
                                             s["elevation"], x["phase"])
            res = (q["time"] - e["origin"]).dt.total_seconds() - q["tt"]
            q = q[res.abs() <= tt_tol]
        q = q.sort_values(["confidence", "time"], ascending=[False, True]).groupby(["station", "phase"]).head(1)
        for x in q.itertuples():
            tt = x.tt
            ch = sensor_of[x.station] + ("Z" if x.phase == "P" else "N")
            rows.append(dict(eventId=int(e["rtdd_id"]), isotime=x.time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                             lowerUncertainty="", upperUncertainty="", type=x.phase, networkCode="KS",
                             stationCode=x.station, locationCode="", channelCode=ch))
            kept.append(dict(kma_id=e["kma_id"], station=x.station, phase=x.phase, matched_ref=bool(x.matched),
                             dl_class=q.loc[x.Index, "class"], confidence=x.confidence,
                             res_tt_s=(x.time - e["origin"]).total_seconds() - tt if assoc == "window_tt" else np.nan))
    ph = pd.DataFrame(rows).sort_values(["eventId", "isotime"])
    ph.to_csv(f"{outdir}/phase.csv", index=False)
    return ph, pd.DataFrame(kept)


def relocate(outdir, settings_extra):
    cat = hdd.Catalog(f"{outdir}/station.csv", f"{outdir}/event.csv", f"{outdir}/phase.csv")
    cfg = hdd.Config()
    ttt = hdd.NLLGrid(gridPath=NLL_PATH, gridModel="kim1983", maxSearchDistance=0.1)
    dd = hdd.DD(cat, cfg, ttt)
    cc = hdd.ClusteringOptions()
    cc.numEllipsoids = 0
    cc.maxNeighbourDist = 10.0
    cc.minNumNeigh = 1
    cc.maxNumNeigh = 0
    cc.minNumPhases = 1
    so = hdd.SolverOptions()
    so.absLocConstraintStart = 0.0
    so.absLocConstraintEnd = 0.0
    so.dampingFactorStart = 0.01
    so.dampingFactorEnd = 0.01
    clusters = dd.findClusters(cc)
    n_clusters = len(clusters)
    proc = f"{outdir}/processing"
    if os.path.isdir(proc):
        shutil.rmtree(proc)
    new = dd.relocateMultiEvents(clusters, so, saveProcessing=True, processingDataDir=proc)
    new.writeToFile(f"{outdir}/relocated-station.csv", f"{outdir}/relocated-event.csv", f"{outdir}/relocated-phase.csv")
    s = dict(Config=options_dict(cfg), ClusteringOptions=options_dict(cc), SolverOptions=options_dict(so),
             NLLGrid=dict(gridPath=NLL_PATH, gridModel="kim1983", maxSearchDistance=0.1, swapBytes=False,
                          maxOpenFiles=512, accessMethod="KeepOpen (default)"),
             relocateMultiEvents=dict(saveProcessing=True, processingDataDir=proc),
             n_clusters=n_clusters, catalog_files=[f"{outdir}/station.csv", f"{outdir}/event.csv", f"{outdir}/phase.csv"])
    s.update(settings_extra)
    json.dump(s, open(f"{outdir}/settings.json", "w"), indent=1, default=str)
    return n_clusters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--best-json", required=True)
    ap.add_argument("--win-before", type=float, default=5.0)
    ap.add_argument("--win-after", type=float, default=60.0)
    ap.add_argument("--tt-tol", type=float, default=1.0)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    hdd.Logger.setLevel(hdd.Logger.Level.warning)
    best = json.load(open(a.best_json))["best_model"]

    idm = pd.read_csv(f"{DATA}/reference_tables/event_id_map.csv", dtype={"kma_id": str})
    ev = pd.read_csv(f"{CAT}/event.csv").rename(columns={"id": "rtdd_id"}).merge(idm[["rtdd_id", "kma_id", "kma_ml"]], on="rtdd_id")
    ev["origin"] = pd.to_datetime(ev["isotime"], utc=True)
    st0 = pd.read_csv(f"{CAT}/event_centroid_start.csv")
    ev["lat0"], ev["lon0"], ev["dep0"] = st0["latitude"].iloc[0], st0["longitude"].iloc[0], st0["depth"].iloc[0]
    assert st0[["latitude", "longitude", "depth"]].nunique().max() == 1, "start locations differ between events"
    ev["win_before"], ev["win_after"] = a.win_before, a.win_after
    stations = pd.read_csv(f"{CAT}/station.csv").set_index("stationCode")
    bound = pd.read_csv(f"{a.run_dir}/config/stations_bound.csv").set_index("station")
    sensor_of = bound["sensor"].to_dict()
    dl = pd.read_csv(f"{a.run_dir}/analysis/dl_picks_all.csv", dtype={"kma_id": str})
    dl["time"] = pd.to_datetime(dl["time"], utc=True)
    ttt = hdd.NLLGrid(gridPath=NLL_PATH, gridModel="kim1983", maxSearchDistance=0.1)

    solutions, info = {}, {}
    # control: the reference picks, same settings
    d = f"{a.out_dir}/control_phasenet_plus"
    os.makedirs(d, exist_ok=True)
    for f in ("station.csv", "event_centroid_start.csv", "phase.csv"):
        shutil.copyfile(f"{CAT}/{f}", f"{d}/{'event.csv' if f == 'event_centroid_start.csv' else f}")
    ph = pd.read_csv(f"{d}/phase.csv")
    info["control_phasenet_plus"] = dict(picks=dict(P=int((ph["type"] == "P").sum()), S=int((ph["type"] == "S").sum())),
                                         n_clusters=relocate(d, dict(solution="control_phasenet_plus",
                                                                     picks="reference phase.csv (PhaseNet+)")))
    solutions["control_phasenet_plus"] = d
    for m in a.models:
        for assoc in ("window", "window_tt"):
            name = f"dl_{m}_{assoc}"
            d = f"{a.out_dir}/{name}"
            os.makedirs(d, exist_ok=True)
            shutil.copyfile(f"{CAT}/station.csv", f"{d}/station.csv")
            shutil.copyfile(f"{CAT}/event_centroid_start.csv", f"{d}/event.csv")
            ph, kept = build_dl_catalog(dl[dl["variant"] == m], ev, sensor_of, stations, ttt, assoc, a.tt_tol, d)
            kept.to_csv(f"{d}/picks_kept.csv", index=False)
            info[name] = dict(picks=dict(P=int((ph["type"] == "P").sum()), S=int((ph["type"] == "S").sum())),
                              picks_matching_phasenet_plus=int(kept["matched_ref"].sum()),
                              picks_not_matching_phasenet_plus=int((~kept["matched_ref"]).sum()),
                              n_clusters=relocate(d, dict(solution=name, model=m, association=assoc,
                                                          window_s=[-a.win_before, a.win_after],
                                                          tt_tol_s=a.tt_tol if assoc == "window_tt" else None,
                                                          one_pick_per_station_phase="highest confidence")))
            solutions[name] = d

    # diagnostic pair for the best model (variants, reported as such): the SAME observations (event,
    # station, phase) twice, once with the DL pick times (only DL picks that matched a PhaseNet+ pick) and
    # once with the PhaseNet+ times from the reference phase.csv. Their difference is the effect of the
    # pick TIMES alone; the window catalog vs this pair shows the effect of WHICH picks exist.
    q = dl[(dl["variant"] == best) & dl["in_window"].astype(bool) & dl["matched"].astype(bool)]
    rid = dict(zip(ev["kma_id"], ev["rtdd_id"]))
    keys = {(int(rid[k]), s, p) for k, s, p in zip(q["kma_id"], q["station"], q["phase"])}
    refph = pd.read_csv(f"{CAT}/phase.csv")
    sub = refph[[(int(e), s, p) in keys for e, s, p in zip(refph["eventId"], refph["stationCode"], refph["type"])]]
    for name, phdf in ((f"dl_{best}_matched_only", None), (f"control_phasenet_plus_same_subset", sub)):
        d = f"{a.out_dir}/{name}"
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(f"{CAT}/station.csv", f"{d}/station.csv")
        shutil.copyfile(f"{CAT}/event_centroid_start.csv", f"{d}/event.csv")
        if phdf is None:
            rows = [dict(eventId=int(rid[x.kma_id]), isotime=x.time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                         lowerUncertainty="", upperUncertainty="", type=x.phase, networkCode="KS",
                         stationCode=x.station, locationCode="",
                         channelCode=sensor_of[x.station] + ("Z" if x.phase == "P" else "N")) for x in q.itertuples()]
            phdf = pd.DataFrame(rows).sort_values(["eventId", "isotime"])
        phdf.to_csv(f"{d}/phase.csv", index=False)
        info[name] = dict(picks=dict(P=int((phdf["type"] == "P").sum()), S=int((phdf["type"] == "S").sum())),
                          n_clusters=relocate(d, dict(solution=name, model=best,
                                                      association="DL picks matched to a PhaseNet+ pick" if "dl_" in name
                                                      else "reference picks at the same (event, station, phase) set")))
        solutions[name] = d

    # ------------------------------------------------------------------ positions
    dc = pd.read_csv(f"{DATA}/reference_tables/hypodd_dtcc.csv")
    lat0, lon0, dep0 = dc["centroid_lat"].iloc[0], dc["centroid_lon"].iloc[0], dc["centroid_depth_km"].iloc[0]
    pos = []
    for name, f in (("hypodd_dtct", "hypodd_dtct.csv"), ("hypodd_dtcc", "hypodd_dtcc.csv")):
        t = pd.read_csv(f"{DATA}/reference_tables/{f}")
        e, n, u = enu(t["latitude"], t["longitude"], t["depth_km"], lat0, lon0, dep0)
        for i, r in enumerate(t.itertuples()):
            pos.append(dict(solution=name, rtdd_id=r.rtdd_id, east_m=e[i], north_m=n[i], up_m=u[i], relocated=True,
                            boot_ex95_m=r.boot_ex95_m, boot_ey95_m=r.boot_ey95_m, boot_ez95_m=r.boot_ez95_m))
    hi = pd.read_csv(f"{CAT}/event.csv")
    e, n, u = enu(hi["latitude"], hi["longitude"], hi["depth"], lat0, lon0, dep0)
    for i, r in enumerate(hi.itertuples()):
        pos.append(dict(solution="hypoinverse_start", rtdd_id=r.id, east_m=e[i], north_m=n[i], up_m=u[i], relocated=True))
    e, n, u = enu(st0["latitude"], st0["longitude"], st0["depth"], lat0, lon0, dep0)
    for i, r in enumerate(st0.itertuples()):
        pos.append(dict(solution="all_at_centroid", rtdd_id=r.id, east_m=e[i], north_m=n[i], up_m=u[i], relocated=True))
    for name, d in solutions.items():
        t = pd.read_csv(f"{d}/relocated-event.csv")
        rel = t["relocated"].astype(str).str.lower() == "true"
        e, n, u = enu(t["latitude"], t["longitude"], t["depth"], lat0, lon0, dep0)
        for i, r in enumerate(t.itertuples()):
            pos.append(dict(solution=name, rtdd_id=r.id, east_m=e[i], north_m=n[i], up_m=u[i], relocated=bool(rel.iloc[i]),
                            startRms=getattr(r, "startRms", np.nan), finalRms=getattr(r, "finalRms", np.nan)))
        ph = pd.read_csv(f"{d}/relocated-phase.csv")
        used = ph["usedInReloc"].astype(str).str.lower() == "true"
        info[name].update(n_events_relocated=int(rel.sum()), phases_used=dict(P=int((used & (ph["type"] == "P")).sum()),
                                                                              S=int((used & (ph["type"] == "S")).sum())),
                          phases_in_catalog=int(len(ph)),
                          final_rms_median_s=float(t.loc[rel, "finalRms"].median()) if "finalRms" in t else np.nan)
    pos = pd.DataFrame(pos)
    pos.to_csv(f"{a.out_dir}/positions.csv", index=False, float_format="%.2f")

    # ------------------------------------------------------------------ comparisons
    # yardsticks: the two HypoDD solutions, and the pyrtdd control (same relocator, PhaseNet+ picks), which
    # isolates the effect of the picks from the effect of the relocation program
    refs = ("hypodd_dtct", "hypodd_dtcc", "control_phasenet_plus")
    sols = ["all_at_centroid", "hypoinverse_start", "hypodd_dtct", "control_phasenet_plus",
            "control_phasenet_plus_same_subset"] + [n for n in solutions if n.startswith("dl_")]
    rows, per = [], []
    pairs = [(s, r) for s in sols for r in refs if s != r]
    # extra pairs: the pure pick-time effect (same observations), and how much the geometry moves when the
    # travel-time check removes a few picks (window_tt vs window of the same model)
    pairs.append((f"dl_{best}_matched_only", "control_phasenet_plus_same_subset"))
    pairs += [(f"dl_{m}_window_tt", f"dl_{m}_window") for m in a.models]
    for s, r in pairs:
        if True:
            A = pos[(pos["solution"] == s) & pos["relocated"]].set_index("rtdd_id")
            B = pos[pos["solution"] == r].set_index("rtdd_id")
            ids = sorted(set(A.index) & set(B.index))
            a3 = A.loc[ids, ["east_m", "north_m", "up_m"]].to_numpy(float)
            b3 = B.loc[ids, ["east_m", "north_m", "up_m"]].to_numpy(float)
            cs = a3.mean(axis=0) - b3.mean(axis=0)           # metric (b): centroid shift, solution - reference
            a3 = a3 - a3.mean(axis=0)
            b3 = b3 - b3.mean(axis=0)
            dd_ = a3 - b3
            n3 = np.linalg.norm(dd_, axis=1)
            rows.append(dict(solution=s, reference=r, n_events=len(ids),
                             rms_3d_m=float(np.sqrt(np.mean(n3 ** 2))), rms_east_m=float(np.sqrt(np.mean(dd_[:, 0] ** 2))),
                             rms_north_m=float(np.sqrt(np.mean(dd_[:, 1] ** 2))), rms_up_m=float(np.sqrt(np.mean(dd_[:, 2] ** 2))),
                             max_3d_m=float(n3.max()), median_3d_m=float(np.median(n3)),
                             spread_solution_rms_m=float(np.sqrt(np.mean(np.sum(a3 ** 2, axis=1)))),
                             spread_reference_rms_m=float(np.sqrt(np.mean(np.sum(b3 ** 2, axis=1)))),
                             centroid_shift_east_m=float(cs[0]), centroid_shift_north_m=float(cs[1]),
                             centroid_shift_up_m=float(cs[2]), centroid_shift_3d_m=float(np.linalg.norm(cs))))
            for k, i in enumerate(ids):
                per.append(dict(solution=s, reference=r, rtdd_id=i, d_east_m=dd_[k, 0], d_north_m=dd_[k, 1],
                                d_up_m=dd_[k, 2], d_3d_m=n3[k],
                                ref_boot_ex95_m=B.loc[i].get("boot_ex95_m", np.nan),
                                ref_boot_ey95_m=B.loc[i].get("boot_ey95_m", np.nan),
                                ref_boot_ez95_m=B.loc[i].get("boot_ez95_m", np.nan)))
    cmp_ = pd.DataFrame(rows)
    cmp_.to_csv(f"{a.out_dir}/compare_pairs.csv", index=False, float_format="%.2f")
    # metric (b) per solution: centroid of the relocated events - their starting centroid (HypoDD's ISTART=1
    # centroid = event_centroid_start.csv, the start of the HypoDD runs and of every pyrtdd run here)
    S0 = pos[pos["solution"] == "all_at_centroid"].set_index("rtdd_id")
    drift = []
    for name in ["hypodd_dtct", "hypodd_dtcc"] + list(solutions):
        A = pos[(pos["solution"] == name) & pos["relocated"]].set_index("rtdd_id")
        ids = sorted(set(A.index) & set(S0.index))
        cs = (A.loc[ids, ["east_m", "north_m", "up_m"]].to_numpy(float).mean(axis=0)
              - S0.loc[ids, ["east_m", "north_m", "up_m"]].to_numpy(float).mean(axis=0))
        drift.append(dict(solution=name, relocator="HypoDD" if name.startswith("hypodd_") else "pyrtdd",
                          n_events=len(ids), shift_east_m=float(cs[0]), shift_north_m=float(cs[1]),
                          shift_up_m=float(cs[2]), shift_horizontal_m=float(np.hypot(cs[0], cs[1])),
                          shift_3d_m=float(np.linalg.norm(cs))))
    drift_df = pd.DataFrame(drift)
    drift_df.to_csv(f"{a.out_dir}/centroid_shift_from_start.csv", index=False, float_format="%.2f")
    perdf = pd.DataFrame(per).merge(idm[["rtdd_id", "kma_id", "kma_ml"]], on="rtdd_id")
    perdf.to_csv(f"{a.out_dir}/compare_per_event.csv", index=False, float_format="%.2f")
    boot = {r: pd.read_csv(f"{DATA}/reference_tables/{r}.csv")[["boot_ex95_m", "boot_ey95_m", "boot_ez95_m"]].median().to_dict()
            for r in ("hypodd_dtct", "hypodd_dtcc")}
    summary = dict(best_model=best, main_solution=f"dl_{best}_window", solutions=info, comparison=rows,
                   centroid_shift_from_start=dict(
                       definition="centroid of the relocated events - starting centroid (event_centroid_start.csv = "
                                  "HypoDD's ISTART=1 centroid), east/north/up m; the absolute position of a "
                                  "catalog-only solution is not meaningful by itself",
                       rows=drift),
                   reference_bootstrap_95_median_m=boot,
                   enu_origin=dict(lat=lat0, lon=lon0, depth_km=dep0, note="HypoDD dt.cc centroid; WGS84 local tangent plane"))
    json.dump(summary, open(f"{a.out_dir}/reloc_summary.json", "w"), indent=1, default=str)

    pd.set_option("display.width", 250)
    print(json.dumps(info, indent=1, default=str))
    print(cmp_.round(1).to_string(index=False))
    print("centroid shift from the starting centroid (m):")
    print(drift_df.round(1).to_string(index=False))
    print("reference bootstrap 95% half-widths (median over events, m):", {k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in boot.items()})


if __name__ == "__main__":
    main()
