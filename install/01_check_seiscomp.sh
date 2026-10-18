#!/usr/bin/env bash
# 01_check_seiscomp.sh -- smoke checks of the SeisComP 7.4.0 build made by 01_build_seiscomp.sh.
#
# In plain words: after compiling we want proof, from a FRESH login shell (nothing left over from
# the build session), that
#   1. the environment file works and SeisComP's tools start (seiscomp, scautopick, scrtdd, msrtsimul)
#   2. SeisComP's Python modules import in the conda Python 3.12 (incl. numpy arrays)
#   3. every program finds all of its libraries in the conda env or in SEISCOMP_ROOT/lib, never
#      some other copy on the system (only glibc itself comes from the system) -- checked once with
#      the library path of the environment file and once with no LD_LIBRARY_PATH at all
#   4. scrtdd's NonLinLoc travel-time plugin and the scdlrtpicker plugin are installed together
#      with their configuration descriptions, and the plugin uses exactly ONNX Runtime 1.31.0
#   5. a real SeisComP program (scautopick) loads the dlrtpicker plugin and can create the four
#      deep-learning pickers DL1C, DL3C (P) and SDL1C, SDL3C (S); as a control, the same picker
#      names must be rejected when the plugin is not loaded
#   6. the unit tests were compiled (only listed with 'ctest -N'; they are RUN in step T)
#   7. nothing was written to ~/.seiscomp
#
# Nothing is installed or changed. Files are written only to runs/01_check_seiscomp/ (small inputs,
# logs of each check) and runs/seiscomp_home/ (SeisComP's per-user folder for these runs).
# No daemon is started, no network port is opened, no database is used.
#
# Usage:  bash 01_check_seiscomp.sh            # DRY RUN: print every check command
#         bash 01_check_seiscomp.sh --apply    # run the checks; appends to logs/01_build_seiscomp_<date>.log
# Exit code: 0 = all checks passed, 1 = at least one check failed (listed in the summary).

set -euo pipefail

# ------------------------------------------------------------------------------------------
# Parameters
# ------------------------------------------------------------------------------------------
PROJECT=/home/msseo/works/74.SeisComP_rtDD_DLpicker
ENV_PREFIX=/home/msseo/miniforge3/envs/seiscomp
SEISCOMP_ROOT=$PROJECT/software/seiscomp
SC_BUILD_DIR=$PROJECT/software/build/seiscomp
SC_SRC_DIR=$PROJECT/software/src/seiscomp
ORT_BUILD_LIB=$PROJECT/software/onnxruntime/onnxruntime-linux-x64-1.31.0/lib/libonnxruntime.so.1.31.0
ENV_SCRIPT=$PROJECT/install/env_seiscomp.sh
IMPORT_HELPER=$PROJECT/install/01_check_seiscomp_imports.py
SC_HOME=$PROJECT/runs/seiscomp_home          # HOME given to SeisComP programs during the checks
CHECK_DIR=$PROJECT/runs/01_check_seiscomp    # inputs + per-check logs
REAL_HOME=/home/msseo                        # only to start a normal login shell (user's profile)

EXPECT_SC=7.4.0
EXPECT_SCRTDD=2.0.10
EXPECT_DLRT=1.1.1
EXPECT_ORT=1.31.0

# programs / libraries whose library resolution is audited (paths relative to SEISCOMP_ROOT)
LDD_TARGETS=(
  bin/scautopick bin/scrtdd bin/scautoloc bin/scevent bin/scamp bin/scmag
  share/plugins/dlrtpicker.so share/plugins/tttnll.so
  lib/libseiscomp_core.so lib/libseiscomp_client.so lib/libhdd.so
  lib/python/seiscomp/_core.so lib/python/seiscomp/_client.so
)
# libraries that may legitimately come from the operating system: glibc itself
GLIBC_RE='^(linux-vdso[.]so[.]1|ld-linux-x86-64[.]so[.]2|libc[.]so[.]6|libm[.]so[.]6|libpthread[.]so[.]0|libdl[.]so[.]2|librt[.]so[.]1|libutil[.]so[.]1)$'   # [.] = a literal dot (awk -v would eat a backslash)

# ------------------------------------------------------------------------------------------
APPLY=0
[[ ${1:-} == --apply ]] && APPLY=1
mkdir -p "$PROJECT/logs"
if [[ $APPLY -eq 1 ]]; then
  LOG=$PROJECT/logs/01_build_seiscomp_$(date +%Y%m%d).log   # same log as the build (step A)
else
  LOG=$PROJECT/logs/01_check_seiscomp_dryrun.log
  : > "$LOG"
fi
exec > >(tee -a "$LOG") 2>&1
ME=$(id -un)

RESULTS=()
result() {   # result "name" PASS|FAIL ["detail"]
  RESULTS+=("$2  $1${3:+  -- $3}")
  echo ">>> $2: $1${3:+  -- $3}"
}
header() { echo; echo "############ $*"; }

# Run a command line in a FRESH login shell: empty environment (env -i), the user's normal login
# profile (bash -l), then our environment file; SeisComP programs get HOME=$SC_HOME so they never
# create ~/.seiscomp. Prints the exact command first.
fresh() {
  local cmd="source $ENV_SCRIPT && export HOME=$SC_HOME && cd $CHECK_DIR && $1"
  echo "+ env -i HOME=$REAL_HOME USER=$ME LOGNAME=$ME TERM=dumb PATH=/usr/bin:/bin bash -lc $(printf '%q' "$cmd")"
  [[ $APPLY -eq 1 ]] || return 0
  env -i HOME="$REAL_HOME" USER="$ME" LOGNAME="$ME" TERM=dumb PATH=/usr/bin:/bin bash -lc "$cmd"
}

writefile() {   # writefile PATH CONTENT -- small input files of the checks
  echo "+ write $1:"
  printf '%s\n' "$2" | sed 's/^/      | /'
  [[ $APPLY -eq 1 ]] && printf '%s\n' "$2" > "$1"
  return 0
}

echo "=================================================================================="
echo "== 01_check_seiscomp.sh  $(date '+%F %T %Z')  host=$(hostname -s)  APPLY=$APPLY"
echo "=================================================================================="
echo "+ mkdir -p $CHECK_DIR $SC_HOME"
[[ $APPLY -eq 1 ]] && mkdir -p "$CHECK_DIR" "$SC_HOME"
HOME_SC_BEFORE=no; [[ -e $REAL_HOME/.seiscomp ]] && HOME_SC_BEFORE=yes
echo "   ~/.seiscomp exists before the checks: $HOME_SC_BEFORE"

# ------------------------------------------------------------------------------------------
header "1. environment file + 'seiscomp print env' in a fresh login shell"
rc=0; out=$(fresh 'echo "SEISCOMP_ROOT=$SEISCOMP_ROOT"; echo "SEISCOMP_LOCAL_CONFIG=$SEISCOMP_LOCAL_CONFIG"; echo "CONDA_PREFIX=$CONDA_PREFIX"; echo "python=$(command -v python) ($(python -V 2>&1))"; seiscomp print env' 2>&1) || rc=$?
echo "$out"
if [[ $APPLY -eq 1 ]]; then
  if [[ $rc -eq 0 && $out == *"SEISCOMP_ROOT=$SEISCOMP_ROOT"* && $out == *"python=$ENV_PREFIX/bin/python (Python 3.12"* ]]; then
    result "env_seiscomp.sh + seiscomp print env" PASS
  else result "env_seiscomp.sh + seiscomp print env" FAIL "exit $rc"; fi
fi

# ------------------------------------------------------------------------------------------
header "2. scautopick --help, scrtdd --help / --version, msrtsimul --help"
rc=0; out=$(fresh 'scautopick --help > scautopick_help.txt 2>&1; a=$?; head -4 scautopick_help.txt; scrtdd --help > scrtdd_help.txt 2>&1; b=$?; grep -E -- "--reloc-catalog|--origin-id|--ep " scrtdd_help.txt; scrtdd --version; c=$?; msrtsimul --help > msrtsimul_help.txt 2>&1; d=$?; head -3 msrtsimul_help.txt; echo "exit codes: scautopick --help=$a scrtdd --help=$b scrtdd --version=$c msrtsimul --help=$d"; exit $((a+b+c+d))' 2>&1) || rc=$?
echo "$out"
if [[ $APPLY -eq 1 ]]; then
  if [[ $rc -eq 0 && $out == *"scrtdd: $EXPECT_SCRTDD"* && $out == *"Framework: $EXPECT_SC Release"* ]]; then
    result "scautopick/scrtdd/msrtsimul start; scrtdd $EXPECT_SCRTDD on SeisComP $EXPECT_SC" PASS
  else result "scautopick/scrtdd/msrtsimul start" FAIL "exit $rc"; fi
fi

# ------------------------------------------------------------------------------------------
header "3. Python: import seiscomp.* in the conda Python (helper $(basename "$IMPORT_HELPER"))"
rc=0; out=$(fresh "python $IMPORT_HELPER" 2>&1) || rc=$?
echo "$out"
if [[ $APPLY -eq 1 ]]; then
  if [[ $rc -eq 0 && $out == *"python        : $ENV_PREFIX/bin/python"* && $out == *"framework     : $EXPECT_SC"* ]]; then
    result "python import seiscomp.core/client/datamodel/... (+numpy)" PASS
  else result "python import seiscomp.*" FAIL "exit $rc"; fi
fi

# ------------------------------------------------------------------------------------------
header "4. installed plugins, descriptions and models"
echo "+ ls $SEISCOMP_ROOT/share/plugins; test -e <each expected file>; ls <models dir>/*.onnx | wc -l"
if [[ $APPLY -eq 1 ]]; then
  ls "$SEISCOMP_ROOT/share/plugins" | tr '\n' ' '; echo
  missing=()
  for f in share/plugins/dlrtpicker.so share/plugins/tttnll.so \
           etc/descriptions/global_dlrtpicker.xml etc/descriptions/scrtdd.xml \
           etc/descriptions/global_nllttt.xml bin/scrtdd bin/msrtsimul; do
    if [[ -e $SEISCOMP_ROOT/$f ]]; then echo "   present: $f"; else echo "   MISSING: $f"; missing+=("$f"); fi
  done
  nmodels=$(ls "$SC_SRC_DIR/src/extras/scdlrtpicker/models/"*.onnx | wc -l)
  echo "   scdlrtpicker models (.onnx) in $SC_SRC_DIR/src/extras/scdlrtpicker/models: $nmodels"
  if [[ ${#missing[@]} -eq 0 && $nmodels -eq 49 ]]; then
    result "dlrtpicker.so, tttnll.so, global_dlrtpicker.xml, scrtdd.xml, global_nllttt.xml, msrtsimul, 49 models" PASS
  else result "plugins/descriptions/models" FAIL "missing: ${missing[*]:-none}; models=$nmodels"; fi
fi

# ------------------------------------------------------------------------------------------
header "5. ONNX Runtime used by the plugin = the release it was compiled against ($EXPECT_ORT)"
echo "+ readelf -V $SEISCOMP_ROOT/share/plugins/dlrtpicker.so | grep -A1 'File: libonnxruntime'"
echo "+ readlink -f $SEISCOMP_ROOT/lib/libonnxruntime.so.1"
echo "+ sha256sum <that file> $ORT_BUILD_LIB"
if [[ $APPLY -eq 1 ]]; then
  vers=$(readelf -V "$SEISCOMP_ROOT/share/plugins/dlrtpicker.so" | grep -A1 'File: libonnxruntime' | grep -o 'VERS_[0-9.]*' || true)
  echo "   symbol version required by the plugin: ${vers:-none}"
  target=$(readlink -f "$SEISCOMP_ROOT/lib/libonnxruntime.so.1" || true)
  echo "   libonnxruntime.so.1 -> $target"
  s1=$(sha256sum "$target" | cut -d' ' -f1); s2=$(sha256sum "$ORT_BUILD_LIB" | cut -d' ' -f1)
  echo "   $s1  $target"; echo "   $s2  $ORT_BUILD_LIB"
  if [[ $vers == "VERS_$EXPECT_ORT" && $target == *"/lib/onnxruntime-linux-x64-$EXPECT_ORT/lib/libonnxruntime.so.$EXPECT_ORT" && $s1 == "$s2" ]]; then
    result "plugin needs VERS_$EXPECT_ORT; libonnxruntime.so.1 -> byte-identical $EXPECT_ORT release" PASS
  else result "ONNX Runtime version consistency" FAIL "vers=$vers target=$target"; fi
fi

# ------------------------------------------------------------------------------------------
header "6. library resolution (ldd): only SEISCOMP_ROOT/lib, the conda env lib, or glibc"
echo "+ readelf -d <file> | grep RPATH   (search path written into the installed files; a DT_RPATH"
echo "  of a program also applies to the plugins it loads, a DT_RUNPATH would not)"
if [[ $APPLY -eq 1 ]]; then
  for t in bin/scautopick share/plugins/dlrtpicker.so lib/libseiscomp_core.so; do
    echo "   $t: $(readelf -d "$SEISCOMP_ROOT/$t" | grep -E '\((RPATH|RUNPATH)\)' | sed 's/^ *0x[0-9a-f]* *//')"
  done
fi
# (a) as a user gets it: fresh login shell + environment file
rc=0; fresh "for t in ${LDD_TARGETS[*]}; do ldd \$SEISCOMP_ROOT/\$t > ldd_env_\$(basename \$t).txt 2>&1 || echo \"ldd failed: \$t\"; done; echo \"LD_LIBRARY_PATH=\$LD_LIBRARY_PATH\"" || rc=$?
# (b) strictest: no LD_LIBRARY_PATH at all, only what is written into the files
echo "+ for t in ${LDD_TARGETS[*]}; do env -u LD_LIBRARY_PATH ldd \$SEISCOMP_ROOT/\$t > ldd_rpath_<name>.txt; done"
if [[ $APPLY -eq 1 ]]; then
  for t in "${LDD_TARGETS[@]}"; do
    env -u LD_LIBRARY_PATH ldd "$SEISCOMP_ROOT/$t" > "$CHECK_DIR/ldd_rpath_$(basename "$t").txt" 2>&1 || echo "ldd failed: $t"
  done
  bad=0
  for mode in env rpath; do
    if [[ $mode == env ]]; then echo "   -- (a) fresh login shell + env_seiscomp.sh"; else echo "   -- (b) LD_LIBRARY_PATH unset (only the RPATH in the files)"; fi
    for t in "${LDD_TARGETS[@]}"; do
      f=$CHECK_DIR/ldd_${mode}_$(basename "$t").txt
      line=$(awk -v R="$SEISCOMP_ROOT/lib/" -v E="$ENV_PREFIX/lib/" -v G="$GLIBC_RE" '
        $2=="=>" { n++
          if ($3=="not") { bad++; list=list " NOTFOUND:" $1; next }
          if (index($3,R)==1) { r++; next }
          if (index($3,E)==1) { e++; next }
          if ($1 ~ G) { g++; next }
          bad++; list=list " OTHER:" $1 "->" $3 }
        END { printf "%d libs: %d SEISCOMP_ROOT/lib, %d conda, %d glibc, %d bad%s", n, r, e, g, bad, list }' "$f")
      echo "      $t: $line"
      [[ $line == *" 0 bad" ]] || bad=$((bad+1))
    done
  done
  if [[ $rc -eq 0 && $bad -eq 0 ]]; then
    result "ldd of ${#LDD_TARGETS[@]} files x 2 modes: no 'not found', nothing from outside conda/SEISCOMP_ROOT except glibc" PASS
  else result "ldd library resolution" FAIL "$bad file/mode combinations with problems"; fi
fi

# ------------------------------------------------------------------------------------------
header "7. scautopick loads the dlrtpicker plugin and creates DL1C/DL3C/SDL1C/SDL3C"
# scautopick checks its configured pickers right after start-up (picker.cpp, App::init):
#   picker  -> "Picker 'X' is not available, abort application" if X is not registered
#   spicker -> "Unknown secondary picker: X"                    if X is not registered
# Only after both checks does it look for stations; with the empty inventory used here it then
# stops with "No stations added ... nothing to do" (exit code 1, expected). Reaching that message
# therefore proves that both pickers were created. No messaging, no database (--offline, XML
# inventory/config), no waveforms (empty miniSEED file), no model needed for creating a picker.
SCX='<?xml version="1.0" encoding="UTF-8"?>'
NS='http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.14'
writefile "$CHECK_DIR/inventory_empty.xml" "$SCX
<seiscomp xmlns=\"$NS\" version=\"0.14\">
  <Inventory/>
</seiscomp>"
writefile "$CHECK_DIR/config_empty.xml" "$SCX
<seiscomp xmlns=\"$NS\" version=\"0.14\">
  <Config/>
</seiscomp>"
echo "+ : > $CHECK_DIR/empty.mseed"
[[ $APPLY -eq 1 ]] && : > "$CHECK_DIR/empty.mseed"
writefile "$CHECK_DIR/no_plugin_DL3C.cfg"   "picker = DL3C"
writefile "$CHECK_DIR/no_plugin_DL1C.cfg"   "picker = DL1C"
writefile "$CHECK_DIR/no_plugin_SDL3C.cfg"  "spicker = SDL3C"
writefile "$CHECK_DIR/no_plugin_SDL1C.cfg"  "spicker = SDL1C"
writefile "$CHECK_DIR/plugin_DL3C_SDL3C.cfg" "plugins = dlrtpicker
picker = DL3C
spicker = SDL3C"
writefile "$CHECK_DIR/plugin_DL1C_SDL1C.cfg" "plugins = dlrtpicker
picker = DL1C
spicker = SDL1C"
SCAP_ARGS="--offline --playback --inventory-db $CHECK_DIR/inventory_empty.xml --config-db $CHECK_DIR/config_empty.xml -I file://$CHECK_DIR/empty.mseed --debug"
for case in no_plugin_DL3C no_plugin_DL1C no_plugin_SDL3C no_plugin_SDL1C plugin_DL3C_SDL3C plugin_DL1C_SDL1C; do
  echo "   -- case $case"
  rc=0; fresh "/usr/bin/timeout 120 scautopick --config-file $CHECK_DIR/$case.cfg $SCAP_ARGS > $case.log 2>&1; echo \"exit code \$?\"; grep -E 'Trying to open plugin|registered|description:|version:|not available|Unknown|No stations added' $case.log" || rc=$?
  [[ $APPLY -eq 1 ]] || continue
  logf=$CHECK_DIR/$case.log
  if [[ $case == no_plugin_* ]]; then
    name=${case#no_plugin_}
    if grep -q -E "Picker '$name' is not available|Unknown secondary picker: $name" "$logf"; then
      result "control without plugin: '$name' rejected" PASS
    else result "control without plugin: '$name' rejected" FAIL "see $logf"; fi
  else
    if grep -q 'Plugin dlrtpicker registered' "$logf" && grep -q "version: $EXPECT_DLRT" "$logf" \
       && grep -q 'No stations added' "$logf" \
       && ! grep -q -E 'not available|Unknown picker|Unknown secondary picker' "$logf"; then
      result "with plugin dlrtpicker $EXPECT_DLRT: ${case#plugin_} created by scautopick" PASS
    else result "with plugin: ${case#plugin_}" FAIL "see $logf"; fi
  fi
done

# ------------------------------------------------------------------------------------------
header "8. unit tests compiled (listing only; they are run in step T)"
rc=0; out=$(fresh "cd $SC_BUILD_DIR && ctest -N | tail -5 && echo \"scrtdd libhdd tests: \$(ctest -N | grep -c test_hdd_)\"" 2>&1) || rc=$?
echo "$out"
if [[ $APPLY -eq 1 ]]; then
  if [[ $rc -eq 0 && $out =~ Total\ Tests:\ ([0-9]+) && ${BASH_REMATCH[1]} -gt 0 && $out =~ libhdd\ tests:\ ([1-9][0-9]*) ]]; then
    result "ctest -N lists the unit tests incl. scrtdd's test_hdd_*" PASS
  else result "ctest -N" FAIL "exit $rc"; fi
fi

# ------------------------------------------------------------------------------------------
header "9. ~/.seiscomp untouched"
echo "+ test ! -e $REAL_HOME/.seiscomp"
if [[ $APPLY -eq 1 ]]; then
  if [[ -e $REAL_HOME/.seiscomp ]]; then
    echo "   $REAL_HOME/.seiscomp EXISTS (before the checks: $HOME_SC_BEFORE)"
    result "~/.seiscomp does not exist" FAIL
  else
    echo "   $REAL_HOME/.seiscomp does not exist; per-user folder used by these runs: $(ls -d "$SC_HOME"/.seiscomp 2>/dev/null || echo none)"
    result "~/.seiscomp does not exist" PASS
  fi
fi

# ------------------------------------------------------------------------------------------
echo
echo "############ SUMMARY ($(date '+%F %T'))"
if [[ $APPLY -eq 0 ]]; then echo "   dry run: no checks executed"; exit 0; fi
nfail=0
for r in "${RESULTS[@]}"; do echo "   $r"; [[ $r == FAIL* ]] && nfail=$((nfail+1)); done
echo "   ${#RESULTS[@]} checks, $nfail failed"
[[ $nfail -eq 0 ]]
