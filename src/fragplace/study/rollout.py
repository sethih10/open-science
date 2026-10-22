"""The pipeline as code: the deterministic rollout over the steps of registry.steps.

This is the module that runs who comes next. The decision is not left to an LLM: the order is the board's, the
tools come from the registry by board step, and the five checkpoints are raised as CheckpointPending and persisted
by runtime.state, so a run stops exactly where a human must look and resumes from there. The practised patterns it
follows: paper-qa's run_fake_agent, a deterministic rollout over the same registered tools an LLM agent could
call; Adsorb-Agent's singlerun_adsorb_aigent, one fixed sequence with critic loops; ChemGraph's approvals,
a pause at a human review, the decision journaled, a policy that blocks the call. No graph library: fourteen steps
in a fixed order with five pauses need none, and the hook in runtime.policy enforces the same gates for an LLM
that calls the tools itself.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..errors import CheckpointPending
from ..registry.agents import PLANNER  # noqa: F401  re-exported for the tests and the figures
from ..registry.steps import AFTER_STEP, BY_KEY, PIPELINE, STEP_ORDER, PipelineStep, agents_at, next_step, tools_at  # noqa: F401
from ..runtime import state as run_state

Invoke = Callable[[str, str], object]  # invoke(tool_name, step_key): the caller binds the tool's inputs from the run's artifacts


def run(run_dir: Path, study: str, invoke: Invoke, use_minima_hopping: bool = False) -> str:
    """The deterministic rollout. Resumes from state.json, calls each step's core tools in order through
    `invoke`, records the step, and stops with CheckpointPending where the human must choose. Returns "done"
    when the last step has run. The same gates hold for an LLM planner calling the tools itself: the hook reads
    the registry's checkpoint_gate, this function reads the step's checkpoint, and both come from the registry."""
    st = run_state.resume(run_dir, study)          # raises CheckpointPending if a choice is still owed
    key = st.current_step
    while key not in (None, "done"):
        step = BY_KEY[key]
        skip = bool(step.alternative_to) and not use_minima_hopping
        if not skip:
            for tool in step.tools:
                invoke(tool, key)
        run_state.complete(run_dir, st, key, next_checkpoint=step.checkpoint)
        if step.checkpoint:
            raise CheckpointPending(step.checkpoint)
        key = next_step(key)
    return "done"
