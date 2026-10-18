#!/usr/bin/env bash
# 04_gwangyang_inputs.sh -- step C2: build the Gwangyang 11-event benchmark inputs for rtDD (scrtdd /
# pyrtdd) and for the DL picker, from the read-only reference copy in data/gwangyang_11ev/reference.
#
# What it produces (all inside the project folder):
#   data/gwangyang_11ev/reference_supplement/  read-only copies of 5 small files from server B that the
#                                              reference copy lacks (cluster config, CLI, KMA catalog)
#   data/gwangyang_11ev/inputs/rtdd_catalog/   station.csv, event.csv, event_centroid_start.csv, phase.csv,
#                                              phase_extra.csv, event_id_map.csv   (rtDD multi-event CSV format)
#   data/gwangyang_11ev/inputs/sds/            SDS miniSEED archive (STEIM2, 512-byte records)
#   data/gwangyang_11ev/inputs/playback/       one miniSEED file per event (not yet time-sorted)
#   data/gwangyang_11ev/inputs/stations.xml    StationXML subset of reference/inventory/merged_inventory.xml
#   data/gwangyang_11ev/inputs/checks/         cross-check tables written by the tools
#   data/gwangyang_11ev/reference_tables/      tidy CSV copies of the reference results
#
# Usage:  bash 04_gwangyang_inputs.sh            # dry run: print every action, change nothing
#         bash 04_gwangyang_inputs.sh --apply    # really do it (log in logs/04_gwangyang_inputs_<date>.log)
#
# Nothing under data/gwangyang_11ev/reference/ is ever written. server B is only read (rsync pull).

set -euo pipefail

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

# --- parameters ---------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
DATA=$PROJECT/data/gwangyang_11ev
TOOLS=$DATA/tools                                   # the Python helpers of this step
PY=/home/msseo/miniforge3/envs/pyrtdd/bin/python    # env pyrtdd: obspy 1.5.1, pandas, numpy, pyrtdd
LOG=$PROJECT/logs/04_gwangyang_inputs_$(date +%Y%m%d).log
SERVER_B=<server-B>
SERVER_B_EQ=/home/msseo/works/10.Earthquake_cycle_project   # source of the reference run (read only)
SUP=$DATA/reference_supplement
# md5 sums of the server B files copied on 2026-10-17 (see reference_supplement/PROVENANCE.md)
declare -A SUP_FILES=(
  [pipeline_code_extra/clusters/gwangyang.py]="$SERVER_B_EQ/pipeline/clusters/gwangyang.py 2917dbbcaeaf0ac5287104c8f521f213"
  [pipeline_code_extra/clusters/_base.py]="$SERVER_B_EQ/pipeline/clusters/_base.py 3c68a02ac593b2fb49679a2aa5ee7584"
  [pipeline_code_extra/cli/run_pipeline.py]="$SERVER_B_EQ/pipeline/cli/run_pipeline.py b6ad7d727476fcb185fc54ebd7a49009"
  [pipeline_code_extra/cli/bootstrap.py]="$SERVER_B_EQ/pipeline/cli/bootstrap.py ba2b543f7f1e9307f7c03f25da671e29"
  [kma_catalog/event_catalog.csv]="$SERVER_B_EQ/Gwangyang_sequence/event_catalog/event_catalog.csv 04581d47c5e74c7a0c280f912ff2f35b"
)

run() {
  echo "+ $*"
  if [[ $APPLY -eq 1 ]]; then "$@"; fi
}

if [[ $APPLY -eq 1 ]]; then
  mkdir -p "$PROJECT/logs"
  exec > >(tee -a "$LOG") 2>&1
  echo "== 04_gwangyang_inputs.sh --apply  $(date '+%F %T %Z')"
else
  echo "== 04_gwangyang_inputs.sh DRY RUN (nothing is changed; add --apply to run)"
fi

# --- 1. small files the reference copy lacks --------------------------------------------------------
# WHY: the cluster configuration (cross-correlation window/band, pair override, picker window), the
# command line and the KMA catalog (magnitudes, KST times) are needed to document the reference run
# and to give events their magnitudes. They are pulled read-only from server B and checked by md5; a file
# that is already present with the right md5 is not fetched again.
for rel in "${!SUP_FILES[@]}"; do
  read -r src want <<< "${SUP_FILES[$rel]}"
  dst=$SUP/$rel
  if [[ -f $dst ]] && [[ $(md5sum "$dst" | cut -d' ' -f1) == "$want" ]]; then
    echo "   ok (md5 matches): $dst"
    continue
  fi
  run mkdir -p "$(dirname "$dst")"
  run timeout 120 rsync -a -e "ssh -o BatchMode=yes -o ConnectTimeout=10" "$SERVER_B:$src" "$dst"
  if [[ $APPLY -eq 1 ]] && [[ $(md5sum "$dst" | cut -d' ' -f1) != "$want" ]]; then
    echo "!! md5 of $dst differs from the 2026-10-17 copy -- the server B file changed; stop and check"; exit 1
  fi
done

# --- 2. rtDD catalog triplet + cross-checks -----------------------------------------------------
# WHY: events/picks exactly as HypoDD's ph2dt used them (Gwangyang_mod.pha, origins from the .pha
# headers), ids 1..11 because rtDD stores event ids as 32-bit integers, channel codes from the SAC set.
run nice -n 10 "$PY" "$TOOLS/make_rtdd_catalog.py"

# --- 3. waveforms: SAC -> SDS archive + per-event playback files ----------------------------------
# WHY: SeisComP (scrtdd, scautopick with the DL picker) reads miniSEED through a RecordStream (SDS
# archive or file); pyrtdd's obspy proxies read the same SDS archive. --overwrite rebuilds both folders
# from scratch so no stale file survives a re-run; the tool verifies sample-exact round trips.
run nice -n 10 "$PY" "$TOOLS/make_waveform_archive.py" --overwrite

# --- 4. station metadata subset -----------------------------------------------------------------
# WHY: scrtdd needs channel dip/azimuth to find the vertical/horizontal channels (for L2/T/R
# cross-correlation) and scautopick needs responses; only metadata that exists is copied.
run nice -n 10 "$PY" "$TOOLS/make_stations_xml.py"

# --- 5. tidy reference tables ----------------------------------------------------------------------
# WHY: one CSV per reference result (HYPOINVERSE, HypoDD dt.ct, HypoDD dt.cc, PhaseNet+ picks) with the
# same event ids as the rtDD catalog, so later runs can be compared row by row.
run nice -n 10 "$PY" "$TOOLS/make_reference_tables.py"

# --- 6. load the catalog with pyrtdd's own reader ------------------------------------------------
# WHY: an independent check with the real C++ parser (scrtdd libhdd) that every value survives.
run nice -n 10 "$PY" "$TOOLS/check_rtdd_catalog_with_pyrtdd.py"

echo "== done (APPLY=$APPLY)"
