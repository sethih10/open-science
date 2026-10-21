"""Figure 19: the solution planner from the second whiteboard (21 October 2026). The board's step 3,
placing the dissociated fragment, is the final-state problem; its six points map onto 9a to 9e."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

RED = "#b91c1c"
fig = plt.figure(figsize=(13, 10.4))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "Solution planner, second board: placing the dissociated fragment (step 3) is the final-state problem, and its six points are 9a to 9e",
      "board steps in grey with the problem and fix in red · the six points of step 3 in blue, each mapped to its sub-step · question marks dashed · schematic")

cols = [0.03, 0.275, 0.52, 0.765]; W = 0.215
def step(ci, y, t, b, note=None, h=0.092, hi=False):
    box(ax, cols[ci], y, W, h, t, b, fs=8.4, bfs=6.8, hi=hi)
    if note:
        ax.text(cols[ci] + W / 2, y - 0.011, note, ha="center", va="top", fontsize=6.5, color=RED, linespacing=1.2)

y1 = 0.80
step(0, y1, "(1) Structure retriever", "surface and adsorbates with their energies;\nE_ads from the literature; a system description",
     "fix: lock settings and references\nin PROJECT.md before anything runs")
step(1, y1, "(1*) MLIP selection", "chosen before placement so step 3 can use it;\nactive-learning prospect",
     "fix: benchmark on the system class, record why;\nspin for Ni and Co; one potential for IS and FS")
step(2, y1, "(2) Adsorption sites with pymatgen", "sites on the clean slab",
     "fix: symmetry-complete on ACAT and spglib;\nfcc and hcp hollows apart; count reported")
step(3, y1, "(3) Adsorbate placement: very important", "'a Python script might not be enough';\nthe six points below", hi=True,
     note="this is the stated problem: the final state\nwith B as near to A as it can be without bonding back")
y2 = 0.585
step(0, y2, "(4) Initial configurations", "all degrees of freedom of the adsorbate\n× all sites",
     "fix: Burnside counting; conformers in\nvacuum first; start 2 to 3 Å up")
step(1, y2, "(5) Physics-based and anomaly filtering", "script, and ML or script",
     "fix: the nine-check gate as code, before and\nafter relaxation; the LLM never overrides it")
step(2, y2, "(6) SOAP clustering", "pick the lowest-energy configurations\nfrom each cluster, three or more",
     "fix: cluster the survivors of the gate, as NEBscape\ndoes; keep the nearest and the lowest per cluster")
step(3, y2, "(7) Uncertainty estimation", "with all relevant models from (1*)",
     "problem: disagreement is not error\nfix: calibrate on a few DFT labels")
y3 = 0.37
step(0, y3, "Input prompt", "surface + adsorbates + system description;\ncritic and knowledge prompts into 3 and 8;\nreasoning questions into 3 and 5",
     "fix: knowledge as a written skill, prompts\nas a fixed list; the LLM reads cards only")
step(1, y3, "(8) Rank; user picks up to 5", "optional: uncertainty and potential issues",
     "fix: choose on descriptor card, rank and\nuncertainty; choice and reason to the case bank")
step(2, y3, "Solution", "the nearest non-recombining final state,\nE(FS near), E(FS ∞), rejections, uncertainty",
     "measured now: recombination rate,\nlateral interaction, policy comparison")
step(3, y3, "Known and supplied", "surface energy; adsorbate energy relaxed\nin vacuum; E_ads from the literature",
     "fix: one set of gas references for AB, A\nand B; same settings for all three")
for y in (y1, y2):
    for ci in range(3):
        arrow(ax, (cols[ci] + W + 0.002, y + 0.046), (cols[ci + 1] - 0.002, y + 0.046), lw=1.3)
arrow(ax, (cols[1] + W + 0.002, y3 + 0.046), (cols[2] - 0.002, y3 + 0.046), lw=1.3)
def snake(y_from, y_to):
    xr = cols[3] + W / 2; xl = cols[0] + W / 2; ym = y_from - 0.072
    ax.plot([xr, xr, 0.015, 0.015], [y_from, ym, ym, ym], color=GREY, lw=1.1, zorder=0)
    ax.plot([0.015, 0.015], [ym, y_to + 0.13], color=GREY, lw=1.1, zorder=0)
    arrow(ax, (0.015, y_to + 0.13), (xl - 0.09, y_to + 0.094), lw=1.1, con="arc3,rad=-0.3")
snake(y1, y2)
arrow(ax, (cols[3] + W / 2, y2 - 0.034), (cols[1] + W / 2 + 0.05, y3 + 0.094), lw=1.1, con="arc3,rad=0.25")

# ---- the six points of step 3, mapped to 9a to 9e
grp = FancyBboxPatch((0.03, 0.108), 0.955, 0.205, boxstyle="round,pad=0.004,rounding_size=0.02",
                     fc=HI_FACE, ec=HI_EDGE, lw=1.8, zorder=1); ax.add_patch(grp)
ax.text(0.5075, 0.309, "Step 3 on the board, point by point, and where each lands in the final-state procedure 9a to 9e",
        ha="center", va="top", fontsize=8.6, fontweight="bold", color="#1e3a8a")
pts = [("1 · the least distance at which B is not pulled back", "→ 9d, the bond-re-formed check; CatTSunami's\n1.25 to 1.63× of the bond length is the breaking range"),
       ("2 · window [1.5 d, 5] Å, d the length of the bond to break", "→ 9b, the range of B sites around A;\nNEBscape cuts at 4.5 Å; the floor is the gate, not a guess"),
       ("3 · the MLIP's pull force on the binding fragment", "→ new 9c pre-filter: one force call per pair before\nrelaxing; force on B towards A means likely recombination"),
       ("4 · agentic critique of what the cleavage does", "→ geometry-critic on cards: proposes a site type per\nfragment, AdsMind style; never overrides a code check"),
       ("5 · pymatgen site and orientation so the fragment adsorbs", "→ 9a, symmetry-complete and counted; the site-type\nproposal of point 4 narrows the list, code places"),
       ("6 · or minima hopping with the MLIP", "→ NEBscape's generator, wrapped; its Pareto choice is the\nbaseline our nearest-first policy is scored against")]
pw, ph = 0.305, 0.072
for i, (t, b) in enumerate(pts):
    r, c = divmod(i, 3)
    x = 0.043 + c * 0.317; y = 0.203 - r * 0.085
    box(ax, x, y, pw, ph, t, b, fs=7.3, bfs=6.4)

# ---- extension layer
ext = FancyBboxPatch((0.03, 0.014), 0.955, 0.088, boxstyle="round,pad=0.004,rounding_size=0.02",
                     fc="white", ec=GREY, lw=1.2, ls="--", zorder=1); ax.add_patch(ext)
ax.text(0.5075, 0.099, "Extension layer: the board's question marks, kept out of the core", ha="center", va="top", fontsize=8.2, fontweight="bold", color="#444444")
exts = [("Vision model predicts the whole placement (?)", "attaches to 3; only after the geometry\nbenchmark shows an image helps"),
        ("Agentic uncertainty, and DFT (?)", "attaches to 7; N runs, variance of choices;\nDFT single points on the chosen five"),
        ("Active learning from (1*)", "doubt → a few DFT labels → fine-tune"),
        ("More than three per cluster (?)", "attaches to 6; set by the recombination\nrate per cluster, not by hand")]
ew = 0.225
for i, (t, b) in enumerate(exts):
    x = 0.042 + i * 0.237
    p = FancyBboxPatch((x, 0.020), ew, 0.052, boxstyle="round,pad=0.003,rounding_size=0.01", fc="white", ec=GREY, lw=1.0, ls="--", zorder=2); ax.add_patch(p)
    ax.text(x + ew / 2, 0.068, t, ha="center", va="top", fontsize=7.0, fontweight="bold", zorder=3)
    ax.text(x + ew / 2, 0.024, b, ha="center", va="bottom", fontsize=6.2, zorder=3, linespacing=1.2)
finish(fig, os.path.join(os.path.dirname(__file__), "..", "19-solution-planner-pipeline.png"))
