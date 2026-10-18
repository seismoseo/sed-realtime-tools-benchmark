# Step C1: NonLinLoc and travel-time grids for the Gwangyang benchmark (2026-10-17)

## Result

**NonLinLoc builds and runs on Server A.** I made travel-time grids of the HypoDD velocity model for the
Gwangyang benchmark. pyrtdd reads them correctly.

- NonLinLoc **v7.00.16-beta** is the newest (and only) release tag. It compiled with the conda GCC 13.4
  in env `seiscomp`. There were **no source patches**. All 24 programs were built.
- Smoke test: the new `Vel2Grid` and `Grid2Time` re-created scrtdd's own test grid set
  (iasp91, 2-D, azimuthal equidistant): 32 time grids, 32 angle grids and 2 model grids, as expected.
- The Gwangyang grids cover **54 stations**, P and S, each with a travel-time grid and a take-off-angle
  grid (216 grids). They are in `data/gwangyang_11ev/inputs/nll_kim1983/time/`.
- **Accuracy.** I compared the grid times at the cluster centroid with an independent exact 1-D
  calculation of the same layered model. The largest difference is **2.0 ms for P** and **3.9 ms for S**.
  The grids are slightly slow throughout (mean +1.6 ms P, +2.9 ms S). That is the normal small error of
  the finite-difference method at 0.1 km cells.
- **Station lookup.** pyrtdd finds the grid of every station with its strictest default tolerance
  (0.1 m). The station positions stored in the grid headers reproduce the station table to better than
  1 mm.
- **Observed travel times.** I took PhaseNet+ pick time minus HypoDD (dt.cc) origin time and subtracted
  the grid time, using all 763 picks:
  - P: median **+0.036 s**, interquartile range −0.083 to +0.122 s.
  - S: median **−0.265 s**, interquartile range −0.385 to −0.132 s.
  - The S offset does not come from the grids. An origin-free Wadati fit by the independent check
    (S-P against P, one intercept per event) gives Vp/Vs = 1.727, so the model's 1.73 is right, but every
    event has an S-P intercept of -0.23 to -0.30 s: the reference S-P times are about 0.27 s shorter than
    the model predicts. That constant offset is a property of the picks (S early or P late), not of
    Vp/Vs; it pulls the simple tS/tP ratio down to 1.700. (Corrected 2026-10-17; the first version
    blamed Vp/Vs.)
- The grids are **byte-identical** when the script is run again from scratch: all 440 files have the same
  md5 checksums.

## How to use the grids

| program | setting |
|---|---|
| pyrtdd | `NLLGrid(gridPath='/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/nll_kim1983/time', gridModel='kim1983')`. The default `maxSearchDistance=0.1` (m) works. |
| scrtdd in SeisComP (global config) | add plugin `tttnll`; `ttt.NLLGrid.tables = kim1983`; `ttt.NLLGrid.kim1983.tablePath = /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/nll_kim1983/time/kim1983` (one value: folder plus model name); `maxSearchDistance` defaults to 10 m |
| scrtdd profile | `tableType = NLLGrid`, `tableModel = kim1983` |

The P grid also answers the phase names P, Pg and Pn, and the S grid answers S, Sg and Sn (plugin defaults).
The grid of a station is found by the station's **location**, not by its name. So the station
coordinates given to pyrtdd or SeisComP must equal those in `nll_kim1983/stations_gridded.csv`:
latitude and longitude from `used_stations_100km.csv`, and the elevation in metres.

## Things the next steps must know

1. **The StationXML inventory does not match the grids.** `reference/inventory/merged_inventory.xml`
   has these problems:
   - Every station elevation is **0 m**.
   - Six stations sit at other positions than in the station table: BOSB 14 m, EURB 9 m, HAMB 14 m,
     NAJA 137 m, SUCA 11 m and YNDB 33 m away.
   - **HADA** is missing.

   The validator tested these coordinates against the grids, using the scrtdd plugin's default tolerance
   of 10 m. **0 of 54 stations found their grid**, because the vertical mismatch alone is 45 to 698 m.
   A SeisComP inventory for scrtdd must therefore get its station latitude, longitude and **elevation**
   from `used_stations_100km.csv`, and it must include HADA. The other way round is to make a second set
   of grids from the inventory coordinates. The validator reports the inventory coordinates of every
   station in the `inv_*` columns of `validation.csv`.
2. **Station elevation.** The grids place each station at its real elevation (45 to 698 m above sea
   level). The benchmark's HYPOINVERSE and HypoDD runs put all stations at sea level, because HypoDD's
   layered model ignores elevation. Including the elevation adds up to 0.061 s (P) and 0.106 s (S) of
   travel time. So a comparison with HypoDD contains this small, station-dependent difference.
3. **S picks arrive about 0.27 s 'early' against the model.** The model uses Vp/Vs = 1.73, and an
   origin-free Wadati fit of the picks also gives 1.727 (per-event median 1.726), but each event's S-P
   intercept is -0.23 to -0.30 s. So keep Vp/Vs = 1.73 and treat the constant offset as a property of the
   reference picks. (HYPOINVERSE used its own S model, 3.40/3.79/4.58 km/s, and its own .arc S residuals
   also have a median of -0.24 s.) The simple median tS/tP of 1.6998 over 336 event-station pairs is
   pulled down by that offset. S residuals grow with distance,
   from −0.08 s (< 30 km) to −0.43 s (60–80 km). For double-difference relocation inside a 100 m cluster
   this hardly matters. For absolute single-event locations it will pull the solutions. I kept the model
   exactly as in hypoDD.inp, as asked.
4. **Mis-picks in the PhaseNet+ picks.** 17 of 763 picks (9 P, 8 S, 2.2 %) differ from the grid by more
   than 1 s:
   - 8 of the 9 P outliers are 5.7–10.8 s late, around or after the S time.
   - 7 of the 8 S outliers are 2.5–4.0 s late, and one is 7.1 s early.

   They are listed in the validation output. The medians above use all picks. Without these 17 picks the medians are +0.033 s
   (P) and −0.268 s (S).
5. **Take-off angles.** At the centroid the angle quality is 9 or 10 for every station, well above
   scrtdd's cut-off of 5. pyrtdd returned take-off angles for all 763 picks. The grid angles agree with
   the 1-D rays to 0.13° or better, except at three stations: YKDB, TOY2 and SUCA, at 65–68 km. They
   differ there by 3.4–9.6°. Those three stations lie at the distance where the first arrival switches
   from the direct wave (leaving upward at about 102°) to the head wave along the 15 km boundary (leaving
   downward at 69.6°). The grid smooths that jump over a few hundred metres. The travel times there still
   agree to 2 ms.
6. **The task text says 773 picks.** The 11 pick files contain 763 picks (360 P, 403 S), or 774 lines
   including the 11 header lines.
7. **KWJU and KWJ2 share one position.** They have the same latitude and longitude (35.1599 N,
   126.9911 E) and differ only in elevation (249 m and 238 m), so their grids are 11 m apart. pyrtdd picks
   the right grid for each: the P times differ by 0.64 ms, as expected. A `maxSearchDistance` of 11 m or
   more could confuse them if a station position were slightly off. Keep the tolerance small: 0.1–1 m
   works, because the headers reproduce the coordinates to under 1 mm. The scrtdd plugin default of 10 m
   is just below that limit.

## Versions

| item | value |
|---|---|
| NonLinLoc | tag `v7.00.16-beta` = commit `4bb22a7cc607355e158540506b859d582bd67d14` (2023-04-17; release published 2023-06-16), from https://github.com/alomax/NonLinLoc. The programs report "NonLinLoc v7.00.16 17Apr2023". |
| compiler / tools | conda-forge GCC 13.4.0 (`x86_64-conda-linux-gnu-cc`), CMake 3.31.8, GNU make, git 2.55 (env `seiscomp`). Build type Release (forced by NonLinLoc's CMakeLists.txt), `-fcommon`, conda's default CFLAGS. |
| run-time libraries | only the system `libc.so.6` and `libm.so.6`. The programs run without activating any conda env. |
| smoke-test recipe | scrtdd tag `v2.0.10`, `libs/hdd/test/data/nll/iasp91_2D_azimuthal_equidist` (identical to scrtdd master on 2026-10-17) |
| validation | env `pyrtdd`: pyrtdd (commit d122c3a, scrtdd v2.0.9 inside; the travel-time code is the same as v2.0.10), numpy 2.5.4, pandas 3.0.6, scipy 1.18.1, pyproj 3.8.0, obspy 1.5.1 |

Newer commits exist on NonLinLoc's `main` branch (25 commits up to 2026-01-22). I checked their change
notes. They add NLLoc features and fix NLLoc, Loc2ssst and build issues, plus a bug in reading GMT grd
surfaces in `velmod.c`. Nothing there changes Vel2Grid with LAYER models, Grid2Time, 2-D grids or
take-off angles. So the release tag is adequate for this work.

## What was done

Everything was run by `install/02_build_nonlinloc.sh`, one stage at a time with `--apply --stage <stage>`.
The log is `logs/02_build_nonlinloc_20261017.log`.

1. **build** (about 15 s)
   - Shallow `git clone` of exactly the tag. The script refuses to continue if the tag points to another
     commit.
   - `cmake -S software/src/NonLinLoc/src -B software/build/NonLinLoc`, then `nice -n 10 make -j8`.
   - NonLinLoc's CMakeLists.txt always writes the programs to `software/src/NonLinLoc/src/bin`. The script
     copies them to `software/NonLinLoc/bin` (24 programs: NLLoc, Vel2Grid, Grid2Time, Time2Angles,
     GridCascadingDecimate, Grid2GMT, LocSum, Loc2ssst, NLDiffLoc, ...).
   - Smoke test in `software/NonLinLoc/smoke_test/`. There was one compiler warning (`strncat` bound),
     which is harmless.
2. **grids** (about 13 s)
   - The station list is the union of `used_stations_100km.csv`, the three HypoDD `station.dat` files
     and the station codes of the SAC files. All three lists hold the same 54 KS stations.
   - The script writes the control files and runs Vel2Grid and Grid2Time for P and S.
3. **validate** (about 3 s): `install/02_validate_nll_grids.py`; details below.

### Grid design (and why)

- **Velocity model**: kim1983 exactly as in `2.HypoDD/02.dt.cc/hypoDD.inp`.

  | layer top | Vp | Vs = Vp/1.73 |
  |---|---|---|
  | 0 km (extended to −5 km) | 5.98 km/s | 3.456647 km/s |
  | 15 km | 6.38 km/s | 3.687861 km/s |
  | 32 km | 7.95 km/s | 4.595376 km/s |

  The top layer starts at −5 km, as in scrtdd's recipe, so that stations above sea level sit inside it.
- **2-D grids** (`GTMODE GRID2D ANGLES_YES`), as in scrtdd's recipe. For a 1-D model one grid of
  distance × depth per station is enough. The program reading the grid computes the distance from event
  to station itself.
- **Extent and spacing**:
  - Distance 0 to 120 km. The stations are 7.1 to 99.3 km from the cluster.
  - Depth −3.0 to 50.0 km. The highest station is at −0.698 km and the Moho at 32 km.
  - 0.1 km cells, giving 1201 × 531 nodes.
  - Vel2Grid samples the model at cell centres. Starting the grid at −3.0 km with 0.1 km cells puts the
    15 km and 32 km boundaries exactly on cell boundaries, so the layer boundaries are not shifted.
- **Map projection: transverse Mercator (TRANS_MERC, WGS-84) centred on the cluster
  (35.0000 N, 127.7286 E).** The task suggested AZIMUTHAL_EQUIDIST or SIMPLE. I checked NonLinLoc's
  source (`src/map_project.c`):
  - Its AZIMUTHAL_EQUIDIST is a **spherical** projection that uses the ellipsoid's equatorial radius
    (6378.137 km). For our stations it gets the cluster–station distance wrong by up to **331 m**, about
    55 ms for P and 96 ms for S.
  - SIMPLE (a 6371 km sphere) is wrong by up to 313 m.
  - SDC is wrong by 13 m.
  - Ellipsoidal TRANS_MERC is wrong by only 3.4 m (under 1 ms), measured against the WGS-84 geodesic
    distance.

  TRANS_MERC is one of the projections scrtdd's grid reader supports (`libs/hdd/nll/grid.cpp`). This was
  a configuration choice; no code was changed.
- **Stations**: `GTSRCE <code> LATLON <lat> <lon> 0.000 <elevation km>`, so NonLinLoc puts each station at
  depth −elevation. The label is the bare station code; all stations are network KS and the codes are
  unique.
- The remaining settings are copied from scrtdd's recipe: `GT_PLFD 1.0e-3 0` and `CONTROL 1 99991`.

### Output files

`data/gwangyang_11ev/inputs/nll_kim1983/` (1.1 GB):

| path | content |
|---|---|
| `stations.in`, `stations_gridded.csv` | the 54 GTSRCE lines; the station list with the source of each coordinate |
| `run/general.in`, `run/Vel2Grid.in`, `run/Grid2Time.in`, `run/phaseP.run`, `run/phaseS.run` | NonLinLoc control files |
| `model/kim1983.{P,S}.mod.{hdr,buf}` | velocity grids, written by Vel2Grid |
| `time/kim1983.{P,S}.<STA>.time.{hdr,buf}` and `.angle.{hdr,buf}` | the travel-time and take-off-angle grids, plus copies of the model grids (`kim1983.{P,S}.mod.*`) that Grid2Time puts there. pyrtdd and scrtdd need all of them in this one folder. |
| `validation.csv` | one row per station: distance, 1-D and grid times, angles, quality, observed medians, inventory comparison |
| `validation_picks.csv` | one row per pick: observed time, grid time, 1-D times, residuals |

NonLinLoc stores 2-D grids with two identical-size x-sheets (5.1 MB per file), although the header
says one. scrtdd reads only the first sheet. This only doubles the disk use.

### Validation (`install/02_validate_nll_grids.py`)

- **Independent 1-D calculation.** I wrote my own exact flat-layer first-arrival calculation:
  - It takes the fastest of the direct ray (Snell's law) and the head waves along the 15 km and 32 km
    boundaries.
  - Distances are WGS-84 geodesic distances, so no map projection is involved.
  - It checks itself before use: the head-wave formula equals a brute-force Fermat minimisation to under
    1 µs.
  - For our stations the first arrival is the direct wave up to about 66 km and the head wave along the
    15 km boundary beyond that (24 and 30 stations). The Moho head wave would only come first beyond
    about 130 km.
- **Grid readers.** Grids were read through `pyrtdd.hdd.NLLGrid`, the same C++ code scrtdd uses. As a
  cross-check I also read them with my own numpy reader, which re-implements NonLinLoc's transverse
  Mercator and scrtdd's interpolation. The two agree to under 2 µs.

| check | P | S |
|---|---|---|
| grid − exact 1-D at the centroid, largest absolute value (54 stations) | 2.04 ms (YKDB, 65 km) | 3.93 ms (JNHA, 94 km) |
| grid − exact 1-D, mean | +1.55 ms | +2.90 ms |
| take-off dip, grid − 1-D | ≤ 0.13° except 3 stations at the crossover (3.4–9.5°) | ≤ 0.13°; crossover 3.6–9.6° |
| angle quality at the centroid (scrtdd rejects < 5) | 9–10 | 9–10 |
| observed − grid, all picks: N / median / IQR | 360 / +0.036 s / [−0.083, +0.122] s | 403 / −0.265 s / [−0.385, −0.132] s |
| observed − grid: MAD×1.4826 / 5–95 % range | 0.156 s / [−0.219, +0.204] s | 0.186 s / [−0.482, +0.073] s |
| same, without 17 picks off by more than 1 s: median / std | +0.033 s / 0.139 s | −0.268 s / 0.182 s |

The station position read back from the grid headers (header → latitude/longitude/depth) is at most
0.65 mm from the station table horizontally, and 0 mm vertically.

## Reproduce

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker
bash install/02_build_nonlinloc.sh                        # dry run: shows every command and control file
bash install/02_build_nonlinloc.sh --apply --stage build  # clone + compile + install + smoke test
bash install/02_build_nonlinloc.sh --apply --stage grids  # refuses if grids already exist; remove first:
                                                          #   rm -rf data/gwangyang_11ev/inputs/nll_kim1983/model data/gwangyang_11ev/inputs/nll_kim1983/time
bash install/02_build_nonlinloc.sh --apply --stage validate
# or everything at once: bash install/02_build_nonlinloc.sh --apply
```

The helpers are `install/02_nll_station_list.py` (station list) and `install/02_validate_nll_grids.py`
(checks). Both run in env `pyrtdd`.

To use NonLinLoc by hand, run `export PATH=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/NonLinLoc/bin:$PATH`.
No conda env is needed to run the programs. Run them from the folder that holds the control files,
because NonLinLoc's INCLUDE paths are relative to the current directory.
