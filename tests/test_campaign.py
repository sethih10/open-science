"""The example campaign end to end with EMT: the rollout stops at each of the five checkpoints, the human's choice is
checked and recorded, and the run ends with a report, a trace that names every core tool and a case in the bank."""
import json

import pytest

from fragplace.agent import pipeline
from fragplace.agent.campaign import Campaign, briefing, record_choice
from fragplace.errors import CheckpointPending, FragPlaceError
from fragplace.registry.agents import CHECKPOINTS
from fragplace.registry.tools import CORE
from fragplace.runtime import project
from fragplace.runtime.journal import set_run

pytest.importorskip("ase")
pytest.importorskip("acat")
pytest.importorskip("dscribe")

from fragplace.agent.example import build_example  # noqa: E402


def test_example_campaign_runs_to_the_report(tmp_path, monkeypatch):
    from fragplace.tools.literature import CatalysisHub

    def offline(self, query):
        raise OSError("offline in the tests")
    monkeypatch.setattr(CatalysisHub, "post", offline)
    c = build_example(tmp_path, "e2e")
    path = c.run.dir / "PROJECT.md"
    s = project.read(path)
    s.decisions["pair_enumeration.upper_bound_A"] = 3.0          # fewer pairs: the test is about the rollout, not the chemistry
    project.write(path, s)
    assert "Example campaign" in path.read_text()

    stops = []
    for _ in range(len(CHECKPOINTS) + 1):
        try:
            assert pipeline.run(c.run.dir, "e2e", Campaign(tmp_path, "e2e").invoke) == "done"
            break
        except CheckpointPending as e:
            stops.append(e.name)
            assert briefing(tmp_path, "e2e", e.name)
            chosen = []
            if e.name == "review flagged cases":
                with pytest.raises(FragPlaceError):
                    record_choice(tmp_path, "e2e", e.name, ["not-kept"], "test", "tester")
                chosen = Campaign(tmp_path, "e2e").data["kept"][:1]                      # the human keeps one; the ranking shows only it
            if e.name == "pick up to five final states":
                ranked = Campaign(tmp_path, "e2e").data["ranked"]
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
    assert data["pairs"] and len(data["placed"]) >= len(data["pairs"]) and len(data["gates"]) == len(data["placed"])
    assert len(data["final_states"]) == 1 and data["final_states"][0]["candidate_id"] == data["ranked"][0]["candidate_id"]
    assert [r["candidate_id"] for r in data["ranked"]] == data["kept"][:1]
    report = (c.run.dir / "report.md").read_text()
    assert "## Final states" in report and "## Recombination rate" in report and data["final_states"][0]["candidate_id"] in report
    assert "from emt, the potential" in report and "## The human's choices" in report and "| tester |" in report
    called = {json.loads(line)["tool"] for line in (c.run.dir / "trace.jsonl").read_text().splitlines()}
    assert {t.name for t in CORE} - {"minima_hopping"} <= called
    assert "picked" in (tmp_path / "lessons.md").read_text()


def test_a_checkpoint_is_recorded_only_when_pending(tmp_path):
    build_example(tmp_path, "early")
    with pytest.raises(FragPlaceError):
        record_choice(tmp_path, "early", "approve the plan", [], "too early", "tester")
    set_run(None)
