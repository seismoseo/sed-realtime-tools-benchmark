# 02_nll_station_list.py -- write the NonLinLoc station list (GTSRCE lines) for the Gwangyang benchmark.
#
# Part of step C1 (install/02_build_nonlinloc.sh, stage "grids"). Run in conda env 'pyrtdd'.
#
# Why: NonLinLoc's Grid2Time computes one travel-time grid (and one take-off-angle grid) per GTSRCE
# line, i.e. per station. scrtdd/pyrtdd later find the grid of a station by its LOCATION (the station
# position stored in the grid header), not by its name, so the coordinates written here must be exactly
# the coordinates the relocation will later be given for the same station.
#
# Station set = union of three independent lists of the benchmark (they should agree; we check):
#   reference/gwangyang_pnplus/station_table/used_stations_100km.csv   (Network,Code,Latitude,Longitude,Elevation[m],Sensor)
#   reference/gwangyang_pnplus/2.HypoDD/*/station.dat                    (code = network+station, e.g. KSBAU)
#   reference/gwangyang_pnplus/waveforms_100km/<event>/<event>.<NET>.<STA>.<CHA>.sac
# Coordinates/elevation come from used_stations_100km.csv; kma_stations_100km.csv is the fallback for a
# station missing there. Elevation (m, positive up) is written as the GTSRCE 'elev' field in km, with
# zSrce = 0, so NonLinLoc puts the station at depth = -elevation (above sea level = negative depth).
#
# Usage: python 02_nll_station_list.py <reference_dir> <output_dir>
# Output: <output_dir>/stations.in (GTSRCE lines) and <output_dir>/stations_gridded.csv (what was used, and why).

import glob
import os
import sys

import pandas as pd

if len(sys.argv) != 3:
    sys.exit("usage: python 02_nll_station_list.py <reference_dir> <output_dir>")
ref_dir, out_dir = sys.argv[1], sys.argv[2]
bench = os.path.join(ref_dir, "gwangyang_pnplus")

used = pd.read_csv(os.path.join(bench, "station_table", "used_stations_100km.csv"))
kma = pd.read_csv(os.path.join(bench, "station_table", "kma_stations_100km.csv"))

# --- the three station lists ------------------------------------------------------------------
in_used = set(zip(used.Network, used.Code))

# station.dat codes are network+station glued together (KSBAU); split them using the known networks
networks = sorted(set(used.Network) | set(kma.Network), key=len, reverse=True)
in_dat = set()
for f in sorted(glob.glob(os.path.join(bench, "2.HypoDD", "*", "station.dat"))):
    for line in open(f):
        tok = line.split()
        if not tok:
            continue
        net = next((n for n in networks if tok[0].startswith(n)), None)
        if net is None:
            sys.exit(f"cannot split network from station.dat code {tok[0]} in {f}")
        in_dat.add((net, tok[0][len(net):]))

in_sac = set()
for f in glob.glob(os.path.join(bench, "waveforms_100km", "*", "*.sac")):
    parts = os.path.basename(f).split(".")
    in_sac.add((parts[1], parts[2]))

union = sorted(in_used | in_dat | in_sac)
print(f"stations: used_stations_100km.csv {len(in_used)}, station.dat {len(in_dat)}, SAC files {len(in_sac)}, union {len(union)}")

# --- coordinates --------------------------------------------------------------------------------
rows = []
for net, sta in union:
    src = "used_stations_100km.csv"
    rec = used[(used.Network == net) & (used.Code == sta)]
    if rec.empty:
        src = "kma_stations_100km.csv"
        rec = kma[(kma.Network == net) & (kma.Code == sta)]
    if rec.empty:
        sys.exit(f"no coordinates for station {net}.{sta} in either station table")
    r = rec.iloc[0]
    rows.append(dict(Network=net, Code=sta, Latitude=float(r.Latitude), Longitude=float(r.Longitude),
                     Elevation_m=float(r.Elevation), coord_source=src,
                     in_used_csv=(net, sta) in in_used, in_station_dat=(net, sta) in in_dat,
                     in_sac=(net, sta) in in_sac))
st = pd.DataFrame(rows)

# NonLinLoc labels must be unique: we use the bare station code (all stations are network KS here)
dup = st.Code[st.Code.duplicated()]
if len(dup):
    sys.exit(f"duplicate station codes across networks, cannot use bare codes as labels: {sorted(set(dup))}")

os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "stations.in"), "w") as fp:
    fp.write("# GTSRCE label LATLON latSrce longSrce zSrce elev   (written by install/02_nll_station_list.py)\n")
    fp.write("# zSrce = 0 and elev = station elevation [km]: NonLinLoc places the station at depth zSrce - elev.\n")
    fp.write(f"# {len(st)} stations; coordinates from {sorted(set(st.coord_source))}\n")
    for r in st.itertuples():
        fp.write(f"GTSRCE {r.Code:<6s} LATLON {r.Latitude:.6f} {r.Longitude:.6f} 0.000 {r.Elevation_m / 1000.0:.3f}\n")
st.to_csv(os.path.join(out_dir, "stations_gridded.csv"), index=False)
print(f"wrote {os.path.join(out_dir, 'stations.in')} and stations_gridded.csv ({len(st)} stations)")
print(f"coordinate sources: {st.coord_source.value_counts().to_dict()}")
print(f"elevation range: {st.Elevation_m.min():.0f} .. {st.Elevation_m.max():.0f} m")
