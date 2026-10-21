"""Tool reference_energies: board step solution. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import StructureRef
from ..provenance import traced


@traced(step="solution", tool="reference_energies")
def reference_energies(slab: StructureRef, fragments: Tuple[StructureRef, StructureRef], calculator: str) -> Any:
    """E(A*), E(B*) and E(slab) each in its own cell with the chosen potential and the locked settings, for E(FS ∞) and the lateral interaction.

    Board steps: solution. Status: core.

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
        - finalstate.calculators
    Logs: t; h; e;  ; t; h; r; e; e;  ; e; n; e; r; g; i; e; s.
    """
    raise NotImplementedError("reference_energies: see agent.md section 3 and finalstate.registry")
