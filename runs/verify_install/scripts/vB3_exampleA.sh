# vB3_exampleA.sh -- verifier scratch: re-run step B example A (README snippet) in verify_install and compare with the reference via their helper
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
R=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/src/pyrtdd/package/test/py/data
I=/home/msseo/works/74.SeisComP_rtDD_DLpicker/install
source /home/msseo/miniforge3/etc/profile.d/conda.sh; conda activate /home/msseo/miniforge3/envs/pyrtdd
export HOME=$V/home PYTHONDONTWRITEBYTECODE=1
mkdir -p $V/tmp/exampleA && cd $V/tmp/exampleA
python -I $I/03_pyrtdd_readme_example.py $R > run.log 2>&1; echo "example A exit=$?"
python -I $I/03_compare_relocated_events.py relocated-event.csv $R/relocated-event.csv $R/starting-event.csv 2>&1 | tail -6
echo "-- their stored A output vs mine:"; cmp relocated-event.csv /home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/pyrtdd_selftest/readme_snippet/relocated-event.csv && echo "IDENTICAL to their run A output"
