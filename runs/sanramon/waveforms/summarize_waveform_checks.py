#!/usr/bin/env python
# summarize_waveform_checks.py -- tables for docs/sanramon_waveforms.md from the outputs of
# data/sanramon_2015/tools/check_waveforms.py (reference_tables/waveform_*.csv, stats_20_waveforms.json).
#
# Writes (this folder):
#   pick_fraction_by_channel_type.csv  every pick of rtDD phase.csv (25,684) by phase and channel type:
#                                      within the 60 km waveform plan, data on the picked channel, data on
#                                      the components rtDD correlates (P: vertical, S: both horizontals)
#   partial_windows_cc.csv             the cross-correlation request windows that are not one complete piece
#   partial_windows_affecting_picks.csv picks whose rtDD window touches such a gap
# Usage (env pyrtdd): python -I summarize_waveform_checks.py      (read-only on the data)

import json

import pandas as pd

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
SR = f"{PROJECT}/data/sanramon_2015"
TAB = f"{SR}/reference_tables"
OUT = f"{PROJECT}/runs/sanramon/waveforms"


def main():
    ph = pd.read_csv(f"{SR}/inputs/rtdd_catalog/phase.csv", keep_default_na=False, dtype=str)
    pc = pd.read_csv(f"{TAB}/waveform_pick_coverage.csv", keep_default_na=False, dtype=str)
    pc = pc[(pc.set == "cc") & (pc.in_phase_csv == "True")]
    ph["channel_type"] = ph.channelCode.str[:2]
    ph["key"] = ph.eventId + "|" + ph.type + "|" + ph.networkCode + "." + ph.stationCode + "." + \
        ph.locationCode + "." + ph.channelCode
    pc["key"] = pc.event_id + "|" + pc.phase + "|" + pc.network + "." + pc.station + "." + pc.location + \
        "." + pc.channel
    m = ph.merge(pc[["key", "covered_pick_channel", "covered_rtdd_components", "rtdd_components"]],
                 on="key", how="left")
    m["in_plan"] = m.covered_pick_channel.notna()
    m["data_pick_channel"] = m.covered_pick_channel == "True"
    m["data_rtdd_components"] = m.covered_rtdd_components == "True"
    rows = []
    for (t, c), g in list(m.groupby(["type", "channel_type"])) + [((t, "all"), g) for t, g in m.groupby("type")] + \
            [(("all", "all"), m)]:
        rows.append(dict(phase=t, channel_type=c, picks=len(g), within_60km_plan=int(g.in_plan.sum()),
                         data_on_pick_channel=int(g.data_pick_channel.sum()),
                         data_on_rtdd_components=int(g.data_rtdd_components.sum()),
                         frac_data_pick_channel=round(g.data_pick_channel.mean(), 4),
                         frac_data_rtdd_components=round(g.data_rtdd_components.mean(), 4),
                         s_without_two_horizontals=int((g.rtdd_components == "no 2 horizontals").sum())))
    t = pd.DataFrame(rows)
    t.to_csv(f"{OUT}/pick_fraction_by_channel_type.csv", index=False)
    print(t.to_string())

    cov = pd.read_csv(f"{TAB}/waveform_coverage_cc.csv", keep_default_na=False, dtype={"location": str})
    bad = cov[(cov.coverage < 0.999) | (cov.n_pieces > 1)].copy()
    bad.to_csv(f"{OUT}/partial_windows_cc.csv", index=False)
    print(f"\npartial cc windows: {len(bad)}; events {bad.event_id.nunique()}; channels "
          f"{bad[['network', 'station', 'location', 'channel']].drop_duplicates().shape[0]}")
    print(bad.groupby("event_id").agg(n=("channel", "size"), min_cov=("coverage", "min"),
                                     max_pieces=("n_pieces", "max")).to_string())
    print(bad[["event_id", "network", "station", "location", "channel", "coverage", "n_pieces",
               "first_sample", "last_sample"]].to_string())
    # picks of those event/sensor pairs whose rtDD window is NOT covered
    allpc = pd.read_csv(f"{TAB}/waveform_pick_coverage.csv", keep_default_na=False, dtype=str)
    allpc = allpc[allpc.set == "cc"]
    nc = allpc[(allpc.covered_rtdd_components != "True") & (allpc.rtdd_components != "no 2 horizontals")]
    nc.to_csv(f"{OUT}/partial_windows_affecting_picks.csv", index=False)
    print(f"\npicks (any, cc set) whose rtDD component window is not covered although the components exist: "
          f"{len(nc)}")
    print(nc[["event_id", "phase", "network", "station", "location", "channel", "in_phase_csv"]].to_string())
    s = json.load(open(f"{TAB}/stats_20_waveforms.json"))
    print(json.dumps(s["cc"]["dayfiles"]))


if __name__ == "__main__":
    main()
