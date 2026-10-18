# vA4_plugin.sh -- verifier scratch: scautopick plugin A/B test (no plugin vs plugins=dlrtpicker), in a fresh login shell
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
export SEISCOMP_LOCAL_CONFIG=$V/seiscomp_user
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
export HOME=$V/home ORT_DISABLE_TELEMETRY=1
D=$V/tmp/plugin_ab; mkdir -p $D; cd $D
NS='http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.14'
printf '<?xml version="1.0" encoding="UTF-8"?>\n<seiscomp xmlns="%s" version="0.14">\n  <Inventory/>\n</seiscomp>\n' $NS > inv.xml
printf '<?xml version="1.0" encoding="UTF-8"?>\n<seiscomp xmlns="%s" version="0.14">\n  <Config/>\n</seiscomp>\n' $NS > cfg.xml
: > empty.mseed
echo 'picker = DL3C' > np_DL3C.cfg; echo 'picker = DL1C' > np_DL1C.cfg
echo 'spicker = SDL3C' > np_SDL3C.cfg; echo 'spicker = SDL1C' > np_SDL1C.cfg
printf 'plugins = dlrtpicker\npicker = DL3C\nspicker = SDL3C\n' > p_DL3C_SDL3C.cfg
printf 'plugins = dlrtpicker\npicker = DL1C\nspicker = SDL1C\n' > p_DL1C_SDL1C.cfg
# extra control: plugin loaded but a bogus picker name must still be rejected
printf 'plugins = dlrtpicker\npicker = DLXX\n' > p_bogus.cfg
for c in np_DL3C np_DL1C np_SDL3C np_SDL1C p_DL3C_SDL3C p_DL1C_SDL1C p_bogus; do
  /usr/bin/timeout 120 scautopick --config-file $D/$c.cfg --offline --playback --inventory-db $D/inv.xml --config-db $D/cfg.xml -I file://$D/empty.mseed --debug > $c.log 2>&1
  echo "== $c exit=$?"; grep -E 'Trying to open plugin|registered|version:|not available|Unknown|No stations added' $c.log | sed 's/^/   /'
done
# which libonnxruntime / libstdc++ are mapped into the process when the plugin is loaded
LD_DEBUG=libs /usr/bin/timeout 120 scautopick --config-file $D/p_DL3C_SDL3C.cfg --offline --playback --inventory-db $D/inv.xml --config-db $D/cfg.xml -I file://$D/empty.mseed > lddebug.log 2>&1
echo "== LD_DEBUG run exit=$?"
grep -E 'calling init: .*(libonnxruntime|libstdc\+\+|libgcc_s|dlrtpicker|libboost_filesystem|libxml2|libssl)' lddebug.log | sed 's/^ *[0-9]*: *//' | sort -u
ls -la $V/home
