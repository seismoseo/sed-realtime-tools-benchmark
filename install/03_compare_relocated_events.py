# 03_compare_relocated_events.py -- used by 03_install_pyrtdd.sh (step example).
#
# Compares a relocated event catalog written by pyrtdd (relocated-event.csv) with the reference
# file shipped in the pyrtdd repository (package/test/py/data/relocated-event.csv), event by event:
#   dH_m  horizontal distance between the two locations [m] (WGS84 ellipsoid, pyproj.Geod)
#   dZ_m  depth difference, new minus reference [m]
#   dT_ms origin-time difference, new minus reference [ms]
# For context it also gives how far the reference relocation moved each event away from the
# starting catalog (shiftH_m, shiftZ_m): a difference is only "small" relative to that shift.
# Events are matched by their id. The per-event table is written next to the new catalog as
# comparison_vs_reference.csv, and a summary is printed.
#
# Usage: python 03_compare_relocated_events.py <new relocated-event.csv> <reference relocated-event.csv>
#                                               <starting-event.csv>

import os
import sys

import numpy as np
import pandas as pd
from pyproj import Geod

new_file, ref_file, start_file = sys.argv[1:4]
geod = Geod(ellps="WGS84")


def read_events(path):
    df = pd.read_csv(path)
    # isotime looks like 2041-06-14T23:43:00.999274Z (microseconds, UTC). Force microsecond units:
    # pandas 3 already parses at "us" resolution, pandas 2 at "ns", so never assume the unit.
    df["t_us"] = pd.to_datetime(df["isotime"], utc=True).dt.as_unit("us").astype("int64")
    return df.set_index("id")


new = read_events(new_file)
ref = read_events(ref_file)
start = read_events(start_file)

common = ref.index.intersection(new.index)
missing = ref.index.difference(new.index)
extra = new.index.difference(ref.index)

rows = []
for ev in common:
    n, r, s = new.loc[ev], ref.loc[ev], start.loc[ev]
    _, _, dh = geod.inv(r.longitude, r.latitude, n.longitude, n.latitude)
    _, _, sh = geod.inv(s.longitude, s.latitude, r.longitude, r.latitude)
    rows.append({
        "id": ev,
        "new_relocated": str(n.get("relocated", "")).lower(),
        "ref_relocated": str(r.get("relocated", "")).lower(),
        "dH_m": dh,
        "dZ_m": (n.depth - r.depth) * 1000.0,
        "dT_ms": (n.t_us - r.t_us) / 1000.0,
        "new_finalRms_s": n.get("finalRms", np.nan),
        "ref_finalRms_s": r.get("finalRms", np.nan),
        "shiftH_m": sh,
        "shiftZ_m": (r.depth - s.depth) * 1000.0,
    })
tab = pd.DataFrame(rows)

out = os.path.join(os.path.dirname(os.path.abspath(new_file)), "comparison_vs_reference.csv")
tab.to_csv(out, index=False, float_format="%.6f")

pd.set_option("display.width", 200)
print(f"   new catalog      : {new_file}")
print(f"   reference catalog: {ref_file}")
print(f"   events compared  : {len(common)}   missing in new: {list(missing)}   extra in new: {list(extra)}")
print(f"   relocated flag in new catalog: {int((tab.new_relocated == 'true').sum())} true, "
      f"{int((tab.new_relocated != 'true').sum())} not relocated")
print(tab.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
for col, unit in [("dH_m", "m"), ("dZ_m", "m"), ("dT_ms", "ms")]:
    a = tab[col].abs()
    print(f"   |{col}|  max {a.max():.4f} {unit}   median {a.median():.4f} {unit}   (event {int(tab.id[a.idxmax()])} is the max)")
print(f"   context: the reference relocation moved events by {tab.shiftH_m.median():.0f} m (median, "
      f"max {tab.shiftH_m.max():.0f} m) horizontally and {tab.shiftZ_m.abs().median():.0f} m "
      f"(median, max {tab.shiftZ_m.abs().max():.0f} m) vertically from the starting catalog")
print(f"   per-event table written to {out}")
