#!/usr/bin/env python
# run_pyrtdd_sanramon2026.py
#
# COPY of runs/sanramon/pyrtdd/run_pyrtdd_sanramon.py (2015 San Ramon swarm, docs/results/11_sanramon_relocation.md),
# made 2026-10-18 for the San Ramon 2025-26 sequence (927 events; inputs in data/sanramon_2026/inputs, see
# docs/sanramon2026_inputs.md). The 2015 driver is not modified. What changed against the 2015 copy, and nothing else:
#   * paths: data/sanramon_2015 -> data/sanramon_2026, runs/sanramon -> runs/sanramon2026, log names
#     logs/11_sanramon_* -> logs/13_sanramon2026_*;
#   * NonLinLoc grid model name 'sanramon_con' -> 'sanramon2026_con' (TRANS_MERC grids centred on the 2025-26 swarm,
#     300 stations within 120 km); maxSearchDistance stays 0.1 m (all 600 station/phase grids found, checked);
#   * clustering maxEvStaDist: 2015 -1 (no limit) -> 120 km, as the task asks (2,998 P picks lie at stations
#     beyond 120 km, which have no grid; 2015: 937). With -1 such picks still count towards minNumPhases in the
#     clustering and are only dropped later, at the travel-time lookup. Every other clustering value stays at the
#     libhdd default;
#   * only the four task runs are defined (P0, P1 here; S0, S1 in ../scrtdd). The 2015 sensitivity runs are not
#     repeated (task: "no extra sensitivity runs unless something fails").
# One named run per setting combination (RUNS below). Each run writes, in runs/sanramon2026/pyrtdd/<run>/:
#   relocated-{station,event,phase}.csv   the relocated catalog (rtDD CSV format)
#   processing/                           libhdd's own saveProcessing output (relocation.log, cluster-<i>-pair.csv,
#                                         cluster-<i>-{initial,final}-double-difference.csv, xcorr.csv, ...)
#   clusters/cluster_<i>.csv              the clusters given to relocateMultiEvents
#   xcorr_cache.csv                       the XCorrCache (cross-correlation runs)
#   options.json                          EVERY option value actually used, read back from the libhdd objects
#   run_info.json                         status, wall time, peak memory, counters
#   console.log                           everything libhdd printed (file descriptor 2 is redirected)
#
# RUNS (task "San Ramon 2025-26 relocation", docs/results/13_sanramon2026_relocation.md):
#   P0   catalog differential times only; rtDD DEFAULT clustering (ellipsoids: numEllipsoids 5, maxNumNeigh 40,
#        minNumNeigh 8, minNumPhases 8, maxNeighbourDist 5 km; here with maxEvStaDist 120 km) and DEFAULT solver
#        (LSMR, absLocConstraint 0.3, damping 0.01, residual down-weighting 10 -> 5, 20 iterations).
#   P1   P0 + cross-correlation with rtDD's default windows (P -0.5..+0.5 s, S -0.5..+1.0 s, winScaling
#        0.02/0.04, maxDelay 0.5 s, |CC| >= 0.7), P on the vertical (component priority Z, then 1 = the
#        vertical of NCSN/BK borehole sensors named 1/2/3), S on L2 (both horizontals), traces resampled to
#        1000 Hz and band-passed 1.5-15 Hz (4 poles, causal; the 2015 band, kept unchanged).
# Travel times: NonLinLoc 2-D TRANS_MERC grids of the NCSS CON model (inputs/nll_con_tm/time, model
# 'sanramon2026_con'; 300 stations within 120 km of the swarm centre, maxSearchDistance 0.1 m; picks at stations
# more than 120 km from an event are excluded by the clustering (maxEvStaDist 120 km); a station within 120 km of
# an event but without a grid would still be skipped by rtDD with one warning per station).
#
# KNOWN PYRTDD BUGS and the workarounds used here (copied from runs/gwangyang/pyrtdd/run_pyrtdd_gwangyang.py,
# see docs/results/07_gwangyang_pyrtdd.md section 1):
#   (1) the Python proxy's filter() works on a COPY (pybind11 trampoline, package/src/pyrtdd/hdd/proxy_ext.cpp),
#       so cfg.wfFilter.filterStr never reaches the cross-correlation. The cross-correlation runs therefore use
#       PreprocessingSDSProxy, which does inside loadTrace() what libhdd would do with a working filter():
#       demean -> libhdd's own Hann-windowed sinc resampler (exact numpy port of waveform.cpp resample()) ->
#       obspy Trace.filter() with the same arguments as the stock proxy; libhdd's own resampleFreq/filterStr
#       are set to 0/"" for these runs, and the waveform disk cache is NOT used (the proxy must see exactly the
#       window libhdd processes).
#   (2) single-event mode only (padded batch loading) - not used here (multi-event runs only).
#
# Usage (env pyrtdd; one run per process so that peak memory is per run):
#   python -I run_pyrtdd_sanramon2026.py                       dry run: prints every run's resolved settings
#   python -I run_pyrtdd_sanramon2026.py --apply --runs P0     runs the named run(s)
#   --force   re-run a run whose folder already has run_info.json with status "ok"
# Run it niced and under 'prlimit --as=60000000000'; OMP/OPENBLAS threads are capped at 8 below.
# Summary lines go to stdout and to logs/13_sanramon2026_pyrtdd_<YYYYMMDD>.log.

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "8")

import argparse
import contextlib
import datetime as _dt
import hashlib
import json
import resource
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np
import pandas as pd

# ============================================================================= parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/sanramon_2026"
CATDIR = f"{DATA}/inputs/rtdd_catalog"
STATION_CSV = f"{CATDIR}/station.csv"
EVENT_CSV = f"{CATDIR}/event.csv"              # NCSS routine locations (geoid depth, km below sea level)
PHASE_CSV = f"{CATDIR}/phase.csv"              # 41,870 NCSS picks (37,929 P + 3,941 S; 2,489 automatic)
NLL_GRID_PATH = f"{DATA}/inputs/nll_con_tm/time"
NLL_GRID_MODEL = "sanramon2026_con"
NLL_MAX_SEARCH_DISTANCE_M = 0.1    # libhdd default (as 2015); all 600 station/phase grids found at 0.1 m (checked)
NLL_MAX_OPEN_FILES = 512           # libhdd / tttnll plugin default
SDS = f"{DATA}/inputs/sds"
INVENTORY_XML = f"{DATA}/inputs/stations.xml"  # StationXML (NCEDC/EarthScope), for component orientation
OUTROOT = f"{PROJECT}/runs/sanramon2026/pyrtdd"
LOGFILE = f"{PROJECT}/logs/13_sanramon2026_pyrtdd_{_dt.date.today():%Y%m%d}.log"
PYRTDD_SRC = f"{PROJECT}/software/src/pyrtdd"

# ----------------------------------------------------------------------------- named settings
# Empty dict = libhdd defaults (ClusteringOptions(): numEllipsoids 5, maxNeighbourDist 5 km, minNumNeigh 8,
# maxNumNeigh 40, minNumPhases 8, maxNumPhases 0, minEvStaToInterEvRatio 3, minEvStaDist 0, maxEvStaDist -1).
# 2025-26: maxEvStaDist 120 km (task; the grids end at 120 km from the centre), all else at the libhdd default.
CLUSTERING = {
    "rtdd_default_maxEvSta120": dict(maxEvStaDist=120.0),
}
# Empty dict = libhdd defaults (SolverOptions(): LSMR, absLocConstraint 0.3/0.3, damping 0.01/0.01,
# downWeightingByResidual 10/5, algoIterations 20, solverIterations 0 = auto, L2normalization true,
# usePickUncertainties false, xcorrWeightScaler 2).
SOLVER = {
    "rtdd_default": dict(),
}
# Cross-correlation: rtDD default windows (libs/hdd/dd.h XcorrOptions) with the P component list extended by
# '1' (vertical of the 1/2/3-named borehole sensors: NC.CCH1/CGP1/CYD1/CSU1 EP, BK/BP CN/DP/EP/HN; every '1'
# channel of a sensor without a 'Z' channel has dip +-90 in stations.xml). S stays on L2 (vertical-only
# sensors therefore give no S cross-correlation).
XC_P = dict(minCoef=0.7, startOffset=-0.5, endOffset=0.5, winScaling=0.02, maxDelay=0.5, components=["Z", "1"])
XC_S = dict(minCoef=0.7, startOffset=-0.5, endOffset=1.0, winScaling=0.04, maxDelay=0.5, components=["L2"])
XCORR = {
    "rtdd_default_windows": dict(enable=True, minEvStaDist=0.0, maxEvStaDist=-1.0, maxInterEvDist=-1.0,
                                 P=XC_P, S=XC_S),
    "off": None,
}
WFFILTER = {
    "bp1.5-15_causal_1000Hz": dict(filterStr="bandpass;freqmin=1.5;freqmax=15;corners=4", resampleFreq=1000.0,
                                   extraTraceLen=1.0),
    "none": dict(filterStr="", resampleFreq=0.0, extraTraceLen=1.0),
}

P0 = dict(clustering="rtdd_default_maxEvSta120", solver="rtdd_default", xcorr="off", wffilter="none", proxy="none")
P1 = dict(P0, xcorr="rtdd_default_windows", wffilter="bp1.5-15_causal_1000Hz", proxy="preprocess")
RUNS = {
    "P0": dict(P0, what="catalog dt only; rtDD default clustering (ellipsoids; maxEvStaDist 120 km) and solver "
                        "(absLocConstraint 0.3)"),
    "P1": dict(P1, what="P0 + cross-correlation (default windows; P Z/1, S L2; 1.5-15 Hz, 1000 Hz; filtering proxy)"),
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
    conversions (truncation toward zero) are reproduced, including the double use of sample 0 at the start.
    (verbatim from runs/gwangyang/pyrtdd/run_pyrtdd_gwangyang.py; validated there by run V1)"""
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


def make_proxy_class():
    """Defined lazily (needs obspy + pyrtdd). Verbatim logic of PreprocessingSDSProxy of the Gwangyang driver
    (padding only used in single-event mode, kept for completeness), plus counters by failure reason."""
    import obspy
    from pyrtdd.hdd import Trace
    from pyrtdd.obspy.waveform import ObspyClientProxy, _to_utcdatetime, _to_hdd_time

    class PreprocessingSDSProxy(ObspyClientProxy):
        """Does in loadTrace() what libhdd's BasicProcessor::filter would do with a working filter():
        demean -> libhdd sinc resample -> obspy Trace.filter(kind, **float kwargs) (same call as the stock
        proxy's filter()). Batch requests are routed through loadTrace."""

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
            self.failed_by_channel_orientation = {}
            self.loaded_by_channel_type = {}

        def loadTrace(self, tw, networkCode, stationCode, locationCode, channelCode, pad=0.0):
            tr = self._fetch(networkCode, stationCode, locationCode, channelCode,
                             _to_utcdatetime(tw.startTime) - pad, _to_utcdatetime(tw.endTime) + pad)
            if tr is None:
                self.n_failed += 1
                k = channelCode[2:]
                self.failed_by_channel_orientation[k] = self.failed_by_channel_orientation.get(k, 0) + 1
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
            k = channelCode[:2]
            self.loaded_by_channel_type[k] = self.loaded_by_channel_type.get(k, 0) + 1
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

    return PreprocessingSDSProxy


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
    for k, v in SOLVER[r["solver"]].items():
        setattr(so, k, v)
    xo = XcorrOptions()
    xs = XCORR[r["xcorr"]]
    if xs is not None:
        xo.enable = True
        for k in ("minEvStaDist", "maxEvStaDist", "maxInterEvDist"):
            setattr(xo, k, xs[k])
        mk = lambda d: XcorrOptions.XCorr(d["minCoef"], d["startOffset"], d["endOffset"], d["winScaling"],
                                          d["maxDelay"], d["components"])
        xo.phase = {PT.P: mk(xs["P"]), PT.S: mk(xs["S"])}
    else:
        xo.enable = False
    # read back and assert (pybind11 STL members are easy to set by accident on a temporary copy)
    for k, v in CLUSTERING[r["clustering"]].items():
        assert getattr(co, k) == v, (k, getattr(co, k), v)
    for k, v in SOLVER[r["solver"]].items():
        assert getattr(so, k) == v, (k, getattr(so, k), v)
    if xs is not None:
        for t, key in ((PT.P, "P"), (PT.S, "S")):
            got = xo.phase[t]
            for k, v in xs[key].items():
                assert getattr(got, k) == v, (key, k, getattr(got, k), v)
    assert cfg.wfFilter.filterStr == lib_wf["filterStr"] and cfg.wfFilter.resampleFreq == lib_wf["resampleFreq"]
    return cfg, co, so, xo, wf


def xs_thr(xo, phase):
    from pyrtdd.hdd import Catalog
    return xo.phase[getattr(Catalog.Phase.Type, phase)].minCoef


def make_ttt():
    from pyrtdd.hdd import NLLGrid
    args = dict(gridPath=NLL_GRID_PATH, gridModel=NLL_GRID_MODEL, maxSearchDistance=NLL_MAX_SEARCH_DISTANCE_M,
                swapBytes=False, maxOpenFiles=NLL_MAX_OPEN_FILES, accessMethod="KeepOpen")
    return NLLGrid(**args), dict(type="NLLGrid", **args)


def make_proxy(r, wf, state):
    import obspy
    from obspy.clients.filesystem.sds import Client as SDSClient
    if r["proxy"] == "none":
        return None, dict(type="none (NoWaveformProxy: no cross-correlation)")
    t0 = time.perf_counter()
    inv = state.setdefault("inventory", obspy.read_inventory(INVENTORY_XML))
    state["inventory_read_s"] = round(time.perf_counter() - t0, 1)
    cls = make_proxy_class()
    p = cls(SDSClient(SDS), inv, False, wf["filterStr"], wf["resampleFreq"])
    desc = dict(type="PreprocessingSDSProxy(ObspyClientProxy) defined in run_pyrtdd_sanramon2026.py",
                client="obspy.clients.filesystem.sds.Client", sds=SDS, inventory=INVENTORY_XML, guess_zne=False,
                waveform_disk_cache="disabled (the proxy must see the window libhdd processes)",
                processing_actually_applied=f"demean + libhdd sinc resample (numpy port) to "
                f"{wf['resampleFreq']:g} Hz + obspy Trace.filter({p.kind!r}, **{p.kwargs}) on window +- "
                f"{wf['extraTraceLen']:g} s; then libhdd demeans again and slices",
                filter_kind=p.kind, filter_kwargs=p.kwargs, zerophase=bool(p.kwargs.get("zerophase", 0)),
                batch_loading="routed through loadTrace, no padding (multi-event mode only)")
    return p, desc


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
def run_multi(name, r, rundir, state):
    from pyrtdd.hdd import Catalog, DD, XCorrCache, Neighbours
    cfg, co, so, xo, wf = build_options(r)
    files = (STATION_CSV, EVENT_CSV, PHASE_CSV)
    cat = Catalog(*files)
    ttt, ttt_desc = make_ttt()
    proxy, proxy_desc = make_proxy(r, wf, state)
    pre = r.get("xcorr_precomputed")
    options = dict(run=name, definition=r, Config=to_jsonable(cfg), ClusteringOptions=to_jsonable(co),
                   SolverOptions=to_jsonable(so), XcorrOptions=to_jsonable(xo),
                   wffilter_requested=wf, travel_time_table=ttt_desc, waveform_proxy=proxy_desc,
                   xcorr_precomputed=(f"{OUTROOT}/{pre}/xcorr_cache.csv" if pre else None),
                   catalog_files={os.path.basename(f): dict(path=f, md5=md5(f)) for f in files},
                   start_locations="event.csv = NCSS routine locations", saveProcessing=True,
                   threads_env={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS")},
                   versions=versions())
    with open(f"{rundir}/options.json", "w") as fo:
        json.dump(options, fo, indent=1, default=str)
    dd = DD(cat, cfg, ttt, proxy) if proxy is not None else DD(cat, cfg, ttt)
    t0 = time.perf_counter()
    clusters = dd.findClusters(co)
    t_clust = time.perf_counter() - t0
    os.makedirs(f"{rundir}/clusters", exist_ok=True)
    for i, c in enumerate(clusters):
        Neighbours.writeToFile(c, cat, f"{rundir}/clusters/cluster_{i + 1}.csv")
    ncl = [len(c) for c in clusters]
    t0 = time.perf_counter()
    if xo.enable:
        if pre and r.get("xcorr_drop_negative"):
            os.makedirs(f"{rundir}/inputs", exist_ok=True)
            src = f"{OUTROOT}/{pre}/xcorr_cache.csv"
            xc = pd.read_csv(src, dtype=str, keep_default_na=False)
            coef = xc.coefficient.astype(float)
            thr = {"P": xs_thr(xo, "P"), "S": xs_thr(xo, "S")}
            neg = (xc.valid.str.lower() == "true") & (coef <= -xc.phaseType.map(thr))
            xc.loc[neg, "valid"] = "false"
            dst = f"{rundir}/inputs/xcorr_cache_positive_only.csv"
            xc.to_csv(dst, index=False)
            state["xcorr_entries_invalidated"] = {k: int(v) for k, v in xc[neg].phaseType.value_counts().items()}
            xcd = XCorrCache.readFromFile(cat, dst)
        elif pre:
            xcd = XCorrCache.readFromFile(cat, f"{OUTROOT}/{pre}/xcorr_cache.csv")
        else:
            xcd = XCorrCache()
        newcat = dd.relocateMultiEvents(clusters, xcd, xo, so, True, f"{rundir}/processing")
        xcd.writeToFile(cat, f"{rundir}/xcorr_cache.csv")
    else:
        newcat = dd.relocateMultiEvents(clusters, so, True, f"{rundir}/processing")
    t_reloc = time.perf_counter() - t0
    newcat.writeToFile(f"{rundir}/relocated-station.csv", f"{rundir}/relocated-event.csv",
                       f"{rundir}/relocated-phase.csv")
    extra = dict(n_input_events=len(cat.getEvents()), n_clusters=len(clusters), cluster_sizes=ncl,
                 n_clustered=int(sum(ncl)), n_relocated=len(newcat.getEvents()),
                 clustering_s=round(t_clust, 1), relocation_incl_xcorr_s=round(t_reloc, 1))
    if "xcorr_entries_invalidated" in state:
        extra["xcorr_entries_invalidated_negative_cc"] = state.pop("xcorr_entries_invalidated")
    if proxy is not None:
        extra.update(proxy_traces_processed=proxy.n_loaded, proxy_traces_failed=proxy.n_failed,
                     proxy_failed_by_channel_orientation=proxy.failed_by_channel_orientation,
                     proxy_loaded_by_channel_type=proxy.loaded_by_channel_type,
                     inventory_read_s=state.get("inventory_read_s"))
    return extra


# ============================================================================= main
def resolve(n):
    r = dict(RUNS[n])
    r.setdefault("proxy", "none")
    return r


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
            print(f"== {n}: {r['what']}\n   {json.dumps(r)}")
            print(f"   clustering {CLUSTERING[r['clustering']] or 'libhdd defaults'}\n   solver "
                  f"{SOLVER[r['solver']] or 'libhdd defaults'}\n   xcorr {XCORR[r['xcorr']]}\n   wffilter "
                  f"{WFFILTER[r['wffilter']]}")
        print(f"[dry run] {len(names)} runs; outputs would go to {OUTROOT}/<run>/; nothing written")
        return

    from pyrtdd.hdd import Logger
    Logger.setLevel(Logger.Level.info)
    state = {}
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    log(f"start: {len(names)} runs: {names} (pid {os.getpid()})")
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
        info = dict(run=n, what=r["what"], started=_dt.datetime.now().isoformat(timespec="seconds"),
                    host=os.uname().nodename, pid=os.getpid())
        try:
            with redirect_fd2(f"{rundir}/console.log"):
                extra = run_multi(n, r, rundir, state)
            info.update(status="ok", **extra)
        except Exception as e:
            info.update(status="failed", error=f"{type(e).__name__}: {e}", traceback=traceback.format_exc())
        info["wall_time_s"] = round(time.perf_counter() - t0, 2)
        ru = resource.getrusage(resource.RUSAGE_SELF)
        info["peak_rss_mb_process_so_far"] = round(ru.ru_maxrss / 1024, 1)
        info["cpu_user_s_process_so_far"] = round(ru.ru_utime, 1)
        info["finished"] = _dt.datetime.now().isoformat(timespec="seconds")
        with open(f"{rundir}/run_info.json", "w") as fo:
            json.dump(info, fo, indent=1, default=str)
        log(f"{n}: {info['status']} in {info['wall_time_s']:.1f} s; relocated {info.get('n_relocated')} of "
            f"{info.get('n_input_events')} (clustered {info.get('n_clustered')}, clusters {info.get('cluster_sizes')}); "
            f"peak RSS {info['peak_rss_mb_process_so_far']} MB {info.get('error', '')}")
    log("done")


if __name__ == "__main__":
    main()
