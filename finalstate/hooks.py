"""Hooks that enforce the two rules prose cannot: the LLM never edits coordinates, and never runs a tool past a
checkpoint the human has not passed.

Claude Code calls these with the tool input as JSON on stdin; exit code 2 blocks the call and the message is shown.
Wired in hooks/hooks.json. The checkpoint each tool needs is the registry's checkpoint_gate, so the hook and the
docs cannot disagree.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .checkpoints import passed

STRUCTURE_FILE = re.compile(r"(^|/)(runs/.*/structures/|structures/).*\.(xyz|extxyz|cif|vasp|json|traj)$")


def block_coordinate_edits() -> int:
    data = json.load(sys.stdin)
    path = str(data.get("tool_input", {}).get("file_path", ""))
    if STRUCTURE_FILE.search(path):
        print("blocked: structures are written by tools only; the LLM never edits coordinates", file=sys.stderr)
        return 2
    return 0


def require_checkpoint() -> int:
    """Block a pipeline tool call when the checkpoint it is gated on has not been passed."""
    data = json.load(sys.stdin)
    tool = str(data.get("tool_name", ""))
    if not tool.startswith("mcp__finalstate__"):
        return 0
    name = tool.split("__")[-1]
    from .registry import BY_NAME
    spec = BY_NAME.get(name)
    if spec is None or spec.checkpoint_gate is None:
        return 0
    run_dir = Path(data.get("cwd", ".")) / "runs" / data.get("campaign", "current")
    if spec.checkpoint_gate in {c.checkpoint for c in passed(run_dir)}:
        return 0
    print(f"blocked: {name} needs the '{spec.checkpoint_gate}' checkpoint, which the human has not passed", file=sys.stderr)
    return 2


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"block-coordinate-edits": block_coordinate_edits, "require-checkpoint": require_checkpoint}[cmd]())


if __name__ == "__main__":
    main()
