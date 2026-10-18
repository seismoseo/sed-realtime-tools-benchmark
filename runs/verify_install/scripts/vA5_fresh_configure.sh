# vA5_fresh_configure.sh -- verifier scratch: ONE fresh cmake configure with the exact options of 01_build_seiscomp.sh into a scratch
# build dir (no compile), then ctest -N, to check that a single configure registers the scrtdd tests (HDD_TESTS fix)
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
P=/home/msseo/works/74.SeisComP_rtDD_DLpicker
E=/home/msseo/miniforge3/envs/seiscomp
source /home/msseo/miniforge3/etc/profile.d/conda.sh; conda activate $E
export HOME=$V/home
B=$V/tmp/fresh_build
nice -n 10 cmake -S $P/software/src/seiscomp -B $B -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$P/software/seiscomp -DCMAKE_PREFIX_PATH=$E \
  "-DCMAKE_INSTALL_RPATH=$P/software/seiscomp/lib;$E/lib" -DSC_GLOBAL_GUI=OFF -DSC_GLOBAL_UNITTESTS=ON -DHDD_TESTS=ON -DSC_GLOBAL_PYTHON_WRAPPER=ON \
  -DSC_GLOBAL_PYTHON_WRAPPER_NUMPY=ON -DSC_TRUNK_DB_MYSQL=OFF -DSC_TRUNK_DB_POSTGRESQL=OFF -DSC_TRUNK_DB_SQLITE3=ON -DSC_DOC_GENERATE=OFF -DSC_DLRTPICKER=ON \
  -DONNXRUNTIME_ROOT=$P/software/onnxruntime/onnxruntime-linux-x64-1.31.0 -DPython_EXECUTABLE=$E/bin/python3.12 -DPYTHON_EXECUTABLE=$E/bin/python3.12 \
  -DPYTHON_INCLUDE_DIR=$E/include/python3.12 -DPYTHON_LIBRARY=$E/lib/libpython3.12.so > $V/logs/A5_fresh_configure.log 2>&1
echo "configure exit=$?"
grep -E '^HDD_TESTS|^SC_DLRTPICKER|^ONNXRUNTIME_ROOT' $B/CMakeCache.txt
cd $B && ctest -N | tail -1; echo "hdd tests: $(ctest -N | grep -c -E 'test_hdd')"
