# Step B: pyrtdd on Server A (2026-10-17)

## Result

**pyrtdd installs and runs on Server A.** It needed no source patches and no new conda packages.

- The repository's test suite passes: **46 passed, 0 failed, 0 skipped**.
- Relocating the repository's synthetic test catalog with the settings of its own regression test gives
  output files that are **byte-identical** to the reference result shipped in the repository.
- The README example (default settings) gives a slightly different answer from the reference: at most
  0.14 m horizontally, 0.69 m in depth and 0.02 ms in origin time. That is expected, because it uses
  different settings. During that relocation the events moved by about 1.8 km.
- A brand-new shell with only `conda activate pyrtdd` imports the package from the env. One travel time
  computed with it (Gwangyang ML 2.2 to KS.BAU) agrees with an independent hand calculation to better
  than 1 microsecond.

## What pyrtdd is

pyrtdd is a Python package for **double-difference relocation** (the HypoDD idea: relocate events
relative to each other from differences of travel times). It runs the same C++ engine ("libhdd") that the
SeisComP module scrtdd ("rtDD") uses, but it does **not** need SeisComP. Its inputs are:

- a catalog: three CSV files (stations, events, picks) or an ObsPy `Catalog` plus `Inventory`;
- a velocity model: either constant Vp/Vs (`Homogeneous`) or travel-time grids made by NonLinLoc (`NLLGrid`);
- optionally, waveforms for cross-correlation, through ObsPy (`pyrtdd.obspy.waveform`).

## Versions

| item | value |
|---|---|
| pyrtdd | git commit `d122c3ae50333839475f0d1134c01aba720153cd` (master, 2026-07-29, "Fix documentation"). pyrtdd has no releases; package version string 0.0.1 |
| scrtdd inside pyrtdd (`deps/scrtdd`) | commit `6e9035de92085168302de0ca1f49f42529cfb24c` = exactly tag **v2.0.9** (2026-07-29) |
| scrtdd v2.0.9 vs v2.0.10 (current release) | the relocation library `libs/hdd` is **identical**. v2.0.10 changed only a default config file, docs and the version number. So pyrtdd and the SeisComP scrtdd v2.0.10 module run the same relocation code |
| compiler | conda-forge GCC 13.4.0 (`x86_64-conda-linux-gnu-c++`), C++20, `-O3 -DNDEBUG` (CMake "Release") on top of conda's default flags (`-march=nocona -mtune=haswell -O2 ...`), link-time optimisation for the Python module |
| build tools | CMake 3.31.8, Ninja 1.13.2, pybind11 3.1.0, scikit-build 0.19.0, setuptools 84.0.0, wheel 0.48.0, pip 26.2.1 |
| Python stack (env `pyrtdd`, all from conda, untouched) | Python 3.12.15, numpy 2.5.4, obspy 1.5.1, pytest 9.1.1, scipy 1.18.1, pandas 3.0.6, pyproj 3.8.0 |

## What was done

All steps were run by `install/03_install_pyrtdd.sh`, one at a time and in order (`--apply --only <step>`).
A plain `--apply` runs the same steps in the same order. Everything is logged to
`logs/03_install_pyrtdd_20261017.log`.

1. **clone**: `git clone --recursive` of pyrtdd into `software/src/pyrtdd`, then checkout of the pinned
   commit. This also prints the commits and confirms the libhdd v2.0.9/v2.0.10 identity.
2. **install**:
   - Save `conda list` before.
   - `pip install --dry-run` to ask pip what it would install. The answer was `pyrtdd==0.0.1` only, so
     conda's numpy, obspy and pytest are left alone (checked by `install/03_check_pip_report.py`).
   - The real build: `pip install -v --no-build-isolation '.[obspy,test]'` with at most 16 compile jobs
     at `nice 10`. `--no-build-isolation` worked, so the fallback (an isolated build) was not needed.
   - Save `conda list` after and compare. The only difference is the new line
     `pyrtdd 0.0.1 pypi_0 pypi`. `pip check`: "No broken requirements found."
   - The build (configure + 30 compile/link steps + install) took about 16 seconds. There were no
     compiler warnings.
3. **pytest**: `pytest -v` from the repository root, after confirming that Python imports the
   *installed* copy (`site-packages/pyrtdd`), not the source tree.
4. **example**: three relocations of the repository's synthetic test catalog (42 events, 8 stations,
   near 47 N 8.5 E, homogeneous Vp 5.8 / Vs 3.36 km/s, no cross-correlation), each in its own folder
   under `runs/pyrtdd_selftest/`:
   - A `readme_snippet`: the README "Example workflow" code, word for word, with all options at their
     defaults (`install/03_pyrtdd_readme_example.py`). Only the catalog paths change, because the
     example runs outside the repository.
   - B `examples_relocate_py`: `examples/relocate.py` with only its three `TODO` catalog paths filled
     in (`relocate_filled.py` is kept in the folder).
   - C `test_dd_settings`: the settings of the repository test that checks the reference file
     (`install/03_pyrtdd_test_settings_example.py`).
5. **compare**: event-by-event comparison with the reference `package/test/py/data/relocated-event.csv`
   (`install/03_compare_relocated_events.py`) plus a byte-for-byte check of the three output files.
6. **importcheck**: a new shell with an empty environment (`env -i`). Only `conda activate pyrtdd` is
   done, then it runs from `runs/`, not from the repository (`install/03_pyrtdd_import_check.py`).

## Results

### Test suite

```
46 passed in 4.83s
```

The 46 tests cover:

- 16 tests of the C++ bindings, including two full relocations of the test catalog that are compared
  with the reference file;
- 18 tests of the ObsPy catalog conversion;
- 12 tests of the ObsPy waveform sources.

None needs the internet. The repository tests compare locations with a relative tolerance of 1e-5. At
47 N that is about 52 m in latitude, 6 m in longitude and 5 cm in depth, so "tests pass" by itself
guarantees only that much. The byte-for-byte check below is much stricter.

### Example relocations compared with the reference file

How the three settings differ:

| | A README defaults | B examples/relocate.py | C repository test |
|---|---|---|---|
| neighbour selection | 5 ellipsoids (Waldhauser 2009) | nearest neighbours | nearest neighbours |
| max neighbour distance | 5 km | 5 km | 15 km |
| down-weighting of large residuals | 10 then 5 | 10 then 5 | off |

Differences from the reference (new minus reference; all 42 events relocated in every run):

| run | max horizontal difference | max depth difference | max origin-time difference | output files |
|---|---|---|---|---|
| A README snippet | 0.136 m (median 0.128) | 0.687 m (median 0.550) | 0.020 ms (median 0.006) | event/phase files differ, station file identical |
| B examples/relocate.py | 0.133 m (median 0.126) | 0.682 m (median 0.546) | 0.020 ms (median 0.007) | event/phase files differ, station file identical |
| C repository-test settings | 0 | 0 | 0 | **all three files byte-identical** |

For scale: the relocation moved the events from their starting positions by 1834 m horizontally and
1594 m vertically (medians; up to 3.6 km and 3.4 km).

**Do they agree?** Yes.

- Run C reproduces the reference exactly. Our Server A build computes the same numbers, to the last printed
  digit, as the build that made the reference file.
- Runs A and B differ from it by well under 1 m, and in nearly the same way for every event:
  - every event is 0.08–0.14 m off horizontally;
  - all 42 events are shallower, 40 of them by 0.49–0.69 m (event 15 by 0.41–0.42 m, event 16 by
    0.03–0.04 m).

  So the shape of the cluster is the same to within about half a metre, and the small offset comes from
  the different settings.
- All runs fit the synthetic picks to an RMS of 0.29 ms (median event).

Per-event values are in `runs/pyrtdd_selftest/<run>/comparison_vs_reference.csv`. Columns:

- `dH_m`: horizontal difference [m];
- `dZ_m`: depth difference [m];
- `dT_ms`: origin-time difference [ms];
- `shiftH_m`, `shiftZ_m`: how far the reference relocation moved the event.

### Fresh-shell check

- `python -c 'import pyrtdd, pyrtdd.hdd; from pyrtdd.obspy import catalog, waveform'` printed "import OK".
- pyrtdd is loaded from `/home/msseo/miniforge3/envs/pyrtdd/lib/python3.12/site-packages/pyrtdd/`. No
  source or build folder is on `sys.path`.
- One travel time with `Homogeneous(5.8, 3.36)`:
  - from: the Gwangyang ML 2.2 hypocenter (event 20210827220322, HypoDD dt.cc result:
    34.99982 N, 127.72852 E, 13.93 km);
  - to: station KS.BAU (35.1027 N, 127.5968 E, 562 m);
  - result: **P 3.793404 s, S 6.548138 s**. Epicentral distance 16.555 km, vertical 14.492 km, ray 22.002 km.
- My own straight-ray formula gives the same values to better than 1 microsecond.
- `computeAll` also returns:
  - takeoff azimuth −46.3°. Note that this uses the −180..180 convention: −46.3° = 313.7°, i.e. NW;
  - takeoff dip 131.2° (0 = down, 180 = up);
  - dt/dΔ 14.425 s/deg;
  - dt/dh 0.11356 s/km.
- `dir(pyrtdd.hdd)`: `Catalog, ClusteringOptions, Config, DD, Homogeneous, Logger, NLLGrid, Neighbours,
  NoWaveformProxy, SolverOptions, ThreeComponents, TimeWindow, Trace, UTCClock, WaveformProxy,
  XCorrCache, XcorrOptions, hdd_ext`. The base class `TravelTimeTable` exists only in `hdd_ext`.
- The Jupyter kernel "pyrtdd" (registered by `00_create_conda_envs.sh`) starts this env's Python, so
  notebooks on that kernel get the installed pyrtdd.

## Problems and how they were handled

- **Build: none.** There were two harmless warnings:
  - a CMake developer warning (policy CMP0177) about the repository's `install()` path;
  - a setuptools note that `pyrtdd/lib` is not a declared package. The static library `libhdd.a`
    (2.8 MB) is copied into `site-packages/pyrtdd/lib/` but is not needed at run time.
- **My comparison helper had a bug (found and fixed).** The first comparison reported all origin-time
  differences as exactly 0. The real values are a few microseconds (for example
  `00.99928` vs `00.999274`). The cause: pandas 3 reads these times at microsecond resolution, and my
  code assumed nanoseconds, so it truncated to milliseconds. The helper now sets the unit explicitly.
  The comparison became its own step and was re-run. The wrong first output stays in the log, followed
  by a note saying so.
- **PYTHONPATH from `~/.bash_profile`.** It contains `/home/msseo/works/MudPy/src/python:`, a folder that
  does not exist, and the trailing colon means "the current folder". The install script removes it for
  its own run, for reproducibility. Normal use is not affected. Just do not run Python from inside
  `software/src/pyrtdd/package/src`: there, `import pyrtdd` would pick up the uncompiled source copy.
- **Build folder location.** scikit-build (the build tool pyrtdd uses) always builds inside the source
  folder (`software/src/pyrtdd/_skbuild/`, plus `pyrtdd.egg-info/`), not in `software/build/`. It
  has no option to change this. Repository plus build folder: 90 MB.

## Hints for the next steps (Gwangyang with pyrtdd)

- The default clustering requires at least 8 neighbours per event (`minNumNeigh = 8`) and at least 8
  differential times per event pair (`minNumPhases = 8`). With only 11 Gwangyang events, each event has
  at most 10 possible neighbours, so these limits matter.
- `Homogeneous` is a single-velocity model. A layered model such as kim1983 (the one used by the HypoDD
  reference) needs NonLinLoc travel-time grids (`NLLGrid`), from the NonLinLoc step.
- Accepted phase names by default: P, Pg, Pn and S, Sg, Sn. The PhaseNet+ picks use P and S.
- pyrtdd's log time stamps and the auto-named processing folders (`multievent_YYYYMMDDhhmmss_N`) use
  UTC, not Korean time.
- The C++ library's own unit tests (in `deps/scrtdd/libs/hdd/test`, Boost.Test) were not built here. They
  belong to the SeisComP/scrtdd build.

## Reproduce

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker
bash install/03_install_pyrtdd.sh                      # dry run: prints every command, changes nothing
bash install/03_install_pyrtdd.sh --apply              # clone, install, pytest, example, compare, importcheck
bash install/03_install_pyrtdd.sh --apply --only pytest   # a single step
```

- The `example` step refuses to overwrite existing results. Remove `runs/pyrtdd_selftest/readme_snippet`,
  `examples_relocate_py` and `test_dd_settings` first.
- Re-running `install` rebuilds and reinstalls the same pinned version. The first build took about 16 s.

To use pyrtdd afterwards:

```bash
source /home/msseo/miniforge3/etc/profile.d/conda.sh
conda activate pyrtdd
python -c "from pyrtdd.hdd import Catalog, DD, Homogeneous"
```

Alternatively, choose the "pyrtdd" kernel in Jupyter.

## Files

| file | content |
|---|---|
| `install/03_install_pyrtdd.sh` | the install/test script (dry run by default) |
| `install/03_check_pip_report.py` | stops if pip would install anything besides pyrtdd |
| `install/03_pyrtdd_readme_example.py` | run A, the README example |
| `install/03_pyrtdd_test_settings_example.py` | run C, the repository-test settings |
| `install/03_compare_relocated_events.py` | event-by-event comparison with the reference |
| `install/03_pyrtdd_import_check.py` | fresh-shell import, travel-time check, `dir()` |
| `logs/03_install_pyrtdd_20261017.log` | full log of every step |
| `logs/03_conda_list_{before,after}_pip_20261017.txt`, `logs/03_pip_dryrun_report_20261017.json` | proof that pip changed nothing but pyrtdd |
| `runs/pyrtdd_selftest/{readme_snippet,examples_relocate_py,test_dd_settings}/` | relocated catalogs, pyrtdd processing folders, comparison tables |
| `software/src/pyrtdd/` | source (pinned commit) and build folder `_skbuild/` |
