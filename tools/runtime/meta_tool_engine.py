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
import ast
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

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

from tools.context.high_density_encoder import HighDensityEncoder
from tools.core.bm25_retriever import BM25Index
from tools.runtime.action_bundler import ActionBundler
from tools.runtime.codeact_engine import CodeActEngine
from tools.runtime.trajectory_compressor import TrajectoryCompressor

TOOLS_SCHEMA_PATH = os.path.join(_REPO_ROOT, "tools", "tools_schema.json")
SKILLS_INDEX_PATH = os.path.join(_REPO_ROOT, "skills_index.json")

_SAFE_PREDICATE_NAMES = frozenset({
    "r", "item", "record", "True", "False", "None",
    "len", "str", "int", "float", "bool", "abs", "min", "max", "any", "all",
})
_SAFE_PREDICATE_ATTRS = frozenset({
    "get", "lower", "upper", "strip", "startswith", "endswith", "keys", "values", "items",
})
_SAFE_PREDICATE_NODES = (
    ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.IfExp,
    ast.Constant, ast.Name, ast.Load, ast.Subscript, ast.Slice,
    ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Attribute, ast.Call,
    ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
    ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd,
)


def _validate_predicate_expr(expr: str) -> Optional[Tuple[bool, str]]:
    """Validates that a filter predicate is a deterministic, AST-safe Python expression.
    Returns None when valid, or (is_security_violation, error_message) when rejected.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as err:
        return False, f"Invalid predicate syntax: {err}"

    for node in ast.walk(tree):
        if not isinstance(node, _SAFE_PREDICATE_NODES):
            return True, f"Disallowed AST node in predicate: {type(node).__name__}"
        if isinstance(node, ast.Name) and node.id not in _SAFE_PREDICATE_NAMES:
            return True, f"Disallowed identifier in predicate: {node.id}"
        if isinstance(node, ast.Attribute) and node.attr not in _SAFE_PREDICATE_ATTRS:
            return True, f"Disallowed attribute in predicate: {node.attr}"
    return None


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
        self.schema_source: Optional[str] = None
        self._tools_catalog: Dict[str, Any] = {}
        self._skills_catalog: List[Dict[str, Any]] = []
        self._bm25_index: Optional[BM25Index] = None
        self._load_catalogs()

    def _load_json_dict(self, path: str) -> Optional[Dict[str, Any]]:
        """Loads a JSON object file safely, returning None if missing or malformed."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                tools_obj = data.get("tools", data)
                if isinstance(tools_obj, dict):
                    return tools_obj
        except (OSError, json.JSONDecodeError, ValueError):
            return None
        return None

    def _load_catalogs(self) -> None:
        self._tools_catalog = {}
        self.schema_source = None
        self._bm25_index = None

        schema_candidates = (
            ("tools_schema.min.json", os.path.join(self.repo_root, "tools", "tools_schema.min.json")),
            ("tools_schema.json", os.path.join(self.repo_root, "tools", "tools_schema.json")),
        )
        for source_name, candidate_path in schema_candidates:
            loaded = self._load_json_dict(candidate_path)
            if loaded is not None:
                self._tools_catalog = loaded
                self.schema_source = source_name
                break

        skills_path = os.path.join(self.repo_root, "skills_index.json")
        if os.path.exists(skills_path):
            try:
                with open(skills_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        skills_val = data.get("skills", [])
                        self._skills_catalog = skills_val if isinstance(skills_val, list) else []
                    elif isinstance(data, list):
                        self._skills_catalog = data
            except (OSError, json.JSONDecodeError, ValueError):
                self._skills_catalog = []

    def _ensure_bm25_index(self) -> BM25Index:
        """Lazily builds and caches a BM25Index over all loaded CLI tools and skills."""
        if self._bm25_index is not None:
            return self._bm25_index

        index = BM25Index()
        for name, defn in self._tools_catalog.items():
            if not isinstance(defn, dict):
                continue
            raw_summary = defn.get("summary", "")
            cmd_raw = defn.get("command", defn.get("cmd")) or ""
            arg_keys = " ".join(defn.get("args", {}).keys()) if isinstance(defn.get("args"), dict) else ""
            name_words = name.replace("_", " ").replace("-", " ")
            index.add_document(
                doc_id=f"tool:{name}",
                title=f"{name} {name_words}",
                content=f"{raw_summary} {cmd_raw} {arg_keys}",
                source="tool",
            )

        for skill in self._skills_catalog:
            if not isinstance(skill, dict):
                continue
            s_id = str(skill.get("id", ""))
            s_dom = str(skill.get("domain", ""))
            s_sum = str(skill.get("summary", ""))
            triggers = " ".join(str(t) for t in skill.get("stack_triggers", []))
            index.add_document(
                doc_id=f"skill:{s_id}",
                title=s_id,
                content=f"{s_dom} {triggers} {s_sum}",
                source="skill",
            )

        index.build()
        self._bm25_index = index
        return index

    def search_tools(
        self,
        query: str,
        domain: Optional[str] = None,
        compact_format: str = "json",
    ) -> Any:
        """Searches tools and skills using lazy BM25 ranking + exact keyword boosts."""
        q = query.lower().strip() if isinstance(query, str) else ""
        dom = domain.lower().strip() if isinstance(domain, str) else ""
        fmt = (compact_format or "json").strip().lower()
        if not q and not dom:
            return HighDensityEncoder.encode_records_to_toon([]) if fmt == "toon" else []

        bm25 = self._ensure_bm25_index()
        bm25_scores: Dict[str, float] = {}
        if q and bm25.doc_count > 0:
            hits = bm25.search(q, top_k=bm25.doc_count)
            bm25_scores = {h["doc_id"]: float(h["score"]) for h in hits}

        results: List[Dict[str, Any]] = []

        # 1. Search CLI Tools
        if q:
            for name, defn in self._tools_catalog.items():
                if not isinstance(defn, dict):
                    continue
                score = bm25_scores.get(f"tool:{name}", 0.0)
                name_lower = name.lower()
                raw_summary = defn.get("summary", "")
                summary = raw_summary.lower()
                cmd_raw = defn.get("command", defn.get("cmd"))
                cmd = (cmd_raw or "").lower()

                if q in name_lower:
                    score += 10.0
                if q in summary:
                    score += 5.0
                if q in cmd:
                    score += 3.0

                if score > 0:
                    results.append({
                        "kind": "tool",
                        "name": name,
                        "command": cmd_raw,
                        "summary": raw_summary,
                        "args": defn.get("args", {}),
                        "score": score,
                    })

        # 2. Search Skills
        for skill in self._skills_catalog:
            if not isinstance(skill, dict):
                continue
            s_id_raw = skill.get("id", "")
            s_id = s_id_raw.lower()
            s_dom = (skill.get("domain") or "").lower()
            s_sum = (skill.get("summary") or "").lower()
            triggers = [t.lower() for t in skill.get("stack_triggers", [])]
            score = bm25_scores.get(f"skill:{s_id_raw}", 0.0)

            if dom and dom in s_dom:
                score += 8.0
            if q:
                if q in s_id:
                    score += 10.0
                if any(q in t for t in triggers):
                    score += 8.0
                if q in s_sum:
                    score += 4.0

            if score > 0:
                results.append({
                    "kind": "skill",
                    "id": s_id_raw,
                    "domain": skill.get("domain"),
                    "summary": skill.get("summary"),
                    "score": score,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        compact_results = [{k: v for k, v in r.items() if k != "score"} for r in results[:5]]
        if fmt == "toon":
            return HighDensityEncoder.encode_records_to_toon(compact_results)
        return compact_results

    def execute_tool(
        self,
        name: str,
        args: Optional[Dict[str, Any]] = None,
        mask_observations: bool = True,
    ) -> Dict[str, Any]:
        """Executes a tool by name with arguments via Python subprocess and optional observation masking."""
        args = args or {}
        tool_def = self._tools_catalog.get(name)
        if not isinstance(tool_def, dict):
            # Check if name is a script path directly
            candidate = os.path.join(self.repo_root, name if name.endswith(".py") else f"tools/{name}.py")
            if not os.path.exists(candidate):
                return {
                    "status": "ERROR",
                    "exit_code": 127,
                    "error": f"Tool '{name}' not found in catalog or filesystem.",
                    "masked": False,
                    "log_file": None,
                }
            cmd_parts = [sys.executable, candidate]
        else:
            raw_cmd = tool_def.get("command") or tool_def.get("cmd")
            if raw_cmd:
                exe_prefix = f"{sys.executable} "
                if sys.executable and raw_cmd.startswith(exe_prefix):
                    cmd_parts = [sys.executable] + raw_cmd[len(exe_prefix):].split()
                else:
                    cmd_parts = raw_cmd.split()
                    if cmd_parts and cmd_parts[0] in ("python", "python3"):
                        cmd_parts[0] = sys.executable
            else:
                cmd_parts = [sys.executable, str(tool_def.get("path"))]
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
            is_truncated = len(stdout) > 2000 or len(stderr) > 1000
            out_stdout = stdout[:2000] if len(stdout) > 2000 else stdout
            masked = False
            log_file: Optional[str] = None

            if mask_observations and stdout:
                obs_dir = os.path.join(self.repo_root, ".synapse", "observations")
                obs_res = TrajectoryCompressor.mask_tool_observation(
                    name,
                    args,
                    stdout,
                    log_dir=obs_dir,
                )
                if obs_res.get("masked"):
                    masked = True
                    log_file = obs_res.get("log_file")
                    out_stdout = obs_res.get("content", out_stdout)

            return {
                "status": "SUCCESS" if res.returncode == 0 else "FAILED",
                "exit_code": res.returncode,
                "stdout": out_stdout,
                "stderr": stderr[:1000] if len(stderr) > 1000 else stderr,
                "truncated": is_truncated,
                "masked": masked,
                "log_file": log_file,
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "exit_code": 124,
                "error": "Execution timed out after 60s",
                "masked": False,
                "log_file": None,
            }
        except Exception as e:
            return {
                "status": "EXCEPTION",
                "exit_code": 1,
                "error": str(e),
                "masked": False,
                "log_file": None,
            }

    def execute_batch(
        self,
        actions: List[Dict[str, Any]],
        mask_observations: bool = True,
    ) -> Dict[str, Any]:
        """Executes a batch of actions concurrently via ActionBundler with optional observation masking."""
        if not isinstance(actions, list) or not all(isinstance(a, dict) for a in actions):
            return {
                "status": "ERROR",
                "error": "actions must be a list of action dictionaries.",
                "batch_size": 0,
                "completed": 0,
                "round_trips_saved": 0,
                "results": {},
                "masked": False,
                "masked_count": 0,
                "log_file": None,
                "log_files": [],
            }
        if not actions:
            return {
                "status": "SUCCESS",
                "batch_size": 0,
                "completed": 0,
                "round_trips_saved": 0,
                "results": {},
                "masked": False,
                "masked_count": 0,
                "log_file": None,
                "log_files": [],
            }

        batch_res = ActionBundler.execute_batch(actions, repo_root=self.repo_root)
        obs_dir = os.path.join(self.repo_root, ".synapse", "observations")
        masked_count = 0
        log_files: List[str] = []
        success_count = 0

        for op_id, item in batch_res["results"].items():
            if item.get("status") == "SUCCESS":
                success_count += 1
            item["masked"] = False
            item["log_file"] = None
            item["truncated"] = False

            for field in ("content", "stdout", "skeleton"):
                raw_val = item.get(field)
                if isinstance(raw_val, str) and raw_val:
                    if mask_observations:
                        obs_res = TrajectoryCompressor.mask_tool_observation(
                            f"batch_{op_id}",
                            {"action": item.get("action", "op")},
                            raw_val,
                            log_dir=obs_dir,
                        )
                        if obs_res.get("masked"):
                            item[field] = obs_res["content"]
                            item["masked"] = True
                            item["log_file"] = obs_res.get("log_file")
                            masked_count += 1
                            if item["log_file"]:
                                log_files.append(item["log_file"])
                            continue
                    if len(raw_val) > 2000:
                        item[field] = raw_val[:2000]
                        item["truncated"] = True

        total_items = len(batch_res["results"])
        if success_count == total_items:
            overall_status = "SUCCESS"
        elif success_count > 0:
            overall_status = "PARTIAL"
        else:
            overall_status = "FAILED"

        return {
            "status": overall_status,
            "batch_size": batch_res["batch_size"],
            "completed": batch_res["completed"],
            "round_trips_saved": batch_res["round_trips_saved"],
            "results": batch_res["results"],
            "masked": masked_count > 0,
            "masked_count": masked_count,
            "log_file": log_files[0] if log_files else None,
            "log_files": log_files,
        }

    def filter_output_in_memory(
        self,
        records: List[Dict[str, Any]],
        predicate_expr: str,
    ) -> Dict[str, Any]:
        """Filters structured records in memory via CodeActEngine using an AST-safe predicate."""
        if not isinstance(records, list):
            return {
                "status": "ERROR",
                "error": "records must be a list of dictionaries.",
                "filtered": [],
                "input_count": 0,
                "matched_count": 0,
                "tokens_saved": 0,
                "savings_percent": 0.0,
                "security_violation": False,
            }
        if not isinstance(predicate_expr, str) or not predicate_expr.strip():
            return {
                "status": "ERROR",
                "error": "predicate_expr must be a non-empty string.",
                "filtered": [],
                "input_count": len(records),
                "matched_count": 0,
                "tokens_saved": 0,
                "savings_percent": 0.0,
                "security_violation": False,
            }

        expr = predicate_expr.strip()
        validation_err = _validate_predicate_expr(expr)
        if validation_err is not None:
            is_sec_violation, err_msg = validation_err
            return {
                "status": "ERROR",
                "error": err_msg,
                "filtered": [],
                "input_count": len(records),
                "matched_count": 0,
                "tokens_saved": 0,
                "savings_percent": 0.0,
                "security_violation": is_sec_violation,
            }

        if not records:
            return {
                "status": "SUCCESS",
                "filtered": [],
                "input_count": 0,
                "matched_count": 0,
                "tokens_saved": 0,
                "savings_percent": 0.0,
                "security_violation": False,
            }

        raw_json = json.dumps(records, ensure_ascii=False)
        filter_script = (
            "import json, sys\n"
            "data = json.loads(sys.stdin.read())\n"
            "out = []\n"
            "for r in data:\n"
            "    item = record = r\n"
            f"    if bool({expr}):\n"
            "        out.append(r)\n"
            "print(json.dumps(out, ensure_ascii=False))\n"
        )
        codeact = CodeActEngine(working_dir=self.repo_root)
        exec_res = codeact.filter_in_memory(raw_data=raw_json, filter_script=filter_script)
        if exec_res.get("security_violation") or exec_res.get("exit_code") != 0:
            return {
                "status": "ERROR",
                "error": exec_res.get("stderr") or "In-memory filter execution failed.",
                "filtered": [],
                "input_count": len(records),
                "matched_count": 0,
                "tokens_saved": 0,
                "savings_percent": 0.0,
                "security_violation": bool(exec_res.get("security_violation")),
            }

        filtered = json.loads(exec_res["stdout"])
        savings = codeact.calculate_token_savings(raw_json, filter_script, exec_res["stdout"])
        return {
            "status": "SUCCESS",
            "filtered": filtered,
            "input_count": len(records),
            "matched_count": len(filtered),
            "tokens_saved": savings["tokens_saved"],
            "savings_percent": savings["savings_percent"],
            "security_violation": False,
        }


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
