"""Tool structure_retrieval: board step 1. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import StructureRef
from ..provenance import traced


@traced(step="1", tool="structure_retrieval")
def structure_retrieval(slab: StructureRef, adsorbate_vacuum: StructureRef, initial_state: StructureRef, bond_to_break: Tuple[int, int]) -> Any:
    """Take the three supplied relaxed structures with their energies, cleave the named bond to make A and B, and select the surface cell so periodic images stay apart.

    Board steps: 1. Status: core.

    Inputs:
        slab: StructureRef
        adsorbate_vacuum: StructureRef
        initial_state: StructureRef
        bond_to_break: tuple[int, int], atom indices in AB
    Outputs:
        fragment_A: StructureRef
        fragment_B: StructureRef
        cell_repeat: tuple[int, int]
        structures: list[StructureRef]
    Checks:
        - the three inputs share one settings set, check 8
        - images at least min_image_distance_A apart
    Thresholds:
        min_image_distance_A: 10
    Wraps:
        - ase.io
        - pymatgen.core
    Logs: input hashes; the cell and why.
    """
    raise NotImplementedError("structure_retrieval: see agent.md section 3 and finalstate.registry")
