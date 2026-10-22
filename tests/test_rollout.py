"""The example study end to end with EMT through the test harness: the rollout stops at each of the five checkpoints,
the human's choice is checked and recorded, and the run ends with a report and a trace that names every core tool; an
example study leaves the case bank alone."""
import json

import pytest

from fragplace.study import rollout
from fragplace.study.store import Study, briefing, record_choice
from fragplace.errors import CheckpointPending, FragPlaceError
from fragplace.registry.agents import CHECKPOINTS
from fragplace.registry.tools import CORE
from fragplace.runtime import artifacts, project
from fragplace.schemas.records import StructureRef
from fragplace.runtime.journal import set_run

pytest.importorskip("ase")
pytest.importorskip("acat")
pytest.importorskip("dscribe")

from fragplace.study.example import build_example  # noqa: E402


def test_example_study_runs_to_the_report(tmp_path, monkeypatch):
    from fragplace.tools.literature import CatalysisHub, CMRCatApp

    def offline(self, *args):
        raise OSError("offline in the tests")
    monkeypatch.setattr(CatalysisHub, "post", offline)
    monkeypatch.setattr(CMRCatApp, "database", offline)
    c = build_example(tmp_path, "e2e")
    path = c.run.dir / "PROJECT.md"
    s = project.read(path)
    s.decisions["pair_enumeration.upper_bound_A"] = 3.0          # fewer pairs: the test is about the rollout, not the chemistry
    project.write(path, s)
    assert "Example study" in path.read_text()

    stops = []
    for _ in range(len(CHECKPOINTS) + 1):
        try:
            assert rollout.run(c.run.dir, "e2e", Study(tmp_path, "e2e").invoke) == "done"
            break
        except CheckpointPending as e:
            stops.append(e.name)
            assert briefing(tmp_path, "e2e", e.name)
            chosen = []
            if e.name == "review flagged cases":
                with pytest.raises(FragPlaceError):
                    record_choice(tmp_path, "e2e", e.name, ["not-kept"], "test", "tester")
                chosen = Study(tmp_path, "e2e").data["kept"][:1]                      # the human keeps one; the ranking shows only it
            if e.name == "pick up to five final states":
                ranked = Study(tmp_path, "e2e").data["ranked"]
                with pytest.raises(FragPlaceError):
                    record_choice(tmp_path, "e2e", e.name, ["not-a-candidate"], "test", "tester")
                chosen = [ranked[0]["candidate_id"]]
            with pytest.raises(FragPlaceError):
                record_choice(tmp_path, "e2e", e.name, chosen, " ", "tester")         # a choice needs its reason
            record_choice(tmp_path, "e2e", e.name, chosen, "test", "tester")
    set_run(None)
    assert stops == list(CHECKPOINTS)
    assert project.read(path).locked and project.read(path).approved_by == "tester"

    data = json.loads((c.run.dir / "artifacts.json").read_text())
    passed_before = [g["candidate_id"] for g in data["gates_before"] if g["passed"]]
    assert data["pairs"] and len(data["placed"]) >= len(data["pairs"]) and len(data["gates"]) == len(passed_before)
    assert len(data["final_states"]) == 1 and data["final_states"][0]["candidate_id"] == data["ranked"][0]["candidate_id"]
    assert [r["candidate_id"] for r in data["ranked"]] == data["kept"][:1]
    report = (c.run.dir / "report.md").read_text()
    assert "## Final states" in report and "## Recombination rate" in report and data["final_states"][0]["candidate_id"] in report
    assert "from emt, the potential" in report and "## The human's choices" in report and "| tester |" in report
    called = {json.loads(line)["tool"] for line in (c.run.dir / "trace.jsonl").read_text().splitlines()}
    assert {t.name for t in CORE} - {"minima_hopping"} <= called
    assert not (tmp_path / "lessons.md").exists()                    # an example study teaches the case bank nothing
    assert len(data["gates_before"]) == len(data["placed"]) and all(g["stage"] == "before_relaxation" for g in data["gates_before"])

    # the reaction energy is taken in one cell: the initial state is the selected slab plus the adsorbate, as the final state
    Study(tmp_path, "e2e")
    used = data["initial_state_used"]
    cell = artifacts.read(StructureRef.model_validate(data["retrieval"]["structures"][0]))
    ab = artifacts.read(StructureRef.model_validate(data["inputs"]["adsorbate_vacuum"]))
    supplied = artifacts.read(StructureRef.model_validate(data["inputs"]["initial_state"]))
    is_atoms = artifacts.read(StructureRef.model_validate(used["structure"]))
    assert tuple(used["cell_repeat"]) == tuple(data["retrieval"]["cell_repeat"]) != (1, 1)
    assert used["atoms"] == len(is_atoms) == len(cell) + len(ab) > len(supplied)
    assert is_atoms.cell.array == pytest.approx(cell.cell.array)
    fs = next(r for r in data["relaxed"] if r["candidate_id"] == data["final_states"][0]["candidate_id"])
    assert len(artifacts.read(StructureRef.model_validate(fs["structure"]))) == len(is_atoms)
    assert data["final_states"][0]["reaction_energy_eV"] is not None
    n1, n2 = used["cell_repeat"]
    assert f"E(IS) from the initial state in the selected cell, {n1}×{n2}" in report and f"{len(is_atoms)} atoms" in report

    # the report names the reference E_ads was computed against: no fragment vacuum files, so the cleaved fragments alone
    assert "fragment_A_vacuum" not in data["inputs"]
    assert "E_ads(A\\*) and E_ads(B\\*) are against the cleaved fragments alone in vacuum: O " in report
    assert "against the supplied A and B in vacuum" not in report
    set_run(None)


def test_a_checkpoint_is_recorded_only_when_pending(tmp_path):
    build_example(tmp_path, "early")
    with pytest.raises(FragPlaceError):
        record_choice(tmp_path, "early", "approve the plan", [], "too early", "tester")
    set_run(None)
