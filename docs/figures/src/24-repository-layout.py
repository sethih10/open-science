"""Figure 24: how the repository is laid out so that a human and an agent can each read it in order.
Left: the tree, one colour per kind. Right: who reads what, and the one-way call rule."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

KIND = {"docs":    dict(fc="#f3f4f6", ec="#6b7280"), "skill": dict(fc="#dcfce7", ec="#15803d"),
        "agent":   dict(fc="#f3e8ff", ec="#7e22ce"), "tool":  dict(fc=HI_FACE,   ec=HI_EDGE),
        "lib":     dict(fc="white",   ec=EDGE),      "data":  dict(fc="#fef3c7", ec="#b45309"),
        "test":    dict(fc="white",   ec="#be185d"), "root":  dict(fc="white",   ec="#374151")}
fig = plt.figure(figsize=(14, 9.6))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "Repository layout: one folder per kind, one file per tool, and a one-way rule: agents call skills, skills call tools, tools call the library",
      "left: the tree, coloured by kind · right: who reads what, in order · a Claude Code plugin beside AtomisticSkills · schematic")

# legend
leg = [("root", "root files"), ("docs", "documents"), ("skill", "skills: procedures"), ("agent", "agents: roles"),
       ("tool", "MCP tools"), ("lib", "library: the logic"), ("data", "runs and data"), ("test", "tests")]
for j, (k, lab) in enumerate(leg):
    x = 0.03 + j * 0.116
    ax.add_patch(FancyBboxPatch((x, 0.868), 0.016, 0.012, boxstyle="round,pad=0.002,rounding_size=0.004", lw=1.1, zorder=2, **KIND[k]))
    ax.text(x + 0.021, 0.874, lab, ha="left", va="center", fontsize=7.8)

# ---- left: the tree
tree = [
 (0, "root", "open-science-hackathon/", "the repository is a Claude Code plugin"),
 (1, "root", "README.md", "one page: what it is, install, run the first case"),
 (1, "root", "CLAUDE.md", "agent instructions: reading order, rules, where things are"),
 (1, "root", "PROJECT.md", "locked settings and decisions of the current campaign"),
 (1, "root", "pyproject.toml", "one package: the library, the server, the tests"),
 (1, "docs", "docs/", "design doc, agent context, build context, survey, figures"),
 (1, "root", ".claude-plugin/plugin.json", "declares skills, agents, hooks and the MCP server"),
 (1, "skill", "skills/", "few, human-written, one folder each"),
 (2, "skill", "dft-settings-protocol · mlip-doubt-calibration", "the settings lock · doubt against DFT labels"),
 (2, "skill", "dissociation-final-state · final-state-report · hpc-dft-jobs", "9a to 9e · the report · only with HPC"),
 (1, "agent", "agents/", "one markdown file per role, one page each"),
 (2, "agent", "final-state-planner.md · dft-settings-interviewer.md", "next tool call, when to stop · the interview, once"),
 (2, "agent", "geometry-critic.md · dft-job-steward.md", "extension: card versus verdicts · only with HPC"),
 (1, "root", "hooks/hooks.json", "blocks coordinate edits; pauses at human checkpoints"),
 (1, "tool", "mcp/", "one server, typed tools, one file per tool"),
 (2, "tool", "server.py", "registers the tools below"),
 (2, "tool", "tools/dft_settings_lock.py · site_enumeration.py", "T1 · T2"),
 (2, "tool", "tools/adsorbate_placement.py · validity_gate.py · descriptor_card.py", "T3 · T4 · T5"),
 (2, "tool", "tools/mlip_choice.py · mlip_doubt.py · dissociation_final_state.py", "T6 · T7 · P1, 9a to 9e"),
 (2, "tool", "tools/dft_single_points.py · final_state_report.py", "P5 · 14; later: endpoint_pairing, neb_band, saddle_validation"),
 (1, "lib", "finalstate/", "pure Python, no LLM, no MCP: the logic the tools wrap"),
 (2, "lib", "site_enumeration.py · validity_gate.py · ...", "one module per tool, same name as the tool"),
 (1, "test", "tests/", "one test file per tool; Burnside on C4v; the gate on known failures"),
 (1, "data", "benchmark/", "OC20NEB subset, baselines, scoring, results"),
 (1, "data", "runs/<campaign>/", "PROJECT.md copy, trace.jsonl, cards/, structures/, report.md"),
 (1, "data", "lessons.md", "the lessons log; recurring entries become skill lines"),
]
y = 0.835; dy = 0.0292
for depth, kind, name, note in tree:
    x = 0.03 + depth * 0.028
    w = 0.30 - depth * 0.028
    ax.add_patch(FancyBboxPatch((x, y - 0.022), w, 0.022, boxstyle="round,pad=0.002,rounding_size=0.006", lw=1.0, zorder=2, **KIND[kind]))
    ax.text(x + 0.008, y - 0.011, name, ha="left", va="center", fontsize=7.4, family="DejaVu Sans Mono", zorder=3)
    ax.text(0.345, y - 0.011, note, ha="left", va="center", fontsize=7.2, color="#444444", zorder=3)
    if depth > 0:
        ax.plot([x - 0.014, x - 0.014, x - 0.002], [y - 0.0, y - 0.011, y - 0.011], color="#9a9a9a", lw=0.8, zorder=1)
    y -= dy

# ---- right: who reads what
X0 = 0.655
ax.text(X0 + 0.165, 0.84, "Who reads what, in order", ha="center", va="center", fontsize=9.4, fontweight="bold")
def col(x, head, items, kind):
    ax.add_patch(FancyBboxPatch((x, 0.50), 0.155, 0.31, boxstyle="round,pad=0.003,rounding_size=0.01", fc="white", ec=EDGE, lw=1.0, zorder=1))
    ax.text(x + 0.0775, 0.80, head, ha="center", va="top", fontsize=8.6, fontweight="bold", zorder=3)
    yy = 0.765
    for it, k in items:
        ax.add_patch(FancyBboxPatch((x + 0.012, yy - 0.03), 0.131, 0.03, boxstyle="round,pad=0.002,rounding_size=0.006", lw=1.0, zorder=2, **KIND[k]))
        ax.text(x + 0.0775, yy - 0.015, it, ha="center", va="center", fontsize=7.0, zorder=3)
        yy -= 0.043
        if yy > 0.52: arrow(ax, (x + 0.0775, yy + 0.013), (x + 0.0775, yy + 0.002), lw=1.0, ms=7)
col(X0, "A human", [("README.md", "root"), ("docs/ design document", "docs"), ("PROJECT.md", "root"), ("runs/<campaign>/report.md", "data"), ("lessons.md", "data")], "root")
col(X0 + 0.175, "An agent", [("CLAUDE.md", "root"), ("docs/agent-context.md", "docs"), ("docs/agent-build-context.md", "docs"), ("skills/*/SKILL.md", "skill"), ("mcp tool docstrings", "tool")], "root")

# ---- right bottom: the one-way call rule
ax.text(X0 + 0.165, 0.455, "The one-way rule: calls go down, never up or sideways", ha="center", va="center", fontsize=9.4, fontweight="bold")
chain = [("agents/", "agent", "decide what to do next; no logic"), ("skills/", "skill", "say how, step by step; no logic"),
         ("mcp/tools/", "tool", "typed entry points; no logic"), ("finalstate/", "lib", "all the logic; tested"), ("runs/", "data", "every call and verdict logged")]
yy = 0.415
for name, k, note in chain:
    ax.add_patch(FancyBboxPatch((X0 + 0.02, yy - 0.05), 0.13, 0.05, boxstyle="round,pad=0.003,rounding_size=0.01", lw=1.2, zorder=2, **KIND[k]))
    ax.text(X0 + 0.085, yy - 0.025, name, ha="center", va="center", fontsize=8.2, fontweight="bold", family="DejaVu Sans Mono", zorder=3)
    ax.text(X0 + 0.165, yy - 0.025, note, ha="left", va="center", fontsize=7.4, color="#444444", zorder=3)
    if name != "runs/": arrow(ax, (X0 + 0.085, yy - 0.052), (X0 + 0.085, yy - 0.071), lw=1.2, ms=9)
    yy -= 0.073
ax.text(X0 + 0.165, 0.035, "tests/ sits beside finalstate/ and never beside an agent: if a check\nis wrong, the test fails, not the conversation", ha="center", va="bottom",
        fontsize=7.2, style="italic", color="#444444")
ax.text(0.03, 0.02, "Readability rules: every file has one kind; a skill is under 200 lines and names tools, never code; an agent file is one page; "
                    "a tool is one file that wraps one library module of the same name.", ha="left", va="bottom", fontsize=7.2, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "24-repository-layout.png"))
