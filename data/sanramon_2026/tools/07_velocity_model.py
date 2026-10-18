# 07_velocity_model.py -- the NCSS routine velocity model for the San Ramon 2025-26 sequence and the
# files inputs/velocity_model.csv (+ the NCSS travel-time table for later checks). Copied from the
# 2015 tool; differences: (a) the model weights of every benchmark event are computed with the
# Hypoinverse multiple-model rule (hyp1.40.pdf pp. 13-15: inside any inner circle -> that model only;
# else cosine-taper weights of the first 3 outer circles hit, normalised, default model 1 makes up a
# total < 1), so the question "does the NCSS use CON here?" is answered per event
# (reference_tables/ncss_model_weights.csv); (b) the datum shift is the median NCSS datum of the
# 2025-26 benchmark events (computed, not typed in).
#
# Sources (all saved under reference/):
#   ncss_hypoinverse_metadata/multmod5a.hyp   NCSS multiple-model set-up (NOD = model regions,
#                                             PSM = S/P travel-time relation per model)
#   ncss_hypoinverse_metadata/hypoinverse/models/cor.crt   'CONCORD-CALAVERAS' TTGEN table
#     (multmod5a.hyp loads model 9 from './hypoinverse/models/con.crt'; the 2023 zip has no
#      con.crt but has cor.crt with the title CONCORD-CALAVERAS and the same depth/velocity points
#      as the CON model in Table 8 of NCEDC shadow2000.pdf)
# What it does
#   1. For every benchmark event, distance to every NOD circle in multmod5a.hyp -> which NCSS
#      regional model(s) apply (inner circle = weight 1, transition ring = blended).
#   2. Parses cor.crt: model points, REDV, and the full travel-time table (depth x distance) ->
#      reference_tables/ncss_con_ttgen_table.csv (model-surface source depth, distance, time).
#   3. Writes inputs/velocity_model.csv: rows = model points with linear gradients between rows
#      (last row = half-space), depths referred to sea level by shifting the NCSS model surface to
#      DATUM_KM above sea level; Vs = Vp / VPVS. Extra columns give the gradients and the original
#      model-surface depths, so the table is the exact NCSS gradient model, not a layer cake.
# Usage: python -I 07_velocity_model.py

import json
import math
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

META = os.path.join(C.REF, "ncss_hypoinverse_metadata")
DATUM_KM = None     # median NCSS depth datum of the benchmark events (cols 171-174), set in main()
VPVS = 1.73         # Vp/Vs for S: same as 2015 (W&S 2008 para. 33); 2025-26 picks beyond 10 km: Wadati 1.776 (tool 14)
TOP_KM = -3.0       # the grid top; the first model velocity is extended up to here


def read_nodes():
    nodes, models = [], {}
    default = None
    for ln in open(os.path.join(META, "multmod5a.hyp")):
        if ln.strip().startswith("*") or not ln.strip():
            continue
        mq = re.match(r"^\s*(crt|del)\s+(\d+)\s+'([^']*)'", ln, flags=re.I)
        if mq:                                   # quoted file names contain '/', keep them whole
            if mq.group(1).lower() == "crt":
                models[int(mq.group(2))] = mq.group(3)
            continue
        s = ln.split("/")[0].strip()             # '/' starts a comment on free-format lines
        p = s.split()
        if not p:
            continue
        if p[0].lower() == "mul":
            default = int(p[2])                  # 'mul t 1': multiple models, default model 1
        elif p[0].lower() == "nod":
            v = [float(x) for x in p[1:8]]
            lat = v[0] + v[1] / 60.0
            lon = -(v[2] + v[3] / 60.0)          # west longitudes written positive in the file
            nodes.append(dict(lat=lat, lon=lon, r_in=v[4], r_tr=v[5], model=int(v[6])))
        elif p[0].lower() == "psm":
            models.setdefault(f"psm{p[1]}", (float(p[2]), float(p[3])))
    models["default"] = default
    return nodes, models


def hypoinverse_weights(lat, lon, nodes, default):
    """model weights of one epicentre, Hypoinverse multiple-model rule (hyp1.40 pp. 13-15)."""
    d = [float(km_between(lat, lon, n["lat"], n["lon"])) for n in nodes]
    for n, dk in zip(nodes, d):                  # nodes tested in the order defined
        if dk <= n["r_in"]:
            return {n["model"]: 1.0}
    w, hits = {}, 0
    for n, dk in zip(nodes, d):
        if dk < n["r_in"] + n["r_tr"]:
            x = (dk - n["r_in"]) / n["r_tr"]
            w[n["model"]] = w.get(n["model"], 0.0) + 0.5 * (1 + math.cos(math.pi * x))
            hits += 1
            if hits == 3:
                break
    tot = sum(w.values())
    if tot > 1.0:
        w = {k: v / tot for k, v in w.items()}
    elif tot < 1.0:
        w[default] = w.get(default, 0.0) + 1.0 - tot
    return w


def km_between(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dlat, dlon = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def read_crt(path):
    L = open(path).read().splitlines()
    name, npts, redv = L[0][:20].strip(), int(L[0][20:22]), float(L[0][22:30])
    dep = [float(L[1][5 * i:5 * i + 5]) for i in range(npts)]
    vel = [float(L[2][5 * i:5 * i + 5]) for i in range(npts)]
    dd1, nd1, dd2, nd2 = float(L[3][0:7]), int(L[3][7:10]), float(L[3][10:17]), int(L[3][17:20])
    dz1, nz1, dz2, nz2 = float(L[4][0:7]), int(L[4][7:10]), float(L[4][10:17]), int(L[4][17:20])
    dists = [0.0] + [dd1 * (i + 1) for i in range(nd1)] + [dd1 * nd1 + dd2 * (i + 1) for i in range(nd2)]
    nd = nd1 + nd2 + 1
    rows, i = [], 5
    blocks = nz1 + nz2 + 1
    for b in range(blocks):
        z, v = float(L[i][0:10]), float(L[i][10:20])
        i += 1
        vals = []
        while len(vals) < nd:
            s = L[i]
            vals += [int(s[6 * k:6 * k + 6]) for k in range(len(s) // 6) if s[6 * k:6 * k + 6].strip()]
            i += 1
        for d, iv in zip(dists, vals[:nd]):
            rows.append(dict(depth_model_km=z, dist_km=d,
                             ttime_s=(iv + 32000) * 0.0005 + d * redv, vel_at_depth=v))
    return dict(name=name, npts=npts, redv=redv, depths=dep, vels=vel, grid=(dd1, nd1, dd2, nd2,
                dz1, nz1, dz2, nz2)), pd.DataFrame(rows)


def main():
    global DATUM_KM
    stats = {}
    nodes, models = read_nodes()
    ev = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv"))
    ev = ev[ev.benchmark_event]
    DATUM_KM = round(float(ev.depth_datum_m.median()) / 1000.0, 2)
    stats["datum_km_used"] = DATUM_KM
    stats["datum_m_of_benchmark_events"] = dict(
        min=float(ev.depth_datum_m.min()), median=float(ev.depth_datum_m.median()),
        max=float(ev.depth_datum_m.max()), n_missing=int(ev.depth_datum_m.isna().sum()),
        most_common=ev.depth_datum_m.value_counts().head(5).to_dict())
    # ---- 0. Hypoinverse model weights of every benchmark event (final NCSS epicentre)
    name = {m: os.path.basename(f).split(".")[0] for m, f in models.items()
            if isinstance(m, int)}
    wrows = []
    for r in ev.itertuples():
        w = hypoinverse_weights(r.latitude, r.longitude, nodes, models["default"])
        wrows.append(dict(event_id=r.event_id, latitude=r.latitude, longitude=r.longitude,
                          weights=";".join(f"{name.get(k, k)}:{v:.3f}" for k, v in
                                           sorted(w.items(), key=lambda kv: -kv[1])),
                          con_weight=round(w.get(9, 0.0), 4)))
    wt = pd.DataFrame(wrows)
    wt.to_csv(os.path.join(C.TAB, "ncss_model_weights.csv"), index=False)
    stats["hypoinverse_model_weights"] = dict(
        n_events=int(len(wt)), con_weight_1=int((wt.con_weight >= 0.9999).sum()),
        con_weight_ge_0p9=int((wt.con_weight >= 0.9).sum()),
        con_weight_min=float(wt.con_weight.min()),
        weight_patterns=wt.weights.value_counts().head(10).to_dict(),
        default_model=models["default"])
    # ---- 1. which NCSS model region contains the events
    res = []
    for nd in nodes:
        d = km_between(ev.latitude.values, ev.longitude.values, nd["lat"], nd["lon"])
        res.append(dict(model=nd["model"], file=models.get(nd["model"], "?"), lat=nd["lat"],
                        lon=nd["lon"], r_in=nd["r_in"], r_tr=nd["r_tr"], dmin_km=float(d.min()),
                        dmax_km=float(d.max()), n_inside_inner=int((d <= nd["r_in"]).sum()),
                        n_in_transition=int(((d > nd["r_in"]) & (d <= nd["r_in"] + nd["r_tr"])).sum())))
    rn = pd.DataFrame(res)
    near = rn[(rn.n_inside_inner > 0) | (rn.n_in_transition > 0)]
    stats["nodes_touching_benchmark_events"] = near.to_dict("records")
    # events inside at least one inner circle of model 9 and not touched by any other model
    inner9 = np.zeros(len(ev), bool)
    other = np.zeros(len(ev), bool)
    for nd in nodes:
        d = km_between(ev.latitude.values, ev.longitude.values, nd["lat"], nd["lon"])
        if nd["model"] == 9:
            inner9 |= d <= nd["r_in"]
        else:
            other |= d <= nd["r_in"] + nd["r_tr"]
    stats["events_inside_CON_inner_circle"] = int(inner9.sum())
    stats["events_touching_other_model_regions"] = int(other.sum())
    stats["n_benchmark_events"] = int(len(ev))
    stats["psm_con"] = models.get("psm9")
    stats["psm_all_near_models"] = {f"{m}:{name.get(m, m)}": models.get(f"psm{m}")
                                    for m in sorted(set(near.model))}
    # ---- 2. the CON model and its TTGEN table
    crt, tab = read_crt(os.path.join(META, "hypoinverse", "models", "cor.crt"))
    stats["crt"] = crt
    tab.to_csv(os.path.join(C.TAB, "ncss_con_ttgen_table.csv"), index=False, float_format="%.4f")
    # ---- 3. velocity_model.csv (sea-level depths)
    z = np.array(crt["depths"])
    vp = np.array(crt["vels"])
    grad = np.append(np.diff(vp) / np.diff(z), 0.0)          # half-space: no gradient
    rows = [dict(top_km=TOP_KM, vp_km_s=vp[0], vs_km_s=round(vp[0] / VPVS, 4),
                 vp_grad_per_km=0.0, vs_grad_per_km=0.0, top_km_below_model_surface=None,
                 note=f"constant extension of the first model velocity above the model surface "
                      f"(stations up to {-TOP_KM:.1f} km elevation)")]
    for i in range(len(z)):
        rows.append(dict(top_km=round(z[i] - DATUM_KM, 4), vp_km_s=vp[i],
                         vs_km_s=round(vp[i] / VPVS, 4), vp_grad_per_km=round(grad[i], 6),
                         vs_grad_per_km=round(grad[i] / VPVS, 6),
                         top_km_below_model_surface=z[i],
                         note=("NCSS CON point; linear to next row" if i < len(z) - 1
                               else "NCSS CON half-space")))
    vm = pd.DataFrame(rows)
    vm.to_csv(os.path.join(C.INP, "velocity_model.csv"), index=False)
    stats["velocity_model_csv"] = vm.to_dict("records")
    with open(os.path.join(C.TAB, "stats_07.json"), "w") as f:
        json.dump(stats, f, indent=1, default=str)
    print(json.dumps(stats, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
