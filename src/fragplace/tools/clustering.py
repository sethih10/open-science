"""SOAP clustering and the ranking the human picks from. Tools: soap_clustering, ranking. Defined in fragplace.registry."""
from __future__ import annotations

from typing import Any, List, Tuple
from ..schemas.records import Candidate, DescriptorCard, DoubtFlag, Pair, RelaxationResult
from ..runtime.journal import traced


@traced(step="6", tool="soap_clustering")
def soap_clustering(survivors: List[Candidate], energies: List[RelaxationResult], pairs: List[Pair]) -> Any:
    """Cluster the survivors by SOAP; keep the nearest and the lowest per cluster; nearest first overall.

    Board steps: 6. Status: core. Lane: laptop. Allowed roles: solution-planner.

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
    Logs: clusters and representatives.
    """
    raise NotImplementedError("soap_clustering: see AGENTS.md section 3 and fragplace.registry")


@traced(step="8", tool="ranking")
def ranking(kept: list, cards: List[DescriptorCard], flags: List[DoubtFlag], pairs: List[Pair]) -> Any:
    """Rank the kept final states nearest first, then by energy, with doubt and verdicts on each card, for the human to pick up to five; record the choice and reason in the case bank.

    Board steps: 8. Status: core. Lane: laptop. Allowed roles: solution-planner.

    Inputs:
        kept: list[str]
        cards: list[DescriptorCard]
        flags: list[DoubtFlag]
        pairs: list[Pair]
    Outputs:
        ranked: list[RankedCandidate]
    Checks:
        - the human picks; the tool never drops a candidate
    Thresholds:
        shortlist_size: open: team decision: up to five, or fewer
    Wraps:
        - none
    Logs: the order shown; the human's choice and reason, to lessons.md.
    """
    raise NotImplementedError("ranking: see AGENTS.md section 3 and fragplace.registry")
