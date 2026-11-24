#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/task_memory_manager.py — Compaction-Resilient Working Memory Manager
Inspired by OthmanAdi/planning-with-files (28.1k ⭐).

Maintains disk-persistent working memory across agent compactions and sessions:
- task_plan.md: Strategic goal, phases, and active state.
- findings.md: Empirical discovery, DOM selectors, diagnostic evidence.
- progress.md: Checklists, milestones, step-by-step audit log.
- .checksums.json: SHA-256 cryptographic verification of file integrity.

100% Python Standard Library (zero external dependencies).
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


import argparse
import datetime
import hashlib
import json
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple

DEFAULT_MEMORY_DIR = ".task_memory"


def compute_sha256(content: str) -> str:
    """Computes SHA-256 hexadecimal digest for a string content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_file_sha256(file_path: str) -> Optional[str]:
    """Computes SHA-256 for a file on disk."""
    if not os.path.isfile(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return hashlib.sha256(f.read().encode("utf-8")).hexdigest()


class TaskMemoryManager:
    """Manages disk-persistent working memory files with cryptographic checksums."""

    def __init__(self, memory_dir: str = DEFAULT_MEMORY_DIR):
        self.memory_dir = os.path.abspath(memory_dir)
        self.plan_path = os.path.join(self.memory_dir, "task_plan.md")
        self.findings_path = os.path.join(self.memory_dir, "findings.md")
        self.progress_path = os.path.join(self.memory_dir, "progress.md")
        self.checksums_path = os.path.join(self.memory_dir, ".checksums.json")

    def _read_checksums(self) -> Dict[str, str]:
        if not os.path.isfile(self.checksums_path):
            return {}
        for attempt in range(10):
            try:
                with open(self.checksums_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                time.sleep(0.005 * (attempt + 1))
                continue
        return {}

    def _write_checksums(self, checksums: Dict[str, str]) -> None:
        tmp_path = self.checksums_path + ".tmp"
        actual_tmp = f"{tmp_path}.{os.getpid()}_{id(checksums)}"
        with open(actual_tmp, "w", encoding="utf-8") as f:
            json.dump(checksums, f, indent=2, ensure_ascii=False)
        for attempt in range(10):
            try:
                os.replace(actual_tmp, self.checksums_path)
                return
            except OSError:
                if attempt == 9:
                    try:
                        with open(self.checksums_path, "w", encoding="utf-8") as f:
                            json.dump(checksums, f, indent=2, ensure_ascii=False)
                        if os.path.exists(actual_tmp):
                            os.remove(actual_tmp)
                        return
                    except OSError:
                        return
                time.sleep(0.02 * (attempt + 1))

    def _update_file_checksum(self, filename: str, content: str) -> None:
        checksums = self._read_checksums()
        checksums[filename] = compute_sha256(content)
        self._write_checksums(checksums)

    def init_memory(self, title: str = "Task Execution Plan", goal: str = "Execute task according to DoD") -> Dict[str, str]:
        """Initializes empty memory files if they do not exist."""
        os.makedirs(self.memory_dir, exist_ok=True)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Query Cold Memory (TestMemoryOS) for relevant historical lessons/mutations
        historical_insights = ""
        try:
            from test_memory_os import TestMemoryOS
            mem = TestMemoryOS()
            ctx = mem.retrieve_session_context(query=f"{title} {goal}", top_k=3)
            if ctx.get("count", 0) > 0:
                historical_insights = f"\n## 0. Historical Insights (Cold-Memory Hydration)\n{ctx['markdown_block']}\n"
        except Exception:
            historical_insights = ""

        if not os.path.isfile(self.plan_path):
            initial_plan = (
                f"# {title}\n\n"
                f"> Initialized: `{now}`\n{historical_insights}"
                f"## 1. Goal & Requirements\n{goal}\n\n"
                f"## 2. Phases & Milestones\n- [ ] Phase 1: Discovery & Analysis\n- [ ] Phase 2: Implementation\n- [ ] Phase 3: Verification & DoD\n\n"
                f"## 3. Active Status\n`IN_PROGRESS`\n"
            )
            with open(self.plan_path, "w", encoding="utf-8") as f:
                f.write(initial_plan)
            self._update_file_checksum("task_plan.md", initial_plan)

        if not os.path.isfile(self.findings_path):
            initial_findings = (
                f"# Empirical Findings & Evidence Log\n\n"
                f"> Initialized: `{now}`\n\n"
                f"| Timestamp | Category | Summary | Details |\n"
                f"|---|---|---|---|\n"
            )
            with open(self.findings_path, "w", encoding="utf-8") as f:
                f.write(initial_findings)
            self._update_file_checksum("findings.md", initial_findings)

        if not os.path.isfile(self.progress_path):
            initial_progress = (
                f"# Execution Progress & Milestone Ledger\n\n"
                f"> Initialized: `{now}`\n\n"
                f"## Milestones\n"
                f"- [x] Task memory initialized (`{now}`)\n"
            )
            with open(self.progress_path, "w", encoding="utf-8") as f:
                f.write(initial_progress)
            self._update_file_checksum("progress.md", initial_progress)

        return self._read_checksums()

    def update_task_plan(self, content: str) -> str:
        """Overwrites or updates task_plan.md and recomputes checksum."""
        os.makedirs(self.memory_dir, exist_ok=True)
        with open(self.plan_path, "w", encoding="utf-8") as f:
            f.write(content)
        sha = compute_sha256(content)
        self._update_file_checksum("task_plan.md", content)
        return sha

    def record_finding(self, title: str, details: str, category: str = "OBSERVATION") -> None:
        """Appends an empirical finding or diagnostic evidence to findings.md."""
        os.makedirs(self.memory_dir, exist_ok=True)
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        sanitized_title = str(title).replace("\r", " ").replace("\n", " ").replace("|", "/")
        sanitized_cat = str(category).replace("\r", " ").replace("\n", " ").replace("|", "/")
        sanitized_details = str(details).replace("\r", " ").replace("\n", " ").replace("|", "/")
        row = f"| `{now}` | `{sanitized_cat}` | **{sanitized_title}** | {sanitized_details} |\n"

        if not os.path.isfile(self.findings_path):
            self.init_memory()

        with open(self.findings_path, "a", encoding="utf-8") as f:
            f.write(row)

        with open(self.findings_path, "r", encoding="utf-8") as f:
            content = f.read()
        self._update_file_checksum("findings.md", content)

    def record_progress(self, step: str, status: str = "DONE") -> None:
        """Records a completed step or milestone in progress.md."""
        os.makedirs(self.memory_dir, exist_ok=True)
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S UTC")
        sanitized_step = str(step).replace("\r", " ").replace("\n", " ")
        sanitized_status = str(status).replace("\r", " ").replace("\n", " ")
        mark = "[x]" if sanitized_status.upper() in ("DONE", "COMPLETED", "PASS") else "[-]"
        entry = f"- {mark} `{now}` {sanitized_step} (`{sanitized_status}`)\n"

        if not os.path.isfile(self.progress_path):
            self.init_memory()

        with open(self.progress_path, "a", encoding="utf-8") as f:
            f.write(entry)

        with open(self.progress_path, "r", encoding="utf-8") as f:
            content = f.read()
        self._update_file_checksum("progress.md", content)

    def verify_integrity(self) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
        """
        Verifies SHA-256 hashes of all memory files against recorded checksums.
        Returns: (all_valid, details_map)
        """
        checksums = self._read_checksums()
        results: Dict[str, Dict[str, Any]] = {}
        all_valid = True

        files = [
            ("task_plan.md", self.plan_path),
            ("findings.md", self.findings_path),
            ("progress.md", self.progress_path),
        ]

        for fname, fpath in files:
            expected = checksums.get(fname)
            actual = compute_file_sha256(fpath)
            valid = (actual is not None) and (actual == expected)
            if not valid:
                all_valid = False
            results[fname] = {
                "exists": os.path.isfile(fpath),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "valid": valid,
            }

        return all_valid, results

    def check_compaction_trigger(self, current_tokens: int, threshold: int = 50000) -> Dict[str, Any]:
        """
        Evaluates whether host/agent compaction should be recommended and enforces
        pre-prune disk SHA-256 integrity verification before allowing any prune action.
        """
        integrity_verified, details = self.verify_integrity()
        compaction_recommended = int(current_tokens) >= int(threshold)
        can_prune = compaction_recommended and integrity_verified

        if not integrity_verified:
            status = "INTEGRITY_FAILED_PRUNE_BLOCKED"
        elif compaction_recommended:
            status = "COMPACTION_RECOMMENDED"
        else:
            status = "OK"

        return {
            "current_tokens": int(current_tokens),
            "threshold": int(threshold),
            "compaction_recommended": compaction_recommended,
            "integrity_verified": integrity_verified,
            "can_prune": can_prune,
            "status": status,
            "details": details,
        }

    def export_summary(self) -> str:
        """Exports a compact text summary of working memory state."""
        valid, details = self.verify_integrity()
        lines = [
            f"Task Memory Status: {'VALID (100% SHA-256 Match)' if valid else 'COMPROMISED / MODIFIED'}",
            f"Location: {self.memory_dir}",
        ]
        for fname, info in details.items():
            status = "OK" if info["valid"] else "MISMATCH / MISSING"
            lines.append(f"  - {fname}: {status} (SHA: {str(info['actual_sha256'])[:8]}...)")
        return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compaction-Resilient Working Memory Manager (OthmanAdi Pattern)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_p = subparsers.add_parser("init", help="Initialize memory files")
    init_p.add_argument("--dir", default=DEFAULT_MEMORY_DIR, help="Memory directory")
    init_p.add_argument("--title", default="Task Execution Plan", help="Plan title")

    # finding
    finding_p = subparsers.add_parser("finding", help="Record finding")
    finding_p.add_argument("title", help="Finding title")
    finding_p.add_argument("details", help="Details text")
    finding_p.add_argument("--dir", default=DEFAULT_MEMORY_DIR, help="Memory directory")
    finding_p.add_argument("--cat", default="OBSERVATION", help="Category")

    # progress
    progress_p = subparsers.add_parser("progress", help="Record progress milestone")
    progress_p.add_argument("step", help="Completed step description")
    progress_p.add_argument("--dir", default=DEFAULT_MEMORY_DIR, help="Memory directory")
    progress_p.add_argument("--status", default="DONE", help="Step status")

    # verify
    verify_p = subparsers.add_parser("verify", help="Verify cryptographic integrity")
    verify_p.add_argument("--dir", default=DEFAULT_MEMORY_DIR, help="Memory directory")

    args = parser.parse_args()
    mgr = TaskMemoryManager(args.dir)

    if args.command == "init":
        res = mgr.init_memory(title=args.title)
        print(f"✅ Initialized task memory in {args.dir} with checksums: {list(res.keys())}")
        return 0

    if args.command == "finding":
        mgr.record_finding(title=args.title, details=args.details, category=args.cat)
        print(f"✅ Recorded finding: '{args.title}' in {args.dir}/findings.md")
        return 0

    if args.command == "progress":
        mgr.record_progress(step=args.step, status=args.status)
        print(f"✅ Recorded progress: '{args.step}' in {args.dir}/progress.md")
        return 0

    if args.command == "verify":
        valid, details = mgr.verify_integrity()
        print(mgr.export_summary())
        return 0 if valid else 1

    return -1


if __name__ == "__main__":
    sys.exit(main())
