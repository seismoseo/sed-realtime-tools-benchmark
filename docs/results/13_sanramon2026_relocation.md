# Step 13: rtDD relocation of the San Ramon 2025-26 sequence (pyrtdd and scrtdd), 927 events (2026-10-18)

The 2015 San Ramon test (`docs/results/11_sanramon_relocation.md`) repeated on the 2025-26 sequence with the same
settings. Scripts and outputs are in `runs/sanramon2026/`. All scripts are dry runs by default; `--apply` acts.

| script | purpose |
|---|---|
| `pyrtdd/run_pyrtdd_sanramon2026.py` | pyrtdd runs P0, P1 (copy of the 2015 driver) |
| `scrtdd/scrtdd_sanramon2026.py` + `scrtdd/scrtdd_common_sanramon2026.py` | scrtdd runs S0, S1 (copies of the 2015 drivers) |
| `analysis/analyze_sanramon2026.py` | all comparisons (copy of the 2015 analysis, same metric code, additions listed in its header) |
| `analysis/check_clustering_maxevsta.py` | clustering-only check of the one changed setting (no relocation) |

Logs are `logs/13_sanramon2026_*`.

## Short answer

- **All four runs finished.** Every run relocated **893 of the 927 events**, all in one cluster. The same 34 events
  were dropped in every run, almost all small automatic or 'I' events with fewer than 8 picks (section 9).
  2015: 680 of 685.
- **scrtdd = pyrtdd again.**
  - **S1 vs P1:** a median of 1.0 m apart, at most 25 m. 97.8 % of the 483,819 measured lags are identical (2015:
    97.9 %). Unlike 2015, no event jumped between two solutions.
  - **S0 vs P0:** a median of 1.1 m apart (0.15 m relative). But 4 poorly constrained events differ by more than
    100 m, up to 5.9 km. The worst two left the travel-time grid during the iterations (sections 5, 9).
- **Shape against LDEO DD-RT (primary reference).** Medians over the 842 common events.
  - "Relative" = position after removing each catalog's centroid. "Local" = the vectors to each event's 10 nearest
    neighbours in LDEO (median spacing 210 m; 2015: 107 m).
  - The 2015 numbers are in brackets.

  | | relative H / V (m) | local H / V (m) | closer to LDEO than the NCSS start (3-D / local) |
  |---|---|---|---|
  | NCSS routine (start) | 307 / 730 (229 / 394) | 365 / 853 (292 / 506) | |
  | P0 = S0 (catalog only) | 167 / 274 (142 / 134) | 149 / 265 (137 / 147) | 78 % / 93 % (80 % / 93 %) |
  | **P1 = S1 (cross-correlation)** | **145 / 311** (97 / 106) | **142 / 217** (51 / 63) | 77 % / 94 % (89 % / 98 %) |
  | P1, median offset removed instead of the mean | 145 / 233 | (not affected) | |
  | *NCEDC DD vs LDEO DD-RT, for scale* | *74 / 158* (162 / 236) | *98 / 204* (190 / 241) | |

  - rtDD again brings the events about **2.4× closer** to the reference structure than the NCSS start (3-D;
    2015: 2.1× catalog only, 2.9× with cross-correlation).
  - **Cross-correlation helps much less than in 2015.**
    - In 2015 it cut the local errors by about 60 %. Here: horizontal by 5 %, vertical by 18 %.
    - The relative horizontal error falls by 13 %.
    - The mean-centred vertical error even rises (274 → 311 m). This comes from about 16 events with depth errors
      over 3 km, which shift P1's mean centroid by 176 m. With the median offset removed, the vertical error falls
      from 263 to 233 m.
  - **NCEDC DD agrees with LDEO DD-RT better than either rtDD solution.** But both are real-time DD-RT solutions tied
    to the same base catalog, so this agreement is not an independent check (caveats).
- **Why cross-correlation gains less.** The data cannot separate these causes:
  - the yardstick is a real-time solution, which fixes each new event against older base-catalog events (to 2021),
    and whose own neighbour spacing is twice that of 2015;
  - the sequence is wider: double-difference pairs are a median of 1.04 km apart (2015: 0.77 km);
  - fewer near-field stations;
  - lower correlation quality:
    - 54 % of the measured P pairs pass |CC| ≥ 0.7 (2015: 58 %), and 23 % of the accepted P values are negative;
    - accepted lags are longer: median 47 ms P, 80 ms S (2015: 33 / 50 ms);
    - the final correlation residual MAD is 21 ms (2015: 13 ms).
- **Absolute position: again do not use it.** The default solver's absolute equations move the whole cluster
  2.4–2.6 km deeper and 1.3–1.4 km west of LDEO DD-RT (2015: 2.3 km deeper, 0.7–0.8 km west).
- **Fault structure.**
  - LDEO DD-RT, P0 and S0 all fit a plane striking 189° and dipping 78.6–80.1° W. P1/S1 fit a near-vertical plane
    (15.6° / 87.7° E, which is 6° of strike and 12° of dip from LDEO).
  - Median distances from the plane: LDEO 260 m, P0 284 m, P1 367 m, NCSS 332 m.
  - Every catalog's RMS distance is 0.73–0.80 km, so a single plane describes this sequence poorly.
- **Review status.** The 83 automatic-only events (with LDEO DD-RT) end only somewhat farther from LDEO than the 756
  analyst events (horizontal 172 vs 137 m local; vertical is mixed):
  - P1 vs LDEO, median-centred relative H / V: automatic 162 / 188 m, analyst 143 / 237 m;
  - local: automatic 172 / 229 m, analyst 137 / 211 m.
  - But automatic and 'I' events make up 27 of the 34 dropped events and every grid escape.
- **Where the 2025-26 sequence lies relative to 2015.** Method: each P1 is shifted by its own mean offset against
  LDEO; section 10.
  - It lies **SSE of the 2015 swarm**: centroid 4.1 km away at azimuth 147°, 0.18 km shallower.
  - It lies about **2 km east of the 2015 fault plane**: 846 of 893 events are more than 1 km east of it, and only
    8 are within 500 m.
  - **It does not reactivate the 2015 strand.** Its main body (835 events) lies on a structure parallel to the
    2015 strand (strike within 2–5°), which contains a small 2015 SE-edge cluster (5 events, 1.3–1.9 km east of
    the 2015 plane). Those 5 events are the nearest 2015 event for 156 of the 161 events within 1 km of a 2015
    event.
  - The LDEO catalogs alone give the same picture.
- **Runtime and memory** (single-threaded, `nice -n 10`, `prlimit --as=60G`):

  | run | 2015 | 2025-26 |
  |---|---|---|
  | P0 | 55 s, 437 MB | 91 s, 626 MB |
  | S0 | 54 s, 356 MB | 114 s, 532 MB |
  | P1 | 27.9 min, 1,008 MB | 38.4 min, 1,536 MB |
  | S1 | 19.4 min, 756 MB | 29.0 min, 1,118 MB |

## 1. What was relocated, and with what

- **Events:** the 927 benchmark events of the 2025-26 San Ramon sequence (Calaveras fault, 2025-10-23 to 2026-09-28;
  largest Mw 4.18, nc75305736).
  - Start: the NCSS **routine** locations (`data/sanramon_2026/inputs/rtdd_catalog/event.csv`; depth below sea level).
  - Picks: 41,870 NCSS picks (37,929 P + 3,941 S) at 594 stations. **Not all are analyst picks** (2015: every
    event was analyst-reviewed):
    - 764 events are analyst-reviewed ('F');
    - 98 events ('A' 97, 'H' 1) were never reviewed; they carry only the NCSS real-time automatic P picks;
    - 65 'I' events are mostly small 'Mh' events, 62 of them without any DD solution;
    - in all, 2,489 picks are automatic.
  - Inputs are described in `docs/sanramon2026_inputs.md`; the waveform checks in `docs/sanramon2026_waveforms.md`.
- **Travel times:** NonLinLoc 2-D grids of the NCSS CON gradient model (Vp/Vs 1.73), TRANS_MERC projection centred
  on the 2025-26 swarm (`inputs/nll_con_tm/time`, model `sanramon2026_con`).
  - The grids cover the 300 stations within 120 km of the swarm centre (2015: 264).
  - All 600 station/phase grids are found with libhdd's default `maxSearchDistance` of 0.1 m. This was checked
    with pyrtdd for the mainshock: 600 of 600 lookups. station.csv and the grid station list agree to the digit.
- **Waveforms:** the SDS archive `inputs/sds` holds origin −10 s to +30 s for every picked sensor within 60 km
  (62,246 windows, 61,943 complete).
  - pyrtdd reads the component orientations from the StationXML `inputs/stations.xml`.
  - scrtdd reads them from `runs/sanramon2026/scrtdd/inputs/inventory_sc.xml`, the `fdsnxml2inv --formatted`
    conversion of the same file (same command as 2015; 0 errors, 447 unit/elevation warnings, log
    `fdsnxml2inv.log`). In multi-event mode scrtdd takes station positions from station.csv, not from this
    inventory.

### Runs

| run | program | what it is | cross-correlation | clustering | solver |
|---|---|---|---|---|---|
| **P0** | pyrtdd | catalog differential times only | off | rtDD default (ellipsoids); maxEvStaDist 120 km | rtDD default (absLocConstraint 0.3, damping 0.01) |
| **P1** | pyrtdd | P0 + cross-correlation (band-pass really applied, through the 2015 proxy workaround) | on | as P0 | default |
| **S0** | scrtdd | = P0 | off | as P0 | default |
| **S1** | scrtdd | = P1 | on | as P0 | default |

These are the only relocations made. The 2015 sensitivity runs were not repeated, because nothing failed. The only
extra computation is a clustering-only check of the one changed setting (section 2.1); it relocates nothing.

## 2. Settings: the 2015 values, with three changes

The drivers are copies of the 2015 drivers; the 2015 files are untouched.

| 2015 template | 2025-26 copy |
|---|---|
| `runs/sanramon/pyrtdd/run_pyrtdd_sanramon.py` | `runs/sanramon2026/pyrtdd/run_pyrtdd_sanramon2026.py` |
| `runs/sanramon/scrtdd/scrtdd_sanramon.py` + `scrtdd_common_sanramon.py` | `runs/sanramon2026/scrtdd/scrtdd_sanramon2026.py` + `scrtdd_common_sanramon2026.py` |
| `runs/sanramon/analysis/analyze_sanramon.py` | `runs/sanramon2026/analysis/analyze_sanramon2026.py` |

Every option of every run is dumped:
- pyrtdd reads its values back from the libhdd objects into `<run>/options.json`;
- scrtdd's values come from SeisComP's own configuration reader and go to `<run>/run_options.json`, with every key
  written explicitly. scrtdd's `--print-config-vars` lists no variable that the dump misses.

A key-by-key comparison of these dumps with the 2015 dumps (P0, P1, S0, S1 each against its 2015 twin) shows only
these differences:

| what | 2015 | 2025-26 | why |
|---|---|---|---|
| input and output paths | `data/sanramon_2015`, `runs/sanramon` | `data/sanramon_2026`, `runs/sanramon2026` | new case |
| NonLinLoc grid model | `sanramon_con` | `sanramon2026_con` | new grids (centred on the new swarm, model surface 0.32 km above sea level) |
| clustering `maxEvStaDist` (pyrtdd) = `doubleDifferenceSystem.phaseFiltering.maxStationDistance` (scrtdd) | −1 (no limit) | **120 km** | asked for in the task; there is no grid beyond 120 km (2,998 P picks are farther) |
| scrtdd profile `region` | 37.786, −121.963, 30 km | 37.757, −121.940, 30 km | used only in real time; ignored with `--profile` |
| scrtdd run timeout | 6 h | 12 h | safety margin only |

Everything else is the 2015 value:
- **Clustering:** rtDD default (numEllipsoids 5, maxNumNeigh 40, minNumNeigh 8, minNumPhases 8, maxNeighbourDist
  5 km, minEvStaToInterEvRatio 3).
- **Solver:** rtDD default (LSMR, 20 iterations, absLocConstraint 0.3, damping 0.01, residual down-weighting
  10 → 5, xcorrWeightScaler 2, usePickUncertainties false).
- **Cross-correlation:**
  - rtDD's default windows: P −0.5…+0.5 s with winScaling 0.02; S −0.5…+1.0 s with winScaling 0.04; maxDelay
    0.5 s; |CC| ≥ 0.7;
  - no station or inter-event distance limit;
  - **P components Z, 1**; **S on L2**;
  - **1.5–15 Hz** 4-pole causal Butterworth band-pass at **1000 Hz**. pyrtdd applies it through the 2015
    `PreprocessingSDSProxy` workaround for its filter bug; scrtdd uses `BW(4,1.5,15)` and `resampling 1000`;
  - no waveform disk cache.
- **Execution:** `nice -n 10`, `prlimit --as=60000000000`, one process per run. libhdd is single-threaded, and
  OMP/OpenBLAS are capped at 8 as in 2015.
- **Software:** as in 2015 — pyrtdd commit d122c3a with libhdd v2.0.9, and scrtdd 2.0.10 in SeisComP 7.4.0.

**"Z, 1" still matters.** 1,553 P picks are on 1/2/3-named borehole sensors (EP1 1,100, DP1 315, CN1 67, HN1 67;
2015: 2,854).

### 2.1 What the 120 km limit changes

`analysis/check_clustering_maxevsta.py` runs only rtDD's clustering step, once with −1 and once with 120 km, on the
same catalog. Results are in `clustering_maxevsta_check.json`.

| | maxEvStaDist −1 (2015 value) | 120 km (these runs) |
|---|---:|---:|
| events clustered / clusters | 893 / 1 | 893 / 1 (the same events) |
| phase pairs (P / S) | 564,447 (528,278 / 36,169) | 557,268 (521,099 / 36,169) |
| event pairs | 27,040 | 27,044 |

- The 120 km clustering is identical, pair for pair, to the pair file of run P0.
- 7,455 P phase pairs exist only without the limit:
  - 7,063 of them are at stations that have no grid, which rtDD would have dropped anyway at the travel-time lookup;
  - 392 are at stations beyond 120 km that do have a grid.
- 276 pairs exist only with the limit (a slightly different ellipsoid selection).
- **So the change affects about 0.1 % of the usable data and no event.**

## 3. Results against the reference catalogs: shape, centroid, improvement (metrics a, b, f)

**How the numbers are made** (`analysis/analyze_sanramon2026.py`; the metric code is the 2015 code):

- **Event set.** All solutions are compared on the same events: those relocated by all four runs that are also in
  the reference. That is 842 for LDEO DD-RT and 843 for NCEDC DD.
  - Most of the other 51 relocated events are 'I' events without DD solutions.
  - 20 NCEDC DD events in the wide box have no NCSS datum and are left out of the NCEDC reference, as in 2015.
- **Coordinates.** Metres east, north and up of 37.757 N, −121.940 E (transverse Mercator). Depths are all below
  sea level:
  - rtDD inherits sea level from the NonLinLoc grids and `event.csv`;
  - LDEO DD-RT is geoid-referenced;
  - NCEDC DD depths are below the local model surface. They were converted with each event's NCSS datum (depth −
    datum), as in 2015.
- **Metrics** (as in 2015):
  - **relative geometry** = each event's position minus its catalog's centroid, against the same in the reference;
  - **local** = for each event, the median over its 10 nearest reference neighbours of the difference between our
    and the reference's event-to-neighbour vectors;
  - **centroid shift** = mean of the solution minus mean of the reference (U positive = shallower);
  - **improvement** = the NCSS start's median error divided by the solution's;
  - **events closer** = the share of events whose own error is smaller than the NCSS start's.
- The relative columns give the median / 90th percentile over events.

### 3.1 Against LDEO DD-RT `NCAeqDDRT.v202201` (primary; 842 events)

| solution | relative H median / p90 (m) | relative V median / p90 (m) | local H / V (m) | centroid shift E / N / U (m) | improvement 3-D | improvement local H / V | events closer than NCSS (3-D / local) |
|---|---|---|---|---|---|---|---|
| NCSS start | 307 / 732 | 730 / 1914 | 365 / 853 | −349 / −210 / +48 | 1 | 1 / 1 | |
| **P0** | 167 / 411 | 274 / 962 | 149 / 265 | −1277 / −366 / −2600 | 2.4 | 2.4 / 3.2 | 78 % / 93 % |
| **S0** | 168 / 408 | 277 / 966 | 149 / 266 | −1275 / −370 / −2604 | 2.4 | 2.4 / 3.2 | 78 % / 93 % |
| **P1** | **145** / 403 | 311 / 1065 | **142** / **217** | −1366 / −495 / −2396 | 2.4 | 2.6 / 3.9 | 77 % / 94 % |
| **S1** | 145 / 403 | 311 / 1064 | 141 / 217 | −1366 / −495 / −2397 | 2.3 | 2.6 / 3.9 | 77 % / 94 % |
| *NCEDC DD (for scale)* | *74 / 211* | *158 / 592* | *98 / 204* | *+276 / +130 / +522* | *4.4* | *3.7 / 4.2* | |

**Median offset removed instead of the centroid** (relative H / V, m): NCSS 288 / 724, P0 163 / 263,
**P1 145 / 233**, S0 162 / 264, S1 144 / 234, NCEDC DD 73 / 150.
- In 2015 this robust variant changed the rtDD numbers by at most 10 m. Here it changes P1's vertical number by
  78 m.
- About 16 events have depth errors over 3 km in P1 (13 in P0). They pull P1's mean depth 176 m away from its
  median depth (P0: 99 m). Through the mean centroid, this shifts every other event.

### 3.2 Against NCEDC DD = DD-RT (secondary; 843 events)

| solution | relative H median / p90 (m) | relative V median / p90 (m) | local H / V (m) | centroid shift E / N / U (m) | improvement 3-D | improvement local H / V | events closer than NCSS |
|---|---|---|---|---|---|---|---|
| NCSS start | 323 / 754 | 746 / 1995 | 390 / 942 | −624 / −340 / −472 | 1 | 1 / 1 | |
| P0 = S0 | 180 / 426 | 274 / 1007 | 165 / 265 | −1554 / −496 / −3123 | 2.5 | 2.4 / 3.6 | 81 % / 92 % |
| P1 = S1 | 164 / 459 | 303 / 1076 | 148 / 223 | −1642 / −625 / −2918 | 2.4 | 2.6 / 4.2 | 79 % / 95 % |
| *LDEO DD-RT (for scale)* | *74 / 211* | *158 / 592* | *99 / 185* | *−276 / −130 / −522* | *4.7* | *3.9 / 5.1* | |

Median-centred: P0 179 / 264, P1 163 / 234, LDEO 73 / 150. NCEDC's neighbour spacing is 222 m.

### 3.3 What this means

- **rtDD improves the routine catalog about as much as in 2015, catalog-only or not.**
  - The NCSS start is worse than in 2015, especially vertically: 730 m against LDEO DD-RT (2015: 394 m against LDEO).
  - P0 and P1 both bring the 3-D relative error down by about 2.4×.
  - 93–94 % of the events end locally closer to the reference than they started.
- **Cross-correlation adds little here.** P1 against P0 (LDEO, robust numbers):
  - relative H 163 → 145 m and V 263 → 233 m;
  - local H 149 → 142 m and V 265 → 217 m;
  - only 52 % of events end closer to LDEO in P1 than in P0 (67 % locally).
  - In 2015 the same step halved the local errors (137 / 147 → 51 / 63 m).
- **Possible reasons.** All are real; the data cannot rank them.
  - **The yardstick.** LDEO DD-RT fixes each 2025-26 event against older base-catalog events, one at a time. It never
    relates the 2025-26 events to each other directly. Its own neighbour spacing is 210 m (2015: 107 m). If its
    inter-event geometry is only good to 100–200 m, rtDD's 140–230 m cannot be judged more finely.
  - **The sequence.**
    - It is larger: its 5–95 % extent in LDEO is 2.4 km E–W by 3.5 km N–S, against 0.9 by 2.2 km in 2015
      (inputs report). Small separate groups lie up to 9 km farther south (section 10).
    - Its double-difference pairs are a median of 1.04 km apart, against 0.77 km. Correlated pairs are 0.90 km
      apart, against 0.67 km.
  - **The data** (section 6).
    - Fewer near stations: only 91 stations within 60 km are common to both years, and the dense C0xx/J0xx sites
      are gone.
    - Lower correlation acceptance and longer lags.
    - Larger final correlation residuals.
- **The two references agree with each other better than either agrees with rtDD.** In 2015 they disagreed by
  more than rtDD differed from LDEO. This does not make DD-RT "true": both are real-time DD-RT solutions against
  the same base catalog and NCSS picks.
- **Against NCEDC DD the ranking is the same as against LDEO DD-RT.** This differs from 2015, when NCEDC DD was
  too scattered to separate the runs.

## 4. Fault structure (metric c)

Plane fit by SVD of each catalog's centred event coordinates (`plane_fit.csv`; normal = direction of least spread,
strike by the right-hand rule).

| catalog | event set | strike | dip (toward) | median distance from plane (m) | RMS (m) | p90 (m) | RMS spread along strike / down dip (m) |
|---|---|---|---|---:|---:|---:|---|
| LDEO DD-RT | 842 common | 189.1° | 80.1° (W, 279°) | 260 | 725 | 810 | 1321 / 1234 |
| LDEO DD-RT | 864 in box | 189.5° | 80.9° (W) | 275 | 788 | 820 | 1313 / 1330 |
| NCEDC DD | 842 common | 187.6° | 81.8° (W) | 266 | 728 | 813 | 1312 / 1222 |
| NCSS start | 842 common | 196.4° | 81.1° (W) | 332 | 784 | 990 | 1462 / 1756 |
| P0 | 842 common | 188.8° | 78.6° (W) | 284 | 800 | 892 | 1627 / 1057 |
| S0 | 842 common | 189.5° | 79.4° (W) | 292 | 797 | 879 | 1616 / 1057 |
| P1 | 842 common | 15.6° | 87.7° (E, 106°) | 367 | 793 | 805 | 1447 / 1083 |
| S1 | 842 common | 15.6° | 87.7° (E) | 367 | 793 | 805 | 1447 / 1083 |

- **All catalogs see a steep plane striking about N10°E / S10°W.**
  - LDEO, NCEDC, P0 and S0 agree to within 2° of strike and 3.2° of dip (78.6–81.8° W).
  - P1/S1 turn it to near-vertical (87.7° toward ESE, which equals 92° toward W). That is 12° steeper than LDEO,
    with the strike 6.5° different.
- **But no catalog is well described by one plane.**
  - The RMS distance is 0.73–0.80 km everywhere; 2015 had 0.36–0.46 km.
  - The median distance is 260–370 m. Section 10 shows that the sequence has a main body and several small separate
    groups.
- **P1 is the least planar by the median** (367 m against 284 m for P0 and 260 m for LDEO), but has the smallest
  90th percentile (805 m against 892 m for P0 and 810 m for LDEO). With cross-correlation, fewer events lie far
  from the best plane, but fewer lie close to it.
- These whole-sequence planes are pulled by the small separate groups in the south-west (section 10). The main body
  alone fits a near-vertical plane striking 179° (P1) or 173° (LDEO), parallel to the 2015 strand. The present data
  cannot say whether P1's or LDEO's sheet is right.
- The 2015 conclusion "rtDD reproduces LDEO's strike to within 2°" holds for P0/S0 here. For P1/S1 the agreement is
  within 6.5° in strike and 12° in dip.

## 5. scrtdd against pyrtdd (metric d)

| pair | event positions: median / 90 % / max 3-D difference (m) | relative (median offset removed): median / 90 % / max (m) | events > 10 m / > 100 m | origin time, max (ms) |
|---|---|---|---|---|
| P0 vs S0 | 1.09 / 1.86 / 5945 | 0.15 / 1.00 / 5946 | 14 / 4 | 618 |
| **P1 vs S1** | **1.04 / 2.30 / 25** | **0.45 / 1.82 / 25** | 5 / 0 | 2.2 |
| *2015 P0 vs S0* | *0.25 / 0.26 / 7.3* | *0.01 / 0.03 / 7.1* | *0 / 0* | *0.3* |
| *2015 P1 vs S1* | *1.1 / 2.5 / 6263* | *0.45 / 2.1 / 6264* | *6 / 2* | *333* |

- **S0 against P0.**
  - Both programs built the same 557,268 phase pairs and the same initial system. The initial residual statistics
    are identical (MAD 71.1 ms).
  - 879 of 893 events agree within 10 m.
  - The 4 events more than 100 m apart are poorly constrained:
    - three automatic-only events ('A', 9–27 P picks, no S) that start at 1.0–3.5 km depth;
    - one analyst event (75279256, 11 P + 1 S) that starts above sea level.
  - The largest is **75276711** ('A'): P0 puts it at 7.6 km depth, S0 at 12.1 km, 5.9 km apart.
    - In both runs this event left the travel-time grid in 6 of the 20 iterations: rtDD moved it 5–32 km above the
      grid top (−3 km). The two builds took different paths there.
  - The second largest, 75303031 (479 m), also left the grid in both runs.
  - As in 2015, the two builds differ by tiny floating-point amounts, which grow over 20 iterations. Here these
    escapes amplify them into kilometres.
- **S1 against P1** (`xcorr_triplets_P1_vs_S1.csv`).
  - Both made the same 557,268 attempts and measured the same 483,819 lags.
  - 473,104 lags are identical (97.8 %); 10,477 differ by one sample (1 ms); 238 by more than 1 ms; 191 by more than
    10 ms (58 P, 133 S).
  - Coefficients: median difference 0; 99th percentile 0.0012.
  - 65 measurements fall on opposite sides of the 0.7 threshold (19 P, 46 S).
  - Positions: median 1.0 m, maximum 25 m (75276711 again). No event jumped.
  - Against the references, the medians of P1 and S1 differ by at most 2 m.
- **So scrtdd and pyrtdd (with the proxy workaround) give the same answer.** They differ only for events that rtDD
  cannot hold inside the grid.

## 6. Cross-correlation and residuals (metric e)

**Waveforms used** (pyrtdd proxy counters; the scrtdd log agrees to within 3):
- 34,737 traces loaded and processed; 16,922 requests found no data (8,265 for a Z channel, 8,625 for a '1'
  channel, 32 for horizontals). Most of these are P phases at stations beyond the 60 km waveform radius
  (60–120 km have grids but no waveforms).
- Loaded by channel type: EH 15,895, HN 10,063, HH 6,736, EP 1,645, DP 272, CN 65, BH 61.
- No disk cache.

**Cross-correlation measurements** (`xcorr_stats.csv`; libhdd's logged counts agree):

| phase | phase pairs | measured | \|CC\| ≥ 0.7 | of which CC ≥ +0.7 | of which CC ≤ −0.7 | median \|CC\| (measured) | median / 95th percentile \|lag\| of accepted (ms) |
|---|---:|---:|---:|---:|---:|---:|---|
| P | 521,099 | 451,713 | **243,624 (54 %)** | 187,880 | **55,744** | 0.72 | 47 / 348 |
| S (L2) | 36,169 | 32,106 | **18,959 (59 %)** | 18,959 | 0 | 0.73 | 80 / 394 |
| *2015 P* | *320,207* | *296,378* | *173,002 (58 %)* | *136,561* | *36,441* | *0.73* | *33 / 287* |
| *2015 S* | *38,267* | *35,030* | *19,907 (57 %)* | *19,907* | *0* | *0.72* | *50 / 240* |

- "Not measured" means no waveform: 69,386 P and 4,063 S pairs, from stations beyond 60 km and from S on
  vertical-only sensors.
- S makes up only 6.5 % of the phase pairs (2015: 10.7 %).

**Lag sizes by sign of the correlation** (P; P1 cache):

| P measurements | n | median \|lag\| | \|lag\| ≤ 20 ms | \|lag\| ≥ 200 ms |
|---|---:|---:|---:|---:|
| CC ≥ +0.7 | 187,880 | 37 ms (2015: 28) | 33 % (41 %) | 13 % (8 %) |
| CC ≤ −0.7 | 55,744 | 115 ms (2015: 76) | 14 % (21 %) | 29 % (19 %) |

- As in 2015, the negative-CC values are mostly polarity-reversed or wrong-peak matches; rtDD accepts |CC| ≥ minCoef.
- In the final system, 96 % of the positive-CC data keep a weight (median |residual| 15 ms). 90 % of the
  negative-CC data keep one (median |residual| 74 ms).

**Double-difference residuals before and after** (libhdd `cluster-1-initial/final-double-difference.csv`;
"weighted RMS" over the data with final weight > 0):

| run | data | initial: n | initial: MAD (ms) | initial: weighted RMS (ms) | final: n with weight > 0 | final: MAD (ms) | final: weighted RMS (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| P0 = S0 | catalog | 557,268 | 71.1 | 149.0 | 505,541 | 39.3 | 55.0 |
| P1 = S1 | all | 557,268 | 77.2 | 158.6 | 498,491 | 39.9 | 55.2 |
| P1 = S1 | cross-correlation | 262,582 | 69.9 | 147.3 | 247,756 | **21.2** | **47.7** |
| P1 = S1 | catalog | 294,686 | 84.5 | 176.2 | 250,735 | 64.0 | 67.5 |
| *2015 P0* | *catalog* | *357,531* | *51.3* | *101.0* | *329,863* | *27.0* | *38.0* |
| *2015 P1* | *cross-correlation* | *192,908* | *52.7* | *106.5* | *178,590* | *13.2* | *27.0* |

- Every residual is 1.3–1.6× its 2015 value. This reflects the picks (automatic ones included), the larger
  distances between paired events, and the fit of the correlation data.
- **Absolute travel-time RMS per event** (rtDD `startRms`/`finalRms`, median): 367 ms at the NCSS locations,
  311 ms after P0, 316 ms after P1 (2015: 235 → 243 / 247 ms).
  - The large start value shows the CON-grid misfit without station corrections, as in 2015, plus the
    near-station S delay (section 12).

## 7. Absolute position (metric f)

Centroid of each solution minus the reference centroid (E / N / U in m; U positive = shallower; common events):

| | vs LDEO DD-RT | vs NCEDC DD (datum-converted) | 2015, vs LDEO |
|---|---|---|---|
| NCSS start | −349 / −210 / +48 | −624 / −340 / −472 | −28 / −55 / −444 |
| P0 = S0 | −1277 / −366 / **−2600** | −1554 / −496 / −3123 | −675 / −95 / −2346 |
| P1 = S1 | −1366 / −495 / **−2396** | −1642 / −625 / −2918 | −826 / −204 / −2254 |
| NCEDC DD vs LDEO DD-RT | +276 / +130 / +522 | | +153 / +80 / +625 |

- **The same bias as in 2015, slightly larger.** rtDD's default absolute-residual equations (absLocConstraint 0.3)
  fit the CON grids, which have no station corrections. The cluster moves 2.4–2.6 km deeper and 1.3–1.4 km west.
  - The mean depth goes from about 7.1 km (LDEO, and the NCSS start) to about 9.5–9.7 km.
  - The median move from the NCSS start is 1.0–1.1 km west, 0.2–0.3 km south and 2.2–2.5 km down.
- The near-station S delay (tS/tP ≈ 2.15 within 5 km, +0.3 s median S−P residual) does not cancel in these
  absolute equations and probably adds to the bias. This was not separated (no sensitivity runs).
- **The NCSS start's centroid sits at LDEO's depth (+48 m).** The NCSS geoid depths and LDEO depths agree on
  average, as stated in the inputs report.
- **Do not use rtDD's absolute positions from these runs.** Use the relative geometry.

## 8. Results by review status (metric g)

Per-event errors of section 3 grouped by the NCSS review flag of each event (`review_split.csv`). Centroids and
reference neighbours come from all common events, so the groups can be compared with the full-set numbers. The
"median-centred" columns use the solution's median offset over all events (robust; see 3.1).

| solution vs LDEO DD-RT | group | n | relative H / V (m) | median-centred H / V (m) | local H / V (m) | improvement 3-D | closer than NCSS (3-D / local) |
|---|---|---:|---|---|---|---:|---|
| NCSS start | analyst 'F' | 756 | 312 / 734 | 291 / 735 | 360 / 842 | 1 | |
| NCSS start | automatic 'A'/'H' | 83 | 286 / 596 | 279 / 577 | 395 / 894 | 1 | |
| P0 | analyst 'F' | 756 | 167 / 265 | 164 / 263 | 150 / 258 | 2.5 | 80 % / 94 % |
| P0 | automatic 'A'/'H' | 83 | 158 / 341 | 158 / 269 | 138 / 302 | 1.9 | 67 % / 82 % |
| **P1** | analyst 'F' | 756 | 143 / 319 | 143 / 237 | 137 / 211 | 2.3 | 77 % / 95 % |
| **P1** | automatic 'A'/'H' | 83 | 156 / 243 | 162 / 188 | 172 / 229 | 2.3 | 75 % / 86 % |
| *NCEDC DD* | *analyst 'F'* | *756* | *73 / 158* | *72 / 151* | *96 / 197* | *4.5* | |
| *NCEDC DD* | *automatic 'A'/'H'* | *83* | *82 / 164* | *86 / 158* | *109 / 248* | *3.5* | |

(S0/S1 are within a few metres of P0/P1. The 3 'I' events with a DD-RT solution are in `review_split.csv`; 3 events
are too few to report. Against NCEDC DD the picture is the same.)

- **Automatic-only events end up about as close to the reference as analyst events.** The differences go both
  ways:
  - local H: automatic 35 m worse in P1, 12 m better in P0;
  - vertical: in P1 the median-centred error is smaller for automatic events (188 vs 237 m) but the local one
    larger (229 vs 211 m); in P0 automatic events are worse (local 302 vs 258 m).
  - The reference itself is weaker for automatic events:
    - LDEO DD-RT depths of automatic events stay closer to the automatic NCSS depths (16 % within 0.1 km, against
      8 % for 'F');
    - 11 of the 97 'A' events sit shallower than 3 km in LDEO DD-RT (9 of 763 'F').
- **They make the trouble.**
  - Automatic and 'I' events are 27 of the 34 dropped events (section 9).
  - Every grid escape is an automatic event. Every event that ends above sea level is automatic or 'I'.
    Every event that ends deeper than 13 km is too, except 75425082 ('F'), which LDEO DD-RT also puts at 13.2 km.
  - In P0, only 67 % of automatic events end closer to LDEO than their start (analyst: 80 %).
- **Relocated by review flag** (all four runs the same):
  - 'F' 757 of 764;
  - 'A' 82 of 97;
  - 'H' 1 of 1;
  - 'I' 53 of 65.

## 9. Events relocated, dropped and escaped (metric h)

- **Relocated:** 893 of 927 in every run, in one cluster.
- **Dropped:** the same 34 events in every run (`dropped_events.csv`). The reasons are reconstructed with the
  clustering's own phase filters: station ≤ 120 km, and station distance / inter-event distance ≥ 3.

  | reason | 'A' | 'F' | 'I' | total |
  |---|---:|---:|---:|---:|
  | fewer than 8 picks: cannot share minNumPhases = 8 phases with any neighbour | 14 | 3 | 11 | 28 |
  | 8 picks, but only 7 at stations within 120 km (75305946; also dropped with maxEvStaDist −1, section 2.1) | 1 | 0 | 0 | 1 |
  | fewer than minNumNeigh = 8 neighbours sharing ≥ 8 phases (75274076, 75274081, 75305706, 75414102, 75308662) | 0 | 4 | 1 | 5 |

  - The dropped events have M 0.45–1.97. 22 have an LDEO DD-RT solution.
  - Two of the five neighbour-limited events (75274076, 75274081, M 0.8–0.9) lie at the edge of the sequence,
    with only 7 and 21 events within 5 km.
  - The 120 km setting dropped no event that −1 would have kept (section 2.1).
- **Grid escapes and runaway events** (`grid_escapes.csv`). libhdd logs "TTT: n/n queries failed" when an event
  has moved outside the travel-time grids (depth −3 to 30 km). The event then keeps its last position for that
  iteration.
  - In P0/S0, three automatic events left the grid:
    - **75276711** ('A', 15 P) in 6 iterations, rising 5–32 km above sea level, then returning;
    - **75303031** ('A', 9 P) in 4 iterations; it ends 21 km north of the swarm, 2.2–2.4 km above sea level;
    - **75306441** ('A', 10 P) once, at 35.6 km depth.
  - In P1/S1, only **75307997** ('A', 18 P) left the grid, once.
  - Final positions that are wrong or doubtful:

    | event | flag, picks | NCSS start depth | LDEO DD-RT depth | P0 / S0 | P1 / S1 |
    |---|---|---:|---:|---|---|
    | 75303031 | A, 9 P | 1.0 km | 1.1 km | 21 km N, 2.2–2.4 km above sea level | 8.8 km, in the cluster |
    | 75306441 | A, 10 P | 1.2 km | 1.2 km | 9.2 km | **28.5 km depth** |
    | 75306291 | A, 9 P | 1.3 km | 1.3 km | **19.9 km depth** | **19.7 km depth** |
    | 75307997 | A, 18 P | 0.1 km | 0.6 km | 8.4 km | **13.9 km depth** |
    | 75277146 | A, 27 P | 3.5 km | 1.5 km | 1.9 km | **0.30 km above sea level** |
    | 75308582 | I, 15 P + 1 S | at sea level | none | 0.18 km above sea level | 0.25 km above sea level |
    | 75276711 | A, 15 P | 1.3 km | 1.7 km | 7.6 / 12.1 km (P0 ≠ S0 by 5.9 km) | 6.6 km |

  - All are small (M 1.3–2.2) automatic or 'I' events.
    - Five of them start at 0–1.3 km depth, with routine vertical errors of 3.9–13.8 km.
    - 75277146 and 75308582 have small routine errors (1.1 and 0.8 km) but start at 3.5 km and at sea level.
  - LDEO DD-RT puts six of them at 0.6–1.7 km depth. That is also doubtful for events of a 7 km deep swarm.
  - 2015 had no grid escape.
- 10 other relocated events start within 0.5 km of sea level or above it (7 'I', 2 'F', 1 'A'). Most move
  7–9 km down into the cluster (P1 median final depth 8.5 km). These are large but sensible moves.
  - LDEO DD-RT keeps at least one of them in the air (75279256, 'F', −0.23 km).
  - 75308132 ('I', start 13.6 km, no DD solution) ends at 16.3 km in P0/S0 and 8.7 km in P1/S1.

## 10. The 2015 and the 2025-26 sequences in one frame

**Method** (`compare_with_2015()` in the analysis script; outputs `comparison_2015_positions.csv`,
`comparison_2015_segments.csv`, `summary.json` → `comparison_2015`):

1. Each P1 solution keeps its own relative geometry. It is shifted by its own mean offset against its LDEO
   reference, on the common events of its analysis.
   - 2015 P1: (−826, −204, −2254) m against LDEO NCAeqDD v202112.1 (680 events).
   - 2025-26 P1: (−1366, −495, −2396) m against LDEO DD-RT (842 events).
   - After the shift, each P1 has its LDEO centroid.
2. Both LDEO catalogs share one frame. DD-RT relocates new events against the v202112.1 base catalog, and both use
   geoid depths. So the two shifted P1 solutions are in one absolute frame.
3. Both are projected to metres about 37.757 N, −121.940 E.
4. The axes come from the SVD plane of the shifted 2015 P1 (strike 354.6°, dip 86.1° E; origin = its centroid):
   - **along strike**: + toward N5°W;
   - **fault-normal**: + = east of the 2015 plane, toward 085°;
   - **down dip**.
5. **Checks:**
   - (a) the same with NCEDC DD-based offsets for both years;
   - (b) the two LDEO catalogs themselves, without rtDD, on each year's benchmark events.

**Result:**

| | P1 frame (LDEO offsets) | P1 frame (NCEDC offsets) | LDEO catalogs alone |
|---|---|---|---|
| 2025-26 centroid relative to 2015 | 4.10 km toward 147°, 178 m shallower | 4.13 km toward 145°, 75 m shallower | 4.10 km toward 148°, 196 m shallower |
| 2025-26 events: distance to the nearest 2015 event, 5 / 50 / 95 % (km) | 0.45 / 1.59 / 3.09 | 0.40 / 1.61 / 3.16 | 0.37 / 1.47 / 3.99 |
| 2025-26 events within 0.5 / 1 / 2 km of a 2015 event | 65 / 161 / 636 of 893 | 76 / 165 / 634 | 68 / 199 / 650 of 864 |

The frame choice changes the picture by about 0.1 km, much less than the structures below.

**Along the 2015 strike** (1 km bins of the along-strike coordinate; n, median fault-normal offset from the 2015
plane with the 10–90 % range, and the 2025-26 median depth):

| along strike (km) | 2015 P1 | 2025-26 P1 | 2025-26 LDEO DD-RT |
|---|---|---|---|
| −10 to −9 | – | 2 events, +1768 m | 3, +378 m |
| −9 to −8 | – | 24, **−728 m** (−926…−627), 7.8 km | 23, −509 m |
| −7 to −6 | – | 9, −2412 m (−2677…+2123), **4.5 km** | 8, −2063 m |
| −6 to −5 | 2, +1556 m | 34, +1955 m (+1620…+2259), 8.0 km | 31, +2123 m |
| −5 to −4 | 3, +1736 m | **245, +1981 m** (+1510…+2373), 7.2 km | 226, +2052 m |
| −4 to −3 | 1 | **314, +1903 m** (+1431…+2588), 7.1 km | 346, +1962 m |
| −3 to −2 | – | **190, +2307 m** (+1459…+2885), 6.8 km | 170, +2166 m |
| −2 to −1 | 45, +48 m (−319…+292) | 65, +1972 m (+1712…+2423), 6.8 km | 52, +1737 m |
| −1 to 0 | **333, +17 m** (−450…+201) | 6 | 3 |
| 0 to +1 | **165, −37 m** (−403…+280) | 3 | 2 |
| +1 to +2 | **127, +87 m** (−151…+462) | – | – |
| +2 to +4 | 5 | – | – |

**What this shows:**
- **The 2015 swarm is one strand.** 91 % of its events lie within ±0.5 km of its plane, over about 2.5 km along
  strike (5–95 %: −1.2 to +1.4 km).
- **The 2025-26 sequence lies beside it, not on it.**
  - Its main body has 835 events: along strike −6 to −1 km and more than 1 km east of the 2015 plane.
    - It lies 1.8–4.7 km (5–95 %) SSE of the 2015 swarm's centre along the 2015 strike.
    - It lies **1.5–2.6 km (10–90 %; median 2.0 km) east of the 2015 plane**.
  - 846 of the 893 events are more than 1 km east of that plane; only 8 are within 500 m of it.
  - Only 13 of the 893 events fall inside the along-strike range of the 2015 swarm, and those are still 1.8 km east
    of it (median).
  - **The main body is parallel to the 2015 strand.**
    - Its own SVD plane strikes 179° and dips 85.5° W in P1, with a median distance of 234 m. In LDEO it strikes
      173° and dips 85.3°, median distance 200 m.
    - The 2015 strand strikes 354.6° / 174.6°, so the two agree within 2–5°.
    - The median fault-normal offset is 1.9–2.3 km in every 1 km bin.
    - The whole-sequence planes (N10–15°E, section 4) are rotated by the two small groups to the south-west.
  - Its depth (median 6.8–8.0 km) matches the 2015 swarm.
- **The overlap between the two years is a small 2015 SE-edge cluster.**
  - It is five events: 71098439, 72549560, 72550205, 72554471 (four of the five "small separate cluster at the SE
    edge" events of report 11; the fifth, 72547870, lies 4.8 km west of the plane) and 72549990.
  - It lies 1.3–1.9 km east of the 2015 plane and 4.7–5.1 km south, inside the 2025-26 body.
  - These five events are the nearest 2015 event for 156 of the 161 2025-26 events that lie within 1 km of any
    2015 event.
- **Two small separate groups lie farther south:**
  - 24 events at 8–9 km along strike, 0.5–0.7 km west of the 2015 plane line, 7.8 km deep;
  - 9 events at 6–7 km, about 2 km west and only 4–5 km deep.
  - LDEO DD-RT shows both.
- **In plain words:** the 2025-26 sequence did not re-break the 2015 patch. It activated a parallel strand about
  2 km to the east and 2–5 km farther south-south-east, at the same depth. The only 2015 events on that strand are
  the five of the small 2015 SE-edge cluster.
- The relation rests on LDEO's absolute frame:
  - 2015 is a re-inversion and 2025-26 a real-time solution, both tied to the same base catalog;
  - the frame checks agree to about 0.1 km;
  - the ~2 km offset is 20× larger than that.

## 11. 2015 and 2025-26 side by side

| | 2015 (report 11) | 2025-26 (this report) |
|---|---|---|
| events / relocated / dropped | 685 / 680 / 5 | 927 / 893 / 34 |
| picks | 25,684 analyst | 41,870, 2,489 of them automatic (98 events automatic only) |
| phase pairs P / S | 320,207 / 38,267 | 521,099 / 36,169 |
| primary reference | LDEO NCAeqDD v202112.1 (re-inversion with cross-correlation) | LDEO DD-RT v202201 (real time) |
| reference neighbour spacing | 107 m | 210 m |
| references against each other, relative H / V | 162 / 236 m | 74 / 158 m (not independent) |
| NCSS start vs LDEO, relative H / V | 229 / 394 m | 307 / 730 m |
| P0 vs LDEO, relative H / V; local H / V | 142 / 134; 137 / 147 m | 167 / 274; 149 / 265 m |
| P1 vs LDEO, relative H / V; local H / V | **97 / 105; 51 / 63 m** | **145 / 311 (median-centred 145 / 233); 142 / 217 m** |
| improvement over the start, 3-D: P0 / P1 | 2.1 / 2.9 | 2.4 / 2.4 |
| events closer than the start, P1 (3-D / local) | 89 % / 98 % | 77 % / 94 % |
| P1 centroid offset vs LDEO (E / N / U) | −826 / −204 / −2254 m | −1366 / −495 / −2396 m |
| plane: LDEO vs P1 (median distance) | 352.5° / 83.6° E (121 m) vs 354.6° / 86.1° E (141 m) | 189.1° / 80.1° W (260 m) vs 15.6° / 87.7° E (367 m) |
| P accepted correlations (of measured); negative | 173,002 (58 %); 36,441 | 243,624 (54 %); 55,744 |
| median accepted lag P / S | 33 / 50 ms | 47 / 80 ms |
| correlation residual MAD, initial → final | 52.7 → 13.2 ms | 69.9 → 21.2 ms |
| catalog residual MAD (P0), initial → final | 51.3 → 27.0 ms | 71.1 → 39.3 ms |
| S0 vs P0: median / max | 0.25 m / 7.3 m | 1.1 m / 5.9 km (one grid escape) |
| S1 vs P1: median / max; identical lags | 1.1 m / 6.3 km; 97.9 % | 1.0 m / 25 m; 97.8 % |
| grid escapes | none | 3 events in P0/S0, 1 in P1/S1 (all automatic) |
| runtime P0 / S0 / P1 / S1 | 55 s / 54 s / 27.9 min / 19.4 min | 91 s / 114 s / 38.4 min / 29.0 min |
| peak memory P0 / S0 / P1 / S1 | 437 / 356 / 1,008 / 756 MB | 626 / 532 / 1,536 / 1,118 MB |

## 12. Caveats

- **The primary reference is a real-time solution, not a cross-correlation re-analysis.**
  - In 2015 the yardstick was LDEO's base catalog NCAeqDD v202112.1. It is a joint re-inversion of all events with
    waveform cross-correlation, made years later.
  - For 2025-26 no such catalog exists; the base catalog ends in 2021.
  - LDEO DD-RT (`NCAeqDDRT.v202201`, software DDRT-3.0) relocates each new event automatically, shortly after it
    happens. It works relative to the event's neighbouring *reference events of the base catalog* (up to 2021),
    with NCSS phase times and waveform cross-correlation against those reference events (catalog header;
    Waldhauser 2009).
  - The 2025-26 events are not re-inverted jointly with each other, and the catalog "may change over time".
  - Its formal 95 % errors (median 24–39 m) describe the fit of that real-time system, not the true accuracy.
  - NCEDC DD is the same kind of real-time DD-RT solution, from an older software version and with model-datum
    depths. The two references share method and data. Their mutual agreement (section 3) is therefore **not** an
    independent measure of reference error, as it was in 2015.
  - So "closer to LDEO DD-RT" means "closer to the real-time DD solution", not "closer to the truth". Differences
    of 100–200 m between rtDD and LDEO DD-RT cannot be assigned to either side.
- **Unreviewed picks.**
  - 98 events ('A' 97, 'H' 1) carry only the NCSS real-time automatic P picks (no S), 15 per event (median).
  - Their NCSS start positions inherit the automatic solution, and so partly do their DD-RT positions (section 8).
  - 253 picks in 'F' events are automatic as well.
  - All picks enter rtDD with equal weight (usePickUncertainties false, as in 2015). 1,531 picks (3.7 %) have an
    NCSS residual over 1 s.
  - The automatic events cause every grid escape (section 9).
- **Station network changes since 2015.**
  - Only 91 of the stations within 60 km are common to both years.
  - The dense NC C0xx/J0xx strong-motion sites close to San Ramon are mostly gone (70 in the 2015 station.csv, 10
    now, with 12 usable picks). The remaining ones are served only by EarthScope.
  - NP and CE strong-motion sites were added. 58 % of the S picks are on strong-motion HN channels (2015: 44 %).
    These are triggered recorders, some with late starts.
  - The two years therefore do not see their swarms through the same stations. Part of the quality difference
    between sections 3 and 11 is a network difference.
- **Near-station S delay.**
  - S picks within 5 km have tS/tP ≈ 2.15. The CON model with Vp/Vs 1.73 leaves +0.3 s median S−P residuals.
  - For double differences of close events this cancels. In the absolute equations of the default solver it does
    not, and it probably adds to the absolute-depth bias (section 7).
  - S makes up only 6.5 % of the phase pairs, which limits depth resolution.
- **Different velocity models and datums** (as in 2015):
  - our CON grids have no station corrections;
  - LDEO uses the NCSN 1-D models with geoid depths;
  - NCEDC DD's model-datum depths were converted with each event's NCSS datum, which is an approximation.
- **Waveform gaps:**
  - event 75311457 has no NC/CE/NP waveforms (NCEDC archive gap);
  - NC.CNI has outages.
  - rtDD falls back to catalog differential times there.
- **Statistics over all common events.**
  - The mean-centred metrics, centroids and planes use every common event, including the few runaway events of
    section 9. For this reason median-centred and local numbers are given next to them.
  - A single plane is a poor model of this sequence (section 10).
- **The 2015 comparison** rests on LDEO's absolute frame (section 10). rtDD's own absolute positions are biased
  differently in the two years (2015: 0.8 km W, 2.3 km deep; 2025-26: 1.4 km W, 2.4 km deep).
- **Choices made before looking at the results:**
  - all settings are the 2015 ones;
  - the one change asked for (maxEvStaDist 120 km) was fixed before any run, and its effect was checked by
    clustering only.
  - Nothing was tuned against the references.

## 13. Files

| file | content |
|---|---|
| `runs/sanramon2026/pyrtdd/run_pyrtdd_sanramon2026.py` | pyrtdd driver (copy of the 2015 driver; parameters at the top, dry run by default) |
| `runs/sanramon2026/pyrtdd/<P0,P1>/` | `options.json` (every option, read back from libhdd), `run_info.json`, `console.log`, `processing/` (libhdd's own output: `relocation.log`, `cluster-1-pair.csv`, `cluster-1-{initial,final}-double-difference.csv`, ...), `clusters/`, `relocated-{event,phase,station}.csv`; P1 also `xcorr_cache.csv` |
| `runs/sanramon2026/scrtdd/scrtdd_sanramon2026.py`, `scrtdd_common_sanramon2026.py` | scrtdd driver and settings (copies of the 2015 files) |
| `runs/sanramon2026/scrtdd/inputs/inventory_sc.xml`, `fdsnxml2inv.log` | SeisComP inventory made from `stations.xml` |
| `runs/sanramon2026/scrtdd/<S0,S1>/` | `seiscomp_user/{global,scrtdd}.cfg`, `run_options.json` (every value scrtdd used), `run_summary.json`, `time_v.txt`, `work/` (`reloc-*.csv`, `relocated.xml`, `scrtdd.log`, `multievent_*/` diagnostics) |
| `runs/sanramon2026/analysis/analyze_sanramon2026.py` | all comparisons |
| `.../analysis/metrics_vs_reference.csv`, `per_event_vs_reference.csv` | metrics a, b, f per solution and reference, and per event (with review flag) |
| `.../analysis/review_split.csv` | metric g |
| `.../analysis/plane_fit.csv` | metric c |
| `.../analysis/run_vs_run.csv`, `xcorr_triplets_P1_vs_S1.csv` | metric d |
| `.../analysis/xcorr_stats.csv`, `residual_stats.csv` | metric e |
| `.../analysis/dropped_events.csv`, `grid_escapes.csv` | metric h |
| `.../analysis/comparison_2015_positions.csv`, `comparison_2015_segments.csv` | the 2015 / 2025-26 frame (section 10) |
| `.../analysis/check_clustering_maxevsta.py`, `clustering_maxevsta_check.json`, `clustering_maxevsta_pairs_only_unlimited.csv` | the maxEvStaDist check (section 2.1) |
| `.../analysis/runtime.csv`, `positions_enu.csv`, `summary.json` | runtime and memory, all positions, everything in one file |
| `logs/13_sanramon2026_pyrtdd_20261018.log`, `..._pyrtdd_{P0,P1}_console.log` | pyrtdd run logs (with `/usr/bin/time -v`) |
| `logs/13_sanramon2026_scrtdd_{dryrun,apply}_*.log`, `..._scrtdd_{S0,S1}_driver_console.log` | scrtdd driver logs |
| `logs/13_sanramon2026_analysis_final.log`, `..._clustering_maxevsta_check.log` | analysis logs |
