# 16_rtdd_integration_check.py -- load the San Ramon inputs with rtDD itself (pyrtdd, the Python
# wrapper of scrtdd's libhdd) to prove they are usable, without relocating anything:
#   1. Catalog(station.csv, event.csv, phase.csv): rtDD's own CSV reader; counts must match.
#   2. NLLGrid(inputs/nll_con/time, 'sanramon_con', maxSearchDistance=10 m): for every station
#      within 120 km, P and S travel time + take-off angles for the mainshock (NCSS location);
#      rtDD finds a station's grid by its position, so this checks station.csv against the grid
#      headers. Times are compared with ray1d at the same projected distance.
#   3. Information only: how many events pass rtDD's default clustering (8 neighbours, 8 phases).
# Output: reference_tables/rtdd_integration_check.csv, stats_16.json
# Usage: python -I 16_rtdd_integration_check.py   (needs pyrtdd in env pyrtdd)
#        python -I 16_rtdd_integration_check.py --variant tm   (grids of inputs/nll_con_tm;
#            writes rtdd_integration_check_tm.csv / stats_16_tm.json, skips the clustering step)

import json
import os
import sys

import numpy as np
import pandas as pd
from pyproj import Proj

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ray1d  # noqa: E402
import sr_common as C  # noqa: E402

from pyrtdd.hdd import Catalog, ClusteringOptions, Config, DD, Logger, NLLGrid  # noqa: E402

RT = os.path.join(C.INP, "rtdd_catalog")
VARIANT = sys.argv[sys.argv.index("--variant") + 1] if "--variant" in sys.argv else ""
SUF = f"_{VARIANT}" if VARIANT else ""
GRID = os.path.join(C.INP, "nll_con" + SUF, "time")
MAIN = 72540765


def main():
    st = {}
    Logger.setLevel(Logger.Level.warning)
    cat = Catalog(os.path.join(RT, "station.csv"), os.path.join(RT, "event.csv"),
                  os.path.join(RT, "phase.csv"))
    ev = pd.read_csv(os.path.join(RT, "event.csv"))
    ph = pd.read_csv(os.path.join(RT, "phase.csv"))
    sta = pd.read_csv(os.path.join(RT, "station.csv"), keep_default_na=False,
                      dtype={"locationCode": str})
    phd = cat.getPhases()                      # pyrtdd returns {event id: [phases]}
    st["catalog_loaded"] = dict(events=len(cat.getEvents()), events_with_phases=len(phd),
                                phases=int(sum(len(v) for v in phd.values())),
                                stations=len(cat.getStations()),
                                mainshock_id_present=MAIN in cat.getEvents(),
                                csv_events=len(ev), csv_phases=len(ph), csv_stations=len(sta))
    # ---- 2. grids through rtDD
    ttt = NLLGrid(gridPath=GRID, gridModel="sanramon_con", maxSearchDistance=10.0,
                  swapBytes=False, maxOpenFiles=64, accessMethod="KeepOpen")
    e = ev[ev.id == MAIN].iloc[0]
    used = pd.read_csv(os.path.join(C.INP, "nll_con" + SUF, "stations_used.csv"), keep_default_na=False,
                       dtype={"locationCode": str})
    vm = pd.read_csv(os.path.join(C.INP, "velocity_model.csv"))
    pts = vm.iloc[1:]
    mods = {"P": ray1d.Model1D(pts.top_km.values, pts.vp_km_s.values, vm.top_km.iloc[0], 0.01),
            "S": ray1d.Model1D(pts.top_km.values, pts.vs_km_s.values, vm.top_km.iloc[0], 0.01)}
    aeqd = Proj(proj="aeqd", lat_0=37.786, lon_0=-121.963, ellps="WGS84")
    exy = np.array(aeqd(e.longitude, e.latitude)) / 1000
    rows = []
    for r in used.itertuples():
        sxy = np.array(aeqd(float(r.longitude), float(r.latitude))) / 1000
        dist = float(np.hypot(*(exy - sxy)))
        for p in ("P", "S"):
            try:
                tt, azi, dip, dtdd, dtdh = ttt.computeAll(
                    float(e.latitude), float(e.longitude), float(e.depth), float(r.latitude),
                    float(r.longitude), float(r.elevation), p)
                err = ""
            except Exception as ex:          # grid not found etc.
                tt = azi = dip = np.nan
                err = str(ex)[:120]
            t_ray = float(mods[p].time([dist], float(e.depth), -float(r.elevation) / 1000,
                                       n_p=2000)[0])
            rows.append(dict(label=r.label, phase=p, dist_km=dist, t_rtdd=tt, t_ray=t_ray,
                             diff_s=tt - t_ray, takeoff_azi=azi, takeoff_dip=dip, error=err))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(C.TAB, f"rtdd_integration_check{SUF}.csv"), index=False, float_format="%.4f")
    ok = df[df.error == ""]
    st["grid_lookup"] = dict(stations=int(len(used)), lookups=int(len(df)), failed=int((df.error != "").sum()),
                             failures=df[df.error != ""].label.unique().tolist()[:20],
                             max_abs_diff_vs_ray1d_s={p: float(ok[ok.phase == p].diff_s.abs().max())
                                                      for p in ("P", "S")},
                             median_abs_diff_s={p: float(ok[ok.phase == p].diff_s.abs().median())
                                                for p in ("P", "S")},
                             takeoff_dip_range=[float(ok.takeoff_dip.min()), float(ok.takeoff_dip.max())])
    # ---- 3. clustering with rtDD defaults (information only)
    if VARIANT:
        with open(os.path.join(C.TAB, f"stats_16{SUF}.json"), "w") as f:
            json.dump(st, f, indent=1, default=str)
        print(json.dumps(st, indent=1, default=str))
        return
    cfg = Config()
    dd = DD(cat, cfg, ttt)
    copt = ClusteringOptions()
    try:
        clusters = dd.findClusters(copt)
        sizes = sorted((len(c) for c in clusters), reverse=True)
        inside = set()
        for c in clusters:
            inside |= set(c.keys())
        st["default_clustering"] = dict(n_clusters=len(sizes), events_in_clusters=int(sum(sizes)),
                                        largest=sizes[:5],
                                        events_not_clustered=sorted(int(i) for i in
                                                                    set(ev.id) - inside))
    except Exception as ex:
        st["default_clustering"] = dict(error=str(ex)[:300])
    with open(os.path.join(C.TAB, "stats_16.json"), "w") as f:
        json.dump(st, f, indent=1, default=str)
    print(json.dumps(st, indent=1, default=str))


if __name__ == "__main__":
    main()
