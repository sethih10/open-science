"""Figure 23: the pipeline for the stated problem (surface + AB* in; the nearest non-recombining
A* + B* and the barrier out), step by step, with the refinement to borrow and its source, the gap,
what is ours, and the extension layer at its step. One colour per kind of idea."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _style import *
from matplotlib.patches import FancyBboxPatch

KIND = {"step":    dict(fc="white",   ec=EDGE,      lw=1.0, ls="-"),
        "borrow":  dict(fc="#dcfce7", ec="#15803d", lw=1.1, ls="-"),
        "missing": dict(fc="#fef3c7", ec="#b45309", lw=1.1, ls="-"),
        "exists":  dict(fc="#fee2e2", ec="#b91c1c", lw=1.1, ls="-"),
        "ours":    dict(fc=HI_FACE,   ec=HI_EDGE,   lw=1.4, ls="-"),
        "ext":     dict(fc="#f3e8ff", ec="#7e22ce", lw=1.2, ls="--"),
        "input":   dict(fc="#f3f4f6", ec="#6b7280", lw=1.2, ls="-")}
OWNER_COL = {"TOOL": "#374151", "LLM": "#0e7490", "HUMAN": "#be185d", "SKILL": "#4d7c0f"}
TITLE_COL = {"step": TEXT, "borrow": "#14532d", "missing": "#92400e", "exists": "#991b1b",
             "ours": "#1e3a8a", "ext": "#581c87", "input": "#374151"}

fig = plt.figure(figsize=(17, 22))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
title(fig, "The pipeline for the stated problem: surface + AB* in, the nearest non-recombining A* + B* first, then the barrier to it",
      "each row: the step, the refinement to borrow with its source, the gap, what is ours, the extension at its step · the whole figure is schematic")

# ---- problem statement: input, output, and why "nearest"
ax.add_patch(FancyBboxPatch((0.04, 0.872), 0.43, 0.036, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND["input"]))
ax.text(0.255, 0.903, "Input", ha="center", va="top", fontsize=8.4, fontweight="bold", color=TITLE_COL["input"], zorder=3)
ax.text(0.255, 0.875, "a surface slab with adsorbate AB* (for example *OH on Pt(111)) and the product named as A* + B* (*O + *H),\nboth fragments to stay adsorbed",
        ha="center", va="bottom", fontsize=7.2, zorder=3, linespacing=1.2)
arrow(ax, (0.472, 0.890), (0.518, 0.890), lw=1.6, ms=11)
ax.add_patch(FancyBboxPatch((0.52, 0.872), 0.473, 0.036, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND["ours"]))
ax.text(0.7565, 0.903, "Output", ha="center", va="top", fontsize=8.4, fontweight="bold", color=TITLE_COL["ours"], zorder=3)
ax.text(0.7565, 0.875, "first the final state with B* as close to A* as possible and not bonded back; then the barrier from AB* to it,\nboth uncertainties, the recombination rate of nearest pairs, and the cost of the DFT band",
        ha="center", va="bottom", fontsize=7.2, zorder=3, linespacing=1.2)
ax.add_patch(FancyBboxPatch((0.04, 0.838), 0.953, 0.026, boxstyle="round,pad=0.003,rounding_size=0.01", fc="white", ec=HI_EDGE, lw=1.2, zorder=2))
ax.text(0.5165, 0.851, "Why nearest: a band from AB* to a far product holds the bond-breaking saddle plus diffusion saddles, needs more images and iterations, and may not converge "
        "or may converge to the wrong maximum.\nThe nearest validated product gives one saddle and a short band. Even with heuristic endpoints, CatTSunami's ML bands converge only "
        "81 to 82 % of the time for dissociations and 68 to 72 % for transfers.",
        ha="center", va="center", fontsize=7.2, color="#1e3a8a", zorder=3, linespacing=1.25)

# ---- legend
leg = [("step", "pipeline step"), ("borrow", "refinement from a source"), ("missing", "missing: must add"),
       ("exists", "already exists elsewhere: not unique"), ("ours", "what makes it ours"), ("ext", "extension layer, later")]
for j, (k, lab) in enumerate(leg):
    x = 0.04 + j * 0.158
    ax.add_patch(FancyBboxPatch((x, 0.8185), 0.018, 0.011, boxstyle="round,pad=0.002,rounding_size=0.004", zorder=2, **KIND[k]))
    ax.text(x + 0.023, 0.824, lab, ha="left", va="center", fontsize=8.2)

ax.text(0.04, 0.811, "Owner line under each step:", ha="left", va="center", fontsize=7.6, color="#333333")
xo = 0.145
for t, d in [("TOOL", "deterministic code"), ("LLM", "plans, chooses, diagnoses, drafts"), ("HUMAN", "approves, picks, interprets"), ("SKILL", "a written procedure the LLM follows")]:
    ax.text(xo, 0.811, t, ha="left", va="center", fontsize=7.6, fontweight="bold", color=OWNER_COL[t])
    ax.text(xo + 0.0056 * len(t) + 0.006, 0.811, d, ha="left", va="center", fontsize=7.6, color="#333333")
    xo += 0.0056 * len(t) + 0.0046 * len(d) + 0.032
COL = {"step": (0.040, 0.153), "borrow": (0.205, 0.225), "gap": (0.442, 0.210),
       "ours": (0.664, 0.160), "ext": (0.836, 0.154)}
HEAD = {"step": "Pipeline step\n(board + path steps)", "borrow": "Refinement to borrow, with its source",
        "gap": "Gap: missing (amber) or already exists (red)", "ours": "What makes it ours",
        "ext": "Extension layer: dashed,\nattached at its step"}
for k, (x0, w) in COL.items():
    ax.text(x0 + w / 2, 0.795, HEAD[k], ha="center", va="center", fontsize=8.6, fontweight="bold", color="#333333")
ax.plot([0.04, 0.993], [0.781, 0.781], color=EDGE, lw=0.8)

TOP, PITCH, H = 0.774, 0.0400, 0.0350
def ytop(i): return TOP - i * PITCH

OWNER_COL = {"TOOL": "#374151", "LLM": "#0e7490", "HUMAN": "#be185d", "SKILL": "#4d7c0f"}
def cell(kind, col, i, head, body, hfs=7.6, bfs=6.9, owner=None):
    x0, w = COL[col]; y = ytop(i) - H
    ax.add_patch(FancyBboxPatch((x0, y), w, H, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND[kind]))
    ax.text(x0 + w / 2, y + H - 0.004, head, ha="center", va="top", fontsize=hfs, fontweight="bold", color=TITLE_COL[kind], zorder=3)
    if owner:
        # owner line under the title, one coloured word per owner
        parts = owner.split(" · "); total = sum(len(t) for t in parts) + 3 * (len(parts) - 1)
        cw = 0.0032; xs = x0 + w / 2 - total * cw / 2
        for t in parts:
            ax.text(xs, y + H - 0.0135, t, ha="left", va="top", fontsize=6.2, fontweight="bold", color=OWNER_COL[t], zorder=3)
            xs += (len(t) + 3) * cw
        ax.text(x0 + w / 2, y + (H - 0.024) / 2, body, ha="center", va="center", fontsize=bfs, zorder=3, linespacing=1.15)
    else:
        ax.text(x0 + w / 2, y + (H - 0.012) / 2, body, ha="center", va="center", fontsize=bfs, zorder=3, linespacing=1.18)

def none(col, i, text):
    x0, w = COL[col]
    ax.text(x0 + w / 2, ytop(i) - H / 2, text, ha="center", va="center", fontsize=7.0, color="#888888", style="italic", linespacing=1.2)

rows = [
 ("(1) Retrieve and lock", "slab, AB in vacuum, A and B as structures;\ngas references; settings in PROJECT.md",
  ("AiiDA common workflows · SSSP · OC20 settings", "protocol or E_ads sweep for cutoff, k-mesh,\nsmearing, layers; OC20's RPBE and PAW choices\nif the benchmark is OC20NEB"),
  ("missing", "Missing", "A* + B* given as structures, not a name; one set\nof gas references for AB, A and B; a cell wide\nenough that the pair never sees its periodic image"),
  "one locked settings file for IS, FS and band;\nevery number traceable to it", None),
 ("(2–4) Initial state AB*", "sites, placement, orientations × sites;\nscript only, the LLM never places atoms",
  ("CatKit · AdsorbML · AtomWorld", "symmetry-reduced sites; heuristic plus random\nfallback; LLM coordinate edits fail (rotations\nunder 12 %), so placement stays a script"),
  ("exists", "Not unique", "every adsorption agent does this: Adsorb-Agent,\nAdsMind, AtomisticSkills addadsorbate"),
  "symmetry-complete and counted (Burnside);\nfcc and hcp apart; a descriptor card out", None),
 ("(4.1, 6) Validity gate", "nine checks, before and after the relaxation\nof step 5; one code path",
  ("AdsorbML anomaly checks", "desorbed, dissociated, intercalated, surface\nreconstructed; we add migrated, settings mismatch,\nmagnetism collapsed, expected range, imaginary mode"),
  ("exists", "Not unique, one check short", "AdsorbML's four checks already exist; they lack\nthe imaginary-mode check that catches the\nsymmetry trap"),
  "the same gate runs later on every A* + B*\ncandidate: barrier-ready endpoints",
  ("EXTENSION · attaches to 4.1 and 6", "an LLM critic reads the descriptor\ncard and comments; it never\noverrides a code check")),
 ("(5, 7) MLIP and doubt", "one potential for IS, FS and band;\ndisagreement across potentials",
  ("CatTSunami · 80-MLIP survey · fine-tuned MLIP TS", "CatTSunami's EquiformerV2 for the band; no\npotential is best everywhere, so an ensemble;\nfine-tune at the saddle with fewer than 10 DFT points"),
  ("missing", "Missing", "calibration of disagreement against a few DFT\nlabels; a rule by system class; spin initialised\nfor Ni and Co"),
  "calibrated doubt that escalates to review\ninstead of guessing",
  ("EXTENSION · attaches to 5", "active-learning loop: doubt → a few\nDFT labels → fine-tune → re-run")),
 ("(8) Human picks ≤ 5 initial states", "on descriptor cards, rank and uncertainty",
  ("AdsorbML", "ML-relax many candidates, DFT on the top k"),
  ("exists", "Not unique", "top-k then DFT is AdsorbML's recipe;\nthe human step is what differs"),
  "choice and reason to the lessons log,\nthen into the skill",
  ("EXTENSION · attaches to 8", "+DFT single points on the five before\nany path; agentic uncertainty (attaches\nto 7 and 8): N runs, variance of choices")),
 ("(9a) Place A, the binding fragment", "the fragment that keeps the binding atom,\nnear the initial-state binding site",
  ("CatTSunami AutoFrameDissociation", "5 lowest-energy placements within 2 Å of the\nreactant's binding site"),
  ("exists", "Not unique", "this is CatTSunami's step, open source in\nfairchem; whether A stays at its IS site or is\nenumerated is a team decision"),
  None, None),
 ("(9b) Enumerate B sites around A", "ordered by site-graph distance from A",
  ("CatTSunami · classical DFT practice", "5 placements in a 1 to 3 Å shell, 25 pairs in all;\nby hand: fragments at nearest or next-nearest\nhollows, chosen by the author"),
  ("missing", "Missing", "an explicit minimum-distance objective; the rule\nis site-graph distance with in-plane distance as\ntiebreaker, in-plane alone still open"),
  "all symmetry-distinct pairs, nearest first;\nthe count of pairs reported",
  ("EXTENSION · attaches to 9b", "coverage scan: the same pair in\nseveral cell sizes to measure the\nlateral interaction directly")),
 ("(9c) Relax each A* + B* pair", "same potential and settings as the initial state;\nrandom displacement first (symmetry trap)",
  ("CatTSunami", "product frames relaxed with the MLIP\nbefore any check"),
  ("exists", "Not unique", "standard"),
  None, None),
 ("(9d) Gate the pair: still dissociated?", "no A–B bond; nothing desorbed, moved or\nsubsurface; surface intact; no imaginary mode",
  ("CatTSunami", "discard frames 'where the products react or some\nother anomaly occurs'"),
  ("missing", "Missing", "the bond-re-formed check as code with a\nthreshold on the A–B distance; the\nimaginary-mode check on the pair"),
  "the same gate as the initial state; every\nrejection logged; a failing state is never paired", None),
 ("(9e) Choose and report the final state", "nearest survivor first, then energy;\nkeep several, not one",
  ("CatTSunami", "one surviving frame picked at random"),
  ("missing", "Missing", "E(FS near) and E(FS ∞) = E(A*) + E(B*) − E(slab)\nboth reported; adjacent fragments can repel, so\nthe nearest is not always the lowest in energy"),
  "the recombination rate of nearest pairs:\na measurable none of the papers above report",
  ("EXTENSION · attaches to 9e", "alternative target: lowest energy\nwithin one site hop (team decision)")),
 ("(10) Map atoms and pair IS with FS", "same atoms, unwrapped across the cell",
  ("NEBscape · CatTSunami", "atom mapping plus symmetry alignment; unwrap by\ndepth-first search from the binding atom; the\nunbroken part moves as one moiety"),
  ("missing", "Missing", "a check that the pair is the intended reaction;\nTSBench's main failure is a saddle that\nconnects the wrong pair"),
  "pairs tried and rejected are reported,\nnot hidden", None),
 ("(11) ML band and climbing image", "several IS–FS pairs; lowest valid barrier kept",
  ("CatTSunami · fine-tuned MLIP TS · TSAgent", "ML NEB within 0.1 eV of DFT 91 % of the time,\n28× faster; TSAgent's plan–execute–analyse–\nreplan loop at DFT level"),
  ("exists", "Not unique", "every TS agent does this; TSAgent reaches 83 %\non an OC20NEB subset. A wrapped tool,\nnot the claim"),
  None, None),
 ("(12) Validate the saddle and the band", "one imaginary mode; the band ends at this\nIS and this FS",
  ("CatTSunami band checks · TSBench · CatDT · Pynta", "breaking bond stretched 1.25 to 1.63× in some\nframe, connectivity constant elsewhere; diagnosis-driven\nrevision (50 → 67 %); propose–validate gate; IRC on every saddle"),
  ("missing", "Missing", "these checks as code in one tool; TSAgent's\nabstract reports none; CatDT is unpublished"),
  "validation is code; endpoint → barrier\npropagation measured (figure 18)", None),
 ("(13) DFT refinement", "single points on IS, TS and FS; then relax",
  ("CatTSunami: ML + 3 DFT single points", "score the ML saddle with DFT; fmax < 0.05 eV/Å;\nin its case study 102 DFT bands converged and\n8 failed; 14 % of converged bands were wrong"),
  ("exists", "Not unique", "standard practice; the cost and the failures\nare the point (compute budget still open)"),
  "force calls and failure rate, gated versus\nnaive endpoints: the cost measurable", None),
 ("(14) Report", "barrier, validated path, both uncertainties,\ndecision trace, cost",
  ("TSAgent BEP check · energetic span · OC20NEB", "BEP relation as a sanity check; energetic span\nif multi-step; OC20NEB DFT bands as the\nground truth"),
  ("missing", "Missing", "the OC20NEB subset and a single-placement\nbaseline; the decision-trace format"),
  "three numbers: barrier shift, recombination\nrate, DFT force calls and failures; open\nskill + MCP tools on AtomisticSkills",
  ("EXTENSION · attaches to 14", "multi-step mechanism scored by\nenergetic span; catalysis after that")),
]

OWNERS = ['TOOL · HUMAN · SKILL', 'TOOL', 'TOOL', 'TOOL · LLM · SKILL', 'HUMAN · LLM', 'TOOL', 'TOOL', 'TOOL', 'TOOL', 'TOOL · LLM', 'TOOL', 'TOOL', 'TOOL · LLM · SKILL', 'TOOL', 'LLM · HUMAN · SKILL']
for i, (st, sb, (bh, bb), (gk, gh, gb), ours, ext) in enumerate(rows):
    cell("step", "step", i, st, sb, hfs=7.9, bfs=6.6, owner=OWNERS[i])
    cell("borrow", "borrow", i, bh, bb)
    cell(gk, "gap", i, gh, gb)
    if ours: cell("ours", "ours", i, "Ours", ours)
    else: none("ours", i, "no claim here: a wrapped tool")
    if ext: cell("ext", "ext", i, ext[0], ext[1], hfs=7.2, bfs=6.8)
    else: none("ext", i, "none")

sx = COL["step"][0] + COL["step"][1] / 2
for i in range(len(rows) - 1):
    arrow(ax, (sx, ytop(i) - H - 0.0008), (sx, ytop(i + 1) + 0.0008), lw=1.3, ms=8)

phases = [("A · set up", 0, 0, GREY), ("B · initial state AB*", 1, 4, GREY),
          ("C · the stated problem: the final state A* + B*", 5, 9, HI_EDGE), ("D · the path and the report", 10, 14, GREY)]
for lab, a, b, col in phases:
    y0, y1 = ytop(b) - H, ytop(a)
    ax.plot([0.028, 0.028], [y0 + 0.003, y1 - 0.003], color=col, lw=2.2 if col == HI_EDGE else 1.6)
    ax.text(0.019, (y0 + y1) / 2, lab, rotation=90, ha="center", va="center", fontsize=7.8,
            color=HI_EDGE if col == HI_EDGE else "#444444", fontweight="bold" if col == HI_EDGE else "normal")

# ---- verdict band
yb, hb = 0.066, 0.080
ax.text(0.04, yb + hb + 0.012, "Verdict on uniqueness for this problem", ha="left", va="bottom", fontsize=9.2, fontweight="bold", color="#333333")
bw = 0.305
verd = [("exists", "Already taken: the final state by sampling, and the band",
         "The dissociation final state by sampling: CatTSunami's\nAutoFrameDissociation, open source in fairchem. ML bands:\nCatTSunami. LLM barrier agents: TSAgent, CatDT, CopyCAT,\nEl Agente Potente. Rates with IRC validation: Pynta. Endpoints\nby global optimisation: NEBscape. The adsorption workflow of\nsteps 2 to 8 as such: every adsorption agent."),
        ("missing", "Still missing before any claim can be measured",
         "A* + B* as structures and one set of gas references; the\ndistance metric; a bond-re-formed threshold; the intended-\nreaction check on IS–FS pairs; the validation tool; an\nOC20NEB subset with a single-placement baseline; the\ncompute budget for DFT bands."),
        ("ours", "Ours, measurable in hackathon time",
         "1. an explicit minimum-distance objective over symmetry-complete\n    pairs, instead of lowest energy in a shell then a random pick\n2. one code gate on both endpoints, every rejection logged\n3. three numbers: barrier shift, nearest-pair recombination rate,\n    DFT force calls and failure rate, gated versus naive endpoints\n4. calibrated ML doubt; open skill + tools scored on OC20NEB\n    (agentic uncertainty only if time allows: extension layer)")]
for j, (k, h, b) in enumerate(verd):
    x0 = 0.04 + j * (bw + 0.019)
    ax.add_patch(FancyBboxPatch((x0, yb), bw, hb, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND[k]))
    ax.text(x0 + bw / 2, yb + hb - 0.005, h, ha="center", va="top", fontsize=8.0, fontweight="bold", color=TITLE_COL[k], zorder=3)
    ax.text(x0 + 0.010, yb + (hb - 0.016) / 2, b, ha="left", va="center", fontsize=7.1, zorder=3, linespacing=1.26)
ax.text(0.5, 0.040, "Numbers are the papers' own, as cited in the design document; the blue bracket marks the rows that are the stated problem; "
                    "dashed purple boxes name the step they attach to; grey italics mark a column with nothing to add.",
        ha="center", va="bottom", fontsize=7.4, style="italic", color="#444444")
finish(fig, os.path.join(os.path.dirname(__file__), "..", "23-problem-pipeline.png"))
