#!/usr/bin/env bash
# 03_install_pyrtdd.sh -- STEP B: install pyrtdd (Python wrapper of the rtDD relocation library) into
# conda env "pyrtdd", then test it.
#
# What pyrtdd is: a pybind11 wrapper around "libhdd", the C++ double-difference engine of scrtdd
# (SeisComP rtDD). It does NOT need SeisComP: pyrtdd carries scrtdd as a git submodule
# (deps/scrtdd) and compiles only the library part of it.
#
# Usage:  bash 03_install_pyrtdd.sh                     # dry run: print every action, change nothing
#         bash 03_install_pyrtdd.sh --apply             # do everything
#         bash 03_install_pyrtdd.sh --apply --only clone   # do one step (clone|install|pytest|example|compare|importcheck)
#
# Everything is written below /home/msseo/works/74.SeisComP_rtDD_DLpicker and into env pyrtdd.

set -euo pipefail

# --- parameters ------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
CONDA_BASE=/home/msseo/miniforge3
ENV_PREFIX=$CONDA_BASE/envs/pyrtdd                  # always address the env by path (see 00_create_conda_envs.sh)
PYRTDD_URL=https://github.com/swiss-seismological-service/pyrtdd.git
PYRTDD_COMMIT=d122c3ae50333839475f0d1134c01aba720153cd   # pyrtdd has no release tags: pin master as of 2026-10-17
SCRTDD_SC_TAG=v2.0.10                               # scrtdd release used for the SeisComP module (other step)
SRC_DIR=$PROJECT/software/src/pyrtdd
INSTALL_DIR=$PROJECT/install                        # this script and its Python helpers
LOG_DIR=$PROJECT/logs
LOG=$LOG_DIR/03_install_pyrtdd_20261017.log
JOBS=16                                             # Server A is shared: at most 16 parallel compile jobs
CONDA_BEFORE=$LOG_DIR/03_conda_list_before_pip_20261017.txt
CONDA_AFTER=$LOG_DIR/03_conda_list_after_pip_20261017.txt
PIP_REPORT=$LOG_DIR/03_pip_dryrun_report_20261017.json
SELFTEST_DIR=$PROJECT/runs/pyrtdd_selftest           # scratch folder for the example relocations
TEST_DATA=$SRC_DIR/package/test/py/data             # the repository's synthetic test catalog + reference result

# --- arguments -------------------------------------------------------------------------------
APPLY=0
ONLY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1 ;;
    --only)  ONLY="$2"; shift ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
  shift
done

mkdir -p "$LOG_DIR"
if [[ $APPLY -eq 1 ]]; then exec > >(tee -a "$LOG") 2>&1; fi   # a dry run only prints, it does not touch the log
echo "=================================================================================="
echo "== 03_install_pyrtdd.sh  $(date '+%Y-%m-%d %H:%M:%S')  APPLY=$APPLY  ONLY=${ONLY:-all}  host=$(hostname -s)"

# run CMD...        : echo the command, execute it only with --apply
run() {
  echo "+ $*"
  if [[ $APPLY -eq 1 ]]; then "$@"; fi
}
# run_in DIR CMD... : same, but inside DIR (sub-shell, so the caller's cwd never changes)
run_in() {
  local dir=$1; shift
  echo "+ (cd $dir && $*)"
  if [[ $APPLY -eq 1 ]]; then (cd "$dir" && "$@"); fi
}
# run_to FILE CMD...: same as run, but the command's standard output goes to FILE
run_to() {
  local out=$1; shift
  echo "+ $* > $out"
  if [[ $APPLY -eq 1 ]]; then "$@" > "$out"; fi
}
want() { [[ -z "$ONLY" || "$ONLY" == "$1" ]]; }

# ~/.bash_profile exports PYTHONPATH=/home/msseo/works/MudPy/src/python: -- a directory that does not
# exist plus an empty entry (= "current directory"). Neither should influence the build or the tests.
unset PYTHONPATH

# Activate env pyrtdd. conda's activation hooks (compiler wrappers) read unset variables,
# so "set -u" is switched off while they run.
set +u
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "$ENV_PREFIX"
set -u
echo "== env: $CONDA_PREFIX   python=$(python --version 2>&1)   CXX=${CXX:-unset}"

# --- step 1: clone ---------------------------------------------------------------------------
# --recursive also fetches deps/scrtdd (the C++ library source) and any submodules inside it.
# Checking out the pinned commit makes a later re-run build exactly the same code.
if want clone; then
  echo "== step clone"
  if [[ -d "$SRC_DIR/.git" ]]; then
    echo "   $SRC_DIR already exists -- not cloning again (only re-checking the pinned commit)"
  else
    run git clone --recursive "$PYRTDD_URL" "$SRC_DIR"
  fi
  run git -C "$SRC_DIR" checkout --detach "$PYRTDD_COMMIT"
  run git -C "$SRC_DIR" submodule update --init --recursive
  # Record exactly what was built: pyrtdd commit, submodule commit(s), and which scrtdd release
  # tag the submodule commit corresponds to (git describe; "vX.Y.Z-N-gHASH" = N commits after vX.Y.Z).
  run git -C "$SRC_DIR" log -1 --format='pyrtdd commit %H (%cd) %s' --date=iso
  run git -C "$SRC_DIR" submodule status --recursive
  run git -C "$SRC_DIR/deps/scrtdd" fetch --tags --quiet
  run git -C "$SRC_DIR/deps/scrtdd" describe --tags --always
  run git -C "$SRC_DIR/deps/scrtdd" log -1 --format='scrtdd submodule commit %H (%cd) %s' --date=iso
  # pyrtdd's submodule is scrtdd v2.0.9, while the SeisComP module is built from scrtdd $SCRTDD_SC_TAG.
  # Does the relocation library itself (libs/hdd) differ between the two tags?
  echo "+ git -C $SRC_DIR/deps/scrtdd diff --quiet v2.0.9 $SCRTDD_SC_TAG -- libs/hdd"
  if [[ $APPLY -eq 1 ]]; then
    if git -C "$SRC_DIR/deps/scrtdd" diff --quiet v2.0.9 "$SCRTDD_SC_TAG" -- libs/hdd; then
      echo "   libs/hdd is identical in scrtdd v2.0.9 and $SCRTDD_SC_TAG"
    else
      echo "   libs/hdd DIFFERS between scrtdd v2.0.9 and $SCRTDD_SC_TAG:"
      git -C "$SRC_DIR/deps/scrtdd" diff --stat v2.0.9 "$SCRTDD_SC_TAG" -- libs/hdd
    fi
    git -C "$SRC_DIR/deps/scrtdd" diff --stat v2.0.9 "$SCRTDD_SC_TAG"   # what did change (whole repo)
  fi
fi

# --- step 2: install -------------------------------------------------------------------------
# pip builds the C++ code (libhdd + the pybind11 module hdd_ext) through scikit-build -> CMake -> Ninja
# and installs the result into env pyrtdd's site-packages.
#  --no-build-isolation : build with the conda tool chain already in the env (GCC 13.4, CMake 3.31,
#                         pybind11 3.1, scikit-build 0.19) instead of letting pip download its own copies
#  .[obspy,test]        : also declare the optional extras (obspy and pytest); both are already
#                         provided by conda, so pip must not install anything for them
#  CMAKE_BUILD_PARALLEL_LEVEL / nice : at most $JOBS compile jobs at low priority (shared server)
# scikit-build always builds inside the source tree, in software/src/pyrtdd/_skbuild/.
if want install; then
  echo "== step install"
  run_to "$CONDA_BEFORE" conda list -p "$ENV_PREFIX"
  # Ask pip first what it WOULD install (no changes). Anything other than pyrtdd itself would mean
  # pip wants to replace a conda package (numpy, obspy, pytest, ...): stop in that case.
  run_in "$SRC_DIR" pip install --dry-run --no-build-isolation --report "$PIP_REPORT" '.[obspy,test]'
  run python "$INSTALL_DIR/03_check_pip_report.py" "$PIP_REPORT"
  run_in "$SRC_DIR" env CMAKE_BUILD_PARALLEL_LEVEL=$JOBS nice -n 10 \
      pip install -v --no-build-isolation '.[obspy,test]'
  run_to "$CONDA_AFTER" conda list -p "$ENV_PREFIX"
  # Expected difference: one new line "pyrtdd 0.0.1 pypi_0 pypi" and nothing else.
  echo "+ diff $CONDA_BEFORE $CONDA_AFTER"
  if [[ $APPLY -eq 1 ]]; then diff "$CONDA_BEFORE" "$CONDA_AFTER" || true; fi
  # pip check: are all installed packages' requirements satisfied? (reported, not fatal)
  if ! run pip check; then echo "!! pip check reported problems (listed above)"; fi
fi

# --- step 3: pytest --------------------------------------------------------------------------
# The repository's own test suite (package/test/py: libhdd bindings, obspy catalog conversion,
# obspy waveform proxies). Run from the repo root as the README says. First print which pyrtdd
# Python imports: it must be the installed copy in site-packages, not the source tree.
if want pytest; then
  echo "== step pytest"
  run_in "$SRC_DIR" python -c 'import pyrtdd, pyrtdd.hdd; print("pyrtdd imported from", pyrtdd.__file__)'
  # a failing test must not abort the script before the summary is printed: report the exit code
  if ! run_in "$SRC_DIR" pytest -v; then echo "!! pytest reported failures/errors (see above)"; fi
fi

# --- step 4: example -------------------------------------------------------------------------
# Relocate the repository's small synthetic test catalog (42 events, 8 stations, near 47 N 8.5 E)
# outside the repository, then compare with the reference result the repository ships
# (package/test/py/data/relocated-event.csv). The examples write into the current folder, so each
# run gets its own sub-folder of runs/pyrtdd_selftest:
#   A readme_snippet       : the README "Example workflow" code, default options
#   B examples_relocate_py : examples/relocate.py with only its three TODO catalog paths filled in
#   C test_dd_settings     : the settings of the repository test that checks relocated-event.csv
# A and B use other settings than the reference (see the helper headers), so they are expected to
# differ from it somewhat; C is expected to reproduce it.
if want example; then
  echo "== step example"
  for RUN in readme_snippet examples_relocate_py test_dd_settings; do
    if [[ -e "$SELFTEST_DIR/$RUN" ]]; then
      # never mix old and new results; deleting is left to the user
      echo "!! $SELFTEST_DIR/$RUN already exists -- remove it first:  rm -rf $SELFTEST_DIR/$RUN"
      if [[ $APPLY -eq 1 ]]; then exit 1; fi
    fi
  done
  run mkdir -p "$SELFTEST_DIR/readme_snippet" "$SELFTEST_DIR/examples_relocate_py" "$SELFTEST_DIR/test_dd_settings"
  # A
  run_in "$SELFTEST_DIR/readme_snippet" python "$INSTALL_DIR/03_pyrtdd_readme_example.py" "$TEST_DATA"
  # B: the filled-in copy is kept next to its results; diff shows the only three changed lines
  run_to "$SELFTEST_DIR/examples_relocate_py/relocate_filled.py" sed \
      -e "s#<path/to/station.csv>#$TEST_DATA/starting-station.csv#" \
      -e "s#<path/to/event.csv>#$TEST_DATA/starting-event.csv#" \
      -e "s#<path/to/phase.csv>#$TEST_DATA/starting-phase.csv#" "$SRC_DIR/examples/relocate.py"
  run diff "$SRC_DIR/examples/relocate.py" "$SELFTEST_DIR/examples_relocate_py/relocate_filled.py" || true
  run_in "$SELFTEST_DIR/examples_relocate_py" python relocate_filled.py
  # C
  run_in "$SELFTEST_DIR/test_dd_settings" python "$INSTALL_DIR/03_pyrtdd_test_settings_example.py" "$TEST_DATA"
fi

# --- step 5: compare -------------------------------------------------------------------------
# Event-by-event comparison of runs A, B, C with the reference (metres, milliseconds), plus a
# byte-for-byte check of the three output files against the reference files.
if want compare; then
  echo "== step compare"
  for RUN in readme_snippet examples_relocate_py test_dd_settings; do
    echo "-- comparison $RUN vs reference"
    run python "$INSTALL_DIR/03_compare_relocated_events.py" "$SELFTEST_DIR/$RUN/relocated-event.csv" \
        "$TEST_DATA/relocated-event.csv" "$TEST_DATA/starting-event.csv"
    for F in station event phase; do
      echo "+ cmp -s $SELFTEST_DIR/$RUN/relocated-$F.csv $TEST_DATA/relocated-$F.csv"
      if [[ $APPLY -eq 1 ]]; then
        if cmp -s "$SELFTEST_DIR/$RUN/relocated-$F.csv" "$TEST_DATA/relocated-$F.csv"; then
          echo "   relocated-$F.csv: byte-identical to the reference"
        else
          echo "   relocated-$F.csv: differs from the reference"
        fi
      fi
    done
  done
fi

# --- step 6: importcheck ---------------------------------------------------------------------
# A brand-new shell with an empty environment (env -i: none of this script's variables, no
# PYTHONPATH), in which only "conda activate pyrtdd" is done, started in runs/ (not the repository):
# proves the installed package works by itself, the way a user's notebook would use it.
if want importcheck; then
  echo "== step importcheck"
  FRESH="source $CONDA_BASE/etc/profile.d/conda.sh && conda activate pyrtdd && cd $PROJECT/runs"
  run env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin bash --noprofile --norc -c \
      "$FRESH && python -c 'import pyrtdd, pyrtdd.hdd; from pyrtdd.obspy import catalog, waveform; print(\"import OK\")'"
  run env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin bash --noprofile --norc -c \
      "$FRESH && python $INSTALL_DIR/03_pyrtdd_import_check.py"
fi

echo "== done (APPLY=$APPLY ONLY=${ONLY:-all})"
