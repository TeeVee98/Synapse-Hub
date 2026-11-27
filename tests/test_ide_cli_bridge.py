#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
4-Scenario Unit & CLI Tests for Phase 2 Milestone 2:
Headless IDE CLI Bridge (`tools/orchestration/ide_cli_bridge.py`).
Strictly mocks `subprocess.run` — zero external IDE CLI executions in pytest.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import os
import subprocess
import sys
import pytest

from tools.core.model_registry import ProviderFamily
from tools.orchestration.ide_cli_bridge import (
    CliBridgeFindingDTO,
    CliBridgeRequestDTO,
    CliBridgeResultDTO,
    discover_local_cli_adapters,
    invoke_readonly_cli_audit,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_cli_bridge_positive_discover_and_readonly_audit(monkeypatch, tmp_path):
    """TC-01 Positive: Discovers installed CLIs in preferred order and parses structured read-only JSON findings."""
    fake_bins = {
        "claude": "/usr/local/bin/claude",
        "codex": "/usr/local/bin/codex",
        "ollama": "/usr/local/bin/ollama",
    }
    monkeypatch.setattr("shutil.which", lambda name: fake_bins.get(name))

    discovered = discover_local_cli_adapters(preferred_order=(ProviderFamily.OPENAI, ProviderFamily.ANTHROPIC))
    assert list(discovered.keys())[:2] == [ProviderFamily.OPENAI, ProviderFamily.ANTHROPIC]
    assert discovered[ProviderFamily.OPENAI] == "/usr/local/bin/codex"
    assert discovered[ProviderFamily.ANTHROPIC] == "/usr/local/bin/claude"
    assert discovered[ProviderFamily.LOCAL_OPENAI] == "/usr/local/bin/ollama"

    captured_calls = []

    def _fake_subproc_run(argv, **kwargs):
        captured_calls.append((argv, kwargs))
        if argv[0].endswith("codex"):
            payload = {
                "summary": "Found 1 boundary risk",
                "findings": [
                    {
                        "severity": "Should fix",
                        "category": "concurrency",
                        "title": "Unbounded timeout value",
                        "file_path": "tools/demo.py",
                        "line_no": 42,
                        "rationale": "Clamp socket timeout <= 30s.",
                    }
                ],
            }
            return _FakeCompletedProcess(0, json.dumps(payload))
        return _FakeCompletedProcess(
            0,
            json.dumps({"result": json.dumps({"summary": "Claude read-only pass", "findings": []})}),
        )

    monkeypatch.setattr("subprocess.run", _fake_subproc_run)

    req_codex = CliBridgeRequestDTO(
        target_provider=ProviderFamily.OPENAI,
        prompt="Audit diff",
        diff_excerpt="+ timeout = 999",
        repo_root=str(tmp_path),
        timeout_sec=30.0,
        read_only=True,
    )
    with pytest.raises(FrozenInstanceError):
        req_codex.read_only = False  # type: ignore[misc]

    res_codex = invoke_readonly_cli_audit(req_codex, allow_live_subprocess=True)
    assert isinstance(res_codex, CliBridgeResultDTO)
    with pytest.raises(FrozenInstanceError):
        res_codex.success = False  # type: ignore[misc]
    assert res_codex.success is True
    assert res_codex.cli_binary == "/usr/local/bin/codex"
    assert res_codex.provider == ProviderFamily.OPENAI
    assert res_codex.model_id == "gpt-6.2-astra"
    assert res_codex.read_only_enforced is True
    assert res_codex.raw_summary == "Found 1 boundary risk"
    assert res_codex.error_code is None
    assert len(res_codex.findings) == 1
    finding0 = res_codex.findings[0]
    assert isinstance(finding0, CliBridgeFindingDTO)
    with pytest.raises(FrozenInstanceError):
        finding0.line_no = 99  # type: ignore[misc]
    assert finding0.severity == "Should fix"
    assert finding0.category == "concurrency"
    assert finding0.title == "Unbounded timeout value"
    assert finding0.file_path == "tools/demo.py"
    assert finding0.line_no == 42
    assert finding0.rationale == "Clamp socket timeout <= 30s."
    # Enforce list-argv, read-only sandbox, and zero shell=True
    argv_codex, kw_codex = captured_calls[0]
    assert "--sandbox" in argv_codex and "read-only" in argv_codex
    assert kw_codex.get("shell") is False

    # Verify Claude CLI read-only enforcement flags (--tools "" / plan mode) and nested JSON result extraction
    res_claude = invoke_readonly_cli_audit(
        CliBridgeRequestDTO(
            target_provider=ProviderFamily.ANTHROPIC,
            prompt="Audit diff",
            diff_excerpt="+ pass",
            repo_root=str(tmp_path),
        ),
        allow_live_subprocess=True,
    )
    assert res_claude.success is True
    assert res_claude.model_id == "claude-opus-5.5"
    assert res_claude.raw_summary == "Claude read-only pass"
    argv_claude, kw_claude = captured_calls[1]
    assert "--tools" in argv_claude
    assert kw_claude.get("shell") is False


def test_cli_bridge_negative_missing_binary_unsafe_write_and_timeout(monkeypatch, tmp_path):
    """TC-03 Negative: Rejects read_only=False, reports CLI_BINARY_NOT_FOUND, and catches TimeoutExpired cleanly."""
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/claude" if name == "claude" else None)

    unsafe_res = invoke_readonly_cli_audit(
        CliBridgeRequestDTO(
            target_provider=ProviderFamily.ANTHROPIC,
            prompt="Edit files",
            diff_excerpt="+ x = 1",
            repo_root=str(tmp_path),
            read_only=False,
        )
    )
    assert unsafe_res.success is False
    assert unsafe_res.read_only_enforced is False
    assert unsafe_res.error_code == "READONLY_POLICY_REQUIRED"

    missing_res = invoke_readonly_cli_audit(
        CliBridgeRequestDTO(
            target_provider=ProviderFamily.OPENAI,
            prompt="Audit diff",
            diff_excerpt="+ x = 1",
            repo_root=str(tmp_path),
        )
    )
    assert missing_res.success is False
    assert missing_res.error_code == "CLI_BINARY_NOT_FOUND"

    def _timeout_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout", 45.0))

    monkeypatch.setattr("subprocess.run", _timeout_run)
    timeout_res = invoke_readonly_cli_audit(
        CliBridgeRequestDTO(
            target_provider=ProviderFamily.ANTHROPIC,
            prompt="Audit diff",
            diff_excerpt="+ x = 1",
            repo_root=str(tmp_path),
            timeout_sec=120.0,
        )
    )
    assert timeout_res.success is False
    assert timeout_res.error_code == "CLI_TIMEOUT"


def test_cli_bridge_boundary_empty_diff_clamped_timeout_and_non_json_fallback(monkeypatch, tmp_path):
    """Boundary: Rejects empty prompt/diff, clamps timeout <= 60s, supports dry subprocess mode and raw text output."""
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/ollama" if name == "ollama" else None)

    empty_res = invoke_readonly_cli_audit(
        CliBridgeRequestDTO(
            target_provider=ProviderFamily.LOCAL_OPENAI,
            prompt="   ",
            diff_excerpt="",
            repo_root=str(tmp_path),
        )
    )
    assert empty_res.success is False
    assert empty_res.error_code == "EMPTY_AUDIT_INPUT"

    dry_res = invoke_readonly_cli_audit(
        CliBridgeRequestDTO(
            target_provider=ProviderFamily.LOCAL_OPENAI,
            prompt="Audit diff",
            diff_excerpt="+ ok",
            repo_root=str(tmp_path),
        ),
        allow_live_subprocess=False,
    )
    assert dry_res.success is True
    assert dry_res.read_only_enforced is True
    assert dry_res.error_code is None

    observed_timeouts = []

    def _plain_text_run(argv, **kwargs):
        observed_timeouts.append((argv[:3], kwargs.get("timeout")))
        return _FakeCompletedProcess(0, "Plain text audit: no issues found.")

    monkeypatch.setattr("subprocess.run", _plain_text_run)
    plain_res = invoke_readonly_cli_audit(
        CliBridgeRequestDTO(
            target_provider=ProviderFamily.LOCAL_OPENAI,
            prompt="Audit diff",
            diff_excerpt="+ ok",
            repo_root=str(tmp_path),
            timeout_sec=240.0,
        ),
        allow_live_subprocess=True,
    )
    assert plain_res.success is True
    assert plain_res.findings == ()
    assert "Plain text audit" in plain_res.raw_summary
    assert observed_timeouts[0][0][1:] == ["run", "qwen3-coder"]
    assert observed_timeouts[0][1] == 60.0


def test_cli_bridge_cli_discover_json():
    """TC-05 CLI: ide_cli_bridge.py --discover --json exits 0 with valid JSON."""
    script = os.path.join(REPO_ROOT, "tools", "orchestration", "ide_cli_bridge.py")
    proc = subprocess.run(
        [sys.executable, script, "--discover", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert isinstance(data.get("available_clis"), dict)
