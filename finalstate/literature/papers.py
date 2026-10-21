"""Papers through paper-qa, FutureHouse's retrieval-and-answer library: an answer with citations, never a bare number."""
from __future__ import annotations

from typing import List

from ..records import LiteratureValue


class Papers:
    name = "papers"

    def lookup(self, system: str, quantity: str) -> List[LiteratureValue]:
        try:
            import paperqa  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install paper-qa") from e
        raise NotImplementedError("ask for the quantity with the system; parse the cited values; return one LiteratureValue per citation")
