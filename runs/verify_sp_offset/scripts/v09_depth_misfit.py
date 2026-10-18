# verify: misfit vs depth for the all-station NonLinLoc runs (hand picks) at the NonLinLoc epicenter; OT solved analytically
import numpy as np, pandas as pd
import pyrtdd.hdd as hdd
hdd.Logger.setLevel(hdd.Logger.Level.warning)
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
D = f"{P}/data/gwangyang_11ev"
TT = hdd.NLLGrid(gridPath=f"{D}/inputs/nll_kim1983/time", gridModel="kim1983", maxSearchDistance=0.1)
ST = pd.read_csv(f"{D}/inputs/nll_kim1983/stations_gridded.csv").set_index("Code")
PK = pd.read_csv(f"{P}/runs/verify_sp_offset/my_picks_with_residuals.csv", dtype={"ev": str})
N = pd.read_csv(f"{P}/runs/gwangyang/sp_offset/nlloc_results.csv", dtype={"kma_id": str})
SH = 0.2727327346801758
zs = np.round(np.arange(13.5, 16.51, 0.02), 3)
for ev in ["20210827220322", "20260204054406", "20210828234556", "20260101024947"]:
    q = PK[(PK.src == "hand") & (PK.ev == ev) & ~PK.out]
    for run, sh in (("p_s", 0.0), ("p_s_shifted", SH)):
        r = N[(N.source == "hand") & (N.network == "all") & (N.run == run) & (N.kma_id == ev)].iloc[0]
        obs = q.ts.to_numpy() + np.where(q.phase == "S", sh, 0.0)
        w = np.where(q.phase == "P", 1 / (0.05**2 + 0.1**2), 1 / (0.1**2 + 0.1**2))
        mis = []
        for z in zs:
            t = np.array([TT.compute(r.lat, r.lon, z, ST.loc[s, "Latitude"], ST.loc[s, "Longitude"], ST.loc[s, "Elevation_m"], ph) for s, ph in zip(q.sta, q.phase)])
            ot = np.sum(w * (obs - t)) / np.sum(w)
            res = obs - ot - t
            mis.append(np.sum(w * res ** 2))
        mis = np.array(mis)
        j = int(np.argmin(mis))
        # local slopes around 15 km
        i15 = int(np.argmin(np.abs(zs - 15.0)))
        print(f"{ev} {run}: NLLoc depth {r.depth_km:.3f}; misfit minimum over depth at {zs[j]:.2f} km (fixed NLLoc epicenter); "
              f"misfit at 14.80/14.90/15.00/15.10/15.20: " + " ".join(f"{mis[np.argmin(np.abs(zs-z))]-mis[j]:.2f}" for z in (14.8, 14.9, 15.0, 15.1, 15.2)))
