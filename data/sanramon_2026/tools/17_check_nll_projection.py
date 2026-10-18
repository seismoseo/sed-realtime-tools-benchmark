# 17_check_nll_projection.py -- (2025-26 case; copied from the 2015 tool) how far does NonLinLoc's
# TRANS_MERC projection (as written into the grid headers, and as used by rtDD) depart from true
# WGS-84 distances? For each station grid of inputs/nll_con_tm: distance from the projection origin
# in NLL's x,y versus the WGS-84 geodesic distance from the origin (= the swarm centre).
# Output: reference_tables/nll_projection_check.csv, stats_17.json
# Usage: python -I 17_check_nll_projection.py

import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from pyproj import Geod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

LAT0, LON0 = C.LAT0, C.LON0
TIME = os.path.join(C.INP, C.NLL_SUBDIR, "time")


def main():
    used = pd.read_csv(os.path.join(C.INP, C.NLL_SUBDIR, "stations_used.csv"), keep_default_na=False,
                       dtype={"locationCode": str})
    g = Geod(ellps="WGS84")
    rows = []
    for r in used.itertuples():
        h = open(os.path.join(TIME, f"{C.MODEL}.P.{r.label}.time.hdr")).read().splitlines()
        _, x, y, z = h[1].split()
        x, y = float(x), float(y)
        az, _, d = g.inv(LON0, LAT0, float(r.longitude), float(r.latitude))
        dn = np.hypot(x, y)
        rows.append(dict(label=r.label, geodesic_km=d / 1000, nll_km=dn,
                         diff_m=(dn - d / 1000) * 1000, rel_diff_pct=(dn - d / 1000) / (d / 1000) * 100
                         if d > 0 else 0.0, azimuth_deg=az % 360))
    df = pd.DataFrame(rows).sort_values("geodesic_km")
    df.to_csv(os.path.join(C.TAB, "nll_projection_check.csv"), index=False, float_format="%.4f")
    far = df[df.geodesic_km > 20]
    st = dict(n=int(len(df)), max_abs_diff_m=float(df.diff_m.abs().max()),
              diff_m_at_max_distance=float(df.diff_m.iloc[-1]),
              rel_diff_pct_range_beyond_20km=[float(far.rel_diff_pct.min()), float(far.rel_diff_pct.max())],
              median_rel_diff_pct_beyond_20km=float(far.rel_diff_pct.median()))
    # crude dependence on azimuth: north-south vs east-west
    ns = far[(far.azimuth_deg < 30) | (far.azimuth_deg > 330) | far.azimuth_deg.between(150, 210)]
    ew = far[far.azimuth_deg.between(60, 120) | far.azimuth_deg.between(240, 300)]
    st["median_rel_diff_pct_NS"] = float(ns.rel_diff_pct.median()) if len(ns) else None
    st["median_rel_diff_pct_EW"] = float(ew.rel_diff_pct.median()) if len(ew) else None
    with open(os.path.join(C.TAB, "stats_17.json"), "w") as f:
        json.dump(st, f, indent=1)
    print(json.dumps(st, indent=1))
    print(df.tail(5).to_string())


if __name__ == "__main__":
    main()
