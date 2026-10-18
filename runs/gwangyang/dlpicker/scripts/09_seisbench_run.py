# 09_seisbench_run.py -- step 09 helper, run in conda env 'dl-base' (READ-ONLY env: nothing is installed
# into it; run as 'python -I' so neither the user site nor the current folder can inject modules).
#
# Cross-check of the scdlrtpicker plugin against SeisBench with the SAME weight sets: SeisBench's own
# continuous picking (classify(): overlapping sliding windows over the whole record, combined, then a
# trigger on/off on each phase curve with the peak as the pick) on the same raw 3-component streams the
# plugin saw (the bound sensor's Z, N, E of every station, raw counts, 100 Hz, every event file).
#   - weights: <Model>.from_pretrained(<dataset>) = the latest version on the SeisBench server (v2 for
#     both models, the version step T recorded for the ONNX exports). 09_weights_check.py then proves
#     the weights are identical by running the ONNX file and the torch model on the same input windows
#     written here (*_weights_test.npz);
#   - thresholds: P_threshold / S_threshold = the plugin's minConfidence (0.4 / 0.3); SeisBench's trigger
#     off level is half of it (its fixed rule). Every other annotate/classify argument stays at the weight
#     set's / model's default and is dumped to <model>_settings.json;
#   - strict=True: only time spans where all three components exist are processed (the plugin also needs
#     all three); the data have no gaps.
# CPU: torch threads limited by --threads (Server A is shared); CPU time of the process is measured with
# resource.getrusage before/after each model (it includes reading the miniSEED files).
#
# Workaround (no change to the env): seisbench 0.11.0 cannot import seisbench.models without its optional
# dependency 'xdas' (ImportError raised at import of seisbench/models/das_base.py, where a type annotation
# 'xdas.DataArray' is evaluated). The DAS code is never used here, so a stub module 'xdas' with placeholder
# classes is registered in sys.modules of THIS process before importing seisbench.
#
# SEISBENCH_CACHE_ROOT must point inside the project (the driver sets it); the script refuses otherwise.
#
# Outputs (in --out-dir): <model>_picks.csv, <model>_settings.json, <model>_weights_test.npz, run.json

import argparse
import glob
import json
import os
import resource
import sys
import time
import types

_stub = types.ModuleType("xdas")
for _n in ("DataArray", "Coordinate", "InterpCoordinate"):
    setattr(_stub, _n, type(_n, (), {}))
sys.modules["xdas"] = _stub

import numpy as np                      # noqa: E402
import obspy                            # noqa: E402
import pandas as pd                     # noqa: E402
import torch                            # noqa: E402
import seisbench                        # noqa: E402
import seisbench.models as sbm          # noqa: E402

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
MODELS = {"phasenet_instance": ("PhaseNet", "instance"), "eqtransformer_stead": ("EQTransformer", "stead")}
# input windows for the weight-equality test: event ML 2.2, stations of every sensor type and distance
TEST_EVENT = "20210827220322"
TEST_STATIONS = ["GWYB", "BAU", "HAIA", "JASA", "MMD", "YOA"]


def cpu_s():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def jsonable(x):
    if isinstance(x, (list, tuple)):
        return [jsonable(y) for y in x]
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    return str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sorted-dir", required=True)
    ap.add_argument("--bound", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--p-threshold", type=float, required=True)
    ap.add_argument("--s-threshold", type=float, required=True)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--ref", required=True, help="PhaseNet+ picks (only to centre the weight-test windows)")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    if not str(seisbench.cache_root).startswith(PROJECT):
        sys.exit(f"ERROR: SEISBENCH_CACHE_ROOT={seisbench.cache_root} is not inside {PROJECT}")
    os.makedirs(a.out_dir, exist_ok=True)
    torch.set_num_threads(a.threads)
    torch.set_grad_enabled(False)

    bound = pd.read_csv(a.bound)
    sensor = dict(zip(bound.loc[bound["bound"] == 1, "station"], bound.loc[bound["bound"] == 1, "sensor"]))
    files = sorted(glob.glob(os.path.join(a.sorted_dir, "*_sorted.mseed")))
    ref = pd.read_csv(a.ref, dtype={"kma_id": str})

    streams = {}
    for f in files:
        kma = os.path.basename(f)[:14]
        st = obspy.read(f)
        st = obspy.Stream([tr for tr in st if tr.stats.station in sensor
                           and tr.stats.channel[:2] == sensor[tr.stats.station]])
        streams[kma] = st
    zspan_h = sum(tr.stats.endtime - tr.stats.starttime for st in streams.values() for tr in st
                  if tr.stats.channel.endswith("Z")) / 3600.0

    run = dict(seisbench=seisbench.__version__, torch=torch.__version__, threads=torch.get_num_threads(),
               cache_root=str(seisbench.cache_root), files=files, station_hours_Z=zspan_h, models={})
    for name in a.models:
        cls_name, ds = MODELS[name]
        cls = getattr(sbm, cls_name)
        c0, w0 = cpu_s(), time.time()
        model = cls.from_pretrained(ds)
        model.eval()
        c_load, w_load = cpu_s() - c0, time.time() - w0
        argdict = dict(P_threshold=a.p_threshold, S_threshold=a.s_threshold, strict=True)
        # every annotate/classify argument as it will be resolved: explicit > weight defaults > class defaults
        resolved = {k: v[1] for k, v in model._annotate_args.items()}
        resolved.update(model.default_args or {})
        resolved.update(argdict)
        settings = dict(model=name, seisbench_class=cls_name, dataset=ds, weights_version=model.weights_version,
                        weights_docstring=model.weights_docstring, explicit_args=argdict,
                        resolved_args=resolved, class_default_args={k: v[1] for k, v in model._annotate_args.items()},
                        weight_default_args=model.default_args, component_order=model.component_order,
                        sampling_rate=model.sampling_rate, in_samples=model.in_samples,
                        norm=getattr(model, "norm", None), norm_amp_per_comp=getattr(model, "norm_amp_per_comp", None),
                        norm_detrend=getattr(model, "norm_detrend", None),
                        filter_args=getattr(model, "filter_args", None), filter_kwargs=getattr(model, "filter_kwargs", None),
                        labels=getattr(model, "labels", None))
        rows = []
        c1, w1 = cpu_s(), time.time()
        for kma, st in streams.items():
            out = model.classify(st.copy(), **argdict)
            for p in out.picks:
                rows.append(dict(model=name, kma_id=kma, trace_id=p.trace_id, station=p.trace_id.split(".")[1],
                                 phase=p.phase, peak_time=str(p.peak_time), peak_value=float(p.peak_value),
                                 start_time=str(p.start_time), end_time=str(p.end_time)))
        c_run, w_run = cpu_s() - c1, time.time() - w1
        pd.DataFrame(rows).to_csv(f"{a.out_dir}/{name}_picks.csv", index=False)

        # weight-equality test windows: raw counts centred on the PhaseNet+ P pick, in the model's component order
        st = streams[TEST_EVENT]
        raws, used = [], []
        n = model.in_samples
        for s in TEST_STATIONS:
            r = ref[(ref["kma_id"] == TEST_EVENT) & (ref["station"] == s) & (ref["phase"] == "P")]
            if len(r) != 1:
                continue
            t0 = obspy.UTCDateTime(r["time"].iloc[0]) - (n // 2) / 100.0
            comp = []
            for c in model.component_order:
                tr = st.select(station=s, channel=f"??{c}")
                if len(tr) != 1:
                    break
                tr = tr[0]
                i0 = int(round((t0 - tr.stats.starttime) * tr.stats.sampling_rate))
                if i0 < 0 or i0 + n > tr.stats.npts:
                    break
                comp.append(tr.data[i0:i0 + n].astype(np.float32))
            if len(comp) == 3:
                raws.append(np.stack(comp))
                used.append(s)
        raw = torch.tensor(np.stack(raws))
        x = model.annotate_batch_pre(raw.clone(), {})
        y = model(x)
        if isinstance(y, (tuple, list)):          # EQTransformer: (Detection, P, S), each [B, N]
            y = torch.stack(list(y), dim=1)
            names = ["Detection", "P", "S"]
        else:                                      # PhaseNet: [B, len(labels), N] in label order
            names = list(model.labels)
        np.savez(f"{a.out_dir}/{name}_weights_test.npz", raw=raw.numpy(), x_seisbench=x.numpy(),
                 y_torch=y.numpy(), names=np.array(names), stations=np.array(used),
                 component_order=np.array(list(model.component_order)), norm=str(getattr(model, "norm", "")))

        settings.update(cpu_load_s=c_load, wall_load_s=w_load, cpu_classify_s=c_run, wall_classify_s=w_run,
                        station_hours_Z=zspan_h, cpu_s_per_station_hour=c_run / zspan_h, n_picks=len(rows),
                        weights_test_stations=used, output_names=names)
        with open(f"{a.out_dir}/{name}_settings.json", "w") as f:
            json.dump(jsonable(settings), f, indent=1)
        run["models"][name] = dict(weights_version=model.weights_version, n_picks=len(rows),
                                   cpu_classify_s=c_run, wall_classify_s=w_run)
        print(f"{name}: SeisBench {cls_name}.from_pretrained('{ds}') version {model.weights_version}; "
              f"{len(rows)} picks; classify CPU {c_run:.1f} s, wall {w_run:.1f} s for {zspan_h:.1f} station-hours "
              f"({c_run / zspan_h:.2f} CPU s per station-hour); test windows {used}", flush=True)
    with open(f"{a.out_dir}/run.json", "w") as f:
        json.dump(jsonable(run), f, indent=1)


if __name__ == "__main__":
    main()
