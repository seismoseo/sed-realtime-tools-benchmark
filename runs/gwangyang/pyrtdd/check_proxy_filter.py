#!/usr/bin/env python
# check_proxy_filter.py
#
# WHAT: establishes which band-pass filter pyrtdd actually applies for each candidate filter string.
#
# WHY: pyrtdd's obspy waveform proxy (pyrtdd/obspy/waveform.py, _ObspyProxyBase.filter) splits the rtDD
# filter string "<type>;key=val;..." and converts EVERY value with float() before calling
# obspy Trace.filter(type, **kwargs). The reference cross-correlation (core/xcorr.py) used
# obspy bandpass(freqmin=5, freqmax=20, corners=4, zerophase=True). Whether "zerophase" survives the
# float() conversion decides whether pyrtdd can mimic the reference filter. Strings tested:
#   A  bandpass;freqmin=5;freqmax=20;corners=4                  (the shared setting)
#   B  bandpass;freqmin=5;freqmax=20;corners=4;zerophase=1      (float 1.0 is truthy)
#   C  bandpass;freqmin=5;freqmax=20;corners=4;zerophase=0      (float 0.0 is falsy)
#   D  bandpass;freqmin=5;freqmax=20;corners=4;zerophase=True   (float('True') should fail)
# Two levels:
#   1. the proxy's filter() called from Python on a pyrtdd.hdd.Trace (the exact method the C++ calls);
#   2. end to end through libhdd: DD.dumpWaveforms() is not bound in pyrtdd, so a recording subclass of
#      the same ObspyClientProxy captures every filter() call libhdd makes during a tiny cross-correlation
#      relocation (events 3 and 4, station KS.GWYB, P on Z and S on L2): the string received, the sampling
#      rate at that moment (resampleFreq 0 and 1000) and the data before/after, compared with obspy.
#
# Usage (env pyrtdd):  python -I check_proxy_filter.py            (dry run: prints the plan)
#                      python -I check_proxy_filter.py --apply    (runs; writes checks/proxy_filter_check.json)
# Writes only inside runs/gwangyang/pyrtdd/checks/.

import argparse
import json
import os
import shutil
import sys

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
CAT = f"{DATA}/inputs/rtdd_catalog"
SDS = f"{DATA}/inputs/sds"
INVENTORY = f"{DATA}/inputs/stations_rtdd.xml"
OUT = f"{PROJECT}/runs/gwangyang/pyrtdd/checks"
EVENT_ID, NET, STA = 3, "KS", "GWYB"      # ML 2.2, closest station (7 km): clear P and S
FILTERS = {
    "A_shared_causal": "bandpass;freqmin=5;freqmax=20;corners=4",
    "B_zerophase_1": "bandpass;freqmin=5;freqmax=20;corners=4;zerophase=1",
    "C_zerophase_0": "bandpass;freqmin=5;freqmax=20;corners=4;zerophase=0",
    "D_zerophase_True": "bandpass;freqmin=5;freqmax=20;corners=4;zerophase=True",
}
EXTRA_TRACE_LEN = 1.0       # rtDD default cfg.wfFilter.extraTraceLen (s)


def rel_diff(a, b):
    """max |a-b| / max |b| (0 = identical)."""
    return float(np.max(np.abs(a - b)) / np.max(np.abs(b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="run the checks (default: dry run)")
    args = ap.parse_args()
    if not args.apply:
        print("[dry run] would test filter strings:", json.dumps(FILTERS, indent=1))
        print(f"[dry run] level 1: proxy.filter() on a 100 Hz trace of {NET}.{STA} event {EVENT_ID}")
        print(f"[dry run] level 2: recording proxy during a 2-event xcorr relocation; results in {OUT}")
        return

    import obspy
    from obspy.clients.filesystem.sds import Client as SDSClient
    from pyrtdd.hdd import Catalog, Config, DD, Homogeneous, XcorrOptions, Logger
    from pyrtdd.obspy.waveform import ObspyClientProxy, _obspy_trace_to_hdd

    Logger.setLevel(Logger.Level.warning)
    PT = Catalog.Phase.Type
    os.makedirs(OUT, exist_ok=True)
    inv = obspy.read_inventory(INVENTORY)
    client = SDSClient(SDS)
    ph = pd.read_csv(f"{CAT}/phase.csv", dtype=str, keep_default_na=False)
    ev = pd.read_csv(f"{CAT}/event.csv")
    sel = ph[(ph.eventId.astype(int) == EVENT_ID) & (ph.stationCode == STA)]
    p_time = obspy.UTCDateTime(sel[sel.type == "P"].isotime.iloc[0])
    s_time = obspy.UTCDateTime(sel[sel.type == "S"].isotime.iloc[0])
    cha_root = sel.channelCode.iloc[0][:2]
    res = {"event_id": EVENT_ID, "station": f"{NET}.{STA}", "channel_root": cha_root,
           "p_pick": str(p_time), "s_pick": str(s_time), "level1": {}, "level2": {}, "level2_1000Hz": {}}

    # ---------------------------------------------------------------- level 1: proxy.filter() directly
    proxy = ObspyClientProxy(client, inv, guess_zne=False)
    raw = client.get_waveforms(NET, STA, "", cha_root + "Z", p_time - 5, p_time + 5).merge(method=1)[0]
    raw.data = raw.data.astype(np.float64)
    raw.data -= raw.data.mean()
    ref_causal = raw.copy().filter("bandpass", freqmin=5, freqmax=20, corners=4, zerophase=False).data
    ref_zero = raw.copy().filter("bandpass", freqmin=5, freqmax=20, corners=4, zerophase=True).data
    for name, fstr in FILTERS.items():
        tr = _obspy_trace_to_hdd(raw)
        try:
            proxy.filter(tr, fstr)
            out = np.array(tr.data(), copy=True)
            res["level1"][name] = {"filterStr": fstr, "error": None,
                                   "rel_diff_vs_obspy_causal": rel_diff(out, ref_causal),
                                   "rel_diff_vs_obspy_zerophase": rel_diff(out, ref_zero)}
        except Exception as e:      # report, do not hide
            res["level1"][name] = {"filterStr": fstr, "error": f"{type(e).__name__}: {e}"}
    res["level1"]["note"] = "rel_diff = max|proxy - obspy| / max|obspy|; 0 means identical"

    # ---------------------------------------------------------------- level 2: through libhdd
    # DD.dumpWaveforms() is not bound in pyrtdd 0.0.1, so a recording proxy (subclass of the same
    # ObspyClientProxy) captures every filter() call libhdd makes during a tiny cross-correlation
    # relocation (events 3 and 4, station GWYB only): the filter string it receives, the sampling rate of
    # the trace at that moment (1000 Hz proves resampling happened first) and the data before/after.
    mini = f"{OUT}/mini_catalog"
    os.makedirs(mini, exist_ok=True)
    shutil.copyfile(f"{CAT}/station.csv", f"{mini}/station.csv")
    ev[ev.id.isin([3, 4])].to_csv(f"{mini}/event.csv", index=False)
    ph[ph.eventId.astype(int).isin([3, 4]) & (ph.stationCode == STA)].to_csv(f"{mini}/phase.csv", index=False)
    from pyrtdd.hdd import ClusteringOptions, SolverOptions, XCorrCache

    class RecordingProxy(ObspyClientProxy):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.calls = []

        def filter(self, trace, filterStr):
            before = np.array(trace.data(), copy=True)
            super().filter(trace, filterStr)
            self.calls.append((filterStr, float(trace.samplingFrequency), trace.channelCode, before,
                               np.array(trace.data(), copy=True)))

    xo = XcorrOptions()
    xo.enable = True
    for t in (PT.P, PT.S):              # like_reference windows: pick -0.5 .. +0.5 s, no scaling
        x = xo.phase[t]
        x.startOffset, x.endOffset, x.winScaling, x.maxDelay, x.minCoef = -0.5, 0.5, 0.0, 0.5, 0.7
        x.components = ["Z"] if t == PT.P else ["L2"]
        xo.phase[t] = x
    co = ClusteringOptions()
    co.numEllipsoids, co.minNumNeigh, co.minNumPhases, co.maxNumNeigh, co.maxNeighbourDist = 0, 1, 1, 0, 10.0
    so = SolverOptions()
    so.absLocConstraintStart = so.absLocConstraintEnd = 0.0
    so.algoIterations = 1
    for name, fstr in FILTERS.items():
        for rs in (0.0, 1000.0):
            if not name.startswith(("A", "B")) and rs > 0:
                continue
            key = "level2" if rs == 0 else "level2_1000Hz"
            entry = {"filterStr": fstr, "resampleFreq": rs}
            cfg = Config()
            cfg.validPphases, cfg.validSphases = ["P"], ["S"]
            cfg.wfFilter.filterStr, cfg.wfFilter.resampleFreq, cfg.wfFilter.extraTraceLen = fstr, rs, EXTRA_TRACE_LEN
            rp = RecordingProxy(client, inv, guess_zne=False)
            cat = Catalog(f"{mini}/station.csv", f"{mini}/event.csv", f"{mini}/phase.csv")
            dd = DD(cat, cfg, Homogeneous(5.98, 3.4566), rp)
            xc = XCorrCache()
            try:
                dd.relocateMultiEvents(dd.findClusters(co), xc, xo, so, False, "")
            except Exception as ex:
                entry["relocation_error"] = f"{type(ex).__name__}: {ex}"
            xc.writeToFile(cat, f"{OUT}/xcorr_{name}_rs{int(rs)}.csv")
            entry["n_filter_calls"] = len(rp.calls)
            entry["xcorr_rows"] = pd.read_csv(f"{OUT}/xcorr_{name}_rs{int(rs)}.csv").to_dict("records")
            entry["calls"] = []
            for fs_str, fs, chan, before, after in rp.calls:
                tmp = obspy.Trace(data=before.copy(), header={"sampling_rate": fs})
                c = {"filterStr_received": fs_str, "fs_at_filter_Hz": fs, "channel": chan, "npts": int(len(before)),
                     "rel_diff_vs_obspy_causal": rel_diff(after, tmp.copy().filter(
                         "bandpass", freqmin=5, freqmax=20, corners=4, zerophase=False).data),
                     "rel_diff_vs_obspy_zerophase": rel_diff(after, tmp.copy().filter(
                         "bandpass", freqmin=5, freqmax=20, corners=4, zerophase=True).data)}
                entry["calls"].append(c)
            if not rp.calls:
                entry["note"] = "libhdd made no filter() call (filtering failed before or traces unavailable)"
            res[key][name] = entry

    res["versions"] = {"obspy": obspy.__version__, "numpy": np.__version__,
                       "scipy": __import__("scipy").__version__, "python": sys.version.split()[0]}
    with open(f"{OUT}/proxy_filter_check.json", "w") as fo:
        json.dump(res, fo, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
