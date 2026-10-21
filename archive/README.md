# Archive

The theory, the design history and the reviews behind the project. Nothing here is needed to write the code; the root `README.md` states the problem and the pipeline, and `agent.md` holds what a coding agent needs.

| Path | What it is |
|---|---|
| `docs/adsorption-agent-workflow.md` | The design document with all 26 figures: science, workflow, prior work, intuition, geometry, the final-state problem, build plan, decisions |
| `docs/agent-context.md` | The same, text only, for agents |
| `docs/agent-build-context.md` | The long form of `agent.md`: every tool with inputs, outputs, checks and thresholds, data formats, build order, open decisions |
| `docs/repo-survey.md` | 42 repositories opened on 21 October 2026: what to wrap, licences, a recommended stack |
| `docs/chemistry-agents-review.md` | 39 LLM agents with chemistry or surface knowledge, by the channel it enters through, with numbers |
| `docs/agent-writing-style.md` | Prose and figure conventions used for everything here |
| `docs/figures/` | The figures and, under `src/`, the scripts for figures 13 to 32; 22 and 23 carry the later phase, 27 and 28 are final-state-only versions, 29 to 32 are the figures shown in the root README |
| `docs/figures/src/_board.py` | The single source of truth for the pipeline: one record per board step; figures 29 to 32 and the README tables are generated from it |
| `docs/figures/src/board_tables.py`, `board_check.py` | Write the README tables from `_board.py`; assert that the four figures, the README and `agent.md` section 2 agree with it |
