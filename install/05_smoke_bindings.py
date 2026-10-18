# 05_smoke_bindings.py -- step T helper (run in conda env 'pyrtdd': obspy).
#
# Writes SeisComP "key files" (station bindings) for the DL-picker smoke test, so that scautopick
# runs its STA/LTA detector on exactly one vertical channel per station.
#
# Why bindings at all: without a configuration module, scautopick's 'useAllStreams' puts a detector
# on EVERY stream it receives, i.e. also on the two horizontal channels, so one station could trigger
# the P picker up to three times. With bindings, scautopick subscribes to the three components of the
# bound sensor (detecStream = first two letters of the channel code, e.g. HH) and detects on the
# vertical one only.
#
# A station is bound only if:
#   - the playback file has its Z, N and E channels of one sensor (one sensor per station here), and
#   - stations.xml has metadata (an epoch covering the data window) for all three channels;
#     the 3-component pickers need the inventory to find the vertical and the two horizontals.
# Every other station is listed with the reason it was skipped (nothing is invented).
#
# Output (in --keydir):
#   station_<NET>_<STA>        "global:<sensor>" + "scautopick:dlsmoke"
#   global/profile_<sensor>    detecLocid = "<loc>" ; detecStream = <sensor>   (one profile per sensor code)
#   scautopick/profile_dlsmoke (no parameters: all scautopick settings are module-wide in scautopick.cfg)
# plus --table: a CSV with one row per station found in the waveform file (bound or skipped, and why).
#
# Usage: python 05_smoke_bindings.py --mseed sorted.mseed --stationxml stations.xml \
#            --keydir <dir> --table stations_bound.csv

import argparse
import csv
import os
import sys
from collections import defaultdict

import obspy

SCAUTOPICK_PROFILE = "dlsmoke"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mseed", required=True)
    ap.add_argument("--stationxml", required=True)
    ap.add_argument("--keydir", required=True)
    ap.add_argument("--table", required=True)
    args = ap.parse_args()

    st = obspy.read(args.mseed, headonly=True)
    inv = obspy.read_inventory(args.stationxml)

    # (net, sta) -> (loc, sensor) -> set of component letters, plus the data window per station
    comps = defaultdict(lambda: defaultdict(set))
    window = {}
    for tr in st:
        s = tr.stats
        key = (s.network, s.station)
        comps[key][(s.location, s.channel[:2])].add(s.channel[2])
        t0, t1 = window.get(key, (s.starttime, s.endtime))
        window[key] = (min(t0, s.starttime), max(t1, s.endtime))

    rows = []
    profiles = {}
    for (net, sta) in sorted(comps):
        groups = comps[(net, sta)]
        t0, t1 = window[(net, sta)]
        tmid = t0 + (t1 - t0) / 2
        candidates = []
        reasons = []
        for (loc, sensor), letters in sorted(groups.items()):
            if not {"Z", "N", "E"} <= letters:
                reasons.append(f"{sensor}: data has components {''.join(sorted(letters))}, not ZNE")
                continue
            missing = []
            for c in "ZNE":
                sel = inv.select(network=net, station=sta, location=loc, channel=sensor + c,
                                 starttime=t0, endtime=t1)
                chans = [ch for n in sel for s_ in n for ch in s_
                         if ch.start_date <= t0 and (ch.end_date is None or ch.end_date >= t1)]
                if not chans:
                    missing.append(sensor + c)
            if missing:
                has_sta = len(inv.select(network=net, station=sta)) > 0
                why = ("station absent from stations.xml" if not has_sta
                       else "no channel epoch covering the data window for " + ",".join(missing))
                reasons.append(f"{sensor}: {why}")
                continue
            candidates.append((loc, sensor))

        if len(candidates) > 1:
            sys.exit(f"ERROR: {net}.{sta} has more than one bindable sensor {candidates}; "
                     "this helper expects one sensor per station (true for the Gwangyang set)")
        if candidates:
            loc, sensor = candidates[0]
            if profiles.get(sensor, loc) != loc:      # one global profile per sensor code
                sys.exit(f"ERROR: sensor {sensor} used with two location codes")
            profiles[sensor] = loc
            rows.append(dict(network=net, station=sta, location=loc, sensor=sensor, bound=1,
                             reason="", data_start=str(t0), data_end=str(t1)))
        else:
            rows.append(dict(network=net, station=sta, location="",
                             sensor="/".join(sorted({g[1] for g in groups})), bound=0,
                             reason="; ".join(reasons), data_start=str(t0), data_end=str(t1)))

    os.makedirs(os.path.join(args.keydir, "global"), exist_ok=True)
    os.makedirs(os.path.join(args.keydir, "scautopick"), exist_ok=True)
    for sensor, loc in sorted(profiles.items()):
        with open(os.path.join(args.keydir, "global", f"profile_{sensor}"), "w") as f:
            f.write(f"# written by 05_smoke_bindings.py: detect on the vertical channel of sensor {sensor}\n")
            f.write(f'detecLocid = "{loc}"\n')
            f.write(f"detecStream = {sensor}\n")
    with open(os.path.join(args.keydir, "scautopick", f"profile_{SCAUTOPICK_PROFILE}"), "w") as f:
        f.write("# written by 05_smoke_bindings.py: no station-specific scautopick parameters;\n")
        f.write("# every scautopick setting of the smoke test is module-wide in scautopick.cfg\n")
    for r in rows:
        if not r["bound"]:
            continue
        with open(os.path.join(args.keydir, f"station_{r['network']}_{r['station']}"), "w") as f:
            f.write(f"global:{r['sensor']}\n")
            f.write(f"scautopick:{SCAUTOPICK_PROFILE}\n")

    with open(args.table, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    nb = sum(r["bound"] for r in rows)
    print(f"stations in waveform file: {len(rows)}; bound: {nb}; skipped: {len(rows) - nb}")
    by_sensor = defaultdict(int)
    for r in rows:
        if r["bound"]:
            by_sensor[r["sensor"]] += 1
    print("bound per sensor: " + ", ".join(f"{k} {v}" for k, v in sorted(by_sensor.items())))
    for r in rows:
        if not r["bound"]:
            print(f"  skipped {r['network']}.{r['station']}: {r['reason']}")


if __name__ == "__main__":
    main()
