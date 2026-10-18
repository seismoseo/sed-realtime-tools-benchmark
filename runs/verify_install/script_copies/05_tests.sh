#!/usr/bin/env bash
# 05_tests.sh -- step T: unit tests of scrtdd (and of SeisComP as a whole), the list of the
# deep-learning models shipped with scdlrtpicker, and a one-event smoke test of the DL picker.
#
# Stages, run in this order by default:
#   nllgrids : scrtdd's unit tests read NonLinLoc travel-time grids that are too big for git; they must
#              be generated first inside the scrtdd source tree (scrtdd README, "Tests"):
#              PATH=<NonLinLoc bin>:$PATH; cd libs/hdd/test/data/nll; ./generate.ch
#              The hddsc tests read the same grids through the symlink libs/hddsc/test/data/nll
#              (part of scrtdd's git tree), so one generation serves both.
#   hdd      : 'ctest -R hdd' = scrtdd's 5 test_hdd_* (library libhdd) + 2 test_hddsc_* (SeisComP glue).
#   ctest    : the complete SeisComP ctest suite (52 tests) EXCEPT 8 tests that start network servers:
#              the 7 test_fdsnws_* start an FDSNWS web server listening on 0.0.0.0:9980 (all network
#              interfaces) and scevent-remote starts two scmaster messaging servers and two scevent
#              REST servers on 127.0.0.1:9981/9982/9991/9992. This project must not open network ports
#              on the shared server Server A, so these 8 are excluded and reported as "not run".
#   models   : the 49 ONNX models shipped with scdlrtpicker: their scdlrtpicker metadata
#              (models/show_model_info.py, in env pyrtdd which has onnx) and the SeisBench metadata of
#              the weight sets they were exported from (05_seisbench_weight_info.py: training data,
#              SeisBench's own pick thresholds, preprocessing). Written to docs/dlrtpicker_models.txt.
#   smoke    : scautopick with the dlrtpicker plugin (P picker DL3C, S picker SDL3C, one PhaseNet ONNX
#              model) on one Gwangyang event (ML 2.2), offline from a file: no messaging, no database,
#              no network. Picks are compared with that event's PhaseNet+ picks. The other recommended
#              models are run the same way, only to check that they load and run (EXTRA_MODELS).
#
# Usage:  bash 05_tests.sh                          # dry run: print every action, change nothing
#         bash 05_tests.sh --apply                  # all stages
#         bash 05_tests.sh --apply --stage smoke    # one stage: nllgrids | hdd | ctest | models | smoke | all
#         --regenerate-grids                        # stage nllgrids: run generate.ch even if all grids exist
#
# Everything is written inside the project folder (the NonLinLoc grids and the files some tests write
# go into the scrtdd source tree, which is inside the project). SeisComP programs run with
# HOME=runs/seiscomp_home and their own SEISCOMP_LOCAL_CONFIG, so ~/.seiscomp is never created.
# In --apply mode all output is appended to the log file below.

set -euo pipefail

# --------------------------------------------------------------------------------------------------
# parameters (everything that defines the result is here)
# --------------------------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
CONDA_BASE=/home/msseo/miniforge3
PY_ENV=$CONDA_BASE/envs/pyrtdd                    # python helpers (obspy, pandas, onnx)
ENV_SC=$PROJECT/install/env_seiscomp.sh           # SeisComP environment (step A)
SC_HOME=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install/home               # HOME for every SeisComP program (rule: never ~/.seiscomp)

SC_BUILD_DIR=$PROJECT/software/build/seiscomp     # CMake build tree with the compiled unit tests
SCRTDD_SRC=$PROJECT/software/src/seiscomp/src/extras/scrtdd
NLL_TEST_DIR=$SCRTDD_SRC/libs/hdd/test/data/nll   # scrtdd's NonLinLoc test-grid recipes
NLL_HDDSC_LINK=$SCRTDD_SRC/libs/hddsc/test/data/nll
NLL_BIN=$PROJECT/software/NonLinLoc/bin           # NonLinLoc v7.00.16 (step C1)
NLL_SETS="iasp91_2D_sdc iasp91_2D_simple iasp91_2D_azimuthal_equidist iasp91_2D_lambert iasp91_2D_merc
          iasp91_3D_sdc iasp91_3D_simple iasp91_3D_azimuthal_equidist iasp91_3D_lambert iasp91_3D_merc"
NLL_TIME_FILES_EXPECTED=132    # per set: 16 stations x P,S x (time, angle) x (.hdr, .buf) = 128,
                               # + Grid2Time's copy of the P and S model grids (.hdr, .buf) = 4
NLL_MODEL_FILES_EXPECTED=4     # per set: P and S velocity model x (.hdr, .buf)

TEST_OUT=$PROJECT/runs/05_tests                   # ctest logs and JUnit XML
CTEST_JOBS=8                                      # Server A is shared
CTEST_TIMEOUT=600                                 # seconds per test
CTEST_EXCLUDE='^(test_fdsnws_.*|scevent-remote)$' # tests that open network ports (see header)

MODELS_DIR=$PROJECT/software/src/seiscomp/src/extras/scdlrtpicker/models
MODELS_TXT=$PROJECT/docs/dlrtpicker_models.txt

# smoke test
EVENT=20210827220322                              # KMA id (UTC) of the ML 2.2 Gwangyang event
DATA=$PROJECT/data/gwangyang_11ev
PLAYBACK=$DATA/inputs/playback/$EVENT.mseed       # all stations, 100 Hz, ~22:00:37-22:09:33 UTC
STATIONXML=$DATA/inputs/stations.xml              # FDSN StationXML (step C2; lacks 7 of the 53 stations)
REF_PICKS=$DATA/reference_tables/picks_phasenet_plus.csv
SMOKE_DIR=$PROJECT/runs/smoke_dlpicker
MODEL=$MODELS_DIR/phasenet_instance.onnx          # primary model (recommendation: docs/install_notes/05_tests.md)
# the other recommended models: load-and-run check on the same event (not the model comparison)
EXTRA_MODELS="phasenet_stead eqtransformer_stead phasenet_original"
P_TOL=0.5                                         # pick matching tolerance P [s]
S_TOL=1.0                                         # pick matching tolerance S [s]

LOG=$PROJECT/logs/05_tests_$(date +%Y%m%d).log

# --------------------------------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------------------------------
APPLY=0
STAGE=all
REGEN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --regenerate-grids) REGEN=1; shift ;;
    --stage) STAGE=${2:?--stage needs nllgrids, hdd, ctest, models, smoke or all}; shift 2 ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
case "$STAGE" in nllgrids|hdd|ctest|models|smoke|all) ;; *) echo "bad --stage $STAGE"; exit 2 ;; esac

# guard: every folder this script writes to must be inside the project
for d in "$SC_HOME" "$SC_BUILD_DIR" "$NLL_TEST_DIR" "$TEST_OUT" "$SMOKE_DIR" "$(dirname "$MODELS_TXT")"; do
  case "$d" in "$PROJECT"/*) ;; *) echo "refusing: $d is outside $PROJECT"; exit 2 ;; esac
done

if [[ $APPLY -eq 1 ]]; then
  mkdir -p "$(dirname "$LOG")"
  exec > >(tee -a "$LOG") 2>&1          # keep a full record of what was done
fi
echo "==== 05_tests.sh  $(date '+%Y-%m-%d %H:%M:%S %Z')  host $(hostname -s)  APPLY=$APPLY  STAGE=$STAGE"
trap 'echo "==== 05_tests.sh finished with exit code $? ($(date +%H:%M:%S))"' EXIT

# --------------------------------------------------------------------------------------------------
# helpers: every action is printed; only executed with --apply
# --------------------------------------------------------------------------------------------------
run() {                       # run a command
  echo "+ $*"
  if [[ $APPLY -eq 1 ]]; then "$@"; fi
}
run_in() {                    # run a command inside a directory
  local dir=$1; shift
  echo "+ (cd $dir && $*)"
  if [[ $APPLY -eq 1 ]]; then (cd "$dir" && "$@"); fi
}
run_out() {                   # run a command, stdout to a file (stderr stays in the log)
  local out=$1; shift
  echo "+ $* > $out"
  if [[ $APPLY -eq 1 ]]; then "$@" > "$out"; fi
}
write_file() {                # write stdin to a file; the content is always shown
  local file=$1 content
  content=$(cat)
  echo "+ write $file"
  printf '%s\n' "$content" | sed 's/^/    | /'
  if [[ $APPLY -eq 1 ]]; then printf '%s\n' "$content" > "$file"; fi
}
sc() {                        # run a command in the SeisComP environment, in a subshell
  # HOME and SEISCOMP_LOCAL_CONFIG point into the project: SeisComP programs create their per-user
  # folder (logs, user config) there and never in the real home directory. SC_LOCAL may be set by
  # the caller to give a run its own per-user folder.
  # ORT_DISABLE_TELEMETRY=1: the official ONNX Runtime 1.31.0 build (used by the dlrtpicker plugin)
  # contains Microsoft's 1DS usage telemetry. Without this switch every scautopick run with the plugin
  # adds an event to $HOME/.cache/Microsoft/DeveloperTools/.onnxruntime/onnxruntime.db (plus a device
  # id) for upload to mobile.events.data.microsoft.com. With it nothing is written (checked
  # 2026-10-17); the picks are identical either way.
  ( export HOME=$SC_HOME
    export SEISCOMP_LOCAL_CONFIG=${SC_LOCAL:-$SC_HOME/.seiscomp}
    export ORT_DISABLE_TELEMETRY=1
    source "$ENV_SC"
    "$@" )
}
py() {                        # run a python helper in env pyrtdd (subshell); -I: ignore user site/cwd
  ( set +u; source "$CONDA_BASE/etc/profile.d/conda.sh"; conda activate "$PY_ENV"; set -u
    python -I "$@" )
}
count_nll_files() {           # prints "<time files> <model files>" of one NLL test-grid set
  local d=$NLL_TEST_DIR/$1
  echo "$(find "$d/time" -maxdepth 1 \( -name '*.hdr' -o -name '*.buf' \) 2>/dev/null | wc -l)" \
       "$(find "$d/model" -maxdepth 1 \( -name '*.hdr' -o -name '*.buf' \) 2>/dev/null | wc -l)"
}

# --------------------------------------------------------------------------------------------------
# stage nllgrids
# --------------------------------------------------------------------------------------------------
stage_nllgrids() {
  echo "== stage nllgrids: NonLinLoc test grids for scrtdd's unit tests"
  for p in Vel2Grid Grid2Time; do
    [[ -x $NLL_BIN/$p ]] || { echo "ERROR: $NLL_BIN/$p missing (run install/02_build_nonlinloc.sh)"; exit 1; }
  done
  echo "   NonLinLoc: $(head -1 "$PROJECT/software/NonLinLoc/VERSION.txt")"
  echo "   hddsc reads the grids through its symlink: $NLL_HDDSC_LINK -> $(readlink "$NLL_HDDSC_LINK")"
  echo "   which resolves to: $(readlink -f "$NLL_HDDSC_LINK")"
  [[ "$(readlink -f "$NLL_HDDSC_LINK")" == "$(readlink -f "$NLL_TEST_DIR")" ]] \
    || { echo "ERROR: hddsc nll link does not point to the hdd grids"; exit 1; }
  # the grids are deterministic: skip the ~70 s generation when every set is already complete
  local complete=1 s nt nm
  for s in $NLL_SETS; do
    read -r nt nm < <(count_nll_files "$s")
    if [[ $nt -ne $NLL_TIME_FILES_EXPECTED || $nm -ne $NLL_MODEL_FILES_EXPECTED ]]; then complete=0; fi
  done
  if [[ $complete -eq 1 && $REGEN -eq 0 ]]; then
    echo "   all $(echo $NLL_SETS | wc -w) grid sets already complete: generate.ch skipped (use --regenerate-grids to force)"
  else
    # generate.ch has no '#!' line; it is a plain sh script (cd into each set, run its generate.sh,
    # which runs Vel2Grid and Grid2Time for P and S). NonLinLoc's chatter goes to its own log file.
    echo "+ (cd $NLL_TEST_DIR && PATH=$NLL_BIN:\$PATH nice -n 10 sh ./generate.ch) > $TEST_OUT/nllgrids_generate.log 2>&1"
    if [[ $APPLY -eq 1 ]]; then
      local t0=$SECONDS
      ( export PATH=$NLL_BIN:$PATH; cd "$NLL_TEST_DIR"; nice -n 10 sh ./generate.ch ) \
        > "$TEST_OUT/nllgrids_generate.log" 2>&1 \
        || { echo "ERROR: generate.ch failed, see $TEST_OUT/nllgrids_generate.log"; tail -20 "$TEST_OUT/nllgrids_generate.log"; exit 1; }
      echo "   generate.ch took $((SECONDS - t0)) s"
    fi
  fi
  local bad=0
  for s in $NLL_SETS; do
    read -r nt nm < <(count_nll_files "$s")
    echo "   $s: $nt time/angle files (expect $NLL_TIME_FILES_EXPECTED), $nm model files (expect $NLL_MODEL_FILES_EXPECTED)"
    if [[ $APPLY -eq 1 && ( $nt -ne $NLL_TIME_FILES_EXPECTED || $nm -ne $NLL_MODEL_FILES_EXPECTED ) ]]; then bad=1; fi
  done
  [[ $bad -eq 0 ]] || { echo "ERROR: incomplete grid sets"; exit 1; }
  echo "   size: $(du -sh "$NLL_TEST_DIR" | cut -f1)"
}

# --------------------------------------------------------------------------------------------------
# stage hdd
# --------------------------------------------------------------------------------------------------
stage_hdd() {
  echo "== stage hdd: scrtdd unit tests (ctest -R hdd)"
  echo "   every test name containing hdd or rtdd (ctest -N):"
  sc ctest --test-dir "$SC_BUILD_DIR" -N | grep -E 'Test +#' | grep -i -E 'hdd|rtdd' | sed 's/^/     /'
  # --output-junit keeps the per-test result in a machine-readable file next to the log
  local rc=0
  echo "+ (SeisComP env) ctest --test-dir $SC_BUILD_DIR -R hdd --output-on-failure --timeout $CTEST_TIMEOUT --output-junit $TEST_OUT/ctest_hdd_junit.xml > $TEST_OUT/ctest_hdd.log"
  if [[ $APPLY -eq 1 ]]; then
    SC_LOCAL=$TEST_OUT/seiscomp_user sc nice -n 10 ctest --test-dir "$SC_BUILD_DIR" -R hdd \
      --output-on-failure --timeout "$CTEST_TIMEOUT" --output-junit "$TEST_OUT/ctest_hdd_junit.xml" \
      > "$TEST_OUT/ctest_hdd.log" 2>&1 || rc=$?
    grep -E 'Test +#|tests passed|tests failed|Total Test time' "$TEST_OUT/ctest_hdd.log" | sed 's/^/     /' || true
    echo "   ctest exit code: $rc (full output: $TEST_OUT/ctest_hdd.log)"
  fi
}

# --------------------------------------------------------------------------------------------------
# stage ctest
# --------------------------------------------------------------------------------------------------
stage_ctest() {
  echo "== stage ctest: complete SeisComP unit-test suite except the tests that open network ports"
  echo "   not run (they start servers on network ports):"
  sc ctest --test-dir "$SC_BUILD_DIR" -N -R "$CTEST_EXCLUDE" | grep 'Test *#' | sed 's/^/     /'
  local rc=0
  echo "+ (SeisComP env) ctest --test-dir $SC_BUILD_DIR -j$CTEST_JOBS -E '$CTEST_EXCLUDE' --output-on-failure --timeout $CTEST_TIMEOUT --output-junit $TEST_OUT/ctest_full_junit.xml > $TEST_OUT/ctest_full.log"
  if [[ $APPLY -eq 1 ]]; then
    SC_LOCAL=$TEST_OUT/seiscomp_user sc nice -n 10 ctest --test-dir "$SC_BUILD_DIR" -j"$CTEST_JOBS" \
      -E "$CTEST_EXCLUDE" --output-on-failure --timeout "$CTEST_TIMEOUT" \
      --output-junit "$TEST_OUT/ctest_full_junit.xml" > "$TEST_OUT/ctest_full.log" 2>&1 || rc=$?
    grep -E 'Test +#|tests passed|tests failed|Total Test time|\*\*\*' "$TEST_OUT/ctest_full.log" | sed 's/^/     /' || true
    echo "   ctest exit code: $rc (full output: $TEST_OUT/ctest_full.log)"
  fi
}

# --------------------------------------------------------------------------------------------------
# stage models
# --------------------------------------------------------------------------------------------------
stage_models() {
  echo "== stage models: scdlrtpicker's shipped ONNX models -> $MODELS_TXT"
  echo "+ (env pyrtdd) build $MODELS_TXT from show_model_info.py (table + per-model detail) and 05_seisbench_weight_info.py"
  if [[ $APPLY -eq 1 ]]; then
    {
      echo "# scdlrtpicker v1.1.1 models ($(ls "$MODELS_DIR"/*.onnx | wc -l) files in $MODELS_DIR)"
      echo "# written $(date '+%Y-%m-%d %H:%M %Z') by install/05_tests.sh --stage models"
      echo "# Part 1: python show_model_info.py *.onnx   (comparison table; run inside models/ so the"
      echo "#         file column shows names instead of long paths)"
      echo "# Part 2: python show_model_info.py <file>   (full detail, one block per model)"
      echo "# Part 3: SeisBench metadata of each weight set (install/05_seisbench_weight_info.py)"
      echo "# python $("$PY_ENV/bin/python" -c 'import sys; print(sys.version.split()[0])'), onnx $("$PY_ENV/bin/python" -c 'import onnx; print(onnx.__version__)')"
      echo
      echo "######## Part 1"
      (cd "$MODELS_DIR" && py show_model_info.py *.onnx)
      echo
      echo "######## Part 2"
      for f in "$MODELS_DIR"/*.onnx; do (cd "$MODELS_DIR" && py show_model_info.py "$(basename "$f")"); done
      echo
      echo "######## Part 3"
      py "$PROJECT/install/05_seisbench_weight_info.py" "$MODELS_DIR"
    } > "$MODELS_TXT"
    echo "   $(wc -l < "$MODELS_TXT") lines written"
  fi
}

# --------------------------------------------------------------------------------------------------
# stage smoke
# --------------------------------------------------------------------------------------------------
model_half_window() {         # half the model window in whole seconds (PhaseNet 30.01 s -> 15, EQTransformer 60 s -> 30)
  py -c 'import sys, onnx
m = {p.key: p.value for p in onnx.load(sys.argv[1], load_external_data=False).metadata_props}
print(round(int(m["seiscomp.picker.windowLength"]) / float(m["seiscomp.picker.sampleRate"]) / 2))' "$1"
}

write_scautopick_cfg() {      # $1 = config file, $2 = model file, $3 = half the model window [s]
  local cfg=$1 model=$2 half=$3
  write_file "$cfg" <<EOF
# scautopick.cfg for the DL-picker smoke test (install/05_tests.sh, stage smoke), model $(basename "$model").
# Read with --config-file: no other configuration file is used.

# --- the deep-learning picker plugin and the pickers it provides (scdlrtpicker README) ---
plugins = dlrtpicker
picker = DL3C
spicker = SDL3C

# --- model: README "Configure", testing form (same settings for every station) ---
module.trunk.global.picker.DL3C.model = $model
module.trunk.global.spicker.SDL3C.model = $model
# P: README "Reliable picks": one window centred on the detector trigger
# (maxLatency left unset = half the model window = $half s for this model)
module.trunk.global.picker.DL3C.maxAttempts = 1
# S: README "Reliable picks", sweep of the S-P range. Stations are 7-99 km away (S-P 1.7-11.7 s for
# this event): windows end $half, $((half + 5)), $((half + 10)), $((half + 15)) s after the P pick, i.e. centred
# on S-P = 0, 5, 10, 15 s; the most confident one is kept.
module.trunk.global.spicker.SDL3C.minLatency = $half
module.trunk.global.spicker.SDL3C.maxLatency = $((half + 15))
module.trunk.global.spicker.SDL3C.maxAttempts = 4
module.trunk.global.spicker.SDL3C.strategy = best
# minConfidence: plugin defaults (P 0.4, S 0.3), not set here

# --- STA/LTA detector: README "scautopick: The STA/LTA detector" (permissive; the model decides) ---
filter = "RMHP(10)->ITAPER(30)->BW_BP(4,5,20)->STALTA(1,30)"
timeCorrection = 0
thresholds.triggerOn = 1.8
thresholds.triggerOff = 1.0
killPendingSPickers = false

# --- dead time: README "scautopick: Dead time" rules of thumb ---
thresholds.deadTime = $half            # = picker.DL3C.maxLatency ($half s, see above)
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

smoke_run() {                 # $1 = model file: configure, run scautopick, compare with PhaseNet+
  local model=$1 name half out cfg
  name=$(basename "$model" .onnx)
  half=$(model_half_window "$model")
  out=$SMOKE_DIR/output/$name
  cfg=$SMOKE_DIR/config/scautopick_$name.cfg
  echo "-- model $name (window $((2 * half)) s; half window $half s)"
  run mkdir -p "$out"
  write_scautopick_cfg "$cfg" "$model" "$half"

  # offline (no messaging), playback (historic data from a file), --ep (picks and amplitudes as
  # SeisComP XML on stdout), inventory and bindings from the files made above. /usr/bin/time -v
  # records wall time and memory (not 'time'/'timeout': the SeisComP environment has its own
  # bin/timeout with a different syntax). Each run gets its own per-user folder for its log file.
  echo "+ (SeisComP env, SEISCOMP_LOCAL_CONFIG=$out/seiscomp_user) /usr/bin/time -v -o $out/time.txt scautopick --config-file $cfg --offline --playback --ep -f --inventory-db file://$SMOKE_DIR/input/inventory_sc.xml --config-db file://$SMOKE_DIR/config/bindings_config.xml -I file://$SMOKE_DIR/input/${EVENT}_sorted.mseed --debug > $out/picks.xml 2> $out/scautopick.log"
  if [[ $APPLY -eq 1 ]]; then
    SC_LOCAL=$out/seiscomp_user sc /usr/bin/time -v -o "$out/time.txt" \
      scautopick --config-file "$cfg" --offline --playback --ep -f \
        --inventory-db "file://$SMOKE_DIR/input/inventory_sc.xml" \
        --config-db "file://$SMOKE_DIR/config/bindings_config.xml" \
        -I "file://$SMOKE_DIR/input/${EVENT}_sorted.mseed" --debug > "$out/picks.xml" 2> "$out/scautopick.log"
    local L=$out/scautopick.log
    echo "   scautopick: $(grep -E '^Found [0-9]+ picks' "$L")"
    grep -E 'Elapsed \(wall clock\)|Maximum resident|Percent of CPU' "$out/time.txt" | sed 's/^\s*/     /' || true
    echo "   plugin: $(grep -m1 'OnnxSession: loaded' "$L" | sed 's/^.*OnnxSession/OnnxSession/')"
    echo "   log: $(grep -c . "$L") lines, $(grep -c '\[error\]' "$L" || true) [error], $(grep -c '\[warning\]' "$L" || true) [warning]"
    grep '\[warning\]\|\[error\]' "$L" | sed 's/^/     /' || true
    echo "   detector triggers: $(grep -c 'trigger on =' "$L" || true);" \
         "DL3C pickers: $(grep -c 'created picker DL3C' "$L" || true);" \
         "SDL3C pickers: $(grep -c 'created secondary picker SDL3C' "$L" || true);" \
         "model windows run: DL3C $(grep -c '\[DL3C/.*attempt' "$L" || true), SDL3C $(grep -c '\[SDL3C/.*attempt' "$L" || true)"
  fi
  run py "$PROJECT/install/05_compare_picks.py" --picks-xml "$out/picks.xml" --ref "$REF_PICKS" \
      --kma-id "$EVENT" --bound "$SMOKE_DIR/config/stations_bound.csv" --p-tol "$P_TOL" --s-tol "$S_TOL" \
      --out "$out/compare"
}

stage_smoke() {
  echo "== stage smoke: scautopick + dlrtpicker on event $EVENT (offline, from a file)"
  local IN=$SMOKE_DIR/input CFG=$SMOKE_DIR/config
  run mkdir -p "$IN" "$CFG/key" "$SMOKE_DIR/output"

  # 1. records sorted by end time, duplicates removed (scmssort -u -E), as SeisComP recommends
  #    before any playback: the picker expects the records of all streams in time order.
  run sc scmssort -u -E -v -o "$IN/${EVENT}_sorted.mseed" "$PLAYBACK"

  # 2. station metadata in SeisComP's own XML format. --core.plugins=dbsqlite3 replaces the default
  #    'core.plugins = dbmysql' of etc/defaults/global.cfg: this build has no MySQL driver, and
  #    every program that reads the default configuration otherwise stops with
  #    "Did not find plugin dbmysql". No database is used.
  run sc fdsnxml2inv --core.plugins=dbsqlite3 -f "$STATIONXML" "$IN/inventory_sc.xml"

  # 3. station bindings: detect on one vertical channel per station (see 05_smoke_bindings.py)
  run py "$PROJECT/install/05_smoke_bindings.py" --mseed "$IN/${EVENT}_sorted.mseed" \
      --stationxml "$STATIONXML" --keydir "$CFG/key" --table "$CFG/stations_bound.csv"
  run sc bindings2cfg --core.plugins=dbsqlite3 --key-dir "$CFG/key" -o "$CFG/bindings_config.xml"

  # 4. the smoke test proper: the primary model
  smoke_run "$MODEL"

  # 5. load-and-run check of the other recommended models (same data and settings, model-specific
  #    window lengths). Not the model comparison, which comes in a later step.
  local m
  for m in $EXTRA_MODELS; do smoke_run "$MODELS_DIR/$m.onnx"; done

  if [[ $APPLY -eq 1 ]]; then
    echo "-- summary (P tolerance $P_TOL s, S tolerance $S_TOL s; see output/<model>/compare_summary.json)"
    py -c 'import json, sys
for f in sys.argv[1:]:
    d = json.load(open(f))
    name = f.split("/")[-2]
    row = [name]
    for ph in ("P", "S"):
        row.append("%s %3d picks, %2d/%d matched, |dt| median %s max %s s" % (
            ph, d["seiscomp_" + ph], d[ph + "_matched"], d["reference_" + ph + "_on_bound_stations"],
            d[ph + "_median_abs_dt_s"], d[ph + "_max_abs_dt_s"]))
    print("   %-22s %s | %s" % tuple(row))' \
      "$SMOKE_DIR/output/$(basename "$MODEL" .onnx)/compare_summary.json" \
      $(for m in $EXTRA_MODELS; do echo "$SMOKE_DIR/output/$m/compare_summary.json"; done)
  fi
  echo "   ~/.seiscomp exists: $([[ -e /home/msseo/.seiscomp ]] && echo YES || echo no)"
}

# --------------------------------------------------------------------------------------------------
run mkdir -p "$TEST_OUT"
case "$STAGE" in
  nllgrids) stage_nllgrids ;;
  hdd)      stage_hdd ;;
  ctest)    stage_ctest ;;
  models)   stage_models ;;
  smoke)    stage_smoke ;;
  all)      stage_nllgrids; stage_hdd; stage_ctest; stage_models; stage_smoke ;;
esac
