# Step 09: the deep-learning picker in SeisComP on all 11 Gwangyang events (2026-10-17)

The deep-learning (DL) picker is scautopick plus the scdlrtpicker plugin: P picker DL3C and S picker SDL3C.
I ran it offline on the 11 Gwangyang events with the four models recommended in step T, plus one "fast picks"
variant. I then compared the picks with the PhaseNet+ reference picks. I also cross-checked them against
SeisBench running the same weights, measured the cost, and relocated the events with pyrtdd from the DL picks.

**Read every "agreement" number with this in mind.** PhaseNet+ is itself an automatic picker. "Matched" means
"agrees with PhaseNet+", not "is right". Where the two disagree, either one can be wrong. Section 5 shows that
many DL picks without a PhaseNet+ partner are probably real arrivals.

## Result in brief

- **Everything ran.** I made 55 picking runs (11 events × 5 variants) and 5 start-up runs.
  - No run printed an `[error]` line.
  - The only warnings were 10 "Duplicate pick ... ignoring" lines, which come from scautopick's own exact-duplicate check.
  - All 54 stations were bound: 32 HG, 17 HH and 5 EL.
  - Nothing was written outside the project. `~/.seiscomp` and `~/.seisbench` were not touched.
- **Best model: `phasenet_original`.** The rule was fixed before any result was seen: highest pooled P+S F1
  against PhaseNet+, with ties (within 0.005) broken by the smaller 95th percentile of |dt|.
  - phasenet_original: F1 0.855. It finds 91 % of the PhaseNet+ P picks and 86 % of the S picks.
    The middle 50 % of its time differences lie within ±0.010–0.015 s of the median (MAD).
  - phasenet_instance comes second (F1 0.836), then eqtransformer_stead (0.782) and phasenet_stead (0.749).
  - Its drawback: it makes the most picks outside the event windows of the four main models, 1.26 P picks
    per station-hour against 0.63 for phasenet_instance and 0.04 for eqtransformer_stead.
- **Large events are nearly complete with every model; small ones are not.**
  - For ML ≥ 1.5, P recall is 0.79–0.95.
  - For ML < 1.5, P recall is 0.43–0.82 and S recall 0.38–0.76.
  - **Why the picks are lost** (section 4):
    - Missed P: the detector did trigger, but the model's P probability stayed below 0.4.
    - Missed S: the station had no P pick, so the S picker never started. The plugin starts S pickers only
      from P picks.
- **The plugin reproduces SeisBench.** The ONNX files hold exactly SeisBench's v2 weights: on identical input
  the outputs differ by about 1e-6, which is float32 rounding (section 9).
  - Pick times agree to a median |dt| of 0.010 s (phasenet_instance) and 0.020 s (eqtransformer_stead).
  - 89–96 % of the pairs agree within 0.05 s (5 samples; fractions are counted in whole samples).
  - The mean offsets (plugin minus SeisBench) are 0.0052 s or less in size, about half a sample.
  - SeisBench's continuous picking finds somewhat more of the PhaseNet+ picks, mainly S picks at stations
    where the plugin had no P pick.
- **Fast picks.** These are the README's P settings 1–8 s after the trigger.
  - Almost the same P times: median |dt| 0.01 s, 92 % within 0.05 s (5 samples), largest 0.19 s.
  - Picks are ready 1.3 s after the onset (median) instead of 15.2 s.
  - The cost is 3.7 times as many P picks outside the event windows.
- **Cost.** The plugin needs 0.11–0.14 CPU-s per station-hour for the PhaseNet models and 0.34 for
  EQTransformer, on one thread. SeisBench's continuous picking on one thread needs about 2.8 times as much.
- **Double-difference relocation from the DL picks works,** with an important limit (section 10).
  - The events lie within about 50–70 m of their centroid (RMS).
  - **Horizontally**, the best model's picks reproduce the PhaseNet+-pick relocation to 16 m (east) and
    8 m (north) RMS. That is inside HypoDD dt.ct's bootstrap 95 % range (34 / 17 m).
  - **In depth** they differ by 46 m RMS.
  - No catalog-only solution resolves this cluster's depths: not HypoDD dt.ct and not the PhaseNet+ picks
    in pyrtdd. Measured against the cross-correlation solution (dt.cc), each of them is about as far away
    (50–53 m RMS) as putting every event at one point (50 m).
  - These numbers compare relative geometry only, with each solution's centroid removed. The clusters do
    not sit at the same place: catalog-only pyrtdd moved the PhaseNet+ control 1.7 km from its start and the
    best model's solution 0.08 km. A catalog-only solution's absolute position is not meaningful.

## 1. What was run

- **Data.** The 11 playback files, sorted with `scmssort -u -E`.
  - Each holds about 7.5 minutes of 100 Hz data per station, from 100–166 s before to 312–383 s after the
    origin.
  - In total: 71.0 station-hours on the bound vertical channels.
- **Inventory.** `data/gwangyang_11ev/inputs/inventory_sc.xml` from step Prep.
- **Bindings.** These follow the step-T design:
  - one per station, on the vertical channel of its only sensor (`detecStream` = HH, HG or EL);
  - written by `09_bindings.py` and converted with `bindings2cfg`;
  - the helper checked that the inventory has Z, N and E of that sensor for every event window of every
    station: 54 of 54 pass.
- **scautopick configuration.** The same as step T: the README's permissive STA/LTA detector
  (5–20 Hz, 1/30 s, on 1.8, off 1.0), dead time = half the model window, `minConfidence` at the plugin
  defaults (P 0.4, S 0.3).
  - **P:** one window centered on the trigger.
  - **S:** four windows ending 15, 20, 25 and 30 s after the P pick (for EQTransformer 30, 35, 40, 45 s);
    the best one is kept.
  - **Fast variant:** only the four README "fast" P settings change (minLatency 1, maxLatency 8,
    maxAttempts 8, strategy fast). The dead time stays at 15 s, so both variants start pickers on the
    same triggers.
  - **Settings dump per variant:** `runs/gwangyang/dlpicker/settings/scautopick_<variant>.settings.json`.
    It holds every cfg value, scautopick's own `--dump-config`/`--dump-settings` output, the plugin's
    defaults (from its source code) and the model metadata.
  - **Check:** the window positions logged by the plugin match the resolved settings exactly:
    P windows start 15.00 or 14.99 s (PhaseNet) or 29.99 s (EQTransformer) before the trigger, and fast
    windows end 1–8 s after it (`analysis/log_checks.csv`).
- **Matching** (as in step T).
  - Same event run, same station and phase; P within 0.5 s, S within 1.0 s; one-to-one, closest first.
  - dt = DL − PhaseNet+.
  - Event window: HYPOINVERSE origin − 5 s to + 60 s.
  - Recall = matched / PhaseNet+ picks (all 763 are at bound stations).
  - Precision = matched / DL picks of that phase inside the window.
  - MAD = median(|dt − median(dt)|).
  - "Identical", "within 0.02 s" and "within 0.05 s" (sections 8 and 9) are counted in whole samples. Pick
    times lie on the 100 Hz sample grid but differ from it by a few microseconds, so a cut at exactly 0.02 s
    is ill-defined. Each difference is therefore rounded to whole samples, n = round(dt × 100): identical
    means n = 0, within 0.02 s means |n| ≤ 2, within 0.05 s means |n| ≤ 5.
- **Reference.** 763 PhaseNet+ picks (360 P, 403 S).
  - 17 of them (9 P, 8 S) are more than 1 s from the kim1983 grid times ("reference outliers", step V3d).
  - Against the grid times at the HypoDD dt.cc locations, the other reference picks have median residuals of
    +0.034 s (P) and −0.267 s (S). That is the known S−P deficit.
  - My epicentral distances agree with the reference table's within 0.005 km.

## 2. Agreement with PhaseNet+, per model

- "Precision counting plausible" is an upper bound. It also counts as correct the unmatched DL picks that lie
  within 1.0 s of the predicted arrival where PhaseNet+ has no pick or only an outlier (section 5).
- All numbers below come from `analysis/summary_by_model.csv`.

| model | phase | recall | precision | precision counting plausible | F1 | median \|dt\| (s) | MAD (s) | p95 \|dt\| (s) | mean dt (s) |
|---|---|---|---|---|---|---|---|---|---|
| **phasenet_original** | P | 326/360 = 0.91 | 326/412 = 0.79 | 0.90 | 0.845 | 0.030 | 0.015 | 0.109 | +0.040 |
| | S | 346/403 = 0.86 | 346/397 = 0.87 | 0.93 | 0.865 | 0.025 | 0.010 | 0.060 | +0.024 |
| phasenet_instance | P | 303/360 = 0.84 | 303/360 = 0.84 | 0.90 | 0.842 | 0.020 | 0.015 | 0.080 | −0.019 |
| | S | 305/403 = 0.76 | 305/332 = 0.92 | 0.95 | 0.830 | 0.065 | 0.020 | 0.164 | −0.072 |
| eqtransformer_stead | P | 265/360 = 0.74 | 265/292 = 0.91 | 0.92 | 0.813 | 0.030 | 0.020 | 0.074 | −0.021 |
| | S | 262/403 = 0.65 | 262/292 = 0.90 | 0.92 | 0.754 | 0.040 | 0.025 | 0.104 | −0.037 |
| phasenet_stead | P | 239/360 = 0.66 | 239/265 = 0.90 | 0.97 | 0.765 | 0.020 | 0.015 | 0.075 | −0.015 |
| | S | 244/403 = 0.61 | 244/262 = 0.93 | 0.97 | 0.734 | 0.025 | 0.010 | 0.070 | −0.028 |
| phasenet_instance **fast** | P | 311/360 = 0.86 | 311/398 = 0.78 | 0.87 | 0.821 | 0.025 | 0.015 | 0.085 | −0.021 |
| | S | 312/403 = 0.77 | 312/338 = 0.92 | 0.96 | 0.842 | 0.065 | 0.020 | 0.160 | −0.070 |

- **Pooled P+S F1:** phasenet_original 0.855, phasenet_instance 0.836, phasenet_instance_fast 0.831,
  eqtransformer_stead 0.782, phasenet_stead 0.749.
- **Leaving out the 17 reference outliers** raises recall by only 0.01–0.02 for every model.
- **The timing offsets are model properties.**
  - phasenet_instance picks S on average 72 ms earlier than PhaseNet+ (median |dt| 65 ms), as in step T.
  - phasenet_original picks slightly later, by 40 ms for P and 24 ms for S.
  - A constant offset cancels in double differences.
  - **These offsets do not say which picker is off.** A DL-minus-PhaseNet+ offset can be a late DL pick or an
    early PhaseNet+ pick; only an independent check can tell.
    - The independent verification looked at the waveforms of 4 examples (2 events × 2 stations; verifier's
      notebook `runs/verify_gwangyang_dl/notebooks/v09_waveform_examples.ipynb`).
    - At the weakest arrival there (ML 1.1 event 20260203021535, MNDB, P, 52 km) the first energy above the
      noise (10–40 Hz) starts at the phasenet_original pick, and the PhaseNet+ pick lies about 0.09 s
      earlier, in the noise (take-home 3; figure
      `runs/verify_gwangyang_dl/figures/v09_waveform_examples_mndb_small_event_P_bands.png`). So part of
      phasenet_original's +0.040 s mean P offset may come from early reference picks, not from late DL picks.
    - For phasenet_instance's S offset the same check points the other way: its S picks sat 0.05–0.075 s
      ahead of the visible S onset, in the pre-S noise, at all three stations where it picked S (take-home 2).
    - Four examples cannot settle the averages; they only show that either picker can be the one that is off.

## 3. Where picks are lost: event size, distance, sensor

Recall, with matched/reference counts in brackets (`analysis/by_magnitude.csv`, `by_distance.csv`,
`by_sensor.csv`; precision and p95 |dt| are there too):

| model | phase | ML < 1.5 (6 events) | ML ≥ 1.5 (5 events) | < 30 km | 30–60 km | > 60 km |
|---|---|---|---|---|---|---|
| phasenet_original | P | 0.82 (100/122) | 0.95 (226/238) | 0.95 | 0.93 | 0.87 |
| | S | 0.76 (125/165) | 0.93 (221/238) | 0.96 | 0.90 | 0.80 |
| phasenet_instance | P | 0.65 (79/122) | 0.94 (224/238) | 0.89 | 0.80 | 0.85 |
| | S | 0.55 (90/165) | 0.90 (215/238) | 0.90 | 0.75 | 0.71 |
| eqtransformer_stead | P | 0.49 (60/122) | 0.86 (205/238) | 0.89 | 0.71 | 0.70 |
| | S | 0.38 (62/165) | 0.84 (200/238) | 0.90 | 0.65 | 0.57 |
| phasenet_stead | P | 0.43 (52/122) | 0.79 (187/238) | 0.85 | 0.70 | 0.57 |
| | S | 0.39 (64/165) | 0.76 (180/238) | 0.85 | 0.66 | 0.49 |
| phasenet_instance fast | P | 0.71 (87/122) | 0.94 (224/238) | 0.88 | 0.86 | 0.86 |
| | S | 0.61 (100/165) | 0.89 (212/238) | 0.84 | 0.83 | 0.72 |

- **Precision drops for small events and far stations.** For ML < 1.5, P precision is
  - 0.64 for phasenet_original,
  - 0.69 for phasenet_instance,
  - 0.94 for eqtransformer_stead.

  This is where the "P picks" on S waves and the plausible arrivals of section 5 are found.
- **Sensor type.**
  - Overall, HH recall is lower than HG recall for every model. For example, phasenet_original has
    HH P 0.89 / S 0.82 against HG 0.91 / 0.89.
  - Most of this is distance: the HH stations are farther away (median 63 km, quarter of them below 56 km)
    than the HG stations (median 57 km, quarter below 34 km).
  - Beyond 60 km, HH and HG recall (P and S together) are about equal (phasenet_original: both 0.84).
  - The EL short-period stations behave like the others for P (0.92 for both PhaseNet models). Their S
    recall is lower (0.74–0.77).

## 4. Why PhaseNet+ picks were missed

`09_compare.py` reads the plugin's debug log for this. For each missed reference pick it checks whether a
detector trigger and a model window covered the onset, and what the best model value in those windows was
(`analysis/missed_reference_diagnosis.csv`).

| model | missed P | below minConfidence | no trigger | trigger but no picker (dead time) | picked another time | missed S | no P pick, so no S picker | below minConfidence | picked another time |
|---|---|---|---|---|---|---|---|---|---|
| phasenet_original | 34 | 15 | 9 | 6 | 3 (+1 vetoed as S) | 57 | 51 | 1 | 5 |
| phasenet_instance | 57 | 35 | 9 | 6 | 7 | 98 | 81 | 10 | 6 (+1 P pick on the S) |
| eqtransformer_stead | 95 | 83 | 6 | 5 | 0 (+1 vetoed) | 141 | 139 | 0 | 2 |
| phasenet_stead | 121 | 106 | 9 | 6 | 0 | 159 | 155 | 1 | 3 |
| phasenet_instance fast | 49 | 23 | 11 | 10 | 5 | 91 | 59 | 19 | 7 (+5 P picks on the S, 1 no window) |

- **The detector misses little.** It missed only 6–11 onsets with no trigger at all, and 5–10 where a
  trigger fell in the dead time.
- **Most P losses are the model's decision.** The window covered the onset, but the model's best P value in
  it stayed below 0.4.
- **Most S losses have no P pick before them.** This is a property of the plugin's design: an S picker only
  runs after a P pick. SeisBench, scanning continuously, finds 32–41 S picks the plugin cannot (section 9).
- **A threshold study would help.** SeisBench's own threshold for phasenet_instance is P 0.09 / S 0.12, far
  below 0.4 / 0.3. Lowering `minConfidence` would probably recover many of the "below minConfidence" losses,
  at the cost of more false picks. I did not tune it, as the task asked.

## 5. DL picks without a PhaseNet+ partner

Each unmatched DL pick inside an event window was classified automatically (rules in the header of
`09_compare.py`).

- **Predicted arrivals** come from the kim1983 NonLinLoc grids at the HypoDD dt.cc locations.
- **"Near"** means within 1.0 s. Every non-outlier PhaseNet+ pick lies within 0.94 s (P) or 0.89 s (S) of
  these times.
- **SNR** is computed after a one-pass 2–20 Hz filter, from 1 s after the pick against 3 to 0.5 s before it.

Counts over all 11 events (`analysis/unmatched_in_window.csv`):

| model | phase | near-duplicate | S wave picked as P (phase confusion) | plausible arrival PhaseNet+ did not pick | PhaseNet+ pick is an outlier, DL plausible | noise / other |
|---|---|---|---|---|---|---|
| phasenet_original | P | 16 | 13 | 43 | 2 | 12 |
| | S | 17 | 1 | 20 | 2 | 11 |
| phasenet_instance | P | 16 | 14 | 20 | 2 | 5 |
| | S | 16 | 1 | 5 | 4 | 1 |
| eqtransformer_stead | P | 24 | 0 | 3 | 0 | 0 |
| | S | 24 | 0 | 4 | 2 | 0 |
| phasenet_stead | P | 9 | 0 | 17 | 0 | 0 |
| | S | 9 | 0 | 7 | 2 | 0 |
| phasenet_instance fast | P | 10 | 26 | 32 | 3 | 15 (+1 timing disagreement) |
| | S | 12 | 1 | 9 | 3 | 1 |

**The two smallest events (ML 1.1)** are listed pick by pick, with confidence, residuals to the predicted P
and S, SNR and how many other models agree, in `analysis/unmatched_smallest_events.csv`.

**Event 5, 2021-08-28 13:39:22.** PhaseNet+ has 23 P and 31 S picks. Matched: phasenet_original 16 P / 25 S,
phasenet_instance 15 / 17, eqtransformer 10 / 11, phasenet_stead 10 / 16, fast 15 / 23.

- **Plausible arrivals PhaseNet+ did not pick** (phasenet_original 10, phasenet_stead 6, phasenet_instance 2,
  eqtransformer 1). They lie within 0.5 s of the predicted P, most within 0.3 s, at 48–90 km. Examples:
  - SACA: picked by three models and the fast variant within 0.1 s of each other, +0.16 to +0.28 s from the
    prediction, SNR 3.1–3.4 dB;
  - GKSA, HACA, NAJA and YKDB: 2–3 models or variants each, SNR 2.6–7.4 dB.

  These are weak but real-looking onsets.
- **Phase confusion** (1 pick for phasenet_instance and phasenet_original, 7 for the fast variant). These are
  "P" picks within 0.65 s of the predicted S (most 0.1–0.6 s before it) at 63–95 km, with SNR 4–16 dB. At these distances the P is too
  weak for the detector, so the S wave triggered it, and the model accepted that window's peak as P. The
  plugin's built-in S check (veto when the S curve is ≥ 80 % of P) did not catch these.
- **Noise** (phasenet_instance 2, fast 3, phasenet_original 1 S). Examples: HACA "P" 3.4 s after the
  predicted P with SNR 0.3 dB, and WICA 6.7 s after it with SNR 0 dB.

**Event 10, 2026-02-03 02:15:35.** PhaseNet+ has 15 P and 23 S picks. Matched: phasenet_original 12 / 12,
phasenet_instance 6 / 6, eqtransformer 4 / 4, phasenet_stead 6 / 7, fast 7 / 8.

- **phasenet_instance:** its 2 unmatched picks are both S waves picked as P (KWJ2 at 70 km and CHDA at
  96 km, SNR 9–13 dB).
- **phasenet_original:** 1 plausible P (HAIA, 42 km, +0.22 s, SNR 3.2 dB) and 1 noise S (JEU2, 3.4 s after
  the predicted S).
- **phasenet_stead:** 1 plausible P (WICA, +0.03 s, SNR 1.4 dB).
- **fast variant:** 4 phase confusions, 1 noise pick 3.9 s before the origin (DGHA) and 1 plausible P
  (HAIA).
- **Bottom line for this event:** the DL models find only 4–12 of its 15 PhaseNet+ P picks. Their extra picks
  are few, and the fast variant's are mostly wrong.

**Near-duplicates** come from the mechanism described in step T. A noise trigger shortly before the real
onset gets a window that already contains the onset, and the real trigger then picks the same onset again.
eqtransformer_stead makes the most (24 + 24), because its 60 s windows reach farther.

## 6. Picks outside the event windows ("false triggers")

- **Searchable data.** Picks were counted in the data outside every catalog event window. This excludes
  scautopick's 60 s start-up time and the last half P window of each file: 49.4 station-hours for the
  PhaseNet models, 47.2 for EQTransformer and 50.3 for the fast variant (out of 71.0 station-hours in total).
- **Event 5 in event 4's file.** Event 4's file reaches into event 5. Picks there are counted as "other
  catalog event", not as false.
- **Coincident picks** are P picks at 3 or more stations within ±10 s. They may be uncataloged events.

| model | P picks outside | S picks outside | other catalog event | coincident | isolated | false P picks per station-hour | false S picks per station-hour |
|---|---|---|---|---|---|---|---|
| phasenet_original | 69 | 23 | 8 | 16 | 68 | 1.26 | 0.45 |
| phasenet_instance | 39 | 5 | 9 | 9 | 26 | 0.63 | 0.08 |
| eqtransformer_stead | 2 | 0 | 0 | 0 | 2 | 0.04 | 0.00 |
| phasenet_stead | 7 | 2 | 3 | 0 | 6 | 0.08 | 0.04 |
| phasenet_instance fast | 144 | 12 | 20 | 39 | 97 | 2.48 | 0.22 |

**Not all of these are noise.** Two coincident groups are probably real, uncataloged events:

- 2026-01-01 02:51:35 at MALA, DGHA and JEU2 (89–94 km), picked by 3 variants;
- 2021-08-27 00:25:46 at GMNA (15 km) and BAU (17 km), with YOA, from phasenet_original.

Over a whole network, a rate of 0.6–1.3 per station-hour means roughly 30–65 single-station picks per hour for
50 stations. An associator such as scanloc must reject these.

## 7. Cost

These are CPU seconds of the whole scautopick process (`/usr/bin/time`): detector, amplitudes and model.
The plugin runs ONNX Runtime on one thread (`SetIntraOpNumThreads(1)` in `onnxmodel.cpp`).
From `analysis/cost.csv`:

| model | CPU s (11 events) | CPU s per station-hour | detector triggers | P / S model windows | ms per window | peak memory |
|---|---|---|---|---|---|---|
| phasenet_original | 9.57 | 0.135 | 2325 | 1818 / 1894 | 2.5 | 122 MB |
| phasenet_instance | 8.64 | 0.122 | 2325 | 1818 / 1576 | 2.5 | 121 MB |
| eqtransformer_stead | 24.08 | 0.339 | 2325 | 1513 / 1176 | 8.8 | 134 MB |
| phasenet_stead | 7.83 | 0.110 | 2325 | 1818 / 1080 | 2.6 | 120 MB |
| phasenet_instance fast | 20.09 | 0.283 | 2325 | 11650 / 2075 | 1.4 | 122 MB |

- **Start-up cost is negligible:** 0.03 s CPU on a 10-s probe file. The probe run never loads the model.
  In an event run the model is loaded once, when the first picker is created (one `OnnxSession: loaded` line
  per log).
- **The detector triggers often:** 2325 times in 71 station-hours, about 33 per station-hour. This is the
  README's permissive setting.
- **SeisBench's continuous `classify()`** on the same 71.0 station-hours (`seisbench/*_settings.json`):
  - with 1 thread: phasenet_instance 23.8 CPU-s (0.335 per station-hour, 2.8 times the plugin (23.83 / 8.64 = 2.76));
    eqtransformer_stead 68.0 CPU-s (0.957 per station-hour, 2.8 times);
  - with 4 threads: 35.1 and 86.8 CPU-s, in 10.0 and 23.1 s wall time;
  - both runs gave byte-identical picks.

## 8. Fast picks against reliable picks (phasenet_instance, P)

From `analysis/summary.json` → fast_vs_reliable, `fast_vs_reliable.csv` (per pair, with dt in whole
samples) and `fast_vs_reliable_latency.csv`.

- **Pick times.** 346 P picks pair up between the two runs, 321 of them inside the event windows.
  - Fast minus reliable inside the windows: median |dt| 0.010 s, mean −0.002 s, 95th percentile 0.070 s,
    largest 0.19 s.
  - Counted in whole samples: 22 % identical, 73 % within 2 samples (0.02 s), 92 % within 5 samples (0.05 s).
  - The fast picks are thus essentially the same times. The model was trained on centered onsets, yet it
    still places them well with the onset near the window end.
- **Latency.** In the fast run, 310 of the 398 in-window P picks were accepted from the first window, which
  ends 1 s after the trigger.
  - Median time from onset to available pick: 1.29 s (90th percentile 6.4 s), against 15.19 s
    (90th percentile 16.0 s) for the reliable setting.
- **Side effects.**
  - More picks: 542 P picks against 399.
  - 2.48 instead of 0.63 false P picks per station-hour.
  - P precision 0.78 against 0.84; P recall 0.86 against 0.84.
  - 26 instead of 14 S waves picked as P.
  - S picks are almost unchanged.
  - The early, mostly pre-trigger windows confirm more marginal triggers.

## 9. Cross-check with SeisBench (same weights)

**Same weights, shown numerically** (`seisbench/weights_check.json`). SeisBench downloaded
`PhaseNet.from_pretrained('instance')` and `EQTransformer.from_pretrained('stead')`, version 2 for both, into
the project's own cache.

- 6 real windows (GWYB, BAU, HAIA, JASA, MMD, YOA; P-centered, event 3) were normalized by SeisBench and fed to
  both networks.
- The outputs of torch and the ONNX files differ by about 1e-6: at most 6 × 10⁻⁷ (PhaseNet) and 9 × 10⁻⁷
  (EQTransformer), with the highest value at the same sample in every window. This is float32 rounding: the
  weights are identical.
  - On 15 other windows (S-centered and noise windows of 3 events), the independent verification found up to
    1.2 × 10⁻⁶ for PhaseNet, again with the same highest sample everywhere (verifier's file
    `runs/verify_gwangyang_dl/out/seisbench/weights_onnx_check.json`).
- Feeding the ONNX model the plugin's own normalization instead changes nothing for PhaseNet on these six
  windows (outputs differ by ≤ 1.4 × 10⁻⁵, no peak moves).
  - This does not hold for every window. The plugin removes the mean in double precision (`onnxmodel.cpp`),
    SeisBench in float32. On HG windows with a large DC offset (10⁵–10⁶ counts) and a weak signal (peaks of
    23–137 counts), this changes the normalized input by up to 0.6 % of its peak and the output by up to about
    3 × 10⁻³ (verifier's file `runs/verify_gwangyang_dl/out/seisbench/weights_onnx_check.json`; the raw
    windows are in `runs/verify_gwangyang_dl/seisbench/phasenet_instance_weight_test_windows.npz`).
  - No pick is affected: on those windows no peak lies within 3 × 10⁻³ of the 0.4 / 0.3 thresholds (peak
    values in the same file).
- For EQTransformer, SeisBench's 6-sample taper at both ends of the window is the only difference: inputs
  differ by up to 0.23 at those edge samples, outputs by at most 1 × 10⁻³, and no peak moves.

**Pick times, plugin minus SeisBench** (`seisbench/compare_seisbench_summary.json`; per pair, with dt in
whole samples: `seisbench/compare_seisbench_pairs.csv`). SeisBench used the plugin's thresholds (P 0.4, S 0.3),
`strict=True`, and all other settings at their defaults. Pairs were formed with the same rules as above.
dt = plugin time − SeisBench time. The fractions are counted in whole samples (section 1).

| model | phase | plugin / SeisBench picks | pairs | median \|dt\| | identical | within 0.02 s (2 samples) | within 0.05 s (5 samples) | p95 | max | mean dt | SeisBench recall / precision vs PhaseNet+ | plugin recall / precision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 399 / 415 | 352 | 0.010 s | 32 % | 83 % | 94 % | 0.060 s | 0.27 s | −0.0012 s | 0.864 / 0.871 | 0.842 / 0.842 |
| | S | 337 / 370 | 301 | 0.010 s | 21 % | 72 % | 96 % | 0.050 s | 0.13 s | +0.0016 s | 0.797 / 0.955 | 0.757 / 0.919 |
| eqtransformer_stead | P | 294 / 294 | 266 | 0.020 s | 21 % | 66 % | 94 % | 0.060 s | 0.15 s | +0.0023 s | 0.764 / 0.975 | 0.736 / 0.908 |
| | S | 292 / 336 | 267 | 0.020 s | 13 % | 60 % | 89 % | 0.070 s | 0.16 s | −0.0052 s | 0.749 / 0.938 | 0.650 / 0.897 |

- **Sign corrected on 2026-10-17.** Up to then `09_compare_seisbench.py` stored SeisBench minus plugin under
  the name plugin minus SeisBench, so every mean dt above had the opposite sign. The independent verification
  found this. The sizes of the offsets did not change.
- In the SeisBench-vs-PhaseNet+ comparison (`compare_seisbench_vs_reference.csv`, column `sb_dt_s`), dt is
  SeisBench minus PhaseNet+, the same convention as dt = DL − PhaseNet+ in the rest of this note.

**Reference picks found by only one of the two:**

| model | phase | only SeisBench | only plugin | neither |
|---|---|---|---|---|
| phasenet_instance | P | 12 | 4 | 45 |
| | S | 32 | 16 | 66 |
| eqtransformer_stead | P | 13 | 3 | 82 |
| | S | 41 | 1 | 100 |

Of the S picks only SeisBench finds, 29 of 32 (phasenet_instance) and 41 of 41 (eqtransformer_stead) are at
stations where the plugin had no P pick, so its S picker never ran. Of the 12 and 13 P picks only SeisBench
finds, 5 and 10 are "below minConfidence" in the plugin's centered window, and the rest had no picker (no
trigger, or the dead time). This comes from joining `seisbench/compare_seisbench_vs_reference.csv` with
`analysis/missed_reference_diagnosis.csv`.

The mean offsets (plugin minus SeisBench) are −0.0012 s (P) and +0.0016 s (S) for phasenet_instance, and
+0.0023 s (P) and −0.0052 s (S) for eqtransformer_stead. All are about half a sample (0.005 s) or less, with
both signs, so neither method is biased against the other. The differences come from how each one forms
windows and picks:

1. **Windows.**
   - The plugin runs one 30 s or 60 s window centered on the detector trigger (P), or four windows after the
     P pick (S). The onset usually sits near the window center, where the models are best.
   - SeisBench slides overlapping windows over the whole record and combines them.
     - PhaseNet: 1500-sample overlap, averaged, 2.5 s blinded at each window edge (the v2 weights' defaults).
     - EQTransformer: 3000-sample overlap, maximum taken, 5 s blinded.
   - So the onset sits at an arbitrary place in each window, and the probability curve at a sample combines
     two windows.
2. **Normalization.** Both normalize each window by its own peak, per component. Different windows contain
   different amplitudes (for example with or without the S wave), so the same onset is scaled differently.
3. **Pick rule.**
   - The plugin takes the most confident local maximum in its window that the S curve does not veto (P), or
     the largest S value after the P pick (S).
   - SeisBench takes the peak of every stretch above the threshold. Its trigger switches off at half the
     threshold.
   - SeisBench can therefore pick S waves without any P pick, and it never makes near-duplicates. These two
     effects explain the extra S picks that only SeisBench finds, and most plugin picks without a SeisBench
     partner (duplicates, isolated triggers, S waves picked as P).
4. **Resampling.** None in either case: the data and the models are both 100 Hz.
5. **The 6 ONNX files with a different input definition (step T).** These are eqtransformer_original,
   eqtransformer_original_nonconservative, obstransformer_obst2024 and eqtp_ncedc (SeisBench normalizes the
   three components together, and for the first three also filters), plus skynet_original and
   skynet_original_multiphase (joint peak). **None of the four models used here is among them**, so this
   does not matter for these results. The only preprocessing difference that remains here is
   EQTransformer's 6-sample taper, and it is negligible (see above).

## 10. End-to-end: double-difference relocation from the DL picks

**Catalog from the DL picks.**

- **Association by time window:** for each event, the DL picks between origin − 5 s and + 60 s
  (HYPOINVERSE origin), one per station and phase (the most confident).
- **Catalog conventions:** P on `<sensor>Z`, S on `<sensor>N`, no uncertainties, the same `station.csv` and
  `event_centroid_start.csv`.
- **Relocation:** pyrtdd, catalog only, 'hypodd_like':
  - clustering: numEllipsoids 0, maxNeighbourDist 10 km, minNumNeigh 1, maxNumNeigh 0, minNumPhases 1;
  - solver: absolute-location constraint 0, damping 0.01, default down-weighting 10 → 5;
  - travel times: NLLGrid kim1983, maxSearchDistance 0.1 m;
  - every option value is in `reloc/<solution>/settings.json`.
- **Control:** the reference picks, `phase.csv` (PhaseNet+), relocated with exactly the same settings. It
  separates the effect of the picks from the effect of the program (pyrtdd against HypoDD).
- **Variants**, all reported:
  - `window_tt`: picks more than 1.0 s from the kim1983 time (from the common start point) are dropped
    before choosing;
  - for the best model, a "matched only" pair: the same (event, station, phase) set, once with DL times and
    once with PhaseNet+ times.

**How solutions are compared.**

- **Metric (a), relative geometry.** Each solution is converted to east/north/up meters. Its own centroid is
  removed. Then the RMS over the 11 events of the 3-D difference is computed. All 11 events were relocated in
  every run.
- **Metric (b), absolute position.** The centroid shift: how far the whole cluster moved from its starting
  point (`reloc/centroid_shift_from_start.csv`; all runs start every event at HypoDD's ISTART=1 centroid,
  `event_centroid_start.csv`), and for each compared pair the solution centroid minus the reference centroid
  (columns `centroid_shift_*` of `reloc/compare_pairs.csv`). Metric (a) removes exactly this shift.

Extract from `reloc/compare_pairs.csv` (RMS in m, east / north / up in brackets) and
`reloc/centroid_shift_from_start.csv` (last column):

| solution | vs HypoDD dt.ct | vs HypoDD dt.cc | vs pyrtdd control (PhaseNet+ picks) | spread of the solution | cluster centroid moved from its start, m (E / N / U) |
|---|---|---|---|---|---|
| all events at one point (no information) | 69.1 | 50.4 (46.5 / 13.9 / 13.5) | 74.5 | 0 | 0 |
| HypoDD dt.ct (catalog only) | – | 51.3 (28.3 / 17.2 / 39.2) | 72.2 | 69.1 | 75 (0 / 23 / 72) |
| pyrtdd control, PhaseNet+ picks | 72.2 | 52.7 (17.0 / 8.6 / 49.2) | – | 74.5 | **1723 (1699 / 151 / 244)** |
| pyrtdd control, PhaseNet+ picks of the matched-only subset | 72.4 | 55.0 | 15.2 | 75.5 | 508 (402 / 302 / −74) |
| **DL phasenet_original, window** | 89.3 | 81.8 (18.9 / 9.9 / 78.9) | **49.1 (16.4 / 8.0 / 45.6)** | 96.9 | 82 (0 / −50 / −65) |
| DL phasenet_original, window_tt | 90.4 | 81.9 | 47.4 | 96.6 | 87 (−65 / −9 / 58) |
| DL phasenet_original, matched only | 86.9 | 73.0 | 38.2; 39.7 against the PhaseNet+ picks of the same subset (12.1 / 9.0 / 36.8) | 89.2 | 63 (−23 / 45 / 38) |
| DL phasenet_instance, window | 127.2 | 109.5 (59.4 / 24.9 / 88.6) | 84.0 | 121.9 | 360 (264 / 158 / −187) |
| DL phasenet_instance, window_tt | 145.3 | 128.7 | 105.8 | 138.2 | 418 (−31 / −234 / 345) |
| DL eqtransformer_stead, window (window_tt identical) | 128.7 | 130.5 | 102.8 | 141.6 | 478 (−173 / −161 / 416) |
| DL phasenet_stead, window (window_tt identical) | 150.3 | 141.2 | 111.2 | 151.3 | 320 (−83 / −243 / −191) |

HypoDD dt.cc moved its centroid only 1.1 m from the same start. Between the compared solutions (metric b in
`compare_pairs.csv`), the main DL solution's centroid lies 1739 m from the control's (E −1699, N −201,
U −309 m), and the matched-only solution's 509 m from that of its same-subset control (E −425, N −257,
U +112 m).

HypoDD's bootstrap 95 % half-widths (median over events) are 34 / 17 / 43 m (E / N / Z) for dt.ct and
3 / 2 / 6 m for dt.cc. Per event: `reloc/compare_per_event.csv` and `analysis/tables_reloc_per_event.md`.

What the numbers say, in plain words:

- **The cluster is tiny.** In the cross-correlation solution (dt.cc) the 11 events lie on average 50 m from
  their centroid. HYPOINVERSE scattered them by 585 m, mostly in depth. Every DD run collapses that to
  50–150 m.
- **Catalog-only DD cannot resolve this cluster's depth structure, whatever the picks.**
  - HypoDD dt.ct and the PhaseNet+ control are each about as far from dt.cc (51–53 m) as the "all at one point"
    solution (50 m).
  - They do recover the east-west stretching: east RMS 17–28 m against 46.5 m for one point.
  - But they add vertical scatter that dt.cc does not have: 39–49 m against 13.5 m.
- **The best model's picks give the same horizontal picture as the PhaseNet+ picks.**
  - Against the control: 16 m east and 8 m north RMS, inside dt.ct's bootstrap range.
  - In depth they add more scatter: 46 m RMS against the control, and 79 m against dt.cc.
- **Pick times alone account for about 40 m RMS, mostly vertical.** This is the matched-only pair: same
  observations, DL times against PhaseNet+ times, with a median |dt| of 0.025 s. In a tight cluster, relative
  depths hang on a few tens of milliseconds of S−P differences.
- **Caveat: the compared clusters do not sit at the same place.**
  - Catalog-only pyrtdd moved the whole PhaseNet+ control cluster 1.72 km from its start (E 1.70, N 0.15,
    U 0.24 km), the same-subset control 0.51 km, and the main DL solution only 0.08 km.
  - This is the known drift of catalog-only rtDD with absLocConstraint 0 and damping 0.01: nothing ties the
    cluster to an absolute position (note 07, section 6; `logs/07_gwangyang_pyrtdd_diag_centroid_drift.log`).
    The HypoDD runs moved theirs by 75 m (dt.ct) and 1 m (dt.cc).
  - Metric (a) removes each solution's centroid, so its numbers stand. But the "effect of the picks alone" and
    the DL-against-control numbers compare solutions that sit up to 1.7 km apart in absolute position. A
    catalog-only solution's absolute position is not meaningful.
  - I did not repeat the comparison with an absolute-location constraint or more damping: that would be a new
    relocator setting.
- **Missing picks make it worse for the other models.**
  - phasenet_instance, eqtransformer_stead and phasenet_stead lose 35–62 % of the small events' PhaseNet+
    picks, and their geometries scatter more (84–111 m against the control).
  - The geometry also reacts strongly to a few picks. Dropping 20 implausible picks (mostly S waves picked as
    P) from phasenet_instance (`window_tt`) moves the solution by 61 m RMS. Event 10, which has only 6–8 DL P picks,
    moves 170 m.
- **Conclusion.** The DL picks of the best model are good enough for catalog-level DD at the precision that
  catalog-only DD reaches here at all: tens of meters horizontally, poorly in depth. They are not good enough
  to replace cross-correlation for this cluster, and neither are the PhaseNet+ picks.
- **Residual RMS is not a quality measure here.** pyrtdd's `finalRms` (median 1.05–1.50 s for catalogs with
  wrong-phase or outlier picks) is dominated by a few picks with huge residuals that the solver gives zero
  weight. With those removed (`window_tt`), it is 0.21–0.29 s.

## 11. For the real-time test

- **Model:** `phasenet_original`, by the fixed rule. Configuration:
  `runs/gwangyang/dlpicker/config/scautopick_phasenet_original.cfg`.
- **Bindings** for all 54 stations:
  - `runs/gwangyang/dlpicker/config/bindings_config.xml`, made by `bindings2cfg` from the key files in
    `runs/gwangyang/dlpicker/config/key/`;
  - inventory: `data/gwangyang_11ev/inputs/inventory_sc.xml`.
- **Trade-off to keep in mind:**
  - phasenet_original has the best recall and F1 against PhaseNet+, but the most picks outside the event
    windows (1.26 P per station-hour).
  - eqtransformer_stead has almost none (0.04), but misses half of the small events' P picks.
  - If the associator struggles with false picks, phasenet_instance is the middle ground.
- **Fast picks:** the README's fast P settings cut the pick latency from about 15 s to about 1.3 s with
  almost the same pick times (92 % within 0.05 s, section 8). They give about four times as many false P picks
  (2.48 against 0.63 per station-hour).

## Caveats

- **PhaseNet+ is not ground truth.** Recall and precision measure agreement with another automatic picker. The
  unmatched-pick classes use a 1-D model (kim1983) and the HypoDD dt.cc locations, which themselves rest on the
  PhaseNet+ picks.
- **The magnitude classes are small:** 6 events below ML 1.5 and 5 above. Per-event numbers are in
  `analysis/by_event.csv`.
- **Only the reliable/fast choice and the four models were varied.** minConfidence, detector thresholds and
  dead time stay at the README/plugin values, as asked. Section 4 suggests minConfidence matters most.
- **The relocation comparison uses one relocator setting ('hypodd_like').** HypoDD's own runs differ:
  - P weight 1.0 against S weight 0.5 (pyrtdd: equal weights);
  - 7 iteration sets with their own cut-offs.

  The pyrtdd control shows this difference alone is 53–72 m RMS for these events.
- **Catalog-only pyrtdd lets the whole cluster drift** (up to 1.7 km here, section 10). Only relative
  geometry is compared; absolute positions of catalog-only solutions are not meaningful.
- **The SeisBench CPU times** include Python reading and data handling. They are fair for "same data, same
  thread count", not a tuned benchmark.

## Problems met

1. **SeisBench 0.11.0 in env dl-base cannot import `seisbench.models`.**
   - Error: `ImportError: Optional dependency 'xdas' is required. Install it with: pip install xdas`.
   - Cause: in `seisbench/models/das_base.py` a type annotation (`xdas.DataArray`) is evaluated at import time.
   - The env is read-only, so nothing was installed.
   - Fix: `09_seisbench_run.py` registers a stub module `xdas` with placeholder classes in its own process
     before importing SeisBench. The DAS code is never used.
   - A first stub that answered every attribute broke `inspect` (`'__file__'`). The final stub defines only
     `DataArray`, `Coordinate` and `InterpCoordinate`.
2. **`09_reloc.py` failed twice in its comparison part. Both times the relocations themselves had finished.**
   - `ValueError: output array is read-only`: fixed by not modifying `to_numpy()` views in place.
   - `FileNotFoundError` for a bootstrap table of the control: the bootstrap columns are read only from the two
     HypoDD tables.

   Both runs are in the log, followed by the successful re-runs.
3. **`window_tt` design check.** I first applied the travel-time check after choosing the most confident pick.
   I then changed it to apply the check first. The results were identical, so no station lost a plausible
   weaker pick.
4. **The CPU comparison was not like-for-like at first.** The first SeisBench run used 4 threads and the plugin
   uses 1. Stage `seisbench1` repeats the run with 1 thread; its picks are identical.
5. **Fixed after the independent verification (2026-10-17).** The findings are in
   `docs/results/verification_findings_gwangyang.md`.
   - Sign error: `09_compare_seisbench.py` stored SeisBench minus plugin as `dt_plugin_minus_seisbench_s`. It now
     stores plugin minus SeisBench; the mean offsets in section 9 changed sign, their sizes did not change.
   - "Within 0.02 s" was ill-defined for differences of exactly 2 samples plus a few microseconds. All
     "identical / within" fractions (sections 8 and 9) are now counted in whole samples, which raised some of
     them by 1–9 percentage points.
   - The relocation comparison did not report how far each cluster moved as a whole. `09_reloc.py` now writes
     the centroid shifts (metric b, section 10). The relocated catalogs did not change (byte-identical).
   - New driver stage `seisbench_compare` re-runs only `09_compare_seisbench.py`. Stages compare,
     seisbench_compare and reloc were re-run; pick and SeisBench runs were not repeated.

## Files

- **Driver:** `runs/gwangyang/dlpicker/scripts/09_dlpicker.sh`. Stages: prep, pick, compare, seisbench,
  seisbench1, seisbench_compare (only the plugin-vs-SeisBench comparison), reloc. It is a dry run without
  `--apply`.
- **Helpers:** `09_bindings.py`, `09_settings_json.py`, `09_compare.py`, `09_seisbench_run.py` (env dl-base),
  `09_weights_check.py`, `09_compare_seisbench.py`, `09_reloc.py` and `09_tables_md.py` (prints every table
  in this note from the result files).
- **Log:** `logs/09_gwangyang_dlpicker_20261017.log`.
- **Configuration and settings:**
  - `config/` (scautopick_*.cfg, key/, bindings_config.xml, stations_bound.csv);
  - `settings/` (per-variant JSON plus scautopick's dumps).
- **Picks:** `output/<variant>/<kma_id>/` (picks.xml, scautopick.log, time.txt).
- **Comparison:** `analysis/`:
  - summary_by_model.csv, by_event / by_sensor / by_distance / by_magnitude.csv;
  - dl_picks_all.csv, reference_vs_dl.csv;
  - unmatched_in_window.csv, unmatched_smallest_events.csv, missed_reference_diagnosis.csv;
  - outside_window.csv, station_hours.csv;
  - cost.csv, cost_per_run.csv;
  - fast_vs_reliable*.csv (fast_vs_reliable.csv has dt in whole samples), log_checks.csv;
  - best_model.json, summary.json, tables.md.
- **SeisBench:** `seisbench/`:
  - picks and settings per model, weights_check.json, compare_seisbench_* (the pairs table has dt in whole
    samples);
  - `threads1/`: the 1-thread run;
  - `cache/`: the downloaded weights.
- **Relocation:** `reloc/`:
  - one folder per solution, with its input catalog, relocated catalog, processing data and settings.json;
  - positions.csv, compare_pairs.csv (metric a and the pairwise centroid shift), compare_per_event.csv,
    centroid_shift_from_start.csv (metric b per solution), reloc_summary.json.

**How to reproduce.** Each stage takes seconds, except seisbench (about 1 min) and seisbench1 (about 1.5 min):

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/gwangyang/dlpicker
bash scripts/09_dlpicker.sh                       # dry run
bash scripts/09_dlpicker.sh --apply               # all stages
bash scripts/09_dlpicker.sh --apply --stage compare
bash scripts/09_dlpicker.sh --apply --stage seisbench_compare
bash scripts/09_dlpicker.sh --apply --stage reloc
# tables of this note, from the result files (env pyrtdd):
python -I scripts/09_tables_md.py --run-dir $PWD > analysis/tables.md
```
