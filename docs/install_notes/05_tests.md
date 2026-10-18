# Step T: unit tests and a smoke test of the deep-learning picker (2026-10-17)

## Result

- **scrtdd's own unit tests all pass: 7 of 7.** These are 5 `test_hdd_*` tests for the relocation
  library libhdd and 2 `test_hddsc_*` tests for its SeisComP connection, with 898 individual test cases
  inside them. First I made the NonLinLoc test grids they need, as scrtdd's README says: 10 grid sets,
  3.5 GB, 72 s.
- **The SeisComP test suite: 44 of 44 tests run, 44 passed, 0 failed.** 8 of the 52 compiled tests were
  not run on purpose, because they start network servers: a web service on port 9980 of all network
  interfaces, and messaging servers. This project must not start servers on the shared server Server A. None
  of the 8 concern scrtdd or scdlrtpicker.
- **scdlrtpicker has no unit tests of its own.** scrtdd has none for its programs and plugins, only for
  the two libraries above. The real check of the picker is the smoke test below.
- **The 49 deep-learning models** that come with scdlrtpicker are listed in `docs/dlrtpicker_models.txt`,
  together with what SeisBench says about each one's training data. Recommended for Gwangyang:
  **phasenet_instance** (used in the smoke test), **phasenet_stead**, **eqtransformer_stead** and
  **phasenet_original** (reasons in section 3).
- **Smoke test: the deep-learning picker works inside SeisComP.** I ran scautopick with DL3C/SDL3C and
  `phasenet_instance.onnx` offline on the ML 2.2 event of 2021-08-27 22:03:22 UTC (46 stations, 9
  minutes of data). It took **0.8 s**. It made **51 P and 46 S picks**. It found **all 45 P and all 43 S
  PhaseNet+ picks** at the stations it could use:
  - P: median time difference 0.020 s, largest 0.070 s.
  - S: median time difference 0.060 s, largest 0.175 s.

  The remaining picks were 6 P and 3 S without a PhaseNet+ partner: near-duplicates, single-station
  picks before or after the event, and one plausible S that PhaseNet+ did not pick. They are explained
  in section 4. The other three recommended models also load and run; on this event they found 41–43
  of the 43 S picks and 44–45 of the 45 P picks.
- **ONNX Runtime's usage telemetry** (built into the official 1.31.0 release) was found and switched off
  with `ORT_DISABLE_TELEMETRY=1`; see "Problems" item 5.
- Nothing was patched or installed:
  - No source code was patched and no conda package was added.
  - Nothing was written outside the project.
  - `~/.seiscomp` was never created.

## 1. scrtdd's unit tests

### The NonLinLoc test grids

Several scrtdd tests compute travel times from NonLinLoc grids. The grids are too large for git, so
scrtdd ships only their recipes (`libs/hdd/test/data/nll/iasp91_*/run/`). Its README ("Tests") asks you to
generate them before testing:

```bash
export PATH=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/NonLinLoc/bin:$PATH   # NonLinLoc v7.00.16 (step C1)
cd software/src/seiscomp/src/extras/scrtdd/libs/hdd/test/data/nll
./generate.ch       # run by the script as 'nice -n 10 sh ./generate.ch' (the file has no '#!' line)
```

- **What was made:** 10 grid sets.
  - Model: iasp91, in 2-D and in 3-D.
  - Map projections: five (SIMPLE, SDC, AZIMUTHAL_EQUIDIST, MERC, LAMBERT).
  - Coverage: 16 test stations, P and S, travel time and take-off angle.
- **Files:** each `time/` folder holds 132 files: 16 × 2 × 2 grids, each a .hdr and a .buf file (128),
  plus the copy of the P and S velocity grids that Grid2Time puts there (4). Each `model/` folder holds
  4 files.
- **Size and time:** 3.5 GB in total (each 3-D set is 0.2–1.1 GB). Generation took 72 s, and NonLinLoc
  printed no error.
- **The hddsc tests need no grids of their own.** `libs/hddsc/test/data/nll` is a symbolic link to
  `../../../hdd/test/data/nll` and is part of scrtdd's git tree. The script checks that it resolves to
  the same folder.
- **Source tree afterwards:** `git status` in the scrtdd tree shows only the 20 new `model/` and `time/`
  folders, and no changed file.

### The tests

`ctest -N` lists exactly 7 tests whose name contains "hdd", and none whose name contains "rtdd". I ran
them in the build folder, in the SeisComP environment:

```bash
ctest -R hdd --output-on-failure --timeout 600
```

| test | what it checks (plain words) | test cases | result | time |
|---|---|---|---|---|
| test_hdd_ellipsoid | the ellipsoid geometry used to choose neighbouring events | 21 | **Passed** | 0.01 s |
| test_hdd_ttt | the constant-velocity model and the 10 NonLinLoc grid sets give the same travel times, derivatives and take-off angles | 36 | **Passed** | 5.3 s |
| test_hdd_clustering | choosing neighbour events and forming clusters | 65 | **Passed** | 0.02 s |
| test_hdd_dd | relocating synthetic catalogs (many events at once, and one event at a time) around 10 centroids with every travel-time table: each event must end up where it should | 660 | **Passed** | 339.5 s |
| test_hdd_waveform | synthetic traces: resampling and cross-correlation delays | 15 | **Passed** | 0.4 s |
| test_hddsc_ttt | SeisComP's own travel-time tables (LOCSAT, libtau, homogeneous), used through scrtdd, agree with scrtdd's native ones | 60 | **Passed** | 1.7 s |
| test_hddsc_waveform | miniSEED read/write through SeisComP, filters, resampling, cross-correlation of real records | 41 | **Passed** | 0.5 s |

**100% tests passed, 0 tests failed out of 7**, in 347.7 s in total. The log is
`runs/05_tests/ctest_hdd.log`, and the per-test output is in `runs/05_tests/ctest_hdd_junit.xml`.

- The number of test cases is the "Running N test cases" line of each program, 898 in total.
- A test program passes only if every one of its test cases passes.
- `test_hdd_dd` is slow (5.7 minutes, on one core). That is why the 600 s limit leaves room, but not much.

One limit is worth knowing: the SeisComP plugin `tttnll.so` itself is not exercised by these unit tests.

- In scrtdd v2.0.10, `test_hddsc_ttt` lists the NonLinLoc grids under their SeisComP name "NLLGrid".
- It then keeps only the entries named "homogeneous" or "tttnll", so the NLLGrid entries are dropped.
- The grids themselves are tested through libhdd's own reader, in `test_hdd_ttt` and `test_hdd_dd`.
- The plugin gets its first real use when scrtdd relocates the Gwangyang events in a later step.

## 2. The complete SeisComP test suite

The command, run in the build folder with the SeisComP environment, and with `HOME` and the per-user
folder inside the project:

```bash
ctest -j8 -E '^(test_fdsnws_.*|scevent-remote)$' --output-on-failure --timeout 600 \
      --output-junit runs/05_tests/ctest_full_junit.xml
```

| | number |
|---|---|
| tests compiled (`ctest -N`) | 52 |
| run | 44 |
| **passed** | **44** |
| **failed** | **0** |
| not run on purpose | 8 (listed below) |

The whole run took 333.9 s, almost all of it `test_hdd_dd` (333.7 s). The log is
`runs/05_tests/ctest_full.log`.

With `-E`, ctest numbers the selected tests 1 to 44 instead of keeping their numbers from `ctest -N`.
This only changes the labels.

There were no failures, so there is nothing to classify. The 8 tests that were not run start network
servers. Leaving them out follows the project rule for the shared server (no daemons, no open ports).
It is not a problem of the installation.

| test | why it was not run | related to scrtdd or scdlrtpicker? |
|---|---|---|
| test_fdsnws_static, test_fdsnws_event, test_fdsnws_station, test_fdsnws_station_conditional, test_fdsnws_station_precision, test_fdsnws_dataselect, test_fdsnws_availability | Each one starts SeisComP's FDSN web service (`fdsnws.py --port=9980`). It listens on **all network interfaces** (0.0.0.0). | No. They test the FDSN web service. |
| scevent-remote | It starts two `scmaster` messaging servers (127.0.0.1:9981 and 9982) and two `scevent` processes with REST servers (127.0.0.1:9991 and 9992). | No. It tests how two scevent instances share event IDs. |

To run these 8 anyway, use `ctest -R '^(test_fdsnws_.*|scevent-remote)$'` in the build folder. Port 9980
would then be open to the network for a few seconds per test.

- **Which build was tested:** the tests ran from the build tree (`software/build/seiscomp/bin`). That
  is the same build that step A installed.
- **Source trees afterwards:** the tests wrote nothing into them. `git status` is clean in the seiscomp,
  common, main, seedlink, extras and scdlrtpicker repositories. Only scrtdd shows the grid folders from
  section 1.

## 3. The 49 deep-learning models that come with scdlrtpicker

`docs/dlrtpicker_models.txt` has three parts:

1. The comparison table printed by the plugin's own `models/show_model_info.py *.onnx`. I ran it in env
   `pyrtdd`, which has `onnx` 1.23.2. It is identical to the snapshot `models/table.txt` that ships with
   the plugin.
2. The full `show_model_info.py <file>` block for every model.
3. For each model, what SeisBench says about the weights it was exported from:
   - the training data and the reference to cite;
   - SeisBench's own pick thresholds;
   - the preprocessing SeisBench applies.

   `install/05_seisbench_weight_info.py` downloads this part from SeisBench's public server. It fetches
   only the small JSON description files, no model weights.

Each file is named `<architecture>_<training data>.onnx`. All 49 models take three components. None of
them gives a time uncertainty, and only `eqtp_ncedc` gives the first-motion polarity.

| architecture | files (training data) | window | sample rate | normalization | outputs |
|---|---|---|---|---|---|
| PhaseNet | 16: aq2009, diting, ethz, geofon, instance, iquique, jma, jma_wc, lendb, neic, original, phasenet_sn, pisdl, scedc, stead, volpick | 3001 samples = 30 s | 100 Hz (diting: 50 Hz, so 60 s) | peak; std for original, phasenet_sn, jma, jma_wc, aq2009, diting | P, S, noise |
| PhaseNetLight | 8: ethz, geofon, instance, iquique, lendb, neic, scedc, stead | 30 s | 100 Hz | peak | P, S, noise |
| EQTransformer | 11: ethz, geofon, instance, iquique, lendb, neic, original, original_nonconservative, scedc, stead, volpick | 6000 samples = 60 s | 100 Hz | peak; std for original and original_nonconservative | detection, P, S |
| OBSTransformer | 1: obst2024 (ocean-bottom stations) | 60 s | 100 Hz | std | detection, P, S |
| EQCCT | 2: eqcctp_original (P only), eqccts_original (S only) | 60 s | 100 Hz | std | P or S |
| BasicPhaseAE | 8: the same 8 training sets as PhaseNetLight | 600 samples = 6 s | 100 Hz | std | P, S, noise |
| Skynet | 2: original, original_multiphase | 30000 samples = 300 s | 100 Hz | peak | P, S, noise |
| EQTP | 1: ncedc | 12000 samples = 120 s | 100 Hz | std | polarity up/down, P, S |

The component order is Z, N, E for all models except phasenet_original, phasenet_phasenet_sn and the two
Skynet files, which use E, N, Z. The plugin reads the order from each file, so this needs no setting.

What the training-data names mean, from the SeisBench descriptions and the dataset papers:

| name | training data |
|---|---|
| instance | the Italian national network: local and regional earthquakes, broadband, short-period and accelerometer channels |
| stead | a global collection of mostly small earthquakes at local distances |
| ethz | Switzerland |
| scedc, original (Zhu & Beroza's PhaseNet), ncedc | California: southern (scedc) and northern (original, ncedc) |
| jma | Japan Meteorological Agency data (Naoi et al., 2024) |
| diting | China (Zhu, Li & Fang, 2023) |
| geofon, neic | global, mostly regional and distant earthquakes |
| iquique | the 2014 Iquique aftershock sequence in Chile |
| lendb | global local earthquakes |
| aq2009 | the 2009 L'Aquila sequence |
| volpick | volcanic earthquakes |
| pisdl | induced seismicity |
| phasenet_sn | the S-net ocean-bottom network off Japan |
| obst2024 | ocean-bottom seismometers |

**Check: does the plugin feed each model the same input as SeisBench does?** I compared SeisBench's
own preprocessing code (seisbench 0.11 in env `dl-base`, only read) with the plugin's
`plugins/picker/dl/onnxmodel.cpp`. The plugin removes the mean and scales **each component on its own**
(by its standard deviation or its peak). It applies no filter.

- **Same input** for PhaseNet, PhaseNetLight, BasicPhaseAE, and the EQTransformer files with "peak"
  normalization. For these models SeisBench also scales each component on its own.
  - EQTransformer in SeisBench also tapers 6 samples at each end of the window. That does not matter
    here.
- **Different input** for 6 files. For the EQTransformer-family files with "std" normalization
  (`eqtransformer_original`, `eqtransformer_original_nonconservative`, `obstransformer_obst2024`,
  `eqtp_ncedc`) and for both Skynet files, SeisBench scales the **three components together**:
  - The EQTransformer-family files use one standard deviation for all three components.
  - The Skynet files use one peak for all three components.
- **Filters the plugin does not apply:** SeisBench filters the data before the network for
  `eqtransformer_original` and `_nonconservative` (1–45 Hz band-pass) and for `obstransformer_obst2024`
  (3–20 Hz).

For those 6 files the plugin's input differs from what the models were made for. I did not test how much
that matters, and I do not recommend them. (EQCCT is not in seisbench 0.11, so I could not check it.)

**SeisBench's own pick thresholds.** SeisBench lists, for each weight set, the threshold that gave the
best F1 score on the training data set. Several are far below the plugin's default `minConfidence` of
P 0.4 and S 0.3:

| model | SeisBench threshold |
|---|---|
| phasenet_instance | P 0.09, S 0.12 |
| eqtransformer_instance | 0.005 |
| eqtransformer_scedc | 0.014 |

For such models the default `minConfidence` may reject real but weak arrivals. The comparison step has
to choose the threshold for each model.

### Recommended models for the Gwangyang tests

The Gwangyang data are local earthquakes (KMA ML 1.1–2.2) recorded at 7–99 km, at 100 Hz. Three kinds of
sensor recorded them: 32 HG accelerometers, 17 HH broadband and 5 EL short-period sensors. I recommend
testing four models, in this order:

1. **phasenet_instance** (PhaseNet, 30 s window, trained on INSTANCE). I used it for the smoke test.
   - **Why:** INSTANCE is a large data set of mostly small local and regional Italian earthquakes,
     recorded at 100 Hz by broadband, short-period *and* accelerometer channels. That is the closest
     match to the Gwangyang station mix, where more than half of the stations are accelerometers.
   - **Input:** the model sees the same input in SeisComP as in SeisBench.
   - **Threshold:** its SeisBench thresholds (P 0.09, S 0.12) are far below the plugin's default, so
     `minConfidence` should be part of the comparison.
2. **phasenet_stead** (PhaseNet, trained on STEAD).
   - **Why:** STEAD is a global collection of mostly small earthquakes at local distances. That is the
     same size and distance range as Gwangyang, but another region and other instruments.
   - **What it shows:** a second training set for the same architecture shows how much the training data
     matter.
3. **eqtransformer_stead** (EQTransformer, 60 s window, trained on STEAD, "peak" normalization).
   - **Why:** it is a different architecture that sees twice as much signal around each trigger.
   - **Input:** the same in SeisComP as in SeisBench.
   - **Not `eqtransformer_original`**, because of the input difference described above.
4. **phasenet_original** (Zhu & Beroza's original PhaseNet, trained in northern California).
   - **Why:** the reference picks were made with PhaseNet+, a later model from the same group, trained
     on Californian data. phasenet_original is the closest relative of PhaseNet+ available as an ONNX
     file.
   - **What it shows:** comparing it with the reference separates what SeisComP's trigger-driven picking
     changes from what a different training set changes.

**Optional, for East Asian training data:**

- **phasenet_jma** (Japan).
- **phasenet_diting** (mainland China). It works at 50 Hz, so the plugin resamples our 100 Hz data and
  its picks come in 20 ms steps.

**Not suited to these data:**

- the global sets of mostly distant earthquakes (geofon, neic);
- the ocean-bottom, volcanic and induced-seismicity sets;
- BasicPhaseAE, whose window is only 6 s;
- Skynet, whose window is 300 s, so `ringBufferSize` and `leadTime` would need to be raised. Its input also
  differs from SeisBench's, as described above.

## 4. Smoke test of the deep-learning picker in SeisComP

### What was run

One Gwangyang event: **2021-08-27 22:03:22 UTC, KMA ML 2.2**, KMA id 20210827220322. It is the largest of
the 11 events. Its playback file holds 9 minutes of 100 Hz data (22:00:37 to 22:09:33) from 53 stations.
Everything ran offline from files, with no messaging server, no database and no network.

1. **Sort the data.** `scmssort -u -E` sorted the 17,536 records by end time and removed duplicate
   records. There were none.
2. **Convert the station metadata.** `fdsnxml2inv` converted `inputs/stations.xml` from FDSN StationXML
   into SeisComP's inventory format. It printed 40 harmless warnings ("ambiguous resourceId '' for
   ResponsePAZ/ResponseFIR"). For each, it made up a new ID that contains the current time, so this file
   is not byte-identical from one run to the next.
3. **Choose which channel scautopick watches.** These choices are station "bindings": one per station,
   on the vertical channel of the station's sensor (`detecStream` = HH, HG or EL).
   `install/05_smoke_bindings.py` wrote them as SeisComP key files, and `bindings2cfg` turned those into
   `config/bindings_config.xml`.
   - **46 of the 53 stations were bound:** 30 HG, 11 HH and 5 EL.
   - **The other 7 have no metadata** in `stations.xml` (CGWB, CHRB, HADA, KWJU, YALB, YKDB, YNDB; known
     from step C2), so scautopick cannot use them.
4. **Pick.** scautopick ran with the plugin, P picker DL3C, S picker SDL3C and the model
   `phasenet_instance.onnx`, with the settings from the scdlrtpicker README (configuration below).
5. **Compare.** `install/05_compare_picks.py` matched the SeisComP picks to the event's PhaseNet+ picks:
   - same station and same phase;
   - P within 0.5 s, S within 1.0 s;
   - each pick used at most once, closest pairs first;
   - every SeisComP pick without a partner gets a reason.

### Results (phasenet_instance)

- **Run time: 0.80 s wall clock** for the whole 9-minute file of 46 stations (0.91 s CPU, user plus
  system; 113 MB memory). These are the numbers of the final run (13:04). The first run (12:57), made
  before I switched off ONNX Runtime's telemetry (see "Problems"), took 0.85 s and gave exactly the same
  picks, confidences and comparison numbers.
- **The plugin loaded the model.** The log says `OnnxSession: loaded '.../phasenet_instance.onnx': 3
  component(s) [ZNE], 100.000 sps, window=3001 (30.0s), resample=true, polarity=no, uncertainty=no`.
  It has no `[error]` line, and 2 `[warning]` lines about duplicates (explained below).
- **What happened inside:**
  1. The STA/LTA detector triggered 182 times.
  2. 154 of these triggers started the P picker. 26 fell under the dead-time rule, and 2 were still in
     progress when the data ended.
  3. The model ran on 149 P windows. The other 5 pickers got no complete 30 s window, because their
     trigger was too close to the start or the end of the station's data.
  4. The model accepted 53 of them, so 51 P picks remained after scautopick dropped 2 exact duplicates.
     It rejected the rest: the noise triggers before the event got a P probability of 0.00–0.13,
     against the threshold of 0.40. This is how the README means the permissive detector to work.
  5. The 51 P picks started 51 S pickers, which ran 204 S windows.
- **Output: 51 P picks (DL3C) and 46 S picks (SDL3C)**, plus 198 amplitudes (MLv, mb, mB). All pick
  times fall exactly on samples of the data.

**Comparison with the PhaseNet+ picks.** PhaseNet+ has 102 picks for this event, 52 P and 50 S. Of these,
45 P and 43 S are at the 46 stations scautopick could use. The other 7 P and 7 S are at the 7 stations
without metadata.

| | P (tolerance 0.5 s) | S (tolerance 1.0 s) |
|---|---|---|
| PhaseNet+ picks at the 46 usable stations | 45 | 43 |
| matched by a SeisComP pick | **45 of 45** | **43 of 43** |
| median absolute time difference | **0.020 s** | **0.060 s** |
| largest absolute time difference | 0.070 s | 0.175 s |
| mean difference (SeisComP minus PhaseNet+) | −0.019 s | −0.065 s |
| lowest model confidence among matched picks | 0.74 | 0.48 |
| SeisComP picks without a PhaseNet+ partner | 6 | 3 |

**Which picks have no partner:**

1. **Near-duplicates (2 P + 2 S, at HAMB and IMSB).** The same arrival was picked twice, 10 ms or less
   apart. Here is how that happens at HAMB:
   - A noise trigger came 11 s before the P wave.
   - The model window centred on that trigger reaches 15 s past it, so it already contained the real P,
     and the model picked it.
   - That pick is only sent when its window is complete. So when the real P triggered the detector
     again, no pick existed yet, the dead-time rule could not stop it, and the model picked the same P
     a second time.
   - scautopick removes a second pick only if its time is *exactly* the same. That happened at HAIA and
     YOA: these are the 2 "Duplicate pick ... ignoring" warnings.

   Each duplicated P also gets its own S picker, so the S picks are duplicated too.
2. **Before the event (2 P).** These are MALA (22:02:28, confidence 0.45) and YGJA (22:02:50, 0.51).
   - They come 55 s and 33 s before the origin time.
   - Each is at one station only, and their confidences are low. The event's real P picks are all at
     0.74 or higher.
   - So they are most likely noise.
3. **After the event (2 P).** These are BOSB (22:06:29, 0.86) and MNDB (22:08:08, 0.68).
   - Each is at one station only, 3 and 4.7 minutes after the origin.
   - The reference has picks only for the catalog event, so they cannot be judged here.
4. **One S with no PhaseNet+ S (JNYA, 22:03:50.44, confidence 0.36).** PhaseNet+ picked P but no S at
   JNYA, 95 km away.
   - The S−P time is 11.2 s, which fits the neighbouring stations at that distance.
   - All four models put an S there within 0.1 s of each other.
   - So it is probably a real S that PhaseNet+ missed.

**The S picks of phasenet_instance are on average 65 ms earlier than PhaseNet+.** 30 of the 43 differ by
more than 0.05 s. This is a difference between the two models' idea of the S onset, not a timing error:

- the plugin's picks fall exactly on data samples;
- the P picks agree to 0.02 s;
- the other models below show other offsets.

### The other recommended models: they load and run

These runs use the same data and settings, and only the window length changes with the model. **This is
not the model comparison.** That comparison needs all 11 events, and it comes in a later step.

| model | P picks | P matched (of 45) | median / largest abs. P diff. | S picks | S matched (of 43) | median / largest abs. S diff. | wall time |
|---|---|---|---|---|---|---|---|
| phasenet_instance | 51 | **45** | 0.020 / 0.070 s | 46 | **43** | 0.060 / 0.175 s | 0.80 s |
| phasenet_stead | 47 | 44 | 0.025 / 0.075 s | 46 | 41 | 0.030 / 0.110 s | 0.74 s |
| eqtransformer_stead | 49 | 45 | 0.030 / 0.140 s | 48 | 43 | 0.040 / 0.095 s | 2.63 s |
| phasenet_original | 48 | 45 | 0.030 / 0.110 s | 48 | 43 | 0.025 / 0.060 s | 0.74 s |

- **phasenet_stead** missed the P and the S at JASA (75 km) and the S at SUCA (68 km).
- **Mean offsets** (SeisComP minus PhaseNet+) are −0.02 to −0.03 s for P and S with phasenet_stead and
  eqtransformer_stead. They are +0.03 s (P) and +0.02 s (S) with phasenet_original.
- **Extra picks:** every model made a few near-duplicates. Only phasenet_instance made the two
  low-confidence picks before the event. The full numbers are in `output/<model>/compare_summary.json`.

### The configuration that works

scautopick reads only this file, because it is given with `--config-file`, so everything it needs is in
the file. This is `runs/smoke_dlpicker/config/scautopick_phasenet_instance.cfg` without its comments:

```
plugins = dlrtpicker
picker = DL3C
spicker = SDL3C
module.trunk.global.picker.DL3C.model = /home/msseo/works/74.SeisComP_rtDD_DLpicker/software/src/seiscomp/src/extras/scdlrtpicker/models/phasenet_instance.onnx
module.trunk.global.spicker.SDL3C.model = /home/msseo/works/74.SeisComP_rtDD_DLpicker/software/src/seiscomp/src/extras/scdlrtpicker/models/phasenet_instance.onnx
module.trunk.global.picker.DL3C.maxAttempts = 1
module.trunk.global.spicker.SDL3C.minLatency = 15
module.trunk.global.spicker.SDL3C.maxLatency = 30
module.trunk.global.spicker.SDL3C.maxAttempts = 4
module.trunk.global.spicker.SDL3C.strategy = best
filter = "RMHP(10)->ITAPER(30)->BW_BP(4,5,20)->STALTA(1,30)"
timeCorrection = 0
thresholds.triggerOn = 1.8
thresholds.triggerOff = 1.0
killPendingSPickers = false
thresholds.deadTime = 15
thresholds.minAmplOffset = 1.8
thresholds.amplMaxTimeWindow = 5
ringBufferSize = 300
leadTime = 60
initTime = 60
thresholds.maxGapLength = 4.5
amplitudes = MLv, mb, mB
extraPickComments = true
```

What the settings mean:

- **Settings for all stations.** `module.trunk.global.*` is the README's "testing form": the picker
  settings apply to every station, without writing them into each station binding.
- **P picker (DL3C).** Each STA/LTA trigger gets one 30 s model window, centred on the trigger. This is
  the README's "reliable picks". The pick is the strongest P peak in the window, if it is above
  `minConfidence` (default 0.4).
- **S picker (SDL3C).** Each P pick gets four 30 s windows, ending 15, 20, 25 and 30 s after the P pick.
  - They are centred on S−P = 0, 5, 10 and 15 s. For this event the S−P times are 1.7–11.7 s.
  - The most confident S peak above `minConfidence` (default 0.3) is kept (`strategy = best`).
- **Detector.** This is the README's permissive STA/LTA:
  - 5–20 Hz band-pass;
  - 1 s and 30 s windows;
  - on at 1.8, off at 1.0;
  - no time correction.
- **Dead time.** The dead time is 15 s, which is half the P window. `minAmplOffset` equals the trigger-on
  level, and `amplMaxTimeWindow` is 5 s (the README says "comfortably below deadTime").
- **Defaults.** The last block repeats scautopick's defaults, because `--config-file` skips the default
  files.
- **60 s models (EQTransformer).** The script sets the half window to 30 s: `SDL3C.minLatency = 30`,
  `maxLatency = 45`, `deadTime = 30`. See `config/scautopick_eqtransformer_stead.cfg`.
- **`minConfidence` stays at the plugin default.** I did not tune it on this one event, which is the
  largest event. Choosing it belongs to the comparison step.

The command, from `runs/smoke_dlpicker`. It runs in a subshell with the SeisComP environment,
`HOME=runs/seiscomp_home`, `SEISCOMP_LOCAL_CONFIG=output/<model>/seiscomp_user` and
`ORT_DISABLE_TELEMETRY=1`:

```bash
scautopick --config-file config/scautopick_phasenet_instance.cfg --offline --playback --ep -f \
  --inventory-db file://input/inventory_sc.xml --config-db file://config/bindings_config.xml \
  -I file://input/20210827220322_sorted.mseed --debug > picks.xml 2> scautopick.log
```

| option | meaning |
|---|---|
| `--offline` | no messaging |
| `--playback` | process old data from a file |
| `--ep` | write the picks and amplitudes as SeisComP XML to stdout |
| `-f` | indented XML |
| `--debug` | full log on stderr |

The paths in the real run are absolute (see the log).

**Reading the output:**

- The XML namespace is `http://geofon.gfz.de/ns/seiscomp-schema/0.14`.
- S picks carry the station's **vertical** channel code in their `waveformID`.
- The model confidence is in the comment with id `confidence`, for P picks only. It is also in the comment
  with id `SNR`, for both P and S, because `extraPickComments = true`.
- An S pick refers to its P pick through the comment with id `RefPickID`.

## Problems met, and how they were solved

1. **My own check of the test grids was wrong at first.**
   - I expected 128 files per `time/` folder (16 stations × P, S × time, angle × .hdr, .buf). NonLinLoc's
     Grid2Time also copies the P and S model grids into `time/`, so there are 132.
   - The first run (12:40, 70 s) made all the grids correctly, but stopped with "ERROR: incomplete grid
     sets".
   - I fixed the number in the script, with a comment, and ran the stage again with
     `--regenerate-grids` (12:42, 72 s). All 10 sets were complete. Both runs are in the log.
2. **"Did not find plugin dbmysql".**
   - **Cause:** SeisComP's default configuration (`etc/defaults/global.cfg`) loads the MySQL database
     driver (`core.plugins = dbmysql`). This build has only the SQLite driver (step A).
   - **Effect:** every SeisComP program that reads the default configuration stops at start-up:
     ```
     [error] Did not find plugin dbmysql
     [error] Failed to load all requested plugins, bailing out
     ```
     It happened here with `fdsnxml2inv` and `bindings2cfg`.
   - **Fix, by configuration only:** `--core.plugins=dbsqlite3` on their command lines. No database is
     used either way. scautopick is not affected, because `--config-file` skips the default
     configuration.
   - **For later steps:** programs that read the default configuration (scrtdd, scevent, ...) need the
     same option. The other way is one line, `core.plugins = dbsqlite3`, in
     `$SEISCOMP_ROOT/etc/global.cfg`. I did not create that file, because other steps share this
     installation.
3. **Without bindings, scautopick watches every channel.** With no station configuration, scautopick's
   "use all streams" mode puts an STA/LTA detector on every stream it receives, horizontals included
   (`handleNewStream` in `scautopick/picker.cpp`). One arrival could then start the P picker three times.
   Fix: station bindings (key files + `bindings2cfg`), one vertical channel per station.
4. **Tests that open network ports were not run.** See section 2.
5. **ONNX Runtime sends usage telemetry to Microsoft unless it is switched off.** This is not a
   failure; I found it while checking that nothing is written outside the project.
   - **What happens:** the official ONNX Runtime 1.31.0 release (the one step A installed for the
     plugin) contains Microsoft's "1DS" telemetry. Every scautopick run that loads the plugin wrote
     two files under `$HOME/.cache/Microsoft/DeveloperTools/.onnxruntime/`: a device id (`deviceid`)
     and a small database (`onnxruntime.db`) with one more queued event per run. The library contains
     the upload address `https://mobile.events.data.microsoft.com/OneCollector/1.0`. I did not check
     whether events were actually uploaded from Server A.
   - **Where it landed:** because every run used `HOME=runs/seiscomp_home`, these files are in
     `runs/seiscomp_home/.cache/...` and not in the real home folder (`/home/msseo/.cache/Microsoft`
     does not exist). The database holds 7 queued events: 6 from my test runs and 1 from a
     deliberate control run.
   - **Fix, by configuration only:** the environment variable `ORT_DISABLE_TELEMETRY=1`. The script now
     sets it for every SeisComP command. Check: with it, a run left `onnxruntime.db` untouched (same
     time stamp, still 7 events). Without it, the next run added an event. The picks are byte-for-byte
     the same either way. The smoke stage was then run again with the switch (13:04); its outputs are
     the ones kept.

## Open points for the next steps

- **Picker settings to look at.** These are not problems of the installation; they come from the
  README's permissive settings:
  - the near-duplicate picks;
  - the single-station picks outside the event;
  - `minConfidence` versus SeisBench's much lower thresholds.

  They should be judged on all 11 events, especially the small ones (ML 1.1).
- **Possible remedies for duplicates, none of which was tried:** a slightly higher `triggerOn`, shorter
  P windows, or removing picks of one station closer than about 0.1 s after picking.
- **7 stations still have no metadata.** The 7 stations without metadata (14 PhaseNet+ picks for this
  event) can only be used once their metadata are added; see step C2's note.
- **Possible upstream issue.** For 6 of the shipped models the plugin's input scaling differs from
  SeisBench's (section 3). This may be worth reporting to the scdlrtpicker authors. Its effect was not
  measured.
- **Telemetry for everyone.** `install/env_seiscomp.sh` (step A) does not set `ORT_DISABLE_TELEMETRY=1`,
  so other steps that run the plugin will still queue telemetry. Adding
  `export ORT_DISABLE_TELEMETRY=1` there would switch it off for all steps; I did not change that shared
  file. The 7 queued events in `runs/seiscomp_home/.cache/Microsoft/` can be deleted if they should
  never be sent.

## Versions

| item | version |
|---|---|
| SeisComP | 7.4.0, the build of step A (commits in `docs/patches.md`); unit tests run from `software/build/seiscomp` |
| scrtdd | v2.0.10, commit `f801f859defac0634341480b98eb85021d5302ac` |
| scdlrtpicker | v1.1.1, commit `409b18fd6d933cd4ebd5354a0ff74998b6cb6113`. Its README on `master` today is identical to the v1.1.1 one |
| ONNX Runtime | 1.31.0 (step A) |
| NonLinLoc | v7.00.16-beta, commit `4bb22a7c` (step C1) |
| CMake / CTest | 3.31.8 (env `seiscomp`) |
| Python helpers | env `pyrtdd`: Python 3.12.15, onnx 1.23.2, obspy 1.5.1, pandas 3.0.6, numpy 2.5.4 |
| SeisBench | 0.11.0 in env `dl-base`. Its source was only read, to compare its preprocessing with the plugin's; nothing was installed or run there |
| SeisBench model descriptions | `https://hifis-storage.desy.de:2880/Helmholtz/HelmholtzAI/SeisBench/models/v3/`, read 2026-10-17 |

## How to reproduce

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker
bash install/05_tests.sh                          # dry run: prints every command, changes nothing
bash install/05_tests.sh --apply                  # all five stages, about 15 minutes
bash install/05_tests.sh --apply --stage smoke    # one stage: nllgrids | hdd | ctest | models | smoke
```

- **Log:** everything the script prints is appended to `logs/05_tests_20261017.log`.
- **How it was run:** I ran the stages in the order nllgrids, hdd, ctest, models, smoke, each as a
  separate `--apply --stage <name>` call. The log keeps all of them, including the first nllgrids run
  that stopped on my wrong file count.
- **Dry run:** a full dry run of the final script is in `logs/05_tests_dryrun.log`. It exited with 0.
- **nllgrids:** skips the 72 s generation when all 10 grid sets are already complete. Add
  `--regenerate-grids` to force it; that is how the second, successful run was made.
- **models:** needs internet access, to read SeisBench's model descriptions (about 1 minute).
- **smoke:** takes about 15 s for all four models (13:04:59 to 13:05:15 in the log). It was run twice;
  the second (final) run adds `ORT_DISABLE_TELEMETRY=1`, and its outputs are the ones in
  `runs/smoke_dlpicker/`.

## Files

| what | where |
|---|---|
| script and helpers | `install/05_tests.sh`, `install/05_smoke_bindings.py`, `install/05_compare_picks.py`, `install/05_seisbench_weight_info.py` |
| logs | `logs/05_tests_20261017.log`, `logs/05_tests_dryrun.log` |
| unit-test outputs | `runs/05_tests/`: `ctest_hdd.log` + `ctest_hdd_junit.xml`, `ctest_full.log` + `ctest_full_junit.xml`, `nllgrids_generate.log` (NonLinLoc output), `seiscomp_user/` (the tests' per-user folder) |
| NonLinLoc test grids | `software/src/seiscomp/src/extras/scrtdd/libs/hdd/test/data/nll/iasp91_*/{model,time}/` (3.5 GB) |
| model list | `docs/dlrtpicker_models.txt` |
| smoke test | `runs/smoke_dlpicker/`, described below |

What is in `runs/smoke_dlpicker/`:

- `input/`: the sorted miniSEED file and the SeisComP inventory.
- `config/`: the key files, `bindings_config.xml`, `stations_bound.csv` and one `scautopick_<model>.cfg`
  per model.
- `output/<model>/`, one folder per model:
  - `picks.xml`, `scautopick.log` and `time.txt`;
  - `compare_summary.json`, `compare_reference_vs_seiscomp.csv` and `compare_seiscomp_picks.csv`;
  - `seiscomp_user/`, the run's per-user folder.
