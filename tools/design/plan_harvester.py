#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/design/plan_harvester.py — Architecture Decision Record (ADR) Plan Harvester
-----------------------------------------------------------------------------------
Harvests verified spec-driven implementation plans (after passing 10/11 DoD gates)
into permanent Architecture Decision Records in docs/adr/ADR-xxxx-[title].md.
Prevents architectural amnesia and serves as the grounding reference for future /plan invocations.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
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

from tools.context.polyglot_ast_parser import parse_polyglot_signatures

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


def slugify(text: str) -> str:
    """Converts a title into a clean URL-friendly and filename-friendly ASCII slug."""
    import unicodedata
    # Normalize unicode to decomposed form and remove non-ASCII accents
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "unnamed-decision"


def get_next_adr_index(adr_dir: str) -> int:
    """Determines the next sequential 4-digit ADR index in adr_dir."""
    existing_files = glob.glob(os.path.join(adr_dir, "ADR-[0-9][0-9][0-9][0-9]-*.md"))
    max_idx = 0
    for f in existing_files:
        basename = os.path.basename(f)
        m = re.match(r"ADR-(\d{4})-", basename)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def parse_plan(content: str) -> Dict[str, Any]:
    """Parses key sections from an implementation plan."""
    # 1. Extract Title
    title_match = re.search(r"^#+\s*(?:Spec-Driven\s+Implementation\s+Plan|Plan):\s*(.*?)$", content, re.MULTILINE | re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "Architectural Decision"
    title = title.strip("[]")

    # 2. Extract Context / Affected Files
    context_match = re.search(
        r"(?:##+\s*(?:1[.\s]*)?Affected\s+Files[^\n]*)(.*?)(?=(?:##+\s*(?:2[.\s]*)?Data\s+Flow)|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    context_text = context_match.group(1).strip() if context_match else "No context extracted."

    # 3. Extract Decision / Interface Signatures
    decision_match = re.search(
        r"(?:##+\s*(?:2[.\s]*)?Data\s+Flow[^\n]*)(.*?)(?=(?:##+\s*(?:3[.\s]*)?Atomic\s+Milestones)|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    decision_text = decision_match.group(1).strip() if decision_match else "No interface signatures extracted."

    # 4. Extract Tri-Vulnerability Self-Critique
    vuln_match = re.search(
        r"(?:##+\s*(?:5[.\s]*)?(?:Tri-Vulnerability|Vulnerability|Lỗ hổng|Red-Teaming)[^\n]*)(.*?)(?=(?:##+\s*(?:6[.\s]*)?Execution|\Z))",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    vuln_text = vuln_match.group(1).strip() if vuln_match else "Standard QA Hub invariants and circuit breakers applied."

    return {
        "title": title,
        "context": context_text,
        "decision": decision_text,
        "mitigations": vuln_text,
    }


def format_adr(
    index: int,
    parsed: Dict[str, Any],
    source_file: str,
    status: str = "Accepted (DoD Certified)",
    date_str: Optional[str] = None,
    calibration: Optional[Dict[str, Any]] = None,
) -> str:
    """Formats parsed plan data into standard Markdown Architecture Decision Record (MADR)."""
    if not date_str:
        date_str = datetime.date.today().isoformat()

    idx_str = f"{index:04d}"
    title = parsed["title"]

    calibration_block = ""
    if calibration:
        unplanned_str = ", ".join(f"`{f}`" for f in calibration.get("unplanned_files", [])) if calibration.get("unplanned_files") else "None (100% Plan Accuracy)"
        sem_acc = calibration.get("semantic_accuracy_score", 1.0) * 100
        sem_drift = calibration.get("semantic_drift_ratio", 0.0)
        calibration_block = f"""
---

## Plan Calibration & Drift Analysis
- **Plan File Accuracy Score:** {calibration.get("accuracy_score", 1.0) * 100:.1f}%
- **Plan File Drift Ratio:** {calibration.get("drift_ratio", 0.0)}
- **Semantic Contract Accuracy Score:** {sem_acc:.1f}%
- **Semantic Contract Drift Ratio:** {sem_drift}
- **Composite Plan Accuracy Score:** {calibration.get("composite_accuracy_score", calibration.get("accuracy_score", 1.0)) * 100:.1f}%
- **Unplanned Files ({len(calibration.get('unplanned_files', []))}):** {unplanned_str}
"""

    return f"""<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-{idx_str}: {title}

- **Status:** {status}
- **Date:** {date_str}
- **Source Plan:** `{os.path.basename(source_file)}`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement
{parsed["context"]}

---

## Decision Drivers & Invariants
- Grounding Principle: "Read First – Plan Later" (AGENTS.md §5).
- Zero Fake-Passes Invariant & Deterministic Verification Matrix.
- Execution DAG with Milestone Circuit Breakers & Clean Context Handoff.

---

## Considered Options & Architectural Decision
{parsed["decision"]}

---

## Vulnerability Self-Critique & Mitigation Strategies
{parsed["mitigations"]}

---

## Consequences & Guarantees
- **Positive:** Sealed interface contracts, zero-regression blast radius, idempotent execution.
- **Negative / Constraints:** Strict adherence to atomic milestone budget (<= 3 files) and type contracts.{calibration_block}
"""


def calibrate_plan_against_git(plan_content: str, repo_root: str = _REPO_ROOT) -> Dict[str, Any]:
    """Compares planned target files against git status/diff to measure Plan Drift."""
    import subprocess

    planned_files: List[str] = []
    for line in plan_content.splitlines():
        if "|" in line and any(tag in line for tag in ("[MODIFY]", "[CREATE]", "[DELETE]")):
            m = re.findall(r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`", line)
            for f in m:
                if not f.startswith(("pytest", "python", "[")):
                    norm_f = f.replace("\\", "/").strip()
                    if norm_f not in planned_files:
                        planned_files.append(norm_f)

    actual_files: List[str] = []
    try:
        cmd = ["git", "diff", "--name-only", "HEAD"]
        res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
        for l in res.stdout.strip().splitlines():
            nl = l.replace("\\", "/").strip()
            if nl and nl not in actual_files and not nl.startswith((".git", "docs/adr")):
                actual_files.append(nl)

        res_un = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True, check=False)
        for l in res_un.stdout.splitlines():
            if l.startswith("?? "):
                nl = l[3:].replace("\\", "/").strip()
                if nl and nl not in actual_files and not nl.startswith((".git", "docs/adr", "scratch")):
                    actual_files.append(nl)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

    unplanned_files = [
        f for f in actual_files
        if f not in planned_files and not f.endswith("implementation_plan.md") and not f.startswith("docs/adr")
    ]
    drift_ratio = len(unplanned_files) / max(len(actual_files), 1) if actual_files else 0.0
    accuracy_score = max(0.0, 1.0 - drift_ratio)

    # Measure Deep Semantic Contract Drift (Polyglot AST interface hashing & arity comparison)
    planned_symbols: List[str] = []
    planned_arities: Dict[str, int] = {}
    planned_signatures: Dict[str, str] = {}
    planned_hashes: Dict[str, str] = {}

    fn_pat = re.compile(r"\b(?:def|function)\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)(?:\s*->\s*([a-zA-Z0-9_\[\], \.]+))?")
    for m in fn_pat.finditer(plan_content):
        s_name = m.group(1)
        if not s_name.startswith("test_") and s_name not in planned_symbols:
            planned_symbols.append(s_name)
            args = [
                a.strip().split(":")[0].strip()
                for a in m.group(2).split(",")
                if a.strip() and a.strip() not in ("self", "cls", "this")
            ]
            planned_arities[s_name] = len(args)
            norm_sig = re.sub(r"\s+", " ", m.group(0).strip())
            planned_signatures[s_name] = norm_sig
            planned_hashes[s_name] = hashlib.sha256(norm_sig.encode("utf-8")).hexdigest()[:8]

    cls_pat = re.compile(r"\b(?:class|interface)\s+([a-zA-Z0-9_]+)")
    for m in cls_pat.finditer(plan_content):
        c_name = m.group(1)
        if not c_name.startswith("Test") and c_name not in planned_symbols:
            planned_symbols.append(c_name)
            planned_signatures[c_name] = f"class {c_name}"
            planned_hashes[c_name] = hashlib.sha256(f"class {c_name}".encode("utf-8")).hexdigest()[:8]

    drifted_symbols: List[str] = []
    if planned_symbols and planned_files:
        all_real_symbols: Dict[str, Dict[str, Any]] = {}
        all_short_symbols: Dict[str, Dict[str, Any]] = {}
        for pf in planned_files:
            full_pf = os.path.join(repo_root, pf)
            if os.path.isfile(full_pf):
                try:
                    res = parse_polyglot_signatures(full_pf)
                    for s in res.get("symbols", []):
                        all_real_symbols[s["name"]] = s
                        all_short_symbols[s["name"].split(".")[-1]] = s
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass

        for sym in planned_symbols:
            matched_s = all_real_symbols.get(sym) or all_short_symbols.get(sym)
            if not matched_s:
                drifted_symbols.append(sym)
            elif sym in planned_arities:
                sig = matched_s.get("signature", "")
                m_args = re.search(r"\(([^)]*)\)", sig)
                if m_args:
                    actual_args = [
                        a.strip().split(":")[0].strip()
                        for a in m_args.group(1).split(",")
                        if a.strip() and a.strip() not in ("self", "cls", "this")
                    ]
                    if len(actual_args) != planned_arities[sym]:
                        drift_desc = f"{sym} (arity drift: planned {planned_arities[sym]}, got {len(actual_args)})"
                        drifted_symbols.append(drift_desc)
                    else:
                        # Hash comparison for exact type / signature drift
                        real_norm_sig = re.sub(r"\s+", " ", sig.strip())
                        real_h = hashlib.sha256(real_norm_sig.encode("utf-8")).hexdigest()[:8]
                        p_hash = planned_hashes.get(sym)
                        if p_hash and real_h != p_hash:
                            drift_desc = f"{sym} (signature hash drift: planned {p_hash}, got {real_h})"
                            drifted_symbols.append(drift_desc)

    semantic_drift_ratio = round(len(drifted_symbols) / max(len(planned_symbols), 1), 3) if planned_symbols else 0.0
    semantic_accuracy_score = round(max(0.0, 1.0 - semantic_drift_ratio), 3)
    composite_accuracy = round(0.5 * accuracy_score + 0.5 * semantic_accuracy_score, 3)
    composite_drift = round(max(0.0, 1.0 - composite_accuracy), 3)

    return {
        "planned_files": planned_files,
        "actual_files": actual_files,
        "unplanned_files": unplanned_files,
        "drift_ratio": round(drift_ratio, 3),
        "accuracy_score": round(accuracy_score, 3),
        "planned_symbols": planned_symbols,
        "drifted_symbols": drifted_symbols,
        "semantic_drift_ratio": semantic_drift_ratio,
        "semantic_accuracy_score": semantic_accuracy_score,
        "composite_drift_ratio": composite_drift,
        "composite_accuracy_score": composite_accuracy,
    }


def update_project_state_calibration(calibration: Dict[str, Any], repo_root: str = _REPO_ROOT) -> None:
    """Updates project_state.json with plan accuracy metrics and prunes stale historical entries."""
    state_file = os.path.join(repo_root, "project_state.json")
    if os.path.isfile(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            # Decay and prune calibration history (keep max 20 entries)
            history = data.get("plan_calibration_history", [])
            history.append({
                "accuracy_score": calibration["accuracy_score"],
                "drift_ratio": calibration["drift_ratio"],
                "semantic_accuracy_score": calibration.get("semantic_accuracy_score", 1.0),
                "semantic_drift_ratio": calibration.get("semantic_drift_ratio", 0.0),
                "calibrated_at": datetime.datetime.now().isoformat(),
            })
            if len(history) > 20:
                history = history[-20:]
            data["plan_calibration_history"] = history

            data["plan_calibration"] = {
                "last_accuracy_score": calibration["accuracy_score"],
                "last_drift_ratio": calibration["drift_ratio"],
                "semantic_accuracy_score": calibration.get("semantic_accuracy_score", 1.0),
                "semantic_drift_ratio": calibration.get("semantic_drift_ratio", 0.0),
                "composite_accuracy_score": calibration.get("composite_accuracy_score", calibration["accuracy_score"]),
                "composite_drift_ratio": calibration.get("composite_drift_ratio", calibration["drift_ratio"]),
                "unplanned_files": calibration["unplanned_files"],
                "drifted_symbols": calibration.get("drifted_symbols", []),
                "last_calibrated_at": datetime.datetime.now().isoformat(),
            }

            # Apply 0.9 exponential temporal decay to coupling memory
            coupling_memory = data.get("coupling_memory", {})
            decayed_memory: Dict[str, float] = {}
            for k, weight in coupling_memory.items():
                new_weight = round(weight * 0.9, 3)
                if new_weight >= 0.1:
                    decayed_memory[k] = new_weight

            for uf in calibration.get("unplanned_files", []):
                decayed_memory[uf] = 1.0

            data["coupling_memory"] = decayed_memory
            with open(state_file, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass


def update_adr_readme(adr_dir: str) -> None:
    """Regenerates or updates docs/adr/README.md with a table of all ADRs."""
    os.makedirs(adr_dir, exist_ok=True)
    adr_files = sorted(glob.glob(os.path.join(adr_dir, "ADR-[0-9][0-9][0-9][0-9]-*.md")))

    rows: List[str] = []
    for f in adr_files:
        basename = os.path.basename(f)
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            title_m = re.search(r"^#\s*ADR-\d{4}:\s*(.*?)$", txt, re.MULTILINE)
            status_m = re.search(r"-\s*\*\*Status:\*\*\s*(.*?)$", txt, re.MULTILINE)
            date_m = re.search(r"-\s*\*\*Date:\*\*\s*(.*?)$", txt, re.MULTILINE)

            title = title_m.group(1) if title_m else basename
            status = status_m.group(1) if status_m else "Accepted"
            date = date_m.group(1) if date_m else "Unknown"

            rows.append(f"| [{basename}](./{basename}) | {title} | {status} | {date} |")
        except Exception:
            rows.append(f"| [{basename}](./{basename}) | {basename} | Unknown | Unknown |")

    table_content = "\n".join(rows) if rows else "| *(None yet)* | *(No ADRs harvested yet)* | | |"

    readme_content = f"""<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Architecture Decision Records (ADR Inventory)

> **Purpose:** Permanent repository memory of verified architectural decisions harvested from `/super-plan` and `/plan` workflows after achieving 100% Definition-of-Done (DoD) Quality Gates.

| ADR Record | Decision Title | Status | Certified Date |
|---|---|---|---|
{table_content}

---
*Auto-indexed by `tools/design/plan_harvester.py`.*
"""
    readme_path = os.path.join(adr_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(readme_content)


def is_adr_worthy_decision(content: str, parsed: Dict[str, Any]) -> Tuple[bool, str, str]:
    """
    Evaluates whether an implementation plan represents a significant, hard-to-reverse
    architectural decision worthy of persistent preservation in docs/adr/.
    Prevents ADR directory fatigue and repository memory bloat from routine bugfixes.
    """
    # 1. Explicit high-impact header marker
    if re.search(r"(?:Architectural-Impact|Architectural\s+Impact)\s*:\s*High", content, re.IGNORECASE):
        return True, "HIGH", "Explicit 'Architectural-Impact: High' marker specified in plan"

    if re.search(r"\[(?:ADR_REQUIRED|HIGH_IMPACT)\s*:\s*(?:TRUE|YES|1)\]", content, re.IGNORECASE):
        return True, "HIGH", "Explicit ADR_REQUIRED tag set to TRUE"

    # 2. Explicit low-impact header marker to prevent ADR fatigue
    if re.search(r"(?:Architectural-Impact|Architectural\s+Impact)\s*:\s*(?:Low|Standard|None)", content, re.IGNORECASE):
        return False, "LOW", "Explicit low/standard impact: ADR file bypassed to prevent ADR inventory fatigue"

    # 3. Architectural keywords in plan title
    title = parsed.get("title", "").lower()
    if any(kw in title for kw in ("architecture", "infrastructure", "protocol", "engine", "contract", "pipeline", "framework")):
        return True, "HIGH", f"Architectural scope detected in title: '{parsed.get('title')}'"

    # 4. Breaking contracts / schema migrations / new database engines
    high_impact_patterns = [
        r"\b(?:breaking\s+change|database\s+migration|schema\s+overhaul|deprecat(?:e|ing|ion))\b",
        r"\b(?:new\s+protocol|security\s+architecture|public\s+api\s+contract)\b",
    ]
    for pat in high_impact_patterns:
        if re.search(pat, content, re.IGNORECASE):
            return True, "HIGH", f"High-impact structural decision detected: matching '{pat}'"

    return False, "STANDARD", "Routine implementation or local refactoring (ADR bypassed to prevent ADR fatigue)"


def harvest_plan(
    plan_path: str,
    output_dir: str,
    dry_run: bool = False,
    status: str = "Accepted (DoD Certified)",
    force: bool = False,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Harvests an implementation plan into an ADR markdown file."""
    if not os.path.isfile(plan_path):
        return False, f"Plan file not found: {plan_path}", {}

    with open(plan_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    parsed = parse_plan(content)
    calibration = calibrate_plan_against_git(content)
    next_idx = get_next_adr_index(output_dir)

    if not dry_run:
        update_project_state_calibration(calibration)

    is_worthy, impact_level, reason = is_adr_worthy_decision(content, parsed)
    if not is_worthy and not force:
        result_data = {
            "index": next_idx,
            "title": parsed["title"],
            "adr_created": False,
            "impact_level": impact_level,
            "reason": reason,
            "dry_run": dry_run,
            "calibration": calibration,
        }
        return True, f"Plan calibration updated in project_state.json; ADR file bypassed ({reason})", result_data

    os.makedirs(output_dir, exist_ok=True)
    next_idx = get_next_adr_index(output_dir)
    slug = slugify(parsed["title"])
    filename = f"ADR-{next_idx:04d}-{slug}.md"
    target_path = os.path.join(output_dir, filename)

    adr_content = format_adr(next_idx, parsed, plan_path, status=status, calibration=calibration)

    if not dry_run:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(adr_content)
        update_adr_readme(output_dir)

    result_data = {
        "index": next_idx,
        "title": parsed["title"],
        "filename": filename,
        "path": target_path,
        "adr_created": True,
        "impact_level": impact_level,
        "dry_run": dry_run,
        "calibration": calibration,
    }
    return True, f"Harvested ADR-{next_idx:04d} into {filename}", result_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan Harvester: Converts verified plans to ADRs")
    parser.add_argument("--file", help="Path to implementation_plan.md to harvest", default="templates/test-plan/spec-driven-plan-template.md")
    parser.add_argument("--output-dir", help="Target ADR directory", default=os.path.join(_REPO_ROOT, "docs", "adr"))
    parser.add_argument("--status", help="ADR status string", default="Accepted (DoD Certified)")
    parser.add_argument("--dry-run", action="store_true", help="Preview ADR extraction without writing to disk")
    parser.add_argument("--force", action="store_true", help="Force ADR file generation regardless of Architectural-Impact level")
    parser.add_argument("--update-index", action="store_true", help="Re-indexes docs/adr/README.md")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    if args.update_index:
        update_adr_readme(args.output_dir)
        print(f"Updated index in {args.output_dir}/README.md")
        return 0

    plan_path = args.file if os.path.isabs(args.file) else os.path.join(_REPO_ROOT, args.file)
    success, msg, data = harvest_plan(
        plan_path,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        status=args.status,
        force=args.force,
    )

    if args.json:
        print(json.dumps({"success": success, "message": msg, "data": data}, indent=2))
        return 0 if success else 1

    status_str = "SUCCESS" if success else "FAILED"
    print(f"[{status_str}] {msg}")
    if success and not args.dry_run:
        print(f"  -> File: {data.get('path')}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
