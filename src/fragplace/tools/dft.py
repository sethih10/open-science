"""DFT single points on a queue; the extension. Tools: dft_single_points. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import Settings, StructureRef
from ..runtime.journal import traced


@traced(step="7", tool="dft_single_points")
def dft_single_points(structures: List[StructureRef], settings: Settings, backend: Any) -> Any:
    """DFT single points on the chosen final states and the separated fragments at the locked settings; only with a DFT code and compute.

    Board steps: 7, solution. Status: extension. Lane: hpc. Allowed roles: solution-planner, dft-recovery-agent.

    Inputs:
        structures: list[StructureRef]
        settings: Settings
        backend: local | slurm
    Outputs:
        energies: dict candidate_id -> eV
        failures: list[str]
    Checks:
        - settings mismatch against PROJECT.md before submission
        - custodian handlers before any agent diagnosis
        - retries capped at three by the job tracker
    Thresholds:
        none
    Wraps:
        - ase.calculators
        - atomate2 through the AtomisticSkills MCP server
        - custodian.vasp.handlers
        - fragplace.compute.tracker
    Logs: force calls, failures, every resubmission.
    """
    raise NotImplementedError("dft_single_points: see AGENTS.md section 3 and fragplace.registry")
