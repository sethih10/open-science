"""Command line: list the registry, check the documents against the data module, start a campaign, run it to the
next checkpoint, record the human's choice there, and show where it stands."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ..execution.local import limit_threads
from ..runtime.journal import default_root

limit_threads()      # before numpy or torch loads

ROOT = Path(__file__).resolve().parents[3]


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


def cmd_init(args):
    options = {"minima_hopping": args.minima_hopping, "max_steps": args.max_steps, "n_hops": args.n_hops}
    if args.example:
        from ..agent.example import build_example
        c = build_example(args.root, args.campaign, args.calculator, options)
        print(f"example campaign {args.campaign} at {c.run.dir}: OH on Pt(111) relaxed with {args.calculator}; "
              f"PROJECT.md carries test values for every open decision")
    elif args.slab:
        from ..agent.example import init_campaign
        if not (args.adsorbate and args.initial_state and args.bond):
            sys.exit("init with inputs needs --slab, --adsorbate, --initial-state and --bond")
        energies = [float(x) for x in args.energies.split(",")] if args.energies else None
        c = init_campaign(args.root, args.campaign, args.slab, args.adsorbate, args.initial_state,
                          tuple(int(x) for x in args.bond.split(",")), energies, options)
        print(f"campaign {args.campaign} at {c.run.dir}; fill PROJECT.md there: protocol, protocol_reason and every decision "
              f"(fragplace decisions {args.campaign}), then fragplace run {args.campaign}")
    else:
        from ..runtime.journal import Run
        run = Run(args.root, args.campaign)
        project = Path(args.root) / "PROJECT.md"
        if project.exists():
            (run.dir / "PROJECT.md").write_text(project.read_text())
        print(f"campaign {args.campaign} at {run.dir}")


def cmd_run(args):
    from ..agent import pipeline
    from ..agent.campaign import Campaign, briefing
    from ..errors import CheckpointPending, FragPlaceError
    c = Campaign(args.root, args.campaign)
    if "inputs" not in c.data:
        sys.exit(f"campaign {args.campaign} has no inputs: fragplace init {args.campaign} --example, or with --slab and the rest")
    try:
        result = pipeline.run(c.run.dir, args.campaign, c.invoke, use_minima_hopping=bool(c.options.get("minima_hopping")))
    except CheckpointPending as e:
        print(f"\nstopped at the checkpoint: {e.name}\n")
        print(briefing(args.root, args.campaign, e.name))
        print(f"\nrecord the choice: fragplace approve {args.campaign} \"{e.name}\" --reason \"...\""
              + (" --chosen <id> ..." if e.name == "pick up to five final states" else
                 " [--chosen lit:0]" if e.name == "approve settings" else
                 " [--chosen <id> ..., to keep only these]" if e.name == "review flagged cases" else ""))
        return
    except FragPlaceError as e:
        sys.exit(f"stopped: {type(e).__name__}: {e}")
    print(f"campaign {args.campaign}: {result}; report at {c.run.dir / 'report.md'}")


def cmd_approve(args):
    from ..agent.campaign import record_choice
    from ..errors import FragPlaceError
    try:
        choice = record_choice(args.root, args.campaign, args.checkpoint, args.chosen or [], args.reason, args.who,
                               Path(args.casebank) if args.casebank else None)
    except FragPlaceError as e:
        sys.exit(f"not recorded: {e}")
    print(f"recorded '{choice.checkpoint}' by {choice.who}; continue with fragplace run {args.campaign}")


def cmd_decide(args):
    import json
    from ..agent.campaign import record_decision
    from ..errors import FragPlaceError
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    try:
        record_decision(args.root, args.campaign, args.key, value, args.who, args.reason)
    except FragPlaceError as e:
        sys.exit(f"not recorded: {e}")
    print(f"{args.key} = {value!r} in runs/{args.campaign}/PROJECT.md, set by {args.who}")


def cmd_status(args):
    from ..agent.campaign import Campaign, briefing
    from ..runtime import state
    c = Campaign(args.root, args.campaign)
    st = state.load(c.run.dir, args.campaign)
    print(f"campaign {args.campaign} at {c.run.dir}\n  step {st.current_step}; done {', '.join(st.completed_steps) or 'none'}; "
          f"pending checkpoint {st.pending_checkpoint or 'none'}")
    if st.pending_checkpoint:
        print(briefing(args.root, args.campaign, st.pending_checkpoint))


def cmd_decisions(args):
    from ..registry.tools import BY_NAME, open_decisions
    from ..runtime import project
    path = Path(args.root) / "runs" / args.campaign / "PROJECT.md" if args.campaign else Path(args.root) / "PROJECT.md"
    s = project.read(path)
    print(f"open decisions in {path}:")
    for key in open_decisions():
        tool, name = key.split(".", 1)
        value = s.decisions.get(key)
        print(f"  {key:52s} {'MISSING' if value is None else repr(value):24s} {BY_NAME[tool].thresholds[name]}")


def main() -> None:
    p = argparse.ArgumentParser(prog="fragplace")
    p.add_argument("--root", type=Path, default=None, help="the directory holding runs/, PROJECT.md and lessons.md; FRAGPLACE_ROOT, else the "
                                                            "repository, as the MCP server and the hooks read it")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("registry", help="list every tool with its steps and status").set_defaults(fn=cmd_registry)
    sub.add_parser("check", help="figures, README, AGENTS.md and the registry agree; tests pass").set_defaults(fn=cmd_check)
    i = sub.add_parser("init", help="create runs/<campaign>: from three relaxed structures, or the example")
    i.add_argument("campaign")
    i.add_argument("--example", action="store_true", help="OH on Pt(111) built and relaxed with --calculator, test values for every decision")
    i.add_argument("--calculator", default="emt", help="the example's potential: emt, mace-mp-small, uma-s-1p2p1, chgnet")
    i.add_argument("--slab"), i.add_argument("--adsorbate", help="the relaxed adsorbate in vacuum"), i.add_argument("--initial-state")
    i.add_argument("--bond", help="the bond to break as two atom indices in the adsorbate, A's side first: 0,1")
    i.add_argument("--energies", help="slab, adsorbate, initial state in eV, when the files carry none")
    i.add_argument("--minima-hopping", action="store_true", help="run step 3.6, the alternative generator, as well")
    i.add_argument("--n-hops", type=int, default=5)
    i.add_argument("--max-steps", type=int, default=500, help="the relaxation step cap")
    i.set_defaults(fn=cmd_init)
    r = sub.add_parser("run", help="run the campaign to the next checkpoint")
    r.add_argument("campaign")
    r.set_defaults(fn=cmd_run)
    a = sub.add_parser("approve", help="record the human's choice at the pending checkpoint")
    a.add_argument("campaign")
    a.add_argument("checkpoint")
    a.add_argument("--reason", required=True)
    a.add_argument("--who", default="human")
    a.add_argument("--chosen", nargs="*", help="lit:<index> for each published value verified at approve settings; the candidates to keep at "
                                               "review flagged cases, all when none; the final states at the pick")
    a.add_argument("--casebank", help="the case bank; ROOT/lessons.md by default")
    a.set_defaults(fn=cmd_approve)
    dc = sub.add_parser("decide", help="set one open decision in the campaign's PROJECT.md before the lock, with who and why")
    dc.add_argument("campaign")
    dc.add_argument("key", help="<tool>.<name>, as fragplace decisions lists it")
    dc.add_argument("value", help="the value as JSON: 5.0, true, \"vacuum\", [\"emt\"]")
    dc.add_argument("--who", default="human")
    dc.add_argument("--reason", required=True)
    dc.set_defaults(fn=cmd_decide)
    s = sub.add_parser("status", help="where the campaign stands and what its checkpoint shows")
    s.add_argument("campaign")
    s.set_defaults(fn=cmd_status)
    d = sub.add_parser("decisions", help="every open decision and its value in PROJECT.md")
    d.add_argument("campaign", nargs="?")
    d.set_defaults(fn=cmd_decisions)
    args = p.parse_args()
    args.root = args.root or default_root()
    args.fn(args)


if __name__ == "__main__":
    main()
