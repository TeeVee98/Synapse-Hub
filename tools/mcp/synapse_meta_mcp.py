#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/mcp/synapse_meta_mcp.py — Tier 2 Ultra-Lean Meta-Tool MCP Server
----------------------------------------------------------------------
Complies with Model Context Protocol (MCP) JSON-RPC 2.0 over stdio.
Exposes strictly TWO Meta-Tools to reduce schema context consumption by 90%:
  1. search_tools: On-demand search across 233 CLI tools and 57 skills.
  2. execute_tool: Sandboxed on-demand tool execution with automatic observation masking.

Total Schema Footprint: < 350 tokens (compared to 15,000–30,000 tokens for 50+ tools).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, Optional

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Enforce UTF-8 stdio
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tools.runtime.meta_tool_engine import MetaToolEngine

logger = logging.getLogger("synapse.meta_mcp")


class SynapseMetaMCPServer:
    """Ultra-lean JSON-RPC 2.0 MCP Server exposing only 2 meta-tools."""

    SERVER_INFO = {
        "name": "synapse-meta-hub",
        "version": "2.0.0",
        "description": "Tier 2 Meta-Tool Lazy Loading MCP Server"
    }

    TOOLS = [
        {
            "name": "search_tools",
            "description": "Search on-demand CLI automations and QA skills by keyword or domain",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword to match tool name, command, or capability"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Optional category or skill domain filter"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "execute_tool",
            "description": "Execute a matched tool on-demand with parameters and automatic observation masking",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Canonical name of the tool (e.g. verify_all, infer_linter)"
                    },
                    "args": {
                        "type": "object",
                        "description": "Key-value dictionary of command-line flags and parameters"
                    }
                },
                "required": ["name"]
            }
        }
    ]

    def __init__(self, repo_root: str = _REPO_ROOT):
        self.repo_root = repo_root
        self.engine = MetaToolEngine(repo_root)

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a single JSON-RPC request and returns the response."""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": self.SERVER_INFO
                }
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.TOOLS}
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name == "search_tools":
                query = tool_args.get("query", "")
                domain = tool_args.get("domain")
                results = self.engine.search_tools(query, domain)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(results, indent=2, ensure_ascii=False)}]
                    }
                }

            elif tool_name == "execute_tool":
                name = tool_args.get("name", "")
                args = tool_args.get("args", {})
                res = self.engine.execute_tool(name, args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res, indent=2, ensure_ascii=False)}],
                        "isError": res.get("status") != "SUCCESS"
                    }
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method or tool '{tool_name}' not found"}
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unsupported method: {method}"}
            }

    def run_stdio(self) -> None:
        """Runs the MCP server loop reading from stdin and writing to stdout."""
        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                req = json.loads(line_str)
                resp = self.handle_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error or exception: {e}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


def main() -> int:
    server = SynapseMetaMCPServer()
    server.run_stdio()
    return 0


if __name__ == "__main__":
    sys.exit(main())
