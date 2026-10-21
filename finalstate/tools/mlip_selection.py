"""Tool mlip_selection: board step 1*. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import StructureRef
from ..provenance import traced


@traced(step="1*", tool="mlip_selection")
def mlip_selection(candidates: list, system_class: str, labels: List[StructureRef]) -> Any:
    """Benchmark two or three candidate potentials on the system class and choose one; every candidate becomes the committee of uncertainty_estimation.

    Board steps: 1*. Status: core.

    Inputs:
        candidates: list[str], calculator names
        system_class: str, metal | oxide | organometallic
        labels: list[StructureRef] with DFT energies, or OC20NEB
    Outputs:
        chosen: str
        committee: list[str]
        benchmark: dict name -> error_eV and anomaly classes
    Checks:
        - spin initialised on Co and Ni
        - cross-family comparison on E_ads only, never total energies
    Thresholds:
        candidates: open: team decision
        label_count: open: team decision
    Wraps:
        - catbench.adsorption.AdsorptionCalculation
        - catbench.adsorption.AdsorptionAnalysis
        - AtomisticSkills ml-mlip-benchmark
        - fairchem.core.FAIRChemCalculator
        - mace.calculators.MACECalculator
        - chgnet
    Logs: benchmark results; the choice and the planner's reason.
    """
    raise NotImplementedError("mlip_selection: see agent.md section 3 and finalstate.registry")
