# verify: "same amount in every event" -- event terms after removing station terms (two-way robust decomposition)
import numpy as np, pandas as pd
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
A = pd.read_csv(f"{P}/runs/verify_sp_offset/my_sp_pairs_all.csv", dtype={"ev": str})
for src in ("hand", "pnp"):
    d = A[(A.src == src) & ~A.excl].copy()
    # alternate median polish: off = mu + ev_term + sta_term + resid
    ev_t = pd.Series(0.0, index=sorted(d.ev.unique())); st_t = pd.Series(0.0, index=sorted(d.sta.unique()))
    mu = d.off.median()
    for it in range(20):
        r = d.off - mu - d.ev.map(ev_t) - d.sta.map(st_t)
        st_t += r.groupby(d.sta).median()
        r = d.off - mu - d.ev.map(ev_t) - d.sta.map(st_t)
        ev_t += r.groupby(d.ev).median()
        m = ev_t.median(); ev_t -= m; mu += m
        m = st_t.median(); st_t -= m; mu += m
    r = d.off - mu - d.ev.map(ev_t) - d.sta.map(st_t)
    # bootstrap of event terms (resample residuals within event)
    rng = np.random.default_rng(1)
    se = {}
    for e, g in r.groupby(d.ev):
        bs = [np.median(rng.choice(g.values, len(g))) for _ in range(2000)]
        se[e] = np.std(bs)
    print(f"{src}: grand {mu:+.3f}; event terms (station terms removed): " + " ".join(f"{v:+.3f}" for v in ev_t.values))
    print(f"   event-term range {ev_t.min():+.3f}..{ev_t.max():+.3f}, SD {ev_t.std():.3f}; typical bootstrap SE of an event term {np.median(list(se.values())):.3f}; residual robust spread {1.4826*np.median(np.abs(r - r.median())):.3f}")
    # 2021 vs 2026
    y = pd.Series([e[:4] for e in ev_t.index], index=ev_t.index)
    print(f"   mean event term 2021: {ev_t[y=='2021'].mean():+.3f}, 2026: {ev_t[y=='2026'].mean():+.3f}")
    # Kruskal-Wallis on station-corrected offsets
    from scipy.stats import kruskal
    rc = d.off - d.sta.map(st_t)
    print("   Kruskal-Wallis on station-corrected offsets across events: p = %.3g" % kruskal(*[g.values for _, g in rc.groupby(d.ev)]).pvalue)
