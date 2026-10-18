#!/usr/bin/env bash
# 01_build_seiscomp.sh -- compile SeisComP 7.4.0 (no graphical programs) together with
#                         scrtdd v2.0.10 (double-difference relocator, "rtDD") and
#                         scdlrtpicker v1.1.1 (deep-learning P/S picker plugin) on Server A.
#
# In plain words:
#   SeisComP is published as several git repositories (the frame + libraries + programs) that
#   are put together into one source tree and compiled with CMake. scrtdd and scdlrtpicker are
#   "extras": they are dropped into src/extras/ of that tree and compiled with it.
#   scdlrtpicker runs .onnx neural-network models through ONNX Runtime (Microsoft's model
#   runner); we use Microsoft's official pre-compiled CPU release, checked by its SHA-256.
#   Everything (compiler, CMake, Boost, libxml2, Python, ...) comes from the conda env
#   'seiscomp' because Server A has no system C++ compiler, CMake or git, and we have no sudo
#   (it does have a system C compiler, Red Hat GCC 14 -- see the 'build' stage for why that matters).
#
# Stages (default: all, in this order; '--stage NAME' runs only that stage, may be repeated):
#   clone      git clone the seven repositories at fixed release tags; print each commit hash
#   ort        download ONNX Runtime, verify its SHA-256, extract it next to the download
#   configure  run cmake (all options are in CMAKE_OPTS below)
#   build      compile: nice -n 10 make -j16 CC=<conda C compiler> (resumable: make only redoes
#              what is missing)
#   install    make install into SEISCOMP_ROOT
#   ortlink    put the ONNX Runtime release under SEISCOMP_ROOT/lib and symlink
#              libonnxruntime.so.1 there (as the scdlrtpicker README says), so every
#              SeisComP program that loads the plugin finds the exact same ORT release
#
# Usage:
#   bash 01_build_seiscomp.sh                           # DRY RUN: only print every command
#   bash 01_build_seiscomp.sh --apply                   # really do all stages
#   bash 01_build_seiscomp.sh --apply --stage build     # one stage only (e.g. to resume)
#
# Logs: --apply appends to logs/01_build_seiscomp_<YYYYMMDD>.log; a dry run overwrites
#       logs/01_build_seiscomp_dryrun.log.
# Source patches: none are applied by this script (see docs/patches.md).
# Afterwards: bash install/01_check_seiscomp.sh --apply   (smoke checks from a fresh login shell)
# Then use:   source install/env_seiscomp.sh

set -euo pipefail

# ------------------------------------------------------------------------------------------
# Parameters
# ------------------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
CONDA_BASE=/home/msseo/miniforge3
ENV_PREFIX=$CONDA_BASE/envs/seiscomp          # conda env with compiler + all libraries

SC_GIT=https://github.com/SeisComP           # official SeisComP repositories
SED_GIT=https://github.com/swiss-seismological-service
SC_TAG=7.4.0                                  # SeisComP release (2026-09-04)
SCRTDD_TAG=v2.0.10                            # scrtdd release (2026-09-12)
DLRT_TAG=v1.1.1                               # scdlrtpicker release (2026-10-11)

ORT_VER=1.31.0                                # newest stable ONNX Runtime (2026-10-09)
ORT_NAME=onnxruntime-linux-x64-$ORT_VER
ORT_URL=https://github.com/microsoft/onnxruntime/releases/download/v$ORT_VER/$ORT_NAME.tgz
# SHA-256 published by GitHub for this release asset (API field "digest"):
ORT_SHA256=cc5c72baf5ae5c8238a6841f0897227be2d02826b9cf98eaf02fdefaeeb03a57

# NOTE: do not rename these to SRC/BUILD: 'conda activate' of the compiler package exports
# BUILD=x86_64-conda-linux-gnu (and HOST, AR, LD, ...), which silently overwrote a variable
# called BUILD in the first attempt and sent the cmake build tree to ./x86_64-conda-linux-gnu.
SC_SRC_DIR=$PROJECT/software/src/seiscomp     # SeisComP source tree
SC_BUILD_DIR=$PROJECT/software/build/seiscomp # CMake build tree (out of source)
SEISCOMP_ROOT=$PROJECT/software/seiscomp      # install prefix = SEISCOMP_ROOT
ORT_DL_DIR=$PROJECT/software/onnxruntime      # ONNX Runtime download + extracted copy for the build
ORT_ROOT=$ORT_DL_DIR/$ORT_NAME                # = ONNXRUNTIME_ROOT given to cmake

JOBS=16                                       # Server A is shared: at most 16 parallel compile jobs
NICE=10                                       # ... and at lower CPU priority

# CMake options. Why each one:
CMAKE_OPTS=(
  -G "Unix Makefiles"
  -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_INSTALL_PREFIX="$SEISCOMP_ROOT"
  -DCMAKE_PREFIX_PATH="$ENV_PREFIX"           # find Boost, libxml2, OpenSSL, ... in the conda env first
  # conda's lib dir is not on LD_LIBRARY_PATH: bake both library dirs into every installed
  # program/library (RPATH), so they run from a fresh shell without extra settings
  -DCMAKE_INSTALL_RPATH="$SEISCOMP_ROOT/lib;$ENV_PREFIX/lib"
  -DSC_GLOBAL_GUI=OFF                         # no Qt on Server A, and no GUI needed
  -DSC_GLOBAL_UNITTESTS=ON                    # unit tests of SeisComP and scrtdd (run in step T)
  # scrtdd turns its libhdd tests on with SET(HDD_TESTS ON) just before OPTION(HDD_TESTS .. OFF);
  # under CMake's old policy CMP0077 the first configure of a fresh build tree clears that
  # SET, caches OFF and silently skips the tests (seen here: HDD_TESTS:BOOL=OFF). Saying it
  # explicitly makes one configure run enough:
  -DHDD_TESTS=ON
  -DSC_GLOBAL_PYTHON_WRAPPER=ON               # 'import seiscomp' in Python
  -DSC_GLOBAL_PYTHON_WRAPPER_NUMPY=ON         # ... with numpy arrays (numpy 1.26 in the env)
  -DSC_TRUNK_DB_MYSQL=OFF                     # database back-ends: SQLite only (no server needed)
  -DSC_TRUNK_DB_POSTGRESQL=OFF
  -DSC_TRUNK_DB_SQLITE3=ON
  -DSC_DOC_GENERATE=OFF                       # documentation is read online
  -DSC_DLRTPICKER=ON                          # build the scdlrtpicker plugin (off by default)
  -DONNXRUNTIME_ROOT="$ORT_ROOT"
  # Server A also has a system Python 3.12 (/usr/include/python3.12). SeisComP looks for Python
  # with three different CMake modules (FindPython, FindPythonInterp, FindPythonLibs), so all
  # three are pinned to the conda interpreter, its headers and its library:
  -DPython_EXECUTABLE="$ENV_PREFIX/bin/python3.12"
  -DPYTHON_EXECUTABLE="$ENV_PREFIX/bin/python3.12"
  -DPYTHON_INCLUDE_DIR="$ENV_PREFIX/include/python3.12"
  -DPYTHON_LIBRARY="$ENV_PREFIX/lib/libpython3.12.so"
)
# Not needed: libbson. The SeisComP README still lists libbson-dev, but SeisComP removed its
# BSON support (CHANGELOG "Remove BSON support") and no CMake file of 7.4.0 looks for it.

ALL_STAGES=(clone ort configure build install ortlink)

# ------------------------------------------------------------------------------------------
# Command line
# ------------------------------------------------------------------------------------------
APPLY=0
STAGES=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --apply) APPLY=1 ;;
    --stage) shift; STAGES+=("${1:?--stage needs a name}") ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
[[ ${#STAGES[@]} -eq 0 ]] && STAGES=("${ALL_STAGES[@]}")
for s in "${STAGES[@]}"; do
  [[ " ${ALL_STAGES[*]} " == *" $s "* ]] || { echo "unknown stage: $s" >&2; exit 2; }
done

mkdir -p "$PROJECT/logs"
if [[ $APPLY -eq 1 ]]; then
  LOG=$PROJECT/logs/01_build_seiscomp_$(date +%Y%m%d).log
else
  LOG=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install/logs/dry_01_build_seiscomp.log
  : > "$LOG"
fi
exec > >(tee -a "$LOG") 2>&1     # everything below goes to the screen AND the log

run() {                          # print a command (shell-quoted, copy-pasteable); execute it only with --apply
  echo "+ $(printf '%q ' "$@")"
  if [[ $APPLY -eq 1 ]]; then "$@"; fi
}

echo "=================================================================================="
echo "== 01_build_seiscomp.sh  $(date '+%F %T %Z')  host=$(hostname -s)  APPLY=$APPLY"
echo "== stages: ${STAGES[*]}"
echo "=================================================================================="

# The conda activation scripts read unset variables, so relax 'set -u' around them.
echo "+ source $CONDA_BASE/etc/profile.d/conda.sh; conda activate $ENV_PREFIX"
set +u
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "$ENV_PREFIX"
set -u
echo "   CONDA_PREFIX=$CONDA_PREFIX"
echo "   CC=$CC"
echo "   CXX=$CXX ($($CXX -dumpfullversion))"
echo "   cmake: $(cmake --version | head -1)   git: $(git --version)"
# Guard: conda activation must not have changed any of our directory variables (see NOTE above).
for v in SC_SRC_DIR SC_BUILD_DIR SEISCOMP_ROOT ORT_DL_DIR ORT_ROOT; do
  [[ ${!v} == "$PROJECT"/* ]] || { echo "!! $v=${!v} is not inside $PROJECT -- stop"; exit 1; }
done

# ------------------------------------------------------------------------------------------
stage_clone() {
  # Shallow clones (--depth 1) of exactly the release tags: smaller and unambiguous.
  clone_one() {  # clone_one URL TAG DEST
    local url=$1 tag=$2 dest=$3
    if [[ -d $dest/.git ]]; then
      echo "   $dest already cloned -- skipping"
    else
      run git clone --depth 1 --branch "$tag" "$url" "$dest"
    fi
    if [[ $APPLY -eq 1 ]]; then
      echo "   COMMIT $(git -C "$dest" rev-parse HEAD)  tag=$tag  $url"
    fi
  }
  run mkdir -p "$(dirname "$SC_SRC_DIR")"
  clone_one "$SC_GIT/seiscomp.git" "$SC_TAG"     "$SC_SRC_DIR"                     # build system + framework
  clone_one "$SC_GIT/common.git"   "$SC_TAG"     "$SC_SRC_DIR/src/base/common"   # libraries
  clone_one "$SC_GIT/main.git"     "$SC_TAG"     "$SC_SRC_DIR/src/base/main"     # scautopick, scautoloc, ...
  clone_one "$SC_GIT/seedlink.git" "$SC_TAG"     "$SC_SRC_DIR/src/base/seedlink" # SeedLink server + plugins
  # 'extras' holds msrtsimul (real-time playback of miniSEED files, needed to test scautopick
  # and scrtdd in real-time mode), scgitinit, slmon, tab2inv. Pure Python, nothing to compile.
  # It is not in 'main' (checked: no msrtsimul in common/main/seedlink 7.4.0).
  clone_one "$SC_GIT/extras.git"   "$SC_TAG"     "$SC_SRC_DIR/src/base/extras"   # msrtsimul, ...
  clone_one "$SED_GIT/scrtdd.git"       "$SCRTDD_TAG" "$SC_SRC_DIR/src/extras/scrtdd"
  clone_one "$SED_GIT/scdlrtpicker.git" "$DLRT_TAG"   "$SC_SRC_DIR/src/extras/scdlrtpicker"
}

stage_ort() {
  run mkdir -p "$ORT_DL_DIR"
  if [[ -f $ORT_DL_DIR/$ORT_NAME.tgz ]]; then
    echo "   $ORT_DL_DIR/$ORT_NAME.tgz already downloaded -- skipping download"
  else
    run curl -L --fail --silent --show-error -o "$ORT_DL_DIR/$ORT_NAME.tgz" "$ORT_URL"
  fi
  # Refuse to continue with a file that is not byte-identical to Microsoft's release.
  echo "+ sha256sum $ORT_DL_DIR/$ORT_NAME.tgz   (expect $ORT_SHA256)"
  if [[ $APPLY -eq 1 ]]; then
    local got
    got=$(sha256sum "$ORT_DL_DIR/$ORT_NAME.tgz" | cut -d' ' -f1)
    echo "   sha256=$got"
    [[ $got == "$ORT_SHA256" ]] || { echo "!! SHA-256 MISMATCH -- stop"; exit 1; }
  fi
  if [[ -d $ORT_ROOT ]]; then
    echo "   $ORT_ROOT already extracted -- skipping"
  else
    run tar -xzf "$ORT_DL_DIR/$ORT_NAME.tgz" -C "$ORT_DL_DIR"
  fi
}

stage_configure() {
  run mkdir -p "$SC_BUILD_DIR"
  run cmake -S "$SC_SRC_DIR" -B "$SC_BUILD_DIR" "${CMAKE_OPTS[@]}"
}

stage_build() {
  # The SeedLink Reftek plugin builds three small helper libraries (reftek_libs/{reftek,rtp,util})
  # with a hand-written Makefile that hard-codes 'CC = gcc'. On Server A plain 'gcc' is the system
  # compiler (Red Hat GCC 14, makes non-PIE code) while everything else is compiled and linked by
  # the conda GCC 13, which links PIE programs by default. The first attempt therefore failed with
  #   libreftek.a(steim.o): relocation R_X86_64_32S ... can not be used when making a PIE object
  # (on Ubuntu both are the same compiler, so upstream never sees this). A variable given on the
  # make command line overrides the Makefile's value in every sub-make (GNU make passes it down
  # through MAKEFLAGS), so CC="$CC" makes these libraries use the conda compiler as well.
  # The 'clean' removes objects left by a build with the wrong compiler (no-op on a fresh tree);
  # make then rebuilds the three libraries (a few seconds).
  local d
  for d in reftek rtp util; do
    run make -C "$SC_SRC_DIR/src/base/seedlink/plugins/reftek_libs/$d" clean
  done
  run nice -n "$NICE" make -C "$SC_BUILD_DIR" -j"$JOBS" CC="$CC"
}

stage_install() {
  run nice -n "$NICE" make -C "$SC_BUILD_DIR" install
}

stage_ortlink() {
  # Upstream scdlrtpicker sets no RPATH for libonnxruntime.so.1 and relies on SEISCOMP_ROOT/lib
  # being on the library path of every SeisComP program ('seiscomp print env'). A copy of the
  # release there + a symlink makes the plugin loadable everywhere, and keeps the version
  # identical to the one compiled against (another release fails with "version 'VERS_x.y.z'
  # not found"). In this build the plugin also carries our install RPATH (SEISCOMP_ROOT/lib),
  # so the symlink is found even without LD_LIBRARY_PATH.
  if [[ -d $SEISCOMP_ROOT/lib/$ORT_NAME ]]; then
    echo "   $SEISCOMP_ROOT/lib/$ORT_NAME already present -- skipping extraction"
  else
    run tar -xzf "$ORT_DL_DIR/$ORT_NAME.tgz" -C "$SEISCOMP_ROOT/lib"
  fi
  run ln -sfn "$ORT_NAME/lib/libonnxruntime.so.1" "$SEISCOMP_ROOT/lib/libonnxruntime.so.1"
}

for s in "${STAGES[@]}"; do
  echo
  echo "---------------------------------------- stage: $s   ($(date '+%F %T'))"
  "stage_$s"
done
echo
echo "== finished stages: ${STAGES[*]}  ($(date '+%F %T'))  APPLY=$APPLY"
