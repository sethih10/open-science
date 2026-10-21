"""Placing fragments by script, and minima hopping as the alternative generator. Tools: adsorbate_placement, minima_hopping. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import SiteEnumeration, StructureRef
from ..runtime.journal import traced


@traced(step="3.5", tool="adsorbate_placement")
def adsorbate_placement(sites: SiteEnumeration, fragment: StructureRef, site_index: int, orientation: int, height_A: float, displacement_amplitude_A: float) -> Any:
    """Place fragment A at every symmetry-distinct site near its old site and B at a given site, by script; orientations under the site's stabiliser; a random displacement before relaxation.

    Board steps: 3.5, 4. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        sites: SiteEnumeration
        fragment: StructureRef
        site_index: int
        orientation: int
        height_A: float
        displacement_amplitude_A: float
    Outputs:
        candidate: Candidate
    Checks:
        - start 2 to 3 Å above the site
        - the LLM never places atoms
    Thresholds:
        displacement_amplitude_A: open: team decision
        fragment_A_fixed_at_old_site: open: team decision
    Wraps:
        - ase.build.add_adsorbate
        - fairchem.data.oc.core.AdsorbateSlabConfig as the baseline
    Logs: site, orientation, height, displacement and random draw.
    """
    raise NotImplementedError("adsorbate_placement: see AGENTS.md section 3 and fragplace.registry")


@traced(step="3.6", tool="minima_hopping")
def minima_hopping(slab: StructureRef, fragments: Tuple[StructureRef, StructureRef], calculator: str, n_hops: int) -> Any:
    """NEBscape's endpoint generator with the chosen potential as the alternative generator and the baseline policy our nearest-first choice is scored against.

    Board steps: 3.6. Status: core. Lane: gpu. Allowed roles: solution-planner.

    Inputs:
        slab: StructureRef
        fragments: tuple[StructureRef, StructureRef]
        calculator: str
        n_hops: int
    Outputs:
        candidates: list[Candidate] with generator minima_hopping
    Checks:
        - Hookean constraints keep A and B intact during hopping, as NEBscape
    Thresholds:
        none
    Wraps:
        - nebscape endpoint generator, MIT
        - ase.optimize.minimahopping.MinimaHopping
    Logs: hops; minima found.
    """
    raise NotImplementedError("minima_hopping: see AGENTS.md section 3 and fragplace.registry")
