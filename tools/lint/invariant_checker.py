#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/lint/invariant_checker.py — Mechanical Invariant Sentinel
--------------------------------------------------------------
Inspired by UNICEF ADT-Studio INVARIANTS.md:
"Principles that only live in prose do not survive agent throughput. Every row here names a check."
Deterministically evaluates the 14 AGENTS.md invariants against codebase truth.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def check_rule_1_utf8(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 1: Zero BOM bytes across repo files."""
    violations: List[Dict[str, Any]] = []
    bom = b"\xef\xbb\xbf"
    ignored_dirs = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "node_modules", "reference_repos", "allure-report"}
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".sandbox")]
        for f in files:
            if f.endswith((".py", ".ts", ".js", ".json", ".md", ".groovy", ".yaml", ".yml")):
                p = os.path.join(root, f)
                try:
                    with open(p, "rb") as fp:
                        if fp.read(3) == bom:
                            rel_p = os.path.relpath(p, repo_root)
                            violations.append({
                                "rule": 1,
                                "name": "UTF-8 No BOM",
                                "file": rel_p,
                                "message": f"BOM bytes (0xEF, 0xBB, 0xBF) detected at start of file: {rel_p}",
                            })
                except OSError:
                    continue
    return violations


def check_rule_2_truth_anchor(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 2: Zero fake passes / dummy pass suppression."""
    violations: List[Dict[str, Any]] = []
    tests_dir = os.path.join(repo_root, "tests")
    if not os.path.isdir(tests_dir):
        return violations

    fake_pattern = re.compile(r"^\s*(?:const\s+_\s*=\s*e|_\s*=\s*(?:err|False)|pass\s*#\s*fake-pass)", re.MULTILINE)
    # Exclude files that test the fake-pass linter itself
    excluded_files = {"test_infer_linter.py", "test_invariant_checker.py"}
    for root, dirs, files in os.walk(tests_dir):
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        for f in files:
            if f in excluded_files:
                continue
            if f.endswith((".py", ".ts", ".js")):
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as fp:
                        content = fp.read()
                        if fake_pattern.search(content):
                            rel_p = os.path.relpath(p, repo_root)
                            violations.append({
                                "rule": 2,
                                "name": "Truth Anchor (Zero Fake Passes)",
                                "file": rel_p,
                                "message": f"Suspicious fake-pass or exception-swallowing dummy suppression in {rel_p}",
                            })
                except OSError:
                    continue
    return violations


def check_rule_3_dynamic_waits(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 3: Dynamic Smart Waits Only (no static sleep in test scripts)."""
    violations: List[Dict[str, Any]] = []
    # Identify test directories to scan based on hub vs client mode
    is_hub = os.path.isfile(os.path.join(repo_root, "tools", "core", "verify_all.py"))
    candidate_dirs: List[str] = []
    if is_hub:
        # In hub source repo, only automation scripts in tests/e2e and Scripts are subject to Invariant 3
        e2e_dir = os.path.join(repo_root, "tests", "e2e")
        scripts_dir = os.path.join(repo_root, "Scripts")
        for d in (e2e_dir, scripts_dir):
            if os.path.isdir(d):
                candidate_dirs.append(d)
    else:
        for folder in ("tests", "Scripts", "cypress", "e2e"):
            d = os.path.join(repo_root, folder)
            if os.path.isdir(d):
                candidate_dirs.append(d)

    if not candidate_dirs:
        return violations

    sleep_pattern = re.compile(r"\b(?:time\.sleep|Thread\.sleep|waitForTimeout)\s*\(")
    for scan_dir in candidate_dirs:
        for root, dirs, files in os.walk(scan_dir):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            for f in files:
                if f.endswith((".py", ".ts", ".js", ".groovy")):
                    p = os.path.join(root, f)
                    try:
                        with open(p, "r", encoding="utf-8", errors="replace") as fp:
                            for line_idx, line in enumerate(fp, 1):
                                if sleep_pattern.search(line):
                                    # check for allowed exemption comment
                                    if "synapse-ignore: STATIC_SLEEP" in line:
                                        continue
                                    rel_p = os.path.relpath(p, repo_root)
                                    violations.append({
                                        "rule": 3,
                                        "name": "Dynamic Smart Waits Only",
                                        "file": rel_p,
                                        "line": line_idx,
                                        "message": f"Static sleep detected in test file: {rel_p}:{line_idx}",
                                    })
                    except OSError:
                        continue
    return violations


def check_rule_5_credentials(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 5: Strict Credential Security."""
    violations: List[Dict[str, Any]] = []
    p1 = "BEGIN " + "RSA PRIVATE KEY"
    p2 = "BEGIN " + "OPENSSH PRIVATE KEY"
    secret_pattern = re.compile(rf"(?:{p1}|{p2}|ghp_[A-Za-z0-9]{{36}}|xoxb-[0-9]{{11}})")
    ignored_dirs = {".git", ".mypy_cache", ".pytest_cache", "node_modules", "reference_repos", "build", "dist", ".venv", "Reports", "reports", "allure-report"}
    scanner_exemptions = {
        "tools/lint/invariant_checker.py",
        "tools/lint/git_pre_commit_guard.py",
        "tests/test_git_pre_commit_guard.py",
        "tools/core/author_integrity.py",
    }
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".sandbox")]
        for f in files:
            if f.endswith((".py", ".ts", ".json", ".md", ".env", ".yaml", ".yml")):
                p = os.path.join(root, f)
                rel_p = os.path.relpath(p, repo_root)
                norm_p = rel_p.replace("\\", "/")
                if norm_p in scanner_exemptions or rel_p in scanner_exemptions:
                    continue
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as fp:
                        content = fp.read()
                        if secret_pattern.search(content):
                            violations.append({
                                "rule": 5,
                                "name": "Strict Credential Security",
                                "file": rel_p,
                                "message": f"Potential raw credential / private key in {rel_p}",
                            })
                except OSError:
                    continue
    return violations


def check_rule_10_author_defense(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 10: Anti-Plagiarism & Author Defense (Thế Vị / @TeeVee98)."""
    violations: List[Dict[str, Any]] = []
    license_path = os.path.join(repo_root, "LICENSE")
    if os.path.isfile(license_path):
        with open(license_path, "r", encoding="utf-8", errors="replace") as f:
            lic = f.read()
            if "Thế Vị" not in lic and "@TeeVee98" not in lic:
                violations.append({
                    "rule": 10,
                    "name": "Anti-Plagiarism & Author Defense",
                    "file": "LICENSE",
                    "message": "Author attribution (Thế Vị / @TeeVee98) missing from LICENSE",
                })
    else:
        violations.append({
            "rule": 10,
            "name": "Anti-Plagiarism & Author Defense",
            "file": "LICENSE",
            "message": "LICENSE file is missing",
        })
    return violations


def check_rule_11_ratchet(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 11: The Ratchet Invariant sensor, coverage floor, and lockfile deduplication check."""
    violations: List[Dict[str, Any]] = []
    ratchet_tool = os.path.join(repo_root, "tools", "lint", "ratchet_sentinel.py")
    if not os.path.isfile(ratchet_tool):
        violations.append({
            "rule": 11,
            "name": "The Ratchet Invariant",
            "file": "tools/lint/ratchet_sentinel.py",
            "message": "ratchet_sentinel.py sensor is missing from tools/lint/",
        })

    # Enforce zero duplicate .skill-lock.json
    dup_lock = os.path.join(repo_root, ".skill-lock.json")
    if os.path.isfile(dup_lock):
        violations.append({
            "rule": 11,
            "name": "The Ratchet Invariant",
            "file": ".skill-lock.json",
            "message": "Duplicate lockfile .skill-lock.json must not exist alongside canonical skills-lock.json",
        })

    # Verify pyproject.toml coverage floor is not weakened below 60%
    pyproject_path = os.path.join(repo_root, "pyproject.toml")
    if os.path.isfile(pyproject_path):
        try:
            with open(pyproject_path, "r", encoding="utf-8", errors="replace") as pf:
                py_text = pf.read()
            m_cov = re.search(r"fail_under\s*=\s*(\d+(?:\.\d+)?)", py_text)
            if m_cov and float(m_cov.group(1)) < 60.0:
                violations.append({
                    "rule": 11,
                    "name": "The Ratchet Invariant",
                    "file": "pyproject.toml",
                    "message": f"Coverage ratchet weakened: fail_under={m_cov.group(1)} < 60.0",
                })
        except OSError as err:
            violations.append({
                "rule": 11,
                "name": "The Ratchet Invariant",
                "file": "pyproject.toml",
                "message": f"Unable to read pyproject.toml for coverage ratchet check: {err}",
            })
    return violations


def check_rule_16_english_codebase(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 16: Bilingual Discipline & English-Only Codebase/Rules (Rule 2.4).
    Scans AGENTS.md, CLAUDE.md, .cursor/rules/*.mdc, and .agent/rules/* for non-whitelisted Vietnamese text.
    Exemptions: Author attribution (Thế Vị / @TeeVee98) and explicit bilingual translation files (*.vi.md).
    """
    violations: List[Dict[str, Any]] = []
    vietnamese_pattern = re.compile(
        r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
        re.IGNORECASE
    )

    # 1. Check prompt & rule documentation files (must be strictly English)
    rule_files: List[str] = []
    for top_rule in ("AGENTS.md", "CLAUDE.md"):
        p_rule = os.path.join(repo_root, top_rule)
        if os.path.isfile(p_rule):
            rule_files.append(p_rule)

    for rel_dir, exts in ((os.path.join(".agent", "rules"), (".md",)), (os.path.join(".cursor", "rules"), (".mdc", ".md"))):
        rules_dir = os.path.join(repo_root, rel_dir)
        if os.path.isdir(rules_dir):
            for rf in sorted(os.listdir(rules_dir)):
                if rf.endswith(exts) and not rf.endswith(".vi.md"):
                    rule_files.append(os.path.join(rules_dir, rf))

    for tree_dir in ("standards", "testing", os.path.join(".agents", "policies")):
        abs_tree = os.path.join(repo_root, tree_dir)
        if os.path.isdir(abs_tree):
            for r_root, r_dirs, r_files in os.walk(abs_tree):
                r_dirs[:] = [d for d in r_dirs if d not in {"examples", "__pycache__"}]
                for rf in sorted(r_files):
                    if rf.endswith(".md") and not rf.endswith(".vi.md"):
                        rule_files.append(os.path.join(r_root, rf))

    skills_dir = os.path.join(repo_root, "skills")
    if os.path.isdir(skills_dir):
        for r, _, fs in os.walk(skills_dir):
            for f in sorted(fs):
                if f.endswith(".sh"):
                    rule_files.append(os.path.join(r, f))

    for p in rule_files:
        rel_p = os.path.relpath(p, repo_root)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fp:
                for line_idx, line in enumerate(fp, 1):
                    cleaned = re.sub(r"Thế\s+Vị", "", line)
                    cleaned = re.sub(r"TeeVee98", "", cleaned)
                    if "synapse-ignore: VIETNAMESE" in line or "synapse-ignore: NON_ENGLISH" in line:
                        continue
                    if vietnamese_pattern.search(cleaned):
                        violations.append({
                            "rule": 16,
                            "name": "English-Only Codebase & Rules (Bilingual Discipline)",
                            "file": rel_p,
                            "line": line_idx,
                            "message": f"Non-English text detected in rule file: {rel_p}:{line_idx}",
                            "snippet": line.strip()[:80]
                        })
        except OSError:
            continue

    return violations


def check_rule_7_skills(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 7: Skill-First Hard Blocker & skills_manifest / skills_index path parity."""
    violations: List[Dict[str, Any]] = []
    router_path = os.path.join(repo_root, "tools", "core", "skill_router.py")
    if not os.path.isfile(router_path):
        violations.append({
            "rule": 7,
            "name": "Skill-First Hard Blocker",
            "file": "tools/core/skill_router.py",
            "message": "skill_router.py sensor is missing from tools/core/",
        })
    manifest_path = os.path.join(repo_root, "skills_manifest.json")
    if not os.path.isfile(manifest_path):
        violations.append({
            "rule": 7,
            "name": "Skill-First Hard Blocker",
            "file": "skills_manifest.json",
            "message": "skills_manifest.json is missing from repo root",
        })
        return violations
    manifest_ids = set()
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        skills = data.get("skills", [])
        if not skills:
            violations.append({
                "rule": 7,
                "name": "Skill-First Hard Blocker",
                "file": "skills_manifest.json",
                "message": "skills_manifest.json contains no skills entries",
            })
        for s in skills:
            sid = s.get("id")
            sp = s.get("path", "")
            if not sid or not sp:
                continue
            manifest_ids.add(sid)
            skill_md = os.path.join(repo_root, sp)
            if not os.path.isfile(skill_md):
                violations.append({
                    "rule": 7,
                    "name": "Skill-First Hard Blocker",
                    "file": sp,
                    "message": f"Skill '{sid}' indexed in skills_manifest.json is missing its SKILL.md file at {sp}",
                })
    except Exception as e:
        violations.append({
            "rule": 7,
            "name": "Skill-First Hard Blocker",
            "file": "skills_manifest.json",
            "message": f"Malformed skills_manifest.json: {e}",
        })

    # Verify skills_index.json embeds valid physical path for every skill (Turn-1 zero-hop guarantee)
    index_path = os.path.join(repo_root, "skills_index.json")
    if os.path.isfile(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as idxf:
                idx_data = json.load(idxf)
            idx_skills = idx_data.get("skills", [])
            idx_ids = set()
            for item in idx_skills:
                sid = item.get("id", "")
                ipath = item.get("path", "")
                if sid:
                    idx_ids.add(sid)
                if not ipath or not os.path.isfile(os.path.join(repo_root, ipath)):
                    violations.append({
                        "rule": 7,
                        "name": "Skill-First Hard Blocker",
                        "file": "skills_index.json",
                        "message": f"Skill '{sid}' in skills_index.json has missing or invalid path '{ipath}'",
                    })
            if manifest_ids and idx_ids != manifest_ids:
                violations.append({
                    "rule": 7,
                    "name": "Skill-First Hard Blocker",
                    "file": "skills_index.json",
                    "message": f"skills_index.json ID parity mismatch with skills_manifest.json (index={len(idx_ids)}, manifest={len(manifest_ids)})",
                })
        except Exception as e:
            violations.append({
                "rule": 7,
                "name": "Skill-First Hard Blocker",
                "file": "skills_index.json",
                "message": f"Malformed skills_index.json: {e}",
            })
    return violations


def check_rule_17_adversarial_audit(repo_root: str) -> List[Dict[str, Any]]:
    """Invariant 17: Mandatory Adversarial Self-Audit sensor existence."""
    violations: List[Dict[str, Any]] = []
    runner_path = os.path.join(repo_root, "tools", "orchestration", "solo_runner.py")
    if not os.path.isfile(runner_path):
        violations.append({
            "rule": 17,
            "name": "Mandatory Adversarial Self-Audit",
            "file": "tools/orchestration/solo_runner.py",
            "message": "solo_runner.py is missing from tools/orchestration/",
        })
    return violations


def check_rule_generic(rule_num: int, repo_root: str) -> List[Dict[str, Any]]:
    """Generic check verifying designated sensors / specs exist."""
    violations: List[Dict[str, Any]] = []
    invariants_doc = os.path.join(repo_root, "docs", "INVARIANTS.md")
    if not os.path.isfile(invariants_doc):
        violations.append({
            "rule": rule_num,
            "name": f"Invariant {rule_num}",
            "file": "docs/INVARIANTS.md",
            "message": "Formal docs/INVARIANTS.md matrix registry is missing",
        })
    return violations


CHECKERS = {
    1: check_rule_1_utf8,
    2: check_rule_2_truth_anchor,
    3: check_rule_3_dynamic_waits,
    5: check_rule_5_credentials,
    7: check_rule_7_skills,
    10: check_rule_10_author_defense,
    11: check_rule_11_ratchet,
    16: check_rule_16_english_codebase,
    17: check_rule_17_adversarial_audit,
}


def evaluate_invariants(
    repo_root: Optional[str] = None,
    rule_scope: Optional[int] = None,
    invariants_doc: str = "docs/INVARIANTS.md",
) -> Tuple[Dict[str, Any], int]:
    """Evaluates requested or all invariants and returns report dict and exit code."""
    root = os.path.abspath(repo_root or _REPO_ROOT)
    doc_path = os.path.join(root, invariants_doc) if not os.path.isabs(invariants_doc) else invariants_doc

    all_violations: List[Dict[str, Any]] = []
    rules_to_check = [rule_scope] if rule_scope is not None else [1, 2, 3, 5, 7, 10, 11, 16, 17]

    for r in rules_to_check:
        checker = CHECKERS.get(r, lambda rp, rn=r: check_rule_generic(rn, rp))
        violations = checker(root)
        all_violations.extend(violations)

    status = "PASS" if not all_violations else "VIOLATIONS_DETECTED"
    exit_code = 0 if not all_violations else 1

    report = {
        "status": status,
        "rules_checked": len(rules_to_check),
        "invariants_doc": doc_path,
        "violations_count": len(all_violations),
        "violations": all_violations,
    }
    return report, exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mechanical Invariant Sentinel (Invariant Registry Sensor)")
    parser.add_argument("--rule", type=int, default=None, help="Check a specific invariant rule (1-17)")
    parser.add_argument("--invariants-doc", type=str, default="docs/INVARIANTS.md", help="Path to formal invariants registry")
    parser.add_argument("--json", action="store_true", help="Output pure JSON report")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    report, exit_code = evaluate_invariants(
        repo_root=_REPO_ROOT,
        rule_scope=args.rule,
        invariants_doc=args.invariants_doc,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if report["status"] == "PASS":
            print(f"[PASS] All {report['rules_checked']} checked invariant(s) mechanically verified clean.")
        else:
            print(f"[VIOLATIONS DETECTED] Found {report['violations_count']} violation(s) across {report['rules_checked']} rule(s):")
            for v in report["violations"]:
                loc = f"{v.get('file', '')}:{v.get('line', '')}" if v.get("line") else v.get("file", "")
                print(f"  - Rule {v['rule']} ({v['name']}) at {loc}: {v['message']}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
