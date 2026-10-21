"""Tool site_enumeration: board step 2. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import StructureRef
from ..provenance import traced


@traced(step="2", tool="site_enumeration")
def site_enumeration(slab: StructureRef, cell_repeat: Tuple[int, int]) -> Any:
    """Every symmetry-inequivalent site of the slab, fcc and hcp hollows apart, with the site graph and a Burnside-checked count; pymatgen's finder as the baseline.

    Board steps: 2. Status: core.

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
    raise NotImplementedError("site_enumeration: see agent.md section 3 and finalstate.registry")
