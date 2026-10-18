# vB_pyrtdd.sh -- verifier scratch: pyrtdd import from another cwd + pytest re-run (no cache, no bytecode, basetemp in verify dir)
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
R=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/src/pyrtdd
source /home/msseo/miniforge3/etc/profile.d/conda.sh
conda activate /home/msseo/miniforge3/envs/pyrtdd
export HOME=$V/home PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=$V/tmp/mpl
echo "PYTHONPATH(login)=$PYTHONPATH"
cd $V/tmp
python -c 'import sys, pyrtdd, pyrtdd.hdd as h; from pyrtdd.obspy import catalog, waveform; print("pyrtdd", pyrtdd.__file__); print("ext", h.hdd_ext.__file__); print("names", [n for n in dir(h) if not n.startswith("_")]); t=h.Homogeneous(5.8,3.36); print("P %.6f S %.6f" % (t.compute(34.99982,127.72852,13.93,35.1027,127.5968,562.0,"P"), t.compute(34.99982,127.72852,13.93,35.1027,127.5968,562.0,"S")))'
echo "import exit=$?"
cd $R
rm -rf /home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install/tmp/pytest_base1 /home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install/tmp/pytest_base2
pytest -q -p no:cacheprovider --basetemp=$V/tmp/pytest_base1 2>&1 | tail -5
echo "pytest -q exit=${PIPESTATUS[0]}"
python $V/scripts/vB_pytest_wrapper.py -q -p no:cacheprovider --basetemp=$V/tmp/pytest_base2 package/test/py 2>&1 | tail -4
