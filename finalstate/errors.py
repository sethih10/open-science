"""Typed failures. A tool never returns a half result; it raises one of these and the trace records it."""


class FinalStateError(Exception):
    """Base class."""


class SettingsNotLocked(FinalStateError):
    """A tool that reads PROJECT.md was called before the human approved the settings."""


class Rejected(FinalStateError):
    """A candidate failed the gate; carries the GateResult."""

    def __init__(self, gate):
        super().__init__(f"candidate {gate.candidate_id} rejected at {gate.stage}")
        self.gate = gate


class Escalate(FinalStateError):
    """Doubt above the threshold or an unseen system: stop and ask the human; carries the DoubtFlag."""

    def __init__(self, flag):
        super().__init__(f"escalate: {flag.trigger} on {flag.candidate_id}")
        self.flag = flag


class CheckpointPending(FinalStateError):
    """The planner reached a checkpoint and must wait for a HumanChoice."""

    def __init__(self, name):
        super().__init__(f"checkpoint pending: {name}")
        self.name = name


class OpenDecision(FinalStateError):
    """A threshold marked 'open: team decision' was needed and not supplied."""
