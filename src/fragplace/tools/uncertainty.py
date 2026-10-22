"""Potential selection, committee doubt and active learning; the mlip-specialist's tools. Tools: mlip_selection, uncertainty_estimation, active_learning. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .. import calculators
from ..runtime import artifacts, project
from ..runtime.cache import for_run
from ..runtime.journal import log, traced
from ..schemas.records import Candidate, DoubtFlag, Role, Settings, StructureRef

MAGNETIC = {"Fe", "Co", "Ni"}
SEEN_ADSORBATE = {"H", "C", "N", "O"}      # OC20's adsorbate elements; anything else is unseen chemistry
NON_METALS = {"H", "He", "B", "C", "N", "O", "F", "Ne", "Si", "P", "S", "Cl", "Ar", "As", "Se", "Br", "Kr", "Te", "I", "Xe"}
BENCH_STEPS = 500


@traced(step="1*", tool="mlip_selection")
def mlip_selection(candidates: List[str], system_class: str, labels: List[StructureRef]) -> Dict[str, Any]:
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

    A label is a set of three structures with energies, a slab, an adsorbate in vacuum and the adsorbate on the
    slab, told apart by role; the three supplied inputs are one. Each potential relaxes all three from the label
    geometry, as CatBench does, and its error is its E_ads minus the label's, so no total energy is compared
    across families. The chosen one has the smallest absolute error; a potential that does not load is reported
    as unavailable and left out of the committee.
    """
    s = project.current_settings()
    wanted = list(project.decision("mlip_selection", "candidates", s))
    if list(candidates) != wanted:
        raise ValueError(f"candidates {list(candidates)} differ from the locked decision mlip_selection.candidates = {wanted}")
    count = int(project.decision("mlip_selection", "label_count", s))
    sets = _label_sets(labels)[:count]
    if not sets:
        raise ValueError("no label set: a slab, an adsorbate in vacuum and an initial state, each with its energy")
    symbols = set(artifacts.read(sets[0]["slab"]).get_chemical_symbols())
    bench: Dict[str, Dict[str, Any]] = {}
    for name in candidates:
        try:
            adapter = calculators.get(name)
        except Exception as e:  # noqa: BLE001 - an unavailable potential is a benchmark result, not a crash
            bench[name] = {"error_eV": None, "anomalies": [f"unavailable: {type(e).__name__}: {e}"]}
            continue
        anomalies, errors = [], []
        if len(sets) < count:
            anomalies.append(f"{len(sets)} of the {count} label sets mlip_selection.label_count asks for")
        for k, ls in enumerate(sets):
            e = {}
            for role, ref in ls.items():
                e[role], converged = _relaxed_energy(adapter, name, artifacts.read(ref), s)
                if not converged:
                    anomalies.append(f"label {k} {role}: not converged in {BENCH_STEPS} steps")
            reference = ls["initial_state"].energy_eV - ls["slab"].energy_eV - ls["adsorbate_vacuum"].energy_eV
            errors.append(e["initial_state"] - e["slab"] - e["adsorbate_vacuum"] - reference)
        if symbols & MAGNETIC and (not s.spin_polarised or adapter.magnetic_moments(artifacts.read(sets[0]["slab"])) is None):
            anomalies.append("magnetic metal without spin")
        if system_class != "metal":
            anomalies.append(f"unseen chemistry: {system_class}")
        bench[name] = {"error_eV": float(np.mean(np.abs(errors))), "signed_errors_eV": [float(x) for x in errors], "anomalies": anomalies}
    usable = [n for n in candidates if bench[n]["error_eV"] is not None]
    if not usable:
        raise RuntimeError("no candidate potential loads: " + "; ".join(f"{n}: {bench[n]['anomalies']}" for n in candidates))
    chosen = min(usable, key=lambda n: bench[n]["error_eV"])
    for n in candidates:
        log("mlip_selection", f"{n}: E_ads error {bench[n]['error_eV']} eV over {len(sets)} label set(s) of {count} asked; anomalies {bench[n]['anomalies']}")
    log("mlip_selection", f"chosen {chosen}: smallest absolute E_ads error; committee {usable}; system class {system_class}")
    return {"chosen": chosen, "committee": usable, "benchmark": bench}


def _label_sets(labels: List[StructureRef]) -> List[Dict[str, StructureRef]]:
    """Consecutive slab, adsorbate-in-vacuum and initial-state refs, each with an energy, grouped into sets."""
    sets, current = [], {}
    for ref in labels:
        role = ref.role.value if isinstance(ref.role, Role) else str(ref.role)
        if role not in ("slab", "adsorbate_vacuum", "initial_state") or ref.energy_eV is None:
            raise ValueError(f"label {ref.path}: role {role}, energy {ref.energy_eV}; a label needs one of the three roles and an energy")
        current[role] = ref
        if len(current) == 3:
            sets.append(current)
            current = {}
    return sets


def _relaxed_energy(adapter, name: str, atoms, s: Settings):
    """Relax with one potential, cached; the energy and whether it converged."""
    cache = for_run()
    key = cache.key(artifacts.structure_hash(atoms), name, project.settings_hash(s), f"bench relax {s.force_threshold_eV_per_A}") if cache else None
    hit = cache.get(key) if cache else None
    if hit:
        return hit["energy_eV"], hit["converged"]
    relaxed, converged, _, _ = adapter.relax(atoms, fmax=s.force_threshold_eV_per_A, steps=BENCH_STEPS)
    out = {"energy_eV": float(relaxed.get_potential_energy()), "converged": bool(converged)}
    if cache:
        cache.put(key, out)
    return out["energy_eV"], out["converged"]


@traced(step="7", tool="uncertainty_estimation")
def uncertainty_estimation(candidates: List[Candidate], committee: List[str], labels: Optional[List[StructureRef]] = None) -> List[DoubtFlag]:
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

    Each member gives the interaction energy of the candidate's adsorbates with its slab, E(all) − E(slab part) −
    E(adsorbate part) at the relaxed geometry, so its own reference cancels; the spread is the standard deviation
    across members, or a committee model's own spread when there is one member. Labels are structures of one
    composition with DFT energies: the chosen potential's errors on them, less their mean, give the error on
    relative energies, and its ratio to the committee's spread on the labels scales every spread into a
    calibrated error. A disagreement flag goes on every candidate and escalates above the threshold; magnetic
    metals and unseen chemistry always escalate, and so does a committee of one model without a committee of its
    own, flagged unmeasured, since it measures no disagreement at all.
    """
    s = project.current_settings()
    threshold = float(project.decision("uncertainty_estimation", "escalation_threshold_eV", s))
    members = [calculators.get(n) for n in committee]
    scale = None
    if labels:
        count = int(project.decision("uncertainty_estimation", "label_count", s))
        used = labels[:count]
        if len(used) < 2 or len({artifacts.read(r).get_chemical_formula() for r in used}) != 1 or any(r.energy_eV is None for r in used):
            raise ValueError("calibration needs at least two labels of one composition, each with an energy")
        errors = np.array([members[0].energy_forces(artifacts.read(r))[0] - r.energy_eV for r in used])
        rmse = float(np.sqrt(np.mean((errors - errors.mean()) ** 2)))
        spreads = [_spread(members, artifacts.read(r)) for r in used]
        spread_on_labels = float(np.mean(spreads)) if None not in spreads else 0.0
        scale = rmse / spread_on_labels if spread_on_labels > 0 else None
        log("uncertainty_estimation", f"{len(used)} labels: relative-energy error {rmse:.3f} eV of {committee[0]}, mean spread {spread_on_labels:.3f} eV, "
                                      f"scale {scale}")
    flags = []
    for c in candidates:
        atoms = artifacts.read(c.structure)
        spread = _spread(members, atoms)
        if spread is None:                      # a committee of one model measures nothing, so the doubt is not small: it is unknown
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=0.0, trigger="unmeasured", escalate=True))
            spread = 0.0
        calibrated = scale * spread if scale is not None else None
        doubt = calibrated if calibrated is not None else spread
        if not any(f.candidate_id == c.id and f.trigger == "unmeasured" for f in flags):
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=spread, calibrated_error_eV=calibrated, trigger="disagreement", escalate=doubt > threshold))
        symbols = set(atoms.get_chemical_symbols())
        if symbols & MAGNETIC:
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=spread, calibrated_error_eV=calibrated, trigger="magnetic_metal", escalate=True))
        if _unseen(atoms):
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=spread, calibrated_error_eV=calibrated, trigger="unseen_chemistry", escalate=True))
    for f in flags:
        log("uncertainty_estimation", f"{f.candidate_id} {f.trigger}: spread {f.committee_spread_eV:.4f} eV, calibrated {f.calibrated_error_eV}"
                                      + (f", ESCALATE above {threshold} eV" if f.trigger == "disagreement" and f.escalate else (", ESCALATE" if f.escalate else "")))
    return flags


def _spread(members, atoms) -> Optional[float]:
    """The committee's spread on the interaction energy; None when one model with no committee of its own measures none."""
    if len(members) == 1:
        return members[0].spread(atoms)
    slab = artifacts.slab_indices(atoms)
    ads = artifacts.adsorbate_indices(atoms)
    e = [m.energy_forces(atoms)[0] - m.energy_forces(atoms[slab])[0] - m.energy_forces(atoms[ads])[0] for m in members]
    return float(np.std(e))


def _unseen(atoms) -> bool:
    """Oxides and other non-metal slabs, and adsorbates beyond H, C, N, O, are outside what OC20 trained on."""
    slab = {atoms[i].symbol for i in artifacts.slab_indices(atoms)}
    ads = {atoms[i].symbol for i in artifacts.adsorbate_indices(atoms)}
    return bool(slab & NON_METALS) or not ads <= SEEN_ADSORBATE


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
    raise NotImplementedError("active_learning is an extension: it needs DFT labels, decision D2; see AGENTS.md section 3")
