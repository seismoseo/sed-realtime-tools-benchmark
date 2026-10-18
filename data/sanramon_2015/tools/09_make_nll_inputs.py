# 09_make_nll_inputs.py -- NonLinLoc control files for 2-D travel-time + take-off-angle grids of
# the NCSS 'CON' (Concord-Calaveras) model, following scrtdd's test recipe
# (libs/hdd/test/data/nll/iasp91_2D_azimuthal_equidist/run/*: GTMODE GRID2D ANGLES_YES,
# TRANS AZIMUTHAL_EQUIDIST, one GTSRCE per station, Vel2Grid then Grid2Time for P and S).
#
# Model    : inputs/velocity_model.csv (NCSS CON gradient model, surface shifted to 0.29 km above
#            sea level, first velocity extended up to -3 km, Vs = Vp/1.73) -> LAYER statements.
# Grid     : TRANS AZIMUTHAL_EQUIDIST WGS-84 centred on the swarm (37.786 N, -121.963 E);
#            2-D grid: distance 0..130 km, depth -3..30 km, 0.1 km spacing (VGGRID 2 1301 331).
# Stations : every net.sta.loc of inputs/rtdd_catalog/station.csv within MAX_DIST_KM of the grid
#            origin; GTSRCE <NET_STA_LOC> LATLON lat lon 0.0 elev_km with elev = sensor elevation
#            (same number as in station.csv, so rtDD's NLLGrid finds each grid by position).
# Output   : inputs/nll_con/run/{general.in,Vel2Grid.in,Grid2Time.in,phaseP.run,phaseS.run},
#            inputs/nll_con/stations.in, inputs/nll_con/stations_used.csv,
#            tools/make_nll_grids.sh (runs Vel2Grid + Grid2Time; grids go to inputs/nll_con/time,
#            which then holds <model>.{P,S}.mod.* and <model>.{P,S}.<label>.{time,angle}.*).
# Usage: python -I 09_make_nll_inputs.py                       (TRANS AZIMUTHAL_EQUIDIST -> inputs/nll_con)
#        python -I 09_make_nll_inputs.py --trans TRANS_MERC    (variant -> inputs/nll_con_tm and
#            tools/make_nll_grids_tm.sh; NLL's AZIMUTHAL_EQUIDIST departs from true distances by up
#            to 0.3 % here, TRANS_MERC by < 7 m at 120 km: see 17/18_*.py and docs)

import math
import os
import sys

import pandas as pd
from pyproj import Geod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

MODEL = "sanramon_con"
TRANS = "AZIMUTHAL_EQUIDIST"
if "--trans" in sys.argv:
    TRANS = sys.argv[sys.argv.index("--trans") + 1]
SUFFIX = {"AZIMUTHAL_EQUIDIST": "", "TRANS_MERC": "_tm"}[TRANS]
NLLDIR = os.path.join(C.INP, "nll_con" + SUFFIX)
LAT0, LON0 = 37.786, -121.963          # median NCSS location of the 685 benchmark events, rounded
MAX_DIST_KM = 120.0
DIST_KM, ZTOP_KM, ZBOT_KM, DX_KM = 130.0, -3.0, 30.0, 0.1
NLL_BIN = os.path.join(C.PROJECT, "software", "NonLinLoc", "bin")


def main():
    os.makedirs(os.path.join(NLLDIR, "run"), exist_ok=True)
    sta = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "station.csv"), keep_default_na=False,
                      dtype={"locationCode": str, "stationCode": str, "networkCode": str})
    g = Geod(ellps="WGS84")
    _, _, d = g.inv([LON0] * len(sta), [LAT0] * len(sta), sta.longitude.astype(float).tolist(),
                    sta.latitude.astype(float).tolist())
    sta["dist_km"] = [x / 1000 for x in d]
    sta["label"] = [f"{n}_{s}_{l if l else '--'}" for n, s, l in
                    zip(sta.networkCode, sta.stationCode, sta.locationCode)]
    use = sta[sta.dist_km <= MAX_DIST_KM].copy()
    far = sta[sta.dist_km > MAX_DIST_KM]
    zmax_elev = use.elevation.astype(float).max() / 1000
    assert -zmax_elev > ZTOP_KM, "a station is above the grid top"
    use.to_csv(os.path.join(NLLDIR, "stations_used.csv"), index=False)
    far.to_csv(os.path.join(NLLDIR, "stations_beyond_120km.csv"), index=False)

    vm = pd.read_csv(os.path.join(C.INP, "velocity_model.csv"))
    layers = "\n".join(
        f"LAYER {r.top_km:7.3f} {r.vp_km_s:7.4f} {r.vp_grad_per_km:9.6f} {r.vs_km_s:7.4f} "
        f"{r.vs_grad_per_km:9.6f} 2.70 0.0" for r in vm.itertuples())
    ny = int(round(DIST_KM / DX_KM)) + 1
    nz = int(round((ZBOT_KM - ZTOP_KM) / DX_KM)) + 1

    general = f"""# general.in -- San Ramon 2015 benchmark, written by tools/09_make_nll_inputs.py
CONTROL 1 54321
# working coordinates: {TRANS} projection centred on the swarm, no rotation
TRANS {TRANS} WGS-84 {LAT0:.4f} {LON0:.4f} 0.0
"""
    vel2grid = f"""# Vel2Grid.in -- NCSS CON (Concord-Calaveras) gradient model, see inputs/velocity_model.md
VGOUT ./model/{MODEL}
# 2-D grid (num_grid_x = 2): distance 0..{DIST_KM:.0f} km, depth {ZTOP_KM:.1f}..{ZBOT_KM:.1f} km, {DX_KM} km
VGGRID 2 {ny} {nz} 0.0 0.0 {ZTOP_KM:.1f} {DX_KM} {DX_KM} {DX_KM} SLOW_LEN
# LAYER depth_top(km, sea level) Vp_top Vp_grad Vs_top Vs_grad rho_top rho_grad
# (velocity = top value + gradient * (depth - depth_top) inside each layer; last = half-space)
{layers}
"""
    grid2time = """# Grid2Time.in
GTMODE GRID2D ANGLES_YES
# Podvin & Lecomte (1991) finite differences
GT_PLFD 1.0e-3 0
"""
    stations_in = "# GTSRCE label LATLON lat lon z(km, 0 = sea level) elev(km above z)\n" + "\n".join(
        f"GTSRCE {r.label} LATLON {float(r.latitude):.6f} {float(r.longitude):.6f} 0.0 "
        f"{float(r.elevation) / 1000:.4f}" for r in use.itertuples()) + "\n"
    runs = {p: f"""# phase{p}.run
VGTYPE {p}
GTFILES ./model/{MODEL} ./time/{MODEL} {p}
INCLUDE stations.in
INCLUDE run/general.in
INCLUDE run/Vel2Grid.in
INCLUDE run/Grid2Time.in
""" for p in ("P", "S")}
    files = {"run/general.in": general, "run/Vel2Grid.in": vel2grid,
             "run/Grid2Time.in": grid2time, "stations.in": stations_in,
             "run/phaseP.run": runs["P"], "run/phaseS.run": runs["S"]}
    for name, txt in files.items():
        with open(os.path.join(NLLDIR, name), "w") as f:
            f.write(txt)
    sh = f"""#!/usr/bin/env bash
# make_nll_grids{SUFFIX}.sh -- build the NonLinLoc 2-D P and S travel-time/take-off-angle grids of the
# NCSS CON model for the San Ramon benchmark, TRANS {TRANS} (control files by 09_make_nll_inputs.py).
# Output: {NLLDIR}/time/{MODEL}.{{P,S}}.mod.*, {MODEL}.{{P,S}}.<NET_STA_LOC>.{{time,angle}}.*
# For rtDD/scrtdd: NLLGrid table directory = {NLLDIR}/time, model name = {MODEL}.
# Usage: bash make_nll_grids{SUFFIX}.sh            (re-run safe: it starts from empty model/ and time/)
set -euo pipefail
NLL_BIN={NLL_BIN}
cd {NLLDIR}
LOG={C.LOGS}/sanramon_nll_grids{SUFFIX}.log
echo "== $(date '+%F %T') make_nll_grids{SUFFIX}.sh start" >> "$LOG"
rm -f {NLLDIR}/DONE
rm -rf {NLLDIR}/model {NLLDIR}/time
mkdir -p model time
for P in P S; do
  "$NLL_BIN/Vel2Grid" run/phase$P.run >> "$LOG" 2>&1
  "$NLL_BIN/Grid2Time" run/phase$P.run >> "$LOG" 2>&1
done
echo "== $(date '+%F %T') done: $(ls time/*.time.hdr | wc -l) time grids, $(ls time/*.angle.hdr | wc -l) angle grids" >> "$LOG"
touch {NLLDIR}/DONE
"""
    shp = os.path.join(C.TOOLS, f"make_nll_grids{SUFFIX}.sh")
    with open(shp, "w") as f:
        f.write(sh)
    os.chmod(shp, 0o755)
    print(f"stations in station.csv {len(sta)}, within {MAX_DIST_KM} km: {len(use)}, beyond: "
          f"{len(far)} ({', '.join(far.label)}), highest sensor {zmax_elev:.3f} km, grid "
          f"{ny} x {nz} nodes; Grid2Time exists: {os.path.exists(os.path.join(NLL_BIN, 'Grid2Time'))}")


if __name__ == "__main__":
    main()
