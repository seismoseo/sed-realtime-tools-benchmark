#!/usr/bin/env bash
# 02_build_nonlinloc.sh -- step C1: NonLinLoc + travel-time grids of the HypoDD velocity model (Gwangyang benchmark).
#
# Why NonLinLoc at all: scrtdd/pyrtdd can read travel times from NonLinLoc grid files ("NLLGrid" model).
# Unlike SeisComP's LOCSAT/libtau tables, NLL grids honour station elevation and allow events above sea
# level, which matters for a local network (stations up to 698 m high, events at ~14 km).
#
# Three stages, run in this order by default:
#   build    : clone NonLinLoc at its newest release tag, compile it with CMake inside conda env 'seiscomp'
#              (no system compiler on Server A), copy the programs to software/NonLinLoc/bin, and smoke-test
#              Vel2Grid + Grid2Time by re-creating one of scrtdd's own test grid sets
#              (iasp91, 2-D, azimuthal equidistant; recipe pinned to scrtdd release v2.0.10).
#   grids    : write the NonLinLoc control files for the HypoDD model 'kim1983' and run Vel2Grid/Grid2Time:
#              one 2-D travel-time grid and one 2-D take-off-angle grid per station and phase (P, S).
#   validate : independent checks in conda env 'pyrtdd' (python helper 02_validate_nll_grids.py):
#              grid times vs an exact 1-D layered-model calculation, vs observed PhaseNet+ travel times,
#              take-off angles, the station-location round trip that scrtdd uses to find a grid, and
#              whether the coordinates in reference/inventory/merged_inventory.xml would find the grids.
#
# Usage:  bash 02_build_nonlinloc.sh                       # dry run: print every action, change nothing
#         bash 02_build_nonlinloc.sh --apply               # do all three stages
#         bash 02_build_nonlinloc.sh --apply --stage grids # one stage only: build | grids | validate | all
#
# Everything is written inside the project folder; nothing outside it (and nothing in other conda envs)
# is touched. In --apply mode all output is appended to the log file below.

set -euo pipefail

# --------------------------------------------------------------------------------------------------
# parameters (everything that defines the result is here)
# --------------------------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
CONDA_BASE=/home/msseo/miniforge3
BUILD_ENV=$CONDA_BASE/envs/seiscomp          # gcc 13 / cmake 3.31 / make (Server A has no system compiler)
PY_ENV=$CONDA_BASE/envs/pyrtdd               # numpy / pandas / obspy / pyproj for the python helpers

NLL_REPO=https://github.com/alomax/NonLinLoc
NLL_TAG=v7.00.16-beta                        # newest (and only) release tag on 2026-10-17 (published 2023-06-16)
NLL_TAG_COMMIT=4bb22a7cc607355e158540506b859d582bd67d14   # commit the tag pointed to when this was written
SRC_DIR=$PROJECT/software/src/NonLinLoc
BUILD_DIR=$PROJECT/software/build/NonLinLoc
NLL_HOME=$PROJECT/software/NonLinLoc         # programs go to $NLL_HOME/bin
JOBS=8                                       # Server A is shared: small C code, -j8 is plenty

# scrtdd's own NonLinLoc test-grid recipe (used as the smoke test of the freshly built programs)
SCRTDD_RECIPE_URL=https://raw.githubusercontent.com/swiss-seismological-service/scrtdd/v2.0.10/libs/hdd/test/data/nll
SMOKE_ROOT=$NLL_HOME/smoke_test                       # mirrors scrtdd's libs/hdd/test/data/nll
SMOKE_DIR=$SMOKE_ROOT/iasp91_2D_azimuthal_equidist

# Gwangyang grids
REF_DIR=$PROJECT/data/gwangyang_11ev/reference          # read-only benchmark copy
GRID_DIR=$PROJECT/data/gwangyang_11ev/inputs/nll_kim1983
MODEL=kim1983                                           # grid file prefix = 'gridModel' for scrtdd/pyrtdd

# Map projection. TRANS_MERC (ellipsoidal transverse Mercator, WGS-84) centred on the cluster centroid.
# Chosen over AZIMUTHAL_EQUIDIST / SIMPLE because NonLinLoc's AZIMUTHAL_EQUIDIST is a SPHERICAL projection
# with the ellipsoid's equatorial radius (6378.137 km) and SIMPLE uses a 6371 km sphere: for our stations
# they misplace the cluster-station distance by up to 331 m / 313 m (= up to 55 ms P, 96 ms S), while
# TRANS_MERC stays within ~3.4 m (< 1 ms). All three are supported by scrtdd's libs/hdd/nll/grid.cpp.
# Syntax: TRANS TRANS_MERC refEllipsoid latOrig longOrig rotAngle  (no false easting, scale factor 1)
TRANS_LINE="TRANS TRANS_MERC WGS-84 35.0000 127.7286 0.0"

# 2-D grid (NonLinLoc needs num_grid_x = 2 for the 2-D velocity grid; y = horizontal distance from the
# station, z = depth). 0.1 km cubic cells: distance 0..120 km (1201 nodes; stations are <= 99.3 km from
# the cluster), depth -3.0..50.0 km (531 nodes; highest station at -0.698 km, Moho at 32 km).
# Origin -3.0 km and spacing 0.1 km put the layer boundaries (15 and 32 km) exactly on cell boundaries
# (Vel2Grid samples the model at cell centres), so the interfaces are not shifted.
VGGRID_LINE="VGGRID 2 1201 531 0.0 0.0 -3.0 0.1 0.1 0.1 SLOW_LEN"

# HypoDD model 'kim1983' (reference/gwangyang_pnplus/2.HypoDD/02.dt.cc/hypoDD.inp): tops 0, 15, 32 km,
# Vp 5.98, 6.38, 7.95 km/s, Vp/Vs 1.73 -> Vs = Vp/1.73 (6 decimals). The top layer starts at -5 km instead
# of 0 km so that stations above sea level sit inside it (as in scrtdd's test recipe).
# LAYER depth Vp_top Vp_grad Vs_top Vs_grad rho_top rho_grad   (density is not used for travel times)
LAYER_LINES=(
  "LAYER  -5.0  5.98 0.0  3.456647 0.0  2.70 0.0"
  "LAYER  15.0  6.38 0.0  3.687861 0.0  2.70 0.0"
  "LAYER  32.0  7.95 0.0  4.595376 0.0  2.70 0.0"
)

LOG=$PROJECT/logs/02_build_nonlinloc_$(date +%Y%m%d).log

# --------------------------------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------------------------------
APPLY=0
STAGE=all
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --stage) STAGE=${2:?--stage needs build, grids, validate or all}; shift 2 ;;
    *) echo "unknown argument: $1"; exit 2 ;;
  esac
done
case "$STAGE" in build|grids|validate|all) ;; *) echo "bad --stage $STAGE"; exit 2 ;; esac

if [[ $APPLY -eq 1 ]]; then
  mkdir -p "$(dirname "$LOG")"
  exec > >(tee -a "$LOG") 2>&1          # keep a full record of what was done
fi
echo "==== 02_build_nonlinloc.sh  $(date '+%Y-%m-%d %H:%M:%S %Z')  host $(hostname -s)  APPLY=$APPLY  STAGE=$STAGE"
trap 'echo "==== 02_build_nonlinloc.sh finished with exit code $? ($(date +%H:%M:%S))"' EXIT

# --------------------------------------------------------------------------------------------------
# helpers: every action is printed; only executed with --apply
# --------------------------------------------------------------------------------------------------
run() {                       # run a command
  echo "+ $*"
  if [[ $APPLY -eq 1 ]]; then "$@"; fi
}
run_in() {                    # run a command inside a directory (NonLinLoc resolves INCLUDE paths from the cwd)
  local dir=$1; shift
  echo "+ (cd $dir && $*)"
  if [[ $APPLY -eq 1 ]]; then (cd "$dir" && "$@"); fi
}
write_file() {                # write stdin to a file; the content is always shown
  local file=$1 content
  content=$(cat)
  echo "+ write $file"
  printf '%s\n' "$content" | sed 's/^/    | /'
  if [[ $APPLY -eq 1 ]]; then printf '%s\n' "$content" > "$file"; fi
}
activate() {                  # conda activation scripts are not 'set -u' safe
  set +u
  source "$CONDA_BASE/etc/profile.d/conda.sh"
  conda activate "$1"
  set -u
}
py_run() {                    # run a python helper in env pyrtdd (subshell, so the build env stays active)
  echo "+ (env pyrtdd) python $*"
  if [[ $APPLY -eq 1 ]]; then ( activate "$PY_ENV"; python -u "$@" ); fi
}

# --------------------------------------------------------------------------------------------------
# stage build
# --------------------------------------------------------------------------------------------------
stage_build() {
  echo "== stage build: NonLinLoc $NLL_TAG"
  activate "$BUILD_ENV"
  echo "   compiler: CC=$CC ($($CC --version | head -1)); $(cmake --version | head -1); $(git --version)"

  # 1) source: a shallow clone of exactly the release tag; refuse to continue if the tag moved
  if [[ -d $SRC_DIR/.git ]]; then
    echo "   source already cloned in $SRC_DIR (not re-cloning)"
  else
    run mkdir -p "$(dirname "$SRC_DIR")"
    run git clone --depth 1 --branch "$NLL_TAG" "$NLL_REPO" "$SRC_DIR"
  fi
  if [[ $APPLY -eq 1 ]]; then
    local head; head=$(git -C "$SRC_DIR" rev-parse HEAD)
    echo "   checked-out commit: $head ($(git -C "$SRC_DIR" log -1 --format=%cd --date=iso))"
    if [[ $head != "$NLL_TAG_COMMIT" ]]; then
      echo "!! $NLL_TAG now points to $head, not $NLL_TAG_COMMIT -- check the release before continuing"; exit 1
    fi
  fi

  # 2) configure + compile. The project's CMakeLists.txt lives in src/; it forces a Release build,
  #    adds -fcommon (needed by GCC >= 10) and writes the programs to $SRC_DIR/src/bin (hard-coded there).
  run cmake -S "$SRC_DIR/src" -B "$BUILD_DIR" -DCMAKE_C_COMPILER="$CC"
  run nice -n 10 make -C "$BUILD_DIR" -j"$JOBS"

  # 3) install = copy the programs to one bin directory that later steps put on PATH
  run mkdir -p "$NLL_HOME/bin"
  run /bin/cp -f "$SRC_DIR"/src/bin/* "$NLL_HOME/bin/"
  if [[ $APPLY -eq 1 ]]; then
    {
      echo "NonLinLoc $NLL_TAG  commit $(git -C "$SRC_DIR" rev-parse HEAD)  from $NLL_REPO"
      echo "built $(date '+%Y-%m-%d %H:%M %Z') on $(hostname -s) by install/02_build_nonlinloc.sh"
      echo "compiler: $($CC --version | head -1)"
    } > "$NLL_HOME/VERSION.txt"
    echo "   installed programs: $(ls "$NLL_HOME/bin" | tr '\n' ' ')"
  fi

  # 4) smoke test: re-create scrtdd's own test grids (iasp91_2D_azimuthal_equidist) with our programs.
  #    Same 4 commands as that folder's generate.sh (run explicitly, the downloaded script is not executed).
  run mkdir -p "$SMOKE_DIR/run" "$SMOKE_DIR/model" "$SMOKE_DIR/time"
  run curl -sSfL -o "$SMOKE_ROOT/stations.in" "$SCRTDD_RECIPE_URL/stations.in"   # the recipe includes ../stations.in
  local f
  for f in general.in Vel2Grid.in Grid2Time.in phaseP.run phaseS.run; do
    run curl -sSfL -o "$SMOKE_DIR/run/$f" "$SCRTDD_RECIPE_URL/iasp91_2D_azimuthal_equidist/run/$f"
  done
  run_in "$SMOKE_DIR" nice -n 10 "$NLL_HOME/bin/Vel2Grid" run/phaseP.run
  run_in "$SMOKE_DIR" nice -n 10 "$NLL_HOME/bin/Vel2Grid" run/phaseS.run
  run_in "$SMOKE_DIR" nice -n 10 "$NLL_HOME/bin/Grid2Time" run/phaseP.run
  run_in "$SMOKE_DIR" nice -n 10 "$NLL_HOME/bin/Grid2Time" run/phaseS.run
  if [[ $APPLY -eq 1 ]]; then
    local nt na nm
    nt=$(ls "$SMOKE_DIR"/time/*.time.hdr | wc -l); na=$(ls "$SMOKE_DIR"/time/*.angle.hdr | wc -l)
    nm=$(ls "$SMOKE_DIR"/time/*.mod.hdr 2>/dev/null | wc -l)
    echo "   smoke test: $nt time grids, $na angle grids, $nm model grids in time/ (expected 32, 32, 2)"
    echo "   example header $SMOKE_DIR/time/iasp91.P.N1_ST01A.time.hdr:"
    sed 's/^/    | /' "$SMOKE_DIR/time/iasp91.P.N1_ST01A.time.hdr"
    [[ $nt -eq 32 && $na -eq 32 && $nm -eq 2 ]] || { echo "!! smoke test FAILED"; exit 1; }
    echo "   smoke test PASSED"
  fi
}

# --------------------------------------------------------------------------------------------------
# stage grids
# --------------------------------------------------------------------------------------------------
stage_grids() {
  echo "== stage grids: model $MODEL -> $GRID_DIR"
  # never mix grids of two runs: scrtdd loads every *.time.hdr in the folder
  if [[ $APPLY -eq 1 ]] && compgen -G "$GRID_DIR/time/*.hdr" > /dev/null; then
    echo "!! $GRID_DIR/time already contains grids. Remove the old grids first, e.g."
    echo "!!   rm -rf $GRID_DIR/model $GRID_DIR/time"
    exit 1
  fi
  run mkdir -p "$GRID_DIR/run" "$GRID_DIR/model" "$GRID_DIR/time"

  # station list (union of the three benchmark station lists; coordinates from used_stations_100km.csv)
  py_run "$PROJECT/install/02_nll_station_list.py" "$REF_DIR" "$GRID_DIR"

  # control files, same layout as scrtdd's recipe (run/*.in included from run/phase{P,S}.run)
  write_file "$GRID_DIR/run/general.in" <<EOF
# Generic NonLinLoc control statements (written by install/02_build_nonlinloc.sh)
# CONTROL message_flag random_seed   (values as in scrtdd's test recipe)
CONTROL 1 99991
# TRANS TRANS_MERC refEllipsoid latOrig longOrig rotAngle : ellipsoidal transverse Mercator centred on the
# Gwangyang cluster (see the script header for why not AZIMUTHAL_EQUIDIST / SIMPLE)
$TRANS_LINE
EOF

  write_file "$GRID_DIR/run/Vel2Grid.in" <<EOF
# Vel2Grid control statements: HypoDD model kim1983 on a 2-D grid
VGOUT  ./model/$MODEL
# VGGRID num_x num_y num_z  orig_x orig_y orig_z  dx dy dz  type   (num_x = 2 for 2-D grids)
$VGGRID_LINE
# LAYER depth Vp_top Vp_grad Vs_top Vs_grad rho_top rho_grad   (Vs = Vp/1.73; top layer extended to -5 km)
$(printf '%s\n' "${LAYER_LINES[@]}")
EOF

  write_file "$GRID_DIR/run/Grid2Time.in" <<EOF
# Grid2Time control statements: 2-D time grids plus take-off-angle grids (needed by scrtdd/pyrtdd)
GTMODE GRID2D ANGLES_YES
# Podvin & Lecomte finite-difference eikonal solver: hs_eps_init message_flag (as in scrtdd's recipe)
GT_PLFD  1.0e-3  0
EOF

  local ph
  for ph in P S; do
    write_file "$GRID_DIR/run/phase$ph.run" <<EOF
# $ph-wave grids (written by install/02_build_nonlinloc.sh); run from $GRID_DIR:
#   Vel2Grid run/phase$ph.run ; Grid2Time run/phase$ph.run
VGTYPE $ph
# GTFILES <input file root> <output file root> wave_type
GTFILES  ./model/$MODEL  ./time/$MODEL $ph
INCLUDE stations.in
INCLUDE run/general.in
INCLUDE run/Vel2Grid.in
INCLUDE run/Grid2Time.in
EOF
  done

  activate "$BUILD_ENV"
  for ph in P S; do run_in "$GRID_DIR" nice -n 10 "$NLL_HOME/bin/Vel2Grid" "run/phase$ph.run"; done
  for ph in P S; do run_in "$GRID_DIR" nice -n 10 "$NLL_HOME/bin/Grid2Time" "run/phase$ph.run"; done

  if [[ $APPLY -eq 1 ]]; then
    local ns nt na nm
    ns=$(grep -c '^GTSRCE' "$GRID_DIR/stations.in")
    nt=$(ls "$GRID_DIR"/time/$MODEL.*.time.hdr | wc -l); na=$(ls "$GRID_DIR"/time/$MODEL.*.angle.hdr | wc -l)
    nm=$(ls "$GRID_DIR"/time/$MODEL.*.mod.hdr | wc -l)
    echo "   $ns stations -> $nt time grids, $na angle grids, $nm model grids in time/ (expected $((2*ns)), $((2*ns)), 2)"
    echo "   disk use: $(du -sh "$GRID_DIR" | cut -f1)"
    echo "   example header $GRID_DIR/time/$MODEL.P.BAU.time.hdr:"
    sed 's/^/    | /' "$GRID_DIR/time/$MODEL.P.BAU.time.hdr"
    [[ $nt -eq $((2*ns)) && $na -eq $((2*ns)) && $nm -eq 2 ]] || { echo "!! grid count check FAILED"; exit 1; }
    echo "   for pyrtdd: NLLGrid(gridPath='$GRID_DIR/time', gridModel='$MODEL')"
    echo "   for scrtdd in SeisComP: plugin tttnll; ttt.NLLGrid.tables = $MODEL;"
    echo "     ttt.NLLGrid.$MODEL.tablePath = $GRID_DIR/time/$MODEL (directory + model name in one value)"
  fi
}

# --------------------------------------------------------------------------------------------------
# stage validate
# --------------------------------------------------------------------------------------------------
stage_validate() {
  echo "== stage validate"
  py_run "$PROJECT/install/02_validate_nll_grids.py" "$REF_DIR" "$GRID_DIR" "$MODEL"
}

case "$STAGE" in
  build)    stage_build ;;
  grids)    stage_grids ;;
  validate) stage_validate ;;
  all)      stage_build; stage_grids; stage_validate ;;
esac
