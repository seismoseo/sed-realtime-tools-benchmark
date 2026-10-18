# 12_polarity_reference_check.py -- step 12 helper (conda env 'pyrtdd': pandas).
#
# Question: do the NCSS analyst first motions on channels whose metadata say "inverted" (a vertical with a
# NEGATIVE gain, or one pointing down, dip +90) refer to the ground motion or to the raw counts? The plugin
# turns its polarity into ground motion from the inventory (VerticalPolaritySense); 12_compare.py found that
# on such channels the analyst agrees with the plugin's RAW-COUNT polarity much more often. This script
# checks the analyst picks themselves, independently of any DL model:
#   for every analyst P first motion (U/D, usable picks of all 685 benchmark events) on an inverted channel,
#   take the analyst first motions of the SAME event on direct (normal) channels with a similar ray: azimuth
#   within --daz deg and take-off angle within --dtoa deg (NCSS's own azimuth/take-off columns), at least
#   --min-neigh of them, and a clear majority (>= 70 % U or >= 70 % D). Similar rays see the same part of
#   the radiation pattern, so the inverted channel's first motion should usually equal that majority IF it
#   refers to ground motion.
#   Control: the same test for a random sample of picks on direct channels.
# Channel sense (dip, gain sign) comes from the SeisComP inventory scautopick read (config/inventory_sc.xml),
# epoch open during 2015-10/11.
# Outputs: analysis/polarity_reference_check.csv (per channel), analysis/polarity_reference_check.json

import argparse
import json
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/sanramon_2015"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--daz", type=float, default=10.0)
    ap.add_argument("--dtoa", type=float, default=10.0)
    ap.add_argument("--min-neigh", type=int, default=2)
    ap.add_argument("--control-n", type=int, default=3000)
    a = ap.parse_args()
    R = a.run_dir

    root = ET.parse(f"{R}/config/inventory_sc.xml").getroot()
    ns = root.tag.split("}")[0] + "}"
    sense, meta = {}, {}
    for net in root.iter(f"{ns}network"):
        for sta in net.findall(f"{ns}station"):
            for loc in sta.findall(f"{ns}sensorLocation"):
                for s in loc.findall(f"{ns}stream"):
                    st, en = s.findtext(f"{ns}start"), s.findtext(f"{ns}end")
                    if (en and en < "2015-10-01") or st > "2015-12-01":
                        continue
                    dip = float(s.findtext(f"{ns}dip") or "nan")
                    gain = float(s.findtext(f"{ns}gain") or "nan")
                    k = (net.get("code"), sta.get("code"), loc.get("code") or "", s.get("code"))
                    sense[k] = "inverted" if (dip > 0) != (gain < 0) else "direct"
                    meta[k] = (dip, gain)

    p = pd.read_csv(f"{DATA}/reference_tables/picks_ncss.csv", dtype={"event_id": str, "location": str})
    p = p[(p["phase"] == "P") & p["first_motion"].isin(["U", "D"]) & p["usable"]].copy()
    p["location"] = p["location"].fillna("")
    keys = list(zip(p["network"], p["station"], p["location"], p["channel"]))
    p["sense"] = [sense.get(k, "unknown") for k in keys]
    p["dip"] = [meta.get(k, (np.nan, np.nan))[0] for k in keys]
    p["gain"] = [meta.get(k, (np.nan, np.nan))[1] for k in keys]
    direct = p[p["sense"] == "direct"]
    by_ev = {e: g for e, g in direct.groupby("event_id")}

    def test(rows):
        out = []
        for r in rows.itertuples():
            d = by_ev.get(r.event_id)
            if d is None:
                continue
            daz = ((d["azimuth_deg"] - r.azimuth_deg + 180) % 360 - 180).abs()
            nb = d[(daz <= a.daz) & ((d["takeoff_deg"] - r.takeoff_deg).abs() <= a.dtoa) & (d["station"] != r.station)]
            if len(nb) < a.min_neigh:
                continue
            fu = (nb["first_motion"] == "U").mean()
            if 0.3 < fu < 0.7:
                continue
            out.append(dict(event_id=r.event_id, network=r.network, station=r.station, channel=r.channel,
                            dip=r.dip, gain=r.gain, analyst_fm=r.first_motion, neighbour_majority="U" if fu >= 0.7 else "D",
                            n_neighbours=len(nb), same=r.first_motion == ("U" if fu >= 0.7 else "D")))
        return pd.DataFrame(out)

    inv = test(p[p["sense"] == "inverted"])
    ctrl = test(direct.sample(min(a.control_n, len(direct)), random_state=620))
    per = (inv.groupby(["network", "station", "channel"])
           .agg(dip=("dip", "first"), gain=("gain", "first"), n_tests=("same", "size"),
                frac_same_as_direct_neighbours=("same", "mean")).reset_index())
    per.to_csv(f"{R}/analysis/polarity_reference_check.csv", index=False, float_format="%.3f")
    res = dict(rule=f"neighbours: same event, direct channel, |daz| <= {a.daz}, |dtakeoff| <= {a.dtoa}, >= {a.min_neigh}, "
                    f"majority >= 70 %", n_inverted_channel_picks=int((p["sense"] == "inverted").sum()),
               n_direct_channel_picks=int((p["sense"] == "direct").sum()),
               inverted_tests=int(len(inv)), inverted_frac_same=float(inv["same"].mean()) if len(inv) else None,
               control_tests=int(len(ctrl)), control_frac_same=float(ctrl["same"].mean()) if len(ctrl) else None,
               per_channel=per.to_dict("records"))
    with open(f"{R}/analysis/polarity_reference_check.json", "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"inverted-channel analyst first motions tested: {len(inv)}; same as direct neighbours: "
          f"{res['inverted_frac_same']:.3f} | control (direct channels): {len(ctrl)} tests, {res['control_frac_same']:.3f}")
    print(per.to_string(index=False))


if __name__ == "__main__":
    main()
