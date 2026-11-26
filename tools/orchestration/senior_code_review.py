#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/senior_code_review.py — Senior Developer Quality & Lean Diff Reviewer
--------------------------------------------------------------------------
Reviews code changes (uncommitted, staged, or branch) like the senior engineer
who gets paged when it breaks:
  1. Bugs & Edge Cases (swallowed errors, broken callers, null/edge handling)
  2. Security & Data Risk (secrets, injection, unvalidated trust boundaries)
  3. Scale & Concurrency (blocking calls, race conditions, memory growth)
  4. Missing Tests (new non-trivial logic without assertions)
  5. Performance & Hot-loops
  6. Lean Code & Bloat (unneeded dependencies, duplicate logic, over-engineering)

Usage:
  python3 tools/senior_code_review.py [target_dir]
  python3 tools/senior_code_review.py [target_dir] --staged
  python3 tools/senior_code_review.py [target_dir] --branch main
  python3 tools/senior_code_review.py [target_dir] --json
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import ast
import os
import sys
import re
import json
import subprocess
import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Set

from tools.lint.output_diff_sentinel import OutputDiffSentinel
from tools.ai.cove_verifier import ChainOfVerificationEngine
from tools.lint.humanize_linter import HumanizeLinter
from tools.orchestration.solo_contracts import AstTautologyAnalyzer
from tools.orchestration.plan_review_auditor import (
    CallerCompatibilityDTO,
    PlanReconciliationDTO,
    SoloProvenanceAuditDTO,
    UnifiedReviewReceiptDTO,
    _audit_callers_and_cycles,
    audit_plan_and_solo_execution,
    compute_review_verdict,
    sign_and_write_review_receipt,
)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


class Finding:
    def __init__(self, severity: str, title: str, file_path: str, line_no: int,
                 what_is: str, problem: str, fix: str, if_skipped: str):
        self.severity = severity  # "Must fix", "Should fix", "Nice to have"
        self.title = title
        self.file_path = file_path
        self.line_no = line_no
        self.what_is = what_is
        self.problem = problem
        self.fix = fix
        self.if_skipped = if_skipped

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "title": self.title,
            "file": self.file_path,
            "line": self.line_no,
            "what_is": self.what_is,
            "problem": self.problem,
            "fix": self.fix,
            "if_skipped": self.if_skipped
        }


def get_git_diff(repo_dir: str, target: str = "uncommitted") -> str:
    """Retrieves git diff based on target: uncommitted (HEAD), staged, or branch/ref."""
    cmd = ["git", "diff", "HEAD"]
    if target == "staged":
        cmd = ["git", "diff", "--cached"]
    elif target != "uncommitted":
        cmd = ["git", "diff", target]

    # Verify target directory is a valid git repository
    try:
        check_repo = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5.0
        )
        if check_repo.returncode != 0:
            sys.stderr.write(f"[SENIOR-REVIEW] Notice: '{repo_dir}' is not a git repository. Review skipped.\n")
            return ""
    except Exception as e:
        sys.stderr.write(f"[SENIOR-REVIEW] Git check failed: {e}\n")
        return ""

    try:
        res = subprocess.run(
            cmd,
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
            timeout=30.0
        )
        if res.returncode != 0:
            err_msg = res.stderr.strip() or f"git diff exited with return code {res.returncode}"
            sys.stderr.write(f"[SENIOR-REVIEW] Error running git diff: {err_msg}\n")
            raise RuntimeError(f"git diff failed: {err_msg}")
        return res.stdout
    except subprocess.TimeoutExpired as te:
        sys.stderr.write(f"[SENIOR-REVIEW] Git diff timed out after 30s: {te}\n")
        raise RuntimeError(f"git diff timed out: {te}")
    except Exception as e:
        sys.stderr.write(f"[SENIOR-REVIEW] Git diff error: {e}\n")
        raise


def parse_diff(diff_text: str) -> List[Dict[str, Any]]:
    """Parses unified diff output into file hunks and added lines."""
    files: List[Dict[str, Any]] = []
    current_file = None
    current_hunk_line = 0

    file_header_re = re.compile(r'^diff --git a/(.+) b/(.+)$')
    hunk_header_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@')

    for line in diff_text.splitlines():
        fm = file_header_re.match(line)
        if fm:
            current_file = {
                "path": fm.group(2),
                "added_lines": [],  # (line_no, line_content)
                "removed_lines": []
            }
            files.append(current_file)
            continue

        if not current_file:
            continue

        hm = hunk_header_re.match(line)
        if hm:
            current_hunk_line = int(hm.group(1))
            continue

        if line.startswith("+") and not line.startswith("+++"):
            current_file["added_lines"].append((current_hunk_line, line[1:]))
            current_hunk_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            current_file["removed_lines"].append(line[1:])
        else:
            current_hunk_line += 1

    return files


_NESTING_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)


def _is_swallowed_handler_body(body: List[ast.stmt]) -> bool:
    if not body:
        return False
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
            continue
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and stmt.targets[0].id == "_"
        ):
            continue
        return False
    return True


def _is_mutable_default(node: Optional[ast.AST]) -> bool:
    if node is None:
        return False
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("list", "dict", "set"):
        return True
    return False


def _is_time_time_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "time"
        and node.func.attr == "time"
        and not node.args
    )


def _max_control_nesting(node: ast.AST, depth: int = 0) -> Tuple[int, int]:
    """Returns (max_depth, deepest_lineno) of control-flow nesting inside node."""
    best_depth = depth
    best_line = getattr(node, "lineno", 1)
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        child_depth = depth + 1 if isinstance(child, _NESTING_NODES) else depth
        sub_depth, sub_line = _max_control_nesting(child, child_depth)
        if sub_depth > best_depth:
            best_depth = sub_depth
            best_line = sub_line
    return best_depth, best_line


def _check_ast_except_handler(
    node: ast.ExceptHandler,
    path: str,
    mapped_line: int,
    raw_line: str,
    existing_swallowed_lines: Set[Tuple[str, int]],
) -> Optional[Finding]:
    if "synapse-ignore: SWALLOWED_EXCEPTION" in raw_line:
        return None
    if not _is_swallowed_handler_body(node.body) or (path, mapped_line) in existing_swallowed_lines:
        return None
    existing_swallowed_lines.add((path, mapped_line))
    return Finding(
        severity="Must fix",
        title="Swallowed exception / empty catch block (multi-line AST)",
        file_path=path,
        line_no=mapped_line,
        what_is="A multi-line except handler that silently suppresses exceptions.",
        problem="Silent failures hide root causes and corrupt downstream state.",
        fix="Log the exception with context or re-raise a specific domain error.",
        if_skipped="Failures vanish silently in production and CI.",
    )


def _check_ast_function_def(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    path: str,
    mapped_line: int,
    map_line_fn: Any,
) -> List[Finding]:
    found: List[Finding] = []
    defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
    if any(_is_mutable_default(d) for d in defaults):
        found.append(
            Finding(
                severity="Must fix",
                title=f"Mutable default argument in function '{node.name}'",
                file_path=path,
                line_no=mapped_line,
                what_is=f"Function '{node.name}' uses a mutable list/dict/set literal as a default argument.",
                problem="Mutable defaults are shared across invocations, causing cross-call state corruption.",
                fix="Default to None and initialize the collection inside the function body.",
                if_skipped="Intermittent state leakage bugs across calls and test runs.",
            )
        )
    max_depth, deep_line = _max_control_nesting(node)
    if max_depth > 4:
        found.append(
            Finding(
                severity="Should fix",
                title=f"Deep nesting ({max_depth} levels) in '{node.name}' (simplify)",
                file_path=path,
                line_no=map_line_fn(deep_line),
                what_is=f"Function '{node.name}' nests control-flow blocks {max_depth} levels deep (> 4).",
                problem="Deeply nested branches increase cognitive load and hide edge-case bugs.",
                fix="Flatten with early-return guard clauses or extract a focused helper.",
                if_skipped="Maintenance complexity and branch bugs accumulate.",
            )
        )
    return found


def _check_ast_call_and_clock(
    node: ast.AST,
    path: str,
    mapped_line: int,
    is_test_file: bool,
) -> Optional[Finding]:
    if isinstance(node, ast.Call) and not is_test_file:
        is_shell_true = any(
            kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords
        )
        if is_shell_true:
            return Finding(
                severity="Must fix",
                title="Dangerous subprocess call with shell=True",
                file_path=path,
                line_no=mapped_line,
                what_is="A subprocess invocation with shell=True enabled.",
                problem="Passing untrusted input to a shell enables OS command injection.",
                fix="Pass an explicit argv list with shell=False (default).",
                if_skipped="Command injection vulnerability on untrusted inputs.",
            )
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            return Finding(
                severity="Must fix",
                title=f"Dynamic code execution via {node.func.id}()",
                file_path=path,
                line_no=mapped_line,
                what_is=f"Call to Python builtin {node.func.id}() in production code.",
                problem="Arbitrary code execution breaks security trust boundaries.",
                fix="Replace with ast.literal_eval(), explicit dispatch maps, or structured parsers.",
                if_skipped="Remote/local code execution exposure.",
            )
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Sub, ast.Add)):
        if _is_time_time_call(node.left) or _is_time_time_call(node.right):
            return Finding(
                severity="Should fix",
                title="Non-monotonic wall-clock time.time() used for duration/timeout",
                file_path=path,
                line_no=mapped_line,
                what_is="Arithmetic on time.time() for elapsed duration or timeout deadline.",
                problem="Wall-clock time can jump backwards on NTP/DST sync, causing timeout bugs.",
                fix="Use time.monotonic() or time.perf_counter() for elapsed durations and deadlines.",
                if_skipped="Timeouts can hang or expire prematurely during clock adjustments.",
            )
    return None


def _python_string_literal_lines(abs_path: str) -> Set[int]:
    """Returns 1-based line numbers inside multi-line Python string literals on disk."""
    if not os.path.isfile(abs_path):
        return set()
    try:
        tree = ast.parse(Path(abs_path).read_text(encoding="utf-8", errors="replace"), filename=abs_path)
    except (OSError, SyntaxError):
        return set()
    lit_lines: Set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            start = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", start) or start
            if end > start:
                lit_lines.update(range(start, end + 1))
    return lit_lines


def _analyze_python_ast_added(
    path: str,
    added_lines: List[Tuple[int, str]],
    repo_dir: str,
    existing_swallowed_lines: Set[Tuple[str, int]],
) -> List[Finding]:
    """Runs AST-backed multi-line anti-pattern and 4-Angle simplify checks on added Python code."""
    if not added_lines:
        return []

    abs_path = os.path.join(repo_dir, path)
    added_line_nums: Set[int] = {ln for ln, _ in added_lines}
    line_lookup: Optional[List[int]] = None
    source_lines: List[str] = []

    if os.path.isfile(abs_path):
        try:
            source = Path(abs_path).read_text(encoding="utf-8", errors="replace")
            source_lines = source.splitlines()
            tree = ast.parse(source, filename=path)
        except (OSError, SyntaxError):
            return []
    else:
        snippet = "\n".join(txt for _, txt in added_lines)
        source_lines = [txt for _, txt in added_lines]
        line_lookup = [ln for ln, _ in added_lines]
        try:
            tree = ast.parse(snippet, filename=path)
        except SyntaxError:
            return []

    def _map_line(ast_lineno: int) -> int:
        if line_lookup is not None and 1 <= ast_lineno <= len(line_lookup):
            return line_lookup[ast_lineno - 1]
        return ast_lineno

    def _is_added(ast_lineno: int) -> bool:
        return True if line_lookup is not None else ast_lineno in added_line_nums

    ast_findings: List[Finding] = []
    path_lower = path.lower()
    is_test_file = (
        "test" in os.path.basename(path_lower)
        or path_lower.startswith("tests/")
        or "/tests/" in path_lower
    )

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", 0)
        if not lineno or not _is_added(lineno):
            continue
        mapped_line = _map_line(lineno)
        raw_line = source_lines[lineno - 1] if 1 <= lineno <= len(source_lines) else ""

        if isinstance(node, ast.ExceptHandler):
            finding = _check_ast_except_handler(node, path, mapped_line, raw_line, existing_swallowed_lines)
            if finding is not None:
                ast_findings.append(finding)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ast_findings.extend(_check_ast_function_def(node, path, mapped_line, _map_line))
        else:
            finding = _check_ast_call_and_clock(node, path, mapped_line, is_test_file)
            if finding is not None:
                ast_findings.append(finding)

    if is_test_file:
        src_for_taut = "\n".join(source_lines)
        for t_line, stmt_str, reason in AstTautologyAnalyzer().analyze_source(src_for_taut):
            if _is_added(t_line):
                ast_findings.append(
                    Finding(
                        severity="Must fix",
                        title="Tautological test assertion detected (Truth Anchor violation)",
                        file_path=path,
                        line_no=_map_line(t_line),
                        what_is=f"Assertion '{stmt_str}' is statically tautological ({reason}).",
                        problem="Tautological assertions create fake passes or forced failures unrelated to behavior.",
                        fix="Assert real domain outputs produced by the code under test.",
                        if_skipped="Test suite provides false confidence and violates Invariant 2.",
                    )
                )

    return ast_findings


def analyze_diff(files: List[Dict[str, Any]], repo_dir: str) -> Tuple[List[Finding], int]:
    """Inspects diff files against senior dev 6-pillar AST & 4-angle simplify heuristics."""
    findings: List[Finding] = []
    lines_cuttable = 0

    has_new_test = False
    has_new_business_code = False

    # Check overall changes for test balance
    for f in files:
        path = f["path"]
        if "test" in path.lower() or "spec" in path.lower():
            if f["added_lines"]:
                has_new_test = True
        else:
            ext = os.path.splitext(path)[1].lower()
            if ext in {".py", ".ts", ".js", ".java", ".groovy", ".go", ".rs"}:
                if len(f["added_lines"]) > 5:
                    has_new_business_code = True

    # Rule checks on added lines
    secret_pattern = re.compile(r'(?:api[_-]?key|password|secret|bearer|token)\s*=\s*[\'"][A-Za-z0-9_\-\.]{8,}[\'"]', re.I)
    swallowed_catch_py = re.compile(r'except\s*(?:Exception)?\s*:\s*(?:pass|\.\.\.)')
    swallowed_catch_js = re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}')
    static_sleep_pattern = re.compile(r'\b(?:Thread\.sleep|time\.sleep|sleep)\s*\(')
    raw_xpath_pattern = re.compile(r'findTestObject|\.locator\(["\']//|\.locator\(["\']xpath=')
    swallowed_lines_seen: Set[Tuple[str, int]] = set()
    humanizer = HumanizeLinter(check_pileup=False)

    for f in files:
        path = f["path"]
        path_lower = path.lower()
        is_code_file = any(path_lower.endswith(ext) for ext in (".py", ".ts", ".js", ".java", ".groovy", ".cs", ".sh", ".ps1", ".mjs", ".cjs"))
        py_lit_lines = _python_string_literal_lines(os.path.join(repo_dir, path)) if path_lower.endswith(".py") else set()
        for line_no, content in f["added_lines"]:
            if line_no in py_lit_lines:
                continue
            stripped = content.strip()

            # 1. Security: Hardcoded Credentials
            if secret_pattern.search(stripped) and "test" not in path_lower:
                findings.append(Finding(
                    severity="Must fix",
                    title="Potential hardcoded secret or token detected",
                    file_path=path,
                    line_no=line_no,
                    what_is="A secret or token literal assignment in source code.",
                    problem="Exposing credentials in source control allows unauthorized access and fails security scans.",
                    fix="Extract the secret to an environment variable or encrypted profile config.",
                    if_skipped="Credentials risk leaking to version control and security audits will fail."
                ))

            # 2. Correctness: Swallowed Exceptions (single-line)
            if is_code_file and "synapse-ignore: SWALLOWED_EXCEPTION" not in stripped and (swallowed_catch_py.search(stripped) or swallowed_catch_js.search(stripped)):
                swallowed_lines_seen.add((path, line_no))
                findings.append(Finding(
                    severity="Must fix",
                    title="Swallowed exception / empty catch block",
                    file_path=path,
                    line_no=line_no,
                    what_is="An exception catch block that suppresses errors without logging or handling.",
                    problem="Silent failures hide root causes, corrupt downstream state, and lead to mysterious bugs in production.",
                    fix="Log the exception with actionable context or rethrow a domain-specific error.",
                    if_skipped="Failures will be completely invisible and impossible to debug under load."
                ))

            # 3. Flakiness / Concurrency: Static Sleep (exclude rule docs/backtick examples like `Thread.sleep(...)`)
            if is_code_file and static_sleep_pattern.search(stripped) and "`Thread.sleep" not in stripped and "`time.sleep" not in stripped:
                findings.append(Finding(
                    severity="Should fix",
                    title="Static sleep detected (pipeline flakiness risk)",
                    file_path=path,
                    line_no=line_no,
                    what_is="A static Thread.sleep or time.sleep delay in execution flow.",
                    problem="Static delays waste CI time under fast networks and fail randomly under heavy load.",
                    fix="Replace with a dynamic wait: element visibility check, network idle state, or condition polling.",
                    if_skipped="Test runs will suffer non-deterministic flakiness and slower CI turnaround."
                ))

            # 4. Clean POM Architecture: Raw locators in scripts
            if is_code_file and ("script" in path_lower or "tests" in path_lower):
                if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("/*") or stripped.startswith("*"):
                    continue
                if raw_xpath_pattern.search(stripped):
                    findings.append(Finding(
                    severity="Should fix",
                    title="Raw selector or object reference inside test script",
                    file_path=path,
                    line_no=line_no,
                    what_is="A raw XPath or direct object call inside a high-level test script.",
                    problem="Violates Clean POM / Flat Architecture separation of concerns; UI changes break scripts directly.",
                    fix="Encapsulate this locator and interaction inside a Page Class extending BasePage.",
                    if_skipped="Any DOM markup change requires updating multiple scripts instead of a single Page Class."
                ))

            # 5. Lean: Commented-out dead code blocks
            if (stripped.startswith("//") or stripped.startswith("#")) and len(stripped) > 20:
                if re.match(r'^(?://|#)\s*(?:const|let|var|def|function|class|import|return)\b', stripped):
                    lines_cuttable += 1
                    findings.append(Finding(
                        severity="Nice to have",
                        title="Commented-out dead code block",
                        file_path=path,
                        line_no=line_no,
                        what_is="A commented-out code statement left in the diff.",
                        problem="Dead code creates visual clutter, confuses future maintainers, and rots over time.",
                        fix="Delete the commented code. Git history preserves past implementations.",
                        if_skipped="Technical debt and confusion will accumulate across commits."
                    ))

            # 6. Flakiness: Raw setTimeout in test code (Next.js & Codex Invariant)
            if is_code_file and ("test" in path_lower or "spec" in path_lower):
                if re.search(r'\bsetTimeout\s*\(', stripped) and not (stripped.startswith("//") or stripped.startswith("#")):
                    findings.append(Finding(
                        severity="Should fix",
                        title="Raw setTimeout detected in test (Next.js / Codex Invariant)",
                        file_path=path,
                        line_no=line_no,
                        what_is="A raw setTimeout delay used in test code.",
                        problem="Fixed time delays cause non-deterministic test race conditions and CI flakiness.",
                        fix="Replace with explicit retry() / waitForCondition() polling on observable state.",
                        if_skipped="Test suite will become flaky under variable runner and network loads."
                    ))

        # 7. Deep Python AST anti-pattern & 4-Angle simplify inspection
        if path_lower.endswith(".py") and f["added_lines"]:
            findings.extend(_analyze_python_ast_added(path, f["added_lines"], repo_dir, swallowed_lines_seen))

        # 8. Optional AI-slop / humanize check on added markdown prose (bounded)
        if path_lower.endswith(".md") and f["added_lines"]:
            added_md = "\n".join(content for _, content in f["added_lines"])
            slop_issues = [i for i in humanizer.lint_text(added_md, source_label=path) if i.issue_type in ("buzzword", "cliche")]
            for issue in slop_issues[:3]:
                idx = min(max(issue.line_number - 1, 0), len(f["added_lines"]) - 1)
                real_ln = f["added_lines"][idx][0]
                findings.append(Finding(
                    severity="Nice to have",
                    title=f"AI writing slop detected ('{issue.matched_text}')",
                    file_path=path,
                    line_no=real_ln,
                    what_is=f"Stock AI {issue.issue_type} '{issue.matched_text}' in added Markdown text.",
                    problem="Robotic filler weakens technical clarity.",
                    fix=f"Rewrite plainly: {issue.suggestion}.",
                    if_skipped="Documentation retains noisy AI-sounding phrasing.",
                ))

    # 9. Completeness: Non-trivial logic without any test
    if has_new_business_code and not has_new_test:
        findings.append(Finding(
            severity="Should fix",
            title="Non-trivial business code added without accompanying tests",
            file_path="[Multiple files]",
            line_no=1,
            what_is="Substantial new implementation code with zero test additions or updates.",
            problem="Risky logic ships unverified; regressions will not be caught automatically by CI.",
            fix="Add at least one targeted unit or integration test proving this logic works on edge cases.",
            if_skipped="Future refactoring risks breaking this behavior silently."
        ))

    return findings, lines_cuttable


def audit_diff_bloat(repo_dir: str) -> Dict[str, Any]:
    """Audits repository diff for monolithic rewrite waste via OutputDiffSentinel."""
    try:
        passed, raw_violations = OutputDiffSentinel.audit_git_diff(repo_dir)
    except Exception as err:
        sys.stderr.write(f"[SENIOR-REVIEW] OutputDiffSentinel audit failed: {err}\n")
        return {
            "diff_bloat_passed": False,
            "diff_bloat_warnings": 0,
            "diff_bloat_violations": [],
            "diff_audit_error": str(err),
        }

    raw_list = raw_violations or []
    violations = [v for v in raw_list if v.get("file") != "git"]
    git_errors = [v for v in raw_list if v.get("file") == "git"]
    if git_errors and not violations:
        err_msg = "; ".join(str(v.get("issue", "git diff failed")) for v in git_errors)
        return {
            "diff_bloat_passed": False,
            "diff_bloat_warnings": 0,
            "diff_bloat_violations": [],
            "diff_audit_error": err_msg,
        }

    return {
        "diff_bloat_passed": bool(passed) and not violations,
        "diff_bloat_warnings": len(violations),
        "diff_bloat_violations": violations,
        "diff_audit_error": None,
    }


def verify_markdown_report(report_path: Optional[str]) -> Dict[str, Any]:
    """Runs Chain-of-Verification (CoVe) on an exported markdown review report."""
    if not report_path or not str(report_path).strip():
        return {
            "status": "SKIPPED",
            "factual_confidence_pct": None,
            "reason": "No markdown report path provided.",
        }

    if not os.path.isfile(report_path):
        return {
            "status": "SKIPPED",
            "factual_confidence_pct": None,
            "reason": f"Markdown report file not found: {report_path}",
        }

    try:
        with open(report_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except OSError as err:
        return {
            "status": "ERROR",
            "factual_confidence_pct": None,
            "error": str(err),
        }

    if not content.strip():
        return {
            "status": "EMPTY_REPORT",
            "factual_confidence_pct": 0.0,
            "reason": "Exported markdown report is empty.",
        }

    try:
        return ChainOfVerificationEngine().verify(report_path)
    except Exception as err:
        sys.stderr.write(f"[SENIOR-REVIEW] CoVe report verification failed: {err}\n")
        return {
            "status": "ERROR",
            "factual_confidence_pct": None,
            "error": str(err),
        }


def format_report(
    findings: List[Finding],
    files: List[Dict[str, Any]],
    lines_cuttable: int,
    diff_bloat_violations: Optional[List[Dict[str, Any]]] = None,
    plan_reconciliation: Optional[PlanReconciliationDTO] = None,
    solo_provenance: Optional[SoloProvenanceAuditDTO] = None,
    caller_compatibility: Optional[CallerCompatibilityDTO] = None,
    verdict: Optional[str] = None,
) -> str:
    """Renders the senior code review report in plain, pragmatic markdown."""
    must_fix = [f for f in findings if f.severity == "Must fix"]
    should_fix = [f for f in findings if f.severity == "Should fix"]
    nice_to_have = [f for f in findings if f.severity == "Nice to have"]
    bloat_list = diff_bloat_violations or []

    lines = [
        "# Senior Developer Quality & Lean Code Review",
        "",
        "> **Perspective:** Reviewed like the senior engineer who will be paged when this breaks.",
        "",
        f"- **Files Changed:** `{len(files)}`",
        f"- **Findings:** `{len(findings)}` (`{len(must_fix)}` Must fix, `{len(should_fix)}` Should fix, `{len(nice_to_have)}` Nice to have)",
        f"- **Diff Bloat Warnings:** `{len(bloat_list)}`",
    ]
    if verdict:
        lines.append(f"- **Verdict:** `{verdict}`")
    lines.extend([
        "",
        "---",
        "",
    ])

    if plan_reconciliation is not None:
        lines.extend([
            "### 📋 Plan Reconciliation Scorecard",
            f"- **Plan:** `{plan_reconciliation.plan_path}` (Scope: `{plan_reconciliation.milestone_scope or 'ALL'}`)",
            f"- **Alignment Score:** `{plan_reconciliation.alignment_score_pct}%` (`{'PASS' if plan_reconciliation.passed else 'FAIL'}`)",
            f"- **Planned Files:** `{len(plan_reconciliation.planned_files)}` | **Missing:** `{len(plan_reconciliation.missing_planned_files)}` | **Undeleted:** `{len(plan_reconciliation.undeleted_files)}` | **Unplanned:** `{len(plan_reconciliation.unplanned_modified_files)}`",
            f"- **Drifted Contracts:** `{len(plan_reconciliation.drifted_contracts)}` | **Missing Matrix Tests:** `{len(plan_reconciliation.missing_matrix_tests)}`",
            "",
        ])

    if solo_provenance is not None:
        mut_display = ", ".join(f"{k}={v:.1f}%" for k, v in sorted(solo_provenance.mutation_scores.items())) or "None"
        lines.extend([
            "### 🔐 /solo Forensic Provenance",
            f"- **Provenance Score:** `{solo_provenance.provenance_score_pct}%` (`{'PASS' if solo_provenance.passed else 'FAIL'}`)",
            f"- **Valid Red Receipts:** `{len(solo_provenance.valid_red_receipts)}` | **Tampered/Invalid:** `{len(solo_provenance.tampered_or_invalid_receipts)}` | **Post-Red Tampered Tests:** `{len(solo_provenance.post_red_tampered_tests)}`",
            f"- **Mutation Scores:** `{mut_display}` | **Decision Log Valid:** `{solo_provenance.decision_log_valid}`",
            "",
        ])

    if caller_compatibility is not None and (
        caller_compatibility.modified_symbols
        or caller_compatibility.broken_call_sites
        or caller_compatibility.import_cycles
        or caller_compatibility.high_fan_in_targets
    ):
        lines.extend([
            "### 🔗 Downstream Caller & Acyclicity Safety",
            f"- **Status:** `{'PASS' if caller_compatibility.passed else 'FAIL'}`",
            f"- **Modified Signatures:** `{len(caller_compatibility.modified_symbols)}` | **Broken Callers:** `{len(caller_compatibility.broken_call_sites)}` | **Import Cycles:** `{len(caller_compatibility.import_cycles)}`",
            "",
        ])

    if not files and not findings:
        lines.append("ℹ️ **No changes found in the specified target.** Working directory is clean.")
    elif not findings:
        lines.append("🎉 **Verdict: Looks good. Clean, lean, and ready to ship.**")
    else:
        # Grouped findings
        count = 1
        for group_name, group_items in [("🚨 Must Fix (Blockers)", must_fix),
                                        ("⚠️ Should Fix (Reliability & Scale)", should_fix),
                                        ("💡 Nice to Have (Lean & Cleanup)", nice_to_have)]:
            if not group_items:
                continue
            lines.append(f"### {group_name}")
            lines.append("")
            for item in group_items:
                loc = f"`{item.file_path}:{item.line_no}`" if item.line_no else f"`{item.file_path}`"
                lines.append(f"#### {count}. **{item.title}** ({loc})")
                lines.append(f"- **What this is:** {item.what_is}")
                lines.append(f"- **Problem:** {item.problem}")
                lines.append(f"- **Fix:** {item.fix}")
                lines.append(f"- **If we skip it:** {item.if_skipped}")
                lines.append("")
                count += 1

        lines.append("---")
        lines.append("### Verdict")
        if must_fix:
            lines.append(f"❌ **Action Required:** Resolve `{len(must_fix)}` blocker(s) before merging.")
        elif should_fix:
            lines.append(f"⚠️ **Caution:** Address `{len(should_fix)}` recommendation(s) to avoid flaky runs or debt.")
        else:
            lines.append("✅ **Approved with minor notes:** Safe to proceed.")

        if lines_cuttable > 0:
            lines.append(f"\n📉 **Lean Opportunity:** ~`{lines_cuttable}` unnecessary line(s) can be safely deleted.")

    if bloat_list:
        lines.append("")
        lines.append("### 📦 Diff Bloat & Anti-Rewrite Audit")
        for violation in bloat_list:
            v_file = violation.get("file", "unknown")
            v_issue = violation.get("issue", "Monolithic rewrite detected")
            lines.append(f"- **{v_file}**: {v_issue}")

    return "\n".join(lines)


def _dict_to_finding(item: Dict[str, str]) -> Finding:
    raw_line = item.get("line", "1")
    line_no = int(raw_line) if str(raw_line).isdigit() else 1
    return Finding(
        severity=item.get("severity", "Should fix"),
        title=item.get("title", item.get("code", "Audit finding")),
        file_path=item.get("file", "."),
        line_no=line_no,
        what_is=item.get("what_is", ""),
        problem=item.get("problem", ""),
        fix=item.get("fix", ""),
        if_skipped=item.get("if_skipped", ""),
    )


def evaluate_review(
    repo_dir: str,
    target: str = "uncommitted",
    output_md: Optional[str] = None,
    verify_report: bool = False,
    plan_path: Optional[str] = None,
    milestone_id: Optional[str] = None,
    strict: bool = False,
    strict_solo: bool = False,
    receipt_out: Optional[str] = None,
) -> Tuple[int, Dict[str, Any], str, Optional[Dict[str, Any]]]:
    """Executes diff extraction, AST review, Plan-vs-Solo reconciliation, and receipt signing without stdout output."""
    repo_dir = os.path.abspath(repo_dir)
    diff_text = get_git_diff(repo_dir, target)

    files = parse_diff(diff_text)
    findings, lines_cuttable = analyze_diff(files, repo_dir)
    diff_audit = audit_diff_bloat(repo_dir)
    bloat_violations = diff_audit["diff_bloat_violations"]

    plan_dto: Optional[PlanReconciliationDTO] = None
    solo_dto: Optional[SoloProvenanceAuditDTO] = None
    caller_dto = CallerCompatibilityDTO(
        modified_symbols=(),
        broken_call_sites=(),
        import_cycles=(),
        high_fan_in_targets=(),
        passed=True,
    )
    changed_paths = [f["path"] for f in files]
    if plan_path or milestone_id or strict_solo:
        plan_dto, solo_dto, caller_dto, audit_findings = audit_plan_and_solo_execution(
            repo_root=repo_dir,
            changed_files=changed_paths,
            diff_text=diff_text,
            plan_path=plan_path,
            milestone_id=milestone_id,
            strict_solo=strict_solo,
        )
        findings.extend(_dict_to_finding(item) for item in audit_findings)
    elif files:
        caller_findings: List[Dict[str, str]] = []
        caller_dto = _audit_callers_and_cycles(
            repo_root=repo_dir,
            changed_files=changed_paths,
            diff_text=diff_text,
            findings=caller_findings,
        )
        findings.extend(_dict_to_finding(item) for item in caller_findings)

    verdict, passed, exit_code = compute_review_verdict(findings, strict=strict)
    must_count = sum(1 for f in findings if f.severity == "Must fix")
    should_count = sum(1 for f in findings if f.severity == "Should fix")
    nice_count = sum(1 for f in findings if f.severity == "Nice to have")

    signed_receipt: Optional[UnifiedReviewReceiptDTO] = None
    resolved_receipt_path: Optional[str] = None
    if receipt_out and str(receipt_out).strip():
        resolved_receipt_path = str(receipt_out).strip()
    elif plan_path or strict_solo:
        resolved_receipt_path = os.path.join(repo_dir, "reports", "code_review_receipt.json")

    if resolved_receipt_path:
        signed_receipt = sign_and_write_review_receipt(
            receipt_path=resolved_receipt_path,
            repo_root=repo_dir,
            verdict=verdict,
            passed=passed,
            target_scope=target,
            files_changed=len(files),
            must_fix_count=must_count,
            should_fix_count=should_count,
            nice_to_have_count=nice_count,
            plan_reconciliation=plan_dto,
            solo_provenance=solo_dto,
            caller_compatibility=caller_dto,
        )

    report_text = format_report(
        findings,
        files,
        lines_cuttable,
        diff_bloat_violations=bloat_violations,
        plan_reconciliation=plan_dto,
        solo_provenance=solo_dto,
        caller_compatibility=caller_dto,
        verdict=verdict,
    )
    exported_md_path: Optional[str] = None
    if output_md and str(output_md).strip():
        out_path = Path(output_md)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_text, encoding="utf-8")
        exported_md_path = str(out_path)

    cove_result: Optional[Dict[str, Any]] = None
    if verify_report:
        cove_result = verify_markdown_report(exported_md_path)

    payload: Dict[str, Any] = {
        "target": target,
        "verdict": verdict,
        "passed": passed,
        "files_count": len(files),
        "findings_count": len(findings),
        "lines_cuttable": lines_cuttable,
        "diff_bloat_passed": diff_audit["diff_bloat_passed"],
        "diff_bloat_warnings": diff_audit["diff_bloat_warnings"],
        "diff_bloat_violations": bloat_violations,
        "plan_reconciliation": asdict(plan_dto) if plan_dto else None,
        "solo_provenance": asdict(solo_dto) if solo_dto else None,
        "caller_compatibility": asdict(caller_dto),
        "findings": [f.to_dict() for f in findings],
    }
    if signed_receipt is not None:
        payload["receipt_path"] = resolved_receipt_path
        payload["receipt_hmac"] = signed_receipt.receipt_hmac
    if diff_audit.get("diff_audit_error") is not None:
        payload["diff_audit_error"] = diff_audit["diff_audit_error"]
    if verify_report and cove_result is not None:
        payload["cove_verification"] = cove_result
        payload["cove_confidence_pct"] = cove_result.get("factual_confidence_pct")

    return exit_code, payload, report_text, cove_result


def run_review(
    repo_dir: str,
    target: str = "uncommitted",
    as_json: bool = False,
    output_md: Optional[str] = None,
    verify_report: bool = False,
    plan_path: Optional[str] = None,
    milestone_id: Optional[str] = None,
    strict: bool = False,
    strict_solo: bool = False,
    receipt_out: Optional[str] = None,
) -> int:
    """Runs the diff extraction, AST review, Plan-vs-Solo reconciliation, and signed receipt export."""
    try:
        exit_code, payload, report_text, cove_result = evaluate_review(
            repo_dir=repo_dir,
            target=target,
            output_md=output_md,
            verify_report=verify_report,
            plan_path=plan_path,
            milestone_id=milestone_id,
            strict=strict,
            strict_solo=strict_solo,
            receipt_out=receipt_out,
        )
    except Exception as err:
        sys.stderr.write(f"❌ Error: Cannot complete review — {err}\n")
        if as_json:
            print(json.dumps({"error": str(err), "target": target}, indent=2, ensure_ascii=False))
        return 2

    if output_md and str(output_md).strip() and not as_json:
        print(f"📄 Markdown review report exported to: {output_md}")

    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return exit_code

    print("\n" + report_text)
    if cove_result is not None:
        cove_status = cove_result.get("status", "UNKNOWN")
        cove_conf = cove_result.get("factual_confidence_pct")
        conf_display = f"{cove_conf}%" if cove_conf is not None else "N/A"
        print(f"\n🔎 CoVe Report Verification: {cove_status} (Confidence: {conf_display})")
    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Senior Developer Quality & Lean Diff Reviewer (bugs, security, scale, tests, bloat, plan/solo audit)"
    )
    parser.add_argument("target_dir", nargs="?", default=".", help="Repository directory (default: current directory)")
    parser.add_argument("--staged", action="store_true", help="Review staged git changes")
    parser.add_argument("--branch", default=None, help="Review changes against a git branch or commit ref")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--output-md", "-o", default=None, help="Save review report to a Markdown file")
    parser.add_argument(
        "--verify-cove",
        action="store_true",
        help="Run Chain-of-Verification (CoVe) audit on exported Markdown report",
    )
    parser.add_argument("--plan", default=None, help="Path to /super-plan Markdown file to reconcile against")
    parser.add_argument("--milestone", default=None, help="Scope plan and /solo receipt reconciliation to a single milestone ID (e.g., M1)")
    parser.add_argument("--strict", action="store_true", help="Fail with exit code 1 on Should fix findings as well as Must fix")
    parser.add_argument("--strict-solo", action="store_true", help="Require valid signed /solo Red & Mutation receipts and strict decisions.tsv")
    parser.add_argument("--receipt-out", default=None, help="Output path for HMAC-signed code_review_receipt.json")

    args = parser.parse_args()
    diff_target = "staged" if args.staged else (args.branch if args.branch else "uncommitted")
    extra_kwargs: Dict[str, Any] = {}
    if args.plan:
        extra_kwargs["plan_path"] = args.plan
    if args.milestone:
        extra_kwargs["milestone_id"] = args.milestone
    if args.strict:
        extra_kwargs["strict"] = True
    if args.strict_solo:
        extra_kwargs["strict_solo"] = True
    if args.receipt_out:
        extra_kwargs["receipt_out"] = args.receipt_out
    sys.exit(
        run_review(
            args.target_dir,
            diff_target,
            args.json,
            output_md=args.output_md,
            verify_report=args.verify_cove,
            **extra_kwargs,
        )
    )


if __name__ == "__main__":
    main()
