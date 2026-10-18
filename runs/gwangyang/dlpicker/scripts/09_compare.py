# 09_compare.py -- step 09 helper (run in conda env 'pyrtdd': obspy, pandas, pyrtdd).
#
# Compares the picks of scautopick + scdlrtpicker (one SCML file per variant and event, written by
# 09_dlpicker.sh stage pick) with the PhaseNet+ reference picks (reference_tables/picks_phasenet_plus.csv).
# PhaseNet+ is itself an automatic picker: "agreement" here is agreement with PhaseNet+, not truth.
#
# Matching rule (from step T's install/05_compare_picks.py; functions read_scml_picks and match are
# copied from there unchanged): same event run, same station, same phase; P within --p-tol, S within
# --s-tol; dt = DL time - PhaseNet+ time; candidate pairs taken in order of increasing |dt|, each pick
# used at most once. Stations are compared by code only (scautopick stores S picks on the vertical channel).
#
# Definitions (all disclosed in summary.json):
#   event window    : HYPOINVERSE origin (inputs/rtdd_catalog/event.csv) - --win-before s to + --win-after s
#   recall          : matched reference picks / reference picks at bound stations (all 54 are bound)
#   precision       : matched DL picks / DL picks of that phase inside the event's own window
#   F1              : 2 R P / (R + P)
#   dt statistics   : over matched pairs: median |dt|, MAD = median(|dt - median(dt)|) (robust spread),
#                     95th percentile of |dt|, mean signed dt, median signed dt, max |dt|
#   reference outlier: a PhaseNet+ pick more than --ref-outlier s from the kim1983 grid time
#                     (inputs/nll_kim1983/validation_picks.csv; 17 picks: 9 P + 8 S). Recall is also given
#                     without them.
#   predicted times : NonLinLoc kim1983 grids (pyrtdd NLLGrid) at the HypoDD dt.cc location and origin.
#                     Every non-flagged PhaseNet+ pick lies within 0.94 s (P) / 0.89 s (S) of these, so
#                     --pred-tol (1.0 s) is the "near the predicted arrival" tolerance for both phases.
#   SNR             : 20 log10(RMS[t, t+1 s] / RMS[t-3 s, t-0.5 s]) on the raw counts after demean and a
#                     ONE-PASS (causal) 2-20 Hz Butterworth band-pass (4 corners): a two-pass filter would
#                     smear energy ahead of the onset. P: vertical; S: both horizontals combined.
#
# Classes of unmatched DL picks INSIDE the own event window (first rule that applies):
#   near_duplicate        another DL pick of the same station and phase lies within the matching tolerance
#                         and is matched (or is the more confident / earlier of two unmatched ones)
#   phase_confusion       a DL P within the P tolerance of the reference S (or, with no reference S,
#                         within --pred-tol of the predicted S and not of the predicted P); a DL S likewise
#                         near the reference/predicted P
#   reference_outlier     the reference pick of this phase at this station is a flagged outlier and the DL
#                         pick is within --pred-tol of the predicted time (DL plausible, reference not)
#   plausible_missed_by_reference  no reference pick of this phase at this station, DL pick within
#                         --pred-tol of the predicted time: a plausible real arrival PhaseNet+ did not pick
#   timing_disagreement   a reference pick exists, DL is farther than the tolerance from it, but within
#                         --pred-tol of the predicted time
#   noise_or_other        none of the above (not near the predicted P or S of the event)
# Classes of DL picks OUTSIDE the own event window ("false triggers" for the rate per station-hour):
#   other_catalog_event   inside the window of another catalog event (only possible in the event-4 file,
#                         which reaches into event 5)
#   coincident            P picks at >= --coinc-min-stations distinct stations within +-(--coinc-window) s
#                         (a possible uncatalogued event); an S pick takes the class of its P pick
#   isolated              everything else
# Why a reference pick was missed (from the --debug logs; missed_reference_diagnosis.csv):
#   P: no_detector_trigger (no model window covered the onset and no trigger within 5 s of it),
#      trigger_not_turned_into_picker (a trigger within 5 s, but no window: dead time / amplitude rule),
#      model_below_minConfidence (every covering window's best P < minConfidence),
#      peak_vetoed_as_S (a P peak >= minConfidence existed but the S curve was >= 80 % of it there),
#      window_picked_other_time (a covering window produced a pick, but > tolerance away);
#   S: no_P_pick_so_no_S_picker (no DL P pick at the station in the window: the S picker never ran),
#      only_P_pick_is_on_this_S_wave (the station's only P pick is the S arrival itself),
#      no_S_window_covering, model_below_minConfidence, window_picked_other_time (as for P).
#
# Best model (rule fixed BEFORE any result was seen): among --main-models, the highest pooled F1 over
# P and S (pooled recall = (mP+mS)/(refP+refS), pooled precision = (mP+mS)/(dlP+dlS in window));
# if two are within 0.005, the one with the smaller pooled 95th percentile of |dt|.
#
# Outputs (in --out-dir): dl_picks_all.csv, reference_vs_dl.csv, summary_by_model.csv, by_event.csv,
# by_sensor.csv, by_distance.csv, by_magnitude.csv, unmatched_in_window.csv,
# unmatched_smallest_events.csv, missed_reference_diagnosis.csv, outside_window.csv, station_hours.csv,
# cost.csv, cost_per_run.csv, fast_vs_reliable.csv, fast_vs_reliable_latency.csv, log_checks.csv,
# best_model.json, summary.json.
#
# Fast vs reliable (phasenet_instance P picks paired between the two variants, same matching rule):
# dt = fast time - reliable time. Pick times lie on the 100 Hz sample grid but differ from it by a few
# microseconds, so the fractions are counted in whole samples, n = round(dt * --sampling-rate)
# (dt_samples in fast_vs_reliable.csv): identical |n| == 0, within 0.02 s |n| <= 2, within 0.05 s |n| <= 5
# (summary.json -> fast_vs_reliable; changed on 2026-10-17 after the independent verification, before
# that: float cuts |dt| < 0.005 s, <= 0.02 s + 1e-9, <= 0.05 s + 1e-9).

import argparse
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

import numpy as np
import obspy
import pandas as pd
from obspy.geodetics.base import gps2dist_azimuth

import pyrtdd.hdd as hdd

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"


# ---------------------------------------------------------------- copied unchanged from 05_compare_picks.py
def read_scml_picks(path):
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
            channel=wf.get("channelCode"),
            method=p.findtext(f"{ns}methodID"),
            phase=p.findtext(f"{ns}phaseHint"),
            confidence=float(comments.get("SNR", comments.get("confidence", "nan"))),
            ref_pick_id=comments.get("RefPickID", ""),
        ))
    cols = ["pick_id", "time", "network", "station", "channel", "method", "phase", "confidence",
            "ref_pick_id"]
    df = pd.DataFrame(rows, columns=cols)       # keeps the columns even when there is no pick
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def match(ref, sc, tol):
    # all candidate pairs within tolerance, smallest |dt| first, each pick used once
    pairs = []
    for i, r in ref.iterrows():
        cand = sc[sc["station"] == r["station"]]
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
# ---------------------------------------------------------------- end of copied functions


def dtstats(dts):
    a = np.asarray(dts, dtype=float)
    if len(a) == 0:
        return dict(n_dt=0, median_abs_dt_s=np.nan, mad_dt_s=np.nan, p95_abs_dt_s=np.nan,
                    mean_dt_s=np.nan, median_dt_s=np.nan, max_abs_dt_s=np.nan)
    return dict(n_dt=int(len(a)), median_abs_dt_s=float(np.median(np.abs(a))),
                mad_dt_s=float(np.median(np.abs(a - np.median(a)))),
                p95_abs_dt_s=float(np.percentile(np.abs(a), 95)), mean_dt_s=float(a.mean()),
                median_dt_s=float(np.median(a)), max_abs_dt_s=float(np.abs(a).max()))


def prf(n_ref, n_m_ref, n_dl, n_m_dl):
    r = n_m_ref / n_ref if n_ref else np.nan
    p = n_m_dl / n_dl if n_dl else np.nan
    f = 2 * r * p / (r + p) if (n_ref and n_dl and (r + p) > 0) else np.nan
    return r, p, f


def metrics(ref, dl, extra_cols=None):
    """ref: reference rows (matched, dt_s, ref_outlier); dl: DL rows inside the own window (matched)."""
    n_ref = len(ref)
    n_m = int(ref["matched"].sum())
    n_dl = len(dl)
    n_m_dl = int(dl["matched"].sum())
    r, p, f = prf(n_ref, n_m, n_dl, n_m_dl)
    ok = ref[~ref["ref_outlier"]]
    d = dict(n_ref=n_ref, n_matched=n_m, recall=r, n_dl_in_window=n_dl, n_dl_matched=n_m_dl,
             precision=p, f1=f, n_ref_not_outlier=len(ok), recall_without_ref_outliers=
             (ok["matched"].sum() / len(ok)) if len(ok) else np.nan)
    d.update(dtstats(ref.loc[ref["matched"], "dt_s"]))
    return d


def snr_db(traces, t, sig=(0.0, 1.0), noi=(-3.0, -0.5)):
    """traces: list of (times_abs_ns array, filtered data); combined RMS over the traces (horizontals)."""
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
    """Counts, per-attempt rows and detector triggers of a scautopick --debug log.
    best_value = the logged confidence of an accepted candidate, else the window's best P ('bestP') for a
    rejected P window; for S windows it is the largest S value after the P pick in that window."""
    n_trig = n_pp = n_sp = 0
    rows, trig = [], []
    for line in open(path, errors="replace"):
        if "trigger on =" in line:
            n_trig += 1
            t = TRIGGER_RE.search(line)
            if t:
                trig.append(dict(station=t.group(1).split(".")[1], time=pd.Timestamp(t.group(2))))
        elif "created picker DL3C" in line:
            n_pp += 1
        elif "created secondary picker SDL3C" in line:
            n_sp += 1
        m = ATTEMPT_RE.search(line)
        if m:
            meth, sta, k, n, body, ref, off, win = m.groups()
            conf = re.search(r"confidence=([0-9.]+)", body)
            bestp = re.search(r"bestP=([0-9.]+)", body)
            rows.append(dict(method=meth, station=sta.split(".")[-1], attempt=int(k), n_attempts=int(n),
                             accepted_candidate=conf is not None and "no P peak" not in body,
                             confidence=float(conf.group(1)) if conf else np.nan,
                             best_value=float(conf.group(1)) if conf else (float(bestp.group(1)) if bestp else np.nan),
                             ref=pd.Timestamp(ref), offset_s=float(off), window_s=float(win)))
    return n_trig, n_pp, n_sp, pd.DataFrame(rows), pd.DataFrame(trig, columns=["station", "time"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--variants", nargs="+", required=True)
    ap.add_argument("--main-models", nargs="+", required=True)
    ap.add_argument("--fast-variant", default="phasenet_instance_fast")
    ap.add_argument("--fast-reference-variant", default="phasenet_instance")
    ap.add_argument("--p-tol", type=float, default=0.5)
    ap.add_argument("--s-tol", type=float, default=1.0)
    ap.add_argument("--win-before", type=float, default=5.0)
    ap.add_argument("--win-after", type=float, default=60.0)
    ap.add_argument("--ref-outlier", type=float, default=1.0)
    ap.add_argument("--pred-tol", type=float, default=1.0)
    ap.add_argument("--agree-tol", type=float, default=0.2, help="other-model agreement tolerance [s]")
    ap.add_argument("--coinc-window", type=float, default=10.0)
    ap.add_argument("--coinc-min-stations", type=int, default=3)
    ap.add_argument("--init-time", type=float, default=60.0, help="scautopick initTime [s]")
    ap.add_argument("--sampling-rate", type=float, default=100.0,
                    help="sample rate of the data and models [Hz], for fast-vs-reliable dt in whole samples")
    ap.add_argument("--smallest", nargs="+", default=["20210828133922", "20260203021535"],
                    help="the two ML 1.1 events (event_id_map.csv)")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    tol = {"P": a.p_tol, "S": a.s_tol}

    # ------------------------------------------------------------------ inputs
    idm = pd.read_csv(f"{DATA}/reference_tables/event_id_map.csv", dtype={"kma_id": str})
    ev = pd.read_csv(f"{DATA}/inputs/rtdd_catalog/event.csv").rename(columns={"id": "rtdd_id"})
    ev = ev.merge(idm[["rtdd_id", "kma_id", "kma_ml"]], on="rtdd_id")
    ev["origin"] = pd.to_datetime(ev["isotime"], utc=True)
    ev["w0"] = ev["origin"] - pd.Timedelta(seconds=a.win_before)
    ev["w1"] = ev["origin"] + pd.Timedelta(seconds=a.win_after)
    dd = pd.read_csv(f"{DATA}/reference_tables/hypodd_dtcc.csv", dtype={"kma_id": str})
    dd["origin_dd"] = pd.to_datetime(dd["origin_time_pha_datum"], utc=True)
    ev = ev.merge(dd[["kma_id", "latitude", "longitude", "depth_km", "origin_dd"]].rename(
        columns={"latitude": "lat_dd", "longitude": "lon_dd"}), on="kma_id")
    ev = ev.set_index("kma_id")
    sta = pd.read_csv(f"{DATA}/inputs/rtdd_catalog/station.csv").set_index("stationCode")
    bound = pd.read_csv(f"{a.run_dir}/config/stations_bound.csv").set_index("station")
    sensor_of = bound["sensor"].to_dict()

    ref = pd.read_csv(f"{DATA}/reference_tables/picks_phasenet_plus.csv", dtype={"kma_id": str})
    ref["time"] = pd.to_datetime(ref["time"], utc=True)
    val = pd.read_csv(f"{DATA}/inputs/nll_kim1983/validation_picks.csv", dtype={"Event_ID": str})
    val = val.rename(columns={"Event_ID": "kma_id", "Station": "station", "Phase": "phase"})
    ref = ref.merge(val[["kma_id", "station", "phase", "res_obs_minus_grid_s"]], on=["kma_id", "station", "phase"],
                    how="left", validate="one_to_one")
    ref["ref_outlier"] = ref["res_obs_minus_grid_s"].abs() > a.ref_outlier
    ref["bound"] = ref["station"].isin(bound.index[bound["bound"] == 1])
    if not ref["bound"].all():
        print(f"WARNING: {(~ref['bound']).sum()} reference picks at unbound stations")

    # distances and predicted travel times (NLL kim1983 grids, HypoDD dt.cc locations)
    ttt = hdd.NLLGrid(gridPath=f"{DATA}/inputs/nll_kim1983/time", gridModel="kim1983", maxSearchDistance=0.1)
    geo = []
    for kma, e in ev.iterrows():
        for s, srow in sta.iterrows():
            d_m, _, _ = gps2dist_azimuth(e["latitude"], e["longitude"], srow["latitude"], srow["longitude"])
            tp = ttt.compute(e["lat_dd"], e["lon_dd"], e["depth_km"], srow["latitude"], srow["longitude"],
                             srow["elevation"], "P")
            ts = ttt.compute(e["lat_dd"], e["lon_dd"], e["depth_km"], srow["latitude"], srow["longitude"],
                             srow["elevation"], "S")
            geo.append(dict(kma_id=kma, station=s, dist_km=d_m / 1000.0,
                            pred_P=e["origin_dd"] + pd.Timedelta(seconds=tp),
                            pred_S=e["origin_dd"] + pd.Timedelta(seconds=ts)))
    geo = pd.DataFrame(geo).set_index(["kma_id", "station"])
    ref = ref.join(geo, on=["kma_id", "station"])
    ref["res_pred_s"] = np.where(ref["phase"] == "P", (ref["time"] - ref["pred_P"]).dt.total_seconds(),
                                 (ref["time"] - ref["pred_S"]).dt.total_seconds())
    dist_check = float((ref["dist_km"] - ref["epi_dist_km"]).abs().max())

    def dbin(d):
        return "<30 km" if d < 30 else ("30-60 km" if d < 60 else ">60 km")

    def mclass(ml):
        return "ML<1.5" if ml < 1.5 else "ML>=1.5"

    ref["dist_bin"] = ref["dist_km"].map(dbin)
    ref["mag_class"] = ref["kma_id"].map(lambda k: mclass(ev.loc[k, "kma_ml"]))

    # ------------------------------------------------------------------ waveforms (SNR, station-hours)
    wf = {}            # (kma, station) -> dict(Z=[(tns, x)], H=[...])
    hours = []
    for kma in ev.index:
        st = obspy.read(f"{a.run_dir}/input/{kma}_sorted.mseed")
        st.merge(method=0)
        for tr in st:
            s = tr.stats.station
            if s not in sensor_of or tr.stats.channel[:2] != sensor_of[s]:
                continue
            x = tr.data.astype(float)
            x -= x.mean()
            trf = tr.copy()
            trf.data = x
            trf.filter("bandpass", freqmin=2.0, freqmax=20.0, corners=4, zerophase=False)
            tns = (tr.stats.starttime.ns + np.arange(tr.stats.npts) * int(round(1e9 / tr.stats.sampling_rate)))
            key = (kma, s)
            wf.setdefault(key, {"Z": [], "H": []})
            wf[key]["Z" if tr.stats.channel[2] == "Z" else "H"].append((tns, trf.data))
            if tr.stats.channel[2] == "Z":
                hours.append(dict(kma_id=kma, station=s, sensor=sensor_of[s],
                                  start=pd.Timestamp(tr.stats.starttime.datetime, tz="UTC"),
                                  end=pd.Timestamp(tr.stats.endtime.datetime, tz="UTC")))
    hours = pd.DataFrame(hours)
    hours["span_s"] = (hours["end"] - hours["start"]).dt.total_seconds()

    def pick_snr(kma, s, phase, t):
        w = wf.get((kma, s))
        if w is None:
            return np.nan
        return snr_db(w["Z"] if phase == "P" else w["H"], t.value)

    ref["snr_db"] = [pick_snr(r.kma_id, r.station, r.phase, r.time) for r in ref.itertuples()]

    # ------------------------------------------------------------------ DL picks, matching
    all_dl, all_ref, logs, costs, trigs = [], [], [], [], []
    for v in a.variants:
        for kma in ev.index:
            out = f"{a.run_dir}/output/{v}/{kma}"
            dl = read_scml_picks(f"{out}/picks.xml")
            dl["variant"], dl["kma_id"] = v, kma
            e = ev.loc[kma]
            dl["t_rel_origin_s"] = (dl["time"] - e["origin"]).dt.total_seconds()
            dl["in_window"] = (dl["time"] >= e["w0"]) & (dl["time"] <= e["w1"])
            other = []
            for t in dl["time"]:
                o = [k for k in ev.index if k != kma and ev.loc[k, "w0"] <= t <= ev.loc[k, "w1"]]
                other.append(o[0] if o else "")
            dl["other_event"] = other
            dl["sensor"] = dl["station"].map(sensor_of)
            g = geo.loc[kma]
            dl["dist_km"] = dl["station"].map(g["dist_km"])
            dl["res_pred_P_s"] = (dl["time"] - dl["station"].map(g["pred_P"])).dt.total_seconds()
            dl["res_pred_S_s"] = (dl["time"] - dl["station"].map(g["pred_S"])).dt.total_seconds()
            dl["matched"] = False
            dl["ref_dt_s"] = np.nan
            r = ref[ref["kma_id"] == kma].copy()
            r["variant"] = v
            r["matched"] = False
            r["dt_s"] = np.nan
            r["dl_confidence"] = np.nan
            r["dl_pick_id"] = ""
            for ph in ("P", "S"):
                m = match(r[r["phase"] == ph], dl[dl["phase"] == ph], tol[ph])
                for i, (j, dt) in m.items():
                    r.loc[i, ["matched", "dt_s", "dl_confidence", "dl_pick_id"]] = [True, dt, dl.loc[j, "confidence"],
                                                                                    dl.loc[j, "pick_id"]]
                    dl.loc[j, ["matched", "ref_dt_s"]] = [True, dt]
            all_dl.append(dl)
            all_ref.append(r)
            n_trig, n_pp, n_sp, att, trg = parse_log(f"{out}/scautopick.log")
            att["variant"], att["kma_id"] = v, kma
            trg["variant"], trg["kma_id"] = v, kma
            logs.append(att)
            trigs.append(trg)
            tt = parse_time_txt(f"{out}/time.txt")
            costs.append(dict(variant=v, kma_id=kma, triggers=n_trig, p_pickers=n_pp, s_pickers=n_sp,
                              p_windows=int((att["method"] == "DL3C").sum()) if len(att) else 0,
                              s_windows=int((att["method"] == "SDL3C").sum()) if len(att) else 0,
                              n_picks=len(dl), **tt))
        tt = parse_time_txt(f"{a.run_dir}/output/{v}/startup_probe/time.txt")
        costs.append(dict(variant=v, kma_id="startup_probe", **tt))
    dl = pd.concat(all_dl, ignore_index=True)
    rv = pd.concat(all_ref, ignore_index=True)
    att = pd.concat(logs, ignore_index=True)
    trg = pd.concat(trigs, ignore_index=True)
    cost = pd.DataFrame(costs)

    # SNR of DL picks inside their window (cheap) and of all P picks outside (for the false-trigger table)
    dl["snr_db"] = [pick_snr(x.kma_id, x.station, x.phase, x.time) for x in dl.itertuples()]

    # agreement with the other main models (same event, station, phase, within --agree-tol)
    key = dl.groupby(["kma_id", "station", "phase"])
    n_agree = []
    for x in dl.itertuples():
        grp = key.get_group((x.kma_id, x.station, x.phase))
        others = grp[(grp["variant"] != x.variant) & grp["variant"].isin(a.main_models)]
        close = others[(others["time"] - x.time).abs() <= pd.Timedelta(seconds=a.agree_tol)]
        n_agree.append(close["variant"].nunique())
    dl["n_other_main_models_agree"] = n_agree

    # ------------------------------------------------------------------ classification
    refkey = {(r.kma_id, r.station, r.phase): r for r in ref.itertuples()}
    cls = []
    for x in dl.itertuples():
        if x.matched:
            cls.append("matched")
            continue
        if not x.in_window:
            cls.append("")
            continue
        same = dl[(dl["variant"] == x.variant) & (dl["kma_id"] == x.kma_id) & (dl["station"] == x.station)
                  & (dl["phase"] == x.phase) & (dl.index != x.Index)]
        close = same[(same["time"] - x.time).abs() <= pd.Timedelta(seconds=tol[x.phase])]
        dup = False
        for y in close.itertuples():
            if y.matched or (y.confidence > x.confidence) or (y.confidence == x.confidence and y.time < x.time):
                dup = True
        if dup:
            cls.append("near_duplicate")
            continue
        other = "S" if x.phase == "P" else "P"
        rp_other = refkey.get((x.kma_id, x.station, other))
        rp_same = refkey.get((x.kma_id, x.station, x.phase))
        res_same = x.res_pred_P_s if x.phase == "P" else x.res_pred_S_s
        res_other = x.res_pred_S_s if x.phase == "P" else x.res_pred_P_s
        near_same = abs(res_same) <= a.pred_tol
        if rp_other is not None:
            conf_ph = abs((x.time - rp_other.time).total_seconds()) <= tol[x.phase]
        else:
            conf_ph = abs(res_other) <= a.pred_tol and not near_same
        if conf_ph:
            cls.append("phase_confusion")
        elif rp_same is not None and rp_same.ref_outlier and near_same:
            cls.append("reference_outlier")
        elif rp_same is None and near_same:
            cls.append("plausible_missed_by_reference")
        elif rp_same is not None and near_same:
            cls.append("timing_disagreement")
        else:
            cls.append("noise_or_other")
    dl["class"] = cls

    # outside-window picks: other catalog event / coincident / isolated
    out_mask = ~dl["in_window"]
    dl.loc[out_mask & (dl["other_event"] != ""), "class"] = "other_catalog_event"
    for (v, kma), g in dl[out_mask & (dl["other_event"] == "")].groupby(["variant", "kma_id"]):
        for ph in ("P", "S"):              # P first; an S pick then takes the class of its own P pick
            gp = g[g["phase"] == ph]
            for x in gp.itertuples():
                if ph == "S":
                    own_p = dl[(dl["variant"] == v) & (dl["kma_id"] == kma) & (dl["pick_id"] == x.ref_pick_id)]
                    if len(own_p) == 1 and own_p.iloc[0]["class"] in ("coincident", "isolated"):
                        dl.loc[x.Index, "class"] = own_p.iloc[0]["class"]
                        continue
                near = gp[(gp["time"] - x.time).abs() <= pd.Timedelta(seconds=a.coinc_window)]
                dl.loc[x.Index, "class"] = ("coincident" if near["station"].nunique() >= a.coinc_min_stations
                                            else "isolated")

    # ------------------------------------------------------------------ why reference picks were missed
    # (from the --debug logs: every model window with its position and best value, and every detector trigger)
    minconf = {}
    for v in a.variants:
        sj = json.load(open(f"{a.run_dir}/settings/scautopick_{v}.settings.json"))["plugin_resolved"]
        minconf[v] = (float(sj["picker.DL3C"]["minConfidence"]["value"]),
                      float(sj["spicker.SDL3C"]["minConfidence"]["value"]))
    att["w_start"] = att["ref"] + pd.to_timedelta(att["offset_s"], unit="s")
    att["w_end"] = att["w_start"] + pd.to_timedelta(att["window_s"], unit="s")
    miss = rv[~rv["matched"]].copy()
    why, best_val = [], []
    for x in miss.itertuples():
        A = att[(att["variant"] == x.variant) & (att["kma_id"] == x.kma_id) & (att["station"] == x.station)]
        if x.phase == "P":
            W = A[(A["method"] == "DL3C") & (A["w_start"] <= x.time) & (A["w_end"] >= x.time)]
            if len(W) == 0:
                T = trg[(trg["variant"] == x.variant) & (trg["kma_id"] == x.kma_id) & (trg["station"] == x.station)
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
            pp = dl[(dl["variant"] == x.variant) & (dl["kma_id"] == x.kma_id) & (dl["station"] == x.station)
                    & (dl["phase"] == "P") & dl["in_window"]]
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
    miss[["variant", "kma_id", "station", "sensor", "phase", "time", "probability", "dist_km", "ref_outlier",
          "snr_db", "why_missed", "best_value_in_covering_windows"]].to_csv(
        f"{a.out_dir}/missed_reference_diagnosis.csv", index=False, float_format="%.3f")
    miss_counts = miss.groupby(["variant", "phase", "why_missed"]).size().unstack(fill_value=0)

    # ------------------------------------------------------------------ tables
    win = dl[dl["in_window"]]
    rows = []

    def add(group_name, group_val, v, ph, rsel, dsel):
        d = dict(variant=v, phase=ph, group=group_name, value=group_val)
        d.update(metrics(rsel, dsel))
        rows.append(d)

    for v in a.variants:
        for ph in ("P", "S", "P+S"):
            phs = ["P", "S"] if ph == "P+S" else [ph]
            rr = rv[(rv["variant"] == v) & rv["phase"].isin(phs)]
            ww = win[(win["variant"] == v) & win["phase"].isin(phs)]
            add("all", "all", v, ph, rr, ww)
            for sname in ("HH", "HG", "EL"):
                add("sensor", sname, v, ph, rr[rr["sensor"] == sname], ww[ww["sensor"] == sname])
            for b in ("<30 km", "30-60 km", ">60 km"):
                add("distance", b, v, ph, rr[rr["dist_bin"] == b], ww[ww["dist_km"].map(dbin) == b])
            for mc in ("ML<1.5", "ML>=1.5"):
                kk = [k for k in ev.index if mclass(ev.loc[k, "kma_ml"]) == mc]
                add("magnitude", mc, v, ph, rr[rr["kma_id"].isin(kk)], ww[ww["kma_id"].isin(kk)])
            for k in ev.index:
                add("event", f"{k} ML{ev.loc[k, 'kma_ml']:.1f}", v, ph, rr[rr["kma_id"] == k], ww[ww["kma_id"] == k])
    tab = pd.DataFrame(rows)
    # upper-bound precision: unmatched in-window picks of the classes plausible_missed_by_reference and
    # reference_outlier (near the predicted arrival where PhaseNet+ has no pick or an outlier) counted as correct
    plaus = win[(~win["matched"]) & win["class"].isin(["plausible_missed_by_reference", "reference_outlier"])]
    tab["n_dl_plausible_unmatched"] = np.nan
    tab["precision_counting_plausible"] = np.nan
    for i, r in tab[tab["group"] == "all"].iterrows():
        phs = ["P", "S"] if r["phase"] == "P+S" else [r["phase"]]
        n_pl = int(((plaus["variant"] == r["variant"]) & plaus["phase"].isin(phs)).sum())
        tab.loc[i, "n_dl_plausible_unmatched"] = n_pl
        tab.loc[i, "precision_counting_plausible"] = (r["n_dl_matched"] + n_pl) / r["n_dl_in_window"]
    tab[tab["group"] == "all"].to_csv(f"{a.out_dir}/summary_by_model.csv", index=False, float_format="%.4f")
    for gname, fname in (("sensor", "by_sensor"), ("distance", "by_distance"), ("magnitude", "by_magnitude"),
                         ("event", "by_event")):
        tab[tab["group"] == gname].to_csv(f"{a.out_dir}/{fname}.csv", index=False, float_format="%.4f")

    # station-hours per event file (bound stations, vertical channel), raw and searchable
    p_end = {}
    for v in a.variants:
        sj = json.load(open(f"{a.run_dir}/settings/scautopick_{v}.settings.json"))
        p_end[v] = sj["plugin_resolved"]["picker.DL3C"]["resolved"]["maxLatency_s"]
    hrow = []
    for v in a.variants:
        for h in hours.itertuples():
            s0 = h.start + pd.Timedelta(seconds=a.init_time)
            s1 = h.end - pd.Timedelta(seconds=p_end[v])
            eff = max(0.0, (s1 - s0).total_seconds())
            for k in ev.index:                      # remove every catalog event window inside the span
                o0, o1 = max(s0, ev.loc[k, "w0"]), min(s1, ev.loc[k, "w1"])
                if o1 > o0:
                    eff -= (o1 - o0).total_seconds()
            hrow.append(dict(variant=v, kma_id=h.kma_id, station=h.station, sensor=h.sensor,
                             span_h=h.span_s / 3600.0, searchable_outside_windows_h=eff / 3600.0))
    hrs = pd.DataFrame(hrow)
    hrs.to_csv(f"{a.out_dir}/station_hours.csv", index=False, float_format="%.5f")

    owrows = []
    outside = dl[~dl["in_window"]]
    for v in a.variants:
        hv = hrs[hrs["variant"] == v]
        H_raw, H_eff = hv["span_h"].sum(), hv["searchable_outside_windows_h"].sum()
        for ph in ("P", "S"):
            o = outside[(outside["variant"] == v) & (outside["phase"] == ph)]
            n_false = int(o["class"].isin(["coincident", "isolated"]).sum())
            d = dict(variant=v, phase=ph, n_outside=len(o),
                     n_other_catalog_event=int((o["class"] == "other_catalog_event").sum()),
                     n_coincident=int((o["class"] == "coincident").sum()),
                     n_isolated=int((o["class"] == "isolated").sum()),
                     station_hours_raw=H_raw, station_hours_searchable=H_eff,
                     false_per_station_hour_raw=n_false / H_raw,
                     false_per_station_hour_searchable=n_false / H_eff,
                     isolated_per_station_hour_searchable=int((o["class"] == "isolated").sum()) / H_eff,
                     median_confidence=float(o["confidence"].median()) if len(o) else np.nan)
            for sname in ("HH", "HG", "EL"):
                hs = hv[hv["sensor"] == sname]["searchable_outside_windows_h"].sum()
                d[f"false_per_station_hour_{sname}"] = int(o[o["sensor"] == sname]["class"].isin(
                    ["coincident", "isolated"]).sum()) / hs if hs else np.nan
            owrows.append(d)
    ow = pd.DataFrame(owrows)
    ow.to_csv(f"{a.out_dir}/outside_window.csv", index=False, float_format="%.4f")

    # unmatched picks inside the window
    um = win[~win["matched"]].copy()
    um_cols = ["variant", "kma_id", "station", "sensor", "phase", "time", "t_rel_origin_s", "confidence", "class",
               "dist_km", "res_pred_P_s", "res_pred_S_s", "snr_db", "n_other_main_models_agree", "pick_id"]
    um[um_cols].sort_values(["kma_id", "variant", "station", "phase"]).to_csv(
        f"{a.out_dir}/unmatched_in_window.csv", index=False, float_format="%.3f")
    ums = um[um["kma_id"].isin(a.smallest)][um_cols].sort_values(["kma_id", "station", "phase", "variant"])
    ums.to_csv(f"{a.out_dir}/unmatched_smallest_events.csv", index=False, float_format="%.3f")
    um_counts = um.groupby(["variant", "phase", "class"]).size().unstack(fill_value=0)

    # cost: CPU per station-hour (raw span of the bound vertical channels)
    cr = []
    for v in a.variants:
        c = cost[(cost["variant"] == v) & (cost["kma_id"] != "startup_probe")]
        probe = cost[(cost["variant"] == v) & (cost["kma_id"] == "startup_probe")].iloc[0]
        cpu = (c["user_s"] + c["sys_s"]).sum()
        H = hrs[hrs["variant"] == v]["span_h"].sum()
        cpu_probe = probe["user_s"] + probe["sys_s"]
        nw = c["p_windows"].sum() + c["s_windows"].sum()
        cr.append(dict(variant=v, runs=len(c), station_hours=H, cpu_s_total=cpu, wall_s_total=c["wall_s"].sum(),
                       cpu_s_per_station_hour=cpu / H,
                       startup_probe_cpu_s=cpu_probe,
                       cpu_s_per_station_hour_minus_startup=(cpu - len(c) * cpu_probe) / H,
                       triggers=int(c["triggers"].sum()), p_windows=int(c["p_windows"].sum()),
                       s_windows=int(c["s_windows"].sum()), windows_per_station_hour=nw / H,
                       cpu_ms_per_window=1000 * (cpu - len(c) * cpu_probe) / nw if nw else np.nan,
                       max_rss_mb=c["maxrss_mb"].max()))
    costt = pd.DataFrame(cr)
    costt.to_csv(f"{a.out_dir}/cost.csv", index=False, float_format="%.4f")
    cost.to_csv(f"{a.out_dir}/cost_per_run.csv", index=False, float_format="%.4f")

    # log checks: window offsets seen per variant and method (must equal the resolved settings)
    lc = (att.groupby(["variant", "method", "offset_s", "window_s"]).size().rename("n_attempts").reset_index())
    lc.to_csv(f"{a.out_dir}/log_checks.csv", index=False)

    # fast vs reliable (phasenet_instance): P picks paired between the two variants, and pick latency
    fv, rvn = a.fast_variant, a.fast_reference_variant
    fr = {}
    if fv in a.variants and rvn in a.variants:
        A = dl[(dl["variant"] == rvn) & (dl["phase"] == "P")]
        B = dl[(dl["variant"] == fv) & (dl["phase"] == "P")]
        pairs = []
        for kma in ev.index:
            Ak, Bk = A[A["kma_id"] == kma], B[B["kma_id"] == kma]
            m = match(Ak, Bk, a.p_tol)
            for i, (j, dt) in m.items():
                pairs.append(dict(kma_id=kma, station=Ak.loc[i, "station"], time_reliable=Ak.loc[i, "time"],
                                  time_fast=Bk.loc[j, "time"], dt_fast_minus_reliable_s=dt,
                                  conf_reliable=Ak.loc[i, "confidence"], conf_fast=Bk.loc[j, "confidence"],
                                  in_window=bool(Ak.loc[i, "in_window"]),
                                  reliable_matched_ref=bool(Ak.loc[i, "matched"]),
                                  fast_matched_ref=bool(Bk.loc[j, "matched"])))
        pf = pd.DataFrame(pairs)
        # whole samples: pick times lie on the 100 Hz grid but differ from it by microseconds, so a cut such
        # as |dt| <= 0.02 s is ill-defined at exactly 2 samples; count n = round(dt * --sampling-rate) instead
        if len(pf):
            pf["dt_samples"] = np.rint(pf["dt_fast_minus_reliable_s"].to_numpy() * a.sampling_rate).astype(int)
        # latency: the accepted attempt of each P picker = first attempt line with a confidence (fast
        # strategy accepts the first window with a P peak over minConfidence); window end = ref + offset + window
        lat = []
        for v in (fv, rvn):
            at = att[(att["variant"] == v) & (att["method"] == "DL3C") & att["accepted_candidate"]]
            at = at.sort_values(["kma_id", "station", "ref", "attempt"])
            first = at.groupby(["kma_id", "station", "ref"]).head(1)
            for x in first.itertuples():
                end = x.ref + pd.Timedelta(seconds=x.offset_s + x.window_s)
                cand = dl[(dl["variant"] == v) & (dl["kma_id"] == x.kma_id) & (dl["station"] == x.station)
                          & (dl["phase"] == "P") & ((dl["confidence"] - x.confidence).abs() < 0.006)
                          & (dl["time"] >= x.ref + pd.Timedelta(seconds=x.offset_s)) & (dl["time"] <= end)]
                if len(cand) == 1:
                    c = cand.iloc[0]
                    lat.append(dict(variant=v, kma_id=x.kma_id, station=x.station, attempt=x.attempt,
                                    window_end_after_trigger_s=x.offset_s + x.window_s,
                                    pick_available_after_onset_s=(end - c["time"]).total_seconds(),
                                    in_window=bool(c["in_window"]), matched=bool(c["matched"])))
        lt = pd.DataFrame(lat)
        pf.to_csv(f"{a.out_dir}/fast_vs_reliable.csv", index=False, float_format="%.4f")
        lt.to_csv(f"{a.out_dir}/fast_vs_reliable_latency.csv", index=False, float_format="%.3f")
        d = pf["dt_fast_minus_reliable_s"].to_numpy() if len(pf) else np.array([])
        dwin = pf.loc[pf["in_window"], "dt_fast_minus_reliable_s"].to_numpy() if len(pf) else np.array([])
        n_ = np.abs(pf["dt_samples"].to_numpy()) if len(pf) else np.array([], dtype=int)
        nwin = np.abs(pf.loc[pf["in_window"], "dt_samples"].to_numpy()) if len(pf) else np.array([], dtype=int)
        fr = dict(n_reliable_P=int(len(A)), n_fast_P=int(len(B)), n_paired=int(len(pf)),
                  n_paired_in_window=int(len(dwin)),
                  dt_definition="fast time - reliable time [s]; fractions counted in whole samples, "
                                f"n = round(dt * {a.sampling_rate:g} Hz): identical |n| == 0, "
                                "within 0.02 s |n| <= 2, within 0.05 s |n| <= 5",
                  identical_fraction=float(np.mean(n_ == 0)) if len(n_) else np.nan,
                  within_2_samples_fraction=float(np.mean(n_ <= 2)) if len(n_) else np.nan,
                  within_5_samples_fraction=float(np.mean(n_ <= 5)) if len(n_) else np.nan,
                  in_window_identical_fraction=float(np.mean(nwin == 0)) if len(nwin) else np.nan,
                  in_window_within_2_samples_fraction=float(np.mean(nwin <= 2)) if len(nwin) else np.nan,
                  in_window_within_5_samples_fraction=float(np.mean(nwin <= 5)) if len(nwin) else np.nan,
                  **{f"dt_{k}": val for k, val in dtstats(d).items()},
                  **{f"dt_in_window_{k}": val for k, val in dtstats(dwin).items()})
        for v in (fv, rvn):
            q = lt[(lt["variant"] == v) & lt["in_window"]] if len(lt) else lt
            if len(q):
                fr[f"{v}_pick_available_after_onset_s_median_in_window"] = float(q["pick_available_after_onset_s"].median())
                fr[f"{v}_pick_available_after_onset_s_p90_in_window"] = float(q["pick_available_after_onset_s"].quantile(0.9))
                fr[f"{v}_latency_rows_in_window"] = int(len(q))
                fr[f"{v}_accepted_attempt_counts_in_window"] = q["attempt"].value_counts().sort_index().to_dict()

    # best model (rule in the header)
    allp = tab[(tab["group"] == "all") & (tab["phase"] == "P+S") & tab["variant"].isin(a.main_models)]
    allp = allp.sort_values(["f1", "p95_abs_dt_s"], ascending=[False, True]).reset_index(drop=True)
    best = allp.iloc[0]
    if len(allp) > 1 and abs(allp.iloc[0]["f1"] - allp.iloc[1]["f1"]) < 0.005:
        tied = allp[(allp.iloc[0]["f1"] - allp["f1"]) < 0.005]
        best = tied.sort_values("p95_abs_dt_s").iloc[0]
    bj = dict(rule="highest pooled P+S F1 among the main models; ties (<0.005) -> smaller pooled p95 |dt|",
              best_model=best["variant"],
              cfg_file=f"{a.run_dir}/config/scautopick_{best['variant']}.cfg",
              bindings_config=f"{a.run_dir}/config/bindings_config.xml",
              bindings_keydir=f"{a.run_dir}/config/key",
              ranking=allp[["variant", "f1", "recall", "precision", "p95_abs_dt_s", "median_abs_dt_s"]].to_dict("records"))
    json.dump(bj, open(f"{a.out_dir}/best_model.json", "w"), indent=1, default=str)

    # ------------------------------------------------------------------ save + summary
    dl.to_csv(f"{a.out_dir}/dl_picks_all.csv", index=False, float_format="%.4f")
    rv.to_csv(f"{a.out_dir}/reference_vs_dl.csv", index=False, float_format="%.4f")
    summary = dict(
        definitions=dict(p_tol_s=a.p_tol, s_tol_s=a.s_tol, event_window=f"HYPOINVERSE origin -{a.win_before} s .. +{a.win_after} s",
                         ref_outlier_s=a.ref_outlier, pred_tol_s=a.pred_tol, agree_tol_s=a.agree_tol,
                         coincidence=f">= {a.coinc_min_stations} stations within +-{a.coinc_window} s",
                         init_time_s=a.init_time, mad="median(|dt - median(dt)|)",
                         snr="20log10 RMS[t,t+1s]/RMS[t-3s,t-0.5s], one-pass 2-20 Hz BP 4 corners",
                         predicted_times="NLL kim1983 grids at HypoDD dt.cc locations/origins"),
        n_reference=dict(P=int((ref["phase"] == "P").sum()), S=int((ref["phase"] == "S").sum()),
                         outliers=int(ref["ref_outlier"].sum())),
        reference_residual_vs_prediction=dict(
            P_median_s=float(ref.loc[(ref.phase == "P") & ~ref.ref_outlier, "res_pred_s"].median()),
            S_median_s=float(ref.loc[(ref.phase == "S") & ~ref.ref_outlier, "res_pred_s"].median())),
        distance_check_max_abs_km=dist_check,
        summary_by_model=tab[(tab["group"] == "all")].to_dict("records"),
        outside_window=ow.to_dict("records"),
        unmatched_in_window_counts={f"{k[0]}|{k[1]}": v.to_dict() for k, v in um_counts.iterrows()},
        missed_reference_counts={f"{k[0]}|{k[1]}": v.to_dict() for k, v in miss_counts.iterrows()},
        cost=costt.to_dict("records"),
        fast_vs_reliable=fr,
        best_model=bj,
        log_offsets=lc.to_dict("records"),
    )
    json.dump(summary, open(f"{a.out_dir}/summary.json", "w"), indent=1, default=str)

    # ------------------------------------------------------------------ console report
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    show = ["variant", "phase", "n_ref", "n_matched", "recall", "recall_without_ref_outliers", "n_dl_in_window",
            "precision", "f1", "median_abs_dt_s", "mad_dt_s", "p95_abs_dt_s", "mean_dt_s"]
    print("reference picks:", summary["n_reference"], "| distance check max |diff| km: %.3f" % dist_check,
          "| reference residual vs grid (non-outliers):", summary["reference_residual_vs_prediction"])
    print(tab[tab["group"] == "all"][show].round(3).to_string(index=False))
    print("\noutside the event windows:")
    print(ow[["variant", "phase", "n_outside", "n_other_catalog_event", "n_coincident", "n_isolated",
              "station_hours_searchable", "false_per_station_hour_searchable"]].round(3).to_string(index=False))
    print("\nunmatched picks inside the windows, by class:")
    print(um_counts.to_string())
    print("\nmissed reference picks, why:")
    print(miss_counts.to_string())
    print("\ncost:")
    print(costt[["variant", "station_hours", "cpu_s_total", "cpu_s_per_station_hour", "startup_probe_cpu_s",
                 "p_windows", "s_windows", "cpu_ms_per_window"]].round(4).to_string(index=False))
    print("\nfast vs reliable:", json.dumps(fr, default=str))
    print("\nbest model:", bj["best_model"], [(r["variant"], round(r["f1"], 4)) for r in bj["ranking"]])


if __name__ == "__main__":
    main()
