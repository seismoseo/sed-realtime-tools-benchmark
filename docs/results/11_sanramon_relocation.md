# Step 11: rtDD relocation of the San Ramon 2015 swarm (pyrtdd and scrtdd), 685 events (2026-10-17)

Scripts and outputs are in `runs/sanramon/`. All of them are dry runs by default; `--apply` acts.

| script | purpose |
|---|---|
| `pyrtdd/run_pyrtdd_sanramon.py` | pyrtdd runs |
| `scrtdd/scrtdd_sanramon.py` + `scrtdd/scrtdd_common_sanramon.py` | scrtdd runs |
| `analysis/analyze_sanramon.py` | all comparisons |
| `waveforms/*.py` | band choice and waveform checks |

Logs are `logs/11_sanramon_*`.

## Short answer

- **All runs finished.** Every run relocated **680 of the 685 events**. The same 5 events were always dropped: each
  has fewer than 8 picks, so it cannot share rtDD's default minimum of 8 phases with any neighbour (section 5).
- **scrtdd = pyrtdd, to well below a metre (catalog only) and about a metre (with cross-correlation).**
  - **S0 vs P0.** Both programs built the same 358,474 phase pairs and the same initial double differences.
    The final positions differ by a median of 0.25 m, almost all of it a common shift. The relative difference is
    0.01 m; one event differs by 7 m.
    - Unlike Gwangyang, the digits are not identical.
    - Each program repeats itself bit for bit, and scrtdd's two travel-time readers agree bit for bit. The
      libhdd source and the compiler are the same.
    - So this is a numerical difference between the two builds, amplified over 20 iterations of a
      357,000-equation system. It is not a settings difference (section 7).
  - **S1 vs P1.**
    - Cross-correlation lags: 324,320 of 331,408 measured lags are identical (97.9 %), and another 6,935 differ by
      one sample (1 ms). 62 measurements fall on opposite sides of the 0.7 threshold.
    - Positions: a median of 1.1 m apart (0.45 m relative); 90 % of events within 2.5 m.
    - **One poorly constrained event (72544210, M 0.8, 8 P + 1 S picks) ends 6.3 km apart.** A single S lag
      took a different one of two equally high correlation peaks (+28 vs −79 ms).
    - Against the references, S1 and P1 are indistinguishable.
- **Cluster shape against LDEO NCAeqDD (primary reference).**
  - Medians over the 680 common events. "Relative" = position after removing each catalog's centroid; "local" =
    the vectors to each event's 10 nearest neighbours in LDEO (median spacing 107 m).

  | | relative H / V (m) | local H / V (m) | closer to LDEO than the NCSS start |
  |---|---|---|---|
  | NCSS routine (start) | 229 / 394 | 292 / 506 | |
  | P0 = S0 (catalog only) | 142 / 134 | 137 / 147 | 80 % of events |
  | **P1 / S1 (cross-correlation)** | **97 / 106** | **51 / 63** | **89 %** (98 % locally) |
  | *NCEDC DD (DD-RT) vs LDEO, for scale* | *162 / 236* | *190 / 241* | |

  - rtDD with cross-correlation brings the events **2.9× closer** to LDEO's structure than the NCSS start in 3-D
    (5.8× horizontally and 8.0× vertically at the local scale).
  - It agrees with LDEO **better than the NCEDC DD catalog does**.
  - LDEO's own 95 % errors are only about 13 m. The remaining 50–100 m are therefore real differences (velocity
    model, data, weighting), not LDEO noise.
  - Against NCEDC DD (secondary), P1 is no better than P0 (200 / 266 m against 202 / 206 m). NCEDC DD is itself
    too scattered to judge at this level: its neighbour spacing is 193 m, against LDEO's 107 m.
- **Absolute position: the default solver moves the whole cluster 2.3 km too deep.**
  - Against LDEO, the centroid of P0/S0/P1/S1 is 2.25–2.35 km deeper and 0.7–0.8 km farther west (mean depth
    9.5–9.6 km against 7.3 km).
  - The cause is the absolute-residual equations of the default solver (absLocConstraint 0.3). They fit the CON
    model, which predicts P 0.4–0.6 s too late at 40–120 km (no station corrections; the NCSS uses regional
    models and station delays).
  - Without them (absLocConstraint 0, default damping 0.01) the cluster ends **4.1–4.5 km shallower than LDEO's
    centroid**; measured from the NCSS starting positions, it drifts 4.5–4.9 km upward.
  - Damping 1.0 holds it at the NCSS centroid (0.43 km deeper than LDEO).
  - **Do not use rtDD's absolute positions from these runs.** Use the relative geometry.
- **Fault structure.** All catalogs show the steep, NNW-striking plane of the Calaveras fault:

  | catalog | strike / dip | median distance from the plane | RMS distance from the plane |
  |---|---|---:|---:|
  | LDEO | 352.5° / 83.6° E | 121 m | 359 m |
  | P1 | 354.6° / 86.1° E | 141 m | 405 m |
  | S1 | 354.1° / 88.5° E | 135 m | 406 m |
  | P0 | 353.4° / 88.8° E | 159 m | 427 m |
  | NCSS | 170.8° / 84.0° W | 208 m | 464 m |

  The plane dips 84–89°, so a small change flips the dip direction (NCSS: W). With cross-correlation,
  the swarm's thickness is within about 15–20 m (median) of LDEO's.
- **Cross-correlation (P1 = S1).**
  - P: 320,207 phase pairs, 296,378 measured, 173,002 with |CC| ≥ 0.7 (136,561 positive and **36,441 negative**).
  - S: 38,267 pairs, 35,030 measured, 19,907 with CC ≥ 0.7.
  - Residuals: for the cross-correlation data, the median absolute deviation of the double-difference residuals
    fell from 52.7 ms to 13.2 ms (weighted RMS 106 → 27 ms). For the catalog data it fell from 60 to 42 ms.
- **Negative correlations.** rtDD accepts |CC| ≥ 0.7, so polarity-reversed or wrong-peak P matches are used. Their
  lags are long (median 76 ms against 28 ms for positive CC).
  - A diagnostic that turns them back into catalog times (P1pos, not an rtDD option) moves events by a median of
    38 m.
  - It improves the vertical relative geometry from 106 to 90 m. The other metrics against LDEO change by ≤ 5 m.
- **Sensitivity runs (section 8).**
  - Nearest-neighbour clustering changes positions by a median of 38–46 m but not the overall agreement with
    LDEO. With cross-correlation it is better locally (41 / 55 m) and worse vertically (123 m).
  - Switching off the absolute equations gives the best horizontal shape (63 m) but stretches the cluster
    vertically and lets it drift more than 4 km up.
- **Runtime and memory** (single-threaded; far below the 60 GB limit):

  | run | time | peak memory |
  |---|---|---|
  | P0 | 55 s | 0.44 GB |
  | S0 | 54 s | 0.36 GB |
  | P1 | 27.9 min | 1.0 GB |
  | S1 | 19.4 min | 0.76 GB |

  pyrtdd's Python filtering proxy accounts for most of the difference between P1 and S1.

## 1. What was relocated, and with what

- **Events:** 685 NCSS events of the benchmark box (Calaveras fault near San Ramon, 2015-10-13 to 2015-11-29;
  largest Mw 3.6, nc72540765).
  - Start: the NCSS **routine** locations (`data/sanramon_2015/inputs/rtdd_catalog/event.csv`; depth below sea
    level).
  - Picks: 25,684 NCSS **analyst** picks (22,545 P + 3,139 S) at 415 stations.
  - Inputs are described in `docs/sanramon_inputs.md`; the waveform checks in `docs/sanramon_waveforms.md`.
- **Travel times:** NonLinLoc 2-D grids of the NCSS CON gradient model (Vp/Vs 1.73), TRANS_MERC projection
  (`inputs/nll_con_tm/time`, model name `sanramon_con`).
  - The grids cover the 264 stations within 120 km. Picks at the 151 farther stations get no travel time.
    rtDD skips them. Each run logs 94 "Cannot find a suitable P/S time grid" warnings, one per far station and
    phase that is queried.
  - All 528 station/phase grids are found with libhdd's default `maxSearchDistance` of 0.1 m.
- **Waveforms:** the SDS archive `inputs/sds` holds origin −10 s to +30 s for every picked sensor within 60 km.
  StationXML `inputs/stations.xml` (pyrtdd) and its `fdsnxml2inv` conversion
  `runs/sanramon/scrtdd/inputs/inventory_sc.xml` (scrtdd) give the component orientations.

### Runs

| run | program | what it is | cross-correlation | clustering | solver |
|---|---|---|---|---|---|
| **P0** | pyrtdd | catalog differential times only, as a user would run rtDD on a regional catalog | off | rtDD default (ellipsoids) | rtDD default (absLocConstraint 0.3, damping 0.01) |
| **P1** | pyrtdd | P0 + cross-correlation (band-pass really applied, through the proxy workaround) | on | default | default |
| **S0** | scrtdd | = P0 | off | default | default |
| **S1** | scrtdd | = P1 | on | default | default |
| P0n / S0n | pyrtdd / scrtdd | sensitivity: nearest-neighbour clustering (numEllipsoids 0) | off | nearest neighbour | default |
| P1n | pyrtdd | sensitivity: P1 with nearest-neighbour clustering; P1's cross-correlations re-used, new pairs correlated | on | nearest neighbour | default |
| P0a0 / P1a0 | pyrtdd | sensitivity: no absolute-location equations (absLocConstraint 0, damping 0.01); P1a0 re-uses P1's cross-correlations | off / on | default | pure DD, damping 0.01 |
| P0d1 / P1d1 | pyrtdd | sensitivity: absLocConstraint 0 and damping 1.0 | off / on | default | pure DD, damping 1.0 |
| P1pos | pyrtdd | diagnostic: P1 with its 36,441 negative-CC (≤ −0.7) P measurements marked invalid in a copy of P1's cache, so those pairs fall back to catalog times (emulates a positive-CC-only rule; **not an rtDD option**) | on | default | default |
| P0rep / S0rep | pyrtdd / scrtdd | check: identical repeat of P0 / S0 (is each program deterministic?) | off | default | default |
| S0nat | scrtdd | check: S0 with scrtdd's built-in NonLinLoc reader (`Native:NLLGrid`) instead of the `tttnll` plugin | off | default | default |

Every variant that was run is listed here. Nothing was tuned towards the references.

## 2. Settings: pyrtdd (libhdd) → scrtdd → value

The pyrtdd values are read back from the libhdd objects into each run's `options.json`. scrtdd's values come from
SeisComP's own configuration reader and are written to each run's `run_options.json`; every key is written
explicitly. **scrtdd's profile defaults are not libhdd's defaults.** The keys marked ★ would silently differ if
left unset.

| group | pyrtdd / libhdd | scrtdd key (`profile.sanramon.`…) | value |
|---|---|---|---|
| travel times | `NLLGrid(gridPath=…/nll_con_tm/time, gridModel='sanramon_con', maxSearchDistance=0.1, maxOpenFiles=512, KeepOpen)` | `global.cfg`: `plugins = tttnll`, `ttt.NLLGrid.tables = sanramon_con`, `ttt.NLLGrid.sanramon_con.tablePath = …/time/sanramon_con`, `…maxSearchDistance = 0.1` ★ (plugin default 10 m), `…maxOpenFiles = 512`; profile `tableType = NLLGrid`, `tableModel = sanramon_con` | CON gradient model grids |
| phases | `validPphases ['P']`, `validSphases ['S']`, `PSTableOnly true` | `P-Phases`, `S-Phases`, `PSTableOnly` | P, S, true |
| clustering (default) | `ClusteringOptions()` | `doubleDifferenceSystem.…` | |
| | `numEllipsoids` | `eventPairSelection.multiEvent.numEllipsoids` ★ (scrtdd default 0) | 5 (P0n/S0n/P1n: 0) |
| | `maxNumNeigh` / `maxNeighbourDist` | `…multiEvent.maxNumNeighbours` / `maxNeighbourDistance` | 40 / 5 km |
| | `minNumNeigh` | `eventFiltering.minNumNeighbours` ★ (scrtdd default 4) | 8 |
| | `minNumPhases` / `maxNumPhases` | `eventFiltering.minNumPhases` / fixed in scrtdd | 8 / 0 (no limit) |
| | `minEvStaToInterEvRatio` | `phaseFiltering.minStationToEventPairDistRatio` | 3 |
| | `minEvStaDist` / `maxEvStaDist` | `phaseFiltering.minStationDistance` / `maxStationDistance` | 0 / −1 (no limit) |
| solver (default) | `SolverOptions()`: `type`, `algoIterations`, `absLocConstraintStart/End`, `dampingFactorStart/End`, `downWeightingByResidualStart/End`, `xcorrWeightScaler`, `usePickUncertainties`, `L2normalization`, `solverIterations` | `solver.solverType`, `algoIterations`, `absoluteLocationConstraint`, `dampingFactor`, `downWeightingByResidual`, `xcorrWeightScaler`, `usePickUncertainties`; the last two are fixed in scrtdd | LSMR, 20, 0.3/0.3, 0.01/0.01, 10→5, 2, false, true, auto (P0a0/P1a0: absLoc 0; P0d1/P1d1: absLoc 0 and damping 1.0) |
| cross-correlation (P1/S1) | `XcorrOptions.enable`, `minEvStaDist`, `maxEvStaDist`, `maxInterEvDist` | `crossCorrelation.enable`, `minStationDistance`, `maxStationDistance` ★ (scrtdd default 60 km), `maxInterEventDistance` ★ (scrtdd default 2 km) | true, 0, −1, −1 (no limits) |
| | P: `minCoef, startOffset, endOffset, winScaling, maxDelay, components` | `crossCorrelation.p-phase.minCCCoef, winStart, winEnd, winScaling, maxDelay, components` | 0.7, −0.5 s, +0.5 s, 0.02, 0.5 s, **Z, 1** |
| | S: same | `crossCorrelation.s-phase.…` | 0.7, −0.5 s, +1.0 s, 0.04, 0.5 s, L2 |
| waveform processing (P1/S1) | `wfFilter.filterStr ''`, `resampleFreq 0` in libhdd; the proxy does it instead (bug workaround, below): demean → libhdd's sinc resampler (numpy port) to 1000 Hz → ObsPy `bandpass(freqmin=1.5, freqmax=15, corners=4)`, causal; `extraTraceLen 1 s` | `crossCorrelation.waveformFiltering.filterString "BW(4,1.5,15)"`, `resampling 1000`, `margin 1` | 1.5–15 Hz, 4 poles (8 in total), one pass, at 1000 Hz |
| waveform access | `PreprocessingSDSProxy` (ObsPy SDS client on `inputs/sds`), inventory `stations.xml`, no disk cache | `-I sdsarchive://…/inputs/sds`, `--inventory-db file://…/inventory_sc.xml`, `performance.cacheWaveforms false` (so both programs read the same windows straight from the archive) | |

**Why "Z, 1" for P.** The rtDD default is Z only. The NCSN and BK borehole sensors name their components 1/2/3,
with 1 vertical (dip ±90° in `stations.xml` for every sensor that has a 1 but no Z).
- 2,854 P picks are on such sensors (EP1 1,592, CN1 512, DP1 352, EP2/EP3 316, HN1 66, others 16).
- 2,809 of them are within 60 km and have waveforms.
- With Z alone they could never be cross-correlated.

For sensors that have a Z, Z is used.

**Why 1.5–15 Hz** (`runs/sanramon/waveforms/band_selection.py`; table in `docs/sanramon_waveforms.md` section 6).
The signal-to-noise ratio was measured in rtDD's own windows for 18,785 P and 3,050 S picks:
- **P:** the median SNR exceeds 3 from about 2 Hz to 20 Hz (from 4–5 Hz for M < 1).
- **S:** the median SNR exceeds 3 from 1 Hz to 16 Hz and falls to 2.8 at 20 Hz.
- **40 Hz channels (BH):** they have nothing above 20 Hz.

The common usable band is about 2–16 Hz. The 1.5–15 Hz band-pass lies inside it, and it is the band Waldhauser &
Schaff (2008) used for NCSN cross-correlation in the LDEO catalog.

**Why 1000 Hz resampling.** libhdd's cross-correlation has no sub-sample interpolation, so a lag is quantised to
one sample: 10 ms at the 100 Hz of most EH/HH channels. Resampling (libhdd's windowed-sinc resampler) to 1000 Hz
gives 1 ms lags. This is the same choice as in the Gwangyang runs.

**pyrtdd workaround** (known bug 1, `docs/results/07_gwangyang_pyrtdd.md` 1a). The stock proxy's `filter()` works
on a copy, so a filter string never reaches the cross-correlation. P1 (and P1n/P1a0/P1d1) therefore use
`PreprocessingSDSProxy`, copied from `runs/gwangyang/pyrtdd/run_pyrtdd_gwangyang.py`. It filters and resamples
inside `loadTrace`, and libhdd's own filter and resampling are switched off. pyrtdd itself was not patched.
Single-event mode (bug 2) was not used.

## 3. Results against the reference catalogs: shape, centroid, improvement (metrics a–c)

**How the numbers are made** (`runs/sanramon/analysis/analyze_sanramon.py`):

- **Event set.** All solutions are compared on the same events: the 680 events relocated by every main run
  (P0, P1, S0, S1) that are also in the reference. That is 680 for LDEO and 679 for NCEDC DD (72540935 has no NCEDC
  DD solution).
- **Coordinates.** Positions are converted to metres east, north and up of 37.786 N, −121.963 E (transverse
  Mercator). Depths are all below sea level:
  - rtDD inherits sea level from the NonLinLoc grids and `event.csv`;
  - LDEO is geoid-referenced;
  - NCEDC DD depths are below the local model surface. They were converted with each event's NCSS datum
    (depth − datum, datum 120–421 m).
- **(a) Relative geometry.** Each event's position minus its catalog's centroid, compared with the same in the
  reference; the table gives the median / 90th percentile over events.
  - "Local" is the median, over each event's 10 nearest neighbours in the reference, of the difference between our
    and the reference's event-to-neighbour vectors; the table gives the median / 90th percentile over events.
  - The neighbour spacing is a median of 107 m in LDEO and 193 m in NCEDC DD.
  - Removing the median offset instead of the centroid changes the rtDD numbers against LDEO by at most 9.3 m
    (against NCEDC DD by up to 19.7 m, P0a0; the NCSS start's by up to 29 m vertically; `rel_*_mediancentred`
    columns).
- **(b) Centroid shift.** Mean of the solution minus mean of the reference (E / N / U, m; U positive = shallower).
- **(c) Improvement.** The NCSS start's median error divided by the solution's (> 1 = closer to the reference than
  the start). The last column is the share of events whose own error is smaller than the NCSS start's error, for
  the 3-D relative and the local metric.

### Against LDEO NCAeqDD v202112.1 (primary; 680 events)

| solution | n | relative H median / p90 (m) | relative V median / p90 (m) | local H (m) | local V (m) | centroid shift E / N / U (m) | improvement 3-D | improvement local H / V | events closer than NCSS (3-D / local) |
|---|---|---|---|---|---|---|---|---|---|
| NCSS start | 680 | 229 / 501 | 394 / 1121 | 292 / 534 | 506 / 1169 | −28 / −55 / −444 | 1 | 1 / 1 | |
| **P0** | 680 | 142 / 350 | 134 / 405 | 137 / 297 | 147 / 418 | −675 / −95 / −2346 | 2.1 | 2.1 / 3.4 | 80 % / 93 % |
| **S0** | 680 | 142 / 350 | 134 / 405 | 137 / 297 | 147 / 418 | −675 / −95 / −2347 | 2.1 | 2.1 / 3.4 | 80 % / 93 % |
| **P1** | 680 | **97** / 265 | **105** / 275 | **51** / 151 | **63** / 229 | −826 / −204 / −2254 | **2.9** | **5.8 / 8.0** | **89 % / 98 %** |
| **S1** | 680 | 98 / 263 | 106 / 283 | 51 / 154 | 63 / 228 | −825 / −206 / −2246 | 2.9 | 5.7 / 8.0 | 89 % / 97 % |
| P0n (= S0n) | 680 | 139 / 349 | 154 / 405 | 130 / 307 | 151 / 400 | −746 / −157 / −2634 | 2.0 | 2.2 / 3.4 | 80 % / 94 % |
| P1n | 680 | 92 / 274 | 123 / 279 | 41 / 143 | 55 / 203 | −906 / −270 / −2541 | 2.7 | 7.2 / 9.1 | 88 % / 97 % |
| P0a0 | 680 | 103 / 248 | 320 / 816 | 114 / 250 | 215 / 731 | +443 / +707 / +4064 | 1.3 | 2.6 / 2.3 | 65 % / 88 % |
| P1a0 | 680 | 63 / 158 | 288 / 741 | 37 / 111 | 100 / 416 | −66 / +427 / +4451 | 1.6 | 7.9 / 5.0 | 71 % / 95 % |
| P0d1 | 680 | 133 / 311 | 219 / 606 | 140 / 297 | 223 / 634 | −22 / −49 / −427 | 1.6 | 2.1 / 2.3 | 77 % / 93 % |
| P1d1 | 680 | 84 / 246 | 179 / 435 | 60 / 186 | 146 / 449 | −16 / −55 / −440 | 2.2 | 4.9 / 3.5 | 89 % / 96 % |
| P1pos (diagnostic) | 680 | 95 / 252 | 90 / 262 | 50 / 137 | 58 / 205 | −913 / −222 / −2361 | 3.2 | 5.9 / 8.7 | 90 % / 98 % |
| *NCEDC DD (for scale)* | 679 | *162 / 394* | *236 / 765* | *190 / 416* | *241 / 757* | *+153 / +80 / +625* | *1.4* | *1.5 / 2.1* | |

### Against NCEDC DD = DD-RT (secondary; 679 events)

| solution | relative H median / p90 (m) | relative V median / p90 (m) | local H (m) | local V (m) | centroid shift E / N / U (m) | improvement 3-D | improvement local H / V | events closer than NCSS |
|---|---|---|---|---|---|---|---|---|
| NCSS start | 266 / 574 | 402 / 1182 | 307 / 568 | 493 / 1153 | −181 / −135 / −1071 | 1 | 1 / 1 | |
| P0 = S0 | 202 / 510 | 206 / 755 | 200 / 426 | 172 / 474 | −827 / −175 / −2971 | 1.6 | 1.5 / 2.9 | 70 % / 88 % |
| P1 | 200 / 516 | 266 / 879 | 176 / 429 | 137 / 444 | −979 / −284 / −2879 | 1.5 | 1.7 / 3.6 | 65 % / 91 % |
| S1 | 200 / 515 | 262 / 886 | 176 / 429 | 137 / 450 | −978 / −286 / −2871 | 1.5 | 1.7 / 3.6 | 66 % / 91 % |
| P0n = S0n | 204 / 505 | 210 / 736 | 199 / 429 | 175 / 469 | −899 / −237 / −3259 | 1.6 | 1.5 / 2.8 | 71 % / 89 % |
| P1n | 204 / 508 | 255 / 894 | 177 / 427 | 134 / 447 | −1059 / −350 / −3166 | 1.5 | 1.7 / 3.7 | 67 % / 91 % |
| P0a0 | 151 / 402 | 275 / 726 | 168 / 351 | 273 / 723 | +290 / +628 / +3439 | 1.6 | 1.8 / 1.8 | 70 % / 82 % |
| P1a0 | 162 / 441 | 306 / 799 | 148 / 339 | 268 / 863 | −219 / +347 / +3826 | 1.4 | 2.1 / 1.8 | 67 % / 79 % |
| P0d1 | 187 / 454 | 224 / 658 | 196 / 402 | 240 / 605 | −175 / −129 / −1052 | 1.6 | 1.6 / 2.1 | 76 % / 89 % |
| P1d1 | 189 / 449 | 238 / 787 | 173 / 389 | 211 / 571 | −169 / −135 / −1066 | 1.6 | 1.8 / 2.3 | 76 % / 90 % |
| P1pos | 194 / 500 | 244 / 900 | 173 / 407 | 141 / 450 | −1066 / −302 / −2986 | 1.5 | 1.8 / 3.5 | 67 % / 91 % |
| *LDEO (for scale)* | *162 / 394* | *236 / 765* | *157 / 350* | *146 / 457* | *−153 / −80 / −625* | *1.6* | *2.0 / 3.4* | |

**What this means.**

- **Reference uncertainty sets the floor.** NCEDC DD and LDEO differ from each other by 162 m (H) and 236 m (V)
  in relative geometry, and by 190 / 241 m locally.
  - Against LDEO, P1/S1 are well inside this band: 97 / 106 m, locally 51 / 63 m.
  - Against NCEDC DD, every rtDD solution sits at 150–300 m, about where LDEO itself sits.
  - So NCEDC DD (real-time DD-RT, more scattered) cannot tell the rtDD variants apart. **LDEO is the meaningful
    yardstick.**
- **Cross-correlation is what makes the local structure right.**
  - Catalog-only rtDD (P0/S0) improves on the NCSS routine catalog by a factor of 2 (3-D). Its local errors
    (137 / 147 m) are still larger than the typical LDEO neighbour spacing (107 m), so at the 100 m scale it does
    not resolve which event is next to which.
  - With cross-correlation (P1/S1) the local errors drop to 51 / 63 m, half the neighbour spacing, and 98 % of
    events are locally closer to LDEO than at the start.
- **The remaining 50–100 m are real disagreements, not noise in LDEO.** LDEO's own 95 % relative errors are about
  13 m. The two catalogs differ in:
  - velocity model: CON gradient model with real station elevations and no station delays, against NCSN 1-D layered
    models;
  - data: our P and S analyst picks plus P and S correlation, against LDEO's NCSN P picks plus correlation;
  - weighting: rtDD's default residual down-weighting, against hypoDD's two-stage weighting;
  - correlation processing.
- **Robustness of the metric.** Removing each catalog's median offset instead of its mean centroid changes the
  relative H/V of the rtDD runs by at most 10 m (≤ 5 m horizontally for P0/S0/P1/S1), and of the NCSS start by up
  to 29 m vertically. For example, S1's one 6.3 km outlier moves its mean by about 9 m.

## 4. Fault structure (metric d)

Plane fit by SVD of each catalog's centred event coordinates (`plane_fit.csv`):
- the normal is the direction of least spread;
- strike follows the right-hand rule;
- thickness = distance from the plane (median, RMS, 90th percentile).

Set: the 680 common events. LDEO and NCEDC DD also have their own in-box sets.

| catalog | strike | dip (toward) | median distance from plane (m) | RMS (m) | p90 (m) | RMS spread along strike / down dip (m) |
|---|---|---|---:|---:|---:|---|
| LDEO (680 common) | 352.5° | 83.6° (E, 082°) | 121 | 359 | 448 | 858 / 520 |
| LDEO (677 in box) | 356.6° | 87.2° (E) | 118 | 281 | 421 | 756 / 519 |
| NCEDC DD (683 in box) | 346.2° | 85.3° (E) | 175 | 399 | 499 | 879 / 811 |
| NCSS start | 170.8° | 84.0° (W, 261°) | 208 | 464 | 630 | 930 / 949 |
| P0 = S0 | 353.4° | 88.8° (E) | 159 | 427 | 528 | 956 / 587 |
| P1 | 354.6° | 86.1° (E) | 141 | 405 | 485 | 940 / 557 |
| S1 | 354.1° | 88.5° (E) | 135 | 406 | 492 | 942 / 598 |
| P0n = S0n | 353.7° | 89.8° (E) | 163 | 432 | 532 | 952 / 598 |
| P1n | 354.6° | 87.2° (E) | 143 | 411 | 498 | 937 / 626 |
| P0a0 | 350.2° | 89.3° (E) | 125 | 346 | 422 | 814 / 941 |
| P1a0 | 351.0° | 89.7° (E) | 102 | 333 | 437 | 794 / 950 |
| P0d1 | 170.7° | 87.0° (W) | 149 | 407 | 530 | 912 / 726 |
| P1d1 | 172.0° | 89.0° (W) | 122 | 393 | 517 | 911 / 703 |
| P1pos | 354.3° | 79.2° (E) | 162 | 393 | 502 | 929 / 528 |

- **Every catalog sees a near-vertical plane striking N3–14°W.** It is the same plane, 346–357° in strike.
  - The dip is within 1–11° of vertical everywhere.
  - Near vertical, a few degrees flip the dip direction: NCSS, P0d1 and P1d1 dip W, the others E. These are not
    different faults.
  - **rtDD reproduces LDEO's strike to within 2°.**
- **Thickness.**
  - The RMS distance is dominated by outliers in every catalog.
  - Among them are the 5 events of the small separate cluster at the SE edge of the box (71098439, 72547870,
    72549560, 72550205, 72554471). They lie 1.3–4.8 km from the plane and are among the 10 largest distances.
  - Without them the RMS drops from 359 to 291 m (LDEO) and from 405 to 342 m (P1).
  - The median distance is the more telling number: LDEO 121 m; P1/S1 135–141 m; P0 159 m; NCSS 208 m.
- **Pure-DD runs (P0a0/P1a0) look thinner but are distorted.**
  - P1a0's median distance (102 m) is even below LDEO's. But its spread down dip is 950 m, against 520 m in LDEO:
    the cluster is stretched vertically.
  - It is also 4.5 km too shallow (section 8).
- **The default solver (P0, P1)** brings the down-dip spread close to LDEO's (557–598 m against 520 m).
- **Fault orientation in a plain sentence.** rtDD with cross-correlation shows the swarm as a steep sheet striking
  about N5°W and dipping 86–89° east. That is the same plane LDEO shows (N7°W, 84° E).
  - Its RMS spreads are 0.94 km along strike and 0.56–0.60 km down dip, against 0.86 / 0.52 km in LDEO.
  - It is about 15–20 m thicker (median distance from the plane) than in LDEO. The routine catalog is about 90 m
    thicker.

## 5. Events relocated and dropped (metric e)

- **Relocated:** in every run, 680 of the 685 events, all in one cluster.
- **Dropped:** the same 5 events in every run. Each has fewer than 8 picks. rtDD's default clustering needs at least
  8 neighbours that each share at least 8 phases with the event (minNumPhases 8, minNumNeigh 8). With 6–7 picks
  an event cannot share 8 phases with anyone. Reconstruction in `dropped_events.csv`:

| event | P / S picks | in NCEDC DD | in LDEO |
|---|---|---|---|
| 71098004 | 5 / 1 | no | no |
| 71098214 | 6 / 1 | yes | yes |
| 72536390 | 7 / 0 | yes | yes |
| 72538245 | 7 / 0 | yes | yes |
| 72541935 | 7 / 0 | yes | no |

- **Clustering checks.**
  - No event was lost to the redo loop of the clustering, which drops events whose neighbours were removed.
  - The nearest-neighbour clustering (P0n/S0n/P1n) drops the same 5 events.
- **Phase pairs.**
  - Ellipsoid clustering: 358,474 phase pairs (event pair × station × phase). The first system had 357,531 double
    differences (319,264 P + 38,267 S).
  - Nearest-neighbour clustering: 325,521 pairs, 45 % of them new.
- **Picks with no travel time** (stations beyond 120 km, no grid) are skipped with a warning. They cost no events.
- **Out-of-grid escapes:** no event left the travel-time grids. The log line "relocated, but it is now outside the
  travel time table boundaries" never appears.

## 6. Cross-correlation and residuals (metric f)

**Waveforms used** (P1 and S1 identical):
- 24,223 traces loaded; 8,724 trace requests found no data (pyrtdd proxy counters, scrtdd log).
  - 5,702 asked for a Z channel. 2,680 of these were 1/2/3 borehole sensors, which then succeeded with
    component 1.
  - 3,022 found neither Z nor 1. These are P phases at stations beyond the 60 km waveform radius (60–120 km have
    travel times but no waveforms).
- No disk cache.

**Cross-correlation measurements** (`xcorr_stats.csv`; libhdd's own counts in the logs agree, except that P1's
log counts 173,001 accepted P correlations against 173,002 in its cache: one coefficient written as exactly
0.700000 was presumably just below 0.7 when P1 ran, while the runs that re-use the cache (P1a0, P1d1) count it):

| phase | phase pairs | measured | \|CC\| ≥ 0.7 | of which CC ≥ +0.7 | of which CC ≤ −0.7 | median \|CC\| (measured) | median / 95th percentile \|lag\| of accepted (ms) |
|---|---:|---:|---:|---:|---:|---:|---|
| P | 320,207 | 296,378 | **173,002 (58 %)** | 136,561 | **36,441** | 0.73 | 33 / 287 |
| S (L2) | 38,267 | 35,030 | **19,907 (57 %)** | 19,907 | 0 | 0.72 | 50 / 240 |

"Not measured" means no waveform: 23,829 P and 3,237 S pairs, from stations beyond 60 km and S on vertical-only
sensors. S on L2 (the norm of the two horizontals, a non-negative trace) gave no negative correlation.

P1n (nearest-neighbour pairs), from libhdd's log:
- P: 290,735 pairs attempted, 170,286 (58.6 %) above 0.7;
- S: 34,786 attempted, 19,980 (57.4 %) above 0.7.

Its `xcorr_cache.csv` also holds the P1 entries it was given, so the cache-based counts in `xcorr_stats.csv` for
P1n are larger than its own system.

**Lag sizes by sign of the correlation** (P):

| P measurements | n | median \|lag\| | \|lag\| ≤ 20 ms | \|lag\| ≥ 200 ms |
|---|---:|---:|---:|---:|
| CC ≥ +0.7 | 136,561 | 28 ms | 41 % | 8 % |
| CC ≤ −0.7 | 36,441 | 76 ms | 21 % | 19 % |

The lags are corrections to the analyst differential times. Most analyst picks have weight code 1–2, so 10–20 ms
corrections are normal. Lags ≥ 200 ms are mostly wrong peaks (cycle skips) in a ±0.5 s search.

In the final system:
- 95 % of the positive-CC data keep a weight (median |residual| 10.5 ms);
- 81 % of the negative-CC data keep one (median |residual| 63 ms).

**Double-difference residuals before and after** (libhdd `cluster-1-initial/final-double-difference.csv`;
"weighted RMS" over the data with final weight > 0):

| run | data | initial: n | initial: MAD (ms) | initial: weighted RMS (ms) | final: n with weight > 0 | final: MAD (ms) | final: weighted RMS (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| P0 = S0 | catalog | 357,531 | 51.3 | 101.0 | 329,863 | 27.0 | 38.0 |
| P1 = S1 | all | 357,531 | 55.9 | 110.3 | 316,825 | 23.3 | 31.5 |
| P1 = S1 | cross-correlation | 192,908 | 52.7 | 106.5 | 178,590 | **13.2** | **27.0** |
| P1 = S1 | catalog | 164,623 | 60.1 | 118.1 | 138,235 | 41.8 | 41.3 |
| P1pos | cross-correlation | 156,468 | 47.8 | 94.9 | 148,023 | 10.0 | 20.9 |
| P1n | cross-correlation | 190,266 | 47.5 | 96.5 | 173,228 | 9.4 | 18.5 |

For comparison, the Gwangyang cross-correlation fit reached a MAD of 2.4 ms. Here, events up to 5 km apart are
paired through one 1-D model without station terms, and the analyst picks are coarser.

**Absolute travel-time RMS per event** (rtDD `startRms`/`finalRms`, median over events):
- 235 ms at the NCSS locations;
- 243 ms after P0 and 247 ms after P1;
- 380–389 ms after the pure-DD runs (P0a0/P1a0), whose cluster drifted upward;
- 235–239 ms after the damping-1 runs.

The large starting value shows how poorly the CON grids without station corrections fit the absolute times:

| P picks at | median residual (observed − grid) at the start |
|---|---:|
| 10–40 km | −0.02 to −0.03 s (MAD 0.05–0.12 s) |
| 40–120 km | **−0.42 to −0.56 s** (MAD 0.17–0.28 s) |

## 7. scrtdd against pyrtdd

| pair | event positions: median / 90 % / max 3-D difference (m) | relative (median offset removed): median / 90 % / max (m) | events > 10 m | origin time, max (ms) |
|---|---|---|---|---|
| P0 vs S0 | 0.25 / 0.26 / 7.3 | 0.01 / 0.03 / 7.1 | 0 | 0.3 |
| S0 vs S0nat (plugin vs built-in grid reader) | 0 / 0 / 0 | 0 | 0 | 0 |
| P0 vs P0rep, S0 vs S0rep | 0 / 0 / 0 | 0 | 0 | 0 |
| P0n vs S0n | 0.06 / 0.09 / 1.5 | 0.01 / 0.05 / 1.5 | 0 | 0.1 |
| **P1 vs S1** | **1.1 / 2.5 / 6263** | **0.45 / 2.1 / 6264** | 6 (2 > 100 m) | 333 |

**S0 = P0 in practice, but not to the digit.**
- The clustering gives the same 358,474 phase pairs. 3 of them are listed with the two events in the opposite
  order.
- The initial double differences are identical to the printed microsecond.
- The iteration logs agree to 0.001 ms at iteration 1. The tiny differences then grow over 20 iterations.

What was ruled out:
- each program is deterministic (repeats are bit-identical);
- scrtdd's `tttnll` plugin and its built-in reader give identical results (S0nat);
- the libhdd sources of the two builds are identical (`diff -r`, only test data differ);
- both builds use conda-forge gcc 13.4.0 with the same flags.

What remains is the arithmetic of the two separately built libraries and their bindings. In Gwangyang (11 events)
the two agreed to the digit.

**S1 against P1.**
- **Cross-correlation, triplet by triplet** (`xcorr_triplets_P1_vs_S1.csv`):
  - both programs made the same 358,474 attempts and measured the same 331,408;
  - lags: 324,320 identical (97.9 %); 6,935 differ by one sample (1 ms); 153 by more than 1 ms; 125 by more than
    10 ms (37 P, 88 S);
  - coefficients: median difference 0, 99th percentile 0.001; one P correlation flips sign between the programs
    (BK.BDM: −0.801 in pyrtdd, +0.800 in scrtdd);
  - 62 measurements fall on opposite sides of the 0.7 threshold (14 P, 48 S).
  - This confirms that scrtdd's SeisComP `BW(4,1.5,15)` and pyrtdd's ObsPy band-pass (through the proxy) process
    the same traces almost identically. The S differences come from flat L2 correlation peaks.
- **Positions:**
  - 674 of 680 events within 10 m; median 1.1 m.
  - **Event 72544210** (M 0.82; 8 P and 1 S picks) is 6.3 km apart: P1 puts it at 9.9 km depth near the cluster,
    S1 at 3.8 km depth, 1.2 km to the south-southeast (S35°E).
    - 9 of its lags differ between the two programs: 8 by one sample (1 ms), and its S at NC.CBR with event
      72540100 by more: +28 ms (P1) against −79 ms (S1), at CC 0.738 / 0.737 (two equally high peaks).
    - Both final solutions fit its double differences equally (median |residual| 27 / 25 ms; 403 / 378 data with
      weight).
    - Such an event has two equally good positions and is not determined. LDEO puts it at 7.4 km.
  - **Event 72541385** (M 0.78) is 137 m apart. 4 others are 10–20 m apart.
  - Against LDEO, the medians of section 3 differ by at most 1 m between P1 and S1. The 90th percentiles and the
    centroid shift differ by up to 8 m.

## 8. Sensitivity runs: what moves the cluster, what shapes it

**Absolute position (centroid relative to LDEO, U positive = shallower):**

| solver | catalog only | with cross-correlation |
|---|---|---|
| default, absLocConstraint 0.3, damping 0.01 (P0, P1) | −675 / −95 / **−2346 m** | −826 / −204 / **−2254 m** |
| pure DD, absLocConstraint 0, damping 0.01 (P0a0, P1a0) | +443 / +707 / **+4064 m** | −66 / +427 / **+4451 m** |
| pure DD, damping 1.0 (P0d1, P1d1) | −22 / −49 / −427 m | −16 / −55 / −440 m |
| NCSS start, for comparison | −28 / −55 / −444 m | |

- **The default solver's absolute equations** move the cluster 2.3 km
  deeper and 0.7–0.8 km west. This is probably the CON grids' travel-time bias, but rtDD's own per-event absolute
  RMS does not confirm it as a better fit: it rises slightly, from 235 ms at the start to 243–247 ms. Every catalog with the default solver has a mean depth of 9.5–9.6 km. LDEO's is
  7.3 km, NCSS's 7.7 km and NCEDC DD's 6.6 km (on the common events).
- **Without absolute equations** the cluster drifts upward by over 4 km during the 20 iterations, and the absolute
  RMS rises from 235 to 380 ms. The Gwangyang runs showed the same drift on a smaller scale (up to 1.7 km).
- **Damping 1.0 pins the centroid** to the NCSS start (within 20 m).

**Shape (against LDEO, relative H / V, local H / V, in m):**

| | catalog only | with cross-correlation |
|---|---|---|
| default (P0, P1) | 142 / 134, 137 / 147 | 97 / 105, 51 / 63 |
| pure DD, damping 0.01 (P0a0, P1a0) | 103 / 320, 114 / 215 | **63** / 288, **37** / 100 |
| pure DD, damping 1.0 (P0d1, P1d1) | 133 / 219, 140 / 223 | 84 / 179, 60 / 146 |
| nearest-neighbour clustering (P0n, P1n) | 139 / 154, 130 / 151 | 92 / 123, **41 / 55** |
| positive CC only (P1pos, diagnostic) | | 95 / 90, 50 / 58 |

- **Horizontal shape is best without absolute equations.** P1a0 reaches 63 m relative and 37 m local horizontally.
- **Vertical shape is best with them.** The default solver gives 105 m against 179–288 m without them.
  - The pure-DD solutions keep the vertical stretch of the NCSS start: the down-dip spread is 950 m in P1a0 and
    949 m in NCSS, against 520 m in LDEO.
  - The double differences alone constrain depth differences poorly. At 7–10 km depth only a few stations are
    within one focal depth, and S data are few (11 % of the double differences).
  - The per-event absolute equations add a depth constraint. It is biased in the same way for every event, but it
    compresses this scatter.
  - P1a0 also sits 4.5 km too shallow, which changes the take-off angles.
- **Clustering choice.**
  - Catalog only, nearest-neighbour clustering (P0n) moves events by a median of 46 m relative to P0 (114 events by
    more than 100 m) and the centroid by 0.3 km.
  - The agreement with LDEO is about the same: horizontal 3 m better, vertical 20 m worse.
  - With cross-correlation (P1n), events move by a median of 38 m relative to P1 (76 events by more than 100 m;
    centroid 0.3 km deeper).
  - P1n agrees better with LDEO locally (41 / 55 m against 51 / 63 m) and slightly better horizontally (92 against
    97 m). It agrees worse vertically (123 against 105 m).
  - Nearest-neighbour pairs are closer, so more of them correlate (P: 58.6 % above 0.7, against 54.0 % in P1), and
    the final correlation-residual MAD is lower (9.4 against 13.2 ms).
  - Neither clustering is clearly better overall. The local gain of nearest neighbours costs vertical shape.
- **Negative correlations (P1pos).**
  - Treating the 36,441 negative-CC P measurements as uncorrelated moves events by a median of 38 m relative to P1
    (74 events by more than 100 m).
  - It improves the vertical agreement with LDEO from 105 to 90 m (local 63 → 58 m). Horizontal changes by 2 m.
  - The fit of the remaining correlation data improves (MAD 13.2 → 10.0 ms).
  - This is not an rtDD option. rtDD always accepts |CC| ≥ minCoef.

## 9. Runtime and memory

All runs ran under `nice -n 10` and `prlimit --as=60000000000` on Server A, single-threaded (OMP/OpenBLAS limited to 8;
libhdd uses one core). Wall times are of the whole process; peak memory is the maximum resident set
(`/usr/bin/time -v`).

| run | wall time | CPU (user) | peak memory | notes |
|---|---|---|---|---|
| P0 | 55 s | 52 s | 0.44 GB | clustering 1.3 s, 21 solver passes |
| S0 | 54 s | 49 s | 0.36 GB | |
| **P1** | **27.9 min** | 23.8 min | **1.0 GB** | 358,474 correlations at 1000 Hz; 24,223 traces filtered and resampled in Python |
| **S1** | **19.4 min** | 19.2 min | **0.76 GB** | same correlations, C++ filtering |
| P1n | 15.9 min | 15.7 min | 1.0 GB | 146,242 new phase pairs correlated (22,992 traces processed); P1's results re-used for the rest |
| P0n / S0n | 51 s / 51 s | | 0.40 / 0.32 GB | |
| P0a0 / P0d1 | 59 s / 39 s | | 0.44 GB | |
| P1a0 / P1d1 / P1pos | 73 s / 55 s / 70 s | | 0.67–0.72 GB | correlations read from P1's cache, no waveform read |
| P0rep / S0rep / S0nat | 58 s / 58 s / 51 s | | 0.44 / 0.36 / 0.36 GB | |
| waveform checks | about 2 min (8 processes) | | not measured | `check_waveforms.py` |
| band selection | 11 s (8 processes) | 64 s | 0.22 GB (main process) | |

Memory is dominated by two things:
- the processed 1000 Hz waveform snippets kept in memory (about 24,000 traces);
- the double-difference system (357,000 rows with 8 non-zero entries each).

Both grow with the number of phase pairs. At about 1 GB for 685 events, the 60 GB limit is far away.

## 10. Caveats

- **Different velocity models and datums.**
  - Our grids: the single CON gradient model, stations at their real elevation, model top shifted to 0.29 km above
    sea level, Vp/Vs 1.73, **no station corrections**.
  - LDEO: the NCSN 1-D models (39 local models, each resampled to 28 layers), geoid depths.
  - NCSS: regional models plus station delays.
  - NCEDC DD (DD-RT): depths below a local datum, converted here with each event's NCSS datum, which is an
    approximation.
  - Absolute positions are not expected to agree to better than a few hundred metres. rtDD's default absolute
    equations magnify the model bias into a 2.3 km depth shift.
- **DD-RT against NCAeqDD.**
  - The NCEDC DD positions of these 2015 events are automatic real-time DD-RT solutions, made relative to the base
    catalog and not reviewed.
  - LDEO v202112.1 is a full joint re-inversion with cross-correlation (2022).
  - They differ from each other by more than our P1 differs from LDEO, so NCEDC DD is a weak secondary reference.
- **Analyst picks.**
  - All picks are NCSS analyst picks with 0.01 s resolution. Weight codes 1–2 (0.1–0.2 s) are the majority.
  - LDEO used the same network's P picks (no S) plus correlation. The catalog data are therefore not independent
    of the reference.
  - rtDD used all weight 0–3 picks with equal weight (usePickUncertainties false, the default). 617 picks are more
    than 1 s off; rtDD's residual down-weighting handles them.
- **Vertical-only stations and S.**
  - 42 of the 246 sensors within 60 km are vertical-only. Their 83 S picks cannot be correlated on L2.
  - 44 % of the S picks are on strong-motion HN channels, triggered recorders with occasional short records
    (`docs/sanramon_waveforms.md`).
  - S makes up only 11 % of the double differences, which limits depth resolution.
- **Stations beyond 120 km** (937 usable P picks) have no travel-time grid and are skipped. Waveforms exist only
  within 60 km.
- **Poorly constrained small events can jump** between equally good positions on a single measurement (72544210:
  6.3 km between P1 and S1). With 8–9 picks, such events should be treated with caution in any rtDD catalog.
- **The metrics are statistics over 680 events.**
  - The centroid (a) and the plane (d) use all common events, including the 5 events of the small SE-edge cluster
    and the poorly located ones. Medians are given next to RMS values for that reason.
  - The local metric uses LDEO's 10 nearest neighbours (median spacing 107 m).
- **Choices made before looking at the results:**
  - the 1.5–15 Hz band (from the SNR spectra);
  - the P component list Z, 1 (from the channel naming);
  - 1000 Hz resampling (as in Gwangyang);
  - TRANS_MERC grids (recommended in `docs/sanramon_inputs.md`).

  Nothing was tuned against the references. All variants run are in the tables above.
- **pyrtdd P1 uses our proxy workaround** for the filter bug. Its agreement with scrtdd (97.9 % identical lags)
  shows that the workaround reproduces what scrtdd does natively.

## 11. Files

| file | content |
|---|---|
| `runs/sanramon/pyrtdd/run_pyrtdd_sanramon.py` | pyrtdd driver (parameters at the top, dry run by default) |
| `runs/sanramon/pyrtdd/<run>/` | `options.json` (every option, read back from libhdd), `run_info.json` (status, time, memory, counters), `console.log`, `processing/` (libhdd's own output: `relocation.log`, `cluster-1-pair.csv`, `cluster-1-{initial,final}-double-difference.csv`, `xcorr.csv`, ...), `clusters/`, `xcorr_cache.csv`, `relocated-{event,phase,station}.csv`; P1pos also `inputs/xcorr_cache_positive_only.csv` |
| `runs/sanramon/scrtdd/scrtdd_sanramon.py`, `scrtdd_common_sanramon.py` | scrtdd driver and settings (copy of the Gwangyang helpers, San Ramon values) |
| `runs/sanramon/scrtdd/inputs/inventory_sc.xml` | `fdsnxml2inv` conversion of `stations.xml` (log `fdsnxml2inv.log`) |
| `runs/sanramon/scrtdd/<run>/` | `seiscomp_user/{global,scrtdd}.cfg`, `run_options.json` (every value scrtdd used), `run_summary.json`, `time_v.txt`, `work/` (`reloc-*.csv`, `relocated.xml`, `scrtdd.log`, `multievent_*/` diagnostics) |
| `runs/sanramon/analysis/analyze_sanramon.py` | all comparisons |
| `runs/sanramon/analysis/metrics_vs_reference.csv`, `per_event_vs_reference.csv` | metrics a–c per solution and reference, and per event |
| `runs/sanramon/analysis/plane_fit.csv` | metric d |
| `runs/sanramon/analysis/dropped_events.csv` | metric e |
| `runs/sanramon/analysis/xcorr_stats.csv`, `residual_stats.csv` | metric f |
| `runs/sanramon/analysis/run_vs_run.csv`, `xcorr_triplets_P1_vs_S1.csv` | run against run |
| `runs/sanramon/analysis/runtime.csv`, `positions_enu.csv`, `summary.json` | runtime and memory, all positions, everything in one file |
| `runs/sanramon/waveforms/band_selection.py`, `band_snr_*.csv/json` | band choice |
| `docs/sanramon_waveforms.md` | waveform checks |
| `logs/11_sanramon_*` | run logs |
