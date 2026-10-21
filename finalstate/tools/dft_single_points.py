"""Tool dft_single_points: board steps 7, solution. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import Settings, StructureRef
from ..provenance import traced


@traced(step="7", tool="dft_single_points")
def dft_single_points(structures: List[StructureRef], settings: Settings, backend: Any) -> Any:
    """DFT single points on the chosen final states and the separated fragments at the locked settings; only with a DFT code and compute.

    Board steps: 7, solution. Status: extension.

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
    Thresholds:
        none
    Wraps:
        - ase.calculators
        - atomate2 through the AtomisticSkills MCP server
        - custodian.vasp.handlers
    Logs: f; o; r; c; e;  ; c; a; l; l; s; ,;  ; f; a; i; l; u; r; e; s; ,;  ; e; v; e; r; y;  ; r; e; s; u; b; m; i; s; s; i; o; n.
    """
    raise NotImplementedError("dft_single_points: see agent.md section 3 and finalstate.registry")
