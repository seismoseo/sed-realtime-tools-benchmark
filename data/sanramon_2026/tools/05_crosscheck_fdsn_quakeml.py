# 05_crosscheck_fdsn_quakeml.py -- independent check of the Hypoinverse-archive pick parser:
# download the QuakeML of a few events from the NCEDC FDSN event service and compare every pick
# (network, station, location, channel, phase, time) with reference_tables/picks_ncss.csv.
#
# (2025-26 case; copied from the 2015 tool.) Events (EVENTS below, chosen as in 2015 plus one):
#   75305736 the mainshock (sr_common.MAINSHOCK_ID, Mw 4.18); 75261171 (Md 2.91, the benchmark event
#   with most S picks, 45); 75303161 (Md 1.63, review flag 'A': automatic solution, real-time picks
#   only - a class that did not exist in 2015); 75305951 (Mh 1.60, review flag 'I', no NCEDC DD
#   solution, 9 picks).
# Service: https://service.ncedc.org/fdsnws/event/1/query?eventid=<id>&includearrivals=true
# Output: reference/fdsn_event/<id>.xml (raw QuakeML), reference_tables/fdsn_pick_crosscheck.csv
#         (one row per pick from either source), printed summary.
# Usage: python -I 05_crosscheck_fdsn_quakeml.py [event ids ...]

import os
import sys

import pandas as pd
from obspy import read_events

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

TOOL = "05_crosscheck_fdsn_quakeml"
EVENTS = [C.MAINSHOCK_ID, 75261171, 75303161, 75305951]
OUT = os.path.join(C.REF, "fdsn_event")


def quakeml_picks(path):
    cat = read_events(path, format="QUAKEML")
    assert len(cat) == 1
    ev = cat[0]
    org = ev.preferred_origin() or ev.origins[0]
    arr_by_pick = {str(a.pick_id): a for a in org.arrivals}
    rows = []
    for p in ev.picks:
        a = arr_by_pick.get(str(p.resource_id))
        w = p.waveform_id
        rows.append(dict(network=w.network_code, station=w.station_code,
                         location=(w.location_code or "").replace("--", ""),
                         channel=w.channel_code,
                         phase=(a.phase if a is not None and a.phase else p.phase_hint) or "",
                         time=pd.Timestamp(p.time.datetime),
                         q_onset=str(p.onset or ""), q_polarity=str(p.polarity or ""),
                         q_mode=str(p.evaluation_mode or ""),
                         q_time_weight=(a.time_weight if a is not None else None),
                         q_has_arrival=a is not None))
    info = dict(origin_time=str(org.time), lat=org.latitude, lon=org.longitude,
                depth_m=org.depth, n_picks=len(ev.picks), n_arrivals=len(org.arrivals),
                mag=str([(m.mag, m.magnitude_type) for m in ev.magnitudes]))
    return pd.DataFrame(rows), info


def main():
    ids = [int(x) for x in sys.argv[1:]] or EVENTS
    os.makedirs(OUT, exist_ok=True)
    ours = pd.read_csv(os.path.join(C.TAB, "picks_ncss.csv"), keep_default_na=False,
                       dtype={"location": str, "location_raw": str})
    ours["time"] = pd.to_datetime(ours["time_utc"].str.rstrip("Z"))
    allrows = []
    for eid in ids:
        path = os.path.join(OUT, f"{eid}.xml")
        if not os.path.exists(path):
            r = C.polite_request("https://service.ncedc.org/fdsnws/event/1/query", TOOL,
                                 params=dict(eventid=eid, includearrivals="true"), out_file=path,
                                 timeout=120)
            if r is None or r.status_code != 200:
                print(f"{eid}: download failed ({None if r is None else r.status_code})")
                continue
        q_all, info = quakeml_picks(path)
        q_all["phase1"] = q_all["phase"].str[:1]
        # picks that are not arrivals of the preferred origin: in the archive these are the
        # amplitude-only lines (placeholder 'P' time = origin time) that tool 04 leaves out
        noarr = q_all[~q_all.q_has_arrival]
        t_org = pd.Timestamp(info["origin_time"].rstrip("Z"))
        n_at_origin = int(((noarr.time - t_org).dt.total_seconds().abs() < 0.006).sum())
        if len(noarr):
            print(f"   [{eid}] QuakeML picks without an arrival: {len(noarr)}, of which "
                  f"{n_at_origin} have time = origin time; channels "
                  f"{sorted(set(noarr.channel.str[:2]))}")
        q = q_all[q_all.q_has_arrival].copy()
        o = ours[ours.event_id == eid].copy()
        key = ["network", "station", "location", "channel", "phase1"]
        o["phase1"] = o["phase"]
        m = o.merge(q, on=key, how="outer", suffixes=("_arc", "_qml"), indicator=True)
        m["dt_s"] = (m["time_arc"] - m["time_qml"]).dt.total_seconds()
        m["event_id"] = eid
        both = m[m._merge == "both"]
        n_dup = int(q.duplicated(key).sum())
        print(f"== {eid}: QuakeML {info['n_picks']} picks / {info['n_arrivals']} arrivals (compared: "
              f"picks that are arrivals of the preferred origin), "
              f"origin {info['origin_time']} {info['lat']:.5f} {info['lon']:.5f} "
              f"{info['depth_m']} m, mags {info['mag']}")
        print(f"   archive picks {len(o)} (P {int((o.phase=='P').sum())}, S {int((o.phase=='S').sum())}); "
              f"QuakeML P {int((q.phase1=='P').sum())}, S {int((q.phase1=='S').sum())}; "
              f"matched {len(both)}, only archive {int((m._merge=='left_only').sum())}, "
              f"only QuakeML {int((m._merge=='right_only').sum())}, duplicate keys in QuakeML {n_dup}")
        if len(both):
            print(f"   |dt| max {both.dt_s.abs().max():.4f} s, picks with |dt|>0.01 s: "
                  f"{int((both.dt_s.abs() > 0.0100001).sum())}; |dt| value counts (ms): "
                  f"{(both.dt_s * 1000).round(1).value_counts().to_dict()}; QuakeML phase "
                  f"names: {sorted(set(q.phase))}; QuakeML time decimals seen: "
                  f"{sorted(set(q.time.dt.microsecond % 10000 != 0))}")
        for _, r in m[m._merge != "both"].iterrows():
            print(f"   unmatched ({r._merge}): {r.network}.{r.station}.{r.location}.{r.channel} {r.phase1}")
        allrows.append(m)
    if allrows:
        out = pd.concat(allrows)
        out["_merge"] = out["_merge"].astype(str)
        cols = ["event_id", "network", "station", "location", "channel", "phase1", "phase_arc",
                "phase_qml", "time_arc", "time_qml", "dt_s", "weight_code", "onset", "q_onset",
                "first_motion", "q_polarity", "q_mode", "q_time_weight", "_merge"]
        out[cols].to_csv(os.path.join(C.TAB, "fdsn_pick_crosscheck.csv"), index=False)


if __name__ == "__main__":
    main()
