"""The tool registry: every tool of the pipeline defined once.

A ToolSpec says what a tool is for, which board steps it serves, what it takes and returns, which checks and
thresholds it applies, which library it wraps, what it logs, its status, and the operational facts the server
and the hooks need: version, compute lane, timeout, runtime requirements, the roles allowed to call it, and the
checkpoint that must have passed before it may run. The MCP server builds its tool list from REGISTRY; agent.md
section 3 and the README modules table are generated from it; the tests assert that every spec has a module with
a function of the same name and the same parameter names, that the tool names equal those in the figures' data
module, docs/figures/src/_board.py, and that allowed roles are agents of the roster.

Thresholds marked "open: team decision" are exposed as parameters without defaults and must be asked for.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

OPEN = "open: team decision"
# the category module under fragplace/tools/ that holds each tool, grouped as ChemCrow and Biomni group theirs
CATEGORY = {
            "literature_lookup": "literature",
            "structure_retrieval": "structure",
            "calculation_protocol": "structure",
            "mlip_selection": "uncertainty",
            "uncertainty_estimation": "uncertainty",
            "active_learning": "uncertainty",
            "site_enumeration": "sites",
            "pair_enumeration": "sites",
            "adsorbate_placement": "placement",
            "minima_hopping": "placement",
            "pull_force_screen": "screening",
            "relaxation": "relaxation",
            "reference_energies": "relaxation",
            "anomaly_filter": "filtering",
            "descriptor_card": "filtering",
            "soap_clustering": "clustering",
            "ranking": "clustering",
            "report": "report",
            "dft_single_points": "dft"
}
from .agents import PLANNER  # noqa: E402
LANES = ("laptop", "gpu", "hpc")
CHECKPOINTS = ("approve settings", "approve the plan", "review flagged cases", "pick up to five final states", "interpret results")


@dataclass(frozen=True)
class ToolSpec:
    name: str                                   # function and module name under fragplace/tools/
    board_steps: Tuple[str, ...]                # keys of the board: "prompt", "1", "1*", "2", "3.1" .. "3.6", "4" .. "8", "solution"
    purpose: str
    inputs: Dict[str, str]                      # parameter name -> record or type, with units in the name
    outputs: Dict[str, str]
    checks: Tuple[str, ...] = ()
    thresholds: Dict[str, str] = field(default_factory=dict)
    wraps: Tuple[str, ...] = ()
    logs: Tuple[str, ...] = ()
    status: str = "core"                        # core | extension | later
    version: str = "0.1.0"                      # enters the cache key and the trace
    lane: str = "laptop"                        # laptop | gpu | hpc
    timeout_s: int = 600
    requires: Tuple[str, ...] = ()              # module:name, exe:name, env:NAME, weights:name
    allowed_roles: Tuple[str, ...] = (PLANNER,) # the agents that may call it
    checkpoint_gate: Optional[str] = None       # the checkpoint that must have passed before it runs
    read_only: bool = False                     # writes nothing but the trace
    cacheable: bool = False                     # keyed on structure, calculator, settings hash and version

    @property
    def module(self) -> str:
        return f"fragplace.tools.{CATEGORY[self.name]}"


REGISTRY: List[ToolSpec] = [
    ToolSpec(
        name="literature_lookup", board_steps=("prompt", "3.2"),
        purpose="Published E_ads values with functional and site, and the length d of the bond to break, for a human to verify; one or two values, never from the model's memory.",
        inputs={"system": "str, metal, facet, adsorbate", "quantity": "E_ads | bond_length_d | site", "sources": "list of source names"},
        outputs={"values": "list[LiteratureValue], verified_by_human False until the checkpoint"},
        checks=("every value carries a DOI or URL", "at most two values per quantity"),
        wraps=("paper-qa2 for papers", "Materials Project API through the LLaMP pattern", "Catalysis-Hub"),
        logs=("query", "every value with its source"),
        lane="laptop", timeout_s=300, requires=("module:paperqa", "module:mp_api", "env:MP_API_KEY"),
        allowed_roles=("literature-reader",), read_only=True),
    ToolSpec(
        name="structure_retrieval", board_steps=("1",),
        purpose="Take the three supplied relaxed structures with their energies, cleave the named bond to make A and B, and select the surface cell so periodic images stay apart.",
        inputs={"slab": "StructureRef", "adsorbate_vacuum": "StructureRef", "initial_state": "StructureRef", "bond_to_break": "tuple[int, int], atom indices in AB"},
        outputs={"fragment_A": "StructureRef", "fragment_B": "StructureRef", "cell_repeat": "tuple[int, int]", "structures": "list[StructureRef]"},
        checks=("the three inputs share one settings set, check 8", "images at least min_image_distance_A apart"),
        thresholds={"min_image_distance_A": "10"},
        wraps=("ase.io", "pymatgen.core"), logs=("input hashes", "the cell and why"),
        requires=("module:ase", "module:pymatgen"), allowed_roles=("computational-chemist", PLANNER)),
    ToolSpec(
        name="calculation_protocol", board_steps=("1",),
        purpose="Lock the numerical and physical settings in PROJECT.md from the inputs' settings, the human's physics choices and a verified protocol; never from the model's memory.",
        inputs={"settings_from_inputs": "Settings, as read from the relaxed inputs", "physics_choices": "dict from the human: functional, dispersion, spin, U", "protocol": "aiida_common_workflows | sssp | oc20", "protocol_reason": "str, stated by the computational chemist"},
        outputs={"settings": "Settings with locked False until the human approves"},
        checks=("cutoff, k-mesh, smearing, layers from the protocol table of agent.md section 3", "if OC20NEB is the benchmark, RPBE and PAW as OC20"),
        thresholds={"convergence_target_meV": OPEN, "gas_references": OPEN},
        wraps=("aiida_common_workflows.workflows.relax.CommonRelaxWorkChain protocols", "SSSP", "pymatgen.io.vasp.sets.MPRelaxSet"),
        logs=("protocol and reason", "every setting and its origin"),
        allowed_roles=("computational-chemist", PLANNER)),
    ToolSpec(
        name="mlip_selection", board_steps=("1*",),
        purpose="Benchmark two or three candidate potentials on the system class and choose one; every candidate becomes the committee of uncertainty_estimation.",
        inputs={"candidates": "list[str], calculator names", "system_class": "str, metal | oxide | organometallic", "labels": "list[StructureRef] with DFT energies, or OC20NEB"},
        outputs={"chosen": "str", "committee": "list[str]", "benchmark": "dict name -> error_eV and anomaly classes"},
        checks=("spin initialised on Co and Ni", "cross-family comparison on E_ads only, never total energies"),
        thresholds={"candidates": OPEN, "label_count": OPEN},
        wraps=("catbench.adsorption.AdsorptionCalculation", "catbench.adsorption.AdsorptionAnalysis", "AtomisticSkills ml-mlip-benchmark", "fairchem.core.FAIRChemCalculator", "mace.calculators.MACECalculator", "chgnet"),
        logs=("benchmark results", "the choice and the specialist's reason"),
        lane="gpu", timeout_s=7200, requires=("module:catbench", "module:fairchem.core", "env:HF_TOKEN", "weights:uma-s-1p2p1"),
        allowed_roles=("mlip-specialist",), checkpoint_gate="approve settings", cacheable=True),
    ToolSpec(
        name="site_enumeration", board_steps=("2",),
        purpose="Every symmetry-inequivalent site of the slab, fcc and hcp hollows apart, with the site graph and a Burnside-checked count; pymatgen's finder as the baseline.",
        inputs={"slab": "StructureRef", "cell_repeat": "tuple[int, int]"},
        outputs={"sites": "SiteEnumeration"},
        checks=("Burnside count equals the explicit list", "C4v square cell with two identical adsorbates gives 2"),
        wraps=("spglib.get_symmetry_dataset", "acat.adsorption_sites.SlabAdsorptionSites", "acat.adsorption_sites.SlabAdsorptionSites.get_graph", "pymatgen.core.adsorption.AdsorbateSiteFinder as baseline"),
        logs=("symmetry group", "every site", "count and check"),
        requires=("module:spglib", "module:acat"), checkpoint_gate="approve the plan", cacheable=True),
    ToolSpec(
        name="adsorbate_placement", board_steps=("3.5", "4"),
        purpose="Place fragment A at every symmetry-distinct site near its old site and B at a given site, by script; orientations under the site's stabiliser; a random displacement before relaxation.",
        inputs={"sites": "SiteEnumeration", "fragment": "StructureRef", "site_index": "int", "orientation": "int", "height_A": "float", "displacement_amplitude_A": "float", "base": "Candidate | None, the candidate the fragment is added to; the slab of the enumeration when None"},
        outputs={"candidate": "Candidate"},
        checks=("start 2 to 3 Å above the site", "the LLM never places atoms"),
        thresholds={"displacement_amplitude_A": OPEN, "fragment_A_fixed_at_old_site": OPEN},
        wraps=("ase.build.add_adsorbate", "fairchem.data.oc.core.AdsorbateSlabConfig as the baseline"),
        logs=("site, orientation, height, displacement and random draw",),
        requires=("module:ase",), checkpoint_gate="approve the plan"),
    ToolSpec(
        name="pair_enumeration", board_steps=("3.2",),
        purpose="Every symmetry-distinct (A site, B site) pair inside the window [1.5 d, 5] Å, ordered by site-graph distance with in-plane distance as tiebreaker, nearest first, counted.",
        inputs={"sites": "SiteEnumeration", "d_bond_A": "float, from literature_lookup or the adsorbate structure", "window": "tuple[float, float] in units of d and Å"},
        outputs={"pairs": "list[Pair], nearest first", "count": "int"},
        checks=("no pair outside the window", "symmetry duplicates removed and counted"),
        thresholds={"d_definition": OPEN + ": vacuum or adsorbed bond length", "upper_bound_A": OPEN + ": 5 or NEBscape's 4.5"},
        wraps=("acat.adsorption_sites.SlabAdsorptionSites.get_neighbor_site_list", "acat.build.adlayer.SystematicPatternGenerator"),
        logs=("every pair with both distances", "the count"),
        requires=("module:acat",), checkpoint_gate="approve the plan", cacheable=True),
    ToolSpec(
        name="pull_force_screen", board_steps=("3.3",),
        purpose="One MLIP force call per pair; the force on B along the A–B axis; a pull towards A above the threshold queues the pair last, never drops it.",
        inputs={"candidates": "list[Candidate]", "calculator": "str"},
        outputs={"screens": "list[ForceScreen], queue order"},
        checks=("one force call, no relaxation",),
        thresholds={"threshold_eV_per_A": OPEN},
        wraps=("fragplace.calculators",), logs=("force per pair", "queue order"),
        lane="gpu", timeout_s=3600, requires=("module:ase",), checkpoint_gate="approve the plan", cacheable=True),
    ToolSpec(
        name="minima_hopping", board_steps=("3.6",),
        purpose="NEBscape's endpoint generator with the chosen potential as the alternative generator and the baseline policy our nearest-first choice is scored against.",
        inputs={"slab": "StructureRef", "fragments": "tuple[StructureRef, StructureRef]", "calculator": "str", "n_hops": "int"},
        outputs={"candidates": "list[Candidate] with generator minima_hopping"},
        checks=("Hookean constraints keep A and B intact during hopping, as NEBscape",),
        wraps=("nebscape endpoint generator, MIT", "ase.optimize.minimahopping.MinimaHopping"),
        logs=("hops", "minima found"),
        lane="gpu", timeout_s=14400, requires=("module:nebscape", "module:ase"), checkpoint_gate="approve the plan", cacheable=True),
    ToolSpec(
        name="relaxation", board_steps=("4",),
        purpose="Relax every candidate with the chosen potential and the locked settings, random displacement first; cached by content hash.",
        inputs={"candidates": "list[Candidate]", "calculator": "str", "fmax_eV_per_A": "float", "max_steps": "int"},
        outputs={"results": "list[RelaxationResult]"},
        checks=("same settings as the initial state, check 8",),
        wraps=("ase.optimize", "fragplace.calculators", "fragplace.cache"),
        logs=("steps, fmax, convergence, cache hit per candidate",),
        lane="gpu", timeout_s=14400, requires=("module:ase",), checkpoint_gate="approve the plan", cacheable=True),
    ToolSpec(
        name="anomaly_filter", board_steps=("5", "3.1"),
        purpose="The nine checks of the gate per fragment, before and after relaxation, plus the two final-state checks: the A–B bond re-formed, and the periodic image; verdict into the card; a failing candidate is never kept.",
        inputs={"candidate": "Candidate", "start": "Candidate", "slab": "StructureRef", "settings": "Settings", "prior_E_ads_eV": "float | None", "frequencies_cm": "list[float] | None"},
        outputs={"gate": "GateResult"},
        checks=("1 desorbed per fragment", "2 migrated", "3 dissociated within a fragment", "4 reconstructed", "5 not a minimum", "6 magnetism collapsed", "7 outside expected range", "8 settings mismatch", "9 intercalated", "10 A–B bond re-formed", "11 periodic image"),
        thresholds={"desorbed_A": "3", "AB_bond_reformed_A": OPEN, "migrated": OPEN, "dissociated": OPEN, "reconstructed": OPEN, "imaginary_noise_cm": OPEN, "expected_range_width_eV": OPEN, "magnetism_collapsed": OPEN, "intercalated": OPEN},
        wraps=("fairchem.data.oc.utils.DetectTrajAnomaly", "ase.vibrations.Vibrations", "acat.adsorbate_coverage.SlabAdsorbateCoverage", "CatBench anomaly classes as names"),
        logs=("every verdict with its measured value", "every rejection with its reason"),
        requires=("module:fairchem.data", "module:ase", "module:acat"), checkpoint_gate="approve the plan"),
    ToolSpec(
        name="soap_clustering", board_steps=("6",),
        purpose="Cluster the survivors by SOAP; keep the nearest and the lowest per cluster; nearest first overall.",
        inputs={"survivors": "list[Candidate]", "energies": "list[RelaxationResult]", "pairs": "list[Pair]"},
        outputs={"clusters": "list[Cluster]", "kept": "list[str]"},
        checks=("nearest-first ordering preserved across clusters",),
        thresholds={"per_cluster": OPEN + ": the board says 3, could be more"},
        wraps=("dscribe.descriptors.SOAP", "sklearn.cluster"), logs=("clusters and representatives",),
        requires=("module:dscribe", "module:sklearn"), checkpoint_gate="approve the plan"),
    ToolSpec(
        name="uncertainty_estimation", board_steps=("7",),
        purpose="Committee disagreement across the candidates benchmarked at 1*, calibrated on a few DFT or OC20NEB labels; a doubt flag that escalates to the human instead of guessing.",
        inputs={"candidates": "list[Candidate]", "committee": "list[str]", "labels": "list[StructureRef] | None"},
        outputs={"flags": "list[DoubtFlag]"},
        checks=("disagreement compared on E_ads, never on total energies across families", "magnetic metals always flagged", "unseen chemistry always flagged"),
        thresholds={"escalation_threshold_eV": OPEN, "label_count": OPEN},
        wraps=("mace.calculators.MACECalculator with model_paths", "uncertainty_toolbox.metrics.get_all_metrics", "AtomisticSkills ml-committee-uncertainty"),
        logs=("labels used", "spread against label error", "every flag and escalation"),
        lane="gpu", timeout_s=7200, requires=("module:mace", "module:uncertainty_toolbox"),
        allowed_roles=("mlip-specialist",), checkpoint_gate="approve the plan", cacheable=True),
    ToolSpec(
        name="descriptor_card", board_steps=("3.4", "5", "8"),
        purpose="Render a structure as the text card the LLM reads, with site, distances, verdicts and the A–B distance; a PNG beside it as a second look.",
        inputs={"candidate": "Candidate", "gate": "GateResult | None", "sites": "SiteEnumeration"},
        outputs={"card": "DescriptorCard"},
        checks=("two configurations never share a card: distances and site labels always present",),
        wraps=("pymatgen", "robocrystallographer pattern", "ase.io.write png"), logs=("the card beside the structure",),
        requires=("module:pymatgen", "module:ase"), allowed_roles=(PLANNER, "surface-chemist", "scientific-critic"), read_only=True),
    ToolSpec(
        name="ranking", board_steps=("8",),
        purpose="Rank the kept final states nearest first, then by energy, with doubt and verdicts on each card, for the human to pick up to five; record the choice and reason in the case bank.",
        inputs={"kept": "list[str]", "cards": "list[DescriptorCard]", "flags": "list[DoubtFlag]", "pairs": "list[Pair]"},
        outputs={"ranked": "list[RankedCandidate]"},
        checks=("the human picks; the tool never drops a candidate",),
        thresholds={"shortlist_size": OPEN + ": up to five, or fewer"},
        wraps=(), logs=("the order shown", "the human's choice and reason, to lessons.md"),
        checkpoint_gate="review flagged cases"),
    ToolSpec(
        name="reference_energies", board_steps=("solution",),
        purpose="E(A*), E(B*) and E(slab) each in its own cell with the chosen potential and the locked settings, for E(FS ∞) and the lateral interaction.",
        inputs={"slab": "StructureRef", "fragments": "tuple[StructureRef, StructureRef]", "calculator": "str"},
        outputs={"E_slab_eV": "float", "E_A_eV": "float", "E_B_eV": "float", "E_inf_eV": "float"},
        checks=("same settings as every candidate, check 8",), wraps=("fragplace.calculators",), logs=("the three energies",),
        lane="gpu", timeout_s=3600, requires=("module:ase",), checkpoint_gate="pick up to five final states", cacheable=True),
    ToolSpec(
        name="report", board_steps=("solution",),
        purpose="One auditable record per campaign: final states with both energies, rejections with reasons, the recombination rate, doubt, the OC20NEB comparison, cost and the decision trace.",
        inputs={"campaign": "str", "final_states": "list[FinalState]", "rejected": "list[GateResult]", "flags": "list[DoubtFlag]", "comparison": "dict"},
        outputs={"report": "Report, written to runs/<campaign>/report.md and report.json"},
        checks=("every number traces to a tool output", "the scientific critic reads the draft with the general-peer-review skill"),
        wraps=("AtomisticSkills hyperparameter logging pattern",), logs=("the full trace path",),
        allowed_roles=(PLANNER, "scientific-critic"), checkpoint_gate="pick up to five final states"),
    ToolSpec(
        name="dft_single_points", board_steps=("7", "solution"),
        purpose="DFT single points on the chosen final states and the separated fragments at the locked settings; only with a DFT code and compute.",
        inputs={"structures": "list[StructureRef]", "settings": "Settings", "backend": "local | slurm"},
        outputs={"energies": "dict candidate_id -> eV", "failures": "list[str]"},
        checks=("settings mismatch against PROJECT.md before submission", "custodian handlers before any agent diagnosis", "retries capped at three by the job tracker"),
        wraps=("ase.calculators", "atomate2 through the AtomisticSkills MCP server", "custodian.vasp.handlers", "fragplace.execution.tracker"),
        logs=("force calls, failures, every resubmission",), status="extension",
        lane="hpc", timeout_s=86400, requires=("exe:vasp_std or pw.x", "module:custodian"),
        allowed_roles=(PLANNER, "dft-recovery-agent"), checkpoint_gate="pick up to five final states"),
    ToolSpec(
        name="active_learning", board_steps=("1*",),
        purpose="High doubt to a few DFT labels to a fine-tuned potential to a re-run of steps 4 to 8.",
        inputs={"flags": "list[DoubtFlag]", "labels": "list[StructureRef]", "base_model": "str"},
        outputs={"fine_tuned": "str"},
        wraps=("AtomisticSkills ml-mace-finetune",), logs=("labels used", "model path"), status="extension",
        lane="gpu", timeout_s=86400, requires=("module:mace",), allowed_roles=("mlip-specialist",), checkpoint_gate="review flagged cases"),
]

BY_NAME: Dict[str, ToolSpec] = {t.name: t for t in REGISTRY}
CORE = [t for t in REGISTRY if t.status == "core"]


def for_step(key: str) -> List[ToolSpec]:
    return [t for t in REGISTRY if key in t.board_steps]


def for_role(role: str) -> List[ToolSpec]:
    return [t for t in REGISTRY if role in t.allowed_roles]
