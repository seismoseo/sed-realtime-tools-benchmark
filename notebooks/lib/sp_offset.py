# sp_offset.py -- helper functions for notebook 05_gwangyang_sp_offset.ipynb
# (why are the Gwangyang S-P times about 0.27 s shorter than the kim1983 model predicts?).
# Run in conda env 'pyrtdd' (pyrtdd, obspy 1.5.1, numpy, scipy, pandas, pyproj).
#
# Contents
#   1. reference time of the user's hand-pick tables (SAC nz* headers) -> tidy hand-pick table in UTC
#   2. pick loaders (hand, PhaseNet+, scdlrtpicker models) and the gross-outlier rule
#   3. model travel times
#        - NonLinLoc kim1983 grids read through pyrtdd.hdd.NLLGrid (the reader scrtdd uses)
#        - exact flat-layer 1-D first arrivals: layer_thicknesses / direct_ray / head_waves / first_arrival
#          are copied verbatim from install/02_validate_nll_grids.py (validated there against a Fermat
#          minimization); used for kim2011, for the HYPOINVERSE S model and for stations at sea level
#        - first_arrival_vec: the same physics solved for many source-station pairs at once (bisection on
#          the ray parameter); used only for the Vp/Vs and depth scans, and checked in the notebook against
#          the verbatim first_arrival for every pair
#   4. statistics: station (cluster) bootstrap, running median with stations resampled, Wadati fit,
#      weighted fit helpers for the explanation table, median polish (event and station terms)
#   5. waveforms: read, band-pass, horizontal vector amplitude, AIC onset
#   6. NonLinLoc runs: control file, NLLOC_OBS observation files, output parser, misfit along depth
#   7. pyrtdd catalog-only relocation (relocate() copied from runs/gwangyang/dlpicker/scripts/09_reloc.py)
#      and the east/north/up conversion used there (enu())
# No function here changes any input file. Every threshold is an argument; the notebook passes them
# from its parameter cell.

import glob
import json
import math
import os
import shutil
import subprocess

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read
from pyproj import Geod
from scipy.optimize import brentq

GEOD = Geod(ellps="WGS84")


# ------------------------------------------------------------------------------------------------
# 1. reference time of the hand-pick tables
# ------------------------------------------------------------------------------------------------
def sac_reference_time(path):
    # SAC reference time = nzyear/nzjday/nzhour/nzmin/nzsec/nzmsec (millisecond precision by format)
    h = read(path, headonly=True)[0].stats.sac
    return UTCDateTime(year=int(h.nzyear), julday=int(h.nzjday), hour=int(h.nzhour), minute=int(h.nzmin),
                       second=int(h.nzsec), microsecond=int(h.nzmsec) * 1000)


def sac_pick_values(path):
    # header picks a (P) and t0 (S) in seconds after the reference time; SAC 'undefined' = -12345
    h = read(path, headonly=True)[0].stats.sac
    a = float(h.get("a", np.nan))
    t0 = float(h.get("t0", np.nan))
    a = np.nan if a == -12345.0 else a
    t0 = np.nan if t0 == -12345.0 else t0
    return a, t0


def spotcheck_table(spot_dir, table_dir):
    # compare every copied SAC file's header picks with the table values of the same event and station
    rows = []
    for f in sorted(glob.glob(os.path.join(spot_dir, "*", "*", "*.sac"))):
        src = f.split(os.sep)[-3]
        ev = os.path.basename(f)[:14]
        tr = read(f, headonly=True)[0]
        sta, cha = tr.stats.station, tr.stats.channel
        a, t0 = sac_pick_values(f)
        t = pd.read_csv(os.path.join(table_dir, f"{ev}_manual_phasenet_pick_table.csv")).set_index("Station")
        cp, cs = ("Manual_P", "Manual_S") if src == "manual_picks" else ("PhaseNet_P", "PhaseNet_S")
        rows.append(dict(source_folder=src, kma_id=ev, station=sta, channel=cha,
                         sac_reference_utc=str(sac_reference_time(f)), sac_a_s=a, table_P_s=t.loc[sta, cp],
                         sac_t0_s=t0, table_S_s=t.loc[sta, cs],
                         abs_diff_P_us=abs(a - t.loc[sta, cp]) * 1e6, abs_diff_S_us=abs(t0 - t.loc[sta, cs]) * 1e6))
    return pd.DataFrame(rows)


def reference_from_ml_picks(table_dir, ml_dir, events):
    # the table's PhaseNet columns are the 2026-04-22 SeisBench-PhaseNet picks written into the server B SAC
    # headers; their absolute times are in <ml_dir>/<event>_picks.csv. absolute - relative = reference time
    rows = []
    for ev in events:
        t = pd.read_csv(os.path.join(table_dir, f"{ev}_manual_phasenet_pick_table.csv")).set_index("Station")
        ml = pd.read_csv(os.path.join(ml_dir, f"{ev}_picks.csv"))
        ref = []
        for r in ml.itertuples():
            col = "PhaseNet_" + r.Phase
            if r.Station in t.index and np.isfinite(t.loc[r.Station, col]):
                ref.append(UTCDateTime(r.Time).timestamp - float(t.loc[r.Station, col]))
        ref = np.array(ref)
        med = float(np.median(ref))
        n_tab = int(t["PhaseNet_P"].notna().sum() + t["PhaseNet_S"].notna().sum())
        rows.append(dict(kma_id=ev, n_ml_picks=len(ml), n_table_values=n_tab, n_matched=len(ref),
                         reference_from_ml_utc=str(UTCDateTime(med)),
                         spread_us=float((ref.max() - ref.min()) * 1e6), ref_ts=med))
    return pd.DataFrame(rows)


def build_manual_picks_utc(table_dir, ref_by_event, stations_sensor):
    # tidy table: one row per hand pick, absolute UTC = SAC reference time + table value
    rows = []
    for ev, ref in sorted(ref_by_event.items()):
        t = pd.read_csv(os.path.join(table_dir, f"{ev}_manual_phasenet_pick_table.csv"))
        for r in t.itertuples():
            for ph, val in (("P", r.Manual_P), ("S", r.Manual_S)):
                if not np.isfinite(val):
                    continue
                tt = UTCDateTime(ref) + float(val)
                rows.append(dict(kma_id=ev, network="KS", station=r.Station, sensor=stations_sensor.get(r.Station, ""),
                                 phase=ph, time=tt.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                                 rel_time_s=float(val), sac_reference_utc=UTCDateTime(ref).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                                 source_table=f"{ev}_manual_phasenet_pick_table.csv",
                                 source_header="a" if ph == "P" else "t0"))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# 2. picks
# ------------------------------------------------------------------------------------------------
def load_picks(hand_csv, pnplus_csv, dl_csv, dl_models):
    # long table: source, kma_id (str), station, phase, ts (POSIX seconds), time (ISO)
    out = []
    h = pd.read_csv(hand_csv, dtype={"kma_id": str})
    out.append(pd.DataFrame(dict(source="hand", kma_id=h.kma_id, station=h.station, phase=h.phase, time=h.time)))
    p = pd.read_csv(pnplus_csv, dtype={"kma_id": str})
    out.append(pd.DataFrame(dict(source="phasenet_plus", kma_id=p.kma_id, station=p.station, phase=p.phase, time=p.time)))
    dl_status = {}
    if dl_csv is not None and os.path.exists(dl_csv):
        d = pd.read_csv(dl_csv, dtype={"kma_id": str})
        for m in dl_models:
            q = d[(d.variant == m) & d.in_window.astype(bool)].copy()
            dl_status[m] = int(q.kma_id.nunique())
            if q.empty:
                continue
            q["t"] = pd.to_datetime(q.time, utc=True)
            # one pick per event, station and phase: the most confident one (ties: the earlier one)
            q = q.sort_values(["confidence", "t"], ascending=[False, True]).groupby(["kma_id", "station", "phase"]).head(1)
            out.append(pd.DataFrame(dict(source="dl_" + m, kma_id=q.kma_id, station=q.station, phase=q.phase,
                                         time=q.t.dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))))
    pk = pd.concat(out, ignore_index=True)
    pk["ts"] = [UTCDateTime(x).timestamp for x in pk.time]
    return pk, dl_status


def load_events(dtcc_csv, idmap_csv):
    e = pd.read_csv(dtcc_csv, dtype={"kma_id": str})
    m = pd.read_csv(idmap_csv, dtype={"kma_id": str})
    e = e.merge(m[["kma_id", "kma_origin_utc", "kma_ml"]].rename(columns={"kma_ml": "ml"}), on="kma_id")
    e["origin_ts"] = [UTCDateTime(x).timestamp for x in e.origin_time_pha_datum]
    return e.sort_values("rtdd_id").reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# 3. travel times
# ------------------------------------------------------------------------------------------------
def epi_dist_km(lat, lon, slat, slon):
    _, _, d = GEOD.inv(lon, lat, slon, slat)
    return d / 1000.0


def grid_times(ttt, lat, lon, dep, sta):
    # sta: row with Latitude, Longitude, Elevation_m -> (T_P, T_S) from the NonLinLoc grids
    tp = ttt.compute(lat, lon, dep, sta.Latitude, sta.Longitude, sta.Elevation_m, "P")
    ts = ttt.compute(lat, lon, dep, sta.Latitude, sta.Longitude, sta.Elevation_m, "S")
    return tp, ts


# --- verbatim copy from install/02_validate_nll_grids.py (exact flat-layer first arrivals) ---------
def layer_thicknesses(z_top, z_bot, tops):
    # thickness of each layer inside the depth interval [z_top, z_bot]
    bots = np.append(tops[1:], np.inf)
    return np.clip(np.minimum(bots, z_bot) - np.maximum(tops, z_top), 0.0, None)


def direct_ray(x, zs, zr, tops, v):
    # ray going straight up from the source (depth zs) to the receiver (depth zr < zs), Snell's law
    h = layer_thicknesses(zr, zs, tops)
    use = h > 0
    h, vv = h[use], v[use]
    vsrc = v[np.searchsorted(tops, zs, side="right") - 1]
    if x == 0.0:
        return float(np.sum(h / vv)), 180.0
    vmax = vv.max()

    def xoff(u):  # u = p * vmax in [0, 1)
        p = u / vmax
        return np.sum(h * p * vv / np.sqrt(1.0 - (p * vv) ** 2)) - x

    u = brentq(xoff, 0.0, 1.0 - 1e-15, xtol=1e-15, rtol=1e-15, maxiter=500)
    p = u / vmax
    t = float(np.sum(h / (vv * np.sqrt(1.0 - (p * vv) ** 2))))
    theta_src = math.degrees(math.asin(min(1.0, p * vsrc)))   # angle from the UPWARD vertical
    return t, 180.0 - theta_src                                 # dip: 0 = down, 180 = up


def head_waves(x, zs, zr, tops, v):
    # head wave along the top of every deeper, faster layer k: down from the source, along the interface,
    # up to the receiver. Returns a list of (time, interface depth, dip at the source) for valid branches.
    out = []
    vsrc = v[np.searchsorted(tops, zs, side="right") - 1]
    for k in range(1, len(tops)):
        zk = tops[k]
        if zk <= max(zs, zr):
            continue
        hd = layer_thicknesses(zs, zk, tops)[:k]
        hu = layer_thicknesses(zr, zk, tops)[:k]
        vabove = v[:k][(hd + hu) > 0]
        if v[k] <= vabove.max():
            continue
        q = np.sqrt(1.0 / v[:k] ** 2 - 1.0 / v[k] ** 2)
        xcrit = np.sum((hd + hu) * (v[:k] / v[k]) / np.sqrt(1.0 - (v[:k] / v[k]) ** 2))
        if x < xcrit:
            continue
        t = x / v[k] + np.sum((hd + hu) * q)
        out.append((float(t), zk, math.degrees(math.asin(vsrc / v[k]))))
    return out


def first_arrival(x, zs, zr, tops, v):
    t, dip = direct_ray(x, zs, zr, tops, v)
    best = (t, "direct", dip)
    for th, zk, dh in head_waves(x, zs, zr, tops, v):
        if th < best[0]:
            best = (th, f"head{zk:g}km", dh)
    return best
# --- end of verbatim copy ---------------------------------------------------------------------


def crossover_distance(zs, zr, tops, v, x0=30.0, x1=120.0):
    # epicentral distance where the first arrival switches from the direct wave to a head wave
    xs = np.arange(x0, x1, 0.01)
    br = [first_arrival(x, zs, zr, tops, v)[1] for x in xs]
    for x, b in zip(xs, br):
        if b != "direct":
            return float(x)
    return np.nan


def first_arrival_vec(x, zs, zr, tops, v, n_iter=64):
    # the physics of first_arrival() (fastest of the direct ray and the head waves along the top of every
    # deeper, faster layer) for many (distance, source depth, receiver depth) at once: the direct ray is found
    # by bisection on u = p * vmax in [0, 1) for all pairs together (n_iter halvings: 2^-64 of the interval).
    # Only the first-arrival time is returned. Checked against the verbatim first_arrival in the notebook.
    x, zs, zr = (np.atleast_1d(np.asarray(a, float)) for a in (x, zs, zr))
    tops, v = np.asarray(tops, float), np.asarray(v, float)
    bots = np.append(tops[1:], np.inf)
    h = np.clip(np.minimum(bots[None, :], zs[:, None]) - np.maximum(tops[None, :], zr[:, None]), 0.0, None)
    used = h > 0
    vmax = np.max(np.where(used, v[None, :], 0.0), axis=1)
    lo = np.zeros(len(x))
    hi = np.full(len(x), 1.0 - 1e-15)
    for _ in range(n_iter):
        u = 0.5 * (lo + hi)
        pv = (u / vmax)[:, None] * v[None, :]
        xo = np.sum(np.where(used, h * pv / np.sqrt(np.clip(1.0 - pv ** 2, 1e-300, None)), 0.0), axis=1)
        far = xo > x
        hi = np.where(far, u, hi)
        lo = np.where(far, lo, u)
    pv = (0.5 * (lo + hi) / vmax)[:, None] * v[None, :]
    t = np.sum(np.where(used, h / (v[None, :] * np.sqrt(np.clip(1.0 - pv ** 2, 1e-300, None))), 0.0), axis=1)
    t = np.where(x == 0.0, np.sum(np.where(used, h / v[None, :], 0.0), axis=1), t)
    for k in range(1, len(tops)):
        zk = tops[k]
        hd = np.clip(np.minimum(bots[None, :k], zk) - np.maximum(tops[None, :k], zs[:, None]), 0.0, None)
        hu = np.clip(np.minimum(bots[None, :k], zk) - np.maximum(tops[None, :k], zr[:, None]), 0.0, None)
        hh = hd + hu
        vab = np.max(np.where(hh > 0, v[None, :k], 0.0), axis=1)
        ok = (zk > np.maximum(zs, zr)) & (v[k] > vab)
        rat = v[:k] / v[k]
        # a boundary with no speed increase (e.g. an inserted boundary with the same speed on both sides) gives
        # inf/NaN here; such branches are already excluded by 'ok' (v[k] > speeds above), as in head_waves()
        with np.errstate(divide="ignore", invalid="ignore"):
            q = np.sqrt(1.0 / v[:k] ** 2 - 1.0 / v[k] ** 2)
            xcrit = np.sum(hh * rat / np.sqrt(1.0 - rat ** 2), axis=1)
            th = x / v[k] + np.sum(hh * q, axis=1)
        ok &= x >= xcrit
        t = np.where(ok & (th < t), th, t)
    return t


# ------------------------------------------------------------------------------------------------
# 4. statistics
# ------------------------------------------------------------------------------------------------
def cluster_bootstrap_median(values, clusters, n_boot, rng):
    # resample clusters (stations) with replacement, take all their values, median of the pooled sample
    values = np.asarray(values, float)
    clusters = np.asarray(clusters)
    uc, inv = np.unique(clusters, return_inverse=True)
    groups = [values[inv == i] for i in range(len(uc))]
    meds = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(uc), len(uc))
        meds[b] = np.median(np.concatenate([groups[i] for i in pick]))
    return float(np.median(values)), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def running_median(x, y, groups, centers, half_width, min_n, min_groups, n_boot, rng):
    # median of y in windows [c - half_width, c + half_width) of x; a window needs >= min_n values from
    # >= min_groups groups (stations). Its 95% interval resamples the GROUPS (stations) of the window with
    # replacement, as every other interval of the notebook does; n_boot = 0 gives the median only
    x, y, groups = np.asarray(x, float), np.asarray(y, float), np.asarray(groups)
    rows = []
    for c in centers:
        m = (x >= c - half_width) & (x < c + half_width)
        n = int(m.sum())
        ng = int(len(np.unique(groups[m])))
        if n < min_n or ng < min_groups:
            rows.append(dict(center_km=c, n=n, n_groups=ng, median=np.nan, lo=np.nan, hi=np.nan))
            continue
        if n_boot > 0:
            med, lo, hi = cluster_bootstrap_median(y[m], groups[m], n_boot, rng)
        else:
            med, lo, hi = float(np.median(y[m])), np.nan, np.nan
        rows.append(dict(center_km=c, n=n, n_groups=ng, median=med, lo=lo, hi=hi))
    return pd.DataFrame(rows)


def station_bootstrap_weights(stations, n_boot, rng):
    # one row per bootstrap sample: how often each pair's station was drawn (stations resampled with
    # replacement); a pair weight of 2 means the station was drawn twice, 0 that it was left out
    st = np.asarray(stations)
    us, inv = np.unique(st, return_inverse=True)
    W = np.empty((n_boot, len(st)))
    for b in range(n_boot):
        cnt = np.bincount(rng.integers(0, len(us), len(us)), minlength=len(us))
        W[b] = cnt[inv]
    return W


def best_column(R, w):
    # index of the column of R (pairs x candidates) with the smallest weighted sum of squared residuals
    return int(np.argmin(w @ (R ** 2)))


def weighted_stats(r, w, dist, near_km):
    # RMS, trend against distance (s per 100 km, weighted least squares), and medians of the residuals of
    # the pairs within each distance in near_km and beyond the last one; w are integer pair weights
    r, w, dist = np.asarray(r, float), np.asarray(w, float), np.asarray(dist, float)
    W = w.sum()
    rms = float(np.sqrt(np.sum(w * r ** 2) / W))
    xm, ym = np.sum(w * dist) / W, np.sum(w * r) / W
    trend = float(np.sum(w * (dist - xm) * (r - ym)) / np.sum(w * (dist - xm) ** 2) * 100.0)
    rep = np.repeat(np.arange(len(r)), w.astype(int))
    rr, dd = r[rep], dist[rep]
    out = dict(rms=rms, trend=trend)
    for km in near_km:
        q = rr[dd < km]
        out[f"med_lt_{km:g}"] = float(np.median(q)) if len(q) else np.nan
    q = rr[dd >= near_km[-1]]
    out[f"med_ge_{near_km[-1]:g}"] = float(np.median(q)) if len(q) else np.nan
    return out


def median_polish(values, rows, cols, n_iter=20):
    # Tukey's median polish: values = overall + row term + column term + residual. Column (station) and row
    # (event) medians of the residuals are subtracted in turn; both sets of terms are centered on zero
    v = pd.Series(np.asarray(values, float))
    r = pd.Series(np.asarray(rows))
    c = pd.Series(np.asarray(cols))
    rt = pd.Series(0.0, index=sorted(r.unique()))
    ct = pd.Series(0.0, index=sorted(c.unique()))
    mu = float(v.median())
    for _ in range(n_iter):
        res = v - mu - r.map(rt) - c.map(ct)
        ct = ct + res.groupby(c).median()
        res = v - mu - r.map(rt) - c.map(ct)
        rt = rt + res.groupby(r).median()
        m = float(rt.median())
        rt, mu = rt - m, mu + m
        m = float(ct.median())
        ct, mu = ct - m, mu + m
    res = v - mu - r.map(rt) - c.map(ct)
    return mu, rt, ct, res.to_numpy()


def wadati_fit(sp, tp, event):
    # S-P = m * tP + c_event  (one intercept per event, so the origin times do not matter for m)
    ev = pd.Categorical(event)
    X = np.column_stack([tp] + [(ev.codes == i).astype(float) for i in range(len(ev.categories))])
    coef, *_ = np.linalg.lstsq(X, sp, rcond=None)
    res = sp - X @ coef
    return float(coef[0]), dict(zip(ev.categories, coef[1:])), res


def wadati_bootstrap(sp, tp, event, station, n_boot, rng):
    # resample stations with replacement (all event pairs of a station together); refit the slope each time
    sp, tp, event, station = (np.asarray(a) for a in (sp, tp, event, station))
    st = np.unique(station)
    idx = [np.flatnonzero(station == s) for s in st]
    slopes = np.empty(n_boot)
    for b in range(n_boot):
        ii = np.concatenate([idx[j] for j in rng.integers(0, len(st), len(st))])
        slopes[b] = wadati_fit(sp[ii], tp[ii], event[ii])[0]
    return slopes


def sp_1d(dist_km, zs_km, zr_km, tops, vp, vs):
    # model S-P from the exact flat-layer first arrivals (separately fastest P and fastest S)
    tops, vp, vs = (np.asarray(a, float) for a in (tops, vp, vs))
    return np.array([first_arrival(x, zs, zr, tops, vs)[0] - first_arrival(x, zs, zr, tops, vp)[0]
                     for x, zs, zr in zip(dist_km, zs_km, zr_km)])


# ------------------------------------------------------------------------------------------------
# 5. waveforms
# ------------------------------------------------------------------------------------------------
def read_station(wf_dir, ev, sta):
    # the 3 components of one station for one event (raw counts, 100 Hz)
    st = read(os.path.join(wf_dir, ev, f"{ev}.KS.{sta}.*.sac"))
    return st


def bandpass(st, fmin, fmax, corners, taper_frac, zerophase):
    # zerophase=False (one pass, causal) never moves energy ahead of the true onset; a zero-phase filter
    # can show ringing before an arrival and so make it look earlier than it is
    st = st.copy()
    st.detrend("demean")
    st.detrend("linear")
    st.taper(taper_frac)
    st.filter("bandpass", freqmin=fmin, freqmax=fmax, corners=corners, zerophase=zerophase)
    return st


def component(st, comp):
    q = [tr for tr in st if tr.stats.channel[-1] == comp]
    return q[0] if q else None


def horizontal_vector(st):
    # sqrt(N^2 + E^2) on the common time span: does not depend on the (unverified) sensor orientation
    n, e = component(st, "N"), component(st, "E")
    if n is None or e is None:
        return None, None
    t0 = max(n.stats.starttime, e.stats.starttime)
    t1 = min(n.stats.endtime, e.stats.endtime)
    n = n.slice(t0, t1)
    e = e.slice(t0, t1)
    k = min(n.stats.npts, e.stats.npts)
    amp = np.sqrt(n.data[:k].astype(float) ** 2 + e.data[:k].astype(float) ** 2)
    t = n.stats.starttime.timestamp + np.arange(k) * n.stats.delta
    return t, amp


def horizontal_components(st):
    # N and E samples on their common time span (POSIX seconds), or (None, None, None)
    n, e = component(st, "N"), component(st, "E")
    if n is None or e is None:
        return None, None, None
    t0 = max(n.stats.starttime, e.stats.starttime)
    t1 = min(n.stats.endtime, e.stats.endtime)
    n = n.slice(t0, t1)
    e = e.slice(t0, t1)
    k = min(n.stats.npts, e.stats.npts)
    t = n.stats.starttime.timestamp + np.arange(k) * n.stats.delta
    return t, n.data[:k].astype(float), e.data[:k].astype(float)


def aic_onset(t, x, edge=10):
    # Akaike information criterion change point (Maeda 1985) of a window x (samples x components):
    # AIC(k) = k log(var(x[:k])) + (n - k - 1) log(var(x[k:])), the variances summed over the components.
    # The onset is the first sample of the second part at the smallest AIC; 'edge' samples at both ends of
    # the window are not allowed
    x = np.asarray(x, float)
    if x.ndim == 1:
        x = x[:, None]
    n = len(x)
    k = np.arange(edge, n - edge)
    c1 = np.cumsum(x, axis=0)
    c2 = np.cumsum(x ** 2, axis=0)
    s1, q1 = c1[k - 1], c2[k - 1]
    s2, q2 = c1[-1] - s1, c2[-1] - q1
    v1 = np.sum(q1 / k[:, None] - (s1 / k[:, None]) ** 2, axis=1)
    m = (n - k)[:, None]
    v2 = np.sum(q2 / m - (s2 / m) ** 2, axis=1)
    a = k * np.log(v1) + (n - k - 1) * np.log(v2)
    return float(t[k[int(np.argmin(a))]])


def window(t, y, t0, t1):
    m = (t >= t0) & (t <= t1)
    return t[m], y[m]


# ------------------------------------------------------------------------------------------------
# plotting helpers
# ------------------------------------------------------------------------------------------------
def legend_above(fig, axes, handles, labels, ncol, pad=0.008, fontsize=None):
    # opaque legend placed above the union of the tight bounding boxes of 'axes' (figure coordinates)
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bbs = [ax.get_tightbbox(r) for ax in np.atleast_1d(axes).ravel()]
    bb = Bbox.union(bbs).transformed(fig.transFigure.inverted())
    leg = fig.legend(handles, labels, loc="lower center", bbox_to_anchor=((bb.x0 + bb.x1) / 2.0, bb.y1 + pad),
                     ncol=ncol, frameon=True, framealpha=1.0, facecolor="white", edgecolor="0.6", fontsize=fontsize)
    leg.set_zorder(100)
    return leg


def text_above(fig, artists, text, pad=0.006, **kw):
    # one line of text (e.g. a figure title) placed above the union of the artists' tight bounding boxes
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bb = Bbox.union([a.get_tightbbox(r) for a in artists]).transformed(fig.transFigure.inverted())
    return fig.text(bb.x0, bb.y1 + pad, text, ha="left", va="bottom", **kw)


def text_below(fig, artists, text, pad=0.004, **kw):
    # a note placed below the union of the artists' tight bounding boxes (left-aligned)
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bb = Bbox.union([a.get_tightbbox(r) for a in artists]).transformed(fig.transFigure.inverted())
    return fig.text(bb.x0, bb.y0 - pad, text, ha="left", va="top", **kw)


def save_fig(fig, fig_dir, name, dpi=200):
    png = os.path.join(fig_dir, name + ".png")
    pdf = os.path.join(fig_dir, name + ".pdf")
    fig.savefig(png, dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    return png, pdf


# ------------------------------------------------------------------------------------------------
# 6. NonLinLoc
# ------------------------------------------------------------------------------------------------
def write_nlloc_obs(path, picks, s_shift=0.0, p_err=0.05, s_err=0.10):
    # NLLOC_OBS: station inst comp onset phase FM date hhmm ss.ssss GAU err coda amp per priorwt
    with open(path, "w") as f:
        for r in picks.itertuples():
            t = UTCDateTime(r.ts + (s_shift if r.phase == "S" else 0.0))
            err = p_err if r.phase == "P" else s_err
            sec = t.second + t.microsecond * 1e-6
            f.write(f"{r.station:<6s} ?    ?    ? {r.phase:<6s} ? {t.year:04d}{t.month:02d}{t.day:02d} "
                    f"{t.hour:02d}{t.minute:02d} {sec:7.4f} GAU {err:9.2e} -1.00e+00 -1.00e+00 -1.00e+00 1.0\n")


def write_nlloc_control(path, obs_file, time_root, out_root, s):
    # s: dict of settings from the notebook parameter cell
    lines = [
        "CONTROL 1 54321",
        f"TRANS TRANS_MERC WGS-84 {s['trans_lat']:.4f} {s['trans_lon']:.4f} 0.0",
        "LOCSIG notebook 05_gwangyang_sp_offset",
        f"LOCFILES {obs_file} NLLOC_OBS {time_root} {out_root}",
        "LOCHYPOUT SAVE_NLLOC_ALL",
        f"LOCSEARCH OCT {s['oct_init'][0]} {s['oct_init'][1]} {s['oct_init'][2]} {s['oct_min_node_km']} "
        f"{s['oct_max_nodes']} {s['oct_num_scatter']} 0 1",
        f"LOCGRID {s['grid_n'][0]} {s['grid_n'][1]} {s['grid_n'][2]} {s['grid_orig'][0]} {s['grid_orig'][1]} "
        f"{s['grid_orig'][2]} {s['grid_d'][0]} {s['grid_d'][1]} {s['grid_d'][2]} PROB_DENSITY SAVE",
        f"LOCMETH {s['method']} 9999.0 4 -1 -1 -1.0 6 -1.0 1",
        f"LOCGAU {s['gau_sigma_s']} {s['gau_corr_len_km']}",
        "LOCPHASEID P P",
        "LOCPHASEID S S",
        f"LOCQUAL2ERR {' '.join(str(x) for x in s['qual2err'])}",
        "LOCANGLES ANGLES_NO 5",
        "LOCPHSTAT 9999.0 -1 9999.0 1.0 1.0 9999.9 -9999.9 9999.9",
    ]
    if s.get("gau2") is not None:
        lines.insert(9, f"LOCGAU2 {s['gau2'][0]} {s['gau2'][1]} {s['gau2'][2]}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return lines


def parse_nlloc_hyp(path):
    # maximum-likelihood hypocenter, origin time, quality and covariance (km^2) from a .hyp file
    out = {}
    phases = []
    in_ph = False
    for line in open(path):
        w = line.split()
        if not w:
            continue
        if w[0] == "GEOGRAPHIC":
            yr, mo, dy, hr, mi = (int(x) for x in w[2:7])
            sec = float(w[7])
            out["origin"] = UTCDateTime(yr, mo, dy, hr, mi, 0) + sec
            out["lat"], out["lon"], out["depth_km"] = float(w[9]), float(w[11]), float(w[13])
        elif w[0] == "HYPOCENTER":
            out["x_km"], out["y_km"], out["z_km"] = float(w[2]), float(w[4]), float(w[6])
        elif w[0] == "QUALITY":
            d = dict(zip(w[1::2], w[2::2]))
            out["rms_s"], out["nphs"], out["gap_deg"] = float(d["RMS"]), int(d["Nphs"]), float(d["Gap"])
        elif w[0] == "STATISTICS":
            d = dict(zip(w[1::2], w[2::2]))
            for k in ("CovXX", "XY", "XZ", "YY", "YZ", "ZZ", "ExpectX", "Y", "Z"):
                out["stat_" + k] = float(d[k])
        elif w[0] == "NLLOC":
            out["status"] = " ".join(w[2:])
        elif w[0] == "PHASE":
            in_ph = True
            continue
        elif w[0] == "END_PHASE":
            in_ph = False
        elif in_ph:
            i = w.index(">")
            phases.append(dict(station=w[0], phase=w[4], ttpred=float(w[i + 1]), res=float(w[i + 2]),
                               weight=float(w[i + 3])))
    out["sig_x_km"] = math.sqrt(out["stat_CovXX"])
    out["sig_y_km"] = math.sqrt(out["stat_YY"])
    out["sig_z_km"] = math.sqrt(out["stat_ZZ"])
    return out, pd.DataFrame(phases)


def nlloc_ot_sigma(res, ph, picks, ttt, stations, p_err, s_err, gau_sigma, step_km=0.05):
    # NonLinLoc reports no origin-time uncertainty. With GAU_ANALYTIC the origin time is the weighted mean
    # of (pick - predicted travel time), so its variance = g' C g + 1 / sum(w): C = NonLinLoc's location
    # covariance (km^2), g = -(weighted mean travel-time gradient) in s/km, w = 1 / (pick error^2 + LOCGAU^2)
    lat, lon, dep = res["lat"], res["lon"], res["depth_km"]
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    p = np.radians(lat)
    M = a * (1 - e2) / (1 - e2 * np.sin(p) ** 2) ** 1.5 / 1000.0
    N = a / np.sqrt(1 - e2 * np.sin(p) ** 2) / 1000.0
    dlat = np.degrees(step_km / M)
    dlon = np.degrees(step_km / (N * np.cos(p)))
    g = np.zeros(3)
    wsum = 0.0
    for r in picks.itertuples():
        s = stations.loc[r.station]
        def tt(la, lo, de):
            return ttt.compute(la, lo, de, s.Latitude, s.Longitude, s.Elevation_m, r.phase)
        grad = np.array([(tt(lat, lon + dlon, dep) - tt(lat, lon - dlon, dep)) / (2 * step_km),
                         (tt(lat + dlat, lon, dep) - tt(lat - dlat, lon, dep)) / (2 * step_km),
                         (tt(lat, lon, dep + step_km) - tt(lat, lon, dep - step_km)) / (2 * step_km)])
        w = 1.0 / ((p_err if r.phase == "P" else s_err) ** 2 + gau_sigma ** 2)
        g += w * grad
        wsum += w
    g = -g / wsum
    C = np.array([[res["stat_CovXX"], res["stat_XY"], res["stat_XZ"]],
                  [res["stat_XY"], res["stat_YY"], res["stat_YZ"]],
                  [res["stat_XZ"], res["stat_YZ"], res["stat_ZZ"]]])
    return float(np.sqrt(g @ C @ g + 1.0 / wsum))


def depth_misfit_slice(ttt, lat, lon, depths, picks, stations, p_err, s_err, gau_sigma, s_shift=0.0):
    # the GAU_ANALYTIC misfit of NonLinLoc along depth at a fixed epicenter: for every trial depth the best
    # origin time (weighted mean of pick - travel time) and the weighted sum of squared residuals, with weights
    # 1 / (pick error^2 + LOCGAU sigma^2). A slice through the misfit, not a full re-location at each depth
    ph = picks.phase.to_numpy()
    obs = picks.ts.to_numpy() + np.where(ph == "S", s_shift, 0.0)
    w = 1.0 / (np.where(ph == "P", p_err, s_err) ** 2 + gau_sigma ** 2)
    sta = [stations.loc[s] for s in picks.station]
    out = np.empty(len(depths))
    for j, z in enumerate(depths):
        tt = np.array([ttt.compute(lat, lon, z, s.Latitude, s.Longitude, s.Elevation_m, p) for s, p in zip(sta, ph)])
        ot = np.sum(w * (obs - tt)) / np.sum(w)
        out[j] = np.sum(w * (obs - ot - tt) ** 2)
    return out


def run_nlloc(nll_bin, run_dir, obs_picks, s, s_shift=0.0, p_err=0.05, s_err=0.10, nice=10):
    # one NLLoc run per event (one obs file per event); returns parsed results
    os.makedirs(run_dir, exist_ok=True)
    obs = os.path.join(run_dir, "obs.nll")
    write_nlloc_obs(obs, obs_picks, s_shift=s_shift, p_err=p_err, s_err=s_err)
    out_root = os.path.join(run_dir, "loc", "event")
    os.makedirs(os.path.dirname(out_root), exist_ok=True)
    ctl = os.path.join(run_dir, "nlloc.in")
    write_nlloc_control(ctl, obs, s["time_root"], out_root, s)
    log = os.path.join(run_dir, "nlloc.log")
    with open(log, "w") as lf:
        subprocess.run(["nice", "-n", str(nice), os.path.join(nll_bin, "NLLoc"), ctl], cwd=run_dir, stdout=lf,
                       stderr=subprocess.STDOUT, check=True)
    hyps = sorted(f for f in glob.glob(os.path.join(run_dir, "loc", "event.*.grid0.loc.hyp")) if ".sum." not in f)
    if len(hyps) != 1:
        raise RuntimeError(f"{run_dir}: expected one .hyp file, found {len(hyps)}")
    return parse_nlloc_hyp(hyps[0])


# ------------------------------------------------------------------------------------------------
# 7. pyrtdd catalog-only relocation (as in runs/gwangyang/dlpicker/scripts/09_reloc.py)
# ------------------------------------------------------------------------------------------------
def options_dict(o):
    d = {}
    for k in dir(o):
        if k.startswith("_"):
            continue
        v = getattr(o, k)
        if callable(v):
            continue
        d[k] = v if isinstance(v, (int, float, str, bool, list)) else str(v)
    return d


def enu(lat, lon, depth_km, lat0, lon0, dep0):
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    p = np.radians(lat0)
    M = a * (1 - e2) / (1 - e2 * np.sin(p) ** 2) ** 1.5
    N = a / np.sqrt(1 - e2 * np.sin(p) ** 2)
    n = M * np.radians(np.asarray(lat) - lat0)
    e = N * np.cos(p) * np.radians(np.asarray(lon) - lon0)
    u = -(np.asarray(depth_km) - dep0) * 1000.0
    return e, n, u


def relocate(outdir, nll_path, settings_extra):
    import pyrtdd.hdd as hdd
    cat = hdd.Catalog(f"{outdir}/station.csv", f"{outdir}/event.csv", f"{outdir}/phase.csv")
    cfg = hdd.Config()
    ttt = hdd.NLLGrid(gridPath=nll_path, gridModel="kim1983", maxSearchDistance=0.1)
    dd = hdd.DD(cat, cfg, ttt)
    cc = hdd.ClusteringOptions()
    cc.numEllipsoids = 0
    cc.maxNeighbourDist = 10.0
    cc.minNumNeigh = 1
    cc.maxNumNeigh = 0
    cc.minNumPhases = 1
    so = hdd.SolverOptions()
    so.absLocConstraintStart = 0.0
    so.absLocConstraintEnd = 0.0
    so.dampingFactorStart = 0.01
    so.dampingFactorEnd = 0.01
    clusters = dd.findClusters(cc)
    n_clusters = len(clusters)
    proc = f"{outdir}/processing"
    if os.path.isdir(proc):
        shutil.rmtree(proc)
    new = dd.relocateMultiEvents(clusters, so, saveProcessing=True, processingDataDir=proc)
    new.writeToFile(f"{outdir}/relocated-station.csv", f"{outdir}/relocated-event.csv", f"{outdir}/relocated-phase.csv")
    s = dict(Config=options_dict(cfg), ClusteringOptions=options_dict(cc), SolverOptions=options_dict(so),
             NLLGrid=dict(gridPath=nll_path, gridModel="kim1983", maxSearchDistance=0.1, swapBytes=False,
                          maxOpenFiles=512, accessMethod="KeepOpen (default)"),
             relocateMultiEvents=dict(saveProcessing=True, processingDataDir=proc),
             n_clusters=n_clusters, catalog_files=[f"{outdir}/station.csv", f"{outdir}/event.csv", f"{outdir}/phase.csv"])
    s.update(settings_extra)
    json.dump(s, open(f"{outdir}/settings.json", "w"), indent=1, default=str)
    return n_clusters


def dd_run(outdir, catalog_dir, nll_path, s_shift_of, settings_extra):
    # one catalog-only relocation in a fresh folder: station.csv and the centroid start (event_centroid_start.csv)
    # copied, phase.csv written with every S pick moved by s_shift_of(eventId, stationCode) seconds
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    shutil.copyfile(f"{catalog_dir}/station.csv", f"{outdir}/station.csv")
    shutil.copyfile(f"{catalog_dir}/event_centroid_start.csv", f"{outdir}/event.csv")
    ph = pd.read_csv(f"{catalog_dir}/phase.csv", keep_default_na=False, dtype=str)
    shifts = np.array([s_shift_of(int(e), s) if ty == "S" else 0.0 for e, s, ty in zip(ph.eventId, ph.stationCode, ph.type)])
    ph["isotime"] = [(UTCDateTime(t) + dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ") if dt != 0.0 else t
                     for t, dt in zip(ph.isotime, shifts)]
    ph.to_csv(f"{outdir}/phase.csv", index=False)
    n_cl = relocate(outdir, nll_path, settings_extra)
    ev = pd.read_csv(f"{outdir}/relocated-event.csv").set_index("id")
    return ev, n_cl, ph, shifts


def dd_changes(a, b):
    # b minus a per event (east/north/up in m, origin time in s), the cluster-mean part of it, and each event's
    # change relative to the others (its change minus the cluster-mean change; 3-D length in m)
    b = b.loc[a.index]
    e, n, u = enu(b.latitude.to_numpy(), b.longitude.to_numpy(), b.depth.to_numpy(),
                  a.latitude.to_numpy(), a.longitude.to_numpy(), a.depth.to_numpy())
    dot = np.array([UTCDateTime(y) - UTCDateTime(x) for x, y in zip(a.isotime, b.isotime)])
    df = pd.DataFrame({"east_m": e, "north_m": n, "up_m": u, "ot_s": dot}, index=a.index)
    mean = df[["east_m", "north_m", "up_m"]].mean()
    rel = df[["east_m", "north_m", "up_m"]] - mean
    df["relative_m"] = np.sqrt((rel ** 2).sum(axis=1))
    df["total_m"] = np.sqrt((df[["east_m", "north_m", "up_m"]] ** 2).sum(axis=1))
    return df, float(np.sqrt((mean ** 2).sum()))
