"""CHGNet as a cross-family second opinion on E_ads, and a magnetic-moment check on Ni and Co."""
from __future__ import annotations

from . import ASEAdapter, register


@register("chgnet")
class CHGNet(ASEAdapter):
    name = "chgnet"

    def __init__(self, name: str = "chgnet", **_):
        try:
            from chgnet.model import CHGNetCalculator
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install chgnet") from e
        self._calc = CHGNetCalculator()

    def magnetic_moments(self, atoms):
        atoms = atoms.copy()
        atoms.calc = self._calc
        atoms.get_potential_energy()
        return self._calc.results.get("magmoms")
