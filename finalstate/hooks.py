"""Hooks that enforce the two rules prose cannot: the LLM never edits coordinates, and never passes a checkpoint.

Claude Code calls these with the tool input as JSON on stdin; exit code 2 blocks the call and the message is shown.
Wired in hooks/hooks.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .checkpoints import AFTER_STEP, CHECKPOINTS, passed

STRUCTURE_FILE = re.compile(r"(^|/)(runs/.*/structures/|structures/).*\.(xyz|extxyz|cif|vasp|json|traj)$")
# which checkpoint must be passed before a tool of a later step may run
ORDER = ["prompt", "1", "1*", "2", "3.5", "3.2", "3.3", "3.4", "3.6", "4", "5", "6", "7", "8", "solution"]


def block_coordinate_edits() -> int:
    data = json.load(sys.stdin)
    path = str(data.get("tool_input", {}).get("file_path", ""))
    if STRUCTURE_FILE.search(path):
        print("blocked: structures are written by tools only; the LLM never edits coordinates", file=sys.stderr)
        return 2
    return 0


def require_checkpoint() -> int:
    """Block a pipeline tool call when the checkpoint before its step has not been passed."""
    data = json.load(sys.stdin)
    tool = str(data.get("tool_name", ""))
    if not tool.startswith("mcp__finalstate__"):
        return 0
    name = tool.split("__")[-1]
    try:
        from .registry import BY_NAME
        steps = BY_NAME[name].board_steps
    except KeyError:
        return 0
    run_dir = Path(data.get("cwd", ".")) / "runs" / data.get("campaign", "current")
    done = {c.checkpoint for c in passed(run_dir)}
    for cp in CHECKPOINTS:
        gate_step = AFTER_STEP[cp]
        if cp in done:
            continue
        if any(ORDER.index(s) > ORDER.index(gate_step) for s in steps if s in ORDER):
            print(f"blocked: {name} runs after the '{cp}' checkpoint, which the human has not passed", file=sys.stderr)
            return 2
    return 0


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"block-coordinate-edits": block_coordinate_edits, "require-checkpoint": require_checkpoint}[cmd]())


if __name__ == "__main__":
    main()
