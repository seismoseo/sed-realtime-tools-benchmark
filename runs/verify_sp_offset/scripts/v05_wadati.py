# verify: Wadati fit with per-event intercepts; station bootstrap CI; per-event slopes; sensitivity of intercept to origin time
import numpy as np, pandas as pd
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_sp_offset"
A = pd.read_csv(f"{P}/my_sp_pairs_all.csv", dtype={"ev": str})
A = A[~A.excl]
rng = np.random.default_rng(7)
def fit(d, x="tp_obs"):
    evs = sorted(d.ev.unique())
    X = np.column_stack([d[x].to_numpy()] + [(d.ev == e).to_numpy(float) for e in evs])
    c, *_ = np.linalg.lstsq(X, d.sp_obs.to_numpy(), rcond=None)
    r = d.sp_obs.to_numpy() - X @ c
    return c[0], pd.Series(c[1:], index=evs), r
for src in ("hand", "pnp"):
    d = A[A.src == src].reset_index(drop=True)
    m, ce, r = fit(d)
    st = d.sta.unique(); idx = {s: np.flatnonzero(d.sta == s) for s in st}
    bs = []
    for b in range(4000):
        ii = np.concatenate([idx[s] for s in rng.choice(st, len(st))])
        bs.append(fit(d.iloc[ii])[0])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    pe = [1 + np.polyfit(g.tp_obs, g.sp_obs, 1)[0] for _, g in d.groupby("ev") if len(g) >= 5]
    print(f"{src}: Vp/Vs {1+m:.4f} (95% {1+lo:.4f}..{1+hi:.4f}); per-event median {np.median(pe):.4f} (range {min(pe):.3f}..{max(pe):.3f}, n={len(pe)}); "
          f"intercepts {ce.min():+.3f}..{ce.max():+.3f}, median {ce.median():+.3f}; rms {np.sqrt(np.mean(r**2)):.3f}")
    # slope using MODEL P travel time instead of observed (origin-time independent alternative)
    m2, ce2, _ = fit(d, "tp_grid")
    print(f"     using grid tP instead of observed tP: Vp/Vs {1+m2:.4f}, intercepts {ce2.min():+.3f}..{ce2.max():+.3f} median {ce2.median():+.3f}")
    # also: through-origin fit with obs tP (no intercept)
    k0 = np.sum(d.sp_obs * d.tp_obs) / np.sum(d.tp_obs ** 2)
    print(f"     through-origin (no intercept) Vp/Vs {1+k0:.4f}")
