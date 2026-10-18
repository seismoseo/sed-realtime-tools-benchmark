# nb06_helpers.py -- small helpers for notebooks/06_sanramon_relocation.ipynb
#
# Layout helpers (legend/title/note placed from the tight bounding boxes of the axes, figure saving) are copied from
# notebooks/lib/nb02_helpers.py so that notebook 06 does not depend on notebook 02's module. The computations only
# re-derive numbers from the result files of runs/sanramon/ (no relocation). The analysis script
# runs/sanramon/analysis/analyze_sanramon.py is imported as a module (its main() is not run).
import importlib.util
import json
import os

import numpy as np
import pandas as pd
from matplotlib.transforms import Bbox


# ------------------------------------------------------------------------------------------------
# figure layout (copied from nb02_helpers.py)
# ------------------------------------------------------------------------------------------------
def _union_bbox(fig, artists):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    return Bbox.union([a.get_tightbbox(r) for a in artists]).transformed(fig.transFigure.inverted())


def legend_above(fig, axes, handles, labels, ncol, pad=0.008, fontsize=None, x="center", **kw):
    # opaque legend placed above the union of the tight bounding boxes of 'axes' (figure coordinates)
    bb = _union_bbox(fig, list(np.atleast_1d(axes).ravel()))
    if x == "left":
        loc, xa = "lower left", bb.x0
    else:
        loc, xa = "lower center", (bb.x0 + bb.x1) / 2.0
    leg = fig.legend(handles, labels, loc=loc, bbox_to_anchor=(xa, bb.y1 + pad), ncol=ncol, frameon=True,
                     framealpha=1.0, facecolor="white", edgecolor="0.6", fontsize=fontsize, **kw)
    leg.set_zorder(100)
    return leg


def text_above(fig, artists, text, pad=0.006, **kw):
    # one line of text (the figure's message) placed above the union of the artists' tight bounding boxes
    bb = _union_bbox(fig, artists)
    return fig.text(bb.x0, bb.y1 + pad, text, ha="left", va="bottom", **kw)


def text_below(fig, artists, text, pad=0.004, **kw):
    # a note placed below the union of the artists' tight bounding boxes (left-aligned)
    bb = _union_bbox(fig, artists)
    return fig.text(bb.x0, bb.y0 - pad, text, ha="left", va="top", **kw)


def save_fig(fig, fig_dir, name, dpi=200):
    png = os.path.join(fig_dir, name + ".png")
    pdf = os.path.join(fig_dir, name + ".pdf")
    fig.savefig(png, dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    return png, pdf


def boxed(ax):
    # all four frame lines on, in the same color and width
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_color("k")
        s.set_linewidth(0.8)


# ------------------------------------------------------------------------------------------------
# loading
# ------------------------------------------------------------------------------------------------
def import_analysis(path):
    # imports runs/sanramon/analysis/analyze_sanramon.py as a module; its main() only runs under __main__.
    # No bytecode is written, so that the run folder stays untouched.
    import sys
    spec = importlib.util.spec_from_file_location("analyze_sanramon", path)
    mod = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = old
    return mod


def read_json(path):
    with open(path) as f:
        return json.load(f)


def read_rtdd_csv(path, usecols=None):
    # libhdd csv files: keep empty location codes as '' and turn 'true'/'false' text into booleans
    d = pd.read_csv(path, dtype={"locationCode": str}, keep_default_na=False, usecols=usecols)
    for c in d.columns:
        if d[c].dtype == object and set(d[c].astype(str).str.lower().unique()) <= {"true", "false"}:
            d[c] = d[c].astype(str).str.lower() == "true"
    return d


# ------------------------------------------------------------------------------------------------
# geometry
# ------------------------------------------------------------------------------------------------
def rotate(E, N, strike_deg):
    # map coordinates -> (along strike, across strike); 'across' points to strike + 90 deg (right-hand rule)
    s = np.radians(strike_deg)
    E = np.asarray(E, float)
    N = np.asarray(N, float)
    return E * np.sin(s) + N * np.cos(s), E * np.cos(s) - N * np.sin(s)


def plane_svd(xyz):
    # the same plane as analyze_sanramon.plane_fit (SVD of the centred coordinates, upward normal), but returning the
    # unit normal (E, N, U) and every event's signed distance from the plane (m)
    xyz = np.asarray(xyz, float)
    c = xyz - xyz.mean(axis=0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    n = vt[2].copy()
    if n[2] < 0:
        n = -n
    return n, c @ n


def normal_from_strike_dip(strike_deg, dip_deg):
    # upward unit normal (E, N, U) of a plane given by strike (right-hand rule) and dip; its horizontal part points
    # down dip (the convention of analyze_sanramon.plane_fit)
    dd = np.radians(strike_deg + 90.0)
    dp = np.radians(dip_deg)
    return np.array([np.sin(dp) * np.sin(dd), np.sin(dp) * np.cos(dd), np.cos(dp)])


def plane_trace_in_section(normal, section_strike_deg, up):
    # where the plane through the centroid crosses the vertical section through the centroid (along-strike
    # coordinate 0) of a section looking along 'section_strike_deg': across-strike coordinate for each 'up' value
    n_al, n_ac = rotate(normal[0], normal[1], section_strike_deg)
    return -normal[2] * np.asarray(up, float) / float(n_ac)


def aligned_strike_dip(strike_deg, dip_deg, ref_strike_deg):
    # expresses a plane with the strike closest to ref_strike_deg: a plane dipping the other way is written with
    # strike + 180 and dip 180 - dip (dip > 90 deg = overturned past vertical, i.e. leaning the other way)
    d = (strike_deg - ref_strike_deg + 180.0) % 360.0 - 180.0
    if abs(d) > 90.0:
        return (strike_deg + 180.0) % 360.0, 180.0 - dip_deg
    return strike_deg % 360.0, dip_deg


# ------------------------------------------------------------------------------------------------
# statistics
# ------------------------------------------------------------------------------------------------
def ecdf(x):
    # sorted values and the share of values at or below each one
    x = np.sort(np.asarray(x, float))
    x = x[np.isfinite(x)]
    return x, np.arange(1, len(x) + 1) / len(x)


def mad(x):
    # median absolute deviation from the median (as residual_stats.csv)
    x = np.asarray(x, float)
    return float(np.median(np.abs(x - np.median(x))))


def check_row(what, a, b, tol):
    # one line of a consistency table
    a = float(a)
    b = float(b)
    return {"Check": what, "Value A": a, "Value B": b, "|A - B|": abs(a - b), "Tolerance": tol,
            "Consistent": bool(abs(a - b) <= tol)}


def md_table(df, index=False):
    # pandas -> markdown table
    d = df.reset_index() if index else df
    lines = ["| " + " | ".join(str(c) for c in d.columns) + " |", "|" + "---|" * len(d.columns)]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def text_color_on(color):
    # black or white text, whichever reads better on a filled bar of this color
    from matplotlib.colors import to_rgb
    r, g, b = to_rgb(color)
    return "k" if 0.299 * r + 0.587 * g + 0.114 * b > 0.55 else "white"
