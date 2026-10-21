"""Tool pair_enumeration: board step 3.2. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import SiteEnumeration
from ..provenance import traced


@traced(step="3.2", tool="pair_enumeration")
def pair_enumeration(sites: SiteEnumeration, d_bond_A: float, window: Tuple[float, float]) -> Any:
    """Every symmetry-distinct (A site, B site) pair inside the window [1.5 d, 5] Å, ordered by site-graph distance with in-plane distance as tiebreaker, nearest first, counted.

    Board steps: 3.2. Status: core.

    Inputs:
        sites: SiteEnumeration
        d_bond_A: float, from literature_lookup or the adsorbate structure
        window: tuple[float, float] in units of d and Å
    Outputs:
        pairs: list[Pair], nearest first
        count: int
    Checks:
        - no pair outside the window
        - symmetry duplicates removed and counted
    Thresholds:
        d_definition: open: team decision: vacuum or adsorbed bond length
        upper_bound_A: open: team decision: 5 or NEBscape's 4.5
    Wraps:
        - acat.adsorption_sites.SlabAdsorptionSites.get_neighbor_site_list
        - acat.build.adlayer.SystematicPatternGenerator
    Logs: every pair with both distances; the count.
    """
    raise NotImplementedError("pair_enumeration: see agent.md section 3 and finalstate.registry")
