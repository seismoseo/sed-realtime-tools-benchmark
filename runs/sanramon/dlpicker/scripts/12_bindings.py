# 12_bindings.py -- step 12 helper (conda env 'pyrtdd': obspy). Adapted from step 09's 09_bindings.py
# (same key-file layout); differences are needed because the San Ramon stations, unlike Gwangyang's, often
# carry SEVERAL sensors (e.g. BK: BH + HH + HN; NC: a vertical-only EH + a 3-component HN) and use
# Z/N/E or 1/2/3 component codes.
#
# What it does
#   1. Reads every sorted event file (*_sorted.mseed) header-only: per station, per sensor
#      (location code + 2-letter band/instrument code) the component letters present, and per event file
#      the data span and the number of pieces of each channel.
#   2. Reads the SeisComP inventory that scautopick itself reads (inventory_sc.xml from fdsnxml2inv) and
#      decides for each sensor whether the 3-component pickers (DL3C/SDL3C) can use it. The test copies
#      SeisComP's own DataModel::getThreeComponents (libs/seiscomp/datamodel/utils.cpp:429-520): streams of
#      the sensor open at the event time, axes from azimuth/dip, a stream is dropped if its axis has a dot
#      product > 5 deg (in radians, 0.0873, as in the C++ code) with an axis already kept; >= 3 axes needed;
#      vertical = the axis with the largest |z|. The three chosen channels must also be in the data, and an
#      epoch must cover the data span of every event file in which the sensor has data (a binding is global).
#   3. Chooses ONE sensor per station for the main binding set (a scautopick binding names one sensor per
#      station), by this fixed preference (velocity sensors first, because they have the lower noise floor
#      for small events; then accelerometers):
#          HH > EH > EP > DP > BH > SH > HN > CN > others
#      ties (same sensor type at several location codes): the one with complete data in the most event
#      files, then Z/N/E-named over 1/2/3-named, then the smaller location code.
#   4. Second binding set 'hn': at every station whose main sensor is NOT an accelerometer (HN/CN) but which
#      also has a usable 3-component accelerometer, that accelerometer (HN preferred over CN). Run as
#      separate variants, it gives an accelerometer-vs-velocity-sensor comparison at the same sites.
#   Stations with no usable 3-component sensor (e.g. vertical-only EH) are not bound; the reason is listed.
#
# Output
#   <keydir>/station_<NET>_<STA>  "global:<profile>" + "scautopick:dl12" (one keydir per binding set)
#   <keydir>/global/profile_<profile>   detecLocid = "<loc>" ; detecStream = <sensor>
#   <keydir>/scautopick/profile_dl12    (empty: all scautopick settings are module-wide)
#   --table      one row per station found in the data (sensors, 3-C decision, main/hn sensor, reasons)
#   --coverage   one row per event file x station x bound sensor (main and hn): data span relative to the
#                origin, pieces, 'complete' (all 3 channels in one piece over >= --complete-s seconds)
#   --channels   one row per bound sensor x channel: role (Z/H1/H2 as getThreeComponents assigns them),
#                dip, azimuth, gain, polarity sense (as the plugin's VerticalPolaritySense, maxTilt 20)
#   --probe-out  a 10-s, one-station file for the start-up cost run
#
# Usage: python 12_bindings.py --mseed-dir <dir> --inventory inventory_sc.xml --events dl_subset_events.csv \
#            --keydir-main <dir> --keydir-hn <dir> --table stations_bound.csv --coverage coverage.csv \
#            --channels bound_channels.csv [--probe-out probe.mseed]

import argparse
import csv
import glob
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

import obspy

SCAUTOPICK_PROFILE = "dl12"
PROBE_SECONDS = 10.0
PREFERENCE = ["HH", "EH", "EP", "DP", "BH", "SH", "HN", "CN"]
ACCEL = ("HN", "CN")
PERP_TOL = 5 * math.pi / 180          # utils.cpp: perpendicularityTolerance, compared with a dot product


def tparse(x):
    return obspy.UTCDateTime(x) if x else None


def read_sc_streams(path):
    """(net, sta) -> list of dict(loc, code, start, end, loc_start, loc_end, azimuth, dip, gain)."""
    root = ET.parse(path).getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    out = defaultdict(list)
    for net in root.iter(f"{ns}network"):
        for sta in net.findall(f"{ns}station"):
            for loc in sta.findall(f"{ns}sensorLocation"):
                for s in loc.findall(f"{ns}stream"):
                    def f(tag):
                        v = s.findtext(f"{ns}{tag}")
                        return float(v) if v not in (None, "") else None
                    out[(net.get("code"), sta.get("code"))].append(dict(
                        loc=loc.get("code") or "", code=s.get("code"),
                        start=tparse(s.findtext(f"{ns}start")), end=tparse(s.findtext(f"{ns}end")),
                        loc_start=tparse(loc.findtext(f"{ns}start")), loc_end=tparse(loc.findtext(f"{ns}end")),
                        azimuth=f("azimuth"), dip=f("dip"), gain=f("gain")))
    return out


def open_at(ep, t):
    # utils.cpp getThreeComponents: skip if end <= time or start > time
    if ep["start"] is None or ep["start"] > t:
        return False
    return ep["end"] is None or ep["end"] > t


def three_components(eps, loc, sensor, t):
    """Python copy of DataModel::getThreeComponents for one sensor location at time t.
    Returns (Z, H1, H2) stream dicts or None, plus a reason."""
    comps = []
    for ep in eps:
        if ep["loc"] != loc or not ep["code"].startswith(sensor) or not open_at(ep, t):
            continue
        if ep["dip"] is None:
            continue
        dip, azi = ep["dip"], ep["azimuth"]
        if azi is None:
            if abs(abs(dip) - 90.0) > 0.001:
                continue
            azi = 0.0
        d, a = math.radians(-dip), math.radians(azi)
        # Math::Vector3d::fromAngles(azi, dip): x = cos(dip) sin(azi), y = cos(dip) cos(azi), z = sin(dip)
        ax = (math.cos(d) * math.sin(a), math.cos(d) * math.cos(a), math.sin(d))
        if any(sum(p * q for p, q in zip(c[1], ax)) > PERP_TOL for c in comps):
            continue
        comps.append((ep, ax))
    if not comps:
        return None, "no stream open at the event time"
    comps.sort(key=lambda c: (-abs(c[1][2]), -c[1][2], c[0]["code"]))
    if len(comps) < 3:
        return None, f"only {len(comps)} independent component(s) in the inventory"
    z, h1, h2 = comps[0], comps[1], comps[2]
    cx = (h1[1][1] * h2[1][2] - h1[1][2] * h2[1][1], h1[1][2] * h2[1][0] - h1[1][0] * h2[1][2],
          h1[1][0] * h2[1][1] - h1[1][1] * h2[1][0])
    if sum(p * q for p, q in zip(cx, z[1])) > 0:
        h1, h2 = h2, h1
    return (z[0], h1[0], h2[0]), ""


def polarity_sense(dip, gain, max_tilt=20.0):
    # onnxmodel.cpp VerticalPolaritySense: unknown dip/gain = standard sensor
    down = False
    if dip is not None and abs(dip) <= 90.0:
        if 90.0 - abs(dip) > max_tilt:
            return "Unusable"
        down = dip > 0.0
    neg = gain is not None and gain < 0.0
    return "Inverted" if down != neg else "Direct"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mseed-dir", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--events", required=True)
    ap.add_argument("--keydir-main", required=True)
    ap.add_argument("--keydir-hn", required=True)
    ap.add_argument("--table", required=True)
    ap.add_argument("--coverage", required=True)
    ap.add_argument("--channels", required=True)
    ap.add_argument("--complete-s", type=float, default=239.0)
    ap.add_argument("--probe-out", default="")
    a = ap.parse_args()

    origin = {r["event_id"]: obspy.UTCDateTime(r["origin_time_utc"]) for r in csv.DictReader(open(a.events))}
    files = sorted(glob.glob(os.path.join(a.mseed_dir, "*_sorted.mseed")))
    if not files:
        sys.exit(f"ERROR: no *_sorted.mseed in {a.mseed_dir}")
    inv = read_sc_streams(a.inventory)

    letters = defaultdict(lambda: defaultdict(set))           # (net,sta) -> (loc,sensor) -> letters
    span = {}                                                 # (ev,net,sta,loc,cha) -> [t0, t1, pieces]
    chans_of = defaultdict(set)                               # (ev,net,sta) -> {(loc, cha)}
    station_files = defaultdict(set)
    for f in files:
        ev = os.path.basename(f).split("_")[0]
        for tr in obspy.read(f, headonly=True):
            s = tr.stats
            k = (s.network, s.station)
            letters[k][(s.location, s.channel[:2])].add(s.channel[2])
            station_files[k].add(ev)
            kk = (ev, s.network, s.station, s.location, s.channel)
            chans_of[(ev, s.network, s.station)].add((s.location, s.channel))
            t1 = s.endtime + s.delta
            if kk in span:
                span[kk] = [min(span[kk][0], s.starttime), max(span[kk][1], t1), span[kk][2] + 1]
            else:
                span[kk] = [s.starttime, t1, 1]

    def sensor_check(net, sta, loc, sensor):
        """(ok, reason, {ev: (Z, H1, H2)}) for one sensor over all event files with data."""
        eps = inv.get((net, sta), [])
        if not eps:
            return False, "station absent from the inventory", {}
        chosen = {}
        for ev in sorted(station_files[(net, sta)]):
            chans = [c for (l, c) in chans_of[(ev, net, sta)] if l == loc and c.startswith(sensor)]
            if not chans:
                continue
            t0 = min(span[(ev, net, sta, loc, c)][0] for c in chans)
            comp, why = three_components(eps, loc, sensor, t0)
            if comp is None:
                return False, f"{why} ({ev})", {}
            missing = [c["code"] for c in comp if c["code"] not in chans]
            if missing:
                return False, f"channel(s) {','.join(missing)} chosen by getThreeComponents have no data ({ev})", {}
            t1 = max(span[(ev, net, sta, loc, c)][1] for c in chans)
            for c in comp:                      # an epoch must cover the whole data span
                if not any(ep["loc"] == loc and ep["code"] == c["code"] and ep["start"] <= t0
                           and (ep["end"] is None or ep["end"] >= t1) for ep in eps):
                    return False, f"no epoch of {c['code']} covers the data span of {ev}", {}
            chosen[ev] = comp
        return (bool(chosen), "" if chosen else "no data", chosen)

    def complete(ev, net, sta, loc, comp):
        sp = [span.get((ev, net, sta, loc, c["code"])) for c in comp]
        if any(x is None for x in sp):
            return None
        t0, t1 = max(x[0] for x in sp), min(x[1] for x in sp)
        pieces = max(x[2] for x in sp)
        return dict(t0=t0, t1=t1, pieces=pieces, complete=(pieces == 1 and (t1 - t0) >= a.complete_s))

    rows, cov, chrows, profiles = [], [], [], {"main": {}, "hn": {}}
    binding = {"main": {}, "hn": {}}
    for (net, sta) in sorted(letters):
        groups = letters[(net, sta)]
        desc = ";".join(f"{loc or '--'}.{sen}:{''.join(sorted(c))}" for (loc, sen), c in sorted(groups.items()))
        ok3, reasons = [], []
        for (loc, sensor), lt in sorted(groups.items()):
            if len(lt) < 3:
                reasons.append(f"{loc or '--'}.{sensor}: data has only component(s) {''.join(sorted(lt))}")
                continue
            ok, why, chosen = sensor_check(net, sta, loc, sensor)
            if not ok:
                reasons.append(f"{loc or '--'}.{sensor}: {why}")
                continue
            ncomp = sum(1 for ev, comp in chosen.items() if (complete(ev, net, sta, loc, comp) or {}).get("complete"))
            zne = all(c["code"][2] in "ZNE" for comp in chosen.values() for c in comp)
            ok3.append(dict(loc=loc, sensor=sensor, chosen=chosen, n_complete=ncomp, zne=zne))

        def rank(c):
            pref = PREFERENCE.index(c["sensor"]) if c["sensor"] in PREFERENCE else len(PREFERENCE)
            return (pref, -c["n_complete"], 0 if c["zne"] else 1, c["loc"])

        main = sorted(ok3, key=rank)[0] if ok3 else None
        hn = None
        if main is not None and main["sensor"] not in ACCEL:
            acc = [c for c in ok3 if c["sensor"] in ACCEL]
            if acc:
                hn = sorted(acc, key=lambda c: (ACCEL.index(c["sensor"]), -c["n_complete"],
                                                0 if c["zne"] else 1, c["loc"]))[0]
        row = dict(network=net, station=sta, sensors_in_data=desc, n_event_files=len(station_files[(net, sta)]),
                   three_c_sensors=";".join(f"{c['loc'] or '--'}.{c['sensor']}" for c in ok3),
                   bound=int(main is not None), main_location=main["loc"] if main else "",
                   main_sensor=main["sensor"] if main else "", main_n_complete=main["n_complete"] if main else 0,
                   hn_location=hn["loc"] if hn else "", hn_sensor=hn["sensor"] if hn else "",
                   hn_n_complete=hn["n_complete"] if hn else 0,
                   not_bound_reason="" if main else "; ".join(reasons), other_reasons="; ".join(reasons) if main else "")
        rows.append(row)
        for role, c in (("main", main), ("hn", hn)):
            if c is None:
                continue
            prof = f"L{c['loc'] or 'blank'}_{c['sensor']}"
            profiles[role][prof] = (c["loc"], c["sensor"])
            binding[role][(net, sta)] = prof
            for ev, comp in sorted(c["chosen"].items()):
                cp = complete(ev, net, sta, c["loc"], comp)
                cov.append(dict(event_id=ev, network=net, station=sta, role=role, location=c["loc"],
                                sensor=c["sensor"], z=comp[0]["code"], h1=comp[1]["code"], h2=comp[2]["code"],
                                start_rel_origin_s=round(cp["t0"] - origin[ev], 3),
                                end_rel_origin_s=round(cp["t1"] - origin[ev], 3),
                                max_pieces=cp["pieces"], complete=int(cp["complete"])))
            seen = set()
            for comp in c["chosen"].values():
                for r, ch in zip(("Z", "H1", "H2"), comp):
                    key = (ch["code"], str(ch["start"]))
                    if key in seen:
                        continue
                    seen.add(key)
                    chrows.append(dict(network=net, station=sta, role=role, location=c["loc"], channel=ch["code"],
                                       component_role=r, epoch_start=str(ch["start"]), epoch_end=str(ch["end"]),
                                       dip=ch["dip"], azimuth=ch["azimuth"], gain=ch["gain"],
                                       polarity_sense=polarity_sense(ch["dip"], ch["gain"]) if r == "Z" else ""))

    for role, keydir in (("main", a.keydir_main), ("hn", a.keydir_hn)):
        os.makedirs(os.path.join(keydir, "global"), exist_ok=True)
        os.makedirs(os.path.join(keydir, "scautopick"), exist_ok=True)
        for prof, (loc, sensor) in sorted(profiles[role].items()):
            with open(os.path.join(keydir, "global", f"profile_{prof}"), "w") as f:
                f.write(f"# written by 12_bindings.py ({role} set): detect on the vertical of sensor "
                        f"{loc or '--'}.{sensor}\n")
                f.write(f'detecLocid = "{loc}"\n')
                f.write(f"detecStream = {sensor}\n")
        with open(os.path.join(keydir, "scautopick", f"profile_{SCAUTOPICK_PROFILE}"), "w") as f:
            f.write("# written by 12_bindings.py: no station-specific scautopick parameters;\n")
            f.write("# every scautopick setting of step 12 is module-wide in scautopick_<model>.cfg\n")
        for (net, sta), prof in sorted(binding[role].items()):
            with open(os.path.join(keydir, f"station_{net}_{sta}"), "w") as f:
                f.write(f"global:{prof}\n")
                f.write(f"scautopick:{SCAUTOPICK_PROFILE}\n")

    for path, data in ((a.table, rows), (a.coverage, cov), (a.channels, chrows)):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    nb = sum(r["bound"] for r in rows)
    print(f"event files: {len(files)}; stations with data: {len(rows)}; bound (main): {nb}; "
          f"not bound: {len(rows) - nb}; extra accelerometer bindings (hn set): {len(binding['hn'])}")
    cnt = defaultdict(int)
    for r in rows:
        if r["bound"]:
            cnt[r["main_sensor"]] += 1
    print("main set per sensor: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    cnt = defaultdict(int)
    for r in rows:
        if r["hn_sensor"]:
            cnt[f"{r['main_sensor']}->{r['hn_sensor']}"] += 1
    print("hn set (main sensor -> accelerometer): " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    nc = sum(1 for c in cov if c["role"] == "main" and c["complete"])
    print(f"main set: {nc} of {sum(1 for c in cov if c['role'] == 'main')} station-event records complete")
    for r in rows:
        if not r["bound"]:
            print(f"  not bound {r['network']}.{r['station']} [{r['sensors_in_data']}]: {r['not_bound_reason']}")

    if a.probe_out:
        r0 = next(r for r in rows if r["bound"] and r["main_n_complete"] == len(files))
        st = obspy.read(files[0]).select(network=r0["network"], station=r0["station"],
                                         location=r0["main_location"], channel=r0["main_sensor"] + "?")
        t0 = max(tr.stats.starttime for tr in st)
        st.trim(t0, t0 + PROBE_SECONDS)
        st.write(a.probe_out, format="MSEED", encoding="STEIM2", reclen=512)
        print(f"probe file: {a.probe_out}: {r0['network']}.{r0['station']} {len(st)} traces, "
              f"{PROBE_SECONDS:.0f} s from {t0}")


if __name__ == "__main__":
    main()
