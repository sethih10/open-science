"""Potential selection, committee doubt and active learning; the mlip-specialist's tools. Tools: mlip_selection, uncertainty_estimation, active_learning. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from .. import calculators
from ..runtime import artifacts, geometry, project
from ..runtime.cache import for_run
from ..runtime.journal import log, traced
from ..schemas.records import Candidate, DoubtFlag, Role, Settings, StructureRef

MAGNETIC = {"Fe", "Co", "Ni"}
SEEN_ADSORBATE = {"H", "C", "N", "O"}      # OC20's adsorbate elements; anything else is unseen chemistry
NON_METALS = {"H", "He", "B", "C", "N", "O", "F", "Ne", "Si", "P", "S", "Cl", "Ar", "As", "Se", "Br", "Kr", "Te", "I", "Xe", "At", "Rn"}
BENCH_STEPS = 500
LABEL_ROLES = ("slab", "adsorbate_vacuum", "initial_state")


@traced(step="1*", tool="mlip_selection")
def mlip_selection(candidates: List[str], system_class: str, labels: List[StructureRef]) -> Dict[str, Any]:
    """Benchmark two or three candidate potentials on the system class and choose one; every candidate becomes the committee of uncertainty_estimation.

    Board steps: 1*. Status: core. Lane: gpu. Allowed roles: mlip-specialist.

    Inputs:
        candidates: list[str], calculator names
        system_class: str, metal | oxide | ionic | organometallic
        labels: list[StructureRef] with DFT energies, or OC20NEB; without energies the benchmark is geometric
    Outputs:
        chosen: str
        committee: list[str]
        benchmark: dict name -> error_eV or, geometric, the adsorbate's largest move and the residual fmax, and anomaly classes
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

    A label is a set of three structures, a slab, an adsorbate in vacuum and the adsorbate on the slab, told apart
    by role; the three supplied inputs are one. When the sets carry energies, each potential relaxes all three
    from the label geometry, as CatBench does, and its error is its E_ads minus the label's, so no total energy is
    compared across families; the chosen one has the smallest absolute error. When no set carries energies the
    benchmark is geometric: the residual fmax of each potential at the supplied geometries, and the largest move of
    an adsorbate atom when the potential relaxes the initial state itself; the chosen one moves the adsorbate
    least, then has the smaller fmax. A set whose structures all name the candidate as their calculator measures
    the candidate against itself: it is left out of that candidate's score, and a candidate with nothing else
    ranks after every other. A potential that does not load, or has no parameters for an element of the labels,
    is reported unavailable and left out of the committee. The system class is checked against the slab's
    elements, any non-metal making it oxide or ionic, and unseen chemistry is the rule uncertainty_estimation
    applies.
    """
    s = project.current_settings()
    wanted = list(project.decision("mlip_selection", "candidates", s))
    if list(candidates) != wanted:
        raise ValueError(f"candidates {list(candidates)} differ from the locked decision mlip_selection.candidates = {wanted}")
    count = int(project.decision("mlip_selection", "label_count", s))
    sets = _label_sets(labels)[:count]
    if not sets:
        raise ValueError("no label set: a slab, an adsorbate in vacuum and an initial state")
    structures = [{role: artifacts.read(ref) for role, ref in ls.items()} for ls in sets]
    slab_elements = set(structures[0]["slab"].get_chemical_symbols())
    ads_elements = set(structures[0]["adsorbate_vacuum"].get_chemical_symbols())
    derived = system_class_of(slab_elements, ads_elements)
    unseen = unseen_chemistry(slab_elements, ads_elements)
    elements = {el for st in structures for atoms in st.values() for el in atoms.get_chemical_symbols()}
    energetic = [k for k, ls in enumerate(sets) if all(r.energy_eV is not None for r in ls.values())]
    mode = "E_ads" if energetic else "geometric"
    bench: Dict[str, Dict[str, Any]] = {}
    for name in candidates:
        try:
            adapter = calculators.get(name)
        except Exception as e:  # noqa: BLE001 - an unavailable potential is a benchmark result, not a crash
            bench[name] = _unavailable(f"{type(e).__name__}: {e}")
            continue
        missing = adapter.unsupported(elements)
        if missing:
            bench[name] = _unavailable(f"{name} has no parameters for {', '.join(missing)}")
            continue
        try:
            bench[name] = _benchmark(adapter, name, sets, structures, energetic or list(range(len(sets))), energetic, s)
        except Exception as e:  # noqa: BLE001 - a potential that fails on the labels is reported as one that does not load
            bench[name] = _unavailable(f"failed on the labels: {type(e).__name__}: {e}")
            continue
        anomalies = bench[name]["anomalies"]
        if len(sets) < count:
            anomalies.insert(0, f"{len(sets)} of the {count} label sets mlip_selection.label_count asks for")
        if slab_elements & MAGNETIC and (not s.spin_polarised or adapter.magnetic_moments(structures[0]["slab"]) is None):
            anomalies.append("magnetic metal without spin")
        if unseen:
            anomalies.append(f"unseen chemistry: {unseen}")
        if system_class != derived:
            anomalies.append(f"system class {system_class} given; the slab's elements make it {derived}")
        if getattr(adapter, "licence", None):
            bench[name]["licence"] = adapter.licence
    usable = [n for n in candidates if bench[n]["available"]]
    if not usable:
        raise RuntimeError("no candidate potential loads: " + "; ".join(f"{n}: {bench[n]['anomalies']}" for n in candidates))

    def score(n: str):
        b = bench[n]
        return (b["circular"], b["error_eV"]) if mode == "E_ads" else (b["circular"], b["max_adsorbate_displacement_A"], b["residual_fmax_eV_per_A"])

    chosen = min(usable, key=score)
    if mode == "geometric":
        log("mlip_selection", "benchmark geometric: no label set carries energies, so no E_ads is compared; the candidates are ranked by the "
                              "largest move of an adsorbate atom when each relaxes the initial state, then by the residual fmax at the supplied geometries")
    for n in candidates:
        b = bench[n]
        if not b["available"]:
            log("mlip_selection", f"{n}: {'; '.join(b['anomalies'])}")
            continue
        log("mlip_selection", f"{n}: " + (f"E_ads error {b['error_eV']:.4f} eV, " if b["error_eV"] is not None else "")
            + f"residual fmax {b['residual_fmax_eV_per_A']:.3f} eV/Å at the supplied geometries, an adsorbate atom moved up to "
            f"{b['max_adsorbate_displacement_A']:.3f} Å in its own relaxation, over {b['label_sets']} label set(s) of {count} asked; anomalies {b['anomalies']}")
    rule = "smallest absolute E_ads error" if mode == "E_ads" else "least adsorbate displacement, then the smaller residual fmax"
    log("mlip_selection", f"chosen {chosen}: {rule}" + (", on labels computed with itself" if bench[chosen]["circular"] else "")
        + f"; committee {usable}; system class {derived}")
    return {"chosen": chosen, "committee": usable, "benchmark": bench}


def system_class_of(slab_elements: Iterable[str], adsorbate_elements: Iterable[str]) -> str:
    """metal, oxide, ionic or organometallic from the elements: a non-metal in the slab makes it an oxide when the
    slab holds O and ionic otherwise, as the Cl of NaCl; a metal in the adsorbate makes it organometallic."""
    slab, ads = set(slab_elements), set(adsorbate_elements)
    if slab & NON_METALS:
        return "oxide" if "O" in slab else "ionic"
    return "organometallic" if ads - NON_METALS else "metal"


def unseen_chemistry(slab_elements: Iterable[str], adsorbate_elements: Iterable[str]) -> Optional[str]:
    """Why a system lies outside what OC20 trained on, or None: a non-metal in the slab, or an adsorbate element
    beyond H, C, N and O. Steps 1* and 7 apply this one rule."""
    slab = sorted(set(slab_elements) & NON_METALS)
    ads = sorted(set(adsorbate_elements) - SEEN_ADSORBATE)
    reasons = []
    if slab:
        reasons.append(f"non-metal {', '.join(slab)} in the slab")
    if ads:
        reasons.append(f"adsorbate element {', '.join(ads)} beyond H, C, N, O")
    return "; ".join(reasons) or None


def _unavailable(reason: str) -> Dict[str, Any]:
    return {"available": False, "benchmark": None, "error_eV": None, "anomalies": [f"unavailable: {reason}"]}


def _benchmark(adapter, name: str, sets, structures, pool: List[int], energetic: List[int], s: Settings) -> Dict[str, Any]:
    """One potential on the label sets of the pool: the E_ads error of each set with energies, the residual fmax at
    the supplied geometries, and the largest move of an adsorbate atom when it relaxes the initial state. The sets
    computed with this potential are left out unless they are all there is."""
    anomalies: List[str] = []
    circular = [k for k in pool if all(r.calculator == name for r in sets[k].values())]
    if circular:
        anomalies.append("labels computed with this potential: the error is circular")
    used = [k for k in pool if k not in circular] or pool
    errors, fmax, moved = [], [], []
    for k in used:
        st = structures[k]
        fmax.append(max(_fmax(adapter.energy_forces(atoms)[1]) for atoms in st.values()))
        relaxed = {}
        for role in (LABEL_ROLES if k in energetic else ("initial_state",)):
            relaxed[role] = _relaxed(adapter, name, st[role], s)
            if not relaxed[role]["converged"]:
                anomalies.append(f"label {k} {role}: not converged in {BENCH_STEPS} steps")
        n, start = len(st["slab"]), st["initial_state"]
        shift = geometry.mic(np.asarray(relaxed["initial_state"]["positions"])[n:] - start.positions[n:], start.cell.array)
        moved.append(float(np.linalg.norm(shift, axis=1).max()))
        if k in energetic:
            ls, e = sets[k], {role: r["energy_eV"] for role, r in relaxed.items()}
            reference = ls["initial_state"].energy_eV - ls["slab"].energy_eV - ls["adsorbate_vacuum"].energy_eV
            errors.append(e["initial_state"] - e["slab"] - e["adsorbate_vacuum"] - reference)
    return {"available": True, "benchmark": "E_ads" if energetic else "geometric",
            "error_eV": float(np.mean(np.abs(errors))) if errors else None, "signed_errors_eV": [float(x) for x in errors],
            "residual_fmax_eV_per_A": float(max(fmax)), "max_adsorbate_displacement_A": float(max(moved)), "label_sets": len(used),
            "circular": used == circular, "anomalies": anomalies}


def _label_sets(labels: List[StructureRef]) -> List[Dict[str, StructureRef]]:
    """Consecutive slab, adsorbate-in-vacuum and initial-state refs grouped into sets, with or without energies; a
    fragment relaxed in vacuum is no label and is passed over."""
    sets, current = [], {}
    for ref in labels:
        role = ref.role.value if isinstance(ref.role, Role) else str(ref.role)
        if role in (Role.fragment_A_vacuum.value, Role.fragment_B_vacuum.value):
            continue
        if role not in LABEL_ROLES:
            raise ValueError(f"label {ref.path}: role {role}; a label is a slab, an adsorbate in vacuum or an initial state")
        current[role] = ref
        if len(current) == 3:
            sets.append(current)
            current = {}
    return sets


def _fmax(forces) -> float:
    forces = np.asarray(forces)
    return float(np.sqrt((forces ** 2).sum(axis=1)).max()) if len(forces) else 0.0


def _relaxed(adapter, name: str, atoms, s: Settings) -> Dict[str, Any]:
    """Relax with one potential, cached: the energy, whether it converged, and the relaxed positions."""
    cache = for_run()
    key = cache.key(artifacts.structure_hash(atoms), name, project.settings_hash(s), f"bench relax {s.force_threshold_eV_per_A}") if cache else None
    hit = cache.get(key) if cache else None
    if hit and "positions" in hit:
        return hit
    relaxed, converged, _, _ = adapter.relax(atoms, fmax=s.force_threshold_eV_per_A, steps=BENCH_STEPS)
    out = {"energy_eV": float(relaxed.get_potential_energy()), "converged": bool(converged), "positions": relaxed.positions.tolist()}
    if cache:
        cache.put(key, out)
    return out


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
        - an open shell on a slab with a non-metal flagged
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
    metals and unseen chemistry always escalate, unseen chemistry by mlip_selection's rule, and so does a
    committee of one model without a committee of its own, flagged unmeasured, since it measures no disagreement
    at all; its spread reads not measured, never 0. A fragment with an odd number of electrons on a slab holding a
    non-metal, OH or H on NaCl, keeps the spin a metal would quench, so an open_shell flag escalates whenever a
    member of the committee carries no spin.
    """
    s = project.current_settings()
    threshold = float(project.decision("uncertainty_estimation", "escalation_threshold_eV", s))
    members = [calculators.get(n) for n in committee]
    spinless = [n for n, m in zip(committee, members) if not m.spin]
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
        measured = spread is not None
        if not measured:                        # a committee of one model measures nothing, so the doubt is not small: it is unknown
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=0.0, trigger="unmeasured", escalate=True))
            spread = 0.0
        calibrated = scale * spread if scale is not None and measured else None
        doubt = calibrated if calibrated is not None else spread
        if measured:
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=spread, calibrated_error_eV=calibrated, trigger="disagreement", escalate=doubt > threshold))
        slab_elements = {atoms[i].symbol for i in artifacts.slab_indices(atoms)}
        ads_elements = {atoms[i].symbol for i in artifacts.adsorbate_indices(atoms)}
        if set(atoms.get_chemical_symbols()) & MAGNETIC:
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=spread, calibrated_error_eV=calibrated, trigger="magnetic_metal", escalate=True))
        if unseen_chemistry(slab_elements, ads_elements):
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=spread, calibrated_error_eV=calibrated, trigger="unseen_chemistry", escalate=True))
        odd = [f for f in ("A", "B") if int(atoms.numbers[artifacts.fragment_indices(atoms, f)].sum()) % 2]
        if odd and slab_elements & NON_METALS and spinless:
            flags.append(DoubtFlag(candidate_id=c.id, committee_spread_eV=spread, calibrated_error_eV=calibrated, trigger="open_shell", escalate=True))
            log("uncertainty_estimation", f"{c.id} open shell: fragment {' and '.join(odd)} with an odd number of electrons on a slab holding "
                                          f"{', '.join(sorted(slab_elements & NON_METALS))}; {', '.join(spinless)} carries no spin")
    unmeasured = {f.candidate_id for f in flags if f.trigger == "unmeasured"}
    for f in flags:
        spread_text = "not measured" if f.candidate_id in unmeasured else f"{f.committee_spread_eV:.4f} eV"
        log("uncertainty_estimation", f"{f.candidate_id} {f.trigger}: spread {spread_text}, calibrated {f.calibrated_error_eV}"
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
