"""Relaxations and the reference energies, cached. Tools: relaxation, reference_energies. Defined in fragplace.registry."""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from .. import calculators
from ..errors import SettingsMismatch
from ..runtime import artifacts, project
from ..runtime.cache import for_run
from ..runtime.journal import current_run, log, traced
from ..schemas.records import Candidate, RelaxationResult, Role, StructureRef

MAX_STEPS = 500      # the step cap of reference_energies, which takes none; the rollout passes the same to relaxation


@traced(step="4", tool="relaxation")
def relaxation(candidates: List[Candidate], calculator: str, fmax_eV_per_A: float, max_steps: int) -> List[RelaxationResult]:
    """Relax every candidate with the chosen potential and the locked settings, random displacement first; cached by content hash.

    Board steps: 4. Status: core. Lane: gpu. Allowed roles: solution-planner.

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
        - fragplace.calculators
        - fragplace.cache
    Logs: steps, fmax, convergence, cache hit per candidate.

    Every relaxed structure carries the locked settings hash and the calculator's name, which the gate's check 8
    compares; a calculator other than the one PROJECT.md locks, when it locks one, stops the call. The random
    displacement is adsorbate_placement's; constraints travel with the structure.
    """
    settings = project.current_settings()
    _check_calculator(calculator, settings)
    results = []
    for c in candidates:
        r = _relaxed(artifacts.read(c.structure), c.id, c.structure.role, calculator, float(fmax_eV_per_A), int(max_steps), settings)
        results.append(r)
        log("relaxation", f"{c.id}: {r.steps} steps, fmax {r.fmax_eV_per_A:.3f} eV/Å, {'converged' if r.converged else 'NOT converged'}, "
                          f"E {r.energy_eV:.4f} eV{', cache hit' if r.cache_hit else ''}")
    return results


@traced(step="solution", tool="reference_energies")
def reference_energies(slab: StructureRef, fragments: Tuple[StructureRef, StructureRef], calculator: str) -> Dict[str, float]:
    """E(A*), E(B*) and E(slab) each in its own cell with the chosen potential and the locked settings, for E(FS ∞) and the lateral interaction.

    Board steps: solution. Status: core. Lane: gpu. Allowed roles: solution-planner.

    Inputs:
        slab: StructureRef
        fragments: tuple[StructureRef, StructureRef]
        calculator: str
    Outputs:
        E_slab_eV: float
        E_A_eV: float
        E_B_eV: float
        E_inf_eV: float
    Checks:
        - same settings as every candidate, check 8
    Thresholds:
        none
    Wraps:
        - fragplace.calculators
    Logs: the three energies.

    Each fragment goes on the slab alone, where the ref puts it, and the slab, slab plus A and slab plus B are
    relaxed with the locked force threshold; E(FS ∞) = E(A*) + E(B*) − E(slab). A ref that holds a whole final
    state gives the atoms tagged as its fragment, so the separated product keeps the sites of the final state.
    """
    settings = project.current_settings()
    _check_calculator(calculator, settings)
    fmax = settings.force_threshold_eV_per_A
    host = artifacts.read(slab)
    stem = slab.path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    energies = {"E_slab_eV": _relaxed(host, f"ref-{stem}", Role.reference, calculator, fmax, MAX_STEPS, settings).energy_eV}
    for key, ref, name in (("E_A_eV", fragments[0], "A"), ("E_B_eV", fragments[1], "B")):
        frag = artifacts.fragment_atoms(ref, name)
        system = host + frag
        system.set_constraint(host.constraints)
        system.info = {}
        label = f"ref-{name}-{artifacts.structure_hash(system)}"
        energies[key] = _relaxed(system, label, Role.reference, calculator, fmax, MAX_STEPS, settings).energy_eV
    energies["E_inf_eV"] = energies["E_A_eV"] + energies["E_B_eV"] - energies["E_slab_eV"]
    log("reference_energies", "E(slab) {E_slab_eV:.4f}, E(A*) {E_A_eV:.4f}, E(B*) {E_B_eV:.4f}, E(FS inf) {E_inf_eV:.4f} eV".format(**energies)
        + f", {calculator}")
    return energies


def _check_calculator(calculator: str, settings) -> None:
    if settings.mlip and calculator != settings.mlip:
        raise SettingsMismatch(f"check 8: PROJECT.md locks the potential {settings.mlip}; {calculator} was asked for")


def _relaxed(atoms, label: str, role: Role, calculator: str, fmax: float, steps: int, settings) -> RelaxationResult:
    """One relaxation, cached on structure, potential, settings and task; the relaxed structure written beside its trajectory."""
    sh = project.settings_hash(settings)
    cache = for_run()
    key = cache.key(artifacts.structure_hash(atoms), calculator, sh, f"relax fmax={fmax} steps={steps}") if cache else None
    hit = cache.get(key) if cache else None
    if hit:
        return RelaxationResult.model_validate({**hit, "cache_hit": True})
    run = current_run()
    traj = run.dir / "structures" / f"{label}-relax.traj" if run else None
    adapter = calculators.get(calculator)
    relaxed, converged, n, fmax_reached = adapter.relax(atoms, fmax=fmax, steps=steps, trajectory=str(traj) if traj else None)
    energy = float(relaxed.get_potential_energy())
    if not math.isfinite(energy):
        raise FloatingPointError(f"{label}: {calculator} returned a non-finite energy")
    ref = artifacts.write(relaxed, f"{label}-relaxed", role, energy_eV=energy, settings_hash=sh, calculator=calculator)
    result = RelaxationResult(candidate_id=label, energy_eV=energy, fmax_eV_per_A=fmax_reached, steps=n, converged=converged,
                              trajectory_path=str(traj.relative_to(run.dir)) if traj else None, calculator=calculator, structure=ref)
    if cache:
        cache.put(key, result)
    return result
