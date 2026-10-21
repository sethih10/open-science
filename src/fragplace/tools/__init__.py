"""One module per category, as ChemCrow and Biomni group their tools; get(name) returns the function the registry names."""
from __future__ import annotations

import importlib
from typing import Callable

from ..registry.tools import BY_NAME


def get(name: str) -> Callable:
    return getattr(importlib.import_module(BY_NAME[name].module), name)
