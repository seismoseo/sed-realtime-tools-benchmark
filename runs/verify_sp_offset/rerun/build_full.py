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

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_sp_offset/rerun/full/05_rerun_full.ipynb"
CELLS = []


def md(text):
    CELLS.append(new_markdown_cell(text.strip("\n")))


def code(text):
    CELLS.append(new_code_cell(text.strip("\n")))


# =====================================================================================================
md(r"""
# Gwangyang: the S-P times are shorter than the kim1983 model predicts

**The claim checked here.** In the Gwangyang benchmark (11 KMA events from 2021-07 to 2026-02, KMA magnitude
$\mathit{M}_{\mathrm{L}}$ 1.1-2.2, a cluster about 100 m across at about 13.9 km depth near 35.00 N 127.73 E,
54 KS stations within 100 km), the S-P times of the reference picks seem to be about 0.27 s shorter than the
velocity model predicts, by about the same amount in every event, while Vp/Vs = 1.727 fits the data. If so, this
should not matter for double-difference relocation, but it should bias absolute locations that use S picks.

This notebook checks the claim with three independent kinds of picks (the user's own hand picks, the PhaseNet+
reference picks and four deep-learning pickers of the scdlrtpicker plugin), shows it on the waveforms, tests simple
explanations, and measures the consequences for absolute and for double-difference locations.

**Terms used throughout, in plain words**

- *Pick*: the time at which a seismologist (a *hand pick*) or a computer program marks the arrival of a wave at a
  station.
- *P and S waves*: the P wave (compressional) is faster and arrives first; the S wave (shear) is slower and arrives
  later.
- *S-P time*: how long after the P wave the S wave arrives at a station (S pick minus P pick). Both waves leave the
  source at the same moment, so the unknown origin time of the earthquake cancels: the S-P time depends only on where
  the source and the station are and on the wave speeds in between. It grows with distance, roughly as
  (distance travelled) × (1/Vs − 1/Vp).
- *Vp/Vs*: the P-wave speed divided by the S-wave speed. If Vp/Vs is the same everywhere, the S wave takes exactly
  Vp/Vs times as long as the P wave, so S-P = (Vp/Vs − 1) × (P travel time); for Vp/Vs = 1.73 that is
  0.73 × (P travel time).
- *Velocity model kim1983*: three flat layers with tops at 0, 15 and 32 km and P speeds of 5.98, 6.38 and
  7.95 km/s; S speed = P speed / 1.73. HypoDD used it, and the NonLinLoc travel-time grids of this project hold
  exactly this model, with the real station elevations.
- *Model S-P*: the S-P time that a velocity model predicts at a station for a given hypocenter.
- *Offset*: observed S-P minus model S-P. A negative offset means that the S wave comes sooner after the P wave
  than the model says.
- *Hypocenter*: the point inside the Earth where the earthquake starts; *origin time*: when it starts.
- *Absolute location* (HYPOINVERSE, NonLinLoc) finds one event's hypocenter and origin time from that event's own
  arrival times. *Double-difference relocation* (HypoDD, rtDD/pyrtdd) finds where events are relative to each
  other, from differences of travel times between pairs of events at the same station.
- *95% interval (CI)*: the range that contains the true value with 95% confidence; here always from a bootstrap,
  i.e. from repeating the calculation many times on data resampled with replacement.

**Contents**

0. Parameters
1. Data assembly: the time reference of the hand picks, all picks, hypocenters, model S-P, the outlier rule, and how
   much the model S-P depends on our choices
2. Figure A: one near and one distant station of the $\mathit{M}_{\mathrm{L}}$ 2.2 event
3. Figure B: record sections of two events, aligned on each station's own P pick
4. Figure C: S-P against distance for all 11 events
5. Figure D: the offset event by event, for every picker
6. Figure E: the Wadati diagram, and which simple explanation is needed
7. Figure F: the consequence for absolute locations (NonLinLoc)
8. Figure G: double-difference relocation is not affected (pyrtdd)
9. Comprehensive summary
""")

md(r"""
## 0. Parameters

Every setting of this notebook is in the next cell: input files, velocity models, the outlier rule, bootstrap
counts, the filter, and the NonLinLoc and pyrtdd settings. Nothing further down changes them.
""")

code(r"""
# ============================== PARAMETERS ==============================
# every setting of this notebook; nothing below changes these values
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
DATA = f"{PROJECT}/data/gwangyang_11ev"
WORK = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_sp_offset/rerun/full/work"     # computed files (NonLinLoc and pyrtdd runs, tables)
FIG_DIR = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_sp_offset/rerun/full/figures"          # every figure as 05_*.png (200 dpi) and 05_*.pdf
LIB = f"{PROJECT}/notebooks/lib"                  # nbfont.py and sp_offset.py

# --- inputs ---
HAND_TABLE_DIR = f"{DATA}/reference_supplement/manual_vs_phasenet"     # the user's hand-pick tables (server B, 2026-04-22)
SPOTCHECK_DIR = f"{DATA}/reference_supplement/manual_picks_provenance/sac_spotcheck"   # 16 SAC files copied read-only from server B
ML_PICKS_DIR = f"{DATA}/reference_supplement/manual_picks_provenance/ml_picks_20260422"  # absolute times of the tables' PhaseNet column
HAND_PICKS_UTC = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/runs/verify_sp_offset/rerun/full/picks_manual_utc.csv"       # OUTPUT of section 1.1: tidy hand picks in UTC
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
NEAR_STATION_LAYER_KM = (-5.0, 5.0)      # explanation (viii): lower Vp/Vs only above 5 km depth
SOURCE_LAYER_KM = (10.0, 15.0)           # explanation (ix): lower Vp/Vs only from 10 to 15 km depth
VPVS_SCAN = (1.50, 1.73, 0.005)          # Vp/Vs values tried in (viii) and (ix): start, stop, step

# --- picks and statistics ---
OUTLIER_ABS_RES_S = 1.0       # gross mis-pick: |(pick - HypoDD origin) - grid travel time| > 1.0 s
N_BOOT = 2000                 # bootstrap samples everywhere (stations resampled with replacement)
SEED = 620                    # random seed of all bootstraps
MIN_PAIRS_PER_EVENT = 3       # Figure D: no median for an event with fewer S-P pairs
RUNMED_HALF_WIDTH_KM = 5.0    # running median of Figure C: 10 km wide windows ...
RUNMED_STEP_KM = 1.0          # ... every 1 km ...
RUNMED_MIN_N = 8              # ... with at least 8 pairs
DEPTH_SCAN_KM = (2.0, 30.0, 0.05)    # explanation (iv): depths tried (start, stop, step)
DIST_BINS_KM = [0, 30, 60, 70, 101]  # summary: offset in distance ranges (60-70 km = direct/head-wave crossover)

# --- waveforms ---
BAND_HZ = (5.0, 20.0)         # band-pass
FILTER_CORNERS = 4
FILTER_ZEROPHASE = False      # causal (one pass): cannot move energy ahead of an onset
TAPER_FRACTION = 0.05
EXAMPLE_EVENT = "20210827220322"     # the ML 2.2 event (Figure A and the first record section)

# --- NonLinLoc (identical for every run) ---
NLLOC = dict(trans_lat=35.0000, trans_lon=127.7286, time_root=f"{NLL_TIME_DIR}/kim1983",
             oct_init=(10, 10, 10), oct_min_node_km=0.01, oct_max_nodes=20000, oct_num_scatter=5000,
             grid_n=(61, 61, 61), grid_orig=(-15.0, -15.0, -1.0), grid_d=(0.5, 0.5, 0.5),
             method="GAU_ANALYTIC", gau_sigma_s=0.1, gau_corr_len_km=0.0, gau2=None,
             qual2err=(0.1, 0.5, 1.0, 2.0, 99999.9))
NLLOC_PICK_ERR_S = {"P": 0.05, "S": 0.10}   # Gaussian pick errors written into the NLLOC_OBS files
NLLOC_MIN_PICKS = 8                         # hand picks are used for Figure F if every event has >= 8 P and >= 8 S
NEAR_NETWORK_KM = 35.0                      # Figure F, second row: only stations within this epicentral distance
INTERFACE_DEPTH_KM = 15.0                   # kim1983 layer boundary ...
INTERFACE_TOL_KM = 0.02                     # ... a NonLinLoc depth within 0.02 km of it counts as 'at the boundary'
""")

code(r"""
# imports, Helvetica, versions
import os
import sys
import glob
import json
import shutil
import importlib
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from IPython.display import display, Markdown
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
COL = {"hand": "#000000", "phasenet_plus": "#0072B2", "model": "#D55E00",
       "dl_phasenet_original": "#E69F00", "dl_phasenet_instance": "#56B4E9",
       "dl_eqtransformer_stead": "#009E73", "dl_phasenet_stead": "#CC79A7"}
LABEL = {"hand": "Hand picks", "phasenet_plus": "PhaseNet+",
         "dl_phasenet_original": "DL phasenet_original", "dl_phasenet_instance": "DL phasenet_instance",
         "dl_eqtransformer_stead": "DL eqtransformer_stead", "dl_phasenet_stead": "DL phasenet_stead"}
MARK = {"hand": "o", "phasenet_plus": "^", "dl_phasenet_original": "s", "dl_phasenet_instance": "D",
        "dl_eqtransformer_stead": "v", "dl_phasenet_stead": "P"}
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
  before HYPOINVERSE cut them to 0.01 s); and the four scdlrtpicker models. For the deep-learning pickers we take,
  as the relocation test of step 09 did, the picks inside the event window (origin − 5 s to + 60 s) and, per
  event, station and phase, the most confident one.
- **Gross-outlier rule** (one simple rule for every picker): a pick is dropped if its travel-time residual,
  |(pick time − HypoDD origin time) − grid travel time|, is larger than `OUTLIER_ABS_RES_S`. The residuals of the
  kept picks are a few tenths of a second, while the excluded picks are mostly off by seconds, e.g. an S wave picked
  as P (both ranges are printed below the table). The S-P table further below also gives the median offset without
  this exclusion, which shows that the rule does not drive the result. A station enters the S-P analysis of an event
  only if both its P and its S pick survive.
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
print(f"Typical S-P error of one picker, from the hand/PhaseNet+ differences (1.4826 x MAD / sqrt 2): {PICK_NOISE_SP:.3f} s")
""")

md(r"""
### 1.3 How much does the model S-P depend on our choices?

The model S-P of a station depends on the assumed hypocenter and velocity model. Besides the main choice (kim1983
grids from each event's own HypoDD hypocenter) we recompute it

- (a) from the cluster centroid, one point for all events;
- (b) from a P-only NonLinLoc location of each event (hand P picks, all stations, the settings of section 7): a
  hypocenter that uses no S pick at all;
- (c) with the other Korean model, kim2011, as HYPOINVERSE used it (its own P and S layers), by an exact 1-D
  calculation;
- (d) with all stations at sea level (as HYPOINVERSE and HypoDD had them), by the same 1-D calculation;

and, for reference, (e) with kim1983 P speeds but HYPOINVERSE's own kim1983 S model, and (f) the exact 1-D
calculation of the grid model itself (a check of the grids). The exact 1-D calculation (fastest of the direct ray
and the head waves) is copied verbatim from `install/02_validate_nll_grids.py`, where it was checked against a
brute-force minimisation.
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
from the hand P pick. The three components (vertical Z, north N, east E) are band-passed 5-20 Hz, and each trace is
scaled to its own largest value in the panel.

The filter is causal (one pass). Such a filter can only delay an onset, by a few hundredths of a second, and never
shows energy before it, so it cannot make the S wave look early. Marks: hand P and hand S picks (black), the
PhaseNet+ S pick (blue), and the model S time = hand P pick + model S-P (vermillion).
""")

code(r"""
# Figure A: nearest and farthest station of the ML 2.2 event that has both hand picks
hA = SP[(SP.source == "hand") & (SP.kma_id == EXAMPLE_EVENT)].sort_values("dist_km")
PNP_A = PK[(PK.source == "phasenet_plus") & (PK.kma_id == EXAMPLE_EVENT) & ~PK.outlier].set_index(["station", "phase"]).ts
CHOSEN = [hA.iloc[0], hA.iloc[-1]]
print("Figure A stations (rule: nearest and farthest with both hand picks):",
      ", ".join(f"{c.station} ({c.sensor}, {c.dist_km:.1f} km)" for c in CHOSEN))
eA = EV.loc[EXAMPLE_EVENT]
fig, axes = plt.subplots(len(CHOSEN), 2, figsize=(9.2, 3.1 * len(CHOSEN)), gridspec_kw=dict(hspace=0.58, wspace=0.10))
for row, c in enumerate(CHOSEN):
    stf = so.bandpass(so.read_station(WAVEFORMS, EXAMPLE_EVENT, c.station), BAND_HZ[0], BAND_HZ[1],
                      FILTER_CORNERS, TAPER_FRACTION, FILTER_ZEROPHASE)
    t_pn_s = PNP_A.get((c.station, "S"), np.nan) - c.p_ts
    span = 1.0 if c.dist_km < 30 else 1.5
    for col, (w0, w1) in enumerate([(-0.6 * span, span), (c.sp_model - 1.2 * span, c.sp_model + span)]):
        ax = axes[row, col]
        for i, comp in enumerate(["Z", "N", "E"]):
            tr = so.component(stf, comp)
            t = tr.times("timestamp") - c.p_ts
            msk = (t >= w0) & (t <= w1)
            y = tr.data[msk].astype(float)
            ax.plot(t[msk], 2 - i + 0.42 * y / np.abs(y).max(), color="0.15", lw=0.6, zorder=2)
        if col == 0:
            ax.axvline(0.0, color=COL["hand"], lw=1.4, zorder=3)
        else:
            ax.axvline(c.sp_obs, color=COL["hand"], lw=2.6, ls="--", zorder=3)
            if np.isfinite(t_pn_s):
                ax.axvline(t_pn_s, color=COL["phasenet_plus"], lw=1.2, ls="-.", zorder=4)
            ax.axvline(c.sp_model, color=COL["model"], lw=2.0, zorder=3)
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
handles = [Line2D([], [], color=COL["hand"], lw=1.4), Line2D([], [], color=COL["hand"], lw=2.6, ls="--"),
           Line2D([], [], color=COL["phasenet_plus"], lw=1.2, ls="-."), Line2D([], [], color=COL["model"], lw=2.0)]
labels = ["Hand P pick", "Hand S pick", "PhaseNet+ S pick", "Model S time (hand P pick + model S-P)"]
so.legend_above(fig, axes, handles, labels, ncol=4)
FIGS = {}
FIGS["A"] = so.save_fig(fig, FIG_DIR, "05_A_single_station_traces")
plt.show()
""")

md(r"""
## 3. Figure B: record sections

Every station of an event, sorted by distance (nearest at the bottom). Each trace is the *horizontal vector
amplitude* √(N² + E²) of the 5-20 Hz causal-filtered north and east components: S waves are strongest on the
horizontal components, and this combination does not depend on how the sensors are oriented. (The orientation
metadata of these stations are nominal and not verified, so we do not rotate.) Each trace is scaled to its own
largest value between 0.5 s before the P pick and 2 s after the model S time.

- Left: aligned on each station's own P pick (the hand pick; where a station has no hand P pick, its PhaseNet+ P
  pick, marked with *). Vermillion ticks, joined by a dotted line, are the model S times; black ticks are hand S
  picks and blue ticks PhaseNet+ S picks.
- Right: the same traces re-aligned so that the model S time is at zero. If the model were right, the S onsets and
  the S picks would line up at zero; instead they line up to the left of it, near the median offset (dashed).

Events: the $\mathit{M}_{\mathrm{L}}$ 2.2 event, and the 2026 event with the most hand S-P pairs.
""")

code(r"""
# Figure B: record sections (horizontal vector amplitude), aligned on each station's own P pick
NH = SP[SP.source == "hand"].groupby("kma_id").size()
EV_2026 = max((k for k in NH.index if k.startswith("2026")), key=lambda k: NH[k])
RECORD_EVENTS = [EXAMPLE_EVENT, EV_2026]
print("record-section events:", RECORD_EVENTS)
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
    xR = (-2.0, 2.0)
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.0, 0.2 * n + 1.3), sharey=True,
                                   gridspec_kw=dict(width_ratios=[2.4, 1.0], wspace=0.04))
    for i, r in R.iterrows():
        stf = so.bandpass(so.read_station(WAVEFORMS, k, r.station), BAND_HZ[0], BAND_HZ[1], FILTER_CORNERS,
                          TAPER_FRACTION, FILTER_ZEROPHASE)
        t, a = so.horizontal_vector(stf)
        if t is None:
            axL.text(xL[0] + 0.1, i + 0.45, "No horizontal components", fontsize=6.5, va="center")
            continue
        tt = t - r.p_ref
        nm = (tt >= -0.5) & (tt <= r.sp_model + 2.0)
        a = a / a[nm].max()
        for ax, shift, (x0, x1) in ((axL, 0.0, xL), (axR, r.sp_model, xR)):
            x = tt - shift
            msk = (x >= x0) & (x <= x1)
            y = 0.85 * np.clip(a[msk], 0.0, 1.1)
            ax.fill_between(x[msk], i, i + y, color="0.75", lw=0, zorder=1)
            ax.plot(x[msk], i + y, color="0.3", lw=0.35, zorder=2)
            for val, colr, lw in ((r.s_hand - r.p_ref, COL["hand"], 1.6), (r.s_pnp - r.p_ref, COL["phasenet_plus"], 1.2),
                                  (r.sp_model, COL["model"], 1.6)):
                if np.isfinite(val):
                    ax.plot([val - shift] * 2, [i - 0.05, i + 0.95], color=colr, lw=lw, zorder=4)
        if not np.isfinite(r.s_hand):
            axR.text(xR[1] + 0.08, i + 0.45, "No S pick" if not np.isfinite(r.s_pnp) else "No hand S pick",
                     ha="left", va="center", fontsize=6.5, color="0.25", clip_on=False)
    axL.plot(R.sp_model, R.index + 0.45, color=COL["model"], lw=0.8, ls=":", zorder=3)
    axR.axvline(0.0, color=COL["model"], lw=1.0, zorder=3)
    axR.axvline(HAND_MED, color="k", lw=1.0, ls="--", zorder=3)
    axL.set_yticks(R.index + 0.45)
    axL.set_yticklabels([f"{s}{'' if fh else '*'}  {d:.0f} km" for s, fh, d in zip(R.station, R.p_from_hand, R.dist)], fontsize=6.5)
    axL.set_ylim(-0.3, n + 0.2)
    axL.set_xlim(*xL)
    axR.set_xlim(*xR)
    axL.set_xlabel("Time after the station's P pick (s)")
    axR.set_xlabel("Time after the model S time (s)")
    when = UTCDateTime(e.origin_ts).strftime("%Y-%m-%d %H:%M")
    axL.set_title(f"Event {int(e.n)}, {when} UTC, {ML} {e.ml:.1f}: aligned on each station's own P pick", loc="left")
    axR.set_title("Aligned on the model S time", loc="left")
    handles = [Line2D([], [], color=COL["hand"], lw=1.6), Line2D([], [], color=COL["phasenet_plus"], lw=1.2),
               Line2D([], [], color=COL["model"], lw=1.6), Line2D([], [], color="k", lw=1.0, ls="--")]
    labels = ["Hand S pick", "PhaseNet+ S pick", "Model S time (P pick + model S-P)", f"Median hand-pick offset ({HAND_MED:+.2f} s)"]
    so.legend_above(fig, [axL, axR], handles, labels, ncol=4)
    note = "* Aligned on the PhaseNet+ P pick (no hand P pick)."
    note += (" Not shown (no P pick at all): " + ", ".join(no_p) + ".") if no_p else ""
    fig.canvas.draw()
    bb = axL.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted())
    fig.text(bb.x0, bb.y0 - 0.004, note, ha="left", va="top", fontsize=7)
    FIGS[f"B{fig_no}"] = so.save_fig(fig, FIG_DIR, f"05_B{fig_no}_record_section_{k}")
    plt.show()
    print(f"event {k}: {n} traces ({int((~R.p_from_hand).sum())} aligned on PhaseNet+ P), "
          f"{int(R.s_hand.notna().sum())} hand S picks; stations without any P pick: {len(no_p)}")
""")

# =====================================================================================================
md(r"""
## 4. Figure C: S-P against distance, all 11 events

- (a) Observed S-P times (hand picks: circles; PhaseNet+: triangles) and the kim1983 model curve (exact 1-D, at
  the centroid depth, station at the median station elevation). At this scale a difference of a few tenths of a
  second is hard to see, which is why (b) shows the difference itself.
- (b) Observed minus model S-P of every pair (model from the grids and each event's own hypocenter), with the
  running median of the hand picks (10 km windows, at least `RUNMED_MIN_N` pairs) and its 95% band (bootstrap of
  the median within each window), the running median of the PhaseNet+ picks, zero (the model) and the overall
  median of the hand picks. The dotted line marks the distance where the first-arriving wave changes from the
  direct wave to the head wave along the 15 km boundary (exact 1-D model, station at sea level).
- (c) The median offset of each station over all events (hand picks), by sensor: broadband (HH),
  accelerometer (HG), short period (EL).
""")

code(r"""
# Figure C: S-P against distance
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
RM_H = so.running_median(dH.dist_km.to_numpy(), dH.offset.to_numpy(), CENTERS, RUNMED_HALF_WIDTH_KM, RUNMED_MIN_N, N_BOOT, RNG)
RM_P = so.running_median(dP.dist_km.to_numpy(), dP.offset.to_numpy(), CENTERS, RUNMED_HALF_WIDTH_KM, RUNMED_MIN_N, N_BOOT, RNG)
STMED = dH.groupby("station").agg(dist_km=("dist_km", "median"), median_offset_s=("offset", "median"),
                                  n=("offset", "size"), sensor=("sensor", "first")).sort_values("dist_km")
STMED.to_csv(f"{WORK}/station_median_offsets_hand.csv")

fig, axes = plt.subplots(3, 1, figsize=(8.0, 10.0), sharex=True, gridspec_kw=dict(height_ratios=[1.1, 1.3, 0.9], hspace=0.08))
ax = axes[0]
ax.plot(dP.dist_km, dP.sp_obs, MARK["phasenet_plus"], ms=3.4, mfc="none", mec=COL["phasenet_plus"], mew=0.7, zorder=2)
ax.plot(dH.dist_km, dH.sp_obs, MARK["hand"], ms=3.2, mfc="none", mec=COL["hand"], mew=0.7, zorder=3)
ax.plot(XS, CURVE, color=COL["model"], lw=1.5, zorder=4)
ax.set_ylabel("S-P time (s)")
ax.set_ylim(0, 13)
ax.text(0.015, 0.95, "(a)", transform=ax.transAxes, va="top")
ax = axes[1]
ax.plot(dP.dist_km, dP.offset, MARK["phasenet_plus"], ms=3.2, mfc="none", mec=COL["phasenet_plus"], mew=0.6, alpha=0.55, zorder=2)
ax.plot(dH.dist_km, dH.offset, MARK["hand"], ms=3.0, mfc="none", mec="0.3", mew=0.6, alpha=0.75, zorder=2)
ax.fill_between(RM_H.center_km, RM_H.lo, RM_H.hi, color="0.55", alpha=0.45, lw=0, zorder=3)
ax.plot(RM_H.center_km, RM_H["median"], color="k", lw=1.8, zorder=4)
ax.plot(RM_P.center_km, RM_P["median"], color=COL["phasenet_plus"], lw=1.3, ls="--", zorder=4)
ax.axhline(0.0, color=COL["model"], lw=1.4, zorder=3)
ax.axhline(HAND_MED, color="k", lw=1.0, ls="-.", zorder=3)
ax.set_ylabel("Observed minus model S-P (s)")
ax.set_ylim(-1.0, 0.45)
ax.text(0.015, 0.95, "(b)", transform=ax.transAxes, va="top")
ax = axes[2]
SENS_MARK = {"HH": ("o", "0.15"), "HG": ("s", "white"), "EL": ("D", "#E69F00")}
for sen, (mk, fc) in SENS_MARK.items():
    q = STMED[STMED.sensor == sen]
    ax.plot(q.dist_km, q.median_offset_s, mk, ms=5.0, mfc=fc, mec="k", mew=0.9, zorder=3)
ax.axhline(0.0, color=COL["model"], lw=1.4, zorder=2)
ax.axhline(HAND_MED, color="k", lw=1.0, ls="-.", zorder=2)
ax.set_ylabel("Station median offset (s)")
ax.set_xlabel("Epicentral distance (km)")
ax.set_ylim(-0.75, 0.15)
ax.text(0.015, 0.93, "(c)", transform=ax.transAxes, va="top")
for a in axes:
    a.axvline(XOVER, color="0.35", lw=1.0, ls=":", zorder=1)
axes[0].text(XOVER - 0.8, 12.6, "Direct wave first", ha="right", va="top", fontsize=7.5, color="0.25")
axes[0].text(XOVER + 0.8, 12.6, "Head wave first", ha="left", va="top", fontsize=7.5, color="0.25")
axes[0].set_xlim(0, 101)
handles = [Line2D([], [], ls="none", marker="o", mfc="none", mec="k"), Line2D([], [], ls="none", marker="^", mfc="none", mec=COL["phasenet_plus"]),
           Line2D([], [], color=COL["model"], lw=1.5), Line2D([], [], color="k", lw=1.8), Patch(color="0.55", alpha=0.45, lw=0),
           Line2D([], [], color=COL["phasenet_plus"], lw=1.3, ls="--"), Line2D([], [], color="k", lw=1.0, ls="-."),
           Line2D([], [], color="0.35", lw=1.0, ls=":"), Line2D([], [], alpha=0.0)] + \
          [Line2D([], [], ls="none", marker=mk, mfc=fc, mec="k") for mk, fc in SENS_MARK.values()]
labels = ["Hand picks", "PhaseNet+", "Model kim1983 (zero in b and c)", "Running median, hand picks", "95% band of that median",
          "Running median, PhaseNet+", f"Overall median, hand picks ({HAND_MED:+.2f} s)", "Direct/head-wave crossover", " "] + \
         [f"Station median, {s} sensor" for s in SENS_MARK]
so.legend_above(fig, axes, handles, labels, ncol=4)
FIGS["C"] = so.save_fig(fig, FIG_DIR, "05_C_sp_vs_distance")
plt.show()

bins = pd.cut(SP.dist_km, DIST_BINS_KM, right=False)
rows = []
for src in ("hand", "phasenet_plus"):
    for b, g in SP[SP.source == src].groupby(bins[SP.source == src], observed=True):
        med, lo, hi = so.cluster_bootstrap_median(g.offset, g.station, N_BOOT, RNG)
        rows.append({"Picks": LABEL[src], "Distance (km)": f"{b.left:g}-{b.right:g}", "Pairs": len(g),
                     "Median offset (s)": round(med, 3), "95% CI (s)": f"{lo:+.3f} to {hi:+.3f}"})
DBIN = pd.DataFrame(rows)
display(DBIN)
print(f"station medians (hand picks, stations with >= 3 pairs): {STMED[STMED.n >= 3].median_offset_s.min():+.2f} to "
      f"{STMED[STMED.n >= 3].median_offset_s.max():+.2f} s over {int((STMED.n >= 3).sum())} stations")
""")

# =====================================================================================================
md(r"""
## 5. Figure D: the offset event by event, for every picker

For each event: the median offset over its stations, with a 95% interval from `N_BOOT` bootstrap samples
(the event's stations resampled with replacement; no value when fewer than `MIN_PAIRS_PER_EVENT` pairs). Events are
in time order; the numbers 1-11 are used again in Figure F. The dashed line and the grey band are the overall
median of the hand picks and its 95% interval; zero (vermillion) is the model.
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

fig, ax = plt.subplots(figsize=(10.5, 4.3))
ax.axhspan(HAND_CI[0], HAND_CI[1], color="0.86", lw=0, zorder=0)
ax.axhline(HAND_MED, color="k", lw=1.0, ls="--", zorder=1)
ax.axhline(0.0, color=COL["model"], lw=1.4, zorder=1)
offs = np.linspace(-0.3, 0.3, len(SOURCES))
for j, src in enumerate(SOURCES):
    q = PEV[PEV.source == src].set_index("kma_id").loc[EVL.index]
    x = np.arange(len(EVL)) + offs[j]
    ax.errorbar(x, q["median"], yerr=[q["median"] - q.lo, q.hi - q["median"]], fmt=MARK[src], color=COL[src],
                mfc=COL[src] if src == "hand" else "white", mec=COL[src], ms=5, mew=1.0, elinewidth=0.9, capsize=2, zorder=3)
n_2021 = int(sum(k.startswith("2021") for k in EVL.index))
ax.axvline(n_2021 - 0.5, color="0.5", lw=0.8, ls=":", zorder=1)
ax.set_xticks(np.arange(len(EVL)))
ax.set_xticklabels([f"{int(e.n)}\n{UTCDateTime(e.origin_ts).strftime('%Y-%m-%d')}\n{UTCDateTime(e.origin_ts).strftime('%H:%M')}\n{ML} {e.ml:.1f}"
                    for _, e in EVL.iterrows()], fontsize=7.5)
ylo = min(-0.6, float(np.nanmin(PEV.lo)) - 0.05)
ax.set_ylim(ylo, 0.1)
for i, k in enumerate(EVL.index):
    nh = int(PEV[(PEV.source == "hand") & (PEV.kma_id == k)].n.iloc[0])
    ax.text(i, ylo + 0.02, f"n = {nh}", ha="center", va="bottom", fontsize=7, color="0.25")
ax.set_xlim(-0.6, len(EVL) - 0.4)
ax.set_ylabel("Median observed minus model S-P (s)")
ax.set_xlabel("Event (number, date and time in UTC, KMA magnitude); n = hand-pick S-P pairs")
handles = [Line2D([], [], ls="none", marker=MARK[s], mfc=COL[s] if s == "hand" else "white", mec=COL[s], color=COL[s]) for s in SOURCES]
handles += [Line2D([], [], color="k", lw=1.0, ls="--"), Patch(color="0.86", lw=0), Line2D([], [], color=COL["model"], lw=1.4)]
labels = [LABEL[s] for s in SOURCES] + [f"Overall median, hand picks ({HAND_MED:+.3f} s)", "95% interval of the overall median", "Model (zero offset)"]
so.legend_above(fig, ax, handles, labels, ncol=4)
FIGS["D"] = so.save_fig(fig, FIG_DIR, "05_D_offset_per_event")
plt.show()
tab = PEV.pivot(index="kma_id", columns="source", values="median").loc[EVL.index, SOURCES].rename(columns=LABEL)
tab.index = [f"{int(EV.loc[k, 'n'])}  {k}" for k in tab.index]
display(tab.round(3))
EVSPREAD = PEV[PEV.source == "hand"]["median"]
print(f"hand picks: per-event medians from {EVSPREAD.min():+.3f} to {EVSPREAD.max():+.3f} s "
      f"(standard deviation {EVSPREAD.std():.3f} s over {EVSPREAD.notna().sum()} events)")
""")

# =====================================================================================================
md(r"""
## 6. Figure E: the Wadati diagram, and which simple explanation is needed

A *Wadati diagram* plots S-P against the P travel time. If the S wave always takes Vp/Vs times as long as the P
wave, the points fall on a straight line through the origin with slope Vp/Vs − 1. We fit one common slope and one
intercept per event; the per-event intercepts absorb any error of the origin times, so the slope (and hence Vp/Vs)
does not depend on them. The 95% interval comes from resampling stations (`N_BOOT` samples).

Then we compare simple explanations of the observed S-P times by the root-mean-square (RMS) of their S-P
residuals. The main table uses the hand picks; the same table for PhaseNet+ follows it.

- (i) the model as it is;
- (ii) one uniform Vp/Vs, fitted: S-P = (Vp/Vs − 1) × model P travel time;
- (iii) Vp/Vs 1.73 plus one constant, fitted;
- (iv) only the hypocenter depth changed, fitted: one shift for all events (iv-a), or a free depth per event (iv-b);
- (v) a uniform Vp/Vs and a constant, both fitted;
- (vi) the kim2011 model as HYPOINVERSE used it (nothing fitted);
- (vii) kim1983 with HYPOINVERSE's own S model (nothing fitted);
- (viii) kim1983 with a lower Vp/Vs only near the stations (above 5 km depth), fitted;
- (ix) kim1983 with a lower Vp/Vs only in a layer around the source (10-15 km depth), fitted;
- and, for reference, one constant per station: the floor that no single 1-D explanation can go below, because
  it also absorbs everything that differs from station to station.
""")

code(r"""
# section 6: Wadati fit (origin-time free) and the explanations
rows, WAD = [], {}
for src in ("hand", "phasenet_plus"):
    d = SP[SP.source == src]
    m, ce, res = so.wadati_fit(d.sp_obs.to_numpy(), d.tp_obs.to_numpy(), d.kma_id.to_numpy())
    bs = so.wadati_bootstrap(d.sp_obs, d.tp_obs, d.kma_id, d.station, N_BOOT, RNG)
    per_ev = []
    for k, g in d.groupby("kma_id"):
        if len(g) >= 5:
            per_ev.append(1.0 + np.polyfit(g.tp_obs, g.sp_obs, 1)[0])
    ce = pd.Series(ce)
    WAD[src] = dict(slope=m, vpvs=1.0 + m, lo=1.0 + np.percentile(bs, 2.5), hi=1.0 + np.percentile(bs, 97.5),
                    intercepts=ce, per_event_median=float(np.median(per_ev)), rms=float(np.sqrt(np.mean(res ** 2))))
    rows.append({"Picks": LABEL[src], "Pairs": len(d), "Vp/Vs (common slope + 1)": round(1.0 + m, 4),
                 "95% CI": f"{WAD[src]['lo']:.4f} to {WAD[src]['hi']:.4f}",
                 "Median of per-event Vp/Vs (events with >= 5 pairs)": round(WAD[src]["per_event_median"], 4),
                 "Per-event intercepts (s)": f"{ce.min():+.3f} to {ce.max():+.3f}", "Median intercept (s)": round(float(ce.median()), 3)})
display(pd.DataFrame(rows).set_index("Picks"))

ZS_SCAN = np.round(np.arange(DEPTH_SCAN_KM[0], DEPTH_SCAN_KM[1] + 1e-9, DEPTH_SCAN_KM[2]), 4)
KS_SCAN = np.round(np.arange(VPVS_SCAN[0], VPVS_SCAN[1] + 1e-9, VPVS_SCAN[2]), 4)


def depth_matrix(d):
    # model S-P from the grids at every trial depth, at each event's own epicenter
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


def layer_scan(d, z_top, z_bot):
    # kim1983 with one extra layer [z_top, z_bot] whose Vp/Vs is scanned (Vp unchanged)
    tops = np.array(sorted(set(KIM1983_TOPS + [z_top, z_bot])))
    vp = np.array([VP83[np.searchsorted(T83, z, side="right") - 1] for z in tops])
    k_layer = int(np.flatnonzero(np.isclose(tops, z_top))[0])
    zs_, zr_ = d.kma_id.map(EV.depth_km).to_numpy(), -d.station.map(STA.Elevation_m).to_numpy() / 1000.0
    tp = np.array([so.first_arrival(x, a, b, tops, vp)[0] for x, a, b in zip(d.dist_km, zs_, zr_)])
    best = None
    for kk in KS_SCAN:
        vs = vp / KIM1983_VPVS
        vs[k_layer] = vp[k_layer] / kk
        ts = np.array([so.first_arrival(x, a, b, tops, vs)[0] for x, a, b in zip(d.dist_km, zs_, zr_)])
        r = d.sp_obs.to_numpy() - (ts - tp)
        rms = float(np.sqrt(np.mean(r ** 2)))
        if best is None or rms < best[1]:
            best = (kk, rms, r)
    return best


def explanations(d):
    o, tpg, off, dist = d.sp_obs.to_numpy(), d.tp_grid.to_numpy(), d.offset.to_numpy(), d.dist_km.to_numpy()
    zev = d.kma_id.map(EV.depth_km).to_numpy()
    M = depth_matrix(d)
    out = {}
    out["(i) kim1983 as it is"] = (0, "none", off)
    k1 = np.sum(o * tpg) / np.sum(tpg ** 2)
    out["(ii) one uniform Vp/Vs"] = (1, f"Vp/Vs {1 + k1:.4f}", o - k1 * tpg)
    c3 = off.mean()
    out["(iii) Vp/Vs 1.73 + one constant"] = (1, f"constant {c3:+.3f} s", off - c3)
    dzs = np.round(np.arange(-12.0, 12.0 + 1e-9, 0.05), 3)
    rms_dz = [np.sqrt(np.mean((o - interp_depth(M, zev + dz)) ** 2)) for dz in dzs]
    dzb = float(dzs[int(np.argmin(rms_dz))])
    out["(iv-a) depth only, one shift"] = (1, f"shift {dzb:+.2f} km (negative = shallower)", o - interp_depth(M, zev + dzb))
    r4, shifts = np.empty(len(o)), []
    for k in np.unique(d.kma_id):
        ii = np.flatnonzero(d.kma_id.to_numpy() == k)
        rr = np.sqrt(np.mean((o[ii, None] - M[ii, :]) ** 2, axis=0))
        jb = int(np.argmin(rr))
        r4[ii] = o[ii] - M[ii, jb]
        shifts.append(ZS_SCAN[jb] - EV.loc[k, "depth_km"])
    out["(iv-b) depth only, one depth per event"] = (len(shifts), f"shifts {min(shifts):+.1f} to {max(shifts):+.1f} km", r4)
    A = np.column_stack([tpg, np.ones(len(o))])
    c5 = np.linalg.lstsq(A, o, rcond=None)[0]
    out["(v) uniform Vp/Vs + one constant"] = (2, f"Vp/Vs {1 + c5[0]:.4f}, constant {c5[1]:+.3f} s", o - A @ c5)
    out["(vi) kim2011 as HYPOINVERSE used it"] = (0, "none", o - d.sp_1d_kim2011.to_numpy())
    out["(vii) kim1983 with HYPOINVERSE's S model"] = (0, "none", o - d.sp_1d_hinv_s.to_numpy())
    kb, _, r8 = layer_scan(d, NEAR_STATION_LAYER_KM[0], NEAR_STATION_LAYER_KM[1])
    out["(viii) lower Vp/Vs near the stations only"] = (1, f"Vp/Vs {kb:.3f} above {NEAR_STATION_LAYER_KM[1]:g} km", r8)
    kb, _, r9 = layer_scan(d, SOURCE_LAYER_KM[0], SOURCE_LAYER_KM[1])
    out["(ix) lower Vp/Vs around the source only"] = (1, f"Vp/Vs {kb:.3f} at {SOURCE_LAYER_KM[0]:g}-{SOURCE_LAYER_KM[1]:g} km", r9)
    stc = d.groupby("station").offset.transform("median").to_numpy()
    out["Reference: one constant per station"] = (int(d.station.nunique()), "station medians", off - stc)
    rows = []
    for name, (npar, fit, r) in out.items():
        slope = np.polyfit(dist, r, 1)[0] * 100.0
        rows.append({"Explanation": name, "Free parameters": npar, "Fitted values": fit,
                     "RMS (s)": round(float(np.sqrt(np.mean(r ** 2))), 3), "Median residual (s)": round(float(np.median(r)), 3),
                     "Robust spread (s)": round(float(1.4826 * np.median(np.abs(r - np.median(r)))), 3),
                     "Trend (s per 100 km)": round(float(slope), 3)})
    return pd.DataFrame(rows).set_index("Explanation"), out


EXPL, EXPL_R = {}, {}
for src in ("hand", "phasenet_plus"):
    EXPL[src], EXPL_R[src] = explanations(SP[SP.source == src].reset_index(drop=True))
    EXPL[src].to_csv(f"{WORK}/explanations_{src}.csv")
    print(f"--- {LABEL[src]} ---")
    display(EXPL[src])
""")

code(r"""
# Figure E: Wadati diagram, what is left after removing 0.73 x P travel time, and the explanations
d = SP[SP.source == "hand"]
W = WAD["hand"]
C_MED = float(W["intercepts"].median())
k_model = KIM1983_VPVS - 1.0
fig = plt.figure(figsize=(10.4, 12.8))
gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 0.85, 1.0], hspace=0.40, wspace=0.28)
axa, axb = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
axc, axd = fig.add_subplot(gs[1, :]), fig.add_subplot(gs[2, :])

ax = axa
xx = np.array([0.0, 17.5])
ax.plot(d.tp_obs, d.sp_obs, "o", ms=3.0, mfc="none", mec="0.25", mew=0.6, zorder=2)
ax.plot(xx, W["slope"] * xx + C_MED, color="k", lw=1.4, zorder=3)
ax.plot(xx, k_model * xx, color=COL["model"], lw=1.4, zorder=3)
ax.set_xlim(0, 17.5)
ax.set_ylim(0, 13)
ax.set_xlabel("P travel time (s)")
ax.set_ylabel("S-P time (s)")
ax.set_title(f"(a) Wadati diagram, hand picks: Vp/Vs {W['vpvs']:.3f} ({W['lo']:.3f}-{W['hi']:.3f})", loc="left")
ins = ax.inset_axes([0.56, 0.08, 0.41, 0.40])
m = (d.tp_obs > 1.5) & (d.tp_obs < 6.5)
ins.plot(d.tp_obs[m], d.sp_obs[m], "o", ms=2.6, mfc="none", mec="0.25", mew=0.5)
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
ax.indicate_inset_zoom(ins, edgecolor="0.5")

ax = axb
y = d.sp_obs - k_model * d.tp_obs
ax.plot(d.tp_obs, y, "o", ms=3.0, mfc="none", mec="0.25", mew=0.6, alpha=0.8, zorder=2)
rmed = so.running_median(d.tp_obs.to_numpy(), y.to_numpy(), np.arange(1.0, 17.0, 0.5), 1.0, RUNMED_MIN_N, N_BOOT, RNG)
ax.fill_between(rmed.center_km, rmed.lo, rmed.hi, color="0.55", alpha=0.45, lw=0, zorder=3)
ax.plot(rmed.center_km, rmed["median"], color="k", lw=1.6, zorder=4)
ax.axhline(0.0, color=COL["model"], lw=1.4, zorder=3)
ax.axhline(C_MED, color="k", lw=1.0, ls="--", zorder=3)
ax.set_xlim(0, 17.5)
ax.set_ylim(-1.1, 0.5)
ax.set_xlabel("P travel time (s)")
ax.set_ylabel(f"S-P minus {k_model:.2f} × P travel time (s)")
ax.set_title("(b) What is left after the model's Vp/Vs is removed", loc="left")
handles = [Line2D([], [], ls="none", marker="o", mfc="none", mec="0.25"), Line2D([], [], color="k", lw=1.4),
           Line2D([], [], color=COL["model"], lw=1.4), Line2D([], [], color="k", lw=1.0, ls="--"), Patch(color="0.55", alpha=0.45, lw=0)]
labels = ["Hand-pick S-P pairs", "Fit: common slope, median intercept", f"Model: slope {k_model:.2f} through the origin",
          f"Median intercept ({C_MED:+.3f} s)", "Running median and its 95% band"]
so.legend_above(fig, [axa, axb], handles, labels, ncol=3)

E = EXPL["hand"]
pal = ["#D55E00", "#CC79A7", "#000000", "#999999", "#666666", "#332288", "#0072B2", "#882255", "#E69F00", "#009E73", "#56B4E9"]
ECOL = dict(zip(E.index, pal))
ax = axc
show = ["(i) kim1983 as it is", "(ii) one uniform Vp/Vs", "(iii) Vp/Vs 1.73 + one constant", "(iv-b) depth only, one depth per event",
        "(vi) kim2011 as HYPOINVERSE used it", "(viii) lower Vp/Vs near the stations only", "(ix) lower Vp/Vs around the source only"]
dist = d.dist_km.to_numpy()
ends = []
for name in show:
    rm = so.running_median(dist, EXPL_R["hand"][name][2], CENTERS, RUNMED_HALF_WIDTH_KM, RUNMED_MIN_N, 200, RNG)
    ax.plot(rm.center_km, rm["median"], color=ECOL[name], lw=1.6 if name.startswith("(iii)") else 1.2,
            ls="--" if name.startswith("(iv") else "-", zorder=3)
    ok = rm["median"].notna().to_numpy()
    ends.append([float(rm.center_km[ok].iloc[-1]), float(rm["median"][ok].iloc[-1]), name])
ends.sort(key=lambda t: t[1])
ys = [t[1] for t in ends]
for i in range(1, len(ys)):
    ys[i] = max(ys[i], ys[i - 1] + 0.065)
for (x_, y0, name), y_ in zip(ends, ys):
    ax.annotate(name.split(" ")[0], xy=(x_, y0), xytext=(104.0, y_), va="center", fontsize=7.5, color=ECOL[name],
                annotation_clip=False, arrowprops=dict(arrowstyle="-", lw=0.5, color=ECOL[name], shrinkA=0, shrinkB=2))
ax.axhline(0.0, color="0.4", lw=0.8, zorder=1)
ax.axvline(XOVER, color="0.35", lw=1.0, ls=":", zorder=1)
ax.set_xlim(0, 101)
ax.set_ylim(-0.6, 0.6)
ax.set_xlabel("Epicentral distance (km)")
ax.set_ylabel("Running median of the residual (s)")
ax.set_title("(c) Residual S-P left by each explanation, against distance (labels and colors as in d)", loc="left")

ax = axd
yy = np.arange(len(E))[::-1]
ax.barh(yy, E["RMS (s)"], color=[ECOL[nm] for nm in E.index], height=0.62, zorder=2)
for yv, (nm, r) in zip(yy, E.iterrows()):
    npar = int(r["Free parameters"])
    txt = f"{r['RMS (s)']:.3f} s; nothing fitted" if npar == 0 else \
        f"{r['RMS (s)']:.3f} s; {npar} free parameter{'' if npar == 1 else 's'}: {r['Fitted values']}"
    ax.text(r["RMS (s)"] + 0.004, yv, txt, va="center", fontsize=7)
ax.set_yticks(yy)
ax.set_yticklabels(E.index, fontsize=7.5)
ax.axvline(PICK_NOISE_SP, color="0.3", lw=1.0, ls=":", zorder=3)
ax.text(PICK_NOISE_SP + 0.004, -0.62, "Picking noise of one picker", fontsize=7, va="center", color="0.25")
ax.set_xlim(0, 0.80)
ax.set_ylim(-0.95, len(E) - 0.4)
ax.set_xlabel("RMS of the S-P residuals (s)")
ax.set_title("(d) Misfit of each explanation, hand picks", loc="left")
FIGS["E"] = so.save_fig(fig, FIG_DIR, "05_E_wadati_explanations")
plt.show()
""")

md(r"""
**Reading the explanation table.** Changing only the hypocenter depth cannot produce the offset: a shallower source
shortens S-P mainly at the nearby stations, whereas the observed shortening is similar at all distances, so (iv)
stays far worse than a constant even with a free depth per event. One uniform Vp/Vs (ii) is also worse than a
constant: lowering Vp/Vs shortens S-P in proportion to the travel time, too little nearby and too much far away.
A constant (iii), a constant plus a slightly different Vp/Vs (v), a lower Vp/Vs only near the stations (viii) or
only around the source (ix), and the kim2011 model with nothing fitted (vi) all fit about equally well. Their
remaining misfit is mostly station-to-station scatter (compare the reference "one constant per station"). The
S-P times therefore say that S-P is shortened by a roughly constant amount, but not **where** along the path: near
the source, near the stations, or in a picking convention that hand and machine picks share would all look the
same.
""")

# =====================================================================================================
md(r"""
## 7. Figure F: what the offset does to absolute locations (NonLinLoc)

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

Run 3 minus run 2 is the effect of the offset alone. All three are run twice: with **all stations**, and with
**only the stations within `NEAR_NETWORK_KM` km**, a small local network, where the S-P times carry much of the
depth information. The control file is printed below. In short: the search uses NonLinLoc's oct-tree method in a
30 km × 30 km × 30 km box around the cluster; the method is GAU_ANALYTIC, i.e. least squares with Gaussian errors,
the closest to HYPOINVERSE; pick errors are written into the observation files, so LOCQUAL2ERR is not used; there
are no station corrections. Uncertainty bars are 1σ from NonLinLoc's location covariance (for the horizontal
shift: the root-mean-square of the east and north standard deviations). NonLinLoc does not report an origin-time
uncertainty, so we propagate its location covariance and the pick errors through its own origin-time formula.
""")

code(r"""
# section 7: NonLinLoc runs (P only; P + S as picked; P + S with S shifted), all stations and nearby stations only
cnt = PK[(PK.source == "hand") & ~PK.outlier].groupby(["kma_id", "phase"]).size().unstack()
HAND_OK = bool(len(cnt) == len(EV) and (cnt.min() >= NLLOC_MIN_PICKS).all())
NLL_SRC = "hand" if HAND_OK else "phasenet_plus"
OTHER_SRC = "phasenet_plus" if NLL_SRC == "hand" else "hand"
print(f"hand picks per event: P {int(cnt.P.min())}-{int(cnt.P.max())}, S {int(cnt.S.min())}-{int(cnt.S.max())} "
      f"(rule: >= {NLLOC_MIN_PICKS} of each) -> Figure F uses {LABEL[NLL_SRC]}; {LABEL[OTHER_SRC]} is run as a check")
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
                         "ot_sig_s": b.ot_sig_s.to_numpy(), "ref_sig_z_km": a.sig_z_km.to_numpy(),
                         "ref_sig_h_km": np.sqrt((a.sig_x_km.to_numpy() ** 2 + a.sig_y_km.to_numpy() ** 2) / 2.0),
                         "ref_ot_sig_s": a.ot_sig_s.to_numpy()})


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
                         "Horizontal shift, mean (m)": round(float(sh.d_horiz_m.mean()), 0),
                         "Events shallower": int((sh.d_depth_km < 0).sum())})
NLLSUM = pd.DataFrame(rows)
display(NLLSUM)
at_if = NLL[(NLL.depth_km - INTERFACE_DEPTH_KM).abs() <= INTERFACE_TOL_KM]
print(f"NonLinLoc depths within {INTERFACE_TOL_KM} km of the {INTERFACE_DEPTH_KM:g} km layer boundary: {len(at_if)} of {len(NLL)}; by run:")
display(at_if.groupby(["source", "network", "run"]).size().rename("At the boundary").to_frame())
med_n = NLL.groupby(["source", "network", "run"])[["n_P", "n_S", "sig_z_km", "ot_sig_s", "rms_s"]].median().round(3)
display(med_n.rename(columns={"n_P": "Median P picks", "n_S": "Median S picks", "sig_z_km": "Median depth 1σ (km)",
                              "ot_sig_s": "Median origin-time 1σ (s)", "rms_s": "Median RMS (s)"}))
""")

code(r"""
# Figure F: shifts of runs 2 and 3 relative to the P-only run, per event
fig, axes = plt.subplots(len(NETS), 3, figsize=(11.2, 3.2 * len(NETS)), sharex=True, gridspec_kw=dict(hspace=0.34, wspace=0.32))
RUNSTYLE = {"p_s": ("#E69F00", "o", -0.16, "P and S as picked, minus P only"),
            "p_s_shifted": ("#0072B2", "s", 0.16, f"P and S with S shifted by +{S_SHIFT:.2f} s, minus P only")}
for row, (net, _) in enumerate(NETS):
    df = NLL[(NLL.source == NLL_SRC) & (NLL.network == net)]
    base = shifts(df, "p_s", "p_only")
    netname = "All stations" if net == "all" else f"Stations within {NEAR_NETWORK_KM:g} km"
    for col, (key, sig, ref, fac, ylab) in enumerate((("d_depth_km", "sig_z_km", "ref_sig_z_km", 1.0, "Depth change (km, + = deeper)"),
                                                     ("d_ot_s", "ot_sig_s", "ref_ot_sig_s", 1.0, "Origin-time change (s)"),
                                                     ("d_horiz_m", "sig_h_km", "ref_sig_h_km", 1000.0, "Horizontal shift (m)"))):
        ax = axes[row, col]
        if key == "d_horiz_m":
            ax.bar(base.n, fac * base[ref], bottom=0.0, width=0.62, color="0.86", lw=0, zorder=0)
        else:
            ax.bar(base.n, 2 * fac * base[ref], bottom=-fac * base[ref], width=0.62, color="0.86", lw=0, zorder=0)
        ax.axhline(0.0, color="0.3", lw=0.8, zorder=1)
        for run, (colr, mk, dx, _) in RUNSTYLE.items():
            sh = shifts(df, run, "p_only")
            err = fac * sh[sig].to_numpy()
            yerr = [np.minimum(err, sh[key].to_numpy()), err] if key == "d_horiz_m" else err   # a distance cannot go below 0
            ax.errorbar(sh.n + dx, sh[key], yerr=yerr, fmt=mk, color=colr, mfc=colr, mec=colr, ms=4.5,
                        elinewidth=0.9, capsize=2, zorder=3)
        ax.set_ylabel(ylab)
        ax.set_title(f"{netname}: {ylab.split(' (')[0].lower()}", loc="left")
        ax.set_xticks(np.arange(1, len(EV) + 1))
        if row == len(NETS) - 1:
            ax.set_xlabel("Event number (as in Figure D)")
handles = [Line2D([], [], ls="none", marker=RUNSTYLE[r][1], color=RUNSTYLE[r][0]) for r in RUNSTYLE] + [Patch(color="0.86", lw=0)]
labels = [RUNSTYLE[r][3] for r in RUNSTYLE] + ["1σ of the P-only location"]
so.legend_above(fig, axes, handles, labels, ncol=3)
FIGS["F"] = so.save_fig(fig, FIG_DIR, "05_F_nlloc_location_shifts")
plt.show()
""")

# =====================================================================================================
md(r"""
## 8. Figure G: double-difference relocation does not see the offset (pyrtdd)

Catalog-only relocation with pyrtdd, exactly as in the relocation test of step 09: ClusteringOptions
numEllipsoids 0, maxNeighbourDist 10 km, minNumNeigh 1, maxNumNeigh 0 (no limit), minNumPhases 1; SolverOptions
absLocConstraintStart/End 0, dampingFactorStart/End 0.01, default down-weighting by residual; the kim1983
NonLinLoc grids; start: all events at the HypoDD centroid (`event_centroid_start.csv`); picks: `phase.csv` (the
PhaseNet+ picks HypoDD used). It is run once as picked, and once with every S pick shifted by the same constant as
in section 7. Every option value actually used is saved in each run's `settings.json`.

**Why the difference should be zero.** A double difference is (travel time of event 1 − travel time of event 2) at
one station for one phase, observed minus predicted. A delay that is the same for the same station and phase in
both events cancels in that difference, so the equations, and hence the solution, do not change.
""")

code(r"""
# section 8: pyrtdd catalog-only relocation, as picked and with every S pick shifted
DD = {}
for name, shift in (("as_picked", 0.0), ("s_shifted", S_SHIFT)):
    d = f"{WORK}/pyrtdd/{name}"
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    shutil.copyfile(f"{RTDD_CATALOG}/station.csv", f"{d}/station.csv")
    shutil.copyfile(f"{RTDD_CATALOG}/event_centroid_start.csv", f"{d}/event.csv")
    ph = pd.read_csv(f"{RTDD_CATALOG}/phase.csv", keep_default_na=False, dtype=str)
    if shift != 0.0:
        ph["isotime"] = [(UTCDateTime(t) + shift).strftime("%Y-%m-%dT%H:%M:%S.%fZ") if ty == "S" else t
                         for t, ty in zip(ph.isotime, ph.type)]
    ph.to_csv(f"{d}/phase.csv", index=False)
    n_cl = so.relocate(d, NLL_TIME_DIR, dict(solution=name, s_shift_s=shift, picks="inputs/rtdd_catalog/phase.csv"))
    DD[name] = pd.read_csv(f"{d}/relocated-event.csv").set_index("id")
    print(f"{name}: {n_cl} cluster(s), {int((DD[name].relocated.astype(str).str.lower() == 'true').sum())} of {len(DD[name])} events relocated, "
          f"S picks shifted by {shift:+.3f} s ({int((ph.type == 'S').sum())} S picks, {int((ph.type == 'P').sum())} P picks)")
a, b = DD["as_picked"], DD["s_shifted"].loc[DD["as_picked"].index]
e, n, u = so.enu(b.latitude.to_numpy(), b.longitude.to_numpy(), b.depth.to_numpy(), a.latitude.to_numpy(), a.longitude.to_numpy(), a.depth.to_numpy())
dot = np.array([UTCDateTime(y) - UTCDateTime(x) for x, y in zip(a.isotime, b.isotime)])
DDDIFF = pd.DataFrame({"Event": a.index, "East difference (m)": e, "North difference (m)": n, "Up difference (m)": u,
                       "Origin-time difference (ms)": dot * 1e3})
display(DDDIFF.round(6).set_index("Event"))
DD_MAX_M = float(np.max(np.abs(np.r_[e, n, u])))
DD_MAX_MS = float(np.max(np.abs(dot)) * 1e3)
print(f"largest position difference {DD_MAX_M:.6f} m, largest origin-time difference {DD_MAX_MS:.6f} ms")
if os.path.exists(DL_CONTROL_RELOC):
    c = pd.read_csv(DL_CONTROL_RELOC).set_index("id").loc[a.index]
    e2, n2, u2 = so.enu(a.latitude.to_numpy(), a.longitude.to_numpy(), a.depth.to_numpy(), c.latitude.to_numpy(), c.longitude.to_numpy(), c.depth.to_numpy())
    DD_REPRO_M = float(np.max(np.abs(np.r_[e2, n2, u2])))
    print(f"reproducibility: 'as picked' vs the step-09 control relocation (same picks, same settings): largest difference {DD_REPRO_M:.6f} m")
else:
    DD_REPRO_M = np.nan
    print("!! the step-09 control relocation was not found; reproducibility not checked")
rms_cols = [c for c in ("startRms", "finalRms") if c in a.columns]
display(pd.DataFrame({f"{c} as picked": a[c] for c in rms_cols} | {f"{c} S shifted": b[c] for c in rms_cols}).round(3))
""")

code(r"""
# Figure G: the two pyrtdd solutions on top of each other, and their differences
ref_lat, ref_lon, ref_dep = a.latitude.mean(), a.longitude.mean(), a.depth.mean()
ea, na, ua = so.enu(a.latitude.to_numpy(), a.longitude.to_numpy(), a.depth.to_numpy(), ref_lat, ref_lon, ref_dep)
eb, nb, ub = so.enu(b.latitude.to_numpy(), b.longitude.to_numpy(), b.depth.to_numpy(), ref_lat, ref_lon, ref_dep)
fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.9), gridspec_kw=dict(width_ratios=[1.0, 1.0, 1.25], wspace=0.40))
for ax, (xa_, ya_, xb_, yb_, xl, yl, tt) in zip(axes[:2], ((ea, na, eb, nb, "East of the cluster mean (m)", "North of the cluster mean (m)", "(a) Map view"),
                                                          (ea, ua, eb, ub, "East of the cluster mean (m)", "Above the cluster mean (m)", "(b) East-depth section"))):
    ax.plot(xa_, ya_, "o", ms=9, mfc="none", mec="k", mew=1.1, zorder=2)
    ax.plot(xb_, yb_, "+", ms=9, color="#0072B2", mew=1.4, zorder=3)
    lim = 1.25 * max(np.abs(np.r_[xa_, ya_]).max(), 50.0)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.set_title(tt, loc="left")
ax = axes[2]
x = np.arange(1, len(a) + 1)
DMK = (("East", e, "o", "#E69F00"), ("North", n, "s", "#009E73"), ("Up", u, "^", "#CC79A7"))
for j, (lab, v, mk, fc) in enumerate(DMK):
    ax.plot(x + (j - 1) * 0.25, 1000.0 * v, mk, ms=4.5, mfc=fc, mec="k", mew=0.6, zorder=3)
ax.axhline(0.0, color="0.4", lw=0.8)
ax.set_ylim(-1.0, 1.0)
ax.set_xticks(x)
ax.set_xticklabels([str(i) for i in a.index])
ax.set_xlabel("Event number")
ax.set_ylabel("S shifted minus as picked (mm)")
ax.set_title("(c) Position differences", loc="left")
ax.text(0.5, 0.08, f"Largest: {1000 * DD_MAX_M:.3f} mm in position, {DD_MAX_MS:.3f} ms in origin time",
        transform=ax.transAxes, ha="center", fontsize=7.5)
handles = [Line2D([], [], ls="none", marker="o", mfc="none", mec="k", ms=8), Line2D([], [], ls="none", marker="+", color="#0072B2", ms=8, mew=1.4)] + \
          [Line2D([], [], ls="none", marker=mk, mfc=fc, mec="k", mew=0.6) for _, _, mk, fc in DMK]
labels = ["pyrtdd, picks as picked", f"pyrtdd, every S pick shifted by +{S_SHIFT:.2f} s", "East difference", "North difference", "Up difference"]
so.legend_above(fig, axes, handles, labels, ncol=5)
FIGS["G"] = so.save_fig(fig, FIG_DIR, "05_G_double_difference_unaffected")
plt.show()
""")

# =====================================================================================================
md(r"""
## 9. Comprehensive summary

The table below is computed from the results above (nothing is typed in). Intervals are 95% bootstrap intervals
with stations resampled (`N_BOOT` samples) unless stated otherwise; ± values are standard errors over the 11
events.
""")

code(r"""
# 9. key numbers (all computed above)
def ci_txt(med, lo, hi, nd=3):
    return f"{med:+.{nd}f} s (95% CI {lo:+.{nd}f} to {hi:+.{nd}f})"


K = []
K.append(("Hand picks: UTC reference established", f"SAC headers and absolute PhaseNet times agree within {REFT['Route 2 minus route 1 (µs)'].abs().max():.1f} µs (11 events); 16/16 header spot checks exact", "Section 1.1"))
K.append(("Hand picks", f"{len(HAND)} ({(HAND.phase == 'P').sum()} P, {(HAND.phase == 'S').sum()} S); gross outliers {int(PK[(PK.source == 'hand')].outlier.sum())}", "Section 1.2"))
for src in SOURCES:
    r = OFFS.loc[LABEL[src]]
    K.append((f"Median S-P offset, {LABEL[src]}", ci_txt(r['Median offset (s)'], r['95% CI low (s)'], r['95% CI high (s)']) + f"; {int(r['Pairs used'])} pairs, {int(r['Excluded (gross outlier)'])} excluded", "Figures C, D"))
K.append(("Per-event medians, hand picks", f"{EVSPREAD.min():+.3f} to {EVSPREAD.max():+.3f} s (SD {EVSPREAD.std():.3f} s, 11 events)", "Figure D"))
for _, r in DBIN[DBIN.Picks == "Hand picks"].iterrows():
    K.append((f"Offset at {r['Distance (km)']} km, hand picks", f"{r['Median offset (s)']:+.3f} s (95% CI {r['95% CI (s)']}), {r['Pairs']} pairs", "Figure C"))
K.append(("Hand minus PhaseNet+ (medians)", f"P {HVP.loc['P pick', 'Median (s)']:+.3f} s, S {HVP.loc['S pick', 'Median (s)']:+.3f} s, S-P {HVP.loc['S-P time', 'Median (s)']:+.3f} s (N = {HVP.loc['P pick', 'N']}, {HVP.loc['S pick', 'N']}, {HVP.loc['S-P time', 'N']})", "Section 1.2"))
for src in ("hand", "phasenet_plus"):
    w = WAD[src]
    K.append((f"Wadati Vp/Vs, {LABEL[src]}", f"{w['vpvs']:.4f} (95% CI {w['lo']:.4f} to {w['hi']:.4f}); per-event median {w['per_event_median']:.4f}; intercepts {w['intercepts'].min():+.2f} to {w['intercepts'].max():+.2f} s", "Figure E"))
for name, r in EXPL["hand"].iterrows():
    K.append((f"RMS {name}", f"{r['RMS (s)']:.3f} s ({r['Free parameters']} free; {r['Fitted values']})", "Figure E"))
for col, name in VARIANTS[1:6]:
    r = ROBUST.loc[name]
    K.append((f"Offset with model S-P from {name}", f"hand {r['Hand picks: median offset (s)']:+.3f} s ({r['Hand picks: 95% CI (s)']}); PhaseNet+ {r['PhaseNet+: median offset (s)']:+.3f} s", "Section 1.3"))
for _, r in NLLSUM[NLLSUM.Picks == LABEL[NLL_SRC]].iterrows():
    K.append((f"NonLinLoc, {r['Stations']} stations: {r['Comparison']}", f"depth {r['Depth change, mean ± SE (km)']} km; origin time {r['Origin-time change, mean ± SE (s)']} s; horizontal {r['Horizontal shift, mean (m)']:.0f} m", "Figure F"))
K.append(("NonLinLoc depths at the 15 km layer boundary", f"{len(at_if)} of {len(NLL)} locations", "Section 7"))
K.append(("pyrtdd: S shifted minus as picked", f"largest {1000 * DD_MAX_M:.3f} mm in position, {DD_MAX_MS:.3f} ms in origin time (11 events)", "Figure G"))
K.append(("pyrtdd reproducibility vs step 09 control", f"largest difference {DD_REPRO_M:.6f} m", "Section 8"))
KEY = pd.DataFrame(K, columns=["Quantity", "Value", "Where"])
KEY.to_csv(f"{WORK}/summary_key_numbers.csv", index=False)
with pd.option_context("display.max_colwidth", 200):
    display(KEY.set_index("Quantity"))
json.dump({"hand_median_offset_s": HAND_MED, "hand_ci95_s": HAND_CI, "s_shift_s": S_SHIFT,
           "offsets": {s: dict(OFFS.loc[LABEL[s], ["Median offset (s)", "95% CI low (s)", "95% CI high (s)", "Pairs used"]].astype(float)) for s in SOURCES},
           "wadati": {s: {k: (float(v) if not isinstance(v, pd.Series) else v.to_dict()) for k, v in WAD[s].items()} for s in WAD},
           "dd_max_diff_m": DD_MAX_M, "dd_max_diff_ms": DD_MAX_MS, "figures": FIGS},
          open(f"{WORK}/summary.json", "w"), indent=1, default=str)
print("saved:", f"{WORK}/summary_key_numbers.csv", f"{WORK}/summary.json")
""")

code(r"""
# 9. take-home messages, written from the computed numbers
hr, pr = OFFS.loc["Hand picks"], OFFS.loc["PhaseNet+"]
dl_meds = [OFFS.loc[LABEL[s], "Median offset (s)"] for s in SOURCES[2:]]
eh = EXPL["hand"]
near = DBIN[(DBIN.Picks == "Hand picks")].iloc[0]
far = DBIN[(DBIN.Picks == "Hand picks")].iloc[-1]
xo = DBIN[(DBIN.Picks == "Hand picks")].iloc[-2]
SH = {net: shifts(NLL[(NLL.source == NLL_SRC) & (NLL.network == net)], "p_s", "p_s_shifted") for net, _ in NETS}


def se(x):
    return float(np.std(np.asarray(x, float), ddof=1) / np.sqrt(len(x)))


npk = NLL[(NLL.source == NLL_SRC) & (NLL.network == "near") & (NLL.run == "p_s")]
r11 = ROBUST.loc[VARIANTS[3][1]]
rhs = ROBUST.loc[VARIANTS[5][1]]
ex = REFT.set_index("Event").loc[EXAMPLE_EVENT]
lines = [
    f"- **The hand picks now have exact UTC times.** The tables store seconds after the reference time of the server B SAC files, an earlier "
    f"HYPOINVERSE origin (e.g. {ex['Reference time (route 1, SAC header)']} for the {ML} 2.2 event); the SAC headers and the absolute April "
    f"picks agree within {REFT['Route 2 minus route 1 (µs)'].abs().max():.1f} µs. The reference of the local waveform copy would have made every "
    f"hand pick {REFT['Local minus true (ms)'].min():.0f}-{REFT['Local minus true (ms)'].max():.0f} ms late (section 1.1).",
    f"- **The S-P times are shorter than kim1983 predicts, in every picker.** Median offset {hr['Median offset (s)']:+.3f} s for the hand picks "
    f"(95% CI {hr['95% CI low (s)']:+.3f} to {hr['95% CI high (s)']:+.3f}, {int(hr['Pairs used'])} pairs), {pr['Median offset (s)']:+.3f} s for PhaseNet+ "
    f"and {min(dl_meds):+.3f} to {max(dl_meds):+.3f} s for the four deep-learning pickers (Figures C, D). Figures A and B show it on the waveforms: "
    f"the S energy starts before the model S time.",
    f"- **About the same in every event.** The per-event medians of the hand picks lie between {EVSPREAD.min():+.3f} and {EVSPREAD.max():+.3f} s (Figure D).",
    f"- **Not exactly constant with distance.** {near['Median offset (s)']:+.3f} s within {near['Distance (km)']} km, {xo['Median offset (s)']:+.3f} s at "
    f"{xo['Distance (km)']} km (around the direct/head-wave crossover) and {far['Median offset (s)']:+.3f} s at {far['Distance (km)']} km; station medians "
    f"vary from {STMED[STMED.n >= 3].median_offset_s.min():+.2f} to {STMED[STMED.n >= 3].median_offset_s.max():+.2f} s (Figure C).",
    f"- **Vp/Vs 1.73 still fits the slope.** The origin-time-free Wadati fit gives Vp/Vs {WAD['hand']['vpvs']:.3f} "
    f"(95% CI {WAD['hand']['lo']:.3f}-{WAD['hand']['hi']:.3f}) for the hand picks and {WAD['phasenet_plus']['vpvs']:.3f} for PhaseNet+; the data "
    f"run parallel to the model line, shifted by about {C_MED:+.2f} s (Figure E a, b).",
    f"- **A constant is needed; a depth change or one Vp/Vs is not enough.** RMS: model as is {eh.loc['(i) kim1983 as it is', 'RMS (s)']:.3f} s; "
    f"one uniform Vp/Vs {eh.loc['(ii) one uniform Vp/Vs', 'RMS (s)']:.3f} s; depth only {eh.loc['(iv-b) depth only, one depth per event', 'RMS (s)']:.3f} s "
    f"even with a free depth per event; Vp/Vs 1.73 + constant {eh.loc['(iii) Vp/Vs 1.73 + one constant', 'RMS (s)']:.3f} s (Figure E d).",
    f"- **Where the constant comes from cannot be told from S-P times.** A lower Vp/Vs only near the stations "
    f"({eh.loc['(viii) lower Vp/Vs near the stations only', 'Fitted values']}, RMS {eh.loc['(viii) lower Vp/Vs near the stations only', 'RMS (s)']:.3f} s) "
    f"or only around the source ({eh.loc['(ix) lower Vp/Vs around the source only', 'Fitted values']}, RMS {eh.loc['(ix) lower Vp/Vs around the source only', 'RMS (s)']:.3f} s) "
    f"fits as well as the constant. The kim2011 model, whose upper crust has a lower Vp/Vs, fits with nothing adjusted: offset "
    f"{r11['Hand picks: median offset (s)']:+.3f} s, RMS {eh.loc['(vi) kim2011 as HYPOINVERSE used it', 'RMS (s)']:.3f} s. So the '0.27 s' belongs to "
    f"kim1983 with Vp/Vs 1.73, not to every model (section 1.3, Figure E c).",
    f"- **Absolute locations that use S are biased, and the station geometry decides where the bias goes.** With all stations, the S picks as "
    f"picked make the origin time {abs(SH['all'].d_ot_s.mean()):.3f} ± {se(SH['all'].d_ot_s):.3f} s "
    f"{'earlier' if SH['all'].d_ot_s.mean() < 0 else 'later'} than with S picks corrected by +{S_SHIFT:.3f} s, while the depth changes by only "
    f"{SH['all'].d_depth_km.mean():+.3f} ± {se(SH['all'].d_depth_km):.3f} km. With only the stations within {NEAR_NETWORK_KM:g} km (median "
    f"{int(npk.n_P.median())} P and {int(npk.n_S.median())} S picks), the hypocenter comes out "
    f"{abs(SH['near'].d_depth_km.mean()):.2f} ± {se(SH['near'].d_depth_km):.2f} km "
    f"{'shallower' if SH['near'].d_depth_km.mean() < 0 else 'deeper'} ({int((SH['near'].d_depth_km < 0).sum())} of {len(SH['near'])} events "
    f"shallower) and the origin time {abs(SH['near'].d_ot_s.mean()):.3f} ± {se(SH['near'].d_ot_s):.3f} s "
    f"{'later' if SH['near'].d_ot_s.mean() > 0 else 'earlier'} (Figure F).",
    f"- **Double-difference relocation is unaffected.** pyrtdd gives identical positions and origin times with and without the S shift "
    f"(largest differences {1000 * DD_MAX_M:.3f} mm and {DD_MAX_MS:.3f} ms; Figure G): a delay common to one station and phase cancels in a "
    f"difference of differences.",
]
display(Markdown("**Take-home messages**\n\n" + "\n".join(lines)))
""")

code(r"""
# 9. caveats and what to do, written from the computed numbers
cav = [
    f"- **Not a PhaseNet+ artifact, but possibly a shared picking convention.** Hand and PhaseNet+ picks agree closely "
    f"(medians {HVP.loc['P pick', 'Median (s)']:+.3f} s for P and {HVP.loc['S pick', 'Median (s)']:+.3f} s for S) and show the same offset, and so do four "
    f"other pickers. All of them could still put the S onset at the same early feature of the waveform, so a picking convention shared by "
    f"hand and machine picks is not excluded.",
    "- **The cause cannot be located along the path.** S-P times measure only the total along each path. A low Vp/Vs near the source, a low "
    "Vp/Vs under the stations, and a constant picking delay all shorten S-P by a similar amount at every station (Figure E).",
    f"- **The size of the offset depends on the reference model.** It is {HAND_MED:+.3f} s against kim1983 with Vp/Vs 1.73 (HypoDD and the "
    f"grids), {rhs['Hand picks: median offset (s)']:+.3f} s against kim1983 P speeds with HYPOINVERSE's own S speeds (3.40/3.79/4.58 km/s), and "
    f"{r11['Hand picks: median offset (s)']:+.3f} s against kim2011. The reference HYPOINVERSE locations (kim1983 run) therefore used S picks "
    f"whose S-P times are about {abs(rhs['Hand picks: median offset (s)']):.2f} s shorter than its own model predicts.",
    f"- **Station elevations.** The grids include the real station elevations; HYPOINVERSE and HypoDD used sea level. With stations at sea "
    f"level the offset is {ROBUST.loc[VARIANTS[4][1], 'Hand picks: median offset (s)']:+.3f} s instead of {HAND_MED:+.3f} s.",
    f"- **Layered-model artifact in Figure F.** {len(at_if)} of {len(NLL)} NonLinLoc depths sit at the 15 km layer boundary, where the misfit "
    f"of a layered model has a kink; there the depth does not move freely, so the depth shifts of those solutions (mostly all-station runs "
    f"with S as picked) may be underestimated.",
    f"- **The distance dependence is not perfectly flat** (larger offsets around the direct/head-wave crossover and beyond it), and the "
    f"station medians scatter with a standard deviation of {STMED[STMED.n >= 3].median_offset_s.std():.2f} s (stations with at least 3 pairs), "
    f"so a single constant is a first-order description only.",
    "- **What an analyst should do for absolute locations with S picks:** use S station corrections (e.g. NonLinLoc LOCDELAY or HYPOINVERSE "
    "station delays from the station medians of Figure C, file `station_median_offsets_hand.csv`), or at least one fitted S-P constant; or use "
    "a model with a lower Vp/Vs near the source or under the stations (kim2011 already behaves this way); and check depths against P-only "
    "locations, especially with few nearby stations. Double-difference relocation needs no change.",
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
  `runs/gwangyang/sp_offset/`: `sp_pairs.csv`, `per_event_offsets.csv`, `station_median_offsets_hand.csv`,
  `explanations_*.csv`, `nlloc_results.csv` with the NonLinLoc runs in `nlloc/`, the pyrtdd runs in `pyrtdd/`,
  `hand_pick_reference_times.csv`, `summary_key_numbers.csv`, `summary.json`; figures `notebooks/figures/05_*.png`
  and `.pdf`.
- Helper code: `notebooks/lib/sp_offset.py` (the 1-D travel-time functions are verbatim copies from
  `install/02_validate_nll_grids.py`; `relocate()` follows `runs/gwangyang/dlpicker/scripts/09_reloc.py`).
- Run time: a few minutes on one CPU (NonLinLoc about 130 locations, pyrtdd 2 relocations, bootstraps).
""")

# =====================================================================================================
for i, c in enumerate(CELLS):
    if c.cell_type == "code":
        compile(c.source, f"<cell {i}>", "exec")
nb = new_notebook(cells=CELLS, metadata={
    "kernelspec": {"name": "pyrtdd", "display_name": "pyrtdd", "language": "python"},
    "language_info": {"name": "python"}})
nbformat.write(nb, OUT)
print(f"wrote {OUT}: {len(CELLS)} cells ({sum(c.cell_type == 'code' for c in CELLS)} code); every code cell compiled")
