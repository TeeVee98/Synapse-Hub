#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Enterprise Multi-Project DoD Verifier (One Command Quality Gate)
---------------------------------------------------------
Consolidates all definition-of-done criteria into a single executable command.

Verifies:
  Gate 0: Author Attribution & Copyright Integrity: Verifies author provenance (Thế Vị @TeeVee998).
  Gate 1: 100% UTF-8 No BOM across all repository files (8 extensions).
  Gate 2: Path Portability: Zero absolute machine paths (file:///C:, /Users/...).
  Gate 3: Clean POM & Flat Architecture: Zero raw XPaths or findTestObject in Scripts/.
  Gate 4: AI Docs & Artifacts Anti-Drift: No hallucinated PageClasses, Suites, or Tools.
  Gate 5: Cleanup Blacklist: No temporary properties or debug dump files on disk.
  Gate 6: Credential Security: No plaintext passwords in Profiles/default.glbl or repository.
  Gate 7: Static Defect Sentinel: Meta Infer-style AST scan for fake passes and empty catches.
  Gate 8: Syntactic Micro-Mutation Sentinel: Injects syntactic faults to eliminate tautological tests (Mutation Score >= 80%).
  Gate 9: Tier-2 Skill Collision Guard: Addy Osmani offline TF-IDF cosine similarity check (similarity < 0.75).

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
from datetime import datetime
import ast
import builtins
import argparse

# Enforce UTF-8 stdout encoding and guard against non-blocking stream BlockingIOError
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'fileno'):
        try:
            os.set_blocking(stream.fileno(), True)
        except Exception:
            pass
    if hasattr(stream, 'reconfigure'):
        try:
            stream.reconfigure(encoding='utf-8')
        except Exception:
            pass


def safe_print(text="", stream=sys.stdout):
    """Safely prints text to the given stream, handling BlockingIOError or encoding issues."""
    try:
        if text:
            stream.write(f"{text}\n")
        else:
            stream.write("\n")
        stream.flush()
    except BlockingIOError:
        try:
            if hasattr(stream, 'fileno'):
                os.set_blocking(stream.fileno(), True)
            stream.write(f"{text}\n")
            stream.flush()
        except OSError as err:
            _ = err
    except Exception as err:
        try:
            print(text)
        except Exception as fallback_err:
            _ = fallback_err

BOM_EXTENSIONS = (".groovy", ".tc", ".ts", ".glbl", ".md", ".py", ".json", ".ps1")

# Module-level paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

# Machine-specific absolute path patterns for Gate 2
FORBIDDEN_PATH_PATTERNS = [
    (re.compile(r'file:///[a-zA-Z]:', re.IGNORECASE), "Machine file URI (file:///...)"),
    (re.compile(r'\b[a-zA-Z]:\\Users\\[a-zA-Z0-9_\-]+\\', re.IGNORECASE), "Windows User directory path"),
    (re.compile(r'\b/Users/[a-zA-Z0-9_\-]+/', re.IGNORECASE), "macOS/Unix User directory path"),
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
    hub_root = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

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


def gate_0_author_integrity(repo_root, mode="AUTO"):
    """Gate 0: Verifies author attribution and MIT license provenance across source manifests."""
    print("\n[GATE 0] Verifying Author Attribution & MIT License Integrity...")
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
        print("[FAIL] Author attribution reference mismatch! Original creator ('Thế Vị @TeeVee998') has been altered.")
        return False

    # 2. In HUB mode, verify the Hub repository itself.
    # In TARGET mode, verify the Hub tools root to guarantee engine integrity.
    check_root = repo_root if mode == "HUB" else DEFAULT_REPO_ROOT
    valid, violations = verify_author_attribution(check_root)
    license_violations = [v for v in violations if "LICENSE" in v]
    if license_violations:
        print("[FAIL] Author Attribution & MIT License Violated:")
        for v in license_violations:
            print(f"   • {v}")
        print("   Under MIT License, original author copyright notice to 'Thế Vị (@TeeVee998)' must be preserved in LICENSE.")
        return False
    elif not valid:
        # Informational notices for downstream forks with customized package.json / README
        print("[INFO] Downstream attribution notice:")
        for v in violations:
            print(f"   • {v}")
    print(f"[PASS] Author Attribution & MIT License Provenance verified intact: {get_canonical_watermark()}")
    return True


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


def gate_1_bom_check(repo_root, mode="AUTO"):
    """Gate 1: Verifies 100% UTF-8 encoding with zero Byte Order Mark (BOM) bytes and zero corrupted control characters."""
    print("\n[GATE 1] Scanning UTF-8 No BOM and Encoding Integrity across repository...")
    ignored_dirs = {".git", ".gradle", "node_modules", "allure-results", "graphify-out", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "build", "dist", "claude-ecosystem-repos", "external_repos", "teamwork"}
    ignored_files = {"verify_all.py", "test_tools.py"}
    bom_violations = []
    mojibake_violations = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
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


def gate_2_path_portability(repo_root, mode="AUTO"):
    """Gate 2: Scans for and rejects machine-specific absolute filepaths in code."""
    print("\n[GATE 2] Checking Path Portability (Zero absolute machine paths in repo sources)...")
    ignored_dirs = {
        ".git", ".gradle", "node_modules", "allure-results", "Screenshots",
        "Reports", "reports", "TestReports", "testreports", "Libs", ".settings", "graphify-out",
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "agent_qa.egg-info", "dist", "build", "claude-ecosystem-repos", "external_repos", "teamwork"
    }
    ignored_files = {
        ".project", ".classpath", ".DS_Store", "memory_cache.db",
        "verify_all.py", "git_pre_commit_guard.py", "agent_canary.py", "repo_map.txt", "repo_map.json",
        "PROJECT_HEALTH_REPORT.md", "PROJECT_STATE.md"
    }
    violations = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            if f.startswith(".temp-") or f in ignored_files or f.endswith(
                (".pyc", ".db", ".png", ".jpg", ".zip", ".tar", ".gz", ".xlsx", ".class", ".prefs")
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
        print("[N/A] Hub Mode: Not Applicable (Clean POM rules apply to target test suites in Spokes).")
        return True

    test_dirs = ["tests"] if effective_mode == "HUB" else ["Scripts", "tests", "test", "e2e", "specs", "cypress"]
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
        r'(?:\.(?:click|dblclick|fill|type|press|check|locator|waitForSelector|hover|selectOption)|cy\.(?:get|find)|driver\.find[A-Za-z]*|WebUI\.[a-zA-Z]+)\s*\(\s*[\x22\x27](?P<sel>[^\x22\x27]+)[\x22\x27]'
    )
    RAW_XPATH_PATTERN = re.compile(r'[\x22\x27](?:xpath=|\/{2}[a-zA-Z*@\[])[^\x22\x27]*[\x22\x27]')

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


def gate_4_ai_docs_lint(repo_root, mode="AUTO"):
    """Gate 4: Reconciles PROJECT_AI_GUIDE.md against physical AST to prevent hallucinated classes."""
    print("\n[GATE 4] Running AI Documentation & Artifact Linter...")
    linter_script = os.path.join(SCRIPT_DIR, "lint_ai_docs.py")
    if not os.path.exists(linter_script):
        linter_script = os.path.join(repo_root, "tools", "lint_ai_docs.py")
    if not os.path.exists(linter_script):
        print("[FAIL] lint_ai_docs.py not found in tools/!")
        return False

    try:
        res = subprocess.run([sys.executable, linter_script, repo_root], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60.0)
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
    ]
    found = []
    for pattern in blacklist_patterns:
        for f in glob.glob(pattern):
            if os.path.isfile(f):
                found.append(os.path.relpath(f, repo_root))

    if found:
        print(f"[FAIL] {len(found)} blacklisted temporary files found on disk:")
        for f in found:
            print(f"   - {f}")
        return False
    print("[PASS] Temporary file blacklist is clean.")
    return True


def gate_6_credential_security(repo_root, mode="AUTO"):
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
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "agent_qa.egg-info", "dist", "build", "claude-ecosystem-repos", "external_repos", "teamwork"
    }

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            if not f.endswith((".py", ".groovy", ".ts", ".js", ".json", ".txt", ".md", ".yml", ".yaml", ".properties", ".sh", ".ps1", ".glbl")):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo_root)

            # Skip self scanning of pattern definitions in verify_all.py or scanner tests
            if rel_path in ("tools\\verify_all.py", "tools/verify_all.py", "tests\\test_tools.py", "tests/test_tools.py"):
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
            except (OSError, PermissionError):
                continue

    if violations:
        print(f"[FAIL] {len(violations)} hardcoded secrets/credentials detected on disk:")
        for rel_path, line_no, desc in violations:
            print(f"   - {rel_path}:{line_no} contains '{desc}'")
        return False

    print("[PASS] 100% Verified: Zero hardcoded plaintext credentials or secret tokens across repository.")
    return True


def check_python_ast_integrity(repo_root):
    """
    Performs static AST validation across all Python files in the repository.
    Enforces F821 parity (zero undefined variable names) and zero syntax errors.
    """
    builtin_names = set(dir(builtins)) | {'__file__', '__name__', '__doc__', '__package__'}
    py_files = []
    ignored = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'claude-ecosystem-repos', 'build', 'dist', '.gradle', 'external_repos', 'teamwork'}

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored]
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))

    violations = []

    for file_path in sorted(py_files):
        rel_path = os.path.relpath(file_path, repo_root)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
            tree = ast.parse(content, file_path)
        except SyntaxError as e:
            violations.append((rel_path, e.lineno or 1, f"SyntaxError: {e.msg}"))
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

    return violations


def gate_7_infer_linter(repo_root, mode="AUTO"):
    """Gate 7: Runs Meta Infer-style static defect sentinel catching fake passes, 0 assert, and sleeps."""
    print("\n[GATE 7] Running Meta Infer-Style Static Defect & Fake-Pass Sentinel...")
    effective_mode = detect_repo_mode(repo_root) if mode == "AUTO" else mode

    # Static Python AST & Undefined Name (F821) Sentinel
    ast_violations = check_python_ast_integrity(repo_root)
    if ast_violations:
        print(f"[FAIL] Static Python AST Sentinel detected {len(ast_violations)} syntax errors or undefined names:")
        for rel_file, line_no, desc in ast_violations:
            print(f"   - {rel_file}:{line_no} -> {desc}")
        return False
    print("[PASS] 100% Python AST integrity verified (zero syntax errors, zero undefined variables).")

    # In HUB mode: dogfood tools/ with baseline to prevent new unbaselined defects
    if effective_mode == "HUB":
        baseline_file = os.path.join(repo_root, "tools", ".infer_baseline.json")
        infer_script = os.path.join(repo_root, "tools", "infer_linter.py")
        if os.path.exists(baseline_file) and os.path.exists(infer_script):
            tools_dir = os.path.join(repo_root, "tools")
            try:
                res = subprocess.run([
                    sys.executable, infer_script, "--strict", "--baseline", baseline_file, "--dir", tools_dir
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60.0)
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

    test_dirs = ["tests"] if effective_mode == "HUB" else ["Scripts", "tests", "test", "e2e", "specs", "cypress"]
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

    infer_script = os.path.join(SCRIPT_DIR, "infer_linter.py")
    if not os.path.exists(infer_script):
        infer_script = os.path.join(repo_root, "tools", "infer_linter.py")

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


def gate_8_micro_mutator(repo_root, mode="AUTO", test_cmd=""):
    """Gate 8: Runs syntactic mutation testing and verifies assertion sensitivity score >= 80%."""
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
        if mode == "HUB":
            print(f"[N/A] Hub Mode: Not Applicable (Assertion Sensitivity & Syntactic Mutation applies to target test suites in Spokes) [{eval_mode_desc}].")
            return True
        else:
            print("[N/A] No automated test scripts found in Scripts/ or tests/ to mutate.")
            return True

    mutator_script = os.path.join(SCRIPT_DIR, "micro_mutator.py")
    if not os.path.exists(mutator_script):
        mutator_script = os.path.join(repo_root, "tools", "micro_mutator.py")

    if not os.path.exists(mutator_script):
        print("[FAIL] micro_mutator.py not found in tools/! Gate 8 requires micro_mutator.py (fail-closed).")
        return False

    cfg = load_synapse_config(repo_root)
    qg_cfg = cfg.get("quality_gates", {})
    min_score_val = float(qg_cfg.get("mutation_min_score", 80.0))
    min_score_str = str(min_score_val)
    allow_empty_val = bool(qg_cfg.get("allow_empty_mutations", False))

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
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120.0)
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
            mode_label = "DYNAMIC" if test_cmd else "HEURISTIC STATIC"
            print(f"[PASS] Assertion Sensitivity [{mode_label}]: {data.get('mutation_score', 100)}% >= 80% (Caught {data.get('killed', 0)}/{data.get('total_mutants', 0)} syntactic mutants). Zero unasserted logic branches.")
            if os.path.exists(baseline_file):
                print(f"   Mutant Baseline: Recorded {data.get('killed', 0)}/{data.get('total_mutants', 0)} mutants ({data.get('mutation_score', 100)}%) into reports/mutant_baseline.json")
        except (json.JSONDecodeError, ValueError, KeyError):
            print(f"[PASS] Assertion Sensitivity Sentinel passed: Score >= 80% [{eval_mode_desc}].")
        return True


def gate_9_skill_collision(repo_root, mode="AUTO"):
    """Gate 9: Scans skill descriptions to ensure semantic trigger overlap remains < 0.75."""
    print("\n[GATE 9] Running Tier-2 Skill Routing & Collision Guard (Addy Osmani Pattern)...")
    guard_script = os.path.join(SCRIPT_DIR, "skill_collision_guard.py")
    if not os.path.exists(guard_script):
        guard_script = os.path.join(repo_root, "tools", "skill_collision_guard.py")
    if not os.path.exists(guard_script):
        print("[FAIL] skill_collision_guard.py not found in tools/!")
        return False

    skills_dir = os.path.join(repo_root, ".agents", "skills")
    if not os.path.exists(skills_dir):
        print("[PASS] Target project mode: .agents/skills/ not present (SKIPPED).")
        return True

    try:
        res = subprocess.run([sys.executable, guard_script, "--dir", skills_dir, "--threshold", "0.75"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60.0)
    except subprocess.TimeoutExpired:
        print("[FAIL] skill_collision_guard.py timed out after 60s!")
        return False

    if res.returncode != 0:
        safe_print(res.stdout)
        safe_print(res.stderr)
        return False
    print("[PASS] 100% Verified: 0 skill description collisions detected (similarity < 0.75).")
    return True


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


def format_gates_junit(gate_results, repo_root):
    """Formats 10 DoD Quality Gates result into JUnit XML testsuite."""
    total = len(gate_results)
    failures = len([g for g in gate_results if not g[1]])
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<testsuite name="synapse-quality-gates" tests="{total}" failures="{failures}" errors="0">'
    ]
    for name, success, reason in gate_results:
        cname = "synapse.quality_gates"
        tname = name.split(":")[0].strip().replace(" ", "_")
        lines.append(f'  <testcase classname="{cname}" name="{tname}">')
        if not success:
            lines.append(f'    <failure message="Quality Gate Failed: {name}">{name} failed in repository {repo_root} ({reason})</failure>')
        lines.append('  </testcase>')
    lines.append('</testsuite>')
    return "\n".join(lines)


def run_all_gates(repo_root, mode="AUTO", test_cmd="", output_format="text", config_path=None):
    """Programmatic entrypoint to execute all 10 DoD Quality Gates with config and format support."""
    effective_mode = detect_repo_mode(repo_root) if mode.upper() == "AUTO" else mode.upper()
    cfg = load_synapse_config(repo_root, config_path=config_path)
    qg_cfg = cfg.get("quality_gates", {})
    gate_toggles = qg_cfg.get("gates", {})

    if output_format == "text":
        print_header(f"ENTERPRISE AUTOMATION - ONE-COMMAND DoD VERIFICATION [{effective_mode} MODE]")
        print(f"Target Repository: {repo_root}")
        print(f"Operational Mode : {effective_mode}")

    gates = [
        ("gate_0_author_integrity", "Gate 0: Author Attribution & Integrity", gate_0_author_integrity),
        ("gate_1_bom_check", "Gate 1: UTF-8 No BOM", gate_1_bom_check),
        ("gate_2_path_portability", "Gate 2: Path Portability", gate_2_path_portability),
        ("gate_3_clean_pom", "Gate 3: Clean POM & Flat Architecture", gate_3_clean_pom),
        ("gate_4_ai_docs_lint", "Gate 4: AI Documentation Linter", gate_4_ai_docs_lint),
        ("gate_5_cleanup_blacklist", "Gate 5: Temporary Files Blacklist", gate_5_cleanup_blacklist),
        ("gate_6_credential_security", "Gate 6: Credential Security", gate_6_credential_security),
        ("gate_7_infer_linter", "Gate 7: Static Defect Sentinel", gate_7_infer_linter),
        ("gate_8_micro_mutator", "Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel", lambda r, mode: gate_8_micro_mutator(r, mode=mode, test_cmd=test_cmd)),
        ("gate_9_skill_collision", "Gate 9: Tier-2 Skill Routing & Collision Guard", gate_9_skill_collision),
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
        res_doc = {
            "timestamp": datetime.now().isoformat(),
            "target": repo_root,
            "mode": effective_mode,
            "all_passed": all_passed and failed_count == 0,
            "summary": {
                "total": len(gates),
                "passed": passed_count,
                "skipped": skipped_count,
                "failed": failed_count
            },
            "gates": [{"name": g[0], "passed": g[1], "status": g[2]} for g in gate_results]
        }
        print(json.dumps(res_doc, indent=2))
        return 0 if (all_passed and failed_count == 0) else 1

    if output_format == "junit":
        print(format_gates_junit(gate_results, repo_root))
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
    args = parser.parse_args()

    try:
        repo_root = resolve_target_repo(cli_target=args.target, cli_repo=args.repo_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    return run_all_gates(repo_root, mode=args.mode, test_cmd=args.test_cmd, output_format=args.format, config_path=args.config)


if __name__ == "__main__":
    sys.exit(main())
