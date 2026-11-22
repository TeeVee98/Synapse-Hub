#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Base abstractions, result models, and shared utilities for DoD Quality Gates.
"""

from abc import ABC, abstractmethod
import ast
import builtins
from dataclasses import dataclass, field
import glob
import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("synapse.gates")

# Enforce UTF-8 stdout encoding and guard against non-blocking stream BlockingIOError
for stream in (sys.stdout, sys.stderr):
    if hasattr(os, "set_blocking") and hasattr(stream, "fileno"):
        try:
            os.set_blocking(stream.fileno(), True)
        except OSError as err:
            logger.debug("Stream set_blocking failed: %s", err)
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", line_buffering=False)
        except (AttributeError, ValueError) as err:
            logger.debug("Stream reconfigure failed: %s", err)


@dataclass
class GateResult:
    """Standardized result data transfer object for quality gate executions."""

    gate_id: int
    name: str
    passed: bool
    status: str = "PASS"  # "PASS", "FAIL", "SKIPPED_BY_CONFIG"
    errors: List[str] = field(default_factory=list)
    duration_sec: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


class BaseGate(ABC):
    """Abstract base class for all Synapse Hub Definition of Done (DoD) Quality Gates."""

    gate_id: int = 0
    name: str = "Base Gate"
    key: str = "base_gate"

    @abstractmethod
    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        """Executes the gate check. Returns True if passed, False otherwise."""
        raise NotImplementedError

    def execute(self, repo_root: str, mode: str = "AUTO", **kwargs) -> GateResult:
        """Runs the gate and returns a structured GateResult with execution duration."""
        start_time = time.time()
        try:
            passed = self.run(repo_root, mode=mode, **kwargs)
            duration = time.time() - start_time
            status = "PASS" if passed else "FAIL"
            metrics = LAST_GATE_METRICS.get(self.key, {})
            return GateResult(
                gate_id=self.gate_id,
                name=self.name,
                passed=passed,
                status=status,
                errors=[] if passed else [f"{self.name} failed"],
                duration_sec=duration,
                metrics=metrics,
            )
        except Exception as exc:
            duration = time.time() - start_time
            logger.error("Exception during execution of %s: %s", self.name, exc, exc_info=True)
            return GateResult(
                gate_id=self.gate_id,
                name=self.name,
                passed=False,
                status="FAIL",
                errors=[str(exc)],
                duration_sec=duration,
                metrics={},
            )


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
            if hasattr(os, "set_blocking") and hasattr(target_stream, "fileno"):
                os.set_blocking(target_stream.fileno(), True)
            target_stream.write(f"{text}\n")
            target_stream.flush()
        except OSError as err:
            logger.debug("safe_print retry failed: %s", err)
    except Exception as exc:
        try:
            sys.stderr.write(f"{text}\n")
        except Exception as err:
            logger.debug("safe_print stderr fallback failed: %s (original: %s)", err, exc)


BOM_EXTENSIONS = (
    ".groovy", ".tc", ".ts", ".glbl", ".md", ".py", ".json", ".ps1",
    ".java", ".yaml", ".yml", ".xml"
)

# Module-level paths
GATES_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.abspath(os.path.join(GATES_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# Module-level telemetry for gate execution metrics (populated during gate runs)
LAST_GATE_METRICS: Dict[str, Any] = {}


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
    except (OSError, subprocess.SubprocessError) as err:
        logger.debug("get_git_commit_sha failed: %s", err)
    return "unknown"


def parse_pytest_metrics(output: str) -> Dict[str, Any]:
    """
    Parses exact pytest execution metrics from command output:
    capturing collected, passed, skipped, failed, xfailed, xpassed, errors, and runtime seconds.
    """
    metrics: Dict[str, Any] = {
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
    output = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", output)

    coll_match = re.search(r"collected\s+(\d+)\s+items?", output)

    # Search for summary line from bottom up
    lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
    summary_line = ""
    for line in reversed(lines):
        line_clean = line.strip("= ").strip()
        # Summary line contains 'in X.XXs' and test outcome status keywords
        if re.search(r"\bin\s+[0-9\.]+s\b", line_clean) and any(
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
        dur_m = re.search(r"in\s+([0-9\.]+)s", summary_line)
        if dur_m:
            metrics["duration_seconds"] = float(dur_m.group(1))

        p_m = re.search(r"\b(\d+)\s+passed\b", summary_line)
        if p_m:
            metrics["passed"] = int(p_m.group(1))

        s_m = re.search(r"\b(\d+)\s+skipped\b", summary_line)
        if s_m:
            metrics["skipped"] = int(s_m.group(1))

        f_m = re.search(r"\b(\d+)\s+failed\b", summary_line)
        if f_m:
            metrics["failed"] = int(f_m.group(1))

        xf_m = re.search(r"\b(\d+)\s+xfailed\b", summary_line)
        if xf_m:
            metrics["xfailed"] = int(xf_m.group(1))

        xp_m = re.search(r"\b(\d+)\s+xpassed\b", summary_line)
        if xp_m:
            metrics["xpassed"] = int(xp_m.group(1))

        err_m = re.search(r"\b(\d+)\s+errors?\b", summary_line)
        if err_m:
            metrics["errors"] = int(err_m.group(1))

        sub_m = re.search(r"\b(\d+)\s+subtests?\s+passed\b", summary_line)
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
    (re.compile(r"file:///[a-zA-Z]:", re.IGNORECASE), "Machine file URI (file:///...)"),
    (re.compile(r"\b[a-zA-Z]:\\Users\\[a-zA-Z0-9_\-]+\\", re.IGNORECASE), "Windows User directory path"),
    (re.compile(r"(?:^|[\s\"'`\(\[\{</])/(?:Users|home)/[a-zA-Z0-9_\-]+/", re.IGNORECASE), "User home directory path"),
    (re.compile(r"\b[a-zA-Z]:[/\\](?:agent-skills|workspace|jenkins|builds)\b", re.IGNORECASE), "Machine-specific repository path"),
    (re.compile(r"[/\\\\]legacy_abs_path[/\\\\]", re.IGNORECASE), "Legacy absolute path reference"),
]


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def detect_repo_mode(repo_root):
    """Detects whether the repository is a QA Hub or a Target Test Suite."""
    # 0. Explicit Environment Override
    env_mode = os.environ.get("SYNAPSE_MODE", "").strip().upper()
    if env_mode in ("CLIENT", "TARGET", "SPOKE"):
        return "TARGET"
    if env_mode == "HUB":
        return "HUB"

    # 0.1 Explicit Config File Override (synapse.config.json)
    cfg = load_synapse_config(repo_root)
    cfg_mode = str(cfg.get("mode", "")).strip().upper()
    if cfg_mode in ("CLIENT", "TARGET", "SPOKE"):
        return "TARGET"
    if cfg_mode == "HUB":
        return "HUB"

    # 1. Target Test Suite Markers (Playwright, Katalon, Cypress, Selenium, Pytest)
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
    has_cypress_project = (
        os.path.exists(os.path.join(repo_root, "cypress.config.ts"))
        or os.path.exists(os.path.join(repo_root, "cypress.config.js"))
        or os.path.isdir(os.path.join(repo_root, "cypress"))
    )

    if has_groovy_tests or has_katalon_project or has_playwright_project or has_cypress_project:
        return "TARGET"

    # 2. Authentic Hub Identification (must have canonical source tools and package identity)
    has_hub_tools = os.path.isfile(os.path.join(repo_root, "tools", "core", "verify_all.py"))
    has_skills_manifest = os.path.isfile(os.path.join(repo_root, "skills_manifest.json"))
    if has_hub_tools and has_skills_manifest:
        return "HUB"

    if os.path.exists(os.path.join(repo_root, "skills_manifest.json")) and not os.path.isdir(os.path.join(repo_root, "tests")):
        return "TARGET"

    if os.path.isdir(os.path.join(repo_root, ".agents", "skills")) and not has_hub_tools:
        # Client project that installed skills locally via npx setup
        return "TARGET"

    if has_hub_tools:
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
    hub_root = REPO_ROOT

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
        sys.path.insert(0, SCRIPT_DIR)
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
    "\u00c3\u00a1",
    "\u00c3\u00a3",
    "\u00c3\u00a9",
    "\u00c3\u00a8",
    "\u00c3\u00b3",
    "\u00c3\u00b2",
    "\ufffd",
    "\u00e2\u20ac\u2014",
    "\u00e2\u20ac\u0153",
    "\u00e2\u20ac\u009d",
)


def get_scoped_git_files(repo_root: str, staged_only: bool = True):
    """
    Retrieves list of scoped files directly from git index for instant verification (<1s).
    If staged_only=True:
      - Reads directly from 'git diff --cached --name-only'.
      - If staged diff is empty (e.g. dev testing before git add), falls back to 'git diff HEAD --name-only'.
    If staged_only=False:
      - Directly reads from 'git diff HEAD --name-only' (captures all working tree + staged changes).
    Returns None if git is unavailable or repo is not a git workspace.
    """
    try:
        if staged_only:
            res = subprocess.run(
                ["git", "-C", repo_root, "diff", "--cached", "--name-only"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0
            )
            if res.returncode == 0:
                staged = [line.strip().replace("\\", "/") for line in res.stdout.splitlines() if line.strip()]
                if staged:
                    return staged

        # Fallback to uncommitted working tree diff vs HEAD
        res_head = subprocess.run(
            ["git", "-C", repo_root, "diff", "HEAD", "--name-only"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5.0
        )
        if res_head.returncode == 0:
            return [line.strip().replace("\\", "/") for line in res_head.stdout.splitlines() if line.strip()]
        return []
    except (OSError, subprocess.SubprocessError):
        return None


def resolve_tool_path(repo_root: str, script_name: str, domain: str = "") -> str:
    """Resolves a tool path checking tools/<domain>/<script_name>, tools/<script_name>, or Hub REPO_ROOT/tools."""
    candidates = []
    if domain:
        candidates.append(os.path.join(repo_root, "tools", domain, script_name))
    candidates.append(os.path.join(repo_root, "tools", script_name))
    candidates.append(os.path.join(SCRIPT_DIR, script_name))
    if domain:
        candidates.append(os.path.join(REPO_ROOT, "tools", domain, script_name))
    candidates.append(os.path.join(REPO_ROOT, "tools", script_name))
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(repo_root, "tools", domain, script_name) if domain else os.path.join(repo_root, "tools", script_name)


def is_page_class_path(file_path: str) -> bool:
    """Return True if the file path indicates a Page Class / Object Repository rather than a test script."""
    if not file_path:
        return False
    fp = file_path.replace("\\", "/").lower()
    if any(p in fp for p in ["/pages/", "pages/", "/page_objects/", "page_objects/", "/object repository/", "/object-repository/"]):
        return True
    base = os.path.basename(fp)
    if base.endswith("page.js") or base.endswith("page.ts") or base.endswith("page.groovy") or base.endswith("page.py") or "basepage" in base:
        return True
    return False


def check_python_ast_integrity(repo_root: str, fast: bool = False) -> List[Tuple[str, int, str]]:
    """
    Performs static AST validation across Python files in the repository.
    Enforces F821 parity (zero undefined variable names) and zero syntax errors.
    Accelerated with Boost B3 AST Pre-Validation Cache and Git Scoped Fast Path.
    """
    builtin_names = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__"}
    py_files = []
    ignored = {".git", "node_modules", "__pycache__", ".venv", "venv", "claude-ecosystem-repos", "build", "dist", ".gradle", "external_repos", "reference_repos", "teamwork", "synapse_hub.egg-info", "agent_qa.egg-info"}

    if fast:
        scoped = get_scoped_git_files(repo_root, staged_only=True)
        if scoped is not None:
            py_files = [
                os.path.join(repo_root, f.replace("/", os.sep))
                for f in scoped
                if f.endswith(".py") and os.path.isfile(os.path.join(repo_root, f.replace("/", os.sep)))
            ]
            if not py_files:
                return []

    if not py_files and not fast:
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored and not d.endswith(".egg-info") and not d.startswith(("synapse_hub-", "synapse-hub-", ".temp-"))]
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))

    violations: List[Tuple[str, int, str]] = []

    # Boost B3: Initialize AST Pre-Validation Cache
    try:
        from ast_cache import get_ast_cache
        cache = get_ast_cache(repo_root)
    except Exception:
        try:
            from tools.context.ast_cache import get_ast_cache
            cache = get_ast_cache(repo_root)
        except Exception:
            try:
                if SCRIPT_DIR not in sys.path:
                    sys.path.insert(0, SCRIPT_DIR)
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
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
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
                    module_names.add(a.asname or a.name.split(".")[0])
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
                if hasattr(ast, "NamedExpr") and isinstance(n, ast.NamedExpr) and isinstance(getattr(n, "target", None), ast.Name):
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
                for case in getattr(node, "cases", []):
                    pattern = getattr(case, "pattern", None)
                    if pattern:
                        for n in ast.walk(pattern):
                            name = getattr(n, "name", None)
                            if isinstance(name, str):
                                self.scopes[-1].add(name)
                            rest = getattr(n, "rest", None)
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
                    self.scopes[-1].add(a.asname or a.name.split(".")[0])

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
                    if node.id.startswith("__") and node.id.endswith("__"):
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


def load_synapse_config(repo_root: Optional[str] = None, config_path: Optional[str] = None) -> Dict[str, Any]:
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


PARALLEL_STATIC_GATE_KEYS: Set[str] = {
    "gate_1_bom_check",
    "gate_2_path_portability",
    "gate_4_ai_docs_lint",
    "gate_5_cleanup_blacklist",
    "gate_6_credential_security",
    "gate_7_infer_linter",
    "gate_9_skill_collision",
}
