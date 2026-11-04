"""
Synapse Hub — Model Context Protocol (MCP) Servers (tools.mcp)
--------------------------------------------------------------
Domain package grouping all standard MCP services: core QA automation
MCP server and offline Excel spreadsheet manipulation server.
"""

from tools import (
    mcp_excel_server,
    mcp_server,
)

__all__ = [
    "mcp_excel_server",
    "mcp_server",
]
