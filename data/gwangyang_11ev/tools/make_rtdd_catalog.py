#!/usr/bin/env python
# make_rtdd_catalog.py
#
# Builds the rtDD (scrtdd / pyrtdd) multi-event input catalog for the 11-event Gwangyang benchmark
# from the reference HYPOINVERSE + ph2dt + HypoDD run, and cross-checks it against every other copy
# of the same information in the reference tree (KMA catalog, HYPOINVERSE .sum/.phs, ph2dt .pha,
# the three event.dat copies, PhaseNet+ pick tables, SAC pick headers, dt.ct / dt.cc files).
#
# Run with the pyrtdd environment:
#     /home/msseo/miniforge3/envs/pyrtdd/bin/python make_rtdd_catalog.py
# Reads only (never writes) data/gwangyang_11ev/reference/ and data/gwangyang_11ev/reference_supplement/.
# Writes data/gwangyang_11ev/inputs/rtdd_catalog/ and data/gwangyang_11ev/inputs/checks/.
#
# Format: scrtdd doc/base/multievent.rst, "Event Catalog: Plain CSV Files". Parsing rules checked in
# scrtdd v2.0.10 libs/hdd/catalog.cpp, csvreader.cpp and utctime.cpp:
#   * event ids are read with std::stoul into a 32-bit 'unsigned', so a 14-digit KMA id would be
#     silently wrapped modulo 2^32; the catalog therefore uses ids 1..11 (event_id_map.csv);
#   * isotime must match YYYY-MM-DDTHH:MM:SS.<digits>Z (the fraction is mandatory);
#   * no byte-order mark, no blank lines, no spaces around commas; a blank uncertainty becomes NaN;
#   * a phase whose NET.STA.LOC is not in station.csv aborts the whole catalog read;
#   * channelCode: rtDD keeps only its first two letters (band + instrument, e.g. HH) and appends the
#     component it is configured to cross-correlate (libs/hdd/dd.cpp DD::getWaveform), and it skips a
#     pair whose two phases have different first two letters (DD::xcorrPhases).

import csv
import glob
import hashlib
import os
import re
import sys

import numpy as np
import pandas as pd
from obspy import UTCDateTime, read
from obspy.geodetics import gps2dist_azimuth

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
REF = f"{DATA}/reference/gwangyang_pnplus"
SUP = f"{DATA}/reference_supplement"
OUT = f"{DATA}/inputs/rtdd_catalog"
CHECKS = f"{DATA}/inputs/checks"

HYPODD_ID_OFFSET = 200000     # HypoDD id = 200000 + index of the event folder (core/hypoinverse.py:228)
KST_OFFSET_H = 9              # KMA catalog is in KST; event ids are UTC (core/waveforms.py:250-254)
P_COMPONENT = "Z"             # orientation letter written into channelCode for P picks
S_COMPONENT = "N"             # ... for S picks (the reference .phs file attaches every S pick to N)
LOCATION_CODE = ""            # SAC khole is unset in all files -> blank location code
PHA_TRUNC_TOL_MS = 10.0       # .phs pick times are PhaseNet+ times truncated to 0.01 s (hypoinverse.py:216,225)
SAC_TOL_MS = 0.1              # SAC a/t0 headers are float32 copies of the PhaseNet+ times
WEIGHT_TO_CODE = {1.0: 0, 0.5: 1, 0.2: 2, 0.1: 3}   # ncsn2pha: HYPOINVERSE weight code -> ph2dt weight


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def iso(t):
    # rtDD wants a fraction and a trailing Z; obspy keeps nanoseconds, we print microseconds
    return t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_from_cs(year, month, day, hour, minute, centisec):
    # exact integer construction (no float rounding): centisec = seconds * 100
    return UTCDateTime(year, month, day, hour, minute, centisec // 100, (centisec % 100) * 10000)


def horiz_m(lat1, lon1, lat2, lon2):
    return gps2dist_azimuth(lat1, lon1, lat2, lon2)[0]


# ----------------------------------------------------------------------------- readers
def read_event_dat(path):
    # HypoDD event.dat: DATE(yyyymmdd) TIME(hhmmsscc, leading zeros dropped) LAT LON DEP MAG EH EZ RMS ID
    rows = []
    for line in open(path):
        t = line.split()
        if not t:
            continue
        d, hms = t[0], int(t[1])
        hh, mi, cs = hms // 1000000, (hms // 10000) % 100, hms % 10000
        rows.append(dict(hypodd_id=int(t[9]), time_field=t[1],
                         origin=utc_from_cs(int(d[:4]), int(d[4:6]), int(d[6:8]), hh, mi, cs),
                         lat=float(t[2]), lon=float(t[3]), depth=float(t[4]), mag=float(t[5]),
                         eh=float(t[6]), ez=float(t[7]), rms=float(t[8])))
    return pd.DataFrame(rows).set_index("hypodd_id", drop=False)


def read_pha(path):
    # ph2dt phase file: '# yr mo dy hr mi sc lat lon dep mag eh ez rms id' then 'NETSTA tt weight P|S'
    events, phases, cur = [], [], None
    for line in open(path):
        if not line.strip():
            continue
        t = line.split()
        if t[0] == "#":
            cs = int(round(float(t[6]) * 100))
            cur = int(t[14])
            events.append(dict(hypodd_id=cur, sec_field=t[6],
                               origin=utc_from_cs(int(t[1]), int(t[2]), int(t[3]), int(t[4]), int(t[5]), cs),
                               lat=float(t[7]), lon=float(t[8]), depth=float(t[9]), mag=float(t[10]),
                               eh=float(t[11]), ez=float(t[12]), rms=float(t[13])))
        else:
            phases.append(dict(hypodd_id=cur, netsta=t[0], tt_field=t[1],
                               tt_ms=int(round(float(t[1]) * 1000)), weight=float(t[2]), phase=t[3]))
    return pd.DataFrame(events).set_index("hypodd_id", drop=False), pd.DataFrame(phases)


def read_sum(path):
    # HYPOINVERSE H71 summary (comma separated, space padded header)
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    dcol = next(c for c in df.columns if c.startswith("DATE"))
    rows = []
    for _, r in df.iterrows():
        d, hm = str(r[dcol]).strip().split()
        y, mo, dy = (int(x) for x in d.split("/"))
        hh, mi = (int(x) for x in hm.split(":"))
        rows.append(dict(hypodd_id=int(r["ID-NUM"]),
                         origin=utc_from_cs(y, mo, dy, hh, mi, int(round(float(r["SEC"]) * 100))),
                         lat=float(r["LAT"]), lon=float(r["LON"]), depth=float(r["DEPTH"]),
                         num=int(r["NUM"]), gap=int(r["GAP"]), dmin=float(r["DMIN"]), rms=float(r["RMS"]),
                         erh=float(r["ERH"]), erz=float(r["ERZ"]), qual=str(r["QASR"]).strip()))
    return pd.DataFrame(rows).set_index("hypodd_id", drop=False)


def read_phs(path):
    # HYPOINVERSE input phase file written by core/hypoinverse.py:184-229 (one P per station from the
    # Z file, one S per station from the first horizontal file; terminator line carries the HypoDD id)
    rows, block = [], []
    for line in open(path):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        if line[:2] == "20" and line[:14].isdigit():          # event header: <event_id>00<lat>N<lon>E
            block = []
            continue
        if line.startswith(" "):                              # terminator: spaces + 200xxx
            hid = int(line.split()[-1])
            for b in block:
                b["hypodd_id"] = hid
            rows.extend(block)
            continue
        sta, net, cha = line[0:5].strip(), line[5:9].strip(), line[9:13].strip()
        if line[13:15] == "IP":
            block.append(dict(station=sta, net=net, phs_channel=cha, phase="P", phs_weight_code=int(line[16])))
        else:
            k = line.index("ES", 13)
            block.append(dict(station=sta, net=net, phs_channel=cha, phase="S", phs_weight_code=int(line[k + 3])))
    return pd.DataFrame(rows)


def read_dt_file(path, with_cc):
    # dt.ct: '# id1 id2' + 'NETSTA t1 t2 w P|S'; dt.cc: '# id1 id2 otc' + 'NETSTA dt cc P|S'
    rows, pair = [], None
    for line in open(path):
        t = line.split()
        if not t:
            continue
        if t[0] == "#":
            pair = (int(t[1]), int(t[2]))
            continue
        if with_cc:
            rows.append(dict(id1=pair[0], id2=pair[1], netsta=t[0], dt=float(t[1]), cc=float(t[2]), phase=t[3]))
        else:
            rows.append(dict(id1=pair[0], id2=pair[1], netsta=t[0], t1=float(t[1]), t2=float(t[2]),
                             w=float(t[3]), phase=t[4]))
    return pd.DataFrame(rows)


def ph2dt_input_phase_file(inp):
    lines = [l.rstrip("\n") for l in open(inp)]
    i = next(k for k, l in enumerate(lines) if l.strip().lower().startswith("* input phase file"))
    return lines[i + 1].strip()


def hypodd_log_centroid(log):
    for line in open(log):
        m = re.search(r"Cluster centroid at:\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", line)
        if m:
            return tuple(float(x) for x in m.groups())
    raise RuntimeError(f"no 'Cluster centroid at:' line in {log}")


# ----------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CHECKS, exist_ok=True)
    problems = []

    # --- event folders = KMA ids (UTC); their sorted order defines the HypoDD id ---------------
    wf_root = f"{REF}/waveforms_100km"
    event_dirs = sorted(d for d in os.listdir(wf_root) if os.path.isdir(f"{wf_root}/{d}"))
    idmap = pd.DataFrame(dict(rtdd_id=np.arange(1, len(event_dirs) + 1), kma_id=event_dirs,
                              hypodd_id=[HYPODD_ID_OFFSET + i for i in range(len(event_dirs))]))
    hid2kma = dict(zip(idmap.hypodd_id, idmap.kma_id))
    hid2rt = dict(zip(idmap.hypodd_id, idmap.rtdd_id))
    print(f"[events] {len(event_dirs)} event folders: {event_dirs[0]} .. {event_dirs[-1]}")

    # --- KMA catalog (KST) -> UTC id, magnitude ----------------------------------------------
    kma = pd.read_csv(f"{SUP}/kma_catalog/event_catalog.csv", encoding="utf-8-sig")
    kma.columns = [c.strip().lower() for c in kma.columns]
    kma["origin_utc"] = [UTCDateTime(int(r.year), int(r.month), int(r.day), int(r.hour), int(r.minute),
                                     int(r.second)) - KST_OFFSET_H * 3600 for r in kma.itertuples()]
    kma["kma_id"] = [t.strftime("%Y%m%d%H%M%S") for t in kma.origin_utc]
    kma["kst"] = [(t + KST_OFFSET_H * 3600).strftime("%Y-%m-%dT%H:%M:%S") for t in kma.origin_utc]
    if sorted(kma.kma_id) != event_dirs:
        problems.append("KMA catalog ids (KST-9h) differ from the waveform folder names")
    kma = kma.set_index("kma_id")
    final = pd.read_csv(f"{REF}/2.HypoDD/02.dt.cc/final_locations.csv", dtype={"event_id": str}).set_index("event_id")
    for k in event_dirs:
        if abs(final.loc[k, "magnitude"] - kma.loc[k, "magnitude"]) > 1e-6:
            problems.append(f"magnitude of {k}: final_locations {final.loc[k, 'magnitude']} vs KMA {kma.loc[k, 'magnitude']}")

    # --- every copy of the starting locations ------------------------------------------------
    ev02 = read_event_dat(f"{REF}/2.HypoDD/02.dt.cc/event.dat")
    ev01 = read_event_dat(f"{REF}/2.HypoDD/01.dt.ct/event.dat")
    ev00 = read_event_dat(f"{REF}/2.HypoDD/00.ph2dt/event.dat")
    sumdf = read_sum(f"{REF}/1.HypoInv/kim1983/Gwangyang.sum")
    pha_name = ph2dt_input_phase_file(f"{REF}/2.HypoDD/00.ph2dt/ph2dt.inp")
    pha_path = f"{REF}/2.HypoDD/00.ph2dt/{pha_name}"
    pha_other = f"{REF}/2.HypoDD/00.ph2dt/Gwangyang.pha"
    same_pha = md5(pha_path) == md5(pha_other)
    print(f"[ph2dt] ph2dt.inp reads '{pha_name}'; identical to Gwangyang.pha: {same_pha}")
    if not same_pha:
        problems.append(f"{pha_name} differs from Gwangyang.pha")
    pha_ev, pha_ph = read_pha(pha_path)
    centroid = hypodd_log_centroid(f"{REF}/2.HypoDD/02.dt.cc/hypoDD.log")
    centroid_ct = hypodd_log_centroid(f"{REF}/2.HypoDD/01.dt.ct/hypoDD.log")

    rows = []
    for hid in idmap.hypodd_id:
        k = hid2kma[hid]
        e2, e1, e0, s, p = ev02.loc[hid], ev01.loc[hid], ev00.loc[hid], sumdf.loc[hid], pha_ev.loc[hid]
        r = dict(rtdd_id=hid2rt[hid], kma_id=k, hypodd_id=hid,
                 kma_origin_utc=iso(kma.loc[k, "origin_utc"]), kma_lat=kma.loc[k, "latitude"],
                 kma_lon=kma.loc[k, "longitude"], kma_depth=kma.loc[k, "depth"], kma_ml=kma.loc[k, "magnitude"],
                 sum_origin=iso(s.origin), sum_lat=s.lat, sum_lon=s.lon, sum_depth=s.depth,
                 pha_origin=iso(p.origin), pha_lat=p.lat, pha_lon=p.lon, pha_depth=p.depth,
                 evdat02_time_field=e2.time_field, evdat02_origin=iso(e2.origin), evdat02_lat=e2.lat,
                 evdat02_lon=e2.lon, evdat02_depth=e2.depth, evdat02_mag=e2.mag,
                 evdat01_equal_02=bool(e1.origin == e2.origin and e1.lat == e2.lat and e1.lon == e2.lon and e1.depth == e2.depth),
                 evdat00_equal_02=bool(e0.origin == e2.origin and e0.lat == e2.lat and e0.lon == e2.lon and e0.depth == e2.depth),
                 d_origin_evdat_minus_pha_s=round(e2.origin - p.origin, 3),
                 d_epi_evdat_minus_pha_m=round(horiz_m(e2.lat, e2.lon, p.lat, p.lon), 1),
                 d_depth_evdat_minus_pha_m=round((e2.depth - p.depth) * 1000, 1),
                 d_origin_sum_minus_pha_s=round(s.origin - p.origin, 3),
                 d_epi_sum_minus_pha_m=round(horiz_m(s.lat, s.lon, p.lat, p.lon), 1),
                 d_lat_sum_minus_pha_deg=round(s.lat - p.lat, 4), d_lon_sum_minus_pha_deg=round(s.lon - p.lon, 4),
                 d_depth_sum_minus_pha_m=round((s.depth - p.depth) * 1000, 1),
                 d_origin_kma_minus_pha_s=round(kma.loc[k, "origin_utc"] - p.origin, 2),
                 d_epi_kma_minus_pha_km=round(horiz_m(kma.loc[k, "latitude"], kma.loc[k, "longitude"], p.lat, p.lon) / 1000, 2))
        # ph2dt writes TIME as the number HHMMSScc; held in single precision (24-bit mantissa) a value
        # between 2^24 = 16777216 and 2^25 can only be even, so an odd HHMMSScc at or after 17:00:00
        # (17000000 > 2^24) comes out 0.01 s later
        true_hms = p.origin.hour * 1000000 + p.origin.minute * 10000 + int(round((p.origin.second + p.origin.microsecond / 1e6) * 100))
        r["pha_hhmmsscc"] = true_hms
        r["float32_of_pha_hhmmsscc"] = int(np.float32(true_hms))
        r["evdat_time_is_float32_artifact"] = bool(int(np.float32(true_hms)) == int(e2.time_field) != true_hms)
        rows.append(r)
    evx = pd.DataFrame(rows)
    evx.to_csv(f"{CHECKS}/event_crosscheck.csv", index=False)
    n_dt = int((evx.d_origin_evdat_minus_pha_s != 0).sum())
    print(f"[events] event.dat (02) == event.dat (01): {evx.evdat01_equal_02.all()}, == 00.ph2dt: {evx.evdat00_equal_02.all()}")
    print(f"[events] event.dat vs .pha origin differs for {n_dt} event(s): "
          + ", ".join(f"{r.hypodd_id}:{r.d_origin_evdat_minus_pha_s:+.2f}s" for r in evx.itertuples() if r.d_origin_evdat_minus_pha_s != 0))
    print(f"[events] event.dat vs .pha location: max horizontal {evx.d_epi_evdat_minus_pha_m.max()} m, max depth {evx.d_depth_evdat_minus_pha_m.abs().max()} m")
    print(f"[events] .sum vs .pha: origin max |d| {evx.d_origin_sum_minus_pha_s.abs().max():.2f} s, "
          f"horizontal max {evx.d_epi_sum_minus_pha_m.max()} m, depth max |d| {evx.d_depth_sum_minus_pha_m.abs().max()} m")
    print(f"[events] KMA catalog vs .pha: origin |d| max {evx.d_origin_kma_minus_pha_s.abs().max():.2f} s, "
          f"epicentre max {evx.d_epi_kma_minus_pha_km.max()} km")
    mean_c = (pha_ev.lat.mean(), pha_ev.lon.mean(), pha_ev.depth.mean())
    print(f"[events] HypoDD ISTART=1 centroid (hypoDD.log, dt.cc run) = {centroid}; dt.ct run = {centroid_ct}; "
          f"mean of event.dat = ({mean_c[0]:.6f}, {mean_c[1]:.6f}, {mean_c[2]:.6f})")
    if max(abs(mean_c[0] - centroid[0]), abs(mean_c[1] - centroid[1])) > 1e-5 or abs(mean_c[2] - centroid[2]) > 1e-4:
        problems.append("hypoDD.log centroid differs from the mean of event.dat")

    # --- stations ----------------------------------------------------------------------------
    st = pd.read_csv(f"{REF}/station_table/used_stations_100km.csv")
    st = st.sort_values(["Network", "Code"]).reset_index(drop=True)
    sdat = {}
    for line in open(f"{REF}/2.HypoDD/00.ph2dt/station.dat"):
        t = line.split()
        sdat[t[0]] = (float(t[1]), float(t[2]))
    st["d_station_dat_m"] = [round(horiz_m(r.Latitude, r.Longitude, *sdat[r.Network + r.Code]), 2)
                             for r in st.itertuples()]
    print(f"[stations] {len(st)} stations; station.dat vs station table max offset {st.d_station_dat_m.max()} m")

    # --- waveform file inventory: which channel each station has in which event --------------
    wf = pd.DataFrame([dict(kma_id=os.path.basename(os.path.dirname(f)), **dict(zip(
        ("net", "sta", "cha"), os.path.basename(f).split(".")[1:4]))) for f in glob.glob(f"{wf_root}/*/*.sac")])
    wf["sensor"] = wf.cha.str[:2]
    sensors = wf.groupby("sta").sensor.unique()
    multi = {s: list(v) for s, v in sensors.items() if len(v) > 1}
    if multi:
        problems.append(f"stations with more than one sensor in the SAC set: {multi}")
    sensor_of = {s: v[0] for s, v in sensors.items()}
    table_sensor = dict(zip(st.Code, st.Sensor))
    for s, v in sensor_of.items():
        if table_sensor.get(s) != v:
            problems.append(f"sensor of {s}: SAC {v} vs used_stations table {table_sensor.get(s)}")
    have = set(zip(wf.kma_id, wf.sta, wf.cha))

    # --- phases: exactly the ph2dt input picks -------------------------------------------------
    pha_ph["net"] = pha_ph.netsta.str[:2]
    pha_ph["sta"] = pha_ph.netsta.str[2:]
    bad_net = pha_ph[~(pha_ph.net + pha_ph.sta).isin(set(st.Network + st.Code))]
    if len(bad_net):
        problems.append(f"{len(bad_net)} ph2dt phases at stations not in the station table")
    pha_ph["kma_id"] = pha_ph.hypodd_id.map(hid2kma)
    pha_ph["rtdd_id"] = pha_ph.hypodd_id.map(hid2rt)
    pha_ph["abs_time"] = [UTCDateTime(ns=pha_ev.loc[r.hypodd_id, "origin"].ns + r.tt_ms * 1_000_000)
                          for r in pha_ph.itertuples()]
    pha_ph["sensor"] = pha_ph.sta.map(sensor_of)
    pha_ph["channel"] = [r.sensor + (P_COMPONENT if r.phase == "P" else S_COMPONENT) for r in pha_ph.itertuples()]
    pha_ph["channel_file_exists"] = [(r.kma_id, r.sta, r.channel) in have for r in pha_ph.itertuples()]
    pha_ph["all3_files_exist"] = [all((r.kma_id, r.sta, r.sensor + c) in have for c in "ZNE") for r in pha_ph.itertuples()]
    if not pha_ph.channel_file_exists.all() or not pha_ph.all3_files_exist.all():
        problems.append("some ph2dt phases have no matching SAC channel file")
    dup = pha_ph.duplicated(["hypodd_id", "sta", "phase"]).sum()
    if dup:
        problems.append(f"{dup} duplicated (event, station, phase) entries in the .pha file")

    # .phs (HYPOINVERSE input): the channel each pick was attached to + weight code
    phs = read_phs(f"{REF}/1.HypoInv/PHS/Gwangyang.phs").rename(columns={"station": "sta"})
    pha_ph = pha_ph.merge(phs[["hypodd_id", "sta", "phase", "phs_channel", "phs_weight_code"]],
                          on=["hypodd_id", "sta", "phase"], how="left")
    pha_ph["weight_code_from_pha"] = pha_ph.weight.map(WEIGHT_TO_CODE)
    n_wmis = int((pha_ph.weight_code_from_pha != pha_ph.phs_weight_code).sum())
    n_chmis = int((pha_ph.phs_channel != pha_ph.channel).sum())
    print(f"[phases] {len(pha_ph)} ph2dt phases ({(pha_ph.phase == 'P').sum()} P, {(pha_ph.phase == 'S').sum()} S) "
          f"at {pha_ph.sta.nunique()} stations; .phs rows matched: {pha_ph.phs_channel.notna().sum()}; "
          f"weight-code mismatches {n_wmis}; channel differs from .phs: {n_chmis}")

    # PhaseNet+ picks
    pn = pd.concat([pd.read_csv(f, dtype={"Event_ID": str}) for f in sorted(glob.glob(f"{REF}/picks/*_picks.csv"))],
                   ignore_index=True)
    pn = pn.rename(columns={"Event_ID": "kma_id", "Station": "sta", "Phase": "phase"})
    print(f"[picks] PhaseNet+ tables: {len(pn)} picks ({(pn.phase == 'P').sum()} P, {(pn.phase == 'S').sum()} S) "
          f"in {pn.kma_id.nunique()} files")
    pha_ph = pha_ph.merge(pn[["kma_id", "sta", "phase", "Time", "Probability", "Polarity", "Amplitude"]],
                          on=["kma_id", "sta", "phase"], how="left", indicator="pn_match")
    pha_ph["pn_time"] = [UTCDateTime(t) if isinstance(t, str) else None for t in pha_ph.Time]
    pha_ph["pha_minus_pn_ms"] = [round((a - b) * 1000, 3) if b is not None else np.nan
                                 for a, b in zip(pha_ph.abs_time, pha_ph.pn_time)]
    pn_keys = set(zip(pha_ph.kma_id, pha_ph.sta, pha_ph.phase))
    pn_only = pn[[(k, s, p) not in pn_keys for k, s, p in zip(pn.kma_id, pn.sta, pn.phase)]]

    # SAC pick headers (absolute = reference time + a/t0), read from the channel the pick is attached to
    sac_t = []
    for r in pha_ph.itertuples():
        f = f"{wf_root}/{r.kma_id}/{r.kma_id}.{r.net}.{r.sta}.{r.channel}.sac"
        tr = read(f, headonly=True)[0]
        s = tr.stats.sac
        v = s.get("a" if r.phase == "P" else "t0", -12345.0)
        sac_t.append(None if v == -12345.0 else (tr.stats.starttime - s.b) + float(v))
    pha_ph["sac_time"] = sac_t
    pha_ph["sac_minus_pn_ms"] = [round((a - b) * 1000, 4) if (a is not None and b is not None) else np.nan
                                 for a, b in zip(pha_ph.sac_time, pha_ph.pn_time)]

    # usage counts in the HypoDD data files
    dtct = read_dt_file(f"{REF}/2.HypoDD/02.dt.cc/dt.ct", with_cc=False)
    dtcc07 = read_dt_file(f"{REF}/2.HypoDD/02.dt.cc/dt.cc_0.7_combined", with_cc=True)
    dtcc_all = pd.concat([read_dt_file(f, with_cc=True) for f in sorted(glob.glob(f"{REF}/2.HypoDD/02.dt.cc/dt.cc_[PS]/dt.cc_*"))],
                         ignore_index=True)

    def usage(df):
        c = pd.concat([df[["id1", "netsta", "phase"]].rename(columns={"id1": "hypodd_id"}),
                       df[["id2", "netsta", "phase"]].rename(columns={"id2": "hypodd_id"})])
        return c.groupby(["hypodd_id", "netsta", "phase"]).size()

    u_ct, u_cc07, u_cc = usage(dtct), usage(dtcc07), usage(dtcc_all)
    # ph2dt outliers: 'Outlier: NETSTA id1 id2 offset t1 t2 t1-t2' (phase found by matching t1/t2)
    tt_of = {(r.hypodd_id, r.netsta, round(r.tt_ms / 1000, 3)): r.phase for r in pha_ph.itertuples()}
    outl, n_outlier_lines = [], 0
    for line in open(f"{REF}/2.HypoDD/00.ph2dt/ph2dt.log"):
        if line.startswith("Outlier:"):
            n_outlier_lines += 1
            t = line.split()
            ns, i1, i2, t1, t2 = t[1], int(t[2]), int(t[3]), float(t[5]), float(t[6])
            ph1, ph2 = tt_of.get((i1, ns, round(t1, 3))), tt_of.get((i2, ns, round(t2, 3)))
            outl += [(i1, ns, ph1), (i2, ns, ph2)]
    n_unmatched_outl = sum(1 for o in outl if o[2] is None)
    if n_unmatched_outl:
        problems.append(f"{n_unmatched_outl} ph2dt outlier picks could not be matched to a .pha phase")
    outl = [o for o in outl if o[2] is not None]
    u_out = pd.Series(1, index=pd.MultiIndex.from_tuples(outl)).groupby(level=[0, 1, 2]).sum() if outl else pd.Series(dtype=int)
    key = list(zip(pha_ph.hypodd_id, pha_ph.netsta, pha_ph.phase))
    pha_ph["n_dtct"] = [int(u_ct.get(k, 0)) for k in key]
    pha_ph["n_ph2dt_outlier_pairs"] = [int(u_out.get(k, 0)) for k in key]
    pha_ph["n_dtcc_measured"] = [int(u_cc.get(k, 0)) for k in key]
    pha_ph["n_dtcc_cc07"] = [int(u_cc07.get(k, 0)) for k in key]
    print(f"[hypodd] dt.ct: {len(dtct)} lines ({(dtct.phase == 'P').sum()} P, {(dtct.phase == 'S').sum()} S); "
          f"dt.cc measured: {len(dtcc_all)} ({(dtcc_all.phase == 'P').sum()} P, {(dtcc_all.phase == 'S').sum()} S); "
          f"dt.cc cc>=0.7: {len(dtcc07)} ({(dtcc07.phase == 'P').sum()} P, {(dtcc07.phase == 'S').sum()} S); "
          f"ph2dt outlier lines: {n_outlier_lines}")
    used_sta = set(dtct.netsta) | set(dtcc07.netsta)
    unused = sorted(set(pha_ph.netsta) - used_sta)
    print(f"[hypodd] stations with ph2dt phases but no dt.ct/dt.cc data: {unused}")

    # epicentral distance from the starting (event.dat) location
    stc = {r.Network + r.Code: (r.Latitude, r.Longitude) for r in st.itertuples()}
    pha_ph["epi_dist_km"] = [round(horiz_m(ev02.loc[r.hypodd_id, "lat"], ev02.loc[r.hypodd_id, "lon"], *stc[r.netsta]) / 1000, 2)
                             for r in pha_ph.itertuples()]

    # mismatch report
    # expected: .pha time = PhaseNet+ time truncated to 0.01 s, i.e. -10 ms < (.pha - PhaseNet+) <= 0
    reason = []
    for r in pha_ph.itertuples():
        why = []
        if r.pn_match != "both":
            why.append("no PhaseNet+ pick")
        elif not (-PHA_TRUNC_TOL_MS + 1e-6 < r.pha_minus_pn_ms <= 1e-6):
            why.append(f".pha-PhaseNet+ = {r.pha_minus_pn_ms:+.3f} ms, outside (-10, 0] ms")
        if not (abs(r.sac_minus_pn_ms) <= SAC_TOL_MS):
            why.append("SAC header pick differs from PhaseNet+ by > 0.1 ms (or missing)")
        reason.append("; ".join(why))
    pha_ph["mismatch"] = reason
    bad = pha_ph[pha_ph.mismatch != ""]
    mis_cols = ["rtdd_id", "kma_id", "hypodd_id", "sta", "phase", "abs_time", "pn_time", "pha_minus_pn_ms",
                "sac_time", "sac_minus_pn_ms", "mismatch"]
    bad[mis_cols].assign(abs_time=lambda d: d.abs_time.map(iso),
                         pn_time=lambda d: d.pn_time.map(lambda t: iso(t) if t is not None else ""),
                         sac_time=lambda d: d.sac_time.map(lambda t: iso(t) if t is not None else "")
                         ).to_csv(f"{CHECKS}/pick_mismatches.csv", index=False)
    hist = pha_ph.pha_minus_pn_ms.value_counts().sort_index()
    print("[picks] (.pha - PhaseNet+) histogram [ms: count]: " + ", ".join(f"{k:+.0f}: {v}" for k, v in hist.items()))
    print(f"[picks] .pha (absolute) minus PhaseNet+: min {pha_ph.pha_minus_pn_ms.min():.3f} ms, "
          f"max {pha_ph.pha_minus_pn_ms.max():.3f} ms, median {pha_ph.pha_minus_pn_ms.median():.3f} ms; "
          f"SAC header minus PhaseNet+: max |d| {pha_ph.sac_minus_pn_ms.abs().max():.4f} ms")
    print(f"[picks] picks outside tolerance or unmatched: {len(bad)} (listed in checks/pick_mismatches.csv); "
          f"PhaseNet+ picks not used by ph2dt: {len(pn_only)}")
    if len(pn_only):
        pn_only.to_csv(f"{CHECKS}/phasenet_picks_not_in_pha.csv", index=False)

    # ------------------------------------------------------------------------- write outputs
    def write(path, header, rows):
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)

    # station.csv: coordinates and true elevation (m) exactly as in used_stations_100km.csv -- the same
    # values the NonLinLoc grids of step C1 were computed for (rtDD's NLLGrid finds a station's grid by its
    # 3-D position, so these numbers must not be rounded or changed). HYPOINVERSE/HypoDD used elevation 0.
    sta_hdr = ["latitude", "longitude", "elevation", "networkCode", "stationCode", "locationCode"]
    assert all(abs(round(v, 5) - v) < 1e-12 for v in list(st.Latitude) + list(st.Longitude)), "more than 5 decimals"
    write(f"{OUT}/station.csv", sta_hdr,
          [[f"{r.Latitude:.5f}", f"{r.Longitude:.5f}", f"{r.Elevation:.1f}", r.Network, r.Code, LOCATION_CODE]
           for r in st.itertuples()])

    # event.csv: location = HypoDD event.dat (identical to the .pha headers); origin time = .pha header
    ev_hdr = ["id", "isotime", "latitude", "longitude", "depth", "magnitude"]
    write(f"{OUT}/event.csv", ev_hdr,
          [[hid2rt[h], iso(pha_ev.loc[h, "origin"]), f"{ev02.loc[h, 'lat']:.4f}", f"{ev02.loc[h, 'lon']:.4f}",
            f"{ev02.loc[h, 'depth']:.3f}", f"{kma.loc[hid2kma[h], 'magnitude']:.1f}"] for h in idmap.hypodd_id])
    # event_centroid_start.csv: what HypoDD really started from with ISTART=1 (all events at the centroid)
    write(f"{OUT}/event_centroid_start.csv", ev_hdr,
          [[hid2rt[h], iso(pha_ev.loc[h, "origin"]), f"{centroid[0]:.6f}", f"{centroid[1]:.6f}",
            f"{centroid[2]:.6f}", f"{kma.loc[hid2kma[h], 'magnitude']:.1f}"] for h in idmap.hypodd_id])

    # phase.csv (blank uncertainties) + phase_extra.csv
    ph_hdr = ["eventId", "isotime", "lowerUncertainty", "upperUncertainty", "type", "networkCode",
              "stationCode", "locationCode", "channelCode"]
    write(f"{OUT}/phase.csv", ph_hdr,
          [[r.rtdd_id, iso(r.abs_time), "", "", r.phase, r.net, r.sta, LOCATION_CODE, r.channel]
           for r in pha_ph.itertuples()])
    extra = pd.DataFrame(dict(
        eventId=pha_ph.rtdd_id, kmaId=pha_ph.kma_id, hypoddId=pha_ph.hypodd_id, networkCode=pha_ph.net,
        stationCode=pha_ph.sta, locationCode=LOCATION_CODE, type=pha_ph.phase, channelCode=pha_ph.channel,
        sensor=pha_ph.sensor, isotime=pha_ph.abs_time.map(iso), travelTime_pha_s=pha_ph.tt_field,
        ph2dt_weight=pha_ph.weight, hypoinverse_weight_code=pha_ph.phs_weight_code,
        phs_channel=pha_ph.phs_channel, epi_dist_km=pha_ph.epi_dist_km,
        phasenet_time=pha_ph.pn_time.map(lambda t: iso(t) if t is not None else ""),
        phasenet_probability=pha_ph.Probability, phasenet_polarity=pha_ph.Polarity,
        phasenet_amplitude=pha_ph.Amplitude, isotime_minus_phasenet_ms=pha_ph.pha_minus_pn_ms,
        sac_header_time=pha_ph.sac_time.map(lambda t: iso(t) if t is not None else ""),
        sac_minus_phasenet_ms=pha_ph.sac_minus_pn_ms, n_dtct=pha_ph.n_dtct,
        n_ph2dt_outlier_pairs=pha_ph.n_ph2dt_outlier_pairs, n_dtcc_measured=pha_ph.n_dtcc_measured,
        n_dtcc_cc07=pha_ph.n_dtcc_cc07))
    extra.to_csv(f"{OUT}/phase_extra.csv", index=False, lineterminator="\n")

    # event_id_map.csv
    mp = idmap.assign(kma_origin_utc=[iso(kma.loc[k, "origin_utc"]) for k in idmap.kma_id],
                      kma_origin_kst=[kma.loc[k, "kst"] for k in idmap.kma_id],
                      kma_ml=[kma.loc[k, "magnitude"] for k in idmap.kma_id])
    mp.to_csv(f"{OUT}/event_id_map.csv", index=False, lineterminator="\n")

    # ------------------------------------------------------------------------- self-checks
    # 1) the rtDD id would be garbled by the 32-bit reader
    wrapped = [int(k) % 2**32 for k in idmap.kma_id]
    print(f"[ids] KMA ids as 32-bit unsigned (what rtDD would store): {wrapped[:3]} ... -> ids 1..{len(idmap)} used")
    # 2) re-read the written triplet with the same rules rtDD applies
    iso_re = re.compile(r"^(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)\.(\d+)Z$")
    s_ = pd.read_csv(f"{OUT}/station.csv", dtype=str, keep_default_na=False)
    e_ = pd.read_csv(f"{OUT}/event.csv", dtype=str, keep_default_na=False)
    p_ = pd.read_csv(f"{OUT}/phase.csv", dtype=str, keep_default_na=False)
    sid = set(s_.networkCode + "." + s_.stationCode + "." + s_.locationCode)
    assert all(iso_re.match(x) for x in list(e_.isotime) + list(p_.isotime)), "isotime format"
    assert set(p_.networkCode + "." + p_.stationCode + "." + p_.locationCode) <= sid, "phase station missing"
    assert set(p_.eventId) <= set(e_.id), "phase event missing"
    assert all(0 < int(x) < 2**32 for x in e_.id), "event id range"
    for f in ("station.csv", "event.csv", "event_centroid_start.csv", "phase.csv"):
        raw = open(f"{OUT}/{f}", "rb").read()
        assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw and b"\n\n" not in raw, f
        assert all(l == l.strip() and ", " not in l for l in raw.decode().splitlines()), f
    # 3) travel times implied by the written catalog equal the .pha travel times exactly
    e_t = {int(r.id): UTCDateTime(r.isotime) for r in e_.itertuples()}
    tt_written = [round(UTCDateTime(r.isotime) - e_t[int(r.eventId)], 3) for r in p_.itertuples()]
    assert np.allclose(tt_written, pha_ph.tt_ms / 1000.0, atol=5e-7), "travel times differ from .pha"
    print("[check] catalog triplet passes the rtDD reader rules; travel times == .pha travel times")

    print(f"[write] {OUT}: station.csv ({len(st)}), event.csv ({len(idmap)}), "
          f"event_centroid_start.csv, phase.csv ({len(pha_ph)}), phase_extra.csv, event_id_map.csv")
    if problems:
        print("[PROBLEMS]")
        for p in problems:
            print("  -", p)
    else:
        print("[problems] none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
