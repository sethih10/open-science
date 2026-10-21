"""Shared look for the design-doc figures: white background, rounded grey boxes,
grey arrows, one light-blue highlight, bold title line."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

GREY = "#8c8c8c"
EDGE = "#9a9a9a"
TEXT = "#222222"
HI_FACE, HI_EDGE = "#dbeafe", "#2563eb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": TEXT,
                     "axes.edgecolor": EDGE, "axes.labelcolor": TEXT,
                     "xtick.color": TEXT, "ytick.color": TEXT})


def box(ax, x, y, w, h, title, body=None, hi=False, fs=9, bfs=7.8, lw=1.0, pad=0.006):
    """Rounded box with a bold title and optional smaller body text."""
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={pad},rounding_size=0.035",
                       fc=HI_FACE if hi else "white", ec=HI_EDGE if hi else EDGE,
                       lw=1.6 if hi else lw, zorder=2)
    ax.add_patch(p)
    if body:
        ax.text(x + w / 2, y + h - 0.012, title, ha="center", va="top", fontsize=fs,
                fontweight="bold", zorder=3, wrap=True)
        ax.text(x + w / 2, y + 0.012, body, ha="center", va="bottom", fontsize=bfs,
                zorder=3, linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs,
                fontweight="bold", zorder=3)
    return p


def arrow(ax, p0, p1, color=GREY, lw=1.2, style="-|>", ms=10, con="arc3,rad=0.0", ls="-"):
    a = FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=ms, color=color, lw=lw,
                        connectionstyle=con, linestyle=ls, zorder=1, shrinkA=2, shrinkB=2)
    ax.add_patch(a)
    return a


def title(fig, text, sub=None):
    fig.text(0.5, 0.965, text, ha="center", va="top", fontsize=12.5, fontweight="bold")
    if sub:
        fig.text(0.5, 0.925, sub, ha="center", va="top", fontsize=9, color="#555555")


def finish(fig, out):
    fig.savefig(out, dpi=150, facecolor="white")
    print("wrote", out)
