#!/usr/bin/env python
# verify_metrics.py
#
# Independent re-computation of the Gwangyang relocation comparison metrics (a)-(e) for rtDD solutions
# (pyrtdd relocated-event.csv / scrtdd reloc-event.csv) against HypoDD 02.dt.cc and 01.dt.ct.
#
# WHY this file exists: the pyrtdd and scrtdd agents each wrote their own metric code; this verifier
# re-derives every number from the RAW HypoDD outputs (hypoDD.reloc, bootstrap_errors.csv, event.dat,
# Gwangyang_mod.pha) and the raw rtDD CSVs, without using reference_tables/ or the agents' scripts.
#
# Choices (all disclosed, all printed to the JSON dump):
#   * local east/north/up about 35.0000 N 127.7286 E, computed two independent ways:
#       - "tm": pyproj transverse Mercator (WGS84, k=1) centred on that point, up = -depth
#       - "ecef": geodetic -> ECEF -> local ENU tangent plane at that point (depth as negative height)
#     The two must agree to centimetres; the report uses "tm".
#   * HypoDD positions two ways:
#       - "latlon": the LAT/LON/DEPTH columns of hypoDD.reloc (1e-6 deg, 1 m depth resolution)
#       - "xyz": HypoDD's own X/Y/Z columns (0.1 m) added to the cluster centroid it printed in hypoDD.log
#         (X east, Y north, Z down); the absolute frame is then HypoDD's own (SDC) projection.
#   * bootstrap half-widths: raw bootstrap_errors.csv (unrounded) and, for dt.cc, final_locations.csv (0.1 m)
#   * origin times: HypoDD reloc times corrected to the .pha datum (event.dat minus .pha origin, which is
#     0.01 s for 200002 only); the uncorrected variant is also reported.
#
# Run (env pyrtdd):  python -I verify_metrics.py [--apply]  (dry run prints; --apply also writes CSV/JSON here)

import json
import os
import sys
from itertools import combinations

import numpy as np
import pandas as pd
from obspy import UTCDateTime
from pyproj import Transformer

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
OUT = f"{PROJECT}/runs/verify_gwangyang_reloc"
REF = f"{PROJECT}/data/gwangyang_11ev/reference/gwangyang_pnplus/2.HypoDD"
LAT0, LON0 = 35.0000, 127.7286
PY = f"{PROJECT}/runs/gwangyang/pyrtdd"
SC = f"{PROJECT}/runs/gwangyang/scrtdd"
SOLUTIONS = {
    "R0": f"{PY}/R0_catalog_only_hypodd_like/relocated-event.csv",
    "R1": f"{PY}/R1_xcorr_like_reference_hypodd_like/relocated-event.csv",
    "R1f": f"{PY}/R1f_xcorr_like_reference_hypodd_like_filtered/relocated-event.csv",
    "R1fz": f"{PY}/R1fz_xcorr_like_reference_hypodd_like_filtered_zerophase/relocated-event.csv",
    "R2": f"{PY}/R2_xcorr_default_rtdd_default/relocated-event.csv",
    "R2f": f"{PY}/R2f_xcorr_default_rtdd_default_filtered/relocated-event.csv",
    "R3a": f"{PY}/R3a_catalog_only_hypodd_like_hypoinverse_start/relocated-event.csv",
    "R3bf": f"{PY}/R3bf_xcorr_like_reference_hypodd_like_hypoinverse_start_filtered/relocated-event.csv",
    "R4f": f"{PY}/R4f_xcorr_like_reference_hypodd_like_no_outlier_picks_filtered/relocated-event.csv",
    "R5f": f"{PY}/R5f_xcorr_like_reference_hypodd_like_homogeneous_filtered/relocated-event.csv",
    "S0": f"{SC}/S0/work/reloc-event.csv",
    "S0n": f"{SC}/S0n/work/reloc-event.csv",
    "S0h": f"{SC}/S0h/work/reloc-event.csv",
    "S1": f"{SC}/S1/work/reloc-event.csv",
    "S1h": f"{SC}/S1h/work/reloc-event.csv",
    "S2": f"{SC}/S2/work/reloc-event.csv",
    "S2sc": f"{SC}/S2sc/work/reloc-event.csv",
}
RELOC_COLS = ["id", "lat", "lon", "depth", "x", "y", "z", "ex", "ey", "ez", "yr", "mo", "dy", "hr", "mi", "sc",
              "mag", "nccp", "nccs", "nctp", "ncts", "rcc", "rct", "cid"]
HYPODD_CENTROID = {"02.dt.cc": (34.999695, 127.728889, 13.942727), "01.dt.ct": (34.999695, 127.728889, 13.942727)}

APPLY = "--apply" in sys.argv
TM = Transformer.from_crs("EPSG:4326", f"+proj=tmerc +lat_0={LAT0} +lon_0={LON0} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m",
                          always_xy=True)
ECEF = Transformer.from_crs("EPSG:4979", "EPSG:4978", always_xy=True)


def enu_tm(lat, lon, depth_km):
    e, n = TM.transform(np.asarray(lon, float), np.asarray(lat, float))
    return np.column_stack([e, n, -np.asarray(depth_km, float) * 1000.0])


def enu_ecef(lat, lon, depth_km):
    lat = np.asarray(lat, float); lon = np.asarray(lon, float); h = -np.asarray(depth_km, float) * 1000.0
    x, y, z = ECEF.transform(lon, lat, h)
    x0, y0, z0 = ECEF.transform(LON0, LAT0, 0.0)
    la, lo = np.radians(LAT0), np.radians(LON0)
    R = np.array([[-np.sin(lo), np.cos(lo), 0],
                  [-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)],
                  [np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]])
    d = np.vstack([x - x0, y - y0, z - z0])
    return (R @ d).T


def read_pha_origins(path):
    out = {}
    for line in open(path):
        if line.startswith("#"):
            p = line.split()
            t = UTCDateTime(int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5])) + float(p[6])
            out[int(p[-1])] = t
    return out


def read_evdat_origins(path):
    out = {}
    for line in open(path):
        p = line.split()
        d, hms = p[0], int(p[1])
        hh, mm, cs = hms // 1000000, (hms // 10000) % 100, hms % 10000
        t = UTCDateTime(int(d[:4]), int(d[4:6]), int(d[6:8]), hh, mm) + cs / 100.0
        out[int(p[-1])] = t
    return out


def read_hypodd(branch, datum_shift):
    r = pd.read_csv(f"{REF}/{branch}/hypoDD.reloc", sep=r"\s+", header=None, names=RELOC_COLS)
    r["rtdd_id"] = r["id"] - 199999
    r["t_raw"] = [UTCDateTime(int(a.yr), int(a.mo), int(a.dy), int(a.hr), int(a.mi)) + float(a.sc) for a in r.itertuples()]
    r["t_pha"] = [t - datum_shift[i] for t, i in zip(r.t_raw, r["id"])]
    b = pd.read_csv(f"{REF}/{branch}/bootstrap_errors.csv", comment="#")
    r = r.merge(b[["id", "ex95", "ey95", "ez95"]], on="id")
    return r.sort_values("rtdd_id").reset_index(drop=True)


def hypodd_positions(r, branch, how, proj="tm"):
    if how == "latlon":
        f = enu_tm if proj == "tm" else enu_ecef
        return f(r.lat, r.lon, r.depth)
    c = HYPODD_CENTROID[branch]
    f = enu_tm if proj == "tm" else enu_ecef
    c_enu = f([c[0]], [c[1]], [c[2]])[0]
    return c_enu + np.column_stack([r.x, r.y, -r.z])


def read_rtdd(path):
    d = pd.read_csv(path).sort_values("id").reset_index(drop=True)
    d["t"] = [UTCDateTime(s) for s in d.isotime]
    return d


def metrics(P, Q, tP, tQ, half):
    """P, Q: (11,3) ENU (solution, reference); tP, tQ: origin times; half: (11,3) bootstrap half-widths."""
    cP, cQ = P.mean(0), Q.mean(0)
    D = (P - cP) - (Q - cQ)
    h = np.hypot(D[:, 0], D[:, 1]); v = np.abs(D[:, 2]); r3 = np.linalg.norm(D, axis=1)
    inside = np.all(np.abs(D) <= half, axis=1)
    iu = list(combinations(range(len(P)), 2))
    dP = np.array([np.linalg.norm(P[i] - P[j]) for i, j in iu]); dQ = np.array([np.linalg.norm(Q[i] - Q[j]) for i, j in iu])
    dt = np.array([float(a - b) for a, b in zip(tP, tQ)]) * 1000.0
    dt -= dt.mean()
    return dict(h_rms=np.sqrt(np.mean(h ** 2)), h_max=h.max(), v_rms=np.sqrt(np.mean(v ** 2)), v_max=v.max(), d3_max=r3.max(),
                cE=cP[0] - cQ[0], cN=cP[1] - cQ[1], cU=cP[2] - cQ[2], n_inside=int(inside.sum()),
                inside_ids=[i + 1 for i in np.where(inside)[0]],
                r_pairs=np.corrcoef(dP, dQ)[0, 1], rms_pairs=np.sqrt(np.mean((dP - dQ) ** 2)), n_pairs=len(iu),
                ot_rms=np.sqrt(np.mean(dt ** 2)), ot_max=np.abs(dt).max()), D, inside


def main():
    pha = read_pha_origins(f"{REF}/00.ph2dt/Gwangyang_mod.pha")
    evd = read_evdat_origins(f"{REF}/02.dt.cc/event.dat")
    shift = {k: round(float(evd[k] - pha[k]), 6) for k in pha}
    print("event.dat minus .pha origin (s):", {k: v for k, v in shift.items() if v != 0})
    refs = {b: read_hypodd(b, shift) for b in ["02.dt.cc", "01.dt.ct"]}
    fl = pd.read_csv(f"{REF}/02.dt.cc/final_locations.csv", dtype={"event_id": str})
    half_round_cc = fl[["ex95_m", "ey95_m", "ez95_m"]].to_numpy()

    # consistency checks of the reference itself
    for b, r in refs.items():
        A = hypodd_positions(r, b, "latlon"); B = hypodd_positions(r, b, "xyz")
        dd = (A - A.mean(0)) - (B - B.mean(0))
        print(f"[{b}] latlon vs xyz shape diff: max |dE| {abs(dd[:,0]).max():.2f} |dN| {abs(dd[:,1]).max():.2f} |dU| {abs(dd[:,2]).max():.2f} m;"
              f" centroid diff {np.round(A.mean(0)-B.mean(0),2)}")
        A2 = hypodd_positions(r, b, "latlon", "ecef")
        print(f"[{b}] tm vs ecef: max abs diff {np.abs(A - A2).max():.3f} m")

    rows, per_event = [], []
    sols = {k: read_rtdd(v) for k, v in SOLUTIONS.items() if os.path.exists(v)}
    # also the HypoDD dt.ct solution compared with dt.cc, for scale
    for refname, b in [("dtcc", "02.dt.cc"), ("dtct", "01.dt.ct")]:
        r = refs[b]
        for how in ["latlon", "xyz"]:
            Q = hypodd_positions(r, b, how)
            for halfname, half in [("raw", r[["ex95", "ey95", "ez95"]].to_numpy()), ("round01", half_round_cc if b == "02.dt.cc" else np.round(r[["ex95", "ey95", "ez95"]].to_numpy(), 1))]:
                for name, s in sols.items():
                    assert list(s.id) == list(r.rtdd_id)
                    P = enu_tm(s.latitude, s.longitude, s.depth)
                    for tcol in ["t_pha", "t_raw"]:
                        m, D, ins = metrics(P, Q, list(s.t), list(r[tcol]), half)
                        rows.append(dict(run=name, ref=refname, ref_pos=how, half=halfname, ref_time=tcol, **m))
                        if how == "xyz" and halfname == "raw" and tcol == "t_pha":
                            for k in range(len(P)):
                                per_event.append(dict(run=name, ref=refname, event=k + 1, dE=D[k, 0], dN=D[k, 1], dU=D[k, 2],
                                                      exb=half[k, 0], eyb=half[k, 1], ezb=half[k, 2], inside=bool(ins[k])))
                if refname == "dtcc":
                    rc = refs["01.dt.ct"]
                    P = hypodd_positions(rc, "01.dt.ct", how)
                    for tcol in ["t_pha", "t_raw"]:
                        m, D, ins = metrics(P, Q, list(rc[tcol]), list(r[tcol]), half)
                        rows.append(dict(run="HypoDD_dtct", ref=refname, ref_pos=how, half=halfname, ref_time=tcol, **m))
    df = pd.DataFrame(rows)
    if APPLY:
        df.to_csv(f"{OUT}/verify_metrics.csv", index=False)
        pd.DataFrame(per_event).to_csv(f"{OUT}/verify_per_event.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    cols = ["run", "ref", "ref_pos", "half", "h_rms", "h_max", "v_rms", "v_max", "d3_max", "cE", "cN", "cU", "n_inside", "r_pairs", "rms_pairs", "ot_rms", "ot_max"]
    sel = df[(df.ref_time == "t_pha")]
    print(sel[cols].round(2).to_string(index=False))
    if APPLY:
        json.dump(dict(lat0=LAT0, lon0=LON0, solutions=SOLUTIONS, hypodd_centroid=HYPODD_CENTROID, datum_shift_s=shift),
                  open(f"{OUT}/verify_metrics_settings.json", "w"), indent=1)


if __name__ == "__main__":
    main()
