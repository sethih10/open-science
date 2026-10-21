"""Figure 22: what has to be built, in which order, what each piece reuses, and what is measured.
Numbered blue badges and thick blue arrows mark the critical path to the first measured barrier."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch, Circle

GREEN, AMBER_F, AMBER_E, PURPLE_F, PURPLE_E = "#15803d", "#fef3c7", "#b45309", "#f3e8ff", "#7e22ce"
KIND = {"decide": dict(fc="#f3f4f6", ec="#6b7280", lw=1.1, ls="-"),
        "build":  dict(fc="white",   ec=EDGE,      lw=1.0, ls="-"),
        "measure":dict(fc=AMBER_F,   ec=AMBER_E,   lw=1.1, ls="-"),
        "release":dict(fc=HI_FACE,   ec=HI_EDGE,   lw=1.4, ls="-"),
        "ext":    dict(fc=PURPLE_F,  ec=PURPLE_E,  lw=1.2, ls="--")}

fig = plt.figure(figsize=(16, 11))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "What has to be built for the final state: five columns in order, the numbered blue path is the shortest route to one validated nearest final state",
      "each box: the task, what it does, what it reuses (green), what it needs (grey) · dashed purple is the extension layer, including the path, which is a later phase · schematic")

# legend
leg = [("decide", "decide first (human)"), ("build", "build: a code tool"), ("measure", "measure: an experiment"),
       ("release", "release"), ("ext", "extension layer, later")]
for j, (k, lab) in enumerate(leg):
    x = 0.02 + j * 0.15
    ax.add_patch(FancyBboxPatch((x, 0.8835), 0.018, 0.011, boxstyle="round,pad=0.002,rounding_size=0.004", zorder=2, **KIND[k]))
    ax.text(x + 0.023, 0.889, lab, ha="left", va="center", fontsize=8.2)
ax.add_patch(Circle((0.787, 0.889), 0.0075, fc=HI_EDGE, ec="white", zorder=3)); ax.text(0.787, 0.889, "3", ha="center", va="center", fontsize=6.5, color="white", fontweight="bold", zorder=4)
ax.text(0.80, 0.889, "critical path, in order", ha="left", va="center", fontsize=8.2)
ax.text(0.905, 0.889, "reuse: existing code", ha="left", va="center", fontsize=8.2, color=GREEN)

COLW, GAP, X0 = 0.176, 0.020, 0.014
def cx(i): return X0 + i * (COLW + GAP)
heads = ["0 · Decide first", "1 · Foundations", "2 · ML relaxation and trust", "3 · Final state; the path later", "4 · Measure, then release"]
for i, h in enumerate(heads):
    ax.text(cx(i) + COLW / 2, 0.853, h, ha="center", va="center", fontsize=9.2, fontweight="bold", color="#333333")
ax.plot([0.014, 0.982], [0.838, 0.838], color=EDGE, lw=0.8)

TOP, PITCH, H = 0.828, 0.118, 0.102
pos = {}
def task(col, row, key, kind, head, body, reuse=None, needs=None, badge=None, h=H):
    x = cx(col); y = TOP - row * PITCH - h
    ax.add_patch(FancyBboxPatch((x, y), COLW, h, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND[kind]))
    ax.text(x + COLW / 2, y + h - 0.006, head, ha="center", va="top", fontsize=8.2, fontweight="bold", zorder=3)
    yb = y + h - 0.030
    ax.text(x + COLW / 2, yb, body, ha="center", va="top", fontsize=6.8, zorder=3, linespacing=1.18)
    if reuse: ax.text(x + COLW / 2, y + 0.022 if needs else y + 0.006, "reuse: " + reuse, ha="center", va="bottom", fontsize=6.5, color=GREEN, zorder=3)
    if needs: ax.text(x + COLW / 2, y + 0.006, "needs: " + needs, ha="center", va="bottom", fontsize=6.3, color="#777777", style="italic", zorder=3)
    if badge:
        ax.add_patch(Circle((x + 0.012, y + h - 0.012), 0.0095, fc=HI_EDGE, ec="white", lw=1.2, zorder=5))
        ax.text(x + 0.012, y + h - 0.012, str(badge), ha="center", va="center", fontsize=7, color="white", fontweight="bold", zorder=6)
    pos[key] = (x, y, COLW, h)

# ---- column 0: decide
task(0, 0, "D1", "decide", "System and product", "adsorbate AB*, surface, product A* + B*;\nfirst case *OH → *O + *H on Pt(111)?", badge=1)
task(0, 1, "D2", "decide", "Compute and codes", "DFT code and budget; GPU for MLIPs;\nany DFT NEB at all, or ML only?")
task(0, 2, "D3", "decide", "Benchmark and pass criterion", "OC20NEB product frames as the comparison?\nthen settings match OC20's RPBE and PAW;\nwhat counts as a pass for a final state")
task(0, 3, "D4", "decide", "Headline claim", "barrier-ready endpoints, or\n'knows when not to trust itself'")
task(0, 4, "D5", "decide", "Final-state rules", "distance metric; binding fragment\nfixed or free; nearest survivor or\nlowest energy within one hop")

# ---- column 1: foundations
task(1, 0, "T1", "build", "Settings lock", "convergence sweep on E_ads for cutoff,\nk-mesh, smearing, layers; writes\nPROJECT.md; every run reads it",
     reuse="AiiDA common workflows, SSSP", needs="D1, D3", badge=2)
task(1, 1, "T2", "build", "Site and pair enumeration", "symmetry-complete sites and A–B pairs;\nBurnside count; fcc and hcp apart;\ncount checked against the pattern",
     reuse="spglib, CatKit, pymatgen", needs="T1", badge=3)
task(1, 2, "T3", "build", "Placement script", "conformers in vacuum first; start 2 to 3 Å\nabove the site; random displacement;\nthe LLM never places atoms",
     reuse="ASE, CatKit", needs="T2")
task(1, 3, "T4", "build", "Validity gate", "AdsorbML's four checks + imaginary mode\n+ bond re-formed; one code path for\ninitial and final states",
     reuse="fairchem anomaly detection", needs="T3", badge=4)
task(1, 4, "T5", "build", "Descriptor card", "structure in; site, point group, CN, height,\nbonds, tilt, moments, verdicts out;\nthe only thing the LLM reads",
     reuse="pymatgen, Robocrystallographer", needs="T4")

# ---- column 2: ML and trust
task(2, 0, "T6", "build", "MLIP choice", "benchmark two or three potentials on the\nsystem class; record the choice and why",
     reuse="AtomisticSkills ml-mlip-benchmark", needs="D2", badge=5)
task(2, 1, "T7", "build", "Calibrated doubt", "ensemble disagreement against DFT error\non a few labels; a threshold that\nescalates instead of guessing",
     reuse="UMA, MACE, EquiformerV2", needs="T6, T4")
task(2, 2, "T8", "build", "Rank and human checkpoint", "cards + rank + uncertainty shown;\nthe choice and its reason go to the\nlessons log, later into the skill",
     reuse="none: ours", needs="T5, T7")
task(2, 3, "T9", "ext", "+DFT on the chosen five", "single points before any path search;\nthe board's '+DFT?'", needs="T8, D2")
task(2, 4, "T10", "ext", "Active-learning loop", "high doubt → a few DFT labels →\nfine-tune → re-run 6 to 8",
     reuse="AtomisticSkills ml-mace-finetune", needs="T7, D2")

# ---- column 3: path
task(3, 0, "P1", "build", "Nearest non-recombining FS", "enumerate pairs, relax, gate, rank by\nsite distance; keep several; report\nrejected pairs and E(FS near) − E(FS ∞)",
     reuse="fairchem AutoFrameDissociation", needs="T2, T4, T6, D5", badge=6)
task(3, 1, "P2", "ext", "Later: pairing and connectivity", "atom mapping and unwrapping across the\ncell; check the IS–FS pair is the\nintended reaction",
     reuse="CatTSunami interpolation, NEBscape idea", needs="P1")
task(3, 2, "P3", "ext", "Later: ML band and climbing image", "band on the MLIP, climbing image or\ndimer refinement; several pairs per\nreaction, lowest valid kept",
     reuse="ASE DyNEB with UMA", needs="P2")
task(3, 3, "P4", "ext", "Later: saddle validation", "one imaginary mode; path ends at this IS and\nFS; connectivity constant along the band except\nthe breaking bond; diagnose, revise once",
     reuse="ASE vibrations, Sella, CatTSunami band checks", needs="P3")
task(3, 4, "P5", "build", "DFT check and report", "DFT single points on the chosen final states\nwith the locked settings; E(FS near), E(FS ∞),\nrejections, uncertainty, full decision trace",
     reuse="ASE calculators, AiiDA", needs="P1, T7, D2")

# ---- column 4: measure and release
task(4, 0, "M1", "measure", "H on Pt(111) end to end", "steps 1 to 8 on the simplest system;\nE_ads against CE27 and OC20",
     needs="T1 to T8")
task(4, 1, "M2", "measure", "*OH → *O + *H final state against OC20NEB", "our nearest final state versus the product\nframe of the released band: distance, energy,\nvalidity; the pass criterion is D3",
     needs="P1, P5, D3", badge=7)
task(4, 2, "M3", "measure", "Two numbers nobody reports", "how often the nearest pair bonds back, per\nsystem and per shell; E(FS near) − E(FS ∞), the\nlateral interaction. Later: the barrier shift\nand the band cost from gated endpoints",
     needs="P1, P5")
task(4, 3, "M4", "measure", "Ni(111) doubt demo", "the agent flags ML disagreement and\nstops for review instead of guessing",
     needs="T7, T8")
task(4, 4, "M5", "ext", "Agentic uncertainty", "run the planner N times on one input;\nreport how often its choices differ",
     needs="T8, P5")
task(4, 5, "R1", "release", "Release", "SKILL.md, MCP tools on AtomisticSkills,\nbenchmark data and traces on Zenodo",
     needs="M1, M2", badge=8, h=0.072)

# ---- critical path arrows
def centre(k, side):
    x, y, w, h = pos[k]
    return {"r": (x + w, y + h / 2), "l": (x, y + h / 2), "t": (x + w / 2, y + h), "b": (x + w / 2, y)}[side]
path = [("D1", "T1", "r", "l"), ("T1", "T2", "b", "t"), ("T2", "T4", "b", "t"), ("T4", "T6", "r", "l"),
        ("T6", "P1", "r", "l"), ("P1", "M2", "r", "l"), ("M2", "R1", "r", "r")]
for a, b, sa, sb in path:
    p0, p1 = centre(a, sa), centre(b, sb)
    if (a, b) == ("T2", "T4"):
        # skip past T3 along the left margin of the column
        x = pos["T2"][0] - 0.008
        ax.plot([pos["T2"][0] + 0.03, x, x], [pos["T2"][1], pos["T2"][1], pos["T4"][1] + pos["T4"][3]], color=HI_EDGE, lw=2.2, zorder=1)
        arrow(ax, (x, pos["T4"][1] + pos["T4"][3]), (pos["T4"][0] + 0.03, pos["T4"][1] + pos["T4"][3]), color=HI_EDGE, lw=2.2, ms=12)
        continue
    if (a, b) == ("P1", "P3"):
        x = pos["P1"][0] - 0.008
        ax.plot([pos["P1"][0] + 0.03, x, x], [pos["P1"][1], pos["P1"][1], pos["P3"][1] + pos["P3"][3]], color=HI_EDGE, lw=2.2, zorder=1)
        arrow(ax, (x, pos["P3"][1] + pos["P3"][3]), (pos["P3"][0] + 0.03, pos["P3"][1] + pos["P3"][3]), color=HI_EDGE, lw=2.2, ms=12)
        continue
    if (a, b) == ("T4", "T6"):
        # climb from T4 (row 3) to T6 (row 0) through the gap between the columns
        xg = pos["T4"][0] + pos["T4"][2] + GAP / 2
        ax.plot([p0[0], xg, xg], [p0[1], p0[1], p1[1]], color=HI_EDGE, lw=2.2, zorder=1)
        arrow(ax, (xg, p1[1]), p1, color=HI_EDGE, lw=2.2, ms=12)
        continue
    if (a, b) == ("M2", "R1"):
        # down the right margin of the last column, past the measurement boxes
        xr = pos["M2"][0] + pos["M2"][2] + 0.009
        ax.plot([pos["M2"][0] + pos["M2"][2], xr, xr], [p0[1] - 0.0, p0[1] - 0.0, pos["R1"][1] + pos["R1"][3] / 2], color=HI_EDGE, lw=2.2, zorder=1)
        arrow(ax, (xr, pos["R1"][1] + pos["R1"][3] / 2), (pos["R1"][0] + pos["R1"][2], pos["R1"][1] + pos["R1"][3] / 2), color=HI_EDGE, lw=2.2, ms=12)
        continue
    if (a, b) == ("P1", "M2"):
        xg = pos["P1"][0] + pos["P1"][2] + GAP / 2
        ax.plot([p0[0], xg, xg], [p0[1], p0[1], p1[1]], color=HI_EDGE, lw=2.2, zorder=1)
        arrow(ax, (xg, p1[1]), p1, color=HI_EDGE, lw=2.2, ms=12)
        continue
    arrow(ax, p0, p1, color=HI_EDGE, lw=2.2, ms=12)

# ---- LLM and human layer
yb = 0.035; hb = 0.072
ax.add_patch(FancyBboxPatch((cx(1), yb), 4 * COLW + 3 * GAP, hb, boxstyle="round,pad=0.003,rounding_size=0.01", fc="white", ec=EDGE, lw=1.0, zorder=2))
ax.text(cx(1) + (4 * COLW + 3 * GAP) / 2, yb + hb - 0.008, "The LLM and human layer that runs on top of every column, written last",
        ha="center", va="top", fontsize=8.2, fontweight="bold", zorder=3)
ax.text(cx(1) + (4 * COLW + 3 * GAP) / 2, yb + 0.008,
        "SKILL.md with the procedures (few, human-written) · Formulate interview and PROJECT.md template · lessons log that feeds the skill · "
        "a planner that calls the tools by name, reads descriptor cards, never writes coordinates, and stops at the checkpoints",
        ha="center", va="bottom", fontsize=6.9, zorder=3, linespacing=1.3)
ax.text(cx(0) + COLW / 2, yb + hb / 2, "Answers to column 0\nunblock everything\nto the right", ha="center", va="center", fontsize=7.4, style="italic", color="#555555")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "22-build-plan.png"))
