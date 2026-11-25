#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/core/schema_minifier.py — Tier 2 JSON Schema Pruner & Minifier
--------------------------------------------------------------------
Compresses verbose JSON Tool Schemas by 70–85% to eliminate massive prompt overhead.
Removes verbose descriptions, redundant examples, and auxiliary metadata while
retaining structural integrity: parameter names, types, enums, and required constraints.

Usage:
  python3 tools/core/schema_minifier.py tools/tools_schema.json
  python3 tools/core/schema_minifier.py --all-tools --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class SchemaMinifier:
    """Minifies JSON tool schemas for maximum token efficiency."""

    EXCLUDED_KEYS = {
        "description", "help", "examples", "example", "$schema", "version",
        "generated_at", "title", "summary"
    }

    @classmethod
    def minify_parameter_schema(cls, schema: Dict[str, Any], aggressive: bool = True) -> Dict[str, Any]:
        """Minifies a single parameter definition."""
        if not isinstance(schema, dict):
            return schema

        minified = {}
        for k, v in schema.items():
            if aggressive and k in cls.EXCLUDED_KEYS:
                continue
            if isinstance(v, dict):
                minified[k] = cls.minify_parameter_schema(v, aggressive=aggressive)
            elif isinstance(v, list):
                minified[k] = [cls.minify_parameter_schema(item, aggressive=aggressive) if isinstance(item, dict) else item for item in v]
            else:
                minified[k] = v
        return minified

    @classmethod
    def _minify_args_map(cls, raw_args: Dict[str, Any]) -> Dict[str, Any]:
        """Minifies an argument dictionary into compact schema entries."""
        out: Dict[str, Any] = {}
        for arg_name, arg_val in raw_args.items():
            if isinstance(arg_val, dict):
                clean_arg: Dict[str, Any] = {"type": arg_val.get("type", "string")}
                if arg_val.get("required"):
                    clean_arg["req"] = True
                if "choices" in arg_val:
                    clean_arg["choices"] = arg_val["choices"]
                if "default" in arg_val and arg_val["default"] not in (None, False, ""):
                    clean_arg["default"] = arg_val["default"]
                out[arg_name] = clean_arg
            else:
                out[arg_name] = arg_val
        return out

    @classmethod
    def minify_tool_dict(cls, tool_def: Dict[str, Any], aggressive: bool = True) -> Dict[str, Any]:
        """Minifies a full tool entry."""
        res: Dict[str, Any] = {}
        if "command" in tool_def:
            res["cmd"] = tool_def["command"]
        elif "path" in tool_def:
            res["path"] = tool_def["path"]

        if "args" in tool_def and isinstance(tool_def["args"], dict):
            res["args"] = cls._minify_args_map(tool_def["args"])

        if "subcommands" in tool_def and isinstance(tool_def["subcommands"], dict):
            res["subcommands"] = {
                sub_name: {
                    "args": cls._minify_args_map(sub_def.get("args", {}))
                    if isinstance(sub_def, dict) and isinstance(sub_def.get("args"), dict)
                    else {}
                }
                for sub_name, sub_def in tool_def["subcommands"].items()
            }

        # If it's a standard OpenAPI / JSON Schema format (parameters / properties)
        if "parameters" in tool_def and isinstance(tool_def["parameters"], dict):
            res["params"] = cls.minify_parameter_schema(tool_def["parameters"], aggressive=aggressive)

        return res

    @classmethod
    def minify_schema_file(cls, file_path: str, aggressive: bool = True) -> Tuple[Dict[str, Any], int, int]:
        """Minifies an entire tools schema file and calculates token savings."""
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        original_data = json.loads(raw_text)
        original_size = len(raw_text)

        tools_data = original_data.get("tools", original_data)
        minified_tools = {}

        for name, defn in tools_data.items():
            if isinstance(defn, dict):
                minified_tools[name] = cls.minify_tool_dict(defn, aggressive=aggressive)
            else:
                minified_tools[name] = defn

        minified_text = json.dumps(minified_tools, separators=(",", ":"), ensure_ascii=False)
        minified_size = len(minified_text)

        return minified_tools, original_size, minified_size


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 2 JSON Schema Pruner & Minifier")
    parser.add_argument("target", nargs="?", default=os.path.join(_REPO_ROOT, "tools", "tools_schema.json"), help="Target schema file")
    parser.add_argument("--json", action="store_true", help="Print minified JSON to stdout")
    args = parser.parse_args()

    if not os.path.exists(args.target):
        print(f"Error: Target file not found: {args.target}", file=sys.stderr)
        return 1

    minified, orig_len, mini_len = SchemaMinifier.minify_schema_file(args.target)
    savings = (1 - (mini_len / orig_len)) * 100

    if args.json:
        print(json.dumps(minified, separators=(",", ":"), ensure_ascii=False))
        return 0

    print(f"=== Tier 2 Schema Pruning Analysis for {os.path.basename(args.target)} ===")
    print(f"Original Characters : {orig_len:,} chars (~{int(orig_len/3.8):,} tokens)")
    print(f"Minified Characters : {mini_len:,} chars (~{int(mini_len/3.8):,} tokens)")
    print(f"Token Reduction     : {savings:.1f}% SAVED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
