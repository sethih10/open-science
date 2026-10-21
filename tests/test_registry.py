"""The registry, the tool modules and the figures' data module name the same tools with the same parameters."""
import importlib
import inspect
import sys
from pathlib import Path

import pytest

from finalstate.registry import BY_NAME, REGISTRY, ToolSpec

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "archive" / "docs" / "figures" / "src"))
import _board  # noqa: E402


@pytest.mark.parametrize("spec", REGISTRY, ids=lambda s: s.name)
def test_module_exposes_function_with_spec_parameters(spec: ToolSpec):
    module = importlib.import_module(spec.module)
    fn = getattr(module, spec.name)
    assert callable(fn)
    assert list(inspect.signature(fn).parameters) == list(spec.inputs)


@pytest.mark.parametrize("spec", REGISTRY, ids=lambda s: s.name)
def test_spec_is_complete(spec: ToolSpec):
    assert spec.status in ("core", "extension", "later")
    assert spec.purpose and spec.inputs and spec.outputs
    keys = {s.key for s in _board.STEPS}
    for k in spec.board_steps:
        assert k in keys, f"{spec.name}: {k} is not a board step"


def test_board_and_registry_name_the_same_tools():
    in_board = {t for s in _board.STEPS for t in s.tools + s.ext_tools}
    core_and_ext = {t.name for t in REGISTRY if t.status in ("core", "extension")}
    assert in_board == core_and_ext, f"only in board: {in_board - core_and_ext}; only in registry: {core_and_ext - in_board}"


def test_every_board_step_has_a_tool_or_an_owner_that_is_not_a_tool():
    for s in _board.STEPS:
        if "T" in s.owners:
            assert s.tools, f"step {s.key} is owned by a tool but names none"


def test_registry_names_are_unique_and_match_board_step_tools():
    assert len(BY_NAME) == len(REGISTRY)
    for s in _board.STEPS:
        for t in s.tools:
            assert s.key in BY_NAME[t].board_steps, f"{t} does not list board step {s.key}"
