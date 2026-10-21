"""The registry, the tool modules, the agent files and the figures' data module name the same tools, roles and
checkpoints with the same parameters."""
import importlib
import inspect
import re
import sys
from pathlib import Path

import pytest

from fragplace.registry.tools import BY_NAME, CHECKPOINTS, LANES, REGISTRY, ToolSpec, for_role

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docs" / "figures" / "src"))
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
    assert spec.lane in LANES
    assert spec.checkpoint_gate is None or spec.checkpoint_gate in CHECKPOINTS
    assert spec.purpose and spec.inputs and spec.outputs and spec.allowed_roles
    assert re.match(r"\d+\.\d+\.\d+$", spec.version)
    keys = {s.key for s in _board.STEPS}
    for k in spec.board_steps:
        assert k in keys, f"{spec.name}: {k} is not a board step"
    for role in spec.allowed_roles:
        assert role in _board.AGENTS, f"{spec.name}: {role} is not an agent of the roster"


def test_board_and_registry_name_the_same_tools():
    in_board = {t for s in _board.STEPS for t in s.tools + s.ext_tools}
    core_and_ext = {t.name for t in REGISTRY if t.status in ("core", "extension")}
    assert in_board == core_and_ext, f"only in board: {in_board - core_and_ext}; only in registry: {core_and_ext - in_board}"


def test_registry_checkpoints_equal_board_checkpoints():
    assert CHECKPOINTS == _board.CHECKPOINTS


def test_every_board_step_has_a_tool_or_an_owner_that_is_not_a_tool():
    for s in _board.STEPS:
        if "T" in s.owners:
            assert s.tools, f"step {s.key} is owned by a tool but names none"


def test_registry_names_are_unique_and_match_board_step_tools():
    assert len(BY_NAME) == len(REGISTRY)
    for s in _board.STEPS:
        for t in s.tools:
            assert s.key in BY_NAME[t].board_steps, f"{t} does not list board step {s.key}"


def test_every_agent_of_the_board_acts_somewhere_and_has_a_file():
    acting = {n for s in _board.STEPS for n, _ in s.agents} | {_board.PLANNER}
    for name in _board.AGENTS:
        if name in _board.HPC_ONLY:
            continue
        assert name in acting, f"{name} is in the roster but acts at no step"
    for name in _board.AGENTS:
        assert (ROOT / "agents" / f"{name}.md").exists(), f"agents/{name}.md is missing"


@pytest.mark.parametrize("name", list(_board.AGENTS), ids=lambda n: n)
def test_agent_file_lists_exactly_the_tools_the_registry_allows(name: str):
    text = (ROOT / "agents" / f"{name}.md").read_text()
    m = re.search(r"^tools:\s*(.*)$", text, re.M)
    assert m, f"agents/{name}.md has no tools line"
    listed = {t.strip() for t in m.group(1).split(",") if t.strip().startswith("mcp__fragplace__")}
    allowed = {f"mcp__fragplace__{t.name}" for t in for_role(name)}
    assert listed == allowed, f"{name}: listed {sorted(listed)} but the registry allows {sorted(allowed)}"
    assert re.search(r"^name:\s*" + re.escape(name) + r"\s*$", text, re.M)


def test_pipeline_agrees_with_the_board_and_the_registry():
    from fragplace.agent import pipeline
    from fragplace.runtime import checkpoints, state
    assert state.STEP_ORDER == pipeline.STEP_ORDER
    assert checkpoints.CHECKPOINTS == CHECKPOINTS == _board.CHECKPOINTS
    board = {s.key: s for s in _board.STEPS}
    for step in pipeline.PIPELINE:
        b = board[step.key]
        assert step.checkpoint == b.checkpoint, step.key
        assert set(step.agents) - {pipeline.PLANNER} == {n for n, _ in b.agents} - {pipeline.PLANNER}, step.key
        assert set(step.tools) == set(b.tools), step.key
        assert set(step.ext_tools) == set(b.ext_tools), step.key
    assert set(pipeline.STEP_ORDER) | {"3.1"} == set(board)  # 3.1 runs inside 5 and is not a step of its own


def test_rollout_stops_at_each_checkpoint_and_resumes(tmp_path: Path):
    from fragplace.agent import pipeline
    from fragplace.errors import CheckpointPending
    from fragplace.runtime import checkpoints
    from fragplace.schemas.records import HumanChoice
    calls = []
    invoke = lambda tool, step: calls.append((step, tool))  # noqa: E731
    stops = []
    for _ in range(6):
        try:
            assert pipeline.run(tmp_path, "c", invoke) == "done"
            break
        except CheckpointPending as e:
            stops.append(e.name)
            checkpoints.record(tmp_path, HumanChoice(checkpoint=stops[-1], chosen=[], reason="ok", who="team"))
    assert len(stops) == 5
    steps_called = [s for s, _ in calls]
    assert steps_called == sorted(steps_called, key=pipeline.STEP_ORDER.index)
    assert "3.6" not in steps_called and "3.5" in steps_called
    assert ("prompt", "literature_lookup") in calls and ("8", "ranking") in calls
