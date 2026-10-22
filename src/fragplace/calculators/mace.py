"""MACE: a foundation model by name, or a single model or a committee from files. mace-mp-small, -medium and -large
are the MACE-MP-0 models, downloaded on first use; mace and mace-committee read FRAGPLACE_MACE_MODELS, model files
separated by colons, and several files return energy_var and forces_var."""
from __future__ import annotations

import os
from typing import List, Optional

from . import ASEAdapter, device, register


@register("mace")
@register("mace-committee")
@register("mace-mp-small")
@register("mace-mp-medium")
@register("mace-mp-large")
class MACE(ASEAdapter):
    name = "mace"

    def __init__(self, name: str = "mace", model_paths: Optional[List[str]] = None, device_name: Optional[str] = None, **_):
        try:
            from mace.calculators import MACECalculator, mace_mp
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install mace-torch") from e
        self.name = name
        dev = device_name or device()
        if name.startswith("mace-mp-"):
            self.model_paths = []
            self._calc = mace_mp(model=name.rsplit("-", 1)[1], device=dev, default_dtype="float64")
            return
        self.model_paths = model_paths or [p for p in os.environ.get("FRAGPLACE_MACE_MODELS", "").split(":") if p]
        if not self.model_paths:
            raise ValueError(f"{name} needs model files: set FRAGPLACE_MACE_MODELS, or use mace-mp-small, -medium or -large")
        self._calc = MACECalculator(model_paths=self.model_paths, device=dev, default_dtype="float64")

    def spread(self, atoms) -> Optional[float]:
        """The committee's spread when several model files were given; None for one model."""
        atoms = atoms.copy()
        atoms.calc = self._calc
        atoms.get_potential_energy()
        var = self._calc.results.get("energy_var")
        return float(var) ** 0.5 if var is not None else None
