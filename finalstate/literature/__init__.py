"""Literature and database sources behind one interface. Every value returned carries its source and is unverified
until a human marks it at the approve-settings checkpoint. The LLM never cites from memory."""
from __future__ import annotations

from typing import List, Protocol

from ..records import LiteratureValue


class Source(Protocol):
    name: str

    def lookup(self, system: str, quantity: str) -> List[LiteratureValue]: ...


def get(name: str) -> Source:
    if name == "materials_project":
        from .materials_project import MaterialsProject
        return MaterialsProject()
    if name == "catalysis_hub":
        from .catalysis_hub import CatalysisHub
        return CatalysisHub()
    if name == "papers":
        from .papers import Papers
        return Papers()
    raise KeyError(f"unknown source {name}; known: materials_project, catalysis_hub, papers")
