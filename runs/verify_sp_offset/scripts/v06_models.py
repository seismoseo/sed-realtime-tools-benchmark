# verify: model variants and explanation fits with my own flat-layer travel-time code (independent of sp_offset.py)
import numpy as np, pandas as pd
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
D = f"{P}/data/gwangyang_11ev"
A = pd.read_csv(f"{P}/runs/verify_sp_offset/my_sp_pairs_all.csv", dtype={"ev": str})
A = A[~A.excl].reset_index(drop=True)
EV = pd.read_csv(f"{D}/reference_tables/hypodd_dtcc.csv", dtype={"kma_id": str}).set_index("kma_id")
ST = pd.read_csv(f"{D}/inputs/nll_kim1983/stations_gridded.csv").set_index("Code")

def tfirst(x, zs, zr, tops, v):
    tops = np.asarray(tops, float); v = np.asarray(v, float)
    bots = np.r_[tops[1:], 1e9]
    # direct
    h = np.clip(np.minimum(bots, zs) - np.maximum(tops, zr), 0, None)
    m = h > 0; hh, vv = h[m], v[m]
    if x < 1e-9:
        best = np.sum(hh / vv)
    else:
        lo, hi = 0.0, (1 - 1e-13) / vv.max()
        for _ in range(200):
            p = 0.5 * (lo + hi)
            X = np.sum(hh * p * vv / np.sqrt(1 - (p * vv) ** 2))
            lo, hi = (p, hi) if X < x else (lo, p)
        p = 0.5 * (lo + hi)
        best = np.sum(hh / (vv * np.sqrt(1 - (p * vv) ** 2)))
    # head waves along the top of each layer below the source
    for n in range(1, len(tops)):
        zn = tops[n]
        if zn <= zs:
            continue
        hd = np.clip(np.minimum(bots, zn) - np.maximum(tops, zs), 0, None)[:n]
        hu = np.clip(np.minimum(bots, zn) - np.maximum(tops, zr), 0, None)[:n]
        used = (hd + hu) > 0
        if v[n] <= v[:n][used].max():
            continue
        s = v[:n] / v[n]
        xc = np.sum((hd + hu) * s / np.sqrt(1 - s ** 2))
        if x < xc:
            continue
        t = x / v[n] + np.sum((hd + hu) * np.sqrt(1 / v[:n] ** 2 - 1 / v[n] ** 2))
        best = min(best, t)
    return best

zs = A.ev.map(EV.depth_km).to_numpy()
zr = -A.sta.map(ST.Elevation_m).to_numpy() / 1000.0
def sp(tops, vp, vs, zr_=zr):
    return np.array([tfirst(x, a, b, tops, vs) - tfirst(x, a, b, tops, vp) for x, a, b in zip(A.dist, zs, zr_)])
T83 = [-5, 15, 32]; VP83 = np.array([5.98, 6.38, 7.95])
A["m83"] = sp(T83, VP83, VP83 / 1.73)
A["m83_sea"] = sp(T83, VP83, VP83 / 1.73, np.zeros(len(A)))
A["m83_hinvS"] = sp(T83, VP83, [3.40, 3.79, 4.58])
A["m11"] = sp([-5, 7.29, 20.7, 31.3], [5.63, 6.17, 6.58, 7.77], [3.40, 3.60, 3.70, 4.45])
print("max |grid S-P - my 1-D kim1983 S-P| (ms):", 1000 * np.abs(A.sp_mod - A.m83).max())
for src in ("hand", "pnp"):
    d = A[A.src == src]
    o = d.sp_obs.to_numpy()
    for col in ("m83", "m83_sea", "m83_hinvS", "m11"):
        r = o - d[col].to_numpy()
        print(f"{src} {col:10s}: median offset {np.median(r):+.4f}  RMS {np.sqrt(np.mean(r**2)):.4f}  trend {np.polyfit(d.dist, r, 1)[0]*100:+.3f} s/100km")
    tpg = d.tp_grid.to_numpy(); off = d.off.to_numpy()
    k = np.sum(o * tpg) / np.sum(tpg ** 2)
    print(f"   (i) RMS {np.sqrt(np.mean(off**2)):.4f}; (ii) Vp/Vs {1+k:.4f} RMS {np.sqrt(np.mean((o-k*tpg)**2)):.4f}; "
          f"(iii) c {off.mean():+.4f} RMS {np.sqrt(np.mean((off-off.mean())**2)):.4f}")
    X = np.column_stack([tpg, np.ones(len(o))]); c = np.linalg.lstsq(X, o, rcond=None)[0]
    print(f"   (v) Vp/Vs {1+c[0]:.4f} c {c[1]:+.4f} RMS {np.sqrt(np.mean((o-X@c)**2)):.4f}")
    stc = d.groupby("sta").off.transform("median")
    print(f"   station-constant RMS {np.sqrt(np.mean((off-stc)**2)):.4f}")
    # (viii) / (ix) layer scans
    for name, (z1, z2) in (("viii near-station -5..5", (-5.0, 5.0)), ("ix source 10..15", (10.0, 15.0))):
        tops = sorted(set(T83 + [z1, z2]))
        vp = np.array([VP83[np.searchsorted(T83, z, side='right') - 1] for z in tops])
        kl = tops.index(z1)
        zs_d = d.ev.map(EV.depth_km).to_numpy(); zr_d = -d.sta.map(ST.Elevation_m).to_numpy() / 1000
        tp = np.array([tfirst(x, a, b, tops, vp) for x, a, b in zip(d.dist, zs_d, zr_d)])
        best = None
        for kk in np.arange(1.50, 1.7301, 0.005):
            vs = vp / 1.73; vs[kl] = vp[kl] / kk
            ts = np.array([tfirst(x, a, b, tops, vs) for x, a, b in zip(d.dist, zs_d, zr_d)])
            rms = np.sqrt(np.mean((o - (ts - tp)) ** 2))
            if best is None or rms < best[1]:
                best = (kk, rms)
        print(f"   ({name}) best Vp/Vs {best[0]:.3f} RMS {best[1]:.4f}")
A.to_csv(f"{P}/runs/verify_sp_offset/my_sp_pairs_models.csv", index=False)
