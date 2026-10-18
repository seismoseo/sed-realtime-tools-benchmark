#!/usr/bin/env bash
# 09_dlpicker.sh -- step 09: the scdlrtpicker deep-learning picker (scautopick + plugin dlrtpicker,
# P picker DL3C, S picker SDL3C) on all 11 Gwangyang events with 4 models, compared with the
# PhaseNet+ reference picks; cross-checked against SeisBench with the same weights; costed; and fed
# to pyrtdd (catalog-only double difference) to see whether the DL picks are good enough for DD.
#
# Built on the step-T recipe (install/05_tests.sh stage smoke, install/05_smoke_bindings.py,
# install/05_compare_picks.py; docs/install_notes/05_tests.md section 4). Differences from step T:
#   - all 11 events, and all 54 stations are bound (the step-Prep inventory has metadata for all);
#   - the inventory is data/gwangyang_11ev/inputs/inventory_sc.xml (step Prep), not a fresh
#     fdsnxml2inv of the old stations.xml;
#   - HOME and SEISCOMP_LOCAL_CONFIG point into THIS run folder (project rule 1);
#   - a 5th variant: phasenet_instance with the README's "fast picks" P settings.
#
# Stages (default order; 'all' runs them all):
#   prep      sort the 11 playback files (scmssort -u -E); station bindings for every station
#             (detecStream = the station's one sensor, HH/HG/EL; 09_bindings.py + bindings2cfg);
#             one scautopick config per variant; a JSON dump of every setting each variant uses
#             (scautopick --dump-config/--dump-settings + the plugin's own settings + model metadata).
#   pick      scautopick --offline --playback on every event x variant, /usr/bin/time -v per run,
#             plus one start-up run per variant on a 10-s, 1-station probe file (no trigger can occur
#             there, so it measures the fixed start-up cost only).
#   compare   09_compare.py: recall / precision / pick-time differences vs PhaseNet+, by sensor,
#             distance and magnitude; picks outside the event windows per station-hour; classes of the
#             unmatched picks; CPU cost per station-hour; the best model (rule fixed in 09_compare.py
#             before any result was seen).
#   seisbench 09_seisbench_run.py in env dl-base (READ-ONLY env, python -I, CPU, <= 4 threads):
#             SeisBench classify() with the same weight sets on the same raw streams; it also writes
#             test windows for 09_weights_check.py (env pyrtdd: ONNX vs torch on identical input);
#             09_compare_seisbench.py: plugin vs SeisBench pick times.
#   seisbench1 the SeisBench run again with ONE torch thread, for a like-for-like CPU cost (the plugin runs
#             ONNX Runtime single-threaded); its picks must equal the main run's.
#   seisbench_compare  only 09_compare_seisbench.py (plugin vs SeisBench pick times), with the same
#             arguments as in stage seisbench, on the existing SeisBench picks: seconds, nothing is re-picked.
#             Not part of 'all' (stage seisbench already runs it). Added 2026-10-17 to re-run the comparison
#             after the sign fix (dt = plugin - SeisBench) and the whole-sample fractions.
#   reloc     09_reloc.py (env pyrtdd): rtDD catalogs from the DL picks (every model; the best one is
#             the main result) and from the PhaseNet+ picks (control), pyrtdd catalog-only relocation
#             with the 'hypodd_like' settings, compared in metres with HypoDD dt.ct and dt.cc.
#
# Usage:  bash 09_dlpicker.sh                       # dry run: print every action, change nothing
#         bash 09_dlpicker.sh --apply               # all stages
#         bash 09_dlpicker.sh --apply --stage pick  # one stage: prep | pick | compare | seisbench | seisbench1 |
#                                                   #   seisbench_compare | reloc | all
#         bash 09_dlpicker.sh --apply --stage seisbench_compare   # only the plugin-vs-SeisBench comparison
#
# Everything is written inside the project folder. In --apply mode all output is appended to $LOG.

set -euo pipefail

# --------------------------------------------------------------------------------------------------
# parameters (everything that defines the result is here)
# --------------------------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
RUN=$PROJECT/runs/gwangyang/dlpicker              # this step's run folder
SCRIPTS=$RUN/scripts
CONDA_BASE=/home/msseo/miniforge3
PY_ENV=$CONDA_BASE/envs/pyrtdd                    # python helpers (obspy, pandas, onnx, onnxruntime, pyrtdd)
DLBASE_PY=$CONDA_BASE/envs/dl-base/bin/python     # SeisBench 0.11 + torch; READ-ONLY env, run with -I
ENV_SC=$PROJECT/install/env_seiscomp.sh           # SeisComP environment (step A)
SC_HOME=$RUN/sc_home                              # HOME for every SeisComP program (rule 1)

DATA=$PROJECT/data/gwangyang_11ev
PLAYBACK_DIR=$DATA/inputs/playback                # <kma_id>.mseed, unsorted, 100 Hz counts
INV_SC=$DATA/inputs/inventory_sc.xml              # SeisComP inventory of step Prep (54 stations, 255 streams)
REF_PICKS=$DATA/reference_tables/picks_phasenet_plus.csv
EVENT_IDS="20210720161418 20210827002315 20210827220322 20210828133410 20210828133922 20210828234556
           20260101024947 20260101084800 20260202194119 20260203021535 20260204054406"

MODELS_DIR=$PROJECT/software/src/seiscomp/src/extras/scdlrtpicker/models
MODELS="phasenet_instance phasenet_stead eqtransformer_stead phasenet_original"   # step-T recommendation
FAST_MODEL=phasenet_instance                      # the README "fast picks" P variant is run for this model
FAST_VARIANT=${FAST_MODEL}_fast
VARIANTS="$MODELS $FAST_VARIANT"
SEISBENCH_MODELS="phasenet_instance eqtransformer_stead"   # SeisBench cross-check (task item 2)
SEISBENCH_THREADS=4                               # torch CPU threads (Server A is shared; <= 8 per agent)

P_TOL=0.5                                         # pick matching tolerance P [s]
S_TOL=1.0                                         # pick matching tolerance S [s]
WIN_BEFORE=5                                      # event window = HYPOINVERSE origin - 5 s ...
WIN_AFTER=60                                      # ... to origin + 60 s

LOG=$PROJECT/logs/09_gwangyang_dlpicker_$(date +%Y%m%d).log

# --------------------------------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------------------------------
APPLY=0
STAGE=all
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --stage) STAGE=${2:?--stage needs prep, pick, compare, seisbench, seisbench1, seisbench_compare, reloc or all}; shift 2 ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
case "$STAGE" in prep|pick|compare|seisbench|seisbench1|seisbench_compare|reloc|all) ;; *) echo "bad --stage $STAGE"; exit 2 ;; esac

for d in "$RUN" "$SC_HOME"; do                     # guard: write only inside the project
  case "$d" in "$PROJECT"/*) ;; *) echo "refusing: $d is outside $PROJECT"; exit 2 ;; esac
done

if [[ $APPLY -eq 1 ]]; then
  mkdir -p "$(dirname "$LOG")"
  exec > >(tee -a "$LOG") 2>&1          # keep a full record of what was done
fi
echo "==== 09_dlpicker.sh  $(date '+%Y-%m-%d %H:%M:%S %Z')  host $(hostname -s)  APPLY=$APPLY  STAGE=$STAGE"
trap 'echo "==== 09_dlpicker.sh finished with exit code $? ($(date +%H:%M:%S))"' EXIT

# --------------------------------------------------------------------------------------------------
# helpers: every action is printed; only executed with --apply
# --------------------------------------------------------------------------------------------------
run() {                       # run a command
  echo "+ $*"
  if [[ $APPLY -eq 1 ]]; then "$@"; fi
}
write_file() {                # write stdin to a file; the content is shown in full only in dry-run
  local file=$1 content
  content=$(cat)
  echo "+ write $file ($(printf '%s\n' "$content" | wc -l) lines)"
  if [[ $APPLY -eq 1 ]]; then printf '%s\n' "$content" > "$file"; else printf '%s\n' "$content" | sed 's/^/    | /'; fi
}
sc() {                        # run a command in the SeisComP environment, in a subshell
  # HOME and SEISCOMP_LOCAL_CONFIG point into this run folder, so no SeisComP program writes to the
  # real home directory (rule 1). SC_LOCAL may be set by the caller to give a run its own folder.
  # ORT_DISABLE_TELEMETRY=1: the official ONNX Runtime 1.31.0 used by the plugin contains Microsoft's
  # usage telemetry (step T, "Problems" item 5); env_seiscomp.sh sets it too, this is belt and braces.
  ( export HOME=$SC_HOME
    export SEISCOMP_LOCAL_CONFIG=${SC_LOCAL:-$SC_HOME/.seiscomp}
    export ORT_DISABLE_TELEMETRY=1
    source "$ENV_SC"
    "$@" )
}
py() {                        # python helper in env pyrtdd (subshell); -I: ignore user site and cwd
  ( set +u; source "$CONDA_BASE/etc/profile.d/conda.sh"; conda activate "$PY_ENV"; set -u
    nice -n 10 python -I "$@" )
}
model_of() {                  # variant name -> ONNX model name
  case "$1" in *_fast) echo "${1%_fast}" ;; *) echo "$1" ;; esac
}
model_half_window() {         # half the model window in whole seconds (PhaseNet 30.01 s -> 15, EQTransformer 60 s -> 30)
  py -c 'import sys, onnx
m = {p.key: p.value for p in onnx.load(sys.argv[1], load_external_data=False).metadata_props}
print(round(int(m["seiscomp.picker.windowLength"]) / float(m["seiscomp.picker.sampleRate"]) / 2))' "$1"
}

# --------------------------------------------------------------------------------------------------
# stage prep
# --------------------------------------------------------------------------------------------------
write_scautopick_cfg() {      # $1 = config file, $2 = variant, $3 = model file, $4 = half the model window [s]
  local cfg=$1 variant=$2 model=$3 half=$4 pblock
  if [[ $variant == *_fast ]]; then
    pblock="# P: README \"Fast picks\": windows ending 1, 2, ..., 8 s after the detector trigger; the first one
# with a P peak over minConfidence is accepted (strategy fast). Only these 4 P settings differ from the
# 'reliable' variant $(model_of "$variant"): detector, dead time ($half s) and S picker are unchanged, so both
# variants start their P pickers on the same triggers and only the P window placement differs.
module.trunk.global.picker.DL3C.minLatency = 1
module.trunk.global.picker.DL3C.maxLatency = 8
module.trunk.global.picker.DL3C.maxAttempts = 8
module.trunk.global.picker.DL3C.strategy = fast"
  else
    pblock="# P: README \"Reliable picks\": one window centred on the detector trigger
# (maxLatency left unset = half the model window = $half s for this model)
module.trunk.global.picker.DL3C.maxAttempts = 1"
  fi
  write_file "$cfg" <<EOF
# scautopick.cfg of step 09 (runs/gwangyang/dlpicker/scripts/09_dlpicker.sh), variant $variant,
# model $(basename "$model"). Read with --config-file: no other configuration file is used.
# Same settings as the step-T smoke test (docs/install_notes/05_tests.md section 4) unless stated.

# --- the deep-learning picker plugin and the pickers it provides (scdlrtpicker README) ---
plugins = dlrtpicker
picker = DL3C
spicker = SDL3C

# --- model: README "Configure", testing form (same settings for every station) ---
module.trunk.global.picker.DL3C.model = $model
module.trunk.global.spicker.SDL3C.model = $model
$pblock
# S: README "Reliable picks", sweep of the S-P range. Stations are 7-99 km away (S-P about 1-12 s):
# windows end $half, $((half + 5)), $((half + 10)), $((half + 15)) s after the P pick, i.e. centred
# on S-P = 0, 5, 10, 15 s; the most confident one is kept.
module.trunk.global.spicker.SDL3C.minLatency = $half
module.trunk.global.spicker.SDL3C.maxLatency = $((half + 15))
module.trunk.global.spicker.SDL3C.maxAttempts = 4
module.trunk.global.spicker.SDL3C.strategy = best
# minConfidence: plugin defaults (P 0.4, S 0.3), not set here (task: plugin defaults)

# --- STA/LTA detector: README "scautopick: The STA/LTA detector" (permissive; the model decides) ---
filter = "RMHP(10)->ITAPER(30)->BW_BP(4,5,20)->STALTA(1,30)"
timeCorrection = 0
thresholds.triggerOn = 1.8
thresholds.triggerOff = 1.0
killPendingSPickers = false

# --- dead time: README "scautopick: Dead time" rules of thumb ---
thresholds.deadTime = $half            # = the reliable P window's maxLatency ($half s)
thresholds.minAmplOffset = 1.8      # = thresholds.triggerOn
thresholds.amplMaxTimeWindow = 5    # "comfortably below deadTime" (default 10 s)

# --- scautopick defaults (etc/defaults/scautopick.cfg), repeated because --config-file skips them ---
ringBufferSize = 300
leadTime = 60
initTime = 60
thresholds.maxGapLength = 4.5
amplitudes = MLv, mb, mB

# --- output: the confidence of S picks is only available as an extra 'SNR' comment ---
extraPickComments = true
EOF
}

scautopick_args() {           # $1 = variant, $2 = input file: the common scautopick command line
  echo "--config-file $RUN/config/scautopick_$1.cfg --offline --playback --ep -f" \
       "--inventory-db file://$INV_SC --config-db file://$RUN/config/bindings_config.xml -I file://$2"
}

stage_prep() {
  echo "== stage prep: sorted playback files, station bindings, scautopick configs, settings dumps"
  run mkdir -p "$RUN/input" "$RUN/config/key" "$RUN/output" "$RUN/settings" "$SC_HOME"

  # 1. records sorted by end time, duplicates removed (scmssort -u -E), as SeisComP recommends before
  #    any playback: the picker expects the records of all streams in time order.
  local ev
  for ev in $EVENT_IDS; do
    run sc scmssort -u -E -v -o "$RUN/input/${ev}_sorted.mseed" "$PLAYBACK_DIR/$ev.mseed"
  done

  # 2. station bindings for every station with data: detect on the vertical channel of the station's
  #    one sensor; the 3-component pickers need Z, N, E of that sensor in the inventory for every event
  #    window (checked by 09_bindings.py). Also writes the 10-s probe file for the start-up cost run.
  run py "$SCRIPTS/09_bindings.py" --mseed-dir "$RUN/input" --inventory "$INV_SC" \
      --keydir "$RUN/config/key" --table "$RUN/config/stations_bound.csv" \
      --probe-out "$RUN/input/startup_probe.mseed"
  # core.plugins = dbsqlite3 is in $SEISCOMP_ROOT/etc/global.cfg since step Prep, so bindings2cfg
  # needs no --core.plugins option any more.
  run sc bindings2cfg --key-dir "$RUN/config/key" -o "$RUN/config/bindings_config.xml"

  # 3. one scautopick configuration per variant
  local v m half
  for v in $VARIANTS; do
    m=$(model_of "$v")
    if [[ $APPLY -eq 1 || -f $MODELS_DIR/$m.onnx ]]; then half=$(model_half_window "$MODELS_DIR/$m.onnx"); else half=15; fi
    write_scautopick_cfg "$RUN/config/scautopick_$v.cfg" "$v" "$MODELS_DIR/$m.onnx" "$half"
  done

  # 4. what scautopick actually resolved (module configuration and per-stream settings), and the
  #    plugin's settings (cfg values + the plugin's built-in defaults + the model's metadata) as JSON
  for v in $VARIANTS; do
    echo "+ (SeisComP env) scautopick $(scautopick_args "$v" "$RUN/input/20210827220322_sorted.mseed") --dump-config > $RUN/settings/$v.dump-config.txt"
    echo "+ (SeisComP env) scautopick ... --dump-settings > $RUN/settings/$v.dump-settings.txt"
    if [[ $APPLY -eq 1 ]]; then
      # shellcheck disable=SC2046
      SC_LOCAL=$RUN/settings/seiscomp_user sc scautopick $(scautopick_args "$v" "$RUN/input/20210827220322_sorted.mseed") \
        --dump-config > "$RUN/settings/$v.dump-config.txt" 2>&1
      # shellcheck disable=SC2046
      SC_LOCAL=$RUN/settings/seiscomp_user sc scautopick $(scautopick_args "$v" "$RUN/input/20210827220322_sorted.mseed") \
        --dump-settings > "$RUN/settings/$v.dump-settings.txt" 2>&1
    fi
    run py "$SCRIPTS/09_settings_json.py" --variant "$v" --cfg "$RUN/config/scautopick_$v.cfg" \
        --dump-config "$RUN/settings/$v.dump-config.txt" --dump-settings "$RUN/settings/$v.dump-settings.txt" \
        --bound "$RUN/config/stations_bound.csv" --out "$RUN/settings/scautopick_$v.settings.json"
  done
}

# --------------------------------------------------------------------------------------------------
# stage pick
# --------------------------------------------------------------------------------------------------
pick_one() {                  # $1 = variant, $2 = input file, $3 = output folder
  local v=$1 in=$2 out=$3
  run mkdir -p "$out"
  # offline (no messaging), playback (historic data from a file), --ep (picks and amplitudes as SCML
  # on stdout), --debug (per-attempt confidences in the log). /usr/bin/time -v (not the SeisComP
  # environment's own bin/time) records CPU time, wall time and memory. nice -n 10: Server A is shared.
  echo "+ (SeisComP env, SEISCOMP_LOCAL_CONFIG=$out/seiscomp_user) nice -n 10 /usr/bin/time -v -o $out/time.txt scautopick $(scautopick_args "$v" "$in") --debug > $out/picks.xml 2> $out/scautopick.log"
  if [[ $APPLY -eq 1 ]]; then
    # shellcheck disable=SC2046
    SC_LOCAL=$out/seiscomp_user sc nice -n 10 /usr/bin/time -v -o "$out/time.txt" \
      scautopick $(scautopick_args "$v" "$in") --debug > "$out/picks.xml" 2> "$out/scautopick.log"
    local L=$out/scautopick.log
    printf '   %-26s %-15s %s; CPU %s s; %s [error], %s [warning]; windows DL3C %s SDL3C %s\n' "$v" "$(basename "$out")" \
      "$(grep -E '^Found [0-9]+ picks' "$L" || echo 'no "Found" line')" \
      "$(awk -F': ' '/User time/{u=$2} /System time/{s=$2} END{printf "%.2f", u+s}' "$out/time.txt")" \
      "$(grep -c '\[error\]' "$L" || true)" "$(grep -c '\[warning\]' "$L" || true)" \
      "$(grep -c '\[DL3C/.*attempt' "$L" || true)" "$(grep -c '\[SDL3C/.*attempt' "$L" || true)"
  fi
}

stage_pick() {
  echo "== stage pick: scautopick + dlrtpicker, $(echo $EVENT_IDS | wc -w) events x variants: $VARIANTS"
  local v ev
  for v in $VARIANTS; do
    for ev in $EVENT_IDS; do
      pick_one "$v" "$RUN/input/${ev}_sorted.mseed" "$RUN/output/$v/$ev"
    done
    # start-up cost: same program and configuration on a 10-s file of one station. initTime is 60 s,
    # so no detector can trigger and no model window can run: what is measured is the fixed cost.
    pick_one "$v" "$RUN/input/startup_probe.mseed" "$RUN/output/$v/startup_probe"
  done
  echo "   ~/.seiscomp exists: $([[ -e /home/msseo/.seiscomp ]] && echo YES || echo no);" \
       "telemetry folder in run HOME: $([[ -e $SC_HOME/.cache/Microsoft ]] && echo YES || echo no)"
}

# --------------------------------------------------------------------------------------------------
# stage compare
# --------------------------------------------------------------------------------------------------
stage_compare() {
  echo "== stage compare: DL picks vs PhaseNet+ (P within $P_TOL s, S within $S_TOL s)"
  run mkdir -p "$RUN/analysis"
  run py "$SCRIPTS/09_compare.py" --run-dir "$RUN" --variants $VARIANTS --main-models $MODELS \
      --p-tol "$P_TOL" --s-tol "$S_TOL" --win-before "$WIN_BEFORE" --win-after "$WIN_AFTER" \
      --out-dir "$RUN/analysis"
}

# --------------------------------------------------------------------------------------------------
# stage seisbench
# --------------------------------------------------------------------------------------------------
stage_seisbench() {
  echo "== stage seisbench: SeisBench classify() with the same weights (env dl-base, read-only, CPU)"
  run mkdir -p "$RUN/seisbench/cache"
  # SEISBENCH_CACHE_ROOT: SeisBench downloads the weight files into this project folder, never into
  # ~/.seisbench. OMP/MKL threads and torch.set_num_threads: <= $SEISBENCH_THREADS CPU threads.
  echo "+ (SEISBENCH_CACHE_ROOT=$RUN/seisbench/cache OMP_NUM_THREADS=$SEISBENCH_THREADS CUDA_VISIBLE_DEVICES='') nice -n 10 /usr/bin/time -v -o $RUN/seisbench/time.txt $DLBASE_PY -I $SCRIPTS/09_seisbench_run.py ..."
  if [[ $APPLY -eq 1 ]]; then
    ( export SEISBENCH_CACHE_ROOT=$RUN/seisbench/cache OMP_NUM_THREADS=$SEISBENCH_THREADS \
             MKL_NUM_THREADS=$SEISBENCH_THREADS CUDA_VISIBLE_DEVICES=''
      nice -n 10 /usr/bin/time -v -o "$RUN/seisbench/time.txt" "$DLBASE_PY" -I "$SCRIPTS/09_seisbench_run.py" \
        --sorted-dir "$RUN/input" --bound "$RUN/config/stations_bound.csv" \
        --models $SEISBENCH_MODELS --p-threshold 0.4 --s-threshold 0.3 --threads "$SEISBENCH_THREADS" \
        --ref "$REF_PICKS" --out-dir "$RUN/seisbench" )
  fi
  run py "$SCRIPTS/09_weights_check.py" --npz-dir "$RUN/seisbench" --models-dir "$MODELS_DIR" \
      --models $SEISBENCH_MODELS --out "$RUN/seisbench/weights_check.json"
  compare_seisbench
  echo "   ~/.seisbench untouched: $(stat -c '%y' /home/msseo/.seisbench/config.json)"
}

compare_seisbench() {         # plugin vs SeisBench pick times (used by stages seisbench and seisbench_compare)
  run py "$SCRIPTS/09_compare_seisbench.py" --run-dir "$RUN" --models $SEISBENCH_MODELS \
      --p-tol "$P_TOL" --s-tol "$S_TOL" --win-before "$WIN_BEFORE" --win-after "$WIN_AFTER" \
      --out-dir "$RUN/seisbench"
}

# --------------------------------------------------------------------------------------------------
# stage seisbench_compare: only the plugin-vs-SeisBench comparison, on the existing SeisBench picks
# --------------------------------------------------------------------------------------------------
stage_seisbench_compare() {
  echo "== stage seisbench_compare: 09_compare_seisbench.py only (no SeisBench run, no weights check)"
  local m
  for m in $SEISBENCH_MODELS; do
    [[ -f $RUN/seisbench/${m}_picks.csv ]] || { echo "missing $RUN/seisbench/${m}_picks.csv: run stage seisbench first"; exit 2; }
  done
  compare_seisbench
}

# --------------------------------------------------------------------------------------------------
# stage seisbench1: cost-only repeat of the SeisBench run with ONE torch thread
# --------------------------------------------------------------------------------------------------
stage_seisbench1() {
  # Why: the plugin runs ONNX Runtime single-threaded (onnxmodel.cpp: SetIntraOpNumThreads(1)), while the
  # main SeisBench run used $SEISBENCH_THREADS threads, whose CPU time includes thread synchronisation.
  # For a like-for-like CPU cost, SeisBench is repeated here with 1 thread (picks written to a separate
  # folder; they are only compared with the main run to show they are the same).
  echo "== stage seisbench1: SeisBench classify() again with 1 torch thread (CPU cost only)"
  run mkdir -p "$RUN/seisbench/threads1"
  echo "+ (SEISBENCH_CACHE_ROOT=$RUN/seisbench/cache OMP_NUM_THREADS=1) nice -n 10 /usr/bin/time -v -o $RUN/seisbench/threads1/time.txt $DLBASE_PY -I $SCRIPTS/09_seisbench_run.py ... --threads 1 --out-dir $RUN/seisbench/threads1"
  if [[ $APPLY -eq 1 ]]; then
    ( export SEISBENCH_CACHE_ROOT=$RUN/seisbench/cache OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
      nice -n 10 /usr/bin/time -v -o "$RUN/seisbench/threads1/time.txt" "$DLBASE_PY" -I "$SCRIPTS/09_seisbench_run.py" \
        --sorted-dir "$RUN/input" --bound "$RUN/config/stations_bound.csv" \
        --models $SEISBENCH_MODELS --p-threshold 0.4 --s-threshold 0.3 --threads 1 \
        --ref "$REF_PICKS" --out-dir "$RUN/seisbench/threads1" )
    local m
    for m in $SEISBENCH_MODELS; do
      echo "   $m: picks identical to the $SEISBENCH_THREADS-thread run: $(cmp -s "$RUN/seisbench/$m"_picks.csv "$RUN/seisbench/threads1/$m"_picks.csv && echo yes || echo NO)"
    done
  fi
}

# --------------------------------------------------------------------------------------------------
# stage reloc
# --------------------------------------------------------------------------------------------------
stage_reloc() {
  echo "== stage reloc: pyrtdd catalog-only relocation with the DL picks ('hypodd_like')"
  run mkdir -p "$RUN/reloc"
  run py "$SCRIPTS/09_reloc.py" --run-dir "$RUN" --models $MODELS \
      --best-json "$RUN/analysis/best_model.json" --win-before "$WIN_BEFORE" --win-after "$WIN_AFTER" \
      --out-dir "$RUN/reloc"
}

# --------------------------------------------------------------------------------------------------
case "$STAGE" in
  prep)      stage_prep ;;
  pick)      stage_pick ;;
  compare)   stage_compare ;;
  seisbench) stage_seisbench ;;
  seisbench1) stage_seisbench1 ;;
  seisbench_compare) stage_seisbench_compare ;;
  reloc)     stage_reloc ;;
  all)       stage_prep; stage_pick; stage_compare; stage_seisbench; stage_seisbench1; stage_reloc ;;
esac
