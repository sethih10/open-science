"""One golden example per tool, on OH on Pt(111) with EMT: the outputs the registry promises, the checks it names
and the failures it must raise. The world of the module is built once: inputs, cell, sites, pairs, placements."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import make_inputs
from conftest import test_settings as settings_for
from fragplace.errors import FragPlaceError, OpenDecision, SettingsMismatch
from fragplace.runtime import artifacts, geometry, project
from fragplace.runtime.journal import Run, set_run
from fragplace.schemas.records import Candidate, Role, Settings

pytest.importorskip("ase")
pytest.importorskip("acat")
pytest.importorskip("spglib")

from fragplace.tools.clustering import ranking, soap_clustering  # noqa: E402
from fragplace.tools.dft import dft_single_points  # noqa: E402
from fragplace.tools.filtering import anomaly_filter, descriptor_card, gas_reference  # noqa: E402
from fragplace.tools.literature import CatalysisHub, literature_lookup  # noqa: E402
from fragplace.tools.placement import adsorbate_placement, minima_hopping  # noqa: E402
from fragplace.tools.relaxation import reference_energies, relaxation  # noqa: E402
from fragplace.tools.report import report  # noqa: E402
from fragplace.tools.screening import pull_force_screen  # noqa: E402
from fragplace.tools.sites import burnside, pair_enumeration, site_enumeration  # noqa: E402
from fragplace.tools.structure import calculation_protocol, structure_retrieval  # noqa: E402
from fragplace.tools.uncertainty import active_learning, mlip_selection, uncertainty_estimation  # noqa: E402


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    run = Run(tmp_path_factory.mktemp("world"), "test")
    settings = project.lock(settings_for(), approved_by="team")
    project.write(run.dir / "PROJECT.md", settings)
    set_run(run)
    try:
        inputs = make_inputs(run)
        refs = inputs["refs"]
        retrieval = structure_retrieval(refs["slab"], refs["adsorbate_vacuum"], refs["initial_state"], (0, 1))
        sites = site_enumeration(refs["slab"], retrieval["cell_repeat"])
        base_ref = retrieval["structures"][1]
        atoms = artifacts.read(base_ref)
        site, _ = geometry.nearest_site(sites, atoms.positions[geometry.lowest(atoms, artifacts.fragment_indices(atoms, "A"))], atoms.cell.array)
        base = Candidate(id=f"A{site.index:03d}", structure=base_ref, site_A=site.index)
        d = geometry.distance(inputs["atoms"]["adsorbate_vacuum"], 0, 1)
        pairs = pair_enumeration(sites, d, (1.5, 5.0), site.index)["pairs"]
        placed = [adsorbate_placement(sites, retrieval["fragment_B"], p.site_B, 0, 2.0, 0.1, base) for p in pairs]
        slab = relaxation([Candidate(id="slab", structure=sites.slab, generator="reference")], "emt", 0.03, 500)[0]
        first = {}
        for p, c in zip(pairs, placed):
            first.setdefault(sites.sites[p.site_B].label, c)
    finally:
        set_run(None)
    return SimpleNamespace(run=run, settings=settings, inputs=inputs, retrieval=retrieval, sites=sites, base=base, site_A=site, d=d,
                           pairs=pairs, placed=placed, slab=slab, first=first)


@pytest.fixture
def here(world):
    set_run(world.run)
    yield world
    set_run(None)


def relaxed(c: Candidate) -> Candidate:
    r = relaxation([c], "emt", 0.03, 500)[0]
    return c.model_copy(update={"structure": r.structure})


# ---- 1: structure_retrieval, calculation_protocol
def test_structure_retrieval_cleaves_the_bond_and_picks_the_cell(here):
    out = here.retrieval
    a, b = artifacts.read(out["fragment_A"]), artifacts.read(out["fragment_B"])
    assert a.get_chemical_formula() == "O" and b.get_chemical_formula() == "H"     # O keeps the binding atom
    assert set(a.get_tags()) == {artifacts.TAG_A} and set(b.get_tags()) == {artifacts.TAG_B}
    assert tuple(out["cell_repeat"]) == (2, 2)                                      # 3 x 2.77 Å < 10 Å <= 6 x 2.77 Å
    slab, base = (artifacts.read(r) for r in out["structures"])
    assert geometry.shortest_translation(slab.cell.array) >= 10.0
    assert len(base) == len(slab) + 1 and artifacts.fragment_indices(base, "A") == [len(slab)]


def test_structure_retrieval_refuses_mixed_settings_and_unbonded_atoms(run, pt111):
    refs = pt111["refs"]
    with pytest.raises(SettingsMismatch):
        structure_retrieval(refs["slab"], refs["adsorbate_vacuum"].model_copy(update={"settings_hash": "other"}), refs["initial_state"], (0, 1))
    with pytest.raises(ValueError):
        structure_retrieval(refs["slab"], refs["adsorbate_vacuum"], refs["initial_state"], (0, 0))


def test_calculation_protocol_fills_gaps_never_overrides_and_keeps_the_interview(run):
    path = run.dir / "PROJECT.md"
    project.write(path, settings_for())                                                 # unlocked, as before the lock
    path.write_text(path.read_text() + "\n## Interview\n\nkept\n")
    s = settings_for(cutoff_eV=None, pseudopotential_family=None, locked=False)
    out = calculation_protocol(s, {"spin": False}, "oc20", "OC20NEB is the ground truth")
    assert out.cutoff_eV == 350.0 and out.pseudopotential_family == "PAW" and not out.locked
    assert "## Interview\n\nkept" in path.read_text() and project.read(path).cutoff_eV == 350.0
    with pytest.raises(SettingsMismatch):
        calculation_protocol(s, {"functional": "PBE"}, "oc20", "reason")             # the inputs were relaxed with RPBE
    with pytest.raises(SettingsMismatch):
        calculation_protocol(settings_for(functional="PBE"), {}, "oc20", "reason")     # OC20NEB needs RPBE
    with pytest.raises(OpenDecision):
        calculation_protocol(settings_for(decisions={}), {}, "oc20", "reason")
    project.write(path, project.lock(out, "team"))
    with pytest.raises(FragPlaceError):
        calculation_protocol(s, {}, "oc20", "reason")                                   # a locked PROJECT.md is never rewritten


# ---- 2 and 3.2: site_enumeration, pair_enumeration
def test_site_enumeration_tells_fcc_from_hcp_and_agrees_with_burnside(here):
    e = here.sites
    assert e.count == e.burnside_count == 4 and e.baseline_count == 4 and e.total_sites == 216
    reps = {e.sites[o].label: e.sites[o] for o in {s.orbit for s in e.sites}}
    assert {k: v.point_group for k, v in reps.items()} == {"top": "C3v", "bridge": "Cs", "fcc": "C3v", "hcp": "C3v"}
    assert reps["hcp"].atom_beneath == "Pt" and reps["fcc"].atom_beneath is None
    assert {k: v.coordination for k, v in reps.items()} == {"top": 1, "bridge": 2, "fcc": 3, "hcp": 3}
    adj = geometry.site_graph(e)
    assert all(e.sites[j].label == "bridge" for j in adj[reps["fcc"].index])           # hollows touch bridges first


def test_site_enumeration_on_fcc100(run, ase):
    from ase.build import fcc100
    slab = artifacts.tag_slab_layers(fcc100("Pt", size=(3, 3, 4), vacuum=7.5))
    project.write(run.dir / "PROJECT.md", project.lock(settings_for(facet="100"), "team"))
    e = site_enumeration(artifacts.write(slab, "pt100", Role.slab), (1, 1))
    reps = {e.sites[o].label: e.sites[o].point_group for o in {s.orbit for s in e.sites}}
    assert e.count == e.burnside_count == 3 and reps == {"top": "C4v", "bridge": "C2v", "4fold": "C4v"}


def test_burnside_two_identical_adsorbates_on_a_square_give_2():
    # corners 0 (0,0), 1 (1,0), 2 (1,1), 3 (0,1) of a square under C4v
    c4v = [[0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1], [3, 0, 1, 2], [1, 0, 3, 2], [3, 2, 1, 0], [0, 3, 2, 1], [2, 1, 0, 3]]
    pairs = [frozenset((i, j)) for i in range(4) for j in range(i + 1, 4)]
    assert burnside(c4v, pairs) == 2


def test_pair_enumeration_is_nearest_first_inside_the_window(here):
    lower = 1.5 * here.d
    assert here.pairs and all(lower <= p.in_plane_distance_A <= 5.0 and p.site_A == here.site_A.index for p in here.pairs)
    keys = [(p.site_graph_distance, round(p.in_plane_distance_A, 3)) for p in here.pairs]
    assert keys == sorted(keys)
    first = here.pairs[0]
    assert here.sites.sites[first.site_B].label in ("top", "hcp") and first.in_plane_distance_A == pytest.approx(1.60, abs=0.05)
    assert len({p.candidate_id for p in here.pairs}) == len(here.pairs)
    with pytest.raises(ValueError):
        pair_enumeration(here.sites, here.d, (1.5, 4.5), here.site_A.index)          # the locked upper bound is 5
    assert pair_enumeration(here.sites, here.d, (1.5, 5.0))["count"] > len(here.pairs)  # every A orbit


# ---- 4: adsorbate_placement, relaxation
def test_adsorbate_placement_is_scripted_and_reproducible(here):
    p = here.pairs[0]
    again = adsorbate_placement(here.sites, here.retrieval["fragment_B"], p.site_B, 0, 2.0, 0.1, here.base)
    assert again.id == p.candidate_id == here.placed[0].id and again.site_A == here.site_A.index and again.site_B == p.site_B
    assert np.allclose(artifacts.read(again.structure).positions, artifacts.read(here.placed[0].structure).positions)
    atoms = artifacts.read(again.structure)
    h = artifacts.fragment_indices(atoms, "B")[0]
    assert 1.85 <= geometry.height(atoms, h) <= 2.15                                    # 2 Å up, displaced by at most 0.1 per axis
    for bad in ({"height_A": 4.0}, {"displacement_amplitude_A": 0.2}, {"orientation": 1}):
        kw = dict(sites=here.sites, fragment=here.retrieval["fragment_B"], site_index=p.site_B, orientation=0, height_A=2.0,
                  displacement_amplitude_A=0.1, base=here.base) | bad
        with pytest.raises(ValueError):
            adsorbate_placement(**kw)


def test_relaxation_converges_caches_and_stamps_the_settings(here):
    c = here.first["hcp"]
    r1 = relaxation([c], "emt", 0.03, 500)[0]
    r2 = relaxation([c], "emt", 0.03, 500)[0]
    assert r1.converged and r1.fmax_eV_per_A <= 0.03 and not r1.cache_hit and r2.cache_hit and r2.energy_eV == r1.energy_eV
    assert r1.structure.settings_hash == project.settings_hash(here.settings) and r1.structure.calculator == "emt"
    with pytest.raises(SettingsMismatch):
        relaxation([c], "mace-mp-small", 0.03, 500)                                     # PROJECT.md locks emt


# ---- 3.3: pull_force_screen
def test_pull_force_screen_queues_flagged_pairs_last(here, monkeypatch):
    screens = pull_force_screen(here.placed, "emt")
    assert [s.queue_position for s in screens] == list(range(len(here.placed)))
    assert all(s.flagged == (s.force_on_B_along_AB_eV_per_A > 0.5) for s in screens)
    forces = sorted(s.force_on_B_along_AB_eV_per_A for s in screens)
    cut = forces[len(forces) // 2]
    from fragplace.tools import screening
    real = screening.project.decision
    monkeypatch.setattr(screening.project, "decision", lambda tool, name, s=None: cut if name == "threshold_eV_per_A" else real(tool, name, s))
    queue = pull_force_screen(here.placed, "emt")
    flags = [s.flagged for s in queue]
    assert any(flags) and flags == sorted(flags)                                        # unflagged first, never dropped
    assert len(queue) == len(here.placed)
    order = [c.id for c in here.placed]
    assert [s.candidate_id for s in queue if s.flagged] == [k for k in order if k in {s.candidate_id for s in queue if s.flagged}]


# ---- 5: anomaly_filter, descriptor_card
def test_anomaly_filter_passes_a_hollow_pair_with_all_eleven_checks(here):
    c = here.first["hcp"]
    gate = anomaly_filter(relaxed(c), c, here.slab.structure, here.settings, None, None)
    assert gate.stage == "after_relaxation" and {v.check_id for v in gate.verdicts} == set(range(1, 12))
    assert gate.passed, [v for v in gate.verdicts if not v.passed]
    five = next(v for v in gate.verdicts if v.check_id == 5)
    assert five.reason.startswith("no imaginary mode")                                  # frequencies from the potential, as decided


def test_anomaly_filter_rejects_recombination_and_desorption(here):
    base = artifacts.read(here.base.structure)
    o = artifacts.fragment_indices(base, "A")[0]
    for name, offset, check in (("recombined", [0.0, 0.0, 1.0], 10), ("desorbed", [8.0, 0.0, 5.0], 1)):
        atoms = base.copy()
        from ase import Atoms
        h = Atoms("H", positions=[base.positions[o] + offset], tags=[artifacts.TAG_B])
        atoms += h
        atoms.set_constraint(base.constraints)
        ref = artifacts.write(atoms, name, Role.candidate, settings_hash=project.settings_hash(here.settings), calculator="emt")
        c = Candidate(id=name, structure=ref)
        gate = anomaly_filter(c, c, here.slab.structure, here.settings, None, None)
        failed = {v.check_id for v in gate.verdicts if not v.passed}
        assert not gate.passed and check in failed, (name, failed)


def test_anomaly_filter_check_seven_needs_a_prior_and_references(here):
    s = here.settings
    assert gas_reference(s, ["O", "H"]) == pytest.approx(-14.22 - 0.5 * -6.77)          # OH = H2O − ½ H2
    assert gas_reference(s, ["Pt"]) is None


def test_descriptor_card_reads_both_fragments_and_writes_files(here):
    c = here.placed[0]
    card = descriptor_card(c, None, here.sites)
    assert card.candidate_id == c.id and card.site_label.startswith("A fcc · B ") and card.layers == 4 and card.fixed_layers == 2
    assert card.AB_distance_A > 1.5 and card.site_graph_distance == here.pairs[0].site_graph_distance
    assert len(card.fragment_lines) == 2 and "check" not in card.text()
    stem = c.structure.path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    assert (here.run.dir / "cards" / f"{stem}.txt").exists() and (here.run.dir / "cards" / f"{stem}.json").exists()


# ---- 6, 7, 8 and the solution
def test_soap_clustering_joins_copies_and_keeps_nearest_first(here):
    hcp, fcc = relaxed(here.first["hcp"]), relaxed(here.first["fcc"])
    copy = hcp.model_copy(update={"id": "copy"})
    energies = relaxation([here.first["hcp"], here.first["fcc"]], "emt", 0.03, 500)
    energies.append(energies[0].model_copy(update={"candidate_id": "copy"}))
    out = soap_clustering([fcc, hcp, copy], energies, here.pairs)
    groups = sorted(sorted(c.members) for c in out["clusters"])
    assert sorted([hcp.id, "copy"]) in groups and [fcc.id] in groups
    near = {p.candidate_id: (p.site_graph_distance, p.in_plane_distance_A) for p in here.pairs}
    kept = [k for k in out["kept"] if k in near]
    assert kept == sorted(kept, key=near.get)


def test_uncertainty_estimation_flags_every_candidate_and_always_magnetic_metals(here, ase):
    c = relaxed(here.first["hcp"])
    flags = uncertainty_estimation([c], ["emt"], None)
    assert [(f.trigger, f.escalate) for f in flags] == [("unmeasured", True)]          # one model measures no disagreement
    from ase.build import fcc111
    ni = artifacts.tag_slab_layers(fcc111("Ni", size=(2, 2, 3), vacuum=6.0))
    from ase import Atoms
    ads = Atoms("OH", positions=[[0, 0, ni.positions[:, 2].max() + 1.5], [3, 0, ni.positions[:, 2].max() + 1.5]], tags=[2, 3])
    ni += ads
    nc = Candidate(id="ni", structure=artifacts.write(ni, "ni", Role.candidate))
    triggers = {(f.trigger, f.escalate) for f in uncertainty_estimation([nc], ["emt"], None)}
    assert ("magnetic_metal", True) in triggers


def test_mlip_selection_benchmarks_on_the_supplied_inputs(here):
    refs = here.inputs["refs"]
    labels = [refs["slab"], refs["adsorbate_vacuum"], refs["initial_state"]]
    out = mlip_selection(["emt"], "metal", labels)        # the fixture relaxed to 0.05 eV/Å, the benchmark to the locked 0.03
    assert out["chosen"] == "emt" and out["committee"] == ["emt"] and abs(out["benchmark"]["emt"]["error_eV"]) < 0.02
    with pytest.raises(ValueError):
        mlip_selection(["emt", "chgnet"], "metal", labels)                               # not the locked candidates


def test_ranking_orders_nearest_first_and_drops_nothing(here):
    hcp, fcc = relaxed(here.first["hcp"]), relaxed(here.first["fcc"])
    cards = [descriptor_card(c, None, here.sites) for c in (fcc, hcp)]
    flags = uncertainty_estimation([fcc, hcp], ["emt"], None)
    ranked = ranking([fcc.id, hcp.id], cards, flags, here.pairs)
    assert [r.rank for r in ranked] == [1, 2] and {r.candidate_id for r in ranked} == {fcc.id, hcp.id}
    assert ranked[0].site_graph_distance <= ranked[1].site_graph_distance and ranked[0].doubt.trigger == "unmeasured"


def test_reference_energies_put_each_fragment_alone_on_the_slab(here):
    c = relaxed(here.first["hcp"])
    e = reference_energies(here.slab.structure, (c.structure, c.structure), "emt")
    assert e["E_inf_eV"] == pytest.approx(e["E_A_eV"] + e["E_B_eV"] - e["E_slab_eV"])
    assert abs(c.structure.energy_eV - e["E_inf_eV"]) < 1.0                             # a lateral interaction, not a new bond


def test_report_writes_markdown_and_json_with_rates_from_the_trace(here):
    c = here.first["hcp"]
    gate = anomaly_filter(relaxed(c), c, here.slab.structure, here.settings, None, None)
    rep = report("test", [], [] if gate.passed else [gate], [], {})
    assert (here.run.dir / "report.md").exists() and json.loads((here.run.dir / "report.json").read_text())["campaign"] == "test"
    shell = next(p.site_graph_distance for p in here.pairs if p.candidate_id == c.id)
    assert rep.recombination_rate_by_shell[shell] == 0.0 and rep.cost["gates"] >= 1
    with pytest.raises(ValueError):
        report("another campaign", [], [], [], {})


# ---- prompt and 3.6: literature_lookup, minima_hopping; the extensions
def test_literature_lookup_keeps_two_values_each_with_a_source(run, monkeypatch):
    def node(energy, products, pub):        # synthetic records: they test the parsing, they are not data
        return {"node": {"Equation": "", "reactionEnergy": energy, "surfaceComposition": "Pt", "facet": "111", "sites": '{"OH": "fcc"}',
                         "dftFunctional": "TEST", "products": products, "pubId": pub}}
    reply = {"data": {"reactions": {"edges": [node(0.1, '{"OHstar": 1}', "Test1"), node(0.2, '{"Ostar": 1, "Hstar": 1}', "Test2"),
                                              node(0.3, '{"OHstar": 1}', "Test3"), node(0.4, '{"OHstar": 1}', "Test4")]}}}
    monkeypatch.setattr(CatalysisHub, "post", lambda self, query: reply)
    values = literature_lookup("Pt(111) OH", "E_ads", ["catalysis_hub"])
    assert [v.value for v in values] == [0.1, 0.3] and all(v.source.startswith("https://") and not v.verified_by_human for v in values)
    with pytest.raises(LookupError):
        literature_lookup("Pt(111) OH", "bond_length_d", ["catalysis_hub"])
    with pytest.raises(ValueError):
        literature_lookup("Pt(111) OH", "E_ads", ["a source nobody wrote"])


def test_minima_hopping_returns_minima_as_candidates(here):
    found = minima_hopping(here.sites.slab, (here.retrieval["fragment_A"], here.placed[0].structure), "emt", 1)
    assert found and all(c.generator == "minima_hopping" and c.structure.energy_eV is not None for c in found)
    atoms = artifacts.read(found[0].structure)
    assert artifacts.fragment_indices(atoms, "A") and artifacts.fragment_indices(atoms, "B")


def test_extensions_are_stubs_until_d2():
    with pytest.raises(NotImplementedError):
        dft_single_points([], Settings(metal="Pt", facet="111", adsorbate="OH", product=("O", "H"), functional="RPBE"), "local")
    with pytest.raises(NotImplementedError):
        active_learning([], [], "mace")
