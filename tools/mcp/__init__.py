# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — Model Context Protocol (MCP) Servers (tools.mcp)
--------------------------------------------------------------
Domain package grouping all standard MCP services: core QA automation
MCP server and offline Excel spreadsheet manipulation server.
"""

from tools import (
    mcp_docx_server,
    mcp_excel_server,
    mcp_server,
)

__all__ = [
    "mcp_docx_server",
    "mcp_excel_server",
    "mcp_server",
]
