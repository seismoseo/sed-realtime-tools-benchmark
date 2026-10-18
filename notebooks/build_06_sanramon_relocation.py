# build_06_sanramon_relocation.py -- writes notebooks/06_sanramon_relocation.ipynb (markdown + code cells).
#
# Run in conda env 'pyrtdd':
#   python build_06_sanramon_relocation.py
# then execute (kernel 'pyrtdd'):
#   jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=pyrtdd \
#       --ExecutePreprocessor.timeout=1800 06_sanramon_relocation.ipynb
#
# The notebook only LOADS the result files of note 11 (docs/results/11_sanramon_relocation.md: runs/sanramon/) and the
# reference tables, and visualizes them; nothing is relocated. runs/sanramon/analysis/analyze_sanramon.py is imported
# as a module (its main() is not run) so that its loaders, comparison and plane fit are reused. Every emitted code
# cell is compiled with compile(..., 'exec') before the notebook is written; code cells carry '#' comments only (no
# docstrings). Helpers live in notebooks/lib/nb06_helpers.py. Markdown cells quote only parameter values ([[NAME]] or
# [[NAME:i]], filled from the parameter cell, which is executed once here); every result number is formatted from
# variables inside code cells.

import re

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker/notebooks/06_sanramon_relocation.ipynb"
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
# every setting of this notebook; nothing below changes these values (the markdown text quotes some of them)
import time as _time
T_START = _time.time()                            # the run time is printed at the very end
PROJECT = "/home/msseo/works/74.SeisComP_rtDD_DLpicker"
LIB = f"{PROJECT}/notebooks/lib"                  # nbfont.py (Helvetica) and nb06_helpers.py
FIG_DIR = f"{PROJECT}/notebooks/figures"          # every figure as 06_*.png and 06_*.pdf
FIG_DPI = 200                                     # resolution of the PNG files

# --- inputs (all read only) ---
SR = f"{PROJECT}/data/sanramon_2015"
TAB = f"{SR}/reference_tables"
MATCH_CSV = f"{TAB}/event_matching.csv"           # which event is in which catalog and in the benchmark box
RTDD_IN = f"{SR}/inputs/rtdd_catalog"             # rtDD input: event.csv (= NCSS routine start), phase.csv (analyst picks)
RUNS_DIR = f"{PROJECT}/runs/sanramon"
AN = f"{RUNS_DIR}/analysis"
ANALYZE_PY = f"{AN}/analyze_sanramon.py"          # imported as a module (main() not run): loaders, compare(), plane_fit()
METRICS_CSV = f"{AN}/metrics_vs_reference.csv"    # metrics a-c per solution and reference
PER_EVENT_CSV = f"{AN}/per_event_vs_reference.csv"   # the same per event
PLANE_CSV = f"{AN}/plane_fit.csv"                 # metric d (plane fits)
RUN_VS_RUN_CSV = f"{AN}/run_vs_run.csv"           # run against run
XCORR_STATS_CSV = f"{AN}/xcorr_stats.csv"         # cross-correlation counts (from the runs' caches and logs)
RESIDUAL_CSV = f"{AN}/residual_stats.csv"         # double-difference residuals, initial and final
RUNTIME_CSV = f"{AN}/runtime.csv"                 # time, memory and per-event absolute RMS of every run
DROPPED_CSV = f"{AN}/dropped_events.csv"          # metric e
POSITIONS_CSV = f"{AN}/positions_enu.csv"         # every solution's positions (east, north, up)
SUMMARY_JSON = f"{AN}/summary.json"               # event counts and the P1-vs-S1 lag comparison
TRIPLETS_CSV = f"{AN}/xcorr_triplets_P1_vs_S1.csv"   # every P1 and S1 correlation, side by side
PY_DIR = f"{RUNS_DIR}/pyrtdd/{{run}}"             # options.json, run_info.json, xcorr_cache.csv, processing/
SC_DIR = f"{RUNS_DIR}/scrtdd/{{run}}"             # run_options.json, run_summary.json, work/
DD_FILE = f"{RUNS_DIR}/pyrtdd/{{run}}/processing/cluster-1-{{stage}}-double-difference.csv"   # libhdd's own residuals
P1POS_CACHE = f"{RUNS_DIR}/pyrtdd/P1pos/inputs/xcorr_cache_positive_only.csv"   # P1's cache with negative CC made invalid

# --- runs and reference ---
PY_RUNS = ["P0", "P1", "P0n", "P1n", "P0a0", "P1a0", "P0d1", "P1d1", "P1pos", "P0rep"]
SC_RUNS = ["S0", "S1", "S0n", "S0rep", "S0nat"]
K_NEIGH = 10                                      # neighbors of the 'local' metric (must equal analyze_sanramon.K_NEIGH; asserted)
CC_MIN = 0.7                                      # rtDD accepts a correlation when |CC| >= this value
MAINSHOCK_ID = 72540765                           # the largest event; marked in Figure 1 (asserted = largest magnitude)
OUTLIER_ID = 72544210                             # the event that ends far apart in P1 and S1 (asserted from run_vs_run.csv)
SECTION_PLANE = "REF_LDEO"                        # its fitted strike (common events) sets the along/across-strike frame

# --- one color and marker per catalog, the same in every figure (Okabe-Ito; pyrtdd/scrtdd as in notebook 02:
#     P0 = R0, S0 = S0, P1 = R1f, S1 = S1; Paul Tol's colors for the sensitivity runs) ---
STYLE = {
    "REF_LDEO": dict(label="LDEO NCAeqDD v202112 (primary reference)", short="LDEO", color="#000000", marker="o", filled=True, ls="-"),
    "REF_NCEDC": dict(label="NCEDC DD (DD-RT; secondary reference)", short="NCEDC DD", color="#009E73", marker="D", filled=False, ls=":"),
    "NCSS": dict(label="NCSS routine (rtDD start)", short="NCSS routine", color="#808080", marker="o", filled=False, ls="-"),
    "P0": dict(label="pyrtdd P0 (catalog times only)", short="pyrtdd P0", color="#CC79A7", marker="X", filled=False, ls="-"),
    "S0": dict(label="scrtdd S0 (catalog times only)", short="scrtdd S0", color="#CC79A7", marker="P", filled=True, ls="--"),
    "P1": dict(label="pyrtdd P1 (with cross-correlation)", short="pyrtdd P1", color="#E69F00", marker="^", filled=False, ls="-"),
    "S1": dict(label="scrtdd S1 (with cross-correlation)", short="scrtdd S1", color="#0072B2", marker="s", filled=False, ls="--"),
    "P0n": dict(label="pyrtdd P0n (nearest-neighbor pairs)", short="pyrtdd P0n", color="#88CCEE", marker=">", filled=True, ls="-"),
    "P1n": dict(label="pyrtdd P1n (nearest-neighbor pairs)", short="pyrtdd P1n", color="#332288", marker="<", filled=True, ls="-"),
    "P0a0": dict(label="pyrtdd P0a0 (no absolute-location equations)", short="pyrtdd P0a0", color="#DDCC77", marker="v", filled=True, ls="-"),
    "P1a0": dict(label="pyrtdd P1a0 (no absolute-location equations)", short="pyrtdd P1a0", color="#882255", marker="v", filled=True, ls="-"),
    "P0d1": dict(label="pyrtdd P0d1 (no absolute equations, strong damping)", short="pyrtdd P0d1", color="#44AA99", marker="h", filled=True, ls="-"),
    "P1d1": dict(label="pyrtdd P1d1 (no absolute equations, strong damping)", short="pyrtdd P1d1", color="#999933", marker="p", filled=True, ls="-"),
    "P1pos": dict(label="pyrtdd P1pos (negative correlations dropped; diagnostic)", short="pyrtdd P1pos", color="#AA4499", marker="d", filled=True, ls="-"),
    "S0n": dict(label="scrtdd S0n (nearest-neighbor pairs)", short="scrtdd S0n", color="#88CCEE", marker="<", filled=False, ls="--"),
}
NEG_COLOR = "#D55E00"          # negative correlations (Figure 6)
MS = 6.0                       # marker size (points)
MEW = 1.1                      # marker edge width

# --- figures ---
F1_CATALOGS = ["NCSS", "P0", "P1", "REF_LDEO"]    # Figure 1 columns
F1_HALF_M = {"E": 1700, "N": 2200, "along": 2200, "across": 1700, "U": 2200}   # half-width of each panel window (m)
F1_IN_PER_KM = 0.62                               # Figure 1 scale (inches per km), the same in every panel
F1_SIZE_M1 = 4.0                                  # marker area (pt^2) of a magnitude-1 event ...
F1_SIZE_FACTOR = 2.2                              # ... multiplied by this per magnitude unit
F1_SIZE_NOMAG = 2.0                               # marker area of the events without a magnitude
F1_SIZE_LEGEND = [1, 2, 3]                        # magnitudes shown in the size legend
F1_STAR_SIZE = 160.0                              # marker area of the mainshock star
F1_CMAP = "viridis"                               # color = days since the first event
F2_SOLUTIONS = ["NCSS", "P0", "P1", "S1", "REF_NCEDC"]   # Figure 2, all against LDEO
F2_XLIM_M = (1.0, 10000.0)                        # logarithmic axis; smaller values are drawn at the left edge
F3_BEFORE, F3_AFTER = "NCSS", "P1"                # Figure 3
F3_LIM_M = (5.0, 6000.0)
F3_RATIO = 10.0                                   # dotted line: 'this many times closer'
F3_CMAP = "cividis"                               # color = magnitude
F4_ROWS = [("REF_LDEO", "common"), ("REF_LDEO", "own"), ("REF_NCEDC", "own"), ("NCSS", "common"), ("P0", "common"),
           ("S0", "common"), ("P1", "common"), ("S1", "common"), ("P0n", "common"), ("P1n", "common"),
           ("P0a0", "common"), ("P1a0", "common"), ("P0d1", "common"), ("P1d1", "common"), ("P1pos", "common")]
F4_CDF = ["NCSS", "P0", "P1", "S1", "REF_LDEO"]   # Figure 4 d: distance-from-plane distributions
F4_SECTIONS = ["NCSS", "P0", "P1", "S1", "REF_LDEO"]   # Figure 4 e-i: fault-normal sections
F4_HALF_M = {"across": 1000, "U": 2200}           # half-widths of the section windows (m)
F4_XLIM_DIST_M = (1.0, 5000.0)
F5_PAIRS = [("P0", "S0"), ("P1", "S1")]           # Figure 5: pyrtdd run, scrtdd run
F5_XLIM_M = (1e-4, 1e4)                           # smaller differences are drawn at the left edge
F5_SECTION_PAD_M = 700                            # margin of Figure 5 c around the plotted positions
F6_CC_BIN = 0.02                                  # Figure 6 b: bin width of the CC histogram
F6_LAG_MAX_MS = 500                               # Figure 6 c: axis limit (rtDD's maximum lag is 0.5 s)
F6_RES_LIM_MS = 300                               # Figure 6 d: residual axis limits (+-)
F6_RES_BIN_MS = 5                                 # Figure 6 d: bin width
F6_MAD_ROWS = [("P0", "catalog"), ("P1", "all"), ("P1", "catalog"), ("P1", "xcorr"), ("P1n", "xcorr"),
               ("P1a0", "xcorr"), ("P1d1", "xcorr"), ("P1pos", "xcorr")]
F7_RUNS = ["P0", "S0", "P0n", "P1", "S1", "P1n", "P1pos", "P0a0", "P1a0", "P0d1", "P1d1"]
F8_GROUPS = [("Start and secondary reference", ["NCSS", "REF_NCEDC"]),
             ("Catalog times only", ["P0", "S0", "P0n", "P0a0", "P0d1"]),
             ("With cross-correlation", ["P1", "S1", "P1n", "P1a0", "P1d1", "P1pos"])]

# --- consistency checks between files (tolerances) ---
TOL_POS_M = 0.001              # positions_enu.csv is written to 1 micrometer
TOL_METRIC_M = 0.01            # metrics_vs_reference.csv is written to 0.1 mm
TOL_PER_EVENT_M = 0.001        # per_event_vs_reference.csv is written to 1 mm
TOL_DEG = 0.051                # plane_fit.csv angles (rounded to 0.1 deg by the fit itself)
TOL_MS = 0.01                  # residual_stats.csv (ms)

# --- values printed in note 11, typed here ONLY as targets of the check in section 1.4 (no figure or text uses them):
#     (key, what, value as printed, tolerance = half a unit of the last printed digit, kind: 'eq' or 'le' = at most) ---
NOTE11_VALUES = [
    ("n_relocated", "Events relocated by every run", 680, 0, "eq"),
    ("n_dropped", "Events dropped (the same in every run)", 5, 0, "eq"),
    ("s0p0_med", "S0 vs P0: median 3-D distance (m)", 0.25, 0.005, "eq"),
    ("s0p0_rel_med", "S0 vs P0: median relative distance (m)", 0.01, 0.005, "eq"),
    ("s0p0_max", "S0 vs P0: largest 3-D distance (m)", 7.3, 0.05, "eq"),
    ("s1p1_med", "S1 vs P1: median 3-D distance (m)", 1.1, 0.05, "eq"),
    ("s1p1_rel_med", "S1 vs P1: median relative distance (m)", 0.45, 0.005, "eq"),
    ("s1p1_p90", "S1 vs P1: 90th percentile of the 3-D distance (m)", 2.5, 0.05, "eq"),
    ("s1p1_max_km", "S1 vs P1: largest 3-D distance (km)", 6.3, 0.05, "eq"),
    ("lag_identical", "P1 vs S1: identical lags", 324320, 0, "eq"),
    ("lag_identical_pct", "P1 vs S1: identical lags (%)", 97.9, 0.05, "eq"),
    ("lag_1ms", "P1 vs S1: lags one sample (1 ms) apart", 6935, 0, "eq"),
    ("lag_gt1", "P1 vs S1: lags more than 1 ms apart", 153, 0, "eq"),
    ("lag_gt10", "P1 vs S1: lags more than 10 ms apart", 125, 0, "eq"),
    ("cc_side", "P1 vs S1: measurements on opposite sides of the CC threshold", 62, 0, "eq"),
    ("P_pairs", "P phase pairs (P1)", 320207, 0, "eq"),
    ("P_meas", "P measured (P1)", 296378, 0, "eq"),
    ("P_acc", "P with |CC| >= 0.7 (P1, cache)", 173002, 0, "eq"),
    ("P_acc_log", "P above the threshold (P1, libhdd log; note: 'the logs agree')", 173002, 0, "eq"),
    ("P_pos", "P with CC >= +0.7", 136561, 0, "eq"),
    ("P_neg", "P with CC <= -0.7", 36441, 0, "eq"),
    ("S_pairs", "S phase pairs", 38267, 0, "eq"),
    ("S_meas", "S measured", 35030, 0, "eq"),
    ("S_acc", "S with CC >= 0.7", 19907, 0, "eq"),
    ("lag_pos", "Median |lag| of accepted positive P (ms)", 28, 0.5, "eq"),
    ("lag_neg", "Median |lag| of accepted negative P (ms)", 76, 0.5, "eq"),
    ("w_pos", "Positive-CC data keeping a weight in the final system (%)", 95, 0.5, "eq"),
    ("w_neg", "Negative-CC data keeping a weight in the final system (%)", 81, 0.5, "eq"),
    ("r_pos", "Median |final residual| of positive-CC data, all weights (ms)", 10.5, 0.05, "eq"),
    ("r_neg", "Median |final residual| of negative-CC data, all weights (ms)", 63, 0.5, "eq"),
    ("mad_xc_i", "P1 cross-correlation data: residual MAD, initial (ms)", 52.7, 0.05, "eq"),
    ("mad_xc_f", "P1 cross-correlation data: residual MAD, final (ms)", 13.2, 0.05, "eq"),
    ("mad_cat_i", "P1 catalog data: residual MAD, initial (ms)", 60.1, 0.05, "eq"),
    ("mad_cat_f", "P1 catalog data: residual MAD, final (ms)", 41.8, 0.05, "eq"),
    ("mad_pos_f", "P1pos cross-correlation data: residual MAD, final (ms)", 10.0, 0.05, "eq"),
    ("NCSS_rh", "NCSS vs LDEO: relative horizontal median (m)", 229, 0.5, "eq"),
    ("NCSS_rv", "NCSS vs LDEO: relative vertical median (m)", 394, 0.5, "eq"),
    ("NCSS_lh", "NCSS vs LDEO: local horizontal median (m)", 292, 0.5, "eq"),
    ("NCSS_lv", "NCSS vs LDEO: local vertical median (m)", 506, 0.5, "eq"),
    ("P0_rh", "P0 vs LDEO: relative horizontal median (m)", 142, 0.5, "eq"),
    ("P0_rv", "P0 vs LDEO: relative vertical median (m)", 134, 0.5, "eq"),
    ("P0_lh", "P0 vs LDEO: local horizontal median (m)", 137, 0.5, "eq"),
    ("P0_lv", "P0 vs LDEO: local vertical median (m)", 147, 0.5, "eq"),
    ("P1_rh", "P1 vs LDEO: relative horizontal median (m)", 97, 0.5, "eq"),
    ("P1_rv", "P1 vs LDEO: relative vertical median (m)", 105, 0.5, "eq"),
    ("P1_lh", "P1 vs LDEO: local horizontal median (m)", 51, 0.5, "eq"),
    ("P1_lv", "P1 vs LDEO: local vertical median (m)", 63, 0.5, "eq"),
    ("S1_rh", "S1 vs LDEO: relative horizontal median (m)", 98, 0.5, "eq"),
    ("S1_rv", "S1 vs LDEO: relative vertical median (m)", 106, 0.5, "eq"),
    ("NC_rh", "NCEDC DD vs LDEO: relative horizontal median (m)", 162, 0.5, "eq"),
    ("NC_rv", "NCEDC DD vs LDEO: relative vertical median (m)", 236, 0.5, "eq"),
    ("NC_lh", "NCEDC DD vs LDEO: local horizontal median (m)", 190, 0.5, "eq"),
    ("NC_lv", "NCEDC DD vs LDEO: local vertical median (m)", 241, 0.5, "eq"),
    ("P1pos_rv", "P1pos vs LDEO: relative vertical median (m)", 90, 0.5, "eq"),
    ("P1n_lh", "P1n vs LDEO: local horizontal median (m)", 41, 0.5, "eq"),
    ("P1n_lv", "P1n vs LDEO: local vertical median (m)", 55, 0.5, "eq"),
    ("P1n_rv", "P1n vs LDEO: relative vertical median (m)", 123, 0.5, "eq"),
    ("P1a0_rh", "P1a0 vs LDEO: relative horizontal median (m)", 63, 0.5, "eq"),
    ("P1_fr", "P1: events closer to LDEO than the NCSS start, relative 3-D (%)", 89, 0.5, "eq"),
    ("P1_fl", "P1: events closer to LDEO than the NCSS start, local (%)", 98, 0.5, "eq"),
    ("P0_fr", "P0: events closer to LDEO than the NCSS start, relative 3-D (%)", 80, 0.5, "eq"),
    ("P0_fl", "P0: events closer to LDEO than the NCSS start, local (%)", 93, 0.5, "eq"),
    ("P1_i3", "P1: improvement factor, relative 3-D", 2.9, 0.05, "eq"),
    ("P1_ilh", "P1: improvement factor, local horizontal", 5.8, 0.05, "eq"),
    ("P1_ilv", "P1: improvement factor, local vertical", 8.0, 0.05, "eq"),
    ("P0_U", "P0 centroid vs LDEO, up (m)", -2346, 0.5, "eq"),
    ("P1_U", "P1 centroid vs LDEO, up (m)", -2254, 0.5, "eq"),
    ("P0a0_U", "P0a0 centroid vs LDEO, up (m)", 4064, 0.5, "eq"),
    ("P1a0_U", "P1a0 centroid vs LDEO, up (m)", 4451, 0.5, "eq"),
    ("P0d1_U", "P0d1 centroid vs LDEO, up (m)", -427, 0.5, "eq"),
    ("P1d1_U", "P1d1 centroid vs LDEO, up (m)", -440, 0.5, "eq"),
    ("a0_up_min", "absLocConstraint-0 runs: upward drift, smaller of the two (km; note: 'drifts 4.1-4.5 km upward'), measured from the NCSS start", 4.1, 0.05, "eq"),
    ("a0_up_max", "absLocConstraint-0 runs: upward drift, larger of the two (km), measured from the NCSS start", 4.5, 0.05, "eq"),
    ("a0_vsL_min", "absLocConstraint-0 runs: centroid above LDEO's, smaller (km)", 4.1, 0.05, "eq"),
    ("a0_vsL_max", "absLocConstraint-0 runs: centroid above LDEO's, larger (km)", 4.5, 0.05, "eq"),
    ("z_LDEO", "Mean depth, LDEO (km)", 7.3, 0.05, "eq"),
    ("z_NCSS", "Mean depth, NCSS (km)", 7.7, 0.05, "eq"),
    ("z_NC", "Mean depth, NCEDC DD (km)", 6.6, 0.05, "eq"),
    ("z_def_min", "Mean depth, default-solver runs, smallest (km)", 9.5, 0.05, "eq"),
    ("z_def_max", "Mean depth, default-solver runs, largest (km)", 9.6, 0.05, "eq"),
    ("L_strike", "LDEO plane strike (deg)", 352.5, 0.05, "eq"),
    ("L_dip", "LDEO plane dip (deg)", 83.6, 0.05, "eq"),
    ("P1_strike", "P1 plane strike (deg)", 354.6, 0.05, "eq"),
    ("P1_dip", "P1 plane dip (deg)", 86.1, 0.05, "eq"),
    ("L_med", "LDEO median distance from the plane (m)", 121, 0.5, "eq"),
    ("P1_med", "P1 median distance from the plane (m)", 141, 0.5, "eq"),
    ("S1_med", "S1 median distance from the plane (m)", 135, 0.5, "eq"),
    ("P0_med", "P0 median distance from the plane (m)", 159, 0.5, "eq"),
    ("NCSS_med", "NCSS median distance from the plane (m)", 208, 0.5, "eq"),
    ("L_rms_noSE", "LDEO RMS distance from the plane without the 5 south-east events (m)", 291, 0.5, "eq"),
    ("P1_rms_noSE", "P1 RMS distance from the plane without the 5 south-east events (m)", 342, 0.5, "eq"),
    ("medctr_rt", "Change of any rtDD run's relative median when the median offset replaces the centroid (m; note: at most)", 10, 0, "le"),
    ("medctr_ncss", "The same for the NCSS start, largest (m)", 29, 0.5, "eq"),
    ("nb_L", "LDEO median neighbor spacing (m)", 107, 0.5, "eq"),
    ("nb_NC", "NCEDC DD median neighbor spacing (m)", 193, 0.5, "eq"),
    ("ldeo_eh", "LDEO median 95% horizontal error EH1 (m)", 13, 0.5, "eq"),
    ("out_zP1", "Event 72544210: depth in P1 (km)", 9.9, 0.05, "eq"),
    ("out_zS1", "Event 72544210: depth in S1 (km)", 3.8, 0.05, "eq"),
    ("out_zL", "Event 72544210: depth in LDEO (km)", 7.4, 0.05, "eq"),
    ("out_h", "Event 72544210: horizontal distance S1 - P1 (km; note: '1.2 km to the south')", 1.2, 0.05, "eq"),
    ("out_lagP", "Event 72544210: the differing S lag in P1 (ms)", 28, 0.5, "eq"),
    ("out_lagS", "Event 72544210: the differing S lag in S1 (ms)", -79, 0.5, "eq"),
    ("out_ndiff", "Event 72544210: lags that differ between P1 and S1 (note: 'the only lag that differs')", 1, 0, "eq"),
    ("out_ndiff1", "Event 72544210: lags that differ by more than 1 ms", 1, 0, "eq"),
    ("ev2_m", "Event 72541385: P1 vs S1 distance (m)", 137, 1.0, "eq"),
    ("rms_start", "Median per-event absolute RMS at the NCSS start (ms)", 235, 0.5, "eq"),
    ("rms_P0", "Median per-event absolute RMS after P0 (ms)", 243, 0.5, "eq"),
    ("rms_P1", "Median per-event absolute RMS after P1 (ms)", 247, 0.5, "eq"),
]
"""
exec(PARAM_CELL, PAR)

# =====================================================================================================
md(r"""
# San Ramon 2015: does rtDD reproduce a published double-difference catalog?

**What is checked.** SED's real-time double-difference relocator **rtDD** exists in two forms: **pyrtdd**, a Python
package around its C++ engine (libhdd), and **scrtdd**, the SeisComP module built on the same engine. Both were run
on the 2015 San Ramon swarm on the Calaveras fault (California): 685 events of the Northern California Seismic
System (**NCSS**), all public NCEDC data, with the NCSS analyst picks and the NCSS routine locations as the start.
The results are compared with two published double-difference catalogs: **LDEO NCAeqDD v202112** (a 2022 joint
re-inversion with cross-correlation; the primary reference) and the **NCEDC DD** catalog (automatic real-time DD-RT
solutions for 2015; the secondary reference). All runs and comparisons are done (note
`docs/results/11_sanramon_relocation.md`; inputs in `docs/sanramon_inputs.md`, waveform checks in
`docs/sanramon_waveforms.md`). This notebook only **loads** the result files and shows them; nothing is relocated.

**Terms used throughout, in plain words**

- *Relocation, double difference*: an earthquake's position is found from wave arrival times. Double-difference
  relocation uses, for each pair of nearby events and each station, the *difference* of their travel times. Errors
  shared by both events (the path to the station, the velocity model) cancel, so the events' positions *relative to
  each other* come out much better than their absolute positions.
- *Catalog differential times*: travel-time differences computed from the picked arrival times.
  *Cross-correlation*: the same differences measured by sliding one event's waveform over the other's until they
  match best; much more precise for similar events. The *lag* is the shift that matches best; it corrects the
  picked difference.
- *CC (correlation coefficient)*: how similar two waveforms are, from -1 (mirror images: the same shape upside
  down) through 0 to +1 (identical shape). rtDD keeps a measurement when |CC| ≥ [[CC_MIN]], so it also keeps
  mirror-image (negative) matches.
- *Centroid*: the average position of all events of one catalog.
- ***Relative* position**: each event's position minus its own catalog's centroid. Comparing relative positions
  compares the *shape* of the swarm and ignores where the swarm as a whole sits.
- ***Local* geometry**: for each event, the arrows (vectors) from it to its [[K_NEIGH]] nearest neighbors in the
  LDEO catalog. The same arrows are drawn in the other catalog, and the *local* difference is the median length of
  the difference between the two sets of arrows. It asks: are the event's immediate neighbors in the same
  directions and at the same distances? It is not affected by a slow bending or stretching of the whole swarm.
- *Horizontal (H)* and *vertical (V)*: the map-view part and the depth part of a difference.
- *Median*: half of the events are above, half below. *90th percentile (p90)*: 90% of the events are below.
- *Cumulative distribution*: for each value on the horizontal axis, the share of events whose value is at most
  that. A curve further left means smaller differences.
- *Fault plane fit*: the flat plane that passes closest to all events of a catalog; its *strike* is its compass
  direction, its *dip* its steepness (90° = vertical). The distance of each event from that plane measures how thin
  the swarm is.
- *absLocConstraint* and *damping*: two rtDD solver settings. absLocConstraint adds, for every event, equations that
  tie it to its own absolute arrival times (by default on). Damping penalizes large position changes in each
  iteration. Without absolute equations, only the damping keeps the swarm as a whole from sliding.
- *Residual*: what the final positions still fail to explain of a measured double difference. *MAD*: the median
  absolute deviation of the residuals, a robust measure of their spread.

**The catalogs and runs** (settings read from the run folders in section 1.1)

| name | program | what it is |
|---|---|---|
| NCSS routine | | the NCSS routine locations: the start of every rtDD run |
| LDEO | | LDEO NCAeqDD v202112.1, the primary reference |
| NCEDC DD | | NCEDC DD (DD-RT) catalog, the secondary reference |
| P0, S0 | pyrtdd, scrtdd | catalog differential times only, rtDD defaults: as a user would run rtDD on a regional catalog |
| P1, S1 | pyrtdd, scrtdd | P0/S0 plus cross-correlation (pyrtdd through the project's filtering proxy, see note 11 section 2) |
| P0n, S0n, P1n | pyrtdd, scrtdd | event pairs from nearest neighbors instead of rtDD's default ellipsoids |
| P0a0, P1a0 | pyrtdd | no absolute-location equations |
| P0d1, P1d1 | pyrtdd | no absolute-location equations and strong damping |
| P1pos | pyrtdd | diagnostic: P1 with its negative correlations turned back into catalog times (not an rtDD option) |
| P0rep, S0rep, S0nat | pyrtdd, scrtdd | checks: identical repeats, and scrtdd's built-in grid reader |

**Contents**

0. Parameters
1. Loading; runs and settings; dropped events; cross-file consistency checks; note 11 against the files
2. Figure 1: the swarm in four catalogs
3. Figure 2: how far each event is from LDEO
4. Figure 3: before and after, event by event
5. Figure 4: the fault plane
6. Figure 5: pyrtdd and scrtdd
7. Figure 6: cross-correlation measurements and residuals
8. Figure 7: absolute position (a caveat)
9. Figure 8: sensitivity runs
10. Comprehensive summary
""")

md(r"""
## 0. Parameters

Every setting of this notebook is in the next cell: input files, the color and marker of each catalog, figure
windows and bins, the tolerances of the consistency checks, and (at the end) the values printed in note 11 that
section 1.4 checks against the files. Nothing further down changes them.
""")

code(PARAM_CELL)

code(r"""
# imports, Helvetica, versions, plotting style
import os
import sys
import textwrap
import importlib
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.colors import Normalize
from matplotlib.ticker import FuncFormatter, MultipleLocator
from IPython.display import display, Markdown

sys.path.insert(0, "/home/msseo/works/74.SeisComP_rtDD_DLpicker/notebooks/lib")
import nbfont
FONT_FAMILY = nbfont.use_helvetica(verbose=True)
print("resolved font family:", FONT_FAMILY, "| font file matplotlib uses for text:",
      matplotlib.font_manager.findfont(matplotlib.font_manager.FontProperties(family=["sans-serif"])))
import nb06_helpers as hp
importlib.reload(hp)

plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 8,
                     "xtick.labelsize": 8, "ytick.labelsize": 8, "figure.dpi": 100,
                     "mathtext.cal": "Helvetica:italic"})   # unused calligraphic slot; avoids a 'cursive' font lookup
os.makedirs(FIG_DIR, exist_ok=True)
pd.set_option("display.width", 230)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 140)

MT = r"$\mathit{M}$"
FIGS = {}


def mk(key, ms=None, filled=None, **over):
    # plot keywords of one catalog (same color and marker in every figure)
    s = STYLE[key]
    f = s["filled"] if filled is None else filled
    kw = dict(ls="none", marker=s["marker"], ms=MS if ms is None else ms, mec=s["color"],
              mfc=s["color"] if f else "white", mew=MEW, color=s["color"])
    kw.update(over)
    return kw


def handle(key, **over):
    return Line2D([], [], **mk(key, **over))


def plain_log(ax, axis="x"):
    # logarithmic axis labeled 0.1, 1, 10, ... instead of powers of ten
    getattr(ax, f"{axis}axis").set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))


def bearing(az):
    # azimuth (deg) -> quadrant bearing such as N7.5°W
    az = az % 360.0
    if az <= 90.0:
        return f"N{az:.1f}°E"
    if az <= 180.0:
        return f"S{180.0 - az:.1f}°E"
    if az <= 270.0:
        return f"S{az - 180.0:.1f}°W"
    return f"N{360.0 - az:.1f}°W"


print("versions: numpy", np.__version__, "| pandas", pd.__version__, "| matplotlib", matplotlib.__version__)
""")

# =====================================================================================================
md(r"""
## 1. Loading the result files

The analysis script `runs/sanramon/analysis/analyze_sanramon.py` is imported as a module (its `main()` is not run),
and its own loaders read every relocated catalog and the two references into one local frame: metres east, north
and up of the swarm, all depths below sea level (NCEDC DD depths are moved from the local model datum to sea level
with each event's NCSS datum, as in note 11). The comparison tables the script wrote are read as well.

**Event set.** Every comparison uses the same events: those relocated by all four main runs (P0, P1, S0, S1) that
are also in LDEO (NCEDC DD lacks one of them).
""")

code(r"""
# 1. load every result file (nothing is relocated)
AZ = hp.import_analysis(ANALYZE_PY)
assert AZ.K_NEIGH == K_NEIGH, "K_NEIGH differs from analyze_sanramon.py"
SOLS = AZ.load_solutions()                       # NCSS start and every run: id, latitude, longitude, depth, E, N, U
REFS, N_NODATUM = AZ.load_references()           # LDEO and NCEDC DD in the same frame
CAT = dict(SOLS)
CAT["REF_LDEO"], CAT["REF_NCEDC"] = REFS["LDEO"], REFS["NCEDC"]
MET = pd.read_csv(METRICS_CSV)
PER = pd.read_csv(PER_EVENT_CSV)
PLANE = pd.read_csv(PLANE_CSV)
PLANE["set"] = np.where(PLANE.event_set.str.startswith("common"), "common", "own")
RVR = pd.read_csv(RUN_VS_RUN_CSV)
XST = pd.read_csv(XCORR_STATS_CSV)
RES = pd.read_csv(RESIDUAL_CSV)
RT = pd.read_csv(RUNTIME_CSV).set_index("run")
DROP = pd.read_csv(DROPPED_CSV)
POSF = pd.read_csv(POSITIONS_CSV)
SUMJ = hp.read_json(SUMMARY_JSON)
EV = pd.read_csv(f"{RTDD_IN}/event.csv").set_index("id")
PH = pd.read_csv(f"{RTDD_IN}/phase.csv")
MATCH = pd.read_csv(MATCH_CSV)
NPICK = PH.groupby(["eventId", "type"]).size().unstack(fill_value=0)
NPICK["all"] = NPICK.sum(axis=1)
OT = pd.to_datetime(EV.isotime, format="ISO8601")
T_FIRST = OT.min()
DAYS = (OT - T_FIRST).dt.total_seconds() / 86400.0
MAG = EV.magnitude
MAIN4 = list(AZ.MAIN)
COMMON = sorted(set.intersection(*[set(SOLS[m].id) for m in MAIN4]) & set(REFS["LDEO"].id))
COMMON_NC = sorted(set.intersection(*[set(SOLS[m].id) for m in MAIN4]) & set(REFS["NCEDC"].id))
SE_IDS = sorted(MATCH[MATCH.benchmark_event & ~MATCH.ncss_in_box].event_id)   # the small south-east cluster
N_EV = len(EV)
assert int(MAG.idxmax()) == MAINSHOCK_ID, "MAINSHOCK_ID is not the largest event"
assert int(RVR[(RVR.a == "P1") & (RVR.b == "S1")].id_max.iloc[0]) == OUTLIER_ID, "OUTLIER_ID is not P1-vs-S1's largest"


def pos(key, ids=None):
    # east/north/up (m) of a catalog on an event set (default: the common events)
    d = CAT[key].set_index("id")
    return d.loc[COMMON if ids is None else ids, ["E", "N", "U"]].astype(float)


def rel(key, ids=None):
    # relative positions: minus the catalog's own centroid on that event set
    p = pos(key, ids)
    return p - p.mean()


def met(sol, ref="LDEO"):
    # one row of metrics_vs_reference.csv
    r = MET[(MET.solution == sol) & (MET.reference == ref)]
    assert len(r) == 1, (sol, ref)
    return r.iloc[0]


def per(sol, ref="LDEO"):
    # per-event rows of per_event_vs_reference.csv
    return PER[(PER.solution == sol) & (PER.reference == ref)].set_index("id")


def plane(cat, es="common"):
    # one row of plane_fit.csv ('common' = the common events; 'own' = all events of the catalog, references in the box)
    r = PLANE[(PLANE.catalog == cat) & (PLANE.set == es)]
    assert len(r) == 1, (cat, es)
    return r.iloc[0]


def rvr(a, b):
    r = RVR[(RVR.a == a) & (RVR.b == b)]
    assert len(r) == 1, (a, b)
    return r.iloc[0]


def xst(run, phase):
    r = XST[(XST.run == run) & (XST.phase == phase)]
    assert len(r) == 1, (run, phase)
    return r.iloc[0]


def res(run, stage, subset):
    r = RES[(RES.run == run) & (RES.stage == stage) & (RES.subset == subset)]
    assert len(r) == 1, (run, stage, subset)
    return r.iloc[0]


SEC_STRIKE = float(plane(SECTION_PLANE).strike)
print(f"{N_EV} input events (NCSS routine start), {len(PH)} picks ({int((PH.type == 'P').sum())} P, "
      f"{int((PH.type == 'S').sum())} S); first event {T_FIRST:%Y-%m-%d %H:%M} UTC, last {OT.max():%Y-%m-%d} UTC")
print(f"relocated: " + ", ".join(f"{k} {len(v)}" for k, v in SOLS.items() if k != "NCSS"))
print(f"common event set: {len(COMMON)} with LDEO, {len(COMMON_NC)} with NCEDC DD (events without an NCSS datum, "
      f"left out of NCEDC DD: {N_NODATUM})")
print(f"largest event {MAINSHOCK_ID}: {MT} {MAG.loc[MAINSHOCK_ID]:.2f}, {OT.loc[MAINSHOCK_ID]:%Y-%m-%d %H:%M:%S} UTC")
print(f"small south-east cluster (DD location in the box, NCSS routine location outside): {SE_IDS}")
print(f"section frame: strike {SEC_STRIKE:.1f}° of {SECTION_PLANE}'s plane fit ({bearing(SEC_STRIKE)})")
""")

md(r"""
### 1.1 Runs and their settings

Read back from every run folder: `options.json` of the pyrtdd runs (the values libhdd reports) and
`run_options.json` of the scrtdd runs (the values scrtdd's configuration reader used). Only the settings that
differ between runs are tabulated; note 11 (section 2) lists every setting. Time and memory come from
`runtime.csv`.
""")

code(r"""
# 1.1 settings of every run, from the run folders
SET = {}
for r in PY_RUNS:
    o = hp.read_json(f"{PY_DIR.format(run=r)}/options.json")
    d = o["definition"]
    xc = bool(o["XcorrOptions"]["enable"])
    SET[r] = dict(program="pyrtdd", xcorr=xc, n_ell=int(o["ClusteringOptions"]["numEllipsoids"]),
                  absloc=float(o["SolverOptions"]["absLocConstraintStart"]),
                  damping=float(o["SolverOptions"]["dampingFactorStart"]),
                  iterations=int(o["SolverOptions"]["algoIterations"]),
                  min_phases=int(o["ClusteringOptions"]["minNumPhases"]), min_neigh=int(o["ClusteringOptions"]["minNumNeigh"]),
                  xcorr_from=(f"re-used from {d['xcorr_precomputed']}" if d.get("xcorr_precomputed") else
                              ("measured" if xc else "-")),
                  drop_negative=bool(d.get("xcorr_drop_negative", False)), what=d["what"])
for r in SC_RUNS:
    j = hp.read_json(f"{SC_DIR.format(run=r)}/run_options.json")
    po = j["profile_options"]
    xc = bool(po["crossCorrelation.enable"]["value"])
    SET[r] = dict(program="scrtdd", xcorr=xc,
                  n_ell=int(po["doubleDifferenceSystem.eventPairSelection.multiEvent.numEllipsoids"]["value"]),
                  absloc=float(po["solver.absoluteLocationConstraint"]["value"][0]),
                  damping=float(po["solver.dampingFactor"]["value"][0]),
                  iterations=int(po["solver.algoIterations"]["value"]),
                  min_phases=int(po["doubleDifferenceSystem.eventFiltering.minNumPhases"]["value"]),
                  min_neigh=int(po["doubleDifferenceSystem.eventFiltering.minNumNeighbours"]["value"]),
                  xcorr_from="measured" if xc else "-", drop_negative=False, what=j["description"])


def solver_txt(r):
    return f"absLocConstraint {SET[r]['absloc']:g}, damping {SET[r]['damping']:g}"


def pairs_txt(r):
    return f"ellipsoids ({SET[r]['n_ell']})" if SET[r]["n_ell"] > 0 else "nearest neighbors"


ROWS_SET = []
for r in PY_RUNS + SC_RUNS:
    s = SET[r]
    ROWS_SET.append({"Run": r, "Program": s["program"], "Cross-correlation": "yes" if s["xcorr"] else "no",
                     "Correlations": s["xcorr_from"] + (" (negative CC made invalid)" if s["drop_negative"] else ""),
                     "Event pairs": pairs_txt(r), "absLocConstraint": f"{s['absloc']:g}", "Damping": f"{s['damping']:g}",
                     "Iterations": s["iterations"], "Min. phases / neighbors": f"{s['min_phases']} / {s['min_neigh']}",
                     "Relocated": len(SOLS[r]), "Wall time (s)": f"{RT.loc[r, 'wall_s']:.0f}",
                     "Peak memory (GB)": f"{RT.loc[r, 'peak_rss_mb'] / 1024:.2f}", "What": s["what"]})
SETT = pd.DataFrame(ROWS_SET)
display(Markdown(hp.md_table(SETT)))
""")

md(r"""
### 1.2 Events that rtDD did not relocate

rtDD's clustering keeps an event only if enough neighbors share enough phases with it (minimum phases and
neighbors in the table above). The reconstruction is in `dropped_events.csv`.
""")

code(r"""
# 1.2 dropped events: the same set in every run?
sets = DROP.groupby("run").id.apply(lambda s: tuple(sorted(s)))
assert sets.nunique() == 1, "different runs dropped different events"
DROPPED = list(sets.iloc[0])
d0 = DROP[DROP.run == sets.index[0]].set_index("id")
in_l = set(REFS["LDEO"].id)
in_n = set(REFS["NCEDC"].id)
DT = pd.DataFrame({"Event": DROPPED, "P picks": [int(d0.loc[e, "n_P"]) for e in DROPPED],
                   "S picks": [int(d0.loc[e, "n_S"]) for e in DROPPED],
                   "Most phases shared with any neighbor": [int(d0.loc[e, "max_shared_phases"]) for e in DROPPED],
                   "In LDEO": ["yes" if e in in_l else "no" for e in DROPPED],
                   "In NCEDC DD": ["yes" if e in in_n else "no" for e in DROPPED]})
display(Markdown(hp.md_table(DT)))
print(f"{len(DROPPED)} of {N_EV} events dropped, the same in all {sets.size} runs; reason given: "
      f"{'; '.join(sorted(set(DROP.reason)))}")
""")

md(r"""
### 1.3 Cross-file consistency checks

Each quantity shown in the figures is stored in a result file; here it is recomputed from the raw run outputs
(relocated catalogs, cross-correlation caches, libhdd's double-difference files) with the analysis script's own
functions where possible, and compared with the stored value. A check fails if the difference exceeds its
tolerance (parameter cell). Failed checks are listed again in the summary.
""")

code(r"""
# 1.3 consistency checks: value A (recomputed) vs value B (stored)
CHECKS = []
# (i) positions loaded by the module vs positions_enu.csv
for k, s in CAT.items():
    f = POSF[POSF.solution == k].set_index("id").sort_index()
    a = s.set_index("id").sort_index().loc[f.index, ["E", "N", "U"]]
    CHECKS.append(hp.check_row(f"positions of {k}: module vs positions_enu.csv, largest |difference| (m)",
                               np.abs(a.to_numpy() - f[["E", "N", "U"]].to_numpy()).max(), 0.0, TOL_POS_M))

# (ii) metrics a-c recomputed with analyze_sanramon.compare() vs metrics_vs_reference.csv
RECOMP = {}
for ref, ids in (("LDEO", COMMON), ("NCEDC", COMMON_NC)):
    for sol in ["NCSS", "P0", "S0", "P1", "S1", "P1pos", "P1n", "P1a0", "P1d1"] + (["REF_NCEDC"] if ref == "LDEO" else []):
        ids_s = sorted(set(ids) & set(CAT[sol].id))
        summ, pe = AZ.compare(CAT[sol], REFS[ref], ids_s)
        RECOMP[(sol, ref)] = (summ, pe)
        m = met(sol, ref)
        for c in ("rel_h_median_m", "rel_v_median_m", "local_h_median_m", "local_v_median_m", "centroid_shift_U_m"):
            CHECKS.append(hp.check_row(f"{sol} vs {ref}: {c}, recomputed vs stored", summ[c], m[c], TOL_METRIC_M))
# (iii) per-event values recomputed vs per_event_vs_reference.csv
for sol in ("NCSS", "P1"):
    pe = RECOMP[(sol, "LDEO")][1].set_index("id")
    st = per(sol).loc[pe.index]
    for c in ("d3_rel_m", "local_dh_med_m", "local_dv_med_m"):
        CHECKS.append(hp.check_row(f"{sol} vs LDEO per event: {c}, largest |difference| (m)",
                                   (pe[c] - st[c]).abs().max(), 0.0, TOL_PER_EVENT_M))
# (iv) fraction of events closer than the NCSS start (Figure 3) vs stored
for sol in ("P0", "P1"):
    a, b = per(sol).loc[COMMON], per("NCSS").loc[COMMON]
    CHECKS.append(hp.check_row(f"{sol}: share of events closer than NCSS, relative 3-D", (a.d3_rel_m < b.d3_rel_m).mean(),
                               met(sol).frac_events_closer_than_NCSS_rel3d, 1e-4))
    CHECKS.append(hp.check_row(f"{sol}: share of events closer than NCSS, local",
                               (np.hypot(a.local_dh_med_m, a.local_dv_med_m) < np.hypot(b.local_dh_med_m, b.local_dv_med_m)).mean(),
                               met(sol).frac_events_closer_than_NCSS_local, 1e-4))
# (v) plane fits recomputed with analyze_sanramon.plane_fit() vs plane_fit.csv; and this notebook's SVD distances
PLANE_DIST = {}
for k in ["NCSS", "P0", "S0", "P1", "S1", "P0n", "P1n", "P0a0", "P1a0", "P0d1", "P1d1", "P1pos", "REF_LDEO"]:
    xyz = pos(k).to_numpy()
    pf = AZ.plane_fit(xyz)
    st = plane(k)
    for c, tol in (("strike", TOL_DEG), ("dip", TOL_DEG), ("median_abs_dist_m", 0.01), ("thickness_rms_m", 0.01)):
        dd = pf[c] - st[c]
        if c == "strike":
            dd = (dd + 180.0) % 360.0 - 180.0
        CHECKS.append(hp.check_row(f"plane of {k}: {c}, recomputed vs stored", abs(dd), 0.0, tol))
    n_, dist_ = hp.plane_svd(xyz)
    PLANE_DIST[k] = pd.Series(dist_, index=COMMON)
    CHECKS.append(hp.check_row(f"plane of {k}: median |distance| of the notebook's SVD vs plane_fit()",
                               np.median(np.abs(dist_)), pf["median_abs_dist_m"], 1e-6))
# (vi) pyrtdd vs scrtdd medians recomputed vs run_vs_run.csv
for a, b in F5_PAIRS:
    ids = sorted(set(SOLS[a].id) & set(SOLS[b].id))
    d = pos(a, ids).to_numpy() - pos(b, ids).to_numpy()
    dr = d - np.median(d, axis=0)
    CHECKS.append(hp.check_row(f"{a} vs {b}: median 3-D distance (m), recomputed vs stored",
                               np.median(np.linalg.norm(d, axis=1)), rvr(a, b).abs3d_median_m, 1e-3))
    CHECKS.append(hp.check_row(f"{a} vs {b}: median relative distance (m), recomputed vs stored",
                               np.median(np.linalg.norm(dr, axis=1)), rvr(a, b).rel3d_median_m, 1e-3))
print(f"{len(CHECKS)} checks so far")
""")

code(r"""
# 1.3 (continued) cross-correlation caches, the P1-vs-S1 triplets and libhdd's residual files
XC = hp.read_rtdd_csv(f"{PY_DIR.format(run='P1')}/xcorr_cache.csv")
XV = XC[XC.valid]
XCOUNT = {}
for ph in ("P", "S"):
    g = XC[XC.phaseType == ph]
    v = g[g.valid]
    XCOUNT[ph] = dict(pairs=len(g), measured=len(v), acc=int((v.coefficient.abs() >= CC_MIN).sum()),
                      pos=int((v.coefficient >= CC_MIN).sum()), neg=int((v.coefficient <= -CC_MIN).sum()))
    s = xst("P1", ph)
    for c, sc in (("pairs", "entries"), ("measured", "valid"), ("acc", "abs_cc_ge"), ("pos", "cc_ge_pos"), ("neg", "cc_le_neg")):
        CHECKS.append(hp.check_row(f"P1 {ph}: {c}, from the cache vs xcorr_stats.csv", XCOUNT[ph][c], s[sc], 0))
    CHECKS.append(hp.check_row(f"P1 {ph}: above the threshold, cache vs libhdd's own log line", XCOUNT[ph]["acc"],
                               s.log_cc_above_threshold, 0))
N_AT_THRESHOLD = int((XV.coefficient.abs() == CC_MIN).sum())     # written as exactly 0.700000 in the cache
# S1's own counts (scrtdd's xcorr.csv) next to P1's
for ph in ("P", "S"):
    CHECKS.append(hp.check_row(f"S1 vs P1 {ph}: accepted correlations (xcorr_stats.csv)", xst("S1", ph).abs_cc_ge,
                               xst("P1", ph).abs_cc_ge, int(SUMJ["xcorr_pyrtdd_vs_scrtdd"]["P1_vs_S1"][f"{ph}_threshold_side_differs"])))

# P1pos: the measurements made invalid are exactly P1's negative ones
XPOS = hp.read_rtdd_csv(P1POS_CACHE)
kk = ["eventId1", "eventId2", "networkCode", "stationCode", "locationCode", "phaseType"]
mm = XC.merge(XPOS, on=kk, suffixes=("_p1", "_pos"))
changed = mm[mm.valid_p1 != mm.valid_pos]
CHECKS.append(hp.check_row("P1pos cache: measurements made invalid vs P1's CC <= -0.7", len(changed), XCOUNT["P"]["neg"], 0))
CHECKS.append(hp.check_row("P1pos cache: largest CC among those made invalid", changed.coefficient_p1.max(), -CC_MIN, 1e-9))

# P1 vs S1, triplet by triplet
TRIP = pd.read_csv(TRIPLETS_CSV, dtype={"locationCode": str}, keep_default_na=False)
TB = TRIP[TRIP.valid_py & TRIP.valid_sc].copy()
TB["dlag_ms"] = (TB.lag_py - TB.lag_sc).abs() * 1000.0
LAGCAT = {"identical": TB.dlag_ms < 0.5, "one sample (1 ms)": (TB.dlag_ms >= 0.5) & (TB.dlag_ms < 1.5),
          "2-10 ms": (TB.dlag_ms >= 1.5) & (TB.dlag_ms <= 10.5), "more than 10 ms": TB.dlag_ms > 10.5}
SJ = SUMJ["xcorr_pyrtdd_vs_scrtdd"]["P1_vs_S1"]
CHECKS.append(hp.check_row("P1 vs S1: identical lags, recomputed vs summary.json", LAGCAT["identical"].sum(), SJ["lag_identical"], 0))
CHECKS.append(hp.check_row("P1 vs S1: lags > 1 ms apart, recomputed vs summary.json", (TB.dlag_ms > 1.5).sum(), SJ["lag_diff_gt_1ms"], 0))
CHECKS.append(hp.check_row("P1 vs S1: lags > 10 ms apart, recomputed vs summary.json", LAGCAT["more than 10 ms"].sum(), SJ["lag_diff_gt_10ms"], 0))
SIDE = (TB.coefficient_py.abs() >= CC_MIN) != (TB.coefficient_sc.abs() >= CC_MIN)
CHECKS.append(hp.check_row("P1 vs S1: opposite sides of the threshold, recomputed vs summary.json", SIDE.sum(), SJ["threshold_side_differs"], 0))

# libhdd's double-difference files of P1: residual MAD recomputed vs residual_stats.csv
DDC = ["phaseType", "weight", "xcorrUsed", "xcorrCoefficient", "doubleDifferenceResidual"]
DD = {st: hp.read_rtdd_csv(DD_FILE.format(run="P1", stage=st), usecols=DDC) for st in ("initial", "final")}
for st, d in DD.items():
    d["res_ms"] = d.doubleDifferenceResidual.astype(float) * 1000.0
    for sub, g in (("xcorr", d[d.xcorrUsed]), ("catalog", d[~d.xcorrUsed])):
        CHECKS.append(hp.check_row(f"P1 {st} {sub}: residual MAD (ms), recomputed vs residual_stats.csv", hp.mad(g.res_ms),
                                   res("P1", st, sub).mad_ms, TOL_MS))
CHK = pd.DataFrame(CHECKS)
print(f"{int(CHK.Consistent.sum())} of {len(CHK)} checks consistent")
if (~CHK.Consistent).any():
    print("checks that FAIL:")
    display(CHK[~CHK.Consistent])
print(f"(|CC| written as exactly {CC_MIN} in P1's cache: {N_AT_THRESHOLD} measurement(s))")
""")

md(r"""
### 1.4 Note 11 against the files

The numbers printed in note 11 (typed into the parameter cell only as check targets) are recomputed here from the
files, with the same definitions as the note. A row fails if the file value differs by more than half a unit of the
note's last printed digit (or, for a bound such as "at most", lies outside it). The rows that fail are discussed in
the summary.
""")

code(r"""
# 1.4 recompute every note-11 number from the files
C = {}
C["n_relocated"] = min(len(SOLS[r]) for r in SOLS if r != "NCSS")
C["n_dropped"] = len(DROPPED)
for a, b, k in (("P0", "S0", "s0p0"), ("P1", "S1", "s1p1")):
    r_ = rvr(a, b)
    C[f"{k}_med"], C[f"{k}_rel_med"], C[f"{k}_p90"] = r_.abs3d_median_m, r_.rel3d_median_m, r_.abs3d_p90_m
C["s0p0_max"] = rvr("P0", "S0").abs3d_max_m
C["s1p1_max_km"] = rvr("P1", "S1").abs3d_max_m / 1000.0
C["lag_identical"] = int(LAGCAT["identical"].sum())
C["lag_identical_pct"] = 100.0 * LAGCAT["identical"].mean()
C["lag_1ms"] = int(LAGCAT["one sample (1 ms)"].sum())
C["lag_gt1"] = int((TB.dlag_ms > 1.5).sum())
C["lag_gt10"] = int(LAGCAT["more than 10 ms"].sum())
C["cc_side"] = int(SIDE.sum())
C.update(P_pairs=XCOUNT["P"]["pairs"], P_meas=XCOUNT["P"]["measured"], P_acc=XCOUNT["P"]["acc"],
         P_acc_log=int(xst("P1", "P").log_cc_above_threshold), P_pos=XCOUNT["P"]["pos"], P_neg=XCOUNT["P"]["neg"],
         S_pairs=XCOUNT["S"]["pairs"], S_meas=XCOUNT["S"]["measured"], S_acc=XCOUNT["S"]["acc"])
vp = XV[XV.phaseType == "P"]
LAG_POS = vp[vp.coefficient >= CC_MIN].lag.abs() * 1000.0
LAG_NEG = vp[vp.coefficient <= -CC_MIN].lag.abs() * 1000.0
LAG_S = XV[(XV.phaseType == "S") & (XV.coefficient >= CC_MIN)].lag.abs() * 1000.0
C["lag_pos"], C["lag_neg"] = LAG_POS.median(), LAG_NEG.median()
fx = DD["final"][DD["final"].xcorrUsed]
FPOS, FNEG = fx[fx.xcorrCoefficient > 0], fx[fx.xcorrCoefficient < 0]
C["w_pos"], C["w_neg"] = 100.0 * (FPOS.weight > 0).mean(), 100.0 * (FNEG.weight > 0).mean()
C["r_pos"], C["r_neg"] = FPOS.res_ms.abs().median(), FNEG.res_ms.abs().median()
C["mad_xc_i"], C["mad_xc_f"] = res("P1", "initial", "xcorr").mad_ms, res("P1", "final", "xcorr").mad_ms
C["mad_cat_i"], C["mad_cat_f"] = res("P1", "initial", "catalog").mad_ms, res("P1", "final", "catalog").mad_ms
C["mad_pos_f"] = res("P1pos", "final", "xcorr").mad_ms
for sol, k in (("NCSS", "NCSS"), ("P0", "P0"), ("P1", "P1"), ("S1", "S1"), ("REF_NCEDC", "NC")):
    m = met(sol)
    C[f"{k}_rh"], C[f"{k}_rv"], C[f"{k}_lh"], C[f"{k}_lv"] = (m.rel_h_median_m, m.rel_v_median_m, m.local_h_median_m,
                                                              m.local_v_median_m)
C["P1pos_rv"] = met("P1pos").rel_v_median_m
C["P1n_lh"], C["P1n_lv"], C["P1n_rv"] = met("P1n").local_h_median_m, met("P1n").local_v_median_m, met("P1n").rel_v_median_m
C["P1a0_rh"] = met("P1a0").rel_h_median_m
for sol in ("P0", "P1"):
    C[f"{sol}_fr"] = 100.0 * met(sol).frac_events_closer_than_NCSS_rel3d
    C[f"{sol}_fl"] = 100.0 * met(sol).frac_events_closer_than_NCSS_local
C["P1_i3"], C["P1_ilh"], C["P1_ilv"] = met("P1").improvement_rel_3d, met("P1").improvement_local_h, met("P1").improvement_local_v
for sol in ("P0", "P1", "P0a0", "P1a0", "P0d1", "P1d1"):
    C[f"{sol}_U"] = met(sol).centroid_shift_U_m
UP_FROM_START = {r: (pos(r).U.mean() - pos("NCSS").U.mean()) / 1000.0 for r in ("P0a0", "P1a0")}
C["a0_up_min"], C["a0_up_max"] = min(UP_FROM_START.values()), max(UP_FROM_START.values())
C["a0_vsL_min"] = min(met(r).centroid_shift_U_m for r in ("P0a0", "P1a0")) / 1000.0
C["a0_vsL_max"] = max(met(r).centroid_shift_U_m for r in ("P0a0", "P1a0")) / 1000.0
ZMEAN = {k: -pos(k).U.mean() / 1000.0 for k in CAT if k != "REF_NCEDC"}
ZMEAN["REF_NCEDC"] = -pos("REF_NCEDC", COMMON_NC).U.mean() / 1000.0
DEFAULT_RUNS = [r for r in ("P0", "S0", "P1", "S1") if SET[r]["absloc"] > 0]
C["z_LDEO"], C["z_NCSS"], C["z_NC"] = ZMEAN["REF_LDEO"], ZMEAN["NCSS"], ZMEAN["REF_NCEDC"]
C["z_def_min"], C["z_def_max"] = min(ZMEAN[r] for r in DEFAULT_RUNS), max(ZMEAN[r] for r in DEFAULT_RUNS)
C["L_strike"], C["L_dip"] = plane("REF_LDEO").strike, plane("REF_LDEO").dip
C["P1_strike"], C["P1_dip"] = plane("P1").strike, plane("P1").dip
for k, c in (("REF_LDEO", "L_med"), ("P1", "P1_med"), ("S1", "S1_med"), ("P0", "P0_med"), ("NCSS", "NCSS_med")):
    C[c] = plane(k).median_abs_dist_m
for k, c in (("REF_LDEO", "L_rms_noSE"), ("P1", "P1_rms_noSE")):
    d_ = PLANE_DIST[k].drop(index=[e for e in SE_IDS if e in PLANE_DIST[k].index])
    C[c] = float(np.sqrt(np.mean(d_ ** 2)))
MET["chg_h"] = (MET.rel_h_median_m_mediancentred - MET.rel_h_median_m).abs()
MET["chg_v"] = (MET.rel_v_median_m_mediancentred - MET.rel_v_median_m).abs()
rt_rows = MET[~MET.solution.isin(["NCSS", "REF_LDEO", "REF_NCEDC"])]
C["medctr_rt"] = float(rt_rows[["chg_h", "chg_v"]].to_numpy().max())
MEDCTR_WORST = rt_rows.loc[rt_rows[["chg_h", "chg_v"]].max(axis=1).idxmax()]
C["medctr_ncss"] = float(MET[MET.solution == "NCSS"][["chg_h", "chg_v"]].to_numpy().max())
C["nb_L"], C["nb_NC"] = met("P1").ref_neighbour_dist_median_m, met("P1", "NCEDC").ref_neighbour_dist_median_m
LD = REFS["LDEO"].set_index("id").loc[COMMON]
C["ldeo_eh"] = float(np.median(LD.eh1_km)) * 1000.0
C["out_zP1"], C["out_zS1"] = -pos("P1", [OUTLIER_ID]).U.iloc[0] / 1000.0, -pos("S1", [OUTLIER_ID]).U.iloc[0] / 1000.0
C["out_zL"] = -pos("REF_LDEO", [OUTLIER_ID]).U.iloc[0] / 1000.0
dEN = pos("S1", [OUTLIER_ID]).iloc[0] - pos("P1", [OUTLIER_ID]).iloc[0]
C["out_h"] = float(np.hypot(dEN.E, dEN.N)) / 1000.0
OUT_TRIP = TB[(TB.eventId1 == OUTLIER_ID) | (TB.eventId2 == OUTLIER_ID)]
OUT_KEY = OUT_TRIP.loc[OUT_TRIP.dlag_ms.idxmax()]
C["out_lagP"], C["out_lagS"] = OUT_KEY.lag_py * 1000.0, OUT_KEY.lag_sc * 1000.0
C["out_ndiff"] = int((OUT_TRIP.dlag_ms >= 0.5).sum())
C["out_ndiff1"] = int((OUT_TRIP.dlag_ms > 1.5).sum())
d2 = pos("P1", [72541385]).iloc[0] - pos("S1", [72541385]).iloc[0]
C["ev2_m"] = float(np.linalg.norm(d2))
C["rms_start"] = RT.loc["P0", "event_startRms_median_ms"]
C["rms_P0"], C["rms_P1"] = RT.loc["P0", "event_finalRms_median_ms"], RT.loc["P1", "event_finalRms_median_ms"]

REUSE_LOG = {r: int(xst(r, "P").log_cc_above_threshold) for r in ("P1a0", "P1d1")}
N_ONE_SAMPLE_OUT = int(((OUT_TRIP.dlag_ms >= 0.5) & (OUT_TRIP.dlag_ms < 1.5)).sum())
L_ONLY = MET[(MET.reference == "LDEO") & ~MET.solution.isin(["NCSS", "REF_LDEO", "REF_NCEDC"])]
COMMENT = {
    "P_acc_log": (f"P1's own log counts {C['P_acc_log']:,}; the runs that re-use P1's cache log "
                  + ", ".join(f"{r} {v:,}" for r, v in REUSE_LOG.items()) + f": the cache holds {N_AT_THRESHOLD} "
                  f"coefficient written as exactly {CC_MIN:g} (six decimals), which P1's own count apparently did not include "
                  f"(its unrounded value presumably just below {CC_MIN:g})"),
    "a0_up_min": "the note's 4.1-4.5 km is the offset from LDEO's centroid (rows below); from the NCSS start it is "
                 f"{C['a0_up_min']:.1f}-{C['a0_up_max']:.1f} km",
    "a0_up_max": "see the row above",
    "medctr_rt": (f"largest: {MEDCTR_WORST.solution} against {MEDCTR_WORST.reference}; against LDEO at most "
                  f"{float(L_ONLY[['chg_h', 'chg_v']].to_numpy().max()):.1f} m"),
    "out_ndiff": (f"{N_ONE_SAMPLE_OUT} of them differ by one sample (1 ms); the note's statement holds for differences "
                  f"above 1 ms (next row)"),
}
N11 = []
for key, what, val, tol, kind in NOTE11_VALUES:
    v = float(C[key])
    ok = (v <= val + 1e-9) if kind == "le" else (abs(v - val) <= tol + 1e-9)
    N11.append({"Quantity": what, "Note 11": f"{'at most ' if kind == 'le' else ''}{val:g}",
                "Files": f"{v:.4g}" if abs(v) < 1000 else f"{v:.0f}", "Consistent": "yes" if ok else "NO",
                "Comment": "" if ok else COMMENT.get(key, "")})
N11 = pd.DataFrame(N11)
display(Markdown(hp.md_table(N11)))
print(f"{int((N11.Consistent == 'yes').sum())} of {len(N11)} note-11 numbers agree with the files")
""")

# =====================================================================================================
md(r"""
## 2. Figure 1: the swarm in four catalogs

**What it shows.** The same events in four catalogs, side by side: the NCSS routine locations (rtDD's start),
rtDD with catalog times only (pyrtdd P0), rtDD with cross-correlation (pyrtdd P1; scrtdd S1 is the same, Figure 5)
and LDEO. Each catalog is drawn **relative to its own centroid**, so only the shape is compared; where the swarm
sits as a whole differs between catalogs (Figure 7). Top row: map view. Middle row: a vertical section along the
fault (looking at the fault face). Bottom row: a vertical section across the fault (looking along the fault); a
thin, sharp fault appears as a narrow vertical band here. The along/across-strike frame is set by the strike of
LDEO's fitted plane (Figure 4). Every panel has the same scale (equal east, north and vertical scales). Color is the
time since the first event, marker size grows with magnitude, and the star is the largest event.
""")

code(r"""
# Figure 1: map view, along-strike and across-strike sections, four catalogs, relative to their own centroids
F1F = {}
for k in F1_CATALOGS:
    r_ = rel(k)
    al, ac = hp.rotate(r_.E, r_.N, SEC_STRIKE)
    F1F[k] = pd.DataFrame({"E": r_.E, "N": r_.N, "U": r_.U, "along": al, "across": ac}, index=r_.index)
ROWS1 = [("E", "N", "East of the centroid (m)", "Map view: north of the centroid (m)"),
         ("along", "U", f"Along strike, toward {bearing(SEC_STRIKE)} (m)", "Section along strike: up (m)"),
         ("across", "U", f"Across strike, toward {bearing(SEC_STRIKE + 90.0)} (m)", "Section across strike: up (m)")]
SIZE = (F1_SIZE_M1 * F1_SIZE_FACTOR ** (MAG - 1.0)).fillna(F1_SIZE_NOMAG)
NORM_T = Normalize(0.0, float(DAYS.loc[COMMON].max()))
ORD = np.array(COMMON)[np.argsort(DAYS.loc[COMMON].to_numpy(), kind="stable")]   # earliest drawn first
s_ = F1_IN_PER_KM / 1000.0
cw = max(2 * F1_HALF_M[cx] for cx, *_ in ROWS1) * s_
rh = [2 * F1_HALF_M[cy] * s_ for _, cy, *_ in ROWS1]
ml_, mr_, mb_, mt_, gw_, gh_ = 0.78, 1.15, 0.5, 0.3, 0.22, 0.62
nc = len(F1_CATALOGS)
W = ml_ + nc * cw + (nc - 1) * gw_ + mr_
H = mb_ + sum(rh) + (len(ROWS1) - 1) * gh_ + mt_
fig = plt.figure(figsize=(W, H))
AX1 = []
letters = iter("abcdefghijklmnopqrstuvwxyz")
NOUT = {}
y_top = H - mt_
for i, (cx, cy, xl, yl) in enumerate(ROWS1):
    y0 = y_top - rh[i]
    for j, k in enumerate(F1_CATALOGS):
        w = 2 * F1_HALF_M[cx] * s_
        ax = fig.add_axes([(ml_ + j * (cw + gw_)) / W, y0 / H, w / W, rh[i] / H])
        d = F1F[k].loc[ORD]
        ax.scatter(d[cx], d[cy], c=DAYS.loc[ORD], s=SIZE.loc[ORD], cmap=F1_CMAP, norm=NORM_T, linewidths=0, zorder=3)
        ms_ = F1F[k].loc[MAINSHOCK_ID]
        ax.scatter([ms_[cx]], [ms_[cy]], marker="*", s=F1_STAR_SIZE, c=[DAYS.loc[MAINSHOCK_ID]], cmap=F1_CMAP, norm=NORM_T,
                   edgecolors="k", linewidths=0.7, zorder=5)
        if cx == "E":
            t_ = np.array([-3.0, 3.0]) * F1_HALF_M["N"]
            ax.plot(t_ * np.sin(np.radians(SEC_STRIKE)), t_ * np.cos(np.radians(SEC_STRIKE)), color="0.35", lw=0.8,
                    ls=(0, (5, 3)), zorder=2)
        ax.set_xlim(-F1_HALF_M[cx], F1_HALF_M[cx])
        ax.set_ylim(-F1_HALF_M[cy], F1_HALF_M[cy])
        ax.set_aspect("equal", adjustable="box")
        ax.xaxis.set_major_locator(MultipleLocator(1000))
        ax.yaxis.set_major_locator(MultipleLocator(1000))
        ax.set_xlabel(xl, fontsize=8)
        if j == 0:
            ax.set_ylabel(yl, fontsize=8.5)
        else:
            ax.tick_params(labelleft=False)
        nout = int(((F1F[k][cx].abs() > F1_HALF_M[cx]) | (F1F[k][cy].abs() > F1_HALF_M[cy])).sum())
        NOUT[(k, cx)] = nout
        ax.set_title(f"({next(letters)}) {STYLE[k]['short']}" + (" (= S1)" if k == "P1" else ""), loc="left", fontsize=9)
        ax.set_title(f"{nout} outside", loc="right", fontsize=7, color="0.3")
        AX1.append(ax)
    y_top = y0 - gh_
cax = fig.add_axes([(W - mr_ + 0.28) / W, mb_ / H, 0.13 / W, (H - mb_ - mt_) / H])
sm = matplotlib.cm.ScalarMappable(norm=NORM_T, cmap=F1_CMAP)
cb = fig.colorbar(sm, cax=cax)
cb.set_label(f"Days since the first event ({T_FIRST:%Y-%m-%d %H:%M} UTC)")
handles = [Line2D([], [], ls="none", marker="o", ms=float(np.sqrt(F1_SIZE_M1 * F1_SIZE_FACTOR ** (m - 1.0))), mfc="0.45",
                  mec="none") for m in F1_SIZE_LEGEND]
labels = [f"{MT} {m:g}" for m in F1_SIZE_LEGEND]
handles += [Line2D([], [], ls="none", marker="*", ms=float(np.sqrt(F1_STAR_SIZE)), mfc="0.8", mec="k", mew=0.7),
            Line2D([], [], color="0.35", lw=0.8, ls=(0, (5, 3)))]
labels += [f"Largest event, {MT} {MAG.loc[MAINSHOCK_ID]:.1f} ({MAINSHOCK_ID})",
           f"Strike of LDEO's fitted plane ({SEC_STRIKE:.1f}°): direction of the sections"]
leg = hp.legend_above(fig, AX1 + [cax], handles, labels, ncol=len(handles), fontsize=8)
pl = {k: plane(k) for k in F1_CATALOGS}
msg = ("The fault sharpens from the routine catalog to rtDD with cross-correlation: median distance from the fitted "
       "plane " + ", ".join(f"{STYLE[k]['short'].replace('pyrtdd ', '')} {pl[k].median_abs_dist_m:.0f} m" for k in F1_CATALOGS)
       + "; down-dip spread (RMS) " + ", ".join(f"{pl[k].spread_down_dip_rms_m:.0f}" for k in F1_CATALOGS) + " m")
hp.text_above(fig, [leg] + AX1, msg, fontsize=9.5)
note = (f"{len(COMMON)} common events, each catalog relative to its own centroid. Color: days since the first event; "
        f"marker area {F1_SIZE_M1:g} pt² at {MT} 1, times {F1_SIZE_FACTOR:g} per magnitude unit (no magnitude: "
        f"{F1_SIZE_NOMAG:g} pt²). Windows: east ±{F1_HALF_M['E']:,} m, north and along strike ±{F1_HALF_M['N']:,} m, across "
        f"strike ±{F1_HALF_M['across']:,} m, up ±{F1_HALF_M['U']:,} m; events outside each window are counted at its top "
        f"right (among them the {len(SE_IDS)} events of a small cluster to the south-east). Up is positive.")
hp.text_below(fig, AX1[-nc:], textwrap.fill(note, 175), fontsize=7)
FIGS["1"] = hp.save_fig(fig, FIG_DIR, "06_1_swarm_four_catalogs", dpi=FIG_DPI)
plt.show()
""")

# =====================================================================================================
md(r"""
## 3. Figure 2: how far is each event from LDEO?

**What it shows.** For every common event, its distance from its LDEO position, as cumulative distributions (a
curve further left = closer to LDEO). (a, b) **Relative** positions (each catalog minus its own centroid),
horizontal and vertical. (c, d) **Local** vectors (the arrows to the event's [[K_NEIGH]] nearest LDEO neighbors),
horizontal and vertical. Curves: the NCSS routine start, rtDD with catalog times only (P0) and with
cross-correlation (P1 and S1, nearly on top of each other), and, for scale, the other published double-difference
catalog, NCEDC DD, against LDEO. The symbol on each curve marks its median. Two lines give a sense of scale: LDEO's
own median 95% error (relative panels) and the median distance to the [[K_NEIGH]] nearest LDEO neighbors (local
panels).
""")

code(r"""
# Figure 2: cumulative distributions of the per-event distance from LDEO
COLS2 = [("dh_rel_m", "(a) Relative position, horizontal"), ("dv_rel_m", "(b) Relative position, vertical"),
         ("local_dh_med_m", "(c) Local vectors, horizontal"), ("local_dv_med_m", "(d) Local vectors, vertical")]
LDEO_EH = float(np.median(LD.eh1_km)) * 1000.0
LDEO_EZ = float(np.median(LD.ez_km)) * 1000.0
NB = float(met("P1").ref_neighbour_dist_median_m)
fig, axes = plt.subplots(2, 2, figsize=(10.6, 7.4), gridspec_kw=dict(hspace=0.36, wspace=0.16))
NBELOW = {}
for ax, (col, tt) in zip(axes.ravel(), COLS2):
    ax.axhline(0.5, color="0.8", lw=0.6, zorder=1)
    for k in F2_SOLUTIONS:
        d = per(k)[col]
        NBELOW[(k, col)] = int((d < F2_XLIM_M[0]).sum())
        x, y = hp.ecdf(np.clip(d.to_numpy(), F2_XLIM_M[0], None))
        ax.step(np.r_[F2_XLIM_M[0], x], np.r_[0.0, y], where="post", color=STYLE[k]["color"], ls=STYLE[k]["ls"],
                lw=1.5, zorder=3)
        hollow = {} if STYLE[k]["filled"] else {"mfc": "none"}
        ax.plot(float(d.median()), 0.5, **mk(k, ms=9.0 if k == "P1" else 6.5, zorder=4 if k == "P1" else 5, **hollow))
    if col.startswith("local"):
        ax.axvline(NB, color="0.3", lw=0.9, ls="-.", zorder=2)
    else:
        ax.axvline(LDEO_EH if "dh" in col else LDEO_EZ, color="k", lw=0.9, ls=(0, (1, 1.5)), zorder=2)
    ax.set_xscale("log")
    ax.set_xlim(F2_XLIM_M)
    ax.set_ylim(0.0, 1.0)
    plain_log(ax, "x")
    ax.set_xlabel("Distance from the LDEO position (m)")
    ax.set_ylabel("Share of events at or below")
    ax.set_title(tt, loc="left")
handles = [Line2D([], [], color=STYLE[k]["color"], ls=STYLE[k]["ls"], lw=1.5, marker=STYLE[k]["marker"], ms=6,
                  mfc=STYLE[k]["color"] if STYLE[k]["filled"] else "white", mec=STYLE[k]["color"], mew=MEW) for k in F2_SOLUTIONS]
labels = [STYLE[k]["label"] for k in F2_SOLUTIONS]
handles += [Line2D([], [], color="k", lw=0.9, ls=(0, (1, 1.5))), Line2D([], [], color="0.3", lw=0.9, ls="-.")]
labels += [f"LDEO's own median 95% error (horizontal {LDEO_EH:.0f} m, vertical {LDEO_EZ:.0f} m)",
           f"Median distance to the {K_NEIGH} nearest LDEO neighbors ({NB:.0f} m)"]
leg = hp.legend_above(fig, axes, handles, labels, ncol=3, fontsize=7.5)
mm2 = {k: met(k) for k in F2_SOLUTIONS}
msg = (f"rtDD with cross-correlation is closer to LDEO than the NCSS start and than NCEDC DD: local median "
       f"{mm2['P1'].local_h_median_m:.0f} / {mm2['P1'].local_v_median_m:.0f} m (P1, horizontal / vertical), against "
       f"{mm2['NCSS'].local_h_median_m:.0f} / {mm2['NCSS'].local_v_median_m:.0f} m (NCSS) and "
       f"{mm2['REF_NCEDC'].local_h_median_m:.0f} / {mm2['REF_NCEDC'].local_v_median_m:.0f} m (NCEDC DD)")
hp.text_above(fig, [leg] + list(axes.ravel()), msg, fontsize=9.5)
nb_txt = ", ".join(f"{STYLE[k]['short']} {'/'.join(str(NBELOW[(k, c)]) for c, _ in COLS2)}" for k in F2_SOLUTIONS
                   if any(NBELOW[(k, c)] for c, _ in COLS2))
note = (f"{len(COMMON)} common events ({len(per('REF_NCEDC'))} for NCEDC DD). Local: per event, the median over its "
        f"{K_NEIGH} nearest LDEO neighbors of the difference between the event-to-neighbor arrows. LDEO's 95% errors: "
        f"median over these events of EH1 (major axis of the horizontal ellipse) and EV. Values below "
        f"{F2_XLIM_M[0]:g} m are drawn at the left edge (events per panel a-d: {nb_txt if nb_txt else 'none'}).")
hp.text_below(fig, list(axes.ravel()), textwrap.fill(note, 170), fontsize=7)
FIGS["2"] = hp.save_fig(fig, FIG_DIR, "06_2_distance_to_ldeo", dpi=FIG_DPI)
plt.show()
""")

# =====================================================================================================
md(r"""
## 4. Figure 3: before and after, event by event

**What it shows.** Each dot is one event: its distance from LDEO at the start (NCSS routine, horizontal axis)
against its distance after rtDD with cross-correlation (P1, vertical axis). Dots below the diagonal moved closer to
LDEO's structure; the dotted line marks "[[F3_RATIO]] times closer". (a) Relative position in 3-D. (b) Local vectors
in 3-D (horizontal and vertical local differences combined). Color is the event's magnitude; the open circle marks
event [[OUTLIER_ID]] (Figure 5).
""")

code(r"""
# Figure 3: per-event distance from LDEO before (NCSS) and after (P1)
B3, A3 = per(F3_BEFORE).loc[COMMON], per(F3_AFTER).loc[COMMON]
V3 = [("rel", B3.d3_rel_m, A3.d3_rel_m, "(a) Relative position, 3-D"),
      ("local", np.hypot(B3.local_dh_med_m, B3.local_dv_med_m), np.hypot(A3.local_dh_med_m, A3.local_dv_med_m),
       "(b) Local vectors, 3-D")]
cmap3 = plt.get_cmap(F3_CMAP)
NORM_M = Normalize(float(MAG.loc[COMMON].min()), float(MAG.loc[COMMON].max()))
fig, axes = plt.subplots(1, 2, figsize=(10.8, 5.3), gridspec_kw=dict(wspace=0.22))
F3S = {}
mg = MAG.reindex(COMMON)
okm = mg.notna().to_numpy()
for ax, (key, b, a, tt) in zip(axes, V3):
    bb, aa = np.clip(b.to_numpy(), *F3_LIM_M), np.clip(a.to_numpy(), *F3_LIM_M)
    ax.plot(F3_LIM_M, F3_LIM_M, color="0.25", lw=0.9, ls="--", zorder=2)
    ax.plot(F3_LIM_M, np.array(F3_LIM_M) / F3_RATIO, color="0.35", lw=0.9, ls=":", zorder=2)
    ax.scatter(bb[okm], aa[okm], c=mg.to_numpy()[okm], cmap=cmap3, norm=NORM_M, s=10, linewidths=0, zorder=3)
    ax.scatter(bb[~okm], aa[~okm], color="0.6", s=10, linewidths=0, zorder=3)
    io = COMMON.index(OUTLIER_ID)
    ax.plot(bb[io], aa[io], ls="none", marker="o", ms=11, mfc="none", mec="k", mew=1.0, zorder=4)
    ax.annotate(str(OUTLIER_ID), (bb[io], aa[io]), xytext=(9, 7), textcoords="offset points", fontsize=7.5, zorder=6,
                bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
    frac = float((a < b).mean())
    F3S[key] = dict(frac=frac, b_med=float(b.median()), a_med=float(a.median()), n=len(a))
    ax.text(0.03, 0.97, f"{frac:.0%} of {len(a)} events closer after {F3_AFTER}\nmedian {b.median():.0f} m before, "
            f"{a.median():.0f} m after", transform=ax.transAxes, ha="left", va="top", fontsize=8.5,
            bbox=dict(boxstyle="square,pad=0.3", fc="white", ec="0.6"), zorder=7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(F3_LIM_M)
    ax.set_ylim(F3_LIM_M)
    ax.set_aspect("equal")
    plain_log(ax, "x")
    plain_log(ax, "y")
    ax.set_xlabel(f"Before: {STYLE[F3_BEFORE]['label'].split(' (')[0]}, distance from LDEO (m)")
    ax.set_ylabel(f"After: {STYLE[F3_AFTER]['label'].split(' (')[0]}, distance from LDEO (m)")
    ax.set_title(tt, loc="left")
fig.canvas.draw()
bb_ = axes[1].get_position()
cax = fig.add_axes([bb_.x1 + 0.015, bb_.y0, 0.012, bb_.height])
cb = fig.colorbar(matplotlib.cm.ScalarMappable(norm=NORM_M, cmap=cmap3), cax=cax)
cb.set_label(f"Magnitude {MT} (NCSS preferred)")
handles = [Line2D([], [], color="0.25", lw=0.9, ls="--"), Line2D([], [], color="0.35", lw=0.9, ls=":"),
           Line2D([], [], ls="none", marker="o", ms=4, mfc="0.6", mec="none"),
           Line2D([], [], ls="none", marker="o", ms=11, mfc="none", mec="k", mew=1.0)]
labels = ["Same distance before and after", f"{F3_RATIO:g} times closer after",
          f"No magnitude ({int((~okm).sum())} events)", f"Event {OUTLIER_ID} (Figure 5)"]
leg = hp.legend_above(fig, list(axes) + [cax], handles, labels, ncol=4, fontsize=8)
msg = (f"rtDD with cross-correlation moves {F3S['rel']['frac']:.0%} of the events closer to LDEO's structure "
       f"(relative 3-D) and {F3S['local']['frac']:.0%} closer at the scale of their neighbors")
hp.text_above(fig, [leg] + list(axes) + [cax], msg, fontsize=9.5)
note = (f"Distances clipped to {F3_LIM_M[0]:g}-{F3_LIM_M[1]:,.0f} m for display. For comparison, catalog-only P0: "
        f"{met('P0').frac_events_closer_than_NCSS_rel3d:.0%} (relative 3-D) and "
        f"{met('P0').frac_events_closer_than_NCSS_local:.0%} (local) of the events closer than at the start.")
hp.text_below(fig, list(axes), textwrap.fill(note, 160), fontsize=7)
FIGS["3"] = hp.save_fig(fig, FIG_DIR, "06_3_before_after", dpi=FIG_DPI)
plt.show()
""")

# =====================================================================================================
md(r"""
## 5. Figure 4: the fault plane

**What it shows.** A flat plane fitted to each catalog's events (the plane that passes closest to all of them).
(a) Its strike and (b) its dip; the plane is within a few degrees of vertical in every catalog, so a small change
tips it from leaning east to leaning west: (b) therefore measures every dip toward the same side, and a value above
90° means the plane leans the other way. (c) The median and the 90th-percentile distance of the events from their
own catalog's plane: how thin the swarm is. Rows marked *own events* use all of a reference catalog's events in the
benchmark box instead of the common set. (d) The full distributions of that distance for the main catalogs.
(e-i) Sections across the fault (looking along strike, relative to each catalog's centroid), with the catalog's
plane (solid), LDEO's plane (dashed) and the median distance on either side (dotted).
""")

code(r"""
# Figure 4: plane fits, distance-from-plane distributions, and fault-normal sections with the planes
fig = plt.figure(figsize=(13.4, 11.2))
gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.12], hspace=0.24)
top = gs[0].subgridspec(1, 2, width_ratios=[3.0, 1.15], wspace=0.22)
tl = top[0].subgridspec(1, 3, width_ratios=[1.0, 1.0, 1.15], wspace=0.06)
ax_s = fig.add_subplot(tl[0])
ax_d = fig.add_subplot(tl[1], sharey=ax_s)
ax_m = fig.add_subplot(tl[2], sharey=ax_s)
ax_c = fig.add_subplot(top[1])
ypos = np.arange(len(F4_ROWS))[::-1].astype(float)
F4V = []
for y, (k, es) in zip(ypos, F4_ROWS):
    p = plane(k, es)
    st_al, dp_al = hp.aligned_strike_dip(float(p.strike), float(p.dip), SEC_STRIKE)
    F4V.append(dict(cat=k, set=es, strike=st_al, dip=dp_al, med=p.median_abs_dist_m, p90=p.p90_abs_dist_m, n=int(p.n)))
    filled = None if es == "common" else False
    ax_s.plot(st_al, y, **mk(k, filled=filled, zorder=4))
    ax_d.plot(dp_al, y, **mk(k, filled=filled, zorder=4))
    ax_m.plot([p.median_abs_dist_m, p.p90_abs_dist_m], [y, y], color=STYLE[k]["color"], lw=1.0, zorder=3)
    ax_m.plot(p.median_abs_dist_m, y, **mk(k, filled=filled, zorder=4))
    ax_m.plot(p.p90_abs_dist_m, y, ls="none", marker="|", ms=9, mew=1.6, color=STYLE[k]["color"], zorder=4)
F4V = pd.DataFrame(F4V)
ax_s.axvline(SEC_STRIKE, color="0.5", lw=0.8, ls="--", zorder=1)
ax_d.axvline(90.0, color="0.5", lw=0.8, ls="--", zorder=1)
ax_s.set_yticks(ypos)
ax_s.set_yticklabels([STYLE[k]["short"] + (" (own events)" if es == "own" else "") for k, es in F4_ROWS])
for a_ in (ax_d, ax_m):
    a_.tick_params(labelleft=False)
ax_s.set_ylim(ypos.min() - 0.7, ypos.max() + 0.7)
ax_s.set_xlabel("Strike (°)")
ax_d.set_xlabel(f"Dip toward {bearing(SEC_STRIKE + 90.0)} (°)")
ax_m.set_xlabel("Distance from the plane (m)")
ax_m.set_xlim(0.0, 1.08 * float(F4V.p90.max()))
ax_s.set_title("(a) Strike", loc="left")
ax_d.set_title("(b) Dip", loc="left")
ax_m.set_title("(c) Median and 90th percentile", loc="left")
ax_d.text(90.0, ypos.min() - 0.45, "vertical ", ha="right", va="center", fontsize=7, color="0.35")
for k in F4_CDF:
    x, yv = hp.ecdf(np.clip(np.abs(PLANE_DIST[k].to_numpy()), F4_XLIM_DIST_M[0], None))
    ax_c.step(np.r_[F4_XLIM_DIST_M[0], x], np.r_[0.0, yv], where="post", color=STYLE[k]["color"], ls=STYLE[k]["ls"], lw=1.5)
    ax_c.plot(float(np.median(np.abs(PLANE_DIST[k]))), 0.5, **mk(k, ms=6, zorder=5))
ax_c.axhline(0.5, color="0.8", lw=0.6, zorder=1)
ax_c.set_xscale("log")
plain_log(ax_c, "x")
ax_c.set_xlim(F4_XLIM_DIST_M)
ax_c.set_ylim(0, 1)
ax_c.set_xlabel("Distance from the plane (m)")
ax_c.set_ylabel("Share of events at or below")
ax_c.set_title("(d) Distance from the plane", loc="left")
# sections across the fault
bot = gs[1].subgridspec(1, len(F4_SECTIONS), wspace=0.08)
nL = hp.normal_from_strike_dip(float(plane("REF_LDEO").strike), float(plane("REF_LDEO").dip))
uu = np.array([-F4_HALF_M["U"], F4_HALF_M["U"]], float)
AXS = []
letters = iter("efghijklmn")
for i, k in enumerate(F4_SECTIONS):
    ax = fig.add_subplot(bot[i])
    r_ = rel(k)
    al, ac = hp.rotate(r_.E, r_.N, SEC_STRIKE)
    ax.scatter(ac, r_.U, s=4, color=STYLE[k]["color"], alpha=0.55, linewidths=0, zorder=2)
    p = plane(k)
    n_ = hp.normal_from_strike_dip(float(p.strike), float(p.dip))
    n_al, n_ac = hp.rotate(n_[0], n_[1], SEC_STRIKE)
    ax.plot(hp.plane_trace_in_section(n_, SEC_STRIKE, uu), uu, color="k" if k == "REF_LDEO" else STYLE[k]["color"],
            lw=1.8, zorder=4)
    for sgn in (-1.0, 1.0):
        ax.plot((sgn * p.median_abs_dist_m - n_[2] * uu) / float(n_ac), uu, color="0.2", lw=0.8, ls=":", zorder=4)
    if k != "REF_LDEO":
        ax.plot(hp.plane_trace_in_section(nL, SEC_STRIKE, uu), uu, color="k", lw=1.0, ls="--", zorder=5)
    ax.set_xlim(-F4_HALF_M["across"], F4_HALF_M["across"])
    ax.set_ylim(-F4_HALF_M["U"], F4_HALF_M["U"])
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([-F4_HALF_M["across"] / 2.0, 0.0, F4_HALF_M["across"] / 2.0])
    ax.yaxis.set_major_locator(MultipleLocator(1000))
    ax.set_xlabel("Across strike (m)")
    if i == 0:
        ax.set_ylabel("Up (m, relative to the centroid)")
    else:
        ax.tick_params(labelleft=False)
    nout = int(((np.abs(ac) > F4_HALF_M["across"]) | (r_.U.abs() > F4_HALF_M["U"])).sum())
    ax.set_title(f"({next(letters)}) {STYLE[k]['short']}", loc="left", fontsize=9)
    ax.set_title(f"{nout} outside", loc="right", fontsize=7, color="0.3")
    AXS.append(ax)
handles = [handle(k) for k in ["REF_LDEO", "REF_NCEDC", "NCSS", "P0", "S0", "P1", "S1"]]
labels = [STYLE[k]["label"] for k in ["REF_LDEO", "REF_NCEDC", "NCSS", "P0", "S0", "P1", "S1"]]
handles += [Line2D([], [], ls="none", marker="|", ms=9, mew=1.6, color="0.3"), Line2D([], [], color="0.3", lw=1.8),
            Line2D([], [], color="k", lw=1.0, ls="--"), Line2D([], [], color="0.2", lw=0.8, ls=":")]
labels += ["90th percentile (c)", "The catalog's own plane (e-i)", "LDEO's plane (e-h)", "± median distance (e-i)"]
leg = hp.legend_above(fig, [ax_s, ax_d, ax_m, ax_c], handles, labels, ncol=4, fontsize=7.5)
main = F4V[F4V.cat.isin(["REF_LDEO", "REF_NCEDC", "NCSS", "P0", "S0", "P1", "S1"])]
msg = (f"Every catalog sees the same steep plane (strike {main.strike.min():.0f}-{main.strike.max():.0f}°, dip within "
       f"{(main.dip - 90).abs().max():.0f}° of vertical); with cross-correlation the swarm is nearly as thin as in LDEO: median "
       f"distance {plane('P1').median_abs_dist_m:.0f} m (P1), {plane('S1').median_abs_dist_m:.0f} m (S1), "
       f"{plane('REF_LDEO').median_abs_dist_m:.0f} m (LDEO), against {plane('NCSS').median_abs_dist_m:.0f} m (NCSS)")
hp.text_above(fig, [leg, ax_s, ax_d, ax_m, ax_c] + AXS, msg, fontsize=9.5)
note = (f"Plane: least-squares fit (SVD) to the {len(COMMON)} common events, as analyze_sanramon.plane_fit; 'own events': "
        f"all of the reference's events in the box (LDEO {plane('REF_LDEO', 'own').n}, NCEDC DD {plane('REF_NCEDC', 'own').n}). "
        f"Sections: across-strike axis toward {bearing(SEC_STRIKE + 90.0)}; each plane is drawn where it crosses the section "
        f"through the centroid. The distances include the {len(SE_IDS)} events of the small south-east cluster, which lie "
        f"far off the plane in every catalog.")
hp.text_below(fig, AXS, textwrap.fill(note, 185), fontsize=7)
FIGS["4"] = hp.save_fig(fig, FIG_DIR, "06_4_fault_plane", dpi=FIG_DPI)
plt.show()
""")

# =====================================================================================================
md(r"""
## 6. Figure 5: pyrtdd and scrtdd give the same catalog

**What it shows.** (a) For every event, the distance between its pyrtdd and its scrtdd position, as cumulative
distributions: catalog times only (S0 vs P0) and with cross-correlation (S1 vs P1). Solid: the plain 3-D distance;
dashed: after removing the median offset of the whole catalog (the *relative* difference). (b) The relative
difference against the number of picks of the event: the large differences belong to events with few picks.
(c) The one event that ends far apart, [[OUTLIER_ID]], in a section along strike: its position in P1 and in S1 (and,
for orientation, in LDEO and the NCSS start), each relative to its own catalog's centroid, over the P1 swarm (gray).
(d) The cross-correlation lags of P1 and S1, measurement by measurement: how many are identical, one sample (1 ms)
apart, 2-10 ms apart or more than 10 ms apart.
""")

code(r"""
# Figure 5: pyrtdd vs scrtdd
D5 = {}
for a, b in F5_PAIRS:
    ids = sorted(set(SOLS[a].id) & set(SOLS[b].id))
    d = pos(b, ids) - pos(a, ids)
    dr = d - d.median()
    D5[(a, b)] = dict(abs=pd.Series(np.linalg.norm(d.to_numpy(), axis=1), index=ids),
                      rel=pd.Series(np.linalg.norm(dr.to_numpy(), axis=1), index=ids))
fig, axes = plt.subplots(1, 4, figsize=(15.6, 4.8), gridspec_kw=dict(width_ratios=[1.15, 1.15, 0.75, 1.0], wspace=0.42))
ax = axes[0]
for a, b in F5_PAIRS:
    for kind, ls in (("abs", "-"), ("rel", "--")):
        v = D5[(a, b)][kind]
        x, y = hp.ecdf(np.clip(v.to_numpy(), F5_XLIM_M[0], None))
        ax.step(np.r_[F5_XLIM_M[0], x], np.r_[0.0, y], where="post", color=STYLE[b]["color"], ls=ls, lw=1.5)
        ax.plot(float(v.median()), 0.5, **mk(b, ms=6, filled=(kind == "abs"), zorder=5))
ax.axhline(0.5, color="0.8", lw=0.6, zorder=1)
ax.set_xscale("log")
ax.set_xlim(F5_XLIM_M)
ax.set_ylim(0, 1)
plain_log(ax, "x")
ax.set_xlabel("scrtdd minus pyrtdd, per event (m)")
ax.set_ylabel("Share of events at or below")
ax.set_title("(a) Position differences", loc="left")
ax = axes[1]
for a, b in F5_PAIRS:
    v = D5[(a, b)]["rel"]
    ax.plot(NPICK.loc[v.index, "all"], np.clip(v.to_numpy(), F5_XLIM_M[0], None), **mk(b, ms=4.0, mew=0.8, zorder=3, alpha=0.8))
vo = D5[("P1", "S1")]["rel"]
ax.annotate(f"{OUTLIER_ID}\n{MT} {MAG.loc[OUTLIER_ID]:.2f}, {NPICK.loc[OUTLIER_ID, 'P']} P + {NPICK.loc[OUTLIER_ID, 'S']} S picks",
            (NPICK.loc[OUTLIER_ID, "all"], vo.loc[OUTLIER_ID]), xytext=(14, -6), textcoords="offset points", fontsize=7.5,
            va="top", arrowprops=dict(arrowstyle="-", lw=0.6, color="0.3"))
ax.set_xscale("log")
ax.set_yscale("log")
plain_log(ax, "x")
plain_log(ax, "y")
ax.set_ylim(F5_XLIM_M[0] * 0.7, 2.0 * float(vo.max()))
ax.set_xlabel("Picks of the event (P + S)")
ax.set_ylabel("Relative difference, scrtdd minus pyrtdd (m)")
ax.set_title("(b) Differences and number of picks", loc="left")
# (c) the outlier event, along-strike section
ax = axes[2]
r1 = rel("P1")
al1, _ = hp.rotate(r1.E, r1.N, SEC_STRIKE)
ax.scatter(al1, r1.U, s=3, color="0.75", linewidths=0, zorder=2)
OPOS = {}
for k in ("NCSS", "REF_LDEO", "P1", "S1"):
    rk = rel(k).loc[OUTLIER_ID]
    a_, _ = hp.rotate(rk.E, rk.N, SEC_STRIKE)
    OPOS[k] = (float(a_), float(rk.U))
    ax.plot(*OPOS[k], **mk(k, ms=8, zorder=5))
ax.annotate("", OPOS["S1"], OPOS["P1"], arrowprops=dict(arrowstyle="->", lw=0.9, color="0.25", shrinkA=5, shrinkB=5), zorder=4)
partner = int(OUT_KEY.eventId1 if OUT_KEY.eventId2 == OUTLIER_ID else OUT_KEY.eventId2)
rp = r1.loc[partner]
ap_, _ = hp.rotate(rp.E, rp.N, SEC_STRIKE)
ax.plot(float(ap_), float(rp.U), ls="none", marker="+", ms=10, mew=1.4, color="k", zorder=6)
xs_ = [v[0] for v in OPOS.values()] + [float(ap_)]
ys_ = [v[1] for v in OPOS.values()] + [float(rp.U)]
ax.set_xlim(min(xs_ + [float(np.quantile(al1, 0.01))]) - F5_SECTION_PAD_M, max(xs_ + [float(np.quantile(al1, 0.99))]) + F5_SECTION_PAD_M)
ax.set_ylim(min(ys_ + [float(np.quantile(r1.U, 0.01))]) - F5_SECTION_PAD_M, max(ys_) + F5_SECTION_PAD_M)
ax.set_aspect("equal", adjustable="datalim")
ax.xaxis.set_major_locator(MultipleLocator(1000))
ax.yaxis.set_major_locator(MultipleLocator(1000))
ax.set_xlabel(f"Along strike, toward {bearing(SEC_STRIKE)} (m)")
ax.set_ylabel("Up, relative to the centroid (m)")
ax.set_title(f"(c) Event {OUTLIER_ID}", loc="left")
# (d) lags
ax = axes[3]
cats = list(LAGCAT)
colors = ["0.1", "0.45", "0.72", "white"]
hatches = [None, None, None, "////"]
wbar = 0.2
for j, ph in enumerate(("P", "S")):
    g = TB.phaseType == ph
    for i_, c in enumerate(cats):
        n_ = int((LAGCAT[c] & g).sum())
        x_ = j + (i_ - 1.5) * wbar
        ax.bar(x_, max(n_, 0.6), width=wbar * 0.92, color=colors[i_], edgecolor="k", lw=0.6, hatch=hatches[i_], zorder=3)
        ax.text(x_, max(n_, 0.6) * 1.25, f"{n_:,}", ha="center", va="bottom", fontsize=6.8, rotation=90)
ax.set_yscale("log")
ax.set_ylim(0.5, 5e6)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.set_xticks([0, 1])
ax.set_xticklabels([f"P ({int((TB.phaseType == 'P').sum()):,} measured by both)",
                    f"S ({int((TB.phaseType == 'S').sum()):,})"])
ax.set_ylabel("Measurements")
ax.set_title("(d) Lags, S1 vs P1", loc="left")
handles = [Line2D([], [], color=STYLE["S0"]["color"], lw=1.5, ls="-"), Line2D([], [], color=STYLE["S0"]["color"], lw=1.5, ls="--"),
           Line2D([], [], color=STYLE["S1"]["color"], lw=1.5, ls="-"), Line2D([], [], color=STYLE["S1"]["color"], lw=1.5, ls="--"),
           handle("S0", ms=4.0, mew=0.8), handle("S1", ms=4.0, mew=0.8)]
labels = ["S0 vs P0, 3-D (a)", "S0 vs P0, relative (a)", "S1 vs P1, 3-D (a)", "S1 vs P1, relative (a)",
          "S0 vs P0, per event (b)", "S1 vs P1, per event (b)"]
handles += [handle(k, ms=7) for k in ("P1", "S1", "REF_LDEO", "NCSS")] + [
    Line2D([], [], ls="none", marker="+", ms=9, mew=1.4, color="k"), Line2D([], [], ls="none", marker="o", ms=4, mfc="0.75", mec="none")]
labels += [f"{OUTLIER_ID} in P1 (c)", f"{OUTLIER_ID} in S1 (c)", f"{OUTLIER_ID} in LDEO (c)", f"{OUTLIER_ID} at the NCSS start (c)",
           f"Event {partner}, in P1 (c)", "P1 swarm (c)"]
handles += [Patch(facecolor=c_, edgecolor="k", hatch=h_, lw=0.6) for c_, h_ in zip(colors, hatches)]
LAGLAB = {"identical": "Identical lags", "one sample (1 ms)": "Lags 1 ms (one sample) apart", "2-10 ms": "Lags 2-10 ms apart",
          "more than 10 ms": "Lags more than 10 ms apart"}
labels += [f"{LAGLAB[c]} (d)" for c in cats]
leg = hp.legend_above(fig, axes, handles, labels, ncol=4, fontsize=7.3)
s0, s1 = D5[("P0", "S0")], D5[("P1", "S1")]
CCX = TB.loc[(TB.coefficient_py - TB.coefficient_sc).abs().idxmax()]
msg = (f"pyrtdd and scrtdd give the same catalog: median distance {s0['abs'].median():.2f} m (S0 vs P0) and "
       f"{s1['abs'].median():.1f} m (S1 vs P1), {LAGCAT['identical'].mean():.1%} of the lags identical; one event with "
       f"{NPICK.loc[OUTLIER_ID, 'all']} picks ends {s1['abs'].loc[OUTLIER_ID] / 1000:.1f} km apart over a single S lag")
hp.text_above(fig, [leg] + list(axes), msg, fontsize=9.5)
note = (f"(c) The only lag of {OUTLIER_ID} that differs by more than 1 ms is its {OUT_KEY.phaseType} at "
        f"{OUT_KEY.networkCode}.{OUT_KEY.stationCode} with event {partner}: {1000 * OUT_KEY.lag_py:+.0f} ms in P1 (CC "
        f"{OUT_KEY.coefficient_py:.3f}) against {1000 * OUT_KEY.lag_sc:+.0f} ms in S1 (CC {OUT_KEY.coefficient_sc:.3f}): two "
        f"almost equally high correlation peaks. Depth {C['out_zP1']:.1f} km in P1, {C['out_zS1']:.1f} km in S1, "
        f"{C['out_zL']:.1f} km in LDEO. (d) {int(SIDE.sum())} measurements lie on opposite sides of |CC| = {CC_MIN:g} "
        f"(P {int((SIDE & (TB.phaseType == 'P')).sum())}, S {int((SIDE & (TB.phaseType == 'S')).sum())}); the largest CC "
        f"difference is a sign flip ({CCX.phaseType} at {CCX.networkCode}.{CCX.stationCode}: {CCX.coefficient_py:+.3f} in P1, "
        f"{CCX.coefficient_sc:+.3f} in S1). Differences below {F5_XLIM_M[0]:g} m are drawn at the left edge (a) or bottom (b).")
hp.text_below(fig, list(axes), textwrap.fill(note, 200), fontsize=7)
FIGS["5"] = hp.save_fig(fig, FIG_DIR, "06_5_pyrtdd_vs_scrtdd", dpi=FIG_DPI)
plt.show()
""")

# =====================================================================================================
md(r"""
## 7. Figure 6: cross-correlation measurements and residuals

**What it shows.** The cross-correlation measurements of P1 (S1's are the same up to the differences of Figure 5)
and how well the final positions explain the data.
(a) How many event pairs could be correlated at each station and phase, how many had waveforms for both events
(measured), and how many rtDD accepted (|CC| ≥ [[CC_MIN]]), split into positive and negative correlations.
(b) All measured correlation coefficients: rtDD accepts both shaded zones, including the negative one (mirror-image
matches: a flipped polarity, or the wrong peak of an oscillating wave). (c) The size of the accepted lags (the
correction to the picked time difference): negative matches need much longer ones. (d) Double-difference residuals
of P1 before (first iteration) and after (last iteration), for the cross-correlation data and the catalog data.
(e) The spread (MAD) of those residuals before and after, for several runs. (f) The diagnostic run P1pos, in which
the negative P matches were turned back into catalog times (not an rtDD option): its agreement with LDEO next to
P1's.
""")

code(r"""
# Figure 6: cross-correlation statistics and residuals
fig, axes = plt.subplots(2, 3, figsize=(15.0, 9.0), gridspec_kw=dict(hspace=0.36, wspace=0.36))
(axa, axb, axc), (axd, axe, axf) = axes
# (a) counts
rowsA = []
for ph in ("P", "S"):
    rowsA += [(ph, "Phase pairs", XCOUNT[ph]["pairs"]), (ph, "Measured", XCOUNT[ph]["measured"]),
              (ph, f"|CC| ≥ {CC_MIN:g}", None)]
ya = np.arange(len(rowsA))[::-1].astype(float)
ya[:3] += 0.6
for y, (ph, what, n_) in zip(ya, rowsA):
    if n_ is not None:
        axa.barh(y, n_, color="0.82" if what == "Phase pairs" else "0.6", edgecolor="k", lw=0.5, height=0.72, zorder=3)
        axa.text(n_, y, f" {n_:,}", va="center", ha="left", fontsize=7.5)
    else:
        p_, n2 = XCOUNT[ph]["pos"], XCOUNT[ph]["neg"]
        axa.barh(y, p_, color="0.25", edgecolor="k", lw=0.5, height=0.72, zorder=3)
        axa.barh(y, n2, left=p_, color=NEG_COLOR, edgecolor="k", lw=0.5, height=0.72, zorder=3)
        axa.text(p_ + n2, y, f" {p_ + n2:,} ({p_:,} + {n2:,})", va="center", ha="left", fontsize=7.5)
axa.set_yticks(ya)
axa.set_yticklabels([f"{ph}: {w}" for ph, w, _ in rowsA])
axa.set_xlim(0, 1.55 * XCOUNT["P"]["pairs"])
axa.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1000:g}"))
axa.set_xlabel("Number (thousands)")
axa.set_title("(a) Correlations by phase", loc="left")
# (b) CC histogram
edges = np.linspace(-1.0, 1.0, int(round(2.0 / F6_CC_BIN)) + 1)
axb.axvspan(CC_MIN, 1.0, color="0.88", zorder=1)
axb.axvspan(-1.0, -CC_MIN, color=NEG_COLOR, alpha=0.15, lw=0, zorder=1)
for ph, col_, ls_ in (("P", "k", "-"), ("S", "0.45", "--")):
    v = XV[XV.phaseType == ph].coefficient
    axb.hist(v, bins=edges, histtype="step", color=col_, ls=ls_, lw=1.3, zorder=3)
axb.set_xlim(-1, 1)
axb.set_xlabel("Correlation coefficient CC")
axb.set_ylabel(f"Measurements per {F6_CC_BIN:g} bin")
axb.set_title("(b) Measured coefficients", loc="left")
# (c) lags
for v, col_, ls_ in ((LAG_POS, "k", "-"), (LAG_NEG, NEG_COLOR, "-"), (LAG_S, "0.45", "--")):
    x, y = hp.ecdf(v.to_numpy())
    axc.step(np.r_[0.0, x], np.r_[0.0, y], where="post", color=col_, ls=ls_, lw=1.5)
    axc.plot(float(v.median()), 0.5, ls="none", marker="o", ms=5, color=col_, zorder=5)
axc.axhline(0.5, color="0.8", lw=0.6, zorder=1)
axc.set_xlim(0, F6_LAG_MAX_MS)
axc.set_ylim(0, 1)
axc.set_xlabel("|Lag| of the accepted measurements (ms)")
axc.set_ylabel("Share at or below")
axc.set_title("(c) Lag sizes", loc="left")
# (d) residual histograms
edges_r = np.arange(-F6_RES_LIM_MS, F6_RES_LIM_MS + F6_RES_BIN_MS, F6_RES_BIN_MS)
RSPEC = [("xcorr", "initial", "k", ":"), ("xcorr", "final", "k", "-"), ("catalog", "initial", "0.55", ":"),
         ("catalog", "final", "0.55", "-")]
OUTSIDE = {}
for sub, st, col_, ls_ in RSPEC:
    d = DD[st]
    g = d[d.xcorrUsed] if sub == "xcorr" else d[~d.xcorrUsed]
    OUTSIDE[(sub, st)] = float((g.res_ms.abs() > F6_RES_LIM_MS).mean())
    axd.hist(g.res_ms, bins=edges_r, histtype="step", color=col_, ls=ls_, lw=1.3)
axd.set_yscale("log")
axd.set_xlim(-F6_RES_LIM_MS, F6_RES_LIM_MS)
axd.set_xlabel("Double-difference residual (ms)")
axd.set_ylabel(f"Data per {F6_RES_BIN_MS:g}-ms bin")
axd.set_title("(d) Residuals of P1", loc="left")
# (e) MAD before and after
ye = np.arange(len(F6_MAD_ROWS))[::-1].astype(float)
SUBTXT = {"xcorr": "correlation data", "catalog": "catalog data", "all": "all data"}
for y, (run, sub) in zip(ye, F6_MAD_ROWS):
    i_, f_ = res(run, "initial", sub).mad_ms, res(run, "final", sub).mad_ms
    axe.annotate("", (f_, y), (i_, y), arrowprops=dict(arrowstyle="->", lw=0.9, color=STYLE[run]["color"], shrinkA=4, shrinkB=4))
    axe.plot(i_, y, **mk(run, filled=False, ms=6))
    axe.plot(f_, y, **mk(run, filled=True, ms=6))
    axe.text(max(i_, f_) + 1.5, y, f"{i_:.1f} → {f_:.1f}", va="center", fontsize=7.5)
axe.set_yticks(ye)
axe.set_yticklabels([f"{run}: {SUBTXT[sub]}" for run, sub in F6_MAD_ROWS])
axe.set_xlim(0, 1.3 * max(res(r, "initial", s).mad_ms for r, s in F6_MAD_ROWS))
axe.set_ylim(ye.min() - 0.7, ye.max() + 0.7)
axe.set_xlabel("Residual MAD (ms): first → last iteration")
axe.set_title("(e) Residual spread", loc="left")
# (f) P1pos vs P1 against LDEO
MF = [("rel_h_median_m", "Relative\nhorizontal"), ("rel_v_median_m", "Relative\nvertical"),
      ("local_h_median_m", "Local\nhorizontal"), ("local_v_median_m", "Local\nvertical")]
for i_, (c, t_) in enumerate(MF):
    a_, b_ = float(met("P1")[c]), float(met("P1pos")[c])
    axf.plot(i_ - 0.12, a_, **mk("P1", ms=7))
    axf.plot(i_ + 0.12, b_, **mk("P1pos", ms=7))
    axf.annotate("", (i_ + 0.12, b_), (i_ - 0.12, a_), arrowprops=dict(arrowstyle="->", lw=0.8, color="0.35", shrinkA=5, shrinkB=5))
    axf.text(i_, max(a_, b_) + 6, f"{a_:.0f} → {b_:.0f}", ha="center", va="bottom", fontsize=7.5)
axf.set_xticks(range(len(MF)))
axf.set_xticklabels([t_ for _, t_ in MF])
axf.set_xlim(-0.6, len(MF) - 0.4)
axf.set_ylim(0, 1.25 * max(float(met(k)[c]) for k in ("P1", "P1pos") for c, _ in MF))
axf.set_ylabel("Median distance from LDEO (m)")
axf.set_title("(f) Negative correlations dropped (P1pos)", loc="left")
handles = [Patch(facecolor="0.82", edgecolor="k", lw=0.5), Patch(facecolor="0.6", edgecolor="k", lw=0.5),
           Patch(facecolor="0.25", edgecolor="k", lw=0.5), Patch(facecolor=NEG_COLOR, edgecolor="k", lw=0.5),
           Line2D([], [], color="k", lw=1.3), Line2D([], [], color="0.45", lw=1.3, ls="--"),
           Line2D([], [], color=NEG_COLOR, lw=1.5),
           Line2D([], [], color="k", lw=1.3, ls=":"), Line2D([], [], color="k", lw=1.3),
           Line2D([], [], color="0.55", lw=1.3, ls=":"), Line2D([], [], color="0.55", lw=1.3),
           handle("P1", filled=False), handle("P1pos")]
labels = ["Phase pairs (a)", "Measured: waveforms of both events (a)", f"Accepted, CC ≥ +{CC_MIN:g} (a)",
          f"Accepted, CC ≤ -{CC_MIN:g} (a, b, c)", "P (b), accepted positive P (c)", "S (b, c)", "Accepted negative P (c)",
          "Cross-correlation data, first iteration (d)", "Cross-correlation data, last iteration (d)",
          "Catalog data, first iteration (d)", "Catalog data, last iteration (d)",
          STYLE["P1"]["label"] + " (f)", STYLE["P1pos"]["label"] + " (f)"]
leg = hp.legend_above(fig, axes, handles, labels, ncol=4, fontsize=7.3)
msg = (f"rtDD accepts {XCOUNT['P']['acc']:,} P and {XCOUNT['S']['acc']:,} S correlations, {XCOUNT['P']['neg']:,} of the P "
       f"ones negative (median lag {LAG_NEG.median():.0f} ms against {LAG_POS.median():.0f} ms); the cross-correlation "
       f"residual spread falls from {res('P1', 'initial', 'xcorr').mad_ms:.0f} to {res('P1', 'final', 'xcorr').mad_ms:.0f} ms")
hp.text_above(fig, [leg] + list(axes.ravel()), msg, fontsize=9.5)
note = (f"(a-c) P1's correlation cache: one measurement per event pair, station and phase; P on the vertical "
        f"component, S on both horizontals combined (non-negative, hence no negative S). (d) libhdd's own "
        f"double-difference files; residuals beyond ±{F6_RES_LIM_MS} ms are off the axis (cross-correlation "
        f"{OUTSIDE[('xcorr', 'initial')]:.1%} first / {OUTSIDE[('xcorr', 'final')]:.1%} last; catalog "
        f"{OUTSIDE[('catalog', 'initial')]:.1%} / {OUTSIDE[('catalog', 'final')]:.1%}). In the last iteration "
        f"{C['w_pos']:.0f}% of the positive correlations (P and S) and {C['w_neg']:.0f}% of the negative ones (all P) still "
        f"carry weight. "
        f"(e) Open symbols: first iteration; filled: last; 'correlation data' = the double differences measured by "
        f"cross-correlation. (f) P1pos moves the events by a median of {rvr('P1', 'P1pos').rel3d_median_m:.0f} m relative to P1 "
        f"({int(rvr('P1', 'P1pos').n_rel3d_gt_100m)} events by more than 100 m).")
hp.text_below(fig, list(axes[1]), textwrap.fill(note, 200), fontsize=7)
FIGS["6"] = hp.save_fig(fig, FIG_DIR, "06_6_cross_correlation", dpi=FIG_DPI)
plt.show()
""")

# =====================================================================================================
md(r"""
## 8. Figure 7: absolute position (a caveat)

**What it shows.** Where each run puts the swarm as a whole: the offset of its centroid from LDEO's centroid,
east, north and up (positive = shallower), on the common events. The gray dashed line is the NCSS routine start,
the green dotted line NCEDC DD. The top axis of (c) converts the up offset into the mean depth below sea level. The
runs are grouped by their solver settings (read from the run folders). (d) The median per-event absolute
travel-time RMS (how well each event's own arrival times are fit) at the start and after relocation, as rtDD reports
it. These offsets come from the velocity model and the solver, not from the relative geometry: compare the swarm's
shape between catalogs, not its absolute position.
""")

code(r"""
# Figure 7: centroid offsets from LDEO and the absolute RMS
groups7 = {}
for r in F7_RUNS:
    groups7.setdefault((SET[r]["absloc"], SET[r]["damping"]), []).append(r)
rows7, ylab7, yhdr7 = [], [], []
y = 0.0
for (al_, dmp), runs_ in groups7.items():
    yhdr7.append((y, f"absLocConstraint {al_:g}, damping {dmp:g}"))
    y -= 1.0
    for r in runs_:
        rows7.append((r, y))
        y -= 1.0
    y -= 0.4
fig, axes = plt.subplots(1, 4, figsize=(15.0, 5.6), sharey=True, gridspec_kw=dict(wspace=0.08, width_ratios=[1, 1, 1.25, 1]))
COMP7 = [("centroid_shift_E_m", "(a) East"), ("centroid_shift_N_m", "(b) North"), ("centroid_shift_U_m", "(c) Up")]
for ax, (c, tt) in zip(axes[:3], COMP7):
    ax.axvline(0.0, color="k", lw=1.0, zorder=1)
    ax.axvline(float(met("NCSS")[c]), color=STYLE["NCSS"]["color"], lw=1.1, ls="--", zorder=1)
    ax.axvline(float(met("REF_NCEDC")[c]), color=STYLE["REF_NCEDC"]["color"], lw=1.3, ls=":", zorder=1)
    for r, yy in rows7:
        ax.plot(float(met(r)[c]), yy, **mk(r, ms=7, zorder=4))
    ax.set_xlabel("Centroid minus LDEO's centroid (m)")
    ax.set_title(tt, loc="left")
lo_, hi_ = axes[2].get_xlim()
axes[2].set_xlim(lo_ - 0.08 * (hi_ - lo_), hi_ + 0.08 * (hi_ - lo_))
ZL = ZMEAN["REF_LDEO"]
sec = axes[2].secondary_xaxis("top", functions=(lambda u: ZL - u / 1000.0, lambda z: (ZL - z) * 1000.0))
sec.set_xlabel("Mean depth below sea level (km)", fontsize=8)
ax = axes[3]
for r, yy in rows7:
    s_, f_ = float(RT.loc[r, "event_startRms_median_ms"]), float(RT.loc[r, "event_finalRms_median_ms"])
    ax.annotate("", (f_, yy), (s_, yy), arrowprops=dict(arrowstyle="->", lw=0.9, color=STYLE[r]["color"], shrinkA=4, shrinkB=4))
    ax.plot(s_, yy, **mk(r, filled=False, ms=6))
    ax.plot(f_, yy, **mk(r, filled=True, ms=6))
    ax.text(max(s_, f_) + 6, yy, f"{s_:.0f} → {f_:.0f}", va="center", fontsize=7.5)
ax.set_xlim(0.9 * min(RT.loc[F7_RUNS, "event_startRms_median_ms"].min(), RT.loc[F7_RUNS, "event_finalRms_median_ms"].min()),
            1.18 * RT.loc[F7_RUNS, "event_finalRms_median_ms"].max())
ax.set_xlabel("Median per-event absolute RMS (ms): start → final")
ax.set_title("(d) Absolute travel-time fit", loc="left")
axes[0].set_yticks([yy for _, yy in rows7])
axes[0].set_yticklabels([f"{SET[r]['program']} {r}" for r, _ in rows7])
for yy, t_ in yhdr7:
    axes[0].text(0.01, yy, t_, transform=axes[0].get_yaxis_transform(), ha="left", va="center", fontsize=8, color="0.2",
                 bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"), zorder=6)
axes[0].set_ylim(min(yy for _, yy in rows7) - 0.8, 0.6)
handles = [Line2D([], [], color="k", lw=1.0), Line2D([], [], color=STYLE["NCSS"]["color"], lw=1.1, ls="--"),
           Line2D([], [], color=STYLE["REF_NCEDC"]["color"], lw=1.3, ls=":")] + [handle(r) for r, _ in rows7]
labels = ["LDEO (reference)", STYLE["NCSS"]["label"], STYLE["REF_NCEDC"]["label"]] + [STYLE[r]["label"] for r, _ in rows7]
leg = hp.legend_above(fig, axes, handles, labels, ncol=4, fontsize=7.3)
dU = {r: float(met(r).centroid_shift_U_m) / 1000.0 for r in F7_RUNS}
gdef = [r for r in F7_RUNS if SET[r]["absloc"] > 0]
ga0 = [r for r in F7_RUNS if SET[r]["absloc"] == 0 and SET[r]["damping"] < 0.5]
gd1 = [r for r in F7_RUNS if SET[r]["absloc"] == 0 and SET[r]["damping"] >= 0.5]
msg = (f"Do not use the absolute positions: the default solver puts the swarm {-max(dU[r] for r in gdef):.1f}-"
       f"{-min(dU[r] for r in gdef):.1f} km deeper than LDEO, without absolute equations it ends {min(dU[r] for r in ga0):.1f}-"
       f"{max(dU[r] for r in ga0):.1f} km shallower, and strong damping keeps it at the NCSS start "
       f"({-max(dU[r] for r in gd1) * 1000:.0f}-{-min(dU[r] for r in gd1) * 1000:.0f} m deeper than LDEO)")
hp.text_above(fig, [leg] + list(axes), msg, fontsize=9.5)
note = (f"{len(COMMON)} common events. Mean depths: LDEO {ZMEAN['REF_LDEO']:.2f} km, NCSS {ZMEAN['NCSS']:.2f} km, "
        f"NCEDC DD {ZMEAN['REF_NCEDC']:.2f} km (its {len(COMMON_NC)} events, depths moved to sea level with the NCSS datum). "
        f"Drift from the NCSS start without absolute equations: "
        + ", ".join(f"{r} {UP_FROM_START[r]:.1f} km up" for r in UP_FROM_START)
        + ". (d) rtDD's startRms / finalRms per event (CON model, no station corrections).")
hp.text_below(fig, list(axes), textwrap.fill(note, 200), fontsize=7)
FIGS["7"] = hp.save_fig(fig, FIG_DIR, "06_7_absolute_position", dpi=FIG_DPI)
plt.show()
""")

# =====================================================================================================
md(r"""
## 9. Figure 8: sensitivity runs

**What it shows.** The four median distances from LDEO (relative and local, horizontal and vertical) for every run,
grouped into catalog-only and cross-correlation runs; the NCSS start and NCEDC DD are shown for scale. Each run
changes one setting relative to P0 or P1 (settings in section 1.1). The dotted vertical line in each panel is P1's
value. Smaller is closer to LDEO.
""")

code(r"""
# Figure 8: medians against LDEO for every run
COLS8 = [("rel_h_median_m", "(a) Relative, horizontal"), ("rel_v_median_m", "(b) Relative, vertical"),
         ("local_h_median_m", "(c) Local, horizontal"), ("local_v_median_m", "(d) Local, vertical")]
rows8, hdr8 = [], []
y = 0.0
for gname, runs_ in F8_GROUPS:
    hdr8.append((y, gname))
    y -= 1.0
    for r in runs_:
        rows8.append((r, y))
        y -= 1.0
    y -= 0.4
fig, axes = plt.subplots(1, 4, figsize=(14.6, 6.4), sharey=True, gridspec_kw=dict(wspace=0.07))
for ax, (c, tt) in zip(axes, COLS8):
    vals = [float(met(r)[c]) for r, _ in rows8]
    ax.axvline(float(met("P1")[c]), color=STYLE["P1"]["color"], lw=1.0, ls=":", zorder=1)
    for (r, yy), v in zip(rows8, vals):
        ax.plot(v, yy, **mk(r, ms=7, zorder=4))
        ax.text(v, yy - 0.42, f"{v:.0f}", ha="center", va="center", fontsize=6.8, color="0.15")
    ax.set_xlim(0.0, 1.12 * max(vals))
    ax.set_xlabel("Median distance from LDEO (m)")
    ax.set_title(tt, loc="left")
axes[0].set_yticks([yy for _, yy in rows8])
axes[0].set_yticklabels([(f"{SET[r]['program']} {r}" if r in SET else STYLE[r]["short"]) for r, _ in rows8])
for yy, t_ in hdr8:
    axes[0].text(0.01, yy, t_, transform=axes[0].get_yaxis_transform(), ha="left", va="center", fontsize=8, color="0.2",
                 bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"), zorder=6)
axes[0].set_ylim(min(yy for _, yy in rows8) - 0.9, 0.6)
handles = [handle(r) for r, _ in rows8] + [Line2D([], [], color=STYLE["P1"]["color"], lw=1.0, ls=":")]
labels = [STYLE[r]["label"] for r, _ in rows8] + ["P1's value"]
leg = hp.legend_above(fig, axes, handles, labels, ncol=4, fontsize=7.3)
cand = [r for _, rs in F8_GROUPS[1:] for r in rs]
P1ROW = met("P1")
best = {c: min(cand, key=lambda r: float(met(r)[c])) for c, _ in COLS8}
msg = ("Cross-correlation matters most; among the variants no setting wins everywhere (best: "
       + "; ".join(f"{t_.split(') ')[1].replace(',', '').lower()} {best[c]}, {float(met(best[c])[c]):.0f} m" for c, t_ in COLS8)
       + "; P1: " + " / ".join(f"{float(P1ROW[c]):.0f}" for c, _ in COLS8) + " m)")
hp.text_above(fig, [leg] + list(axes), msg, fontsize=9.5)
note = (f"{len(COMMON)} common events against LDEO ({len(per('REF_NCEDC'))} for NCEDC DD). P1n, P1a0, P1d1 and P1pos re-use "
        f"P1's correlations. Settings of every run: section 1.1 (P0n/P1n: nearest-neighbor pairs, {solver_txt('P1n')}; "
        f"P0a0/P1a0: {solver_txt('P1a0')}; P0d1/P1d1: {solver_txt('P1d1')}; others: {solver_txt('P1')}). Absolute positions "
        f"of these runs differ by kilometers (Figure 7); this figure compares only the shape.")
hp.text_below(fig, list(axes), textwrap.fill(note, 190), fontsize=7)
FIGS["8"] = hp.save_fig(fig, FIG_DIR, "06_8_sensitivity_runs", dpi=FIG_DPI)
plt.show()
""")

# =====================================================================================================
md(r"""
## 10. Comprehensive summary

The table collects the numbers behind the figures (all computed above from the result files). The take-home
messages and caveats below are written from the same variables.
""")

code(r"""
# 10. key numbers
def mtxt(sol, ref="LDEO"):
    m = met(sol, ref)
    return (f"relative {m.rel_h_median_m:.0f} / {m.rel_v_median_m:.0f} m, local {m.local_h_median_m:.0f} / "
            f"{m.local_v_median_m:.0f} m (horizontal / vertical medians)")


K = []
K.append(("Events", f"{N_EV} input (NCSS routine start, {len(PH):,} analyst picks); {C['n_relocated']} relocated by every run; "
          f"{len(DROPPED)} dropped in every run (each fewer than {SET['P0']['min_phases']} picks)", "Section 1.2"))
for k in ("NCSS", "P0", "S0", "P1", "S1", "REF_NCEDC"):
    K.append((f"{STYLE[k]['label']} vs LDEO", mtxt(k), "Figures 2, 8"))
K.append(("Closer to LDEO than the NCSS start (P1)", f"{met('P1').frac_events_closer_than_NCSS_rel3d:.0%} of events (relative 3-D), "
          f"{met('P1').frac_events_closer_than_NCSS_local:.0%} (local); P0: {met('P0').frac_events_closer_than_NCSS_rel3d:.0%} / "
          f"{met('P0').frac_events_closer_than_NCSS_local:.0%}", "Figure 3"))
K.append(("Improvement factor over the start (P1)", f"{met('P1').improvement_rel_3d:.1f}× (relative 3-D), "
          f"{met('P1').improvement_local_h:.1f}× / {met('P1').improvement_local_v:.1f}× (local horizontal / vertical)", "Figures 2, 3"))
K.append(("LDEO's own errors and spacing", f"median 95% error {LDEO_EH:.0f} m horizontal, {LDEO_EZ:.0f} m vertical; median "
          f"distance to the {K_NEIGH} nearest neighbors {NB:.0f} m", "Figure 2"))
for k in ("REF_LDEO", "NCSS", "P0", "P1", "S1"):
    p = plane(k)
    K.append((f"Plane of {STYLE[k]['short']}", f"strike {p.strike:.1f}°, dip {p.dip:.1f}° toward {p.dip_direction:.0f}°; median "
              f"distance {p.median_abs_dist_m:.0f} m, RMS {p.thickness_rms_m:.0f} m; down-dip spread {p.spread_down_dip_rms_m:.0f} m", "Figures 1, 4"))
K.append(("pyrtdd vs scrtdd", f"S0 vs P0 median {rvr('P0', 'S0').abs3d_median_m:.2f} m (relative {rvr('P0', 'S0').rel3d_median_m:.2f} m); "
          f"S1 vs P1 median {rvr('P1', 'S1').abs3d_median_m:.2f} m (relative {rvr('P1', 'S1').rel3d_median_m:.2f} m), largest "
          f"{rvr('P1', 'S1').abs3d_max_m / 1000:.1f} km ({OUTLIER_ID}); lags identical {C['lag_identical']:,} of {len(TB):,} "
          f"({C['lag_identical_pct']:.1f}%)", "Figure 5"))
K.append(("Correlations accepted (P1)", f"P {XCOUNT['P']['acc']:,} of {XCOUNT['P']['measured']:,} measured ({XCOUNT['P']['neg']:,} "
          f"negative); S {XCOUNT['S']['acc']:,} of {XCOUNT['S']['measured']:,}", "Figure 6"))
K.append(("Accepted P lags (median |lag|)", f"positive {LAG_POS.median():.0f} ms, negative {LAG_NEG.median():.0f} ms", "Figure 6"))
K.append(("Residual MAD (P1)", f"cross-correlation data {C['mad_xc_i']:.1f} → {C['mad_xc_f']:.1f} ms; catalog data "
          f"{C['mad_cat_i']:.1f} → {C['mad_cat_f']:.1f} ms", "Figure 6"))
K.append(("P1pos (negative CC dropped) vs P1, against LDEO", f"{mtxt('P1pos')}; moves events by a median of "
          f"{rvr('P1', 'P1pos').rel3d_median_m:.0f} m", "Figure 6"))
for r in ("P0", "P1", "P0a0", "P1a0", "P0d1", "P1d1"):
    m = met(r)
    K.append((f"{r} centroid minus LDEO's ({solver_txt(r)})", f"{m.centroid_shift_E_m:+.0f} / {m.centroid_shift_N_m:+.0f} / "
              f"{m.centroid_shift_U_m:+.0f} m (east / north / up); mean depth {ZMEAN[r]:.2f} km (LDEO {ZMEAN['REF_LDEO']:.2f} km)", "Figure 7"))
for r in ("P0n", "P1n", "P0a0", "P1a0", "P0d1", "P1d1"):
    K.append((f"Sensitivity: {r} vs LDEO", mtxt(r), "Figure 8"))
K.append(("Cross-file consistency checks", f"{int(CHK.Consistent.sum())} of {len(CHK)} consistent", "Section 1.3"))
K.append(("Note 11 against the files", f"{int((N11.Consistent == 'yes').sum())} of {len(N11)} numbers agree", "Section 1.4"))
KEY = pd.DataFrame(K, columns=["Quantity", "Value", "Where"])
display(Markdown(hp.md_table(KEY)))
""")

code(r"""
# 10. take-home messages, written from the numbers above
m0, m1, s1m, mn, mr = met("P0"), met("P1"), met("S1"), met("NCSS"), met("REF_NCEDC")
pL, p1p, pN = plane("REF_LDEO"), plane("P1"), plane("NCSS")
lines = [
    f"- **Does rtDD reproduce a published double-difference catalog on public data? Its relative structure, yes, with "
    f"cross-correlation.** P1 (pyrtdd) and S1 (scrtdd) differ from LDEO by a median of {m1.rel_h_median_m:.0f} / "
    f"{m1.rel_v_median_m:.0f} m (relative, horizontal / vertical) and {m1.local_h_median_m:.0f} / {m1.local_v_median_m:.0f} m "
    f"at the scale of each event's {K_NEIGH} nearest neighbors, which is closer to LDEO than the other published "
    f"catalog, NCEDC DD, is ({mr.local_h_median_m:.0f} / {mr.local_v_median_m:.0f} m locally) (Figures 1, 2).",
    f"- **How close?** Starting from the NCSS routine locations ({mn.local_h_median_m:.0f} / {mn.local_v_median_m:.0f} m "
    f"locally), {m1.frac_events_closer_than_NCSS_rel3d:.0%} of the events end closer to LDEO's structure and "
    f"{m1.frac_events_closer_than_NCSS_local:.0%} closer to their LDEO neighbors (Figure 3). The remaining differences are "
    f"larger than LDEO's own errors (median {LDEO_EH:.0f} m), so they reflect different velocity models, data and "
    f"weighting, not noise in LDEO.",
    f"- **The fault.** Every catalog shows the same near-vertical plane striking about {bearing(SEC_STRIKE)}; with "
    f"cross-correlation the swarm is nearly as thin as in LDEO (median distance from the plane {p1p.median_abs_dist_m:.0f} m "
    f"against {pL.median_abs_dist_m:.0f} m; NCSS {pN.median_abs_dist_m:.0f} m) (Figures 1, 4).",
    f"- **Which settings?** Cross-correlation is what fixes the local structure: catalog times alone (P0) leave "
    f"{m0.local_h_median_m:.0f} / {m0.local_v_median_m:.0f} m locally, more than LDEO's typical neighbor spacing ({NB:.0f} m). "
    f"rtDD's default solver gives the best vertical shape; switching off the absolute equations (P1a0) gives the best "
    f"horizontal shape ({met('P1a0').rel_h_median_m:.0f} m) but stretches the swarm vertically ({met('P1a0').rel_v_median_m:.0f} m); "
    f"nearest-neighbor pairs (P1n) help locally ({met('P1n').local_h_median_m:.0f} / {met('P1n').local_v_median_m:.0f} m) and "
    f"hurt vertically ({met('P1n').rel_v_median_m:.0f} m) (Figure 8). Use the defaults with cross-correlation.",
    f"- **Which program?** Either: scrtdd and pyrtdd agree to a median of {rvr('P0', 'S0').abs3d_median_m:.2f} m (catalog "
    f"only) and {rvr('P1', 'S1').abs3d_median_m:.1f} m (with cross-correlation), with {C['lag_identical_pct']:.1f}% of the "
    f"lags identical (Figure 5). pyrtdd needs the project's filtering proxy for its band-pass to reach the waveforms "
    f"(note 11, section 2).",
    f"- **Watch out (1): absolute position.** With the default solver the swarm sits {-m1.centroid_shift_U_m / 1000:.1f} km "
    f"deeper than LDEO (CON model without station corrections); without absolute equations it drifts "
    f"{min(UP_FROM_START.values()):.1f}-{max(UP_FROM_START.values()):.1f} km up from its start. Only the relative "
    f"geometry of these runs is meaningful (Figure 7).",
    f"- **Watch out (2): negative correlations.** rtDD accepts |CC| ≥ {CC_MIN:g}, so {XCOUNT['P']['neg']:,} mirror-image P "
    f"matches with long lags (median {LAG_NEG.median():.0f} ms) enter the system; turning them back into catalog times "
    f"(P1pos, not an rtDD option) improves the vertical shape from {m1.rel_v_median_m:.0f} to "
    f"{met('P1pos').rel_v_median_m:.0f} m and changes the rest by a few meters (Figure 6).",
    f"- **Watch out (3): sparse events.** The {len(DROPPED)} events with fewer than {SET['P0']['min_phases']} picks are never "
    f"relocated, and an event with {NPICK.loc[OUTLIER_ID, 'all']} picks ({OUTLIER_ID}) has two equally good positions "
    f"{rvr('P1', 'S1').abs3d_max_m / 1000:.1f} km apart, chosen by a single S lag (Figure 5). Treat poorly picked events "
    f"in any rtDD catalog with caution.",
]
display(Markdown("**Take-home messages**\n\n" + "\n".join(lines)))
""")

code(r"""
# 10. caveats, written from the numbers above
M4C = ["rel_h_median_m", "rel_v_median_m", "local_h_median_m", "local_v_median_m"]
NCV = [float(met(r, "NCEDC")[c]) for r in PY_RUNS + SC_RUNS for c in M4C]
LNV = [float(met("REF_LDEO", "NCEDC")[c]) for c in M4C]
cav = [
    f"- **Different velocity models and datums.** rtDD used one CON gradient model without station corrections; LDEO "
    f"used the NCSN 1-D models; NCEDC DD depths are below a local model datum and were moved to sea level with each "
    f"event's NCSS datum (an approximation). Absolute positions cannot agree to better than a few hundred meters, "
    f"and the default solver turns the model bias into a {-met('P1').centroid_shift_U_m / 1000:.1f}-km depth shift (Figure 7).",
    f"- **LDEO has its own errors.** Its stated 95% errors (median {LDEO_EH:.0f} m horizontal, {LDEO_EZ:.0f} m vertical) "
    f"measure only its precision; the two published DD catalogs differ from each other by {mr.rel_h_median_m:.0f} / "
    f"{mr.rel_v_median_m:.0f} m (relative) and {mr.local_h_median_m:.0f} / {mr.local_v_median_m:.0f} m (local), far more "
    f"than their stated errors. LDEO is a yardstick, not the truth.",
    "- **NCEDC DD is a weak secondary reference.** Its 2015 positions are automatic real-time DD-RT solutions; against "
    f"it, the four medians of every rtDD run lie between {min(NCV):.0f} and {max(NCV):.0f} m, about where LDEO itself "
    f"sits ({min(LNV):.0f}-{max(LNV):.0f} m), so it cannot tell the runs apart (metrics_vs_reference.csv).",
    "- **The picks are NCSS analyst picks**, mostly of weight 1-2, and LDEO used the same network's P picks: the catalog "
    "data are not independent of the reference. rtDD used all picks with equal weight (its default).",
    f"- **The metrics are statistics over {len(COMMON)} events.** Centroids and planes include the {len(SE_IDS)} events of "
    f"the small south-east cluster and the poorly located events; medians are shown next to RMS values for that reason. "
    f"The local metric uses LDEO's {K_NEIGH} nearest neighbors.",
    "- **pyrtdd P1 uses the project's proxy workaround** for pyrtdd's filter bug; its near-identity with scrtdd S1 "
    "(Figure 5) shows that the workaround reproduces what scrtdd does natively. P1pos is a diagnostic, not an rtDD option.",
    "- **Nothing was tuned towards the references**; every run made is shown (note 11, sections 1 and 10).",
]
display(Markdown("**Caveats**\n\n" + "\n".join(cav)))
bad = CHK[~CHK.Consistent]
bad11 = N11[N11.Consistent != "yes"]
txt = [f"- Cross-file checks (section 1.3): {int(CHK.Consistent.sum())} of {len(CHK)} consistent."]
for _, r in bad.iterrows():
    extra = ""
    if "libhdd's own log" in r.Check:
        extra = (f" The cache holds {N_AT_THRESHOLD} correlation written as exactly {CC_MIN:g} (six decimals), which the "
                 f"cache count includes and libhdd's log apparently did not.")
    txt.append(f"  - {r.Check}: {r['Value A']:g} against {r['Value B']:g}.{extra}")
txt.append(f"- Note 11 against the files (section 1.4): {int((N11.Consistent == 'yes').sum())} of {len(N11)} numbers agree; "
           f"the others:")
for _, r in bad11.iterrows():
    txt.append(f"  - {r.Quantity}: note {r['Note 11']}, files {r.Files}" + (f" ({r.Comment})." if r.Comment else "."))
txt.append(f"- Not a contradiction, but not in note 11: event {OUTLIER_ID} is {C['out_h']:.1f} km from its P1 position "
           f"horizontally, toward {bearing(float(np.degrees(np.arctan2(dEN.E, dEN.N))))} (note: 'to the south'); one P "
           f"correlation flips sign between the programs ({CCX.coefficient_py:+.3f} against {CCX.coefficient_sc:+.3f}).")
display(Markdown("**Inconsistencies found**\n\n" + "\n".join(txt)))
print("figures written:")
for k_, (png, pdf) in FIGS.items():
    print(f"  Figure {k_}: {png}  |  {pdf}")
""")

md(r"""
### How to reproduce

```bash
cd /home/msseo/works/74.SeisComP_rtDD_DLpicker/notebooks
source /home/msseo/miniforge3/etc/profile.d/conda.sh && conda activate pyrtdd
python build_06_sanramon_relocation.py      # writes 06_sanramon_relocation.ipynb (and compiles every code cell)
rm -f figures/06_*.png figures/06_*.pdf     # remove old figures
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=pyrtdd \
    --ExecutePreprocessor.timeout=1800 06_sanramon_relocation.ipynb
```

- Inputs (read only): the reference tables in `data/sanramon_2015/reference_tables/`, the rtDD input catalog in
  `data/sanramon_2015/inputs/rtdd_catalog/`, the run folders `runs/sanramon/pyrtdd/<run>/` and
  `runs/sanramon/scrtdd/<run>/`, and the comparison tables in `runs/sanramon/analysis/` (written by
  `analyze_sanramon.py`, which this notebook imports as a module).
- The relocations themselves are reproduced with the scripts listed in note 11
  (`runs/sanramon/pyrtdd/run_pyrtdd_sanramon.py`, `runs/sanramon/scrtdd/scrtdd_sanramon.py`; then
  `python -I runs/sanramon/analysis/analyze_sanramon.py` in env `pyrtdd`).
- Outputs: figures `notebooks/figures/06_*.png` and `.pdf`; nothing else is written.
- Helper code: `notebooks/lib/nb06_helpers.py`; fonts: `notebooks/lib/nbfont.py`.
""")

code(r"""
# run time of this execution
print(f"run time {(_time.time() - T_START):.1f} s")
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
