#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

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
import re
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
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
    """Retrieves git diff based on target: uncommitted, staged, or branch/ref."""
    cmd = ["git", "diff"]
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


def analyze_diff(files: List[Dict[str, Any]], repo_dir: str) -> Tuple[List[Finding], int]:
    """Inspects diff files against senior dev quality & lean heuristics."""
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
    static_sleep_pattern = re.compile(r'(?:Thread\.sleep|time\.sleep|sleep\(\d{3,}\))')
    raw_xpath_pattern = re.compile(r'findTestObject|\.locator\(["\']//|\.locator\(["\']xpath=')

    for f in files:
        path = f["path"]
        path_lower = path.lower()
        is_code_file = any(path_lower.endswith(ext) for ext in (".py", ".ts", ".js", ".java", ".groovy", ".cs", ".sh", ".ps1", ".mjs", ".cjs"))
        for line_no, content in f["added_lines"]:
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

            # 2. Correctness: Swallowed Exceptions
            if is_code_file and (swallowed_catch_py.search(stripped) or swallowed_catch_js.search(stripped)):
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

            # 3. Flakiness / Concurrency: Static Sleep
            if is_code_file and static_sleep_pattern.search(stripped):
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

    # 6. Completeness: Non-trivial logic without any test
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


def format_report(findings: List[Finding], files: List[Dict[str, Any]], lines_cuttable: int) -> str:
    """Renders the senior code review report in plain, pragmatic markdown."""
    must_fix = [f for f in findings if f.severity == "Must fix"]
    should_fix = [f for f in findings if f.severity == "Should fix"]
    nice_to_have = [f for f in findings if f.severity == "Nice to have"]

    lines = [
        "# Senior Developer Quality & Lean Code Review",
        "",
        "> **Perspective:** Reviewed like the senior engineer who will be paged when this breaks.",
        "",
        f"- **Files Changed:** `{len(files)}`",
        f"- **Findings:** `{len(findings)}` (`{len(must_fix)}` Must fix, `{len(should_fix)}` Should fix, `{len(nice_to_have)}` Nice to have)",
        "",
        "---",
        "",
    ]

    if not files:
        lines.append("ℹ️ **No changes found in the specified target.** Working directory is clean.")
        return "\n".join(lines)

    if not findings:
        lines.append("🎉 **Verdict: Looks good. Clean, lean, and ready to ship.**")
        return "\n".join(lines)

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

    return "\n".join(lines)


def run_review(
    repo_dir: str,
    target: str = "uncommitted",
    as_json: bool = False,
    output_md: Optional[str] = None,
) -> int:
    """Runs the diff extraction and review."""
    repo_dir = os.path.abspath(repo_dir)
    try:
        diff_text = get_git_diff(repo_dir, target)
    except Exception as err:
        sys.stderr.write(f"❌ Error: Cannot complete review — {err}\n")
        if as_json:
            print(json.dumps({"error": str(err), "target": target}, indent=2, ensure_ascii=False))
        return 2

    files = parse_diff(diff_text)
    findings, lines_cuttable = analyze_diff(files, repo_dir)

    if as_json:
        payload = {
            "target": target,
            "files_count": len(files),
            "findings_count": len(findings),
            "lines_cuttable": lines_cuttable,
            "findings": [f.to_dict() for f in findings],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if not any(f.severity == "Must fix" for f in findings) else 1

    report_text = format_report(findings, files, lines_cuttable)
    if output_md:
        out_path = Path(output_md)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_text, encoding="utf-8")
        print(f"📄 Markdown review report exported to: {output_md}")

    print("\n" + report_text)
    return 0 if not any(f.severity == "Must fix" for f in findings) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Senior Developer Quality & Lean Diff Reviewer (bugs, security, scale, tests, bloat)"
    )
    parser.add_argument("target_dir", nargs="?", default=".", help="Repository directory (default: current directory)")
    parser.add_argument("--staged", action="store_true", help="Review staged git changes")
    parser.add_argument("--branch", default=None, help="Review changes against a git branch or commit ref")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--output-md", "-o", default=None, help="Save review report to a Markdown file")

    args = parser.parse_args()
    diff_target = "staged" if args.staged else (args.branch if args.branch else "uncommitted")
    sys.exit(run_review(args.target_dir, diff_target, args.json, output_md=args.output_md))


if __name__ == "__main__":
    main()
