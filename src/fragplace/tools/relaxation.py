"""Relaxations and the reference energies, cached. Tools: relaxation, reference_energies. Defined in fragplace.registry."""
from __future__ import annotations

import math
from contextlib import closing
from typing import Dict, Iterator, List, Optional, Tuple

from .. import calculators
from ..errors import SettingsMismatch
from ..execution import pool
from ..runtime import artifacts, project
from ..runtime.cache import for_run
from ..runtime.journal import current_run, log, traced
from ..schemas.records import Candidate, RelaxationResult, Role, StructureRef

MAX_STEPS = 500      # the step cap of reference_energies, which takes none; the rollout passes the same to relaxation
# What E_ads of each fragment is against, as reference_energies logs it and the report reads it back
GAS_SUPPLIED = "the supplied A and B in vacuum"
GAS_CLEAVED = "the cleaved fragments alone in vacuum"


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
    displacement is adsorbate_placement's; constraints travel with the structure, and so does its info, which
    names the binding atoms of A and B. With FRAGPLACE_WORKERS, or the approved compute rule's workers, above 1, the
    relaxations run in execution.pool's processes, the CPUs shared among them; the records are the serial path's, in
    the same order, and this process alone writes the structures, the cache and the trace.
    """
    settings = project.current_settings()
    _check_calculator(calculator, settings)
    fmax, steps = float(fmax_eV_per_A), int(max_steps)
    n = pool.workers()
    results = (_pooled(candidates, calculator, fmax, steps, settings, n) if n > 1 and len(candidates) > 1 else
               (_relaxed(artifacts.read(c.structure), c.id, c.structure.role, calculator, fmax, steps, settings) for c in candidates))
    out = []
    for c, r in zip(candidates, results):
        out.append(r)
        log("relaxation", f"{c.id}: {r.steps} steps, fmax {r.fmax_eV_per_A:.3f} eV/Å, {'converged' if r.converged else 'NOT converged'}, "
                          f"E {r.energy_eV:.4f} eV{', cache hit' if r.cache_hit else ''}")
    return out


@traced(step="solution", tool="reference_energies")
def reference_energies(slab: StructureRef, fragments: Tuple[StructureRef, StructureRef], calculator: str,
                       gas: Optional[Tuple[StructureRef, StructureRef]] = None) -> Dict[str, float]:
    """E(A*), E(B*) and E(slab) each in its own cell with the chosen potential and the locked settings, for E(FS ∞) and the lateral interaction; and each fragment's adsorption energy against its own gas reference on the same potential.

    Board steps: solution. Status: core. Lane: gpu. Allowed roles: solution-planner.

    Inputs:
        slab: StructureRef
        fragments: tuple[StructureRef, StructureRef]
        calculator: str
        gas: tuple[StructureRef, StructureRef] | None, A and B in vacuum as supplied; the cleaved fragments when None
    Outputs:
        E_slab_eV: float
        E_A_eV: float
        E_B_eV: float
        E_inf_eV: float
        E_ads_A_eV: float
        E_ads_B_eV: float
    Checks:
        - same settings as every candidate, check 8
    Thresholds:
        none
    Wraps:
        - fragplace.calculators
    Logs: the three energies.

    Each fragment goes on the slab alone, where the ref puts it; a ref that holds a whole final state gives the
    atoms tagged as its fragment, so the separated product keeps the sites of the final state. The slab, slab plus
    A, slab plus B and the two gas references are relaxed by the relaxation tool with the locked force threshold,
    so each is in the trace with its steps and energy and counts in the report's cost. Their structures keep no info,
    binding atoms included, since only their energies are read. E(FS ∞) = E(A*) + E(B*) − E(slab), and E_ads(A*) =
    E(A*) − E(slab) − E(A in vacuum), with A in vacuum relaxed by the same potential so no two energy scales mix: the
    supplied structure when gas is given, else the cleaved fragment alone, centred in its cell.
    """
    settings = project.current_settings()
    _check_calculator(calculator, settings)
    sh = project.settings_hash(settings)
    host = artifacts.read(slab)
    stem = slab.path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    systems = {"E_slab_eV": (f"ref-{stem}", host)}
    for k, name in enumerate(("A", "B")):
        frag = artifacts.fragment_atoms(fragments[k], name)
        system = host + frag
        system.set_constraint(host.constraints)
        system.info = {}
        systems[f"E_{name}_eV"] = (f"ref-{name}-{artifacts.structure_hash(system)}", system)
        alone = artifacts.read(gas[k]) if gas else frag.copy()
        if not gas:
            alone.center()            # the same isolated fragment from every final state shares one cached relaxation
        alone.set_constraint()
        alone.info = {}
        systems[f"gas_{name}"] = (f"gas-{name}-{artifacts.structure_hash(alone)}", alone)
    refs = [Candidate(id=label, structure=artifacts.write(atoms, label, Role.reference, settings_hash=sh), generator="reference")
            for label, atoms in systems.values()]
    energy = {key: r.energy_eV for key, r in zip(systems, relaxation(refs, calculator, settings.force_threshold_eV_per_A, MAX_STEPS))}
    out = {key: energy[key] for key in ("E_slab_eV", "E_A_eV", "E_B_eV")}
    out["E_inf_eV"] = out["E_A_eV"] + out["E_B_eV"] - out["E_slab_eV"]
    out["E_ads_A_eV"] = out["E_A_eV"] - out["E_slab_eV"] - energy["gas_A"]
    out["E_ads_B_eV"] = out["E_B_eV"] - out["E_slab_eV"] - energy["gas_B"]
    formulas = [systems[f"gas_{name}"][1].get_chemical_formula() for name in ("A", "B")]
    log("reference_energies", "E(slab) {E_slab_eV:.4f}, E(A*) {E_A_eV:.4f}, E(B*) {E_B_eV:.4f}, E(FS inf) {E_inf_eV:.4f}, "
        "E_ads(A*) {E_ads_A_eV:.4f}, E_ads(B*) {E_ads_B_eV:.4f} eV".format(**out)
        + f", {calculator}; gas references {GAS_SUPPLIED if gas else GAS_CLEAVED}: {formulas[0]} "
          f"{energy['gas_A']:.4f} eV and {formulas[1]} {energy['gas_B']:.4f} eV")
    return out


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
    traj = _trajectory(label)
    adapter = calculators.get(calculator)
    relaxed, converged, n, fmax_reached = adapter.relax(atoms, fmax=fmax, steps=steps, trajectory=str(traj) if traj else None)
    return _kept(relaxed, label, role, calculator, float(relaxed.get_potential_energy()), n, fmax_reached, converged, sh, key)


def _trajectory(label: str):
    run = current_run()
    return run.dir / "structures" / f"{label}-relax.traj" if run else None


def _kept(relaxed, label: str, role: Role, calculator: str, energy: float, n: int, fmax_reached: float, converged: bool, sh: str,
          key: Optional[str]) -> RelaxationResult:
    """A finished relaxation as the parent keeps it: the relaxed structure written, the record cached."""
    if not math.isfinite(energy):
        raise FloatingPointError(f"{label}: {calculator} returned a non-finite energy")
    run, traj, cache = current_run(), _trajectory(label), for_run()
    ref = artifacts.write(relaxed, f"{label}-relaxed", role, energy_eV=energy, settings_hash=sh, calculator=calculator)
    result = RelaxationResult(candidate_id=label, energy_eV=energy, fmax_eV_per_A=fmax_reached, steps=n, converged=converged,
                              trajectory_path=str(traj.relative_to(run.dir)) if traj else None, calculator=calculator, structure=ref)
    if cache and key:
        cache.put(key, result)
    return result


def _pooled(candidates: List[Candidate], calculator: str, fmax: float, steps: int, settings, n: int) -> Iterator[RelaxationResult]:
    """The candidates relaxed in a pool of n processes, yielded in their order with the serial path's records: a
    cache hit as a hit, a structure met twice in one call relaxed once and the second a hit, as in the serial path.
    Workers only relax; this process writes every structure, cache entry and trace line."""
    sh = project.settings_hash(settings)
    cache = for_run()
    plan, jobs, first = [], [], set()
    for c in candidates:
        atoms = artifacts.read(c.structure)
        key = cache.key(artifacts.structure_hash(atoms), calculator, sh, f"relax fmax={fmax} steps={steps}") if cache else None
        hit = cache.get(key) if cache else None
        if hit:
            plan.append(("hit", RelaxationResult.model_validate({**hit, "cache_hit": True}), None, None))
        elif key is not None and key in first:
            plan.append(("again", None, None, key))
        else:
            first.add(key)
            traj = _trajectory(c.id)
            jobs.append((atoms, str(traj) if traj else None))
            plan.append(("run", c, atoms, key))
    procs, threads = pool.shape(len(jobs), n)
    log("relaxation", f"{len(jobs)} of {len(candidates)} candidates relaxed in a pool of {procs} processes, {threads} threads each")
    with closing(pool.relax_all(jobs, calculator, fmax, steps, n)) as answers:
        for kind, c, atoms, key in plan:
            if kind == "hit":
                yield c
            elif kind == "again":
                yield RelaxationResult.model_validate({**cache.get(key), "cache_hit": True})
            else:
                a = next(answers)
                relaxed = atoms.copy()
                relaxed.set_positions(a["positions"], apply_constraint=False)
                yield _kept(relaxed, c.id, c.structure.role, calculator, a["energy_eV"], a["steps"], a["fmax_eV_per_A"], a["converged"], sh, key)
