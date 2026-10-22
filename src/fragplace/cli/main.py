"""Command line: list the registry, check the documents against the data module, start a study, run it to the
next checkpoint, record the human's choice there, and show where it stands.

The root is the folder that holds runs/, never runs/ itself or a folder inside it. When execution.srun chooses the
worker lane, FRAGPLACE_SRUN or FRAGPLACE_SLURM_JOB set outside a Slurm job or the study's lane, init --example and
run start themselves again under srun on a compute node, one job each, since both relax structures.
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from ..execution.local import limit_threads
from ..runtime.journal import default_root

limit_threads()      # before numpy or torch loads

from ..execution import srun  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
# the init flags passed on to init_study by keyword, each with its keyword there
TO_INIT_STUDY = {"--fragment-a": "fragment_A_vacuum", "--fragment-b": "fragment_B_vacuum", "--facet": "facet"}


def check_root(root: Path, lane: Optional[str] = None) -> None:
    """The root is the folder that holds runs/. A root named runs, or inside a runs/ folder, puts the study in
    runs/<x>/runs/<study>, as a guide that set FRAGPLACE_ROOT to runs/_demo once did. In the worker lane, the one
    given or the environment's, a root on a node's own disk, /tmp among them, is refused as well: the compute node
    would see its own."""
    if "runs" in root.parts:
        holder = Path(*root.parts[:root.parts.index("runs")])
        sys.exit(f"the root {root} is a runs/ folder or lies inside one. The root is the folder that holds runs/, here {holder}: "
                 f"pass --root {holder} or set FRAGPLACE_ROOT to it.")
    try:
        lane = lane or srun.choose()
    except ValueError:
        return                            # the lane's own error comes where the lane is used
    if lane in ("worker", "batch") and srun.node_local(root):
        sys.exit(f"the root {root} is on this node's own disk, and a compute node has its own. In the {lane} lane the root must be "
                 f"on a shared filesystem: pass --root or set FRAGPLACE_ROOT to a folder there.")


def existing(args) -> Path:
    """runs/<study> under the root; a command on a study that does not exist stops instead of making it."""
    run_dir = args.root / "runs" / args.study
    if not run_dir.is_dir():
        sys.exit(f"no study {args.study} under {args.root / 'runs'}; start one with fragplace init {args.study}")
    return run_dir


def on_compute_node(args, setting: Optional[str]) -> None:
    """Start this command again under srun when the lane, the study's setting or the environment's, is the worker;
    inside a Slurm job it is local. The command line has no batch lane of its own: a whole run is one command, so in
    the batch lane it goes on a compute node under srun as well. srun replaces this process, so the output and the
    exit code are the command's."""
    try:
        if srun.choose(setting) == "local":
            return
    except ValueError as e:
        sys.exit(str(e))
    check_root(args.root, "worker")       # the study's own lane may ask for the worker when the environment does not
    opts = srun.options()
    command = srun.argv([sys.executable, "-m", "fragplace.cli.main", *args.argv], opts)
    print(f"on a compute node: srun {' '.join(opts)}", file=sys.stderr, flush=True)
    try:
        os.execvpe(command[0], command, srun.environment(opts, args.root))
    except OSError as e:
        sys.exit(f"the lane is the worker but srun did not start: {e}")


def cmd_registry(_):
    from ..registry.tools import REGISTRY
    for t in REGISTRY:
        print(f"{t.name:24s} {t.status:9s} steps {', '.join(t.board_steps)}")


def cmd_check(_):
    py = sys.executable
    src = ROOT / "docs" / "figures" / "src"
    rc = subprocess.call([py, str(src / "board_tables.py"), "--check"])
    rc |= subprocess.call([py, str(src / "board_check.py")])
    rc |= subprocess.call([py, "-m", "pytest", "-q", str(ROOT / "tests")])
    sys.exit(rc)


def bond_question(adsorbate: str) -> str:
    """What init says without a usable --bond: the adsorbate's atoms by index and element, never a coordinate, so the
    human can name the bond to break."""
    from ase.io import read
    try:
        symbols = read(adsorbate).get_chemical_symbols()
    except Exception as e:  # noqa: BLE001 - any reader error means the same to the human: the file did not read
        return f"cannot read the adsorbate {adsorbate}: {type(e).__name__}: {e}"
    rows = "\n".join(f"  {k} {s}" for k, s in enumerate(symbols))
    return (f"name the bond to break with --bond i,j, two atom indices in the adsorbate, A's side first; A keeps the binding atom. "
            f"The atoms of {adsorbate}:\n{rows}")


def cmd_init(args):
    options = {"minima_hopping": args.minima_hopping, "max_steps": args.max_steps, "n_hops": args.n_hops}
    if args.lane:
        options["lane"] = args.lane
    given = {flag: getattr(args, flag[2:].replace("-", "_")) for flag in TO_INIT_STUDY}
    given = {flag: value for flag, value in given.items() if value}
    if given and not args.slab:
        sys.exit(f"{', '.join(given)}: only with --slab, --adsorbate, --initial-state and --bond")
    if args.example:
        artifacts = args.root / "runs" / args.study / "artifacts.json"
        if artifacts.exists() and "inputs" in json.loads(artifacts.read_text()):
            sys.exit(f"study {args.study} already has inputs at {artifacts.parent}")
        on_compute_node(args, args.lane)
        from ..study.example import build_example
        c = build_example(args.root, args.study, args.calculator, options)
        print(f"example study {args.study} made at {c.run.dir}: OH on Pt(111) relaxed with {args.calculator}; "
              f"PROJECT.md carries test values for every open decision")
    elif args.slab:
        from ..study.example import init_study
        if not (args.adsorbate and args.initial_state):
            sys.exit("init with inputs needs --slab, --adsorbate, --initial-state and --bond")
        try:
            bond = tuple(int(x) for x in args.bond.split(","))
        except (AttributeError, ValueError):
            bond = ()
        if len(bond) != 2:
            sys.exit(bond_question(args.adsorbate))
        missing = [flag for flag in given if TO_INIT_STUDY[flag] not in inspect.signature(init_study).parameters]
        if missing:
            sys.exit(f"this fragplace cannot take {', '.join(missing)} yet: init_study has no parameter "
                     f"{', '.join(TO_INIT_STUDY[f] for f in missing)}. Init without them, or update fragplace.")
        energies = [float(x) for x in args.energies.split(",")] if args.energies else None
        c = init_study(args.root, args.study, args.slab, args.adsorbate, args.initial_state, bond, energies, options,
                       **{TO_INIT_STUDY[flag]: value for flag, value in given.items()})
        print(f"study {args.study} made at {c.run.dir}; fill PROJECT.md there: protocol, protocol_reason and every decision "
              f"(fragplace decisions {args.study}), then fragplace run {args.study}")
    else:
        from ..runtime.journal import Run
        run = Run(args.root, args.study)
        project = Path(args.root) / "PROJECT.md"
        if project.exists():
            (run.dir / "PROJECT.md").write_text(project.read_text())
        print(f"study {args.study} made at {run.dir}")


def cmd_run(args):
    from ..errors import CheckpointPending, FragPlaceError
    from ..runtime import state
    from ..study import rollout
    from ..study.calls import MADE_BY
    from ..study.store import Study, briefing
    existing(args)
    c = Study(args.root, args.study)
    if "inputs" not in c.data:
        sys.exit(f"study {args.study} has no inputs: fragplace init {args.study} --example, or with --slab and the rest")
    made = [tool for key, tool in MADE_BY if key in c.data]
    if made and not state.path(c.run.dir).exists():
        sys.exit(f"study {args.study} ran from the chat, {', '.join(made)}, and has no state.json, so fragplace run would start "
                 f"again at the prompt step. Go on in the chat, or start a new study.")
    on_compute_node(args, c.options.get("lane"))
    try:
        result = rollout.run(c.run.dir, args.study, c.invoke, use_minima_hopping=bool(c.options.get("minima_hopping")))
    except CheckpointPending as e:
        print(f"\nstopped at the checkpoint: {e.name}\n")
        print(briefing(args.root, args.study, e.name))
        print(f"\nrecord the choice: fragplace approve {args.study} \"{e.name}\" --reason \"...\""
              + (" --chosen <id> ..." if e.name == "pick up to five final states" else
                 " [--chosen lit:0]" if e.name == "approve settings" else
                 " [--chosen <id> ..., to keep only these]" if e.name == "review flagged cases" else ""))
        return
    except FragPlaceError as e:
        sys.exit(f"stopped: {type(e).__name__}: {e}")
    print(f"study {args.study}: {result}; report at {c.run.dir / 'report.md'}")


def cmd_approve(args):
    from ..errors import FragPlaceError
    from ..runtime import state
    from ..study.human import human_name
    from ..study.store import record_choice
    run_dir = existing(args)
    try:
        choice = record_choice(args.root, args.study, args.checkpoint, args.chosen or [], args.reason, args.who or human_name(),
                               Path(args.casebank) if args.casebank else None)
    except FragPlaceError as e:
        sys.exit(f"not recorded: {e}")
    after = f"fragplace run {args.study}" if state.path(run_dir).exists() else "the chat"
    print(f"recorded '{choice.checkpoint}' by {choice.who}" + (f", chosen {', '.join(choice.chosen)}" if choice.chosen else "")
          + f"; continue with {after}")


def cmd_decide(args):
    from ..errors import FragPlaceError
    from ..study.human import human_name
    from ..study.store import record_decision
    run_dir = existing(args)
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    who = args.who or human_name()
    try:
        record_decision(args.root, args.study, args.key, value, who, args.reason)
    except FragPlaceError as e:
        sys.exit(f"not recorded: {e}")
    print(f"{args.key} = {value!r} in {run_dir / 'PROJECT.md'}, set by {who}")


def cmd_status(args):
    """From state.json when fragplace run drove the study; else from what the tool calls of the chat recorded, which
    write no state.json."""
    from ..runtime import state
    from ..study.store import briefing
    run_dir = existing(args)
    if state.path(run_dir).exists():
        st = state.load(run_dir, args.study)
        print(f"study {args.study} at {run_dir}\n  step {st.current_step}; done {', '.join(st.completed_steps) or 'none'}; "
              f"pending checkpoint {st.pending_checkpoint or 'none'}")
        due = st.pending_checkpoint
    else:
        from ..study.calls import study_status
        s = study_status(args.study)
        if s.get("inputs") is False:
            print(f"study {args.study} at {run_dir} has no inputs: fragplace init {args.study} --example, or with --slab and the rest")
            return
        due = s.get("checkpoint_due")
        print(f"study {args.study} at {run_dir}, run from the chat\n  done {', '.join(s['done']) or 'none'}\n"
              f"  passed {', '.join(s['passed_checkpoints']) or 'none'}\n  next {s['next']}; checkpoint due {due or 'none'}")
        if s.get("open_decisions_missing"):
            print(f"  open decisions missing {len(s['open_decisions_missing'])}: fragplace decisions {args.study}")
    if due:
        print(briefing(args.root, args.study, due))


def cmd_decisions(args):
    from ..registry.tools import BY_NAME, open_decisions
    from ..runtime import project
    path = existing(args) / "PROJECT.md" if args.study else Path(args.root) / "PROJECT.md"
    s = project.read(path)
    print(f"open decisions in {path}:")
    for key in open_decisions():
        tool, name = key.split(".", 1)
        value = s.decisions.get(key)
        print(f"  {key:52s} {'MISSING' if value is None else repr(value):24s} {BY_NAME[tool].thresholds[name]}")


def parser() -> argparse.ArgumentParser:
    who = "who decides; FRAGPLACE_HUMAN, else git's user.name, else the login name"
    p = argparse.ArgumentParser(prog="fragplace")
    p.add_argument("--root", type=Path, default=None, help="the folder that holds runs/, PROJECT.md and lessons.md, never runs/ itself; "
                                                            "FRAGPLACE_ROOT, else the repository, as the MCP server and the hooks read it")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("registry", help="list every tool with its steps and status").set_defaults(fn=cmd_registry)
    sub.add_parser("check", help="figures, README, AGENTS.md and the registry agree; tests pass").set_defaults(fn=cmd_check)
    i = sub.add_parser("init", help="create runs/<study> from the supplied relaxed structures, or the example, and say where")
    i.add_argument("study")
    i.add_argument("--example", action="store_true", help="OH on Pt(111) built and relaxed with --calculator, test values for every decision; "
                                                          "under srun in the worker lane")
    i.add_argument("--calculator", default="emt", help="the example's potential: emt, mace-mp-small, uma-s-1p2p1, chgnet")
    i.add_argument("--slab", help="the relaxed surface")
    i.add_argument("--adsorbate", help="the relaxed adsorbate in vacuum")
    i.add_argument("--initial-state", help="the relaxed initial state, the adsorbate on the surface")
    i.add_argument("--bond", help="the bond to break as two atom indices in the adsorbate, A's side first: 0,1; without it init lists the atoms")
    i.add_argument("--fragment-a", help="fragment A relaxed in vacuum, when the human supplies it")
    i.add_argument("--fragment-b", help="fragment B relaxed in vacuum, when the human supplies it")
    i.add_argument("--facet", help="the surface's facet as Miller indices: 111, 100")
    i.add_argument("--energies", help="slab, adsorbate, initial state in eV, when the files carry none")
    i.add_argument("--minima-hopping", action="store_true", help="run step 3.6, the alternative generator, as well")
    i.add_argument("--n-hops", type=int, default=5)
    i.add_argument("--max-steps", type=int, default=500, help="the relaxation step cap")
    i.add_argument("--lane", choices=srun.LANES, help="where the study's heavy calls run, over FRAGPLACE_LANE: local, worker under srun, or batch, one sbatch job per call")
    i.set_defaults(fn=cmd_init)
    r = sub.add_parser("run", help="run the study to the next checkpoint; under srun in the worker lane")
    r.add_argument("study")
    r.set_defaults(fn=cmd_run)
    a = sub.add_parser("approve", help="record the human's choice at the pending checkpoint of the study")
    a.add_argument("study")
    a.add_argument("checkpoint")
    a.add_argument("--reason", required=True)
    a.add_argument("--who", help=who)
    a.add_argument("--chosen", action="extend", nargs="+", metavar="ID",
                   help="ids after one flag or one per flag: lit:<index> for each published value verified at approve settings; the "
                        "candidates to keep at review flagged cases, all when none; the final states at the pick")
    a.add_argument("--casebank", help="the case bank; ROOT/lessons.md by default")
    a.set_defaults(fn=cmd_approve)
    dc = sub.add_parser("decide", help="set one open decision in the study's PROJECT.md before the lock, with who and why")
    dc.add_argument("study")
    dc.add_argument("key", help="<tool>.<name>, as fragplace decisions lists it")
    dc.add_argument("value", help="the value as JSON: 5.0, true, \"vacuum\", [\"emt\"]")
    dc.add_argument("--who", help=who)
    dc.add_argument("--reason", required=True)
    dc.set_defaults(fn=cmd_decide)
    s = sub.add_parser("status", help="where the study stands and what its checkpoint shows, from state.json or from the chat's tool calls")
    s.add_argument("study")
    s.set_defaults(fn=cmd_status)
    d = sub.add_parser("decisions", help="every open decision and its value in PROJECT.md, the study's when one is named")
    d.add_argument("study", nargs="?")
    d.set_defaults(fn=cmd_decisions)
    return p


def main(argv: Optional[List[str]] = None) -> None:
    args = parser().parse_args(argv)
    args.argv = sys.argv[1:] if argv is None else list(argv)
    args.root = Path(os.path.abspath(os.path.expanduser(args.root or default_root())))
    if args.cmd not in ("registry", "check"):
        check_root(args.root)
        os.environ["FRAGPLACE_ROOT"] = str(args.root)    # the root study.calls, the hooks and a compute node read
    args.fn(args)


if __name__ == "__main__":
    main()
