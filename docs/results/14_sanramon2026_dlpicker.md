# Step 14: the deep-learning picker on 26 events of the San Ramon 2025-26 sequence, same settings as 2015 (2026-10-18)

This step repeats step 12 (`docs/results/12_sanramon_dlpicker.md`, the 2015 San Ramon swarm) on the 2025-26 San
Ramon sequence. The deep-learning (DL) picker is again scautopick with the scdlrtpicker plugin: the P picker DL3C
(started by an STA/LTA detector trigger) and the S picker SDL3C (started by a P pick), in SeisComP 7.4.0.

**Nothing in the picker set-up was changed.** The run uses the same four models, the same window settings taken
from each model's metadata, and the same detector, thresholds and buffers. Stations are bound by the same two rules
("main" and "hn"). The pick matching, the reference rule and the four recall denominators are the same, and so is
the polarity analysis. The scripts are copies of the step-12 scripts; their headers list the few case changes
(data paths, the top magnitude bin 3.0–4.18, and the time window of the polarity reference check). The 26 test
events are the analyst-reviewed events of `data/sanramon_2026/inputs/dl_subset_events.csv`: M 0.60–4.18, including
the Mw 4.18 mainshock 75305736 and the overlap test event 75283011 (Md 2.29, 5.5 s before an Mw 3.77).

**How to read the numbers** (as in step 12):

- The reference is the set of NCSS analyst picks. The analysts did not pick every station, and they picked S at
  only 229 station-events (against 3329 P).
- **Recall** is the share of analyst picks that the DL picker found. It is a fair measure.
- **Precision** is the share of DL picks that match an analyst pick. It is only a lower bound, and for S it means
  almost nothing.
- Recall is given over four sets of analyst picks:
  - **all**: every usable analyst pick;
  - **with data**: picks at stations that have waveforms in the playback file;
  - **3-C**: picks at stations with a sensor the 3-component models can use;
  - **complete**: picks on 3-component records that cover the whole file in one piece.

## Result in brief

- **Everything ran.** There were 216 picking runs: 26 events × 8 variants, plus 8 start-up runs.
  - The 4 main variants printed no `[error]` line.
  - Each run of the 4 "hn" variants printed one `[error]`: "Ambiguous vertical component across epochs for
    BK.BRK.00.HN".
  - The warnings were 230 "Duplicate pick … ignoring" lines from scautopick's own check, plus 13 polarity-tilt
    warnings at BK.BRK.
  - Nothing was written outside the project. `~/.seiscomp` does not exist, and no ONNX telemetry folder was made.
- **The data are much better for a 3-component picker than in 2015.**
  - In 2015, 46 % of the station-event records were triggered strong-motion records that start about 40 s before
    the origin, too late for the detector.
  - Now 4625 of the 4681 records (99 %) are complete. The NP strong-motion records are continuous in the archive,
    and most of the triggered NC NetQuakes sites (C0xx/J0xx) are gone.
  - Only 13 analyst P picks lie on triggered records (2015: 471).
  - One new loss comes from the binding rule itself. NC.CSR, the station nearest the swarm, is bound to its HH,
    which started only on 2026-02-04, so it is not picked in the 20 earlier events (sections 1–2).
- **P recall of the best models is higher.** For `phasenet_instance`:
  - 0.48 of all analyst P picks (2015: 0.31);
  - 0.75 of those with data (0.43);
  - **0.85 at 3-component stations (0.56)**;
  - 0.86 on complete records (0.82).
- **On complete records the models rank as in 2015.** P recall is `phasenet_instance` 0.86, `phasenet_original`
  0.85, `phasenet_scedc` 0.75 and `eqtp_ncedc` 0.74 (2015: 0.82, 0.80, 0.67, 0.62). S recall on complete records
  is 0.91, 0.93, 0.66 and 0.89 (2015: 0.80, 0.84, 0.58, 0.76).
- **On events with no other catalog event within 120 s, the PhaseNet models score exactly as in 2015**: 0.89, 0.88
  and 0.74 in both years. `eqtp_ncedc` scores 0.66 (2015: 0.71). The models behave the same; what changed is
  the data.
- **The fixed ranking rule now names `phasenet_scedc`** (pooled P+S F1 0.640, then `phasenet_instance` 0.615,
  `phasenet_original` 0.542, `eqtp_ncedc` 0.542).
  - It wins only on S precision (0.17 against 0.13), which measures how few S picks it makes, not how good they are.
    It has the lowest P and S recall of the three PhaseNet models.
  - On P alone the order is `phasenet_instance` 0.783, `phasenet_original` 0.748, `phasenet_scedc` 0.745,
    `eqtp_ncedc` 0.715, as in 2015 (section 13).
- **The swarm problem is the same.**
  - Overlap event 75283011, 5.5 s before an Mw 3.77: the PhaseNet models find 0.11–0.39 of its P onsets, because
    their windows keep the larger event's P.
  - `eqtp_ncedc` finds 0.80 of the foreshock onsets but then loses the Mw 3.77: only 33 of that event's 272 analyst
    P picks are matched in the same file.
  - Either way, one of two events a few seconds apart is lost.
- **`eqtp_ncedc` is still the weakest picker and now costs 22–25 times as much CPU as the PhaseNet models**
  (5.0 against 0.20–0.23 CPU-s per station-hour). The cost per window is the same as in 2015 (110 ms); there are
  simply more windows per station-hour.
  - Its P value again stays near zero at many clear onsets: 202 of its 334 "below minConfidence" misses had a
    best value ≤ 0.1. The median SNR at the 334 missed onsets is 11 dB.
  - It is weakest on broadband HH channels: 0.55, against 0.87 for `phasenet_instance` and `phasenet_original`.
- **`eqtp_ncedc` P polarity is better than in 2015.**
  - Coverage / agreement with the analysts on normally oriented channels: 0.88 / 0.89 at
    `polarityMinConfidence` 0.5, and 0.72 / 0.93 at 0.7 (2015: 0.83 / 0.83 and 0.61 / 0.90).
  - For full-weight (weight-0) onsets: 0.93 / 0.94 at 0.5, and 0.84 / 0.95 at 0.7.
  - On channels with a negative gain (BK borehole EP1) agreement is 0.04 (26 pairs). The independent test shows
    again that the NCSS first motions on those channels follow the raw counts: 0.24 of 147 tests agree with
    similar rays on normal channels, against 0.82 for normal channels.
- **Accelerometers work for P and S.** At the 25 velocity-sensor stations whose accelerometer could be run:
  - P recall with the accelerometer is 0.81 against 0.82 with the velocity sensor (`phasenet_instance`);
  - S recall is 0.83 against 0.72.
  - 3 of the 28 accelerometers (BK.BRIB, BK.BRK, BK.LCOS) gave no picks because of a metadata problem (section 5).
- **False picks** (P picks per station-hour of pre-event noise): `phasenet_instance` 0.87, `eqtp_ncedc` 1.34,
  `phasenet_scedc` 2.91, `phasenet_original` 3.89 (2015: 1.08, 1.28, 1.84, 3.93). Many coincide at several
  stations and may be uncatalogued small events.
- **BK.CMSB.00.HN? (200 Hz data, 100 Hz in the metadata before 2026-03-13) is handled correctly.**
  - scautopick and the plugin use the rate written in each record and never the inventory rate. There is no
    "sampling rate changed" warning.
  - The accelerometer's P picks lie 0.03–0.14 s (median per model) from the analyst picks on the 500 Hz borehole
    sensor. A wrong rate would put them seconds off.
- **SeisBench cross-check** (`eqtp_ncedc`, 5 events, same weights): the plugin now finds 0.78 of the analyst P
  picks at 3-C stations, against 0.81 for SeisBench's continuous picking (2015: 0.42 against 0.84). The 2015 gap
  came from triggered records, which are gone. The plugin's normalisation is again not the cause of the eqtp
  misses (section 11).

## 2015 against 2025-26, side by side

Same code, same settings. The full table, with all four models, is `runs/sanramon2026/dlpicker/analysis/side_by_side_2015_vs_2026.md`
(and `.csv`), made by `scripts/14_side_by_side.py` from the result files of both runs.

| quantity | 2015 swarm (step 12) | 2025-26 sequence (step 14) |
|---|---|---|
| events (magnitude range) | 26 (M 0.8–3.6) | 26 (M 0.60–4.18) |
| stations with data / bound (main set) | 217 / 181 | 226 / 204 |
| main set by sensor | HN 145, HH 15, EH 9, EP 9, CN 2, DP 1 | HN 152, HH 34, EH 7, EP 7, DP 2, CN 2 |
| bound HN by network | NC 93, NP 48, BK 4 | NP 72, NC 57, CE 14, WR 6, BK 3 |
| stations without a usable 3-C sensor | 36 (35 vertical-only EH) | 22 (21 vertical-only EH) |
| hn set (accelerometers at velocity-sensor stations) | 13 | 28 (25 worked) |
| main-set records complete | 1789 / 3291 = 0.54 | **4625 / 4681 = 0.99** |
| station-hours (main set) | 177.1 | 310.0 |
| usable analyst P / S picks | 2422 / 163 | 3329 / 229 |
| P: no waveform / no 3-C sensor / triggered / complete | 694 / 411 / 471 / 846 | 1194 / 261 / **13** / 1861 |
| automatic ('R') P picks in the reference | 5 | 71 (removing them changes recall by ≤ 0.002) |
| **P recall, phasenet_instance** (all / with data / 3-C / complete) | 0.31 / 0.43 / 0.56 / 0.82 | 0.48 / 0.75 / **0.85** / 0.86 |
| P recall, phasenet_original | 0.30 / 0.42 / 0.55 / 0.80 | 0.48 / 0.75 / 0.85 / 0.85 |
| P recall, phasenet_scedc | 0.25 / 0.35 / 0.46 / 0.67 | 0.42 / 0.65 / 0.74 / 0.75 |
| P recall, eqtp_ncedc | 0.25 / 0.36 / 0.47 / 0.62 | 0.41 / 0.65 / 0.74 / 0.74 |
| P recall at complete records, events with no other event within 120 s (instance / original / scedc / eqtp) | 0.89 / 0.88 / 0.74 / 0.71 | 0.89 / 0.88 / 0.74 / 0.66 |
| S recall at complete records (instance / original / scedc / eqtp) | 0.80 / 0.84 / 0.58 / 0.76 (n 90) | 0.91 / 0.93 / 0.66 / 0.89 (n 213) |
| P precision (instance / original / scedc / eqtp) | 0.73 / 0.64 / 0.74 / 0.75 | 0.72 / 0.67 / 0.75 / 0.70 |
| P precision counting plausible picks | 0.91 / 0.82 / 0.84 / 0.83 | 0.92 / 0.84 / 0.85 / 0.77 |
| P median \|dt\| (s) | 0.030 / 0.028 / 0.032 / 0.022 | 0.040 / 0.033 / 0.047 / 0.030 |
| P mean dt, the model offset (s) | −0.020 / +0.042 / +0.034 / +0.014 | −0.025 / +0.046 / +0.054 / +0.018 |
| pooled P+S F1 (the ranking rule) | **instance 0.505**, scedc 0.488, eqtp 0.460, original 0.438 | **scedc 0.640**, instance 0.615, original 0.542, eqtp 0.542 |
| P-only F1 | instance 0.635, original 0.592, eqtp 0.576, scedc 0.568 | instance 0.783, original 0.748, scedc 0.745, eqtp 0.715 |
| overlap test event, P recall at complete records (instance / original / scedc / eqtp) | 72540760: 0.04 / 0.04 / 0.09 / 0.28 (n 46) | 75283011: 0.11 / 0.19 / 0.39 / 0.80 (n 137) |
| false P picks per station-hour (instance / original / scedc / eqtp) | 1.08 / 3.93 / 1.84 / 1.28 (25.0 h) | 0.87 / 3.89 / 2.91 / 1.34 (56.0 h) |
| CPU-s per station-hour (PhaseNet / eqtp) | 0.22–0.25 / 3.92 | 0.20–0.23 / 5.01 |
| ms per model window (PhaseNet / eqtp) | 3.7–4.0 / 113 | 2.9–3.1 / 110 |
| eqtp / PhaseNet CPU ratio | 16–18 | 22–25 |
| P recall at hn stations, velocity sensor / accelerometer (phasenet_instance) | 0.87 / 0.80 (13 stations) | 0.83 / 0.72 as run (28); **0.82 / 0.81** (25 that worked) |
| S recall at hn stations, velocity / accelerometer (phasenet_instance) | 0.83 / 0.59 | 0.73 / 0.77 as run; 0.72 / 0.83 (25) |
| eqtp polarity, normal channels: coverage / agreement at 0.5 | 0.83 / 0.83 (n 524) | 0.88 / 0.89 (n 1039) |
| same at 0.7 | 0.61 / 0.90 | 0.72 / 0.93 |
| eqtp polarity, inverted channels: agreement at 0.5 | 0.21 (n 51) | 0.04 (n 26) |
| analyst first motions on inverted channels agreeing with similar rays (control) | 0.32 of 148 (0.70) | 0.24 of 147 (0.82) |

## 1. What was run

- **Data.**
  - The 26 playback files `data/sanramon_2026/inputs/playback/<eventid>.mseed` contain all channels of every
    sensor within 80 km that has metadata, from origin −120 s to +120 s.
  - They were sorted with `scmssort -u -E` into `input/<id>_sorted.mseed`, as in step 12.
  - 226 stations have data; 169–201 stations are bound per event file (2015: 66–177).
- **Inventory.** `fdsnxml2inv` of `inputs/stations.xml` gives `config/inventory_sc.xml`.
  - `scinv check` reports 3 conflicts and 17 warnings (`config/scinv_check.txt`). The conflicts are overlapping
    sensor-location epochs at BK.BRIB.01, BK.BRK.00 and BK.LCOS.00, and they matter for the hn set (section 5).
  - The warnings are borehole depths over 500 m (NC.MDH1) and small negative depths (WR).
- **Bindings** (`scripts/14_bindings.py`, code identical to `12_bindings.py`). The rules are the same:
  - a sensor is usable if a Python copy of SeisComP's `getThreeComponents` finds three components, those
    channels have data, and an epoch covers every event file;
  - **main set**: one sensor per station, velocity sensors first (HH > EH > EP > DP > BH > HN > CN). 204 stations
    are bound: HN 152, HH 34, EH 7, EP 7, DP 2, CN 2;
  - not bound: 21 vertical-only EH stations, and BK.RB2B, which has two components in the data;
  - **hn set**: the accelerometer at the 28 stations whose main sensor is a velocity sensor (HH 21, EH 4, EP 2,
    DP 1). These run as the variants `<model>_hn`.
  - Of the 4681 station-event records of the main set, 4625 are complete. The 56 others start late (50), end
    early (48) or have gaps (7). 49 of them are at the 17 remaining NC NetQuakes sites (C0xx/J0xx); the rest are
    at NC.JBG, NP.1758, NP.1863, NP.LVA4, NP.TWIT2 and one record of NC.NTO HH (`config/coverage_bound.csv`).
  - **One binding for all files has a cost at NC.CSR**, the station nearest the swarm (3 km). The rule binds its HH
    (velocity sensors first), but that HH started only on 2026-02-04 and has data in 6 of the 26 files. In the 20
    earlier files CSR is therefore not picked in the main set; its HN (complete in all 26 files) is used only in the
    hn set. Step 12 had no such case.
- **Models and window settings: identical to step 12.** The four `scautopick_<model>.cfg` files differ from step
  12's only in their comment lines.
  - The windows that the plugin logged match the settings exactly (`analysis/log_checks.csv`):
    - P windows start 60.00/59.99 s (eqtp) or 15.00/14.99 s (PhaseNet) before the trigger;
    - S windows start 59.99, 54.99, 49.99 and 44.99 s (or 15, 10, 5 and 0 s) before the P pick.
  - Every setting of every variant is in `settings/scautopick_<variant>.settings.json`.

  | model | window | P window | dead time | S windows end after the P pick | ringBufferSize / leadTime |
  |---|---|---|---|---|---|
  | `eqtp_ncedc` | 120 s | ends 60 s after the trigger | 60 s | 60, 65, 70, 75 s | 300 / 180 s |
  | `phasenet_original`, `phasenet_scedc`, `phasenet_instance` | 30.01 s | ends 15 s after | 15 s | 15, 20, 25, 30 s | 300 / 60 s |

- **Detector, matching, windows and classes:** as in step 12.
  - Detector: STA/LTA 5–20 Hz, 1/30 s, on 1.8, off 1.0.
  - Matching: P within 0.5 s, S within 1.0 s, one-to-one, against the analyst picks of every catalog event in the
    file; reference weight codes 0–3.
  - Event window: −5 to +60 s. Plausible-arrival tolerance: 1 s.
- **Predicted arrivals** come from `ray1d.py` through the NCSS CON model, as in step 12. The analyst picks fit them
  with a median residual of −0.12 s for P and +0.26 s for S. 98 % of P and 92 % of S residuals lie within 1 s
  (2015: 97 % for both). The S picks carry the near-station S delay described in `docs/sanramon2026_inputs.md`.
- **Only case changes in the scripts:**
  - data paths;
  - top magnitude bin 3.0–4.2 (2015: 3.0–3.7), because the subset's top bin reaches the Mw 4.18 mainshock;
  - the polarity reference check takes each pick's own inventory epoch, because the period is one year and 242
    channels have two epochs (`14_polarity_reference_check.py` header);
  - `14_pick_one.sh` runs scautopick under `/usr/bin/timeout` (1800 s). No run came near it; the longest was the
    mainshock with `eqtp_ncedc` (152 CPU-s).

## 2. Which analyst picks a 3-component picker can use

Analyst picks (weight 0–3) of the 26 events, by what the station offers (`analysis/reference_picks.csv`):

| phase | no waveform (beyond 80 km) | data, but no usable 3-C sensor | 3-C sensor, triggered record | 3-C sensor, complete record | total |
|---|---|---|---|---|---|
| P | 1194 | 261 | 13 | 1861 | 3329 |
| S | 1 | 15 | 0 | 213 | 229 |
| *2015, P* | *694* | *411* | *471* | *846* | *2422* |
| *2015, S* | *0* | *1* | *72* | *90* | *163* |

- **No waveform:** 1193 of the 1195 picks are at stations beyond 80 km, which is by design (the 2025-26 picks
  reach farther than 2015's). The other 2 are P picks at NC.CNI during an outage.
- **No usable 3-C sensor:** 261 P and 15 S picks.
  - 235 P picks are at 19 vertical-only EH stations (21 such stations have data; 2015: 398 picks at 35).
  - 7 P picks are on the two-component borehole BK.RB2B.
  - 19 P and 15 S picks are at NC.CSR in the 20 files where its bound HH has no data (section 1). The hn variants,
    which bind CSR's HN, find 17 of its 25 P and 15 of its 21 S analyst picks, against 4 and 4 in the main set.
- **The analysts picked P mostly on EH (1384) and HH (960) channels, and S mostly on HN (148 of 229).** Of the 880
  EH P picks with data, 235 are at vertical-only stations and 10 on the EHZ of NC.CSR.
- **Automatic picks:** the step-12 rule (weight 0–3) also takes 71 automatic real-time P picks (data source 'R')
  of these reviewed events (2015: 5). Without them, P recall at complete records changes by at most 0.002
  (`analysis/extra_checks.json`).

## 3. Agreement with the analyst picks, per model

From `analysis/summary_by_model.csv` (main binding set; F1 uses recall over 3-C stations):

| model | phase | recall, all | recall, with data | recall, 3-C | recall, complete | precision | precision counting plausible | F1 | median \|dt\| (s) | MAD (s) | p95 \|dt\| (s) | mean dt (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **phasenet_instance** | P | 1600/3329 = 0.48 | 0.75 | 1600/1874 = 0.85 | 1597/1861 = **0.86** | 1775/2456 = 0.72 | 0.92 | 0.783 | 0.040 | 0.027 | 0.210 | −0.025 |
| | S | 194/229 = 0.85 | 0.85 | 194/213 = 0.91 | 194/213 = 0.91 | 221/1709 = 0.13 | 0.75 | 0.227 | 0.070 | 0.062 | 0.356 | −0.017 |
| phasenet_original | P | 1592/3329 = 0.48 | 0.75 | 1592/1874 = 0.85 | 1589/1861 = 0.85 | 1763/2641 = 0.67 | 0.84 | 0.748 | 0.033 | 0.028 | 0.230 | +0.046 |
| | S | 198/229 = 0.86 | 0.87 | 198/213 = 0.93 | 198/213 = 0.93 | 233/2398 = 0.10 | 0.64 | 0.176 | 0.077 | 0.052 | 0.391 | +0.084 |
| phasenet_scedc | P | 1389/3329 = 0.42 | 0.65 | 1389/1874 = 0.74 | 1388/1861 = 0.75 | 1462/1954 = 0.75 | 0.85 | 0.745 | 0.047 | 0.050 | 0.320 | +0.054 |
| | S | 141/229 = 0.62 | 0.62 | 141/213 = 0.66 | 141/213 = 0.66 | 155/891 = 0.17 | 0.70 | 0.276 | 0.090 | 0.081 | 0.420 | +0.106 |
| eqtp_ncedc | P | 1378/3329 = 0.41 | 0.65 | 1378/1874 = 0.74 | 1377/1861 = 0.74 | 1413/2030 = 0.70 | 0.77 | 0.715 | 0.030 | 0.030 | 0.171 | +0.018 |
| | S | 189/229 = 0.83 | 0.83 | 189/213 = 0.89 | 189/213 = 0.89 | 207/1794 = 0.12 | 0.54 | 0.204 | 0.060 | 0.060 | 0.382 | +0.043 |

- **The 3-C and complete recalls are now almost equal**, because almost no record is triggered. In 2015 they
  differed by 0.15–0.26.
- **Pooled P+S F1** (the ranking rule fixed in step 12, `analysis/best_model.json`): phasenet_scedc 0.640,
  phasenet_instance 0.615, phasenet_original 0.542, eqtp_ncedc 0.542.
  - The S F1 values (0.18–0.28) are set by the S precision. The S precision only says how many S picks a model
    makes where the analysts made none.
  - `phasenet_scedc` makes the fewest S picks (891 in the windows, against 1709–2398). That is why it wins,
    although its S recall is the lowest (0.66 against 0.89–0.93).
- **Timing.**
  - Median |dt| is 0.030–0.047 s for P and 0.06–0.09 s for S, slightly larger than in 2015 (0.022–0.032 s for
    P). It is larger within each weight code too; the cause was not investigated.
  - For weight-0 picks the P median |dt| is 0.020–0.030 s and the p95 is 0.085–0.10 s for three models; for
    phasenet_scedc the p95 is 0.26 s (`analysis/tables.md` T6b).
  - The offsets are model properties and repeat 2015's: `phasenet_instance` picks P 25 ms early,
    `phasenet_original` 46 ms late, `phasenet_scedc` 54 ms late, `eqtp_ncedc` 18 ms late (2015: −20, +42, +34,
    +14 ms).

## 4. Where picks are lost

All tables are in `analysis/tables.md`; the breakdowns are in `analysis/by_*.csv`.

**By the sensor the picker used** (P recall on complete records, main set):

| bound sensor | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc | *2015 (instance / eqtp)* |
|---|---|---|---|---|---|---|
| HH (broadband) | 422 | 0.87 | 0.87 | 0.78 | **0.55** | *0.85 / 0.49* |
| EH (short period, 3-C) | 107 | 0.89 | 0.89 | 0.90 | 0.86 | *0.89 / 0.76* |
| EP (borehole geophone) | 86 | 0.91 | 0.85 | 0.65 | 0.73 | *0.74 / 0.60* |
| DP / CN (borehole, 500 Hz) | 11 / 11 | 0.91 / 0.91 | 0.91 / 0.91 | 1.00 / 0.64 | 0.91 / 0.91 | *1.00 / 1.00; 0.88 / 0.81* |
| HN (accelerometer), complete records | 1224 | 0.85 | 0.84 | 0.72 | 0.79 | *0.78 / 0.62* |

- **`eqtp_ncedc` is weak on HH, as in 2015.** It finds 0.55 of the HH onsets, against 0.87 for
  `phasenet_instance` and `phasenet_original`.
- **The accelerometers, now 1224 of the 1861 complete-record P picks, do as well as the velocity sensors** for
  the PhaseNet models.
- **P precision by sensor** is 0.42–0.85. The lowest is DP (0.42–0.50, over 21–26 DL picks).

**By distance** (P recall on complete records / P precision):

| distance | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0–20 km | 349 | 0.89 / 0.85 | 0.90 / 0.79 | 0.81 / 0.82 | 0.81 / 0.77 |
| 20–40 km | 765 | 0.85 / 0.75 | 0.85 / 0.69 | 0.73 / 0.77 | 0.76 / 0.69 |
| 40–60 km | 509 | 0.84 / 0.66 | 0.82 / 0.61 | 0.70 / 0.73 | 0.72 / 0.69 |
| 60–80 km | 238 | 0.87 / 0.63 | 0.87 / 0.58 | 0.81 / 0.65 | 0.62 / 0.63 |

- As in 2015, the PhaseNet models keep their recall out to 80 km, while `eqtp_ncedc` loses it with distance.
- Precision falls with distance, mostly because of plausible arrivals that the analysts did not pick.

**By magnitude** (P recall on complete records):

| magnitude | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| M 0.5–1.0 (4 events) | 60 | 0.62 | 0.68 | 0.33 | 0.30 |
| M 1.0–1.5 (4) | 79 | 0.81 | 0.82 | 0.62 | 0.39 |
| M 1.5–2.0 (4) | 134 | 0.77 | 0.76 | 0.55 | 0.40 |
| M 2.0–2.5 (5) | 401 | 0.63 | 0.65 | 0.61 | 0.69 |
| M 2.5–3.0 (4) | 411 | 0.94 | 0.91 | 0.76 | 0.71 |
| M 3.0–4.18 (5) | 776 | 0.97 | 0.97 | 0.89 | 0.91 |

- **The dip at M 2.0–2.5 is the overlap event 75283011.** It holds 137 of the bin's 401 picks.
- **Small events separate the models.** Below M 2, `eqtp_ncedc` finds only 0.30–0.40 and `phasenet_scedc`
  0.33–0.62. The two Northern-California/Italian PhaseNet models find 0.62–0.82.
- **S recall on complete records** is 0.67–1.00 per bin for the three best models (8–95 picks per bin; T4b).

**By the time to the nearest other catalog event in the same file** (P recall on complete records;
`analysis/event_neighbours.csv`):

| nearest other event | events | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|---|
| none within 120 s | 16 | 858 | 0.89 | 0.88 | 0.74 | 0.66 |
| 60–120 s | 4 | 395 | 0.95 | 0.94 | 0.83 | 0.83 |
| 15–60 s | 3 | 243 | 0.94 | 0.93 | 0.83 | 0.81 |
| ≤ 15 s | 3 | 365 | 0.64 | 0.65 | 0.62 | 0.78 |

- **The "≤ 15 s" class mixes two situations.**
  - 75283011 (Md 2.29) is the smaller event of its pair, 5.5 s before an Mw 3.77.
  - 75304291 (Mw 3.40, 12.2 s before an M 3.11) and 75305761 (M 2.79, 10.7 s after an M 1.82) are the larger
    events of their pairs, and all models find 0.87–0.96 of their onsets (except `eqtp_ncedc` 0.58 and
    `phasenet_scedc` 0.57 for 75305761; `analysis/by_event.csv`).
- **Overlap event 75283011** (P recall at complete records, n = 137): phasenet_instance 0.11, phasenet_original
  0.19, phasenet_scedc 0.39, eqtp_ncedc 0.80.
  - In that file the PhaseNet models' matched P picks belong mostly to the following Mw 3.77 (75283016): 145, 128
    and 55 picks, against 15, 26 and 54 of 75283011 (`analysis/extra_checks.json`).
  - `eqtp_ncedc` does the opposite: 109 picks of 75283011 and only 33 of the 272 analyst P picks of the Mw 3.77.
    Its 120 s window covers both onsets and keeps the first; the 60 s dead time then blocks the second.
  - **So no model keeps both events.** Recall over the 26 test events does not show this, because 75283016 is not
    a test event. The same happened in 2015, where eqtp also kept more of the foreshock (0.28 against 0.04–0.09).
- **For eqtp, the 0.66 on events without neighbours is the better measure**; its high "≤ 15 s" value comes from
  trading the Mw 3.77 for its foreshock.

**By analyst pick quality** (P at 3-C stations; recall, then median / p95 |dt| in s):

| weight code | n | phasenet_instance | phasenet_original | phasenet_scedc | eqtp_ncedc |
|---|---|---|---|---|---|
| 0 (full weight) | 499 | 0.93; 0.030 / 0.098 | 0.94; 0.021 / 0.090 | 0.92; 0.030 / 0.260 | 0.92; 0.020 / 0.085 |
| 1 | 768 | 0.89; 0.032 / 0.170 | 0.90; 0.030 / 0.167 | 0.81; 0.048 / 0.280 | 0.80; 0.030 / 0.140 |
| 2 | 480 | 0.78; 0.050 / 0.290 | 0.76; 0.070 / 0.283 | 0.57; 0.110 / 0.380 | 0.57; 0.060 / 0.295 |
| 3 | 127 | 0.60; 0.084 / 0.333 | 0.51; 0.140 / 0.448 | 0.32; 0.150 / 0.411 | 0.28; 0.085 / 0.412 |

- Weight-0 onsets are found 92–94 % of the time by every model (2015: 74–79 %, when many sat on triggered records).

## 5. Velocity sensor against accelerometer at the same stations

The `_hn` variants bind the HN accelerometer at the 28 stations whose main sensor is HH (21), EH (4), EP (2) or
DP (1).

**Three of the 28 accelerometers gave no picks at all**: BK.BRIB.01.HN, BK.BRK.00.HN and BK.LCOS.00.HN.

- **Cause.** NCEDC's StationXML gives each of these stations two overlapping sensor-location epochs with the same
  location code, and it splits the HN channels between them. At BK.BRK, HNE and HNN sit under the epoch that
  starts in 2011 and HNZ under the one that starts in 2014. `scinv check` lists all three as conflicts.
- **What scautopick does with it.**
  - At BK.BRK it reports "Ambiguous vertical component across epochs" (`picker.cpp:623`) and detects on HNE.
  - At all three, when a trigger starts the DL picker, the sensor-location epoch it looks up does not hold all
    three HN channels. The picker then gets streams with an empty channel code (log lines "Added processor on
    stream BK.BRIB.01." etc.) and never picks.
- **Why the binding check passed them.** `14_bindings.py` (= `12_bindings.py`) pools all epochs of one location
  code before applying its copy of `getThreeComponents`, so it does not see the split.
- **Scope.** The main set is not affected: no main-set log has an empty-channel processor or a detection channel
  other than the expected vertical. In 2015 none of this happened.

Source: `analysis/accelerometer_vs_velocity.csv` (all 28 stations, as run) and `analysis/extra_checks.json`
(the 25 that worked).

| model | phase | velocity sensor, 28 stations | accelerometer, 28 (as run) | velocity, 25 that worked | accelerometer, 25 | *2015, velocity / accel. (13)* |
|---|---|---|---|---|---|---|
| phasenet_instance | P | 340/411 = 0.83 | 295/411 = 0.72 | 299/365 = 0.82 | 295/365 = **0.81** | *0.87 / 0.80* |
| | S | 68/93 = 0.73 | 72/93 = 0.77 | 63/87 = 0.72 | 72/87 = **0.83** | *0.83 / 0.59* |
| phasenet_original | P | 0.83 | 0.75 | 0.82 | 0.85 | *0.84 / 0.81* |
| | S | 0.77 | 0.83 | 0.77 | 0.89 | *0.83 / 0.78* |
| phasenet_scedc | P | 0.76 | 0.60 | 0.75 | 0.67 | *0.72 / 0.67* |
| | S | 0.54 | 0.47 | 0.52 | 0.51 | *0.51 / 0.44* |
| eqtp_ncedc | P | 0.63 | 0.67 | 0.65 | 0.76 | *0.65 / 0.68* |
| | S | 0.73 | 0.77 | 0.74 | 0.83 | *0.78 / 0.51* |

- **Where the accelerometer runs, it is as good as the velocity sensor for P** with the two best models
  (−0.01 to +0.03), and better with `eqtp_ncedc` (+0.11). Only `phasenet_scedc` loses on P (−0.08).
- **For S it is better** with three models (+0.09 to +0.12); `phasenet_scedc` is even (−0.01).
- In 2015 the accelerometer cost 3–7 points of P recall and up to 24 points of S recall. The hn set is now larger
  and different (BK 15 and NC 13 stations; 2015: BK 9, NC 4), so the two years' numbers are not a like-for-like
  comparison of sensors.
- At NC.CSR the hn binding is the only one that covers the 20 early events (section 2).
- P precision of the hn variants is 0.74–0.83 (`analysis/tables.md` T1). False P picks per station-hour at these
  stations: 0.36–5.3 (`analysis/outside_window.csv`; 8.2 station-hours only).

## 6. Why analyst picks at 3-C stations were missed

From the `--debug` logs (`analysis/missed_reference_diagnosis.csv`). Complete records:

| model | missed P | below minConfidence | no trigger | trigger not turned into a picker | window picked another time | vetoed as S | missed S | no P pick so no S picker | S window picked another time | S below minConfidence |
|---|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | 264 | 33 | 55 | 16 | 159 | 1 | 19 | 14 | 3 | 2 |
| phasenet_original | 272 | 38 | 55 | 16 | 162 | 1 | 15 | 10 | 5 | 0 |
| phasenet_scedc | 473 | 286 | 55 | 16 | 107 | 9 | 72 | 18 | 14 | 38 (+2 other) |
| eqtp_ncedc | 484 | 334 | 47 | 14 | 82 | 7 | 24 | 13 | 9 | 1 (+1 no window) |

- **"Window picked another time" is mostly the overlap event.** For the PhaseNet models, 117 of 159, 102 of 162
  and 50 of 107 of these misses are in 75283011. For `eqtp_ncedc` it is 23 of 82.
- **"Below minConfidence" again splits the models.**
  - It is rare for `phasenet_instance` (33) and `phasenet_original` (38).
  - `phasenet_scedc` (286) has values spread evenly over 0–0.4, mostly on HN (187); a lower threshold would
    recover many.
  - **`eqtp_ncedc` (334) had a best value ≤ 0.1 in 202 cases (21 at exactly 0).** 224 of the 334 are in events
    with no neighbour, and the median SNR at the 334 onsets is 11 dB, so these are clear arrivals. They are on HH
    (162) and HN (146). This repeats step 12's finding: the model does not see these onsets.
- **Triggered records** (13 P picks): 9–10 are "record starts too late", as in 2015. That problem has almost
  disappeared with the data.

## 7. DL picks without an analyst partner

Unmatched DL picks inside the event windows, classified by the step-12 rules (`analysis/unmatched_in_window.csv`):

| model | phase | plausible, analyst did not pick | plausible arrival of another catalog event | near-duplicate | phase confusion | timing disagreement | noise / other |
|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 454 | 12 | 70 | 5 | 26 | 104 |
| | S | 975 | 93 | 66 | 1 | 0 | 353 |
| phasenet_original | P | 423 | 19 | 81 | 21 | 35 | 287 |
| | S | 1163 | 128 | 113 | 10 | 0 | 751 |
| phasenet_scedc | P | 188 | 8 | 66 | 26 | 40 | 162 |
| | S | 427 | 45 | 33 | 50 | 0 | 181 |
| eqtp_ncedc | P | 147 | 1 | 344 | 1 | 17 | 103 |
| | S | 668 | 89 | 327 | 57 | 0 | 446 |

(12 or fewer "analyst pick is an outlier" cases per model are left out.)

- **Most unmatched P picks are plausible:** they lie within 1 s of the predicted P where the analyst made no
  pick.
  - Noise P picks are fewest for `phasenet_instance` (104 of 2456 P picks in the windows) and `eqtp_ncedc` (103
    of 2030).
  - `phasenet_original` has 287 of 2641.
- **`eqtp_ncedc` makes many near-duplicates** (344 P, 327 S; 2015: 109, 105). An earlier trigger's 120 s window
  already contains the onset, and a later trigger picks it again.
- **S:** most DL S picks have no analyst partner because the analysts picked few S. Half or more of them are
  plausible.

## 8. Picks outside the event windows

- **Counting span.** As in step 12, one span is used for all models: from the record start + `initTime` to the
  record end − 60 s, minus every NCSS catalog event window (998 events in the wide box). Here that is 56.0
  station-hours of pre-event noise (2015: 25.0).
- **Coincident** means P picks at 3 or more stations within ±10 s.
- Source: `analysis/outside_window.csv`.

| model | phase | DL picks outside the windows | in another catalog event's window | in the common noise span | false picks per station-hour | on HH | on HN | on EH | on EP |
|---|---|---|---|---|---|---|---|---|---|
| phasenet_instance | P | 479 | 245 | 49 (17 coincident) | **0.87** | 0.73 | 0.83 | 1.93 | 1.35 |
| | S | 243 | 201 | 11 | 0.20 | | | | |
| phasenet_original | P | 883 | 299 | 218 (183 coincident) | **3.89** | 2.28 | 4.12 | 3.86 | 7.22 |
| | S | 578 | 334 | 129 | 2.30 | | | | |
| phasenet_scedc | P | 546 | 164 | 163 (125 coincident) | **2.91** | 2.18 | 3.12 | 4.34 | 1.35 |
| | S | 181 | 89 | 52 | 0.93 | | | | |
| eqtp_ncedc | P | 210 | 38 | 75 (24 coincident) | **1.34** | 1.87 | 1.32 | 0.48 | 0.45 |
| | S | 68 | 32 | 27 | 0.48 | | | | |

- **Some of these are real.** Of the P picks in the noise span, the share that another model also picked at the
  same station within 0.5 s is (`analysis/extra_checks.json`; the same code gives step 12's numbers):
  - phasenet_instance 33 of 49 (2015: 19 of 27);
  - phasenet_original 53 of 218 (27 of 98);
  - phasenet_scedc 38 of 163 (13 of 46);
  - eqtp_ncedc 27 of 75 (9 of 32).
- **Most of `phasenet_original`'s noise picks are coincident** (183 of 218 at 3 or more stations). In this busy
  sequence many may be small uncatalogued events. Still, only a quarter are confirmed by another model.
- **Ranking:** `phasenet_instance` makes the fewest false P picks and `phasenet_original` 4–5 times as many, as
  in 2015 and in Gwangyang. `phasenet_scedc` rose from 1.84 to 2.91. Unlike 2015, broadband HH is not the noisiest
  sensor for the PhaseNet models.

## 9. Cost

These are CPU seconds of the whole scautopick process (`/usr/bin/time`), 26 runs per model, 6 runs at a time on
the shared 32-core Server A. Source: `analysis/cost.csv`.

| model | CPU s | station-hours | CPU s per station-hour | triggers | P / S model windows | ms per window | peak memory |
|---|---|---|---|---|---|---|---|
| phasenet_instance | 66.8 | 310.0 | 0.215 | 10505 | 8464 / 11637 | 3.1 | 336 MB |
| phasenet_original | 69.7 | 310.0 | 0.225 | 10505 | 8464 / 13871 | 2.9 | 340 MB |
| phasenet_scedc | 61.6 | 310.0 | 0.199 | 10505 | 8464 / 9870 | 3.1 | 318 MB |
| eqtp_ncedc | 1554.3 | 310.0 | **5.013** | 10505 | 5432 / 8607 | **110.4** | 481 MB |

- **Per model window the cost is the same as in 2015** (PhaseNet 3 ms, eqtp 110 ms).
- **Per station-hour, eqtp costs more than in 2015** (5.0 against 3.9 CPU-s). The detector fires more often on
  these continuous records (34 triggers per station-hour against 29), and eqtp evaluates 45 windows per
  station-hour against 34.
- So **`eqtp_ncedc` costs 22–25 times as much as the PhaseNet models** (2015: 16–18).
- **Start-up:** 0.14–0.16 CPU-s on a 10 s probe file.
- The whole pick stage (216 runs) took 6 min of wall time.

## 10. `eqtp_ncedc` first-motion polarity against the analysts

Same method as step 12: matched P picks whose analyst pick has a first motion U or D. The plugin's polarity
refers to ground motion: it swaps up and down for a vertical with dip +90° or a negative gain. Coverage at 0.7 is
the subset with `polarity_confidence` ≥ 0.7. Source: `analysis/polarity_pairs.csv`, `summary.json` → polarity.

**Main binding set:** 1700 analyst first motions, 1267 of them at 3-C stations, 1065 matched (2015: 1951, 1120,
575).

| group | n | coverage (0.5) | agreement (0.5) | agreement if the swap is undone (0.5) | coverage (0.7) | agreement (0.7) |
|---|---|---|---|---|---|---|
| all | 1065 | 0.88 | 0.87 | 0.89 | 0.72 | 0.91 |
| normally oriented vertical (dip −90, gain > 0) | 1039 | 0.88 | **0.89** | 0.89 | 0.72 | **0.93** |
| inverted vertical (gain < 0 or dip +90) | 26 | 0.88 | **0.04** | **0.96** | 0.62 | 0.06 |
| analyst weight 0 | 457 | 0.93 | 0.94 | 0.95 | 0.84 | 0.95 |
| analyst weight 1 | 607 | 0.84 | 0.81 | 0.84 | 0.63 | 0.87 |
| bound HH | 193 | 0.82 | 0.85 | 0.85 | 0.64 | 0.94 |
| bound EH | 76 | 1.00 | 0.95 | 0.95 | 0.89 | 0.94 |
| bound HN | 735 | 0.88 | 0.89 | 0.89 | 0.72 | 0.92 |
| bound EP | 46 | 0.87 | 0.40 | 0.93 | 0.65 | 0.43 |
| 0–20 km | 264 | 0.91 | 0.93 | 0.93 | 0.80 | 0.95 |
| 40–60 km | 263 | 0.87 | 0.79 | 0.88 | 0.70 | 0.84 |
| 60–80 km | 98 | 0.84 | 0.74 | 0.74 | 0.57 | 0.88 |

- **Onset types.** In 2025-26, the analysts gave a first motion almost only for impulsive onsets: 1061 of the
  1065 pairs are 'I'.
  - So the "emergent" row of step 12 (agreement near chance) cannot be repeated; the 4 emergent pairs agree.
  - Weight 1 plays that role here: agreement is 0.81 at 0.5 and 0.87 at 0.7.
- **The hn set** (accelerometers, all normal orientation) gives 237 pairs: coverage 0.86 / 0.73 and agreement
  0.91 / 0.94 at 0.5 / 0.7 (2015: 0.94 / 0.95).
- **Where polarity is reliable:** on normally oriented channels, 89 % (threshold 0.5) to 93 % (0.7). It is
  95 % for weight-0 onsets and within 20 km. It drops to 0.74–0.79 at 40–80 km at threshold 0.5.
- **0.7 is again the better threshold for focal mechanisms.** It gives up a fifth of the coverage for 4 points of
  agreement.
- **Stations that always disagree** (3 or more comparisons; `analysis/polarity_by_station_eqtp_ncedc.csv`):
  - BK.MHDL (7), BK.OHLN (4), BK.OXMT (4), BK.SBRN (8): all with a negative gain on EP1. MHDL and SBRN were in
    the 2015 list; OHLN and OXMT are new in it;
  - NC.JMGB (6) and NC.NGVB (3): normal orientation in the metadata. A reversed channel or reversed analyst
    readings at these two stations is possible; not investigated.
- **What the analysts' first motions on inverted channels mean** (`scripts/14_polarity_reference_check.py`, no DL
  model involved; all 2025-26 picks in the wide box; each pick with its own inventory epoch).
  - Inverted-channel first motions match the majority of similar rays on normal channels in only **0.24 of 147
    tests**. The control, normal channels, match in **0.82 of 595**. Using analyst ('J') picks only gives the same
    result: 0.24 of 129 and 0.83 of 574.
  - Per channel: BK.MHDL.EP1 0.12 (43 tests), BK.OXMT.EP1 0.07 (29), BK.OHLN.EP1 0.24 (33), BK.SBRN.EP1 0.37 (19).
  - The two dip +90 channels with 4 or more tests behave differently: BK.SM2B.DP1 0.67 (6) and BK.PETB.EP1 0.75
    (4).
  - **Conclusion, as in step 12:** the NCSS first motions on the negative-gain EP1 channels follow the raw counts,
    not the ground motion. The plugin's swap is consistent with the StationXML. For focal mechanisms, use the
    plugin's polarity as it is, and do not use the NCSS first motions of those channels without correcting them.

## 11. Cross-check with SeisBench (`eqtp_ncedc`, 5 events)

- **Events** (fixed in the driver before any result was seen): 75305736 (Mw 4.18 mainshock), 75283011 (Md 2.29,
  the overlap event), 75285161 (M 2.60), 75283271 (M 1.59) and 75282561 (M 1.17).
- **Method: exactly step 12's.**
  - SeisBench 0.11 `EQTP.from_pretrained('ncedc')` v1, read-only env dl-base, CPU, one thread.
  - The weights are a local copy of step 12's project cache, so SeisBench did not contact its repository.
  - SeisBench gets the same raw streams of the bound sensors, with P 0.4, S 0.3, polarity 0.5 and `strict=True`.
- **Same weights:** on 8 identical mainshock windows, ONNX and torch differ by at most 5 × 10⁻⁶
  (`seisbench/weights_check.json`). The plugin's per-component normalisation changes the outputs by up to 0.16.
  P peaks move by at most 1 sample, and the polarity is the same in 8 of 8 windows.

**The plugin's input normalisation is again not the problem** (`scripts/14_normalization_test.py` on exactly the
windows the plugin evaluated; the recomputed window maxima reproduce the logged values to 0.005):

| windows | n | P ≥ 0.4 near the analyst pick, plugin input | same, SeisBench input | median P near the pick (plugin / SeisBench input) |
|---|---|---|---|---|
| analyst P picks the plugin missed "below minConfidence" | 334 | 0 | 22 | 0.014 / 0.012 |
| analyst P picks the plugin matched | 1378 | 1374 | 1339 | 0.955 / 0.954 |

SeisBench's normalisation would recover 22 of the 334 misses and lose 39 of the 1378 hits (2015: +13 / −10).

**Plugin against SeisBench, same weights and data** (`seisbench/compare_seisbench_summary.json`):

| phase | method | picks | recall, 3-C | recall, complete | precision | median \|dt\| vs analyst | polarity coverage / agreement |
|---|---|---|---|---|---|---|---|
| P | plugin | 620 | 398/511 = 0.78 | 0.79 | 0.73 | 0.030 s | 0.91 / 0.81 |
| P | SeisBench | 627 | 416/511 = 0.81 | 0.82 | 0.88 | 0.039 s | 0.92 / 0.84 |
| S | plugin | 537 | 56/66 = 0.85 | 0.85 | 0.14 | 0.080 s | |
| S | SeisBench | 745 | 58/66 = 0.88 | 0.88 | 0.13 | 0.080 s | |
| *P, 2015* | *plugin / SeisBench* | *329 / 678* | *0.42 / 0.84* | *0.58 / 0.82* | *0.78 / 0.74* | | *0.82 / 0.76; 0.85 / 0.82* |

(Triggered records: 6 P picks in 2025-26, found by neither; in 2015 the plugin found 0.19 and SeisBench 0.88.)

- **The 2015 gap has almost closed.** In 2015 SeisBench's continuous picking found twice as many analyst P picks
  as the plugin (0.84 against 0.42), mostly on triggered records. Now only 6 of the 511 analyst P picks of these
  events lie on triggered records (neither method finds them), and the plugin reaches 0.78 against SeisBench's
  0.81.
  - This confirms step 12's conclusion: the gap came from the plugin's triggering and windowing on triggered
    records, not from the model.
- **Where both pick, the times agree.**
  - P: 459 pairs, median |dt| 0.015 s, 88 % within 0.05 s, mean +0.008 s.
  - S: 372 pairs, median 0.020 s.
  - Polarity: of 348 pairs with a polarity from both, 94 % agree.
- **The 25 analyst P picks only SeisBench found**, by the plugin's reason for missing them:
  - 12 "window picked another time";
  - 10 "below minConfidence";
  - 2 "no trigger";
  - 1 "vetoed as S".

  The plugin found 7 that SeisBench did not.
- **SeisBench's precision is higher** (0.88 against 0.73). The difference is mostly the plugin's near-duplicates:
  126 of its 594 P picks in these event windows are second picks of an onset that an earlier 120 s window had
  already picked (section 7; `analysis/dl_picks_all.csv`).
- **Continuous picking does not solve the overlap either.** In the 75283011 file, SeisBench has a P pick within
  0.5 s for 121 of the 139 analyst P picks of the foreshock at 3-C stations, but for only 66 of the 164 of the
  Mw 3.77 that follows 5.5 s later (`analysis/extra_checks.json`; a simple count, not one-to-one).
- **On the same 5 events the PhaseNet models in the plugin** reach 0.68 (`phasenet_instance`) and 0.70
  (`phasenet_original`) at 3-C stations, below EQTP. That is entirely the overlap event: without it they reach
  0.89, against the plugin's EQTP 0.77 (`analysis/reference_vs_dl.csv`).
- **Cost:** SeisBench's continuous EQTP needed 348 CPU-s for 59.5 station-hours (5.9 per station-hour, one torch
  thread), 1.2 times the plugin's 5.0 (2015: 1.5 times). Wall time 6 min; peak memory 10.9 GB.

## 12. BK.CMSB: 200 Hz data with 100 Hz in the metadata

- **The facts.**
  - The BK.CMSB.00.HN? records are 200 Hz in all 26 files.
  - `stations.xml`, and so the SeisComP inventory, says 100 Hz for the epochs up to 2026-03-13 15:55, and 200 Hz
    after that. 22 of the 26 events fall before the switch; 75327827, 75335142, 75335382 and 75339357 fall after
    it.
  - CMSB's main sensor is the 500 Hz borehole geophone 40.DP (175 m deep, consistent rates). The HN is bound only
    in the hn set.
- **How scautopick handles it: it uses the rate written in each record.**
  - The waveform processors set themselves up with `record->samplingFrequency()`
    (`libs/seiscomp/processing/waveformprocessor.cpp`, `setupStream`). The detector's timing uses the record rate
    (`scautopick/detector.cpp`). The plugin resamples from that rate to the model's 100 Hz (`dl.h`, `resampler.h`).
  - Nothing in this path reads the inventory's sampleRateNumerator/Denominator.
  - In all 216 logs there is no "sampling rate changed" warning. 210 DL pickers were created on CMSB's HN in the hn
    runs (`analysis/extra_checks.json`).
- **The pick times confirm it.** The analysts picked CMSB on the borehole DP channels (11 P, 6 S).
  - The hn variants' picks on the 200 Hz HNZ match 7–10 of the 11 P picks, with median dt +0.03 s
    (phasenet_instance) to +0.14 s (phasenet_scedc) and at most 0.31 s.
  - The main variants' picks on DP1 have a median of −0.035 to +0.02 s.
  - With a wrong rate, the time axis would stretch by a factor of 2, and picks would be off by seconds to tens of
    seconds.
  - The same model's HN picks lie close to its DP picks: median |difference| 0.135 s over the 86 pairs within 1 s.
    A small delay of the surface sensor is expected, because it sits 175 m above the borehole sensor.
- **For a real-time system** the mismatch is still worth fixing in the inventory. Programs that compute
  amplitudes or responses from the inventory rate could be affected; scautopick's picking is not.

## 13. For the real-time setup

- **Model.**
  - The rule fixed in step 12 (highest pooled P+S F1) names **`phasenet_scedc`** here. That result comes only
    from its lower number of S picks (section 3). It has the lowest P and S recall of the PhaseNet models, 2.9
    false P picks per station-hour, and the largest timing scatter (p95 0.32 s).
  - By every P measure, and by S recall, **`phasenet_instance` is the best picker again**: P recall 0.86 on
    complete records, the fewest false P picks (0.87 per station-hour), and P-only F1 0.783.
  - I did not change the rule after seeing the result. My reading is that the pooled rule should not be used
    while the S reference is this incomplete, and that the step-12 choice (`phasenet_instance`) stands. The
    decision is yours.
  - Configuration: `runs/sanramon2026/dlpicker/config/scautopick_phasenet_instance.cfg` (identical in its
    settings to step 12's), bindings `config/bindings_main.xml`, inventory `config/inventory_sc.xml`.
- **Polarity:** only `eqtp_ncedc` gives it. It is now better (0.93 agreement at 0.7 on normal channels), but it
  costs 22–25 times as much CPU and picks worse. Use `polarityMinConfidence` 0.7 for focal mechanisms.
- **Swarms:** one P per window plus the dead time still loses one of two events a few seconds apart. PhaseNet
  keeps the larger, eqtp the earlier. Shorter dead times or several windows per trigger were not tested.
- **Metadata to fix before real-time use:**
  - BK.BRIB.01, BK.BRK.00 and BK.LCOS.00 have overlapping sensor-location epochs that split the HN channels. Bind
    a fixed component, or merge the epochs in the inventory, if their accelerometers are to be used.
  - BK.CMSB.00.HN? has the wrong rate before 2026-03-13 (harmless for picking).
  - The binding check (`14_bindings.py`) should model sensor-location epochs. It does not today, which is why it
    missed the split.
- **Vertical-only stations** (19 with analyst picks here, 235 P picks) are still lost to a 3-component picker.
- **Sensor changes during a sequence:** a station whose preferred sensor appears mid-sequence (NC.CSR, HH from
  2026-02-04) needs its binding changed at that date. A single offline binding cannot do that.

## Caveats

- **The analyst picks are the reference, and they are incomplete.**
  - Precision is a lower bound; most extra P picks fit the predicted arrival.
  - S was picked at 229 station-events, so S precision is not meaningful, and it decides the pooled F1 ranking.
  - Analyst first motions on negative-gain channels follow the raw counts (section 10).
- **26 events, and small groups.**
  - The year comparison rests on 26 events per year, 4–5 per magnitude bin, and one overlap event per year.
  - Within the "≤ 15 s" class, one event dominates.
  - Per-event numbers are in `analysis/by_event.csv`.
- **The two years differ in more than the sequence.**
  - The networks changed: the dense NC C0xx/J0xx NetQuakes strong-motion sites near San Ramon are mostly gone
    (the 17 that remain give most of the 56 incomplete records), and NP and CE strong-motion sites were added.
    Within 80 km the main set grew from 181 to 204 stations, and HH stations from 15 to 34.
  - Most importantly, the strong-motion records in the archive are now continuous.
  - The sequence is 3.9 km SSE of the 2015 swarm, wider, and has a larger mainshock (Mw 4.18).
  - The 2025-26 analyst picks reach farther (1194 P picks beyond 80 km), and the NCSS now leaves some picks
    automatic (71 'R' P picks inside the reference; they do not change the result).
  - So "recall, all" and "recall, with data" are not comparable between the years as model measures. The
    complete-record numbers, especially for events without neighbours, are.
- **Only the models and the binding set were varied**, as in step 12. Thresholds, detector settings and dead
  times stay at the README/plugin values.
- **hn set:** 3 of 28 accelerometers did not run (section 5). Both versions of the comparison are given.
- **Predicted arrivals** come from a 1-D model without station corrections: 98 % of the analyst P picks and 92 %
  of the S picks lie within 1 s. The "plausible" classes are approximate.
- **CPU:** six scautopick runs at a time on a shared machine. CPU time per run is unaffected; wall time is not a
  benchmark.

## Problems met

1. **`14_extra_checks.py` failed twice before its first result.** The first failure was pandas date parsing of
   mixed ISO strings (the same problem as step 12's problem 3; fixed with `format="ISO8601"`). The second was a
   wrong `rename` of a grouped count. Both were fixed and the script was re-run in full; no number was taken from
   a failed run.
2. **The hn-set metadata problem** (section 5) was found in the logs after the pick stage, not by the binding
   check. The runs were not repeated with a changed binding, to keep the step-12 binding rule; the comparison is
   given with and without the three stations.
3. **NC.CSR** (section 1) was likewise found in the analysis: its 34 analyst picks in 20 events fell into the
   "no usable 3-C sensor" tier although the station has a working accelerometer. It was left as the step-12 rule
   binds it, and reported.

## Files

- **Driver:** `runs/sanramon2026/dlpicker/scripts/14_dlpicker.sh`, a copy of `12_dlpicker.sh` with paths and the
  timeout changed. Stages: prep, pick, compare, seisbench, tables; 'all' leaves out seisbench. It is a dry run
  without `--apply`.
- **Helpers (copies of step 12's):**
  - `14_bindings.py` and `14_settings_json.py`: code identical;
  - `14_pick_one.sh`: adds `/usr/bin/timeout`;
  - `14_compare.py`: data path, top magnitude bin;
  - `14_polarity_reference_check.py`: data path, per-pick epoch, analyst-only variant;
  - `14_tables_md.py`: optional SeisBench tables, station counts;
  - `14_seisbench_run.py`, `14_compare_seisbench.py`, `14_weights_check.py`, `14_normalization_test.py`: test
    event and data path only.
- **New helpers:**
  - `14_extra_checks.py`: BK.CMSB rate, automatic picks, hn-set failures, noise picks confirmed by another model,
    the overlap file;
  - `14_side_by_side.py`: the 2015 vs 2025-26 table.
- **Log:** `logs/14_sanramon2026_dlpicker_20261018.log`.
- **Configuration:** `runs/sanramon2026/dlpicker/config/`:
  - `inventory_sc.xml`, `scinv_check.txt`, `scautopick_<model>.cfg`;
  - `key_main/`, `key_hn/`, `bindings_main.xml`, `bindings_hn.xml`;
  - `stations_bound.csv`, `coverage_bound.csv`, `bound_channels.csv`.
- **Settings:** `settings/` (per-variant JSON and scautopick dumps).
- **Picks:** `output/<variant>/<eventid>/` (picks.xml, scautopick.log, time.txt).
- **Comparison:** `analysis/`:
  - the same files as step 12: `summary_by_model.csv`, `by_*.csv`, `reference_vs_dl.csv`, `dl_picks_all.csv`,
    `missed_reference_diagnosis.csv`, `unmatched_in_window.csv`, `outside_window.csv`, `cost.csv`,
    `polarity_pairs.csv`, `polarity_reference_check.{csv,json}`, `best_model.json`, `summary.json`, `tables.md`;
  - new: `extra_checks.json` (+ `extra_checks_console.txt`), `side_by_side_2015_vs_2026.{csv,md}`.
- **SeisBench:** `seisbench/`.

**How to reproduce.** prep takes about 1 min, pick about 6 min (6 at a time), compare about 11 min, seisbench
about 12 min and tables a few seconds:

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/sanramon2026/dlpicker
bash scripts/14_dlpicker.sh                        # dry run
bash scripts/14_dlpicker.sh --apply                # prep, pick, compare, tables
bash scripts/14_dlpicker.sh --apply --stage seisbench
# then (env pyrtdd):
python -I scripts/14_extra_checks.py --run-dir $PWD > analysis/extra_checks_console.txt
python -I scripts/14_side_by_side.py --run-2015 ../../sanramon/dlpicker --run-2026 $PWD \
    --out analysis/side_by_side_2015_vs_2026.csv > analysis/side_by_side_2015_vs_2026.md
```
