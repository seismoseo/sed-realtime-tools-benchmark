# nb08_helpers.py -- small helpers for notebooks/08_sanramon2026_relocation.ipynb (written by
# build_08_sanramon2026_relocation.py).
#
# The notebook only LOADS the result files of step 13 (runs/sanramon2026/, the 2025-26 San Ramon sequence) and of
# step 11 (runs/sanramon/, the 2015 swarm) and plots them; nothing here relocates or changes a result file.
#
# Everything in the first two blocks (layout, loading) and ecdf(), rotate() and md_table() are verbatim copies from
# notebooks/lib/nb06_helpers.py (notebook 06, the 2015 San Ramon relocation), so that both notebooks lay out and
# load figures the same way without importing each other's module. Only the last block is new.
import importlib.util
import json
import os

import numpy as np
import pandas as pd
from matplotlib.transforms import Bbox


# ------------------------------------------------------------------------------------------------
# figure layout (verbatim from nb06_helpers.py)
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
# loading (verbatim from nb06_helpers.py)
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


# ------------------------------------------------------------------------------------------------
# geometry and statistics (verbatim from nb06_helpers.py)
# ------------------------------------------------------------------------------------------------
def rotate(E, N, strike_deg):
    # map coordinates -> (along strike, across strike); 'across' points to strike + 90 deg (right-hand rule)
    s = np.radians(strike_deg)
    E = np.asarray(E, float)
    N = np.asarray(N, float)
    return E * np.sin(s) + N * np.cos(s), E * np.cos(s) - N * np.sin(s)


def ecdf(x):
    # sorted values and the share of values at or below each one
    x = np.sort(np.asarray(x, float))
    x = x[np.isfinite(x)]
    return x, np.arange(1, len(x) + 1) / len(x)


def md_table(df, index=False):
    # pandas -> markdown table
    d = df.reset_index() if index else df
    lines = ["| " + " | ".join(str(c) for c in d.columns) + " |", "|" + "---|" * len(d.columns)]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------
# new for notebook 08
# ------------------------------------------------------------------------------------------------
def strike_difference(a_deg, b_deg):
    # smallest angle between two strike lines (deg, 0-90); a strike and strike + 180 are the same line
    d = (float(a_deg) - float(b_deg)) % 180.0
    return min(d, 180.0 - d)


def n_outside(x, y, xlim, ylim):
    # number of points outside a panel window (NaN coordinates count as outside)
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    inside = (x >= xlim[0]) & (x <= xlim[1]) & (y >= ylim[0]) & (y <= ylim[1])
    return int((~inside).sum())


def fmt_duration(seconds):
    # wall time as '91 s' below two minutes, otherwise '38.4 min'
    s = float(seconds)
    return f"{s:.0f} s" if s < 120.0 else f"{s / 60.0:.1f} min"


def month_ticks(t_first, t_last):
    # first day of every month between two timestamps (UTC), as timestamps
    start = pd.Timestamp(year=t_first.year, month=t_first.month, day=1, tz=t_first.tz)
    out = pd.date_range(start, t_last, freq="MS")
    return [t for t in out if t >= t_first]
