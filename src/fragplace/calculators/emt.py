"""ASE's effective-medium theory potential: Al, Cu, Ag, Au, Ni, Pd, Pt and, for testing only, H, C, N, O.
Not a production potential; the calculator every test runs the pipeline with, since it needs nothing installed
beyond ASE and answers in milliseconds."""
from __future__ import annotations

from . import ASEAdapter, register


@register("emt")
class EMT(ASEAdapter):
    name = "emt"

    def __init__(self, **_):
        try:
            from ase.calculators.emt import EMT as _EMT
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install ase") from e
        self._calc = _EMT()
