# v09_reloc_check.py -- independent verifier of step 09, part 5 (end-to-end DL-pick relocation numbers).
# Env: pyrtdd (pyrtdd, numpy, pandas, pyproj, obspy, lxml). Run with 'python -I'.
#
# Why: step 09 reports, for the catalog-only pyrtdd relocation, metric (a) "relative geometry" (each event's
# offset from its own solution's 11-event centroid, minus the same offset in the reference solution; RMS over
# the 11 events, 3-D and per component), e.g. best DL model vs the PhaseNet+ control 49.1 m (E16.4/N8.0/U45.6),
# vs HypoDD dt.cc 81.8 m. Three independent checks:
#   1. Recompute metric (a) from step 09's own relocated-event.csv files and the HypoDD tables with MY
#      east/north conversion (pyproj azimuthal-equidistant projection on WGS84, centred on the dt.cc centroid;
#      step 09 used a linearised local tangent plane), and compare with compare_pairs.csv.
#   2. Rebuild the main DL catalog (phasenet_original, association 'window') from the raw picks.xml with my
#      own parser and the stated rule (HYPOINVERSE origin -5 s .. +60 s, one pick per station and phase = the
#      most confident, ties -> earlier; P on <sensor>Z, S on <sensor>N; blank uncertainties) and compare it
#      with step 09's phase.csv.
#   3. Re-run pyrtdd myself on (i) my rebuilt DL catalog and (ii) the control catalog (reference phase.csv),
#      with the stated 'hypodd_like' options, dump every option value by introspection, and compare the
#      positions with step 09's (expected identical if the run is deterministic) and recompute metric (a).
# Usage: python -I v09_reloc_check.py            # dry run: checks 1-2 printed, no relocation, nothing written
#        python -I v09_reloc_check.py --apply    # also run 3 and write results

import argparse
import json
import os
import shutil
import sys

import numpy as np
import obspy
import pandas as pd
import pyproj
from lxml import etree

# ------------------------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
CAT = f"{DATA}/inputs/rtdd_catalog"
RUN09 = f"{PROJECT}/runs/gwangyang/dlpicker"
RELOC09 = f"{RUN09}/reloc"
OUT_DIR = f"{PROJECT}/runs/verify_gwangyang_dl/reloc"
NLL_PATH = f"{DATA}/inputs/nll_kim1983/time"
BEST = "phasenet_original"
WIN_BEFORE, WIN_AFTER = 5.0, 60.0
SOLUTIONS09 = ["control_phasenet_plus", "control_phasenet_plus_same_subset", "dl_phasenet_original_window",
               "dl_phasenet_original_window_tt", "dl_phasenet_original_matched_only", "dl_phasenet_instance_window",
               "dl_eqtransformer_stead_window", "dl_phasenet_stead_window"]
REFS = ["hypodd_dtct", "hypodd_dtcc", "control_phasenet_plus"]
# 'hypodd_like' options stated in the step-09 notes (everything else at the pyrtdd defaults)
CLUSTERING = dict(numEllipsoids=0, maxNeighbourDist=10.0, minNumNeigh=1, maxNumNeigh=0, minNumPhases=1)
SOLVER = dict(absLocConstraintStart=0.0, absLocConstraintEnd=0.0, dampingFactorStart=0.01, dampingFactorEnd=0.01)
NLL = dict(gridPath=NLL_PATH, gridModel="kim1983", maxSearchDistance=0.1)
NS = 1_000_000_000


def ns(t):
    return obspy.UTCDateTime(t).ns


def options(o):
    d = {}
    for k in sorted(dir(o)):
        if k.startswith("_"):
            continue
        v = getattr(o, k)
        if callable(v):
            continue
        d[k] = v if isinstance(v, (int, float, str, bool, list)) else repr(v)
    return d


# ------------------------------------------------------------------------------------------- positions
def enu_factory(lat0, lon0, dep0):
    proj = pyproj.Proj(proj="aeqd", lat_0=lat0, lon_0=lon0, datum="WGS84", units="m")

    def f(lat, lon, depth_km):
        e, n = proj(np.asarray(lon, float), np.asarray(lat, float))
        return np.asarray(e), np.asarray(n), -(np.asarray(depth_km, float) - dep0) * 1000.0
    return f


def metric_a(A, B):
    """A, B: DataFrames indexed by rtdd_id with east/north/up [m]. Returns RMS of centroid-removed differences."""
    ids = sorted(set(A.index) & set(B.index))
    a = A.loc[ids, ["e", "n", "u"]].to_numpy(float)
    b = B.loc[ids, ["e", "n", "u"]].to_numpy(float)
    d = (a - a.mean(0)) - (b - b.mean(0))
    r3 = np.linalg.norm(d, axis=1)
    return dict(n_events=len(ids), rms_3d_m=float(np.sqrt(np.mean(r3 ** 2))), rms_east_m=float(np.sqrt(np.mean(d[:, 0] ** 2))),
                rms_north_m=float(np.sqrt(np.mean(d[:, 1] ** 2))), rms_up_m=float(np.sqrt(np.mean(d[:, 2] ** 2))),
                rms_horizontal_m=float(np.sqrt(np.mean(d[:, 0] ** 2 + d[:, 1] ** 2))), max_3d_m=float(r3.max()),
                spread_A_m=float(np.sqrt(np.mean(np.sum((a - a.mean(0)) ** 2, 1)))),
                spread_B_m=float(np.sqrt(np.mean(np.sum((b - b.mean(0)) ** 2, 1)))))


# ------------------------------------------------------------------------------------------- DL catalog
def read_picks_xml(path):
    rows = []
    for p in etree.parse(path).iter("{*}pick"):
        wf = p.find("{*}waveformID")
        com = {c.findtext("{*}id"): c.findtext("{*}text") for c in p.findall("{*}comment")}
        conf = float(com["confidence"]) if "confidence" in com else float(com.get("SNR", "nan"))
        t = p.find("{*}time/{*}value").text
        rows.append(dict(t_ns=ns(t), station=wf.get("stationCode"), phase=p.findtext("{*}phaseHint"), conf=conf))
    return pd.DataFrame(rows)


def build_dl_phase_csv(ev, sensor):
    rows = []
    for e in ev.itertuples():
        d = read_picks_xml(f"{RUN09}/output/{BEST}/{e.kma_id}/picks.xml")
        d = d[(d.t_ns >= e.o_ns - int(WIN_BEFORE * NS)) & (d.t_ns <= e.o_ns + int(WIN_AFTER * NS))]
        d = d.sort_values(["conf", "t_ns"], ascending=[False, True]).groupby(["station", "phase"]).head(1)
        for x in d.itertuples():
            rows.append(dict(eventId=int(e.rtdd_id),
                             isotime=obspy.UTCDateTime(ns=int(x.t_ns)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                             lowerUncertainty="", upperUncertainty="", type=x.phase, networkCode="KS",
                             stationCode=x.station, locationCode="",
                             channelCode=sensor[x.station] + ("Z" if x.phase == "P" else "N")))
    return pd.DataFrame(rows).sort_values(["eventId", "isotime", "stationCode", "type"]).reset_index(drop=True)


def relocate(folder, phase_src_df):
    import pyrtdd.hdd as hdd
    os.makedirs(folder, exist_ok=True)
    shutil.copyfile(f"{CAT}/station.csv", f"{folder}/station.csv")
    shutil.copyfile(f"{CAT}/event_centroid_start.csv", f"{folder}/event.csv")
    phase_src_df.to_csv(f"{folder}/phase.csv", index=False)
    cat = hdd.Catalog(f"{folder}/station.csv", f"{folder}/event.csv", f"{folder}/phase.csv")
    cfg = hdd.Config()
    ttt = hdd.NLLGrid(**NLL)
    dd = hdd.DD(cat, cfg, ttt)
    co = hdd.ClusteringOptions()
    for k, v in CLUSTERING.items():
        setattr(co, k, v)
    so = hdd.SolverOptions()
    for k, v in SOLVER.items():
        setattr(so, k, v)
    clusters = dd.findClusters(co)
    proc = f"{folder}/processing"
    if os.path.isdir(proc):
        shutil.rmtree(proc)
    new = dd.relocateMultiEvents(clusters, so, saveProcessing=True, processingDataDir=proc)
    new.writeToFile(f"{folder}/relocated-station.csv", f"{folder}/relocated-event.csv", f"{folder}/relocated-phase.csv")
    s = dict(Config=options(cfg), ClusteringOptions=options(co), SolverOptions=options(so), NLLGrid=NLL,
             n_clusters=len(clusters), relocateMultiEvents=dict(saveProcessing=True, processingDataDir=proc),
             catalog=[f"{folder}/station.csv", f"{folder}/event.csv", f"{folder}/phase.csv"])
    json.dump(s, open(f"{folder}/settings.json", "w"), indent=1, default=str)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    res = {}

    dc = pd.read_csv(f"{DATA}/reference_tables/hypodd_dtcc.csv", dtype={"kma_id": str})
    lat0, lon0, dep0 = float(dc.latitude.mean()), float(dc.longitude.mean()), float(dc.depth_km.mean())
    enu = enu_factory(lat0, lon0, dep0)
    pos = {}

    def put(name, ids, lat, lon, dep):
        e, n, u = enu(lat, lon, dep)
        pos[name] = pd.DataFrame(dict(e=e, n=n, u=u), index=pd.Index(ids, name="rtdd_id"))

    for name in ("hypodd_dtct", "hypodd_dtcc"):
        t = pd.read_csv(f"{DATA}/reference_tables/{name}.csv")
        put(name, t.rtdd_id, t.latitude, t.longitude, t.depth_km)
    st0 = pd.read_csv(f"{CAT}/event_centroid_start.csv")
    put("all_at_centroid", st0.id, st0.latitude, st0.longitude, st0.depth)
    for s in SOLUTIONS09:
        t = pd.read_csv(f"{RELOC09}/{s}/relocated-event.csv")
        t = t[t.relocated.astype(str).str.lower() == "true"]
        put(s, t.id, t.latitude, t.longitude, t.depth)

    # 1. metric (a) from step 09's outputs, my conversion, vs compare_pairs.csv
    c09 = pd.read_csv(f"{RELOC09}/compare_pairs.csv")
    rows = []
    pairs = [(s, r) for s in ["all_at_centroid", "hypodd_dtct"] + SOLUTIONS09 for r in REFS if s != r]
    pairs.append(("dl_phasenet_original_matched_only", "control_phasenet_plus_same_subset"))
    for s, r in pairs:
        m = metric_a(pos[s], pos[r])
        c = c09[(c09.solution == s) & (c09.reference == r)]
        m.update(solution=s, reference=r)
        if len(c) == 1:
            c = c.iloc[0]
            m.update(claimed_rms_3d_m=c.rms_3d_m, claimed_rms_east_m=c.rms_east_m, claimed_rms_north_m=c.rms_north_m,
                     claimed_rms_up_m=c.rms_up_m, abs_diff_3d_m=abs(m["rms_3d_m"] - c.rms_3d_m))
        rows.append(m)
    mt = pd.DataFrame(rows)
    res["metric_a_from_step09_outputs_max_abs_diff_m"] = float(mt.abs_diff_3d_m.max())
    # HypoDD bootstrap 95 % half-widths, median over the 11 events (claimed dt.ct 34/17/43 m, dt.cc 3/2/6 m)
    res["hypodd_bootstrap95_median_m"] = {n: pd.read_csv(f"{DATA}/reference_tables/{n}.csv")[
        ["boot_ex95_m", "boot_ey95_m", "boot_ez95_m"]].median().round(2).to_dict() for n in ("hypodd_dtct", "hypodd_dtcc")}
    # metric (b), not reported by step 09: where each solution put the whole cluster (centroid shift vs dt.cc)
    cb = {}
    for s in ["hypodd_dtct", "all_at_centroid"] + SOLUTIONS09:
        ids = sorted(set(pos[s].index) & set(pos["hypodd_dtcc"].index))
        d = pos[s].loc[ids].mean() - pos["hypodd_dtcc"].loc[ids].mean()
        cb[s] = dict(east_m=round(float(d.e), 1), north_m=round(float(d.n), 1), up_m=round(float(d.u), 1),
                     norm_m=round(float(np.linalg.norm(d.to_numpy())), 1))
    res["centroid_shift_vs_dtcc_m"] = cb

    # 2. rebuild the main DL catalog and compare with step 09's phase.csv
    hyp = pd.read_csv(f"{DATA}/reference_tables/hypoinverse_kim1983.csv", dtype={"kma_id": str})
    hyp["o_ns"] = [ns(t) for t in hyp.origin_time]
    sb = pd.read_csv(f"{RUN09}/config/stations_bound.csv")
    sensor = dict(zip(sb.station, sb.sensor))
    mine = build_dl_phase_csv(hyp[["rtdd_id", "kma_id", "o_ns"]], sensor)
    theirs = pd.read_csv(f"{RELOC09}/dl_{BEST}_window/phase.csv", keep_default_na=False)
    key = ["eventId", "stationCode", "type", "channelCode"]
    mine_k = mine.assign(t_ns=[ns(t) for t in mine.isotime])
    theirs_k = theirs.assign(t_ns=[ns(t) for t in theirs.isotime])
    j = mine_k[key + ["t_ns"]].merge(theirs_k[key + ["t_ns"]], on=key, how="outer", suffixes=("_mine", "_09"),
                                     indicator=True)
    res["dl_catalog_rebuild"] = dict(n_mine=len(mine), n_step09=len(theirs),
                                     P_mine=int((mine.type == "P").sum()), S_mine=int((mine.type == "S").sum()),
                                     only_mine=int((j["_merge"] == "left_only").sum()),
                                     only_step09=int((j["_merge"] == "right_only").sum()),
                                     time_differs=int(((j["_merge"] == "both") & (j.t_ns_mine != j.t_ns_09)).sum()))

    # 3. re-run pyrtdd (apply only)
    if a.apply:
        os.makedirs(OUT_DIR, exist_ok=True)
        ctrl = pd.read_csv(f"{CAT}/phase.csv", keep_default_na=False)
        settings = {}
        for name, df in (("my_dl_phasenet_original_window", mine), ("my_control_phasenet_plus", ctrl)):
            settings[name] = relocate(f"{OUT_DIR}/{name}", df)
            t = pd.read_csv(f"{OUT_DIR}/{name}/relocated-event.csv")
            res[f"{name}_n_relocated"] = int((t.relocated.astype(str).str.lower() == "true").sum())
            t = t[t.relocated.astype(str).str.lower() == "true"]
            put(name, t.id, t.latitude, t.longitude, t.depth)
        rr = []
        for s, r in (("my_dl_phasenet_original_window", "dl_phasenet_original_window"),
                     ("my_control_phasenet_plus", "control_phasenet_plus"),
                     ("my_dl_phasenet_original_window", "my_control_phasenet_plus"),
                     ("my_dl_phasenet_original_window", "hypodd_dtcc"),
                     ("my_dl_phasenet_original_window", "hypodd_dtct"),
                     ("my_control_phasenet_plus", "hypodd_dtcc")):
            m = metric_a(pos[s], pos[r])
            m.update(solution=s, reference=r)
            A, B = pos[s], pos[r]
            ids = sorted(set(A.index) & set(B.index))
            m["max_abs_position_diff_m"] = float(np.abs(A.loc[ids].to_numpy() - B.loc[ids].to_numpy()).max())
            rr.append(m)
        rerun = pd.DataFrame(rr)
        rerun.to_csv(f"{OUT_DIR}/rerun_metric_a.csv", index=False, float_format="%.3f")
        mt.to_csv(f"{OUT_DIR}/metric_a_from_step09_outputs.csv", index=False, float_format="%.3f")
        mine.to_csv(f"{OUT_DIR}/my_dl_phasenet_original_window_phase.csv", index=False)
        json.dump(dict(settings=dict(script=os.path.abspath(__file__), BEST=BEST, WIN=[-WIN_BEFORE, WIN_AFTER],
                                     CLUSTERING=CLUSTERING, SOLVER=SOLVER, NLL=NLL,
                                     enu=f"pyproj aeqd WGS84 centred on mean dt.cc position {lat0:.6f} {lon0:.6f} {dep0:.4f} km",
                                     resolved_options=settings,
                                     versions=dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__,
                                                   pyproj=pyproj.__version__)),
                       results=res), open(f"{OUT_DIR}/reloc_check.json", "w"), indent=1, default=str)
        print(rerun.round(2).to_string(index=False))
    pd.set_option("display.width", 250)
    print(mt[["solution", "reference", "rms_3d_m", "claimed_rms_3d_m", "rms_east_m", "claimed_rms_east_m", "rms_north_m",
              "claimed_rms_north_m", "rms_up_m", "claimed_rms_up_m", "rms_horizontal_m", "max_3d_m"]].round(2).to_string(index=False))
    print(json.dumps(res, indent=1))
    if not a.apply:
        print("dry run: no relocation run, nothing written (use --apply)")


if __name__ == "__main__":
    main()
