#!/usr/bin/env python
# verify_rt_latency.py -- independent spot check of the paced-feed latencies of step 10 (RT3, RT5).
#
# msrtsimul (software/seiscomp/bin/msrtsimul, rt_simul) starts its simulated clock at etime = the END time of the
# first record, truncated to whole seconds (calendar.timegm(rec.end_time.timetuple())), at wall time rtime (just
# after it prints 'Starting msrtsimul at ...'). A record is released when etime + (wall - rtime) reaches its last
# sample time (also truncated). So the simulated clock reads data time T at wall time T + (rtime - etime).
# rt_analyze.py instead uses median(wall release - next record begin) as the offset, and the FINAL scautoloc origin
# time as the reference time. Here: offset = rtime - etime from the first record's header (obspy), and two reference
# times (final scautoloc origin time, S1 origin time), so the size of both choices is visible.
# Reads only: <run>/logs/msrtsimul_<kma>.stderr, <run>/data/<kma>_sorted.mseed, the database COPIES made by
# verify_rt_db.py, S1 reloc-event.csv. Writes OUT/verify_latency.csv only with --apply.
# Usage (env pyrtdd): python -I verify_rt_latency.py [--apply]

import argparse
import csv
import datetime as dt
import re
import sqlite3

from obspy import UTCDateTime
from obspy.io.mseed.util import get_record_information

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
RTROOT = f"{PROJECT}/runs/gwangyang/realtime"
OUT = f"{PROJECT}/runs/verify_gwangyang_realtime"
RUNS = ["RT3_paced", "RT5_paced_creationtime"]
REPLAY = {"20210827220322": 3, "20260202194119": 9}
S1 = f"{PROJECT}/runs/gwangyang/scrtdd/S1/work/reloc-event.csv"
CLAIMS = {  # (run, kma): first DL pick, first scautoloc origin, first RTDD (s after origin time, notes table)
    ("RT3_paced", "20210827220322"): (15.1, 38.3, 62.8), ("RT3_paced", "20260202194119"): (13.3, 40.4, 60.5),
    ("RT5_paced_creationtime", "20210827220322"): (15.1, 38.4, 232.6),
    ("RT5_paced_creationtime", "20260202194119"): (13.3, 40.5, 58.8)}


def t_sql(v, us):
    return UTCDateTime(str(v).replace(" ", "T") + "Z") + int(us or 0) / 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    s1 = {int(r["id"]): UTCDateTime(r["isotime"]) for r in csv.DictReader(open(S1))}
    rows = []
    for run in RUNS:
        con = sqlite3.connect(f"file:{OUT}/db_copies/{run}/seiscomp.sqlite?mode=ro&immutable=1", uri=True)
        picks = [(t_sql(r[0], r[1]), t_sql(r[2], r[3])) for r in con.execute(
            "SELECT time_value, time_value_ms, creationInfo_creationTime, creationInfo_creationTime_ms FROM Pick")]
        orgs = [dict(t=t_sql(r[0], r[1]), created=t_sql(r[2], r[3]), author=r[4], method=r[5]) for r in con.execute(
            "SELECT time_value, time_value_ms, creationInfo_creationTime, creationInfo_creationTime_ms, "
            "creationInfo_author, methodID FROM Origin")]
        con.close()
        for kma, rid in REPLAY.items():
            line = open(f"{RTROOT}/{run}/logs/msrtsimul_{kma}.stderr").readline()
            rtime = UTCDateTime(re.match(r"Starting msrtsimul at (\S+ \S+)", line).group(1).replace("+00:00", ""))
            info = get_record_information(f"{RTROOT}/{run}/data/{kma}_sorted.mseed", offset=0)
            end_first = info["starttime"] + info["npts"] / info["samp_rate"]       # = rec.end_time in msrtsimul
            etime = UTCDateTime(int(end_first.timestamp))                         # truncated to whole seconds
            offset = rtime - etime
            ev = [o for o in orgs if abs(o["t"] - s1[rid]) < 30]
            loc = sorted([o for o in ev if o["author"].startswith("scautoloc")], key=lambda o: o["created"])
            rt = sorted([o for o in ev if o["method"] == "RTDD"], key=lambda o: o["created"])
            pk = [c for t, c in picks if -200 <= t - s1[rid] <= 400]
            for ref_name, t0 in (("final_scautoloc_origin_time", loc[-1]["t"]), ("S1_origin_time", s1[rid])):
                w0 = t0 + offset
                row = dict(run=run, kma_id=kma, reference=ref_name, reference_time=str(t0), offset_s=round(offset, 3),
                           first_record_end=str(end_first), first_DL_pick_s=round(min(pk) - w0, 2),
                           first_scautoloc_origin_s=round(loc[0]["created"] - w0, 2),
                           first_RTDD_s=round(rt[0]["created"] - w0, 2) if rt else None,
                           last_RTDD_s=round(rt[-1]["created"] - w0, 2) if rt else None,
                           claimed_first_pick_origin_RTDD=CLAIMS[(run, kma)])
                rows.append(row)
                print(row)
    if a.apply:
        with open(f"{OUT}/verify_latency.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {OUT}/verify_latency.csv")


if __name__ == "__main__":
    main()
