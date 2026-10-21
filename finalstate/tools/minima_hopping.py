"""Tool minima_hopping: board step 3.6. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import StructureRef
from ..provenance import traced


@traced(step="3.6", tool="minima_hopping")
def minima_hopping(slab: StructureRef, fragments: Tuple[StructureRef, StructureRef], calculator: str, n_hops: int) -> Any:
    """NEBscape's endpoint generator with the chosen potential as the alternative generator and the baseline policy our nearest-first choice is scored against.

    Board steps: 3.6. Status: core.

    Inputs:
        slab: StructureRef
        fragments: tuple[StructureRef, StructureRef]
        calculator: str
        n_hops: int
    Outputs:
        candidates: list[Candidate] with generator minima_hopping
    Checks:
        - Hookean constraints keep A and B intact during hopping, as NEBscape
    Thresholds:
        none
    Wraps:
        - nebscape endpoint generator, MIT
        - ase.optimize.minimahopping.MinimaHopping
    Logs: hops; minima found.
    """
    raise NotImplementedError("minima_hopping: see agent.md section 3 and finalstate.registry")
