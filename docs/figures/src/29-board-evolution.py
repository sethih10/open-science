"""Figure 29: how the plan evolved, one row per step of the board, in the board's order and numbering: what the
board says, what the literature refined, what we added or decided, what is open or an extension. All text from
_board.py."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from _board import STEPS, BOARD_DATE, OWNER_NAMES, code_order_note
from matplotlib.patches import FancyBboxPatch

fig = plt.figure(figsize=(17, 21))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "How the plan evolved: one row per step of the board, in the board's order; what the board says, what the literature refined, what we added",
      f"board of {BOARD_DATE}, numbering kept, including the six points of step 3 · owner line under each step · amber is open, dashed purple is an extension · schematic")

leg = [("board", "as written on the board"), ("lit", "refined by the literature"), ("ours", "what we added or decided"),
       ("open", "open: team decision"), ("ext", "extension layer, later"), ("deferred", "deferred: commented out of the code")]
for j, (k, lab) in enumerate(leg):
    x = 0.04 + j * 0.155
    ax.add_patch(FancyBboxPatch((x, 0.8905), 0.018, 0.011, boxstyle="round,pad=0.002,rounding_size=0.004", zorder=2, **KIND[k]))
    ax.text(x + 0.023, 0.896, lab, ha="left", va="center", fontsize=8.2)
ax.text(0.04, 0.877, "Owner line:", ha="left", va="center", fontsize=7.6, color="#333333")
xo = 0.10
for t, d in [("TOOL", "deterministic code"), ("LLM", "reads cards, proposes, drafts"), ("HUMAN", "decides, picks, interprets"), ("SKILL", "a written procedure the LLM follows")]:
    ax.text(xo, 0.877, t, ha="left", va="center", fontsize=7.6, fontweight="bold", color=OWNER_COL[t])
    ax.text(xo + 0.0056 * len(t) + 0.006, 0.877, d, ha="left", va="center", fontsize=7.6, color="#333333")
    xo += 0.0056 * len(t) + 0.0046 * len(d) + 0.032

COL = {"board": (0.040, 0.215), "lit": (0.267, 0.245), "ours": (0.524, 0.235), "open": (0.771, 0.222)}
WRAP = {"board": 44, "lit": 52, "ours": 50, "open": 46}
HEAD = {"board": "On the board", "lit": "Refined by the literature", "ours": "What we added or decided", "open": "Open, or an extension"}
for k, (x0, w) in COL.items():
    ax.text(x0 + w / 2, 0.860, HEAD[k], ha="center", va="center", fontsize=8.8, fontweight="bold", color="#333333")
ax.plot([0.04, 0.993], [0.849, 0.849], color=EDGE, lw=0.8)

TOP, PITCH, H = 0.843, 0.0478, 0.042
def ytop(i): return TOP - i * PITCH
def cell(kind, col, i, head, body, hfs=7.6, bfs=6.8, owner=None):
    x0, w = COL[col]; y = ytop(i) - H
    body = wrap(body, WRAP[col]); n = body.count("\n") + 1
    bfs = bfs if n <= 3 else 6.2
    ax.add_patch(FancyBboxPatch((x0, y), w, H, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND[kind]))
    ax.text(x0 + w / 2, y + H - 0.004, head, ha="center", va="top", fontsize=hfs, fontweight="bold", color=TITLE_COL[kind], zorder=3)
    if owner:
        parts = owner; total = sum(len(t) for t in parts) + 3 * (len(parts) - 1); cw = 0.0032
        xs = x0 + w / 2 - total * cw / 2
        for t in parts:
            ax.text(xs, y + H - 0.0135, t, ha="left", va="top", fontsize=6.2, fontweight="bold", color=OWNER_COL[t], zorder=3); xs += (len(t) + 3) * cw
        ax.text(x0 + w / 2, y + (H - 0.024) / 2, body, ha="center", va="center", fontsize=bfs, zorder=3, linespacing=1.14)
    else:
        ax.text(x0 + w / 2, y + (H - 0.012) / 2, body, ha="center", va="center", fontsize=bfs, zorder=3, linespacing=1.16)
def none(col, i):
    x0, w = COL[col]; ax.text(x0 + w / 2, ytop(i) - H / 2, "none", ha="center", va="center", fontsize=7.0, color="#888888", style="italic")

for i, s in enumerate(STEPS):
    cell("board", "board", i, s.title, s.board, hfs=7.7, bfs=6.6, owner=[OWNER_NAMES[o] for o in s.owners])
    cell("lit", "lit", i, s.lit_source, s.lit)
    cell("ours", "ours", i, "Ours", s.ours)
    if s.deferred: cell("deferred", "open", i, "DEFERRED", s.deferred + (f" · open: {s.open}" if s.open else ""), hfs=7.2, bfs=6.4)
    elif s.open: cell("open", "open", i, "Open", s.open + (f" · extension: {s.ext}" if s.ext else ""), hfs=7.2, bfs=6.4 if s.ext else 6.8)
    elif s.ext: cell("ext", "open", i, "EXTENSION", s.ext, hfs=7.2, bfs=6.8)
    else: none("open", i)
sx = COL["board"][0] + COL["board"][1] / 2
for i in range(len(STEPS) - 1):
    arrow(ax, (sx, ytop(i) - H - 0.0008), (sx, ytop(i + 1) + 0.0008), lw=1.3, ms=8)
pts = [i for i, s in enumerate(STEPS) if s.is_point]
x0, w = COL["board"]
ax.add_patch(FancyBboxPatch((x0 - 0.006, ytop(pts[-1]) - H - 0.004), w + 0.012, ytop(pts[0]) - (ytop(pts[-1]) - H) + 0.008,
                            boxstyle="round,pad=0.002,rounding_size=0.01", fc="none", ec=HI_EDGE, lw=1.6, ls="--", zorder=1))
ax.text(x0 - 0.012, (ytop(pts[0]) + ytop(pts[-1]) - H) / 2, "step 3: adsorbate placement, the stated problem", rotation=90, ha="center", va="center", fontsize=7.4, color=HI_EDGE, fontweight="bold")
ax.text(0.04, 0.045, "The board's own open questions: step 3 applies to dissociative adsorption only, by the fixed scope; the models of step 7 are the candidates benchmarked at 1*; "
                     "\"phys. int.\" at step 8 is read as the physical issues shown on each card; the vision model feeds step 3 and is an extension.\n"
                     f"The six points of step 3 keep the board's order 1 → 2 → 3 → 4 → 5 or 6; {code_order_note()}.",
        ha="left", va="bottom", fontsize=7.2, style="italic", color="#444444", linespacing=1.3)
finish(fig, os.path.join(os.path.dirname(__file__), "..", "29-board-evolution.png"), copy_to="board-evolution")
