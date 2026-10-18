# build_03_gwangyang_dlpicker.py -- writes notebooks/03_gwangyang_dlpicker.ipynb (markdown + code cells).
#
# Run in conda env 'pyrtdd':
#   python build_03_gwangyang_dlpicker.py
# then execute (kernel 'pyrtdd'):
#   jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=pyrtdd \
#       --ExecutePreprocessor.timeout=1800 03_gwangyang_dlpicker.ipynb
#
# The notebook only LOADS the result files of step 09 (runs/gwangyang/dlpicker/) and visualizes them: no picking,
# no relocation. Every emitted code cell is compiled with compile(..., 'exec') before the notebook is written;
# code cells carry '#' comments only (no docstrings). Small helpers live in notebooks/lib/nb03_helpers.py.
# Markdown cells quote parameter values as [[NAME]] or [[NAME:i]] (element i of a tuple or list); they are filled
# from the parameter cell itself, which is executed once here. Result numbers are never typed into markdown:
# they are printed by code cells from the loaded files.

import re

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/notebooks/03_gwangyang_dlpicker.ipynb"
CELLS = []
PAR = {}


def pretty(v):
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def fill(text):
    def rep(m):
        name, _, idx = m.group(1).partition(":")
        v = PAR[name]
        return pretty(v[int(idx)] if idx else v)
    out = re.sub(r"\[\[([A-Z][A-Z_0-9]*(?::\d+)?)\]\]", rep, text)
    assert "[[" not in out, out[out.index("[["):out.index("[[") + 40]
    return out


def md(text):
    CELLS.append(new_markdown_cell(fill(text.strip("\n"))))


def code(text):
    CELLS.append(new_code_cell(text.strip("\n")))


PARAM_CELL = r"""
# ============================== PARAMETERS ==============================
# every setting of this notebook; nothing below changes these values (the markdown text quotes them)
import time as _time
T_START = _time.time()                             # the run time is printed at the very end
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
RUN = f"{PROJECT}/runs/gwangyang/dlpicker"         # step 09 (scautopick + scdlrtpicker), read only
ANA = f"{RUN}/analysis"                            # comparison tables of step 09
SB_DIR = f"{RUN}/seisbench"                        # SeisBench cross-check of step 09
RELOC = f"{RUN}/reloc"                             # pyrtdd relocations from the DL picks (step 09)
SETTINGS_DIR = f"{RUN}/settings"                   # resolved scautopick and plugin settings per variant
PICK_DIR = f"{RUN}/output"                         # scautopick logs per variant and event (error/warning count)
PLAYBACK_DIR = f"{RUN}/input"                      # miniSEED files scautopick read (only to check the SAC copies)
NOTE09 = f"{PROJECT}/docs/results/09_gwangyang_dlpicker.md"   # only to cross-check a few quoted numbers
OUT = f"{PROJECT}/runs/gwangyang/dlpicker_nb03"    # what this notebook writes: key-number table, summary.json
FIG_DIR = f"{PROJECT}/notebooks/figures"           # every figure as 03_*.png (200 dpi) and 03_*.pdf
LIB = f"{PROJECT}/notebooks/lib"                   # nbfont.py and nb03_helpers.py

# --- reference (PhaseNet+) and events ---
REF_PICKS = f"{DATA}/reference_tables/picks_phasenet_plus.csv"   # the PhaseNet+ reference picks
EVENT_ID_MAP = f"{DATA}/reference_tables/event_id_map.csv"       # event number, KMA origin time and magnitude
HYPODD_DTCC = f"{DATA}/reference_tables/hypodd_dtcc.csv"         # HypoDD dt.cc positions (checked against Figure 9's file)
WAVEFORMS = f"{DATA}/reference/gwangyang_pnplus/waveforms_100km" # SAC, 100 Hz, counts (Figure 4)

# --- the picker runs compared (step 09 names) ---
VARIANTS = ["phasenet_original", "phasenet_instance", "phasenet_instance_fast", "eqtransformer_stead", "phasenet_stead"]
FAST, RELIABLE = "phasenet_instance_fast", "phasenet_instance"   # Figure 7: same model, fast and reliable P settings
SB_MODELS = ["phasenet_instance", "eqtransformer_stead"]         # Figure 6: the models also run in SeisBench
FS_HZ = 100.0                                                     # sampling rate of the data and of the models

# --- Figure 2 ---
DT_XLIM_S = 0.30          # x-range of the time-difference histograms, +-0.30 s (pairs beyond it are counted)
DT_BIN_S = 0.01           # bin width = one sample

# --- Figure 4 (waveforms) ---
BAND_HZ = (5.0, 20.0)     # band-pass
FILTER_CORNERS = 4
FILTER_ZEROPHASE = False  # causal (one pass): cannot move energy ahead of an onset
TAPER_FRACTION = 0.05     # taper of the whole ~7.5-min record before filtering
WF_SENSORS = ["HH", "HG"] # per event: the nearest and the farthest station of each of these sensor types
WF_OVERVIEW_S = (-2.0, 3.0)   # left column: 2 s before the reference P pick to 3 s after the reference S pick
WF_ZOOM_S = (-1.0, 1.0)       # middle column (vertical, on the P pick) and right column (horizontals, on the S pick)

# --- Figure 6 ---
SB_HIST_LIM = 15          # plugin minus SeisBench in whole samples, shown from -15 to +15 (pairs beyond are counted)

# --- Figure 9 ---
MAP_SOLUTIONS = ["hypodd_dtcc", "hypodd_dtct", "control_phasenet_plus", "dl_phasenet_original_window"]
RMS_SOLUTIONS = ["all_at_centroid", "hypodd_dtct", "control_phasenet_plus", "control_phasenet_plus_same_subset",
                 "dl_phasenet_original_window", "dl_phasenet_original_window_tt", "dl_phasenet_original_matched_only",
                 "dl_phasenet_instance_window", "dl_phasenet_instance_window_tt", "dl_eqtransformer_stead_window",
                 "dl_phasenet_stead_window"]
"""
exec(PARAM_CELL, PAR)

# =====================================================================================================
md(r"""
# Gwangyang: the deep-learning picker inside SeisComP (scdlrtpicker)

**What is checked here.** SED's scdlrtpicker plugin puts deep-learning (DL) phase pickers inside SeisComP's
automatic picker *scautopick*: the usual detector (an STA/LTA trigger) finds candidate arrivals, and a neural network
(an ONNX model) decides whether and exactly where there is a P arrival in a window around each trigger. After a P pick
it starts a second network that looks for the S arrival. Step 09 of this project ran the plugin offline on the
Gwangyang benchmark (11 KMA events from 2021-07 to 2026-02, KMA magnitude $\mathit{M}_{\mathrm{L}}$ 1.1-2.2, 54 KS
stations within 100 km) with four models and one "fast" variant, compared the picks with the PhaseNet+ reference
picks, cross-checked them against SeisBench running the same weights, measured the cost, and relocated the events
with pyrtdd from the DL picks.

**This notebook does no picking and no relocation.** It loads the result files of step 09 (verified and corrected
after the independent verification, `docs/results/fixes_after_verification.md`), recomputes every summary number it
shows from the per-pick files as a check, and draws nine figures. Every number in the text below a figure is
formatted from the loaded files; none is typed in.

**Read every "agreement" number with this in mind.** PhaseNet+ is itself an automatic picker. "Matched" means
"agrees with PhaseNet+", not "is right". Where the two disagree, either one can be wrong.

**Terms used throughout, in plain words**

- *Pick*: the time at which a program (or a person) marks the arrival of a wave at a station.
- *P and S waves*: the P wave (compressional) is faster and arrives first; the S wave (shear) arrives later and is
  strongest on the horizontal components.
- *Reference picks*: the PhaseNet+ picks of the Gwangyang benchmark, the picks the published locations rest on.
- *Model / variant*: one trained network (for example PhaseNet trained on the INSTANCE data set). A *variant* is a
  model plus scautopick settings; the *fast* variant is PhaseNet (INSTANCE weights) with the README's fast P settings.
- *Match*: a DL pick and a reference pick of the same event, station and phase whose times are within the matching
  tolerance (table in section 1.3). Pairs are formed one-to-one, closest first.
- *Recall*: of all the arrivals that PhaseNet+ picked, the share that the DL picker also picked. "Did it find what
  PhaseNet+ found?"
- *Precision*: of all the picks the DL picker made inside the event windows, the share that has a PhaseNet+ partner.
  "Are its picks ones that PhaseNet+ agrees with?" An unmatched DL pick is not necessarily wrong: it can be a real
  arrival that PhaseNet+ missed, so precision is a lower bound on the share of good picks.
- *F1*: one number that combines recall (R) and precision (P), F1 = 2RP / (R + P), their harmonic mean. It is high
  only when both are high.
- *dt*: DL pick time minus PhaseNet+ pick time of a matched pair. *Median |dt|* is the typical size of the difference,
  *p95 |dt|* the size that 95% of the pairs stay below, and *MAD* the median distance of dt from its own median (a
  robust width of the distribution).
- *minConfidence*: the smallest network output (between 0 and 1) that the plugin accepts as a pick.
- *Station-hour*: one hour of data at one station; rates of picks outside the event windows are given per station-hour.
- *Double-difference (DD) relocation*: finds where events are relative to each other from differences of travel
  times between pairs of events at the same station. *Catalog-only* DD uses the picks alone; *dt.cc* DD also uses
  waveform cross-correlation and is the most precise solution here.

**Contents**

0. Parameters, imports
1. Inputs, consistency checks and the settings of the runs
2. Figure 1: recall, precision and F1 per model and phase
3. Figure 2: pick-time differences against PhaseNet+
4. Figure 3: recall by event magnitude, distance and sensor type
5. Figure 4: example waveforms of a large and a small event
6. Figure 5: why PhaseNet+ picks were missed
7. Figure 6: plugin against SeisBench with the same weights
8. Figure 7: fast against reliable P settings
9. Figure 8: picks outside the event windows and CPU cost
10. Figure 9: double-difference relocation from the DL picks
11. Comprehensive summary
""")

md(r"""
## 0. Parameters

Every setting of this notebook is in the next cell: the input folders, the five picker runs, the histogram ranges,
the waveform filter and windows, and the relocation solutions shown. Nothing further down changes them.
""")

code(PARAM_CELL)

code(r"""
# imports, Helvetica, versions, colors and labels
import os
import sys
import glob
import json
import re
import textwrap
import importlib
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from IPython.display import display, Markdown
import obspy
from obspy import read, UTCDateTime

sys.path.insert(0, LIB)
import nbfont
import nb03_helpers as h
importlib.reload(h)

FONT_FAMILY = nbfont.use_helvetica(verbose=True)
print("resolved font family:", FONT_FAMILY, "| font file matplotlib uses for text:",
      matplotlib.font_manager.findfont(matplotlib.font_manager.FontProperties(family=["sans-serif"])))
plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.0, "axes.labelsize": 9, "legend.fontsize": 8,
                     "xtick.labelsize": 8, "ytick.labelsize": 8, "figure.dpi": 100, "hatch.linewidth": 0.7,
                     "mathtext.cal": "Helvetica:italic"})   # unused calligraphic slot; avoids a 'cursive' font lookup
os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
pd.set_option("display.width", 230)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 120)

ML = r"$\mathit{M}_{\mathrm{L}}$"
# one color and one marker per picker, kept in every figure; the DL models and PhaseNet+ as in notebook 05, Figure D
COL = {"phasenet_plus": "#0072B2", "phasenet_original": "#E69F00", "phasenet_instance": "#56B4E9",
       "phasenet_instance_fast": "#D55E00", "eqtransformer_stead": "#009E73", "phasenet_stead": "#CC79A7"}
MARK = {"phasenet_plus": "^", "phasenet_original": "s", "phasenet_instance": "D", "phasenet_instance_fast": "X",
        "eqtransformer_stead": "v", "phasenet_stead": "P"}
LABEL = {"phasenet_plus": "PhaseNet+ (reference)", "phasenet_original": "PhaseNet (original weights)",
         "phasenet_instance": "PhaseNet (INSTANCE weights)",
         "phasenet_instance_fast": "PhaseNet (INSTANCE weights), fast P settings",
         "eqtransformer_stead": "EQTransformer (STEAD weights)", "phasenet_stead": "PhaseNet (STEAD weights)"}
SHORT = {"phasenet_original": "PhaseNet original", "phasenet_instance": "PhaseNet INSTANCE",
         "phasenet_instance_fast": "PhaseNet INSTANCE fast", "eqtransformer_stead": "EQTransformer STEAD",
         "phasenet_stead": "PhaseNet STEAD"}
TICK = {v: SHORT[v].replace(" ", "\n", 1) for v in SHORT}
FIGS = {}
print("versions: numpy", np.__version__, "| pandas", pd.__version__, "| obspy", obspy.__version__,
      "| matplotlib", matplotlib.__version__)
""")

# =====================================================================================================
md(r"""
## 1. Inputs, consistency checks and settings

### 1.1 The result files of step 09

All tables below are read as they are on disk. The next cell lists each file with its modification time and size,
so that it is clear which version was plotted.
""")

code(r"""
# 1.1 load every result file of step 09 that the figures use
def ts_utc(s):
    # POSIX seconds of time strings such as '2021-07-20 16:14:21.578000+00:00' (independent of pandas' datetime unit)
    t = pd.to_datetime(pd.Series(s), utc=True, format="mixed")
    return ((t - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()).to_numpy()


FILES = {
    "summary_by_model": f"{ANA}/summary_by_model.csv", "by_event": f"{ANA}/by_event.csv",
    "by_distance": f"{ANA}/by_distance.csv", "by_sensor": f"{ANA}/by_sensor.csv", "by_magnitude": f"{ANA}/by_magnitude.csv",
    "reference_vs_dl": f"{ANA}/reference_vs_dl.csv", "dl_picks_all": f"{ANA}/dl_picks_all.csv",
    "missed_reference_diagnosis": f"{ANA}/missed_reference_diagnosis.csv",
    "unmatched_in_window": f"{ANA}/unmatched_in_window.csv", "outside_window": f"{ANA}/outside_window.csv",
    "station_hours": f"{ANA}/station_hours.csv", "cost": f"{ANA}/cost.csv", "cost_per_run": f"{ANA}/cost_per_run.csv",
    "fast_vs_reliable": f"{ANA}/fast_vs_reliable.csv", "fast_vs_reliable_latency": f"{ANA}/fast_vs_reliable_latency.csv",
    "summary_json": f"{ANA}/summary.json", "best_model": f"{ANA}/best_model.json",
    "seisbench_pairs": f"{SB_DIR}/compare_seisbench_pairs.csv", "seisbench_summary": f"{SB_DIR}/compare_seisbench_summary.json",
    "seisbench_vs_reference": f"{SB_DIR}/compare_seisbench_vs_reference.csv",
    "seisbench_run_4_threads": f"{SB_DIR}/run.json", "seisbench_run_1_thread": f"{SB_DIR}/threads1/run.json",
    "seisbench_weights_check": f"{SB_DIR}/weights_check.json",
    "reloc_positions": f"{RELOC}/positions.csv", "reloc_compare_pairs": f"{RELOC}/compare_pairs.csv",
    "reloc_centroid_shift": f"{RELOC}/centroid_shift_from_start.csv", "reloc_summary": f"{RELOC}/reloc_summary.json",
    "reference_picks": REF_PICKS, "event_id_map": EVENT_ID_MAP, "hypodd_dtcc": HYPODD_DTCC}
display(pd.DataFrame([{"Name": k, "File": v.replace(PROJECT + "/", ""),
                       "Modified (local time)": pd.Timestamp(os.path.getmtime(v), unit="s", tz="UTC").tz_convert("Asia/Seoul").strftime("%Y-%m-%d %H:%M"),
                       "Size (kB)": round(os.path.getsize(v) / 1024, 1)} for k, v in FILES.items()]).set_index("Name"))

rd = lambda k: pd.read_csv(FILES[k], dtype={"kma_id": str})
EVM = pd.read_csv(EVENT_ID_MAP, dtype={"kma_id": str}).set_index("kma_id")
EVM["n"] = EVM.rtdd_id.astype(int)
SBM = pd.read_csv(FILES["summary_by_model"])
BYEV, BYDIST, BYSENS, BYMAG = (pd.read_csv(FILES[k]) for k in ("by_event", "by_distance", "by_sensor", "by_magnitude"))
BYEV["kma_id"] = BYEV["value"].str.slice(0, 14)
BYEV["ml_in_table"] = BYEV["value"].str.extract(r"ML([0-9.]+)")[0].astype(float)
RVD = rd("reference_vs_dl")
DLP = rd("dl_picks_all")
MISS = rd("missed_reference_diagnosis")
UNM = rd("unmatched_in_window")
OUTW = pd.read_csv(FILES["outside_window"])
SHRS = rd("station_hours")
COST = pd.read_csv(FILES["cost"]).set_index("variant")
COSTRUN = rd("cost_per_run")
FVR = rd("fast_vs_reliable")
FVRL = rd("fast_vs_reliable_latency")
SUMJ = json.load(open(FILES["summary_json"]))
BEST = json.load(open(FILES["best_model"]))
BEST_MODEL = BEST["best_model"]
SBP = rd("seisbench_pairs")
SBS = json.load(open(FILES["seisbench_summary"]))
SBR = rd("seisbench_vs_reference")
SBRUN = {"4 threads": json.load(open(FILES["seisbench_run_4_threads"])), "1 thread": json.load(open(FILES["seisbench_run_1_thread"]))}
WCHK = json.load(open(FILES["seisbench_weights_check"]))
SBSET = {m: json.load(open(f"{SB_DIR}/{m}_settings.json")) for m in SB_MODELS}
POS = pd.read_csv(FILES["reloc_positions"])
CMP = pd.read_csv(FILES["reloc_compare_pairs"])
CSH = pd.read_csv(FILES["reloc_centroid_shift"]).set_index("solution")
RSUM = json.load(open(FILES["reloc_summary"]))
REF = rd("reference_picks")
DTCC = pd.read_csv(HYPODD_DTCC, dtype={"kma_id": str})
SETS = {v: json.load(open(f"{SETTINGS_DIR}/scautopick_{v}.settings.json")) for v in VARIANTS}
for df in (RVD, DLP, MISS, FVR):
    for c in ("matched", "in_window", "ref_outlier", "reliable_matched_ref", "fast_matched_ref"):
        if c in df.columns:
            df[c] = df[c].astype(bool)
RVD["ts"] = ts_utc(RVD["time"])
DLP["ts"] = ts_utc(DLP["time"])
ALL = SBM[SBM.group == "all"].set_index(["variant", "phase"])
N_REF = {ph: int(ALL.loc[(VARIANTS[0], ph), "n_ref"]) for ph in ("P", "S")}
print(f"{len(EVM)} events (ML {EVM.kma_ml.min():.1f}-{EVM.kma_ml.max():.1f}); {len(REF)} PhaseNet+ reference picks "
      f"({(REF.phase == 'P').sum()} P, {(REF.phase == 'S').sum()} S); {DLP.variant.nunique()} picker runs; best model by "
      f"step 09's fixed rule: {BEST_MODEL}")
assert set(DLP.variant) == set(VARIANTS), "the variants in dl_picks_all.csv differ from VARIANTS"
assert len(REF) == N_REF["P"] + N_REF["S"], "summary_by_model.csv counts a different number of reference picks"

# scautopick logs: [error] and [warning] lines of every run (start-up probes included)
LOGS = sorted(glob.glob(f"{PICK_DIR}/*/*/scautopick.log"))
n_err = n_warn = 0
warn_kinds = {}
for f in LOGS:
    for line in open(f, errors="replace"):
        if "[error]" in line:
            n_err += 1
        elif "[warning]" in line:
            n_warn += 1
            k = re.sub(r" on .*", "", line.split("[warning]", 1)[1].strip())[:40]
            warn_kinds[k] = warn_kinds.get(k, 0) + 1
LOGSTAT = dict(n_logs=len(LOGS), n_error=n_err, n_warning=n_warn, warning_kinds=warn_kinds)
print(f"scautopick logs: {len(LOGS)} ({len(VARIANTS)} variants x {len(EVM)} events + start-up probes); "
      f"[error] lines: {n_err}; [warning] lines: {n_warn} {warn_kinds}")
""")

md(r"""
### 1.2 Consistency checks

Each summary number used in the figures is recomputed here from the per-pick files (the pick tables, the pair tables
and the relocated positions). The differences must be rounding only (the CSV files carry 4 decimals). A failed check
is listed in the summary at the end.
""")

code(r"""
# 1.2 recompute the summary numbers from the per-pick files
CHK = []


def chk(name, file_value, recomputed, tol):
    a = np.atleast_1d(np.asarray(file_value, float))
    b = np.atleast_1d(np.asarray(recomputed, float))
    d = float(np.nanmax(np.abs(a - b))) if len(a) else 0.0
    CHK.append({"Check": name, "Values compared": len(a), "Largest difference": d, "Tolerance": tol, "OK": bool(d <= tol)})


# recall, precision and dt statistics (summary_by_model.csv) from reference_vs_dl.csv and dl_picks_all.csv
rows = []
for v in VARIANTS:
    for ph in ("P", "S"):
        r = RVD[(RVD.variant == v) & (RVD.phase == ph)]
        d = DLP[(DLP.variant == v) & (DLP.phase == ph) & DLP.in_window]
        dts = r[r.matched].dt_s.to_numpy()
        rows.append(dict(variant=v, phase=ph, n_ref=len(r), n_matched=int(r.matched.sum()), n_dl_in_window=len(d),
                         n_dl_matched=int(d.matched.sum()), median_abs_dt_s=float(np.median(np.abs(dts))),
                         p95_abs_dt_s=float(np.percentile(np.abs(dts), 95)), mean_dt_s=float(dts.mean()),
                         mad_dt_s=h.mad(dts), n_ref_not_outlier=int((~r.ref_outlier).sum()),
                         n_matched_not_outlier=int((r.matched & ~r.ref_outlier).sum())))
RC = pd.DataFrame(rows).set_index(["variant", "phase"])
for c in ("n_ref", "n_matched", "n_dl_in_window", "n_dl_matched", "n_ref_not_outlier"):
    chk(f"summary_by_model.csv {c} = per-pick count", ALL.loc[RC.index, c], RC[c], 0)
for c in ("median_abs_dt_s", "p95_abs_dt_s", "mean_dt_s", "mad_dt_s"):
    chk(f"summary_by_model.csv {c} = from reference_vs_dl.csv dt_s", ALL.loc[RC.index, c], RC[c], 2e-4)
chk("summary_by_model.csv recall = n_matched / n_ref", ALL.recall, ALL.n_matched / ALL.n_ref, 6e-5)
chk("summary_by_model.csv precision = n_dl_matched / n_dl_in_window", ALL.precision, ALL.n_dl_matched / ALL.n_dl_in_window, 6e-5)
chk("summary_by_model.csv F1 = 2RP / (R + P)", ALL.f1, 2 * ALL.recall * ALL.precision / (ALL.recall + ALL.precision), 2e-4)
SJ = pd.DataFrame(SUMJ["summary_by_model"]).set_index(["variant", "phase"])
chk("summary.json recall/precision/F1 = summary_by_model.csv", SJ.loc[ALL.index, ["recall", "precision", "f1"]].to_numpy(),
    ALL[["recall", "precision", "f1"]].to_numpy(), 6e-5)
# per-event, distance, sensor and magnitude tables: matched counts from reference_vs_dl.csv
for name, tab, key in (("by_event.csv", BYEV, "kma_id"), ("by_distance.csv", BYDIST, "dist_bin"),
                       ("by_sensor.csv", BYSENS, "sensor"), ("by_magnitude.csv", BYMAG, "mag_class")):
    t = tab[tab.phase != "P+S"].copy()
    keyv = t["kma_id"] if key == "kma_id" else t["value"]
    re_ = RVD.groupby(["variant", "phase", key]).matched.agg(["sum", "size"])
    idx = list(zip(t.variant, t.phase, keyv))
    chk(f"{name} matched / reference counts = reference_vs_dl.csv", np.c_[t.n_matched, t.n_ref], re_.loc[idx].to_numpy(), 0)
chk("by_event.csv magnitudes = event_id_map.csv", BYEV.drop_duplicates("kma_id").set_index("kma_id").ml_in_table.loc[EVM.index], EVM.kma_ml, 1e-9)
# missed reference picks: every unmatched reference pick has a diagnosis; counts = summary.json
mc = MISS.groupby(["variant", "phase", "why_missed"]).size()
js = pd.Series({(k.split("|")[0], k.split("|")[1], c): n for k, d_ in SUMJ["missed_reference_counts"].items() for c, n in d_.items() if n > 0})
chk("missed_reference_diagnosis.csv cause counts = summary.json", js.sort_index(), mc.reindex(js.sort_index().index).fillna(0), 0)
chk("missed picks per variant and phase = n_ref - n_matched", MISS.groupby(["variant", "phase"]).size().loc[RC.index],
    RC.n_ref - RC.n_matched, 0)
uc = UNM.groupby(["variant", "phase", "class"]).size()
ju = pd.Series({(k.split("|")[0], k.split("|")[1], c): n for k, d_ in SUMJ["unmatched_in_window_counts"].items() for c, n in d_.items() if n > 0})
chk("unmatched_in_window.csv class counts = summary.json", ju.sort_index(), uc.reindex(ju.sort_index().index).fillna(0), 0)
# picks outside the event windows and their rates
o = DLP[~DLP.in_window].groupby(["variant", "phase", "class"]).size()
ow = OUTW.set_index(["variant", "phase"])
for c, cls in (("n_other_catalog_event", "other_catalog_event"), ("n_coincident", "coincident"), ("n_isolated", "isolated")):
    chk(f"outside_window.csv {c} = dl_picks_all.csv", ow[c], [o.get((v, p, cls), 0) for v, p in ow.index], 0)
hrs = SHRS.groupby("variant").searchable_outside_windows_h.sum()
chk("outside_window.csv searchable station-hours = station_hours.csv", ow.station_hours_searchable, hrs.loc[ow.index.get_level_values(0)], 2e-3)
chk("false picks per station-hour = (coincident + isolated) / searchable hours", ow.false_per_station_hour_searchable,
    (ow.n_coincident + ow.n_isolated) / ow.station_hours_searchable, 2e-4)
# cost
cr = COSTRUN[COSTRUN.kma_id != "startup_probe"].groupby("variant")[["user_s", "sys_s"]].sum().sum(axis=1)
chk("cost.csv CPU s = sum of cost_per_run.csv (event runs, start-up probes excluded)", COST.cpu_s_total, cr.loc[COST.index], 0.011)
chk("cost.csv CPU s per station-hour = CPU s / station-hours", COST.cpu_s_per_station_hour, COST.cpu_s_total / COST.station_hours, 2e-4)
chk("cost.csv station-hours = station_hours.csv", COST.station_hours, SHRS.groupby("variant").span_h.sum().loc[COST.index], 2e-3)
# fast against reliable
FJ = SUMJ["fast_vs_reliable"]
fw = FVR[FVR.in_window]
nw_ = h.whole_samples(fw.dt_fast_minus_reliable_s, FS_HZ)
chk("fast_vs_reliable.csv dt_samples = round(dt x 100)", FVR.dt_samples, h.whole_samples(FVR.dt_fast_minus_reliable_s, FS_HZ), 0)
chk("fast vs reliable in-window fractions (0, 2, 5 samples) = summary.json",
    [FJ["in_window_identical_fraction"], FJ["in_window_within_2_samples_fraction"], FJ["in_window_within_5_samples_fraction"]],
    [h.frac_within(nw_, 0), h.frac_within(nw_, 2), h.frac_within(nw_, 5)], 1e-9)
lat = FVRL[FVRL.in_window].groupby("variant").pick_available_after_onset_s.median()
chk("pick latency medians (fast, reliable) = summary.json",
    [FJ[f"{FAST}_pick_available_after_onset_s_median_in_window"], FJ[f"{RELIABLE}_pick_available_after_onset_s_median_in_window"]],
    [lat[FAST], lat[RELIABLE]], 1e-3)
# SeisBench pairs and 'found by' counts
for m in SB_MODELS:
    for ph in ("P", "S"):
        q = SBP[(SBP.model == m) & (SBP.phase == ph)]
        a = SBS["models"][m][ph]["all"]
        n = h.whole_samples(q.dt_plugin_minus_seisbench_s, FS_HZ)
        chk(f"SeisBench {m} {ph}: pairs, fractions (0/2/5 samples), mean dt = summary",
            [a["n_pairs"], a["frac_identical_0_samples"], a["frac_within_2_samples"], a["frac_within_5_samples"], a["mean_dt_s"]],
            [len(q), h.frac_within(n, 0), h.frac_within(n, 2), h.frac_within(n, 5), q.dt_plugin_minus_seisbench_s.mean()], 6e-5)
SBJ = SBR.merge(RVD[["variant", "kma_id", "station", "phase", "matched"]].rename(columns={"variant": "model"}),
                on=["model", "kma_id", "station", "phase"], how="left")
SBJ["sb_matched"] = SBJ.sb_matched.astype(bool)
for m in SB_MODELS:
    for ph in ("P", "S"):
        q = SBJ[(SBJ.model == m) & (SBJ.phase == ph)]
        s_ = SBS["models"][m][ph]
        chk(f"SeisBench {m} {ph}: found by both / only SeisBench / only plugin / neither = summary",
            [s_["reference_found_by_both"], s_["reference_found_only_by_seisbench"], s_["reference_found_only_by_plugin"], s_["reference_found_by_neither"]],
            [(q.sb_matched & q.matched).sum(), (q.sb_matched & ~q.matched).sum(), (~q.sb_matched & q.matched).sum(), (~q.sb_matched & ~q.matched).sum()], 0)
# relocation: metric (a) and the centroid shifts recomputed from positions.csv
PE = {s: g.sort_values("rtdd_id")[["east_m", "north_m", "up_m"]].to_numpy() for s, g in POS.groupby("solution")}
dd_ = []
for r in CMP.itertuples():
    if r.solution in PE and r.reference in PE:
        rms3, comp = h.enu_rms(PE[r.solution], PE[r.reference])
        dd_.append([r.rms_3d_m - rms3, r.rms_east_m - comp[0], r.rms_north_m - comp[1], r.rms_up_m - comp[2]])
chk("reloc compare_pairs.csv RMS (3-D, E, N, U) = from positions.csv (both stored to 0.01 m)", np.ravel(dd_), np.zeros(np.size(dd_)), 0.01)
c0 = PE["all_at_centroid"].mean(axis=0)
chk("reloc centroid_shift_from_start.csv = centroid - start point (positions.csv)",
    CSH[["shift_east_m", "shift_north_m", "shift_up_m"]].to_numpy(),
    np.array([PE[s].mean(axis=0) - c0 for s in CSH.index]), 0.15)
dtcc_pos = DTCC.sort_values("rtdd_id")[["east_m", "north_m", "up_m"]].to_numpy()
chk("reloc positions.csv HypoDD dt.cc = hypodd_dtcc.csv (stored to 0.1 m)", PE["hypodd_dtcc"], dtcc_pos, 0.1)

CHKT = pd.DataFrame(CHK)
with pd.option_context("display.max_colwidth", 120):
    display(CHKT.set_index("Check"))
FAILED = CHKT[~CHKT.OK]
print(f"{int(CHKT.OK.sum())} of {len(CHKT)} checks passed" + ("" if FAILED.empty else f"; FAILED: {list(FAILED.Check)}"))
""")

md(r"""
### 1.3 Settings of the picker runs and of the comparison

The first table is read from step 09's settings files (`settings/scautopick_<variant>.settings.json`, which hold the
cfg values, scautopick's own settings dump and the plugin defaults read from its source code). The second table holds
the definitions that the comparison used (`analysis/summary.json`). Only the four models and the fast P settings
were varied; the detector, `minConfidence` and the dead time stay at the README and plugin values.
""")

code(r"""
# 1.3 settings of every run, and the comparison definitions
rows = []
for v in VARIANTS:
    s = SETS[v]
    pr, sr, cf = s["plugin_resolved"]["picker.DL3C"], s["plugin_resolved"]["spicker.SDL3C"], s["cfg_file_values"]
    rows.append({"Variant": v, "ONNX model": os.path.basename(s["model_file"]),
                 "Model window (s)": pr["resolved"]["window_duration_s"],
                 "Model normalization": s["model_metadata"].get("seiscomp.picker.normalization", ""),
                 "P minConfidence": pr["minConfidence"]["value"], "P strategy": pr["strategy"]["value"],
                 "P windows end after the trigger (s)": ", ".join(f"{x:g}" for x in pr["resolved"]["attempt_window_ends_after_reference_s"]),
                 "S minConfidence": sr["minConfidence"]["value"], "S strategy": sr["strategy"]["value"],
                 "S windows end after the P pick (s)": ", ".join(f"{x:g}" for x in sr["resolved"]["attempt_window_ends_after_reference_s"]),
                 "S-veto of P peaks": pr["S-veto (internal)"]["value"],
                 "Detector filter": cf["filter"], "Trigger on / off": f"{cf['thresholds.triggerOn']} / {cf['thresholds.triggerOff']}",
                 "Dead time (s)": cf["thresholds.deadTime"], "initTime (s)": cf["initTime"]})
SETT = pd.DataFrame(rows).set_index("Variant")
with pd.option_context("display.max_colwidth", 60):
    display(SETT.T)
P_MINCONF = {v: float(SETT.loc[v, "P minConfidence"]) for v in VARIANTS}
S_MINCONF = {v: float(SETT.loc[v, "S minConfidence"]) for v in VARIANTS}
bound = SETS[VARIANTS[0]]["bound_stations"]
print(f"bound stations: {bound['n']} ({', '.join(f'{n} {k}' for k, n in bound['per_sensor'].items())}); "
      f"station-hours of data (bound vertical channels): {COST.station_hours.iloc[0]:.1f}")
DEFS = SUMJ["definitions"]
COINC = str(DEFS["coincidence"]).replace(">=", "≥").replace("+-", "±")   # for figure text
display(pd.DataFrame({"Value": {k: str(v) for k, v in DEFS.items()}}).rename_axis("Definition (analysis/summary.json)"))
""")

# =====================================================================================================
md(r"""
## 2. Figure 1: how many of the PhaseNet+ picks does each model find, and how many of its picks agree?

**What is shown.** Three panels: *recall* (the share of the PhaseNet+ picks that the model also picked), *precision*
(the share of the model's picks inside the event windows that have a PhaseNet+ partner) and *F1* (both combined).
Each group of bars is one phase: P, S, and P and S pooled. The numbers above the bars are the counts behind each share
(found / PhaseNet+ picks for recall, agreeing / all DL picks for precision). In the precision panel a short black line
marks the "precision counting plausible picks": it also counts as correct the unmatched DL picks that lie within the
tolerance of the predicted arrival time where PhaseNet+ has no pick or only an outlier pick (an upper bound).

**How to read it.** A model can have a high precision just by picking little; recall shows what it misses. F1 is high
only when both are high. Step 09 chose its best model by a rule fixed before any result was seen: the highest pooled
P and S F1 among the four main models, with near-ties broken by the smaller 95th percentile of |dt|.
""")

code(r"""
# Figure 1: recall, precision and F1 per model and phase
PH3 = ["P", "S", "P+S"]
METRICS = [("recall", "Recall: PhaseNet+ picks found", "n_matched", "n_ref"),
           ("precision", "Precision: DL picks with a PhaseNet+ partner", "n_dl_matched", "n_dl_in_window"),
           ("f1", "F1: recall and precision combined", None, None)]
nv = len(VARIANTS)
w = 0.84 / nv
fig, axes = plt.subplots(1, len(METRICS), figsize=(13.0, 4.3), sharey=True, gridspec_kw=dict(wspace=0.07))
for k, (ax, (key, title, num, den)) in enumerate(zip(axes, METRICS)):
    for j, v in enumerate(VARIANTS):
        for i, ph in enumerate(PH3):
            r = ALL.loc[(v, ph)]
            x = i + (j - (nv - 1) / 2.0) * w
            ax.bar(x, r[key], width=w * 0.9, color=COL[v], edgecolor="0.2", lw=0.4, zorder=2)
            top = r[key]
            if key == "precision":
                ax.plot([x - 0.42 * w, x + 0.42 * w], [r.precision_counting_plausible] * 2, color="k", lw=1.4, zorder=3,
                        solid_capstyle="butt")
                top = max(top, r.precision_counting_plausible)
            lab = f"{int(r[num])}/{int(r[den])}" if num else f"{r[key]:.3f}"
            ax.text(x, top + 0.012, lab, rotation=90, ha="center", va="bottom", fontsize=6.2, zorder=4)
    ax.set_xticks(range(len(PH3)))
    ax.set_xticklabels(["P", "S", "P and S pooled"])
    ax.set_xlim(-0.55, len(PH3) - 0.45)
    ax.set_ylim(0, 1.2)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.grid(axis="y", color="0.9", lw=0.6, zorder=0)
    ax.set_title(title, loc="left")
    h.panel_letter(ax, "abc"[k])
axes[0].set_ylabel("Share (0 to 1)")
hs, ls = h.model_handles(VARIANTS, COL, MARK, LABEL)
hs = [Patch(facecolor=COL[v], edgecolor="0.2", lw=0.4) for v in VARIANTS] + [Line2D([], [], color="k", lw=1.4)]
ls = ls + ["Precision counting plausible unmatched picks (upper bound)"]
h.legend_above(fig, axes, hs, ls, ncol=3)
FIGS["1"] = h.save_fig(fig, FIG_DIR, "03_1_recall_precision_f1")
plt.show()
tab = ALL.loc[[(v, p) for v in VARIANTS for p in PH3], ["n_ref", "n_matched", "recall", "n_dl_in_window", "n_dl_matched", "precision",
                                                         "precision_counting_plausible", "f1", "recall_without_ref_outliers"]]
display(tab.round(3))
""")

code(r"""
# Figure 1: what it says (numbers from the files)
rk = pd.DataFrame(BEST["ranking"]).set_index("variant")
pooled = ALL.xs("P+S", level="phase")
b = ALL.loc[(BEST_MODEL, "P")], ALL.loc[(BEST_MODEL, "S")]
gain = (ALL.recall_without_ref_outliers - ALL.recall)
lines = [
    f"- **Best model by the fixed rule: {BEST_MODEL}**, pooled F1 {rk.loc[BEST_MODEL, 'f1']:.3f}; then "
    + ", ".join(f"{v} {rk.loc[v, 'f1']:.3f}" for v in rk.index[1:]) + f" (the fast variant: {pooled.loc[FAST, 'f1']:.3f}).",
    f"- {BEST_MODEL} finds {b[0].recall:.0%} of the PhaseNet+ P picks ({int(b[0].n_matched)}/{int(b[0].n_ref)}) and {b[1].recall:.0%} of the S "
    f"picks ({int(b[1].n_matched)}/{int(b[1].n_ref)}); {b[0].precision:.0%} of its P and {b[1].precision:.0%} of its S picks have a PhaseNet+ partner.",
    f"- The other models are more conservative: precision {pooled.precision.drop(BEST_MODEL).min():.2f}-{pooled.precision.drop(BEST_MODEL).max():.2f} "
    f"(pooled) but recall only {pooled.recall.drop(BEST_MODEL).min():.2f}-{pooled.recall.drop(BEST_MODEL).max():.2f}.",
    f"- Counting plausible unmatched picks as correct raises precision to {ALL.precision_counting_plausible.min():.2f}-"
    f"{ALL.precision_counting_plausible.max():.2f} for every model and phase: many 'disagreements' are probably arrivals PhaseNet+ did not pick.",
    f"- Leaving out the {SUMJ['n_reference']['outliers']} reference outlier picks (more than {DEFS['ref_outlier_s']} s from the model "
    f"travel time) raises recall by only {gain.min():.3f}-{gain.max():.3f}.",
]
display(Markdown("\n".join(lines)))
""")

# =====================================================================================================
md(r"""
## 3. Figure 2: how far are the DL pick times from the PhaseNet+ pick times?

**What is shown.** For every matched pair, dt = DL pick time − PhaseNet+ pick time. One panel per model (columns) and
phase (rows), histograms with bins of one sample ([[DT_BIN_S]] s), shown from −[[DT_XLIM_S]] to +[[DT_XLIM_S]] s (pairs
beyond that are counted in the panel). The black line is the median dt, the gray dashed lines are ± the 95th
percentile of |dt|. Each panel title gives the number of pairs, the median dt, the MAD and the p95 |dt|.

**Caveat: the sign cannot be assigned to either picker.** A positive dt means the DL pick is later than the PhaseNet+
pick. That can be a late DL pick or an early PhaseNet+ pick: both are automatic, and only an independent check (for
example the waveforms, Figure 4, or hand picks) can tell which one is off. A constant offset between two pickers
cancels in double-difference relocation as long as all events are picked by the same picker.
""")

code(r"""
# Figure 2: dt = DL - PhaseNet+ of the matched pairs, per model and phase
MP = RVD[RVD.matched]
edges = np.arange(-DT_XLIM_S - DT_BIN_S / 2.0, DT_XLIM_S + DT_BIN_S, DT_BIN_S)
PHS = ["P", "S"]
fig, axes = plt.subplots(len(PHS), nv, figsize=(2.45 * nv, 2.55 * len(PHS) + 0.4), sharex=True, sharey=True,
                         gridspec_kw=dict(hspace=0.62, wspace=0.08))
DTS = {}
for i, ph in enumerate(PHS):
    for j, v in enumerate(VARIANTS):
        ax = axes[i, j]
        d = MP[(MP.variant == v) & (MP.phase == ph)].dt_s.to_numpy()
        med, p95, md_ = np.median(d), np.percentile(np.abs(d), 95), h.mad(d)
        DTS[(v, ph)] = dict(n=len(d), median=med, p95=p95, mad=md_, mean=d.mean(), beyond=int((np.abs(d) > DT_XLIM_S).sum()))
        ax.hist(d[np.abs(d) <= DT_XLIM_S], bins=edges, color=COL[v], edgecolor="0.25", lw=0.3, zorder=2)
        ax.axvline(0.0, color="0.55", lw=0.7, zorder=1)
        ax.axvline(med, color="k", lw=1.3, zorder=3)
        for s in (-1, 1):
            ax.axvline(s * p95, color="0.35", lw=1.0, ls="--", zorder=3)
        ax.set_title(f"{SHORT[v]}, {ph}\nn {len(d)}, median {med:+.3f} s\nMAD {md_:.3f} s, p95 |dt| {p95:.3f} s",
                     loc="left", fontsize=7.6)
        if DTS[(v, ph)]["beyond"]:
            ax.text(0.98, 0.97, f"{DTS[(v, ph)]['beyond']} beyond ±{DT_XLIM_S:g} s", transform=ax.transAxes,
                    ha="right", va="top", fontsize=6.8, color="0.25", zorder=6,
                    bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="0.6", lw=0.5))
        ax.set_xlim(-DT_XLIM_S, DT_XLIM_S)
        if j == 0:
            ax.set_ylabel(f"{ph} pairs per {DT_BIN_S:g} s bin")
        if i == len(PHS) - 1:
            ax.set_xlabel("dt = DL − PhaseNet+ (s)")
        h.panel_letter(ax, "abcdefghij"[i * nv + j], fontsize=9)
hs = [Line2D([], [], color="k", lw=1.3), Line2D([], [], color="0.35", lw=1.0, ls="--"), Line2D([], [], color="0.55", lw=0.7)]
ls = ["Median dt", "± 95th percentile of |dt|", "Zero (same time)"]
h.legend_above(fig, axes, hs, ls, ncol=3)
FIGS["2"] = h.save_fig(fig, FIG_DIR, "03_2_pick_time_differences")
plt.show()
for (v, ph), s in DTS.items():
    assert abs(s["median"] - ALL.loc[(v, ph), "median_dt_s"]) < 2e-4 and abs(s["p95"] - ALL.loc[(v, ph), "p95_abs_dt_s"]) < 2e-4
""")

code(r"""
# Figure 2: what it says
D2 = pd.DataFrame(DTS).T.astype(float)
lines = [
    f"- **The typical size of the difference is a few samples:** median |dt| {ALL.loc[[(v, 'P') for v in VARIANTS], 'median_abs_dt_s'].min():.3f}-"
    f"{ALL.loc[[(v, 'P') for v in VARIANTS], 'median_abs_dt_s'].max():.3f} s for P and {ALL.loc[[(v, 'S') for v in VARIANTS], 'median_abs_dt_s'].min():.3f}-"
    f"{ALL.loc[[(v, 'S') for v in VARIANTS], 'median_abs_dt_s'].max():.3f} s for S; the widths (MAD) are {D2.mad.min():.3f}-{D2.mad.max():.3f} s.",
    f"- **Each model has its own offset.** {SHORT[BEST_MODEL]} picks later than PhaseNet+ (median {D2.loc[(BEST_MODEL, 'P'), 'median']:+.3f} s for P, "
    f"{D2.loc[(BEST_MODEL, 'S'), 'median']:+.3f} s for S); {SHORT[RELIABLE]} picks S earlier (median {D2.loc[(RELIABLE, 'S'), 'median']:+.3f} s, "
    f"mean {D2.loc[(RELIABLE, 'S'), 'mean']:+.3f} s), and its fast variant the same ({D2.loc[(FAST, 'S'), 'median']:+.3f} s).",
    f"- The largest p95 |dt| is {D2.p95.max():.3f} s ({SHORT[D2.p95.idxmax()[0]]}, {D2.p95.idxmax()[1]}); the smallest {D2.p95.min():.3f} s "
    f"({SHORT[D2.p95.idxmin()[0]]}, {D2.p95.idxmin()[1]}).",
    "- **Which picker is off cannot be read from these offsets** (see the caveat above). A constant offset cancels in double "
    "differences; what does not cancel is its scatter from event to event (Figure 9).",
]
display(Markdown("\n".join(lines)))
""")

# =====================================================================================================
md(r"""
## 4. Figure 3: where are picks lost? Event size, distance and sensor type

**What is shown.** Recall (the share of the PhaseNet+ picks found) for P (top row) and S (bottom row), split three
ways:

- left: per event, the events sorted by KMA magnitude (event number, magnitude and the number N of PhaseNet+ picks
  of that phase under each event); the dotted line separates the two magnitude classes of step 09
  (the class boundary is printed below the figure);
- middle: by epicentral distance (step 09's three bins);
- right: by sensor type: HH (broadband), HG (accelerometer) and EL (short-period).

Each model keeps its color and marker; the points of the five runs are spread sideways a little so that they do not
hide each other. Smaller events have weaker arrivals, so a picker that needs a clear signal loses them first.
""")

code(r"""
# Figure 3: recall per event (sorted by magnitude), per distance bin and per sensor type
EVO = EVM.reset_index().sort_values(["kma_ml", "n"]).set_index("kma_id")
DBINS = list(dict.fromkeys(RVD.sort_values("dist_km").dist_bin))
SENS = [s for s in ("HH", "HG", "EL") if s in set(RVD.sensor)]
ML_SPLIT = sorted(BYMAG.value.unique())           # step 09's two magnitude classes, e.g. 'ML<1.5' and 'ML>=1.5'
ML_CUT = float(re.search(r"[0-9.]+", ML_SPLIT[0]).group())
MLC = {c: ML + (" < " if "<" in c else " ≥ ") + f"{ML_CUT:g}" for c in ML_SPLIT}   # the classes written with the italic M_L
fig = plt.figure(figsize=(13.0, 7.2))
gs = fig.add_gridspec(len(PHS), 3, width_ratios=[2.6, 1.0, 1.0], wspace=0.12, hspace=0.55)
offs = np.linspace(-0.28, 0.28, nv)
axs = []
for i, ph in enumerate(PHS):
    a0 = fig.add_subplot(gs[i, 0])
    a1 = fig.add_subplot(gs[i, 1], sharey=a0)
    a2 = fig.add_subplot(gs[i, 2], sharey=a0)
    axs += [a0, a1, a2]
    for j, v in enumerate(VARIANTS):
        e = BYEV[(BYEV.variant == v) & (BYEV.phase == ph)].set_index("kma_id").loc[EVO.index]
        a0.plot(np.arange(len(EVO)) + offs[j], e.recall, ls="none", marker=MARK[v], color=COL[v], mec=COL[v], mfc="white",
                ms=5.5, mew=1.1, zorder=3)
        d = BYDIST[(BYDIST.variant == v) & (BYDIST.phase == ph)].set_index("value").loc[DBINS]
        a1.plot(np.arange(len(DBINS)) + offs[j], d.recall, ls="none", marker=MARK[v], color=COL[v], mec=COL[v], mfc="white",
                ms=5.5, mew=1.1, zorder=3)
        s = BYSENS[(BYSENS.variant == v) & (BYSENS.phase == ph)].set_index("value").loc[SENS]
        a2.plot(np.arange(len(SENS)) + offs[j], s.recall, ls="none", marker=MARK[v], color=COL[v], mec=COL[v], mfc="white",
                ms=5.5, mew=1.1, zorder=3)
    nref_ev = BYEV[(BYEV.variant == VARIANTS[0]) & (BYEV.phase == ph)].set_index("kma_id").loc[EVO.index].n_ref
    a0.set_xticks(np.arange(len(EVO)))
    a0.set_xticklabels([f"{int(e.n)}\n{ML} {e.kma_ml:.1f}\nN {int(n)}" for (_, e), n in zip(EVO.iterrows(), nref_ev)], fontsize=7.3)
    split = int((EVO.kma_ml < ML_CUT).sum()) - 0.5
    a0.axvline(split, color="0.4", lw=0.9, ls=":", zorder=1)
    a0.text(split - 0.1, 0.03, MLC[ML_SPLIT[0]], ha="right", va="bottom", fontsize=7.5, color="0.3")
    a0.text(split + 0.1, 0.03, MLC[ML_SPLIT[1]], ha="left", va="bottom", fontsize=7.5, color="0.3")
    a0.set_xlim(-0.6, len(EVO) - 0.4)
    nref_d = BYDIST[(BYDIST.variant == VARIANTS[0]) & (BYDIST.phase == ph)].set_index("value").loc[DBINS].n_ref
    a1.set_xticks(np.arange(len(DBINS)))
    a1.set_xticklabels([f"{b_}\nN {int(n)}" for b_, n in zip(DBINS, nref_d)], fontsize=7.5)
    a1.set_xlim(-0.6, len(DBINS) - 0.4)
    nref_s = BYSENS[(BYSENS.variant == VARIANTS[0]) & (BYSENS.phase == ph)].set_index("value").loc[SENS].n_ref
    a2.set_xticks(np.arange(len(SENS)))
    a2.set_xticklabels([f"{s_}\nN {int(n)}" for s_, n in zip(SENS, nref_s)], fontsize=7.5)
    a2.set_xlim(-0.6, len(SENS) - 0.4)
    for a in (a1, a2):
        a.tick_params(labelleft=False)
    for a in (a0, a1, a2):
        a.set_ylim(0, 1.04)
        a.grid(axis="y", color="0.9", lw=0.6, zorder=0)
    a0.set_ylabel(f"Recall of {ph} picks")
    a0.set_title(f"{ph} picks per event (event number, magnitude, N = PhaseNet+ {ph} picks)", loc="left")
    a1.set_title(f"{ph}: by epicentral distance", loc="left")
    a2.set_title(f"{ph}: by sensor type", loc="left")
for k, a in enumerate(axs):
    h.panel_letter(a, "abcdef"[k], fontsize=9)
hs, ls = h.model_handles(VARIANTS, COL, MARK, LABEL)
h.legend_above(fig, axs, hs, ls, ncol=3)
FIGS["3"] = h.save_fig(fig, FIG_DIR, "03_3_recall_by_magnitude_distance_sensor")
plt.show()
""")

code(r"""
# Figure 3: what it says (magnitude classes, distance, sensor and the distance confound of the sensor types)
mg = BYMAG.set_index(["variant", "phase", "value"])
lo, hi = ML_SPLIT[0], ML_SPLIT[1]
rP_lo = [mg.loc[(v, "P", lo), "recall"] for v in VARIANTS]
rP_hi = [mg.loc[(v, "P", hi), "recall"] for v in VARIANTS]
rS_lo = [mg.loc[(v, "S", lo), "recall"] for v in VARIANTS]
rS_hi = [mg.loc[(v, "S", hi), "recall"] for v in VARIANTS]
dist_ref = RVD[RVD.variant == VARIANTS[0]]
sens_dist = dist_ref.groupby("sensor").dist_km.agg(median="median", q25=lambda x: x.quantile(0.25))
far = RVD[(RVD.variant == BEST_MODEL) & (RVD.dist_bin == DBINS[-1])].groupby("sensor").matched.mean()
nev = EVM.groupby(EVM.kma_ml < ML_CUT).size()
mt = mg.xs("P+S", level="phase").recall.unstack()
display(mt.loc[VARIANTS].round(3).rename_axis("Pooled P and S recall"))
lines = [
    f"- **Large events are nearly complete with every model; small ones are not.** For {MLC[hi]} ({nev[False]} events) P recall is "
    f"{min(rP_hi):.2f}-{max(rP_hi):.2f} and S recall {min(rS_hi):.2f}-{max(rS_hi):.2f}; for {MLC[lo]} ({nev[True]} events) P recall is "
    f"{min(rP_lo):.2f}-{max(rP_lo):.2f} and S recall {min(rS_lo):.2f}-{max(rS_lo):.2f}.",
    f"- The best model loses the least: {SHORT[BEST_MODEL]} keeps {mg.loc[(BEST_MODEL, 'P', lo), 'recall']:.2f} (P) and "
    f"{mg.loc[(BEST_MODEL, 'S', lo), 'recall']:.2f} (S) for {MLC[lo]}; {SHORT['phasenet_stead']} only {mg.loc[('phasenet_stead', 'P', lo), 'recall']:.2f} "
    f"and {mg.loc[('phasenet_stead', 'S', lo), 'recall']:.2f}.",
    f"- **Distance.** P recall falls from {BYDIST[(BYDIST.phase == 'P') & (BYDIST.value == DBINS[0])].recall.min():.2f}-"
    f"{BYDIST[(BYDIST.phase == 'P') & (BYDIST.value == DBINS[0])].recall.max():.2f} ({DBINS[0]}) to "
    f"{BYDIST[(BYDIST.phase == 'P') & (BYDIST.value == DBINS[-1])].recall.min():.2f}-{BYDIST[(BYDIST.phase == 'P') & (BYDIST.value == DBINS[-1])].recall.max():.2f} "
    f"({DBINS[-1]}); S from {BYDIST[(BYDIST.phase == 'S') & (BYDIST.value == DBINS[0])].recall.min():.2f}-"
    f"{BYDIST[(BYDIST.phase == 'S') & (BYDIST.value == DBINS[0])].recall.max():.2f} to {BYDIST[(BYDIST.phase == 'S') & (BYDIST.value == DBINS[-1])].recall.min():.2f}-"
    f"{BYDIST[(BYDIST.phase == 'S') & (BYDIST.value == DBINS[-1])].recall.max():.2f}.",
    f"- **Sensor type is mostly distance.** The PhaseNet+ picks at HH stations lie farther away (median {sens_dist.loc['HH', 'median']:.0f} km, "
    f"a quarter below {sens_dist.loc['HH', 'q25']:.0f} km) than those at HG stations (median {sens_dist.loc['HG', 'median']:.0f} km, a quarter "
    f"below {sens_dist.loc['HG', 'q25']:.0f} km). In the last distance bin ({DBINS[-1]}), {SHORT[BEST_MODEL]} finds "
    f"{far.get('HH', np.nan):.2f} of the HH and {far.get('HG', np.nan):.2f} of the HG picks (P and S together).",
]
display(Markdown("\n".join(lines)))
""")

# =====================================================================================================
md(r"""
## 5. Figure 4: what the picks look like on the waveforms

**What is shown.** Two events: the largest one ($\mathit{M}_{\mathrm{L}}$ ≥ 2) and, of the two smallest events, the one
where the best model found the smallest share of the PhaseNet+ picks (both chosen by these rules, not by eye). For each
event four stations, also chosen by a rule: the nearest and the farthest station of each sensor type
([[WF_SENSORS:0]] and [[WF_SENSORS:1]]) among the stations where PhaseNet+ has both a P and an S pick that is not an
outlier. One row per station:

- left: all three components (vertical Z, north N, east E) from [[WF_OVERVIEW_S:0]] s before the PhaseNet+ P pick to
  +[[WF_OVERVIEW_S:1]] s after the PhaseNet+ S pick, aligned on the station's own PhaseNet+ P pick; the two gray bands are
  the stretches shown enlarged in the other two columns;
- middle: the vertical component, aligned on the station's own PhaseNet+ P pick ([[WF_ZOOM_S:0]] to +[[WF_ZOOM_S:1]] s);
- right: the two horizontal components, aligned on the station's own PhaseNet+ S pick (same span).

Every trace is band-passed [[BAND_HZ:0]]-[[BAND_HZ:1]] Hz with a causal (one-pass, [[FILTER_CORNERS]]-corner Butterworth)
filter, which can only delay an onset by a few hundredths of a second and never shows energy before it; each trace is
scaled to its own largest value in its panel. PhaseNet+ picks are vertical blue lines (P solid, S dashed; the other
phase is drawn too when it falls inside a panel). Above the traces, one row per DL run: a filled marker is that run's
pick of the panel's phase, an open marker with a letter just below the row is its pick of the other phase inside the
panel (for example a P pick placed on the S wave), and "no pick" means the run made no pick of that phase at that station inside the event
window. A pick that exists but lies outside the panel is written out with its time.

As a check on the input, every plotted SAC trace is compared sample by sample with the miniSEED playback file that
scautopick read.
""")

code(r"""
# Figure 4: choose the two events and the stations (rules, not by eye)
EV_BIG = EVM.kma_ml.idxmax()
assert EVM.loc[EV_BIG, "kma_ml"] >= 2.0, "no event with ML >= 2"
smallest = EVM[EVM.kma_ml == EVM.kma_ml.min()].index
pooled_ev = BYEV[(BYEV.variant == BEST_MODEL) & (BYEV.phase == "P+S")].set_index("kma_id").recall
EV_SMALL = pooled_ev.loc[smallest].idxmin()
print(f"largest event: {EV_BIG} (event {EVM.loc[EV_BIG, 'n']}, ML {EVM.loc[EV_BIG, 'kma_ml']:.1f}); smallest events: "
      + ", ".join(f"{k} (event {EVM.loc[k, 'n']}, {SHORT[BEST_MODEL]} pooled recall {pooled_ev[k]:.2f})" for k in smallest)
      + f" -> {EV_SMALL}")


def wf_stations(ev):
    q = RVD[(RVD.variant == BEST_MODEL) & (RVD.kma_id == ev) & ~RVD.ref_outlier]
    both = q.groupby("station").phase.nunique()
    st_ = q[q.station.isin(both[both == 2].index)].drop_duplicates("station")[["station", "sensor", "dist_km"]]
    out = []
    for sen in WF_SENSORS:
        s = st_[st_.sensor == sen].sort_values("dist_km")
        out += [s.iloc[0], s.iloc[-1]]
    return pd.DataFrame(out).drop_duplicates("station").sort_values("dist_km").reset_index(drop=True)


WF_SEL = {ev: wf_stations(ev) for ev in (EV_BIG, EV_SMALL)}
for ev, s in WF_SEL.items():
    print(f"event {EVM.loc[ev, 'n']}: " + ", ".join(f"{r.station} ({r.sensor}, {r.dist_km:.1f} km)" for r in s.itertuples()))
PLAYBACK = {}


def playback_check(ev, sta, st):
    # the SAC samples must equal the miniSEED playback samples scautopick read (same channel, same times)
    if ev not in PLAYBACK:
        PLAYBACK[ev] = read(f"{PLAYBACK_DIR}/{ev}_sorted.mseed")
    worst = 0.0
    for tr in st:
        m = PLAYBACK[ev].select(station=sta, channel=tr.stats.channel).copy().merge()
        if not len(m):
            return np.nan
        t0, t1 = max(m[0].stats.starttime, tr.stats.starttime), min(m[0].stats.endtime, tr.stats.endtime)
        a, b_ = m[0].slice(t0, t1).data.astype(float), tr.slice(t0, t1).data.astype(float)
        k = min(len(a), len(b_))
        worst = max(worst, float(np.abs(a[:k] - b_[:k]).max()))
    return worst
""")

code(r"""
# Figure 4: helper that draws one event (rows = stations; columns = overview, P zoom, S zoom)
ROW_Y = {v: 1.75 + 0.62 * (nv - 1 - j) for j, v in enumerate(VARIANTS)}   # the run rows above the traces
Y_TOP = max(ROW_Y.values()) + 0.5
WF_STATUS = []


def dl_picks(ev, sta):
    return DLP[(DLP.kma_id == ev) & (DLP.station == sta) & DLP.in_window]


def draw_rows(ax, ev, sta, t_ref, phase, other_ref):
    x0, x1 = WF_ZOOM_S
    q = dl_picks(ev, sta)
    for v in VARIANTS:
        y = ROW_Y[v]
        ax.axhline(y, color="0.92", lw=0.6, zorder=0)
        mine = q[(q.variant == v) & (q.phase == phase)]
        oth = q[(q.variant == v) & (q.phase != phase)]
        if mine.empty:
            ax.text(x0 + 0.25 * (x1 - x0), y, "no pick", ha="center", va="center", fontsize=6.8, color="0.35", zorder=4)
            status = "no pick"
        else:
            status = []
            for r in mine.itertuples():
                x = r.ts - t_ref
                if x0 <= x <= x1:
                    ax.plot([x], [y], ls="none", marker=MARK[v], color=COL[v], mec="0.15", mew=0.5, ms=6.2, zorder=5)
                else:
                    ax.text(x1 - 0.02 if x > x1 else x0 + 0.02, y, f"{phase} pick at {x:+.2f} s",
                            ha="right" if x > x1 else "left", va="center", fontsize=6.5, color="0.2", zorder=4)
                status.append(f"{x:+.3f}" + ("" if r.matched else " (unmatched)"))
            status = ", ".join(status)
        for r in oth.itertuples():
            x = r.ts - t_ref
            if x0 <= x <= x1:
                ax.plot([x], [y - 0.24], ls="none", marker=MARK[v], color=COL[v], mec=COL[v], mfc="white", mew=1.0, ms=5.2, zorder=5)
                ax.text(x + 0.06, y - 0.24, r.phase, fontsize=7, color="0.1", ha="left", va="center", zorder=6,
                        bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none"))
        WF_STATUS.append(dict(kma_id=ev, station=sta, variant=v, phase=phase, dl_minus_phasenet_plus_s=status))


def draw_event(ev, fig_name, letter_offset=0):
    sel = WF_SEL[ev]
    e = EVM.loc[ev]
    rp = RVD[(RVD.variant == BEST_MODEL) & (RVD.kma_id == ev)].set_index(["station", "phase"]).ts
    nrow = len(sel)
    fig = plt.figure(figsize=(13.4, 2.55 * nrow + 0.3))
    gs = fig.add_gridspec(nrow, 4, width_ratios=[1.55, 0.36, 1.0, 1.0], wspace=0.13, hspace=0.55)   # column 1: room for the run labels
    axes = []
    for i, s in enumerate(sel.itertuples()):
        st = read(f"{WAVEFORMS}/{ev}/{ev}.KS.{s.station}.*.sac")
        dev = playback_check(ev, s.station, st)
        stf = h.bandpass(st, BAND_HZ[0], BAND_HZ[1], FILTER_CORNERS, TAPER_FRACTION, FILTER_ZEROPHASE)
        tP, tS = rp[(s.station, "P")], rp[(s.station, "S")]
        sp = tS - tP
        WF_STATUS.append(dict(kma_id=ev, station=s.station, variant="SAC vs playback", phase="ZNE",
                              dl_minus_phasenet_plus_s=f"largest sample difference {dev:g} counts"))
        # left: overview Z, N, E aligned on the P pick
        a0 = fig.add_subplot(gs[i, 0])
        w0, w1 = WF_OVERVIEW_S[0], sp + WF_OVERVIEW_S[1]
        for k, comp in enumerate(("Z", "N", "E")):
            tr = h.component(stf, comp)
            t, y = h.norm_window(tr.times("timestamp") - tP, tr.data, w0, w1)
            a0.plot(t, 2 - k + 0.45 * y, color="0.15", lw=0.45, zorder=2)
        a0.axvspan(*WF_ZOOM_S, color="0.9", lw=0, zorder=0)
        a0.axvspan(sp + WF_ZOOM_S[0], sp + WF_ZOOM_S[1], color="0.9", lw=0, zorder=0)
        a0.axvline(0.0, color=COL["phasenet_plus"], lw=1.1, zorder=3)
        a0.axvline(sp, color=COL["phasenet_plus"], lw=1.1, ls="--", zorder=3)
        a0.set_xlim(w0, w1)
        a0.set_ylim(-0.6, 2.6)
        a0.set_yticks([2, 1, 0])
        a0.set_yticklabels(["Z", "N", "E"])
        a0.set_title(f"{s.station} ({s.sensor}), {s.dist_km:.1f} km: S−P {sp:.2f} s", loc="left")
        a0.set_xlabel("Time after the PhaseNet+ P pick (s)")
        # middle: vertical on the P pick; right: horizontals on the S pick
        a1 = fig.add_subplot(gs[i, 2])
        a2 = fig.add_subplot(gs[i, 3])
        tr = h.component(stf, "Z")
        t, y = h.norm_window(tr.times("timestamp") - tP, tr.data, *WF_ZOOM_S)
        a1.plot(t, 0.85 * y, color="0.15", lw=0.6, zorder=2)
        for k, comp in enumerate(("N", "E")):
            tr = h.component(stf, comp)
            t, y = h.norm_window(tr.times("timestamp") - tS, tr.data, *WF_ZOOM_S)
            a2.plot(t, 0.5 - k + 0.45 * y, color="0.15", lw=0.6, zorder=2)
        for ax, t_ref, ph, other in ((a1, tP, "P", tS), (a2, tS, "S", tP)):
            ax.axvline(0.0, color=COL["phasenet_plus"], lw=1.1, ls="-" if ph == "P" else "--", zorder=3)
            xo = other - t_ref
            if WF_ZOOM_S[0] <= xo <= WF_ZOOM_S[1]:
                ax.axvline(xo, color=COL["phasenet_plus"], lw=1.1, ls="--" if ph == "P" else "-", zorder=3)
            draw_rows(ax, ev, s.station, t_ref, ph, other)
            ax.set_xlim(*WF_ZOOM_S)
            ax.set_ylim(-1.05, Y_TOP)
        a1.set_yticks([0.0] + [ROW_Y[v] for v in VARIANTS])
        a1.set_yticklabels(["Z"] + [SHORT[v] for v in VARIANTS], fontsize=6.8)
        a2.set_yticks([0.5, -0.5])
        a2.set_yticklabels(["N", "E"])
        a2.yaxis.tick_right()
        a1.set_title("Vertical, on the PhaseNet+ P pick", loc="left")
        a2.set_title("Horizontals, on the PhaseNet+ S pick", loc="left")
        a1.set_xlabel("Time after the PhaseNet+ P pick (s)")
        a2.set_xlabel("Time after the PhaseNet+ S pick (s)")
        axes += [a0, a1, a2]
    for k, a in enumerate(axes):
        h.panel_letter(a, chr(ord("a") + k), fontsize=9)
    hs = [Line2D([], [], color=COL["phasenet_plus"], lw=1.1), Line2D([], [], color=COL["phasenet_plus"], lw=1.1, ls="--"),
          Patch(color="0.9", lw=0)]
    ls = ["PhaseNet+ P pick", "PhaseNet+ S pick", "Stretch enlarged in the middle and right columns"]
    hs += [Line2D([], [], ls="none", marker=MARK[v], color=COL[v], mec="0.15", mew=0.5, ms=6.2) for v in VARIANTS]
    ls += [f"{LABEL[v]}: pick of the panel's phase" for v in VARIANTS]
    hs += [Line2D([], [], ls="none", marker="o", color="0.3", mfc="white", ms=6)]
    ls += ["Open marker with letter, just below a row: that run's pick of the other phase"]
    leg = h.legend_above(fig, axes, hs, ls, ncol=3, fontsize=7.3)
    h.text_above(fig, [leg] + axes, f"Event {int(e.n)}, {pd.Timestamp(e.kma_origin_utc).strftime('%Y-%m-%d %H:%M')} UTC, "
                 f"{ML} {e.kma_ml:.1f}: {BAND_HZ[0]:g}-{BAND_HZ[1]:g} Hz causal band-pass, each trace scaled to its own maximum "
                 f"in its panel", fontsize=9.5)
    out = h.save_fig(fig, FIG_DIR, fig_name)
    plt.show()
    return out
""")

code(r"""
# Figure 4a: the largest event
FIGS["4a"] = draw_event(EV_BIG, f"03_4a_waveforms_event{EVM.loc[EV_BIG, 'n']}_{EV_BIG}")
""")

code(r"""
# Figure 4b: the small event
FIGS["4b"] = draw_event(EV_SMALL, f"03_4b_waveforms_event{EVM.loc[EV_SMALL, 'n']}_{EV_SMALL}")
""")

code(r"""
# Figure 4: the picks shown, as a table (time after the PhaseNet+ pick in s; 'no pick' = none in the event window)
WFS = pd.DataFrame(WF_STATUS)
chk_rows = WFS[WFS.variant == "SAC vs playback"]
print("SAC copies against the playback miniSEED:", "; ".join(f"event {EVM.loc[r.kma_id, 'n']} {r.station}: {r.dl_minus_phasenet_plus_s}"
                                                     for r in chk_rows.itertuples()))
assert chk_rows.dl_minus_phasenet_plus_s.str.contains("difference 0 counts").all(), "a SAC copy differs from the playback data"
T4 = WFS[WFS.variant != "SAC vs playback"].pivot_table(index=["kma_id", "station", "phase"], columns="variant",
                                                         values="dl_minus_phasenet_plus_s", aggfunc="first")[VARIANTS]
T4.columns = [SHORT[v] for v in VARIANTS]
display(T4)
nopick = {ev: int((T4.loc[ev] == "no pick").sum().sum()) for ev in (EV_BIG, EV_SMALL)}
cells = {ev: int(T4.loc[ev].size) for ev in (EV_BIG, EV_SMALL)}
shown = DLP[DLP.in_window & DLP.matched & DLP.kma_id.isin([EV_BIG]) & DLP.station.isin(WF_SEL[EV_BIG].station)]
q4 = WFS[(WFS.kma_id == EV_SMALL) & (WFS.variant != "SAC vs playback")].pivot_table(index=["station", "variant"], columns="phase",
                                                                                        values="dl_minus_phasenet_plus_s", aggfunc="first")
noP = q4[q4["P"] == "no pick"]
conf4 = UNM[(UNM.kma_id == EV_SMALL) & UNM.station.isin(WF_SEL[EV_SMALL].station) & (UNM["class"] == "phase_confusion")]
display(Markdown(
    f"- Event {EVM.loc[EV_BIG, 'n']} ({ML} {EVM.loc[EV_BIG, 'kma_ml']:.1f}): {cells[EV_BIG] - nopick[EV_BIG]} of {cells[EV_BIG]} "
    f"station-phase-run combinations have a DL pick; all lie within {shown.ref_dt_s.abs().max():.2f} s of the PhaseNet+ picks, at near and "
    f"far stations alike.\n"
    f"- Event {EVM.loc[EV_SMALL, 'n']} ({ML} {EVM.loc[EV_SMALL, 'kma_ml']:.1f}): only {cells[EV_SMALL] - nopick[EV_SMALL]} of "
    f"{cells[EV_SMALL]} have a DL pick. Of the {len(noP)} station-run combinations without a P pick, {int((noP['S'] == 'no pick').sum())} "
    f"have no S pick either (Figure 5 explains why). {len(conf4)} 'P' pick(s) of these stations lie on the S wave "
    f"({', '.join(f'{r.station}, {SHORT[r.variant]}' for r in conf4.itertuples())}; open markers in the right column)."))
""")

# =====================================================================================================
md(r"""
## 6. Figure 5: why were PhaseNet+ picks missed?

**What is shown.** Step 09 read the plugin's debug log for every PhaseNet+ pick that a run missed and recorded why
(`missed_reference_diagnosis.csv`):

- **No detector trigger**: the STA/LTA detector never triggered near the onset, so no model window covered it.
- **Trigger in dead time (no picker)**: a trigger came, but within the dead time after an earlier trigger, so no
  picker was started.
- **Model value below minConfidence**: a model window covered the onset, but the network's highest P (or S) value in
  it stayed below the plugin's `minConfidence`. This is the model's own decision.
- **P peak vetoed as S**: a P peak above the threshold was rejected because the S output was nearly as high there
  (the plugin's internal S check, listed in section 1.3).
- **Picker picked another time**: a window produced a pick, but farther from the PhaseNet+ pick than the tolerance.
- **No P pick, so no S picker ran**: the plugin starts an S picker only after a P pick at the same station; without
  a P pick no S pick is possible.
- Rare S cases: the station's only P pick was the S arrival itself; no S window covered the onset.

Panels (a) and (b) count the causes for the missed P and S picks of each run. Panel (c) shows, for the P picks lost
"below minConfidence", the highest P value the model reached in the windows that covered the onset, with the plugin's
P threshold. Panel (d) follows the S picks lost for want of a P pick back to their station's P: why was there no DL P
pick there (including stations where PhaseNet+ itself has no P pick)?
""")

code(r"""
# Figure 5: causes of the missed reference picks
CAUSE = {  # label, face color, hatch (grays and hatches: the model colors stay reserved for the models)
    "model_below_minConfidence": ("Model value below minConfidence", "0.25", None),
    "no_P_pick_so_no_S_picker": ("No P pick, so no S picker ran", "0.62", None),
    "no_detector_trigger": ("No detector trigger", "white", "////"),
    "trigger_not_turned_into_picker": ("Trigger in dead time (no picker)", "0.86", None),
    "window_picked_other_time": ("Picker picked another time", "white", "...."),
    "peak_vetoed_as_S": ("P peak vetoed as S", "white", "xxxx"),
    "only_P_pick_is_on_this_S_wave": ("Only P pick was on this S wave", "white", "\\\\\\\\"),
    "no_S_window_covering": ("No S window covered the onset", "white", "++"),
    "no_phasenet_plus_P": ("No PhaseNet+ P pick at the station either", "white", "----"),
}
order_P = ["model_below_minConfidence", "no_detector_trigger", "trigger_not_turned_into_picker", "peak_vetoed_as_S", "window_picked_other_time"]
order_S = ["no_P_pick_so_no_S_picker", "model_below_minConfidence", "window_picked_other_time", "only_P_pick_is_on_this_S_wave", "no_S_window_covering"]
cnt = MISS.groupby(["variant", "phase", "why_missed"]).size()
assert set(MISS[MISS.phase == "P"].why_missed) <= set(order_P) and set(MISS[MISS.phase == "S"].why_missed) <= set(order_S)
# (d): S lost for want of a P pick -> why there was no DL P pick at that station
sP = MISS[(MISS.phase == "S") & (MISS.why_missed == "no_P_pick_so_no_S_picker")]
pref = RVD[RVD.phase == "P"][["variant", "kma_id", "station", "matched"]]
pwhy = MISS[MISS.phase == "P"][["variant", "kma_id", "station", "why_missed"]].rename(columns={"why_missed": "p_why"})
SCH = sP.merge(pref, on=["variant", "kma_id", "station"], how="left").merge(pwhy, on=["variant", "kma_id", "station"], how="left")
assert not (SCH.matched == True).any(), "an S lost for want of a P pick, although the P was matched"
SCH["p_state"] = np.where(SCH.matched.isna(), "no_phasenet_plus_P", SCH.p_why)
order_D = ["model_below_minConfidence", "no_phasenet_plus_P", "no_detector_trigger", "trigger_not_turned_into_picker", "peak_vetoed_as_S"]
assert set(SCH.p_state) <= set(order_D)
cntD = SCH.groupby(["variant", "p_state"]).size()

fig, axes = plt.subplots(2, 2, figsize=(13.0, 7.6), gridspec_kw=dict(hspace=0.42, wspace=0.42))
yv = np.arange(nv)[::-1]
for ax, ph, order, src, ttl in ((axes[0, 0], "P", order_P, "miss", "Missed P picks by cause"),
                                (axes[0, 1], "S", order_S, "miss", "Missed S picks by cause"),
                                (axes[1, 1], "S", order_D, "chain", "S lost for want of a P pick: why no DL P pick there")):
    left = np.zeros(nv)
    for c in order:
        vals = np.array([(cnt.get((v, ph, c), 0) if src == "miss" else cntD.get((v, c), 0)) for v in VARIANTS], float)
        lab, fc, hat = CAUSE[c]
        ax.barh(yv, vals, left=left, height=0.62, color=fc, hatch=hat, edgecolor="0.25", lw=0.5, zorder=2)
        left += vals
    for y, tot in zip(yv, left):
        ax.text(tot + 1.5, y, f"{int(tot)}", va="center", fontsize=7.5)
    ax.set_yticks(yv)
    ax.set_yticklabels([SHORT[v] for v in VARIANTS])
    h.ytick_markers(ax, yv, VARIANTS, COL, MARK, x=-0.035)
    ax.tick_params(axis="y", pad=16)
    ax.set_xlim(0, left.max() * 1.12)
    ax.set_xlabel("Number of PhaseNet+ picks")
    ax.set_title(ttl, loc="left")
    ax.grid(axis="x", color="0.9", lw=0.6, zorder=0)
# (c): best P value in the covering windows of the P picks lost below minConfidence
ax = axes[1, 0]
rng = np.random.default_rng(0)                   # sideways spread of the points only
for y, v in zip(yv, VARIANTS):
    x = MISS[(MISS.variant == v) & (MISS.phase == "P") & (MISS.why_missed == "model_below_minConfidence")].best_value_in_covering_windows.to_numpy(float)
    ax.plot(x, y + rng.uniform(-0.22, 0.22, len(x)), ls="none", marker=MARK[v], color=COL[v], mec=COL[v], mfc="white", ms=4.2,
            mew=0.9, zorder=3)
    if len(x):
        ax.plot([np.median(x)] * 2, [y - 0.3, y + 0.3], color="k", lw=1.4, zorder=4)
pth = sorted(set(P_MINCONF.values()))
for t in pth:
    ax.axvline(t, color="0.2", lw=1.0, ls="--", zorder=2)
ax.set_yticks(yv)
ax.set_yticklabels([SHORT[v] for v in VARIANTS])
h.ytick_markers(ax, yv, VARIANTS, COL, MARK, x=-0.035)
ax.tick_params(axis="y", pad=16)
ax.set_xlim(-0.012, max(pth) * 1.08)
ax.set_xlabel("Highest model P value in the windows covering the onset")
ax.set_title("P lost below minConfidence: how close did the model come?", loc="left")
ax.grid(axis="x", color="0.9", lw=0.6, zorder=0)
for k, a in enumerate(axes.ravel()):
    h.panel_letter(a, "abcd"[k])
used = []
for c in order_P + order_S + order_D:
    if c not in used:
        used.append(c)
hs = [h.patch(CAUSE[c][1], CAUSE[c][2]) for c in used] + [Line2D([], [], color="0.2", lw=1.0, ls="--"), Line2D([], [], color="k", lw=1.4)]
ls = [CAUSE[c][0] for c in used] + [f"Plugin P minConfidence ({', '.join(f'{t:g}' for t in pth)})", "Median of the points"]
h.legend_above(fig, axes, hs, ls, ncol=4, fontsize=7.4)
FIGS["5"] = h.save_fig(fig, FIG_DIR, "03_5_why_picks_were_missed")
plt.show()
T5 = pd.concat({"P": cnt.xs("P", level="phase").unstack(fill_value=0), "S": cnt.xs("S", level="phase").unstack(fill_value=0)}, axis=1).fillna(0).astype(int).loc[VARIANTS]
display(T5)
display(cntD.unstack(fill_value=0).loc[VARIANTS].rename_axis("S lost for want of a P pick: P state"))
""")

code(r"""
# Figure 5: what it says
mP = MISS[MISS.phase == "P"].groupby("variant").size()
mS = MISS[MISS.phase == "S"].groupby("variant").size()
bP = cnt.xs("P", level="phase").unstack(fill_value=0)["model_below_minConfidence"]
nS = cnt.xs("S", level="phase").unstack(fill_value=0)["no_P_pick_so_no_S_picker"]
det = cnt.xs("P", level="phase").unstack(fill_value=0)[["no_detector_trigger", "trigger_not_turned_into_picker"]]
bv = MISS[(MISS.phase == "P") & (MISS.why_missed == "model_below_minConfidence")]
half = (bv.best_value_in_covering_windows >= 0.5 * bv.variant.map(P_MINCONF)).mean()
sb_thr = {m: SBSET[m]["weight_default_args"] for m in SB_MODELS}
lines = [
    f"- **The detector misses little:** {det.no_detector_trigger.min()}-{det.no_detector_trigger.max()} P onsets per run had no trigger at all and "
    f"{det.trigger_not_turned_into_picker.min()}-{det.trigger_not_turned_into_picker.max()} had a trigger in the dead time.",
    f"- **Most P losses are the model's decision:** the window covered the onset, but the model's best P value stayed below minConfidence: "
    + ", ".join(f"{SHORT[v]} {bP[v]} of {mP[v]}" for v in VARIANTS) + " missed P picks.",
    f"- Of all P picks lost below minConfidence, {half:.0%} reached at least half the threshold (panel c). The default thresholds that "
    f"SeisBench ships with these weights are, against the plugin's P {P_MINCONF[RELIABLE]:g} and S {S_MINCONF[RELIABLE]:g}: "
    + "; ".join(f"{m} P {sb_thr[m].get('P_threshold', np.nan):.3f}, S {sb_thr[m].get('S_threshold', np.nan):.3f} "
                f"({'lower' if sb_thr[m].get('P_threshold', 1) < P_MINCONF[m] else 'higher'})" for m in SB_MODELS)
    + ". For the PhaseNet weights a lower minConfidence would probably recover many of the lost P picks, at the cost of more false "
    "picks; it was not tuned here.",
    f"- **Most S losses come from the plugin's design, not from the S model:** no P pick, so no S picker: "
    + ", ".join(f"{SHORT[v]} {nS[v]} of {mS[v]}" for v in VARIANTS) + " missed S picks.",
    f"- Panel (d): behind these S losses the station's P was mostly lost below minConfidence ("
    + ", ".join(f"{SHORT[v]} {cntD.get((v, 'model_below_minConfidence'), 0)}" for v in VARIANTS)
    + "), or PhaseNet+ itself had no P pick at that station (" + ", ".join(f"{cntD.get((v, 'no_phasenet_plus_P'), 0)}" for v in VARIANTS) + ").",
]
display(Markdown("\n".join(lines)))
""")

# =====================================================================================================
md(r"""
## 7. Figure 6: does the plugin reproduce SeisBench with the same weights?

**What is shown.** Step 09 ran SeisBench's own `classify()` with the same two sets of weights (PhaseNet INSTANCE and
EQTransformer STEAD), the plugin's thresholds and otherwise default settings, continuously over the same
data, and paired its picks with the plugin's picks by the same matching rule.

- (a)-(d): plugin pick time minus SeisBench pick time, in whole samples, n = round(dt × [[FS_HZ]] Hz) (0 = the same
  sample; pairs beyond ±[[SB_HIST_LIM]] samples are counted in the panel). Shaded: within 2 samples, lighter: within 5 samples.
- (e): recall against PhaseNet+, plugin (filled bars) and SeisBench (hatched bars).
- (f): the PhaseNet+ picks that only one of the two found, or neither.

**Why they can differ at all.** The networks are identical (on identical input windows their outputs differ only by
float32 rounding, `seisbench/weights_check.json`; the bound is printed below the figure). What differs is how each forms windows and picks: the plugin runs
one window centered on the detector trigger (P) or windows after the P pick (S); SeisBench slides overlapping windows
over the whole record, combines them, and picks every stretch above the threshold, so it can also pick S without a P.
""")

code(r"""
# Figure 6: plugin against SeisBench
fig = plt.figure(figsize=(13.0, 7.4))
gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.0, 1.25], hspace=0.55, wspace=0.30)
axs6 = []
SB6 = {}
for i, m in enumerate(SB_MODELS):
    for j, ph in enumerate(PHS):
        ax = fig.add_subplot(gs[i, j])
        axs6.append(ax)
        q = SBP[(SBP.model == m) & (SBP.phase == ph)]
        n = h.whole_samples(q.dt_plugin_minus_seisbench_s, FS_HZ)
        a = SBS["models"][m][ph]["all"]
        SB6[(m, ph)] = dict(pairs=len(n), identical=h.frac_within(n, 0), w2=h.frac_within(n, 2), w5=h.frac_within(n, 5),
                            mean=float(q.dt_plugin_minus_seisbench_s.mean()), median_abs=a["median_abs_dt_s"], p95=a["p95_abs_dt_s"],
                            max_samples=int(np.abs(n).max()), beyond=int((np.abs(n) > SB_HIST_LIM).sum()))
        ax.axvspan(-5.5, 5.5, color="0.93", lw=0, zorder=0)
        ax.axvspan(-2.5, 2.5, color="0.84", lw=0, zorder=0)
        k_, c_ = np.unique(n[np.abs(n) <= SB_HIST_LIM], return_counts=True)
        ax.bar(k_, c_, width=0.85, color=COL[m], edgecolor="0.25", lw=0.3, zorder=2)
        ax.axvline(0, color="0.4", lw=0.6, zorder=1)
        ax.set_xlim(-SB_HIST_LIM - 0.5, SB_HIST_LIM + 0.5)
        s = SB6[(m, ph)]
        ax.set_title(f"{SHORT[m]}, {ph}: {s['pairs']} pairs, mean {s['mean']:+.4f} s\nsame sample {s['identical']:.0%}, "
                     f"within 2 / 5 samples {s['w2']:.0%} / {s['w5']:.0%}", loc="left", fontsize=7.8)
        if s["beyond"]:
            ax.text(0.98, 0.96, f"{s['beyond']} beyond ±{SB_HIST_LIM}", transform=ax.transAxes, ha="right", va="top", fontsize=6.8, color="0.25")
        ax.set_xlabel("Plugin − SeisBench (samples of 0.01 s)")
        ax.set_ylabel("Pairs")
# (e) recall, plugin vs SeisBench
ax = fig.add_subplot(gs[0, 2])
axs6.append(ax)
groups = [(m, ph) for m in SB_MODELS for ph in PHS]
for g, (m, ph) in enumerate(groups):
    rp_ = ALL.loc[(m, ph), "recall"]
    rs_ = SBS["models"][m][ph]["seisbench_vs_reference"]["recall"]
    ax.bar(g - 0.19, rp_, width=0.36, color=COL[m], edgecolor="0.25", lw=0.5, zorder=2)
    ax.bar(g + 0.19, rs_, width=0.36, color="white", edgecolor=COL[m], hatch="////", lw=0.9, zorder=2)
    ax.text(g - 0.19, rp_ + 0.015, f"{rp_:.2f}", ha="center", va="bottom", fontsize=7)
    ax.text(g + 0.19, rs_ + 0.015, f"{rs_:.2f}", ha="center", va="bottom", fontsize=7)
ax.set_xticks(range(len(groups)))
ax.set_xticklabels([f"{TICK[m]}\n{ph}" for m, ph in groups], fontsize=7.3)
ax.set_ylim(0, 1.08)
ax.set_ylabel("Recall against PhaseNet+")
ax.set_title("Recall: plugin and SeisBench", loc="left")
ax.grid(axis="y", color="0.9", lw=0.6, zorder=0)
# (f) found by only one, or neither
ax = fig.add_subplot(gs[1, 2])
axs6.append(ax)
for g, (m, ph) in enumerate(groups):
    s_ = SBS["models"][m][ph]
    vals = [s_["reference_found_only_by_seisbench"], s_["reference_found_only_by_plugin"], s_["reference_found_by_neither"]]
    for k, (val, sty) in enumerate(zip(vals, [dict(color="white", edgecolor=COL[m], hatch="////", lw=0.9),
                                               dict(color=COL[m], edgecolor="0.25", lw=0.5),
                                               dict(color="0.82", edgecolor="0.25", lw=0.5)])):
        x = g + (k - 1) * 0.27
        ax.bar(x, val, width=0.25, zorder=2, **sty)
        ax.text(x, val + 1.5, f"{val}", ha="center", va="bottom", fontsize=6.8)
ax.set_xticks(range(len(groups)))
ax.set_xticklabels([f"{TICK[m]}\n{ph}" for m, ph in groups], fontsize=7.3)
ax.set_ylabel("PhaseNet+ picks")
ax.set_ylim(0, max(SBS["models"][m][ph]["reference_found_by_neither"] for m, ph in groups) * 1.15)
ax.set_title("PhaseNet+ picks found by only one, or by neither", loc="left")
ax.grid(axis="y", color="0.9", lw=0.6, zorder=0)
for k, a in enumerate(axs6):
    h.panel_letter(a, "abcdef"[k], fontsize=9)
hs = [Patch(color="0.84", lw=0), Patch(color="0.93", lw=0)]
ls = ["Within 2 samples (0.02 s)", "Within 5 samples (0.05 s)"]
for m in SB_MODELS:
    hs += [Patch(facecolor=COL[m], edgecolor="0.25", lw=0.5), Patch(facecolor="white", edgecolor=COL[m], hatch="////", lw=0.9)]
    ls += [f"{LABEL[m]}: plugin (e: recall; f: only the plugin)", f"{LABEL[m]}: SeisBench (e: recall; f: only SeisBench)"]
hs += [Patch(facecolor="0.82", edgecolor="0.25", lw=0.5)]
ls += ["Found by neither (f)"]
h.legend_above(fig, axs6, hs, ls, ncol=2, fontsize=7.4)
FIGS["6"] = h.save_fig(fig, FIG_DIR, "03_6_plugin_vs_seisbench")
plt.show()
""")

code(r"""
# Figure 6: what it says
S6 = pd.DataFrame(SB6).T.astype(float)
only = {(m, ph): SBJ[(SBJ.model == m) & (SBJ.phase == ph) & SBJ.sb_matched & ~SBJ.matched]
        .merge(MISS.rename(columns={"variant": "model"})[["model", "kma_id", "station", "phase", "why_missed"]],
               on=["model", "kma_id", "station", "phase"], how="left") for m in SB_MODELS for ph in PHS}
nopS = {m: int((only[(m, 'S')].why_missed == "no_P_pick_so_no_S_picker").sum()) for m in SB_MODELS}
belowP = {m: int((only[(m, 'P')].why_missed == "model_below_minConfidence").sum()) for m in SB_MODELS}
wmax = max(max(v_["same_input_max_abs_diff"] for v_ in WCHK[m]["phases"].values()) for m in SB_MODELS if m in WCHK)
cpu1 = {m: SBRUN["1 thread"]["models"][m]["cpu_classify_s"] / SBRUN["1 thread"]["station_hours_Z"] for m in SB_MODELS}
lines = [
    f"- **Same networks:** on identical input windows the ONNX files and SeisBench differ by at most {wmax:.1e} (float32 rounding).",
    f"- **Same pick times to a sample or two:** median |dt| " + ", ".join(f"{SHORT[m]} {ph} {S6.loc[(m, ph), 'median_abs']:.3f} s" for m in SB_MODELS for ph in PHS)
    + f"; {S6.w5.min():.0%}-{S6.w5.max():.0%} of the pairs agree within 5 samples and {S6.w2.min():.0%}-{S6.w2.max():.0%} within 2.",
    f"- **No bias between the two:** mean plugin − SeisBench " + ", ".join(f"{S6.loc[(m, ph), 'mean']:+.4f} s" for m in SB_MODELS for ph in PHS)
    + f" ({SHORT[SB_MODELS[0]]} P, S; {SHORT[SB_MODELS[1]]} P, S), at most {S6['mean'].abs().max() * FS_HZ:.2f} of a sample, with both signs.",
    f"- **SeisBench finds somewhat more of the PhaseNet+ picks, mainly S:** of the S picks only SeisBench found, "
    + ", ".join(f"{nopS[m]} of {len(only[(m, 'S')])} ({SHORT[m]})" for m in SB_MODELS)
    + " are at stations where the plugin had no P pick, so its S picker never ran. Of the P picks only SeisBench found, "
    + ", ".join(f"{belowP[m]} of {len(only[(m, 'P')])} ({SHORT[m]})" for m in SB_MODELS) + " were below minConfidence in the plugin's centered window.",
    f"- Continuous SeisBench costs more CPU on one thread: " + ", ".join(f"{SHORT[m]} {cpu1[m]:.3f} CPU-s per station-hour "
    f"({cpu1[m] / COST.loc[m, 'cpu_s_per_station_hour']:.2f} times the plugin)" for m in SB_MODELS) + " (Figure 8).",
]
display(Markdown("\n".join(lines)))
""")

# =====================================================================================================
md(r"""
## 8. Figure 7: fast against reliable P settings

**What is shown.** The same model (PhaseNet, INSTANCE weights) run twice: with the *reliable* P setting (one window
centered on the trigger, so the pick can only be made once the window is full, half a window after the trigger) and
with the README's *fast* P setting (a series of short windows that end soon after the trigger, listed in section 1.3;
the first one with a P value above minConfidence is accepted). Everything else is the same, including the dead time, so both runs start pickers on the
same triggers.

- (a) fast minus reliable P pick time for the P picks the two runs share inside the event windows, in whole samples;
- (b) *latency*: how long after the onset the pick could be made, i.e. the end of the accepted model window minus
  the pick time (the data the model needed; processing time on top is small, Figure 8), as cumulative curves;
- (c) the price: counts of P picks, false P picks outside the event windows (with their rate per station-hour) and S
  waves picked as P inside the windows;
- (d) P recall, precision and F1 against PhaseNet+.
""")

code(r"""
# Figure 7: fast against reliable (phasenet_instance, P picks)
FR = [RELIABLE, FAST]
FRLAB = {RELIABLE: "Reliable P setting", FAST: "Fast P setting"}
fig, axes = plt.subplots(2, 2, figsize=(12.0, 7.6), gridspec_kw=dict(hspace=0.5, wspace=0.28))
# (a)
ax = axes[0, 0]
k_, c_ = np.unique(nw_, return_counts=True)
ax.axvspan(-5.5, 5.5, color="0.93", lw=0, zorder=0)
ax.axvspan(-2.5, 2.5, color="0.84", lw=0, zorder=0)
ax.bar(k_, c_, width=0.85, color=COL[FAST], edgecolor="0.25", lw=0.3, zorder=2)
ax.axvline(0, color="0.4", lw=0.6, zorder=1)
ax.set_xlabel("Fast − reliable P pick time (samples of 0.01 s)")
ax.set_ylabel("P picks found by both runs")
ax.set_title(f"{len(nw_)} shared P picks in the event windows: same sample {h.frac_within(nw_, 0):.0%},\n"
             f"within 2 samples {h.frac_within(nw_, 2):.0%}, within 5 samples {h.frac_within(nw_, 5):.0%}", loc="left")
# (b)
ax = axes[0, 1]
LAT = {}
for v in FR:
    x = FVRL[(FVRL.variant == v) & FVRL.in_window].pick_available_after_onset_s.to_numpy()
    xs, ys = h.ecdf(x)
    LAT[v] = dict(n=len(x), median=float(np.median(x)), p90=float(np.quantile(x, 0.9)), max=float(x.max()))
    ax.step(xs, ys, where="post", color=COL[v], lw=1.6, zorder=3)
    ax.axvline(LAT[v]["median"], color=COL[v], lw=1.0, ls="--", zorder=2)
    ax.text(LAT[v]["median"] + 0.25, 0.42 if v == FAST else 0.30, f"median {LAT[v]['median']:.2f} s", color="0.1", fontsize=7.5,
            ha="left", va="center", bbox=dict(fc="white", ec="none", pad=0.5))
ax.set_xlim(0, max(LAT[v]["max"] for v in FR) * 1.03)
ax.set_ylim(0, 1.02)
ax.set_xlabel("Time from the onset until the pick could be made (s)")
ax.set_ylabel("Share of the P picks in the event windows")
ax.set_title("Latency: end of the accepted model window minus the pick time", loc="left")
ax.grid(color="0.92", lw=0.6, zorder=0)
# (c)
ax = axes[1, 0]
uc_ = UNM[UNM.phase == "P"].groupby(["variant", "class"]).size()
CNT7 = {v: {"All P picks": int((DLP[(DLP.variant == v) & (DLP.phase == "P")]).shape[0]),
            "P picks in the event windows": int(ALL.loc[(v, "P"), "n_dl_in_window"]),
            "False P picks outside the windows": int(ow.loc[(v, "P"), "n_coincident"] + ow.loc[(v, "P"), "n_isolated"]),
            "S waves picked as P (in the windows)": int(uc_.get((v, "phase_confusion"), 0))} for v in FR}
cats = list(CNT7[FR[0]].keys())
for g, cname in enumerate(cats):
    for k, v in enumerate(FR):
        val = CNT7[v][cname]
        x = g + (k - 0.5) * 0.36
        ax.bar(x, val, width=0.34, color=COL[v], edgecolor="0.25", lw=0.5, zorder=2)
        lab = f"{val}"
        if cname.startswith("False"):
            lab += f"\n{ow.loc[(v, 'P'), 'false_per_station_hour_searchable']:.2f}/h"
        ax.text(x, val + 6, lab, ha="center", va="bottom", fontsize=7)
ax.set_xticks(range(len(cats)))
ax.set_xticklabels([textwrap.fill(c, 16) for c in cats], fontsize=7.6)
ax.set_ylim(0, max(max(d_.values()) for d_ in CNT7.values()) * 1.18)
ax.set_ylabel("Number of picks")
ax.set_title("The price: more picks, more false picks, more S waves picked as P", loc="left")
ax.grid(axis="y", color="0.92", lw=0.6, zorder=0)
# (d)
ax = axes[1, 1]
for g, key in enumerate(("recall", "precision", "f1")):
    for k, v in enumerate(FR):
        val = ALL.loc[(v, "P"), key]
        x = g + (k - 0.5) * 0.36
        ax.bar(x, val, width=0.34, color=COL[v], edgecolor="0.25", lw=0.5, zorder=2)
        ax.text(x, val + 0.015, f"{val:.3f}", ha="center", va="bottom", fontsize=7)
ax.set_xticks(range(3))
ax.set_xticklabels(["P recall", "P precision", "P F1"])
ax.set_ylim(0, 1.08)
ax.set_ylabel("Share (0 to 1)")
ax.set_title("Agreement of the P picks with PhaseNet+", loc="left")
ax.grid(axis="y", color="0.92", lw=0.6, zorder=0)
for k, a in enumerate(axes.ravel()):
    h.panel_letter(a, "abcd"[k])
hs = [Patch(facecolor=COL[v], edgecolor="0.25", lw=0.5) for v in FR] + [Patch(color="0.84", lw=0), Patch(color="0.93", lw=0)]
ls = [f"{LABEL[RELIABLE]}, reliable P setting", f"{LABEL[FAST]}"] + ["Within 2 samples (a)", "Within 5 samples (a)"]
h.legend_above(fig, axes, hs, ls, ncol=2)
FIGS["7"] = h.save_fig(fig, FIG_DIR, "03_7_fast_vs_reliable")
plt.show()
""")

code(r"""
# Figure 7: what it says
acc = FJ[f"{FAST}_accepted_attempt_counts_in_window"]
first_ = int(acc.get("1", acc.get(1, 0)))
lines = [
    f"- **Almost the same P times:** of {FJ['n_paired_in_window']} shared P picks in the event windows, {FJ['in_window_identical_fraction']:.0%} "
    f"fall on the same sample, {FJ['in_window_within_2_samples_fraction']:.0%} within 2 samples and {FJ['in_window_within_5_samples_fraction']:.0%} "
    f"within 5 samples; median |dt| {FJ['dt_in_window_median_abs_dt_s']:.3f} s, mean {FJ['dt_in_window_mean_dt_s']:+.4f} s, largest "
    f"{FJ['dt_in_window_max_abs_dt_s']:.2f} s.",
    f"- **Much earlier picks:** median {LAT[FAST]['median']:.2f} s after the onset (90% within {LAT[FAST]['p90']:.1f} s) instead of "
    f"{LAT[RELIABLE]['median']:.2f} s ({LAT[RELIABLE]['p90']:.1f} s); {first_} of the fast run's {LAT[FAST]['n']} in-window P picks came "
    f"from the first window, which ends {SETT.loc[FAST, 'P windows end after the trigger (s)'].split(',')[0]} s after the trigger.",
    f"- **The price:** {CNT7[FAST]['All P picks']} instead of {CNT7[RELIABLE]['All P picks']} P picks; "
    f"{ow.loc[(FAST, 'P'), 'false_per_station_hour_searchable']:.2f} instead of {ow.loc[(RELIABLE, 'P'), 'false_per_station_hour_searchable']:.2f} "
    f"false P picks per station-hour ({ow.loc[(FAST, 'P'), 'false_per_station_hour_searchable'] / ow.loc[(RELIABLE, 'P'), 'false_per_station_hour_searchable']:.1f} times); "
    f"{CNT7[FAST]['S waves picked as P (in the windows)']} instead of {CNT7[RELIABLE]['S waves picked as P (in the windows)']} S waves picked as P; "
    f"P precision {ALL.loc[(FAST, 'P'), 'precision']:.2f} instead of {ALL.loc[(RELIABLE, 'P'), 'precision']:.2f} at a P recall of "
    f"{ALL.loc[(FAST, 'P'), 'recall']:.2f} instead of {ALL.loc[(RELIABLE, 'P'), 'recall']:.2f}. The S picks are almost unchanged "
    f"(S F1 {ALL.loc[(FAST, 'S'), 'f1']:.3f} against {ALL.loc[(RELIABLE, 'S'), 'f1']:.3f}).",
    f"- The CPU cost rises with the number of model windows: {COST.loc[FAST, 'cpu_s_per_station_hour']:.3f} instead of "
    f"{COST.loc[RELIABLE, 'cpu_s_per_station_hour']:.3f} CPU-s per station-hour ({int(COST.loc[FAST, 'p_windows'])} instead of "
    f"{int(COST.loc[RELIABLE, 'p_windows'])} P windows).",
]
display(Markdown("\n".join(lines)))
""")

# =====================================================================================================
md(r"""
## 9. Figure 8: picks outside the event windows, and CPU cost

**What is shown.**

- (a) DL picks made *outside* every catalog event window, per station-hour of searchable data (the data outside the
  windows, without scautopick's start-up time and the last half model window of each file). Picks that fall into the
  window of another catalog event are not counted. The rest are split into *coincident* picks (P picks at several
  stations at nearly the same time, as defined in section 1.3: possibly real, uncatalogued events; an S pick takes its
  P pick's class) and *isolated* picks
  (everything else: mostly false triggers). An associator such as scanloc has to reject these.
- (b) CPU seconds of the whole scautopick process (detector, amplitudes and model) per station-hour, on one thread;
  for the two models also run in SeisBench, the cost of SeisBench's continuous `classify()` on one thread (hatched).
- (c) the trade-off: P recall against the rate of false P picks.
""")

code(r"""
# Figure 8: false picks per station-hour, CPU cost, and the trade-off
fig, axes = plt.subplots(1, 3, figsize=(14.6, 4.8), gridspec_kw=dict(width_ratios=[1.55, 1.0, 0.95], wspace=0.55))
TICK3 = {v: SHORT[v].replace(" ", "\n") for v in VARIANTS}   # one word per line under narrow bars
ax = axes[0]
for j, v in enumerate(VARIANTS):
    for k, ph in enumerate(PHS):
        r = ow.loc[(v, ph)]
        hrs_ = r.station_hours_searchable
        x = j + (k - 0.5) * 0.38
        iso, coi = r.n_isolated / hrs_, r.n_coincident / hrs_
        sty = dict(color=COL[v], edgecolor="0.25", lw=0.5) if ph == "P" else dict(color="white", edgecolor=COL[v], hatch="////", lw=0.9)
        ax.bar(x, iso, width=0.34, zorder=2, **sty)
        ax.bar(x, coi, bottom=iso, width=0.34, color="0.85", edgecolor="0.25", lw=0.5, zorder=2)
        ax.text(x, iso + coi + 0.03, f"{r.false_per_station_hour_searchable:.2f}", ha="center", va="bottom", fontsize=6.8)
ax.set_xticks(range(nv))
ax.set_xticklabels([TICK3[v] for v in VARIANTS], fontsize=7.3)
ax.set_ylabel("Picks per station-hour")
ax.set_title("False picks outside the event windows (P left, S right)", loc="left")
ax.set_ylim(0, ow.false_per_station_hour_searchable.max() * 1.15)
ax.grid(axis="y", color="0.92", lw=0.6, zorder=0)
ax = axes[1]
yv8 = np.arange(nv)[::-1].astype(float)
for y, v in zip(yv8, VARIANTS):
    val = COST.loc[v, "cpu_s_per_station_hour"]
    has_sb = v in SB_MODELS
    yy = y + (0.19 if has_sb else 0.0)
    ax.barh(yy, val, height=0.36, color=COL[v], edgecolor="0.25", lw=0.5, zorder=2)
    ax.text(val + 0.01, yy, f"{val:.3f}", va="center", fontsize=6.8)
    if has_sb:
        sbv = cpu1[v]
        ax.barh(y - 0.19, sbv, height=0.36, color="white", edgecolor=COL[v], hatch="////", lw=0.9, zorder=2)
        ax.text(sbv + 0.01, y - 0.19, f"{sbv:.3f}", va="center", fontsize=6.8)
ax.set_yticks(yv8)
ax.set_yticklabels([SHORT[v] for v in VARIANTS], fontsize=7.6)
h.ytick_markers(ax, yv8, VARIANTS, COL, MARK, x=-0.04)
ax.tick_params(axis="y", pad=16)
ax.set_xlabel("CPU seconds per station-hour (one thread)")
ax.set_title("CPU cost", loc="left")
ax.set_xlim(0, max(cpu1.values()) * 1.22)
ax.grid(axis="x", color="0.92", lw=0.6, zorder=0)
ax = axes[2]
for v in VARIANTS:
    ax.plot(ow.loc[(v, "P"), "false_per_station_hour_searchable"], ALL.loc[(v, "P"), "recall"], ls="none", marker=MARK[v], color=COL[v],
            mec=COL[v], mfc="white", ms=8, mew=1.4, zorder=3)
ax.set_xlabel("False P picks per station-hour")
ax.set_ylabel("P recall against PhaseNet+")
ax.set_xlim(-0.1, ow.false_per_station_hour_searchable.max() * 1.1)
ax.set_ylim(0.5, 1.0)
ax.set_title("Trade-off: more P found, more false P", loc="left")
ax.grid(color="0.92", lw=0.6, zorder=0)
for k, a in enumerate(axes):
    h.panel_letter(a, "abc"[k])
hs, ls = h.model_handles(VARIANTS, COL, MARK, LABEL)
hs += [h.patch("0.5"), h.patch("white", "////"), h.patch("0.85")]
ls += ["Filled: P picks; plugin (b)", "Hatched: S picks (a); SeisBench classify(), one thread (b)", f"Coincident picks ({COINC})"]
h.legend_above(fig, axes, hs, ls, ncol=3, fontsize=7.6)
FIGS["8"] = h.save_fig(fig, FIG_DIR, "03_8_false_picks_and_cost")
plt.show()
display(ow[["n_outside", "n_other_catalog_event", "n_coincident", "n_isolated", "station_hours_searchable",
            "false_per_station_hour_searchable", "false_per_station_hour_HH", "false_per_station_hour_HG", "false_per_station_hour_EL"]].round(3))
display(COST[["runs", "station_hours", "cpu_s_total", "cpu_s_per_station_hour", "p_windows", "s_windows", "cpu_ms_per_window", "max_rss_mb"]].loc[VARIANTS].round(3))
""")

code(r"""
# Figure 8: what it says
fP = ow.xs("P", level="phase").false_per_station_hour_searchable
nsta = bound["n"]
lines = [
    f"- **False P picks per station-hour:** " + ", ".join(f"{SHORT[v]} {fP[v]:.2f}" for v in VARIANTS) + ". Over a network of "
    f"{nsta} stations, {SHORT[BEST_MODEL]}'s rate means about {fP[BEST_MODEL] * nsta:.0f} single-station P picks per hour that an associator must reject; "
    f"{SHORT['eqtransformer_stead']}'s about {fP['eqtransformer_stead'] * nsta:.0f}.",
    f"- Not all are noise: {int(ow.loc[BEST_MODEL, 'n_coincident'].sum())} of {SHORT[BEST_MODEL]}'s {int((ow.loc[BEST_MODEL, 'n_coincident'] + ow.loc[BEST_MODEL, 'n_isolated']).sum())} "
    f"false P and S picks are coincident ({COINC}): possible uncatalogued events.",
    f"- **Cost is small:** {COST.loc[[v for v in VARIANTS if v.startswith('phasenet') and v != FAST], 'cpu_s_per_station_hour'].min():.2f}-"
    f"{COST.loc[[v for v in VARIANTS if v.startswith('phasenet') and v != FAST], 'cpu_s_per_station_hour'].max():.2f} CPU-s per station-hour for the "
    f"PhaseNet models and {COST.loc['eqtransformer_stead', 'cpu_s_per_station_hour']:.2f} for EQTransformer ({COST.loc['eqtransformer_stead', 'cpu_ms_per_window']:.1f} ms "
    f"per window against {COST.loc[BEST_MODEL, 'cpu_ms_per_window']:.1f}); peak memory {COST.max_rss_mb.min():.0f}-{COST.max_rss_mb.max():.0f} MB, "
    f"at the README's permissive detector setting ({COST.loc[BEST_MODEL, 'triggers'] / COST.loc[BEST_MODEL, 'station_hours']:.0f} triggers per station-hour).",
    f"- SeisBench's continuous picking on one thread needs " + " and ".join(f"{cpu1[m] / COST.loc[m, 'cpu_s_per_station_hour']:.2f} times ({SHORT[m]})" for m in SB_MODELS)
    + " as much CPU (it includes Python reading and data handling; a fair 'same data, same thread count' comparison, not a tuned benchmark).",
    f"- **Trade-off (c):** the model that finds the most P picks also makes the most false ones; {SHORT['eqtransformer_stead']} makes almost none but finds only "
    f"{ALL.loc[('eqtransformer_stead', 'P'), 'recall']:.2f} of the P picks.",
]
display(Markdown("\n".join(lines)))
""")

# =====================================================================================================
md(r"""
## 10. Figure 9: are the DL picks good enough for double-difference relocation?

**What was done in step 09.** For each event, the DL picks inside the event window (section 1.3), one per station
and phase (the most confident), were written as a catalog and relocated with pyrtdd, *catalog only*
(no cross-correlation), with the 'hypodd_like' settings. As a *control*, the PhaseNet+ picks were relocated with exactly
the same settings: the control separates the effect of the picks from the effect of the program. Variants: a
travel-time check (picks far from the model travel time dropped first, with step 09's tolerance), and for the best model a "matched only"
pair (the same event-station-phase set, once with DL times and once with PhaseNet+ times). Every setting is in
`reloc/<solution>/settings.json`.

**How solutions are compared.** *Relative geometry* (step 09's metric a): each solution in east, north and up meters,
its own centroid removed, then the RMS over the events of the 3-D difference (and of each component). *Absolute
position* (metric b): how far the whole cluster moved from its common starting point.

**What is shown.**

Figure 9a:

- (a) map view and (b) east-west depth section of four solutions, each with its own centroid removed: HypoDD dt.cc (the
  cross-correlation solution, the most precise), HypoDD dt.ct (catalog only), the pyrtdd control (PhaseNet+ picks) and
  pyrtdd from the best model's picks; thin lines join each event's control and DL positions; the numbers are the
  event numbers (at the dt.cc positions);
- (c) how far each cluster moved as a whole from its start (log scale).

Figure 9b: relative-geometry RMS (metric a) of every solution, against HypoDD dt.cc (top row) and against the pyrtdd
control (bottom row); columns: the 3-D RMS and the RMS of the east, north and up components. In the bottom row the
dashed lines are HypoDD dt.ct's bootstrap 95% half-widths (median over the events), a measure of how precisely
catalog-only DD places these events. The last row of the bottom panels compares the best model's matched-only solution
with the PhaseNet+ solution of exactly the same picks.
""")

code(r"""
# Figure 9: relocation from the DL picks; styles of the solutions
SOL = {"all_at_centroid": ("All events at one point (no information)", dict(color="0.85", edgecolor="0.3")),
       "hypodd_dtcc": ("HypoDD dt.cc (cross-correlation)", dict(color="k", edgecolor="k")),
       "hypodd_dtct": ("HypoDD dt.ct (catalog only)", dict(color="0.55", edgecolor="0.3")),
       "control_phasenet_plus": ("pyrtdd, PhaseNet+ picks (control)", dict(color=COL["phasenet_plus"], edgecolor="0.25")),
       "control_phasenet_plus_same_subset": ("pyrtdd, PhaseNet+ picks, matched subset", dict(color="white", edgecolor=COL["phasenet_plus"], hatch="////")),
       "dl_phasenet_original_window": (f"pyrtdd, {SHORT['phasenet_original']} picks", dict(color=COL["phasenet_original"], edgecolor="0.25")),
       "dl_phasenet_original_window_tt": (f"pyrtdd, {SHORT['phasenet_original']}, travel-time check", dict(color="white", edgecolor=COL["phasenet_original"], hatch="////")),
       "dl_phasenet_original_matched_only": (f"pyrtdd, {SHORT['phasenet_original']}, matched subset", dict(color="white", edgecolor=COL["phasenet_original"], hatch="....")),
       "dl_phasenet_instance_window": (f"pyrtdd, {SHORT['phasenet_instance']} picks", dict(color=COL["phasenet_instance"], edgecolor="0.25")),
       "dl_phasenet_instance_window_tt": (f"pyrtdd, {SHORT['phasenet_instance']}, travel-time check", dict(color="white", edgecolor=COL["phasenet_instance"], hatch="////")),
       "dl_eqtransformer_stead_window": (f"pyrtdd, {SHORT['eqtransformer_stead']} picks", dict(color=COL["eqtransformer_stead"], edgecolor="0.25")),
       "dl_phasenet_stead_window": (f"pyrtdd, {SHORT['phasenet_stead']} picks", dict(color=COL["phasenet_stead"], edgecolor="0.25"))}
MAPSTY = {"hypodd_dtcc": dict(marker="o", color="k", mfc="k", ms=5.5), "hypodd_dtct": dict(marker="o", color="0.45", mfc="white", ms=6.5),
          "control_phasenet_plus": dict(marker=MARK["phasenet_plus"], color=COL["phasenet_plus"], mfc="white", ms=7),
          "dl_phasenet_original_window": dict(marker=MARK["phasenet_original"], color=COL["phasenet_original"], mfc="white", ms=6.5)}
same_tt = [s for s in ("dl_eqtransformer_stead_window", "dl_phasenet_stead_window") if np.allclose(PE[s], PE[s + "_tt"])]
cm = CMP.set_index(["solution", "reference"])
REL = {s: PE[s] - PE[s].mean(axis=0) for s in PE}
evn = POS[POS.solution == "hypodd_dtcc"].sort_values("rtdd_id").rtdd_id.to_numpy()

# Figure 9a: geometry and drift
fig = plt.figure(figsize=(14.2, 4.9))
gs = fig.add_gridspec(1, 5, width_ratios=[1.0, 0.16, 1.0, 0.62, 1.05], wspace=0.08)
axA, axB, axC = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[0, 4])
for ax, (ix, iy, xl, yl, ttl) in ((axA, (0, 1, "East (m)", "North (m)", "Map view, own centroid removed")),
                                  (axB, (0, 2, "East (m)", "Up (m)", "East-west section, own centroid removed"))):
    for k in range(len(evn)):
        a, b_ = REL["control_phasenet_plus"][k], REL["dl_phasenet_original_window"][k]
        ax.plot([a[ix], b_[ix]], [a[iy], b_[iy]], color=COL["phasenet_original"], lw=0.6, zorder=1)
    for s in MAP_SOLUTIONS:
        sty = MAPSTY[s]
        ax.plot(REL[s][:, ix], REL[s][:, iy], ls="none", marker=sty["marker"], color=sty["color"], mec=sty["color"], mfc=sty["mfc"],
                ms=sty["ms"], mew=1.1, zorder=3)
    for k, n_ in enumerate(evn):
        ax.annotate(str(n_), (REL["hypodd_dtcc"][k, ix], REL["hypodd_dtcc"][k, iy]), xytext=(3, -8), textcoords="offset points",
                    fontsize=6.5, color="0.1", zorder=4)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.set_title(ttl, loc="left")
    ax.grid(color="0.92", lw=0.6, zorder=0)
csol = ["hypodd_dtcc", "hypodd_dtct", "control_phasenet_plus", "control_phasenet_plus_same_subset", "dl_phasenet_original_window",
        "dl_phasenet_original_window_tt", "dl_phasenet_original_matched_only", "dl_phasenet_instance_window", "dl_phasenet_instance_window_tt",
        "dl_eqtransformer_stead_window", "dl_phasenet_stead_window"]
yc = np.arange(len(csol))[::-1]
for y, s in zip(yc, csol):
    v_ = CSH.loc[s, "shift_3d_m"]
    axC.barh(y, v_, height=0.6, lw=0.6, zorder=2, **SOL[s][1])
    axC.text(v_ * 1.12, y, f"{v_:.0f} m" if v_ >= 10 else f"{v_:.1f} m", va="center", fontsize=6.8)
axC.set_xscale("log")
axC.set_xlim(0.5, CSH.shift_3d_m.max() * 8)
axC.set_yticks(yc)
axC.set_yticklabels([SOL[s][0].replace("pyrtdd, ", "") for s in csol], fontsize=7)
axC.set_xlabel("Cluster centroid moved from its start (m, log scale)")
axC.set_title("Absolute position: drift of the whole cluster", loc="left")
axC.grid(axis="x", color="0.92", lw=0.6, zorder=0)
for k, a in enumerate((axA, axB, axC)):
    h.panel_letter(a, "abc"[k])
hs = [Line2D([], [], ls="none", marker=MAPSTY[s]["marker"], color=MAPSTY[s]["color"], mec=MAPSTY[s]["color"], mfc=MAPSTY[s]["mfc"], ms=MAPSTY[s]["ms"])
      for s in MAP_SOLUTIONS] + [Line2D([], [], color=COL["phasenet_original"], lw=0.6)]
ls = [SOL[s][0] for s in MAP_SOLUTIONS] + ["Same event: control to DL"]
h.legend_above(fig, [axA, axB], hs, ls, ncol=3, fontsize=7.6)
FIGS["9a"] = h.save_fig(fig, FIG_DIR, "03_9a_dd_relocation_geometry")
plt.show()
print("solutions identical with and without the travel-time check (not drawn twice):", ", ".join(same_tt))
""")

code(r"""
# Figure 9b: relative-geometry RMS, against HypoDD dt.cc (top) and the pyrtdd control (bottom); columns 3-D, E, N, U
bt = RSUM["reference_bootstrap_95_median_m"]["hypodd_dtct"]
REFROWS = [("hypodd_dtcc", "Against HypoDD dt.cc", [(s, "hypodd_dtcc") for s in RMS_SOLUTIONS], None),
           ("control_phasenet_plus", "Against the pyrtdd control (PhaseNet+ picks)",
            [(s, "control_phasenet_plus") for s in RMS_SOLUTIONS if s != "control_phasenet_plus"]
            + [("dl_phasenet_original_matched_only", "control_phasenet_plus_same_subset")],
            {"rms_east_m": bt["boot_ex95_m"], "rms_north_m": bt["boot_ey95_m"], "rms_up_m": bt["boot_ez95_m"]})]
COLS9 = [("rms_3d_m", "3-D"), ("rms_east_m", "East"), ("rms_north_m", "North"), ("rms_up_m", "Up")]
nrow9 = max(len(r[2]) for r in REFROWS)
fig, axes = plt.subplots(len(REFROWS), len(COLS9), figsize=(14.0, 0.33 * nrow9 * len(REFROWS) + 2.2), sharex="col",
                         gridspec_kw=dict(hspace=0.36, wspace=0.06))
for i, (ref, rtitle, rows, refl) in enumerate(REFROWS):
    y = np.arange(len(rows))[::-1].astype(float)
    for j, (c, ctitle) in enumerate(COLS9):
        ax = axes[i, j]
        for yy, (s, r) in zip(y, rows):
            val = cm.loc[(s, r), c]
            ax.barh(yy, val, height=0.62, lw=0.6, zorder=2, **SOL[s][1])
            ax.text(val + 2, yy, f"{val:.1f}", va="center", fontsize=6.6, zorder=5,
                    bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
        if refl is not None and c in refl:
            ax.axvline(refl[c], color="0.2", lw=1.0, ls="--", zorder=3)
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_yticks(y)
        if j == 0:
            ax.set_yticklabels([SOL[s][0].replace("pyrtdd, ", "") + ("" if r == ref else ",\nagainst the PhaseNet+ picks of the same subset")
                                for s, r in rows], fontsize=7)
        else:
            ax.tick_params(labelleft=False)
        ax.grid(axis="x", color="0.92", lw=0.6, zorder=0)
        ax.set_title(ctitle, loc="left")
        if i == len(REFROWS) - 1:
            ax.set_xlabel(f"{ctitle} RMS difference (m)")
for j in range(len(COLS9)):
    xmax = max(axes[i, j].get_xlim()[1] for i in range(len(REFROWS)))
    axes[0, j].set_xlim(0, xmax * 1.12)
for k, a in enumerate(axes.ravel()):
    h.panel_letter(a, "abcdefgh"[k])
heads = [h.text_above(fig, list(axes[i]), f"Relative geometry {REFROWS[i][1][0].lower()}{REFROWS[i][1][1:]}", pad=0.012, fontsize=9.5)
         for i in range(len(REFROWS))]
hs = [Line2D([], [], color="0.2", lw=1.0, ls="--")]
ls = ["HypoDD dt.ct bootstrap 95% half-width, median over the events (bottom row)"]
h.legend_above(fig, list(axes.ravel()) + heads, hs, ls, ncol=1, fontsize=7.6)
FIGS["9b"] = h.save_fig(fig, FIG_DIR, "03_9b_dd_relocation_rms")
plt.show()
""")

code(r"""
# Figure 9: the numbers behind the panels, and what they say
T9 = CMP[CMP.reference.isin(["hypodd_dtcc", "control_phasenet_plus", "control_phasenet_plus_same_subset", "hypodd_dtct"])]
T9 = T9.pivot_table(index="solution", columns="reference", values="rms_3d_m").reindex(["all_at_centroid", "hypoinverse_start", "hypodd_dtct"] + RMS_SOLUTIONS[2:])
T9 = T9.join(CMP.drop_duplicates("solution").set_index("solution").spread_solution_rms_m.rename("spread of the solution (RMS from its centroid)"))
T9 = T9.join(CSH.shift_3d_m.rename("centroid moved from start (m)"))
display(T9.round(1))
q_ctl = cm.loc[("control_phasenet_plus", "hypodd_dtcc")]
q_ct = cm.loc[("hypodd_dtct", "hypodd_dtcc")]
q_one = cm.loc[("all_at_centroid", "hypodd_dtcc")]
q_dl = cm.loc[("dl_phasenet_original_window", "control_phasenet_plus")]
q_dlcc = cm.loc[("dl_phasenet_original_window", "hypodd_dtcc")]
q_mo = cm.loc[("dl_phasenet_original_matched_only", "control_phasenet_plus_same_subset")]
q_hinv = cm.loc[("hypoinverse_start", "hypodd_dtcc")]
others = {"phasenet_instance": "dl_phasenet_instance_window", "eqtransformer_stead": "dl_eqtransformer_stead_window",
          "phasenet_stead": "dl_phasenet_stead_window"}
others_txt = ", ".join(f"{SHORT[v]} {cm.loc[(s, 'control_phasenet_plus'), 'rms_3d_m']:.0f} m" for v, s in others.items())
lossS = {v: 1 - mg.loc[(v, "S", ML_SPLIT[0]), "recall"] for v in others}
lines = [
    f"- **The cluster is tiny.** In HypoDD dt.cc the 11 events lie {q_one.spread_reference_rms_m:.0f} m (RMS) from their centroid; HYPOINVERSE "
    f"scattered them by {q_hinv.spread_solution_rms_m:.0f} m, and every catalog-only DD run collapses that to {T9['spread of the solution (RMS from its centroid)'].drop(['all_at_centroid', 'hypoinverse_start']).min():.0f}-"
    f"{T9['spread of the solution (RMS from its centroid)'].drop(['all_at_centroid', 'hypoinverse_start']).max():.0f} m.",
    f"- **Catalog-only DD does not resolve this cluster's depths, whatever the picks.** Against dt.cc, HypoDD dt.ct is {q_ct.rms_3d_m:.1f} m and the "
    f"PhaseNet+ control {q_ctl.rms_3d_m:.1f} m off, about as far as putting all events at one point ({q_one.rms_3d_m:.1f} m). They do recover the "
    f"east-west stretch (east RMS {q_ctl.rms_east_m:.0f} and {q_ct.rms_east_m:.0f} m against {q_one.rms_east_m:.0f} m for one point) but add vertical "
    f"scatter ({q_ctl.rms_up_m:.0f} and {q_ct.rms_up_m:.0f} m against {q_one.rms_up_m:.0f} m).",
    f"- **The best model's picks give the same horizontal picture as the PhaseNet+ picks:** {q_dl.rms_east_m:.1f} m east and {q_dl.rms_north_m:.1f} m "
    f"north RMS against the control, inside dt.ct's bootstrap 95% half-widths ({bt['boot_ex95_m']:.1f} / {bt['boot_ey95_m']:.1f} m; Figure 9b); in depth they "
    f"differ by {q_dl.rms_up_m:.1f} m RMS ({q_dlcc.rms_up_m:.0f} m against dt.cc).",
    f"- **Pick times alone account for about {q_mo.rms_3d_m:.0f} m RMS, mostly vertical** ({q_mo.rms_east_m:.0f} / {q_mo.rms_north_m:.0f} / "
    f"{q_mo.rms_up_m:.0f} m E / N / U): the matched-only pair has the same observations, once with DL and once with PhaseNet+ times.",
    f"- **Models that miss more picks scatter more:** against the control {others_txt} (they miss "
    f"{min(lossS.values()):.0%}-{max(lossS.values()):.0%} of the small events' S picks, Figure 3).",
    f"- **Caveat, absolute position:** catalog-only pyrtdd moved the control cluster {CSH.loc['control_phasenet_plus', 'shift_3d_m']:.0f} m from its start, "
    f"the same-subset control {CSH.loc['control_phasenet_plus_same_subset', 'shift_3d_m']:.0f} m and the best model's solution "
    f"{CSH.loc['dl_phasenet_original_window', 'shift_3d_m']:.0f} m; HypoDD moved dt.ct {CSH.loc['hypodd_dtct', 'shift_3d_m']:.0f} m and dt.cc "
    f"{CSH.loc['hypodd_dtcc', 'shift_3d_m']:.1f} m. Nothing ties a catalog-only pyrtdd solution to an absolute position here, so only the "
    "relative geometry (Figure 9b) is compared; the absolute position of a catalog-only solution is not meaningful.",
]
display(Markdown("\n".join(lines)))
""")

# =====================================================================================================
md(r"""
## 11. Comprehensive summary

First the headline numbers (computed from the files above), then the take-home messages, the caveats, the
consistency of the files, and how to reproduce this notebook. Every number in this section is formatted from variables
computed above; none is typed in.
""")

code(r"""
# 11. headline numbers per picker run
rows = []
for v in VARIANTS:
    rows.append({"Run": SHORT[v],
                 "P recall": ALL.loc[(v, "P"), "recall"], "S recall": ALL.loc[(v, "S"), "recall"],
                 "P precision": ALL.loc[(v, "P"), "precision"], "S precision": ALL.loc[(v, "S"), "precision"],
                 "Pooled F1": ALL.loc[(v, "P+S"), "f1"],
                 f"P recall, {ML_SPLIT[0]}": mg.loc[(v, "P", ML_SPLIT[0]), "recall"], f"S recall, {ML_SPLIT[0]}": mg.loc[(v, "S", ML_SPLIT[0]), "recall"],
                 "P median dt (s)": ALL.loc[(v, "P"), "median_dt_s"], "S median dt (s)": ALL.loc[(v, "S"), "median_dt_s"],
                 "P p95 |dt| (s)": ALL.loc[(v, "P"), "p95_abs_dt_s"], "S p95 |dt| (s)": ALL.loc[(v, "S"), "p95_abs_dt_s"],
                 "P lost below minConfidence": int(bP[v]), "S lost for want of a P pick": int(nS[v]),
                 "False P per station-hour": fP[v], "CPU-s per station-hour": COST.loc[v, "cpu_s_per_station_hour"],
                 "DD: 3-D RMS vs control (m)": cm.loc[(f"dl_{v}_window", "control_phasenet_plus"), "rms_3d_m"] if (f"dl_{v}_window", "control_phasenet_plus") in cm.index else np.nan})
HEAD = pd.DataFrame(rows).set_index("Run")
display(HEAD.T.round(3))
K = [("Picker runs", f"{len(VARIANTS)} variants x {len(EVM)} events; {LOGSTAT['n_logs']} scautopick logs, {LOGSTAT['n_error']} [error] lines, "
      f"{LOGSTAT['n_warning']} [warning] lines ({', '.join(f'{n} {k}' for k, n in LOGSTAT['warning_kinds'].items())})", "Section 1.1"),
     ("Stations and data", f"{bound['n']} bound ({', '.join(f'{n} {k}' for k, n in bound['per_sensor'].items())}); {COST.station_hours.iloc[0]:.1f} station-hours", "Section 1.3"),
     ("Reference", f"{N_REF['P']} P and {N_REF['S']} S PhaseNet+ picks; {SUMJ['n_reference']['outliers']} outliers", "Section 1.1"),
     ("Best model (fixed rule)", f"{BEST_MODEL}: pooled F1 {rk.loc[BEST_MODEL, 'f1']:.3f}, recall P {ALL.loc[(BEST_MODEL, 'P'), 'recall']:.2f} / "
      f"S {ALL.loc[(BEST_MODEL, 'S'), 'recall']:.2f}", "Figure 1"),
     (f"Recall {ML_SPLIT[1]} / {ML_SPLIT[0]} (KMA ML)", f"P {min(rP_hi):.2f}-{max(rP_hi):.2f} / {min(rP_lo):.2f}-{max(rP_lo):.2f}; S {min(rS_hi):.2f}-{max(rS_hi):.2f} / "
      f"{min(rS_lo):.2f}-{max(rS_lo):.2f}", "Figure 3"),
     ("Plugin vs SeisBench", f"median |dt| {S6.median_abs.min():.3f}-{S6.median_abs.max():.3f} s; within 5 samples {S6.w5.min():.0%}-{S6.w5.max():.0%}; "
      f"|mean dt| ≤ {S6['mean'].abs().max():.4f} s", "Figure 6"),
     ("Fast vs reliable P", f"within 5 samples {FJ['in_window_within_5_samples_fraction']:.0%}; latency median {LAT[FAST]['median']:.2f} s vs "
      f"{LAT[RELIABLE]['median']:.2f} s; false P {fP[FAST]:.2f} vs {fP[RELIABLE]:.2f} per station-hour", "Figure 7"),
     ("DD, best model vs PhaseNet+ control", f"{q_dl.rms_3d_m:.1f} m 3-D RMS ({q_dl.rms_east_m:.1f} / {q_dl.rms_north_m:.1f} / {q_dl.rms_up_m:.1f} m E/N/U)", "Figure 9"),
     ("DD, catalog-only vs dt.cc", f"dt.ct {q_ct.rms_3d_m:.1f} m, control {q_ctl.rms_3d_m:.1f} m, best model {q_dlcc.rms_3d_m:.1f} m; one point {q_one.rms_3d_m:.1f} m", "Figure 9"),
     ("DD, cluster drift from start", f"control {CSH.loc['control_phasenet_plus', 'shift_3d_m']:.0f} m, best model {CSH.loc['dl_phasenet_original_window', 'shift_3d_m']:.0f} m, "
      f"dt.cc {CSH.loc['hypodd_dtcc', 'shift_3d_m']:.1f} m", "Figure 9"),
     ("Consistency checks", f"{int(CHKT.OK.sum())} of {len(CHKT)} passed", "Section 1.2")]
KEY = pd.DataFrame(K, columns=["Quantity", "Value", "Where"])
KEY.to_csv(f"{OUT}/summary_key_numbers.csv", index=False)
HEAD.to_csv(f"{OUT}/summary_per_run.csv")
with pd.option_context("display.max_colwidth", 200):
    display(KEY.set_index("Quantity"))
json.dump({"best_model": BEST_MODEL, "events": {"big": EV_BIG, "small": EV_SMALL}, "waveform_stations": {k: list(v.station) for k, v in WF_SEL.items()},
           "per_run": HEAD.to_dict(orient="index"), "checks_passed": int(CHKT.OK.sum()), "checks_total": len(CHKT),
           "log_stats": LOGSTAT, "figures": FIGS}, open(f"{OUT}/summary.json", "w"), indent=1, default=str)
print("saved:", f"{OUT}/summary_key_numbers.csv", f"{OUT}/summary_per_run.csv", f"{OUT}/summary.json")
""")

code(r"""
# 11. take-home messages, written from the computed numbers
lines = [
    f"- **The plugin works.** All {len(VARIANTS) * len(EVM)} picking runs finished ({LOGSTAT['n_error']} [error] lines in "
    f"{LOGSTAT['n_logs']} logs), all {bound['n']} stations were bound, and the plugin's networks reproduce SeisBench with the same weights: "
    f"pick times agree to a median |dt| of {S6.median_abs.min():.3f}-{S6.median_abs.max():.3f} s and {S6.w5.min():.0%}-{S6.w5.max():.0%} within 5 samples, "
    f"without bias (Figure 6).",
    f"- **How well: close to PhaseNet+ for the larger events.** The best model, {SHORT[BEST_MODEL]}, finds {ALL.loc[(BEST_MODEL, 'P'), 'recall']:.0%} of the "
    f"PhaseNet+ P and {ALL.loc[(BEST_MODEL, 'S'), 'recall']:.0%} of the S picks (pooled F1 {rk.loc[BEST_MODEL, 'f1']:.2f}; Figure 1), with a typical time "
    f"difference of {ALL.loc[(BEST_MODEL, 'P'), 'median_abs_dt_s']:.3f} s (P) and {ALL.loc[(BEST_MODEL, 'S'), 'median_abs_dt_s']:.3f} s (S) (Figure 2). "
    f"For {MLC[ML_SPLIT[1]]} every model finds {min(rP_hi):.0%}-{max(rP_hi):.0%} of the P picks (Figure 3, Figure 4a).",
    f"- **Which model:** {SHORT[BEST_MODEL]} by the fixed rule (highest pooled F1), with the most false P picks of the four main models "
    f"({fP[BEST_MODEL]:.2f} per station-hour; Figure 8). {SHORT['eqtransformer_stead']} makes almost none ({fP['eqtransformer_stead']:.2f}) but finds only "
    f"{mg.loc[('eqtransformer_stead', 'P', ML_SPLIT[0]), 'recall']:.0%} of the small events' P picks; {SHORT['phasenet_instance']} lies in between "
    f"({fP['phasenet_instance']:.2f} per station-hour, pooled F1 {rk.loc['phasenet_instance', 'f1']:.2f}).",
    f"- **What limits it (1): minConfidence.** The detector misses few onsets; most lost P picks are windows where the model's P value stayed "
    f"below the plugin's {P_MINCONF[BEST_MODEL]:g} ({bP[BEST_MODEL]} of {mP[BEST_MODEL]} for {SHORT[BEST_MODEL]}, {bP['phasenet_stead']} of "
    f"{mP['phasenet_stead']} for {SHORT['phasenet_stead']}; Figure 5 a, c). This hits the small events hardest "
    f"({MLC[ML_SPLIT[0]]}: P recall {min(rP_lo):.2f}-{max(rP_lo):.2f}; Figures 3, 4b).",
    f"- **What limits it (2): S only after P.** The S picker runs only after a P pick at the same station, so most lost S picks "
    f"({nS[BEST_MODEL]} of {mS[BEST_MODEL]} for {SHORT[BEST_MODEL]}) had no P pick before them (Figure 5 b, d); SeisBench's continuous picking "
    f"finds such S picks (Figure 6 f).",
    f"- **Timing offsets are model properties of a few hundredths of a second** (median dt {SHORT[BEST_MODEL]} P {ALL.loc[(BEST_MODEL, 'P'), 'median_dt_s']:+.3f} s, "
    f"{SHORT[RELIABLE]} S {ALL.loc[(RELIABLE, 'S'), 'median_dt_s']:+.3f} s; Figure 2). Which picker is off cannot be read from them.",
    f"- **Fast P settings** make picks available {LAT[FAST]['median']:.1f} s after the onset instead of {LAT[RELIABLE]['median']:.0f} s with almost the same "
    f"times ({FJ['in_window_within_5_samples_fraction']:.0%} within 5 samples), at {fP[FAST] / fP[RELIABLE]:.1f} times the false P picks (Figure 7).",
    f"- **Cost is no obstacle:** {COST.cpu_s_per_station_hour.min():.2f}-{COST.cpu_s_per_station_hour.max():.2f} CPU-s per station-hour on one thread (Figure 8).",
    f"- **Good enough for catalog-level DD, not a substitute for cross-correlation.** The best model's picks reproduce the PhaseNet+-pick relocation "
    f"horizontally to {q_dl.rms_east_m:.0f} / {q_dl.rms_north_m:.0f} m (E / N) RMS, within catalog-only DD's own precision, but differ by "
    f"{q_dl.rms_up_m:.0f} m in depth; and no catalog-only solution, PhaseNet+ picks included, resolves this cluster's depths (Figure 9).",
]
display(Markdown("**Take-home messages**\n\n" + "\n".join(lines)))
""")

code(r"""
# 11. caveats, and the consistency of the files (written from the computed numbers)
note = open(NOTE09).read()
ratio_note = {m: re.search(rf"{m} [0-9.]+ CPU-s \([0-9.]+ per station-hour, ([0-9.]+) times", note) for m in SB_MODELS}
ratio_note = {m: (float(r.group(1)) if r else np.nan) for m, r in ratio_note.items()}
ratio_file = {m: cpu1[m] / COST.loc[m, "cpu_s_per_station_hour"] for m in SB_MODELS}
cav = [
    f"- **PhaseNet+ is not ground truth.** Recall and precision measure agreement with another automatic picker; counting plausible unmatched "
    f"DL picks as correct raises precision to {ALL.precision_counting_plausible.min():.2f}-{ALL.precision_counting_plausible.max():.2f} (Figure 1).",
    "- **The sign of the timing offsets is open** (Figure 2): the independent verification's waveform examples (note 09, section 2) found a "
    "case where PhaseNet+ was early and one where a DL model was early; Figure 4 shows more stations but is not a statistical test.",
    f"- **Small samples:** {nev[True]} events below and {nev[False]} at or above {ML} {ML_CUT:g}; the waveform examples are "
    f"{sum(len(s) for s in WF_SEL.values())} stations of {len(WF_SEL)} events, chosen by rules.",
    f"- **Only the four models and the fast P settings were varied.** minConfidence (P {P_MINCONF[BEST_MODEL]:g}, S {S_MINCONF[BEST_MODEL]:g}), "
    f"the detector and the dead time stay at the README and plugin values; Figure 5 suggests minConfidence matters most.",
    f"- **Relocation:** one relocator setting ('hypodd_like', catalog only); catalog-only pyrtdd lets the whole cluster drift (up to "
    f"{CSH.shift_3d_m.max() / 1000:.1f} km here), so only relative geometry is compared.",
    f"- **SeisBench CPU times** include Python reading and data handling.",
]
display(Markdown("**Caveats**\n\n" + "\n".join(cav)))
inc = [f"- Consistency checks: {int(CHKT.OK.sum())} of {len(CHKT)} passed" + ("." if FAILED.empty else f"; failed: {', '.join(FAILED.Check)}.")]
for m in SB_MODELS:
    if np.isfinite(ratio_note[m]) and abs(round(ratio_file[m], 1) - ratio_note[m]) > 1e-9:
        inc.append(f"- Note 09, section 7 gives SeisBench one-thread CPU for {m} as {ratio_note[m]:g} times the plugin; the files give "
                   f"{ratio_file[m]:.3f}, i.e. {ratio_file[m]:.1f} after rounding (the 'Result in brief' of note 09 is consistent with the files).")
display(Markdown("**Consistency of the files**\n\n" + "\n".join(inc)))
print("figures written:")
for k_, (png, pdf) in FIGS.items():
    print(f"  {k_}: {png}  |  {pdf}")
""")

md(r"""
### How to reproduce

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker/notebooks
source /home/msseo/miniforge3/etc/profile.d/conda.sh && conda activate pyrtdd
python build_03_gwangyang_dlpicker.py      # writes 03_gwangyang_dlpicker.ipynb (and compiles every code cell)
rm -f figures/03_*.png figures/03_*.pdf     # remove old figures
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=pyrtdd \
    --ExecutePreprocessor.timeout=1800 03_gwangyang_dlpicker.ipynb
```

- Inputs (read only): the step 09 result folders `runs/gwangyang/dlpicker/{analysis, seisbench, reloc, settings,
  output}` (the scautopick logs are only scanned for error and warning lines), the playback miniSEED files in
  `runs/gwangyang/dlpicker/input/` (only to check the SAC copies), and from `data/gwangyang_11ev/`: the PhaseNet+
  picks, the event table, the HypoDD dt.cc table and the SAC waveforms.
- To regenerate the step 09 results themselves (not needed for this notebook): `runs/gwangyang/dlpicker/scripts/09_dlpicker.sh`
  (stages compare, seisbench_compare and reloc take seconds; see note 09).
- Outputs: figures `notebooks/figures/03_*.png` (200 dpi) and `.pdf`; in `runs/gwangyang/dlpicker_nb03/`:
  `summary_key_numbers.csv`, `summary_per_run.csv` and `summary.json`.
- Helper code: `notebooks/lib/nb03_helpers.py` (the filter and layout helpers are verbatim copies from
  `notebooks/lib/sp_offset.py`); fonts: `notebooks/lib/nbfont.py`.
- Run time: printed by the last cell (one CPU; no picking, no relocation).
""")

code(r"""
# run time of this execution
print(f"run time {(_time.time() - T_START) / 60.0:.1f} min")
""")

# =====================================================================================================
for i, c in enumerate(CELLS):
    if c.cell_type == "code":
        compile(c.source, f"<cell {i}>", "exec")
        assert '"""' not in c.source and "'''" not in c.source, f"cell {i}: no triple-quoted strings in cells"
nb = new_notebook(cells=CELLS, metadata={
    "kernelspec": {"name": "pyrtdd", "display_name": "pyrtdd", "language": "python"},
    "language_info": {"name": "python"}})
nbformat.write(nb, OUT)
print(f"wrote {OUT}: {len(CELLS)} cells ({sum(c.cell_type == 'code' for c in CELLS)} code); every code cell compiled")
