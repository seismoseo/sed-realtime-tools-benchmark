# 12_select_dl_subset_and_waveform_plan.py -- (2025-26 case; copied from the 2015 tool) choose
# (a) the waveform plan for cross-correlation and (b) a 26-event test subset for the deep-learning
# picker, both written as csv files.
#
# (b) DL subset (inputs/dl_subset_events.csv), the 2015 rule adapted:
#     candidates = benchmark events with an NCEDC DD solution (2015: in both DD catalogs; NCEDC DD is
#     the designated reference here), NCSS review flag 'F' (analyst-final; in 2015 all 685 events
#     were 'F', in 2025-26 98 events are automatic-only 'A'/'H' and 65 are 'I'), magnitude
#     0.5..max, >= 8 P picks in rtDD phase.csv. Magnitude bins 0.5-1.0, 1.0-1.5, 1.5-2.0, 2.0-2.5,
#     2.5-3.0, 3.0-max; in each bin N_PER_BIN events nearest to evenly spaced time quantiles
#     (1/8, 3/8, 5/8, 7/8) of that bin. Always included (FORCED): the mainshock 75305736 (Mw 4.18,
#     required) and an overlapping-waveform test event. 2015 used the Md 2.32 event 6.3 s before
#     the mainshock; the 2025-26 mainshock has no neighbour within 10 s (nearest 31 s), so the
#     same role goes to the earlier event of the < 10 s pair whose later event is largest:
#     75283011 (Md 2.29), 5.5 s before 75283016 (Mw 3.77). Deterministic (no random numbers).
# (a) waveform plan (inputs/waveform_plan_channels.csv + _events.csv): all benchmark events;
#     every channel of every picked sensor (all components from stations.xml) of stations with
#     picks within CC_MAX_KM (cross-correlation) / DL_MAX_KM (DL subset) of the swarm centre.
#     DL_MAX_KM = 80 km and DL_WIN = -120..+120 s here (= what download_waveforms.py fetches; the
#     2015 plan said 120 km / -60..+120 s while the 2015 download used 80 km / -120..+120 s).
# Usage: python -I 12_select_dl_subset_and_waveform_plan.py

import os
import sys

import numpy as np
import pandas as pd
from pyproj import Geod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

LAT0, LON0 = C.LAT0, C.LON0
BINS = [(0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 3.0), (3.0, 4.19)]
N_PER_BIN = 4
FORCED = {C.MAINSHOCK_ID: "Mw 4.18 mainshock (required)",
          75283011: "Md 2.29, 5.5 s before Mw 3.77 75283016: overlapping waveforms "
                    "(role of the 2015 Md 2.32 foreshock; earlier event of the < 10 s pair with "
                    "the largest later event)"}
CC_MAX_KM, DL_MAX_KM = 60.0, 80.0
CC_WIN = (-10.0, 30.0)     # s relative to origin: P and S out to 60 km + rtDD filter margins
DL_WIN = (-120.0, 120.0)   # s relative to origin (as downloaded by download_waveforms.py)


def main():
    ev = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv"))
    ev = ev[ev.benchmark_event].copy()
    ph = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "phase.csv"), keep_default_na=False,
                     dtype={"locationCode": str})
    nP = ph[ph.type == "P"].groupby("eventId").size()
    nS = ph[ph.type == "S"].groupby("eventId").size()
    ev["n_P"] = ev.event_id.map(nP).fillna(0).astype(int)
    ev["n_S"] = ev.event_id.map(nS).fillna(0).astype(int)
    ev["t"] = pd.to_datetime(ev.origin_time_utc.str.rstrip("Z"))
    # the overlap event must be what the rule says: earlier event of the < 10 s pair whose later
    # event has the largest magnitude
    s_ = ev.sort_values("t").reset_index(drop=True)
    gap = s_.t.diff().dt.total_seconds()
    pairs = [(s_.loc[i - 1, "event_id"], s_.loc[i, "pref_mag"]) for i in range(1, len(s_)) if gap[i] < 10]
    assert max(pairs, key=lambda x: x[1])[0] in FORCED, ("overlap rule", pairs)
    mmax = float(ev.pref_mag.max())
    cand = ev[ev.in_ncedc_dd & (ev.review_version == "F") & (ev.n_P >= 8) &
              ev.pref_mag.between(0.5, mmax)]
    rows = []
    for eid, why in FORCED.items():
        rows.append(dict(event_id=eid, reason=why))
    chosen = set(FORCED)
    for lo, hi in BINS:
        b = cand[(cand.pref_mag >= lo) & (cand.pref_mag < hi) & ~cand.event_id.isin(chosen)]
        b = b.sort_values("t")
        if len(b) == 0:
            continue
        qs = (np.arange(N_PER_BIN) + 0.5) / N_PER_BIN
        tq = b.t.quantile(qs, interpolation="nearest").values
        for q, t in zip(qs, tq):
            avail = b[~b.event_id.isin(chosen)]
            if len(avail) == 0:
                break
            k = (avail.t - pd.Timestamp(t)).abs().idxmin()
            eid = int(avail.loc[k, "event_id"])
            chosen.add(eid)
            rows.append(dict(event_id=eid, reason=f"magnitude bin {lo:.1f}-{min(hi, mmax):.2f}, "
                                                   f"time quantile {q:.3f} of that bin"))
    sub = pd.DataFrame(rows).merge(ev, on="event_id", how="left")
    sub = sub.sort_values("t")
    # other benchmark events within +-10 s (their waveforms overlap in the DL windows)
    sub["other_events_within_10s"] = [
        ";".join(f"{int(o.event_id)}({(o.t - t).total_seconds():+.1f}s,M{o.pref_mag:.2f})"
                 for o in ev[(ev.t - t).abs().dt.total_seconds().between(0.001, 10)].itertuples())
        for t in sub.t]
    sub[["event_id", "origin_time_utc", "latitude", "longitude", "depth_geoid_km", "pref_mag",
         "pref_mag_type", "n_P", "n_S", "in_ncedc_dd", "in_ldeo_dd", "review_version",
         "other_events_within_10s", "reason"]].to_csv(
        os.path.join(C.INP, "dl_subset_events.csv"), index=False)
    print(sub[["event_id", "origin_time_utc", "pref_mag", "n_P", "n_S", "other_events_within_10s",
               "reason"]].to_string())
    print("DL subset size", len(sub))

    # ---- waveform plan: channels of picked sensors
    ch = pd.read_csv(os.path.join(C.TAB, "station_channels.csv"), keep_default_na=False,
                     dtype={"location": str})
    ch["group"] = ch.channel.str[:2]
    picked_groups = ch[ch.picked.astype(str) == "True"][["network", "station", "location", "group"]]
    picked_groups = picked_groups.drop_duplicates()
    plan = ch.merge(picked_groups, on=["network", "station", "location", "group"])
    plan = plan.drop_duplicates(["network", "station", "location", "channel"])
    g = Geod(ellps="WGS84")
    _, _, d = g.inv(np.full(len(plan), LON0), np.full(len(plan), LAT0),
                    plan.longitude.astype(float).values, plan.latitude.astype(float).values)
    plan["dist_km"] = np.asarray(d) / 1000
    plan["for_cc"] = plan.dist_km <= CC_MAX_KM
    plan["for_dl"] = plan.dist_km <= DL_MAX_KM
    comps = plan.groupby(["network", "station", "location", "group"]).channel.apply(
        lambda x: "".join(sorted(c[-1] for c in x)))
    plan["sensor_components"] = [comps[(r.network, r.station, r.location, r.group)]
                                 for r in plan.itertuples()]
    plan = plan.sort_values(["dist_km", "network", "station", "location", "channel"])
    plan[["network", "station", "location", "channel", "sample_rate", "dist_km",
          "sensor_components", "picked", "n_picks", "for_cc", "for_dl"]].to_csv(
        os.path.join(C.INP, "waveform_plan_channels.csv"), index=False, float_format="%.3f")
    wev = ev[["event_id", "origin_time_utc", "pref_mag"]].copy()
    t0 = pd.to_datetime(wev.origin_time_utc.str.rstrip("Z"))
    wev["cc_start"] = (t0 + pd.Timedelta(seconds=CC_WIN[0])).dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    wev["cc_end"] = (t0 + pd.Timedelta(seconds=CC_WIN[1])).dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    wev["in_dl_subset"] = wev.event_id.isin(sub.event_id)
    wev["dl_start"] = np.where(wev.in_dl_subset, (t0 + pd.Timedelta(seconds=DL_WIN[0])).dt.strftime(
        "%Y-%m-%dT%H:%M:%S.%f"), "")
    wev["dl_end"] = np.where(wev.in_dl_subset, (t0 + pd.Timedelta(seconds=DL_WIN[1])).dt.strftime(
        "%Y-%m-%dT%H:%M:%S.%f"), "")
    wev.to_csv(os.path.join(C.INP, "waveform_plan_events.csv"), index=False)
    cc = plan[plan.for_cc]
    dl = plan[plan.for_dl]
    n_cc_sta = cc[["network", "station", "location"]].drop_duplicates().shape[0]
    n_dl_sta = dl[["network", "station", "location"]].drop_duplicates().shape[0]
    sps_cc = cc.sample_rate.astype(float).sum()
    sps_dl = dl.sample_rate.astype(float).sum()
    print(f"CC plan: {len(ev)} events x {len(cc)} channels ({n_cc_sta} net.sta.loc <= {CC_MAX_KM} km), "
          f"{CC_WIN[1]-CC_WIN[0]:.0f} s each: ~{len(ev) * sps_cc * (CC_WIN[1]-CC_WIN[0]) / 1e9:.2f} "
          f"G samples")
    print(f"DL plan: {len(sub)} events x {len(dl)} channels ({n_dl_sta} net.sta.loc <= {DL_MAX_KM} km), "
          f"{DL_WIN[1]-DL_WIN[0]:.0f} s each: ~{len(sub) * sps_dl * (DL_WIN[1]-DL_WIN[0]) / 1e9:.2f} "
          f"G samples")


if __name__ == "__main__":
    main()
