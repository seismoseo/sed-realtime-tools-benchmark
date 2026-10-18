# 13_compare_dd_versions.py -- how different are the two double-difference references, and how much
# of the difference is a common shift?
#   NCEDC DD (DD-RT solutions, depths below the NCSS model surface) vs LDEO NCAeqDD.v202112.1
#   (base catalog re-run in 2022, geoid depths). Also NCSS routine vs each DD.
# For events in both catalogs: (1) per-event 3-D difference, (2) the same after removing the
# median offset (common shift), (3) inter-event vectors for all pairs closer than 2 km in LDEO:
# |v_A - v_B| (km), i.e. how well the two catalogs agree on relative positions.
# Depths: NCEDC DD depth is converted to sea level with each event's NCSS datum (cols 171-174 of
# the Hypoinverse summary line) before comparing with LDEO; this is an approximation (DD-RT used
# the model-surface datum of its own reference events).
# Output: reference_tables/dd_version_comparison.csv (per event), stats_13.json
# Usage: python -I 13_compare_dd_versions.py

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

LAT0, LON0 = 37.786, -121.963


def enu(lat, lon):
    R = 6371.0
    x = np.radians(lon - LON0) * R * np.cos(np.radians(LAT0))
    y = np.radians(lat - LAT0) * R
    return x, y


def pair_stats(A, B, maxsep=2.0):
    """A, B: (n,3) arrays (same events). inter-event vectors for pairs closer than maxsep in B."""
    n = len(A)
    i, j = np.triu_indices(n, 1)
    vb = B[j] - B[i]
    sep = np.linalg.norm(vb, axis=1)
    m = sep < maxsep
    va = A[j[m]] - A[i[m]]
    d = va - vb[m]
    return dict(n_pairs=int(m.sum()),
                median_abs_dvec_h_km=float(np.median(np.hypot(d[:, 0], d[:, 1]))),
                median_abs_dvec_z_km=float(np.median(np.abs(d[:, 2]))),
                p90_dvec_3d_km=float(np.quantile(np.linalg.norm(d, axis=1), 0.9)),
                median_sep_km=float(np.median(sep[m])))


def main():
    st = {}
    ev = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv"))
    ev = ev[ev.benchmark_event]
    dd = pd.read_csv(os.path.join(C.TAB, "dd_catalog.csv"))
    ld = pd.read_csv(os.path.join(C.TAB, "ldeo_dd_catalog.csv"))
    x = ev[["event_id", "latitude", "longitude", "depth_geoid_km", "depth_datum_m"]].merge(
        dd[["event_id", "latitude", "longitude", "depth_km"]].add_prefix("dd_"),
        left_on="event_id", right_on="dd_event_id").merge(
        ld[["event_id", "latitude", "longitude", "depth_km", "eh1_km", "ez_km"]].add_prefix("ld_"),
        left_on="event_id", right_on="ld_event_id")
    P = {}
    P["ncss"] = np.column_stack(enu(x.latitude.values, x.longitude.values) +
                                (x.depth_geoid_km.values,))
    P["ncedc_dd"] = np.column_stack(enu(x.dd_latitude.values, x.dd_longitude.values) +
                                    (x.dd_depth_km.values - x.depth_datum_m.values / 1000.0,))
    P["ldeo_dd"] = np.column_stack(enu(x.ld_latitude.values, x.ld_longitude.values) +
                                   (x.ld_depth_km.values,))
    st["n_events_in_all_three"] = int(len(x))
    out = pd.DataFrame(dict(event_id=x.event_id))
    for a, b in (("ncedc_dd", "ldeo_dd"), ("ncss", "ldeo_dd"), ("ncss", "ncedc_dd")):
        d = P[a] - P[b]
        med = np.median(d, axis=0)
        r = d - med
        out[f"{a}_minus_{b}_dx_km"] = d[:, 0]
        out[f"{a}_minus_{b}_dy_km"] = d[:, 1]
        out[f"{a}_minus_{b}_dz_km"] = d[:, 2]
        st[f"{a}_vs_{b}"] = dict(
            median_offset_km=[round(float(v), 3) for v in med],
            median_abs_h_km=float(np.median(np.hypot(d[:, 0], d[:, 1]))),
            median_abs_z_km=float(np.median(np.abs(d[:, 2]))),
            after_removing_median_offset=dict(
                median_abs_h_km=float(np.median(np.hypot(r[:, 0], r[:, 1]))),
                median_abs_z_km=float(np.median(np.abs(r[:, 2]))),
                p90_3d_km=float(np.quantile(np.linalg.norm(r, axis=1), 0.9))),
            interevent_vectors=pair_stats(P[a], P[b]))
    st["ldeo_relative_errors_95pct"] = dict(median_eh1_km=float(x.ld_eh1_km.median()),
                                            median_ez_km=float(x.ld_ez_km.median()),
                                            p90_eh1_km=float(x.ld_eh1_km.quantile(0.9)),
                                            p90_ez_km=float(x.ld_ez_km.quantile(0.9)),
                                            n_minus1=int((x.ld_eh1_km < 0).sum()))
    out.to_csv(os.path.join(C.TAB, "dd_version_comparison.csv"), index=False, float_format="%.4f")
    with open(os.path.join(C.TAB, "stats_13.json"), "w") as f:
        json.dump(st, f, indent=1)
    print(json.dumps(st, indent=1))


if __name__ == "__main__":
    main()
