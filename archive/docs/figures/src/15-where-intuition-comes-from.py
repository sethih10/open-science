"""Figure 15: sources of expert knowledge -> kinds of intuition -> the channel that enforces each."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *

fig = plt.figure(figsize=(11, 7.2))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "Scientific intuition is written down in more places than it seems; the rest we elicit and log",
      "Sources on the left feed four kinds of intuition, each enforced through the channel on the right · schematic")

heads = [(0.03, "Where it is written (sources)"), (0.385, "What kind of intuition it is"), (0.70, "Channel that enforces it")]
for x, t in heads:
    ax.text(x + 0.15 if x < 0.1 else x + 0.13, 0.875, t, fontsize=9.5, fontweight="bold", ha="center")

src = [
 ("Textbooks and reviews", "Sholl & Steckel; Nørskov et al.; functional and\nreference-state guidance"),
 ("Protocol libraries", "SSSP, AiiDA common workflows (fast/moderate/\nprecise), Materials Project input sets"),
 ("Published inputs and datasets", "OC20 settings (RPBE, PAW, 350 eV); NOMAD;\nMaterials Cloud; Catalysis-Hub"),
 ("Benchmarks", "CE27, Δ-test, CatBench, MLIP surveys:\nexpected errors and known failures"),
 ("Forums and group lore", "VASP wiki and forum, QE mailing list,\nlab wikis: 'set MAGMOM on Ni'"),
 ("Experienced researcher", "Formulate interview before the run;\nreview of flagged cases after it", True),
 ("Our own runs", "Lessons log: every correction a reviewer\nmakes, with the reason"),
]
y0, dh, w, h = 0.755, 0.104, 0.30, 0.088
for i, s in enumerate(src):
    t, b = s[0], s[1]; hi = len(s) > 2
    box(ax, 0.03, y0 - i * dh, w, h, t, b, hi=hi, fs=8.6, bfs=7.2)

kinds = [
 ("Procedures", "Break symmetry before relaxing;\nconverge E_ads not E_total;\nsame settings on both sides"),
 ("Priors and expected ranges", "H on Pt(111) ≈ −0.5 eV; CO prefers\ntop on Pt despite GGA; MLIPs fail on\nmagnetic Ni and Co"),
 ("Sanity constraints", "Adsorbate within 3 Å of surface;\nno imaginary modes at a minimum;\nmagnetic moment not collapsed"),
 ("Judgement of when to stop", "Disagreement between two MLIPs;\nunseen chemistry; result outside\nthe expected range → ask a human"),
]
ky0, kdh, kh = 0.70, 0.17, 0.14
for i, (t, b) in enumerate(kinds):
    box(ax, 0.385, ky0 - i * kdh, 0.26, kh, t, b, fs=8.8, bfs=7.3)

chan = [
 ("Skill (SKILL.md)", "procedures, pitfalls"),
 ("Tools (code)", "constraints as tests, convergence sweeps"),
 ("Project memory (PROJECT.md)", "choices locked for this system"),
 ("Checkpoint", "settings approval, flagged-case review"),
 ("Lessons log → skill", "corrections fed back"),
]
cy0, cdh, ch = 0.735, 0.128, 0.09
for i, (t, b) in enumerate(chan):
    box(ax, 0.70, cy0 - i * cdh, 0.27, ch, t, b, fs=8.8, bfs=7.4)

# bundle arrows between columns
for yy in (0.33, 0.52, 0.72):
    arrow(ax, (0.335, yy), (0.383, yy), lw=1.4)
    arrow(ax, (0.648, yy), (0.698, yy), lw=1.4)
# feedback loop: checkpoint -> lessons log -> skill (dashed, returns to sources column bottom)
arrow(ax, (0.835, 0.223), (0.33, 0.175), lw=1.1, ls="--", con="arc3,rad=0.28")
ax.text(0.52, 0.10, "corrections from review become lines in the lessons log, then in the skill (dashed)", fontsize=7.5, color="#555555", ha="center")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "15-where-intuition-comes-from.png"))
