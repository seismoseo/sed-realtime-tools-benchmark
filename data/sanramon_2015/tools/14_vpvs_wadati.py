# 14_vpvs_wadati.py -- empirical Vp/Vs of the San Ramon swarm from the NCSS picks (supports the
# choice Vs = Vp/1.73 in inputs/velocity_model.md).
#   per event (>= 3 stations with both P and S, P spread > 1 s): Wadati slope a of
#   (tS - tP) against tP; Vp/Vs = 1 + a (does not depend on the origin time). Median over events.
#   pooled: (tS - tP) = a * Ptt + b with Ptt from NCSS origin times (compare NCSS 'psm 9 1.708 0.208').
# Picks: weight code 0-3, benchmark events, earliest P and S per event and net.sta.loc.
# Output: reference_tables/stats_14.json
# Usage: python -I 14_vpvs_wadati.py

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402


def main():
    pk = pd.read_csv(os.path.join(C.TAB, "picks_ncss.csv"), keep_default_na=False,
                     dtype={"location": str})
    pk = pk[(pk.benchmark_event.astype(str) == "True") & (pd.to_numeric(pk.weight_code) <= 3)]
    pk["t"] = pd.to_datetime(pk.time_utc.str.rstrip("Z"))
    k = ["event_id", "network", "station", "location"]
    p = pk[pk.phase == "P"].groupby(k).t.min()
    s = pk[pk.phase == "S"].groupby(k).t.min()
    ev = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv")).set_index("event_id")
    j = pd.concat([p.rename("tp"), s.rename("ts")], axis=1).dropna().reset_index()
    j["sp"] = (j.ts - j.tp).dt.total_seconds()
    j["ptt"] = (j.tp - pd.to_datetime(j.event_id.map(ev.origin_time_utc).str.rstrip("Z"))
                ).dt.total_seconds()
    n_bad = int((j.sp <= 0).sum())
    j = j[j.sp > 0]
    slopes = []
    for _, g in j.groupby("event_id"):
        rel = (g.tp - g.tp.min()).dt.total_seconds()
        if len(g) >= 3 and rel.max() > 1.0:
            slopes.append(np.polyfit(rel, g.sp, 1)[0])
    slopes = np.array(slopes)
    a, b = np.polyfit(j.ptt, j.sp, 1)
    st = dict(n_pairs=int(len(j)), n_pairs_s_not_after_p=n_bad, n_events_wadati=int(len(slopes)),
              vpvs_median=float(1 + np.median(slopes)),
              vpvs_iqr=[float(x) for x in np.percentile(1 + slopes, [25, 75])],
              pooled_fit=dict(vpvs=float(1 + a), intercept_s=float(b)),
              median_sp_residual_s={
                  "NCSS psm 1.708 +0.208": float((j.sp - (0.708 * j.ptt + 0.208)).median()),
                  "Vp/Vs 1.78": float((j.sp - 0.78 * j.ptt).median()),
                  "Vp/Vs 1.73": float((j.sp - 0.73 * j.ptt).median())})
    with open(os.path.join(C.TAB, "stats_14.json"), "w") as f:
        json.dump(st, f, indent=1)
    print(json.dumps(st, indent=1))


if __name__ == "__main__":
    main()
