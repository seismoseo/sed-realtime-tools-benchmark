#!/usr/bin/env python
# verify_dtct_identity.py -- are rtDD's catalog travel times (input-phase pick - input-event origin of S1) identical to
# the travel times HypoDD read from the raw dt.ct (T1, T2 columns)? WHY: the comparison of cross-correlation
# differential times assumes both programs share the catalog datum.
import glob
import numpy as np, pandas as pd
from obspy import UTCDateTime
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
folder = glob.glob(f"{P}/runs/gwangyang/scrtdd/S1/work/multievent_*")[0]
ph = pd.read_csv(f"{folder}/input-phase.csv", keep_default_na=False); ev = pd.read_csv(f"{folder}/input-event.csv")
ot = {int(r.id): UTCDateTime(r.isotime) for r in ev.itertuples()}
tt = {(int(r.eventId), r.stationCode, r.type): UTCDateTime(r.isotime) - ot[int(r.eventId)] for r in ph.itertuples()}
rows = []
e1 = e2 = None
for line in open(f"{P}/data/gwangyang_11ev/reference/gwangyang_pnplus/2.HypoDD/02.dt.cc/dt.ct"):
    q = line.split()
    if line.startswith("#"):
        e1, e2 = int(q[1]) - 199999, int(q[2]) - 199999; continue
    sta = q[0][2:]; t1, t2, ph_ = float(q[1]), float(q[2]), q[4]
    rows.append((e1, e2, sta, ph_, t1 - tt[(e1, sta, ph_)], t2 - tt[(e2, sta, ph_)]))
d = pd.DataFrame(rows, columns=["e1", "e2", "sta", "ph", "d1", "d2"])
print("dt.ct lines", len(d), "max |T1 - rtDD tt| %.6f s, max |T2 - rtDD tt| %.6f s" % (d.d1.abs().max(), d.d2.abs().max()))
