#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/heal/ci_auto_healer.py — CI/CD Failure Detection & Safe Auto-Heal Bridge
-------------------------------------------------------------------------------
Connects CI/CD failure artifacts and GitHub Actions failed runs to Synapse Hub's
deterministic healing engines (pinpoint_failure, auto_fixer, agentless_patcher,
and ci_healing_hook):

  1. Ingests JUnit XML reports and CI failure logs (locally or via `gh` CLI).
  2. Triages each failure into:
       - AUTO_FIX_LINT: static test anti-patterns (hard delays, missing await, etc.)
       - LOCATOR_HEAL: broken UI selectors / wait timeouts in Page Classes
       - AUT_OR_LOGIC_DEFECT: genuine product/assertion/env bugs (NEVER auto-patched)
  3. Applies bounded, Clean-POM-compliant patches when `--apply` is enabled.
  4. Executes `--verify-cmd` and automatically rolls back patched files on failure.
  5. Emits structured JSON, PR markdown (`--out-pr`), and optional PR (`--create-pr`).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

from tools.heal.agentless_patcher import AgentlessPatcher
from tools.lint.auto_fixer import apply_file_fix, generate_fixes_for_code
from tools.report.pinpoint_failure import parse_failures

AUTO_FIX_LINT = "AUTO_FIX_LINT"
LOCATOR_HEAL = "LOCATOR_HEAL"
AUT_OR_LOGIC_DEFECT = "AUT_OR_LOGIC_DEFECT"
CI_ENV_DEFECT = "CI_ENV_DEFECT"

_LINT_SIGNAL_PATTERNS = (
    r"\bEXCESSIVE_HARD_DELAY\b",
    r"\bHARD_DELAY(?:_ANTI_PATTERN)?\b",
    r"\bUNAWAITED_ASYNC_ASSERTION\b",
    r"\bSWALLOWED_EXCEPTION\b",
    r"\bDANGLING_ASSERTION(?:_NO_MATCHER)?\b",
    r"\bwaitForTimeout\b",
    r"\bThread\.sleep\b",
    r"\btime\.sleep\b",
)

_LOCATOR_SIGNAL_PATTERNS = (
    r"\bTimeoutError\b",
    r"waiting for locator\b",
    r"\blocator\(",
    r"\bNoSuchElementException\b",
    r"\bElementNotFound\b",
    r"\bUnable to find element\b",
    r"strict mode violation",
    r"\bElementClickInterceptedException\b",
    r"\bStaleElementReferenceException\b",
    r"\bgetByRole\b",
    r"\bgetByTestId\b",
)

_CI_ENV_DEFECT_PATTERNS = (
    r"Executable doesn't exist",
    r"browserType\.launch",
    r"Please run the following command to download new browsers",
    r"\bECONNREFUSED\b",
    r"\bENOENT\b",
    r"\bModuleNotFoundError\b",
    r"\bImportError\b",
    r"\bcommand not found\b",
    r"Missing required release-candidate target",
)

_AUT_DEFECT_PATTERNS = (
    r"\bAssertionError\b",
    r"\bAssertion failed\b",
    r"\bHTTP\s+[45]\d{2}\b",
    r"\b500\s+Internal Server Error\b",
    r"\b401\s+Unauthorized\b",
    r"\b403\s+Forbidden\b",
    r"\b404\s+Not Found\b",
    r"status[_\s]?code",
    r"\bKeyError\b",
    r"\bTypeError\b",
    r"\bAttributeError\b",
    r"\bZeroDivisionError\b",
    r"\bSyntaxError\b",
    r"expected\s+.+?\s+(?:but got|to equal|to be|!=)",
)


def classify_failure(failure: Dict[str, Any]) -> Dict[str, Any]:
    """Classifies a CI failure into AUTO_FIX_LINT, LOCATOR_HEAL, CI_ENV_DEFECT, or AUT_OR_LOGIC_DEFECT."""
    reason = str(failure.get("reason") or "")
    raw_trace = str(failure.get("trace") or "")
    combined = f"{reason}\n{raw_trace}".strip()

    for pat in _LINT_SIGNAL_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return {
                "category": AUTO_FIX_LINT,
                "eligible": True,
                "rationale": f"Matched static test anti-pattern signal ({pat}).",
            }

    for pat in _CI_ENV_DEFECT_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return {
                "category": CI_ENV_DEFECT,
                "eligible": False,
                "rationale": f"Matched CI/environment infrastructure signal ({pat}); fix runner setup rather than test scripts.",
            }

    for pat in _AUT_DEFECT_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return {
                "category": AUT_OR_LOGIC_DEFECT,
                "eligible": False,
                "rationale": f"Matched AUT/logic/environment assertion signal ({pat}); never mask product bugs.",
            }

    for pat in _LOCATOR_SIGNAL_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return {
                "category": LOCATOR_HEAL,
                "eligible": True,
                "rationale": f"Matched UI locator/synchronization failure signal ({pat}).",
            }

    return {
        "category": AUT_OR_LOGIC_DEFECT,
        "eligible": False,
        "rationale": "Unclassified failure treated conservatively as non-auto-healable defect.",
    }


def _resolve_target_file(repo_root: str, raw_file: str) -> str:
    """Resolves a failure file path against repo_root when relative."""
    if not raw_file or raw_file == "UnknownFile":
        return ""
    if os.path.isfile(raw_file):
        return os.path.abspath(raw_file)
    candidate = os.path.abspath(os.path.join(repo_root, raw_file))
    if os.path.isfile(candidate):
        return candidate
    return raw_file


def _parse_log_failures(log_path: str, repo_root: str) -> List[Dict[str, Any]]:
    """Extracts structured failure candidates from a raw CI failure log file."""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return []

    patcher = AgentlessPatcher(repo_root=repo_root)
    failures: List[Dict[str, Any]] = []
    seen = set()

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        has_signal = any(
            re.search(pat, stripped, re.IGNORECASE)
            for pat in (_LINT_SIGNAL_PATTERNS + _CI_ENV_DEFECT_PATTERNS + _LOCATOR_SIGNAL_PATTERNS + _AUT_DEFECT_PATTERNS)
        )
        if not has_signal:
            continue
        parsed = patcher.parse_stacktrace(stripped)
        if not parsed:
            m = re.search(
                r"([A-Za-z]:[/\\][^\s:]+|[^\s:]+\.(?:ts|tsx|js|jsx|py|groovy)):(\d+)",
                stripped,
            )
            if m:
                parsed = {"file": m.group(1), "line": int(m.group(2)), "method": "unknown_method"}
        if parsed:
            key = (parsed["file"], str(parsed["line"]), stripped[:120])
            if key not in seen:
                seen.add(key)
                failures.append(
                    {
                        "tc": os.path.basename(parsed["file"]),
                        "reason": stripped[:240],
                        "file": parsed["file"],
                        "line": str(parsed["line"]),
                        "trace": stripped,
                        "source": log_path,
                    }
                )

    if not failures:
        loc = patcher.parse_stacktrace(content)
        if loc:
            failures.append(
                {
                    "tc": os.path.basename(loc["file"]),
                    "reason": content.splitlines()[-1][:240] if content.splitlines() else "CI log failure",
                    "file": loc["file"],
                    "line": str(loc["line"]),
                    "trace": content[-600:],
                    "source": log_path,
                }
            )

    return failures


def _discover_artifact_files(
    artifacts_dir: str,
    xml_files: List[str],
    log_files: List[str],
) -> None:
    """Discovers JUnit XML and CI log files under artifacts_dir without duplicates."""
    if not os.path.isdir(artifacts_dir):
        return
    for walk_root, _, files in os.walk(artifacts_dir):
        for fname in sorted(files):
            fpath = os.path.abspath(os.path.join(walk_root, fname))
            lower = fname.lower()
            if lower.endswith(".xml") and fpath not in xml_files:
                xml_files.append(fpath)
            elif lower.endswith((".log", ".txt")) and fpath not in log_files:
                log_files.append(fpath)


def collect_ci_failures(
    artifacts_dir: str,
    error_log: Optional[str] = None,
    xml_path: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Collects failures from JUnit XML reports and CI logs under artifacts_dir."""
    root_dir = os.path.abspath(repo_root or os.getcwd())
    xml_files: List[str] = []
    log_files: List[str] = []

    if xml_path and os.path.isfile(xml_path):
        xml_files.append(os.path.abspath(xml_path))
    if error_log and os.path.isfile(error_log):
        log_files.append(os.path.abspath(error_log))

    _discover_artifact_files(artifacts_dir, xml_files, log_files)

    failures: List[Dict[str, Any]] = []
    seen = set()

    for xf in xml_files:
        for item in parse_failures(xf):
            resolved = _resolve_target_file(root_dir, str(item.get("file", "")))
            entry = dict(item)
            entry["file"] = resolved or item.get("file", "UnknownFile")
            entry["source"] = xf
            dedup_key = (entry["file"], str(entry.get("line", "?")), str(entry.get("reason", ""))[:120])
            if dedup_key not in seen:
                seen.add(dedup_key)
                failures.append(entry)

    for lf in log_files:
        for item in _parse_log_failures(lf, root_dir):
            resolved = _resolve_target_file(root_dir, str(item.get("file", "")))
            item["file"] = resolved or item.get("file", "UnknownFile")
            dedup_key = (item["file"], str(item.get("line", "?")), str(item.get("reason", ""))[:120])
            if dedup_key not in seen:
                seen.add(dedup_key)
                failures.append(item)

    return {
        "failures": failures,
        "xml_files": xml_files,
        "log_files": log_files,
    }


def fetch_gh_failed_run(
    repo_root: str,
    run_id: Optional[str] = None,
    artifacts_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetches failed GitHub Actions run logs/artifacts using the `gh` CLI."""
    gh_bin = shutil.which("gh")
    if not gh_bin:
        return {
            "ok": False,
            "run_id": run_id,
            "error": "GitHub CLI (`gh`) is not installed or not on PATH.",
        }

    target_dir = os.path.abspath(artifacts_dir or os.path.join(repo_root, "artifacts"))
    os.makedirs(target_dir, exist_ok=True)
    resolved_run_id = str(run_id).strip() if run_id else ""
    branch = ""

    if not resolved_run_id:
        list_proc = subprocess.run(
            [
                gh_bin,
                "run",
                "list",
                "--status",
                "failure",
                "--limit",
                "1",
                "--json",
                "databaseId,headBranch,workflowName,url",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if list_proc.returncode != 0:
            return {
                "ok": False,
                "run_id": None,
                "error": (list_proc.stderr or list_proc.stdout or "gh run list failed").strip(),
            }
        try:
            runs = json.loads(list_proc.stdout or "[]")
        except json.JSONDecodeError as exc:
            return {"ok": False, "run_id": None, "error": f"Invalid gh JSON output: {exc}"}
        if not runs:
            return {"ok": False, "run_id": None, "error": "No failed workflow runs found via gh."}
        resolved_run_id = str(runs[0].get("databaseId", "")).strip()
        branch = str(runs[0].get("headBranch", "")).strip()

    log_proc = subprocess.run(
        [gh_bin, "run", "view", resolved_run_id, "--log-failed"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if log_proc.returncode != 0:
        return {
            "ok": False,
            "run_id": resolved_run_id,
            "error": (log_proc.stderr or log_proc.stdout or "gh run view failed").strip(),
        }

    failed_log_path = os.path.join(target_dir, f"gh_run_{resolved_run_id}_failed.log")
    if log_proc.stdout:
        with open(failed_log_path, "w", encoding="utf-8") as f:
            f.write(log_proc.stdout)

    dl_proc = subprocess.run(
        [gh_bin, "run", "download", resolved_run_id, "--dir", target_dir],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=180,
    )

    return {
        "ok": True,
        "run_id": resolved_run_id,
        "branch": branch,
        "log_path": failed_log_path if os.path.isfile(failed_log_path) else None,
        "artifacts_downloaded": dl_proc.returncode == 0,
        "download_note": (dl_proc.stderr or "").strip() if dl_proc.returncode != 0 else "",
    }


def _plan_locator_patch(
    patcher: AgentlessPatcher,
    target_file: str,
    line_no: int,
) -> Optional[Dict[str, Any]]:
    """Generates and validates a minimal Clean-POM-compliant locator patch for target_file:line_no."""
    if not os.path.isfile(target_file):
        return None
    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return None

    if line_no <= 0 or line_no > len(lines):
        return None

    orig_line = lines[line_no - 1]
    if not re.search(
        r"(?:\bpage\.|\blocator\(|\bclick\(|\bgetBy|\bBy\.|\bfind_element|\bWebUI\.)",
        orig_line,
    ):
        return None
    ext = target_file.rsplit(".", 1)[-1].lower() if "." in target_file else "ts"
    candidates = patcher.generate_candidates(target_file, line_no, failing_chunk=orig_line)

    valid: List[Tuple[int, Dict[str, Any], str]] = []
    for cand in candidates:
        patch_text = str(cand.get("patch", "")).strip()
        if not patch_text or patch_text == orig_line.strip():
            continue
        syn_ok, _ = patcher.validate_syntax(patch_text, file_type=ext)
        if not syn_ok:
            continue
        pom_ok, _ = patcher.enforce_clean_pom(target_file, patch_text)
        if not pom_ok:
            continue
        valid.append((len(patch_text.splitlines()), cand, patch_text))

    if not valid:
        return None

    valid.sort(key=lambda item: item[0])
    _, winner, winner_patch = valid[0]
    indent = orig_line[: len(orig_line) - len(orig_line.lstrip(" \t"))]
    replacement_lines = [
        f"{indent}{sub}" if sub.strip() else sub for sub in winner_patch.splitlines()
    ]
    replacement_block = "\n".join(replacement_lines) + ("\n" if orig_line.endswith("\n") else "")

    return {
        "candidate_id": winner["id"],
        "strategy": winner["type"],
        "line": line_no,
        "original_line": orig_line.rstrip("\r\n"),
        "patched_block": replacement_block.rstrip("\r\n"),
        "replacement_block": replacement_block,
    }


def _build_pr_markdown(result: Dict[str, Any]) -> str:
    """Formats a structured Pull Request description with diffs, skipped AUT bugs, and verification proof."""
    run_label = result.get("run_id") or "local"
    applied = result.get("applied_patches") or []
    planned = result.get("planned_patches") or []
    patches = applied if applied else planned
    skipped = result.get("skipped_aut_defects") or []
    skipped_env = result.get("skipped_env_defects") or []

    lines = [
        "## CI/CD Autonomous Self-Healing Report",
        "",
        f"- **CI Run ID:** `{run_label}`",
        f"- **Status:** `{result.get('status')}`",
        f"- **Verified:** `{result.get('verified')}`",
        f"- **Timestamp (UTC):** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        "",
        "### Applied / Planned Safe Repairs",
    ]

    if patches:
        for p in patches:
            lines.append(f"- `{p['file']}` ({p['category']}): {p.get('summary', 'patched')}")
            if p.get("diff"):
                lines.extend(["```diff", p["diff"].strip(), "```"])
    else:
        lines.append("- None")

    lines.extend(["", "### Skipped CI / Environment Defects (Runner / Setup)"])
    if skipped_env:
        for s in skipped_env:
            lines.append(f"- `{s.get('tc', 'unknown')}` (`{s.get('file', '?')}:{s.get('line', '?')}`): {s.get('reason', '')}")
    else:
        lines.append("- None")

    lines.extend(["", "### Skipped AUT / Logic Defects (Never Masked)"])
    if skipped:
        for s in skipped:
            lines.append(f"- `{s.get('tc', 'unknown')}` (`{s.get('file', '?')}:{s.get('line', '?')}`): {s.get('reason', '')}")
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def _rollback_files(originals: Dict[str, str]) -> bool:
    """Restores modified files to their exact pre-heal snapshots."""
    ok = True
    for fpath, content in originals.items():
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError:
            ok = False
    return ok


def _create_heal_pr(
    repo_root: str,
    modified_files: List[str],
    pr_body_path: Optional[str],
    pr_markdown: str,
    run_id: Optional[str],
    base_branch: str,
) -> Dict[str, Any]:
    """Creates a dedicated auto-heal branch, commits modified files, pushes, and opens a PR via `gh`."""
    gh_bin = shutil.which("gh")
    if not gh_bin:
        return {"created": False, "error": "gh CLI unavailable for PR creation."}

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = str(run_id).strip() if run_id else "local"
    branch_name = f"auto-heal/ci-{suffix}-{ts}"

    orig_proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    orig_branch = (orig_proc.stdout or "").strip() if orig_proc.returncode == 0 else ""

    created_temp_body = False
    body_file = pr_body_path
    if not body_file:
        reports_dir = os.path.join(repo_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        body_file = os.path.join(reports_dir, f"auto_heal_pr_{suffix}.md")
        with open(body_file, "w", encoding="utf-8") as f:
            f.write(pr_markdown)
        created_temp_body = True

    rel_files = [os.path.relpath(f, repo_root) for f in modified_files]
    steps = [
        ["git", "checkout", "-b", branch_name],
        ["git", "add", "--", *rel_files],
        ["git", "commit", "-m", f"fix(ci): auto-heal eligible test failures from run {suffix}"],
        ["git", "push", "-u", "origin", branch_name],
        [
            gh_bin,
            "pr",
            "create",
            "--base",
            base_branch,
            "--title",
            f"fix(ci): auto-heal eligible failures (run {suffix})",
            "--body-file",
            body_file,
        ],
    ]
    pr_url = ""
    switched_branch = False
    for cmd in steps:
        proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=60)
        if cmd[:3] == ["git", "checkout", "-b"] and proc.returncode == 0:
            switched_branch = True
        if proc.returncode != 0:
            if switched_branch and orig_branch and orig_branch != "HEAD":
                subprocess.run(
                    ["git", "checkout", orig_branch],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            if created_temp_body and body_file and os.path.isfile(body_file):
                try:
                    os.remove(body_file)
                except OSError as cleanup_err:
                    sys.stderr.write(f"Notice: failed to remove temp PR body {body_file}: {cleanup_err}\n")
            return {
                "created": False,
                "branch": branch_name,
                "error": (proc.stderr or proc.stdout or f"Command failed: {' '.join(cmd)}").strip(),
            }
    if cmd[0] == gh_bin:
            pr_url = (proc.stdout or "").strip()
    return {"created": True, "branch": branch_name, "pr_url": pr_url}


def _git_dirty_paths(repo_root: str) -> Dict[str, str]:
    """Returns a map of relative path -> git porcelain status code for dirty files."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return {}
    if proc.returncode != 0:
        return {}
    dirty: Dict[str, str] = {}
    for raw_line in proc.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        status_code = raw_line[:2]
        rel_path = raw_line[3:].strip()
        if " -> " in rel_path:
            rel_path = rel_path.split(" -> ")[1].strip()
        dirty[rel_path] = status_code
    return dirty


def _rollback_copilot_paths(
    repo_root: str,
    changed_files: List[str],
    post_dirty: Dict[str, str],
    pre_snapshots: Dict[str, str],
) -> bool:
    """Rolls back files modified or created by Copilot CLI without touching unrelated files."""
    ok = _rollback_files(pre_snapshots)
    for rel_path in changed_files:
        abs_path = os.path.abspath(os.path.join(repo_root, rel_path))
        if abs_path in pre_snapshots:
            continue
        if post_dirty.get(rel_path) == "??":
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                except OSError:
                    ok = False
            continue
        try:
            proc = subprocess.run(
                ["git", "checkout", "--", rel_path],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                ok = False
        except (subprocess.SubprocessError, OSError):
            ok = False
    return ok


def build_copilot_repair_prompt(
    result: Dict[str, Any],
    unresolved_eligible: List[Dict[str, Any]],
    artifacts_dir: str,
) -> str:
    """Builds a guardrail-enforced repair prompt for GitHub Copilot CLI or Coding Agent."""
    run_label = result.get("run_id") or "local"
    skipped = result.get("skipped_aut_defects") or []
    lines = [
        f"# CI/CD Auto-Heal Escalation Prompt (Run `{run_label}`)",
        "",
        "You are assisting Synapse Hub's CI/CD Auto-Heal pipeline.",
        f"- **Artifacts Directory:** `{artifacts_dir}`",
        f"- **Current Pipeline Status:** `{result.get('status')}`",
        "",
        "## Strict Guardrails",
        "1. Follow `.github/copilot-instructions.md` and Clean POM architecture (keep UI selectors inside Page Classes).",
        "2. DO NOT weaken assertions, delete tests, add `waitForTimeout`/`time.sleep`, or silence exceptions.",
        "3. DO NOT mask AUT/logic bugs listed below; only repair legitimate test/locator/synchronization issues.",
        "4. Keep the diff minimal and surgical.",
        "",
        "## Unresolved Eligible Failures to Fix",
    ]
    if unresolved_eligible:
        for item in unresolved_eligible:
            lines.append(
                f"- `{item.get('tc', 'unknown')}` (`{item.get('file', '?')}:{item.get('line', '?')}`): {item.get('reason', '')}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Skipped AUT / Logic Defects (DO NOT MASK)"])
    if skipped:
        for item in skipped:
            lines.append(
                f"- `{item.get('tc', 'unknown')}` (`{item.get('file', '?')}:{item.get('line', '?')}`): {item.get('reason', '')}"
            )
    else:
        lines.append("- None")

    skipped_env = result.get("skipped_env_defects") or []
    lines.extend(["", "## Skipped CI / Environment Defects (Runner / Setup)"])
    if skipped_env:
        for item in skipped_env:
            lines.append(
                f"- `{item.get('tc', 'unknown')}` (`{item.get('file', '?')}:{item.get('line', '?')}`): {item.get('reason', '')}"
            )
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def run_copilot_cli_fallback(
    repo_root: str,
    prompt: str,
    verify_cmd: Optional[str] = None,
    pre_snapshots: Optional[Dict[str, str]] = None,
    allowed_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Invokes GitHub Copilot CLI in headless mode with strict tool guardrails and rollback."""
    copilot_bin = shutil.which("copilot")
    if not copilot_bin:
        return {
            "attempted": False,
            "ok": False,
            "changed_files": [],
            "verified": False,
            "rolled_back": False,
            "error": "Copilot CLI (`copilot`) is not installed or not on PATH.",
        }

    snapshots = dict(pre_snapshots or {})
    pre_dirty = _git_dirty_paths(repo_root)
    tools = allowed_tools or ["write", "shell(git diff:*)", "shell(pytest:*)"]
    cmd = [copilot_bin, "-p", prompt, "-s", *[f"--allow-tool={t}" for t in tools]]

    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "attempted": True,
            "ok": False,
            "changed_files": [],
            "verified": False,
            "rolled_back": False,
            "error": f"Copilot CLI execution failed: {exc}",
        }

    post_dirty = _git_dirty_paths(repo_root)
    changed_files = [
        path for path, st in post_dirty.items() if path not in pre_dirty or st != pre_dirty[path]
    ]
    if proc.returncode != 0 or not changed_files:
        rolled = False
        if changed_files:
            rolled = _rollback_copilot_paths(repo_root, changed_files, post_dirty, snapshots)
        err_msg = (proc.stderr or proc.stdout or "Copilot CLI made no changes.").strip()
        return {
            "attempted": True,
            "ok": False,
            "changed_files": changed_files,
            "verified": False,
            "rolled_back": rolled,
            "error": err_msg[:500],
        }

    patcher = AgentlessPatcher(repo_root=repo_root)
    for rel_path in changed_files:
        abs_path = os.path.abspath(os.path.join(repo_root, rel_path))
        if os.path.isfile(abs_path):
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            pom_ok, pom_msg = patcher.enforce_clean_pom(abs_path, content)
            if not pom_ok:
                rolled = _rollback_copilot_paths(repo_root, changed_files, post_dirty, snapshots)
                return {
                    "attempted": True,
                    "ok": False,
                    "changed_files": changed_files,
                    "verified": False,
                    "rolled_back": rolled,
                    "error": pom_msg,
                }

    if verify_cmd:
        verify_ok, verify_out = _run_verify_command(verify_cmd, repo_root)
        if not verify_ok:
            rolled = _rollback_copilot_paths(repo_root, changed_files, post_dirty, snapshots)
            return {
                "attempted": True,
                "ok": False,
                "changed_files": changed_files,
                "verified": False,
                "rolled_back": rolled,
                "error": verify_out[:500],
            }

    return {
        "attempted": True,
        "ok": True,
        "changed_files": changed_files,
        "verified": True,
        "rolled_back": False,
        "error": "",
    }


def create_copilot_issue(
    repo_root: str,
    result: Dict[str, Any],
    prompt_text: str,
    run_id: Optional[str] = None,
    assign_copilot: bool = True,
) -> Dict[str, Any]:
    """Opens a GitHub Issue summarizing unresolved CI failures and optionally assigns @copilot."""
    gh_bin = shutil.which("gh")
    if not gh_bin:
        return {"created": False, "assigned": False, "error": "gh CLI unavailable for issue creation."}

    suffix = str(run_id).strip() if run_id else "local"
    reports_dir = os.path.join(repo_root, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    body_file = os.path.join(reports_dir, f"copilot_issue_{suffix}.md")
    title = f"fix(ci): triage & heal unresolved CI failures (run {suffix})"

    try:
        with open(body_file, "w", encoding="utf-8") as f:
            f.write(prompt_text)

        base_cmd = [gh_bin, "issue", "create", "--title", title, "--body-file", body_file]
        if assign_copilot:
            proc = subprocess.run(
                [*base_cmd, "--assignee", "@copilot"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0:
                return {"created": True, "assigned": True, "issue_url": (proc.stdout or "").strip()}

        proc_unassigned = subprocess.run(
            base_cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc_unassigned.returncode == 0:
            return {
                "created": True,
                "assigned": False,
                "issue_url": (proc_unassigned.stdout or "").strip(),
            }
        return {
            "created": False,
            "assigned": False,
            "error": (proc_unassigned.stderr or proc_unassigned.stdout or "gh issue create failed").strip(),
        }
    except (subprocess.SubprocessError, OSError) as exc:
        return {"created": False, "assigned": False, "error": str(exc)}
    finally:
        if os.path.isfile(body_file):
            try:
                os.remove(body_file)
            except OSError as cleanup_err:
                sys.stderr.write(f"Notice: failed to remove temp issue body {body_file}: {cleanup_err}\n")


def _apply_patches_for_file(
    target_file: str,
    before_content: str,
    file_entries: List[Dict[str, Any]],
) -> str:
    """Applies deduplicated lint fixes and bottom-up locator patches to target_file."""
    apply_lint = any(e.get("lint_fixes") for e in file_entries)
    if apply_lint:
        apply_file_fix(target_file, dry_run=False, create_backup=False)

    locator_plans = [e["locator_patch"] for e in file_entries if e.get("locator_patch")]
    locator_plans.sort(key=lambda lp: int(lp.get("line", 0)), reverse=True)
    if locator_plans:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            file_lines = f.readlines()
        for lp in locator_plans:
            idx = int(lp["line"]) - 1
            if 0 <= idx < len(file_lines):
                file_lines[idx] = lp["replacement_block"]
        with open(target_file, "w", encoding="utf-8") as f:
            f.writelines(file_lines)

    with open(target_file, "r", encoding="utf-8", errors="replace") as f:
        after_content = f.read()
    if after_content == before_content:
        return ""
    return "\n".join(
        difflib.unified_diff(
            before_content.splitlines(),
            after_content.splitlines(),
            fromfile=f"a/{os.path.basename(target_file)}",
            tofile=f"b/{os.path.basename(target_file)}",
            lineterm="",
        )
    )


def _run_verify_command(verify_cmd: str, repo_root: str) -> Tuple[bool, str]:
    """Executes verification command safely, catching parse, OS, and timeout errors."""
    try:
        argv = shlex.split(verify_cmd)
        if not argv:
            return False, "Empty verification command."
        proc = subprocess.run(
            argv,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, output
    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
        return False, f"Verification execution failed: {exc}"


def _apply_copilot_escalation(
    resolved_root: str,
    artifacts_dir: str,
    result: Dict[str, Any],
    unresolved_eligible: List[Dict[str, Any]],
    originals: Dict[str, str],
    apply_patches: bool,
    verify_cmd: Optional[str],
    copilot_fallback: bool,
    copilot_issue: bool,
    out_copilot_prompt: Optional[str],
    run_id: Optional[str],
) -> None:
    """Writes Copilot prompt, runs Copilot CLI fallback if needed, and optionally files an Issue."""
    needs_ai = bool(unresolved_eligible) or bool(result.get("rolled_back"))
    prompt_text = build_copilot_repair_prompt(result, unresolved_eligible, artifacts_dir)
    if out_copilot_prompt:
        os.makedirs(os.path.dirname(os.path.abspath(out_copilot_prompt)), exist_ok=True)
        with open(out_copilot_prompt, "w", encoding="utf-8") as f:
            f.write(prompt_text)

    copilot_res: Optional[Dict[str, Any]] = None
    if copilot_fallback and apply_patches and needs_ai:
        copilot_res = run_copilot_cli_fallback(
            repo_root=resolved_root,
            prompt=prompt_text,
            verify_cmd=verify_cmd,
            pre_snapshots=originals,
        )
        if copilot_res.get("ok") and copilot_res.get("verified"):
            for rel_path in copilot_res.get("changed_files", []):
                abs_path = os.path.abspath(os.path.join(resolved_root, rel_path))
                result["applied_patches"].append(
                    {
                        "file": abs_path,
                        "category": "COPILOT_CLI_HEAL",
                        "tc": "copilot_cli",
                        "summary": "Repaired via GitHub Copilot CLI fallback and verified",
                        "diff": "",
                    }
                )
            result["applied_count"] = len(result["applied_patches"])
            result["verified"] = True
            result["rolled_back"] = False
            result["status"] = "COPILOT_HEALED_AND_VERIFIED"
            needs_ai = False
        elif copilot_res.get("rolled_back"):
            result["rolled_back"] = True
            result["verified"] = False
            result["status"] = "VERIFICATION_FAILED_ROLLED_BACK"

    issue_res: Optional[Dict[str, Any]] = None
    has_unfixed_aut = bool(result.get("skipped_aut_defects")) and not (
        result.get("verified") and not needs_ai
    )
    if copilot_issue and (needs_ai or has_unfixed_aut):
        issue_res = create_copilot_issue(
            repo_root=resolved_root,
            result=result,
            prompt_text=prompt_text,
            run_id=run_id,
            assign_copilot=needs_ai,
        )

    result["needs_ai_escalation"] = needs_ai
    result["copilot_fallback"] = copilot_res
    result["copilot_issue"] = issue_res


def run_ci_auto_heal(
    repo_root: str,
    artifacts_dir: str,
    apply_patches: bool = False,
    verify_cmd: Optional[str] = None,
    out_pr: Optional[str] = None,
    run_id: Optional[str] = None,
    max_fixes: int = 5,
    create_pr: bool = False,
    base_branch: str = "main",
    error_log: Optional[str] = None,
    xml_path: Optional[str] = None,
    copilot_fallback: bool = False,
    copilot_issue: bool = False,
    out_copilot_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs CI failure ingestion, triage, bounded healing, verification, and PR drafting."""
    resolved_root = os.path.abspath(repo_root)
    collected = collect_ci_failures(
        artifacts_dir=artifacts_dir,
        error_log=error_log,
        xml_path=xml_path,
        repo_root=resolved_root,
    )
    failures = collected["failures"]

    if not failures:
        result: Dict[str, Any] = {
            "status": "NO_FAILURES_FOUND",
            "run_id": run_id,
            "failures_detected": 0,
            "planned_count": 0,
            "applied_count": 0,
            "skipped_cap_count": 0,
            "verified": False,
            "rolled_back": False,
            "planned_patches": [],
            "applied_patches": [],
            "skipped_aut_defects": [],
            "skipped_env_defects": [],
            "triage_breakdown": {
                "auto_fix_lint": 0,
                "locator_heal": 0,
                "ci_env_defect": 0,
                "aut_or_logic_defect": 0,
            },
            "needs_ai_escalation": False,
            "copilot_fallback": None,
            "copilot_issue": None,
            "pr_info": None,
        }
        if out_pr:
            os.makedirs(os.path.dirname(os.path.abspath(out_pr)), exist_ok=True)
            with open(out_pr, "w", encoding="utf-8") as f:
                f.write(_build_pr_markdown(result))
        return result

    patcher = AgentlessPatcher(repo_root=resolved_root)
    originals: Dict[str, str] = {}
    planned_patches: List[Dict[str, Any]] = []
    applied_patches: List[Dict[str, Any]] = []
    skipped_aut_defects: List[Dict[str, Any]] = []
    skipped_env_defects: List[Dict[str, Any]] = []
    unresolved_eligible: List[Dict[str, Any]] = []
    seen_lint_files = set()
    triage_breakdown: Dict[str, int] = {
        "auto_fix_lint": 0,
        "locator_heal": 0,
        "ci_env_defect": 0,
        "aut_or_logic_defect": 0,
    }
    skipped_cap_count = 0
    fix_cap = max(0, int(max_fixes))

    for failure in failures:
        triage = classify_failure(failure)
        triage_key = triage["category"].lower()
        if triage_key in triage_breakdown:
            triage_breakdown[triage_key] += 1
        if not triage["eligible"]:
            skipped_entry = {
                "tc": failure.get("tc", "unknown"),
                "file": failure.get("file", "UnknownFile"),
                "line": failure.get("line", "?"),
                "reason": failure.get("reason", ""),
                "category": triage["category"],
                "rationale": triage["rationale"],
            }
            if triage["category"] == CI_ENV_DEFECT:
                skipped_env_defects.append(skipped_entry)
            else:
                skipped_aut_defects.append(skipped_entry)
            continue

        if len(planned_patches) >= fix_cap:
            skipped_cap_count += 1
            unresolved_eligible.append(failure)
            continue

        target_file = _resolve_target_file(resolved_root, str(failure.get("file", "")))
        if not target_file or not os.path.isfile(target_file):
            unresolved_eligible.append(failure)
            continue

        try:
            line_no = int(str(failure.get("line", "1")))
        except ValueError:
            line_no = 1

        if target_file not in originals:
            try:
                with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                    originals[target_file] = f.read()
            except OSError:
                unresolved_eligible.append(failure)
                continue

        before_content = originals[target_file]
        lint_fixes: List[str] = []
        lint_diff = ""
        if target_file not in seen_lint_files:
            _, lint_fixes, lint_diff = generate_fixes_for_code(before_content, target_file)

        locator_plan: Optional[Dict[str, Any]] = None
        if triage["category"] == LOCATOR_HEAL:
            locator_plan = _plan_locator_patch(patcher, target_file, line_no)
            if not locator_plan:
                unresolved_eligible.append(failure)
                continue

        if not lint_fixes and not locator_plan:
            unresolved_eligible.append(failure)
            continue

        if lint_fixes:
            seen_lint_files.add(target_file)
            if triage_key != "auto_fix_lint":
                triage_breakdown["auto_fix_lint"] += 1

        patch_entry: Dict[str, Any] = {
            "file": target_file,
            "category": triage["category"],
            "tc": failure.get("tc", "unknown"),
            "lint_fixes": lint_fixes,
            "locator_patch": locator_plan,
            "summary": "; ".join(
                lint_fixes
                + ([f"Locator healed ({locator_plan['strategy']})"] if locator_plan else [])
            ),
            "diff": lint_diff,
        }
        planned_patches.append(patch_entry)

    if apply_patches and planned_patches:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for entry in planned_patches:
            grouped.setdefault(entry["file"], []).append(entry)
        for target_file, entries in grouped.items():
            diff_str = _apply_patches_for_file(
                target_file=target_file,
                before_content=originals[target_file],
                file_entries=entries,
            )
            if diff_str:
                for entry in entries:
                    entry["diff"] = diff_str
                    applied_patches.append(entry)

    verified = False
    rolled_back = False
    verify_output = ""

    if not apply_patches:
        if planned_patches:
            status = "DRY_RUN_PLANNED"
        elif skipped_env_defects and not skipped_aut_defects:
            status = "CI_ENV_DEFECTS_ONLY_NO_PATCH"
        else:
            status = "AUT_DEFECTS_ONLY_NO_PATCH"
    elif not applied_patches:
        if skipped_env_defects and not skipped_aut_defects:
            status = "CI_ENV_DEFECTS_ONLY_NO_PATCH"
        elif skipped_aut_defects:
            status = "AUT_DEFECTS_ONLY_NO_PATCH"
        else:
            status = "NO_ELIGIBLE_PATCHES"
    elif verify_cmd:
        verify_ok, verify_output = _run_verify_command(verify_cmd, resolved_root)
        if verify_ok:
            verified = True
            status = "HEALED_AND_VERIFIED"
        else:
            touched = {p["file"]: originals[p["file"]] for p in applied_patches if p["file"] in originals}
            rolled_back = _rollback_files(touched)
            status = "VERIFICATION_FAILED_ROLLED_BACK"
    else:
        verified = True
        status = "HEALED"

    result = {
        "status": status,
        "run_id": run_id,
        "failures_detected": len(failures),
        "planned_count": len(planned_patches),
        "applied_count": len(applied_patches),
        "skipped_cap_count": skipped_cap_count,
        "verified": verified,
        "rolled_back": rolled_back,
        "verify_output": verify_output[:1000] if verify_output else "",
        "planned_patches": planned_patches,
        "applied_patches": applied_patches,
        "skipped_aut_defects": skipped_aut_defects,
        "skipped_env_defects": skipped_env_defects,
        "triage_breakdown": triage_breakdown,
        "needs_ai_escalation": False,
        "copilot_fallback": None,
        "copilot_issue": None,
        "pr_info": None,
    }

    _apply_copilot_escalation(
        resolved_root=resolved_root,
        artifacts_dir=artifacts_dir,
        result=result,
        unresolved_eligible=unresolved_eligible,
        originals=originals,
        apply_patches=apply_patches,
        verify_cmd=verify_cmd,
        copilot_fallback=copilot_fallback,
        copilot_issue=copilot_issue,
        out_copilot_prompt=out_copilot_prompt,
        run_id=run_id,
    )

    pr_markdown = _build_pr_markdown(result)
    if out_pr:
        os.makedirs(os.path.dirname(os.path.abspath(out_pr)), exist_ok=True)
        with open(out_pr, "w", encoding="utf-8") as f:
            f.write(pr_markdown)

    if create_pr and apply_patches and result["applied_patches"] and result["verified"]:
        modified_files = sorted({p["file"] for p in result["applied_patches"]})
        result["pr_info"] = _create_heal_pr(
            repo_root=resolved_root,
            modified_files=modified_files,
            pr_body_path=out_pr,
            pr_markdown=pr_markdown,
            run_id=run_id,
            base_branch=base_branch,
        )

    return result


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser for ci_auto_healer."""
    parser = argparse.ArgumentParser(
        description="CI/CD Failure Detection, Triage & Safe Auto-Heal Bridge"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=os.getcwd(),
        help="Target repository root directory",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default="artifacts",
        help="Directory containing downloaded CI JUnit XML and log artifacts",
    )
    parser.add_argument(
        "--xml",
        type=str,
        default=None,
        help="Optional explicit path to a JUnit XML failure report",
    )
    parser.add_argument(
        "--error-log",
        type=str,
        default=None,
        help="Optional explicit path to a CI failure log file",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="GitHub Actions workflow run ID for reporting or fetching",
    )
    parser.add_argument(
        "--fetch-gh",
        action="store_true",
        help="Fetch failed CI logs and artifacts via GitHub CLI (`gh`)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply eligible Clean-POM patches on disk (default is dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and plan repairs without modifying files on disk",
    )
    parser.add_argument(
        "--max-fixes",
        type=int,
        default=5,
        help="Maximum number of eligible failures to patch per CI run",
    )
    parser.add_argument(
        "--verify-cmd",
        type=str,
        default=None,
        help="Verification command executed after patching (rolls back on failure)",
    )
    parser.add_argument(
        "--out-pr",
        type=str,
        default=None,
        help="Write generated Pull Request markdown body to this file",
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create an auto-heal branch, commit, push, and open a PR via `gh`",
    )
    parser.add_argument(
        "--base-branch",
        type=str,
        default="main",
        help="Base branch targeted when opening an auto-heal Pull Request",
    )
    parser.add_argument(
        "--copilot-fallback",
        action="store_true",
        help="Invoke GitHub Copilot CLI when deterministic healing leaves unresolved failures",
    )
    parser.add_argument(
        "--copilot-issue",
        action="store_true",
        help="Open a GitHub Issue assigned to @copilot for unresolved CI failures or AUT defects",
    )
    parser.add_argument(
        "--out-copilot-prompt",
        type=str,
        default=None,
        help="Write generated Copilot escalation prompt markdown to this file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON healing report",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for CI/CD Auto-Healer."""
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    artifacts_dir = (
        args.artifacts_dir
        if os.path.isabs(args.artifacts_dir)
        else os.path.join(repo_root, args.artifacts_dir)
    )
    run_id = args.run_id
    gh_fetch_info: Optional[Dict[str, Any]] = None

    if args.fetch_gh:
        gh_fetch_info = fetch_gh_failed_run(
            repo_root=repo_root,
            run_id=run_id,
            artifacts_dir=artifacts_dir,
        )
        if gh_fetch_info.get("run_id") and not run_id:
            run_id = gh_fetch_info["run_id"]

    should_apply = bool(args.apply and not args.dry_run)
    result = run_ci_auto_heal(
        repo_root=repo_root,
        artifacts_dir=artifacts_dir,
        apply_patches=should_apply,
        verify_cmd=args.verify_cmd,
        out_pr=args.out_pr,
        run_id=run_id,
        max_fixes=args.max_fixes,
        create_pr=args.create_pr,
        base_branch=args.base_branch,
        error_log=args.error_log,
        xml_path=args.xml,
        copilot_fallback=args.copilot_fallback,
        copilot_issue=args.copilot_issue,
        out_copilot_prompt=args.out_copilot_prompt,
    )
    if gh_fetch_info is not None:
        result["gh_fetch"] = gh_fetch_info

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"[{result['status']}] Failures: {result['failures_detected']} | "
            f"Applied: {result['applied_count']} | "
            f"Skipped AUT: {len(result['skipped_aut_defects'])} | "
            f"Skipped Env: {len(result.get('skipped_env_defects', []))}"
        )

    return 1 if result["status"] == "VERIFICATION_FAILED_ROLLED_BACK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
