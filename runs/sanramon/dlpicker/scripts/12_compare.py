# 12_compare.py -- step 12 helper (conda env 'pyrtdd': obspy, pandas, numpy; plus the project's own
# data/sanramon_2015/tools/ray1d.py for predicted travel times).
#
# Compares the picks of scautopick + scdlrtpicker (one SCML file per variant and event, written by
# 12_dlpicker.sh stage pick) with the NCSS ANALYST picks (data/sanramon_2015/reference_tables/picks_ncss.csv).
# Unlike step 09 (Gwangyang, reference = PhaseNet+), the reference here is human: reviewed NCSS picks with
# Hypoinverse weight codes 0-3 ('usable'; the 15 out-weighted picks with codes 5-8 are left out) and P
# first motions. The analyst did not pick every station, so a DL pick without an analyst partner is not
# necessarily wrong (classes below; 'precision counting plausible' is the upper bound).
#
# Matching (rules of step 09 / step T's 05_compare_picks.py; match() copied, but the station key is
# NET.STA because station codes are not unique across networks here): same event file, same NET.STA, same
# phase; P within --p-tol, S within --s-tol; candidate pairs in order of increasing |dt|, each pick used at
# most once; dt = DL - analyst. The candidates are the analyst picks of EVERY NCSS catalog event whose picks
# fall in the file (origin -120..+120 s), not only the target event's: the files of overlapping events
# (e.g. 72540760 and the mainshock 72540765, 6.3 s apart) then credit a DL pick of the neighbour event as a
# match of that event. Recall counts only the target event's picks.
#
# Reference tiers (each analyst pick of the 26 target events gets exactly one):
#   no_data           the station has no waveform in the playback file (beyond 80 km, or no data served)
#   no_3c_sensor      data, but no sensor the 3-component pickers can use (vertical-only EH etc.; see
#                     12_bindings.py, which copies SeisComP's getThreeComponents test)
#   3c_incomplete     the bound 3-C sensor's record of this event is not complete (triggered recorders: the
#                     record starts after the file start or has gaps)
#   3c_complete       the bound 3-C sensor's record covers the whole file in one piece
# Recall is reported over all usable analyst picks (tier >= no_data), over picks with data, over picks at
# stations with a usable 3-C sensor ('3-C stations'), and over 3c_complete.
#
# Definitions (all in summary.json):
#   event window   : NCSS origin (dl_subset_events.csv) - --win-before s to + --win-after s
#   precision      : DL picks of the phase inside the target event window that match an analyst pick of any
#                    catalog event / all DL picks of that phase inside the window
#   F1             : 2 R P / (R + P) with R = recall over 3-C stations
#   dt statistics  : median |dt|, MAD = median(|dt - median dt|), p95 |dt|, mean dt, median dt, max |dt|
#   predicted times: ray1d.py through the NCSS CON model (inputs/velocity_model.csv, Vs = Vp/1.73), NCSS
#                    routine origin and hypocentre, station elevation from station_channels.csv. Their fit to
#                    the analyst picks is reported (pred_check); --pred-tol is the "near the predicted
#                    arrival" tolerance
#   reference outlier: an analyst pick with |NCSS residual| > --ref-outlier s
#   SNR            : 20 log10(RMS[t, t+1 s] / RMS[t-3 s, t-0.5 s]) on raw counts after demean and a ONE-PASS
#                    2-20 Hz Butterworth band-pass (4 corners), on the bound sensor (P: vertical; S: both
#                    horizontals), for the analyst picks at 3-C stations
#
# A DL pick inside the target window that matches an analyst pick of ANOTHER catalog event is class
# matched_other_event (counted as correct in the precision).
# Classes of unmatched DL picks INSIDE the target window (first that applies):
#   near_duplicate        another DL pick of the same NET.STA and phase within the tolerance is matched or
#                         more confident (or equally confident and earlier)
#   phase_confusion       a DL P within the P tolerance of the analyst S (or, without analyst S, within
#                         --pred-tol of the predicted S and not of the predicted P); a DL S likewise near P
#   reference_outlier     the analyst pick of this phase here is an outlier and the DL pick is near the
#                         predicted time
#   plausible_no_analyst_pick  no analyst pick of this phase at this station, DL pick within --pred-tol of
#                         the predicted time (the analyst simply did not pick this station)
#   timing_disagreement   an analyst pick exists, DL is farther than the tolerance from it but within
#                         --pred-tol of the predicted time
#   plausible_other_event_arrival  within --pred-tol of the predicted P or S of another NCSS catalog event whose
#                         origin lies in the same file (overlapping events of the swarm)
#   noise_or_other        none of the above
# 'precision counting plausible' counts reference_outlier, plausible_no_analyst_pick and
# plausible_other_event_arrival as correct (upper bound).
# Events are also grouped by the time to the nearest other catalog event in their file (event_neighbours.csv):
# none within 120 s / 60-120 s / 15-60 s / <= 15 s (one P pick per model window and the dead time matter there).
# Classes of DL picks OUTSIDE the target window:
#   other_catalog_event   inside the window of another NCSS catalog event (reference_tables/ncss_catalog.csv,
#                         706 events in the wide box)
#   coincident            P picks at >= --coinc-min-stations stations within +-(--coinc-window) s
#   isolated              everything else
#   false picks per station-hour = (coincident + isolated picks inside the searchable span) / searchable hours;
#   searchable = the bound sensor's record from start + initTime to end - the LARGEST P-window end after the
#   trigger of all variants (60 s), minus every catalog event window: one span for all models.
# Why an analyst pick at a 3-C station was missed (from the --debug logs):
#   P: record_starts_too_late (pick earlier than record start + initTime: the detector was not yet running),
#      no_detector_trigger, trigger_not_turned_into_picker, model_below_minConfidence, peak_vetoed_as_S,
#      window_picked_other_time
#   S: no_P_pick_so_no_S_picker, only_P_pick_is_on_this_S_wave, no_S_window_covering,
#      model_below_minConfidence, window_picked_other_time
#
# Polarity (variants whose model declares polarity labels, here eqtp_ncedc): matched P picks of analyst
# picks with a first motion U/D. The plugin's polarity already refers to ground motion (it swaps up/down
# for a vertical with dip +90 or a negative gain, VerticalPolaritySense); the raw-count polarity is
# reconstructed by undoing that swap, to test which convention the analyst first motions follow.
# Coverage = picks with a DL polarity / matched picks with an analyst first motion, at the plugin default
# polarityMinConfidence (0.5) and at 0.7 (= the subset with polarity_confidence >= 0.7; picks do not depend
# on polarityMinConfidence).
#
# Best model (rule fixed BEFORE any result was seen): among --main-models (binding set 'main'), the highest
# pooled P+S F1 (pooled recall over 3-C stations, pooled precision); ties (< 0.005) -> smaller pooled p95 |dt|.

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
import obspy
import pandas as pd
from obspy.geodetics.base import gps2dist_azimuth

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/sanramon_2015"
sys.path.insert(0, f"{DATA}/tools")
import ray1d  # noqa: E402

TIERS = ["no_data", "no_3c_sensor", "3c_incomplete", "3c_complete"]
DIST_BINS = [(0, 20, "0-20 km"), (20, 40, "20-40 km"), (40, 60, "40-60 km"), (60, 80.5, "60-80 km"),
             (80.5, 1e9, ">80 km")]
MAG_BINS = [(0.5, 1.0, "M0.5-1.0"), (1.0, 1.5, "M1.0-1.5"), (1.5, 2.0, "M1.5-2.0"), (2.0, 2.5, "M2.0-2.5"),
            (2.5, 3.0, "M2.5-3.0"), (3.0, 3.7, "M3.0-3.6")]


def dbin(d):
    for a, b, n in DIST_BINS:
        if a <= d < b:
            return n
    return ">80 km"


def mbin(m):
    for a, b, n in MAG_BINS:
        if a <= m < b:
            return n
    return "other"


def read_scml_picks(path):
    # step T's read_scml_picks, plus location code, polarity and polarity_confidence
    root = ET.parse(path).getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    rows = []
    for p in root.iter(f"{ns}pick"):
        wf = p.find(f"{ns}waveformID")
        comments = {c.findtext(f"{ns}id"): c.findtext(f"{ns}text") for c in p.findall(f"{ns}comment")}
        rows.append(dict(
            pick_id=p.get("publicID"),
            time=pd.Timestamp(p.find(f"{ns}time/{ns}value").text),
            network=wf.get("networkCode"),
            station=wf.get("stationCode"),
            location=wf.get("locationCode") or "",
            channel=wf.get("channelCode"),
            method=p.findtext(f"{ns}methodID"),
            phase=p.findtext(f"{ns}phaseHint"),
            confidence=float(comments.get("SNR", comments.get("confidence", "nan"))),
            polarity=p.findtext(f"{ns}polarity") or "",
            polarity_confidence=float(comments.get("polarity_confidence", "nan")),
            ref_pick_id=comments.get("RefPickID", ""),
        ))
    cols = ["pick_id", "time", "network", "station", "location", "channel", "method", "phase", "confidence",
            "polarity", "polarity_confidence", "ref_pick_id"]
    df = pd.DataFrame(rows, columns=cols)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["nsta"] = df["network"] + "." + df["station"]
    return df


def match(ref, sc, tol):
    # step T's match(), with the station key NET.STA ('nsta')
    pairs = []
    for i, r in ref.iterrows():
        cand = sc[sc["nsta"] == r["nsta"]]
        for j, s in cand.iterrows():
            dt = (s["time"] - r["time"]).total_seconds()
            if abs(dt) <= tol:
                pairs.append((abs(dt), dt, i, j))
    pairs.sort()
    used_r, used_s, out = set(), set(), {}
    for adt, dt, i, j in pairs:
        if i in used_r or j in used_s:
            continue
        used_r.add(i)
        used_s.add(j)
        out[i] = (j, dt)
    return out


def dtstats(dts):
    a = np.asarray(dts, dtype=float)
    if len(a) == 0:
        return dict(n_dt=0, median_abs_dt_s=np.nan, mad_dt_s=np.nan, p95_abs_dt_s=np.nan,
                    mean_dt_s=np.nan, median_dt_s=np.nan, max_abs_dt_s=np.nan)
    return dict(n_dt=int(len(a)), median_abs_dt_s=float(np.median(np.abs(a))),
                mad_dt_s=float(np.median(np.abs(a - np.median(a)))),
                p95_abs_dt_s=float(np.percentile(np.abs(a), 95)), mean_dt_s=float(a.mean()),
                median_dt_s=float(np.median(a)), max_abs_dt_s=float(np.abs(a).max()))


def snr_db(traces, t, sig=(0.0, 1.0), noi=(-3.0, -0.5)):
    num = den = 0.0
    ok = False
    for tns, x in traces:
        s0, s1 = t + sig[0] * 1e9, t + sig[1] * 1e9
        n0, n1 = t + noi[0] * 1e9, t + noi[1] * 1e9
        ms = (tns >= s0) & (tns < s1)
        mn = (tns >= n0) & (tns < n1)
        if ms.sum() < 10 or mn.sum() < 10:
            continue
        num += np.mean(x[ms] ** 2)
        den += np.mean(x[mn] ** 2)
        ok = True
    if not ok or den <= 0 or num <= 0:
        return np.nan
    return float(10 * np.log10(num / den))


def parse_time_txt(path):
    d = {}
    for line in open(path):
        line = line.strip()
        if line.startswith("User time"):
            d["user_s"] = float(line.split(":")[-1])
        elif line.startswith("System time"):
            d["sys_s"] = float(line.split(":")[-1])
        elif line.startswith("Elapsed (wall clock)"):
            v = line.split("):", 1)[1].strip().split(":")
            d["wall_s"] = sum(float(x) * 60 ** i for i, x in enumerate(reversed(v)))
        elif line.startswith("Maximum resident set size"):
            d["maxrss_mb"] = float(line.split(":")[-1]) / 1024
    return d


ATTEMPT_RE = re.compile(r"\[(S?DL3C)/(\S+)\] attempt (\d+)/(\d+): (.*)\(ref=(\S+) offset=([-0-9.]+)s window=([0-9.]+)s\)")
TRIGGER_RE = re.compile(r"\[(\S+)\] trigger on = (\S+),")


def parse_log(path):
    # step 09's parse_log; the station key is NET.STA here
    n_trig = n_pp = n_sp = 0
    rows, trig = [], []
    for line in open(path, errors="replace"):
        if "trigger on =" in line:
            n_trig += 1
            t = TRIGGER_RE.search(line)
            if t:
                p = t.group(1).split(".")
                trig.append(dict(nsta=f"{p[0]}.{p[1]}", time=pd.Timestamp(t.group(2))))
        elif "created picker DL3C" in line:
            n_pp += 1
        elif "created secondary picker SDL3C" in line:
            n_sp += 1
        m = ATTEMPT_RE.search(line)
        if m:
            meth, sta, k, n, body, ref, off, win = m.groups()
            conf = re.search(r"confidence=([0-9.]+)", body)
            bestp = re.search(r"bestP=([0-9.]+)", body)
            pol = re.search(r"polarity=(\w+|-)\(([0-9.]+)\)", body)
            rows.append(dict(method=meth, nsta=sta, attempt=int(k), n_attempts=int(n),
                             accepted_candidate=conf is not None and "no P peak" not in body,
                             confidence=float(conf.group(1)) if conf else np.nan,
                             best_value=float(conf.group(1)) if conf else (float(bestp.group(1)) if bestp else np.nan),
                             polarity_log=pol.group(1) if pol else "", polarity_conf_log=float(pol.group(2)) if pol else np.nan,
                             ref=pd.Timestamp(ref), offset_s=float(off), window_s=float(win)))
    return (n_trig, n_pp, n_sp, pd.DataFrame(rows),
            pd.DataFrame(trig, columns=["nsta", "time"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--variants", nargs="+", required=True)
    ap.add_argument("--main-models", nargs="+", required=True)
    ap.add_argument("--p-tol", type=float, default=0.5)
    ap.add_argument("--s-tol", type=float, default=1.0)
    ap.add_argument("--win-before", type=float, default=5.0)
    ap.add_argument("--win-after", type=float, default=60.0)
    ap.add_argument("--file-half-s", type=float, default=120.0, help="playback files: origin +- this [s]")
    ap.add_argument("--ref-outlier", type=float, default=1.0)
    ap.add_argument("--pred-tol", type=float, default=1.0)
    ap.add_argument("--coinc-window", type=float, default=10.0)
    ap.add_argument("--coinc-min-stations", type=int, default=3)
    ap.add_argument("--init-time", type=float, default=60.0, help="scautopick initTime [s]")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    tol = {"P": a.p_tol, "S": a.s_tol}
    R = a.run_dir

    # ------------------------------------------------------------------ inputs
    ev = pd.read_csv(f"{DATA}/inputs/dl_subset_events.csv", dtype={"event_id": str}).set_index("event_id")
    ev["origin"] = pd.to_datetime(ev["origin_time_utc"], utc=True)
    ev["w0"] = ev["origin"] - pd.Timedelta(seconds=a.win_before)
    ev["w1"] = ev["origin"] + pd.Timedelta(seconds=a.win_after)
    ev["mag_bin"] = ev["pref_mag"].map(mbin)
    cat = pd.read_csv(f"{DATA}/reference_tables/ncss_catalog.csv", dtype={"event_id": str})
    cat["origin"] = pd.to_datetime(cat["origin_time_utc"], utc=True)
    cat["w0"] = cat["origin"] - pd.Timedelta(seconds=a.win_before)
    cat["w1"] = cat["origin"] + pd.Timedelta(seconds=a.win_after)

    picks = pd.read_csv(f"{DATA}/reference_tables/picks_ncss.csv", dtype={"event_id": str, "location": str})
    picks["time"] = pd.to_datetime(picks["time_utc"], utc=True)
    picks["nsta"] = picks["network"] + "." + picks["station"]
    picks["ch_type"] = picks["channel"].str[:2]
    picks["ref_outlier"] = picks["residual_s"].abs() > a.ref_outlier
    n_target_all = int(picks["event_id"].isin(ev.index).sum())
    n_target_unusable = int((picks["event_id"].isin(ev.index) & ~picks["usable"]).sum())
    up = picks[picks["usable"]].copy()                       # weight codes 0-3

    bound = pd.read_csv(f"{R}/config/stations_bound.csv", dtype=str).fillna("")
    bound["nsta"] = bound["network"] + "." + bound["station"]
    bound = bound.set_index("nsta")
    cov = pd.read_csv(f"{R}/config/coverage_bound.csv", dtype={"event_id": str, "location": str})
    cov["nsta"] = cov["network"] + "." + cov["station"]
    covd = {(r.role, r.event_id, r.nsta): r for r in cov.itertuples()}
    bch = pd.read_csv(f"{R}/config/bound_channels.csv", dtype={"location": str})
    bch["nsta"] = bch["network"] + "." + bch["station"]
    zsense = {(r.role, r.nsta): (r.channel, r.dip, r.gain, r.polarity_sense)
              for r in bch[bch["component_role"] == "Z"].itertuples()}

    chans = pd.read_csv(f"{DATA}/reference_tables/station_channels.csv", dtype={"location": str})
    chans["nsta"] = chans["network"] + "." + chans["station"]
    stc = chans.groupby("nsta").agg(lat=("latitude", "first"), lon=("longitude", "first"),
                                    elev_m=("elevation_m", "first"))

    # data present per (event, NET.STA) from the sorted files (header only)
    present = {}
    for e in ev.index:
        st = obspy.read(f"{R}/input/{e}_sorted.mseed", headonly=True)
        present[e] = {f"{tr.stats.network}.{tr.stats.station}" for tr in st}

    # ------------------------------------------------------------------ predicted travel times (ray1d, CON model)
    vm = pd.read_csv(f"{DATA}/inputs/velocity_model.csv")
    pts = vm.iloc[1:]
    # 20 m sub-layers and 2000 ray parameters: within 0.1 ms of the 10 m / 6000-ray setting that matches the
    # NCSS TTGEN table to <= 6 ms (tools/10_validate_nll_grids.py), about 7 times faster
    mp = ray1d.Model1D(pts.top_km.values, pts.vp_km_s.values, z_top=vm.top_km.iloc[0], dz=0.02)
    ms = ray1d.Model1D(pts.top_km.values, pts.vs_km_s.values, z_top=vm.top_km.iloc[0], dz=0.02)
    # target events plus every other NCSS catalog event whose origin lies in a target file (neighbours)
    nb_ids = set()
    for e in ev.index:
        o = ev.loc[e, "origin"]
        m = cat[((cat["origin"] - o).dt.total_seconds().abs() <= a.file_half_s) & (cat["event_id"] != e)]
        nb_ids |= set(m["event_id"])
    nb_ids -= set(ev.index)
    pev = pd.concat([ev[["origin", "latitude", "longitude", "depth_geoid_km"]],
                     cat[cat["event_id"].isin(nb_ids)].set_index("event_id")[["origin", "latitude", "longitude",
                                                                                "depth_geoid_km"]]])
    geo = []
    all_sta = sorted(set().union(*present.values()) | set(up.loc[up["event_id"].isin(ev.index), "nsta"]))
    for e, row in pev.iterrows():
        rows = []
        for s in all_sta:
            if s not in stc.index:
                continue
            d_m, _, _ = gps2dist_azimuth(row["latitude"], row["longitude"], stc.loc[s, "lat"], stc.loc[s, "lon"])
            # receiver depth rounded to 0.1 km (<= 0.05 km error -> < 0.03 s, far below --pred-tol)
            rows.append((s, d_m / 1000.0, round(-stc.loc[s, "elev_m"] / 1000.0, 1)))
        df = pd.DataFrame(rows, columns=["nsta", "dist_km", "zr"])
        tp = np.full(len(df), np.nan)
        ts = np.full(len(df), np.nan)
        for zr, g in df.groupby("zr"):
            tp[g.index] = mp.time(g["dist_km"].values, row["depth_geoid_km"], zr, n_p=2000)
            ts[g.index] = ms.time(g["dist_km"].values, row["depth_geoid_km"], zr, n_p=2000)
        df["event_id"] = e
        df["pred_P"] = row["origin"] + pd.to_timedelta(tp, unit="s")
        df["pred_S"] = row["origin"] + pd.to_timedelta(ts, unit="s")
        geo.append(df)
    geo = pd.concat(geo).set_index(["event_id", "nsta"])

    # nearest other catalog event of each target event (overlapping waveforms in a swarm)
    nbr = {}
    for e in ev.index:
        o = ev.loc[e, "origin"]
        m = cat[(cat["event_id"] != e)].copy()
        m["dt"] = (m["origin"] - o).dt.total_seconds()
        m = m[m["dt"].abs() <= a.file_half_s]
        if len(m):
            x = m.loc[m["dt"].abs().idxmin()]
            nbr[e] = dict(nearest_other_event=x["event_id"], nearest_dt_s=float(x["dt"]), nearest_mag=float(x["pref_mag"]),
                          others_in_file=",".join(f"{r.event_id}({r.dt:+.1f}s,M{r.pref_mag:.2f})" for r in m.itertuples()))
        else:
            nbr[e] = dict(nearest_other_event="", nearest_dt_s=np.nan, nearest_mag=np.nan, others_in_file="")

    def nclass(e):
        dtn = abs(nbr[e]["nearest_dt_s"])
        if not dtn == dtn:
            return "none within 120 s"
        return "nearest <= 15 s" if dtn <= 15 else ("nearest 15-60 s" if dtn <= 60 else "nearest 60-120 s")
    ev["neighbour_class"] = [nclass(e) for e in ev.index]
    pd.DataFrame([dict(event_id=e, mag=ev.loc[e, "pref_mag"], neighbour_class=ev.loc[e, "neighbour_class"], **nbr[e])
                  for e in ev.index]).to_csv(f"{a.out_dir}/event_neighbours.csv", index=False)

    # ------------------------------------------------------------------ reference picks of the 26 target events
    ref = up[up["event_id"].isin(ev.index)].copy().reset_index(drop=True)
    ref = ref.join(geo[["dist_km", "pred_P", "pred_S"]], on=["event_id", "nsta"])
    ref["res_pred_s"] = np.where(ref["phase"] == "P", (ref["time"] - ref["pred_P"]).dt.total_seconds(),
                                 (ref["time"] - ref["pred_S"]).dt.total_seconds())
    ref["dist_bin"] = ref["dist_km"].map(dbin)
    ref["mag"] = ref["event_id"].map(ev["pref_mag"])
    ref["mag_bin"] = ref["event_id"].map(ev["mag_bin"])
    ref["has_data"] = [s in present[e] for e, s in zip(ref["event_id"], ref["nsta"])]
    ref["main_sensor"] = ref["nsta"].map(lambda s: bound.loc[s, "main_sensor"] if s in bound.index else "")
    ref["hn_sensor"] = ref["nsta"].map(lambda s: bound.loc[s, "hn_sensor"] if s in bound.index else "")
    tier, rstart = [], []
    for r in ref.itertuples():
        c = covd.get(("main", r.event_id, r.nsta))
        if not r.has_data:
            tier.append("no_data")
            rstart.append(np.nan)
        elif not r.main_sensor or c is None:
            tier.append("no_3c_sensor")
            rstart.append(np.nan)
        else:
            tier.append("3c_complete" if c.complete else "3c_incomplete")
            rstart.append(c.start_rel_origin_s)
    ref["tier"] = tier
    ref["record_start_rel_origin_s"] = rstart
    ref["t_rel_origin_s"] = (ref["time"] - ref["event_id"].map(ev["origin"])).dt.total_seconds()
    ref["is_3c"] = ref["tier"].isin(["3c_incomplete", "3c_complete"])
    pred_check = {}
    for ph in ("P", "S"):
        x = ref.loc[(ref["phase"] == ph) & ~ref["ref_outlier"] & ref["res_pred_s"].notna(), "res_pred_s"]
        pred_check[ph] = dict(n=int(len(x)), median_s=float(x.median()), p01_s=float(x.quantile(0.01)),
                              p99_s=float(x.quantile(0.99)), frac_within_pred_tol=float((x.abs() <= a.pred_tol).mean()))

    # ------------------------------------------------------------------ waveforms of the bound sensors (SNR, hours)
    wf = {}
    for e in ev.index:
        st = obspy.read(f"{R}/input/{e}_sorted.mseed")
        st.merge(method=0, fill_value=None)
        st = st.split()
        for tr in st:
            s = f"{tr.stats.network}.{tr.stats.station}"
            c = covd.get(("main", e, s))
            if c is None or tr.stats.location != (c.location if isinstance(c.location, str) else "") \
                    or tr.stats.channel[:2] != c.sensor:
                continue
            if tr.stats.npts < 50:
                continue
            x = tr.data.astype(float)
            x -= x.mean()
            trf = tr.copy()
            trf.data = x
            trf.filter("bandpass", freqmin=2.0, freqmax=20.0, corners=4, zerophase=False)
            tns = tr.stats.starttime.ns + (np.arange(tr.stats.npts) * (1e9 / tr.stats.sampling_rate)).astype(np.int64)
            key = (e, s)
            wf.setdefault(key, {"Z": [], "H": []})
            wf[key]["Z" if tr.stats.channel == c.z else "H"].append((tns, trf.data))

    def pick_snr(e, s, phase, t):
        w = wf.get((e, s))
        if w is None:
            return np.nan
        return snr_db(w["Z"] if phase == "P" else w["H"], t.value)

    ref["snr_db_bound_sensor"] = [pick_snr(r.event_id, r.nsta, r.phase, r.time) if r.is_3c else np.nan
                                  for r in ref.itertuples()]

    # ------------------------------------------------------------------ DL picks and matching
    settings = {}
    for v in a.variants:
        settings[v] = json.load(open(f"{R}/settings/scautopick_{v}.settings.json"))
    all_dl, all_rv, logs, costs, trigs = [], [], [], [], []
    for v in a.variants:
        role = settings[v].get("binding_set", "main")
        for e in ev.index:
            out = f"{R}/output/{v}/{e}"
            dl = read_scml_picks(f"{out}/picks.xml")
            dl["variant"], dl["event_id"], dl["role"] = v, e, role
            o = ev.loc[e, "origin"]
            dl["t_rel_origin_s"] = (dl["time"] - o).dt.total_seconds()
            dl["in_window"] = (dl["time"] >= ev.loc[e, "w0"]) & (dl["time"] <= ev.loc[e, "w1"])
            oth = []
            for t in dl["time"]:
                m = cat[(cat["event_id"] != e) & (cat["w0"] <= t) & (cat["w1"] >= t)]
                oth.append(",".join(m["event_id"]) if len(m) else "")
            dl["other_event_window"] = oth
            dl["sensor"] = dl["nsta"].map(lambda s: bound.loc[s, f"{role}_sensor"] if s in bound.index else "")
            g = geo.loc[e]
            dl["dist_km"] = dl["nsta"].map(g["dist_km"])
            dl["res_pred_P_s"] = (dl["time"] - dl["nsta"].map(g["pred_P"])).dt.total_seconds()
            dl["res_pred_S_s"] = (dl["time"] - dl["nsta"].map(g["pred_S"])).dt.total_seconds()
            dl["matched"] = False
            dl["matched_event_id"] = ""
            dl["ref_dt_s"] = np.nan
            f0, f1 = o - pd.Timedelta(seconds=a.file_half_s), o + pd.Timedelta(seconds=a.file_half_s)
            cand = up[(up["time"] >= f0) & (up["time"] <= f1)].copy()
            cand["matched"] = False
            cand["dt_s"] = np.nan
            for c_ in ("dl_confidence", "dl_polarity_confidence"):
                cand[c_] = np.nan
            for c_ in ("dl_pick_id", "dl_polarity", "dl_channel"):
                cand[c_] = ""
            for ph in ("P", "S"):
                m = match(cand[cand["phase"] == ph], dl[dl["phase"] == ph], tol[ph])
                for i, (j, dt) in m.items():
                    cand.loc[i, ["matched", "dt_s", "dl_confidence", "dl_pick_id", "dl_polarity",
                                 "dl_polarity_confidence", "dl_channel"]] = [
                        True, dt, dl.loc[j, "confidence"], dl.loc[j, "pick_id"], dl.loc[j, "polarity"],
                        dl.loc[j, "polarity_confidence"], dl.loc[j, "channel"]]
                    dl.loc[j, ["matched", "matched_event_id", "ref_dt_s"]] = [True, cand.loc[i, "event_id"], dt]
            tgt = cand[cand["event_id"] == e].set_index(["phase", "nsta"])
            rv = ref[ref["event_id"] == e].copy()
            rv["variant"] = v
            for c_ in ("matched", "dt_s", "dl_confidence", "dl_pick_id", "dl_polarity", "dl_polarity_confidence",
                       "dl_channel"):
                rv[c_] = [tgt.loc[(p_, s_), c_] for p_, s_ in zip(rv["phase"], rv["nsta"])]
            rv["matched"] = rv["matched"].astype(bool)
            all_dl.append(dl)
            all_rv.append(rv)
            n_trig, n_pp, n_sp, att, trg = parse_log(f"{out}/scautopick.log")
            att["variant"], att["event_id"] = v, e
            trg["variant"], trg["event_id"] = v, e
            logs.append(att)
            trigs.append(trg)
            tt = parse_time_txt(f"{out}/time.txt")
            costs.append(dict(variant=v, event_id=e, triggers=n_trig, p_pickers=n_pp, s_pickers=n_sp,
                              p_windows=int((att["method"] == "DL3C").sum()) if len(att) else 0,
                              s_windows=int((att["method"] == "SDL3C").sum()) if len(att) else 0,
                              n_picks=len(dl), **tt))
        tt = parse_time_txt(f"{R}/output/{v}/startup_probe/time.txt")
        costs.append(dict(variant=v, event_id="startup_probe", **tt))
    dl = pd.concat(all_dl, ignore_index=True)
    rv = pd.concat(all_rv, ignore_index=True)
    att = pd.concat(logs, ignore_index=True)
    trg = pd.concat(trigs, ignore_index=True)
    cost = pd.DataFrame(costs)

    # ------------------------------------------------------------------ classification of unmatched DL picks
    refkey = {(r.event_id, r.nsta, r.phase): r for r in ref.itertuples()}
    file_nb = {e: [n_ for n_ in nb_ids
                   if abs((cat.loc[cat["event_id"] == n_, "origin"].iloc[0] - ev.loc[e, "origin"]).total_seconds())
                   <= a.file_half_s] for e in ev.index}
    cls = []
    for x in dl.itertuples():
        if x.matched:
            cls.append("matched" if x.matched_event_id == x.event_id else "matched_other_event")
            continue
        if not x.in_window:
            cls.append("")
            continue
        same = dl[(dl["variant"] == x.variant) & (dl["event_id"] == x.event_id) & (dl["nsta"] == x.nsta)
                  & (dl["phase"] == x.phase) & (dl.index != x.Index)]
        close = same[(same["time"] - x.time).abs() <= pd.Timedelta(seconds=tol[x.phase])]
        if any(y.matched or (y.confidence > x.confidence) or (y.confidence == x.confidence and y.time < x.time)
               for y in close.itertuples()):
            cls.append("near_duplicate")
            continue
        other = "S" if x.phase == "P" else "P"
        rp_other = refkey.get((x.event_id, x.nsta, other))
        rp_same = refkey.get((x.event_id, x.nsta, x.phase))
        res_same = x.res_pred_P_s if x.phase == "P" else x.res_pred_S_s
        res_other = x.res_pred_S_s if x.phase == "P" else x.res_pred_P_s
        near_same = abs(res_same) <= a.pred_tol if pd.notna(res_same) else False
        if rp_other is not None:
            conf_ph = abs((x.time - rp_other.time).total_seconds()) <= tol[x.phase]
        else:
            conf_ph = (abs(res_other) <= a.pred_tol if pd.notna(res_other) else False) and not near_same
        if conf_ph:
            cls.append("phase_confusion")
        elif rp_same is not None and rp_same.ref_outlier and near_same:
            cls.append("reference_outlier")
        elif rp_same is None and near_same:
            cls.append("plausible_no_analyst_pick")
        elif rp_same is not None and near_same:
            cls.append("timing_disagreement")
        elif any(abs((x.time - geo.loc[(n_, x.nsta), f"pred_{ph_}"]).total_seconds()) <= a.pred_tol
                 for n_ in file_nb[x.event_id] if (n_, x.nsta) in geo.index for ph_ in ("P", "S")):
            cls.append("plausible_other_event_arrival")
        else:
            cls.append("noise_or_other")
    dl["class"] = cls
    out_mask = ~dl["in_window"] & ~dl["matched"]
    dl.loc[~dl["in_window"] & dl["matched"], "class"] = "outside_matched_catalog_pick"
    dl.loc[out_mask & (dl["other_event_window"] != ""), "class"] = "other_catalog_event"
    for (v, e), g in dl[out_mask & (dl["other_event_window"] == "")].groupby(["variant", "event_id"]):
        for ph in ("P", "S"):
            gp = g[g["phase"] == ph]
            for x in gp.itertuples():
                if ph == "S":
                    own_p = dl[(dl["variant"] == v) & (dl["event_id"] == e) & (dl["pick_id"] == x.ref_pick_id)]
                    if len(own_p) == 1 and own_p.iloc[0]["class"] in ("coincident", "isolated"):
                        dl.loc[x.Index, "class"] = own_p.iloc[0]["class"]
                        continue
                allp = dl[(dl["variant"] == v) & (dl["event_id"] == e) & (dl["phase"] == "P")]
                near = allp[(allp["time"] - x.time).abs() <= pd.Timedelta(seconds=a.coinc_window)]
                dl.loc[x.Index, "class"] = ("coincident" if near["nsta"].nunique() >= a.coinc_min_stations
                                            else "isolated")

    # ------------------------------------------------------------------ why analyst picks at 3-C stations were missed
    minconf = {v: (float(settings[v]["plugin_resolved"]["picker.DL3C"]["minConfidence"]["value"]),
                   float(settings[v]["plugin_resolved"]["spicker.SDL3C"]["minConfidence"]["value"]))
               for v in a.variants}
    p_end = {v: settings[v]["plugin_resolved"]["picker.DL3C"]["resolved"]["maxLatency_s"] for v in a.variants}
    att["w_start"] = att["ref"] + pd.to_timedelta(att["offset_s"], unit="s")
    att["w_end"] = att["w_start"] + pd.to_timedelta(att["window_s"], unit="s")
    miss = rv[~rv["matched"] & rv["is_3c"] & ~rv["variant"].str.endswith("_hn")].copy()
    why, best_val = [], []
    for x in miss.itertuples():
        A = att[(att["variant"] == x.variant) & (att["event_id"] == x.event_id) & (att["nsta"] == x.nsta)]
        if x.phase == "P":
            W = A[(A["method"] == "DL3C") & (A["w_start"] <= x.time) & (A["w_end"] >= x.time)]
            if len(W) == 0:
                if pd.notna(x.record_start_rel_origin_s) and x.t_rel_origin_s < x.record_start_rel_origin_s + a.init_time:
                    why.append("record_starts_too_late")
                else:
                    T = trg[(trg["variant"] == x.variant) & (trg["event_id"] == x.event_id) & (trg["nsta"] == x.nsta)
                            & ((trg["time"] - x.time).abs() <= pd.Timedelta(seconds=5))]
                    why.append("trigger_not_turned_into_picker" if len(T) else "no_detector_trigger")
                best_val.append(np.nan)
                continue
            bv = W["best_value"].max()
            best_val.append(bv)
            if W["accepted_candidate"].any():
                why.append("window_picked_other_time")
            elif bv >= minconf[x.variant][0]:
                why.append("peak_vetoed_as_S")
            else:
                why.append("model_below_minConfidence")
        else:
            pp = dl[(dl["variant"] == x.variant) & (dl["event_id"] == x.event_id) & (dl["nsta"] == x.nsta)
                    & (dl["phase"] == "P") & (dl["time"] < x.time)]
            if len(pp) == 0:
                why.append("no_P_pick_so_no_S_picker")
                best_val.append(np.nan)
                continue
            if ((pp["time"] - x.time).abs() <= pd.Timedelta(seconds=a.p_tol)).all():
                why.append("only_P_pick_is_on_this_S_wave")
                best_val.append(np.nan)
                continue
            W = A[(A["method"] == "SDL3C") & (A["w_start"] <= x.time) & (A["w_end"] >= x.time) & (A["ref"] < x.time)]
            if len(W) == 0:
                why.append("no_S_window_covering")
                best_val.append(np.nan)
                continue
            bv = W["best_value"].max()
            best_val.append(bv)
            why.append("window_picked_other_time" if bv >= minconf[x.variant][1] else "model_below_minConfidence")
    miss["why_missed"] = why
    miss["best_value_in_covering_windows"] = best_val
    miss[["variant", "event_id", "nsta", "channel", "main_sensor", "tier", "phase", "time", "weight_code",
          "dist_km", "mag", "ref_outlier", "snr_db_bound_sensor", "record_start_rel_origin_s", "why_missed",
          "best_value_in_covering_windows"]].to_csv(f"{a.out_dir}/missed_reference_diagnosis.csv", index=False,
                                                   float_format="%.3f")
    miss_counts = miss.groupby(["variant", "phase", "why_missed"]).size().unstack(fill_value=0)

    # ------------------------------------------------------------------ tables
    win = dl[dl["in_window"]]
    rows = []

    def metr(rr, ww):
        d = {}
        for name, sel in (("all", rr), ("with_data", rr[rr["tier"] != "no_data"]), ("3c", rr[rr["is_3c"]]),
                          ("3c_complete", rr[rr["tier"] == "3c_complete"])):
            d[f"n_ref_{name}"] = len(sel)
            d[f"n_matched_{name}"] = int(sel["matched"].sum())
            d[f"recall_{name}"] = sel["matched"].mean() if len(sel) else np.nan
        d["n_dl_in_window"] = len(ww)
        d["n_dl_matched_any_event"] = int(ww["matched"].sum())
        d["n_dl_matched_other_event"] = int((ww["class"] == "matched_other_event").sum())
        d["precision"] = d["n_dl_matched_any_event"] / len(ww) if len(ww) else np.nan
        n_pl = int(ww["class"].isin(["plausible_no_analyst_pick", "reference_outlier",
                                     "plausible_other_event_arrival"]).sum())
        d["n_dl_plausible_unmatched"] = n_pl
        d["precision_counting_plausible"] = (d["n_dl_matched_any_event"] + n_pl) / len(ww) if len(ww) else np.nan
        r_, p_ = d["recall_3c"], d["precision"]
        d["f1"] = 2 * r_ * p_ / (r_ + p_) if (pd.notna(r_) and pd.notna(p_) and r_ + p_ > 0) else np.nan
        d.update(dtstats(rr.loc[rr["matched"], "dt_s"]))
        return d

    def add(group, value, v, ph, rr, ww):
        d = dict(variant=v, phase=ph, group=group, value=value)
        d.update(metr(rr, ww))
        rows.append(d)

    for v in a.variants:
        for ph in ("P", "S", "P+S"):
            phs = ["P", "S"] if ph == "P+S" else [ph]
            rr = rv[(rv["variant"] == v) & rv["phase"].isin(phs)]
            ww = win[(win["variant"] == v) & win["phase"].isin(phs)]
            add("all", "all", v, ph, rr, ww)
            for t in TIERS:
                add("tier", t, v, ph, rr[rr["tier"] == t], ww.iloc[0:0])
            for s in sorted(rr["ch_type"].unique()):
                add("analyst_channel", s, v, ph, rr[rr["ch_type"] == s], ww.iloc[0:0])
            for s in sorted(set(rr["main_sensor"].unique()) | set(ww["sensor"].unique())):
                sel = rr[rr["main_sensor"] == s] if not v.endswith("_hn") else rr[rr["hn_sensor"] == s]
                add("bound_sensor", s or "(none)", v, ph, sel, ww[ww["sensor"] == s])
            for b in [n for _, _, n in DIST_BINS]:
                add("distance", b, v, ph, rr[rr["dist_bin"] == b], ww[ww["dist_km"].map(dbin) == b])
            for b in [n for _, _, n in MAG_BINS]:
                kk = ev.index[ev["mag_bin"] == b]
                add("magnitude", b, v, ph, rr[rr["event_id"].isin(kk)], ww[ww["event_id"].isin(kk)])
            for wc in (0, 1, 2, 3):
                add("weight_code", str(wc), v, ph, rr[rr["weight_code"] == wc], ww.iloc[0:0])
            for nc in ("none within 120 s", "nearest 60-120 s", "nearest 15-60 s", "nearest <= 15 s"):
                kk = ev.index[ev["neighbour_class"] == nc]
                add("neighbour", nc, v, ph, rr[rr["event_id"].isin(kk)], ww[ww["event_id"].isin(kk)])
            for e in ev.index:
                add("event", f"{e} M{ev.loc[e, 'pref_mag']:.2f}", v, ph, rr[rr["event_id"] == e],
                    ww[ww["event_id"] == e])
    tab = pd.DataFrame(rows)
    tab[tab["group"] == "all"].to_csv(f"{a.out_dir}/summary_by_model.csv", index=False, float_format="%.4f")
    for gname in ("tier", "analyst_channel", "bound_sensor", "distance", "magnitude", "weight_code", "neighbour",
                  "event"):
        tab[tab["group"] == gname].to_csv(f"{a.out_dir}/by_{gname}.csv", index=False, float_format="%.4f")

    # accelerometer vs velocity sensor at the same stations (binding sets main vs hn)
    hn_st = set(bound.index[bound["hn_sensor"] != ""])
    hrows = []
    for m in a.main_models:
        if f"{m}_hn" not in a.variants:
            continue
        for v in (m, f"{m}_hn"):
            for ph in ("P", "S"):
                rr = rv[(rv["variant"] == v) & (rv["phase"] == ph) & rv["nsta"].isin(hn_st) & rv["has_data"]]
                ww = win[(win["variant"] == v) & (win["phase"] == ph) & win["nsta"].isin(hn_st)]
                d = dict(model=m, binding_set="hn (accelerometer)" if v.endswith("_hn") else "main (velocity sensor)",
                         variant=v, phase=ph)
                d.update(metr(rr, ww))
                hrows.append(d)
    pd.DataFrame(hrows).to_csv(f"{a.out_dir}/accelerometer_vs_velocity.csv", index=False, float_format="%.4f")

    # ------------------------------------------------------------------ searchable hours and outside-window picks
    # One span for ALL models, so the rates are comparable: from record start + initTime (the detector starts)
    # to record end - the largest P-window end after the trigger of all variants (60 s for eqtp_ncedc), minus
    # the union of all catalog event windows. Only picks whose time lies in that span of their own station
    # record are counted (for the 240 s files this is the pre-event noise from origin -60 s to -5 s).
    common_end = max(p_end.values())
    spans, hrow = {}, []
    for v in a.variants:
        role = settings[v].get("binding_set", "main")
        for c in cov[cov["role"] == role].itertuples():
            o = ev.loc[c.event_id, "origin"]
            s0 = o + pd.Timedelta(seconds=c.start_rel_origin_s + a.init_time)
            s1 = o + pd.Timedelta(seconds=c.end_rel_origin_s - common_end)
            ivs = []
            if s1 > s0:
                ov = cat[(cat["w1"] > s0) & (cat["w0"] < s1)].sort_values("w0")
                cur = s0
                for r in ov.itertuples():
                    if r.w0 > cur:
                        ivs.append((cur, min(r.w0, s1)))
                    cur = max(cur, r.w1)
                if cur < s1:
                    ivs.append((cur, s1))
            spans[(v, c.event_id, c.nsta)] = ivs
            eff = sum((b - a_).total_seconds() for a_, b in ivs)
            hrow.append(dict(variant=v, event_id=c.event_id, nsta=c.nsta, sensor=c.sensor, complete=c.complete,
                             span_h=(c.end_rel_origin_s - c.start_rel_origin_s) / 3600.0,
                             searchable_outside_windows_h=eff / 3600.0))
    hrs = pd.DataFrame(hrow)
    hrs.to_csv(f"{a.out_dir}/station_hours.csv", index=False, float_format="%.5f")
    dl["in_searchable_span"] = [any(a_ <= t <= b for a_, b in spans.get((v, e, n), []))
                                for v, e, n, t in zip(dl["variant"], dl["event_id"], dl["nsta"], dl["time"])]
    owrows = []
    outside = dl[~dl["in_window"]]
    for v in a.variants:
        hv = hrs[hrs["variant"] == v]
        H_raw, H_eff = hv["span_h"].sum(), hv["searchable_outside_windows_h"].sum()
        for ph in ("P", "S"):
            o = outside[(outside["variant"] == v) & (outside["phase"] == ph)]
            fs = o[o["class"].isin(["coincident", "isolated"]) & o["in_searchable_span"]]
            d = dict(variant=v, phase=ph, n_outside=len(o),
                     n_outside_matched_catalog_pick=int((o["class"] == "outside_matched_catalog_pick").sum()),
                     n_other_catalog_event=int((o["class"] == "other_catalog_event").sum()),
                     n_coincident=int((o["class"] == "coincident").sum()),
                     n_isolated=int((o["class"] == "isolated").sum()),
                     n_false_in_searchable_span=len(fs),
                     n_coincident_in_span=int((fs["class"] == "coincident").sum()),
                     n_isolated_in_span=int((fs["class"] == "isolated").sum()),
                     station_hours_raw=H_raw, station_hours_searchable=H_eff,
                     false_per_station_hour_searchable=len(fs) / H_eff if H_eff else np.nan,
                     isolated_per_station_hour_searchable=int((fs["class"] == "isolated").sum()) / H_eff if H_eff else np.nan,
                     median_confidence_false=float(fs["confidence"].median()) if len(fs) else np.nan)
            for sname in sorted(hv["sensor"].unique()):
                hs = hv[hv["sensor"] == sname]["searchable_outside_windows_h"].sum()
                d[f"false_per_station_hour_{sname}"] = int((fs["sensor"] == sname).sum()) / hs if hs else np.nan
                d[f"searchable_h_{sname}"] = hs
            owrows.append(d)
    ow = pd.DataFrame(owrows)
    ow.to_csv(f"{a.out_dir}/outside_window.csv", index=False, float_format="%.4f")

    um = win[~win["matched"]].copy()
    um[["variant", "event_id", "nsta", "channel", "sensor", "phase", "time", "t_rel_origin_s", "confidence", "class",
        "dist_km", "res_pred_P_s", "res_pred_S_s", "pick_id"]].sort_values(["event_id", "variant", "nsta", "phase"]).to_csv(
        f"{a.out_dir}/unmatched_in_window.csv", index=False, float_format="%.3f")
    um_counts = um.groupby(["variant", "phase", "class"]).size().unstack(fill_value=0)

    # ------------------------------------------------------------------ cost
    cr = []
    for v in a.variants:
        c = cost[(cost["variant"] == v) & (cost["event_id"] != "startup_probe")]
        probe = cost[(cost["variant"] == v) & (cost["event_id"] == "startup_probe")].iloc[0]
        cpu = (c["user_s"] + c["sys_s"]).sum()
        H = hrs[hrs["variant"] == v]["span_h"].sum()
        cpu_probe = probe["user_s"] + probe["sys_s"]
        nw = c["p_windows"].sum() + c["s_windows"].sum()
        cr.append(dict(variant=v, runs=len(c), station_hours=H, cpu_s_total=cpu, wall_s_total=c["wall_s"].sum(),
                       cpu_s_per_station_hour=cpu / H, startup_probe_cpu_s=cpu_probe,
                       cpu_s_per_station_hour_minus_startup=(cpu - len(c) * cpu_probe) / H,
                       triggers=int(c["triggers"].sum()), triggers_per_station_hour=c["triggers"].sum() / H,
                       p_windows=int(c["p_windows"].sum()), s_windows=int(c["s_windows"].sum()),
                       windows_per_station_hour=nw / H,
                       cpu_ms_per_window=1000 * (cpu - len(c) * cpu_probe) / nw if nw else np.nan,
                       max_rss_mb=c["maxrss_mb"].max()))
    costt = pd.DataFrame(cr)
    costt.to_csv(f"{a.out_dir}/cost.csv", index=False, float_format="%.4f")
    cost.to_csv(f"{a.out_dir}/cost_per_run.csv", index=False, float_format="%.4f")
    lc = att.groupby(["variant", "method", "offset_s", "window_s"]).size().rename("n_attempts").reset_index()
    lc.to_csv(f"{a.out_dir}/log_checks.csv", index=False)

    # ------------------------------------------------------------------ polarity (models with polarity labels)
    pol_rows, pol_sum = [], {}
    for v in a.variants:
        meta = settings[v]["model_metadata"]
        if not meta.get("seiscomp.picker.polarityLabels"):
            continue
        role = settings[v].get("binding_set", "main")
        q = rv[(rv["variant"] == v) & (rv["phase"] == "P") & rv["matched"]].copy()
        q["analyst_fm"] = q["first_motion"].fillna("")
        q = q[q["analyst_fm"].isin(["U", "D"])]
        q["dl_fm"] = q["dl_polarity"].map({"positive": "U", "negative": "D"}).fillna("")
        sense = q["nsta"].map(lambda s: zsense.get((role, s), ("", np.nan, np.nan, ""))[3])
        q["dl_channel_sense"] = sense
        q["dl_vertical"] = q["nsta"].map(lambda s: zsense.get((role, s), ("",))[0])
        flip = {"U": "D", "D": "U", "": ""}
        q["dl_fm_raw_counts"] = [flip[f] if s == "Inverted" else f for f, s in zip(q["dl_fm"], q["dl_channel_sense"])]
        q["same_channel_as_analyst"] = q["dl_vertical"] == q["channel"]
        q["agree"] = np.where(q["dl_fm"] != "", q["dl_fm"] == q["analyst_fm"], np.nan)
        q["agree_raw_counts"] = np.where(q["dl_fm"] != "", q["dl_fm_raw_counts"] == q["analyst_fm"], np.nan)
        pol_rows.append(q)

        def ps(sel, thr):
            has = sel[(sel["dl_fm"] != "") & (sel["dl_polarity_confidence"] >= thr)]
            return dict(n_matched_with_analyst_fm=len(sel), n_with_dl_polarity=len(has),
                        coverage=len(has) / len(sel) if len(sel) else np.nan,
                        n_agree=int((has["dl_fm"] == has["analyst_fm"]).sum()),
                        agreement=float((has["dl_fm"] == has["analyst_fm"]).mean()) if len(has) else np.nan,
                        agreement_raw_counts=float((has["dl_fm_raw_counts"] == has["analyst_fm"]).mean()) if len(has) else np.nan)
        d = {}
        for thr in (0.5, 0.7):
            d[f"thr_{thr}"] = dict(
                all=ps(q, thr),
                onset_I=ps(q[q["onset"] == "I"], thr), onset_E=ps(q[q["onset"] == "E"], thr),
                **{f"weight_{w}": ps(q[q["weight_code"] == w], thr) for w in (0, 1, 2, 3)},
                same_channel=ps(q[q["same_channel_as_analyst"]], thr),
                other_channel=ps(q[~q["same_channel_as_analyst"]], thr),
                direct_sense=ps(q[q["dl_channel_sense"] == "Direct"], thr),
                inverted_sense=ps(q[q["dl_channel_sense"] == "Inverted"], thr),
                **{f"dist_{b}": ps(q[q["dist_bin"] == b], thr) for _, _, b in DIST_BINS[:4]},
                **{f"mag_{b}": ps(q[q["mag_bin"] == b], thr) for _, _, b in MAG_BINS},
                **{f"bound_{s}": ps(q[q["main_sensor" if role == "main" else "hn_sensor"] == s], thr)
                   for s in sorted(q["main_sensor" if role == "main" else "hn_sensor"].unique())})
        # all analyst first motions (not only matched picks): how many get a DL polarity at all
        allfm = rv[(rv["variant"] == v) & (rv["phase"] == "P") & rv["first_motion"].isin(["U", "D"])]
        d["analyst_fm_total"] = int(len(allfm))
        d["analyst_fm_at_3c"] = int(allfm["is_3c"].sum())
        d["analyst_fm_matched"] = int(allfm["matched"].sum())
        # per-station consistency (systematic disagreement = possible reversal in data/metadata or analyst)
        has = q[q["dl_fm"] != ""]
        st = has.groupby("nsta").agg(n=("agree", "size"), agree=("agree", "mean"), sense=("dl_channel_sense", "first"),
                                     dl_vertical=("dl_vertical", "first"),
                                     analyst_channels=("channel", lambda x: ",".join(sorted(set(x)))))
        d["stations_ge3_disagree_ge80pct"] = st[(st["n"] >= 3) & (st["agree"] <= 0.2)].reset_index().to_dict("records")
        d["n_stations_ge3"] = int((st["n"] >= 3).sum())
        pol_sum[v] = d
        st.reset_index().to_csv(f"{a.out_dir}/polarity_by_station_{v}.csv", index=False, float_format="%.3f")
    if pol_rows:
        pd.concat(pol_rows).to_csv(f"{a.out_dir}/polarity_pairs.csv", index=False, float_format="%.4f")

    # ------------------------------------------------------------------ best model
    allp = tab[(tab["group"] == "all") & (tab["phase"] == "P+S") & tab["variant"].isin(a.main_models)]
    allp = allp.sort_values(["f1", "p95_abs_dt_s"], ascending=[False, True]).reset_index(drop=True)
    best = allp.iloc[0]
    if len(allp) > 1 and abs(allp.iloc[0]["f1"] - allp.iloc[1]["f1"]) < 0.005:
        best = allp[(allp.iloc[0]["f1"] - allp["f1"]) < 0.005].sort_values("p95_abs_dt_s").iloc[0]
    bj = dict(rule="highest pooled P+S F1 (recall over 3-C stations, precision vs any catalog pick) among the "
                   "main-set models; ties (<0.005) -> smaller pooled p95 |dt|",
              best_model=best["variant"], cfg_file=f"{R}/config/scautopick_{best['variant']}.cfg",
              bindings_config=f"{R}/config/bindings_main.xml",
              ranking=allp[["variant", "f1", "recall_3c", "precision", "p95_abs_dt_s", "median_abs_dt_s"]].to_dict("records"))
    json.dump(bj, open(f"{a.out_dir}/best_model.json", "w"), indent=1, default=str)

    # ------------------------------------------------------------------ save + summary
    dl.to_csv(f"{a.out_dir}/dl_picks_all.csv", index=False, float_format="%.4f")
    rv.to_csv(f"{a.out_dir}/reference_vs_dl.csv", index=False, float_format="%.4f")
    ref.to_csv(f"{a.out_dir}/reference_picks.csv", index=False, float_format="%.4f")
    tiers = ref.groupby(["phase", "tier"]).size().unstack(fill_value=0)
    summary = dict(
        definitions=dict(p_tol_s=a.p_tol, s_tol_s=a.s_tol,
                         event_window=f"NCSS origin -{a.win_before} s .. +{a.win_after} s",
                         ref_outlier_s=a.ref_outlier, pred_tol_s=a.pred_tol,
                         coincidence=f">= {a.coinc_min_stations} stations within +-{a.coinc_window} s",
                         init_time_s=a.init_time, mad="median(|dt - median(dt)|)",
                         snr="20log10 RMS[t,t+1s]/RMS[t-3s,t-0.5s], one-pass 2-20 Hz BP 4 corners, bound sensor",
                         predicted_times="ray1d CON model, Vs=Vp/1.73, NCSS origin/hypocentre"),
        n_reference=dict(target_events_all_picks=n_target_all, out_weighted_left_out=n_target_unusable,
                         usable=int(len(ref)), P=int((ref["phase"] == "P").sum()), S=int((ref["phase"] == "S").sum()),
                         outliers=int(ref["ref_outlier"].sum()), tiers=tiers.to_dict(),
                         P_by_analyst_channel=ref[ref.phase == "P"]["ch_type"].value_counts().to_dict(),
                         S_by_analyst_channel=ref[ref.phase == "S"]["ch_type"].value_counts().to_dict()),
        pred_check=pred_check,
        summary_by_model=tab[(tab["group"] == "all")].to_dict("records"),
        outside_window=ow.to_dict("records"),
        unmatched_in_window_counts={f"{k[0]}|{k[1]}": v_.to_dict() for k, v_ in um_counts.iterrows()},
        missed_reference_counts={f"{k[0]}|{k[1]}": v_.to_dict() for k, v_ in miss_counts.iterrows()},
        cost=costt.to_dict("records"), polarity=pol_sum, best_model=bj, log_offsets=lc.to_dict("records"))
    json.dump(summary, open(f"{a.out_dir}/summary.json", "w"), indent=1, default=str)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print("reference:", json.dumps(summary["n_reference"], default=str))
    print("prediction check:", json.dumps(pred_check))
    show = ["variant", "phase", "n_ref_all", "recall_all", "recall_with_data", "n_ref_3c", "recall_3c",
            "recall_3c_complete", "n_dl_in_window", "precision", "precision_counting_plausible", "f1",
            "median_abs_dt_s", "mad_dt_s", "p95_abs_dt_s", "mean_dt_s"]
    print(tab[tab["group"] == "all"][show].round(3).to_string(index=False))
    print("\noutside the event windows:")
    print(ow[["variant", "phase", "n_outside", "n_other_catalog_event", "n_coincident", "n_isolated",
              "station_hours_searchable", "false_per_station_hour_searchable"]].round(3).to_string(index=False))
    print("\nunmatched picks inside the windows, by class:")
    print(um_counts.to_string())
    print("\nmissed analyst picks at 3-C stations, why:")
    print(miss_counts.to_string())
    print("\ncost:")
    print(costt[["variant", "station_hours", "cpu_s_total", "cpu_s_per_station_hour", "startup_probe_cpu_s",
                 "triggers", "p_windows", "s_windows", "cpu_ms_per_window", "max_rss_mb"]].round(4).to_string(index=False))
    for v, d in pol_sum.items():
        print(f"\npolarity {v}: thr 0.5 {d['thr_0.5']['all']}; thr 0.7 {d['thr_0.7']['all']}")
    print("\nbest model:", bj["best_model"], [(r["variant"], round(r["f1"], 4)) for r in bj["ranking"]])


if __name__ == "__main__":
    main()
