# Step C2: Gwangyang benchmark inputs for rtDD and the DL picker (2026-10-17)

## Result

All inputs for the 11-event Gwangyang benchmark are built and checked.

| input | check |
|---|---|
| rtDD catalog (CSV triplet) | Loads in pyrtdd's own C++ reader (the scrtdd v2.0.9 `libhdd` parser) with **0 mismatches**: 11 events, 763 picks, 54 stations come back exactly as written. The travel times it implies are **exactly** the travel times HypoDD's ph2dt used. |
| SDS miniSEED archive | **Sample-exact** for all 1656 SAC files. |
| per-event playback files | **Sample-exact** for all 1656 SAC files. |
| `stations.xml` | Schema-valid. Covers 141 of the 162 SAC channels. **21 channels at 7 stations have no metadata in `merged_inventory.xml`** (listed below; nothing was invented). |
| reference tables | Written for HYPOINVERSE, HypoDD dt.ct, HypoDD dt.cc and the PhaseNet+ picks. |
| settings note | Every reference-run setting is documented in `docs/reference_run_settings.md`. |

No source code was patched, no package was installed, and nothing under
`data/gwangyang_11ev/reference/` was written.

## Counts

| item | number |
|---|---|
| events | 11: 6 in 2021, 5 in 2026; KMA ML 1.1-2.2 |
| stations | 54, network KS; one sensor each: 32 HG (accelerometer), 17 HH (broadband), 5 EL (short period). 52-53 stations have data in the 2021 events, 47 in the 2026 events |
| picks (PhaseNet+) | **763**: **360 P + 403 S**. The task text said 773; the 11 pick files have 774 lines including 11 header lines, so the true count is 763 |
| picks used by ph2dt (HypoDD) | all 763 are ph2dt input; 748 end up in at least one `dt.ct` difference |
| HypoDD data | `dt.ct`: 1181 P + 1548 S; `dt.cc` with cc ≥ 0.7: 1017 P + 1509 S (measured before the threshold: 1226 P + 1575 S) |
| SAC files | 1656 (HH 546, HG 978, EL 132), 162 distinct channels |
| SDS files | **1041** channel-day files (7 days); 85.2 MB |
| playback files | 11, one per event; 87.9 MB |
| `stations.xml` | 47 stations, 141 channels in 222 channel epochs |
| channels without metadata | **21** (7 stations x 3 components) |

## What was done

All steps are in `install/04_gwangyang_inputs.sh`; one `--apply` run did everything. The log is
`logs/04_gwangyang_inputs_20261017.log`. The Python helpers live in `data/gwangyang_11ev/tools/` and
were run with env `pyrtdd`'s python (obspy 1.5.1, pandas 3.0.6, numpy 2.5.4).

The whole run was then repeated with `--apply` (the log holds both runs). All **1071 output files came
out byte-identical** (md5), so the build is deterministic.

1. **Small files copied from server B (read only).** The reference copy lacks 5 files that are needed to
   document the run: the cluster configuration `clusters/gwangyang.py`, `clusters/_base.py`, the
   command-line front ends `cli/run_pipeline.py` and `cli/bootstrap.py`, and the KMA catalog.
   - They are now in `data/gwangyang_11ev/reference_supplement/`, with md5 sums in its
     `PROVENANCE.md`.
   - The reference copy's `config.py`, `README.md` and `core/*.py` were checked against server B: all
     md5-identical.
2. **`make_rtdd_catalog.py`** builds the rtDD catalog and the cross-checks (details below).
3. **`make_waveform_archive.py --overwrite`** converts SAC to SDS plus playback files and verifies the
   round trip.
4. **`make_stations_xml.py`** writes the StationXML subset and the metadata checks.
5. **`make_reference_tables.py`** writes the tidy reference CSVs.
6. **`check_rtdd_catalog_with_pyrtdd.py`** re-reads the catalog with pyrtdd (installed in step B).

Upstream documents read: scrtdd `doc/base/multievent.rst`, `xcorr.rst`, `ttt.rst` and
`singleevent.rst` (master), pyrtdd `README.md` (master). Upstream source files read to confirm the
parser and channel rules: scrtdd tag **v2.0.10**
- `libs/hdd/catalog.cpp`, `catalog.h`, `csvreader.cpp`, `utctime.cpp`
- `libs/hdd/dd.cpp`, `waveform.cpp`, `waveform.h`
- `libs/hddsc/waveform.cpp`, `libs/hdd/ttt/nllgrid.cpp`
- pyrtdd `package/src/pyrtdd/obspy/waveform.py`

## Decisions, and why

1. **Event ids 1..11, not the 14-digit KMA ids.**
   - rtDD reads ids with `std::stoul` into a 32-bit `unsigned` (scrtdd v2.0.10 `libs/hdd/catalog.cpp:128`,
     `:167`; `catalog.h:71`). A 14-digit id is silently wrapped modulo 2^32, with no error.
   - This was shown with pyrtdd: `20210720161418` is stored as an unrelated number such as 740289715.
   - `event_id_map.csv` gives rtDD id ↔ KMA id ↔ HypoDD id (rtDD id = HypoDD id - 199999).
   - **The "KMA ids" are UTC times**: the KMA catalog time (KST) minus 9 h.
2. **Starting locations = HypoDD `event.dat`** (all three copies are identical). They equal the
   `.pha` event headers to the last digit.
   - **HypoDD did not start from these positions.** With `ISTART 1` it put all 11 events at their
     centroid, 34.999695 N 127.728889 E 13.942727 km (`hypoDD.log:67`), and relocated from there.
   - `event_centroid_start.csv` reproduces that start for rtDD: same origin times, every event at
     the centroid.
3. **Origin times = the `.pha` headers**, which are identical to the HYPOINVERSE `.arc`/`.sum`.
   - These are the origins that the `dt.ct` and `dt.cc` travel times were computed from.
   - They agree with `event.dat` except for event 3 (HypoDD 200002; see inconsistency 2).
   - With these origins, (pick time - origin time) in the rtDD catalog equals the `.pha` travel
     time exactly, for all 763 picks.
4. **Picks = exactly the ph2dt input.**
   - `ph2dt.inp:5` reads `Gwangyang_mod.pha`, which is byte-identical to `Gwangyang.pha`. The pipeline
     writes the fixed file and copies it to `_mod` to keep the old hand-workflow file name
     (`core/hypodd.py:94-97, 103`).
   - Absolute time = `.pha` origin + `.pha` travel time.
   - `lowerUncertainty`/`upperUncertainty` are left blank.
   - The ph2dt weight, the HYPOINVERSE weight code, the PhaseNet+ time, probability, polarity and
     amplitude, and the usage counts in `dt.ct`/`dt.cc` are in `phase_extra.csv`.
5. **channelCode: P → `<sensor>Z` (e.g. HHZ, HGZ, ELZ); S → `<sensor>N` (e.g. HHN).** `<sensor>` is the
   station's one sensor in the SAC set. Why:
   - The docs say channelCode is "used only in the cross-correlation and specifies the waveform to
     fetch for a phase" (multievent.rst:135).
   - The source code shows that rtDD keeps **only the first two letters** (band + instrument, e.g. HH)
     and adds the component it is configured to correlate (`libs/hdd/dd.cpp:1720`).
   - It **skips a pair whose two picks have different first two letters** (`dd.cpp:1495`). Hence one
     sensor code per station, for every event.
   - With an empty component list, it uses the pick's own third letter (`dd.cpp:215`).
   - P: the pyrtdd default component is `["Z"]` (README:479), so HHZ is what is loaded anyway.
   - S: the default is `["L2"]` (README:490). It loads both horizontal channels named in the inventory
     (dip 0) and uses sqrt(N² + E²), which does not depend on the sensor orientation. It needs the
     inventory (multievent.rst:95; xcorr.rst:10; README:401). The third letter of the S channelCode is
     then ignored.
   - S channelCode ends in **N** because the reference HYPOINVERSE phase file attaches every S pick to
     the N channel (all 763 channel codes match `PHS/Gwangyang.phs`).
   - **T was not used** (the scrtdd example does, multievent.rst:125). With an empty component list it
     would silently make rtDD rotate with the inventory azimuths, which are nominal and not verified
     here (see inconsistency 11).
   - The reference S cross-correlation used the better of raw N and raw E (`core/xcorr.py:157-162`).
     rtDD has no exact equivalent: its component list is a fallback order, not "best of".
6. **Stations.** `station.csv` uses the latitude, longitude and elevation of
   `station_table/used_stations_100km.csv` without rounding. These are the same numbers the NonLinLoc
   grids of step C1 were computed for. rtDD's `NLLGrid` finds a station's grid by its 3-D position
   (`libs/hdd/ttt/nllgrid.cpp:234-254`, tolerance `maxSearchDistance`), so these numbers must not
   change.
   - HYPOINVERSE and HypoDD used elevation 0 for every station.
   - An "elevation 0" station file was tried and **deleted**: it would not match the C1 grids.
7. **Waveforms.**
   - The SAC samples are float32 but all are whole numbers (largest |count| 14 455 063, below 2^24, so
     float32 holds them exactly). They were therefore stored as int32 with **STEIM2** compression,
     in **512-byte** big-endian records (the SeisComP/SeedLink standard).
   - Location code blank (SAC `khole` is unset everywhere).
   - SDS layout `YEAR/NET/STA/CHA.D/NET.STA.LOC.CHA.D.YEAR.DOY`.
   - Events 4 and 5 (2021-08-28 13:34:10 and 13:39:22) have overlapping windows: 2 452 529 samples,
     **all identical**. They were merged in the SDS day files only after checking that.
   - Real gaps are never filled. Days with two separate windows keep two traces: 456 day files.
8. **`stations.xml`** keeps every channel epoch of `merged_inventory.xml` whose code is in the SAC set
   and that overlaps 2021-07-01..2026-03-01. Coordinates, orientations, responses and comments are
   copied unchanged.

## Checks and their results

- **Picks vs PhaseNet+.**
  - The catalog (`.pha`) time minus the PhaseNet+ time is -10, -8, -3 or 0 ms (8, 59, 633 and 63 picks).
  - This is expected. HYPOINVERSE pick times are PhaseNet+ times **cut** (not rounded) to 0.01 s
    (`core/hypoinverse.py:102, 111`), and the PhaseNet+ times sit on the waveform sample grid.
  - **8 picks (all in event 9, 2026-02-02) are a full 10.000 ms early.** Their PhaseNet+ time lies
    exactly on a 10 ms boundary, single-precision SAC rounding put it a few microseconds below, and
    the cut then removed one whole step. They are listed in `inputs/checks/pick_mismatches.csv`.
  - The SAC header picks equal the PhaseNet+ times within 0.009 ms.
  - No PhaseNet+ pick is missing from the `.pha` file, and the `.pha` file has no extra picks.
- **Events.** See `inputs/checks/event_crosscheck.csv`.
  - `event.dat` in `00.ph2dt`, `01.dt.ct` and `02.dt.cc` are identical.
  - Origins in `.sum`, `.arc` and `.pha` are identical.
  - The KMA catalog differs from them by 0.1-1.25 s and 0.2-2.0 km. That is expected: KMA gives
    whole seconds and 0.01°.
- **Waveforms.** See `inputs/checks/waveform_manifest.csv` and `sds_files.csv`.
  - 1656/1656 SAC files are reproduced sample by sample, both from the SDS archive (read with
    `obspy.clients.filesystem.sds.Client`) and from the playback files.
  - SDS: 1041 files, 162 channels, 54 stations, 0 overlaps.
  - 585 day files hold one continuous trace and 456 hold two (two event windows on the same day).
  - Start times agree exactly for 1086 of the 1656 traces. In the other 570 (the later window in a day
    file shared with an earlier event: events 3, 5, 6 and 8, with 149, 150, 144 and 127 traces) the
    SDS start time is 1-23 µs (at most 0.0023 sample) away from the SAC start time: merging the two
    windows of a day snaps the later one onto the first window's 10 ms sample grid. The samples
    themselves are identical. (Corrected 2026-10-17 after the independent check; the first version of
    this note said only event 5 was affected.)
- **Inventory.** See `inputs/checks/inventory_channel_check.csv`, `channels_without_metadata.csv` and
  `station_sensor_table.csv`.
  - Every channel that has metadata has azimuth, dip and sample rate (100 Hz, equal to the SAC data).
  - Exactly one epoch covers every event window, and no epochs overlap.
  - Location codes match: blank in both.
  - **One sensor per station in the SAC set** (no station has two), and it equals the station table's
    sensor.

## Inconsistencies found

1. **Pick count**: 763, not 773 (see Counts).
2. **Event 3 (ML 2.2, HypoDD 200002) origin is 0.01 s later in `event.dat` (22:03:23.20) than in
   `.pha`/`.arc`/`.sum` (22:03:23.19).**
   - Cause: ph2dt writes the time as the number HHMMSScc held in single precision. Above 2^24 =
     16 777 216 such a number can only be even, so 22032319 becomes 22032320.
   - Of the 11 events, only this one is affected.
   - HypoDD copies it into `hypoDD.loc` and `hypoDD.reloc`, so their origin time for 200002 is 0.01 s
     late. The locations are not affected.
   - The reference tables give both `origin_time` (as HypoDD wrote it) and `origin_time_pha_datum`
     (corrected).
3. **HypoDD started all events at the centroid** (ISTART 1), not at the `event.dat` positions.
4. **HYPOINVERSE `.sum` vs `event.dat` positions differ by up to 0.0001° (≤ 14.4 m)**: `.sum` rounds to
   4 decimals and `ncsn2pha` cuts.
5. **HypoDD's centroid** (34.999695, 127.728889) differs from the plain mean of the `event.dat`
   positions (34.999691, 127.728882) by less than 1 m.
6. **`ph2dt.log:90` says "linked event pairs = 56"**, but `dt.ct` contains the 55 possible pairs.
7. **15 picks never enter `dt.ct`**:
   - JNHA, which has a single pick (event 9), so HypoDD sees 53 stations;
   - 14 picks that ph2dt rejected as outliers in every pair: event 1 YGJA P+S and CGPA S; event 2
     JASA P and CHRB S; event 3 CLSA P+S; event 4 YOA S; event 5 YALB P; event 6 CGWB S and CLSA P;
     event 8 SACA P and CGWB P; event 11 KKDA P.
   - They are all in `phase.csv` (the exact ph2dt input) with `n_dtct = 0` in `phase_extra.csv`.
     rtDD has no ph2dt-style outlier test, so the next step may want to drop them:
     `phase_extra.n_dtct == 0`.
   - Station JASA (75 km) shows why. Its P travel time is 12.6 s in events 3, 4, 6 and 9, as
     expected, but 18.51, 20.78 and 20.50 s in events 2, 8 and 10. Those three P picks are almost
     certainly S energy picked as P (JASA's S travel time is 21.5-22.9 s). Pairing them with the
     good ones makes the good ones look like outliers too (3-5 outlier pairs each).
8. **Metadata missing in `merged_inventory.xml` for 21 SAC channels (7 stations, 81 catalog picks:
   38 P + 43 S)**:
   - CGWB, CHRB, YALB, YKDB, YNDB: the reference used the HH broadband, but the merged inventory has
     only HG for these stations;
   - **HADA**: the station is absent. It is the second-closest station, about 10 km away, with 12 picks;
   - KWJU HH: the epoch ends 2015-10-01, but KMA data exist in 2021 and 2026.
   - All 21 channels exist in the KMA master StationXML on server B
     (`/home/msseo/works/27.Haenam_sequence/data/stations/responses/master/KS_KG_metadata_1.0.2.xml`,
     md5 687bf07d…), with epochs covering 2021-2026. That was checked read-only and **not** copied,
     because this step was defined as a subset of `merged_inventory.xml`.
   - Without them, scautopick cannot process these streams, and rtDD cannot use L2/T/R on their S
     picks. P on literal Z needs no inventory.
9. **Station elevations.**
   - `merged_inventory.xml` gives 0 m for every station.
   - The KMA station table gives 45-698 m.
   - HYPOINVERSE and HypoDD used 0 m.
   - `station.csv` uses the table values (decision 6).
10. **Station coordinates in the inventory vs the station table**: NAJA differs by 137 m (longitude
    126.8250 vs 126.8265), YNDB by 33 m, the others by ≤ 14 m. HypoDD's `station.dat` matches the
    table within 0.9 m.
11. **Orientations are nominal.**
    - Every horizontal in `stations.xml` has azimuth 0 or 90.
    - Every channel carries the comment "orientation: use registry/orientation.py, not this file".
    - KMA borehole horizontals are known to be re-oriented without metadata changes.
    - So T/R rotation is not trustworthy with this file. L2 and Z are unaffected.
12. **KWJU and KWJ2 are two instruments at the same site** (same latitude/longitude; master XML:
    STS-1 vs STS-2.5). Their records are not copies of each other: the vertical-component correlation
    was 0.38 and 0.17 in the two events checked. Both were used as separate stations, so the site
    counts twice in the reference.
13. **S velocities.** HYPOINVERSE used S velocities 3.40/3.79/4.58 km/s; HypoDD used Vp/1.73 =
    3.46/3.69/4.60 km/s.
14. **Picker comment.** The cluster file's picker comment says PhaseNet "stead", 1-40 Hz, threshold
    0.2, but the run used PhaseNet+ (raw data, threshold 0.3).
15. **DAMP has no effect.** The `hypoDD.inp` values (8, 6) do nothing with the SVD solver
    (ISOLV 1) that both runs used.
16. **Overlapping windows.** The playback file of event 4 contains the first 7-53 s of event 5
    (event 4's windows end after event 5's origin). A picker run on it may legitimately pick event 5
    too.
17. **SAC orientation.** SAC `cmpaz`/`cmpinc` are unset everywhere, so orientation can only come from
    the inventory.
18. **Dangling symlinks.** In the reference copy, `1.HypoInv/*/kim*_?.crh` are dangling symlinks to
    server B paths. The model values are in the `.prt` files and in `clusters/gwangyang.py:86-93`.

## Files

| path | content |
|---|---|
| `data/gwangyang_11ev/inputs/rtdd_catalog/station.csv` | 54 stations (rtDD format) |
| `.../rtdd_catalog/event.csv` | 11 events: `event.dat` positions, `.pha` origin times, KMA ML |
| `.../rtdd_catalog/event_centroid_start.csv` | same, all events at the HypoDD start centroid |
| `.../rtdd_catalog/phase.csv` | 763 picks (rtDD format; uncertainties blank) |
| `.../rtdd_catalog/phase_extra.csv` | per-pick side information |
| `.../rtdd_catalog/event_id_map.csv` | rtDD id, KMA id (UTC), HypoDD id, KMA UTC/KST time, ML |
| `data/gwangyang_11ev/inputs/sds/` | SDS archive, 1041 files |
| `data/gwangyang_11ev/inputs/playback/<event>.mseed` | 11 per-event files (to be sorted with `scmssort -E` before a playback) |
| `data/gwangyang_11ev/inputs/stations.xml` | StationXML subset |
| `data/gwangyang_11ev/inputs/checks/*.csv` | all cross-check tables named above |
| `data/gwangyang_11ev/reference_tables/` | `hypoinverse_kim1983.csv`, `hypodd_dtct.csv`, `hypodd_dtcc.csv`, `picks_phasenet_plus.csv`, `event_id_map.csv` (byte copy of the catalog one) |
| `data/gwangyang_11ev/reference_supplement/` | 5 read-only files from server B + `PROVENANCE.md` |
| `data/gwangyang_11ev/tools/*.py` | the 5 helpers |
| `docs/reference_run_settings.md` | how the reference run was made |

About the location tables:

- `east_m`/`north_m`/`up_m` are offsets from the centroid of the table's own 11 events.
- HypoDD's own `x_m`/`y_m`/`z_m` are relative to its starting centroid. They agree with the offsets
  after removing a constant shift: 0.6 m at most.
- For dt.ct the relocated cluster sits 23 m north and 72 m shallower than the start. For dt.cc it is
  within 1 m of the start.

## Reproduce

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker
bash install/04_gwangyang_inputs.sh            # dry run: prints every command
bash install/04_gwangyang_inputs.sh --apply    # about 1.5 minutes; log in logs/04_gwangyang_inputs_<date>.log
```

Each helper can also be run alone, in this order (later ones read files written by earlier ones):

```bash
PY=/home/msseo/miniforge3/envs/pyrtdd/bin/python
T=data/gwangyang_11ev/tools
$PY $T/make_rtdd_catalog.py
$PY $T/make_waveform_archive.py --overwrite
$PY $T/make_stations_xml.py
$PY $T/make_reference_tables.py
$PY $T/check_rtdd_catalog_with_pyrtdd.py
```
