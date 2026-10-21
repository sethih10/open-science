"""The MCP server: one typed tool per registry entry, built at start-up, so the agents call tools by name and
never by code.

Lives inside the package, not in a top-level mcp/ folder, because that name would shadow the MCP SDK's own package.
Run: fragplace-server, or python -m fragplace.server. Needs the MCP Python SDK, mcp 1.x, pip install "mcp[cli]".
With --list it prints the registry and exits without the SDK, which CI uses as a smoke test.
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys

from .. import tools
from ..registry.tools import REGISTRY


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


def build():
    Server = _server_class()
    server = Server("fragplace")
    for spec in REGISTRY:
        fn = tools.get(spec.name)
        description = (f"{spec.purpose} Board steps: {', '.join(spec.board_steps)}. Lane: {spec.lane}. "
                       f"Allowed roles: {', '.join(spec.allowed_roles)}. Thresholds marked 'open: team decision' must be given explicitly."
                       + (f" Requires the '{spec.checkpoint_gate}' checkpoint to have passed." if spec.checkpoint_gate else ""))

        def make(fn=fn, spec=spec):
            def call(**kwargs):
                out = fn(**kwargs)
                return json.loads(json.dumps(out, default=lambda o: o.model_dump(mode="json") if hasattr(o, "model_dump") else str(o)))
            call.__name__ = spec.name
            call.__doc__ = description
            call.__signature__ = inspect.signature(fn)
            return call

        server.tool(name=spec.name, description=description)(make())
    return server


def main() -> None:
    p = argparse.ArgumentParser(prog="fragplace-server")
    p.add_argument("--list", action="store_true", help="print the tools the server would expose and exit")
    a = p.parse_args()
    if a.list:
        for spec in REGISTRY:
            print(f"{spec.name:24s} v{spec.version} {spec.status:9s} lane {spec.lane:6s} gate {spec.checkpoint_gate or '-':28s} roles {', '.join(spec.allowed_roles)}")
        return
    build().run()


if __name__ == "__main__":
    main()
