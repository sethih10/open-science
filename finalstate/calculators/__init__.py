"""Calculator adapters behind one interface, so a tool never imports a potential's package directly.

Registered names are the ones mlip_selection chooses among. Each adapter is imported lazily, so the package
installs without the potentials; a missing package fails at first use with a clear message.
"""
from __future__ import annotations

from typing import Callable, Dict, Protocol, Tuple


class Calculator(Protocol):
    name: str

    def energy_forces(self, atoms) -> Tuple[float, "object"]: ...
    def relax(self, atoms, fmax: float, steps: int): ...


_FACTORIES: Dict[str, Callable[..., Calculator]] = {}


def register(name: str):
    def deco(factory):
        _FACTORIES[name] = factory
        return factory
    return deco


def get(name: str, **kw) -> Calculator:
    from . import uma, mace, chgnet  # noqa: F401  register on import
    if name not in _FACTORIES:
        raise KeyError(f"unknown calculator {name}; known: {sorted(_FACTORIES)}")
    return _FACTORIES[name](**kw)


def available() -> list:
    from . import uma, mace, chgnet  # noqa: F401
    return sorted(_FACTORIES)
