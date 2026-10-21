"""Figure 19: the whiteboard solution planner, the path steps it lacks, problems, and the extension layer."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

RED = "#b91c1c"
fig = plt.figure(figsize=(13, 9.2))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "Solution planner: the whiteboard pipeline finds configurations; the path steps, drawn in blue, are what still has to be built",
      "Core steps as on the board (grey) · problems and fixes (red notes) · extension layer for the question-mark items (dashed) · schematic")

cols = [0.03, 0.275, 0.52, 0.765]; W = 0.215
def step(ci, y, t, b, note=None, h=0.095, **kw):
    box(ax, cols[ci], y, W, h, t, b, fs=8.6, bfs=6.9, **kw)
    if note:
        ax.text(cols[ci] + W / 2, y - 0.012, note, ha="center", va="top", fontsize=6.6, color=RED, linespacing=1.2)

# ---- row 1
y1 = 0.78
step(0, y1, "(1) Structure retriever", "surface + adsorbates + general\nsystem description from the prompt",
     "fix: settings and references locked\nin PROJECT.md before anything runs")
step(1, y1, "(2) Adsorption sites (pymatgen)", "sites on the clean slab",
     "fix: symmetry-complete (spglib, CatKit);\nfcc vs hcp hollow by the atom beneath")
step(2, y1, "(3) Adsorbate placement", "'very important'; 'a Python script\nmight not be enough'",
     "problem: the LLM must not place atoms\nfix: script + symmetry + random displacement;\nconformers in vacuum first; start 2–3 Å, not 10 Å")
step(3, y1, "(4) Initial configurations", "all DoF of the adsorbate × all sites",
     "problem: explodes for large molecules\nfix: Burnside counting; keep few conformers")
# ---- row 2
y2 = 0.555
step(0, y2, "(4.1) Physics-based filtering", "drop configurations that are not physical",
     "fix: write the tests: desorbed, migrated,\ndissociated, reconstructed, imaginary mode")
step(1, y2, "(5) MLIP selection", "which universal potential; prospect\nof active-learning fine-tuning",
     "problem: organometallics are where MLIPs\nfail; dispersion, spin, images ≥ 10 Å apart")
step(2, y2, "(6) Anomaly filter", "same checks after relaxation",
     "fix: same code as 4.1, run on every\nrelaxed structure, verdict into the card")
step(3, y2, "(7) Uncertainty estimation", "disagreement across the models from (5)",
     "problem: disagreement is not error\nfix: calibrate on a few DFT labels")
# ---- row 3: human choice + path block
y3 = 0.315
step(0, y3, "(8) Rank; human picks ≤ 5", "with uncertainty and potential issues",
     "fix: choose on descriptor card + rank\n+ uncertainty; then DFT on the five")
grp = FancyBboxPatch((0.27, 0.255), 0.715, 0.175, boxstyle="round,pad=0.004,rounding_size=0.02",
                     fc=HI_FACE, ec=HI_EDGE, lw=1.8, zorder=1); ax.add_patch(grp)
ax.text(0.6275, 0.42, "Path steps to add: we know the start and the end, these find the way between", ha="center", va="top",
        fontsize=8.6, fontweight="bold", color="#1e3a8a")
sub = [("(9) Final-state enumeration", "product geometry on the surface:\nsites, orientations, pair distances"),
       ("(10) Atom mapping and IS–FS pairing", "minimal displacement after symmetry;\nkeep several pairs, not one"),
       ("(11) Path search", "ML NEB (CatTSunami-style), then\nclimbing image or dimer refinement"),
       ("(12) Saddle validation", "exactly one imaginary mode;\npath reaches this IS and this FS"),
       ("(13) DFT refinement", "single points, then relax endpoints\nand saddle with the locked settings"),
       ("(14) Report", "barrier, validated path, both\nuncertainties; energetic span if multi-step")]
sw, sh = 0.225, 0.056
for i, (t, b) in enumerate(sub):
    r, c = divmod(i, 3)
    x = 0.283 + c * 0.236; y = 0.338 - r * 0.074
    box(ax, x, y, sw, sh, t, b, fs=7.6, bfs=6.4)
    if c < 2: arrow(ax, (x + sw + 0.002, y + sh / 2), (x + 0.236 - 0.002, y + sh / 2), lw=1.1, ms=8)
ax.text(0.6275, 0.262, "(11) continues at (12), bottom-left", ha="center", fontsize=6.4, color="#555555")

# ---- arrows between core boxes
for y in (y1, y2):
    for ci in range(3):
        arrow(ax, (cols[ci] + W + 0.002, y + 0.0475), (cols[ci + 1] - 0.002, y + 0.0475), lw=1.3)
def snake(y_from, y_to):
    xr = cols[3] + W / 2; xl = cols[0] + W / 2; ym = y_from - 0.075
    ax.plot([xr, xr, 0.015, 0.015], [y_from, ym, ym, ym], color=GREY, lw=1.1, zorder=0)
    ax.plot([0.015, 0.015], [ym, y_to + 0.1 + 0.03], color=GREY, lw=1.1, zorder=0)
    arrow(ax, (0.015, y_to + 0.13), (xl - 0.09, y_to + 0.095 + 0.002), lw=1.1, con="arc3,rad=-0.3")
snake(y1, y2); snake(y2, y3)
arrow(ax, (cols[0] + W + 0.002, y3 + 0.0475), (0.27 - 0.002, y3 + 0.0475), lw=1.3)

# ---- extension layer
ext = FancyBboxPatch((0.03, 0.035), 0.955, 0.145, boxstyle="round,pad=0.004,rounding_size=0.02",
                     fc="white", ec=GREY, lw=1.2, ls="--", zorder=1); ax.add_patch(ext)
ax.text(0.5075, 0.172, "Extension layer: the question marks on the board, kept out of the core and added later if time allows",
        ha="center", va="top", fontsize=8.6, fontweight="bold", color="#444444")
exts = [("Agentic uncertainty (?)", "run the planner N times on the same\ninput; report how often the chosen\nconfigurations and path differ", 7),
        ("Active-learning loop (?)", "high uncertainty → a few DFT labels\n→ fine-tune the MLIP → re-run 6 to 8", 5),
        ("LLM critic on cards (?)", "'physics filtering beyond a script':\ncritic reads descriptor cards only;\nnever overrides a code check", 4.1),
        ("+DFT on the chosen five (?)", "the board's '+DFT?': yes, at least\nsingle points before any path search", 8),
        ("Multi-step mechanism (?)", "adsorb → diffuse → react → desorb;\nenergetic span instead of one saddle;\ncatalysis later", 14)]
ew = 0.178
for i, (t, b, _) in enumerate(exts):
    x = 0.045 + i * 0.191
    p = FancyBboxPatch((x, 0.058), ew, 0.098, boxstyle="round,pad=0.004,rounding_size=0.02",
                       fc="white", ec=GREY, lw=1.0, ls="--", zorder=2); ax.add_patch(p)
    ax.text(x + ew / 2, 0.146, t, ha="center", va="top", fontsize=7.8, fontweight="bold", zorder=3)
    ax.text(x + ew / 2, 0.063, b, ha="center", va="bottom", fontsize=6.4, zorder=3, linespacing=1.2)
tags = ["attaches to steps 7 and 8", "attaches to step 5", "attaches to steps 4.1 and 6", "attaches to step 8", "attaches to step 14"]
for i, t in enumerate(tags):
    ax.text(0.045 + i * 0.191 + ew / 2, 0.04, t, ha="center", va="bottom", fontsize=6.3, color="#777777", style="italic")
ax.text(0.5075, 0.012, "Reading order: rows 1 to 3 left to right (thin grey connectors wrap the rows); blue block follows step 8; each dashed box names the core step it attaches to.",
        ha="center", fontsize=7.2, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "19-solution-planner-pipeline.png"))
