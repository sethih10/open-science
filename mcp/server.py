"""The MCP server: one typed tool per registry entry, built at start-up, so the agents call tools by name and
never by code. Run: python -m mcp.server (needs the MCP Python SDK: pip install "mcp[cli]")."""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from finalstate.registry import REGISTRY  # noqa: E402
from finalstate import tools  # noqa: E402


def build():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:  # pragma: no cover
        raise ImportError('pip install "mcp[cli]"') from e
    server = FastMCP("finalstate")
    for spec in REGISTRY:
        fn = tools.get(spec.name)
        description = spec.purpose + "\nSteps: " + ", ".join(spec.board_steps) + ". Thresholds marked 'open: team decision' must be given explicitly."

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


if __name__ == "__main__":
    build().run()
