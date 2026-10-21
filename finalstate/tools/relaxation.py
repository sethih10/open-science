"""Tool relaxation: board step 4. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import Candidate
from ..provenance import traced


@traced(step="4", tool="relaxation")
def relaxation(candidates: List[Candidate], calculator: str, fmax_eV_per_A: float, max_steps: int) -> Any:
    """Relax every candidate with the chosen potential and the locked settings, random displacement first; cached by content hash.

    Board steps: 4. Status: core.

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
        - finalstate.calculators
        - finalstate.cache
    Logs: s; t; e; p; s; ,;  ; f; m; a; x; ,;  ; c; o; n; v; e; r; g; e; n; c; e; ,;  ; c; a; c; h; e;  ; h; i; t;  ; p; e; r;  ; c; a; n; d; i; d; a; t; e.
    """
    raise NotImplementedError("relaxation: see agent.md section 3 and finalstate.registry")
