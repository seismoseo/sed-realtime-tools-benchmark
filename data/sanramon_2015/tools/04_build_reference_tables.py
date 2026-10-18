# 04_build_reference_tables.py -- turn the raw NCEDC / LDEO downloads into tidy tables and match
# the routine (NCSS) catalog to the double-difference (DD) catalogs by event id.
#
# Inputs (written by tools 02 and 03):
#   reference/ncedc_catalog/txt/ncphraw_wide_*.txt   NCSS summary + phase lines (Hypoinverse archive)
#   reference/ncedc_catalog/txt/nccsv_wide_*.txt     NCSS catalog csv (cross-check of the parser)
#   reference/ncedc_catalog/txt/ddcsv_wide_*.txt     NCEDC DD catalog csv (positions, 5 decimals)
#   reference/ncedc_catalog/txt/ddread_box_*.txt     NCEDC DD readable (cross-check)
#   reference/ncedc_catalog/txt/ddraw_box_*.txt      NCEDC DD Hypoinverse summary (version, ERZ field)
#   reference/ldeo/NCAeqDD.v202112.1.gz              LDEO DD base catalog 1984-2021 (geoid depths)
# Outputs (reference_tables/):
#   dd_catalog.csv           NCEDC DD events in the wide box (flag in_box = DD location in benchmark box)
#   ldeo_dd_catalog.csv      LDEO NCAeqDD.v202112.1 events in the wide box and period
#   ncss_catalog.csv         NCSS routine events in the wide box with depth datum, errors, pick counts
#   picks_ncss.csv           one row per NCSS P or S pick (amplitude-only lines are left out)
#   event_matching.csv       every id seen in any catalog, with membership flags
#   location_differences.csv per matched event: NCSS-DD and NCEDC_DD-LDEO_DD shifts (km)
#   stats_04.json            counts used in docs/sanramon_inputs.md
# Usage: python -I 04_build_reference_tables.py

import csv
import glob
import gzip
import io
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hypoinverse_archive as H  # noqa: E402
import sr_common as C  # noqa: E402

TXT = os.path.join(C.REF, "ncedc_catalog", "txt")
BOX = dict(lat0=37.75, lat1=37.83, lon0=-122.01, lon1=-121.91)
WIDE = dict(lat0=37.70, lat1=37.88, lon0=-122.06, lon1=-121.86)
T0, T1 = pd.Timestamp("2015-10-01"), pd.Timestamp("2015-12-01")


def in_box(lat, lon, b):
    return (lat >= b["lat0"]) & (lat <= b["lat1"]) & (lon >= b["lon0"]) & (lon <= b["lon1"])


def iso(t, nd=2):
    """datetime -> 'YYYY-MM-DDThh:mm:ss.ffZ' with nd decimals (rounded, not truncated)."""
    t = pd.Timestamp(t).round(f"{10 ** (3 - nd)}ms") if nd < 3 else pd.Timestamp(t)
    s = t.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return s[: len(s) - 6 + nd] + "Z"


def one(pattern):
    f = sorted(glob.glob(os.path.join(TXT, pattern)))
    assert len(f) == 1, (pattern, f)
    return f[0]


def read_ncedc_csv(path):
    df = pd.read_csv(path, skip_blank_lines=True)
    df["origin_time"] = pd.to_datetime(df["DateTime"], format="%Y/%m/%d %H:%M:%S.%f")
    return df


def dist_km(lat1, lon1, lat2, lon2):
    """local flat-earth distance components (east, north) in km; fine for < 20 km."""
    R = 6371.0
    lat_m = np.radians((np.asarray(lat1) + np.asarray(lat2)) / 2)
    dn = np.radians(np.asarray(lat2) - np.asarray(lat1)) * R
    de = np.radians(np.asarray(lon2) - np.asarray(lon1)) * R * np.cos(lat_m)
    return de, dn


def main():
    os.makedirs(C.TAB, exist_ok=True)
    stats = {}

    # ---------------- NCSS routine catalog + picks (Hypoinverse archive) ----------------
    events, pick_rows, n_amp_lines, n_other_lines = [], [], 0, 0
    for f in sorted(glob.glob(os.path.join(TXT, "ncphraw_wide_*.txt"))):
        for summ, phases, term_id in H.read_archive(open(f).read()):
            assert term_id == summ["event_id"], (f, summ["event_id"], term_id)
            events.append(summ)
            for ph in phases:
                picks = H.phase_picks(ph)
                is_amp_line = (ph["p_remark"] == "P" and ph["p_weight_code"] == 4
                               and ph["data_source"] == "" and not ph["has_s_field"])
                if is_amp_line:
                    n_amp_lines += 1      # amplitude reading with a placeholder 'P' time: not a pick
                    continue
                if not picks:
                    n_other_lines += 1
                    continue
                for pk in picks:
                    pick_rows.append(dict(
                        event_id=summ["event_id"], phase=pk["phase"], time_utc=iso(pk["time"]),
                        network=ph["network"], station=ph["station"], location=ph["location"],
                        location_raw=ph["location_raw"], channel=ph["channel"],
                        onset=pk["onset"], remark=pk["remark"], first_motion=pk["first_motion"],
                        weight_code=pk["weight_code"], weight_used=pk["weight_used"],
                        residual_s=pk["residual"], epi_dist_km=ph["epi_dist_km"],
                        azimuth_deg=ph["azimuth_deg"], takeoff_deg=ph["takeoff_deg"],
                        data_source=ph["data_source"]))
    ev = pd.DataFrame(events)
    pk = pd.DataFrame(pick_rows)
    assert ev["event_id"].is_unique
    # depth datum: reported depth (cols 32-36) is the geoid depth for depth_type G; the model depth
    # (depth below the flat top of the Hypoinverse CRT model) = geoid depth + datum elevation.
    ev["depth_geoid_km"] = ev["depth_km"]
    ev["depth_model_km"] = ev["depth_geoid_km"] + ev["depth_datum_m"] / 1000.0
    ev["in_box"] = in_box(ev.latitude, ev.longitude, BOX)
    pk["usable"] = pk["weight_code"].between(0, 3)   # 4 = no weight, 5-9 = out-weighted by NCSS
    # ---- cross-check the summary parser against NCEDC's own csv conversion
    cc = read_ncedc_csv(one("nccsv_wide_*.txt"))
    m = ev.merge(cc, left_on="event_id", right_on="EventID", how="outer", indicator=True)
    both = m[m["_merge"] == "both"]
    stats["ncss_parser_check"] = dict(
        n_archive=int(len(ev)), n_csv=int(len(cc)), n_both=int(len(both)),
        max_dlat_deg=float((both.latitude - both.Latitude).abs().max()),
        max_dlon_deg=float((both.longitude - both.Longitude).abs().max()),
        max_ddepth_km=float((both.depth_km - both.Depth).abs().max()),
        max_dt_s=float((both.origin_time_x - both.origin_time_y).abs().max().total_seconds()),
        max_dmag=float((both.pref_mag - both.Magnitude).abs().max()))

    # ---------------- NCEDC DD catalog ----------------
    dd = read_ncedc_csv(one("ddcsv_wide_*.txt"))
    dd = dd.rename(columns={"EventID": "event_id", "Latitude": "latitude", "Longitude": "longitude",
                            "Depth": "depth_km", "Magnitude": "magnitude", "MagType": "mag_type",
                            "Source": "source"})
    dd["in_box"] = in_box(dd.latitude, dd.longitude, BOX)
    ddbox = read_ncedc_csv(one("ddcsv_box_*.txt"))
    stats["ncedc_dd_box_csv_n"] = int(len(ddbox))
    stats["ncedc_dd_box_from_wide_n"] = int(dd.in_box.sum())
    assert set(ddbox.EventID) == set(dd.loc[dd.in_box, "event_id"]), "box/wide DD mismatch"
    # readable format: same numbers?
    rlines =[ln for ln in open(one("ddread_box_*.txt")).read().splitlines()
              if ln[:4].isdigit()]
    rd = pd.DataFrame([dict(event_id=int(ln.split()[-1]), lat=float(ln.split()[2]),
                            lon=float(ln.split()[3]), dep=float(ln.split()[4]))
                       for ln in rlines])
    mr = dd.merge(rd, on="event_id")
    stats["ddread_vs_ddcsv"] = dict(n=int(len(mr)),
                                    max_dlat=float((mr.lat - mr.latitude).abs().max()),
                                    max_dlon=float((mr.lon - mr.longitude).abs().max()),
                                    max_ddep=float((mr.dep - mr.depth_km).abs().max()))
    raw = [H.parse_summary(ln) for ln in open(one("ddraw_box_*.txt")).read().splitlines()
           if ln.strip()]
    rawdf = pd.DataFrame(raw)[["event_id", "version", "review_version", "erh_km", "erz_km",
                               "latitude", "longitude", "depth_km"]]
    rawdf = rawdf.rename(columns={"version": "ddraw_version", "review_version": "ddraw_review",
                                  "erh_km": "ddraw_erh_field_km", "erz_km": "ddraw_erz_field_km",
                                  "latitude": "ddraw_lat", "longitude": "ddraw_lon",
                                  "depth_km": "ddraw_depth_km"})
    dd = dd.merge(rawdf, on="event_id", how="left")
    stats["ddraw_vs_ddcsv_max_dhoriz_m"] = float(np.nanmax(np.hypot(
        *dist_km(dd.latitude, dd.longitude, dd.ddraw_lat, dd.ddraw_lon))) * 1000)
    stats["ddraw_erh_field_values"] = sorted(set(dd["ddraw_erh_field_km"].dropna().tolist()))
    stats["ddraw_erz_field_range_km"] = [float(dd.ddraw_erz_field_km.min()),
                                         float(dd.ddraw_erz_field_km.median()),
                                         float(dd.ddraw_erz_field_km.max())]
    dd["origin_time_utc"] = dd["origin_time"].map(iso)
    dd_out = dd[["event_id", "origin_time_utc", "latitude", "longitude", "depth_km", "magnitude",
                 "mag_type", "source", "in_box", "ddraw_version", "ddraw_review",
                 "ddraw_erh_field_km", "ddraw_erz_field_km"]].sort_values("origin_time_utc")
    dd_out.to_csv(os.path.join(C.TAB, "dd_catalog.csv"), index=False, float_format="%.5f")

    # ---------------- LDEO NCAeqDD.v202112.1 (geoid depths, bootstrap errors) ----------------
    rows = []
    with gzip.open(os.path.join(C.REF, "ldeo", "NCAeqDD.v202112.1.gz"), "rt") as f:
        for ln in f:
            p = ln.split()
            if len(p) != 15 or not p[0].isdigit() or len(p[0]) != 4:
                continue
            lat, lon = float(p[6]), float(p[7])
            if not (WIDE["lat0"] <= lat <= WIDE["lat1"] and WIDE["lon0"] <= lon <= WIDE["lon1"]):
                continue
            t = pd.Timestamp(f"{p[0]}-{p[1]}-{p[2]}T{p[3]}:{p[4]}:00") + pd.Timedelta(seconds=float(p[5]))
            if not (T0 <= t < T1):
                continue
            rows.append(dict(event_id=int(p[14]), origin_time=t, latitude=lat, longitude=lon,
                             depth_km=float(p[8]), eh1_km=float(p[9]), eh2_km=float(p[10]),
                             az_deg=float(p[11]), ez_km=float(p[12]), magnitude=float(p[13])))
    ld = pd.DataFrame(rows)
    ld["in_box"] = in_box(ld.latitude, ld.longitude, BOX)
    ld["origin_time_utc"] = ld["origin_time"].map(lambda t: iso(t, 3))
    ld[["event_id", "origin_time_utc", "latitude", "longitude", "depth_km", "eh1_km", "eh2_km",
        "az_deg", "ez_km", "magnitude", "in_box"]].sort_values("origin_time_utc").to_csv(
        os.path.join(C.TAB, "ldeo_dd_catalog.csv"), index=False, float_format="%.5f")

    # ---------------- id matching ----------------
    ids = sorted(set(ev.event_id) | set(dd.event_id) | set(ld.event_id))
    em = pd.DataFrame(dict(event_id=ids))
    em["in_ncss"] = em.event_id.isin(ev.event_id)
    em["ncss_in_box"] = em.event_id.isin(ev.loc[ev.in_box, "event_id"])
    em["in_ncedc_dd"] = em.event_id.isin(dd.event_id)
    em["ncedc_dd_in_box"] = em.event_id.isin(dd.loc[dd.in_box, "event_id"])
    em["in_ldeo_dd"] = em.event_id.isin(ld.event_id)
    em["ldeo_dd_in_box"] = em.event_id.isin(ld.loc[ld.in_box, "event_id"])
    em["benchmark_event"] = em.in_ncss & (em.ncss_in_box | em.ncedc_dd_in_box | em.ldeo_dd_in_box)
    em.to_csv(os.path.join(C.TAB, "event_matching.csv"), index=False)
    stats["matching"] = dict(
        ncss_wide=int(em.in_ncss.sum()), ncss_box=int(em.ncss_in_box.sum()),
        ncedc_dd_wide=int(em.in_ncedc_dd.sum()), ncedc_dd_box=int(em.ncedc_dd_in_box.sum()),
        ldeo_dd_wide=int(em.in_ldeo_dd.sum()), ldeo_dd_box=int(em.ldeo_dd_in_box.sum()),
        ncedc_dd_box_not_in_ncss=em.loc[em.ncedc_dd_in_box & ~em.in_ncss, "event_id"].tolist(),
        ncss_box_not_in_ncedc_dd=em.loc[em.ncss_in_box & ~em.in_ncedc_dd, "event_id"].tolist(),
        ldeo_dd_box_not_in_ncss=em.loc[em.ldeo_dd_in_box & ~em.in_ncss, "event_id"].tolist(),
        ncss_box_not_in_ldeo_dd=em.loc[em.ncss_in_box & ~em.in_ldeo_dd, "event_id"].tolist(),
        ncedc_dd_box_not_in_ldeo=em.loc[em.ncedc_dd_in_box & ~em.in_ldeo_dd, "event_id"].tolist(),
        ldeo_box_not_in_ncedc_dd=em.loc[em.ldeo_dd_in_box & ~em.in_ncedc_dd, "event_id"].tolist(),
        ncss_box_dd_outside_box=em.loc[em.ncss_in_box & em.in_ncedc_dd & ~em.ncedc_dd_in_box,
                                       "event_id"].tolist(),
        dd_box_ncss_outside_box=em.loc[em.ncedc_dd_in_box & em.in_ncss & ~em.ncss_in_box,
                                       "event_id"].tolist(),
        benchmark_events=int(em.benchmark_event.sum()))

    # ---------------- per-event pick counts and NCSS table ----------------
    use = pk[pk.usable]
    cnt = use.groupby(["event_id", "phase"]).size().unstack(fill_value=0)
    cnt_all = pk.groupby(["event_id", "phase"]).size().unstack(fill_value=0)
    ev = ev.merge(cnt.rename(columns={"P": "n_P_usable", "S": "n_S_usable"}), left_on="event_id",
                  right_index=True, how="left")
    ev = ev.merge(cnt_all.rename(columns={"P": "n_P_all", "S": "n_S_all"}), left_on="event_id",
                  right_index=True, how="left")
    for c in ("n_P_usable", "n_S_usable", "n_P_all", "n_S_all"):
        ev[c] = ev[c].fillna(0).astype(int)
    ev = ev.merge(em[["event_id", "in_ncedc_dd", "ncedc_dd_in_box", "in_ldeo_dd", "ldeo_dd_in_box",
                      "benchmark_event"]], on="event_id", how="left")
    ev["origin_time_utc"] = ev["origin_time"].map(iso)
    cols = ["event_id", "origin_time_utc", "latitude", "longitude", "depth_geoid_km",
            "depth_datum_m", "depth_model_km", "pref_mag", "pref_mag_type", "coda_mag",
            "n_ps_wt01", "n_s_wt01", "n_valid_ps", "gap_deg", "dmin_km", "rms_s", "erh_km",
            "erz_km", "version", "review_version", "domain", "proc_version", "depth_type",
            "crust_type", "remark_analyst", "remark_program", "in_box", "in_ncedc_dd",
            "ncedc_dd_in_box", "in_ldeo_dd", "ldeo_dd_in_box", "benchmark_event", "n_P_usable",
            "n_S_usable", "n_P_all", "n_S_all"]
    ev[cols].sort_values("origin_time_utc").to_csv(os.path.join(C.TAB, "ncss_catalog.csv"),
                                                   index=False, float_format="%.5f")
    pk = pk.merge(em[["event_id", "benchmark_event"]], on="event_id", how="left")
    pk.sort_values(["event_id", "time_utc", "phase"]).to_csv(
        os.path.join(C.TAB, "picks_ncss.csv"), index=False)
    stats["picks"] = dict(
        n_rows=int(len(pk)), n_P=int((pk.phase == "P").sum()), n_S=int((pk.phase == "S").sum()),
        n_usable_P=int(((pk.phase == "P") & pk.usable).sum()),
        n_usable_S=int(((pk.phase == "S") & pk.usable).sum()),
        amplitude_only_lines_skipped=n_amp_lines, other_lines_without_time=n_other_lines,
        weight_codes_P=pk[pk.phase == "P"].weight_code.value_counts().sort_index().to_dict(),
        weight_codes_S=pk[pk.phase == "S"].weight_code.value_counts().sort_index().to_dict())
    stats["ncss_depth_datum_m"] = dict(
        n_with_datum=int(ev.depth_datum_m.notna().sum()),
        min=float(ev.depth_datum_m.min()), median=float(ev.depth_datum_m.median()),
        max=float(ev.depth_datum_m.max()),
        events_without_datum=ev.loc[ev.depth_datum_m.isna(), "event_id"].tolist())

    # ---------------- location differences ----------------
    a = ev[ev.benchmark_event][["event_id", "origin_time", "latitude", "longitude",
                                 "depth_geoid_km", "depth_model_km", "depth_datum_m"]]
    b = dd[["event_id", "origin_time", "latitude", "longitude", "depth_km"]].add_prefix("dd_")
    c = ld[["event_id", "origin_time", "latitude", "longitude", "depth_km", "eh1_km", "ez_km"]]
    c = c.add_prefix("ldeo_")
    x = a.merge(b, left_on="event_id", right_on="dd_event_id", how="left")
    x = x.merge(c, left_on="event_id", right_on="ldeo_event_id", how="left")
    de, dn = dist_km(x.latitude, x.longitude, x.dd_latitude, x.dd_longitude)
    x["ncss_to_ncedc_dd_dh_km"] = np.hypot(de, dn)
    x["ncss_to_ncedc_dd_de_km"], x["ncss_to_ncedc_dd_dn_km"] = de, dn
    # NCEDC DD depth uses the model-surface datum: compare with the NCSS model depth
    x["ncss_model_minus_ncedc_dd_dz_km"] = x.depth_model_km - x.dd_depth_km
    x["ncss_geoid_minus_ncedc_dd_dz_km"] = x.depth_geoid_km - x.dd_depth_km
    x["ncss_minus_ncedc_dd_dt_s"] = (x.origin_time - x.dd_origin_time).dt.total_seconds()
    de, dn = dist_km(x.latitude, x.longitude, x.ldeo_latitude, x.ldeo_longitude)
    x["ncss_to_ldeo_dd_dh_km"] = np.hypot(de, dn)
    x["ncss_geoid_minus_ldeo_dd_dz_km"] = x.depth_geoid_km - x.ldeo_depth_km
    x["ncss_minus_ldeo_dd_dt_s"] = (x.origin_time - x.ldeo_origin_time).dt.total_seconds()
    de, dn = dist_km(x.dd_latitude, x.dd_longitude, x.ldeo_latitude, x.ldeo_longitude)
    x["ncedc_dd_to_ldeo_dd_dh_km"] = np.hypot(de, dn)
    x["ncedc_dd_minus_ldeo_dd_dz_km"] = x.dd_depth_km - x.ldeo_depth_km
    # NCEDC DD depth converted to geoid with the event's NCSS datum (approximation)
    x["ncedc_dd_geoidapprox_minus_ldeo_dz_km"] = (x.dd_depth_km - x.depth_datum_m / 1000.0
                                                  - x.ldeo_depth_km)
    x["ncedc_dd_minus_ldeo_dd_dt_s"] = (x.dd_origin_time - x.ldeo_origin_time).dt.total_seconds()
    keep = ["event_id", "ncss_to_ncedc_dd_dh_km", "ncss_to_ncedc_dd_de_km",
            "ncss_to_ncedc_dd_dn_km", "ncss_model_minus_ncedc_dd_dz_km",
            "ncss_geoid_minus_ncedc_dd_dz_km", "ncss_minus_ncedc_dd_dt_s",
            "ncss_to_ldeo_dd_dh_km", "ncss_geoid_minus_ldeo_dd_dz_km", "ncss_minus_ldeo_dd_dt_s",
            "ncedc_dd_to_ldeo_dd_dh_km", "ncedc_dd_minus_ldeo_dd_dz_km",
            "ncedc_dd_geoidapprox_minus_ldeo_dz_km", "ncedc_dd_minus_ldeo_dd_dt_s"]
    x[keep].to_csv(os.path.join(C.TAB, "location_differences.csv"), index=False,
                   float_format="%.4f")

    def q(s):
        s = s.dropna()
        return dict(n=int(len(s)), median=float(s.median()), median_abs=float(s.abs().median()),
                    p90_abs=float(s.abs().quantile(0.9)), max_abs=float(s.abs().max()))
    stats["differences"] = {k: q(x[k]) for k in keep[1:]}
    with open(os.path.join(C.TAB, "stats_04.json"), "w") as f:
        json.dump(stats, f, indent=1, default=str)
    print(json.dumps(stats, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
