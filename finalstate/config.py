"""PROJECT.md: the locked settings and decisions of one campaign.

The file is Markdown for the human with one fenced ```yaml block that holds the Settings record. Every tool that
reads the project calls require_locked() first; the lock is set only at the approve-settings checkpoint.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from .errors import SettingsNotLocked
from .records import Settings

FENCE = re.compile(r"```yaml\n(.*?)\n```", re.S)


def settings_hash(settings: Settings) -> str:
    payload = settings.model_dump(mode="json", exclude={"locked", "approved_by", "approved_at", "protocol_reason"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def read(path: Path) -> Settings:
    text = Path(path).read_text()
    m = FENCE.search(text)
    if not m:
        raise ValueError(f"{path}: no ```yaml block with the settings")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(m.group(1))
    except ImportError:
        data = json.loads(m.group(1))
    return Settings.model_validate(data)


def write(path: Path, settings: Settings, title: str = "PROJECT") -> None:
    body = json.dumps(settings.model_dump(mode="json"), indent=2, ensure_ascii=False)
    text = (f"# {title}\n\nThe locked settings and decisions of this campaign. Edited by calculation_protocol and locked at the "
            f"approve-settings checkpoint; every tool reads it and none changes a locked value.\n\n"
            f"settings hash: `{settings_hash(settings)}`\n\n```yaml\n{body}\n```\n")
    Path(path).write_text(text)


def require_locked(settings: Settings) -> Settings:
    if not settings.locked:
        raise SettingsNotLocked("PROJECT.md is not locked; the approve-settings checkpoint has not been passed")
    return settings


def lock(settings: Settings, approved_by: str) -> Settings:
    from datetime import datetime
    return settings.model_copy(update={"locked": True, "approved_by": approved_by, "approved_at": datetime.now()})


def find_project(start: Optional[Path] = None) -> Path:
    here = Path(start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / "PROJECT.md").exists():
            return p / "PROJECT.md"
    raise FileNotFoundError("no PROJECT.md above the working directory")
