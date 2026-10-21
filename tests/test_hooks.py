"""The hooks block coordinate edits and tool calls past an unpassed checkpoint."""
import io
import json
import sys
from pathlib import Path

from finalstate import hooks


def run(fn, payload):
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        return fn()
    finally:
        sys.stdin = sys.__stdin__


def test_coordinate_edit_is_blocked():
    assert run(hooks.block_coordinate_edits, {"tool_input": {"file_path": "runs/x/structures/c1.extxyz"}}) == 2
    assert run(hooks.block_coordinate_edits, {"tool_input": {"file_path": "README.md"}}) == 0


def test_tool_after_unpassed_checkpoint_is_blocked(tmp_path: Path):
    (tmp_path / "runs" / "current").mkdir(parents=True)
    assert run(hooks.require_checkpoint, {"tool_name": "mcp__finalstate__site_enumeration", "cwd": str(tmp_path), "campaign": "current"}) == 2
    assert run(hooks.require_checkpoint, {"tool_name": "mcp__finalstate__structure_retrieval", "cwd": str(tmp_path), "campaign": "current"}) == 0
    assert run(hooks.require_checkpoint, {"tool_name": "Read", "cwd": str(tmp_path)}) == 0
