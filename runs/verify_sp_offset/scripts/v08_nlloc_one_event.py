# verify: re-run NonLinLoc for one event with the notebook's control-file settings, from MY picks (server B header dump)
import os, subprocess, glob, sys
import numpy as np, pandas as pd
from obspy import UTCDateTime
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
D = f"{P}/data/gwangyang_11ev"
W = f"{P}/runs/verify_sp_offset/nlloc"
NLL = f"{P}/software/NonLinLoc/bin/NLLoc"
EVID = sys.argv[1] if len(sys.argv) > 1 else "20210827220322"
SHIFT = 0.2727327346801758   # = -(median hand offset), as in the notebook (I reproduced -0.2727)
PK = pd.read_csv(f"{P}/runs/verify_sp_offset/my_picks_with_residuals.csv", dtype={"ev": str})
PK = PK[(PK.src == "hand") & (PK.ev == EVID) & ~PK.out]
ST = pd.read_csv(f"{D}/inputs/nll_kim1983/stations_gridded.csv").set_index("Code")
EV = pd.read_csv(f"{D}/reference_tables/hypodd_dtcc.csv", dtype={"kma_id": str}).set_index("kma_id")
from pyproj import Geod
G = Geod(ellps="WGS84")
e = EV.loc[EVID]
PK["dist"] = [G.inv(e.longitude, e.latitude, ST.loc[s, "Longitude"], ST.loc[s, "Latitude"])[2] / 1e3 for s in PK.sta]
CTL = """CONTROL 1 54321
TRANS TRANS_MERC WGS-84 35.0000 127.7286 0.0
LOCSIG verify
LOCFILES {obs} NLLOC_OBS {D}/inputs/nll_kim1983/time/kim1983 {out}
LOCHYPOUT SAVE_NLLOC_ALL
LOCSEARCH OCT 10 10 10 0.01 20000 5000 0 1
LOCGRID 61 61 61 -15.0 -15.0 -1.0 0.5 0.5 0.5 PROB_DENSITY SAVE
LOCMETH GAU_ANALYTIC 9999.0 4 -1 -1 -1.0 6 -1.0 1
LOCGAU 0.1 0.0
LOCPHASEID P P
LOCPHASEID S S
LOCQUAL2ERR 0.1 0.5 1.0 2.0 99999.9
LOCANGLES ANGLES_NO 5
LOCPHSTAT 9999.0 -1 9999.0 1.0 1.0 9999.9 -9999.9 9999.9
"""
res = {}
for net, dmax in (("all", 1e9), ("near", 35.0)):
    for run, phases, sh in (("p_only", ["P"], 0.0), ("p_s", ["P", "S"], 0.0), ("p_s_shifted", ["P", "S"], SHIFT)):
        q = PK[(PK.dist <= dmax) & PK.phase.isin(phases)].sort_values("ts")
        rd = f"{W}/{EVID}/{net}/{run}"
        os.makedirs(f"{rd}/loc", exist_ok=True)
        for f in glob.glob(f"{rd}/loc/*"):
            os.remove(f)
        with open(f"{rd}/obs.nll", "w") as fo:
            for r in q.itertuples():
                t = UTCDateTime(r.ts + (sh if r.phase == "S" else 0.0))
                err = 0.05 if r.phase == "P" else 0.10
                fo.write(f"{r.sta:<6s} ?    ?    ? {r.phase:<6s} ? {t.strftime('%Y%m%d %H%M')} {t.second + t.microsecond*1e-6:7.4f} GAU {err:9.2e} -1.00e+00 -1.00e+00 -1.00e+00 1.0\n")
        open(f"{rd}/nlloc.in", "w").write(CTL.format(obs=f"{rd}/obs.nll", D=D, out=f"{rd}/loc/event"))
        with open(f"{rd}/nlloc.log", "w") as lf:
            subprocess.run(["nice", "-n", "10", NLL, f"{rd}/nlloc.in"], cwd=rd, stdout=lf, stderr=subprocess.STDOUT, check=True)
        hyp = [f for f in glob.glob(f"{rd}/loc/event.*.grid0.loc.hyp") if ".sum." not in f]
        assert len(hyp) == 1, hyp
        out = {}
        for line in open(hyp[0]):
            w = line.split()
            if not w:
                continue
            if w[0] == "GEOGRAPHIC":
                out["ot"] = (UTCDateTime(int(w[2]), int(w[3]), int(w[4]), int(w[5]), int(w[6])) + float(w[7])).timestamp
                out["lat"], out["lon"], out["dep"] = float(w[9]), float(w[11]), float(w[13])
            if w[0] == "QUALITY":
                dd = dict(zip(w[1::2], w[2::2])); out["rms"] = float(dd["RMS"]); out["nphs"] = int(dd["Nphs"])
            if w[0] == "NLLOC":
                out["status"] = " ".join(w[2:4])
        out["nP"] = int((q.phase == "P").sum()); out["nS"] = int((q.phase == "S").sum())
        res[(net, run)] = out
        print(net, run, out)
R = pd.DataFrame(res).T
R.to_csv(f"{W}/{EVID}_my_nlloc.csv")
def enu(a, b):
    lat0 = np.radians(b["lat"])
    n = (a["lat"] - b["lat"]) * 111194.9 ; e_ = (a["lon"] - b["lon"]) * 111194.9 * np.cos(lat0)
    return e_, n
for net in ("all", "near"):
    a, b = res[(net, "p_s")], res[(net, "p_s_shifted")]
    e_, n = enu(a, b)
    print(f"{net}: as picked minus S shifted: depth {a['dep'] - b['dep']:+.3f} km, origin time {a['ot'] - b['ot']:+.4f} s, horizontal {np.hypot(e_, n):.0f} m")
    c = res[(net, "p_only")]
    print(f"{net}: as picked minus P only: depth {a['dep'] - c['dep']:+.3f} km, OT {a['ot'] - c['ot']:+.4f} s; shifted minus P only: depth {b['dep'] - c['dep']:+.3f}, OT {b['ot'] - c['ot']:+.4f}")
