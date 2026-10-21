"""Submit to Slurm. Only the DFT lane uses it. Error handling: custodian handlers wrap the DFT command inside the
job script, so a failed SCF or a wrong POTIM is retried by code before any agent is asked."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import Job, JobHandle

SCRIPT = """#!/bin/bash
#SBATCH --job-name={name}
#SBATCH --nodes={nodes}
#SBATCH --time={time}
#SBATCH --partition={partition}
cd {workdir}
{command}
"""


class SlurmBackend:
    name = "slurm"

    def submit(self, job: Job) -> JobHandle:
        r = {"nodes": "1", "time": "02:00:00", "partition": "normal", **job.resources}
        script = Path(job.workdir) / f"{job.name}.sh"
        script.write_text(SCRIPT.format(name=job.name, workdir=job.workdir, command=job.command, **r))
        out = subprocess.run(["sbatch", str(script)], capture_output=True, text=True, check=True).stdout
        return JobHandle(id=out.strip().split()[-1], backend=self.name)

    def status(self, handle: JobHandle) -> str:
        out = subprocess.run(["squeue", "-h", "-j", handle.id, "-o", "%T"], capture_output=True, text=True).stdout.strip()
        if out in ("PENDING", "CONFIGURING"):
            return "submitted"
        if out in ("RUNNING", "COMPLETING"):
            return "running"
        acct = subprocess.run(["sacct", "-n", "-j", handle.id, "-o", "State", "-X"], capture_output=True, text=True).stdout.strip()
        return "done" if acct.startswith("COMPLETED") else "failed"

    def result_dir(self, handle: JobHandle) -> str:
        return subprocess.run(["scontrol", "show", "job", handle.id], capture_output=True, text=True).stdout.split("WorkDir=")[-1].split()[0]
