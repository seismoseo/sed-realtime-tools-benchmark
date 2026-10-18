# 06_download_stationxml.py -- (2025-26 case; copied from the 2015 tool, period from sr_common.py)
# StationXML (level=response) for every channel that carries an NCSS
# pick in a benchmark event, plus the other components of the same sensor (e.g. HHN/HHE with HHZ).
#
# Steps
#   1. sensor groups = (net, sta, loc, first two channel letters) of all picks of benchmark events
#      (reference_tables/picks_ncss.csv, column benchmark_event); query pattern "HH?" etc.
#   2. level=channel bulk POST to NCEDC (https://service.ncedc.org/fdsnws/station/1/query) for all
#      groups, epochs overlapping the benchmark period (sr_common.T0_STR..T1_STR, 2025-10-01..
#      2026-10-18); groups NCEDC does not answer are asked
#      from EarthScope (https://service.earthscope.org/fdsnws/station/1/query).
#   3. level=response bulk POST (chunks of <= 120 channels) for every channel found in step 2, to the
#      service that answered in step 2.
#   4. merge -> inputs/stations.xml; per-channel table -> reference_tables/station_channels.csv;
#      report of picked channels without metadata and vertical-only sensors -> stats_06.json
# Raw answers: reference/stationxml/raw/<service>_<level>_<k>.xml (re-run safe: existing files are
# reused, not downloaded again). Every request is logged in logs/sanramon2026_requests.tsv.
# Usage: python -I 06_download_stationxml.py   (long: run in the background; writes
#        reference/stationxml/DONE when finished)

import json
import os
import sys

import pandas as pd
from obspy import Inventory, UTCDateTime, read_inventory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

TOOL = "06_download_stationxml"
SERVICES = {"ncedc": "https://service.ncedc.org/fdsnws/station/1/query",
            "earthscope": "https://service.earthscope.org/fdsnws/station/1/query"}
T0, T1 = C.T0_STR, C.T1_STR
RAW = os.path.join(C.REF, "stationxml", "raw")
CHUNK_CHANNEL = 40     # sensor groups per channel-level request (one 450-line request timed out: HTTP 504)
CHUNK_RESPONSE = 40    # channels per response-level request
DONE = os.path.join(C.REF, "stationxml", "DONE")


def loc_q(loc):
    return loc if loc else "--"


def post(service, level, lines, tag):
    """bulk POST; returns Inventory or None (204/404 = no data)."""
    path = os.path.join(RAW, f"{service}_{level}_{tag}.xml")
    nodata = path + ".nodata"
    if os.path.exists(path):
        return read_inventory(path, format="STATIONXML")
    if os.path.exists(nodata):
        return None
    body = f"level={level}\nformat=xml\n" + "\n".join(lines) + "\n"
    r = C.polite_request(SERVICES[service], TOOL, method="POST", data=body.encode(),
                         out_file=path, timeout=600, headers={"Content-Type": "text/plain"})
    if r is None:
        raise RuntimeError(f"no answer from {service} ({tag})")
    if r.status_code in (204, 404):
        with open(nodata, "w") as f:
            f.write(f"HTTP {r.status_code}\n" + body)
        return None
    if r.status_code != 200:
        raise RuntimeError(f"{service} {tag}: HTTP {r.status_code}: {r.text[:300]}")
    with open(path + ".request.txt", "w") as f:
        f.write(body)
    return read_inventory(path, format="STATIONXML")


def channel_rows(inv, service):
    rows = []
    for net in inv:
        for sta in net:
            for ch in sta:
                rows.append(dict(
                    network=net.code, station=sta.code, location=ch.location_code,
                    channel=ch.code, start=str(ch.start_date), end=str(ch.end_date),
                    latitude=ch.latitude, longitude=ch.longitude, elevation_m=ch.elevation,
                    depth_m=ch.depth, azimuth=ch.azimuth, dip=ch.dip,
                    sample_rate=ch.sample_rate,
                    sensor=(ch.sensor.description if ch.sensor and ch.sensor.description else ""),
                    station_elevation_m=sta.elevation, service=service))
    return rows


def main():
    os.makedirs(RAW, exist_ok=True)
    pk = pd.read_csv(os.path.join(C.TAB, "picks_ncss.csv"), keep_default_na=False,
                     dtype={"location": str, "station": str, "network": str, "channel": str})
    pk = pk[pk.benchmark_event.astype(str) == "True"]
    picked = pk.groupby(["network", "station", "location", "channel"]).agg(
        n_picks=("phase", "size"), first=("time_utc", "min"), last=("time_utc", "max")).reset_index()
    picked["group"] = picked.channel.str[:2]
    groups = picked[["network", "station", "location", "group"]].drop_duplicates()
    lines = [f"{g.network} {g.station} {loc_q(g.location)} {g.group}? {T0} {T1}"
             for g in groups.itertuples()]
    print(f"picked channels {len(picked)}, sensor groups {len(groups)}")

    # ---- step 2: channel level, NCEDC first
    rows = []
    for k in range(0, len(lines), CHUNK_CHANNEL):
        inv = post("ncedc", "channel", lines[k:k + CHUNK_CHANNEL], f"groups{k // CHUNK_CHANNEL:02d}")
        print(f"  channel chunk {k // CHUNK_CHANNEL:02d} done", flush=True)
        if inv is not None:
            rows += channel_rows(inv, "ncedc")
    ch = pd.DataFrame(rows)
    have = set(zip(ch.network, ch.station, ch.location, ch.channel.str[:2])) if len(ch) else set()
    missing = [g for g in groups.itertuples()
               if (g.network, g.station, g.location, g.group) not in have]
    print(f"NCEDC answered {len(have)} of {len(groups)} groups; asking EarthScope for {len(missing)}")
    if missing:
        ml = [f"{g.network} {g.station} {loc_q(g.location)} {g.group}? {T0} {T1}" for g in missing]
        inv = post("earthscope", "channel", ml, "groups_missing_at_ncedc")
        if inv is not None:
            ch = pd.concat([ch, pd.DataFrame(channel_rows(inv, "earthscope"))], ignore_index=True)
    # ---- step 3: response level for all channels found, per service
    full = Inventory(networks=[], source="NCEDC + EarthScope FDSN station services")
    resp_rows = []
    for service in ("ncedc", "earthscope"):
        sub = ch[ch.service == service][["network", "station", "location", "channel"]]
        sub = sub.drop_duplicates()
        rl = [f"{r.network} {r.station} {loc_q(r.location)} {r.channel} {T0} {T1}"
              for r in sub.itertuples()]
        for k in range(0, len(rl), CHUNK_RESPONSE):
            inv = post(service, "response", rl[k:k + CHUNK_RESPONSE], f"chunk{k // CHUNK_RESPONSE:02d}")
            print(f"  {service} response chunk {k // CHUNK_RESPONSE:02d} done", flush=True)
            if inv is not None:
                full += inv
                resp_rows += channel_rows(inv, service)
    full.source = "NCEDC + EarthScope FDSN station services (merged by 06_download_stationxml.py)"
    out_xml = os.path.join(C.INP, "stations.xml")
    os.makedirs(C.INP, exist_ok=True)
    full.write(out_xml, format="STATIONXML", validate=True)
    rc = pd.DataFrame(resp_rows)
    # one row per channel epoch with response, mark picked channels
    key = ["network", "station", "location", "channel"]
    rc = rc.merge(picked[key + ["n_picks", "first", "last"]], on=key, how="left")
    rc["picked"] = rc.n_picks.notna()
    rc["n_picks"] = rc.n_picks.fillna(0).astype(int)
    rc.to_csv(os.path.join(C.TAB, "station_channels.csv"), index=False)

    # ---- step 4: reports
    found = set(zip(rc.network, rc.station, rc.location, rc.channel))
    no_meta = picked[[(r.network, r.station, r.location, r.channel) not in found
                      for r in picked.itertuples()]]
    # epochs covering each picked channel's pick span
    multi = []
    for (n, s, l, c), g in rc.groupby(key):
        if len(g) > 1:
            multi.append(dict(nslc=f"{n}.{s}.{l}.{c}", epochs=len(g),
                              lat_span=float(g.latitude.max() - g.latitude.min()),
                              elev_span=float(g.elevation_m.max() - g.elevation_m.min()),
                              starts=list(g.start)))
    sensors = rc.assign(group=rc.channel.str[:2]).groupby(
        ["network", "station", "location", "group"]).channel.apply(lambda x: sorted(set(x)))
    vert_only = [f"{n}.{s}.{l}.{g}?" for (n, s, l, g), chans in sensors.items()
                 if all(c[-1] == "Z" for c in chans)]
    st = dict(picked_channels=int(len(picked)), sensor_groups=int(len(groups)),
              channel_epochs_with_response=int(len(rc)),
              unique_channels_with_response=int(len(found)),
              by_service=rc.service.value_counts().to_dict(),
              picked_channels_without_metadata=[f"{r.network}.{r.station}.{r.location}.{r.channel}"
                                                f" ({r.n_picks} picks)" for r in no_meta.itertuples()],
              n_picks_without_metadata=int(no_meta.n_picks.sum()),
              channels_with_several_epochs_in_window=multi,
              vertical_only_sensor_groups=vert_only, n_vertical_only=len(vert_only),
              n_sensor_groups_with_response=int(len(sensors)))
    with open(os.path.join(C.TAB, "stats_06.json"), "w") as f:
        json.dump(st, f, indent=1)
    print(json.dumps({k: v for k, v in st.items() if k != "vertical_only_sensor_groups"},
                     indent=1)[:5000])
    print("vertical-only sensor groups:", len(vert_only))
    with open(DONE, "w") as f:
        f.write("finished\n")


if __name__ == "__main__":
    main()
