"""Run a job as a local subprocess; the laptop and GPU lanes. And the CPU budget of this process, which sets how
many threads the numerical libraries start."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict

from . import Job, JobHandle

BLAS_THREADS_MAX = 4      # the optimisers' eigensolves are small; more BLAS threads only wait on each other


def cpu_budget() -> int:
    """The CPUs this process may use: its affinity mask, cut to the CPU quota of its cgroup where one is set. A
    shared login node may grant a user two CPUs while the mask shows every core; a Slurm job's mask is its allocation."""
    n = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)
    try:
        group = Path("/sys/fs/cgroup" + Path("/proc/self/cgroup").read_text().strip().split("::")[-1])
        for d in [group, *group.parents]:
            limit = d / "cpu.max"
            if limit.exists():
                quota, period = limit.read_text().split()
                if quota != "max":
                    n = min(n, max(1, int(quota) // int(period)))
    except (OSError, ValueError):
        pass
    return n


def limit_threads() -> int:
    """Set the thread counts of OpenMP, torch included, and of OpenBLAS to the CPU budget, unless the user set them;
    a library that starts a thread per visible core on a smaller budget runs a hundred times slower. Call it before
    numpy or torch loads."""
    n = cpu_budget()
    os.environ.setdefault("OMP_NUM_THREADS", str(n))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", str(min(n, BLAS_THREADS_MAX)))
    os.environ.setdefault("MKL_NUM_THREADS", str(n))
    return n


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
