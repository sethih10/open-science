"""The batch lane: one sbatch job per heavy call, never one per structure, for a call too long to hold the session.

BatchLane.run writes the call as request.json under runs/<study>/jobs/<hash>/ and submits one job that makes the
same call, <python> -m fragplace.execution.batch run <request.json>. Inside the job SLURM_JOB_ID is set, so the call
runs there, locally, and writes result.json beside the request, with the job's log slurm-<id>.out beside both. The
hash is of the tool's name, its arguments and the study's records, so a repeated call with the same hash reattaches
to the job still running, or returns the stored result, and never submits again; runs/<study>/jobs.json keeps each
job's hash, id, state, attempts, resources and times, through execution.tracker.

The lane polls with one squeue, then sacct, never more often than every POLL_S seconds, an Aalto rule; a job that has
left the queue has succeeded only when sacct says COMPLETED and result.json is there. TIMEOUT is submitted again with
twice the time, OUT_OF_MEMORY with twice the memory, NODE_FAIL and PREEMPTED as they were, three attempts in all;
then the call answers with an error that carries the Slurm state and the end of the job's log, for the
hpc-specialist to read. The lane never cancels a job. A call still without an answer at its registry timeout says
so and leaves the job running; the same call later reattaches. Every submission, change of state and resubmission
goes into the study's trace. The job script always sets the CPUs, the memory and the time, takes the thread counts
from SLURM_CPUS_PER_TASK and passes on PYTHONPATH and FRAGPLACE_ROOT; a root on a node's own disk is refused, as the
worker refuses it. A queued call found again by its hash is the idea of libAtoms ExPyRe and wfl, GPL-2.0; none of
their code is used.
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any, Callable, Dict, Mapping, Optional

from ..registry.tools import BY_NAME
from ..runtime.journal import Run, content_hash, default_root
from .local import BLAS_THREADS_MAX, limit_threads
from .slurm import ACTIVE, header, slurm_state, submit_script, word
from .srun import BATCH_CPUS, TAIL_CHARS, node_local
from .tracker import RETRY_CAP, JobRecord, JobTracker

POLL_S = 15.0                   # the least time between two polls of the scheduler, an Aalto rule for agents on Triton
MORE = {"TIMEOUT": "time", "OUT_OF_MEMORY": "mem_GB"}          # submitted again with twice this resource
AGAIN = ("NODE_FAIL", "PREEMPTED")                              # submitted again as they were
RESOURCES = ("cpus", "mem_GB", "time", "workers", "partition")   # the fields of a compute rule a job is made with
DEFAULT = {"cpus": BATCH_CPUS[0], "mem_GB": 2 * BATCH_CPUS[0], "workers": 1}   # a batch call without a rule; its time is the tool's registry timeout
GRACE_POLLS = 2                 # polls a COMPLETED job may take to show its result.json on a shared filesystem
TIME = re.compile(r"^(?:(\d+)-)?(\d+):([0-5]\d):([0-5]\d)$")
_LAST_POLL = [float("-inf")]    # when this process last asked the scheduler, for the floor between two polls


def seconds(text: str) -> int:
    """A Slurm time, HH:MM:SS or D-HH:MM:SS, in seconds."""
    m = TIME.match(str(text).strip())
    if not m:
        raise ValueError(f"time {text!r}: write HH:MM:SS")
    days, hours, minutes, secs = (int(x or 0) for x in m.groups())
    return ((days * 24 + hours) * 60 + minutes) * 60 + secs


def hms(total: float) -> str:
    """Seconds as a Slurm time: HH:MM:SS, D-HH:MM:SS from a day on."""
    days, rest = divmod(int(math.ceil(total)), 86400)
    hours, rest = divmod(rest, 3600)
    return (f"{days}-" if days else "") + f"{hours:02d}:{rest // 60:02d}:{rest % 60:02d}"


def request_hash(name: str, kwargs: Mapping[str, Any], records: str) -> str:
    """A request's identity: the tool, its arguments and the digest of the study's records it reads."""
    return content_hash({"tool": name, "kwargs": dict(kwargs), "records": records})


def resources_text(r: Mapping[str, Any]) -> str:
    return (f"{r.get('cpus')} CPUs, {r.get('mem_GB')} GB, time {r.get('time')}, {r.get('workers', 1)} pool workers, "
            + (f"partition {r['partition']}" if r.get("partition") else "partition from the time"))


def script(study: str, name: str, folder: Path, resources: Mapping[str, Any], python: Optional[str] = None) -> str:
    """The job script of one call: CPUs, memory and time always set, a partition only when the rule names one, the
    thread counts from SLURM_CPUS_PER_TASK, PYTHONPATH and FRAGPLACE_ROOT passed on, and the call made inside."""
    r = {"job-name": f"fragplace-{study}-{name}", "ntasks": "1", "cpus-per-task": str(int(resources["cpus"])),
         "mem": f"{math.ceil(float(resources['mem_GB']))}G", "time": str(resources["time"]), "partition": resources.get("partition"),
         "output": str(folder / "slurm-%j.out")}
    passed = {"PYTHONPATH": os.environ.get("PYTHONPATH", ""), "FRAGPLACE_ROOT": str(default_root()),
              "FRAGPLACE_WORKERS": str(int(resources.get("workers") or 1))}
    return "\n".join(["#!/bin/bash -l", *header(r),
                      'export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"',
                      f'export OPENBLAS_NUM_THREADS="$(( SLURM_CPUS_PER_TASK < {BLAS_THREADS_MAX} ? SLURM_CPUS_PER_TASK : {BLAS_THREADS_MAX} ))"',
                      *[f"export {k}={shlex.quote(v)}" for k, v in passed.items() if v],
                      f"cd {shlex.quote(str(folder))}",
                      f"exec {shlex.quote(python or sys.executable)} -m fragplace.execution.batch run {shlex.quote(str(folder / 'request.json'))}",
                      ""])


def poll(job: str) -> str:
    """The job's Slurm state, one squeue then sacct, never sooner than POLL_S after this process last asked."""
    wait = _LAST_POLL[0] + POLL_S - monotonic()
    if wait > 0:
        sleep(wait)
    _LAST_POLL[0] = monotonic()
    return slurm_state(job)


class BatchLane:
    """One sbatch job for one heavy call, with the resources of the call's rule; see the module docstring.
    functions names the function each tool's job calls, by its module and name; records is the digest of the
    study's records the request hash reads."""
    name = "batch"

    def __init__(self, functions: Mapping[str, Callable[..., Dict[str, Any]]], resources: Optional[Mapping[str, Any]] = None,
                 records: str = ""):
        self.functions, self.records = functions, records
        self.resources = {k: v for k, v in dict(resources or {}).items() if k in RESOURCES and v is not None}

    def run(self, name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        study = kwargs.get("study")
        if not study:
            return {"error": "ValueError", "message": f"{name}: the batch lane needs the study the call names"}
        root = default_root()
        if node_local(root):
            return {"error": "ComputeNodeError", "message": f"the root {root} is on this node's own disk, and a batch job's node has its "
                                                              "own: set FRAGPLACE_ROOT to a folder on a shared filesystem"}
        run_dir = root / "runs" / study
        if not (run_dir / "artifacts.json").is_file():
            return {"blocked": f"study {study} has no records under {run_dir}, so {name} has nothing to compute; nothing was submitted"}
        key = request_hash(name, kwargs, self.records)
        folder = run_dir / "jobs" / key
        jobs = JobTracker(run_dir)
        say = _trace(root, study, name, key)
        rec = jobs.jobs.get(key)
        try:
            if rec is None:
                rec = self._first(name, kwargs, study, key, folder, jobs, say)
            elif rec.state == "done" and (stored := _answer(folder)) is not None:
                say(f"the same call again: the stored result of job {rec.handle_id}; nothing submitted", job=rec.handle_id)
                return stored
            elif rec.state in ("done", "failed"):
                say(f"the same call again: job {rec.handle_id} ended {rec.slurm_state}; nothing submitted", job=rec.handle_id)
                return _error(rec, folder, again=True)
            else:
                say(f"the same call again: reattached to job {rec.handle_id}, attempt {rec.attempts} of {RETRY_CAP}", job=rec.handle_id)
            return self._wait(name, study, rec, folder, jobs, say)
        except subprocess.CalledProcessError as e:
            said = (e.stderr or e.stdout or "").strip()[-TAIL_CHARS:]
            if rec is not None:
                return self._end(rec, jobs, say, folder, rec.slurm_state or "UNKNOWN", f"sbatch refused the next attempt: {said}")
            return {"error": "BatchJobError", "message": f"sbatch refused the job of {name}, so nothing was submitted: {said}"}
        except OSError as e:
            return {"error": "BatchJobError", "message": f"{name} in the batch lane: {type(e).__name__}: {e}"}

    def close(self) -> None:
        pass                       # a batch lane holds nothing between calls, and never cancels a job

    def _submit(self, study: str, name: str, folder: Path, resources: Mapping[str, Any]) -> str:
        path = folder / "job.sh"
        path.write_text(script(study, name, folder, resources))
        return submit_script(path)

    def _first(self, name: str, kwargs: Dict[str, Any], study: str, key: str, folder: Path, jobs: JobTracker, say) -> JobRecord:
        """Attempt 1: the request written, the job submitted and recorded."""
        resources = {**DEFAULT, "time": hms(BY_NAME[name].timeout_s if name in BY_NAME else 3600), **self.resources}
        folder.mkdir(parents=True, exist_ok=True)
        fn = self.functions[name]
        (folder / "request.json").write_text(json.dumps({"module": fn.__module__, "function": name, "kwargs": kwargs, "hash": key},
                                                        indent=1, default=str, ensure_ascii=False))
        job = self._submit(study, name, folder, resources)
        rec = JobRecord(name=f"fragplace-{study}-{name}", backend="slurm", handle_id=job, workdir=str(folder), tool=name, hash=key,
                        resources=resources, submitted=datetime.now())
        jobs.put(key, rec)
        say(f"submitted job {job}, attempt 1 of {RETRY_CAP}: {resources_text(resources)}", job=job, resources=resources)
        return rec

    def _wait(self, name: str, study: str, rec: JobRecord, folder: Path, jobs: JobTracker, say) -> Dict[str, Any]:
        """Poll until the job ends, submitting again what may be; the call's answer, an error, or the job still running
        at the registry timeout."""
        timeout_s = BY_NAME[name].timeout_s if name in BY_NAME else 3600
        deadline, grace = monotonic() + timeout_s, 0
        while True:
            state = poll(rec.handle_id)
            if state != rec.slurm_state:
                say(f"job {rec.handle_id}: {rec.slurm_state or 'submitted'} to {state}", job=rec.handle_id, state=state)
                rec.slurm_state, rec.state = state, word(state)
                jobs.put(rec.hash, rec)
            if state == "COMPLETED":
                answer = _answer(folder)
                if answer is not None:
                    rec.finished = datetime.now()
                    jobs.put(rec.hash, rec)
                    return answer
                if grace < GRACE_POLLS:
                    grace += 1
                    continue
                return self._end(rec, jobs, say, folder, state, "the job ended without writing result.json, so the call did not finish")
            if state in ACTIVE:
                if monotonic() >= deadline:
                    say(f"no answer within {timeout_s / 60:g} min, the registry timeout; job {rec.handle_id} goes on, {state}", job=rec.handle_id)
                    return {"running": f"{name} is still in job {rec.handle_id}, {state}, after {timeout_s / 60:g} min, its registry timeout; "
                                       "the job goes on and is never cancelled",
                            "job": rec.handle_id, "state": state,
                            "next": "call the same tool with the same arguments again: it reattaches to this job and submits nothing"}
                continue
            if (state in MORE or state in AGAIN) and rec.attempts < RETRY_CAP:
                self._again(name, study, rec, folder, jobs, say, state)
                continue
            why = f"{rec.attempts} of {RETRY_CAP} attempts made" if state in MORE or state in AGAIN else "a state the lane does not submit again"
            return self._end(rec, jobs, say, folder, state, why)

    def _again(self, name: str, study: str, rec: JobRecord, folder: Path, jobs: JobTracker, say, state: str) -> None:
        """The next attempt: twice the time after TIMEOUT, twice the memory after OUT_OF_MEMORY, else as it was."""
        before, resources = dict(rec.resources), dict(rec.resources)
        what = MORE.get(state)
        if what == "time":
            resources["time"] = hms(2 * seconds(before["time"]))
        elif what == "mem_GB":
            resources["mem_GB"] = 2 * float(before["mem_GB"])
        change = f"{what} {before[what]} to {resources[what]}" if what else "as it was"
        old, job = rec.handle_id, self._submit(study, name, folder, resources)
        rec.diagnoses.append(f"attempt {rec.attempts}, job {old}: {state}; submitted again, {change}")
        rec.attempts, rec.handle_id, rec.resources, rec.slurm_state, rec.state = rec.attempts + 1, job, resources, None, "submitted"
        jobs.put(rec.hash, rec)
        say(f"job {old} ended {state}; submitted again as job {job}, attempt {rec.attempts} of {RETRY_CAP}, {change}", job=job, resources=resources)

    def _end(self, rec: JobRecord, jobs: JobTracker, say, folder: Path, state: str, why: str) -> Dict[str, Any]:
        rec.state, rec.slurm_state, rec.finished = "failed", state, datetime.now()
        rec.diagnoses.append(f"attempt {rec.attempts}, job {rec.handle_id}: {state}; {why}")
        jobs.put(rec.hash, rec)
        say(f"job {rec.handle_id} ended {state}: {why}; not submitted again", job=rec.handle_id, state=state)
        return _error(rec, folder)


def _answer(folder: Path) -> Optional[Dict[str, Any]]:
    """The stored result of a request, None until the job has written it whole."""
    try:
        return json.loads((folder / "result.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _tail(path: Path) -> str:
    try:
        return path.read_text(errors="replace").strip()[-TAIL_CHARS:]
    except OSError:
        return ""


def _error(rec: JobRecord, folder: Path, again: bool = False) -> Dict[str, Any]:
    """The answer of a failed request: the Slurm state, what happened at each attempt and the end of the last job's log."""
    log = folder / f"slurm-{rec.handle_id}.out"
    tail = _tail(log)
    return {"error": "BatchJobError", "state": rec.slurm_state, "job": rec.handle_id, "attempts": rec.attempts, "log": str(log),
            "message": (f"{rec.tool} in the batch lane ended {rec.slurm_state}: " + "; ".join(rec.diagnoses)
                        + (". The same call answers this again and submits nothing" if again else "")
                        + (f". The end of its log, {log.name}:\n{tail}" if tail else f". {log.name} is empty or missing")),
            "log_tail": tail}


def _trace(root: Path, study: str, tool: str, key: str) -> Callable[..., None]:
    """say(message, **inputs): one line of the study's trace about this request, under the tool's board step."""
    run = Run(root, study)
    step = BY_NAME[tool].board_steps[0] if tool in BY_NAME else "batch"

    def say(message: str, **inputs: Any) -> None:
        run.event(step, tool, "batch", {"hash": key, **inputs}, "", message=f"batch lane: {message}")
    return say


# ---- inside the job
def run_request(path: Path) -> int:
    """Make the call request.json names, here, and write its answer whole to result.json beside it; a call that
    raises answers with the end of its traceback, as the worker does."""
    request = json.loads(Path(path).read_text())
    try:
        fn = getattr(importlib.import_module(request["module"]), request["function"])
        answer = fn(**request.get("kwargs", {}))
    except Exception:  # noqa: BLE001 - the answer says what failed; the lane reads it like any other
        answer = {"error": "ComputeNodeError", "message": traceback.format_exc()[-TAIL_CHARS:]}
    out = Path(path).with_name("result.json")
    part = out.with_name("result.json.part")
    part.write_text(json.dumps(answer, default=str, ensure_ascii=False))
    os.replace(part, out)
    return 0


def main(argv: Optional[list] = None) -> None:
    p = argparse.ArgumentParser(prog="python -m fragplace.execution.batch", description="the batch lane's side, inside a job")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="make the call of request.json here and write result.json beside it")
    r.add_argument("request", type=Path)
    a = p.parse_args(argv)
    limit_threads()      # before numpy or torch loads; the job script has set the counts from SLURM_CPUS_PER_TASK
    sys.exit(run_request(a.request))


if __name__ == "__main__":
    main()
