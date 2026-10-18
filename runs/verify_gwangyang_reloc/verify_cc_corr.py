#!/usr/bin/env python
# verify_cc_corr.py -- CC-value correlation between rtDD (S1 / R1f) and the reference, over ALL measured triplets
# (reference dt.cc_P/ and dt.cc_S/ directories, no CC threshold), signed and absolute rtDD CC.
# WHY: the scrtdd note quotes "P |CC| r 0.76, S r 0.69", the pyrtdd note "r 0.23"; check which subset each means.
import sys, glob
import numpy as np, pandas as pd
sys.path.insert(0, "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_gwangyang_reloc")
from verify_xcorr import read_hypodd_cc, rtdd_table, RUNS, REF
meas = pd.concat([read_hypodd_cc(sorted(glob.glob(f"{REF}/dt.cc_P/*"))), read_hypodd_cc(sorted(glob.glob(f"{REF}/dt.cc_S/*")))])
for run in ["S1", "R1f"]:
    r = rtdd_table(RUNS[run])
    m = r.merge(meas, on=["e1", "e2", "station", "phase"], suffixes=("_r", "_ref"))
    for ph in "PS":
        s = m[m.phase == ph]
        print(run, ph, len(s), "signed r %.3f" % np.corrcoef(s.cc_r, s.cc_ref)[0, 1], "abs r %.3f" % np.corrcoef(s.cc_r.abs(), s.cc_ref)[0, 1])
