#!/usr/bin/env python
# check_inventory_sc.py  --  step Prep (install/06_gwangyang_prep.sh, stage scinv)
#
# Reads data/gwangyang_11ev/inputs/inventory_sc.xml (made by 'fdsnxml2inv' from stations_rtdd.xml) with SeisComP's
# OWN Python API (seiscomp.io.XMLArchive -> seiscomp.datamodel.Inventory) and checks, object by object:
#   * every Station and every SensorLocation has latitude/longitude/elevation equal to
#     inputs/rtdd_catalog/station.csv (scrtdd reads the SensorLocation coordinates: libs/hddsc/utils.cpp:311-313);
#   * every Stream equals its StationXML channel epoch (same NET.STA.LOC.CHA and start): end time, depth, azimuth,
#     dip, sample rate, gain (= InstrumentSensitivity value), gain frequency and gain unit; nothing is lost or added;
#   * the exact lookup scrtdd makes for a pick, DataModel::getSensorLocation(inv, net, sta, loc, pick time)
#     (libs/hddsc/utils.cpp:93), for all 763 catalog picks of inputs/rtdd_catalog/phase.csv, returns the
#     station.csv coordinates;
#   * the NSLC list printed by 'scinv ls --nslc' equals the 162 channel codes of the StationXML.
#
# Runs with the python of the SeisComP environment (conda env seiscomp, standard library + seiscomp modules; no
# pandas there). Called with 'python -I', so $SEISCOMP_ROOT/lib/python is added to sys.path below.
#   python -I check_inventory_sc.py --scml <inventory_sc.xml> --stationxml <stations_rtdd.xml>
#          --station-csv <station.csv> --outdir <dir> [--scinv-ls-nslc <file>] [--options-json <json>]

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.environ["SEISCOMP_ROOT"], "lib", "python"))
import seiscomp.core as sccore            # noqa: E402
import seiscomp.datamodel as scdm         # noqa: E402
import seiscomp.io as scio                # noqa: E402

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
PHASE_CSV = f"{PROJECT}/data/gwangyang_11ev/inputs/rtdd_catalog/phase.csv"   # the 763 catalog picks
NS = "{http://www.fdsn.org/xml/station/1}"
FAR_FUTURE_YEARS = (2099, 9999)   # end dates the KMA master XML uses for "still running" epochs
REL_TOL_GAIN = 1e-12              # gain comparison tolerance (relative)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def t_iso(get):
    # SeisComP optional time -> 'YYYY-MM-DDThh:mm:ss' or '' when not set
    try:
        return get().toString("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return ""


def sx_time(s):
    return "" if not s else s[:19]


def read_stationxml_channels(path):
    rows = {}
    root = ET.parse(path).getroot()
    for net in root.findall(NS + "Network"):
        for sta in net.findall(NS + "Station"):
            for ch in sta.findall(NS + "Channel"):
                sens = ch.find(f"{NS}Response/{NS}InstrumentSensitivity")
                key = (net.get("code"), sta.get("code"), ch.get("locationCode") or "", ch.get("code"),
                       sx_time(ch.get("startDate")))
                rows[key] = dict(
                    end=sx_time(ch.get("endDate")), depth=float(ch.findtext(NS + "Depth")),
                    azimuth=float(ch.findtext(NS + "Azimuth")), dip=float(ch.findtext(NS + "Dip")),
                    sample_rate=float(ch.findtext(NS + "SampleRate")),
                    gain=float(sens.findtext(NS + "Value")), gain_frequency=float(sens.findtext(NS + "Frequency")),
                    gain_unit=sens.findtext(f"{NS}InputUnits/{NS}Name"))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scml", required=True)
    ap.add_argument("--stationxml", required=True)
    ap.add_argument("--station-csv", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--scinv-ls-nslc", default=None)
    ap.add_argument("--options-json", default=None)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    problems, summary = [], {}

    with open(args.station_csv) as f:
        st = {(r["networkCode"], r["stationCode"], r["locationCode"]): (float(r["latitude"]), float(r["longitude"]),
                                                                         float(r["elevation"])) for r in csv.DictReader(f)}
    sx = read_stationxml_channels(args.stationxml)

    ar = scio.XMLArchive()
    if not ar.open(args.scml):
        sys.exit(f"ERROR: SeisComP cannot open {args.scml}")
    inv = scdm.Inventory.Cast(ar.readObject())
    ar.close()
    if inv is None:
        sys.exit("ERROR: no Inventory object in the file")
    summary["counts"] = dict(networks=inv.networkCount(), sensors=inv.sensorCount(), dataloggers=inv.dataloggerCount(),
                             responsePAZ=inv.responsePAZCount(), responseFIR=inv.responseFIRCount(),
                             responsePolynomial=inv.responsePolynomialCount(), responseIIR=inv.responseIIRCount(),
                             responseFAP=inv.responseFAPCount())

    loc_rows, stream_rows, seen = [], [], set()
    n_sta = 0
    for i in range(inv.networkCount()):
        net = inv.network(i)
        for j in range(net.stationCount()):
            sta = net.station(j)
            n_sta += 1
            for k in range(sta.sensorLocationCount()):
                loc = sta.sensorLocation(k)
                want = st.get((net.code(), sta.code(), loc.code()))
                got_sta = (sta.latitude(), sta.longitude(), sta.elevation())
                got_loc = (loc.latitude(), loc.longitude(), loc.elevation())
                loc_rows.append(dict(
                    network=net.code(), station=sta.code(), location=loc.code(), station_start=t_iso(sta.start),
                    station_end=t_iso(sta.end), location_start=t_iso(loc.start), location_end=t_iso(loc.end),
                    station_latitude=got_sta[0], station_longitude=got_sta[1], station_elevation_m=got_sta[2],
                    location_latitude=got_loc[0], location_longitude=got_loc[1], location_elevation_m=got_loc[2],
                    csv_latitude=want[0] if want else "", csv_longitude=want[1] if want else "",
                    csv_elevation_m=want[2] if want else "", n_streams=loc.streamCount(),
                    station_equals_csv=(got_sta == want), location_equals_csv=(got_loc == want)))
                for m in range(loc.streamCount()):
                    s = loc.stream(m)
                    key = (net.code(), sta.code(), loc.code(), s.code(), t_iso(s.start))
                    seen.add(key)
                    ref = sx.get(key)
                    row = dict(network=key[0], station=key[1], location=key[2], channel=key[3], start=key[4],
                               end=t_iso(s.end), depth_m=s.depth(), azimuth=s.azimuth(), dip=s.dip(),
                               sample_rate=s.sampleRateNumerator() / s.sampleRateDenominator(), gain=s.gain(),
                               gain_frequency=s.gainFrequency(), gain_unit=s.gainUnit(), in_stationxml=ref is not None)
                    if ref:
                        end_ok = (row["end"] == ref["end"]) or (row["end"] == "" and ref["end"][:4].isdigit()
                                                                 and int(ref["end"][:4]) in FAR_FUTURE_YEARS)
                        diffs = [a for a in ("depth", "azimuth", "dip", "sample_rate", "gain_frequency")
                                 if abs(row[a if a != "depth" else "depth_m"] - ref[a]) > 1e-9]
                        if abs(row["gain"] - ref["gain"]) > REL_TOL_GAIN * abs(ref["gain"]):
                            diffs.append("gain")
                        if row["gain_unit"] != ref["gain_unit"]:
                            diffs.append("gain_unit")
                        if not end_ok:
                            diffs.append("end")
                        row.update(stationxml_end=ref["end"], stationxml_gain=ref["gain"],
                                   end_note=("StationXML end " + ref["end"] + " -> open in SeisComP"
                                             if row["end"] == "" and ref["end"] else ""),
                                   differences=" ".join(diffs))
                        if diffs:
                            problems.append(f"{'.'.join(key[:4])} {key[4]}: differs from StationXML in {diffs}")
                    else:
                        problems.append(f"{'.'.join(key[:4])} {key[4]}: stream not in the StationXML")
                    stream_rows.append(row)
    missing = sorted(set(sx) - seen)
    for k in missing:
        problems.append(f"{'.'.join(k[:4])} {k[4]}: StationXML channel epoch missing in SeisComP XML")

    # the lookup scrtdd makes for each pick
    pick_rows = []
    with open(PHASE_CSV) as f:
        for p in csv.DictReader(f):
            t = sccore.Time.FromString(p["isotime"].rstrip("Z"), "%Y-%m-%dT%H:%M:%S.%f")
            loc = scdm.getSensorLocation(inv, p["networkCode"], p["stationCode"], p["locationCode"], t)
            got = (loc.latitude(), loc.longitude(), loc.elevation()) if loc else None
            want = st[(p["networkCode"], p["stationCode"], p["locationCode"])]
            pick_rows.append(dict(eventId=p["eventId"], station=p["stationCode"], type=p["type"], isotime=p["isotime"],
                                  found=loc is not None, equals_station_csv=(got == want)))
    n_pick_ok = sum(r["equals_station_csv"] for r in pick_rows)
    if n_pick_ok != len(pick_rows):
        problems.append(f"getSensorLocation at pick times: {len(pick_rows) - n_pick_ok} picks without station.csv coordinates")

    # scinv ls --nslc
    if args.scinv_ls_nslc and os.path.exists(args.scinv_ls_nslc):
        ls = set()
        for line in open(args.scinv_ls_nslc):
            m = re.match(r"^\s*([A-Z0-9]+)\.([A-Z0-9]+)\.([A-Z0-9]*)\.([A-Z0-9]+)\b", line)
            if m:
                ls.add(m.groups())
        sx_nslc = {k[:4] for k in sx}
        summary["scinv_ls_nslc"] = dict(n=len(ls), equals_stationxml_codes=(ls == sx_nslc),
                                        only_in_ls=sorted(".".join(x) for x in ls - sx_nslc),
                                        only_in_stationxml=sorted(".".join(x) for x in sx_nslc - ls))
        if ls != sx_nslc:
            problems.append("scinv ls --nslc list differs from the StationXML channel codes")

    def write(name, rows):
        with open(os.path.join(args.outdir, name), "w", newline="") as fo:
            w = csv.DictWriter(fo, fieldnames=list(rows[0].keys()) if rows else ["empty"])
            w.writeheader()
            w.writerows(rows)

    write("inventory_sc_locations.csv", loc_rows)
    write("inventory_sc_streams.csv", stream_rows)
    write("inventory_sc_pick_lookup.csv", pick_rows)
    n_loc_ok = sum(r["location_equals_csv"] and r["station_equals_csv"] for r in loc_rows)
    if n_loc_ok != len(loc_rows):
        problems.append(f"{len(loc_rows) - n_loc_ok} sensor locations/stations differ from station.csv")
    open_ends = sum(1 for r in stream_rows if r.get("end_note"))
    summary.update(stations=n_sta, sensor_locations=len(loc_rows), streams=len(stream_rows),
                   stationxml_channel_epochs=len(sx), stationxml_epochs_missing=len(missing),
                   sensor_locations_equal_station_csv=n_loc_ok,
                   sensor_locations_per_station_max=max(sum(1 for r in loc_rows if r["station"] == s)
                                                        for s in {r["station"] for r in loc_rows}),
                   streams_equal_stationxml=sum(1 for r in stream_rows if r.get("in_stationxml") and not r.get("differences")),
                   streams_far_future_end_to_open=open_ends,
                   picks=len(pick_rows), picks_getSensorLocation_equal_station_csv=n_pick_ok,
                   station_start_dates=sorted({r["station_start"] for r in loc_rows})[:3],
                   problems=problems)
    with open(os.path.join(args.outdir, "inventory_sc_check_summary.json"), "w") as fo:
        json.dump(summary, fo, indent=1)
    print(f"[sc] SeisComP read {args.scml}: {summary['counts']}")
    print(f"[sc] {n_sta} stations, {len(loc_rows)} sensor locations (max {summary['sensor_locations_per_station_max']} per "
          f"station), {len(stream_rows)} streams; StationXML channel epochs {len(sx)}, missing in SeisComP XML {len(missing)}")
    print(f"[sc] Station and SensorLocation latitude/longitude/elevation equal to station.csv: {n_loc_ok}/{len(loc_rows)}")
    print(f"[sc] streams equal to their StationXML epoch (end, depth, azimuth, dip, sample rate, gain, gain frequency, "
          f"gain unit): {summary['streams_equal_stationxml']}/{len(stream_rows)}; StationXML ends in "
          f"{FAR_FUTURE_YEARS} that became open-ended: {open_ends}")
    print(f"[sc] DataModel::getSensorLocation(inv, net, sta, loc, pick time) for {len(pick_rows)} picks: "
          f"station.csv coordinates {n_pick_ok}")
    if "scinv_ls_nslc" in summary:
        print(f"[sc] 'scinv ls --nslc': {summary['scinv_ls_nslc']['n']} channel codes; equal to the StationXML codes: "
              f"{summary['scinv_ls_nslc']['equals_stationxml_codes']}")
    if args.options_json:
        with open(args.options_json, "w") as fo:
            json.dump(dict(script=os.path.abspath(__file__), run_time=datetime.datetime.now().astimezone().isoformat(),
                           argv=sys.argv, args=vars(args), PHASE_CSV=PHASE_CSV, FAR_FUTURE_YEARS=FAR_FUTURE_YEARS,
                           REL_TOL_GAIN=REL_TOL_GAIN, SEISCOMP_ROOT=os.environ.get("SEISCOMP_ROOT"),
                           python=sys.version.split()[0],
                           inputs={p: md5(p) for p in (args.scml, args.stationxml, args.station_csv, PHASE_CSV)},
                           n_problems=len(problems)), fo, indent=1)
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems[:50]))
        return 1
    print("[ok] all SeisComP-side checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
