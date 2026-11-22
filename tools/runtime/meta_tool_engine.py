#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/runtime/meta_tool_engine.py — Tier 2 Meta-Tool Lazy Loading Runtime
-------------------------------------------------------------------------
Replaces 50+ monolithic tool schemas in the LLM context with exactly TWO Meta-Tools:
  1. search_tools(query, domain) -> returns compact descriptors for matched tools only.
  2. execute_tool(name, args) -> executes tool on-demand via isolated subprocess.

Reduces schema overhead from 15,000–30,000 tokens down to < 400 tokens per turn.

Usage:
  python3 tools/runtime/meta_tool_engine.py search "linter"
  python3 tools/runtime/meta_tool_engine.py execute verify_all '{"--tier": "fast"}'
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

TOOLS_SCHEMA_PATH = os.path.join(_REPO_ROOT, "tools", "tools_schema.json")
SKILLS_INDEX_PATH = os.path.join(_REPO_ROOT, "skills_index.json")


class MetaToolEngine:
    """Dynamic Meta-Tool Runtime for lazy schema loading and execution."""

    META_TOOLS_DEFINITION = [
        {
            "name": "search_tools",
            "desc": "Search on-demand tool/skill catalog by keyword or domain",
            "params": {
                "query": {"type": "string", "req": True},
                "domain": {"type": "string", "req": False}
            }
        },
        {
            "name": "execute_tool",
            "desc": "Execute a matched tool on-demand with args",
            "params": {
                "name": {"type": "string", "req": True},
                "args": {"type": "object", "req": False}
            }
        }
    ]

    def __init__(self, repo_root: str = _REPO_ROOT):
        self.repo_root = repo_root
        self._tools_catalog: Dict[str, Any] = {}
        self._skills_catalog: List[Dict[str, Any]] = []
        self._load_catalogs()

    def _load_catalogs(self) -> None:
        if os.path.exists(TOOLS_SCHEMA_PATH):
            try:
                with open(TOOLS_SCHEMA_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._tools_catalog = data.get("tools", data)
            except Exception:
                self._tools_catalog = {}

        if os.path.exists(SKILLS_INDEX_PATH):
            try:
                with open(SKILLS_INDEX_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._skills_catalog = data.get("skills", [])
                    elif isinstance(data, list):
                        self._skills_catalog = data
            except Exception:
                self._skills_catalog = []

    def search_tools(self, query: str, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches tools and skills by query and domain, returning compact descriptors."""
        q = query.lower().strip()
        results: List[Dict[str, Any]] = []

        # 1. Search CLI Tools
        for name, defn in self._tools_catalog.items():
            score = 0
            name_lower = name.lower()
            summary = defn.get("summary", "").lower()
            cmd = defn.get("command", "").lower()

            if q in name_lower:
                score += 10
            if q in summary:
                score += 5
            if q in cmd:
                score += 3

            if score > 0:
                results.append({
                    "kind": "tool",
                    "name": name,
                    "command": defn.get("command"),
                    "summary": defn.get("summary", ""),
                    "args": defn.get("args", {}),
                    "score": score
                })

        # 2. Search Skills
        for skill in self._skills_catalog:
            score = 0
            s_id = skill.get("id", "").lower()
            s_dom = skill.get("domain", "").lower()
            s_sum = skill.get("summary", "").lower()
            triggers = [t.lower() for t in skill.get("stack_triggers", [])]

            if domain and domain.lower() in s_dom:
                score += 8
            if q in s_id:
                score += 10
            if any(q in t for t in triggers):
                score += 8
            if q in s_sum:
                score += 4

            if score > 0:
                results.append({
                    "kind": "skill",
                    "id": skill.get("id"),
                    "domain": skill.get("domain"),
                    "summary": skill.get("summary"),
                    "score": score
                })

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        # Return top 5 most relevant items with score stripped
        return [{k: v for k, v in r.items() if k != "score"} for r in results[:5]]

    def execute_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a tool by name with arguments via Python subprocess."""
        args = args or {}
        tool_def = self._tools_catalog.get(name)
        if not tool_def:
            # Check if name is a script path directly
            candidate = os.path.join(self.repo_root, name if name.endswith(".py") else f"tools/{name}.py")
            if not os.path.exists(candidate):
                return {
                    "status": "ERROR",
                    "exit_code": 127,
                    "error": f"Tool '{name}' not found in catalog or filesystem."
                }
            base_cmd = f"python3 {candidate}"
        else:
            base_cmd = tool_def.get("command", f"python3 {tool_def.get('path')}")

        cmd_parts = base_cmd.split()
        for k, v in args.items():
            if isinstance(v, bool):
                if v:
                    cmd_parts.append(k)
            elif k.startswith("-"):
                cmd_parts.extend([k, str(v)])
            else:
                # Positional argument
                cmd_parts.append(str(v))

        try:
            res = subprocess.run(
                cmd_parts,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()
            return {
                "status": "SUCCESS" if res.returncode == 0 else "FAILED",
                "exit_code": res.returncode,
                "stdout": stdout[:2000] if len(stdout) > 2000 else stdout,
                "stderr": stderr[:1000] if len(stderr) > 1000 else stderr,
                "truncated": len(stdout) > 2000 or len(stderr) > 1000
            }
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "exit_code": 124, "error": "Execution timed out after 60s"}
        except Exception as e:
            return {"status": "EXCEPTION", "exit_code": 1, "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 2 Meta-Tool Lazy Loading Runtime")
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    search_p = subparsers.add_parser("search", help="Search tools catalog")
    search_p.add_argument("query", help="Keyword to search")
    search_p.add_argument("--domain", help="Filter by domain")
    search_p.add_argument("--json", action="store_true", help="Output JSON")

    exec_p = subparsers.add_parser("execute", help="Execute a tool on-demand")
    exec_p.add_argument("name", help="Tool name")
    exec_p.add_argument("params", nargs="?", default="{}", help="JSON string of arguments")

    args = parser.parse_args()
    engine = MetaToolEngine()

    if args.action == "search":
        matches = engine.search_tools(args.query, args.domain)
        if args.json or True:
            print(json.dumps(matches, indent=2, ensure_ascii=False))
        return 0

    elif args.action == "execute":
        try:
            param_dict = json.loads(args.params)
        except Exception:
            param_dict = {}
        result = engine.execute_tool(args.name, param_dict)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("status") == "SUCCESS" else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
