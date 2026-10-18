# How the Gwangyang reference run was made

This note explains, in plain words, every setting of the reference run that the rtDD and DL-picker
tests are compared with. Each value is quoted with a `file:line` reference. Paths are relative to
`data/gwangyang_11ev/`:

- `reference/gwangyang_pnplus/` holds the run's outputs (read-only copy from server B).
- `reference/pipeline_code/` holds the code that made it (md5-identical to server B on 2026-10-17).
- `reference_supplement/` holds 5 small files from server B that the reference copy lacks: the
  cluster configuration, the command-line front ends and the KMA catalog (see its `PROVENANCE.md`).

Short names used below:

- `cfg` = `reference_supplement/pipeline_code_extra/clusters/gwangyang.py`
- `core/` = `reference/pipeline_code/core/`
- `run/` = `reference/gwangyang_pnplus/`

## 0. What the run is

The run is `runs/gwangyang_pnplus` of the earthquake-cycle relocation pipeline on server B. It was made
on 2026-05-28; the bootstrap error estimates were added on 2026-05-29. It is the Gwangyang cluster
configuration with one change: the picker was switched from SeisBench PhaseNet to **PhaseNet+**.

- The pipeline offers this switch as `--picker phasenet_plus`
  (`reference_supplement/pipeline_code_extra/cli/run_pipeline.py:34-42`).
- The output folder name `gwangyang_pnplus` comes from the run suffix `_pnplus` that
  `cli/bootstrap.py:36-45` and the results notebook use.
- The pick tables prove PhaseNet+ was used. They have `Polarity` and `Amplitude` columns, which
  only the PhaseNet+ code writes (`core/picking.py:156-160`). Their lowest probability is 0.301,
  just above the PhaseNet+ threshold of 0.3 (`reference/pipeline_code/config.py:56`).
- `cfg:73-76` still says "PhaseNet 'stead', 1-40 Hz, threshold 0.2". Those settings belong to the
  SeisBench path and were not used.

The chain runs in this order (`core/pipeline.py:23-24`). Each step is explained below.

1. Station selection
2. Waveform gathering
3. PhaseNet+ picking
4. HYPOINVERSE location
5. ph2dt
6. HypoDD with catalog times only (`2.HypoDD/01.dt.ct`)
7. Re-referencing of the SAC origin times
8. Cross-correlation
9. HypoDD with cross-correlation times (`2.HypoDD/02.dt.cc`)
10. Bootstrap errors

## 1. Events and ids

- **Events.** The 11 events come from the KMA catalog (`reference_supplement/kma_catalog/event_catalog.csv`,
  times in KST). Each event id is the KMA origin time converted to UTC (KST - 9 h), written
  `YYYYMMDDhhmmss` (`core/waveforms.py:26-46`; `cfg:59`). Example: the ML 2.2 event at 2021-08-28
  07:03:22 KST is `20210827220322`.
- **HypoDD ids.** The HypoDD id is 200000 plus the position of the event folder in sorted order
  (`core/hypoinverse.py:114`; `reference/pipeline_code/config.py:203`). So `20210720161418` is
  200000 and `20260204054406` is 200010.
- **rtDD ids.** The rtDD catalog uses 1..11 (rtDD id = HypoDD id - 199999). The full map is in
  `inputs/rtdd_catalog/event_id_map.csv`.

## 2. Station selection

1. Take all KS-network stations within 100 km of 35.00 N 127.72 E (`cfg:55-57`; `core/stations.py:60-69`).
   That gives 90 stations (`run/station_table/kma_stations_100km.csv`).
2. Keep the stations that have a vertical-component file in the KMA event archive for at least one
   event. That gives 54 (`run/station_table/used_stations_100km.csv`).
3. Each station gets exactly one sensor: broadband HH if it has one; else short-period EL; else
   accelerometer HG (`core/stations.py:73-101`, lines 88-97).
   - Result: 17 HH, 5 EL and 32 HG stations.
   - No KG-network station was used.
4. A station is not required to have data for every event. The 2021 events have 52-53 stations and
   the 2026 events have 47.

## 3. Waveforms

`core/waveforms.py:50-77` copies the KMA event-archive SAC files of the chosen sensor
(`cfg:64-68`) into `waveforms_100km/<event>/<event>.<NET>.<STA>.<CHA>.sac`.

- **Headers written.** Event location (`evla`/`evlo`, from the KMA catalog), station location
  (`stla`/`stlo`, from the station table) and the reference time (the KMA origin).
- **Not done.** No filtering, no instrument correction, no rotation, no trimming. The windows are
  the ~460 s windows of the KMA archive.
- **Not set.** `cmpaz`/`cmpinc` (component orientation) and `khole` (location code) are never set.

## 4. Picking (PhaseNet+)

- **Model and input.** The EQNet PhaseNet+ model runs on the raw 3-component data with no high-pass
  filter. It uses weights `model_99.pth`, a pick threshold of 0.3, and 36864-sample patches
  (`reference/pipeline_code/config.py:53-58`). The SAC files are turned into temporary miniSEED
  files, and one network pass picks all stations of an event (`core/eqnet_backend.py:90-147`).
- **Which picks are kept** (`core/picking.py:105-163`):
  - **Search window.** A pick must fall between origin + R/5.9 - 1 s and origin + R/3.0 + 4 s.
    R is the hypocentral distance for an assumed 15 km depth: R = sqrt(epicentral distance² + 15²)
    (`cfg:78`; `core/picking.py:113, 136-139`). The origin is the KMA catalog time.
  - **P and S pair.** Among all P-S pairs with 0 < S-P < 15 s, the pair with the largest summed
    probability wins (`cfg:77`; `core/picking.py:144-146`). If there is no such pair, the most
    probable P and/or the most probable S after P is kept (`core/picking.py:147-152`).
  - **Saved where.** The pick times go into the SAC headers (`a` = P, `t0` = S) of all 3 components
    (`core/picking.py:167-186`) and into `run/picks/<event>_picks.csv`.
- **Result.** 763 picks (360 P, 403 S).

## 5. Absolute location (HYPOINVERSE)

- **Phase file.** `core/hypoinverse.py:70-115` writes `run/1.HypoInv/PHS/Gwangyang.phs` from the SAC
  headers. The P pick is attached to the Z channel and the S pick to the first horizontal file,
  which is always N.
  - **Pick times are cut, not rounded, to 0.01 s** (`core/hypoinverse.py:102, 111`). The catalog pick
    times are therefore 0-10 ms earlier than the PhaseNet+ times (median 3 ms).
  - **Pick weights depend on the distance from the KMA epicenter** (`reference/pipeline_code/config.py:182-186`):

    | | < 20 km | 20-50 km | 50-70 km | 70-100 km | ≥ 100 km |
    |---|---|---|---|---|---|
    | P weight code | 0 | 1 | 2 | 3 | 4 |
    | S weight code | 1 | 2 | 3 | 3 | 3 |

- **Station file.** `core/hypoinverse.py:41-66` labels every station "HHZ" and gives every station
  **elevation 0**.
- **Control settings** (`cfg:81-84`; template `core/hypoinverse.py:141-164`):
  - CON 50 = up to 50 iterations.
  - MIN 4 = at least 4 stations.
  - ZTR 10 F = trial depth 10 km, depth free.
  - DIS 4 50 1 3 = distance weighting.
  - RMS 4 0.12 2 4 = residual weighting.
  - ERF T, TOP F, LST 2 0 1, KPR 3, H71 4 1 3.
- **Velocity models.** The events were located with two models, kim1983 and kim2011 (`cfg:85-94`).
  The **kim1983** `.arc` file feeds ph2dt (`cli/run_pipeline.py:25-27`, default `--arc-velmodel kim1983`).

## 6. ph2dt (catalog differential times)

`core/hypodd.py:84-106` prepares the input:

1. Copy the kim1983 `.arc` file.
2. Move the S-pick flag where HypoDD expects it (`core/hypodd.py:34-43`).
3. Convert the file with `ncsn2pha` to `Gwangyang.pha`.
4. Fix the longitude sign. `ncsn2pha` assumes west longitudes, so the minus sign is removed
   (`core/hypodd.py:46-59`).
5. Copy the result to `Gwangyang_mod.pha` (`core/hypodd.py:97`).
6. Write `station.dat` (`core/hypodd.py:62-71`).
7. Write `ph2dt.inp`, which reads `Gwangyang_mod.pha` (`core/hypodd.py:103`;
   `run/2.HypoDD/00.ph2dt/ph2dt.inp:5`).

**Why there are two `.pha` files.** In the original hand-made workflow the longitude sign was
corrected by hand and saved as `_mod.pha`. The pipeline now makes that correction in `Gwangyang.pha`
and copies it, only to keep the old file name. The two files are byte-identical
(md5 12510e1e2d86e3b0c0ee92e74c0172cc).

`run/2.HypoDD/00.ph2dt/ph2dt.inp:7`:

| setting | value | meaning |
|---|---|---|
| MINWGHT | 0 | keep picks of any weight |
| MAXDIST | 200 km | largest event-station distance used (all stations are within 100 km) |
| MAXSEP | 10 km | largest distance between two events that may be paired |
| MAXNGH | 200 | largest number of neighbours per event (all 10 others are taken) |
| MINLNK | 1 | one shared pick is enough to call two events neighbours |
| MINOBS | 1 | smallest number of shared picks for a pair to be written |
| MAXOBS | 500 | largest number of shared picks per pair (never reached) |

**Pick weights.** The weights in the `.pha` file are 1.0, 0.5, 0.2 and 0.1 for HYPOINVERSE weight
codes 0, 1, 2 and 3. Each `dt.ct` line carries the **mean** of the two pick weights; this was
checked on all 2729 lines.

**Result** (`run/2.HypoDD/00.ph2dt/ph2dt.log:6, 82-90`):

- 763 picks went in.
- ph2dt formed 1226 P and 1575 S travel-time differences.
- 72 differences (2 %) were removed. Each was larger than the event separation allows and is
  listed as "Outlier" in `ph2dt.log`.
- 1181 P and 1548 S differences remain.
- `dt.ct` holds all 55 event pairs. The log prints "linked event pairs = 56".

## 7. HypoDD with catalog times only (`run/2.HypoDD/01.dt.ct/hypoDD.inp`)

| line | value | meaning |
|---|---|---|
| 4 | (blank) | no cross-correlation file |
| 6, 8, 10 | `dt.ct`, `event.dat`, `station.dat` | input files |
| 24 | IDAT 2, IPHA 3, DIST 500 | catalog data only, P and S, stations up to 500 km from the cluster centre |
| 26 | OBSCC 0, OBSCT 0 | no clustering (all events form one cluster) |
| 28 | ISTART 1, ISOLV 1, NSET 5 | **all events start at the cluster centroid**; SVD solver; 5 iteration sets |
| 30-34 | see below | iteration sets (4 iterations each) |
| 36-40 | NLAY 3, RATIO 1.73, TOP 0 15 32, VEL 5.98 6.38 7.95 | velocity model (section 11) |
| 42 | CID 0 | relocate all clusters |

The 5 iteration sets keep the catalog weights at P 1.0 and S 0.5. Each set throws out more outliers
and allows less distance between paired events:

| set | iterations | outlier cutoff (WRCT) | largest event separation (WDCT) |
|---|---|---|---|
| 1 | 1-4 | none | no limit |
| 2 | 5-8 | 8 x the spread of the residuals | 6 km |
| 3 | 9-12 | 6 x | 4 km |
| 4 | 13-16 | 5 x | 3 km |
| 5 | 17-20 | 3 x | 1 km |

- The cross-correlation weights in these lines (0.01/0.005) have no effect here, because there is
  no cross-correlation file.
- DAMP 8 has no effect with the SVD solver; it is used only by LSQR.
- **ISTART=1 means HypoDD does not start from the `event.dat` locations.** It averages them into one
  centroid, 34.999695 N 127.728889 E 13.942727 km (`run/2.HypoDD/01.dt.ct/hypoDD.log:51`), and starts
  all 11 events there. The `event.dat` origin times are kept.

## 8. Re-referencing the SAC origin times

`core/rereference.py:38-69` runs after the catalog relocation (`core/pipeline.py:60-62`).

- It sets every SAC reference time to the kim1983 HYPOINVERSE origin
  (`run/1.HypoInv/kim1983/Gwangyang.sum`, 0.01 s precision).
- It re-expresses `a`/`t0` relative to that origin.
- Absolute pick times and sample times do not change. The SAC files in the reference copy are in
  this re-referenced state (modified 2026-05-28 15:21:47).

## 9. Cross-correlation (`dt.cc`)

The code is `core/xcorr.py`. The settings are `cfg:122-126`, which are merged into the defaults at
`core/xcorr.py:234-239`.

| item | value | where |
|---|---|---|
| traces used | the raw SAC files of the station's one sensor: `{event}.*.{station}.*{comp}.sac`, first match | `core/xcorr.py:67` |
| P component | **Z** | `core/xcorr.py:128-146` (line 135) |
| S component | **N and E separately; the one with the higher coefficient wins** (ties go to E) | `cfg:123`; `core/xcorr.py:149-172` (lines 157-162) |
| rotation / orientation correction | **none**: raw N and E as recorded, no turn to radial/transverse, no misorientation correction | `core/xcorr.py:62-78`; `rotation.py`/`misorientation.py` are not in the chain (`core/pipeline.py:23-24`) |
| pre-processing of the whole ~460 s trace | resample 100 → **1000 Hz** (Lanczos, a=20); remove mean; 5 % taper; band-pass **5-20 Hz**, 4 poles, zero-phase (forward and backward); remove mean; 5 % taper | `core/xcorr.py:70-74`; `cfg:122` |
| window | **0.5 s before to 0.5 s after** the pick (`a` for P, `t0` for S) | `cfg:122`; `core/xcorr.py:94` |
| exception: any pair with the ML 2.2 event `20210827220322` | window **0.05 s before to 0.05 s after** the pick, band **1-40 Hz** (a hand-tuned choice; it leaves that event with fewer cc data: 48 P + 65 S in the final run, others 66-196 P) | `cfg:124-126`; `core/xcorr.py:105-115` |
| search | the second event's window is slid by -0.5 ... +0.499 s in **1 ms steps** (`margin` 0.5, `slide_step` 0.001). At each step `obspy` `correlate(..., shift=500 samples)` plus `xcorr_max(abs_max=False)` finds the best positive correlation within ±0.5 s; the step with the highest coefficient wins | `core/xcorr.py:88-102`; `core/xcorr.py:234-236` |
| largest delay that can be found | up to about ±1 s (slide ±0.5 s plus shift ±0.5 s) | `core/xcorr.py:97-102` |
| sub-sample precision | from the 1000 Hz resampling and the 1 ms slide grid only (no peak interpolation); delays rounded to 1 ms | `core/xcorr.py:102` |
| differential time written | (t1 + delay - origin1) - (t2 - origin2), using the re-referenced origins | `core/xcorr.py:138-140, 164-166` |
| weight written | the correlation coefficient itself (3rd column of `dt.cc`) | `core/xcorr.py:118-120` |
| threshold | keep 0.7 ≤ coefficient ≤ 1.0 | `cfg:123`; `core/xcorr.py:186-191` |
| event pairs / stations | all 55 pairs; every station where both events have a pick | `core/xcorr.py:222-232` |

Data counts:

- Measured: 1226 P and 1575 S (`run/2.HypoDD/02.dt.cc/dt.cc_P/`, `dt.cc_S/`).
- After the 0.7 threshold: **1017 P and 1509 S** (`dt.cc_0.7_combined`, 110 pair headers).
- A variant without the ML 2.2 pairs also exists (`dt.cc_0.7_combined_no_main`; `cfg:111-114`),
  but the reference result does not use it.

## 10. HypoDD with cross-correlation times (`run/2.HypoDD/02.dt.cc/hypoDD.inp`)

| line | value | meaning |
|---|---|---|
| 4, 6 | `dt.cc_0.7_combined`, `dt.ct` | both kinds of data |
| 24 | IDAT 3, IPHA 3, DIST 500 | cross-correlation + catalog data, P and S |
| 26 | OBSCC 4, OBSCT 0 | an event pair counts as linked when it has at least 4 observations (the log reports "min. number of links set to 4": `hypoDD.log:59`); all 11 events form one cluster |
| 28 | ISTART 1, ISOLV 1, NSET 7 | start all events at the centroid (`hypoDD.log:67`: 34.999695 N 127.728889 E 13.942727 km); SVD; 7 sets |
| 30-36 | see below | iteration sets |
| 38-42 | NLAY 3, RATIO 1.73, TOP 0 15 32, VEL 5.98 6.38 7.95 | velocity model |
| 44 | CID 0 | all clusters |

The iteration sets have 4 iterations each, 28 iterations in all:

| set | iterations | what drives the fit | outlier cutoff | largest pair separation | cc observations kept (last iteration of the set, from `hypoDD.log`) |
|---|---|---|---|---|---|
| 1 | 1-4 | catalog (P 1.0, S 0.8); cc weight 0.01/0.005 | none | no limit | 2526 |
| 2 | 5-8 | catalog | catalog: 8 x spread | 6 km | 2526 |
| 3 | 9-12 | catalog | catalog: 6 x spread | 4 km | 2526 |
| 4 | 13-16 | **cross-correlation** (P 1.0, S 0.8); catalog 0.01/0.005 | cc: 6 x spread (0.127 → 0.014 s) | 4 km | 2040 |
| 5 | 17-20 | cross-correlation | cc: 4 x spread (0.009 s) | 2 km | 1984 |
| 6 | 21-24 | cross-correlation | cc: 3 x spread (0.006-0.007 s) | 1 km | 1853 |
| 7 | 25-28 | cross-correlation | cc: 2 x spread (0.003-0.004 s) | 0.5 km | **1472** |

- The catalog data stay in with weights 0.01 (P) and 0.005 (S): 2645 observations in the last
  iteration.
- DAMP (8, then 6) has no effect with SVD.
- In the last iteration the cc rms is 1.3 ms and the catalog rms 42 ms (`hypoDD.log`, iteration 28).
- `hypoDD.log:45-53` counts the input as 1017/1509 cc and 1181/1548 catalog differences. Only 53 of
  the 54 stations have data, because station JNHA has a single pick (event 9) and so pairs with
  nothing.

## 11. Velocity model (kim1983)

| layer top (km) | Vp (km/s) | Vs in HYPOINVERSE (km/s) | Vs in HypoDD = Vp / 1.73 |
|---|---|---|---|
| 0 | 5.98 | 3.40 | 3.457 |
| 15 | 6.38 | 3.79 | 3.688 |
| 32 | 7.95 | 4.58 | 4.595 |

Sources: `cfg:86-89`; `run/1.HypoInv/kim1983/Gwangyang.prt` (model listing); `hypoDD.inp:38-42`.

- HYPOINVERSE uses its own S model, whose Vp/Vs ratio is 1.76, 1.68 and 1.74 by layer. HypoDD uses a
  constant 1.73. The two programs therefore have slightly different S velocities.
- Both treat stations as sitting at depth 0, because elevations were set to 0 (section 5) and
  HypoDD's `station.dat` has no elevation.

## 12. Bootstrap errors (`final_locations.csv`)

`core/hypodd.py:466-578` re-runs HypoDD 1000 times. The header of
`run/2.HypoDD/02.dt.cc/bootstrap_errors.csv:1` reads
"n=1000 seed=0 branch=dtcc resample=global ci=percentile2.5-97.5 align=median init=solution".

Each replica does the following:

1. Draw the differential-time observations at random, with replacement, from the pooled `dt.ct` and
   `dt.cc` data.
2. Keep the `hypoDD.inp` settings fixed.
3. Start from the final solution.
4. Shift the result so that its median position matches the main solution.

The error columns `ex95_m`/`ey95_m`/`ez95_m` are half the width of the 2.5-97.5 % range of the
replica positions. The `magnitude` column of `final_locations.csv` is the KMA ML.

## 13. Notes for setting up rtDD to mimic this run (suggested, not yet tested)

| reference | closest rtDD setting |
|---|---|
| kim1983, Vp/Vs 1.73 | NonLinLoc grids of step C1 (`inputs/nll_kim1983`) |
| start at the centroid (ISTART=1) | `inputs/rtdd_catalog/event_centroid_start.csv` (rtDD always starts from the catalog positions) |
| catalog weights P 1.0 / S 0.8, pick weights 1.0-0.1 | rtDD weights picks by uncertainty classes only when `usePickUncertainties` is on; the catalog leaves uncertainties blank |
| cc P on Z | `XcorrOptions.phase[P].components = ["Z"]` |
| cc S on N or E, best of the two, no rotation | no exact equivalent. rtDD's component list is a fallback order, not "best of". `["L2"]` (the default) combines N and E and does not depend on the sensor orientation |
| window -0.5 / +0.5 s | `startOffset = -0.5`, `endOffset = 0.5`, `winScaling = 0` |
| max delay ~±1 s | `maxDelay` (rtDD default 0.5 s) |
| 5-20 Hz band on 1000 Hz traces | `cfg.wfFilter.filterStr = "bandpass;freqmin=5;freqmax=20;corners=4"` (pyrtdd obspy proxy); `resampleFreq = 1000`. The proxy turns every filter value into a number (pyrtdd `obspy/waveform.py` `filter()`), so `zerophase=True` cannot be passed and the filter runs one way only. The reference ran it forward and backward (zero-phase). `corners=4.0` was checked to work with obspy 1.5.1 / scipy 1.18.1 |
| cc ≥ 0.7 | `minCoef = 0.7` |
| distance cutoffs per set | rtDD has no distance cutoff; it down-weights by residual (`downWeightingByResidualStart/End`) |
