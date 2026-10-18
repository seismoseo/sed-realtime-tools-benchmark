# 01_check_seiscomp_imports.py -- helper of install/01_check_seiscomp.sh (step A smoke checks).
#
# Imports SeisComP's Python modules and prints which Python runs them, which versions they
# report and from which files they were loaded, so the log shows that 'import seiscomp' uses
# the conda Python 3.12 and the modules installed in SEISCOMP_ROOT (not some other copy).
# It also turns a SeisComP array into a numpy array (the wrappers were built with numpy 1.26).
# Exit code 0 = all modules come from SEISCOMP_ROOT, 1 = at least one does not.
#
# Run in the project environment:
#   source install/env_seiscomp.sh; python install/01_check_seiscomp_imports.py

import os
import sys

import numpy

import seiscomp.client
import seiscomp.core
import seiscomp.datamodel
import seiscomp.io
import seiscomp.math
import seiscomp.seismology
import seiscomp.system

root = os.path.realpath(os.environ["SEISCOMP_ROOT"])
print("python        :", sys.executable, sys.version.split()[0])
print("numpy         :", numpy.__version__)
print("framework     :", seiscomp.core.FrameworkVersion().toString())
print("data schema   :", f"{seiscomp.datamodel.Version.Major}.{seiscomp.datamodel.Version.Minor}")

outside = 0
for mod in (seiscomp.core, seiscomp.client, seiscomp.datamodel, seiscomp.io,
            seiscomp.math, seiscomp.seismology, seiscomp.system):
    inside = os.path.realpath(mod.__file__).startswith(root + os.sep)
    outside += not inside
    where = "in SEISCOMP_ROOT" if inside else "NOT in SEISCOMP_ROOT"
    print(f"{mod.__name__:20s} {mod.__file__}  ({where})")

arr = seiscomp.core.DoubleArray(3)
arr.set(1, 2.5)
print("numpy view of a SeisComP DoubleArray:", repr(arr.numpy()))

sys.exit(1 if outside else 0)
