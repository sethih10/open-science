"""H2O* -> OH* + H* on NaCl(100), the first ionic substrate, on a synthetic stand-in built with ASE: rocksalt with
a = 5.64 Å, a 2x2 conventional surface cell of four layers, the bottom two fixed, 15 Å of vacuum, water with its O
2.4 Å above a Na and its two H atoms pointing down at the Cl on either side, and the molecules in boxes. No
structure is relaxed and none carries an energy, as the supplied inputs of the study carry none. The tests hold the
sites of a slab of two elements, A named by the bond the human gives, the system written into PROJECT.md from
the files, the geometric benchmark of the potentials, and EMT refusing Na and Cl."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import DECISIONS
from conftest import test_settings as settings_for
from fragplace import calculators
from fragplace.errors import FragPlaceError, SettingsMismatch
from fragplace.runtime import artifacts, geometry, project
from fragplace.runtime.journal import Run, set_run
from fragplace.schemas.records import Candidate, DescriptorCard, DoubtFlag, Role, StructureRef

pytest.importorskip("ase")
pytest.importorskip("spglib")
pytest.importorskip("scipy")

from fragplace.study.example import init_study  # noqa: E402
from fragplace.tools.clustering import ranking  # noqa: E402
from fragplace.tools.placement import adsorbate_placement  # noqa: E402
from fragplace.tools.sites import site_enumeration  # noqa: E402
from fragplace.tools.structure import structure_retrieval  # noqa: E402
from fragplace.tools.uncertainty import mlip_selection, system_class_of, uncertainty_estimation, unseen_chemistry  # noqa: E402

A_NACL = 5.64
LABELS = ("slab", "adsorbate_vacuum", "initial_state")


def nacl_settings(**over):
    decisions = {**DECISIONS, "mlip_selection.candidates": ["mace-mp-small"], "mlip_selection.label_count": 1}
    base = dict(metal="NaCl", facet="100", adsorbate="H2O", product=("OH", "H"), mlip=None, mlip_committee=[], decisions=decisions)
    return settings_for(**{**base, **over})


def structures() -> dict:
    """The stand-in: the slab, water, OH and H in vacuum, and water on the slab, in the slab's order then water's."""
    from ase import Atoms
    from ase.build import bulk
    from ase.constraints import FixAtoms
    slab = bulk("NaCl", "rocksalt", a=A_NACL, cubic=True).repeat((2, 2, 2))      # two (100) layers per cube, four in all
    slab.center(vacuum=7.5, axis=2)
    slab.pbc = (True, True, False)
    z = slab.positions[:, 2]
    slab.set_constraint(FixAtoms(indices=[k for k in range(len(slab)) if z[k] < z.min() + A_NACL / 2 + 0.1]))
    artifacts.tag_slab_layers(slab)
    middle = slab.cell.array[:2, :2].sum(axis=0) / 2
    na = min((k for k in artifacts.surface_indices(slab) if slab[k].symbol == "Na"), key=lambda k: np.linalg.norm(slab.positions[k, :2] - middle))
    o = slab.positions[na] + [0.0, 0.0, 2.4]
    down = [np.array([dx, 0.0, -2.4]) / np.hypot(dx, 2.4) for dx in (A_NACL / 2, -A_NACL / 2)]     # at the Cl on either side along x
    initial = slab.copy()
    initial += Atoms("OH2", positions=[o, o + 0.97 * down[0], o + 0.97 * down[1]])
    initial.set_constraint(slab.constraints)
    box, angle = [12.0] * 3, np.radians(104.5)
    water = Atoms("OH2", positions=[[6, 6, 6], [6.97, 6, 6], [6 + 0.97 * np.cos(angle), 6 + 0.97 * np.sin(angle), 6]], cell=box, pbc=True)
    oh = Atoms("OH", positions=[[6, 6, 6], [6, 6, 6.97]], cell=box, pbc=True)
    h = Atoms("H", positions=[[6, 6, 6]], cell=box, pbc=True)
    return {"slab": slab, "water": water, "OH": oh, "H": h, "initial": initial}


@pytest.fixture
def nacl(tmp_path):
    """A run with a locked PROJECT.md for NaCl(100) and the three inputs in it, without energies."""
    run = Run(tmp_path, "nacl")
    project.write(run.dir / "PROJECT.md", project.lock(nacl_settings(), "team"))
    set_run(run)
    s = structures()
    refs = {"slab": artifacts.write(s["slab"], "slab", Role.slab), "adsorbate_vacuum": artifacts.write(s["water"], "H2O-vacuum", Role.adsorbate_vacuum),
            "initial_state": artifacts.write(s["initial"], "initial-state", Role.initial_state)}
    yield SimpleNamespace(run=run, refs=refs, atoms=s)
    set_run(None)


@pytest.fixture
def files(tmp_path):
    """The stand-in written as the human supplies it: one extxyz file per structure."""
    from ase.io import write
    folder = tmp_path / "supplied"
    folder.mkdir()
    out = {}
    for key, atoms in structures().items():
        out[key] = str(folder / f"{key}.extxyz")
        write(out[key], atoms, format="extxyz")
    yield out
    set_run(None)


def relock(run, **over) -> None:
    project.write(run.dir / "PROJECT.md", project.lock(nacl_settings(**over), "team"))


def trace(run) -> str:
    return "\n".join(json.loads(line)["message"] for line in (run.dir / "trace.jsonl").read_text().splitlines())


def placed(nacl) -> Candidate:
    """B on a hollow of the slab with A at its initial-state site: a final state to read the binding atoms from."""
    out = structure_retrieval(nacl.refs["slab"], nacl.refs["adsorbate_vacuum"], nacl.refs["initial_state"], (0, 1))
    sites = site_enumeration(nacl.refs["slab"], out["cell_repeat"])
    base = Candidate(id="A000", structure=out["structures"][1], site_A=0)
    hollow = next(s.index for s in sites.sites if s.label == "hollow")
    return adsorbate_placement(sites, out["fragment_B"], hollow, 0, 2.0, 0.1, base)


# ---- 2: sites on a slab of two elements
def test_sites_on_nacl100_name_the_ions_and_agree_with_pymatgen(nacl):
    e = site_enumeration(nacl.refs["slab"], (1, 1))
    reps = {e.sites[o].label: e.sites[o] for o in {s.orbit for s in e.sites}}
    assert set(reps) == {"top Na", "top Cl", "bridge Na-Cl", "hollow"}
    assert e.count == e.burnside_count == 4 and e.baseline_count == e.count and e.total_sites == 64     # 16 tops, 32 bridges, 16 hollows
    assert {k: v.point_group for k, v in reps.items()} == {"top Na": "C4v", "top Cl": "C4v", "bridge Na-Cl": "Cs", "hollow": "C2v"}
    assert {k: v.coordination for k, v in reps.items()} == {"top Na": 1, "top Cl": 1, "bridge Na-Cl": 2, "hollow": 4}
    adj = geometry.site_graph(e)
    assert all(e.sites[j].label == "bridge Na-Cl" for j in adj[reps["hollow"].index])                  # a hollow touches bridges first
    assert "flag" not in trace(nacl.run)


# ---- 1 and 4: A named by the bond order, the binding atoms carried into every placed structure
def test_structure_retrieval_names_A_by_the_bond_order(nacl):
    n = len(nacl.atoms["slab"])
    initial = nacl.atoms["initial"]
    assert initial.positions[n + 1:, 2].max() < initial.positions[n, 2]           # both H sit below the O: the lowest atom binds nothing
    out = structure_retrieval(nacl.refs["slab"], nacl.refs["adsorbate_vacuum"], nacl.refs["initial_state"], (0, 1))
    a, b = artifacts.read(out["fragment_A"]), artifacts.read(out["fragment_B"])
    assert sorted(a.get_chemical_symbols()) == ["H", "O"] and b.get_chemical_symbols() == ["H"]
    assert a[artifacts.binding_atom(a)].symbol == "O" and b[artifacts.binding_atom(b)].symbol == "H"
    base = artifacts.read(out["structures"][1])
    assert base[artifacts.binding_index(base, "A")].symbol == "O"
    said = trace(nacl.run)
    assert "A = OH" in said and "B = H" in said and "maps onto the named one under a surface operation of the slab" in said

    c = placed(nacl)
    atoms = artifacts.read(c.structure)
    assert atoms.info["binding_A"] == base.info["binding_A"] and artifacts.binding_index(atoms, "B") == len(atoms) - 1

    relock(nacl.run, adsorbate="OH")                                                   # PROJECT.md naming another adsorbate stops the call
    with pytest.raises(SettingsMismatch):
        structure_retrieval(nacl.refs["slab"], nacl.refs["adsorbate_vacuum"], nacl.refs["initial_state"], (0, 1))
    relock(nacl.run, product=("H", "OH"))                                              # the bond names A's side first
    with pytest.raises(SettingsMismatch):
        structure_retrieval(nacl.refs["slab"], nacl.refs["adsorbate_vacuum"], nacl.refs["initial_state"], (0, 1))


# ---- the inputs: init_study writes the system from the files
def test_init_study_writes_the_system_from_the_inputs(tmp_path, files):
    c = init_study(tmp_path, "nacl", files["slab"], files["water"], files["initial"], (0, 1),
                   fragment_A_vacuum=files["OH"], fragment_B_vacuum=files["H"], facet="100")
    s = project.read(c.run.dir / "PROJECT.md")
    assert (s.adsorbate, tuple(s.product), s.metal, s.facet, s.locked) == ("H2O", ("OH", "H"), "NaCl", "100", False)
    inputs = c.data["inputs"]
    assert inputs["fragment_A_vacuum"]["role"] == "fragment_A_vacuum" and inputs["fragment_B_vacuum"]["role"] == "fragment_B_vacuum"
    assert all(inputs[k]["energy_eV"] is None for k in LABELS)
    assert "PROJECT.md from the inputs" in trace(c.run)

    with pytest.raises(FragPlaceError):                                               # the template's facet belongs to Pt
        init_study(tmp_path, "no-facet", files["slab"], files["water"], files["initial"], (0, 1))
    with pytest.raises(FragPlaceError):                                               # the fragment files swapped
        init_study(tmp_path, "swapped", files["slab"], files["water"], files["initial"], (0, 1), fragment_A_vacuum=files["H"],
                   fragment_B_vacuum=files["OH"], facet="100")


def test_init_study_reorders_an_initial_state_it_can_match_and_refuses_one_it_cannot(tmp_path, files):
    from ase import Atoms
    from ase.io import read, write
    slab, initial = read(files["slab"]), read(files["initial"])
    n = len(slab)
    shuffled = initial[[n, n + 2, n + 1] + list(range(n))[::-1]]                      # water first, its H atoms swapped, the slab reversed
    write(tmp_path / "shuffled.extxyz", shuffled, format="extxyz")
    c = init_study(tmp_path, "reordered", files["slab"], files["water"], str(tmp_path / "shuffled.extxyz"), (0, 1), facet="100")
    stored = artifacts.read(StructureRef.model_validate(c.data["inputs"]["initial_state"]))
    assert stored.get_chemical_symbols() == slab.get_chemical_symbols() + ["O", "H", "H"]
    assert np.allclose(stored.positions[:n], slab.positions) and np.allclose(stored.positions[n], initial.positions[n])
    assert "reordered" in trace(c.run)

    extra = initial + Atoms("H", positions=[[0.0, 0.0, initial.positions[:, 2].max() + 3.0]])
    write(tmp_path / "extra.extxyz", extra, format="extxyz")
    with pytest.raises(FragPlaceError):
        init_study(tmp_path, "extra", files["slab"], files["water"], str(tmp_path / "extra.extxyz"), (0, 1), facet="100")


# ---- 1*: the benchmark without energies, and a potential that has no Na or Cl
def test_mlip_selection_is_geometric_without_energies(nacl):
    pytest.importorskip("mace")
    relock(nacl.run, decisions={**nacl_settings().decisions, "mlip_selection.candidates": ["emt", "mace-mp-small"]})
    out = mlip_selection(["emt", "mace-mp-small"], "ionic", [nacl.refs[k] for k in LABELS])
    bench = out["benchmark"]
    assert out["chosen"] == "mace-mp-small" and out["committee"] == ["mace-mp-small"]
    assert not bench["emt"]["available"] and bench["emt"]["anomalies"] == ["unavailable: emt has no parameters for Cl, Na"]
    m = bench["mace-mp-small"]
    assert m["benchmark"] == "geometric" and m["error_eV"] is None and m["licence"] == "MIT"
    assert m["residual_fmax_eV_per_A"] > 0 and 0 <= m["max_adsorbate_displacement_A"] < 2.0
    assert "unseen chemistry: non-metal Cl in the slab" in m["anomalies"]
    assert "benchmark geometric" in trace(nacl.run)


def test_emt_on_nacl_is_unavailable_and_a_broken_adapter_is_not_cached(nacl):
    relock(nacl.run, decisions={**nacl_settings().decisions, "mlip_selection.candidates": ["emt"]})
    with pytest.raises(RuntimeError, match="unavailable: emt has no parameters for Cl, Na"):
        mlip_selection(["emt"], "ionic", [nacl.refs[k] for k in LABELS])
    with pytest.raises(calculators.UnsupportedElements):
        calculators.get("emt").energy_forces(nacl.atoms["slab"])
    tries = []

    def broken(name, **_):
        tries.append(name)
        raise RuntimeError("no weights")
    calculators._load()
    calculators.register("test-broken")(broken)
    try:
        for _ in range(2):
            with pytest.raises(RuntimeError):
                calculators.get("test-broken")
    finally:
        calculators._FACTORIES.pop("test-broken", None)
    assert tries == ["test-broken", "test-broken"]


# ---- 7 and 8: one rule for unseen chemistry, the open shell, and no 0.0 for a spread nobody measured
def test_one_rule_for_the_system_class_and_unseen_chemistry():
    assert system_class_of({"Na", "Cl"}, {"H", "O"}) == "ionic" and system_class_of({"Mg", "O"}, {"H", "O"}) == "oxide"
    assert system_class_of({"Pt"}, {"H", "O"}) == "metal"
    assert unseen_chemistry({"Pt"}, {"O", "H"}) is None
    assert unseen_chemistry({"Na", "Cl"}, {"O", "H"}) == "non-metal Cl in the slab"
    assert unseen_chemistry({"Pt"}, {"S", "H"}) == "adsorbate element S beyond H, C, N, O"


def test_uncertainty_flags_the_open_shell_on_nacl(nacl):
    pytest.importorskip("mace")
    c = placed(nacl)
    flags = uncertainty_estimation([c], ["mace-mp-small"], None)
    assert {(f.trigger, f.escalate) for f in flags} == {("unmeasured", True), ("unseen_chemistry", True), ("open_shell", True)}
    said = trace(nacl.run)
    assert "spread not measured" in said and "spread 0.0000" not in said


def test_ranking_says_not_measured_for_an_unmeasured_spread(nacl):
    card = DescriptorCard(candidate_id="A000-B001", composition="Na32Cl32H2O", cell="11.28 × 11.28 Å", facet="100", layers=4, vacuum_A=15.0,
                          fixed_layers=2, site_label="A top Na · B hollow", point_group="C4v · C2v", coordination=4, height_A=2.0,
                          nn_distances_A=[2.4], AB_distance_A=2.5, site_graph_distance=2, energy_eV=-1.0)
    flag = DoubtFlag(candidate_id="A000-B001", committee_spread_eV=0.0, trigger="unmeasured", escalate=True)
    ranked = ranking(["A000-B001"], [card], [flag], [])
    assert "spread not measured" in ranked[0].reason and "0.000 eV" not in ranked[0].reason


def test_mace_foundation_models_are_registered_with_their_licences():
    from fragplace.calculators.mace import FOUNDATION
    assert {"mace-mp-small", "mace-mpa-0", "mace-omat-0", "mace-omat-0-small", "mace-mp-0b3", "mace-matpes-pbe-0"} <= set(calculators.available())
    assert FOUNDATION["mace-mpa-0"] == ("medium-mpa-0", "MIT") and FOUNDATION["mace-omat-0"] == ("medium-omat-0", "ASL")
