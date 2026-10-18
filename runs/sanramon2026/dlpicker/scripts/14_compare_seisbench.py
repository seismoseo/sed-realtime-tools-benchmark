# 14_compare_seisbench.py -- step 14 copy of runs/sanramon/dlpicker/scripts/12_compare_seisbench.py (San Ramon 2015, step 12; not modified).
# Changed: DATA = data/sanramon_2026. Nothing else.
#
# 12_compare_seisbench.py -- step 12 helper (conda env 'pyrtdd': pandas). Adapted from step 09's
# 09_compare_seisbench.py.
#
# For the weight set eqtp_ncedc, compares on the SeisBench test events
#   (a) the plugin's picks (scautopick runs of stage pick, as tabulated by 12_compare.py in
#       analysis/dl_picks_all.csv, variant <model> = binding set 'main') with
#   (b) SeisBench's continuous picking (12_seisbench_run.py: <model>_picks.csv) on the same raw streams.
# Pairing: one-to-one, closest first, same event file, NET.STA and phase, P within --p-tol, S within --s-tol;
# dt = plugin - SeisBench. Reported: pairs, median |dt|, fraction within 0.02 / 0.05 s, p95, mean, max; the
# polarity of paired P picks (both set; agreement); and each method against the NCSS analyst picks with the
# rules of 12_compare.py (recall over analyst picks at 3-C stations of these events, precision inside the
# event windows against analyst picks of any catalog event, polarity agreement with analyst first motions),
# plus how many analyst picks only one of the two found.
#
# Outputs (in --out-dir): compare_seisbench_pairs.csv, compare_seisbench_vs_reference.csv,
# compare_seisbench_summary.json

import argparse
import json

import numpy as np
import pandas as pd

PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/sanramon_2026"


def match(ref, sc, tol):
    # step T's match(), station key NET.STA ('nsta')
    pairs = []
    for i, r in ref.iterrows():
        cand = sc[sc["nsta"] == r["nsta"]]
        for j, s in cand.iterrows():
            dt = (s["time"] - r["time"]).total_seconds()
            if abs(dt) <= tol:
                pairs.append((abs(dt), dt, i, j))
    pairs.sort()
    used_r, used_s, out = set(), set(), {}
    for adt, dt, i, j in pairs:
        if i in used_r or j in used_s:
            continue
        used_r.add(i)
        used_s.add(j)
        out[i] = (j, dt)
    return out


def dstats(d):
    d = np.asarray(d, dtype=float)
    if len(d) == 0:
        return dict(n_pairs=0)
    ad = np.abs(d)
    return dict(n_pairs=int(len(d)), median_abs_dt_s=float(np.median(ad)),
                frac_within_0p02_s=float(np.mean(ad <= 0.02 + 1e-6)),
                frac_within_0p05_s=float(np.mean(ad <= 0.05 + 1e-6)),
                frac_identical=float(np.mean(ad <= 0.001)),
                p95_abs_dt_s=float(np.percentile(ad, 95)), mean_dt_s=float(d.mean()), max_abs_dt_s=float(ad.max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--events", nargs="+", required=True)
    ap.add_argument("--p-tol", type=float, default=0.5)
    ap.add_argument("--s-tol", type=float, default=1.0)
    ap.add_argument("--win-before", type=float, default=5.0)
    ap.add_argument("--win-after", type=float, default=60.0)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    tol = {"P": a.p_tol, "S": a.s_tol}
    R = a.run_dir

    ev = pd.read_csv(f"{DATA}/inputs/dl_subset_events.csv", dtype={"event_id": str}).set_index("event_id")
    ev["origin"] = pd.to_datetime(ev["origin_time_utc"], utc=True)
    picks = pd.read_csv(f"{DATA}/reference_tables/picks_ncss.csv", dtype={"event_id": str})
    picks = picks[picks["usable"]].copy()
    picks["time"] = pd.to_datetime(picks["time_utc"], utc=True, format="ISO8601")
    picks["nsta"] = picks["network"] + "." + picks["station"]
    refp = pd.read_csv(f"{R}/analysis/reference_picks.csv", dtype={"event_id": str})
    is3c = {(r.event_id, r.nsta, r.phase): bool(r.is_3c) for r in refp.itertuples()}
    tier = {(r.event_id, r.nsta, r.phase): r.tier for r in refp.itertuples()}
    miss = pd.read_csv(f"{R}/analysis/missed_reference_diagnosis.csv", dtype={"event_id": str})
    miss = miss[miss["variant"] == a.model]
    why = {(r.event_id, r.nsta, r.phase): r.why_missed for r in miss.itertuples()}

    pl = pd.read_csv(f"{R}/analysis/dl_picks_all.csv", dtype={"event_id": str})
    pl = pl[(pl["variant"] == a.model) & pl["event_id"].isin(a.events)].copy()
    pl["time"] = pd.to_datetime(pl["time"], utc=True, format="ISO8601")
    pl["fm"] = pl["polarity"].map({"positive": "U", "negative": "D"}).fillna("")
    pl["pconf"] = pl["polarity_confidence"]
    sb = pd.read_csv(f"{R}/seisbench/{a.model}_picks.csv", dtype={"event_id": str})
    sb["time"] = pd.to_datetime(sb["peak_time"], utc=True, format="ISO8601")
    sb["confidence"] = sb["peak_value"]
    sb["fm"] = sb["polarity"].fillna("").where(sb["polarity"].isin(["U", "D"]), "")
    sb["pconf"] = sb["polarity_value"]

    pairs = []
    for e in a.events:
        for ph in ("P", "S"):
            A = pl[(pl["event_id"] == e) & (pl["phase"] == ph)]
            B = sb[(sb["event_id"] == e) & (sb["phase"] == ph)]
            m = match(A, B, tol[ph])
            for i, (j, dt) in m.items():
                pairs.append(dict(event_id=e, nsta=A.loc[i, "nsta"], phase=ph, time_plugin=A.loc[i, "time"],
                                  time_seisbench=B.loc[j, "time"], dt_plugin_minus_seisbench_s=dt,
                                  conf_plugin=A.loc[i, "confidence"], conf_seisbench=B.loc[j, "confidence"],
                                  fm_plugin=A.loc[i, "fm"], pconf_plugin=A.loc[i, "pconf"],
                                  fm_seisbench=B.loc[j, "fm"], pconf_seisbench=B.loc[j, "pconf"]))
    pf = pd.DataFrame(pairs)
    pf.to_csv(f"{a.out_dir}/compare_seisbench_pairs.csv", index=False, float_format="%.4f")

    # each method vs the analyst picks (candidates: every catalog event's picks in the file span)
    rows = []
    for meth, D in (("plugin", pl), ("seisbench", sb)):
        for e in a.events:
            o = ev.loc[e, "origin"]
            cand = picks[(picks["time"] >= o - pd.Timedelta(seconds=120)) & (picks["time"] <= o + pd.Timedelta(seconds=120))].copy()
            De = D[D["event_id"] == e].copy()
            De["matched"] = False
            for ph in ("P", "S"):
                m = match(cand[cand["phase"] == ph], De[De["phase"] == ph], tol[ph])
                for i, (j, dt) in m.items():
                    De.loc[j, "matched"] = True
                    if cand.loc[i, "event_id"] == e:
                        rows.append(dict(method=meth, event_id=e, nsta=cand.loc[i, "nsta"], phase=ph, dt_s=dt,
                                         analyst_fm=cand.loc[i, "first_motion"] if isinstance(cand.loc[i, "first_motion"], str) else "",
                                         dl_fm=De.loc[j, "fm"], dl_pconf=De.loc[j, "pconf"], kind="matched"))
            inwin = De[(De["time"] >= o - pd.Timedelta(seconds=a.win_before)) & (De["time"] <= o + pd.Timedelta(seconds=a.win_after))]
            for x in inwin.itertuples():
                rows.append(dict(method=meth, event_id=e, nsta=x.nsta, phase=x.phase, matched_any=bool(x.matched),
                                 kind="in_window"))
    vr = pd.DataFrame(rows)
    vr.to_csv(f"{a.out_dir}/compare_seisbench_vs_reference.csv", index=False, float_format="%.4f")

    tgt = picks[picks["event_id"].isin(a.events)].copy()
    tgt["is_3c"] = [is3c.get((r.event_id, r.nsta, r.phase), False) for r in tgt.itertuples()]
    summ = dict(model=a.model, events=a.events, rules=f"P {a.p_tol} s, S {a.s_tol} s; window -{a.win_before}..+{a.win_after} s",
                plugin_vs_seisbench={}, vs_reference={}, found_by_only_one={})
    for ph in ("P", "S"):
        q = pf[pf["phase"] == ph] if len(pf) else pf
        d = dstats(q["dt_plugin_minus_seisbench_s"]) if len(q) else dict(n_pairs=0)
        d["n_plugin"] = int((pl["phase"] == ph).sum())
        d["n_seisbench"] = int((sb["phase"] == ph).sum())
        if ph == "P" and len(q):
            both = q[(q["fm_plugin"] != "") & (q["fm_seisbench"] != "")]
            d["polarity_both_set"] = int(len(both))
            d["polarity_agree"] = float((both["fm_plugin"] == both["fm_seisbench"]).mean()) if len(both) else np.nan
            d["polarity_set_plugin_only"] = int(((q["fm_plugin"] != "") & (q["fm_seisbench"] == "")).sum())
            d["polarity_set_seisbench_only"] = int(((q["fm_plugin"] == "") & (q["fm_seisbench"] != "")).sum())
        summ["plugin_vs_seisbench"][ph] = d
        T = tgt[(tgt["phase"] == ph) & tgt["is_3c"]]
        keys3 = set(zip(T["event_id"], T["nsta"]))
        found = {}
        for meth in ("plugin", "seisbench"):
            m = vr[(vr["method"] == meth) & (vr["kind"] == "matched") & (vr["phase"] == ph)]
            m3 = m[[k in keys3 for k in zip(m["event_id"], m["nsta"])]]
            w = vr[(vr["method"] == meth) & (vr["kind"] == "in_window") & (vr["phase"] == ph)]
            dd = dict(n_ref_3c=len(T), n_matched_3c=len(m3), recall_3c=len(m3) / len(T) if len(T) else np.nan,
                      n_in_window=len(w), precision=float(w["matched_any"].mean()) if len(w) else np.nan,
                      median_abs_dt_s=float(m3["dt_s"].abs().median()) if len(m3) else np.nan,
                      mean_dt_s=float(m3["dt_s"].mean()) if len(m3) else np.nan)
            if ph == "P":
                f = m3[m3["analyst_fm"].isin(["U", "D"])]
                h = f[f["dl_fm"] != ""]
                dd.update(polarity_matched_with_analyst_fm=len(f), polarity_coverage=len(h) / len(f) if len(f) else np.nan,
                          polarity_agreement=float((h["dl_fm"] == h["analyst_fm"]).mean()) if len(h) else np.nan)
            summ["vs_reference"].setdefault(ph, {})[meth] = dd
            found[meth] = set(zip(m3["event_id"], m3["nsta"]))
        only_sb = found["seisbench"] - found["plugin"]
        summ["found_by_only_one"][ph] = dict(only_seisbench=len(only_sb),
                                             only_plugin=len(found["plugin"] - found["seisbench"]),
                                             neither=len(keys3 - found["plugin"] - found["seisbench"]))
        # the analyst picks only SeisBench found: record tier and the plugin's miss reason (12_compare.py)
        summ["found_by_only_one"][ph]["only_seisbench_by_tier_and_plugin_reason"] = (
            pd.Series([f"{tier.get((e, n, ph), '?')} | {why.get((e, n, ph), '?')}" for e, n in only_sb])
            .value_counts().to_dict())
        for tname in ("3c_complete", "3c_incomplete"):
            kt = {k for k in keys3 if tier.get((k[0], k[1], ph)) == tname}
            summ["vs_reference"][ph][f"recall_{tname}"] = {
                meth: (len(found[meth] & kt) / len(kt) if kt else None) for meth in ("plugin", "seisbench")}
            summ["vs_reference"][ph][f"n_{tname}"] = len(kt)
    with open(f"{a.out_dir}/compare_seisbench_summary.json", "w") as f:
        json.dump(summ, f, indent=1, default=str)
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
