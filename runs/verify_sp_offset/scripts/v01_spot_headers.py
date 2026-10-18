# verify: hand-pick reference times from my own rsync'ed server B SAC files
import glob, os
import numpy as np, pandas as pd
from obspy import read, UTCDateTime
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
TAB = f"{P}/data/gwangyang_11ev/reference_supplement/manual_vs_phasenet"
UTC = pd.read_csv(f"{P}/data/gwangyang_11ev/reference_tables/picks_manual_utc.csv", dtype={"kma_id": str})
for f in sorted(glob.glob(f"{P}/runs/verify_sp_offset/serverB_spot/*/*.sac")):
    tr = read(f, headonly=True)[0]
    h = tr.stats.sac
    ref = UTCDateTime(year=h.nzyear, julday=h.nzjday, hour=h.nzhour, minute=h.nzmin, second=h.nzsec, microsecond=h.nzmsec * 1000)
    ev = os.path.basename(f)[:14]
    sta = tr.stats.station
    t = pd.read_csv(f"{TAB}/{ev}_manual_phasenet_pick_table.csv").set_index("Station")
    a, t0 = h.get("a"), h.get("t0")
    print(f"{ev} {sta} {tr.stats.channel}: nz ref {ref}  b={h.b:.4f} o={h.get('o')} a={a!r} t0={t0!r} ka={h.get('ka')} kt0={h.get('kt0')}")
    print(f"   table Manual_P={t.loc[sta,'Manual_P']!r} Manual_S={t.loc[sta,'Manual_S']!r}  diff a {a - t.loc[sta,'Manual_P']:.3e} t0 {t0 - t.loc[sta,'Manual_S']:.3e}")
    u = UTC[(UTC.kma_id == ev) & (UTC.station == sta)].set_index("phase")
    for ph, v in (("P", a), ("S", t0)):
        mine = ref + float(v)
        theirs = UTCDateTime(u.loc[ph, "time"])
        print(f"   {ph}: my UTC {mine}  table UTC {theirs}  diff {(mine - theirs)*1e6:.2f} us; their sac_reference_utc {u.loc[ph,'sac_reference_utc']}")
    # starttime check
    print(f"   trace starttime {tr.stats.starttime} = ref + b ? {abs((ref + h.b) - tr.stats.starttime) < 1e-3}")
