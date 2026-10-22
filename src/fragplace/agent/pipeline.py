"""The pipeline as code: the board's steps in execution order, the tools each step may call, the agents that act
there, and the checkpoint the human passes before the next step runs.

This is the module that knows who runs next. The decision is not left to an LLM: the order is the board's, the
tools come from the registry by board step, and the five checkpoints are raised as CheckpointPending and persisted
by runtime.state, so a run stops exactly where a human must look and resumes from there. The practised patterns it
follows: paper-qa's run_fake_agent, a deterministic rollout over the same registered tools an LLM agent could
call; Adsorb-Agent's singlerun_adsorb_aigent, one fixed sequence with critic loops; ChemGraph's approvals,
a pause at a human review, the decision journaled, a policy that blocks the call. No graph library: fourteen steps
in a fixed order with five pauses need none, and the hook in runtime.policy enforces the same gates for an LLM
that calls the tools itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ..errors import CheckpointPending
from ..registry.agents import CHECKPOINTS, PLANNER
from ..registry.tools import REGISTRY


@dataclass(frozen=True)
class PipelineStep:
    key: str                                  # the board's number
    agents: Tuple[str, ...]                   # the agents that act here, the planner always
    checkpoint: Optional[str] = None          # the human passes it before the next step runs
    alternative_to: Optional[str] = None      # 3.6 is the alternative generator to the enumeration of 3.5

    @property
    def tools(self) -> Tuple[str, ...]:
        return tuple(t.name for t in REGISTRY if self.key in t.board_steps and t.status == "core")

    @property
    def ext_tools(self) -> Tuple[str, ...]:
        return tuple(t.name for t in REGISTRY if self.key in t.board_steps and t.status == "extension")


# execution order: 3.2, 3.3, 3.4 run in that order inside step 3; 3.6 is the alternative generator; 3.1 runs inside 5.
# 3.5 is deferred: the team decides later how to implement it; until then fragment A stays at its initial-state site,
# the cheap baseline the board named, and adsorbate_placement runs only at step 4, for B.
PIPELINE: Tuple[PipelineStep, ...] = (
    PipelineStep("prompt", (PLANNER, "computational-chemist", "literature-reader")),
    PipelineStep("1", (PLANNER, "computational-chemist"), checkpoint="approve settings"),
    PipelineStep("1*", (PLANNER, "mlip-specialist", "scientific-critic"), checkpoint="approve the plan"),
    PipelineStep("2", (PLANNER,)),
    # PipelineStep("3.5", (PLANNER,)),   deferred, see above; the board keeps the number
    PipelineStep("3.2", (PLANNER, "literature-reader")),
    PipelineStep("3.3", (PLANNER,)),
    PipelineStep("3.4", (PLANNER, "surface-chemist")),
    PipelineStep("3.6", (PLANNER,), alternative_to="3.5"),
    PipelineStep("4", (PLANNER,)),
    PipelineStep("5", (PLANNER,)),
    PipelineStep("6", (PLANNER,)),
    PipelineStep("7", (PLANNER, "mlip-specialist"), checkpoint="review flagged cases"),
    PipelineStep("8", (PLANNER,), checkpoint="pick up to five final states"),
    PipelineStep("solution", (PLANNER, "scientific-critic"), checkpoint="interpret results"),
)
BY_KEY: Dict[str, PipelineStep] = {s.key: s for s in PIPELINE}
STEP_ORDER: List[str] = [s.key for s in PIPELINE]
AFTER_STEP: Dict[str, str] = {s.checkpoint: s.key for s in PIPELINE if s.checkpoint}
assert tuple(AFTER_STEP) == CHECKPOINTS, "every checkpoint sits after exactly one step, in the board's order"


def next_step(key: str) -> Optional[str]:
    i = STEP_ORDER.index(key)
    return STEP_ORDER[i + 1] if i + 1 < len(STEP_ORDER) else None


def agents_at(key: str) -> Tuple[str, ...]:
    return BY_KEY[key].agents


def tools_at(key: str) -> Tuple[str, ...]:
    return BY_KEY[key].tools


Invoke = Callable[[str, str], object]  # invoke(tool_name, step_key): the caller binds the tool's inputs from the run's artifacts


def run(run_dir: Path, campaign: str, invoke: Invoke, use_minima_hopping: bool = False) -> str:
    """The deterministic rollout. Resumes from state.json, calls each step's core tools in order through
    `invoke`, records the step, and stops with CheckpointPending where the human must choose. Returns the key of
    the step it stopped after, or "done". The same gates hold for an LLM planner calling the tools itself: the
    hook reads the registry's checkpoint_gate, this function reads the step's checkpoint, and both come from the
    same two tables."""
    from ..runtime import state as run_state
    st = run_state.resume(run_dir, campaign)          # raises CheckpointPending if a choice is still owed
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
