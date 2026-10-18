# verify: (iv-a) depth-only explanation; distance-bin composition; station effects; crossover
import numpy as np, pandas as pd, sys
sys.path.insert(0, "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_sp_offset/scripts")
from importlib import util
spec = util.spec_from_file_location("v06", "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_sp_offset/scripts/v06_models.py")
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
A = pd.read_csv(f"{P}/runs/verify_sp_offset/my_sp_pairs_models.csv", dtype={"ev": str})
D = f"{P}/data/gwangyang_11ev"
EV = pd.read_csv(f"{D}/reference_tables/hypodd_dtcc.csv", dtype={"kma_id": str}).set_index("kma_id")
ST = pd.read_csv(f"{D}/inputs/nll_kim1983/stations_gridded.csv").set_index("Code")
exec(open(f"{P}/runs/verify_sp_offset/scripts/v06_models.py").read().split("zs = A.ev.map")[0].split("def tfirst")[1].join(["def tfirst", ""]) if False else "")
# re-define tfirst (copied from my v06)
src = open(f"{P}/runs/verify_sp_offset/scripts/v06_models.py").read()
start = src.index("def tfirst"); end = src.index("zs = A.ev.map")
exec(src[start:end])
d = A[A.src == "hand"].reset_index(drop=True)
o = d.sp_obs.to_numpy()
zs0 = d.ev.map(EV.depth_km).to_numpy(); zr = -d.sta.map(ST.Elevation_m).to_numpy() / 1000
VP = np.array([5.98, 6.38, 7.95]); T = [-5, 15, 32]
best = None
for dz in np.arange(-8.0, 4.01, 0.05):
    m = np.array([tfirst(x, a + dz, b, T, VP / 1.73) - tfirst(x, a + dz, b, T, VP) for x, a, b in zip(d.dist, zs0, zr)])
    r = np.sqrt(np.mean((o - m) ** 2))
    if best is None or r < best[1]:
        best = (dz, r)
print(f"(iv-a) best common depth shift {best[0]:+.2f} km, RMS {best[1]:.4f}")
# distance bins
for lo, hi in ((0, 30), (30, 60), (60, 70), (70, 101)):
    g = d[(d.dist >= lo) & (d.dist < hi)]
    sm = g.groupby("sta").off.agg(["median", "size"]).sort_values("median")
    print(f"{lo}-{hi} km: pairs {len(g)}, stations {g.sta.nunique()}, median {g.off.median():+.3f}; median of station medians {sm['median'].median():+.3f}")
    print("    ", ", ".join(f"{s}:{m:+.2f}({n})" for s, (m, n) in sm.iterrows()))
# station medians
sm = d.groupby("sta").agg(dist=("dist", "median"), med=("off", "median"), n=("off", "size"))
s3 = sm[sm.n >= 3]
print(f"station medians (n>=3): {len(s3)} stations, range {s3.med.min():+.2f}..{s3.med.max():+.2f}, SD {s3.med.std():.3f}")
# event x station two-way: how much of the variance is station vs event
import itertools
print("variance of offsets:", d.off.var(), " after removing station medians:", (d.off - d.groupby('sta').off.transform('median')).var())
