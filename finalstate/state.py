"""Resumable run state: which board step the campaign is at, which are done, which checkpoint is pending.

runs/<campaign>/state.json. A run that stops, at a checkpoint, on an escalation or on a crash, resumes from here;
nothing is recomputed that the cache and the trace already hold. The pattern is TSAgent's runtime state file.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from .errors import CheckpointPending

STEP_ORDER = ["prompt", "1", "1*", "2", "3.5", "3.2", "3.3", "3.4", "3.6", "4", "5", "6", "7", "8", "solution"]


class RunState(BaseModel):
    campaign: str
    current_step: str = "prompt"
    completed_steps: List[str] = Field(default_factory=list)
    pending_checkpoint: Optional[str] = None
    escalation: Optional[str] = None
    updated: datetime = Field(default_factory=datetime.now)


def path(run_dir: Path) -> Path:
    return Path(run_dir) / "state.json"


def load(run_dir: Path, campaign: str) -> RunState:
    p = path(run_dir)
    return RunState.model_validate_json(p.read_text()) if p.exists() else RunState(campaign=campaign)


def save(run_dir: Path, state: RunState) -> None:
    state.updated = datetime.now()
    path(run_dir).write_text(state.model_dump_json(indent=1))


def complete(run_dir: Path, state: RunState, step: str, next_checkpoint: Optional[str] = None) -> RunState:
    if step not in STEP_ORDER:
        raise ValueError(f"unknown step {step}")
    if step not in state.completed_steps:
        state.completed_steps.append(step)
    i = STEP_ORDER.index(step)
    state.current_step = STEP_ORDER[i + 1] if i + 1 < len(STEP_ORDER) else "done"
    state.pending_checkpoint = next_checkpoint
    save(run_dir, state)
    return state


def resume(run_dir: Path, campaign: str) -> RunState:
    state = load(run_dir, campaign)
    if state.pending_checkpoint:
        from .checkpoints import passed
        if state.pending_checkpoint not in {c.checkpoint for c in passed(run_dir)}:
            raise CheckpointPending(state.pending_checkpoint)
        state.pending_checkpoint = None
        save(run_dir, state)
    return state
