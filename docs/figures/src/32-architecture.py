"""Figure 32: the architecture in one picture, in the manner of Adsorb-Agent's overview: the human at both ends,
the three LLM agents in one box, the skills under them, the tool chain below in board order. All names from
_board.py. Axes in inches."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from _board import STEPS, AGENTS, HPC_ONLY, SKILLS_OURS, SKILLS_REUSED, TOOLS, CHECKPOINTS, BOARD_DATE
from matplotlib.patches import FancyBboxPatch

FW, FH = 16.0, 9.2
fig = plt.figure(figsize=(FW, FH))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis("off")
fig.text(0.5, 0.972, f"The architecture: the human at both ends, {len([n for n in AGENTS if n not in HPC_ONLY])} LLM agents that only plan, propose and draft, the skills they follow, {len(TOOLS) - 2} tools that do every calculation",
         ha="center", va="top", fontsize=12.5, fontweight="bold")
fig.text(0.5, 0.945, f"board of {BOARD_DATE} · arrows are calls and hand-offs · every number the agents report is a tool output · hooks block coordinate edits and pause at the checkpoints",
         ha="center", va="top", fontsize=8.4, color="#555555")
H_E, H_F = LANE["H"][1], LANE["H"][2]; L_E, L_F = LANE["L"][1], LANE["L"][2]
S_E, S_F = LANE["S"][1], LANE["S"][2]; T_E, T_F = LANE["T"][1], LANE["T"][2]

def rbox(x, y, w, h, fc, ec, lw=1.2, ls="-", z=2, r=0.12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={r}", fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))

# ---- human, left: inputs
rbox(0.35, 5.0, 2.6, 2.9, H_F, H_E)
ax.text(1.65, 7.65, "Human, before the run", ha="center", va="center", fontsize=9.4, fontweight="bold", color=H_E, zorder=4)
ax.text(1.65, 6.35, wrap("supplies the relaxed surface, the relaxed adsorbate and the relaxed initial state with their energies, and names the product A* + B*; answers the five interview questions; approves the settings lock and the plan", 34),
        ha="center", va="center", fontsize=7.4, zorder=4, linespacing=1.25)
# ---- human, right: checkpoints and interpretation
rbox(13.05, 5.0, 2.6, 2.9, H_F, H_E)
ax.text(14.35, 7.65, "Human, during and after", ha="center", va="center", fontsize=9.4, fontweight="bold", color=H_E, zorder=4)
cps = "\n".join(f"{PAUSE} {c}" for c in CHECKPOINTS)
ax.text(14.35, 6.35, "the five checkpoints where the agent waits:\n" + cps + "\n\nchoice and reason go to the case bank;\nonly a human promotes a case to a skill;\nwith HPC, " + HPC_ONLY[0] + " retries a failed\nDFT step, capped at three", ha="center", va="center", fontsize=7.0, zorder=4, linespacing=1.3)

# ---- LLM agents box
rbox(3.35, 5.0, 9.3, 2.9, L_F, L_E, lw=1.6)
ax.text(8.0, 7.65, "LLM agents: plan, propose, draft; never compute, never place atoms", ha="center", va="center", fontsize=9.6, fontweight="bold", color=L_E, zorder=4)
names = [n for n in AGENTS if n not in HPC_ONLY]
for i, n in enumerate(names):
    row, col = divmod(i, 4)   # four per row: seven agents fit in two rows
    x = 3.50 + col * 2.30; y0 = 6.35 - row * 1.15
    rbox(x, y0, 2.20, 1.05, "white", L_E, lw=1.0, z=3)
    ax.text(x + 1.10, y0 + 0.86, n, ha="center", va="center", fontsize=8.2, fontweight="bold", color=L_E, zorder=4)
    ax.text(x + 1.10, y0 + 0.40, wrap(AGENTS[n], 40), ha="center", va="center", fontsize=6.0, zorder=4, linespacing=1.15)
ax.text(8.0, 5.08, "hooks: no coordinate edits; a pause at every checkpoint", ha="center", va="bottom", fontsize=6.8, color=L_E, style="italic", zorder=4)

# ---- skills strip
rbox(3.35, 3.75, 9.3, 0.95, S_F, S_E)
ax.text(3.55, 4.45, "Skills the agents follow, written by humans:", ha="left", va="center", fontsize=8.2, fontweight="bold", color=S_E, zorder=4)
ax.text(3.55, 4.05, "ours: " + " · ".join(SKILLS_OURS) + "\nreused from AtomisticSkills: " + " · ".join(SKILLS_REUSED), ha="left", va="center", fontsize=7.0, zorder=4, linespacing=1.3)

# ---- tool chain
rbox(0.35, 0.75, 15.3, 2.65, T_F, T_E)
ax.text(0.55, 3.18, "Tools, deterministic code under src/fragplace/tools/<category>.py, each wrapping one module of fragplace/; the planner calls them by name, in this order:", ha="left", va="center", fontsize=8.2, fontweight="bold", color=T_E, zorder=4)
order = [t for t in TOOLS if t not in ("dft_single_points", "active_learning")]
serves = {t: sorted({s.key for s in STEPS if t in s.tools}, key=lambda k: [x.key for x in STEPS].index(k)) for t in order}
per_row = 9; bg, bx0 = 0.12, 0.55; bw = (15.3 - 0.4 - (per_row - 1) * bg) / per_row
for i, t in enumerate(order):
    row, col = divmod(i, per_row)
    x = bx0 + col * (bw + bg); by = 2.05 - row * 0.95
    rbox(x, by, bw, 0.82, "white", T_E, lw=1.0, z=3, r=0.08)
    ax.text(x + bw / 2, by + 0.56, t, ha="center", va="center", fontsize=6.6, fontweight="bold", family="DejaVu Sans Mono", zorder=4)
    ks = [{"solution": "the Solution", "prompt": "the prompt"}.get(k, k) for k in serves[t]]
    tag = ks[0] if ks in (["the Solution"], ["the prompt"]) else ("step " if len(ks) == 1 else "steps ") + ", ".join(ks)
    ax.text(x + bw / 2, by + 0.24, tag, ha="center", va="center", fontsize=6.2, color="#555555", zorder=4)
    if col < per_row - 1 and i < len(order) - 1: arrow(ax, (x + bw + 0.01, by + 0.41), (x + bw + bg - 0.01, by + 0.41), lw=1.0, ms=8)
    elif i < len(order) - 1: arrow(ax, (x + bw / 2, by - 0.01), (bx0 + bw / 2, by - 0.95 + 0.82 + 0.01), lw=1.0, ms=8, con="arc3,rad=0.0")
ax.text(8.0, 0.82, "extensions: dft_single_points, only if D2 allows DFT; active_learning · every tool returns its structure as a descriptor card and logs every parameter beside its output",
        ha="center", va="bottom", fontsize=6.6, style="italic", color="#555555", zorder=4)

# ---- arrows: hand-offs
arrow(ax, (2.95, 6.9), (3.35, 6.9), color=H_E, lw=1.4, ms=11)
arrow(ax, (12.65, 6.9), (13.05, 6.9), color=L_E, lw=1.4, ms=11)
arrow(ax, (13.05, 6.0), (12.65, 6.0), color=H_E, lw=1.4, ms=11)
arrow(ax, (8.0, 5.0), (8.0, 4.7), color=L_E, lw=1.4, ms=11)
ax.text(8.15, 4.86, "follow", ha="left", va="center", fontsize=6.6, color=L_E)
arrow(ax, (8.0, 3.75), (8.0, 3.4), color=T_E, lw=1.6, ms=12)
ax.text(8.15, 3.58, "call by name; cards come back", ha="left", va="center", fontsize=6.6, color=T_E)
arrow(ax, (2.0, 5.0), (2.0, 3.4), color=H_E, lw=1.2, ms=10, ls="--")
ax.text(2.12, 4.2, "PROJECT.md, the locked settings,\nread by every tool", ha="left", va="center", fontsize=6.4, color=H_E)
ax.text(FW / 2, 0.28, "Reading: the human supplies and decides; the agents route the work through skills to tools; tools compute and come back as descriptor cards; the planner stops at every checkpoint and the human picks. Nothing the agents say is a number they computed.",
        ha="center", va="bottom", fontsize=7.4, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "32-architecture.png"), copy_to="architecture")
