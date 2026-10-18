#!/usr/bin/env python
# run_pyrtdd_gwangyang.py
#
# WHAT: pyrtdd (scrtdd libhdd v2.0.9) double-difference relocations of the 11 Gwangyang events, one named
# run per setting combination (see RUNS below). Each run writes, in runs/gwangyang/pyrtdd/<run>/:
#   relocated-{station,event,phase}.csv   the relocated catalog (rtDD CSV format)
#   processing/                           saveProcessing output of libhdd (logs, pairs, initial/final DDs, xcorr)
#   clusters/cluster_<i>.csv              the clusters given to relocateMultiEvents
#   xcorr_cache.csv                       the XCorrCache (cross-correlation runs)
#   inputs/                               the exact catalog files the run read
#   options.json                          EVERY option value actually used, read back from the libhdd objects
#   run_info.json                         wall time, status, errors, waveform/filter call counters
#   console.log                           everything libhdd printed (file descriptor 2 is redirected)
#
# WHY these runs (task "PYRTDD RELOCATIONS", shared settings in docs/results/07_gwangyang_pyrtdd.md):
#   R0  catalog only, clustering + solver 'hypodd_like', HypoDD ISTART=1 centroid start (analogue of 01.dt.ct)
#   R1  R0 + cross-correlation 'like_reference'                                       (analogue of 02.dt.cc)
#   R2  rtDD default solver + default XcorrOptions (same waveform filter), 'hypodd_like' clustering
#   R3a/R3b  R0/R1 started from the HYPOINVERSE locations (event.csv)
#   R4  R1 without the 17 picks that are > 1 s off the kim1983 grid times
#   R5  R1 with Homogeneous(5.98, 3.4566) instead of the NonLinLoc kim1983 grids
#   R6  leave-one-out single-event relocation against R1's catalog without the event
#
# IMPORTANT (found by check_filter_reaches_libhdd.py, 2026-10-17): with stock pyrtdd d122c3a the waveform
# band-pass NEVER reaches the traces libhdd cross-correlates. libhdd calls the Python proxy's filter(trace,
# filterStr) through a pybind11 trampoline (package/src/pyrtdd/hdd/proxy_ext.cpp, PYBIND11_OVERRIDE_PURE with
# `Trace &trace`); the Python side receives a copy, so its in-place filtering is lost. Even a filter() that
# zeroes the samples leaves every CC and lag unchanged. libhdd's own C++ steps (demean, 1000 Hz resampling,
# L2) do work. Therefore every cross-correlation run exists in two flavours:
#   proxy 'stock'       pyrtdd.obspy.waveform.ObspyClientProxy exactly as shipped (cfg.wfFilter.filterStr is
#                       set as requested but has NO effect: traces are demeaned + resampled, not band-passed);
#                       waveform disk cache enabled (raw traces) as the task asks.
#   proxy 'preprocess'  a subclass of the same proxy (PreprocessingSDSProxy below) that performs, inside
#                       loadTrace(), exactly the processing libhdd's BasicProcessor would do if the filter worked:
#                       demean -> libhdd's own Hann-windowed sinc resampler (numpy port of waveform.cpp
#                       resample()) -> obspy Trace.filter() with the same arguments as the stock proxy;
#                       libhdd's resampleFreq/filterStr are then set to 0/"" (libhdd only demeans again, which
#                       Pearson CC ignores). It receives exactly the window libhdd would process (window +-
#                       extraTraceLen) because the disk cache is NOT enabled for these runs (a disk cache would
#                       store processed traces and hand the proxy a 10 s window instead).
#   The port of the resampler is validated by run V1 (preprocess proxy, filter off) which must reproduce the
#   stock V0 cross-correlation results (stock V0 = R1 without disk cache: resampled, unfiltered).
# SECOND ISSUE (single-event mode only, found in R6): libhdd's BatchLoader::get, which serves the waveforms of the
# event being relocated, accepts a trace only if it CONTAINS the requested window. obspy trims to the nearest
# sample and the KMA samples sit a few ms off the request grid (e.g. x.xx3096 s), so every trace returned by the
# stock proxy's get_waveforms_bulk() misses the window by a fraction of a sample and libhdd skips every
# single-event cross-correlation ("no waveform data for phase"). Multi-event mode is not affected (its loaders
# slice an inner window). Runs with pad_batch_s > 0 fetch each batch request 0.05 s wider on both sides
# (R6p/R6tp: stock processing otherwise; R6f/R6tf: preprocess proxy); R6/R6t keep the stock behaviour.
#
# Usage (env pyrtdd; nice; one process; CPU only):
#   python -I run_pyrtdd_gwangyang.py                    dry run: prints every run's resolved settings
#   python -I run_pyrtdd_gwangyang.py --apply            runs every run (in the order of RUNS)
#   python -I run_pyrtdd_gwangyang.py --apply --runs R0_catalog_only_hypodd_like,R1_...   selected runs
#   --force   re-run a run whose folder already has run_info.json with status "ok"
# Summary lines go to stdout and to logs/07_gwangyang_pyrtdd_<YYYYMMDD>.log.

import argparse
import contextlib
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np
import pandas as pd

# ============================================================================= parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
CATDIR = f"{DATA}/inputs/rtdd_catalog"
STATION_CSV = f"{CATDIR}/station.csv"
EVENT_HYPOINVERSE_CSV = f"{CATDIR}/event.csv"                 # HYPOINVERSE kim1983 locations
EVENT_CENTROID_CSV = f"{CATDIR}/event_centroid_start.csv"     # HypoDD ISTART=1: all events at the centroid
PHASE_CSV = f"{CATDIR}/phase.csv"                             # the 763 picks ph2dt used (no uncertainties)
VALIDATION_PICKS_CSV = f"{DATA}/inputs/nll_kim1983/validation_picks.csv"
OUTLIER_LOG = f"{PROJECT}/runs/verify_inputs/v3d_outliers.log"
OUTLIER_THRESHOLD_S = 1.0          # |observed - grid| travel time above which a pick is called an outlier (R4)
EVENT_ID_MAP = f"{DATA}/reference_tables/event_id_map.csv"
NLL_GRID_PATH = f"{DATA}/inputs/nll_kim1983/time"
NLL_GRID_MODEL = "kim1983"
NLL_MAX_SEARCH_DISTANCE_M = 0.1    # grids were made at station.csv coordinates; prep found all 108 at 0.1 m
HOMOGENEOUS_VP, HOMOGENEOUS_VS = 5.98, 3.4566   # kim1983 source layer; Vs = 5.98/1.73 as in HypoDD (R5)
SDS = f"{DATA}/inputs/sds"
INVENTORY_XML = f"{DATA}/inputs/stations_rtdd.xml"  # station.csv coordinates; nominal orientations 0/90
OUTROOT = f"{PROJECT}/runs/gwangyang/pyrtdd"
WFCACHE = f"{OUTROOT}/wfcache"     # raw-waveform disk cache shared by the 'stock' runs (keyed by stream+window)
DISK_TRACE_MIN_LEN = 10.0          # rtDD default (s of raw data cached around each pick)
PAD_BATCH_S = 0.05                 # single-event batch loads: fetch +- 0.05 s more so the trace contains the window
LOGFILE = f"{PROJECT}/logs/07_gwangyang_pyrtdd_{_dt.date.today():%Y%m%d}.log"
PYRTDD_SRC = f"{PROJECT}/software/src/pyrtdd"

# ----------------------------------------------------------------------------- named settings
# Clustering 'hypodd_like' mirrors ph2dt (MAXSEP 10 km, MAXNGH 200 = no limit here, MINLNK 1, MINOBS 1).
CLUSTERING = {
    "hypodd_like": dict(numEllipsoids=0, maxNeighbourDist=10.0, minNumNeigh=1, maxNumNeigh=0, minNumPhases=1,
                        maxNumPhases=0, minEvStaToInterEvRatio=3.0, minEvStaDist=0.0, maxEvStaDist=-1.0),
    # Single-event (real-time) mode: scrtdd.xml singleEvent / eventFiltering / phaseFiltering defaults
    # (minNumNeighbours 4, maxNumNeighbours 80, maxNeighbourDistance 5 km, numEllipsoids 5, minNumPhases 8,
    # minStationToEventPairDistRatio 3). libhdd's ClusteringOptions() defaults differ only in minNumNeigh (8)
    # and maxNumNeigh (40); with 10 background events neither binds unless < 8 neighbours qualify.
    "single_event_scrtdd_defaults": dict(numEllipsoids=5, maxNeighbourDist=5.0, minNumNeigh=4, maxNumNeigh=80,
                                         minNumPhases=8, maxNumPhases=0, minEvStaToInterEvRatio=3.0,
                                         minEvStaDist=0.0, maxEvStaDist=-1.0),
}
# Solver 'hypodd_like': pure double difference (HypoDD's SVD keeps the centroid fixed and has no absolute
# constraint) -> absLocConstraint 0; everything else stays at the rtDD default (reported in options.json).
SOLVER = {
    "hypodd_like": dict(type="LSMR", absLocConstraintStart=0.0, absLocConstraintEnd=0.0, dampingFactorStart=0.01,
                        dampingFactorEnd=0.01, downWeightingByResidualStart=10.0, downWeightingByResidualEnd=5.0,
                        usePickUncertainties=False),
    "rtdd_default": dict(),
}
# Cross-correlation 'like_reference': reference window -0.5/+0.5 s around the pick, no travel-time scaling,
# CC >= 0.7, P on Z, S on L2 (orientation-free; the reference took the better of raw N and E).
XC_LIKE_REF = dict(minCoef=0.7, startOffset=-0.5, endOffset=0.5, winScaling=0.0, maxDelay=0.5)
XCORR = {
    "like_reference": dict(enable=True, minEvStaDist=0.0, maxEvStaDist=-1.0, maxInterEvDist=-1.0,
                           P=dict(XC_LIKE_REF, components=["Z"]), S=dict(XC_LIKE_REF, components=["L2"])),
    "xcorr_default": dict(enable=True),      # XcorrOptions() defaults, only switched on
    "off": None,
}
# Waveform preprocessing (cfg.wfFilter). The stock proxy maps filterStr to obspy Trace.filter(kind, **floats).
WFFILTER = {
    "bw5_20_causal_1000Hz": dict(filterStr="bandpass;freqmin=5;freqmax=20;corners=4", resampleFreq=1000.0,
                                 extraTraceLen=1.0),
    "bw5_20_zerophase_1000Hz": dict(filterStr="bandpass;freqmin=5;freqmax=20;corners=4;zerophase=1",
                                    resampleFreq=1000.0, extraTraceLen=1.0),
    "none_1000Hz": dict(filterStr="", resampleFreq=1000.0, extraTraceLen=1.0),
    "none": dict(filterStr="", resampleFreq=0.0, extraTraceLen=1.0),
}

LIKE_REF = dict(clustering="hypodd_like", solver="hypodd_like", xcorr="like_reference",
                wffilter="bw5_20_causal_1000Hz", ttt="nll", start="centroid", phases="all", mode="multi")
CAT_ONLY = dict(LIKE_REF, xcorr="off", wffilter="none", proxy="none")

# The runs, in execution order. 'proxy': stock | preprocess | none. Every option not named stays at its
# libhdd default and is still written to options.json.
RUNS = {
    "R0_catalog_only_hypodd_like": dict(CAT_ONLY),
    "R1_xcorr_like_reference_hypodd_like": dict(LIKE_REF, proxy="stock"),
    "V0_stock_no_disk_cache": dict(LIKE_REF, proxy="stock", disk_cache=False,
                                   note="R1 without the waveform disk cache: shows the cache does not change results "
                                        "and gives V1 the identical input windows"),
    "V1_port_check_preprocess_nofilter": dict(LIKE_REF, proxy="preprocess", wffilter="none_1000Hz",
                                              note="validation of the resampler port: must equal V0 (stock V0/R1 are "
                                                   "resampled but unfiltered)"),
    "R1f_xcorr_like_reference_hypodd_like_filtered": dict(LIKE_REF, proxy="preprocess"),
    "R1fz_xcorr_like_reference_hypodd_like_filtered_zerophase": dict(LIKE_REF, proxy="preprocess",
                                                                     wffilter="bw5_20_zerophase_1000Hz"),
    "R2_xcorr_default_rtdd_default": dict(LIKE_REF, xcorr="xcorr_default", solver="rtdd_default", proxy="stock"),
    "R2f_xcorr_default_rtdd_default_filtered": dict(LIKE_REF, xcorr="xcorr_default", solver="rtdd_default",
                                                    proxy="preprocess"),
    "R3a_catalog_only_hypodd_like_hypoinverse_start": dict(CAT_ONLY, start="hypoinverse"),
    "R3b_xcorr_like_reference_hypodd_like_hypoinverse_start": dict(LIKE_REF, proxy="stock", start="hypoinverse"),
    "R3bf_xcorr_like_reference_hypodd_like_hypoinverse_start_filtered": dict(LIKE_REF, proxy="preprocess",
                                                                            start="hypoinverse"),
    "R4_xcorr_like_reference_hypodd_like_no_outlier_picks": dict(LIKE_REF, proxy="stock", phases="no_outliers"),
    "R4f_xcorr_like_reference_hypodd_like_no_outlier_picks_filtered": dict(LIKE_REF, proxy="preprocess",
                                                                          phases="no_outliers"),
    "R5_xcorr_like_reference_hypodd_like_homogeneous": dict(LIKE_REF, proxy="stock", ttt="homogeneous"),
    "R5f_xcorr_like_reference_hypodd_like_homogeneous_filtered": dict(LIKE_REF, proxy="preprocess",
                                                                      ttt="homogeneous"),
    "R1fw_xcorr_like_reference_hypodd_like_filtered_xcorrweight100": dict(
        LIKE_REF, proxy="preprocess", solver_override=dict(xcorrWeightScaler=100.0),
        note="exploratory: HypoDD's final iteration sets weight cc data ~100x the catalog data (1.0/0.8 vs "
             "0.01/0.005); rtDD's default scaler 2 gives cc data only 1+|cc| times the catalog weight"),
    # R6: leave-one-out single-event mode. 'one_step' = one relocateSingleEvent call with cross-correlation
    # (as the task specifies); 'scrtdd_two_step' = the procedure of scrtdd's rtddtool.cpp
    # (Profile::relocateSingleEvent): step 1 without cross-correlation and minEvStaToInterEvRatio 1, step 2 from
    # the step-1 location with numEllipsoids 1 and cross-correlation. isManual True treats the picks like
    # catalog picks (both cross-correlation directions, as in multi-event mode); False is how scrtdd treats an
    # automatic origin (only the catalog pick window is trusted).
    "R6_single_event_loo_one_step": dict(LIKE_REF, proxy="stock", mode="single", background="R1_xcorr_like_reference_hypodd_like",
                                         clustering="single_event_scrtdd_defaults", steps="one_step", is_manual=True),
    "R6p_single_event_loo_one_step_padded": dict(LIKE_REF, proxy="stock", mode="single",
                                                 background="R1_xcorr_like_reference_hypodd_like",
                                                 clustering="single_event_scrtdd_defaults", steps="one_step",
                                                 is_manual=True, pad_batch_s=PAD_BATCH_S,
                                                 note="R6 with the batch-loading fix only (still unfiltered, like R1)"),
    "R6f_single_event_loo_one_step_filtered": dict(LIKE_REF, proxy="preprocess", mode="single", pad_batch_s=PAD_BATCH_S,
                                                  background="R1f_xcorr_like_reference_hypodd_like_filtered",
                                                  clustering="single_event_scrtdd_defaults", steps="one_step",
                                                  is_manual=True),
    "R6t_single_event_loo_scrtdd_two_step_automatic": dict(LIKE_REF, proxy="stock", mode="single",
                                                           background="R1_xcorr_like_reference_hypodd_like",
                                                           clustering="single_event_scrtdd_defaults",
                                                           steps="scrtdd_two_step", is_manual=False),
    "R6tp_single_event_loo_scrtdd_two_step_automatic_padded": dict(
        LIKE_REF, proxy="stock", mode="single", background="R1_xcorr_like_reference_hypodd_like",
        clustering="single_event_scrtdd_defaults", steps="scrtdd_two_step", is_manual=False, pad_batch_s=PAD_BATCH_S,
        note="R6t with the batch-loading fix only (still unfiltered, like R1)"),
    "R6tf_single_event_loo_scrtdd_two_step_automatic_filtered": dict(
        LIKE_REF, proxy="preprocess", mode="single", background="R1f_xcorr_like_reference_hypodd_like_filtered",
        pad_batch_s=PAD_BATCH_S,
        clustering="single_event_scrtdd_defaults", steps="scrtdd_two_step", is_manual=False),
}


# ============================================================================= helpers
def log(msg):
    line = f"[{_dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOGFILE, "a") as fo:
        fo.write(line + "\n")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_jsonable(obj):
    """Read back every public, non-callable attribute of a pybind11 options object (recursively)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(o) for o in obj]
    if isinstance(obj, dict):
        return {(k.name if hasattr(k, "name") else str(k)): to_jsonable(v) for k, v in obj.items()}
    out = {}
    for a in dir(obj):
        if a.startswith("_"):
            continue
        v = getattr(obj, a)
        if callable(v):
            continue
        out[a] = to_jsonable(v)
    return out


@contextlib.contextmanager
def redirect_fd2(path):
    """libhdd logs with std::cerr (fd 2): send it to the run's console.log for the duration of the run."""
    sys.stderr.flush()
    saved = os.dup(2)
    with open(path, "a") as f:
        os.dup2(f.fileno(), 2)
        try:
            yield
        finally:
            sys.stderr.flush()
            os.dup2(saved, 2)
            os.close(saved)


def hdd_resample(data, data_sf, new_sf):
    """Exact numpy port of libhdd waveform.cpp resample() (scrtdd v2.0.9): Hann-windowed sinc, low-pass at
    min(new_sf, data_sf)/2, window length ceil(5.98*data_sf/(0.1*nyquist)) input samples. The C++ integer
    conversions (truncation toward zero) are reproduced, including the double use of sample 0 at the start."""
    if new_sf <= 0 or data_sf == new_sf:
        return np.asarray(data, dtype=np.float64)
    data = np.asarray(data, dtype=np.float64)
    n = data.size
    factor = new_sf / data_sf
    fmax = min(new_sf, data_sf) / 2.0
    win_len = int(np.ceil(5.98 * data_sf / (fmax * 0.10)))
    gain = 2 * fmax / data_sf
    lo = int(-(win_len / 2.0))
    win_i = np.array([w for w in range(lo, win_len + 1) if w < win_len - (win_len / 2.0)], dtype=np.float64)
    n_out = int(n * factor)
    x = np.arange(n_out, dtype=np.float64) / factor
    pos = x[:, None] + win_i[None, :]
    data_i = np.trunc(pos).astype(np.int64)
    win_x = data_i - x[:, None]
    ok = (data_i >= 0) & (data_i < n)
    hann = np.sin(np.pi * (0.5 + win_x / win_len)) ** 2
    a = 2 * np.pi * win_x * fmax / data_sf
    with np.errstate(invalid="ignore", divide="ignore"):
        sinc = np.where(a == 0, 1.0, np.sin(a) / np.where(a == 0, 1.0, a))
    vals = np.where(ok, data[np.clip(data_i, 0, n - 1)], 0.0)
    return np.sum(gain * hann * sinc * vals, axis=1)


def make_proxies():
    """Defined lazily (needs obspy + pyrtdd)."""
    import obspy
    from pyrtdd.hdd import Trace
    from pyrtdd.obspy.waveform import ObspyClientProxy, _to_utcdatetime, _to_hdd_time, _obspy_trace_to_hdd

    class CountingStockProxy(ObspyClientProxy):
        """The stock proxy, unchanged, except that it counts the filter() calls libhdd makes (so options.json
        can show that libhdd asked for the filter, although the result never reaches libhdd), and - only when
        pad_batch_s > 0 - fixes batch loading: libhdd's BatchLoader::get (single-event mode: the waveforms of the
        event being relocated) accepts a trace only if it CONTAINS the requested window, but obspy trims to the
        nearest sample and the KMA samples sit a few ms off the request grid (e.g. x.xx3096 s), so the stock
        get_waveforms_bulk() traces always miss the window by a fraction of a sample and every single-event
        cross-correlation is skipped. With pad_batch_s > 0 each batch request is fetched pad_batch_s wider on
        both sides (one get_waveforms call per request); libhdd then slices it back to the requested window."""

        def __init__(self, client, inventory, guess_zne=False, pad_batch_s=0.0):
            super().__init__(client, inventory, guess_zne)
            self.filter_calls = {}
            self.pad_batch_s = float(pad_batch_s)
            self.n_batch_loaded, self.n_batch_failed = 0, 0

        def loadTraces(self, request, onTraceLoaded, onTraceFailed):
            if self.pad_batch_s <= 0:          # stock behaviour (SDS client get_waveforms_bulk)
                ok = lambda sid, tw, tr: (setattr(self, "n_batch_loaded", self.n_batch_loaded + 1),
                                          onTraceLoaded(sid, tw, tr))
                bad = lambda sid, tw, msg: (setattr(self, "n_batch_failed", self.n_batch_failed + 1),
                                            onTraceFailed(sid, tw, msg))
                super().loadTraces(request, ok, bad)
                return
            for streamId, tw in request:
                net, sta, loc, cha = streamId.split(".")
                try:
                    tr = self._fetch(net, sta, loc, cha, _to_utcdatetime(tw.startTime) - self.pad_batch_s,
                                     _to_utcdatetime(tw.endTime) + self.pad_batch_s)
                    if tr is None:
                        raise RuntimeError(f"no waveform data for {streamId}")
                    self.n_batch_loaded += 1
                    onTraceLoaded(streamId, tw, _obspy_trace_to_hdd(tr))
                except Exception as e:
                    self.n_batch_failed += 1
                    onTraceFailed(streamId, tw, str(e))

        def filter(self, trace, filterStr):
            key = f"{filterStr} @ {trace.samplingFrequency:g} Hz"
            self.filter_calls[key] = self.filter_calls.get(key, 0) + 1
            super().filter(trace, filterStr)

    class PreprocessingSDSProxy(ObspyClientProxy):
        """Does in loadTrace() what libhdd's BasicProcessor::filter would do with a working filter():
        demean -> libhdd sinc resample -> obspy Trace.filter(kind, **float kwargs) (same call as the stock
        proxy's filter()). Batch requests are routed through loadTrace (the stock ObspyClientProxy would use
        the SDS client's get_waveforms_bulk and skip the processing)."""

        def __init__(self, client, inventory, guess_zne, filter_str, resample_hz, pad_batch_s=0.0):
            super().__init__(client, inventory, guess_zne)
            self.pad_batch_s = float(pad_batch_s)
            self.n_batch_loaded, self.n_batch_failed = 0, 0
            self.resample_hz = float(resample_hz)
            self.kind, self.kwargs = None, {}
            if filter_str:
                kind, *parts = filter_str.split(";")
                self.kind = kind
                self.kwargs = {p.split("=")[0]: float(p.split("=")[1]) for p in parts}   # as the stock proxy
            self.n_loaded, self.n_failed = 0, 0

        def loadTrace(self, tw, networkCode, stationCode, locationCode, channelCode, pad=0.0):
            tr = self._fetch(networkCode, stationCode, locationCode, channelCode,
                             _to_utcdatetime(tw.startTime) - pad, _to_utcdatetime(tw.endTime) + pad)
            if tr is None:
                self.n_failed += 1
                raise RuntimeError(f"no waveform data for {networkCode}.{stationCode}.{locationCode}.{channelCode}")
            data = tr.data.astype(np.float64)
            data = data - data.mean()
            fs = float(tr.stats.sampling_rate)
            if self.resample_hz > 0 and fs != self.resample_hz:
                data = hdd_resample(data, fs, self.resample_hz)
                fs = self.resample_hz
            if self.kind:
                tmp = obspy.Trace(data=data, header={"sampling_rate": fs})
                tmp.filter(self.kind, **self.kwargs)
                data = tmp.data
            self.n_loaded += 1
            return Trace(networkCode, stationCode, locationCode, channelCode, _to_hdd_time(tr.stats.starttime),
                         fs, np.ascontiguousarray(data, dtype=np.float64))

        def loadTraces(self, request, onTraceLoaded, onTraceFailed):
            for streamId, tw in request:
                net, sta, loc, cha = streamId.split(".")
                try:
                    tr = self.loadTrace(tw, net, sta, loc, cha, pad=self.pad_batch_s)
                    self.n_batch_loaded += 1
                    onTraceLoaded(streamId, tw, tr)
                except Exception as e:
                    self.n_batch_failed += 1
                    onTraceFailed(streamId, tw, str(e))

        def filter(self, trace, filterStr):
            raise RuntimeError("PreprocessingSDSProxy.filter() must not be called (libhdd filterStr must be empty)")

    return CountingStockProxy, PreprocessingSDSProxy


def outlier_picks():
    """The 17 picks whose observed travel time is > OUTLIER_THRESHOLD_S off the kim1983 grid time
    (validation_picks.csv), cross-checked against runs/verify_inputs/v3d_outliers.log."""
    v = pd.read_csv(VALIDATION_PICKS_CSV)
    idm = pd.read_csv(EVENT_ID_MAP)
    v = v.merge(idm[["rtdd_id", "kma_id"]], left_on="Event_ID", right_on="kma_id")
    o = v[v.res_obs_minus_grid_s.abs() > OUTLIER_THRESHOLD_S].copy()
    o = o.rename(columns={"Station": "stationCode", "Phase": "type"})
    o = o[["rtdd_id", "kma_id", "stationCode", "type", "t_obs_s", "t_grid_s", "res_obs_minus_grid_s"]]
    logged = set()
    for line in open(OUTLIER_LOG):
        line = line.strip()
        if line.startswith("("):
            p = line.strip("()").replace("'", "").split(",")
            logged.add((int(p[0]), p[1].strip(), p[2].strip()))
    mine = set(zip(o.rtdd_id.astype(int), o.stationCode, o.type))
    if mine != logged:
        raise RuntimeError(f"outlier lists differ: only in csv {mine - logged}, only in log {logged - mine}")
    return o.sort_values(["rtdd_id", "stationCode", "type"]).reset_index(drop=True)


def resolve(run_name):
    """Expand a run definition into the full set of named settings."""
    r = dict(RUNS[run_name])
    r.setdefault("proxy", "none")
    r.setdefault("note", "")
    r.setdefault("disk_cache", r["proxy"] == "stock")     # preprocess proxy: never (see header)
    return r


def build_options(r):
    from pyrtdd.hdd import Config, ClusteringOptions, SolverOptions, XcorrOptions, Catalog
    PT = Catalog.Phase.Type
    cfg = Config()
    cfg.validPphases, cfg.validSphases = ["P"], ["S"]
    wf = WFFILTER[r["wffilter"]]
    lib_wf = dict(wf)
    if r["proxy"] == "preprocess":          # the proxy does it; libhdd must not try (it would be a no-op anyway)
        lib_wf.update(filterStr="", resampleFreq=0.0)
    cfg.wfFilter.filterStr, cfg.wfFilter.resampleFreq, cfg.wfFilter.extraTraceLen = (
        lib_wf["filterStr"], lib_wf["resampleFreq"], lib_wf["extraTraceLen"])
    co = ClusteringOptions()
    for k, v in CLUSTERING[r["clustering"]].items():
        setattr(co, k, v)
    so = SolverOptions()
    for k, v in dict(SOLVER[r["solver"]], **r.get("solver_override", {})).items():
        setattr(so, k, v)
    xo = XcorrOptions()
    xs = XCORR[r["xcorr"]]
    if xs is not None:
        xo.enable = True
        for k in ("minEvStaDist", "maxEvStaDist", "maxInterEvDist"):
            if k in xs:
                setattr(xo, k, xs[k])
        if "P" in xs:
            mk = lambda d: XcorrOptions.XCorr(d["minCoef"], d["startOffset"], d["endOffset"], d["winScaling"],
                                              d["maxDelay"], d["components"])
            xo.phase = {PT.P: mk(xs["P"]), PT.S: mk(xs["S"])}
    else:
        xo.enable = False
    # read back and assert (pybind11 STL members are easy to set by accident on a temporary copy)
    for k, v in CLUSTERING[r["clustering"]].items():
        assert getattr(co, k) == v, (k, getattr(co, k), v)
    for k, v in dict(SOLVER[r["solver"]], **r.get("solver_override", {})).items():
        assert getattr(so, k) == v, (k, getattr(so, k), v)
    if xs is not None and "P" in xs:
        for t, key in ((PT.P, "P"), (PT.S, "S")):
            got = xo.phase[t]
            for k, v in xs[key].items():
                assert getattr(got, k) == v, (key, k, getattr(got, k), v)
    assert cfg.wfFilter.filterStr == lib_wf["filterStr"] and cfg.wfFilter.resampleFreq == lib_wf["resampleFreq"]
    return cfg, co, so, xo, wf


def make_ttt(r):
    from pyrtdd.hdd import NLLGrid, Homogeneous
    if r["ttt"] == "nll":
        args = dict(gridPath=NLL_GRID_PATH, gridModel=NLL_GRID_MODEL, maxSearchDistance=NLL_MAX_SEARCH_DISTANCE_M,
                    swapBytes=False, maxOpenFiles=512, accessMethod="KeepOpen")
        return NLLGrid(**args), dict(type="NLLGrid", **args)
    args = dict(pVel=HOMOGENEOUS_VP, sVel=HOMOGENEOUS_VS)
    return Homogeneous(HOMOGENEOUS_VP, HOMOGENEOUS_VS), dict(type="Homogeneous", **args)


def make_proxy(r, wf, counters):
    import obspy
    from obspy.clients.filesystem.sds import Client as SDSClient
    CountingStockProxy, PreprocessingSDSProxy = counters["classes"]
    if r["proxy"] == "none":
        return None, dict(type="none (NoWaveformProxy: no cross-correlation)")
    inv = counters.setdefault("inventory", obspy.read_inventory(INVENTORY_XML))
    client = SDSClient(SDS)
    if r["proxy"] == "stock":
        p = CountingStockProxy(client, inv, guess_zne=False, pad_batch_s=r.get("pad_batch_s", 0.0))
        desc = dict(type="pyrtdd.obspy.waveform.ObspyClientProxy (stock; subclass only counts filter() calls)",
                    client="obspy.clients.filesystem.sds.Client", sds=SDS, inventory=INVENTORY_XML, guess_zne=False,
                    waveform_disk_cache=WFCACHE if r["disk_cache"] else "disabled",
                    diskTraceMinLen=DISK_TRACE_MIN_LEN if r["disk_cache"] else None,
                    processing_actually_applied="demean + libhdd sinc resample to "
                    f"{wf['resampleFreq']:g} Hz (if > 0); band-pass NOT applied (pyrtdd trampoline copy bug)",
                    batch_loading=("stock get_waveforms_bulk (single-event traces miss the requested window by a "
                                   "fraction of a sample -> libhdd BatchLoader rejects them)"
                                   if r.get("pad_batch_s", 0.0) <= 0 else
                                   f"padded: one get_waveforms per request, window +- {r['pad_batch_s']} s"))
    else:
        p = PreprocessingSDSProxy(client, inv, False, wf["filterStr"], wf["resampleFreq"],
                                  pad_batch_s=r.get("pad_batch_s", 0.0))
        desc = dict(type="PreprocessingSDSProxy(ObspyClientProxy) defined in run_pyrtdd_gwangyang.py",
                    client="obspy.clients.filesystem.sds.Client", sds=SDS, inventory=INVENTORY_XML, guess_zne=False,
                    waveform_disk_cache="disabled (the proxy must see the window libhdd processes)",
                    processing_actually_applied=f"demean + libhdd sinc resample (numpy port) to "
                    f"{wf['resampleFreq']:g} Hz + obspy Trace.filter({p.kind!r}, **{p.kwargs}) on window +- "
                    f"{wf['extraTraceLen']:g} s; then libhdd demeans again and slices",
                    filter_kind=p.kind, filter_kwargs=p.kwargs,
                    batch_loading=("routed through loadTrace, no padding" if r.get("pad_batch_s", 0.0) <= 0 else
                                   f"routed through loadTrace, window +- {r['pad_batch_s']} s (processing on the "
                                   "padded window)"))
    return p, desc


def write_catalog_inputs(r, rundir):
    """Copy/derive the catalog files this run reads into <run>/inputs/ and return their paths + notes."""
    ind = f"{rundir}/inputs"
    os.makedirs(ind, exist_ok=True)
    shutil.copyfile(STATION_CSV, f"{ind}/station.csv")
    shutil.copyfile(EVENT_CENTROID_CSV if r["start"] == "centroid" else EVENT_HYPOINVERSE_CSV, f"{ind}/event.csv")
    notes = {"event_source": EVENT_CENTROID_CSV if r["start"] == "centroid" else EVENT_HYPOINVERSE_CSV}
    ph = pd.read_csv(PHASE_CSV, dtype=str, keep_default_na=False)
    if r["phases"] == "no_outliers":
        o = outlier_picks()
        key = set(zip(o.rtdd_id.astype(str), o.stationCode, o.type))
        drop = [(e, s, t) in key for e, s, t in zip(ph.eventId, ph.stationCode, ph.type)]
        dropped = ph[drop].copy()
        if len(dropped) != len(o):
            raise RuntimeError(f"expected to drop {len(o)} picks, matched {len(dropped)}")
        dropped = dropped.merge(o.assign(eventId=o.rtdd_id.astype(str)), on=["eventId", "stationCode", "type"])
        dropped.to_csv(f"{ind}/dropped_picks.csv", index=False)
        ph = ph[[not d for d in drop]]
        notes["dropped_picks"] = f"{len(dropped)} picks (|obs - kim1983 grid| > {OUTLIER_THRESHOLD_S} s), listed in inputs/dropped_picks.csv"
    ph.to_csv(f"{ind}/phase.csv", index=False)
    notes["phase_source"] = PHASE_CSV
    notes["n_picks"] = int(len(ph))
    return (f"{ind}/station.csv", f"{ind}/event.csv", f"{ind}/phase.csv"), notes


def finish_info(rundir, info):
    with open(f"{rundir}/run_info.json", "w") as fo:
        json.dump(info, fo, indent=1, default=str)


def versions():
    import obspy
    v = {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
         "obspy": obspy.__version__}
    try:
        v["pyrtdd_commit"] = subprocess.run(["git", "-C", PYRTDD_SRC, "rev-parse", "HEAD"], capture_output=True,
                                            text=True).stdout.strip()
        v["libhdd_tag"] = subprocess.run(["git", "-C", f"{PYRTDD_SRC}/deps/scrtdd", "describe", "--tags"],
                                         capture_output=True, text=True).stdout.strip()
    except Exception as e:
        v["git_error"] = str(e)
    import pyrtdd
    v["pyrtdd_module"] = pyrtdd.__file__
    return v


# ============================================================================= multi-event run
def run_multi(name, r, rundir, counters):
    from pyrtdd.hdd import Catalog, DD, XCorrCache, Neighbours
    cfg, co, so, xo, wf = build_options(r)
    files, notes = write_catalog_inputs(r, rundir)
    cat = Catalog(*files)
    ttt, ttt_desc = make_ttt(r)
    proxy, proxy_desc = make_proxy(r, wf, counters)
    options = dict(run=name, definition=r, Config=to_jsonable(cfg), ClusteringOptions=to_jsonable(co),
                   SolverOptions=to_jsonable(so), XcorrOptions=to_jsonable(xo),
                   wffilter_requested=wf, travel_time_table=ttt_desc, waveform_proxy=proxy_desc,
                   catalog_files={os.path.basename(f): dict(path=f, md5=md5(f)) for f in files}, catalog_notes=notes,
                   saveProcessing=True, versions=versions())
    with open(f"{rundir}/options.json", "w") as fo:
        json.dump(options, fo, indent=1, default=str)
    dd = DD(cat, cfg, ttt, proxy) if proxy is not None else DD(cat, cfg, ttt)
    if r["disk_cache"]:
        dd.enableCatalogWaveformDiskCache(WFCACHE, DISK_TRACE_MIN_LEN)
    clusters = dd.findClusters(co)
    os.makedirs(f"{rundir}/clusters", exist_ok=True)
    for i, c in enumerate(clusters):
        Neighbours.writeToFile(c, cat, f"{rundir}/clusters/cluster_{i + 1}.csv")
    ncl = [len(c) for c in clusters]
    xcd = XCorrCache()
    if xo.enable:
        newcat = dd.relocateMultiEvents(clusters, xcd, xo, so, True, f"{rundir}/processing")
        xcd.writeToFile(cat, f"{rundir}/xcorr_cache.csv")
    else:
        newcat = dd.relocateMultiEvents(clusters, so, True, f"{rundir}/processing")
    newcat.writeToFile(f"{rundir}/relocated-station.csv", f"{rundir}/relocated-event.csv",
                       f"{rundir}/relocated-phase.csv")
    extra = dict(n_clusters=len(clusters), cluster_sizes=ncl, n_relocated=len(newcat.getEvents()))
    if proxy is not None:
        extra["filter_calls_received_by_proxy"] = getattr(proxy, "filter_calls", None)
        extra["proxy_traces_processed"] = getattr(proxy, "n_loaded", None)
        extra["proxy_traces_failed"] = getattr(proxy, "n_failed", None)
    return extra


# ============================================================================= single-event (leave-one-out) run
def run_single(name, r, rundir, counters):
    from pyrtdd.hdd import Catalog, DD, ClusteringOptions
    cfg, co, so, xo, wf = build_options(r)
    files, notes = write_catalog_inputs(r, rundir)          # the input catalog (centroid start, original picks)
    incat = Catalog(*files)
    bgdir = f"{OUTROOT}/{r['background']}"
    if not os.path.exists(f"{bgdir}/run_info.json") or json.load(open(f"{bgdir}/run_info.json"))["status"] != "ok":
        raise RuntimeError(f"background run {r['background']} has not finished successfully")
    bev = pd.read_csv(f"{bgdir}/relocated-event.csv")
    bph = pd.read_csv(f"{bgdir}/relocated-phase.csv", dtype=str, keep_default_na=False)
    ev_cols = ["id", "isotime", "latitude", "longitude", "depth", "magnitude"]
    ph_cols = ["eventId", "isotime", "lowerUncertainty", "upperUncertainty", "type", "networkCode", "stationCode",
               "locationCode", "channelCode"]
    ttt_desc = make_ttt(r)[1]
    proxy_desc = make_proxy(r, wf, counters)[1]
    # clustering of the two scrtdd steps (rtddtool.cpp): step 1 ratio 1 without xcorr; step 2 numEllipsoids 1
    co1 = ClusteringOptions()
    co2 = ClusteringOptions()
    for k, v in CLUSTERING[r["clustering"]].items():
        setattr(co1, k, v)
        setattr(co2, k, v)
    co1.minEvStaToInterEvRatio = 1.0
    co2.numEllipsoids = 1
    from pyrtdd.hdd import XcorrOptions
    xo_off = XcorrOptions()
    xo_off.enable = False
    options = dict(run=name, definition=r, Config=to_jsonable(cfg), SolverOptions=to_jsonable(so),
                   XcorrOptions=to_jsonable(xo), wffilter_requested=wf, travel_time_table=ttt_desc,
                   waveform_proxy=proxy_desc, is_manual=r["is_manual"], steps=r["steps"],
                   background_catalog=dict(run=r["background"], event_csv=f"{bgdir}/relocated-event.csv",
                                           phase_csv=f"{bgdir}/relocated-phase.csv", station_csv=STATION_CSV,
                                           note="background for event k = these files without event k"),
                   single_event_source=dict(files={os.path.basename(f): dict(path=f, md5=md5(f)) for f in files},
                                            note="Catalog.extractEvent(k, keepEvId=True) of the input catalog"),
                   versions=versions())
    if r["steps"] == "one_step":
        options["ClusteringOptions"] = to_jsonable(co)
    else:
        options["ClusteringOptions_step1"] = to_jsonable(co1)
        options["XcorrOptions_step1"] = to_jsonable(xo_off)
        options["ClusteringOptions_step2"] = to_jsonable(co2)
        options["XcorrOptions_step2"] = to_jsonable(xo)
    with open(f"{rundir}/options.json", "w") as fo:
        json.dump(options, fo, indent=1, default=str)

    rows, ev_rows, ph_rows, per_event = [], [], [], {}
    for k in sorted(incat.getEvents().keys()):
        evd = f"{rundir}/inputs/background_without_{k}"
        os.makedirs(evd, exist_ok=True)
        shutil.copyfile(STATION_CSV, f"{evd}/station.csv")
        bev[bev.id != k][ev_cols].to_csv(f"{evd}/event.csv", index=False)
        bph[bph.eventId.astype(int) != k][ph_cols].to_csv(f"{evd}/phase.csv", index=False)
        bg = Catalog(f"{evd}/station.csv", f"{evd}/event.csv", f"{evd}/phase.csv")
        single = incat.extractEvent(k, True)
        ttt = make_ttt(r)[0]
        proxy = make_proxy(r, wf, counters)[0]
        dd = DD(bg, cfg, ttt, proxy)
        if r["disk_cache"]:
            dd.enableCatalogWaveformDiskCache(WFCACHE, DISK_TRACE_MIN_LEN)
        t0 = time.perf_counter()
        status, err, step1_ok = "ok", "", None
        try:
            if r["steps"] == "one_step":
                rel = dd.relocateSingleEvent(single, r["is_manual"], co, xo, so, True, f"{rundir}/processing/ev{k}")
            else:
                s1 = dd.relocateSingleEvent(single, r["is_manual"], co1, xo_off, so, True,
                                            f"{rundir}/processing/ev{k}/step1")
                step1_ok = len(s1.getEvents()) > 0
                start2 = s1 if step1_ok else single
                rel = dd.relocateSingleEvent(start2, r["is_manual"], co2, xo, so, True,
                                             f"{rundir}/processing/ev{k}/step2")
            evs = rel.getEvents()
            if len(evs) != 1:
                status, err = "failed", f"relocateSingleEvent returned {len(evs)} events"
        except Exception as e:
            status, err = "failed", f"{type(e).__name__}: {e}"
        dt = time.perf_counter() - t0
        row = dict(event_id=k, status=status, error=err, wall_s=round(dt, 2), step1_ok=step1_ok,
                   batch_traces_loaded=getattr(proxy, "n_batch_loaded", None),
                   batch_traces_failed=getattr(proxy, "n_batch_failed", None))
        ddf = f"{rundir}/processing/ev{k}" + ("" if r["steps"] == "one_step" else "/step2") + "/initial-double-difference.csv"
        if os.path.exists(ddf):
            ddi = pd.read_csv(ddf)
            row.update(n_dd=int(len(ddi)), n_xcorr_measured=int((ddi.xcorrCoefficient != 0).sum()),
                       n_xcorr_used=int((ddi.xcorrUsed.astype(str).str.lower() == "true").sum()))
        if status == "ok":
            e = list(evs.values())[0]
            from pyrtdd.hdd import UTCClock
            row.update(new_id=e.id, latitude=e.latitude, longitude=e.longitude, depth=e.depth,
                       isotime=UTCClock.toString(e.time), startRms=e.relocInfo.startRms,
                       finalRms=e.relocInfo.finalRms)
            rel.writeToFile(f"{rundir}/processing/ev{k}/final-reloc-station.csv",
                            f"{rundir}/processing/ev{k}/final-reloc-event.csv",
                            f"{rundir}/processing/ev{k}/final-reloc-phase.csv")
            ev_rows.append(dict(id=k, isotime=row["isotime"], latitude=e.latitude, longitude=e.longitude,
                                depth=e.depth, magnitude=e.magnitude, relocated="true", startRms=e.relocInfo.startRms,
                                finalRms=e.relocInfo.finalRms))
            rp = pd.read_csv(f"{rundir}/processing/ev{k}/final-reloc-phase.csv", dtype=str, keep_default_na=False)
            rp["eventId"] = str(k)
            ph_rows.append(rp)
        rows.append(row)
        per_event[k] = dict(getattr(proxy, "filter_calls", {}) or {}, n_loaded=getattr(proxy, "n_loaded", None))
        log(f"   {name} event {k}: {status} {err} ({dt:.1f} s)")
    pd.DataFrame(rows).to_csv(f"{rundir}/single_event_results.csv", index=False)
    if ev_rows:
        pd.DataFrame(ev_rows).to_csv(f"{rundir}/relocated-event.csv", index=False, float_format="%.8f")
        pd.concat(ph_rows).to_csv(f"{rundir}/relocated-phase.csv", index=False)
        shutil.copyfile(STATION_CSV, f"{rundir}/relocated-station.csv")
    n_ok = sum(r_["status"] == "ok" for r_ in rows)
    return dict(n_relocated=n_ok, n_failed=len(rows) - n_ok, proxy_counters_per_event=per_event,
                note="relocated-event.csv is assembled from the 11 single-event results (ids = original ids); "
                     "processing/ev<k>/ holds libhdd's own output per event")


# ============================================================================= main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="run (default: dry run, print the plan)")
    ap.add_argument("--runs", default="", help="comma-separated run names (default: all, in order)")
    ap.add_argument("--force", action="store_true", help="re-run runs that already finished ok")
    args = ap.parse_args()
    names = [n for n in args.runs.split(",") if n] or list(RUNS)
    for n in names:
        if n not in RUNS:
            sys.exit(f"unknown run {n}; known: {list(RUNS)}")
    if not args.apply:
        for n in names:
            r = resolve(n)
            print(f"== {n}\n   {json.dumps(r)}")
            print(f"   clustering {CLUSTERING[r['clustering']]}\n   solver {SOLVER[r['solver']]} "
                  f"{r.get('solver_override', '')}\n   xcorr {XCORR[r['xcorr']]}\n   wffilter {WFFILTER[r['wffilter']]}")
        print(f"[dry run] {len(names)} runs; outputs would go to {OUTROOT}/<run>/; nothing written")
        print("[dry run] R4 would drop:\n" + outlier_picks().to_string())
        return

    from pyrtdd.hdd import Logger
    Logger.setLevel(Logger.Level.info)
    counters = {"classes": make_proxies()}
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    log(f"start: {len(names)} runs: {names}")
    for n in names:
        r = resolve(n)
        rundir = f"{OUTROOT}/{n}"
        if os.path.exists(f"{rundir}/run_info.json") and not args.force:
            if json.load(open(f"{rundir}/run_info.json")).get("status") == "ok":
                log(f"skip {n}: already ok (use --force to redo)")
                continue
        if os.path.isdir(rundir):
            shutil.rmtree(rundir)            # a previous failed/forced attempt: start clean
        os.makedirs(rundir)
        t0 = time.perf_counter()
        info = dict(run=n, started=_dt.datetime.now().isoformat(timespec="seconds"), host=os.uname().nodename)
        try:
            with redirect_fd2(f"{rundir}/console.log"):
                extra = run_single(n, r, rundir, counters) if r["mode"] == "single" else run_multi(n, r, rundir, counters)
            info.update(status="ok", **extra)
        except Exception as e:
            info.update(status="failed", error=f"{type(e).__name__}: {e}", traceback=traceback.format_exc())
        info["wall_time_s"] = round(time.perf_counter() - t0, 2)
        info["finished"] = _dt.datetime.now().isoformat(timespec="seconds")
        finish_info(rundir, info)
        log(f"{n}: {info['status']} in {info['wall_time_s']:.1f} s; relocated {info.get('n_relocated')} "
            f"{info.get('error', '')}")
    log("done")


if __name__ == "__main__":
    main()
