#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/runtime/action_bundler.py — Tier 6 Multi-Action Parallel Bundler
---------------------------------------------------------------------
Batches multiple independent tool actions (parallel file reads, test runs, static checks)
into a SINGLE execution round-trip.
Eliminates 50–75% of repeated prompt/prefix token re-evaluations across multi-step tasks.

Supported Batch Actions:
  - read_slice: Reads targeted [start_line, end_line] slice of file.
  - run_cmd: Runs command in isolated subprocess with timeout.
  - ast_slice: Extracts AST structural skeleton of file.

Usage:
  python3 tools/runtime/action_bundler.py --batch '[{"id": "1", "action": "read_slice", "path": "AGENTS.md", "lines": [1, 25]}]'
  python3 tools/runtime/action_bundler.py --demo
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

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


class ActionBundler:
    """Executes bundles of tool operations concurrently to eliminate API round-trips."""

    @classmethod
    def execute_single_action(cls, op: Dict[str, Any], repo_root: str = _REPO_ROOT) -> Dict[str, Any]:
        """Executes a single operation item."""
        op_id = op.get("id", "op")
        action = op.get("action", "")

        try:
            if action == "read_slice":
                file_path = os.path.join(repo_root, op.get("path", ""))
                if not os.path.exists(file_path):
                    return {"id": op_id, "status": "ERROR", "error": f"File not found: {file_path}"}

                lines_range = op.get("lines", [1, 50])
                start_l, end_l = lines_range[0], lines_range[1]

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    all_lines = f.readlines()

                slice_content = "".join(all_lines[max(0, start_l - 1):end_l])
                return {
                    "id": op_id,
                    "status": "SUCCESS",
                    "action": "read_slice",
                    "path": op.get("path"),
                    "lines": [start_l, min(end_l, len(all_lines))],
                    "total_file_lines": len(all_lines),
                    "content": slice_content
                }

            elif action == "run_cmd":
                cmd = op.get("cmd") or op.get("command")
                if not cmd:
                    return {"id": op_id, "status": "ERROR", "error": "Missing cmd parameter"}

                import shlex
                cmd_args = shlex.split(cmd) if isinstance(cmd, str) else cmd
                timeout = op.get("timeout", 30)
                res = subprocess.run(
                    cmd_args,
                    shell=False,
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                stdout = res.stdout.strip()
                stderr = res.stderr.strip()
                return {
                    "id": op_id,
                    "status": "SUCCESS" if res.returncode == 0 else "FAILED",
                    "exit_code": res.returncode,
                    "stdout": stdout[:1500] if len(stdout) > 1500 else stdout,
                    "stderr": stderr[:500] if len(stderr) > 500 else stderr
                }

            elif action == "ast_slice":
                from tools.context.context_slicer import ASTSkeletonExtractor
                file_path = os.path.join(repo_root, op.get("path", ""))
                skeleton = ASTSkeletonExtractor.extract_skeleton(file_path)
                return {
                    "id": op_id,
                    "status": "SUCCESS",
                    "action": "ast_slice",
                    "path": op.get("path"),
                    "skeleton": skeleton
                }

            else:
                return {"id": op_id, "status": "ERROR", "error": f"Unsupported bundled action: '{action}'"}

        except Exception as e:
            return {"id": op_id, "status": "EXCEPTION", "error": str(e)}

    @classmethod
    def execute_batch(cls, operations: List[Dict[str, Any]], max_workers: int = 4, repo_root: str = _REPO_ROOT) -> Dict[str, Any]:
        """Executes operations concurrently and aggregates results."""
        results: Dict[str, Any] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_op = {
                executor.submit(cls.execute_single_action, op, repo_root): op.get("id", f"op_{idx}")
                for idx, op in enumerate(operations)
            }
            for future in concurrent.futures.as_completed(future_to_op):
                op_id = future_to_op[future]
                try:
                    res = future.result()
                    results[op_id] = res
                except Exception as e:
                    results[op_id] = {"status": "EXCEPTION", "error": str(e)}

        return {
            "batch_size": len(operations),
            "completed": len(results),
            "round_trips_saved": max(0, len(operations) - 1),
            "results": results
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 6 Multi-Action Parallel Bundler")
    parser.add_argument("--batch", help="JSON string or file path containing array of operations")
    parser.add_argument("--demo", action="store_true", help="Run multi-action bundler demo")
    args = parser.parse_args()

    if args.demo:
        demo_ops = [
            {"id": "read_agents_anchor", "action": "read_slice", "path": "AGENTS.md", "lines": [1, 20]},
            {"id": "ast_check_enforcer", "action": "ast_slice", "path": "tools/core/cache_prefix_enforcer.py"},
            {"id": "lint_prefix_check", "action": "run_cmd", "cmd": "python3 tools/lint/lint_cache_prefix.py"}
        ]
        res = ActionBundler.execute_batch(demo_ops)
        print("=== Demo Tier 6 Multi-Action Bundler Execution ===")
        print(f"Batch Size          : {res['batch_size']} operations executed concurrently")
        print(f"Round-Trips Saved   : {res['round_trips_saved']} round-trips eliminated!")
        print("\nAggregated Results:")
        for op_id, r in res["results"].items():
            status = r.get("status")
            err = f" (Error: {r.get('error')})" if status != "SUCCESS" else ""
            print(f"  - [{status}] Operation '{op_id}'{err}")
        return 0

    if args.batch:
        if os.path.exists(args.batch):
            with open(args.batch, "r", encoding="utf-8") as f:
                ops = json.load(f)
        else:
            ops = json.loads(args.batch)

        res = ActionBundler.execute_batch(ops)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
