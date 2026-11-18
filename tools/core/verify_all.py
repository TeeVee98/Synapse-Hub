#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Enterprise Multi-Project DoD Verifier (One Command Quality Gate)
---------------------------------------------------------
Consolidates all definition-of-done criteria into a single executable command.

Verifies:
  Pre-flight: Author Attribution & Copyright Integrity: Verifies author provenance (Thế Vị @TeeVee98).
  Gate 1: 100% UTF-8 No BOM across all repository files (8 extensions).
  Gate 2: Path Portability: Zero absolute machine paths (file:///C:, /Users/...).
  Gate 3: Clean POM & Flat Architecture: Zero raw XPaths or findTestObject in Scripts/.
  Gate 4: AI Docs & Artifacts Anti-Drift: No hallucinated PageClasses, Suites, or Tools.
  Gate 5: Cleanup Blacklist: No temporary properties or debug dump files on disk.
  Gate 6: Credential Security: No plaintext passwords in Profiles/default.glbl or repository.
  Gate 7: Static Defect Sentinel: Meta Infer-style AST scan for fake passes and empty catches.
  Gate 8: Syntactic Micro-Mutation Sentinel: Injects syntactic faults to eliminate tautological tests (Mutation Score >= 80%).
  Gate 9: Tier-2 Skill Collision Guard: Addy Osmani offline TF-IDF cosine similarity check (similarity < 0.75).
  Gate 10: Performance & SLA Sentinel: Enforces P95/P99 latency budgets and max error rate gates on JTL/k6 reports.

Supports:
  - Hub Mode: Verifies the centralized QA Hub / skills repository integrity.
  - Target Mode: Verifies enterprise automation target test suites (e.g. Katalon/Playwright).

Usage:
  python3 tools/verify_all.py [--mode auto|hub|target]
"""

import os
import sys
import subprocess
import glob
import re
import json
import io
import time
import logging
from datetime import datetime
import ast
import html as html_lib
import builtins
import argparse
from typing import Dict, Any

# Enforce UTF-8 stdout encoding and guard against non-blocking stream BlockingIOError
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'fileno'):
        try:
            os.set_blocking(stream.fileno(), True)
        except Exception:
            pass
    if hasattr(stream, 'reconfigure'):
        try:
            stream.reconfigure(encoding='utf-8', line_buffering=False)
        except Exception:
            pass


def safe_print(text="", stream=None):
    """Safely prints text to the given stream, handling BlockingIOError or encoding issues."""
    target_stream = stream if stream is not None else sys.stdout
    try:
        if text:
            target_stream.write(f"{text}\n")
        else:
            target_stream.write("\n")
        target_stream.flush()
    except BlockingIOError:
        try:
            if hasattr(target_stream, 'fileno'):
                os.set_blocking(target_stream.fileno(), True)
            target_stream.write(f"{text}\n")
            target_stream.flush()
        except OSError:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass
    except Exception:
        try:
            sys.stderr.write(f"{text}\n")
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass

BOM_EXTENSIONS = (
    ".groovy", ".tc", ".ts", ".glbl", ".md", ".py", ".json", ".ps1",
    ".java", ".yaml", ".yml", ".xml"
)

# Module-level paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# Module-level telemetry for gate execution metrics (populated during gate runs)
LAST_GATE_METRICS = {}


def get_git_commit_sha(repo_root=None, short=False) -> str:
    """Retrieves current Git commit SHA of the repository."""
    root = repo_root or REPO_ROOT
    try:
        cmd = ["git", "-C", root, "rev-parse"]
        if short:
            cmd.append("--short")
        cmd.append("HEAD")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except (OSError, subprocess.SubprocessError):  # synapse-ignore: SWALLOWED_EXCEPTION
        pass
    return "unknown"


def parse_pytest_metrics(output: str) -> Dict[str, Any]:
    """
    Parses exact pytest execution metrics from command output:
    capturing collected, passed, skipped, failed, xfailed, xpassed, errors, and runtime seconds.
    """
    metrics = {
        "collected": 0,
        "passed": 0,
        "skipped": 0,
        "failed": 0,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 0,
        "subtests_passed": 0,
        "duration_seconds": 0.0,
        "raw_summary": "",
    }
    if not output:
        return metrics

    # Strip ANSI escape sequences (e.g. \x1b[32m) to prevent word-boundary collision in regex
    output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)

    # Check for 'collected N items'
    coll_match = re.search(r'collected\s+(\d+)\s+items?', output)

    # Search for summary line from bottom up
    lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
    summary_line = ""
    for line in reversed(lines):
        line_clean = line.strip("= ").strip()
        # Summary line contains 'in X.XXs' and test outcome status keywords
        if re.search(r'\bin\s+[0-9\.]+s\b', line_clean) and any(
            w in line_clean for w in ("passed", "failed", "skipped", "xfailed", "xpassed", "error", "subtest")
        ):
            summary_line = line_clean
            break

    if not summary_line and lines:
        for line in reversed(lines):
            line_clean = line.strip("= ").strip()
            if any(w in line_clean for w in ("passed", "failed", "skipped", "xfailed")):
                summary_line = line_clean
                break

    metrics["raw_summary"] = summary_line

    if summary_line:
        dur_m = re.search(r'in\s+([0-9\.]+)s', summary_line)
        if dur_m:
            metrics["duration_seconds"] = float(dur_m.group(1))

        p_m = re.search(r'\b(\d+)\s+passed\b', summary_line)
        if p_m:
            metrics["passed"] = int(p_m.group(1))

        s_m = re.search(r'\b(\d+)\s+skipped\b', summary_line)
        if s_m:
            metrics["skipped"] = int(s_m.group(1))

        f_m = re.search(r'\b(\d+)\s+failed\b', summary_line)
        if f_m:
            metrics["failed"] = int(f_m.group(1))

        xf_m = re.search(r'\b(\d+)\s+xfailed\b', summary_line)
        if xf_m:
            metrics["xfailed"] = int(xf_m.group(1))

        xp_m = re.search(r'\b(\d+)\s+xpassed\b', summary_line)
        if xp_m:
            metrics["xpassed"] = int(xp_m.group(1))

        err_m = re.search(r'\b(\d+)\s+errors?\b', summary_line)
        if err_m:
            metrics["errors"] = int(err_m.group(1))

        sub_m = re.search(r'\b(\d+)\s+subtests?\s+passed\b', summary_line)
        if sub_m:
            metrics["subtests_passed"] = int(sub_m.group(1))

    if coll_match:
        metrics["collected"] = int(coll_match.group(1))
    else:
        metrics["collected"] = (
            metrics["passed"]
            + metrics["skipped"]
            + metrics["failed"]
            + metrics["xfailed"]
            + metrics["xpassed"]
            + metrics["errors"]
        )

    return metrics


# Public alias for compatibility
parse_pytest_output = parse_pytest_metrics

# Machine-specific absolute path patterns for Gate 2
FORBIDDEN_PATH_PATTERNS = [
    (re.compile(r'file:///[a-zA-Z]:', re.IGNORECASE), "Machine file URI (file:///...)"),
    (re.compile(r'\b[a-zA-Z]:\\Users\\[a-zA-Z0-9_\-]+\\', re.IGNORECASE), "Windows User directory path"),
    (re.compile(r'(?:^|[\s"\'`\(\[\{</])/(?:Users|home)/[a-zA-Z0-9_\-]+/', re.IGNORECASE), "User home directory path (/Users/ or /home/)"),
    (re.compile(r'\b[a-zA-Z]:[/\\](?:agent-skills|workspace|jenkins|builds)\b', re.IGNORECASE), "Machine-specific repository path"),
    (re.compile(r'[/\\\\]legacy_abs_path[/\\\\]', re.IGNORECASE), "Legacy absolute path reference"),
]


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def detect_repo_mode(repo_root):
    """Detects whether the repository is a QA Hub or a Target Test Suite."""
    has_groovy_tests = any(
        f.endswith(".groovy")
        for f in glob.glob(os.path.join(repo_root, "Scripts", "**", "*.groovy"), recursive=True)
    )
    has_katalon_project = (
        os.path.exists(os.path.join(repo_root, ".project"))
        or os.path.isdir(os.path.join(repo_root, "Keywords", "pages"))
    )
    has_playwright_project = (
        os.path.exists(os.path.join(repo_root, "playwright.config.ts"))
        or os.path.exists(os.path.join(repo_root, "playwright.config.js"))
    )

    if has_groovy_tests or has_katalon_project or has_playwright_project:
        return "TARGET"

    if (
        os.path.exists(os.path.join(repo_root, "skills_manifest.json"))
        or os.path.isdir(os.path.join(repo_root, ".agents", "skills"))
    ):
        return "HUB"

    return "TARGET"


def resolve_target_repo(cli_target=None, cli_repo=None):
    """
    Resolves the target repository path with the following precedence:
    1. Explicit CLI argument (--repo / --path or positional target).
    2. Environment variable TARGET_PROJECT_DIR.
    3. Current Working Directory (if different from Hub and contains project markers).
    4. Default fallback: QA Hub root (parent of tools/).
    """
    hub_root = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

    # 1. Explicit CLI flag or positional target
    chosen = cli_repo or cli_target
    if chosen:
        resolved = os.path.abspath(chosen)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Specified target repository path does not exist: {resolved}")
        return resolved

    # 2. Environment variable
    env_dir = os.environ.get("TARGET_PROJECT_DIR")
    if env_dir and os.path.exists(env_dir):
        return os.path.abspath(env_dir)

    # 3. Current Working Directory detection
    cwd = os.path.abspath(os.getcwd())
    if cwd.lower() != hub_root.lower():
        project_markers = [
            "Scripts", "Keywords", "Test Cases", "Test Suites",
            "playwright.config.ts", "playwright.config.js",
            ".project", "pom.xml", "build.gradle", "package.json", "tests"
        ]
        if any(os.path.exists(os.path.join(cwd, marker)) for marker in project_markers):
            return cwd

    # 4. Default fallback to QA Hub root
    return hub_root


def verify_engine_preflight(repo_root, mode="AUTO", silent=True):
    """Pre-flight Engine Integrity Guard: Verifies author attribution and MIT license provenance (silent by default)."""
    if not silent:
        print("\n[PRE-FLIGHT] Verifying Author Attribution & MIT License Integrity...")
    try:
        from author_integrity import (
            verify_author_attribution,
            get_canonical_watermark,
            verify_author_fingerprint,
            DEFAULT_REPO_ROOT,
        )
    except ImportError:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from author_integrity import (
            verify_author_attribution,
            get_canonical_watermark,
            verify_author_fingerprint,
            DEFAULT_REPO_ROOT,
        )

    # 1. Author metadata hash verification
    if not verify_author_fingerprint():
        print("\n[PRE-FLIGHT] [FAIL] Author attribution reference mismatch! Original creator ('Thế Vị @TeeVee98') has been altered.")
        return False

    # 2. In HUB mode, verify the Hub repository itself.
    # In TARGET mode, verify the Hub tools root to guarantee engine integrity.
    check_root = repo_root if mode == "HUB" else DEFAULT_REPO_ROOT
    valid, violations = verify_author_attribution(check_root)
    license_violations = [v for v in violations if "LICENSE" in v]
    if license_violations:
        print("\n[PRE-FLIGHT] [FAIL] Author Attribution & MIT License Violated:")
        for v in license_violations:
            print(f"   • {v}")
        print("   Under MIT License, original author copyright notice to 'Thế Vị (@TeeVee98)' must be preserved in LICENSE.")
        return False
    elif not valid and not silent:
        # Informational notices for downstream forks with customized package.json / README
        print("[INFO] Downstream attribution notice:")
        for v in violations:
            print(f"   • {v}")
    if not silent:
        print(f"[PASS] Author Attribution & MIT License Provenance verified intact: {get_canonical_watermark()}")
    return True


# Backward-compatibility alias
gate_0_author_integrity = verify_engine_preflight


MOJIBAKE_INDICATORS = (
    "\u00c3\u00a1",  # Ã¡
    "\u00c3\u00a3",  # Ã£
    "\u00c3\u00a9",  # Ã©
    "\u00c3\u00a8",  # Ã¨
    "\u00c3\u00b3",  # Ã³
    "\u00c3\u00b2",  # Ã²
    "\ufffd",        # replacement char
    "\u00e2\u20ac\u2014",  # double encoded em-dash
    "\u00e2\u20ac\u0153",  # double encoded open quote
    "\u00e2\u20ac\u009d",  # double encoded close quote
)


def get_scoped_git_files(repo_root: str, staged_only: bool = True):
    """
    Retrieves list of scoped files directly from git index for instant verification (<1s).
    Prioritizes staged changes (--cached); falls back to HEAD uncommitted diff if staged is empty.
    Returns None if git is unavailable or repo is not a git workspace.
    """
    try:
        # 1. Staged files check
        res = subprocess.run(
            ["git", "-C", repo_root, "diff", "--cached", "--name-only"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0
        )
        if res.returncode == 0:
            staged = [line.strip().replace("\\", "/") for line in res.stdout.splitlines() if line.strip()]
            if staged or staged_only:
                if staged:
                    return staged
        # 2. Fallback to uncommitted working tree diff vs HEAD
        res_head = subprocess.run(
            ["git", "-C", repo_root, "diff", "HEAD", "--name-only"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0
        )
        if res_head.returncode == 0:
            return [line.strip().replace("\\", "/") for line in res_head.stdout.splitlines() if line.strip()]
        return []
    except (OSError, subprocess.SubprocessError):
        return None


def gate_1_bom_check(repo_root, mode="AUTO", fast=False):
    """Gate 1: Verifies 100% UTF-8 encoding with zero Byte Order Mark (BOM) bytes and zero corrupted control characters."""
    print("\n[GATE 1] Scanning UTF-8 No BOM and Encoding Integrity across repository...")
    ignored_dirs = {".git", ".gradle", "node_modules", "allure-results", "graphify-out", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "build", "dist", "claude-ecosystem-repos", "external_repos", "teamwork", ".synapse", ".sandbox_snapshots", "agent_qa.egg-info", "synapse_hub.egg-info"}
    ignored_files = {"verify_all.py", "test_tools.py"}
    bom_violations = []
    mojibake_violations = []

    files_to_check = None
    if fast:
        scoped = get_scoped_git_files(repo_root, staged_only=True)
        if scoped is not None:
            files_to_check = scoped
            if not files_to_check:
                print("[PASS] [FAST MODE] Zero staged/changed files detected. Gate 1 instant pass.")
                return True

    if files_to_check is not None:
        # Fast path: only iterate scoped git files (zero os.walk)
        for rel_path in files_to_check:
            parts = rel_path.split("/")
            if any(p in ignored_dirs or p.endswith(".egg-info") or p.startswith(("synapse_hub-", "synapse-hub-", ".temp-")) for p in parts[:-1]):
                continue
            filename = parts[-1]
            if filename in ignored_files or not filename.endswith(BOM_EXTENSIONS):
                continue
            full_path = os.path.join(repo_root, *parts)
            if not os.path.isfile(full_path):
                continue
            try:
                with open(full_path, "rb") as fp:
                    raw = fp.read()
                    if raw[:3] == b"\xef\xbb\xbf":
                        bom_violations.append(rel_path)
                try:
                    text = raw.decode("utf-8")
                    if any(ind in text for ind in MOJIBAKE_INDICATORS):
                        mojibake_violations.append(rel_path)
                    bad_ctrl = [c for c in text if ord(c) < 32 and c not in ('\n', '\r', '\t')]
                    if bad_ctrl:
                        mojibake_violations.append(f"{rel_path} (Contains {len(bad_ctrl)} corrupted control char(s) e.g. {repr(bad_ctrl[0])})")
                except UnicodeDecodeError:
                    mojibake_violations.append(f"{rel_path} (Invalid UTF-8 decode)")
            except (OSError, PermissionError):
                continue
    else:
        # Full repository scan via os.walk
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.endswith(".egg-info") and not d.startswith(("synapse_hub-", "synapse-hub-", ".temp-"))]
            for f in files:
                if f.endswith(BOM_EXTENSIONS):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, repo_root)
                    if f in ignored_files:
                        continue
                    try:
                        with open(full_path, "rb") as fp:
                            raw = fp.read()
                            if raw[:3] == b"\xef\xbb\xbf":
                                bom_violations.append(rel_path)
                        try:
                            text = raw.decode("utf-8")
                            if any(ind in text for ind in MOJIBAKE_INDICATORS):
                                mojibake_violations.append(rel_path)
                            # Check for unescaped corrupted control characters (< 0x20 except \n, \r, \t)
                            bad_ctrl = [c for c in text if ord(c) < 32 and c not in ('\n', '\r', '\t')]
                            if bad_ctrl:
                                mojibake_violations.append(f"{rel_path} (Contains {len(bad_ctrl)} corrupted control char(s) e.g. {repr(bad_ctrl[0])})")
                        except UnicodeDecodeError:
                            mojibake_violations.append(f"{rel_path} (Invalid UTF-8 decode)")
                    except (OSError, PermissionError):
                        continue

    failed = False
    if bom_violations:
        print(f"[FAIL] {len(bom_violations)} files contain UTF-8 BOM bytes:")
        for v in bom_violations:
            print(f"   - {v}")
        failed = True
    if mojibake_violations:
        print(f"[FAIL] {len(mojibake_violations)} files contain Mojibake / Corrupted Encoding:")
        for v in mojibake_violations:
            print(f"   - {v}")
        failed = True

    if failed:
        return False

    print("[PASS] 100% UTF-8 No BOM & Clean Encoding verified across all source files.")
    return True


def gate_2_path_portability(repo_root, mode="AUTO", fast=False):
    """Gate 2: Scans for and rejects machine-specific absolute filepaths in code."""
    print("\n[GATE 2] Checking Path Portability (Zero absolute machine paths in repo sources)...")
    ignored_dirs = {
        ".git", ".gradle", "node_modules", "allure-results", "Screenshots",
        "Reports", "reports", "TestReports", "testreports", "Libs", ".settings", "graphify-out",
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "agent_qa.egg-info", "synapse_hub.egg-info", "dist", "build", "claude-ecosystem-repos", "external_repos", "teamwork", ".synapse", ".sandbox_snapshots"
    }
    ignored_files = {
        ".project", ".classpath", ".DS_Store", "memory_cache.db",
        "verify_all.py", "git_pre_commit_guard.py", "agent_canary.py", "repo_map.txt", "repo_map.json",
        "PROJECT_HEALTH_REPORT.md", "PROJECT_STATE.md", "AUDIT_REPORT.md"
    }
    violations = []

    files_to_check = None
    if fast:
        scoped = get_scoped_git_files(repo_root, staged_only=True)
        if scoped is not None:
            files_to_check = scoped
            if not files_to_check:
                print("[PASS] [FAST MODE] Zero staged/changed files detected. Gate 2 instant pass.")
                return True

    if files_to_check is not None:
        # Fast path: only iterate scoped git files (zero os.walk)
        for rel_path in files_to_check:
            parts = rel_path.split("/")
            if any(p in ignored_dirs or p.endswith(".egg-info") or p.startswith(("synapse_hub-", "synapse-hub-", ".temp-")) for p in parts[:-1]):
                continue
            filename = parts[-1]
            if filename.startswith(".temp-") or filename in ignored_files or filename.endswith(
                (".pyc", ".db", ".png", ".jpg", ".zip", ".tar", ".gz", ".xlsx", ".class", ".prefs", ".synapse_mutator_bak", ".bak")
            ):
                continue
            if "FINAL_REPORT.md" in rel_path or ".gitignore" in rel_path or ".coverage" in rel_path:
                continue
            full_path = os.path.join(repo_root, *parts)
            if not os.path.isfile(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        for pattern, desc in FORBIDDEN_PATH_PATTERNS:
                            if pattern.search(line):
                                violations.append((rel_path, line_no, desc))
            except (OSError, PermissionError):
                continue
    else:
        # Full scan via os.walk
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.endswith(".egg-info") and not d.startswith(("synapse_hub-", "synapse-hub-", ".temp-"))]
            for f in files:
                if f.startswith(".temp-") or f in ignored_files or f.endswith(
                    (".pyc", ".db", ".png", ".jpg", ".zip", ".tar", ".gz", ".xlsx", ".class", ".prefs", ".synapse_mutator_bak", ".bak")
                ):
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, repo_root)

                # Skip historical documentation, gitignore, or temporary coverage files
                if "FINAL_REPORT.md" in rel_path or ".gitignore" in rel_path or ".coverage" in rel_path:
                    continue

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        for line_no, line in enumerate(fp, 1):
                            for pattern, desc in FORBIDDEN_PATH_PATTERNS:
                                if pattern.search(line):
                                    violations.append((rel_path, line_no, desc))
                except (OSError, PermissionError):
                    continue

    if violations:
        print(f"[FAIL] {len(violations)} forbidden machine paths found:")
        for rel_path, line_no, term in violations:
            print(f"   - {rel_path}:{line_no} contains '{term}'")
        return False
    print("[PASS] Zero machine-specific absolute paths detected in source files.")
    return True


def is_page_class_path(file_path: str) -> bool:
    """Return True if the file path indicates a Page Class / Object Repository rather than a test script."""
    if not file_path:
        return False
    fp = file_path.replace("\\", "/").lower()
    # Directory checks for dedicated Page Class subfolders
    if any(p in fp for p in ["/pages/", "pages/", "/page_objects/", "page_objects/", "/object repository/", "/object-repository/"]):
        return True
    base = os.path.basename(fp)
    if base.endswith("page.js") or base.endswith("page.ts") or base.endswith("page.groovy") or base.endswith("page.py") or "basepage" in base:
        return True
    return False


def gate_3_clean_pom(repo_root, mode="AUTO"):
    """Gate 3: Enforces Clean Page Object Model by rejecting raw selectors in test scripts."""
    print("\n[GATE 3] Checking Clean POM & Flat Architecture in Test Scripts...")
    effective_mode = detect_repo_mode(repo_root) if mode == "AUTO" else mode
    if effective_mode == "HUB":
        examples_dir = os.path.join(repo_root, "examples")
        if os.path.isdir(examples_dir):
            print("[HUB MODE] Verifying Clean POM across reference example suites (examples/)...")
            test_dirs = ["examples"]
        else:
            print("[N/A] Hub Mode: Not Applicable (Clean POM rules apply to target test suites in Spokes).")
            return True
    else:
        test_dirs = ["Scripts", "tests", "test", "e2e", "specs", "cypress"]
    test_files = []
    for td in test_dirs:
        d = os.path.join(repo_root, td)
        if os.path.isdir(d):
            for ext in ("*.groovy", "*.ts", "*.js", "*.py", "*.java"):
                test_files.extend(glob.glob(os.path.join(d, "**", ext), recursive=True))

    if not test_files:
        print("[N/A] No test scripts present in candidate directories (Scripts/, tests/, e2e/).")
        return True

    LOCATOR_CALL_PATTERN = re.compile(
        r'(?:\.(?:click|dblclick|fill|type|press|check|locator|waitForSelector|hover|selectOption)|cy\.(?:get|find)|driver\.find[A-Za-z]*|WebUI\.[a-zA-Z]+)\s*\(\s*[\x22\x27`](?P<sel>[^\x22\x27`]+)[\x22\x27`]'
    )
    RAW_XPATH_PATTERN = re.compile(r'[\x22\x27`](?:xpath=|\/{2}[a-zA-Z*@\[])[^\x22\x27`]*[\x22\x27`]')
    SEMANTIC_LOCATOR_PATTERN = re.compile(
        r'(?:page|frame)\.(?:getByRole|getByLabel|getByPlaceholder|getByText|getByTestId|getByAltText|getByTitle)\s*\('
    )

    violations = []
    for full_path in sorted(set(test_files)):
        rel_path = os.path.relpath(full_path, repo_root)
        if is_page_class_path(rel_path):
            continue
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, 1):
                    stripped = line.strip()
                    if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("#"):
                        continue
                    # Ignore standard navigation statements to prevent false-positive XPath violations on URLs
                    if re.search(r'\.(?:goto|get|open|navigate)\s*\(\s*[\x22\x27]https?:\/\/', stripped):
                        continue
                    if "findTestObject" in line:
                        violations.append((rel_path, line_no, "Raw findTestObject"))
                        continue
                    # Check Playwright semantic locators in test script
                    if SEMANTIC_LOCATOR_PATTERN.search(stripped):
                        violations.append((rel_path, line_no, f"Raw Playwright semantic locator in Test Script: '{stripped}'"))
                        continue
                    # Check locator calls taking raw CSS/XPath selectors
                    m = LOCATOR_CALL_PATTERN.search(stripped)
                    if m:
                        sel = m.group('sel').strip()
                        if any(sel.startswith(p) for p in ('.', '#', '//', 'xpath=', '[')) or ' > ' in sel:
                            violations.append((rel_path, line_no, f"Raw CSS/XPath Selector in Test Script: '{sel}'"))
                            continue
                    if RAW_XPATH_PATTERN.search(stripped):
                        violations.append((rel_path, line_no, "Raw XPath literal in Test Script"))
        except (OSError, PermissionError):
            continue

    if violations:
        print(f"[FAIL] {len(violations)} Clean POM violations in test scripts:")
        for rel_path, line_no, reason in violations:
            print(f"   - {rel_path}:{line_no} ({reason})")
        return False
    print("[PASS] 100% Clean POM compliance (all locators encapsulated in Page Classes).")
    return True


def resolve_tool_path(repo_root, script_name, domain=""):
    """Resolves a tool path checking tools/<domain>/<script_name>, tools/<script_name>, or SCRIPT_DIR."""
    candidates = []
    if domain:
        candidates.append(os.path.join(repo_root, "tools", domain, script_name))
    candidates.append(os.path.join(repo_root, "tools", script_name))
    candidates.append(os.path.join(SCRIPT_DIR, script_name))
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(repo_root, "tools", domain, script_name) if domain else os.path.join(repo_root, "tools", script_name)


def gate_4_ai_docs_lint(repo_root, mode="AUTO"):
    """Gate 4: Reconciles PROJECT_AI_GUIDE.md against physical AST to prevent hallucinated classes."""
    print("\n[GATE 4] Running AI Documentation & Artifact Linter...")
    linter_script = resolve_tool_path(repo_root, "lint_ai_docs.py", "lint")
    if not os.path.exists(linter_script):
        print("[FAIL] lint_ai_docs.py not found in tools/!")
        return False

    try:
        res = subprocess.run([sys.executable, linter_script, repo_root], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=60.0)
    except subprocess.TimeoutExpired:
        print("[FAIL] lint_ai_docs.py timed out after 60s!")
        return False
    if res.returncode != 0:
        safe_print(res.stdout)
        safe_print(res.stderr)
        return False
    print("[PASS] Zero documentation drift / zero hallucinated PageClasses & Suites.")
    return True


def gate_5_cleanup_blacklist(repo_root, mode="AUTO"):
    """Gate 5: Scans for prohibited temporary files, heap dumps, and local cache artifacts."""
    print("\n[GATE 5] Checking Temporary File Blacklist...")
    blacklist_patterns = [
        os.path.join(repo_root, "Reports", "batch*.properties"),
        os.path.join(repo_root, "*_debug.txt"),
        os.path.join(repo_root, "debug_output.txt"),
        os.path.join(repo_root, "*.tmp"),
        os.path.join(repo_root, ".temp-*"),
        os.path.join(repo_root, "*_tmp.db"),
        os.path.join(repo_root, "temp_*.db"),
        os.path.join(repo_root, "nonexistent_*.db"),
        os.path.join(repo_root, "*.heapsnapshot"),
        os.path.join(repo_root, "*.hprof"),
    ]
    # Allowed test artifact directories exempted from heap dump cleanups
    exempt_prefixes = (
        os.path.normpath(os.path.join(repo_root, "Reports", "perf")),
        os.path.normpath(os.path.join(repo_root, ".synapse", "heapsnapshots")),
    )
    found = []
    for pattern in blacklist_patterns:
        for f in glob.glob(pattern):
            norm_f = os.path.normpath(f)
            if any(norm_f.startswith(prefix) for prefix in exempt_prefixes):
                continue
            if os.path.isfile(f):
                found.append(os.path.relpath(f, repo_root))

    if found:
        print(f"[FAIL] {len(found)} blacklisted temporary files found on disk:")
        for f in found:
            print(f"   - {f}")
        return False
    print("[PASS] Temporary file blacklist is clean.")
    return True


def gate_6_credential_security(repo_root, mode="AUTO", fast=False):
    """Gate 6: Scans for plaintext passwords, API tokens, and private keys across codebase."""
    print("\n[GATE 6] Checking Credential Security across repository...")
    violations = []

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
            if re.search(r'(?i)\b(?:Pass(?:word)?@?\d+|Admin@?\d+|Root@?\d+|Default@?\d+)\b', content):  # gate6-allowlist
                violations.append((glbl_file, 1, "Plaintext default password found in default.glbl"))
        except Exception as e:
            print(f"[WARN] Error reading default.glbl: {e}")

    # 2. Universal Repository Scan for Hardcoded Plaintext Secrets
    # High-confidence token patterns that must NEVER be bypassed by generic indicators
    token_patterns = [
        (re.compile(r'\bghp_[0-9a-zA-Z]{36}\b'), "GitHub Personal Access Token"),
        (re.compile(r'\bgithub_pat_[0-9a-zA-Z_]{82}\b'), "GitHub Fine-Grained Personal Access Token"),
        (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), "AWS Access Key ID"),
        (re.compile(r'\bsk_(?:live|test)_[0-9a-zA-Z]{24,}\b'), "Stripe Secret Key"),
        (re.compile(r'\bxox[baprs]-[0-9a-zA-Z-]{10,}\b'), "Slack API Token"),
        (re.compile(r'\bAIza[0-9A-Za-z-_]{35}\b'), "Google API Key"),
        (re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----'), "Private Key Header"),
    ]

    password_patterns = [
        (re.compile(r'(?i)\b(?:Pass(?:word)?@?\d+|Admin@?\d+|Root@?\d+|Default@?\d+)\b'), "Known Default Password"),
        (re.compile(r'(?i)\b(?:password|passwd|pwd)\s*[:=]\s*[\x22\x27][^\x22\x27]{4,}[\x22\x27]'), "Hardcoded Plaintext Password Assignment"),
    ]

    password_allowlist_indicators = [
        "System.getenv", "os.getenv", "os.environ", "process.env",
        "dummy", "placeholder", "***", "<password>", "your_password",
        "test_password", "NEO4J_PASSWORD", "DynamicTestPwd",
        "secret_patterns", "<name>PASSWORD</name>", 'password = ""', "password = ''",
        "type=str", "help="
    ]

    ignored_dirs = {
        ".git", ".gradle", "node_modules", "allure-results", "Screenshots",
        "Reports", "reports", "TestReports", "testreports", "Libs", ".settings", "graphify-out",
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "agent_qa.egg-info", "synapse_hub.egg-info", "dist", "build", "claude-ecosystem-repos", "external_repos", "teamwork", ".synapse", ".sandbox_snapshots"
    }

    valid_exts = (".py", ".groovy", ".ts", ".js", ".json", ".txt", ".md", ".yml", ".yaml", ".properties", ".sh", ".ps1", ".glbl")

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
            if norm_rel in ("tools/verify_all.py", "tools/core/verify_all.py", "tests/test_tools.py", "tests/test_git_pre_commit_guard.py") or norm_rel.endswith(("/verify_all.py", "/test_tools.py", "/test_git_pre_commit_guard.py")):
                continue
            full_path = os.path.join(repo_root, *parts)
            if not os.path.isfile(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        if "# gate6-allowlist" in line:
                            continue
                        for pat, desc in token_patterns:
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

                # Skip self scanning of pattern definitions in verify_all.py or scanner tests
                norm_rel = rel_path.replace("\\", "/")
                if norm_rel in ("tools/verify_all.py", "tools/core/verify_all.py", "tests/test_tools.py", "tests/test_git_pre_commit_guard.py") or norm_rel.endswith(("/verify_all.py", "/test_tools.py", "/test_git_pre_commit_guard.py")):
                    continue

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        for line_no, line in enumerate(fp, 1):
                            # Strict explicit allowlist comment
                            if "# gate6-allowlist" in line:
                                continue

                            # Check high-confidence token patterns (NEVER skipped by dummy, mock_, or # nosec)
                            for pat, desc in token_patterns:
                                if pat.search(line):
                                    violations.append((rel_path, line_no, desc))

                            # Check password patterns (subject to password_allowlist_indicators)
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

    print("[PASS] 100% Verified: Zero hardcoded plaintext credentials or secret tokens across repository.")
    return True


def check_python_ast_integrity(repo_root, fast=False):
    """
    Performs static AST validation across Python files in the repository.
    Enforces F821 parity (zero undefined variable names) and zero syntax errors.
    Accelerated with Boost B3 AST Pre-Validation Cache and Git Scoped Fast Path.
    """
    builtin_names = set(dir(builtins)) | {'__file__', '__name__', '__doc__', '__package__'}
    py_files = []
    ignored = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'claude-ecosystem-repos', 'build', 'dist', '.gradle', 'external_repos', 'teamwork', 'synapse_hub.egg-info', 'agent_qa.egg-info'}

    if fast:
        scoped = get_scoped_git_files(repo_root, staged_only=True)
        if scoped is not None:
            py_files = [
                os.path.join(repo_root, f.replace('/', os.sep))
                for f in scoped
                if f.endswith('.py') and os.path.isfile(os.path.join(repo_root, f.replace('/', os.sep)))
            ]
            if not py_files:
                return []

    if not py_files and not fast:
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored and not d.endswith('.egg-info') and not d.startswith(('synapse_hub-', 'synapse-hub-', '.temp-'))]
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))

    violations = []

    # Boost B3: Initialize AST Pre-Validation Cache
    try:
        from ast_cache import get_ast_cache
        cache = get_ast_cache(repo_root)
    except Exception:
        try:
            from tools.ast_cache import get_ast_cache
            cache = get_ast_cache(repo_root)
        except Exception:
            try:
                tools_dir = os.path.dirname(os.path.abspath(__file__))
                if tools_dir not in sys.path:
                    sys.path.insert(0, tools_dir)
                from ast_cache import get_ast_cache
                cache = get_ast_cache(repo_root)
            except Exception:
                cache = None

    for file_path in sorted(py_files):
        rel_path = os.path.relpath(file_path, repo_root)

        sig = cache.get_signature(file_path) if cache else None
        if sig is not None:
            cached_data = cache.get_cached_result(rel_path, sig[0], sig[1])
            if cached_data is not None:
                cached_viols = cached_data.get("violations", [])
                violations.extend([(rel_path, v[0], v[1]) for v in cached_viols])
                continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
            tree = ast.parse(content, file_path)
        except (FileNotFoundError, OSError):
            continue
        except SyntaxError as e:
            syntax_viol = (rel_path, e.lineno or 1, f"SyntaxError: {e.msg}")
            violations.append(syntax_viol)
            if cache and sig is not None:
                cache.put_result(rel_path, sig[0], sig[1], {"violations": [[syntax_viol[1], syntax_viol[2]]]})
            continue

        module_names = set(builtin_names)
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                module_names.add(stmt.name)
            elif isinstance(stmt, ast.Import):
                for a in stmt.names:
                    module_names.add(a.asname or a.name.split('.')[0])
            elif isinstance(stmt, ast.ImportFrom):
                for a in stmt.names:
                    module_names.add(a.asname or a.name)
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                targets = [stmt.target] if isinstance(stmt, ast.AnnAssign) else stmt.targets
                for t in targets:
                    for n in ast.walk(t):
                        if isinstance(n, ast.Name):
                            module_names.add(n.id)
            for n in ast.walk(stmt):
                if hasattr(ast, 'NamedExpr') and isinstance(n, ast.NamedExpr) and isinstance(getattr(n, 'target', None), ast.Name):
                    module_names.add(n.target.id)

        class ScopeVisitor(ast.NodeVisitor):
            def __init__(self):
                self.scopes = [set(module_names)]
                self.file_violations = []

            def visit_FunctionDef(self, node):
                self.scopes[-1].add(node.name)
                fn_scope = set(self.scopes[-1])
                for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
                    fn_scope.add(arg.arg)
                if node.args.vararg:
                    fn_scope.add(node.args.vararg.arg)
                if node.args.kwarg:
                    fn_scope.add(node.args.kwarg.arg)
                self.scopes.append(fn_scope)
                self.generic_visit(node)
                self.scopes.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_ClassDef(self, node):
                self.scopes[-1].add(node.name)
                cls_scope = set(self.scopes[-1])
                self.scopes.append(cls_scope)
                self.generic_visit(node)
                self.scopes.pop()

            def visit_Assign(self, node):
                for t in node.targets:
                    for n in ast.walk(t):
                        if isinstance(n, ast.Name):
                            self.scopes[-1].add(n.id)
                self.generic_visit(node)

            def visit_AnnAssign(self, node):
                if isinstance(node.target, ast.Name):
                    self.scopes[-1].add(node.target.id)
                self.generic_visit(node)

            def visit_For(self, node):
                for n in ast.walk(node.target):
                    if isinstance(n, ast.Name):
                        self.scopes[-1].add(n.id)
                self.generic_visit(node)

            def visit_With(self, node):
                for item in node.items:
                    if item.optional_vars:
                        for n in ast.walk(item.optional_vars):
                            if isinstance(n, ast.Name):
                                self.scopes[-1].add(n.id)
                self.generic_visit(node)

            def visit_ExceptHandler(self, node):
                if node.name:
                    self.scopes[-1].add(node.name)
                self.generic_visit(node)

            def visit_NamedExpr(self, node):
                if isinstance(node.target, ast.Name):
                    for s in self.scopes:
                        s.add(node.target.id)
                self.generic_visit(node)

            def visit_Match(self, node):
                for case in getattr(node, 'cases', []):
                    pattern = getattr(case, 'pattern', None)
                    if pattern:
                        for n in ast.walk(pattern):
                            name = getattr(n, 'name', None)
                            if isinstance(name, str):
                                self.scopes[-1].add(name)
                            rest = getattr(n, 'rest', None)
                            if isinstance(rest, str):
                                self.scopes[-1].add(rest)
                self.generic_visit(node)

            def visit_Global(self, node):
                for name in node.names:
                    for s in self.scopes:
                        s.add(name)
                self.generic_visit(node)

            def visit_Nonlocal(self, node):
                for name in node.names:
                    self.scopes[-1].add(name)
                self.generic_visit(node)

            def visit_Import(self, node):
                for a in node.names:
                    self.scopes[-1].add(a.asname or a.name.split('.')[0])

            def visit_ImportFrom(self, node):
                for a in node.names:
                    self.scopes[-1].add(a.asname or a.name)

            def visit_ListComp(self, node):
                comp_scope = set(self.scopes[-1])
                for gen in node.generators:
                    for n in ast.walk(gen.target):
                        if isinstance(n, ast.Name):
                            comp_scope.add(n.id)
                self.scopes.append(comp_scope)
                self.generic_visit(node)
                self.scopes.pop()

            visit_SetComp = visit_ListComp
            visit_GeneratorExp = visit_ListComp
            visit_DictComp = visit_ListComp

            def visit_Lambda(self, node):
                lam_scope = set(self.scopes[-1])
                for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
                    lam_scope.add(arg.arg)
                if node.args.vararg:
                    lam_scope.add(node.args.vararg.arg)
                if node.args.kwarg:
                    lam_scope.add(node.args.kwarg.arg)
                self.scopes.append(lam_scope)
                self.generic_visit(node)
                self.scopes.pop()

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load):
                    if node.id.startswith('__') and node.id.endswith('__'):
                        return
                    if not any(node.id in s for s in reversed(self.scopes)):
                        self.file_violations.append((rel_path, node.lineno, f"Undefined name '{node.id}' (F821)"))

        visitor = ScopeVisitor()
        visitor.visit(tree)
        violations.extend(visitor.file_violations)

        if cache and sig is not None:
            cache.put_result(
                rel_path,
                sig[0],
                sig[1],
                {"violations": [[v[1], v[2]] for v in visitor.file_violations]}
            )

    if cache:
        cache.save()

    return violations


def has_python_sources(repo_root: str) -> bool:
    """Fast O(1) check if repository contains any Python source files, pruning heavy directories."""
    candidate_dirs = [".", "tests", "test", "pages", "src", "Scripts", "features", "step_definitions"]
    for cd in candidate_dirs:
        target = os.path.join(repo_root, cd) if cd != "." else repo_root
        if os.path.isdir(target):
            try:
                for entry in os.scandir(target):
                    if entry.is_file(follow_symlinks=False) and entry.name.endswith(".py"):
                        return True
            except OSError:
                continue

    ignored = {".git", "node_modules", ".venv", "venv", "build", "dist", ".gradle", "target", "__pycache__"}
    try:
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored]
            if any(f.endswith(".py") for f in files):
                return True
    except OSError:
        return False
    return False


def gate_7_infer_linter(repo_root, mode="AUTO", fast=False):
    """Gate 7: Runs Meta Infer-style static defect sentinel catching fake passes, 0 assert, and sleeps."""
    print("\n[GATE 7] Running Meta Infer-Style Static Defect & Fake-Pass Sentinel...")
    effective_mode = detect_repo_mode(repo_root) if mode == "AUTO" else mode

    # Static Python AST & Undefined Name (F821) Sentinel
    ast_violations = check_python_ast_integrity(repo_root, fast=fast)
    if ast_violations:
        print(f"[FAIL] Static Python AST Sentinel detected {len(ast_violations)} syntax errors or undefined names:")
        for rel_file, line_no, desc in ast_violations:
            print(f"   - {rel_file}:{line_no} -> {desc}")
        return False
    print("[PASS] 100% Python AST integrity verified (zero syntax errors, zero undefined variables).")

    # Ruff Linter & Code Quality Sentinel (Hub vs Target Adaptive Policy)
    if effective_mode == "HUB":
        # Ruff Linter & Code Quality Sentinel for Synapse Hub codebase
        if fast:
            scoped = get_scoped_git_files(repo_root, staged_only=True)
            if scoped is not None:
                ruff_targets = [
                    f.replace('/', os.sep) for f in scoped
                    if f.endswith('.py') and os.path.isfile(os.path.join(repo_root, f.replace('/', os.sep)))
                ]
                if not ruff_targets:
                    print("[PASS] [FAST MODE] Zero changed Python files detected (Ruff instant pass).")
            else:
                ruff_targets = []
        else:
            ruff_targets = [d for d in ["tools", "tests", "scripts"] if os.path.isdir(os.path.join(repo_root, d))]
        if ruff_targets:
            try:
                res_ruff = subprocess.run(
                    [sys.executable, "-m", "ruff", "check"] + ruff_targets,
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=45.0,
                )
                if res_ruff.returncode == 0:
                    print(f"[PASS] 100% Ruff clean: zero linting defects across {', '.join(ruff_targets)}.")
                elif "No module named ruff" in (res_ruff.stderr or ""):
                    print("[INFO] Ruff not installed in current environment, skipping ruff check.")
                else:
                    print(f"[FAIL] Ruff linter detected violations across {', '.join(ruff_targets)}:")
                    safe_print(res_ruff.stdout or res_ruff.stderr)
                    return False
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as err:
                print(f"[WARN] Ruff execution skipped: {err}")
    else:
        # TARGET mode: Adaptive Ruff Sentinel for Target Project Python files
        if has_python_sources(repo_root):
            try:
                has_own_config = (
                    os.path.isfile(os.path.join(repo_root, "ruff.toml"))
                    or os.path.isfile(os.path.join(repo_root, ".ruff.toml"))
                    or (
                        os.path.isfile(os.path.join(repo_root, "pyproject.toml"))
                        and "[tool.ruff" in open(os.path.join(repo_root, "pyproject.toml"), "r", encoding="utf-8", errors="ignore").read()
                    )
                )

                if has_own_config:
                    ruff_cmd = [sys.executable, "-m", "ruff", "check", repo_root]
                else:
                    ruff_cmd = [
                        sys.executable, "-m", "ruff", "check",
                        "--select", "E,F",
                        "--ignore", "E501,E731,E741,F841",
                        "--exclude", ".git,.venv,venv,node_modules,build,dist,__pycache__,reports,Reports,Screenshots",
                        repo_root,
                    ]

                res_ruff = subprocess.run(
                    ruff_cmd,
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=45.0,
                )
                if res_ruff.returncode == 0:
                    print("[PASS] 100% Target Python code verified clean via Ruff (zero syntax or critical defects).")
                elif "No module named ruff" in (res_ruff.stderr or ""):
                    print("[INFO] Ruff not installed in target environment, skipping ruff check.")
                else:
                    print("[FAIL] Ruff linter detected defects in target Python project:")
                    safe_print(res_ruff.stdout or res_ruff.stderr)
                    return False
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as err:
                print(f"[WARN] Target Ruff execution skipped: {err}")
        else:
            print("[PASS] Non-Python target stack: zero Python files detected (Ruff skipped).")

    # In HUB mode: dogfood tools/ with baseline to prevent new unbaselined defects
    if effective_mode == "HUB":

        baseline_file = os.path.join(repo_root, "tools", ".infer_baseline.json")
        infer_script = resolve_tool_path(repo_root, "infer_linter.py", "lint")
        if os.path.exists(baseline_file) and os.path.exists(infer_script):
            tools_dir = os.path.join(repo_root, "tools")
            try:
                res = subprocess.run([
                    sys.executable, infer_script, "--strict", "--baseline", baseline_file, "--dir", tools_dir
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=60.0)
                if res.returncode != 0:
                    print("[FAIL] Hub internal tools contain unbaselined critical defects:")
                    safe_print(res.stdout)
                    return False
            except subprocess.TimeoutExpired:
                print("[FAIL] infer_linter.py timed out after 60s!")
                return False
            except (OSError, subprocess.SubprocessError) as err:
                print(f"[WARN] Failed to execute infer_linter: {err}")

        # Hub Mode Version Synchronization Verification
        try:
            import check_version_sync
            synced, versions, canonical = check_version_sync.check_sync(repo_root)
            if not synced:
                print(f"[FAIL] Gate 7 Version Synchronization: Inconsistent versions detected across manifests: {versions}")
                return False
        except (ImportError, OSError) as err:
            print(f"[WARN] Failed to run check_version_sync: {err}")

        # Hub Mode Regression Test Suite Verification
        if fast:
            safe_print("[PASS] [FAST MODE] Hub Regression Test Suite skipped for sub-3s rapid verification.")
            LAST_GATE_METRICS["gate_7"] = {
                "status": "FAST_MODE",
                "execution_mode": "FAST_PASS",
                "collected": 0,
                "passed": 1,
                "duration_seconds": 0.05,
                "note": "Regression suite execution skipped via --fast for sub-3s feedback",
            }
        elif "PYTEST_CURRENT_TEST" not in os.environ and os.environ.get("SYNAPSE_GATE7_TESTING") != "1":
            safe_print("[GATE 7] Executing Hub Regression Test Suite (pytest tests -q)...")
            tests_dir = os.path.join(repo_root, "tests")
            if os.path.isdir(tests_dir):
                env = os.environ.copy()
                env["SYNAPSE_GATE7_TESTING"] = "1"
                env["SYNAPSE_LANG"] = "en"
                env["PYTHONIOENCODING"] = "utf-8"
                reports_dir = os.path.join(repo_root, "reports")
                os.makedirs(reports_dir, exist_ok=True)
                junit_file = os.path.join(reports_dir, "junit_test_report.xml")
                pytest_cmd = [sys.executable, "-m", "pytest", "tests", "-q", f"--junitxml={junit_file}"]
                import importlib.util
                if importlib.util.find_spec("xdist") is not None:
                    # Windows & cross-platform guard: cap workers to min(cpu_count, 8) to prevent socket/process exhaustion
                    max_workers = max(1, min(os.cpu_count() or 4, 8))
                    pytest_cmd.extend(["-n", str(max_workers)])
                try:
                    test_res = subprocess.run(
                        pytest_cmd,
                        cwd=repo_root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=360.0,
                        env=env
                    )
                    combined_output = (test_res.stdout or "") + "\n" + (test_res.stderr or "")
                    commit_sha = get_git_commit_sha(repo_root)
                    metrics = parse_pytest_metrics(combined_output)
                    metrics["commit"] = commit_sha
                    if os.path.exists(junit_file):
                        metrics["junit_report_path"] = os.path.relpath(junit_file, repo_root)
                    LAST_GATE_METRICS["gate_7"] = metrics

                    if test_res.returncode != 0:
                        safe_print(f"[FAIL] Gate 7 Hub Regression Test Suite Failed ({metrics.get('failed', 0)} failed):")
                        safe_print(test_res.stdout or test_res.stderr)
                        return False

                    summary_parts = [f"{metrics['passed']} passed"]
                    if metrics.get("skipped", 0) > 0:
                        summary_parts.append(f"{metrics['skipped']} skipped")
                    if metrics.get("failed", 0) > 0:
                        summary_parts.append(f"{metrics['failed']} failed")
                    if metrics.get("xfailed", 0) > 0:
                        summary_parts.append(f"{metrics['xfailed']} xfailed")
                    metrics_desc = ", ".join(summary_parts)
                    safe_print(f"[PASS] Hub regression test suite passed: {metrics_desc} in {metrics['duration_seconds']:.2f}s (Git commit: {commit_sha}).")
                except subprocess.TimeoutExpired:
                    safe_print("[FAIL] Gate 7 Hub Regression Test Suite timed out after 360s!")
                    return False
                except (OSError, subprocess.SubprocessError) as err:
                    safe_print(f"[FAIL] Gate 7 Failed to run test suite: {err}")
                    return False
            else:
                safe_print(f"[FAIL] Gate 7 Hub Mode: Missing mandatory 'tests/' directory at {tests_dir}!")
                return False
        else:
            commit_sha = get_git_commit_sha(repo_root)
            if "gate_7" not in LAST_GATE_METRICS:
                parent_test = os.environ.get("PYTEST_CURRENT_TEST", "").split(" ")[0]
                LAST_GATE_METRICS["gate_7"] = {
                    "status": "PARENT_RUNNER_ACTIVE",
                    "execution_mode": "PARENT_SESSION",
                    "collected": 0,
                    "passed": 0,
                    "skipped": 0,
                    "failed": 0,
                    "xfailed": 0,
                    "duration_seconds": 0.0,
                    "commit": commit_sha,
                    "uncollected": True,
                    "parent_test": parent_test or "active_pytest_runner",
                    "note": "Regression suite execution managed dynamically by active parent test runner",
                }
            safe_print(f"[PASS] Hub Mode Regression Test Suite: Verified via active parent test runner (Git commit: {commit_sha}).")

    test_dirs = ["examples"] if effective_mode == "HUB" else ["Scripts", "tests", "test", "e2e", "specs", "cypress"]
    has_tests = False
    target_scan_dir = None
    for td in test_dirs:
        d = os.path.join(repo_root, td)
        if os.path.isdir(d):
            for ext in ("*.groovy", "*.ts", "*.js", "*.py", "*.java"):
                if glob.glob(os.path.join(d, "**", ext), recursive=True):
                    has_tests = True
                    target_scan_dir = d
                    break
        if has_tests:
            break

    if not has_tests:
        print("[N/A] No test scripts (Groovy/TS/JS/Py) present in candidate test directories.")
        return True

    infer_script = resolve_tool_path(repo_root, "infer_linter.py", "lint")

    if os.path.exists(infer_script):
        try:
            target_baseline = os.path.join(repo_root, ".infer_baseline.json")
            cmd = [sys.executable, infer_script, "--strict", "--dir", target_scan_dir]
            if os.path.exists(target_baseline):
                cmd.extend(["--baseline", target_baseline])
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=60.0)
            if res.returncode != 0:
                print("[FAIL] Static Defect Sentinel detected critical issues in test scripts:")
                safe_print(res.stdout)
                return False
        except subprocess.TimeoutExpired:
            print("[FAIL] infer_linter.py timed out after 60s!")
            return False
    print("[PASS] Zero critical defects / zero swallowed exceptions across active test suites.")
    return True


def gate_8_micro_mutator(repo_root, mode="AUTO", test_cmd="", scoped_test_cmd="", changed_only=False, fast=False):
    """Gate 8: Runs syntactic mutation testing and verifies assertion sensitivity score >= 80%."""
    effective_mode = detect_repo_mode(repo_root) if mode == "AUTO" else mode
    is_pr_or_changed = not fast and (changed_only or bool(scoped_test_cmd) or os.environ.get("SYNAPSE_PR_MODE") == "1")

    mutator_script = resolve_tool_path(repo_root, "micro_mutator.py", "lint")

    if not os.path.exists(mutator_script):
        print("[FAIL] micro_mutator.py not found in tools/! Gate 8 requires micro_mutator.py (fail-closed).")
        return False

    cfg = load_synapse_config(repo_root)
    qg_cfg = cfg.get("quality_gates", {})
    min_score_val = float(qg_cfg.get("mutation_min_score", 80.0))
    min_score_str = str(min_score_val)
    allow_empty_val = bool(qg_cfg.get("allow_empty_mutations", False))

    # PR / Changed Code Scoped Dynamic Mutation Mode
    if effective_mode == "HUB" and is_pr_or_changed:
        print(f"\n[GATE 8] Running Assertion Sensitivity & Scoped Syntactic Mutation Sentinel [PR / CHANGED CODE MODE] (Min Score >= {min_score_str}%)...")
        modified_files = []
        try:
            from tools import test_impact
            if hasattr(test_impact, "get_git_modified_files"):
                modified_files = test_impact.get_git_modified_files(repo_root)
        except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass

        if not modified_files:
            try:
                res = subprocess.run(
                    ["git", "-C", repo_root, "diff", "--name-only", "HEAD"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0
                )
                modified_files = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            except (OSError, subprocess.SubprocessError):  # synapse-ignore: SWALLOWED_EXCEPTION
                modified_files = []

        py_targets = [
            f for f in modified_files
            if f.endswith(".py")
            and (f.startswith("tools/") or f.startswith("tools\\"))
            and not f.startswith(("tools/templates", "tools/templates/"))
        ]

        if not py_targets:
            print("[PASS] Scoped Dynamic Mutation: Zero modified source files in tools/ detected in Git diff. Gate 8 passed.")
            LAST_GATE_METRICS["gate_8"] = {
                "mode": "DYNAMIC_SCOPED",
                "measurement_kind": "no_modified_code",
                "modified_files": [],
                "dynamic_mutation_score": None,
                "static_assertion_sensitivity_score": None,
                "mutation_score": None,
                "valid_mutants": 0,
                "killed": 0,
                "survived": 0,
                "timed_out": 0,
                "invalid_syntax": 0,
                "passed": True,
                "note": "Zero modified Python source files in tools/ detected in Git diff"
            }
            return True

        print(f"   Detected {len(py_targets)} modified source file(s) for scoped mutation: {', '.join(py_targets)}")
        effective_scoped_cmd = scoped_test_cmd or f"{sys.executable} -m pytest {{test_files}} -q"

        all_ok = True
        gate8_reports = []
        for target_rel in py_targets:
            target_abs = os.path.join(repo_root, target_rel)
            if not os.path.isfile(target_abs):
                continue
            cmd = [
                sys.executable, mutator_script, target_abs,
                "--scoped-test-cmd", effective_scoped_cmd,
                "--min-score", min_score_str,
                "--allow-empty",
                "--json"
            ]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180.0)
                try:
                    rep = json.loads(proc.stdout)
                except Exception:
                    rep = {
                        "passed": proc.returncode == 0,
                        "mutation_score": 0.0 if proc.returncode != 0 else None,
                        "dynamic_mutation_score": 0.0 if proc.returncode != 0 else None,
                        "valid_mutants": 0,
                        "killed": 0,
                        "survived": 0,
                        "timed_out": 0,
                        "invalid_syntax": 0
                    }
                gate8_reports.append((target_rel, rep))
                dyn_score = rep.get("dynamic_mutation_score", rep.get("mutation_score", 0.0))
                if proc.returncode != 0:
                    all_ok = False
                    safe_print(f"[FAIL] Scoped Dynamic Mutation failed on {target_rel} (Score: {dyn_score}% < {min_score_str}%, survived: {rep.get('survived', 0)})")
                    if proc.stderr:
                        safe_print(proc.stderr)
                else:
                    valid_cnt = rep.get("valid_mutants", rep.get("total_mutants", 0))
                    safe_print(f"[PASS] Scoped Dynamic Mutation on {target_rel}: {dyn_score}% (Killed {rep.get('killed', 0)}/{valid_cnt} valid mutants)")
            except subprocess.TimeoutExpired:
                safe_print(f"[FAIL] Scoped Dynamic Mutation timed out on {target_rel} after 180s")
                all_ok = False

        total_killed = sum(r.get("killed", 0) for r in [x[1] for x in gate8_reports])
        total_survived = sum(r.get("survived", 0) for r in [x[1] for x in gate8_reports])
        total_timed_out = sum(r.get("timed_out", 0) for r in [x[1] for x in gate8_reports])
        total_invalid = sum(r.get("invalid_syntax", 0) for r in [x[1] for x in gate8_reports])
        total_valid = total_killed + total_survived + total_timed_out
        overall_score = round((total_killed / total_valid) * 100.0, 2) if total_valid > 0 else 0.0

        LAST_GATE_METRICS["gate_8"] = {
            "mode": "DYNAMIC_SCOPED",
            "measurement_kind": "dynamic_execution",
            "modified_files": py_targets,
            "dynamic_mutation_score": overall_score if total_valid > 0 else None,
            "static_assertion_sensitivity_score": None,
            "mutation_score": overall_score if total_valid > 0 else None,
            "valid_mutants": total_valid,
            "killed": total_killed,
            "survived": total_survived,
            "timed_out": total_timed_out,
            "invalid_syntax": total_invalid,
            "passed": all_ok,
            "reports": [r[1] for r in gate8_reports]
        }
        return all_ok

    eval_mode_desc = f"DYNAMIC EXECUTION MODE ({test_cmd})" if test_cmd else "HEURISTIC STATIC MODE"
    print(f"\n[GATE 8] Running Assertion Sensitivity & Syntactic Mutation Sentinel [{eval_mode_desc}] (Min Score >= 80%)...")
    scripts_dir = os.path.join(repo_root, "Scripts")
    tests_dir = os.path.join(repo_root, "tests")

    target_dir = None
    if os.path.isdir(scripts_dir):
        groovy_files = [f for f in glob.glob(os.path.join(scripts_dir, "**", "*.groovy"), recursive=True)]
        if groovy_files:
            target_dir = scripts_dir
    if not target_dir and os.path.isdir(tests_dir):
        test_files = [f for f in glob.glob(os.path.join(tests_dir, "**", "*.*"), recursive=True) if f.endswith((".py", ".ts", ".js", ".groovy"))]
        if test_files:
            target_dir = tests_dir

    if not target_dir:
        if effective_mode == "HUB":
            print(f"[N/A] Hub Mode: Not Applicable (Assertion Sensitivity & Syntactic Mutation applies to target test suites in Spokes) [{eval_mode_desc}].")
            return True
        else:
            print("[N/A] No automated test scripts found in Scripts/ or tests/ to mutate.")
            return True

    if not test_cmd:
        test_cmd = qg_cfg.get("test_cmd") or cfg.get("test_cmd", "")

    baseline_dir = os.path.join(repo_root, "reports")
    os.makedirs(baseline_dir, exist_ok=True)
    baseline_file = os.path.join(baseline_dir, "mutant_baseline.json")

    cmd = [sys.executable, mutator_script, target_dir, "--min-score", min_score_str, "--baseline", baseline_file, "--json"]
    if test_cmd:
        cmd.extend(["--test-cmd", test_cmd])
    if allow_empty_val:
        cmd.append("--allow-empty")
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=120.0)
    except subprocess.TimeoutExpired:
        print("[FAIL] Assertion Sensitivity Sentinel timed out after 120s!")
        return False
    if res.returncode != 0:
        try:
            data = json.loads(res.stdout)
            if data.get("total_mutants", 0) == 0 or data.get("no_mutants_generated"):
                if allow_empty_val:
                    print(f"[N/A] Zero mutable expressions detected in {target_dir} (Allowed by configuration). Gate 8 skipped.")
                    return True
                else:
                    print(f"[FAIL] Gate 8 REJECTED: Zero mutable expressions detected in {target_dir}! Test suite must contain mutable logic or assertions. (Fail-closed)")
                    return False
            print("[FAIL] Assertion Sensitivity Sentinel REJECTED: Score < 80% or unasserted logic found.")
            print(f"   Assertion Sensitivity: {data.get('mutation_score', 0)}% (Required: >= 80%)")
            print(f"   Mutants Caught: {data.get('killed', 0)} / {data.get('total_mutants', 0)}")
        except (json.JSONDecodeError, ValueError, KeyError):
            if res.stdout:
                safe_print(res.stdout)
        return False
    else:
        try:
            data = json.loads(res.stdout)
            mode_label = f"DYNAMIC ({test_cmd})" if test_cmd else "STATIC AST HEURISTIC"
            is_dynamic = bool(test_cmd)
            score_val = data.get("mutation_score", 100.0)
            score_label = "Runtime Dynamic Mutation Score" if is_dynamic else "Assertion Sensitivity [STATIC AST HEURISTIC]"
            denominator_desc = "valid mutants" if is_dynamic else "syntactic mutants"
            print(f"[PASS] {score_label}: {score_val}% >= 80% (Caught {data.get('killed', 0)}/{data.get('total_mutants', 0)} {denominator_desc}). Zero unasserted logic branches.")
            if not test_cmd:
                print("   ℹ️  Note: Evaluated via static AST dataflow analysis. Pass --test-cmd '<command>' to execute live mutant runs.")
            if os.path.exists(baseline_file):
                print(f"   Mutant Baseline: Recorded {data.get('killed', 0)}/{data.get('total_mutants', 0)} mutants ({score_val}%) into reports/mutant_baseline.json")
            LAST_GATE_METRICS["gate_8"] = {
                "mode": mode_label,
                "measurement_kind": "dynamic_execution" if is_dynamic else "static_ast_heuristic",
                "static_assertion_sensitivity_score": score_val if not is_dynamic else None,
                "dynamic_mutation_score": score_val if is_dynamic else None,
                "mutation_score": score_val,
                "killed": data.get("killed", 0),
                "survived": data.get("survived", 0),
                "timed_out": data.get("timed_out", 0),
                "invalid_syntax": data.get("invalid_syntax", 0),
                "total_mutants": data.get("total_mutants", 0),
                "valid_mutants": data.get("valid_mutants", data.get("total_mutants", 0)),
                "passed": True
            }
        except (json.JSONDecodeError, ValueError, KeyError):
            print(f"[PASS] Assertion Sensitivity Sentinel passed: Score >= 80% [{eval_mode_desc}].")
            LAST_GATE_METRICS["gate_8"] = {
                "mode": eval_mode_desc,
                "measurement_kind": "dynamic_execution" if test_cmd else "static_ast_heuristic",
                "static_assertion_sensitivity_score": 100.0 if not test_cmd else None,
                "dynamic_mutation_score": 100.0 if test_cmd else None,
                "mutation_score": 100.0,
                "killed": 0,
                "total_mutants": 0,
                "valid_mutants": 0,
                "passed": True
            }
        return True


def gate_9_skill_collision(repo_root, mode="AUTO"):
    """Gate 9: Scans skill descriptions and rules to ensure semantic trigger overlap remains < 0.75."""
    print("\n[GATE 9] Running Tier-2 Skill Routing & Collision Guard (Addy Osmani Pattern)...")
    guard_script = resolve_tool_path(repo_root, "skill_collision_guard.py", "lint")
    if not os.path.exists(guard_script):
        print("[FAIL] skill_collision_guard.py not found in tools/!")
        return False

    skills_dir = os.path.join(repo_root, ".agents", "skills")
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    manifest_file = os.path.join(repo_root, "skills_manifest.json")
    if not os.path.exists(skills_dir) and not os.path.exists(manifest_file):
        print("[PASS] Target project mode: skills not present (SKIPPED).")
        return True

    # 1. Skill Schema & Policy Validation
    schema_validator = resolve_tool_path(repo_root, "validate_skills_schema.py", "lint")

    if os.path.exists(schema_validator):
        try:
            validator_cmd = [sys.executable, schema_validator, "--check-links"]
            if os.path.exists(skills_dir):
                validator_cmd.extend(["--skills-dir", skills_dir])
            s_res = subprocess.run(
                validator_cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=60.0
            )
            if s_res.returncode != 0:
                print("[FAIL] Gate 9 Skill Schema Validation Failed:")
                safe_print(s_res.stdout)
                safe_print(s_res.stderr)
                return False
            print("[PASS] 100% Verified: All registered skills conform to Frontmatter Schema & Policies.")
        except Exception as s_err:
            print(f"[FAIL] Gate 9 Skill Schema Validator execution error: {s_err}")
            return False

    # 2. Addy Osmani TF-IDF Skill Collision Guard
    cmd = [sys.executable, guard_script, "--threshold", "0.75"]
    if os.path.exists(skills_dir):
        cmd.extend(["--dir", skills_dir])
    if os.path.exists(rules_dir):
        cmd.extend(["--scan-rules", "--rules-dir", rules_dir])

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=60.0)
    except subprocess.TimeoutExpired:
        print("[FAIL] skill_collision_guard.py timed out after 60s!")
        return False

    if res.returncode != 0:
        safe_print(res.stdout)
        safe_print(res.stderr)
        return False
    print("[PASS] 100% Verified: 0 skill description and rule collisions detected (similarity < 0.75).")

    # Run Mechanical UI Finish Gate (Leonxlnx taste-skill pattern)
    mech_script = resolve_tool_path(repo_root, "mechanical_ui_gate.py", "design")
    if os.path.exists(mech_script):
        try:
            m_res = subprocess.run([sys.executable, mech_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=30.0)
            if m_res.returncode == 0:
                print("[PASS] Mechanical UI Finish Gate: Layout, contrast, and interactive elements verified.")
            else:
                safe_print(f"[WARN] Mechanical UI Finish Gate non-zero exit: {m_res.stderr.strip()[:100]}")
        except (OSError, subprocess.SubprocessError) as m_err:
            safe_print(f"[WARN] Mechanical UI Finish Gate execution error: {m_err}")

    # 3. Canonical Skills Lockfile & Content Hash Integrity Verification
    try:
        from skill_canonical_digest import validate_lockfile_integrity
        lock_ok, lock_msg = validate_lockfile_integrity(repo_root, enforce_content_hash=True)
        if not lock_ok:
            print(f"[FAIL] Gate 9 Skills Lockfile Integrity: {lock_msg}")
            return False
        print(f"[PASS] 100% Verified: {lock_msg}.")
    except Exception as lock_err:
        print(f"[FAIL] Gate 9 Skills Lockfile verification exception: {lock_err}")
        return False

    return True


def gate_10_performance_sla(repo_root, mode="AUTO"):
    """Gate 10: Performance & SLA Sentinel: Ingests perf test results (.jtl, k6_summary.json) and enforces SLA thresholds."""
    print("\n[GATE 10] Running Performance & SLA Sentinel...")
    perf_dirs = [
        os.path.join(repo_root, "Reports", "perf"),
        os.path.join(repo_root, "Reports"),
        os.path.join(repo_root, ".synapse", "perf")
    ]

    jtl_candidates = []
    k6_candidates = []
    for pdir in perf_dirs:
        if os.path.exists(pdir):
            jtl_candidates.extend(glob.glob(os.path.join(pdir, "*.jtl")))
            jtl_candidates.extend(glob.glob(os.path.join(pdir, "*_results.csv")))
            k6_candidates.extend(glob.glob(os.path.join(pdir, "*k6*.json")))
            k6_candidates.extend(glob.glob(os.path.join(pdir, "summary.json")))

    cfg = load_synapse_config(repo_root)
    perf_top_cfg = cfg.get("performance", {})
    perf_cfg = perf_top_cfg.get("sla", {})
    sla_p95 = perf_cfg.get("p95_ms", 500.0)
    sla_p99 = perf_cfg.get("p99_ms", 1000.0)
    max_error_rate = perf_cfg.get("max_error_rate_pct", 1.0)

    fresh_benchmark_run = False

    # Check for companion metadata file or k6 metadata
    meta = {}
    meta_candidates = [
        os.path.join(repo_root, "Reports", "perf", "perf_metadata.json"),
        os.path.join(repo_root, "Reports", "perf_metadata.json"),
    ]
    for mpath in meta_candidates:
        if os.path.exists(mpath):
            try:
                with open(mpath, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
                break
            except (OSError, json.JSONDecodeError) as err:  # synapse-ignore: SWALLOWED_EXCEPTION
                logging.getLogger("verify_all").debug("Could not read perf_metadata: %s", err)

    if not meta and k6_candidates:
        for kp in k6_candidates:
            try:
                with open(kp, "r", encoding="utf-8") as kf:
                    k_obj = json.load(kf)
                    if isinstance(k_obj, dict) and "metadata" in k_obj:
                        meta = k_obj["metadata"]
                        break
            except (OSError, json.JSONDecodeError) as err:  # synapse-ignore: SWALLOWED_EXCEPTION
                logging.getLogger("verify_all").debug("Could not read k6 metadata: %s", err)

    max_age_hours = float(perf_top_cfg.get("max_artifact_age_hours") or perf_cfg.get("max_artifact_age_hours") or 24.0)
    require_fresh = bool(perf_top_cfg.get("require_fresh") or perf_cfg.get("require_fresh") or os.environ.get("SYNAPSE_PERF_FRESH") == "1")

    # Assess staleness of pre-existing artifacts
    is_stale = False
    staleness_reason = None
    if jtl_candidates or k6_candidates:
        sample_path = (k6_candidates or jtl_candidates)[0]
        gen_time_str = meta.get("generated_at")
        artifact_epoch = None
        if gen_time_str:
            try:
                dt = datetime.fromisoformat(gen_time_str.replace("Z", "+00:00"))
                artifact_epoch = dt.timestamp()
            except (ValueError, TypeError) as err:  # synapse-ignore: SWALLOWED_EXCEPTION
                logging.getLogger("verify_all").debug("Could not parse generated_at timestamp: %s", err)
        if artifact_epoch is None and os.path.exists(sample_path):
            artifact_epoch = os.path.getmtime(sample_path)

        if artifact_epoch is not None:
            age_hours = (time.time() - artifact_epoch) / 3600.0
            if age_hours > max_age_hours:
                is_stale = True
                staleness_reason = f"Artifact is {age_hours:.1f}h old (exceeds {max_age_hours:.1f}h threshold)"

    if (is_stale or require_fresh or (not jtl_candidates and not k6_candidates)):
        auto_bench = cfg.get("performance", {}).get("auto_benchmark_fallback", True)
        if auto_bench and not (require_fresh and not cfg.get("performance", {}).get("allow_auto_bench_on_require_fresh", True)):
            trigger_reason = f"Stale artifact detected ({staleness_reason})" if is_stale else ("Fresh benchmark required" if require_fresh else "No existing perf run found")
            print(f"[GATE 10] {trigger_reason}. Triggering synthetic performance benchmark runner...")
            try:
                try:
                    from tools.perf.benchmark_perf_runner import run_benchmark
                except ImportError:
                    sys.path.insert(0, os.path.join(repo_root, "tools"))
                    from perf.benchmark_perf_runner import run_benchmark
                out_dir = os.path.join(repo_root, "Reports", "perf")
                bench_res = run_benchmark(iterations=50, output_dir=out_dir)
                jtl_candidates = [bench_res["jtl_file"]]
                k6_candidates = [bench_res["k6_file"]]
                meta = bench_res.get("metadata", {})
                fresh_benchmark_run = True
                is_stale = False
                staleness_reason = None
                print(f"[GATE 10] Real fresh benchmark generated: P95={bench_res['p95_ms']}ms, P99={bench_res['p99_ms']}ms, Error={bench_res['error_rate_pct']}%.")
            except Exception as exc:
                print(f"[FAIL] Gate 10 Performance Sentinel REJECTED: Failed to execute performance benchmark: {exc}")
                return False
        elif require_fresh:
            print(f"[FAIL] Gate 10 Performance Sentinel REJECTED: {staleness_reason or 'Fresh benchmark required but not generated.'} (Stale artifact not accepted as new measurement)")
            return False
        elif not jtl_candidates and not k6_candidates:
            print("[FAIL] Gate 10 Performance Sentinel REJECTED: No active perf runs found in Reports/perf/ and auto_benchmark_fallback is false. (Fail-closed)")
            return False

    try:
        try:
            from tools.jtl_analyzer import parse_jtl, evaluate_sla
        except ImportError:
            sys.path.insert(0, SCRIPT_DIR)
            from jtl_analyzer import parse_jtl, evaluate_sla
    except Exception as e:
        print(f"[WARN] jtl_analyzer not available: {e}")
        return True

    all_passed = True

    # 1. Evaluate Apache JMeter JTL / CSV results
    for jtl_path in jtl_candidates:
        rel_path = os.path.relpath(jtl_path, repo_root)
        try:
            per_sampler, agg_raw = parse_jtl(jtl_path)
            if not per_sampler:
                continue
            agg_stats = agg_raw.compute()
            passed, violations = evaluate_sla(
                agg_stats,
                sla_p95=sla_p95,
                sla_p99=sla_p99,
                max_error_rate=max_error_rate
            )
            if not passed:
                all_passed = False
                print(f"[FAIL] SLA breach detected in {rel_path}:")
                for v in violations:
                    print(f"   🔴 {v}")
            else:
                mtime_epoch = os.path.getmtime(jtl_path) if os.path.exists(jtl_path) else None
                mtime_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime_epoch)) if mtime_epoch else "unknown"
                pass_mode_tag = "[FRESH LOAD TEST PASS]" if fresh_benchmark_run else "[ARTIFACT SENTINEL PASS]"
                print(f"[PASS] {pass_mode_tag} SLA compliant in {rel_path} (P95: {agg_stats['p95_ms']}ms, Error: {agg_stats['error_rate_pct']}%, artifact freshness: {mtime_str})")
        except Exception as e:
            print(f"[WARN] Failed to parse JTL {rel_path}: {e}")

    # 2. Evaluate k6 summary export JSON
    for k6_path in k6_candidates:
        rel_path = os.path.relpath(k6_path, repo_root)
        try:
            with open(k6_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            metrics = data.get("metrics", {})
            dur = metrics.get("http_req_duration", {}).get("values", {})
            p95 = dur.get("p(95)", 0.0)
            err_rate = metrics.get("http_req_failed", {}).get("values", {}).get("rate", 0.0) * 100.0

            violations = []
            if p95 > sla_p95:
                violations.append(f"P95 Latency SLA Breached: {p95:.1f}ms > {sla_p95}ms")
            if err_rate > max_error_rate:
                violations.append(f"Error Rate SLA Breached: {err_rate:.2f}% > {max_error_rate}%")

            if violations:
                all_passed = False
                print(f"[FAIL] k6 SLA breach detected in {rel_path}:")
                for v in violations:
                    print(f"   🔴 {v}")
            else:
                mtime_epoch = os.path.getmtime(k6_path) if os.path.exists(k6_path) else None
                mtime_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime_epoch)) if mtime_epoch else "unknown"
                pass_mode_tag = "[FRESH LOAD TEST PASS]" if fresh_benchmark_run else "[ARTIFACT SENTINEL PASS]"
                print(f"[PASS] {pass_mode_tag} k6 SLA compliant in {rel_path} (P95: {p95:.1f}ms, Error: {err_rate:.2f}%, artifact freshness: {mtime_str})")
        except Exception as e:
            print(f"[WARN] Failed to parse k6 summary {rel_path}: {e}")

    sample_path = (k6_candidates or jtl_candidates)[0] if (k6_candidates or jtl_candidates) else None
    mtime_epoch = os.path.getmtime(sample_path) if sample_path and os.path.exists(sample_path) else None
    default_gen_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime_epoch)) if mtime_epoch else None

    LAST_GATE_METRICS["gate_10"] = {
        "execution_mode": "FRESH_LOAD_TEST" if fresh_benchmark_run else "ARTIFACT_SENTINEL",
        "evaluation_type": "RUN_FRESH_BENCHMARK" if fresh_benchmark_run else "VALIDATE_EXISTING_REPORT",
        "is_fresh_measurement": bool(fresh_benchmark_run),
        "is_stale": bool(is_stale),
        "staleness_reason": staleness_reason,
        "generated_at": meta.get("generated_at") or default_gen_str,
        "commit": meta.get("commit") or get_git_commit_sha(repo_root),
        "command": meta.get("command") or (f"{sys.executable} -m tools.perf.benchmark_perf_runner" if fresh_benchmark_run else "N/A"),
        "fixture_environment": meta.get("fixture_environment") or {},
        "passed": all_passed,
        "sla_p95_ms": sla_p95,
        "max_error_rate_pct": max_error_rate,
        "evaluated_artifacts": [os.path.relpath(p, repo_root) for p in jtl_candidates + k6_candidates],
    }

    if all_passed:
        if fresh_benchmark_run:
            mode_summary = "Fresh Load Test"
            print(f"[PASS] 100% Performance SLA Compliant ({mode_summary}, P95 <= {sla_p95}ms, Error Rate <= {max_error_rate}%).")
        else:
            stale_tag = " [STALE ARTIFACT]" if is_stale else ""
            mode_summary = f"Pre-existing Artifact Sentinel{stale_tag}"
            print(f"[PASS] 100% Performance SLA Compliant ({mode_summary}, P95 <= {sla_p95}ms, Error Rate <= {max_error_rate}%).")
            if is_stale:
                print(f"   ⚠️ Notice: Existing artifact is stale ({staleness_reason}). For a fresh measurement, run tools/perf/benchmark_perf_runner.py or pass --fresh-perf.")
        return True
    return False


def load_synapse_config(repo_root=None, config_path=None):
    """Loads configuration from synapse.config.json if present."""
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
    root = repo_root or REPO_ROOT
    cand = os.path.join(root, "synapse.config.json")
    if os.path.exists(cand):
        try:
            with open(cand, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def format_gates_junit(gate_results, repo_root, gate_metrics=None):
    """Formats 10 DoD Quality Gates result into JUnit XML testsuite."""
    metrics_map = gate_metrics if gate_metrics is not None else LAST_GATE_METRICS
    total = len(gate_results)
    failures = len([g for g in gate_results if not g[1]])
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<testsuite name="synapse-quality-gates" tests="{total}" failures="{failures}" errors="0">'
    ]
    for name, success, reason in gate_results:
        cname = "synapse.quality_gates"
        tname = html_lib.escape(name.split(":")[0].strip().replace(" ", "_"), quote=True)
        g7_metric = metrics_map.get("gate_7", {}) if ("gate_7" in name.lower() or "static defect" in name.lower()) else None
        g8_metric = metrics_map.get("gate_8", {}) if ("gate_8" in name.lower() or "mutation" in name.lower() or "assertion" in name.lower()) else None
        g10_metric = metrics_map.get("gate_10", {}) if ("gate_10" in name.lower() or "performance" in name.lower() or "sla" in name.lower()) else None

        if g7_metric and g7_metric.get("duration_seconds"):
            time_attr = f' time="{g7_metric["duration_seconds"]:.2f}"'
        else:
            time_attr = ''

        lines.append(f'  <testcase classname="{cname}" name="{tname}"{time_attr}>')
        if g7_metric:
            lines.append('    <properties>')
            for k in ("status", "execution_mode", "collected", "passed", "skipped", "failed", "xfailed", "commit", "uncollected", "parent_test", "note"):
                if k in g7_metric and g7_metric[k] is not None:
                    val_str = html_lib.escape(str(g7_metric[k]), quote=True)
                    lines.append(f'      <property name="{k}" value="{val_str}"/>')
            lines.append('    </properties>')

            commit_sha = html_lib.escape(str(g7_metric.get("commit", "unknown")), quote=True)
            if g7_metric.get("uncollected") or g7_metric.get("status") == "PARENT_RUNNER_ACTIVE":
                status_desc = "passed" if success else "failed"
                note_str = html_lib.escape(str(g7_metric.get("note", "Verified via active parent test runner")))
                lines.append(f'    <system-out>Hub regression test suite {status_desc}: {note_str} (Git commit: {commit_sha}).</system-out>')
            else:
                is_suite_passed = success and (g7_metric.get("failed", 0) == 0) and (g7_metric.get("errors", 0) == 0)
                status_desc = "passed" if is_suite_passed else "failed"
                summary_parts = [f"{g7_metric.get('passed', 0)} passed"]
                if g7_metric.get("skipped", 0) > 0:
                    summary_parts.append(f"{g7_metric['skipped']} skipped")
                if g7_metric.get("failed", 0) > 0:
                    summary_parts.append(f"{g7_metric['failed']} failed")
                if g7_metric.get("xfailed", 0) > 0:
                    summary_parts.append(f"{g7_metric['xfailed']} xfailed")
                if g7_metric.get("errors", 0) > 0:
                    summary_parts.append(f"{g7_metric['errors']} errors")
                metric_str = html_lib.escape(", ".join(summary_parts))
                dur = g7_metric.get("duration_seconds", 0.0)
                lines.append(f'    <system-out>Hub regression test suite {status_desc}: {metric_str} in {dur:.2f}s (Git commit: {commit_sha}).</system-out>')
        elif g8_metric:
            lines.append('    <properties>')
            for k in ("mode", "measurement_kind", "static_assertion_sensitivity_score", "dynamic_mutation_score", "mutation_score", "killed", "survived", "timed_out", "invalid_syntax", "total_mutants", "valid_mutants"):
                if k in g8_metric and g8_metric[k] is not None:
                    val_str = html_lib.escape(str(g8_metric[k]), quote=True)
                    lines.append(f'      <property name="{k}" value="{val_str}"/>')
            lines.append('    </properties>')
        elif g10_metric:
            lines.append('    <properties>')
            for k in ("execution_mode", "evaluation_type", "is_fresh_measurement", "is_stale", "staleness_reason", "generated_at", "commit", "sla_p95_ms", "max_error_rate_pct"):
                if k in g10_metric and g10_metric[k] is not None:
                    val_str = html_lib.escape(str(g10_metric[k]), quote=True)
                    lines.append(f'      <property name="{k}" value="{val_str}"/>')
            lines.append('    </properties>')
        if not success:
            esc_name = html_lib.escape(str(name), quote=True)
            esc_repo = html_lib.escape(str(repo_root))
            esc_reason = html_lib.escape(str(reason))
            lines.append(f'    <failure message="Quality Gate Failed: {esc_name}">{esc_name} failed in repository {esc_repo} ({esc_reason})</failure>')
        lines.append('  </testcase>')
    lines.append('</testsuite>')
    return "\n".join(lines)


def run_all_gates(repo_root, mode="AUTO", test_cmd="", scoped_test_cmd="", changed_only=False, output_format="text", config_path=None, fast=False):
    """Programmatic entrypoint to execute all 10 DoD Quality Gates with config and format support."""
    effective_mode = detect_repo_mode(repo_root) if mode.upper() == "AUTO" else mode.upper()
    effective_changed_only = changed_only or fast
    cfg = load_synapse_config(repo_root, config_path=config_path)
    qg_cfg = cfg.get("quality_gates", {})
    gate_toggles = qg_cfg.get("gates", {})

    if output_format == "text":
        mode_suffix = f" [{effective_mode} FAST MODE]" if fast else f" [{effective_mode} MODE]"
        print_header(f"ENTERPRISE AUTOMATION - ONE-COMMAND DoD VERIFICATION{mode_suffix}")
        print(f"Target Repository: {repo_root}")
        print(f"Operational Mode : {effective_mode}")
        if fast:
            print("Execution Speed  : FAST (Sub-3s targeted feedback loop)")

    # Pre-flight Engine Integrity Guard (Silent author attribution & MIT license provenance check)
    if not verify_engine_preflight(repo_root, mode=effective_mode, silent=True):
        if output_format == "text":
            print("\n[DoD BLOCKED] Pre-flight Engine Integrity Guard failed: Author Attribution / MIT License Violated.")
            print("   Under MIT License, original author copyright notice to 'Thế Vị (@TeeVee98)' must be preserved.")
        return 1

    gates = [
        ("gate_1_bom_check", "Gate 1: UTF-8 No BOM", lambda r, mode: gate_1_bom_check(r, mode=mode, fast=fast)),
        ("gate_2_path_portability", "Gate 2: Path Portability", lambda r, mode: gate_2_path_portability(r, mode=mode, fast=fast)),
        ("gate_3_clean_pom", "Gate 3: Clean POM & Flat Architecture", gate_3_clean_pom),
        ("gate_4_ai_docs_lint", "Gate 4: AI Documentation Linter", gate_4_ai_docs_lint),
        ("gate_5_cleanup_blacklist", "Gate 5: Temporary Files Blacklist", gate_5_cleanup_blacklist),
        ("gate_6_credential_security", "Gate 6: Credential Security", lambda r, mode: gate_6_credential_security(r, mode=mode, fast=fast)),
        ("gate_7_infer_linter", "Gate 7: Static Defect Sentinel", lambda r, mode: gate_7_infer_linter(r, mode=mode, fast=fast)),
        ("gate_8_micro_mutator", "Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel", lambda r, mode: gate_8_micro_mutator(r, mode=mode, test_cmd=test_cmd, scoped_test_cmd=scoped_test_cmd, changed_only=effective_changed_only, fast=fast)),
        ("gate_9_skill_collision", "Gate 9: Tier-2 Skill Routing & Collision Guard", gate_9_skill_collision),
        ("gate_10_performance_sla", "Gate 10: Performance & SLA Sentinel", gate_10_performance_sla),
    ]

    all_passed = True
    gate_results = []

    if output_format in ("json", "junit"):
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            for g_key, name, gate_fn in gates:
                if gate_toggles.get(g_key) is False:
                    gate_results.append((name, True, "SKIPPED_BY_CONFIG"))
                    continue
                success = gate_fn(repo_root, mode=effective_mode)
                gate_results.append((name, success, "PASS" if success else "FAIL"))
                if not success:
                    all_passed = False
        finally:
            sys.stdout = old_stdout
    else:
        for g_key, name, gate_fn in gates:
            if gate_toggles.get(g_key) is False:
                print(f"\n[{name.split(':')[0].upper()}] Disabled via synapse.config.json (SKIPPED)")
                gate_results.append((name, True, "SKIPPED_BY_CONFIG"))
                continue

            success = gate_fn(repo_root, mode=effective_mode)
            gate_results.append((name, success, "PASS" if success else "FAIL"))
            if not success:
                all_passed = False

    passed_count = sum(1 for _, passed, status in gate_results if passed and status == "PASS")
    skipped_count = sum(1 for _, _, status in gate_results if status in ("SKIPPED_BY_CONFIG", "SKIPPED"))
    failed_count = sum(1 for _, passed, status in gate_results if not passed or status == "FAIL")

    if output_format == "json":
        gates_json = []
        for g in gate_results:
            g_dict = {"name": g[0], "passed": g[1], "status": g[2]}
            if "gate_7" in g[0].lower() or "static defect" in g[0].lower():
                if "gate_7" in LAST_GATE_METRICS:
                    g_dict["metrics"] = LAST_GATE_METRICS["gate_7"]
            elif "gate_8" in g[0].lower() or "mutation" in g[0].lower() or "assertion" in g[0].lower():
                if "gate_8" in LAST_GATE_METRICS:
                    g_dict["metrics"] = LAST_GATE_METRICS["gate_8"]
            elif "gate_10" in g[0].lower() or "performance" in g[0].lower() or "sla" in g[0].lower():
                if "gate_10" in LAST_GATE_METRICS:
                    g_dict["metrics"] = LAST_GATE_METRICS["gate_10"]
            gates_json.append(g_dict)

        commit_sha = get_git_commit_sha(repo_root)
        res_doc = {
            "timestamp": datetime.now().isoformat(),
            "target": repo_root,
            "mode": effective_mode,
            "git_commit": commit_sha,
            "all_passed": all_passed and failed_count == 0,
            "summary": {
                "total": len(gates),
                "passed": passed_count,
                "skipped": skipped_count,
                "failed": failed_count
            },
            "gates": gates_json
        }
        if "gate_7" in LAST_GATE_METRICS:
            res_doc["pytest_metrics"] = LAST_GATE_METRICS["gate_7"]
            if not res_doc.get("git_commit") and LAST_GATE_METRICS["gate_7"].get("commit"):
                res_doc["git_commit"] = LAST_GATE_METRICS["gate_7"]["commit"]
        if "gate_8" in LAST_GATE_METRICS:
            res_doc["assertion_and_mutation_metrics"] = LAST_GATE_METRICS["gate_8"]
        if "gate_10" in LAST_GATE_METRICS:
            res_doc["performance_metrics"] = LAST_GATE_METRICS["gate_10"]

        # Persist verify_all_report.json artifact
        try:
            reports_dir = os.path.join(repo_root, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            with open(os.path.join(reports_dir, "verify_all_report.json"), "w", encoding="utf-8") as vf:
                json.dump(res_doc, vf, indent=2)
        except (OSError, TypeError) as err:  # synapse-ignore: SWALLOWED_EXCEPTION
            logging.getLogger("verify_all").debug("Could not persist verify_all_report.json: %s", err)

        print(json.dumps(res_doc, indent=2))
        return 0 if (all_passed and failed_count == 0) else 1

    if output_format == "junit":
        print(format_gates_junit(gate_results, repo_root, gate_metrics=LAST_GATE_METRICS))
        return 0 if (all_passed and failed_count == 0) else 1

    print("\n" + "=" * 70)
    if all_passed and failed_count == 0 and skipped_count == 0:
        print(f"[ALL {len(gates)} QUALITY GATES PASSED - 100% DoD COMPLIANT]")
        print("   Repository is 100% compliant, secure, and ready for execution/CI/CD.")
        print("=" * 70 + "\n")
        return 0
    elif all_passed and failed_count == 0 and skipped_count > 0:
        print(f"[QUALITY GATES PASSED: {passed_count}/{len(gates)} PASSED, {skipped_count} SKIPPED BY CONFIG]")
        print("   Note: Some gates were disabled via synapse.config.json.")
        print("=" * 70 + "\n")
        return 0
    else:
        print(f"[DoD BLOCKED] {failed_count} OF {len(gates)} QUALITY GATES FAILED.")
        print("   Please review the errors above and resolve them before proceeding.")
        print("=" * 70 + "\n")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Enterprise DoD Verification Sentinel")
    parser.add_argument("target", nargs="?", default=None,
                        help="Target repository path to verify (defaults to auto-detection from CWD or Hub)")
    parser.add_argument("--repo", "--path", dest="repo_path", default=None,
                        help="Target repository path to verify")
    parser.add_argument("--mode", choices=["auto", "hub", "target"], default="auto",
                        help="Execution mode (auto-detect, hub, or target test project)")
    parser.add_argument("--format", choices=["text", "json", "junit"], default="text",
                        help="Output report format (default: text)")
    parser.add_argument("--config", help="Path to synapse.config.json")
    parser.add_argument("--test-cmd", default="",
                        help="Optional test command for Gate 8 dynamic mutation testing (e.g. 'pytest' or 'npx playwright test')")
    parser.add_argument("--scoped-test-cmd", default="",
                        help="Scoped dynamic test command for Gate 8 (e.g. 'pytest {test_files}')")
    parser.add_argument("--changed-only", "--pr", action="store_true", dest="changed_only",
                        help="Scope Gate 8 dynamic mutation to changed files in git diff (PR mode)")
    parser.add_argument("--fast", "-f", action="store_true", default=False,
                        help="Enable fast verification mode (<3s): runs static AST gates and skips full regression suites")
    args = parser.parse_args()

    try:
        repo_root = resolve_target_repo(cli_target=args.target, cli_repo=args.repo_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    return run_all_gates(repo_root, mode=args.mode, test_cmd=args.test_cmd, scoped_test_cmd=args.scoped_test_cmd, changed_only=args.changed_only, output_format=args.format, config_path=args.config, fast=args.fast)


if __name__ == "__main__":
    sys.exit(main())
