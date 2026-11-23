# -*- coding: utf-8 -*-
"""AST Command Guard Engine (tools/runtime/ast_command_guard.py).

Inspired by AgentScope 2.0's bash parser:
Analyzes command tokens and syntax structures before subprocess execution.
Detects destructive filesystem mutations, fork bombs, unauthorized system shutdowns,
and tampering with repository integrity guardrails.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

from __future__ import annotations

import re
import shlex
import sys
from dataclasses import dataclass, field
from typing import List

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass(frozen=True)
class CommandAuditResult:
    """Audit verdict produced by ASTCommandGuard."""

    is_safe: bool
    violations: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    suggested_action: str = "PROCEED"


class ASTCommandGuard:
    """Pre-execution analyzer that screens shell and terminal commands."""

    # High-risk patterns that indicate catastrophic system/repo mutation
    DANGEROUS_PATTERNS = [
        # Root / System destruction
        (re.compile(r"\brm\s+-(?:r[fv]|f[rv]|rf)\s+(?:/|[a-zA-Z]:[\\/]|~|\$HOME)", re.IGNORECASE), "Catastrophic directory deletion on root/home"),
        (re.compile(r"\b(?:del|rmdir)\s+/(?:s|q|f)\b.*(?:[a-zA-Z]:\\|\\windows)", re.IGNORECASE), "Catastrophic Windows system path deletion"),
        (re.compile(r"\b(?:format|mkfs)\b", re.IGNORECASE), "Disk formatting utility detected"),
        (re.compile(r"\bdd\s+if=.*of=(?:/dev/|[a-zA-Z]:)", re.IGNORECASE), "Raw block device write detected"),
        # Fork bombs & denial of service
        (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE), "Fork bomb signature detected"),
        # Unauthorized reboot / shutdown
        (re.compile(r"\b(?:shutdown|reboot|poweroff|init\s+0)\b", re.IGNORECASE), "System reboot / shutdown attempt"),
        # Tampering with MIT attribution & author integrity
        (re.compile(r"\b(?:sed|awk|perl)\b.*author_integrity\.py", re.IGNORECASE), "Illegal tampering with author integrity verification"),
        (re.compile(r"\brm\s+.*author_integrity\.py", re.IGNORECASE), "Deletion of author integrity sentinel"),
    ]

    def tokenize(self, command_str_or_args: str | List[str]) -> List[str]:
        """Safely tokenizes input string or normalizes existing token list."""
        if isinstance(command_str_or_args, list):
            return [str(a) for a in command_str_or_args]
        raw_cmd = str(command_str_or_args).strip()
        if not raw_cmd:
            return []
        try:
            # Use posix=False on Windows to preserve Windows backslashes properly
            is_windows = sys.platform.startswith("win")
            return shlex.split(raw_cmd, posix=not is_windows)
        except Exception:
            return raw_cmd.split()

    def audit_command(self, command_input: str | List[str]) -> CommandAuditResult:
        """Audits the command against destructive and unsafe patterns."""
        tokens = self.tokenize(command_input)
        if not tokens:
            return CommandAuditResult(
                is_safe=True,
                violations=[],
                tokens=[],
                suggested_action="PROCEED",
            )

        full_cmd_str = " ".join(tokens)
        violations: List[str] = []

        for pattern, description in self.DANGEROUS_PATTERNS:
            if pattern.search(full_cmd_str):
                violations.append(description)

        if violations:
            return CommandAuditResult(
                is_safe=False,
                violations=violations,
                tokens=tokens,
                suggested_action="HALT_AND_ESCALATE",
            )

        return CommandAuditResult(
            is_safe=True,
            violations=[],
            tokens=tokens,
            suggested_action="PROCEED",
        )
