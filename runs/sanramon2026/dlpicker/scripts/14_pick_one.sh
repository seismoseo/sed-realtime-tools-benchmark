#!/usr/bin/env bash
# 14_pick_one.sh -- one scautopick + scdlrtpicker run of step 14 (called by 14_dlpicker.sh stage pick,
# several at a time through xargs). Copy of runs/sanramon/dlpicker/scripts/12_pick_one.sh; the only change is
# the 7th argument: scautopick runs under /usr/bin/timeout -k 30 <seconds> (inside /usr/bin/time, so the
# measured CPU time and memory still include scautopick; exit 124 = killed by the timeout). Same command as step 09's pick_one():
#   scautopick --config-file <cfg> --offline --playback --ep -f --inventory-db file://<inv>
#              --config-db file://<bindings> -I file://<sorted mseed> --debug
# HOME and SEISCOMP_LOCAL_CONFIG point into the run folder; /usr/bin/time -v (not SeisComP's own 'time')
# records CPU time, wall time and memory; nice -n 10 (Server A is shared).
# Usage: 14_pick_one.sh <run dir> <cfg> <bindings xml> <inventory xml> <input mseed> <output dir> <timeout s>
set -euo pipefail
RUN=$1 CFG=$2 BIND=$3 INV=$4 IN=$5 OUT=$6 TMO=${7:-1800}
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
case "$OUT" in "$PROJECT"/*) ;; *) echo "refusing: $OUT is outside $PROJECT"; exit 2 ;; esac
mkdir -p "$OUT"
(
  export HOME=$RUN/sc_home
  export SEISCOMP_LOCAL_CONFIG=$OUT/seiscomp_user
  export ORT_DISABLE_TELEMETRY=1
  source "$PROJECT/install/env_seiscomp.sh"
  nice -n 10 /usr/bin/time -v -o "$OUT/time.txt" /usr/bin/timeout -k 30 "$TMO" \
    scautopick --config-file "$CFG" --offline --playback --ep -f \
      --inventory-db "file://$INV" --config-db "file://$BIND" -I "file://$IN" --debug \
      > "$OUT/picks.xml" 2> "$OUT/scautopick.log"
)
L=$OUT/scautopick.log
printf '   %-60s %s; CPU %s s; %s [error], %s [warning]; windows DL3C %s SDL3C %s\n' "${OUT#$RUN/output/}" \
  "$(grep -E '^Found [0-9]+ picks' "$L" || echo 'no "Found" line')" \
  "$(awk -F': ' '/User time/{u=$2} /System time/{s=$2} END{printf "%.2f", u+s}' "$OUT/time.txt")" \
  "$(grep -c '\[error\]' "$L" || true)" "$(grep -c '\[warning\]' "$L" || true)" \
  "$(grep -c '\[DL3C/.*attempt' "$L" || true)" "$(grep -c '\[SDL3C/.*attempt' "$L" || true)"
