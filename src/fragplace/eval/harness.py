"""The agent-level harness: the same campaign with and without each skill and each agent, scored on the same OC20NEB subset, as AtomisticSkillsBenchmark and aviary environments do. Data under docs/benchmark/ until D3 fixes the subset."""


def run(campaign: str, subset: str, ablate: str = "") -> dict:
    raise NotImplementedError("D3: the subset and the pass criterion are open: team decision")
