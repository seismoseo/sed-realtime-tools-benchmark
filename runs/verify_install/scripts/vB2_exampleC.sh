# vB2_exampleC.sh -- verifier scratch: re-run step B example C (repo regression-test settings) in a verify dir and cmp with the repo reference
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
R=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/src/pyrtdd
source /home/msseo/miniforge3/etc/profile.d/conda.sh
conda activate /home/msseo/miniforge3/envs/pyrtdd
export HOME=$V/home PYTHONDONTWRITEBYTECODE=1
mkdir -p $V/tmp/exampleC && cd $V/tmp/exampleC
python -I /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/03_pyrtdd_test_settings_example.py $R/package/test/py/data > run.log 2>&1; echo "example C exit=$?"
for f in relocated-event.csv relocated-phase.csv relocated-station.csv; do cmp $f $R/package/test/py/data/$f && echo "IDENTICAL $f ($(wc -l < $f) lines)"; done
ls
