"""Tool anomaly_filter: board steps 5, 3.1. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import Candidate, Settings, StructureRef
from ..provenance import traced


@traced(step="5", tool="anomaly_filter")
def anomaly_filter(candidate: Candidate, start: Candidate, slab: StructureRef, settings: Settings, prior_E_ads_eV: float, frequencies_cm: list) -> Any:
    """The nine checks of the gate per fragment, before and after relaxation, plus the two final-state checks: the A–B bond re-formed, and the periodic image; verdict into the card; a failing candidate is never kept.

    Board steps: 5, 3.1. Status: core.

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
    raise NotImplementedError("anomaly_filter: see agent.md section 3 and finalstate.registry")
