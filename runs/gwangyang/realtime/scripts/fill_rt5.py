# fill_rt5.py -- kept from the real-time step: it filled the RT5 rows of docs/results/10_gwangyang_realtime.md (moved here from the session scratchpad on 2026-10-17).
# fill_rt5.py -- one-off helper: fills the RT5 placeholders of docs/results/10_gwangyang_realtime.md from the
# computed tables (RT5 results/delays.csv, positions, network/after_stop.json, offline_check_failed). Prints the
# values it used so they can be checked against the tables.
import csv
import json
import sys

P = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
RT = f"{P}/runs/gwangyang/realtime/RT5_paced_creationtime"
DOC = f"{P}/docs/results/10_gwangyang_realtime.md"

dl = {r["kma_id"]: r for r in csv.DictReader(open(f"{RT}/results/delays.csv"))}
pos = list(csv.DictReader(open(f"{RT}/results/positions_vs_reference.csv")))


def f1(x):
    return f"{float(x):.1f}"


def lat(r, k):
    v = r.get(f"latency_{k}_after_origin_time_s", "")
    return f1(v) + " s" if v not in ("", None) else "-"


def dist(kma, label):
    for p in pos:
        if p["kma_id"] == kma and p["solution"] == label and p["versus"] == "S1" and p["kind"] == "absolute":
            return float(p["d3D_m"])
    return None


vals = {}
for kma, tag in (("20210827220322", "E3"), ("20260202194119", "E9")):
    r = dl[kma]
    vals[f"RT5_{tag}_FIRSTPICK"] = lat(r, "first_DL_pick_created")
    vals[f"RT5_{tag}_PLAT"] = f"{f1(r['DL3C_latency_after_pick_time_median_s'])} / {f1(r['DL3C_latency_after_pick_time_p90_s'])} s"
    vals[f"RT5_{tag}_SLAT"] = f"{f1(r['SDL3C_latency_after_pick_time_median_s'])} / {f1(r['SDL3C_latency_after_pick_time_p90_s'])} s"
    vals[f"RT5_{tag}_ORIG"] = f"{lat(r, 'first_origin_created')[:-2]} / {lat(r, 'event_created')}"
    n_rtdd = int(r["n_RTDD_origins"])
    first = lat(r, "RTDD_1_created")
    lastl = lat(r, f"RTDD_{n_rtdd}_created")
    inp1 = r.get("RTDD_1_input_n_P", "")
    failed = int(r.get("scrtdd_failed_attempts") or 0)
    note = f" (from the {int(float(inp1))}-phase origin)" if inp1 else ""
    if failed:
        orgs = {o["publicID"]: o for o in csv.DictReader(open(f"{RT}/results/origins.csv"))}
        fp = []
        for fid in ["Origin/" + x for x in r["scrtdd_failed_inputs"].split("Origin/") if x]:
            fp.append(orgs[fid.rstrip("/")]["n_arr_P"])
        note += f"; the attempt on the {', '.join(fp)}-phase version before it failed"
    vals[f"RT5_{tag}_RTDD1"] = f"**{first}**{note}"
    nP = r["scautoloc_versions_n_P"].split("/")
    vals[f"RT5_{tag}_LAST"] = f"{lat(r, 'final_scautoloc_origin_created')} ({nP[-1]} phases)"
    vals[f"RT5_{tag}_RTDDL"] = lastl
    d1, dn = dist(kma, "RTDD_1"), dist(kma, f"RTDD_{n_rtdd}")
    vals[f"RT5_{tag}_DIST"] = f"{d1:.1f} / {dn:.1f} m" if n_rtdd > 1 else f"{d1:.1f} m (one RTDD origin)"
stop = json.load(open(f"{RT}/network/after_stop.json"))["stop"]
ap = [v for k, v in json.load(open(f"{RT}/results/summary.json"))["cost_cpu_s"].items() if k.startswith("scautopick") and isinstance(v, dict)]
vals["RT5_COST_PICK"] = " + ".join(f"{x['cpu_s']:.2f}" for x in ap)
vals["RT5_COST_RTDD"] = f"{stop['scrtdd']['cpu_s']:.2f}"
vals["RT5_COST_LOC"] = f"{stop['scautoloc']['cpu_s']:.2f}"
vals["RT5_COST_EV"] = f"{stop['scevent']['cpu_s']:.2f}"
vals["RT5_COST_MASTER"] = f"{stop['scmaster']['cpu_s']:.2f}"
for k, v in vals.items():
    print(f"{k:22s} {v}")
if "--apply" in sys.argv:
    s = open(DOC).read()
    for k, v in vals.items():
        if k not in s:
            print("placeholder not found:", k)
        s = s.replace(k, v)
    open(DOC, "w").write(s)
    print("filled", DOC)
