# Benchmark

The measurables of the README, scored on an OC20NEB subset that starts with *OH → *O + *H on Pt(111). Nothing is here yet; the subset, the single-placement baseline and the pass criterion are open: team decision, AGENTS.md section 11.

| File, planned | Holds |
|---|---|
| `subset.json` | the OC20NEB reactions chosen, with their product frames |
| `baselines/` | NEBscape's Pareto choice, CatTSunami's shell sampling, a single placement, per reaction |
| `score.py` | recombination rate, lateral interaction, the three-policy comparison, the OC20NEB product-frame comparison |
| `results/` | one JSON per run, written by `fragplace.tools.report` |
| `agents/` | the agent-level harness: the same campaign run with and without each skill and each agent, scored on the same subset, as AtomisticSkillsBenchmark and aviary environments do |
