"""The five human checkpoints. The planner stops at each and waits; the hook enforces it.

A checkpoint is passed when a HumanChoice for it exists in runs/<campaign>/checkpoints.json. The choice and its
reason also go to the case bank. Names are the ones in agent.md section 3 and the figures' data module.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..errors import CheckpointPending
from ..schemas.records import HumanChoice

CHECKPOINTS = ("approve settings", "approve the plan", "review flagged cases", "pick up to five final states", "interpret results")

# which board step each checkpoint sits after; the "approve the plan" placement is the team's to confirm
AFTER_STEP = {"approve settings": "1", "approve the plan": "1*", "review flagged cases": "7",
              "pick up to five final states": "8", "interpret results": "solution"}


def _path(run_dir: Path) -> Path:
    return Path(run_dir) / "checkpoints.json"


def passed(run_dir: Path) -> List[HumanChoice]:
    p = _path(run_dir)
    if not p.exists():
        return []
    return [HumanChoice.model_validate(x) for x in json.loads(p.read_text())]


def require(run_dir: Path, name: str) -> HumanChoice:
    if name not in CHECKPOINTS:
        raise ValueError(f"unknown checkpoint {name}")
    for c in passed(run_dir):
        if c.checkpoint == name:
            return c
    raise CheckpointPending(name)


def record(run_dir: Path, choice: HumanChoice) -> None:
    if choice.checkpoint not in CHECKPOINTS:
        raise ValueError(f"unknown checkpoint {choice.checkpoint}")
    items = [c.model_dump(mode="json") for c in passed(run_dir)] + [choice.model_dump(mode="json")]
    _path(run_dir).write_text(json.dumps(items, indent=1, default=str))
