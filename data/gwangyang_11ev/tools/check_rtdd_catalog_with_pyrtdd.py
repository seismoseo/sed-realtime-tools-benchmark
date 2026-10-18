#!/usr/bin/env python
# check_rtdd_catalog_with_pyrtdd.py
#
# Loads the rtDD catalog triplet written by make_rtdd_catalog.py with pyrtdd's own C++ reader
# (pyrtdd.hdd.Catalog = scrtdd libhdd, the same parser scrtdd uses) and checks that every event,
# phase and station comes back exactly as written. It also shows, on a throw-away copy, what the
# reader does with the 14-digit KMA ids (it stores ids in a 32-bit unsigned integer).
#
# Run with the pyrtdd environment (needs pyrtdd installed, step 03):
#     /home/msseo/miniforge3/envs/pyrtdd/bin/python check_rtdd_catalog_with_pyrtdd.py
# Writes nothing permanent (temporary files live in inputs/checks/ and are removed at the end).

import datetime
import os
import sys
import tempfile

import numpy as np
import pandas as pd
from obspy import UTCDateTime
from pyrtdd.hdd import Catalog

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
CAT = f"{PROJECT}/data/gwangyang_11ev/inputs/rtdd_catalog"
CHECKS = f"{PROJECT}/data/gwangyang_11ev/inputs/checks"


def to_utc(td):
    # pyrtdd returns times as datetime.timedelta since 1970-01-01
    return UTCDateTime(1970, 1, 1) + td.days * 86400 + td.seconds + td.microseconds / 1e6


def check(event_file):
    sta = pd.read_csv(f"{CAT}/station.csv", dtype=str, keep_default_na=False)
    ev = pd.read_csv(f"{CAT}/{event_file}", dtype=str, keep_default_na=False)
    ph = pd.read_csv(f"{CAT}/phase.csv", dtype=str, keep_default_na=False)
    c = Catalog(f"{CAT}/station.csv", f"{CAT}/{event_file}", f"{CAT}/phase.csv")
    E, P, S = c.getEvents(), c.getPhases(), c.getStations()
    n_ph = sum(len(v) for v in P.values())
    errors = []
    if (len(E), n_ph, len(S)) != (len(ev), len(ph), len(sta)):
        errors.append(f"counts loaded {(len(E), n_ph, len(S))} vs written {(len(ev), len(ph), len(sta))}")
    for r in ev.itertuples():
        e = E[int(r.id)]
        if abs(to_utc(e.time) - UTCDateTime(r.isotime)) > 1e-6 or abs(e.latitude - float(r.latitude)) > 1e-9 \
                or abs(e.longitude - float(r.longitude)) > 1e-9 or abs(e.depth - float(r.depth)) > 1e-9 \
                or abs(e.magnitude - float(r.magnitude)) > 1e-9:
            errors.append(f"event {r.id} differs after loading")
    loaded = {(p.eventId, p.stationCode, p.type): p for v in P.values() for p in v}
    for r in ph.itertuples():
        p = loaded.get((int(r.eventId), r.stationCode, r.type))
        if p is None:
            errors.append(f"phase {r.eventId} {r.stationCode} {r.type} not loaded")
            continue
        if abs(to_utc(p.time) - UTCDateTime(r.isotime)) > 1e-6 or p.channelCode != r.channelCode \
                or p.locationCode != r.locationCode or p.networkCode != r.networkCode \
                or not (np.isnan(p.lowerUncertainty) and np.isnan(p.upperUncertainty)):
            errors.append(f"phase {r.eventId} {r.stationCode} {r.type} differs after loading")
    for r in sta.itertuples():
        s = S[f"{r.networkCode}.{r.stationCode}.{r.locationCode}"]
        if abs(s.latitude - float(r.latitude)) > 1e-9 or abs(s.longitude - float(r.longitude)) > 1e-9 \
                or abs(s.elevation - float(r.elevation)) > 1e-9:
            errors.append(f"station {r.stationCode} differs after loading")
    print(f"[pyrtdd] {event_file}: loaded {len(E)} events, {n_ph} phases, {len(S)} stations; "
          f"value mismatches: {len(errors)}")
    for e in errors[:20]:
        print("   ", e)
    return len(errors)


def kma_id_demo():
    # what happens with the 14-digit KMA ids (temporary copy, removed afterwards)
    mp = pd.read_csv(f"{CAT}/event_id_map.csv", dtype={"kma_id": str})
    rt2kma = dict(zip(mp.rtdd_id.astype(str), mp.kma_id))
    with tempfile.TemporaryDirectory(dir=CHECKS, prefix="tmp_kma_id_demo_") as td:
        ev = pd.read_csv(f"{CAT}/event.csv", dtype=str, keep_default_na=False)
        ph = pd.read_csv(f"{CAT}/phase.csv", dtype=str, keep_default_na=False)
        ev["id"] = ev.id.map(rt2kma)
        ph["eventId"] = ph.eventId.map(rt2kma)
        ev.to_csv(f"{td}/event.csv", index=False, lineterminator="\n")
        ph.to_csv(f"{td}/phase.csv", index=False, lineterminator="\n")
        c = Catalog(f"{CAT}/station.csv", f"{td}/event.csv", f"{td}/phase.csv")
        got = sorted(c.getEvents().keys())
    want = sorted(int(k) for k in mp.kma_id)
    wrapped = sorted(w % 2**32 for w in want)
    print(f"[pyrtdd] with KMA ids the reader stores {got[:3]} ... instead of {want[:3]} ... "
          f"(stored ids == KMA id mod 2^32: {got == wrapped}) -> ids 1..{len(mp)} are required")


if __name__ == "__main__":
    n = check("event.csv") + check("event_centroid_start.csv")
    kma_id_demo()
    print("[problems] none" if n == 0 else f"[PROBLEMS] {n} mismatches")
    sys.exit(1 if n else 0)
