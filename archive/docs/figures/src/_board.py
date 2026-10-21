"""The single source of truth for the pipeline figures and the README tables.

One record per step of the team's board of 21 October 2026, in the board's order and numbering, plus the
input prompt. Every figure script imports STEPS; board_tables.py writes the README tables from it;
board_check.py asserts that every figure and the README carry the same names. Change a word here, never
in a figure script.

Field notes:
- owners: tuple of H, L, S, T; the first does the work and equals the Owner column of agent.md section 2.
- action: the one line a figure prints under the step name: the tool and what it does.
- open: the one headline open decision shown as the amber tag; agent.md section 11 holds the full list.
- ext: the extension at this step, dashed purple in every figure.
- code_order: for the six points of step 3, the order the code runs them; 0 means the alternative.
- checkpoint: one of CHECKPOINTS. The placement of "approve the plan" after 1* is the team's to confirm.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

BOARD_DATE = "21 October 2026"
CHECKPOINTS = ("approve settings", "approve the plan", "review flagged cases", "pick up to five final states", "interpret results")
AGENTS = {
    "final-state-planner": "the next tool call and when to stop; holds the checkpoint list; calls every tool by name, reads cards, never writes coordinates",
    "dft-settings-interviewer": "what the Formulate interview locks into PROJECT.md; runs once, before the run",
    "geometry-critic": "the site type and orientation to try per fragment; whether a card and its verdicts disagree; never overrides a check",
    "dft-job-steward": "resubmit, adjust or escalate a failed DFT job; only with HPC",
}
SKILLS_OURS = ("dft-settings-protocol", "mlip-doubt-calibration", "dissociation-final-state", "final-state-report", "hpc-dft-jobs")
SKILLS_REUSED = ("ml-committee-uncertainty", "ml-mlip-benchmark", "ml-mace-finetune", "chem-thermochemistry", "general-peer-review")
TOOLS = ("dft_settings_lock", "mlip_choice", "site_enumeration", "adsorbate_placement", "validity_gate",
         "descriptor_card", "mlip_doubt", "dissociation_final_state", "final_state_report", "dft_single_points")
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
    open: Optional[str] = None
    ext: Optional[str] = None
    skill: Optional[str] = None
    agent: Optional[Tuple[str, str]] = None      # (name, what it does here)
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
         board="surf + adsorbates (2) + a general system description; surface and adsorbate with their energies, E_ads from the literature",
         lit_source="Get Physics Done · AutoDFT",
         lit="a Formulate interview that locks scope, conventions and verification targets; compact written settings rules, such as spin for Ni and Co",
         ours="the interviewer asks five fixed questions and writes PROJECT.md; the three relaxed inputs and A, B as structures are supplied",
         action="dft-settings-interviewer: five fixed questions, answers into PROJECT.md",
         owners=("H", "L", "S"), tools=(), skill="dft-settings-protocol",
         agent=("dft-settings-interviewer", "asks the fixed questions, writes PROJECT.md"),
         human="supplies the surface, the adsorbates and a description; answers the five interview questions",
         board_input="Critic, knowledge prompts"),
    Step("1", "Structure retriever", "setup", 1,
         board="fed by the input prompt: surf + adsorbates (2) and a general system description; surface and adsorbate with their energies",
         lit_source="AiiDA common workflows · SSSP · OC20",
         lit="numerical settings come from a verified protocol, never from the model; OC20's RPBE and PAW if the benchmark is OC20NEB",
         ours="the three relaxed inputs plus A and B as structures; settings locked in PROJECT.md; a cell wide enough for the pair",
         action="dft_settings_lock: the three relaxed inputs, A and B as structures, the cell; settings locked in PROJECT.md",
         owners=("T", "H", "S"), tools=("dft_settings_lock",), open="one set of gas references for AB, A and B",
         skill="dft-settings-protocol", agent=("final-state-planner", "picks the protocol and states why"),
         human="approves the settings lock", checkpoint="approve settings"),
    Step("1*", "MLIP selection, AL prospect", "setup", 1,
         board="chosen before placement so step 3 can use it; active learning as a prospect",
         lit_source="80-MLIP survey · CatBench · AtomisticSkills",
         lit="no potential is best everywhere; CatBench classes each failure; ml-mlip-benchmark scores candidates on the system class",
         ours="benchmark two or three, record why; spin for Ni and Co; the candidates become the committee of step 7",
         action="mlip_choice: two or three candidates benchmarked on the system class; the chosen one relaxes, all form the committee of step 7",
         owners=("T", "L", "S", "H"), tools=("mlip_choice",), ext="active learning: doubt → a few DFT labels → fine-tune → re-run",
         skill="ml-mlip-benchmark, reused", agent=("final-state-planner", "records the choice and the reason"),
         human="approves the plan", checkpoint="approve the plan"),
    Step("2", "Adsorption sites with pymatgen", "setup", 3,
         board="Python, with pymatgen",
         lit_source="pymatgen · ACAT · spglib",
         lit="pymatgen's site finder labels no fcc or hcp hollow; ACAT gives labelled sites and the site graph; spglib the symmetry operations",
         ours="symmetry-complete and counted; fcc and hcp apart; pymatgen kept as the baseline",
         action="site_enumeration: symmetry-inequivalent sites, fcc and hcp apart, counted; pymatgen as the baseline",
         owners=("T",), tools=("site_enumeration",)),
    Step("3.1", "Least distance before pull-back", "step3", 4,
         board="estimate the minimum distance at which the dissociated atom is not pulled back",
         lit_source="CatTSunami · NEBscape",
         lit="CatTSunami treats a bond as breaking at 1.25 to 1.63× its length; NEBscape keeps fragments intact by Hookean constraint during sampling",
         ours="the bond-re-formed check as code, after relaxation, with a logged reason; a pair that fails is never kept",
         action="validity_gate, check 10: the A–B bond re-formed after relaxation; runs inside step 5",
         owners=("T",), tools=("validity_gate",), open="the A–B distance threshold",
         skill="dissociation-final-state", code_order=5),
    Step("3.2", "Window [1.5 d, 5] Å", "step3", 4,
         board="d the max vdW length of the bond to break, from the literature",
         lit_source="NEBscape · CatTSunami",
         lit="NEBscape excludes separations above 4.5 Å; CatTSunami samples a 1 to 3 Å shell, 25 pairs, one survivor at random",
         ours="every symmetry-distinct pair inside the window, ordered by site-graph distance, nearest first, counted: the objective is explicit",
         action="dissociation_final_state: every symmetry-distinct A–B pair in [1.5 d, 5] Å, nearest first by site-graph distance, counted",
         owners=("T",), tools=("dissociation_final_state", "site_enumeration"),
         open="d from vacuum or from the adsorbed molecule; 5 Å or NEBscape's 4.5 Å",
         skill="dissociation-final-state", code_order=2),
    Step("3.3", "Pull force with the MLIP", "step3", 4,
         board="use the selected MLIP to estimate the pull force on the binding fragment",
         lit_source="NEBscape · CatTSunami",
         lit="neither screens by force; both relax every candidate they generate",
         ours="one force call per pair before relaxing; a pull towards the other fragment queues the pair last, never drops it",
         action="dissociation_final_state: one MLIP force call per pair; a pull towards the other fragment queues the pair last",
         owners=("T",), tools=("dissociation_final_state", "mlip_choice"), open="the force threshold",
         skill="dissociation-final-state", code_order=3),
    Step("3.4", "Agentic critique of the cleavage", "step3", 5,
         board="criticise and adjust the placement from knowledge of what the cleavage does",
         lit_source="AdsMind · AtomWorld · ChemCrow",
         lit="AdsMind: the LLM returns a site type, code places, 98.8 %; AtomWorld: LLM coordinate edits fail; an LLM judge rates fluent wrong answers well",
         ours="geometry-critic reads descriptor cards, proposes a site type per fragment, orders the list; never edits coordinates, never overrides a check",
         action="geometry-critic reads descriptor_card text, proposes a site type and orientation per fragment, reorders; never edits coordinates",
         owners=("L", "T"), tools=("descriptor_card",),
         ext="a vision model to predict the sites, only after the geometry benchmark shows an image helps",
         skill="dissociation-final-state", agent=("geometry-critic", "proposes a site type per fragment, orders the list; never overrides a check"),
         board_input="Critic, knowledge; Vision model (?)", code_order=4),
    Step("3.5", "Site and orientation, pymatgen", "step3", 3,
         board="agentic knowledge or a package such as pymatgen, so the binding fragment adsorbs",
         lit_source="El Agente Potente · CatTSunami",
         lit="symmetry-distinct sites and orientations enumerated by code; CatTSunami: 5 placements within 2 Å of the old binding site",
         ours="code places, the LLM never does: the fragment keeping the binding atom at symmetry-distinct sites near its old site, counted",
         action="adsorbate_placement: A at every symmetry-distinct site near its old site, counted; A fixed is the cheap baseline",
         owners=("T",), tools=("adsorbate_placement", "dissociation_final_state"),
         open="the binding fragment fixed at its old site, or enumerated",
         skill="dissociation-final-state", code_order=1),
    Step("3.6", "Or minima hopping with the MLIP", "step3", 5,
         board="alternatively, minima hopping with the selected MLIP for the binding fragment",
         lit_source="NEBscape",
         lit="minima hopping from symmetry-inequivalent sites with Hookean constraints; 94 % of 304 OC20NEB reactions converge; MIT code",
         ours="kept as the alternative generator, wrapped, and as the baseline policy our nearest-first choice is scored against",
         action="dissociation_final_state: NEBscape's endpoint generator with the chosen MLIP, the alternative and the baseline policy",
         owners=("T",), tools=("dissociation_final_state",), skill="dissociation-final-state", code_order=0),
    Step("4", "Initial configurations", "select", 4,
         board="output of step 3: all degrees of freedom of the adsorbate × all sites",
         lit_source="Burnside · symmetry trap",
         lit="the count checked by Burnside's lemma; a small random displacement before relaxing, or a symmetric start relaxes to a saddle",
         ours="every candidate pair relaxed with the chosen potential and the locked settings, displacement first",
         action="dissociation_final_state: relax every pair with the chosen MLIP and the locked settings, random displacement first; Burnside-counted",
         owners=("T",), tools=("dissociation_final_state", "site_enumeration", "adsorbate_placement"),
         open="the displacement amplitude", skill="dissociation-final-state"),
    Step("5", "Physics-based and anomaly filtering", "select", 4,
         board="physics by script; anomaly by ML and/or script; reasoning questions injected",
         lit_source="AdsorbML in fairchem",
         lit="four anomaly checks exist; the desorbed check treats A* + B* as one adsorbate and misses B leaving while A stays",
         ours="nine checks as code, per fragment, before and after relaxation; the ML variant not taken; every rejection logged with its reason",
         action="validity_gate: nine checks per fragment plus two final-state checks, before and after relaxation; verdict into the card; rejections logged",
         owners=("T",), tools=("validity_gate", "descriptor_card"),
         ext="an LLM critic reads the card and comments; it never overrides a check",
         skill="dissociation-final-state", agent_ext="geometry-critic: comments on cards, never overrides",
         board_input="Reasoning questions"),
    Step("6", "SOAP clustering", "select", 5,
         board="pick the 3 lowest-energy configurations from each cluster, could be more",
         lit_source="NEBscape",
         lit="deduplicates by SOAP and keeps the first two energy–distance Pareto fronts within 1.2 eV",
         ours="cluster the survivors; keep the nearest and the lowest per cluster; nearest first overall",
         action="dissociation_final_state: SOAP clusters of the survivors; the nearest and the lowest per cluster; E(FS near), E(FS ∞)",
         owners=("T",), tools=("dissociation_final_state",), open="how many per cluster", skill="dissociation-final-state"),
    Step("7", "Uncertainty estimation", "select", 5,
         board="with all relevant models from 1*; agentic uncertainty and DFT as question marks",
         lit_source="MACE committees · uncertainty-toolbox",
         lit="committee variance is cheap; calibration metrics exist; El Agente Potente saw two MLIPs disagree in sign on a reaction energy",
         ours="disagreement calibrated on a few DFT or OC20NEB labels; doubt escalates to the human instead of guessing",
         action="mlip_doubt: committee disagreement across the 1* candidates, calibrated on DFT or OC20NEB labels; doubt escalates",
         owners=("T", "S", "L", "H"), tools=("mlip_doubt",),
         ext="agentic uncertainty: N planner runs; DFT single points if D2 allows DFT",
         skill="mlip-doubt-calibration", agent=("final-state-planner", "stops on doubt and asks"),
         agent_ext="agentic uncertainty: N planner runs; DFT single points if D2 allows",
         human="reviews the flagged cases", checkpoint="review flagged cases",
         board_input="Agentic uncertainty (?), DFT (?)"),
    Step("8", "Rank; user chooses up to 5", "select", 5,
         board="optional: uncertainty estimates and potential issues; critic and knowledge prompts",
         lit_source="AdsorbML · CatDT",
         lit="top-k then DFT is AdsorbML's recipe; CatDT: a raw case bank scores 68 % against 52 to 54 % for distilled lessons",
         ours="descriptor cards with rank, doubt and verdicts; the choice and reason go to the case bank; only a human promotes a case to a skill",
         action="descriptor_card: one card per final state with rank, doubt and verdicts; the human picks; choice and reason to lessons.md",
         owners=("H", "L", "T"), tools=("descriptor_card",), open="up to five, or fewer",
         agent=("final-state-planner", "shows the cards with rank, doubt and verdicts"),
         human="picks up to five on the cards; choice and reason to the case bank", checkpoint="pick up to five final states",
         board_input="Critic, knowledge"),
    Step("solution", "Solution", "select", 2,
         board="final output, with uncertainty and issues alongside",
         lit_source="OC20NEB · AtomisticSkills",
         lit="OC20NEB product frames as the comparison; every parameter logged beside its output; general-peer-review reads the report",
         ours="the nearest non-recombining final state with E(FS near), E(FS ∞), rejections, recombination rate, trace; two numbers and two comparisons",
         action="final_state_report: E(FS near), E(FS ∞), rejections with reasons, recombination rate, decision trace",
         owners=("L", "T", "H", "S"), tools=("final_state_report",), open="the pass criterion against the OC20NEB product frame",
         skill="final-state-report; general-peer-review, reused", agent=("final-state-planner", "drafts the report"),
         human="interprets the report", checkpoint="interpret results"),
]

BY_KEY = {s.key: s for s in STEPS}


def code_order_note() -> str:
    pts = [s for s in STEPS if s.is_point]
    run = [s.key for s in sorted((p for p in pts if p.code_order and p.code_order < 5), key=lambda p: p.code_order)]
    alt = [s.key for s in pts if s.code_order == 0]
    inside = [s.key for s in pts if s.code_order == 5]
    return f"in code: {', '.join(run)}; {', '.join(alt)} is the alternative; {', '.join(inside)} runs inside step 5"


if __name__ == "__main__":
    for s in STEPS:
        print(f"{s.title:40s} {'/'.join(s.owners):8s} {', '.join(s.tools)}")
    print(code_order_note())
