# Step 12: the deep-learning picker in SeisComP on 26 San Ramon 2015 events (2026-10-17)

The deep-learning (DL) picker is scautopick plus the scdlrtpicker plugin: P picker DL3C (started by an STA/LTA
detector trigger) and S picker SDL3C (started by a P pick). I ran it offline on the 26 test events of the 2015
San Ramon swarm (Northern California, M 0.8–3.6, NCEDC data) with four models and compared the picks with the
**NCSS analyst picks**. I also measured false picks and cost, checked the first-motion polarity of
`eqtp_ncedc`, and cross-checked `eqtp_ncedc` against SeisBench.

**How to read the numbers.** Unlike Gwangyang (step 09), the reference here is human: reviewed picks of the
Northern California Seismic System (NCSS). But the analysts did not pick every station, and they picked S at only
163 station-events (against 2422 P). So:

- **recall** (share of analyst picks the DL picker found) is a fair measure;
- **precision** (share of DL picks that match an analyst pick) is a lower bound. Many DL picks without an analyst
  partner sit exactly where the arrival is expected (section 7). For S, precision against the analysts means
  almost nothing.

## Result in brief

- **Everything ran.** 216 picking runs (26 events × 8 variants, plus 8 start-up runs). No run printed an
  `[error]` line. The only warnings were 75 "Duplicate pick ... ignoring" lines from scautopick's own check.
  Nothing was written outside the project; `~/.seiscomp` does not exist and `~/.seisbench` is unchanged since 2021.
- **Many analyst picks cannot be reached by a 3-component picker in this test.** Of the 2585 usable analyst
  picks (2422 P, 163 S):
  - 694 P picks are at stations beyond 80 km, which have no waveforms in the playback files (by design);
  - **412 picks (411 P, 1 S) are at stations with data but no sensor the 3-component pickers can use**: 35
    vertical-only EH stations and one two-component borehole station. All 49 shipped models are 3-component;
    no 1-component model was used;
  - 543 picks (471 P, 72 S) are on **triggered strong-motion records** (NC and NP accelerometers). Their data
    start on average 43 s before the origin, so scautopick's detector (which waits `initTime` = 60 s after the
    first sample) is not running when the P arrives;
  - 936 picks (846 P, 90 S) are on complete 3-component records. This is where the models can be judged.
- **P recall, best model (`phasenet_instance`):** 0.31 of all analyst P picks, 0.43 of those with data, 0.56 at
  3-component stations, **0.82 at complete records**. `phasenet_original` is nearly the same (0.80),
  `phasenet_scedc` 0.67, **`eqtp_ncedc` only 0.62**. S recall at complete records is 0.80, 0.84, 0.58 and 0.76.
- **Best model by the rule fixed beforehand** (pooled P+S F1, recall over 3-component stations):
  `phasenet_instance` 0.505, then `phasenet_scedc` 0.488, `eqtp_ncedc` 0.460, `phasenet_original` 0.438.
  `phasenet_original` loses only on precision: it makes the most extra picks.
- **Pick times agree well with the analysts:** median |dt| 0.02–0.03 s for P. Agreement is best where the
  analyst was sure: for weight-0 picks the 95th percentile of |dt| is 0.06–0.12 s. The offsets are model
  properties, as in Gwangyang: `phasenet_instance` picks P 20 ms early, `phasenet_original` 42 ms late.
- **The swarm itself costs picks.** For events with another catalog event within 15 s, P recall at complete
  records drops to 0.43–0.56, against 0.71–0.89 for events with no other event within 120 s.
  - Reason: the plugin keeps one P pick per model window, the most confident one, and the dead time then
    blocks a second picker. When a larger event follows within seconds, its P "wins".
  - Example: the Md 2.32 foreshock 72540760, 6.3 s before the Mw 3.6 mainshock: P recall 0.04–0.09 for the
    PhaseNet models.
- **`eqtp_ncedc` is weaker here although it was trained on NCEDC data, and it costs 16-18 times as much CPU** (17.1 x phasenet_instance, 15.7 x phasenet_original, 18.1 x phasenet_scedc).
  - Its weights are identical to SeisBench's (largest output difference 2 × 10⁻⁵).
  - The plugin's different input normalisation is **not** the cause. On the plugin's own windows, SeisBench's
    normalisation would recover only 13 of its 154 low-confidence misses (and lose 10 of 617 hits).
  - The model's P value simply stays near zero (median 0.015) at many clear onsets, mostly on HH and HN
    channels.
  - SeisBench's continuous picking with the same weights finds twice as many P picks on 5 test events (0.84
    against 0.42). The difference comes from the plugin's triggering and windowing: triggered records, and one
    pick per 120 s window with a 60 s dead time. It does not come from the model.
- **`eqtp_ncedc` P polarity.**
  - Coverage: it gives a polarity for 83 % of the matched analyst first motions at the default
    `polarityMinConfidence` (0.5), 62 % at 0.7.
  - Agreement on normally oriented channels: 0.83 at 0.5 and 0.90 at 0.7.
  - Agreement for impulsive weight-0 onsets: 0.91 and 0.93. For emergent onsets it is near chance (0.53).
  - **On channels with a negative gain or a downward sensor** (BK boreholes, 51 comparisons) agreement is 0.21.
    An independent test shows that the analyst first motions on those channels follow the raw counts, not the
    ground motion (section 10). The plugin's dip/gain handling is consistent with the metadata.
- **Accelerometers work for P.** At 13 stations with both kinds of sensor, P recall on the HN accelerometer is
  only a little lower than on the velocity sensor (`phasenet_instance` 0.80 against 0.87). S suffers more
  (0.59 against 0.83).
- **False picks:** P picks per station-hour of pre-event noise: `phasenet_instance` 1.1, `eqtp_ncedc` 1.3,
  `phasenet_scedc` 1.8, `phasenet_original` 3.9. Some are confirmed by other models and may be uncatalogued
  swarm events.
- **Cost:** 0.22–0.25 CPU-s per station-hour for the PhaseNet models (4 ms per window); 3.9 for `eqtp_ncedc`
  (113 ms per window). These are whole scautopick processes on one thread.

## 1. What was run

- **Data.**
  - The 26 playback files `data/sanramon_2015/inputs/playback/<eventid>.mseed`: all channels of every sensor
    within 80 km that has metadata, origin −120 s to +120 s.
  - They are not in scmssort order: `scmssort -E -u` output differs from every file
    (`runs/sanramon_waveform_checks/scmssort_playback.txt`), so they were sorted here with `scmssort -u -E`.
  - 217 stations have data; 98–208 per event. The triggered NC/NP strong-motion recorders deliver data mostly
    for the larger events.
- **Inventory.** `fdsnxml2inv` of `inputs/stations.xml` gives `config/inventory_sc.xml`.
  - `scinv check` reports only information-level items and depth warnings (`config/scinv_check.txt`).
  - fdsnxml2inv warned about empty response resource ids (it generated new ones) and one coordinate conflict
    (WR.KPK).
- **Bindings** (`scripts/12_bindings.py`, key files, then `bindings2cfg`).
  - A scautopick binding names ONE sensor per station. Many San Ramon stations have several (BK: BH, HH, HN;
    NC: a vertical-only EH plus an HN).
  - Test for a usable sensor: a sensor counts as usable by the 3-component pickers if a Python copy of
    SeisComP's `getThreeComponents` finds a vertical and two horizontals for it in the inventory. Those three
    channels must have data, and an epoch must cover every event file. 1/2/3-named components (EP, CN, DP, HN
    at BK/NC boreholes) pass by their dips and azimuths.
  - **Main set** (one sensor per station, velocity sensors first: HH > EH > EP > DP > BH > HN > CN): 181
    stations bound. By sensor: HN 145, HH 15, EH 9, EP 9, CN 2, DP 1.
  - Not bound: 35 vertical-only EH stations, and BK.RB2B (two components each).
  - **hn set**: the accelerometer at the 13 stations whose main sensor is a velocity sensor. These are run as
    separate variants `<model>_hn` (section 5).
  - Of the 3291 station-event records of the main set, 1789 are complete. The other 1502 are triggered
    records: NC HN 1026, NP HN 474, NC EH 2. They start a median 36 s before the origin. (Strictly, 47 of these
    1502 have a gap and 13 start at the file start, so those 13 are not triggered records.)
- **Models and window settings.** All window settings come from each model's metadata (`windowLength` /
  `sampleRate`); the plugin defaults are kept otherwise (P `minConfidence` 0.4, S 0.3, `polarityMinConfidence`
  0.5, `polarityMaxTilt` 20°).

  | model | training data | window | P window (centred on the trigger) | dead time | S windows end after the P pick | ringBufferSize / leadTime |
  |---|---|---|---|---|---|---|
  | `eqtp_ncedc` | NCEDC (with polarity) | 120 s | ends 60 s after the trigger | 60 s | 60, 65, 70, 75 s | 300 / 180 s |
  | `phasenet_original` | Northern California (Zhu & Beroza) | 30.01 s | ends 15 s after | 15 s | 15, 20, 25, 30 s | 300 / 60 s |
  | `phasenet_scedc` | Southern California | 30.01 s | ends 15 s after | 15 s | 15, 20, 25, 30 s | 300 / 60 s |
  | `phasenet_instance` | Italy (INSTANCE) | 30.01 s | ends 15 s after | 15 s | 15, 20, 25, 30 s | 300 / 60 s |

  - **For the 120 s model:** the README asks for ringBufferSize and leadTime above the window. Rule used:
    ringBufferSize = max(300, 2.5 × window), leadTime = max(60, 1.5 × window).
    - `leadTime` has no effect in `--playback` mode (scautopick `picker.cpp:418-424`). It is set for a
      real-time copy of the configuration.
    - The P window starts 60 s before the trigger. The detector starts `initTime` = 60 s after the first sample.
      So with 120 s of data before the origin, the earliest possible window starts exactly at the first sample.
    - S windows are centred on S−P = 0, 5, 10 and 15 s; the most confident is kept. S−P at 80 km is about 10 s.
  - **The windows the plugin logged match these settings exactly** (`analysis/log_checks.csv`). P windows start
    60.00/59.99 s or 15.00/14.99 s before the trigger. S windows start 59.99, 54.99, 49.99 and 44.99 s (or
    15, 10, 5 and 0 s) before the P pick.
  - Every setting of every variant is in `settings/scautopick_<variant>.settings.json`, with scautopick's own
    `--dump-config`/`--dump-settings`.
- **Detector:** the README's permissive STA/LTA (5–20 Hz, 1/30 s, on 1.8, off 1.0), `amplMaxTimeWindow` 5 s,
  `minAmplOffset` 1.8, `killPendingSPickers` false. These are the same as in step 09.
- **Matching** (step 09 rules).
  - Same event file, same NET.STA, same phase. P within 0.5 s, S within 1.0 s; one-to-one, closest first.
    dt = DL − analyst.
  - Candidates are the analyst picks of every NCSS event in the file, so a DL pick of a neighbouring event
    counts as a correct pick of that event. Recall counts only the target event's picks.
  - Reference: weight codes 0–3. The 15 out-weighted picks (codes 5–8) are left out.
  - Event window: NCSS origin −5 s to +60 s.
  - Precision: DL picks in that window that match any analyst pick, divided by all DL picks in the window.
- **Predicted arrivals** (to classify DL picks without an analyst partner).
  - Computed with the project's `ray1d.py` through the NCSS CON model, with Vs = Vp/1.73, from the NCSS
    hypocentre.
  - Check against the analyst picks: P median residual −0.11 s and S +0.15 s; 97 % of both lie within 1 s.
  - So "within 1 s of the predicted time" (`--pred-tol`) is the "plausible arrival" test.

## 2. Which analyst picks a 3-component picker can use

Analyst picks (weight 0–3) of the 26 events, by what the station offers (`analysis/reference_picks.csv`):

| phase | no waveform (beyond 80 km) | data, but no usable 3-C sensor | 3-C sensor, triggered record | 3-C sensor, complete record | total |
|---|---|---|---|---|---|
| P | 694 | 411 | 471 | 846 | 2422 |
| S | 0 | 1 | 72 | 90 | 163 |

- **Stations the 3-component pickers cannot use: 412 analyst picks (411 P, 1 S).**
  - 398 of them were picked on vertical-only EH channels.
  - 13 were picked on the two-component borehole BK.RB2B (DP/CN).
  - The S pick is on the horizontal-only EL sensor of NC.CVP.
- **The analysts picked P mostly on EH channels** (1321 of 2422). Among picks with data, 398 of the 788 EH picks
  are at vertical-only stations.
- **17 NC stations have a vertical EH plus an HN accelerometer.** There the analysts picked P on the EH channel (239
  of 249 P picks) and S on the HN (35 of 37). The 3-component picker can use only the HN record, which at these
  stations is mostly continuous: 385 of 399 records are complete, and 243 of the 249 P picks are on complete records.
  (Corrected 2026-10-17; the first version called these HN records triggered.)
- **The HN analyst picks (571 P, 109 S) are almost all triggered records:** 466 of the 571 P picks.
- **Recall is given at four levels**: over all usable analyst picks, over picks with data, over picks at
  3-component stations ("3-C"), and over picks on complete 3-component records ("complete").

## 3. Agreement with the analyst picks, per model

From `analysis/summary_by_model.csv` (main binding set; F1 uses recall over 3-C stations):

| model | phase | recall, all | recall, with data | recall, 3-C | recall, complete | precision | precision counting plausible | F1 | median \|dt\| (s) | MAD (s) | p95 \|dt\| (s) | mean dt (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **phasenet_instance** | P | 743/2422 = 0.31 | 0.43 | 743/1317 = 0.56 | 690/846 = **0.82** | 959/1318 = 0.73 | 0.91 | 0.635 | 0.030 | 0.020 | 0.170 | −0.020 |
| | S | 79/163 = 0.48 | 0.48 | 79/162 = 0.49 | 72/90 = 0.80 | 100/970 = 0.10 | 0.71 | 0.170 | 0.050 | 0.030 | 0.130 | −0.041 |
| phasenet_original | P | 728/2422 = 0.30 | 0.42 | 728/1317 = 0.55 | 674/846 = 0.80 | 948/1490 = 0.64 | 0.82 | 0.592 | 0.028 | 0.020 | 0.186 | +0.042 |
| | S | 84/163 = 0.52 | 0.52 | 84/162 = 0.52 | 76/90 = 0.84 | 105/1399 = 0.08 | 0.63 | 0.131 | 0.035 | 0.025 | 0.170 | +0.054 |
| phasenet_scedc | P | 610/2422 = 0.25 | 0.35 | 610/1317 = 0.46 | 571/846 = 0.67 | 754/1025 = 0.74 | 0.84 | 0.568 | 0.032 | 0.033 | 0.250 | +0.034 |
| | S | 56/163 = 0.34 | 0.34 | 56/162 = 0.35 | 52/90 = 0.58 | 71/527 = 0.13 | 0.64 | 0.194 | 0.040 | 0.036 | 0.170 | +0.030 |
| eqtp_ncedc | P | 617/2422 = 0.25 | 0.36 | 617/1317 = 0.47 | 526/846 = 0.62 | 716/960 = 0.75 | 0.83 | 0.576 | 0.022 | 0.027 | 0.140 | +0.014 |
| | S | 73/163 = 0.45 | 0.45 | 73/162 = 0.45 | 68/90 = 0.76 | 83/805 = 0.10 | 0.58 | 0.168 | 0.030 | 0.040 | 0.173 | +0.004 |

- **Pooled P+S F1** (the ranking rule, `analysis/best_model.json`): phasenet_instance 0.505, phasenet_scedc
  0.488, eqtp_ncedc 0.460, phasenet_original 0.438.
  - The F1 is pulled down by the S precision, which only reflects how rarely the analysts picked S.
  - For P alone the order is phasenet_instance 0.635, phasenet_original 0.592, eqtp_ncedc 0.576, phasenet_scedc
    0.568.
- **"Precision counting plausible"** is an upper bound. It also counts as correct the unmatched DL picks that lie
  within 1 s of the predicted arrival where the analyst has no pick, or where the analyst pick is an outlier, or
  that fit another catalog event in the same file.
- **Timing offsets are model properties and repeat Gwangyang's.** `phasenet_instance` picks early (P −20 ms,
  S −41 ms), `phasenet_original` late (P +42 ms, S +54 ms). In Gwangyang the values against PhaseNet+ were
  −19 ms and +40 ms for P. A constant offset cancels in double differences.
- **Comparison with Gwangyang:** there, phasenet_original found 91 % of the PhaseNet+ P picks. Here the best
  models find 80–82 % of the analyst P picks on complete records. The reference is stricter (human), and the
  swarm overlaps events (section 4).

## 4. Where picks are lost

All breakdowns are in `analysis/by_*.csv`; the tables come from `analysis/tables.md`.

**By the sensor the picker used** (P recall on complete records, main set):

| bound sensor | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| HH (broadband) | 188 | 0.85 | 0.80 | 0.68 | **0.49** |
| EH (short period, 3-C) | 151 | 0.89 | 0.85 | 0.81 | 0.76 |
| EP (borehole geophone) | 125 | 0.74 | 0.74 | 0.71 | 0.60 |
| DP / CN (borehole, 500 Hz) | 7 / 32 | 1.00 / 0.88 | 1.00 / 0.91 | 0.71 / 0.88 | 1.00 / 0.81 |
| HN (accelerometer), complete records | 343 | 0.78 | 0.78 | 0.58 | 0.62 |
| HN, all records incl. triggered | 814 | 0.40 | 0.39 | 0.29 | 0.37 |

- **P precision by sensor** is 0.56–0.91. The lowest values are HN for `phasenet_original` (0.56) and DP (0.60, over 15 DL picks at the
  stations with the 7 DP analyst picks).
- **Resampling works.** The 200 Hz and 500 Hz data (HN, EP, CN, DP) and 40 Hz BH are resampled to 100 Hz by the
  plugin's Lanczos filter, with no visible penalty.
- **By the analyst's channel**, over picks with data:
  - HH 0.49–0.84, EP 0.60–0.75, CN 0.69–0.79;
  - **EH 0.32–0.39**: half of the EH picks are at vertical-only stations;
  - **HN 0.17–0.28**: these are triggered records.

**By distance** (P recall on complete records / P precision):

| distance | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0–20 km | 256 | 0.82 / 0.91 | 0.84 / 0.86 | 0.74 / 0.88 | 0.73 / 0.86 |
| 20–40 km | 300 | 0.84 / 0.73 | 0.81 / 0.62 | 0.66 / 0.72 | 0.64 / 0.74 |
| 40–60 km | 230 | 0.77 / 0.66 | 0.73 / 0.55 | 0.61 / 0.66 | 0.51 / 0.70 |
| 60–80 km | 60 | 0.85 / 0.52 | 0.82 / 0.48 | 0.72 / 0.61 | 0.48 / 0.50 |

- The PhaseNet models keep their recall out to 80 km. `eqtp_ncedc` loses it with distance.
- Precision falls with distance for all models. Many of the far "extra" picks are plausible arrivals that the
  analysts did not pick (section 7).

**By magnitude** (P recall on complete records):

| magnitude | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| M 0.5–1.0 (4 events) | 39 | 0.72 | 0.82 | 0.54 | 0.54 |
| M 1.0–1.5 (4) | 62 | 0.65 | 0.71 | 0.52 | 0.42 |
| M 1.5–2.0 (4) | 89 | 0.89 | 0.87 | 0.72 | 0.53 |
| M 2.0–2.5 (5) | 173 | 0.58 | 0.61 | 0.47 | 0.49 |
| M 2.5–3.0 (4) | 178 | 0.89 | 0.80 | 0.72 | 0.60 |
| M 3.0–3.6 (5) | 305 | 0.93 | 0.90 | 0.80 | 0.79 |

- **The dip at M 2.0–2.5 is not about size.** That bin holds the foreshock 72540760 and 71097774, both with a
  neighbouring event within 10 s (next table).
- **S recall on complete records** is 0.45–1.00 per bin. The bins hold only 11–18 picks each (`analysis/tables.md`
  T4b).

**By the time to the nearest other catalog event in the same file** (P recall on complete records;
`analysis/event_neighbours.csv` lists the neighbours):

| nearest other event | events | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|---|
| none within 120 s | 16 | 493 | 0.89 | 0.88 | 0.74 | 0.71 |
| 60–120 s | 2 | 47 | 0.81 | 0.85 | 0.70 | 0.40 |
| 15–60 s | 2 | 110 | 0.93 | 0.89 | 0.79 | 0.61 |
| ≤ 15 s | 6 | 196 | 0.56 | 0.52 | 0.43 | 0.47 |

- **Why a neighbour costs picks.** In a swarm, two events often lie a few seconds apart. The plugin runs one
  window per trigger and keeps only its most confident P peak. A window that covers both onsets keeps the larger
  one. The detector's dead time (15 s, or 60 s for `eqtp_ncedc`) then keeps the second onset from starting its
  own picker unless it is much stronger.
  - 72540760 (Md 2.32), 6.3 s before the Mw 3.6 mainshock: P recall 0.04–0.09 (PhaseNet) and 0.28 (eqtp).
    Its windows picked the mainshock P.
  - 71097904 (M 1.27), 12.1 s after an M 1.23 event: 0.00–0.29.
- **The 120 s window of `eqtp_ncedc` reaches further.** It also loses events with a neighbour 48–65 s away:
  72541095 (0.34 against 0.72–0.91 for the PhaseNet models) and 72545170 (0.37 against 0.80–0.87).

**By analyst pick quality** (P at 3-C stations; recall, then median / p95 |dt| in s):

| weight code | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0 (full weight) | 282 | 0.79; 0.022 / 0.062 | 0.79; 0.020 / 0.090 | 0.76; 0.020 / 0.120 | 0.74; 0.020 / 0.087 |
| 1 | 336 | 0.58; 0.020 / 0.117 | 0.58; 0.029 / 0.130 | 0.50; 0.030 / 0.190 | 0.53; 0.020 / 0.120 |
| 2 | 568 | 0.49; 0.050 / 0.193 | 0.47; 0.038 / 0.240 | 0.36; 0.058 / 0.320 | 0.37; 0.037 / 0.188 |
| 3 | 131 | 0.36; 0.060 / 0.392 | 0.34; 0.084 / 0.457 | 0.19; 0.080 / 0.459 | 0.17; 0.060 / 0.453 |

- The DL picker finds the onsets the analyst was sure about, and agrees with them closely.
- The |dt| for weight 2–3 picks reflects the analysts' own uncertainty: 0.2 and 0.3 s in the NCSS convention.

## 5. Velocity sensor against accelerometer at the same 13 stations

The `_hn` variants bind the HN (or CN) accelerometer at the 13 stations whose main sensor is HH (7), EP (3),
EH (2) or DP (1). All their records are complete. Same models, same events, same analyst picks
(`analysis/accelerometer_vs_velocity.csv`):

| model | phase | recall, velocity sensor | recall, accelerometer | precision, velocity / accel. | p95 \|dt\|, velocity / accel. (s) |
|---|---|---|---|---|---|
| phasenet_instance | P | 208/240 = 0.87 | 192/240 = 0.80 | 0.88 / 0.88 | 0.157 / 0.154 |
| | S | 34/41 = 0.83 | 24/41 = 0.59 | | |
| phasenet_original | P | 202/240 = 0.84 | 194/240 = 0.81 | 0.83 / 0.83 | 0.138 / 0.168 |
| | S | 34/41 = 0.83 | 32/41 = 0.78 | | |
| phasenet_scedc | P | 173/240 = 0.72 | 161/240 = 0.67 | 0.89 / 0.91 | 0.118 / 0.168 |
| | S | 21/41 = 0.51 | 18/41 = 0.44 | | |
| eqtp_ncedc | P | 155/240 = 0.65 | 163/240 = 0.68 | 0.80 / 0.85 | 0.113 / 0.110 |
| | S | 32/41 = 0.78 | 21/41 = 0.51 | | |

- **For P, the accelerometer costs 3–7 percentage points of recall** (eqtp: none) and nothing in precision or
  timing.
- **For S the loss is larger** for some models: phasenet_instance 0.83 → 0.59.
- So continuous strong-motion channels are a usable fallback where no velocity sensor exists. The problem with
  most HN stations in this data set is the triggered recording, not the sensor (section 6).
- False P picks per station-hour at these 13 stations: 0.2–1.9 for the accelerometers
  (`analysis/outside_window.csv`).

## 6. Why analyst picks at 3-C stations were missed

From the `--debug` logs (`analysis/missed_reference_diagnosis.csv`). For each missed pick the script checks
whether a model window covered the onset, what the best model value in it was, and whether a trigger was near.

**Complete records:**

| model | missed P | below minConfidence | no trigger | trigger but dead time | window picked another time | vetoed as S | missed S | no P pick so no S picker | S window picked another time | S below minConfidence |
|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | 156 | 30 | 42 | 4 | 79 | 1 | 18 | 4 | 10 | 3 (+1 no window) |
| phasenet_original | 172 | 19 | 42 | 4 | 107 | 0 | 14 | 6 | 7 | 0 (+1) |
| phasenet_scedc | 275 | 136 | 42 | 4 | 91 | 2 | 38 | 10 | 6 | 21 (+1) |
| eqtp_ncedc | 320 | 144 | 37 | 18 | 119 | 2 | 22 | 7 | 14 | 1 |

- **"Window picked another time" is the swarm effect of section 4.** Of these misses, 64–82 (PhaseNet) and 69
  (eqtp) are in the 6 events with a neighbour within 15 s.
- **"Below minConfidence" splits the models.**
  - For phasenet_instance and phasenet_original it is rare (19–30). The best value in those windows was mostly
    0.1–0.4.
  - For phasenet_scedc (136) the values lie spread over 0–0.4; a lower threshold would recover many.
  - For **eqtp_ncedc (144) the value was ≤ 0.1 in 92 cases** (81 in (0, 0.1] plus 11 at exactly 0.00): the model does not see these onsets. 105 of its
    144 are in events with no neighbour, and the median SNR at those onsets is 9 dB. So these are clear
    arrivals.
- **"No trigger" (37–42)**: the permissive detector missed few onsets.

**Triggered records** (471 P, 72 S analyst picks):

- **410 of these 471 P picks are lost as "record starts too late"** (342 for eqtp_ncedc): the onset comes before
  record start + 60 s, so the detector was not yet running. P recall on triggered records is 0.08–0.11 for the
  PhaseNet models.
- **Missed S picks there are "no P pick, so no S picker"** (59–65).
- **`eqtp_ncedc` still picks 19 % of these P onsets.** A later trigger on such a record (for example on the S
  wave) gets a 120 s window that reaches back to the P.
- **In real time this matters less than it seems.** The triggered NetQuakes-type (NC) and NSMP (NP) recorders
  do not stream continuously, so a real-time SeisComP would not see them at all.

## 7. DL picks without an analyst partner

Unmatched DL picks inside the event windows, classified automatically (rules in the header of
`scripts/12_compare.py`; `analysis/unmatched_in_window.csv`):

| model | phase | plausible, analyst did not pick | plausible arrival of another catalog event | near-duplicate | phase confusion | timing disagreement | noise / other |
|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 207 | 37 | 32 | 12 | 11 | 58 |
| | S | 474 | 117 | 30 | 4 | 0 | 245 |
| phasenet_original | P | 219 | 55 | 31 | 30 | 18 | 187 |
| | S | 623 | 156 | 54 | 2 | 0 | 459 |
| phasenet_scedc | P | 88 | 15 | 33 | 26 | 16 | 91 |
| | S | 214 | 50 | 17 | 29 | 0 | 146 |
| eqtp_ncedc | P | 70 | 12 | 109 | 4 | 13 | 35 |
| | S | 350 | 33 | 105 | 23 | 0 | 211 |

(2 or fewer "analyst pick is an outlier" cases per model are left out.)

- **Most unmatched P picks are plausible.** They lie within 1 s of the predicted P where the analyst made no
  pick. Noise P picks are fewest for eqtp_ncedc (35 of 960 P picks in the windows) and phasenet_instance (58 of
  1318); phasenet_original has 187 of 1490.
- **`eqtp_ncedc` makes many near-duplicates** (109 P, 105 S). An earlier noise trigger's 120 s window already
  contains the onset, and the real trigger then picks it again.
- **S picks:** the analysts picked S at only 163 station-events, so most DL S picks have no partner.
  - Half or more are plausible.
  - The "noise" S picks lie mostly 1–30 s after the predicted S. The S picker always returns the strongest S
    value after its P pick, which can be in the coda.
  - S precision against the analysts (0.08–0.14) therefore says little. A real S benchmark here would need
    another reference.

## 8. Picks outside the event windows

- **Counting span.** Picks are counted only in one span that is the same for all models. It runs from the
  record start + `initTime` to the record end − 60 s (the largest P-window end of all models), minus every
  NCSS catalog event window (−5 to +60 s, 706 events). In these 240 s files that is the pre-event noise from
  −60 s to −5 s on complete records: 25.0 station-hours.
- **Coincident** means P picks at ≥ 3 stations within ±10 s.
- Source: `analysis/outside_window.csv`.

| model | phase | DL picks outside the windows | in another catalog event's window | in the common noise span | false picks per station-hour | on HH | on HN | on EH | on EP |
|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 200 | 56 | 27 (8 coincident) | **1.08** | 2.05 | 0.58 | 1.54 | 1.23 |
| | S | 96 | 77 | 4 | 0.16 | | | | |
| phasenet_original | P | 364 | 74 | 98 (42 coincident) | **3.93** | 5.59 | 3.41 | 3.08 | 4.00 |
| | S | 225 | 122 | 46 | 1.84 | | | | |
| phasenet_scedc | P | 236 | 48 | 46 (2 coincident) | **1.84** | 3.54 | 1.50 | 0.62 | 1.23 |
| | S | 65 | 37 | 8 | 0.32 | | | | |
| eqtp_ncedc | P | 182 | 53 | 32 (5 coincident) | **1.28** | 3.17 | 0.58 | 1.54 | 0.92 |
| | S | 52 | 38 | 9 | 0.36 | | | | |

- **Some of these are probably real.** Of the P picks in the noise span, the share confirmed by at least one
  other model at the same station within 0.5 s is:
  - phasenet_instance 19 of 27,
  - phasenet_original 27 of 98,
  - phasenet_scedc 13 of 46,
  - eqtp_ncedc 9 of 32.

  The swarm had many events below the catalog's completeness, so the confirmed ones are likely small
  uncatalogued events.
- **Broadband HH channels give the most false P picks** for every model.
- **Ranking:** phasenet_original makes 3–4 times as many as phasenet_instance, as in Gwangyang (1.26 against
  0.63 there).

## 9. Cost

These are CPU seconds of the whole scautopick process (`/usr/bin/time`), 26 runs per model, 6 runs at a time
(CPU time is per process; wall time is affected). ONNX Runtime runs on one thread. Source: `analysis/cost.csv`.

| model | CPU s | station-hours | CPU s per station-hour | triggers | P / S model windows | ms per window | peak memory |
|---|---|---|---|---|---|---|---|
| phasenet_instance | 40.6 | 177.1 | 0.229 | 5114 | 4033 / 6036 | 3.8 | 304 MB |
| phasenet_original | 44.2 | 177.1 | 0.250 | 5114 | 4033 / 7313 | 3.7 | 308 MB |
| phasenet_scedc | 38.3 | 177.1 | 0.216 | 5114 | 4033 / 4958 | 4.0 | 260 MB |
| eqtp_ncedc | 694.2 | 177.1 | **3.920** | 5114 | 2259 / 3852 | **113.2** | 364 MB |

- **Start-up:** 0.08–0.10 CPU-s on a 10 s probe file.
- **Detector triggers:** 29 per station-hour. The detector is the same for all models; only the dead time
  differs, so `eqtp_ncedc` runs fewer P windows.
- **`eqtp_ncedc` costs 16-18 times as much per station-hour as the PhaseNet models** (15.7-18.1 x). Its 12000-sample transformer
  needs 113 ms per window.
- **SeisBench's continuous EQTP picking** (one torch thread, 5 events) needed 5.7 CPU-s per station-hour,
  1.5 times the plugin (section 11).

## 10. `eqtp_ncedc` first-motion polarity against the analysts

- **Pairs used:** matched P picks whose analyst pick has a first motion U or D.
- **How the plugin sets the polarity:** it reads the up/down rows at the pick sample, sets the polarity when the
  larger of the two reaches `polarityMinConfidence`, and refers it to ground motion. Up and down are swapped
  when the vertical's inventory dip is +90° or its gain is negative.
- **Coverage at 0.7** is the subset with `polarity_confidence` ≥ 0.7. Picks do not depend on this threshold.
- Source: `analysis/polarity_pairs.csv`, `summary.json` → polarity.

**Main binding set:** 1951 analyst first motions in total, 1120 at 3-C stations, 575 matched.

| group | n | coverage (0.5) | agreement (0.5) | agreement if the swap is undone (0.5) | coverage (0.7) | agreement (0.7) |
|---|---|---|---|---|---|---|
| all | 575 | 0.83 | 0.77 | 0.83 | 0.62 | 0.83 |
| normally oriented vertical (dip −90, gain > 0) | 524 | 0.83 | **0.83** | 0.83 | 0.61 | **0.90** |
| inverted vertical (gain < 0 or dip +90) | 51 | 0.82 | **0.21** | **0.79** | 0.67 | 0.21 |
| impulsive onset (I) | 384 | 0.87 | 0.88 | 0.92 | 0.72 | 0.91 |
| emergent onset (E) | 191 | 0.73 | 0.53 | 0.61 | 0.41 | 0.56 |
| analyst weight 0 | 208 | 0.90 | 0.91 | 0.94 | 0.80 | 0.93 |
| analyst weight 1 | 176 | 0.84 | 0.84 | 0.88 | 0.62 | 0.89 |
| analyst weight 2 | 191 | 0.73 | 0.53 | 0.61 | 0.41 | 0.56 |
| bound HH | 90 | 0.79 | 0.93 | 0.93 | 0.64 | 0.97 |
| bound EH | 105 | 0.90 | 0.86 | 0.86 | 0.68 | 0.93 |
| bound HN | 282 | 0.80 | 0.76 | 0.76 | 0.56 | 0.85 |
| 40–60 km | 123 | 0.79 | 0.52 | 0.66 | 0.49 | 0.58 |

- **The hn set** (accelerometers at the 13 velocity-sensor stations, almost all normal orientation) gives 156
  pairs: coverage 0.84 / 0.72, agreement 0.94 / 0.95 at 0.5 / 0.7.
- **Where polarity is reliable:** on normally oriented channels it agrees with the analysts in 83 % (threshold
  0.5) to 90 % (0.7) of cases. For impulsive, full-weight onsets the figure is 91–93 %. For emergent weight-2
  onsets and at 40–60 km it is close to chance. **0.7 is the better threshold** if the polarities feed focal
  mechanisms: it gives up a quarter of the coverage for clearly better agreement.
- **Stations that always disagree** (≥ 3 comparisons): BK.MHDL (8 of 8) and BK.SBRN (6 of 6), both with a
  negative gain on EP1, and NP.1804 (3 of 3, normal orientation).
- **What the analysts' first motions on inverted channels mean** (`scripts/12_polarity_reference_check.py`, no DL
  model involved).
  - Test: for every analyst first motion on such a channel (all 685 benchmark events), I took the analyst first
    motions of the same event on normal channels with a similar ray (azimuth and take-off angle within 10°,
    at least 2, with a ≥ 70 % majority). Rays this similar should usually show the same first motion.
  - Inverted channels match their neighbours in only **0.32 of 148 tests**. The control, normal channels, match
    in 0.70 of 809.
  - Per channel: BK.MHDL.EP1 0.12 (50 tests), BK.OXMT.EP1 0.30 (44), BK.SBRN.EP1 0.50 (16), BK.VALB.EP1 0.58 (12).
  - Conclusion: the NCSS archive first motions on these channels, at least at MHDL and OXMT, follow the raw
    counts and not the ground motion. The plugin's swap is consistent with the StationXML. For focal
    mechanisms, use the plugin's polarity as it is, and do not use the NCSS first motions of those channels
    without correcting them.

## 11. Cross-check with SeisBench (`eqtp_ncedc`, 5 events)

- **Events:** 72540765 (Mw 3.6), 72542520 (M 3.23), 72541095 (M 2.79), 72545170 (M 1.96), 72537850 (M 1.14).
  They mix events with and without neighbours, and include two where the plugin's eqtp did badly.
- **Model:** SeisBench 0.11 `EQTP.from_pretrained('ncedc')` v1, run read-only in env dl-base, CPU, one thread.
  The weights were downloaded into the project's own cache.
- **Input:** the same raw streams as the plugin (the bound sensor's vertical, first and second horizontal),
  renamed in memory to Z/N/E so that SeisBench uses the plugin's component order. SeisBench resamples to
  100 Hz itself.
- **Thresholds:** P 0.4, S 0.3, polarity 0.5, `strict=True`; everything else at SeisBench's defaults
  (`seisbench/eqtp_ncedc_settings.json`).

**Same weights.** On 8 identical, already normalised mainshock windows, the ONNX file and the torch model differ
by at most 2 × 10⁻⁵ (`seisbench/weights_check.json`).

**The plugin's input normalisation is not the problem.**

- The difference: the plugin divides each component by its own standard deviation. SeisBench divides all three
  by one and tapers 6 samples at each end.
- On the 8 test windows this changes the outputs by up to 0.41, but P peaks move by at most 1 sample and every
  polarity stays the same.
- The decisive test (`scripts/12_normalization_test.py`): re-run the model on **exactly the windows the plugin
  evaluated**, read back from its log, with both normalisations. My recomputed window maxima reproduce the
  logged values to 0.005.

| windows | n | P ≥ 0.4 near the analyst pick, plugin input | same, SeisBench input | median P near the pick (plugin / SeisBench input) |
|---|---|---|---|---|
| analyst P picks the plugin missed "below minConfidence" | 154 | 2 | 13 | 0.015 / 0.014 |
| analyst P picks the plugin matched | 617 | 614 | 604 | 0.956 / 0.956 |

**Plugin against SeisBench, same weights and data** (`seisbench/compare_seisbench_summary.json`):

| phase | method | picks | recall, 3-C | recall, complete | recall, triggered | precision | median \|dt\| vs analyst | polarity coverage / agreement |
|---|---|---|---|---|---|---|---|---|
| P | plugin | 329 | 158/380 = 0.42 | 0.58 | 0.19 | 0.78 | 0.030 s | 0.82 / 0.76 |
| P | SeisBench | 678 | 321/380 = 0.84 | 0.82 | 0.88 | 0.74 | 0.032 s | 0.85 / 0.82 |
| S | plugin | 249 | 12/27 = 0.44 | 0.67 | 0.27 | 0.06 | 0.030 s | |
| S | SeisBench | 779 | 25/27 = 0.93 | 0.92 | 0.93 | 0.05 | 0.048 s | |

- **Where both pick, the times agree.**
  - P: 278 pairs, median |dt| 0.020 s, 83 % within 0.05 s, mean −0.008 s.
  - S: 199 pairs, median 0.020 s.
  - Polarity: of 166 pairs with a polarity from both, 93 % agree.
- **The 168 analyst P picks only SeisBench found**, by the plugin's reason for missing them:
  - 100 are on triggered records ("record starts too late");
  - 50 are "window picked another time" (43 on complete records);
  - 14 had no trigger or fell in the dead time;
  - only 4 were "below minConfidence".

  The plugin found 5 that SeisBench did not.
- **So the gap is the plugin's trigger-and-window design, not the model.**
  - Continuous sliding windows see triggered records and do not have to choose one P per 120 s.
  - SeisBench also scores higher on polarity agreement. Part of that comes from SeisBench reporting raw-count
    polarity, which matches the analysts on the inverted channels (section 10).
- **On complete records, even SeisBench's EQTP stays below the plugin's PhaseNet models**: 0.82 here, against
  199/221 = 0.90 for `phasenet_instance` and 0.88 for `phasenet_original` on the same 5 events
  (`analysis/reference_vs_dl.csv`).
- **Counting the triggered records too, SeisBench's continuous EQTP (0.84) beats the plugin's
  `phasenet_instance` (249/380 = 0.66)** on these events. Continuous picking of the triggered strong-motion
  records is worth that much here.

## 12. For the real-time setup

- **Model:** `phasenet_instance`, by the fixed rule. Configuration:
  `runs/sanramon/dlpicker/config/scautopick_phasenet_instance.cfg`. Bindings:
  `runs/sanramon/dlpicker/config/bindings_main.xml` (key files in `config/key_main/`); inventory:
  `config/inventory_sc.xml`.
  - It has the best P recall (0.82 on complete records), the fewest noise picks, and 1.1 false P picks per
    station-hour.
  - `phasenet_original` is an equal picker (0.80) but makes 3.9 false P picks per station-hour.
- **For polarity, `eqtp_ncedc` is the only option.** It is weaker as a picker and 16-18 times as expensive.
  - A practical split would run a PhaseNet model for picks, and EQTP only for the polarity at those pick times.
    The plugin cannot do that today: polarity comes only from the P picker's own model.
  - Use `polarityMinConfidence` 0.7 for focal mechanisms.
- **Swarms:** one P per window plus the dead time loses the smaller of two events a few seconds apart.
  - Shorter windows (PhaseNet) suffer less than 120 s windows.
  - Shorter dead times or several windows per trigger (README "fast"/"best" strategies) might recover some; not
    tested here.
- **Vertical-only stations** (35 here, 398 analyst P picks) are lost to a 3-component picker. Using them needs a
  1-component model, which the plugin supports (DL1C) but which is not among the shipped models.

## Caveats

- **The analyst picks are the reference, and they are incomplete.**
  - Precision is a lower bound. Most extra P picks fit the predicted arrival.
  - S was picked at only 163 station-events, so S precision is not meaningful and S recall rests on 90 picks
    on complete records.
  - The NCSS first motions on inverted channels seem to follow raw counts (section 10).
- **NCSS picks are mostly P** and mostly on EH channels. Many EH stations are vertical-only. The breakdowns
  "by analyst channel" and "by bound sensor" differ for that reason.
- **Strong-motion HN channels.**
  - Most are triggered recorders (NC "C"/"J" stations, NSMP). Their records start about 36–44 s before the
    origin and are often short.
  - Their poor recall in this offline test (0.29–0.40) is a property of the data and of scautopick's
    `initTime`, not of the models. On continuous HN channels the models work almost as well as on velocity
    sensors (section 5).
  - A lower `initTime` was not tried.
- **Only the models and the binding set were varied.** Thresholds, detector settings and dead times stay at the
  README/plugin values, as in step 09.
- **Small groups:** 4–5 events per magnitude bin, 6 events with a neighbour within 15 s, 13 stations in the
  accelerometer comparison, 5 events in the SeisBench check. Per-event numbers are in `analysis/by_event.csv`.
- **Predicted arrivals** come from a 1-D model without station corrections (97 % of analyst picks within 1 s).
  The "plausible" classes are therefore approximate.
- **CPU:** six scautopick runs at a time on a shared 32-core machine. CPU time per run is unaffected; wall time
  is not a benchmark. The SeisBench CPU time includes Python I/O.

## Problems met

1. **The first comparison run was too slow.** Predicted times took 0.9 s per ray1d call at 10 m / 6000 rays,
   for ~150 receiver heights per event. I stopped it and changed `12_compare.py` to 0.1 km receiver-height steps
   and 20 m / 2000 rays. Those times agree within 0.1 ms with the original setting, which matches the NCSS
   TTGEN table to 6 ms.
2. **The first false-pick rates used each model's own span.** For the 120 s model, picks can lie up to 60 s
   before the first possible trigger, outside that span. I changed this to one span for all models (section 8)
   before writing this note. The first numbers are not used.
3. **`12_compare_seisbench.py` failed once on pandas date parsing** of mixed ISO strings. Fixed with
   `format="ISO8601"`; the seisbench stage was then re-run in full and gave the same 1457 SeisBench picks.
4. **`12_normalization_test.py`: obspy's Lanczos interpolation cannot downsample at a window edge.** I used
   `Trace.resample` (FFT) for the 200/500/40 Hz rows; those rows are flagged. The 100 Hz rows alone give the
   same conclusion (0 against 8 of 118 recovered).

## Files

- **Driver:** `runs/sanramon/dlpicker/scripts/12_dlpicker.sh`. Stages: prep, pick, compare, seisbench, tables. It
  is a dry run without `--apply`.
- **Helpers:**
  - `12_bindings.py`, `12_settings_json.py`, `12_pick_one.sh`, `12_compare.py`;
  - `12_seisbench_run.py` (env dl-base, read-only), `12_weights_check.py`, `12_compare_seisbench.py`;
  - `12_normalization_test.py`, `12_polarity_reference_check.py`;
  - `12_tables_md.py` (prints every table of this note into `analysis/tables.md`).
- **Log:** `logs/12_sanramon_dlpicker_20261017.log`.
- **Configuration:** `config/`:
  - `inventory_sc.xml`, `scinv_check.txt`;
  - `scautopick_<model>.cfg`;
  - `key_main/`, `key_hn/`, `bindings_main.xml`, `bindings_hn.xml`;
  - `stations_bound.csv` (every station, its sensors, the decision and the reasons);
  - `coverage_bound.csv` (every station-event record: start, end, complete);
  - `bound_channels.csv` (Z/H1/H2 roles, dip, gain, polarity sense).
- **Settings:** `settings/` (per-variant JSON and scautopick dumps).
- **Picks:** `output/<variant>/<eventid>/` (picks.xml, scautopick.log, time.txt).
- **Comparison:** `analysis/`:
  - summary_by_model.csv, by_tier / by_bound_sensor / by_analyst_channel / by_distance / by_magnitude /
    by_neighbour / by_weight_code / by_event.csv;
  - accelerometer_vs_velocity.csv, event_neighbours.csv;
  - reference_picks.csv, reference_vs_dl.csv, dl_picks_all.csv;
  - missed_reference_diagnosis.csv, unmatched_in_window.csv, outside_window.csv, station_hours.csv;
  - cost.csv, cost_per_run.csv, log_checks.csv;
  - polarity_pairs.csv, polarity_by_station_*.csv, polarity_reference_check.{csv,json};
  - normalization_test.{csv,json};
  - best_model.json, summary.json, tables.md.
- **SeisBench:** `seisbench/`:
  - eqtp_ncedc_picks.csv, eqtp_ncedc_settings.json, eqtp_ncedc_weights_test.npz;
  - weights_check.json, compare_seisbench_*;
  - `cache/` (the downloaded weights).

**How to reproduce.** The prep stage takes about 1 min, pick about 5 min (6 at a time), compare about 7 min,
seisbench about 7 min and tables a few seconds:

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/sanramon/dlpicker
bash scripts/12_dlpicker.sh                       # dry run
bash scripts/12_dlpicker.sh --apply               # all stages
bash scripts/12_dlpicker.sh --apply --stage compare
```
