# verify: per-event uniformity of the reference time across ALL server B manual_picks SAC files; header picks vs table values
import os
import numpy as np, pandas as pd
from obspy import UTCDateTime
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
TAB = f"{P}/data/gwangyang_11ev/reference_supplement/manual_vs_phasenet"
rows = []
for line in open(f"{P}/runs/verify_sp_offset/serverB_manual_picks_headers.txt"):
    w = line.split()
    f, a, t0 = w[0], float(w[1]), float(w[2])
    yr, jd, hh, mi, ss, ms = (int(x) for x in w[3:9])
    ev = f.split("/")[0]
    _, net, sta, cha, _ = os.path.basename(f)[15:].split(".") if False else (None,) + tuple(os.path.basename(f).split(".")[1:4]) + (None,)
    ref = UTCDateTime(year=yr, julday=jd, hour=hh, minute=mi, second=ss, microsecond=ms * 1000)
    rows.append(dict(ev=ev, sta=sta, cha=cha, a=a, t0=t0, ref=ref.timestamp, refs=str(ref)))
H = pd.DataFrame(rows)
H.loc[H.a == -12345.0, "a"] = np.nan
H.loc[H.t0 == -12345.0, "t0"] = np.nan
print("files:", len(H), "events:", H.ev.nunique())
for ev, g in H.groupby("ev"):
    print(ev, "unique nz references:", sorted(set(g.refs)), "files", len(g))
# compare Z files with table
UTC = pd.read_csv(f"{P}/data/gwangyang_11ev/reference_tables/picks_manual_utc.csv", dtype={"kma_id": str})
mx = 0; n = 0; mism = []
for ev, g in H[H.cha.str.endswith("Z")].groupby("ev"):
    t = pd.read_csv(f"{TAB}/{ev}_manual_phasenet_pick_table.csv").set_index("Station")
    for r in g.itertuples():
        for col, v in (("Manual_P", r.a), ("Manual_S", r.t0)):
            tv = t.loc[r.sta, col] if r.sta in t.index else np.nan
            if np.isfinite(v) != np.isfinite(tv):
                mism.append((ev, r.sta, col, v, tv))
            elif np.isfinite(v):
                n += 1
                mx = max(mx, abs(v - tv))
    # stations in table but no Z file
    zs = set(g.sta)
    missing = [s for s in t.index if s not in zs and (np.isfinite(t.loc[s, 'Manual_P']) or np.isfinite(t.loc[s, 'Manual_S']))]
    if missing:
        print(ev, "table stations with hand picks but no Z file:", missing)
print(f"Z-file header picks compared with table: {n} values, max |diff| {mx*1e6:.2f} us (od prints 8 significant digits)")
print("presence mismatches (header vs table):", len(mism), mism[:10])
# absolute: ref + a vs picks_manual_utc
U = UTC.copy(); U["ts"] = [UTCDateTime(x).timestamp for x in U.time]
Z = H[H.cha.str.endswith("Z")].set_index(["ev", "sta"])
d = []
for r in U.itertuples():
    z = Z.loc[(r.kma_id, r.station)]
    v = z.a if r.phase == "P" else z.t0
    d.append((z.ref + v) - r.ts)
d = np.array(d)
print(f"picks_manual_utc.csv vs (server B Z header ref + a/t0): N={len(d)}, max |diff| {np.nanmax(np.abs(d))*1e6:.2f} us, n nan {np.isnan(d).sum()}")
print("picks_manual_utc rows:", len(U), (U.phase=='P').sum(), (U.phase=='S').sum())
# components: are the a/t0 the same on all 3 components? (notebook 9 copies them)
for (ev, sta), g in H.groupby(["ev", "sta"]):
    if g.a.nunique(dropna=False) > 1 or g.t0.nunique(dropna=False) > 1:
        print("component disagreement:", ev, sta, g[["cha", "a", "t0"]].values.tolist())
