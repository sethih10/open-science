# Docs

The theory, the design history and the reviews behind the project. Nothing here is needed to write the code; the root `README.md` states the problem and the pipeline, and `AGENTS.md` holds what a coding agent needs.

| Path | What it is |
|---|---|
| `design/adsorption-agent-workflow.md` | The design document with all 26 figures: science, workflow, prior work, intuition, geometry, the final-state problem, build plan, decisions |
| `design/agent-context.md` | The same, text only, for agents |
| `design/agent-build-context.md` | The long form of `AGENTS.md`: every tool with inputs, outputs, checks and thresholds, data formats, build order, open decisions |
| `design/repo-survey.md` | 42 repositories opened on 21 October 2026: what to wrap, licences, a recommended stack |
| `design/chemistry-agents-review.md` | 39 LLM agents with chemistry or surface knowledge, by the channel it enters through, with numbers |
| `design/agent-writing-style.md` | Prose and figure conventions used for everything here |
| `figures/` | The figures and, under `src/`, the scripts for figures 13 to 32; 22 and 23 carry the later phase, 27 and 28 are final-state-only versions, 29 to 32 are the figures shown in the root README |
| `figures/src/_board.py` | The single source of truth for the pipeline: one record per board step; figures 29 to 32 and the README tables are generated from it |
| `design/scientific-agent-architectures.md` | 28 scientific-agent systems and their verbatim role names, 12 repositories' tool declarations, operational components, the roster mapping; opened 21 October 2026 |
| `figures/src/board_tables.py`, `board_check.py` | Write the README tables from `_board.py`; assert that the four figures, the README and `AGENTS.md` section 2 agree with it |

The roster was renamed on 21 October 2026 after the architecture review; the earlier figures 19 to 28 and the design documents carry the old names final-state-planner, dft-settings-interviewer, geometry-critic and dft-job-steward.
