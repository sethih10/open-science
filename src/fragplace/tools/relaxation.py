"""Relaxations and the reference energies, cached. Tools: relaxation, reference_energies. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import Candidate, StructureRef
from ..runtime.journal import traced


@traced(step="4", tool="relaxation")
def relaxation(candidates: List[Candidate], calculator: str, fmax_eV_per_A: float, max_steps: int) -> Any:
    """Relax every candidate with the chosen potential and the locked settings, random displacement first; cached by content hash.

    Board steps: 4. Status: core. Lane: gpu. Allowed roles: solution-planner.

    Inputs:
        candidates: list[Candidate]
        calculator: str
        fmax_eV_per_A: float
        max_steps: int
    Outputs:
        results: list[RelaxationResult]
    Checks:
        - same settings as the initial state, check 8
    Thresholds:
        none
    Wraps:
        - ase.optimize
        - fragplace.calculators
        - fragplace.cache
    Logs: steps, fmax, convergence, cache hit per candidate.
    """
    raise NotImplementedError("relaxation: see AGENTS.md section 3 and fragplace.registry")


@traced(step="solution", tool="reference_energies")
def reference_energies(slab: StructureRef, fragments: Tuple[StructureRef, StructureRef], calculator: str) -> Any:
    """E(A*), E(B*) and E(slab) each in its own cell with the chosen potential and the locked settings, for E(FS ∞) and the lateral interaction.

    Board steps: solution. Status: core. Lane: gpu. Allowed roles: solution-planner.

    Inputs:
        slab: StructureRef
        fragments: tuple[StructureRef, StructureRef]
        calculator: str
    Outputs:
        E_slab_eV: float
        E_A_eV: float
        E_B_eV: float
        E_inf_eV: float
    Checks:
        - same settings as every candidate, check 8
    Thresholds:
        none
    Wraps:
        - fragplace.calculators
    Logs: the three energies.
    """
    raise NotImplementedError("reference_energies: see AGENTS.md section 3 and fragplace.registry")
