# 09_bindings.py -- step 09 helper (run in conda env 'pyrtdd': obspy). Adapted from step T's
# install/05_smoke_bindings.py (same key-file layout and the same one-sensor-per-station rule).
#
# Writes SeisComP "key files" (station bindings) so that scautopick runs its STA/LTA detector on
# exactly one vertical channel per station (detecStream = the station's sensor code HH/HG/EL).
# Without bindings scautopick's 'useAllStreams' would put a detector on every stream, horizontals
# included, and one arrival could start the P picker three times (step T, "Problems" item 3).
#
# Differences from the step-T helper:
#   - it reads ALL sorted event files of a folder (*_sorted.mseed), not one: a binding is global, so a
#     station is bound only if its inventory covers the data windows of every event in which it has data;
#   - it checks the SeisComP inventory that scautopick itself reads (inventory_sc.xml, SCML 0.14):
#     the bound sensor's Z, N and E streams must exist in one sensor location whose epochs cover every
#     data window of that station. The 3-component pickers need all three (vertical by dip, horizontals
#     by azimuth, SeisComP getThreeComponents);
#   - optionally writes a 10-s, one-station probe file (--probe-out) for the start-up cost run.
# Every station found in the data but not bound is listed with the reason (nothing is invented).
#
# Output (in --keydir):
#   station_<NET>_<STA>        "global:<sensor>" + "scautopick:dl09"
#   global/profile_<sensor>    detecLocid = "<loc>" ; detecStream = <sensor>
#   scautopick/profile_dl09    (no parameters: all scautopick settings are module-wide in scautopick.cfg)
# plus --table: one row per station found in the waveform files.
#
# Usage: python 09_bindings.py --mseed-dir <dir with *_sorted.mseed> --inventory inventory_sc.xml \
#            --keydir <dir> --table stations_bound.csv [--probe-out probe.mseed]

import argparse
import csv
import glob
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

import obspy

SCAUTOPICK_PROFILE = "dl09"
PROBE_SECONDS = 10.0          # probe file length: far below scautopick's initTime (60 s)


def read_sc_streams(path):
    """(net, sta) -> list of dict(loc, code, start, end, azimuth, dip) from a SeisComP XML inventory."""
    root = ET.parse(path).getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    out = defaultdict(list)

    def t(el, tag):
        x = el.findtext(f"{ns}{tag}")
        return obspy.UTCDateTime(x) if x else None

    for net in root.iter(f"{ns}network"):
        for sta in net.findall(f"{ns}station"):
            for loc in sta.findall(f"{ns}sensorLocation"):
                for s in loc.findall(f"{ns}stream"):
                    out[(net.get("code"), sta.get("code"))].append(dict(
                        loc=loc.get("code") or "", code=s.get("code"), start=t(s, "start"), end=t(s, "end"),
                        loc_start=t(loc, "start"), loc_end=t(loc, "end"),
                        azimuth=s.findtext(f"{ns}azimuth"), dip=s.findtext(f"{ns}dip")))
    return out


def covers(ep, t0, t1, key_start="start", key_end="end"):
    return ep[key_start] is not None and ep[key_start] <= t0 and (ep[key_end] is None or ep[key_end] >= t1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mseed-dir", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--keydir", required=True)
    ap.add_argument("--table", required=True)
    ap.add_argument("--probe-out", default="")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.mseed_dir, "*_sorted.mseed")))
    if not files:
        sys.exit(f"ERROR: no *_sorted.mseed in {args.mseed_dir}")
    inv = read_sc_streams(args.inventory)

    # (net, sta) -> (loc, sensor) -> set of component letters; data windows per (net, sta, file)
    comps = defaultdict(lambda: defaultdict(set))
    windows = defaultdict(list)
    for f in files:
        st = obspy.read(f, headonly=True)
        win = {}
        for tr in st:
            s = tr.stats
            key = (s.network, s.station)
            comps[key][(s.location, s.channel[:2])].add(s.channel[2])
            t0, t1 = win.get(key, (s.starttime, s.endtime))
            win[key] = (min(t0, s.starttime), max(t1, s.endtime))
        for key, w in win.items():
            windows[key].append((os.path.basename(f), w[0], w[1]))

    rows, profiles = [], {}
    for (net, sta) in sorted(comps):
        groups = comps[(net, sta)]
        candidates, reasons = [], []
        for (loc, sensor), letters in sorted(groups.items()):
            if not {"Z", "N", "E"} <= letters:
                reasons.append(f"{sensor}: data has components {''.join(sorted(letters))}, not ZNE")
                continue
            missing = []
            for fname, t0, t1 in windows[(net, sta)]:
                for c in "ZNE":
                    ok = [ep for ep in inv.get((net, sta), [])
                          if ep["loc"] == loc and ep["code"] == sensor + c
                          and covers(ep, t0, t1) and covers(ep, t0, t1, "loc_start", "loc_end")]
                    if not ok:
                        missing.append(f"{sensor}{c}@{fname[:14]}")
            if missing:
                why = ("station absent from the inventory" if (net, sta) not in inv
                       else "no stream epoch covering " + ",".join(missing))
                reasons.append(f"{sensor}: {why}")
                continue
            candidates.append((loc, sensor))

        if len(candidates) > 1:
            sys.exit(f"ERROR: {net}.{sta} has more than one bindable sensor {candidates}; "
                     "this helper expects one sensor per station (true for the Gwangyang set)")
        nev = len(windows[(net, sta)])
        if candidates:
            loc, sensor = candidates[0]
            if profiles.get(sensor, loc) != loc:          # one global profile per sensor code
                sys.exit(f"ERROR: sensor {sensor} used with two location codes")
            profiles[sensor] = loc
            zdip = [ep["dip"] for ep in inv[(net, sta)] if ep["code"] == sensor + "Z" and ep["loc"] == loc]
            rows.append(dict(network=net, station=sta, location=loc, sensor=sensor, bound=1, reason="",
                             n_event_files=nev, z_dip=";".join(sorted(set(str(d) for d in zdip)))))
        else:
            rows.append(dict(network=net, station=sta, location="",
                             sensor="/".join(sorted({g[1] for g in groups})), bound=0,
                             reason="; ".join(reasons), n_event_files=nev, z_dip=""))

    os.makedirs(os.path.join(args.keydir, "global"), exist_ok=True)
    os.makedirs(os.path.join(args.keydir, "scautopick"), exist_ok=True)
    for sensor, loc in sorted(profiles.items()):
        with open(os.path.join(args.keydir, "global", f"profile_{sensor}"), "w") as f:
            f.write(f"# written by 09_bindings.py: detect on the vertical channel of sensor {sensor}\n")
            f.write(f'detecLocid = "{loc}"\n')
            f.write(f"detecStream = {sensor}\n")
    with open(os.path.join(args.keydir, "scautopick", f"profile_{SCAUTOPICK_PROFILE}"), "w") as f:
        f.write("# written by 09_bindings.py: no station-specific scautopick parameters;\n")
        f.write("# every scautopick setting of step 09 is module-wide in scautopick_<variant>.cfg\n")
    for r in rows:
        if r["bound"]:
            with open(os.path.join(args.keydir, f"station_{r['network']}_{r['station']}"), "w") as f:
                f.write(f"global:{r['sensor']}\n")
                f.write(f"scautopick:{SCAUTOPICK_PROFILE}\n")

    with open(args.table, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    nb = sum(r["bound"] for r in rows)
    print(f"event files: {len(files)}; stations with data: {len(rows)}; bound: {nb}; skipped: {len(rows) - nb}")
    by_sensor = defaultdict(int)
    for r in rows:
        if r["bound"]:
            by_sensor[r["sensor"]] += 1
    print("bound per sensor: " + ", ".join(f"{k} {v}" for k, v in sorted(by_sensor.items())))
    for r in rows:
        if not r["bound"]:
            print(f"  skipped {r['network']}.{r['station']}: {r['reason']}")

    if args.probe_out:
        # the first bound station of the first event file, its 3 bound channels, first PROBE_SECONDS s
        r0 = next(r for r in rows if r["bound"])
        st = obspy.read(files[0]).select(network=r0["network"], station=r0["station"],
                                         channel=r0["sensor"] + "?")
        t0 = max(tr.stats.starttime for tr in st)
        st.trim(t0, t0 + PROBE_SECONDS)
        st.write(args.probe_out, format="MSEED", encoding="STEIM2", reclen=512)
        print(f"probe file: {args.probe_out}: {r0['network']}.{r0['station']} {len(st)} traces, "
              f"{PROBE_SECONDS:.0f} s from {t0}")


if __name__ == "__main__":
    main()
