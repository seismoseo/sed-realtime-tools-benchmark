#!/usr/bin/env python
# check_stations_rtdd_xml.py  --  step Prep (install/06_gwangyang_prep.sh, stage validate)
#
# Independent checks of data/gwangyang_11ev/inputs/stations_rtdd.xml (written by make_stations_rtdd_xml.py):
#
#  1. FDSN StationXML schema (obspy's validator) and an obspy read.
#  2. Epoch coverage: each of the 1656 SAC files (162 channels x their events) must be covered by exactly one
#     channel epoch AND by its station epoch.
#  3. The coordinate path pyrtdd uses when it builds a catalog from obspy objects
#     (pyrtdd/obspy/catalog.py: inventory.get_coordinates("NET.STA.LOC.CHA", pick time)): for all 763 catalog
#     picks (inputs/rtdd_catalog/phase.csv, P on <sensor>Z, S on <sensor>N) the coordinates returned must equal
#     inputs/rtdd_catalog/station.csv exactly.
#  4. NonLinLoc kim1983 grids through pyrtdd.hdd.NLLGrid (the libhdd reader scrtdd itself uses) for all 54
#     stations, with the coordinates READ BACK from stations_rtdd.xml, at maxSearchDistance 0.1 m (libhdd/pyrtdd
#     default) and 10 m (scrtdd plugin default, plugins/ttt/nll/nll_ttt.cpp:142): P and S travel times at the
#     HypoDD starting centroid. Which grid was found is identified (a) by the grid header positions (nearest and
#     second-nearest grid, own projection) and (b) by matching the returned time with each station's own grid
#     time. KWJU and KWJ2 share latitude/longitude and are 11 m apart in elevation: each must find its own grid.
#     For contrast, the same lookups with the ORIGINAL coordinates of the source inventories
#     (inputs/checks/inventory_coordinate_changes.csv) show what would have happened without the replacement.
#
# Run with env pyrtdd:  python check_stations_rtdd_xml.py --xml <stations_rtdd.xml> --outdir <dir> --options-json <json>

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager

import numpy as np
import obspy
import pandas as pd
import pyproj
from obspy import UTCDateTime, read_inventory
from obspy.io.stationxml.core import validate_stationxml

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
STATION_CSV = f"{DATA}/inputs/rtdd_catalog/station.csv"
PHASE_CSV = f"{DATA}/inputs/rtdd_catalog/phase.csv"
CENTROID_CSV = f"{DATA}/inputs/rtdd_catalog/event_centroid_start.csv"   # HypoDD ISTART=1 start (all events)
MANIFEST = f"{DATA}/inputs/checks/waveform_manifest.csv"
CHANGES = f"{DATA}/inputs/checks/inventory_coordinate_changes.csv"       # original coordinates (contrast test)
GRID_PATH = f"{DATA}/inputs/nll_kim1983/time"                           # NLLGrid gridPath
GRID_MODEL = "kim1983"                                                  # NLLGrid gridModel
GRID_VALIDATION = f"{DATA}/inputs/nll_kim1983/validation.csv"           # step C1 grid times (station.csv coords)
C1_CENTROID = (35.0000, 127.7286, 13.94)  # point where step C1 evaluated validation.csv (install/02_validate_nll_grids.py:49)
MAX_SEARCH_M = (0.1, 10.0)        # libhdd/pyrtdd default; scrtdd plugin default ttt.NLLGrid.<model>.maxSearchDistance
PHASES = ("P", "S")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@contextmanager
def capture_fd2(out):
    # libhdd (C++ inside pyrtdd) logs its warnings straight to file descriptor 2, e.g.
    # "Cannot find a suitable P time grid (...). Closest grid is at 562 [m] <file>": keep them per lookup
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


def covers(ep, a, b):
    return (ep.start_date is None or ep.start_date <= a) and (ep.end_date is None or ep.end_date >= b)


def read_grid_headers(path, model):
    # station label and source position (km, NLL transverse-Mercator frame) of every <model>.<P|S>.<STA>.time.hdr
    rows = []
    for f in sorted(glob.glob(os.path.join(path, f"{model}.*.*.time.hdr"))):
        lines = open(f).read().splitlines()
        ph, sta = os.path.basename(f).split(".")[1:3]
        lab, x, y, z = lines[1].split()[:4]
        m = re.search(r"TRANS_MERC RefEllipsoid (\S+)\s+LatOrig (\S+)\s+LongOrig (\S+)", lines[2])
        rows.append(dict(phase=ph, file_station=sta, label=lab, x_km=float(x), y_km=float(y), z_km=float(z),
                         ellps=m.group(1), lat0=float(m.group(2)), lon0=float(m.group(3)), hdr=f))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--options-json", default=None)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    summary, problems = {}, []

    # ------------------------------------------------------------------ 1. schema + read
    valid, errors = validate_stationxml(args.xml)
    inv = read_inventory(args.xml)
    nsta = sum(len(n.stations) for n in inv)
    nep = sum(len(s.channels) for n in inv for s in n)
    nslc = sorted({(n.code, s.code, c.location_code, c.code) for n in inv for s in n for c in s})
    summary["schema_valid"] = bool(valid)
    summary["schema_errors"] = [str(e) for e in errors]
    summary.update(networks=len(inv.networks), stations=nsta, channel_epochs=nep, channel_codes=len(nslc))
    print(f"[1] schema valid: {valid} ({len(errors)} errors); obspy read: {len(inv.networks)} network(s), "
          f"{nsta} stations, {len(nslc)} channel codes, {nep} channel epochs")
    if not valid:
        problems.append(f"schema errors: {errors}")

    # ------------------------------------------------------------------ 2. SAC epoch coverage
    man = pd.read_csv(MANIFEST, dtype={"kma_id": str, "loc": str, "net": str, "sta": str, "cha": str},
                      keep_default_na=False)
    rows = []
    for fr in man.itertuples():
        a, b = UTCDateTime(fr.starttime), UTCDateTime(fr.endtime)
        stas = [s for n in inv if n.code == fr.net for s in n if s.code == fr.sta]
        eps = [c for s in stas for c in s if c.location_code == fr.loc and c.code == fr.cha and covers(c, a, b)]
        rows.append(dict(kma_id=fr.kma_id, nslc=f"{fr.net}.{fr.sta}.{fr.loc}.{fr.cha}", starttime=fr.starttime,
                         endtime=fr.endtime, n_channel_epochs_covering=len(eps),
                         station_epoch_covers=any(covers(s, a, b) for s in stas),
                         epoch_start=str(eps[0].start_date) if len(eps) == 1 else "",
                         epoch_end=(str(eps[0].end_date) if eps[0].end_date else "open") if len(eps) == 1 else "",
                         sensor=(eps[0].sensor.model if len(eps) == 1 and eps[0].sensor else "")))
    cov = pd.DataFrame(rows)
    cov.to_csv(f"{args.outdir}/sac_epoch_coverage.csv", index=False)
    n_ok = int(((cov.n_channel_epochs_covering == 1) & cov.station_epoch_covers).sum())
    sac_nslc = sorted(set(zip(man.net, man.sta, man["loc"], man.cha)))
    summary.update(sac_files=len(cov), sac_channels=len(sac_nslc), sac_files_covered_once=n_ok,
                   channel_codes_equal_sac_set=(nslc == sac_nslc))
    print(f"[2] SAC files covered by exactly one channel epoch and by the station epoch: {n_ok}/{len(cov)} "
          f"({len(sac_nslc)} channels); channel codes in the file == SAC set: {nslc == sac_nslc}")
    if n_ok != len(cov) or nslc != sac_nslc:
        problems.append("SAC coverage / channel set check failed")

    # ------------------------------------------------------------------ 3. pyrtdd's coordinate path for every pick
    st = pd.read_csv(STATION_CSV, dtype={"networkCode": str, "stationCode": str, "locationCode": str},
                     keep_default_na=False)
    st_by = {(r.networkCode, r.stationCode, r.locationCode): (float(r.latitude), float(r.longitude), float(r.elevation))
             for r in st.itertuples()}
    ph = pd.read_csv(PHASE_CSV, dtype={"networkCode": str, "stationCode": str, "locationCode": str,
                                       "channelCode": str}, keep_default_na=False)
    prow = []
    for p in ph.itertuples():
        seed = f"{p.networkCode}.{p.stationCode}.{p.locationCode}.{p.channelCode}"
        try:
            c = inv.get_coordinates(seed, UTCDateTime(p.isotime))
            got = (c["latitude"], c["longitude"], c["elevation"])
            err = ""
        except Exception as e:      # noqa: BLE001 -- reported, not hidden
            got, err = (np.nan, np.nan, np.nan), str(e)
        want = st_by[(p.networkCode, p.stationCode, p.locationCode)]
        prow.append(dict(eventId=p.eventId, seed_id=seed, type=p.type, isotime=p.isotime, latitude=got[0],
                         longitude=got[1], elevation=got[2], local_depth=(c["local_depth"] if not err else np.nan),
                         equals_station_csv=(got == want), error=err))
    pc = pd.DataFrame(prow)
    pc.to_csv(f"{args.outdir}/pick_coordinates_check.csv", index=False)
    summary.update(picks=len(pc), picks_coordinates_equal_station_csv=int(pc.equals_station_csv.sum()),
                   picks_coordinate_errors=int((pc.error != "").sum()))
    print(f"[3] inventory.get_coordinates(seed id, pick time) for the {len(pc)} catalog picks: equal to station.csv "
          f"{int(pc.equals_station_csv.sum())}, errors {int((pc.error != '').sum())}")
    if pc.equals_station_csv.sum() != len(pc):
        problems.append("pick coordinate check failed")

    # ------------------------------------------------------------------ 4. NLLGrid lookups
    from pyrtdd.hdd import NLLGrid
    cen = pd.read_csv(CENTROID_CSV).iloc[0]
    clat, clon, cdep = float(cen.latitude), float(cen.longitude), float(cen.depth)
    hdr = read_grid_headers(GRID_PATH, GRID_MODEL)
    if len(set(zip(hdr.ellps, hdr.lat0, hdr.lon0))) != 1:
        sys.exit("ERROR: grids use different projections")
    ellps, lat0, lon0 = hdr.ellps.iloc[0], hdr.lat0.iloc[0], hdr.lon0.iloc[0]
    tm = pyproj.Proj(proj="tmerc", lat_0=lat0, lon_0=lon0, k=1.0, x_0=0.0, y_0=0.0,
                     ellps={"WGS-84": "WGS84"}.get(ellps, ellps))
    grids = {d: NLLGrid(gridPath=GRID_PATH, gridModel=GRID_MODEL, maxSearchDistance=d) for d in MAX_SEARCH_M}
    # coordinates read back from the file: every channel epoch and the station element of each station
    xml_coords = {}
    for n in inv:
        for s in n:
            cs = {(float(c.latitude), float(c.longitude), float(c.elevation)) for c in s}
            cs.add((float(s.latitude), float(s.longitude), float(s.elevation)))
            if len(cs) != 1:
                problems.append(f"{s.code}: station/channel coordinates differ inside the file: {cs}")
            xml_coords[(n.code, s.code, s[0].location_code)] = next(iter(cs))
    chg = pd.read_csv(CHANGES, dtype={"network": str, "station": str, "location": str}, keep_default_na=False)
    orig = {(r.network, r.station, r.location): (r.orig_latitude, r.orig_longitude, r.orig_elevation_m)
            for r in chg[chg.level == "station"].itertuples()}

    def lookup(coords, phase, d, at=None):
        elat, elon, edep = at or (clat, clon, cdep)
        cap = {}
        with capture_fd2(cap):
            try:
                t, err = grids[d].compute(elat, elon, edep, coords[0], coords[1], coords[2], phase), ""
            except Exception as e:      # noqa: BLE001 -- reported in the table
                t, err = np.nan, str(e)
        warn = " | ".join(sorted({l.split("] ", 1)[-1].strip() for l in cap["text"].splitlines() if l.strip()}))
        if warn:
            err = (err + " || libhdd: " + warn).strip()
        return t, err

    # each station's own-grid time (new coordinates, 0.1 m): the reference for identifying which grid answered
    own_time = {}
    for key, xyz in xml_coords.items():
        for phase in PHASES:
            own_time[(key[1], phase)] = lookup(xyz, phase, MAX_SEARCH_M[0])[0]
    val = pd.read_csv(GRID_VALIDATION).set_index("Code")
    nrows = []
    for coord_set in ("stations_rtdd.xml", "original (source inventory)"):
        for key in sorted(xml_coords):
            xyz = xml_coords[key] if coord_set == "stations_rtdd.xml" else orig[key]
            x, y = tm(xyz[1], xyz[0])
            for phase in PHASES:
                h = hdr[hdr.phase == phase]
                dist = np.sqrt((h.x_km - x / 1000.0) ** 2 + (h.y_km - y / 1000.0) ** 2 + (h.z_km + xyz[2] / 1000.0) ** 2) * 1000.0
                order = np.argsort(dist.values)
                near, second = h.iloc[order[0]], h.iloc[order[1]]
                r = dict(coordinates=coord_set, network=key[0], station=key[1], location=key[2], phase=phase,
                         latitude=xyz[0], longitude=xyz[1], elevation_m=xyz[2],
                         nearest_grid=near.label, nearest_grid_dist_m=round(float(dist.values[order[0]]), 3),
                         second_grid=second.label, second_grid_dist_m=round(float(dist.values[order[1]]), 3),
                         own_grid_dist_m=round(float(dist[h.label == key[1]].iloc[0]), 3))
                for d in MAX_SEARCH_M:
                    t, err = lookup(xyz, phase, d)
                    same = [k[0] for k, v in own_time.items() if k[1] == phase and np.isfinite(t) and v == t]
                    r[f"time_s_{d:g}m"] = t
                    r[f"ok_{d:g}m"] = bool(np.isfinite(t))
                    r[f"grid_found_{d:g}m"] = " ".join(same) if same else ("" if not np.isfinite(t) else "?")
                    r[f"error_{d:g}m"] = err
                if coord_set == "stations_rtdd.xml":
                    # same lookup at the point where step C1 evaluated its validation.csv (station.csv coordinates)
                    r["time_s_at_c1_point_10m"] = lookup(xyz, phase, MAX_SEARCH_M[1], at=C1_CENTROID)[0]
                    r["c1_validation_time_s"] = float(val.loc[key[1], f"{phase}_grid_s"])
                nrows.append(r)
    nl = pd.DataFrame(nrows)
    nl.to_csv(f"{args.outdir}/nll_lookup.csv", index=False)
    new = nl[nl.coordinates == "stations_rtdd.xml"]
    old = nl[nl.coordinates != "stations_rtdd.xml"]
    for label, df in (("stations_rtdd.xml", new), ("original", old)):
        for d in MAX_SEARCH_M:
            okc = df[f"ok_{d:g}m"]
            own = df[f"grid_found_{d:g}m"] == df.station
            wrong = okc & ~own
            summary[f"nll_{label}_{d:g}m"] = dict(lookups=len(df), succeeded=int(okc.sum()), own_grid=int(own.sum()),
                                                  wrong_grid=int(wrong.sum()),
                                                  wrong_grid_list=sorted(set(df[wrong].station + "->" + df[wrong][f"grid_found_{d:g}m"])))
            print(f"[4] {label:18s} coordinates, maxSearchDistance {d:>4g} m: {int(okc.sum())}/{len(df)} lookups found a grid; "
                  f"own grid {int(own.sum())}; another station's grid {int(wrong.sum())} "
                  f"{sorted(set(df[wrong].station + '->' + df[wrong][f'grid_found_{d:g}m']))}")
    tdiff = (new["time_s_0.1m"] - new["time_s_10m"]).abs().max()
    vdiff = (new.time_s_at_c1_point_10m - new.c1_validation_time_s).abs().max()
    nwarn = int(nl[[c for c in nl.columns if c.startswith("error_")]].apply(lambda x: x.str.contains("libhdd")).sum().sum())
    print(f"[4] libhdd warnings caught during the lookups: {nwarn} (all for failed lookups; text in nll_lookup.csv error_* columns)")
    summary.update(nll_new_time_diff_0p1_vs_10m_s=float(tdiff), nll_new_vs_c1_validation_max_abs_s=float(vdiff),
                   nll_new_nearest_is_own=int((new.nearest_grid == new.station).sum()),
                   nll_new_max_own_grid_dist_m=float(new.own_grid_dist_m.max()),
                   nll_new_min_second_grid_dist_m=float(new.second_grid_dist_m.min()))
    print(f"[4] stations_rtdd.xml coordinates: nearest grid is the station's own for "
          f"{int((new.nearest_grid == new.station).sum())}/{len(new)} lookups; own grid at <= "
          f"{new.own_grid_dist_m.max():.3f} m (own projection); next grid >= {new.second_grid_dist_m.min():.1f} m away; "
          f"times at 0.1 m vs 10 m: max |diff| {tdiff:.3g} s; at the step C1 check point {C1_CENTROID} vs C1 "
          f"validation.csv (made with station.csv coordinates): max |diff| {vdiff:.2g} s (that file has 6 decimals)")
    for label, df in (("stations_rtdd.xml", new), ("original", old)):
        for r in df[df.station.isin(["KWJU", "KWJ2"])].to_dict("records"):
            print(f"      {label:18s} {r['station']} {r['phase']}: elevation {r['elevation_m']:g} m -> grid found at 10 m: "
                  f"{r['grid_found_10m'] or 'none'}, at 0.1 m: {r['grid_found_0.1m'] or 'none'} "
                  f"(t = {r['time_s_10m']:.6f} s); own grid {r['own_grid_dist_m']} m away, "
                  f"nearest {r['nearest_grid']} {r['nearest_grid_dist_m']} m, second {r['second_grid']} {r['second_grid_dist_m']} m")
    for d in MAX_SEARCH_M:
        if summary[f"nll_stations_rtdd.xml_{d:g}m"]["own_grid"] != len(new):
            problems.append(f"NLLGrid lookups with stations_rtdd.xml coordinates at {d:g} m did not all find the own grid")
    if tdiff != 0 or vdiff > 2e-6:
        problems.append("NLLGrid times differ between tolerances or from the step C1 validation")

    summary["problems"] = problems
    with open(f"{args.outdir}/validate_summary.json", "w") as fo:
        json.dump(summary, fo, indent=1, default=str)
    if args.options_json:
        doc = NLLGrid.__init__.__doc__ or ""
        defaults = dict(re.findall(r"(\w+): [^=,)]+= ([^,)]+)", doc))
        json.dump(dict(
            script=os.path.abspath(__file__), run_time=datetime.datetime.now().astimezone().isoformat(),
            argv=sys.argv, args=vars(args), STATION_CSV=STATION_CSV, PHASE_CSV=PHASE_CSV, CENTROID_CSV=CENTROID_CSV,
            centroid=dict(latitude=clat, longitude=clon, depth_km=cdep), C1_CENTROID=C1_CENTROID,
            GRID_VALIDATION=GRID_VALIDATION, MANIFEST=MANIFEST, CHANGES=CHANGES,
            NLLGrid=dict(gridPath=GRID_PATH, gridModel=GRID_MODEL, maxSearchDistance_values_m=list(MAX_SEARCH_M),
                         constructor_signature=doc.strip(), constructor_defaults_from_signature=defaults),
            projection_for_own_grid_check=dict(proj="tmerc", lat_0=lat0, lon_0=lon0, k=1.0, ellps=ellps),
            inputs={p: md5(p) for p in (args.xml, STATION_CSV, PHASE_CSV, CENTROID_CSV, MANIFEST, CHANGES)},
            versions=dict(python=sys.version.split()[0], obspy=obspy.__version__, pandas=pd.__version__,
                          numpy=np.__version__, pyproj=pyproj.__version__),
            n_problems=len(problems)), open(args.options_json, "w"), indent=1, default=str)
        print(f"[options] {args.options_json}")
    print(f"[summary] {args.outdir}/validate_summary.json")
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("[ok] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
