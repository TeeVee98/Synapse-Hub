#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/ide_cli_bridge.py — Read-Only Headless IDE CLI Bridge
-------------------------------------------------------------------------
Discovers locally installed secondary IDE/agent CLIs (`claude`, `codex`,
`ollama`, `gemini`) and executes bounded, strictly read-only single-thread
semantic diff audits via `subprocess.run(..., shell=False)` with zero API keys
when IDE subscriptions are already authenticated locally.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Mapping, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.core.model_registry import ProviderFamily

MAX_CLI_TIMEOUT_SEC = 60.0

_CLI_SPECS: Dict[ProviderFamily, Tuple[str, str]] = {
    ProviderFamily.ANTHROPIC: ("claude", "claude-opus-5.5"),
    ProviderFamily.OPENAI: ("codex", "gpt-6.2-astra"),
    ProviderFamily.LOCAL_OPENAI: ("ollama", "ollama-qwen3-coder"),
    ProviderFamily.GEMINI: ("gemini", "gemini-4-carbon"),
}


@dataclass(frozen=True)
class CliBridgeRequestDTO:
    target_provider: ProviderFamily
    prompt: str
    diff_excerpt: str
    repo_root: str
    timeout_sec: float = 45.0
    read_only: bool = True


@dataclass(frozen=True)
class CliBridgeFindingDTO:
    severity: str
    category: str
    title: str
    file_path: str
    line_no: int
    rationale: str


@dataclass(frozen=True)
class CliBridgeResultDTO:
    success: bool
    cli_binary: str
    provider: ProviderFamily
    model_id: str
    read_only_enforced: bool
    findings: Tuple[CliBridgeFindingDTO, ...]
    raw_summary: str
    error_code: Optional[str] = None


def discover_local_cli_adapters(
    preferred_order: Tuple[ProviderFamily, ...] = (),
) -> Dict[ProviderFamily, str]:
    """Discovers installed secondary IDE/agent CLIs (claude, codex, ollama, gemini) on PATH without opening network sockets."""
    found: Dict[ProviderFamily, str] = {}
    for family, (bin_name, _model) in _CLI_SPECS.items():
        resolved = shutil.which(bin_name)
        if resolved:
            found[family] = resolved

    ordered: Dict[ProviderFamily, str] = {}
    for fam in preferred_order:
        if fam in found:
            ordered[fam] = found[fam]
    for fam, path in found.items():
        if fam not in ordered:
            ordered[fam] = path
    return ordered


def _build_readonly_argv(cli_path: str, provider: ProviderFamily, audit_prompt: str) -> List[str]:
    if provider == ProviderFamily.ANTHROPIC:
        return [
            cli_path,
            "-p",
            audit_prompt,
            "--output-format",
            "json",
            "--tools",
            "",
            "--permission-mode",
            "plan",
        ]
    if provider == ProviderFamily.OPENAI:
        return [cli_path, "exec", "--sandbox", "read-only", "--json", audit_prompt]
    if provider == ProviderFamily.LOCAL_OPENAI:
        return [cli_path, "run", "qwen3-coder", audit_prompt]
    return [cli_path, "-p", audit_prompt]


def _extract_json_dict(raw_text: str) -> Optional[Dict[str, Any]]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("```")).strip()
    try:
        parsed = json.loads(text)
    except ValueError:
        return None
    if isinstance(parsed, dict) and isinstance(parsed.get("result"), str):
        return _extract_json_dict(parsed["result"])
    return parsed if isinstance(parsed, dict) else None


def _parse_cli_findings(stdout_text: str) -> Tuple[Tuple[CliBridgeFindingDTO, ...], str]:
    payload = _extract_json_dict(stdout_text)
    if payload is None:
        return (), stdout_text.strip()[:500]
    summary = str(payload.get("summary", "")).strip()
    findings: List[CliBridgeFindingDTO] = []
    for item in payload.get("findings", ()):
        if isinstance(item, Mapping):
            findings.append(
                CliBridgeFindingDTO(
                    severity=str(item.get("severity", "Should fix")),
                    category=str(item.get("category", "general")),
                    title=str(item.get("title", "Cross-LLM audit finding")),
                    file_path=str(item.get("file_path", ".")),
                    line_no=int(item.get("line_no", 1)),
                    rationale=str(item.get("rationale", "")),
                )
            )
    return tuple(findings), summary


def invoke_readonly_cli_audit(
    request: CliBridgeRequestDTO,
    allow_live_subprocess: bool = True,
) -> CliBridgeResultDTO:
    """Executes bounded single-thread synchronous read-only CLI audit (no tool edits, zero shell=True, timeout <= 60s)."""
    model_id = _CLI_SPECS.get(request.target_provider, ("", "unknown"))[1]
    if not request.read_only:
        return CliBridgeResultDTO(
            success=False,
            cli_binary="",
            provider=request.target_provider,
            model_id=model_id,
            read_only_enforced=False,
            findings=(),
            raw_summary="Blocked write-capable CLI bridge request.",
            error_code="READONLY_POLICY_REQUIRED",
        )

    if not request.prompt.strip() and not request.diff_excerpt.strip():
        return CliBridgeResultDTO(
            success=False,
            cli_binary="",
            provider=request.target_provider,
            model_id=model_id,
            read_only_enforced=True,
            findings=(),
            raw_summary="Empty audit prompt and diff excerpt.",
            error_code="EMPTY_AUDIT_INPUT",
        )

    cli_path = discover_local_cli_adapters().get(request.target_provider)
    if not cli_path:
        return CliBridgeResultDTO(
            success=False,
            cli_binary="",
            provider=request.target_provider,
            model_id=model_id,
            read_only_enforced=True,
            findings=(),
            raw_summary=f"No local CLI installed for {request.target_provider.value}.",
            error_code="CLI_BINARY_NOT_FOUND",
        )

    audit_prompt = (
        f"{request.prompt.strip()}\n\n"
        "Respond ONLY with JSON object {summary: str, findings: [{severity, category, title, file_path, line_no, rationale}]}.\n"
        f"<UNTRUSTED_DIFF_READONLY>\n{request.diff_excerpt}\n</UNTRUSTED_DIFF_READONLY>"
    )
    argv = _build_readonly_argv(cli_path, request.target_provider, audit_prompt)
    if not allow_live_subprocess:
        return CliBridgeResultDTO(
            success=True,
            cli_binary=cli_path,
            provider=request.target_provider,
            model_id=model_id,
            read_only_enforced=True,
            findings=(),
            raw_summary="DRY_RUN: " + " ".join(argv[:3]),
            error_code=None,
        )

    clamped_timeout = min(MAX_CLI_TIMEOUT_SEC, float(request.timeout_sec))
    try:
        proc = subprocess.run(
            argv,
            cwd=request.repo_root,
            capture_output=True,
            text=True,
            timeout=clamped_timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CliBridgeResultDTO(
            success=False,
            cli_binary=cli_path,
            provider=request.target_provider,
            model_id=model_id,
            read_only_enforced=True,
            findings=(),
            raw_summary=f"Timed out after {clamped_timeout}s",
            error_code="CLI_TIMEOUT",
        )

    if proc.returncode != 0:
        return CliBridgeResultDTO(
            success=False,
            cli_binary=cli_path,
            provider=request.target_provider,
            model_id=model_id,
            read_only_enforced=True,
            findings=(),
            raw_summary=proc.stderr.strip()[:400],
            error_code="CLI_NONZERO_EXIT",
        )

    findings, summary = _parse_cli_findings(proc.stdout)
    return CliBridgeResultDTO(
        success=True,
        cli_binary=cli_path,
        provider=request.target_provider,
        model_id=model_id,
        read_only_enforced=True,
        findings=findings,
        raw_summary=summary,
        error_code=None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub Read-Only Headless IDE CLI Bridge")
    _d1 = parser.add_argument("--discover", action="store_true", help="Discover installed local IDE/agent CLIs")
    _d2 = parser.add_argument("--json", action="store_true", help="Output structured JSON")
    args = parser.parse_args()

    available = {fam.value: path for fam, path in discover_local_cli_adapters().items()}
    if args.discover or args.json:
        print(json.dumps({"available_clis": available}, indent=2))
        return 0
    print(f"Available read-only CLI adapters: {available}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
