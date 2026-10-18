# nb09_helpers.py -- helpers for notebooks/09_sanramon2026_dlpicker.ipynb (written by build_09_sanramon2026_dlpicker.py).
#
# The notebook only LOADS the result files of step 12 (runs/sanramon/dlpicker/) and step 14
# (runs/sanramon2026/dlpicker/) and plots them; nothing here picks or changes a result file.
#
# legend_above(), save_fig(), panel_letter() and boxed() are verbatim copies from notebooks/lib/nb07_helpers.py
# (notebook 07), so that both notebooks lay out figures the same way without importing each other's module.
import os

import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.patheffects as pe


# ------------------------------------------------------------------------------------------------
# verbatim copies from notebooks/lib/nb07_helpers.py
# ------------------------------------------------------------------------------------------------
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


def panel_letter(ax, letter, **kw):
    # '(a)' put in front of the panel's left title (call after set_title(..., loc="left")), so that it can never
    # collide with a neighboring panel; the title keeps its font size
    t = ax._left_title
    s = t.get_text()
    t.set_text(f"({letter}) {s}" if s else f"({letter})")


def boxed(axes):
    # all four frame lines on every panel, same color and width
    for ax in np.atleast_1d(axes).ravel():
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_color("k")
            s.set_linewidth(0.8)


# ------------------------------------------------------------------------------------------------
# new helpers for notebook 09
# ------------------------------------------------------------------------------------------------
def tint(color, frac):
    # the color mixed with white; frac = share of white (0 = the color itself, 1 = white)
    r, g, b = to_rgb(color)
    return (r + (1 - r) * frac, g + (1 - g) * frac, b + (1 - b) * frac)


# how the two years are drawn: the earlier year as a pale, hatched bar edged in the model color, the later year as a
# solid bar; the year is therefore never told by color alone (the model is named on the x axis)
YEAR_TINT = 0.62
YEAR_HATCH = "////"


def year_bar(ax, x, y, width, color, year_index):
    # one bar of one model and one year (year_index 0 = 2015, 1 = 2025-26)
    if year_index == 0:
        return ax.bar(x, y, width=width, facecolor=tint(color, YEAR_TINT), edgecolor=color, hatch=YEAR_HATCH,
                      lw=0.8, zorder=2)
    return ax.bar(x, y, width=width, facecolor=color, edgecolor="0.15", lw=0.5, zorder=2)


def year_handles(color="0.35"):
    # legend keys of the two year styles, drawn in a neutral gray
    return [Patch(facecolor=tint(color, YEAR_TINT), edgecolor=color, hatch=YEAR_HATCH, lw=0.8),
            Patch(facecolor=color, edgecolor="0.15", lw=0.5)]


def value_label(ax, x, y, text, fontsize=7.0, pad=0.012):
    # a value written just above a bar (white halo so that it stays readable over grid lines)
    t = ax.text(x, y + pad, text, ha="center", va="bottom", fontsize=fontsize, zorder=6)
    t.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])
    return t


def level_tick(ax, x, y, width, color="k", lw=1.8):
    # a short horizontal line across a bar that marks a second value of the same quantity
    ln, = ax.plot([x - width / 2.0, x + width / 2.0], [y, y], color=color, lw=lw, zorder=5, solid_capstyle="butt")
    ln.set_path_effects([pe.withStroke(linewidth=lw + 1.8, foreground="white")])
    return ln


def foot_label(ax, x, text, y=0.02, fontsize=7.0):
    # a value written at the foot of a bar, inside it, on a small white box: it can never be confused with a marker
    # drawn near the top of the bar
    return ax.text(x, y, text, ha="center", va="bottom", fontsize=fontsize, zorder=6,
                   bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
