"""Hooks that enforce the rules prose cannot: the LLM never edits coordinates or the study's records, never runs
a tool past a checkpoint the human has not passed, never passes a checkpoint itself, and never answers its own
question.

Claude Code calls these with the tool input as JSON on stdin; exit code 2 blocks the call and the message is shown.
Wired in hooks/hooks.json as python -m fragplace.runtime.policy <command>. The checkpoint each tool needs is the
registry's checkpoint_gate, so the hook and the docs cannot disagree; the study is the one the tool call names,
under the root the MCP server uses. The human passes a checkpoint by answering the orchestrator's question box,
which fragplace.study.human records after Claude Code has collected the answer; in a terminal without Claude, the
human runs fragplace approve, which the model may not run.
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
SELF_APPROVAL = re.compile(r"\bfragplace(\.cli\.main)?(\s+--root\s+\S+)?\s+(approve|decide)\b|record_(choice|decision|interview)|study\.human|checkpoints\.(record|json)|lock\("
                           r"|(>|\btee\b|\bsed\s+-i|\bcp\b|\bmv\b|\brm\b)[^|;&]*runs/[^/\s]+/(PROJECT\.md|state\.json|artifacts\.json|trace\.jsonl)")
TOOL = re.compile(r"^mcp__(plugin_fragplace_)?fragplace__(\w+)$")


def block_coordinate_edits() -> int:
    data = json.load(sys.stdin)
    path = str(data.get("tool_input", {}).get("file_path", "") or data.get("tool_input", {}).get("notebook_path", ""))
    if STRUCTURE_FILE.search(path):
        print("blocked: structures are written by tools only; the LLM never edits coordinates", file=sys.stderr)
        return 2
    if RECORD_FILE.search(path):
        print("blocked: a study's PROJECT.md, checkpoints, state, artifacts and trace, and the case bank, are written by code and by the "
              "human only; ask the human with the question box, and the answer is recorded for you", file=sys.stderr)
        return 2
    return 0


def block_self_approval() -> int:
    """Block a shell command of the model that would pass a checkpoint, set a decision, feed the answer recorder or
    write a study's records: only the human's answers and the tools do that."""
    data = json.load(sys.stdin)
    command = str(data.get("tool_input", {}).get("command", ""))
    if SELF_APPROVAL.search(command):
        print("blocked: only the human passes a checkpoint. Ask with the question box that study_status gives under ask_human; "
              "the human's answer is recorded by code", file=sys.stderr)
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
    study = data.get("tool_input", {}).get("study") or data.get("study") or os.environ.get("FRAGPLACE_STUDY", "current")
    if spec.checkpoint_gate in {c.checkpoint for c in passed(default_root() / "runs" / study)}:
        return 0
    print(f"blocked: {spec.name} needs the '{spec.checkpoint_gate}' checkpoint, which the human has not passed; "
          f"call study_status for {study} and ask the human with the question box it gives under ask_human", file=sys.stderr)
    return 2


def guard_question() -> int:
    """Refuse a question box whose answers the model filled in: the answers are the human's to give. Claude Code drops
    such answers anyway; refusing says so to the model instead of letting it believe it answered."""
    data = json.load(sys.stdin)
    if (data.get("tool_input") or {}).get("answers"):
        print("blocked: a question box carries no answers from the model; ask, and the human answers", file=sys.stderr)
        return 2
    return 0


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"block-coordinate-edits": block_coordinate_edits, "block-self-approval": block_self_approval,
              "require-checkpoint": require_checkpoint, "guard-question": guard_question}[cmd]())


if __name__ == "__main__":
    main()
