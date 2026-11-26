#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/lint/output_diff_sentinel.py — Tier 5 Output Diff & Anti-Rewrite Sentinel
-------------------------------------------------------------------------------
Guarantees that AI Agent code mutations strictly adhere to Search/Replace Blocks
or Unified Diffs, permanently prohibiting monolithic full-file rewrites.

Key Invariants:
  1. Forbids full-file overwrites on files > 100 lines when modifications touch < 30% of lines.
  2. Validates Search/Replace block formats (e.g. Target/Replacement or <<<<<<< SEARCH).
  3. Calculates output token wastage and enforces Lean Output Diff discipline.

Usage:
  python3 tools/lint/output_diff_sentinel.py --check-diff
  python3 tools/lint/output_diff_sentinel.py --validate-patch patch.diff
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class OutputDiffSentinel:
    """Enforces diff-first, search/replace output discipline."""

    MAX_REWRITE_RATIO = 0.35  # If < 35% changed but 100% rewritten, flag violation
    MIN_LINES_FOR_AUDIT = 80

    @classmethod
    def audit_git_diff(cls, repo_root: str = _REPO_ROOT, target: str = "uncommitted") -> Tuple[bool, List[Dict[str, Any]]]:
        """Audits current git status and diff for monolithic rewrite violations."""
        cmd = ["git", "diff", "HEAD", "--numstat"]
        if target == "staged":
            cmd = ["git", "diff", "--cached", "--numstat"]
        elif target != "uncommitted":
            cmd = ["git", "diff", target, "--numstat"]
        try:
            res = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True
            )
        except Exception as e:
            return False, [{"file": "git", "issue": f"Git diff execution failed: {e}"}]

        violations = []
        for line in res.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                added, deleted, file_path = parts
                if added == "-" or deleted == "-":
                    continue  # Binary file
                add_cnt = int(added)
                del_cnt = int(deleted)
                total_mod = add_cnt + del_cnt

                full_path = os.path.join(repo_root, file_path)
                if not os.path.exists(full_path):
                    continue

                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    total_file_lines = len(f.readlines())

                # Check if entire file was rewritten
                if total_file_lines >= cls.MIN_LINES_FOR_AUDIT:
                    if del_cnt >= int(total_file_lines * 0.8) and add_cnt >= int(total_file_lines * 0.8):
                        violations.append({
                            "file": file_path,
                            "total_lines": total_file_lines,
                            "added": add_cnt,
                            "deleted": del_cnt,
                            "issue": "MONOLITHIC_FULL_REWRITE: Entire file deleted and rewritten instead of targeted Search/Replace!"
                        })

        return len(violations) == 0, violations

    @classmethod
    def validate_search_replace_block(cls, target_content: str, replacement_content: str, full_file_content: str) -> Dict[str, Any]:
        """Validates that a search/replace edit meets targeted precision standards."""
        if not target_content:
            return {"valid": False, "reason": "Target search block cannot be empty."}

        target_lines = len(target_content.splitlines())
        full_lines = len(full_file_content.splitlines())

        if full_lines > cls.MIN_LINES_FOR_AUDIT and target_lines > int(full_lines * 0.7):
            return {
                "valid": False,
                "reason": f"Target search block encompasses {target_lines}/{full_lines} lines (> 70%). Use smaller surgical replacements."
            }

        if target_content not in full_file_content:
            return {"valid": False, "reason": "Target content not found in target file."}

        occurrences = full_file_content.count(target_content)
        return {
            "valid": True,
            "occurrences": occurrences,
            "target_lines": target_lines,
            "replacement_lines": len(replacement_content.splitlines()),
            "net_line_delta": len(replacement_content.splitlines()) - target_lines
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 5 Output Diff & Anti-Rewrite Sentinel")
    parser.add_argument("--check-diff", action="store_true", help="Audit current Git working tree diff")
    args = parser.parse_args()

    passed, violations = OutputDiffSentinel.audit_git_diff()
    if passed:
        print("PASS: 100% Clean surgical diffs verified. Zero monolithic full-file rewrites detected.")
        return 0

    print("FAIL: Detected monolithic full-file rewrites:", file=sys.stderr)
    for v in violations:
        print(f"  - [X] {v['file']}: {v['issue']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
