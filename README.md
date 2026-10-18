# SED's scdlrtpicker, scrtdd and pyrtdd on Server A

Checked 2026-10-17 on Server A (Rocky Linux 10.2, no sudo) on two benchmarks:
- **Gwangyang**: the user's own 11-event KMA benchmark, with PhaseNet+ picks and a HypoDD dt.ct/dt.cc solution.
- **San Ramon**: the public 2015 San Ramon swarm in California (685 events, NCEDC data), compared with Waldhauser's published double-difference catalog.

## The answer in short

All three packages install and run on Server A, entirely in user space, with no source patches. On both benchmarks they
reproduce trusted results. Two bugs in pyrtdd (not in scrtdd) need the workarounds described below.

| Package | Installs? | Own tests | Gwangyang (11 events) | San Ramon (685 / 26 events) |
|---|---|---|---|---|
| **scrtdd** v2.0.10 (SeisComP 7.4.0 module) | yes (built in about 3.5 min) | 7 of 7 pass (898 cases) | Cluster shape matches HypoDD dt.cc to 3.1 m horizontal / 4.3 m vertical RMS; inter-event distances r = 0.997 | Median 97 m horizontal / 106 m vertical from the LDEO DD catalog after removing the centroid (51 / 63 m in local geometry); routine catalog 229 / 394 m |
| **pyrtdd** (master d122c3a = scrtdd v2.0.9 engine) | yes (pip, 16 s) | 46 of 46 pass | Same as scrtdd, but **only with our workaround**: stock pyrtdd silently skips the band-pass (5.7 / 8.2 m) | Same as scrtdd within 1 m (median), with the workaround |
| **scdlrtpicker** v1.1.1 (plugin for scautopick/scolv) | yes (with ONNX Runtime 1.31.0) | none upstream; plugin load + smoke test pass | Best model finds 91 % of P and 86 % of S PhaseNet+ picks, median timing difference 0.03 s | On complete 3-component records 82 % of analyst P and 80 % of S picks; 31 % of all analyst picks (see limits) |

A **real-time chain** also ran end to end on Server A, with all traffic on localhost: waveforms → DL picker → scautoloc → scevent → scrtdd. The first relocated origin came about 60 s after the origin time, 61 m and 5 m from the offline multi-event positions.

## How to use the installation

```bash
# SeisComP 7.4.0 with scrtdd and the DL picker (also switches off ONNX Runtime telemetry)
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
scrtdd --version          # scrtdd: 2.0.10, Framework: 7.4.0 Release
scautopick --help
# note: SeisComP ships its own 'timeout' program; use /usr/bin/timeout in scripts

# pyrtdd (Python, no SeisComP); also the Jupyter kernel "pyrtdd"
source /home/msseo/miniforge3/etc/profile.d/conda.sh; conda activate pyrtdd
python -c "import pyrtdd.hdd"
```

Working configurations to copy:
- scrtdd profiles: `runs/gwangyang/scrtdd/templates/` and `runs/sanramon/scrtdd/`;
- scautopick with the DL picker: `runs/gwangyang/dlpicker/` and `runs/sanramon/dlpicker/config/`;
- the real-time setup: `runs/gwangyang/realtime/scripts/`.

## Results, with notebooks

Every figure lives in an executed notebook in `notebooks/`, with PNG and PDF copies in `notebooks/figures/`. Each notebook ends with a computed summary.

| Notebook | What it shows |
|---|---|
| `02_gwangyang_relocation` | rtDD against your HypoDD solution; scrtdd = pyrtdd; the pyrtdd filter bug made visible; absolute drift; single-event (real-time) mode; which settings matter |
| `03_gwangyang_dlpicker` | DL picker against PhaseNet+: recall, precision, timing, magnitude and distance; waveforms; SeisBench check; relocation with DL picks |
| `04_gwangyang_realtime` | Data flow, latency timeline and positions of the real-time chain test |
| `05_gwangyang_sp_offset` | Finding: the reference S-P times are about 0.27 s shorter than the kim1983 model predicts (see below) |
| `06_sanramon_relocation` | rtDD against the LDEO and NCEDC double-difference catalogs; fault-plane sharpening |
| `07_sanramon_dlpicker` | DL picker against NCSS analyst picks; what limits recall; eqtp_ncedc first-motion polarity |

The written results, in plain language and with every table, are in:
- `docs/results/07_gwangyang_pyrtdd.md`
- `08_gwangyang_scrtdd.md`
- `09_gwangyang_dlpicker.md`
- `10_gwangyang_realtime.md`
- `11_sanramon_relocation.md`
- `12_sanramon_dlpicker.md`

Independent verifiers recomputed the headline numbers. Their findings and the corrections are in
`docs/results/verification_findings_gwangyang.md` and `docs/results/fixes_after_verification.md`.

### Gwangyang

**Relocation** (notes 07, 08; notebook 02)
- **Cross-correlation.** With the band-pass actually applied, scrtdd (S1) and pyrtdd (R1f) reproduce the HypoDD dt.cc cluster shape to
  3.1 m horizontal / 4.3 m vertical RMS. Five of the 11 events lie inside HypoDD's own bootstrap 95 % box, and the
  others miss it by at most 1.47 times its half-width. For the measurements HypoDD kept in its final iteration, 90 % of rtDD's
  differential times agree with the reference dt.cc within 2 ms; over all common measurements, 72 %.
- **scrtdd and pyrtdd agree.** Catalog-only runs are identical to the last digit. Cross-correlation runs agree within 1.8 m, with 2787 of 2801 lags identical.
- **Catalog only** (no cross-correlation): 40 m horizontal / 60 m vertical RMS from HypoDD dt.ct. For scale, HypoDD's own dt.ct and dt.cc differ by 33 / 39 m.
- **Single-event (real-time) mode, leave-one-out:** events land a median 0.3-1.7 m from their
  multi-event positions. The ML 2.2 is the exception, at 28-44 m.

**DL picker** (note 09; notebook 03)
- **Best model** (phasenet_original): P recall 0.91, S recall 0.86, median |dt| 0.030 / 0.025 s against PhaseNet+.
- **Small events are harder:** for ML < 1.5, P recall is 0.43-0.82.
- **Same weights as SeisBench.** The plugin runs SeisBench's own weights (output difference ≤ 1e-6), and its pick times agree with SeisBench's.
- **Cheap to run:** 0.11-0.34 CPU-s per station-hour.
- **"Fast" P settings** give a pick 1.3 s after the onset instead of 15 s, at about 4 times the false P picks.

**Real-time chain** (note 10; notebook 04)
- **What works:** DL picks → scautoloc (LOCSAT) → scevent → scrtdd, with scmaster on 127.0.0.1 only. Everything was stopped afterwards.
- **Latency:** the first relocated origin comes about 59-63 s after the origin time. That is about 17 s for the DL picker's window, 14 s waiting for the mb amplitude, and 10 s of scrtdd delay plus computing.
- **Accuracy:** the LOCSAT start was 2.7-3.9 km too shallow. scrtdd moved it to 61 m (ML 2.2) and 5 m (ML 1.6) from the offline result.

### The S-P finding (notebook 05)

- **What it is.** Your Gwangyang S-P times are about 0.27 s shorter than the kim1983 model predicts, at almost every station and in
  every event:
  - hand picks: -0.273 s (95 % CI -0.304 to -0.239);
  - PhaseNet+: -0.262 s;
  - the four DL models: -0.25 to -0.31 s;
  - an automatic onset detector that uses no picks: -0.22 s.
- **It is not a picker artifact.** Your hand picks agree with PhaseNet+ to 0.01-0.02 s.
- **Vp/Vs still fits.** The Wadati slope gives Vp/Vs 1.728 (95 % CI 1.719-1.736).
- **Not perfectly constant.** The offset is -0.43 s at 60-70 km, driven by three stations, and station medians scatter by 0.11 s.
- **Cause not settled.** Either a near-source / shared-convention constant, or a slightly shallower source with lower Vp/Vs
  near the surface, fits about equally well.
- **Effect on absolute locations.** Correcting the S picks by 0.27 s moves NonLinLoc hypocenters (stations within 35 km) by 1.6 km in depth and
  0.1 s in origin time.
- **Effect on double differences.** Relative positions are exactly unchanged by any S shift common to all events. Event-specific parts move events by
  up to 11 m.

### San Ramon

**Relocation** (note 11; notebook 06)
- **Events relocated:** 680 of 685 (5 have fewer than 8 picks).
- **Against the LDEO NCAeqDD catalog** (median per event, centroid removed):
  - with cross-correlation (P1 = S1): 97 / 106 m (horizontal / vertical), and 51 / 63 m in local geometry;
  - catalog only: 142 / 134 m;
  - the routine NCSS start: 229 / 394 m;
  - NCEDC's own DD catalog: 162 / 236 m.
  - 89 % of events end closer to LDEO than they started, 98 % in local geometry.
- **Fault plane:** 354.6°/86.1° against LDEO's 352.5°/83.6°.
- **pyrtdd vs scrtdd:** a median 0.25 m apart (catalog only) and 1.1 m (cross-correlation).
- **Runtime:** cross-correlation runs take 19-28 min on one core.
- **Absolute position:** the default solver put the cluster 2.3 km too deep, probably because the routine CON grids have no station corrections. Use the relative geometry.

**DL picker** (note 12; notebook 07)
- **Complete 3-component records:** phasenet_instance finds 82 % of analyst P and 80 % of S picks, median |dt| 0.03 s.
- **All analyst picks: 31 %.** The rest are lost to things outside the model:
  - vertical-only stations, because every shipped model is 3-component;
  - triggered strong-motion records that start before scautopick's 60 s warm-up;
  - overlapping swarm events, because the plugin keeps one P per window.
- **eqtp_ncedc first-motion polarity** agrees with the analysts in 83 % of cases at the default threshold and 90 % at 0.7.

## Problems found, and what to do about them

1. **pyrtdd: the waveform filter never reaches the cross-correlation.**
   - The C++ engine asks the Python waveform loader to filter each trace in place, but pyrtdd's pybind11 binding hands
     Python a copy (`software/src/pyrtdd/package/src/pyrtdd/hdd/proxy_ext.cpp:78-79`). The filtered samples are lost, and pyrtdd silently correlates unfiltered traces.
   - Proof: identical CC and lag with no filter, 5-20 Hz, 1 Hz low-pass, and a filter that zeroes every sample.
   - pyrtdd's own tests do not catch it.
   - Workaround: a loader subclass that filters inside `loadTrace` (`runs/gwangyang/pyrtdd/run_pyrtdd_gwangyang.py`).
   - scrtdd is not affected.
2. **pyrtdd single-event mode rejects KMA traces.** The ObsPy loader trims to the nearest sample, and KMA samples are a few ms
   off the request grid, so the returned window is slightly short. Only 1-2 of 5602 correlations survived.
   Workaround: request slightly wider windows. scrtdd is not affected.
3. **The official ONNX Runtime 1.31.0 contains Microsoft usage telemetry.** It is now switched off in `install/env_seiscomp.sh`
   (`ORT_DISABLE_TELEMETRY=1`). The 7 queued records held only system information and were deleted unsent. The conda ONNX Runtime used by pyrtdd has no telemetry.
4. **rtDD's absolute position needs care.**
   - With pure double differences (absLocConstraint 0) and the default damping of 0.01, a cluster can slide by
     kilometres while its shape stays right. Use damping of 0.1 or more, or the absolute constraint.
   - The absolute constraint inherits any travel-time model error (San Ramon: 2.3 km).
5. **The station inventory must match the travel-time grids exactly.** scrtdd finds NonLinLoc grids by station position.
   With the original Gwangyang StationXML (elevations 0 m, some stations 9-137 m off), only 6 of 108 lookups worked, and KWJU silently used KWJ2's grid. Fixed: `data/gwangyang_11ev/inputs/stations_rtdd.xml` (docs/install_notes/06).
6. **Real-time chain settings.**
   - scautoloc rejects DL picks unless `autoloc.dynamicPickThresholdInterval = 0`, because the DL "SNR" is a confidence of at most 1.
   - scautoloc associates P only, so scrtdd relocates without S. Offline, P+S improved 61 → 41 m.
   - seedlink cannot be bound to localhost, so it was not used on shared Server A.
7. **DL picker limits.**
   - All shipped models are 3-component.
   - The S picker runs only after a P pick.
   - The default `minConfidence` (P 0.4, S 0.3) is conservative, so most missed small-event picks are "below minConfidence"; a threshold study was not done.
   - In swarms, one P per window and the dead time cost picks.
8. **SeisComP details.**
   - The default database driver (MySQL) is not built, so `core.plugins = dbsqlite3` is set in `software/seiscomp/etc/global.cfg`.
   - SeisComP's `bin/timeout` shadows the system command.

I can draft GitHub issues for problems 1 and 2 for the SED developers with the evidence. Nothing has been posted.

## Folder map

| Folder | Content |
|---|---|
| `install/` | Install scripts 00-06: dry run by default, `--apply` to act; `env_seiscomp.sh` |
| `software/` | Sources, build trees, `seiscomp/` (SEISCOMP_ROOT), `NonLinLoc/`, `onnxruntime/` |
| `data/gwangyang_11ev/` | Read-only reference copy from server B (`reference/`, `PROVENANCE.md`), converted inputs, NonLinLoc grids, reference tables |
| `data/sanramon_2015/` | NCEDC catalogs, picks, StationXML, CON model and grids, waveforms, reference tables |
| `runs/` | Every run: option dumps, logs, outputs (`gwangyang/{pyrtdd,scrtdd,dlpicker,realtime,sp_offset}`, `sanramon/...`) |
| `notebooks/` | Notebooks 02-07, their builder scripts, `lib/`, `figures/` |
| `docs/` | `install_notes/`, `results/`, `reference_run_settings.md`, `sanramon_inputs.md`, `sanramon_waveforms.md`, `patches.md` (no source patches), `side_effects_outside_project.md` |
| `logs/` | Logs of every step |

## This public repository

github.com/seismoseo/sed-realtime-tools-benchmark holds a curated part of the project folder, listed by
`install/07_publish_selection.py`.

- **Included:**
  - code (install, run and analysis scripts, notebook builders);
  - notes (`docs/`);
  - executed notebooks and their figures;
  - small result tables, each 2 MB or less: the derived Gwangyang tables and the San Ramon tables.
- **Not included** (regenerate them with the install and run scripts):
  - raw waveforms (KMA, NCEDC);
  - StationXML and SeisComP inventories;
  - NonLinLoc travel-time grids;
  - databases and caches;
  - per-iteration dumps and logs;
  - third-party software: SeisComP, scrtdd and scdlrtpicker (AGPL-3.0), pyrtdd (MIT), NonLinLoc, ONNX Runtime. The install scripts fetch these from their official sources.
- **Redacted:** server addresses in text files are replaced by placeholders such as `<server-B>`, `<server-A>` and
  `<server-ip>` (a git clean filter). Paths such as `/home/msseo/works/...` are the original working paths.

Data and acknowledgements:
- **Gwangyang.** Waveforms and metadata come from the Korea Meteorological Administration (KMA). The picks, hand picks and HypoDD
  results are from the author's own Gwangyang analysis.
- **San Ramon.**
  - Waveforms, metadata and the NCSS catalog with picks were accessed through the Northern California
    Earthquake Data Center (NCEDC), doi:10.7932/NCEDC.
  - The double-difference reference catalogs are NCAeqDD v202112 (Waldhauser & Schaff, 2008; LDEO) and the NCEDC
    DD catalog.
- **Software.** SeisComP (GFZ / gempa), scrtdd, pyrtdd and scdlrtpicker (Swiss Seismological Service, ETH Zurich;
  scrtdd: Scarabello & Diehl, doi:10.5281/zenodo.5337361), SeisBench, NonLinLoc (A. Lomax), ObsPy.

## Reproducing

- **Install.** `bash install/00_create_conda_envs.sh --apply`, then `01_build_seiscomp.sh`, `02_build_nonlinloc.sh`, `03_install_pyrtdd.sh`,
  `04_gwangyang_inputs.sh`, `05_tests.sh` and `06_gwangyang_prep.sh`, each with `--apply`.
- **Runs.** Each folder in `runs/` has its own driver script; the notes in `docs/results/` give the exact commands.
- **Notebooks.** Rebuild with `python notebooks/build_0N_*.py` and execute with the `pyrtdd` kernel.
- **Footprint outside the project.** Two conda environments, a Jupyter kernel and caches; listed, with optional clean-up commands, in
  `docs/side_effects_outside_project.md`. `~/.seiscomp` was never created, and other environments are untouched.
