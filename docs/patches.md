# Source patches

Every change made to upstream source code in this project: file, unified diff, reason.
Sections are per install step; a step with no patches says so.

## Step B: pyrtdd (install/03_install_pyrtdd.sh), 2026-10-17

**No source patches.** pyrtdd commit `d122c3ae50333839475f0d1134c01aba720153cd` and its submodule
`deps/scrtdd` at `6e9035de92085168302de0ca1f49f42529cfb24c` (tag v2.0.9) were built exactly as cloned.
`git status` in `software/src/pyrtdd` shows only untracked build and test products (`_skbuild/`,
`pyrtdd.egg-info/`, `package/test/py/__pycache__/`, `.pytest_cache/`). No tracked file was modified.


## Step C1: NonLinLoc (install/02_build_nonlinloc.sh), 2026-10-17

**No source patches.** NonLinLoc tag `v7.00.16-beta` (commit `4bb22a7cc607355e158540506b859d582bd67d14`,
the newest release) was built exactly as cloned. `git status` in `software/src/NonLinLoc` is clean: the
programs are written to `src/bin/`, which the repository's own `.gitignore` excludes. No configuration
work-around was needed either (the project's CMakeLists.txt already adds `-fcommon` for GCC >= 10).


## Step A: SeisComP 7.4.0 + scrtdd v2.0.10 + scdlrtpicker v1.1.1 (install/01_build_seiscomp.sh), 2026-10-17

**No source patches.** All seven repositories were built exactly as cloned. `git status` shows no modified
and no untracked file in any of them; the only build products inside the source tree are the Reftek helper
objects (`src/base/seedlink/plugins/reftek_libs/{reftek,rtp,util}/*.o, *.a`), which seedlink's own
`.gitignore` lists (lines 55-56).

| repository | tag | commit |
|---|---|---|
| SeisComP/seiscomp | 7.4.0 | `ab07c61fe4f4c0853bc636ed9a61b8c3eca44ac1` |
| SeisComP/common | 7.4.0 | `789503ef25a2b318519d54a9702ed8264f30ef61` |
| SeisComP/main | 7.4.0 | `ec3f026e1e001f76e86f16533f97d5e6cec4c84d` |
| SeisComP/seedlink | 7.4.0 | `a56406e395994ced8872d0cec7ebc49bc8e3784f` |
| SeisComP/extras | 7.4.0 (= 7.3.0, 7.3.1) | `ced008a516b3273a1ccbb015d1cd597823b0f2ff` |
| swiss-seismological-service/scrtdd | v2.0.10 | `f801f859defac0634341480b98eb85021d5302ac` |
| swiss-seismological-service/scdlrtpicker | v1.1.1 | `409b18fd6d933cd4ebd5354a0ff74998b6cb6113` |

Two upstream build problems were solved by **configuration only** (both are in the script, with comments;
details and error texts in `docs/install_notes/01_seiscomp.md`):

1. SeedLink Reftek plugin failed to link (`libreftek.a(steim.o): relocation R_X86_64_32S ... can not be
   used when making a PIE object; recompile with -fPIE`): its hand-written Makefiles hard-code `CC = gcc`,
   which on Server A is the system Red Hat GCC 14 (non-PIE), while the rest is built and linked by conda
   GCC 13 (PIE). Fix: `make CC=$CC` on the top-level make command line, which overrides the Makefile value
   in all sub-makes.
2. scrtdd's libhdd unit tests were silently left out on the first configure of a fresh build tree
   (`HDD_TESTS:BOOL=OFF`, CMake policy CMP0077 warning). Fix: `-DHDD_TESTS=ON`.


## Step C2: Gwangyang benchmark inputs (install/04_gwangyang_inputs.sh), 2026-10-17

**No source patches.** This step only reads upstream code and documents (scrtdd tag v2.0.10, pyrtdd
master) and the read-only reference copy; it writes new files under `data/gwangyang_11ev/` with its
own helpers in `data/gwangyang_11ev/tools/`. No upstream or reference file was modified.


## Step T: unit tests and DL-picker smoke test (install/05_tests.sh), 2026-10-17

**No source patches.** Upstream code was only built (step A) and run here. The only files added to an
upstream source tree are the ones scrtdd's own test instructions create: its NonLinLoc test grids
(`libs/hdd/test/data/nll/iasp91_*/{model,time}/`, 3.5 GB, made by scrtdd's `generate.ch`). After all
tests, `git status` in `src/extras/scrtdd` shows exactly these 20 untracked folders and no modified
file, and it is clean in the seiscomp, common, main, seedlink, extras and scdlrtpicker repositories.
Three run-time problems were solved by configuration (details in `docs/install_notes/05_tests.md`):

1. SeisComP's default configuration (`etc/defaults/global.cfg`) says `core.plugins = dbmysql`, but this
   build has only the SQLite driver, so `fdsnxml2inv` and `bindings2cfg` stopped with
   `[error] Did not find plugin dbmysql`. Fix: `--core.plugins=dbsqlite3` on their command lines
   (scautopick is run with `--config-file`, which skips the default configuration).
2. Without station bindings scautopick runs a detector on every stream, horizontals included. Fix: key
   files + `bindings2cfg` (one binding per station, `detecStream` = the station's sensor code).
3. The official ONNX Runtime 1.31.0 build contains Microsoft's 1DS usage telemetry: each scautopick run
   with the plugin queued an event in `$HOME/.cache/Microsoft/DeveloperTools/.onnxruntime/onnxruntime.db`
   (here `runs/seiscomp_home/...`, because HOME is redirected). Fix: `ORT_DISABLE_TELEMETRY=1` in the
   environment of every SeisComP command of `install/05_tests.sh` (verified: database untouched with it,
   one more event without it; picks identical).
