"""The case bank, lessons.md: raw cases, not distilled lessons.

Each entry keeps the descriptor card as the planner saw it, the correction and the reason. The planner retrieves
cases by system and failure; only a human sets promoted_to. The format is one Markdown section per case with a
fenced ```json block, so a human can read it and a tool can parse it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

from .records import Case

BLOCK = re.compile(r"```json\n(.*?)\n```", re.S)


class CaseBank:
    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.exists():
            self.path.write_text("# Case bank\n\nRaw cases: what was seen, what was done, why. A human promotes a case to a skill line, a check or a prior.\n")

    def add(self, case: Case) -> None:
        with self.path.open("a") as f:
            f.write(f"\n## {case.system}: {case.correction}\n\n```json\n{case.model_dump_json(indent=1)}\n```\n")

    def all(self) -> List[Case]:
        return [Case.model_validate_json(m.group(1)) for m in BLOCK.finditer(self.path.read_text())]

    def retrieve(self, system: Optional[str] = None, failure: Optional[str] = None) -> List[Case]:
        out = self.all()
        if system:
            out = [c for c in out if system.lower() in c.system.lower()]
        if failure:
            out = [c for c in out if failure.lower() in (c.correction + " " + c.reason + " " + c.card).lower()]
        return out


SEED = [
    Case(system="CO on Pt-group metals", card="", correction="compare the top and hollow sites against experiment, not DFT alone",
         reason="GGA functionals put CO at the hollow site; experiment finds top", source_checkpoint="seed"),
    Case(system="Ni(111), Co(0001)", card="", correction="set initial magnetic moments and keep spin polarisation on",
         reason="or the SCF fails or the moment collapses", source_checkpoint="seed"),
    Case(system="any high-symmetry site", card="", correction="displace the adsorbate randomly before relaxing",
         reason="a symmetric start relaxes to a saddle, the symmetry trap", source_checkpoint="seed"),
]
