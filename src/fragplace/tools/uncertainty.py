"""Potential selection, committee doubt and active learning; the mlip-specialist's tools. Tools: mlip_selection, uncertainty_estimation, active_learning. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import Candidate, DoubtFlag, StructureRef
from ..runtime.journal import traced


@traced(step="1*", tool="mlip_selection")
def mlip_selection(candidates: list, system_class: str, labels: List[StructureRef]) -> Any:
    """Benchmark two or three candidate potentials on the system class and choose one; every candidate becomes the committee of uncertainty_estimation.

    Board steps: 1*. Status: core. Lane: gpu. Allowed roles: mlip-specialist.

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
    Logs: benchmark results; the choice and the specialist's reason.
    """
    raise NotImplementedError("mlip_selection: see AGENTS.md section 3 and fragplace.registry")


@traced(step="7", tool="uncertainty_estimation")
def uncertainty_estimation(candidates: List[Candidate], committee: list, labels: List[StructureRef]) -> Any:
    """Committee disagreement across the candidates benchmarked at 1*, calibrated on a few DFT or OC20NEB labels; a doubt flag that escalates to the human instead of guessing.

    Board steps: 7. Status: core. Lane: gpu. Allowed roles: mlip-specialist.

    Inputs:
        candidates: list[Candidate]
        committee: list[str]
        labels: list[StructureRef] | None
    Outputs:
        flags: list[DoubtFlag]
    Checks:
        - disagreement compared on E_ads, never on total energies across families
        - magnetic metals always flagged
        - unseen chemistry always flagged
    Thresholds:
        escalation_threshold_eV: open: team decision
        label_count: open: team decision
    Wraps:
        - mace.calculators.MACECalculator with model_paths
        - uncertainty_toolbox.metrics.get_all_metrics
        - AtomisticSkills ml-committee-uncertainty
    Logs: labels used; spread against label error; every flag and escalation.
    """
    raise NotImplementedError("uncertainty_estimation: see AGENTS.md section 3 and fragplace.registry")


@traced(step="1*", tool="active_learning")
def active_learning(flags: List[DoubtFlag], labels: List[StructureRef], base_model: str) -> Any:
    """High doubt to a few DFT labels to a fine-tuned potential to a re-run of steps 4 to 8.

    Board steps: 1*. Status: extension. Lane: gpu. Allowed roles: mlip-specialist.

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
    raise NotImplementedError("active_learning: see AGENTS.md section 3 and fragplace.registry")
