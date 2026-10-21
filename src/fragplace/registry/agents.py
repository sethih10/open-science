"""The roster: every agent named as the literature names the role, with the one thing it decides.
docs/figures/src/_board.py imports this, so the figures, the docs and the code share one list."""
PLANNER = "solution-planner"
HPC_ONLY = ("dft-recovery-agent",)
CHECKPOINTS = ("approve settings", "approve the plan", "review flagged cases", "pick up to five final states", "interpret results")
AGENTS = {
    "solution-planner": "the next tool call and when to stop; holds the checkpoint list; calls every tool by name, reads cards, never writes coordinates",
    "literature-reader": "which published values and sources to put before the human: E_ads with functional and site, and d, the length of the bond to break",
    "computational-chemist": "which protocol and settings to propose for the lock, from the Formulate interview and the inputs' own settings",
    "surface-chemist": "which site types and orderings to try per fragment, from the chemistry of the broken bond; never a coordinate, never an override",
    "mlip-specialist": "which potential to use, and whether to trust, repair or escalate on the calibrated doubt",
    "scientific-critic": "whether the plan and the report hold up, judged in its own context before the human sees them",
    "dft-recovery-agent": "how to retry a failed DFT step, one change at a time, capped at three; only with HPC",
}
SKILLS_OURS = ("dft-settings-protocol", "mlip-doubt-calibration", "dissociation-final-state", "final-state-report", "hpc-dft-jobs")
SKILLS_REUSED = ("ml-committee-uncertainty", "ml-mlip-benchmark", "ml-mace-finetune", "chem-thermochemistry", "general-peer-review")
