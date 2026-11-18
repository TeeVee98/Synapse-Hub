#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/orchestration/worktree_manager.py — Multi-Agent Git Worktree Orchestration Harness
---------------------------------------------------------------------------------------
Inspired by ecc2 Rust Worktree Orchestrator (affaan-m/ecc).
Provides isolated git worktree environments for concurrent AI subagents
(e.g. pom-crafter and failure-analyst) running in parallel without git index
lock collisions or dirty working tree interference.

Cross-platform: Windows, macOS, Linux. Handles Windows read-only file lock
cleanup gracefully.

Usage:
  python3 tools/orchestration/worktree_manager.py create --branch subagent-fix-1
  python3 tools/orchestration/worktree_manager.py list
  python3 tools/orchestration/worktree_manager.py cleanup --path <worktree_dir>
"""

import os
import sys
import stat
import shutil
import subprocess
import argparse
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _remove_readonly(func, path, exc_info):
    """Windows-safe error handler for shutil.rmtree to unlink read-only git files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


def run_git(args: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Executes a git command with UTF-8 encoding."""
    cmd = ["git"] + args
    res = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return res.returncode, res.stdout.strip(), res.stderr.strip()


class WorktreeManager:
    def __init__(self, repo_root: str = REPO_ROOT):
        self.repo_root = repo_root

    def list_worktrees(self) -> List[Dict[str, str]]:
        """Returns a list of all active git worktrees."""
        code, out, err = run_git(["worktree", "list", "--porcelain"], cwd=self.repo_root)
        if code != 0:
            return []

        worktrees = []
        current: Dict[str, str] = {}
        for line in out.splitlines():
            line = line.strip()
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
                continue
            if line.startswith("worktree "):
                current["path"] = line.split("worktree ", 1)[1].strip()
            elif line.startswith("HEAD "):
                current["head"] = line.split("HEAD ", 1)[1].strip()
            elif line.startswith("branch "):
                current["branch"] = line.split("branch ", 1)[1].strip()
            elif line == "bare":
                current["bare"] = "true"

        if current:
            worktrees.append(current)
        return worktrees

    def create_worktree(self, branch: str, target_dir: Optional[str] = None, base: str = "HEAD") -> Tuple[bool, str]:
        """Creates a new isolated git worktree for a subagent."""
        if not target_dir:
            # Default to a sibling scratch directory outside git index
            base_name = f"worktree_{branch.replace('/', '_')}"
            target_dir = os.path.abspath(os.path.join(self.repo_root, "..", base_name))

        # Check if worktree directory already exists
        if os.path.exists(target_dir):
            return False, f"Target directory already exists: {target_dir}"

        # Run git worktree add
        code, out, err = run_git(
            ["worktree", "add", "-b", branch, target_dir, base],
            cwd=self.repo_root,
        )
        if code != 0:
            # If branch already exists, try adding without -b
            code2, out2, err2 = run_git(
                ["worktree", "add", target_dir, branch],
                cwd=self.repo_root,
            )
            if code2 != 0:
                return False, f"Failed to create worktree: {err or err2}"

        return True, target_dir

    def cleanup_worktree(self, target_dir: str, force: bool = False) -> Tuple[bool, str]:
        """Safely removes an agent worktree and prunes git worktree metadata."""
        target_dir = os.path.abspath(target_dir)

        # 1. Run git worktree remove
        remove_args = ["worktree", "remove", target_dir]
        if force:
            remove_args.append("--force")

        code, out, err = run_git(remove_args, cwd=self.repo_root)

        # 2. If git removed it or if physical directory remains, clean up
        if os.path.exists(target_dir):
            try:
                shutil.rmtree(target_dir, onerror=_remove_readonly)
            except Exception as e:
                return False, f"Directory cleanup error: {e}"

        # 3. Prune worktree metadata
        run_git(["worktree", "prune"], cwd=self.repo_root)
        return True, f"Cleaned up worktree at: {target_dir}"


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Git Worktree Orchestration Harness")
    subparsers = parser.add_subparsers(dest="command")

    p_list = subparsers.add_parser("list", help="List all active git worktrees")

    p_create = subparsers.add_parser("create", help="Create an isolated worktree for subagent")
    p_create.add_argument("--branch", required=True, help="Branch name for the worktree")
    p_create.add_argument("--dir", help="Target directory (optional, defaults to sibling dir)")
    p_create.add_argument("--base", default="HEAD", help="Base commit/branch (default: HEAD)")

    p_clean = subparsers.add_parser("cleanup", help="Safely remove an agent worktree")
    p_clean.add_argument("--path", required=True, help="Path to worktree directory")
    p_clean.add_argument("--force", action="store_true", help="Force remove worktree")

    args = parser.parse_args()
    mgr = WorktreeManager()

    if not args.command or args.command == "list":
        wt_list = mgr.list_worktrees()
        print(f"[WORKTREE HARNESS] Active Git Worktrees: {len(wt_list)}")
        for idx, wt in enumerate(wt_list, 1):
            br = wt.get("branch", "detached")
            print(f"  {idx}. [{br}] {wt.get('path')} (Commit: {wt.get('head', '')[:8]})")

    elif args.command == "create":
        ok, res = mgr.create_worktree(args.branch, target_dir=args.dir, base=args.base)
        if ok:
            print(f"[WORKTREE CREATED] Path: {res}")
        else:
            print(f"[FAIL] {res}")
            sys.exit(1)

    elif args.command == "cleanup":
        ok, msg = mgr.cleanup_worktree(args.path, force=args.force)
        if ok:
            print(f"[WORKTREE CLEANUP] {msg}")
        else:
            print(f"[FAIL] {msg}")
            sys.exit(1)


if __name__ == "__main__":
    main()
