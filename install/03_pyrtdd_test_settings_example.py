# 03_pyrtdd_test_settings_example.py -- used by 03_install_pyrtdd.sh (step example, run C).
#
# Same six steps as the README example, but with the settings of the repository's own test
# test_dd_and_relocate_multi_events_without_xcorr_overloads (package/test/py/test_dd_ext.py, commit
# d122c3a). That test compares its result with package/test/py/data/relocated-event.csv, so these
# are (we assume) the settings that produced that reference file. Running them here and writing the
# result to disk lets us measure the agreement in metres, instead of only the test's relative
# tolerance (rtol=1e-5 on latitude, longitude and depth).
#
# Differences from the README defaults: simple nearest-neighbour selection (numEllipsoids=0),
# neighbours within 15 km (default 5 km), and no down-weighting of large residuals (default 10 -> 5).
#
# Usage (run inside the output folder):
#   python 03_pyrtdd_test_settings_example.py <pyrtdd repo>/package/test/py/data

import sys

from pyrtdd.hdd import Catalog, Config, Homogeneous, DD, ClusteringOptions, SolverOptions

DATA_DIR = sys.argv[1].rstrip("/")

con = Config()
cat = Catalog(DATA_DIR + "/starting-station.csv",
              DATA_DIR + "/starting-event.csv",
              DATA_DIR + "/starting-phase.csv", False)
ttt = Homogeneous(5.8, 3.36)

dd = DD(cat, con, ttt)

cluster_cfg = ClusteringOptions()
cluster_cfg.numEllipsoids = 0
cluster_cfg.maxNeighbourDist = 15

solver_cfg = SolverOptions()
solver_cfg.algoIterations = 20
solver_cfg.absLocConstraintStart = 0.3
solver_cfg.absLocConstraintEnd = 0.3
solver_cfg.dampingFactorStart = 0.01
solver_cfg.dampingFactorEnd = 0.01
solver_cfg.downWeightingByResidualStart = 0
solver_cfg.downWeightingByResidualEnd = 0

clusters = dd.findClusters(cluster_cfg)
cat_new = dd.relocateMultiEvents(clusters, solver_cfg, saveProcessing=True, processingDataDir="")

cat_new.writeToFile("relocated-station.csv", "relocated-event.csv", "relocated-phase.csv")
