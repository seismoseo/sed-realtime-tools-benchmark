#!/usr/bin/env python
# make_stations_rtdd_xml.py  --  step Prep (install/06_gwangyang_prep.sh, stage inventory)
#
# Writes data/gwangyang_11ev/inputs/stations_rtdd.xml, the FDSN StationXML that rtDD (pyrtdd, scrtdd via
# fdsnxml2inv) and scautopick use for the Gwangyang 11-event benchmark:
#
#   * channels: exactly the 162 network/station/location/channel codes of the reference SAC files
#     (inputs/checks/waveform_manifest.csv; 54 stations x 3 components);
#   * metadata (epochs, orientation azimuth/dip, depth, sample rate, sensor, datalogger, response, comments):
#     copied unchanged from reference/inventory/merged_inventory.xml when it has that channel code with
#     epochs covering every SAC window of the channel, otherwise from the KMA master StationXML
#     (reference_supplement/inventory/KS_KG_metadata_1.0.2.xml; 21 channels at 7 stations). Every channel
#     epoch of the chosen source that overlaps 2021-07-01..2026-03-01 is kept (same rule as step C2's
#     stations.xml). A channel that a source covers only partly, or a station whose channels would come from
#     both sources, stops the script: that would need a decision, not a silent rule;
#   * coordinates: station AND channel latitude/longitude/elevation are REPLACED by
#     inputs/rtdd_catalog/station.csv (WHY: these are the numbers HypoDD's station.dat and the NonLinLoc kim1983
#     grids were made from; scrtdd/pyrtdd find a station's grid by its 3-D position within maxSearchDistance,
#     0.1 m in libhdd/pyrtdd, 10 m in the scrtdd plugin, and both programs take the position from the
#     CHANNEL / SensorLocation coordinates: pyrtdd obspy/catalog.py inventory.get_coordinates(),
#     scrtdd libs/hddsc/utils.cpp:311-313 SensorLocation lat/lon/elevation). The channel depth is kept.
#     Every original and new value goes to inputs/checks/inventory_coordinate_changes.csv;
#   * one Comment per station and per channel epoch records the source and the coordinate change.
#
# Self-checks after writing (re-read with obspy): the channel codes equal the SAC set; every SAC file is
# covered by exactly one channel epoch; coordinates equal station.csv exactly; every response equals its
# source (obspy object equality AND the complete response evaluated at EVAL_FREQS_HZ); azimuth, dip, depth,
# sample rate, sensor and epoch boundaries equal the source.
#
# Run with env pyrtdd (obspy 1.5.1, lxml, pandas):
#   python make_stations_rtdd_xml.py --master <KS_KG_metadata_1.0.2.xml> --out <stations_rtdd.xml>
#          --changes <inventory_coordinate_changes.csv> --options-json <json>

import argparse
import copy
import datetime
import hashlib
import io
import json
import os
import sys
import tempfile
from contextlib import contextmanager

import lxml
import numpy as np
import obspy
import pandas as pd
from lxml import etree
from obspy import Inventory, UTCDateTime, read_inventory
from obspy.core.inventory import Comment
from obspy.geodetics import gps2dist_azimuth

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
MERGED = f"{DATA}/reference/inventory/merged_inventory.xml"           # metadata source 1 (preferred)
MASTER_DEFAULT = f"{DATA}/reference_supplement/inventory/KS_KG_metadata_1.0.2.xml"  # metadata source 2
STATION_CSV = f"{DATA}/inputs/rtdd_catalog/station.csv"               # coordinates that replace the inventory ones
MANIFEST = f"{DATA}/inputs/checks/waveform_manifest.csv"              # the 1656 SAC files (written in step C2)
OUT_DEFAULT = f"{DATA}/inputs/stations_rtdd.xml"
CHANGES_DEFAULT = f"{DATA}/inputs/checks/inventory_coordinate_changes.csv"
SOURCES_CSV = f"{DATA}/inputs/checks/stations_rtdd_channel_sources.csv"  # one row per channel epoch written
PERIOD = ("2021-07-01T00:00:00", "2026-03-01T00:00:00")              # epochs overlapping this are kept
EVAL_FREQS_HZ = [0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 40.0, 45.0]  # response comparison
STATIONXML_NS = "{http://www.fdsn.org/xml/station/1}"
TODAY = datetime.date.today().isoformat()


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@contextmanager
def capture_c_stderr(out):
    # evalresp (the C library inside obspy) prints its warnings directly to file descriptor 2; catch them per
    # call so they can be counted and reported per channel epoch instead of flooding the log
    sys.stderr.flush()
    saved = os.dup(2)
    tmp = tempfile.TemporaryFile()
    os.dup2(tmp.fileno(), 2)
    try:
        yield out
    finally:
        sys.stderr.flush()
        os.dup2(saved, 2)
        os.close(saved)
        tmp.seek(0)
        out["text"] = tmp.read().decode(errors="replace")
        tmp.close()


def overlaps(ch, a, b):
    return ch.start_date < b and (ch.end_date is None or ch.end_date > a)


def covers(ch, a, b):
    return ch.start_date <= a and (ch.end_date is None or ch.end_date >= b)


def extract_stations(xml_path, network, stations):
    # Read only the wanted <Station> elements of a (large) StationXML with lxml and hand them to obspy as a
    # small in-memory StationXML; the elements are copied byte for byte (no field is touched).
    head, root_attrib, net_attrib, keep = [], None, None, []
    tags = tuple(STATIONXML_NS + t for t in ("Station", "Source", "Sender", "Module", "ModuleURI", "Created"))
    for _, el in etree.iterparse(xml_path, events=("end",), tag=tags):
        if el.tag == STATIONXML_NS + "Station":
            net = el.getparent()
            if net.get("code") == network and el.get("code") in stations:
                keep.append(etree.tostring(el))
                net_attrib = dict(net.attrib)
                root_attrib = dict(net.getparent().attrib)
            el.clear()
        elif el.getparent() is not None and el.getparent().tag == STATIONXML_NS + "FDSNStationXML":
            head.append(etree.tostring(el))
    if not keep:
        return Inventory(networks=[], source="(empty)")
    root = etree.Element(STATIONXML_NS + "FDSNStationXML", attrib=root_attrib, nsmap={None: STATIONXML_NS[1:-1]})
    for h in head:
        root.append(etree.fromstring(h))
    net = etree.SubElement(root, STATIONXML_NS + "Network", attrib=net_attrib)
    for k in keep:
        net.append(etree.fromstring(k))
    return read_inventory(io.BytesIO(etree.tostring(root, xml_declaration=True, encoding="UTF-8")), format="STATIONXML")


def channel_epochs(inv, net, sta, loc, cha, t0, t1):
    return sorted([c for n in inv if n.code == net for s in n if s.code == sta for c in s
                   if c.location_code == loc and c.code == cha and overlaps(c, t0, t1)], key=lambda c: c.start_date)


def station_objects(inv, net, sta):
    return [s for n in inv if n.code == net for s in n if s.code == sta]


def fmt_t(t):
    return "" if t is None else str(t)[:19]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master", default=MASTER_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--changes", default=CHANGES_DEFAULT)
    ap.add_argument("--sources-csv", default=SOURCES_CSV)
    ap.add_argument("--options-json", default=None)
    args = ap.parse_args()
    t0, t1 = UTCDateTime(PERIOD[0]), UTCDateTime(PERIOD[1])

    # ------------------------------------------------------------------ inputs
    st = pd.read_csv(STATION_CSV, dtype={"networkCode": str, "stationCode": str, "locationCode": str},
                     keep_default_na=False)
    st_by = {(r.networkCode, r.stationCode, r.locationCode): r for r in st.itertuples()}
    man = pd.read_csv(MANIFEST, dtype={"kma_id": str, "loc": str, "net": str, "sta": str, "cha": str},
                      keep_default_na=False)
    man["t0"] = man.starttime.map(UTCDateTime)
    man["t1"] = man.endtime.map(UTCDateTime)
    sac_nslc = sorted(set(zip(man.net, man.sta, man["loc"], man.cha)))
    sac_sta = sorted(set((n, s, l) for n, s, l, _ in sac_nslc))
    print(f"[inputs] station.csv: {len(st)} stations; SAC: {len(man)} files, {len(sac_nslc)} channels at "
          f"{len(sac_sta)} station/location codes")
    if set(sac_sta) != set(st_by):
        sys.exit(f"ERROR: SAC stations differ from station.csv: only SAC {sorted(set(sac_sta) - set(st_by))}, "
                 f"only csv {sorted(set(st_by) - set(sac_sta))}")

    merged = read_inventory(MERGED)
    print(f"[merged] {MERGED}: {sum(len(n.stations) for n in merged)} stations, "
          f"{sum(len(s.channels) for n in merged for s in n)} channel epochs")

    # ------------------------------------------------------------------ choose the source of each SAC channel
    choice = {}
    need_master = set()
    for nslc in sac_nslc:
        net, sta, loc, cha = nslc
        files = man[(man.net == net) & (man.sta == sta) & (man["loc"] == loc) & (man.cha == cha)]
        eps = channel_epochs(merged, net, sta, loc, cha, t0, t1)
        if eps:
            ncov = [sum(covers(c, r.t0, r.t1) for c in eps) for r in files.itertuples()]
            if any(n != 1 for n in ncov):
                sys.exit(f"ERROR: {'.'.join(nslc)}: merged_inventory.xml has epochs in the period but they do not "
                         f"cover every SAC window exactly once (coverage counts {ncov}); this needs a decision")
            choice[nslc] = ("merged_inventory.xml", eps, files)
        else:
            need_master.add((net, sta))
            choice[nslc] = None
    print(f"[choice] channels from merged_inventory.xml: {sum(v is not None for v in choice.values())}; "
          f"to take from the master XML: {sum(v is None for v in choice.values())} "
          f"(stations {', '.join(s for _, s in sorted(need_master))})")

    master = Inventory(networks=[], source="(not read)")
    if need_master:
        print(f"[master] reading the {len(need_master)} stations from {args.master} (md5 {md5(args.master)})")
        nets = {n for n, _ in need_master}
        if len(nets) != 1:
            sys.exit("ERROR: master stations from several networks are not handled")
        master = extract_stations(args.master, nets.pop(), {s for _, s in need_master})
        print(f"[master] extracted {sum(len(n.stations) for n in master)} station elements, "
              f"{sum(len(s.channels) for n in master for s in n)} channel epochs")
    for nslc, v in list(choice.items()):
        if v is not None:
            continue
        net, sta, loc, cha = nslc
        files = man[(man.net == net) & (man.sta == sta) & (man["loc"] == loc) & (man.cha == cha)]
        eps = channel_epochs(master, net, sta, loc, cha, t0, t1)
        ncov = [sum(covers(c, r.t0, r.t1) for c in eps) for r in files.itertuples()]
        if not eps or any(n != 1 for n in ncov):
            sys.exit(f"ERROR: {'.'.join(nslc)}: the master XML does not cover every SAC window exactly once "
                     f"(epochs {len(eps)}, coverage counts {ncov})")
        choice[nslc] = ("KS_KG_metadata_1.0.2.xml", eps, files)

    # ------------------------------------------------------------------ build the inventory
    src_inv = {"merged_inventory.xml": merged, "KS_KG_metadata_1.0.2.xml": master}
    src_path = {"merged_inventory.xml": MERGED, "KS_KG_metadata_1.0.2.xml": args.master}
    knet = [n for n in merged if n.code == "KS"]
    if len(knet) != 1:
        sys.exit("ERROR: expected exactly one KS network in merged_inventory.xml")
    out_net = copy.deepcopy(knet[0])
    out_net.stations = []
    changes, source_rows, origin = [], [], {}
    for net, sta, loc in sac_sta:
        nslcs = [x for x in sac_nslc if x[:3] == (net, sta, loc)]
        srcs = {choice[x][0] for x in nslcs}
        if len(srcs) != 1:
            sys.exit(f"ERROR: station {net}.{sta} would mix metadata sources {srcs}; this needs a decision")
        src = srcs.pop()
        sobjs = station_objects(src_inv[src], net, sta)
        # the station element(s) that hold the chosen channel epochs
        holders = [s for s in sobjs if any(c in s.channels for x in nslcs for c in choice[x][1])]
        if len(holders) != 1:
            sys.exit(f"ERROR: {net}.{sta}: chosen channel epochs sit in {len(holders)} station elements of {src}")
        new_sta = copy.deepcopy(holders[0])
        new_sta.channels = []
        r = st_by[(net, sta, loc)]
        new_lat, new_lon, new_elev = float(r.latitude), float(r.longitude), float(r.elevation)

        def record(level, obj, cha="", start=None, end=None, depth=None):
            o_lat, o_lon, o_elev = float(obj.latitude), float(obj.longitude), float(obj.elevation)
            dh = gps2dist_azimuth(o_lat, o_lon, new_lat, new_lon)[0]
            changes.append(dict(
                level=level, network=net, station=sta, location=loc, channel=cha, start=fmt_t(start), end=fmt_t(end),
                metadata_source=src, orig_latitude=o_lat, orig_longitude=o_lon, orig_elevation_m=o_elev,
                new_latitude=new_lat, new_longitude=new_lon, new_elevation_m=new_elev,
                depth_m_kept=("" if depth is None else float(depth)),
                dlat_deg=round(new_lat - o_lat, 6), dlon_deg=round(new_lon - o_lon, 6),
                delev_m=round(new_elev - o_elev, 3), horizontal_offset_m=round(dh, 2),
                offset_3d_m=round(float(np.hypot(dh, new_elev - o_elev)), 2),
                changed=bool(o_lat != new_lat or o_lon != new_lon or o_elev != new_elev)))
            return o_lat, o_lon, o_elev

        o = record("station", new_sta, start=new_sta.start_date, end=new_sta.end_date)
        origin[(net, sta)] = o
        new_sta.latitude, new_sta.longitude, new_sta.elevation = new_lat, new_lon, new_elev
        new_sta.comments.append(Comment(
            f"stations_rtdd.xml ({TODAY}, install/06_gwangyang_prep.sh stage inventory): station metadata from {src}; "
            f"latitude/longitude/elevation replaced by data/gwangyang_11ev/inputs/rtdd_catalog/station.csv "
            f"({new_lat}, {new_lon}, {new_elev} m; was {o[0]}, {o[1]}, {o[2]} m)"))
        for x in nslcs:
            for c in choice[x][1]:
                nc = copy.deepcopy(c)
                oc = record("channel", nc, cha=nc.code, start=nc.start_date, end=nc.end_date, depth=nc.depth)
                nc.latitude, nc.longitude, nc.elevation = new_lat, new_lon, new_elev
                nc.comments.append(Comment(
                    f"stations_rtdd.xml ({TODAY}, install/06_gwangyang_prep.sh stage inventory): channel epoch copied "
                    f"from {src} with epoch, orientation, depth, sample rate, sensor and response unchanged; "
                    f"latitude/longitude/elevation replaced by data/gwangyang_11ev/inputs/rtdd_catalog/station.csv "
                    f"({new_lat}, {new_lon}, {new_elev} m; was {oc[0]}, {oc[1]}, {oc[2]} m)"))
                new_sta.channels.append(nc)
                files = choice[x][2]
                source_rows.append(dict(
                    network=net, station=sta, location=loc, channel=nc.code, start=fmt_t(nc.start_date),
                    end=fmt_t(nc.end_date), metadata_source=src, source_file=src_path[src],
                    events_covered=" ".join(sorted(fr.kma_id for fr in files.itertuples() if covers(c, fr.t0, fr.t1))),
                    sensor_model=(nc.sensor.model if nc.sensor else ""), depth_m=nc.depth, azimuth=nc.azimuth,
                    dip=nc.dip, sample_rate=nc.sample_rate,
                    sensitivity=(nc.response.instrument_sensitivity.value
                                 if nc.response and nc.response.instrument_sensitivity else np.nan),
                    input_units=(nc.response.instrument_sensitivity.input_units
                                 if nc.response and nc.response.instrument_sensitivity else ""),
                    n_response_stages=(len(nc.response.response_stages) if nc.response else 0)))
        new_sta.selected_number_of_channels = len(new_sta.channels)
        out_net.stations.append(new_sta)
    out_net.selected_number_of_stations = len(out_net.stations)
    inv = Inventory(networks=[out_net], source=(
        "Gwangyang 11-event benchmark: stations_rtdd.xml for rtDD/SeisComP (install/06_gwangyang_prep.sh; "
        "tools/make_stations_rtdd_xml.py). SAC channels only; metadata from merged_inventory.xml, else from "
        "KS_KG_metadata_1.0.2.xml; latitude/longitude/elevation from inputs/rtdd_catalog/station.csv"))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    inv.write(args.out, format="STATIONXML", validate=True)
    print(f"[write] {args.out}: {len(out_net.stations)} stations, "
          f"{sum(len(s.channels) for s in out_net.stations)} channel epochs (schema-validated on write)")

    # ------------------------------------------------------------------ self-checks on the re-read file
    back = read_inventory(args.out)
    problems = []
    nslc_back = sorted({(n.code, s.code, c.location_code, c.code) for n in back for s in n for c in s})
    if nslc_back != sac_nslc:
        problems.append(f"channel codes differ from the SAC set ({len(nslc_back)} vs {len(sac_nslc)})")
    ncov_bad = 0
    for fr in man.itertuples():
        eps = [c for n in back if n.code == fr.net for s in n if s.code == fr.sta for c in s
               if c.location_code == fr.loc and c.code == fr.cha and covers(c, fr.t0, fr.t1)]
        ncov_bad += len(eps) != 1
    if ncov_bad:
        problems.append(f"{ncov_bad} SAC files not covered by exactly one epoch")
    coord_bad = 0
    for n in back:
        for s in n:
            r = st_by[(n.code, s.code, s[0].location_code)]
            want = (float(r.latitude), float(r.longitude), float(r.elevation))
            coord_bad += (float(s.latitude), float(s.longitude), float(s.elevation)) != want
            coord_bad += sum((float(c.latitude), float(c.longitude), float(c.elevation)) != want for c in s)
    if coord_bad:
        problems.append(f"{coord_bad} station/channel coordinates differ from station.csv")
    # responses and channel metadata vs the source objects
    f = np.array(EVAL_FREQS_HZ)
    resp_rows = []
    for n in back:
        for s in n:
            for c in s:
                src = next(v[0] for k, v in choice.items() if k == (n.code, s.code, c.location_code, c.code))
                sc = [x for x in channel_epochs(src_inv[src], n.code, s.code, c.location_code, c.code, t0, t1)
                      if x.start_date == c.start_date and x.end_date == c.end_date]
                if len(sc) != 1:
                    problems.append(f"{n.code}.{s.code}.{c.code} {c.start_date}: no unique source epoch")
                    continue
                sc = sc[0]
                same_obj = c.response == sc.response
                cap = {}
                with capture_c_stderr(cap):
                    r_new = c.response.get_evalresp_response_for_frequencies(f, output="DEF")
                    r_old = sc.response.get_evalresp_response_for_frequencies(f, output="DEF")
                    sens = c.response.instrument_sensitivity
                    r_sens = c.response.get_evalresp_response_for_frequencies(np.array([sens.frequency]), output="DEF")[0]
                rel = float(np.max(np.abs(r_new - r_old) / np.abs(r_old)))
                # evalresp's own consistency test (norm_resp): |response at the sensitivity frequency| vs the stated
                # InstrumentSensitivity; a property of the SOURCE metadata (identical for source and copy)
                ratio = float(np.abs(r_sens) / sens.value)
                # what evalresp's norm_resp test compares: the product of the stage gains vs the stated sensitivity
                prod_ratio = float(np.prod([g.stage_gain for g in c.response.response_stages]) / sens.value)
                n_warn = cap["text"].count("WARNING")
                meta_same = all(getattr(c, a) == getattr(sc, a) for a in
                                ("azimuth", "dip", "depth", "sample_rate", "start_date", "end_date", "code",
                                 "location_code")) and c.sensor == sc.sensor and c.data_logger == sc.data_logger
                resp_rows.append(dict(nslc=f"{n.code}.{s.code}.{c.location_code}.{c.code}", start=fmt_t(c.start_date),
                                      response_object_equal=same_obj, response_max_rel_diff=rel,
                                      orientation_depth_rate_sensor_epoch_equal=meta_same,
                                      stated_sensitivity=sens.value, sensitivity_frequency_hz=sens.frequency,
                                      evaluated_over_stated_at_sens_freq=round(ratio, 6),
                                      stage_gain_product_over_stated=round(prod_ratio, 6),
                                      evalresp_warning_lines=n_warn,
                                      evalresp_warning_texts=" | ".join(sorted({l.strip() for l in cap["text"].splitlines()
                                                                               if "WARNING" in l}))))
                if not same_obj or rel > 1e-12 or not meta_same:
                    problems.append(f"{n.code}.{s.code}.{c.code} {c.start_date}: response/metadata changed "
                                    f"(object equal {same_obj}, max rel diff {rel:.3g}, other metadata equal {meta_same})")
    rr = pd.DataFrame(resp_rows)
    print(f"[check] channel codes == SAC set: {nslc_back == sac_nslc} ({len(nslc_back)}); SAC files covered by "
          f"exactly one epoch: {len(man) - ncov_bad}/{len(man)}; coordinate mismatches vs station.csv: {coord_bad}")
    print(f"[check] responses: {int(rr.response_object_equal.sum())}/{len(rr)} channel epochs equal to their source "
          f"as obspy objects; largest relative difference of the evaluated response at {EVAL_FREQS_HZ} Hz: "
          f"{rr.response_max_rel_diff.max():.3g}; orientation/depth/sample rate/sensor/epoch equal: "
          f"{int(rr.orientation_depth_rate_sensor_epoch_equal.sum())}/{len(rr)}")
    # properties of the SOURCE metadata (identical in source and copy; reported, not changed)
    flagged = rr[rr.evalresp_warning_lines > 0]
    signflip = rr[rr.stage_gain_product_over_stated < 0]
    print(f"[metadata] evalresp printed {sorted(set(flagged.evalresp_warning_texts))} for {len(flagged)} channel epochs "
          f"(same for source and copy). Epochs whose stage-gain product has the opposite sign of the stated "
          f"sensitivity: {len(signflip)}; the two sets are identical: {set(flagged.index) == set(signflip.index)}; "
          f"|product/stated| in those: {signflip.stage_gain_product_over_stated.abs().min():.4f}.."
          f"{signflip.stage_gain_product_over_stated.abs().max():.4f}")
    for (sta, start), g in signflip.assign(sta=signflip.nslc.str.split('.').str[1]).groupby(["sta", "start"]):
        print(f"          {sta} {start} ({', '.join(x.split('.')[3] for x in g.nslc)})")
    neg = rr[rr.stated_sensitivity < 0]
    print(f"[metadata] epochs with a NEGATIVE stated sensitivity: {len(neg)} "
          f"({', '.join(sorted({x.split('.')[1] + ' ' + y[:10] for x, y in zip(neg.nslc, neg.start)}))})")
    off = rr[(rr.evaluated_over_stated_at_sens_freq.abs() - 1).abs() > 0.05]
    print(f"[metadata] epochs whose full response at the sensitivity frequency differs from the stated sensitivity "
          f"by more than 5 %: {len(off)} " + ", ".join(f"{x} {y[:10]} ({v:.3f})" for x, y, v in
                                                       zip(off.nslc, off.start, off.evaluated_over_stated_at_sens_freq)))

    # ------------------------------------------------------------------ tables
    ch = pd.DataFrame(changes)
    ch.to_csv(args.changes, index=False)
    srcdf = pd.DataFrame(source_rows).merge(rr.assign(
        network=rr.nslc.str.split(".").str[0], station=rr.nslc.str.split(".").str[1],
        location=rr.nslc.str.split(".").str[2], channel=rr.nslc.str.split(".").str[3]).drop(columns="nslc"),
        on=["network", "station", "location", "channel", "start"], how="left")
    srcdf.to_csv(args.sources_csv, index=False)
    stl = ch[ch.level == "station"]
    print(f"[changes] {args.changes}: {len(ch)} rows ({len(stl)} stations, {int((ch.level == 'channel').sum())} channel "
          f"epochs); rows that changed: {int(ch.changed.sum())}")
    print(f"[changes] per station (station level): horizontal offset median {stl.horizontal_offset_m.median():.1f} m, "
          f"max {stl.horizontal_offset_m.max():.1f} m; elevation change {stl.delev_m.min():.1f}..{stl.delev_m.max():.1f} m")
    for r in stl[stl.horizontal_offset_m > 1.0].itertuples():
        print(f"          {r.station:5s} ({r.metadata_source}): horizontal {r.horizontal_offset_m} m "
              f"(lat {r.orig_latitude} -> {r.new_latitude}, lon {r.orig_longitude} -> {r.new_longitude}), "
              f"elevation {r.orig_elevation_m} -> {r.new_elevation_m} m")
    for r in stl[(stl.horizontal_offset_m <= 1.0) & (stl.metadata_source != "merged_inventory.xml")].itertuples():
        print(f"          {r.station:5s} ({r.metadata_source}): horizontal {r.horizontal_offset_m} m, "
              f"elevation {r.orig_elevation_m} -> {r.new_elevation_m} m")
    cc = ch[ch.level == "channel"]
    inconsistent = cc.groupby("station").apply(
        lambda g: len(set(zip(g.orig_latitude, g.orig_longitude, g.orig_elevation_m))) > 1, include_groups=False)
    print(f"[changes] stations whose channel epochs had differing original coordinates: "
          f"{', '.join(inconsistent[inconsistent].index) or 'none'}")
    print(f"[sources] {args.sources_csv}: {len(srcdf)} channel epochs; by source: "
          f"{srcdf.metadata_source.value_counts().to_dict()}")

    # ------------------------------------------------------------------ options actually used
    if args.options_json:
        opts = dict(
            script=os.path.abspath(__file__), run_time=datetime.datetime.now().astimezone().isoformat(),
            argv=sys.argv, args=vars(args), PERIOD=PERIOD, EVAL_FREQS_HZ=EVAL_FREQS_HZ,
            inputs={p: md5(p) for p in (MERGED, args.master, STATION_CSV, MANIFEST)},
            outputs={p: md5(p) for p in (args.out, args.changes, args.sources_csv)},
            rules=dict(
                channel_codes="exactly the NET.STA.LOC.CHA of the SAC files (waveform_manifest.csv)",
                source_order=["merged_inventory.xml (if it covers every SAC window of the channel exactly once)",
                              "KS_KG_metadata_1.0.2.xml (master), same coverage test"],
                epochs_kept="every channel epoch of the chosen source overlapping PERIOD",
                coordinates="station and channel latitude/longitude/elevation := station.csv; depth kept",
                unchanged="epoch boundaries, azimuth, dip, depth, sample rate, sensor, datalogger, response, "
                          "existing comments; station/network elements copied from the source",
                added="one Comment per station and per channel epoch; selected_number_of_channels/stations "
                      "set to the numbers written"),
            versions=dict(python=sys.version.split()[0], obspy=obspy.__version__, pandas=pd.__version__,
                          numpy=np.__version__, lxml=lxml.__version__),
            n_problems=len(problems), problems=problems)
        with open(args.options_json, "w") as fo:
            json.dump(opts, fo, indent=1, default=str)
        print(f"[options] {args.options_json}")
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("[ok] all self-checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
