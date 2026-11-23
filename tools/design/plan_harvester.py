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
        calibration_block = f"""
---

## Plan Calibration & Drift Analysis
- **Plan Accuracy Score:** {calibration.get("accuracy_score", 1.0) * 100:.1f}%
- **Plan Drift Ratio:** {calibration.get("drift_ratio", 0.0)}
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

    return {
        "planned_files": planned_files,
        "actual_files": actual_files,
        "unplanned_files": unplanned_files,
        "drift_ratio": round(drift_ratio, 3),
        "accuracy_score": round(accuracy_score, 3),
    }


def update_project_state_calibration(calibration: Dict[str, Any], repo_root: str = _REPO_ROOT) -> None:
    """Updates project_state.json with plan accuracy metrics."""
    state_file = os.path.join(repo_root, "project_state.json")
    if os.path.isfile(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            data["plan_calibration"] = {
                "last_accuracy_score": calibration["accuracy_score"],
                "last_drift_ratio": calibration["drift_ratio"],
                "unplanned_files": calibration["unplanned_files"],
                "last_calibrated_at": datetime.datetime.now().isoformat(),
            }
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


def harvest_plan(
    plan_path: str,
    output_dir: str,
    dry_run: bool = False,
    status: str = "Accepted (DoD Certified)",
) -> Tuple[bool, str, Dict[str, Any]]:
    """Harvests an implementation plan into an ADR markdown file."""
    if not os.path.isfile(plan_path):
        return False, f"Plan file not found: {plan_path}", {}

    with open(plan_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    parsed = parse_plan(content)
    os.makedirs(output_dir, exist_ok=True)
    next_idx = get_next_adr_index(output_dir)
    slug = slugify(parsed["title"])
    filename = f"ADR-{next_idx:04d}-{slug}.md"
    target_path = os.path.join(output_dir, filename)

    calibration = calibrate_plan_against_git(content)
    adr_content = format_adr(next_idx, parsed, plan_path, status=status, calibration=calibration)

    if not dry_run:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(adr_content)
        update_adr_readme(output_dir)
        update_project_state_calibration(calibration)

    result_data = {
        "index": next_idx,
        "title": parsed["title"],
        "filename": filename,
        "path": target_path,
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
