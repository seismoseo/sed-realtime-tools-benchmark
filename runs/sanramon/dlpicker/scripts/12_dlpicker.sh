#!/usr/bin/env bash
# 12_dlpicker.sh -- step 12: the scdlrtpicker deep-learning picker (scautopick + plugin dlrtpicker, P picker
# DL3C, S picker SDL3C) on the 26 San Ramon 2015 test events (NCEDC data, Northern California), compared
# with the NCSS ANALYST picks (unlike Gwangyang, where the reference was PhaseNet+).
#
# Built on step 09's recipe (runs/gwangyang/dlpicker/scripts/09_dlpicker.sh, docs/results/09_gwangyang_dlpicker.md):
# scmssort -u -E, fdsnxml2inv, station bindings via key files + bindings2cfg, the README's permissive STA/LTA
# settings, dead time = half the model window, one P window centred on the trigger, a 4-window S sweep,
# minConfidence at the plugin defaults, per-run HOME/SEISCOMP_LOCAL_CONFIG inside this run folder.
# Differences from step 09:
#   - models: eqtp_ncedc (EQTransformer + first-motion polarity, trained on NCEDC data, 120 s window),
#     phasenet_original (Northern California), phasenet_scedc (Southern California), phasenet_instance (Italy);
#     every window setting is derived from the model's own metadata (window length / sample rate);
#   - long-window model: the README's "Buffer sizing" asks for ringBufferSize and leadTime above the window:
#     ringBufferSize = max(300, 2.5 x window) and leadTime = max(60, 1.5 x window) -> eqtp_ncedc 300 s / 180 s.
#     (leadTime is not used in --playback mode: scautopick picker.cpp:418-424; it is set for a real-time copy.)
#   - San Ramon stations often have several sensors: 12_bindings.py binds ONE 3-component sensor per station
#     (velocity sensors preferred) = binding set 'main'; a second set 'hn' binds the accelerometer at the
#     stations whose main sensor is a velocity sensor (same models, variants <model>_hn);
#   - picking runs go several at a time (xargs -P $NPAR); CPU time per run is unaffected, wall time is.
#
# Stages: prep | pick | compare | seisbench | tables | all
#   prep      sorted playback files (scmssort -u -E); SeisComP inventory (fdsnxml2inv) + scinv check;
#             bindings (12_bindings.py + bindings2cfg, two sets); one scautopick cfg per model;
#             scautopick --dump-config/--dump-settings per variant; settings JSON per variant
#   pick      scautopick on every event x variant (+ one start-up probe run per variant)
#   compare   12_compare.py: recall/precision/dt vs NCSS analyst picks, breakdowns, false picks per
#             station-hour, cost, missed-pick diagnosis, eqtp_ncedc polarity vs analyst first motions
#   seisbench 12_seisbench_run.py (env dl-base, READ-ONLY, python -I, CPU): SeisBench EQTP 'ncedc' on 5 events;
#             12_weights_check.py (ONNX vs torch, joint vs per-component normalisation);
#             12_compare_seisbench.py (plugin vs SeisBench pick times and polarities);
#             12_normalization_test.py (env pyrtdd): the plugin's eqtp_ncedc windows re-run with SeisBench's input
#             normalisation (one std for all 3 components + taper) instead of the plugin's per-component std
#   tables    12_polarity_reference_check.py (do NCSS first motions on inverted channels refer to raw counts?)
#             and 12_tables_md.py > analysis/tables.md (every table of docs/results/12_sanramon_dlpicker.md)
#
# Usage:  bash 12_dlpicker.sh                       # dry run: print every action, change nothing
#         bash 12_dlpicker.sh --apply [--stage X]   # X = prep | pick | compare | seisbench | tables | all
# Everything is written inside the project folder. In --apply mode all output is appended to $LOG.

set -euo pipefail

# --------------------------------------------------------------------------------------------------
# parameters (everything that defines the result is here)
# --------------------------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
RUN=$PROJECT/runs/sanramon/dlpicker
SCRIPTS=$RUN/scripts
CONDA_BASE=/home/msseo/miniforge3
PY_ENV=$CONDA_BASE/envs/pyrtdd                    # python helpers (obspy, pandas, onnx, onnxruntime)
DLBASE_PY=$CONDA_BASE/envs/dl-base/bin/python     # SeisBench 0.11 + torch; READ-ONLY env, run with -I
ENV_SC=$PROJECT/install/env_seiscomp.sh
SC_HOME=$RUN/sc_home

DATA=$PROJECT/data/sanramon_2015
PLAYBACK_DIR=$DATA/inputs/playback                # <event id>.mseed, all stations <= 80 km, origin -120..+120 s
STATIONXML=$DATA/inputs/stations.xml
EVENTS_CSV=$DATA/inputs/dl_subset_events.csv
INV_SC=$RUN/config/inventory_sc.xml               # made here by fdsnxml2inv
EVENT_IDS=$(awk -F, 'NR>1{print $1}' "$EVENTS_CSV" | tr '\n' ' ')

MODELS_DIR=$PROJECT/software/src/seiscomp/src/extras/scdlrtpicker/models
MODELS="eqtp_ncedc phasenet_original phasenet_scedc phasenet_instance"
BINDING_SETS="main hn"                            # variant = <model> (main) or <model>_hn (hn)
NPAR=6                                            # scautopick runs at a time (Server A: 32 cores, shared)
SEISBENCH_MODEL=eqtp_ncedc                        # SeisBench cross-check: one model ...
SEISBENCH_EVENTS="72540765 72542520 72541095 72545170 72537850"   # ... on 5 events (M3.6, 3.23, 2.79, 1.96, 1.14)
SEISBENCH_THREADS=1                               # torch threads (like-for-like CPU with the plugin)

P_TOL=0.5                                         # pick matching tolerance P [s]
S_TOL=1.0                                         # pick matching tolerance S [s]
WIN_BEFORE=5                                      # event window = NCSS origin - 5 s ...
WIN_AFTER=60                                      # ... to + 60 s (as step 09; S at 80 km arrives about +25 s)

LOG=$PROJECT/logs/12_sanramon_dlpicker_$(date +%Y%m%d).log

# --------------------------------------------------------------------------------------------------
APPLY=0
STAGE=all
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --stage) STAGE=${2:?--stage needs prep, pick, compare, seisbench, tables or all}; shift 2 ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
case "$STAGE" in prep|pick|compare|seisbench|tables|all) ;; *) echo "bad --stage $STAGE"; exit 2 ;; esac
for d in "$RUN" "$SC_HOME"; do
  case "$d" in "$PROJECT"/*) ;; *) echo "refusing: $d is outside $PROJECT"; exit 2 ;; esac
done
if [[ $APPLY -eq 1 ]]; then
  mkdir -p "$(dirname "$LOG")"
  exec > >(tee -a "$LOG") 2>&1
fi
echo "==== 12_dlpicker.sh  $(date '+%Y-%m-%d %H:%M:%S %Z')  host $(hostname -s)  APPLY=$APPLY  STAGE=$STAGE"
trap 'echo "==== 12_dlpicker.sh finished with exit code $? ($(date +%H:%M:%S))"' EXIT

run() { echo "+ $*"; if [[ $APPLY -eq 1 ]]; then "$@"; fi; }
write_file() {
  local file=$1 content
  content=$(cat)
  echo "+ write $file ($(printf '%s\n' "$content" | wc -l) lines)"
  if [[ $APPLY -eq 1 ]]; then printf '%s\n' "$content" > "$file"; else printf '%s\n' "$content" | sed 's/^/    | /'; fi
}
sc() {
  ( export HOME=$SC_HOME
    export SEISCOMP_LOCAL_CONFIG=${SC_LOCAL:-$SC_HOME/.seiscomp}
    export ORT_DISABLE_TELEMETRY=1
    source "$ENV_SC"
    "$@" )
}
py() {
  ( set +u; source "$CONDA_BASE/etc/profile.d/conda.sh"; conda activate "$PY_ENV"; set -u
    nice -n 10 python -I "$@" )
}
model_of() { case "$1" in *_hn) echo "${1%_hn}" ;; *) echo "$1" ;; esac; }
set_of()   { case "$1" in *_hn) echo hn ;; *) echo main ;; esac; }
variants() { local m s; for s in $BINDING_SETS; do for m in $MODELS; do
               if [[ $s == main ]]; then echo "$m"; else echo "${m}_$s"; fi; done; done; }
model_window_s() {            # model window in seconds from its metadata
  py -c 'import sys, onnx
m = {p.key: p.value for p in onnx.load(sys.argv[1], load_external_data=False).metadata_props}
print(int(m["seiscomp.picker.windowLength"]) / float(m["seiscomp.picker.sampleRate"]))' "$1"
}

# --------------------------------------------------------------------------------------------------
write_scautopick_cfg() {      # $1 cfg file, $2 model, $3 model file, $4 window [s]
  local cfg=$1 model=$2 file=$3 W=$4 half rb lead
  half=$(python3 -c "print(round($W/2))")
  rb=$(python3 -c "print(max(300, round(2.5*$W)))")
  lead=$(python3 -c "print(max(60, round(1.5*$W)))")
  write_file "$cfg" <<EOF
# scautopick.cfg of step 12 (runs/sanramon/dlpicker/scripts/12_dlpicker.sh), model $model
# ($(basename "$file"), window $W s from its metadata). Read with --config-file: no other configuration file is
# used. Same settings as step 09 (docs/results/09_gwangyang_dlpicker.md) unless stated. Used with both binding
# sets (main: preferred 3-component sensor per station; hn: accelerometers at velocity-sensor stations).

# --- the deep-learning picker plugin and the pickers it provides (scdlrtpicker README) ---
plugins = dlrtpicker
picker = DL3C
spicker = SDL3C

# --- model: README "Configure", testing form (same settings for every station) ---
module.trunk.global.picker.DL3C.model = $file
module.trunk.global.spicker.SDL3C.model = $file
# P: README "Reliable picks": one window centred on the detector trigger
# (maxLatency left unset = half the model window = $half s for this model)
module.trunk.global.picker.DL3C.maxAttempts = 1
# S: README "Reliable picks", sweep of the S-P range. Stations are <= 80 km away (S-P <= about 10 s):
# windows end $half, $((half + 5)), $((half + 10)), $((half + 15)) s after the P pick, i.e. centred on
# S-P = 0, 5, 10, 15 s; the most confident one is kept.
module.trunk.global.spicker.SDL3C.minLatency = $half
module.trunk.global.spicker.SDL3C.maxLatency = $((half + 15))
module.trunk.global.spicker.SDL3C.maxAttempts = 4
module.trunk.global.spicker.SDL3C.strategy = best
# minConfidence (P 0.4, S 0.3), polarityMinConfidence (0.5) and polarityMaxTilt (20): plugin defaults, not set

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

# --- buffers: README "Buffer sizing": ringBufferSize = max(300, 2.5 x window), leadTime = max(60, 1.5 x window)
#     (scautopick defaults 300 / 60 s; leadTime has no effect in --playback mode, picker.cpp:418-424) ---
ringBufferSize = $rb
leadTime = $lead
# --- scautopick defaults (etc/defaults/scautopick.cfg), repeated because --config-file skips them ---
initTime = 60
thresholds.maxGapLength = 4.5
amplitudes = MLv, mb, mB

# --- output: the confidence of S picks is only available as an extra 'SNR' comment ---
extraPickComments = true
EOF
}

scautopick_args() {           # $1 variant, $2 input file
  local v=$1 m s
  m=$(model_of "$v"); s=$(set_of "$v")
  echo "--config-file $RUN/config/scautopick_$m.cfg --offline --playback --ep -f" \
       "--inventory-db file://$INV_SC --config-db file://$RUN/config/bindings_$s.xml -I file://$2"
}

stage_prep() {
  echo "== stage prep: sorted playback files, inventory, bindings, scautopick configs, settings dumps"
  run mkdir -p "$RUN/input" "$RUN/config/key_main" "$RUN/config/key_hn" "$RUN/output" "$RUN/settings" "$SC_HOME"
  local ev
  for ev in $EVENT_IDS; do
    run sc scmssort -u -E -v -o "$RUN/input/${ev}_sorted.mseed" "$PLAYBACK_DIR/$ev.mseed"
  done
  # SeisComP inventory from the StationXML (fdsnxml2inv), then SeisComP's own consistency check
  run sc fdsnxml2inv -f "$STATIONXML" "$INV_SC"
  echo "+ (SeisComP env) scinv check $INV_SC > $RUN/config/scinv_check.txt"
  if [[ $APPLY -eq 1 ]]; then sc scinv check "$INV_SC" > "$RUN/config/scinv_check.txt" 2>&1 || true; fi
  run py "$SCRIPTS/12_bindings.py" --mseed-dir "$RUN/input" --inventory "$INV_SC" --events "$EVENTS_CSV" \
      --keydir-main "$RUN/config/key_main" --keydir-hn "$RUN/config/key_hn" \
      --table "$RUN/config/stations_bound.csv" --coverage "$RUN/config/coverage_bound.csv" \
      --channels "$RUN/config/bound_channels.csv" --probe-out "$RUN/input/startup_probe.mseed"
  local s
  for s in $BINDING_SETS; do
    run sc bindings2cfg --key-dir "$RUN/config/key_$s" -o "$RUN/config/bindings_$s.xml"
  done
  local m W
  for m in $MODELS; do
    if [[ $APPLY -eq 1 || -f $MODELS_DIR/$m.onnx ]]; then W=$(model_window_s "$MODELS_DIR/$m.onnx"); else W=30.01; fi
    write_scautopick_cfg "$RUN/config/scautopick_$m.cfg" "$m" "$MODELS_DIR/$m.onnx" "$W"
  done
  local v first
  first=$(echo $EVENT_IDS | awk '{print $1}')
  for v in $(variants); do
    echo "+ (SeisComP env) scautopick $(scautopick_args "$v" "$RUN/input/${first}_sorted.mseed") --dump-config/--dump-settings > $RUN/settings/$v.dump-*.txt"
    if [[ $APPLY -eq 1 ]]; then
      # shellcheck disable=SC2046
      SC_LOCAL=$RUN/settings/seiscomp_user sc scautopick $(scautopick_args "$v" "$RUN/input/${first}_sorted.mseed") \
        --dump-config > "$RUN/settings/$v.dump-config.txt" 2>&1
      # shellcheck disable=SC2046
      SC_LOCAL=$RUN/settings/seiscomp_user sc scautopick $(scautopick_args "$v" "$RUN/input/${first}_sorted.mseed") \
        --dump-settings > "$RUN/settings/$v.dump-settings.txt" 2>&1
    fi
    run py "$SCRIPTS/12_settings_json.py" --variant "$v" --cfg "$RUN/config/scautopick_$(model_of "$v").cfg" \
        --dump-config "$RUN/settings/$v.dump-config.txt" --dump-settings "$RUN/settings/$v.dump-settings.txt" \
        --bound "$RUN/config/stations_bound.csv" --role "$(set_of "$v")" --out "$RUN/settings/scautopick_$v.settings.json"
  done
}

stage_pick() {
  echo "== stage pick: $(echo $EVENT_IDS | wc -w) events x variants: $(variants | tr '\n' ' ') ($NPAR at a time)"
  local jobs=$RUN/output/jobs.txt v ev m s
  run mkdir -p "$RUN/output"
  {
    for v in $(variants); do
      m=$(model_of "$v"); s=$(set_of "$v")
      for ev in $EVENT_IDS startup_probe; do
        if [[ $ev == startup_probe ]]; then in=$RUN/input/startup_probe.mseed; else in=$RUN/input/${ev}_sorted.mseed; fi
        echo "$RUN $RUN/config/scautopick_$m.cfg $RUN/config/bindings_$s.xml $INV_SC $in $RUN/output/$v/$ev"
      done
    done
  } > "${jobs}.tmp"
  echo "+ $(wc -l < "${jobs}.tmp") runs, e.g.: bash $SCRIPTS/12_pick_one.sh $(head -1 "${jobs}.tmp")"
  if [[ $APPLY -eq 1 ]]; then
    mv "${jobs}.tmp" "$jobs"
    xargs -P "$NPAR" -L 1 bash "$SCRIPTS/12_pick_one.sh" < "$jobs"
  else
    rm -f "${jobs}.tmp"
  fi
  echo "   ~/.seiscomp exists: $([[ -e /home/msseo/.seiscomp ]] && echo YES || echo no);" \
       "telemetry folder in run HOME: $([[ -e $SC_HOME/.cache/Microsoft ]] && echo YES || echo no)"
}

stage_compare() {
  echo "== stage compare: DL picks vs NCSS analyst picks (P within $P_TOL s, S within $S_TOL s)"
  run mkdir -p "$RUN/analysis"
  run py "$SCRIPTS/12_compare.py" --run-dir "$RUN" --variants $(variants) --main-models $MODELS \
      --p-tol "$P_TOL" --s-tol "$S_TOL" --win-before "$WIN_BEFORE" --win-after "$WIN_AFTER" \
      --out-dir "$RUN/analysis"
}

stage_seisbench() {
  echo "== stage seisbench: SeisBench EQTP('ncedc') on $SEISBENCH_EVENTS (env dl-base, read-only, CPU)"
  run mkdir -p "$RUN/seisbench/cache"
  echo "+ (SEISBENCH_CACHE_ROOT=$RUN/seisbench/cache OMP_NUM_THREADS=$SEISBENCH_THREADS CUDA_VISIBLE_DEVICES='') nice -n 10 /usr/bin/time -v -o $RUN/seisbench/time.txt $DLBASE_PY -I $SCRIPTS/12_seisbench_run.py ..."
  if [[ $APPLY -eq 1 ]]; then
    ( export SEISBENCH_CACHE_ROOT=$RUN/seisbench/cache OMP_NUM_THREADS=$SEISBENCH_THREADS \
             MKL_NUM_THREADS=$SEISBENCH_THREADS CUDA_VISIBLE_DEVICES=''
      nice -n 10 /usr/bin/time -v -o "$RUN/seisbench/time.txt" "$DLBASE_PY" -I "$SCRIPTS/12_seisbench_run.py" \
        --sorted-dir "$RUN/input" --coverage "$RUN/config/coverage_bound.csv" --events $SEISBENCH_EVENTS \
        --p-threshold 0.4 --s-threshold 0.3 --polarity-threshold 0.5 --threads "$SEISBENCH_THREADS" \
        --ref "$DATA/reference_tables/picks_ncss.csv" --out-dir "$RUN/seisbench" )
  fi
  run py "$SCRIPTS/12_weights_check.py" --npz "$RUN/seisbench/${SEISBENCH_MODEL}_weights_test.npz" \
      --model "$MODELS_DIR/$SEISBENCH_MODEL.onnx" --out "$RUN/seisbench/weights_check.json"
  run py "$SCRIPTS/12_compare_seisbench.py" --run-dir "$RUN" --model "$SEISBENCH_MODEL" --events $SEISBENCH_EVENTS \
      --p-tol "$P_TOL" --s-tol "$S_TOL" --out-dir "$RUN/seisbench"
  run py "$SCRIPTS/12_normalization_test.py" --run-dir "$RUN" --model "$MODELS_DIR/$SEISBENCH_MODEL.onnx" \
      --variant "$SEISBENCH_MODEL"
  echo "   ~/.seisbench: $(ls -d /home/msseo/.seisbench 2>/dev/null || echo absent)"
}

stage_tables() {
  echo "== stage tables: polarity reference check and the markdown tables of the results note"
  run py "$SCRIPTS/12_polarity_reference_check.py" --run-dir "$RUN"
  echo "+ py $SCRIPTS/12_tables_md.py --run-dir $RUN > $RUN/analysis/tables.md"
  if [[ $APPLY -eq 1 ]]; then py "$SCRIPTS/12_tables_md.py" --run-dir "$RUN" > "$RUN/analysis/tables.md"; fi
}

case "$STAGE" in
  prep)      stage_prep ;;
  pick)      stage_pick ;;
  compare)   stage_compare ;;
  seisbench) stage_seisbench ;;
  tables)    stage_tables ;;
  all)       stage_prep; stage_pick; stage_compare; stage_seisbench; stage_tables ;;
esac
