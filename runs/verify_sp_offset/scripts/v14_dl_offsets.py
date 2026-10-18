# verify: DL-picker S-P offsets (4 main models), most confident in-window pick per event/station/phase
import numpy as np, pandas as pd
from obspy import UTCDateTime
import pyrtdd.hdd as hdd
hdd.Logger.setLevel(hdd.Logger.Level.warning)
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
D = f"{P}/data/gwangyang_11ev"
d = pd.read_csv(f"{P}/runs/gwangyang/dlpicker/analysis/dl_picks_all.csv", dtype={"kma_id": str})
EV = pd.read_csv(f"{D}/reference_tables/hypodd_dtcc.csv", dtype={"kma_id": str}).set_index("kma_id")
EV["ot"] = [UTCDateTime(t).timestamp for t in EV.origin_time_pha_datum]
ST = pd.read_csv(f"{D}/inputs/nll_kim1983/stations_gridded.csv").set_index("Code")
TT = hdd.NLLGrid(gridPath=f"{D}/inputs/nll_kim1983/time", gridModel="kim1983", maxSearchDistance=0.1)
cache = {}
def gt(ev, s, ph):
    k = (ev, s, ph)
    if k not in cache:
        e = EV.loc[ev]; st = ST.loc[s]
        cache[k] = TT.compute(e.latitude, e.longitude, e.depth_km, st.Latitude, st.Longitude, st.Elevation_m, ph)
    return cache[k]
rng = np.random.default_rng(5)
for m in ["phasenet_original", "phasenet_instance", "eqtransformer_stead", "phasenet_stead"]:
    q = d[(d.variant == m) & d.in_window.astype(bool)].copy()
    q["ts"] = [UTCDateTime(t.replace(" ", "T")).timestamp for t in q.time]
    q = q.sort_values(["confidence", "ts"], ascending=[False, True]).groupby(["kma_id", "station", "phase"]).head(1)
    q = q[q.station.isin(ST.index)]
    q["res"] = [t - EV.loc[e, "ot"] - gt(e, s, p) for t, e, s, p in zip(q.ts, q.kma_id, q.station, q.phase)]
    q["out"] = q.res.abs() > 1.0
    rows = []
    for (e, s), g in q.groupby(["kma_id", "station"]):
        p, sp = g[g.phase == "P"], g[g.phase == "S"]
        if len(p) == 1 and len(sp) == 1:
            rows.append(dict(ev=e, sta=s, off=(sp.ts.iloc[0] - p.ts.iloc[0]) - (gt(e, s, "S") - gt(e, s, "P")), ex=bool(p.out.iloc[0] or sp.out.iloc[0])))
    r = pd.DataFrame(rows); u = r[~r.ex]
    sts = u.sta.unique(); grp = {s: u.off[u.sta == s].values for s in sts}
    bs = [np.median(np.concatenate([grp[s] for s in rng.choice(sts, len(sts))])) for _ in range(2000)]
    print(f"{m}: picks P {int((q.phase=='P').sum())} S {int((q.phase=='S').sum())}, excluded picks P {int(q[(q.phase=='P')].out.sum())} S {int(q[(q.phase=='S')].out.sum())}; "
          f"pairs {len(r)}, excluded {int(r.ex.sum())}, median {u.off.median():+.3f} (95% {np.percentile(bs,2.5):+.3f}..{np.percentile(bs,97.5):+.3f}), events {u.ev.nunique()}")
