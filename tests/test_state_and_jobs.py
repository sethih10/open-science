"""Run state resumes and job attempts are capped."""
from pathlib import Path

import pytest

from fragplace.runtime import checkpoints, state
from fragplace.execution import Job, JobHandle
from fragplace.execution.tracker import RETRY_CAP, JobTracker
from fragplace.errors import CheckpointPending
from fragplace.schemas.records import HumanChoice


def test_state_advances_and_blocks_on_a_pending_checkpoint(tmp_path: Path):
    s = state.load(tmp_path, "c")
    assert s.current_step == "prompt"
    state.complete(tmp_path, s, "prompt")
    state.complete(tmp_path, s, "1", next_checkpoint="approve settings")
    assert s.current_step == "1*"
    with pytest.raises(CheckpointPending):
        state.resume(tmp_path, "c")
    checkpoints.record(tmp_path, HumanChoice(checkpoint="approve settings", chosen=[], reason="ok", who="team"))
    assert state.resume(tmp_path, "c").pending_checkpoint is None
    with pytest.raises(ValueError):
        state.complete(tmp_path, s, "9z")


def test_job_tracker_caps_retries(tmp_path: Path):
    t = JobTracker(tmp_path)
    job = Job(name="sp-c1", command="echo", workdir=str(tmp_path))
    for i in range(RETRY_CAP):
        assert t.can_retry("sp-c1")
        t.add(job, JobHandle(id=str(i), backend="local"))
        t.update("sp-c1", "failed", diagnosis=f"attempt {i}")
    assert not t.can_retry("sp-c1")
    assert JobTracker(tmp_path).jobs["sp-c1"].attempts == RETRY_CAP
    assert len(t.failed()) == 1
