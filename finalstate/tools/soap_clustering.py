"""Tool soap_clustering: board step 6. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import Candidate, Pair, RelaxationResult
from ..provenance import traced


@traced(step="6", tool="soap_clustering")
def soap_clustering(survivors: List[Candidate], energies: List[RelaxationResult], pairs: List[Pair]) -> Any:
    """Cluster the survivors by SOAP; keep the nearest and the lowest per cluster; nearest first overall.

    Board steps: 6. Status: core.

    Inputs:
        survivors: list[Candidate]
        energies: list[RelaxationResult]
        pairs: list[Pair]
    Outputs:
        clusters: list[Cluster]
        kept: list[str]
    Checks:
        - nearest-first ordering preserved across clusters
    Thresholds:
        per_cluster: open: team decision: the board says 3, could be more
    Wraps:
        - dscribe.descriptors.SOAP
        - sklearn.cluster
    Logs: c; l; u; s; t; e; r; s;  ; a; n; d;  ; r; e; p; r; e; s; e; n; t; a; t; i; v; e; s.
    """
    raise NotImplementedError("soap_clustering: see agent.md section 3 and finalstate.registry")
