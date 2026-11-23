#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/lint/plan_schema_sentinel.py — Spec-Driven Planning & Implementation Plan Linter
-------------------------------------------------------------------------------------
Mechanically enforces the Planning Pillars declared in AGENTS.md §5 & standards/qa-process/plan-protocol.md:
  [Standard Mode - 4 Pillars]:
    1. Strict Grounding: Repository context surveyed before planning.
    2. Mandatory 4-Part Structure:
       - Affected Files & Blast Radius
       - Data Flow & Interface Signatures
       - Atomic Milestones (Budget: <= 3 files per milestone)
       - Verification Matrix ("Define the Exam in the Plan")
    3. Non-Generic Assertions: Zero vague statements like "write unit tests".
  [Super Mode - /super-plan 6 Principles]:
    4. Execution DAG: Milestones define depends_on, with strict cycle detection.
    5. Milestone Circuit Breakers: Max fix attempts, scope guard, and rollback triggers.
    6. Line Anchors: Target files locked to specific line coordinates (Lxx-Lyy).
    7. Anti-Full-Code Invariant: Only signatures and schemas (no full algorithmic bodies).
    8. Tri-Vulnerability Red-Teaming: Explicit mitigation for Race, Boundary, and Blast Radius.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

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

REQUIRED_SECTIONS = [
    ("affected_files", re.compile(r"#+\s*(?:1[.\s]*)?Affected\s+Files", re.IGNORECASE)),
    ("data_flow", re.compile(r"#+\s*(?:2[.\s]*)?Data\s+Flow|Interface\s+Signatures", re.IGNORECASE)),
    ("atomic_milestones", re.compile(r"#+\s*(?:3[.\s]*)?Atomic\s+Milestones|Milestones", re.IGNORECASE)),
    ("verification_matrix", re.compile(r"#+\s*(?:4[.\s]*)?Verification\s+Matrix|Verification\s+Plan", re.IGNORECASE)),
]

FORBIDDEN_GENERIC_PATTERNS = [
    re.compile(r"\bwrite\s+(?:some\s+)?unit\s+tests?\s+to\s+verify\b", re.IGNORECASE),
    re.compile(r"\bviết\s+(?:các\s+)?unit\s+tests?\s+để\s+kiểm\s+tra\b", re.IGNORECASE),
    re.compile(r"\btest\s+xem\s+có\s+lỗi\s+không\b", re.IGNORECASE),
    re.compile(r"\bmanually\s+test\s+feature\b", re.IGNORECASE),
]

TEST_COMMAND_PATTERNS = [
    re.compile(r"`(?:pytest|npm test|npx playwright test|mvn test|python3?|ruff|jest|vitest)[^`]*`"),
    re.compile(r"\b(?:pytest|playwright|mvn test|npm test)\b"),
]

LINE_ANCHOR_PATTERNS = [
    re.compile(r"\(L\d+(?:-L?\d+)?\)", re.IGNORECASE),
    re.compile(r":L\d+(?:-L?\d+)?", re.IGNORECASE),
    re.compile(r"::[a-zA-Z0-9_.]+", re.IGNORECASE),
    re.compile(r"\(AST:\s*[^)]+\)", re.IGNORECASE),
    re.compile(r"\((?:New|Delete|Tạo mới|Xóa)\)", re.IGNORECASE),
]

VULNERABILITY_PATTERNS = [
    ("race_condition", re.compile(r"(?:race\s+condition|concurrency|idempotent|đồng\s+thời)", re.IGNORECASE)),
    ("boundary_resource", re.compile(r"(?:boundary|extreme|timeout|resource|rỗng|quá\s+tải)", re.IGNORECASE)),
    ("backward_compat", re.compile(r"(?:backward|compatibility|blast\s+radius|caller|tương\s+thích)", re.IGNORECASE)),
]

DANGEROUS_COMMAND_PATTERNS = [
    re.compile(r"\brm\s+-(?:rf?|fr?)\s+(?:/|/\*|~|\$HOME|\.\./\.\.)", re.IGNORECASE),
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:", re.IGNORECASE),
    re.compile(r"\b(?:mkfs|dd\s+if=)\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+-R\s+777\s+/", re.IGNORECASE),
    re.compile(r"\brm\s+-(?:rf?|fr?)\s+\.git\b", re.IGNORECASE),
]

HIDDEN_COUPLING_PATTERNS = [
    ("os.environ", re.compile(r"\bos\.environ\[", re.IGNORECASE)),
    ("process.env", re.compile(r"\bprocess\.env\.", re.IGNORECASE)),
    ("global variable", re.compile(r"\bglobal\s+[A-Za-z0-9_]+", re.IGNORECASE)),
    ("sys.modules", re.compile(r"\bsys\.modules\[", re.IGNORECASE)),
]


def validate_rollback_hook_safety(cmd: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a rollback hook command is syntactically safe and executable.
    Rejects catastrophic commands (rm -rf /, forkbombs, dd) and ensures binary exists on PATH.
    """
    if not cmd or not cmd.strip():
        return False, "Rollback hook command cannot be empty."

    cmd_clean = cmd.strip()
    for pat in DANGEROUS_COMMAND_PATTERNS:
        if pat.search(cmd_clean):
            return False, f"Dangerous command pattern detected in rollback hook: '{cmd_clean}'."

    parts = cmd_clean.split()
    if not parts:
        return False, "Empty rollback command."
    binary = parts[0]

    # Standard safe tools
    if binary in ("python", "python3", "pytest", "git", "npm", "npx", "node", "sh", "bash", "echo", "touch", "rm"):
        return True, None

    if shutil.which(binary):
        return True, None

    if os.path.isfile(binary) or (binary.startswith("./") and os.path.isfile(binary[2:])):
        return True, None

    return False, f"Binary or executable '{binary}' in rollback hook was not found on system PATH."


def scan_undeclared_couplings(block: str, node_id: str = "node") -> List[str]:
    """
    Scans milestone content for undeclared global/env state mutations that can cause
    race conditions or hidden side-effects, especially in [PARALLEL_OK] blocks.
    """
    issues = []
    is_parallel = bool(re.search(r"\[PARALLEL_OK\]", block, re.IGNORECASE))

    for name, pat in HIDDEN_COUPLING_PATTERNS:
        if pat.search(block):
            if is_parallel:
                issues.append(
                    f"Hidden State Mutation: Milestone '{node_id}' declares [PARALLEL_OK] "
                    f"but modifies shared global/env state ({name}). This causes non-deterministic race conditions."
                )
    return issues


def is_reachable(execution_graph: Dict[str, List[str]], start: str, target: str) -> bool:
    """Checks if target is reachable from start in execution graph (start executes before target)."""
    visited: Set[str] = set()
    queue: List[str] = [start]
    while queue:
        curr = queue.pop(0)
        if curr == target:
            return True
        for nxt in execution_graph.get(curr, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return False


def detect_dag_cycles(graph: Dict[str, List[str]]) -> List[str]:
    """Detects cycles in an execution DAG using depth-first search."""
    visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
    cycles: List[str] = []

    def dfs(node: str, path: List[str]) -> None:
        visited[node] = 1
        for dep in graph.get(node, []):
            if visited.get(dep, 0) == 1:
                cycles.append(" -> ".join(path + [dep]))
            elif visited.get(dep, 0) == 0:
                dfs(dep, path + [dep])
        visited[node] = 2

    for n in graph:
        if visited.get(n, 0) == 0:
            dfs(n, [n])

    return cycles


def verify_plan_ast_grounding(content: str, repo_root: str = _REPO_ROOT) -> Dict[str, Any]:
    """Pre-flight AST & File-System verification.

    Verifies that all files and target references declared as [MODIFY] or [DELETE]
    physically exist in the repository, stopping hallucinated files before execution.
    """
    lines = content.splitlines()
    target_files: List[Tuple[str, str]] = []

    for line in lines:
        if "|" in line:
            if "`[MODIFY]`" in line or "`[DELETE]`" in line or "[MODIFY]" in line or "[DELETE]" in line:
                m = re.findall(r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`", line)
                for f in m:
                    if not f.startswith(("pytest", "python", "[")):
                        target_files.append((f, "must_exist"))
            elif "`[CREATE]`" in line or "[CREATE]" in line:
                m = re.findall(r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`", line)
                for f in m:
                    if not f.startswith(("pytest", "python", "[")):
                        target_files.append((f, "can_be_new"))

    missing_files: List[str] = []
    checked_files = 0

    for fpath, rule in target_files:
        if rule == "can_be_new":
            continue
        # Exclude template placeholders
        if fpath.startswith(("[", "path/", "src/modules/target_module", "src/target_types", "src/caller", "obsolete/")):
            continue
        full_path = os.path.join(repo_root, fpath)
        checked_files += 1
        if not os.path.isfile(full_path):
            missing_files.append(fpath)

    return {
        "is_valid": len(missing_files) == 0,
        "missing_files": missing_files,
        "checked_files": checked_files,
    }


def validate_plan_content(
    content: str,
    filename: str = "plan.md",
    mode: str = "auto",
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validates markdown content against Spec-Driven Planning pillars.

    Args:
        content: Markdown string of the plan.
        filename: Label for reporting.
        mode: 'standard', 'super', or 'auto' (detects super mode if super keywords found).

    Returns:
        (passed, issues, details)
    """
    issues: List[str] = []

    # Auto-detect mode if requested
    is_super = mode == "super" or (
        mode == "auto" and bool(
            re.search(r"super-plan|Execution\s+DAG|Tri-Vulnerability|depends_on", content, re.IGNORECASE)
        )
    )

    details: Dict[str, Any] = {
        "file": filename,
        "mode": "super" if is_super else "standard",
        "sections_present": {},
        "milestones_checked": 0,
        "has_verification_commands": False,
        "forbidden_phrases_detected": [],
        "line_anchors_detected": 0,
        "circuit_breakers_detected": 0,
        "dag_nodes": [],
        "dag_cycles": [],
    }

    # Pillar 1 & 2: Check required sections
    for section_key, pattern in REQUIRED_SECTIONS:
        found = bool(pattern.search(content))
        details["sections_present"][section_key] = found
        if not found:
            issues.append(f"Missing mandatory section header matching '{section_key}' in {filename}")

    # Pillar 3: Atomic Milestones Budget Check (Max 3 files per milestone)
    milestone_blocks = re.findall(
        r"(###?\s*(?:Milestone\s*\d+|Chặng\s*\d+|Node\s*[A-Za-z0-9]+)[^\n]*.*?)(?=(?:###?\s*(?:Milestone\s*\d+|Chặng\s*\d+|Node\s*[A-Za-z0-9]+))|(?:\n##+\s+)|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    details["milestones_checked"] = len(milestone_blocks)
    dag_graph: Dict[str, List[str]] = {}
    node_ids: Set[str] = set()
    node_write_sets: Dict[str, Set[str]] = {}
    parallel_node_ids: Set[str] = set()
    node_consumes: Dict[str, Set[str]] = {}
    node_produces: Dict[str, Set[str]] = {}

    for idx, block in enumerate(milestone_blocks, 1):
        # Look for explicit Files Modified line or extract source file paths
        m_files = re.search(r"Files\s+Modified[^\n:]*:\s*([^\n]+)", block, re.IGNORECASE)
        if m_files:
            raw_splits = [f.strip("`* ") for f in m_files.group(1).split(",") if "." in f]
            source_files = [f for f in raw_splits if not re.match(r"^\d+\.\d+$", f) and not f.startswith(("pytest", "python"))]
        else:
            raw_files = re.findall(r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`", block)
            unique_files = list(set(raw_files))
            source_files = [f for f in unique_files if not re.match(r"^\d+\.\d+$", f) and not f.startswith(("pytest", "python"))]

        if len(source_files) > 3:
            issues.append(
                f"Milestone {idx} violates Atomic Milestone budget: modifies {len(source_files)} files "
                f"(max allowed is 3): {source_files}"
            )

        # Parse DAG Node ID and depends_on
        node_match = re.search(r"Node\s*ID:\s*`?([a-zA-Z0-9_\-]+)`?", block, re.IGNORECASE)
        node_id = node_match.group(1) if node_match else f"M{idx}"
        node_ids.add(node_id)
        details["dag_nodes"].append(node_id)

        # Extract write_set
        m_write = re.search(r"Write\s+Set[^\n:]*:\s*`?\[(.*?)\]`?", block, re.IGNORECASE)
        if m_write:
            write_files = {w.strip("`'\" ") for w in m_write.group(1).split(",") if w.strip()}
        else:
            write_files = set(source_files)
        node_write_sets[node_id] = write_files

        if re.search(r"\[PARALLEL_OK\]", block, re.IGNORECASE):
            parallel_node_ids.add(node_id)

        # Extract consumes / produces for Formal Contract Verification
        m_con = re.search(r"consumes[\s*_:`]*\[(.*?)\]", block, re.IGNORECASE)
        m_prod = re.search(r"produces[\s*_:`]*\[(.*?)\]", block, re.IGNORECASE)
        node_consumes[node_id] = set(re.findall(r"['\"]contract['\"]\s*:\s*['\"]([a-zA-Z0-9_]+)['\"]", m_con.group(1))) if m_con else set()
        node_produces[node_id] = set(re.findall(r"['\"]contract['\"]\s*:\s*['\"]([a-zA-Z0-9_]+)['\"]", m_prod.group(1))) if m_prod else set()

        # Hidden Coupling Sentinel: verify parallel nodes don't mutate global/env state
        coupling_issues = scan_undeclared_couplings(block, node_id)
        issues.extend(coupling_issues)

        # Rollback Hook Safety Guard
        m_hook = re.search(r"Rollback\s+Hook[^\n`]*?:\*?\*?\s*`?([^`\n\r]+)", block, re.IGNORECASE)
        if m_hook:
            hook_cmd = m_hook.group(1).strip("`*\"' ")
            is_safe, safety_reason = validate_rollback_hook_safety(hook_cmd)
            if not is_safe:
                issues.append(f"Milestone {idx} ({node_id}) defines unsafe or invalid Rollback Hook: {safety_reason}")

        # Super Mode checks per milestone
        if is_super:
            # Check Circuit Breaker
            if re.search(r"Circuit\s+Breaker", block, re.IGNORECASE):
                details["circuit_breakers_detected"] += 1
            else:
                issues.append(f"Milestone {idx} missing mandatory 'Circuit Breaker' definition (Max attempts / rollback trigger).")

            # Check Compute Tier Annotation
            if re.search(r"Compute\s+Tier|Model:", block, re.IGNORECASE):
                details["compute_tiers_detected"] = details.get("compute_tiers_detected", 0) + 1
            else:
                issues.append(f"Milestone {idx} missing 'Compute Tier:' annotation (e.g. `[Model: Flash | Thinking: Off]`).")

            deps_match = re.search(r"depends_on[\s*:`_]*\[(.*?)\]", block, re.IGNORECASE)
            if deps_match:
                deps_raw = deps_match.group(1).strip()
                deps = [d.strip().strip("`'\"") for d in deps_raw.split(",") if d.strip()]
                dag_graph[node_id] = deps
            else:
                dag_graph[node_id] = []
                issues.append(f"Milestone {idx} ({node_id}) missing explicit 'depends_on: [...]' DAG declaration.")

    # Super Mode DAG validation
    if is_super and dag_graph:
        # Build forward execution graph (dep -> node_id)
        execution_graph: Dict[str, List[str]] = {nid: [] for nid in node_ids}
        # Check referenced dependencies exist
        for nid, deps in dag_graph.items():
            for dep in deps:
                # Allow referencing either ID like 'M1' or 'Milestone 1'
                matched = any(dep.lower() in known.lower() or known.lower() in dep.lower() for known in node_ids)
                if not matched and not dep.startswith("Milestone"):
                    issues.append(f"DAG Node '{nid}' depends on unknown milestone '{dep}'.")
                else:
                    for known in node_ids:
                        if dep.lower() in known.lower() or known.lower() in dep.lower():
                            execution_graph[known].append(nid)

        # Check for cycles
        cycles = detect_dag_cycles(dag_graph)
        details["dag_cycles"] = cycles
        if cycles:
            issues.append(f"Circular dependency cycle detected in Execution DAG: {cycles}")

        # Check Parallel Write-Set Collisions between [PARALLEL_OK] nodes
        for u in parallel_node_ids:
            for v in parallel_node_ids:
                if u < v:
                    # Check if they are truly independent (neither executes before the other)
                    if not is_reachable(execution_graph, u, v) and not is_reachable(execution_graph, v, u):
                        overlap = node_write_sets.get(u, set()) & node_write_sets.get(v, set())
                        if overlap:
                            issues.append(
                                f"Parallel Collision detected between '{u}' and '{v}': both declare [PARALLEL_OK] "
                                f"but share write-set {sorted(list(overlap))}. Revoke [PARALLEL_OK] or sequence with depends_on."
                            )

        # Formal Contract Verification across DAG edges:
        # If node v consumes contract C, verify C is produced by an ancestor u or defined in Section 2
        defined_dtos = set(re.findall(r"\bclass\s+([a-zA-Z0-9_]+)", content))
        for v, consumed_set in node_consumes.items():
            for c in consumed_set:
                produced_by_ancestor = any(
                    is_reachable(execution_graph, u, v) and c in node_produces.get(u, set())
                    for u in node_ids if u != v
                )
                if not produced_by_ancestor and c not in defined_dtos:
                    issues.append(
                        f"Contract Disconnect: Milestone '{v}' consumes contract '{c}' which is neither "
                        f"produced by any prerequisite ancestor node in the DAG nor defined in Section 2 DTOs."
                    )

    # Pillar 4: Verification Matrix Determinism
    has_command = any(p.search(content) for p in TEST_COMMAND_PATTERNS)
    details["has_verification_commands"] = has_command
    if not has_command:
        issues.append(
            f"Verification Matrix in {filename} lacks concrete executable test commands (`pytest`, `npx playwright test`, etc.)"
        )

    # Check for forbidden generic assertions
    for pattern in FORBIDDEN_GENERIC_PATTERNS:
        match = pattern.search(content)
        if match:
            phrase = match.group(0)
            details["forbidden_phrases_detected"].append(phrase)
            issues.append(f"Forbidden generic test description detected in {filename}: '{phrase}'. Specify concrete input/output.")

    # Super Mode: Line Anchors check in Section 1
    if is_super:
        has_anchor = any(p.search(content) for p in LINE_ANCHOR_PATTERNS)
        if has_anchor:
            details["line_anchors_detected"] += 1
        else:
            issues.append(f"Super-Plan in {filename} requires explicit Line Anchors (e.g. `file.py (L45-L60)` or `(New)`).")

        # Super Mode: Tri-Vulnerability Self-Critique
        vuln_section = bool(re.search(r"#+\s*(?:5[.\s]*)?(?:Tri-Vulnerability|Vulnerability|Lỗ hổng|Red-Teaming)", content, re.IGNORECASE))
        if not vuln_section:
            issues.append(f"Super-Plan in {filename} missing mandatory 'Tri-Vulnerability Self-Critique' section.")
        else:
            for v_name, v_pat in VULNERABILITY_PATTERNS:
                if not v_pat.search(content):
                    issues.append(f"Tri-Vulnerability section missing analysis for category: '{v_name}'.")

        # Super Mode: AST Pre-flight Grounding
        ast_result = verify_plan_ast_grounding(content)
        details["ast_grounding"] = ast_result
        if not ast_result["is_valid"]:
            issues.append(
                f"AST Pre-flight failed: Plan references non-existent files on disk: {ast_result['missing_files']}. "
                "Ensure target files exist or are explicitly tagged with (New) or [CREATE]."
            )
    else:
        # Standard mode: record warnings only
        ast_result = verify_plan_ast_grounding(content)
        details["ast_grounding"] = ast_result
        if not ast_result["is_valid"]:
            details["warnings"] = [f"Warning: Non-existent files referenced: {ast_result['missing_files']}"]

    passed = len(issues) == 0
    return passed, issues, details


def lint_plan_file(filepath: str, mode: str = "auto") -> Tuple[bool, List[str], Dict[str, Any]]:
    """Lints a specific plan file from disk."""
    if not os.path.isfile(filepath):
        return False, [f"File does not exist: {filepath}"], {"file": filepath, "exists": False}
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return validate_plan_content(content, filename=filepath, mode=mode)
    except Exception as e:
        return False, [f"Error reading {filepath}: {e}"], {"file": filepath, "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Spec-Driven Planning Sentinel (AGENTS.md §5 / plan-protocol.md)")
    parser.add_argument("--file", help="Path to markdown plan to validate")
    parser.add_argument("--mode", choices=["standard", "super", "auto"], default="auto", help="Validation mode")
    parser.add_argument("--check-templates", action="store_true", help="Validates built-in templates")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    target_files: List[str] = []
    if args.check_templates:
        tmpl = os.path.join(_REPO_ROOT, "templates", "test-plan", "spec-driven-plan-template.md")
        if os.path.isfile(tmpl):
            target_files.append(tmpl)

    if args.file:
        target_files.append(args.file)

    if not target_files:
        tmpl = os.path.join(_REPO_ROOT, "templates", "test-plan", "spec-driven-plan-template.md")
        if os.path.isfile(tmpl):
            target_files.append(tmpl)
        else:
            parser.print_help()
            return 1

    all_passed = True
    results: List[Dict[str, Any]] = []

    for fpath in target_files:
        passed, issues, details = lint_plan_file(fpath, mode=args.mode)
        if not passed:
            all_passed = False
        results.append({
            "file": fpath,
            "passed": passed,
            "issues": issues,
            "details": details,
        })

    if args.json:
        print(json.dumps({"passed": all_passed, "results": results}, indent=2))
        return 0 if all_passed else 1

    for res in results:
        status_str = "PASS" if res["passed"] else "FAIL"
        mode_str = res["details"].get("mode", "standard").upper()
        print(f"[{status_str}] [{mode_str}] {os.path.basename(res['file'])}")
        if not res["passed"]:
            for issue in res["issues"]:
                print(f"  - [X] {issue}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
