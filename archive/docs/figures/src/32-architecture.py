"""Figure 32: the architecture in one picture, in the manner of Adsorb-Agent's overview: the human at both ends,
the three LLM agents in one box, the skills under them, the tool chain below in board order. All names from
_board.py. Axes in inches."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from _board import STEPS, AGENTS, SKILLS_OURS, SKILLS_REUSED, TOOLS, CHECKPOINTS, BOARD_DATE
from matplotlib.patches import FancyBboxPatch

FW, FH = 16.0, 9.2
fig = plt.figure(figsize=(FW, FH))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, FW); ax.set_ylim(0, FH); ax.axis("off")
fig.text(0.5, 0.972, "The architecture: the human at both ends, three LLM agents that only plan, propose and draft, five skills they follow, nine tools that do every calculation",
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
ax.text(14.35, 6.35, "the five checkpoints where the agent waits:\n" + cps + "\n\nchoice and reason go to the case bank;\nonly a human promotes a case to a skill", ha="center", va="center", fontsize=7.2, zorder=4, linespacing=1.3)

# ---- LLM agents box
rbox(3.35, 5.0, 9.3, 2.9, L_F, L_E, lw=1.6)
ax.text(8.0, 7.65, "LLM agents: plan, propose, draft; never compute, never place atoms", ha="center", va="center", fontsize=9.6, fontweight="bold", color=L_E, zorder=4)
names = ["final-state-planner", "geometry-critic", "dft-settings-interviewer"]
for i, n in enumerate(names):
    x = 3.55 + i * 3.05
    rbox(x, 5.2, 2.85, 2.15, "white", L_E, lw=1.0, z=3)
    ax.text(x + 1.425, 7.15, n, ha="center", va="center", fontsize=8.6, fontweight="bold", color=L_E, zorder=4)
    ax.text(x + 1.425, 6.2, wrap(AGENTS[n], 40), ha="center", va="center", fontsize=7.0, zorder=4, linespacing=1.25)
ax.text(8.0, 5.08, "hooks: no coordinate edits; a pause at every checkpoint", ha="center", va="bottom", fontsize=6.8, color=L_E, style="italic", zorder=4)

# ---- skills strip
rbox(3.35, 3.75, 9.3, 0.95, S_F, S_E)
ax.text(3.55, 4.45, "Skills the agents follow, written by humans:", ha="left", va="center", fontsize=8.2, fontweight="bold", color=S_E, zorder=4)
ax.text(3.55, 4.05, "ours: " + " · ".join(SKILLS_OURS) + "\nreused from AtomisticSkills: " + " · ".join(SKILLS_REUSED), ha="left", va="center", fontsize=7.0, zorder=4, linespacing=1.3)

# ---- tool chain
rbox(0.35, 0.95, 15.3, 2.45, T_F, T_E)
ax.text(0.55, 3.18, "Tools, deterministic code under mcp/tools/, each wrapping one module of finalstate/; the planner calls them by name, in this order:", ha="left", va="center", fontsize=8.2, fontweight="bold", color=T_E, zorder=4)
order = ["dft_settings_lock", "mlip_choice", "site_enumeration", "adsorbate_placement", "dissociation_final_state", "validity_gate", "mlip_doubt", "descriptor_card", "final_state_report"]
serves = {t: sorted({s.key for s in STEPS if t in s.tools}, key=lambda k: [x.key for x in STEPS].index(k)) for t in order}
bw, bg, bx0, by = 1.56, 0.14, 0.55, 1.35
for i, t in enumerate(order):
    x = bx0 + i * (bw + bg)
    rbox(x, by, bw, 1.45, "white", T_E, lw=1.0, z=3, r=0.08)
    ax.text(x + bw / 2, by + 1.2, t, ha="center", va="center", fontsize=6.9, fontweight="bold", family="DejaVu Sans Mono", zorder=4)
    ks = [("the Solution" if k == "solution" else k) for k in serves[t]]
    tag = ks[0] if ks == ["the Solution"] else ("step " if len(ks) == 1 else "steps ") + ", ".join(ks)
    ax.text(x + bw / 2, by + 0.55, tag, ha="center", va="center", fontsize=6.6, color="#555555", zorder=4, linespacing=1.2)
    if i < len(order) - 1: arrow(ax, (x + bw + 0.01, by + 0.72), (x + bw + bg - 0.01, by + 0.72), lw=1.0, ms=8)
ax.text(8.0, 1.08, "extension, only if D2 allows DFT: dft_single_points · every tool returns its structure as a descriptor card and logs every parameter beside its output",
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
