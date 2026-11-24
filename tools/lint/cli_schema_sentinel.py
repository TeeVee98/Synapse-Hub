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

    module_constants: Dict[str, Any] = {}
    module_dict_keys: Dict[str, List[Any]] = {}
    for stmt in tree.body:
        target_name = None
        val_node = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            target_name = stmt.targets[0].id
            val_node = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
            target_name = stmt.target.id
            val_node = stmt.value
        if target_name and val_node is not None:
            if isinstance(val_node, ast.Constant):
                module_constants[target_name] = val_node.value
            elif isinstance(val_node, ast.Dict):
                keys = [k.value for k in val_node.keys if isinstance(k, ast.Constant)]
                if len(keys) == len(val_node.keys):
                    module_dict_keys[target_name] = keys

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
                elif kw.arg == "default":
                    if isinstance(kw.value, ast.Constant):
                        has_default = True
                        default_val = kw.value.value
                    elif isinstance(kw.value, ast.Name) and kw.value.id in module_constants:
                        has_default = True
                        default_val = module_constants[kw.value.id]
                elif kw.arg == "required" and isinstance(kw.value, ast.Constant):
                    req_val = kw.value.value
                elif kw.arg == "choices":
                    if isinstance(kw.value, (ast.List, ast.Tuple)):
                        choices_val = [
                            elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)
                        ]
                    elif (
                        isinstance(kw.value, ast.Call)
                        and isinstance(kw.value.func, ast.Name)
                        and kw.value.func.id == "list"
                        and len(kw.value.args) == 1
                        and isinstance(kw.value.args[0], ast.Call)
                        and isinstance(kw.value.args[0].func, ast.Attribute)
                        and kw.value.args[0].func.attr == "keys"
                        and isinstance(kw.value.args[0].func.value, ast.Name)
                        and kw.value.args[0].func.value.id in module_dict_keys
                    ):
                        choices_val = list(module_dict_keys[kw.value.args[0].func.value.id])
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
            elif nargs_val in ("*", "+") or (isinstance(nargs_val, int) and nargs_val > 1):
                meta["type"] = "array"

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


def _resolve_excluded_paths(raw_excluded: Any, schema_dir: str) -> set[str]:
    """Normalizes excluded_internal_tools entries (list or dict) to absolute paths."""
    if isinstance(raw_excluded, dict):
        entries = list(raw_excluded.keys())
    elif isinstance(raw_excluded, (list, tuple, set)):
        entries = list(raw_excluded)
    else:
        return set()

    resolved: set[str] = set()
    for item in entries:
        if not isinstance(item, str) or not item.strip():
            continue
        if os.path.isabs(item):
            resolved.add(os.path.abspath(item))
        else:
            repo_candidate = os.path.abspath(os.path.join(_REPO_ROOT, item))
            schema_candidate = os.path.abspath(os.path.join(schema_dir, item))
            cwd_candidate = os.path.abspath(item)
            for candidate in (cwd_candidate, repo_candidate, schema_candidate):
                resolved.add(candidate)
    return resolved


def _compare_arg_fields(
    tool_name: str,
    arg_name: str,
    ast_meta: Dict[str, Any],
    schema_meta: Any,
) -> List[Dict[str, Any]]:
    """Compares type, required, default, and choices between AST and schema metadata."""
    if not isinstance(schema_meta, dict):
        return []

    diffs: List[Dict[str, Any]] = []

    if "type" in schema_meta:
        ast_type = ast_meta.get("type", "string")
        if schema_meta.get("type") != ast_type:
            diffs.append({
                "tool": tool_name,
                "arg": arg_name,
                "field": "type",
                "schema_value": schema_meta.get("type"),
                "ast_value": ast_type,
            })

    ast_req = bool(ast_meta.get("required", False))
    schema_req = bool(schema_meta.get("required", False))
    if schema_req != ast_req:
        diffs.append({
            "tool": tool_name,
            "arg": arg_name,
            "field": "required",
            "schema_value": schema_req,
            "ast_value": ast_req,
        })

    if "default" in schema_meta:
        if schema_meta.get("default") != ast_meta.get("default"):
            diffs.append({
                "tool": tool_name,
                "arg": arg_name,
                "field": "default",
                "schema_value": schema_meta.get("default"),
                "ast_value": ast_meta.get("default"),
            })
    elif "default" in ast_meta and not (
        ast_meta.get("type") == "boolean" and ast_meta.get("default") is False
    ):
        diffs.append({
            "tool": tool_name,
            "arg": arg_name,
            "field": "default",
            "schema_value": None,
            "ast_value": ast_meta.get("default"),
        })

    ast_choices = ast_meta.get("choices")
    schema_choices = schema_meta.get("choices")
    if ast_choices != schema_choices:
        diffs.append({
            "tool": tool_name,
            "arg": arg_name,
            "field": "choices",
            "schema_value": schema_choices,
            "ast_value": ast_choices,
        })

    return diffs


def validate_schema_drift(
    schema_path: str = "tools/tools_schema.json",
    tools_dir: str = "tools",
    tool_scope: Optional[str] = None,
    sync: bool = False,
    expand_all: bool = False,
    fail_unregistered: bool = False,
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
            "field_drifts": [],
            "unregistered_public": [],
            "excluded_internal_count": 0,
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
            "field_drifts": [],
            "unregistered_public": [],
            "excluded_internal_count": 0,
            "message": f"Malformed schema JSON: {e}",
        }, 1

    tools_dict = schema_data.get("tools", {})
    tools_to_check = [tool_scope] if tool_scope and tool_scope in tools_dict else list(tools_dict.keys())
    raw_excluded = schema_data.get("excluded_internal_tools", {})
    excluded_internal_count = len(raw_excluded) if isinstance(raw_excluded, (dict, list, tuple, set)) else 0
    excluded_abs_paths = _resolve_excluded_paths(
        raw_excluded, os.path.dirname(os.path.abspath(schema_path))
    )

    drifts: List[Dict[str, Any]] = []
    field_drifts: List[Dict[str, Any]] = []
    tools_checked = 0

    for tool_name in tools_to_check:
        tool_info = tools_dict[tool_name]
        script_rel_path = tool_info.get("path", "")
        script_abs_path = os.path.abspath(script_rel_path)
        if not os.path.isfile(script_abs_path) and not os.path.isabs(script_rel_path):
            repo_candidate = os.path.abspath(os.path.join(_REPO_ROOT, script_rel_path))
            if os.path.isfile(repo_candidate):
                script_abs_path = repo_candidate

        if not os.path.isfile(script_abs_path):
            raw_schema_args = tool_info.get("args", {})
            phantom_args = list(raw_schema_args.keys()) if isinstance(raw_schema_args, dict) else list(raw_schema_args)
            drifts.append({
                "tool": tool_name,
                "script": script_rel_path,
                "missing_in_schema": [],
                "phantom_in_schema": phantom_args,
                "field_drifts": [],
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
        tool_field_drifts: List[Dict[str, Any]] = []
        if isinstance(schema_args, dict):
            for arg_name in sorted(ast_names & schema_names):
                tool_field_drifts.extend(
                    _compare_arg_fields(tool_name, arg_name, ast_args[arg_name], schema_args[arg_name])
                )

        if missing_in_schema or phantom_in_schema or tool_field_drifts:
            drift_entry: Dict[str, Any] = {
                "tool": tool_name,
                "script": script_rel_path,
                "missing_in_schema": missing_in_schema,
                "phantom_in_schema": phantom_in_schema,
                "ast_arguments": sorted(list(ast_names)),
            }
            if tool_field_drifts:
                drift_entry["field_drifts"] = tool_field_drifts
                field_drifts.extend(tool_field_drifts)
            drifts.append(drift_entry)

            if sync:
                # Synchronize schema from AST code truth
                tool_info["args"] = ast_args

    unregistered_tools: List[str] = []
    unregistered_public: List[str] = []
    if (expand_all or fail_unregistered) and os.path.isdir(tools_dir):
        registered_paths = set()
        for t in tools_dict.values():
            p = t.get("path", "")
            if p:
                registered_paths.add(os.path.abspath(p))
                if not os.path.isabs(p):
                    registered_paths.add(os.path.abspath(os.path.join(_REPO_ROOT, p)))

        for root, _, files in os.walk(tools_dir):
            for file in files:
                if file.endswith(".py"):
                    full_p = os.path.abspath(os.path.join(root, file))
                    if full_p not in registered_paths and has_argparse_entrypoint(full_p):
                        try:
                            rel_p = os.path.relpath(full_p, _REPO_ROOT)
                        except ValueError:
                            rel_p = os.path.relpath(full_p, tools_dir)
                        rel_p = rel_p.replace("\\", "/")
                        unregistered_tools.append(rel_p)
                        if full_p not in excluded_abs_paths:
                            unregistered_public.append(rel_p)
        unregistered_tools.sort()
        unregistered_public.sort()

        if fail_unregistered and unregistered_public:
            for unreg in unregistered_public:
                drifts.append({
                    "tool": unreg,
                    "script": unreg,
                    "error": "UNREGISTERED_TOOL",
                    "missing_in_schema": [],
                    "phantom_in_schema": [],
                    "message": f"Script '{unreg}' contains CLI argparse entry point but is not registered in {schema_path}."
                })

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
        "field_drifts": field_drifts,
        "unregistered_public": unregistered_public,
        "excluded_internal_count": excluded_internal_count,
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
    parser.add_argument(
        "--fail-unregistered",
        action="store_true",
        help="Fail with exit code 1 if any script with argparse in tools-dir is missing from schema",
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
        fail_unregistered=args.fail_unregistered,
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
                if d.get("missing_in_schema"):
                    print(f"    Missing in schema: {d['missing_in_schema']}")
                if d.get("phantom_in_schema"):
                    print(f"    Phantom in schema: {d['phantom_in_schema']}")
                if d.get("field_drifts"):
                    for fd in d["field_drifts"]:
                        print(f"    Field drift ({fd['arg']}.{fd['field']}): schema={fd['schema_value']!r} vs ast={fd['ast_value']!r}")
                if d.get("message"):
                    print(f"    Notice: {d['message']}")
            if not args.sync:
                print("Run with --sync to automatically reconcile schema from AST truth.")

        if "unregistered_tools" in report and report["unregistered_tools"]:
            print(f"\nUnregistered CLI tools ({len(report['unregistered_tools'])}):")
            for t in report["unregistered_tools"]:
                print(f"  - {t}")

    return exit_code if args.check else (0 if report["status"] == "PASS" or args.sync else 1)


if __name__ == "__main__":
    sys.exit(main())
