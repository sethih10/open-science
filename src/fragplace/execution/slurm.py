"""Submit to Slurm, and read a job's state the one way both Slurm users here read it: the DFT lane's SlurmBackend
and the batch lane of execution.batch. Error handling of the DFT lane: custodian handlers wrap the DFT command
inside the job script, so a failed SCF or a wrong POTIM is retried by code before any agent is asked.

No partition is set unless the job names one: Triton picks it from the time. sbatch runs with --parsable, so its
answer is the job id alone. A job's state comes from one squeue while it is in the active queue, then from one
sacct; a job that has left the queue has not succeeded until sacct says COMPLETED.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List

from . import Job, JobHandle

# Slurm's job states as squeue and sacct print them, in the four words of JobHandle and the tracker. UNKNOWN is a
# job neither command knows yet, as right after it left the queue and before accounting has it; any state not
# listed has ended without success.
STATES: Dict[str, str] = {
    **dict.fromkeys(("PENDING", "CONFIGURING", "REQUEUED", "REQUEUE_HOLD", "REQUEUE_FED", "RESV_DEL_HOLD", "UNKNOWN"), "submitted"),
    **dict.fromkeys(("RUNNING", "COMPLETING", "SUSPENDED", "STOPPED", "STAGE_OUT", "SIGNALING", "RESIZING"), "running"),
    "COMPLETED": "done",
}
ACTIVE = frozenset(k for k, v in STATES.items() if v != "done")


def word(state: str) -> str:
    """A Slurm state in the four words: submitted, running, done or failed."""
    return STATES.get(state, "failed")


def _first_word(text: str) -> str:
    """The state on the last line of a command's answer, CANCELLED for "CANCELLED by 1234"; empty when none."""
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return lines[-1].split()[0].upper() if lines else ""


def slurm_state(job_id: str) -> str:
    """The job's Slurm state: one squeue while it is in the active queue, else one sacct; UNKNOWN when neither
    knows it yet. The caller keeps the interval between two calls."""
    queued = subprocess.run(["squeue", "-h", "-j", str(job_id), "-o", "%T"], capture_output=True, text=True)
    state = _first_word(queued.stdout) if queued.returncode == 0 else ""
    if state:
        return state
    acct = subprocess.run(["sacct", "-n", "-X", "-P", "-j", str(job_id), "-o", "State"], capture_output=True, text=True)
    return _first_word(acct.stdout) or "UNKNOWN"


def submit_script(path: Path) -> str:
    """sbatch --parsable on a job script; the job id. A refusal raises CalledProcessError with sbatch's own words."""
    out = subprocess.run(["sbatch", "--parsable", str(path)], capture_output=True, text=True, check=True).stdout
    return out.strip().split(";")[0]


def header(resources: Dict[str, str]) -> List[str]:
    """The #SBATCH lines of resources, in a fixed order; a partition only when one is named."""
    order = ("job-name", "nodes", "ntasks", "cpus-per-task", "mem", "time", "partition", "gpus", "output")
    return [f"#SBATCH --{k}={resources[k]}" for k in order if resources.get(k) not in (None, "")]


class SlurmBackend:
    name = "slurm"

    def submit(self, job: Job) -> JobHandle:
        r = {"nodes": "1", "time": "02:00:00", **job.resources, "job-name": job.name}
        script = Path(job.workdir) / f"{job.name}.sh"
        script.write_text("\n".join(["#!/bin/bash -l", *header(r), f"cd {job.workdir}", job.command, ""]))
        return JobHandle(id=submit_script(script), backend=self.name)

    def status(self, handle: JobHandle) -> str:
        return word(slurm_state(handle.id))

    def result_dir(self, handle: JobHandle) -> str:
        return subprocess.run(["scontrol", "show", "job", handle.id], capture_output=True, text=True).stdout.split("WorkDir=")[-1].split()[0]
