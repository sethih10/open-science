"""Run a job as a local subprocess; the laptop and GPU lanes."""
from __future__ import annotations

import subprocess
from typing import Dict

from . import Job, JobHandle


class LocalBackend:
    name = "local"

    def __init__(self):
        self._procs: Dict[str, subprocess.Popen] = {}
        self._dirs: Dict[str, str] = {}

    def submit(self, job: Job) -> JobHandle:
        proc = subprocess.Popen(job.command, shell=True, cwd=job.workdir)
        self._procs[job.name] = proc
        self._dirs[job.name] = job.workdir
        return JobHandle(id=job.name, backend=self.name)

    def status(self, handle: JobHandle) -> str:
        proc = self._procs[handle.id]
        rc = proc.poll()
        if rc is None:
            return "running"
        return "done" if rc == 0 else "failed"

    def result_dir(self, handle: JobHandle) -> str:
        return self._dirs[handle.id]
