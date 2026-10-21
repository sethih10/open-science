"""Tool calculation_protocol: board step 1. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import Settings
from ..provenance import traced


@traced(step="1", tool="calculation_protocol")
def calculation_protocol(settings_from_inputs: Settings, physics_choices: Any, protocol: Any, protocol_reason: str) -> Any:
    """Lock the numerical and physical settings in PROJECT.md from the inputs' settings, the human's physics choices and a verified protocol; never from the model's memory.

    Board steps: 1. Status: core.

    Inputs:
        settings_from_inputs: Settings, as read from the relaxed inputs
        physics_choices: dict from the human: functional, dispersion, spin, U
        protocol: aiida_common_workflows | sssp | oc20
        protocol_reason: str, stated by the planner
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
    raise NotImplementedError("calculation_protocol: see agent.md section 3 and finalstate.registry")
