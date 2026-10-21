"""The anomaly filter, eleven checks, and the descriptor card the agents read. Tools: anomaly_filter, descriptor_card. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import Candidate, GateResult, Settings, SiteEnumeration, StructureRef
from ..runtime.journal import traced


@traced(step="5", tool="anomaly_filter")
def anomaly_filter(candidate: Candidate, start: Candidate, slab: StructureRef, settings: Settings, prior_E_ads_eV: float, frequencies_cm: list) -> Any:
    """The nine checks of the gate per fragment, before and after relaxation, plus the two final-state checks: the A–B bond re-formed, and the periodic image; verdict into the card; a failing candidate is never kept.

    Board steps: 5, 3.1. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        candidate: Candidate
        start: Candidate
        slab: StructureRef
        settings: Settings
        prior_E_ads_eV: float | None
        frequencies_cm: list[float] | None
    Outputs:
        gate: GateResult
    Checks:
        - 1 desorbed per fragment
        - 2 migrated
        - 3 dissociated within a fragment
        - 4 reconstructed
        - 5 not a minimum
        - 6 magnetism collapsed
        - 7 outside expected range
        - 8 settings mismatch
        - 9 intercalated
        - 10 A–B bond re-formed
        - 11 periodic image
    Thresholds:
        desorbed_A: 3
        AB_bond_reformed_A: open: team decision
        migrated: open: team decision
        dissociated: open: team decision
        reconstructed: open: team decision
        imaginary_noise_cm: open: team decision
        expected_range_width_eV: open: team decision
        magnetism_collapsed: open: team decision
        intercalated: open: team decision
    Wraps:
        - fairchem.data.oc.utils.DetectTrajAnomaly
        - ase.vibrations.Vibrations
        - acat.adsorbate_coverage.SlabAdsorbateCoverage
        - CatBench anomaly classes as names
    Logs: every verdict with its measured value; every rejection with its reason.
    """
    raise NotImplementedError("anomaly_filter: see AGENTS.md section 3 and fragplace.registry")


@traced(step="3.4", tool="descriptor_card")
def descriptor_card(candidate: Candidate, gate: GateResult, sites: SiteEnumeration) -> Any:
    """Render a structure as the text card the LLM reads, with site, distances, verdicts and the A–B distance; a PNG beside it as a second look.

    Board steps: 3.4, 5, 8. Status: core. Lane: laptop. Allowed roles: solution-planner, surface-chemist, scientific-critic.

    Inputs:
        candidate: Candidate
        gate: GateResult | None
        sites: SiteEnumeration
    Outputs:
        card: DescriptorCard
    Checks:
        - two configurations never share a card: distances and site labels always present
    Thresholds:
        none
    Wraps:
        - pymatgen
        - robocrystallographer pattern
        - ase.io.write png
    Logs: the card beside the structure.
    """
    raise NotImplementedError("descriptor_card: see AGENTS.md section 3 and fragplace.registry")
