"""finalstate: the nearest non-recombining final state of a dissociated adsorbate, as a library of deterministic tools.

The LLM agents call the tools by name through the MCP server in mcp/server.py; the tools are defined once in
finalstate.registry and implemented one per module under finalstate.tools. Nothing here places atoms from text.
"""
__version__ = "0.1.0"
