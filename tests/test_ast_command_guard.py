# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for ASTCommandGuard (tests/test_ast_command_guard.py).

Verifies safety filtering of dangerous commands, benign command passing,
and edge cases.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

import pytest

from tools.runtime.ast_command_guard import ASTCommandGuard


@pytest.fixture
def guard():
    return ASTCommandGuard()


def test_safe_qa_commands_allowed(guard):
    safe_commands = [
        "pytest tests/test_login.py -v",
        "python tools/core/verify_all.py --mode hub --tier fast",
        "npx playwright test --project=chromium",
        "git status --porcelain",
        ["python", "tools/lint/infer_linter.py", "--check"],
    ]
    for cmd in safe_commands:
        result = guard.audit_command(cmd)
        assert result.is_safe is True
        assert len(result.violations) == 0
        assert result.suggested_action == "PROCEED"


def test_catastrophic_deletion_blocked(guard):
    blocked_commands = [
        "rm -rf /",
        "rm -rf /home/user",
        "del /f /s /q C:\\Windows",
        "format D: /fs:NTFS",
        "shutdown -h now",
        "reboot",
    ]
    for cmd in blocked_commands:
        result = guard.audit_command(cmd)
        assert result.is_safe is False
        assert len(result.violations) > 0
        assert result.suggested_action == "HALT_AND_ESCALATE"


def test_author_integrity_tampering_blocked(guard):
    tamper_commands = [
        "sed -i 's/TeeVee98/Other/g' tools/core/author_integrity.py",
        "rm tools/core/author_integrity.py",
    ]
    for cmd in tamper_commands:
        result = guard.audit_command(cmd)
        assert result.is_safe is False
        assert any("author integrity" in v.lower() for v in result.violations)


def test_boundary_empty_command(guard):
    result = guard.audit_command("")
    assert result.is_safe is True
    assert result.tokens == []
    assert result.suggested_action == "PROCEED"


def test_boundary_whitespace_only(guard):
    result = guard.audit_command("   \t  \n ")
    assert result.is_safe is True
    assert result.tokens == []
