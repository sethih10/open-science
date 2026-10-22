"""The pull-force pre-filter. Tools: pull_force_screen. Defined in fragplace.registry."""
from __future__ import annotations

from typing import List

import numpy as np

from .. import calculators
from ..runtime import artifacts, geometry, project
from ..runtime.cache import for_run
from ..runtime.journal import log, traced
from ..schemas.records import Candidate, ForceScreen


@traced(step="3.3", tool="pull_force_screen")
def pull_force_screen(candidates: List[Candidate], calculator: str) -> List[ForceScreen]:
    """One MLIP force call per pair; the force on B along the A–B axis; a pull towards A above the threshold queues the pair last, never drops it.

    Board steps: 3.3. Status: core. Lane: gpu. Allowed roles: solution-planner.

    Inputs:
        candidates: list[Candidate]
        calculator: str
    Outputs:
        screens: list[ForceScreen], queue order
    Checks:
        - one force call, no relaxation
    Thresholds:
        threshold_eV_per_A: open: team decision
    Wraps:
        - fragplace.calculators
    Logs: force per pair; queue order.

    The force is the net force on B's atoms along the in-plane axis from B's centre to A's, positive towards A;
    the axis lies in the surface plane, so the surface's pull on B, mostly along the normal, is not counted as a
    pull towards A. Flagged pairs keep their relative order behind the unflagged ones.
    """
    settings = project.current_settings()
    threshold = float(project.decision("pull_force_screen", "threshold_eV_per_A", settings))
    sh = project.settings_hash(settings)
    cache = for_run()
    adapter = None
    measured = []
    for c in candidates:
        atoms = artifacts.read(c.structure)
        a, b = artifacts.fragment_indices(atoms, "A"), artifacts.fragment_indices(atoms, "B")
        if not a or not b:
            raise ValueError(f"{c.id} holds no pair: fragment A {len(a)} atoms, fragment B {len(b)} atoms")
        key = cache.key(artifacts.structure_hash(atoms), calculator, sh, "forces") if cache else None
        forces = cache.get(key) if cache else None
        if forces is None:
            adapter = adapter or calculators.get(calculator)
            forces = adapter.energy_forces(atoms)[1].tolist()
            if cache:
                cache.put(key, forces)
        forces = np.asarray(forces)
        axis = geometry.mic(artifacts.centre(atoms, a) - artifacts.centre(atoms, b), atoms.cell.array)[0]
        axis[2] = 0.0
        u = axis / np.linalg.norm(axis)
        on_b, on_a = float(forces[b].sum(axis=0) @ u), float(forces[a].sum(axis=0) @ -u)
        measured.append((c.id, on_b, on_a))
    flagged = {cid for cid, on_b, _ in measured if on_b > threshold}
    order = [m for m in measured if m[0] not in flagged] + [m for m in measured if m[0] in flagged]
    screens = [ForceScreen(candidate_id=cid, force_on_B_along_AB_eV_per_A=on_b, flagged=cid in flagged, threshold_eV_per_A=threshold,
                           queue_position=k) for k, (cid, on_b, _) in enumerate(order)]
    for cid, on_b, on_a in measured:
        log("pull_force_screen", f"{cid}: force on B towards A {on_b:+.3f} eV/Å, on A towards B {on_a:+.3f} eV/Å"
                                 + (f", above {threshold}: queued last" if cid in flagged else ""))
    log("pull_force_screen", "queue: " + ", ".join(s.candidate_id for s in screens))
    return screens
