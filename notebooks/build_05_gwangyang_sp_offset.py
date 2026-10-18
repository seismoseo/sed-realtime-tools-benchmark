# build_05_gwangyang_sp_offset.py -- writes notebooks/05_gwangyang_sp_offset.ipynb (markdown + code cells).
#
# Run in conda env 'pyrtdd':
#   python build_05_gwangyang_sp_offset.py
# then execute (kernel 'pyrtdd'):
#   jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=pyrtdd \
#       --ExecutePreprocessor.timeout=3600 05_gwangyang_sp_offset.ipynb
#
# Every emitted code cell is compiled with compile(..., 'exec') before the notebook is written; code cells
# carry '#' comments only (no docstrings). Heavy helpers live in notebooks/lib/sp_offset.py.
# Markdown cells quote parameter values as [[NAME]] or [[NAME:i]] (element i of a tuple or list). They are filled
# from the parameter cell itself, which is executed once here, so the text and the parameters cannot disagree.

import re

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/notebooks/05_gwangyang_sp_offset.ipynb"
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
T_START = _time.time()                            # the run time is printed at the very end
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
WORK = f"{PROJECT}/runs/gwangyang/sp_offset"     # computed files (NonLinLoc and pyrtdd runs, tables)
FIG_DIR = f"{PROJECT}/notebooks/figures"          # every figure as 05_*.png (200 dpi) and 05_*.pdf
LIB = f"{PROJECT}/notebooks/lib"                  # nbfont.py and sp_offset.py

# --- inputs ---
HAND_TABLE_DIR = f"{DATA}/reference_supplement/manual_vs_phasenet"     # the user's hand-pick tables (server B, 2026-04-22)
SPOTCHECK_DIR = f"{DATA}/reference_supplement/manual_picks_provenance/sac_spotcheck"   # 16 SAC files copied read-only from server B
ML_PICKS_DIR = f"{DATA}/reference_supplement/manual_picks_provenance/ml_picks_20260422"  # absolute times of the tables' PhaseNet column
HAND_PICKS_UTC = f"{DATA}/reference_tables/picks_manual_utc.csv"       # OUTPUT of section 1.1: tidy hand picks in UTC
PNPLUS_PICKS = f"{DATA}/reference_tables/picks_phasenet_plus.csv"      # the 763 PhaseNet+ reference picks
HYPODD_DTCC = f"{DATA}/reference_tables/hypodd_dtcc.csv"               # HypoDD dt.cc relocations
HYPOINVERSE = f"{DATA}/reference_tables/hypoinverse_kim1983.csv"
EVENT_ID_MAP = f"{DATA}/reference_tables/event_id_map.csv"
STATIONS = f"{DATA}/inputs/nll_kim1983/stations_gridded.csv"           # the station coordinates the grids were made for
STATION_SENSORS = f"{DATA}/reference/gwangyang_pnplus/station_table/used_stations_100km.csv"
NLL_TIME_DIR = f"{DATA}/inputs/nll_kim1983/time"                       # kim1983 NonLinLoc grids (2-D, TRANS_MERC)
WAVEFORMS = f"{DATA}/reference/gwangyang_pnplus/waveforms_100km"       # SAC, 100 Hz, counts
RTDD_CATALOG = f"{DATA}/inputs/rtdd_catalog"                           # station.csv, event_centroid_start.csv, phase.csv
DL_PICKS = f"{PROJECT}/runs/gwangyang/dlpicker/analysis/dl_picks_all.csv"   # scdlrtpicker picks of step 09 (read only)
DL_MODELS = ["phasenet_original", "phasenet_instance", "eqtransformer_stead", "phasenet_stead"]
DL_CONTROL_RELOC = f"{PROJECT}/runs/gwangyang/dlpicker/reloc/control_phasenet_plus/relocated-event.csv"
NLL_BIN = f"{PROJECT}/software/NonLinLoc/bin"

# --- velocity models (layer tops in km, speeds in km/s) ---
KIM1983_TOPS = [-5.0, 15.0, 32.0]        # top layer extended up to -5 km, as in the grids
KIM1983_VP = [5.98, 6.38, 7.95]
KIM1983_VPVS = 1.73                      # HypoDD and the NonLinLoc grids
HINV_KIM1983_VS = [3.40, 3.79, 4.58]     # HYPOINVERSE's own kim1983 S model (kim1983 Gwangyang.prt, crust model 2)
KIM2011_TOPS = [-5.0, 7.29, 20.7, 31.3]  # kim2011 as listed in the kim2011 Gwangyang.prt (crust models 1 and 2)
KIM2011_VP = [5.63, 6.17, 6.58, 7.77]
KIM2011_VS = [3.40, 3.60, 3.70, 4.45]
NEAR_STATION_LAYER_KM = (-5.0, 5.0)      # explanations (viii), (x): lower Vp/Vs only above 5 km depth
SOURCE_LAYER_KM = (10.0, 15.0)           # explanations (ix), (xi): lower Vp/Vs only from 10 to 15 km depth
VPVS_SCAN = (1.50, 1.73, 0.005)          # Vp/Vs values tried in (viii) to (xi): start, stop, step
DEPTH_SCAN_KM = (2.0, 30.0, 0.05)        # explanation (iv-b): trial depths (start, stop, step)
DEPTH_SHIFT_SCAN_KM = (-12.0, 12.0, 0.05)    # explanation (iv-a): common depth shifts tried
JOINT_DZ_SCAN_KM = (-3.0, 1.0, 0.25)     # explanations (x), (xi): common depth shifts tried together with the layer Vp/Vs

# --- picks and statistics ---
OUTLIER_ABS_RES_S = 1.0       # gross mis-pick: |(pick - HypoDD origin) - grid travel time| > 1.0 s
N_BOOT = 2000                 # bootstrap samples everywhere (stations resampled with replacement)
SEED = 620                    # random seed of all bootstraps
MIN_PAIRS_PER_EVENT = 3       # Figure D: no median for an event with fewer S-P pairs
STATION_MIN_PAIRS = 3         # station medians (Figure C c and their spread): stations with at least 3 pairs
RUNMED_HALF_WIDTH_KM = 5.0    # running medians against distance: 10 km wide windows ...
RUNMED_STEP_KM = 1.0          # ... every 1 km ...
RUNMED_MIN_N = 8              # ... with at least 8 pairs ...
RUNMED_MIN_STATIONS = 3       # ... from at least 3 stations (the 95% band resamples the stations of a window)
RUNMED_TP_HALF_WIDTH_S = 1.0  # Figure E1 b: 2 s wide windows of P travel time ...
RUNMED_TP_STEP_S = 0.5        # ... every 0.5 s (same minimum counts)
DIST_BINS_KM = [0, 30, 60, 70, 101]  # distance bins; 60 and 70 km set around the model's direct/head-wave crossover (66 km)
NEAR_KM = (12.0, 30.0)        # explanation table: residuals of the pairs within 12 km and within 30 km
EVENT_TERM_ITER = 20          # median-polish iterations (event and station terms)

# --- waveforms ---
BAND_HZ = (5.0, 20.0)         # band-pass
FILTER_CORNERS = 4
FILTER_ZEROPHASE = False      # causal (one pass): cannot move energy ahead of an onset
TAPER_FRACTION = 0.05
EXAMPLE_EVENT = "20210827220322"     # the ML 2.2 event (Figure A and the first record section)
FIG_A_P_WINDOW_S = (-0.6, 1.0)       # Figure A: window around the hand P pick ...
FIG_A_S_WINDOW_S = (-1.2, 1.0)       # ... and around the model S time (the same spans in both rows)
STACK_WINDOW_S = (-2.0, 2.0)         # Figure B: right panels and stack, around the model S time
AIC_WINDOW_S = (-1.0, 1.0)           # AIC onset: search window around the model S time (hand P pick + model S-P) ...
AIC_MIN_AFTER_P = 0.55               # ... starting no earlier than hand P pick + 0.55 x model S-P (keeps the P wave out)
AIC_EDGE_SAMPLES = 10                # the AIC change point may not lie within 10 samples (0.1 s) of the window ends

# --- NonLinLoc (identical for every run) ---
NLLOC = dict(trans_lat=35.0000, trans_lon=127.7286, time_root=f"{NLL_TIME_DIR}/kim1983",
             oct_init=(10, 10, 10), oct_min_node_km=0.01, oct_max_nodes=20000, oct_num_scatter=5000,
             grid_n=(61, 61, 61), grid_orig=(-15.0, -15.0, -1.0), grid_d=(0.5, 0.5, 0.5),
             method="GAU_ANALYTIC", gau_sigma_s=0.1, gau_corr_len_km=0.0, gau2=None,
             qual2err=(0.1, 0.5, 1.0, 2.0, 99999.9))
NLLOC_PICK_ERR_S = {"P": 0.05, "S": 0.10}   # Gaussian pick errors written into the NLLOC_OBS files
NLLOC_MIN_PICKS = 8                         # hand picks are used for Figure F1 if every event has >= 8 P and >= 8 S
NEAR_NETWORK_KM = 35.0                      # Figures F1, F2, second row: only stations within this epicentral distance
INTERFACE_DEPTH_KM = 15.0                   # kim1983 layer boundary
INTERFACE_TOLS_KM = (0.02, 0.1, 0.2)        # a NonLinLoc depth this close to the boundary counts as 'at the boundary'
INTERFACE_FLAG_KM = 0.1                     # Figure F1 marks solutions within 0.1 km of the boundary
DEPTH_SLICE_KM = (11.0, 17.5, 0.05)         # Figure F2: trial depths of the misfit slices (start, stop, step)

# --- pyrtdd controls (section 8) ---
DD_STATIC_RANGE_S = (0.1, 0.5)   # each station's S picks shifted by its own random amount in this range ...
DD_STATIC_SEED = 3               # ... drawn with this seed (the same shift in every event)
DD_ONE_EVENT = 3                 # only this event's S picks shifted (by the same constant as everywhere else)
"""
exec(PARAM_CELL, PAR)

# =====================================================================================================
md(r"""
# Gwangyang: the S-P times are shorter than the kim1983 model predicts

**The claim checked here.** In the Gwangyang benchmark (11 KMA events from 2021-07 to 2026-02, KMA magnitude
$\mathit{M}_{\mathrm{L}}$ 1.1-2.2, a cluster about 100 m across at about 13.9 km depth near 35.00 N 127.73 E,
54 KS stations within 100 km), the S-P times of the reference picks seem to be about 0.27 s shorter than the
velocity model predicts, by about the same amount in every event, while Vp/Vs = 1.727 fits the data. If so, this
should not matter for double-difference relocation, but it should bias absolute locations that use S picks.

This notebook checks the claim with independent kinds of picks (the user's own hand picks, the PhaseNet+ reference
picks and, when their picks exist for all events, the four deep-learning models of the scdlrtpicker plugin), shows it
on the waveforms and with an automatic onset detector that uses no pick at all, tests simple explanations, and
measures the consequences for absolute and for double-difference locations. Section 9 gives a verdict on each part
of the claim.

**Terms used throughout, in plain words**

- *Pick*: the time at which a seismologist (a *hand pick*) or a computer program marks the arrival of a wave at a
  station.
- *P and S waves*: the P wave (compressional) is faster and arrives first; the S wave (shear) is slower and arrives
  later.
- *S-P time*: how long after the P wave the S wave arrives at a station (S pick minus P pick). Both waves leave the
  source at the same moment, so the unknown origin time of the earthquake cancels: the S-P time depends only on where
  the source and the station are and on the wave speeds in between. It grows with distance, roughly as
  (distance traveled) × (1/Vs − 1/Vp).
- *P travel time*: P pick minus origin time, i.e. how long the P wave took to travel from the source to the station.
- *Vp/Vs*: the P-wave speed divided by the S-wave speed. If Vp/Vs is the same everywhere, the S wave takes exactly
  Vp/Vs times as long as the P wave, so S-P = (Vp/Vs − 1) × (P travel time); for Vp/Vs = 1.73 that is
  0.73 × (P travel time).
- *Velocity model kim1983*: three flat layers with tops at 0, 15 and 32 km and P speeds of 5.98, 6.38 and
  7.95 km/s; S speed = P speed / 1.73. HypoDD used it, and the NonLinLoc travel-time grids of this project hold
  exactly this model, with the real station elevations.
- *Head wave*: in a layered model, the wave that goes down to the faster rock below 15 km, travels along its top
  and comes back up. Beyond about 66 km from these sources it arrives before the *direct wave* (the wave that goes
  straight from the source to the station).
- *Model S-P*: the S-P time that a velocity model predicts at a station for a given hypocenter.
- *Offset*: observed S-P minus model S-P. A negative offset means that the S wave comes sooner after the P wave
  than the model says.
- *Hypocenter*: the point inside the Earth where the earthquake starts; *origin time*: when it starts.
- *Absolute location* (HYPOINVERSE, NonLinLoc) finds one event's hypocenter and origin time from that event's own
  arrival times. *Double-difference relocation* (HypoDD, rtDD/pyrtdd) finds where events are relative to each
  other, from differences of travel times between pairs of events at the same station.
- *95% interval (CI)*: the range that contains the true value with 95% confidence. Here it always comes from a
  bootstrap, i.e. from repeating the calculation [[N_BOOT]] times on data resampled with replacement. We resample
  whole stations (all picks of a station together), because the picks of one station share its path and its site,
  so they are not independent of each other.

**Contents**

0. Parameters
1. Data assembly: the time reference of the hand picks, all picks, hypocenters, model S-P, the outlier rule, and how
   much the model S-P depends on our choices
2. Figure A: one near and one distant station of the $\mathit{M}_{\mathrm{L}}$ 2.2 event
3. Figure B: record sections of two events, aligned on each station's own P pick; Figure B3: S onsets found without
   any pick
4. Figure C: S-P against distance for all events
5. Figure D: the offset event by event, for every picker; event terms
6. Figure E1: the Wadati diagram; Figure E2: which simple explanation is needed
7. Figures F1 and F2: the consequence for absolute locations (NonLinLoc)
8. Figure G: double-difference relocation (pyrtdd), with controls
9. Comprehensive summary: verdict on each part of the claim, key numbers, take-home messages, caveats
""")

md(r"""
## 0. Parameters

Every setting of this notebook is in the next cell: input files, velocity models, the outlier rule, bootstrap
counts, the filter, the onset detector, and the NonLinLoc and pyrtdd settings. Nothing further down changes them.
""")

code(PARAM_CELL)

code(r"""
# imports, Helvetica, versions, colors and labels
import os
import sys
import glob
import json
import shutil
import importlib
import textwrap
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from IPython.display import display, Markdown
from scipy.stats import kruskal
import obspy
from obspy import UTCDateTime

sys.path.insert(0, LIB)
import nbfont
import sp_offset as so
importlib.reload(so)
import pyrtdd.hdd as hdd

hdd.Logger.setLevel(hdd.Logger.Level.warning)
FONT_FAMILY = nbfont.use_helvetica(verbose=True)
print("resolved font family:", FONT_FAMILY, "| font file matplotlib uses for text:",
      matplotlib.font_manager.findfont(matplotlib.font_manager.FontProperties(family=["sans-serif"])))
plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 8,
                     "xtick.labelsize": 8, "ytick.labelsize": 8, "figure.dpi": 100,
                     "mathtext.cal": "Helvetica:italic"})   # unused calligraphic slot; avoids a 'cursive' font lookup
os.makedirs(WORK, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)
pd.set_option("display.width", 230)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 90)

ML = r"$\mathit{M}_{\mathrm{L}}$"
# picker colors (Figures A-D only); the model is always vermilion
COL = {"hand": "#000000", "phasenet_plus": "#0072B2", "model": "#D55E00",
       "dl_phasenet_original": "#E69F00", "dl_phasenet_instance": "#56B4E9",
       "dl_eqtransformer_stead": "#009E73", "dl_phasenet_stead": "#CC79A7"}
LABEL = {"hand": "Hand picks", "phasenet_plus": "PhaseNet+",
         "dl_phasenet_original": "PhaseNet (original weights)", "dl_phasenet_instance": "PhaseNet (INSTANCE weights)",
         "dl_eqtransformer_stead": "EQTransformer (STEAD weights)", "dl_phasenet_stead": "PhaseNet (STEAD weights)"}
MARK = {"hand": "o", "phasenet_plus": "^", "dl_phasenet_original": "s", "dl_phasenet_instance": "D",
        "dl_eqtransformer_stead": "v", "dl_phasenet_stead": "P"}
NUMWORD = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
           9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def nw(n):
    return NUMWORD.get(int(n), str(int(n)))


print("versions: numpy", np.__version__, "| pandas", pd.__version__, "| obspy", obspy.__version__,
      "| matplotlib", matplotlib.__version__)
""")

# =====================================================================================================
md(r"""
## 1. Data assembly

### 1.1 The time reference of the hand-pick tables

The user's hand-pick tables (`manual_vs_phasenet/<event>_manual_phasenet_pick_table.csv`, made on 2026-04-22 by the
notebook `10.Compare_manual_ML_picks.ipynb` on server B) store every pick as *seconds after a reference time*: the SAC
header values `a` (P) and `t0` (S) of the vertical-component files. The reference time itself is not in the
tables. It is the reference time (the `nz*` header fields) of the SAC files the values were read from:

- columns `Manual_P`, `Manual_S`: `Gwangyang_sequence/manual_picks/<event>/*Z.sac` on server B;
- columns `PhaseNet_P`, `PhaseNet_S`: `Gwangyang_sequence/waveforms_100km/<event>/*Z.sac` on server B. These are the
  SeisBench PhaseNet picks of 2026-04-22, **not** the PhaseNet+ reference picks, which were made later
  (2026-05-28).

**A trap.** The local waveform copy (`reference/gwangyang_pnplus/waveforms_100km/`) was re-referenced on
2026-05-28 to the origin times of a later HYPOINVERSE run, so its reference time is not the one the tables were
read with. We therefore establish the reference time in two independent ways:

1. **SAC headers.** 16 SAC files were copied read-only from server B: the vertical-component file of station GWYB of
   every event from `manual_picks`, three more files of the $\mathit{M}_{\mathrm{L}}$ 2.2 event (GWYB N and E,
   BAU Z, KWJ2 Z), and one file from server B's `waveforms_100km`. Their `nz*` fields give the reference time, and
   their `a`/`t0` values must equal the table values.
2. **Absolute PhaseNet times.** The absolute times of the tables' PhaseNet column are in server B's
   `picks/<event>_picks.csv` (written 2026-04-22 09:50, copied read-only). Absolute time minus table value is
   the reference time, and it must be the same for every pick of an event.

The provenance of the copies (sources and md5 sums) is in `reference_supplement/PROVENANCE.md`.
""")

code(r"""
# 1.1 route 1: the SAC headers of the copied files (header picks must equal the table values)
EVENT_IDS = sorted(f[:14] for f in os.listdir(HAND_TABLE_DIR) if f.endswith("_manual_phasenet_pick_table.csv"))
SPOT = so.spotcheck_table(SPOTCHECK_DIR, HAND_TABLE_DIR)
worst_us = float(np.nanmax(np.r_[SPOT.abs_diff_P_us.to_numpy(), SPOT.abs_diff_S_us.to_numpy()]))
for ev, g in SPOT.groupby("kma_id"):
    assert g.sac_reference_utc.nunique() == 1, f"{ev}: the copied files disagree on the reference time"
assert worst_us < 1.0, "a SAC header pick differs from the table value"
SPOT_EXACT = int(((SPOT.abs_diff_P_us.fillna(0) < 1.0) & (SPOT.abs_diff_S_us.fillna(0) < 1.0)).sum())
print(f"{len(EVENT_IDS)} hand-pick tables; {len(SPOT)} SAC files from server B: every header pick equals the table value "
      f"(largest difference {worst_us:.4f} microseconds)")
display(SPOT[["source_folder", "kma_id", "station", "channel", "sac_reference_utc", "sac_a_s", "table_P_s",
              "sac_t0_s", "table_S_s"]].rename(columns={
    "source_folder": "Folder on server B", "kma_id": "Event", "station": "Station", "channel": "Channel",
    "sac_reference_utc": "SAC reference time", "sac_a_s": "Header a (s)", "table_P_s": "Table P (s)",
    "sac_t0_s": "Header t0 (s)", "table_S_s": "Table S (s)"}))
REF_TS = {ev: so.sac_reference_time(f"{SPOTCHECK_DIR}/manual_picks/{ev}/{ev}.KS.GWYB.HHZ.sac").timestamp
          for ev in EVENT_IDS}
""")

code(r"""
# 1.1 route 2: absolute times of the tables' PhaseNet column minus the table values; and what the local copy would give
MLREF = so.reference_from_ml_picks(HAND_TABLE_DIR, ML_PICKS_DIR, EVENT_IDS).set_index("kma_id")
PNP_RAW = pd.read_csv(PNPLUS_PICKS, dtype={"kma_id": str})
rows = []
for ev in EVENT_IDS:
    local_ref = so.sac_reference_time(sorted(glob.glob(f"{WAVEFORMS}/{ev}/{ev}.KS.*.sac"))[0]).timestamp
    tab = pd.read_csv(f"{HAND_TABLE_DIR}/{ev}_manual_phasenet_pick_table.csv").set_index("Station")
    d = []
    for r in PNP_RAW[PNP_RAW.kma_id == ev].itertuples():
        if r.station in tab.index and np.isfinite(tab.loc[r.station, "PhaseNet_" + r.phase]):
            d.append(UTCDateTime(r.time).timestamp - (local_ref + tab.loc[r.station, "PhaseNet_" + r.phase]))
    d = np.array(d)
    rows.append({"Event": ev,
                 "Reference time (route 1, SAC header)": UTCDateTime(REF_TS[ev]).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                 "Picks used by route 2": int(MLREF.loc[ev, "n_matched"]),
                 "Route 2 minus route 1 (µs)": round((MLREF.loc[ev, "ref_ts"] - REF_TS[ev]) * 1e6, 1),
                 "Route 2 spread (µs)": round(float(MLREF.loc[ev, "spread_us"]), 1),
                 "Local copy reference": UTCDateTime(local_ref).strftime("%H:%M:%S.%f")[:-3],
                 "Local minus true (ms)": round((local_ref - REF_TS[ev]) * 1e3, 1),
                 "PhaseNet+ minus table PhaseNet on the local reference, median (ms)": round(np.median(d) * 1e3, 1),
                 "Same, interquartile range (ms)": round((np.percentile(d, 75) - np.percentile(d, 25)) * 1e3, 1)})
REFT = pd.DataFrame(rows)
assert (REFT["Route 2 minus route 1 (µs)"].abs() < 5).all(), "the two routes disagree"
REFT.to_csv(f"{WORK}/hand_pick_reference_times.csv", index=False)
display(REFT)
print(f"Routes 1 and 2 agree within {REFT['Route 2 minus route 1 (µs)'].abs().max():.1f} µs in all {len(REFT)} events "
      f"(route 2 spreads of up to {REFT['Route 2 spread (µs)'].max():.0f} µs are the float32 rounding of SAC header values).")
print(f"With the reference time of the local, re-referenced waveform copy every hand pick would come out "
      f"{REFT['Local minus true (ms)'].min():.0f} to {REFT['Local minus true (ms)'].max():.0f} ms too late; and the tables' "
      f"PhaseNet column is not PhaseNet+ (interquartile ranges of {REFT['Same, interquartile range (ms)'].min():.0f}-"
      f"{REFT['Same, interquartile range (ms)'].max():.0f} ms), so that route cannot give the reference time.")
""")

code(r"""
# 1.1 the tidy hand-pick table in absolute UTC: absolute time = SAC reference time + table value
SENSOR = pd.read_csv(STATION_SENSORS).set_index("Code").Sensor.to_dict()
HAND = so.build_manual_picks_utc(HAND_TABLE_DIR, REF_TS, SENSOR)
HAND.to_csv(HAND_PICKS_UTC, index=False)
print(f"written {HAND_PICKS_UTC}")
print(f"{len(HAND)} hand picks: {(HAND.phase == 'P').sum()} P and {(HAND.phase == 'S').sum()} S, "
      f"{HAND.kma_id.nunique()} events, {HAND.station.nunique()} stations")
display(HAND.head(4))
""")

md(r"""
### 1.2 Picks, hypocenters and the model S-P of every station

- **Hypocenters**: the HypoDD dt.cc relocations of the reference run (`hypodd_dtcc.csv`), with the origin times
  of column `origin_time_pha_datum` (the origins the HypoDD travel times were computed from).
- **Model travel times**: the NonLinLoc kim1983 grids, read through `pyrtdd.hdd.NLLGrid` (the reader scrtdd
  uses), from each event's own hypocenter to each station at its real elevation.
- **Picks**: the hand picks (the UTC table above); PhaseNet+ (`picks_phasenet_plus.csv`, the PhaseNet+ times
  before HYPOINVERSE cut them to 0.01 s); and the scdlrtpicker models whose picks exist for every event. For the
  deep-learning pickers we take, as the relocation test of step 09 did, the picks inside the event window
  (origin − 5 s to + 60 s) and, per event, station and phase, the most confident one.
- **Gross-outlier rule** (one simple rule for every picker): a pick is dropped if its travel-time residual,
  |(pick time − HypoDD origin time) − grid travel time|, is larger than [[OUTLIER_ABS_RES_S]] s. The kept picks
  and the excluded ones are described below the table (range of the kept residuals, largest kept residual, range
  of the excluded ones). The S-P table further below also gives the median offset without this exclusion, which
  shows that the rule does not drive the result. A station enters the S-P analysis of an event only if both its P
  and its S pick survive.
""")

code(r"""
# 1.2 events, stations and picks; grid travel times from each event's own HypoDD hypocenter; the outlier rule
EV = so.load_events(HYPODD_DTCC, EVENT_ID_MAP).set_index("kma_id")
EV["n"] = EV.rtdd_id.astype(int)
HINV = pd.read_csv(HYPOINVERSE, dtype={"kma_id": str}).set_index("kma_id")
STA = pd.read_csv(STATIONS).set_index("Code")
STA["sensor"] = STA.index.map(SENSOR)
CENTROID = (float(EV.centroid_lat.iloc[0]), float(EV.centroid_lon.iloc[0]), float(EV.centroid_depth_km.iloc[0]))
print(f"{len(EV)} events; HypoDD dt.cc centroid {CENTROID[0]:.6f} N, {CENTROID[1]:.6f} E, {CENTROID[2]:.3f} km; "
      f"{len(STA)} stations")

dl_file = DL_PICKS if os.path.exists(DL_PICKS) else None
if dl_file is None:
    print(f"!! The DL-picker picks were not found ({DL_PICKS}); the notebook continues without them.")
PK, DL_STATUS = so.load_picks(HAND_PICKS_UTC, PNPLUS_PICKS, dl_file, DL_MODELS)
DL_AVAILABLE = [m for m in DL_MODELS if DL_STATUS.get(m, 0) == len(EV)]
for m in DL_MODELS:
    if m not in DL_AVAILABLE:
        print(f"!! DL model {m}: picks for {DL_STATUS.get(m, 0)} of {len(EV)} events, so it is left out")
print("DL models used:", ", ".join(DL_AVAILABLE) if DL_AVAILABLE else "none")
SOURCES = ["hand", "phasenet_plus"] + ["dl_" + m for m in DL_AVAILABLE]
PK = PK[PK.source.isin(SOURCES)].reset_index(drop=True)

TTT = hdd.NLLGrid(gridPath=NLL_TIME_DIR, gridModel="kim1983", maxSearchDistance=0.1)
GT = {(k, s): so.grid_times(TTT, e.latitude, e.longitude, e.depth_km, STA.loc[s]) for k, e in EV.iterrows() for s in STA.index}
DIST = {(k, s): so.epi_dist_km(e.latitude, e.longitude, STA.loc[s, "Latitude"], STA.loc[s, "Longitude"])
        for k, e in EV.iterrows() for s in STA.index}
PK["dist_km"] = [DIST[(k, s)] for k, s in zip(PK.kma_id, PK.station)]
PK["t_obs"] = PK.ts - PK.kma_id.map(EV.origin_ts)
PK["t_grid"] = [GT[(k, s)][0 if p == "P" else 1] for k, s, p in zip(PK.kma_id, PK.station, PK.phase)]
PK["res"] = PK.t_obs - PK.t_grid
PK["outlier"] = PK.res.abs() > OUTLIER_ABS_RES_S
rows = []
for src in SOURCES:
    q = PK[PK.source == src]
    row = {"Picks": LABEL[src]}
    for ph in ("P", "S"):
        a = q[q.phase == ph]
        row[f"{ph} picks"] = len(a)
        row[f"{ph} excluded"] = int(a.outlier.sum())
        row[f"Median {ph} residual of kept picks (s)"] = round(float(a[~a.outlier].res.median()), 3)
    rows.append(row)
OUTL = pd.DataFrame(rows).set_index("Picks")
display(OUTL)
print(f"Outlier rule: |residual| > {OUTLIER_ABS_RES_S} s; {int(PK.outlier.sum())} of {len(PK)} picks excluded in all.")
for src in SOURCES:
    q = PK[PK.source == src]
    kept, out = q[~q.outlier].res, q[q.outlier].res
    txt = f"excluded |residual| {out.abs().min():.2f}-{out.abs().max():.2f} s" if len(out) else "nothing excluded"
    print(f"  {LABEL[src]}: kept picks 5-95% residual range {kept.quantile(0.05):+.2f} to {kept.quantile(0.95):+.2f} s, "
          f"largest |residual| kept {kept.abs().max():.2f} s; {txt}")
""")

code(r"""
# 1.2 S-P pairs: one per picker, event and station with both a P and an S pick
rows = []
for (src, k, sta), g in PK.groupby(["source", "kma_id", "station"]):
    p = g[g.phase == "P"]
    s = g[g.phase == "S"]
    if len(p) != 1 or len(s) != 1:
        continue
    tp, ts = GT[(k, sta)]
    rows.append(dict(source=src, kma_id=k, station=sta, sensor=STA.loc[sta, "sensor"], dist_km=DIST[(k, sta)],
                     p_ts=float(p.ts.iloc[0]), s_ts=float(s.ts.iloc[0]), tp_obs=float(p.t_obs.iloc[0]),
                     tp_grid=tp, ts_grid=ts, excluded=bool(p.outlier.iloc[0] or s.outlier.iloc[0])))
ALLSP = pd.DataFrame(rows)
ALLSP["sp_obs"] = ALLSP.s_ts - ALLSP.p_ts
ALLSP["sp_model"] = ALLSP.ts_grid - ALLSP.tp_grid
ALLSP["offset"] = ALLSP.sp_obs - ALLSP.sp_model
SP = ALLSP[~ALLSP.excluded].reset_index(drop=True)
SP.to_csv(f"{WORK}/sp_pairs.csv", index=False)

RNG = np.random.default_rng(SEED)
rows = []
for src in SOURCES:
    d = SP[SP.source == src]
    a = ALLSP[ALLSP.source == src]
    med, lo, hi = so.cluster_bootstrap_median(d.offset, d.station, N_BOOT, RNG)
    rows.append({"Picks": LABEL[src], "S-P pairs": len(a), "Excluded (gross outlier)": int(a.excluded.sum()),
                 "Pairs used": len(d), "Events": d.kma_id.nunique(), "Stations": d.station.nunique(),
                 "Median offset (s)": med, "95% CI low (s)": lo, "95% CI high (s)": hi,
                 "Lower quartile (s)": d.offset.quantile(0.25), "Upper quartile (s)": d.offset.quantile(0.75),
                 "Median without the exclusion (s)": a.offset.median()})
OFFS = pd.DataFrame(rows).set_index("Picks")
display(OFFS.round(3))
HAND_MED = float(OFFS.loc["Hand picks", "Median offset (s)"])
HAND_CI = (float(OFFS.loc["Hand picks", "95% CI low (s)"]), float(OFFS.loc["Hand picks", "95% CI high (s)"]))
S_SHIFT = -HAND_MED   # the constant used in sections 7 and 8 (computed, not typed in)
print(f"Median offset of the hand picks: {HAND_MED:+.3f} s (95% CI {HAND_CI[0]:+.3f} to {HAND_CI[1]:+.3f} s; "
      f"{N_BOOT} bootstrap samples, stations resampled). Sections 7 and 8 shift S picks by +{S_SHIFT:.3f} s.")
""")

code(r"""
# 1.2 hand picks against the PhaseNet+ picks of the same event, station and phase
h = PK[(PK.source == "hand") & ~PK.outlier][["kma_id", "station", "phase", "ts"]]
p = PK[(PK.source == "phasenet_plus") & ~PK.outlier][["kma_id", "station", "phase", "ts"]]
m = h.merge(p, on=["kma_id", "station", "phase"], suffixes=("_hand", "_pnp"))
m["dt"] = m.ts_hand - m.ts_pnp
spm = SP[SP.source == "hand"].merge(SP[SP.source == "phasenet_plus"], on=["kma_id", "station"], suffixes=("_hand", "_pnp"))
DSP = spm.sp_obs_hand - spm.sp_obs_pnp
rows = []
for name, x in (("P pick", m[m.phase == "P"].dt), ("S pick", m[m.phase == "S"].dt), ("S-P time", DSP)):
    rows.append({"Hand minus PhaseNet+": name, "N": len(x), "Median (s)": round(float(x.median()), 3),
                 "Lower quartile (s)": round(float(x.quantile(0.25)), 3), "Upper quartile (s)": round(float(x.quantile(0.75)), 3),
                 "Within ±0.05 s": f"{(x.abs() <= 0.05).mean():.0%}"})
HVP = pd.DataFrame(rows).set_index("Hand minus PhaseNet+")
display(HVP)
PICK_NOISE_SP = float(1.4826 * np.median(np.abs(DSP - DSP.median())) / np.sqrt(2))
TABS = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{HAND_TABLE_DIR}/*_manual_phasenet_pick_table.csv"))])
print(f"For comparison, hand minus the tables' own 'PhaseNet' column (SeisBench PhaseNet of 2026-04-22, not PhaseNet+): "
      f"P {np.nanmedian(TABS.Manual_P - TABS.PhaseNet_P):+.3f} s (N {int((TABS.Manual_P - TABS.PhaseNet_P).notna().sum())}), "
      f"S {np.nanmedian(TABS.Manual_S - TABS.PhaseNet_S):+.3f} s (N {int((TABS.Manual_S - TABS.PhaseNet_S).notna().sum())})")
print(f"Hand vs PhaseNet+ consistency of the S-P times (1.4826 x MAD / sqrt 2): {PICK_NOISE_SP:.3f} s. Both pickers mark "
      f"the same onset, so their errors are correlated: this is only a lower bound on the picking error of one picker.")
""")

md(r"""
### 1.3 How much does the model S-P depend on our choices?

The model S-P of a station depends on the assumed hypocenter and velocity model. Besides the main choice (kim1983
grids from each event's own HypoDD hypocenter) we recompute it

- (a) from the cluster centroid, one point for all events;
- (b) from a P-only NonLinLoc location of each event (hand P picks, all stations, the settings of section 7): a
  hypocenter that uses no S pick at all (its depths are used again in section 6);
- (c) with the other Korean model, kim2011, as HYPOINVERSE used it (its own P and S layers), by an exact 1-D
  calculation;
- (d) with all stations at sea level (as HYPOINVERSE and HypoDD had them), by the same 1-D calculation;

and, for reference, (e) with kim1983 P speeds but HYPOINVERSE's own kim1983 S model, and (f) the exact 1-D
calculation of the grid model itself (a check of the grids). The exact 1-D calculation (fastest of the direct ray
and the head waves) is copied verbatim from `install/02_validate_nll_grids.py`, where it was checked against a
brute-force minimization.
""")

code(r"""
# 1.3 (b) P-only NonLinLoc locations (hand picks, all stations), then the model S-P under every variant
def nll_picks(source, kma_id, max_dist_km, phases):
    q = PK[(PK.source == source) & (PK.kma_id == kma_id) & ~PK.outlier & (PK.dist_km <= max_dist_km) & PK.phase.isin(phases)]
    return q.sort_values("ts")


def run_nll_set(source, network, max_dist_km, run, phases, s_shift):
    out = []
    for k in EV.index:
        q = nll_picks(source, k, max_dist_km, phases)
        run_dir = f"{WORK}/nlloc/{source}_{network}/{k}/{run}"
        if os.path.isdir(run_dir):
            shutil.rmtree(run_dir)
        res, ph = so.run_nlloc(NLL_BIN, run_dir, q, NLLOC, s_shift=s_shift, p_err=NLLOC_PICK_ERR_S["P"], s_err=NLLOC_PICK_ERR_S["S"])
        assert res["nphs"] == len(q), (k, run, res["nphs"], len(q))
        ot_sig = so.nlloc_ot_sigma(res, ph, q, TTT, STA, NLLOC_PICK_ERR_S["P"], NLLOC_PICK_ERR_S["S"], NLLOC["gau_sigma_s"])
        out.append(dict(source=source, network=network, run=run, kma_id=k, n_P=int((q.phase == "P").sum()),
                        n_S=int((q.phase == "S").sum()), lat=res["lat"], lon=res["lon"], depth_km=res["depth_km"],
                        origin_ts=res["origin"].timestamp, sig_x_km=res["sig_x_km"], sig_y_km=res["sig_y_km"],
                        sig_z_km=res["sig_z_km"], ot_sig_s=ot_sig, rms_s=res["rms_s"], gap_deg=res["gap_deg"],
                        status=res["status"]))
    return pd.DataFrame(out)


NLL_PONLY_HAND = run_nll_set("hand", "all", 1e9, "p_only", ["P"], 0.0)
P1 = NLL_PONLY_HAND.set_index("kma_id")
print("P-only NonLinLoc depths (hand picks, all stations), km:", ", ".join(f"{z:.2f}" for z in P1.depth_km))

T83, VP83 = np.array(KIM1983_TOPS), np.array(KIM1983_VP)
VS83 = VP83 / KIM1983_VPVS
zs = SP.kma_id.map(EV.depth_km).to_numpy()
zr = -SP.station.map(STA.Elevation_m).to_numpy() / 1000.0
cen = {s: so.grid_times(TTT, CENTROID[0], CENTROID[1], CENTROID[2], STA.loc[s]) for s in STA.index}
pon = {(k, s): so.grid_times(TTT, P1.loc[k, "lat"], P1.loc[k, "lon"], P1.loc[k, "depth_km"], STA.loc[s])
       for k in EV.index for s in STA.index}
SP["sp_centroid"] = [cen[s][1] - cen[s][0] for s in SP.station]
SP["sp_nll_p_only"] = [pon[(k, s)][1] - pon[(k, s)][0] for k, s in zip(SP.kma_id, SP.station)]
SP["sp_1d_kim2011"] = so.sp_1d(SP.dist_km, zs, zr, KIM2011_TOPS, KIM2011_VP, KIM2011_VS)
SP["sp_1d_sea_level"] = so.sp_1d(SP.dist_km, zs, np.zeros(len(SP)), T83, VP83, VS83)
SP["sp_1d_hinv_s"] = so.sp_1d(SP.dist_km, zs, zr, T83, VP83, HINV_KIM1983_VS)
SP["sp_1d_kim1983"] = so.sp_1d(SP.dist_km, zs, zr, T83, VP83, VS83)
SP.to_csv(f"{WORK}/sp_pairs.csv", index=False)
print(f"grid check: |grid S-P - exact 1-D S-P| <= {(SP.sp_model - SP.sp_1d_kim1983).abs().max() * 1000:.1f} ms for all {len(SP)} pairs")

VARIANTS = [("sp_model", "Main: kim1983 grids, each event's own HypoDD hypocenter"),
            ("sp_centroid", "(a) kim1983 grids, cluster centroid"),
            ("sp_nll_p_only", "(b) kim1983 grids, P-only NonLinLoc hypocenter"),
            ("sp_1d_kim2011", "(c) kim2011 (HYPOINVERSE's P and S models), 1-D"),
            ("sp_1d_sea_level", "(d) kim1983, stations at sea level, 1-D"),
            ("sp_1d_hinv_s", "(e) kim1983 P with HYPOINVERSE's S model, 1-D"),
            ("sp_1d_kim1983", "(f) kim1983, exact 1-D (check of the grids)")]
rows = []
for col, name in VARIANTS:
    row = {"Model S-P from": name}
    for src in ("hand", "phasenet_plus"):
        d = SP[SP.source == src]
        med, lo, hi = so.cluster_bootstrap_median(d.sp_obs - d[col], d.station, N_BOOT, RNG)
        row[f"{LABEL[src]}: median offset (s)"] = round(med, 3)
        row[f"{LABEL[src]}: 95% CI (s)"] = f"{lo:+.3f} to {hi:+.3f}"
    for src in SOURCES[2:]:
        d = SP[SP.source == src]
        row[f"{LABEL[src]} (s)"] = round(float((d.sp_obs - d[col]).median()), 3)
    rows.append(row)
ROBUST = pd.DataFrame(rows).set_index("Model S-P from")
display(ROBUST)
""")

# =====================================================================================================
md(r"""
## 2. Figure A: what the offset looks like on the waveforms of one station

The $\mathit{M}_{\mathrm{L}}$ 2.2 event of 2021-08-27 22:03 UTC, at the nearest and at the farthest station that has
both a hand P and a hand S pick (a fixed rule, so the two stations are not hand-chosen). Each row is one station;
the left panel shows the time around the P arrival and the right panel the time around the S arrival, both measured
from the hand P pick. The windows have the same length in both rows: [[FIG_A_P_WINDOW_S:0]] to +[[FIG_A_P_WINDOW_S:1]] s
around the hand P pick, and [[FIG_A_S_WINDOW_S:0]] to +[[FIG_A_S_WINDOW_S:1]] s around the model S time. The three
components (vertical Z, north N, east E) are band-passed [[BAND_HZ:0]]-[[BAND_HZ:1]] Hz, and each trace is scaled to
its own largest value in the panel.

The filter is causal (one pass). Such a filter can only delay an onset, by a few hundredths of a second, and never
shows energy before it, so it cannot make the S wave look early. Marks: hand P and hand S picks (black), the
PhaseNet+ S pick (blue), and the model S time = hand P pick + model S-P (vermilion).
""")

code(r"""
# Figure A: nearest and farthest station of the example event that have both hand picks
hA = SP[(SP.source == "hand") & (SP.kma_id == EXAMPLE_EVENT)].sort_values("dist_km")
PNP_A = PK[(PK.source == "phasenet_plus") & (PK.kma_id == EXAMPLE_EVENT) & ~PK.outlier].set_index(["station", "phase"]).ts
CHOSEN = [hA.iloc[0], hA.iloc[-1]]
print("Figure A stations (rule: nearest and farthest with both hand picks):",
      ", ".join(f"{c.station} ({c.sensor}, {c.dist_km:.1f} km)" for c in CHOSEN))
eA = EV.loc[EXAMPLE_EVENT]
fig, axes = plt.subplots(len(CHOSEN), 2, figsize=(9.2, 3.1 * len(CHOSEN)), gridspec_kw=dict(hspace=0.62, wspace=0.10))
for row, c in enumerate(CHOSEN):
    stf = so.bandpass(so.read_station(WAVEFORMS, EXAMPLE_EVENT, c.station), BAND_HZ[0], BAND_HZ[1],
                      FILTER_CORNERS, TAPER_FRACTION, FILTER_ZEROPHASE)
    t_pn_s = PNP_A.get((c.station, "S"), np.nan) - c.p_ts
    wins = [FIG_A_P_WINDOW_S, (c.sp_model + FIG_A_S_WINDOW_S[0], c.sp_model + FIG_A_S_WINDOW_S[1])]
    for col, (w0, w1) in enumerate(wins):
        ax = axes[row, col]
        for i, comp in enumerate(["Z", "N", "E"]):
            tr = so.component(stf, comp)
            t = tr.times("timestamp") - c.p_ts
            msk = (t >= w0) & (t <= w1)
            y = tr.data[msk].astype(float)
            ax.plot(t[msk], 2 - i + 0.42 * y / np.abs(y).max(), color="0.15", lw=0.6, zorder=2)
        if col == 0:
            ax.axvline(0.0, color=COL["hand"], lw=1.2, zorder=3)
        else:
            ax.axvline(c.sp_obs, color=COL["hand"], lw=1.2, ls="--", zorder=3)
            if np.isfinite(t_pn_s):
                ax.axvline(t_pn_s, color=COL["phasenet_plus"], lw=1.0, ls="-.", zorder=4)
            ax.axvline(c.sp_model, color=COL["model"], lw=1.2, zorder=3)
        ax.set_xlim(w0, w1)
        ax.set_ylim(-0.62, 2.62)
        ax.set_yticks([2, 1, 0])
        ax.set_yticklabels(["Z", "N", "E"])
        ax.set_xlabel("Time after the hand P pick (s)")
        where = "around the P arrival" if col == 0 else "around the S arrival"
        title = f"{c.station} ({c.sensor}), {c.dist_km:.1f} km: {where}"
        if col == 1:
            title += f"\nObserved S-P {c.sp_obs:.2f} s, model S-P {c.sp_model:.2f} s, difference {c.offset:+.2f} s"
        ax.set_title(title, loc="left")
handles = [Line2D([], [], color=COL["hand"], lw=1.2), Line2D([], [], color=COL["hand"], lw=1.2, ls="--"),
           Line2D([], [], color=COL["phasenet_plus"], lw=1.0, ls="-."), Line2D([], [], color=COL["model"], lw=1.2)]
labels = ["Hand P pick", "Hand S pick", "PhaseNet+ S pick", "Model S time (hand P pick + model S-P)"]
leg = so.legend_above(fig, axes, handles, labels, ncol=4)
so.text_above(fig, [leg] + list(axes.ravel()),
              f"Event {int(eA.n)}, {UTCDateTime(eA.origin_ts).strftime('%Y-%m-%d %H:%M')} UTC, {ML} {eA.ml:.1f}; "
              f"{BAND_HZ[0]:g}-{BAND_HZ[1]:g} Hz causal band-pass; each trace scaled to its own maximum in the panel",
              fontsize=9.5)
FIGS = {}
FIGS["A"] = so.save_fig(fig, FIG_DIR, "05_A_single_station_traces")
plt.show()
""")

md(r"""
## 3. Figure B: record sections

Every station of an event, sorted by distance (nearest at the bottom). Each trace is the *horizontal vector
amplitude* √(N² + E²) of the [[BAND_HZ:0]]-[[BAND_HZ:1]] Hz causal-filtered north and east components: S waves are
strongest on the horizontal components, and this combination does not depend on how the sensors are oriented. (The
orientation metadata of these stations are nominal and not verified, so we do not rotate.) Each trace is scaled to
its own largest value between 0.5 s before the P pick and 2 s after the model S time.

- Left: aligned on each station's own P pick (the hand pick; where a station has no hand P pick, its PhaseNet+ P
  pick, marked with *). Short ticks just above each trace mark the picks and the model, so that they do not hide the
  onsets: hand S pick (black), PhaseNet+ S pick (blue), model S time (vermilion; joined by a dotted line).
- Right: the same traces re-aligned so that the model S time is at zero. If the model were right, the S onsets and
  the S picks would line up at zero; instead they line up to the left of it, near the all-event median offset
  (dashed). The thin vertical lines are drawn behind the traces.
- Top right, *stack*: at every moment, the median of all the scaled traces of the event, aligned on the model S
  time. It shows where the S energy of the event as a whole starts, without looking at any S pick.

Events: the $\mathit{M}_{\mathrm{L}}$ 2.2 event, and the 2026 event with the most hand S-P pairs.
""")

code(r"""
# Figure B: record sections (horizontal vector amplitude), aligned on each station's own P pick, with a stack
NH = SP[SP.source == "hand"].groupby("kma_id").size()
EV_2026 = max((k for k in NH.index if k.startswith("2026")), key=lambda k: NH[k])
RECORD_EVENTS = [EXAMPLE_EVENT, EV_2026]
print("record-section events:", RECORD_EVENTS)
TRACE_H, TICK_LO, TICK_HI = 0.64, 0.68, 0.99     # trace height and the span of the pick ticks within each row (row height 1)
TAU = np.round(np.arange(STACK_WINDOW_S[0], STACK_WINDOW_S[1] + 1e-9, 0.01), 4)
STACKS = {}
for fig_no, k in enumerate(RECORD_EVENTS, start=1):
    e = EV.loc[k]
    hp = PK[(PK.kma_id == k) & (PK.source == "hand") & ~PK.outlier].set_index(["station", "phase"]).ts
    pp = PK[(PK.kma_id == k) & (PK.source == "phasenet_plus") & ~PK.outlier].set_index(["station", "phase"]).ts
    rows, no_p = [], []
    for sta in STA.index:
        if not glob.glob(f"{WAVEFORMS}/{k}/{k}.KS.{sta}.*.sac"):
            continue
        p_h, p_p = hp.get((sta, "P"), np.nan), pp.get((sta, "P"), np.nan)
        if not np.isfinite(p_h) and not np.isfinite(p_p):
            no_p.append(sta)
            continue
        tp, ts = GT[(k, sta)]
        rows.append(dict(station=sta, dist=DIST[(k, sta)], p_ref=p_h if np.isfinite(p_h) else p_p,
                         p_from_hand=bool(np.isfinite(p_h)), s_hand=hp.get((sta, "S"), np.nan),
                         s_pnp=pp.get((sta, "S"), np.nan), sp_model=ts - tp))
    R = pd.DataFrame(rows).sort_values("dist").reset_index(drop=True)
    n = len(R)
    xL = (-1.0, float(R.sp_model.max()) + 2.0)
    xR = STACK_WINDOW_S
    fig = plt.figure(figsize=(10.0, 0.2 * n + 2.3))
    gs = fig.add_gridspec(2, 2, width_ratios=[2.4, 1.0], height_ratios=[1.6, 0.2 * n], wspace=0.08, hspace=0.04)
    axL = fig.add_subplot(gs[1, 0])
    axR = fig.add_subplot(gs[1, 1], sharey=axL)
    axS = fig.add_subplot(gs[0, 1], sharex=axR)
    stack_rows, no_h = [], []
    for i, r in R.iterrows():
        stf = so.bandpass(so.read_station(WAVEFORMS, k, r.station), BAND_HZ[0], BAND_HZ[1], FILTER_CORNERS,
                          TAPER_FRACTION, FILTER_ZEROPHASE)
        t, a = so.horizontal_vector(stf)
        if t is None:
            no_h.append(r.station)
            axL.text(xL[0] + 0.1, i + 0.35, "No horizontal components", fontsize=6.5, va="center")
            continue
        tt = t - r.p_ref
        nm = (tt >= -0.5) & (tt <= r.sp_model + 2.0)
        a = a / a[nm].max()
        stack_rows.append(np.interp(TAU, tt - r.sp_model, a, left=np.nan, right=np.nan))
        for ax, shift, (x0, x1) in ((axL, 0.0, xL), (axR, r.sp_model, xR)):
            x = tt - shift
            msk = (x >= x0) & (x <= x1)
            y = TRACE_H * np.clip(a[msk], 0.0, 1.0)
            ax.fill_between(x[msk], i, i + y, color="0.78", lw=0, zorder=1)
            ax.plot(x[msk], i + y, color="0.3", lw=0.35, zorder=2)
            for val, colr, lw in ((r.s_hand - r.p_ref, COL["hand"], 2.0), (r.s_pnp - r.p_ref, COL["phasenet_plus"], 1.6),
                                  (r.sp_model, COL["model"], 1.6)):
                if np.isfinite(val) and x0 <= val - shift <= x1:
                    ax.plot([val - shift] * 2, [i + TICK_LO, i + TICK_HI], color=colr, lw=lw, zorder=4,
                            solid_capstyle="butt")
        if not np.isfinite(r.s_hand):
            axR.text(xR[1] + 0.08, i + 0.4, "No S pick" if not np.isfinite(r.s_pnp) else "No hand S pick",
                     ha="left", va="center", fontsize=6.5, color="0.25", clip_on=False)
    axL.plot(R.sp_model, R.index + 0.5 * (TICK_LO + TICK_HI), color=COL["model"], lw=0.6, ls=":", zorder=0.5)
    axR.axvline(0.0, color=COL["model"], lw=0.8, zorder=0.5)
    axR.axvline(HAND_MED, color="k", lw=0.8, ls="--", zorder=0.5)
    STK = np.nanmedian(np.vstack(stack_rows), axis=0)
    STACKS[k] = dict(tau=TAU, stack=STK, n=len(stack_rows))
    axS.fill_between(TAU, 0.0, STK, color="0.72", lw=0, zorder=1)
    axS.plot(TAU, STK, color="0.2", lw=0.7, zorder=2)
    axS.axvline(0.0, color=COL["model"], lw=0.8, zorder=0.5)
    axS.axvline(HAND_MED, color="k", lw=0.8, ls="--", zorder=0.5)
    axS.set_ylim(0.0, 1.15 * float(np.nanmax(STK)))
    axS.set_yticks([])
    axS.set_ylabel("Stack")
    axS.tick_params(labelbottom=False)
    axS.set_title(f"Stack: median of the {len(stack_rows)} traces", loc="left")
    axL.set_yticks(R.index + 0.35)
    axL.set_yticklabels([f"{s}{'' if fh else '*'}  {d:.0f} km" for s, fh, d in zip(R.station, R.p_from_hand, R.dist)], fontsize=6.5)
    axR.tick_params(labelleft=False)
    axL.set_ylim(-0.3, n + 0.1)
    axL.set_xlim(*xL)
    axR.set_xlim(*xR)
    axL.set_xlabel("Time after the station's P pick (s)")
    axR.set_xlabel("Time after the model S time (s)")
    when = UTCDateTime(e.origin_ts).strftime("%Y-%m-%d %H:%M")
    axL.set_title(f"Event {int(e.n)}, {when} UTC, {ML} {e.ml:.1f}: aligned on each station's own P pick", loc="left")
    handles = [Line2D([], [], color=COL["hand"], lw=2.0), Line2D([], [], color=COL["phasenet_plus"], lw=1.6),
               Line2D([], [], color=COL["model"], lw=1.6), Line2D([], [], color="k", lw=0.8, ls="--")]
    labels = ["Hand S pick", "PhaseNet+ S pick", "Model S time (P pick + model S-P)",
              f"All-event median offset, hand picks ({HAND_MED:+.2f} s)"]
    so.legend_above(fig, [axL, axR, axS], handles, labels, ncol=4)
    note = (f"Traces: horizontal vector amplitude √(N² + E²) of the {BAND_HZ[0]:g}-{BAND_HZ[1]:g} Hz causal band-passed "
            f"north and east components, each scaled to its own maximum between 0.5 s before the P pick and 2 s after the "
            f"model S time. Ticks above each trace: hand S pick (black), PhaseNet+ S pick (blue), model S time (vermilion).")
    note += (" * Aligned on the PhaseNet+ P pick (no hand P pick)." if (~R.p_from_hand).any()
             else " All traces are aligned on hand P picks.")
    note += (" Not shown (no P pick at all): " + ", ".join(no_p) + ".") if no_p else ""
    so.text_below(fig, [axL, axR], textwrap.fill(note, 175), fontsize=7)
    FIGS[f"B{fig_no}"] = so.save_fig(fig, FIG_DIR, f"05_B{fig_no}_record_section_{k}")
    plt.show()
    print(f"event {k}: {n} traces ({int((~R.p_from_hand).sum())} aligned on PhaseNet+ P), "
          f"{int(R.s_hand.notna().sum())} hand S picks; stations without any P pick: {len(no_p)}; "
          f"without horizontal components: {len(no_h)}; stack of {len(stack_rows)} traces")
""")

md(r"""
### 3.1 Figure B3: S onsets found without any pick

Hand picks and PhaseNet+ agree closely (section 1.2), so both could share a habit of marking the S wave early. We
therefore also let a simple automatic method find the S onset without looking at any S pick: the *AIC onset*
(Akaike information criterion; Maeda, 1985), the moment at which the horizontal signal changes most clearly from
one level of variability to another. For every hand-pick S-P pair it is searched on the same
[[BAND_HZ:0]]-[[BAND_HZ:1]] Hz causal-filtered north and east components, in a window from [[AIC_WINDOW_S:0]] s to
+[[AIC_WINDOW_S:1]] s around the model S time (hand P pick + model S-P), which never starts earlier than
hand P pick + [[AIC_MIN_AFTER_P]] × model S-P (so that the P wave itself is left out). The onset may not lie within
[[AIC_EDGE_SAMPLES]] samples of the window ends. The window is centered on the model, not on any pick, so a model
that was right would give onsets around zero.
""")

code(r"""
# 3.1 pick-independent S onsets: the AIC change point of the horizontal components near the model S time
rows = []
for r in SP[SP.source == "hand"].itertuples():
    stf = so.bandpass(so.read_station(WAVEFORMS, r.kma_id, r.station), BAND_HZ[0], BAND_HZ[1], FILTER_CORNERS,
                      TAPER_FRACTION, FILTER_ZEROPHASE)
    t, nn, ee = so.horizontal_components(stf)
    if t is None:
        continue
    s_model = r.p_ts + r.sp_model
    w0 = max(r.p_ts + AIC_MIN_AFTER_P * r.sp_model, s_model + AIC_WINDOW_S[0])
    msk = (t >= w0) & (t <= s_model + AIC_WINDOW_S[1])
    on = so.aic_onset(t[msk], np.column_stack([nn[msk], ee[msk]]), edge=AIC_EDGE_SAMPLES)
    rows.append(dict(kma_id=r.kma_id, station=r.station, dist_km=r.dist_km, window_start_s=w0 - s_model,
                     aic_minus_model_s=on - s_model, hand_s_minus_model_s=r.s_ts - s_model, aic_minus_hand_s_s=on - r.s_ts))
AIC = pd.DataFrame(rows)
AIC.to_csv(f"{WORK}/aic_onsets_hand.csv", index=False)
med, lo, hi = so.cluster_bootstrap_median(AIC.aic_minus_model_s, AIC.station, N_BOOT, RNG)
AIC_ALL = dict(med=med, lo=lo, hi=hi, n=len(AIC), before=float((AIC.aic_minus_model_s < 0).mean()),
               minus_hand=float(AIC.aic_minus_hand_s_s.median()),
               minus_hand_q=(float(AIC.aic_minus_hand_s_s.quantile(0.25)), float(AIC.aic_minus_hand_s_s.quantile(0.75))))
rows = [{"Distance": "All distances", "Pairs": len(AIC), "Stations": AIC.station.nunique(),
         "AIC onset minus model S time, median (s)": round(med, 3), "95% CI (s)": f"{lo:+.3f} to {hi:+.3f}",
         "AIC onsets before the model S time": f"{AIC_ALL['before']:.0%}",
         "Hand S pick minus model S time, median (s)": round(float(AIC.hand_s_minus_model_s.median()), 3),
         "AIC onset minus hand S pick, median (s)": round(AIC_ALL["minus_hand"], 3)}]
for b, g in AIC.groupby(pd.cut(AIC.dist_km, DIST_BINS_KM, right=False), observed=True):
    m_, l_, h_ = so.cluster_bootstrap_median(g.aic_minus_model_s, g.station, N_BOOT, RNG)
    rows.append({"Distance": f"{b.left:g}-{b.right:g} km", "Pairs": len(g), "Stations": g.station.nunique(),
                 "AIC onset minus model S time, median (s)": round(m_, 3), "95% CI (s)": f"{l_:+.3f} to {h_:+.3f}",
                 "AIC onsets before the model S time": f"{(g.aic_minus_model_s < 0).mean():.0%}",
                 "Hand S pick minus model S time, median (s)": round(float(g.hand_s_minus_model_s.median()), 3),
                 "AIC onset minus hand S pick, median (s)": round(float(g.aic_minus_hand_s_s.median()), 3)})
AICT = pd.DataFrame(rows).set_index("Distance")
display(AICT)
print(f"AIC onsets (no pick used) lie {AIC_ALL['med']:+.3f} s from the model S time (median, 95% CI {lo:+.3f} to {hi:+.3f}); "
      f"{AIC_ALL['before']:.0%} of {AIC_ALL['n']} pairs before it. They lie {AIC_ALL['minus_hand']:+.3f} s from the hand S pick "
      f"(median; quartiles {AIC_ALL['minus_hand_q'][0]:+.3f} to {AIC_ALL['minus_hand_q'][1]:+.3f} s).")

fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.0, 3.6), gridspec_kw=dict(wspace=0.26))
edges = np.round(np.arange(AIC_WINDOW_S[0], AIC_WINDOW_S[1] + 1e-9, 0.04), 4)
a1.hist(AIC.aic_minus_model_s, bins=edges, color="0.72", edgecolor="0.45", lw=0.5, zorder=2)
a1.hist(AIC.hand_s_minus_model_s, bins=edges, histtype="step", color=COL["hand"], lw=1.3, zorder=3)
a1.axvline(0.0, color=COL["model"], lw=1.4, zorder=4)
a1.axvline(AIC_ALL["med"], color="0.35", lw=1.2, ls="--", zorder=4)
a1.axvline(float(AIC.hand_s_minus_model_s.median()), color=COL["hand"], lw=1.0, ls=":", zorder=4)
a1.set_xlim(*AIC_WINDOW_S)
a1.set_xlabel("Time relative to the model S time (s)")
a1.set_ylabel("Station-event pairs")
a1.set_title("(a) S onsets and hand S picks, relative to the model S time", loc="left")
lim = float(np.ceil(AIC.aic_minus_hand_s_s.abs().max() * 10.0) / 10.0)
edges2 = np.round(np.arange(-lim, lim + 1e-9, 0.02), 4)
a2.hist(AIC.aic_minus_hand_s_s, bins=edges2, color="0.72", edgecolor="0.45", lw=0.5, zorder=2)
a2.axvline(0.0, color=COL["hand"], lw=1.2, zorder=3)
a2.axvline(AIC_ALL["minus_hand"], color="0.35", lw=1.2, ls="--", zorder=3)
a2.set_xlim(-lim, lim)
a2.set_xlabel("AIC onset minus hand S pick (s)")
a2.set_ylabel("Station-event pairs")
a2.set_title("(b) AIC onset against the hand S pick", loc="left")
handles = [Patch(facecolor="0.72", edgecolor="0.45", lw=0.5), Patch(facecolor="none", edgecolor=COL["hand"], lw=1.3),
           Line2D([], [], color=COL["model"], lw=1.4), Line2D([], [], color=COL["hand"], lw=1.2),
           Line2D([], [], color="0.35", lw=1.2, ls="--"), Line2D([], [], color=COL["hand"], lw=1.0, ls=":")]
labels = ["AIC onsets (no pick used)", "Hand S picks (a)", "Model S time (zero in a)", "Hand S pick (zero in b)",
          f"Median of the AIC onsets ({AIC_ALL['med']:+.2f} s in a, {AIC_ALL['minus_hand']:+.2f} s in b)",
          f"Median of the hand S picks ({float(AIC.hand_s_minus_model_s.median()):+.2f} s, a)"]
so.legend_above(fig, [a1, a2], handles, labels, ncol=3)
FIGS["B3"] = so.save_fig(fig, FIG_DIR, "05_B3_aic_onsets")
plt.show()
""")

# =====================================================================================================
md(r"""
## 4. Figure C: S-P against distance, all events

- (a) Observed S-P times (hand picks: circles; PhaseNet+: triangles) and the kim1983 model curve (exact 1-D, at
  the centroid depth, station at the median station elevation). At this scale a difference of a few tenths of a
  second is hard to see, which is why (b) shows the difference itself.
- (b) Observed minus model S-P of every pair (model from the grids and each event's own hypocenter). Black line:
  running median of the hand picks in [[RUNMED_HALF_WIDTH_KM]] km on either side of each point, every
  [[RUNMED_STEP_KM]] km, drawn only where a window holds at least [[RUNMED_MIN_N]] pairs from at least
  [[RUNMED_MIN_STATIONS]] stations (hence the gaps); gray band: its 95% interval with the stations of the window
  resampled (as for every other interval here). Dashed blue line: the same running median for PhaseNet+. Also drawn:
  zero (the model), the overall median of the hand picks, and the distance at which the first-arriving wave changes
  from the direct wave to the head wave along the 15 km boundary (dotted; exact 1-D model, station at sea level).
- (c) The median offset of each station over all events (hand picks; stations with at least
  [[STATION_MIN_PAIRS]] pairs), by sensor: broadband (HH), accelerometer (HG), short period (EL); and the median
  offset of the hand picks in four distance ranges (thick segment, labeled with its value) with its 95% interval
  (gray box). The range edges 60 and 70 km were set around the model's direct/head-wave crossover, not chosen from
  the data.
""")

code(r"""
# Figure C: S-P against distance, with station-bootstrap running medians and distance-range medians
dH = SP[SP.source == "hand"]
dP = SP[SP.source == "phasenet_plus"]
ZR_MED = -float(STA.Elevation_m.median()) / 1000.0
XS = np.arange(1.0, 101.0, 0.5)
CURVE = so.sp_1d(XS, np.full(len(XS), CENTROID[2]), np.full(len(XS), ZR_MED), T83, VP83, VS83)
XOVER = so.crossover_distance(CENTROID[2], 0.0, T83, VP83)
XOVER_ELEV = so.crossover_distance(CENTROID[2], ZR_MED, T83, VP83)
print(f"crossover direct wave -> head wave at the centroid depth: {XOVER:.2f} km (station at sea level), "
      f"{XOVER_ELEV:.2f} km (station at the median elevation, {-ZR_MED * 1000:.0f} m)")
CENTERS = np.arange(5.0, 100.0 + 1e-9, RUNMED_STEP_KM)
RM_H = so.running_median(dH.dist_km, dH.offset, dH.station, CENTERS, RUNMED_HALF_WIDTH_KM, RUNMED_MIN_N,
                         RUNMED_MIN_STATIONS, N_BOOT, RNG)
RM_P = so.running_median(dP.dist_km, dP.offset, dP.station, CENTERS, RUNMED_HALF_WIDTH_KM, RUNMED_MIN_N,
                         RUNMED_MIN_STATIONS, N_BOOT, RNG)
STMED = dH.groupby("station").agg(dist_km=("dist_km", "median"), median_offset_s=("offset", "median"),
                                  n=("offset", "size"), sensor=("sensor", "first")).sort_values("dist_km")
STMED.to_csv(f"{WORK}/station_median_offsets_hand.csv")
STM = STMED[STMED.n >= STATION_MIN_PAIRS]
bins = pd.cut(SP.dist_km, DIST_BINS_KM, right=False)
rows = []
for src in ("hand", "phasenet_plus"):
    for b, g in SP[SP.source == src].groupby(bins[SP.source == src], observed=True):
        med, lo, hi = so.cluster_bootstrap_median(g.offset, g.station, N_BOOT, RNG)
        top = g.station.value_counts().head(3)
        rows.append({"Picks": LABEL[src], "Distance (km)": f"{b.left:g}-{b.right:g}", "left": float(b.left),
                     "right": float(b.right), "Pairs": len(g), "Stations": g.station.nunique(),
                     "Median offset (s)": med, "lo": lo, "hi": hi, "95% CI (s)": f"{lo:+.3f} to {hi:+.3f}",
                     "Median of station medians (s)": float(g.groupby("station").offset.median().median()),
                     "Stations with most pairs": ", ".join(f"{s} ({c})" for s, c in top.items()),
                     "Share of pairs from them": f"{top.sum() / len(g):.0%}"})
DBIN = pd.DataFrame(rows)
DBH = DBIN[DBIN.Picks == "Hand picks"].reset_index(drop=True)

fig = plt.figure(figsize=(8.0, 11.0))
gs = fig.add_gridspec(4, 1, height_ratios=[1.1, 1.35, 0.30, 0.9], hspace=0.06)
axa = fig.add_subplot(gs[0])
axb = fig.add_subplot(gs[1], sharex=axa)
axc = fig.add_subplot(gs[3], sharex=axa)
axa.tick_params(labelbottom=False)
axb.tick_params(labelbottom=False)
HMK = dict(ls="none", marker="o", ms=3.0, mfc="none", mec="0.3", mew=0.6, alpha=0.8)
PMK = dict(ls="none", marker="^", ms=3.2, mfc="none", mec=COL["phasenet_plus"], mew=0.6, alpha=0.6)
axa.plot(dP.dist_km, dP.sp_obs, zorder=2, **PMK)
axa.plot(dH.dist_km, dH.sp_obs, zorder=3, **HMK)
axa.plot(XS, CURVE, color=COL["model"], lw=1.5, zorder=4)
axa.set_ylabel("S-P time (s)")
axa.set_ylim(0, 13)
axa.text(0.015, 0.95, "(a)", transform=axa.transAxes, va="top")
axb.plot(dP.dist_km, dP.offset, zorder=2, **PMK)
axb.plot(dH.dist_km, dH.offset, zorder=2, **HMK)
axb.fill_between(RM_H.center_km, RM_H.lo, RM_H.hi, color="0.55", alpha=0.35, lw=0, zorder=3)
axb.plot(RM_H.center_km, RM_H["median"], color="k", lw=1.6, zorder=4)
axb.plot(RM_P.center_km, RM_P["median"], color=COL["phasenet_plus"], lw=1.2, ls="--", zorder=4)
axb.axhline(0.0, color=COL["model"], lw=1.4, zorder=3)
axb.axhline(HAND_MED, color="k", lw=1.0, ls="-.", zorder=3)
axb.set_ylabel("Observed minus model S-P (s)")
axb.set_ylim(-1.0, 0.45)
axb.text(0.015, 0.95, "(b)", transform=axb.transAxes, va="top")
for _, r in DBH.iterrows():
    axc.add_patch(Rectangle((r.left, r.lo), r.right - r.left, r.hi - r.lo, facecolor="0.90", edgecolor="0.35",
                            lw=0.8, ls=(0, (4, 2)), zorder=1))
    axc.plot([r.left, r.right], [r["Median offset (s)"]] * 2, color="k", lw=2.2, zorder=2, solid_capstyle="butt")
    axc.text(0.5 * (r.left + r.right), -0.70, f"{r['Median offset (s)']:+.2f} s", ha="center", va="center",
             fontsize=7.5, color="0.1", zorder=6)
SENS_MARK = {"HH": ("o", "0.15"), "HG": ("s", "white"), "EL": ("D", "#E69F00")}
for sen, (mk, fc) in SENS_MARK.items():
    q = STM[STM.sensor == sen]
    axc.plot(q.dist_km, q.median_offset_s, mk, ms=5.0, mfc=fc, mec="k", mew=0.9, zorder=4)
axc.axhline(0.0, color=COL["model"], lw=1.4, zorder=2)
axc.axhline(HAND_MED, color="k", lw=1.0, ls="-.", zorder=2)
axc.set_ylabel("Median offset (s)")
axc.set_xlabel("Epicentral distance (km)")
axc.set_ylim(-0.75, 0.15)
axc.text(0.015, 0.93, "(c)", transform=axc.transAxes, va="top")
for a_ in (axa, axb, axc):
    a_.axvline(XOVER, color="0.35", lw=1.0, ls=":", zorder=1)
axa.text(XOVER - 0.8, 12.6, "Direct wave first", ha="right", va="top", fontsize=7.5, color="0.25")
axa.text(XOVER + 0.8, 12.6, "Head wave first", ha="left", va="top", fontsize=7.5, color="0.25")
axa.set_xlim(0, 101)
so.legend_above(fig, [axc], [Line2D([], [], ls="none", marker=mk, mfc=fc, mec="k", mew=0.9, ms=5) for mk, fc in SENS_MARK.values()]
                + [(Patch(facecolor="0.90", edgecolor="0.35", lw=0.8, ls=(0, (4, 2))), Line2D([], [], color="k", lw=2.2))],
                [f"Station median, {s} sensor" for s in SENS_MARK] + ["Distance-range median and its 95% interval"], ncol=2)
handles = [Line2D([], [], **HMK), Line2D([], [], **PMK), Line2D([], [], color=COL["model"], lw=1.5),
           Line2D([], [], color="k", lw=1.6), Patch(color="0.55", alpha=0.35, lw=0),
           Line2D([], [], color=COL["phasenet_plus"], lw=1.2, ls="--"),
           Line2D([], [], color="k", lw=1.0, ls="-."), Line2D([], [], color="0.35", lw=1.0, ls=":")]
labels = ["Hand-pick S-P pairs", "PhaseNet+ S-P pairs", "Model kim1983 (the zero line in b and c)",
          "Running median, hand picks", "Its 95% band (stations resampled)", "Running median, PhaseNet+",
          f"Overall median, hand picks ({HAND_MED:+.2f} s)", "Direct/head-wave crossover"]
so.legend_above(fig, [axa], handles, labels, ncol=3)
FIGS["C"] = so.save_fig(fig, FIG_DIR, "05_C_sp_vs_distance")
plt.show()

show = DBIN.drop(columns=["left", "right", "lo", "hi"]).copy()
show["Median offset (s)"] = show["Median offset (s)"].round(3)
show["Median of station medians (s)"] = show["Median of station medians (s)"].round(3)
display(show)
STSPREAD = dict(lo=float(STM.median_offset_s.min()), hi=float(STM.median_offset_s.max()), sd=float(STM.median_offset_s.std()),
                n=len(STM))
print(f"station medians (hand picks, stations with >= {STATION_MIN_PAIRS} pairs): {STSPREAD['lo']:+.2f} to {STSPREAD['hi']:+.2f} s, "
      f"SD {STSPREAD['sd']:.2f} s over {STSPREAD['n']} stations")
xb = DBH[(DBH.left <= XOVER) & (DBH.right > XOVER)].iloc[0]
gx = dH[(dH.dist_km >= xb.left) & (dH.dist_km < xb.right)]
TOP3 = gx.station.value_counts().head(3).index.tolist()
ax3 = AIC[AIC.station.isin(TOP3) & (AIC.dist_km >= xb.left) & (AIC.dist_km < xb.right)]
XBIN = dict(label=xb["Distance (km)"], pairs=int(xb.Pairs), top3=TOP3, n_top3=int(gx.station.isin(TOP3).sum()),
            top3_meds=gx[gx.station.isin(TOP3)].groupby("station").offset.median(),
            med=float(xb["Median offset (s)"]), med_sta=float(xb["Median of station medians (s)"]),
            aic_minus_hand=float(ax3.aic_minus_hand_s_s.median()), aic_minus_model=float(ax3.aic_minus_model_s.median()))
print(f"The {XBIN['label']} km range (around the crossover at {XOVER:.0f} km): {XBIN['n_top3']} of its {XBIN['pairs']} pairs come "
      f"from {', '.join(TOP3)} (station medians " + ", ".join(f"{v:+.2f}" for v in XBIN["top3_meds"].to_numpy()) +
      f" s); the median of its station medians is {XBIN['med_sta']:+.3f} s against {XBIN['med']:+.3f} s for all its pairs. "
      f"At these stations the AIC onsets lie {XBIN['aic_minus_hand']:+.3f} s from the hand S picks and "
      f"{XBIN['aic_minus_model']:+.3f} s from the model S time (medians).")
""")

# =====================================================================================================
md(r"""
## 5. Figure D: the offset event by event, for every picker

For each event: the median offset over its stations, with a 95% interval from [[N_BOOT]] bootstrap samples (the
event's stations resampled with replacement; no value when an event has fewer than [[MIN_PAIRS_PER_EVENT]] pairs).
Events are in time order; the numbers 1-11 are used again in Figures F1 and G. The dashed line and the gray band
are the overall median of the hand picks and its 95% interval; zero (vermilion) is the model. The deep-learning
pickers are the scdlrtpicker models, named by their network and training data set.
""")

code(r"""
# Figure D: per-event median offsets with bootstrap intervals, every picker
EVL = EV.sort_values("origin_ts")
rows = []
for src in SOURCES:
    for k in EVL.index:
        x = SP[(SP.source == src) & (SP.kma_id == k)].offset.to_numpy()
        if len(x) < MIN_PAIRS_PER_EVENT:
            rows.append(dict(source=src, kma_id=k, n=len(x), median=np.nan, lo=np.nan, hi=np.nan))
            continue
        bs = np.median(RNG.choice(x, size=(N_BOOT, len(x)), replace=True), axis=1)
        rows.append(dict(source=src, kma_id=k, n=len(x), median=float(np.median(x)),
                         lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5))))
PEV = pd.DataFrame(rows)
PEV.to_csv(f"{WORK}/per_event_offsets.csv", index=False)

fig, ax = plt.subplots(figsize=(10.5, 4.4))
ax.axhspan(HAND_CI[0], HAND_CI[1], color="0.86", lw=0, zorder=0)
ax.axhline(HAND_MED, color="k", lw=1.0, ls="--", zorder=1)
ax.axhline(0.0, color=COL["model"], lw=1.4, zorder=1)
offs = np.linspace(-0.3, 0.3, len(SOURCES))
for j, src in enumerate(SOURCES):
    q = PEV[PEV.source == src].set_index("kma_id").loc[EVL.index]
    x = np.arange(len(EVL)) + offs[j]
    ax.errorbar(x, q["median"], yerr=[q["median"] - q.lo, q.hi - q["median"]], fmt=MARK[src], color=COL[src],
                mfc=COL[src] if src == "hand" else "white", mec=COL[src], ms=5, mew=1.0, elinewidth=0.9, capsize=2, zorder=3)
years = np.array([UTCDateTime(t).year for t in EVL.origin_ts])
for i in range(1, len(years)):
    if years[i] != years[i - 1]:
        ax.axvline(i - 0.5, color="0.5", lw=0.8, ls=":", zorder=1)
for yv in np.unique(years):
    idx = np.flatnonzero(years == yv)
    ax.text(0.5 * (idx.min() + idx.max()), 0.075, str(yv), ha="center", va="center", fontsize=8.5, color="0.3")
ax.set_xticks(np.arange(len(EVL)))
ax.set_xticklabels([f"{int(e.n)}\n{UTCDateTime(e.origin_ts).strftime('%Y-%m-%d')}\n{UTCDateTime(e.origin_ts).strftime('%H:%M')}\n{ML} {e.ml:.1f}"
                    for _, e in EVL.iterrows()], fontsize=7.5)
ylo = min(-0.6, float(np.nanmin(PEV.lo)) - 0.05)
ax.set_ylim(ylo, 0.1)
for i, k in enumerate(EVL.index):
    nh = int(PEV[(PEV.source == "hand") & (PEV.kma_id == k)].n.iloc[0])
    ax.text(i, ylo + 0.02, f"N = {nh}", ha="center", va="bottom", fontsize=7, color="0.25")
ax.set_xlim(-0.6, len(EVL) - 0.4)
ax.set_ylabel("Median observed minus model S-P (s)")
ax.set_xlabel("Event (number, date and time in UTC, KMA magnitude); N = hand-pick S-P pairs")
handles = [Line2D([], [], ls="none", marker=MARK[s], mfc=COL[s] if s == "hand" else "white", mec=COL[s], color=COL[s]) for s in SOURCES]
handles += [Line2D([], [], color="0.3", marker="|", ms=11, mew=1.0, ls="none"), Line2D([], [], color="k", lw=1.0, ls="--"),
            Patch(color="0.86", lw=0), Line2D([], [], color=COL["model"], lw=1.4)]
labels = [LABEL[s] for s in SOURCES] + ["Error bar: 95% interval (the event's stations resampled)",
                                        f"Overall median, hand picks ({HAND_MED:+.3f} s)", "95% interval of the overall median",
                                        "Model (zero offset)"]
so.legend_above(fig, ax, handles, labels, ncol=3)
FIGS["D"] = so.save_fig(fig, FIG_DIR, "05_D_offset_per_event")
plt.show()
tab = PEV.pivot(index="kma_id", columns="source", values="median").loc[EVL.index, SOURCES].rename(columns=LABEL)
tab.index = [f"{int(EV.loc[k, 'n'])}  {k}" for k in tab.index]
display(tab.round(3))
EVSPREAD = PEV[PEV.source == "hand"]["median"]
ALLPICK_EV = PEV["median"]
print(f"hand picks: per-event medians from {EVSPREAD.min():+.3f} to {EVSPREAD.max():+.3f} s "
      f"(standard deviation {EVSPREAD.std():.3f} s over {EVSPREAD.notna().sum()} events); all {len(SOURCES)} pickers: "
      f"{ALLPICK_EV.min():+.3f} to {ALLPICK_EV.max():+.3f} s")
""")

md(r"""
### 5.1 Event terms: how much do the events really differ?

Each event was recorded by a somewhat different set of stations, and the stations differ from each other
(Figure C c), so the per-event medians above mix event and station effects. An *event term* is how much one event's
offsets differ from the typical value after the station-to-station differences are removed. We get it by a
*median polish* ([[EVENT_TERM_ITER]] rounds of subtracting, in turn, each station's median and each event's median
of what is left). A Kruskal-Wallis test then asks whether the station-corrected offsets of all events could share
one median (a small p-value means that the events do differ).
""")

code(r"""
# 5.1 event terms (station terms removed) by median polish, and a test of equal event medians
rows, EVTERM = [], {}
for src in ("hand", "phasenet_plus"):
    d = SP[SP.source == src]
    mu, ev_t, st_t, res = so.median_polish(d.offset, d.kma_id, d.station, EVENT_TERM_ITER)
    corr = d.offset.to_numpy() - d.station.map(st_t).to_numpy()
    kw = kruskal(*[corr[d.kma_id.to_numpy() == k] for k in ev_t.index])
    EVTERM[src] = dict(mu=mu, ev=ev_t, st=st_t, kw_p=float(kw.pvalue), sd=float(ev_t.std()),
                       res_spread=float(1.4826 * np.median(np.abs(res - np.median(res)))))
    rows.append({"Picks": LABEL[src], "Overall value (s)": round(mu, 3), "Event terms, lowest (s)": round(float(ev_t.min()), 3),
                 "Event terms, highest (s)": round(float(ev_t.max()), 3), "Event terms, SD (s)": round(EVTERM[src]["sd"], 3),
                 "Kruskal-Wallis p (equal event medians)": f"{kw.pvalue:.1g}",
                 "Robust spread of what is left (s)": round(EVTERM[src]["res_spread"], 3)})
display(pd.DataFrame(rows).set_index("Picks"))
ET = pd.DataFrame({LABEL[s]: EVTERM[s]["ev"] for s in EVTERM}).loc[EVL.index]
ET.index = [f"{int(EV.loc[k, 'n'])}  {k}" for k in ET.index]
ET.to_csv(f"{WORK}/event_terms.csv")
display(ET.round(3))
""")

# =====================================================================================================
md(r"""
## 6. Figures E1 and E2: Vp/Vs, and which simple explanation is needed

### 6.1 Figure E1: the Wadati diagram

A *Wadati diagram* plots S-P against the P travel time. If the S wave always takes Vp/Vs times as long as the P
wave, the points fall on a straight line through the origin with slope Vp/Vs − 1. We fit one common slope and one
intercept per event. An error in an event's origin time shifts all of its P travel times by the same amount, and the
event's own intercept absorbs that shift: **the slope (and hence Vp/Vs) does not depend on the origin times, but the
intercepts do**. As a check that uses no origin time at all, we also fit S-P against the *model* P travel times.
The 95% intervals resample stations ([[N_BOOT]] samples).

Why the gap between the fitted line and the model line (the median intercept) is a little larger than the median
offset: the intercept is S-P minus slope × *observed* P travel time, while the offset is S-P minus 0.73 × *model*
P travel time. With a slope close to 0.73 the two differ by about 0.73 × (observed − model P travel time); the
numbers are printed below the table.
""")

code(r"""
# 6. Wadati fits: observed P travel times (slope origin-time free) and model P travel times (no origin time used)
rows, WAD, WADM = [], {}, {}
for src in ("hand", "phasenet_plus"):
    d = SP[SP.source == src]
    for xcol, store, xname in (("tp_obs", WAD, "observed P travel time"), ("tp_grid", WADM, "model P travel time")):
        m, ce, res = so.wadati_fit(d.sp_obs.to_numpy(), d[xcol].to_numpy(), d.kma_id.to_numpy())
        bs = so.wadati_bootstrap(d.sp_obs, d[xcol], d.kma_id, d.station, N_BOOT, RNG)
        per_ev = [1.0 + np.polyfit(g[xcol], g.sp_obs, 1)[0] for _, g in d.groupby("kma_id") if len(g) >= 5]
        ce = pd.Series(ce)
        store[src] = dict(slope=m, vpvs=1.0 + m, lo=1.0 + np.percentile(bs, 2.5), hi=1.0 + np.percentile(bs, 97.5),
                          intercepts=ce, per_event_median=float(np.median(per_ev)), rms=float(np.sqrt(np.mean(res ** 2))))
        rows.append({"Picks": LABEL[src], "Against": xname, "Pairs": len(d), "Vp/Vs (common slope + 1)": round(1.0 + m, 4),
                     "95% CI": f"{store[src]['lo']:.4f} to {store[src]['hi']:.4f}",
                     "Median of per-event Vp/Vs (events with >= 5 pairs)": round(store[src]["per_event_median"], 4),
                     "Per-event intercepts (s)": f"{ce.min():+.3f} to {ce.max():+.3f}", "Median intercept (s)": round(float(ce.median()), 3)})
display(pd.DataFrame(rows).set_index(["Picks", "Against"]))
k_model = KIM1983_VPVS - 1.0
P_RES_MED = float((dH.tp_obs - dH.tp_grid).median())
C_MED = float(WAD["hand"]["intercepts"].median())
print(f"Gap of the Wadati fit (median intercept, hand picks) {C_MED:+.3f} s vs the median offset {HAND_MED:+.3f} s: the hand P picks "
      f"come {P_RES_MED:+.3f} s (median) after the model P times, and {k_model:.2f} x {P_RES_MED:+.3f} = {k_model * P_RES_MED:+.3f} s, "
      f"which accounts for most of the difference ({C_MED - HAND_MED:+.3f} s).")
print(f"Against model P travel times (no origin time used): Vp/Vs {WADM['hand']['vpvs']:.4f} "
      f"(95% CI {WADM['hand']['lo']:.4f} to {WADM['hand']['hi']:.4f}), median intercept {WADM['hand']['intercepts'].median():+.3f} s.")
""")

code(r"""
# Figure E1: Wadati diagram, and what is left after removing the model's 0.73 x P travel time
d = SP[SP.source == "hand"]
W = WAD["hand"]
fig, (axa, axb) = plt.subplots(1, 2, figsize=(10.4, 4.6), gridspec_kw=dict(wspace=0.28))
xx = np.array([0.0, 17.5])
axa.plot(d.tp_obs, d.sp_obs, "o", ms=3.0, mfc="none", mec="0.25", mew=0.6, zorder=2)
axa.plot(xx, W["slope"] * xx + C_MED, color="k", lw=1.4, zorder=3)
axa.plot(xx, k_model * xx, color=COL["model"], lw=1.4, zorder=3)
axa.set_xlim(0, 17.5)
axa.set_ylim(0, 13)
axa.set_xlabel("P travel time (s)")
axa.set_ylabel("S-P time (s)")
axa.set_title(f"(a) Wadati diagram, hand picks: Vp/Vs {W['vpvs']:.3f} (95% CI {W['lo']:.3f}-{W['hi']:.3f})", loc="left")
ins = axa.inset_axes([0.56, 0.08, 0.41, 0.40])
msk = (d.tp_obs > 1.5) & (d.tp_obs < 6.5)
ins.plot(d.tp_obs[msk], d.sp_obs[msk], "o", ms=2.6, mfc="none", mec="0.25", mew=0.5)
xi = np.array([1.5, 6.5])
ins.plot(xi, W["slope"] * xi + C_MED, color="k", lw=1.2)
ins.plot(xi, k_model * xi, color=COL["model"], lw=1.2)
ins.set_xlim(1.5, 6.5)
ins.set_ylim(0.6, 4.9)
ins.tick_params(labelsize=6.5)
xa = 4.5
ya_fit, ya_mod = W["slope"] * xa + C_MED, k_model * xa
ins.annotate("", xy=(xa, ya_fit), xytext=(xa, ya_mod), arrowprops=dict(arrowstyle="|-|", lw=0.9, mutation_scale=2.5, shrinkA=0, shrinkB=0))
ins.annotate(f"Gap {C_MED:+.2f} s", xy=(xa + 0.05, 0.5 * (ya_fit + ya_mod)), xytext=(3.9, 1.45), ha="left", va="center", fontsize=7,
             arrowprops=dict(arrowstyle="-", lw=0.6, color="0.3", shrinkA=1, shrinkB=1))
axa.indicate_inset_zoom(ins, edgecolor="0.5")
y = d.sp_obs - k_model * d.tp_obs
axb.plot(d.tp_obs, y, "o", ms=3.0, mfc="none", mec="0.25", mew=0.6, alpha=0.8, zorder=2)
rmed = so.running_median(d.tp_obs, y, d.station, np.arange(1.0, 17.0, RUNMED_TP_STEP_S), RUNMED_TP_HALF_WIDTH_S,
                         RUNMED_MIN_N, RUNMED_MIN_STATIONS, N_BOOT, RNG)
axb.fill_between(rmed.center_km, rmed.lo, rmed.hi, color="0.55", alpha=0.35, lw=0, zorder=3)
axb.plot(rmed.center_km, rmed["median"], color="k", lw=1.6, zorder=4)
axb.axhline(0.0, color=COL["model"], lw=1.4, zorder=3)
axb.axhline(C_MED, color="k", lw=1.0, ls="--", zorder=3)
axb.set_xlim(0, 17.5)
axb.set_ylim(-1.1, 0.5)
axb.set_xlabel("P travel time (s)")
axb.set_ylabel(f"S-P minus {k_model:.2f} × P travel time (s)")
axb.set_title("(b) What is left after the model's Vp/Vs is removed", loc="left")
handles = [Line2D([], [], ls="none", marker="o", mfc="none", mec="0.25"), Line2D([], [], color="k", lw=1.4),
           Line2D([], [], color=COL["model"], lw=1.4), Line2D([], [], color="k", lw=1.0, ls="--"),
           Line2D([], [], color="k", lw=1.6), Patch(color="0.55", alpha=0.35, lw=0)]
labels = ["Hand-pick S-P pairs", "Fit: common slope, median intercept", f"Model: slope {k_model:.2f} through the origin",
          f"Median intercept ({C_MED:+.3f} s)", "Running median (2 s windows)", "Its 95% band (stations resampled)"]
so.legend_above(fig, [axa, axb], handles, labels, ncol=3)
FIGS["E1"] = so.save_fig(fig, FIG_DIR, "05_E1_wadati")
plt.show()
""")

md(r"""
### 6.2 Figure E2: which simple explanation is needed?

We compare simple explanations of the observed S-P times. Each one predicts an S-P time for every pair; what is
left over (observed minus predicted) is its *residual*. For each explanation we report

- the *RMS* (root-mean-square) of the residuals: one number for the overall misfit;
- the *trend*: how much the residual changes per 100 km of distance (zero if the explanation captures how the
  offset depends on distance);
- the median residual of the *nearest stations* (within [[NEAR_KM:0]] km and within [[NEAR_KM:1]] km). These
  stations are the sharpest test, because their paths are short and nearly vertical: an explanation that works
  through the length of the path (a lower Vp/Vs somewhere) shortens their S-P much less than at distant stations.

All intervals resample stations ([[N_BOOT]] samples), and **every fit is redone in each bootstrap sample**, so the
intervals include the uncertainty of the fitted values. "RMS minus (iii)" is computed within each bootstrap sample,
so its interval says whether an explanation fits measurably worse or better than a constant.

The explanations:

- (i) the model as it is;
- (ii) one uniform Vp/Vs, fitted: S-P = (Vp/Vs − 1) × model P travel time;
- (iii) Vp/Vs [[KIM1983_VPVS]] plus one constant, fitted;
- (iv) only the hypocenter depth changed, fitted: one shift for all events (iv-a; shifts from
  [[DEPTH_SHIFT_SCAN_KM:0]] to +[[DEPTH_SHIFT_SCAN_KM:1]] km in steps of [[DEPTH_SHIFT_SCAN_KM:2]] km), or a free
  depth per event (iv-b; [[DEPTH_SCAN_KM:0]] to [[DEPTH_SCAN_KM:1]] km in steps of [[DEPTH_SCAN_KM:2]] km);
- (v) a uniform Vp/Vs and a constant, both fitted (its trend is zero by construction);
- (vi) the kim2011 model as HYPOINVERSE used it (nothing fitted);
- (vii) kim1983 with HYPOINVERSE's own S model (nothing fitted);
- (viii) kim1983 with a lower Vp/Vs only near the stations (from [[NEAR_STATION_LAYER_KM:0]] to
  [[NEAR_STATION_LAYER_KM:1]] km depth), fitted;
- (ix) kim1983 with a lower Vp/Vs only in a layer around the source ([[SOURCE_LAYER_KM:0]]-[[SOURCE_LAYER_KM:1]] km
  depth), fitted;
- (x) and (xi): (viii) and (ix) with, in addition, one depth shift for all events (from [[JOINT_DZ_SCAN_KM:0]] to
  +[[JOINT_DZ_SCAN_KM:1]] km in steps of [[JOINT_DZ_SCAN_KM:2]] km). These test whether a source at a different
  depth than HypoDD puts it, combined with a lower Vp/Vs, can imitate a constant;
- and, for reference, one constant per station: the floor that no single 1-D explanation can go below, because it
  also absorbs everything that differs from station to station.

In (viii) to (xi) Vp/Vs is tried from [[VPVS_SCAN:0]] to [[VPVS_SCAN:1]] in steps of [[VPVS_SCAN:2]] and the P
speeds are unchanged. The scans use a vectorized version of the exact 1-D first-arrival calculation; the cell after
the tables checks it against the verbatim one for every pair.
""")

code(r"""
# 6.2 explanations: candidate residuals, fits for pair weights w, and the station bootstrap with refits
ZS_SCAN = np.round(np.arange(DEPTH_SCAN_KM[0], DEPTH_SCAN_KM[1] + 1e-9, DEPTH_SCAN_KM[2]), 4)
DZ_4A = np.round(np.arange(DEPTH_SHIFT_SCAN_KM[0], DEPTH_SHIFT_SCAN_KM[1] + 1e-9, DEPTH_SHIFT_SCAN_KM[2]), 4)
KS_SCAN = np.round(np.arange(VPVS_SCAN[0], VPVS_SCAN[1] + 1e-9, VPVS_SCAN[2]), 4)
DZ_JOINT = np.round(np.arange(JOINT_DZ_SCAN_KM[0], JOINT_DZ_SCAN_KM[1] + 1e-9, JOINT_DZ_SCAN_KM[2]), 4)
assert np.any(DZ_JOINT == 0.0), "the joint depth-shift scan must contain zero"
NAMES = {"i": "(i) kim1983 as it is", "ii": "(ii) one uniform Vp/Vs", "iii": f"(iii) Vp/Vs {KIM1983_VPVS:g} + one constant",
         "iva": "(iv-a) depth only, one shift", "ivb": "(iv-b) depth only, one depth per event",
         "v": "(v) uniform Vp/Vs + one constant", "vi": "(vi) kim2011 as HYPOINVERSE used it",
         "vii": "(vii) kim1983 with HYPOINVERSE's S model", "viii": "(viii) lower Vp/Vs near the stations",
         "ix": "(ix) lower Vp/Vs around the source", "x": "(x) as (viii), plus one depth shift",
         "xi": "(xi) as (ix), plus one depth shift", "ref": "Reference: one constant per station"}
NEAR_COL = f"med_lt_{NEAR_KM[-1]:g}"


def depth_matrix(d):
    # model S-P from the grids at every trial depth, at each event's own epicenter (pairs x depths)
    M = np.empty((len(d), len(ZS_SCAN)))
    for i, (k, s) in enumerate(zip(d.kma_id, d.station)):
        e, sta = EV.loc[k], STA.loc[s]
        for j, z in enumerate(ZS_SCAN):
            tp, ts = so.grid_times(TTT, e.latitude, e.longitude, z, sta)
            M[i, j] = ts - tp
    return M


def interp_depth(M, z):
    f = (np.asarray(z) - ZS_SCAN[0]) / DEPTH_SCAN_KM[2]
    j = np.clip(np.floor(f).astype(int), 0, len(ZS_SCAN) - 2)
    w = f - j
    r = np.arange(len(M))
    return M[r, j] * (1.0 - w) + M[r, j + 1] * w


def layer_model(z_top, z_bot):
    # kim1983 with one extra layer [z_top, z_bot] (P speeds unchanged); index of that layer
    tops = np.array(sorted(set(KIM1983_TOPS + [z_top, z_bot])))
    vp = np.array([VP83[np.searchsorted(T83, z, side="right") - 1] for z in tops])
    return tops, vp, int(np.flatnonzero(np.isclose(tops, z_top))[0])


def layer_matrix(d, z_top, z_bot):
    # residual S-P of every pair for every (common depth shift, Vp/Vs of the extra layer); columns dz-major
    tops, vp, kl = layer_model(z_top, z_bot)
    x, zs_ = d.dist_km.to_numpy(), d.kma_id.map(EV.depth_km).to_numpy()
    zr_ = -d.station.map(STA.Elevation_m).to_numpy() / 1000.0
    cols, pars = [], []
    for dz in DZ_JOINT:
        tp = so.first_arrival_vec(x, zs_ + dz, zr_, tops, vp)
        for kk in KS_SCAN:
            vs = vp / KIM1983_VPVS
            vs[kl] = vp[kl] / kk
            cols.append(d.sp_obs.to_numpy() - (so.first_arrival_vec(x, zs_ + dz, zr_, tops, vs) - tp))
            pars.append((float(dz), float(kk)))
    return np.column_stack(cols), pars


def explanation_setup(d):
    # everything that does not depend on the bootstrap weights
    o = d.sp_obs.to_numpy()
    S = dict(o=o, tpg=d.tp_grid.to_numpy(), off=d.offset.to_numpy(), dist=d.dist_km.to_numpy(),
             ev=pd.Categorical(d.kma_id).codes, station=d.station.to_numpy(), zev=d.kma_id.map(EV.depth_km).to_numpy(),
             n_sta=int(d.station.nunique()), n_ev=int(d.kma_id.nunique()))
    M = depth_matrix(d)
    S["R4a"] = np.column_stack([o - interp_depth(M, S["zev"] + dz) for dz in DZ_4A])
    S["R4b"] = o[:, None] - M
    for key, (z1, z2) in (("near", NEAR_STATION_LAYER_KM), ("source", SOURCE_LAYER_KM)):
        R, pars = layer_matrix(d, z1, z2)
        S["R_" + key], S["P_" + key] = R, pars
        S["j0_" + key] = np.array([j for j, (dz, kk) in enumerate(pars) if dz == 0.0])
    for key in ("R4a", "R4b", "R_near", "R_source"):
        S[key + "2"] = S[key] ** 2
    S["r_vi"] = o - d.sp_1d_kim2011.to_numpy()
    S["r_vii"] = o - d.sp_1d_hinv_s.to_numpy()
    S["r_ref"] = S["off"] - d.groupby("station").offset.transform("median").to_numpy()
    return S


def explanation_fit(S, w):
    # (free parameters, fitted values, residuals, parameters) of every explanation for pair weights w
    o, tpg, off = S["o"], S["tpg"], S["off"]
    out = {"i": (0, "none", off, None)}
    k1 = np.sum(w * o * tpg) / np.sum(w * tpg ** 2)
    out["ii"] = (1, f"Vp/Vs {1 + k1:.4f}", o - k1 * tpg, dict(vpvs=1 + k1))
    c3 = np.sum(w * off) / np.sum(w)
    out["iii"] = (1, f"constant {c3:+.3f} s", off - c3, dict(c=c3))
    j = so.best_column(S["R4a"], w)
    out["iva"] = (1, f"shift {DZ_4A[j]:+.2f} km (negative = shallower)", S["R4a"][:, j], dict(dz=DZ_4A[j]))
    r4, sh = np.empty(len(o)), []
    for e in np.unique(S["ev"]):
        ii = S["ev"] == e
        we = w[ii] if w[ii].sum() > 0 else np.ones(int(ii.sum()))
        jj = int(np.argmin(we @ S["R4b2"][ii]))
        r4[ii] = S["R4b"][ii, jj]
        sh.append(ZS_SCAN[jj] - S["zev"][ii][0])
    out["ivb"] = (S["n_ev"], f"shifts {min(sh):+.1f} to {max(sh):+.1f} km", r4, dict(shifts=sh))
    A = np.column_stack([tpg, np.ones(len(o))])
    sw = np.sqrt(w)
    c5 = np.linalg.lstsq(A * sw[:, None], o * sw, rcond=None)[0]
    out["v"] = (2, f"Vp/Vs {1 + c5[0]:.4f}, constant {c5[1]:+.3f} s", o - A @ c5, dict(vpvs=1 + c5[0], c=c5[1]))
    out["vi"] = (0, "none", S["r_vi"], None)
    out["vii"] = (0, "none", S["r_vii"], None)
    for key, rid, rid2, (z1, z2) in (("near", "viii", "x", NEAR_STATION_LAYER_KM), ("source", "ix", "xi", SOURCE_LAYER_KM)):
        where = f"above {z2:g} km" if key == "near" else f"at {z1:g}-{z2:g} km"
        j0 = S["j0_" + key]
        jb = int(j0[np.argmin(w @ S["R_" + key + "2"][:, j0])])
        out[rid] = (1, f"Vp/Vs {S['P_' + key][jb][1]:.3f} {where}", S["R_" + key][:, jb], dict(dz=0.0, vpvs=S["P_" + key][jb][1]))
        jb = int(np.argmin(w @ S["R_" + key + "2"]))
        dz, kk = S["P_" + key][jb]
        out[rid2] = (2, f"Vp/Vs {kk:.3f} {where}, depth shift {dz:+.2f} km", S["R_" + key][:, jb], dict(dz=dz, vpvs=kk))
    out["ref"] = (S["n_sta"], "station medians", S["r_ref"], None)
    return out


ORDER = ["i", "ii", "iii", "iva", "ivb", "v", "vi", "vii", "viii", "ix", "x", "xi", "ref"]


def explanation_table(d, S, n_boot, rng):
    w1 = np.ones(len(d))
    base = explanation_fit(S, w1)
    base = {k: base[k] for k in ORDER}
    st1 = {k: so.weighted_stats(v[2], w1, S["dist"], NEAR_KM) for k, v in base.items()}
    WB = so.station_bootstrap_weights(S["station"], n_boot, rng)
    BS = {k: [] for k in base}
    for w in WB:
        f = explanation_fit(S, w)
        for k in base:
            BS[k].append(so.weighted_stats(f[k][2], w, S["dist"], NEAR_KM))
    BS = {k: pd.DataFrame(v) for k, v in BS.items()}
    near = S["dist"] < NEAR_KM[-1]
    rows = []
    for k, (npar, fit, r, _) in base.items():
        b = BS[k]
        sm = pd.Series(r[near]).groupby(S["station"][near]).median()
        drms = b.rms - BS["iii"].rms
        rows.append({"key": k, "Explanation": NAMES[k], "Free parameters": npar, "Fitted values": fit,
                     "RMS": st1[k]["rms"], "RMS lo": b.rms.quantile(0.025), "RMS hi": b.rms.quantile(0.975),
                     "dRMS": st1[k]["rms"] - st1["iii"]["rms"], "dRMS lo": drms.quantile(0.025), "dRMS hi": drms.quantile(0.975),
                     "Trend": st1[k]["trend"], "Trend lo": b.trend.quantile(0.025), "Trend hi": b.trend.quantile(0.975),
                     "Near1": st1[k][f"med_lt_{NEAR_KM[0]:g}"], "Near": st1[k][NEAR_COL],
                     "Near lo": b[NEAR_COL].quantile(0.025), "Near hi": b[NEAR_COL].quantile(0.975),
                     "Far": st1[k][f"med_ge_{NEAR_KM[-1]:g}"], "Near stations negative": int((sm < 0).sum()), "Near stations": len(sm)})
    return pd.DataFrame(rows).set_index("key"), base, BS


def explanation_display(T):
    ci = lambda a, lo, hi, f: [f"{x:{f}} [{y:{f}}, {z:{f}}]" for x, y, z in zip(T[a], T[lo], T[hi])]
    out = pd.DataFrame({"Free parameters": T["Free parameters"], "Fitted values": T["Fitted values"],
                        "RMS (s) [95% CI]": ci("RMS", "RMS lo", "RMS hi", ".3f"),
                        "RMS minus (iii) (s) [95% CI]": ci("dRMS", "dRMS lo", "dRMS hi", "+.3f"),
                        "Trend (s per 100 km) [95% CI]": ci("Trend", "Trend lo", "Trend hi", "+.2f"),
                        f"Median residual within {NEAR_KM[0]:g} km (s)": T["Near1"].round(3),
                        f"Median residual within {NEAR_KM[1]:g} km (s) [95% CI]": ci("Near", "Near lo", "Near hi", "+.3f"),
                        f"Median residual beyond {NEAR_KM[1]:g} km (s)": T["Far"].round(3),
                        f"Stations within {NEAR_KM[1]:g} km with a negative median residual":
                            [f"{a} of {b}" for a, b in zip(T["Near stations negative"], T["Near stations"])]})
    out.index = T["Explanation"]
    return out


EXPL, EXPL_BASE, EXPL_BS, EXPL_SETUP = {}, {}, {}, {}
for src in ("hand", "phasenet_plus"):
    d = SP[SP.source == src].reset_index(drop=True)
    EXPL_SETUP[src] = explanation_setup(d)
    EXPL[src], EXPL_BASE[src], EXPL_BS[src] = explanation_table(d, EXPL_SETUP[src], N_BOOT, RNG)
    EXPL[src].to_csv(f"{WORK}/explanations_{src}.csv")
    print(f"--- {LABEL[src]} ({len(d)} S-P pairs, {d.station.nunique()} stations) ---")
    with pd.option_context("display.max_colwidth", 60):
        display(explanation_display(EXPL[src]))
""")

code(r"""
# 6.2 check: the vectorized first arrivals used in the scans against the verbatim first_arrival, for every pair
pairs = SP.drop_duplicates(["kma_id", "station"])
x_, zs_, zr_ = pairs.dist_km.to_numpy(), pairs.kma_id.map(EV.depth_km).to_numpy(), -pairs.station.map(STA.Elevation_m).to_numpy() / 1000.0
checks = [("kim1983 P", T83, VP83, 0.0), ("kim1983 S", T83, VS83, 0.0),
          ("kim2011 P", np.array(KIM2011_TOPS), np.array(KIM2011_VP), 0.0),
          ("kim2011 S", np.array(KIM2011_TOPS), np.array(KIM2011_VS), 0.0)]
for rid, (z1, z2) in (("x", NEAR_STATION_LAYER_KM), ("xi", SOURCE_LAYER_KM)):
    prm = EXPL_BASE["hand"][rid][3]
    tops, vp, kl = layer_model(z1, z2)
    vs = vp / KIM1983_VPVS
    vs[kl] = vp[kl] / prm["vpvs"]
    checks += [(f"{NAMES[rid]}, best fit, P", tops, vp, prm["dz"]), (f"{NAMES[rid]}, best fit, S", tops, vs, prm["dz"])]
rows = []
for name, tops, v, dz in checks:
    ref = np.array([so.first_arrival(a, z + dz, b, np.asarray(tops, float), np.asarray(v, float))[0] for a, z, b in zip(x_, zs_, zr_)])
    vec = so.first_arrival_vec(x_, zs_ + dz, zr_, tops, v)
    rows.append({"Model": name, "Depth shift (km)": dz, "Station-event pairs": len(x_),
                 "Largest |vectorized - verbatim| (µs)": float(np.max(np.abs(ref - vec)) * 1e6)})
VEC_CHECK = pd.DataFrame(rows)
display(VEC_CHECK)
assert VEC_CHECK["Largest |vectorized - verbatim| (µs)"].max() < 1.0, "the vectorized first arrivals differ from the verbatim ones"
""")

code(r"""
# Figure E2: which explanation is needed (hand picks)
T, BASE = EXPL["hand"], EXPL_BASE["hand"]
d = SP[SP.source == "hand"].reset_index(drop=True)
dist = d.dist_km.to_numpy()
ECOL = {"i": COL["model"], "ii": "#882255", "iii": "#332288", "ivb": "#999933", "x": "#44AA99"}
GRAY = ["vi", "viii", "ix", "xi"]
fig = plt.figure(figsize=(10.6, 10.4))
gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.3], hspace=0.30, wspace=0.10)
axa = fig.add_subplot(gs[0, :])
axr = [fig.add_subplot(gs[1, 0])]
axr += [fig.add_subplot(gs[1, j], sharey=axr[0]) for j in (1, 2)]
ends = []
for k in GRAY + list(ECOL):
    rm = so.running_median(dist, BASE[k][2], d.station, CENTERS, RUNMED_HALF_WIDTH_KM, RUNMED_MIN_N, RUNMED_MIN_STATIONS, 0, RNG)
    colored = k in ECOL
    axa.plot(rm.center_km, rm["median"], color=ECOL.get(k, "0.70"), lw=1.7 if colored else 0.9,
             ls="--" if k == "ivb" else "-", zorder=3 if colored else 2)
    if colored:
        ok = rm["median"].notna().to_numpy()
        ends.append([float(rm.center_km[ok].iloc[-1]), float(rm["median"][ok].iloc[-1]), k])
ends.sort(key=lambda t: t[1])
ys = [t[1] for t in ends]
for i in range(1, len(ys)):
    ys[i] = max(ys[i], ys[i - 1] + 0.08)
for (xe, y0, k), y_ in zip(ends, ys):
    r = T.loc[k]
    axa.annotate(f"{NAMES[k].split(' ')[0]}  {r['Trend']:+.2f} ({r['Trend lo']:+.2f} to {r['Trend hi']:+.2f})", xy=(xe, y0),
                 xytext=(103.0, y_), va="center", fontsize=7.5, color=ECOL[k], annotation_clip=False,
                 arrowprops=dict(arrowstyle="-", lw=0.5, color=ECOL[k], shrinkA=0, shrinkB=2))
axa.text(103.0, max(ys) + 0.10, "Trend, s per 100 km\n(95% interval)", fontsize=7.5, color="0.25", va="bottom")
axa.axhline(0.0, color="0.4", lw=0.8, zorder=1)
axa.axvline(XOVER, color="0.35", lw=1.0, ls=":", zorder=1)
axa.set_xlim(0, 101)
axa.set_ylim(-0.6, 0.6)
axa.set_xlabel("Epicentral distance (km)")
axa.set_ylabel("Running median of the residual (s)")
axa.set_title("(a) What each explanation leaves, against distance ((iv-a), (v), (vii) not drawn)", loc="left")
order = list(T.index)
yy = np.arange(len(order))[::-1]
panels = (("RMS", "RMS lo", "RMS hi", "RMS of the residuals (s)", "(b) Misfit", None),
          ("Trend", "Trend lo", "Trend hi", "Trend (s per 100 km)", "(c) Trend with distance", 0.0),
          ("Near", "Near lo", "Near hi", f"Median residual within {NEAR_KM[1]:g} km (s)", "(d) Nearest stations", 0.0))
for ax, (c, lo, hi, xl, ttl, ref) in zip(axr, panels):
    if ref is not None:
        ax.axvline(ref, color="0.5", lw=0.8, zorder=1)
    for yv, k in zip(yy, order):
        colr = ECOL.get(k, "0.35")
        ax.errorbar(T.loc[k, c], yv, xerr=[[T.loc[k, c] - T.loc[k, lo]], [T.loc[k, hi] - T.loc[k, c]]], fmt="o", color=colr,
                    mfc=colr, ms=4.5, elinewidth=1.1, capsize=2, zorder=3)
    ax.set_xlabel(xl)
    ax.set_title(ttl, loc="left")
    ax.set_ylim(-0.7, len(order) - 0.3)
axr[0].axvline(PICK_NOISE_SP, color="0.3", lw=0.9, ls=":", zorder=1)
axr[0].set_xlim(0, 1.12 * float(T["RMS hi"].max()))
axr[0].set_yticks(yy)
axr[0].set_yticklabels([NAMES[k] for k in order], fontsize=7.5)
for ax in axr[1:]:
    ax.tick_params(labelleft=False)
handles = [Line2D([], [], color=ECOL[k], lw=1.7, ls="--" if k == "ivb" else "-") for k in ECOL] + \
          [Line2D([], [], color="0.70", lw=0.9), Line2D([], [], color="0.35", marker="o", ms=4.5, ls="-", lw=1.1),
           Line2D([], [], color="0.3", lw=0.9, ls=":")]
labels = [NAMES[k] for k in ECOL] + ["(vi), (viii), (ix), (xi), in gray",
                                     "Panels b-d: value and 95% interval (stations resampled, fits redone)",
                                     "Hand vs PhaseNet+ consistency (lower bound on the picking error)"]
so.legend_above(fig, [axa] + axr, handles, labels, ncol=2)
FIGS["E2"] = so.save_fig(fig, FIG_DIR, "05_E2_explanations")
plt.show()
""")

code(r"""
# 6.2 reading the explanation table (hand picks; every number from the table above)
T = EXPL["hand"]
P1DZ = (P1.depth_km - EV.depth_km.loc[P1.index]).to_numpy()
PATH = ["vi", "viii", "ix"]
nn = [T.loc[k, "Near stations negative"] for k in PATH]
shf = EXPL_BASE["hand"]["ivb"][3]["shifts"]
txt = [
    f"- **Changing only the depth (iv) does not work.** Even with a free depth per event the RMS stays at "
    f"{T.loc['ivb', 'RMS']:.3f} s (the fit moves the sources by {min(shf):+.1f} to {max(shf):+.1f} km; negative = shallower), "
    f"and it leaves a strong trend with distance ({T.loc['ivb', 'Trend']:+.2f} s per 100 km): a shallower source shortens S-P "
    f"mainly at the nearby stations.",
    f"- **One uniform Vp/Vs (ii) is ruled out by the trend, not by the RMS.** Its RMS is {T.loc['ii', 'dRMS']:+.3f} s "
    f"(95% CI {T.loc['ii', 'dRMS lo']:+.3f} to {T.loc['ii', 'dRMS hi']:+.3f}) away from that of a constant (iii), a difference "
    f"the data do not resolve. But it leaves a residual that grows with distance ({T.loc['ii', 'Trend']:+.2f} s per 100 km, "
    f"95% CI {T.loc['ii', 'Trend lo']:+.2f} to {T.loc['ii', 'Trend hi']:+.2f}): a lower Vp/Vs shortens S-P in proportion to "
    f"the travel time, too little nearby and too much far away.",
    f"- **With the HypoDD depths, the nearest stations favor a shortening that does not grow with distance.** The "
    f"explanations that act along the path, (vi) kim2011, (viii) a lower Vp/Vs near the stations and (ix) a lower Vp/Vs "
    f"around the source, leave {min(T.loc[k, 'Near1'] for k in PATH):+.2f} to {max(T.loc[k, 'Near1'] for k in PATH):+.2f} s "
    f"within {NEAR_KM[0]:g} km and negative station medians at "
    + (f"{min(nn)}" if min(nn) == max(nn) else f"{min(nn)} to {max(nn)}") + f" of the {T.loc['vi', 'Near stations']} "
    f"stations within {NEAR_KM[1]:g} km; the pooled median within {NEAR_KM[1]:g} km is "
    + ", ".join(f"{T.loc[k, 'Near']:+.3f} s ({T.loc[k, 'Near lo']:+.3f} to {T.loc[k, 'Near hi']:+.3f}) for ({k})" for k in PATH)
    + f". A constant leaves {T.loc['iii', 'Near']:+.3f} s ({T.loc['iii', 'Near lo']:+.3f} to {T.loc['iii', 'Near hi']:+.3f}) "
    f"there, and (v) {T.loc['v', 'Near']:+.3f} s. Beyond {NEAR_KM[1]:g} km they all fit about equally well (RMS "
    f"{min(T.loc[k, 'RMS'] for k in PATH + ['iii']):.3f}-{max(T.loc[k, 'RMS'] for k in PATH + ['iii']):.3f} s overall).",
    f"- **That conclusion rests on the depth.** Explanation (x), a Vp/Vs of {EXPL_BASE['hand']['x'][3]['vpvs']:.3f} above "
    f"{NEAR_STATION_LAYER_KM[1]:g} km with all sources {abs(EXPL_BASE['hand']['x'][3]['dz']):.2f} km "
    f"{'shallower' if EXPL_BASE['hand']['x'][3]['dz'] < 0 else 'deeper'} than HypoDD puts them, fits as well as or better than "
    f"the constant, with one more free parameter (RMS {T.loc['x', 'RMS']:.3f} vs {T.loc['iii', 'RMS']:.3f} s; difference {T.loc['x', 'dRMS']:+.3f} s, 95% CI "
    f"{T.loc['x', 'dRMS lo']:+.3f} to {T.loc['x', 'dRMS hi']:+.3f}), the nearest stations included ({T.loc['x', 'Near1']:+.3f} s "
    f"within {NEAR_KM[0]:g} km, trend {T.loc['x', 'Trend']:+.2f} s per 100 km). (xi), the same with the lower Vp/Vs around "
    f"the source, needs a shift of {EXPL_BASE['hand']['xi'][3]['dz']:+.2f} km and still leaves {T.loc['xi', 'Near1']:+.3f} s "
    f"within {NEAR_KM[0]:g} km. The P picks alone (P-only NonLinLoc locations with the kim1983 P speeds, section 1.3) put "
    f"the sources {abs(P1DZ.mean()):.2f} ± {P1DZ.std(ddof=1) / np.sqrt(len(P1DZ)):.2f} km "
    f"{'deeper' if P1DZ.mean() > 0 else 'shallower'} than HypoDD (mean ± standard error over {len(P1DZ)} events), "
    f"{abs(P1DZ.mean() - EXPL_BASE['hand']['x'][3]['dz']) / (P1DZ.std(ddof=1) / np.sqrt(len(P1DZ))):.0f} standard errors away from "
    f"the {EXPL_BASE['hand']['x'][3]['dz']:+.2f} km that (x) needs; but those depths rest on the kim1983 P speeds, which are "
    f"themselves uncertain. **S-P times alone therefore cannot tell a distance-independent shortening (a picking convention "
    f"shared by hand and machine picks, or an effect very close to the source) from a shallower source combined with a "
    f"lower Vp/Vs near the surface.**",
    f"- **The size of the constant depends on the Vp/Vs assumed.** With Vp/Vs {KIM1983_VPVS:g} it is "
    f"{EXPL_BASE['hand']['iii'][3]['c']:+.3f} s (mean; the median offset is {HAND_MED:+.3f} s); with the best-fitting uniform "
    f"Vp/Vs, {EXPL_BASE['hand']['v'][3]['vpvs']:.4f} (v), it is {EXPL_BASE['hand']['v'][3]['c']:+.3f} s. Both fit (RMS "
    f"{T.loc['iii', 'RMS']:.3f} and {T.loc['v', 'RMS']:.3f} s), so the data say 'a constant of about "
    f"{abs(EXPL_BASE['hand']['v'][3]['c']):.2f} to {abs(EXPL_BASE['hand']['iii'][3]['c']):.2f} s', and the '0.27 s' is the "
    f"value for Vp/Vs {KIM1983_VPVS:g}.",
    f"- What remains after any one of these explanations is mostly station-to-station scatter: one constant per station "
    f"brings the RMS down to {T.loc['ref', 'RMS']:.3f} s.",
]
display(Markdown("**Reading the explanation table (hand picks)**\n\n" + "\n".join(txt)))
""")

# =====================================================================================================
md(r"""
## 7. Figures F1 and F2: what the offset does to absolute locations (NonLinLoc)

**Why a constant S-P offset moves the hypocenter.** An absolute locator chooses the hypocenter and origin time that
make the predicted arrival times match the picks. The P picks fix the hypocenter through the differences in P
arrival time between stations. The S-P time adds an independent constraint on the distance from the source to
each station: a shorter S-P means a source closer to the station. If every observed S-P is shorter than the model
allows, P and S cannot both be matched. The locator compromises: it shifts the origin time (which moves all
predicted P and S times together), moves the source so that the source-station distances shrink where that helps
most, and leaves systematic residuals (P picks late, S picks early). How much goes into each depends on the
station geometry and on the weights.

**Three runs per event**, with identical NonLinLoc settings and the same picks:

1. P picks only;
2. P and S picks as picked;
3. P and S picks with every S pick shifted later by the constant found in section 1 (minus the median hand-pick
   offset).

The effect of the offset alone is run 2 minus run 3 (S as picked minus S corrected), and Figure F1 plots exactly
that, one marker per event. Its gray bars are ±1σ of the run-2 location (P and S as picked, from NonLinLoc's
covariance): that is the uncertainty an analyst would report for a location that uses S, so a bias larger than the
bar would not be covered by the reported uncertainty. (The P-only 1σ would be the scale for a P-only location; it
is listed in the table below the runs.) All three are run twice: with **all stations**, and with **only the stations within [[NEAR_NETWORK_KM]] km**,
a small local network, where the S-P times carry much of the depth information. The control file is printed below.
In short: the search uses NonLinLoc's oct-tree method in a 30 km × 30 km × 30 km box around the cluster; the method
is GAU_ANALYTIC, i.e. least squares with Gaussian errors, the closest to HYPOINVERSE; the pick errors (printed
below) are written into the observation files, so LOCQUAL2ERR is not used; there are no station corrections. The
hand picks are used if every event has at least [[NLLOC_MIN_PICKS]] P and [[NLLOC_MIN_PICKS]] S picks (otherwise
PhaseNet+); the other picker is run as a check. NonLinLoc does not report an origin-time uncertainty, so we
propagate its location covariance and the pick errors through its own origin-time formula.

**A trap of layered models** (Figure F2). kim1983 has a layer boundary at [[INTERFACE_DEPTH_KM]] km, about 1 km
below the cluster. At a boundary the predicted travel times change slope with depth, so the misfit has a corner
there, and a solution can stick to the boundary although the data alone would not put it there. We count the
solutions within [[INTERFACE_TOLS_KM:0]], [[INTERFACE_TOLS_KM:1]] and [[INTERFACE_TOLS_KM:2]] km of the boundary,
and Figure F2 shows the misfit along depth.
""")

code(r"""
# section 7: NonLinLoc runs (P only; P + S as picked; P + S with S shifted), all stations and nearby stations only
cnt = PK[(PK.source == "hand") & ~PK.outlier].groupby(["kma_id", "phase"]).size().unstack()
HAND_OK = bool(len(cnt) == len(EV) and (cnt.min() >= NLLOC_MIN_PICKS).all())
NLL_SRC = "hand" if HAND_OK else "phasenet_plus"
OTHER_SRC = "phasenet_plus" if NLL_SRC == "hand" else "hand"
print(f"hand picks per event: P {int(cnt.P.min())}-{int(cnt.P.max())}, S {int(cnt.S.min())}-{int(cnt.S.max())} "
      f"(rule: >= {NLLOC_MIN_PICKS} of each) -> Figure F1 uses {LABEL[NLL_SRC]}; {LABEL[OTHER_SRC]} is run as a check")
print("NonLinLoc control file (identical for every run except the file names):")
print(open(f"{WORK}/nlloc/hand_all/{EV.index[0]}/p_only/nlloc.in").read())
print(f"pick errors in the observation files: P {NLLOC_PICK_ERR_S['P']} s, S {NLLOC_PICK_ERR_S['S']} s; S shift of run 3: +{S_SHIFT:.3f} s")
RUNS = [("p_only", ["P"], 0.0), ("p_s", ["P", "S"], 0.0), ("p_s_shifted", ["P", "S"], S_SHIFT)]
NETS = [("all", 1e9), ("near", NEAR_NETWORK_KM)]
parts = []
for src in (NLL_SRC, OTHER_SRC):
    for net, dmax in NETS:
        for run, phases, shift in RUNS:
            if src == "hand" and net == "all" and run == "p_only":
                parts.append(NLL_PONLY_HAND)   # already run in section 1.3, same settings
                continue
            parts.append(run_nll_set(src, net, dmax, run, phases, shift))
NLL = pd.concat(parts, ignore_index=True)
NLL.to_csv(f"{WORK}/nlloc_results.csv", index=False)
assert NLL.status.str.contains("LOCATED").all()
print(f"{len(NLL)} NonLinLoc locations, all 'LOCATED'")


def shifts(df, run, ref):
    a = df[df.run == ref].set_index("kma_id")
    b = df[df.run == run].set_index("kma_id").loc[a.index]
    e, n, u = so.enu(b.lat.to_numpy(), b.lon.to_numpy(), b.depth_km.to_numpy(), a.lat.to_numpy(), a.lon.to_numpy(), a.depth_km.to_numpy())
    return pd.DataFrame({"kma_id": a.index, "n": EV.loc[a.index, "n"].to_numpy(),
                         "d_depth_km": b.depth_km.to_numpy() - a.depth_km.to_numpy(),
                         "d_ot_s": b.origin_ts.to_numpy() - a.origin_ts.to_numpy(), "d_east_m": e, "d_north_m": n,
                         "d_horiz_m": np.hypot(e, n), "sig_z_km": b.sig_z_km.to_numpy(),
                         "sig_h_km": np.sqrt((b.sig_x_km.to_numpy() ** 2 + b.sig_y_km.to_numpy() ** 2) / 2.0),
                         "ot_sig_s": b.ot_sig_s.to_numpy(), "depth_run_km": b.depth_km.to_numpy(), "depth_ref_km": a.depth_km.to_numpy()})


def mean_se(x):
    x = np.asarray(x, float)
    return f"{x.mean():+.3f} ± {x.std(ddof=1) / np.sqrt(len(x)):.3f}"


rows = []
for src in (NLL_SRC, OTHER_SRC):
    for net, _ in NETS:
        df = NLL[(NLL.source == src) & (NLL.network == net)]
        for run, ref, name in (("p_s", "p_only", "P+S as picked minus P only"),
                               ("p_s_shifted", "p_only", "P+S, S shifted, minus P only"),
                               ("p_s", "p_s_shifted", "Effect of the offset: as picked minus S shifted")):
            sh = shifts(df, run, ref)
            rows.append({"Picks": LABEL[src], "Stations": "all" if net == "all" else f"within {NEAR_NETWORK_KM:g} km",
                         "Comparison": name, "Depth change, mean ± SE (km)": mean_se(sh.d_depth_km),
                         "Origin-time change, mean ± SE (s)": mean_se(sh.d_ot_s),
                         "Horizontal distance, mean (m)": round(float(sh.d_horiz_m.mean()), 0),
                         "Events shallower": int((sh.d_depth_km < 0).sum())})
NLLSUM = pd.DataFrame(rows)
display(NLLSUM)
rows = []
for (src_, net_, run_), g in NLL.groupby(["source", "network", "run"], sort=False):
    row = {"Picks": LABEL[src_], "Stations": "all" if net_ == "all" else f"within {NEAR_NETWORK_KM:g} km", "Run": run_, "Locations": len(g)}
    for tol in INTERFACE_TOLS_KM:
        row[f"Within {tol:g} km of {INTERFACE_DEPTH_KM:g} km"] = int(((g.depth_km - INTERFACE_DEPTH_KM).abs() <= tol).sum())
    rows.append(row)
BOUND = pd.DataFrame(rows)
print(f"NonLinLoc depths close to the {INTERFACE_DEPTH_KM:g} km layer boundary, by run:")
display(BOUND)
med_n = NLL.groupby(["source", "network", "run"])[["n_P", "n_S", "sig_z_km", "ot_sig_s", "rms_s"]].median().round(3)
display(med_n.rename(columns={"n_P": "Median P picks", "n_S": "Median S picks", "sig_z_km": "Median depth 1σ (km)",
                              "ot_sig_s": "Median origin-time 1σ (s)", "rms_s": "Median RMS (s)"}))
""")

code(r"""
# Figure F1: the effect of the offset alone (S as picked minus S shifted), per event
fig, axes = plt.subplots(len(NETS), 3, figsize=(11.2, 3.5 * len(NETS)), sharex=True, gridspec_kw=dict(hspace=0.38, wspace=0.34))
NLLEFF = {}
for row, (net, _) in enumerate(NETS):
    df = NLL[(NLL.source == NLL_SRC) & (NLL.network == net)]
    sh = shifts(df, "p_s", "p_s_shifted")
    ctx = df[df.run == "p_s"].set_index("kma_id").loc[sh.kma_id]
    pinned = ((sh.depth_run_km - INTERFACE_DEPTH_KM).abs() <= INTERFACE_FLAG_KM) | \
             ((sh.depth_ref_km - INTERFACE_DEPTH_KM).abs() <= INTERFACE_FLAG_KM)
    NLLEFF[net] = dict(sh=sh, pinned=pinned)
    netname = "All stations" if net == "all" else f"Stations within {NEAR_NETWORK_KM:g} km"
    # sigma columns: NonLinLoc 1-sigma of the as-picked P+S location; km for depth and horizontal, s for origin time
    for col, (key, sig, ylab, unit, nd, sgn) in enumerate((
            ("d_depth_km", ctx.sig_z_km.to_numpy(), "Depth change (km, − = shallower)", "km", 2, "+"),
            ("d_ot_s", ctx.ot_sig_s.to_numpy(), "Origin-time change (s, − = earlier)", "s", 3, "+"),
            ("d_horiz_m", 1000.0 * np.sqrt((ctx.sig_x_km.to_numpy() ** 2 + ctx.sig_y_km.to_numpy() ** 2) / 2.0),
             "Horizontal distance (m)", "m", 0, ""))):
        ax = axes[row, col]
        if key == "d_horiz_m":
            ax.bar(sh.n, sig, bottom=0.0, width=0.62, color="0.88", lw=0, zorder=0)
        else:
            ax.bar(sh.n, 2 * sig, bottom=-sig, width=0.62, color="0.88", lw=0, zorder=0)
        ax.axhline(0.0, color="0.3", lw=0.8, zorder=1)
        y = sh[key].to_numpy()
        ax.plot(sh.n[~pinned], y[~pinned], "o", color="k", ms=5.5, zorder=3)
        ax.plot(sh.n[pinned], y[pinned], "o", mfc="white", mec="k", mew=1.2, ms=5.5, zorder=3)
        mean, se_ = float(np.mean(y)), float(np.std(y, ddof=1) / np.sqrt(len(y)))
        ax.axhline(mean, color="k", lw=1.0, ls="--", zorder=2)
        note = f"Mean {mean:{sgn}.{nd}f} ± {se_:.{nd}f} {unit}"
        if key == "d_depth_km":
            note += f"; {int((y < 0).sum())} of {len(y)} shallower"
        ytop = max(float(np.max(y)), float(np.max(sig)), 0.0)
        ybot = min(float(np.min(y)), float(-np.max(sig)) if key != "d_horiz_m" else 0.0, 0.0)
        span = ytop - ybot
        ax.set_ylim(ybot - 0.06 * span, ytop + 0.30 * span)
        ax.text(0.03, 0.96, note, transform=ax.transAxes, ha="left", va="top", fontsize=7.5,
                bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none"), zorder=5)
        ax.set_ylabel(ylab)
        ax.set_title(f"{netname}: {ylab.split(' (')[0].lower()}", loc="left")
        ax.set_xticks(np.arange(1, len(EV) + 1))
        if row == len(NETS) - 1:
            ax.set_xlabel("Event number (as in Figure D)")
handles = [Line2D([], [], ls="none", marker="o", color="k", ms=5.5),
           Line2D([], [], ls="none", marker="o", mfc="white", mec="k", mew=1.2, ms=5.5),
           Line2D([], [], color="k", lw=1.0, ls="--"), Patch(color="0.88", lw=0)]
labels = [f"One event: S as picked minus S shifted by +{S_SHIFT:.2f} s",
          f"Same, one of the two solutions within {INTERFACE_FLAG_KM:g} km of the {INTERFACE_DEPTH_KM:g} km boundary",
          "Mean over the events (± standard error)", "±1σ of the P+S location (S as picked), for scale"]
so.legend_above(fig, axes, handles, labels, ncol=2)
FIGS["F1"] = so.save_fig(fig, FIG_DIR, "05_F1_nlloc_offset_effect")
plt.show()
for net in NLLEFF:
    print(f"{net}: {int(NLLEFF[net]['pinned'].sum())} of {len(NLLEFF[net]['pinned'])} events have a solution within "
          f"{INTERFACE_FLAG_KM:g} km of the boundary")
""")

md(r"""
### Figure F2: is the depth set by the data or by the layer boundary?

A *misfit slice*: for each NonLinLoc solution we keep its epicenter, move only the depth (from
[[DEPTH_SLICE_KM:0]] to [[DEPTH_SLICE_KM:1]] km in steps of [[DEPTH_SLICE_KM:2]] km), and for each trial depth
recompute the best origin time and the misfit that GAU_ANALYTIC minimizes: the sum of squared residuals, each
divided by its variance (pick error² + LOCGAU σ²). It is shown relative to its smallest value; a rise of 1 is
roughly a one-standard-deviation change. A smooth bowl means that the data determine the depth; a corner at
[[INTERFACE_DEPTH_KM]] km means that the layer boundary does. (A slice, not a full re-location at each depth.)
""")

code(r"""
# Figure F2: misfit along depth at each solution's epicenter, S as picked and S shifted
ZSL = np.round(np.arange(DEPTH_SLICE_KM[0], DEPTH_SLICE_KM[1] + 1e-9, DEPTH_SLICE_KM[2]), 4)
CASES_F2 = [("p_s", 0.0, "S as picked"), ("p_s_shifted", S_SHIFT, f"S shifted by +{S_SHIFT:.2f} s")]
fig, axes = plt.subplots(len(NETS), len(CASES_F2), figsize=(9.8, 3.3 * len(NETS)), sharex=True, sharey=True,
                         gridspec_kw=dict(hspace=0.36, wspace=0.08))
rows = []
for row, (net, dmax) in enumerate(NETS):
    for col, (run, shift, rname) in enumerate(CASES_F2):
        ax = axes[row, col]
        for k in EV.index:
            r = NLL[(NLL.source == NLL_SRC) & (NLL.network == net) & (NLL.run == run) & (NLL.kma_id == k)].iloc[0]
            q = nll_picks(NLL_SRC, k, dmax, ["P", "S"])
            mis = so.depth_misfit_slice(TTT, r.lat, r.lon, ZSL, q, STA, NLLOC_PICK_ERR_S["P"], NLLOC_PICK_ERR_S["S"],
                                        NLLOC["gau_sigma_s"], s_shift=shift)
            dmis = mis - mis.min()
            ax.plot(ZSL, dmis, color="0.45", lw=0.8, zorder=2)
            ax.plot(r.depth_km, np.interp(r.depth_km, ZSL, dmis), "o", color="k", ms=3.5, zorder=3)
            rows.append(dict(network=net, run=run, kma_id=k, nlloc_depth_km=r.depth_km, slice_min_depth_km=float(ZSL[np.argmin(mis)]),
                             at_boundary=bool(abs(r.depth_km - INTERFACE_DEPTH_KM) <= INTERFACE_FLAG_KM)))
        nb = sum(1 for x in rows if x["network"] == net and x["run"] == run and x["at_boundary"])
        ax.axvline(INTERFACE_DEPTH_KM, color="0.15", lw=1.0, ls="--", zorder=1)
        ax.set_title(f"{'All stations' if net == 'all' else f'Stations within {NEAR_NETWORK_KM:g} km'}, {rname}\n"
                     f"{nb} of {len(EV)} depths within {INTERFACE_FLAG_KM:g} km of the {INTERFACE_DEPTH_KM:g} km boundary", loc="left")
        ax.set_ylim(0, 30)
        ax.set_xlim(ZSL[0], ZSL[-1])
        if col == 0:
            ax.set_ylabel("Misfit above its minimum")
        if row == len(NETS) - 1:
            ax.set_xlabel("Trial depth (km)")
SLICES = pd.DataFrame(rows)
SLICES.to_csv(f"{WORK}/nlloc_depth_slices.csv", index=False)
handles = [Line2D([], [], color="0.45", lw=0.8), Line2D([], [], ls="none", marker="o", color="k", ms=3.5),
           Line2D([], [], color="0.15", lw=1.0, ls="--")]
labels = ["One event: misfit along depth at its epicenter", "NonLinLoc depth of that event",
          f"kim1983 layer boundary ({INTERFACE_DEPTH_KM:g} km)"]
so.legend_above(fig, axes, handles, labels, ncol=3)
FIGS["F2"] = so.save_fig(fig, FIG_DIR, "05_F2_nlloc_depth_misfit")
plt.show()
print(f"consistency: |NonLinLoc depth - lowest point of the slice| <= {(SLICES.nlloc_depth_km - SLICES.slice_min_depth_km).abs().max():.2f} km "
      f"(slice step {DEPTH_SLICE_KM[2]:g} km)")
""")

# =====================================================================================================
md(r"""
## 8. Figure G: double-difference relocation (pyrtdd), with controls

Catalog-only relocation with pyrtdd, exactly as in the relocation test of step 09: ClusteringOptions
numEllipsoids 0, maxNeighbourDist 10 km, minNumNeigh 1, maxNumNeigh 0 (no limit), minNumPhases 1; SolverOptions
absLocConstraintStart/End 0, dampingFactorStart/End 0.01, default down-weighting by residual; the kim1983
NonLinLoc grids; start: all events at the HypoDD centroid (`event_centroid_start.csv`); picks: `phase.csv` (the
PhaseNet+ picks HypoDD used). Every option value actually used is saved in each run's `settings.json`.

**Why a common shift should change nothing.** A double difference is (travel time of event 1 − travel time of
event 2) at one station for one phase, observed minus predicted. A delay that is the same for the same station and
phase in both events cancels in that difference, so the equations, and hence the solution, do not change. That is
true by construction, so the test is only meaningful together with controls that are *not* common to all events:

1. *As picked* (the reference run).
2. *Every S pick shifted* by the same constant as in section 7.
3. *Station statics*: each station's S picks shifted by its own random amount between [[DD_STATIC_RANGE_S:0]] and
   [[DD_STATIC_RANGE_S:1]] s (seed [[DD_STATIC_SEED]]), the same in every event. Should also change nothing.
4. *Event terms removed*: each event's S picks shifted by minus its PhaseNet+ event term (section 5.1), i.e. the
   part of the offset that differs from event to event is removed. This measures how much that part matters.
5. *One event shifted* (positive control): only the S picks of event [[DD_ONE_EVENT]] shifted by the constant.
   This must move that event; it shows that the relocation does respond to S timing.

For each run we report each event's change of position relative to the other events (its change minus the change
of the cluster mean) and the change of the cluster mean itself.
""")

code(r"""
# section 8: pyrtdd catalog-only relocations: as picked, every S shifted, station statics, event terms removed, one event shifted
EVT_PNP = EVTERM["phasenet_plus"]["ev"]
RID = {int(EV.loc[k, "n"]): k for k in EV.index}
ph0 = pd.read_csv(f"{RTDD_CATALOG}/phase.csv", keep_default_na=False, dtype=str)
st_codes = sorted(ph0.stationCode.unique())
STATIC = dict(zip(st_codes, np.random.default_rng(DD_STATIC_SEED).uniform(DD_STATIC_RANGE_S[0], DD_STATIC_RANGE_S[1], len(st_codes))))
DD_CASES = [("as_picked", "S picks as picked", lambda e, s: 0.0),
            ("s_shifted", f"Every S pick +{S_SHIFT:.3f} s", lambda e, s: S_SHIFT),
            ("station_static", f"Station statics ({DD_STATIC_RANGE_S[0]:g}-{DD_STATIC_RANGE_S[1]:g} s)", lambda e, s: float(STATIC[s])),
            ("event_terms_removed", "Event terms removed", lambda e, s: -float(EVT_PNP[RID[e]])),
            ("one_event", f"Event {DD_ONE_EVENT} alone shifted (+{S_SHIFT:.3f} s)", lambda e, s: S_SHIFT if e == DD_ONE_EVENT else 0.0)]
DD, DDLAB = {}, {}
for name, label, fn in DD_CASES:
    ev, n_cl, ph, shv = so.dd_run(f"{WORK}/pyrtdd/{name}", RTDD_CATALOG, NLL_TIME_DIR, fn,
                                  dict(solution=name, description=label, picks="inputs/rtdd_catalog/phase.csv"))
    DD[name], DDLAB[name] = ev, label
    nonzero = shv[np.abs(shv) > 0]
    print(f"{name}: {n_cl} cluster(s), {int((ev.relocated.astype(str).str.lower() == 'true').sum())} of {len(ev)} events relocated; "
          f"S picks moved: {len(nonzero)} of {int((ph.type == 'S').sum())}"
          + (f" (by {nonzero.min():+.3f} to {nonzero.max():+.3f} s)" if len(nonzero) else ""))
REF_DD = DD["as_picked"]
rows, DDCH = [], {}
for name, label, _ in DD_CASES[1:]:
    ch, cm = so.dd_changes(REF_DD, DD[name])
    DDCH[name] = (ch, cm)
    rows.append({"Run": label, "Cluster-mean shift (m)": round(cm, 3), "Largest relative change (m)": round(float(ch.relative_m.max()), 3),
                 "Event with the largest relative change": int(ch.relative_m.idxmax()),
                 "Largest origin-time change (ms)": round(float(np.abs(ch.ot_s).max() * 1e3), 3)})
DDT = pd.DataFrame(rows).set_index("Run")
DDT.to_csv(f"{WORK}/dd_controls.csv")
display(DDT)
DD_MAX_M = float(DDCH["s_shifted"][0][["east_m", "north_m", "up_m"]].abs().to_numpy().max())
DD_MAX_MS = float(np.abs(DDCH["s_shifted"][0].ot_s).max() * 1e3)
print(f"every S pick shifted: largest position difference {DD_MAX_M:.6f} m, largest origin-time difference {DD_MAX_MS:.6f} ms")
if os.path.exists(DL_CONTROL_RELOC):
    c9 = pd.read_csv(DL_CONTROL_RELOC).set_index("id")
    ch9, _ = so.dd_changes(c9, REF_DD)
    DD_REPRO_M = float(ch9.total_m.max())
    print(f"reproducibility: 'as picked' vs the step-09 control relocation (same picks, same settings): largest difference {DD_REPRO_M:.6f} m")
else:
    DD_REPRO_M = np.nan
    print("!! the step-09 control relocation was not found; reproducibility not checked")

# where the cluster went (the absolute position is not constrained: absLocConstraint 0)
st0 = pd.read_csv(f"{RTDD_CATALOG}/event_centroid_start.csv").set_index("id").loc[REF_DD.index]
de, dn, du = so.enu(REF_DD.latitude.to_numpy(), REF_DD.longitude.to_numpy(), REF_DD.depth.to_numpy(),
                    st0.latitude.to_numpy(), st0.longitude.to_numpy(), st0.depth.to_numpy())
DRIFT = dict(east=float(np.mean(de)), north=float(np.mean(dn)), up=float(np.mean(du)))
print(f"cluster mean of 'as picked' relative to the start centroid: {DRIFT['east']:+.0f} m east, {DRIFT['north']:+.0f} m north, "
      f"{DRIFT['up']:+.0f} m up")

# the absolute residuals pyrtdd reports (startRms, finalRms): recomputed from the grids, with and without gross mis-picks
sta_dd = pd.read_csv(f"{RTDD_CATALOG}/station.csv").set_index("stationCode")
rows = []
for i in REF_DD.index:
    g = ph0[ph0.eventId.astype(int) == i]
    res = {}
    for when, e_ in (("start", st0.loc[i]), ("final", REF_DD.loc[i])):
        tt = np.array([TTT.compute(e_.latitude, e_.longitude, e_.depth, sta_dd.loc[s, "latitude"], sta_dd.loc[s, "longitude"],
                                   sta_dd.loc[s, "elevation"], ty) for s, ty in zip(g.stationCode, g.type)])
        res[when] = np.array([UTCDateTime(t) - UTCDateTime(e_.isotime) for t in g.isotime]) - tt
    keep = np.abs(res["start"]) <= OUTLIER_ABS_RES_S
    rows.append({"Event": i, "startRms (pyrtdd)": REF_DD.loc[i, "startRms"], "Recomputed, start": np.sqrt(np.mean(res["start"] ** 2)),
                 "finalRms (pyrtdd)": REF_DD.loc[i, "finalRms"], "Recomputed, final": np.sqrt(np.mean(res["final"] ** 2)),
                 f"Phases with |residual| > {OUTLIER_ABS_RES_S:g} s": int((~keep).sum()),
                 "Largest |residual| (s)": float(np.max(np.abs(res["start"]))),
                 f"Start RMS without them (s)": float(np.sqrt(np.mean(res["start"][keep] ** 2))),
                 f"Final RMS without them (s)": float(np.sqrt(np.mean(res["final"][keep] ** 2)))})
DDRMS = pd.DataFrame(rows).set_index("Event")
display(DDRMS.round(3))
assert (DDRMS["startRms (pyrtdd)"] - DDRMS["Recomputed, start"]).abs().max() < 0.01, "startRms not reproduced"
""")

code(r"""
# Figure G: positions of the main runs, and each event's change relative to the others in every control run
ref_lat, ref_lon, ref_dep = REF_DD.latitude.mean(), REF_DD.longitude.mean(), REF_DD.depth.mean()
ea, na, ua = so.enu(REF_DD.latitude.to_numpy(), REF_DD.longitude.to_numpy(), REF_DD.depth.to_numpy(), ref_lat, ref_lon, ref_dep)
bb = DD["s_shifted"].loc[REF_DD.index]
eb, nb_, ub = so.enu(bb.latitude.to_numpy(), bb.longitude.to_numpy(), bb.depth.to_numpy(), ref_lat, ref_lon, ref_dep)
fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.0), gridspec_kw=dict(width_ratios=[1.0, 1.0, 1.55], wspace=0.42))
for ax, (xa_, ya_, xb_, yb_, xl, yl, tt) in zip(axes[:2], ((ea, na, eb, nb_, "East of the cluster mean (m)", "North of the cluster mean (m)", "(a) Map view"),
                                                          (ea, ua, eb, ub, "East of the cluster mean (m)", "Above the cluster mean (m)", "(b) East-depth section"))):
    ax.plot(xa_, ya_, "o", ms=9, mfc="none", mec="k", mew=1.1, zorder=2)
    ax.plot(xb_, yb_, "+", ms=9, color="k", mew=1.4, zorder=3)
    lim = 1.25 * max(np.abs(np.r_[xa_, ya_]).max(), 50.0)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.set_title(tt, loc="left")
ax = axes[2]
xev = np.arange(1, len(REF_DD) + 1)
GMK = {"s_shifted": ("+", "k", "k", 9, -0.24), "station_static": ("x", "k", "k", 7, -0.08),
       "event_terms_removed": ("D", "0.55", "0.25", 5, 0.08), "one_event": ("^", "0.85", "k", 6, 0.24)}
for name, (mk, fc, ec, ms, dx) in GMK.items():
    ch = DDCH[name][0].loc[REF_DD.index]
    ax.plot(xev + dx, ch.relative_m.to_numpy(), mk, mfc=fc, mec=ec, color=ec, ms=ms, mew=1.1, ls="none", zorder=3)
ax.set_yscale("symlog", linthresh=1.0)
ax.set_ylim(-0.1, 10 ** np.ceil(np.log10(max(10.0, max(DDCH[k][0].relative_m.max() for k in GMK)) * 1.5)))
ax.axhline(0.0, color="0.4", lw=0.8, zorder=1)
ax.set_xticks(xev)
ax.set_xticklabels([str(i) for i in REF_DD.index])
ax.set_xlabel("Event number (as in Figure D)")
ax.set_ylabel("Change relative to the other events (m)")
ax.set_title("(c) Each event's change of position, relative to the others", loc="left")
ZERO_TXT = {"s_shifted": "every S pick shifted", "station_static": "station statics"}
z0 = [ZERO_TXT[k] for k in ZERO_TXT if DDCH[k][0].relative_m.max() == 0.0]
if z0:
    ax.text(0.03, 0.06, "Exactly zero: " + " and ".join(z0), transform=ax.transAxes,
            fontsize=7.5, ha="left", va="bottom", bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none"))
handles = [Line2D([], [], ls="none", marker="o", mfc="none", mec="k", ms=8, mew=1.1)] + \
          [Line2D([], [], ls="none", marker=mk, mfc=fc, mec=ec, color=ec, ms=ms, mew=1.1) for mk, fc, ec, ms, _ in GMK.values()]
labels = ["As picked (a, b)", f"{DDLAB['s_shifted']} (a, b, c)"] + [f"{DDLAB[k]} (c)" for k in list(GMK)[1:]]
leg = so.legend_above(fig, axes, handles, labels, ncol=3)
so.text_above(fig, [leg] + list(axes),
              "pyrtdd relative positions: unchanged by S shifts common to all events, changed by event-specific S shifts",
              fontsize=9.5)
note = (f"Positions in a and b are relative to the cluster mean of the 'as picked' run. The cluster as a whole lies "
        f"{DRIFT['east']:+.0f} m east, {DRIFT['north']:+.0f} m north and {DRIFT['up']:+.0f} m up from the start centroid "
        f"(absLocConstraint 0), in both of these runs. Shift of the cluster mean in the runs of c: "
        + "; ".join(f"{DDLAB[k][0].lower() + DDLAB[k][1:]}, {DDCH[k][1]:.0f} m" for k in GMK) + ".")
so.text_below(fig, list(axes), textwrap.fill(note, 190), fontsize=7)
FIGS["G"] = so.save_fig(fig, FIG_DIR, "05_G_double_difference_controls")
plt.show()
""")

# =====================================================================================================
md(r"""
## 9. Comprehensive summary

First a verdict on each part of the claim, then the key numbers, take-home messages and caveats. Every number in
this section is formatted from variables computed above; none is typed in. Intervals are 95% bootstrap intervals
with stations resampled ([[N_BOOT]] samples) unless stated otherwise; ± values are standard errors over the events.
""")

code(r"""
# 9. verdict on each part of the claim (all numbers computed above)
hr, pr = OFFS.loc["Hand picks"], OFFS.loc["PhaseNet+"]
DL_MEDS = [float(OFFS.loc[LABEL[s], "Median offset (s)"]) for s in SOURCES[2:]]
DL_TXT = (f"; the {nw(len(DL_MEDS))} deep-learning pickers {min(DL_MEDS):+.3f} to {max(DL_MEDS):+.3f} s" if DL_MEDS
          else "; no deep-learning picks were available")
r11, rhs = ROBUST.loc[VARIANTS[3][1]], ROBUST.loc[VARIANTS[5][1]]
TX, BX = EXPL["hand"], EXPL_BASE["hand"]
eth = EVTERM["hand"]
dbin_txt = ", ".join(f"{r['Median offset (s)']:+.2f} s at {r['Distance (km)']} km" for _, r in DBH.iterrows())
SH = {net: NLLEFF[net]["sh"] for net in NLLEFF}
NPIN = {net: int(NLLEFF[net]["pinned"].sum()) for net in NLLEFF}


def se(x):
    return float(np.std(np.asarray(x, float), ddof=1) / np.sqrt(len(x)))


npk = NLL[(NLL.source == NLL_SRC) & (NLL.network == "near") & (NLL.run == "p_s")]
VERDICT = [
    ("S-P about 0.27 s shorter than the velocity model predicts",
     f"Holds for kim1983 with Vp/Vs {KIM1983_VPVS:g} (the model of HypoDD and the grids); the size depends on the model",
     f"Median offset {hr['Median offset (s)']:+.3f} s (95% CI {hr['95% CI low (s)']:+.3f} to {hr['95% CI high (s)']:+.3f}) for the hand "
     f"picks, {pr['Median offset (s)']:+.3f} s for PhaseNet+{DL_TXT}. Onsets found without any pick: {AIC_ALL['med']:+.3f} s "
     f"({AIC_ALL['before']:.0%} before the model S time). Against kim2011 {r11['Hand picks: median offset (s)']:+.3f} s, against "
     f"kim1983 P with HYPOINVERSE's S model {rhs['Hand picks: median offset (s)']:+.3f} s; with the best-fitting uniform Vp/Vs "
     f"({BX['v'][3]['vpvs']:.3f}) the constant is {BX['v'][3]['c']:+.3f} s.",
     "Figures A-D, B3; sections 1.3, 6.2"),
    ("By the same amount in every event",
     "Holds to within a few hundredths of a second; but not the same at every distance or station",
     f"Per-event medians {EVSPREAD.min():+.3f} to {EVSPREAD.max():+.3f} s (hand picks); event terms after removing station terms "
     f"{eth['ev'].min():+.3f} to {eth['ev'].max():+.3f} s (SD {eth['sd']:.3f} s; Kruskal-Wallis p = {eth['kw_p']:.1g}: small but "
     f"real). By distance: {dbin_txt}; the {XBIN['label']} km value comes mostly from {nw(len(XBIN['top3']))} stations "
     f"({XBIN['n_top3']} of {XBIN['pairs']} pairs; median of station medians {XBIN['med_sta']:+.2f} s). Station medians "
     f"{STSPREAD['lo']:+.2f} to {STSPREAD['hi']:+.2f} s (SD {STSPREAD['sd']:.2f} s).",
     "Figures C, D; section 5.1"),
    ("Vp/Vs = 1.727 fits the data",
     "Holds",
     f"Wadati slope (independent of the origin times) {WAD['hand']['vpvs']:.4f} (95% CI {WAD['hand']['lo']:.4f} to "
     f"{WAD['hand']['hi']:.4f}) for the hand picks, {WAD['phasenet_plus']['vpvs']:.4f} for PhaseNet+; against model P travel "
     f"times {WADM['hand']['vpvs']:.4f}. The intercepts (about {C_MED:+.2f} s) do depend on the origin times.",
     "Figure E1"),
    ("This does not matter for double-difference relocation",
     "Holds for the part of the offset that is common to all events at a station",
     f"pyrtdd positions identical (largest difference {1000 * DD_MAX_M:.3f} mm, {DD_MAX_MS:.3f} ms) with every S pick "
     f"+{S_SHIFT:.3f} s, and with random station statics ({DDT.loc[DDLAB['station_static'], 'Largest relative change (m)']:.3f} m). "
     f"Removing the event-to-event part (event terms) moves events by up to "
     f"{DDT.loc[DDLAB['event_terms_removed'], 'Largest relative change (m)']:.0f} m relative to each other; shifting the S picks of "
     f"event {DD_ONE_EVENT} alone moves it {DDCH['one_event'][0].relative_m.loc[DD_ONE_EVENT]:.0f} m.",
     "Figure G"),
    ("It would bias absolute locations that use S",
     "Holds; where the bias goes depends on the station geometry",
     f"NonLinLoc, S as picked minus S corrected. All stations: origin time {SH['all'].d_ot_s.mean():+.3f} ± {se(SH['all'].d_ot_s):.3f} s; "
     f"the depth change cannot be measured with kim1983 ({NPIN['all']} of {len(SH['all'])} events have a solution within "
     f"{INTERFACE_FLAG_KM:g} km of the {INTERFACE_DEPTH_KM:g} km boundary). Stations within {NEAR_NETWORK_KM:g} km: depth "
     f"{SH['near'].d_depth_km.mean():+.2f} ± {se(SH['near'].d_depth_km):.2f} km ({int((SH['near'].d_depth_km < 0).sum())} of "
     f"{len(SH['near'])} shallower) for this configuration.",
     "Figures F1, F2"),
]
lines = ["| Part of the claim | Verdict | Evidence (computed) | Where |", "|---|---|---|---|"]
lines += [f"| {a} | **{b}** | {c} | {d} |" for a, b, c, d in VERDICT]
display(Markdown("**Verdict on each part of the claim**\n\n" + "\n".join(lines)))
""")

code(r"""
# 9. key numbers (all computed above)
def ci_txt(med, lo, hi, nd=3):
    return f"{med:+.{nd}f} s (95% CI {lo:+.{nd}f} to {hi:+.{nd}f})"


K = []
K.append(("Hand picks: UTC reference established",
          f"SAC headers and absolute PhaseNet times agree within {REFT['Route 2 minus route 1 (µs)'].abs().max():.1f} µs "
          f"({len(REFT)} events); {SPOT_EXACT} of {len(SPOT)} header spot checks exact", "Section 1.1"))
K.append(("Hand picks", f"{len(HAND)} ({(HAND.phase == 'P').sum()} P, {(HAND.phase == 'S').sum()} S); gross outliers "
          f"{int(PK[(PK.source == 'hand')].outlier.sum())}", "Section 1.2"))
for src in SOURCES:
    r = OFFS.loc[LABEL[src]]
    K.append((f"Median S-P offset, {LABEL[src]}", ci_txt(r['Median offset (s)'], r['95% CI low (s)'], r['95% CI high (s)'])
              + f"; {int(r['Pairs used'])} pairs, {int(r['Excluded (gross outlier)'])} excluded",
              "Figures C, D" if src in ("hand", "phasenet_plus") else "Figure D"))
K.append(("AIC onsets (no pick used) minus model S time", ci_txt(AIC_ALL["med"], AIC_ALL["lo"], AIC_ALL["hi"])
          + f"; {AIC_ALL['before']:.0%} of {AIC_ALL['n']} pairs before it; AIC onset minus hand S pick {AIC_ALL['minus_hand']:+.3f} s (median)",
          "Figure B3"))
K.append(("Per-event medians, hand picks", f"{EVSPREAD.min():+.3f} to {EVSPREAD.max():+.3f} s (SD {EVSPREAD.std():.3f} s, "
          f"{int(EVSPREAD.notna().sum())} events); all pickers {ALLPICK_EV.min():+.3f} to {ALLPICK_EV.max():+.3f} s", "Figure D"))
for src in EVTERM:
    t_ = EVTERM[src]
    K.append((f"Event terms (station terms removed), {LABEL[src]}", f"{t_['ev'].min():+.3f} to {t_['ev'].max():+.3f} s "
              f"(SD {t_['sd']:.3f} s); Kruskal-Wallis p = {t_['kw_p']:.1g}", "Section 5.1"))
for _, r in DBH.iterrows():
    K.append((f"Offset at {r['Distance (km)']} km, hand picks", f"{r['Median offset (s)']:+.3f} s (95% CI {r['95% CI (s)']}), "
              f"{r['Pairs']} pairs from {r['Stations']} stations; median of station medians {r['Median of station medians (s)']:+.3f} s",
              "Figure C"))
K.append((f"Station medians, hand picks (>= {STATION_MIN_PAIRS} pairs)", f"{STSPREAD['lo']:+.2f} to {STSPREAD['hi']:+.2f} s, SD "
          f"{STSPREAD['sd']:.2f} s ({STSPREAD['n']} stations)", "Figure C"))
K.append(("Hand minus PhaseNet+ (medians)", f"P {HVP.loc['P pick', 'Median (s)']:+.3f} s, S {HVP.loc['S pick', 'Median (s)']:+.3f} s, "
          f"S-P {HVP.loc['S-P time', 'Median (s)']:+.3f} s (N = {HVP.loc['P pick', 'N']}, {HVP.loc['S pick', 'N']}, {HVP.loc['S-P time', 'N']})",
          "Section 1.2"))
K.append(("Hand vs PhaseNet+ S-P consistency", f"{PICK_NOISE_SP:.3f} s (lower bound on the picking error of one picker)", "Section 1.2"))
for src in ("hand", "phasenet_plus"):
    w = WAD[src]
    K.append((f"Wadati Vp/Vs, {LABEL[src]}", f"{w['vpvs']:.4f} (95% CI {w['lo']:.4f} to {w['hi']:.4f}); per-event median "
              f"{w['per_event_median']:.4f}; intercepts {w['intercepts'].min():+.2f} to {w['intercepts'].max():+.2f} s; against "
              f"model P travel times {WADM[src]['vpvs']:.4f}", "Figure E1"))
for k, r in TX.iterrows():
    K.append((f"Explanation {NAMES[k]}", f"RMS {r['RMS']:.3f} s [{r['RMS lo']:.3f}, {r['RMS hi']:.3f}]; trend {r['Trend']:+.2f} "
              f"[{r['Trend lo']:+.2f}, {r['Trend hi']:+.2f}] s per 100 km; within {NEAR_KM[1]:g} km {r['Near']:+.3f} s "
              f"[{r['Near lo']:+.3f}, {r['Near hi']:+.3f}]; fitted: {r['Fitted values']}", "Figure E2"))
for col, name in VARIANTS[1:6]:
    r = ROBUST.loc[name]
    K.append((f"Offset with model S-P from {name}", f"hand {r['Hand picks: median offset (s)']:+.3f} s ({r['Hand picks: 95% CI (s)']}); "
              f"PhaseNet+ {r['PhaseNet+: median offset (s)']:+.3f} s", "Section 1.3"))
for _, r in NLLSUM[NLLSUM.Picks == LABEL[NLL_SRC]].iterrows():
    K.append((f"NonLinLoc, {r['Stations']} stations: {r['Comparison']}", f"depth {r['Depth change, mean ± SE (km)']} km; origin time "
              f"{r['Origin-time change, mean ± SE (s)']} s; horizontal {r['Horizontal distance, mean (m)']:.0f} m", "Figure F1"))
for _, r in BOUND[BOUND.Picks == LABEL[NLL_SRC]].iterrows():
    K.append((f"NonLinLoc depths at the {INTERFACE_DEPTH_KM:g} km boundary, {r['Stations']} stations, {r['Run']}",
              ", ".join(f"{r[f'Within {t:g} km of {INTERFACE_DEPTH_KM:g} km']} within {t:g} km" for t in INTERFACE_TOLS_KM)
              + f" (of {r['Locations']})", "Figure F2"))
for name, r in DDT.iterrows():
    K.append((f"pyrtdd: {name} minus as picked", f"largest relative change {r['Largest relative change (m)']:.3f} m; cluster-mean shift "
              f"{r['Cluster-mean shift (m)']:.3f} m; largest origin-time change {r['Largest origin-time change (ms)']:.3f} ms", "Figure G"))
K.append(("pyrtdd reproducibility vs step 09 control", f"largest difference {DD_REPRO_M:.6f} m", "Section 8"))
K.append(("pyrtdd cluster drift from the start centroid", f"{DRIFT['east']:+.0f} m east, {DRIFT['north']:+.0f} m north, {DRIFT['up']:+.0f} m up",
          "Section 8"))
K.append(("pyrtdd absolute RMS without gross mis-picks", f"start {DDRMS['Start RMS without them (s)'].min():.3f}-"
          f"{DDRMS['Start RMS without them (s)'].max():.3f} s, final {DDRMS['Final RMS without them (s)'].min():.3f}-"
          f"{DDRMS['Final RMS without them (s)'].max():.3f} s", "Section 8"))
KEY = pd.DataFrame(K, columns=["Quantity", "Value", "Where"])
KEY.to_csv(f"{WORK}/summary_key_numbers.csv", index=False)
with pd.option_context("display.max_colwidth", 220):
    display(KEY.set_index("Quantity"))
json.dump({"hand_median_offset_s": HAND_MED, "hand_ci95_s": HAND_CI, "s_shift_s": S_SHIFT,
           "offsets": {s: dict(OFFS.loc[LABEL[s], ["Median offset (s)", "95% CI low (s)", "95% CI high (s)", "Pairs used"]].astype(float)) for s in SOURCES},
           "aic": {k: v for k, v in AIC_ALL.items()},
           "wadati": {s: {k: (float(v) if not isinstance(v, pd.Series) else v.to_dict()) for k, v in WAD[s].items()} for s in WAD},
           "event_terms": {s: {"sd": EVTERM[s]["sd"], "kw_p": EVTERM[s]["kw_p"], "terms": EVTERM[s]["ev"].to_dict()} for s in EVTERM},
           "explanations_hand": TX.drop(columns=["Explanation"]).to_dict(orient="index"),
           "dd_controls": DDT.to_dict(orient="index"), "dd_max_diff_m": DD_MAX_M, "dd_max_diff_ms": DD_MAX_MS,
           "figures": FIGS}, open(f"{WORK}/summary.json", "w"), indent=1, default=str)
print("saved:", f"{WORK}/summary_key_numbers.csv", f"{WORK}/summary.json")
""")

code(r"""
# 9. take-home messages, written from the computed numbers
ex = REFT.set_index("Event").loc[EXAMPLE_EVENT]
lines = [
    f"- **The hand picks now have exact UTC times.** The tables store seconds after the reference time of the server B SAC files, an earlier "
    f"HYPOINVERSE origin (e.g. {ex['Reference time (route 1, SAC header)']} for the {ML} {EV.loc[EXAMPLE_EVENT, 'ml']:.1f} event); the SAC "
    f"headers and the absolute April picks agree within {REFT['Route 2 minus route 1 (µs)'].abs().max():.1f} µs. The reference of the local "
    f"waveform copy would have made every hand pick {REFT['Local minus true (ms)'].min():.0f}-{REFT['Local minus true (ms)'].max():.0f} ms "
    f"late (section 1.1).",
    f"- **The S-P times are shorter than kim1983 predicts, in every picker and in the waveforms themselves.** Median offset "
    f"{hr['Median offset (s)']:+.3f} s for the hand picks (95% CI {hr['95% CI low (s)']:+.3f} to {hr['95% CI high (s)']:+.3f}, "
    f"{int(hr['Pairs used'])} pairs) and {pr['Median offset (s)']:+.3f} s for PhaseNet+ (Figures C, D){DL_TXT}"
    + (" (Figure D)" if DL_MEDS else "") + f". An onset detector that "
    f"uses no pick finds the S onsets {AIC_ALL['med']:+.3f} s from the model S time ({AIC_ALL['before']:.0%} of the pairs before it; "
    f"Figure B3), and the stacks of Figure B rise before zero: the S energy really starts before the model S time.",
    f"- **About the same in every event, but not at every distance.** Per-event medians {EVSPREAD.min():+.3f} to {EVSPREAD.max():+.3f} s "
    f"(Figure D); after removing the station-to-station differences the events differ by {eth['ev'].min():+.3f} to {eth['ev'].max():+.3f} s, "
    f"small but real (section 5.1). Against distance the offset is negative everywhere and roughly constant ({dbin_txt}); the "
    f"{XBIN['label']} km value comes mostly from {nw(len(XBIN['top3']))} stations ({', '.join(XBIN['top3'])}), and station medians "
    f"scatter with SD {STSPREAD['sd']:.2f} s (Figure C).",
    f"- **Vp/Vs {KIM1983_VPVS:g} still fits the slope; the constant depends on the Vp/Vs assumed.** The Wadati slope gives Vp/Vs "
    f"{WAD['hand']['vpvs']:.3f} (95% CI {WAD['hand']['lo']:.3f}-{WAD['hand']['hi']:.3f}) for the hand picks and "
    f"{WAD['phasenet_plus']['vpvs']:.3f} for PhaseNet+ (Figure E1). The constant is {BX['iii'][3]['c']:+.2f} s with Vp/Vs "
    f"{KIM1983_VPVS:g} and {BX['v'][3]['c']:+.2f} s with the best-fitting {BX['v'][3]['vpvs']:.3f}; both fit (section 6.2).",
    f"- **A depth change or one uniform Vp/Vs is not enough.** Depth only: RMS {TX.loc['ivb', 'RMS']:.3f} s even with a free depth per "
    f"event. One uniform Vp/Vs: RMS close to that of a constant, but a residual trend of {TX.loc['ii', 'Trend']:+.2f} s per 100 km "
    f"(95% CI {TX.loc['ii', 'Trend lo']:+.2f} to {TX.loc['ii', 'Trend hi']:+.2f}) (Figure E2 a, c).",
    f"- **Where the shortening comes from is not settled.** With the HypoDD depths the nearest stations favor a shortening that does not "
    f"grow with distance (a shared picking convention or an effect very close to the source): explanations acting along the path leave "
    f"{min(TX.loc[k, 'Near1'] for k in ('vi', 'viii', 'ix')):+.2f} to {max(TX.loc[k, 'Near1'] for k in ('vi', 'viii', 'ix')):+.2f} s within "
    f"{NEAR_KM[0]:g} km (Figure E2 d). But sources {abs(BX['x'][3]['dz']):.2f} km shallower plus Vp/Vs {BX['x'][3]['vpvs']:.3f} above "
    f"{NEAR_STATION_LAYER_KM[1]:g} km fit as well (RMS {TX.loc['x', 'RMS']:.3f} vs {TX.loc['iii', 'RMS']:.3f} s); only the P-only depths "
    f"({abs(P1DZ.mean()):.2f} ± {P1DZ.std(ddof=1) / np.sqrt(len(P1DZ)):.2f} km {'deeper' if P1DZ.mean() > 0 else 'shallower'} than "
    f"HypoDD, with the kim1983 P speeds) speak against that. The kim2011 model "
    f"fits with nothing adjusted (offset {r11['Hand picks: median offset (s)']:+.3f} s), so the '0.27 s' belongs to kim1983 with Vp/Vs "
    f"{KIM1983_VPVS:g}.",
    f"- **Absolute locations that use S are biased; the station geometry decides where the bias goes.** With all stations the S picks "
    f"as picked move the origin time by {SH['all'].d_ot_s.mean():+.3f} ± {se(SH['all'].d_ot_s):.3f} s relative to S picks corrected by "
    f"+{S_SHIFT:.3f} s; the depth change cannot be measured with kim1983, because {NPIN['all']} of {len(SH['all'])} events have a solution "
    f"within {INTERFACE_FLAG_KM:g} km of the {INTERFACE_DEPTH_KM:g} km layer boundary, where the misfit has a corner (Figures F1, F2). "
    f"With only the stations within {NEAR_NETWORK_KM:g} km (median {int(npk.n_P.median())} P and {int(npk.n_S.median())} S picks), the "
    f"hypocenters come out {abs(SH['near'].d_depth_km.mean()):.2f} ± {se(SH['near'].d_depth_km):.2f} km "
    f"{'shallower' if SH['near'].d_depth_km.mean() < 0 else 'deeper'} ({int((SH['near'].d_depth_km < 0).sum())} of {len(SH['near'])} "
    f"events) for this configuration, {abs(SH['near'].d_depth_km.mean()) / float(npk.sig_z_km.median()):.1f} times the depth 1σ that "
    f"NonLinLoc reports for these locations (median {float(npk.sig_z_km.median()):.2f} km); the ± is the event-to-event spread, not the "
    f"uncertainty of the bias.",
    f"- **Double-difference relocation is unaffected by the part of the offset that all events share at a station.** pyrtdd gives "
    f"identical relative positions with every S pick shifted and with random station statics, but the part that differs from event to "
    f"event (event terms) moves events by up to {DDT.loc[DDLAB['event_terms_removed'], 'Largest relative change (m)']:.0f} m, and "
    f"shifting one event's S picks moves it {DDCH['one_event'][0].relative_m.loc[DD_ONE_EVENT]:.0f} m (Figure G).",
]
display(Markdown("**Take-home messages**\n\n" + "\n".join(lines)))
""")

code(r"""
# 9. caveats and what to do, written from the computed numbers
BROW = BOUND[(BOUND.Picks == LABEL[NLL_SRC]) & (BOUND.Stations == "all") & (BOUND.Run == "p_s")].iloc[0]
cav = [
    f"- **A shared picking convention is not excluded.** Hand and PhaseNet+ picks agree closely (medians "
    f"{HVP.loc['P pick', 'Median (s)']:+.3f} s for P and {HVP.loc['S pick', 'Median (s)']:+.3f} s for S) and show the same offset"
    + (f", and so do the {nw(len(DL_MEDS))} deep-learning pickers" if DL_MEDS else "") + ". The AIC onsets lie "
    f"{AIC_ALL['minus_hand']:+.3f} s from the hand S picks (median): AIC marks where the variability changes most, which for an "
    f"emergent onset is usually a little after the first visible energy, so it supports most of the offset ({AIC_ALL['med']:+.3f} s) "
    f"but cannot decide about a convention of a few hundredths of a second.",
    f"- **Where the shortening arises depends on the depth assumed.** With the HypoDD depths the nearest stations favor a "
    f"distance-independent term; a shallower source (by {abs(BX['x'][3]['dz']):.2f} km) combined with a lower Vp/Vs near the surface "
    f"fits as well. Only the P-only depths, which rest on the kim1983 P speeds, argue against it (section 6.2).",
    f"- **The size of the offset depends on the reference model.** It is {HAND_MED:+.3f} s against kim1983 with Vp/Vs "
    f"{KIM1983_VPVS:g} (HypoDD and the grids), {rhs['Hand picks: median offset (s)']:+.3f} s against kim1983 P speeds with "
    f"HYPOINVERSE's own S speeds ({'/'.join(f'{v:.2f}' for v in HINV_KIM1983_VS)} km/s), and {r11['Hand picks: median offset (s)']:+.3f} s "
    f"against kim2011. The reference HYPOINVERSE locations (kim1983 run) therefore used S picks whose S-P times are about "
    f"{abs(rhs['Hand picks: median offset (s)']):.2f} s shorter than its own model predicts.",
    f"- **Station elevations.** The grids include the real station elevations; HYPOINVERSE and HypoDD used sea level. With stations at "
    f"sea level the offset is {ROBUST.loc[VARIANTS[4][1], 'Hand picks: median offset (s)']:+.3f} s instead of {HAND_MED:+.3f} s.",
    f"- **One NonLinLoc configuration, and a layered model.** Only GAU_ANALYTIC with pick errors {NLLOC_PICK_ERR_S['P']}/"
    f"{NLLOC_PICK_ERR_S['S']} s, LOCGAU {NLLOC['gau_sigma_s']} s and the {NEAR_NETWORK_KM:g} km subset were tried; other weights "
    f"(or EDT) split the bias between origin time and depth differently. Of the {int(BROW['Locations'])} all-station solutions with S "
    f"as picked, " + ", ".join(f"{int(BROW[f'Within {t:g} km of {INTERFACE_DEPTH_KM:g} km'])} lie within {t:g} km" for t in INTERFACE_TOLS_KM)
    + f" of the {INTERFACE_DEPTH_KM:g} km boundary (table in section 7); where a solution sits on that corner its depth is set by the "
    f"model, not the data (Figure F2). The origin-time 1σ values are computed here by propagating NonLinLoc's covariance; NonLinLoc reports none.",
    f"- **Double difference.** The zero change is exact by construction for any shift common to both events of a pair. The absolute "
    f"position of a double-difference solution comes from its start or anchor (here the cluster drifted {DRIFT['east'] / 1000.0:.2f} km "
    f"east of the start centroid, identically with and without the S shift; shifting one event's S picks moved the whole cluster by "
    f"{DDCH['one_event'][1] / 1000.0:.1f} km), so a biased absolute catalog stays biased. When the catalog and "
    f"new events are picked by different pickers, the difference of their offsets (picker medians differ by up to "
    f"{float(OFFS['Median offset (s)'].max() - OFFS['Median offset (s)'].min()):.3f} s here) does not cancel. pyrtdd's startRms and "
    f"finalRms include gross mis-picks (up to {DDRMS['Largest |residual| (s)'].max():.1f} s); without them the absolute RMS rises from "
    f"{DDRMS['Start RMS without them (s)'].median():.2f} to {DDRMS['Final RMS without them (s)'].median():.2f} s (medians), because "
    f"double difference does not minimize absolute residuals and the cluster is free to drift.",
    f"- **The distance dependence is not flat**: {XBIN['med']:+.2f} s in the {XBIN['label']} km range, which comes mostly from "
    f"{', '.join(XBIN['top3'])} (median of its station medians {XBIN['med_sta']:+.2f} s), and the station medians scatter with SD "
    f"{STSPREAD['sd']:.2f} s, so a single constant is a first-order description only.",
    "- **What an analyst should do for absolute locations with S picks:** use S station corrections (e.g. NonLinLoc LOCDELAY or "
    "HYPOINVERSE station delays from the station medians of Figure C, file `station_median_offsets_hand.csv`; not tested here), or at "
    "least one fitted S-P constant; or use a model whose S-P times fit (kim2011 already does); and check depths against P-only "
    "locations, especially with few nearby stations. Double-difference relocation needs no change as long as all events are picked "
    "the same way.",
]
display(Markdown("**Caveats**\n\n" + "\n".join(cav)))
print("figures written:")
for k_, (png, pdf) in FIGS.items():
    print(f"  {k_}: {png}  |  {pdf}")
""")

md(r"""
### How to reproduce

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker/notebooks
source /home/msseo/miniforge3/etc/profile.d/conda.sh && conda activate pyrtdd
python build_05_gwangyang_sp_offset.py      # writes 05_gwangyang_sp_offset.ipynb (and compiles every code cell)
rm -f figures/05_*.png figures/05_*.pdf      # remove old figures
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=pyrtdd \
    --ExecutePreprocessor.timeout=3600 05_gwangyang_sp_offset.ipynb
```

- Inputs: everything under `data/gwangyang_11ev/` named in the parameter cell, the DL-picker picks of step 09
  (`runs/gwangyang/dlpicker/analysis/dl_picks_all.csv`; if absent, the notebook says so and runs without them),
  and NonLinLoc v7.00.16 (`software/NonLinLoc/bin`).
- The 16 SAC files, 11 pick files and 4 notebooks copied read-only from server B are in
  `data/gwangyang_11ev/reference_supplement/manual_picks_provenance/` (md5 sums in `reference_supplement/PROVENANCE.md`).
- Outputs: `data/gwangyang_11ev/reference_tables/picks_manual_utc.csv` (tidy hand picks in UTC); in
  `runs/gwangyang/sp_offset/`: `sp_pairs.csv`, `aic_onsets_hand.csv`, `per_event_offsets.csv`, `event_terms.csv`,
  `station_median_offsets_hand.csv`, `explanations_*.csv`, `nlloc_results.csv` with the NonLinLoc runs in `nlloc/`,
  `nlloc_depth_slices.csv`, the pyrtdd runs in `pyrtdd/` (one folder per control) with `dd_controls.csv`,
  `hand_pick_reference_times.csv`, `summary_key_numbers.csv`, `summary.json`; figures `notebooks/figures/05_*.png`
  and `.pdf`.
- Helper code: `notebooks/lib/sp_offset.py` (the 1-D travel-time functions are verbatim copies from
  `install/02_validate_nll_grids.py`, and their vectorized twin is checked against them in section 6.2;
  `relocate()` follows `runs/gwangyang/dlpicker/scripts/09_reloc.py`).
- Run time: printed by the last cell (one CPU; NonLinLoc about 130 locations, 5 pyrtdd relocations, bootstraps).
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
