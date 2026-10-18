# ray1d.py -- independent first-arrival travel times for a flat-earth 1-D velocity model made of
# linear-gradient segments (the NCSS 'CRT' model type), used to check the NonLinLoc grids.
#
# Method: the model is cut into thin homogeneous sub-layers (default 5 m, velocity = value at the
# sub-layer centre). For each ray parameter p the horizontal distance X(p) and time T(p) are summed
# layer by layer (X = sum h*p*v/sqrt(1-p^2 v^2), T = sum h/(v*sqrt(1-p^2 v^2))). Three branches are
# evaluated and the earliest time at the requested distance is returned:
#   up    : ray leaves the source upwards and goes straight to the receiver
#   turn  : ray leaves the source downwards, turns where p*v reaches 1, comes back up
#   head  : head wave along the top of the homogeneous half-space (p = 1/v_halfspace)
# Distances are flat (km), depths positive down (km), receivers may be above sea level (z < 0).
# Nothing here is shared with NonLinLoc (which solves the eikonal equation on a grid).

import numpy as np


class Model1D:
    def __init__(self, z_pts, v_pts, z_top, dz=0.005, below_half_km=40.0):
        """z_pts/v_pts: velocity-depth points, linear in between; v is constant above z_pts[0]
        (up to z_top) and below z_pts[-1] (half-space, sampled down to below_half_km deeper)."""
        self.zp = np.asarray(z_pts, float)
        self.vp = np.asarray(v_pts, float)
        self.z_top = float(z_top)
        self.z_half = float(self.zp[-1])
        self.v_half = float(self.vp[-1])
        z_bot = self.z_half + below_half_km
        n = int(round((z_bot - self.z_top) / dz))
        self.edges = np.linspace(self.z_top, z_bot, n + 1)
        mid = 0.5 * (self.edges[:-1] + self.edges[1:])
        self.v = np.interp(mid, self.zp, self.vp)      # constant outside the point range
        self.h = np.diff(self.edges)

    def _slice(self, z1, z2):
        """thicknesses and velocities of the sub-layers between depths z1 < z2 (partial ends)."""
        e = self.edges
        top = np.clip(e[:-1], z1, z2)
        bot = np.clip(e[1:], z1, z2)
        h = bot - top
        m = h > 1e-12
        return h[m], self.v[m]

    @staticmethod
    def _xt(h, v, p):
        a = np.outer(p, v)
        with np.errstate(invalid="ignore", divide="ignore"):
            c = np.sqrt(1.0 - a * a)
            dx = h * a / c
            dt = h / (v * c)
        bad = a >= 1.0
        dx[bad] = np.nan
        dt[bad] = np.nan
        return dx, dt

    def time(self, dist, z_src, z_rcv, n_p=6000, return_branch=False):
        """first-arrival time (s) at horizontal distance dist (km) between a source at depth z_src
        and a receiver at depth z_rcv (z_rcv < z_src)."""
        dist = np.atleast_1d(np.asarray(dist, float))
        zr, zs = (z_rcv, z_src) if z_rcv < z_src else (z_src, z_rcv)
        hu, vu = self._slice(zr, zs)
        if len(hu) == 0:                       # source and receiver at the same depth
            hu = np.array([1e-9])
            vu = np.array([np.interp(zs, self.zp, self.vp)])
        vmax_up = vu.max()
        best = np.full(dist.shape, np.inf)
        branch = np.full(dist.shape, "", dtype=object)
        # --- up-going branch (monotonic X(p))
        th = np.linspace(0.0, np.pi / 2, n_p, endpoint=False)
        p = np.sin(th) / vmax_up
        dx, dt = self._xt(hu, vu, p)
        Xu, Tu = np.nansum(dx, 1), np.nansum(dt, 1)
        ok = dist <= Xu[-1]
        tu = np.interp(dist, Xu, Tu)
        upd = ok & (tu < best)
        best[upd], branch[upd] = tu[upd], "up"
        # --- turning rays below the source (only possible above the half-space top)
        hd, vd = self._slice(zs, self.z_half) if zs < self.z_half else (np.array([]), np.array([]))
        if len(hd):
            vmax_below = vd.max()
            pmin = 1.0 / max(vmax_below, self.v_half)     # deeper rays reach the half-space
            pmax = 1.0 / vmax_up
            if pmin < pmax:
                pt = np.linspace(pmin, pmax, n_p, endpoint=False)[1:]
                dxd, dtd = self._xt(hd, vd, pt)
                # sum down to the first layer where the ray turns (p*v >= 1 -> nan)
                turned = np.isnan(dxd)
                first = np.where(turned.any(1), turned.argmax(1), -1)
                keep = first >= 0
                cx = np.nancumsum(np.nan_to_num(dxd), 1)
                ct = np.nancumsum(np.nan_to_num(dtd), 1)
                idx = np.clip(first - 1, 0, None)
                Xd = np.where(first > 0, cx[np.arange(len(pt)), idx], 0.0)
                Td = np.where(first > 0, ct[np.arange(len(pt)), idx], 0.0)
                dxu, dtu = self._xt(hu, vu, pt)
                X = 2 * Xd + np.nansum(dxu, 1)
                T = 2 * Td + np.nansum(dtu, 1)
                X, T = X[keep], T[keep]
                for i, d in enumerate(dist):
                    s = np.sign(X - d)
                    k = np.where(s[:-1] * s[1:] <= 0)[0]
                    for j in k:
                        if X[j + 1] == X[j]:
                            continue
                        f = (d - X[j]) / (X[j + 1] - X[j])
                        tt = T[j] + f * (T[j + 1] - T[j])
                        if tt < best[i]:
                            best[i], branch[i] = tt, "turn"
        # --- head wave along the half-space top (source above the half-space)
        if zs <= self.z_half and self.v_half > max(vmax_up, vd.max() if len(hd) else 0):
            ph = np.array([1.0 / self.v_half])
            dxd, dtd = self._xt(hd, vd, ph)
            dxu, dtu = self._xt(hu, vu, ph)
            X0 = 2 * np.nansum(dxd) + np.nansum(dxu)
            T0 = 2 * np.nansum(dtd) + np.nansum(dtu)
            th_ = T0 + (dist - X0) * ph[0]
            upd = (dist >= X0) & (th_ < best)
            best[upd], branch[upd] = th_[upd], "head"
        return (best, branch) if return_branch else best
