"""The hooks block coordinate edits and tool calls whose checkpoint gate the human has not passed."""
import io
import json
import sys
from pathlib import Path

from finalstate import checkpoints, hooks
from finalstate.records import HumanChoice


def run(fn, payload):
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        return fn()
    finally:
        sys.stdin = sys.__stdin__


def test_coordinate_edit_is_blocked():
    assert run(hooks.block_coordinate_edits, {"tool_input": {"file_path": "runs/x/structures/c1.extxyz"}}) == 2
    assert run(hooks.block_coordinate_edits, {"tool_input": {"file_path": "README.md"}}) == 0


def test_tool_is_blocked_until_its_gate_is_passed(tmp_path: Path):
    run_dir = tmp_path / "runs" / "current"
    run_dir.mkdir(parents=True)
    payload = {"tool_name": "mcp__finalstate__site_enumeration", "cwd": str(tmp_path), "campaign": "current"}
    assert run(hooks.require_checkpoint, payload) == 2
    checkpoints.record(run_dir, HumanChoice(checkpoint="approve the plan", chosen=[], reason="ok", who="team"))
    assert run(hooks.require_checkpoint, payload) == 0
    assert run(hooks.require_checkpoint, {"tool_name": "mcp__finalstate__structure_retrieval", "cwd": str(tmp_path), "campaign": "current"}) == 0
    assert run(hooks.require_checkpoint, {"tool_name": "Read", "cwd": str(tmp_path)}) == 0
