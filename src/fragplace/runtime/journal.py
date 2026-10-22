"""The decision trace and the run directory.

runs/<study>/
  PROJECT.md      a copy of the locked settings at the start of the run
  trace.jsonl     one TraceEvent per tool call, human choice and escalation
  cards/          descriptor cards, text and PNG
  structures/     every structure a tool wrote, never edited by hand or by the LLM
  cache/          content-addressed results of expensive calls
  report.md       the report, with report.json beside it

The @traced decorator wraps a tool function: it hashes the inputs, runs the tool, stores the outputs as JSON under
structures/ or cache/, and appends the event. A tool that raises still leaves an event with the error message.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel

from ..schemas.records import TraceEvent


def _jsonable(x: Any) -> Any:
    if isinstance(x, BaseModel):
        return x.model_dump(mode="json")
    if isinstance(x, (list, tuple)):
        return [_jsonable(i) for i in x]
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, Path):
        return str(x)
    return x


def content_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(_jsonable(obj), sort_keys=True, default=str).encode()).hexdigest()[:16]


class Run:
    """The run directory of one study."""

    def __init__(self, root: Path, study: str):
        self.dir = Path(root) / "runs" / study
        for sub in ("cards", "structures", "cache"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        self.trace_path = self.dir / "trace.jsonl"
        self.study = study
        self.step: Optional[str] = None      # the pipeline step running now; a tool's own board step when None

    def event(self, step: str, tool: str, actor: str, inputs: Any, outputs_ref: str, message: str = "") -> TraceEvent:
        ev = TraceEvent(step=step, tool=tool, actor=actor, inputs_hash=content_hash(inputs), outputs_ref=outputs_ref, message=message)
        with self.trace_path.open("a") as f:
            f.write(ev.model_dump_json() + "\n")
        return ev

    def store(self, name: str, obj: Any, sub: str = "structures") -> str:
        path = self.dir / sub / f"{name}.json"
        path.write_text(json.dumps(_jsonable(obj), indent=1, ensure_ascii=False, default=str))
        return str(path.relative_to(self.dir))

    def events(self):
        if not self.trace_path.exists():
            return []
        return [TraceEvent.model_validate_json(line) for line in self.trace_path.read_text().splitlines() if line.strip()]


REPOSITORY = Path(__file__).resolve().parents[3]


def default_root() -> Path:
    """The directory that holds runs/: FRAGPLACE_ROOT, else the repository. The MCP server and the hooks both read it,
    so the gate a hook checks is the one the server keeps."""
    return Path(os.environ.get("FRAGPLACE_ROOT") or REPOSITORY)


_CURRENT: Optional[Run] = None


def set_run(run: Run) -> None:
    global _CURRENT
    _CURRENT = run


def current_run() -> Optional[Run]:
    return _CURRENT


def log(tool: str, message: str) -> None:
    """One line in the trace beside a tool's call: what it measured or chose, and why; under the pipeline step running
    now, else the tool's first board step. A no-op outside a run."""
    run = current_run()
    if run:
        from ..registry.tools import BY_NAME
        run.event(run.step or BY_NAME[tool].board_steps[0], tool, "tool", {}, "", message=message)


def traced(step: str, tool: str, actor: str = "tool") -> Callable:
    """Decorate a tool function so every call lands in the trace."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            run = current_run()
            inputs = {"args": args, "kwargs": kwargs}
            key = run.step if run and run.step else step
            try:
                out = fn(*args, **kwargs)
            except Exception as e:  # noqa: BLE001 - the trace must record every failure
                if run:
                    run.event(key, tool, actor, inputs, "", message=f"error: {type(e).__name__}: {e}")
                raise
            if run:
                ref = run.store(f"{tool}-{content_hash(inputs)}", out)
                run.event(key, tool, actor, inputs, ref)
            return out
        return wrapper
    return deco
