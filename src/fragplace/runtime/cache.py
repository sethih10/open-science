"""Content-addressed cache for expensive calls: relaxations, force calls, single points.

The key is the hash of the structure, the calculator name and the settings hash, so a changed setting never
returns a stale result. Values are JSON records under runs/<campaign>/cache/.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .journal import _jsonable, content_hash


class Cache:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def key(self, structure_hash: str, calculator: str, settings_hash: str, task: str) -> str:
        return content_hash({"s": structure_hash, "c": calculator, "p": settings_hash, "t": task})

    def get(self, key: str) -> Optional[Any]:
        p = self.dir / f"{key}.json"
        return json.loads(p.read_text()) if p.exists() else None

    def put(self, key: str, value: Any) -> None:
        (self.dir / f"{key}.json").write_text(json.dumps(_jsonable(value), default=str))
