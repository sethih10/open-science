"""The steps as data: the board's numbers in execution order, the agents that act at each, the tools each may
call, from registry.tools by board step, and the checkpoint the human passes before the next step runs.

A definition, not a loop: agent.pipeline runs it, runtime.state persists the position in it, and the figures'
data module checks against it. Step 3.5 is deferred: it stays on the board with its number, commented out here
until the team decides how to implement it; fragment A stays at its initial-state site and adsorbate_placement
runs only at step 4, for B. 3.6 is the alternative generator; 3.1 runs inside step 5.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .agents import CHECKPOINTS, PLANNER
from .tools import REGISTRY


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


PIPELINE: Tuple[PipelineStep, ...] = (
    PipelineStep("prompt", (PLANNER, "computational-chemist", "literature-reader")),
    PipelineStep("1", (PLANNER, "computational-chemist"), checkpoint="approve settings"),
    PipelineStep("1*", (PLANNER, "mlip-specialist", "scientific-critic"), checkpoint="approve the plan"),
    PipelineStep("2", (PLANNER,)),
    # PipelineStep("3.5", (PLANNER,)),   deferred, see the module docstring; the board keeps the number
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
