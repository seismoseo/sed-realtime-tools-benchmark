# 03_check_pip_report.py -- used by 03_install_pyrtdd.sh (step install).
#
# Reads the JSON report written by "pip install --dry-run --report <file>" and lists what pip
# would install. Exits with an error if pip wants anything other than pyrtdd itself, because that
# would mean pip is about to replace a conda package (numpy, obspy, pytest, ...) with a PyPI copy.
#
# Usage: python 03_check_pip_report.py <report.json>

import json
import sys

report = json.load(open(sys.argv[1]))
names = [item["metadata"]["name"] + "==" + item["metadata"]["version"] for item in report["install"]]
print("   pip would install:", names)
others = [n for n in names if not n.lower().startswith("pyrtdd==")]
if others:
    sys.exit("   STOP: pip wants to install or replace packages other than pyrtdd: " + ", ".join(others))
print("   OK: only pyrtdd would be installed; conda's numpy/obspy/pytest stay untouched")
