# env_seiscomp.sh -- SOURCE this file (do not run it as a program):
#
#     source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
#
# Afterwards the SeisComP 7.4.0 build of this project (with scrtdd and the scdlrtpicker plugin)
# works in the current shell: scautopick, scrtdd, scevent, msrtsimul, ... are on PATH and
# "python -c 'import seiscomp.client'" works.
#
# What it does, and why:
#   1. activates the conda env 'seiscomp': the programs were compiled against its libraries
#      and its Python 3.12 (the Python modules only import in that Python)
#   2. runs 'seiscomp print env', SeisComP's own way of setting PATH, LD_LIBRARY_PATH,
#      PYTHONPATH and MANPATH for an installation, and exports SEISCOMP_ROOT
#   3. every SeisComP program creates and uses a per-user folder, normally ~/.seiscomp
#      (log files, personal settings). SEISCOMP_LOCAL_CONFIG moves it into this project
#      (runs/seiscomp_home/.seiscomp), so nothing is written to the home directory.
#      A value that is already set is kept (e.g. a separate folder per test run).
#   4. switches off ONNX Runtime's usage telemetry. The official onnxruntime-linux-x64-1.31.0
#      release that the scdlrtpicker plugin loads contains Microsoft's "1DS" telemetry client:
#      without ORT_DISABLE_TELEMETRY=1 every scautopick/scolv run that loads a DL model queues a
#      record (OS, process name, CPU model, ORT version, a random device id; no waveforms, picks or
#      file names) under $HOME/.cache/Microsoft/DeveloperTools/.onnxruntime and may upload it to
#      mobile.events.data.microsoft.com. (The conda-forge onnxruntime in env pyrtdd has no such client.)
#
# There is deliberately no 'set -euo pipefail' here: a sourced file runs inside the caller's
# shell, where those options would stay switched on afterwards ('set -e' would even close an
# interactive terminal at the first failing command). If the caller has 'set -u' on, it is
# switched off while conda's activation scripts run (they read unset variables) and restored.

_sc_project=/home/msseo/works/74.SeisComP_rtDD_DLpicker
_sc_conda_base=/home/msseo/miniforge3
_sc_env_prefix=$_sc_conda_base/envs/seiscomp

case $- in *u*) _sc_had_u=1; set +u ;; *) _sc_had_u=0 ;; esac

source "$_sc_conda_base/etc/profile.d/conda.sh"
conda activate "$_sc_env_prefix"

export SEISCOMP_ROOT=$_sc_project/software/seiscomp
eval "$("$SEISCOMP_ROOT/bin/seiscomp" print env)"
export SEISCOMP_ROOT

export SEISCOMP_LOCAL_CONFIG="${SEISCOMP_LOCAL_CONFIG:-$_sc_project/runs/seiscomp_home/.seiscomp}"

export ORT_DISABLE_TELEMETRY=1

if [ "$_sc_had_u" = 1 ]; then set -u; fi
unset _sc_project _sc_conda_base _sc_env_prefix _sc_had_u
