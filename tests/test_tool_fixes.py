"""The fixes the trial run's reviews asked for, on OH on Pt(111) with EMT: the k-mesh and the origins the lock
writes, the gate before relaxation and the words of its trace, check 2's height, check 7 like with like, check 8's
reason, the gas reference, the reference relaxations in the trace and the cost, the report's added sections, and
the literature sources. Nothing here reaches the network."""
import inspect
import io
import json
import re
import urllib.error
import urllib.request
from types import SimpleNamespace

import pytest

from conftest import make_inputs
from conftest import test_settings as settings_for
from fragplace.errors import OpenDecision, SettingsMismatch
from fragplace.registry.tools import BY_NAME, open_decisions
from fragplace.runtime import artifacts, checkpoints, geometry, project
from fragplace.runtime.journal import Run, set_run
from fragplace.schemas.records import Candidate, DoubtFlag, FinalState, GasReference, HumanChoice, LiteratureValue, Role

pytest.importorskip("ase")
pytest.importorskip("acat")
pytest.importorskip("spglib")

from fragplace.tools import get as tool  # noqa: E402
from fragplace.tools import literature  # noqa: E402
from fragplace.tools.clustering import soap_clustering  # noqa: E402
from fragplace.tools.filtering import anomaly_filter, descriptor_card, gas_reference  # noqa: E402
from fragplace.tools.placement import adsorbate_placement  # noqa: E402
from fragplace.tools.relaxation import reference_energies, relaxation  # noqa: E402
from fragplace.tools.report import report  # noqa: E402
from fragplace.tools.sites import pair_enumeration, site_enumeration  # noqa: E402
from fragplace.tools.structure import DFT_SETTINGS, REPORTED, RUN_SETTINGS, calculation_protocol, structure_retrieval  # noqa: E402

NOT_RUN = "not checked: not run before relaxation"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """A test that reaches urlopen without replacing it fails."""
    def refuse(*args, **kwargs):
        raise AssertionError("a test tried the network")
    monkeypatch.setattr(urllib.request, "urlopen", refuse)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """The inputs, the 2x2 cell, the sites, B placed on the first pair of each site kind, and the relaxed slab."""
    run = Run(tmp_path_factory.mktemp("fixes"), "fixes")
    settings = project.lock(settings_for(), approved_by="team")
    project.write(run.dir / "PROJECT.md", settings)
    set_run(run)
    try:
        refs = make_inputs(run)["refs"]
        retrieval = structure_retrieval(refs["slab"], refs["adsorbate_vacuum"], refs["initial_state"], (0, 1))
        sites = site_enumeration(refs["slab"], retrieval["cell_repeat"])
        base_ref = retrieval["structures"][1]
        atoms = artifacts.read(base_ref)
        site, _ = geometry.nearest_site(sites, atoms.positions[artifacts.fragment_indices(atoms, "A")[0]], atoms.cell.array)
        base = Candidate(id=f"A{site.index:03d}", structure=base_ref, site_A=site.index)
        d = geometry.distance(artifacts.read(refs["adsorbate_vacuum"]), 0, 1)
        pairs = pair_enumeration(sites, d, (1.5, 5.0), site.index)["pairs"]
        first = {}
        for p in pairs:
            first.setdefault(sites.sites[p.site_B].label, p)
        placed = {label: adsorbate_placement(sites, retrieval["fragment_B"], p.site_B, 0, 2.0, 0.1, base) for label, p in first.items()}
        slab = relaxation([Candidate(id="slab", structure=sites.slab, generator="reference")], "emt", 0.03, 500)[0]
    finally:
        set_run(None)
    return SimpleNamespace(run=run, settings=settings, sites=sites, base=base, pairs=pairs, placed=placed, slab=slab)


@pytest.fixture
def here(world):
    set_run(world.run)
    yield world
    set_run(None)


def relaxed(c: Candidate, steps: int = 500) -> Candidate:
    r = relaxation([c], "emt", 0.03, steps)[0]
    return c.model_copy(update={"structure": r.structure})


def deciding(settings, checks):
    """The locked settings with another list of checks before relaxation."""
    return settings.model_copy(update={"decisions": {**settings.decisions, "anomaly_filter.checks_before_relaxation": checks}})


def with_h(here, offset, name: str) -> Candidate:
    """A at its initial-state site and H at an offset from it, written as a candidate of the locked potential."""
    from ase import Atoms
    base = artifacts.read(here.base.structure)
    o = artifacts.fragment_indices(base, "A")[0]
    atoms = base + Atoms("H", positions=[base.positions[o] + offset], tags=[artifacts.TAG_B])
    atoms.set_constraint(base.constraints)
    ref = artifacts.write(atoms, name, Role.candidate, settings_hash=project.settings_hash(here.settings), calculator="emt")
    return Candidate(id=name, structure=ref)


def section(md: str, title: str) -> list:
    return md.split(f"## {title}\n", 1)[1].split("\n## ", 1)[0].splitlines()


def docstring_head(spec) -> str:
    """The head of a tool's docstring as the registry writes it."""
    lines = [spec.purpose, "", f"Board steps: {', '.join(spec.board_steps)}. Status: {spec.status}. Lane: {spec.lane}. "
             f"Allowed roles: {', '.join(spec.allowed_roles)}.", "", "Inputs:"]
    lines += [f"    {k}: {v}" for k, v in spec.inputs.items()] + ["Outputs:"] + [f"    {k}: {v}" for k, v in spec.outputs.items()]
    lines += ["Checks:"] + [f"    - {c}" for c in spec.checks] + ["Thresholds:"]
    lines += [f"    {k}: {v}" for k, v in spec.thresholds.items()] or ["    none"]
    return "\n".join(lines + ["Wraps:"] + [f"    - {w}" for w in spec.wraps] + [f"Logs: {'; '.join(spec.logs)}."])


@pytest.mark.parametrize("name", ["literature_lookup", "calculation_protocol", "relaxation", "reference_energies", "anomaly_filter",
                                  "descriptor_card", "report"])
def test_docstrings_mirror_the_registry(name):
    assert inspect.getdoc(tool(name)).startswith(docstring_head(BY_NAME[name]))


# ---- 1: the k-mesh and the origins of the lock
def proposal(run, **over):
    """The settings as read before the lock, with an unlocked PROJECT.md for calculation_protocol to write."""
    project.write(run.dir / "PROJECT.md", settings_for())
    return settings_for(locked=False, **over)


def test_the_kmesh_follows_the_oc20_rule_on_the_selected_cell(run):
    out = calculation_protocol(proposal(run, kmesh=None, cell_A=(16.63, 8.0)), {}, "oc20", "OC20NEB is the ground truth")
    assert out.kmesh == (3, 5, 1)                                  # 40 / 16.63 = 2.4 rounds up; 40 / 8 = 5 exactly stays 5
    assert out.origins["kmesh"] == "protocol oc20: 40 / in-plane length, Γ-centred, one along the vacuum"
    assert project.read(run.dir / "PROJECT.md").kmesh == (3, 5, 1)
    assert any("kmesh protocol oc20: 40 / in-plane length" in e.message for e in run.events())


def test_a_kmesh_the_human_gives_wins_and_one_the_inputs_hold_stays(run):
    out = calculation_protocol(proposal(run, kmesh=None, cell_A=(16.63, 16.63)), {"kmesh": [5, 5, 1]}, "oc20", "reason")
    assert out.kmesh == (5, 5, 1) and out.origins["kmesh"] == "physics choice"
    held = proposal(run, kmesh=(4, 4, 1), cell_A=(16.63, 16.63))
    out = calculation_protocol(held, {}, "oc20", "reason")
    assert out.kmesh == (4, 4, 1) and out.origins["kmesh"] == "PROJECT.md before the lock; protocol oc20 says (3, 3, 1)"
    with pytest.raises(SettingsMismatch):
        calculation_protocol(held, {"kmesh": [5, 5, 1]}, "oc20", "reason")       # new physics needs new inputs
    for bad in ([3, 3], [0, 3, 1], [3.0, 3, 1], [True, 3, 1], "3x3x1"):
        with pytest.raises(ValueError, match="three positive integers"):
            calculation_protocol(proposal(run, kmesh=None), {"kmesh": bad}, "oc20", "reason")


def test_the_no_dft_lock_sets_no_dft_field_and_a_dft_protocol_still_fills_the_kmesh(run):
    out = calculation_protocol(proposal(run, kmesh=None, cell_A=(16.63, 8.0)), {}, "oc20", "OC20NEB is the ground truth")
    assert out.kmesh == (3, 5, 1) and out.functional == "RPBE" and out.cutoff_eV == 350.0 and list(out.origins) == list(REPORTED)
    before = len(run.events())
    out = calculation_protocol(proposal(run, kmesh=None, cell_A=(16.63, 8.0)), {"spin": True}, "mlip", "no DFT runs; EMT computes every energy")
    assert all(getattr(out, f) in (None, {}) for f in DFT_SETTINGS) and out.spin_polarised
    assert list(out.origins) == list(RUN_SETTINGS) + ["spin_polarised"] and out.origins["cell_A"] == "PROJECT.md before the lock"
    assert project.read(run.dir / "PROJECT.md").cutoff_eV is None
    said = [e.message for e in run.events()[before:] if e.tool == "calculation_protocol" and e.message]
    assert any(m.startswith("no DFT runs: the potential chosen at 1* computes every energy") and "cleared functional" in m for m in said)
    assert not any("needed only by DFT single points" in m or (m.startswith("origins:") and "kmesh" in m) for m in said)
    for choice in ({"functional": "RPBE"}, {"kmesh": [3, 3, 1]}, {"U": {"Pt": 2.0}}):
        with pytest.raises(ValueError, match="runs no DFT"):
            calculation_protocol(proposal(run), choice, "mlip", "no DFT")
    with pytest.raises(SettingsMismatch, match="needs DFT"):
        calculation_protocol(proposal(run, decisions={**settings_for().decisions, "anomaly_filter.frequencies_source": "dft"}), {}, "mlip", "no DFT")


def test_convergence_target_is_asked_only_when_the_study_runs_dft(run):
    open_ = dict(settings_for().decisions, **{"calculation_protocol.convergence_target_meV": None, "anomaly_filter.frequencies_source": None})
    s = proposal(run, decisions=open_)
    out = calculation_protocol(s, {}, "mlip", "no DFT runs")
    assert out.convergence_target_meV is None and out.decisions["anomaly_filter.frequencies_source"] == "mlip"
    assert project.missing_decisions(proposal(run, decisions=open_, protocol=None)) == []          # no protocol yet means no DFT
    assert project.missing_decisions(s, dft=True) == ["calculation_protocol.convergence_target_meV", "anomaly_filter.frequencies_source"]
    with pytest.raises(OpenDecision, match="convergence_target_meV"):
        calculation_protocol(proposal(run, decisions=open_), {}, "oc20", "OC20NEB is the ground truth")


def test_without_the_cell_the_kmesh_stays_unset_and_every_setting_has_an_origin(run):
    s = proposal(run, kmesh=None, cell_A=None, cutoff_eV=None, dispersion=None)
    out = calculation_protocol(s, {"spin": False}, "oc20", "reason")
    said = [e.message for e in run.events() if e.tool == "calculation_protocol" and e.message]
    assert out.kmesh is None and any(m.startswith("kmesh unset: cell_A, the in-plane lengths of the selected cell, is not known") for m in said)
    assert list(out.origins) == list(REPORTED)
    assert out.origins["cutoff_eV"] == "protocol oc20" and out.origins["spin_polarised"] == "physics choice"
    assert out.origins["functional"] == "PROJECT.md before the lock" and out.origins["dispersion"] == "unset" and out.origins["kmesh"] == "unset"
    assert out.origins["convergence_target_meV"] == "decision calculation_protocol.convergence_target_meV"
    assert project.read(run.dir / "PROJECT.md").origins == out.origins
    assert not any(m.startswith("origins: ;") for m in said)


# ---- 5: the gate before relaxation, the words of its trace, checks 2, 7 and 8, the gas reference
def test_before_relaxation_only_the_listed_checks_decide(here):
    c = here.placed["hcp"]                                          # placed, never relaxed: candidate and start are one structure
    gate = anomaly_filter(c, c, here.sites.slab, here.settings, None, None)
    assert gate.stage == "before_relaxation" and gate.passed
    for v in gate.verdicts:
        if v.check_id in (1, 9, 10, 11):
            assert v.measured is not None and "not checked" not in v.reason
        else:
            assert v.passed and v.measured is None and v.reason == NOT_RUN
    assert {v.check_id for v in gate.verdicts} == set(range(1, 12))
    far = with_h(here, [8.0, 0.0, 5.0], "desorbed-before")         # B leaves the surface: check 1 fails
    assert not anomaly_filter(far, far, here.sites.slab, here.settings, None, None).passed
    assert anomaly_filter(far, far, here.sites.slab, deciding(here.settings, [10]), None, None).passed     # 1 not listed, not run
    for bad in ("1, 10", [0, 10], [10.0], None):
        with pytest.raises(OpenDecision):
            anomaly_filter(c, c, here.sites.slab, deciding(here.settings, bad), None, None)


def test_check_eight_says_not_checked_without_a_potential_and_fails_on_another_lock(here):
    c = here.placed["hcp"]
    gate = anomaly_filter(c, c, here.sites.slab, deciding(here.settings, [8, 10]), None, None)
    eight = next(v for v in gate.verdicts if v.check_id == 8)
    assert eight.passed and eight.reason.startswith("not checked: ") and "the candidate records no potential" in eight.reason
    done = relaxed(c)
    eight = next(v for v in anomaly_filter(done, c, here.slab.structure, here.settings, None, None).verdicts if v.check_id == 8)
    assert eight.passed and "the inputs' own consistency is checked by structure_retrieval" in eight.reason
    other = here.settings.model_copy(update={"cutoff_eV": 400.0})
    assert not next(v for v in anomaly_filter(done, c, here.slab.structure, other, None, None).verdicts if v.check_id == 8).passed


def test_the_trace_says_not_checked_where_the_verdict_does(here):
    c = here.placed["fcc"]
    done = relaxed(c)
    start = len(here.run.events())
    gate = anomaly_filter(done, c, here.slab.structure, here.settings, None, None)
    lines = [e.message for e in here.run.events()[start:] if e.tool == "anomaly_filter" and e.message.startswith(f"{c.id} check ")]
    assert gate.stage == "after_relaxation" and len(lines) == len(gate.verdicts)
    for v, line in zip(gate.verdicts, lines):
        assert ("not checked" in line) == ("not checked" in v.reason) and "measured None" not in line, line
    assert {v.check_id for v in gate.verdicts if "not checked" in v.reason} == {3, 6, 7}     # no bond, no magnetism, a pair
    two = [v for v in gate.verdicts if v.check_id == 2]
    assert len(two) == 2 and all(re.search(r"moved \d\.\d\d Å in the plane and [+-]\d\.\d\d Å in height", v.reason) for v in two)
    card = descriptor_card(done, gate, here.sites)
    assert card.displacement_from_start.startswith("binding atom moved in the plane from the start (check 2): A ")


def test_check_seven_compares_like_with_like(here):
    pair = relaxed(here.placed["hcp"])
    seven = next(v for v in anomaly_filter(pair, here.placed["hcp"], here.slab.structure, here.settings, -1.0, None).verdicts if v.check_id == 7)
    assert seven.passed and seven.measured is None and seven.reason.startswith("not checked: a final state holds two fragments")
    alone = relaxed(here.base)                                     # A alone: one adsorbate, its own E_ads against the prior
    seven = next(v for v in anomaly_filter(alone, here.base, here.slab.structure, here.settings, -1.0, None).verdicts if v.check_id == 7)
    assert seven.measured is not None and seven.reason.startswith("E_ads ")


def test_gas_reference_takes_the_species_itself_and_refuses_a_blend():
    refs = [GasReference(species="H2O", energy_eV=-14.22), GasReference(species="OH", energy_eV=-8.07), GasReference(species="H", energy_eV=-1.1)]
    dependent = settings_for(gas_references=refs)
    assert gas_reference(dependent, ["O", "H"]) == pytest.approx(-8.07)           # OH itself, not a blend of the three
    assert gas_reference(dependent, ["O"]) is None                                 # H2O − 2 H or OH − H: more than one way
    assert gas_reference(settings_for(), ["O", "H"]) == pytest.approx(-14.22 - 0.5 * -6.77)   # the one way from H2 and H2O


def test_relaxation_keeps_the_binding_atoms_in_info(here):
    atoms = artifacts.read(here.placed["top"].structure)
    o, h = artifacts.fragment_indices(atoms, "A")[0], artifacts.fragment_indices(atoms, "B")[0]
    atoms.info.update(binding_A=o, binding_B=h)
    ref = artifacts.write(atoms, "with-binding", Role.candidate, settings_hash=project.settings_hash(here.settings))
    out = artifacts.read(relaxation([Candidate(id="with-binding", structure=ref)], "emt", 0.03, 500)[0].structure)
    assert (out.info["binding_A"], out.info["binding_B"]) == (o, h)


# ---- solution: the reference relaxations in the trace, E_ads per fragment
def test_reference_energies_relax_in_the_trace_and_give_e_ads_per_fragment(here):
    from ase import Atoms
    fs = relaxed(here.placed["hcp"]).structure
    start = len(here.run.events())
    e = reference_energies(here.slab.structure, (fs, fs), "emt", None)
    assert set(e) == set(BY_NAME["reference_energies"].outputs)
    events = here.run.events()[start:]
    results = [r for ev in events if ev.tool == "relaxation" and ev.outputs_ref for r in json.loads((here.run.dir / ev.outputs_ref).read_text())]
    assert len(results) == 5 and all(r["structure"]["role"] == "reference" and r["steps"] >= 0 for r in results)
    assert len([ev for ev in events if ev.tool == "relaxation" and " steps, fmax " in ev.message]) == 5
    gas_a = next(r["energy_eV"] for r in results if r["candidate_id"].startswith("gas-A-"))
    assert e["E_ads_A_eV"] == pytest.approx(e["E_A_eV"] - e["E_slab_eV"] - gas_a)
    assert e["E_inf_eV"] == pytest.approx(e["E_A_eV"] + e["E_B_eV"] - e["E_slab_eV"])
    gas = tuple(artifacts.write(Atoms(x, positions=[[6, 6, 6]], cell=[12, 12, 12], pbc=True), f"{x}-vacuum", Role.adsorbate_vacuum) for x in "OH")
    supplied = reference_energies(here.slab.structure, (fs, fs), "emt", gas)
    assert supplied["E_ads_A_eV"] == pytest.approx(e["E_ads_A_eV"], abs=1e-6)       # an EMT atom alone is alone in either cell
    assert supplied["E_ads_B_eV"] == pytest.approx(e["E_ads_B_eV"], abs=1e-6)


# ---- solution: the report, last, on everything the module traced
def test_report_shows_every_survivor_the_cell_the_open_decisions_and_no_rounded_zero(here):
    hcp, fcc = (relaxed(here.placed[k]) for k in ("hcp", "fcc"))
    gates = {c.id: anomaly_filter(c, here.placed[k], here.slab.structure, here.settings, None, [100.0])       # check 5 is not the point here
             for c, k in ((hcp, "hcp"), (fcc, "fcc"))}
    assert all(g.passed for g in gates.values()), {k: [v.reason for v in g.verdicts if not v.passed] for k, g in gates.items()}
    near = with_h(here, [1.5, 0.0, 0.2], "near")                   # passes check 10 at 1.51 Å, within 0.5 Å of the 1.3 Å threshold
    start = artifacts.write(artifacts.read(near.structure), "near-start", Role.candidate, settings_hash=near.structure.settings_hash, calculator="emt")
    assert anomaly_filter(near, Candidate(id="near", structure=start), here.slab.structure, here.settings, None, [100.0]).passed
    capped = Candidate(id="capped", structure=here.placed["bridge"].structure)
    stopped = relaxed(capped, steps=1)
    assert anomaly_filter(stopped, capped, here.slab.structure, here.settings, None, [100.0]).passed
    energies = relaxation([here.placed["hcp"], here.placed["fcc"]], "emt", 0.03, 500)
    assert set(soap_clustering([hcp, fcc], energies, here.pairs)["kept"]) == {hcp.id, fcc.id}
    checkpoints.record(here.run.dir, HumanChoice(checkpoint="review flagged cases", chosen=[], reason="keep all", who="tester"))
    checkpoints.record(here.run.dir, HumanChoice(checkpoint="pick up to five final states", chosen=[hcp.id], reason="nearest", who="tester"))
    shell = next(p.site_graph_distance for p in here.pairs if p.candidate_id == hcp.id)
    e_near = energies[0].energy_eV
    final = FinalState(candidate_id=hcp.id, E_near_eV=e_near, E_inf_eV=e_near - 2.06e-05, lateral_interaction_eV=2.06e-05,
                       AB_distance_A=next(v.measured for v in gates[hcp.id].verdicts if v.check_id == 10), site_graph_distance=shell, E_ads_A_eV=-3.2)
    flags = [DoubtFlag(candidate_id=hcp.id, committee_spread_eV=0.0, trigger="unmeasured", escalate=True),
             DoubtFlag(candidate_id=fcc.id, committee_spread_eV=0.0123, trigger="disagreement", escalate=False)]

    rep = report("fixes", [final], [], flags, {})
    md = (here.run.dir / "report.md").read_text()
    assert "Example study" not in md and rep.cost["reference_relaxations"] >= 5 and rep.cost["gates_before_relaxation"] >= 1
    row = next(line for line in section(md, "Final states") if line.startswith(f"| {hcp.id} |"))
    assert "| +2.06e-05 |" in row and "| -3.2000 |" in row and "| not computed |" in row      # never +0.0000
    survivors = {line.split(" | ")[0][2:]: line for line in section(md, "Every survivor of the gate") if line.startswith("| ") and "---" not in line}
    assert survivors[hcp.id].endswith("| flagged: unmeasured, escalated | picked |") and survivors[fcc.id].endswith("| kept, not picked |")
    assert survivors["near"].endswith("| not kept by clustering |") and "| 1.51 |" in survivors["near"]
    assert "| no, stopped at the step cap | 1 |" in survivors["capped"]
    assert "| Repeat of the supplied cell | 2 × 2 |" in md and "| Surface atoms in the cell | 36 |" in md
    assert "| Coverage of A, O\\*, ML | 1/36 = 0.0278 |" in md and "| Coverage of B, H\\*, ML | 1/36 = 0.0278 |" in md
    recombination = "\n".join(section(md, "Recombination rate"))
    assert "Check 10 fails below an A–B distance of 1.3 Å" in recombination and "| near | 1.51 | 0.21 | not kept by clustering |" in recombination
    doubt = section(md, "Doubt")
    assert any(line.startswith(f"| {hcp.id} | unmeasured | not measured |") for line in doubt)
    assert any(line.startswith(f"| {fcc.id} | disagreement | 0.0123 |") for line in doubt)
    opened = "\n".join(section(md, "Open decisions"))
    assert all(f"| {k} | " in opened for k in open_decisions()) and "| anomaly_filter.checks_before_relaxation | [1, 9, 10, 11] |" in opened
    assert all(re.search(rf"^\| {d} .*\| open: team decision \|$", opened, re.M) for d in ("D1", "D2", "D3", "D4", "D5"))
    assert "| charge: no setting or check models the net charge of the fragments | open: team decision |" in opened
    unchecked = "\n".join(section(md, "Not checked"))
    assert "on checks 1, 9, 10, 11 only" in unchecked and "not converged among the survivors: capped." in unchecked
    assert "| Of them, reference relaxations for E(FS ∞) and E_ads |" in md

    path = here.run.dir / "PROJECT.md"
    text = path.read_text()
    title, _, rest = text.partition("\n\n")
    path.write_text(f"{title}\n\n> **Example study.** OH on Pt(111) with the emt potential.\n\n{rest}")
    try:
        report("fixes", [final], [], flags, {})
        head = (here.run.dir / "report.md").read_text().split("\n## ", 1)[0]
        assert "> **Example study.** Every number in this report comes from a test potential, emt," in head and "no chemical claim" in head
    finally:
        path.write_text(text)


# ---- prompt: the literature sources, offline
class Reply:
    """What urlopen returns: a context manager whose body is the bytes given."""

    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.body


def test_catalysis_hub_sends_the_key_and_reads_the_reply(run, monkeypatch):
    sent = []
    node = {"reactionEnergy": 0.1, "products": '{"OHstar": 1}', "sites": '{"OH": "fcc"}', "dftCode": "TEST", "dftFunctional": "TEST",
            "pubId": "Test1", "publication": {"doi": "10.1234/test"}}           # synthetic: it tests the parsing, it is not data

    def urlopen(req, timeout=None):
        sent.append(req)
        return Reply(json.dumps({"data": {"reactions": {"edges": [{"node": node}]}}}).encode())
    monkeypatch.setenv("CATHUB_API_KEY", "test-key")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    values = literature.literature_lookup("Pt(111) OH", "E_ads", ["catalysis_hub"])
    assert len(sent) == 1 and sent[0].full_url == literature.CatalysisHub.url
    assert {k.lower(): v for k, v in sent[0].header_items()}["x-api-key"] == "test-key"
    assert [(v.value, v.source, v.verified_by_human) for v in values] == [(0.1, "https://doi.org/10.1234/test", False)]


def test_catalysis_hub_without_a_key_says_how_to_get_one_and_sends_nothing(monkeypatch):
    monkeypatch.delenv("CATHUB_API_KEY", raising=False)
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: calls.append(a))
    with pytest.raises(PermissionError, match="not configured.*CATHUB_API_KEY"):
        literature.CatalysisHub().post("{}")
    with pytest.raises(LookupError, match="not configured.*CATHUB_API_KEY"):
        literature.literature_lookup("Pt(111) OH", "E_ads", ["catalysis_hub"])
    assert calls == []


@pytest.mark.parametrize("body, said", [(b'{"errors": [{"message": "Missing API key: sign in with ORCID"}]}', "Missing API key: sign in with ORCID"),
                                        (b'{"message": "Invalid API key"}', "Invalid API key"), (b"Unauthorized: no key given", "Unauthorized: no key given")])
def test_catalysis_hub_surfaces_the_message_of_a_401(monkeypatch, body, said):
    def urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "UNAUTHORIZED", {}, io.BytesIO(body))
    monkeypatch.setenv("CATHUB_API_KEY", "wrong-key")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with pytest.raises(PermissionError) as e:
        literature.CatalysisHub().post("{}")
    assert str(e.value) == f"Catalysis-Hub answered 401: {said}"

    def down(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, io.BytesIO(b""))
    monkeypatch.setattr(urllib.request, "urlopen", down)
    with pytest.raises(ConnectionError, match="answered 503: Service Unavailable"):
        literature.CatalysisHub().post("{}")


def test_cmr_catapp_reads_reaction_energies_from_the_local_database(run, monkeypatch, tmp_path):
    from ase import Atoms
    from ase.db import connect
    data = tmp_path / "data"
    data.mkdir()
    db = connect(str(data / "catapp.db"))
    db.write(Atoms("OH"), ab="OH*", a="O*", b="H*", surface="Pt(111)", xc="RPBE", er=0.311, url="http://example.org/catapp/1")
    db.write(Atoms("OH"), ab="OH*", a="O*", b="H*", surface="Pd(111)", xc="RPBE", er=0.25, url="http://example.org/catapp/2")
    db.write(Atoms("OH"), ab="OH*", a="OH*", b="H*", surface="Pt(111)", xc="RPBE", er=9.9, url="http://example.org/catapp/3")
    db.write(Atoms("OH"), ab="OH*", a="H*", b="O*", surface="Pt(111)", xc="PBE", er=0.42)       # no url: the CatApp page is the source
    monkeypatch.setenv("FRAGPLACE_DATA", str(data))
    values = literature.literature_lookup("Pt(111) OH->O+H", "reaction_energy", ["cmr_catapp"])
    assert [(v.value, v.functional, v.source) for v in values] == [(0.311, "RPBE", "http://example.org/catapp/1"), (0.42, "PBE", literature.CMRCatApp.page)]
    assert all(v.quantity == "reaction_energy" and v.system == "Pt(111) OH->O+H" and not v.verified_by_human for v in values)
    with pytest.raises(LookupError):
        literature.literature_lookup("Pt(111) OH", "E_ads", ["cmr_catapp"])     # CatApp holds no adsorption energies


def test_cmr_catapp_never_caches_a_page_for_the_database(monkeypatch, tmp_path):
    monkeypatch.setenv("FRAGPLACE_DATA", str(tmp_path))
    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout=None: Reply(b"<html>moved</html>"))
    with pytest.raises(LookupError, match="no SQLite database"):
        literature.CMRCatApp().database()
    assert not (tmp_path / "catapp.db").exists() and not (tmp_path / "catapp.part").exists()


def test_papers_need_a_doi_or_url_and_answer_their_own_system(run):
    def value(source, system="", energy=-1.0):
        return LiteratureValue(quantity="E_ads", value=energy, unit="eV", system=system, source=source, verified_by_human=True)
    with pytest.raises(ValueError, match="DOI or a URL"):
        literature.literature_lookup("Pt(111) OH", "E_ads", ["papers"], [value("10.1021/fine"), value("Smith et al. 2020")])
    with pytest.raises(ValueError, match="name the source papers"):
        literature.literature_lookup("Pt(111) OH", "E_ads", ["catalysis_hub"], [value("10.1021/fine")])
    got = literature.literature_lookup("Pt(111) O", "E_ads", ["papers"], [value("10.1021/oh", "Pt(111) OH", -2.0),
                                                                          value("https://doi.org/10.1/o", "Pt(111)  O", -4.0), value("doi:10.5/any")])
    assert [(v.value, v.system, v.verified_by_human) for v in got] == [(-4.0, "Pt(111)  O", False), (-1.0, "Pt(111) O", False)]
