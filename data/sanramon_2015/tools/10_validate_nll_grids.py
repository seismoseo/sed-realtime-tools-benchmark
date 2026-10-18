# 10_validate_nll_grids.py -- check the NonLinLoc travel-time grids of inputs/nll_con against
# two independent 1-D calculations:
#   (a) ray1d.py (our own ray shooting in the same gradient model; itself checked against the NCSS
#       TTGEN table to <= 6 ms) for 5 real stations (near to far, different elevations), at grid
#       nodes (distance 0-130 km every 2 km, depth 1-20 km every 1 km) and at 100 benchmark
#       event positions (bilinear interpolation in rtDD's projected distance, as rtDD reads 2-D grids);
#   (b) the NCSS TTGEN travel-time table of the CON model (cor.crt), for a virtual station placed
#       on the NCSS model surface (0.29 km above sea level): grid built in inputs/nll_con_validation
#       with the same control files (only this one GTSRCE), compared at the TTGEN depths/distances.
# Output: reference_tables/nll_validation.csv (+ printed summary, stats_10.json)
# Usage: python -I 10_validate_nll_grids.py     (after tools/make_nll_grids.sh)

import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
from pyproj import Proj

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ray1d  # noqa: E402
import sr_common as C  # noqa: E402

NLLDIR = os.path.join(C.INP, "nll_con")
VALDIR = os.path.join(C.INP, "nll_con_validation")
MODEL = "sanramon_con"
DATUM_KM = 0.29
NLL_BIN = os.path.join(C.PROJECT, "software", "NonLinLoc", "bin")
N_EVENTS = 100      # benchmark events used for the at-event check (evenly spaced in id order)


def read_grid(base):
    h = open(base + ".hdr").read().splitlines()
    p = h[0].split()
    nx, ny, nz = int(p[0]), int(p[1]), int(p[2])
    x0, y0, z0, dx, dy, dz = map(float, p[3:9])
    src = h[1].split() if len(h) > 2 else None
    # 2-D time/angle .buf files hold 2 x-planes although the header says nx=1; like rtDD
    # (libs/hdd/nll/grid.cpp) we use the header dimensions, i.e. the first (source) plane
    a = np.fromfile(base + ".buf", dtype="<f4", count=nx * ny * nz).reshape(nx, ny, nz)
    return dict(a=a, y0=y0, z0=z0, dy=dy, dz=dz, ny=ny, nz=nz, src=src, hdr=h)


def bilinear(g, dist, depth):
    fy = (dist - g["y0"]) / g["dy"]
    fz = (depth - g["z0"]) / g["dz"]
    iy, iz = np.floor(fy).astype(int), np.floor(fz).astype(int)
    ty, tz = fy - iy, fz - iz
    a = g["a"][0]
    v00, v10 = a[iy, iz], a[iy + 1, iz]
    v01, v11 = a[iy, iz + 1], a[iy + 1, iz + 1]
    return (v00 * (1 - ty) * (1 - tz) + v10 * ty * (1 - tz) + v01 * (1 - ty) * tz + v11 * ty * tz)


def models():
    vm = pd.read_csv(os.path.join(C.INP, "velocity_model.csv"))
    pts = vm.iloc[1:]                     # row 0 = constant extension above the model surface
    z = pts.top_km.values
    # 10 m sub-layers: ray1d with dz=0.01 matches the NCSS TTGEN table to <= 6 ms
    return (ray1d.Model1D(z, pts.vp_km_s.values, z_top=vm.top_km.iloc[0], dz=0.01),
            ray1d.Model1D(z, pts.vs_km_s.values, z_top=vm.top_km.iloc[0], dz=0.01))


def main():
    st = {}
    mP, mS = models()
    use = pd.read_csv(os.path.join(NLLDIR, "stations_used.csv"), keep_default_na=False,
                      dtype={"locationCode": str})
    det = pd.read_csv(os.path.join(C.TAB, "rtdd_stations_detail.csv"), keep_default_na=False,
                      dtype={"location": str})
    use = use.merge(det[["network", "station", "location", "depth_m"]],
                    left_on=["networkCode", "stationCode", "locationCode"],
                    right_on=["network", "station", "location"], how="left")
    use["elev_km"] = use.elevation.astype(float) / 1000
    # pick 5 stations: nearest, ~20, ~50, ~85, ~115 km (closest to these targets)
    chosen = []
    for target in (0, 20, 50, 85, 115):
        cand = use[~use.label.isin(chosen)].copy()
        cand["score"] = (cand.dist_km - target).abs()
        chosen.append(cand.sort_values("score").label.iloc[0])
    # swap one for the highest station within 60 km if not already there
    hi = use[use.dist_km < 60].sort_values("elev_km").label.iloc[-1]
    if hi not in chosen:
        chosen[2] = hi
    st["chosen"] = use[use.label.isin(chosen)][["label", "dist_km", "elev_km", "depth_m"]].to_dict("records")
    ev = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv"))
    ev = ev[ev.benchmark_event].sort_values("event_id")
    ev = ev.iloc[np.linspace(0, len(ev) - 1, N_EVENTS).round().astype(int)]   # deterministic subset
    # rtDD measures the event-station distance in the grid's projected plane
    # (libs/hdd/nll/grid.cpp: transform->fromLatLon, then sqrt(dx^2+dy^2) to the header source)
    aeqd = Proj(proj="aeqd", lat_0=37.786, lon_0=-121.963, ellps="WGS84")
    ex, ey = aeqd(ev.longitude.values, ev.latitude.values)
    ex, ey = np.asarray(ex) / 1000, np.asarray(ey) / 1000
    proj_check = []
    rows = []
    for lab in chosen:
        s = use[use.label == lab].iloc[0]
        zr = -s.elev_km
        for ph, m in (("P", mP), ("S", mS)):
            G = read_grid(os.path.join(NLLDIR, "time", f"{MODEL}.{ph}.{lab}.time"))
            # (1) nodes
            dists = np.arange(0.0, 130.01, 2.0)
            for zz in np.arange(1.0, 20.01, 1.0):
                iz = int(round((zz - G["z0"]) / G["dz"]))
                iy = np.round((dists - G["y0"]) / G["dy"]).astype(int)
                t_nll = G["a"][0, iy, iz]
                t_ray, br = m.time(dists, zz, zr, n_p=2000, return_branch=True)
                for d, a_, b_, r_ in zip(dists, t_nll, t_ray, br):
                    rows.append(dict(kind="node", label=lab, phase=ph, dist_km=d, depth_km=zz,
                                     t_nll=float(a_), t_ray=float(b_), branch=r_))
            # (2) events, bilinear as rtDD does for 2-D grids
            sx, sy, sz = (float(v) for v in G["src"][1:4])
            px, py = aeqd(float(s.longitude), float(s.latitude))
            proj_check.append(dict(label=lab, phase=ph, nll_x=sx, nll_y=sy, nll_z=sz,
                                   proj_dx_m=(px / 1000 - sx) * 1000,
                                   proj_dy_m=(py / 1000 - sy) * 1000,
                                   dz_vs_elev_m=(sz + s.elev_km) * 1000))
            dk = np.hypot(ex - sx, ey - sy)
            t_nll = bilinear(G, dk, ev.depth_geoid_km.values)
            for d0, z0, a_, eid in zip(dk, ev.depth_geoid_km.values, t_nll, ev.event_id.values):
                rows.append(dict(kind="event", label=lab, phase=ph, dist_km=d0, depth_km=z0,
                                 t_nll=float(a_), t_ray=np.nan, event_id=int(eid)))
    df = pd.DataFrame(rows)
    # ray times for events (vectorised per station/phase/depth bins is complex; loop per event)
    for (lab, ph), sub in df[df.kind == "event"].groupby(["label", "phase"]):
        s = use[use.label == lab].iloc[0]
        m = mP if ph == "P" else mS
        for z0, sub2 in sub.groupby("depth_km"):
            df.loc[sub2.index, "t_ray"] = m.time(sub2.dist_km.values, z0, -s.elev_km, n_p=2000)
    df["diff_s"] = df.t_nll - df.t_ray
    df["rel_diff"] = df.diff_s / df.t_ray
    df.to_csv(os.path.join(C.TAB, "nll_validation.csv"), index=False, float_format="%.5f")
    summ = df.groupby(["kind", "label", "phase"]).diff_s.agg(
        n="size", mean="mean", max_abs=lambda x: x.abs().max(),
        p95_abs=lambda x: x.abs().quantile(0.95)).reset_index()
    st["summary_ray1d"] = summ.to_dict("records")
    st["projection_check"] = proj_check
    print(summ.to_string())
    print(pd.DataFrame(proj_check).to_string())

    # (b) TTGEN check with a virtual station on the model surface
    if os.path.exists(os.path.join(NLL_BIN, "Grid2Time")):
        if os.path.exists(VALDIR):
            shutil.rmtree(VALDIR)
        os.makedirs(os.path.join(VALDIR, "run"))
        for f in ("general.in", "Vel2Grid.in", "Grid2Time.in", "phaseP.run"):
            shutil.copy(os.path.join(NLLDIR, "run", f), os.path.join(VALDIR, "run", f))
        with open(os.path.join(VALDIR, "stations.in"), "w") as f:
            f.write(f"GTSRCE VIRT_SURF LATLON 37.786 -121.963 0.0 {DATUM_KM:.3f}\n")
        os.makedirs(os.path.join(VALDIR, "model"))
        os.makedirs(os.path.join(VALDIR, "time"))
        for prog in ("Vel2Grid", "Grid2Time"):
            subprocess.run([os.path.join(NLL_BIN, prog), "run/phaseP.run"], cwd=VALDIR,
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        G = read_grid(os.path.join(VALDIR, "time", f"{MODEL}.P.VIRT_SURF.time"))
        tab = pd.read_csv(os.path.join(C.TAB, "ncss_con_ttgen_table.csv"))
        tab = tab[(tab.depth_model_km <= 20) & (tab.dist_km < 129.95)].copy()   # grid ends at 130 km
        tab["depth_sea_km"] = tab.depth_model_km - DATUM_KM
        tab = tab[tab.depth_sea_km >= G["z0"] + 0.2]
        tab["t_nll"] = bilinear(G, tab.dist_km.values, tab.depth_sea_km.values)
        tab["diff_s"] = tab.t_nll - tab.ttime_s
        tab.to_csv(os.path.join(C.TAB, "nll_validation_ttgen.csv"), index=False,
                   float_format="%.5f")
        st["summary_ttgen"] = dict(n=int(len(tab)), mean=float(tab.diff_s.mean()),
                                   max_abs=float(tab.diff_s.abs().max()),
                                   p95_abs=float(tab.diff_s.abs().quantile(0.95)))
        print("TTGEN check:", st["summary_ttgen"])
        shutil.rmtree(os.path.join(VALDIR, "model"))      # keep only the time grid of VIRT_SURF
    with open(os.path.join(C.TAB, "stats_10.json"), "w") as f:
        json.dump(st, f, indent=1, default=str)


if __name__ == "__main__":
    main()
