"""PROJECT.md: the locked settings and decisions of one study.

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
from ..registry.tools import asked_decisions, runs_dft
from ..schemas.records import Settings

FENCE = re.compile(r"```yaml\n(.*?)\n```", re.S)
HASH_LINE = re.compile(r"^settings hash: `[^`]*`$", re.M)


def settings_hash(settings: Settings) -> str:
    payload = settings.model_dump(mode="json", exclude={"locked", "approved_by", "approved_at", "protocol_reason", "origins"})
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
        text = (f"# {title}\n\nThe locked settings and decisions of this study. Edited by calculation_protocol and locked at the "
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
    """The settings of the current run: runs/<study>/PROJECT.md when a Run is set, else the nearest PROJECT.md."""
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


GAS_FILE = "gas_references.json"     # the potential's gas references of a study without DFT, beside PROJECT.md


def write_potential_gas(run_dir: Path, refs: list) -> None:
    """The gas references the potential chosen at 1* computed, for a study that runs no DFT. They sit beside the
    lock, never in it: the lock holds the species, and an energy computed after it changes no locked value."""
    Path(run_dir, GAS_FILE).write_text(json.dumps([g.model_dump(mode="json") for g in refs], indent=1, ensure_ascii=False))


def gas_references(settings: Settings) -> list:
    """The gas references every reader uses: the lock's in a study that runs DFT; else the potential's, computed after
    1*, and none before. Energies the supplied files carry are never among them, so two scales never mix."""
    from ..schemas.records import GasReference
    if runs_dft(settings.protocol):
        return list(settings.gas_references)
    from .journal import current_run
    run = current_run()
    path = Path(run.dir, GAS_FILE) if run else None
    if path is None or not path.exists():
        return []
    return [GasReference.model_validate(g) for g in json.loads(path.read_text())]


def missing_decisions(settings: Settings, dft: Optional[bool] = None) -> list:
    """Every open threshold of the registry that PROJECT.md does not set yet and the study needs: a study that runs
    no DFT, the default until its lock names a DFT protocol, is never asked a DFT-only one."""
    needed = asked_decisions(runs_dft(settings.protocol) if dft is None else dft)
    return [k for k in needed if settings.decisions.get(k) is None]
