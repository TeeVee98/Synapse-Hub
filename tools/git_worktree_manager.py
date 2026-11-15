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

import sys
import os
import re
import subprocess
import argparse
import json
import time
from typing import Dict, List, Any, Optional

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

    def create_worktree(self, agent_id: str, branch_name: Optional[str] = None) -> Dict[str, Any]:
        os.makedirs(self.base_dir, exist_ok=True)
        timestamp = int(time.time())
        clean_agent_id = re.sub(r'[^a-zA-Z0-9_.-]', '-', agent_id)
        branch = branch_name or f"subagent/{clean_agent_id}-{timestamp}"
        target_path = os.path.abspath(os.path.join(self.base_dir, f"{clean_agent_id}-{timestamp}"))

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

        return {
            "success": True,
            "agent_id": agent_id,
            "worktree_path": target_path,
            "branch": branch,
            "created_at": timestamp
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

def main():
    parser = argparse.ArgumentParser(description="Manage ephemeral git worktrees for subagent isolation.")
    parser.add_argument("action", choices=["list", "create", "remove", "prune"], help="Action to execute.")
    parser.add_argument("--agent-id", help="Subagent identifier for creation.")
    parser.add_argument("--path", help="Worktree path for removal.")
    parser.add_argument("--json", action="store_true", help="Output JSON format.")
    args = parser.parse_args()

    manager = WorktreeManager()

    if args.action == "list":
        items = manager.list_worktrees()
        if args.json:
            print(json.dumps(items, indent=2))
        else:
            print(f"[WORKTREE MANAGER] Active Worktrees ({len(items)}):")
            for it in items:
                print(f"  - {it.get('path')} ({it.get('branch', 'detached')})")

    elif args.action == "create":
        if not args.agent_id:
            print("Error: --agent-id is required for create.", file=sys.stderr)
            sys.exit(1)
        res = manager.create_worktree(args.agent_id)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res["success"]:
                print(f"[WORKTREE CREATED] Path: {res['worktree_path']} (Branch: {res['branch']})")
            else:
                print(f"[ERROR] Failed to create worktree: {res.get('error')}", file=sys.stderr)
                sys.exit(1)

    elif args.action == "remove":
        if not args.path:
            print("Error: --path is required for remove.", file=sys.stderr)
            sys.exit(1)
        res = manager.remove_worktree(args.path)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res["success"]:
                print(f"[WORKTREE REMOVED] {res['path']} - Deleted branch: {res.get('deleted_branch')}")
            else:
                print(f"[ERROR] Failed to remove worktree: {res.get('error')}", file=sys.stderr)
                sys.exit(1)

    elif args.action == "prune":
        res = manager.prune_stale()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[WORKTREE PRUNED] Output: {res['output'] or 'Zero stale worktrees.'}")

if __name__ == "__main__":
    main()
