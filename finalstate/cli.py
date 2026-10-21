"""Command line: list the registry, check the documents against the data module, start a campaign."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cmd_registry(_):
    from .registry import REGISTRY
    for t in REGISTRY:
        print(f"{t.name:24s} {t.status:9s} steps {', '.join(t.board_steps)}")


def cmd_check(_):
    py = sys.executable
    src = ROOT / "archive" / "docs" / "figures" / "src"
    rc = subprocess.call([py, str(src / "board_check.py")])
    rc |= subprocess.call([py, "-m", "pytest", "-q", str(ROOT / "tests")])
    sys.exit(rc)


def cmd_init(args):
    from .provenance import Run
    run = Run(ROOT, args.campaign)
    project = ROOT / "PROJECT.md"
    if project.exists():
        (run.dir / "PROJECT.md").write_text(project.read_text())
    print(f"campaign {args.campaign} at {run.dir}")


def main() -> None:
    p = argparse.ArgumentParser(prog="finalstate")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("registry", help="list every tool with its steps and status").set_defaults(fn=cmd_registry)
    sub.add_parser("check", help="figures, README, agent.md and the registry agree; tests pass").set_defaults(fn=cmd_check)
    i = sub.add_parser("init", help="create runs/<campaign> with a copy of PROJECT.md"); i.add_argument("campaign"); i.set_defaults(fn=cmd_init)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
