# vT1_ctest_hdd.sh -- verifier scratch: re-run 'ctest -R hdd' (same options as step T) from a fresh login shell; logs to verify_install/logs
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
export SEISCOMP_LOCAL_CONFIG=$V/seiscomp_user_ctest
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
export HOME=$V/home ORT_DISABLE_TELEMETRY=1
B=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/build/seiscomp
echo "start $(date '+%F %T')"
ctest --test-dir $B -N | tail -3
echo "hdd/rtdd tests listed: $(ctest --test-dir $B -N | grep -E 'Test +#' | grep -i -c -E 'hdd|rtdd')"
nice -n 10 ctest --test-dir $B -R hdd --output-on-failure --timeout 600 --output-junit $V/logs/ctest_hdd_junit.xml > $V/logs/ctest_hdd.log 2>&1
echo "ctest EXIT=$?"
echo "end $(date '+%F %T')"
