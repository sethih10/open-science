"""Tool report: board step solution. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import DoubtFlag, FinalState, GateResult
from ..provenance import traced


@traced(step="solution", tool="report")
def report(campaign: str, final_states: List[FinalState], rejected: List[GateResult], flags: List[DoubtFlag], comparison: Any) -> Any:
    """One auditable record per campaign: final states with both energies, rejections with reasons, the recombination rate, doubt, the OC20NEB comparison, cost and the decision trace.

    Board steps: solution. Status: core.

    Inputs:
        campaign: str
        final_states: list[FinalState]
        rejected: list[GateResult]
        flags: list[DoubtFlag]
        comparison: dict
    Outputs:
        report: Report, written to runs/<campaign>/report.md and report.json
    Checks:
        - every number traces to a tool output
        - the general-peer-review skill reads the draft
    Thresholds:
        none
    Wraps:
        - AtomisticSkills hyperparameter logging pattern
    Logs: t; h; e;  ; f; u; l; l;  ; t; r; a; c; e;  ; p; a; t; h.
    """
    raise NotImplementedError("report: see agent.md section 3 and finalstate.registry")
