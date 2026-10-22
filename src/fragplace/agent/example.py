"""The example campaign: *OH on Pt(111) built and relaxed with a named potential, so the pipeline can be tried
without supplied inputs; and init_campaign, which starts a campaign from the three supplied structures.

The example's structures are the test fixture's: a 3x3 four-layer slab with the bottom two layers fixed, OH in a
box, OH at the fcc hollow. Its PROJECT.md carries the test suite's value for every open decision and says so at
the top: they are test values, not team decisions, and no number from the example means anything about Pt.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from ..errors import FragPlaceError
from ..runtime import artifacts, project
from ..schemas.records import Role, Settings
from .campaign import Campaign

ROOT = Path(__file__).resolve().parents[3]
TEST_DECISIONS: Dict[str, Any] = {   # the values of tests/conftest.py, the gas reference excepted
    "structure_retrieval.image_measure": "own_image",
    "calculation_protocol.convergence_target_meV": 25, "calculation_protocol.gas_references": ["OH"],
    "mlip_selection.candidates": ["emt"], "mlip_selection.label_count": 3,
    "adsorbate_placement.displacement_amplitude_A": 0.1, "adsorbate_placement.fragment_A_fixed_at_old_site": True,
    "pair_enumeration.d_definition": "vacuum", "pair_enumeration.upper_bound_A": 5.0,
    "pull_force_screen.threshold_eV_per_A": 0.5,
    "anomaly_filter.AB_bond_reformed_A": 1.3, "anomaly_filter.migrated": 1.0, "anomaly_filter.dissociated": 1.25,
    "anomaly_filter.reconstructed": 0.5, "anomaly_filter.imaginary_noise_cm": 50.0, "anomaly_filter.expected_range_width_eV": 2.0,
    "anomaly_filter.magnetism_collapsed": 0.1, "anomaly_filter.intercalated": 0.0, "anomaly_filter.frequencies_source": "mlip",
    "soap_clustering.per_cluster": 3,
    "uncertainty_estimation.escalation_threshold_eV": 0.1, "uncertainty_estimation.label_count": 3,
    "ranking.shortlist_size": 5,
}
BANNER = ("> **Example campaign.** OH on Pt(111) with the {calc} potential. Every value under `decisions` is a test value from "
          "`tests/conftest.py`, not a team decision; replace them before trusting a number.\n\n")


def init_campaign(root: Path, name: str, slab: str, adsorbate_vacuum: str, initial_state: str, bond_to_break: Tuple[int, int],
                  energies: Optional[Sequence[float]] = None, options: Optional[Dict[str, Any]] = None,
                  calculator: Optional[str] = None) -> Campaign:
    """Copy the three supplied structures into runs/<name>/inputs/ with their energies, read from the files or given
    in the order slab, adsorbate in vacuum, initial state, and PROJECT.md from the template when the run has none.
    calculator names the method all three were relaxed with, when it is known, for check 8."""
    from ase.io import read
    c = Campaign(root, name)
    if "inputs" in c.data:
        raise FragPlaceError(f"campaign {name} already has inputs at {c.run.dir}")
    refs = {}
    slab_atoms = None
    for k, (key, path, role) in enumerate((("slab", slab, Role.slab), ("adsorbate_vacuum", adsorbate_vacuum, Role.adsorbate_vacuum),
                                           ("initial_state", initial_state, Role.initial_state))):
        atoms = read(path)
        energy = float(energies[k]) if energies else (float(atoms.get_potential_energy()) if atoms.calc is not None else None)
        if key == "slab":
            if artifacts.TAG_SURFACE not in set(atoms.get_tags()):
                artifacts.tag_slab_layers(atoms)
            slab_atoms = atoms
        elif key == "initial_state" and slab_atoms is not None and len(atoms) > len(slab_atoms):
            atoms.set_tags(list(slab_atoms.get_tags()) + [artifacts.TAG_A] * (len(atoms) - len(slab_atoms)))
        refs[key] = artifacts.write(atoms, key, role, energy_eV=energy, calculator=calculator, directory=c.run.dir / "inputs")
    if not (c.run.dir / "PROJECT.md").exists():
        (c.run.dir / "PROJECT.md").write_text((Path(root) / "PROJECT.md").read_text() if (Path(root) / "PROJECT.md").exists()
                                              else (ROOT / "PROJECT.md").read_text())
    c.put("inputs", {**refs, "bond_to_break": list(bond_to_break)})
    c.put("options", options or {})
    return c


def build_example(root: Path, name: str, calculator: str = "emt", options: Optional[Dict[str, Any]] = None) -> Campaign:
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
    c = init_campaign(root, name, *paths, bond_to_break=(0, 1), options={"example": calculator, **(options or {})}, calculator=calculator)
    path = c.run.dir / "PROJECT.md"
    s = project.read(path)
    decisions = {**TEST_DECISIONS, "mlip_selection.candidates": [calculator]}
    s = Settings.model_validate({**s.model_dump(), "protocol": "oc20", "decisions": decisions,
                                 "protocol_reason": "the settings record of the template, RPBE, PAW and 350 eV, is OC20's; this example relaxes "
                                                    f"everything with {calculator}, so the record describes no structure here and no DFT value is used"})
    project.write(path, s)
    text = path.read_text()
    title, _, rest = text.partition("\n\n")
    path.write_text(f"{title}\n\n{BANNER.format(calc=calculator)}{rest}")
    return c
