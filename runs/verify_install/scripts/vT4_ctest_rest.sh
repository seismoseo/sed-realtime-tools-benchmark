# vT4_ctest_rest.sh -- verifier scratch: re-run the non-hdd SeisComP unit tests, excluding the 8 port-opening tests (fresh login shell)
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
export SEISCOMP_LOCAL_CONFIG=$V/seiscomp_user_ctest
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
export HOME=$V/home ORT_DISABLE_TELEMETRY=1
B=/home/msseo/works/74.SeisComP_rtDD_DLpicker/software/build/seiscomp
echo "not run (port-opening, by rule):"; ctest --test-dir $B -N -R '^(test_fdsnws_.*|scevent-remote)$' | grep -E 'Test +#'
nice -n 10 ctest --test-dir $B -j8 -E '^(test_fdsnws_.*|scevent-remote|test_hdd.*)$' --output-on-failure --timeout 600 --output-junit $V/logs/ctest_rest_junit.xml > $V/logs/ctest_rest.log 2>&1
echo "ctest EXIT=$?"; grep -E 'tests passed|tests failed|Total Test time' $V/logs/ctest_rest.log
