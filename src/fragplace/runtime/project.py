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

from ..errors import OpenDecision, SettingsNotLocked
from ..registry.tools import open_decisions
from ..schemas.records import Settings

FENCE = re.compile(r"```yaml\n(.*?)\n```", re.S)
HASH_LINE = re.compile(r"^settings hash: `[^`]*`$", re.M)


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
    """Write the settings into the ```yaml block; an existing file keeps every line outside the block, so the
    interview answers and the decisions table survive."""
    body = json.dumps(settings.model_dump(mode="json"), indent=2, ensure_ascii=False)
    block = f"```yaml\n{body}\n```"
    old = Path(path).read_text() if Path(path).exists() else ""
    if FENCE.search(old):
        text = FENCE.sub(lambda _: block, old, count=1)
        text = HASH_LINE.sub(f"settings hash: `{settings_hash(settings)}`", text, count=1)
    else:
        text = (f"# {title}\n\nThe locked settings and decisions of this campaign. Edited by calculation_protocol and locked at the "
                f"approve-settings checkpoint; every tool reads it and none changes a locked value.\n\n"
                f"settings hash: `{settings_hash(settings)}`\n\n{block}\n")
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


def current_settings(require_lock: bool = True) -> Settings:
    """The settings of the current run: runs/<campaign>/PROJECT.md when a Run is set, else the nearest PROJECT.md."""
    from .journal import current_run
    run = current_run()
    path = run.dir / "PROJECT.md" if run and (run.dir / "PROJECT.md").exists() else find_project()
    s = read(path)
    return require_locked(s) if require_lock else s


def decision(tool: str, name: str, settings: Optional[Settings] = None):
    """A threshold marked 'open: team decision'. It is never guessed: the team writes it into PROJECT.md under
    decisions as <tool>.<name>, and a tool that needs one that is missing or null stops with OpenDecision."""
    s = settings or current_settings()
    key = f"{tool}.{name}"
    if s.decisions.get(key) is None:
        raise OpenDecision(f"{key} is open: team decision; set decisions.{key} in PROJECT.md")
    return s.decisions[key]


def missing_decisions(settings: Settings) -> list:
    """Every open threshold of the registry that PROJECT.md does not set yet."""
    return [k for k in open_decisions() if settings.decisions.get(k) is None]
