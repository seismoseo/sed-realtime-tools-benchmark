# 14_weights_check.py -- step 14 copy of runs/sanramon/dlpicker/scripts/12_weights_check.py (San Ramon 2015, step 12; not modified).
# CODE UNCHANGED (only these header lines were added).
#
# 12_weights_check.py -- step 12 helper (conda env 'pyrtdd': onnx, onnxruntime (conda-forge CPU build, no
# telemetry), numpy). Adapted from step 09's 09_weights_check.py for the 4-output EQTP model.
#
# 1. Same weights? The ONNX file the plugin runs and SeisBench's torch model get the identical,
#    already-normalised input windows (x_seisbench = SeisBench's own annotate_batch_pre() of real San Ramon
#    windows, written by 12_seisbench_run.py); their four output curves (Polarity_U, Polarity_D, P, S) are
#    compared sample by sample. Equal weights give differences at float32 rounding level.
# 2. Does the plugin's different input matter? x_plugin = the plugin's normalisation of the same raw window
#    (onnxmodel.cpp: demean, then divide EACH component by its own standard deviation (N-1); no taper),
#    whereas SeisBench divides all three components by ONE standard deviation and tapers 6 samples at each end.
#    Reported per window: P and S peak position shift (samples) and peak value, and the polarity read at the
#    P peak (max(U, D) and which is larger), with both inputs.
#
# Usage: python 12_weights_check.py --npz <eqtp_ncedc_weights_test.npz> --model <eqtp_ncedc.onnx> --out <json>

import argparse
import json

import numpy as np
import onnx
import onnxruntime as ort


def plugin_norm(raw, norm):
    x = raw.astype(np.float64)
    x = x - x.mean(axis=-1, keepdims=True)
    if norm == "peak":
        d = np.abs(x).max(axis=-1, keepdims=True)
    elif norm == "std":
        d = x.std(axis=-1, ddof=1, keepdims=True)
    else:
        d = np.ones_like(x[..., :1])
    d[d == 0] = 1.0
    return (x / d).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    so.inter_op_num_threads = 1
    z = np.load(a.npz)
    meta = {p.key: p.value for p in onnx.load(a.model, load_external_data=False).metadata_props}
    onnx_names = meta["seiscomp.picker.phases"].split(",")
    sess = ort.InferenceSession(a.model, so, providers=["CPUExecutionProvider"])
    iname = sess.get_inputs()[0].name
    names = [str(s) for s in z["names"]]

    def run(x):
        return np.concatenate([sess.run(None, {iname: x[i:i + 1]})[0].reshape(1, len(onnx_names), -1)
                               for i in range(x.shape[0])])

    y_t = z["y_torch"]
    y_o = run(z["x_seisbench"])
    norm = meta.get("seiscomp.picker.normalization", "std")
    x_p = plugin_norm(z["raw"], norm)
    y_p = run(x_p)
    stations = [str(s) for s in z["stations"]]
    res = dict(model=a.model, stations=stations, onnx_outputs=onnx_names, seisbench_outputs=names,
               onnx_normalization=norm, seisbench_norm=str(z["norm"]), same_input={}, plugin_input={}, per_window=[])
    for nm in names:
        it, io = names.index(nm), onnx_names.index(nm)
        res["same_input"][nm] = float(np.abs(y_t[:, it, :] - y_o[:, io, :]).max())
        res["plugin_input"][nm] = float(np.abs(y_t[:, it, :] - y_p[:, io, :]).max())
    res["same_weights"] = all(v < 1e-3 for v in res["same_input"].values())
    res["input_max_abs_diff_plugin_vs_seisbench"] = float(np.abs(x_p - z["x_seisbench"]).max())
    iP, iS, iU, iD = (onnx_names.index(k) for k in ("P", "S", "Polarity_U", "Polarity_D"))
    for k, s in enumerate(stations):
        row = dict(station=s)
        raw = z["raw"][k].astype(np.float64)
        sd = (raw - raw.mean(axis=-1, keepdims=True)).std(axis=-1, ddof=1)
        row["component_std_ratio_H_over_Z"] = [round(float(sd[1] / sd[0]), 3), round(float(sd[2] / sd[0]), 3)]
        for tag, y in (("seisbench_input", y_o), ("plugin_input", y_p)):
            pk = int(np.argmax(y[k, iP]))
            sk = int(np.argmax(y[k, iS]))
            u, d = float(y[k, iU, pk]), float(y[k, iD, pk])
            row[tag] = dict(P_peak_sample=pk, P_peak=round(float(y[k, iP, pk]), 4), S_peak_sample=sk,
                            S_peak=round(float(y[k, iS, sk]), 4), polarity=("U" if u >= d else "D"),
                            polarity_conf=round(max(u, d), 4))
        row["P_shift_samples"] = row["plugin_input"]["P_peak_sample"] - row["seisbench_input"]["P_peak_sample"]
        row["S_shift_samples"] = row["plugin_input"]["S_peak_sample"] - row["seisbench_input"]["S_peak_sample"]
        row["same_polarity"] = row["plugin_input"]["polarity"] == row["seisbench_input"]["polarity"]
        res["per_window"].append(row)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(f"windows {stations}")
    print(f"same input: max |ONNX - torch| = {res['same_input']}; same weights: {res['same_weights']}")
    print(f"plugin input differs from SeisBench's by <= {res['input_max_abs_diff_plugin_vs_seisbench']:.3g}; "
          f"outputs differ by <= {res['plugin_input']}")
    for r in res["per_window"]:
        print(f"  {r['station']}: H/Z std {r['component_std_ratio_H_over_Z']}; P shift {r['P_shift_samples']} samples "
              f"(peak {r['seisbench_input']['P_peak']} -> {r['plugin_input']['P_peak']}), S shift {r['S_shift_samples']} "
              f"(peak {r['seisbench_input']['S_peak']} -> {r['plugin_input']['S_peak']}), polarity "
              f"{r['seisbench_input']['polarity']}({r['seisbench_input']['polarity_conf']}) -> "
              f"{r['plugin_input']['polarity']}({r['plugin_input']['polarity_conf']})")


if __name__ == "__main__":
    main()
