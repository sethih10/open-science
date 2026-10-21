"""Published values with their sources; the literature-reader's tools and the source adapters behind them. Tools: literature_lookup. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..runtime.journal import traced


@traced(step="prompt", tool="literature_lookup")
def literature_lookup(system: str, quantity: Any, sources: Any) -> Any:
    """Published E_ads values with functional and site, and the length d of the bond to break, for a human to verify; one or two values, never from the model's memory.

    Board steps: prompt, 3.2. Status: core. Lane: laptop. Allowed roles: literature-reader.

    Inputs:
        system: str, metal, facet, adsorbate
        quantity: E_ads | bond_length_d | site
        sources: list of source names
    Outputs:
        values: list[LiteratureValue], verified_by_human False until the checkpoint
    Checks:
        - every value carries a DOI or URL
        - at most two values per quantity
    Thresholds:
        none
    Wraps:
        - paper-qa2 for papers
        - Materials Project API through the LLaMP pattern
        - Catalysis-Hub
    Logs: query; every value with its source.
    """
    raise NotImplementedError("literature_lookup: see AGENTS.md section 3 and fragplace.registry")


# ---- source adapters, each returning LiteratureValue records with a DOI or URL; the LLM never cites from memory
class MaterialsProject:
    name = "materials_project"

    def lookup(self, system: str, quantity: str):
        try:
            from mp_api.client import MPRester  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install mp-api; set MP_API_KEY") from e
        raise NotImplementedError("query bulk and surface data; return LiteratureValue records with the material id as source")


class CatalysisHub:
    name = "catalysis_hub"

    def lookup(self, system: str, quantity: str):
        raise NotImplementedError("GraphQL query to api.catalysis-hub.org; return E_ads with functional, site and the DOI as source")


class Papers:
    name = "papers"

    def lookup(self, system: str, quantity: str):
        try:
            import paperqa  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install paper-qa") from e
        raise NotImplementedError("ask for the quantity with the system; one LiteratureValue per citation")


SOURCES = {"materials_project": MaterialsProject, "catalysis_hub": CatalysisHub, "papers": Papers}
