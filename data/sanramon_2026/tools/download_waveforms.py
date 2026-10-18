# download_waveforms.py -- resumable waveform downloader and builder for the San Ramon 2025-26
# benchmark (data/sanramon_2026). Copied from the 2015 tool (SR-B); only paths, log names, the
# user agent, the mainshock id and the request log changed: every request attempt is ALSO written
# to logs/sanramon2026_requests.tsv (as all other tools of this case do). Env "pyrtdd"
# (obspy 1.5.1). Run with "python -I".
#
# Two waveform sets
#   cc  cross-correlation set for rtDD. Every event of inputs/rtdd_catalog/event.csv (927) x every
#       sensor that carries an NCSS analyst pick of that event (reference_tables/picks_ncss.csv,
#       benchmark events, all weights, so every pick of phase.csv is included) at <= 60 km
#       epicentral distance (epicentre from event.csv, sensor position from inputs/stations.xml).
#       All components of that sensor that are open in stations.xml at that time (a vertical-only
#       sensor gives one trace). A sensor without metadata is asked with a wildcard ("HN?") and its
#       distance is the Hypoinverse one from the pick line.
#       Window origin-10 s .. origin+30 s. Output: SDS archive inputs/sds/
#       YEAR/NET/STA/CHA.D/NET.STA.LOC.CHA.D.YEAR.DOY, one file per channel and UTC day, all event
#       windows of that day merged (obspy cleanup merge), no overlapping traces, 512-byte records.
#   dl  DL-picker set. The events of inputs/dl_subset_events.csv (26) x every channel of
#       inputs/stations.xml (open at that time) of every sensor <= 80 km from the epicentre, with
#       or without picks. Window origin-120 s .. origin+120 s. Output: inputs/playback/<id>.mseed,
#       one file per event, 512-byte records sorted by record end time (what "scmssort -E" does).
#   All windows are half-open [start, end): a sample exactly at "end" is not kept (NCEDC does the
#   same).
#
# Sources and politeness
#   * NCEDC first: obspy FDSN client (Client("NCEDC")), fdsnws/dataselect bulk POST, one request
#     per event (dl: per event in chunks of <= DL_CHUNK lines).
#   * EarthScope fallback (Client("EARTHSCOPE")) for every plan line (event x channel) that NCEDC
#     answered with no data at all in its window. EarthScope retired its availability service and
#     station?matchtimeseries (HTTP 404/410, tools/19_probe_waveform_services.py), so we cannot ask
#     what it holds; instead all missing lines go to EarthScope as a few large bulk requests
#     (windows of one channel that overlap or touch are joined into one line; <= FALLBACK_CHUNK
#     lines per request, in time order). The answers are kept as served; the builder takes from
#     them, for each event, only the channels that event was missing at NCEDC.
#   * At most WORKERS (2) requests at a time over both services, >= MIN_GAP_S between request
#     starts; up to MAX_TRIES attempts with exponential back-off (5, 10, 20, 40, 80 s, +-20 %;
#     >= 60 s after HTTP 429/503); 204 (no data) and other 4xx answers are final.
#   * Every attempt is logged (UTC time, service, set, event, chunk, lines, attempt, HTTP status,
#     bytes, seconds, URL) in logs/sanramon2026_waveforms_20261018.log and as one row of
#     logs/sanramon2026_requests.tsv.
#
# Resumable, no partial files
#   Raw answers: reference/waveforms_raw/<set>/ncedc/<eventid>_c<k>.mseed and
#   reference/waveforms_raw/<set>/earthscope/batch_c<k>.mseed, each with a .json manifest
#   (request lines, status, bytes, seconds; for EarthScope also the events each line serves). A request counts as done when its manifest exists with
#   status 200 (and the mseed file has the recorded size) or 204, and its request lines equal the
#   current plan; re-runs skip it. Every file is written as *.part, read back, then renamed. Stale
#   *.part files are removed at start. SDS day files and playback files are rebuilt from the raw
#   answers (deterministic); a build manifest (reference/waveforms_raw/build_<set>.json) lets re-runs
#   skip outputs whose inputs did not change.
#
# Steps (default all, in this order)
#   plan      request tables reference_tables/waveform_requests_{cc,dl}.csv
#   ncedc     NCEDC requests
#   fallback  EarthScope bulk requests for the plan lines without NCEDC data
#   build     SDS archive (cc) / playback files (dl); per-trace source table
#             reference_tables/waveform_sources_{cc,dl}.csv
# A file reference/waveforms_raw/DONE_<set> is written when all steps of a set ended without a
# failed request.
# Usage
#   python -I download_waveforms.py [--set cc|dl|both] [--steps plan,ncedc,fallback,build]
#                                   [--limit N] [--workers 1|2]
#   (--limit N: only the first N events of each set, for tests; no DONE file then)
#   long run: nohup python -I download_waveforms.py > logs/sanramon2026_waveforms_console.log 2>&1 &

import argparse
import concurrent.futures as cf
import fnmatch
import glob
import json
import logging
import os
import random
import sys
import threading
import time
from collections import defaultdict

import numpy as np
import pandas as pd
from obspy import Stream, Trace, UTCDateTime, read, read_inventory
from obspy.core.util import AttribDict
from obspy.clients.fdsn import Client
from obspy.clients.fdsn import header as fh
from obspy.io.mseed.util import get_record_information
from pyproj import Geod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402  (paths only)

TOOL = "download_waveforms"
RAW = os.path.join(C.REF, "waveforms_raw")
SDS = os.path.join(C.INP, "sds")
PLAYBACK = os.path.join(C.INP, "playback")
LOG = os.path.join(C.LOGS, "sanramon2026_waveforms_20261018.log")
STATIONXML = os.path.join(C.INP, "stations.xml")

CC_MAX_KM, CC_WIN = 60.0, (-10.0, 30.0)
DL_MAX_KM, DL_WIN = 80.0, (-120.0, 120.0)
CC_CHUNK = 500        # lines per request (cc: max 409 lines per event, so one request per event)
DL_CHUNK = 240        # lines per request (dl: ~687 lines per event -> 3 requests per event)
FALLBACK_CHUNK = 500   # lines per EarthScope fallback request
WORKERS = 2           # never more than 2 requests at a time
MIN_GAP_S = 0.5       # between two request starts
MAX_TRIES = 6
BACKOFF_S = 5.0
TIMEOUT_S = 600
RECLEN = 512
USER_AGENT = ("SanRamon2026-rtDD-benchmark (ObsPy 1.5.1 FDSN client; research use; "
              "<= 2 concurrent requests)")
SERVICES = {"ncedc": "NCEDC", "earthscope": "EARTHSCOPE"}

log = logging.getLogger(TOOL)
_sem = threading.BoundedSemaphore(WORKERS)
_gap_lock = threading.Lock()
_last_start = [0.0]
_tls = threading.local()


# ------------------------------------------------------------------ helpers
def setup_logging():
    os.makedirs(C.LOGS, exist_ok=True)
    logging.Formatter.converter = time.gmtime
    fmt = logging.Formatter("%(asctime)sZ %(levelname)s [%(threadName)s] %(message)s",
                            datefmt="%Y-%m-%dT%H:%M:%S")
    log.setLevel(logging.INFO)
    for h in (logging.FileHandler(LOG), logging.StreamHandler(sys.stdout)):
        h.setFormatter(fmt)
        log.addHandler(h)


def rel(path):
    return os.path.relpath(path, C.PROJECT)


def write_json_atomic(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    part = path + ".part"
    with open(part, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(part, path)


def remove_stale_parts():
    """*.part files of this tool only (raw answers, SDS, playback, waveform_* tables)"""
    n = 0
    for root in (RAW, SDS, PLAYBACK, C.TAB):
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if fn.endswith(".part") and (root != C.TAB or fn.startswith("waveform_")):
                    os.remove(os.path.join(dirpath, fn))
                    n += 1
    if n:
        log.info("removed %d stale *.part files from an interrupted run", n)


def loc_q(loc):
    return loc if loc else "--"


def line_str(net, sta, loc, cha, t0, t1):
    return f"{net} {sta} {loc_q(loc)} {cha} {UTCDateTime(t0).strftime('%Y-%m-%dT%H:%M:%S.%f')} " \
           f"{UTCDateTime(t1).strftime('%Y-%m-%dT%H:%M:%S.%f')}"


# ------------------------------------------------------------------ plan
def metadata_table():
    """One row per channel epoch of inputs/stations.xml."""
    inv = read_inventory(STATIONXML, format="STATIONXML")
    rows = []
    for net in inv:
        for sta in net:
            for ch in sta:
                rows.append(dict(network=net.code, station=sta.code, location=ch.location_code,
                                 channel=ch.code, t0=ch.start_date,
                                 t1=ch.end_date if ch.end_date is not None else UTCDateTime(3000, 1, 1),
                                 latitude=ch.latitude, longitude=ch.longitude, dip=ch.dip,
                                 sample_rate=ch.sample_rate))
    md = pd.DataFrame(rows)
    md["group"] = md.channel.str[:2]
    md["t0_ns"] = [t.ns for t in md.t0]   # integer times: pandas cannot sort UTCDateTime objects
    md["t1_ns"] = [t.ns for t in md.t1]
    return md


def open_channels(md_by_group, key, t0, t1):
    """channels of sensor 'key' (net, sta, loc, group) whose epoch overlaps [t0, t1)"""
    g = md_by_group.get(key)
    if g is None:
        return []
    out = [r for r in g if r["t0"] < t1 and r["t1"] > t0]
    # one row per channel code (an epoch boundary inside the window would give two)
    seen, res = set(), []
    for r in sorted(out, key=lambda r: (r["channel"], r["t0"])):
        if r["channel"] not in seen:
            seen.add(r["channel"])
            res.append(r)
    return res


def make_plan():
    geod = Geod(ellps="WGS84")
    ev = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "event.csv"))
    ev = ev.set_index("id")
    origin = {int(i): UTCDateTime(t) for i, t in ev.isotime.items()}
    picks = pd.read_csv(os.path.join(C.TAB, "picks_ncss.csv"), keep_default_na=False,
                        dtype={"location": str, "location_raw": str})
    picks = picks[picks.benchmark_event.astype(str) == "True"].copy()
    picks["group"] = picks.channel.str[:2]
    md = metadata_table()
    md_by_group = defaultdict(list)
    for r in md.to_dict("records"):
        md_by_group[(r["network"], r["station"], r["location"], r["group"])].append(r)
    log.info("stations.xml: %d channel epochs, %d channels", len(md),
             md[["network", "station", "location", "channel"]].drop_duplicates().shape[0])

    # ---- cc
    rows = []
    for eid, pp in picks.groupby("event_id"):
        eid = int(eid)
        if eid not in origin:
            continue
        o = origin[eid]
        ws, we = o + CC_WIN[0], o + CC_WIN[1]
        elat, elon = float(ev.loc[eid, "latitude"]), float(ev.loc[eid, "longitude"])
        for (net, sta, loc, grp), gp in pp.groupby(["network", "station", "location", "group"]):
            chans = open_channels(md_by_group, (net, sta, loc, grp), ws, we)
            npick = gp.groupby("channel").size().to_dict()
            if chans:
                _, _, d = geod.inv(elon, elat, chans[0]["longitude"], chans[0]["latitude"])
                dist, dist_src = d / 1000.0, "stations.xml"
            else:
                dist, dist_src = float(np.median(gp.epi_dist_km.astype(float))), "hypoinverse"
            if dist > CC_MAX_KM:
                continue
            base = dict(set="cc", event_id=eid, origin_time=str(o), start=str(ws), end=str(we),
                        network=net, station=sta, location=loc, sensor=f"{net}.{sta}.{loc}.{grp}",
                        dist_km=round(dist, 3), dist_source=dist_src)
            for c in chans:
                rows.append(dict(base, channel=c["channel"], has_metadata=True, wildcard=False,
                                 sample_rate=c["sample_rate"], dip=c["dip"],
                                 picked_channel=c["channel"] in npick,
                                 n_picks_channel=int(npick.get(c["channel"], 0))))
            if not chans:
                rows.append(dict(base, channel=grp + "?", has_metadata=False, wildcard=True,
                                 sample_rate=np.nan, dip=np.nan, picked_channel=True,
                                 n_picks_channel=int(len(gp))))
            else:
                for pc in sorted(set(npick) - {c["channel"] for c in chans}):
                    rows.append(dict(base, channel=pc, has_metadata=False, wildcard=False,
                                     sample_rate=np.nan, dip=np.nan, picked_channel=True,
                                     n_picks_channel=int(npick[pc])))
    cc = pd.DataFrame(rows)

    # ---- dl
    dls = pd.read_csv(os.path.join(C.INP, "dl_subset_events.csv"))
    picked_by_event = defaultdict(lambda: defaultdict(int))  # event -> (net,sta,loc,cha) -> n
    for r in picks.itertuples():
        picked_by_event[int(r.event_id)][(r.network, r.station, r.location, r.channel)] += 1
    rows = []
    for eid in dls.event_id.astype(int):
        o = origin[eid]
        ws, we = o + DL_WIN[0], o + DL_WIN[1]
        elat, elon = float(ev.loc[eid, "latitude"]), float(ev.loc[eid, "longitude"])
        m = md[(md.t0_ns < we.ns) & (md.t1_ns > ws.ns)]
        m = m.sort_values(["network", "station", "location", "channel", "t0_ns"]).drop_duplicates(
            ["network", "station", "location", "channel"])
        _, _, d = geod.inv(np.full(len(m), elon), np.full(len(m), elat),
                           m.longitude.astype(float).values, m.latitude.astype(float).values)
        m = m.assign(dist_km=np.round(np.asarray(d) / 1000.0, 3))
        # sensor distance = distance of its first channel (all channels of a sensor share a place)
        sd = m.groupby(["network", "station", "location", "group"]).dist_km.transform("first")
        m = m[sd <= DL_MAX_KM]
        pk = picked_by_event[eid]
        for r in m.itertuples():
            npk = int(pk.get((r.network, r.station, r.location, r.channel), 0))
            rows.append(dict(set="dl", event_id=eid, origin_time=str(o), start=str(ws), end=str(we),
                             network=r.network, station=r.station, location=r.location,
                             sensor=f"{r.network}.{r.station}.{r.location}.{r.group}",
                             dist_km=r.dist_km, dist_source="stations.xml", channel=r.channel,
                             has_metadata=True, wildcard=False, sample_rate=r.sample_rate,
                             dip=r.dip, picked_channel=npk > 0, n_picks_channel=npk))
    dl = pd.DataFrame(rows)
    for df, chunk in ((cc, CC_CHUNK), (dl, DL_CHUNK)):
        df.sort_values(["event_id", "network", "station", "location", "channel"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        k = df.groupby("event_id").cumcount()
        n = df.groupby("event_id").event_id.transform("size")
        nchunk = np.ceil(n / chunk).astype(int)
        size = np.ceil(n / nchunk).astype(int)
        df["chunk"] = (k // size).astype(int)
    cols = ["set", "event_id", "origin_time", "start", "end", "chunk", "network", "station",
            "location", "channel", "sensor", "dist_km", "dist_source", "has_metadata", "wildcard",
            "sample_rate", "dip", "picked_channel", "n_picks_channel"]
    for name, df in (("cc", cc), ("dl", dl)):
        path = os.path.join(C.TAB, f"waveform_requests_{name}.csv")
        df[cols].to_csv(path + ".part", index=False)
        os.replace(path + ".part", path)
        log.info("plan %s: %d events, %d request lines, %d requests, %d distinct channels -> %s",
                 name, df.event_id.nunique(), len(df),
                 df[["event_id", "chunk"]].drop_duplicates().shape[0],
                 df[["network", "station", "location", "channel"]].drop_duplicates().shape[0],
                 rel(path))
    return cc, dl


def load_plan(name):
    return pd.read_csv(os.path.join(C.TAB, f"waveform_requests_{name}.csv"),
                       keep_default_na=False, dtype={"location": str},
                       converters={"has_metadata": lambda x: x == "True",
                                   "wildcard": lambda x: x == "True",
                                   "picked_channel": lambda x: x == "True"})


# ------------------------------------------------------------------ download
def client(service):
    c = getattr(_tls, service, None)
    if c is None:
        c = Client(SERVICES[service], user_agent=USER_AGENT, timeout=TIMEOUT_S,
                   _discover_services=False)
        setattr(_tls, service, c)
    return c


def _status_of(exc):
    table = [("FDSNNoDataException", 204), ("FDSNBadRequestException", 400),
             ("FDSNUnauthorizedException", 401), ("FDSNForbiddenException", 403),
             ("FDSNRequestTooLargeException", 413), ("FDSNTooManyRequestsException", 429),
             ("FDSNInternalServerException", 500), ("FDSNNotImplementedException", 501),
             ("FDSNBadGatewayException", 502), ("FDSNServiceUnavailableException", 503),
             ("FDSNTimeoutException", "TIMEOUT")]
    for name, code in table:
        cls = getattr(fh, name, None)
        if cls is not None and isinstance(exc, cls):
            return code
    msg = str(exc)
    if "Unknown HTTP code:" in msg:
        try:
            return int(msg.split("Unknown HTTP code:")[1].split()[0].strip("',)"))
        except ValueError:
            pass
    return "ERR"


def raw_paths(set_, service, eid, chunk):
    base = os.path.join(RAW, set_, service, f"{eid}_c{chunk:02d}")
    return base + ".mseed", base + ".json"


def is_done(js, lines):
    if not os.path.exists(js):
        return False
    try:
        m = json.load(open(js))
    except (OSError, ValueError):
        return False
    if m.get("lines") != lines:
        return False
    if m.get("status") == 204:
        return True
    if m.get("status") == 200:
        p = os.path.join(C.PROJECT, m["file"])
        return os.path.exists(p) and os.path.getsize(p) == m["bytes"]
    return False


def fetch(task):
    """task: dict(set, service, event_id, chunk, lines(list of str), bulk(list of tuples))
    returns 'skip' | 200 | 204 | 'failed:<status>'"""
    mseed, js = task["mseed"], task["json"]
    if is_done(js, task["lines"]):
        return "skip"
    os.makedirs(os.path.dirname(mseed), exist_ok=True)
    part = mseed + ".part"
    url = client(task["service"])._build_url("dataselect", "query")
    status = None
    for attempt in range(1, MAX_TRIES + 1):
        note = ""
        with _sem:
            with _gap_lock:
                gap = time.time() - _last_start[0]
                if gap < MIN_GAP_S:
                    time.sleep(MIN_GAP_S - gap)
                _last_start[0] = time.time()
            t0 = time.time()
            try:
                client(task["service"]).get_waveforms_bulk(task["bulk"], filename=part)
                status = 200
            except Exception as e:  # noqa: BLE001  (every failure is logged and classified)
                status = _status_of(e)
                if status not in (204,):
                    note = f"{type(e).__name__}: {str(e)[:200]}".replace("\n", " ")
            secs = time.time() - t0
        nbytes = os.path.getsize(part) if (status == 200 and os.path.exists(part)) else 0
        ntr = ""
        if status == 200:
            try:
                st = read(part, format="MSEED", headonly=True)
                ntr = len(st)
                if nbytes == 0 or ntr == 0:
                    status, note = "EMPTY200", "HTTP 200 without miniSEED records"
            except Exception as e:  # noqa: BLE001
                status, note = "BADMSEED", f"{type(e).__name__}: {str(e)[:200]}"
        log.info("REQUEST service=%s set=%s event=%s chunk=%d lines=%d attempt=%d status=%s "
                 "bytes=%d seconds=%.2f traces=%s url=%s file=%s%s", task["service"], task["set"],
                 task["event_id"], task["chunk"], len(task["lines"]), attempt, status, nbytes, secs,
                 ntr, url, rel(mseed) if status == 200 else "-", f" note={note}" if note else "")
        C.log_request(TOOL, "POST", url, f"<bulk: {len(task['lines'])} lines; set {task['set']}, "
                      f"event {task['event_id']}, chunk {task['chunk']}; request in "
                      f"{rel(js)}>", status, nbytes, secs,
                      mseed if status == 200 else "", attempt, note)
        if status == 200:
            os.replace(part, mseed)
            write_json_atomic(dict(set=task["set"], service=task["service"],
                                   event_id=int(task["event_id"]), chunk=int(task["chunk"]),
                                   url=url, status=200, bytes=nbytes, seconds=round(secs, 2),
                                   attempts=attempt, traces=ntr, file=rel(mseed),
                                   utc=str(UTCDateTime()), lines=task["lines"],
                                   **task.get("extra", {})), js)
            return 200
        if os.path.exists(part):
            os.remove(part)
        if status == 204:
            write_json_atomic(dict(set=task["set"], service=task["service"],
                                   event_id=int(task["event_id"]), chunk=int(task["chunk"]),
                                   url=url, status=204, bytes=0, seconds=round(secs, 2),
                                   attempts=attempt, traces=0, file=None, utc=str(UTCDateTime()),
                                   lines=task["lines"], **task.get("extra", {})), js)
            return 204
        if isinstance(status, int) and 400 <= status < 500 and status != 429:
            break  # a definite answer; retrying will not change it
        if attempt < MAX_TRIES:
            wait = BACKOFF_S * 2 ** (attempt - 1) * random.uniform(0.8, 1.2)
            if status in (429, 503):
                wait = max(wait, 60.0)
            log.info("retry in %.0f s (event %s chunk %d, status %s)", wait, task["event_id"],
                     task["chunk"], status)
            time.sleep(wait)
    log.error("FAILED service=%s set=%s event=%s chunk=%d status=%s", task["service"],
              task["set"], task["event_id"], task["chunk"], status)
    return f"failed:{status}"


def tasks_from_plan(df, set_, service):
    tasks = []
    for (eid, chunk), g in df.groupby(["event_id", "chunk"], sort=True):
        bulk = [(r.network, r.station, r.location, r.channel, UTCDateTime(r.start),
                 UTCDateTime(r.end)) for r in g.itertuples()]
        lines = [line_str(*b) for b in bulk]
        mseed, js = raw_paths(set_, service, int(eid), int(chunk))
        tasks.append(dict(set=set_, service=service, event_id=int(eid), chunk=int(chunk),
                          bulk=bulk, lines=lines, mseed=mseed, json=js))
    return tasks


def run_tasks(tasks, workers):
    res = defaultdict(int)
    failed = []
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=workers, thread_name_prefix="dl") as ex:
        futs = {ex.submit(fetch, t): t for t in tasks}
        for k, f in enumerate(cf.as_completed(futs), 1):
            t = futs[f]
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001
                r = f"failed:{type(e).__name__}"
                log.exception("task crashed: %s %s", t["event_id"], t["chunk"])
            res[str(r).split(":")[0]] += 1
            if str(r).startswith("failed"):
                failed.append((t["set"], t["service"], t["event_id"], t["chunk"], r))
            if k % 25 == 0 or k == len(tasks):
                log.info("progress %d/%d tasks (%s) %.0f s", k, len(tasks), dict(res),
                         time.time() - t0)
    return dict(res), failed


# ------------------------------------------------------------------ fallback
def raw_spans(set_, service, eid):
    """{trace id: [(start, end)]} of the raw answers of one event (header only)"""
    spans = defaultdict(list)
    for js in sorted(glob.glob(os.path.join(RAW, set_, service, f"{eid}_c*.json"))):
        m = json.load(open(js))
        if m.get("status") != 200:
            continue
        for tr in read(os.path.join(C.PROJECT, m["file"]), format="MSEED", headonly=True):
            spans[tr.id].append((tr.stats.starttime, tr.stats.endtime))
    return spans


def missing_rows(df, set_, service="ncedc"):
    """plan rows without any data overlapping their window in the raw answers of 'service'"""
    miss = []
    for eid, g in df.groupby("event_id"):
        spans = raw_spans(set_, service, int(eid))
        for r in g.itertuples():
            ws, we = UTCDateTime(r.start), UTCDateTime(r.end)
            pat = f"{r.network}.{r.station}.{r.location}.{r.channel}"
            ids = fnmatch.filter(spans.keys(), pat) if r.wildcard else ([pat] if pat in spans else [])
            ok = any(a < we and b >= ws for i in ids for a, b in spans[i])
            if not ok:
                miss.append(r.Index)
    return df.loc[miss]


def fallback(df, set_, workers):
    """EarthScope bulk requests for every plan line without NCEDC data (see header)."""
    miss = missing_rows(df, set_)
    log.info("fallback %s: %d of %d plan lines have no NCEDC data (%d channels, %d events)", set_,
             len(miss), len(df), miss[["network", "station", "location", "channel"]
                                       ].drop_duplicates().shape[0], miss.event_id.nunique())
    lines = []
    for (net, sta, loc, cha), g in miss.groupby(["network", "station", "location", "channel"]):
        wins = sorted((UTCDateTime(r.start), UTCDateTime(r.end), int(r.event_id))
                      for r in g.itertuples())
        cur = [wins[0][0], wins[0][1], [wins[0][2]]]
        for a, b, e in wins[1:]:
            if a <= cur[1]:
                cur[1] = max(cur[1], b)
                cur[2].append(e)
            else:
                lines.append((net, sta, loc, cha, cur[0], cur[1], cur[2]))
                cur = [a, b, [e]]
        lines.append((net, sta, loc, cha, cur[0], cur[1], cur[2]))
    lines.sort(key=lambda x: (x[4].ns, x[0], x[1], x[2], x[3]))
    nchunk = int(np.ceil(len(lines) / FALLBACK_CHUNK))
    size = int(np.ceil(len(lines) / nchunk)) if nchunk else 0
    tasks = []
    for k in range(nchunk):
        part = lines[k * size:(k + 1) * size]
        bulk = [x[:6] for x in part]
        mseed = os.path.join(RAW, set_, "earthscope", f"batch_c{k:02d}.mseed")
        tasks.append(dict(set=set_, service="earthscope", event_id=0, chunk=k, bulk=bulk,
                          lines=[line_str(*b) for b in bulk], mseed=mseed,
                          json=mseed[:-len(".mseed")] + ".json",
                          extra=dict(line_events=[x[6] for x in part])))
    # answers of an earlier fallback plan with more chunks would be read by the builder: remove
    for js in glob.glob(os.path.join(RAW, set_, "earthscope", "batch_c*.json")):
        k = int(os.path.basename(js)[len("batch_c"):-len(".json")])
        if k >= nchunk:
            for p in (js, js[:-len(".json")] + ".mseed"):
                if os.path.exists(p):
                    os.remove(p)
            log.info("removed stale fallback answer %s", rel(js))
    log.info("fallback %s: %d EarthScope lines (joined windows) in %d requests", set_, len(lines),
             nchunk)
    res, failed = run_tasks(tasks, workers) if tasks else ({}, [])
    held = set()
    for t in tasks:
        if is_done(t["json"], t["lines"]) and os.path.exists(t["mseed"]):
            held.update(tr.id for tr in read(t["mseed"], format="MSEED", headonly=True))
    log.info("fallback %s: EarthScope answered with data for %d channels", set_, len(held))
    _FALLBACK.pop(set_, None)
    return res, failed, miss, held


# ------------------------------------------------------------------ build
_FALLBACK = {}


def fallback_answers(set_):
    """EarthScope batch answers of a set: (Stream, {event: set of trace patterns}, [[file, bytes]])"""
    if set_ not in _FALLBACK:
        st, idx, files = Stream(), defaultdict(set), []
        for js in sorted(glob.glob(os.path.join(RAW, set_, "earthscope", "batch_c*.json"))):
            m = json.load(open(js))
            if m.get("status") != 200:
                continue
            s = read(os.path.join(C.PROJECT, m["file"]), format="MSEED")
            for tr in s:
                tr.stats.source_service = "earthscope"
            st += s
            files.append([m["file"], m["bytes"]])
            for line, evs in zip(m["lines"], m["line_events"]):
                net, sta, loc, cha = line.split()[:4]
                pat = f"{net}.{sta}.{'' if loc == '--' else loc}.{cha}"
                for e in evs:
                    idx[int(e)].add(pat)
        _FALLBACK[set_] = (st, idx, files)
    return _FALLBACK[set_]


def read_raw_event(set_, eid, ws, we):
    """NCEDC answers of one event + the EarthScope traces of the channels it was missing"""
    st = Stream()
    inputs = []
    for js in sorted(glob.glob(os.path.join(RAW, set_, "ncedc", f"{eid}_c*.json"))):
        m = json.load(open(js))
        if m.get("status") != 200:
            continue
        s = read(os.path.join(C.PROJECT, m["file"]), format="MSEED")
        for tr in s:
            tr.stats.source_service = "ncedc"
        st += s
        inputs.append([m["file"], m["bytes"]])
    fst, idx, files = fallback_answers(set_)
    pats = idx.get(int(eid))
    if pats:
        for tr in fst:
            if tr.stats.starttime < we and tr.stats.endtime >= ws and \
                    any(fnmatch.fnmatch(tr.id, p) for p in pats):
                st.append(tr)
        inputs.extend(files)
    return st, inputs


def cut(tr, a, b):
    """samples with a <= t < b, as a new trace (None if empty)"""
    sr = tr.stats.sampling_rate
    t0 = tr.stats.starttime
    i0 = max(0, int(np.ceil((a - t0) * sr - 1e-6)))
    i1 = min(tr.stats.npts, int(np.ceil((b - t0) * sr - 1e-6)))
    if i1 <= i0:
        return None
    hdr = tr.stats.copy()
    hdr.npts = i1 - i0          # obspy keeps a header's npts when a Trace is built from it
    hdr.starttime = t0 + i0 / sr
    out = Trace(data=tr.data[i0:i1].copy(), header=hdr)
    if out.stats.npts != len(out.data):
        raise RuntimeError(f"cut(): npts mismatch for {tr.id}")
    return out


def merge_no_overlap(traces):
    """cleanup merge (identical overlaps and adjacent pieces are joined), then any remaining
    overlap is removed by cutting the later trace. Returns (Stream, n_overlaps_cut)."""
    st = Stream(traces)
    st.merge(method=-1)
    st.sort(["starttime", "endtime"])
    out, ncut = [], 0
    for tr in st:
        if out and tr.stats.starttime <= out[-1].stats.endtime:
            ncut += 1
            tr = cut(tr, out[-1].stats.endtime + 0.5 * tr.stats.delta,
                     tr.stats.endtime + tr.stats.delta)
            if tr is None:
                continue
        out.append(tr)
    res = Stream(out)
    if ncut:
        res.merge(method=-1)  # pieces made adjacent by the cut are joined again
        res.sort(["starttime", "endtime"])
    return res, ncut


def per_id_summary(stream):
    """{id: (samples, first start ns, last end ns, number of overlaps, all samples)}"""
    d = defaultdict(list)
    for tr in stream:
        d[tr.id].append(tr)
    out = {}
    for k, trs in d.items():
        trs.sort(key=lambda t: (t.stats.starttime.ns, t.stats.endtime.ns))
        nov = sum(1 for a, b in zip(trs, trs[1:]) if b.stats.starttime <= a.stats.endtime)
        out[k] = (sum(t.stats.npts for t in trs), trs[0].stats.starttime.ns,
                  trs[-1].stats.endtime.ns, nov, np.concatenate([t.data for t in trs]))
    return out


def write_mseed_atomic(st, path, sort_records=False):
    """write 512-byte records (Steim2 for integer data; Steim1 / INT32 if Steim2 fails; obspy's
    choice for float data), keep each trace's data-quality letter, read the file back and compare
    per channel: sample count, first and last sample time, all samples, no overlapping traces;
    then rename *.part -> path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    part = path + ".part"
    tmp = path + ".unsorted.part"
    target = tmp if sort_records else part
    for tr in st:
        q = tr.stats.get("mseed", {}).get("dataquality", "D")
        tr.stats.mseed = AttribDict({"dataquality": q})
    ints = all(tr.data.dtype == np.int32 for tr in st)
    encs = ("STEIM2", "STEIM1", "INT32") if ints else (None,)
    for k, enc in enumerate(encs):
        try:
            if enc is None:
                st.write(target, format="MSEED", reclen=RECLEN)
            else:
                st.write(target, format="MSEED", reclen=RECLEN, encoding=enc)
            break
        except Exception as e:  # noqa: BLE001
            if os.path.exists(target):
                os.remove(target)
            if k == len(encs) - 1:
                raise
            log.warning("writing %s with %s failed (%s), trying %s", rel(path), enc, e,
                        encs[k + 1])
    if sort_records:
        sort_records_by_endtime(tmp, part)
        os.remove(tmp)
    want = per_id_summary(st)
    have = per_id_summary(read(part, format="MSEED"))
    if set(want) != set(have) or not all(
            want[k][:3] == have[k][:3] and have[k][3] == 0 and np.array_equal(want[k][4], have[k][4])
            for k in want):
        os.remove(part)
        raise RuntimeError(f"read-back of {path} differs from what was written (or overlaps)")
    if os.path.getsize(part) % RECLEN:
        os.remove(part)
        raise RuntimeError(f"{path}: size is not a multiple of {RECLEN}")
    os.replace(part, path)
    return os.path.getsize(path)


def sort_records_by_endtime(src, dst):
    """fixed-length records sorted by (end time, start time, stream id), like scmssort -E"""
    size = os.path.getsize(src)
    recs = []
    with open(src, "rb") as f:
        off = 0
        while off < size:
            info = get_record_information(f, offset=off)
            n = info["record_length"]
            sid = f"{info['network']}.{info['station']}.{info['location']}.{info['channel']}"
            recs.append((info["endtime"].ns, info["starttime"].ns, sid, off, n))
            off += n
    recs.sort()
    with open(src, "rb") as f, open(dst, "wb") as g:
        for _, _, _, off, n in recs:
            f.seek(off)
            g.write(f.read(n))


def sds_path(tid, day):
    net, sta, loc, cha = tid.split(".")
    y, j = day.year, day.julday
    return os.path.join(SDS, f"{y}", net, sta, f"{cha}.D", f"{net}.{sta}.{loc}.{cha}.D.{y}.{j:03d}")


def allowed_fn(df):
    """event id -> function(trace id) telling whether that trace was asked for"""
    exact, wild = defaultdict(set), defaultdict(list)
    for r in df.itertuples():
        pat = f"{r.network}.{r.station}.{r.location}.{r.channel}"
        (wild[r.event_id].append(pat) if r.wildcard else exact[r.event_id].add(pat))
    return lambda eid, tid: tid in exact[eid] or any(fnmatch.fnmatch(tid, p) for p in wild[eid])


def build_cc(df):
    mpath = os.path.join(RAW, "build_cc.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    wins = {int(e): (UTCDateTime(g.start.iloc[0]), UTCDateTime(g.end.iloc[0]))
            for e, g in df.groupby("event_id")}
    allowed = allowed_fn(df)
    day_events = defaultdict(list)
    for eid, (ws, we) in wins.items():
        d = UTCDateTime(ws.date)
        while d < we:
            day_events[str(d.date)].append(eid)
            d += 86400
    src_rows, n_unexp, n_cut, n_written, n_skipped = [], 0, 0, 0, 0
    cache = {}
    for day in sorted(day_events):
        d0 = UTCDateTime(day)
        d1 = d0 + 86400
        eids = sorted(day_events[day], key=lambda e: (wins[e][0], e))
        pieces = defaultdict(list)
        sig = []
        for eid in eids:
            if eid not in cache:
                # keep only the latest event: one that spans midnight is the last event of a day
                # and the first of the next
                cache.clear()
                cache[eid] = read_raw_event("cc", eid, *wins[eid])
            st, inputs = cache[eid]
            sig.extend(inputs)
            ws, we = wins[eid]
            a, b = max(ws, d0), min(we, d1)
            for tr in st:
                if not allowed(eid, tr.id):
                    n_unexp += 1
                    continue
                p = cut(tr, a, b)
                if p is not None:
                    pieces[tr.id].append(p)
                    src_rows.append((eid, tr.id, tr.stats.source_service, str(p.stats.starttime),
                                     str(p.stats.endtime), p.stats.npts, p.stats.sampling_rate))
        prev = manifest.get(day)
        outs = {tid: sds_path(tid, d0) for tid in pieces}
        if prev and prev.get("inputs") == sig and all(
                os.path.exists(p) and os.path.getsize(p) == prev["outputs"].get(rel(p))
                for p in outs.values()) and len(prev["outputs"]) == len(outs):
            n_skipped += len(outs)
            continue
        written = {}
        for tid, lst in sorted(pieces.items()):
            st, nc = merge_no_overlap(lst)
            n_cut += nc
            written[rel(outs[tid])] = write_mseed_atomic(st, outs[tid])
            n_written += 1
        manifest[day] = dict(inputs=sig, outputs=written)
        write_json_atomic(manifest, mpath)
        log.info("build cc %s: %d events, %d day files", day, len(eids), len(written))
    src = pd.DataFrame(src_rows, columns=["event_id", "trace_id", "service", "start", "end", "npts",
                                          "sampling_rate"])
    path = os.path.join(C.TAB, "waveform_sources_cc.csv")
    src.to_csv(path + ".part", index=False)
    os.replace(path + ".part", path)
    log.info("build cc done: %d day files written, %d unchanged, %d unexpected traces dropped, "
             "%d remaining overlaps cut", n_written, n_skipped, n_unexp, n_cut)
    return dict(day_files_written=n_written, day_files_unchanged=n_skipped,
                unexpected_traces=n_unexp, overlaps_cut=n_cut)


def build_dl(df):
    mpath = os.path.join(RAW, "build_dl.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    allowed = allowed_fn(df)
    src_rows, n_unexp, n_cut, n_written, n_skipped = [], 0, 0, 0, 0
    for eid, g in df.groupby("event_id"):
        eid = int(eid)
        ws, we = UTCDateTime(g.start.iloc[0]), UTCDateTime(g.end.iloc[0])
        out = os.path.join(PLAYBACK, f"{eid}.mseed")
        st, sig = read_raw_event("dl", eid, ws, we)
        prev = manifest.get(str(eid))
        if prev and prev.get("inputs") == sig and os.path.exists(out) and \
                os.path.getsize(out) == prev.get("bytes"):
            n_skipped += 1
            continue
        pieces = defaultdict(list)
        for tr in st:
            if not allowed(eid, tr.id):
                n_unexp += 1
                continue
            p = cut(tr, ws, we)
            if p is not None:
                pieces[tr.id].append(p)
                src_rows.append((eid, tr.id, tr.stats.source_service, str(p.stats.starttime),
                                 str(p.stats.endtime), p.stats.npts, p.stats.sampling_rate))
        allst = Stream()
        for tid, lst in sorted(pieces.items()):
            s, nc = merge_no_overlap(lst)
            n_cut += nc
            allst += s
        nbytes = write_mseed_atomic(allst, out, sort_records=True)
        manifest[str(eid)] = dict(inputs=sig, bytes=nbytes)
        write_json_atomic(manifest, mpath)
        n_written += 1
        log.info("build dl %d: %d traces (%d channels), %.1f MB", eid, len(allst), len(pieces),
                 nbytes / 1e6)
    if src_rows or not os.path.exists(os.path.join(C.TAB, "waveform_sources_dl.csv")):
        src = pd.DataFrame(src_rows, columns=["event_id", "trace_id", "service", "start", "end",
                                              "npts", "sampling_rate"])
        path = os.path.join(C.TAB, "waveform_sources_dl.csv")
        if n_skipped and os.path.exists(path):  # keep rows of events that were not rebuilt
            old = pd.read_csv(path)
            src = pd.concat([old[~old.event_id.isin(src.event_id)], src]).sort_values(
                ["event_id", "trace_id"])
        src.to_csv(path + ".part", index=False)
        os.replace(path + ".part", path)
    log.info("build dl done: %d playback files written, %d unchanged, %d unexpected traces "
             "dropped, %d remaining overlaps cut", n_written, n_skipped, n_unexp, n_cut)
    return dict(files_written=n_written, files_unchanged=n_skipped, unexpected_traces=n_unexp,
                overlaps_cut=n_cut)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="both", choices=["cc", "dl", "both"])
    ap.add_argument("--steps", default="plan,ncedc,fallback,build")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=WORKERS)
    args = ap.parse_args()
    workers = max(1, min(WORKERS, args.workers))
    steps = args.steps.split(",")
    sets = ["cc", "dl"] if args.set == "both" else [args.set]
    setup_logging()
    t_start = time.time()
    log.info("start: sets %s, steps %s, limit %s, workers %d, pid %d", sets, steps, args.limit,
             workers, os.getpid())
    remove_stale_parts()
    if "plan" in steps:
        make_plan()
    for set_ in sets:
        df = load_plan(set_)
        if args.limit:
            keep = sorted(df.event_id.unique())[:args.limit]
            if set_ == "dl":
                keep = list(dict.fromkeys([C.MAINSHOCK_ID] + keep))[:args.limit]
            df = df[df.event_id.isin(keep)]
        status = dict(set=set_, limit=args.limit, events=int(df.event_id.nunique()),
                      plan_lines=len(df))
        failed = []
        if "ncedc" in steps:
            t0 = time.time()
            res, f1 = run_tasks(tasks_from_plan(df, set_, "ncedc"), workers)
            failed += f1
            status["ncedc"] = dict(results=res, failed=len(f1), seconds=round(time.time() - t0, 1))
        if "fallback" in steps:
            t0 = time.time()
            res, f2, miss, held = fallback(df, set_, workers)
            failed += f2
            status["fallback"] = dict(results=res, failed=len(f2), missing_lines=len(miss),
                                      missing_channels=int(miss[["network", "station", "location",
                                                                 "channel"]].drop_duplicates()
                                                           .shape[0]) if len(miss) else 0,
                                      earthscope_channels_with_data=sorted(held),
                                      seconds=round(time.time() - t0, 1))
        if "build" in steps:
            t0 = time.time()
            status["build"] = build_cc(df) if set_ == "cc" else build_dl(df)
            status["build"]["seconds"] = round(time.time() - t0, 1)
        status["failed_requests"] = failed
        status["finished_utc"] = str(UTCDateTime())
        tag = f"_limit{args.limit}" if args.limit else ""
        write_json_atomic(status, os.path.join(RAW, f"status_{set_}{tag}.json"))
        if not failed and not args.limit and all(s in steps for s in
                                                 ("ncedc", "fallback", "build")):
            write_json_atomic(status, os.path.join(RAW, f"DONE_{set_}"))
            log.info("DONE %s", set_)
        elif failed:
            log.error("%s: %d failed requests; run again to retry them", set_, len(failed))
    log.info("finished in %.0f s", time.time() - t_start)


if __name__ == "__main__":
    main()
