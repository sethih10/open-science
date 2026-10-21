"""Catalysis-Hub: published adsorption and reaction energies with functional and site."""
from __future__ import annotations

from typing import List

from ..records import LiteratureValue


class CatalysisHub:
    name = "catalysis_hub"

    def lookup(self, system: str, quantity: str) -> List[LiteratureValue]:
        raise NotImplementedError("GraphQL query to api.catalysis-hub.org; return E_ads with functional, site and the publication DOI as source")
