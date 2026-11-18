# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — MCP Package (tools.mcp)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.mcp import mcp_docx_server
from tools.mcp import mcp_excel_server
from tools.mcp import mcp_server

__all__ = [
    "mcp_docx_server",
    "mcp_excel_server",
    "mcp_server"
]
