# 14_extra_checks.py -- step 14 helper (conda env 'pyrtdd': obspy, pandas). New in step 14 (no step-12
# counterpart); reads only files written by 14_dlpicker.sh and 14_compare.py, changes nothing else.
#
# 1. BK.CMSB.00.HN? sampling rate. The records are 200 Hz, but stations.xml (and so the SeisComP inventory made
#    by fdsnxml2inv) says 100 Hz for the epoch that ends 2026-03-12. SeisComP's waveform processors take the rate
#    of each record (processing/waveformprocessor.cpp: setupStream(record->samplingFrequency())), and the plugin
#    resamples from that rate to the model rate. Checks: (a) the rates in the records and in the inventory per
#    epoch; (b) every 'sampling rate changed' warning in all scautopick logs; (c) the DL picks of the hn variants
#    (which bind CMSB's HN) against the analyst picks of CMSB (picked on the 500 Hz borehole DP channels) and the
#    picks of the main variants on CMSB's DP sensor: with a wrong rate the pick times would be off by seconds.
# 2. Automatic picks in the reference. The 2015 rule (weight codes 0-3) also takes the NCSS real-time picks
#    (data source 'R') that sit in analyst-reviewed events: 71 P picks of the 26 events here (2015: 5). Recall of
#    the main models with and without them.
# 3. hn set: accelerometers whose three components scautopick could not assemble (overlapping sensor-location
#    epochs in the NCEDC metadata; log lines 'Added processor on stream NET.STA.LOC. ' with an empty channel
#    code). 14_bindings.py's copy of getThreeComponents pools all epochs of a location code and so passed them.
#    The accelerometer-vs-velocity recall is repeated without those stations.
# 4. P picks in the common noise span confirmed by another model at the same station within 0.5 s (the count of
#    the step-12 note, section 8; the same code gives step 12's 19/27, 27/98, 13/46, 9/32 on its own files).
# 5. The overlap-test file 75283011: which catalog event each model's matched P picks belong to.
# 6. If the SeisBench stage ran: how many analyst P picks of 75283011 and of the following Mw 3.77 (75283016)
#    SeisBench's continuous EQTP has a P pick for (within 0.5 s; simple count, not one-to-one).
# Output: analysis/extra_checks.json (+ printout).
# Usage: python 14_extra_checks.py --run-dir runs/sanramon2026/dlpicker

import argparse
import glob
import json
import os
import re
import xml.etree.ElementTree as ET

import numpy as np
import obspy
import pandas as pd

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
MAIN = ["phasenet_instance", "phasenet_original", "phasenet_scedc", "eqtp_ncedc"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--station", default="BK.CMSB")
    a = ap.parse_args()
    R, A = a.run_dir, f"{a.run_dir}/analysis"
    net, sta = a.station.split(".")
    out = {}

    # ---- 1a rates in the records and in the inventory
    rec = []
    for f in sorted(glob.glob(f"{R}/input/*_sorted.mseed")):
        ev = os.path.basename(f).split("_")[0]
        for tr in obspy.read(f, headonly=True).select(network=net, station=sta):
            rec.append(dict(event_id=ev, channel=f"{tr.stats.location}.{tr.stats.channel}",
                            record_rate_hz=tr.stats.sampling_rate, start=str(tr.stats.starttime)))
    rec = pd.DataFrame(rec).drop_duplicates(["event_id", "channel"])
    root = ET.parse(f"{R}/config/inventory_sc.xml").getroot()
    ns = root.tag.split("}")[0] + "}"
    inv = []
    for n in root.iter(f"{ns}network"):
        if n.get("code") != net:
            continue
        for s in n.findall(f"{ns}station"):
            if s.get("code") != sta:
                continue
            for loc in s.findall(f"{ns}sensorLocation"):
                for st in loc.findall(f"{ns}stream"):
                    num, den = st.findtext(f"{ns}sampleRateNumerator"), st.findtext(f"{ns}sampleRateDenominator")
                    inv.append(dict(channel=f"{loc.get('code') or ''}.{st.get('code')}", start=st.findtext(f"{ns}start"),
                                    end=st.findtext(f"{ns}end"),
                                    inventory_rate_hz=float(num) / float(den) if num and den else None))
    inv = pd.DataFrame(inv)
    out["cmsb_record_rates"] = rec.groupby("channel")["record_rate_hz"].agg(lambda x: sorted(set(x))).to_dict()
    out["cmsb_inventory_epochs"] = inv.to_dict("records")

    # ---- 1b 'sampling rate changed' warnings in every scautopick log
    nwarn, wlines = 0, []
    for f in glob.glob(f"{R}/output/*/*/scautopick.log"):
        for line in open(f, errors="replace"):
            if "sampling rate changed" in line:
                nwarn += 1
                if len(wlines) < 5:
                    wlines.append(f"{os.path.relpath(f, R)}: {line.strip()[:160]}")
    out["sampling_rate_changed_warnings"] = dict(n=nwarn, examples=wlines)
    nrs = 0
    for f in glob.glob(f"{R}/output/*_hn/*/scautopick.log"):
        nrs += sum(1 for line in open(f, errors="replace") if f"{a.station}.00.HN" in line and "created picker" in line)
    out["cmsb_hn_pickers_created_in_hn_runs"] = nrs

    # ---- 1c CMSB picks vs analyst picks
    rv = pd.read_csv(f"{A}/reference_vs_dl.csv", dtype={"event_id": str})
    q = rv[rv["nsta"] == a.station]
    rows = []
    for v, g in q.groupby("variant"):
        for ph in ("P", "S"):
            gg = g[g["phase"] == ph]
            m = gg[gg["matched"]]
            rows.append(dict(variant=v, phase=ph, analyst_picks=len(gg), matched=len(m),
                             dl_channels=",".join(sorted(set(m["dl_channel"].dropna().astype(str)))),
                             analyst_channels=",".join(sorted(set(gg["channel"]))),
                             median_dt_s=float(m["dt_s"].median()) if len(m) else None,
                             max_abs_dt_s=float(m["dt_s"].abs().max()) if len(m) else None))
    out["cmsb_vs_analyst"] = rows
    dl = pd.read_csv(f"{A}/dl_picks_all.csv", dtype={"event_id": str, "matched_event_id": str})
    dl["time"] = pd.to_datetime(dl["time"], utc=True, format="ISO8601")
    c = dl[dl["nsta"] == a.station]
    pair = []
    for m in MAIN:
        hn, mn = c[c["variant"] == f"{m}_hn"], c[c["variant"] == m]
        for (e, ph), g in hn.groupby(["event_id", "phase"]):
            h = mn[(mn["event_id"] == e) & (mn["phase"] == ph)]
            for t in g["time"]:
                if len(h):
                    d = (h["time"] - t).dt.total_seconds()
                    j = d.abs().idxmin()
                    pair.append(dict(model=m, event_id=e, phase=ph, hn_minus_dp_s=-float(d.loc[j])))
    pair = pd.DataFrame(pair)
    if len(pair):
        close = pair[pair["hn_minus_dp_s"].abs() <= 1.0]
        out["cmsb_hn_vs_dp_same_model"] = dict(n_hn_picks_with_a_dp_pick=len(pair), n_within_1s=len(close),
                                               median_abs_dt_within_1s=float(close["hn_minus_dp_s"].abs().median()) if len(close) else None)
    events_after = sorted(set(rec.loc[rec["start"] >= "2026-03-13T15:55", "event_id"]))
    out["cmsb_events_in_200hz_epoch_of_inventory"] = events_after

    # ---- 2 recall without automatic picks
    ref = pd.read_csv(f"{A}/reference_picks.csv", dtype={"event_id": str})
    out["reference_data_source_counts"] = {f"{k[0]}|{k[1]}": int(v) for k, v in
                                           ref.groupby(["phase", "data_source"]).size().items()}
    sens = []
    for v in MAIN:
        g = rv[(rv["variant"] == v) & (rv["phase"] == "P")]
        for name, sel in (("all usable (step-12 rule)", g), ("analyst 'J' only", g[g["data_source"] == "J"]),
                          ("automatic 'R' only", g[g["data_source"] == "R"])):
            d = dict(variant=v, reference=name, n=len(sel))
            for t, ss in (("all", sel), ("3c", sel[sel["is_3c"]]), ("complete", sel[sel["tier"] == "3c_complete"])):
                d[f"recall_{t}"] = float(ss["matched"].mean()) if len(ss) else None
                d[f"n_{t}"] = len(ss)
            sens.append(d)
    out["recall_P_by_data_source"] = sens

    # ---- 3 hn set: stations where scautopick could not assemble the accelerometer's three components
    # (log lines 'Added processor on stream NET.STA.LOC. ' with an empty channel code; 'Ambiguous vertical
    # component across epochs'), and the accelerometer-vs-velocity comparison without them
    broken, amb = {}, {}
    for f in glob.glob(f"{R}/output/*_hn/*/scautopick.log"):
        for line in open(f, errors="replace"):
            m = re.search(r"Added processor on stream ([A-Z0-9]+)\.([A-Z0-9]+)\.([0-9A-Z]*)\. ", line)
            if m:
                broken[f"{m.group(1)}.{m.group(2)}"] = broken.get(f"{m.group(1)}.{m.group(2)}", 0) + 1
            m = re.search(r"Ambiguous vertical component across epochs for (\S+)\.", line)
            if m:
                amb[m.group(1)] = amb.get(m.group(1), 0) + 1
    out["hn_failed_three_component_assembly"] = broken
    out["hn_ambiguous_vertical_errors"] = amb
    bound = pd.read_csv(f"{R}/config/stations_bound.csv", dtype=str).fillna("")
    hn_st = set((bound["network"] + "." + bound["station"])[bound["hn_sensor"] != ""])
    ok_st = hn_st - set(broken)
    acc = []
    for m in MAIN:
        for v in (m, f"{m}_hn"):
            for ph in ("P", "S"):
                for name, st in (("all hn stations", hn_st), ("hn stations that worked", ok_st)):
                    g = rv[(rv["variant"] == v) & (rv["phase"] == ph) & rv["nsta"].isin(st) & rv["has_data"]]
                    acc.append(dict(model=m, sensor="accelerometer" if v.endswith("_hn") else "velocity sensor",
                                    phase=ph, stations=name, n_stations=len(st), n_ref=len(g),
                                    n_matched=int(g["matched"].sum()),
                                    recall=float(g["matched"].mean()) if len(g) else None))
    out["accelerometer_vs_velocity_without_failed"] = acc

    # ---- 4 false-pick candidates confirmed by another model (the count of step-12 note section 8): P picks in the
    # common noise span (class coincident/isolated, in_searchable_span) with a P pick of another main model at the
    # same NET.STA within 0.5 s in the same event file
    P = dl[dl["variant"].isin(MAIN) & (dl["phase"] == "P")]
    conf = {}
    for v in MAIN:
        fs = P[(P["variant"] == v) & P["class"].isin(["coincident", "isolated"]) & P["in_searchable_span"]]
        oth = P[P["variant"] != v]
        n = 0
        for r in fs.itertuples():
            o = oth[(oth["event_id"] == r.event_id) & (oth["nsta"] == r.nsta)]
            n += int(((o["time"] - r.time).abs() <= pd.Timedelta(seconds=0.5)).any())
        conf[v] = dict(n_noise_span_P=len(fs), n_confirmed_by_other_model=n)
    out["noise_span_P_confirmed_by_other_model"] = conf

    # ---- 5 the overlap-test file: which catalog event each model's matched P picks belong to
    ov = {}
    for v in MAIN:
        d = dl[(dl["variant"] == v) & (dl["event_id"] == "75283011") & (dl["phase"] == "P") & dl["matched"]]
        ov[v] = {str(k): int(x) for k, x in d["matched_event_id"].astype(str).value_counts().items()}
    out["overlap_file_75283011_matched_P_by_event"] = ov

    # ---- 6 (only if the SeisBench stage ran) SeisBench's continuous EQTP in the overlap file: analyst P picks of
    # 75283011 and of the following Mw 3.77 75283016 at stations with a usable 3-C sensor that have a SeisBench P
    # pick within the P tolerance (simple count, not one-to-one)
    sbf = f"{R}/seisbench/eqtp_ncedc_picks.csv"
    if os.path.exists(sbf):
        sb = pd.read_csv(sbf, dtype={"event_id": str})
        sb = sb[(sb["event_id"] == "75283011") & (sb["phase"] == "P")].copy()
        sb["t"] = pd.to_datetime(sb["peak_time"], utc=True, format="ISO8601")
        pk = pd.read_csv(f"{PROJECT}/data/sanramon_2026/reference_tables/picks_ncss.csv", dtype={"event_id": str})
        pk = pk[pk["usable"] & (pk["phase"] == "P")].copy()
        pk["t"] = pd.to_datetime(pk["time_utc"], utc=True)
        pk["nsta"] = pk["network"] + "." + pk["station"]
        s3 = set(ref.loc[ref["is_3c"], "nsta"])
        sbo = {}
        for e in ("75283011", "75283016"):
            q_ = pk[(pk["event_id"] == e) & pk["nsta"].isin(s3)]
            n = sum(bool(((sb.loc[sb["nsta"] == r.nsta, "t"] - r.t).abs() <= pd.Timedelta(seconds=0.5)).any())
                    for r in q_.itertuples())
            sbo[e] = dict(analyst_P_at_3c_stations=len(q_), with_seisbench_P_within_0p5s=n)
        out["seisbench_overlap_file_75283011"] = sbo
        print("SeisBench in the overlap file:", sbo)

    json.dump(out, open(f"{A}/extra_checks.json", "w"), indent=1, default=str)
    print("noise-span P picks confirmed by another model:", conf)
    print("overlap file 75283011, matched P picks by event:", ov)
    print("hn set: failed 3-C assembly (processor count):", broken, "; ambiguous-vertical errors:", amb)
    print(pd.DataFrame(acc).round(3).to_string(index=False))
    print("CMSB record rates:", out["cmsb_record_rates"])
    print("CMSB inventory epochs:")
    print(inv.to_string(index=False))
    print("'sampling rate changed' warnings:", out["sampling_rate_changed_warnings"])
    print("CMSB HN pickers created in hn runs:", nrs)
    print(pd.DataFrame(rows).to_string(index=False))
    print("CMSB hn vs main picks (same model):", out.get("cmsb_hn_vs_dp_same_model"))
    print("events after the inventory switches to 200 Hz:", events_after)
    print(pd.DataFrame(sens).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
