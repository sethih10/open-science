"""The test system every tool test shares: OH on Pt(111) with ASE's EMT potential, the nearest-first pipeline's
first case, built in a temporary run directory with a locked PROJECT.md whose decisions carry test values for
every threshold marked open. Tests that need ASE skip when it is not installed."""
from fragplace.execution.local import limit_threads

limit_threads()      # as fragplace.cli.main does, before numpy loads

from pathlib import Path  # noqa: E402

import pytest

from fragplace.runtime import project
from fragplace.runtime.journal import Run, set_run
from fragplace.schemas.records import GasReference, Settings

DECISIONS = {
    "structure_retrieval.image_measure": "own_image", "anomaly_filter.frequencies_source": "mlip",
    "calculation_protocol.convergence_target_meV": 25, "calculation_protocol.gas_references": ["H2", "H2O"],
    "mlip_selection.candidates": ["emt"], "mlip_selection.label_count": 3,
    "adsorbate_placement.displacement_amplitude_A": 0.1, "adsorbate_placement.fragment_A_fixed_at_old_site": True,
    "pair_enumeration.d_definition": "vacuum", "pair_enumeration.upper_bound_A": 5.0,
    "pull_force_screen.threshold_eV_per_A": 0.5,
    "anomaly_filter.AB_bond_reformed_A": 1.3, "anomaly_filter.migrated": 1.0, "anomaly_filter.dissociated": 1.25,
    "anomaly_filter.reconstructed": 0.5, "anomaly_filter.imaginary_noise_cm": 50.0, "anomaly_filter.expected_range_width_eV": 2.0,
    "anomaly_filter.magnetism_collapsed": 0.1, "anomaly_filter.intercalated": 0.0,
    # Desorbed, intercalated, A–B bond re-formed and periodic image mean something on an unrelaxed placed structure;
    # 2, 3 and 4 would compare it with itself, and 5 to 8 need a calculation.
    "anomaly_filter.checks_before_relaxation": [1, 9, 10, 11],
    "soap_clustering.per_cluster": 3,
    "uncertainty_estimation.escalation_threshold_eV": 0.1, "uncertainty_estimation.label_count": 3,
    "ranking.shortlist_size": 5,
}


def test_settings(**over) -> Settings:
    base = dict(metal="Pt", facet="111", adsorbate="OH", product=("O", "H"), functional="RPBE", cutoff_eV=350.0, kmesh=(4, 4, 1),
                smearing="MP", sigma_eV=0.1, layers=4, fixed_layers=2, vacuum_A=15.0, cell_repeat=(3, 3), mlip="emt", mlip_committee=["emt"],
                gas_references=[GasReference(species="H2", energy_eV=-6.77), GasReference(species="H2O", energy_eV=-14.22)],
                protocol="oc20", protocol_reason="test", decisions=dict(DECISIONS))
    base.update(over)
    return Settings(**base)


@pytest.fixture
def settings() -> Settings:
    return project.lock(test_settings(), approved_by="team")


@pytest.fixture
def run(tmp_path: Path, settings: Settings) -> Run:
    """A run directory with a locked PROJECT.md; the current run for the trace and for current_settings()."""
    r = Run(tmp_path, "test")
    project.write(r.dir / "PROJECT.md", settings)
    set_run(r)
    yield r
    set_run(None)


@pytest.fixture
def ase():
    return pytest.importorskip("ase")


@pytest.fixture
def pt111(ase, run: Run):
    """Pt(111), 3x3, four layers, bottom two fixed, EMT; tags 1 on the top layer, 0 below; a dict of the three
    inputs as atoms and as refs: slab, OH in vacuum, OH at the fcc site; plus O and H indices in the adsorbate."""
    return make_inputs(run)


def make_inputs(run: Run) -> dict:
    """The three inputs of the pt111 fixture, written into the run."""
    from ase import Atoms
    from ase.build import add_adsorbate, fcc111
    from ase.constraints import FixAtoms
    from fragplace.calculators import get
    from fragplace.runtime import artifacts
    from fragplace.schemas.records import Role

    calc = get("emt")
    slab = fcc111("Pt", size=(3, 3, 4), vacuum=7.5)
    layer_tags = slab.get_tags()                       # fcc111: 1 is the top layer, 4 the bottom
    slab.set_constraint(FixAtoms(indices=[i for i, t in enumerate(layer_tags) if t >= 3]))
    slab.set_tags([artifacts.TAG_SURFACE if t == 1 else artifacts.TAG_SUBSURFACE for t in layer_tags])
    slab, _, _, _ = calc.relax(slab, fmax=0.05, steps=60)
    e_slab = calc.energy_forces(slab)[0]

    oh = Atoms("OH", positions=[[0, 0, 0], [0, 0, 0.97]], cell=[10, 10, 10], pbc=True)
    oh.set_tags([artifacts.TAG_A, artifacts.TAG_B])
    oh, _, _, _ = calc.relax(oh, fmax=0.05, steps=60)
    e_oh = calc.energy_forces(oh)[0]

    initial = slab.copy()
    ads = Atoms("OH", positions=[[0, 0, 0], [0, 0, 0.97]])
    ads.set_tags([artifacts.TAG_A, artifacts.TAG_B])
    add_adsorbate(initial, ads, height=1.9, position="fcc")
    initial.set_constraint(slab.constraints)
    initial, _, _, _ = calc.relax(initial, fmax=0.05, steps=80)
    e_is = calc.energy_forces(initial)[0]

    sh = project.settings_hash(project.read(run.dir / "PROJECT.md"))
    refs = {
        "slab": artifacts.write(slab, "slab", Role.slab, energy_eV=e_slab, settings_hash=sh, calculator="emt"),
        "adsorbate_vacuum": artifacts.write(oh, "OH-vacuum", Role.adsorbate_vacuum, energy_eV=e_oh, settings_hash=sh, calculator="emt"),
        "initial_state": artifacts.write(initial, "initial-state", Role.initial_state, energy_eV=e_is, settings_hash=sh, calculator="emt"),
    }
    return {"atoms": {"slab": slab, "adsorbate_vacuum": oh, "initial_state": initial}, "refs": refs, "bond_to_break": (0, 1), "calculator": "emt"}
