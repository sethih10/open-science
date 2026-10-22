"""A persisted job tracker with a retry cap: every submission, its state and its attempts in runs/<study>/jobs.json.

The recovery agent may ask for a retry only while attempts are below the cap; the cap is code, not a prompt. The
batch lane keeps its jobs here too, each under its request hash, with the heavy tool, the Slurm state, the
resources of the last attempt and the times it was submitted and finished; state is one of the four words of
execution.slurm.STATES.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from . import Job, JobHandle

RETRY_CAP = 3


class JobRecord(BaseModel):
    name: str
    backend: str
    handle_id: str
    workdir: str
    state: str = "submitted"
    attempts: int = 1
    diagnoses: List[str] = Field(default_factory=list)
    updated: datetime = Field(default_factory=datetime.now)
    tool: Optional[str] = None                  # the batch lane's: the heavy tool the job calls
    hash: Optional[str] = None                  # the batch lane's request hash, the record's key in jobs.json
    slurm_state: Optional[str] = None           # PENDING, RUNNING, COMPLETED, TIMEOUT, as Slurm last said
    resources: Dict[str, Any] = Field(default_factory=dict)
    submitted: Optional[datetime] = None
    finished: Optional[datetime] = None


class JobTracker:
    def __init__(self, run_dir: Path):
        self.path = Path(run_dir) / "jobs.json"
        self.jobs: Dict[str, JobRecord] = {}
        if self.path.exists():
            for k, v in json.loads(self.path.read_text()).items():
                self.jobs[k] = JobRecord.model_validate(v)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({k: v.model_dump(mode="json") for k, v in self.jobs.items()}, indent=1, default=str))

    def put(self, key: str, rec: JobRecord) -> JobRecord:
        """Keep rec under key, its update time now, and save."""
        rec.updated = datetime.now()
        self.jobs[key] = rec
        self._save()
        return rec

    def add(self, job: Job, handle: JobHandle) -> JobRecord:
        rec = self.jobs.get(job.name)
        if rec:
            rec.attempts += 1; rec.handle_id = handle.id; rec.state = "submitted"; rec.updated = datetime.now()
        else:
            rec = JobRecord(name=job.name, backend=handle.backend, handle_id=handle.id, workdir=job.workdir)
            self.jobs[job.name] = rec
        self._save()
        return rec

    def update(self, name: str, state: str, diagnosis: Optional[str] = None) -> JobRecord:
        rec = self.jobs[name]
        rec.state = state; rec.updated = datetime.now()
        if diagnosis:
            rec.diagnoses.append(diagnosis)
        self._save()
        return rec

    def can_retry(self, name: str, cap: int = RETRY_CAP) -> bool:
        rec = self.jobs.get(name)
        return rec is None or rec.attempts < cap

    def failed(self) -> List[JobRecord]:
        return [r for r in self.jobs.values() if r.state == "failed"]
