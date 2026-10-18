# 08_make_rtdd_inputs.py -- write the rtDD multi-event catalog triplet (station.csv, event.csv,
# phase.csv; format of scrtdd doc/base/multievent.rst) for the San Ramon benchmark, starting from
# the NCSS ROUTINE locations (not the DD ones) and the NCSS analyst picks.
#
# Events   : the 685 'benchmark events' of reference_tables/event_matching.csv (NCSS events whose
#            routine OR NCEDC-DD OR LDEO-DD location is inside the benchmark box).
#            id = NCSS event id (all < 2^32: rtDD reads ids with std::stoul into a 32-bit
#            'unsigned', libs/hdd/catalog.cpp, so larger ids would wrap around silently).
#            depth = NCSS geoid depth (km below sea level), consistent with station elevations.
# Phases   : NCSS P and S picks with Hypoinverse weight code 0-3 whose station has metadata.
#            Codes 4 (no weight) and 5-9 (out-weighted by NCSS: duplicate or misfit) are NOT in
#            phase.csv; they are kept, flagged, in phase_extra.csv.
#            lower/upperUncertainty = NCSN 'subjective error' of the weight code (NCEDC
#            shadow2000.pdf, Table 9): 0 -> 0.02 s, 1 -> 0.10 s, 2 -> 0.20 s, 3 -> 0.30 s.
#            If one station (net.sta.loc) has two picks of the same type for one event (e.g. P on
#            EHZ and on HNZ), only the best one is kept (lowest weight code, then high-gain
#            EH/HH/BH/EP/DP/CN before HN/EL, then vertical before horizontal); the other is
#            flagged 'duplicate' in phase_extra.csv.
# Stations : one row per net.sta.loc used in phase.csv, from reference_tables/station_channels.csv
#            (StationXML of inputs/stations.xml), coordinates of the channel with most picks;
#            elevation = SENSOR elevation in m (rule per channel, see 'elev_rule' below: NCEDC
#            StationXML mixes 'Channel/Elevation = sensor' and 'Channel/Elevation = surface').
# Output   : inputs/rtdd_catalog/{station,event,phase,phase_extra}.csv,
#            reference_tables/event_id_map.csv, reference_tables/stats_08.json
# Usage: python -I 08_make_rtdd_inputs.py

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

OUT = os.path.join(C.INP, "rtdd_catalog")
UNC = {0: 0.02, 1: 0.10, 2: 0.20, 3: 0.30}          # shadow2000.pdf Table 9 'subjective error'
GAIN_RANK = {"EH": 0, "HH": 0, "BH": 0, "EP": 0, "DP": 0, "SH": 0, "CN": 1, "HN": 2, "EL": 3}


def iso6(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def write_csv(df, path):
    # rtDD's reader fails on blank lines: write without a trailing empty line
    txt = df.to_csv(index=False, lineterminator="\n")
    with open(path, "w") as f:
        f.write(txt.rstrip("\n") + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    st = {}
    em = pd.read_csv(os.path.join(C.TAB, "event_matching.csv"))
    ev = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv"))
    ev = ev[ev.event_id.isin(em.loc[em.benchmark_event, "event_id"])].copy()
    assert ev.event_id.max() < 2 ** 32 and ev.event_id.min() > 0
    pk = pd.read_csv(os.path.join(C.TAB, "picks_ncss.csv"), keep_default_na=False,
                     dtype={"location": str, "station": str, "network": str, "channel": str,
                            "location_raw": str})
    pk = pk[pk.event_id.isin(ev.event_id)].copy()
    ch = pd.read_csv(os.path.join(C.TAB, "station_channels.csv"), keep_default_na=False,
                     dtype={"location": str, "station": str, "network": str, "channel": str})
    for c in ("latitude", "longitude", "elevation_m", "depth_m"):
        ch[c] = pd.to_numeric(ch[c])
    # ---------- stations: coordinates per net.sta.loc
    # Sensor elevation. NCEDC StationXML mixes two conventions (checked 2026-10-17):
    #  (a) Channel/Elevation already = sensor elevation (= station elevation - depth): BK boreholes
    #      and vaults like HAST, BP, NC.CYD1, WR  -> use Channel/Elevation
    #  (b) Channel/Elevation = station (surface) elevation, Depth = borehole depth: PB boreholes,
    #      NC.CCH1 -> use Channel/Elevation - Depth
    #  (c) Channel/Elevation = station elevation and Depth = overburden of a BK tunnel vault
    #      (BDM, BKS, KCC, ...; 6-87 m) -> use Channel/Elevation (the sensor is not that far below
    #      the station elevation)
    #  anything else -> Channel/Elevation, flagged 'other'
    se = pd.to_numeric(ch.station_elevation_m)
    rule, elev = [], []
    for ce, d, s_e, net in zip(ch.elevation_m, ch.depth_m, se, ch.network):
        if d <= 0.5:
            rule.append("depth~0"), elev.append(ce)
        elif abs(ce - (s_e - d)) <= 1.0:
            rule.append("a: channel elev is sensor elev"), elev.append(ce)
        elif abs(ce - s_e) <= 1.0 and net != "BK":
            rule.append("b: channel elev is surface, minus depth"), elev.append(ce - d)
        elif abs(ce - s_e) <= 1.0 and net == "BK":
            rule.append("c: BK vault overburden, channel elev"), elev.append(ce)
        else:
            rule.append("other: channel elev"), elev.append(ce)
    ch["sensor_elev_m"] = elev
    ch["elev_rule"] = rule
    ch["n_picks"] = pd.to_numeric(ch.n_picks)
    nsl = ["network", "station", "location"]
    spread = ch.groupby(nsl).agg(lat_span=("latitude", lambda x: x.max() - x.min()),
                                 lon_span=("longitude", lambda x: x.max() - x.min()),
                                 elev_span=("sensor_elev_m", lambda x: x.max() - x.min()),
                                 n_epochs=("channel", "size")).reset_index()
    # epoch that covers the middle of the channel's picks (or of the swarm for unpicked channels)
    t_start = pd.to_datetime(ch.start.str.replace("Z", ""), errors="coerce")
    t_end = pd.to_datetime(ch.end.replace({"None": "2100-01-01T00:00:00"}).str.replace("Z", ""),
                           errors="coerce")
    first = pd.to_datetime(ch["first"].str.rstrip("Z"), errors="coerce")
    last = pd.to_datetime(ch["last"].str.rstrip("Z"), errors="coerce")
    mid = (first + (last - first) / 2).fillna(pd.Timestamp("2015-10-20"))
    ch["covers_picks"] = (t_start <= mid) & (mid <= t_end)
    best = ch.sort_values(["covers_picks", "n_picks", "channel"],
                          ascending=[False, False, True]).drop_duplicates(nsl)
    sta = best[nsl + ["latitude", "longitude", "sensor_elev_m", "elev_rule", "elevation_m",
                      "station_elevation_m", "depth_m", "channel"]].merge(spread, on=nsl)
    st["nsl_with_coordinate_spread_gt_10m"] = [
        dict(nsl=f"{r.network}.{r.station}.{r.location}", lat_span_deg=r.lat_span,
             lon_span_deg=r.lon_span, elev_span_m=r.elev_span)
        for r in sta.itertuples()
        if r.lat_span > 1e-4 or r.lon_span > 1e-4 or r.elev_span > 10]
    # ---------- picks -> phase.csv
    pk["weight_code"] = pd.to_numeric(pk.weight_code)
    have_meta = set(zip(ch.network, ch.station, ch.location, ch.channel))
    pk["has_metadata"] = [(r.network, r.station, r.location, r.channel) in have_meta
                          for r in pk.itertuples()]
    pk["reason"] = ""
    pk.loc[pk.weight_code == 4, "reason"] = "weight code 4 (no weight in NCSS)"
    pk.loc[pk.weight_code >= 5, "reason"] = "weight code 5-9 (out-weighted by NCSS)"
    pk.loc[~pk.has_metadata & (pk.reason == ""), "reason"] = "no station metadata"
    cand = pk[pk.reason == ""].copy()
    cand["gain_rank"] = cand.channel.str[:2].map(GAIN_RANK).fillna(4)
    cand["horiz"] = (cand.channel.str[-1] != "Z").astype(int)
    cand = cand.sort_values(["event_id", "network", "station", "location", "phase", "weight_code",
                             "gain_rank", "horiz", "channel"])
    dup = cand.duplicated(["event_id", "network", "station", "location", "phase"], keep="first")
    pk.loc[cand.index[dup], "reason"] = "duplicate (same event, station, phase; worse pick)"
    keep = pk[pk.reason == ""].copy()
    keep["unc"] = keep.weight_code.map(UNC)
    phase = pd.DataFrame(dict(
        eventId=keep.event_id, isotime=keep.time_utc.map(lambda s: iso6(s.rstrip("Z"))),
        lowerUncertainty=keep.unc.map(lambda x: f"{x:.3f}"),
        upperUncertainty=keep.unc.map(lambda x: f"{x:.3f}"),
        type=keep.phase, networkCode=keep.network, stationCode=keep.station,
        locationCode=keep.location, channelCode=keep.channel))
    phase = phase.sort_values(["eventId", "isotime"])
    write_csv(phase, os.path.join(OUT, "phase.csv"))
    extra = pk[["event_id", "phase", "time_utc", "network", "station", "location", "location_raw",
                "channel", "onset", "remark", "first_motion", "weight_code", "weight_used",
                "residual_s", "epi_dist_km", "azimuth_deg", "takeoff_deg", "data_source",
                "has_metadata", "reason"]].copy()
    extra["in_phase_csv"] = extra.reason == ""
    extra["uncertainty_s"] = extra.weight_code.map(UNC)
    # QC flags (information only; these picks are NOT removed from phase.csv):
    #  flag_large_residual: |NCSS travel-time residual| > 1.0 s (NCSS gave most of them weight 0)
    #  flag_s_not_after_p : S time <= P time at the same net.sta.loc for the same event
    res = pd.to_numeric(extra.residual_s, errors="coerce")
    extra["flag_large_residual"] = res.abs() > 1.0
    t = pd.to_datetime(extra.time_utc.str.rstrip("Z"))
    tp = t[extra.phase == "P"].groupby([extra.event_id, extra.network, extra.station,
                                        extra.location]).min()
    keyS = list(zip(extra.event_id, extra.network, extra.station, extra.location))
    extra["flag_s_not_after_p"] = [(ph_ == "S") and (k in tp.index) and (tt <= tp[k])
                                   for ph_, k, tt in zip(extra.phase, keyS, t)]
    st["flagged_in_phase_csv"] = dict(
        large_residual=int((extra.flag_large_residual & extra.in_phase_csv).sum()),
        s_not_after_p=int((extra.flag_s_not_after_p & extra.in_phase_csv).sum()))
    extra.sort_values(["event_id", "time_utc"]).to_csv(os.path.join(OUT, "phase_extra.csv"),
                                                       index=False)
    # ---------- stations used
    used = keep[nsl].drop_duplicates()
    s_used = sta.merge(used, on=nsl)
    station = pd.DataFrame(dict(latitude=s_used.latitude.map(lambda x: f"{x:.6f}"),
                                longitude=s_used.longitude.map(lambda x: f"{x:.6f}"),
                                elevation=s_used.sensor_elev_m.map(lambda x: f"{x:.1f}"),
                                networkCode=s_used.network, stationCode=s_used.station,
                                locationCode=s_used.location))
    station = station.sort_values(["networkCode", "stationCode", "locationCode"])
    write_csv(station, os.path.join(OUT, "station.csv"))
    s_used.to_csv(os.path.join(C.TAB, "rtdd_stations_detail.csv"), index=False)
    # ---------- events
    ev = ev.sort_values("origin_time_utc")
    event = pd.DataFrame(dict(
        id=ev.event_id, isotime=ev.origin_time_utc.map(lambda s: iso6(s.rstrip("Z"))),
        latitude=ev.latitude.map(lambda x: f"{x:.6f}"),
        longitude=ev.longitude.map(lambda x: f"{x:.6f}"),
        depth=ev.depth_geoid_km.map(lambda x: f"{x:.3f}"),
        magnitude=[("" if (pd.isna(m) or (m == 0 and t == "N")) else f"{m:.2f}")
                   for m, t in zip(ev.pref_mag, ev.pref_mag_type)]))
    write_csv(event, os.path.join(OUT, "event.csv"))
    # ---------- id map
    idm = em[em.benchmark_event].merge(ev[["event_id", "origin_time_utc", "pref_mag"]],
                                      on="event_id", how="left")
    idm.insert(1, "rtdd_id", idm.event_id)
    idm = idm.rename(columns={"event_id": "ncss_event_id"})
    idm["n_P_in_phase_csv"] = idm.ncss_event_id.map(keep[keep.phase == "P"].groupby("event_id").size()).fillna(0).astype(int)
    idm["n_S_in_phase_csv"] = idm.ncss_event_id.map(keep[keep.phase == "S"].groupby("event_id").size()).fillna(0).astype(int)
    idm.to_csv(os.path.join(C.TAB, "event_id_map.csv"), index=False)
    # ---------- checks + stats
    assert set(phase.eventId) <= set(event.id)
    sid = set(zip(station.networkCode, station.stationCode, station.locationCode))
    assert all((n, s, l) in sid for n, s, l in zip(phase.networkCode, phase.stationCode,
                                                     phase.locationCode))
    st.update(dict(
        n_events=int(len(event)), n_events_without_magnitude=int((event.magnitude == "").sum()),
        n_phase_rows=int(len(phase)), n_P=int((phase.type == "P").sum()),
        n_S=int((phase.type == "S").sum()), n_stations=int(len(station)),
        excluded=pk.reason.replace("", "kept").value_counts().to_dict(),
        events_with_lt4_P=int((idm.n_P_in_phase_csv < 4).sum()),
        events_without_phases=idm.loc[(idm.n_P_in_phase_csv + idm.n_S_in_phase_csv) == 0,
                                      "ncss_event_id"].tolist(),
        uncertainty_counts=phase.lowerUncertainty.value_counts().to_dict(),
        max_event_id=int(event.id.max()), uint32_max=2 ** 32 - 1,
        station_elevation_m=dict(min=float(s_used.sensor_elev_m.min()),
                                 max=float(s_used.sensor_elev_m.max())),
        elevation_rules=s_used.elev_rule.value_counts().to_dict(),
        stations_with_nonzero_depth=[f"{r.network}.{r.station}.{r.location}: station elev "
                                     f"{r.station_elevation_m} m, channel elev {r.elevation_m} m, "
                                     f"depth {r.depth_m} m -> sensor {r.sensor_elev_m:.1f} m "
                                     f"({r.elev_rule})"
                                     for r in s_used.itertuples() if r.depth_m > 0.5]))
    with open(os.path.join(C.TAB, "stats_08.json"), "w") as f:
        json.dump(st, f, indent=1, default=str)
    print(json.dumps(st, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
