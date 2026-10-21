"""Figure 26: the plan in five steps, as the team drew it, each mapped to the rows of the full pipeline."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

OWNER_COL = {"TOOL": "#374151", "LLM": "#0e7490", "HUMAN": "#be185d"}
fig = plt.figure(figsize=(14, 4.9))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "The plan in five steps: relaxed inputs in, the dissociated final state out",
      "the team's numbering is kept; the grey line under each box names the rows of the full pipeline it corresponds to · schematic")
steps = [("(1) Inputs", "relaxed initial state AB* on the surface;\nrelaxed clean surface; relaxed adsorbate\nin vacuum; settings locked in PROJECT.md", "HUMAN · TOOL", "rows 1 and 1*", False),
         ("(3) Unit cell and unique sites", "symmetry-inequivalent sites on the slab,\ncounted; the fragment that keeps the\nbinding atom placed near its old site", "TOOL", "rows 2 and 9a", False),
         ("(4) Least distance before pull-back", "B sites around A within [1.5 d, 5] Å;\none force call per pair, then relaxation;\nthe gate: no A–B bond, nothing desorbed", "TOOL", "rows 9b, 9c, 9d", True),
         ("(5) Best configuration for both", "survivors clustered by SOAP; nearest first,\nthen energy; a few kept per cluster; doubt from\nthe committee; the human picks up to five", "TOOL · LLM", "rows 9e, 7, 8", False),
         ("(2) Output: the final state", "A* + B* as close as they can be without\nbonding back; E(FS near), E(FS ∞), pairs\nrejected with reasons, recombination rate", "TOOL · HUMAN", "row 14", False)]
W, H, G = 0.178, 0.46, 0.0225; x0 = 0.02
for i, (t, b, own, rows, hi) in enumerate(steps):
    x = x0 + i * (W + G); y = 0.30
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.004,rounding_size=0.02",
                                fc=HI_FACE if hi else "white", ec=HI_EDGE if hi else EDGE, lw=1.6 if hi else 1.0, zorder=2))
    ax.text(x + W / 2, y + H - 0.03, t, ha="center", va="top", fontsize=9.2, fontweight="bold", zorder=3)
    parts = own.split(" · "); total = sum(len(p) for p in parts) + 3 * (len(parts) - 1); cw = 0.0048
    xs = x + W / 2 - total * cw / 2
    for p in parts:
        ax.text(xs, y + H - 0.105, p, ha="left", va="top", fontsize=7.2, fontweight="bold", color=OWNER_COL[p], zorder=3); xs += (len(p) + 3) * cw
    ax.text(x + W / 2, y + 0.2, b, ha="center", va="center", fontsize=7.4, zorder=3, linespacing=1.3)
    ax.text(x + W / 2, y - 0.045, rows + " of the full pipeline", ha="center", va="top", fontsize=7.2, color="#666666", style="italic")
    if i < 4: arrow(ax, (x + W + 0.002, y + H / 2), (x + W + G - 0.002, y + H / 2), lw=1.4, ms=11)
ax.text(0.5, 0.07, "Owners: TOOL is deterministic code, LLM reads descriptor cards and never touches coordinates, HUMAN locks settings and interprets. "
                   "The highlighted step is the stated problem.", ha="center", va="bottom", fontsize=7.6, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "26-simplified-pipeline.png"))
