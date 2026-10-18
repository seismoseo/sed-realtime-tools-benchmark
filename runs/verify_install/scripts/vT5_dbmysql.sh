# vT5_dbmysql.sh -- verifier scratch: does fdsnxml2inv fail without --core.plugins=dbsqlite3 (default core.plugins=dbmysql)?
V=/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_install
export SEISCOMP_LOCAL_CONFIG=$V/seiscomp_user
source /home/msseo/works/74.SeisComP_rtDD_DLpicker/install/env_seiscomp.sh
export HOME=$V/home ORT_DISABLE_TELEMETRY=1
cd $V/tmp
X=/home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/stations.xml
grep -n 'core.plugins' $SEISCOMP_ROOT/etc/defaults/global.cfg; ls $SEISCOMP_ROOT/etc/global.cfg 2>&1
fdsnxml2inv -f $X inv_default.xml > fx1.log 2>&1; echo "without option exit=$?"; grep -E 'error' fx1.log | head -3
fdsnxml2inv --core.plugins=dbsqlite3 -f $X inv_sqlite.xml > fx2.log 2>&1; echo "with --core.plugins=dbsqlite3 exit=$?"; grep -c 'ambiguous' fx2.log; ls -la inv_sqlite.xml
python3 -c "import xml.etree.ElementTree as E; r=E.parse('inv_sqlite.xml').getroot(); ns=r.tag.split('}')[0]+'}'; print('stations in SC inventory:', len(list(r.iter(ns+'station'))))"
