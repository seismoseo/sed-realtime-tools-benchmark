#!/bin/bash
# check_waveforms_seiscomp.sh -- read the San Ramon 2025-26 waveforms with SeisComP's own tools
# (independent of obspy; read-only; SeisComP 7.4.0 build of this project). Copied from the 2015
# SR-B script; only the paths and the default test events changed.
#   1. scart --check inputs/sds
#        SeisComP's integrity check of every SDS day file.
#   2. scart -I sdsarchive://inputs/sds -l <stream list> --test --print-streams
#        the sdsarchive RecordStream (what scrtdd reads with -I sdsarchive://...) must return the
#        cc windows of a few test events (stream list built from waveform_requests_cc.csv).
#   3. scmssort -E -u -v <playback file> | cmp - <playback file>
#        if scmssort's output (sorted by record end time, duplicates skipped) is byte-identical to
#        the input, the playback file is already sorted that way and holds no duplicate records.
# Reports: runs/sanramon2026_waveform_checks/ (no waveform files are written).
# Usage: bash check_waveforms_seiscomp.sh [event ids for step 2; default 75283011 75305736]
# Note: SeisComP's env puts its own "timeout" program first on PATH; /usr/bin/timeout is used here.
set -u
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
SR=$PROJECT/data/sanramon_2026
OUT=$PROJECT/runs/sanramon2026_waveform_checks
mkdir -p "$OUT"
source "$PROJECT/install/env_seiscomp.sh"
EVENTS="${*:-75283011 75305736}"

echo "== 1. scart --check (all day files)"
/usr/bin/timeout 3000 scart --check "$SR/inputs/sds" > "$OUT/scart_check_stdout.txt" 2> "$OUT/scart_check.txt"
echo "exit $?"; tail -3 "$OUT/scart_check.txt"

echo "== 2. sdsarchive RecordStream read of the cc windows of: $EVENTS"
for ev in $EVENTS; do
  # columns: set,event_id,origin_time,start,end,chunk,network,station,location,channel,...
  awk -F, -v ev="$ev" 'NR>1 && $2==ev {s=$4; e=$5; gsub("T"," ",s); gsub("Z","",s);
        gsub("T"," ",e); gsub("Z","",e); print s ";" e ";" $7 "." $8 "." $9 "." $10}' \
      "$SR/reference_tables/waveform_requests_cc.csv" > "$OUT/streams_cc_$ev.txt"
  /usr/bin/timeout 600 scart -I "sdsarchive://$SR/inputs/sds" -l "$OUT/streams_cc_$ev.txt" \
      --test --print-streams > /dev/null 2> "$OUT/recordstream_cc_$ev.txt"
  echo "event $ev: exit $?, $(wc -l < "$OUT/streams_cc_$ev.txt") requested lines," \
       "$(grep -c -E '^[A-Z0-9]+\.[A-Z0-9]+\.[A-Z0-9]*\.[A-Z0-9?]+ ' "$OUT/recordstream_cc_$ev.txt") stream lines printed"
done

echo "== 3. scmssort -E -u on every playback file"
: > "$OUT/scmssort_playback.txt"
for f in "$SR"/inputs/playback/*.mseed; do
  b=$(basename "$f" .mseed)
  scmssort -E -u -v "$f" 2> "$OUT/scmssort_$b.log" | cmp -s - "$f"
  r=$?
  if [ $r -eq 0 ]; then res=identical; else res=DIFFERENT; fi
  echo "$b $res $(stat -c %s "$f") bytes" | tee -a "$OUT/scmssort_playback.txt"
done
echo "done"
