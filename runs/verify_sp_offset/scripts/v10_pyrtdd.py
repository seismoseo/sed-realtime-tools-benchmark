# verify: pyrtdd catalog-only relocation, as picked vs every S pick shifted (+0.2727 s); plus two controls:
#   (c1) S picks shifted by a different amount at each station, same for all events (station static) -> should be identical
#   (c2) S picks of ONE event (rtdd id 3) shifted by +0.2727 s -> must change the solution (shows S picks matter)
import os, shutil, json, filecmp
import numpy as np, pandas as pd
from obspy import UTCDateTime
import pyrtdd.hdd as hdd
hdd.Logger.setLevel(hdd.Logger.Level.warning)
P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
CAT = f"{P}/data/gwangyang_11ev/inputs/rtdd_catalog"
NLLP = f"{P}/data/gwangyang_11ev/inputs/nll_kim1983/time"
W = f"{P}/runs/verify_sp_offset/pyrtdd"
SH = 0.2727327346801758
def reloc(d):
    cat = hdd.Catalog(f"{d}/station.csv", f"{d}/event.csv", f"{d}/phase.csv")
    cfg = hdd.Config()
    ttt = hdd.NLLGrid(gridPath=NLLP, gridModel="kim1983", maxSearchDistance=0.1)
    dd = hdd.DD(cat, cfg, ttt)
    cc = hdd.ClusteringOptions(); cc.numEllipsoids = 0; cc.maxNeighbourDist = 10.0; cc.minNumNeigh = 1; cc.maxNumNeigh = 0; cc.minNumPhases = 1
    so = hdd.SolverOptions(); so.absLocConstraintStart = 0.0; so.absLocConstraintEnd = 0.0; so.dampingFactorStart = 0.01; so.dampingFactorEnd = 0.01
    cl = dd.findClusters(cc)
    new = dd.relocateMultiEvents(cl, so)
    new.writeToFile(f"{d}/relocated-station.csv", f"{d}/relocated-event.csv", f"{d}/relocated-phase.csv")
    return len(cl)
rng = np.random.default_rng(3)
ph0 = pd.read_csv(f"{CAT}/phase.csv", keep_default_na=False, dtype=str)
stat = {s: float(x) for s, x in zip(sorted(ph0.stationCode.unique()), rng.uniform(0.1, 0.5, ph0.stationCode.nunique()))}
cases = {"as_picked": lambda r: 0.0,
         "s_shifted": lambda r: SH if r.type == "S" else 0.0,
         "c1_station_static": lambda r: stat[r.stationCode] if r.type == "S" else 0.0,
         "c2_one_event": lambda r: SH if (r.type == "S" and r.eventId == "3") else 0.0}
OUTS = {}
for name, f in cases.items():
    d = f"{W}/{name}"
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    shutil.copyfile(f"{CAT}/station.csv", f"{d}/station.csv")
    shutil.copyfile(f"{CAT}/event_centroid_start.csv", f"{d}/event.csv")
    ph = ph0.copy()
    ph["isotime"] = [(UTCDateTime(r.isotime) + f(r)).strftime("%Y-%m-%dT%H:%M:%S.%fZ") for r in ph.itertuples()]
    ph.to_csv(f"{d}/phase.csv", index=False)
    n = reloc(d)
    OUTS[name] = pd.read_csv(f"{d}/relocated-event.csv").set_index("id")
    print(name, "clusters", n, "relocated", OUTS[name].relocated.astype(str).str.lower().eq("true").sum())
def cmp(a, b):
    A, B = OUTS[a], OUTS[b]
    dlat = (B.latitude - A.latitude).abs().max() * 111195; dlon = (B.longitude - A.longitude).abs().max() * 111195 * np.cos(np.radians(35))
    ddep = (B.depth - A.depth).abs().max() * 1000
    dot = max(abs(UTCDateTime(x) - UTCDateTime(y)) for x, y in zip(A.isotime, B.isotime))
    return f"max |dN| {dlat:.6f} m, |dE| {dlon:.6f} m, |dZ| {ddep:.6f} m, |dOT| {dot*1e3:.6f} ms"
print("s_shifted vs as_picked:", cmp("as_picked", "s_shifted"))
print("text-identical relocated-event.csv lat/lon/depth/isotime columns:",
      OUTS["as_picked"][["isotime", "latitude", "longitude", "depth"]].equals(OUTS["s_shifted"][["isotime", "latitude", "longitude", "depth"]]))
print("c1 station static vs as_picked:", cmp("as_picked", "c1_station_static"))
print("c2 one event (id 3) vs as_picked:", cmp("as_picked", "c2_one_event"))
A, C = OUTS["as_picked"], OUTS["c2_one_event"]
for i in A.index:
    dz = (C.loc[i, "depth"] - A.loc[i, "depth"]) * 1000; dot = (UTCDateTime(C.loc[i, "isotime"]) - UTCDateTime(A.loc[i, "isotime"])) * 1e3
    print(f"   c2 event {i}: dZ {dz:+.2f} m, dOT {dot:+.2f} ms")
# spread of relocated events (is the relocation non-trivial?)
st0 = pd.read_csv(f"{CAT}/event_centroid_start.csv").set_index("id")
dn = (A.latitude - st0.latitude) * 111195; de = (A.longitude - st0.longitude) * 111195 * np.cos(np.radians(35)); dz = (A.depth - st0.depth) * 1000
print("as_picked moved from centroid start: |dN| up to %.1f m, |dE| up to %.1f m, |dZ| up to %.1f m" % (dn.abs().max(), de.abs().max(), dz.abs().max()))
# compare with the notebook's runs and the step-09 control
for name in ("as_picked", "s_shifted"):
    nb = pd.read_csv(f"{P}/runs/gwangyang/sp_offset/pyrtdd/{name}/relocated-event.csv").set_index("id")
    print(f"notebook {name} vs mine: lat/lon/depth/isotime equal:", nb[["isotime", "latitude", "longitude", "depth"]].equals(OUTS[name][["isotime", "latitude", "longitude", "depth"]]))
c9 = pd.read_csv(f"{P}/runs/gwangyang/dlpicker/reloc/control_phasenet_plus/relocated-event.csv").set_index("id")
print("step-09 control vs my as_picked: equal:", c9[["isotime", "latitude", "longitude", "depth"]].equals(OUTS["as_picked"][["isotime", "latitude", "longitude", "depth"]]))
print(OUTS["as_picked"][["isotime", "latitude", "longitude", "depth", "relocated", "startRms", "finalRms"]].head(11).to_string())
