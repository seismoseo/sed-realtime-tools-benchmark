#!/usr/bin/env python
# make_stations_xml.py
#
# Writes data/gwangyang_11ev/inputs/stations.xml = the subset of
# reference/inventory/merged_inventory.xml that covers exactly the network/station/location/channel
# codes of the reference SAC files, keeping every channel epoch that overlaps 2021-07-01 .. 2026-03-01.
# Nothing is invented or edited: epochs, coordinates, orientations and responses are copied as they are.
# Channels that the merged inventory does not have are only LISTED (checks/channels_without_metadata.csv).
#
# Also checks, for every SAC channel: is there exactly one epoch covering each event window, are azimuth,
# dip and sample rate present, does the sample rate match the SAC data, do location codes match, and
# how do the inventory station coordinates compare with the station table used by the reference run.
#
# Run with the pyrtdd environment (after make_waveform_archive.py, which writes the SAC manifest):
#     /home/msseo/miniforge3/envs/pyrtdd/bin/python make_stations_xml.py

import copy
import os
import sys

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read_inventory
from obspy.geodetics import gps2dist_azimuth

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
INV_IN = f"{DATA}/reference/inventory/merged_inventory.xml"
STATION_TABLE = f"{DATA}/reference/gwangyang_pnplus/station_table/used_stations_100km.csv"
MANIFEST = f"{DATA}/inputs/checks/waveform_manifest.csv"          # written by make_waveform_archive.py
PHASE_EXTRA = f"{DATA}/inputs/rtdd_catalog/phase_extra.csv"        # written by make_rtdd_catalog.py
INV_OUT = f"{DATA}/inputs/stations.xml"
CHECKS = f"{DATA}/inputs/checks"
T0, T1 = UTCDateTime("2021-07-01T00:00:00"), UTCDateTime("2026-03-01T00:00:00")


def overlaps(ch, a, b):
    return ch.start_date < b and (ch.end_date is None or ch.end_date > a)


def covers(ch, a, b):
    return ch.start_date <= a and (ch.end_date is None or ch.end_date >= b)


def period_gaps(epochs, a, b):
    # parts of [a, b] not covered by any epoch (list of (start, end) strings)
    iv = sorted((max(e.start_date, a), min(e.end_date or b, b)) for e in epochs)
    gaps, t = [], a
    for s, e in iv:
        if s > t:
            gaps.append((t, s))
        t = max(t, e)
    if t < b:
        gaps.append((t, b))
    return gaps


def main():
    os.makedirs(CHECKS, exist_ok=True)
    inv = read_inventory(INV_IN)
    man = pd.read_csv(MANIFEST, dtype={"kma_id": str, "loc": str}, keep_default_na=False)
    man["t0"] = man.starttime.map(UTCDateTime)
    man["t1"] = man.endtime.map(UTCDateTime)
    sac_nslc = sorted(set(zip(man.net, man.sta, man["loc"], man.cha)))
    print(f"[sac] {len(sac_nslc)} distinct NET.STA.LOC.CHA in {len(man)} SAC files; "
          f"location codes: {sorted(set(man['loc']))}")

    # --- the subset ------------------------------------------------------------------------
    sub = copy.deepcopy(inv)
    keep = set(sac_nslc)
    for net in sub.networks:
        for sta in net.stations:
            sta.channels = [ch for ch in sta.channels
                            if (net.code, sta.code, ch.location_code, ch.code) in keep and overlaps(ch, T0, T1)]
        net.stations = [s for s in net.stations if s.channels]
    sub.networks = [n for n in sub.networks if n.stations]
    sub.source = (f"{inv.source} | subset for the Gwangyang 11-event benchmark: SAC channels only, "
                  f"epochs overlapping {T0.date}..{T1.date} (make_stations_xml.py)")
    sub.write(INV_OUT, format="STATIONXML", validate=True)
    back = read_inventory(INV_OUT)
    n_ep = sum(len(s.channels) for n in back for s in n)
    print(f"[write] {INV_OUT}: {sum(len(n.stations) for n in back)} stations, {n_ep} channel epochs "
          f"(schema-validated on write, re-read OK)")

    # --- per-channel checks ------------------------------------------------------------------
    st_tab = pd.read_csv(STATION_TABLE).set_index("Code")
    rows, missing = [], []
    for nslc in sac_nslc:
        net, sta, loc, cha = nslc
        eps = [ch for n in back if n.code == net for s in n if s.code == sta for ch in s
               if ch.location_code == loc and ch.code == cha]
        any_code = [ch for n in inv if n.code == net for s in n if s.code == sta for ch in s if ch.code == cha]
        files = man[(man.net == net) & (man.sta == sta) & (man["loc"] == loc) & (man.cha == cha)]
        cov = [sum(covers(ch, r.t0, r.t1) for ch in eps) for r in files.itertuples()]
        unc = [r.kma_id for r, c in zip(files.itertuples(), cov) if c == 0]
        mul = [r.kma_id for r, c in zip(files.itertuples(), cov) if c > 1]
        gaps = period_gaps(eps, T0, T1) if eps else [(T0, T1)]
        ovl = [(a.start_date, b.start_date) for i, a in enumerate(sorted(eps, key=lambda c: c.start_date))
               for b in sorted(eps, key=lambda c: c.start_date)[i + 1:] if b.start_date < (a.end_date or UTCDateTime(2100, 1, 1))]
        sens = [ch.response.instrument_sensitivity for ch in eps if ch.response is not None]
        rows.append(dict(
            net=net, sta=sta, loc=loc, cha=cha, n_sac_files=len(files), n_epochs_in_subset=len(eps),
            events_without_epoch=" ".join(unc), events_with_several_epochs=" ".join(mul),
            gaps_in_2021_07_to_2026_03=" ".join(f"{a.date}..{b.date}" for a, b in gaps),
            overlapping_epochs=len(ovl),
            azimuths=" ".join(sorted({f"{ch.azimuth:g}" for ch in eps if ch.azimuth is not None})),
            dips=" ".join(sorted({f"{ch.dip:g}" for ch in eps if ch.dip is not None})),
            sample_rates=" ".join(sorted({f"{ch.sample_rate:g}" for ch in eps if ch.sample_rate is not None})),
            all_have_az_dip_sr=all(ch.azimuth is not None and ch.dip is not None and ch.sample_rate is not None for ch in eps) if eps else False,
            sample_rate_matches_sac=all(abs((ch.sample_rate or 0) - files.sampling_rate.iloc[0]) < 1e-9 for ch in eps) if eps else False,
            depths_m=" ".join(sorted({f"{ch.depth:g}" for ch in eps if ch.depth is not None})),
            sensor_models=" | ".join(sorted({str(ch.sensor.model) for ch in eps if ch.sensor is not None})),
            sensitivities=" ".join(f"{x.value:.6g}" for x in sens if x is not None),
            input_units=" ".join(sorted({str(x.input_units) for x in sens if x is not None})),
            orientation_comment=any("orientation: use registry" in (c.value or "") for ch in eps for c in ch.comments),
            same_code_epochs_in_full_inventory=len(any_code)))
        if unc or not eps:
            reason = "channel code absent from merged_inventory.xml" if not any_code else (
                "no epoch overlapping 2021-07..2026-03" if not eps else "epochs do not cover some event windows")
            inv_sensors = sorted({ch.code[:2] for n in inv if n.code == net for s in n if s.code == sta for ch in s})
            missing.append(dict(net=net, sta=sta, loc=loc, cha=cha, reason=reason,
                                events_affected=" ".join(unc if eps else list(files.kma_id)),
                                n_events_affected=len(unc if eps else files),
                                sensors_of_this_station_in_merged_inventory=" ".join(inv_sensors) or "(station absent)"))
    chk = pd.DataFrame(rows)
    chk.to_csv(f"{CHECKS}/inventory_channel_check.csv", index=False)
    mis = pd.DataFrame(missing, columns=["net", "sta", "loc", "cha", "reason", "events_affected", "n_events_affected",
                                         "sensors_of_this_station_in_merged_inventory"])
    # how many catalog picks sit on these stations
    if os.path.exists(PHASE_EXTRA):
        pe = pd.read_csv(PHASE_EXTRA, dtype={"kmaId": str})
        npk = pe.groupby("stationCode").size()
        mis["n_catalog_picks_at_station"] = mis.sta.map(npk).fillna(0).astype(int)
    mis.to_csv(f"{CHECKS}/channels_without_metadata.csv", index=False)

    ok = chk[chk.n_epochs_in_subset > 0]
    print(f"[check] SAC channels with metadata: {len(ok)}/{len(chk)}; without: {len(mis)} "
          f"({', '.join(sorted(set(mis.sta + '.' + mis.cha.str[:2])))})")
    print(f"[check] channels with metadata whose epochs miss an event window: "
          f"{int((ok.events_without_epoch != '').sum())}; with several covering epochs: "
          f"{int((ok.events_with_several_epochs != '').sum())}; overlapping epochs: {int(ok.overlapping_epochs.sum())}")
    print(f"[check] all epochs have azimuth/dip/sample rate: {bool(ok.all_have_az_dip_sr.all())}; "
          f"sample rate == SAC (100 Hz): {bool(ok.sample_rate_matches_sac.all())}; "
          f"azimuth values seen: {sorted(set(' '.join(ok.azimuths).split()))}; dips: {sorted(set(' '.join(ok.dips).split()))}")
    gp = ok[ok.gaps_in_2021_07_to_2026_03 != ""]
    print(f"[check] channels whose kept epochs leave gaps inside 2021-07-01..2026-03-01: {len(gp)}")
    for r in gp.itertuples():
        print(f"         {r.net}.{r.sta}.{r.loc}.{r.cha}: {r.gaps_in_2021_07_to_2026_03}")
    print(f"[check] epochs carrying 'orientation: use registry/orientation.py, not this file': "
          f"{int(ok.orientation_comment.sum())}/{len(ok)} channels")
    inv_locs = sorted({ch.location_code for n in back for s in n for ch in s})
    print(f"[check] location codes in stations.xml: {inv_locs}; in SAC: {sorted(set(man['loc']))} -> "
          f"{'match' if inv_locs == sorted(set(man['loc'])) else 'DIFFER'}")

    # --- station-level table: sensors and coordinates ---------------------------------------
    srows = []
    sac_sensor = man.groupby("sta").sensor.unique()
    for sta, sensors in sac_sensor.items():
        full = [s for n in inv for s in n if s.code == sta]
        inv_sens = sorted({ch.code[:2] for s in full for ch in s})
        r = dict(station=sta, sensor_in_sac=" ".join(sensors), n_sensors_in_sac=len(sensors),
                 sensor_in_table=st_tab.loc[sta, "Sensor"], sensors_in_merged_inventory=" ".join(inv_sens) or "(absent)",
                 sac_sensor_in_inventory=all(x in inv_sens for x in sensors),
                 table_lat=st_tab.loc[sta, "Latitude"], table_lon=st_tab.loc[sta, "Longitude"],
                 table_elev_m=st_tab.loc[sta, "Elevation"])
        if full:
            s0 = full[0]
            r.update(inv_lat=s0.latitude, inv_lon=s0.longitude, inv_elev_m=s0.elevation,
                     inv_minus_table_horiz_m=round(gps2dist_azimuth(s0.latitude, s0.longitude, r["table_lat"], r["table_lon"])[0], 1),
                     inv_minus_table_elev_m=round(s0.elevation - r["table_elev_m"], 1))
        srows.append(r)
    stab = pd.DataFrame(srows)
    stab.to_csv(f"{CHECKS}/station_sensor_table.csv", index=False)
    print(f"[stations] sensors in the SAC set: {stab.sensor_in_sac.value_counts().to_dict()}; "
          f"stations with >1 sensor in the SAC set: {int((stab.n_sensors_in_sac > 1).sum())}; "
          f"SAC sensor == station-table sensor: {bool((stab.sensor_in_sac == stab.sensor_in_table).all())}")
    print(f"[stations] SAC sensor missing from merged_inventory: "
          f"{', '.join(f'{r.station}({r.sensor_in_sac}; inventory has {r.sensors_in_merged_inventory})' for r in stab[~stab.sac_sensor_in_inventory].itertuples())}")
    have = stab.dropna(subset=["inv_lat"]) if "inv_lat" in stab else stab.iloc[0:0]
    print(f"[stations] inventory vs station table: horizontal offset max {have.inv_minus_table_horiz_m.max()} m "
          f"(median {have.inv_minus_table_horiz_m.median()}); inventory elevations: "
          f"{sorted(set(have.inv_elev_m))[:5]}{' ...' if len(set(have.inv_elev_m)) > 5 else ''}; "
          f"table elevations {have.table_elev_m.min():.0f}..{have.table_elev_m.max():.0f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
