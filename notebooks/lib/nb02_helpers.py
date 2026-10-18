# nb02_helpers.py -- small helpers for notebooks/02_gwangyang_relocation.ipynb
#
# Layout helpers (legend/title/note placed from the tight bounding boxes of the axes, figure saving) follow the
# conventions of notebooks/lib/sp_offset.py (notebook 05); they are copied here so that notebook 02 does not depend
# on notebook 05's module. The computations only re-derive numbers from the result tables (no relocation).
import json
import os

import numpy as np
import pandas as pd
from matplotlib.transforms import Bbox


# ------------------------------------------------------------------------------------------------
# figure layout
# ------------------------------------------------------------------------------------------------
def _union_bbox(fig, artists):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    return Bbox.union([a.get_tightbbox(r) for a in artists]).transformed(fig.transFigure.inverted())


def legend_above(fig, axes, handles, labels, ncol, pad=0.008, fontsize=None, x="center"):
    # opaque legend placed above the union of the tight bounding boxes of 'axes' (figure coordinates)
    bb = _union_bbox(fig, list(np.atleast_1d(axes).ravel()))
    if x == "left":
        loc, xa = "lower left", bb.x0
    else:
        loc, xa = "lower center", (bb.x0 + bb.x1) / 2.0
    leg = fig.legend(handles, labels, loc=loc, bbox_to_anchor=(xa, bb.y1 + pad), ncol=ncol, frameon=True,
                     framealpha=1.0, facecolor="white", edgecolor="0.6", fontsize=fontsize)
    leg.set_zorder(100)
    return leg


def legend_in_axes(ax, handles, labels, loc="upper left", ncol=1, fontsize=None, title=None):
    # opaque legend inside an otherwise empty axes (the axes frame itself is hidden; it carries no data)
    leg = ax.legend(handles, labels, loc=loc, ncol=ncol, frameon=True, framealpha=1.0, facecolor="white",
                    edgecolor="0.6", fontsize=fontsize, title=title, borderaxespad=0.0)
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


def place_labels(ax, xs, ys, texts, avoid_xy=None, avoid_segments=None, radii_pts=(6.5, 11.0, 16.0), fontsize=7.5,
                 marker_px=5.0, leader_color="0.35", **kw):
    # Places one text label next to each point (xs[i], ys[i]). Eight directions at each radius in radii_pts are tried;
    # the candidate that overlaps least with labels already placed, with the points (xs, ys and avoid_xy), with the
    # line segments in avoid_segments (rows x0, y0, x1, y1 in data units; e.g. error bars) and with the axes edge is
    # kept. Labels moved beyond the first radius get a thin leader line. Returns the list of Annotation objects.
    fig = ax.figure
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    pts = np.c_[np.asarray(xs, float), np.asarray(ys, float)]
    pts_all = np.r_[pts, np.asarray(avoid_xy, float)] if avoid_xy is not None and len(avoid_xy) else pts
    disp = ax.transData.transform(pts_all)
    disp_lab = ax.transData.transform(pts)
    seg_pts = np.zeros((0, 2))
    if avoid_segments is not None and len(avoid_segments):
        sg = np.asarray(avoid_segments, float)
        t = np.linspace(0.0, 1.0, 15)[:, None]
        dense = [np.c_[x0 + t[:, 0] * (x1 - x0), y0 + t[:, 0] * (y1 - y0)] for x0, y0, x1, y1 in sg]
        seg_pts = ax.transData.transform(np.vstack(dense))
    axbb = ax.get_window_extent(rend)
    dirs = [(1, 1), (-1, 1), (1, -1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]
    placed, out = [], []
    for (x, y), t_ in zip(pts, texts):
        best = None
        for ir, rad in enumerate(radii_pts):
            for k, (dx, dy) in enumerate(dirs):
                nrm = np.hypot(dx, dy)
                ox, oy = dx / nrm * rad, dy / nrm * rad
                ha = "left" if dx > 0 else ("right" if dx < 0 else "center")
                va = "bottom" if dy > 0 else ("top" if dy < 0 else "center")
                a = ax.annotate(t_, (x, y), xytext=(ox, oy), textcoords="offset points", ha=ha, va=va,
                                fontsize=fontsize, **kw)
                bb = a.get_window_extent(rend)
                a.remove()
                score = 0.0
                for pb in placed:
                    w = min(bb.x1, pb.x1) - max(bb.x0, pb.x0) + 2.0
                    h = min(bb.y1, pb.y1) - max(bb.y0, pb.y0) + 2.0
                    if w > 0 and h > 0:
                        score += 10.0 * w * h
                inside = ((disp[:, 0] > bb.x0 - marker_px) & (disp[:, 0] < bb.x1 + marker_px) &
                          (disp[:, 1] > bb.y0 - marker_px) & (disp[:, 1] < bb.y1 + marker_px))
                score += 400.0 * float(inside.sum())
                # ambiguity: the label's center must be closer to its own point than to any other labeled point
                cx_, cy_ = 0.5 * (bb.x0 + bb.x1), 0.5 * (bb.y0 + bb.y1)
                own_d = np.hypot(*(np.array([cx_, cy_]) - ax.transData.transform((x, y))))
                d_all = np.hypot(disp_lab[:, 0] - cx_, disp_lab[:, 1] - cy_)
                if np.any(d_all < own_d - 0.5):
                    score += 300.0
                if len(seg_pts):
                    on = ((seg_pts[:, 0] > bb.x0 - 1) & (seg_pts[:, 0] < bb.x1 + 1) &
                          (seg_pts[:, 1] > bb.y0 - 1) & (seg_pts[:, 1] < bb.y1 + 1))
                    score += 40.0 * float(on.sum())
                if bb.x0 < axbb.x0 or bb.x1 > axbb.x1 or bb.y0 < axbb.y0 or bb.y1 > axbb.y1:
                    score += 1e6
                score += 60.0 * ir + 0.01 * k      # prefer close labels, then the preferred direction
                if best is None or score < best[0]:
                    best = (score, ox, oy, ha, va, bb, ir)
        _, ox, oy, ha, va, bb, ir = best
        extra = {}
        if ir > 0:
            extra["arrowprops"] = dict(arrowstyle="-", lw=0.5, color=leader_color, shrinkA=0.0, shrinkB=3.0)
        out.append(ax.annotate(t_, (x, y), xytext=(ox, oy), textcoords="offset points", ha=ha, va=va,
                               fontsize=fontsize, **extra, **kw))
        placed.append(bb)
    return out


def text_color_on(color):
    # black or white text, whichever reads better on a filled bar of this color
    from matplotlib.colors import to_rgb
    r, g, b = to_rgb(color)
    return "k" if 0.299 * r + 0.587 * g + 0.114 * b > 0.55 else "white"


# ------------------------------------------------------------------------------------------------
# small computations on the result tables
# ------------------------------------------------------------------------------------------------
def short(run):
    # 'R1f_xcorr_like_reference_hypodd_like_filtered' -> 'R1f'; 'S1' -> 'S1'
    return str(run).split("_")[0]


def rel_centroid(df, cols=("E", "N", "U")):
    # positions relative to the solution's own 11-event centroid
    d = df[list(cols)].astype(float)
    return d - d.mean()


def interevent(X):
    # the 55 event-to-event 3-D distances of an (11, 3) array, upper triangle in row order
    X = np.asarray(X, float)
    iu = np.triu_indices(len(X), 1)
    return np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)[iu]


def shape_metrics(X, Y):
    # metric (a) of notes 07/08: positions relative to each solution's own centroid, X minus Y;
    # RMS and largest of the horizontal distance and of the vertical difference over the events
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    d = (X - X.mean(0)) - (Y - Y.mean(0))
    h = np.hypot(d[:, 0], d[:, 1])
    v = np.abs(d[:, 2])
    return dict(rms_h=float(np.sqrt(np.mean(h ** 2))), max_h=float(h.max()),
                rms_v=float(np.sqrt(np.mean(v ** 2))), max_v=float(v.max()))


def flatten(d, prefix=""):
    # nested dict -> {'A.B.C': value}
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v
    return out


def read_json(path):
    with open(path) as f:
        return json.load(f)


def normalize_pairs(df, id1="id1", id2="id2", flip_cols=()):
    # puts every event pair in id1 < id2 order; differential-time columns change sign when a pair is flipped
    d = df.copy()
    f = d[id1] > d[id2]
    d.loc[f, [id1, id2]] = d.loc[f, [id2, id1]].values
    for c in flip_cols:
        d.loc[f, c] = -d.loc[f, c]
    return d


def grid_fractions(diff_ms, limits=(2, 5)):
    # fraction of differences within each limit, counted on the 1-ms grid (as notes 07/08 after the verification)
    g = np.round(np.asarray(diff_ms, float))
    return {lim: float(np.mean(np.abs(g) <= lim)) for lim in limits}


def check_row(what, a, b, tol):
    # one line of the cross-file consistency table
    a = float(a)
    b = float(b)
    return {"Check": what, "Value A": a, "Value B": b, "|A - B|": abs(a - b), "Tolerance": tol,
            "Consistent": bool(abs(a - b) <= tol)}


def fmt_frame(df, digits=2):
    # rounds the float columns of a table for display
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].round(digits)
    return out
