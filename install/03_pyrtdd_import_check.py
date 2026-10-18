# 03_pyrtdd_import_check.py -- used by 03_install_pyrtdd.sh (step importcheck).
#
# Meant to run in a brand-new shell in which only "conda activate pyrtdd" was done, from a folder
# that is not the pyrtdd repository. It shows that the installed package works on its own:
#  1. where pyrtdd is imported from, and that no source or build folder is on sys.path;
#  2. one travel-time computation with the README's homogeneous model (Vp 5.8, Vs 3.36 km/s), from the
#     Gwangyang ML 2.2 hypocenter (event 20210827220322, HypoDD dt.cc result in
#     data/gwangyang_11ev/reference/gwangyang_pnplus/2.HypoDD/02.dt.cc/final_locations.csv) to station
#     KS.BAU (station_table/used_stations_100km.csv), checked against an independent straight-ray
#     calculation written here (great-circle distance + vertical distance, divided by the velocity);
#  3. the list of names that pyrtdd.hdd exposes.
#
# Usage: python 03_pyrtdd_import_check.py

import math
import sys

import pyrtdd
import pyrtdd.hdd
from pyrtdd.obspy import catalog, waveform  # noqa: F401  (import test of the obspy helpers)
from pyrtdd.hdd import Homogeneous

print("python       :", sys.executable)
print("pyrtdd from  :", pyrtdd.__file__)
print("hdd_ext from :", pyrtdd.hdd.hdd_ext.__file__)
print("obspy helpers:", catalog.__file__, waveform.__file__)
print("sys.path     :", sys.path)
suspicious = [p for p in sys.path if "software/src" in p or "_skbuild" in p]
print("source/build folders on sys.path:", suspicious if suspicious else "none")

EV_LAT, EV_LON, EV_DEPTH_KM = 34.99982, 127.72852, 13.93   # Gwangyang ML 2.2, HypoDD dt.cc
ST_LAT, ST_LON, ST_ELEV_M = 35.1027, 127.5968, 562.0       # KS.BAU
VP, VS = 5.8, 3.36

ttt = Homogeneous(VP, VS)
tp = ttt.compute(EV_LAT, EV_LON, EV_DEPTH_KM, ST_LAT, ST_LON, ST_ELEV_M, "P")
ts = ttt.compute(EV_LAT, EV_LON, EV_DEPTH_KM, ST_LAT, ST_LON, ST_ELEV_M, "S")
tt_all, azi, dip, dtdd, dtdh = ttt.computeAll(EV_LAT, EV_LON, EV_DEPTH_KM, ST_LAT, ST_LON, ST_ELEV_M, "P")
print(f"pyrtdd Homogeneous({VP}, {VS}): P {tp:.6f} s   S {ts:.6f} s")
print(f"  computeAll(P): travelTime {tt_all:.6f} s, takeOffAzimuth {azi:.3f} deg, "
      f"takeOffDip {dip:.3f} deg (0=down, 180=up), dtdd {dtdd:.4f} s/deg, dtdh {dtdh:.5f} s/km")

# Independent check: straight ray in a homogeneous medium. Horizontal part = great-circle distance
# on a sphere (mean Earth radius minus the mean depth of the two ray ends, as libhdd does);
# vertical part = event depth + station elevation.
R_KM = 6371.00877141506 - (EV_DEPTH_KM - ST_ELEV_M / 1000.0) / 2.0
p1, p2 = math.radians(EV_LAT), math.radians(ST_LAT)
dphi, dlam = p2 - p1, math.radians(ST_LON - EV_LON)
a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
h_km = 2 * R_KM * math.asin(math.sqrt(a))
v_km = EV_DEPTH_KM + ST_ELEV_M / 1000.0
d_km = math.hypot(h_km, v_km)
print(f"independent : epicentral {h_km:.4f} km, vertical {v_km:.3f} km, ray {d_km:.4f} km -> "
      f"P {d_km / VP:.6f} s   S {d_km / VS:.6f} s")
print(f"difference  : P {abs(tp - d_km / VP) * 1e6:.3f} us   S {abs(ts - d_km / VS) * 1e6:.3f} us   "
      f"computeAll-vs-compute {abs(tt_all - tp) * 1e6:.3f} us")

print("dir(pyrtdd.hdd):", [n for n in dir(pyrtdd.hdd) if not n.startswith("__")])
