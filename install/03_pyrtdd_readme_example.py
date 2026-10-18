# 03_pyrtdd_readme_example.py -- used by 03_install_pyrtdd.sh (step example, run A).
#
# The "Example workflow" code block of pyrtdd's README.md (commit d122c3a, README lines 85-128),
# copied verbatim. The only change: the README loads the test catalog with paths relative to the
# repository root ('./package/test/py/data/...'); here the data folder is given on the command line,
# because the example runs in a scratch folder (it writes its results into the current directory).
# All three configuration objects are used with their default values, exactly as in the README.
#
# Usage (run inside the output folder):
#   python 03_pyrtdd_readme_example.py <pyrtdd repo>/package/test/py/data

import sys

DATA_DIR = sys.argv[1].rstrip("/")

# ---- README code block starts here (only the three catalog paths changed) ----
from pyrtdd.hdd import (
        Catalog,
        Config,
        Homogeneous,
        DD,
        ClusteringOptions,
        SolverOptions,
    )

# 1. Load the input catalog: stations, events, and phase picks.
#    Here we use the test catalog included in this repo.
#    Catalog format: https://docs.gempa.de/scrtdd/current/base/multievent.html#event-catalog-plain-csv-files
cat = Catalog(DATA_DIR + '/starting-station.csv',
              DATA_DIR + '/starting-event.csv',
              DATA_DIR + '/starting-phase.csv')

# 2. Pick a velocity model. See below for other models
ttt = Homogeneous(5.8, 3.36)  # P/S velocity [km/s]

# 3. Build the relocator.
#    Ownership of `ttt` transfers into `dd` here (matching the C++
#    `unique_ptr` semantics), so it can't be reused afterwards. No waveform
#    proxy is passed, so this uses a `NoWaveformProxy()` internally and
#    cross-correlation stays off (see below for how to enable it).
cfg = Config() # see details later
dd = DD(cat, cfg, ttt)

# 4. Group events into clusters.
#    How multi-event relocation works: https://docs.gempa.de/scrtdd/current/base/multievent.html#relocation-process
cluster_cfg = ClusteringOptions() # see details later
clusters = dd.findClusters(cluster_cfg)

# 5. Then relocate the clusters.
#    How multi-event relocation works: https://docs.gempa.de/scrtdd/current/base/multievent.html#relocation-process
solver_cfg = SolverOptions()  # see details later
cat_new = dd.relocateMultiEvents(
    clusters, solver_cfg,
    saveProcessing=True, processingDataDir="")

# 6. Save the relocated catalog.
#    How to evaluate the results: https://docs.gempa.de/scrtdd/current/base/multievent.html#evaluating-the-results
cat_new.writeToFile('relocated-station.csv',
                    'relocated-event.csv',
                    'relocated-phase.csv')
