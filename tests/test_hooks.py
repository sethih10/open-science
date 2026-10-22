"""The hooks block coordinate edits and tool calls whose checkpoint gate the human has not passed."""
import io
import json
import sys
from pathlib import Path

from fragplace.registry.tools import mcp_name
from fragplace.runtime import checkpoints, policy as hooks
from fragplace.schemas.records import HumanChoice


def run(fn, payload):
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        return fn()
    finally:
        sys.stdin = sys.__stdin__


def test_coordinate_and_record_edits_are_blocked():
    assert run(hooks.block_coordinate_edits, {"tool_input": {"file_path": "runs/x/structures/c1.extxyz"}}) == 2
    for record in ("runs/x/checkpoints.json", "runs/x/artifacts.json", "runs/x/PROJECT.md", "/repo/lessons.md", "runs/x/trace.jsonl"):
        assert run(hooks.block_coordinate_edits, {"tool_input": {"file_path": record}}) == 2, record
    assert run(hooks.block_coordinate_edits, {"tool_input": {"file_path": "README.md"}}) == 0


def test_the_model_never_passes_a_checkpoint():
    for command in ('fragplace approve c "approve settings" --reason ok', "fragplace --root /x approve c 'pick up to five final states'",
                    "python -c 'from fragplace.agent.campaign import record_choice'"):
        assert run(hooks.block_self_approval, {"tool_input": {"command": command}}) == 2, command
    for command in ("fragplace decide c pair_enumeration.upper_bound_A 5.0 --reason 'the human said so'", "fragplace status c", "ls runs"):
        assert run(hooks.block_self_approval, {"tool_input": {"command": command}}) == 0, command


def test_tool_is_blocked_until_its_gate_is_passed(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FRAGPLACE_ROOT", str(tmp_path))
    run_dir = tmp_path / "runs" / "pt111"
    run_dir.mkdir(parents=True)
    payload = {"tool_name": mcp_name("site_enumeration"), "tool_input": {"campaign": "pt111"}}
    assert run(hooks.require_checkpoint, payload) == 2
    checkpoints.record(run_dir, HumanChoice(checkpoint="approve the plan", chosen=[], reason="ok", who="team"))
    assert run(hooks.require_checkpoint, payload) == 0
    assert run(hooks.require_checkpoint, {"tool_name": mcp_name("structure_retrieval"), "tool_input": {"campaign": "pt111"}}) == 0
    assert run(hooks.require_checkpoint, {"tool_name": "Read", "tool_input": {}}) == 0


def test_the_hook_falls_back_to_the_servers_campaign(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FRAGPLACE_ROOT", str(tmp_path))
    run_dir = tmp_path / "runs" / "pt111-oh"
    run_dir.mkdir(parents=True)
    checkpoints.record(run_dir, HumanChoice(checkpoint="approve the plan", chosen=[], reason="ok", who="team"))
    payload = {"tool_name": mcp_name("site_enumeration"), "tool_input": {}}
    assert run(hooks.require_checkpoint, payload) == 2                       # "current" has passed nothing
    monkeypatch.setenv("FRAGPLACE_CAMPAIGN", "pt111-oh")
    assert run(hooks.require_checkpoint, payload) == 0
