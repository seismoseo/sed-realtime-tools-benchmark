# 11_summary_counts.py -- reference_tables/summary_counts.csv: the numbers a reader needs before
# using the San Ramon 2025-26 benchmark (long format: section, item, value, note). Copied from the
# 2015 tool; LDEO = the real-time catalog NCAeqDDRT.v202201 (DDRT solutions only, supplementary).
#   events per magnitude bin (NCSS benchmark events, NCEDC DD box, LDEO DD-RT box)
#   picks per event (all NCSS picks, picks written to rtDD phase.csv), P vs S, weight codes
#   stations (net.sta.loc) and channels by network and by channel type (EH, HH, HN, EP, ...)
# Inputs: reference_tables/{ncss_catalog,dd_catalog,ldeo_ddrt_catalog,picks_ncss,station_channels}.csv
#         inputs/rtdd_catalog/{event,phase,station}.csv, reference_tables/stats_06.json
# Usage: python -I 11_summary_counts.py

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sr_common as C  # noqa: E402

BINS = [-9, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 9]
LABELS = ["<0.0", "0.0-0.5", "0.5-1.0", "1.0-1.5", "1.5-2.0", "2.0-2.5", "2.5-3.0", "3.0-3.5",
          ">=3.5"]


def main():
    out = []

    def add(section, item, value, note=""):
        out.append(dict(section=section, item=item, value=value, note=note))

    ev = pd.read_csv(os.path.join(C.TAB, "ncss_catalog.csv"))
    bev = ev[ev.benchmark_event].copy()
    dd = pd.read_csv(os.path.join(C.TAB, "dd_catalog.csv"))
    ld = pd.read_csv(os.path.join(C.TAB, "ldeo_ddrt_catalog.csv"))
    ld = ld[ld.is_dd.astype(str) == "True"]
    pk = pd.read_csv(os.path.join(C.TAB, "picks_ncss.csv"), keep_default_na=False,
                     dtype={"location": str})
    pk = pk[pk.benchmark_event.astype(str) == "True"]
    ph = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "phase.csv"), keep_default_na=False,
                     dtype={"locationCode": str})
    sta = pd.read_csv(os.path.join(C.INP, "rtdd_catalog", "station.csv"), keep_default_na=False,
                      dtype={"locationCode": str})
    chn = pd.read_csv(os.path.join(C.TAB, "station_channels.csv"), keep_default_na=False,
                      dtype={"location": str})
    s06 = json.load(open(os.path.join(C.TAB, "stats_06.json")))

    # ---- events
    add("events", "NCSS benchmark events (routine or DD location in box)", len(bev))
    add("events", "NCSS events, routine location in box", int(bev.in_box.sum()))
    add("events", "NCEDC DD events, DD location in box", int(dd.in_box.sum()))
    add("events", "LDEO NCAeqDDRT.v202201 DDRT solutions in box (supplementary reference)",
        int(ld.in_box.sum()))
    add("events", "first / last origin time (NCSS benchmark)",
        f"{bev.origin_time_utc.min()} / {bev.origin_time_utc.max()}")
    nomag = (bev.pref_mag.isna()) | ((bev.pref_mag == 0) & (bev.pref_mag_type == "N"))
    add("events", "NCSS benchmark events without magnitude", int(nomag.sum()),
        "preferred magnitude 0.00 with type N")
    add("events", "NCSS preferred magnitude types", bev.pref_mag_type.value_counts().to_dict())
    for name, mags in (("NCSS benchmark", bev.loc[~nomag, "pref_mag"]),
                       ("NCEDC DD box", dd.loc[dd.in_box, "magnitude"].dropna()),
                       ("LDEO DD-RT box", ld.loc[ld.in_box, "magnitude"].dropna())):
        cnt = pd.cut(mags, BINS, labels=LABELS, right=False).value_counts().reindex(LABELS)
        for lab, n in cnt.items():
            add(f"events per magnitude bin ({name})", f"M {lab}", int(n))
        add(f"events per magnitude bin ({name})", "max magnitude", float(mags.max()))
    days = pd.to_datetime(bev.origin_time_utc.str.rstrip("Z")).dt.date.value_counts().sort_index()
    for d, n in days.items():
        if n >= 10:
            add("events per day (NCSS benchmark, days with >= 10)", str(d), int(n))
    # ---- picks
    for scope, df, phcol in (("all NCSS picks of benchmark events", pk, "phase"),
                             ("rtDD phase.csv", ph, "type")):
        add("picks", f"{scope}: total", len(df))
        add("picks", f"{scope}: P", int((df[phcol] == "P").sum()))
        add("picks", f"{scope}: S", int((df[phcol] == "S").sum()))
    w = pk.groupby(["phase", "weight_code"]).size()
    for (p, c), n in w.items():
        add("picks by Hypoinverse weight code (all NCSS picks)", f"{p} code {c}", int(n))
    per = ph.groupby("eventId")["type"].value_counts().unstack(fill_value=0)
    per = per.reindex(bev.event_id, fill_value=0)
    for p in ("P", "S"):
        s = per[p] if p in per else pd.Series(0, index=per.index)
        add("picks per event (rtDD phase.csv)", f"{p}: min / median / mean / max",
            f"{int(s.min())} / {float(s.median()):.0f} / {float(s.mean()):.1f} / {int(s.max())}")
        add("picks per event (rtDD phase.csv)", f"events with 0 {p} picks", int((s == 0).sum()))
    add("picks per event (rtDD phase.csv)", "events with < 8 P picks", int((per.get("P", 0) < 8).sum()),
        "rtDD default clustering needs >= 8 phases per event pair")
    # ---- channel types
    pk["ctype"] = pk.channel.str[:2]
    ph["ctype"] = ph.channelCode.str[:2]
    for ct, g in pk.groupby("ctype"):
        add("picks by channel type (all NCSS picks)", ct,
            f"P {int((g.phase == 'P').sum())}, S {int((g.phase == 'S').sum())}")
    for ct, g in ph.groupby("ctype"):
        add("picks by channel type (rtDD phase.csv)", ct,
            f"P {int((g.type == 'P').sum())}, S {int((g.type == 'S').sum())}")
    pc = chn[chn.picked.astype(str) == "True"]
    for ct, g in pc.groupby(pc.channel.str[:2]):
        add("picked channels by type (stations.xml)", ct, int(len(g[["network", "station",
                                                                      "location", "channel"]].drop_duplicates())))
    # ---- stations
    add("stations", "net.sta.loc in rtDD station.csv", len(sta))
    for n, g in sta.groupby("networkCode"):
        add("stations by network (rtDD station.csv)", n, len(g))
    add("stations", "picked channels (benchmark events)", s06["picked_channels"])
    add("stations", "channels with response in stations.xml", s06["unique_channels_with_response"])
    add("stations", "picked channels without metadata", len(s06["picked_channels_without_metadata"]),
        "; ".join(s06["picked_channels_without_metadata"]))
    add("stations", "vertical-only sensors (no horizontal channel of the same sensor)",
        s06["n_vertical_only"], f"of {s06['n_sensor_groups_with_response']} sensor groups")
    pd.DataFrame(out).to_csv(os.path.join(C.TAB, "summary_counts.csv"), index=False)
    print(pd.DataFrame(out).to_string(max_colwidth=90))


if __name__ == "__main__":
    main()
