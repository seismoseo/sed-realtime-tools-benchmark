# v09_seisbench_rerun.py -- independent verifier of step 09, part 2 (SeisBench re-run on 3 events).
# Env: dl-base (READ-ONLY: nothing is installed; run as 'python -I'), CPU only, few threads.
#
# Why: step 09 claims that the plugin (ONNX, scdlrtpicker) and SeisBench (torch, same weights) give the same
# picks to about 0.01-0.02 s. This script re-runs SeisBench's continuous picking (classify) myself, with
# my own freshly downloaded weights (SEISBENCH_CACHE_ROOT in this verifier's folder, not step 09's cache),
# on 3 of the 11 events, for ONE model (PhaseNet 'instance'). Settings as stated in the step-09 notes:
# P_threshold 0.4, S_threshold 0.3 (the plugin's minConfidence), strict=True, all else at the defaults.
# The resolved settings are dumped to JSON.
#
# It also writes weight-test windows for an ONNX-vs-torch comparison (v09_weights_onnx.py, env pyrtdd):
# windows DIFFERENT from step 09's (S-centred and noise windows of the 3 events, not P-centred event-3
# windows), normalised by SeisBench's own annotate_batch_pre, with the torch outputs.
#
# Workaround, required because the env is read-only: seisbench 0.11.0 raises
# "ImportError: Optional dependency 'xdas' is required" when importing seisbench.models (a type annotation
# xdas.DataArray in seisbench/models/das_base.py is evaluated at import). A stub module 'xdas' with
# placeholder classes is put into sys.modules of THIS process only. No DAS code is used.
#
# Usage: python -I v09_seisbench_rerun.py            # dry run: print what would be run
#        python -I v09_seisbench_rerun.py --apply    # run and write outputs

import argparse
import hashlib
import json
import os
import resource
import sys
import time
import types

# ------------------------------------------------------------------------------------------- parameters
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
RUN09 = f"{PROJECT}/runs/gwangyang/dlpicker"                   # read only: sorted playback + bound sensors
OUT_DIR = f"{PROJECT}/runs/verify_gwangyang_dl/seisbench"
EVENTS = ["20210827220322", "20210828234556", "20260203021535"]   # ML 2.2, 1.5, 1.1 (one large, one mid, one small)
MODEL_CLASS, WEIGHTS = "PhaseNet", "instance"                     # = plugin model phasenet_instance.onnx
EXPLICIT_ARGS = dict(P_threshold=0.4, S_threshold=0.3, strict=True)
THREADS = 2                                                       # Server A is shared
N_WEIGHT_TEST_WINDOWS_PER_EVENT = 4                               # S-centred windows per event (+1 noise window)


def cpu_s():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def jsonable(x):
    import numpy as np
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    return repr(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    cache = os.environ.get("SEISBENCH_CACHE_ROOT", "")
    if not cache.startswith(f"{PROJECT}/runs/verify_gwangyang_dl/"):
        sys.exit(f"ERROR: SEISBENCH_CACHE_ROOT must be inside the verifier folder, got '{cache}'")
    print(f"events {EVENTS}; {MODEL_CLASS}.from_pretrained('{WEIGHTS}'); args {EXPLICIT_ARGS}; threads {THREADS}; "
          f"cache {cache}; out {OUT_DIR}")
    if not a.apply:
        print("dry run: nothing run (use --apply)")
        return

    stub = types.ModuleType("xdas")
    for n in ("DataArray", "Coordinate", "InterpCoordinate"):
        setattr(stub, n, type(n, (), {}))
    sys.modules["xdas"] = stub

    import numpy as np
    import obspy
    import pandas as pd
    import torch
    import seisbench
    import seisbench.models as sbm

    torch.set_num_threads(THREADS)
    torch.set_grad_enabled(False)
    os.makedirs(OUT_DIR, exist_ok=True)

    sb = pd.read_csv(f"{RUN09}/config/stations_bound.csv")
    sensor = dict(zip(sb.loc[sb.bound == 1, "station"], sb.loc[sb.bound == 1, "sensor"]))
    ref = pd.read_csv(f"{DATA}/reference_tables/picks_phasenet_plus.csv", dtype={"kma_id": str})
    hyp = pd.read_csv(f"{DATA}/reference_tables/hypoinverse_kim1983.csv", dtype={"kma_id": str}).set_index("kma_id")

    c0, w0 = cpu_s(), time.time()
    model = getattr(sbm, MODEL_CLASS).from_pretrained(WEIGHTS)
    model.eval()
    load = dict(cpu_s=cpu_s() - c0, wall_s=time.time() - w0)

    # every classify argument as resolved: explicit > weight-file defaults > class defaults
    class_defaults = {k: v[1] for k, v in model._annotate_args.items()}
    resolved = dict(class_defaults)
    resolved.update(model.default_args or {})
    resolved.update(EXPLICIT_ARGS)
    files = {}
    wdir = os.path.join(str(seisbench.cache_root), "models", "v3", MODEL_CLASS.lower())
    for f in sorted(os.listdir(wdir)) if os.path.isdir(wdir) else []:
        files[f] = hashlib.sha256(open(os.path.join(wdir, f), "rb").read()).hexdigest()

    rows, timing, raws, used = [], {}, [], []
    for k in EVENTS:
        st = obspy.read(f"{RUN09}/input/{k}_sorted.mseed")
        st = obspy.Stream([tr for tr in st if tr.stats.station in sensor and tr.stats.channel[:2] == sensor[tr.stats.station]])
        c1, w1 = cpu_s(), time.time()
        out = model.classify(st.copy(), **EXPLICIT_ARGS)
        timing[k] = dict(cpu_s=cpu_s() - c1, wall_s=time.time() - w1, n_traces=len(st))
        for p in out.picks:
            rows.append(dict(kma_id=k, trace_id=p.trace_id, station=p.trace_id.split(".")[1], phase=p.phase,
                             peak_time=str(p.peak_time), peak_value=float(p.peak_value),
                             start_time=str(p.start_time), end_time=str(p.end_time)))
        # weight-test windows: centred on PhaseNet+ S picks at stations of different sensors, plus 1 noise window
        n = model.in_samples
        r = ref[(ref.kma_id == k) & (ref.phase == "S")].sort_values("epi_dist_km")
        picks = list(r.iloc[np.linspace(0, len(r) - 1, N_WEIGHT_TEST_WINDOWS_PER_EVENT).round().astype(int)].itertuples())
        targets = [(p.station, obspy.UTCDateTime(p.time), "S-centred") for p in picks]
        origin = obspy.UTCDateTime(hyp.loc[k, "origin_time"])
        targets.append((picks[0].station, origin - 60.0, "noise, origin-60 s"))
        for s, tc, kind in targets:
            t0 = tc - (n // 2) / 100.0
            comp = []
            for c in model.component_order:
                trs = st.select(station=s, channel=f"??{c}")
                if len(trs) != 1:
                    break
                tr = trs[0]
                i0 = int(round((t0 - tr.stats.starttime) * tr.stats.sampling_rate))
                if i0 < 0 or i0 + n > tr.stats.npts:
                    break
                comp.append(tr.data[i0:i0 + n].astype(np.float32))
            if len(comp) == 3:
                raws.append(np.stack(comp))
                used.append(f"{k}|{s}|{kind}")
    pd.DataFrame(rows).to_csv(f"{OUT_DIR}/phasenet_instance_picks_3events.csv", index=False)

    raw = torch.tensor(np.stack(raws))
    x = model.annotate_batch_pre(raw.clone(), {})
    y = model(x)
    np.savez(f"{OUT_DIR}/phasenet_instance_weight_test_windows.npz", raw=raw.numpy(), x_seisbench=x.numpy(),
             y_torch=y.numpy(), labels=np.array(list(model.labels)), windows=np.array(used),
             component_order=np.array(list(model.component_order)))

    settings = dict(script=os.path.abspath(__file__), events=EVENTS, model_class=MODEL_CLASS, weights=WEIGHTS,
                    weights_version=model.weights_version, weights_files_sha256=files, explicit_args=EXPLICIT_ARGS,
                    resolved_args=resolved, class_default_args=class_defaults, weight_default_args=model.default_args,
                    component_order=model.component_order, in_samples=model.in_samples,
                    sampling_rate=model.sampling_rate, labels=model.labels, norm=getattr(model, "norm", None),
                    norm_amp_per_comp=getattr(model, "norm_amp_per_comp", None),
                    norm_detrend=getattr(model, "norm_detrend", None), threads=torch.get_num_threads(),
                    cache_root=str(seisbench.cache_root), versions=dict(seisbench=seisbench.__version__,
                    torch=torch.__version__, obspy=obspy.__version__, numpy=np.__version__, python=sys.version),
                    xdas_stub="placeholder classes DataArray, Coordinate, InterpCoordinate in sys.modules['xdas']",
                    load=load, timing=timing, n_picks=len(rows), weight_test_windows=used)
    json.dump(jsonable(settings), open(f"{OUT_DIR}/settings_v09_seisbench_rerun.json", "w"), indent=1)
    print(json.dumps(jsonable(dict(weights_version=model.weights_version, files=files, n_picks=len(rows),
                                   timing=timing, windows=used)), indent=1))


if __name__ == "__main__":
    main()
