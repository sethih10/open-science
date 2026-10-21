"""The five human checkpoints. The planner stops at each and waits; the hook enforces it.

A checkpoint is passed when a HumanChoice for it exists in runs/<campaign>/checkpoints.json. The choice and its
reason also go to the case bank. Names are defined once in registry.agents; agent.pipeline says which step each sits after.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..errors import CheckpointPending
from ..schemas.records import HumanChoice

from ..registry.agents import CHECKPOINTS  # noqa: E402  defined once, in the registry; agent.pipeline says which step each sits after


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
