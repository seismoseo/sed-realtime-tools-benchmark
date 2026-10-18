#!/usr/bin/env bash
# 00_create_conda_envs.sh -- create the two conda environments used in this project.
#
# Why conda: Server A (Rocky Linux 10.2) has no system g++, cmake or git and we have no sudo,
# so the whole tool chain (GCC 13, CMake 3.31, Boost 1.84, libxml2, ...) comes from conda-forge.
# The versions mirror Ubuntu 24.04, a platform SeisComP 7 officially supports.
#
#   seiscomp : build + runtime environment for SeisComP 7.4.0 (+ scrtdd, scdlrtpicker) and NonLinLoc
#   pyrtdd   : pyrtdd (Python wrapper of the rtDD library, no SeisComP) + the analysis notebooks
#
# Usage:  bash 00_create_conda_envs.sh            # dry run: print what would be done
#         bash 00_create_conda_envs.sh --apply    # really create the environments
#
# Nothing existing is modified: the script refuses to touch an environment that already exists.
# Environments are created by explicit path in ~/miniforge3/envs (next to dl-base, fmf, ...):
# ~/.bashrc sets MAMBA_ROOT_PREFIX=~/.local/share/mamba, so "mamba create -n" would put them
# where "conda activate <name>" cannot find them.

set -euo pipefail

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

CONDA_BASE=/home/msseo/miniforge3
LOG_DIR=/home/msseo/works/74.SeisComP_rtDD_DLpicker/logs

# --- package lists (one place, so every version is visible) ---------------------------------
SEISCOMP_PKGS=(
  python=3.12 numpy=1.26                       # SeisComP Python wrappers are built against these
  gcc_linux-64=13 gxx_linux-64=13              # GCC 13 = Ubuntu 24.04 compiler
  sysroot_linux-64=2.28                        # glibc headers; binaries then run on glibc >= 2.28
  "cmake>=3.28,<4" make git pkg-config         # CMake 4 removed support for old cmake_minimum_required
  flex bison
  libboost-devel=1.84                          # Boost 1.84 (Ubuntu 24.04 has 1.83, but conda-forge's 1.83 needs
                                               #  ICU 73, which no libxml2 build accepts); 1.84 predates the
                                               #  Boost 1.85 removal of deprecated filesystem APIs
  libxml2=2.13                                 # 2.13 still ships its headers (2.14+ moved them to libxml2-devel)
  openssl zlib libbson libsqlite sqlite ncurses
)
PYRTDD_PKGS=(
  python=3.12
  gcc_linux-64=13 gxx_linux-64=13 sysroot_linux-64=2.28   # pyrtdd needs a C++20 compiler
  "cmake>=3.28,<4" ninja "pybind11>=3" "scikit-build>=0.15" setuptools wheel git
  numpy scipy pandas matplotlib obspy pyproj
  pytest ipykernel nbformat nbclient nbconvert
  onnx "onnxruntime=*=*cpu*"                   # CPU build; to inspect / cross-check the scdlrtpicker ONNX models
  tectonic                                     # PDF reports from Markdown via pandoc (added 2026-10-18)
)

run() {
  echo "+ $*"
  if [[ $APPLY -eq 1 ]]; then "$@"; fi
}

source "$CONDA_BASE/etc/profile.d/conda.sh"

for ENV in seiscomp pyrtdd; do
  if [[ -d "$CONDA_BASE/envs/$ENV" ]]; then
    echo "!! environment '$ENV' already exists at $CONDA_BASE/envs/$ENV -- not touching it"
    continue
  fi
  if [[ $ENV == seiscomp ]]; then PKGS=("${SEISCOMP_PKGS[@]}"); else PKGS=("${PYRTDD_PKGS[@]}"); fi
  echo "== creating conda env '$ENV'"
  run mamba create -y -p "$CONDA_BASE/envs/$ENV" -c conda-forge --override-channels "${PKGS[@]}"
done

# Register the pyrtdd environment as a Jupyter kernel so the notebooks in ../notebooks can use it.
if [[ $APPLY -eq 1 ]]; then
  conda activate "$CONDA_BASE/envs/pyrtdd"
  run python -m ipykernel install --user --name pyrtdd --display-name "pyrtdd"
  conda deactivate
else
  echo "+ python -m ipykernel install --user --name pyrtdd --display-name pyrtdd   (in env pyrtdd)"
fi

echo "== done (APPLY=$APPLY)"
