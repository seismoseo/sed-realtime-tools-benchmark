#!/usr/bin/env python
# check_playback_sort.py -- (copied from runs/sanramon/waveforms/ for the 2025-26 case; only paths changed)
# why does 'scmssort -E -u <file>' differ from the San Ramon 2025-26 playback files?
# (check_waveforms_seiscomp.sh step 3 reported DIFFERENT for all 26 files, with equal record counts.)
#
# For every inputs/playback/<id>.mseed: run scmssort -E -u on it in a SeisComP shell (output read from a
# pipe, nothing written), split both byte streams into 512-byte records and compare
#   * the multiset of records (same records, possibly in another order?) and duplicates;
#   * order by two end-time definitions, read with obspy's get_record_information:
#       last  = time of the last sample            (obspy 'endtime'; used by download_waveforms.py)
#       after = last + 1/sampling rate             (SeisComP Record::endTime(), used by scmssort -E)
#     Each sequence is tested for being non-decreasing under each definition.
# Output: runs/sanramon2026_waveform_checks/playback_sort_check.csv; summary on stdout.
# Usage (env pyrtdd): python -I check_playback_sort.py      (read-only)

import csv
import glob
import io
import os
import subprocess
from collections import Counter

import numpy as np
from obspy.io.mseed.util import get_record_information

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
PLAYBACK = f"{PROJECT}/data/sanramon_2026/inputs/playback"
OUT = f"{PROJECT}/runs/sanramon2026_waveform_checks/playback_sort_check.csv"
ENV = f"{PROJECT}/install/env_seiscomp.sh"
REC = 512


def ends(buf):
    last, after = [], []
    f = io.BytesIO(buf)
    for off in range(0, len(buf), REC):
        info = get_record_information(f, offset=off)
        last.append(info["endtime"].ns)
        after.append(info["endtime"].ns + int(round(1e9 / info["samp_rate"])))
    return np.array(last), np.array(after)


def main():
    rows = []
    for p in sorted(glob.glob(f"{PLAYBACK}/*.mseed")):
        a = open(p, "rb").read()
        r = subprocess.run(["bash", "-c", f"source {ENV} >/dev/null 2>&1; scmssort -E -u '{p}'"],
                           capture_output=True)
        b = r.stdout
        ra = [a[i:i + REC] for i in range(0, len(a), REC)]
        rb = [b[i:i + REC] for i in range(0, len(b), REC)]
        la, aa = ends(a)
        lb, ab = ends(b)
        rows.append(dict(file=os.path.basename(p), records_file=len(ra), records_scmssort=len(rb),
                         scmssort_exit=r.returncode, same_records=Counter(ra) == Counter(rb),
                         duplicates_in_file=len(ra) - len(set(ra)),
                         file_sorted_by_last_sample=bool(np.all(np.diff(la) >= 0)),
                         file_sorted_by_last_plus_dt=bool(np.all(np.diff(aa) >= 0)),
                         scmssort_sorted_by_last_sample=bool(np.all(np.diff(lb) >= 0)),
                         scmssort_sorted_by_last_plus_dt=bool(np.all(np.diff(ab) >= 0)),
                         positions_differing=sum(1 for x, y in zip(ra, rb) if x != y),
                         max_reorder_s=float(np.max(np.abs(la - lb)) / 1e9) if len(la) == len(lb) else np.nan))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)
    keys = ["same_records", "file_sorted_by_last_sample", "scmssort_sorted_by_last_plus_dt"]
    print({k: sum(r[k] for r in rows) for k in keys}, "of", len(rows),
          "| duplicates:", sum(r["duplicates_in_file"] for r in rows),
          "| largest end-time displacement between the two orders (s):", max(r["max_reorder_s"] for r in rows))


if __name__ == "__main__":
    main()
