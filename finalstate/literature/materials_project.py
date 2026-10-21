"""Materials Project through its API, the LLaMP pattern: numbers come from the database, never from the model."""
from __future__ import annotations

from typing import List

from ..records import LiteratureValue


class MaterialsProject:
    name = "materials_project"

    def lookup(self, system: str, quantity: str) -> List[LiteratureValue]:
        try:
            from mp_api.client import MPRester  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install mp-api; set MP_API_KEY") from e
        raise NotImplementedError("query bulk and surface data for the system; return LiteratureValue records with the material id as source")
