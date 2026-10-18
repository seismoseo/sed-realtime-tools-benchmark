# 05_seisbench_weight_info.py -- step T helper (run in conda env 'pyrtdd': onnx; standard library otherwise).
#
# The 49 .onnx models shipped with scdlrtpicker are SeisBench weight sets exported with
# models/export_seisbench_to_onnx.py (file name = <model>_<weights>.onnx). The .onnx files carry only
# the seiscomp.picker.* metadata, not what the weights were trained on. SeisBench publishes a small
# JSON file per weight set and version (docstring = training data and reference, default pick
# thresholds, preprocessing arguments). This helper downloads those JSON files (read-only HTTP from
# SeisBench's public repository; nothing is installed, no model weights are downloaded) and prints,
# per shipped .onnx file:
#   - the newest SeisBench metadata version on the server (the exporter used from_pretrained(), i.e.
#     the newest version at export time; a newer version published later would not be in the .onnx)
#   - SeisBench's own default P/S thresholds (tuned for best F1 on the training domain) next to the
#     plugin defaults minConfidence P 0.4 / S 0.3
#   - normalization: SeisBench 'norm' vs the .onnx seiscomp.picker.normalization
#   - preprocessing SeisBench applies but the plugin does not (filter_args = an obspy filter applied
#     to the stream before the network)
#   - the docstring (training data, reference)
#
# Usage: python 05_seisbench_weight_info.py <models_dir> > out.txt

import glob
import json
import os
import re
import sys
import urllib.request

import onnx

ROOT = "https://hifis-storage.desy.de:2880/Helmholtz/HelmholtzAI/SeisBench/models/v3/"
# file-name prefix -> SeisBench repository folder (SeisBench class name in lower case)
PREFIX = ["phasenetlight", "phasenet", "eqtransformer", "obstransformer", "eqcctp", "eqccts",
          "basicphaseae", "skynet", "eqtp"]
TIMEOUT = 60


def http(url, method="GET"):
    req = urllib.request.Request(url, method=method, headers={"Depth": "1"} if method == "PROPFIND" else {})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8")


def listing(folder):
    xml = http(ROOT + folder + "/", "PROPFIND")
    # files are <weights>.json.v<N>; a file without a version suffix (<weights>.json) is version 1
    names = re.findall(r"<d:href>[^<]*/([^/<]+\.json(?:\.v\d+)?)</d:href>", xml)
    out = {}
    for n in names:
        w, v = re.match(r"(.+?)\.json(?:\.v(\d+))?$", n).groups()
        out.setdefault(w, {})[int(v) if v else 1] = n
    return out


def main():
    models_dir = sys.argv[1]
    files = sorted(glob.glob(os.path.join(models_dir, "*.onnx")))
    cache = {}
    print("# SeisBench metadata of the weight sets behind scdlrtpicker's shipped .onnx models")
    print(f"# source: {ROOT}<model>/<weights>.json.v<N> (newest N on the server)")
    print("# columns: file | SeisBench model/weights vN | SeisBench default P/S threshold"
          " | norm SeisBench vs onnx | SeisBench preprocessing not done by the plugin | docstring")
    print()
    for f in files:
        base = os.path.basename(f)[:-5]
        folder = next(p for p in PREFIX if base.startswith(p + "_"))
        weights = base[len(folder) + 1:]
        if folder not in cache:
            cache[folder] = listing(folder)
        versions = cache[folder].get(weights)
        meta_onnx = {p.key: p.value for p in onnx.load(f, load_external_data=False).metadata_props}
        if not versions:
            print(f"{base}.onnx | {folder}/{weights}: NO metadata JSON found on the server")
            continue
        v = max(versions)
        d = json.loads(http(f"{ROOT}{folder}/{versions[v]}"))
        da = d.get("default_args", {}) or {}
        ma = d.get("model_args", {}) or {}
        pth, sth = da.get("P_threshold", "-"), da.get("S_threshold", "-")
        fmt = lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)  # noqa: E731
        sb_norm = ma.get("norm", "(class default)")
        filt = ma.get("filter_args")
        filt_txt = f"filter {filt} {ma.get('filter_kwargs')}" if filt else "-"
        doc = " ".join(str(d.get("docstring", "")).split())
        print(f"{base}.onnx | {folder}/{weights} v{v} (versions on server: {sorted(versions)}) | "
              f"P {fmt(pth)} / S {fmt(sth)} | norm {sb_norm} vs onnx "
              f"{meta_onnx.get('seiscomp.picker.normalization', '-')} | {filt_txt}")
        print(f"    {doc[:600]}")
        print()


if __name__ == "__main__":
    main()
