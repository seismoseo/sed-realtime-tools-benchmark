# vT3_smoke_rerun.sh -- verifier scratch: re-run the step-T DL-picker smoke test (their config + inputs, read-only) into verify_install; telemetry off
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
S=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/smoke_dlpicker
export SEISCOMP_LOCAL_CONFIG=$V/seiscomp_user_smoke
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
export HOME=$V/home ORT_DISABLE_TELEMETRY=1
O=$V/tmp/smoke_rerun; mkdir -p $O; cd $O
stat -c '%y %n' /tmp/.ses
/usr/bin/time -v -o time.txt scautopick --config-file $S/config/scautopick_phasenet_instance.cfg --offline --playback --ep -f \
  --inventory-db file://$S/input/inventory_sc.xml --config-db file://$S/config/bindings_config.xml \
  -I file://$S/input/20210827220322_sorted.mseed --debug > picks.xml 2> scautopick.log
echo "scautopick exit=$?"
grep -E 'Elapsed|Maximum resident' time.txt
grep -m2 -E 'OnnxSession|Plugin dlrtpicker registered' scautopick.log
echo "errors: $(grep -c '\[error\]' scautopick.log)  warnings: $(grep -c '\[warning\]' scautopick.log)"
stat -c '%y %n' /tmp/.ses
ls -la $HOME; find $HOME -type f | head
