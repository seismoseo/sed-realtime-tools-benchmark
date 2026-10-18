# nb07_helpers.py -- helpers for notebooks/07_sanramon_dlpicker.ipynb (written by build_07_sanramon_dlpicker.py).
#
# The notebook only LOADS the result files of step 12 (runs/sanramon/dlpicker/) and plots them; nothing here picks,
# relocates or changes a result file. The step 12 analysis scripts (runs/sanramon/dlpicker/scripts/12_*.py) are
# imported as modules with import_script(); their main() runs only under __main__, so importing them runs nothing.
#
# bandpass(), component(), legend_above(), text_above(), text_below(), save_fig(), legend_box(), panel_letter(),
# ecdf() and mad() are verbatim copies from notebooks/lib/nb03_helpers.py (notebook 03), so that both notebooks
# filter and lay out figures the same way without importing each other's module.
import importlib.util
import os
import re

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


# ------------------------------------------------------------------------------------------------
# verbatim copies from notebooks/lib/nb03_helpers.py
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


def ecdf(x):
    x = np.sort(np.asarray(x, float))
    return x, np.arange(1, len(x) + 1) / len(x)


def mad(x):
    x = np.asarray(x, float)
    return float(np.median(np.abs(x - np.median(x))))


# ------------------------------------------------------------------------------------------------
# new helpers for notebook 07
# ------------------------------------------------------------------------------------------------
def import_script(path, name):
    # imports one of the step 12 analysis scripts as a module; its main() only runs under __main__
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def boxed(axes):
    # all four frame lines on every panel, same color and width
    for ax in np.atleast_1d(axes).ravel():
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_color("k")
            s.set_linewidth(0.8)


def ts_utc(s):
    # POSIX seconds of time strings such as '2015-10-19 23:21:13.890000+00:00' (independent of pandas' datetime unit)
    t = pd.to_datetime(pd.Series(s), utc=True, format="mixed")
    return ((t - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()).to_numpy()


MAG_SUB = {"D": "d", "W": "w", "L": "L"}


def mag_label(mag, mag_type, nd=2):
    # magnitude written as an italic M with an upright subscript (the NCSS magnitude type), e.g. M_w 3.60
    sub = MAG_SUB.get(str(mag_type), str(mag_type))
    return rf"$\mathit{{M}}_{{\mathrm{{{sub}}}}}$ {mag:.{nd}f}"


def bool_cols(df, cols):
    # 'True'/'False' text (or 1/0) -> bool for the listed columns that exist
    for c in cols:
        if c in df.columns:
            df[c] = df[c].map(lambda x: str(x).strip().lower() in ("true", "1", "1.0"))
    return df


def note_numbers(text, pattern, flags=re.S):
    # every captured group of the first match of 'pattern' in the note, as floats (the note writes minus as U+2212)
    m = re.search(pattern, text, flags)
    if not m:
        return None
    return [float(g.replace("−", "-").replace(",", "")) for g in m.groups()]


def frac_text(k, n, nd=2):
    return f"{int(k)}/{int(n)} = {k / n:.{nd}f}" if n else "n/a"


def model_handles(variants, col, mark, label, open_marker=True, ms=6):
    # legend handles: the model's marker in the model's color (open, as in notebook 03)
    hs = [Line2D([], [], ls="none", marker=mark[v], color=col[v], mec=col[v],
                 mfc="white" if open_marker else col[v], ms=ms, mew=1.1) for v in variants]
    return hs, [label[v] for v in variants]


def patch(fc, hatch=None, ec="0.25", lw=0.5):
    return Patch(facecolor=fc, edgecolor=ec, hatch=hatch, lw=lw)


def norm_window(t, y, t0, t1):
    # samples of one trace between t0 and t1, scaled to the largest absolute value in that window
    m = (t >= t0) & (t <= t1)
    yy = np.asarray(y, float)[m]
    s = np.abs(yy).max() if len(yy) else 1.0
    return t[m], yy / (s if s > 0 else 1.0)


def text_color_on(color):
    # black or white text, whichever reads better on a filled bar of this color
    from matplotlib.colors import to_rgb
    r, g, b = to_rgb(color)
    return "k" if 0.299 * r + 0.587 * g + 0.114 * b > 0.55 else "white"


def coverage_agreement(q, thr):
    # eqtp polarity at polarityMinConfidence = thr, with the rules of 12_compare.py (ps()): coverage = pairs with a
    # DL polarity whose confidence >= thr / pairs; agreement = DL polarity equal to the analyst first motion;
    # 'swap undone' = the plugin's polarity with its gain/dip swap reversed (raw-count polarity)
    has = q[(q["dl_fm"] != "") & (q["dl_polarity_confidence"] >= thr)]
    n, k = len(q), len(has)
    return dict(n=n, n_with_polarity=k, coverage=k / n if n else np.nan,
                n_agree=int((has["dl_fm"] == has["analyst_fm"]).sum()),
                agreement=float((has["dl_fm"] == has["analyst_fm"]).mean()) if k else np.nan,
                agreement_swap_undone=float((has["dl_fm_raw_counts"] == has["analyst_fm"]).mean()) if k else np.nan)


def legend_above_kw(fig, axes, handles, labels, ncol, pad=0.008, fontsize=None, **kw):
    # legend_above() with extra keywords for fig.legend (e.g. handler_map for tuple handles)
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bbs = [ax.get_tightbbox(r) for ax in np.atleast_1d(axes).ravel()]
    bb = Bbox.union(bbs).transformed(fig.transFigure.inverted())
    leg = fig.legend(handles, labels, loc="lower center", bbox_to_anchor=((bb.x0 + bb.x1) / 2.0, bb.y1 + pad),
                     ncol=ncol, frameon=True, framealpha=1.0, facecolor="white", edgecolor="0.6", fontsize=fontsize, **kw)
    leg.set_zorder(100)
    return leg


def spread_labels(values, min_gap):
    # y positions for value labels at one x: labels closer than min_gap are merged into blocks, and each block is centred on
    # the mean of its values with min_gap between neighbours (input order kept)
    values = np.asarray(values, float)
    order = np.argsort(values)
    v = values[order]
    blocks = [[i] for i in range(len(v))]

    def pos(b):
        c = float(np.mean(v[b]))
        return [c + (k - (len(b) - 1) / 2.0) * min_gap for k in range(len(b))]
    changed = True
    while changed:
        changed = False
        for j in range(len(blocks) - 1):
            if pos(blocks[j])[-1] + min_gap > pos(blocks[j + 1])[0] + 1e-12:
                blocks[j] = blocks[j] + blocks[j + 1]
                del blocks[j + 1]
                changed = True
                break
    out = np.empty(len(v))
    for b in blocks:
        for i, p_ in zip(b, pos(b)):
            out[order[i]] = p_
    return out


def clusters(ts, gap):
    # groups of consecutive (sorted) times closer than 'gap'; returns lists of indices into ts
    idx = np.argsort(ts)
    out, cur = [], []
    for i in idx:
        if cur and ts[i] - ts[cur[-1]] >= gap:
            out.append(cur)
            cur = []
        cur.append(i)
    if cur:
        out.append(cur)
    return out
