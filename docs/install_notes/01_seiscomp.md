# Step A: SeisComP 7.4.0 with scrtdd and scdlrtpicker on Server A (2026-10-17)

## Result

**SeisComP 7.4.0 (without graphical programs), the relocator scrtdd v2.0.10 and the deep-learning picker
plugin scdlrtpicker v1.1.1 compile, install and start on Server A.** No source code was changed and no conda
package had to be added.

All 14 smoke checks pass from a brand-new login shell (`install/01_check_seiscomp.sh --apply`):

- `source install/env_seiscomp.sh` sets everything up; `scautopick --help`, `scrtdd --help`,
  `scrtdd --version` (reports `scrtdd: 2.0.10`, `Framework: 7.4.0 Release`) and `msrtsimul --help` work.
- `python -c 'import seiscomp.core, seiscomp.client, seiscomp.datamodel'` works in the conda Python 3.12, and
  SeisComP arrays convert to numpy arrays.
- Every program and plugin finds all of its libraries inside the conda env or inside `SEISCOMP_ROOT/lib`.
  Only glibc itself (libc, libm, libpthread, libdl, librt, libutil) comes from the system. There is no
  "not found", even with `LD_LIBRARY_PATH` removed completely.
- The plugin uses exactly the ONNX Runtime release it was compiled against (1.31.0). The copy in
  `SEISCOMP_ROOT/lib` is byte-identical to it.
- **scautopick loads the plugin and creates all four deep-learning pickers** DL1C and DL3C (P pickers)
  and SDL1C and SDL3C (S pickers). As a control, without the plugin, scautopick refuses the same four
  names. Details are in "Evidence" below.
- 52 unit tests were compiled, including scrtdd's 5 `test_hdd_*` and 2 `test_hddsc_*` tests. They are
  only listed here; step T runs them.
- `~/.seiscomp` was never created.

**Not shown yet** (later steps): picking real waveforms with an ONNX model, and relocating events with
scrtdd. Both need station metadata, waveforms and configuration, which come with the Gwangyang tests.

## What was installed, in plain words

- **SeisComP** is the real-time earthquake monitoring system (data acquisition, picking, location,
  magnitudes). It is published as several git repositories that are put together into one source tree
  and compiled. We used `seiscomp` (build system and control script), `common` (libraries and Python
  modules), `main` (scautopick, scautoloc, scevent, scamp, scmag, scrtdd's companions, tools), `seedlink`
  (the data server and its plugins) and `extras` (msrtsimul and a few small Python tools).
- **scrtdd** ("rtDD") is SED's double-difference relocator. It can relocate one event at a time in real
  time, or a whole catalog offline. It brings a plugin, `tttnll`, that reads NonLinLoc travel-time grids.
- **scdlrtpicker** is a picker plugin (`dlrtpicker`). Inside scautopick or scolv it runs a neural-network
  picking model (PhaseNet, EQTransformer, ...), stored as an `.onnx` file, once per STA/LTA trigger (P)
  or once per P pick (S). 49 ready-made models come with it, in
  `software/src/seiscomp/src/extras/scdlrtpicker/models/`.
- **ONNX Runtime 1.31.0** is Microsoft's library that runs `.onnx` models. We used the official
  pre-compiled CPU release and checked its SHA-256. It is also the version in the `pyrtdd` env, where
  the Python `onnxruntime` package is 1.31.0 too.

## How to use it

```bash
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
scautopick --help
scrtdd --version
python -c 'import seiscomp.client'
```

The env file does three things:

1. It activates the conda env `seiscomp`.
2. It runs SeisComP's own `seiscomp print env`, which sets `PATH`, `LD_LIBRARY_PATH`, `PYTHONPATH` and
   `MANPATH`, and it exports `SEISCOMP_ROOT`.
3. It sets `SEISCOMP_LOCAL_CONFIG=.../runs/seiscomp_home/.seiscomp`. A value that is already set is kept.

Things to know:

- **Every SeisComP program creates a per-user folder at start-up**, normally `~/.seiscomp`, for its log
  files and personal settings (`Environment::init` in `common/libs/seiscomp/system/environment.cpp`).
  The env file moves that folder into the project, to `runs/seiscomp_home/.seiscomp`, so the home
  directory is never touched. Logs of SeisComP programs therefore end up in
  `runs/seiscomp_home/.seiscomp/log/`. For extra safety the check script also runs every SeisComP
  program with `HOME=runs/seiscomp_home`.
- **After sourcing, `timeout` is SeisComP's own program**, not the usual Linux one. SeisComP installs a
  `bin/timeout` with a different syntax; `timeout 60 cmd` then fails with "couldn't exec 60". Use
  `/usr/bin/timeout`. No other SeisComP program name clashes with a system or conda command; this was
  checked for all 75 programs in `bin/` (67 from the main build plus 8 Python tools from SeisComP/extras, e.g. msrtsimul).
- To use the picker, add `plugins = ${plugins},dlrtpicker`, `picker = DL3C` and `spicker = SDL3C` to
  scautopick's configuration. Also set `picker.DL3C.model` and `spicker.SDL3C.model` to an `.onnx`
  file, either in the bindings or as `module.trunk.global.picker.DL3C.model = ...`. See
  `src/extras/scdlrtpicker/README.md`.
- Nothing was set up as a running system: no `seiscomp setup`, no daemons, no crontab, no database.
  Only the SQLite database back-end was compiled; MySQL and PostgreSQL were left out.

## Versions

| item | version |
|---|---|
| SeisComP | 7.4.0 Release (API 17.4.0, data schema 0.14). Commits are listed in `docs/patches.md` |
| scrtdd | v2.0.10, commit `f801f859defac0634341480b98eb85021d5302ac` |
| scdlrtpicker | v1.1.1, commit `409b18fd6d933cd4ebd5354a0ff74998b6cb6113` |
| SeisComP extras (msrtsimul) | 7.4.0, commit `ced008a516b3273a1ccbb015d1cd597823b0f2ff` (the same commit as 7.3.0) |
| ONNX Runtime | 1.31.0 (released 2026-10-09; the newest stable), `onnxruntime-linux-x64-1.31.0.tgz`, sha256 `cc5c72baf5ae5c8238a6841f0897227be2d02826b9cf98eaf02fdefaeeb03a57` (as published by GitHub); `libonnxruntime.so.1.31.0` sha256 `469849977cb60744ea160927e1a3a0643fd4c55c0aff743251c6d293402e334e` |
| compiler | conda-forge GCC 13.4.0 (`x86_64-conda-linux-gnu-c++`), binutils 2.46.1, glibc headers 2.28 (runs on Server A's glibc 2.39) |
| CMake / make | 3.31.8 / GNU make (conda) |
| Boost | 1.84.0 (conda) |
| Python / numpy | 3.12.15 / 1.26.4 (conda) |
| libxml2, OpenSSL, SQLite, ncurses, flex | 2.13.9, 3.6.5, 3.53.4, 6.6, 2.6.4 (all conda) |

## Where things are

| what | path |
|---|---|
| SEISCOMP_ROOT (installed programs) | `software/seiscomp` (121 MB) |
| build tree (CMake, unit tests) | `software/build/seiscomp` (592 MB) |
| source tree | `software/src/seiscomp` (453 MB); scrtdd in `src/extras/scrtdd`, scdlrtpicker in `src/extras/scdlrtpicker` |
| ONNX Runtime used for compiling | `software/onnxruntime/onnxruntime-linux-x64-1.31.0` (+ the downloaded `.tgz`) |
| ONNX Runtime used at run time | `software/seiscomp/lib/onnxruntime-linux-x64-1.31.0`, plus the symlink `software/seiscomp/lib/libonnxruntime.so.1` |
| plugins | `software/seiscomp/share/plugins/dlrtpicker.so`, `tttnll.so` |
| configuration descriptions | `software/seiscomp/etc/descriptions/global_dlrtpicker.xml`, `scrtdd.xml`, `global_nllttt.xml` |
| scripts | `install/01_build_seiscomp.sh`, `install/01_check_seiscomp.sh` (+ `01_check_seiscomp_imports.py`), `install/env_seiscomp.sh` |
| log (build + checks) | `logs/01_build_seiscomp_20261017.log` |
| check outputs | `runs/01_check_seiscomp/` (inputs, `*.log` of the scautopick runs, `ldd_*.txt`) |

All paths are relative to `/home/msseo/works/74.SeisComP_rtDD_DLpicker`.

## What the build script does

`install/01_build_seiscomp.sh` runs these stages in order. Without `--apply` it only prints the commands.

1. **clone**: `git clone --depth 1 --branch <tag>` of the seven repositories. Each commit hash is
   printed to the log.
2. **ort**: downloads the ONNX Runtime release, refuses to continue unless the SHA-256 matches, and
   extracts it.
3. **configure**: runs `cmake` with these options:
   - `CMAKE_BUILD_TYPE=Release` and `CMAKE_INSTALL_PREFIX=software/seiscomp`.
   - `CMAKE_PREFIX_PATH=<conda env>`, so libraries are found in the env first.
   - `CMAKE_INSTALL_RPATH=<SEISCOMP_ROOT>/lib;<conda env>/lib`. Every installed program then knows
     where its libraries are, without `LD_LIBRARY_PATH`.
   - `SC_GLOBAL_GUI=OFF`, `SC_GLOBAL_UNITTESTS=ON` and `HDD_TESTS=ON`.
   - Python wrappers with numpy on.
   - Databases: SQLite on, MySQL and PostgreSQL off. Documentation off.
   - `SC_DLRTPICKER=ON` and `ONNXRUNTIME_ROOT=<extracted release>`.
   - Python pinned to the conda interpreter, its headers and its `libpython3.12.so`.

   `CMakeCache.txt` was checked: Boost, libxml2, OpenSSL, Python, numpy, SQLite, ncurses and flex all
   come from the conda env. Nothing comes from `/usr`, except `librt` from conda's own glibc sysroot.
4. **build**: `nice -n 10 make -j16 CC=<conda C compiler>`. Compiling everything takes about
   3.5 minutes on Server A. It ran 11:52:54-11:53:53 until the Reftek error described below, then
   11:56:11-11:58:33. The compiler printed 638 warnings (539 + 99 in the two runs), most of them in
   the SeedLink data-logger plugins (wave24, lib330, plugin, caps), and no error apart from the Reftek
   link error.
5. **install**: `make install`.
6. **ortlink**: extracts the ONNX Runtime release into `SEISCOMP_ROOT/lib` and symlinks
   `libonnxruntime.so.1` there, as the scdlrtpicker README describes.

## Problems met, and how they were solved

1. **The SeedLink Reftek plugin failed to link.** The build stopped at 48% with:
   ```
   x86_64-conda-linux-gnu-ld: .../reftek_libs/reftek/libreftek.a(steim.o): relocation R_X86_64_32S against
   symbol `transition' can not be used when making a PIE object; recompile with -fPIE
   collect2: error: ld returned 1 exit status
   ```
   Cause: this plugin builds three small helper libraries with hand-written Makefiles that hard-code
   `CC = gcc`. On Server A, plain `gcc` is the system compiler, Red Hat GCC 14.3.1, which by default makes
   code that cannot go into a "position-independent" (PIE) program. Everything else is compiled and linked
   by the conda GCC 13, which makes PIE programs by default. On Ubuntu both are the same compiler, so
   upstream never meets this.

   Fix, by configuration only: the script runs `make ... CC=$CC`. A variable given on the make command
   line wins over the value in every sub-Makefile. The objects left by the failed attempt are removed
   first with `make clean` in the three folders. The new objects say `GCC: (conda-forge gcc 13.4.0-20)`
   in their `.comment` section.
2. **scrtdd's unit tests were silently switched off.** scrtdd's CMake turns them on with
   `SET(HDD_TESTS ON)` just before `OPTION(HDD_TESTS ... OFF)`. Under CMake's old policy CMP0077, the
   first configure of a new build tree throws that setting away. The result was `HDD_TESTS:BOOL=OFF` and
   no `libs/hdd/test` in the build tree. CMake only printed a "developer warning" about it. Upstream
   users usually do not notice, because SeisComP's interactive configure is run several times, and from
   the second run on the tests are on. Fix: `-DHDD_TESTS=ON`. The warning is still printed but is now
   harmless.
3. **msrtsimul is not in `main`.** It is in the `SeisComP/extras` repository, so `extras` (7.4.0) was
   added. It contains only Python scripts, nothing to compile and no new dependency. This is a change
   from the original plan, which listed only seiscomp, common, main and seedlink.
4. **libbson is not needed.** SeisComP's README still lists `libbson-dev`, but SeisComP removed its BSON
   support, as its CHANGELOG says ("Remove BSON support"), and no CMake file of 7.4.0 asks for it. The
   libbson 2.x already in the env is not used, so no libbson 1.x was installed.
5. **Server A has a second Python 3.12** (`/usr/include/python3.12`, `/usr/lib64/libpython3.12.so.1.0`).
   SeisComP looks for Python through three different CMake modules. All three were pinned to the conda
   Python, so the wrappers are built against the conda one.
6. **A bug in my own script, not in upstream.** `conda activate` of the compiler package exports a
   variable `BUILD=x86_64-conda-linux-gnu`. That overwrote the script's own `BUILD` variable, and the
   first configure went to `./x86_64-conda-linux-gnu` instead of `software/build/seiscomp`. That folder
   was deleted, the variables were renamed to `SC_SRC_DIR` and `SC_BUILD_DIR`, and the script now stops
   if any of its folders is outside the project.

Observations that need no action:

- `lib/libhdd.so` (scrtdd's engine) is not linked to Boost.Filesystem itself. Checked on its own, it has 11
  unresolved Boost.Filesystem symbols. Every program and plugin that uses it gets Boost.Filesystem through
  `libseiscomp_core`, and `ldd -r` reports 0 unresolved symbols for `scrtdd` and `tttnll.so`. This is how
  upstream builds it.
- SeisComP's Python modules are linked to `libpython3.12.so`, while the conda `python` has Python built
  into the program itself. Ubuntu's Python is built the same way, and the imports work (check 3).
- `--disable-new-dtags` in conda's compiler flags makes the search path a classic `RPATH`. Unlike the
  newer `RUNPATH`, an `RPATH` of a program also applies to the plugins it loads. This helps
  `dlrtpicker.so` find `libonnxruntime.so.1`.

## Evidence (from `logs/01_build_seiscomp_20261017.log`, second check run, 12:05:59)

Library audit, with `LD_LIBRARY_PATH` unset (an excerpt; all 13 files were audited in both modes, and all
had "0 bad"):

```
bin/scautopick: 24 libs: 3 SEISCOMP_ROOT/lib, 16 conda, 5 glibc, 0 bad
bin/scrtdd: 26 libs: 5 SEISCOMP_ROOT/lib, 16 conda, 5 glibc, 0 bad
share/plugins/dlrtpicker.so: 25 libs: 4 SEISCOMP_ROOT/lib, 16 conda, 5 glibc, 0 bad
share/plugins/tttnll.so: 24 libs: 3 SEISCOMP_ROOT/lib, 16 conda, 5 glibc, 0 bad
lib/libseiscomp_core.so: 22 libs: 1 SEISCOMP_ROOT/lib, 16 conda, 5 glibc, 0 bad
```

Plugin test. scautopick checks its pickers right after start-up, before it looks for stations:

- If the P picker is unknown, it stops with "Picker 'X' is not available".
- If the S picker is unknown, it stops with "Unknown secondary picker: X".

With an empty station list it ends with "No stations added ... nothing to do" (exit code 1). That is
expected, and that message can only be reached after both pickers have been created. The runs had no
messaging, no database and no waveforms:

```
no plugin, picker = DL3C   -> [error] Picker 'DL3C' is not available, abort application
no plugin, picker = DL1C   -> [error] Picker 'DL1C' is not available, abort application
no plugin, spicker = SDL3C -> [error] Unknown secondary picker: SDL3C
no plugin, spicker = SDL1C -> [error] Unknown secondary picker: SDL1C
plugins = dlrtpicker, picker = DL3C, spicker = SDL3C ->
    [info] Plugin dlrtpicker registered
      description: ONNX Runtime based deep-learning P/S pickers (DL1C/DL3C/SDL1C/SDL3C)
          version: 1.1.1
    [error] No stations added (empty module configuration?) and thus nothing to do
plugins = dlrtpicker, picker = DL1C, spicker = SDL1C -> (same three lines)
```

The `ctest -N` listing ends with `test_hdd_waveform`, `test_hddsc_ttt`, `test_hddsc_waveform` and
`Total Tests: 52`.

## Reproduce

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker
bash install/00_create_conda_envs.sh --apply      # only if the env 'seiscomp' does not exist yet
bash install/01_build_seiscomp.sh                  # dry run: shows every command
bash install/01_build_seiscomp.sh --apply          # about 5 minutes (3.5 minutes of compiling)
bash install/01_check_seiscomp.sh --apply          # 14 smoke checks, under a minute
source install/env_seiscomp.sh                     # then use SeisComP
```

A single stage can be repeated, for example `bash install/01_build_seiscomp.sh --apply --stage build`.
`make` only redoes what is missing.

## For the next steps

- Step T, unit tests: run `ctest` in `software/build/seiscomp` with the env sourced. scrtdd's README says
  its NonLinLoc test grids must be generated first, with `generate.ch` in
  `src/extras/scrtdd/libs/hdd/test/data/nll/` and the NonLinLoc programs on `PATH`. Those grids are
  written into the source tree, and the tests run from there.
- For waveform tests, the models are in `software/src/seiscomp/src/extras/scdlrtpicker/models/`. Their
  input windows differ a lot (`models/table.txt`, at 100 Hz):
  - PhaseNet and PhaseNetLight: 3001 samples, which is 30 s.
  - EQTransformer, EQCCT and OBSTransformer: 6000 samples, which is 60 s.
  - BasicPhaseAE: 600 samples, which is 6 s.
  - EQTP: 12000 samples, which is 120 s.
  - Skynet: 30000 samples, which is 300 s.

  The plugin README says the scautopick defaults (`ringBufferSize` 300 s, `leadTime` 60 s) are fine
  for windows up to about 60 s; longer models need both raised. It also advises a permissive STA/LTA
  trigger and `killPendingSPickers = false`.
- msrtsimul is available for real-time playback of miniSEED files.
