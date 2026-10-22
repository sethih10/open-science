"""MACE: a foundation model by name, or a single model or a committee from files. Each name of FOUNDATION is a
model of mace-torch's mace_mp, downloaded into ~/.cache/mace on first use; mace and mace-committee read
FRAGPLACE_MACE_MODELS, model files separated by colons, and several files return energy_var and forces_var.

The licence is the model's, as mace-torch's README lists it: MIT for the MP-0 and MPA-0 models; the Academic
Software License for OMAT-0 and MATPES-PBE-0, which forbids commercial use. Only PBE and PBE+U models are named,
so a committee of them disagrees about the potential, not about the functional."""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from . import ASEAdapter, device, register

FOUNDATION: Dict[str, Tuple[str, str]] = {   # our name: (mace_mp's model key, licence)
    "mace-mp-small": ("small", "MIT"),            # MACE-MP-0, trained on MPtrj
    "mace-mp-medium": ("medium", "MIT"),
    "mace-mp-large": ("large", "MIT"),
    "mace-mp-0b3": ("medium-0b3", "MIT"),         # MPtrj, with better high-pressure stability and reference energies
    "mace-mpa-0": ("medium-mpa-0", "MIT"),        # MPtrj and sAlex
    "mace-omat-0-small": ("small-omat-0", "ASL"),  # OMat24
    "mace-omat-0": ("medium-omat-0", "ASL"),
    "mace-matpes-pbe-0": ("mace-matpes-pbe-0", "ASL"),   # MATPES-PBE, without +U
}


class MACE(ASEAdapter):
    name = "mace"
    licence: Optional[str] = None

    def __init__(self, name: str = "mace", model_paths: Optional[List[str]] = None, device_name: Optional[str] = None, **_):
        try:
            from mace.calculators import MACECalculator, mace_mp
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install mace-torch") from e
        self.name = name
        dev = device_name or device()
        if name in FOUNDATION:
            model, self.licence = FOUNDATION[name]
            self.model_paths = []
            self._calc = mace_mp(model=model, device=dev, default_dtype="float64")
            return
        self.model_paths = model_paths or [p for p in os.environ.get("FRAGPLACE_MACE_MODELS", "").split(":") if p]
        if not self.model_paths:
            raise ValueError(f"{name} needs model files: set FRAGPLACE_MACE_MODELS, or name a foundation model: {', '.join(FOUNDATION)}")
        self._calc = MACECalculator(model_paths=self.model_paths, device=dev, default_dtype="float64")

    def spread(self, atoms) -> Optional[float]:
        """The committee's spread when several model files were given; None for one model."""
        self.check(atoms)
        atoms = atoms.copy()
        atoms.calc = self._calc
        atoms.get_potential_energy()
        var = self._calc.results.get("energy_var")
        return float(var) ** 0.5 if var is not None else None


for _name in ("mace", "mace-committee", *FOUNDATION):
    register(_name)(MACE)
