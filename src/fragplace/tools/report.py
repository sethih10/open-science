"""The campaign report. Tools: report. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import DoubtFlag, FinalState, GateResult
from ..runtime.journal import traced


@traced(step="solution", tool="report")
def report(campaign: str, final_states: List[FinalState], rejected: List[GateResult], flags: List[DoubtFlag], comparison: Any) -> Any:
    """One auditable record per campaign: final states with both energies, rejections with reasons, the recombination rate, doubt, the OC20NEB comparison, cost and the decision trace.

    Board steps: solution. Status: core. Lane: laptop. Allowed roles: solution-planner, scientific-critic.

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
        - the scientific critic reads the draft with the general-peer-review skill
    Thresholds:
        none
    Wraps:
        - AtomisticSkills hyperparameter logging pattern
    Logs: the full trace path.
    """
    raise NotImplementedError("report: see AGENTS.md section 3 and fragplace.registry")
