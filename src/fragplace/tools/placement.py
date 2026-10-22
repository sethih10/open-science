"""Placing fragments by script, and minima hopping as the alternative generator. Tools: adsorbate_placement, minima_hopping. Defined in fragplace.registry."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from .. import calculators
from ..runtime import artifacts, geometry, project
from ..runtime.journal import content_hash, current_run, log, traced
from ..schemas.records import Candidate, Role, SiteEnumeration, StructureRef

HEIGHT_RANGE_A = (2.0, 3.0)    # the docs' start: 2 to 3 Å above the site, never 10
SAME_ORIENTATION_A = 0.05      # two orientations are one when every atom lands within this of an atom of the same species
HOOKE_K_EV_PER_A2 = 5.0        # stiffness of the springs that keep a fragment whole during hopping


@traced(step="4", tool="adsorbate_placement")
def adsorbate_placement(sites: SiteEnumeration, fragment: StructureRef, site_index: int, orientation: int, height_A: float, displacement_amplitude_A: float, base: Optional[Candidate] = None) -> Candidate:
    """Place fragment A at every symmetry-distinct site near its old site and B at a given site, by script; orientations under the site's stabiliser; a random displacement before relaxation.

    Board steps: 3.5, 4. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        sites: SiteEnumeration
        fragment: StructureRef
        site_index: int
        orientation: int
        height_A: float
        displacement_amplitude_A: float
        base: Candidate | None, the candidate the fragment is added to; the slab of the enumeration when None
    Outputs:
        candidate: Candidate
    Checks:
        - start 2 to 3 Å above the site
        - the LLM never places atoms
    Thresholds:
        displacement_amplitude_A: open: team decision
        fragment_A_fixed_at_old_site: open: team decision
    Wraps:
        - ase.build.add_adsorbate
        - fairchem.data.oc.core.AdsorbateSlabConfig as the baseline
    Logs: site, orientation, height, displacement and random draw.

    The binding atom goes height_A above the surface plane over the site; a fragment of several atoms first turns
    so its other atoms point away from the surface. Orientation k is the k-th distinct image of the fragment under
    the site group; a single atom has one. Every atom of the placed fragment then moves by a draw uniform in
    [-a, a] per axis, a the locked amplitude, from a generator seeded by the candidate's id, so a rerun places the
    same atoms. The id is A<site> or B<site>, after the base's id when there is one: A004-B017.
    """
    settings = project.current_settings()
    amplitude = float(project.decision("adsorbate_placement", "displacement_amplitude_A", settings))
    if abs(float(displacement_amplitude_A) - amplitude) > 1e-12:
        raise ValueError(f"displacement {displacement_amplitude_A} Å differs from the locked decision adsorbate_placement.displacement_amplitude_A = {amplitude}")
    if not HEIGHT_RANGE_A[0] <= float(height_A) <= HEIGHT_RANGE_A[1]:
        raise ValueError(f"start height {height_A} Å is outside {HEIGHT_RANGE_A[0]} to {HEIGHT_RANGE_A[1]} Å above the site")
    frag = artifacts.read(fragment)
    tags = set(frag.get_tags())
    if tags not in ({artifacts.TAG_A}, {artifacts.TAG_B}):
        raise ValueError(f"{fragment.path} is not one fragment: tags {sorted(tags)}, expected all {artifacts.TAG_A} or all {artifacts.TAG_B}")
    letter = "A" if tags == {artifacts.TAG_A} else "B"
    host = artifacts.read(base.structure) if base else artifacts.read(sites.slab)
    cell = host.cell.array
    site = sites.sites[int(site_index)]

    shapes = orientations(frag, sites, int(site_index), cell)
    if not 0 <= int(orientation) < len(shapes):
        raise ValueError(f"orientation {orientation}: site {site_index} gives {len(shapes)} distinct orientations of {frag.get_chemical_formula()}")
    local = shapes[int(orientation)]
    cid = f"{letter}{int(site_index):03d}" + (f"o{int(orientation)}" if orientation else "")
    cid = f"{base.id}-{cid}" if base else cid
    seed = int(content_hash({"id": cid, "fragment": fragment.path})[:8], 16)
    draw = np.random.default_rng(seed).uniform(-amplitude, amplitude, size=(len(frag), 3))
    placed = frag.copy()
    placed.positions = local + np.array([site.position[0], site.position[1], artifacts.surface_plane_z(host) + float(height_A)]) + draw
    placed.set_cell(cell)
    out = host + placed
    out.set_constraint(host.constraints)
    out.info = {}
    ref = artifacts.write(out, cid, Role.candidate, settings_hash=project.settings_hash(settings))
    log("adsorbate_placement", f"{cid}: {letter} {frag.get_chemical_formula()} at site {site_index} ({site.label}), orientation "
                               f"{orientation} of {len(shapes)}, {height_A} Å up, displacement {amplitude} Å, seed {seed}, "
                               f"draw {np.round(draw, 4).tolist()}")
    return Candidate(id=cid, structure=ref, site_A=int(site_index) if letter == "A" else (base.site_A if base else None),
                     site_B=int(site_index) if letter == "B" else (base.site_B if base else None),
                     orientation=int(orientation), displacement_amplitude_A=amplitude, generator="enumeration", parent=base.id if base else None)


def orientations(frag, sites: SiteEnumeration, site_index: int, cell) -> List[np.ndarray]:
    """The distinct orientations of a fragment over a site, as positions relative to the point over the site: the
    fragment turned so its centre lies straight above its binding atom, then every operation of the site group."""
    b = artifacts.binding_atom(frag)
    rel = frag.positions - frag.positions[b]
    up = rel.mean(axis=0)
    if len(frag) > 1 and np.linalg.norm(up) > 1e-8:
        rel = rel @ _rotation(up / np.linalg.norm(up), np.array([0.0, 0.0, 1.0])).T
    shapes: List[np.ndarray] = []
    for op in geometry.stabiliser(sites, site_index, cell, tol_A=0.3):
        r = np.asarray(op.rotation)
        shape = rel @ r.T
        if not any(_same(shape, s, frag.numbers) for s in shapes):
            shapes.append(shape)
    return shapes or [rel]


def _rotation(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """The rotation that takes unit vector a onto unit vector b."""
    v, c = np.cross(a, b), float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def _same(p: np.ndarray, q: np.ndarray, numbers) -> bool:
    for z in set(numbers):
        a, b = p[numbers == z], q[numbers == z]
        if np.linalg.norm(a[:, None] - b[None], axis=-1).min(axis=1).max() > SAME_ORIENTATION_A:
            return False
    return True


@traced(step="3.6", tool="minima_hopping")
def minima_hopping(slab: StructureRef, fragments: Tuple[StructureRef, StructureRef], calculator: str, n_hops: int) -> List[Candidate]:
    """NEBscape's endpoint generator with the chosen potential as the alternative generator and the baseline policy our nearest-first choice is scored against.

    Board steps: 3.6. Status: core. Lane: gpu. Allowed roles: solution-planner.

    Inputs:
        slab: StructureRef
        fragments: tuple[StructureRef, StructureRef]
        calculator: str
        n_hops: int
    Outputs:
        candidates: list[Candidate] with generator minima_hopping
    Checks:
        - Hookean constraints keep A and B intact during hopping, as NEBscape
    Thresholds:
        none
    Wraps:
        - nebscape endpoint generator, MIT
        - ase.optimize.minimahopping.MinimaHopping
    Logs: hops; minima found.

    NEBscape's generator is not packaged, so ASE's MinimaHopping runs here with its own defaults, from the slab
    with A and B where the two refs put them; a ref that holds a whole candidate gives the atoms tagged as its
    fragment. Each bond inside a fragment gets a Hookean spring that acts beyond the bond length, so no fragment
    falls apart; nothing holds A and B apart, and the gate rejects a pair that bonded back.
    """
    from ase.constraints import FixAtoms, Hookean
    from ase.optimize.minimahopping import MinimaHopping
    from ase.io import read as ase_read
    settings = project.current_settings()
    host = artifacts.read(slab)
    frag_a, frag_b = artifacts.fragment_atoms(fragments[0], "A"), artifacts.fragment_atoms(fragments[1], "B")
    atoms = host + frag_a + frag_b
    fixed = [i for c in host.constraints if isinstance(c, FixAtoms) for i in c.get_indices()]
    n = len(host)
    springs = []
    for offset, frag in ((n, frag_a), (n + len(frag_a), frag_b)):
        idx = list(range(offset, offset + len(frag)))
        for i, j in geometry.bonds(atoms, idx):
            rt = geometry.BOND_MULT * sum(geometry.cutoffs(atoms, 1.0)[k] for k in (i, j))
            springs.append(Hookean(a1=i, a2=j, rt=rt, k=HOOKE_K_EV_PER_A2))
    atoms.set_constraint([FixAtoms(indices=fixed)] + springs)
    atoms.calc = calculators.get(calculator)._calc
    run = current_run()
    work = (run.dir if run else Path(".")) / "minima_hopping" / content_hash({"s": artifacts.structure_hash(atoms), "c": calculator, "n": n_hops})
    work.mkdir(parents=True, exist_ok=True)
    here = os.getcwd()
    os.chdir(work)
    try:
        MinimaHopping(atoms)(totalsteps=int(n_hops))
        minima = ase_read("minima.traj", index=":")
    finally:
        os.chdir(here)
    sh = project.settings_hash(settings)
    out = []
    for k, m in enumerate(minima):
        m.set_constraint([FixAtoms(indices=fixed)])
        m.set_tags(atoms.get_tags())
        ref = artifacts.write(m, f"MH{k:03d}", Role.candidate, energy_eV=float(m.get_potential_energy()), settings_hash=sh, calculator=calculator)
        out.append(Candidate(id=f"MH{k:03d}", structure=ref, generator="minima_hopping"))
    log("minima_hopping", f"{n_hops} hops with {calculator}, {len(springs)} fragment springs; {len(out)} minima in {work.name}")
    return out
