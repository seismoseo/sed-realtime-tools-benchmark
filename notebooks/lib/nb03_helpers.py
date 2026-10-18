# nb03_helpers.py -- helpers for notebooks/03_gwangyang_dlpicker.ipynb (written by build_03_gwangyang_dlpicker.py).
#
# The notebook only LOADS the result files of step 09 (runs/gwangyang/dlpicker/) and plots them; nothing here
# picks, relocates or changes a result file.
#
# bandpass(), component(), legend_above(), text_above(), text_below() and save_fig() are verbatim copies from
# notebooks/lib/sp_offset.py (notebook 05), so both notebooks filter and lay out figures the same way.
import os

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


# ------------------------------------------------------------------------------------------------
# verbatim copies from notebooks/lib/sp_offset.py
# ------------------------------------------------------------------------------------------------
def bandpass(st, fmin, fmax, corners, taper_frac, zerophase):
    # zerophase=False (one pass, causal) never moves energy ahead of the true onset; a zero-phase filter
    # can show ringing before an arrival and so make it look earlier than it is
    st = st.copy()
    st.detrend("demean")
    st.detrend("linear")
    st.taper(taper_frac)
    st.filter("bandpass", freqmin=fmin, freqmax=fmax, corners=corners, zerophase=zerophase)
    return st


def component(st, comp):
    q = [tr for tr in st if tr.stats.channel[-1] == comp]
    return q[0] if q else None


def legend_above(fig, axes, handles, labels, ncol, pad=0.008, fontsize=None):
    # opaque legend placed above the union of the tight bounding boxes of 'axes' (figure coordinates)
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bbs = [ax.get_tightbbox(r) for ax in np.atleast_1d(axes).ravel()]
    bb = Bbox.union(bbs).transformed(fig.transFigure.inverted())
    leg = fig.legend(handles, labels, loc="lower center", bbox_to_anchor=((bb.x0 + bb.x1) / 2.0, bb.y1 + pad),
                     ncol=ncol, frameon=True, framealpha=1.0, facecolor="white", edgecolor="0.6", fontsize=fontsize)
    leg.set_zorder(100)
    return leg


def text_above(fig, artists, text, pad=0.006, **kw):
    # one line of text (e.g. a figure title) placed above the union of the artists' tight bounding boxes
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bb = Bbox.union([a.get_tightbbox(r) for a in artists]).transformed(fig.transFigure.inverted())
    return fig.text(bb.x0, bb.y1 + pad, text, ha="left", va="bottom", **kw)


def text_below(fig, artists, text, pad=0.004, **kw):
    # a note placed below the union of the artists' tight bounding boxes (left-aligned)
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bb = Bbox.union([a.get_tightbbox(r) for a in artists]).transformed(fig.transFigure.inverted())
    return fig.text(bb.x0, bb.y0 - pad, text, ha="left", va="top", **kw)


def save_fig(fig, fig_dir, name, dpi=200):
    png = os.path.join(fig_dir, name + ".png")
    pdf = os.path.join(fig_dir, name + ".pdf")
    fig.savefig(png, dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    return png, pdf


# ------------------------------------------------------------------------------------------------
# new helpers for notebook 03
# ------------------------------------------------------------------------------------------------
def legend_box(ax, handles, labels, loc="upper left", ncol=1, fontsize=7.0, **kw):
    # opaque legend inside one panel (white, frame 0.6), drawn above the data
    leg = ax.legend(handles, labels, loc=loc, ncol=ncol, fontsize=fontsize, frameon=True, framealpha=1.0,
                    facecolor="white", edgecolor="0.6", **kw)
    leg.set_zorder(100)
    return leg


def panel_letter(ax, letter, **kw):
    # '(a)' put in front of the panel's left title (call after set_title(..., loc="left")), so that it can never
    # collide with a neighboring panel; the title keeps its font size
    t = ax._left_title
    s = t.get_text()
    t.set_text(f"({letter}) {s}" if s else f"({letter})")


def whole_samples(dt_s, fs):
    # a time difference in whole samples, n = round(dt * fs) (as in step 09's scripts)
    return np.rint(np.asarray(dt_s, float) * fs).astype(int)


def frac_within(n, k):
    n = np.abs(np.asarray(n))
    return float(np.mean(n <= k)) if len(n) else np.nan


def ecdf(x):
    x = np.sort(np.asarray(x, float))
    return x, np.arange(1, len(x) + 1) / len(x)


def mad(x):
    x = np.asarray(x, float)
    return float(np.median(np.abs(x - np.median(x))))


def model_handles(variants, col, mark, label, open_marker=True, ms=6):
    # legend handles: the model's marker in the model's color (open, as in notebook 05)
    hs = [Line2D([], [], ls="none", marker=mark[v], color=col[v], mec=col[v],
                 mfc="white" if open_marker else col[v], ms=ms, mew=1.1) for v in variants]
    return hs, [label[v] for v in variants]


def patch(fc, hatch=None, ec="0.25", lw=0.5):
    return Patch(facecolor=fc, edgecolor=ec, hatch=hatch, lw=lw)


def ytick_markers(ax, ys, variants, col, mark, x=-0.012, ms=5.5):
    # the model's marker just left of the axis at each y tick (axes-fraction x, data y)
    tr = ax.get_yaxis_transform()
    for y, v in zip(ys, variants):
        ax.plot([x], [y], ls="none", marker=mark[v], color=col[v], mec=col[v], mfc="white", ms=ms, mew=1.0,
                transform=tr, clip_on=False, zorder=5)


def norm_window(t, y, t0, t1):
    # samples of one trace between t0 and t1, scaled to the largest absolute value in that window
    m = (t >= t0) & (t <= t1)
    yy = np.asarray(y, float)[m]
    s = np.abs(yy).max() if len(yy) else 1.0
    return t[m], yy / (s if s > 0 else 1.0)


def enu_rms(a, b):
    # metric (a) of step 09: both solutions' own centroids removed, RMS over events of the 3-D difference
    # (and of each component); a, b = arrays (events x 3: east, north, up), same event order
    a = np.asarray(a, float) - np.mean(a, axis=0)
    b = np.asarray(b, float) - np.mean(b, axis=0)
    d = a - b
    return float(np.sqrt(np.mean(np.sum(d ** 2, axis=1)))), np.sqrt(np.mean(d ** 2, axis=0))
