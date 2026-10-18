# 14_polarity_reference_check.py -- step 14 copy of runs/sanramon/dlpicker/scripts/12_polarity_reference_check.py
# (San Ramon 2015, step 12; not modified). Changed for the 2025-26 case, nothing else in the test:
#   - DATA = data/sanramon_2026;
#   - channel sense: step 12 kept the epochs open during 2015-10/11 (one per channel). The 2025-26 period is one
#     year and 242 channels have two epochs in it, so here each pick gets the sense of the epoch that is open at
#     the pick time (falls back to 'unknown' if none);
#   - an extra result 'analyst_only' repeats the test with data_source 'J' picks only (2025-26 has 2,489
#     automatic 'R' picks; 2015 had 47). The main result uses every usable pick, as in step 12.
#
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
DATA = f"{PROJECT}/data/sanramon_2026"


def utc(x):
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


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
    epochs = {}                                   # (net, sta, loc, cha) -> [(start, end, dip, gain), ...]
    for net in root.iter(f"{ns}network"):
        for sta in net.findall(f"{ns}station"):
            for loc in sta.findall(f"{ns}sensorLocation"):
                for s in loc.findall(f"{ns}stream"):
                    st, en = s.findtext(f"{ns}start"), s.findtext(f"{ns}end")
                    if (en and en < "2025-10-01") or st > "2026-10-18":
                        continue
                    dip = float(s.findtext(f"{ns}dip") or "nan")
                    gain = float(s.findtext(f"{ns}gain") or "nan")
                    k = (net.get("code"), sta.get("code"), loc.get("code") or "", s.get("code"))
                    epochs.setdefault(k, []).append((utc(st), utc(en) if en else None, dip, gain))

    def epoch_at(k, t):
        for st_, en_, dip_, gain_ in epochs.get(k, []):
            if st_ <= t and (en_ is None or en_ > t):
                return dip_, gain_
        return None

    p = pd.read_csv(f"{DATA}/reference_tables/picks_ncss.csv", dtype={"event_id": str, "location": str})
    p = p[(p["phase"] == "P") & p["first_motion"].isin(["U", "D"]) & p["usable"]].copy()
    p["location"] = p["location"].fillna("")
    keys = list(zip(p["network"], p["station"], p["location"], p["channel"]))
    tt = pd.to_datetime(p["time_utc"], utc=True)
    dg = [epoch_at(k, t) for k, t in zip(keys, tt)]
    p["sense"] = ["unknown" if x is None else ("inverted" if (x[0] > 0) != (x[1] < 0) else "direct") for x in dg]
    p["dip"] = [np.nan if x is None else x[0] for x in dg]
    p["gain"] = [np.nan if x is None else x[1] for x in dg]
    p_all = p

    def run_once(p):
        return _run(p, a)

    res_all, inv, per = run_once(p_all)
    res_j, _, _ = run_once(p_all[p_all["data_source"] == "J"])
    per.to_csv(f"{R}/analysis/polarity_reference_check.csv", index=False, float_format="%.3f")
    res = res_all
    res["analyst_only"] = {k: v for k, v in res_j.items() if k != "per_channel"}
    res["n_unknown_sense"] = int((p_all["sense"] == "unknown").sum())
    with open(f"{R}/analysis/polarity_reference_check.json", "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"inverted-channel analyst first motions tested: {res['inverted_tests']}; same as direct neighbours: "
          f"{res['inverted_frac_same']:.3f} | control (direct channels): {res['control_tests']} tests, {res['control_frac_same']:.3f}")
    print(f"analyst ('J') picks only: inverted {res_j['inverted_tests']} tests, {res_j['inverted_frac_same']}; "
          f"control {res_j['control_tests']} tests, {res_j['control_frac_same']}; picks with no open epoch: {res['n_unknown_sense']}")
    print(per.to_string(index=False))


def _run(p, a):
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
    res = dict(rule=f"neighbours: same event, direct channel, |daz| <= {a.daz}, |dtakeoff| <= {a.dtoa}, >= {a.min_neigh}, "
                    f"majority >= 70 %", n_inverted_channel_picks=int((p["sense"] == "inverted").sum()),
               n_direct_channel_picks=int((p["sense"] == "direct").sum()),
               inverted_tests=int(len(inv)), inverted_frac_same=float(inv["same"].mean()) if len(inv) else None,
               control_tests=int(len(ctrl)), control_frac_same=float(ctrl["same"].mean()) if len(ctrl) else None,
               per_channel=per.to_dict("records"))
    return res, inv, per


if __name__ == "__main__":
    main()
