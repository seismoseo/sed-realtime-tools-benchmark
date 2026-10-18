#!/usr/bin/env python
# check_clustering_maxevsta.py -- what the one deliberate settings change of the 2025-26 runs does: rtDD's default
# clustering (libhdd ClusteringOptions()) with maxEvStaDist -1 (the 2015 value) against 120 km (the value of P0/P1/
# S0/S1 here). ONLY the clustering step (DD.findClusters) is run, twice, on the same catalog; nothing is relocated.
# The 120 km result must reproduce the P0 run's own pair file exactly (checked below).
#
# Output: runs/sanramon2026/analysis/clustering_maxevsta_check.json and clustering_maxevsta_pairs_only_unlimited.csv
#         (the phase pairs that exist only with maxEvStaDist -1, with the station distance from both events and
#          whether the station has a travel-time grid)
# Usage (env pyrtdd): python -I check_clustering_maxevsta.py

import json
import os

import numpy as np
import pandas as pd
from pyproj import Transformer

from pyrtdd.hdd import Catalog, ClusteringOptions, Config, DD, Logger, Neighbours, NLLGrid

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/sanramon_2026"
CATDIR = f"{DATA}/inputs/rtdd_catalog"
OUT = f"{PROJECT}/runs/sanramon2026/analysis"
TMP = f"{OUT}/clustering_check_tmp"
P0_PAIRS = f"{PROJECT}/runs/sanramon2026/pyrtdd/P0/processing/cluster-1-pair.csv"
LAT0, LON0 = 37.757, -121.940


def clusters_to_frame(clusters, cat, tag):
    os.makedirs(TMP, exist_ok=True)
    frames = []
    for i, c in enumerate(clusters):
        f = f"{TMP}/{tag}_cluster_{i + 1}.csv"
        Neighbours.writeToFile(c, cat, f)
        frames.append(pd.read_csv(f, dtype={"locationCode": str}, keep_default_na=False).assign(cluster=i + 1))
        os.remove(f)
    return pd.concat(frames, ignore_index=True)


def main():
    Logger.setLevel(Logger.Level.warning)
    cat = Catalog(f"{CATDIR}/station.csv", f"{CATDIR}/event.csv", f"{CATDIR}/phase.csv")
    cfg = Config()
    cfg.validPphases, cfg.validSphases = ["P"], ["S"]
    ttt = NLLGrid(gridPath=f"{DATA}/inputs/nll_con_tm/time", gridModel="sanramon2026_con", maxSearchDistance=0.1,
                  swapBytes=False, maxOpenFiles=512, accessMethod="KeepOpen")
    dd = DD(cat, cfg, ttt)
    res, frames = {}, {}
    for tag, v in (("unlimited_2015", -1.0), ("120km_2026", 120.0)):
        co = ClusteringOptions()
        co.maxEvStaDist = v
        assert co.maxEvStaDist == v
        cl = dd.findClusters(co)
        fr = clusters_to_frame(cl, cat, tag)
        frames[tag] = fr
        ev = set(fr.eventId1) | set(fr.eventId2)
        res[tag] = dict(maxEvStaDist=v, n_clusters=len(cl), cluster_sizes=[len(c) for c in cl], n_events=len(ev),
                        n_phase_pairs=int(len(fr)), n_event_pairs=int(len(fr[["eventId1", "eventId2"]].drop_duplicates())),
                        n_P=int((fr.phaseType == "P").sum()), n_S=int((fr.phaseType == "S").sum()))
    key = ["eventId1", "eventId2", "networkCode", "stationCode", "locationCode", "phaseType"]
    a, b = frames["unlimited_2015"], frames["120km_2026"]
    ea = set(a.eventId1) | set(a.eventId2)
    eb = set(b.eventId1) | set(b.eventId2)
    m = a[key].merge(b[key], on=key, how="outer", indicator=True)
    only_a = m[m._merge == "left_only"].drop(columns="_merge")
    only_b = m[m._merge == "right_only"].drop(columns="_merge")
    # station distance of the phase pairs that exist only without the limit
    tm = Transformer.from_crs("EPSG:4326", f"+proj=tmerc +lat_0={LAT0} +lon_0={LON0} +k=1 +x_0=0 +y_0=0 +ellps=WGS84",
                              always_xy=True)
    sta = pd.read_csv(f"{CATDIR}/station.csv", dtype={"locationCode": str}, keep_default_na=False)
    sta["sid"] = sta.networkCode + "." + sta.stationCode + "." + sta.locationCode
    sx, sy = tm.transform(sta.longitude.values, sta.latitude.values)
    spos = dict(zip(sta.sid, np.c_[sx, sy, sta.elevation.values.astype(float)]))
    ev = pd.read_csv(f"{CATDIR}/event.csv")
    ex, ey = tm.transform(ev.longitude.values, ev.latitude.values)
    epos = dict(zip(ev.id, np.c_[ex, ey, -ev.depth.values * 1000]))
    used = pd.read_csv(f"{DATA}/inputs/nll_con_tm/stations_used.csv", dtype={"locationCode": str}, keep_default_na=False)
    ingrid = set(used.networkCode + "." + used.stationCode + "." + used.locationCode)
    oa = only_a.copy()
    oa["sid"] = oa.networkCode + "." + oa.stationCode + "." + oa.locationCode
    oa["dist1_km"] = [np.linalg.norm(epos[e] - spos[s]) / 1000 for e, s in zip(oa.eventId1, oa.sid)]
    oa["dist2_km"] = [np.linalg.norm(epos[e] - spos[s]) / 1000 for e, s in zip(oa.eventId2, oa.sid)]
    oa["station_has_grid"] = oa.sid.isin(ingrid)
    oa.to_csv(f"{OUT}/clustering_maxevsta_pairs_only_unlimited.csv", index=False, float_format="%.3f")
    # the 120 km clustering must be exactly the P0 run's clustering
    p0 = pd.read_csv(P0_PAIRS, dtype={"locationCode": str}, keep_default_na=False)
    mp = b[key].merge(p0[key], on=key, how="outer", indicator=True)
    res["comparison"] = dict(
        events_only_unlimited=sorted(int(x) for x in ea - eb), events_only_120km=sorted(int(x) for x in eb - ea),
        phase_pairs_only_unlimited=int(len(only_a)), phase_pairs_only_120km=int(len(only_b)),
        event_pairs_only_unlimited=int(len(only_a[["eventId1", "eventId2"]].drop_duplicates()
                                           .merge(b[["eventId1", "eventId2"]].drop_duplicates(), how="left",
                                                  indicator=True).query("_merge == 'left_only'"))),
        only_unlimited_station_without_grid=int((~oa.station_has_grid).sum()),
        only_unlimited_station_with_grid=int(oa.station_has_grid.sum()),
        only_unlimited_max_dist_km_median=float(np.median(np.maximum(oa.dist1_km, oa.dist2_km))) if len(oa) else None,
        only_unlimited_by_phase=oa.phaseType.value_counts().to_dict(),
        clustering_120km_equals_P0_pair_file=bool((mp._merge == "both").all()),
        P0_pair_file_rows=int(len(p0)))
    os.rmdir(TMP)
    json.dump(res, open(f"{OUT}/clustering_maxevsta_check.json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
