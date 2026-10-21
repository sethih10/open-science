"""CHGNet as a cross-family second opinion on E_ads, and a magnetic-moment check on Ni and Co."""
from __future__ import annotations

from . import register


@register("chgnet")
class CHGNet:
    name = "chgnet"

    def __init__(self):
        try:
            from chgnet.model import CHGNetCalculator
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install chgnet") from e
        self._calc = CHGNetCalculator()

    def energy_forces(self, atoms):
        atoms.calc = self._calc
        return atoms.get_potential_energy(), atoms.get_forces()

    def magnetic_moments(self, atoms):
        atoms.calc = self._calc
        atoms.get_potential_energy()
        return self._calc.results.get("magmoms")

    def relax(self, atoms, fmax: float, steps: int):
        from ase.optimize import BFGS
        atoms.calc = self._calc
        opt = BFGS(atoms, logfile=None)
        converged = opt.run(fmax=fmax, steps=steps)
        return atoms, bool(converged), opt.get_number_of_steps()
