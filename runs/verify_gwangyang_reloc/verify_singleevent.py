#!/usr/bin/env python
# verify_singleevent.py -- single-event (leave-one-out) results vs the multi-event position of the same event.
# scrtdd SEa/SEm (final = step 2, plus step 1 and the HYPOINVERSE start) vs S1; pyrtdd R6* vs R1/R1f.
# WHY: re-derive the "median 1.7 m / 0.3 m, event 3 44 / 28 m" claims from the raw result files.
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_gwangyang_reloc")
from verify_metrics import enu_tm
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
S1 = pd.read_csv(f"{P}/runs/gwangyang/scrtdd/S1/work/reloc-event.csv").set_index("id")
start = pd.read_csv(f"{P}/data/gwangyang_11ev/inputs/rtdd_catalog/event.csv").set_index("id")
def d3(a_lat, a_lon, a_dep, b):
    A = enu_tm(a_lat, a_lon, a_dep); B = enu_tm(b.latitude.values, b.longitude.values, b.depth.values)
    return np.linalg.norm(A - B, axis=1), A - B
for mode in ["SEa", "SEm"]:
    r = pd.read_csv(f"{P}/runs/gwangyang/scrtdd/{mode}/single_event_results.csv").sort_values("event_id").set_index("event_id")
    b = S1.loc[r.index]
    fin, D = d3(r.step2_lat, r.step2_lon, r.step2_depth, b)
    fin2, _ = d3(r.reloc_latitude, r.reloc_longitude, r.reloc_depth_km, b)
    s1, _ = d3(r.step1_lat, r.step1_lon, r.step1_depth, b)
    st, _ = d3(start.loc[r.index].latitude, start.loc[r.index].longitude, start.loc[r.index].depth, b)
    no3 = r.index != 3
    print(mode, "step2 ok", int(r.step2_ok.sum()), "/", len(r), "| final(step2 cols) median %.2f max %.1f (ev %d) max w/o ev3 %.2f (ev %d)" %
          (np.median(fin), fin.max(), r.index[np.argmax(fin)], fin[no3].max(), r.index[no3][np.argmax(fin[no3])]),
          "| reloc_* cols median %.2f max %.1f" % (np.median(fin2), fin2.max()),
          "| step1 median %.1f max %.1f (ev %d) | start median %.0f max %.0f (ev %d)" % (np.median(s1), s1.max(), r.index[np.argmax(s1)], np.median(st), st.max(), r.index[np.argmax(st)]))
    print("   per event final 3-D (m):", dict(zip(r.index, np.round(fin, 2))))
    print("   horiz RMS %.1f vert RMS %.1f" % (np.sqrt(np.mean(D[:, 0]**2 + D[:, 1]**2)), np.sqrt(np.mean(D[:, 2]**2))))
