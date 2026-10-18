# verify: do the explanations really "shorten S-P by a similar amount at every station"? residuals by distance bin
# and per station within 30 km, using my own 1-D code (tfirst from v06).
import numpy as np, pandas as pd
from scipy import stats
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
src = open(f"{P}/runs/verify_sp_offset/scripts/v06_models.py").read()
exec(src[src.index("def tfirst"):src.index("zs = A.ev.map")])
D = f"{P}/data/gwangyang_11ev"
A = pd.read_csv(f"{P}/runs/verify_sp_offset/my_sp_pairs_models.csv", dtype={"ev": str})
EV = pd.read_csv(f"{D}/reference_tables/hypodd_dtcc.csv", dtype={"kma_id": str}).set_index("kma_id")
ST = pd.read_csv(f"{D}/inputs/nll_kim1983/stations_gridded.csv").set_index("Code")
d = A[A.src == "hand"].reset_index(drop=True)
o = d.sp_obs.to_numpy(); zs = d.ev.map(EV.depth_km).to_numpy(); zr = -d.sta.map(ST.Elevation_m).to_numpy() / 1000
T83 = [-5.0, 15.0, 32.0]; VP83 = np.array([5.98, 6.38, 7.95])
def layer_model(z1, z2, k):
    tops = sorted(set(T83 + [z1, z2])); vp = np.array([VP83[np.searchsorted(T83, z, side='right') - 1] for z in tops])
    vs = vp / 1.73; vs[tops.index(z1)] = vp[tops.index(z1)] / k
    return np.array([tfirst(x, a, b, tops, vs) - tfirst(x, a, b, tops, vp) for x, a, b in zip(d.dist, zs, zr)])
R = {"(iii) 1.73 + constant": o - d.m83.to_numpy() - (o - d.m83.to_numpy()).mean(),
     "(vi) kim2011": o - d.m11.to_numpy(),
     "(viii) Vp/Vs 1.66 above 5 km": o - layer_model(-5.0, 5.0, 1.66),
     "(ix) Vp/Vs 1.65 at 10-15 km": o - layer_model(10.0, 15.0, 1.65)}
# how much does each model shorten S-P relative to kim1983 at the nearest and farthest stations?
sh8 = layer_model(-5.0, 5.0, 1.66) - d.m83.to_numpy(); sh9 = layer_model(10.0, 15.0, 1.65) - d.m83.to_numpy(); sh11 = d.m11.to_numpy() - d.m83.to_numpy()
for lo, hi in ((0, 12), (12, 30), (30, 60), (60, 70), (70, 101)):
    m = (d.dist >= lo) & (d.dist < hi)
    print(f"{lo:3d}-{hi:3d} km (pairs {m.sum():3d}, stations {d.sta[m].nunique():2d}): observed offset median {d.off[m].median():+.3f} | model shortening vs kim1983: "
          f"(viii) {np.median(sh8[m]):+.3f} (ix) {np.median(sh9[m]):+.3f} (vi) {np.median(sh11[m]):+.3f} | residual medians: " +
          "  ".join(f"{k.split(' ')[0]} {np.median(v[m]):+.3f}" for k, v in R.items()))
# station-level test within 30 km: station medians of residuals, one-sample t / sign test against 0
near = d.dist < 30
print("stations within 30 km:", sorted(d.sta[near].unique()))
for k, v in R.items():
    sm = pd.Series(v[near]).groupby(d.sta[near].values).median()
    t = stats.ttest_1samp(sm.values, 0.0)
    print(f"  {k:32s}: station medians {' '.join(f'{x:+.2f}' for x in sm.values)} | mean {sm.mean():+.3f}, t-test p = {t.pvalue:.3g}, "
          f"negative {int((sm < 0).sum())}/{len(sm)}")
