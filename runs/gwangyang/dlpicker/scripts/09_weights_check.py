# 09_weights_check.py -- step 09 helper (run in conda env 'pyrtdd': onnx, onnxruntime (conda-forge CPU
# build, no telemetry), numpy).
#
# Proves (or disproves) that the ONNX files the plugin runs contain the SAME weights as the SeisBench
# models 09_seisbench_run.py used: both networks get the identical, already-normalised input windows
# (x_seisbench = SeisBench's own annotate_batch_pre() of real Gwangyang windows) and their output curves
# are compared sample by sample. Equal weights give differences at float32 rounding level (~1e-6).
#
# It also measures the effect of the one preprocessing step the plugin does differently for these models:
# x_plugin = the plugin's normalisation of the same raw window (onnxmodel.cpp: demean, then divide each
# component by its peak |x| ('peak') or its standard deviation with N-1 ('std'); no taper). For PhaseNet
# this equals SeisBench's input; SeisBench's EQTransformer additionally tapers 6 samples at each end.
#
# Output rows are matched by phase name: the ONNX file declares its row order in seiscomp.picker.phases;
# SeisBench's order is in the npz ('names').
#
# Usage: python 09_weights_check.py --npz-dir <dir> --models-dir <onnx dir> --models m1 m2 --out <json>

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
    ap.add_argument("--npz-dir", required=True)
    ap.add_argument("--models-dir", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    so.inter_op_num_threads = 1
    res = {}
    for name in a.models:
        z = np.load(f"{a.npz_dir}/{name}_weights_test.npz")
        path = f"{a.models_dir}/{name}.onnx"
        meta = {p.key: p.value for p in onnx.load(path, load_external_data=False).metadata_props}
        onnx_names = meta["seiscomp.picker.phases"].split(",")
        sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
        iname = sess.get_inputs()[0].name
        names = [str(s) for s in z["names"]]
        y_t = z["y_torch"]

        def run(x):
            return np.concatenate([sess.run(None, {iname: x[i:i + 1]})[0].reshape(1, len(onnx_names), -1)
                                   for i in range(x.shape[0])])

        y_o = run(z["x_seisbench"])
        norm = meta.get("seiscomp.picker.normalization", "std")
        y_p = run(plugin_norm(z["raw"], norm))
        d = {"stations": [str(s) for s in z["stations"]], "onnx_phases": onnx_names, "seisbench_outputs": names,
             "onnx_normalization": norm, "seisbench_norm": str(z["norm"]),
             "component_order": "".join(str(c) for c in z["component_order"]), "phases": {}}
        for ph in ("P", "S"):
            it, io = names.index(ph), onnx_names.index(ph)
            a_t, a_o, a_p = y_t[:, it, :], y_o[:, io, :], y_p[:, io, :]
            d["phases"][ph] = dict(
                same_input_max_abs_diff=float(np.abs(a_t - a_o).max()),
                same_input_argmax_equal=[bool(np.argmax(a_t[i]) == np.argmax(a_o[i])) for i in range(len(a_t))],
                plugin_input_max_abs_diff=float(np.abs(a_t - a_p).max()),
                plugin_input_argmax_shift_samples=[int(np.argmax(a_p[i]) - np.argmax(a_t[i])) for i in range(len(a_t))],
                peak_values_seisbench=[round(float(a_t[i].max()), 4) for i in range(len(a_t))])
        d["input_max_abs_diff_plugin_vs_seisbench"] = float(np.abs(plugin_norm(z["raw"], norm) - z["x_seisbench"]).max())
        d["same_weights"] = all(v["same_input_max_abs_diff"] < 1e-3 for v in d["phases"].values())
        res[name] = d
        print(f"{name}: windows {d['stations']}; same input -> max |ONNX - torch| P {d['phases']['P']['same_input_max_abs_diff']:.2e}, "
              f"S {d['phases']['S']['same_input_max_abs_diff']:.2e}; same weights: {d['same_weights']}; "
              f"plugin-normalised input differs from SeisBench's by <= {d['input_max_abs_diff_plugin_vs_seisbench']:.2e}, "
              f"output by <= {max(v['plugin_input_max_abs_diff'] for v in d['phases'].values()):.2e}; "
              f"argmax shifts {d['phases']['P']['plugin_input_argmax_shift_samples']} (P) samples")
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
