"""Calls go one way: schemas and errors, then registry, then runtime, then tools and calculators and execution,
then agent and mcp and cli on top. A module may import from its own layer or a lower one, never a higher one."""
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "fragplace"
LAYER = {"schemas": 0, "errors": 0, "registry": 1, "runtime": 2, "memory": 2, "calculators": 3, "execution": 3, "tools": 3,
         "agent": 4, "mcp": 4, "eval": 4, "cli": 4}
IMPORT = re.compile(r"^from \.(\.?)(\w*)", re.M)


def layer_of(path: Path) -> str:
    rel = path.relative_to(SRC)
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


@pytest.mark.parametrize("path", sorted(SRC.rglob("*.py")), ids=lambda p: str(p.relative_to(SRC)))
def test_module_imports_only_its_layer_or_below(path: Path):
    here = layer_of(path)
    if here == "__init__":
        return
    for m in IMPORT.finditer(path.read_text()):
        up, name = m.groups()
        target = name if up else here          # "from ..x" reaches a sibling package x; "from .x" stays inside
        if target in ("", "__init__"):
            continue
        assert LAYER[target] <= LAYER[here], f"{path.relative_to(SRC)} ({here}, layer {LAYER[here]}) imports {target} (layer {LAYER[target]})"
