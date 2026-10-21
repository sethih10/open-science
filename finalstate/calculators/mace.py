"""MACE, single model or a committee: several files in model_paths return energy_var and forces_var."""
from __future__ import annotations

from typing import List, Optional

from . import register


@register("mace")
@register("mace-committee")
class MACE:
    name = "mace"

    def __init__(self, model_paths: Optional[List[str]] = None, device: str = "cuda"):
        try:
            from mace.calculators import MACECalculator
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install mace-torch") from e
        self.model_paths = model_paths or []
        self._calc = MACECalculator(model_paths=self.model_paths or None, device=device, default_dtype="float32")

    def energy_forces(self, atoms):
        atoms.calc = self._calc
        return atoms.get_potential_energy(), atoms.get_forces()

    def spread(self, atoms) -> float:
        """Committee variance of the energy, in eV; 0 for a single model."""
        atoms.calc = self._calc
        atoms.get_potential_energy()
        return float(self._calc.results.get("energy_var", 0.0)) ** 0.5

    def relax(self, atoms, fmax: float, steps: int):
        from ase.optimize import BFGS
        atoms.calc = self._calc
        opt = BFGS(atoms, logfile=None)
        converged = opt.run(fmax=fmax, steps=steps)
        return atoms, bool(converged), opt.get_number_of_steps()
