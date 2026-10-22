"""The tools as an agent calls them: by campaign name, with summaries back, a gate or an open decision answered
instead of raised, the human's decisions and approvals recorded by the human's commands only. The example campaign
is driven here the way the solution-planner drives it; the MCP server publishes exactly these functions."""
import asyncio
import json

import pytest

from fragplace.agent import interface as agent
from fragplace.agent.campaign import Campaign, record_choice, record_decision
from fragplace.errors import FragPlaceError
from fragplace.registry.tools import OPERATIONS, REGISTRY
from fragplace.runtime import project
from fragplace.runtime.journal import set_run

pytest.importorskip("ase")
pytest.importorskip("acat")
pytest.importorskip("dscribe")

from fragplace.agent.example import build_example  # noqa: E402

C = "agentic"


@pytest.fixture
def root(tmp_path, monkeypatch):
    from fragplace.tools.literature import CatalysisHub

    def offline(self, query):
        raise OSError("offline in the tests")
    monkeypatch.setattr(CatalysisHub, "post", offline)
    monkeypatch.setenv("FRAGPLACE_ROOT", str(tmp_path))
    yield tmp_path
    set_run(None)


def human(root, checkpoint, chosen=()):
    record_choice(root, C, checkpoint, list(chosen), "the human looked and agrees", "tester")


def test_an_agent_drives_the_example_to_the_report(root):
    assert agent.campaign_status(C)["inputs"] is False
    c = build_example(root, C)
    path = c.run.dir / "PROJECT.md"
    s = project.read(path)
    s.decisions["pair_enumeration.upper_bound_A"] = 3.0
    s.decisions["ranking.shortlist_size"] = None                          # left open: the planner must ask
    project.write(path, s)

    assert "blocked" in agent.mlip_selection(C, "too early")               # gated on approve settings
    assert agent.literature_lookup(C)["found"] == []
    out = agent.structure_retrieval(C)
    assert out["fragment_A"] == "O" and out["fragment_B"] == "H" and out["cell_repeat"] == [2, 2]
    out = agent.calculation_protocol(C, "oc20", "the first case is scored against OC20NEB")
    assert "ranking.shortlist_size" in out["meanings"] and "fragplace decide" in out["ask_human"]
    record_decision(root, C, "ranking.shortlist_size", 2, "tester", "two are enough to compare")
    out = agent.calculation_protocol(C, "oc20", "the first case is scored against OC20NEB")
    assert out["checkpoint_due"] == "approve settings" and "fragplace approve" in out["human_runs"]
    status = agent.campaign_status(C)
    assert status["checkpoint_due"] == "approve settings" and "PROJECT.md" in status["evidence"]
    with pytest.raises(FragPlaceError):
        record_choice(root, C, "approve the plan", [], "out of order", "tester")
    human(root, "approve settings")
    with pytest.raises(FragPlaceError):
        record_decision(root, C, "ranking.shortlist_size", 5, "tester", "too late, it is locked")

    out = agent.mlip_selection(C, "the only candidate; EMT is a test potential", choose="emt")
    assert out["using"] == "emt" and out["checkpoint_due"] == "approve the plan"
    assert agent.note(C, "scientific-critic", "the plan holds for a dry run")["noted"] == 2
    assert "error" in agent.note(C, "an impostor", "trust me")
    human(root, "approve the plan")
    assert "blocked" in agent.structure_retrieval(C)                       # the human passed settings on its results

    assert agent.site_enumeration(C)["count"] == 4
    pairs = agent.pair_enumeration(C)
    assert pairs["count"] >= 2 and pairs["pairs"][0]["site_graph_distance"] <= pairs["pairs"][-1]["site_graph_distance"]
    placed = agent.adsorbate_placement(C)["placed"]
    assert len(agent.pull_force_screen(C)["queue"]) == len(placed)
    cards = agent.descriptor_card(C, placed[:1], "placed")["cards"]
    assert "A–B distance" in cards[placed[0]]
    order = list(reversed(placed))
    out = agent.relaxation(C, order=order[:1], reason="the farthest first, to see the separated limit early")
    assert out["order"][0] == order[0] and len(out["results"]) == len(placed)
    gates = agent.anomaly_filter(C)
    assert set(gates["passed"]) | set(gates["rejected"]) == set(placed)
    kept = agent.soap_clustering(C)["kept"]
    assert kept
    assert "blocked" in agent.ranking(C)                                   # flags first
    out = agent.uncertainty_estimation(C)
    assert out["checkpoint_due"] == "review flagged cases"
    agent.note(C, "mlip-specialist", "trust: one test potential, no disagreement to measure")
    human(root, "review flagged cases")
    ranked = agent.ranking(C)["ranked"]
    assert [r["rank"] for r in ranked] == list(range(1, len(ranked) + 1)) and "card" in ranked[0]
    with pytest.raises(FragPlaceError):
        record_choice(root, C, "pick up to five final states", [r["id"] for r in ranked] * 2, "too many", "tester")
    human(root, "pick up to five final states", [ranked[0]["id"]])
    states = agent.reference_energies(C)["final_states"]
    assert states[0]["candidate_id"] == ranked[0]["id"]
    out = agent.report(C)
    assert out["checkpoint_due"] == "interpret results"
    agent.note(C, "scientific-critic", "a long review " * 2000)
    assert len(json.dumps(agent.campaign_status(C), ensure_ascii=False)) < 20000      # Claude Code refuses a tool result much larger
    text = (root / "runs" / C / "report.md").read_text()
    assert "What the agents said" in text and "scientific-critic" in text and "surface-chemist" in text
    events = [json.loads(line) for line in (root / "runs" / C / "trace.jsonl").read_text().splitlines()]
    actors = {e["actor"] for e in events}
    assert {"tester", "surface-chemist", "mlip-specialist", "scientific-critic"} <= actors
    assert Campaign(root, C).data["order"] == order[:1]


def test_the_server_publishes_the_registry_and_the_two_operations(root):
    pytest.importorskip("mcp")
    from fragplace.mcp.server import build
    server = build(root)

    async def main():
        tools = await server.list_tools()
        status = await server.call_tool("campaign_status", {"campaign": "nothing-here"})
        return tools, status
    tools, status = asyncio.run(main())
    assert {t.name for t in tools} == {t.name for t in REGISTRY} | set(OPERATIONS)
    assert all("campaign" in t.inputSchema["properties"] for t in tools)
    assert "fragplace init nothing-here" in str(status)
