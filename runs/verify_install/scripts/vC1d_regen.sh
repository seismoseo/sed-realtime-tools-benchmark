# vC1d_regen.sh -- verifier scratch: regenerate the Gwangyang kim1983 grids in verify_install from the step-C1 recipe and cmp every file
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
G=/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/nll_kim1983
W=$V/tmp/nll_kim1983_regen
mkdir -p $W/run $W/model $W/time
source /home/msseo/miniforge3/etc/profile.d/conda.sh
conda activate /home/msseo/miniforge3/envs/pyrtdd
export HOME=$V/home PYTHONDONTWRITEBYTECODE=1
python -I /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/02_nll_station_list.py /home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/reference $W > $W/station_list.log 2>&1; echo "station list helper exit=$?"
cmp $W/stations.in $G/stations.in && echo "stations.in IDENTICAL"; cmp $W/stations_gridded.csv $G/stations_gridded.csv && echo "stations_gridded.csv IDENTICAL"
conda deactivate
/bin/cp -f $G/run/* $W/run/
export PATH=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/NonLinLoc/bin:$PATH
cd $W
for ph in P S; do nice -n 10 Vel2Grid run/phase$ph.run > v_$ph.log 2>&1 || echo "Vel2Grid $ph FAILED"; done
for ph in P S; do nice -n 10 Grid2Time run/phase$ph.run > g_$ph.log 2>&1 || echo "Grid2Time $ph FAILED"; done
n=0; nd=0; for f in model/* time/*; do n=$((n+1)); cmp -s $f $G/$f || { nd=$((nd+1)); echo "DIFF $f"; }; done
echo "compared $n files, differing: $nd; their file count: $(ls $G/model $G/time | grep -c -E '\.(hdr|buf)$')"
