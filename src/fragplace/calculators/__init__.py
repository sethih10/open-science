"""Calculator adapters behind one interface, so a tool never imports a potential's package directly.

Registered names are the ones mlip_selection chooses among. Each adapter is imported lazily, so the package
installs without the potentials; a missing package fails at first use with a clear message. Every adapter wraps
an ASE calculator, so energy_forces, relax and spread are written once here; an adapter only builds its calculator.
An adapter that knows its elements refuses atoms of any other before calculating, with UnsupportedElements.
"""
from __future__ import annotations

from typing import Callable, Dict, FrozenSet, Iterable, List, Optional, Tuple

_FACTORIES: Dict[str, Callable[..., "ASEAdapter"]] = {}
_LOADED: Dict[str, "ASEAdapter"] = {}     # a potential loads its weights once per process; only an adapter that built its calculator


class UnsupportedElements(ValueError):
    """A potential was asked about elements it has no parameters for."""


class ASEAdapter:
    """One potential behind ASE. Subclasses set `name` and build `self._calc` in __init__, and `elements` when the
    potential covers only some elements."""
    name: str = "ase"
    _calc = None
    elements: Optional[FrozenSet[str]] = None   # the elements the potential has parameters for; None for every element
    spin: bool = False                          # whether the potential takes a spin state; no adapter here does

    def unsupported(self, symbols: Iterable[str]) -> List[str]:
        """The elements among symbols the potential has no parameters for."""
        return [] if self.elements is None else sorted(set(symbols) - self.elements)

    def check(self, atoms) -> None:
        missing = self.unsupported(atoms.get_chemical_symbols())
        if missing:
            raise UnsupportedElements(f"{self.name} has no parameters for {', '.join(missing)}")

    def energy_forces(self, atoms) -> Tuple[float, "object"]:
        self.check(atoms)
        atoms = atoms.copy()
        atoms.calc = self._calc
        return float(atoms.get_potential_energy()), atoms.get_forces()

    def relax(self, atoms, fmax: float, steps: int, trajectory: Optional[str] = None):
        """BFGS on a copy, constraints respected; returns (atoms, converged, steps, fmax_reached)."""
        import numpy as np
        from ase.optimize import BFGS
        self.check(atoms)
        atoms = atoms.copy()
        atoms.calc = self._calc
        opt = BFGS(atoms, logfile=None, trajectory=trajectory)
        converged = bool(opt.run(fmax=fmax, steps=steps))
        forces = atoms.get_forces(apply_constraint=True)
        fmax_reached = float(np.sqrt((forces ** 2).sum(axis=1)).max()) if len(forces) else 0.0
        return atoms, converged, int(opt.get_number_of_steps()), fmax_reached

    def spread(self, atoms) -> Optional[float]:
        """Committee standard deviation of the energy in eV; None for a single model, which measures no spread."""
        return None

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
    """The adapter of a registered potential, built once per process. A factory that raises, or that builds no
    calculator, leaves nothing cached, so the next call tries again."""
    _load()
    if name not in _FACTORIES:
        raise KeyError(f"unknown calculator {name}; known: {sorted(_FACTORIES)}")
    key = f"{name} {sorted(kw.items())!r}"
    if key not in _LOADED:
        adapter = _FACTORIES[name](name=name, **kw)
        if adapter._calc is None:
            raise RuntimeError(f"{name} built no calculator")
        _LOADED[key] = adapter
    return _LOADED[key]


def device() -> str:
    """cuda when torch sees a GPU, else cpu."""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


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

    def spread(self, atoms) -> Optional[float]:
        import numpy as np
        if len(self.members) == 1:
            return self.members[0].spread(atoms)
        return float(np.std(self.energies(atoms)))
