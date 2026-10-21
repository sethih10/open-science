"""Figure 25: where each step runs (laptop, GPU, HPC) and the roster of agents and skills, with why it is short."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

fig = plt.figure(figsize=(14, 8.6))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "HPC is needed for DFT and for nothing else; the roster is five roles and six skills at most, and the evidence says keep it short",
      "left: where each step runs · right: agents and skills, core versus extension versus only with HPC · schematic")

# ---------- left: compute lanes
LX, LW = 0.03, 0.56
lanes = [("Laptop: code", "#f3f4f6", "#6b7280", 0.79,
          ["1 lock: read the protocol", "2 to 4 enumerate, place", "4.1, 6, 9d the gate", "9a, 9b sites and pairs", "10 mapping, pairing", "12 saddle checks", "14 report, trace"]),
         ("GPU: machine-learned potential", HI_FACE, HI_EDGE, 0.60,
          ["5 ML relaxation", "7 committee disagreement", "9c relax each pair", "11 ML band, climbing image", "12 ML frequencies"]),
         ("HPC: DFT", "#fee2e2", "#b91c1c", 0.41,
          ["1 settings sweep on E_ads", "7 calibration labels", "13 DFT single points, relax", "benchmark DFT check", "DFT frequencies, optional"])]
for name, fc, ec, y, chips in lanes:
    ax.add_patch(FancyBboxPatch((LX, y - 0.15), LW, 0.15, boxstyle="round,pad=0.003,rounding_size=0.01", fc=fc, ec=ec, lw=1.2, zorder=1))
    ax.text(LX + 0.01, y - 0.012, name, ha="left", va="top", fontsize=9, fontweight="bold", color=ec, zorder=3)
    cx, cy = LX + 0.012, y - 0.045
    for c in chips:
        w = 0.0062 * len(c) + 0.014
        if cx + w > LX + LW - 0.01:
            cx = LX + 0.012; cy -= 0.042
        ax.add_patch(FancyBboxPatch((cx, cy - 0.028), w, 0.028, boxstyle="round,pad=0.002,rounding_size=0.008", fc="white", ec=ec, lw=0.9, zorder=2))
        ax.text(cx + w / 2, cy - 0.014, c, ha="center", va="center", fontsize=7.2, zorder=3)
        cx += w + 0.008
# hackathon substitute for the HPC lane
ax.add_patch(FancyBboxPatch((LX, 0.115), LW, 0.11, boxstyle="round,pad=0.003,rounding_size=0.01", fc="white", ec="#b91c1c", lw=1.2, ls="--", zorder=1))
ax.text(LX + 0.01, 0.213, "Without HPC in the hackathon: the HPC lane is replaced, not skipped", ha="left", va="top", fontsize=8.6, fontweight="bold", color="#991b1b")
ax.text(LX + 0.01, 0.125, "settings: take OC20's RPBE and PAW values instead of sweeping, since the benchmark is OC20NEB\n"
                           "labels and ground truth: the released OC20NEB DFT bands stand in for steps 7 and 13 and the benchmark check\n"
                           "one DFT check of the propagation experiment: run once beforehand, on any cluster, and recorded",
        ha="left", va="bottom", fontsize=7.2, linespacing=1.3)
ax.text(LX, 0.08, "Cost, from experience and not measured here: an ML relaxation of a small Pt(111) cell takes seconds on one GPU and an ML band minutes;\n"
                   "the same relaxation in DFT takes core-hours and a DFT band many core-hours. Only the red lane needs a queue.",
        ha="left", va="top", fontsize=7.0, style="italic", color="#444444")

# ---------- right: roster
RX = 0.63
ax.text(RX + 0.175, 0.80, "Agents: one sentence each on what it decides", ha="center", va="center", fontsize=9, fontweight="bold")
agents = [("final-state-planner", "the next tool call, and when to stop", "core", HI_FACE, HI_EDGE),
          ("dft-settings-interviewer", "what the Formulate interview locks into PROJECT.md", "core, before the run", HI_FACE, HI_EDGE),
          ("geometry-critic", "whether a card and its verdicts disagree; never overrides", "extension", "#f3e8ff", "#7e22ce"),
          ("dft-job-steward", "resubmit, adjust or escalate a failed DFT job", "only with HPC", "#fee2e2", "#b91c1c"),
          ("general-peer-review", "whether the report would pass peer review", "reused skill, not a new role", "#dcfce7", "#15803d")]
y = 0.765
for n, d, tag, fc, ec in agents:
    ax.add_patch(FancyBboxPatch((RX, y - 0.052), 0.35, 0.052, boxstyle="round,pad=0.003,rounding_size=0.01", fc=fc, ec=ec, lw=1.1, zorder=2))
    ax.text(RX + 0.01, y - 0.014, n, ha="left", va="center", fontsize=8.4, fontweight="bold", zorder=3)
    ax.text(RX + 0.34, y - 0.014, tag, ha="right", va="center", fontsize=6.8, color=ec, style="italic", zorder=3)
    ax.text(RX + 0.01, y - 0.038, d, ha="left", va="center", fontsize=7.2, zorder=3)
    y -= 0.06

ax.text(RX + 0.175, 0.445, "Skills: ours in green, reused from AtomisticSkills in grey", ha="center", va="center", fontsize=9, fontweight="bold")
ours = ["dft-settings-protocol: the settings lock", "mlip-doubt-calibration: doubt versus DFT labels", "dissociation-final-state: 9a to 9e",
        "final-state-report: format, both energies", "hpc-dft-jobs: only with HPC", "neb-saddle-diagnosis: later phase"]
reused = ["ml-committee-uncertainty", "ml-mlip-benchmark", "ml-mace-finetune", "chem-neb-barrier", "chem-thermochemistry", "general-peer-review"]
y = 0.415
for i in range(6):
    ax.add_patch(FancyBboxPatch((RX, y - 0.03), 0.21, 0.03, boxstyle="round,pad=0.002,rounding_size=0.008", fc="#dcfce7", ec="#15803d", lw=0.9, zorder=2))
    ax.text(RX + 0.105, y - 0.015, ours[i], ha="center", va="center", fontsize=6.9, zorder=3)
    ax.add_patch(FancyBboxPatch((RX + 0.218, y - 0.03), 0.132, 0.03, boxstyle="round,pad=0.002,rounding_size=0.008", fc="#f3f4f6", ec="#6b7280", lw=0.9, zorder=2))
    ax.text(RX + 0.284, y - 0.015, reused[i], ha="center", va="center", fontsize=6.9, zorder=3)
    y -= 0.036

ax.add_patch(FancyBboxPatch((RX, 0.05), 0.35, 0.13, boxstyle="round,pad=0.003,rounding_size=0.01", fc="white", ec=EDGE, lw=1.0, zorder=1))
ax.text(RX + 0.175, 0.17, "Why short", ha="center", va="top", fontsize=8.6, fontweight="bold")
ax.text(RX + 0.175, 0.056, "skill selection precision falls from 29.6 % with 5 skills to 3.3 % with 100\n(Demystifying Agent Skills); curated skills gain 16.2 points, self-written\nskills about none (SkillsBench); CatDT runs eight agents and has published\nno result; in the Virtual Lab the human wrote about 1 % of the words and\nset every agenda. Tools do the work; a role is added only when a human\ncan say in one sentence what it decides.",
        ha="center", va="bottom", fontsize=6.9, linespacing=1.28)
finish(fig, os.path.join(os.path.dirname(__file__), "..", "25-compute-and-roster.png"))
