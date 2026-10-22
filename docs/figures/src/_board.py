"""The single source of truth for the pipeline figures and the README tables.

One record per step of the team's board of 21 October 2026, in the board's order and numbering, plus the
input prompt. Every figure script imports STEPS; board_tables.py writes the README tables from it;
board_check.py asserts that every figure and the README carry the same names. Change a word here, never
in a figure script.

Field notes:
- owners: tuple of H, L, S, T; the first does the work and equals the Owner column of AGENTS.md section 2.
- action: the one line a figure prints under the step name: the tool and what it does.
- open: the one headline open decision shown as the amber tag; AGENTS.md section 11 holds the full list.
- ext: the extension at this step, dashed purple in every figure.
- deferred: the step stays on the board, numbered, but is commented out of the pipeline code until the team decides how to implement it; grey and dashed in every figure.
- code_order: for the six points of step 3, the order the code runs them; 0 means the alternative.
- checkpoint: one of CHECKPOINTS. The placement of "approve the plan" after 1* is the team's to confirm.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

BOARD_DATE = "21 October 2026"
import sys as _sys
_sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3] / "src"))
from fragplace.registry.agents import AGENTS, CHECKPOINTS, HPC_ONLY, PLANNER, SKILLS_OURS, SKILLS_REUSED  # noqa: E402,F401  the roster lives in the package
TOOLS = ("literature_lookup", "structure_retrieval", "calculation_protocol", "mlip_selection", "compute_plan", "site_enumeration", "adsorbate_placement",
         "pair_enumeration", "pull_force_screen", "minima_hopping", "relaxation", "anomaly_filter", "soap_clustering",
         "uncertainty_estimation", "descriptor_card", "ranking", "reference_energies", "report", "dft_single_points", "active_learning")
PHASES = {"setup": "Set up", "step3": "Step 3: adsorbate placement, the stated problem", "select": "Select and report"}
OWNER_NAMES = {"H": "HUMAN", "L": "LLM", "S": "SKILL", "T": "TOOL"}


@dataclass(frozen=True)
class Step:
    key: str                      # "prompt", "1", "1*", "2", "3.1" .. "3.6", "4" .. "8", "solution"
    label: str                    # the board's step name
    phase: str                    # setup | step3 | select
    panel: int                    # panel of the team's visualisation: 1 inputs, 3 sites, 4 distance, 5 best, 2 output
    board: str                    # what the board says
    lit_source: str
    lit: str
    ours: str
    action: str                   # tool: what it does
    owners: Tuple[str, ...]
    tools: Tuple[str, ...]
    ext_tools: Tuple[str, ...] = ()           # tools of the extension at this step
    detail: str = ""                          # what the step does in full, for AGENTS.md section 2
    open: Optional[str] = None
    ext: Optional[str] = None
    deferred: Optional[str] = None               # the step is kept on the board but commented out of the code for now
    skill: Optional[str] = None
    agents: Tuple[Tuple[str, str], ...] = ()    # (name, what it does here), one per agent acting at the step
    agent_ext: Optional[str] = None               # a dashed LLM chip
    human: Optional[str] = None
    checkpoint: Optional[str] = None
    board_input: Optional[str] = None             # the purple box the board drew here
    code_order: Optional[int] = None

    @property
    def title(self) -> str:
        return self.label if self.key in ("prompt", "solution") else f"({self.key}) {self.label}"

    @property
    def is_point(self) -> bool:
        return self.key.startswith("3.")


STEPS = [
    Step("prompt", "Input prompt", "setup", 1,
         detail="The human supplies the relaxed inputs and answers the five interview questions in the orchestrator's question box, from answers the computational-chemist drafts; code writes the answers into PROJECT.md; the literature-reader fetches E_ads of AB, A and B, the reaction energy and d, with sources",
         board="surf + adsorbates (2) + a general system description; surface and adsorbate with their energies, E_ads from the literature",
         lit_source="Get Physics Done · AutoDFT",
         lit="a Formulate interview that locks scope, conventions and verification targets; compact written settings rules, such as spin for Ni and Co",
         ours="the computational-chemist drafts five fixed questions, the orchestrator asks them, code writes the answers into PROJECT.md; the three relaxed inputs, and A and B in vacuum when given, are supplied",
         action="literature_lookup: published E_ads of AB, A and B, the reaction energy and the bond length d, with source, for the human to check",
         owners=("H", "L", "S"), tools=("literature_lookup",), skill="dft-settings-protocol",
         agents=(("computational-chemist", "drafts the Formulate interview the orchestrator asks"), ("literature-reader", "fetches E_ads, the reaction energy and d with their sources, from databases and papers, for the human to check")),
         human="supplies the relaxed inputs; answers the five interview questions in the question box",
         board_input="Critic, knowledge prompts"),
    Step("1", "Structure retriever", "setup", 1,
         detail="Takes the three supplied relaxed structures with their energies and A and B as structures; selects the surface cell so periodic images stay 10 Å apart; locks the settings the run uses in PROJECT.md; with no DFT, every study until `dft_single_points` is built, protocol mlip locks the cell, the force threshold, the gas references and the open decisions and asks nothing about DFT; a study that runs DFT adds the inputs' settings, the human's physics choices and a DFT protocol; `dft-settings-protocol` holds the protocol",
         board="fed by the input prompt: surf + adsorbates (2) and a general system description; surface and adsorbate with their energies",
         lit_source="AiiDA common workflows · SSSP · OC20",
         lit="no DFT runs until dft_single_points is built: protocol mlip locks the cell, the force threshold and the gas species, and the potential computes every energy; DFT settings only from a verified protocol, never from the model",
         ours="the three relaxed inputs plus A and B as structures; settings locked in PROJECT.md; a cell wide enough for the pair",
         action="structure_retrieval and calculation_protocol: the three relaxed inputs, A and B by cleaving the named bond, the cell; settings locked in PROJECT.md",
         owners=("T", "H", "L", "S"), tools=("structure_retrieval", "calculation_protocol"), open="one set of gas references for AB, A and B",
         skill="dft-settings-protocol", agents=(("computational-chemist", "calls structure_retrieval and calculation_protocol, proposes the lock and states the protocol's reason"),),
         human="approves the settings lock in the question box", checkpoint="approve settings"),
    Step("1*", "MLIP selection, AL prospect", "setup", 1,
         detail="Benchmarks two or three candidate potentials on the system class before any placement; the chosen one relaxes every candidate; all candidates form the committee of step 7; spin for Ni and Co; then `compute_plan` estimates the minutes of each heavy step and the hpc-specialist proposes its lane and resources, approved with the plan; active learning is an extension",
         board="chosen before placement so step 3 can use it; active learning as a prospect",
         lit_source="80-MLIP survey · CatBench · AtomisticSkills",
         lit="no potential is best everywhere; CatBench classes each failure; ml-mlip-benchmark scores candidates on the system class",
         ours="benchmark two or three, record why; spin for Ni and Co; the candidates become the committee of step 7; the hpc-specialist sets each heavy step's lane and resources from compute_plan's estimate",
         action="mlip_selection: two or three candidates benchmarked on the system class; the chosen one relaxes, all form the committee of step 7; compute_plan: minutes per heavy step, its lane and resources",
         owners=("T", "L", "S", "H"), tools=("mlip_selection", "compute_plan"), ext_tools=("active_learning",), ext="active_learning: doubt → a few DFT labels → fine-tune → re-run",
         skill="ml-mlip-benchmark, reused", agents=(("mlip-specialist", "chooses the potential from the benchmark and records why"), ("hpc-specialist", "proposes each heavy step's lane and resources"), ("scientific-critic", "reviews the plan before the human approves it")),
         human="approves the plan in the question box", checkpoint="approve the plan"),
    Step("2", "Adsorption sites with pymatgen", "setup", 3,
         detail="Symmetry-inequivalent sites of the selected cell, fcc and hcp hollows apart, counted; pymatgen's finder as the baseline",
         board="Python, with pymatgen",
         lit_source="pymatgen · ACAT · spglib",
         lit="pymatgen's site finder labels no fcc or hcp hollow; ACAT gives labelled sites and the site graph; spglib the symmetry operations",
         ours="symmetry-complete and counted; fcc and hcp apart; pymatgen kept as the baseline",
         action="site_enumeration: symmetry-inequivalent sites, fcc and hcp apart, counted; pymatgen as the baseline",
         owners=("T",), tools=("site_enumeration",)),
    Step("3.1", "Least distance before pull-back", "step3", 4,
         detail="The bond-re-formed check as code, applied inside step 5 after relaxation; a pair that fails is never kept; the A–B threshold open: team decision",
         board="estimate the minimum distance at which the dissociated atom is not pulled back",
         lit_source="CatTSunami · NEBscape",
         lit="CatTSunami treats a bond as breaking at 1.25 to 1.63× its length; NEBscape keeps fragments intact by Hookean constraint during sampling",
         ours="the bond-re-formed check as code, after relaxation, with a logged reason; a pair that fails is never kept",
         action="anomaly_filter, check 10: the A–B bond re-formed after relaxation; runs inside step 5",
         owners=("T",), tools=("anomaly_filter",), open="the A–B distance threshold",
         skill="dissociation-final-state", code_order=5),
    Step("3.2", "Window [1.5 d, 5] Å", "step3", 4,
         detail="B sites around each A within [1.5 d, 5] Å, d the length of the bond to break: a published value the human checked, else the bond measured as d_definition says; every symmetry-distinct pair, ordered by site-graph distance with in-plane tiebreak, counted; then B is placed on every pair, because 3.3 screens placed structures",
         board="d the max vdW length of the bond to break, from the literature",
         lit_source="NEBscape · CatTSunami",
         lit="NEBscape excludes separations above 4.5 Å; CatTSunami samples a 1 to 3 Å shell, 25 pairs, one survivor at random",
         ours="every symmetry-distinct pair inside the window, ordered by site-graph distance, nearest first, counted: the objective is explicit; B placed on each",
         action="pair_enumeration: every symmetry-distinct A–B pair in [1.5 d, 5] Å, nearest first by site-graph distance, counted; d published and checked, else measured; adsorbate_placement puts B on each",
         owners=("T", "L"), tools=("pair_enumeration", "literature_lookup", "adsorbate_placement"),
         open="d from vacuum or from the adsorbed molecule; 5 Å or NEBscape's 4.5 Å",
         skill="dissociation-final-state", agents=(("literature-reader", "looks for d, the length of the bond to break, with its source, for the human to check"),), code_order=2),
    Step("3.3", "Pull force with the MLIP", "step3", 4,
         detail="One MLIP force call per pair; the force component on each fragment along the A–B axis; a pull towards the other fragment above the threshold queues the pair last, never drops it",
         board="use the selected MLIP to estimate the pull force on the binding fragment",
         lit_source="NEBscape · CatTSunami",
         lit="neither screens by force; both relax every candidate they generate",
         ours="one force call per pair before relaxing; a pull towards the other fragment queues the pair last, never drops it",
         action="pull_force_screen: one MLIP force call per pair; a pull towards the other fragment queues the pair last",
         owners=("T",), tools=("pull_force_screen",), open="the force threshold",
         skill="dissociation-final-state", code_order=3),
    Step("3.4", "Agentic critique of the cleavage", "step3", 5,
         detail="`surface-chemist` reads the descriptor cards, reorders the candidates and proposes a site type per fragment as advice; never adds or removes a candidate, never edits coordinates, never overrides a check",
         board="criticise and adjust the placement from knowledge of what the cleavage does",
         lit_source="AdsMind · AtomWorld · ChemCrow",
         lit="AdsMind: the LLM returns a site type, code places, 98.8 %; AtomWorld: LLM coordinate edits fail; an LLM judge rates fluent wrong answers well",
         ours="surface-chemist reads descriptor cards, proposes a site type per fragment, orders the list; never edits coordinates, never overrides a check",
         action="surface-chemist reads descriptor_card text, reorders, advises a site type per fragment; never edits coordinates",
         owners=("L", "T"), tools=("descriptor_card",),
         ext="a vision model to predict the sites, only after the geometry benchmark shows an image helps",
         skill="dissociation-final-state", agents=(("surface-chemist", "orders the list from the chemistry of the cleavage, with a site type per fragment as advice; never adds a candidate or overrides a check"),),
         board_input="Critic, knowledge; Vision model (?)", code_order=4),
    Step("3.5", "Site and orientation, pymatgen", "step3", 3,
         detail="The fragment keeping the binding atom, A, placed at every symmetry-distinct site near its old site, counted; A fixed at its old site is the cheap baseline",
         board="agentic knowledge or a package such as pymatgen, so the binding fragment adsorbs",
         lit_source="El Agente Potente · CatTSunami",
         lit="symmetry-distinct sites and orientations enumerated by code; CatTSunami: 5 placements within 2 Å of the old binding site",
         ours="code places, the LLM never does: the fragment keeping the binding atom at symmetry-distinct sites near its old site, counted",
         action="adsorbate_placement: A at every symmetry-distinct site near its old site, counted; A fixed is the cheap baseline",
         owners=("T",), tools=("adsorbate_placement",),
         open="the binding fragment fixed at its old site, or enumerated",
         deferred="later; the team decides how; A stays at its initial-state site for now",
         skill="dissociation-final-state", code_order=1),
    Step("3.6", "Or minima hopping with the MLIP", "step3", 5,
         detail="NEBscape's endpoint generator with the chosen MLIP as the alternative generator and the baseline policy",
         board="alternatively, minima hopping with the selected MLIP for the binding fragment",
         lit_source="NEBscape",
         lit="minima hopping from symmetry-inequivalent sites with Hookean constraints; 94 % of 304 OC20NEB reactions converge; MIT code",
         ours="kept as the alternative generator, wrapped, and as the baseline policy our nearest-first choice is scored against",
         action="minima_hopping: NEBscape's endpoint generator with the chosen MLIP, the alternative and the baseline policy",
         owners=("T",), tools=("minima_hopping",), skill="dissociation-final-state", code_order=0),
    Step("4", "Initial configurations", "select", 4,
         detail="Every pair that passed the gate before relaxation relaxed with the chosen potential and the locked settings, in the surface-chemist's order; orientations under the site's stabiliser, Burnside-counted; random displacement first; start and end of each written to geometries/",
         board="output of step 3: all degrees of freedom of the adsorbate × all sites",
         lit_source="Burnside · symmetry trap",
         lit="the count checked by Burnside's lemma; a small random displacement before relaxing, or a symmetric start relaxes to a saddle",
         ours="every candidate pair relaxed with the chosen potential and the locked settings, displacement first",
         action="relaxation: relax every pair the first gate passed with the chosen MLIP and the locked settings, random displacement first; Burnside-counted",
         owners=("T",), tools=("relaxation",),
         open="the displacement amplitude", skill="dissociation-final-state"),
    Step("5", "Physics-based and anomaly filtering", "select", 4,
         detail="The gate of section 3.4 on every structure before and after relaxation: nine checks per fragment plus the two final-state checks, 3.1 among them as the bond-re-formed check; verdict into the card; a failing pair is never kept; the ML variant not taken; an LLM critic comments only, extension",
         board="physics by script; anomaly by ML and/or script; reasoning questions injected",
         lit_source="AdsorbML in fairchem",
         lit="four anomaly checks exist; the desorbed check treats A* + B* as one adsorbate and misses B leaving while A stays",
         ours="nine checks as code, per fragment, before and after relaxation; the ML variant not taken; every rejection logged with its reason",
         action="anomaly_filter: nine checks per fragment plus two final-state checks, before relaxation with the checks the team lists and after it with all; verdict into the card; rejections logged",
         owners=("T",), tools=("anomaly_filter", "descriptor_card"), open="which checks run before relaxation",
         ext="an LLM critic reads the card and comments; it never overrides a check",
         skill="dissociation-final-state", agent_ext="surface-chemist: comments on cards, never overrides",
         board_input="Reasoning questions"),
    Step("6", "SOAP clustering", "select", 5,
         detail="Cluster the survivors by SOAP as NEBscape does; keep the lowest per cluster as the board says and the nearest, our objective; nearest first overall; E(A*), E(B*), E(FS ∞) with the chosen MLIP",
         board="pick the 3 lowest-energy configurations from each cluster, could be more",
         lit_source="NEBscape",
         lit="deduplicates by SOAP and keeps the first two energy–distance Pareto fronts within 1.2 eV",
         ours="cluster the survivors; keep the nearest and the lowest per cluster; nearest first overall",
         action="soap_clustering: SOAP clusters of the survivors; the nearest and the lowest per cluster kept",
         owners=("T",), tools=("soap_clustering",), open="how many per cluster", skill="dissociation-final-state"),
    Step("7", "Uncertainty estimation", "select", 5,
         detail="Disagreement across the committee of 1*, calibrated on a few DFT labels if available, else OC20NEB labels; doubt escalates instead of guessing; `mlip-doubt-calibration` says when",
         board="with all relevant models from 1*; agentic uncertainty and DFT as question marks",
         lit_source="MACE committees · uncertainty-toolbox",
         lit="committee variance is cheap; calibration metrics exist; El Agente Potente saw two MLIPs disagree in sign on a reaction energy",
         ours="disagreement calibrated on a few DFT or OC20NEB labels; doubt escalates to the human instead of guessing",
         action="uncertainty_estimation: committee disagreement across the 1* candidates, calibrated on DFT or OC20NEB labels; doubt escalates",
         owners=("T", "S", "L", "H"), tools=("uncertainty_estimation",), ext_tools=("dft_single_points",),
         ext="agentic uncertainty: N planner runs; dft_single_points if D2 allows DFT",
         skill="mlip-doubt-calibration", agents=(("mlip-specialist", "decides trust, repair or escalate from the calibrated doubt"),),
         agent_ext="agentic uncertainty: N planner runs; dft_single_points if D2 allows",
         human="reviews the flagged cases in the question box", checkpoint="review flagged cases",
         board_input="Agentic uncertainty (?), DFT (?)"),
    Step("8", "Rank; user chooses up to 5", "select", 5,
         detail="Cards with rank, doubt and verdicts; the human picks; the choice and its reason go to the case bank",
         board="optional: uncertainty estimates and potential issues; critic and knowledge prompts",
         lit_source="AdsorbML · CatDT",
         lit="top-k then DFT is AdsorbML's recipe; CatDT: a raw case bank scores 68 % against 52 to 54 % for distilled lessons",
         ours="descriptor cards with rank, doubt and verdicts; the choice and reason go to the case bank; only a human promotes a case to a skill",
         action="ranking: nearest first, then energy; one descriptor_card per final state with doubt and verdicts; the human picks; choice and reason to lessons.md",
         owners=("H", "L", "T"), tools=("ranking", "descriptor_card"), open="up to five, or fewer",
         agents=(("solution-planner", "shows the cards and the ranked pictures; asks the pick in the question box"),),
         human="picks up to five in the question box; outside an example, choice and reason to the case bank", checkpoint="pick up to five final states",
         board_input="Critic, knowledge"),
    Step("solution", "Solution", "select", 2,
         detail="The report tool writes the report from the records: the steps in brief, both energies, lateral interaction, each fragment's adsorption energy, survivors and rejections with reasons, recombination rate, doubt, open decisions, decision trace; `final-state-report` holds the format; agents add notes; the human interprets",
         board="final output, with uncertainty and issues alongside",
         lit_source="OC20NEB · AtomisticSkills",
         lit="OC20NEB product frames as the comparison; every parameter logged beside its output; general-peer-review reads the report",
         ours="the nearest non-recombining final state with E(FS near), E(FS ∞), rejections, recombination rate, trace; two numbers and two comparisons",
         action="reference_energies and report: E(FS near), E(FS ∞) from separate cells, rejections with reasons, recombination rate, decision trace",
         owners=("T", "L", "H", "S"), tools=("reference_energies", "report"), ext_tools=("dft_single_points",), open="the pass criterion against the OC20NEB product frame",
         skill="final-state-report; general-peer-review, reused", agents=(("solution-planner", "shows the report and the whole summary"), ("scientific-critic", "reviews the report in its own context before the human reads it")),
         human="interprets the report in the question box", checkpoint="interpret results"),
]

BY_KEY = {s.key: s for s in STEPS}


def code_order_note() -> str:
    pts = [s for s in STEPS if s.is_point]
    run = [s.key for s in sorted((p for p in pts if p.code_order and p.code_order < 5 and not p.deferred), key=lambda p: p.code_order)]
    deferred = [s.key for s in pts if s.deferred]
    alt = [s.key for s in pts if s.code_order == 0]
    inside = [s.key for s in pts if s.code_order == 5]
    note = f"in code: {', '.join(run)}; "
    if deferred:
        note += f"{', '.join(deferred)} deferred; "
    return note + f"{', '.join(alt)} is the alternative; {', '.join(inside)} runs inside step 5"


if __name__ == "__main__":
    for s in STEPS:
        print(f"{s.title:40s} {'/'.join(s.owners):8s} {', '.join(s.tools)}")
    print(code_order_note())
