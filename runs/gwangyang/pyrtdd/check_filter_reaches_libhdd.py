#!/usr/bin/env python
# check_filter_reaches_libhdd.py
#
# WHAT: tests whether the waveform filtering done in a Python WaveformProxy.filter() reaches the trace
# that libhdd (pyrtdd's C++ engine) cross-correlates.
#
# WHY: check_proxy_filter.py found that a causal and a zero-phase 5-20 Hz band-pass give bit-identical
# cross-correlation coefficients and lags. pyrtdd's trampoline (package/src/pyrtdd/hdd/proxy_ext.cpp)
# forwards `Trace &trace` with PYBIND11_OVERRIDE_PURE; pybind11 converts lvalue-reference arguments of
# Python overrides with a copy policy by default, so the Python filter() may mutate a COPY.
# Test: the same 2-event / 1-station cross-correlation (events 3 and 4, KS.GWYB, P on Z, S on L2,
# window -0.5/+0.5 s, maxDelay 0.5 s, 100 Hz, no resampling) with five proxies/filters:
#   none      filterStr ""                       (libhdd never calls filter())
#   bp5_20    filterStr bandpass 5-20 Hz         (stock ObspyClientProxy)
#   lp1       filterStr lowpass 1 Hz             (drastically different waveform)
#   zeroing   a subclass whose filter() sets every sample to 0 (CC must become invalid if it reaches libhdd)
#   scaled    a subclass whose filter() multiplies by -1 (NOT diagnostic: negating both traces leaves their CC unchanged;
#             kept for completeness, see docs/results/07 section 1a)
# If all five give the same coefficient and lag, filter() has no effect on libhdd's data.
# Usage (env pyrtdd): python -I check_filter_reaches_libhdd.py [--apply]
import argparse, json, os, shutil
import numpy as np
import pandas as pd

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
CAT = f"{DATA}/inputs/rtdd_catalog"
OUT = f"{PROJECT}/runs/gwangyang/pyrtdd/checks/filter_effect_test"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    if not ap.parse_args().apply:
        print("[dry run] would run 5 two-event cross-correlations into", OUT)
        return
    import obspy
    from obspy.clients.filesystem.sds import Client as SDSClient
    from pyrtdd.hdd import Catalog, Config, DD, Homogeneous, XcorrOptions, ClusteringOptions, SolverOptions, XCorrCache, Logger
    from pyrtdd.obspy.waveform import ObspyClientProxy
    Logger.setLevel(Logger.Level.warning)
    PT = Catalog.Phase.Type
    os.makedirs(OUT, exist_ok=True)
    ph = pd.read_csv(f"{CAT}/phase.csv", dtype=str, keep_default_na=False)
    ev = pd.read_csv(f"{CAT}/event.csv")
    shutil.copyfile(f"{CAT}/station.csv", f"{OUT}/station.csv")
    ev[ev.id.isin([3, 4])].to_csv(f"{OUT}/event.csv", index=False)
    ph[ph.eventId.astype(int).isin([3, 4]) & (ph.stationCode == "GWYB")].to_csv(f"{OUT}/phase.csv", index=False)
    inv = obspy.read_inventory(f"{DATA}/inputs/stations_rtdd.xml")
    client = SDSClient(f"{DATA}/inputs/sds")

    class Zeroing(ObspyClientProxy):
        def filter(self, trace, filterStr):
            trace.data()[:] = 0.0

    class Negating(ObspyClientProxy):
        def filter(self, trace, filterStr):
            trace.data()[:] = -np.array(trace.data())

    cases = {"none": (ObspyClientProxy, ""), "bp5_20": (ObspyClientProxy, "bandpass;freqmin=5;freqmax=20;corners=4"),
             "lp1": (ObspyClientProxy, "lowpass;freq=1;corners=4"), "zeroing": (Zeroing, "anything"),
             "negating": (Negating, "anything")}
    xo = XcorrOptions(); xo.enable = True
    for t in (PT.P, PT.S):
        x = xo.phase[t]
        x.startOffset, x.endOffset, x.winScaling, x.maxDelay, x.minCoef = -0.5, 0.5, 0.0, 0.5, 0.7
        x.components = ["Z"] if t == PT.P else ["L2"]
        xo.phase[t] = x
    co = ClusteringOptions()
    co.numEllipsoids, co.minNumNeigh, co.minNumPhases, co.maxNumNeigh, co.maxNeighbourDist = 0, 1, 1, 0, 10.0
    so = SolverOptions(); so.absLocConstraintStart = so.absLocConstraintEnd = 0.0; so.algoIterations = 1
    res = {}
    for name, (cls, fstr) in cases.items():
        cfg = Config(); cfg.validPphases, cfg.validSphases = ["P"], ["S"]
        cfg.wfFilter.filterStr, cfg.wfFilter.resampleFreq = fstr, 0.0
        cat = Catalog(f"{OUT}/station.csv", f"{OUT}/event.csv", f"{OUT}/phase.csv")
        dd = DD(cat, cfg, Homogeneous(5.98, 3.4566), cls(client, inv, guess_zne=False))
        xc = XCorrCache()
        dd.relocateMultiEvents(dd.findClusters(co), xc, xo, so, False, "")
        xc.writeToFile(cat, f"{OUT}/xcorr_{name}.csv")
        res[name] = pd.read_csv(f"{OUT}/xcorr_{name}.csv")[["phaseType", "valid", "coefficient", "lag"]].to_dict("records")
    json.dump(res, open(f"{OUT}/filter_effect_test.json", "w"), indent=1)
    for k, v in res.items():
        print(f"{k:9s}", v)


if __name__ == "__main__":
    main()
