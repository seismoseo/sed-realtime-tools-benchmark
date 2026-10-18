# 02_validate_nll_grids.py -- independent checks of the NonLinLoc kim1983 grids of the Gwangyang benchmark.
#
# Part of step C1 (install/02_build_nonlinloc.sh, stage "validate"). Run in conda env 'pyrtdd'.
#
# What is checked, and why:
#  1. Station lookup. scrtdd/pyrtdd find a station's grid by the station LOCATION stored in the grid header
#     (projected x/y + depth), within 'maxSearchDistance' (default 0.1 m). We convert every header location
#     back to latitude/longitude/elevation and compare with the station table.
#  2. Grid travel times at the cluster centroid (35.0000 N, 127.7286 E, 13.94 km), read
#     (a) through pyrtdd.hdd.NLLGrid (the reader scrtdd itself uses) and
#     (a') with our own numpy reader of the .hdr/.buf files (cross-check of the reader, gives the angle quality)
#     versus (b) an INDEPENDENT exact 1-D calculation of the same flat layered model: first arrival =
#     fastest of the direct ray and the head waves along the 15 km and 32 km interfaces, with the WGS-84
#     geodesic epicentral distance (no map projection involved).
#  3. Take-off angles (dip, 0 = down, 180 = up) from the angle grids versus the 1-D ray calculation.
#  4. Observed travel times = PhaseNet+ pick time - HypoDD (02.dt.cc) origin time, versus grid times at each
#     event's own HypoDD location: median and spread of observed-minus-grid residuals per phase.
#  5. Hand-off check for SeisComP/scrtdd: would the station coordinates of reference/inventory/merged_inventory.xml
#     (the StationXML a SeisComP inventory would be made from) find these grids with the scrtdd plugin's default
#     maxSearchDistance of 10 m?
#
# Usage: python 02_validate_nll_grids.py <reference_dir> <grid_dir> <model_name>
# Output: <grid_dir>/validation.csv (one row per station) and <grid_dir>/validation_picks.csv (one row per pick).

import glob
import math
import os
import sys

import numpy as np
import pandas as pd
from pyproj import Geod
from scipy.optimize import brentq, minimize

if len(sys.argv) != 4:
    sys.exit("usage: python 02_validate_nll_grids.py <reference_dir> <grid_dir> <model_name>")
REF_DIR, GRID_DIR, MODEL = sys.argv[1:4]
BENCH = os.path.join(REF_DIR, "gwangyang_pnplus")
TIME_DIR = os.path.join(GRID_DIR, "time")

# ------------------------------------------------------------------------------------------------
# settings (all disclosed here)
# ------------------------------------------------------------------------------------------------
CENTROID = (35.0000, 127.7286, 13.94)          # lat, lon, depth [km] of the cluster (task definition)
# kim1983 exactly as in hypoDD.inp, top layer extended to -5 km (same as the grids):
LAYER_TOPS = np.array([-5.0, 15.0, 32.0])      # km
VP = np.array([5.98, 6.38, 7.95])              # km/s
VPVS = 1.73
VS = VP / VPVS
MAX_SEARCH_M = 0.1                             # libhdd/pyrtdd default maxSearchDistance [m]
MAX_SEARCH_SC_M = 10.0                         # default of scrtdd's SeisComP plugin 'NLLGrid' (ttt.NLLGrid.<model>.maxSearchDistance)
PERIOD = ("2021-07-20", "2026-02-05")          # benchmark period: inventory epochs overlapping it are checked
ANGLE_QUALITY_CUTOFF = 5                       # scrtdd's AngleGrid default: angles with quality < 5 are rejected
OUTLIER_S = 1.0                                # |obs - grid| above this [s] is reported separately as a likely mis-pick
                                               #  (only for the extra robust summary; the main statistics use all picks)
GEOD = Geod(ellps="WGS84")

# ------------------------------------------------------------------------------------------------
# (b) independent exact 1-D first-arrival calculation for a flat layered model
# ------------------------------------------------------------------------------------------------
def layer_thicknesses(z_top, z_bot, tops):
    # thickness of each layer inside the depth interval [z_top, z_bot]
    bots = np.append(tops[1:], np.inf)
    return np.clip(np.minimum(bots, z_bot) - np.maximum(tops, z_top), 0.0, None)


def direct_ray(x, zs, zr, tops, v):
    # ray going straight up from the source (depth zs) to the receiver (depth zr < zs), Snell's law
    h = layer_thicknesses(zr, zs, tops)
    use = h > 0
    h, vv = h[use], v[use]
    vsrc = v[np.searchsorted(tops, zs, side="right") - 1]
    if x == 0.0:
        return float(np.sum(h / vv)), 180.0
    vmax = vv.max()

    def xoff(u):  # u = p * vmax in [0, 1)
        p = u / vmax
        return np.sum(h * p * vv / np.sqrt(1.0 - (p * vv) ** 2)) - x

    u = brentq(xoff, 0.0, 1.0 - 1e-15, xtol=1e-15, rtol=1e-15, maxiter=500)
    p = u / vmax
    t = float(np.sum(h / (vv * np.sqrt(1.0 - (p * vv) ** 2))))
    theta_src = math.degrees(math.asin(min(1.0, p * vsrc)))   # angle from the UPWARD vertical
    return t, 180.0 - theta_src                                 # dip: 0 = down, 180 = up


def head_waves(x, zs, zr, tops, v):
    # head wave along the top of every deeper, faster layer k: down from the source, along the interface,
    # up to the receiver. Returns a list of (time, interface depth, dip at the source) for valid branches.
    out = []
    vsrc = v[np.searchsorted(tops, zs, side="right") - 1]
    for k in range(1, len(tops)):
        zk = tops[k]
        if zk <= max(zs, zr):
            continue
        hd = layer_thicknesses(zs, zk, tops)[:k]
        hu = layer_thicknesses(zr, zk, tops)[:k]
        vabove = v[:k][(hd + hu) > 0]
        if v[k] <= vabove.max():
            continue
        q = np.sqrt(1.0 / v[:k] ** 2 - 1.0 / v[k] ** 2)
        xcrit = np.sum((hd + hu) * (v[:k] / v[k]) / np.sqrt(1.0 - (v[:k] / v[k]) ** 2))
        if x < xcrit:
            continue
        t = x / v[k] + np.sum((hd + hu) * q)
        out.append((float(t), zk, math.degrees(math.asin(vsrc / v[k]))))
    return out


def first_arrival(x, zs, zr, tops, v):
    t, dip = direct_ray(x, zs, zr, tops, v)
    best = (t, "direct", dip)
    for th, zk, dh in head_waves(x, zs, zr, tops, v):
        if th < best[0]:
            best = (th, f"head{zk:g}km", dh)
    return best


def fermat_head_wave(x, zs, zr, tops, v, k):
    # brute-force check of the head-wave formula: minimise the travel time over the points where the
    # down-going and up-going legs cross each interface (Fermat's principle), no Snell's law used
    zk = tops[k]
    hd = layer_thicknesses(zs, zk, tops)[:k]
    hu = layer_thicknesses(zr, zk, tops)[:k]
    nd, nu = int(np.sum(hd > 0)), int(np.sum(hu > 0))
    hd_, vd = hd[hd > 0], v[:k][hd > 0]
    hu_, vu = hu[hu > 0], v[:k][hu > 0]

    def ttime(dx):
        dxd, dxu = np.abs(dx[:nd]), np.abs(dx[nd:])
        along = x - dxd.sum() - dxu.sum()
        if along < 0:
            return 1e9
        return np.sum(np.hypot(dxd, hd_) / vd) + np.sum(np.hypot(dxu, hu_) / vu) + along / v[k]

    x0 = np.concatenate([hd_ * 0.5, hu_ * 0.5])
    res = minimize(ttime, x0, method="Nelder-Mead", options=dict(xatol=1e-10, fatol=1e-12, maxiter=40000))
    return float(res.fun)


# self-test of the 1-D solver before using it
for xt in (60.0, 80.0, 100.0):
    for k in (1, 2):
        hw = {zk: t for t, zk, _ in head_waves(xt, 13.94, -0.3, LAYER_TOPS, VP)}
        if LAYER_TOPS[k] in hw:
            tf = fermat_head_wave(xt, 13.94, -0.3, LAYER_TOPS, VP, k)
            assert abs(tf - hw[LAYER_TOPS[k]]) < 1e-6, (xt, k, tf, hw)
t_hom, _ = direct_ray(30.0, 13.94, -0.3, LAYER_TOPS, VP)
assert abs(t_hom - math.hypot(30.0, 14.24) / VP[0]) < 1e-9
print("1-D solver self-test passed (head-wave formula = Fermat minimisation to < 1 us; direct ray = straight line)")

# ------------------------------------------------------------------------------------------------
# (a') own numpy reader of NonLinLoc grids (replicates scrtdd's libs/hdd/nll/grid.cpp for 2-D grids)
# ------------------------------------------------------------------------------------------------
# NonLinLoc's TRANS_MERC (src/map_project.c, functions vtm/tm/itm) with NonLinLoc's WGS-84 constants
NLL_ELLIPSOIDS = {"WGS-84": (6378137.0, 1.0 / 298.254)}


class NLLTransMerc:
    def __init__(self, ellipsoid, lat0, lon0):
        a, f = NLL_ELLIPSOIDS[ellipsoid]
        self.a = a
        e2 = 2 * f - f * f
        self.e2, e4, e6 = e2, e2 * e2, e2 ** 3
        e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))
        self.t_e2 = e2 / (1.0 - e2)
        self.c1 = 1.0 - 0.25 * e2 - 3.0 * e4 / 64.0 - 5.0 * e6 / 256.0
        self.c2 = 3.0 * e2 / 8.0 + 3.0 * e4 / 32.0 + 45.0 * e6 / 1024.0
        self.c3 = 15.0 * e4 / 256.0 + 45.0 * e6 / 1024.0
        self.c4 = 35.0 * e6 / 3072.0
        self.ic1 = 1.5 * e1 - 27.0 * e1 ** 3 / 32.0
        self.ic2 = 21.0 * e1 * e1 / 16.0 - 55.0 * e1 ** 4 / 32.0
        self.ic3 = 151.0 * e1 ** 3 / 96.0
        self.ic4 = 1097.0 * e1 ** 4 / 512.0
        self.lon0 = lon0
        self.ycp_m = 0.0                                   # y offset of the origin latitude [m]
        self.ycp_m = self.fwd(lat0, lon0)[1] * 1000.0

    def fwd(self, lat, lon):  # -> x, y in km
        dlon = lon - self.lon0
        lat = math.radians(lat)
        M = self.a * (self.c1 * lat - self.c2 * math.sin(2 * lat) + self.c3 * math.sin(4 * lat) - self.c4 * math.sin(6 * lat))
        N = self.a / math.sqrt(1.0 - self.e2 * math.sin(lat) ** 2)
        T = math.tan(lat) ** 2
        C = self.t_e2 * math.cos(lat) ** 2
        A = math.radians(dlon) * math.cos(lat)
        x = N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T * T + 72 * C - 58 * self.t_e2) * A ** 5 / 120)
        y = M + N * math.tan(lat) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24
                                    + (61 - 58 * T + T * T + 600 * C - 330 * self.t_e2) * A ** 6 / 720)
        return x / 1000.0, (y - self.ycp_m) / 1000.0

    def inv(self, x, y):  # x, y in km -> lat, lon
        x, y = x * 1000.0, y * 1000.0 + self.ycp_m
        mu = y / (self.a * self.c1)
        phi1 = mu + self.ic1 * math.sin(2 * mu) + self.ic2 * math.sin(4 * mu) + self.ic3 * math.sin(6 * mu) + self.ic4 * math.sin(8 * mu)
        C1 = self.t_e2 * math.cos(phi1) ** 2
        T1 = math.tan(phi1) ** 2
        tmp = 1.0 - self.e2 * (1.0 - math.cos(phi1) ** 2)
        N1 = self.a / math.sqrt(tmp)
        R1 = self.a * (1.0 - self.e2) / (tmp * math.sqrt(tmp))
        D = x / N1
        lon = self.lon0 + math.degrees((D - (1 + 2 * T1 + C1) * D ** 3 / 6
                                        + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * self.t_e2 + 24 * T1 * T1) * D ** 5 / 120) / math.cos(phi1))
        lat = phi1 - (N1 * math.tan(phi1) / R1) * (D * D / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * self.t_e2) * D ** 4 / 24
                                                    + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * self.t_e2 - 3 * C1 * C1) * D ** 6 / 720)
        return math.degrees(lat), lon


class Grid2D:
    def __init__(self, base):
        lines = [l.split() for l in open(base + ".hdr") if l.strip()]
        h = lines[0]
        self.numx, self.numy, self.numz = int(h[0]), int(h[1]), int(h[2])
        self.origx, self.origy, self.origz = float(h[3]), float(h[4]), float(h[5])
        self.dx, self.dy, self.dz = float(h[6]), float(h[7]), float(h[8])
        self.type = h[9]
        self.label, self.srcex, self.srcey, self.srcez = lines[1][0], float(lines[1][1]), float(lines[1][2]), float(lines[1][3])
        t = lines[2]
        assert t[1] == "TRANS_MERC" and t[2] == "RefEllipsoid" and t[4] == "LatOrig" and t[6] == "LongOrig" and float(t[9]) == 0.0, t
        self.trans = NLLTransMerc(t[3], float(t[5]), float(t[7]))
        raw = np.fromfile(base + ".buf", dtype="<f4")
        nsheet = raw.size // (self.numy * self.numz)       # NonLinLoc stores 2 sheets for 2-D grids, scrtdd reads sheet 0
        self.data = raw.reshape(nsheet, self.numy, self.numz)[0]

    def station_latlon(self):
        return self.trans.inv(self.srcex, self.srcey)

    def _corners(self, lat, lon, depth):
        x, y = self.trans.fwd(lat, lon)
        dist = math.hypot(x - self.srcex, y - self.srcey)
        yoff = (dist - self.origy) / self.dy
        zoff = (depth - self.origz) / self.dz
        iy0, iz0 = int(yoff), int(zoff)
        if iy0 == self.numy - 1:
            iy0 -= 1
        if iz0 == self.numz - 1:
            iz0 -= 1
        return dist, yoff - iy0, zoff - iz0, iy0, iz0

    def time(self, lat, lon, depth):
        _, yd, zd, iy, iz = self._corners(lat, lon, depth)
        v = self.data
        return float((1 - yd) * (1 - zd) * v[iy, iz] + (1 - yd) * zd * v[iy, iz + 1]
                     + yd * (1 - zd) * v[iy + 1, iz] + yd * zd * v[iy + 1, iz + 1])

    def angle(self, lat, lon, depth):
        _, yd, zd, iy, iz = self._corners(lat, lon, depth)
        bits = self.data.view("<u4")
        c = np.array([bits[iy, iz], bits[iy, iz + 1], bits[iy + 1, iz], bits[iy + 1, iz + 1]], dtype=np.uint64)
        qual = int((c & 0xF).min())
        dip = ((c & 0xFFFF) >> 4).astype(float) / 10.0
        d = (1 - yd) * (1 - zd) * dip[0] + (1 - yd) * zd * dip[1] + yd * (1 - zd) * dip[2] + yd * zd * dip[3]
        return float(d), qual


# ------------------------------------------------------------------------------------------------
# stations and grids
# ------------------------------------------------------------------------------------------------
st = pd.read_csv(os.path.join(GRID_DIR, "stations_gridded.csv"))
grids = {}
for ph in ("P", "S"):
    for code in st.Code:
        grids[(ph, code, "time")] = Grid2D(os.path.join(TIME_DIR, f"{MODEL}.{ph}.{code}.time"))
        grids[(ph, code, "angle")] = Grid2D(os.path.join(TIME_DIR, f"{MODEL}.{ph}.{code}.angle"))
n_hdr = len(glob.glob(os.path.join(TIME_DIR, f"{MODEL}.*.time.hdr")))
print(f"{len(st)} stations, {n_hdr} time grids found in {TIME_DIR}")

# 1. station location round trip (header -> lat/lon/elevation) for every time and angle grid
loc_rows = []
for (ph, code, kind), g in grids.items():
    s = st[st.Code == code].iloc[0]
    glat, glon = g.station_latlon()
    _, _, dh = GEOD.inv(s.Longitude, s.Latitude, glon, glat)
    loc_rows.append(dict(Code=code, phase=ph, kind=kind, horiz_err_m=dh, depth_err_m=(g.srcez + s.Elevation_m / 1000.0) * 1000.0))
loc = pd.DataFrame(loc_rows)
print(f"header station location vs table: max horizontal error {loc.horiz_err_m.abs().max() * 1000:.3f} mm, "
      f"max depth error {loc.depth_err_m.abs().max() * 1000:.3f} mm  (scrtdd default tolerance {MAX_SEARCH_M} m)")

# grid extent check
g0 = grids[("P", st.Code.iloc[0], "time")]
print(f"grid: distance {g0.origy:g}..{g0.origy + (g0.numy - 1) * g0.dy:g} km, depth {g0.origz:g}..{g0.origz + (g0.numz - 1) * g0.dz:g} km, "
      f"spacing {g0.dy:g} km ({g0.numy} x {g0.numz} nodes)")

# pyrtdd reader (the reader scrtdd uses); fall back to numpy only if pyrtdd is not importable
try:
    from pyrtdd.hdd import NLLGrid
    ttt = NLLGrid(gridPath=TIME_DIR, gridModel=MODEL, maxSearchDistance=MAX_SEARCH_M)
    HAVE_PYRTDD = True
    print(f"pyrtdd NLLGrid opened with gridPath={TIME_DIR} gridModel={MODEL} maxSearchDistance={MAX_SEARCH_M} m")
except ImportError as e:
    HAVE_PYRTDD = False
    print(f"!! pyrtdd not importable ({e}); using only the numpy reader")

# ------------------------------------------------------------------------------------------------
# 2./3. centroid: grid vs independent 1-D, take-off angles
# ------------------------------------------------------------------------------------------------
clat, clon, cdep = CENTROID
rows = []
for s in st.itertuples():
    az, _, dist_m = GEOD.inv(clon, clat, s.Longitude, s.Latitude)
    x = dist_m / 1000.0
    zr = -s.Elevation_m / 1000.0
    tm = grids[("P", s.Code, "time")].trans
    xs, ys = tm.fwd(s.Latitude, s.Longitude)
    xc, yc = tm.fwd(clat, clon)
    r = dict(Network=s.Network, Code=s.Code, Latitude=s.Latitude, Longitude=s.Longitude, Elevation_m=s.Elevation_m,
             dist_km=round(x, 4), azimuth_deg=round(az % 360, 2),
             proj_dist_err_m=round((math.hypot(xs - xc, ys - yc) - x) * 1000.0, 3))
    for ph, v in (("P", VP), ("S", VS)):
        t1, branch, dip1 = first_arrival(x, cdep, zr, LAYER_TOPS, v)
        t1_sl, branch_sl, _ = first_arrival(x, cdep, 0.0, LAYER_TOPS, v)       # station at sea level (as HypoDD)
        tn = grids[(ph, s.Code, "time")].time(clat, clon, cdep)
        dipn, qual = grids[(ph, s.Code, "angle")].angle(clat, clon, cdep)
        r[f"{ph}_1d_s"] = t1
        r[f"{ph}_1d_branch"] = branch
        r[f"{ph}_1d_sealevel_s"] = t1_sl
        r[f"{ph}_grid_numpy_s"] = tn
        if HAVE_PYRTDD:
            tg = ttt.compute(clat, clon, cdep, s.Latitude, s.Longitude, s.Elevation_m, ph)
            try:
                _, _, dipg, _, _ = ttt.computeAll(clat, clon, cdep, s.Latitude, s.Longitude, s.Elevation_m, ph)
            except Exception as e:  # scrtdd refuses angles of quality < 5
                dipg = np.nan
                print(f"!! pyrtdd computeAll failed for {s.Code} {ph}: {e}")
        else:
            tg, dipg = tn, dipn
        r[f"{ph}_grid_s"] = tg
        r[f"{ph}_grid_minus_1d_s"] = tg - t1
        r[f"{ph}_reader_diff_s"] = tg - tn
        r[f"{ph}_dip_grid_deg"] = dipg
        r[f"{ph}_dip_grid_numpy_deg"] = dipn
        r[f"{ph}_dip_1d_deg"] = dip1
        r[f"{ph}_dip_grid_minus_1d_deg"] = dipg - dip1
        r[f"{ph}_angle_quality"] = qual
    rows.append(r)
val = pd.DataFrame(rows)

# ------------------------------------------------------------------------------------------------
# 4. observed travel times (PhaseNet+ picks - HypoDD 02.dt.cc origin times)
# ------------------------------------------------------------------------------------------------
reloc = pd.read_csv(os.path.join(BENCH, "2.HypoDD", "02.dt.cc", "hypoDD.reloc"), sep=r"\s+", header=None)
reloc = reloc.rename(columns={0: "id", 1: "lat", 2: "lon", 3: "depth", 10: "yr", 11: "mo", 12: "dy", 13: "hr", 14: "mi", 15: "sc"})
reloc["origin"] = [pd.Timestamp(int(a.yr), int(a.mo), int(a.dy), int(a.hr), int(a.mi), tz="UTC") + pd.Timedelta(seconds=float(a.sc))
                   for a in reloc.itertuples()]
picks = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(BENCH, "picks", "*_picks.csv")))], ignore_index=True)
picks["Time"] = pd.to_datetime(picks["Time"], utc=True)
# event ids of the pick files are KMA origin times (YYYYMMDDhhmmss); match each to the nearest HypoDD origin
ev_map = {}
for eid in sorted(picks.Event_ID.unique()):
    t_kma = pd.Timestamp(pd.to_datetime(str(eid), format="%Y%m%d%H%M%S"), tz="UTC")
    dt = (reloc.origin - t_kma).abs()
    i = int(dt.idxmin())
    if dt[i] > pd.Timedelta(seconds=5):
        sys.exit(f"no HypoDD event within 5 s of pick event {eid}")
    ev_map[eid] = i
assert len(set(ev_map.values())) == len(ev_map), "two pick events matched the same HypoDD event"
print(f"{len(picks)} picks of {len(ev_map)} events matched to HypoDD 02.dt.cc relocations "
      f"(max |KMA id time - HypoDD origin| = {max((reloc.origin[i] - pd.Timestamp(pd.to_datetime(str(e), format='%Y%m%d%H%M%S'), tz='UTC')).total_seconds() for e, i in ev_map.items()):.2f} s)")

stn = st.set_index("Code")
prow = []
for p in picks.itertuples():
    ev = reloc.loc[ev_map[p.Event_ID]]
    s = stn.loc[p.Station]
    tobs = (p.Time - ev.origin).total_seconds()
    dipg = np.nan
    if HAVE_PYRTDD:
        tg = ttt.compute(ev.lat, ev.lon, ev.depth, s.Latitude, s.Longitude, s.Elevation_m, p.Phase)
        try:
            dipg = ttt.computeAll(ev.lat, ev.lon, ev.depth, s.Latitude, s.Longitude, s.Elevation_m, p.Phase)[2]
        except Exception as e:
            print(f"!! pyrtdd computeAll failed for event {p.Event_ID} {p.Station} {p.Phase}: {e}")
    else:
        tg = grids[(p.Phase, p.Station, "time")].time(ev.lat, ev.lon, ev.depth)
    _, _, dist_m = GEOD.inv(ev.lon, ev.lat, s.Longitude, s.Latitude)
    v = VP if p.Phase == "P" else VS
    t1 = first_arrival(dist_m / 1000.0, ev.depth, -s.Elevation_m / 1000.0, LAYER_TOPS, v)[0]
    t1_sl = first_arrival(dist_m / 1000.0, ev.depth, 0.0, LAYER_TOPS, v)[0]
    prow.append(dict(Event_ID=p.Event_ID, hypodd_id=int(ev.id), Station=p.Station, Phase=p.Phase, Probability=p.Probability,
                     dist_km=dist_m / 1000.0, t_obs_s=tobs, t_grid_s=tg, dip_grid_deg=dipg, t_1d_s=t1, t_1d_sealevel_s=t1_sl,
                     res_obs_minus_grid_s=tobs - tg, res_obs_minus_1d_sealevel_s=tobs - t1_sl))
pk = pd.DataFrame(prow)

for ph in ("P", "S"):
    g = pk[pk.Phase == ph].groupby("Station")
    val[f"{ph}_n_obs"] = val.Code.map(g.size()).fillna(0).astype(int)
    val[f"{ph}_median_obs_minus_grid_s"] = val.Code.map(g.res_obs_minus_grid_s.median())

# 5. merged_inventory.xml coordinates vs the grids (station-level coordinates of epochs overlapping the period)
inv_rows = []
inv_file = os.path.join(REF_DIR, "inventory", "merged_inventory.xml")
if HAVE_PYRTDD and os.path.exists(inv_file):
    from obspy import UTCDateTime, read_inventory
    inv = read_inventory(inv_file)
    t0, t1 = UTCDateTime(PERIOD[0]), UTCDateTime(PERIOD[1])
    ttt_sc = NLLGrid(gridPath=TIME_DIR, gridModel=MODEL, maxSearchDistance=MAX_SEARCH_SC_M)
    for s in st.itertuples():
        epochs = [sta for net in inv if net.code == s.Network for sta in net if sta.code == s.Code
                  and (sta.start_date is None or sta.start_date <= t1) and (sta.end_date is None or sta.end_date >= t0)]
        if not epochs:
            inv_rows.append(dict(Code=s.Code, inv_epochs=0))
            continue
        e = epochs[-1]
        _, _, dh = GEOD.inv(s.Longitude, s.Latitude, e.longitude, e.latitude)
        try:
            ttt_sc.compute(clat, clon, cdep, e.latitude, e.longitude, e.elevation, "P")
            ok = True
        except Exception:
            ok = False
        inv_rows.append(dict(Code=s.Code, inv_epochs=len(epochs), inv_latitude=e.latitude, inv_longitude=e.longitude,
                             inv_elevation_m=e.elevation, inv_offset_horiz_m=dh, inv_offset_vert_m=e.elevation - s.Elevation_m,
                             inv_offset_3d_m=math.hypot(dh, e.elevation - s.Elevation_m), inv_lookup_ok_10m=ok))
    invdf = pd.DataFrame(inv_rows).set_index("Code")
    for c in invdf.columns:
        val[c] = val.Code.map(invdf[c])
else:
    print("!! inventory check skipped (needs pyrtdd and reference/inventory/merged_inventory.xml)")

val["header_horiz_err_mm"] = val.Code.map(loc.groupby("Code").horiz_err_m.apply(lambda a: a.abs().max() * 1000.0))
val["header_depth_err_mm"] = val.Code.map(loc.groupby("Code").depth_err_m.apply(lambda a: a.abs().max() * 1000.0))

val.to_csv(os.path.join(GRID_DIR, "validation.csv"), index=False, float_format="%.6f")
pk.to_csv(os.path.join(GRID_DIR, "validation_picks.csv"), index=False, float_format="%.6f")

# ------------------------------------------------------------------------------------------------
# summary
# ------------------------------------------------------------------------------------------------
pd.set_option("display.width", 200)
print()
print(f"=== grid vs independent 1-D at the centroid {CENTROID} ({'pyrtdd NLLGrid' if HAVE_PYRTDD else 'numpy reader'}), {len(val)} stations")
for ph in ("P", "S"):
    d = val[f"{ph}_grid_minus_1d_s"]
    i = d.abs().idxmax()
    print(f"{ph}: grid - 1D  max |.| = {d.abs().max() * 1000:.2f} ms (station {val.Code[i]}, {val.dist_km[i]:.1f} km, "
          f"{val[f'{ph}_1d_branch'][i]}), mean {d.mean() * 1000:+.2f} ms, median {d.median() * 1000:+.2f} ms; "
          f"pyrtdd vs numpy reader max |.| = {val[f'{ph}_reader_diff_s'].abs().max() * 1e6:.3f} us")
    print(f"   1-D first-arrival branches: {val[f'{ph}_1d_branch'].value_counts().to_dict()}")
    dd = val[f"{ph}_dip_grid_minus_1d_deg"]
    print(f"   take-off dip grid - 1D: max |.| = {dd.abs().max():.2f} deg, median {dd.median():+.2f} deg; "
          f"angle quality at centroid min {val[f'{ph}_angle_quality'].min()} "
          f"({int((val[f'{ph}_angle_quality'] < ANGLE_QUALITY_CUTOFF).sum())} stations below scrtdd's cutoff {ANGLE_QUALITY_CUTOFF})")
print("projection: |projected - geodesic distance| max %.2f m" % val.proj_dist_err_m.abs().max())
print("elevation effect (1-D, station at its elevation minus station at sea level): P %.3f..%.3f s, S %.3f..%.3f s" % (
    (val.P_1d_s - val.P_1d_sealevel_s).min(), (val.P_1d_s - val.P_1d_sealevel_s).max(),
    (val.S_1d_s - val.S_1d_sealevel_s).min(), (val.S_1d_s - val.S_1d_sealevel_s).max()))

print()
print("=== take-off angles for a few stations (dip: 0 = down, 180 = up)")
few = val.sort_values("dist_km").iloc[[0, len(val) // 4, len(val) // 2, 3 * len(val) // 4, len(val) - 1]]
print(few[["Code", "dist_km", "P_1d_branch", "P_dip_grid_deg", "P_dip_1d_deg", "P_angle_quality",
           "S_1d_branch", "S_dip_grid_deg", "S_dip_1d_deg", "S_angle_quality"]].to_string(index=False, float_format=lambda v: f"{v:.2f}"))

print()
print(f"=== observed (PhaseNet+ pick - HypoDD origin) minus grid travel time, {len(pk)} picks")
for ph in ("P", "S"):
    r = pk[pk.Phase == ph].res_obs_minus_grid_s
    r0 = pk[pk.Phase == ph].res_obs_minus_1d_sealevel_s
    q25, q75 = r.quantile([0.25, 0.75])
    mad = 1.4826 * (r - r.median()).abs().median()
    print(f"{ph}: N {len(r)}  median {r.median():+.3f} s  IQR [{q25:+.3f}, {q75:+.3f}] s  MAD*1.4826 {mad:.3f} s  "
          f"mean {r.mean():+.3f} s  std {r.std():.3f} s  5-95% [{r.quantile(0.05):+.3f}, {r.quantile(0.95):+.3f}] s  |  "
          f"same with stations at sea level (HypoDD geometry): median {r0.median():+.3f} s")
print(f"take-off angles via pyrtdd computeAll at the event locations: {int(pk.dip_grid_deg.notna().sum())} of {len(pk)} picks OK")
print(f"--- extra robust view: picks with |obs - grid| > {OUTLIER_S:g} s are listed and left out (likely mis-picks)")
for ph in ("P", "S"):
    q = pk[(pk.Phase == ph) & (pk.res_obs_minus_grid_s.abs() <= OUTLIER_S)]
    b, a = np.polyfit(q.t_grid_s, q.res_obs_minus_grid_s, 1)
    print(f"{ph}: {int(((pk.Phase == ph) & (pk.res_obs_minus_grid_s.abs() > OUTLIER_S)).sum())} outliers; remaining N {len(q)}  "
          f"median {q.res_obs_minus_grid_s.median():+.3f} s  IQR [{q.res_obs_minus_grid_s.quantile(0.25):+.3f}, "
          f"{q.res_obs_minus_grid_s.quantile(0.75):+.3f}] s  std {q.res_obs_minus_grid_s.std():.3f} s  "
          f"linear trend: res = {a:+.3f} s {b:+.4f} * t_grid")
    for lo, hi in ((0, 30), (30, 60), (60, 80), (80, 120)):
        r = q[(q.dist_km >= lo) & (q.dist_km < hi)].res_obs_minus_grid_s
        print(f"   epicentral distance {lo:3d}-{hi:3d} km: N {len(r):3d}  median {r.median():+.3f} s")
print(pk[pk.res_obs_minus_grid_s.abs() > OUTLIER_S].sort_values(["Phase", "res_obs_minus_grid_s"])[
    ["Event_ID", "Station", "Phase", "Probability", "dist_km", "t_obs_s", "t_grid_s", "res_obs_minus_grid_s"]].to_string(index=False))
w = pk[pk.res_obs_minus_grid_s.abs() <= OUTLIER_S].pivot_table(index=["Event_ID", "Station"], columns="Phase",
                                                                values=["t_obs_s", "t_grid_s"]).dropna()
print(f"S/P travel-time ratio on {len(w)} event-station pairs with both phases: observed median "
      f"{(w[('t_obs_s', 'S')] / w[('t_obs_s', 'P')]).median():.4f}, grid (model Vp/Vs {VPVS}) median "
      f"{(w[('t_grid_s', 'S')] / w[('t_grid_s', 'P')]).median():.4f}")
if inv_rows:
    print()
    print(f"=== hand-off check: station coordinates of merged_inventory.xml vs the grids (scrtdd plugin default "
          f"maxSearchDistance {MAX_SEARCH_SC_M:g} m)")
    have = val[val.inv_epochs > 0]
    print(f"stations in the inventory for {PERIOD[0]}..{PERIOD[1]}: {len(have)} of {len(val)}; missing: "
          f"{sorted(val.Code[val.inv_epochs == 0])}")
    print(f"inventory elevations: {sorted(set(have.inv_elevation_m))} m; horizontal offsets > 1 m: "
          f"{have[have.inv_offset_horiz_m > 1][['Code', 'inv_offset_horiz_m']].round(1).values.tolist()}")
    print(f"grid found with inventory coordinates: {int(have.inv_lookup_ok_10m.sum())} of {len(val)} stations "
          f"(3-D offset to the grid station location {have.inv_offset_3d_m.min():.0f}..{have.inv_offset_3d_m.max():.0f} m)")
print(f"\nwrote {os.path.join(GRID_DIR, 'validation.csv')} and validation_picks.csv")
