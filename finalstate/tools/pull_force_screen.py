"""Tool pull_force_screen: board step 3.3. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import Candidate
from ..provenance import traced


@traced(step="3.3", tool="pull_force_screen")
def pull_force_screen(candidates: List[Candidate], calculator: str) -> Any:
    """One MLIP force call per pair; the force on B along the A–B axis; a pull towards A above the threshold queues the pair last, never drops it.

    Board steps: 3.3. Status: core.

    Inputs:
        candidates: list[Candidate]
        calculator: str
    Outputs:
        screens: list[ForceScreen], queue order
    Checks:
        - one force call, no relaxation
    Thresholds:
        threshold_eV_per_A: open: team decision
    Wraps:
        - finalstate.calculators
    Logs: force per pair; queue order.
    """
    raise NotImplementedError("pull_force_screen: see agent.md section 3 and finalstate.registry")
