# verify: S-P offsets (hand, PhaseNet+) with my own code. Hand picks are rebuilt from the server B header dump,
# not from picks_manual_utc.csv. Grid travel times via pyrtdd NLLGrid from each event's HypoDD hypocenter.
import os
import numpy as np, pandas as pd
from obspy import UTCDateTime
from pyproj import Geod
import pyrtdd.hdd as hdd
hdd.Logger.setLevel(hdd.Logger.Level.warning)
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
D = f"{P}/data/gwangyang_11ev"
OUT = f"{P}/runs/verify_sp_offset"
G = Geod(ellps="WGS84")
# --- hand picks from header dump (Z files)
ref, hp = {}, []
for line in open(f"{OUT}/serverB_manual_picks_headers.txt"):
    w = line.split(); f = w[0]; ev = f.split("/")[0]
    sta, cha = os.path.basename(f).split(".")[2:4]
    yr, jd, hh, mi, ss, ms = (int(x) for x in w[3:9])
    r = UTCDateTime(year=yr, julday=jd, hour=hh, minute=mi, second=ss, microsecond=ms * 1000)
    if not cha.endswith("Z"):
        continue
    for ph, v in (("P", float(w[1])), ("S", float(w[2]))):
        if v != -12345.0:
            hp.append(dict(src="hand", ev=ev, sta=sta, phase=ph, ts=r.timestamp + v))
HP = pd.DataFrame(hp)
pn = pd.read_csv(f"{D}/reference_tables/picks_phasenet_plus.csv", dtype={"kma_id": str})
PN = pd.DataFrame(dict(src="pnp", ev=pn.kma_id, sta=pn.station, phase=pn.phase, ts=[UTCDateTime(t).timestamp for t in pn.time]))
PK = pd.concat([HP, PN], ignore_index=True)
print("picks:", PK.groupby(["src", "phase"]).size().to_dict())
# --- events, stations
EV = pd.read_csv(f"{D}/reference_tables/hypodd_dtcc.csv", dtype={"kma_id": str}).set_index("kma_id")
EV["ot"] = [UTCDateTime(t).timestamp for t in EV.origin_time_pha_datum]
ST = pd.read_csv(f"{D}/inputs/nll_kim1983/stations_gridded.csv").set_index("Code")
TT = hdd.NLLGrid(gridPath=f"{D}/inputs/nll_kim1983/time", gridModel="kim1983", maxSearchDistance=0.1)
def tt(lat, lon, dep, sta, ph):
    s = ST.loc[sta]
    return TT.compute(lat, lon, dep, s.Latitude, s.Longitude, s.Elevation_m, ph)
cache = {}
for ev, e in EV.iterrows():
    for sta in ST.index:
        cache[(ev, sta)] = (tt(e.latitude, e.longitude, e.depth_km, sta, "P"), tt(e.latitude, e.longitude, e.depth_km, sta, "S"),
                            G.inv(e.longitude, e.latitude, ST.loc[sta, "Longitude"], ST.loc[sta, "Latitude"])[2] / 1e3)
PK["tobs"] = PK.ts - PK.ev.map(EV.ot)
PK["tgrid"] = [cache[(e, s)][0 if p == "P" else 1] for e, s, p in zip(PK.ev, PK.sta, PK.phase)]
PK["res"] = PK.tobs - PK.tgrid
PK["out"] = PK.res.abs() > 1.0
for (src, ph), g in PK.groupby(["src", "phase"]):
    o = g[g.out]
    print(f"{src} {ph}: n={len(g)} outliers(|res|>1 s)={len(o)}; kept median res {g[~g.out].res.median():+.3f} s; "
          f"kept 5-95% {g[~g.out].res.quantile(.05):+.2f}..{g[~g.out].res.quantile(.95):+.2f}; max|kept| {g[~g.out].res.abs().max():.2f}; "
          f"excluded |res| {o.res.abs().min() if len(o) else np.nan:.2f}-{o.res.abs().max() if len(o) else np.nan:.2f}")
PK.to_csv(f"{OUT}/my_picks_with_residuals.csv", index=False)
# --- S-P pairs
rows = []
for (src, ev, sta), g in PK.groupby(["src", "ev", "sta"]):
    p, s = g[g.phase == "P"], g[g.phase == "S"]
    if len(p) != 1 or len(s) != 1:
        if len(p) > 1 or len(s) > 1:
            print("DUPLICATE", src, ev, sta)
        continue
    tp, ts, dist = cache[(ev, sta)]
    rows.append(dict(src=src, ev=ev, sta=sta, dist=dist, sp_obs=s.ts.iloc[0] - p.ts.iloc[0], sp_mod=ts - tp,
                     tp_obs=p.tobs.iloc[0], tp_grid=tp, excl=bool(p.out.iloc[0] or s.out.iloc[0])))
A = pd.DataFrame(rows); A["off"] = A.sp_obs - A.sp_mod
A.to_csv(f"{OUT}/my_sp_pairs_all.csv", index=False)
rng = np.random.default_rng(12345)
def sboot(x, st, n=4000):
    x = np.asarray(x); st = np.asarray(st); u = np.unique(st); grp = [x[st == s] for s in u]
    m = [np.median(np.concatenate([grp[i] for i in rng.integers(0, len(u), len(u))])) for _ in range(n)]
    return np.percentile(m, [2.5, 97.5])
for src in ("hand", "pnp"):
    a = A[A.src == src]; d = a[~a.excl]
    lo, hi = sboot(d.off, d.sta)
    print(f"{src}: pairs {len(a)} excluded {int(a.excl.sum())} used {len(d)} events {d.ev.nunique()} stations {d.sta.nunique()} | "
          f"median {d.off.median():+.4f} s (95% station-bootstrap {lo:+.3f}..{hi:+.3f}); IQR {d.off.quantile(.25):+.3f}..{d.off.quantile(.75):+.3f}; "
          f"median w/o exclusion {a.off.median():+.4f}; mean {d.off.mean():+.4f}")
    pe = d.groupby("ev").off.agg(["median", "size"])
    print("   per-event medians:", " ".join(f"{v:+.3f}({n})" for v, n in zip(pe["median"], pe["size"])))
    print(f"   per-event median range {pe['median'].min():+.3f}..{pe['median'].max():+.3f}, SD {pe['median'].std():.3f}")
# hand vs pnp
h = PK[(PK.src == "hand") & ~PK.out].set_index(["ev", "sta", "phase"]).ts
p = PK[(PK.src == "pnp") & ~PK.out].set_index(["ev", "sta", "phase"]).ts
j = pd.concat([h.rename("h"), p.rename("p")], axis=1, join="inner")
dd = (j.h - j.p)
print("hand - PhaseNet+: P median %+.4f (N %d), S median %+.4f (N %d)" % (dd.xs("P", level=2).median(), len(dd.xs("P", level=2)), dd.xs("S", level=2).median(), len(dd.xs("S", level=2))))
hs = A[(A.src == "hand") & ~A.excl].set_index(["ev", "sta"]).sp_obs; ps = A[(A.src == "pnp") & ~A.excl].set_index(["ev", "sta"]).sp_obs
k = pd.concat([hs.rename("h"), ps.rename("p")], axis=1, join="inner")
print("hand - PhaseNet+ S-P: median %+.4f N %d" % ((k.h - k.p).median(), len(k)))
x = k.h - k.p
print("picking noise 1.4826*MAD/sqrt2: %.4f" % (1.4826 * np.median(np.abs(x - x.median())) / np.sqrt(2)))
# centroid variant
c = EV.iloc[0]
for src in ("hand", "pnp"):
    d = A[(A.src == src) & ~A.excl]
    spc = np.array([tt(c.centroid_lat, c.centroid_lon, c.centroid_depth_km, s, "S") - tt(c.centroid_lat, c.centroid_lon, c.centroid_depth_km, s, "P") for s in d.sta])
    print(f"{src}: centroid-model median offset {np.median(d.sp_obs - spc):+.4f}")
