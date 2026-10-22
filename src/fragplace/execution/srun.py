"""Where a heavy call runs, its lane, and the srun command that puts it on a compute node, so a login node
computes nothing.

A Lane runs one call by tool name and keyword arguments and answers as the tool does; close ends whatever the
lane holds. Three lanes are built. local runs the call in the calling process. worker keeps one long-lived process
for the session under srun on a compute node, started on the first heavy call, so a session holds one job and not
one per call; the worker keeps calculators and models loaded between calls and leaves after
FRAGPLACE_SRUN_IDLE_MIN minutes without one, or when its stdin closes, its job with it. A call that gives no answer
within its registry timeout stops the worker; when srun made the allocation, that ends the job too. batch, in
execution.batch, submits one sbatch job per heavy call, never one per structure, for a call too long to hold the
session.

choose() names the default lane: the study's own setting, else FRAGPLACE_LANE, else worker when FRAGPLACE_SRUN holds
srun's options, "--partition=interactive --cpus-per-task=4 --mem=8G --time=02:00:00" for example, or
FRAGPLACE_SLURM_JOB names an allocation the human holds, else local. Inside a Slurm job, where SLURM_JOB_ID is set,
every call is local. With FRAGPLACE_SLURM_JOB the worker runs as a step of that job, srun --jobid=<job> --overlap
-n1, not in a new one. The worker refuses a root on a node's own disk, /tmp among them: a compute node sees its own
/tmp, not the login node's. Once the human has approved a compute plan, its rule for a tool overrides the default
lane, as mcp.server routes the call; TABLE is what compute_plan recommends from a call's expected minutes.
"""
from __future__ import annotations

import json
import os
import queue
import shlex
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Mapping, Optional, Protocol

from ..registry.tools import BY_NAME, REGISTRY
from ..runtime.journal import default_root
from .local import BLAS_THREADS_MAX

ENV, JOB_ENV, LANE_ENV = "FRAGPLACE_SRUN", "FRAGPLACE_SLURM_JOB", "FRAGPLACE_LANE"
IDLE_ENV, IDLE_MIN = "FRAGPLACE_SRUN_IDLE_MIN", 20.0     # a worker without a call for this long leaves, its job with it
LANES = ("local", "worker", "batch")                     # a default lane; a compute plan's rule may also say auto
RULE_LANES = ("worker", "batch", "auto")                 # a rule's lane: never local, which on a login node computes there
# Every tool off the laptop lane, and three on it that still compute: the gate loads the potential, the sites come
# from ACAT, the clusters from dscribe's SOAP.
HEAVY = frozenset({t.name for t in REGISTRY if t.lane != "laptop"} | {"anomaly_filter", "site_enumeration", "soap_clustering"})
LINE = "FRAGPLACE-WORKER "     # starts each line of the worker's protocol on its stdout
START_S = 3600                 # the queue's wait for an allocation and the imports, before the worker says it is ready
STOP_S = 10                    # how long a worker may take to leave before srun is terminated, then killed
TAIL_LINES, TAIL_CHARS = 200, 2000   # how much of the worker's error output a failure keeps and returns
NODE_LOCAL = ("/tmp", "/var/tmp", "/dev/shm")   # each node's own disk, not shared between the login node and a compute node
THREAD_VARS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")
# The lane a heavy call's expected minutes recommend: the code's default table. Every threshold is inferred from
# one measurement, about 1.5 s per MACE-MP-small force call on 146 atoms with 2 CPUs, and gives way to a measured time.
TABLE = (
    (10.0, "worker", "a few minutes, such as a screen of single points: the session's worker, or a step of a held allocation, "
                     "already holds the CPUs and the loaded potential, and a job would wait in the queue longer than it runs"),
    (70.0, "worker", "up to about an hour, such as one to ten relaxations: still the worker, so the human sees the step end within "
                     "the session"),
    (None, "batch", "longer, such as ten to two hundred relaxations: one sbatch job of 8 to 16 CPUs for the whole call, the pool "
                    "inside it and each relaxation cached as it ends, so a resubmitted job goes on from there; never one job per structure"),
)
NEVER = "never the login node: no potential is imported and no force call made there"
BATCH_ABOVE_MIN = max(bound for bound, _, _ in TABLE if bound is not None)   # where the table turns to batch, inferred
BATCH_CPUS = (8, 16)                                                         # the table's job, inferred


def recommend(minutes: Optional[float]) -> tuple:
    """(lane, why) the table gives a call of the expected minutes; auto when they are not known yet, so the call
    decides once its items are."""
    if minutes is None:
        return "auto", (f"the items are not known until the step before has run, so the call decides: batch above "
                        f"{BATCH_ABOVE_MIN:g} min, else the default lane")
    for bound, name, why in TABLE:
        if bound is None or minutes <= bound:
            return name, why
    raise AssertionError("the table ends in a row without a bound")


def choose(setting: Optional[str] = None, env: Optional[Mapping[str, str]] = None) -> str:
    """The lane of the heavy calls: setting, the study's own, else FRAGPLACE_LANE, else worker when FRAGPLACE_SRUN or
    FRAGPLACE_SLURM_JOB asks for a compute node, else local; local inside a Slurm job, which is on one already."""
    env = os.environ if env is None else env
    if env.get("SLURM_JOB_ID"):
        return "local"
    wanted = (setting or env.get(LANE_ENV, "")).strip()
    lane = wanted or ("worker" if env.get(ENV, "").strip() or env.get(JOB_ENV, "").strip() else "local")
    if lane not in LANES:
        raise ValueError(f"no lane {lane!r}; built: {', '.join(LANES)}" + (". auto is a lane of a compute plan's rule only" if lane == "auto" else ""))
    return lane


def options(env: Optional[Mapping[str, str]] = None) -> List[str]:
    """srun's options: FRAGPLACE_SRUN's, after --jobid=<job> --overlap when FRAGPLACE_SLURM_JOB names an allocation
    the human holds, so the command runs as a step of that job, and then -n1 unless the options name the tasks: a
    step takes the job's task count, and a worker per task would all read the one stdin."""
    env = os.environ if env is None else env
    job = env.get(JOB_ENV, "").strip()
    own = shlex.split(env.get(ENV, ""))
    if not job:
        return own
    tasks = any(x in ("-n", "--ntasks") or x.startswith("--ntasks=") or (x.startswith("-n") and x[2:].isdigit()) for x in own)
    return [f"--jobid={job}", "--overlap"] + ([] if tasks else ["-n1"]) + own


def node_local(root: Path) -> bool:
    """Whether root lies on a node's own disk, NODE_LOCAL, which the login node and a compute node do not share."""
    root = Path(os.path.abspath(root))
    return any(root == Path(p) or Path(p) in root.parents for p in NODE_LOCAL)


def idle_seconds(env: Optional[Mapping[str, str]] = None) -> float:
    """How long a worker waits for its next call before it leaves: FRAGPLACE_SRUN_IDLE_MIN minutes, else IDLE_MIN."""
    env = os.environ if env is None else env
    text = env.get(IDLE_ENV, "").strip()
    return 60 * (float(text) if text else IDLE_MIN)


def argv(command: List[str], opts: List[str]) -> List[str]:
    """srun <options> --quiet <command>; --quiet keeps srun's queue messages out of the command's output."""
    return ["srun", *opts, "--quiet", *command]


def cpus_per_task(opts: List[str]) -> Optional[int]:
    """The CPUs per task the options ask for, in any of srun's spellings, the last one winning as in srun; None
    when they name none."""
    found = None
    for k, x in enumerate(opts):
        if x in ("-c", "--cpus-per-task") and k + 1 < len(opts):
            found = opts[k + 1]
        elif x.startswith("--cpus-per-task="):
            found = x.split("=", 1)[1]
        elif x.startswith("-c") and x[2:].isdigit():
            found = x[2:]
    return int(found) if found and found.isdigit() else None


def environment(opts: List[str], root: Path, env: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """The environment srun hands on to the command: this one, with FRAGPLACE_ROOT set to the caller's root, and the
    thread counts set from --cpus-per-task when the options give it, else left out, so limit_threads on the compute
    node counts the step's own CPUs. The login node's budget would otherwise travel along, since limit_threads keeps
    a count that is already set."""
    out = {k: v for k, v in (os.environ if env is None else env).items() if k not in THREAD_VARS}
    out["FRAGPLACE_ROOT"] = str(root)
    n = cpus_per_task(opts)
    if n:
        out.update(OMP_NUM_THREADS=str(n), MKL_NUM_THREADS=str(n), OPENBLAS_NUM_THREADS=str(min(n, BLAS_THREADS_MAX)))
    return out


class Lane(Protocol):
    """Where a heavy call runs. run answers as the tool does, with a dict, and answers a failure of the lane itself
    as {"error": ..., "message": ...} instead of raising; close ends whatever the lane holds."""
    name: str

    def run(self, name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]: ...
    def close(self) -> None: ...


class LocalLane:
    """The call in this process: the laptop lane, and every call inside a Slurm job."""
    name = "local"

    def __init__(self, functions: Mapping[str, Callable[..., Dict[str, Any]]]):
        self.functions = functions

    def run(self, name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return self.functions[name](**kwargs)

    def close(self) -> None:
        pass


class WorkerLane:
    """One worker for the session, command under srun: started on the first call, reused for every later one,
    started again when it has left or died; calls reach it one at a time, each with its registry timeout.

    The protocol is JSON lines. On the worker's stdin, one request per line, {"name": ..., "kwargs": ...}. On its
    stdout, each line after LINE: {"ready": <host>} once, then {"answer": ...} per request, and {"bye": <why>} when
    it leaves, idle or with its stdin closed, so a request sent meanwhile is known not to have run and is sent to a
    new worker. Closing its stdin ends it; a worker that does not leave is terminated with its srun. A call without an
    answer within its registry timeout stops the worker, and when srun made the allocation, the job ends with it; a
    step of FRAGPLACE_SLURM_JOB ends alone and the human's job goes on."""
    name = "worker"

    def __init__(self, command: List[str], env: Optional[Mapping[str, str]] = None):
        self.command, self.env = command, env
        self.proc: Optional[subprocess.Popen] = None
        self.messages: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()
        self.tail: Deque[str] = deque(maxlen=TAIL_LINES)
        self.readers: List[threading.Thread] = []
        self.job: Optional[str] = None       # the allocation the worker is a step of, when the human holds one
        self.lock = threading.Lock()

    def run(self, name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        timeout_s = BY_NAME[name].timeout_s
        with self.lock:
            for _ in range(2):          # once more when the worker left, idle, as the request reached it
                if self.proc is None or self.proc.poll() is not None:
                    failed = self._start()
                    if failed:
                        return failed
                try:
                    self.proc.stdin.write(json.dumps({"name": name, "kwargs": kwargs}, default=str) + "\n")
                    self.proc.stdin.flush()
                except OSError:
                    self._stop()
                    continue
                message = self._next(timeout_s)
                if message and "answer" in message:
                    return message["answer"]
                if message and "bye" in message:
                    self._stop()
                    continue
                if message == {}:
                    ended = f"its step of job {self.job} ended, and the job goes on" if self.job else "the job srun made for it ended"
                    return self._fail(f"{name} gave no answer within {timeout_s / 60:g} min, its registry timeout, so the worker was "
                                      f"stopped and {ended}")
                return self._fail(f"the worker ended during {name}")
            return self._fail("the worker left twice before it answered")

    def close(self) -> None:
        with self.lock:
            self._stop()

    def _start(self) -> Optional[Dict[str, Any]]:
        """srun the worker and wait for its ready line; None when it is ready, else the answer that says why not."""
        root = default_root()
        if node_local(root):
            return {"error": "ComputeNodeError", "message": f"the root {root} is on this node's own disk, and the worker's node has its "
                                                              "own: set FRAGPLACE_ROOT to a folder on a shared filesystem"}
        opts = options(self.env)
        self.job = next((x.split("=", 1)[1] for x in opts if x.startswith("--jobid=")), None)
        self.messages, self.tail = queue.Queue(), deque(maxlen=TAIL_LINES)
        try:
            self.proc = subprocess.Popen(argv(self.command, opts), env=environment(opts, root, self.env), stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", bufsize=1)
        except OSError as e:
            self.proc = None
            return {"error": "ComputeNodeError", "message": f"srun did not start: {e}"}
        self.readers = [threading.Thread(target=_read_messages, args=(self.proc.stdout, self.messages), daemon=True),
                        threading.Thread(target=_keep_tail, args=(self.proc.stderr, self.tail), daemon=True)]
        for t in self.readers:
            t.start()
        message = self._next(START_S)
        if message and "ready" in message:
            return None
        return self._fail(f"the worker did not start within {START_S / 60:g} min" if message == {} else "the worker did not start")

    def _next(self, timeout_s: float) -> Optional[Dict[str, Any]]:
        """The worker's next message; {} when none came in time, None when its output ended."""
        try:
            return self.messages.get(timeout=timeout_s)
        except queue.Empty:
            return {}

    def _fail(self, what: str) -> Dict[str, Any]:
        """Stop the worker and answer with why, and with the end of its error output."""
        self._stop()
        tail = "\n".join(self.tail).strip()[-TAIL_CHARS:]
        return {"error": "ComputeNodeError", "message": what + (f"; its error output ends:\n{tail}" if tail else "")}

    def _stop(self) -> None:
        """Close the worker's stdin, which ends it and a job srun made for it; terminate srun when it lingers."""
        p, self.proc = self.proc, None
        if p is None:
            return
        try:
            p.stdin.close()
        except OSError:
            pass
        try:
            p.wait(timeout=STOP_S)
        except subprocess.TimeoutExpired:
            p.terminate()                 # srun passes it on to the step and gives a job it made back
            try:
                p.wait(timeout=STOP_S)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        for t in self.readers:
            t.join(timeout=STOP_S)


def _read_messages(stream, messages: "queue.Queue[Optional[Dict[str, Any]]]") -> None:
    """The worker's protocol lines as messages, then None when its output ends."""
    for line in stream:
        if line.startswith(LINE):
            try:
                messages.put(json.loads(line[len(LINE):]))
            except json.JSONDecodeError:
                continue
    messages.put(None)


def _keep_tail(stream, tail: Deque[str]) -> None:
    for line in stream:
        tail.append(line.rstrip("\n"))


def lane(choice: str, functions: Mapping[str, Callable[..., Dict[str, Any]]], worker_command: List[str],
         resources: Optional[Mapping[str, Any]] = None, records: str = "") -> Lane:
    """The lane named: local over functions, worker running worker_command under srun, or batch, one sbatch job for
    the call with the resources of its rule and records, the digest of the study's records its request hash reads."""
    if choice == "local":
        return LocalLane(functions)
    if choice == "worker":
        return WorkerLane(worker_command)
    if choice == "batch":
        from .batch import BatchLane
        return BatchLane(functions, resources, records)
    raise ValueError(f"no lane {choice!r}; built: {', '.join(LANES)}")
