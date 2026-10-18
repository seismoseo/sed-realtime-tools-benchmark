# 05_compare_picks.py -- step T helper (run in conda env 'pyrtdd': pandas).
#
# Compares the picks scautopick + scdlrtpicker wrote (SeisComP XML, --ep output) with the PhaseNet+
# picks of the same event (reference_tables/picks_phasenet_plus.csv, made in step C2).
#
# Matching rule (one-to-one, per station and phase):
#   a SeisComP P pick (methodID DL3C) matches a PhaseNet+ P pick of the same station if |dt| <= --p-tol,
#   a SeisComP S pick (methodID SDL3C) matches a PhaseNet+ S pick of the same station if |dt| <= --s-tol;
#   dt = SeisComP time - PhaseNet+ time. Candidate pairs are taken in order of increasing |dt| and each
#   pick is used at most once.
# Picks are compared by station code only, because scautopick stores S picks on the vertical channel
# (e.g. HHZ) while the PhaseNet+ table names the horizontal channel for S.
# Every SeisComP pick without a partner gets a reason (near_duplicate, before_event, after_event,
# no_reference; defined at UNMATCHED_CLASSES below), so nothing is silently dropped from the count.
#
# Outputs (prefix --out):
#   <out>_reference_vs_seiscomp.csv  every PhaseNet+ pick of the event, with the matched SeisComP pick
#   <out>_seiscomp_picks.csv         every SeisComP pick, with match status
#   <out>_summary.json               counts and |dt| statistics (all stations, and bound stations only)
#
# Usage: python 05_compare_picks.py --picks-xml picks.xml --ref picks_phasenet_plus.csv \
#            --kma-id 20210827220322 --bound stations_bound.csv --out <prefix>

import argparse
import json
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd


def read_scml_picks(path):
    root = ET.parse(path).getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    rows = []
    for p in root.iter(f"{ns}pick"):
        wf = p.find(f"{ns}waveformID")
        comments = {c.findtext(f"{ns}id"): c.findtext(f"{ns}text") for c in p.findall(f"{ns}comment")}
        rows.append(dict(
            pick_id=p.get("publicID"),
            time=pd.Timestamp(p.find(f"{ns}time/{ns}value").text),
            network=wf.get("networkCode"),
            station=wf.get("stationCode"),
            channel=wf.get("channelCode"),
            method=p.findtext(f"{ns}methodID"),
            phase=p.findtext(f"{ns}phaseHint"),
            confidence=float(comments.get("SNR", comments.get("confidence", "nan"))),
            ref_pick_id=comments.get("RefPickID", ""),
        ))
    cols = ["pick_id", "time", "network", "station", "channel", "method", "phase", "confidence",
            "ref_pick_id"]
    df = pd.DataFrame(rows, columns=cols)       # keeps the columns even when there is no pick
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def match(ref, sc, tol):
    # all candidate pairs within tolerance, smallest |dt| first, each pick used once
    pairs = []
    for i, r in ref.iterrows():
        cand = sc[sc["station"] == r["station"]]
        for j, s in cand.iterrows():
            dt = (s["time"] - r["time"]).total_seconds()
            if abs(dt) <= tol:
                pairs.append((abs(dt), dt, i, j))
    pairs.sort()
    used_r, used_s, out = set(), set(), {}
    for adt, dt, i, j in pairs:
        if i in used_r or j in used_s:
            continue
        used_r.add(i)
        used_s.add(j)
        out[i] = (j, dt)
    return out


# Why a SeisComP pick has no PhaseNet+ partner:
#   near_duplicate : another SeisComP pick of the same station and phase lies within --dup-tol
#                    (two detector triggers whose model windows both contain the same onset)
#   before_event   : earlier than the event's first PhaseNet+ pick minus 1 s (noise or an uncatalogued event)
#   after_event    : later than the event's last PhaseNet+ pick plus 10 s (coda, noise or a later event)
#   no_reference   : inside the event window, but no PhaseNet+ pick of this phase within the tolerance
UNMATCHED_CLASSES = ("near_duplicate", "before_event", "after_event", "no_reference")


def classify_unmatched(sc, j, ref, dup_tol):
    row = sc.loc[j]
    same = sc[(sc["station"] == row["station"]) & (sc["phase"] == row["phase"]) & (sc.index != j)]
    if len(same) and ((same["time"] - row["time"]).abs() <= pd.Timedelta(seconds=dup_tol)).any():
        return "near_duplicate"
    if row["time"] < ref["time"].min() - pd.Timedelta(seconds=1):
        return "before_event"
    if row["time"] > ref["time"].max() + pd.Timedelta(seconds=10):
        return "after_event"
    return "no_reference"


def stats(dts):
    a = np.abs(np.asarray(dts, dtype=float))
    if len(a) == 0:
        return dict(n=0, median_abs_dt_s=None, max_abs_dt_s=None, mean_dt_s=None)
    return dict(n=int(len(a)), median_abs_dt_s=round(float(np.median(a)), 4),
                max_abs_dt_s=round(float(a.max()), 4), mean_dt_s=round(float(np.mean(dts)), 4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks-xml", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--kma-id", required=True)
    ap.add_argument("--bound", required=True, help="stations_bound.csv from 05_smoke_bindings.py")
    ap.add_argument("--p-tol", type=float, default=0.5)
    ap.add_argument("--s-tol", type=float, default=1.0)
    ap.add_argument("--dup-tol", type=float, default=0.1,
                    help="two SeisComP picks of one station and phase closer than this are near-duplicates")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    sc = read_scml_picks(args.picks_xml)
    ref = pd.read_csv(args.ref, dtype={"kma_id": str})
    ref = ref[ref["kma_id"] == args.kma_id].copy()
    ref["time"] = pd.to_datetime(ref["time"], utc=True)
    bound = pd.read_csv(args.bound)
    bound_sta = set(bound.loc[bound["bound"] == 1, "station"])

    ref["station_bound"] = ref["station"].isin(bound_sta)
    sc["matched"] = False
    sc["unmatched_class"] = ""
    ref["sc_time"] = ""          # ISO string of the matched SeisComP pick (empty = no match)
    ref["dt_s"] = np.nan
    ref["sc_confidence"] = np.nan

    summary = dict(event=args.kma_id, p_tol_s=args.p_tol, s_tol_s=args.s_tol,
                   seiscomp_picks_total=int(len(sc)),
                   seiscomp_P=int((sc["phase"] == "P").sum()) if len(sc) else 0,
                   seiscomp_S=int((sc["phase"] == "S").sum()) if len(sc) else 0,
                   seiscomp_methods=sc["method"].value_counts().to_dict() if len(sc) else {},
                   reference_P=int((ref["phase"] == "P").sum()),
                   reference_S=int((ref["phase"] == "S").sum()),
                   reference_P_on_bound_stations=int(((ref["phase"] == "P") & ref["station_bound"]).sum()),
                   reference_S_on_bound_stations=int(((ref["phase"] == "S") & ref["station_bound"]).sum()),
                   stations_bound=len(bound_sta))

    for phase, tol in (("P", args.p_tol), ("S", args.s_tol)):
        r = ref[ref["phase"] == phase]
        s = sc[sc["phase"] == phase] if len(sc) else sc
        m = match(r, s, tol)
        for i, (j, dt) in m.items():
            ref.loc[i, "sc_time"] = sc.loc[j, "time"].isoformat()
            ref.loc[i, "dt_s"] = dt
            ref.loc[i, "sc_confidence"] = sc.loc[j, "confidence"]
            sc.loc[j, "matched"] = True
        dts = [dt for (_, dt) in m.values()]
        st = stats(dts)
        summary[f"{phase}_matched"] = st["n"]
        summary[f"{phase}_median_abs_dt_s"] = st["median_abs_dt_s"]
        summary[f"{phase}_max_abs_dt_s"] = st["max_abs_dt_s"]
        summary[f"{phase}_mean_dt_s"] = st["mean_dt_s"]
        # SeisComP picks of this phase that match nothing, and why (see classify_unmatched)
        unmatched = s[~s.index.isin([j for (j, _) in m.values()])]
        summary[f"{phase}_seiscomp_unmatched"] = int(len(unmatched))
        for k in UNMATCHED_CLASSES:
            summary[f"{phase}_unmatched_{k}"] = 0
        for j in unmatched.index:
            k = classify_unmatched(sc, j, ref, args.dup_tol)
            sc.loc[j, "unmatched_class"] = k
            summary[f"{phase}_unmatched_{k}"] += 1
        rb = r[r["station_bound"]]
        summary[f"{phase}_reference_on_bound_stations_matched"] = int(rb.index.isin(list(m.keys())).sum())

    ref_out = ref[["network", "station", "channel", "sensor", "phase", "time", "probability",
                   "epi_dist_km", "station_bound", "sc_time", "dt_s", "sc_confidence"]]
    ref_out.to_csv(f"{args.out}_reference_vs_seiscomp.csv", index=False)
    sc.to_csv(f"{args.out}_seiscomp_picks.csv", index=False)
    with open(f"{args.out}_summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=str)
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
