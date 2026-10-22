"""ASE's effective-medium theory potential: Al, Cu, Ag, Au, Ni, Pd, Pt and, for testing only, H, C, N, O.
Not a production potential; the calculator every test runs the pipeline with, since it needs nothing installed
beyond ASE and answers in milliseconds. Its elements are the keys of ASE's parameter table, so atoms of any other
element are refused before EMT sees them."""
from __future__ import annotations

from . import ASEAdapter, register


@register("emt")
class EMT(ASEAdapter):
    name = "emt"

    def __init__(self, name: str = "emt", **_):
        try:
            from ase.calculators.emt import EMT as _EMT
            from ase.calculators.emt import parameters
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install ase") from e
        self.elements = frozenset(parameters)
        self._calc = _EMT()
