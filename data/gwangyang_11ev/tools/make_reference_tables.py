#!/usr/bin/env python
# make_reference_tables.py
#
# Writes tidy CSV versions of the reference results, for comparing rtDD / DL-picker runs with them:
#   reference_tables/hypoinverse_kim1983.csv   HYPOINVERSE locations (1.HypoInv/kim1983/Gwangyang.sum)
#   reference_tables/hypodd_dtct.csv           HypoDD catalog-only relocation (01.dt.ct/hypoDD.reloc)
#                                              + its 1000-sample bootstrap 95% errors (01.dt.ct/bootstrap_errors.csv)
#   reference_tables/hypodd_dtcc.csv           HypoDD cross-correlation relocation (02.dt.cc/hypoDD.reloc)
#                                              + bootstrap 95% errors from 02.dt.cc/final_locations.csv
#   reference_tables/picks_phasenet_plus.csv   every PhaseNet+ pick, one row each, with channel and sensor
#   reference_tables/event_id_map.csv          byte copy of inputs/rtdd_catalog/event_id_map.csv
#
# hypoDD.reloc columns follow the HypoDD manual: ID LAT LON DEPTH X Y Z EX EY EZ YR MO DY HR MI SC MAG
# NCCP NCCS NCTP NCTS RCC RCT CID (X/Y/Z/EX/EY/EZ in metres; X east, Y north, Z down, relative to the
# cluster centroid HypoDD uses internally). Every location table also gets east_m/north_m/up_m = offsets
# from the centroid (mean latitude, longitude, depth) of that table's own 11 events.
#
# Run with the pyrtdd environment after make_rtdd_catalog.py:
#     /home/msseo/miniforge3/envs/pyrtdd/bin/python make_reference_tables.py

import glob
import os
import shutil
import sys

import numpy as np
import pandas as pd
from obspy import UTCDateTime
from obspy.geodetics import gps2dist_azimuth

# ----------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
REF = f"{DATA}/reference/gwangyang_pnplus"
CAT = f"{DATA}/inputs/rtdd_catalog"
OUT = f"{DATA}/reference_tables"
CHECKS = f"{DATA}/inputs/checks"
RELOC_COLS = ["id", "lat", "lon", "depth_km", "x_m", "y_m", "z_m", "ex_m", "ey_m", "ez_m", "yr", "mo", "dy",
              "hr", "mi", "sc", "mag", "nccp", "nccs", "nctp", "ncts", "rcc_s", "rct_s", "cid"]
S_COMPONENT, P_COMPONENT = "N", "Z"     # same channel convention as the rtDD phase.csv


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def enu_from_centroid(df, lat="latitude", lon="longitude", dep="depth_km"):
    c = (df[lat].mean(), df[lon].mean(), df[dep].mean())
    e, n = [], []
    for la, lo in zip(df[lat], df[lon]):
        d, az, _ = gps2dist_azimuth(c[0], c[1], la, lo)
        e.append(d * np.sin(np.radians(az)))
        n.append(d * np.cos(np.radians(az)))
    out = df.copy()
    out["east_m"] = np.round(e, 1)
    out["north_m"] = np.round(n, 1)
    out["up_m"] = np.round(-(df[dep] - c[2]) * 1000.0, 1)
    out["centroid_lat"], out["centroid_lon"], out["centroid_depth_km"] = round(c[0], 6), round(c[1], 6), round(c[2], 4)
    return out


def read_reloc(path):
    df = pd.read_csv(path, sep=r"\s+", header=None, names=RELOC_COLS)
    df["origin_time"] = [iso(UTCDateTime(int(r.yr), int(r.mo), int(r.dy), int(r.hr), int(r.mi)) + float(r.sc))
                         for r in df.itertuples()]
    return df


def main():
    os.makedirs(OUT, exist_ok=True)
    idmap = pd.read_csv(f"{CAT}/event_id_map.csv", dtype={"kma_id": str})
    shutil.copyfile(f"{CAT}/event_id_map.csv", f"{OUT}/event_id_map.csv")
    ids = idmap[["rtdd_id", "kma_id", "hypodd_id"]]
    # origin-time datum: HypoDD event.dat (and hence hypoDD.reloc) carries event 200002 0.01 s later than
    # the .pha/.arc origin all differential times refer to (single-precision artefact, see event_crosscheck)
    evx = pd.read_csv(f"{CHECKS}/event_crosscheck.csv", dtype={"kma_id": str})
    datum_shift = dict(zip(evx.hypodd_id, evx.d_origin_evdat_minus_pha_s))

    # --- HYPOINVERSE kim1983 -------------------------------------------------------------------
    s = pd.read_csv(f"{REF}/1.HypoInv/kim1983/Gwangyang.sum")
    s.columns = s.columns.str.strip()
    dcol = next(c for c in s.columns if c.startswith("DATE"))
    hyp = pd.DataFrame(dict(
        hypodd_id=s["ID-NUM"].astype(int),
        origin_time=[iso(UTCDateTime(str(d).strip().replace("/", "-").replace(" ", "T") + ":00") + float(sec))
                     for d, sec in zip(s[dcol], s["SEC"])],
        latitude=s["LAT"].astype(float), longitude=s["LON"].astype(float), depth_km=s["DEPTH"].astype(float),
        n_phases=s["NUM"].astype(int), gap_deg=s["GAP"].astype(int), dmin_km=s["DMIN"].astype(float),
        rms_s=s["RMS"].astype(float), erh_km=s["ERH"].astype(float), erz_km=s["ERZ"].astype(float),
        quality=s["QASR"].astype(str).str.strip()))
    hyp = enu_from_centroid(ids.merge(hyp, on="hypodd_id", how="left"))
    hyp.to_csv(f"{OUT}/hypoinverse_kim1983.csv", index=False)

    # --- HypoDD dt.ct ---------------------------------------------------------------------------
    def reloc_table(branch):
        r = read_reloc(f"{REF}/2.HypoDD/{branch}/hypoDD.reloc").rename(columns={"id": "hypodd_id", "lat": "latitude", "lon": "longitude"})
        r["origin_time_pha_datum"] = [iso(UTCDateTime(t) - datum_shift[h]) for t, h in zip(r.origin_time, r.hypodd_id)]
        t = enu_from_centroid(ids.merge(r, on="hypodd_id", how="left"))
        # HypoDD's own x/y/z are relative to its internal reference point; compare after removing the mean offset
        dx = (t.x_m - t.east_m) - (t.x_m - t.east_m).mean()
        dy = (t.y_m - t.north_m) - (t.y_m - t.north_m).mean()
        dz = (-t.z_m - t.up_m) - (-t.z_m - t.up_m).mean()
        print(f"[{branch}] HypoDD x/y/z vs computed east/north/up: mean offset "
              f"({(t.x_m - t.east_m).mean():.1f}, {(t.y_m - t.north_m).mean():.1f}, {(-t.z_m - t.up_m).mean():.1f}) m, "
              f"scatter after removing it max {max(dx.abs().max(), dy.abs().max(), dz.abs().max()):.2f} m")
        return t

    ct = reloc_table("01.dt.ct")
    bct = pd.read_csv(f"{REF}/2.HypoDD/01.dt.ct/bootstrap_errors.csv", comment="#").rename(columns={"id": "hypodd_id"})
    ct = ct.merge(bct[["hypodd_id", "n_boot", "ex95", "ey95", "ez95"]].rename(
        columns={"ex95": "boot_ex95_m", "ey95": "boot_ey95_m", "ez95": "boot_ez95_m"}), on="hypodd_id", how="left")
    ct[["boot_ex95_m", "boot_ey95_m", "boot_ez95_m"]] = ct[["boot_ex95_m", "boot_ey95_m", "boot_ez95_m"]].round(1)
    ct.to_csv(f"{OUT}/hypodd_dtct.csv", index=False)

    # --- HypoDD dt.cc + final_locations bootstrap errors ---------------------------------------
    cc = reloc_table("02.dt.cc")
    fl = pd.read_csv(f"{REF}/2.HypoDD/02.dt.cc/final_locations.csv", dtype={"event_id": str}).rename(columns={"event_id": "kma_id"})
    chk = cc.merge(fl[["kma_id", "latitude", "longitude", "depth_km"]], on="kma_id", suffixes=("", "_final"))
    print(f"[02.dt.cc] final_locations vs hypoDD.reloc: max |dlat| {(chk.latitude - chk.latitude_final).abs().max():.6f} deg, "
          f"max |dlon| {(chk.longitude - chk.longitude_final).abs().max():.6f} deg, max |ddepth| {(chk.depth_km - chk.depth_km_final).abs().max():.4f} km "
          f"(final_locations rounds to 5 decimals / 3 decimals)")
    cc = cc.merge(fl[["kma_id", "magnitude", "ex95_m", "ey95_m", "ez95_m", "n_boot", "cc_links", "ct_links", "under_constrained"]].rename(
        columns={"magnitude": "kma_ml", "ex95_m": "boot_ex95_m", "ey95_m": "boot_ey95_m", "ez95_m": "boot_ez95_m"}),
        on="kma_id", how="left")
    cc.to_csv(f"{OUT}/hypodd_dtcc.csv", index=False)

    # --- PhaseNet+ picks, tidy -----------------------------------------------------------------
    pn = pd.concat([pd.read_csv(f, dtype={"Event_ID": str}) for f in sorted(glob.glob(f"{REF}/picks/*_picks.csv"))],
                   ignore_index=True)
    st = pd.read_csv(f"{REF}/station_table/used_stations_100km.csv").set_index("Code")
    pe = pd.read_csv(f"{CAT}/phase_extra.csv", dtype={"kmaId": str})
    used = set(zip(pe.kmaId, pe.stationCode, pe.type))
    pha_time = dict(zip(zip(pe.kmaId, pe.stationCode, pe.type), pe.isotime))
    ev0 = pd.read_csv(f"{CAT}/event.csv").set_index("id")
    rt = dict(zip(idmap.kma_id, idmap.rtdd_id))
    pk = pd.DataFrame(dict(
        rtdd_id=pn.Event_ID.map(rt), kma_id=pn.Event_ID, hypodd_id=pn.Event_ID.map(dict(zip(idmap.kma_id, idmap.hypodd_id))),
        network=pn.Network, station=pn.Station, location="", sensor=pn.Station.map(st.Sensor),
        phase=pn.Phase, time=[iso(UTCDateTime(t)) for t in pn.Time], probability=pn.Probability,
        polarity=pn.Polarity, amplitude=pn.Amplitude))
    pk["channel"] = pk.sensor + np.where(pk.phase == "P", P_COMPONENT, S_COMPONENT)
    pk["epi_dist_km"] = [round(gps2dist_azimuth(ev0.loc[r.rtdd_id, "latitude"], ev0.loc[r.rtdd_id, "longitude"],
                                                st.loc[r.station, "Latitude"], st.loc[r.station, "Longitude"])[0] / 1000, 2)
                         for r in pk.itertuples()]
    pk["used_by_ph2dt"] = [(k, s_, p) in used for k, s_, p in zip(pk.kma_id, pk.station, pk.phase)]
    pk["pha_time"] = [pha_time.get((k, s_, p), "") for k, s_, p in zip(pk.kma_id, pk.station, pk.phase)]
    pk["pha_minus_phasenet_ms"] = [round((UTCDateTime(a) - UTCDateTime(b)) * 1000, 3) if a else np.nan
                                   for a, b in zip(pk.pha_time, pk.time)]
    cols = ["rtdd_id", "kma_id", "hypodd_id", "network", "station", "location", "channel", "sensor", "phase", "time",
            "probability", "polarity", "amplitude", "epi_dist_km", "used_by_ph2dt", "pha_time", "pha_minus_phasenet_ms"]
    pk = pk[cols].sort_values(["rtdd_id", "epi_dist_km", "station", "phase"]).reset_index(drop=True)
    pk.to_csv(f"{OUT}/picks_phasenet_plus.csv", index=False)

    print(f"[write] {OUT}: hypoinverse_kim1983.csv ({len(hyp)}), hypodd_dtct.csv ({len(ct)}), hypodd_dtcc.csv ({len(cc)}), "
          f"picks_phasenet_plus.csv ({len(pk)} picks: {int((pk.phase == 'P').sum())} P, {int((pk.phase == 'S').sum())} S; "
          f"used by ph2dt {int(pk.used_by_ph2dt.sum())}), event_id_map.csv")
    for name, t in (("hypoinverse_kim1983", hyp), ("hypodd_dtct", ct), ("hypodd_dtcc", cc)):
        rad = np.hypot(t.east_m, t.north_m)
        print(f"[{name}] centroid {t.centroid_lat.iloc[0]:.5f} N {t.centroid_lon.iloc[0]:.5f} E "
              f"{t.centroid_depth_km.iloc[0]:.3f} km; max horizontal distance from centroid {rad.max():.0f} m; "
              f"depth range {t.depth_km.min():.3f}-{t.depth_km.max():.3f} km")
    return 0


if __name__ == "__main__":
    sys.exit(main())
