scrtdd v2.0.10 crash with --ep and a file inventory (2026-10-17, Server A)

Command (cwd SEa/ev1/work, SEISCOMP_LOCAL_CONFIG=SEa/ev1/seiscomp_user, HOME=SEa/ev1/home):
  scrtdd --ep origin_1.xml --profile gwangyang
         --inventory-db file:///home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/inventory_sc.xml
         -I sdsarchive:///home/msseo/works/74.SeisComP_rtDD_DLpicker/data/gwangyang_11ev/inputs/sds
         --dump-diagnostics --verbosity=3 --console=1          -> exit -11 (SIGSEGV), core dumped
  same with --debug instead of --verbosity=3 --console=1       -> exit 139 (SIGSEGV), last line
         "[debug] Starting process [Origin/gwangyang/20210720161418/hypoinverse]"

Cause (source reading, apps/scrtdd/rtddtool.cpp of scrtdd v2.0.10):
  lines 1029-1035: with the inventory from a file (--inventory-db file://) and --ep, scrtdd switches the
                   database connection off (setDatabaseEnabled(false, false)), so query() is a null pointer;
  line 1586:       RTDD::startProcess() calls query()->getEvent(org->publicID()) without a null check.
Workaround used: the inventory is imported into a private SQLite database (scdb -i) and scrtdd gets
'-d sqlite3://.../inventory.sqlite' instead of --inventory-db (scrtdd_singleevent.py, make_inventory_db).
