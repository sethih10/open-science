"""Tool ranking: board step 8. Defined in finalstate.registry; implemented here."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple
from ..records import DescriptorCard, DoubtFlag, Pair
from ..provenance import traced


@traced(step="8", tool="ranking")
def ranking(kept: list, cards: List[DescriptorCard], flags: List[DoubtFlag], pairs: List[Pair]) -> Any:
    """Rank the kept final states nearest first, then by energy, with doubt and verdicts on each card, for the human to pick up to five; record the choice and reason in the case bank.

    Board steps: 8. Status: core.

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
    raise NotImplementedError("ranking: see agent.md section 3 and finalstate.registry")
