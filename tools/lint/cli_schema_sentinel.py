#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/lint/cli_schema_sentinel.py — ACI Tool Call Schema & Contract Drift Validator
-----------------------------------------------------------------------------------
Inspired by Automattic Studio evals, UNICEF ADT-Studio, and Antfu CLI patterns.
Statically analyzes Python AST argparse definitions across tools/ to detect contract
drift against tools/tools_schema.json (missing flags, renamed args, phantom args).
Supports --sync to automatically reconcile schema definitions directly from code truth.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def extract_ast_arguments(py_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Parses a Python file AST to extract all argparse arguments and their metadata.
    Returns dict mapping canonical argument name to its schema metadata.
    """
    if not os.path.isfile(py_path):
        return {}

    try:
        with open(py_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=py_path)
    except Exception:
        return {}

    extracted_args: Dict[str, Dict[str, Any]] = {}

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            arg_names: List[str] = []
            for arg_node in node.args:
                if isinstance(arg_node, ast.Constant) and isinstance(arg_node.value, str):
                    arg_names.append(arg_node.value)

            if not arg_names:
                continue

            long_flags = [n for n in arg_names if n.startswith("--")]
            short_flags = [n for n in arg_names if n.startswith("-") and not n.startswith("--")]
            positionals = [n for n in arg_names if not n.startswith("-")]

            canonical = (
                long_flags[0]
                if long_flags
                else (short_flags[0] if short_flags else (positionals[0] if positionals else ""))
            )
            if not canonical or canonical in ("-h", "--help"):
                continue

            is_positional = not canonical.startswith("-")
            meta: Dict[str, Any] = {"type": "string"}

            action = None
            arg_type = None
            default_val = None
            has_default = False
            req_val = None
            choices_val = None
            help_val = None
            nargs_val = None

            for kw in node.keywords:
                if kw.arg == "action" and isinstance(kw.value, ast.Constant):
                    action = kw.value.value
                elif kw.arg == "type" and isinstance(kw.value, ast.Name):
                    arg_type = kw.value.id
                elif kw.arg == "default" and isinstance(kw.value, ast.Constant):
                    has_default = True
                    default_val = kw.value.value
                elif kw.arg == "required" and isinstance(kw.value, ast.Constant):
                    req_val = kw.value.value
                elif kw.arg == "choices" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    choices_val = [
                        elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)
                    ]
                elif kw.arg == "help" and isinstance(kw.value, ast.Constant):
                    help_val = kw.value.value
                elif kw.arg == "nargs" and isinstance(kw.value, ast.Constant):
                    nargs_val = kw.value.value

            if action in ("store_true", "store_false"):
                meta["type"] = "boolean"
                meta["default"] = False if action == "store_true" else True
            elif action == "count":
                meta["type"] = "integer"
            elif action == "append":
                meta["type"] = "array"
            elif arg_type == "int":
                meta["type"] = "integer"
            elif arg_type == "float":
                meta["type"] = "number"
            elif arg_type == "bool":
                meta["type"] = "boolean"

            if choices_val is not None:
                meta["choices"] = choices_val

            if has_default and default_val is not None:
                meta["default"] = default_val

            if req_val is not None:
                meta["required"] = bool(req_val)
            elif is_positional:
                meta["required"] = nargs_val not in ("?", "*") and default_val is None
            else:
                meta["required"] = False

            if help_val:
                meta["help"] = help_val

            extracted_args[canonical] = meta

    return extracted_args


def has_argparse_entrypoint(py_path: str) -> bool:
    """Checks if a python file initializes an ArgumentParser."""
    if not os.path.isfile(py_path):
        return False
    try:
        with open(py_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=py_path)
    except Exception:
        return False

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "ArgumentParser"
        ):
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "ArgumentParser"
        ):
            return True
    return False


def validate_schema_drift(
    schema_path: str = "tools/tools_schema.json",
    tools_dir: str = "tools",
    tool_scope: Optional[str] = None,
    sync: bool = False,
    expand_all: bool = False,
) -> Tuple[Dict[str, Any], int]:
    """
    Validates tools_schema.json against AST code truth.
    Returns (report_dict, exit_code).
    """
    if not os.path.isfile(schema_path):
        return {
            "status": "DRIFT_DETECTED",
            "tools_checked": 0,
            "drift_count": 0,
            "drifts": [],
            "message": f"Schema file not found at: {schema_path}",
        }, 1

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_data = json.load(f)
    except Exception as e:
        return {
            "status": "DRIFT_DETECTED",
            "tools_checked": 0,
            "drift_count": 0,
            "drifts": [],
            "message": f"Malformed schema JSON: {e}",
        }, 1

    tools_dict = schema_data.get("tools", {})
    tools_to_check = [tool_scope] if tool_scope and tool_scope in tools_dict else list(tools_dict.keys())

    drifts: List[Dict[str, Any]] = []
    tools_checked = 0

    for tool_name in tools_to_check:
        tool_info = tools_dict[tool_name]
        script_rel_path = tool_info.get("path", "")
        script_abs_path = os.path.abspath(script_rel_path)

        if not os.path.isfile(script_abs_path):
            raw_schema_args = tool_info.get("args", {})
            phantom_args = list(raw_schema_args.keys()) if isinstance(raw_schema_args, dict) else list(raw_schema_args)
            drifts.append({
                "tool": tool_name,
                "script": script_rel_path,
                "missing_in_schema": [],
                "phantom_in_schema": phantom_args,
                "ast_arguments": [],
                "error": "Script file does not exist",
            })
            continue

        tools_checked += 1
        ast_args = extract_ast_arguments(script_abs_path)
        schema_args = tool_info.get("args", {})

        ast_names = set(ast_args.keys())
        if isinstance(schema_args, dict):
            schema_names = set(schema_args.keys())
        elif isinstance(schema_args, (list, tuple, set)):
            schema_names = set(schema_args)
        else:
            schema_names = set()

        missing_in_schema = sorted(list(ast_names - schema_names))
        phantom_in_schema = sorted(list(schema_names - ast_names))

        if missing_in_schema or phantom_in_schema:
            drifts.append({
                "tool": tool_name,
                "script": script_rel_path,
                "missing_in_schema": missing_in_schema,
                "phantom_in_schema": phantom_in_schema,
                "ast_arguments": sorted(list(ast_names)),
            })

            if sync:
                # Synchronize schema from AST code truth
                tool_info["args"] = ast_args

    unregistered_tools: List[str] = []
    if expand_all and os.path.isdir(tools_dir):
        registered_paths = {os.path.abspath(t.get("path", "")) for t in tools_dict.values()}
        for root, _, files in os.walk(tools_dir):
            for file in files:
                if file.endswith(".py"):
                    full_p = os.path.abspath(os.path.join(root, file))
                    if full_p not in registered_paths and has_argparse_entrypoint(full_p):
                        rel_p = os.path.relpath(full_p, _REPO_ROOT)
                        unregistered_tools.append(rel_p)
        unregistered_tools.sort()

    if sync and drifts:
        os.makedirs(os.path.dirname(os.path.abspath(schema_path)), exist_ok=True)
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    drift_count = len(drifts)
    status = "PASS" if drift_count == 0 else "DRIFT_DETECTED"
    exit_code = 0 if (status == "PASS" or sync) else 1

    report: Dict[str, Any] = {
        "status": status,
        "tools_checked": tools_checked,
        "drift_count": drift_count,
        "drifts": drifts,
    }
    if expand_all:
        report["unregistered_tools"] = unregistered_tools

    return report, exit_code


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI parser for cli_schema_sentinel."""
    parser = argparse.ArgumentParser(
        description="ACI Tool Call Schema & Contract Drift Validator (Studio/ADT pattern)"
    )
    parser.add_argument(
        "--schema",
        type=str,
        default="tools/tools_schema.json",
        help="Path to authoritative schema (default: tools/tools_schema.json)",
    )
    parser.add_argument(
        "--tools-dir",
        type=str,
        default="tools",
        help="Directory containing Python tool scripts (default: tools)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify schema parity without modifying files (exits 1 on drift)",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Synchronize tools_schema.json arguments from AST code truth",
    )
    parser.add_argument(
        "--tool",
        type=str,
        default=None,
        help="Scope check or sync to a specific tool identifier",
    )
    parser.add_argument(
        "--expand-all",
        action="store_true",
        help="Discover unregistered tools with argparse entry points",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable drift report")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    report, exit_code = validate_schema_drift(
        schema_path=args.schema,
        tools_dir=args.tools_dir,
        tool_scope=args.tool,
        sync=args.sync,
        expand_all=args.expand_all,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if report["status"] == "PASS":
            print(f"[PASS] Zero contract drift across {report['tools_checked']} checked tool(s).")
        else:
            print(f"[DRIFT DETECTED] Found {report['drift_count']} drifted tool contract(s):")
            for d in report["drifts"]:
                print(f"  Tool: {d['tool']} ({d['script']})")
                if d["missing_in_schema"]:
                    print(f"    Missing in schema: {d['missing_in_schema']}")
                if d["phantom_in_schema"]:
                    print(f"    Phantom in schema: {d['phantom_in_schema']}")
            if not args.sync:
                print("Run with --sync to automatically reconcile schema from AST truth.")

        if "unregistered_tools" in report and report["unregistered_tools"]:
            print(f"\nUnregistered CLI tools ({len(report['unregistered_tools'])}):")
            for t in report["unregistered_tools"]:
                print(f"  - {t}")

    return exit_code if args.check else (0 if report["status"] == "PASS" or args.sync else 1)


if __name__ == "__main__":
    sys.exit(main())
