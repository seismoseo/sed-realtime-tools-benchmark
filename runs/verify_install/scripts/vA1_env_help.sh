# vA1_env_help.sh -- verifier scratch: run inside a fresh login shell; sources env_seiscomp.sh,
# runs --help/--version and python imports with HOME and SEISCOMP_LOCAL_CONFIG redirected to verify_install.
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
export SEISCOMP_LOCAL_CONFIG=$V/seiscomp_user
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
export HOME=$V/home
export ORT_DISABLE_TELEMETRY=1
cd $V/tmp
echo "SEISCOMP_ROOT=$SEISCOMP_ROOT"
echo "CONDA_PREFIX=$CONDA_PREFIX"
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "PYTHONPATH=$PYTHONPATH"
echo "which: $(command -v scautopick) $(command -v scrtdd) $(command -v python) $(command -v timeout)"
python -V
scautopick --help > $V/logs/A1_scautopick_help.txt 2>&1; echo "scautopick --help exit=$?"; head -3 $V/logs/A1_scautopick_help.txt
scrtdd --help > $V/logs/A1_scrtdd_help.txt 2>&1; echo "scrtdd --help exit=$?"; grep -c -- '--' $V/logs/A1_scrtdd_help.txt
scrtdd --version; echo "scrtdd --version exit=$?"
scautopick --version; echo "scautopick --version exit=$?"
msrtsimul --help > $V/logs/A1_msrtsimul_help.txt 2>&1; echo "msrtsimul --help exit=$?"; head -2 $V/logs/A1_msrtsimul_help.txt
python - <<'PY'
import sys, importlib
mods=['seiscomp','seiscomp.core','seiscomp.client','seiscomp.datamodel','seiscomp.io','seiscomp.math','seiscomp.seismology','seiscomp.system','seiscomp.config','seiscomp.logging']
for m in mods:
    mod=importlib.import_module(m)
    print('import OK', m, getattr(mod,'__file__',None))
import seiscomp.core as C, numpy as np
print('framework', C.CurrentVersion.toString())
a=C.DoubleArray(5)
for i in range(5): a.set(i, float(i))
print('numpy view', a.numpy(), type(a.numpy()))
t=C.Time.GMT(); print('Time', t.iso())
print('numpy', np.__version__, np.__file__)
print('sys.path head', sys.path[:4])
PY
echo "py exit=$?"
ls -la $V/home; ls -la $V/seiscomp_user 2>&1
