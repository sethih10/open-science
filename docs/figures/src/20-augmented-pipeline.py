"""Figure 20: the current pipeline, step by step, with what to borrow from the transition-state
literature, what is missing or already exists, what is ours, and the extension layer at its step.
One colour per kind of idea; the legend at the top is the key."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

# ---- colour schema: one colour per kind of idea
KIND = {"step":    dict(fc="white",   ec=EDGE,      lw=1.0, ls="-"),
        "borrow":  dict(fc="#dcfce7", ec="#15803d", lw=1.1, ls="-"),
        "missing": dict(fc="#fef3c7", ec="#b45309", lw=1.1, ls="-"),
        "exists":  dict(fc="#fee2e2", ec="#b91c1c", lw=1.1, ls="-"),
        "ours":    dict(fc=HI_FACE,   ec=HI_EDGE,   lw=1.4, ls="-"),
        "ext":     dict(fc="#f3e8ff", ec="#7e22ce", lw=1.2, ls="--")}
TITLE_COL = {"step": TEXT, "borrow": "#14532d", "missing": "#92400e", "exists": "#991b1b",
             "ours": "#1e3a8a", "ext": "#581c87"}

fig = plt.figure(figsize=(17, 18.5))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "Augmented pipeline: what to borrow from the transition-state papers, what is missing, "
           "what is ours, and where the extension layer attaches",
      "Read each row left to right: the step, the refinement with its paper, the gap, our claim, the extension · schematic")

# ---- columns (x0, width)
COL = {"step": (0.040, 0.153), "borrow": (0.205, 0.225), "gap": (0.442, 0.210),
       "ours": (0.664, 0.160), "ext": (0.836, 0.154)}
HEAD = {"step": "Current pipeline\n(board + path steps)", "borrow": "Refinement to borrow, with the paper",
        "gap": "Gap: missing (amber) or already exists (red)", "ours": "What makes it ours",
        "ext": "Extension layer: dashed,\nattached at its step"}

# ---- legend
leg = [("step", "current pipeline step"), ("borrow", "refinement from a paper"), ("missing", "missing: must add"),
       ("exists", "already exists elsewhere: not unique"), ("ours", "what makes it ours"), ("ext", "extension layer, later")]
for j, (k, lab) in enumerate(leg):
    x = 0.04 + j * 0.158
    p = FancyBboxPatch((x, 0.9005), 0.018, 0.011, boxstyle="round,pad=0.002,rounding_size=0.004", zorder=2, **KIND[k])
    ax.add_patch(p)
    ax.text(x + 0.023, 0.906, lab, ha="left", va="center", fontsize=8.2)

# ---- column headers
for k, (x0, w) in COL.items():
    ax.text(x0 + w / 2, 0.880, HEAD[k], ha="center", va="center", fontsize=8.6, fontweight="bold", color="#333333")
ax.plot([0.04, 0.993], [0.866, 0.866], color=EDGE, lw=0.8)

# ---- rows
TOP, PITCH, H = 0.858, 0.043, 0.0352
def ytop(i): return TOP - i * PITCH

def cell(kind, col, i, head, body, hfs=7.7, bfs=7.0):
    x0, w = COL[col]; y = ytop(i) - H
    p = FancyBboxPatch((x0, y), w, H, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND[kind])
    ax.add_patch(p)
    ax.text(x0 + w / 2, y + H - 0.004, head, ha="center", va="top", fontsize=hfs, fontweight="bold",
            color=TITLE_COL[kind], zorder=3)
    ax.text(x0 + w / 2, y + (H - 0.012) / 2, body, ha="center", va="center", fontsize=bfs, zorder=3, linespacing=1.18)

def step(i, head, body):
    cell("step", "step", i, head, body, hfs=8.8, bfs=7.2)

def none(col, i, text):
    x0, w = COL[col]
    ax.text(x0 + w / 2, ytop(i) - H / 2, text, ha="center", va="center", fontsize=7.0, color="#888888", style="italic")

rows = [
 # (step title, step body, borrow (head, body), gap (kind, head, body), ours body or None, ext (head, body) or None)
 ("(1) Structure retriever", "surface, adsorbates and the product\nfrom the prompt; settings locked in PROJECT.md",
  ("AiiDA common workflows · SSSP", "cutoff, k-mesh and pseudopotentials from a verified\nprotocol or a sweep on E_ads, never from the LLM's\nmemory (AutoDFT rejected); Δ-test checked sets"),
  ("missing", "Missing", "the product given as a structure, not a name;\ngas-phase references for reactants and product\non one footing: ½ E(H₂), corrected O₂, CO₂"),
  "one locked, converged settings file;\nevery later number traceable to it", None),
 ("(2) Adsorption sites", "sites on the clean slab (pymatgen)",
  ("CatKit · AdsorbML", "CatKit: symmetry-reduced site graphs;\nAdsorbML: heuristic plus random sites\n(OC20-Dense) when symmetry is not used"),
  ("exists", "Not unique", "pymatgen's site finder is already in\nAdsorb-Agent, AdsMind and AtomisticSkills"),
  "symmetry-complete and counted (Burnside);\nfcc and hcp hollows apart; the count\nis reported and checked", None),
 ("(3) Adsorbate placement", "script only; symmetry plus random displacement",
  ("TSBench · AtomWorld", "LLM coordinate edits fail (rotations under 12 %;\nmost TSBench failures are wrong structures),\nso placement stays a script, as in CatTSunami"),
  ("exists", "Not unique, and one competitor", "scripted placement is standard; CopyCAT (ICIQ)\nbets the other way, LLM reasoning to 3D,\nwith no accuracy against DFT reported"),
  "the LLM never touches coordinates; it reads\na descriptor card and calls named tools\n(figure 17)", None),
 ("(4) Initial configurations", "all adsorbate degrees of freedom × all sites",
  ("AdsorbML · CatTSunami", "many configurations per system, heuristic plus\nrandom, then ML relaxation; CatTSunami enumerates\nreactant states the same way before pairing"),
  ("missing", "Missing", "co-adsorbed pairs A* + B* when the product forms\nfrom two adsorbates: lateral interactions and\ncoverage; conformers generated in vacuum first"),
  "pair enumeration by symmetry with the\ncount; few conformers kept", None),
 ("(4.1) Physics-based filtering", "drop unphysical configurations before relaxing",
  ("AdsorbML anomaly checks", "desorbed, dissociated, intercalated, surface\nreconstructed; CatTSunami applies connectivity\nand anomaly checks to its frames"),
  ("exists", "Not unique, one check short", "the four AdsorbML checks exist since 2022;\nthey lack the imaginary-mode check that\ncatches the symmetry trap"),
  "one gate, in code, applied to both endpoints\nbefore any path is run: barrier-ready",
  ("EXTENSION · attaches to 4.1 and 6", "an LLM critic reads the descriptor card\nand comments; it never overrides a\ncode check")),
 ("(5) MLIP selection", "which universal potential",
  ("CatTSunami · fine-tuned MLIP TS · CatDT", "EquiformerV2 on OC20 for ML NEB; fine-tuning with\nfewer than 10 DFT points; UMA or CHGNet;\nAtomisticSkills ml-mlip-benchmark to choose"),
  ("missing", "Missing", "a decision rule by system class: metal, oxide,\norganometallic; spin and dispersion settings;\norganometallics lie outside OC20 training"),
  "benchmark, choose, record why; flag doubt\nwhere the 80-MLIP survey says no potential\nis best",
  ("EXTENSION · attaches to 5", "active-learning loop: high uncertainty\n→ a few DFT labels → fine-tune\n(ml-mace-finetune) → re-run 6 to 8")),
 ("(6) Anomaly filter", "the same checks after relaxation",
  ("AdsorbML", "the same checks run on every relaxed structure;\nAdsorbML discards anomalies before ranking"),
  ("exists", "Not unique", "same code as 4.1; nothing new here"),
  "verdict written into the descriptor card\nso the LLM and the human both see it", None),
 ("(7) Uncertainty estimation", "disagreement across the MLIPs from (5)",
  ("80-MLIP survey (Kempen, Cheula, Andersen)", "no potential is best everywhere, so an ensemble\nof different models is the cheap uncertainty;\nAdsorbML and CatTSunami report none"),
  ("missing", "Missing", "calibration: disagreement against DFT error on\na few labels; uncalibrated, the flag is noise"),
  "calibrated ML doubt that escalates to review\ninstead of guessing (the Ni(111) demo)",
  ("EXTENSION · attaches to 7 and 8", "agentic uncertainty: run the planner\nN times on the same input; report how\noften its choices differ")),
 ("(8) Rank; human picks ≤ 5", "with uncertainty and potential issues",
  ("AdsorbML", "ML-relax many, DFT on the top k:\nthe board's '+DFT?' is this recipe"),
  ("exists", "Not unique", "top-k then DFT is AdsorbML's method;\nthe human step is what differs"),
  "the human picks on descriptor cards with rank\nand uncertainty; choice and reason go to the\nlessons log, then into the skill",
  ("EXTENSION · attaches to 8", "+DFT on the five: single points\nbefore any path search")),
 ("(9) Final-state enumeration", "product geometry on the surface · to build",
  ("CatTSunami · NEBscape", "CatTSunami places products with the same\nenumeration as reactants; NEBscape finds both\nendpoints by global optimisation"),
  ("exists", "Not unique", "product enumeration exists in CatTSunami\nand NEBscape"),
  "the same validity gate on the final state;\na state that fails is never paired", None),
 ("(10) Atom mapping, IS–FS pairing", "minimal displacement after symmetry · to build",
  ("NEBscape · CatTSunami", "NEBscape: atom mapping plus symmetry alignment\nbefore interpolation; CatTSunami: several IS–FS\npairs per reaction, lowest valid barrier kept"),
  ("missing", "Missing", "a connectivity check that IS and FS are the\nintended reaction: TSBench's main failure is a\nsaddle that connects the wrong pair"),
  "pairs kept with a reason; pairs tried and\nrejected are reported, not hidden", None),
 ("(11) Path search", "ML NEB, then climbing image or dimer · to build",
  ("CatTSunami · fine-tuned MLIP TS · TSAgent", "ML NEB within 0.1 eV of DFT 91 % of the time, 28×\nfaster; fine-tuning needs fewer than 10 DFT points;\nTSAgent's plan–execute–analyse–replan loop"),
  ("exists", "Not unique", "every TS agent does this; TSAgent reaches 83 %\non an OC20NEB subset. Keep it as a wrapped\ntool, not as the claim"),
  None, None),
 ("(12) Saddle validation", "one imaginary mode; path reaches this IS\nand this FS · to build",
  ("TSBench · CatDT", "TSBench: diagnosis-driven revision lifts success\n50 → 67 %; CatDT: propose–validate gate on overlaps, atom\ncounts, path collisions, a UMA energy screen; 41 → 84 %\non 600 OC20 surfaces"),
  ("missing", "Missing", "imaginary-mode count and endpoint connectivity\nas code; TSAgent checks the mode, runs no IRC;\nCatDT gates overlaps and atom counts, not bonds"),
  "validation is code; endpoint → barrier\npropagation measured in eV and as a rate\nfactor (figure 18)", None),
 ("(13) DFT refinement", "single points, then endpoints and saddle · to build",
  ("CatTSunami · fine-tuned MLIP TS", "DFT single points on the ML saddle to score it;\na few DFT points feed the fine-tuning loop"),
  ("exists", "Not unique", "standard practice; the cost is the question\n(compute budget still open)"),
  "the same locked settings as the endpoints;\nno setting changes mid-path", None),
 ("(14) Report", "barrier, path, both uncertainties · to build",
  ("TSAgent · energetic span", "TSAgent reproduces the BEP relation as a check;\nthe energetic span (Kozuch and Shaik) scores a\nmulti-step mechanism instead of one saddle"),
  ("missing", "Missing", "a benchmark: an OC20NEB subset (DFT NEBs released\nwith CatTSunami) against a single-placement\nbaseline; a decision trace per run"),
  "barrier + validated path + ML and agentic\nuncertainty + trace; open skill and MCP\ntools on AtomisticSkills",
  ("EXTENSION · attaches to 14", "multi-step mechanism scored by\nenergetic span; catalysis after that")),
]

for i, (st, sb, (bh, bb), (gk, gh, gb), ours, ext) in enumerate(rows):
    step(i, st, sb)
    cell("borrow", "borrow", i, bh, bb)
    cell(gk, "gap", i, gh, gb)
    if ours: cell("ours", "ours", i, "Ours", ours)
    else: none("ours", i, "no claim here: a wrapped tool")
    if ext: cell("ext", "ext", i, ext[0], ext[1], hfs=7.3, bfs=6.9)
    else: none("ext", i, "none")

# ---- flow arrows down the step column
sx = COL["step"][0] + COL["step"][1] / 2
for i in range(len(rows) - 1):
    arrow(ax, (sx, ytop(i) - H - 0.0008), (sx, ytop(i + 1) + 0.0008), lw=1.3, ms=8)

# ---- phase brackets on the left
phases = [("A · set up", 0, 0), ("B · initial-state endpoints", 1, 4), ("C · ML relaxation and trust", 5, 8),
          ("D · path steps, to build", 9, 14)]
for lab, a, b in phases:
    y0, y1 = ytop(b) - H, ytop(a)
    ax.plot([0.028, 0.028], [y0 + 0.003, y1 - 0.003], color=GREY, lw=1.6)
    ax.text(0.019, (y0 + y1) / 2, lab, rotation=90, ha="center", va="center", fontsize=8.0, color="#444444")

# ---- bottom band: the verdict on uniqueness
yb, hb = 0.085, 0.088
ax.text(0.04, yb + hb + 0.012, "Verdict on uniqueness, from the rows above", ha="left", va="bottom",
        fontsize=9.2, fontweight="bold", color="#333333")
bw = 0.305
verd = [("exists", "Already taken: a plain transition-state agent is not a novel claim",
         "ML NEB on surfaces: CatTSunami (91 % within 0.1 eV).\nLLM agents for barriers: TSAgent (83 % on an OC20NEB subset,\n70 % versus 73 ± 12 % for experts), CatDT, CopyCAT.\nAutomated endpoints: NEBscape. Validity checks and\ntop-k DFT: AdsorbML. Site finding: every adsorption agent."),
        ("missing", "Still missing before any claim can be measured",
         "the product as a structure and one set of gas references;\npair enumeration for A* + B*; a connectivity check on\nIS–FS pairs; imaginary-mode and endpoint validation as code;\ncalibration of ML disagreement; an OC20NEB benchmark\nsubset with a single-placement baseline."),
        ("ours", "Ours, measurable in hackathon time",
         "1. barrier-ready endpoints: one gate on IS and FS, and the\n    endpoint → barrier propagation reported in eV and as a rate factor\n2. calibrated ML doubt that escalates instead of guessing\n3. agentic uncertainty: variance of the planner's own choices\n4. open skill + MCP tools on AtomisticSkills, scored on OC20NEB")]
for j, (k, h, b) in enumerate(verd):
    x0 = 0.04 + j * (bw + 0.019)
    p = FancyBboxPatch((x0, yb), bw, hb, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND[k])
    ax.add_patch(p)
    ax.text(x0 + bw / 2, yb + hb - 0.006, h, ha="center", va="top", fontsize=8.4, fontweight="bold", color=TITLE_COL[k], zorder=3)
    ax.text(x0 + 0.010, yb + (hb - 0.018) / 2, b, ha="left", va="center", fontsize=7.8, zorder=3, linespacing=1.28)

ax.text(0.5, 0.055, "Numbers are the papers' own, as cited in the design document; extension boxes are dashed purple and "
                    "name the step they attach to; grey italics mark a column with nothing to add.",
        ha="center", va="bottom", fontsize=7.8, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "20-augmented-pipeline.png"))
