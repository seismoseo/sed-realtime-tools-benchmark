#!/usr/bin/env python
# verify_xcorr.py
#
# Independent re-computation of comparison metric (f): rtDD cross-correlation differential times versus the
# reference HypoDD dt.cc, read from the RAW reference files (dt.cc_0.7_combined, dt.cc_P/*, dt.cc_S/*,
# hypoDD.res) and the RAW rtDD outputs (xcorr.csv written by libhdd, input-phase.csv / input-event.csv).
#
# WHY: both agents used reference_tables/dtcc_*.csv made by another script; this file checks the counts,
# the sign convention and the agreement statistics from first principles.
#
# Sign convention (from the libhdd source, dd.cpp + xcorrcache.h):
#   observed DD time for pair (ev1, ev2) = (tt1 - tt2)_catalog - lag(ev1, ev2), with tt = pick - origin,
#   and XCorrCache::get(ev2, ev1) returns -lag. HypoDD dt.cc line under "# id1 id2" = tt(id1) - tt(id2).
# The convention is ALSO tested empirically: the alternative sign (catalog + lag) is evaluated and must be worse.
#
# Run (env pyrtdd): python -I verify_xcorr.py [--apply]   (dry run prints; --apply also writes CSVs here)

import glob
import json
import os

import sys

import numpy as np
import pandas as pd
from obspy import UTCDateTime

APPLY = "--apply" in sys.argv

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
OUT = f"{PROJECT}/runs/verify_gwangyang_reloc"
REF = f"{PROJECT}/data/gwangyang_11ev/reference/gwangyang_pnplus/2.HypoDD/02.dt.cc"
RUNS = {
    "S1": glob.glob(f"{PROJECT}/runs/gwangyang/scrtdd/S1/work/multievent_*")[0],
    "R1f": f"{PROJECT}/runs/gwangyang/pyrtdd/R1f_xcorr_like_reference_hypodd_like_filtered/processing",
    "R1": f"{PROJECT}/runs/gwangyang/pyrtdd/R1_xcorr_like_reference_hypodd_like/processing",
    "S2": glob.glob(f"{PROJECT}/runs/gwangyang/scrtdd/S2/work/multievent_*")[0],
    "R2f": f"{PROJECT}/runs/gwangyang/pyrtdd/R2f_xcorr_default_rtdd_default_filtered/processing",
}
CCMIN = 0.7


def read_hypodd_cc(paths):
    rows = []
    for p in paths:
        e1 = e2 = None
        for line in open(p):
            if line.startswith("#"):
                q = line.split(); e1, e2 = int(q[1]) - 199999, int(q[2]) - 199999
                continue
            q = line.split()
            if len(q) < 4:
                continue
            sta = q[0][2:] if q[0].startswith("KS") else q[0]
            rows.append((e1, e2, sta, q[3], float(q[1]), float(q[2])))
    d = pd.DataFrame(rows, columns=["e1", "e2", "station", "phase", "dt", "cc"])
    sw = d.e1 > d.e2
    d.loc[sw, ["e1", "e2"]] = d.loc[sw, ["e2", "e1"]].values
    d.loc[sw, "dt"] = -d.loc[sw, "dt"]
    return d


def read_res():
    r = pd.read_csv(f"{REF}/hypoDD.res", sep=r"\s+", skiprows=1, header=None,
                    names=["sta", "dt", "c1", "c2", "idx", "qual", "res_ms", "wt", "offs"])
    r = r[r.idx.isin([1, 2])].copy()
    r["station"] = r.sta.str[2:]; r["phase"] = np.where(r.idx == 1, "P", "S")
    r["e1"] = r.c1 - 199999; r["e2"] = r.c2 - 199999
    sw = r.e1 > r.e2
    r.loc[sw, ["e1", "e2"]] = r.loc[sw, ["e2", "e1"]].values
    return set(zip(r.e1, r.e2, r.station, r.phase))


def rtdd_table(folder, sign=-1.0):
    x = pd.read_csv(f"{folder}/xcorr.csv", keep_default_na=False)
    ph = pd.read_csv(f"{folder}/input-phase.csv", keep_default_na=False)
    ev = pd.read_csv(f"{folder}/input-event.csv")
    ot = {int(r.id): UTCDateTime(r.isotime) for r in ev.itertuples()}
    tt = {(int(r.eventId), r.stationCode, r.type): UTCDateTime(r.isotime) - ot[int(r.eventId)] for r in ph.itertuples()}
    x = x[x.valid.astype(str).str.lower() == "true"].copy()
    x["dtcat"] = [tt[(a, s, p)] - tt[(b, s, p)] for a, b, s, p in zip(x.eventId1, x.eventId2, x.stationCode, x.phaseType)]
    x["dt"] = x.dtcat + sign * x.lag
    out = pd.DataFrame(dict(e1=x.eventId1, e2=x.eventId2, station=x.stationCode, phase=x.phaseType, dt=x.dt,
                            cc=x.coefficient, lag=x.lag, dtcat=x.dtcat))
    sw = out.e1 > out.e2
    out.loc[sw, ["e1", "e2"]] = out.loc[sw, ["e2", "e1"]].values
    out.loc[sw, ["dt", "lag", "dtcat"]] = -out.loc[sw, ["dt", "lag", "dtcat"]].values
    return out


def stats(diff_ms):
    d = np.round(np.asarray(diff_ms, float))       # both sides sit on a 1 ms grid; rounding removes float noise
    if len(d) == 0:
        return dict(n=0)
    med = np.median(d)
    return dict(n=int(len(d)), median_ms=float(med), mad_ms=float(np.median(np.abs(d - med))),
                within2=float(np.mean(np.abs(d) <= 2)), within5=float(np.mean(np.abs(d) <= 5)),
                rms_ms=float(np.sqrt(np.mean(d ** 2))), p95_abs_ms=float(np.percentile(np.abs(d), 95)))


def main():
    used = read_hypodd_cc([f"{REF}/dt.cc_0.7_combined"])
    measP = read_hypodd_cc(sorted(glob.glob(f"{REF}/dt.cc_P/*"))); measS = read_hypodd_cc(sorted(glob.glob(f"{REF}/dt.cc_S/*")))
    meas = pd.concat([measP, measS], ignore_index=True)
    kept = read_res()
    res = dict(ref_used_P=int((used.phase == "P").sum()), ref_used_S=int((used.phase == "S").sum()),
               ref_meas_P=int((meas.phase == "P").sum()), ref_meas_S=int((meas.phase == "S").sum()),
               ref_used_min_cc=float(used.cc.min()), ref_kept_final=len(kept))
    # duplicate check
    res["ref_used_duplicates"] = int(used.duplicated(["e1", "e2", "station", "phase"]).sum())
    print(json.dumps(res))
    allrows = []
    for run, folder in RUNS.items():
        for sign, sname in [(-1.0, "cat_minus_lag"), (+1.0, "cat_plus_lag")]:
            r = rtdd_table(folder, sign)
            o = dict(run=run, sign=sname)
            for ph in "PS":
                rp = r[r.phase == ph]
                o[f"n_valid_{ph}"] = int(len(rp)); o[f"n_abs07_{ph}"] = int((rp.cc.abs() >= CCMIN).sum())
                o[f"n_pos07_{ph}"] = int((rp.cc >= CCMIN).sum()); o[f"n_neg07_{ph}"] = int((rp.cc <= -CCMIN).sum())
            ru = r[r.cc.abs() >= CCMIN]
            m = ru.merge(used, on=["e1", "e2", "station", "phase"], suffixes=("_r", "_ref"))
            m["diff_ms"] = (m.dt_r - m.dt_ref) * 1000.0
            m["kept"] = [k in kept for k in zip(m.e1, m.e2, m.station, m.phase)]
            m["ev3"] = (m.e1 == 3) | (m.e2 == 3)
            subsets = {"both": m, "both_P": m[m.phase == "P"], "both_S": m[m.phase == "S"],
                       "without_ev3": m[~m.ev3], "ev3": m[m.ev3], "kept_by_hypodd": m[m.kept], "rejected_by_hypodd": m[~m.kept],
                       "rtdd_neg": m[m.cc_r < 0]}
            for sn, sub in subsets.items():
                st = stats(sub.diff_ms)
                for k, v in st.items():
                    o[f"{sn}_{k}"] = v
                if len(sub) > 2:
                    o[f"{sn}_ccr_signed"] = float(np.corrcoef(sub.cc_r, sub.cc_ref)[0, 1])
                    o[f"{sn}_ccr_abs"] = float(np.corrcoef(sub.cc_r.abs(), sub.cc_ref)[0, 1])
            # all measured triplets (no CC threshold)
            mm = r.merge(meas, on=["e1", "e2", "station", "phase"], suffixes=("_r", "_ref"))
            st = stats((mm.dt_r - mm.dt_ref) * 1000.0)
            o.update({f"allmeas_{k}": v for k, v in st.items()})
            allrows.append(o)
            if sname == "cat_minus_lag" and APPLY:
                m.to_csv(f"{OUT}/verify_xcorr_pairs_{run}.csv", index=False)
    df = pd.DataFrame(allrows)
    if APPLY:
        df.to_csv(f"{OUT}/verify_xcorr.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 200)
    for _, row in df.iterrows():
        print("\n==", row.run, row.sign)
        keys = [k for k in row.index if k not in ("run", "sign")]
        print({k: (round(row[k], 3) if isinstance(row[k], float) else row[k]) for k in keys})
    # S1 vs R1f lag identity
    a = rtdd_table(RUNS["S1"]); b = rtdd_table(RUNS["R1f"])
    j = a.merge(b, on=["e1", "e2", "station", "phase"], suffixes=("_s", "_p"))
    dl = np.round((j.lag_s - j.lag_p) * 1000.0)
    print("\nS1 vs R1f: n", len(j), "lags identical", int((dl == 0).sum()), "P identical", int(((dl == 0) & (j.phase == "P")).sum()),
          "of", int((j.phase == "P").sum()), "S identical", int(((dl == 0) & (j.phase == "S")).sum()), "of", int((j.phase == "S").sum()),
          "max |dCC|", float((j.cc_s - j.cc_p).abs().max()), "max |dlag| ms", float(dl.abs().max()))


if __name__ == "__main__":
    main()
