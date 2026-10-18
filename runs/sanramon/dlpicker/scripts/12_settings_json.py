# 12_settings_json.py -- step 12 helper (copy of step 09's 09_settings_json.py; only the bound-station
# count reads the step-12 station table, column main_sensor/hn_sensor by --role)
# Original header:
# 09_settings_json.py -- step 09 helper (run in conda env 'pyrtdd': onnx). Writes ONE JSON file per
# scautopick variant with every setting that variant runs with, so the variants are fully disclosed and
# comparable (project rule 5). Sources, in this order:
#   1. cfg_file_values   : every 'key = value' line of the variant's scautopick_<variant>.cfg (the only
#                          configuration file scautopick reads, because it is given with --config-file);
#   2. scautopick_resolved: scautopick's own '--dump-config' output (module configuration as the program
#                          resolved it, plus the per-stream detector configuration of every bound stream)
#                          and its '--dump-settings' output (application settings), parsed to key/value;
#   3. plugin_resolved   : the dlrtpicker picker settings (picker.DL3C.*, spicker.SDL3C.*). scautopick does
#                          not print them, so they are resolved here exactly as the plugin does it: the cfg
#                          value if set, else the plugin's built-in default (PLUGIN_DEFAULTS below, read from
#                          plugins/picker/dl/dl.cpp and S_dl.cpp of scdlrtpicker v1.1.1, with line numbers),
#                          and the window positions ('attempt delays') with the plugin's own formula. Step 09's
#                          09_compare.py checks these delays against the offsets the plugin logs per attempt;
#   4. model_metadata    : the ONNX file's seiscomp.picker.* metadata (window, rate, normalisation, phases);
#   5. bound stations    : how many stations are bound, per sensor code.
#
# Usage: python 09_settings_json.py --variant V --cfg scautopick_V.cfg --dump-config V.dump-config.txt \
#            --dump-settings V.dump-settings.txt --bound stations_bound.csv --out V.settings.json

import argparse
import csv
import json
import math
import re
from collections import Counter

import onnx

# plugin built-in defaults (scdlrtpicker v1.1.1, commit 409b18fd)
PLUGIN_DEFAULTS = {
    "picker.DL3C": {
        "minConfidence": (0.4, "dl.cpp:63,125"),
        "polarityMinConfidence": (0.5, "dl.cpp:64,130-131"),
        "polarityMaxTilt": (20.0, "dl.cpp:134-135"),
        "uncertaintyMap": (None, "dl.cpp:162 (unset: no uncertainty)"),
        "strategy": ("fast", "dl.cpp:173-175"),
        "maxLatency": ("windowDuration/2", "dl.cpp:197-198"),
        "minLatency": ("= maxLatency", "dl.cpp:201-202"),
        "maxAttempts": ("auto: span<=0 -> 1, else min(20, ceil(span/(W/2))+1)", "dl.cpp:211-218"),
        "S-veto (internal)": ("P peak skipped if S curve >= 0.8 * P there", "dl.cpp:408-445"),
    },
    "spicker.SDL3C": {
        "minConfidence": (0.3, "S_dl.cpp:49,106"),
        "phaseHint": ("S", "S_dl.cpp:49,112"),
        "uncertaintyMap": (None, "S_dl.cpp:122 (unset: no uncertainty)"),
        "strategy": ("fast", "S_dl.cpp:133-135"),
        "maxLatency": ("60 + windowDuration/2", "S_dl.cpp:163-164"),
        "minLatency": ("min(windowDuration/2, maxLatency)", "S_dl.cpp:167-168"),
        "maxAttempts": ("auto: span<=0 -> 1, else min(20, ceil(span/(W/2))+1)", "S_dl.cpp:177-184"),
        "search region (internal)": ("only samples strictly after the reference P pick", "S_dl.cpp:345-354"),
    },
}


def parse_cfg(path):
    vals = {}
    for line in open(path):
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        k, v = (x.strip() for x in line.split("=", 1))
        vals[k] = v.strip('"')
    return vals


def parse_dump_config(path):
    module, streams, section = {}, {}, None
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("Configuration:"):
            section = "module"
            continue
        if line.startswith("Stream configuration:"):
            section = "streams"
            continue
        if not line.strip() or section is None:
            continue
        if section == "module":
            parts = re.split(r"\s{2,}", line.strip(), maxsplit=1)
            module[parts[0]] = parts[1] if len(parts) > 1 else ""
        else:
            p = line.split()
            if len(p) >= 5:
                streams[p[0]] = dict(trigger_on=p[1], trigger_off=p[2], time_correction=p[3], filter=" ".join(p[4:]))
    return module, streams


def parse_dump_settings(path):
    out = {}
    for line in open(path):
        line = line.rstrip("\n")
        if ": " in line:
            k, v = line.split(": ", 1)
            out[k.strip()] = v
        elif line.endswith(":"):
            out[line[:-1].strip()] = ""
    return out


def model_meta(path):
    m = onnx.load(path, load_external_data=False)
    meta = {p.key: p.value for p in m.metadata_props}
    return meta


def resolve(cfg, meta, kind):
    """Resolve the plugin settings as dl.cpp / S_dl.cpp do. kind = 'picker.DL3C' or 'spicker.SDL3C'."""
    pre = f"module.trunk.global.{kind}."
    W = int(meta["seiscomp.picker.windowLength"]) / float(meta["seiscomp.picker.sampleRate"])
    out = {}
    for key, (default, src) in PLUGIN_DEFAULTS[kind].items():
        if pre + key in cfg:
            out[key] = dict(value=cfg[pre + key], source="cfg file")
        else:
            out[key] = dict(value=default, source=f"plugin default ({src})")
    out["model"] = dict(value=cfg.get(pre + "model"), source="cfg file")
    if kind == "picker.DL3C":
        maxl = float(cfg.get(pre + "maxLatency", W * 0.5))
        minl = float(cfg.get(pre + "minLatency", maxl))
    else:
        maxl = float(cfg.get(pre + "maxLatency", 60.0 + W * 0.5))
        minl = float(cfg.get(pre + "minLatency", min(W * 0.5, maxl)))
    maxl = max(maxl, minl)
    na = int(cfg.get(pre + "maxAttempts", 0))
    if na < 1:
        span = maxl - minl
        na = 1 if span <= 0 else min(20, int(math.ceil(span / (W * 0.5))) + 1)
    delays = [maxl] if na == 1 else [minl + (maxl - minl) * i / (na - 1) for i in range(na)]
    out["resolved"] = dict(window_duration_s=W, minLatency_s=minl, maxLatency_s=maxl, attempts=na,
                           attempt_window_ends_after_reference_s=[round(d, 4) for d in delays],
                           attempt_window_starts_after_reference_s=[round(d - W, 4) for d in delays],
                           reference="detector trigger" if kind == "picker.DL3C" else "P pick")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True)
    ap.add_argument("--cfg", required=True)
    ap.add_argument("--dump-config", required=True)
    ap.add_argument("--dump-settings", required=True)
    ap.add_argument("--bound", required=True)
    ap.add_argument("--role", default="main", choices=["main", "hn"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    cfg = parse_cfg(a.cfg)
    model_path = cfg["module.trunk.global.picker.DL3C.model"]
    meta = model_meta(model_path)
    module, streams = parse_dump_config(a.dump_config)
    settings = parse_dump_settings(a.dump_settings)
    col = f"{a.role}_sensor"
    bound = [r for r in csv.DictReader(open(a.bound)) if r[col]]

    doc = dict(
        variant=a.variant,
        cfg_file=a.cfg,
        cfg_file_values=cfg,
        plugin_resolved={k: resolve(cfg, meta, k) for k in ("picker.DL3C", "spicker.SDL3C")},
        model_file=model_path,
        model_metadata=meta,
        scautopick_resolved=dict(dump_config_module=module, dump_config_streams=streams,
                                 n_streams=len(streams), dump_settings=settings),
        binding_set=a.role,
        bound_stations=dict(n=len(bound), per_sensor=dict(Counter(r[col] for r in bound))),
    )
    with open(a.out, "w") as f:
        json.dump(doc, f, indent=1)
    p, s = doc["plugin_resolved"]["picker.DL3C"]["resolved"], doc["plugin_resolved"]["spicker.SDL3C"]["resolved"]
    print(f"{a.variant}: window {p['window_duration_s']:.2f} s; P windows end {p['attempt_window_ends_after_reference_s']} s "
          f"after the trigger; S windows end {s['attempt_window_ends_after_reference_s']} s after the P pick; "
          f"{len(streams)} streams in scautopick's dump; module keys {len(module)}; app settings {len(settings)}")


if __name__ == "__main__":
    main()
