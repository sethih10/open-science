"""Tool adsorbate_placement: board steps 3.5, 4. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import SiteEnumeration, StructureRef
from ..provenance import traced


@traced(step="3.5", tool="adsorbate_placement")
def adsorbate_placement(sites: SiteEnumeration, fragment: StructureRef, site_index: int, orientation: int, height_A: float, displacement_amplitude_A: float) -> Any:
    """Place fragment A at every symmetry-distinct site near its old site and B at a given site, by script; orientations under the site's stabiliser; a random displacement before relaxation.

    Board steps: 3.5, 4. Status: core.

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
    Logs: s; i; t; e; ,;  ; o; r; i; e; n; t; a; t; i; o; n; ,;  ; h; e; i; g; h; t; ,;  ; d; i; s; p; l; a; c; e; m; e; n; t;  ; a; n; d;  ; r; a; n; d; o; m;  ; d; r; a; w.
    """
    raise NotImplementedError("adsorbate_placement: see agent.md section 3 and finalstate.registry")
