"""Figure 17: the LLM reads descriptor cards and verdicts, never coordinates."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *

fig = plt.figure(figsize=(11, 7.2))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "Geometry stays in code: the LLM reads descriptor cards and verdicts, never coordinates",
      "Top: what the benchmarks found. Bottom: how geometry flows through our agent · schematic")

# evidence row
ev = [
 ("AtomWorld (2025)", "10 structure edits in CIF; add/remove 60–95%,\nmove 20–80%, rotate below 12%;\npymatgen tools gave limited gains"),
 ("Adsorb-Agent (2024)", "LLM-proposed configurations:\nMAE 1.84 eV vs DFT, max above 3.5 eV,\nsign errors on molecular adsorbates"),
 ("LLMConfBench (2026)", "Ranking conformers from raw XYZ:\nfrontier models beat UFF (τ 0.6 vs 0.2)\nbut fail on ring strain; uneven"),
 ("MiSI-Bench (2025)", "A fine-tuned 7B vision model beats\nhuman experts on molecular spatial\ntransformations; images help"),
]
for i, (t, b) in enumerate(ev):
    box(ax, 0.03 + i * 0.24, 0.70, 0.22, 0.14, t, b, fs=8.6, bfs=7.0)
ax.text(0.5, 0.665, "Conclusion: geometry understanding is improving but uneven and unverifiable case by case, so it is not trusted for any decision",
        ha="center", fontsize=8, style="italic", color="#444444")

# flow row
y, h = 0.40, 0.16
flow = [
 (0.03, 0.15, "Structure", "coordinates, CIF,\ntrajectory"),
 (0.215, 0.19, "Geometry tools", "spglib symmetry; CatKit/ACAT sites;\npymatgen neighbours; ASE render"),
 (0.44, 0.20, "Descriptor card + image", "site, point group, CN, height,\nbond lengths, tilt, displacement\nfrom start, magnetic moment"),
 (0.675, 0.14, "LLM", "plans, chooses,\ndiagnoses, explains"),
 (0.85, 0.13, "Named tool call", "place(site, orient.)\ndisplace(0.05 Å)"),
]
for x, w, t, b in flow:
    hi = t.startswith("Descriptor")
    box(ax, x, y, w, h, t, b, hi=hi, fs=8.8, bfs=7.2)
for (x, w, *_), (x2, *_) in zip(flow[:-1], flow[1:]):
    arrow(ax, (x + w + 0.002, y + h / 2), (x2 - 0.002, y + h / 2), lw=1.4)

# checks row and feedback
box(ax, 0.215, 0.12, 0.42, 0.13, "Validity checks (code)",
    "desorbed > 3 Å · migrated to another site · dissociated · reconstructed\n· imaginary modes · magnetic moment collapsed · outside expected range", fs=8.8, bfs=7.2)
arrow(ax, (0.915, y - 0.002), (0.915, 0.185), lw=1.4)
arrow(ax, (0.915, 0.185), (0.637, 0.185), lw=1.4)
ax.text(0.78, 0.195, "relax, then check", fontsize=7.5, color="#555555", ha="center")
arrow(ax, (0.213, 0.17), (0.09, y - 0.004), lw=1.2, ls="--", con="arc3,rad=0.35")
ax.text(0.085, 0.255, "verdict as text,\nback into the card", fontsize=7.5, color="#555555", ha="center")

# forbidden path
ax.plot([0.745, 0.745], [y - 0.005, 0.30], color="#b91c1c", lw=1.2, ls=":")
ax.plot([0.745, 0.11], [0.30, 0.30], color="#b91c1c", lw=1.2, ls=":")
ax.text(0.43, 0.31, "✗ never: the LLM writing or editing coordinates directly (Adsorb-Agent style)", fontsize=7.8, color="#b91c1c", ha="center")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "17-geometry-stays-in-code.png"))
