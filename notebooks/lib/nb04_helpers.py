# nb04_helpers.py -- helpers of notebook 04_gwangyang_realtime (step 10: the real-time chain on Server A).
#
# Only file, database-copy and plotting helpers live here. Positions (local east/north/up) and times are computed
# with the canonical functions of runs/gwangyang/realtime/scripts/rt_analyze.py, which the notebook loads with
# load_script(); the SQL read-back queries are rt_chain.py's own (rt_chain.SQL).
import hashlib
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile

import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


# ------------------------------------------------------------------------------------------------ files
def load_script(path, name):
    # load a driver script as a module: its top level only defines constants and functions (main() is guarded by
    # __name__ == "__main__"); no bytecode is written next to it
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = old
    return mod


def md5_file(path, block=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(block), b""):
            h.update(b)
    return h.hexdigest()


def read_db_copy(db, queries, parent):
    # Copy the SQLite database (and its -wal file when it is not empty) into a new temporary folder under 'parent',
    # open the COPY read-only (mode=ro), run the queries, then delete the folder. The original file is only read
    # by the copy; its md5 is taken before and after.
    md5_before = md5_file(db)
    tmp = tempfile.mkdtemp(prefix="nb04_dbcopy_", dir=parent)
    copied = []
    try:
        dst = os.path.join(tmp, "copy.sqlite")
        shutil.copy2(db, dst)
        copied.append(os.path.basename(db))
        wal = db + "-wal"
        if os.path.exists(wal) and os.path.getsize(wal) > 0:
            shutil.copy2(wal, dst + "-wal")
            copied.append(os.path.basename(wal))
        con = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
        try:
            tables = {k: pd.read_sql_query(q, con) for k, q in queries.items()}
            journal = con.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    md5_after = md5_file(db)
    info = dict(db=db, files_copied="+".join(copied), journal_mode=journal, md5_before=md5_before,
                md5_after=md5_after, original_unchanged=md5_before == md5_after,
                temporary_copy_removed=not os.path.exists(tmp))
    return tables, info


# ------------------------------------------------------------------------------------------------ figures
def close_box(ax, lw=0.8, color="black"):
    # all four frame lines on
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(lw)
        s.set_color(color)


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


def save_fig(fig, fig_dir, name, dpi=200):
    png = os.path.join(fig_dir, name + ".png")
    pdf = os.path.join(fig_dir, name + ".pdf")
    fig.savefig(png, dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    return png, pdf


# ------------------------------------------------------------------------------------------------ diagram
def box(ax, x, y, w, h, title, body="", fc="white", ec="0.25", lw=1.0, title_size=10, body_size=7.6,
        ls="-", radius=0.6, title_color="black", wrap=None):
    # rounded box with a title line and a body text below it (data coordinates of a 0-100 canvas)
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}", fc=fc, ec=ec, lw=lw, ls=ls,
                       zorder=2)
    ax.add_patch(p)
    ax.text(x + 0.8, y + h - 0.7, title, ha="left", va="top", fontsize=title_size, color=title_color, zorder=3)
    if body:
        ax.text(x + 0.8, y + h - 0.7 - title_size * 0.30, body, ha="left", va="top", fontsize=body_size,
                color="0.15", zorder=3, linespacing=1.25)
    return p


def arrow(ax, p0, p1, color="0.2", lw=1.3, ls="-", rad=0.0, head=9, z=4, shrink=0.0):
    a = FancyArrowPatch(p0, p1, arrowstyle=f"-|>,head_length={head / 18:.2f},head_width={head / 30:.2f}",
                        connectionstyle=f"arc3,rad={rad}", color=color, lw=lw, ls=ls, zorder=z,
                        shrinkA=shrink, shrinkB=shrink, mutation_scale=10)
    ax.add_patch(a)
    return a


# ------------------------------------------------------------------------------------------------ geometry
def clip_to_box(p_from, p_to, half_x, half_y, center):
    # point where the straight line from p_from (outside the box) to p_to (inside) enters the box
    # [center - half, center + half]; used to draw an arrow from an off-panel start into a zoom panel
    p0 = np.asarray(p_from, float) - np.asarray(center, float)
    p1 = np.asarray(p_to, float) - np.asarray(center, float)
    d = p1 - p0
    lo, hi = 0.0, 1.0
    for i, hw in enumerate((half_x, half_y)):
        if abs(d[i]) < 1e-12:
            continue
        t0, t1 = (-hw - p0[i]) / d[i], (hw - p0[i]) / d[i]
        lo = max(lo, min(t0, t1))
        hi = min(hi, max(t0, t1))
    return np.asarray(center, float) + p0 + lo * d
