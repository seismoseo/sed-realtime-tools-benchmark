# Step 07: pyrtdd relocations of the 11 Gwangyang events (2026-10-17)

- **Scripts** (all in `runs/gwangyang/pyrtdd/`, env `pyrtdd`, dry run by default, `--apply` runs):
  - `run_pyrtdd_gwangyang.py`: the driver, one named run per setting combination;
  - `analyze_pyrtdd_gwangyang.py`: the metrics;
  - `check_proxy_filter.py`, `check_filter_reaches_libhdd.py`: checks of the filtering;
  - `diag_centroid_drift.py`: the centroid-drift diagnostic (`--metrics-only` recomputes its table without relocating);
  - `print_note_tables.py`: prints the tables of this note from the result files.
- **Logs**: `logs/07_gwangyang_pyrtdd_<date>.log` (one line per run), `logs/07_gwangyang_pyrtdd_final_console.log`
  and, for the re-analysis after the independent verification (2026-10-17, `docs/results/fixes_after_verification.md`),
  `logs/07_gwangyang_pyrtdd_analysis_after_verification_20261017.log`.
- **Each run folder** holds:
  - `options.json`: every option value, read back from the libhdd objects;
  - `run_info.json`: status, wall time, counters;
  - `console.log`: everything libhdd printed;
  - `processing/`: libhdd's own `saveProcessing` output;
  - `clusters/` and `xcorr_cache.csv`;
  - the relocated catalog `relocated-{station,event,phase}.csv`.
- All 22 runs finished. They are deterministic: a complete re-run gave identical numbers.

## Short answer

**Does pyrtdd reproduce HypoDD's relative locations within the bootstrap 95% errors?** Not completely, but close
once the waveform filter really is applied.

- **Best like-for-like run (R1f).** Cross-correlation with the 5-20 Hz band-pass actually applied.
  - The cluster shape agrees with HypoDD dt.cc to an RMS of **3.1 m horizontally and 4.3 m vertically**
    (largest 5.8 m and 9.0 m).
  - **5 of 11** events lie inside HypoDD's bootstrap 95% box. The largest ratio of a difference to its
    half-width is 1.47 (event 9, north): no event is far outside.
  - For the ten well-constrained events that box is only 1.7-4.8 m horizontally and 3.3-6.9 m vertically.
    One of the five inside events is event 3, whose box is much wider (16 / 6 / 26 m). The other four inside
    events (2, 5, 7, 8) are among the ten well-constrained ones.
  - The box measures only HypoDD's own precision: its bootstrap re-runs HypoDD from its own solution with the
    same data and settings. It does not measure accuracy (section 10).
  - The 55 inter-event distances correlate at r = 0.997 (RMS difference 5.1 m).
  - In short: the same cluster, with differences about as large as HypoDD's own error bars.
- **pyrtdd exactly as specified (R1).** The band-pass is silently not applied (section 1a): 5.7 m / 8.2 m RMS
  (largest 8.8 m / 17.4 m), 2 of 11 events inside (largest ratio 3.11), r = 0.984.
- **Catalog times only (R0) vs HypoDD dt.ct.** 40 m / 60 m RMS, 4 of 11 events inside dt.ct's much wider
  bootstrap box (12-58 m horizontal, 32-78 m vertical). For scale, HypoDD's own dt.ct and dt.cc solutions
  differ by 33 m / 39 m.
- **Absolute position is NOT reproduced.** With `absLocConstraint 0` and the default damping 0.01, the whole
  rtDD cluster slides 0.2-1.7 km during the 20 iterations.
  - HypoDD's SVD solver constrains the mean shift of the cluster. In its dt.cc run the center ended within
    1 m of its start (final cumulative shift 0.0 m east, 0.0 m north, 1.0 m up, −6.3 ms in `hypoDD.log`). In its dt.ct run
    it still moved 22.8 m north and 71.9 m up, with +148.8 ms.
  - The slide hardly changes the shape. Damping 0.1 or 1.0 keeps the center within about 5-23 m (3-D) of the
    start in the cross-correlation runs (R0: 182 m vertically at 0.1, 15 m at 1.0). The shape then differs
    from the damping-0.01 shape by 0.5-1.8 m RMS horizontally and 0.7-4.2 m RMS vertically (section 6).

**Which settings matter** (change of the cluster shape, RMS horizontal / vertical):

| what changes | effect |
|---|---|
| cross-correlation vs catalog times only | 20 / 53 m |
| homogeneous velocity instead of the kim1983 grids | 1.3-1.5 / 18-23 m (mostly depth) |
| single-event mode with the stock proxy (cross-correlation silently fails) | 22 / 37 m |
| band-pass applied vs not applied | 5.1 / 4.9 m |
| rtDD default solver and default cross-correlation windows | 4.9 / 7.8 m (stock), 2.2 / 3.3 m (filtered) |
| single-event mode with working cross-correlation | 10 of 11 events within 1.1 m (one step) or 3.0 m (scrtdd two-step) of their multi-event position; the ML 2.2 event 28-44 m |
| zero-phase vs causal band-pass | 0.8 / 0.9 m |
| removing the 17 picks that are > 1 s off | 0.1-0.2 / 0.1-0.4 m |
| start at HYPOINVERSE instead of the centroid | ≤ 0.2 / ≤ 0.4 m (shape); only the centroid drift differs |
| xcorrWeightScaler 100 instead of 2 | 0.2 / 0.2 m |
| waveform disk cache on/off; our resampler port | ≤ 0.3 m |

## 1. Two problems in pyrtdd found on the way (read this first)

### 1a. The waveform band-pass is never applied (stock pyrtdd)

- **What happens.**
  - libhdd (the C++ engine) asks the Python waveform proxy to filter each trace by calling
    `proxy.filter(trace, filterStr)`.
  - The Python side receives a **copy** of the trace, so the filtered samples never reach libhdd.
  - libhdd therefore cross-correlates traces that are demeaned and resampled to 1000 Hz (both done in C++), but
    **not band-passed**, whatever `cfg.wfFilter.filterStr` says.
- **Evidence** (`check_filter_reaches_libhdd.py`, `checks/filter_effect_test/filter_effect_test.json`).
  - The same 2-event cross-correlation was run five ways: no filter, a 5-20 Hz band-pass, a 1 Hz low-pass, a
    `filter()` that sets every sample to zero, and one that flips the sign. All five give **identical**
    coefficients and lags.
  - The decisive cases are the band-pass, the low-pass and the zeroing filter, which would each have changed or
    invalidated the result if the filtered samples reached libhdd.
  - The sign-flip case proves nothing. Flipping the sign of both traces leaves their correlation unchanged, so it
    gives the same result whether or not the filter reaches libhdd. It was kept in the test for completeness.
    (Corrected 2026-10-17 after notebook 02's cross-checks; the first version counted it as evidence.)
  - Independent confirmation: scrtdd's SeisComP loader does filter, and its cross-correlation matches pyrtdd only
    when the band-pass is applied inside our own proxy (run R1f; 2787 of 2801 lags identical).
  - A recording proxy confirmed that libhdd does call `filter()`, with the exact string and after resampling to
    1000 Hz (`checks/proxy_filter_check.json`). In the real runs libhdd made 1165 such calls per run (`run_info.json`).
- **Cause** (our reading of the code).
  - `package/src/pyrtdd/hdd/proxy_ext.cpp` forwards `Trace &trace` with `PYBIND11_OVERRIDE_PURE`.
  - pybind11 converts lvalue-reference arguments of Python overrides with a copy policy.
  - A fix would pass the trace by reference (`py::cast(&trace, py::return_value_policy::reference)`) or return
    the filtered data. **Nothing in pyrtdd was patched.**
- **Does `zerophase=1` work?**
  - At the proxy level, yes. The proxy turns every value into a float, `1.0` counts as true, and the result is
    identical to obspy's `zerophase=True` (relative difference 0).
  - `zerophase=0` gives the causal filter.
  - `zerophase=True` fails: `ValueError: could not convert string to float: 'True'`.
  - With stock pyrtdd none of this matters, because no filter reaches libhdd.
- **What we did.** Every cross-correlation run exists twice:
  - **stock runs** (names without `f`): exactly the requested settings, with the stock `ObspyClientProxy` and the
    raw-waveform disk cache on. The filter string is set but has no effect.
  - **filtered runs** (names with `f`): a subclass of the same proxy, defined in the driver
    (`PreprocessingSDSProxy`), does inside `loadTrace()` what libhdd would do if the filter worked:
    1. demean;
    2. resample with libhdd's own sinc resampler (an exact numpy port of `waveform.cpp resample()`);
    3. apply the same obspy `Trace.filter()` call as the stock proxy.

    libhdd's own resampling and filtering are switched off for these runs. There is no disk cache, because the
    proxy must see exactly the window libhdd would process.
  - **Check of the port** (runs V0 and V1, both unfiltered):
    - All 1226 P cross-correlations are identical: coefficients to the 6 printed decimals, lags to the sample.
    - For S, 7 of 1575 lags differ by more than 1 ms, and the largest coefficient difference is 3e-4. The cause:
      libhdd demeans the already-processed horizontals once more, and the S trace is the non-linear
      L2 = sqrt(N² + E²). No coefficient crosses 0.7.
    - The locations differ by ≤ 0.3 m (section 5).
- **Answered in step 08.** scrtdd's SeisComP filter `BW(4,5,20)` behaves like the causal ObsPy
  `bandpass(corners=4)` of the filtered runs. scrtdd's run S1 and the filtered pyrtdd run R1f give the same lag
  for 2787 of 2801 phase pairs (all 1226 P and 1561 of 1575 S; `runs/gwangyang/scrtdd/comparison/xcorr_scrtdd_vs_pyrtdd.csv`).

### 1b. Single-event (real-time) mode cannot cross-correlate with the stock proxy

- **What happens.**
  - In single-event mode, the waveforms of the event being relocated are loaded in one batch.
  - libhdd's `BatchLoader::get` accepts a batch trace only if it **contains** the requested time window.
  - obspy trims to the nearest sample, and the KMA samples sit a few milliseconds off the request grid (for
    example at x.xx3096 s). So every returned trace misses the window by a fraction of a sample at its start or
    end.
  - libhdd then skips the cross-correlation ("no waveform data for phase", seen at debug level).
  - Multi-event mode is not affected: its loaders cut an inner window.
- **Effect.**
  - The proxy returned all 1165 batch traces, but libhdd rejected them.
  - R6 and R6t measured cross-correlations for only 8 of 5602 event-pair/station/phase combinations, all of them
    for event 8.
  - In the final systems only 1 (R6) and 2 (R6t) cross-correlation differential times carried weight. The
    "cross-correlation" single-event runs are therefore effectively catalog-only.
- **What we did.**
  - The padded runs fetch every batch request 0.05 s wider on both sides (one `get_waveforms` call per
    request), and libhdd cuts it back. All 5602 combinations were then measured (R6p, R6f).
  - R6p and R6tp: otherwise stock (unfiltered, like R1).
  - R6f and R6tf: the filtering proxy (like R1f).
- **For scrtdd (answered in step 08).**
  - The containment test is in libhdd, which scrtdd shares.
  - SeisComP's record stream does return traces that pass it. In scrtdd's single-event runs with automatic
    picks (SEa), 286-577 of the 348-650 step-2 double differences per event came from cross-correlation
    (event 1: 399 of 478). With manual picks (SEm) the counts equal R6f's for 10 of 11 events (event 1:
    406 of 478; `runs/gwangyang/scrtdd/comparison/single_event_vs_S1.csv`, columns `step2_dd_*`).

### 1c. rtDD also uses negative correlations (design, not a bug)

- **What rtDD does.** It keeps the lag with the largest |CC| and accepts |CC| ≥ minCoef. A strongly
  anti-correlated window therefore counts as a good measurement.
- **What the reference did.** It accepted only CC ≥ +0.7.
- **Effect here.**
  - R1f has 58 P-wave measurements with CC ≤ −0.7.
  - 54 of them are in the reference dt.cc file with a positive CC (median 0.92).
  - Their differential times differ from the reference by tens of ms (MAD 53 ms; none within 5 ms).
  - So these are probably cycle skips, i.e. the wrong peak.
  - rtDD's residual down-weighting removes most of them later.

## 2. The runs

| run | what it is |
|---|---|
| R0 | catalog times only; clustering + solver 'hypodd_like'; start at HypoDD's ISTART=1 centroid (analogue of 01.dt.ct) |
| R1 / R1f | R0 + cross-correlation 'like_reference' (analogue of 02.dt.cc); stock / filtered |
| R1fz | R1f with a zero-phase band-pass (the reference's filter) |
| R1fw | R1f with xcorrWeightScaler 100 (exploratory: HypoDD weights cc data ~100x the catalog data) |
| R2 / R2f | rtDD default solver (absLocConstraint 0.3) + default XcorrOptions, same filter, 'hypodd_like' clustering |
| R3a / R3b / R3bf | R0 / R1 / R1f started from the HYPOINVERSE locations (event.csv) |
| R4 / R4f | R1 / R1f without the 17 picks that are > 1 s off the grid times |
| R5 / R5f | R1 / R1f with Homogeneous(5.98, 3.4566) instead of the grids |
| R6 / R6p / R6f | single-event leave-one-out, one `relocateSingleEvent` call each, isManual true; background = R1 (R6, R6p) or R1f (R6f) without the event |
| R6t / R6tp / R6tf | the same, but with scrtdd's own two-step procedure (`rtddtool.cpp`) for an automatic origin (isManual false) |
| V0 / V1 | checks: R1 without the disk cache; the preprocessing proxy with the filter off (must equal V0) |

The 17 picks dropped in R4 are listed in `R4_.../inputs/dropped_picks.csv` (event:station:phase):

- 1:YGJA:P, 1:YGJA:S, 1:CGPA:S
- 2:JASA:P, 2:CLSA:S, 2:CHRB:S
- 4:CLSA:S, 4:YOA:S
- 5:YALB:P
- 6:CGWB:S, 6:CLSA:P, 6:CLSA:S
- 8:SACA:P, 8:JASA:P, 8:CGWB:P
- 10:JASA:P
- 11:KKDA:P

These are the same as `runs/verify_inputs/v3d_outliers.log`; the driver checks this. 746 picks remain.

## 3. Settings

Shared settings (the same numbers are meant for the scrtdd runs; the full read-back is in each `options.json`):

| group | setting | value |
|---|---|---|
| travel times | NonLinLoc kim1983 2-D grids | `inputs/nll_kim1983/time`, model `kim1983`, maxSearchDistance 0.1 m (stations at their elevation; HypoDD used 0 m) |
| phases | validPphases / validSphases | ['P'] / ['S']; PSTableOnly true |
| clustering 'hypodd_like' | numEllipsoids, maxNeighbourDist, minNumNeigh, maxNumNeigh, minNumPhases, maxNumPhases, minEvStaToInterEvRatio, minEvStaDist, maxEvStaDist | 0, 10 km, 1, 0 (no limit), 1, 0, 3, 0, -1 |
| solver 'hypodd_like' | type, absLocConstraint start/end, damping start/end, downWeightingByResidual start/end, usePickUncertainties, xcorrWeightScaler, algoIterations, solverIterations, L2normalization | LSMR, 0/0, 0.01/0.01, 10/5, false, 2.0 (default), 20 (default), 0 = automatic (default), true (default) |
| solver 'rtdd_default' | the same | LSMR, 0.3/0.3, 0.01/0.01, 10/5, false, 2.0, 20, 0, true |
| xcorr 'like_reference' | P and S: minCoef, startOffset, endOffset, winScaling, maxDelay; components | 0.7, -0.5 s, +0.5 s, 0, 0.5 s; P ['Z'], S ['L2']; no station or inter-event distance limits |
| xcorr 'xcorr_default' | XcorrOptions() defaults | P 0.7, -0.5, +0.5, 0.02, 0.5, ['Z']; S 0.7, -0.5, +1.0, 0.04, 0.5, ['L2'] |
| waveforms | cfg.wfFilter | `bandpass;freqmin=5;freqmax=20;corners=4` (R1fz: `...;zerophase=1`), resampleFreq 1000 Hz, extraTraceLen 1 s (default) |
| waveforms | source | obspy SDS client on `inputs/sds`, inventory `inputs/stations_rtdd.xml`, guess_zne false |
| waveforms | disk cache (stock runs) | `runs/gwangyang/pyrtdd/wfcache` (raw traces), diskTraceMinLen 10 s |
| start | main runs / R3 | `event_centroid_start.csv` (HypoDD's ISTART=1 centroid) / `event.csv` (HYPOINVERSE) |
| single event (R6) | clustering | scrtdd.xml single-event defaults: numEllipsoids 5, maxNeighbourDist 5 km, minNumNeigh 4, maxNumNeigh 80, minNumPhases 8, ratio 3. libhdd's `ClusteringOptions()` differs only in minNumNeigh 8 and maxNumNeigh 40; every event found all 10 neighbors, so neither binds. Two-step runs: step 1 without cross-correlation and ratio 1, step 2 with numEllipsoids 1 (as in `rtddtool.cpp`) |

**Checks of the settings.**

- **Clustering removed nothing.** Every multi-event run built exactly as many double differences as the picks
  allow: 2801 (1226 P + 1575 S, the same pairs ph2dt formed); R4: 2735. This includes R3a/R3b, which start from
  the spread-out HYPOINVERSE locations, so `minEvStaToInterEvRatio 3` removed nothing there either.
- **Iterations.** rtDD runs 20 solver iterations by default, plus a last pass that only computes residuals.
  LSMR chooses its own number of inner iterations (for example, 12 in R1's first solve).
- **scrtdd defaults that differ from libhdd's** (set them explicitly in scrtdd):

  | setting | scrtdd.xml | libhdd |
  |---|---|---|
  | crossCorrelation.maxStationDistance | 60 km | none |
  | crossCorrelation.maxInterEventDistance | 2 km | none |
  | eventFiltering.minNumNeighbours | 4 | 8 |
  | multiEvent.numEllipsoids | 0 | 5 |
  | singleEvent.maxNumNeighbours | 80 | 40 |

**What rtDD cannot copy from HypoDD.**

- **Weights.**
  - HypoDD's last iteration sets weight cross-correlation data 100 times (P) and 160 times (S) more than catalog
    data. They also cut residuals at 2 x spread and inter-event distance at 0.5 km.
  - rtDD keeps one observation per pair, station and phase. When the cross-correlation passes, its time replaces
    the catalog time with weight 1 + |CC|; otherwise the catalog time stays with weight 1. Everything is then
    down-weighted by residual (biweight, 10 → 5 x MAD).
  - In practice the down-weighting removes most catalog times anyway: in R1f only 84 of 411 catalog-only
    observations keep a weight. This is why R1fw (scaler 100) changes almost nothing.
- **Centroid.** HypoDD's SVD solver constrains the mean shift of the cluster. That held in the dt.cc run (final
  cumulative centroid shift 0.0 m east, 0.0 m north, 1.0 m up, −6.3 ms), but not fully in the dt.ct run: there the center
  moved 22.8 m north and 71.9 m up, +148.8 ms, during the later iterations (`hypoDD.log`, "mean centroid
  (origin) shift"). This matters when R0 is compared with dt.ct. rtDD with `absLocConstraint 0` relies only on
  the damping (section 6).
- **Cross-correlation measurement.**
  - The reference took the better of raw N and E and accepted only positive CC. It slid a ±0.5 s window on top of
    a ±0.5 s lag search, on traces filtered over their whole length. For pairs with the ML 2.2 event (id 3) it
    used ±0.05 s and 1-40 Hz.
  - rtDD uses L2 for S, |CC| ≥ 0.7, a ±0.5 s lag, and the better of the two window directions.

## 4. Results against HypoDD

**What the numbers mean.**

- (a) **Shape difference.** For each event, its position relative to its own cluster's center, minus the same for
  HypoDD. RMS and largest value over the 11 events, horizontal (H) and vertical (V).
- (b) **Centroid shift.** How far the whole cluster has moved: east / north / up.
- (c) **Inside the bootstrap box.** The event's (a) difference is smaller than HypoDD's own 95% bootstrap
  half-widths in all three directions. Next to the count: the largest ratio of |difference| to half-width over
  all events and directions, and its event. A ratio just above 1 means "just outside".
- (d) **Inter-event distances.** The 55 event-to-event distances: Pearson r and RMS difference. r near 1 means
  the same shape and size.
- (e) **Origin times.** Differences after removing the mean offset. HypoDD gives origin times to 0.01 s, so about
  3 ms RMS is pure rounding.

**Convention (the same in step 08 since the verification).** Local east/north/up are taken about 35.0000 N
127.7286 E. HypoDD positions are HypoDD's own X/Y/Z columns of `hypoDD.reloc` (0.1 m; X east, Y north, Z down)
added to the cluster centroid printed in `hypoDD.log` ("Cluster centroid at", the start point X/Y/Z refer to).
The bootstrap half-widths are the unrounded values of `bootstrap_errors.csv`. Before the verification, this
note used the LAT/LON columns for east/north and half-widths rounded to 0.1 m, and step 08 used the 1-m DEPTH
column; the two notes then quoted different counts for nearly identical solutions (for example R2f 3/11 here
against S2 2/11 there). With one convention, (c) changed for R1 (3 → 2), R2f (3 → 2), R3b (3 → 2) and R4
(4 → 3); horizontal (a) changed by up to 0.35 m. All tables below are printed by `print_note_tables.py` from the
result files.

### Against HypoDD 02.dt.cc (bootstrap half-widths 1.7-4.8 m horizontal, 3.3-6.9 m vertical; event 3: 16.2 / 6.2 / 25.7 m)

| run | shape RMS H / V (m) | shape max H / V (m) | centroid shift E / N / U (m) | inside box (largest ratio, event) | inter-event r / RMS diff (m) | origin time RMS / max (ms) |
|---|---|---|---|---|---|---|
| HypoDD dt.ct (for scale) | 33.1 / 39.1 | 59.3 / 88.1 | -0 / 23 / 71 | 0/11 (21.67, ev 7) | 0.575 / 49.4 | 11.5 / 23.6 |
| HYPOINVERSE (for scale) | 163.2 / 563.2 | 453.0 / 885.0 | 3 / 2 / -1 | 0/11 (194.45, ev 8) | -0.176 / 821.5 | 59.6 / 96.4 |
| R0 | 19.0 / 49.3 | 35.4 / 104.7 | 1699 / 151 / 243 | 0/11 (14.46, ev 2) | 0.605 / 54.8 | 12.4 / 23.3 |
| R1 | 5.7 / 8.2 | 8.8 / 17.4 | -214 / -30 / -651 | 2/11 (3.11, ev 4) | 0.984 / 10.0 | 3.3 / 5.2 |
| R1f | 3.1 / 4.3 | 5.8 / 9.0 | -317 / 35 / -172 | 5/11 (1.47, ev 9) | 0.997 / 5.1 | 3.3 / 5.7 |
| R1fz | 2.9 / 4.2 | 5.0 / 7.4 | -328 / -2 / -170 | 5/11 (1.38, ev 4) | 0.998 / 4.8 | 3.2 / 5.6 |
| R1fw | 3.1 / 4.2 | 5.7 / 8.6 | -313 / 24 / -162 | 5/11 (1.45, ev 9) | 0.997 / 5.0 | 3.3 / 5.8 |
| R2 | 8.3 / 8.8 | 17.5 / 16.4 | -164 / 16 / -420 | 1/11 (3.46, ev 10) | 0.973 / 12.0 | 3.6 / 6.0 |
| R2f | 4.3 / 4.4 | 9.5 / 7.5 | -232 / 10 / -732 | 2/11 (2.37, ev 9) | 0.998 / 5.3 | 3.3 / 4.8 |
| R3a | 19.0 / 49.5 | 35.5 / 105.3 | 1622 / 326 / 227 | 0/11 (14.41, ev 2) | 0.603 / 55.0 | 12.4 / 23.4 |
| R3b | 5.7 / 8.2 | 8.8 / 17.4 | -223 / -25 / -651 | 2/11 (3.11, ev 4) | 0.984 / 10.0 | 3.3 / 5.2 |
| R3bf | 3.1 / 4.3 | 5.7 / 9.2 | -392 / 396 / -183 | 5/11 (1.46, ev 9) | 0.997 / 5.1 | 3.3 / 5.7 |
| R4 | 5.6 / 8.0 | 8.6 / 16.3 | -200 / -50 / -649 | 3/11 (3.08, ev 4) | 0.985 / 9.6 | 3.3 / 5.2 |
| R4f | 3.1 / 4.3 | 5.7 / 9.3 | -319 / 32 / -168 | 5/11 (1.45, ev 9) | 0.997 / 5.2 | 3.3 / 5.7 |
| R5 | 5.8 / 24.7 | 10.7 / 44.2 | 17 / 37 / 238 | 0/11 (9.24, ev 4) | 0.915 / 26.1 | 2.8 / 6.1 |
| R5f | 3.5 / 26.2 | 7.0 / 45.6 | -37 / 55 / -69 | 0/11 (7.07, ev 9) | 0.886 / 30.2 | 4.0 / 9.3 |
| R6 | 21.9 / 33.5 | 48.0 / 81.1 | -223 / -33 / -647 | 0/11 (12.79, ev 1) | 0.752 / 40.3 | 10.2 / 20.9 |
| R6t | 22.0 / 33.4 | 47.9 / 80.7 | -223 / -33 / -647 | 0/11 (12.87, ev 1) | 0.756 / 40.2 | 10.2 / 20.9 |
| R6p | 7.9 / 10.9 | 19.7 / 28.4 | -214 / -27 / -650 | 0/11 (3.18, ev 3) | 0.959 / 14.9 | 3.2 / 5.1 |
| R6tp | 8.9 / 11.7 | 23.8 / 31.6 | -214 / -26 / -650 | 0/11 (3.84, ev 3) | 0.946 / 16.5 | 3.2 / 5.0 |
| R6f | 5.0 / 4.9 | 12.4 / 12.2 | -318 / 36 / -174 | 7/11 (1.68, ev 4) | 0.995 / 6.4 | 3.0 / 4.1 |
| R6tf | 7.3 / 8.1 | 20.7 / 24.4 | -319 / 36 / -175 | 7/11 (1.77, ev 6) | 0.986 / 9.6 | 2.9 / 4.0 |
| V0 | 5.8 / 8.4 | 9.4 / 18.1 | -230 / -47 / -650 | 3/11 (3.06, ev 4) | 0.983 / 10.2 | 3.3 / 5.2 |
| V1 | 5.8 / 8.4 | 9.5 / 18.1 | -220 / -47 / -650 | 3/11 (3.10, ev 4) | 0.983 / 10.3 | 3.3 / 5.2 |

Per event, R1f against dt.cc (difference of the position within the cluster; bootstrap half-widths, unrounded):

| event | dE / dN / dU (m) | bootstrap E / N / U (m) | inside | largest abs(d) / half-width |
|---|---|---|---|---|
| 1 | -2.9 / -0.9 / -0.1 | 2.35 / 2.10 / 3.90 | no (E) | 1.23 |
| 2 | -1.6 / -0.9 / -2.3 | 3.25 / 2.15 / 3.65 | yes | 0.64 |
| 3 | +1.1 / -1.5 / +9.0 | 16.20 / 6.15 / 25.65 | yes | 0.35 |
| 4 | +0.8 / -1.0 / +4.1 | 2.60 / 1.70 / 3.30 | no (U) | 1.24 |
| 5 | +1.5 / -2.2 / -0.1 | 4.80 / 2.75 / 6.20 | yes | 0.79 |
| 6 | +3.8 / -3.0 / +4.1 | 3.50 / 2.15 / 5.45 | no (E, N) | 1.41 |
| 7 | -1.2 / +1.0 / +0.6 | 2.65 / 1.90 / 4.50 | yes | 0.55 |
| 8 | -2.7 / -2.0 / -1.3 | 3.20 / 2.45 / 4.55 | yes | 0.83 |
| 9 | +0.2 / +5.7 / -2.5 | 3.20 / 3.90 / 6.45 | no (N) | 1.47 |
| 10 | +0.4 / +2.7 / -3.9 | 2.35 / 2.25 / 6.85 | no (N) | 1.22 |
| 11 | +0.5 / +1.9 / -7.5 | 3.55 / 2.75 / 6.10 | no (U) | 1.23 |

The same table for R1 is in `per_event_vs_reference.csv`. Its largest differences are event 3 (dU +17.4 m,
dN −7.5 m), event 9 (dU −10.6 m), event 4 (dU +10.3 m) and event 11 (dU −9.8 m).

### Against HypoDD 01.dt.ct (bootstrap half-widths 12-58 m horizontal, 32-78 m vertical)

| run | shape RMS H / V (m) | shape max H / V (m) | centroid shift E / N / U (m) | inside box (largest ratio, event) | inter-event r / RMS diff (m) | origin time RMS / max (ms) |
|---|---|---|---|---|---|---|
| R0 | 40.2 / 59.9 | 73.2 / 127.9 | 1699 / 128 / 172 | 4/11 (2.21, ev 3) | 0.348 / 48.4 | 8.4 / 17.3 |
| R3a | 40.2 / 60.1 | 73.0 / 128.5 | 1622 / 303 / 156 | 4/11 (2.22, ev 3) | 0.345 / 48.7 | 8.4 / 17.4 |
| R1 | 34.0 / 41.8 | 64.6 / 97.9 | -214 / -53 / -722 | 3/11 (1.84, ev 11) | 0.543 / 46.0 | 9.8 / 20.5 |
| R1f | 33.2 / 40.8 | 58.4 / 95.7 | -317 / 13 / -243 | 4/11 (2.08, ev 3) | 0.566 / 47.6 | 10.5 / 21.7 |
| R2f | 33.2 / 39.9 | 58.5 / 95.7 | -232 / -12 / -803 | 4/11 (2.06, ev 3) | 0.577 / 46.9 | 10.1 / 21.3 |
| R5f | 33.0 / 49.3 | 58.8 / 122.2 | -37 / 32 / -140 | 4/11 (2.29, ev 11) | 0.484 / 41.4 | 11.5 / 24.5 |
| R6 | 43.4 / 54.2 | 73.8 / 108.6 | -223 / -56 / -717 | 4/11 (2.39, ev 3) | 0.344 / 46.9 | 7.8 / 14.9 |

All other runs are in `summary_metrics.csv`. Every cross-correlation run except the stock single-event runs
R6/R6t is 33-38 m (horizontal) and 40-50 m (vertical) from dt.ct.

- **Catalog only.** rtDD's catalog-only solution (R0) is about as far from HypoDD dt.ct (40 / 60 m) as HypoDD's
  dt.ct is from its own dt.cc (33 / 39 m). It is within dt.ct's large bootstrap box for 4 of 11 events.
- **Why R0 differs from dt.ct.** ph2dt removed 72 differential times as outliers, and HypoDD used distance and
  residual cutoffs; rtDD kept everything and down-weighted by residual. R0 is in fact closer to dt.cc than to
  dt.ct horizontally (19 m against 40 m).
- **Absolute frames differ.** dt.ct's own center moved 22.8 m north and 71.9 m up from its start (section 3),
  so the centroid shifts (b) against dt.ct and against dt.cc differ by that amount.

## 5. Run against run

| pair | what changes | shape RMS H / V (m) | shape max H / V (m) | centroid shift E / N / U (m) | inter-event RMS diff (m) | origin time RMS (ms) |
|---|---|---|---|---|---|---|
| R3a vs R0 | start position (catalog only) | 0.2 / 0.4 | 0.4 / 0.6 | -77 / 175 / -15 | 0.5 | 0.0 |
| R3b vs R1 | start position | 0.0 / 0.0 | 0.0 / 0.1 | -8 / 5 / 1 | 0.0 | 0.0 |
| R3bf vs R1f | start position (filtered) | 0.1 / 0.2 | 0.2 / 0.4 | -76 / 360 / -10 | 0.1 | 0.0 |
| R4 vs R1 | 17 outlier picks removed | 0.2 / 0.4 | 0.4 / 1.1 | 15 / -20 / 2 | 0.5 | 0.1 |
| R4f vs R1f | 17 outlier picks removed (filtered) | 0.1 / 0.1 | 0.2 / 0.3 | -3 / -4 / 5 | 0.1 | 0.0 |
| R5 vs R1 | homogeneous velocity | 1.5 / 18.4 | 2.8 / 33.6 | 231 / 67 / 890 | 19.5 | 2.4 |
| R5f vs R1f | homogeneous velocity (filtered) | 1.3 / 22.8 | 2.6 / 43.0 | 279 / 20 / 103 | 26.5 | 2.3 |
| R1f vs R1 | band-pass applied vs not | 5.1 / 4.9 | 8.3 / 8.3 | -102 / 65 / 479 | 7.2 | 1.5 |
| R1fz vs R1f | zero-phase vs causal | 0.8 / 0.9 | 1.3 / 1.6 | -12 / -38 / 2 | 1.2 | 0.1 |
| R1fw vs R1f | xcorrWeightScaler 100 vs 2 | 0.2 / 0.2 | 0.6 / 0.4 | 4 / -12 / 10 | 0.3 | 0.0 |
| R2 vs R1 | rtDD default solver + xcorr windows | 4.9 / 7.8 | 12.3 / 17.1 | 50 / 46 / 231 | 7.4 | 1.8 |
| R2f vs R1f | the same, filtered | 2.2 / 3.3 | 4.2 / 5.9 | 84 / -25 / -560 | 3.6 | 0.8 |
| R1 vs R0 | adding cross-correlation | 19.7 / 52.6 | 35.0 / 122.0 | -1913 / -181 / -894 | 50.2 | 11.7 |
| V0 vs R1 | disk cache off vs on | 0.3 / 0.3 | 0.9 / 0.7 | -15 / -17 / 1 | 0.4 | 0.0 |
| V1 vs V0 | numpy resampler port vs libhdd (check) | 0.1 / 0.2 | 0.3 / 0.3 | 10 / -0 / 0 | 0.1 | 0.0 |

The single-event pairs are in section 7.

- **Centroid shifts in this table** are mostly the drift of section 6, not a real effect of the setting.
- **The homogeneous model** also lowers the shape agreement with HypoDD to r = 0.89-0.92 (section 4). A
  straight-ray model gives wrong take-off angles for the stations beyond ~50 km, where the kim1983 rays are
  head waves, and this changes depths.

## 6. The cluster center slides (diagnostic `diag_centroid_drift.py`)

The base run is re-run with the same inputs and the same cross-correlation results (read back from its
`xcorr_cache.csv`). Only the number of iterations or the damping changes. The last column compares each
variant's shape with its base run's final shape (20 iterations, damping 0.01), with the same metric (a) as
against HypoDD. The table was recomputed from the relocated catalogs on disk with `diag_centroid_drift.py
--apply --metrics-only` (shared HypoDD convention; no relocation was repeated):

| base | iterations | damping | center minus start E / N / U (m) | shape RMS vs dt.cc H / V (m) | inside box (largest ratio) | shape vs base run RMS H / V (max) (m) |
|---|---|---|---|---|---|---|
| R0 | 1 | 0.01 | -5 / -1 / 13 | 33.0 / 92.4 | 0/11 (33.02) | 24.4 / 60.8 (max 41.2 / 119.1) |
| R0 | 2 | 0.01 | -7 / 4 / 83 | 25.0 / 73.6 | 0/11 (23.28) | 14.0 / 37.6 (max 22.0 / 76.0) |
| R0 | 3 | 0.01 | 22 / 119 / 165 | 22.2 / 64.2 | 0/11 (19.78) | 9.7 / 26.5 (max 17.5 / 54.6) |
| R0 | 5 | 0.01 | 254 / 526 / 194 | 20.8 / 58.6 | 0/11 (18.83) | 6.6 / 18.5 (max 12.6 / 29.1) |
| R0 | 10 | 0.01 | 1039 / 390 / 209 | 19.5 / 53.2 | 0/11 (15.89) | 2.7 / 7.6 (max 4.7 / 14.0) |
| R0 | 20 | 0.01 | 1699 / 151 / 244 | 19.0 / 49.3 | 0/11 (14.46) | 0.0 / 0.0 (max 0.0 / 0.0) |
| R0 | 40 | 0.01 | 1747 / 422 / 203 | 19.0 / 47.3 | 0/11 (13.40) | 1.4 / 4.3 (max 3.0 / 7.9) |
| R1 | 1 | 0.01 | 4 / 1 / 4 | 36.8 / 61.6 | 0/11 (34.91) | 35.4 / 62.0 (max 73.0 / 156.1) |
| R1 | 2 | 0.01 | 2 / 7 / 26 | 13.0 / 12.7 | 0/11 (7.60) | 11.3 / 13.9 (max 23.5 / 26.3) |
| R1 | 3 | 0.01 | -3 / 6 / 7 | 7.1 / 7.8 | 1/11 (3.91) | 5.1 / 4.9 (max 14.2 / 10.8) |
| R1 | 5 | 0.01 | -25 / 5 / -42 | 5.6 / 9.0 | 2/11 (3.06) | 1.5 / 2.7 (max 2.7 / 4.8) |
| R1 | 10 | 0.01 | -50 / -10 / -255 | 6.1 / 8.9 | 1/11 (2.82) | 1.3 / 2.4 (max 2.7 / 4.1) |
| R1 | 20 | 0.01 | -209 / -24 / -652 | 5.7 / 8.2 | 2/11 (3.10) | 0.0 / 0.0 (max 0.0 / 0.1) |
| R1 | 40 | 0.01 | -384 / 43 / -647 | 5.7 / 8.1 | 2/11 (3.08) | 0.2 / 0.2 (max 0.4 / 0.4) |
| R1f | 1 | 0.01 | -2 / 0 / -0 | 9.9 / 12.7 | 0/11 (5.12) | 10.3 / 14.0 (max 20.1 / 24.7) |
| R1f | 2 | 0.01 | -10 / -1 / -76 | 3.5 / 4.5 | 4/11 (1.61) | 2.4 / 2.6 (max 6.7 / 5.6) |
| R1f | 3 | 0.01 | -16 / -5 / -165 | 3.0 / 4.1 | 5/11 (1.60) | 1.0 / 1.7 (max 2.9 / 4.3) |
| R1f | 5 | 0.01 | -50 / 4 / -187 | 3.1 / 4.2 | 5/11 (1.49) | 0.2 / 0.7 (max 0.3 / 1.6) |
| R1f | 10 | 0.01 | -143 / 13 / -207 | 3.1 / 4.3 | 5/11 (1.49) | 0.1 / 0.3 (max 0.1 / 0.5) |
| R1f | 20 | 0.01 | -316 / 35 / -171 | 3.1 / 4.3 | 5/11 (1.47) | 0.0 / 0.0 (max 0.0 / 0.0) |
| R1f | 40 | 0.01 | -633 / 119 / -159 | 3.1 / 4.3 | 5/11 (1.45) | 0.1 / 0.4 (max 0.4 / 0.7) |
| R0 | 20 | 0.1 | 27 / 61 / 182 | 19.0 / 47.7 | 0/11 (14.15) | 2.7 / 7.0 (max 4.3 / 13.8) |
| R0 | 20 | 1 | -4 / 1 / 15 | 20.8 / 52.4 | 0/11 (16.23) | 6.4 / 15.8 (max 13.1 / 42.1) |
| R1 | 20 | 0.1 | -4 / 1 / -14 | 5.9 / 9.0 | 1/11 (3.10) | 1.4 / 2.7 (max 2.7 / 4.8) |
| R1 | 20 | 1 | -2 / 1 / 4 | 6.3 / 8.6 | 1/11 (3.00) | 1.8 / 4.2 (max 3.3 / 7.6) |
| R1f | 20 | 0.1 | -6 / 0 / -22 | 2.8 / 4.3 | 5/11 (1.38) | 0.5 / 0.7 (max 0.9 / 1.3) |
| R1f | 20 | 1 | -3 / 2 / 4 | 3.0 / 3.7 | 5/11 (1.36) | 0.6 / 1.5 (max 1.0 / 4.3) |

- **Plain words.** Double differences say very little about where the whole cluster sits. rtDD has no
  constraint on the mean shift of the cluster; with `absLocConstraint 0`, only the damping holds it. (HypoDD's
  SVD constrains it: its dt.cc run ended within 1 m of its start, although its dt.ct run moved 72 m up; section 3.)
- **Damping 0.01 (rtDD default).** The center wanders a little at every iteration and keeps going: 633 m after
  40 iterations in R1f.
- **The shape settles faster than the center, but not at once.** For R1f the shape still differs from its
  20-iteration shape by 2.4 / 2.6 m RMS (H / V) after 2 iterations and 1.0 / 1.7 m after 3; after 5 iterations
  it is within about 1 m (0.2 / 0.7 m RMS, largest 1.6 m vertically), while the center keeps wandering. The
  unfiltered R1 settles more slowly (1.5 / 2.7 m after 5 iterations, 1.3 / 2.4 m after 10), and the
  catalog-only R0 more slowly still (2.7 / 7.6 m after 10 iterations).
- **Damping 0.1 or 1.0** keeps the center within about 5-23 m (3-D) of the start in the cross-correlation runs (R0: 182 m
  vertically at 0.1, 15 m at 1.0). It does change the shape somewhat: for R1f by 0.5 / 0.7 m RMS (0.1) and
  0.6 / 1.5 m RMS, largest 4.3 m vertically (1.0); for R1 by 1.4 / 2.7 m and 1.8 / 4.2 m. The agreement of R1f
  with dt.cc changes by ≤ 0.6 m.
- The rtDD manual warns about exactly this: "low damping ... risks large cluster shifts" (`doc/base/multievent.rst`).

## 7. Single-event (real-time style) relocation, leave-one-out

- **How it was done.** Each event in turn is removed from R1's (or R1f's) relocated catalog. It is then relocated
  alone against the 10 others, starting at the centroid with its original picks. The background events stay
  fixed, so the result is compared with the event's own multi-event position without removing any centroid.
- **Neighbors.** Every event found all 10 neighbors, in every step.
- **The background is not independent of the left-out event.** The 10 fixed background positions come from the
  multi-event solutions R1 or R1f, which were computed with the left-out event included. A fully independent
  test would rebuild the background without that event (a multi-event run of 10 events); this was not done.

3-D distance (m) between the single-event and the multi-event position of each event:

| event | R6 (stock, cross-correlation fails) | R6p (padded, unfiltered) | R6tp (two-step, padded) | R6f (padded, filtered) | R6tf (two-step, filtered) | R6f cross-correlations used / pairs |
|---|---|---|---|---|---|---|
| 1 | 58.5 | 0.4 | 0.5 | 0.3 | 1.0 | 406 / 478 |
| 2 | 13.0 | 0.5 | 1.4 | 0.2 | 0.6 | 566 / 650 |
| 3 (ML 2.2) | 107.4 | 33.1 | 38.7 | 27.7 | 43.5 | 514 / 649 |
| 4 | 16.7 | 0.8 | 2.2 | 0.8 | 1.7 | 589 / 650 |
| 5 | 31.4 | 1.1 | 3.0 | 0.1 | 2.2 | 379 / 451 |
| 6 | 31.4 | 0.1 | 1.7 | 0.3 | 0.4 | 542 / 631 |
| 7 | 27.9 | 1.1 | 1.4 | 0.6 | 0.7 | 348 / 392 |
| 8 | 32.8 | 0.5 | 1.0 | 0.2 | 2.2 | 330 / 396 |
| 9 | 32.9 | 0.2 | 1.6 | 0.1 | 1.5 | 468 / 536 |
| 10 | 23.7 | 0.7 | 2.7 | 0.4 | 1.9 | 288 / 348 |
| 11 | 16.0 | 0.9 | 1.8 | 0.3 | 2.2 | 349 / 421 |
| RMS / max | 43.8 / 107.4 | 10.0 / 33.1 | 11.8 / 38.7 | 8.4 / 27.7 | 13.2 / 43.5 | |

R6t (stock, two-step) behaves like R6: RMS 43.8 m, max 107.4 m.

- **When cross-correlation works,** single-event mode puts 10 of 11 events within about 1 m (one step) or 3 m
  (scrtdd two-step, automatic origin) of their multi-event positions.
- **The exception is event 3**, the ML 2.2 and largest event (28-44 m). HypoDD's bootstrap is also widest for
  it (16 / 6 / 26 m). In the reference it has the fewest cross-correlation data (48 P + 65 S), because of its
  special window and band. Its position is the least stable in both programs.
- **Against HypoDD dt.cc** (section 4), R6f places 7 of 11 events inside the bootstrap box (largest ratio
  1.68, event 4; shape RMS 5.0 / 4.9 m).

## 8. Cross-correlation compared with the reference dt.cc (f)

The reference measured 1226 P + 1575 S differential times; 1017 P + 1509 S had CC ≥ 0.7.

**How the agreement is counted.** Both sets of differential times lie on a 1-ms grid (rtDD's lags at
1000 Hz; the reference values are written to 1 ms), so "within 2 ms" means |difference| ≤ 2 ms on that grid
(`|round(diff_ms)| <= 2`; the largest distance of any difference from the grid is 3e-12 ms). Before the
verification, the script compared the raw floating-point differences with 2.0 ms; about half of the
differences of exactly 2 ms failed that test through rounding noise, so every 2-ms fraction was too low, by
up to 12 points (for example R1f 66 % instead of 71.6 %). The 5-ms fractions moved by at most 2 points.

**CC correlation.** The last column correlates rtDD's CC with the reference CC over the pairs in both with
CC ≥ 0.7 (the "in both" column), once with rtDD's signed CC and once with its absolute value. The reference
kept only positive CC, so the signed value is pulled down by rtDD's anti-correlated matches (section 1c).

| run | measured P / S | abs(CC) >= 0.7 P / S | of these CC <= -0.7 P / S | CC >= +0.7 P / S | in both (CC >= 0.7) | dt difference median / MAD (ms) | within 2 / 5 ms | CC r signed / abs |
|---|---|---|---|---|---|---|---|---|
| R1 | 1226 / 1575 | 754 / 1025 | 93 / 23 | 661 / 1002 | 1684 | -0.0 / 2.0 | 53.7 % / 70.1 % | 0.19 / 0.17 |
| R1f | 1226 / 1575 | 910 / 1480 | 58 / 0 | 852 / 1480 | 2342 | 0.0 / 1.0 | 71.6 % / 77.6 % | 0.23 / 0.65 |
| R1fz | 1226 / 1575 | 943 / 1472 | 74 / 0 | 869 / 1472 | 2365 | 0.0 / 1.0 | 72.1 % / 77.2 % | 0.21 / 0.65 |
| R2 | 1226 / 1575 | 714 / 712 | 80 / 3 | 634 / 709 | 1339 | -0.0 / 2.0 | 59.1 % / 74.5 % | 0.18 / 0.13 |
| R2f | 1226 / 1575 | 894 / 1375 | 38 / 0 | 856 / 1375 | 2228 | -0.0 / 1.0 | 72.1 % / 80.5 % | 0.22 / 0.55 |
| R4 | 1185 / 1550 | 747 / 1025 | 90 / 23 | 657 / 1002 | 1683 | -0.0 / 2.0 | 53.7 % / 70.2 % | 0.19 / 0.17 |
| R4f | 1185 / 1550 | 909 / 1470 | 57 / 0 | 852 / 1470 | 2337 | 0.0 / 1.0 | 71.7 % / 77.7 % | 0.23 / 0.65 |

R3b/R5 equal R1, R3bf/R5f/R1fw equal R1f, and V0/V1 equal R1 within rounding: same waveforms, same measurement.

Subsets (triplets in both with CC ≥ 0.7; dt difference = rtDD minus reference):

| run | subset | n | median / MAD (ms) | RMS (ms) | within 2 / 5 ms | CC r signed / abs | median CC rtDD / reference |
|---|---|---|---|---|---|---|---|
| R1 | without_event3 | 1378 | -0.0 / 2.0 | 123.5 | 63.3 % / 80.9 % | 0.23 / 0.19 | 0.86 / 0.95 |
| R1 | event3_pairs_only | 306 | 2.0 / 63.0 | 245.9 | 10.5 % / 21.6 % | 0.02 / 0.06 | 0.78 / 0.94 |
| R1 | rtdd_cc_negative | 92 | -140.0 / 268.5 | 369.4 | 0.0 % / 0.0 % | 0.14 / -0.14 | -0.80 / 0.90 |
| R1f | without_event3 | 1833 | -0.0 / 1.0 | 21.4 | 88.8 % / 93.7 % | 0.55 / 0.83 | 0.93 / 0.94 |
| R1f | event3_pairs_only | 509 | 5.0 / 58.0 | 185.0 | 9.8 % / 19.6 % | 0.00 / 0.18 | 0.83 / 0.93 |
| R1f | P | 885 | 0.0 / 1.0 | 76.8 | 79.0 % / 81.1 % | 0.16 / 0.69 | 0.89 / 0.92 |
| R1f | S | 1457 | -0.0 / 1.0 | 94.6 | 67.1 % / 75.5 % | 0.58 / 0.58 | 0.92 / 0.95 |
| R1f | rtdd_cc_negative | 54 | 4.0 / 53.0 | 158.1 | 0.0 % / 0.0 % | -0.22 / 0.22 | -0.78 / 0.92 |
| R1fz | without_event3 | 1846 | -0.0 / 1.0 | 20.3 | 89.8 % / 93.8 % | 0.52 / 0.87 | 0.94 / 0.94 |
| R2f | without_event3 | 1785 | -0.0 / 1.0 | 19.7 | 87.4 % / 95.2 % | 0.63 / 0.68 | 0.90 / 0.95 |

Over all measured triplets (no CC threshold, `both_measured` in `xcorr_comparison.csv`):

| run | all measured triplets | within 2 / 5 ms | largest distance from the 1-ms grid (ms) |
|---|---|---|---|
| R1 | 2801 | 41.2 % / 54.2 % | 3.4e-12 |
| R1f | 2801 | 64.2 % / 70.0 % | 3.4e-12 |

- **Count.** With the band-pass applied, rtDD finds about as many good S measurements as the reference
  (1480 against 1509) but fewer P (910 against 1017, of which 58 negative). Without the band-pass, it finds far
  fewer (754 P, 1025 S).
- **Agreement.** Excluding pairs with event 3, 87-90 % of the filtered differential times agree with the
  reference within 2 ms (R2f 87.4 %, R1f 88.8 %, R1fz 89.8 %) and 94-95 % within 5 ms (median 0, MAD 1 ms).
  Over all pairs where both passed, R1f agrees within 2 ms for 71.6 % (P 79.0 %, S 67.1 %); the stock run R1
  for 53.7 %.
- **The rest.**
  - The pairs with event 3 disagree: the reference measured them with a ±0.05 s window at 1-40 Hz.
  - The negative-CC measurements disagree (section 1c).
  - So does a minority of cycle skips: RMS 20-21 ms against a median of 0.
- **The CC values themselves.** Signed, they correlate poorly with the reference CC (R1f r = 0.23; P 0.16,
  S 0.58). With rtDD's |CC| the correlation is clearly better (R1f 0.65; P 0.69; without event 3, 0.83): much of
  the low signed value comes from the anti-correlated P matches. The rest of the scatter comes from different
  normalization and windows, and from L2 instead of the better of N and E for S.
- **Over all 2801 measured triplets** (no CC threshold), R1f agrees with the reference within 2 ms for 64.2 %
  and within 5 ms for 70.0 %.

## 9. Residuals: rtDD's own statistics and HypoDD's RCC/RCT

| run | double differences (initial) | with weight > 0 at the end (of which cc) | final RMS, weight > 0: all / cc / catalog (ms) | final weighted RMS (ms) | last-iteration median / MAD (ms) | wall time (s) |
|---|---|---|---|---|---|---|
| R0 | 2801 | 2603 (0) | 32.3 / - / 32.3 | 22.4 | -0.76 / 15.5 | 0.4 |
| R1 | 2801 | 2083 (1526) | 9.5 / 5.1 / 16.3 | 5.0 | -0.28 / 4.6 | 25 |
| R1f | 2801 | 2228 (2144) | 3.9 / 3.4 / 10.3 | 2.8 | -0.18 / 2.4 | 42 |
| R1fz | 2801 | 2225 (2138) | 4.1 / 3.6 / 10.5 | 2.9 | -0.22 / 2.5 | 42 |
| R2 | 2801 | 2242 (1289) | 14.8 / 6.3 / 21.4 | 8.0 | -0.23 / 6.9 | 32 |
| R2f | 2801 | 2234 (2112) | 3.7 / 3.1 / 9.0 | 2.7 | -0.14 / 2.3 | 51 |
| R4 | 2735 | 2044 (1521) | 8.7 / 4.8 / 15.1 | 4.7 | -0.24 / 4.2 | 23 |
| R4f | 2735 | 2219 (2140) | 3.8 / 3.4 / 10.0 | 2.7 | -0.17 / 2.3 | 39 |
| R5 | 2801 | 2096 (1528) | 9.9 / 5.4 / 16.9 | 5.3 | -0.29 / 4.8 | 24 |
| R5f | 2801 | 2206 (2135) | 3.6 / 3.2 / 9.3 | 2.5 | -0.17 / 2.1 | 40 |
| R6 (11 systems) | 5602 | 5178 (1) | 34.4 / 11.9 / 34.4 | 24.3 | - | 9 |
| R6p (11 systems) | 5602 | 4230 (3085) | 13.9 / 7.3 / 23.9 | 8.0 | - | 165 |
| R6f (11 systems) | 5602 | 4654 (4442) | 10.3 / 9.0 / 24.6 | 6.4 | - | 305 |
| R6tf (11 step-2 systems) | 5602 | 4639 (4395) | 10.2 / 8.6 / 25.2 | 6.8 | - | 300 |

HypoDD for comparison (`hypoDD.log`, last iteration; RCC/RCT = per-event values in `hypoDD.reloc`, median over
events):

| run | final cc RMS (ms) | final ct RMS (ms) | data kept, cc / ct | RCC / RCT median (ms) |
|---|---|---|---|---|
| 02.dt.cc | 1.3 | 41.7 | 1472 / 2645 | 1 / 41 |
| 01.dt.ct | - | 23.0 | - / 2729 differences, 2645 kept in the dt.cc run | - / 23 |

- **The initial double-difference RMS is ~950 ms in every run.** The 17 outlier picks produce it (R4: 118-153 ms).
- **The median absolute travel-time RMS per event is ~1 s** (`relocated-event.csv`, `startRms` / `finalRms`).
  It is dominated by the same outlier picks; R4: 229-236 ms.
- **The final cc RMS is larger in rtDD (3.4 ms) than in HypoDD (1.3 ms).** HypoDD's last set throws away cc data
  beyond 2 x spread and keeps 1472 of 2526; rtDD keeps 2144.

## 10. Caveats

- **The filtered runs use our own proxy subclass.** pyrtdd itself cannot filter (section 1a). The subclass
  reproduces libhdd's resampler exactly for P. For S, libhdd's extra demean of the processed horizontals before
  L2 changes 7 of 1575 lags (shape effect ≤ 0.2 m).
- **The padded single-event runs change the batch loading only.** Fetching 0.05 s more (section 1b) is a proxy
  fix, not a pyrtdd setting.
- **Origin times.** HypoDD gives them to 0.01 s, so an origin-time RMS of about 3 ms is the rounding floor.
- **The reference's event-3 pairs** were measured with a ±0.05 s window at 1-40 Hz. Its dt.cc results for event
  3 are not comparable with any rtDD measurement.
- **Station elevations.** The NonLinLoc grids put stations at their elevation; HypoDD used 0 m. This changes
  absolute travel times by up to 0.061 s (P) and 0.106 s (S), at BAU, 562 m (`validation.csv`). For a cluster
  about 150 m across the change should cancel almost completely in double differences (same station, nearly
  the same ray), but this was not tested: no run used grids with the stations at 0 m.
- **The S picks carry a constant ~0.27 s S-P deficit** (found before this step). It cancels in double differences at the same
  station.
- **rtDD's per-event `startRms` / `finalRms` are absolute residuals**, not the double-difference fit.
- **The drift numbers in "centroid shift" are not reproducible to the meter between settings:** they are a
  random walk of the cluster (section 6). The shape numbers are reproducible.
- **The bootstrap box measures only HypoDD's own precision.** The bootstrap (`bootstrap_errors.csv`: 1000
  resamples, started from HypoDD's own solution, same data and settings) shows how much HypoDD's solution moves
  when its data are resampled: 1.7-4.8 m horizontally and 3.3-6.9 m vertically for ten events, 16 / 6 / 26 m for
  event 3. "Inside the box" therefore means "as close to HypoDD as HypoDD is to itself", not "correct". One of
  R1f's five inside events is event 3, whose wide box is easy to fall into; the other four (2, 5, 7, 8) are
  among the ten well-constrained events.
- **The leave-one-out runs (R6\*) are not fully independent.** Their fixed background positions come from R1 or
  R1f, which were computed with the left-out event included (section 7).

## 11. Files (all under `runs/gwangyang/pyrtdd/`)

| file | content |
|---|---|
| `summary_metrics.csv` | one row per run x reference: (a)-(f); also the scale rows `REF_hypodd_dtct` and `REF_hypoinverse_kim1983` against dt.cc |
| `per_event_vs_reference.csv` | per run x reference x event: shape and absolute differences, bootstrap half-widths, inside flags, origin-time differences |
| `run_vs_run_metrics.csv`, `per_event_run_vs_run.csv` | section 5 and section 7 |
| `xcorr_comparison.csv` | (f) per run and subset |
| `residual_stats.csv` | section 9 |
| `positions_enu.csv` | every solution's event positions (local ENU, latitude, longitude, depth, origin time) |
| `diag_centroid_drift/diag_centroid_drift.csv` | section 6 (27 variants, each with its own relocated catalog and `options.json`; recomputed with `--metrics-only` after the verification) |
| `print_note_tables.py`, `note07_tables.md` | prints every table of sections 4-9 of this note from the files above (and its last output) |
| `checks/proxy_filter_check.json`, `checks/filter_effect_test/filter_effect_test.json` | section 1a |
| `<run>/...` | per run: relocated catalog, `options.json`, `run_info.json`, `console.log`, `processing/`, `clusters/`, `xcorr_cache.csv`, `inputs/` (R6: `single_event_results.csv`, `inputs/background_without_<k>/`) |

**Catalog for the scrtdd and real-time steps.**

- **R1** (exactly the requested settings):
  `R1_xcorr_like_reference_hypodd_like/relocated-{station,event,phase}.csv`.
- **R1f** (the same with the band-pass really applied; closer to HypoDD):
  `R1f_xcorr_like_reference_hypodd_like_filtered/relocated-{station,event,phase}.csv`.
- **Contents.** Both catalogs keep the event ids 1-11, all 763 picks and 54 stations. Pick uncertainties are
  written as `nan`, which libhdd reads back without problems: the R6 background catalogs were built from them.
- **Absolute position.** Both centers slid during the relocation (section 6): R1 sits 214 m west and 651 m
  deeper than HypoDD dt.cc, R1f 317 m west and 172 m deeper. If a catalog at the original center is wanted:
  `diag_centroid_drift/R1f_xcorr_like_reference_hypodd_like_filtered__it20_damp1/relocated-*.csv` (damping 1.0;
  center within 5 m of the start; shape against dt.cc 3.0 / 3.7 m instead of 3.1 / 4.3 m, and 0.6 / 1.5 m RMS
  from R1f's own shape; no processing output saved for the diagnostic variants).
