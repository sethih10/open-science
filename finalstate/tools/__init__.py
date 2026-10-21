"""One module per tool, named as in finalstate.registry. get(name) returns the function."""
from __future__ import annotations

import importlib
from typing import Callable

from ..registry import BY_NAME


def get(name: str) -> Callable:
    spec = BY_NAME[name]
    module = importlib.import_module(spec.module)
    return getattr(module, name)
