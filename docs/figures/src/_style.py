"""Shared look for the design-doc figures: white background, rounded grey boxes, grey arrows, one light-blue
highlight, bold title line. Also the shared colours of the board figures, and finish(), which writes the PNG,
an SVG with editable text, a text dump for board_check.py, and a copy into the root figures folder."""
import os
import textwrap
from pathlib import Path
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
                     "xtick.color": TEXT, "ytick.color": TEXT, "svg.fonttype": "none"})

# ---- colours shared by the board figures (29 to 32)
KIND = {"board":  dict(fc="white",   ec="#374151", lw=1.1, ls="-"),
        "lit":    dict(fc="#dcfce7", ec="#15803d", lw=1.1, ls="-"),
        "ours":   dict(fc=HI_FACE,   ec=HI_EDGE,   lw=1.4, ls="-"),
        "open":   dict(fc="#fef3c7", ec="#b45309", lw=1.1, ls="-"),
        "ext":    dict(fc="#f3e8ff", ec="#7e22ce", lw=1.2, ls="--")}
TITLE_COL = {"board": "#111827", "lit": "#14532d", "ours": "#1e3a8a", "open": "#92400e", "ext": "#581c87"}
OWNER_COL = {"TOOL": "#374151", "LLM": "#0e7490", "HUMAN": "#be185d", "SKILL": "#4d7c0f"}
LANE = {"H": ("Human", "#be185d", "#fdf2f8"), "L": ("LLM agent", "#0e7490", "#ecfeff"),
        "S": ("Skill", "#4d7c0f", "#f7fee7"), "T": ("Tool", "#374151", "#f3f4f6")}
FLOW = {"grey": ("#f0efe9", "#8a8a85"), "coral": ("#fdf0ea", "#c2410c"), "purple": ("#ecebff", "#6366f1", "#4338ca"),
        "amber": ("#fef3c7", "#b45309", "#92400e"), "pink": "#be185d"}
PAUSE = "❚❚"

ROOT_FIGURES = Path(__file__).resolve().parents[3] / "figures"


def wrap(text, width):
    """Wrap a one-line record string for a box of the given character width."""
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False))


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


def finish(fig, out, copy_to=None, tight=False):
    """Write <out>.png, <out>.svg and <out>.txt (every drawn string); copy png and svg to figures/<copy_to>."""
    out = str(out)
    base = out[:-4] if out.endswith(".png") else out
    kw = dict(dpi=150, facecolor="white")
    if tight:
        kw.update(bbox_inches="tight", pad_inches=0.15)
    fig.savefig(base + ".png", **kw)
    fig.savefig(base + ".svg", facecolor="white", **({"bbox_inches": "tight", "pad_inches": 0.15} if tight else {}))
    strings = [t.get_text() for t in fig.findobj(matplotlib.text.Text) if t.get_text().strip()]
    with open(base + ".txt", "w") as f:
        f.write("\n".join(strings))
    print("wrote", base + ".png")
    if copy_to:
        import shutil
        ROOT_FIGURES.mkdir(exist_ok=True)
        for ext in ("png", "svg"):
            shutil.copyfile(f"{base}.{ext}", ROOT_FIGURES / f"{copy_to}.{ext}")
        print("copied to", ROOT_FIGURES / f"{copy_to}.png")
