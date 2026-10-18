# 14_seisbench_run.py -- step 14 copy of runs/sanramon/dlpicker/scripts/12_seisbench_run.py (San Ramon 2015, step 12; not modified).
# Changed: TEST_EVENT = the 2025-26 mainshock 75305736 (2015: 72540765). Nothing else.
#
# 12_seisbench_run.py -- step 12 helper, run in conda env 'dl-base' (READ-ONLY env: nothing is installed into
# it; run as 'python -I'). Adapted from step 09's 09_seisbench_run.py.
#
# Cross-check of the scdlrtpicker plugin against SeisBench for ONE weight set, eqtp_ncedc = SeisBench
# EQTP.from_pretrained('ncedc'), on a few events. This model is the interesting one to check because step T
# found that the plugin feeds it a different input than SeisBench does: the plugin divides each component by
# its own standard deviation, SeisBench's EQTransformer family ('std' norm, norm_amp_per_comp False) divides
# all three components by ONE standard deviation, and SeisBench also tapers 6 samples at each window end.
#
# What SeisBench gets: the same raw streams the plugin saw, i.e. for every station the three channels of the
# bound sensor of binding set 'main' (config/coverage_bound.csv: z, h1, h2 = the vertical and the first and
# second horizontal exactly as SeisComP's getThreeComponents orders them). Because SeisBench recognises
# components by the last letter of the channel code (Z, N, E), the channels are renamed in memory to
# <sensor>Z / <sensor>N / <sensor>E in that order (this only matters for 1/2/3-named sensors, and gives
# SeisBench the plugin's own component assignment). SeisBench resamples 200/500/40 Hz data to 100 Hz itself.
#   - classify(): SeisBench's continuous picking (overlapping windows over the whole record, combined, trigger
#     on/off per phase curve, peak = pick; EQTP adds the polarity at each P pick);
#   - thresholds: P 0.4 / S 0.3 (= the plugin's minConfidence) and polarity 0.5 (= the plugin's
#     polarityMinConfidence); every other argument stays at SeisBench's default and is dumped;
#   - strict=True: only spans where all three components exist.
# Weight-equality windows: for the mainshock file, 12000-sample raw windows (Z, H1, H2) centred on the
# analyst P pick at up to 8 stations whose bound sensor records at 100 Hz; saved with SeisBench's
# annotate_batch_pre() input and the torch outputs, for 12_weights_check.py (ONNX vs torch).
#
# Workaround as in step 09: a stub module 'xdas' is registered before importing seisbench (seisbench 0.11.0
# cannot import seisbench.models without it; the DAS code is never used). SEISBENCH_CACHE_ROOT must point
# inside the project.
#
# Outputs (in --out-dir): eqtp_ncedc_picks.csv, eqtp_ncedc_settings.json, eqtp_ncedc_weights_test.npz, run.json

import argparse
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
NAME, CLS, DATASET = "eqtp_ncedc", "EQTP", "ncedc"
TEST_EVENT = "75305736"
N_TEST = 8


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
    ap.add_argument("--coverage", required=True)
    ap.add_argument("--events", nargs="+", required=True)
    ap.add_argument("--p-threshold", type=float, required=True)
    ap.add_argument("--s-threshold", type=float, required=True)
    ap.add_argument("--polarity-threshold", type=float, required=True)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--ref", required=True, help="NCSS analyst picks (only to centre the weight-test windows)")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    if not str(seisbench.cache_root).startswith(PROJECT):
        sys.exit(f"ERROR: SEISBENCH_CACHE_ROOT={seisbench.cache_root} is not inside {PROJECT}")
    os.makedirs(a.out_dir, exist_ok=True)
    torch.set_num_threads(a.threads)
    torch.set_grad_enabled(False)

    cov = pd.read_csv(a.coverage, dtype={"event_id": str, "location": str}).fillna({"location": ""})
    cov = cov[cov["role"] == "main"]
    ref = pd.read_csv(a.ref, dtype={"event_id": str})

    streams, renamed = {}, {}
    for e in a.events:
        st = obspy.read(os.path.join(a.sorted_dir, f"{e}_sorted.mseed"))
        out = obspy.Stream()
        for c in cov[cov["event_id"] == e].itertuples():
            for orig, new in ((c.z, "Z"), (c.h1, "N"), (c.h2, "E")):
                for tr in st.select(network=c.network, station=c.station, location=c.location, channel=orig):
                    tr = tr.copy()
                    tr.stats.channel = c.sensor + new
                    out.append(tr)
                    renamed[f"{c.network}.{c.station}.{c.location}.{orig}"] = c.sensor + new
        streams[e] = out
    zspan_h = sum(tr.stats.endtime - tr.stats.starttime for st in streams.values() for tr in st
                  if tr.stats.channel.endswith("Z")) / 3600.0

    c0, w0 = cpu_s(), time.time()
    model = getattr(sbm, CLS).from_pretrained(DATASET)
    model.eval()
    c_load, w_load = cpu_s() - c0, time.time() - w0
    argdict = dict(P_threshold=a.p_threshold, S_threshold=a.s_threshold, polarity_threshold=a.polarity_threshold,
                   strict=True)
    resolved = {k: v[1] for k, v in model._annotate_args.items()}
    resolved.update(model.default_args or {})
    resolved.update(argdict)
    settings = dict(model=NAME, seisbench_class=CLS, dataset=DATASET, seisbench_version=seisbench.__version__,
                    torch_version=torch.__version__, threads=torch.get_num_threads(),
                    weights_version=model.weights_version, weights_docstring=model.weights_docstring,
                    explicit_args=argdict, resolved_args=resolved,
                    class_default_args={k: v[1] for k, v in model._annotate_args.items()},
                    weight_default_args=model.default_args, component_order=model.component_order,
                    sampling_rate=model.sampling_rate, in_samples=model.in_samples,
                    norm=getattr(model, "norm", None), norm_amp_per_comp=getattr(model, "norm_amp_per_comp", None),
                    norm_detrend=getattr(model, "norm_detrend", None), labels=getattr(model, "labels", None),
                    events=a.events, channel_renaming=renamed)
    rows = []
    c1, w1 = cpu_s(), time.time()
    for e, st in streams.items():
        out = model.classify(st.copy(), **argdict)
        for p in out.picks:
            rows.append(dict(model=NAME, event_id=e, trace_id=p.trace_id,
                             nsta=".".join(p.trace_id.split(".")[:2]), phase=p.phase,
                             peak_time=str(p.peak_time), peak_value=float(p.peak_value),
                             start_time=str(p.start_time), end_time=str(p.end_time),
                             polarity=getattr(p, "polarity", None) or "",
                             polarity_value=float(getattr(p, "polarity_value", np.nan) or np.nan)))
    c_run, w_run = cpu_s() - c1, time.time() - w1
    pd.DataFrame(rows).to_csv(f"{a.out_dir}/{NAME}_picks.csv", index=False)

    # weight-equality windows: raw counts centred on the analyst P pick, components in the plugin's order
    st = streams[TEST_EVENT]
    n = model.in_samples
    r = ref[(ref["event_id"] == TEST_EVENT) & (ref["phase"] == "P") & ref["usable"]].sort_values("epi_dist_km")
    raws, used = [], []
    for x in r.itertuples():
        sel = st.select(network=x.network, station=x.station)
        if len(sel) != 3 or any(tr.stats.sampling_rate != 100.0 for tr in sel):
            continue
        t0 = obspy.UTCDateTime(x.time_utc) - (n // 2) / 100.0
        comp = []
        for c in "ZNE":
            tr = sel.select(channel=f"??{c}")
            if len(tr) != 1:
                break
            tr = tr[0]
            i0 = int(round((t0 - tr.stats.starttime) * tr.stats.sampling_rate))
            if i0 < 0 or i0 + n > tr.stats.npts:
                break
            comp.append(tr.data[i0:i0 + n].astype(np.float32))
        if len(comp) == 3:
            raws.append(np.stack(comp))
            used.append(f"{x.network}.{x.station}.{sel[0].stats.channel[:2]}")
        if len(used) >= N_TEST:
            break
    raw = torch.tensor(np.stack(raws))
    xin = model.annotate_batch_pre(raw.clone(), {})
    y = model(xin)
    y = torch.stack(list(y), dim=1)              # EQTP forward: (Polarity_U, Polarity_D, P, S)
    names = ["Polarity_U", "Polarity_D", "P", "S"]
    np.savez(f"{a.out_dir}/{NAME}_weights_test.npz", raw=raw.numpy(), x_seisbench=xin.numpy(), y_torch=y.numpy(),
             names=np.array(names), stations=np.array(used), component_order=np.array(list(model.component_order)),
             norm=str(getattr(model, "norm", "")))

    settings.update(cpu_load_s=c_load, wall_load_s=w_load, cpu_classify_s=c_run, wall_classify_s=w_run,
                    station_hours_Z=zspan_h, cpu_s_per_station_hour=c_run / zspan_h if zspan_h else None,
                    n_picks=len(rows), weights_test_stations=used, output_names=names)
    with open(f"{a.out_dir}/{NAME}_settings.json", "w") as f:
        json.dump(jsonable(settings), f, indent=1)
    with open(f"{a.out_dir}/run.json", "w") as f:
        json.dump(jsonable(dict(seisbench=seisbench.__version__, torch=torch.__version__,
                                threads=torch.get_num_threads(), cache_root=str(seisbench.cache_root),
                                events=a.events, station_hours_Z=zspan_h, n_picks=len(rows),
                                cpu_classify_s=c_run, wall_classify_s=w_run)), f, indent=1)
    print(f"{NAME}: SeisBench {CLS}.from_pretrained('{DATASET}') version {model.weights_version}; {len(rows)} picks; "
          f"classify CPU {c_run:.1f} s, wall {w_run:.1f} s for {zspan_h:.2f} station-hours "
          f"({c_run / zspan_h:.2f} CPU s per station-hour); test windows {used}", flush=True)


if __name__ == "__main__":
    main()
