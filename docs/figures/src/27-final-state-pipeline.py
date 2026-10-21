"""Figure 27: the pipeline for the stated problem, final state only, derived from figure 23 (surface + AB* in; the nearest non-recombining
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
        "later":   dict(fc="white",   ec="#9a9a9a", lw=1.0, ls="--"),
        "input":   dict(fc="#f3f4f6", ec="#6b7280", lw=1.2, ls="-")}
OWNER_COL = {"TOOL": "#374151", "LLM": "#0e7490", "HUMAN": "#be185d", "SKILL": "#4d7c0f"}
TITLE_COL = {"later": "#777777", "step": TEXT, "borrow": "#14532d", "missing": "#92400e", "exists": "#991b1b",
             "ours": "#1e3a8a", "ext": "#581c87", "input": "#374151"}

fig = plt.figure(figsize=(17, 18.5))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0.16, 1); ax.axis("off")
title(fig, "The pipeline for the stated problem: surface + AB* in, the nearest non-recombining A* + B* out",
      "each row: the step, the refinement to borrow with its source, the gap, what is ours, the extension at its step · the whole figure is schematic")

# ---- problem statement: input, output, and why "nearest"
ax.add_patch(FancyBboxPatch((0.04, 0.872), 0.43, 0.036, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND["input"]))
ax.text(0.255, 0.903, "Input", ha="center", va="top", fontsize=8.4, fontweight="bold", color=TITLE_COL["input"], zorder=3)
ax.text(0.255, 0.875, "a surface slab with adsorbate AB* (for example *OH on Pt(111)) and the product named as A* + B* (*O + *H),\nboth fragments to stay adsorbed",
        ha="center", va="bottom", fontsize=7.2, zorder=3, linespacing=1.2)
arrow(ax, (0.472, 0.890), (0.518, 0.890), lw=1.6, ms=11)
ax.add_patch(FancyBboxPatch((0.52, 0.872), 0.473, 0.036, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND["ours"]))
ax.text(0.7565, 0.903, "Output", ha="center", va="top", fontsize=8.4, fontweight="bold", color=TITLE_COL["ours"], zorder=3)
ax.text(0.7565, 0.875, "the final state with B* as close to A* as possible and not bonded back, with E(FS near), E(FS ∞),\nthe pairs tried and rejected, the recombination rate and the uncertainty",
        ha="center", va="bottom", fontsize=7.2, zorder=3, linespacing=1.2)
ax.add_patch(FancyBboxPatch((0.04, 0.838), 0.953, 0.026, boxstyle="round,pad=0.003,rounding_size=0.01", fc="white", ec=HI_EDGE, lw=1.2, zorder=2))
ax.text(0.5165, 0.851, "Why nearest: any later path from AB* to a far product crosses diffusion saddles as well as the bond-breaking one, so it is longer and fails more often; "
        "the nearest validated product keeps one saddle.\nNEBscape, with a 4.5 Å separation cut-off and Pareto-selected endpoints, converges 94 % of 304 OC20NEB reactions; CatTSunami's bands, with sampled endpoints, 81 to 82 % for dissociations.",
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
 ("(5, 7) MLIP and doubt", "chosen before placement, so 9c can use it;\none potential for IS and FS; committee disagreement",
  ("CatTSunami · 80-MLIP survey · fine-tuned MLIP TS", "CatTSunami's EquiformerV2 for the band; no\npotential is best everywhere, so an ensemble;\nfine-tune at the saddle with fewer than 10 DFT points"),
  ("missing", "Missing", "calibration of disagreement against a few DFT\nlabels; a rule by system class; spin initialised\nfor Ni and Co"),
  "calibrated doubt that escalates to review\ninstead of guessing",
  ("EXTENSION · attaches to 5", "active-learning loop: doubt → a few\nDFT labels → fine-tune → re-run")),
 ("(8) Human picks ≤ 5 states", "the final states after 9e, on cards with rank\nand doubt; initial states only if AB* is enumerated",
  ("AdsorbML", "ML-relax many candidates, DFT on the top k"),
  ("exists", "Not unique", "top-k then DFT is AdsorbML's recipe;\nthe human step is what differs"),
  "choice and reason to the lessons log,\nthen into the skill",
  ("EXTENSION · attaches to 8", "+DFT single points on the five before\nany path; agentic uncertainty (attaches\nto 7 and 8): N runs, variance of choices")),
 ("(9a) Place A, the binding fragment", "the fragment that keeps the binding atom,\nnear the initial-state binding site",
  ("NEBscape · CatTSunami", "NEBscape: minima hopping from symmetry-inequivalent\nspglib sites, random orientations; CatTSunami: 5 lowest-\nenergy placements within 2 Å of the reactant's site"),
  ("exists", "Not unique", "both do it, both open source (MIT); whether A\nstays at its IS site or is enumerated is a\nteam decision"),
  "the geometry-critic orders the list by a site\ntype per fragment, the board's point 4, AdsMind\nstyle; it never removes a pair", None),
 ("(9b) Enumerate B sites around A", "ordered by site-graph distance from A, within\nthe board's window [1.5 d, 5] Å, d the bond to break",
  ("NEBscape · CatTSunami", "NEBscape: two adsorbates arranged combinatorially on\nunique sites, separations above 4.5 Å excluded;\nCatTSunami: 5 placements in a 1 to 3 Å shell, 25 pairs"),
  ("missing", "Missing", "a nearest-first objective: NEBscape keeps a cut-off\nand an energy–distance Pareto front, CatTSunami\nsamples; the metric: site graph, in-plane tiebreak"),
  "all symmetry-distinct pairs, nearest first and\ncounted; the policy compared with NEBscape's\nPareto choice on the same reactions",
  ("EXTENSION · attaches to 9b", "coverage scan: the same pair in\nseveral cell sizes to measure the\nlateral interaction directly")),
 ("(9c) Pre-filter, then relax each pair", "one MLIP force call per pair: force on B towards A\nflags likely recombination; then relax, same potential\nand settings as the IS, random displacement first",
  ("NEBscape · CatTSunami", "both relax every candidate with the MLIP;\nneither screens by force first"),
  ("missing", "Missing", "the pull-force threshold; whether a flagged pair\nis queued last or dropped (board: queued)"),
  "the board's pull-force pre-filter: cheap, before\nany relaxation; flagged pairs go to the back\nof the queue, not out", None),
 ("(9d) Gate the pair: still dissociated?", "no A–B bond; nothing desorbed, moved or\nsubsurface; surface intact; no imaginary mode",
  ("NEBscape · CatTSunami", "NEBscape: Hookean constraints keep fragments intact\nduring sampling, graph isomorphism checks after;\nCatTSunami: discard frames 'where the products react'"),
  ("missing", "Missing", "the bond-re-formed check as code with a\nthreshold on the A–B distance; the\nimaginary-mode check on the pair"),
  "a test after relaxation with a logged reason, not\na constraint during sampling; same gate as the IS;\na failing state is never paired", None),
 ("(9e) Choose and report the final state", "cluster survivors by SOAP; nearest first, then\nenergy; keep the nearest and lowest per cluster",
  ("NEBscape · CatTSunami", "NEBscape: within 1.2 eV of the minimum, the first two\nenergy–distance Pareto fronts, SOAP deduplication;\nCatTSunami: one survivor at random"),
  ("missing", "Missing", "E(FS near) and E(FS ∞) = E(A*) + E(B*) − E(slab)\nboth reported; adjacent fragments can repel, so\nthe nearest is not always the lowest in energy"),
  "the recombination rate of nearest pairs:\na measurable none of the papers above report",
  ("EXTENSION · attaches to 9e", "alternative target: lowest energy\nwithin one site hop (team decision)")),
 ("(14) Report", "both energies, rejections with reasons,\nrecombination rate, doubt, decision trace",
  ("AtomisticSkills logging · general-peer-review · OC20NEB", "every parameter logged beside its output; the\nreport read by the peer-review skill; OC20NEB\nproduct frames as the comparison"),
  ("missing", "Missing", "the OC20NEB subset and a single-placement\nbaseline; the decision-trace format"),
  "two numbers and two comparisons; open\nskill + MCP tools on AtomisticSkills",
  None),
]

OWNERS = ['TOOL · HUMAN · SKILL', 'TOOL', 'TOOL', 'TOOL · LLM · SKILL', 'HUMAN · LLM', 'TOOL', 'TOOL', 'TOOL', 'TOOL', 'TOOL · LLM', 'TOOL', 'TOOL', 'TOOL · LLM · SKILL', 'TOOL', 'LLM · HUMAN · SKILL']
LATER = set()   # the path and the report: a later phase, not the goal now
for i, (st, sb, (bh, bb), (gk, gh, gb), ours, ext) in enumerate(rows):
    cell("later" if i in LATER else "step", "step", i, ("later · " + st) if i in LATER else st, sb, hfs=7.9, bfs=6.6, owner=OWNERS[i])
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
          ("C · the stated problem: the final state A* + B*", 5, 9, HI_EDGE), ("D · report", 10, 10, GREY)]
for lab, a, b, col in phases:
    y0, y1 = ytop(b) - H, ytop(a)
    ax.plot([0.028, 0.028], [y0 + 0.003, y1 - 0.003], color=col, lw=2.2 if col == HI_EDGE else 1.6)
    ax.text(0.019, (y0 + y1) / 2, lab, rotation=90, ha="center", va="center", fontsize=7.8,
            color=HI_EDGE if col == HI_EDGE else "#444444", fontweight="bold" if col == HI_EDGE else "normal")

# ---- verdict band
yb, hb = 0.20, 0.080
ax.text(0.04, yb + hb + 0.012, "Verdict on uniqueness for this problem", ha="left", va="bottom", fontsize=9.2, fontweight="bold", color="#333333")
bw = 0.305
verd = [("exists", "Already taken: NEBscape is the closest prior work; CatTSunami samples",
         "NEBscape (MIT, no LLM): symmetry-inequivalent sites, two adsorbates\nplaced combinatorially, separations above 4.5 Å excluded, Hookean\nfragment integrity, energy–distance Pareto selection, graph checks\nalong the band; 304 OC20NEB reactions, 94 % converged. CatTSunami\nsamples the same final state. Steps 2 to 8: every adsorption agent;\nnone builds a co-adsorbed product and checks that it stayed apart."),
        ("missing", "Still missing before any claim can be measured",
         "A* + B* as structures and one set of gas references; the\ndistance metric; a bond-re-formed threshold; the pass\ncriterion for a final state; an OC20NEB subset whose\nproduct frames we compare against; a single-placement\nbaseline; whether any DFT single point runs."),
        ("ours", "Ours, measurable in hackathon time",
         "1. a nearest-first objective over symmetry-complete, counted pairs,\n    instead of NEBscape's cut-off and Pareto front or CatTSunami's sampling\n2. one code gate on both endpoints, every rejection logged\n3. two numbers now: nearest-pair recombination rate, E(FS near) − E(FS ∞);\n    and the three final-state policies compared on the same dissociations\n4. calibrated ML doubt; open skill + tools scored against\n    OC20NEB product frames (agentic uncertainty: extension)")]
for j, (k, h, b) in enumerate(verd):
    x0 = 0.04 + j * (bw + 0.019)
    ax.add_patch(FancyBboxPatch((x0, yb), bw, hb, boxstyle="round,pad=0.003,rounding_size=0.01", zorder=2, **KIND[k]))
    ax.text(x0 + bw / 2, yb + hb - 0.005, h, ha="center", va="top", fontsize=8.0, fontweight="bold", color=TITLE_COL[k], zorder=3)
    ax.text(x0 + 0.010, yb + (hb - 0.016) / 2, b, ha="left", va="center", fontsize=7.1, zorder=3, linespacing=1.26)
ax.text(0.5, 0.168, "Numbers are the papers' own, as cited in the design document; the blue bracket marks the rows that are the stated problem; "
                    "dashed purple boxes name the step they attach to; grey italics mark a column with nothing to add.",
        ha="center", va="bottom", fontsize=7.4, style="italic", color="#444444")
out = os.path.join(os.path.dirname(__file__), "..", "27-final-state-pipeline.png")
fig.savefig(out, dpi=150, facecolor="white"); print("wrote", out)
