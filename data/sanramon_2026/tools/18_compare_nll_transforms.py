# 18_compare_nll_transforms.py -- (2025-26 case; copied from the 2015 tool, stations and centre of
# this case) which NonLinLoc map transform keeps station distances closest to
# true WGS-84 geodesic distances in the San Ramon area? (17_check_nll_projection.py found up to
# 0.3 % error for AZIMUTHAL_EQUIDIST.) For 8 stations of the benchmark at 60-120 km in different
# directions we run Grid2Time (P only, small 2-D grid) once per transform and compare the distance
# from the origin written in the grid header with the geodesic distance. Transforms tried are the
# ones scrtdd's NLL reader supports (libs/hdd/test/data/nll: SIMPLE, SDC, LAMBERT, TRANS_MERC,
# AZIMUTHAL_EQUIDIST). The test grids are deleted afterwards; only the table is kept.
# Output: reference_tables/nll_transform_comparison.csv, stats_18.json
# Usage: python -I 18_compare_nll_transforms.py

import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
from pyproj import Geod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

LAT0, LON0 = C.LAT0, C.LON0
NLL_BIN = os.path.join(C.PROJECT, "software", "NonLinLoc", "bin")
WORK = os.path.join(C.INP, "nll_transform_test")
TRANSFORMS = {
    "AZIMUTHAL_EQUIDIST": f"TRANS AZIMUTHAL_EQUIDIST WGS-84 {LAT0} {LON0} 0.0",
    "TRANS_MERC": f"TRANS TRANS_MERC WGS-84 {LAT0} {LON0} 0.0",
    "LAMBERT": f"TRANS LAMBERT WGS-84 {LAT0} {LON0} 37.0 38.6 0.0",
    "SDC": f"TRANS SDC {LAT0} {LON0} 0.0",
    "SIMPLE": f"TRANS SIMPLE {LAT0} {LON0} 0.0",
}


def main():
    used = pd.read_csv(os.path.join(C.INP, C.NLL_SUBDIR, "stations_used.csv"), keep_default_na=False,
                       dtype={"locationCode": str})
    g = Geod(ellps="WGS84")
    az, _, d = g.inv(np.full(len(used), LON0), np.full(len(used), LAT0),
                     used.longitude.astype(float).values, used.latitude.astype(float).values)
    used["az"], used["geod_km"] = np.mod(az, 360), np.asarray(d) / 1000
    far = used[used.geod_km.between(60, 120)]
    pick = []
    for target in range(0, 360, 45):          # one station per 45-degree sector, the farthest
        sec = far[((far.az - target + 22.5) % 360) < 45]
        if len(sec):
            pick.append(sec.sort_values("geod_km").iloc[-1])
    st_df = pd.DataFrame(pick)
    vel = open(os.path.join(C.INP, C.NLL_SUBDIR, "run", "Vel2Grid.in")).read()
    vel = vel.replace("VGGRID 2 1301 331 0.0 0.0 -3.0 0.1 0.1 0.1 SLOW_LEN",
                      "VGGRID 2 131 41 0.0 0.0 -3.0 1.0 1.0 1.0 SLOW_LEN")
    vel = vel.replace(f"VGOUT ./model/{C.MODEL}", "VGOUT ./model/t")
    assert "VGGRID 2 131 41" in vel and "VGOUT ./model/t" in vel, "Vel2Grid.in replacement failed"
    rows = []
    for name, trans in TRANSFORMS.items():
        if os.path.exists(WORK):
            shutil.rmtree(WORK)
        os.makedirs(os.path.join(WORK, "run"))
        os.makedirs(os.path.join(WORK, "model"))
        os.makedirs(os.path.join(WORK, "time"))
        open(os.path.join(WORK, "run", "general.in"), "w").write(f"CONTROL 0 54321\n{trans}\n")
        open(os.path.join(WORK, "run", "Vel2Grid.in"), "w").write(vel)
        open(os.path.join(WORK, "run", "Grid2Time.in"), "w").write("GTMODE GRID2D ANGLES_NO\nGT_PLFD 1.0e-3 0\n")
        open(os.path.join(WORK, "stations.in"), "w").write("\n".join(
            f"GTSRCE {r.label} LATLON {float(r.latitude):.6f} {float(r.longitude):.6f} 0.0 "
            f"{float(r.elevation) / 1000:.4f}" for r in st_df.itertuples()) + "\n")
        open(os.path.join(WORK, "run", "phaseP.run"), "w").write(
            "VGTYPE P\nGTFILES ./model/t ./time/t P\nINCLUDE stations.in\nINCLUDE run/general.in\n"
            "INCLUDE run/Vel2Grid.in\nINCLUDE run/Grid2Time.in\n")
        for prog in ("Vel2Grid", "Grid2Time"):
            subprocess.run([os.path.join(NLL_BIN, prog), "run/phaseP.run"], cwd=WORK, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for r in st_df.itertuples():
            h = open(os.path.join(WORK, "time", f"t.P.{r.label}.time.hdr")).read().splitlines()
            _, x, y, _ = h[1].split()
            dn = float(np.hypot(float(x), float(y)))
            rows.append(dict(transform=name, label=r.label, azimuth_deg=r.az, geodesic_km=r.geod_km,
                             nll_km=dn, diff_m=(dn - r.geod_km) * 1000,
                             rel_diff_pct=(dn - r.geod_km) / r.geod_km * 100))
    shutil.rmtree(WORK)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(C.TAB, "nll_transform_comparison.csv"), index=False, float_format="%.4f")
    summ = df.groupby("transform").diff_m.agg(max_abs_m=lambda x: x.abs().max(),
                                             mean_m="mean").reset_index()
    with open(os.path.join(C.TAB, "stats_18.json"), "w") as f:
        json.dump(dict(stations=st_df.label.tolist(), summary=summ.to_dict("records")), f, indent=1)
    print(summ.to_string())
    print(df.pivot(index="label", columns="transform", values="diff_m").round(1).to_string())


if __name__ == "__main__":
    main()
