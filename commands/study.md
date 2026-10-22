---
description: Run a FragPlace study with the orchestrator, from the inputs to the report, asking the human at every checkpoint
argument-hint: <study>
allowed-tools: Read, Grep, Glob, AskUserQuestion, Agent, Bash(code:*), Bash(fragplace init:*), Bash(fragplace status:*), mcp__plugin_fragplace_fragplace
---

# Study $ARGUMENTS

From now on in this conversation you are the orchestrator of the study `$ARGUMENTS`. Your instructions are the agent page `agents/solution-planner.md` of this plugin, the one copy of them: read it now, at `${CLAUDE_PLUGIN_ROOT}/agents/solution-planner.md`, which is `agents/solution-planner.md` in this repository, and follow it. Then call `study_status` for `$ARGUMENTS` and go on from where the study stands.
