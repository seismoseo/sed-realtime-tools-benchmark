# San Ramon 2025-26 sequence benchmark: inputs

Written 2026-10-18. All files are under `data/sanramon_2026/`. The tools are in `data/sanramon_2026/tools/`,
copied from `data/sanramon_2015/tools/` and changed only where the case differs (period, boxes, centre,
mainshock, model name, paths, log names); every case parameter is set once in `tools/sr_common.py`
(section 11). Every HTTP request, including failed ones, is logged in `logs/sanramon2026_requests.tsv` with URL,
form fields, HTTP status, bytes and seconds. The sources of all raw files, with md5 sums, are in
`data/sanramon_2026/reference/PROVENANCE.md`. Read this together with the 2015 description
(`docs/sanramon_inputs.md`); everything not repeated here works as described there.

## 0. Summary

| Item | Number |
|---|---|
| Benchmark box / period | lat 37.70–37.80, lon −122.01…−121.89; **2025-10-01 00:00 to 2026-10-18 00:00 UTC (end excluded)**; all magnitudes |
| NCEDC DD events in box (designated reference) | **864** (DD-RT; depths below the local model surface) |
| LDEO DD-RT `NCAeqDDRT.v202201` in box (supplementary, found during this work) | 864 DDRT-3.0 solutions (geoid depths, formal 95 % errors ~0.03 km) |
| LDEO base catalog NCAeqDD.v202112.1 | ends 2021: no events |
| NCSS routine events in box | 922 |
| **Benchmark events** (NCSS routine OR NCEDC DD location in box) | **927**, 2025-10-23 to 2026-09-28; ids < 2^32 |
| Analyst review | 764 'F'; **98 automatic only ('A' 97, 'H' 1)**; 65 'I' (2015: all 685 'F') |
| NCSS picks in benchmark events | 42,372 (38,405 P, 3,967 S); **41,870 in rtDD phase.csv** (37,929 P, 3,941 S), 594 stations |
| Mainshock 75305736 (Mw 4.18) | NCSS 37.75633, −121.94367, 9.56 km (geoid) · NCEDC DD 37.75998, −121.92766, 6.938 km (model datum) · LDEO DD-RT 37.75942, −121.93087, 6.845 km (geoid) |
| Median NCSS → DD shift | horizontal 0.67 km (NCEDC DD), 0.39 km (LDEO DD-RT); NCSS model depth 0.58 km deeper than NCEDC DD; NCSS geoid depth = LDEO depth (+0.02 km) |
| NCEDC DD vs LDEO DD-RT | common shift (+0.27 E, +0.13 N, −0.54 depth) km; inter-event vectors differ by 0.11 km horizontal, 0.23 km vertical (median) |
| Velocity model | NCSS **CON** (Concord–Calaveras), as in 2015: 918 of 927 events use CON only in the NCSS (processing "NC 06"); model surface 0.32 km above sea level; Vs = Vp/1.73 |
| Stations / grids | `stations.xml` 1,765 channels (NCEDC answered all 697 picked sensors); NonLinLoc TRANS_MERC grids for **300 stations within 120 km** (model `sanramon2026_con`), checked against ray1d (NLL later by ≤ 14 ms P, ≤ 25 ms S) and by rtDD itself (600 of 600 lookups) |
| Waveforms | cc: 927 events, 62,246 windows, 61,943 complete (`inputs/sds/`, 18,868 day files); dl: 26 events (`inputs/playback/`, 518 MB); see `docs/sanramon2026_waveforms.md` |
| DL subset | 26 'F' events, M 0.60–4.18, incl. 75305736 and the overlap event 75283011 |

**Main points for the next steps.**
* **There is a second DD reference**, although the task assumed NCEDC DD to be the only one: LDEO's real-time catalog
  `NCAeqDDRT.v202201` covers 2022 to 2026-10-17 with geoid depths. It and NCEDC DD agree well on relative positions
  but differ by a ~0.3 km horizontal / 0.5 km vertical shift. NCEDC DD stays the designated reference.
* **98 events have only automatic picks**; the DL subset uses only analyst-final ('F') events.
* The 2025-26 sequence sits **3.9 km SSE of the 2015 swarm** at the same depth, partly overlapping it, and is wider;
  **only 91 of the stations within 60 km are common to both years** (the dense NC C0xx/J0xx sites are mostly gone;
  NP and CE strong-motion sites were added).

## 1. The period and the box

* **Period:** 2025-10-01 00:00:00 UTC to **2026-10-18 00:00:00 UTC, end excluded** (sent to NCEDC as
  `mintime=2025/10/01,00:00:00`, `maxtime=2026/10/18,00:00:00`). The end is the last complete UTC day before
  the downloads (made 2026-10-18 from 03:20 UTC). The last benchmark event is on 2026-09-28; nothing in the box
  between then and the end.
* **Benchmark box:** lat 37.70–37.80, lon −122.01…−121.89, as set in the task. Note: the task called this "the
  same box size as 2015", but it is 0.10° × 0.12° (about 11 × 10.5 km); the 2015 box was 0.08° × 0.10°
  (37.75–37.83, −122.01…−121.91; about 9 × 9 km). We used the numbers given.
* **Wide box** (for id matching, as in 2015: box + 0.05° on each side): lat 37.65–37.85, lon −122.06…−121.84.
* **Benchmark events** (the 2015 definition): NCSS events whose routine **or** DD location lies in the box. In
  2015 "DD" meant either DD catalog (NCEDC or LDEO base). Here the designated DD reference is NCEDC DD, so the
  rule is "NCSS routine or NCEDC DD in the box". Using the LDEO real-time DD positions as well (section 2.2)
  would add no event (`event_matching.csv`, column `benchmark_if_ldeo_ddrt_used`).
* **Swarm centre** (median NCSS routine location of the benchmark events, rounded to 0.001°):
  **37.757 N, −121.940 E** (`sr_common.LAT0, LON0`; used for the NonLinLoc grids, the station distances and
  the waveform plan). The 2015 centre was 37.786 N, −121.963 E.

## 2. Reference double-difference (DD) catalogs

### 2.1 NCEDC DD catalog (the designated reference)

Query: `POST https://ncedc.org/cgi-bin/catalog-search2.pl` with form fields `format=<fmt>`,
`mintime=2025/10/01,00:00:00`, `maxtime=2026/10/18,00:00:00`, `minlat=37.70`, `maxlat=37.80`, `minlon=-122.01`,
`maxlon=-121.89`, `minmag=-5`, `maxmag=10`, `mindepth=-10`, `maxdepth=100`, `etype=E`, `no_mag=no_mag`,
`keywds=`, `outputloc=web`, `searchlimit=500000` (dates with slashes, as the form requires). Formats `ddcsv`,
`ddread`, `ddraw` (box) and `ddcsv` (wide box). `ddjson` was not requested again: in 2015 it did not return
JSON but built a "cross-section set" on the NCEDC site. Raw answers in `reference/ncedc_catalog/raw/`, text in
`.../txt/`; table `reference_tables/dd_catalog.csv` (wide box, flag `in_box`).

* **864 events in the box** (863 with magnitude; 1 "Mn 0.00"), 949 in the wide box; 2025-10-28 to 2026-09-28.
  (The task's check, 2025/10/01–2026/10/19 with the same box, gave 863; the extra event here is within the
  period, so the difference is a catalog update between the two queries or the end date; not investigated.)
* `ddread` = `ddcsv` exactly (864 events). `ddraw` positions within 12 m of `ddcsv` (0.01′ rounding).
* `ddraw` horizontal-error field = 0 for all; vertical-error field 0.01–0.57 km (median 0.05), undocumented
  for DD rows, as in 2015. All 864 have review character 'A' (DD solutions are automatic).
* **What it is.** NCEDC's DD catalog since 2012 consists of real-time DD-RT solutions (NCEDC blog 2014-06-02;
  copy in `reference/docs/`). The NCEDC search page, re-read 2026-10-18 and unchanged, still says that this
  catalog "is not generated by the most recent version of the software. It uses a depth datum that is
  referenced to the closest stations … Users should … obtain current, geoid referenced DD solutions from …
  https://nocaldd.ldeo.columbia.edu". So **NCEDC DD depths are model depths** (below the local station datum),
  not sea-level depths. Version string: none; recorded as "NCEDC DD as served on 2026-10-18".

### 2.2 LDEO: base catalog ends in 2021, but a real-time DD catalog covers 2025-26

* The LDEO **base** catalog NCAeqDD.v202112.1 (the primary reference of the 2015 benchmark) covers 1984–2021.
  The catalog directory https://nocaldd.ldeo.columbia.edu/catalog/ (fetched 2026-10-18, byte-identical to
  2026-10-17) lists no newer base version. It contains **none** of the 2025-26 events.
* **However**, the LDEO DD-RT front page (https://nocaldd.ldeo.columbia.edu/, "Last updated … Oct 18 03:22:09
  UTC 2026") links a download "DD real-time catalog, Jan 2022 - present":
  **https://nocaldd.ldeo.columbia.edu/catalog/NCAeqDDRT.v202201** (13.1 MB, fetched 2026-10-18 03:23 UTC with
  the CA bundle of 2015, certificate checking on; `reference/ldeo/NCAeqDDRT.v202201`). Its header: "Version:
  202201 — Created: Sat Oct 17 22:48:21 EDT 2026; Base catalog ID: DD202112.1; Software version: DDRT-3.0.ncsn;
  Includes events from 2022-01-01 to 2026-10-17". It is "automatically updated … hypocenter locations and
  origin times may change over time"; cite Waldhauser (2009) and the version number. Columns: date, time,
  lat, lon, depth, EX/EY/EZ ("formal least-squares relative location errors … at the 95% confidence level"),
  ML, CUSP id, version AA.BB, base catalog, method (DDRT-3.0, or HINV = no DD solution, NCSS location copied).
  The front page states that all depths are now **with respect to the geoid**.
* In our box: **864 DDRT-3.0 solutions** (no HINV rows), the same number as NCEDC DD but not the same set
  (75373076 only in NCEDC DD; 75276946 only in LDEO). Table: `reference_tables/ldeo_ddrt_catalog.csv`.
  Formal 95 % errors: median EX 0.026, EY 0.024, EZ 0.039 km (90 %: 0.047 / 0.045 / 0.067 km).
* **The task assumed NCEDC DD to be the only DD reference.** We kept NCEDC DD as the designated reference
  (benchmark definition, DL subset), and added LDEO DD-RT as a supplementary, geoid-referenced reference.
  Section 3.3 shows how the two compare. **Recommendation:** for the relocation comparison use **both**, and
  prefer LDEO DD-RT for absolute depths (geoid datum, same datum as the NCSS, rtDD inputs and NLL grids; newer
  DDRT-3.0 software against the 2021 base catalog).

## 3. NCSS routine catalog and picks; NCSS vs DD

### 3.1 Download and parsing

As in 2015: `format=ncphraw` (Hypoinverse archive, summary + phase lines) for the **wide** box, **one request per
week** (55 requests, largest answer 2.0 MB for 2026-01-28…02-04), plus `nccsv`/`ncread` (box) and
`nccsv`/`ncraw` (wide). All 63 catalog requests answered HTTP 200 on the first try. Reader:
`tools/hypoinverse_archive.py` (unchanged).

* **998 NCSS events in the wide box, 922 in the box; 927 benchmark events**, 2025-10-23 to 2026-09-28. All have
  picks.
* **Parser check:** all 998 summary lines agree with NCEDC's own `nccsv`: lat/lon within 7e-6°, depth, time
  and magnitude exactly.
* **Processing:** all 927 are "NC 06", depth type G (geoid), model type T (CRT gradient). In 2015 all were
  "NC 05". The crust-model label (cols 111–113) is blank, as in 2015.
* **Amplitude-only lines:** 26,441 station lines (HN 13,707, HH 12,727, EH 6, DP 1) have remark " P", weight 4,
  no data source, no S field and a "P time" equal to the origin time (checked: **all 26,441**). They are ML
  amplitude readings, not picks, and are left out (as in 2015). The QuakeML of the four cross-checked events
  holds no picks without an arrival, consistent with this.
* **Picks kept** (`reference_tables/picks_ncss.csv`): 45,008 in the wide box; **42,372 in benchmark events
  (38,405 P, 3,967 S)**. Weight codes, all wide-box picks: P 0: 10,401, 1: 13,329, 2: 12,526, 3: 3,928, 4: 18,
  5–8: 491; S 0: 8, 1: 2,690, 2: 1,508, 3: 79, 6–8: 30. (2015 had no weight-4 picks.)

### 3.2 New in 2025-26: not every solution is analyst-reviewed

Column 164 of the summary line ("version number of last human review" in the Hypoinverse manual hyp1.40, which
only passes it through; NCEDC's search form lists
`rflag=A,F,H,I`) was 'F' for all 685 events of 2015. In 2025-26:

| flag | events | in NCEDC DD | time span | picks (data source) | meaning (our reading) |
|---|---:|---:|---|---|---|
| F | 764 | 764 | 2025-11-09 – 2026-09-28 | Jiggle 'J' analyst picks (+ 253 'R') | final, analyst-reviewed |
| A | 97 | 96 | 2025-10-28 – 2026-02-05 | **only automatic real-time 'R' picks, P only** | automatic, never reviewed |
| H | 1 | 1 | 2026-02-03 | only 'R' picks (17 P) | |
| I | 65 | 3 | 2025-10-23 – 2026-02-06 | mostly 'J'; 62 have magnitude type 'Mh' | 62 of the 63 events without NCEDC DD |

The 'A' events cluster in the busiest weeks (Nov 2025 – early Feb 2026): the NCSS did not review all events of
the bursts. Consequences:
* The rtDD catalog includes them, as the 2015 rule includes every benchmark event, but their picks are
  automatic (P only, 15 per event median). `event_id_map.csv` gives `review_version` and the number of 'R'
  picks per event; `phase_extra.csv` gives each pick's `data_source`.
* For the **DL-picker test** the reference must be analyst picks, so the DL subset is drawn from 'F' events
  only (section 8).

### 3.3 Event matching and location differences

`reference_tables/event_matching.csv`, `location_differences.csv`, `dd_version_comparison.csv` (tool 13).

| In … but not in … | ids |
|---|---|
| NCEDC DD (box) → NCSS | none |
| NCSS (box) → NCEDC DD | **63** events (62 flag 'I', 1 flag 'A' (75276946)); e.g. 75253236, 75276546 … (full list in `stats_04.json`) |
| NCEDC DD (box) → LDEO DD-RT | 75373076 |
| LDEO DD-RT (box) → NCEDC DD | 75276946 |
| DD in box, NCSS routine outside | 75274076, 75342697, 75344977, 75433322, 75434697 (M 0.9–1.2; edges of the box) |
| NCSS in box, DD outside | none |

8 benchmark events have ids in a 7500xxxx series (e.g. 75004498; all 'F', all in DD), like the 71xxxxxx ids of
2015 (events added during review, typically the second event of a close pair).

| Comparison (864 / 863 events) | median | median of absolute value | 90th percentile of abs. |
|---|---|---|---|
| NCSS → NCEDC DD, horizontal | 0.67 km | | 1.34 km |
| NCSS model depth − NCEDC DD depth (same datum) | +0.58 km | 0.89 km | 2.03 km |
| NCSS − NCEDC DD origin time | −0.01 s | 0.04 s | 0.13 s |
| NCSS → LDEO DD-RT, horizontal | 0.39 km | | 1.03 km |
| NCSS geoid depth − LDEO DD-RT depth (same datum) | +0.02 km | 0.69 km | 1.91 km |
| NCSS − LDEO DD-RT origin time | +0.01 s | 0.04 s | 0.12 s |

**The two DD catalogs** (863 common events; NCEDC depth converted to sea level with each event's NCSS datum,
an approximation):
* median offset NCEDC − LDEO (E, N, depth) = **(+0.27, +0.13, −0.54) km**;
* after removing it: median 0.07 km horizontal, 0.16 km vertical (90 % of 3-D differences < 0.69 km);
* inter-event vectors (228,968 pairs closer than 2 km): median difference **0.11 km horizontal, 0.23 km
  vertical** (2015, NCEDC DD vs LDEO base: 0.25 / 0.38 km);
* for comparison, NCSS vs LDEO DD-RT inter-event vectors differ by 0.41 / 1.04 km.
So the two DD-RT catalogs agree well on the relative geometry but differ by a ~0.3 km horizontal and ~0.5 km
vertical shift (NCEDC shallower, as in 2015).

**Mainshock 75305736** (Mw 4.18): NCSS 37.75633, −121.94367, 9.56 km (geoid; datum 169 m) · NCEDC DD 37.75998,
−121.92766, 6.938 km (model datum) · LDEO DD-RT 37.75942, −121.93087, 6.845 km (geoid; EX 0.026, EZ 0.046 km).
Its routine depth is 2.7 km below both DD depths and its routine epicentre 1.1–1.4 km west of them.

### 3.4 Cross-check with the FDSN event service (`tools/05_crosscheck_fdsn_quakeml.py`)

QuakeML from `https://service.ncedc.org/fdsnws/event/1/query?eventid=<id>&includearrivals=true`
(`reference/fdsn_event/`); per-pick table `reference_tables/fdsn_pick_crosscheck.csv`.

| Event | QuakeML picks (= arrivals of the preferred origin) | archive picks | matched (net.sta.loc.cha + phase) | time differences |
|---|---|---|---|---|
| 75305736 (Mw 4.18, mainshock) | 518 (493 P, 25 S) | 518 | 518 | 517 equal, 1 at 0.01 s |
| 75261171 (Md 2.91, most S picks: 45) | 315 (270 P, 45 S) | 315 | 315 | 313 equal, 2 at −0.01 s |
| 75303161 (Md 1.63, flag 'A', automatic) | 17 (17 P) | 17 | 17 | all equal |
| 75305951 (Mh 1.60, flag 'I', no NCEDC DD) | 10 (9 P, 1 S) | 10 | 10 | all equal |

Phase names and channel codes agree for every pick; ±0.01 s is rounding.

## 4. Station metadata (`inputs/stations.xml`, `tools/06_download_stationxml.py`)

* **Requested** exactly as in 2015: every channel carrying an NCSS pick in a benchmark event (**894 channels,
  697 sensors**; 2015: 599 / 464) plus the other components of the same sensor, epochs overlapping the period.
  Bulk POST to `https://service.ncedc.org/fdsnws/station/1/query`, `level=channel` in 18 requests of ≤ 40 sensors,
  then `level=response` in 45 requests of ≤ 40 channels (about 47 s each; 63 requests, all HTTP 200 on the first
  try, 03:29–04:22 UTC). **NCEDC answered all 697 sensors**, so the EarthScope fallback was not needed.
* **Result:** `inputs/stations.xml` (50.8 MB; obspy merge, validated against the StationXML schema): **2,061
  channel epochs = 1,765 channels**, all from NCEDC; table `reference_tables/station_channels.csv`.
* **No picked channel lacks metadata** (2015: NC.J053.01.HNZ).
* **Networks** (channel epochs): NC 733, BK 560, NP 357, BG 93, CE 60, NN 56, BP 48, PB 42, WR 42, CI 37, RE 21,
  PG 6, GM 3, SB 3. New since 2015 among the picked stations: **CE** (California Strong Motion Instrumentation
  Program; 12 sites within 60 km), **BG** (The Geysers), **RE**, **GM**, **SB** (all > 120 km).
* **Epoch changes inside the one-year period** (242 channels have two epochs). Positions change for only five
  net.sta.loc (`stats_08.json`):
  * BK.BKS.00: a new epoch from 2026-10-13 switches the elevation convention (243.9 m → 218.3 m = 243.9 − 25.6 m);
    all BKS picks are older, and tool 08 takes the epoch that covers the picks (243.9 m, as in 2015, rule c).
  * BK.WEBR.00 HN: the new epoch (2026-01-28) says elevation **2.8 m** instead of 744.2 m, apparently a metadata
    error at NCEDC. The one HN pick is older; the station is 153 km away (no grid).
  * NC.NTR (92.5 km): EHZ replaced by an HH broadband on 2026-07-15, 27 m away (2.7 m lower). station.csv keeps
    the EHZ position (most picks); the 6 later picks are flagged `flag_station_moved` in `phase_extra.csv`.
  * NC.KMR (71 m elevation-convention change, 312 km away); CE.57202.10 (0.0001° in longitude, 9 m; 41 km).
* **Vertical-only sensors:** 162 of 697 (NC EH 159, NN EH 2, CI EH 1). Within 60 km of the swarm centre: 41 of
  252 sensors; within 120 km: 86 of 396 (2015: 42 of 246 and 80 of 308). They give no S picks and no S
  cross-correlation.
* **Sensor elevation:** the 2015 rules (tool 08 header) were applied unchanged. For the 594 stations of
  station.csv: depth ≈ 0 for 390, (a) channel elevation is the sensor elevation 170, (b) surface minus depth 19
  (PB boreholes, NC.CGP1, NC.MBS1, CI.SMR, WR.MOFF, NC.LCM, NC.PL11C), (c) BK vault overburden 11, other 4
  (BK.SUTB, BP.EADB, NC.MDH1, NC.MDH1.01; channel elevation used). Sensor elevations −243 to 3,324 m overall,
  −235 to 1,250 m within 120 km (BK.MHC highest, as in 2015).
* **Caveat for real-time scrtdd:** in multi-event mode scrtdd takes positions from station.csv (= our sensor
  elevations, which match the grids). A SeisComP inventory made from `stations.xml` carries NCEDC's raw channel
  elevations, which for rule-(b) stations differ by the borehole depth (up to 236 m), and for BK.WEBR HN after
  2026-01-28 by 741 m. For single-event (real-time) runs, check that the inventory elevations match the grid
  headers (as for Gwangyang, `docs/install_notes/06`).

## 5. Velocity model

See `data/sanramon_2026/inputs/velocity_model.md`. In short:
* **The NCSS uses CON here, as in 2015.** All 927 solutions are processing version "NC 06", which is the
  configuration of the newest NCSS Hypoinverse package (`hypoinv-standalone-20230210.zip`, still the newest on
  the NCEDC server on 2026-10-18). Applying the Hypoinverse multiple-model rule (hyp1.40 pp. 13–15) to every
  final epicentre with the nodes of its `multmod5a.hyp`: **918 events use CON only**, 924 get ≥ 90 % CON; two
  events at the south-west edge are blended with HAY (Hayward): 75342697 (66 % CON) and 75434697 (37 % CON).
  We use CON for all, as in 2015.
* CON (`cor.crt`, = shadow2000 Table 8): Vp 2.50 / 4.70 / 5.77 / 6.12 / 7.95 km/s at 0 / 2 / 12 / 24 / 26 km
  below the model surface, linear in between. **Model surface 0.32 km above sea level** (median NCSS datum of the
  927 events: 319 m, range 167–473 m; 2015: 0.29 km); 2.50 km/s extended up to 3 km above sea level.
* Vs = Vp / 1.73, as in 2015. The all-station Wadati slope of the 2025-26 picks is only 1.60 because many
  near-station S picks carry a large extra delay (tS/tP median 2.15 within 5 km); beyond 10 km the picks give
  1.776 (2015: 1.765). Median S−P residual with 1.73: +0.32 s (all), +0.26 s (> 10 km).

## 6. rtDD multi-event catalog (`inputs/rtdd_catalog/`, `tools/08_make_rtdd_inputs.py`)

Format of scrtdd `doc/base/multievent.rst`, exactly as in 2015. Run with
`scrtdd --reloc-catalog station.csv,event.csv,phase.csv` or pyrtdd's `Catalog(station, event, phase)`.

| File | Rows | Content |
|---|---|---|
| `event.csv` | **927** | NCSS **routine** origin time and hypocentre; depth = NCSS geoid depth (km below sea level); magnitude blank for the one event without (75321157) |
| `phase.csv` | **41,870 (37,929 P, 3,941 S)** | NCSS picks with weight code 0–3 and station metadata; uncertainty from the weight code |
| `station.csv` | **594** | net.sta.loc used in phase.csv; elevation = sensor elevation (m) |
| `phase_extra.csv` | 42,372 | every NCSS pick of the 927 events with raw Hypoinverse fields, `data_source` (J analyst, R automatic), `in_phase_csv`, `reason`, flags |

* **Event ids:** all < 2^32 (max 75,444,052), NCSS ids used unchanged (`event_id_map.csv`, which also gives
  `review_version`, magnitude type and the number of automatic 'R' picks per event).
* **Weight codes → uncertainty** exactly as in 2015 (shadow2000 Table 9): 0 → 0.02 s (9,642 picks), 1 → 0.10 s
  (15,086), 2 → 0.20 s (13,316), 3 → 0.30 s (3,826).
* **Excluded** (kept in phase_extra.csv): 484 picks with codes 5–9 (out-weighted by the NCSS) and 18 with code 4
  (no weight; 2015 had none). No pick lacks metadata. The de-duplication rule removed nothing.
* **Kept but flagged:** 1,531 picks with |NCSS residual| > 1 s (3.7 %; 2015: 2.4 %); 6 picks at NC.NTR
  (`flag_station_moved`). No S pick at or before P.
* **Automatic picks:** 2,489 of the 41,870 phase.csv picks are automatic real-time picks (data source 'R'): all
  picks of the 98 'A'/'H' events (P only) and 253 picks in 'F' events. In 2015: 47 of 25,916.
* **Picks per event:** P min 4, median 22, mean 40.9, max 479; S min 0, median 3, max 45; 181 events have no S;
  38 have < 8 P.
* **By channel type (phase.csv, P / S):** EH 20,218 / 690, HH 9,697 / 631, HN 6,208 / 2,301, EP 1,122 / 293,
  DP 508 / 23, BH 108 / 0, CN 68 / 3. 58 % of the S picks are on strong-motion HN channels (2015: 44 %).
* **Distance** (Hypoinverse epicentral distance of each pick): P 27,839 within 60 km, 7,092 at 60–120 km and
  2,998 beyond 120 km (no grid; 2,969 of them on the 294 stations beyond 120 km of the centre); S 3,937 within
  60 km, 4 at 60–120 km.
* **Checked with rtDD itself** (`tools/16_rtdd_integration_check.py`, pyrtdd): the triplet loads with 927
  events, 41,870 phases, 594 stations; the mainshock is present. rtDD's default clustering (8 neighbours,
  8 phases per pair) keeps **893 of 927** events in one cluster; the 34 left out have 4–16 P picks and are mostly
  'A' (15) or 'I' (12) events (2015: 680 of 685).
* Reader traps of 2015 avoided the same way (no trailing blank line; times with fraction and `Z`).

## 7. NonLinLoc grids (`inputs/nll_con_tm/`, TRANS_MERC only)

* **Recipe** as in 2015 (`GTMODE GRID2D ANGLES_YES`, `GT_PLFD 1.0e-3 0`, `VGGRID 2 1301 331 0.0 0.0 -3.0 0.1 0.1
  0.1 SLOW_LEN`: distance 0–130 km, depth −3 to 30 km, 0.1 km), but **`TRANS TRANS_MERC WGS-84 37.7570 -121.9400
  0.0`** (the swarm centre; the 2015 study recommended TRANS_MERC because NLL's AZIMUTHAL_EQUIDIST was off by up
  to 0.3 % in distance). Only this grid set was made. Model name **`sanramon2026_con`**.
* **Stations:** the **300** net.sta.loc of station.csv within 120 km of the centre (`nll_con_tm/stations_used.csv`;
  2015: 264); 294 stations with picks lie beyond 120 km (`stations_beyond_120km.csv`).
* **Built** by `bash tools/make_nll_grids_tm.sh` (NonLinLoc v7.00.16-beta, `software/NonLinLoc/bin`) in 40 s:
  600 time + 600 angle grids, `nll_con_tm/time/`, 3.9 GB; log `logs/sanramon2026_nll_grids_tm.log`, no errors or
  warnings. (As in 2015, the 2-D `.buf` files hold two x-planes; readers use the first.)
* **rtDD settings:** `NLLGrid(gridPath=".../data/sanramon_2026/inputs/nll_con_tm/time",
  gridModel="sanramon2026_con", maxSearchDistance=10.0)`; in scrtdd a TTT profile `NLLGrid` with table
  `.../nll_con_tm/time/sanramon2026_con`.

**Checks** (`tools/10`, `16`, `17`, `18`):
1. **NLL's TRANS_MERC = pyproj `tmerc`** (same origin, scale 1): station positions in the grid headers agree to
   ≤ 3 mm, so event distances in the grid plane can be computed exactly as rtDD does.
2. **NLL against ray1d** (independent ray code, itself within 5.6 ms of the NCSS TTGEN table; unchanged from
   2015), five stations: NC.CSR.01 (3.4 km, 0.23 km elevation), NP.1859.10 (20 km), BK.MHC.00 (53 km, 1.25 km,
   highest within 60 km), NP.1848.10 (85 km), PB.B067 (115 km, borehole sensor at −0.02 km). At 1,320 nodes per
   station and phase (5,318 head-wave, 3,984 turning, 3,898 direct nodes) NLL is **later by 0–14 ms (P) and
   0–25 ms (S)**, mean 9.6 / 16.5 ms; at 100 benchmark-event positions, read like rtDD (bilinear in the grid's own
   plane), 0.7–12.2 ms (P) and 1.3–21.0 ms (S). The same smooth finite-difference offset as in 2015.
3. **NLL against the NCSS TTGEN table** (virtual station on the model surface, 0.32 km above sea level;
   `nll_con_tm_validation/`): 720 points, mean +10.0 ms, max 18.3 ms.
4. **rtDD finds every grid:** pyrtdd's `NLLGrid` returned P and S times and take-off angles for all 300 stations
   (600 lookups, 0 failures) for the mainshock; difference from ray1d at near-geodesic distance ≤ 13.0 ms (P) and
   22.6 ms (S); take-off dips 44.1–156.8°.
5. **Projection error:** grid-header distances from the origin vs WGS-84 geodesic distances, all 300 stations:
   max **6.6 m** (`nll_projection_check.csv`). For 8 stations at 60–120 km, max distance error per transform:
   TRANS_MERC 6.6 m, LAMBERT 11.4 m, SDC 21.0 m, AZIMUTHAL_EQUIDIST 303 m, SIMPLE 429 m
   (`nll_transform_comparison.csv`) — the 2015 ranking.

## 8. DL-picker subset and waveform plan (`tools/12_select_dl_subset_and_waveform_plan.py`)

**(b) DL-picker test subset** (`inputs/dl_subset_events.csv`, 26 events): the 2015 rule, adapted only where the
2025-26 data force it.
* **Candidates:** benchmark events with an NCEDC DD solution (2015: in both DD catalogs), magnitude 0.5 to the
  maximum, ≥ 8 P picks in phase.csv, and **NCSS review flag 'F'** (new condition: in 2015 every event was 'F'; here
  98 events have only automatic picks, which cannot serve as reference picks for a picker test).
* **4 events per magnitude bin** (0.5–1.0, 1.0–1.5, 1.5–2.0, 2.0–2.5, 2.5–3.0, 3.0–4.18), each the event closest to
  the 1/8, 3/8, 5/8, 7/8 time quantile of its bin. Deterministic.
* **Forced:** **75305736** (Mw 4.18, required) and an overlapping-waveform test event. 2015 used the Md 2.32 event
  6.3 s before its mainshock. The 2025-26 mainshock has no neighbour within 10 s (nearest: 75305731, 31 s
  earlier). The same role goes to the earlier event of the < 10 s pair whose later event is largest:
  **75283011 (Md 2.29), 5.50 s before 75283016 (Mw 3.77)** on 2025-12-20 03:49 (tool 12 asserts this rule).
* **Result:** M 0.60–4.18 (4 events below M 1.0, 5 at M ≥ 3.0; Md 20, Mw 5, ML 1), 2025-11-10 to 2026-04-05,
  11–479 P and 0–36 S analyst picks per event. Only 75283011 has another event within 10 s (column
  `other_events_within_10s`). In the whole benchmark 13 pairs are < 10 s apart, none < 2 s (2015: 19 and 2).

**(a) Cross-correlation plan** (`inputs/waveform_plan_{channels,events}.csv`), as in 2015: all 927 events × every
channel of every picked sensor within 60 km of the centre: **672 channels at 188 net.sta.loc** (252 sensors, 41
vertical-only; 518 channels at 100 Hz, 99 at 200 Hz, 33 at 40 Hz, 22 at 500 Hz), window origin −10 s to +30 s;
about 3.1 × 10⁹ samples. (The downloader works per event: only the sensors that picked that event, 692 distinct
channels in all.)

**DL plan:** all channels in `stations.xml` of sensors within **80 km**, origin −120 s to +120 s (802 channels at
230 net.sta.loc; about 0.6 × 10⁹ samples). Unlike 2015, tool 12 now writes the values the downloader uses (2015's
plan said 120 km / −60…+120 s while its download used 80 km / −120…+120 s).

**Reference picks:** the NCSS analyst picks of `reference_tables/picks_ncss.csv` (all 26 events are 'F').

## 9. Waveforms

See **`docs/sanramon2026_waveforms.md`**. In short: all 1,036 requests succeeded at the first try. Of the 62,246 cc windows, 62,008 have data and 61,943 are
complete; 99.7 % of the requested phase.csv picks (75.6 % of all phase.csv picks) have data over rtDD's whole
cross-correlation window. The gaps are one NC.CNI outage and a 2-minute NCEDC archive gap (2026-02-09
22:04:55–22:06:54) that removes event 75311457 at NC/CE/NP stations. The 17 NC C0xx/J0xx strong-motion sites
picked in 2025-26 are served only by EarthScope. `scart --check` is clean on 18,868 day files. The playback
files hold every analyst pick of the subset except 2 at NC.CNI.

## 10. What differs from 2015, and what the next steps must know

Numbers from `reference_tables/comparison_with_2015.csv` and `stations_2015_vs_2026.csv`
(`tools/21_compare_with_2015.py`).

### 10.1 The swarm

| | 2015 | 2025-26 |
|---|---|---|
| events (benchmark) | 685 in 2 months | 927 in 12.5 months; bursts 2025-11-09/10, 12-08, 12-20/21, 2026-02-02…05, 03-02, 03-30 |
| largest | Mw 3.6 | Mw 4.18; then Mw 3.95, 3.90, 3.83, 3.80, 3.79, 3.77; 17 events of M ≥ 3.0 |
| centre (LDEO DD) | 37.7869 N, −121.9621 | 37.7585 N, −121.9360: **3.9 km SSE** (azimuth 144°) of the 2015 swarm |
| extent E–W / N–S (LDEO DD, 5–95 %) | 0.9 / 2.2 km | 2.4 / 3.5 km |
| depth, LDEO DD (geoid), 5/50/95 % | 6.6 / 7.2 / 8.3 km | 4.8 / 7.4 / 8.6 km |
| depth, NCEDC DD (model datum) | 5.7 / 7.0 / 8.2 km | 4.4 / 7.1 / 8.4 km |
| depth, NCSS routine (geoid) | 6.0 / 7.8 / 9.2 km | 3.4 / 7.4 / 9.5 km |
| best plane through the LDEO DD hypocentres (strike/dip, rms off-plane) | 352.7°/83.6°, 0.36 km | 189.4°/80.9°, 0.79 km |
| overlap | | 649 of 864 events within 2 km (3-D) of a 2015 event, 199 within 1 km, 68 within 0.5 km; median distance to the nearest 2015 event 1.5 km |

So the 2025-26 sequence lies at the same depth, on the same Calaveras-fault segment, overlapping the southern
part of the 2015 swarm and extending about 4 km further south-south-east. It is about twice as wide, and a single
plane fits it less well (rms 0.8 km): expect more than one structure. The plane numbers are a rough description
only. Both catalogs used here are the LDEO ones, which share the DD system and the geoid datum; the 2015 positions are the 2022
re-inversion, the 2025-26 ones real-time solutions.

### 10.2 The stations

* **Within 60 km of each centre:** 2015 199 net.sta, 2025-26 178; **only 91 in common**. Gone since 2015: 80 NC
  sites (mostly the dense NC C0xx/J0xx strong-motion sites close to San Ramon: 70 in the 2015 station.csv, 10
  in 2025-26, with only 12 usable picks; also short-period sites such as NC.CBS, NC.CHR, NC.CVP, and the borehole
  sites NC.CCH1, NC.CSU1, NC.CMW1), 24 NP, 3 BK (BK.CMAB, JRSC, SVIN), 1 PB. New: 42 NP, 18 NC, **12 CE**, 10 BK (e.g. BK.BRIB,
  LLNL, RVRP, TESL), 5 WR.
* By net.sta.loc (what rtDD and the grids use): 204 → 181 within 60 km, 65 in common. **50 stations recorded in
  both years changed location code** (e.g. NC.CAO, NC.GBB: '' → '01'), so 2015 and 2025-26 station lists cannot be
  matched on net.sta.loc.
* Within 120 km: 264 → 300 net.sta.loc (grids); with picks at any distance: 415 → 594 (BG Geysers stations and
  many far BK/NC sites now carry picks).
* Vertical-only sensors within 60 km: 42 of 246 → 41 of 252.
* Picks: phase.csv P picks per event median 19 → 22, S median 4 → 3; S fraction 12.2 % → 9.4 %. S picks on HN
  channels 44 % → 58 %; CN (500 Hz accelerometers) almost gone (519 P → 68 P); HH grew (3,128 → 9,697 P).

### 10.3 What the relocation step must know

1. **References:** NCEDC DD (designated; model-surface depths) and LDEO DD-RT `NCAeqDDRT.v202201` (geoid depths,
   formal 95 % errors ~25–40 m). They agree on inter-event vectors to 0.11 km horizontal / 0.23 km vertical
   (median) but differ by a common shift of (+0.27 E, +0.13 N, −0.54 depth) km. There is **no** cross-correlation
   base-catalog solution (like LDEO v202112.1 in 2015) for these events. Judge rtDD on relative positions against
   both, and on absolute depth against LDEO DD-RT.
2. **Grids:** `inputs/nll_con_tm/time`, model `sanramon2026_con`, TRANS_MERC centred on 37.757 N, −121.940 E. Model
   surface 0.32 km above sea level (2015: 0.29 km). Do not mix with the 2015 grids (other centre, other datum).
3. **Automatic events:** 98 events ('A'/'H') have only automatic P picks; 65 'I' events (62 without DD) are
   small and poorly picked. rtDD's default clustering leaves out 34 events (mostly these). Report results for the
   'F' events separately.
4. **S picks:** a large near-station S delay (tS/tP ≈ 2.15 within 5 km); the S model (Vp/Vs 1.73) leaves +0.3 s
   median S−P residuals. Harmless for double differences, visible in absolute residuals.
5. **Mainshock depth:** NCSS routine 9.56 km against ~6.9 km in both DD catalogs. The routine starting depths of
   the larger events are 2–3 km deep; expect large depth moves.
6. **Picks beyond 120 km** (2,998 P) have no grid: set `maxEvStaDist` ≤ 120 km.
7. **Real-time scrtdd:** check inventory elevations against the grids (section 4).
8. **Waveform gaps:** event 75311457 has no NC/CE/NP waveforms (NCEDC archive gap 2026-02-09 22:04:55–22:06:54);
   NC.CNI has outages (81 picks without data). rtDD will fall back to catalog differential times there.

### 10.4 What the DL-picker step must know

1. Reference = NCSS analyst picks; all 26 subset events are 'F'. For any other event check `review_version`:
   picks of 'A'/'H' events are the NCSS's own automatic picks, a ready-made automatic baseline (P only).
2. The overlap test event is 75283011 (5.5 s before the Mw 3.77 75283016, in the same playback window).
3. Network differences: only 17 of the dense near-field NC C0xx/J0xx sites still pick (their waveforms come from
   EarthScope); more NP/CE strong-motion (HN) sites; 41 vertical-only sensors within 60 km (the shipped DL models
   are 3-component). Triggered strong-motion records (NP, CE) may start late, as in 2015. BK.CMSB.00.HN? data are
   200 Hz while `stations.xml` says 100 Hz before 2026-03-13; processing normally uses the rate written in the
   records, but check any step that compares the two.
4. The playback window is −120 s to +120 s and covers every channel with metadata within 80 km.

## 11. Tools, in run order (`data/sanramon_2026/tools/`, env `pyrtdd`, `python -I <tool>`)

All tools are copies of the 2015 tools with the case parameters moved to `sr_common.py`; their headers say what
changed. All can be re-run safely (downloads skip files on disk; tables are rebuilt from the raw files).

| Tool | What it does here | Main outputs |
|---|---|---|
| `sr_common.py` | **case parameters** (`T0_STR`, `T1_STR`, `BOX`, `WIDE`, `LAT0`, `LON0`, `MAINSHOCK_ID`, `MODEL`, `NLL_SUBDIR`), paths, HTTP helper (one request at a time, ≥ 1 s apart, up to 5 tries with 4–32 s back-off), `log_request()` for the waveform downloader | `logs/sanramon2026_requests.tsv` |
| `hypoinverse_archive.py`, `ray1d.py` | unchanged copies | — |
| `01_download_reference_docs.py` | copies the 2015 documentation downloads (no request; listed in `reference/docs/COPIED_FROM_2015.txt`) and re-fetches the NCEDC search page and the Hypoinverse directory | `reference/docs/`, `reference/ncss_hypoinverse_metadata/` |
| `02_try_ldeo_dd_sites.py` | copies the 2015 CA bundle; fetches the LDEO DD-RT front page, the base-catalog directory and `NCAeqDDRT.v202201` | `reference/ldeo/` |
| `03_download_ncedc_catalogs.py` | NCEDC DD (ddcsv, ddread, ddraw) and NCSS (nccsv, ncread, ncraw, weekly ncphraw) | `reference/ncedc_catalog/` |
| `04_build_reference_tables.py` | parsing, parser check, LDEO DD-RT table, id matching, location differences; also the amplitude-line check, the benchmark centre and the processing/review flags | `reference_tables/{dd_catalog,ldeo_ddrt_catalog,ncss_catalog,picks_ncss,event_matching,location_differences}.csv`, `stats_04.json` |
| `05_crosscheck_fdsn_quakeml.py` | QuakeML pick comparison, 4 events | `reference/fdsn_event/`, `fdsn_pick_crosscheck.csv` |
| `06_download_stationxml.py` | StationXML, channel then response level (run in background; writes `reference/stationxml/DONE`) | `inputs/stations.xml`, `station_channels.csv`, `stats_06.json` |
| `07_velocity_model.py` | Hypoinverse model weights per event, CON model, datum from the data | `inputs/velocity_model.csv`, `ncss_model_weights.csv`, `ncss_con_ttgen_table.csv`, `stats_07.json` |
| `08_make_rtdd_inputs.py` | rtDD station/event/phase csv, phase_extra (+ `flag_station_moved`, `data_source`), id map (+ review flag, automatic picks) | `inputs/rtdd_catalog/*`, `event_id_map.csv`, `rtdd_stations_detail.csv`, `stats_08.json` |
| `09_make_nll_inputs.py` | NonLinLoc control files, TRANS_MERC by default, and `make_nll_grids_tm.sh` | `inputs/nll_con_tm/{run,stations.in,...}` |
| `make_nll_grids_tm.sh` | Vel2Grid + Grid2Time for P and S (log `logs/sanramon2026_nll_grids_tm.log`) | `inputs/nll_con_tm/time/` |
| `10_validate_nll_grids.py` | grids vs ray1d (5 stations; event lookups in the TRANS_MERC plane) and vs the NCSS TTGEN table | `nll_validation*.csv`, `stats_10.json` |
| `11_summary_counts.py` | counts by magnitude, pick, station, channel type | `summary_counts.csv` |
| `12_select_dl_subset_and_waveform_plan.py` | DL subset (2015 rule + 'F' only; overlap event 75283011) and waveform plan (80 km, −120…+120 s for DL) | `inputs/dl_subset_events.csv`, `inputs/waveform_plan_{channels,events}.csv` |
| `13_compare_dd_versions.py` | NCEDC DD vs LDEO DD-RT (shift, inter-event vectors) | `dd_version_comparison.csv`, `stats_13.json` |
| `14_vpvs_wadati.py` | Wadati Vp/Vs, all stations and beyond 10 km | `stats_14.json` |
| `15_write_provenance.py` | size, md5, source of every raw file (waveform folders summarised) | `reference/PROVENANCE.md` |
| `16_rtdd_integration_check.py` | loads the triplet and queries every grid through pyrtdd; default clustering | `rtdd_integration_check.csv`, `stats_16.json` |
| `17_check_nll_projection.py` | TRANS_MERC header distances vs geodesic distances | `nll_projection_check.csv`, `stats_17.json` |
| `18_compare_nll_transforms.py` | 5 NLL transforms for 8 stations at 60–120 km (temporary grids deleted) | `nll_transform_comparison.csv`, `stats_18.json` |
| `19_probe_waveform_services.py` | probes: EarthScope availability (retired), NCEDC dataselect answer format, no-data answer | `reference/waveforms_probe/` |
| `download_waveforms.py` | waveforms, cc set (SDS) and dl set (playback); resumable; ≤ 2 requests at a time | `inputs/sds/`, `inputs/playback/`, `reference/waveforms_raw/`, `waveform_requests_*.csv`, `waveform_sources_*.csv` |
| `check_waveforms.py`, `check_waveforms_seiscomp.sh` | waveform checks (obspy; SeisComP scart/scmssort) | `waveform_*.csv`, `stats_20_waveforms.json`; `runs/sanramon2026_waveform_checks/` |
| `check_playback_sort.py` | copy of `runs/sanramon/waveforms/check_playback_sort.py` (paths only): why `scmssort -E -u` output differs from the playback files | `runs/sanramon2026_waveform_checks/playback_sort_check.csv` |
| `21_compare_with_2015.py` (new) | swarm position/depth/plane and station network, 2015 vs 2025-26 | `comparison_with_2015.csv`, `stations_2015_vs_2026.csv`, `stats_21.json` |

Run order used: 03, 02, 01, 04, 05, 14, 06, 07, 13, 19, 08, 09, `make_nll_grids_tm.sh`, 10, 16, 17, 18, 11, 12,
`download_waveforms.py`, `check_waveforms.py`, `check_waveforms_seiscomp.sh`, `check_playback_sort.py`,
19 (probe 5), 21, 15.
