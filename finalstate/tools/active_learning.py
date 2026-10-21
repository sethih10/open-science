"""Tool active_learning: board step 1*. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import DoubtFlag, StructureRef
from ..provenance import traced


@traced(step="1*", tool="active_learning")
def active_learning(flags: List[DoubtFlag], labels: List[StructureRef], base_model: str) -> Any:
    """High doubt to a few DFT labels to a fine-tuned potential to a re-run of steps 4 to 8.

    Board steps: 1*. Status: extension.

    Inputs:
        flags: list[DoubtFlag]
        labels: list[StructureRef]
        base_model: str
    Outputs:
        fine_tuned: str
    Checks:
        - none
    Thresholds:
        none
    Wraps:
        - AtomisticSkills ml-mace-finetune
    Logs: labels used; model path.
    """
    raise NotImplementedError("active_learning: see agent.md section 3 and finalstate.registry")
