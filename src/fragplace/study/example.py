"""The example study: *OH on Pt(111) built and relaxed with a named potential, so the pipeline can be tried
without supplied inputs; and init_study, which starts a study from the supplied structures.

The example's structures are the test fixture's: a 3x3 four-layer slab with the bottom two layers fixed, OH in a
box, OH at the fcc hollow. Its PROJECT.md carries the test suite's value for every open decision and says so at
the top: they are test values, not team decisions, and no number from the example means anything about Pt.
"""
from __future__ import annotations

from itertools import permutations, product
from math import factorial, prod
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..errors import FragPlaceError
from ..registry.tools import NO_DFT
from ..runtime import artifacts, geometry, project
from ..schemas.records import Role, Settings
from ..tools.structure import MAX_SLAB_DRIFT_A, composition, species_name
from .store import Study

ROOT = Path(__file__).resolve().parents[3]
MAX_MATCHES = 40320          # the orderings of the adsorbate's atoms tried against the initial state's, 8! at most
MAX_MISFIT_A = 1.0           # adsorption changes no distance within the molecule by more than this, or the files hold two molecules
SAME_SHAPE_A = 0.05          # two orderings fit the molecule equally when their worst distances differ by less than this
TEST_DECISIONS: Dict[str, Any] = {   # the values of tests/conftest.py, the gas reference and the DFT-only convergence target excepted
    "structure_retrieval.image_measure": "own_image",
    "calculation_protocol.gas_references": ["OH"],
    "mlip_selection.candidates": ["emt"], "mlip_selection.label_count": 3,
    "adsorbate_placement.displacement_amplitude_A": 0.1, "adsorbate_placement.fragment_A_fixed_at_old_site": True,
    "pair_enumeration.d_definition": "vacuum", "pair_enumeration.upper_bound_A": 5.0,
    "pull_force_screen.threshold_eV_per_A": 0.5,
    "anomaly_filter.AB_bond_reformed_A": 1.3, "anomaly_filter.migrated": 1.0, "anomaly_filter.dissociated": 1.25,
    "anomaly_filter.reconstructed": 0.5, "anomaly_filter.imaginary_noise_cm": 50.0, "anomaly_filter.expected_range_width_eV": 2.0,
    "anomaly_filter.magnetism_collapsed": 0.1, "anomaly_filter.intercalated": 0.0, "anomaly_filter.frequencies_source": "mlip",
    "anomaly_filter.checks_before_relaxation": [1, 9, 10, 11],
    "soap_clustering.per_cluster": 3,
    "uncertainty_estimation.escalation_threshold_eV": 0.1, "uncertainty_estimation.label_count": 3,
    "ranking.shortlist_size": 5,
}
BANNER = ("> **Example study.** OH on Pt(111) with the {calc} potential. Every value under `decisions` is a test value from "
          "`tests/conftest.py`, not a team decision; replace them before trusting a number.\n\n")


def init_study(root: Path, name: str, slab: str, adsorbate_vacuum: str, initial_state: str, bond_to_break: Tuple[int, int],
               energies: Optional[Sequence[float]] = None, options: Optional[Dict[str, Any]] = None,
               calculator: Optional[str] = None, fragment_A_vacuum: Optional[str] = None, fragment_B_vacuum: Optional[str] = None,
               facet: Optional[str] = None) -> Study:
    """Copy the supplied structures into runs/<name>/inputs/ with their energies, read from the files or given in the
    order slab, adsorbate in vacuum, initial state, then A and B in vacuum when supplied; and write the study's
    system into its PROJECT.md, from the template when the run has none, before the lock. calculator names the
    method the inputs were relaxed with, when it is known, for check 8.

    The system is read from the files: the adsorbate is AB's formula, H2O; the product the two sides of the bond,
    A's side first, each written from its binding atom, OH and H; the metal the slab's reduced formula, NaCl; the
    facet as given. A name PROJECT.md holds with the same composition stays, so OH is not rewritten HO; without a
    facet, PROJECT.md's stands only when its metal is the slab's. A fragment file must hold its side of the bond.
    An initial state that is not the slab's atoms followed by AB's is matched to them, the slab's atoms by species
    and nearest position and AB's by species and the distances within the molecule, reordered, and the
    reordering goes to the trace; one that cannot be matched is refused. Nothing is written before every check
    has passed."""
    from ase.io import read
    c = Study(root, name)
    if "inputs" in c.data:
        raise FragPlaceError(f"study {name} already has inputs at {c.run.dir}")
    files = [("slab", slab, Role.slab), ("adsorbate_vacuum", adsorbate_vacuum, Role.adsorbate_vacuum), ("initial_state", initial_state, Role.initial_state),
             ("fragment_A_vacuum", fragment_A_vacuum, Role.fragment_A_vacuum), ("fragment_B_vacuum", fragment_B_vacuum, Role.fragment_B_vacuum)]
    atoms: Dict[str, Any] = {}
    energy: Dict[str, Optional[float]] = {}
    for k, (key, path, _) in enumerate(files):
        if path is not None:
            atoms[key] = read(path)
            energy[key] = float(energies[k]) if energies and k < len(energies) else _energy(atoms[key])
    s_atoms, ab = atoms["slab"], atoms["adsorbate_vacuum"]
    tags = set(s_atoms.get_tags())
    if artifacts.TAG_SURFACE not in tags or not tags <= {artifacts.TAG_SUBSURFACE, artifacts.TAG_SURFACE}:
        artifacts.tag_slab_layers(s_atoms)               # a builder's layer numbers would read as fragment tags

    i, j = (int(x) for x in bond_to_break)
    if not (0 <= i < len(ab) and 0 <= j < len(ab)) or i == j:
        raise FragPlaceError(f"the bond {i}, {j} does not name two atoms of {ab.get_chemical_formula()}")
    graph = geometry.bonds(ab, range(len(ab)))
    if (min(i, j), max(i, j)) not in graph:
        raise FragPlaceError(f"atoms {i} and {j} of {ab.get_chemical_formula()} are not bonded in vacuum")
    side = {k: part for part in geometry.components(range(len(ab)), [b for b in graph if set(b) != {i, j}]) for k in part}
    if side[i] is side[j]:
        raise FragPlaceError(f"breaking {i}, {j} leaves {ab.get_chemical_formula()} in one piece; the bond is in a ring")
    names = (species_name(ab[side[i]], side[i].index(i)), species_name(ab[side[j]], side[j].index(j)))
    for key, named in (("fragment_A_vacuum", names[0]), ("fragment_B_vacuum", names[1])):
        if key in atoms and composition(atoms[key].get_chemical_formula()) != composition(named):
            raise FragPlaceError(f"{key} holds {atoms[key].get_chemical_formula()}; breaking {i}, {j} of {ab.get_chemical_formula()} "
                                 f"leaves {named} on that side, A's side first")
    initial, note = _in_order(s_atoms, ab, atoms["initial_state"], (i, j))
    initial.set_tags(list(s_atoms.get_tags()) + [artifacts.TAG_A] * len(ab))
    atoms["initial_state"] = initial

    path = c.run.dir / "PROJECT.md"
    template = path if path.exists() else (Path(root) / "PROJECT.md" if (Path(root) / "PROJECT.md").exists() else ROOT / "PROJECT.md")
    s = project.read(template)
    if s.locked:
        raise FragPlaceError(f"{template} is locked; a new system means a new study")
    changes = _system(s, s_atoms, ab, names, facet)

    refs = {key: artifacts.write(atoms[key], key, role, energy_eV=energy[key], calculator=calculator, directory=c.run.dir / "inputs")
            for key, file, role in files if file is not None}
    if not path.exists():
        path.write_text(template.read_text())
    if changes:
        project.write(path, s)
    given = {key: str(file) for key, file, _ in files if file is not None}
    for message in ([note] if note else []) + (["PROJECT.md from the inputs: " + "; ".join(changes)] if changes else []):
        c.run.event("1", "init_study", "tool", given, "", message=message)
    c.put("inputs", {**refs, "bond_to_break": [i, j]})
    c.put("options", options or {})
    return c


def _energy(atoms) -> Optional[float]:
    """The energy a file carries, or None."""
    from ase.calculators.calculator import PropertyNotImplementedError
    if atoms.calc is None:
        return None
    try:
        return float(atoms.get_potential_energy())
    except PropertyNotImplementedError:
        return None


def _system(s: Settings, slab, ab, names: Tuple[str, str], facet: Optional[str]) -> List[str]:
    """PROJECT.md's metal, adsorbate, product and facet set from the inputs, in place; a name of the same composition
    stays. What changed, each with where it came from."""
    metal = slab.get_chemical_formula(mode="metal", empirical=True)
    same_metal = composition(s.metal, reduce=True) == composition(metal, reduce=True)
    changes = []
    if not same_metal:
        changes.append(f"metal {s.metal} to {metal}, the slab's reduced formula")
        old_metal, s.metal = s.metal, metal
    adsorbate = species_name(ab)
    if composition(s.adsorbate) != composition(adsorbate):
        changes.append(f"adsorbate {s.adsorbate} to {adsorbate}, the adsorbate in vacuum")
        s.adsorbate = adsorbate
    product = tuple(held if composition(held) == composition(new) else new for held, new in zip(s.product, names))
    if product != tuple(s.product):
        changes.append(f"product {s.product[0]} + {s.product[1]} to {product[0]} + {product[1]}, the two sides of the bond, A's first")
        s.product = product
    if facet is not None:
        given = str(facet).strip().strip("()")
        if given != s.facet:
            changes.append(f"facet {s.facet} to {given}, as given")
            s.facet = given
    elif not same_metal:
        raise FragPlaceError(f"PROJECT.md's facet {s.facet} belongs to {old_metal}, not to the {metal} slab: give the facet")
    return changes


def _in_order(slab, ab, initial, bond: Tuple[int, int]) -> Tuple[Any, str]:
    """The initial state as the slab's atoms in the slab's order followed by AB's in AB's order, and a note for the
    trace when it had to be reordered. The slab's atoms are matched one to one by species and nearest position; the
    atoms left over are AB's, matched by species and the distances within the molecule, which adsorption changes
    little. When two orderings fit AB equally and put the named bond on different atoms, the note says which."""
    from scipy.optimize import linear_sum_assignment
    n, m, cell = len(slab), len(ab), slab.cell.array
    if len(initial) != n + m:
        raise FragPlaceError(f"the initial state has {len(initial)} atoms; the slab and the adsorbate have {n} and {m}")
    if not np.allclose(initial.cell.array, cell, atol=1e-3):
        raise FragPlaceError("the initial state and the slab have different cells")

    def apart(a, b) -> np.ndarray:
        return np.linalg.norm(geometry.mic(np.asarray(a) - np.asarray(b), cell), axis=-1)

    if (list(initial.numbers[:n]) == list(slab.numbers) and list(initial.numbers[n:]) == list(ab.numbers)
            and apart(initial.positions[:n], slab.positions).max() <= MAX_SLAB_DRIFT_A):
        return initial, ""
    match: Dict[int, int] = {}
    worst = 0.0
    for z in sorted(set(slab.numbers)):
        rows = [k for k in range(n) if slab.numbers[k] == z]
        cols = [k for k in range(len(initial)) if initial.numbers[k] == z]
        if len(cols) < len(rows):
            raise FragPlaceError(f"the initial state has {len(cols)} atoms of element {z}; the slab alone has {len(rows)}")
        d = np.array([apart(initial.positions[cols], slab.positions[k]) for k in rows])
        r, col = linear_sum_assignment(d)
        worst = max(worst, float(d[r, col].max()))
        match.update({rows[a]: cols[b] for a, b in zip(r, col)})
    if worst > MAX_SLAB_DRIFT_A:
        raise FragPlaceError(f"a slab atom of the initial state sits {worst:.2f} Å from its match in the slab: not the same slab")
    order = [match[k] for k in range(n)]
    rest = [k for k in range(len(initial)) if k not in set(order)]
    if sorted(initial.numbers[rest]) != sorted(ab.numbers):
        raise FragPlaceError(f"the atoms of the initial state beyond the slab, {initial[rest].get_chemical_formula()}, are not the adsorbate's, "
                             f"{ab.get_chemical_formula()}")
    elements = sorted(set(ab.numbers))
    slots = {z: [k for k in range(m) if ab.numbers[k] == z] for z in elements}
    pools = {z: [k for k in rest if initial.numbers[k] == z] for z in elements}
    if prod(factorial(len(v)) for v in slots.values()) > MAX_MATCHES:
        raise FragPlaceError("the adsorbate has too many atoms of one element to match; write the initial state as the slab's atoms followed by "
                             "the adsorbate's, in the order of the adsorbate in vacuum")
    target = ab.get_all_distances(mic=True)
    fits = []
    for choice in product(*(permutations(pools[z]) for z in elements)):
        ads = [0] * m
        for z, picked in zip(elements, choice):
            for slot, k in zip(slots[z], picked):
                ads[slot] = k
        fits.append((float(np.abs(initial[ads].get_all_distances(mic=True) - target).max()), ads))
    fits.sort(key=lambda f: f[0])
    misfit, ads = fits[0]
    if misfit > MAX_MISFIT_A:
        raise FragPlaceError(f"the adsorbate of the initial state differs from the adsorbate in vacuum by {misfit:.2f} Å in an interatomic distance")
    i, j = bond
    others = sorted({(o[i], o[j]) for f, o in fits[1:] if f - misfit < SAME_SHAPE_A} - {(ads[i], ads[j])})
    note = (f"the initial state was not the slab's atoms followed by the adsorbate's: reordered, the {n} slab atoms matched by species and "
            f"nearest position, up to {worst:.2f} Å apart, and the {m} adsorbate atoms by species and the distances within the molecule, "
            f"up to {misfit:.2f} Å off those in vacuum")
    if others:
        note += (f"; the adsorbate in vacuum fits more than one ordering equally, so the bond {i}, {j} was taken as atoms {ads[i]} and {ads[j]} of "
                 f"the file, not {', '.join(f'{a} and {b}' for a, b in others)}; structure_retrieval says whether the two are the same by symmetry")
    return initial[order + ads], note


def build_example(root: Path, name: str, calculator: str = "emt", options: Optional[Dict[str, Any]] = None) -> Study:
    """The three inputs of *OH on Pt(111), relaxed with `calculator`, and a PROJECT.md ready to lock."""
    from ase import Atoms
    from ase.build import add_adsorbate, fcc111
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.constraints import FixAtoms
    from .. import calculators
    adapter = calculators.get(calculator)
    work = Path(root) / "runs" / name / "example-inputs"
    work.mkdir(parents=True, exist_ok=True)

    slab = fcc111("Pt", size=(3, 3, 4), vacuum=7.5)
    layers = slab.get_tags()                       # fcc111 numbers the layers 1 at the top to 4 at the bottom
    slab.set_constraint(FixAtoms(indices=[i for i, t in enumerate(layers) if t >= 3]))
    slab.set_tags([artifacts.TAG_SURFACE if t == 1 else artifacts.TAG_SUBSURFACE for t in layers])
    slab = adapter.relax(slab, fmax=0.03, steps=200)[0]
    oh = Atoms("OH", positions=[[0, 0, 0], [0, 0, 0.97]], cell=[12, 12, 12], pbc=True)
    oh = adapter.relax(oh, fmax=0.03, steps=200)[0]
    initial = slab.copy()
    ads = Atoms("OH", positions=[[0, 0, 0], [0, 0, 0.97]])
    ads.set_tags([artifacts.TAG_A, artifacts.TAG_B])
    add_adsorbate(initial, ads, height=1.9, position="fcc")
    initial.set_constraint(slab.constraints)
    initial = adapter.relax(initial, fmax=0.03, steps=300)[0]
    paths = []
    for label, atoms in (("slab", slab), ("OH-vacuum", oh), ("OH-fcc", initial)):
        out = atoms.copy()
        out.calc = SinglePointCalculator(out, energy=float(atoms.get_potential_energy()))
        out.info = {}
        path = work / f"{label}.extxyz"
        out.write(path, format="extxyz")
        paths.append(str(path))
    c = init_study(root, name, *paths, bond_to_break=(0, 1), options={"example": calculator, **(options or {})}, calculator=calculator)
    path = c.run.dir / "PROJECT.md"
    s = project.read(path)
    decisions = {**TEST_DECISIONS, "mlip_selection.candidates": [calculator]}
    s = Settings.model_validate({**s.model_dump(), "protocol": NO_DFT, "decisions": decisions,
                                 "protocol_reason": f"this example relaxes everything with {calculator} and runs no DFT, so the potential computes every energy"})
    project.write(path, s)
    text = path.read_text()
    title, _, rest = text.partition("\n\n")
    path.write_text(f"{title}\n\n{BANNER.format(calc=calculator)}{rest}")
    return c
