# verify: reference time of the local (re-referenced) waveform copy vs the server B hand-pick reference; route 2 (April ML picks)
import glob, os
import numpy as np, pandas as pd
from obspy import read, UTCDateTime
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
D = f"{P}/data/gwangyang_11ev"
H = {}
for line in open(f"{P}/runs/verify_sp_offset/serverB_manual_picks_headers.txt"):
    w = line.split(); ev = w[0].split("/")[0]
    yr, jd, hh, mi, ss, ms = (int(x) for x in w[3:9])
    H[ev] = UTCDateTime(year=yr, julday=jd, hour=hh, minute=mi, second=ss, microsecond=ms * 1000)
hinv = pd.read_csv(f"{D}/reference_tables/hypoinverse_kim1983.csv", dtype={"kma_id": str}).set_index("kma_id")
for ev in sorted(H):
    refs = set()
    for f in sorted(glob.glob(f"{D}/reference/gwangyang_pnplus/waveforms_100km/{ev}/*.sac")):
        h = read(f, headonly=True)[0].stats.sac
        refs.add(str(UTCDateTime(year=h.nzyear, julday=h.nzjday, hour=h.nzhour, minute=h.nzmin, second=h.nzsec, microsecond=h.nzmsec * 1000)))
    loc = UTCDateTime(sorted(refs)[0])
    # route 2: April ML picks absolute minus table PhaseNet column
    t = pd.read_csv(f"{D}/reference_supplement/manual_vs_phasenet/{ev}_manual_phasenet_pick_table.csv").set_index("Station")
    ml = pd.read_csv(f"{D}/reference_supplement/manual_picks_provenance/ml_picks_20260422/{ev}_picks.csv")
    r2 = []
    for r in ml.itertuples():
        c = "PhaseNet_" + r.Phase
        if r.Station in t.index and np.isfinite(t.loc[r.Station, c]):
            r2.append(UTCDateTime(r.Time).timestamp - t.loc[r.Station, c])
    r2 = np.array(r2)
    print(f"{ev}: server B ref {H[ev]} | local copy refs {len(refs)} {loc} local-server B {(loc - H[ev])*1e3:7.1f} ms | "
          f"route2 n={len(r2)} median-server B {(np.median(r2) - H[ev].timestamp)*1e6:6.1f} us spread {(r2.max()-r2.min())*1e6:5.1f} us | "
          f"hinv_kim1983 origin {hinv.loc[ev,'origin_time']}")
