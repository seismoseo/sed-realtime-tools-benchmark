#!/usr/bin/env bash
# v09_verify.sh -- independent, skeptical verification of step 09 (scautopick + scdlrtpicker DL picker on the
# 11 Gwangyang events). Every number is recomputed with this verifier's OWN code from raw files:
#   picks      v09_pick_stats.py (env pyrtdd): recall / precision / |dt| per model and phase from the raw
#              picks.xml and the PhaseNet+ table; windows, tolerances, bindings and denominators.
#   seisbench  v09_seisbench_rerun.py (env dl-base, READ-ONLY env, python -I, CPU, 2 threads): SeisBench
#              PhaseNet 'instance' re-run on 3 events with freshly downloaded weights in this folder's cache;
#              then v09_weights_onnx.py (ONNX vs torch on new windows) and v09_seisbench_compare.py
#              (plugin vs SeisBench pick times) in env pyrtdd.
#   reloc      v09_reloc_check.py (env pyrtdd): metric (a) recomputed from step 09's relocated catalogs, the
#              main DL catalog rebuilt from picks.xml, and pyrtdd re-run on it and on the control.
#   figure     v09_build_waveform_notebook.py (env pyrtdd): builds and executes a notebook with 4 waveform
#              examples (2 events x 2 stations, one HH and one HG) with PhaseNet+ and DL picks; PNG copy.
# Usage: bash v09_verify.sh                     # dry run: print every action, change nothing
#        bash v09_verify.sh --apply             # all stages
#        bash v09_verify.sh --apply --stage picks|seisbench|reloc|figure|all
set -euo pipefail

# ------------------------------------------------------------------------------------------- parameters
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
VDIR=$PROJECT/runs/verify_gwangyang_dl            # this verifier's folder (everything is written here)
SCRIPTS=$VDIR/scripts
CONDA_BASE=/home/msseo/miniforge3
PY_ENV=$CONDA_BASE/envs/pyrtdd
DLBASE_PY=$CONDA_BASE/envs/dl-base/bin/python     # READ-ONLY env: only run, with -I
SB_THREADS=2                                      # Server A is shared (<= 8 processes per agent)
LOG=$PROJECT/logs/09v_verify_gwangyang_dl_$(date +%Y%m%d).log

APPLY=0
STAGE=all
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --stage) STAGE=${2:?}; shift 2 ;;
    *) echo "unknown argument $1"; exit 2 ;;
  esac
done
case "$STAGE" in picks|seisbench|reloc|figure|all) ;; *) echo "bad --stage $STAGE"; exit 2 ;; esac
if [[ $APPLY -eq 1 ]]; then exec > >(tee -a "$LOG") 2>&1; fi
echo "==== v09_verify.sh $(date '+%F %T %Z') host $(hostname -s) APPLY=$APPLY STAGE=$STAGE"
trap 'echo "==== v09_verify.sh exit code $? ($(date +%T))"' EXIT

AP=()
[[ $APPLY -eq 1 ]] && AP=(--apply)

py() {   # env pyrtdd; matplotlib writes its cache inside this folder (MPLCONFIGDIR), never in ~
  ( set +u; source "$CONDA_BASE/etc/profile.d/conda.sh"; conda activate "$PY_ENV"; set -u
    export MPLCONFIGDIR=$VDIR/mpl
    echo "+ (pyrtdd) nice -n 10 python -I $*"
    nice -n 10 python -I "$@" )
}

stage_picks() {
  echo "== stage picks"
  py "$SCRIPTS/v09_pick_stats.py" "${AP[@]}"
}

stage_seisbench() {
  echo "== stage seisbench"
  # SeisBench's cache in THIS folder: weights are downloaded fresh, step 09's cache is not reused or touched.
  echo "+ (dl-base, SEISBENCH_CACHE_ROOT=$VDIR/seisbench/cache, ${SB_THREADS} threads, no GPU) nice -n 10 /usr/bin/time -v -o $VDIR/seisbench/time.txt $DLBASE_PY -I $SCRIPTS/v09_seisbench_rerun.py ${AP[*]}"
  ( export SEISBENCH_CACHE_ROOT=$VDIR/seisbench/cache OMP_NUM_THREADS=$SB_THREADS MKL_NUM_THREADS=$SB_THREADS \
           CUDA_VISIBLE_DEVICES='' MPLCONFIGDIR=$VDIR/mpl
    if [[ $APPLY -eq 1 ]]; then
      nice -n 10 /usr/bin/time -v -o "$VDIR/seisbench/time.txt" "$DLBASE_PY" -I "$SCRIPTS/v09_seisbench_rerun.py" --apply
    else
      "$DLBASE_PY" -I "$SCRIPTS/v09_seisbench_rerun.py"
    fi )
  if [[ $APPLY -eq 1 ]]; then
    py "$SCRIPTS/v09_weights_onnx.py" --apply
    py "$SCRIPTS/v09_seisbench_compare.py" --apply
  else
    echo "+ (pyrtdd) v09_weights_onnx.py --apply and v09_seisbench_compare.py --apply (need the SeisBench output)"
  fi
}

stage_reloc() {
  echo "== stage reloc"
  py "$SCRIPTS/v09_reloc_check.py" "${AP[@]}"
}

stage_figure() {
  echo "== stage figure"
  py "$SCRIPTS/v09_build_waveform_notebook.py" "${AP[@]}"
}

case "$STAGE" in
  picks) stage_picks ;;
  seisbench) stage_seisbench ;;
  reloc) stage_reloc ;;
  figure) stage_figure ;;
  all) stage_picks; stage_seisbench; stage_reloc; stage_figure ;;
esac
echo "   ~/.seiscomp exists: $([[ -e /home/msseo/.seiscomp ]] && echo YES || echo no)"
