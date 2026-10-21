"""Tool descriptor_card: board steps 3.4, 5, 8. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import Candidate, GateResult, SiteEnumeration
from ..provenance import traced


@traced(step="3.4", tool="descriptor_card")
def descriptor_card(candidate: Candidate, gate: GateResult, sites: SiteEnumeration) -> Any:
    """Render a structure as the text card the LLM reads, with site, distances, verdicts and the A–B distance; a PNG beside it as a second look.

    Board steps: 3.4, 5, 8. Status: core.

    Inputs:
        candidate: Candidate
        gate: GateResult | None
        sites: SiteEnumeration
    Outputs:
        card: DescriptorCard
    Checks:
        - two configurations never share a card: distances and site labels always present
    Thresholds:
        none
    Wraps:
        - pymatgen
        - robocrystallographer pattern
        - ase.io.write png
    Logs: t; h; e;  ; c; a; r; d;  ; b; e; s; i; d; e;  ; t; h; e;  ; s; t; r; u; c; t; u; r; e.
    """
    raise NotImplementedError("descriptor_card: see agent.md section 3 and finalstate.registry")
