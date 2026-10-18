# v09_weights_onnx.py -- independent verifier of step 09, part 4 (are the plugin's ONNX weights SeisBench's?).
# Env: pyrtdd (onnx, onnxruntime CPU conda-forge build, numpy). Run with 'python -I'.
#
# Why: step 09 claims the plugin's phasenet_instance.onnx holds exactly SeisBench's PhaseNet 'instance' v2
# weights (outputs differ by < 1e-6 on identical input). v09_seisbench_rerun.py wrote windows that step 09 did
# NOT use (S-centred windows and noise windows of 3 events), normalised by SeisBench's annotate_batch_pre,
# with the torch outputs. Here the ONNX file runs on the same normalised input; equal weights give float32
# rounding-level differences. A second input is my own implementation of the plugin's stated normalisation
# (demean, then divide each component by its peak |x|), to see whether the input definition matters.
# Usage: python -I v09_weights_onnx.py [--apply]

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import onnx
import onnxruntime as ort

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
ONNX = f"{PROJECT}/software/src/seiscomp/src/extras/scdlrtpicker/models/phasenet_instance.onnx"
NPZ = f"{PROJECT}/runs/verify_gwangyang_dl/seisbench/phasenet_instance_weight_test_windows.npz"
OUT = f"{PROJECT}/runs/verify_gwangyang_dl/out/seisbench/weights_onnx_check.json"


def my_plugin_norm(raw):
    x = raw.astype(np.float64)
    x = x - x.mean(axis=-1, keepdims=True)
    pk = np.abs(x).max(axis=-1, keepdims=True)
    pk[pk == 0] = 1.0
    return (x / pk).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    z = np.load(NPZ)
    meta = {p.key: p.value for p in onnx.load(ONNX, load_external_data=False).metadata_props}
    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    so.inter_op_num_threads = 1
    sess = ort.InferenceSession(ONNX, so, providers=["CPUExecutionProvider"])
    iname = sess.get_inputs()[0].name
    onnx_ph = meta["seiscomp.picker.phases"].split(",")
    sb_ph = [str(c) for c in z["labels"]]

    def run(x):
        return np.concatenate([sess.run(None, {iname: x[i:i + 1]})[0] for i in range(x.shape[0])])

    y_t = z["y_torch"]
    y_o = run(z["x_seisbench"])
    y_p = run(my_plugin_norm(z["raw"]))
    res = dict(onnx=ONNX, onnx_sha256=hashlib.sha256(open(ONNX, "rb").read()).hexdigest(), onnx_metadata=meta,
               seisbench_labels=sb_ph, windows=[str(w) for w in z["windows"]], phases={},
               input_max_abs_diff_my_plugin_norm_vs_seisbench=float(np.abs(my_plugin_norm(z["raw"]) - z["x_seisbench"]).max()),
               versions=dict(python=sys.version, numpy=np.__version__, onnxruntime=ort.__version__, onnx=onnx.__version__))
    for ph in ("P", "S", "N"):
        it, io = sb_ph.index(ph), onnx_ph.index(ph)
        t, o, p = y_t[:, it, :], y_o[:, io, :], y_p[:, io, :]
        res["phases"][ph] = dict(same_input_max_abs_diff=float(np.abs(t - o).max()),
                                 same_input_argmax_equal=[bool(np.argmax(t[i]) == np.argmax(o[i])) for i in range(len(t))],
                                 my_plugin_norm_max_abs_diff=float(np.abs(t - p).max()),
                                 peak_values_torch=[round(float(t[i].max()), 4) for i in range(len(t))])
    print(json.dumps(res, indent=1))
    if a.apply:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump(res, open(OUT, "w"), indent=1)
        print("written:", OUT)
    else:
        print("dry run: nothing written (use --apply)")


if __name__ == "__main__":
    main()
