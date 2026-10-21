"""Tool literature_lookup: board steps prompt, 3.2. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..provenance import traced


@traced(step="prompt", tool="literature_lookup")
def literature_lookup(system: str, quantity: Any, sources: Any) -> Any:
    """Published E_ads values with functional and site, and the length d of the bond to break, for a human to verify; one or two values, never from the model's memory.

    Board steps: prompt, 3.2. Status: core.

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
    raise NotImplementedError("literature_lookup: see agent.md section 3 and finalstate.registry")
