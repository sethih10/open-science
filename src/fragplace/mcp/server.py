"""The MCP server: one tool per registry entry and the two campaign operations, so the agents call tools by name
and never by code.

Each tool is the agent-facing function of agent.interface: it names its campaign, takes only what an agent
decides, and answers with a summary; the records stay on disk. Claude Code publishes the tools of this plugin as
mcp__plugin_fragplace_fragplace__<name>. Lives inside the package, not in a top-level mcp/ folder, because that
name would shadow the MCP SDK's own package. Run: fragplace-server. Needs the MCP Python SDK, mcp 1.x. With
--list it prints the tools and exits without the SDK, which CI uses as a smoke test.
"""
from __future__ import annotations

import argparse
import os

from ..execution.local import limit_threads  # noqa: E402

limit_threads()      # before numpy or torch loads

from ..registry.tools import BY_NAME, OPERATIONS, REGISTRY  # noqa: E402


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
    spec = BY_NAME[name]
    return (f"{spec.purpose} Board steps: {', '.join(spec.board_steps)}. Allowed roles: {', '.join(spec.allowed_roles)}."
            + (f" Needs the '{spec.checkpoint_gate}' checkpoint, which only the human passes." if spec.checkpoint_gate else "")
            + " Answers with a summary; a call that cannot run says what the human, or an earlier tool, must do first.")


def build(root=None):
    """The server; runs/ lives under root, FRAGPLACE_ROOT or the repository by default."""
    if root:
        os.environ["FRAGPLACE_ROOT"] = str(root)
    from ..agent import interface
    server = _server_class()("fragplace")
    for name, fn in interface.FUNCTIONS.items():
        server.tool(name=name, description=description(name) + "\n\n" + (fn.__doc__ or ""))(fn)
    return server


def main() -> None:
    p = argparse.ArgumentParser(prog="fragplace-server")
    p.add_argument("--list", action="store_true", help="print the tools the server would expose and exit")
    a = p.parse_args()
    if a.list:
        for spec in REGISTRY:
            print(f"{spec.name:24s} v{spec.version} {spec.status:9s} lane {spec.lane:6s} gate {spec.checkpoint_gate or '-':28s} roles {', '.join(spec.allowed_roles)}")
        for name in OPERATIONS:
            print(f"{name:24s} operation, every role")
        return
    build().run()


if __name__ == "__main__":
    main()
