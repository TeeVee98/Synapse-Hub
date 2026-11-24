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
from typing import Any, Dict, List, Optional

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
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "toon"],
                        "description": "Output format (json or toon)"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "execute_tool",
            "description": "Execute a tool or action batch with observation masking and optional in-memory filtering",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Canonical tool name (e.g. verify_all)"
                    },
                    "args": {
                        "type": "object",
                        "description": "Tool CLI flags and parameters"
                    },
                    "actions": {
                        "type": "array",
                        "description": "Optional parallel action batch"
                    },
                    "filter_expr": {
                        "type": "string",
                        "description": "Optional predicate to filter output in memory"
                    }
                }
            }
        }
    ]

    def __init__(self, repo_root: str = _REPO_ROOT):
        self.repo_root = repo_root
        self.engine = MetaToolEngine(repo_root)

    @staticmethod
    def _extract_records_for_filter(raw_text: str) -> List[Dict[str, Any]]:
        """Parses tool stdout as JSON records, falling back to line-indexed text records."""
        try:
            parsed = json.loads(raw_text)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get("records"), list):
            return parsed["records"]
        return [{"line": idx + 1, "text": ln} for idx, ln in enumerate(raw_text.splitlines())]

    def _apply_filter_to_result(self, res: Dict[str, Any], records: List[Dict[str, Any]], filter_expr: str) -> None:
        """Applies in-memory CodeAct filtering to records and merges metrics into result dict."""
        flt = self.engine.filter_output_in_memory(records, filter_expr)
        if flt.get("status") != "SUCCESS":
            res["status"] = flt.get("status", "ERROR")
            res["error"] = flt.get("error", "In-memory filtering failed")
            res["filter_result"] = flt
            return
        res["filtered"] = flt["filtered"]
        res["matched_count"] = flt["matched_count"]
        res["tokens_saved"] = flt["tokens_saved"]
        res["stdout"] = json.dumps(flt["filtered"], ensure_ascii=False)

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
            tool_args = params.get("arguments") or {}

            if tool_name == "search_tools":
                query = tool_args.get("query", "")
                domain = tool_args.get("domain")
                fmt = tool_args.get("format", "json")
                results = self.engine.search_tools(query, domain, compact_format=fmt)
                text_out = results if isinstance(results, str) else json.dumps(results, indent=2, ensure_ascii=False)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text_out}]
                    }
                }

            elif tool_name == "execute_tool":
                name = tool_args.get("name", "")
                args = tool_args.get("args") or {}
                mask_obs = tool_args.get("mask_observations", True)
                actions = tool_args.get("actions")
                filter_expr = tool_args.get("filter_expr")

                if actions is not None:
                    res = self.engine.execute_batch(actions, mask_observations=mask_obs)
                    if filter_expr and res.get("status") == "SUCCESS":
                        self._apply_filter_to_result(res, list(res.get("results", {}).values()), filter_expr)
                elif filter_expr and not name and "records" in tool_args:
                    res = self.engine.filter_output_in_memory(tool_args["records"], filter_expr)
                else:
                    res = self.engine.execute_tool(name, args, mask_observations=mask_obs)
                    if filter_expr and res.get("status") == "SUCCESS":
                        raw_text = res.get("stdout", "")
                        log_file = res.get("log_file")
                        if res.get("masked") and log_file and os.path.isfile(log_file):
                            with open(log_file, "r", encoding="utf-8", errors="replace") as lf:
                                raw_text = lf.read()
                        records = self._extract_records_for_filter(raw_text)
                        self._apply_filter_to_result(res, records, filter_expr)

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res, indent=2, ensure_ascii=False)}],
                        "isError": res.get("status") != "SUCCESS",
                        "masked": bool(res.get("masked")),
                        "log_file": res.get("log_file"),
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
