"""Typed records that every tool reads and writes. One class per thing the pipeline passes between steps.

The LLM never sees a structure; it sees a DescriptorCard. Every number a tool reports lives in one of
these records, so the decision trace can point at it. Units are in the field names where they matter.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class Role(str, Enum):
    slab = "slab"
    adsorbate_vacuum = "adsorbate_vacuum"
    initial_state = "initial_state"
    fragment_A = "fragment_A"          # keeps the binding atom, the team's adsorbent #1
    fragment_B = "fragment_B"          # the dissociated part, adsorbent #2
    candidate = "candidate"
    reference = "reference"


class StructureRef(BaseModel):
    """A structure on disk, never in the prompt."""
    path: str
    format: str = "extxyz"
    role: Role
    energy_eV: Optional[float] = None
    settings_hash: Optional[str] = Field(None, description="hash of the Settings the structure was relaxed with")
    calculator: Optional[str] = None


class GasReference(BaseModel):
    species: str                     # "H2", "O2", "CO2", "AB", "A", "B"
    energy_eV: float
    correction_eV: float = 0.0
    note: str = ""


class Settings(BaseModel):
    """The locked numerical and physical settings of a campaign; written to PROJECT.md by calculation_protocol."""
    metal: str
    facet: str
    adsorbate: str                   # AB
    product: Tuple[str, str]         # (A, B)
    functional: str                  # PBE, RPBE, BEEF-vdW
    dispersion: Optional[str] = None
    spin_polarised: bool = False
    initial_moments: Dict[str, float] = Field(default_factory=dict)
    hubbard_u: Dict[str, float] = Field(default_factory=dict)
    pseudopotential_family: Optional[str] = None
    pseudopotential_version: Optional[str] = None
    cutoff_eV: Optional[float] = None
    kmesh: Optional[Tuple[int, int, int]] = None
    smearing: Optional[str] = None
    sigma_eV: Optional[float] = None
    layers: Optional[int] = None
    fixed_layers: Optional[int] = None
    vacuum_A: Optional[float] = None
    dipole_correction: bool = True
    cell_repeat: Optional[Tuple[int, int]] = None
    min_image_distance_A: float = 10.0
    force_threshold_eV_per_A: float = 0.03
    scf_threshold_eV: float = 1e-5
    convergence_target_meV: Optional[float] = Field(None, description="open: team decision, 10 or 25")
    gas_references: List[GasReference] = Field(default_factory=list)
    protocol: Optional[str] = Field(None, description="which protocol library or sweep the values come from")
    protocol_reason: Optional[str] = Field(None, description="the planner's stated reason for the protocol")
    mlip: Optional[str] = None
    mlip_committee: List[str] = Field(default_factory=list)
    decisions: Dict[str, Any] = Field(default_factory=dict, description="every threshold marked 'open: team decision', keyed <tool>.<name>, set by the team and locked with the rest")
    locked: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class LiteratureValue(BaseModel):
    quantity: str                    # "E_ads", "bond_length_d", "site"
    value: float
    unit: str
    system: str
    functional: Optional[str] = None
    site: Optional[str] = None
    source: str                      # DOI or URL
    verified_by_human: bool = False


class Site(BaseModel):
    index: int
    label: str                       # "fcc", "hcp", "bridge", "top", "4fold"
    point_group: str                 # "C3v", "C2v", "C4v"
    coordination: int
    atom_beneath: Optional[str] = None
    position: Tuple[float, float, float]
    orbit: int = Field(0, description="sites with the same orbit are symmetry-equivalent")
    anchor_atoms: List[int] = Field(default_factory=list, description="indices of the slab atoms that define the site")


class SymmetryOperation(BaseModel):
    """One operation of the slab's symmetry group in Cartesian coordinates: x' = R x + t."""
    rotation: List[List[float]]
    translation: List[float]


class SiteEnumeration(BaseModel):
    sites: List[Site]
    count: int                       # the symmetry-inequivalent sites: the number of orbits
    burnside_count: int              # the same number from Burnside's lemma; must equal count
    symmetry_group: str
    edges: List[Tuple[int, int]] = Field(default_factory=list, description="site-graph edges between neighbouring sites")
    baseline_count: Optional[int] = Field(None, description="pymatgen's count for the same slab")
    slab: Optional[StructureRef] = Field(None, description="the slab the sites were found on, with cell_repeat applied")
    operations: List[SymmetryOperation] = Field(default_factory=list, description="the operations the orbits were formed under")
    total_sites: int = Field(0, description="every site in the cell, before symmetry reduction")


class Candidate(BaseModel):
    id: str
    structure: StructureRef
    site_A: Optional[int] = None
    site_B: Optional[int] = None
    orientation: Optional[int] = None
    displacement_amplitude_A: float = 0.0
    generator: str = "enumeration"   # enumeration | minima_hopping | baseline
    parent: Optional[str] = None


class Pair(BaseModel):
    candidate_id: str
    site_A: int
    site_B: int
    site_graph_distance: int
    in_plane_distance_A: float
    within_window: bool
    window_A: Tuple[float, float]
    d_bond_A: float


class ForceScreen(BaseModel):
    candidate_id: str
    force_on_B_along_AB_eV_per_A: float
    flagged: bool
    threshold_eV_per_A: Optional[float] = Field(None, description="open: team decision")
    queue_position: int


class RelaxationResult(BaseModel):
    candidate_id: str
    energy_eV: float
    fmax_eV_per_A: float
    steps: int
    converged: bool
    trajectory_path: Optional[str] = None
    calculator: str
    cache_hit: bool = False
    structure: Optional[StructureRef] = Field(None, description="the relaxed structure, with its energy")


class CheckVerdict(BaseModel):
    check_id: int                    # 1 to 11, as in agent.md section 3
    name: str
    passed: bool
    measured: Optional[float] = None
    threshold: Optional[str] = None
    reason: str = ""
    fragment: Optional[str] = Field(None, description="A, B or None; desorption runs per fragment")


class GateResult(BaseModel):
    candidate_id: str
    verdicts: List[CheckVerdict]
    passed: bool
    stage: str                       # "before_relaxation" | "after_relaxation"


class Cluster(BaseModel):
    id: int
    members: List[str]
    nearest: str
    lowest: str


class DoubtFlag(BaseModel):
    candidate_id: str
    committee_spread_eV: float
    calibrated_error_eV: Optional[float] = None
    trigger: str                     # "disagreement" | "unmeasured" | "magnetic_metal" | "unseen_chemistry" | "out_of_range"
    escalate: bool


class DescriptorCard(BaseModel):
    """The only view of geometry the LLM gets."""
    candidate_id: str
    composition: str
    cell: str
    facet: str
    layers: int
    vacuum_A: float
    fixed_layers: int
    site_label: str
    point_group: str
    coordination: int
    height_A: float
    nn_distances_A: List[float]
    tilt_deg: Optional[float] = None
    displacement_from_start: str = ""
    magnetic_moment: Optional[float] = None
    verdicts: List[CheckVerdict] = Field(default_factory=list)
    AB_distance_A: Optional[float] = None
    site_graph_distance: Optional[int] = None
    energy_eV: Optional[float] = None
    image_path: Optional[str] = None
    fragment_lines: List[str] = Field(default_factory=list, description="one line per fragment: site, group, height, neighbours; the fields above describe B in a pair")

    def text(self) -> str:
        lines = [f"candidate {self.candidate_id}: {self.composition} on {self.facet}, {self.layers} layers, {self.vacuum_A:.1f} Å vacuum",
                 f"site {self.site_label}, {self.point_group}, coordination {self.coordination}; height {self.height_A:.2f} Å",
                 "nearest neighbours " + ", ".join(f"{d:.2f}" for d in self.nn_distances_A) + " Å"]
        lines += self.fragment_lines
        if self.AB_distance_A is not None:
            lines.append(f"A–B distance {self.AB_distance_A:.2f} Å; site-graph distance {self.site_graph_distance}")
        if self.energy_eV is not None:
            lines.append(f"energy {self.energy_eV:.3f} eV")
        if self.displacement_from_start:
            lines.append(self.displacement_from_start)
        if self.magnetic_moment is not None:
            lines.append(f"total moment {self.magnetic_moment:.2f} μB")
        for v in self.verdicts:
            status = "FAIL" if not v.passed else ("not checked" if "not checked" in v.reason else "pass")
            lines.append(f"check {v.check_id} {v.name}: {status} {v.reason}".rstrip())
        return "\n".join(lines)


class RankedCandidate(BaseModel):
    candidate_id: str
    rank: int
    site_graph_distance: int
    energy_eV: float
    doubt: Optional[DoubtFlag] = None
    reason: str = ""


class HumanChoice(BaseModel):
    checkpoint: str
    chosen: List[str]
    reason: str
    who: str
    when: datetime = Field(default_factory=datetime.now)


class FinalState(BaseModel):
    candidate_id: str
    E_near_eV: float
    E_inf_eV: float
    lateral_interaction_eV: float
    AB_distance_A: float
    site_graph_distance: int
    recombined: bool = False


class Report(BaseModel):
    campaign: str
    final_states: List[FinalState]
    rejected: List[GateResult]
    recombination_rate: float
    recombination_rate_by_shell: Dict[int, float] = Field(default_factory=dict)
    doubt: List[DoubtFlag] = Field(default_factory=list)
    comparison_oc20neb: Dict[str, float] = Field(default_factory=dict)
    cost: Dict[str, float] = Field(default_factory=dict)
    trace_path: str
    settings_hash: str


class TraceEvent(BaseModel):
    when: datetime = Field(default_factory=datetime.now)
    step: str
    tool: str
    actor: str                       # tool | agent name | human
    inputs_hash: str
    outputs_ref: str
    message: str = ""


class Case(BaseModel):
    """One raw case in the case bank, lessons.md: what was seen, what was done, why."""
    system: str
    card: str
    correction: str
    reason: str
    source_checkpoint: str
    promoted_to: Optional[str] = Field(None, description="skill line, check or prior; only a human sets this")
    when: datetime = Field(default_factory=datetime.now)
