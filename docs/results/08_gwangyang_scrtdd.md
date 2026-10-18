# Step 08: scrtdd relocations of the 11 Gwangyang events (2026-10-17)

The relocations were run with **scrtdd**, the SeisComP module version of rtDD (scrtdd v2.0.10 in SeisComP
7.4.0). Everything ran offline on Server A, with no messaging and no network ports.

## Main results

- **scrtdd and pyrtdd give the same numbers.** All 11 events were relocated in every run.
  - With catalog differential times only, the scrtdd run (S0) and the pyrtdd run (R0) give the same latitude,
    longitude, depth and origin time for all 11 events, to the last digit written (8 decimals).
  - scrtdd reads the NonLinLoc grids through the SeisComP plugin `tttnll`. Its built-in grid reader gives the
    same digits (S0 = S0n). So the plugin path changes nothing.
- **With cross-correlation set up like the reference (S1), the relative locations match HypoDD 02.dt.cc
  closely.**
  - Horizontal differences: 3.1 m RMS (largest 5.7 m). Vertical differences: 4.3 m RMS (largest 9.2 m).
    Largest 3-D difference: 9.4 m.
  - The 55 inter-event distances agree with r = 0.997 (RMS difference 5.2 m).
  - 5 of the 11 events lie inside HypoDD's bootstrap 95 % error box. The other six are just outside: the
    largest ratio of a difference to its half-width is 1.47 (event 9, north).
  - One of the five inside events is event 3, whose box is wide (16 / 6 / 26 m); the other four are among the
    ten well-constrained events. The box measures only HypoDD's own precision (section 6).
  - These numbers use the same HypoDD convention as step 07 since the verification (section 3), so S1 and
    pyrtdd's R1f now read the same: 5 of 11 inside, largest ratio 1.47.
  - For scale, HypoDD's own two solutions (dt.ct and dt.cc) differ by 33 m RMS horizontally and 39 m
    vertically.
- **The band-pass filter really reaches the waveforms in scrtdd.** This is not true in stock pyrtdd: the
  pyrtdd step found that its stock filter does not reach the traces.
  - S1's cross-correlation lags equal those of pyrtdd's filtered run R1f for 2787 of 2801 phase pairs. The
    coefficients differ by at most 0.002.
  - The relocated positions differ by at most 1.8 m in absolute terms and 0.25 m in relative terms.
- **The cluster centroid is not held in place.** These runs use no absolute-location equations
  (absoluteLocationConstraint 0) and only light damping (0.01). The relative geometry is still fine.
  - The catalog-only runs moved the whole cluster about **1.7 km east** of HypoDD's centroid.
  - The cross-correlation runs moved it 0.36 km (S1) and 0.57 km (S1h).
  - The default solver (S2, absolute-location weight 0.3) put it 0.73 km deeper.
- **Real-time style (single-event) relocation works, after one workaround.**
  - `scrtdd --ep` with a file inventory crashes with a segmentation fault (an upstream bug, explained below).
    With the inventory in a small SQLite database, all 22 runs (11 events × automatic or manual picks)
    completed both steps.
  - Each event was relocated against the S1 catalog without that event. The final positions lie within
    **0.3 m (manual picks) and 1.7 m (automatic picks)** of the S1 positions (median over the events). The
    starting HYPOINVERSE locations were about 450 m away.
  - pyrtdd's single-event runs give the same result. SEa and pyrtdd's R6tf differ by a median 1.7 m (largest
    2.2 m), SEm and R6f by 1.7 m (largest 1.8 m). That is the offset between their two reference catalogs (S1
    minus R1f: median 1.7 m, mostly 1.5 m south and 0.8 m up). With that offset removed they agree to a median
    0.1 m (section 4.5).
  - The exception is event 3 (the ML 2.2): 28 m (manual) and 44 m (automatic). It is also the least
    consistent event in S1 and in HypoDD's bootstrap.
- **Two upstream scrtdd problems were found (details below).**
  - `--ep` crashes when the inventory comes from a file.
  - Single-event step 1 never uses reference event id 1, because of an id clash.

## 1. Runs

All runs are in `runs/gwangyang/scrtdd/`, one folder per run. Each folder holds:

- its own `seiscomp_user/{global.cfg,scrtdd.cfg}`, which is the folder `SEISCOMP_LOCAL_CONFIG` points to;
- its own `home/`;
- `work/`, with the outputs and the scrtdd log;
- `run_options.json`, with every option value the module used.

| run | what it is | start | cross-correlation | solver | time |
|---|---|---|---|---|---|
| S0 | catalog differential times only | centroid (HypoDD ISTART=1) | off | hypodd_like | 0.4 s |
| S0n | S0 with scrtdd's built-in NonLinLoc reader (`Native:NLLGrid`) instead of the plugin | centroid | off | hypodd_like | 0.4 s |
| S0h | S0 from the HYPOINVERSE locations | HYPOINVERSE | off | hypodd_like | 0.4 s |
| S1 | analogue of HypoDD 02.dt.cc | centroid | like_reference | hypodd_like | 22 s |
| S1h | S1 from the HYPOINVERSE locations | HYPOINVERSE | like_reference | hypodd_like | 21 s |
| S2 | rtDD defaults | centroid | xcorr_default | rtdd_default | 28 s |
| S2sc | scrtdd's own profile defaults: only the model, phase names, cross-correlation on, filter and resampling set | centroid | scrtdd defaults (≤ 60 km, events < 2 km apart) | scrtdd defaults | 14 s |
| SEa | single-event, leave-one-out, origin and picks *automatic* (11 runs) | HYPOINVERSE | like_reference | hypodd_like | 8–16 s per event |
| SEm | as SEa, origin and picks *manual* | HYPOINVERSE | like_reference | hypodd_like | 9–16 s per event |

Command of the multi-event runs (cwd = `<run>/work`; `SEISCOMP_LOCAL_CONFIG=<run>/seiscomp_user`;
`HOME=<run>/home`; `nice -n 10 /usr/bin/timeout 570`):

```
scrtdd --reloc-catalog station.csv,<event_centroid_start.csv|event.csv>,phase.csv --profile gwangyang \
       --inventory-db file://.../inputs/inventory_sc.xml -I sdsarchive://.../inputs/sds \
       --dump-diagnostics --xmlout --verbosity=3 --console=1  > relocated.xml  2> scrtdd.log
```

The single-event runs use `scrtdd --ep origin_<k>.xml --profile gwangyang -d sqlite3://.../inventory.sqlite ...`
(see section 5.1 for why).

## 2. Settings: pyrtdd name → scrtdd option → value

The scrtdd profile options are `profile.gwangyang.<option>` in `scrtdd.cfg`. The option list was read from
`descriptions/scrtdd.xml`, `doc/base/multievent.rst` and the code that reads them
(`apps/scrtdd/rtddtool.cpp:340-1028`).

- Every value is written explicitly, even where it equals the default.
- `run_options.json` lists the value of every option the module reads. Options that are not set appear with
  the module's own fallback and its source line.
- It also lists the libhdd structures as scrtdd fills them. These have the same names as in pyrtdd.
- `scrtdd --print-config-vars` lists the variables the module reads. Every one of them is covered by the dump.

### Velocity model and phases

| pyrtdd / libhdd | scrtdd | value |
|---|---|---|
| `NLLGrid(gridPath=.../nll_kim1983/time, gridModel='kim1983')` | `global.cfg`: `plugins = tttnll`, `ttt.NLLGrid.tables = kim1983`, `ttt.NLLGrid.kim1983.tablePath = .../nll_kim1983/time/kim1983`; profile `tableType = NLLGrid`, `tableModel = kim1983` | kim1983 grids |
| `NLLGrid(maxSearchDistance=0.1)` (meters) | `ttt.NLLGrid.kim1983.maxSearchDistance` (plugin default 10 m) | 0.1 |
| `Config.validPphases` / `validSphases` | `P-Phases` / `S-Phases` | `P` / `S` |
| `Config.PSTableOnly` | `PSTableOnly` | true |
| `Config.pickUncertaintyClasses` | `pickUncertaintyClasses` | 0, 0.025, 0.05, 0.1, 0.2, 0.4 (unused) |

### Clustering 'hypodd_like' (mirrors ph2dt)

| pyrtdd `ClusteringOptions` | scrtdd option | value |
|---|---|---|
| `numEllipsoids` | `doubleDifferenceSystem.eventPairSelection.multiEvent.numEllipsoids` | 0 (nearest neighbor) |
| `maxNeighbourDist` | `...multiEvent.maxNeighbourDistance` | 10 km |
| `maxNumNeigh` | `...multiEvent.maxNumNeighbours` | 0 (no limit) |
| `minNumNeigh` | `doubleDifferenceSystem.eventFiltering.minNumNeighbours` (one value for multi- **and** single-event) | 1 |
| `minNumPhases` | `doubleDifferenceSystem.eventFiltering.minNumPhases` (one value for both modes) | 1 |
| `maxNumPhases` | not configurable; scrtdd fixes it (`rtddtool.cpp:1020-1021`) | 0 (no limit) |
| `minEvStaToInterEvRatio` | `doubleDifferenceSystem.phaseFiltering.minStationToEventPairDistRatio` | 3 |
| `minEvStaDist` / `maxEvStaDist` | `...phaseFiltering.minStationDistance` / `maxStationDistance` (≤ 0 = no limit) | 0 / −1 |
| single-event block (only for `--ep`) | `...eventPairSelection.singleEvent.maxNumNeighbours` / `maxNeighbourDistance` / `numEllipsoids` | 0 / 10 km / 5 |

Notes on the single-event block:

- With `maxNumNeigh` 0, libhdd uses nearest-neighbor selection whatever `numEllipsoids` says
  (`clustering.cpp:311-314`).
- scrtdd itself fixes the step settings: step 1 uses a ratio of 1 and no cross-correlation; step 2 uses
  numEllipsoids 1 (`rtddtool.cpp:2075-2112`).

**Check of the ratio 3.** Every multi-event run built 2801 double differences, in the first and in every later
iteration. That is 1226 P + 1575 S, every event-pair/station/phase triple that ph2dt formed before its own
outlier removal. So the ratio of 3 removed nothing, from either start. This holds even for the HYPOINVERSE
start, where events are up to about 1 km apart; the closest station is 7 km away.

### Solver

| pyrtdd `SolverOptions` | scrtdd option | hypodd_like | rtdd_default |
|---|---|---|---|
| `type` | `solver.solverType` | LSMR | LSMR |
| `algoIterations` | `solver.algoIterations` | 20 | 20 |
| `absLocConstraintStart/End` | `solver.absoluteLocationConstraint` (1 value = start and end) | 0 | 0.3 |
| `dampingFactorStart/End` | `solver.dampingFactor` | 0.01 | 0.01 |
| `downWeightingByResidualStart/End` | `solver.downWeightingByResidual` | 10, 5 | 10, 5 |
| `usePickUncertainties` | `solver.usePickUncertainties` | false | false |
| `xcorrWeightScaler` | `solver.xcorrWeightScaler` | 2.0 | 2.0 |
| `L2normalization`, `solverIterations` | not configurable; scrtdd fixes them (`rtddtool.cpp:1022-1023`) | true, 0 (auto) | true, 0 |

Number of iterations: 20 outer iterations. The log shows iterations 0–19 and a final residual report labeled
"Iteration 20". Inside each, LSMR stopped after at most 22 steps (the automatic limit).

### Cross-correlation

| pyrtdd `XcorrOptions` | scrtdd option | like_reference | xcorr_default | scrtdd profile default |
|---|---|---|---|---|
| `enable` | `crossCorrelation.enable` | true | true | false |
| `minEvStaDist` | `crossCorrelation.minStationDistance` | 0 | 0 | 0 |
| `maxEvStaDist` | `crossCorrelation.maxStationDistance` | −1 (none) | −1 (= libhdd/pyrtdd default) | **60 km** |
| `maxInterEvDist` | `crossCorrelation.maxInterEventDistance` | −1 (none) | −1 (= libhdd/pyrtdd default) | **2 km** |
| `phase[P].minCoef/startOffset/endOffset/winScaling/maxDelay/components` | `crossCorrelation.p-phase.minCCCoef/winStart/winEnd/winScaling/maxDelay/components` | 0.7 / −0.5 / 0.5 / 0 / 0.5 / Z | 0.7 / −0.5 / 0.5 / 0.02 / 0.5 / Z | same as xcorr_default |
| `phase[S]...` | `crossCorrelation.s-phase....` | 0.7 / −0.5 / 0.5 / 0 / 0.5 / L2 | 0.7 / −0.5 / 1.0 / 0.04 / 0.5 / L2 | same as xcorr_default |
| `Config.wfFilter.filterStr` (`bandpass;freqmin=5;freqmax=20;corners=4`) | `crossCorrelation.waveformFiltering.filterString` | `"BW(4,5,20)"` | `"BW(4,5,20)"` | set to `"BW(4,5,20)"` in S2sc |
| `Config.wfFilter.resampleFreq` | `...waveformFiltering.resampling` | 1000 Hz | 1000 Hz | 1000 (S2sc) |
| `Config.wfFilter.extraTraceLen` | `...waveformFiltering.margin` | 1 s | 1 s | 1 s |
| `DD.enableCatalogWaveformDiskCache(dir, 10)` | `performance.cacheWaveforms / cacheDirectory / cachedWaveformLength` (module level) | on, `<run>/wfcache`, 10 s | same | default dir `$SEISCOMP_ROOT/var/lib/rtdd` |

**What filter was actually applied.** `BW(4,5,20)` is SeisComP's Butterworth band-pass of order 4
(`math/filter/butterworth.cpp:315-400`): a 4-pole low-pass prototype turned into a band-pass, which gives 8 poles
in 4 biquads, as in ObsPy `corners=4`. The corner frequencies are pre-warped and the bilinear transform is used.
It is applied once, forward (causal), starting from rest.

- SeisComP filter strings have no zero-phase option, so the reference's forward-and-backward filtering cannot
  be reproduced in scrtdd.
- The order of operations is libhdd's own (`waveform.cpp:439-458`, identical in pyrtdd):
  1. remove the mean of the window plus its 1 s margins;
  2. resample to 1000 Hz with libhdd's windowed-sinc resampler;
  3. apply the SeisComP filter, which modifies the trace in place (`hddsc/waveform.cpp:361-378`).
- The comparison in section 4.1 shows that the filter is really applied.
- The value must be quoted in the `.cfg` file. Otherwise the commas turn it into a list.

## 3. How to read the comparison numbers

All positions are converted to meters east, north and up of 35.0000 N 127.7286 E. East and north come from
ObsPy `gps2dist_azimuth`, as in the reference tables; up = −depth. HypoDD's origin times are
`origin_time_pha_datum`.

**HypoDD convention (the same as step 07 since the verification).** HypoDD positions are HypoDD's own X/Y/Z
columns of `hypoDD.reloc` (0.1 m; X east, Y north, Z down) added to the cluster centroid printed in `hypoDD.log`
("Cluster centroid at", the start point X/Y/Z refer to). The bootstrap half-widths are the unrounded values of
`bootstrap_errors.csv`. Before the verification this note used the LAT/LON/DEPTH columns (1-m depth) and
half-widths rounded to 0.1 m, while step 07 used X/Y/Z depths; the two notes then quoted different numbers for
practically identical solutions (S1 vertical 4.5 / 9.6 m here against R1f 4.3 / 9.0 m there). All tables in
section 4 are printed by `scripts/scrtdd_note_tables.py` from `comparison/`.

- **(a) relative geometry.** Each event's offset from its own solution's 11-event centroid, minus the same
  offset in HypoDD. This measures only the shape of the cluster.
- **(b) centroid shift.** Where the solution put the whole cluster, relative to HypoDD.
- **(c) bootstrap test.** How many events have |dE|, |dN| and |dU| from (a) all within HypoDD dt.cc's
  bootstrap 95 % half-widths (2–16 m E, 2–6 m N, 3–26 m U). Next to the count: the largest ratio of |difference|
  to half-width over all events and directions, and its event (a ratio just above 1 means "just outside").
- **(d) inter-event distances.** The 55 event-to-event 3-D distances: correlation r and RMS difference.
- **(e) origin times.** Solution minus HypoDD, after removing the mean difference.
- **(f) cross-correlation.** Explained in section 4.4.

## 4. Results

### 4.1 scrtdd and pyrtdd with the same settings

Source: `comparison/scrtdd_vs_pyrtdd_summary.csv` and `xcorr_scrtdd_vs_pyrtdd.csv`.

The pyrtdd step found that the stock pyrtdd waveform proxy never band-passes the traces: its runs R1 and R2 are
resampled but **unfiltered**. Its runs R1f, R2f and R3bf pre-process the traces in the proxy with the requested
filter. The option check (`comparison/options_scrtdd_vs_pyrtdd.csv`) finds no difference in any numeric option
between the paired runs, except where the filtering happens.

| scrtdd | pyrtdd | largest position difference | relative geometry (max / RMS) | largest origin-time difference |
|---|---|---|---|---|
| S0 | R0 | **0** (same digits) | 0 | 0 |
| S0n | R0 | **0** (same digits) | 0 | 0 |
| S0h | R3a | **0** (same digits) | 0 | 0 |
| S1 | R1f (filtered) | 1.8 m (mostly a common shift: N −1.5 m, U +0.8 m) | 0.25 / 0.13 m | 0.05 ms |
| S1h | R3bf (filtered) | 45.7 m (a common shift of 45 m up) | 0.45 / 0.24 m | 0.05 ms |
| S2 | R2f (filtered) | 0.8 m | 0.15 / 0.08 m | 0.04 ms |
| S1 | R1 (stock, unfiltered) | 502 m | 11.8 / 7.1 m | 3.5 ms |
| S2 | R2 (stock, unfiltered) | 331 m | 18.7 / 10.1 m | 35.5 ms |

Cross-correlation, phase pair by phase pair:

- **S1 vs R1f.** All 1226 P lags are the same. 1561 of 1575 S lags are the same. 13 S lags differ by 1–3 ms,
  with the same coefficient to 3–4 decimals: the L2 (horizontal-norm) correlation peak is flat, so a tiny
  numerical difference picks the neighboring sample. One lag differs by 78 ms: event pair 3–6 at BOSB, S,
  CC 0.70, where two peaks are about equally high. The largest coefficient difference is 0.0019. All 2801
  pairs fall on the same side of the 0.7 threshold.
- **S1 vs R1 (stock).** Only 435 of 2801 lags are the same, and the coefficients correlate with r = 0.37.
  This, together with the near-identity with R1f, shows that scrtdd's SeisComP filter is applied.
- **Why S1h vs R3bf differs by 45 m.** These differences in the lags were enough to shift the unconstrained
  centroid by 45 m. The relative geometry changed by less than 0.5 m.

### 4.2 Against HypoDD

Source: `comparison/metrics_vs_hypodd.csv` and `comparison/run_vs_run.csv`. Column formats:

- "RMS / max" columns are over the 11 events.
- (c) is out of 11 events, with the largest ratio of |difference| to half-width and its event.
- (d) is "r / RMS of the difference" over the 55 distances.

Against **HypoDD 02.dt.cc** (cross-correlation solution):

| run | (a) horizontal RMS / max (m) | (a) vertical RMS / max (m) | (a) 3-D max (m) | (b) centroid shift E, N, U (m) | (c) inside dt.cc 95 % (largest ratio, event) | (d) r / RMS (m) | (e) RMS / max (ms) |
|---|---|---|---|---|---|---|---|
| S0 | 19.0 / 35.4 | 49.3 / 104.7 | 110.5 | +1699, +151, +243 | 0/11 (14.46, ev 2) | 0.605 / 54.8 | 12.4 / 23.3 |
| S0h | 19.0 / 35.5 | 49.5 / 105.3 | 111.1 | +1622, +326, +227 | 0/11 (14.41, ev 2) | 0.603 / 55.0 | 12.4 / 23.4 |
| S1 | 3.1 / 5.7 | 4.3 / 9.2 | 9.4 | -317, +34, -171 | 5/11 (1.47, ev 9) | 0.997 / 5.2 | 3.3 / 5.7 |
| S1h | 3.1 / 5.8 | 4.4 / 9.6 | 9.7 | -396, +392, -138 | 5/11 (1.48, ev 9) | 0.997 / 5.2 | 3.3 / 5.8 |
| S2 | 4.3 / 9.4 | 4.4 / 7.6 | 11.8 | -232, +10, -733 | 2/11 (2.35, ev 9) | 0.998 / 5.2 | 3.3 / 4.8 |
| S2sc | 4.7 / 8.8 | 19.5 / 30.1 | 30.3 | -294, +75, -98 | 0/11 (6.23, ev 8) | 0.944 / 17.9 | 3.0 / 6.6 |
| pyrtdd R1f | 3.1 / 5.8 | 4.3 / 9.0 | 9.2 | -317, +35, -172 | 5/11 (1.47, ev 9) | 0.997 / 5.1 | 3.3 / 5.7 |
| pyrtdd R1 (unfiltered) | 5.7 / 8.8 | 8.2 / 17.4 | 19.5 | -214, -30, -651 | 2/11 (3.11, ev 4) | 0.984 / 10.0 | 3.3 / 5.2 |
| HYPOINVERSE start | 163.2 / 453.0 | 563.2 / 885.0 | 978.1 | +3, +2, -1 | 0/11 (194.45, ev 8) | -0.176 / 821.5 | 59.6 / 96.4 |
| HypoDD 01.dt.ct | 33.1 / 59.3 | 39.1 / 88.1 | 94.3 | -0, +23, +71 | 0/11 (21.67, ev 7) | 0.575 / 49.4 | 11.5 / 23.6 |

Against **HypoDD 01.dt.ct** (catalog-only solution); (c) against dt.cc's box, and against dt.ct's own box:

| run | (a) horizontal RMS / max (m) | (a) vertical RMS / max (m) | (a) 3-D max (m) | (b) centroid shift E, N, U (m) | (c) inside dt.cc 95 % (largest ratio, event) | (d) r / RMS (m) | (e) RMS / max (ms) |
|---|---|---|---|---|---|---|---|
| S0 | 40.2 / 73.2 | 59.9 / 127.9 | 133.2 | +1699, +128, +172 | 0/11 (23.37, ev 7); own dt.ct box 4/11 (2.21) | 0.348 / 48.4 | 8.4 / 17.3 |
| S0h | 40.2 / 73.0 | 60.1 / 128.5 | 133.8 | +1622, +303, +156 | 0/11 (23.49, ev 7); own dt.ct box 4/11 (2.22) | 0.345 / 48.7 | 8.4 / 17.4 |
| S1 | 33.2 / 58.4 | 40.8 / 95.7 | 101.6 | -317, +11, -242 | 0/11 (21.21, ev 7); own dt.ct box 4/11 (2.08) | 0.566 / 47.5 | 10.5 / 21.7 |
| S2 | 33.2 / 58.5 | 39.9 / 95.7 | 102.4 | -232, -12, -804 | 0/11 (21.26, ev 7); own dt.ct box 4/11 (2.06) | 0.577 / 46.9 | 10.1 / 21.3 |

scrtdd runs against each other (shape, metric a; `run_vs_run.csv`):

| pair | what changes | horizontal RMS / max (m) | vertical RMS / max (m) | inter-event RMS diff (m) | origin time RMS (ms) |
|---|---|---|---|---|---|
| S0n vs S0 | built-in NonLinLoc reader instead of the tttnll plugin | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 | 0.00 |
| S0h vs S0 | HYPOINVERSE start (catalog only) | 0.20 / 0.40 | 0.38 / 0.64 | 0.46 | 0.05 |
| S1h vs S1 | HYPOINVERSE start | 0.10 / 0.25 | 0.18 / 0.38 | 0.14 | 0.02 |
| S2 vs S1 | rtdd_default solver (absolute equations 0.3) + default cross-correlation windows | 2.25 / 4.20 | 3.33 / 6.08 | 3.62 | 0.81 |
| S2sc vs S1 | scrtdd profile defaults | 4.09 / 5.42 | 19.97 / 39.26 | 16.63 | 2.29 |
| S1 vs S0 | adding cross-correlation | 19.07 / 36.70 | 51.11 / 113.85 | 51.98 | 12.91 |

What this means:

- **Cross-correlation runs (S1, S1h, S2).** They reproduce HypoDD dt.cc's cluster shape to a few meters. The
  remaining differences are of the size of HypoDD's own bootstrap errors (2–6 m horizontally, 3–26 m
  vertically).
  - Six S1 events fall just outside the 95 % box, each by 0.25–1.8 m in one or two components (largest ratio
    1.18–1.47):
    - east: events 1 and 6;
    - north: events 6, 9 and 10;
    - up: events 4 and 11.
  - The pure double-difference solver (S1) and the default solver with absolute equations (S2) do **not** give
    quite the same shape. S2 differs from S1 by 2.25 m horizontally and 3.33 m vertically RMS (largest 4.2 /
    6.1 m). That is about as large as S1's difference from HypoDD (3.1 / 4.3 m) and as the bootstrap
    half-widths, and S2 has 2 of 11 events inside the box against 5 for S1. S2 also uses the default
    cross-correlation windows, so this is not a solver-only comparison.
- **Catalog-only runs (S0, S0h).** They do *not* reproduce HypoDD dt.ct well: 40 m horizontal and 60 m vertical
  RMS, inter-event distance r = 0.35.
  - But dt.ct itself is far from dt.cc (33/39 m), and its own bootstrap errors are 12–58 m horizontally and
    32–78 m vertically. Catalog times alone (0.01 s picks) do not fix the shape at the 10 m level.
  - The two programs also treat the catalog data differently:
    - HypoDD (01.dt.ct) used ph2dt's outlier-cleaned dt.ct (2729 of 2801), pick weights 1.0–0.1 and
      distance-dependent re-weighting.
    - rtDD used all 2801 differential times, the same weight for every pick, and only residual-based
      down-weighting.
- **S2sc (scrtdd out of the box).** It cross-correlates only stations within 60 km, so 1637 instead of 2801
  phase pairs. Its vertical shape is worse: 19.5 m RMS.

The centroid shifts (b) of tens to hundreds of meters, and 1.7 km for S0, are not an error of the cluster
shape:

- HypoDD's SVD solver constrains the mean shift of the cluster. In the dt.cc run the centroid stayed within 1 m
  of its start, the HYPOINVERSE centroid (final cumulative shift 0.0 m east, 0.0 m north, 1.0 m up, −6.3 ms in
  `hypoDD.log`). In the dt.ct run it did not: it moved 22.8 m north and 71.9 m up, with +148.8 ms. This matters
  when S0 is compared with dt.ct.
- rtDD's damped least squares with absoluteLocationConstraint 0 has no such constraint. The catalog-only runs
  drifted 1.7 km east over the 20 iterations.
  - In those runs the smallest per-event absolute RMS rose from 216 to 380 ms. The event RMS values include the
    17 picks that are more than 1 s off the travel-time grids, so medians are about 1 s.
- With absolute equations (S2) the cluster went 0.73 km deeper. Why is not established. One hypothesis is that
  the best absolute fit with these grids, which include the real station elevations, lies deeper than HypoDD's
  centroid. But pyrtdd's R2, with the same absolute picks and absoluteLocationConstraint 0.3 and only the
  unfiltered cross-correlation different, ended 0.42 km deeper. So the absolute depth also depends on the
  cross-correlation data and on the damping drift. The absolute residuals are also dominated by the 17 picks
  more than 1 s off and by the ~0.27 s S−P deficit. An absolute-only location of the same picks, with and
  without the 17 outliers, would test the hypothesis; it was not run.

### 4.3 S1 event by event against HypoDD dt.cc

Source: `comparison/per_event_vs_hypodd.csv`. The last column holds HypoDD dt.cc's bootstrap 95 % half-widths
(unrounded, from `bootstrap_errors.csv`).

| event | dE | dN | dU | 3-D | origin time (ms, mean removed) | inside 95 % | largest abs(d) / half-width | half-widths E/N/U |
|---|---|---|---|---|---|---|---|---|
| 1 | -2.9 | -0.9 | -0.0 | 3.1 | -3.0 | no (E) | 1.25 | 2.35 / 2.10 / 3.90 |
| 2 | -1.5 | -1.0 | -2.5 | 3.1 | 3.4 | yes | 0.67 | 3.25 / 2.15 / 3.65 |
| 3 | 1.3 | -1.4 | 9.2 | 9.4 | 5.7 | yes | 0.36 | 16.20 / 6.15 / 25.65 |
| 4 | 0.9 | -0.9 | 4.0 | 4.2 | -3.8 | no (U) | 1.22 | 2.60 / 1.70 / 3.30 |
| 5 | 1.5 | -2.1 | 0.0 | 2.6 | -3.8 | yes | 0.77 | 4.80 / 2.75 / 6.20 |
| 6 | 3.7 | -3.1 | 4.1 | 6.4 | -4.3 | no (E, N) | 1.43 | 3.50 / 2.15 / 5.45 |
| 7 | -1.2 | 1.0 | 0.6 | 1.7 | -1.3 | yes | 0.54 | 2.65 / 1.90 / 4.50 |
| 8 | -2.7 | -2.0 | -1.4 | 3.6 | 3.3 | yes | 0.84 | 3.20 / 2.45 / 4.55 |
| 9 | 0.3 | 5.7 | -2.6 | 6.3 | 0.4 | no (N) | 1.47 | 3.20 / 3.90 / 6.45 |
| 10 | 0.2 | 2.6 | -3.9 | 4.8 | 1.3 | no (N) | 1.18 | 2.35 / 2.25 / 6.85 |
| 11 | 0.5 | 2.0 | -7.5 | 7.8 | 2.0 | no (U) | 1.24 | 3.55 / 2.75 / 6.10 |

### 4.4 Cross-correlation measurements against the reference dt.cc (metric f)

Sources: `comparison/xcorr_vs_reference.csv` and `xcorr_triplets_<run>_vs_reference.csv`.

How the values are compared:

- rtDD's cross-correlation differential time for a pair is the catalog differential time minus the lag
  (libhdd `dd.cpp:897, 921`; a reversed pair flips the sign, `xcorrcache.h:129-137`).
- It is compared with the reference dt.cc value of the same event pair, station and phase.
- The catalog differential times of the two programs are identical (largest difference 0 ms).
- rtDD accepts a correlation when **|CC| ≥ 0.7**, so polarity-reversed matches count (`dd.cpp:918`). The
  reference kept only positive CC ≥ 0.7.

**How the agreement is counted.** Both programs' differential times lie on a 1-ms grid (rtDD's lags at
1000 Hz; the reference values are written to 1 ms). "Within 2 ms" therefore means |difference| ≤ 2 ms on that
grid (`|round(diff_ms)| <= 2`). Before the verification, the script compared the raw floating-point differences
with 2.0 ms; about half of the differences of exactly 2 ms (135 of 274 for S1) failed that test through rounding
noise, so every 2-ms fraction was 3-10 points too low. The 5-ms fractions moved by at most 2 points.

**CC correlation.** Pearson r between rtDD's CC and the reference CC, with rtDD's signed CC and with its absolute
value (the reference CC is always positive). The first set is over the pairs where both passed (the "both
passed" column); the second over every triplet both measured, whatever the CC. For P the signed value is pulled
down by rtDD's anti-correlated matches; S has none, so its signed and absolute values are equal.

| run | P: abs(CC) >= 0.7 (positive + negative) of measured | S: abs(CC) >= 0.7 of measured | pairs where both passed (P / S) | difference median / MAD (ms) | within 2 ms (P / S) | within 5 ms (P / S) | CC r, both passed: P signed / P abs / S | CC r, all measured: P signed / P abs / S |
|---|---|---|---|---|---|---|---|---|
| reference dt.cc | 1017 (positive only) of 1226 | 1509 of 1575 | | | | | | |
| S1 | 910 (852 + 58) of 1226 | 1480 (1480 + 0) of 1575 | 885 / 1457 | 0 / 1 | 79.0 % / 67.1 % | 81.1 % / 75.5 % | 0.16 / 0.69 / 0.58 | 0.38 / 0.76 / 0.69 |
| S2 | 894 (856 + 38) of 1226 | 1375 (1375 + 0) of 1575 | 867 / 1361 | -0 / 1 | 79.0 % / 67.7 % | 82.0 % / 79.5 % | 0.16 / 0.69 / 0.46 | 0.37 / 0.76 / 0.63 |
| S2sc | 550 (544 + 6) of 771 | 791 (791 + 0) of 866 | 534 / 785 | -0 / 1 | 84.8 % / 66.4 % | 87.1 % / 78.6 % | 0.33 / 0.78 / 0.40 | 0.42 / 0.78 / 0.55 |
| pyrtdd R1f | 910 (852 + 58) of 1226 | 1480 (1480 + 0) of 1575 | 885 / 1457 | 0 / 1 | 79.0 % / 67.1 % | 81.1 % / 75.5 % | 0.16 / 0.69 / 0.58 | 0.38 / 0.76 / 0.69 |
| pyrtdd R1 (unfiltered) | 754 (661 + 93) of 1226 | 1025 (1002 + 23) of 1575 | 665 / 1019 | -0 / 2 | 54.7 % / 53.0 % | 70.4 % / 70.0 % | 0.20 / 0.14 / 0.10 | 0.23 / 0.40 / 0.18 |

The disagreement sits mostly in values that HypoDD itself threw away. Of the 2342 pairs where both S1 and the
reference passed (`hypoDD.res` tells which ones HypoDD kept in its final iteration):

| subset (S1, both passed) | n | within 2 ms | within 5 ms | 95th percentile of the difference |
|---|---|---|---|---|
| all | 2342 | 71.6 % | 77.6 % | 214 ms |
| kept by HypoDD in its final iteration | 1432 | 90.1 % | 95.4 % | 5 ms |
| rejected by HypoDD's outlier test | 910 | 42.5 % | 49.7 % | 356 ms |
| all measured triplets (any CC) | 2801 | 64.2 % | 70.0 % | 338 ms |

Where the remaining differences come from:

- The reference searched up to about ±1 s: a ±0.5 s slide on top of a ±0.5 s lag search. 22 reference lags are
  beyond rtDD's ±0.5 s.
- The reference used the better of raw N and E for S; rtDD uses the orientation-free L2 norm.
- The reference filtered forward and backward on the whole 460 s trace.
- pyrtdd's zero-phase run R1fz (pyrtdd step) shows how much the causal-versus-zero-phase choice matters: the
  shape changes by 0.8 / 0.9 m RMS (horizontal / vertical) against R1f, and the agreement with HypoDD by about
  0.2 m horizontally (2.9 against 3.1 m RMS).

### 4.5 Single-event (real-time style) relocation, leave-one-out

Sources: `SEa/`, `SEm/`, `comparison/single_event_vs_S1.csv` and `single_event_vs_S1_summary.csv`.

How it was set up:

- For event k, the reference catalog is S1 without event k: its relocated position and its picks are removed
  (`SE*/catalogs/loo_<k>/`). So an event never pairs with itself.
- The input is one SCML origin per event, written with `seiscomp.datamodel` and `seiscomp.io.XMLArchive`. It
  holds the HYPOINVERSE location and time, one pick per `phase.csv` row with the full stream id
  (`KS.STA..HHZ`), and an arrival per pick (weight 1, time used).
- The profile is S1's, plus `catalog.eventFile/phaFile/stationFile`.
- scrtdd relocates in two steps:
  1. catalog differential times only;
  2. from the step-1 location again, with cross-correlation.
- Two modes, because rtDD cross-correlates automatic picks with a long real-time window and trusts manual picks
  like catalog picks (`dd.cpp:1572-1585`):
  - **SEa** = origin and picks *automatic*, as from scautoloc;
  - **SEm** = *manual*.

Results:

- **All 22 runs:** exit code 0, step 1 succeeded, step 2 succeeded, and the output contains one relocated
  origin (methodID RTDD).
- Step 1 found 9 reference events for events 2–11 and 10 for event 1. Step 2 found 10 for all. The 9 is a bug
  (section 5.2).
- Step 2 had 132–304 P and 216–348 S cross-correlation pairs per event. Of these, 61–86 % of P and 89–97 % of S
  reached |CC| ≥ 0.7. Manual picks pass slightly more often than automatic ones (SEa P 61–84 %, SEm P 64–86 %).

Position against the S1 multi-event position of the same event (summary):

| | from the start (HYPOINVERSE) | after step 1 (catalog dt) | after step 2, SEa (automatic) | after step 2, SEm (manual) |
|---|---|---|---|---|
| median 3-D distance (m) | 447 | 35.9 | 1.71 | 0.32 |
| horizontal / vertical RMS (m) | | 23.2 / 37.2 | 7.7 / 11.0 | 4.5 / 7.0 |
| largest (event) | 1283 (10) | 96.4 (3) | 44.0 (3) | 27.6 (3) |
| largest without event 3 | | 53.4 (5) | 2.2 (11) | 0.7 (4) |
| origin-time RMS (ms) | | 11.8 | 1.3 | 0.8 |

Event 3 (ML 2.2, the largest event) is the exception, and the data say so in three ways:

- In S1 its final double differences have the largest misfit: median 3.6 ms, against 1.4–1.9 ms for the
  others. 292 of its double differences were given zero weight, against 56–118 for the others
  (`comparison/final_dd_residuals_by_event.csv`).
- In single-event step 2 the misfit stays at a MAD of 12.5 ms.
- HypoDD's bootstrap gives it the largest errors (16 m E, 26 m U). The reference even used a special 0.05 s
  window and 1–40 Hz band for its pairs.

Its single-event position is therefore not well determined.

**Comparison with pyrtdd's single-event runs** (`comparison/single_event_scrtdd_vs_pyrtdd.csv` and
`single_event_context.csv`). The closest partners are SEa and pyrtdd's R6tf (pyrtdd's replica of scrtdd's two
steps, automatic picks, filtered), and SEm and R6f (one step with cross-correlation, filtered):

| solution | versus | what | 3-D median / max (m) | median without event 3 (m) | after removing S1 minus R1f at the same event: median / max (m) |
|---|---|---|---|---|---|
| SEa | S1 | own reference catalog | 1.71 / 44.03 (ev 3) | 1.60 |  |
| SEm | S1 | own reference catalog | 0.32 / 27.60 (ev 3) | 0.29 |  |
| R6 | pyrtdd R1 (unfiltered) | own reference catalog | 31.37 / 107.44 (ev 3) | 29.64 |  |
| R6f | pyrtdd R1f | own reference catalog | 0.28 / 27.68 (ev 3) | 0.28 |  |
| R6p | pyrtdd R1 (unfiltered) | own reference catalog | 0.67 / 33.09 (ev 3) | 0.58 |  |
| R6t | pyrtdd R1 (unfiltered) | own reference catalog | 31.37 / 107.44 (ev 3) | 29.64 |  |
| R6tf | pyrtdd R1f | own reference catalog | 1.74 / 43.53 (ev 3) | 1.62 |  |
| R6tp | pyrtdd R1 (unfiltered) | own reference catalog | 1.75 / 38.66 (ev 3) | 1.68 |  |
| S1 | pyrtdd R1f | the two reference catalogs (multi-event) | 1.70 / 1.78 (ev 10) | 1.69 |  |
| SEa | R6tf | scrtdd vs pyrtdd single event | 1.68 / 2.21 (ev 3) | 1.67 | 0.13 / 1.07 |
| SEm | R6f | scrtdd vs pyrtdd single event | 1.72 / 1.81 (ev 10) | 1.70 | 0.10 / 0.16 |

- **The two tools agree in single-event mode.** SEa and R6tf differ by a median 1.68 m (largest 2.21 m), SEm and
  R6f by 1.72 m (largest 1.81 m).
- **That difference is the offset between the two reference catalogs.** S1 (scrtdd) and R1f (pyrtdd) differ by
  a median 1.70 m, mostly a common shift (S1 is 1.5 m south of and 0.8 m above R1f; section 4.1). Each
  single-event run sits at its own catalog's position. With that offset removed event by event, SEa and R6tf
  agree to a median 0.13 m (largest 1.07 m, event 3), and SEm and R6f to 0.10 m (largest 0.16 m).
- **Each tool against its own reference catalog:** SEa 1.71 m and R6tf 1.74 m (median; event 3: 44.0 and
  43.5 m); SEm 0.32 m and R6f 0.28 m (event 3: 27.6 and 27.7 m).
- The remaining input differences (R6tf starts from the centroid, not from HYPOINVERSE, and uses scrtdd's
  single-event default neighbor selection; with 10 reference events less than 0.2 km away both select all of
  them) therefore change the result by about 0.1 m.
- **Earlier version of this comparison.** Before the verification this section said "median 10 m, largest
  17 m" and "R6tf lies a median 7.9 m from R1f". Those numbers came from pyrtdd's earlier R6f/R6tf runs, read
  at 16:42 KST; pyrtdd re-ran R6f (17:04) and R6tf (17:12) with the padded batch loading of step 07
  (section 1b there). `scrtdd_compare.py --apply` was re-run on the current files
  (`logs/08_gwangyang_scrtdd_compare_apply_2026-10-17T2140.log`); `comparison/summary.json` now lists the
  modification time of every pyrtdd input it read.

## 5. Problems found

### 5.1 `scrtdd --ep` crashes with a file inventory (upstream scrtdd v2.0.10)

`scrtdd --ep origin.xml --inventory-db file://inventory_sc.xml ...` ended with a **segmentation fault**:

- exit code −11 with `--verbosity=3`;
- exit code 139 with `--debug`;
- in both, right after `[debug] Starting process [Origin/...]`.

Evidence: `runs/gwangyang/scrtdd/evidence_ep_crash/`, with both logs, the origin file and the option dump.

Cause, from reading the source:

- With the inventory read from a file and `--ep` given, scrtdd switches the database off
  (`apps/scrtdd/rtddtool.cpp:1029-1035`).
- `RTDD::startProcess` then calls `query()->getEvent(...)` on the database query object, which no longer
  exists (`rtddtool.cpp:1586`).

**Workaround used:**

1. The inventory (`inventory_sc.xml`) was imported once, with `scdb -i`, into a private SQLite database with
   the SeisComP schema: `runs/gwangyang/scrtdd/se_inventory_db/inventory.sqlite`.
   - 1 network, 54 stations, 54 sensor locations, 255 streams; no origins, picks or events.
   - The import takes about 2 minutes on /home.
2. scrtdd got `-d sqlite3://.../inventory.sqlite` instead of `--inventory-db`.
3. The database md5 is the same before and after all 22 runs.

In a real-time setup with a database this path is not affected.

### 5.2 Single-event step 1 never uses reference event id 1 (upstream libhdd)

- The new origin is put into an empty catalog, so it gets id 1 (`catalog.cpp:389-394`;
  `SE*/ev*/work/singleevent_*/step1/single-event.csv` shows id 1).
- Neighbor selection skips any reference event whose id equals the new event's id
  (`clustering.cpp:342`).
- So reference event 1 is never a step-1 neighbor. The step-1 `pair.csv` of every run except event 1's lists all
  reference events but event 1.
- In step 2 the new event has id 12 and event 1 is used.
- Effect here: one neighbor fewer in step 1, which is the coarse step.
- Simple remedy for the real-time catalog: number the reference events from 2 upwards.

### 5.3 Other observations

- **Centroid drift** with `absoluteLocationConstraint = 0`: 1.7 km for catalog-only runs (section 4.2). Use
  relative geometry for comparisons. For an absolute position, use a solver with absolute equations, or check
  the drift.
- The 17 picks more than 1 s off the grid times (`runs/verify_inputs/v3d_outliers.log`) are not removed in these
  runs. rtDD's residual weighting handles them.
  - 69 double differences contain one of these picks. In the last iteration of S0, S1 and S2, 66 of them had
    zero weight.
  - The other 3 are the CLSA S pairs among events 2, 4 and 6. Their three picks are all 3.62 s late, so the error
    cancels in the difference (residual below 15 ms).
  - The absolute RMS values in `reloc-event.csv` still include all 17 picks.

## 6. Caveats

- **Elevations.** HypoDD placed all stations at 0 m. The NonLinLoc grids, and therefore rtDD, use the real
  elevations (45–562 m). This should shift mainly the absolute depths: for a cluster about 150 m across the
  elevation term is nearly the same for both events of a pair at the same station and should cancel in the
  double differences. This was not tested (no run used grids with the stations at 0 m).
- **The bootstrap box measures only HypoDD's own precision.** HypoDD's bootstrap (`bootstrap_errors.csv`: 1000
  resamples, started from HypoDD's own solution, same data and settings) shows how much HypoDD's solution moves
  when its data are resampled: 1.7–4.8 m horizontally and 3.3–6.9 m vertically for ten events, 16 / 6 / 26 m
  for event 3, whose reference cross-correlation used ±0.05 s and 1–40 Hz. "Inside the box" therefore means
  "as close to HypoDD as HypoDD is to itself", not "correct". One of S1's five inside events is event 3; the
  other four (2, 5, 7, 8) are among the ten well-constrained events.
- **The leave-one-out runs are not fully independent.** Each event's reference catalog is S1 without that
  event, but S1's positions of the other ten events were computed with that event included. A fully
  independent test would rebuild the catalog from a 10-event multi-event run; this was not done.
- **Weights.** HypoDD dt.cc weighted cross-correlation data about 100 times more than catalog data in its last
  sets, and cut pairs by distance. rtDD gives cross-correlation data (1 + |CC|) times the catalog weight
  (`xcorrWeightScaler` 2) and has no distance cut. These rules differ, and nothing was tuned to make them
  agree.
- **pyrtdd runs.** The pyrtdd runs and the pyrtdd single-event runs (R6\*) were made by another agent at the
  same time. The first comparison read them at 16:42 KST (`logs/08_gwangyang_scrtdd_compare_apply_2026-10-17T1642.log`),
  before pyrtdd re-ran R6f and R6tf; that made section 4.5 stale. After the verification the comparison was
  re-run on the current files (`...T2140.log`; the `...T2138.log` run is the same without the step-2 counts),
  and `comparison/summary.json` now records the modification time of each pyrtdd input. If the pyrtdd runs
  are redone, re-run `scrtdd_compare.py --apply` and `scrtdd_note_tables.py`.
- **HypoDD positions.** This note uses HypoDD's X/Y/Z (0.1 m) about the `hypoDD.log` centroid (section 3).
  The LAT/LON/DEPTH columns are given to 6 decimals of a degree (about 0.1 m) but only 1 m in depth. (c) depends
  on such choices by ±1 event for some runs (the verifier's `runs/verify_gwangyang_reloc/extra_c_sensitivity.csv`):
  pyrtdd R1 is 3/11 with LAT/LON and 2/11 with X/Y/Z; R2f is 3/11 only with half-widths rounded to 0.1 m
  (event 8's ratio is 1.008 unrounded). S1 is 5/11 under every convention. The east, north and up computed here
  agree with the reference table columns to 0.06 m after removing the means.

## 7. Templates for the real-time test

These are in `runs/gwangyang/scrtdd/templates/` and were made by `scripts/scrtdd_templates.py`.
`template_options.json` holds every value they set or leave at the default, as read back by SeisComP's
configuration reader. `--print-config-vars` parses them without error.

- `global.cfg` contains:
  - `plugins = tttnll`;
  - `ttt.NLLGrid.kim1983.*`, with maxSearchDistance 0.1 m;
  - `recordstream = sdsarchive://.../inputs/sds`;
  - commented: `combined://slink/localhost:18000?timeout=5&retries=0;sdsarchive//...` for real time.
- `scrtdd.cfg` contains profile `gwangyang`, with exactly S1's settings and these additions:
  - `catalog.eventFile/phaFile/stationFile` point to `templates/reference_catalog/`: the S1 positions of all
    11 events (standard columns), the 763 picks and the 54 stations;
  - `activeProfiles = gwangyang`;
  - `acceptedOriginAuthors = scautoloc@server-a` (loop protection);
  - `connection.primaryGroup = LOCATION`;
  - `connection.subscriptions = SERVICE_REQUEST, EVENT, LOCATION, PICK`;
  - `onlyPreferredOrigins = true` (needs scevent);
  - `performance.profileTimeAlive = -1` (keeps the catalog waveforms in memory);
  - `performance.delayTime = 10`;
  - `performance.cacheDirectory = runs/realtime/rtdd_cache` (a placeholder).

## 8. Files

- **Scripts** (`runs/gwangyang/scrtdd/scripts/`):
  - `scrtdd_common.py`: paths, the shared settings as scrtdd keys, and option resolution.
  - `scrtdd_multievent.py`: runs S0…S2sc.
  - `scrtdd_singleevent.py`: SCML origins, leave-one-out catalogs, SQLite inventory and the SEa/SEm runs.
  - `scrtdd_compare.py`: all metrics; runs in env pyrtdd.
  - `scrtdd_note_tables.py`: prints the tables of section 4 of this note from `comparison/` (env pyrtdd).
  - `scrtdd_templates.py`.
  - All of them are dry-run by default; `--apply` makes them act.
- **Logs:** `logs/08_gwangyang_scrtdd_{multievent,singleevent,compare,templates}_*.log`.
  - The compare logs of 21:38 and 21:40 are the re-runs after the independent verification
    (`docs/results/fixes_after_verification.md`); 21:40 is the current one.
  - The singleevent log of 16:27 is the crashed first attempt.
  - The one of 16:29 is the single-event-1 test after the workaround.
- **Per run:**
  - `<run>/run_options.json`: every option value used;
  - `<run>/run_summary.json` for the multi-event runs;
  - `<run>/work/{reloc-event.csv, reloc-phase.csv, reloc-station.csv, relocated.xml, scrtdd.log}`;
  - `<run>/work/multievent_*/`: `xcorr.csv`, `cluster-1-pair.csv`, initial and final double differences.
- **Single event:**
  - `SEa/`, `SEm/`;
  - `single_event_results.csv` and `.json`;
  - `origins/origin_<k>.xml` and `origins_all.xml`;
  - `catalogs/loo_<k>/`.
- **Comparison** (`runs/gwangyang/scrtdd/comparison/`):
  - `metrics_vs_hypodd.csv` and `per_event_vs_hypodd.csv`;
  - `run_vs_run.csv` (scrtdd runs against each other);
  - `scrtdd_vs_pyrtdd_summary.csv` and `scrtdd_vs_pyrtdd_per_event.csv`;
  - `xcorr_vs_reference.csv`, `xcorr_scrtdd_vs_pyrtdd.csv` and `xcorr_triplets_*.csv`;
  - `single_event_vs_S1.csv` (with the step-2 cross-correlation counts), `single_event_vs_S1_summary.csv`,
    `single_event_scrtdd_vs_pyrtdd.csv` and `single_event_context.csv` (each single-event run against its own
    reference catalog, and the cross-tool difference with the catalog offset removed);
  - `final_dd_residuals_by_event.csv`;
  - `options_by_run.csv` and `options_scrtdd_vs_pyrtdd.csv`;
  - `positions_enu.csv`;
  - `summary.json`;
  - `note08_tables.md` (the last output of `scrtdd_note_tables.py`).
