"""MACE, single model or a committee: several files in model_paths return energy_var and forces_var."""
from __future__ import annotations

from typing import List, Optional

from . import ASEAdapter, register


@register("mace")
@register("mace-committee")
class MACE(ASEAdapter):
    name = "mace"

    def __init__(self, model_paths: Optional[List[str]] = None, device: str = "cuda", **_):
        try:
            from mace.calculators import MACECalculator
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install mace-torch") from e
        self.model_paths = model_paths or []
        self._calc = MACECalculator(model_paths=self.model_paths or None, device=device, default_dtype="float32")

    def spread(self, atoms) -> float:
        atoms = atoms.copy()
        atoms.calc = self._calc
        atoms.get_potential_energy()
        return float(self._calc.results.get("energy_var", 0.0)) ** 0.5
