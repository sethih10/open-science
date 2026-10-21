"""Figure 31: who does what, step by step. Four lanes, human, LLM agents, skills, tools; one row per board step;
the box with the thick edge does the work, the others contribute; dashed is an extension."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

LANES = {"H": ("Human", 0.060, 0.185, "#be185d", "#fdf2f8"), "L": ("LLM agents", 0.258, 0.225, "#0e7490", "#ecfeff"),
         "S": ("Skills: written procedures", 0.496, 0.170, "#4d7c0f", "#f7fee7"), "T": ("Tools: deterministic code", 0.679, 0.311, "#374151", "#f3f4f6")}
fig = plt.figure(figsize=(16, 15.5))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "Who does what, step by step: the box with the thick edge does the work, the others feed it; the planner runs the whole column",
      "lanes: human, LLM agents, skills, tools · rows: the board's steps · a pause sign marks a human checkpoint · dashed is an extension · schematic")

TOP, PITCH, H = 0.865, 0.0515, 0.0415
ROWS = 15
# lane backgrounds and headers
for k, (name, x, w, ec, fc) in LANES.items():
    ax.add_patch(FancyBboxPatch((x - 0.008, TOP - ROWS * PITCH - 0.004), w + 0.016, ROWS * PITCH + 0.004 + 0.02,
                                boxstyle="round,pad=0.002,rounding_size=0.01", fc=fc, ec="none", zorder=0))
    ax.text(x + w / 2, TOP + 0.03, name, ha="center", va="center", fontsize=9.6, fontweight="bold", color=ec)
ax.text(LANES["L"][1] + LANES["L"][2] / 2, TOP + 0.012, "final-state-planner throughout: calls each tool by name, reads cards,\nnever writes coordinates, stops at every checkpoint; hooks enforce the last two",
        ha="center", va="center", fontsize=6.6, color="#0e7490", style="italic")

def ytop(i): return TOP - i * PITCH
def cell(lane, i, text, owner=False, ext=False, pause=False):
    name, x, w, ec, fc = LANES[lane]; y = ytop(i) - H
    ax.add_patch(FancyBboxPatch((x, y), w, H, boxstyle="round,pad=0.003,rounding_size=0.01", fc="white", ec=ec,
                                lw=2.2 if owner else 0.9, ls="--" if ext else "-", zorder=2))
    ax.text(x + w / 2, y + H / 2, text, ha="center", va="center", fontsize=6.7, zorder=3, linespacing=1.18, color="#111111" if not ext else "#555555")
    if pause: ax.text(x + w - 0.008, y + H - 0.006, "❚❚", ha="right", va="top", fontsize=6.5, color=ec, fontweight="bold", zorder=4)
def label(i, text):
    ax.text(0.052, ytop(i) - H / 2, text, ha="right", va="center", fontsize=7.4, fontweight="bold", color="#333333")
def link(i, a, b):
    xa = LANES[a][1] + LANES[a][2]; xb = LANES[b][1]
    arrow(ax, (xa + 0.002, ytop(i) - H / 2), (xb - 0.002, ytop(i) - H / 2), lw=1.0, ms=8)

rows = [
 ("Input prompt", {"H": ("supplies the surface, the adsorbates and a description;\nanswers the five interview questions", True, False, False),
                   "L": ("dft-settings-interviewer asks the fixed\nquestions and writes PROJECT.md", False, False, False),
                   "S": ("dft-settings-protocol", False, False, False)}, [("H", "L"), ("L", "S")]),
 ("(1)", {"H": ("approves the settings lock", False, False, True),
          "L": ("planner picks the protocol and states why", False, False, False),
          "S": ("dft-settings-protocol", False, False, False),
          "T": ("dft_settings_lock: the three relaxed inputs, A and B as\nstructures, the cell, the locked settings", True, False, False)}, [("L", "S"), ("S", "T")]),
 ("(1*)", {"L": ("planner records the choice and the reason", False, False, False),
           "S": ("mlip-doubt-calibration: when to doubt", False, False, False),
           "T": ("mlip_choice: CatBench and ml-mlip-benchmark on the\nsystem class; the candidates become the committee", True, False, False)}, [("L", "S"), ("S", "T")]),
 ("(2)", {"T": ("site_enumeration: symmetry-complete sites, fcc and hcp\napart, counted; pymatgen as the baseline", True, False, False)}, []),
 ("(3.1)", {"S": ("dissociation-final-state", False, False, False),
            "T": ("validity_gate: the bond-re-formed check after relaxation,\nthreshold open; a failing pair is never kept", True, False, False)}, [("S", "T")]),
 ("(3.2)", {"T": ("dissociation_final_state: every symmetry-distinct pair in\n[1.5 d, 5] Å, ordered by site-graph distance, counted", True, False, False)}, []),
 ("(3.3)", {"T": ("dissociation_final_state: one force call per pair with the\nchosen potential; a pull towards the other fragment queues last", True, False, False)}, []),
 ("(3.4)", {"L": ("geometry-critic reads the descriptor cards, proposes a\nsite type per fragment, orders the list; never edits\ncoordinates, never overrides a check", True, False, False),
            "T": ("descriptor_card renders every candidate as text:\nsite, distances, verdicts", False, False, False)}, [("L", "T")]),
 ("(3.5 | 3.6)", {"T": ("adsorbate_placement at symmetry-distinct sites, or NEBscape's\nminima hopping with the chosen potential as the alternative", True, False, False)}, []),
 ("(4)", {"T": ("dissociation_final_state: relax every pair with the locked\nsettings, random displacement first", True, False, False)}, []),
 ("(5)", {"L": ("extension: the critic comments on cards,\nnever overrides", False, True, False),
          "T": ("validity_gate: nine checks per fragment, before and after\nrelaxation; verdict into the card; rejections logged", True, False, False)}, []),
 ("(6)", {"T": ("dissociation_final_state: SOAP clustering; the nearest and\nthe lowest per cluster kept; nearest first overall", True, False, False)}, []),
 ("(7)", {"H": ("reviews the flagged cases", False, False, True),
          "L": ("planner stops on doubt and asks;\nextension: agentic uncertainty over N runs", False, False, False),
          "S": ("mlip-doubt-calibration", False, False, False),
          "T": ("mlip_doubt: committee disagreement calibrated on a few\nDFT or OC20NEB labels", True, False, False)}, [("T", "S"), ("S", "L"), ("L", "H")]),
 ("(8)", {"H": ("picks up to five on the cards;\nchoice and reason go to the case bank", True, False, True),
          "L": ("planner shows the cards with rank, doubt and verdicts", False, False, False),
          "T": ("descriptor_card: one card per final state", False, False, False)}, [("T", "L"), ("L", "H")]),
 ("Solution", {"H": ("interprets the report", False, False, False),
               "L": ("planner drafts the report", True, False, False),
               "S": ("final-state-report; general-peer-review, reused", False, False, False),
               "T": ("final_state_report: both energies, rejections, recombination\nrate, decision trace", False, False, False)}, [("T", "S"), ("S", "L"), ("L", "H")]),
]
for i, (lab, cells, links) in enumerate(rows):
    label(i, lab)
    for lane, (text, owner, ext, pause) in cells.items():
        cell(lane, i, text, owner=owner, ext=ext, pause=pause)
    for a, b in links:
        # draw the link only between adjacent lanes that both have a box
        order = ["H", "L", "S", "T"]
        ia, ib = order.index(a), order.index(b)
        lo, hi = sorted((ia, ib))
        for k in range(lo, hi):
            if order[k] in cells and order[k + 1] in cells:
                link(i, order[k], order[k + 1])
# step 3 bracket
y0, y1 = ytop(8) - H, ytop(4)
ax.plot([0.056, 0.056], [y0, y1], color=HI_EDGE, lw=2.4)
ax.text(0.0135, (y0 + y1) / 2, "step 3: the stated problem", rotation=90, ha="center", va="center", fontsize=7.4, color=HI_EDGE, fontweight="bold")
ax.text(0.5, 0.035, "Legend: thick edge, the box that does the work · thin edge, a contribution · dashed, an extension · ❚❚ a human checkpoint where the agent waits · "
                    "arrows, the hand-off within a step. Tool names are the files under mcp/tools/; skill names the folders under skills/; agent names the files under agents/.",
        ha="center", va="bottom", fontsize=7.2, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "31-who-does-what.png"))
