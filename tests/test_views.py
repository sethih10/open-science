"""What the human reads beside the tools: views.after_step writes each step's geometry files under
runs/<study>/geometries/<step>/, views.show draws named candidates and refuses an unknown one, and summary.md keeps
one block per step in the order of the pipeline, replaced when the step runs again. The study is a handful of
hand-made records on a 6x6 Pt(111) slab, wide enough for the window around the adsorbate, so the test takes
seconds and needs no potential."""
import random

import numpy as np
import pytest

from fragplace.runtime import artifacts
from fragplace.schemas.records import (Candidate, CheckVerdict, FinalState, GateResult, RankedCandidate, RelaxationResult, Role, Site,
                                       SiteEnumeration)

pytest.importorskip("ase")
pytest.importorskip("matplotlib")

from fragplace.study import summary, views  # noqa: E402
from fragplace.study.store import Study  # noqa: E402

IDS = ["A002-B014", "A002-B015", "A002-B018"]


@pytest.fixture
def study(run, tmp_path):
    """The records of a study that has run to the final states: three candidates placed, one stopped by the gate
    before relaxation, two relaxed, one of them rejected after; B of the first sits across the cell boundary."""
    from ase import Atoms
    from ase.build import fcc111
    slab = fcc111("Pt", size=(6, 6, 2), vacuum=7.0)
    slab.set_tags([artifacts.TAG_SURFACE if t == 1 else artifacts.TAG_SUBSURFACE for t in slab.get_tags()])
    top = slab.positions[[i for i, t in enumerate(slab.get_tags()) if t == artifacts.TAG_SURFACE]]
    corner = top[np.argmin(np.linalg.norm(top[:, :2], axis=1))]
    a1, a2 = slab.cell[0] / 6, slab.cell[1] / 6
    kinds = {"top": corner, "bridge": corner + a1 / 2, "fcc": corner + (a1 + a2) / 3, "hcp": corner + 2 * (a1 + a2) / 3}
    sites = [Site(index=k, label=label, point_group="C3v", coordination=1, position=tuple(map(float, p)), orbit=k) for k, (label, p) in enumerate(kinds.items())]
    sites += [Site(index=4 + k, label=s.label, point_group=s.point_group, coordination=1, position=tuple(map(float, np.array(s.position) + a1 + a2)),
                   orbit=s.index) for k, s in enumerate(sites)]
    slab_ref = artifacts.write(slab, "slab", Role.slab, energy_eV=-10.0)
    oh = Atoms("OH", positions=[[0, 0, 0], [0, 0, 0.97]], cell=[10, 10, 10], pbc=True)
    with_a = slab + Atoms("O", positions=[kinds["fcc"] + [0, 0, 1.2]], tags=[artifacts.TAG_A])
    initial = with_a + Atoms("H", positions=[kinds["fcc"] + [0, 0, 2.17]], tags=[artifacts.TAG_A])
    frag_a = Atoms("O", positions=[kinds["fcc"] + [0, 0, 1.2]], tags=[artifacts.TAG_A], cell=slab.cell, pbc=True)
    frag_b = Atoms("H", positions=[kinds["fcc"] + [0, 0, 2.17]], tags=[artifacts.TAG_B], cell=slab.cell, pbc=True)
    records = dict(inputs={"slab": slab_ref, "adsorbate_vacuum": artifacts.write(oh, "OH", Role.adsorbate_vacuum, energy_eV=-7.0),
                          "initial_state": artifacts.write(initial, "initial", Role.initial_state, energy_eV=-17.5), "bond_to_break": [0, 1]},
                  retrieval={"fragment_A": artifacts.write(frag_a, "A", Role.fragment_A), "fragment_B": artifacts.write(frag_b, "B", Role.fragment_B),
                             "cell_repeat": [1, 1], "structures": [slab_ref, artifacts.write(with_a, "slab-A", Role.reference)]},
                  sites=SiteEnumeration(sites=sites, count=4, burnside_count=4, symmetry_group="P3m1", baseline_count=3, slab=slab_ref,
                                        total_sites=len(sites)),
                  mlip={"calculator": "emt"})
    placed, relaxed = [], []
    for k, (cid, b) in enumerate(zip(IDS, (-1.5 * a1, a1, a2))):
        atoms = with_a + Atoms("H", positions=[kinds["fcc"] + b + [0, 0, 1.0]], tags=[artifacts.TAG_B])
        atoms.wrap()                                   # the first B lands across the cell boundary from A
        placed.append(Candidate(id=cid, structure=artifacts.write(atoms, cid, Role.candidate), site_A=2, site_B=k, orientation=0))
        if k:
            atoms.positions[-1] += [0.1, 0.0, -0.05]
            relaxed.append(RelaxationResult(candidate_id=cid, energy_eV=20.0 + k / 10, fmax_eV_per_A=0.02, steps=10 + k, converged=True, calculator="emt",
                                            structure=artifacts.write(atoms, f"{cid}-relaxed", Role.candidate)))
    failed = [CheckVerdict(check_id=10, name="bond re-formed", passed=False, reason="A–B 1.0 Å below 1.3 Å")]
    records.update(placed=placed, relaxed=relaxed,
                  gates_before=[GateResult(candidate_id=IDS[0], verdicts=failed, passed=False, stage="before_relaxation")]
                  + [GateResult(candidate_id=k, verdicts=[], passed=True, stage="before_relaxation") for k in IDS[1:]],
                  gates=[GateResult(candidate_id=IDS[1], verdicts=[], passed=True, stage="after_relaxation"),
                         GateResult(candidate_id=IDS[2], verdicts=failed, passed=False, stage="after_relaxation")],
                  clusters=[{"id": 0, "members": [IDS[1]], "nearest": IDS[1], "lowest": IDS[1]}], kept=[IDS[1]],
                  cards_kept=[{"candidate_id": IDS[1], "AB_distance_A": 2.9}],
                  ranked=[RankedCandidate(candidate_id=IDS[1], rank=1, site_graph_distance=1, energy_eV=20.1, reason="nearest")],
                  final_states=[FinalState(candidate_id=IDS[1], E_near_eV=20.1, E_inf_eV=20.0, lateral_interaction_eV=0.1, AB_distance_A=2.9,
                                           site_graph_distance=1)])
    c = Study(tmp_path, run.study)
    for key, value in records.items():               # through put, so each record is stored as artifacts.json holds it
        c.put(key, value)
    return Study(tmp_path, run.study)


EXPECTED = {
    "structure_retrieval": {"slab.xyz", "adsorbate-in-vacuum.xyz", "initial-state.xyz", "inputs.png", "fragment-A.xyz", "fragment-B.xyz",
                            "fragments.png", "selected-cell.xyz", "selected-cell.png"},
    "site_enumeration": {"sites.png", "slab-cell.xyz"},
    "adsorbate_placement": {"placed.xyz", "sheet.png"},
    "anomaly_filter_before": {"rejected.xyz", "rejected.png"},
    "relaxation": {f"{k}.{ext}" for k in IDS[1:] for ext in ("xyz", "png")} | {"sheet.png"},
    "anomaly_filter": {"passed.png", "rejected.png"},
    "soap_clustering": {"sheet.png"},
    "ranking": {"sheet.png"},
    "reference_energies": {"final-states.xyz", "sheet.png"},
}


def test_after_step_writes_each_steps_files(study):
    from ase.io import read
    assert set(EXPECTED) == set(views.FOLDERS)
    for tool_name, names in EXPECTED.items():
        folder = study.run.dir / "geometries" / views.FOLDERS[tool_name]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "stale.png").write_text("from an earlier run of the step")
        files = views.after_step(study, tool_name)
        assert all(f.startswith(f"geometries/{views.FOLDERS[tool_name]}/") for f in files), files
        assert {f.rsplit("/", 1)[-1] for f in files} == names, tool_name
        assert {p.name for p in folder.iterdir()} == names, tool_name           # the stale picture is gone
        assert all((study.run.dir / f).stat().st_size > 0 for f in files)
    frames = read(study.run.dir / "geometries" / "4-relaxed" / f"{IDS[1]}.xyz", index=":")
    assert len(frames) == 2 and frames[0].info["name"] == f"{IDS[1]} start"
    assert frames[1].get_potential_energy() == pytest.approx(20.1)
    assert views.after_step(study, "descriptor_card") == []


def test_the_window_keeps_a_pair_across_the_boundary_together(study):
    atoms = artifacts.read(Candidate.model_validate(study.data["placed"][0]).structure)
    split = artifacts.adsorbate_indices(atoms)
    assert np.linalg.norm(atoms.positions[split[0], :2] - atoms.positions[split[1], :2]) > 10.0    # A and B on opposite edges
    scene, top, side, outline = views._scene(atoms)
    ads = [i for i, t in enumerate(scene.get_tags()) if t in (artifacts.TAG_A, artifacts.TAG_B)]
    assert outline is None and len(ads) == 2 and len(scene) < len(atoms) * 4
    assert np.linalg.norm(scene.positions[ads[0], :2] - scene.positions[ads[1], :2]) < 5.0     # whole again in the window
    assert all(top[0] < x < top[2] and top[1] < y < top[3] for x, y in scene.positions[ads, :2])
    whole = views._scene(atoms, whole=True)
    assert whole[3] is not None and len(whole[0]) == len(atoms)


def test_show_draws_named_candidates_and_refuses_unknown_ones(study):
    out = views.show(study, [IDS[1]], "relaxed")
    assert out["open"].endswith("views/relaxed/views.png") and f"geometries/views/relaxed/{IDS[1]}.xyz" in out["files"]
    out = views.show(study, None, "placed")
    assert out["open"].endswith("sheet.png") and len([f for f in out["files"] if f.endswith(".xyz")]) == len(IDS)
    assert views.show(study, [], "inputs")["open"].endswith("inputs.png")
    for ids, stage in (([IDS[0]], "relaxed"), (["not-a-candidate"], "placed"), (None, "somewhere"), ([IDS[1]], "inputs")):
        with pytest.raises(ValueError):
            views.show(study, ids, stage)
    study.data["final_states"] = []
    with pytest.raises(ValueError, match="nothing at stage final"):
        views.show(study, None, "final")


# The answers of fragplace.study.calls, one per tool, with the keys each returns.
ANSWERS = {
    "literature_lookup": {"found": 1, "none_for": ["B: no source gave a value"], "verify": "the human checks each value",
                          "values": [{"index": "lit:0", "verified": False, "quantity": "E_ads", "system": "Pt(111) OH", "value": -2.3, "unit": "eV",
                                      "functional": "RPBE", "site": "fcc", "source": "https://example.org/a-test-value"}]},
    "structure_retrieval": {"fragment_A": "O", "fragment_B": "H", "cell_repeat": [2, 2], "cell_A": [16.63, 16.63], "atoms_in_cell": 144},
    "calculation_protocol": {"proposed": {"functional": "RPBE", "pseudopotential_family": "PAW", "cutoff_eV": 350.0, "kmesh": [3, 3, 1],
                                          "smearing": "MP", "sigma_eV": 0.1, "layers": 4, "cell_repeat": [2, 2], "protocol": "oc20",
                                          "protocol_reason": "OC20NEB is the benchmark", "convergence_target_meV": 25.0},
                             "project_md": "PROJECT.md", "checkpoint_due": "approve settings"},
    "mlip_selection": {"benchmark": {"emt": {"error_eV": 0.12, "signed_errors_eV": [0.12], "anomalies": []}}, "best": "emt", "using": "emt",
                       "committee": ["emt"], "checkpoint_due": "approve the plan"},
    "compute_plan": {"timing": {"calculator": "emt", "atoms": 146, "s_per_force_call": 0.002, "force_calls_per_item": 150},
                     "estimates": {"relaxation": {"step": "4", "force_calls_per_item": 150, "minutes_per_item": 0.005, "items": None,
                                                  "total_minutes": None, "lane": "auto", "why": "the call decides"}},
                     "proposed": {"relaxation": {"lane": "auto", "batch_above_min": 70.0, "cpus": 8, "mem_GB": 16.0, "time": "04:00:00", "workers": 8}},
                     "reason": "relaxations may pass an hour", "warnings": [], "checkpoint_due": "approve the plan"},
    "site_enumeration": {"count": 4, "burnside_count": 4, "pymatgen_baseline": 3, "symmetry": "P3m1", "sites_in_cell": 216,
                         "inequivalent": [{"site": 0, "label": "top", "group": "C3v", "coordination": 1, "atom_beneath": None, "copies": 36}]},
    "pair_enumeration": {"A_site": {"site": 2, "label": "fcc"}, "count": 2, "d_source": "measured on the vacuum structure", "window_A": [1.47, 3.0],
                         "d_bond_A": 0.98, "pairs": [{"id": k, "B_site": "hcp", "site_graph_distance": 1, "in_plane_A": 1.6} for k in IDS]},
    "adsorbate_placement": {"placed": IDS, "count": 3},
    "pull_force_screen": {"queue": [{"id": k, "force_on_B_towards_A_eV_per_A": 0.6 - n / 10, "flagged": n == 0} for n, k in enumerate(IDS)]},
    "minima_hopping": {"minima": [{"id": "MH000", "energy_eV": 21.0}]},
    "anomaly_filter_before": {"stage": "before_relaxation", "passed": IDS[1:], "rejected": {IDS[0]: ["check 10 bond re-formed: A–B 1.0 Å"]}},
    "relaxation": {"order": IDS[1:], "slab_energy_eV": 10.0, "results": [{"id": k, "energy_eV": 20.0 + n, "steps": 10, "converged": True, "cache_hit": False}
                                                                        for n, k in enumerate(IDS[1:])]},
    "anomaly_filter": {"passed": [IDS[1]], "rejected": {IDS[2]: ["check 5 not a minimum: one imaginary mode"]},
                       "not_checked": ["check 6 magnetism collapsed: not checked, no moments"]},
    "soap_clustering": {"clusters": [{"id": 0, "members": [IDS[1]], "nearest": IDS[1], "lowest": IDS[1]}], "kept": [IDS[1]]},
    "uncertainty_estimation": {"flags": [{"candidate_id": IDS[1], "committee_spread_eV": 0.0, "calibrated_error_eV": None, "trigger": "one potential",
                                          "escalate": True}], "escalated": [f"{IDS[1]} one potential"], "checkpoint_due": "review flagged cases"},
    "ranking": {"ranked": [{"rank": 1, "id": IDS[1], "reason": "nearest", "card": "card text"}], "checkpoint_due": "pick up to five final states"},
    "reference_energies": {"final_states": [{"candidate_id": IDS[1], "E_near_eV": 20.1, "E_inf_eV": 20.0, "lateral_interaction_eV": 0.1,
                                             "AB_distance_A": 2.9, "site_graph_distance": 1, "recombined": False}]},
    "report": {"report_md": "report.md", "final_states": [{"candidate_id": IDS[1]}], "rejected": 2, "recombination_rate": 0.5, "by_shell": {"1": 0.5},
               "checkpoint_due": "interpret results"},
}


def test_summary_reads_in_pipeline_order_and_a_rerun_replaces_its_block(study):
    assert set(ANSWERS) == set(summary.FORMATS) == set(summary.ORDER)
    shuffled = list(ANSWERS)
    random.Random(7).shuffle(shuffled)
    for tool_name in shuffled:
        block = summary.write(study, tool_name, "4", ANSWERS[tool_name], [f"geometries/x/{tool_name}.xyz", "geometries/x/sheet.png"])
        assert block.startswith("## Step 4 · ") and "could not be read" not in block, block
        assert "Tool `" in block.splitlines()[-1]
    text = (study.run.dir / "summary.md").read_text()
    assert text.startswith(f"# {study.run.study} in brief\n") and "OH* → O* + H* on Pt(111)" in text
    marks = [line.removeprefix("<!-- step:").removesuffix(" -->") for line in text.splitlines() if line.startswith("<!-- step:")]
    assert marks == list(summary.ORDER)
    assert text.index("Gate before relaxation") < text.index("· Relaxation") < text.index("Gate after relaxation")

    again = dict(ANSWERS["relaxation"], results=[{"id": "R9", "energy_eV": 1.5, "steps": 3, "converged": False, "cache_hit": True}])
    block = summary.write(study, "relaxation", "4", again, [])
    text = (study.run.dir / "summary.md").read_text()
    assert text.count("<!-- step:relaxation -->") == 1 and "R9" in text and IDS[2] not in block and block in text
    assert summary.write(study, "descriptor_card", "3.4", {"cards": {}}, []) == ""
    assert (study.run.dir / "summary.md").read_text() == text

    brief = summary.full(study)
    assert "<!--" not in brief and "\n\n\n" not in brief and brief.count("\n## ") == len(summary.ORDER)
    assert "Next: you are asked to approve the settings." in text and "Next: you are asked" not in brief   # by the end, all were asked


def test_a_changed_answer_still_gives_a_block(study):
    block = summary.write(study, "relaxation", "4", {"results": [{"id": "x"}], "order": 3}, [])
    assert block.startswith("## Step 4 · Relaxation")
    block = summary.write(study, "pair_enumeration", "3.2", {"pairs": "not a list"}, [])
    assert "could not be read" in block and "pairs" in block
    assert summary.write(study, "literature_lookup", "prompt", {"found": [], "message": "offline"}, []).startswith("## Input prompt · ")
