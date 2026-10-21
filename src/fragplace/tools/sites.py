"""Symmetry-inequivalent sites and the A–B pairs inside the window. Tools: site_enumeration, pair_enumeration. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import SiteEnumeration, StructureRef
from ..runtime.journal import traced


@traced(step="2", tool="site_enumeration")
def site_enumeration(slab: StructureRef, cell_repeat: Tuple[int, int]) -> Any:
    """Every symmetry-inequivalent site of the slab, fcc and hcp hollows apart, with the site graph and a Burnside-checked count; pymatgen's finder as the baseline.

    Board steps: 2. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        slab: StructureRef
        cell_repeat: tuple[int, int]
    Outputs:
        sites: SiteEnumeration
    Checks:
        - Burnside count equals the explicit list
        - C4v square cell with two identical adsorbates gives 2
    Thresholds:
        none
    Wraps:
        - spglib.get_symmetry_dataset
        - acat.adsorption_sites.SlabAdsorptionSites
        - acat.adsorption_sites.SlabAdsorptionSites.get_graph
        - pymatgen.core.adsorption.AdsorbateSiteFinder as baseline
    Logs: symmetry group; every site; count and check.
    """
    raise NotImplementedError("site_enumeration: see AGENTS.md section 3 and fragplace.registry")


@traced(step="3.2", tool="pair_enumeration")
def pair_enumeration(sites: SiteEnumeration, d_bond_A: float, window: Tuple[float, float]) -> Any:
    """Every symmetry-distinct (A site, B site) pair inside the window [1.5 d, 5] Å, ordered by site-graph distance with in-plane distance as tiebreaker, nearest first, counted.

    Board steps: 3.2. Status: core. Lane: laptop. Allowed roles: solution-planner.

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
    raise NotImplementedError("pair_enumeration: see AGENTS.md section 3 and fragplace.registry")
