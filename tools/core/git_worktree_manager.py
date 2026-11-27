#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/git_worktree_manager.py — Ephemeral Git Worktree Manager for Subagents
Inspired by Jesse Vincent (obra/superpowers) and Shan Rais subagent isolation standard.
Allocates, inspects, and cleans up isolated worktrees so concurrent subagents
do not pollute or conflict with the main working directory.
100% UTF-8 No BOM.
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

WORKTREES_ROOT = os.path.join(".synapse", "worktrees")

def run_git(args: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd or os.getcwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

class WorktreeManager:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.join(os.getcwd(), WORKTREES_ROOT)

    def list_worktrees(self) -> List[Dict[str, str]]:
        res = run_git(["worktree", "list", "--porcelain"])
        if res.returncode != 0:
            return []

        worktrees = []
        current: Dict[str, str] = {}
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
            elif line.startswith("worktree "):
                current["path"] = line[len("worktree "):].strip()
            elif line.startswith("branch "):
                current["branch"] = line[len("branch "):].strip()
            elif line.startswith("HEAD "):
                current["head"] = line[len("HEAD "):].strip()
        if current:
            worktrees.append(current)
        return worktrees

    def create_worktree(
        self,
        agent_id: str,
        branch_name: Optional[str] = None,
        plan_path: Optional[str] = None,
        share_dependencies: bool = True,
    ) -> Dict[str, Any]:
        os.makedirs(self.base_dir, exist_ok=True)
        timestamp = int(time.time())
        clean_agent_id = re.sub(r'[^a-zA-Z0-9_.-]', '-', agent_id)
        branch = branch_name or f"subagent/{clean_agent_id}-{timestamp}"
        target_path = os.path.abspath(os.path.join(self.base_dir, f"{clean_agent_id}-{timestamp}"))

        abs_base = os.path.abspath(self.base_dir)
        source_root = (
            os.path.dirname(os.path.dirname(abs_base))
            if os.path.basename(os.path.dirname(abs_base)) == ".synapse"
            else os.getcwd()
        )

        res = run_git(["worktree", "add", "-b", branch, target_path, "HEAD"])
        if res.returncode != 0:
            # Fallback if branch already exists
            res = run_git(["worktree", "add", target_path, "HEAD"])
            if res.returncode != 0:
                return {
                    "success": False,
                    "error": res.stderr.strip() or "Failed to create worktree",
                    "path": target_path
                }

        linked_deps: Dict[str, Any] = {}
        if share_dependencies:
            try:
                from tools.orchestration.worktree_manager import link_shared_dependencies

                linked_deps = link_shared_dependencies(source_root, target_path)
            except ImportError:
                linked_deps = {"linked": [], "errors": ["worktree_manager unavailable"]}

        copied_plan_path: Optional[str] = None
        if plan_path and str(plan_path).strip():
            raw_plan = str(plan_path).strip()
            src_plan = raw_plan if os.path.isabs(raw_plan) else os.path.join(source_root, raw_plan)
            if os.path.isfile(src_plan):
                rel_dest = os.path.join(".synapse", "plans", os.path.basename(src_plan))
                dest_plan = os.path.join(target_path, rel_dest)
                os.makedirs(os.path.dirname(dest_plan), exist_ok=True)
                shutil.copy2(src_plan, dest_plan)
                copied_plan_path = rel_dest.replace("\\", "/")

        return {
            "success": True,
            "agent_id": agent_id,
            "worktree_path": target_path,
            "branch": branch,
            "created_at": timestamp,
            "linked_dependencies": linked_deps,
            "copied_plan_path": copied_plan_path,
        }

    def remove_worktree(self, worktree_path: str, delete_branch: bool = True) -> Dict[str, Any]:
        # Determine branch before removal
        branch_to_delete = None
        if delete_branch:
            for wt in self.list_worktrees():
                if os.path.abspath(wt.get("path", "")) == os.path.abspath(worktree_path):
                    branch_ref = wt.get("branch", "")
                    if branch_ref.startswith("refs/heads/"):
                        branch_to_delete = branch_ref[len("refs/heads/"):]
                    elif branch_ref:
                        branch_to_delete = branch_ref
                    break

        res = run_git(["worktree", "remove", "--force", worktree_path])
        success = res.returncode == 0

        # Run git worktree prune
        run_git(["worktree", "prune"])

        # Clean up ephemeral subagent branch if requested
        if success and delete_branch and branch_to_delete and branch_to_delete.startswith("subagent/"):
            run_git(["branch", "-D", branch_to_delete])

        return {
            "success": success,
            "path": worktree_path,
            "deleted_branch": branch_to_delete if (success and delete_branch) else None,
            "error": res.stderr.strip() if not success else None
        }

    def prune_stale(self) -> Dict[str, Any]:
        res = run_git(["worktree", "prune", "-v"])
        return {
            "success": res.returncode == 0,
            "output": res.stdout.strip()
        }

def _emit_worktree_result(res: Dict[str, Any], as_json: bool, success_msg: str, fail_prefix: str) -> None:
    """Formats worktree CLI action result and exits non-zero on failure."""
    if as_json:
        print(json.dumps(res, indent=2))
        return
    if res.get("success"):
        print(success_msg)
        return
    print(f"[ERROR] {fail_prefix}: {res.get('error')}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Manage ephemeral git worktrees for subagent isolation.")
    parser.add_argument("action", choices=["list", "create", "remove", "prune"], help="Action to execute.")
    parser.add_argument("--agent-id", help="Subagent identifier for creation.")
    parser.add_argument("--plan", help="Optional plan file to copy into the isolated worktree.")
    parser.add_argument("--no-share-deps", action="store_true", help="Skip linking shared node_modules/.venv directories.")
    parser.add_argument("--path", help="Worktree path for removal.")
    parser.add_argument("--json", action="store_true", help="Output JSON format.")
    args = parser.parse_args()

    manager = WorktreeManager()

    if args.action == "list":
        items = manager.list_worktrees()
        if args.json:
            print(json.dumps(items, indent=2))
            return
        print(f"[WORKTREE MANAGER] Active Worktrees ({len(items)}):")
        for it in items:
            print(f"  - {it.get('path')} ({it.get('branch', 'detached')})")
        return

    if args.action == "create":
        if not args.agent_id:
            print("Error: --agent-id is required for create.", file=sys.stderr)
            sys.exit(1)
        res = manager.create_worktree(
            args.agent_id,
            plan_path=getattr(args, "plan", None),
            share_dependencies=not getattr(args, "no_share_deps", False),
        )
        msg = f"[WORKTREE CREATED] Path: {res.get('worktree_path')} (Branch: {res.get('branch')})"
        _emit_worktree_result(res, args.json, msg, "Failed to create worktree")
        return

    if args.action == "remove":
        if not args.path:
            print("Error: --path is required for remove.", file=sys.stderr)
            sys.exit(1)
        res = manager.remove_worktree(args.path)
        msg = f"[WORKTREE REMOVED] {res.get('path')} - Deleted branch: {res.get('deleted_branch')}"
        _emit_worktree_result(res, args.json, msg, "Failed to remove worktree")
        return

    res = manager.prune_stale()
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"[WORKTREE PRUNED] Output: {res['output'] or 'Zero stale worktrees.'}")

if __name__ == "__main__":
    main()
