"""Tool uncertainty_estimation: board step 7. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import Candidate, StructureRef
from ..provenance import traced


@traced(step="7", tool="uncertainty_estimation")
def uncertainty_estimation(candidates: List[Candidate], committee: list, labels: List[StructureRef]) -> Any:
    """Committee disagreement across the candidates benchmarked at 1*, calibrated on a few DFT or OC20NEB labels; a doubt flag that escalates to the human instead of guessing.

    Board steps: 7. Status: core.

    Inputs:
        candidates: list[Candidate]
        committee: list[str]
        labels: list[StructureRef] | None
    Outputs:
        flags: list[DoubtFlag]
    Checks:
        - disagreement compared on E_ads, never on total energies across families
        - magnetic metals always flagged
        - unseen chemistry always flagged
    Thresholds:
        escalation_threshold_eV: open: team decision
        label_count: open: team decision
    Wraps:
        - mace.calculators.MACECalculator with model_paths
        - uncertainty_toolbox.metrics.get_all_metrics
        - AtomisticSkills ml-committee-uncertainty
    Logs: labels used; spread against label error; every flag and escalation.
    """
    raise NotImplementedError("uncertainty_estimation: see agent.md section 3 and finalstate.registry")
