#!/usr/bin/env python
# make_waveform_archive.py
#
# Converts the reference event-window SAC files (data/gwangyang_11ev/reference/gwangyang_pnplus/
# waveforms_100km/<event>/<event>.<NET>.<STA>.<CHA>.sac; 100 Hz, raw counts) into
#   (a) an SDS archive   inputs/sds/YEAR/NET/STA/CHA.D/NET.STA.LOC.CHA.D.YEAR.DOY   (one file per channel-day),
#       the layout SeisComP's "sdsarchive://" RecordStream and obspy.clients.filesystem.sds.Client read;
#   (b) one playback file per event   inputs/playback/<event>.mseed   (all channels of that event;
#       SeisComP needs them time-sorted with scmssort before a playback -- done in a later step),
# and proves that both copies are sample-exact copies of the SAC data.
#
# Why these choices:
#   * miniSEED encoding STEIM2 when the samples are whole numbers (raw counts stored as float32 in SAC),
#     FLOAT32 otherwise; STEIM2 is lossless for integers and is what SeisComP archives normally hold.
#   * 512-byte records: the SeisComP / SeedLink standard record size (slarchive writes 512-byte records).
#   * location code blank: SAC khole is unset in every file (checked below).
#   * two events (2021-08-28 13:34:10 and 13:39:22) have overlapping windows; in the SDS day file the
#     overlapping parts are merged only after checking that they are identical sample by sample.
#
# Run with the pyrtdd environment:
#     /home/msseo/miniforge3/envs/pyrtdd/bin/python make_waveform_archive.py [--overwrite]
# Without --overwrite the script refuses to write into non-empty output folders.
# Reads only data/gwangyang_11ev/reference/; writes inputs/sds, inputs/playback, inputs/checks.

import argparse
import glob
import os
import shutil
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from obspy import Stream, UTCDateTime, read
from obspy.clients.filesystem.sds import Client
from obspy.core.util import AttribDict

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
SAC_ROOT = f"{DATA}/reference/gwangyang_pnplus/waveforms_100km"
SDS_ROOT = f"{DATA}/inputs/sds"
PLAYBACK_DIR = f"{DATA}/inputs/playback"
CHECKS = f"{DATA}/inputs/checks"
RECLEN = 512
SDS_TYPE = "D"
STEIM2_MAX_DIFF = 2**29 - 1      # largest first difference a Steim-2 frame can hold (30-bit signed)
FLOAT32_EXACT_INT = 2**24        # float32 holds every integer exactly only up to 2^24


def sac_to_trace(path):
    tr = read(path, format="SAC")[0]
    eid, net, sta, cha = os.path.basename(path).split(".")[0:4]
    s = tr.stats.sac
    khole = str(s.get("khole", "")).strip()
    loc = "" if khole in ("", "-12345") else khole
    info = dict(sac_file=os.path.relpath(path, DATA), kma_id=eid, net=net, sta=sta, loc=loc, cha=cha,
                sensor=cha[:2], hdr_knetwk=str(s.get("knetwk", "")).strip(), hdr_kstnm=str(s.get("kstnm", "")).strip(),
                hdr_kcmpnm=str(s.get("kcmpnm", "")).strip(), hdr_khole=khole,
                cmpaz_set=s.get("cmpaz", -12345.0) != -12345.0, cmpinc_set=s.get("cmpinc", -12345.0) != -12345.0,
                sampling_rate=tr.stats.sampling_rate, npts=tr.stats.npts,
                starttime=tr.stats.starttime, endtime=tr.stats.endtime, sac_dtype=str(tr.data.dtype))
    data = tr.data
    finite = bool(np.all(np.isfinite(data)))
    integer = finite and bool(np.all(data == np.round(data)))
    max_abs = float(np.max(np.abs(data))) if len(data) else 0.0
    max_diff = float(np.max(np.abs(np.diff(data.astype(np.float64))))) if len(data) > 1 else 0.0
    if integer and max_abs < 2**31 - 1 and max_diff <= STEIM2_MAX_DIFF:
        new = data.astype(np.int64)
        assert np.array_equal(new.astype(np.float64), data.astype(np.float64))
        new = new.astype(np.int32)
        enc = "STEIM2"
    else:
        new = data.astype(np.float32)
        enc = "FLOAT32"
    info.update(finite=finite, integer_valued=integer, max_abs=max_abs, max_abs_diff=max_diff,
                above_float32_exact_range=max_abs > FLOAT32_EXACT_INT, encoding=enc)
    out = tr.copy()
    out.data = new
    out.stats.network, out.stats.station, out.stats.location, out.stats.channel = net, sta, loc, cha
    for k in ("sac", "_format"):
        out.stats.pop(k, None)
    out.stats.mseed = AttribDict(dict(encoding=enc, dataquality=SDS_TYPE))
    return out, info, tr


def sds_path(net, sta, loc, cha, year, doy):
    return f"{SDS_ROOT}/{year}/{net}/{sta}/{cha}.{SDS_TYPE}/{net}.{sta}.{loc}.{cha}.{SDS_TYPE}.{year}.{doy:03d}"


def split_by_day(tr):
    # cut a trace at UTC midnights so every piece belongs to exactly one SDS day file
    pieces, t = [], tr.stats.starttime
    while t <= tr.stats.endtime:
        day0 = UTCDateTime(t.year, t.month, t.day)
        day1 = day0 + 86400
        p = tr.slice(t, min(tr.stats.endtime, day1 - tr.stats.delta / 2.0), nearest_sample=False)
        if p.stats.npts:
            pieces.append(p)
        t = day1
    return pieces


def merge_checked(traces):
    # merge pieces of one channel-day; overlapping samples must be identical, otherwise refuse
    st = Stream([t.copy() for t in traces]).sort(["starttime"])
    n_overlap_checked = 0
    for a, b in zip(st[:-1], st[1:]):
        if b.stats.starttime <= a.stats.endtime:
            # overlap: both traces come from the same continuous record and must agree exactly
            offs = (b.stats.starttime - a.stats.starttime) * a.stats.sampling_rate
            if abs(offs - round(offs)) > 0.01:
                raise RuntimeError(f"{a.id}: overlapping traces are not on the same sample grid ({offs})")
            sa = a.data[int(round(offs)):]
            n = min(len(sa), len(b.data))
            if not np.array_equal(sa[:n], b.data[:n]):
                raise RuntimeError(f"{a.id}: overlapping samples differ between event windows")
            n_overlap_checked += n
    # merge joins the identical overlaps; a real gap (two event windows hours apart on the same day)
    # becomes masked samples, which split() turns back into separate traces (gaps are never filled)
    st.merge(method=0)
    st = st.split()
    for t in st:
        if isinstance(t.data, np.ma.MaskedArray):
            raise RuntimeError(f"{t.id}: merge produced masked samples")
    return st, n_overlap_checked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true", help="delete and rebuild inputs/sds and inputs/playback")
    args = ap.parse_args()

    for d in (SDS_ROOT, PLAYBACK_DIR):
        if os.path.isdir(d) and os.listdir(d):
            if not args.overwrite:
                sys.exit(f"{d} is not empty; re-run with --overwrite to rebuild it")
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
    os.makedirs(CHECKS, exist_ok=True)

    files = sorted(glob.glob(f"{SAC_ROOT}/*/*.sac"))
    print(f"[sac] {len(files)} SAC files in {len(os.listdir(SAC_ROOT))} event folders")
    infos, by_event, by_channel = [], defaultdict(list), defaultdict(list)
    for f in files:
        tr, info, _ = sac_to_trace(f)
        infos.append(info)
        by_event[info["kma_id"]].append(tr)
        by_channel[(tr.stats.network, tr.stats.station, tr.stats.location, tr.stats.channel)].append(tr)
    man = pd.DataFrame(infos)
    hdr_ok = ((man.hdr_knetwk == man.net) & (man.hdr_kstnm == man.sta) & (man.hdr_kcmpnm == man.cha)).all()
    print(f"[sac] header codes == file-name codes: {hdr_ok}; khole set in {int((man.hdr_khole != '').sum())} files; "
          f"cmpaz set in {int(man.cmpaz_set.sum())}, cmpinc set in {int(man.cmpinc_set.sum())} files")
    print(f"[sac] sampling rates: {sorted(man.sampling_rate.unique())}; dtypes: {sorted(man.sac_dtype.unique())}; "
          f"integer-valued: {int(man.integer_valued.sum())}/{len(man)}; largest |count| {man.max_abs.max():.0f}; "
          f"files with |count| > 2^24: {int(man.above_float32_exact_range.sum())}; encodings: {man.encoding.value_counts().to_dict()}")

    # --- (b) per-event playback files ------------------------------------------------------
    for eid, trs in sorted(by_event.items()):
        st = Stream(trs).sort(["network", "station", "location", "channel"])
        st.write(f"{PLAYBACK_DIR}/{eid}.mseed", format="MSEED", reclen=RECLEN)
    print(f"[playback] wrote {len(by_event)} files to {PLAYBACK_DIR}")

    # --- (a) SDS archive --------------------------------------------------------------------
    sds_rows, n_overlap_total = [], 0
    for (net, sta, loc, cha), trs in sorted(by_channel.items()):
        days = defaultdict(list)
        for tr in trs:
            for p in split_by_day(tr):
                days[(p.stats.starttime.year, p.stats.starttime.julday)].append(p)
        for (year, doy), pieces in sorted(days.items()):
            st, n_ov = merge_checked(pieces)
            n_overlap_total += n_ov
            path = sds_path(net, sta, loc, cha, year, doy)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            st.write(path, format="MSEED", reclen=RECLEN)
            sds_rows.append(dict(sds_file=os.path.relpath(path, DATA), net=net, sta=sta, loc=loc, cha=cha,
                                 year=year, doy=doy, n_event_windows=len(pieces), n_traces_written=len(st),
                                 overlap_samples_checked=n_ov))
    print(f"[sds] wrote {len(sds_rows)} channel-day files; {n_overlap_total} overlapping samples checked identical")

    # --- verification 1: every SAC file is reproduced sample-exactly -------------------------
    client = Client(SDS_ROOT, sds_type=SDS_TYPE)
    pb_cache = {}
    sds_eq, sds_dt, sds_npts, pb_eq, pb_dt = [], [], [], [], []
    for f, info in zip(files, infos):
        sac = read(f, format="SAC")[0]
        ref = sac.data.astype(np.float64)
        t0, t1 = info["starttime"], info["endtime"]
        got = client.get_waveforms(info["net"], info["sta"], info["loc"], info["cha"], t0, t1)
        ok = len(got) == 1 and got[0].stats.npts == len(ref) and np.array_equal(got[0].data.astype(np.float64), ref)
        sds_eq.append(bool(ok))
        sds_npts.append(got[0].stats.npts if len(got) == 1 else -len(got))
        sds_dt.append(round((got[0].stats.starttime - t0) * 1e6, 3) if len(got) == 1 else np.nan)
        eid = info["kma_id"]
        if eid not in pb_cache:
            pb_cache = {eid: read(f"{PLAYBACK_DIR}/{eid}.mseed")}
        sel = pb_cache[eid].select(network=info["net"], station=info["sta"], location=info["loc"], channel=info["cha"])
        okp = len(sel) == 1 and np.array_equal(sel[0].data.astype(np.float64), ref)
        pb_eq.append(bool(okp))
        pb_dt.append(round((sel[0].stats.starttime - t0) * 1e6, 3) if len(sel) == 1 else np.nan)
    man["sds_file"] = [os.path.relpath(sds_path(r.net, r.sta, r.loc, r.cha, r.starttime.year, r.starttime.julday), DATA)
                       for r in man.itertuples()]
    man["playback_file"] = [f"inputs/playback/{k}.mseed" for k in man.kma_id]
    man["sds_samples_equal"], man["sds_npts"], man["sds_start_minus_sac_us"] = sds_eq, sds_npts, sds_dt
    man["playback_samples_equal"], man["playback_start_minus_sac_us"] = pb_eq, pb_dt
    man["starttime"] = man.starttime.map(str)
    man["endtime"] = man.endtime.map(str)
    man.to_csv(f"{CHECKS}/waveform_manifest.csv", index=False)
    print(f"[verify] SDS sample-exact: {sum(sds_eq)}/{len(files)}; max |start shift| "
          f"{np.nanmax(np.abs(sds_dt)):.3f} us; playback sample-exact: {sum(pb_eq)}/{len(files)}; "
          f"max |start shift| {np.nanmax(np.abs(pb_dt)):.3f} us")

    # --- verification 2: the SDS archive as obspy's SDS client sees it -----------------------
    nslc = client.get_all_nslc(sds_type=SDS_TYPE)
    stations = client.get_all_stations(sds_type=SDS_TYPE)
    day_rows = []
    for r in sds_rows:
        st = read(f"{DATA}/{r['sds_file']}")
        n_rec_traces = len(st)
        st.merge(-1)
        gaps = st.get_gaps()
        r.update(n_traces_read=n_rec_traces, n_traces_after_cleanup=len(st),
                 n_gaps=sum(1 for g in gaps if g[6] > 0), n_overlaps=sum(1 for g in gaps if g[6] < 0),
                 n_samples=sum(t.stats.npts for t in st), size_bytes=os.path.getsize(f"{DATA}/{r['sds_file']}"),
                 encodings=",".join(sorted({t.stats.mseed.encoding for t in read(f"{DATA}/{r['sds_file']}", headonly=True)})),
                 first_sample=str(min(t.stats.starttime for t in st)), last_sample=str(max(t.stats.endtime for t in st)))
        day_rows.append(r)
    sds = pd.DataFrame(day_rows)
    sds.to_csv(f"{CHECKS}/sds_files.csv", index=False)
    on_disk = sorted(glob.glob(f"{SDS_ROOT}/*/*/*/*.{SDS_TYPE}/*"))
    print(f"[sds] files on disk: {len(on_disk)}; SDS client: {len(nslc)} NSLC, {len(stations)} stations; "
          f"traces per day file after cleanup: {sds.n_traces_after_cleanup.value_counts().sort_index().to_dict()}; "
          f"gaps: {int(sds.n_gaps.sum())} (between separate event windows), overlaps: {int(sds.n_overlaps.sum())}")
    tot = sum(os.path.getsize(p) for p in on_disk)
    tot_pb = sum(os.path.getsize(p) for p in glob.glob(f"{PLAYBACK_DIR}/*.mseed"))
    print(f"[size] SDS {tot / 1e6:.1f} MB, playback {tot_pb / 1e6:.1f} MB")
    bad = (~man.sds_samples_equal) | (~man.playback_samples_equal)
    if bad.any() or sds.n_overlaps.sum() or len(on_disk) != len(sds_rows):
        print("[PROBLEMS] see inputs/checks/waveform_manifest.csv and sds_files.csv")
        return 1
    print("[problems] none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
