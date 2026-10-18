#!/usr/bin/env bash
# 06_gwangyang_prep.sh -- step Prep of the Gwangyang 11-event benchmark: station inventory for rtDD /
# SeisComP, the project's global SeisComP configuration, and tidy tables of the reference HypoDD
# differential times.
#
# Stages, run in this order by default:
#   master    : copy (read-only rsync pull) the user's canonical KMA master StationXML from server B into
#               data/gwangyang_11ev/reference_supplement/inventory/ and record its md5 in PROVENANCE.md.
#               WHY: 21 SAC channels at 7 stations have no metadata in reference/inventory/merged_inventory.xml
#               (step C2, inputs/checks/channels_without_metadata.csv); the master XML has them.
#   inventory : tools/make_stations_rtdd_xml.py -> inputs/stations_rtdd.xml (StationXML).
#               One file for rtDD (pyrtdd and scrtdd) and scautopick: exactly the 162 SAC channels, metadata
#               from merged_inventory.xml where it has the channel, else from the master XML; then station and
#               channel latitude/longitude/elevation REPLACED by inputs/rtdd_catalog/station.csv (the coordinates
#               HypoDD used horizontally and the NonLinLoc grids were computed for). Depth, orientation and
#               responses are not changed. Every coordinate change -> inputs/checks/inventory_coordinate_changes.csv
#   validate  : tools/check_stations_rtdd_xml.py: obspy reads it (and the FDSN schema validates it); each of
#               the 1656 SAC files (162 channels) has exactly one channel epoch covering it; pyrtdd NLLGrid finds
#               the own kim1983 grid of all 54 stations from the coordinates read back from the file, at
#               maxSearchDistance 0.1 m (libhdd/pyrtdd default) and 10 m (scrtdd plugin default), incl. KWJU/KWJ2.
#   scinv     : fdsnxml2inv -> inputs/inventory_sc.xml (SeisComP XML); 'scinv check' (default and strict
#               limits) and 'scinv ls'; tools/check_inventory_sc.py reads it with SeisComP's own Python API and
#               compares every SensorLocation and Stream with stations_rtdd.xml and station.csv.
#   globalcfg : 'core.plugins = dbsqlite3' into $SEISCOMP_ROOT/etc/global.cfg (this project's own installation;
#               existing lines are kept), then a check that fdsnxml2inv and scinv work WITHOUT --core.plugins.
#               WHY: etc/defaults/global.cfg loads dbmysql, which this build does not have; every SeisComP program
#               that reads the default configuration otherwise stops with "Did not find plugin dbmysql".
#   dtables   : tools/make_dt_tables.py -> reference_tables/dtcc_measured.csv, dtcc_used.csv, dtct.csv
#               (tidy copies of the reference HypoDD dt.cc_P/*, dt.cc_S/*, dt.cc_0.7_combined, dt.ct) with
#               consistency and sign checks.
#
# Usage:  bash 06_gwangyang_prep.sh                          # dry run: print every action, change nothing
#         bash 06_gwangyang_prep.sh --apply                  # all stages
#         bash 06_gwangyang_prep.sh --apply --stage scinv    # one stage: master|inventory|validate|scinv|globalcfg|dtables|all
#
# Everything is written inside the project folder; server B is only read (ssh md5sum, rsync pull). SeisComP
# programs run with HOME and SEISCOMP_LOCAL_CONFIG inside the run folder, so ~/.seiscomp is never created.
# In --apply mode all output is appended to the log file below. Option values actually used are saved as
# JSON in $RUN/options/.

set -euo pipefail

# --------------------------------------------------------------------------------------------------
# parameters (everything that defines the result is here)
# --------------------------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
CONDA_BASE=/home/msseo/miniforge3
PY_ENV=$CONDA_BASE/envs/pyrtdd                  # python helpers: obspy 1.5.1, pandas, numpy, pyproj, pyrtdd
ENV_SC=$PROJECT/install/env_seiscomp.sh         # SeisComP 7.4.0 environment (step A)
DATA=$PROJECT/data/gwangyang_11ev
TOOLS=$DATA/tools
RUN=$PROJECT/runs/06_gwangyang_prep             # run folder: options JSON, logs of SeisComP tools, check tables
SC_HOME=$RUN/home                               # HOME for SeisComP programs (rule: never ~/.seiscomp)
SC_LOCAL=$SC_HOME/.seiscomp                     # SEISCOMP_LOCAL_CONFIG for SeisComP programs

# stage master: the KMA master StationXML (KS + KG networks), read-only on server B
SERVER_B=<server-B>
MASTER_SRC=/home/msseo/works/27.Haenam_sequence/data/stations/responses/master/KS_KG_metadata_1.0.2.xml
# the file merged_inventory.xml cites as its master source (a symlink to MASTER_SRC on server B; md5 recorded too)
MASTER_SRC_ALIAS=/home/msseo/works/73.Gwangyang_sequence/data/stations/responses/master/KS_KG_metadata_1.0.2.xml
MASTER_MD5_PREFIX=687bf07d                      # expected md5 prefix (task definition)
SUP=$DATA/reference_supplement
MASTER_XML=$SUP/inventory/KS_KG_metadata_1.0.2.xml

# stage inventory / validate / scinv
STATION_CSV=$DATA/inputs/rtdd_catalog/station.csv
STATIONS_RTDD=$DATA/inputs/stations_rtdd.xml
INVENTORY_SC=$DATA/inputs/inventory_sc.xml
COORD_CHANGES=$DATA/inputs/checks/inventory_coordinate_changes.csv

# scinv check limits: the defaults, and a strict run. The strict run asks for station and sensor location to
# coincide (we set both to station.csv), so any distance/elevation report there would be a real error.
SCINV_STRICT_OPTS="--distance 0.0001 --max-elevation-difference 0.001"

LOG=$PROJECT/logs/06_gwangyang_prep_$(date +%Y%m%d).log

# --------------------------------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------------------------------
APPLY=0
STAGE=all
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --stage) STAGE=${2:?--stage needs master, inventory, validate, scinv, globalcfg, dtables or all}; shift 2 ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
case "$STAGE" in master|inventory|validate|scinv|globalcfg|dtables|all) ;; *) echo "bad --stage $STAGE"; exit 2 ;; esac

# guard: every place this script writes to must be inside the project
for d in "$RUN" "$SC_HOME" "$SUP" "$(dirname "$STATIONS_RTDD")" "$(dirname "$COORD_CHANGES")" "$DATA/reference_tables"; do
  case "$d" in "$PROJECT"/*) ;; *) echo "refusing: $d is outside $PROJECT"; exit 2 ;; esac
done

if [[ $APPLY -eq 1 ]]; then
  mkdir -p "$(dirname "$LOG")"
  exec > >(tee -a "$LOG") 2>&1          # keep a full record of what was done
fi
echo "==== 06_gwangyang_prep.sh  $(date '+%Y-%m-%d %H:%M:%S %Z')  host $(hostname -s)  APPLY=$APPLY  STAGE=$STAGE"
trap 'echo "==== 06_gwangyang_prep.sh finished with exit code $? ($(date +%H:%M:%S))"' EXIT

# --------------------------------------------------------------------------------------------------
# helpers: every action is printed; only executed with --apply
# --------------------------------------------------------------------------------------------------
run() {                       # run a command
  echo "+ $*"
  if [[ $APPLY -eq 1 ]]; then "$@"; fi
}
sc() {                        # run a command in the SeisComP environment, in a subshell
  # HOME and SEISCOMP_LOCAL_CONFIG point into the run folder: SeisComP programs create their per-user
  # folder (logs) there and never in the real home directory. ORT_DISABLE_TELEMETRY=1 as in step T
  # (no DL model is loaded in this step, but the setting costs nothing).
  ( export HOME=$SC_HOME
    export SEISCOMP_LOCAL_CONFIG=$SC_LOCAL
    export ORT_DISABLE_TELEMETRY=1
    source "$ENV_SC"
    "$@" )
}
py() {                        # run a python helper in env pyrtdd (subshell); -I: ignore user site/cwd
  ( set +u; source "$CONDA_BASE/etc/profile.d/conda.sh"; conda activate "$PY_ENV"; set -u
    nice -n 10 python -I "$@" )
}
sc_py() {                     # run a python helper with the SeisComP environment's python (seiscomp modules).
  # -I would also drop PYTHONPATH, which carries SeisComP's python modules; the helper therefore adds
  # $SEISCOMP_ROOT/lib/python to sys.path itself and runs isolated (-I) otherwise.
  sc nice -n 10 python -I "$@"
}
dump_settings_json() {        # $1 = output json, rest = SeisComP command: save '--dump-settings' as JSON
  local out=$1; shift
  echo "+ (SeisComP env) $* --dump-settings > ${out%.json}.txt  (+ JSON)"
  if [[ $APPLY -eq 1 ]]; then
    sc "$@" --dump-settings > "${out%.json}.txt" 2>&1 || true
    py - "${out%.json}.txt" "$out" "$*" <<'EOF'
import json, sys
txt, out, cmd = sys.argv[1:4]
d = {"command": cmd + " --dump-settings", "settings": {}}
for line in open(txt):
    line = line.rstrip("\n")
    if ": " in line:
        k, v = line.split(": ", 1)
        d["settings"][k] = v
    elif line.endswith(":"):
        d["settings"][line[:-1]] = ""
json.dump(d, open(out, "w"), indent=1)
print(f"   {len(d['settings'])} settings -> {out}")
EOF
  fi
}

# --------------------------------------------------------------------------------------------------
# stage master
# --------------------------------------------------------------------------------------------------
stage_master() {
  echo "== stage master: KMA master StationXML from server B (read-only pull)"
  local md5_src md5_alias md5_loc size epoch mtime
  # read-only on server B: md5 of the source (and of the path merged_inventory.xml cites), size, mtime
  echo "+ ssh $SERVER_B md5sum $MASTER_SRC $MASTER_SRC_ALIAS; stat"
  md5_src=$(/usr/bin/timeout 120 ssh -o BatchMode=yes -o ConnectTimeout=10 "$SERVER_B" md5sum "$MASTER_SRC" | cut -d' ' -f1)
  md5_alias=$(/usr/bin/timeout 120 ssh -o BatchMode=yes -o ConnectTimeout=10 "$SERVER_B" md5sum "$MASTER_SRC_ALIAS" | cut -d' ' -f1)
  # (ssh joins its arguments into one remote command line: the format string needs its own quotes)
  read -r size epoch < <(/usr/bin/timeout 60 ssh -o BatchMode=yes -o ConnectTimeout=10 "$SERVER_B" "stat -c '%s %Y' '$MASTER_SRC'")
  mtime=$(date -d "@$epoch" '+%Y-%m-%d %H:%M:%S %Z')
  echo "   server B md5 $md5_src  ($MASTER_SRC; $size bytes, modified $mtime)"
  echo "   server B md5 $md5_alias  ($MASTER_SRC_ALIAS, the path cited in merged_inventory.xml)"
  [[ $md5_src == "$MASTER_MD5_PREFIX"* ]] || { echo "ERROR: server B md5 $md5_src does not start with $MASTER_MD5_PREFIX"; exit 1; }
  if [[ -f $MASTER_XML ]] && [[ $(md5sum "$MASTER_XML" | cut -d' ' -f1) == "$md5_src" ]]; then
    echo "   ok (md5 matches, not fetched again): $MASTER_XML"
  else
    run mkdir -p "$(dirname "$MASTER_XML")"
    # -a keeps the server B modification time; --chmod makes the local copy read-only (it is a reference copy)
    run /usr/bin/timeout 570 rsync -a --chmod=F444 -e "ssh -o BatchMode=yes -o ConnectTimeout=10" "$SERVER_B:$MASTER_SRC" "$MASTER_XML"
  fi
  if [[ $APPLY -eq 1 ]]; then
    md5_loc=$(md5sum "$MASTER_XML" | cut -d' ' -f1)
    echo "   local md5 $md5_loc  $MASTER_XML ($(stat -c %s "$MASTER_XML") bytes)"
    [[ $md5_loc == "$md5_src" ]] || { echo "ERROR: local copy differs from server B"; exit 1; }
    # provenance: append once (the entry names the local file; a re-run with the same md5 adds nothing)
    if grep -q "inventory/KS_KG_metadata_1.0.2.xml.*$md5_loc" "$SUP/PROVENANCE.md"; then
      echo "   PROVENANCE.md already records this file and md5"
    else
      cat >> "$SUP/PROVENANCE.md" <<EOF

## Added $(date '+%Y-%m-%d %H:%M %Z') by install/06_gwangyang_prep.sh (step Prep, stage master)

Copied from server B with \`rsync -a\` (read-only on server B; nothing there was changed). The local copy is made
read-only (mode 444).

| local file | server B source | md5 |
|---|---|---|
| inventory/KS_KG_metadata_1.0.2.xml | $MASTER_SRC (the user's canonical KMA master StationXML, networks KS and KG; $size bytes, modified on server B $mtime) | $md5_loc |

- The path that \`../reference/inventory/merged_inventory.xml\` cites as its "master XML" source,
  $MASTER_SRC_ALIAS, is a symbolic link to the file above on server B
  (md5 $md5_alias, checked by ssh on the same day).
- Used for: the metadata of the 21 SAC channels (7 stations: CGWB, CHRB, YALB, YKDB, YNDB HH; HADA HG;
  KWJU HH) that merged_inventory.xml lacks, when building \`../inputs/stations_rtdd.xml\`.
EOF
      echo "   appended to $SUP/PROVENANCE.md"
    fi
  fi
}

# --------------------------------------------------------------------------------------------------
# stage inventory
# --------------------------------------------------------------------------------------------------
stage_inventory() {
  echo "== stage inventory: inputs/stations_rtdd.xml (+ coordinate changes table)"
  run mkdir -p "$RUN/options"
  run py "$TOOLS/make_stations_rtdd_xml.py" --master "$MASTER_XML" --out "$STATIONS_RTDD" \
      --changes "$COORD_CHANGES" --options-json "$RUN/options/make_stations_rtdd_xml.json"
}

# --------------------------------------------------------------------------------------------------
# stage validate
# --------------------------------------------------------------------------------------------------
stage_validate() {
  echo "== stage validate: obspy read + schema, SAC epoch coverage, NLLGrid lookups"
  run mkdir -p "$RUN/validate" "$RUN/options"
  run py "$TOOLS/check_stations_rtdd_xml.py" --xml "$STATIONS_RTDD" --outdir "$RUN/validate" \
      --options-json "$RUN/options/check_stations_rtdd_xml.json"
}

# --------------------------------------------------------------------------------------------------
# stage scinv
# --------------------------------------------------------------------------------------------------
stage_scinv() {
  echo "== stage scinv: fdsnxml2inv -> inputs/inventory_sc.xml; scinv check / ls; SeisComP-API comparison"
  local D=$RUN/scinv
  run mkdir -p "$D" "$SC_LOCAL" "$RUN/options"
  # conversion, explicitly with --core.plugins=dbsqlite3 (stage globalcfg later makes this the default)
  echo "+ (SeisComP env) fdsnxml2inv --core.plugins=dbsqlite3 -f $STATIONS_RTDD $INVENTORY_SC 2> $D/fdsnxml2inv.log"
  if [[ $APPLY -eq 1 ]]; then
    local rc=0
    sc fdsnxml2inv --core.plugins=dbsqlite3 -f "$STATIONS_RTDD" "$INVENTORY_SC" 2> "$D/fdsnxml2inv.log" || rc=$?
    # fdsnxml2inv marks warnings with a leading "W " and errors with "E "
    echo "   exit code $rc; log: $(grep -c . "$D/fdsnxml2inv.log" || true) lines, $(grep -c -E '^E ' "$D/fdsnxml2inv.log" || true) errors (E), $(grep -c -E '^W ' "$D/fdsnxml2inv.log" || true) warnings (W)"
    # all log lines grouped by text, with the made-up time-stamped resource ids masked, so the kinds of message
    # can be read at a glance
    sed -E 's/[0-9]{14}\.[0-9]+\.[0-9]+/<time-stamped id>/g' "$D/fdsnxml2inv.log" \
      | sort | uniq -c | sort -rn | head -20 | sed 's/^/     /'
    [[ $rc -eq 0 ]] || { echo "ERROR: fdsnxml2inv failed"; exit 1; }
    echo "   $INVENTORY_SC: $(stat -c %s "$INVENTORY_SC") bytes, md5 $(md5sum "$INVENTORY_SC" | cut -d' ' -f1)"
  fi
  dump_settings_json "$RUN/options/fdsnxml2inv_settings.json" fdsnxml2inv --core.plugins=dbsqlite3 -f "$STATIONS_RTDD" "$D/dump_settings_dummy_out.xml"

  # scinv check: default limits, then strict limits; scinv ls at channel level and as NSLC list
  local mode opts
  for mode in default strict; do
    opts=""; [[ $mode == strict ]] && opts=$SCINV_STRICT_OPTS
    echo "+ (SeisComP env) scinv check --core.plugins=dbsqlite3 $opts $INVENTORY_SC > $D/scinv_check_$mode.log 2>&1"
    if [[ $APPLY -eq 1 ]]; then
      local rc=0
      # shellcheck disable=SC2086
      sc scinv check --core.plugins=dbsqlite3 $opts "$INVENTORY_SC" > "$D/scinv_check_$mode.log" 2>&1 || rc=$?
      echo "   scinv check ($mode): exit code $rc, $(grep -c . "$D/scinv_check_$mode.log" || true) output lines"
      sed 's/^/     | /' "$D/scinv_check_$mode.log" | head -60
    fi
  done
  dump_settings_json "$RUN/options/scinv_check_settings.json" scinv check --core.plugins=dbsqlite3 "$INVENTORY_SC"
  run_ls() {                  # $1 = label for the output file name, rest = scinv ls options
    local lvl=$1; shift
    echo "+ (SeisComP env) scinv ls --core.plugins=dbsqlite3 $* $INVENTORY_SC > $D/scinv_ls_$lvl.txt 2> $D/scinv_ls_$lvl.err"
    if [[ $APPLY -eq 1 ]]; then
      sc scinv ls --core.plugins=dbsqlite3 "$@" "$INVENTORY_SC" > "$D/scinv_ls_$lvl.txt" 2> "$D/scinv_ls_$lvl.err" \
        || { echo "ERROR: scinv ls failed"; cat "$D/scinv_ls_$lvl.err"; exit 1; }
      echo "   scinv ls $lvl: $(grep -c . "$D/scinv_ls_$lvl.txt") lines; stderr $(grep -c . "$D/scinv_ls_$lvl.err" || true) lines"
    fi
  }
  run_ls cha --level cha
  run_ls nslc --nslc
  # SeisComP's own Python API reads the converted file: every SensorLocation/Stream vs stations_rtdd.xml and
  # station.csv (coordinates, depth, orientation, sample rate, gain, epochs)
  run sc_py "$TOOLS/check_inventory_sc.py" --scml "$INVENTORY_SC" --stationxml "$STATIONS_RTDD" \
      --station-csv "$STATION_CSV" --outdir "$D" --scinv-ls-nslc "$D/scinv_ls_nslc.txt" \
      --options-json "$RUN/options/check_inventory_sc.json"
}

# --------------------------------------------------------------------------------------------------
# stage globalcfg
# --------------------------------------------------------------------------------------------------
stage_globalcfg() {
  echo "== stage globalcfg: core.plugins = dbsqlite3 in \$SEISCOMP_ROOT/etc/global.cfg"
  local root cfg D=$RUN/globalcfg has_line=0
  root=$(sc printenv SEISCOMP_ROOT)
  cfg=$root/etc/global.cfg
  case "$cfg" in "$PROJECT"/*) ;; *) echo "refusing: $cfg is outside $PROJECT"; exit 2 ;; esac
  run mkdir -p "$D"
  echo "   SEISCOMP_ROOT=$root"
  if [[ -f $cfg ]]; then
    echo "   $cfg exists ($(grep -c . "$cfg") lines); current core.plugins lines:"
    grep -n -E '^\s*core\.plugins' "$cfg" | sed 's/^/     /' || echo "     (none)"
  else
    echo "   $cfg does not exist yet"
  fi
  if [[ -f $cfg ]] && grep -q -E '^\s*core\.plugins\s*=\s*dbsqlite3\s*$' "$cfg"; then
    has_line=1
    echo "   already set: nothing to change"
  elif [[ -f $cfg ]] && grep -q -E '^\s*core\.plugins' "$cfg"; then
    # someone set core.plugins to something else: do not override silently
    echo "ERROR: $cfg already sets core.plugins to another value; decide by hand"; exit 1
  fi

  if [[ $has_line -eq 0 ]]; then
    # before: the failure that motivates the change (fdsnxml2inv without --core.plugins; expected to FAIL)
    echo "+ (SeisComP env) fdsnxml2inv -f $STATIONS_RTDD $D/before.xml 2> $D/fdsnxml2inv_before.log   # expected to fail"
    if [[ $APPLY -eq 1 ]]; then
      local rc0=0
      sc fdsnxml2inv -f "$STATIONS_RTDD" "$D/before.xml" 2> "$D/fdsnxml2inv_before.log" || rc0=$?
      echo "   before the change: exit code $rc0; $(grep -c . "$D/fdsnxml2inv_before.log") log lines:"
      sed 's/^/     | /' "$D/fdsnxml2inv_before.log" | head -5
    fi
    if [[ -f $cfg ]]; then
      run /bin/cp -f -p "$cfg" "$D/global.cfg.before_$(date +%Y%m%d%H%M%S)"   # keep the old file for the record
    fi
    local block header=""
    [[ -f $cfg ]] || header="# global.cfg of this project's own SeisComP installation ($root).
# SeisComP reads it after etc/defaults/global.cfg and before the per-user folder (SEISCOMP_LOCAL_CONFIG), so
# a setting here applies to every SeisComP program of this installation, for every run of this project.
"
    block=$(cat <<EOF
${header}
# --- added $(date '+%Y-%m-%d %H:%M %Z') by install/06_gwangyang_prep.sh (step Prep, stage globalcfg) ---
# etc/defaults/global.cfg loads the MySQL database driver (core.plugins = dbmysql). This build has only
# the SQLite driver (step A), so every SeisComP program that reads the default configuration stopped with
# "Did not find plugin dbmysql". This line replaces the default list (core.plugins overrides, it does not
# add). No database is used by this project; the line only lets the programs start.
core.plugins = dbsqlite3
EOF
)
    echo "+ append to $cfg:"
    printf '%s\n' "$block" | sed 's/^/    | /'
    if [[ $APPLY -eq 1 ]]; then printf '%s\n' "$block" >> "$cfg"; fi
  fi
  if [[ $APPLY -eq 1 ]]; then
    echo "   $cfg now:"; sed 's/^/     | /' "$cfg"
    /bin/cp -f "$cfg" "$D/global.cfg.after"
  fi

  # after: the same conversion and check WITHOUT --core.plugins must work and give the same result. --debug
  # makes fdsnxml2inv log which plugin it loaded (proof that the line in global.cfg is read).
  echo "+ (SeisComP env) fdsnxml2inv --debug -f $STATIONS_RTDD $D/inventory_sc_without_option.xml 2> $D/fdsnxml2inv_without_option.log"
  echo "+ (SeisComP env) scinv check $INVENTORY_SC > $D/scinv_check_without_option.log 2>&1"
  if [[ $APPLY -eq 1 ]]; then
    local rc1=0 rc2=0
    sc fdsnxml2inv --debug -f "$STATIONS_RTDD" "$D/inventory_sc_without_option.xml" 2> "$D/fdsnxml2inv_without_option.log" || rc1=$?
    sc scinv check "$INVENTORY_SC" > "$D/scinv_check_without_option.log" 2>&1 || rc2=$?
    echo "   fdsnxml2inv without --core.plugins: exit code $rc1; plugin lines in its debug log:"
    grep -E 'Trying to open plugin|Plugin .* registered|Did not find plugin' "$D/fdsnxml2inv_without_option.log" | sed 's/^/     | /'
    echo "   scinv check without --core.plugins: exit code $rc2; 'dbmysql' in its output: $(grep -c dbmysql "$D/scinv_check_without_option.log" || true)"
    # the two conversions differ only in the made-up publicIDs that contain the conversion time
    # (step T: "ambiguous resourceId" warnings); compare after masking those
    local n1 n2
    n1=$(sed -E 's/[0-9]{14}\.[0-9]+\.[0-9]+//g' "$INVENTORY_SC" | md5sum | cut -d' ' -f1)
    n2=$(sed -E 's/[0-9]{14}\.[0-9]+\.[0-9]+//g' "$D/inventory_sc_without_option.xml" | md5sum | cut -d' ' -f1)
    echo "   inventory_sc.xml with vs without the option, time-stamped ids masked: md5 $n1 vs $n2 -> $([[ $n1 == "$n2" ]] && echo IDENTICAL || echo DIFFERENT)"
    diff <(sed -E 's/[0-9]{14}\.[0-9]+\.[0-9]+//g' "$INVENTORY_SC") \
         <(sed -E 's/[0-9]{14}\.[0-9]+\.[0-9]+//g' "$D/inventory_sc_without_option.xml") | head -10 | sed 's/^/     /' || true
    if diff "$RUN/scinv/scinv_check_default.log" "$D/scinv_check_without_option.log" > /dev/null; then
      echo "   scinv check output identical to the run with the option"
    else
      echo "   scinv check output differs from the run with the option:"
      diff "$RUN/scinv/scinv_check_default.log" "$D/scinv_check_without_option.log" | head -10 | sed 's/^/     /' || true
    fi
  fi
  dump_settings_json "$RUN/options/scinv_settings_after_globalcfg.json" scinv check "$INVENTORY_SC"
}

# --------------------------------------------------------------------------------------------------
# stage dtables
# --------------------------------------------------------------------------------------------------
stage_dtables() {
  echo "== stage dtables: tidy CSVs of the reference HypoDD dt.cc / dt.ct"
  run mkdir -p "$RUN/dtables" "$RUN/options"
  run py "$TOOLS/make_dt_tables.py" --outdir "$DATA/reference_tables" --summary "$RUN/dtables/dt_tables_summary.json" \
      --options-json "$RUN/options/make_dt_tables.json"
}

# --------------------------------------------------------------------------------------------------
run mkdir -p "$RUN"
case "$STAGE" in
  master)    stage_master ;;
  inventory) stage_inventory ;;
  validate)  stage_validate ;;
  scinv)     stage_scinv ;;
  globalcfg) stage_globalcfg ;;
  dtables)   stage_dtables ;;
  all)       stage_master; stage_inventory; stage_validate; stage_scinv; stage_globalcfg; stage_dtables ;;
esac
echo "   ~/.seiscomp exists: $([[ -e /home/msseo/.seiscomp ]] && echo YES || echo no)"
