"""Hooks that enforce the rules prose cannot: the LLM never edits coordinates or the campaign's records, never runs
a tool past a checkpoint the human has not passed, and never passes a checkpoint itself.

Claude Code calls these with the tool input as JSON on stdin; exit code 2 blocks the call and the message is shown.
Wired in hooks/hooks.json as python -m fragplace.runtime.policy <command>. The checkpoint each tool needs is the
registry's checkpoint_gate, so the hook and the docs cannot disagree; the campaign is the one the tool call names,
under the root the MCP server uses. The human passes a checkpoint from a shell, or with ! in the Claude Code
prompt, which runs outside the model's tool calls and so outside these hooks.
"""
from __future__ import annotations

import json
import os
import re
import sys

from .checkpoints import passed
from .journal import default_root

STRUCTURE_FILE = re.compile(r"(^|/)(runs/.*/structures/|structures/).*\.(xyz|extxyz|cif|vasp|json|traj)$")
RECORD_FILE = re.compile(r"(^|/)runs/[^/]+/(checkpoints\.json|state\.json|artifacts\.json|trace\.jsonl|PROJECT\.md)$|(^|/)lessons\.md$")
SELF_APPROVAL = re.compile(r"fragplace\b.*\bapprove\b|record_choice|checkpoints\.(record|json)|lock\(")
TOOL = re.compile(r"^mcp__(plugin_fragplace_)?fragplace__(\w+)$")


def block_coordinate_edits() -> int:
    data = json.load(sys.stdin)
    path = str(data.get("tool_input", {}).get("file_path", "") or data.get("tool_input", {}).get("notebook_path", ""))
    if STRUCTURE_FILE.search(path):
        print("blocked: structures are written by tools only; the LLM never edits coordinates", file=sys.stderr)
        return 2
    if RECORD_FILE.search(path):
        print("blocked: a campaign's PROJECT.md, checkpoints, state, artifacts and trace, and the case bank, are written by code and by the "
              "human only; a decision the human gave goes in with fragplace decide, an interview answer with the note tool", file=sys.stderr)
        return 2
    return 0


def block_self_approval() -> int:
    """Block a shell command of the model that would pass a checkpoint: only the human does that."""
    data = json.load(sys.stdin)
    command = str(data.get("tool_input", {}).get("command", ""))
    if SELF_APPROVAL.search(command):
        print("blocked: only the human passes a checkpoint. Show the human the command and stop; the human runs it in a shell "
              "or with ! in the prompt", file=sys.stderr)
        return 2
    return 0


def require_checkpoint() -> int:
    """Block a pipeline tool call when the checkpoint it is gated on has not been passed."""
    data = json.load(sys.stdin)
    m = TOOL.match(str(data.get("tool_name", "")))
    if not m:
        return 0
    from ..registry.tools import BY_NAME
    spec = BY_NAME.get(m.group(2))
    if spec is None or spec.checkpoint_gate is None:
        return 0
    campaign = data.get("tool_input", {}).get("campaign") or data.get("campaign") or os.environ.get("FRAGPLACE_CAMPAIGN", "current")
    if spec.checkpoint_gate in {c.checkpoint for c in passed(default_root() / "runs" / campaign)}:
        return 0
    print(f"blocked: {spec.name} needs the '{spec.checkpoint_gate}' checkpoint, which the human has not passed; "
          f"stop and show the human: fragplace approve {campaign} \"{spec.checkpoint_gate}\" --reason \"...\"", file=sys.stderr)
    return 2


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"block-coordinate-edits": block_coordinate_edits, "block-self-approval": block_self_approval,
              "require-checkpoint": require_checkpoint}[cmd]())


if __name__ == "__main__":
    main()
