"""Calculator adapters behind one interface, so a tool never imports a potential's package directly.

Registered names are the ones mlip_selection chooses among. Each adapter is imported lazily, so the package
installs without the potentials; a missing package fails at first use with a clear message. Every adapter wraps
an ASE calculator, so energy_forces, relax and spread are written once here; an adapter only builds its calculator.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

_FACTORIES: Dict[str, Callable[..., "ASEAdapter"]] = {}


class ASEAdapter:
    """One potential behind ASE. Subclasses set `name` and build `self._calc` in __init__."""
    name: str = "ase"
    _calc = None

    def energy_forces(self, atoms) -> Tuple[float, "object"]:
        atoms = atoms.copy()
        atoms.calc = self._calc
        return float(atoms.get_potential_energy()), atoms.get_forces()

    def relax(self, atoms, fmax: float, steps: int, trajectory: Optional[str] = None):
        """BFGS on a copy, constraints respected; returns (atoms, converged, steps, fmax_reached)."""
        import numpy as np
        from ase.optimize import BFGS
        atoms = atoms.copy()
        atoms.calc = self._calc
        opt = BFGS(atoms, logfile=None, trajectory=trajectory)
        converged = bool(opt.run(fmax=fmax, steps=steps))
        forces = atoms.get_forces(apply_constraint=True)
        fmax_reached = float(np.sqrt((forces ** 2).sum(axis=1)).max()) if len(forces) else 0.0
        return atoms, converged, int(opt.get_number_of_steps()), fmax_reached

    def spread(self, atoms) -> float:
        """Committee standard deviation of the energy in eV; 0 for a single model."""
        return 0.0

    def magnetic_moments(self, atoms):
        return None


def register(name: str):
    def deco(factory):
        _FACTORIES[name] = factory
        return factory
    return deco


def _load() -> None:
    from . import chgnet, emt, mace, uma  # noqa: F401  register on import


def get(name: str, **kw) -> ASEAdapter:
    _load()
    if name not in _FACTORIES:
        raise KeyError(f"unknown calculator {name}; known: {sorted(_FACTORIES)}")
    return _FACTORIES[name](**kw)


def available() -> List[str]:
    _load()
    return sorted(_FACTORIES)


class Committee:
    """Several adapters asked the same question; the spread is the standard deviation of their energies.
    Cross-family committees compare E_ads, never total energies: the caller subtracts references per member."""

    def __init__(self, names: List[str], **kw):
        self.names = list(names)
        self.members = [get(n, **kw) for n in self.names]
        self.name = "+".join(self.names)

    def energies(self, atoms) -> List[float]:
        return [m.energy_forces(atoms)[0] for m in self.members]

    def spread(self, atoms) -> float:
        import numpy as np
        if len(self.members) == 1:
            return float(self.members[0].spread(atoms))
        return float(np.std(self.energies(atoms)))
