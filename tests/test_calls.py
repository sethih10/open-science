"""The tools as the orchestrator calls them: by study name, with summaries back, a gate or an open decision
answered with the question box to ask instead of raised, and the human's answers recorded by the hook from what
Claude Code collected. The example study is driven here the way the orchestrator drives it; the MCP server
publishes exactly these functions."""
import asyncio
import json

import pytest

from fragplace.errors import FragPlaceError
from fragplace.registry.tools import OPERATIONS, ORCHESTRATOR_OPERATIONS, REGISTRY
from fragplace.runtime import project
from fragplace.runtime.journal import set_run
from fragplace.study import calls, human
from fragplace.study.store import Study, record_choice, record_decision

pytest.importorskip("ase")
pytest.importorskip("acat")
pytest.importorskip("dscribe")

from fragplace.study.example import build_example  # noqa: E402

C = "agentic"


@pytest.fixture
def root(tmp_path, monkeypatch):
    from fragplace.tools.literature import CatalysisHub, CMRCatApp

    def offline(self, *args):
        raise OSError("offline in the tests")
    monkeypatch.setattr(CatalysisHub, "post", offline)
    monkeypatch.setattr(CMRCatApp, "database", offline)
    monkeypatch.setenv("FRAGPLACE_ROOT", str(tmp_path))
    monkeypatch.setenv("FRAGPLACE_HUMAN", "tester")
    yield tmp_path
    set_run(None)


def answer(box, choose):
    """The payload Claude Code gives the PostToolUse hook after the human answered a question box."""
    answers = {q["question"]: choose(q) for q in box["questions"]}
    return {"tool_name": "AskUserQuestion", "tool_input": {**box, "answers": answers}, "tool_response": {"questions": box["questions"], "answers": answers}}


def test_an_orchestrator_drives_the_example_to_the_report(root):
    assert calls.study_status(C)["inputs"] is False
    c = build_example(root, C)
    path = c.run.dir / "PROJECT.md"
    s = project.read(path)
    s.decisions["pair_enumeration.upper_bound_A"] = 3.0
    s.decisions["ranking.shortlist_size"] = None                          # left open: the orchestrator must ask
    project.write(path, s)

    assert "blocked" in calls.mlip_selection(C, "too early")               # gated on approve settings
    assert calls.literature_lookup(C)["found"] == 0
    assert calls.show_structures(C, "inputs")["open"].endswith("inputs.png")
    out = calls.structure_retrieval(C)
    assert out["fragment_A"] == "O" and out["fragment_B"] == "H" and out["cell_repeat"] == [2, 2]
    assert out["summary"].startswith("## Step 1 · Inputs, fragments") and any(f.endswith(".xyz") for f in out["files"])
    out = calls.calculation_protocol(C, "mlip", "the example runs no DFT; EMT computes every energy")
    box = out["ask_human"]
    assert box["questions"][0]["header"] == "Decision" and "ranking.shortlist_size" in box["questions"][0]["question"]
    said = human.record(answer(box, lambda q: "2"), root)
    assert any("ranking.shortlist_size = 2" in x for x in said)
    out = calls.calculation_protocol(C, "mlip", "the example runs no DFT; EMT computes every energy")
    assert out["checkpoint_due"] == "approve settings" and out["ask_human"]["questions"][0]["header"] == "Checkpoint"
    # the no-DFT lock: the run's settings only, and one line saying the potential computes every energy
    assert out["dft"] is False and set(out["proposed"]) == {"cell_repeat", "cell_A", "force_threshold_eV_per_A", "gas_references", "protocol", "protocol_reason"}
    assert "No DFT runs in this study" in out["summary"] and "Every energy in this study comes from" not in out["summary"]
    shown = json.dumps(out["ask_human"], ensure_ascii=False)
    assert "no DFT runs in this study" in shown and not any(w in shown for w in ("k-mesh", "Functional", "cutoff", "Pseudopotentials"))
    locked = project.read(path)
    assert locked.functional is None and locked.cutoff_eV is None and locked.kmesh is None and locked.convergence_target_meV is None
    assert locked.decisions["anomaly_filter.frequencies_source"] == "mlip" and "calculation_protocol.convergence_target_meV" not in locked.decisions
    status = calls.study_status(C)
    assert status["checkpoint_due"] == "approve settings" and len(status["interview_unanswered"][0]["questions"]) == 4
    interview = {"questions": [dict(q, options=[{"label": "Geometry first"}, {"label": "Settings first"}]) for q in status["interview_unanswered"][0]["questions"]]}
    human.record(answer(interview, lambda q: "Geometry first"), root)
    assert "| Geometry first |" in path.read_text()
    with pytest.raises(FragPlaceError):
        record_choice(root, C, "approve the plan", [], "out of order", "tester")
    said = human.record(answer(status["ask_human"], lambda q: "Change something"), root)
    assert any("not passed" in x for x in said) and project.read(path).locked is False
    said = human.record(answer(status["ask_human"], lambda q: "Approve"), root)
    assert any("'approve settings' passed by tester" in x for x in said) and project.read(path).approved_by == "tester"
    with pytest.raises(FragPlaceError):
        record_decision(root, C, "ranking.shortlist_size", 5, "tester", "too late, it is locked")

    out = calls.mlip_selection(C, "the only candidate; EMT is a test potential")
    assert out["using"] == "emt" and out["checkpoint_due"] == "approve the plan"
    assert calls.note(C, "scientific-critic", "the plan holds for a dry run")["noted"] == 2
    assert "error" in calls.note(C, "an impostor", "trust me")
    human.record(answer(out["ask_human"], lambda q: "Approve"), root)
    assert "blocked" in calls.structure_retrieval(C)                       # the human passed settings on its results

    assert calls.site_enumeration(C)["count"] == 4
    pairs = calls.pair_enumeration(C)
    assert pairs["count"] >= 2 and pairs["d_source"].startswith("measured")
    placed = calls.adsorbate_placement(C)["placed"]
    assert len(calls.pull_force_screen(C)["queue"]) == len(placed)
    cards = calls.descriptor_card(C, placed[:1], "placed")["cards"]
    assert "A–B distance" in cards[placed[0]]
    assert "blocked" in calls.relaxation(C)                                # the gate before relaxation comes first
    before = calls.anomaly_filter(C, stage="before_relaxation")
    assert before["stage"] == "before_relaxation" and set(before["passed"]) | set(before["rejected"]) == set(placed)
    order = list(reversed(before["passed"]))
    out = calls.relaxation(C, order=order[:1], reason="the farthest first, to see the separated limit early")
    assert out["order"][0] == order[0] and len(out["results"]) == len(before["passed"])
    assert any(f.startswith("geometries/4-relaxed/") for f in out["files"])
    gates = calls.anomaly_filter(C)
    assert set(gates["passed"]) | set(gates["rejected"]) == set(before["passed"])
    kept = calls.soap_clustering(C)["kept"]
    assert kept
    assert "blocked" in calls.ranking(C)                                   # flags first
    out = calls.uncertainty_estimation(C)
    assert out["checkpoint_due"] == "review flagged cases"
    calls.note(C, "mlip-specialist", "trust: one test potential, no disagreement to measure")
    human.record(answer(out["ask_human"], lambda q: "Approve"), root)
    out = calls.ranking(C)
    ranked = out["ranked"]
    assert [r["rank"] for r in ranked] == list(range(1, len(ranked) + 1)) and "card" in ranked[0]
    pick = out["ask_human"]
    assert pick["questions"][0]["header"] == "Pick" and pick["questions"][0]["multiSelect"]
    said = human.record(answer(pick, lambda q: q["options"][0]["label"]), root)
    assert any("pick up to five final states' passed by tester" in x for x in said)
    states = calls.reference_energies(C)["final_states"]
    assert states[0]["candidate_id"] == ranked[0]["id"]
    out = calls.report(C)
    assert out["checkpoint_due"] == "interpret results"
    calls.note(C, "scientific-critic", "a long review " * 2000)
    assert len(json.dumps(calls.study_status(C), ensure_ascii=False)) < 20000      # Claude Code refuses a tool result much larger
    human.record(answer(calls.study_status(C)["ask_human"], lambda q: "Approve"), root)
    text = (root / "runs" / C / "report.md").read_text()
    assert "What the agents said" in text and "surface-chemist" in text and "## Steps in brief" in text and "The human's interpretation" in text
    brief = (root / "runs" / C / "summary.md").read_text()
    assert brief.index("· Inputs, fragments") < brief.index("· Relaxation") < brief.index("· Final states")
    events = [json.loads(line) for line in (root / "runs" / C / "trace.jsonl").read_text().splitlines()]
    assert {"tester", "human", "surface-chemist", "mlip-specialist", "scientific-critic"} <= {e["actor"] for e in events}
    assert Study(root, C).data["order"] == order[:1]
    assert not (root / "lessons.md").exists()                              # an example study teaches the case bank nothing


def test_inputs_without_energies_lock_with_no_dft_and_the_potential_computes_the_gas_references(root):
    c = build_example(root, C)
    c.put("inputs", {k: dict(v, energy_eV=None) if isinstance(v, dict) else v for k, v in c.data["inputs"].items()})
    calls.structure_retrieval(C)
    out = calls.calculation_protocol(C, "mlip", "the inputs carry no energies and no DFT runs")
    assert "open_decision" not in out and out["checkpoint_due"] == "approve settings", out
    assert out["proposed"]["gas_references"] == "OH, computed with the potential chosen at 1*"
    record_choice(root, C, "approve settings", [], "no DFT", "tester")
    assert project.read(c.run.dir / "PROJECT.md").gas_references == []           # the lock holds the species, never a file's energy
    assert calls.mlip_selection(C, "EMT is the example's test potential")["using"] == "emt"
    refs = json.loads((c.run.dir / project.GAS_FILE).read_text())
    assert [(g["species"], g["calculator"]) for g in refs] == [("OH", "emt")] and isinstance(refs[0]["energy_eV"], float)
    assert Study(root, C).data["inputs"]["adsorbate_vacuum"]["energy_eV"] is None   # the files' values stay the files'


def test_a_checked_value_rewrites_its_summary_block(root):
    build_example(root, C)
    paper = {"species": "AB", "quantity": "bond_length_d", "value": 0.97, "unit": "Å", "source": "https://doi.org/10.1000/test"}
    out = calls.literature_lookup(C, "bond_length_d", reported=[paper])
    assert out["found"] == 1 and out["values"][0]["system"].endswith("OH")
    assert "error" in calls.literature_lookup(C, reported=[dict(paper, quantity="E_ads", species=None)])   # E_ads covers AB, A and B
    said = human.record(answer(out["ask_human"], lambda q: q["options"][0]["label"]), root)
    assert any("checked against the source: lit:0" in x for x in said)
    block = (root / "runs" / C / "summary.md").read_text().split("<!-- step:literature_lookup -->")[1]
    assert "1 checked by the human" in block and "Rewritten after the human's checks." in block


def test_the_hook_ignores_other_questions_and_refuses_placeholders(root):
    build_example(root, C)
    other = {"questions": [{"question": "Which runtime?", "header": "Runtime", "options": [{"label": "a"}, {"label": "b"}], "multiSelect": False}]}
    assert human.record(answer(other, lambda q: "a"), root) == []
    with pytest.raises(FragPlaceError):
        record_decision(root, C, "ranking.shortlist_size", 3, "<your name>", "the human said so")
    with pytest.raises(FragPlaceError):
        record_decision(root, C, "ranking.shortlist_size", 3, "tester", "<your reason>")


def test_the_server_publishes_the_registry_and_the_operations(root):
    pytest.importorskip("mcp")
    from fragplace.mcp.server import build
    server = build(root)

    async def main():
        tools = await server.list_tools()
        status = await server.call_tool("study_status", {"study": "nothing-here"})
        return tools, status
    tools, status = asyncio.run(main())
    assert {t.name for t in tools} == {t.name for t in REGISTRY} | set(OPERATIONS) | set(ORCHESTRATOR_OPERATIONS)
    assert all("study" in t.inputSchema["properties"] for t in tools)
    assert "fragplace init nothing-here" in str(status)
