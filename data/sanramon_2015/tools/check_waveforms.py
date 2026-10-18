# check_waveforms.py -- SR-B: checks of the waveforms written by download_waveforms.py
# (env pyrtdd, python -I). Nothing is downloaded here.
#
# Reads back
#   * the SDS archive inputs/sds/ with obspy.clients.filesystem.sds.Client: every requested
#     event x channel window of reference_tables/waveform_requests_cc.csv;
#   * every SDS day file directly: traces of one id only (the file name's), sorted, no overlaps
#     (no duplicate data), all samples inside that UTC day, size a multiple of 512 bytes, every
#     record 512 bytes;
#   * every playback file inputs/playback/<id>.mseed: every requested window of
#     reference_tables/waveform_requests_dl.csv; no overlaps; records 512 bytes and sorted by end
#     time.
# Computes
#   * per request line: traces, samples inside the window, coverage (samples / expected samples),
#     number of continuous pieces, sample rate in the data vs stations.xml, source (NCEDC/EarthScope);
#   * pick coverage. cc: every NCSS pick of a benchmark event on a sensor of the cc plan (<= 60 km).
#     dl: every NCSS pick of the 26 DL events on a sensor of the dl plan (<= 80 km). A pick is
#     "covered" when one continuous piece of data spans the window rtDD cross-correlation reads with
#     its default settings: P: pick-2.0 s .. pick+2.0 s+0.02*TT, S: pick-2.0 s .. pick+2.5 s+0.04*TT
#     (TT = pick - origin; winStart -0.5, winEnd 0.5 (P) / 1.0 (S), winScaling 0.02/0.04,
#     maxDelay 0.5, filter margin 1 s; scrtdd.xml v2.0.10). Checked on the picked channel and on the
#     components rtDD uses by default (P: Z = the sensor's vertical; S: L2 = both horizontals).
#     For dl also "+-10 s": continuous data from pick-10 s to pick+10 s on the picked channel;
#   * timing sanity check (independent of the downloader's own bookkeeping): for analyst P picks
#     with weight 0-1 at <= 30 km on vertical channels, an Akaike (AIC) onset is computed on the SDS
#     data in pick-1.0 .. pick+0.5 s after a one-pass (causal) 1 Hz 2-pole high-pass, so no energy
#     is smeared ahead of the onset; the AIC onset minus the analyst pick should scatter around 0;
#   * data volume, file counts; request counts, bytes and seconds from the download log.
# Outputs (reference_tables/): waveform_coverage_cc.csv, waveform_coverage_dl.csv,
#   waveform_aic_vs_picks.csv,
#   waveform_pick_coverage.csv, waveform_dayfile_check.csv, waveform_missing_by_channel.csv
#   (per set and channel: windows without data / with gaps, first and last such window),
#   stats_20_waveforms.json
# Usage: python -I check_waveforms.py [--workers 8]

import argparse
import fnmatch
import glob
import json
import multiprocessing as mp
import os
import re
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read
from obspy.clients.filesystem.sds import Client as SDSClient
from obspy.io.mseed.util import get_record_information

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402  (paths only)

SDS = os.path.join(C.INP, "sds")
PLAYBACK = os.path.join(C.INP, "playback")
RAW = os.path.join(C.REF, "waveforms_raw")
LOG = os.path.join(C.LOGS, "sanramon_waveforms_20261017.log")
RECLEN = 512
TOL = 1e-6


def load_plan(name):
    return pd.read_csv(os.path.join(C.TAB, f"waveform_requests_{name}.csv"),
                       keep_default_na=False, dtype={"location": str},
                       converters={"has_metadata": lambda x: x == "True",
                                   "wildcard": lambda x: x == "True",
                                   "picked_channel": lambda x: x == "True"})


def pieces_in(tr, ws, we):
    """(n samples with ws <= t < we, first sample time, last sample time) of one trace"""
    sr, t0 = tr.stats.sampling_rate, tr.stats.starttime
    i0 = max(0, int(np.ceil((ws - t0) * sr - TOL)))
    i1 = min(tr.stats.npts, int(np.ceil((we - t0) * sr - TOL)))
    if i1 <= i0:
        return 0, None, None
    return i1 - i0, t0 + i0 / sr, t0 + (i1 - 1) / sr


def row_result(r, st):
    """coverage of one request line from the traces of a Stream; also the continuous pieces"""
    ws, we = UTCDateTime(r["start"]), UTCDateTime(r["end"])
    pat = f"{r['network']}.{r['station']}.{r['location']}.{r['channel']}"
    trs = [tr for tr in st if fnmatch.fnmatch(tr.id, pat)] if r["wildcard"] else \
        [tr for tr in st if tr.id == pat]
    ids = sorted({tr.id for tr in trs})
    segs = defaultdict(list)
    nsamp, srs = 0, set()
    for tr in trs:
        n, a, b = pieces_in(tr, ws, we)
        if n:
            nsamp += n
            srs.add(tr.stats.sampling_rate)
            segs[tr.id].append((a.ns, b.ns, tr.stats.sampling_rate))
    sr = max(srs) if srs else (float(r["sample_rate"]) if r["sample_rate"] not in ("", None) else
                               np.nan)
    nids = max(1, len(ids))
    expected = int(round((we - ws) * sr)) * nids if np.isfinite(sr) else 0
    npieces = sum(len(v) for v in segs.values())
    res = dict(event_id=int(r["event_id"]), network=r["network"], station=r["station"],
               location=r["location"], channel=r["channel"], trace_ids=";".join(ids),
               n_pieces=npieces, n_samples=nsamp, expected_samples=expected,
               coverage=round(nsamp / expected, 6) if expected else 0.0,
               sr_data=";".join(f"{x:g}" for x in sorted(srs)),
               sr_meta=r["sample_rate"],
               first_sample=str(UTCDateTime(ns=min(s[0] for v in segs.values() for s in v)))
               if npieces else "",
               last_sample=str(UTCDateTime(ns=max(s[1] for v in segs.values() for s in v)))
               if npieces else "")
    return res, {(int(r["event_id"]), k): sorted(v) for k, v in segs.items()}


def aic_onset(tr, t_pick, before=1.0, after=0.5):
    """AIC onset time and a simple SNR in pick-before .. pick+after, or (None, None)"""
    if tr.stats.starttime > t_pick - before - 2.0 or tr.stats.endtime < t_pick + after:
        return None, None
    w = tr.slice(t_pick - before - 2.0, t_pick + after).copy()  # 2 s extra for the filter
    w.data = w.data.astype(np.float64)
    w.detrend("demean")
    w.filter("highpass", freq=1.0, corners=2, zerophase=False)
    w = w.slice(t_pick - before, t_pick + after)
    x = w.data - w.data.mean()
    n = len(x)
    if n < 20:
        return None, None
    k = np.arange(1, n - 1)
    c1 = np.cumsum(x ** 2)
    s1 = np.cumsum(x)
    v1 = c1[k - 1] / k - (s1[k - 1] / k) ** 2
    v2 = (c1[-1] - c1[k - 1]) / (n - k) - ((s1[-1] - s1[k - 1]) / (n - k)) ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        aic = k * np.log(v1) + (n - k - 1) * np.log(v2)
    aic[~np.isfinite(aic)] = np.inf
    i = int(np.argmin(aic[5:-5])) + 5
    t_on = w.stats.starttime + k[i] * w.stats.delta
    ip = int(round((t_pick - w.stats.starttime) * w.stats.sampling_rate))
    pre = x[max(0, ip - int(0.5 * w.stats.sampling_rate)):ip]
    post = x[ip:ip + int(0.5 * w.stats.sampling_rate)]
    snr = float(np.sqrt(np.mean(post ** 2)) / np.sqrt(np.mean(pre ** 2))) if len(pre) and \
        np.mean(pre ** 2) > 0 else np.nan
    return t_on, snr


def _cc_worker(args):
    sds_root, rows_by_event, aic_picks = args
    client = SDSClient(sds_root)
    out, segs, aic = [], {}, []
    for eid, rows in rows_by_event:
        bulk = [(r["network"], r["station"], r["location"], r["channel"],
                 UTCDateTime(r["start"]), UTCDateTime(r["end"])) for r in rows]
        st = client.get_waveforms_bulk(bulk)
        for r in rows:
            res, sg = row_result(r, st)
            out.append(res)
            segs.update(sg)
        for tid, t_s, ctype, wcode in aic_picks.get(eid, []):
            t = UTCDateTime(t_s)
            for tr in st.select(id=tid):
                t_on, snr = aic_onset(tr, t)
                if t_on is not None:
                    aic.append(dict(event_id=eid, trace_id=tid, channel_type=ctype,
                                    weight_code=wcode, pick=t_s, aic_onset=str(t_on),
                                    aic_minus_pick_s=round(t_on - t, 4), snr=round(snr, 2)))
                    break
    return out, segs, aic


def check_sds_readback(cc, workers, aic_picks):
    by_event = [(eid, g.to_dict("records")) for eid, g in cc.groupby("event_id")]
    jobs = [(SDS, by_event[k::workers], aic_picks) for k in range(workers)]
    with mp.Pool(workers) as pool:
        parts = pool.map(_cc_worker, jobs)
    rows, segs, aic = [], {}, []
    for o, s, a in parts:
        rows.extend(o)
        segs.update(s)
        aic.extend(a)
    return pd.DataFrame(rows), segs, pd.DataFrame(aic)


def _dayfile_worker(paths):
    out = []
    for p in paths:
        name = os.path.basename(p)
        net, sta, loc, cha, typ, year, doy = name.split(".")
        d0 = UTCDateTime(year=int(year), julday=int(doy))
        d1 = d0 + 86400
        size = os.path.getsize(p)
        st = read(p, format="MSEED")
        st.sort(["starttime", "endtime"])
        ids = {tr.id for tr in st}
        n_overlap = sum(1 for a, b in zip(st, st[1:]) if b.stats.starttime <= a.stats.endtime)
        outside = sum(1 for tr in st if tr.stats.starttime < d0 or tr.stats.endtime >= d1)
        reclens, nrec, off = set(), 0, 0
        with open(p, "rb") as f:
            while off < size:
                info = get_record_information(f, offset=off)
                reclens.add(info["record_length"])
                off += info["record_length"]
                nrec += 1
        out.append(dict(file=os.path.relpath(p, SDS), bytes=size, n_records=nrec,
                        record_lengths=";".join(str(x) for x in sorted(reclens)),
                        n_traces=len(st), n_samples=int(sum(tr.stats.npts for tr in st)),
                        ids_ok=ids == {f"{net}.{sta}.{loc}.{cha}"}, n_overlaps=n_overlap,
                        traces_outside_day=outside,
                        sampling_rates=";".join(f"{x:g}" for x in sorted(
                            {tr.stats.sampling_rate for tr in st}))))
    return out


def check_dayfiles(workers):
    paths = sorted(glob.glob(os.path.join(SDS, "*", "*", "*", "*.D", "*.D.*.*")))
    with mp.Pool(workers) as pool:
        parts = pool.map(_dayfile_worker, [paths[k::workers] for k in range(workers)])
    return pd.DataFrame([x for p in parts for x in p]).sort_values("file")


def check_playback(dl):
    rows, segs, files = [], {}, []
    for eid, g in dl.groupby("event_id"):
        p = os.path.join(PLAYBACK, f"{int(eid)}.mseed")
        if not os.path.exists(p):
            files.append(dict(event_id=int(eid), exists=False))
            continue
        size = os.path.getsize(p)
        ends, reclens, off = [], set(), 0
        with open(p, "rb") as f:
            while off < size:
                info = get_record_information(f, offset=off)
                reclens.add(info["record_length"])
                ends.append(info["endtime"].ns)
                off += info["record_length"]
        st = read(p, format="MSEED")
        st.merge(method=-1)
        st.sort(["network", "station", "location", "channel", "starttime"])
        n_overlap = sum(1 for a, b in zip(st, st[1:]) if a.id == b.id and
                        b.stats.starttime <= a.stats.endtime)
        req = {f"{r.network}.{r.station}.{r.location}.{r.channel}" for r in g.itertuples()}
        for r in g.to_dict("records"):
            res, sg = row_result(r, st)
            rows.append(res)
            segs.update(sg)
        files.append(dict(event_id=int(eid), exists=True, bytes=size, n_records=len(ends),
                          record_lengths=";".join(str(x) for x in sorted(reclens)),
                          sorted_by_endtime=bool(all(a <= b for a, b in zip(ends, ends[1:]))),
                          n_traces=len(st), n_channels=len({tr.id for tr in st}),
                          n_channels_requested=len(req),
                          unrequested_ids=len({tr.id for tr in st} - req), n_overlaps=n_overlap,
                          n_samples=int(sum(tr.stats.npts for tr in st))))
    return pd.DataFrame(rows), segs, pd.DataFrame(files)


def covered(segs, key, w0, w1):
    for a, b, sr in segs.get(key, []):
        d = 1.0 / sr
        if a <= (w0 + d).ns and b >= (w1 - d).ns:
            return True
    return False


def pick_coverage(picks, plan, segs, set_, origin):
    """one row per pick of a sensor that is in the plan of that event"""
    sensors = defaultdict(dict)  # (event, net.sta.loc.grp) -> {channel: dip}
    for r in plan.itertuples():
        dip = float(r.dip) if r.dip not in ("", None) else np.nan
        sensors[(int(r.event_id), r.sensor)][r.channel] = dip
    ph = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "phase_extra.csv"), keep_default_na=False,
                     dtype={"location": str})
    in_phase_csv = {(int(r.event_id), r.phase, r.network, r.station, r.location, r.channel,
                     r.time_utc): str(r.in_phase_csv) == "True" for r in ph.itertuples()}
    rows = []
    for r in picks.itertuples():
        eid = int(r.event_id)
        sensor = f"{r.network}.{r.station}.{r.location}.{r.channel[:2]}"
        chans = sensors.get((eid, sensor))
        if chans is None:
            continue
        t = UTCDateTime(r.time_utc)
        tt = t - origin[eid]
        if r.phase == "P":
            w0, w1 = t - 2.0, t + 2.0 + 0.02 * tt
        else:
            w0, w1 = t - 2.0, t + 2.5 + 0.04 * tt
        base = f"{r.network}.{r.station}.{r.location}."
        own = covered(segs, (eid, base + r.channel), w0, w1)
        vert = [c for c, d in chans.items() if np.isfinite(d) and abs(d) >= 60]
        hori = [c for c, d in chans.items() if np.isfinite(d) and abs(d) < 30]
        if r.phase == "P":
            need = vert[:1]
        else:
            need = hori if len(hori) == 2 else []
        comp = bool(need) and all(covered(segs, (eid, base + c), w0, w1) for c in need)
        row = dict(set=set_, event_id=eid, phase=r.phase, time_utc=r.time_utc,
                   network=r.network, station=r.station, location=r.location,
                   channel=r.channel, channel_type=r.channel[:2],
                   weight_code=r.weight_code, epi_dist_km=r.epi_dist_km,
                   in_phase_csv=in_phase_csv.get((eid, r.phase, r.network, r.station, r.location,
                                                  r.channel, r.time_utc), False),
                   has_metadata=bool(chans) and any(np.isfinite(d) for d in chans.values()),
                   covered_pick_channel=own,
                   rtdd_components="Z" if r.phase == "P" else ("L2" if len(hori) == 2 else
                                                                "no 2 horizontals"),
                   covered_rtdd_components=comp)
        if set_ == "dl":
            row["covered_pm10s"] = covered(segs, (eid, base + r.channel), t - 10.0, t + 10.0)
        rows.append(row)
    return pd.DataFrame(rows)


def missing_by_channel(cov, plan, set_):
    m = cov.merge(plan[["event_id", "network", "station", "location", "channel", "origin_time",
                        "dist_km", "picked_channel"]],
                  on=["event_id", "network", "station", "location", "channel"], how="left")
    m["complete"] = (m.coverage >= 0.999) & (m.n_pieces == 1)
    m["nodata"] = m.n_samples == 0
    m["partial"] = ~m.complete & ~m.nodata
    rows = []
    for k, g in m.groupby(["network", "station", "location", "channel"]):
        bad = g[~g.complete].sort_values("origin_time")
        rows.append(dict(set=set_, network=k[0], station=k[1], location=k[2], channel=k[3],
                         dist_km=round(float(g.dist_km.median()), 1), windows=int(len(g)),
                         no_data=int(g.nodata.sum()), partial=int(g.partial.sum()),
                         complete=int(g.complete.sum()),
                         picked_windows_not_complete=int((~g.complete & g.picked_channel).sum()),
                         first_not_complete=bad.origin_time.iloc[0] if len(bad) else "",
                         last_not_complete=bad.origin_time.iloc[-1] if len(bad) else ""))
    return pd.DataFrame(rows)


def parse_log():
    """REQUEST lines of the log, tagged with the run (start line) they belong to"""
    req, runs, run = [], [], None
    pat = re.compile(r"(\S+)Z INFO \[[^]]+\] REQUEST (.*)")
    for line in open(LOG):
        if " start: sets " in line:
            run = dict(start=line.split("Z ")[0], text=line.split("start: ")[1].strip())
            runs.append(run)
        if " finished in " in line and run is not None:
            run["end"] = line.split("Z ")[0]
            run["seconds"] = float(line.split("finished in ")[1].split()[0])
        m = pat.match(line.strip())
        if m:
            d = dict(utc=m.group(1), run=len(runs) - 1)
            body = m.group(2)
            for k in ("service", "set", "event", "chunk", "lines", "attempt", "status", "bytes",
                      "seconds", "traces"):
                mm = re.search(rf"\b{k}=(\S*)", body)
                d[k] = mm.group(1) if mm else ""
            req.append(d)
    return pd.DataFrame(req), runs


def du(path):
    tot, n = 0, 0
    for dp, _, fs in os.walk(path):
        for f in fs:
            tot += os.path.getsize(os.path.join(dp, f))
            n += 1
    return tot, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    stats = {}
    cc, dl = load_plan("cc"), load_plan("dl")
    ev = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "event.csv"))
    origin = {int(i): UTCDateTime(t) for i, t in zip(ev.id, ev.isotime)}

    # ---- SDS read-back (+ AIC timing check on P picks, weight 0-1, <= 30 km, vertical channels)
    picks = pd.read_csv(os.path.join(C.TAB, "picks_ncss.csv"), keep_default_na=False,
                        dtype={"location": str, "location_raw": str})
    picks = picks[picks.benchmark_event.astype(str) == "True"]
    vert = {(int(r.event_id), f"{r.network}.{r.station}.{r.location}.{r.channel}")
            for r in cc.itertuples() if r.dip not in ("", None) and abs(float(r.dip)) >= 60}
    aic_picks = defaultdict(list)
    for r in picks[(picks.phase == "P") & picks.weight_code.astype(int).isin([0, 1]) &
                   (picks.epi_dist_km.astype(float) <= 30)].itertuples():
        tid = f"{r.network}.{r.station}.{r.location}.{r.channel}"
        if (int(r.event_id), tid) in vert:
            aic_picks[int(r.event_id)].append((tid, r.time_utc, r.channel[:2], int(r.weight_code)))
    cov_cc, segs_cc, aic = check_sds_readback(cc, args.workers, dict(aic_picks))
    aic.to_csv(os.path.join(C.TAB, "waveform_aic_vs_picks.csv"), index=False)
    src = pd.read_csv(os.path.join(C.TAB, "waveform_sources_cc.csv"))
    es = src[src.service == "earthscope"].groupby("event_id").trace_id.apply(set).to_dict()
    cov_cc["source"] = [("earthscope" if any(t in es.get(e, set()) for t in ids.split(";") if t)
                         else "ncedc") if ids else "" for e, ids in zip(cov_cc.event_id,
                                                                        cov_cc.trace_ids)]
    cov_cc = cov_cc.sort_values(["event_id", "network", "station", "location", "channel"])
    cov_cc.to_csv(os.path.join(C.TAB, "waveform_coverage_cc.csv"), index=False)
    day = check_dayfiles(args.workers)
    day.to_csv(os.path.join(C.TAB, "waveform_dayfile_check.csv"), index=False)

    # ---- playback files
    cov_dl, segs_dl, files_dl = check_playback(dl)
    srcd = pd.read_csv(os.path.join(C.TAB, "waveform_sources_dl.csv"))
    esd = srcd[srcd.service == "earthscope"].groupby("event_id").trace_id.apply(set).to_dict()
    cov_dl["source"] = [("earthscope" if any(t in esd.get(e, set()) for t in ids.split(";") if t)
                         else "ncedc") if ids else "" for e, ids in zip(cov_dl.event_id,
                                                                        cov_dl.trace_ids)]
    cov_dl.to_csv(os.path.join(C.TAB, "waveform_coverage_dl.csv"), index=False)

    # ---- pick coverage
    pc_cc = pick_coverage(picks, cc, segs_cc, "cc", origin)
    pc_dl = pick_coverage(picks[picks.event_id.isin(dl.event_id.unique())], dl, segs_dl, "dl",
                          origin)
    pc = pd.concat([pc_cc, pc_dl], ignore_index=True)
    pc.to_csv(os.path.join(C.TAB, "waveform_pick_coverage.csv"), index=False)
    mbc = pd.concat([missing_by_channel(cov_cc, cc, "cc"), missing_by_channel(cov_dl, dl, "dl")],
                    ignore_index=True)
    mbc = mbc.sort_values(["set", "no_data", "partial"], ascending=[True, False, False])
    mbc.to_csv(os.path.join(C.TAB, "waveform_missing_by_channel.csv"), index=False)

    # ---- statistics
    def cov_summary(cov):
        c = cov.coverage
        return dict(lines=int(len(cov)), with_data=int((cov.n_samples > 0).sum()),
                    no_data=int((cov.n_samples == 0).sum()),
                    complete_one_piece=int(((c >= 0.999) & (cov.n_pieces == 1)).sum()),
                    partial=int(((cov.n_samples > 0) & ((c < 0.999) | (cov.n_pieces > 1))).sum()),
                    samples=int(cov.n_samples.sum()), expected=int(cov.expected_samples.sum()),
                    from_earthscope=int((cov.source == "earthscope").sum()),
                    by_type={k: dict(lines=int(len(g)), with_data=int((g.n_samples > 0).sum()),
                                     complete=int(((g.coverage >= 0.999) & (g.n_pieces == 1)).sum()))
                             for k, g in cov.groupby(cov.channel.str[:2])},
                    by_network={k: dict(lines=int(len(g)), with_data=int((g.n_samples > 0).sum()))
                                for k, g in cov.groupby("network")})

    def sr_check(cov):
        out = {}
        for k, g in cov[cov.n_samples > 0].groupby(cov.channel.str[:2]):
            meta = pd.to_numeric(g.sr_meta, errors="coerce")
            data = pd.to_numeric(g.sr_data, errors="coerce")
            out[k] = dict(rates_in_data=sorted({float(x) for s in g.sr_data for x in s.split(";")}),
                          lines_rate_differs_from_stationxml=int(((data != meta) &
                                                                  meta.notna()).sum()))
        return out

    def pick_summary(p, extra=False):
        if len(p) == 0:
            return {}
        d = dict(picks=int(len(p)), covered_pick_channel=int(p.covered_pick_channel.sum()),
                 covered_rtdd_components=int(p.covered_rtdd_components.sum()))
        if extra:
            d["covered_pm10s"] = int(p.covered_pm10s.sum())
        d["by_phase"] = {k: dict(picks=int(len(g)), covered_pick_channel=int(
            g.covered_pick_channel.sum()), covered_rtdd_components=int(
            g.covered_rtdd_components.sum())) for k, g in p.groupby("phase")}
        d["by_channel_type"] = {k: dict(picks=int(len(g)), covered_pick_channel=int(
            g.covered_pick_channel.sum()), covered_rtdd_components=int(
            g.covered_rtdd_components.sum())) for k, g in p.groupby("channel_type")}
        d["S_without_2_horizontals"] = int((p.rtdd_components == "no 2 horizontals").sum())
        return d

    sds_bytes, sds_files = du(SDS)
    pb_bytes, pb_files = du(PLAYBACK)
    raw_bytes, raw_files = du(RAW)
    reqs, runs = parse_log()
    stats["cc"] = dict(read_back=cov_summary(cov_cc), sample_rates=sr_check(cov_cc),
                       sds_bytes=sds_bytes, sds_files=sds_files,
                       sds_channels=int(day.file.str.split("/").str[-1].str.rsplit(".", n=3)
                                        .str[0].nunique()),
                       dayfiles=dict(n=int(len(day)), overlaps=int(day.n_overlaps.sum()),
                                     files_with_overlaps=int((day.n_overlaps > 0).sum()),
                                     traces_outside_day=int(day.traces_outside_day.sum()),
                                     wrong_ids=int((~day.ids_ok).sum()),
                                     record_lengths=sorted(set(day.record_lengths)),
                                     traces=int(day.n_traces.sum()),
                                     samples=int(day.n_samples.sum()),
                                     records=int(day.n_records.sum())),
                       picks=pick_summary(pc_cc),
                       picks_in_phase_csv=pick_summary(pc_cc[pc_cc.in_phase_csv]))
    stats["dl"] = dict(read_back=cov_summary(cov_dl), sample_rates=sr_check(cov_dl),
                       playback_bytes=pb_bytes, playback_files=pb_files,
                       files=files_dl.to_dict("records"),
                       picks=pick_summary(pc_dl, extra=True))
    stats["raw_cache"] = dict(bytes=raw_bytes, files=raw_files)
    if len(aic):
        def aic_sum(a):
            d = a.aic_minus_pick_s
            return dict(n=int(len(a)), median_s=round(float(d.median()), 4),
                        mad_s=round(float((d - d.median()).abs().median()), 4),
                        within_0p05s=round(float((d.abs() <= 0.05).mean()), 3),
                        within_0p10s=round(float((d.abs() <= 0.10).mean()), 3))
        hi = aic[aic.snr >= 5]
        stats["aic_timing_check"] = dict(
            all=aic_sum(aic), snr_ge_5=aic_sum(hi),
            snr_ge_5_by_channel_type={k: aic_sum(g) for k, g in hi.groupby("channel_type")},
            snr_ge_5_by_weight={str(k): aic_sum(g) for k, g in hi.groupby("weight_code")})
    for set_ in ("cc", "dl"):
        b = mbc[mbc.set == set_]
        stats[set_]["channels"] = dict(
            n=int(len(b)), always_complete=int((b.complete == b.windows).sum()),
            never_any_data=int((b.no_data == b.windows).sum()),
            worst=b.head(25)[["network", "station", "location", "channel", "dist_km", "windows",
                              "no_data", "partial", "first_not_complete",
                              "last_not_complete"]].to_dict("records"))
    if len(reqs):
        reqs["bytes"] = pd.to_numeric(reqs.bytes, errors="coerce").fillna(0)
        reqs["seconds"] = pd.to_numeric(reqs.seconds, errors="coerce").fillna(0)
        stats["requests_all_runs"] = {
            f"{k[0]}/{k[1]}/{k[2]}": dict(n=int(len(g)), bytes=int(g.bytes.sum()),
                                          seconds=round(float(g.seconds.sum()), 1),
                                          max_seconds=round(float(g.seconds.max()), 1))
            for k, g in reqs.groupby(["service", "set", "status"])}
        stats["requests_total"] = dict(n=int(len(reqs)), bytes=int(reqs.bytes.sum()),
                                       seconds=round(float(reqs.seconds.sum()), 1),
                                       retries=int((pd.to_numeric(reqs.attempt) > 1).sum()))
    stats["runs"] = runs
    main_runs = [k for k, r in enumerate(runs) if "limit 0" in r["text"] and "'ncedc'" in r["text"]]
    if main_runs and len(reqs):
        k = main_runs[-1]
        mr = reqs[reqs.run >= main_runs[0]]
        stats["main_run"] = dict(
            runs=[runs[i] for i in main_runs],
            requests={f"{a}/{b}/{c}": dict(n=int(len(g)), bytes=int(g.bytes.sum()),
                                           seconds=round(float(g.seconds.sum()), 1),
                                           median_seconds=round(float(g.seconds.median()), 2),
                                           max_seconds=round(float(g.seconds.max()), 1))
                      for (a, b, c), g in mr.groupby(["service", "set", "status"])},
            first_request=mr.utc.min(), last_request=mr.utc.max(),
            attempts_gt1=int((pd.to_numeric(mr.attempt) > 1).sum()))
    for name in ("status_cc.json", "status_dl.json"):
        p = os.path.join(RAW, name)
        if os.path.exists(p):
            stats[name] = json.load(open(p))
    with open(os.path.join(C.TAB, "stats_20_waveforms.json"), "w") as f:
        json.dump(stats, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in stats.items() if k not in ("runs",)}, indent=1,
                     default=str)[:20000])


if __name__ == "__main__":
    main()
