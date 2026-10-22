"""The MCP server: one tool per registry entry, the two study operations open to every agent and the one for the
orchestrator alone, so the agents call tools by name and never by code.

Each tool is the agent-facing function of study.calls: it names its study, takes only what an agent decides, and
answers with a summary; the records stay on disk. Claude Code publishes the tools of this plugin as
mcp__plugin_fragplace_fragplace__<name>. Lives inside the package, not in a top-level mcp/ folder, because that
name would shadow the MCP SDK's own package. Run: fragplace-server. Needs the MCP Python SDK, mcp 1.x. With
--list it prints the tools and exits without the SDK, which CI uses as a smoke test.

The server computes nothing heavy on a login node. Each heavy tool of execution.srun runs in the lane route()
names at the call: here, in the session's one worker on a compute node, which is this module run with --worker
under srun, started on the first heavy call and kept until it is idle or the session ends, or in one sbatch job of
execution.batch. Until the human passes approve the plan, the lane is srun.choose's default; after it, the rule
the hpc-specialist proposed with compute_plan for that tool, read from the study's records, where auto weighs the
call's expected minutes against the rule's threshold. The other tools and the operations read and write records
and run here.
"""
from __future__ import annotations

import argparse
import atexit
import functools
import json
import os
import platform
import select
import sys
import traceback
from typing import Any, Callable, Dict, Optional, Tuple

from ..execution.local import limit_threads  # noqa: E402

limit_threads()      # before numpy or torch loads

from ..execution import srun  # noqa: E402
from ..registry.tools import BY_NAME, OPERATIONS, ORCHESTRATOR_OPERATIONS, REGISTRY  # noqa: E402
from ..runtime.journal import default_root  # noqa: E402

WORKER_COMMAND = [sys.executable, "-m", "fragplace.mcp.server", "--worker"]
_LANES: Dict[str, srun.Lane] = {}      # one lane of each kind per server, so one worker per session
# The force calls one item of a heavy tool costs, inferred, not measured on a study; compute_plan's own count wins
# when its timing gives one. A relaxation of a placed pair takes about 150 BFGS steps; a picked state's references
# are four relaxations; the committee asks each member three energies; sites, the gate and SOAP call no potential.
FORCE_CALLS = {"site_enumeration": 0, "pull_force_screen": 1, "minima_hopping": 600, "relaxation": 150, "anomaly_filter": 0,
               "soap_clustering": 0, "uncertainty_estimation": 3, "reference_energies": 600}
REFERENCE_RELAXATIONS = 4      # slab with A, slab with B, A and B alone, for each picked state
# What a heavy call writes besides its own key of calls.MADE_BY and the keys after it; left out of the records a
# request's hash reads, so a repeated call finds the job its first call submitted.
WRITES = {"relaxation": ("order",), "minima_hopping": ("hopped", "options"), "compute_plan": ("compute_plan", "compute_timing")}


def _server_class():
    try:
        from mcp.server.fastmcp import FastMCP  # mcp 1.x
        return FastMCP
    except ImportError:
        try:
            from mcp.server import MCPServer  # mcp 2
            return MCPServer
        except ImportError as e:  # pragma: no cover
            raise ImportError('pip install "mcp[cli]>=1.2,<2"') from e


def description(name: str) -> str:
    if name in OPERATIONS:
        return f"{OPERATIONS[name][0].upper()}{OPERATIONS[name][1:]}. Open to every agent."
    if name in ORCHESTRATOR_OPERATIONS:
        return f"{ORCHESTRATOR_OPERATIONS[name][0].upper()}{ORCHESTRATOR_OPERATIONS[name][1:]}. For the orchestrator alone."
    spec = BY_NAME[name]
    return (f"{spec.purpose} Board steps: {', '.join(spec.board_steps)}. Allowed roles: {', '.join(spec.allowed_roles)}."
            + (f" Needs the '{spec.checkpoint_gate}' checkpoint, which only the human passes." if spec.checkpoint_gate else "")
            + " Answers with a summary; a call that cannot run says what the human, or an earlier tool, must do first.")


def lane(choice: str, rule: Optional[Dict[str, Any]] = None, records: str = "") -> srun.Lane:
    """The server's lane of that kind: local and the worker made on first use and kept, so one worker per session; a
    batch lane made for each call, with its rule's resources and the digest of the study's records it reads."""
    from ..study import calls
    if choice == "batch":
        return srun.lane(choice, calls.FUNCTIONS, WORKER_COMMAND, rule, records)
    if choice not in _LANES:
        _LANES[choice] = srun.lane(choice, calls.FUNCTIONS, WORKER_COMMAND)
    return _LANES[choice]


def close_lanes() -> None:
    """End what the lanes hold, the worker and its job among it; at exit, and between tests."""
    while _LANES:
        _LANES.popitem()[1].close()


def study_lane(study: Optional[str]) -> Optional[str]:
    """The lane the study's options name, set with fragplace init --lane; None when they name none."""
    if not study or not (default_root() / "runs" / study / "artifacts.json").is_file():
        return None
    from ..study.store import Study
    return Study(default_root(), study).options.get("lane")


def _study(study: Optional[str]):
    """The study's records, None when it has none."""
    if not study or not (default_root() / "runs" / study / "artifacts.json").is_file():
        return None
    from ..study.store import Study
    return Study(default_root(), study)


def items(c, name: str, kwargs: Dict[str, Any]) -> Optional[int]:
    """The items one call of a heavy tool takes, from the study's records: the candidates it relaxes, screens, gates
    or clusters; None while the step before it has not run, when the call could not run either."""
    d = c.data
    if name == "site_enumeration":
        return 1 if "mlip" in d else None
    if name == "pull_force_screen":
        return len(d["placed"]) if "placed" in d else None
    if name == "minima_hopping":
        return int(kwargs.get("n_hops", 5)) if "screens" in d else None
    if name == "relaxation":
        return 1 + len(c.ordered()) if "gates_before" in d and "queue" in d else None
    if name == "anomaly_filter":
        if kwargs.get("stage") == "before_relaxation":
            return len(c.queued()) if "screens" in d else None
        return len(d["relaxed"]) if "relaxed" in d else None
    if name == "soap_clustering":
        return sum(1 for g in d["gates"] if g["passed"]) if "gates" in d else None
    if name == "uncertainty_estimation":
        return len(d["kept"]) if "kept" in d else None
    if name == "reference_energies":
        from ..runtime import checkpoints
        pick = [x for x in checkpoints.passed(c.run.dir) if x.checkpoint == "pick up to five final states"]
        return len(pick[-1].chosen) if pick and "ranked" in d else None
    return None


def expected_minutes(c, name: str, kwargs: Dict[str, Any]) -> Optional[float]:
    """A call's expected minutes in one process: the seconds per force call compute_plan measured, times the force
    calls of one item, times the call's items; None without the timing or the items. The force calls of one item are
    the approved plan's estimate for the tool, else compute_timing's count for a relaxation, else FORCE_CALLS."""
    timing = c.data.get("compute_timing") or {}
    n = items(c, name, kwargs)
    if not timing.get("s_per_force_call") or n is None:
        return None
    estimate = ((c.data.get("compute_plan") or {}).get("estimates") or {}).get(name) or {}
    given = timing.get("force_calls_per_item")           # compute_plan's force calls of one relaxation, when it gives them
    per_item = FORCE_CALLS.get(name, 0)
    if estimate.get("force_calls_per_item") is not None:
        per_item = estimate["force_calls_per_item"]
    elif isinstance(given, (int, float)) and name in ("relaxation", "reference_energies"):
        per_item = given * (1 if name == "relaxation" else REFERENCE_RELAXATIONS)
    elif isinstance(given, dict) and given.get(name) is not None:
        per_item = given[name]
    return float(timing["s_per_force_call"]) * float(per_item) * n / 60


def route(name: str, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """The lane of one heavy call and the rule it follows. Before the human passes approve the plan, or for a tool
    the plan names no rule for, the default lane of srun.choose. After it, the approved rule's: batch, the worker,
    or auto, which sends the call to batch when its expected minutes pass the rule's batch_above_min and to the
    default lane otherwise. A call whose items are not known yet cannot run, so it goes to the default lane, where it
    answers at once with what must run first; no job is submitted for it."""
    default = srun.choose(study_lane(kwargs.get("study")))
    c = _study(kwargs.get("study"))
    from ..study.store import approved_rule
    rule = approved_rule(c, name) if c is not None else {}
    if not rule:
        return default, {}
    wanted = rule.get("lane")
    minutes = expected_minutes(c, name, kwargs)
    if items(c, name, kwargs) is None:
        choice, why = default, "its items are not known yet, so it cannot run"
    elif wanted == "batch":
        choice, why = "batch", "the approved rule"
    elif wanted == "worker":
        choice, why = srun.choose("worker"), "the approved rule"
    elif minutes is not None and minutes > float(rule.get("batch_above_min", srun.BATCH_ABOVE_MIN)):
        choice, why = "batch", f"auto: {minutes:.1f} min expected, above {rule.get('batch_above_min')} min"
    else:
        choice, why = default, (f"auto: {minutes:.1f} min expected, within {rule.get('batch_above_min')} min" if minutes is not None
                                else "auto: no timing to estimate it")
    c.run.event(BY_NAME[name].board_steps[0], name, "server", {"rule": rule}, "", message=f"lane {choice} for {name}: {why}")
    return choice, rule


def records(study: str, name: str, kwargs: Dict[str, Any]) -> str:
    """The digest of the study's records a request reads: artifacts.json without the call's own outputs, the keys
    after them and the agents' notes, with checkpoints.json and PROJECT.md. A repeated call computes the same digest
    while its job runs and after it ends, so the batch lane finds that job; an earlier step run again changes it."""
    from ..runtime.journal import content_hash
    from ..study import calls
    c = _study(study)
    if c is None:
        return ""
    keys = [k for k, _ in calls.MADE_BY]
    made = {t: k for k, t in calls.MADE_BY}
    own = "gates_before" if name == "anomaly_filter" and kwargs.get("stage") == "before_relaxation" else made.get(name)
    later = set(keys[keys.index(own):]) if own else set()
    skip = later | {x for k in later for x in calls.DOWNSTREAM.get(k, [])} | {"notes"} | set(WRITES.get(name, ()))
    text = {f: (c.run.dir / f).read_text() if (c.run.dir / f).exists() else "" for f in ("checkpoints.json", "PROJECT.md")}
    return content_hash({"data": {k: v for k, v in c.data.items() if k not in skip}, **text})


def dispatched(name: str, fn: Callable[..., Dict[str, Any]]) -> Callable[..., Dict[str, Any]]:
    """fn as the server publishes a heavy tool: run in the lane route() names at each call. The signature stays
    fn's, so the tool's schema does not change."""
    @functools.wraps(fn)
    def call(**kwargs: Any) -> Dict[str, Any]:
        try:
            choice, rule = route(name, kwargs)
        except ValueError as e:
            return {"error": "ValueError", "message": str(e)}
        return lane(choice, rule, records(kwargs.get("study"), name, kwargs) if choice == "batch" else "").run(name, kwargs)
    return call


def worker() -> None:
    """The worker's side, on the compute node: one request per line on stdin, each answered with one line on stdout
    after srun.LINE, as srun.WorkerLane reads them; calculators and models stay loaded between requests. Whatever
    else is printed, by C libraries too, goes to stderr. It leaves after FRAGPLACE_SRUN_IDLE_MIN minutes without a
    request, or when its stdin closes, and says so first. stdin is read as raw bytes, so the wait can time out."""
    answers = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
    os.dup2(2, 1)

    def say(**message: Any) -> None:
        try:
            answers.write(srun.LINE + json.dumps(message, default=str) + "\n")
            answers.flush()
        except OSError:
            pass                          # the server is gone; stdin closes next

    from ..study import calls
    idle = srun.idle_seconds()
    say(ready=platform.node())
    pending = b""
    while True:
        while b"\n" not in pending:
            if not select.select([0], [], [], idle)[0]:
                say(bye=f"no request for {idle / 60:g} min")
                return
            chunk = os.read(0, 1 << 16)
            if not chunk:
                say(bye="stdin closed")
                return
            pending += chunk
        line, pending = pending.split(b"\n", 1)
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            answer = calls.FUNCTIONS[request["name"]](**request.get("kwargs", {}))
        except Exception:  # noqa: BLE001 - one failed request must not end the worker; the traceback's end is the answer
            answer = {"error": "ComputeNodeError", "message": traceback.format_exc()[-srun.TAIL_CHARS:]}
        say(answer=answer)


def build(root=None):
    """The server; runs/ lives under root, FRAGPLACE_ROOT or the repository by default."""
    if root:
        os.environ["FRAGPLACE_ROOT"] = str(root)
    from ..study import calls
    server = _server_class()("fragplace")
    for name, fn in calls.FUNCTIONS.items():
        tool = dispatched(name, fn) if name in srun.HEAVY else fn
        server.tool(name=name, description=description(name) + "\n\n" + (fn.__doc__ or ""))(tool)
    return server


def main() -> None:
    p = argparse.ArgumentParser(prog="fragplace-server")
    p.add_argument("--list", action="store_true", help="print the tools the server would expose and exit")
    p.add_argument("--worker", action="store_true", help="answer heavy calls from stdin on a compute node; what srun runs")
    a = p.parse_args()
    if a.list:
        for spec in REGISTRY:
            print(f"{spec.name:24s} v{spec.version} {spec.status:9s} lane {spec.lane:6s} gate {spec.checkpoint_gate or '-':28s} roles {', '.join(spec.allowed_roles)}"
                  + ("; heavy: the default lane, or its approved compute rule's" if spec.name in srun.HEAVY else ""))
        for name in OPERATIONS:
            print(f"{name:24s} operation, every role")
        for name in ORCHESTRATOR_OPERATIONS:
            print(f"{name:24s} operation, the orchestrator alone")
        return
    if a.worker:
        worker()
        return
    atexit.register(close_lanes)
    build().run()


if __name__ == "__main__":
    main()
