"""Figure 29: how the plan evolved, one row per step of the team's board in the board's own order and
numbering: what the board says, what the literature refined, what we added or decided, what is open."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

KIND = {"board": dict(fc="white",   ec="#374151", lw=1.1, ls="-"),
        "lit":   dict(fc="#dcfce7", ec="#15803d", lw=1.1, ls="-"),
        "ours":  dict(fc=HI_FACE,   ec=HI_EDGE,   lw=1.4, ls="-"),
        "open":  dict(fc="#fef3c7", ec="#b45309", lw=1.1, ls="-"),
        "ext":   dict(fc="#f3e8ff", ec="#7e22ce", lw=1.2, ls="--")}
TITLE_COL = {"board": "#111827", "lit": "#14532d", "ours": "#1e3a8a", "open": "#92400e", "ext": "#581c87"}
OWNER_COL = {"TOOL": "#374151", "LLM": "#0e7490", "HUMAN": "#be185d", "SKILL": "#4d7c0f"}

fig = plt.figure(figsize=(17, 21))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "How the plan evolved: one row per step of the board, in the board's order; what the board says, what the literature refined, what we added",
      "board of 21 October 2026, numbering kept, including the six points of step 3 · owner line under each step · amber is open, dashed purple is an extension · schematic")

leg = [("board", "as written on the board"), ("lit", "refined by the literature, with the source"), ("ours", "what we added or decided"),
       ("open", "open: team decision"), ("ext", "extension layer, later")]
for j, (k, lab) in enumerate(leg):
    x = 0.04 + j * 0.19
    ax.add_patch(FancyBboxPatch((x, 0.8905), 0.018, 0.011, boxstyle="round,pad=0.002,rounding_size=0.004", zorder=2, **KIND[k]))
    ax.text(x + 0.023, 0.896, lab, ha="left", va="center", fontsize=8.2)
ax.text(0.04, 0.877, "Owner line:", ha="left", va="center", fontsize=7.6, color="#333333")
xo = 0.10
for t, d in [("TOOL", "deterministic code"), ("LLM", "reads cards, proposes, drafts"), ("HUMAN", "decides, picks, interprets"), ("SKILL", "a written procedure the LLM follows")]:
    ax.text(xo, 0.877, t, ha="left", va="center", fontsize=7.6, fontweight="bold", color=OWNER_COL[t])
    ax.text(xo + 0.0056 * len(t) + 0.006, 0.877, d, ha="left", va="center", fontsize=7.6, color="#333333")
    xo += 0.0056 * len(t) + 0.0046 * len(d) + 0.032

COL = {"board": (0.040, 0.215), "lit": (0.267, 0.245), "ours": (0.524, 0.235), "open": (0.771, 0.222)}
HEAD = {"board": "On the board", "lit": "Refined by the literature", "ours": "What we added or decided", "open": "Open, or an extension"}
for k, (x0, w) in COL.items():
    ax.text(x0 + w / 2, 0.860, HEAD[k], ha="center", va="center", fontsize=8.8, fontweight="bold", color="#333333")
ax.plot([0.04, 0.993], [0.849, 0.849], color=EDGE, lw=0.8)

TOP, PITCH, H = 0.843, 0.0495, 0.0435
def ytop(i): return TOP - i * PITCH
def cell(kind, col, i, head, body, hfs=7.6, bfs=6.9, owner=None):
    x0, w = COL[col]; y = ytop(i) - H
    ax.add_patch(FancyBboxPatch((x0, y), w, H, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND[kind]))
    ax.text(x0 + w / 2, y + H - 0.004, head, ha="center", va="top", fontsize=hfs, fontweight="bold", color=TITLE_COL[kind], zorder=3)
    if owner:
        parts = owner.split(" · "); total = sum(len(t) for t in parts) + 3 * (len(parts) - 1); cw = 0.0032
        xs = x0 + w / 2 - total * cw / 2
        for t in parts:
            ax.text(xs, y + H - 0.0135, t, ha="left", va="top", fontsize=6.2, fontweight="bold", color=OWNER_COL[t], zorder=3); xs += (len(t) + 3) * cw
        ax.text(x0 + w / 2, y + (H - 0.024) / 2, body, ha="center", va="center", fontsize=bfs, zorder=3, linespacing=1.16)
    else:
        ax.text(x0 + w / 2, y + (H - 0.012) / 2, body, ha="center", va="center", fontsize=bfs, zorder=3, linespacing=1.18)
def none(col, i):
    x0, w = COL[col]; ax.text(x0 + w / 2, ytop(i) - H / 2, "none", ha="center", va="center", fontsize=7.0, color="#888888", style="italic")

rows = [
 ("(1) Structure retriever", "TOOL · HUMAN", "fed by the input prompt: surf + adsorbates (2)\nand a general system description;\nsurface and adsorbate with their energies",
  ("AiiDA common workflows · SSSP · OC20", "numerical settings come from a verified\nprotocol, never from the model; OC20's RPBE\nand PAW if the benchmark is OC20NEB"),
  "the three relaxed inputs plus A and B as\nstructures; settings locked in PROJECT.md;\na cell wide enough for the pair",
  ("open", "Open", "one set of gas references for AB, A and B")),
 ("(1*) MLIP selection, AL prospect", "TOOL · LLM · SKILL", "chosen before placement so step 3 can\nuse it; active learning as a prospect",
  ("80-MLIP survey · CatBench · AtomisticSkills", "no potential is best everywhere; CatBench\nclasses each failure; ml-mlip-benchmark\nscores candidates on the system class"),
  "benchmark two or three, record why; spin for\nNi and Co; the candidates become the\ncommittee of step 7",
  ("ext", "EXTENSION", "active learning: doubt → a few DFT\nlabels → fine-tune → re-run")),
 ("(2) Adsorption sites with pymatgen", "TOOL", "Python, with pymatgen",
  ("pymatgen · ACAT · spglib", "pymatgen's site finder labels no fcc or hcp\nhollow; ACAT gives labelled sites and the site\ngraph; spglib the symmetry operations"),
  "symmetry-complete and counted; fcc and hcp\napart; pymatgen kept as the baseline", None),
 ("(3.1) least distance before pull-back", "TOOL", "estimate the minimum distance at which the\ndissociated atom is not pulled back",
  ("CatTSunami · NEBscape", "CatTSunami treats a bond as breaking at 1.25\nto 1.63× its length; NEBscape keeps fragments\nintact by Hookean constraint during sampling"),
  "the bond-re-formed check as code, after\nrelaxation, with a logged reason; a pair that\nfails is never kept",
  ("open", "Open", "the A–B distance threshold")),
 ("(3.2) window [1.5 d, 5] Å", "TOOL", "d the max vdW length of the bond to\nbreak, from the literature",
  ("NEBscape · CatTSunami", "NEBscape excludes separations above 4.5 Å;\nCatTSunami samples a 1 to 3 Å shell,\n25 pairs, one survivor at random"),
  "every symmetry-distinct pair inside the window,\nordered by site-graph distance, nearest first,\ncounted: the objective is explicit",
  ("open", "Open", "d from vacuum or from the adsorbed\nmolecule; 5 Å or NEBscape's 4.5 Å")),
 ("(3.3) pull force with the MLIP", "TOOL", "use the selected MLIP to estimate the pull\nforce on the binding fragment",
  ("NEBscape · CatTSunami", "neither screens by force; both relax every\ncandidate they generate"),
  "one force call per pair before relaxing; a pull\ntowards the other fragment queues the pair\nlast, never drops it",
  ("open", "Open", "the force threshold")),
 ("(3.4) agentic critique of the cleavage", "LLM", "criticise and adjust the placement from\nknowledge of what the cleavage does",
  ("AdsMind · AtomWorld · ChemCrow", "AdsMind: the LLM returns a site type, code\nplaces, 98.8 %; AtomWorld: LLM coordinate edits\nfail; an LLM judge rates fluent wrong answers well"),
  "geometry-critic reads descriptor cards, proposes\na site type per fragment, orders the list; never\nedits coordinates, never overrides a check",
  ("ext", "EXTENSION", "a vision model to predict the sites,\nonly after the geometry benchmark\nshows an image helps")),
 ("(3.5) site and orientation, pymatgen", "TOOL", "agentic knowledge or a package such as\npymatgen, so the binding fragment adsorbs",
  ("El Agente Potente · CatTSunami", "symmetry-distinct sites and orientations\nenumerated by code; CatTSunami: 5 placements\nwithin 2 Å of the old binding site"),
  "code places, the LLM never does: the fragment\nkeeping the binding atom at symmetry-distinct\nsites near its old site, counted",
  ("open", "Open", "the binding fragment fixed at its\nold site, or enumerated")),
 ("(3.6) or minima hopping with the MLIP", "TOOL", "alternatively, minima hopping with the\nselected MLIP for the binding fragment",
  ("NEBscape", "minima hopping from symmetry-inequivalent\nsites with Hookean constraints; 94 % of 304\nOC20NEB reactions converge; MIT code"),
  "kept as the alternative generator, wrapped, and\nas the baseline policy our nearest-first choice\nis scored against", None),
 ("(4) Initial configurations", "TOOL", "output of step 3: all degrees of freedom\nof the adsorbate × all sites",
  ("Burnside · symmetry trap", "the count checked by Burnside's lemma; a small\nrandom displacement before relaxing, or a\nsymmetric start relaxes to a saddle"),
  "every candidate pair relaxed with the chosen\npotential and the locked settings,\ndisplacement first",
  ("open", "Open", "the displacement amplitude")),
 ("(5) Physics-based and anomaly filtering", "TOOL", "physics by script; anomaly by ML and/or\nscript; reasoning questions injected",
  ("AdsorbML in fairchem", "four anomaly checks exist; the desorbed check\ntreats A* + B* as one adsorbate and misses B\nleaving while A stays"),
  "nine checks as code, per fragment, before and\nafter relaxation; the ML variant not taken; every\nrejection logged with its reason",
  ("ext", "EXTENSION", "an LLM critic reads the card and\ncomments; it never overrides a check")),
 ("(6) SOAP clustering", "TOOL", "pick the 3 lowest-energy configurations\nfrom each cluster, could be more",
  ("NEBscape", "deduplicates by SOAP and keeps the first two\nenergy–distance Pareto fronts within 1.2 eV"),
  "cluster the survivors; keep the nearest and the\nlowest per cluster; nearest first overall",
  ("open", "Open", "how many per cluster")),
 ("(7) Uncertainty estimation", "TOOL · SKILL", "with all relevant models from 1*; agentic\nuncertainty and DFT as question marks",
  ("MACE committees · uncertainty-toolbox", "committee variance is cheap; calibration\nmetrics exist; El Agente Potente saw two MLIPs\ndisagree in sign on a reaction energy"),
  "disagreement calibrated on a few DFT or\nOC20NEB labels; doubt escalates to the human\ninstead of guessing",
  ("ext", "EXTENSION", "agentic uncertainty: N planner runs;\nDFT single points if D2 allows DFT")),
 ("(8) Rank; user chooses up to 5", "HUMAN · LLM", "optional: uncertainty estimates and potential\nissues; critic and knowledge prompts",
  ("AdsorbML · CatDT", "top-k then DFT is AdsorbML's recipe; CatDT:\na raw case bank scores 68 % against 52 to 54 %\nfor distilled lessons"),
  "descriptor cards with rank, doubt and verdicts;\nthe choice and reason go to the case bank;\nonly a human promotes a case to a skill",
  ("open", "Open", "up to five, or fewer")),
 ("Solution", "TOOL · HUMAN", "final output",
  ("OC20NEB · AtomisticSkills", "OC20NEB product frames as the comparison;\nevery parameter logged beside its output;\ngeneral-peer-review reads the report"),
  "the nearest non-recombining final state with\nE(FS near), E(FS ∞), rejections, recombination\nrate, trace; two numbers and two comparisons",
  ("open", "Open", "the pass criterion against the\nOC20NEB product frame")),
]
for i, (bh, own, bb, (lh, lb), ours, extra) in enumerate(rows):
    cell("board", "board", i, bh, bb, hfs=7.7, bfs=6.7, owner=own)
    cell("lit", "lit", i, lh, lb)
    cell("ours", "ours", i, "Ours", ours)
    if extra: cell(extra[0], "open", i, extra[1], extra[2], hfs=7.2, bfs=6.8)
    else: none("open", i)
sx = COL["board"][0] + COL["board"][1] / 2
for i in range(len(rows) - 1):
    arrow(ax, (sx, ytop(i) - H - 0.0008), (sx, ytop(i + 1) + 0.0008), lw=1.3, ms=8)
x0, w = COL["board"]
ax.add_patch(FancyBboxPatch((x0 - 0.006, ytop(8) - H - 0.004), w + 0.012, ytop(3) - (ytop(8) - H) + 0.008,
                            boxstyle="round,pad=0.002,rounding_size=0.01", fc="none", ec=HI_EDGE, lw=1.6, ls="--", zorder=1))
ax.text(x0 - 0.012, (ytop(3) + ytop(8) - H) / 2, "step 3: adsorbate placement, the stated problem", rotation=90, ha="center", va="center", fontsize=7.4, color=HI_EDGE, fontweight="bold")
ax.text(0.04, 0.062, "The board's own open questions: step 3 applies to dissociative adsorption only, by the fixed scope; the models of step 7 are the candidates benchmarked at 1*; "
                     "\"phys. int.\" at step 8 is read as the physical issues shown on each card; the vision model feeds step 3 and is an extension.\n"
                     "Rows 3.1 to 3.6 keep the board's order 1 → 2 → 3 → 4 → 5 or 6; in code 3.5 runs first, then 3.2, 3.3, 3.1 inside step 5, 3.4 beside 3.5, 3.6 as the alternative.",
        ha="left", va="bottom", fontsize=7.2, style="italic", color="#444444", linespacing=1.3)
finish(fig, os.path.join(os.path.dirname(__file__), "..", "29-board-evolution.png"))
