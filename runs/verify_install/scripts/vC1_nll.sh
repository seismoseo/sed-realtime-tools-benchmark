# vC1_nll.sh -- verifier scratch: run the installed NonLinLoc binaries (no conda env) on a copy of the C1 smoke-test recipe; md5-compare with their grids
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
N=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/NonLinLoc
export PATH=$N/bin:$PATH HOME=$V/home
echo "conda env active: ${CONDA_DEFAULT_ENV:-none}  Vel2Grid=$(command -v Vel2Grid)"
for p in $(ls $N/bin); do f=$N/bin/$p; b=$(ldd $f | awk '$2=="=>"{print $3}' | grep -v -E '^/lib64/(libc|libm|libpthread|libdl|librt|libgcc_s|libstdc\+\+)\.so' | tr '\n' ' '); nf=$(ldd $f | grep -c 'not found'); [ -n "$b" -o "$nf" != 0 ] && echo "ldd $p: notfound=$nf other=$b"; done; echo "ldd check done ($(ls $N/bin | wc -l) programs)"
echo "libs used by NLLoc: $(ldd $N/bin/NLLoc | awk '$2=="=>"{print $1}' | tr '\n' ' ')"
W=$V/tmp/nll_smoke; rm -rf /home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install/tmp/nll_smoke; mkdir -p $W/iasp91_2D_azimuthal_equidist/{model,time}
/bin/cp -f $N/smoke_test/stations.in $W/; /bin/cp -rf $N/smoke_test/iasp91_2D_azimuthal_equidist/run $W/iasp91_2D_azimuthal_equidist/
cd $W/iasp91_2D_azimuthal_equidist
for ph in P S; do Vel2Grid run/phase$ph.run > vel2grid_$ph.log 2>&1; echo "Vel2Grid $ph exit=$?"; Grid2Time run/phase$ph.run > grid2time_$ph.log 2>&1; echo "Grid2Time $ph exit=$?"; done
echo "files: model $(ls model | wc -l), time $(ls time | wc -l)"
nd=0; for f in model/* time/*; do cmp -s $f $N/smoke_test/iasp91_2D_azimuthal_equidist/$f || { nd=$((nd+1)); echo "DIFF $f"; }; done; echo "files differing from C1 smoke_test: $nd"
nd=0; for f in time/*; do cmp -s $f /home/msseo/works/74.SeisComP_rtDD_DLpicker/software/src/seiscomp/src/extras/scrtdd/libs/hdd/test/data/nll/iasp91_2D_azimuthal_equidist/$f || nd=$((nd+1)); done; echo "files differing from step-T scrtdd test grids: $nd"
grep -i -E 'error|warn' vel2grid_*.log grid2time_*.log | head -5
