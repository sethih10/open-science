"""The three relaxed inputs, the cleaved fragments, the cell and the settings lock. Tools: structure_retrieval, calculation_protocol. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import Settings, StructureRef
from ..runtime.journal import traced


@traced(step="1", tool="structure_retrieval")
def structure_retrieval(slab: StructureRef, adsorbate_vacuum: StructureRef, initial_state: StructureRef, bond_to_break: Tuple[int, int]) -> Any:
    """Take the three supplied relaxed structures with their energies, cleave the named bond to make A and B, and select the surface cell so periodic images stay apart.

    Board steps: 1. Status: core. Lane: laptop. Allowed roles: computational-chemist, solution-planner.

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
    raise NotImplementedError("structure_retrieval: see AGENTS.md section 3 and fragplace.registry")


@traced(step="1", tool="calculation_protocol")
def calculation_protocol(settings_from_inputs: Settings, physics_choices: Any, protocol: Any, protocol_reason: str) -> Any:
    """Lock the numerical and physical settings in PROJECT.md from the inputs' settings, the human's physics choices and a verified protocol; never from the model's memory.

    Board steps: 1. Status: core. Lane: laptop. Allowed roles: computational-chemist, solution-planner.

    Inputs:
        settings_from_inputs: Settings, as read from the relaxed inputs
        physics_choices: dict from the human: functional, dispersion, spin, U
        protocol: aiida_common_workflows | sssp | oc20
        protocol_reason: str, stated by the computational chemist
    Outputs:
        settings: Settings with locked False until the human approves
    Checks:
        - cutoff, k-mesh, smearing, layers from the protocol table of agent.md section 3
        - if OC20NEB is the benchmark, RPBE and PAW as OC20
    Thresholds:
        convergence_target_meV: open: team decision
        gas_references: open: team decision
    Wraps:
        - aiida_common_workflows.workflows.relax.CommonRelaxWorkChain protocols
        - SSSP
        - pymatgen.io.vasp.sets.MPRelaxSet
    Logs: protocol and reason; every setting and its origin.
    """
    raise NotImplementedError("calculation_protocol: see AGENTS.md section 3 and fragplace.registry")
