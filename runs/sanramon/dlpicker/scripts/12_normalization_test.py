# 12_normalization_test.py -- step 12 helper (conda env 'pyrtdd': obspy, onnxruntime (conda-forge CPU build),
# onnx, pandas).
#
# Question: does the plugin's input definition for eqtp_ncedc cost picks? The plugin divides EACH component
# by its own standard deviation (onnxmodel.cpp); SeisBench's EQTP (EQTransformer family, norm 'std',
# norm_amp_per_comp False) divides all three components by ONE standard deviation and tapers 6 samples at both
# ends (eqtransformer.py annotate_batch_pre). Step T flagged the difference but did not test it.
#
# Test: re-run the ONNX model on EXACTLY the windows the plugin evaluated (start time and length from the
# --debug log of the eqtp_ncedc run: 'ref' + 'offset', 120 s), on the bound sensor's raw counts in the
# plugin's component order (vertical, first and second horizontal, config/coverage_bound.csv), once with the
# plugin's normalisation and once with SeisBench's. Windows:
#   missed    analyst P picks the plugin missed with reason model_below_minConfidence (12_compare.py)
#   matched   analyst P picks the plugin matched (control: does SeisBench's input lose them?)
# For each window: the largest P value within +-0.5 s of the analyst pick with each input, and whether it
# reaches minConfidence (0.4). Data not at 100 Hz are resampled with obspy's Trace.resample (FFT, with its
# anti-alias filter); the plugin uses its own Lanczos FIR, so those rows are flagged (resampled = True).
# Check: the plugin-normalised P value at the plugin's pick sample must reproduce the logged confidence.
# Outputs: analysis/normalization_test.csv, analysis/normalization_test.json

import argparse
import json
import re

import numpy as np
import obspy
import onnx
import onnxruntime as ort
import pandas as pd

ATTEMPT_RE = re.compile(r"\[(S?DL3C)/(\S+)\] attempt (\d+)/(\d+): (.*)\(ref=(\S+) offset=([-0-9.]+)s window=([0-9.]+)s\)")


def windows_from_log(path):
    rows = []
    for line in open(path, errors="replace"):
        m = ATTEMPT_RE.search(line)
        if m and m.group(1) == "DL3C":
            body = m.group(5)
            conf = re.search(r"confidence=([0-9.]+)", body)
            bestp = re.search(r"bestP=([0-9.]+)", body)
            rows.append(dict(nsta=m.group(2), ref=obspy.UTCDateTime(m.group(6)), offset=float(m.group(7)),
                             window=float(m.group(8)),
                             logged=float(conf.group(1)) if conf else (float(bestp.group(1)) if bestp else np.nan),
                             accepted=conf is not None and "no P peak" not in body))
    return rows


def ut(x):
    return obspy.UTCDateTime(pd.Timestamp(x).tz_convert("UTC").tz_localize(None).isoformat())


def norm_plugin(x):
    x = x.astype(np.float64)
    x = x - x.mean(axis=-1, keepdims=True)
    sd = x.std(axis=-1, ddof=1, keepdims=True)
    sd[sd == 0] = 1.0
    return (x / sd).astype(np.float32)


def norm_seisbench(x):
    x = x.astype(np.float64)
    x = x - x.mean(axis=-1, keepdims=True)
    x = x / (x.std(ddof=1) + 1e-10)                  # torch std over (-1, -2): one value, unbiased
    tap = 0.5 * (1 + np.cos(np.linspace(np.pi, 2 * np.pi, 6)))
    x[:, :6] *= tap
    x[:, -6:] *= tap[::-1]
    return x.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--variant", default="eqtp_ncedc")
    ap.add_argument("--min-conf", type=float, default=0.4)
    ap.add_argument("--tol", type=float, default=0.5)
    a = ap.parse_args()
    R = a.run_dir

    meta = {p.key: p.value for p in onnx.load(a.model, load_external_data=False).metadata_props}
    names = meta["seiscomp.picker.phases"].split(",")
    iP = names.index("P")
    L = int(meta["seiscomp.picker.windowLength"])
    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    sess = ort.InferenceSession(a.model, so, providers=["CPUExecutionProvider"])
    iname = sess.get_inputs()[0].name

    cov = pd.read_csv(f"{R}/config/coverage_bound.csv", dtype={"event_id": str, "location": str}).fillna({"location": ""})
    cov = cov[cov["role"] == "main"]
    cov["nsta"] = cov["network"] + "." + cov["station"]
    covd = {(r.event_id, r.nsta): r for r in cov.itertuples()}
    miss = pd.read_csv(f"{R}/analysis/missed_reference_diagnosis.csv", dtype={"event_id": str})
    miss = miss[(miss["variant"] == a.variant) & (miss["phase"] == "P") & (miss["why_missed"] == "model_below_minConfidence")]
    rv = pd.read_csv(f"{R}/analysis/reference_vs_dl.csv", dtype={"event_id": str}, low_memory=False)
    mat = rv[(rv["variant"] == a.variant) & (rv["phase"] == "P") & rv["matched"]]
    cases = ([("missed", r.event_id, r.nsta, ut(r.time)) for r in miss.itertuples()]
             + [("matched", r.event_id, r.nsta, ut(r.time_utc)) for r in mat.itertuples()])

    rows = []
    for e in sorted({c[1] for c in cases}):
        wins = windows_from_log(f"{R}/output/{a.variant}/{e}/scautopick.log")
        st = obspy.read(f"{R}/input/{e}_sorted.mseed")
        for kind, _, nsta, t in [c for c in cases if c[1] == e]:
            c = covd.get((e, nsta))
            cand = [w for w in wins if w["nsta"] == nsta and w["ref"] + w["offset"] <= t <= w["ref"] + w["offset"] + w["window"]]
            if c is None or not cand:
                continue
            w = max(cand, key=lambda w: w["logged"])
            t0 = w["ref"] + w["offset"]
            comp, resampled = [], False
            for ch in (c.z, c.h1, c.h2):
                tr = st.select(network=c.network, station=c.station, location=c.location, channel=ch)
                tr = tr.copy().merge(method=1, fill_value=0)
                if len(tr) != 1:
                    break
                tr = tr[0]
                tr.data = tr.data.astype(np.float64)
                if tr.stats.sampling_rate != 100.0:
                    tr.resample(100.0)
                    resampled = True
                i0 = int(round((t0 - tr.stats.starttime) * 100.0))
                if i0 < 0 or i0 + L > tr.stats.npts:
                    break
                comp.append(tr.data[i0:i0 + L])
            if len(comp) != 3:
                continue
            x = np.stack(comp)[None]
            yp = sess.run(None, {iname: norm_plugin(x[0])[None]})[0].reshape(len(names), -1)[iP]
            ys = sess.run(None, {iname: norm_seisbench(x[0])[None]})[0].reshape(len(names), -1)[iP]
            k = int(round((t - t0) * 100.0))
            lo, hi = max(0, k - int(a.tol * 100)), min(L, k + int(a.tol * 100) + 1)
            rows.append(dict(kind=kind, event_id=e, nsta=nsta, sensor=c.sensor, resampled=resampled,
                             window_start=str(t0), logged_value=w["logged"], plugin_window_max_P=float(yp.max()),
                             P_near_pick_plugin_norm=float(yp[lo:hi].max()), P_near_pick_seisbench_norm=float(ys[lo:hi].max())))
    df = pd.DataFrame(rows)
    df.to_csv(f"{R}/analysis/normalization_test.csv", index=False, float_format="%.4f")
    res = {}
    for kind in ("missed", "matched"):
        q = df[df["kind"] == kind]
        q100 = q[~q["resampled"]]
        res[kind] = dict(n=int(len(q)), n_100hz=int(len(q100)),
                         reach_min_conf_plugin_norm=int((q["P_near_pick_plugin_norm"] >= a.min_conf).sum()),
                         reach_min_conf_seisbench_norm=int((q["P_near_pick_seisbench_norm"] >= a.min_conf).sum()),
                         median_P_plugin_norm=float(q["P_near_pick_plugin_norm"].median()),
                         median_P_seisbench_norm=float(q["P_near_pick_seisbench_norm"].median()),
                         reach_100hz_plugin=int((q100["P_near_pick_plugin_norm"] >= a.min_conf).sum()),
                         reach_100hz_seisbench=int((q100["P_near_pick_seisbench_norm"] >= a.min_conf).sum()),
                         by_sensor=q.groupby("sensor").apply(
                             lambda g: dict(n=len(g), plugin=int((g["P_near_pick_plugin_norm"] >= a.min_conf).sum()),
                                            seisbench=int((g["P_near_pick_seisbench_norm"] >= a.min_conf).sum())),
                             include_groups=False).to_dict())
    # reproduction check: for missed rows the logged value is the window's best P (bestP), which must equal
    # the plugin-normalised window maximum (100 Hz rows; float32 vs the logged 2 decimals)
    q = df[(df["kind"] == "missed") & ~df["resampled"]]
    res["reproduction_max_abs_diff_logged_vs_recomputed_bestP_100hz"] = float(
        (q["logged_value"] - q["plugin_window_max_P"]).abs().max()) if len(q) else None
    with open(f"{R}/analysis/normalization_test.json", "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
