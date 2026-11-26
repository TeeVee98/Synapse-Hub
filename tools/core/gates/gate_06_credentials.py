#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 6: Credential Security Sentinel.
Scans for plaintext passwords, API tokens, and private keys across codebase.
"""

import os
import re
from typing import List, Tuple

from tools.core.gates.base import (
    BaseGate,
    get_scoped_git_files,
)


def gate_6_credential_security(repo_root: str, mode: str = "AUTO", fast: bool = False) -> bool:
    """Gate 6: Scans for plaintext passwords, API tokens, and private keys across codebase."""
    print("\n[GATE 6] Checking Credential Security across repository...")
    violations: List[Tuple[str, int, str]] = []

    # 1. Target project check: Profiles/default.glbl
    glbl_file = os.path.join(repo_root, "Profiles", "default.glbl")
    if os.path.exists(glbl_file):
        try:
            with open(glbl_file, "r", encoding="utf-8") as fp:
                content = fp.read()
            # Extract PASSWORD entity block
            m = re.search(r'<name>PASSWORD</name>.*?<protected>(.*?)</protected>', content, re.DOTALL)
            if not m:
                m = re.search(r'<protected>(.*?)</protected>.*?<name>PASSWORD</name>', content, re.DOTALL)
            if m:
                protected_val = m.group(1).strip().lower()
                if protected_val != "true":
                    violations.append((glbl_file, 1, f"PASSWORD in Profiles/default.glbl has protected={protected_val} (must be 'true')"))
            else:
                print("[WARN] PASSWORD entity not found in Profiles/default.glbl")

            # Check for plaintext password leaks in glbl
            if re.search(r'(?i)\b(?:Password@?\d+|Admin@?\d+|Root@?\d+|Default@?\d+)\b', content):  # gate6-allowlist
                violations.append((glbl_file, 1, "Plaintext default password found in default.glbl"))
        except Exception as e:
            print(f"[WARN] Error reading default.glbl: {e}")

    # 2. Universal Repository Scan for Hardcoded Plaintext Secrets
    token_patterns = [
        (re.compile(r'\bghp_[0-9a-zA-Z]{36}\b'), "GitHub Personal Access Token"),
        (re.compile(r'\bgithub_pat_[0-9a-zA-Z_]{82}\b'), "GitHub Fine-Grained Personal Access Token"),
        (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), "AWS Access Key ID"),
        (re.compile(r'\bsk_(?:live|test)_[0-9a-zA-Z]{24,}\b'), "Stripe Secret Key"),
        (re.compile(r'\bxox[baprs]-[0-9a-zA-Z-]{10,}\b'), "Slack API Token"),
        (re.compile(r'\bAIza[0-9A-Za-z-_]{35}\b'), "Google API Key"),
        (re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----'), "Private Key Header"),
        (re.compile(r'\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b'), "JSON Web Token (JWT)"),
        (re.compile(r'\b\d{8,12}:AA[A-Za-z0-9_-]{33}\b'), "Telegram Bot Token"),
    ]

    password_patterns = [
        (re.compile(r'(?i)\b(?:Password@?\d+|Admin@?\d+|Root@?\d+|Default@?\d+)\b'), "Known Default Password"),
        (re.compile(r'(?i)\b(?:password|passwd|pwd)\s*[:=]\s*[\x22\x27][^\x22\x27]{4,}[\x22\x27]'), "Hardcoded Plaintext Password Assignment"),
    ]

    password_allowlist_indicators = [
        "System.getenv", "os.getenv", "os.environ", "process.env",
        "dummy", "placeholder", "***", "<password>",
        "secret_patterns", "<name>PASSWORD</name>", 'password = ""', "password = ''",
        "type=str", "help="
    ]

    polyglot_fallback_patterns = [
        (re.compile(r'process\.env\.[A-Za-z0-9_]*(?:PASS|SECRET|PWD|AUTH_TOKEN|API_KEY|PRIVATE_KEY)[A-Za-z0-9_]*\s*(?:\|\||\?\?)\s*[\'"][^\'"]{4,}[\'"]', re.IGNORECASE), "JS/TS Fallback Credential behind Env Query"),
        (re.compile(r'(?:os\.getenv|os\.environ\.get)\s*\(\s*[\'"][A-Za-z0-9_]*(?:PASS|SECRET|PWD|AUTH_TOKEN|API_KEY|PRIVATE_KEY)[A-Za-z0-9_]*[\'"]\s*,\s*[\'"][^\'"]{4,}[\'"]\s*\)', re.IGNORECASE), "Python Fallback Credential behind Env Query"),
        (re.compile(r'(?:vars\.get|System\.getenv)\s*\(\s*[\'"][A-Za-z0-9_]*(?:PASS|SECRET|PWD|AUTH_TOKEN|API_KEY|PRIVATE_KEY)[A-Za-z0-9_]*[\'"]\s*\)\s*\?:\s*[\'"][^\'"]{4,}[\'"]', re.IGNORECASE), "JVM/Groovy Fallback Credential behind Env Query"),
    ]

    ignored_dirs = {
        ".git", ".gradle", "node_modules", "allure-results", "Screenshots",
        "Reports", "reports", "TestReports", "testreports", "Libs", ".settings", "graphify-out",
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "agent_qa.egg-info", "synapse_hub.egg-info",
        "dist", "build", "claude-ecosystem-repos", "external_repos", "reference_repos", "teamwork", ".synapse", ".sandbox_snapshots"
    }

    valid_exts = (".py", ".groovy", ".ts", ".js", ".json", ".txt", ".md", ".yml", ".yaml", ".properties", ".sh", ".ps1", ".glbl")

    exempt_files = {
        "tools/verify_all.py", "tools/core/verify_all.py",
        "tools/core/gates/gate_06_credentials.py", "tools/core/gates/base.py",
        "tests/test_tools.py", "tests/test_git_pre_commit_guard.py",
        "docs/AUDIT_REMEDIATION_PLAN.md", "AUDIT_REMEDIATION_PLAN.md",
    }

    files_to_check = None
    if fast:
        scoped = get_scoped_git_files(repo_root, staged_only=True)
        if scoped is not None:
            files_to_check = scoped
            if not files_to_check and not violations:
                print("[PASS] [FAST MODE] Zero staged/changed files detected. Gate 6 instant pass.")
                return True

    if files_to_check is not None:
        # Fast path: only iterate scoped git files (zero os.walk)
        for rel_path in files_to_check:
            parts = rel_path.split("/")
            if any(p in ignored_dirs or p.endswith(".egg-info") or p.startswith(("synapse_hub-", "synapse-hub-", ".temp-")) for p in parts[:-1]):
                continue
            filename = parts[-1]
            if not filename.endswith(valid_exts):
                continue
            norm_rel = rel_path.replace("\\", "/")
            if norm_rel in exempt_files or norm_rel.endswith(("/verify_all.py", "/gate_06_credentials.py", "/test_tools.py", "/test_git_pre_commit_guard.py", "/AUDIT_REMEDIATION_PLAN.md")):
                continue
            full_path = os.path.join(repo_root, *parts)
            if not os.path.isfile(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        if "# gate6-allowlist" in line or "# pragma: allowlist secret" in line:
                            continue
                        for pat, desc in token_patterns:
                            if pat.search(line):
                                violations.append((rel_path, line_no, desc))
                        for pat, desc in polyglot_fallback_patterns:
                            if pat.search(line):
                                violations.append((rel_path, line_no, desc))
                        if not any(ind in line for ind in password_allowlist_indicators):
                            for pat, desc in password_patterns:
                                if pat.search(line):
                                    violations.append((rel_path, line_no, desc))
            except (OSError, PermissionError):
                continue
    else:
        # Full scan via os.walk
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.endswith(".egg-info") and not d.startswith(("synapse_hub-", "synapse-hub-", ".temp-"))]
            for f in files:
                if not f.endswith(valid_exts):
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, repo_root)

                norm_rel = rel_path.replace("\\", "/")
                if norm_rel in exempt_files or norm_rel.endswith(("/verify_all.py", "/gate_06_credentials.py", "/test_tools.py", "/test_git_pre_commit_guard.py", "/AUDIT_REMEDIATION_PLAN.md")):
                    continue

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        for line_no, line in enumerate(fp, 1):
                            if "# gate6-allowlist" in line or "# pragma: allowlist secret" in line:
                                continue
                            for pat, desc in token_patterns:
                                if pat.search(line):
                                    violations.append((rel_path, line_no, desc))
                            for pat, desc in polyglot_fallback_patterns:
                                if pat.search(line):
                                    violations.append((rel_path, line_no, desc))
                            if not any(ind in line for ind in password_allowlist_indicators):
                                for pat, desc in password_patterns:
                                    if pat.search(line):
                                        violations.append((rel_path, line_no, desc))
                except (OSError, PermissionError):
                    continue

    if violations:
        print(f"[FAIL] {len(violations)} hardcoded secrets/credentials detected on disk:")
        for rel_path, line_no, desc in violations:
            print(f"   - {rel_path}:{line_no} contains '{desc}'")
        return False

    if fast and files_to_check is not None:
        print(f"[PASS] [FAST MODE] 100% Verified: Zero hardcoded credentials across {len(files_to_check)} scoped file(s).")
    else:
        print("[PASS] 100% Verified: Zero hardcoded plaintext credentials or secret tokens across repository.")
    return True


class Gate06Credentials(BaseGate):
    """Gate 6: Credential Security Sentinel."""

    gate_id = 6
    name = "Gate 6: Credential Security"
    key = "gate_6_credential_security"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        fast = kwargs.get("fast", False)
        return gate_6_credential_security(repo_root, mode=mode, fast=fast)
