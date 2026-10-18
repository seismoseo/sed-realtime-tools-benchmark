# 21_compare_with_2015.py -- (new for the 2025-26 case) what differs between the 2015 swarm benchmark
# (data/sanramon_2015, read only) and the 2025-26 benchmark (data/sanramon_2026):
#   1. where the two swarms are: centroids (NCSS routine, NCEDC DD, LDEO DD) and their separation;
#      depth distributions; best-fitting plane through the DD hypocentres (SVD; strike = azimuth of
#      the upward normal - 90, z down); how many 2025-26 events lie within 0.5 / 1 / 2 km (3-D) of a
#      2015 event, using the LDEO catalogs for both years (same DD system family, geoid depths;
#      2015 = NCAeqDD.v202112.1 base catalog, 2025-26 = NCAeqDDRT.v202201 real-time solutions);
#   2. the station network that picked the events: net.sta.loc of rtDD station.csv in both cases,
#      within 60 and 120 km of each swarm centre, by network and channel type; picks per event.
# Output: reference_tables/comparison_with_2015.csv (long format: section, item, y2015, y2026, note),
#         reference_tables/stations_2015_vs_2026.csv (one row per net.sta.loc of either station.csv),
#         reference_tables/stats_21.json
# Usage: python -I 21_compare_with_2015.py   (after tools 04, 08, 11 of both cases)

import json
import os
import sys

import numpy as np
import pandas as pd
from pyproj import Geod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

T15 = os.path.join(C.SR2015, "reference_tables")
I15 = os.path.join(C.SR2015, "inputs")
LAT15, LON15 = 37.786, -121.963          # 2015 grid/swarm centre (data/sanramon_2015 tool 09)
G = Geod(ellps="WGS84")


def enu(lat, lon, lat0=LAT15, lon0=LON15):
    """local east/north km about the 2015 centre (flat earth; fine for < 20 km)"""
    R = 6371.0
    return (np.radians(np.asarray(lon) - lon0) * R * np.cos(np.radians(lat0)),
            np.radians(np.asarray(lat) - lat0) * R)


def plane(x, y, z):
    """best-fitting plane (SVD) of points (km, z down): strike, dip, rms distance, singular values"""
    P = np.column_stack([x, y, z])
    P = P - P.mean(0)
    _, s, vt = np.linalg.svd(P, full_matrices=False)
    n = vt[2]
    if n[2] > 0:                    # make the normal point upward (z down)
        n = -n
    az_up = np.degrees(np.arctan2(n[0], n[1])) % 360      # azimuth of the upward normal = dip direction
    strike = (az_up - 90) % 360
    dip = np.degrees(np.arccos(abs(n[2])))
    rms = float(np.sqrt(np.mean((P @ vt[2]) ** 2)))
    return dict(strike_deg=round(float(strike), 1), dip_deg=round(float(dip), 1),
                rms_off_plane_km=round(rms, 3), sv_km=[round(float(v / np.sqrt(len(P))), 3) for v in s])


def bynet(names):
    c = pd.Series([x.split(".")[0] for x in names]).value_counts()
    return ", ".join(f"{k} {int(v)}" for k, v in c.items())


def q(s, ps=(0.05, 0.5, 0.95)):
    return [round(float(v), 2) for v in s.quantile(list(ps))]


def main():
    out, st = [], {}

    def add(section, item, a, b, note=""):
        out.append(dict(section=section, item=item, y2015=a, y2026=b, note=note))

    # ---------------- 1. events
    e15 = pd.read_csv(os.path.join(T15, "ncss_catalog.csv"))
    e15 = e15[e15.benchmark_event]
    e26 = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv"))
    e26 = e26[e26.benchmark_event]
    d15 = pd.read_csv(os.path.join(T15, "dd_catalog.csv"))
    d15 = d15[d15.event_id.isin(e15.event_id)]
    d26 = pd.read_csv(os.path.join(C.TAB, "dd_catalog.csv"))
    d26 = d26[d26.event_id.isin(e26.event_id)]
    l15 = pd.read_csv(os.path.join(T15, "ldeo_dd_catalog.csv"))
    l15 = l15[l15.event_id.isin(e15.event_id)]
    l26 = pd.read_csv(os.path.join(C.TAB, "ldeo_ddrt_catalog.csv"))
    l26 = l26[l26.event_id.isin(e26.event_id) & (l26.is_dd.astype(str) == "True")]
    add("events", "benchmark events", len(e15), len(e26))
    add("events", "period", "2015-10-01 to 2015-12-01", f"{C.T0_STR[:10]} to {C.T1_STR[:10]} (end excl.)")
    add("events", "box (lat; lon)", "37.75-37.83; -122.01..-121.91",
        f"{C.BOX['lat0']:.2f}-{C.BOX['lat1']:.2f}; {C.BOX['lon0']:.2f}..{C.BOX['lon1']:.2f}")
    add("events", "largest magnitude", f"{e15.pref_mag.max():.2f}", f"{e26.pref_mag.max():.2f}")
    add("events", "NCSS review flag (col 164)", str(e15.review_version.value_counts().to_dict()),
        str(e26.review_version.value_counts().to_dict()), "A = automatic, not analyst-reviewed")
    add("events", "NCSS processing (cols 165-168)",
        str((e15.domain.astype(str) + " " + e15.proc_version.astype(str)).value_counts().to_dict()),
        str((e26.domain.astype(str) + " " + e26.proc_version.astype(str)).value_counts().to_dict()))
    for name, a, b, dcol, note in (
            ("NCSS routine", e15, e26, "depth_geoid_km", "geoid depth"),
            ("NCEDC DD", d15, d26, "depth_km", "model depth (below the local station datum)"),
            ("LDEO DD", l15, l26, "depth_km", "geoid depth; 2015 base catalog, 2025-26 DD-RT")):
        la, lo = [float(a.latitude.median()), float(b.latitude.median())], \
                 [float(a.longitude.median()), float(b.longitude.median())]
        az, _, dist = G.inv(lo[0], la[0], lo[1], la[1])
        add("swarm position", f"{name}: median lat, lon",
            f"{la[0]:.4f}, {lo[0]:.4f}", f"{la[1]:.4f}, {lo[1]:.4f}",
            f"2025-26 centre is {dist / 1000:.2f} km from the 2015 centre, azimuth {az % 360:.0f} deg")
        add("swarm position", f"{name}: depth 5/50/95 % (km)", str(q(a[dcol])), str(q(b[dcol])), note)
        st[f"centre_shift_{name.replace(' ', '_')}"] = dict(km=dist / 1000, azimuth_deg=az % 360)
        xa, ya = enu(a.latitude, a.longitude)
        xb, yb = enu(b.latitude, b.longitude)
        add("swarm position", f"{name}: extent E-W / N-S, 5-95 % (km)",
            f"{np.ptp(np.quantile(xa, [0.05, 0.95])):.2f} / {np.ptp(np.quantile(ya, [0.05, 0.95])):.2f}",
            f"{np.ptp(np.quantile(xb, [0.05, 0.95])):.2f} / {np.ptp(np.quantile(yb, [0.05, 0.95])):.2f}")
        if name != "NCSS routine":
            pa, pb = plane(xa, ya, a[dcol].values), plane(xb, yb, b[dcol].values)
            add("swarm position", f"{name}: best plane strike/dip (deg), rms off-plane (km)",
                f"{pa['strike_deg']}/{pa['dip_deg']}, {pa['rms_off_plane_km']}",
                f"{pb['strike_deg']}/{pb['dip_deg']}, {pb['rms_off_plane_km']}",
                "SVD of all hypocentres; z down; strike = az(upward normal) - 90")
            st[f"plane_{name.replace(' ', '_')}"] = dict(y2015=pa, y2026=pb)
    # overlap of the two swarms (LDEO, geoid depths, same DD system family)
    xa, ya = enu(l15.latitude, l15.longitude)
    xb, yb = enu(l26.latitude, l26.longitude)
    A = np.column_stack([xa, ya, l15.depth_km.values])
    B = np.column_stack([xb, yb, l26.depth_km.values])
    dmin = np.sqrt(((B[:, None, :] - A[None, :, :]) ** 2).sum(-1)).min(1)
    for r in (0.5, 1.0, 2.0):
        add("swarm position", f"2025-26 LDEO DD events within {r} km (3-D) of a 2015 LDEO DD event",
            "", f"{int((dmin <= r).sum())} of {len(dmin)}")
    add("swarm position", "2025-26 LDEO DD: distance to nearest 2015 event 5/50/95 % (km)", "",
        str([round(float(v), 2) for v in np.quantile(dmin, [0.05, 0.5, 0.95])]))
    st["nearest_2015_event_km_quantiles"] = [float(v) for v in np.quantile(dmin, [0.05, 0.5, 0.95])]

    # ---------------- 2. stations and picks
    s15 = pd.read_csv(os.path.join(I15, "rtdd_catalog", "station.csv"), keep_default_na=False,
                      dtype={"locationCode": str})
    s26 = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "station.csv"), keep_default_na=False,
                      dtype={"locationCode": str})
    p15 = pd.read_csv(os.path.join(I15, "rtdd_catalog", "phase.csv"), keep_default_na=False,
                      dtype={"locationCode": str})
    p26 = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "phase.csv"), keep_default_na=False,
                      dtype={"locationCode": str})
    lat26, lon26 = C.LAT0, C.LON0
    for s, lat0, lon0 in ((s15, LAT15, LON15), (s26, lat26, lon26)):
        s["nsl"] = s.networkCode + "." + s.stationCode + "." + s.locationCode
        _, _, d = G.inv(np.full(len(s), lon0), np.full(len(s), lat0), s.longitude.astype(float).values,
                        s.latitude.astype(float).values)
        s["dist_km"] = np.asarray(d) / 1000
    for p in (p15, p26):
        p["nsl"] = p.networkCode + "." + p.stationCode + "." + p.locationCode
    allnsl = sorted(set(s15.nsl) | set(s26.nsl))
    tab = pd.DataFrame(dict(nsl=allnsl))
    tab["in_2015"] = tab.nsl.isin(s15.nsl)
    tab["in_2026"] = tab.nsl.isin(s26.nsl)
    tab["dist_2015_km"] = tab.nsl.map(s15.set_index("nsl").dist_km)
    tab["dist_2026_km"] = tab.nsl.map(s26.set_index("nsl").dist_km)
    tab["picks_2015"] = tab.nsl.map(p15.groupby("nsl").size()).fillna(0).astype(int)
    tab["picks_2026"] = tab.nsl.map(p26.groupby("nsl").size()).fillna(0).astype(int)
    tab["channels_2015"] = tab.nsl.map(p15.groupby("nsl").channelCode.apply(
        lambda x: ",".join(sorted(set(c[:2] for c in x)))))
    tab["channels_2026"] = tab.nsl.map(p26.groupby("nsl").channelCode.apply(
        lambda x: ",".join(sorted(set(c[:2] for c in x)))))
    tab.to_csv(os.path.join(C.TAB, "stations_2015_vs_2026.csv"), index=False, float_format="%.2f")
    for rmax in (60, 120, 1e9):
        a = set(s15.nsl[s15.dist_km <= rmax])
        b = set(s26.nsl[s26.dist_km <= rmax])
        lab = f"<= {rmax:.0f} km" if rmax < 1e8 else "all"
        add("stations (rtDD station.csv, net.sta.loc)", f"{lab} of each swarm centre", len(a), len(b),
            f"common {len(a & b)}, only 2015 {len(a - b)}, only 2025-26 {len(b - a)}")
    # the same at net.sta level (location codes changed for some stations, e.g. '' -> '01')
    for s in (s15, s26):
        s["ns"] = s.networkCode + "." + s.stationCode
    for rmax in (60, 120):
        a = set(s15.ns[s15.dist_km <= rmax])
        b = set(s26.ns[s26.dist_km <= rmax])
        add("stations (net.sta, location code ignored)", f"<= {rmax} km of each swarm centre", len(a),
            len(b), f"common {len(a & b)}; only 2015 {len(a - b)} "
            f"({bynet(a - b)}); only 2025-26 {len(b - a)} ({bynet(b - a)})")
    both = set(s15.ns) & set(s26.ns)
    lc = sorted(n for n in both if set(s15.nsl[s15.ns == n]) != set(s26.nsl[s26.ns == n]))
    add("stations (net.sta, location code ignored)", "stations in both years whose location code(s) differ",
        "", len(lc), ", ".join(lc[:25]) + (" ..." if len(lc) > 25 else ""))
    st["location_code_changes"] = lc
    for net in sorted(set(s15.networkCode) | set(s26.networkCode)):
        a = int(((s15.networkCode == net) & (s15.dist_km <= 60)).sum())
        b = int(((s26.networkCode == net) & (s26.dist_km <= 60)).sum())
        a1 = int((s15.networkCode == net).sum())
        b1 = int((s26.networkCode == net).sum())
        add("stations by network (<= 60 km / all)", net, f"{a} / {a1}", f"{b} / {b1}")
    # vertical-only sensors (no horizontal of the same sensor in stations.xml) near each swarm
    vo = {}
    for y, tabdir, lat0, lon0 in (("2015", T15, LAT15, LON15), ("2026", C.TAB, lat26, lon26)):
        s06 = json.load(open(os.path.join(tabdir, "stats_06.json")))
        vset = set(s06["vertical_only_sensor_groups"])
        chn = pd.read_csv(os.path.join(tabdir, "station_channels.csv"), keep_default_na=False,
                          dtype={"location": str})
        chn["sensor"] = chn.network + "." + chn.station + "." + chn.location + "." + chn.channel.str[:2] + "?"
        sen = chn.drop_duplicates("sensor")
        _, _, d = G.inv(np.full(len(sen), lon0), np.full(len(sen), lat0), sen.longitude.astype(float).values,
                        sen.latitude.astype(float).values)
        sen = sen.assign(dist_km=np.asarray(d) / 1000, vonly=sen.sensor.isin(vset))
        vo[y] = {r: (int((sen.dist_km <= r).sum()), int(((sen.dist_km <= r) & sen.vonly).sum()))
                 for r in (60, 120)}
    for r in (60, 120):
        add("sensors (stations.xml)", f"vertical-only sensors / all sensors <= {r} km",
            f"{vo['2015'][r][1]} / {vo['2015'][r][0]}", f"{vo['2026'][r][1]} / {vo['2026'][r][0]}",
            "no S cross-correlation possible on vertical-only sensors")
    for ct in sorted(set(p15.channelCode.str[:2]) | set(p26.channelCode.str[:2])):
        g15, g26 = p15[p15.channelCode.str[:2] == ct], p26[p26.channelCode.str[:2] == ct]
        add("picks in phase.csv by channel type (P / S)", ct,
            f"{int((g15.type == 'P').sum())} / {int((g15.type == 'S').sum())}",
            f"{int((g26.type == 'P').sum())} / {int((g26.type == 'S').sum())}")
    for p, e, y in ((p15, e15, "2015"), (p26, e26, "2026")):
        per = p.groupby("eventId").type.value_counts().unstack(fill_value=0).reindex(e.event_id,
                                                                                    fill_value=0)
        st[f"picks_per_event_{y}"] = dict(P_median=float(per.P.median()), S_median=float(per.S.median()),
                                          S_fraction=float(per.S.sum() / per.values.sum()))
    add("picks", "P / S picks per event, median", f"{st['picks_per_event_2015']['P_median']:.0f} / "
        f"{st['picks_per_event_2015']['S_median']:.0f}",
        f"{st['picks_per_event_2026']['P_median']:.0f} / {st['picks_per_event_2026']['S_median']:.0f}")
    add("picks", "S fraction of phase.csv", f"{st['picks_per_event_2015']['S_fraction']:.3f}",
        f"{st['picks_per_event_2026']['S_fraction']:.3f}")
    df = pd.DataFrame(out)
    df.to_csv(os.path.join(C.TAB, "comparison_with_2015.csv"), index=False)
    with open(os.path.join(C.TAB, "stats_21.json"), "w") as f:
        json.dump(st, f, indent=1, default=str)
    pd.set_option("display.width", 250)
    print(df.to_string(max_colwidth=70))


if __name__ == "__main__":
    main()
