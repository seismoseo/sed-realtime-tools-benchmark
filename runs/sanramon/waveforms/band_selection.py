#!/usr/bin/env python
# band_selection.py -- San Ramon 2015: which frequency band carries signal above noise in the
# windows rtDD cross-correlates? Used to choose the band-pass of run P1/S1 from the data.
#
# For every analyst pick in phase.csv whose sensor is in the cross-correlation waveform plan
# (<= 60 km) and whose rtDD components are covered (reference_tables/waveform_pick_coverage.csv):
#   * component: P -> the sensor's vertical (dip |90|, channel Z or 1); S -> both horizontals
#     (power summed, i.e. the spectrum of the L2-like pair);
#   * signal window = rtDD's DEFAULT cross-correlation window: P pick-0.5 .. pick+0.5+0.02*TT,
#     S pick-0.5 .. pick+1.0+0.04*TT (TT = pick - NCSS origin);
#   * noise window = the same length, ending 1.0 s before the event's P pick on that station
#     (or before the S pick minus the P-S time if no P pick), i.e. ambient noise before P;
#   * demean, 10 % Hann taper, FFT zero-padded to 4 s; amplitude spectra averaged in 1/3-octave
#     bands (centres 0.5 ... 40 Hz, only below 0.8 x Nyquist); SNR = signal / noise amplitude.
# No instrument correction: the response cancels in the ratio.
# Outputs (this folder): band_snr_per_pick.csv, band_snr_summary.csv, band_snr_summary.json
# Usage (env pyrtdd): python -I band_selection.py [--workers 8]      (read-only on the data)

import argparse
import json
import multiprocessing as mp
import os
from collections import defaultdict

import numpy as np
import pandas as pd
from obspy import UTCDateTime
from obspy.clients.filesystem.sds import Client as SDSClient

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
SR = f"{PROJECT}/data/sanramon_2015"
SDS = f"{SR}/inputs/sds"
PHASE_CSV = f"{SR}/inputs/rtdd_catalog/phase.csv"
EVENT_CSV = f"{SR}/inputs/rtdd_catalog/event.csv"
PICK_COV = f"{SR}/reference_tables/waveform_pick_coverage.csv"
PLAN_CC = f"{SR}/reference_tables/waveform_requests_cc.csv"
OUT = f"{PROJECT}/runs/sanramon/waveforms"
WIN = {"P": (-0.5, 0.5, 0.02), "S": (-0.5, 1.0, 0.04)}   # rtDD defaults: start, end, winScaling
NOISE_GAP_S = 1.0          # noise window ends this long before the P pick
NFFT_S = 4.0               # zero padding length
TAPER = 0.10
CENTRES = np.array([0.5, 0.63, 0.8, 1.0, 1.25, 1.6, 2.0, 2.5, 3.15, 4.0, 5.0, 6.3, 8.0, 10.0,
                    12.5, 16.0, 20.0, 25.0, 31.5, 40.0])
SNR_OK = 3.0               # amplitude SNR regarded as "usable" in the summary


def band_amps(x, fs):
    x = x - x.mean()
    n = len(x)
    w = np.ones(n)
    m = max(1, int(TAPER * n / 2))
    h = np.hanning(2 * m)
    w[:m], w[-m:] = h[:m], h[m:]
    nfft = max(n, int(NFFT_S * fs))
    a = np.abs(np.fft.rfft(x * w, nfft))
    f = np.fft.rfftfreq(nfft, 1 / fs)
    out = np.full(len(CENTRES), np.nan)
    for i, c in enumerate(CENTRES):
        lo, hi = c / 2 ** (1 / 6), c * 2 ** (1 / 6)
        if hi > 0.8 * fs / 2:
            continue
        k = (f >= lo) & (f < hi)
        if k.any():
            out[i] = np.sqrt(np.mean(a[k] ** 2))
    return out


def window(st, tid, t0, t1):
    tr = st.select(id=tid)
    if len(tr) != 1:
        return None, None
    tr = tr[0]
    if tr.stats.starttime > t0 or tr.stats.endtime < t1:
        return None, None
    s = tr.slice(t0, t1)
    return s.data.astype(np.float64), s.stats.sampling_rate


def worker(jobs):
    client = SDSClient(SDS)
    rows = []
    for eid, origin, items in jobs:
        bulk = {}
        for it in items:
            for cha in it["channels"]:
                net, sta, loc, c = cha.split(".")
                bulk[cha] = (net, sta, loc, c, UTCDateTime(origin) - 10, UTCDateTime(origin) + 30)
        st = client.get_waveforms_bulk(list(bulk.values()))
        for it in items:
            t = UTCDateTime(it["time"])
            tt = t - UTCDateTime(origin)
            a, b, sc = WIN[it["phase"]]
            s0, s1 = t + a, t + b + sc * tt
            L = s1 - s0
            tp = UTCDateTime(it["p_time"]) if it["p_time"] else t - tt + tt / 1.73
            n1 = tp - NOISE_GAP_S
            n0 = n1 - L
            ps, pn, fs_ = None, None, None
            ok = True
            for cha in it["channels"]:
                xs, fs = window(st, cha, s0, s1)
                xn, fsn = window(st, cha, n0, n1)
                if xs is None or xn is None or len(xs) < 10 or len(xn) < 10:
                    ok = False
                    break
                bs, bn = band_amps(xs, fs) ** 2, band_amps(xn, fs) ** 2
                ps = bs if ps is None else ps + bs
                pn = bn if pn is None else pn + bn
                fs_ = fs
            if not ok:
                continue
            snr = np.sqrt(ps) / np.sqrt(pn)
            row = dict(event_id=eid, phase=it["phase"], network=it["net"], station=it["sta"],
                       location=it["loc"], pick_channel=it["cha"], channels=";".join(it["channels"]),
                       channel_type=it["cha"][:2], fs=fs_, dist_km=it["dist"], magnitude=it["mag"],
                       weight_code=it["wcode"], tt_s=round(tt, 3))
            for c, v in zip(CENTRES, snr):
                row[f"snr_{c:g}"] = v
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    ev = pd.read_csv(EVENT_CSV)
    origin = dict(zip(ev.id, ev.isotime))
    mag = dict(zip(ev.id, ev.magnitude))
    pc = pd.read_csv(PICK_COV, keep_default_na=False, dtype={"location": str})
    pc = pc[(pc.set == "cc") & (pc.in_phase_csv.astype(str) == "True") &
            (pc.covered_rtdd_components.astype(str) == "True")]
    plan = pd.read_csv(PLAN_CC, keep_default_na=False, dtype={"location": str})
    comps = defaultdict(dict)
    for r in plan.itertuples():
        if r.dip != "":
            comps[(r.event_id, r.sensor)][f"{r.network}.{r.station}.{r.location}.{r.channel}"] = float(r.dip)
    ptime = {(r.event_id, r.network, r.station, r.location): r.time_utc
             for r in pc[pc.phase == "P"].itertuples()}
    by_ev = defaultdict(list)
    for r in pc.itertuples():
        sensor = f"{r.network}.{r.station}.{r.location}.{r.channel[:2]}"
        cs = comps.get((r.event_id, sensor), {})
        if r.phase == "P":
            ch = [c for c, d in cs.items() if abs(abs(d) - 90) < 1e-6][:1]
        else:
            ch = sorted(c for c, d in cs.items() if abs(d) < 1e-6)
            if len(ch) != 2:
                continue
        if not ch:
            continue
        by_ev[r.event_id].append(dict(phase=r.phase, time=r.time_utc, net=r.network, sta=r.station,
                                      loc=r.location, cha=r.channel, channels=ch,
                                      dist=r.epi_dist_km, mag=mag.get(r.event_id), wcode=r.weight_code,
                                      p_time=ptime.get((r.event_id, r.network, r.station, r.location), "")))
    jobs = [(e, origin[e], items) for e, items in sorted(by_ev.items())]
    with mp.Pool(args.workers) as pool:
        parts = pool.map(worker, [jobs[k::args.workers] for k in range(args.workers)])
    df = pd.DataFrame([r for p in parts for r in p])
    df.to_csv(f"{OUT}/band_snr_per_pick.csv", index=False, float_format="%.4g")

    cols = [f"snr_{c:g}" for c in CENTRES]
    df["mbin"] = pd.cut(df.magnitude.fillna(0.5), [-9, 1.0, 2.0, 3.0, 9],
                        labels=["M<1", "1<=M<2", "2<=M<3", "M>=3"], right=False)
    df["dbin"] = pd.cut(df.dist_km.astype(float), [0, 15, 30, 61], labels=["0-15 km", "15-30 km", "30-60 km"])
    summ = []
    for keys, g in [(("all", "all", "all"), df)] + \
                   [((ph, "all", "all"), g) for ph, g in df.groupby("phase")] + \
                   [((ph, str(m), "all"), g) for (ph, m), g in df.groupby(["phase", "mbin"], observed=True)] + \
                   [((ph, "all", str(d)), g) for (ph, d), g in df.groupby(["phase", "dbin"], observed=True)] + \
                   [((ph, "all", "type " + t), g) for (ph, t), g in df.groupby(["phase", "channel_type"])]:
        row = dict(phase=keys[0], magnitude=keys[1], group=keys[2], n=len(g))
        for c, col in zip(CENTRES, cols):
            v = g[col].dropna()
            row[f"median_snr_{c:g}"] = float(v.median()) if len(v) else np.nan
            row[f"frac_ge{SNR_OK:g}_{c:g}"] = float((v >= SNR_OK).mean()) if len(v) else np.nan
        summ.append(row)
    s = pd.DataFrame(summ)
    s.to_csv(f"{OUT}/band_snr_summary.csv", index=False, float_format="%.3f")
    # band where the median SNR >= SNR_OK, per phase and magnitude bin
    res = {}
    for r in s.itertuples():
        ok = [c for c in CENTRES if s.loc[r.Index, f"median_snr_{c:g}"] >= SNR_OK]
        res[f"{r.phase}|{r.magnitude}|{r.group}"] = dict(n=int(r.n), median_snr_ge3_from_hz=min(ok) if ok else None,
                                                         median_snr_ge3_to_hz=max(ok) if ok else None)
    json.dump(dict(parameters=dict(windows=WIN, noise_gap_s=NOISE_GAP_S, nfft_s=NFFT_S, taper=TAPER,
                                   centres_hz=CENTRES.tolist(), snr_ok=SNR_OK),
                   n_picks=int(len(df)), n_by_phase=df.phase.value_counts().to_dict(),
                   band_median_snr_ge3=res), open(f"{OUT}/band_snr_summary.json", "w"), indent=1)
    print(json.dumps(res, indent=0)[:4000])


if __name__ == "__main__":
    main()
