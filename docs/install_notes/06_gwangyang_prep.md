# Step 06: Gwangyang inventory, SeisComP configuration and reference dt tables (2026-10-17)

Driver: `install/06_gwangyang_prep.sh` (dry run by default; `--apply --stage master|inventory|validate|scinv|globalcfg|dtables|all`).
Log: `logs/06_gwangyang_prep_20261017.log`. Checks: `runs/06_gwangyang_prep/`.

The agent that ran this step stopped at the account's session limit after its last stage, before writing
this note; the coordinator re-checked the saved check files and wrote the note. One check threshold was
changed afterwards (see "dt tables").

## Why this step was needed

The first StationXML subset (`inputs/stations.xml`) could not serve SeisComP-mode scrtdd:
- every elevation was 0 m;
- five stations sat 9-137 m away from the coordinates that HypoDD and the travel-time grids use;
- 21 channels at 7 stations (CGWB, CHRB, YALB, YKDB, YNDB HH; HADA HG; KWJU HH) had no metadata at all.

As a result, with those coordinates only 6 of 108 travel-time-grid lookups succeeded, and KWJU silently
took KWJ2's grid (the two stations share latitude and longitude and differ by 11 m in elevation).

## What was done

1. **Master metadata.** Copied the user's canonical KMA master StationXML read-only from server B:
   `27.Haenam_sequence/data/stations/responses/master/KS_KG_metadata_1.0.2.xml`
   (md5 `687bf07ddca65c76e0855de6d3c2673d`) to `data/gwangyang_11ev/reference_supplement/inventory/`.
   This is also the source that `merged_inventory.xml` itself cites.
2. **`inputs/stations_rtdd.xml`.** The 54 stations and exactly the 162 channel codes of the SAC set.
   - Orientation, sample rate and response come from `merged_inventory.xml`, or from the master file for
     the 21 missing channels. Nothing was invented.
   - Station and channel latitude, longitude and elevation were replaced by the `station.csv` values,
     which the HypoDD reference and the NonLinLoc grids use. Every change is listed in
     `inputs/checks/inventory_coordinate_changes.csv`.
   - Responses and orientations are unchanged. Orientations stay nominal (0/90 degrees), so S
     cross-correlation should use L2, which does not depend on azimuth.
3. **`inputs/inventory_sc.xml`.** Made with `fdsnxml2inv`; checked with `scinv check` and `scinv ls`.
4. **SeisComP configuration.** `core.plugins = dbsqlite3` was written into `$SEISCOMP_ROOT/etc/global.cfg`
   (our own installation). The default `dbmysql` driver is not built, so commands needed
   `--core.plugins=dbsqlite3` before. The converted inventory is identical with and without the option.
5. **Reference dt tables** in `data/gwangyang_11ev/reference_tables/`:
   - `dtcc_measured.csv`: every cross-correlation measurement of the reference, including CC < 0.7;
   - `dtcc_used.csv`: what HypoDD read;
   - `dtct.csv`: the catalog differential times.
   Sign convention, as HypoDD defines it: dt = (t1 - ot1) - (t2 - ot2).

## Checks (all passed)

| check | result |
|---|---|
| StationXML schema | valid |
| channel codes vs SAC set | 162 = 162; all 1656 SAC files covered by exactly one epoch |
| pick coordinates vs `station.csv` | 763 of 763 equal |
| NonLinLoc grid lookups with the new coordinates | 108 of 108 find their own grid, at 0.1 m and at 10 m tolerance; nearest other grid at least 11 m away |
| same lookups with the old `stations.xml` coordinates | only 6 of 108 succeed; KWJU takes KWJ2's grid |
| SeisComP inventory | 54 stations, 54 sensor locations equal to `station.csv`, 255 streams = 255 StationXML channel epochs, all 763 picks resolve |
| `~/.seiscomp` | not created |

## dt tables

| table | rows | P | S |
|---|---|---|---|
| dtcc_measured | 2801 (CC 0.33-0.998; 275 below 0.7) | 1226 | 1575 |
| dtcc_used (CC >= 0.7) | 2526 | 1017 | 1509 |
| dtct | 2729 | 1181 | 1548 |

- **Consistency with HypoDD's own output.** All 1472 final-iteration cross-correlation rows and all 2645
  catalog rows of `hypoDD.res` are found in the tables. The largest difference in DT is 1.8 µs, which is
  rounding in `hypoDD.res`.
- **Tolerance change.** The first run failed its own check because the tolerance was 1 µs. It was set to
  10 µs (`make_dt_tables.py`, with a comment); the differential times are given to 1 ms.
- **For later comparisons.** Cross-correlation and catalog differential times of the same
  pair, station and phase differ by a median of 21 ms, with a 95th percentile of 354 ms and a maximum of
  955 ms. The reference slid its window by ±0.5 s on top of a ±0.5 s lag search, so lags near 1 s
  were possible. rtDD's default maximum delay is 0.5 s.
