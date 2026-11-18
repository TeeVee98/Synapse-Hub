#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

r"""
tools/pre_bash_guard.py — Active Pre-Tool Shell Guard (Inspired by Oven Bun pre-bash-guard)
------------------------------------------------------------------------------------------
Active Defensive Shell Interceptor that validates commands before execution.
Enforces:
  1. Scope Isolation (Lesson Learned #7 & #8): Blocks running target test commands
     or installing target dependencies directly in Synapse-Hub repository root.
  2. Destructive Command Prevention: Blocks dangerous recursive deletion commands
     (e.g., rm -rf /, Remove-Item -Recurse -Force C:\).
  3. Git Branch Safety: Blocks force pushing to protected branches (main, master, develop).
  4. Bun / Framework Best Practice: Blocks un-built direct execution commands (e.g. bun test without bun bd).

Usage:
  python tools/pre_bash_guard.py "git push -f origin main"
  python tools/pre_bash_guard.py "playwright test" --cwd "d:/Synapse Hub"
"""

import os
import sys
import re
import argparse
from typing import Tuple, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def validate_shell_command(command: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
    """
    Inspects and validates a shell command string before execution.
    Returns (True, "Command approved") or (False, "Violation reason").
    """
    if not command or not command.strip():
        return True, "Empty command"

    cmd_stripped = command.strip()
    norm_cwd = os.path.abspath(cwd or os.getcwd()).replace("\\", "/")
    norm_hub = REPO_ROOT.replace("\\", "/")
    is_cwd_hub = (norm_cwd == norm_hub)

    # 1. Destructive File System Commands
    destructive_patterns = [
        (re.compile(r'\brm\s+-[a-zA-Z]*(?:r[fF]|fr|[fF]r)[a-zA-Z]*\s+(?:/|~|\*|\$HOME)(?:\s|$)'), "Dangerous recursive deletion of root or home directory (rm -rf /)"),
        (re.compile(r'\bRemove-Item\b.*-(?:Recurse|r)\b.*-(?:Force|f)\b.*[a-zA-Z]:', re.IGNORECASE), "Dangerous recursive deletion of Windows drive root"),
        (re.compile(r'\brmdir\s+/(?:s|S)\s+/(?:q|Q)\s+[a-zA-Z]:', re.IGNORECASE), "Dangerous recursive disk deletion (rmdir /s /q)"),
    ]
    for pat, desc in destructive_patterns:
        if pat.search(cmd_stripped):
            return False, f"SECURITY_VIOLATION: {desc} is strictly prohibited."

    # 2. Force Push on Protected Branches
    force_push_pattern = re.compile(
        r'\bgit\s+push\s+.*(?:-f|--force(?:-with-lease)?)\s+.*(?:main|master|develop)\b',
        re.IGNORECASE
    )
    if force_push_pattern.search(cmd_stripped):
        return False, "SAFETY_VIOLATION: Force push to protected branch (main/master/develop) is strictly prohibited by Git Push Protocol."

    # 3. Lesson Learned #7 & #8: CLI ran on Hub instead of Target Workspace
    # Synapse-Hub is a read-only testing hub and holds 0 business tests.
    if is_cwd_hub:
        # Check if user attempts to run target test runners inside Hub root
        hub_forbidden_runners = [
            (re.compile(r'^\s*(?:npx\s+)?playwright\s+test\b', re.IGNORECASE), "playwright test"),
            (re.compile(r'^\s*(?:npx\s+)?cypress\s+(?:run|open)\b', re.IGNORECASE), "cypress run/open"),
            (re.compile(r'^\s*mvn\s+test\b', re.IGNORECASE), "mvn test"),
            (re.compile(r'^\s*gradle\s+test\b', re.IGNORECASE), "gradle test"),
        ]
        for pat, name in hub_forbidden_runners:
            if pat.search(cmd_stripped):
                return False, (
                    f"SCOPE_VIOLATION: Attempted to run '{name}' directly in Synapse-Hub root. "
                    "Synapse-Hub holds 0 business tests (Lesson Learned #7 & #8). "
                    "Identify target client project workspace and execute tests there."
                )

    # 4. Oven Bun Debug Build Guard
    bun_direct_test_pattern = re.compile(r'^\s*bun\s+test\b', re.IGNORECASE)
    if bun_direct_test_pattern.search(cmd_stripped) and os.path.exists(os.path.join(norm_cwd, "src", "bun.js")):
        return False, (
            "BUN_GUARD_VIOLATION: Never run 'bun test' directly in runtime development; "
            "it does not include local changes. Use 'bun bd test <file>' instead."
        )

    return True, "Command approved"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Active Pre-Tool Shell Guard (Inspired by Oven Bun pre-bash-guard)"
    )
    parser.add_argument("command", help="Shell command string to validate")
    parser.add_argument("--cwd", default=None, help="Working directory context for execution")
    parser.add_argument("--json", action="store_true", help="Output validation result in JSON format")
    args = parser.parse_args()

    ok, reason = validate_shell_command(args.command, cwd=args.cwd)
    if args.json:
        import json
        output = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if ok else "deny",
            "permissionDecisionReason": reason,
            "command": args.command,
            "cwd": args.cwd or os.getcwd(),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if ok:
            print(f"[PASS] Pre-Tool Shell Guard: {reason}")
        else:
            print(f"[DENY] Pre-Tool Shell Guard: {reason}", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
