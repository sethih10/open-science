"""Figure 30: the board as a vertical flowchart. Grey: computation. Coral: step 3, the stated problem, with its
six points. Purple: where an agent or LLM input enters; dashed is optional."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

GREY_F, GREY_E = "#f0efe9", "#8a8a85"
CORAL_F, CORAL_E = "#fdf0ea", "#c2410c"
PUR_F, PUR_E, PUR_T = "#ecebff", "#6366f1", "#4338ca"
fig = plt.figure(figsize=(8.6, 15.2))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
fig.text(0.5, 0.978, "The pipeline as drawn on the board, 21 October 2026", ha="center", va="top", fontsize=12.5, fontweight="bold")
fig.text(0.5, 0.957, "grey: computation · coral: step 3, the stated problem · purple: agent or LLM input, dashed is optional", ha="center", va="top", fontsize=8.6, color="#555555")

CX, W = 0.355, 0.60          # main column
def box(x, y, w, h, title, sub=None, fc=GREY_F, ec=GREY_E, tc=TEXT, ls="-", fs=9.4, lw=1.2, z=3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012", fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))
    if sub:
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center", fontsize=fs, fontweight="bold" if fc != GREY_F else "normal", color=tc, zorder=z + 1)
        ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=7.6, color="#555555" if tc == TEXT else tc, zorder=z + 1)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs, color=tc, zorder=z + 1)
def down(y0, y1, x=CX + W / 2):
    arrow(ax, (x, y0), (x, y1), color=GREY_E, lw=1.2, ms=10)

H = 0.038; G = 0.016
y = 0.93
main = [("Input prompt: surface + adsorbates + description", None), ("(1) Structure retriever", None),
        ("(1*) MLIP selection (AL prospect)", None), ("(2) Adsorption sites via pymatgen", None)]
ys = {}
for t, s in main:
    box(CX, y - H, W, H, t); ys[t] = (y - H, y); down(y - H - 0.002, y - H - G + 0.002); y -= H + G

# ---- step 3 group
g_top = y; inner_h = 0.044; ig = 0.013
sub = [("1. Minimum distance", "dissociated atom not pulled back"), ("2. Distance boundary [1.5 d, 5] Å", "d = max. (vdW) bond length, literature"),
       ("3. MLIP pull force", "on the binding fragment, to set its position"), ("4. Criticise and adjust", "agentic: consequences of bond cleavage")]
g_h = 0.042 + 4 * (inner_h + ig) + inner_h + 0.016
ax.add_patch(FancyBboxPatch((CX, g_top - g_h), W, g_h, boxstyle="round,pad=0.004,rounding_size=0.02", fc=CORAL_F, ec=CORAL_E, lw=1.4, zorder=2))
ax.text(CX + W / 2, g_top - 0.021, "(3) Adsorbate placement (very important)", ha="center", va="center", fontsize=9.8, fontweight="bold", zorder=4)
yy = g_top - 0.042; ix, iw = CX + 0.03, W - 0.06
for i, (t, s) in enumerate(sub):
    purple = i == 3
    box(ix, yy - inner_h, iw, inner_h, t, s, fc=PUR_F if purple else GREY_F, ec=PUR_E if purple else GREY_E, tc=PUR_T if purple else TEXT, fs=9.2, z=4)
    yy -= inner_h
    if i < 3: down(yy - 0.002, yy - ig + 0.002); yy -= ig
# split to 5 or 6
yy -= 0.004
half = (iw - 0.05) / 2
xl, xr = ix, ix + half + 0.05
ax.plot([CX + W / 2, CX + W / 2], [yy + 0.004, yy - 0.004], color=GREY_E, lw=1.2, zorder=4)
ax.plot([xl + half / 2, xr + half / 2], [yy - 0.004, yy - 0.004], color=GREY_E, lw=1.2, zorder=4)
down(yy - 0.004, yy - ig + 0.001, x=xl + half / 2); down(yy - 0.004, yy - ig + 0.001, x=xr + half / 2)
yy -= ig
box(xl, yy - inner_h, half, inner_h, "5. Pick site", "agent or pymatgen", fc=PUR_F, ec=PUR_E, tc=PUR_T, fs=9.2, z=4)
box(xr, yy - inner_h, half, inner_h, "6. Minima hopping", "with the selected MLIP", fs=9.2, z=4)
ax.text(CX + W / 2, yy - inner_h / 2, "or", ha="center", va="center", fontsize=8.6, color="#555555", zorder=5)
y = g_top - g_h
down(y - 0.002, y - G + 0.002); y -= G

rest = [("(4) Initial configurations", None), ("(5) Physics-based + anomaly filtering", None), ("(6) SOAP clustering, 3 lowest-E per cluster", None),
        ("(7) Uncertainty estimation (all models)", None), ("(8) Rank; user picks up to 5", None), ("Solution (+ uncertainty, issues)", None)]
for i, (t, s) in enumerate(rest):
    box(CX, y - H, W, H, t); ys[t] = (y - H, y)
    if i < len(rest) - 1: down(y - H - 0.002, y - H - G + 0.002)
    y -= H + G

# ---- purple side inputs
SX, SW, SH = 0.03, 0.245, 0.036
def side(label, ytarget, dashed=False, dy=0.0):
    yb = ytarget - SH / 2 + dy
    box(SX, yb, SW, SH, label, fc=PUR_F, ec=PUR_E, tc=PUR_T, ls="--" if dashed else "-", fs=9.0, lw=1.1)
    arrow(ax, (SX + SW + 0.003, yb + SH / 2), (CX - 0.004, yb + SH / 2), color=PUR_E, lw=1.2, ms=9, ls="--" if dashed else "-")
side("Critic, knowledge", g_top - 0.021)
side("Vision model (?)", g_top - 0.021 - 0.055, dashed=True)
yc = lambda k: (ys[k][0] + ys[k][1]) / 2
side("Reasoning questions", yc("(5) Physics-based + anomaly filtering"))
side("Agentic uncertainty", yc("(7) Uncertainty estimation (all models)"))
side("Critic, knowledge", yc("(8) Rank; user picks up to 5"))
finish(fig, os.path.join(os.path.dirname(__file__), "..", "30-board-flowchart.png"))
