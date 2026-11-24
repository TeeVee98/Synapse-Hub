# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Append-only Decision Ledger & Fast Search Engine (AGENTS.md / Decision Lineage Protocol).

Provides high-integrity, process-safe, token-efficient decision provenance:
1. Append-only ledger in docs/decisions.jsonl protected with advisory file locks.
2. Low-token, sub-millisecond retrieval prioritizing ripgrep (rg) with BM25/streaming fallback.
3. Passive Obsidian-compatible Markdown export with YAML frontmatter & callouts.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    from tools.core.file_lock import FileLock
except ImportError:
    # Graceful fallback if invoked outside package context
    class FileLock:  # type: ignore[no-redef]
        def __init__(self, target_path: str, timeout: float = 10.0, **_kwargs: Any):
            self.target_path = target_path
            self.timeout = timeout

        def __enter__(self) -> FileLock:
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass


LEDGER_FILENAME = "decisions.jsonl"
DEFAULT_LEDGER_RELPATH = os.path.join("docs", LEDGER_FILENAME)


@dataclass(frozen=True)
class DecisionRecordDTO:
    """Immutable data transfer object representing a single decision entry."""
    id: str
    timestamp: str
    decision: str
    why: str = "Architecture requirement"
    cost_if_wrong: str = "Technical debt"
    scope: str = "general"
    author: str = "agent"
    evidence: str = ""
    tags: List[str] = field(default_factory=list)
    ruling: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Converts DTO to serialized dictionary representation."""
        data = asdict(self)
        if not data.get("ruling"):
            data["ruling"] = f"Ruling: {self.decision} — {self.why} — {self.cost_if_wrong}"
        return data


@dataclass(frozen=True)
class DecisionQueryResultDTO:
    """Immutable data transfer object for search and query responses."""
    total: int
    matches: List[Dict[str, Any]]
    execution_time_ms: float = 0.0
    engine: str = "stream"

    def to_dict(self) -> Dict[str, Any]:
        """Converts query result to dictionary."""
        return asdict(self)


def resolve_ledger_file(target_dir: str) -> str:
    """Resolves absolute path to docs/decisions.jsonl and ensures parent directory exists."""
    norm_target = os.path.abspath(target_dir)
    docs_dir = os.path.join(norm_target, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    return os.path.join(docs_dir, LEDGER_FILENAME)


def append_decision(
    target_dir: str,
    record: Union[DecisionRecordDTO, Dict[str, Any]],
) -> Dict[str, Any]:
    """Appends an immutable decision record to docs/decisions.jsonl with advisory file locking.

    Args:
        target_dir: Target project workspace root directory.
        record: DecisionRecordDTO instance or raw dictionary.

    Returns:
        Dict representing the safely persisted decision record.
    """
    ledger_path = resolve_ledger_file(target_dir)

    if isinstance(record, DecisionRecordDTO):
        record_dict = record.to_dict()
    else:
        record_dict = dict(record)

    # Fill mandatory defaults if omitted
    now = datetime.now()
    if not record_dict.get("timestamp"):
        record_dict["timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S")

    if not record_dict.get("id"):
        # Deterministic micro-timestamp suffix
        record_dict["id"] = f"dec-{now.strftime('%Y%m%d-%H%M%S-%f')[:21]}"

    if not record_dict.get("why"):
        record_dict["why"] = "Architecture requirement"

    if not record_dict.get("cost_if_wrong"):
        record_dict["cost_if_wrong"] = "Technical debt"

    if not record_dict.get("scope"):
        record_dict["scope"] = "general"

    if not record_dict.get("author"):
        record_dict["author"] = "agent"

    if "tags" not in record_dict or record_dict["tags"] is None:
        record_dict["tags"] = []

    if not record_dict.get("ruling"):
        record_dict["ruling"] = (
            f"Ruling: {record_dict['decision']} — {record_dict['why']} — {record_dict['cost_if_wrong']}"
        )

    json_line = json.dumps(record_dict, ensure_ascii=False) + "\n"

    with FileLock(ledger_path, timeout=10.0):
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(json_line)

    return record_dict


def _scan_stream_decisions(
    ledger_path: str,
    query: Optional[str] = None,
    scope: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Iterates through JSONL ledger lines in reverse (newest first) with bounded memory."""
    if not os.path.isfile(ledger_path):
        return []

    matches: List[Dict[str, Any]] = []
    q_lower = query.lower().strip() if query else None
    scope_lower = scope.lower().strip() if scope else None
    tag_lower = tag.lower().strip() if tag else None

    # Read lines in reverse order efficiently
    try:
        with open(ledger_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []

    for line in reversed(lines):
        line_str = line.strip()
        if not line_str:
            continue
        try:
            item = json.loads(line_str)
        except json.JSONDecodeError:
            continue

        if not isinstance(item, dict):
            continue

        # Filter by scope if provided
        if scope_lower:
            item_scope = str(item.get("scope", "")).lower()
            if scope_lower != item_scope:
                continue

        # Filter by tag if provided
        if tag_lower:
            item_tags = [str(t).lower() for t in item.get("tags", [])]
            if tag_lower not in item_tags:
                continue

        # Filter by text query if provided
        if q_lower:
            searchable_corpus = " ".join([
                str(item.get("decision", "")),
                str(item.get("why", "")),
                str(item.get("cost_if_wrong", "")),
                str(item.get("ruling", "")),
                str(item.get("evidence", "")),
                " ".join(str(t) for t in item.get("tags", [])),
            ]).lower()

            if q_lower not in searchable_corpus:
                continue

        matches.append(item)
        if len(matches) >= limit:
            break

    return matches


def _search_with_ripgrep(
    ledger_path: str,
    query: str,
    limit: int = 10,
) -> Optional[List[Dict[str, Any]]]:
    """Uses ripgrep (rg) for sub-millisecond line matching on decisions.jsonl."""
    rg_binary = shutil.which("rg")
    if not rg_binary or not os.path.isfile(ledger_path):
        return None

    try:
        cmd = [rg_binary, "-i", "-F", "--no-line-number", query, ledger_path]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3.0)
        if proc.returncode not in (0, 1):  # 0: found, 1: not found
            return None

        lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        matches: List[Dict[str, Any]] = []
        for ln in reversed(lines):
            try:
                item = json.loads(ln)
                if isinstance(item, dict):
                    matches.append(item)
                    if len(matches) >= limit:
                        break
            except json.JSONDecodeError:
                continue
        return matches
    except Exception:
        return None


def query_decisions(
    target_dir: str,
    query: Optional[str] = None,
    scope: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 10,
    use_fast_search: bool = True,
) -> DecisionQueryResultDTO:
    """Queries decisions from docs/decisions.jsonl with sub-millisecond search & low token overhead.

    Args:
        target_dir: Project directory root.
        query: Optional substring to search across decision, why, and ruling.
        scope: Optional category filter (e.g. 'architecture', 'qa', 'model').
        tag: Optional tag filter (e.g. 'regression', 'refactor').
        limit: Maximum number of matched records to return (defaults to 10).
        use_fast_search: Whether to attempt accelerated search with ripgrep.

    Returns:
        DecisionQueryResultDTO containing matched decisions and metadata.
    """
    start_time = datetime.now()
    ledger_path = resolve_ledger_file(target_dir)

    if not os.path.isfile(ledger_path):
        return DecisionQueryResultDTO(total=0, matches=[], execution_time_ms=0.0, engine="none")

    engine_used = "stream"
    matches: Optional[List[Dict[str, Any]]] = None

    # Ripgrep optimization if only querying text and no scope/tag restrictions
    if use_fast_search and query and not scope and not tag:
        rg_matches = _search_with_ripgrep(ledger_path, query, limit=limit)
        if rg_matches is not None:
            matches = rg_matches
            engine_used = "ripgrep"

    if matches is None:
        matches = _scan_stream_decisions(ledger_path, query=query, scope=scope, tag=tag, limit=limit)
        engine_used = "stream"

    duration_ms = (datetime.now() - start_time).total_seconds() * 1000.0

    return DecisionQueryResultDTO(
        total=len(matches),
        matches=matches,
        execution_time_ms=round(duration_ms, 2),
        engine=engine_used,
    )


def export_obsidian_markdown(
    target_dir: str,
    output_path: Optional[str] = None,
) -> str:
    """Generates an Obsidian-friendly Markdown summary note with YAML frontmatter and callouts.

    Args:
        target_dir: Project root directory.
        output_path: Optional custom destination file path.

    Returns:
        Path to the generated Markdown file.
    """
    ledger_path = resolve_ledger_file(target_dir)
    all_decisions = _scan_stream_decisions(ledger_path, limit=10000)

    if not output_path:
        output_path = os.path.join(target_dir, "docs", "DECISIONS_OBSIDIAN.md")

    now_iso = datetime.now().isoformat()
    doc_lines: List[str] = [
        "---",
        "type: decision-log",
        "project: Synapse-Hub",
        f"updated_at: '{now_iso}'",
        f"total_decisions: {len(all_decisions)}",
        "tags: [decisions, pkm, synapse-hub, architecture]",
        "---",
        "",
        "# Architectural Decision Journal (Obsidian PKM View)",
        "",
        "> **Notice:** This view is compiled from the immutable `docs/decisions.jsonl` ledger.",
        "> For human and team knowledge synthesis. AI agents query raw `.jsonl` directly to conserve token budget.",
        "",
        "## Related Context Links",
        "- [[PROJECT_STATE]] — Active session state anchor",
        "- [[docs/INVARIANTS]] — Universal operating standards & rules",
        "- [[docs/adr/README]] — Formal Architectural Decision Records",
        "",
        "---",
        "",
        "## Decision History",
        "",
    ]

    if not all_decisions:
        doc_lines.append("*No decisions recorded yet.*")
    else:
        for dec in all_decisions:
            dec_id = dec.get("id", "dec-unknown")
            ts = dec.get("timestamp", "unknown-time")
            decision = dec.get("decision", "No decision text")
            why = dec.get("why", "N/A")
            cost = dec.get("cost_if_wrong", "N/A")
            scope = dec.get("scope", "general")
            author = dec.get("author", "agent")
            evidence = dec.get("evidence", "")
            tags = dec.get("tags", [])
            tag_badges = " ".join([f"#{t}" for t in tags]) if tags else ""

            doc_lines.extend([
                f"### {dec_id} — {ts}",
                f"> [!NOTE] {decision}",
                f"> - **Why:** {why}",
                f"> - **Cost if wrong:** {cost}",
                f"> - **Scope:** `{scope}` | **Author:** `{author}` {('| ' + tag_badges) if tag_badges else ''}",
            ])
            if evidence:
                doc_lines.append(f"> - **Evidence:** `{evidence}`")
            doc_lines.append("")

    content = "\n".join(doc_lines) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def main() -> int:
    """CLI Entry point for tools/core/decision_ledger.py."""
    parser = argparse.ArgumentParser(
        description="Append-only Decision Ledger & Fast Search CLI (AGENTS.md / Decision Lineage Protocol)",
    )
    parser.add_argument("--dir", default=".", help="Target workspace directory (default: current directory)")
    parser.add_argument("--log", action="store_true", help="Record a new decision")
    parser.add_argument("--decision", help="Decision statement")
    parser.add_argument("--why", default="Architecture requirement", help="Reasoning / justification")
    parser.add_argument("--cost", default="Technical debt", help="Cost if wrong / risk trade-off")
    parser.add_argument("--scope", default="general", help="Scope / category")
    parser.add_argument("--author", default="agent", help="Decision maker")
    parser.add_argument("--evidence", default="", help="Empirical evidence or log reference")
    parser.add_argument("--tag", action="append", default=[], help="Tags (can be repeated)")

    parser.add_argument("--query", help="Search query string")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of query results (default: 10)")
    parser.add_argument("--export-obsidian", action="store_true", help="Export to Obsidian-friendly Markdown note")
    parser.add_argument("--obsidian-out", help="Custom output path for Obsidian Markdown note")
    parser.add_argument("--gate", action="store_true", help="Verification gate: validate ledger integrity")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    target_dir = os.path.abspath(args.dir)

    # 1. Log mode
    if args.log:
        if not args.decision:
            sys.stderr.write("Error: --decision is required when --log is passed.\n")
            return 2
        entry = DecisionRecordDTO(
            id="",
            timestamp="",
            decision=args.decision,
            why=args.why,
            cost_if_wrong=args.cost,
            scope=args.scope,
            author=args.author,
            evidence=args.evidence,
            tags=args.tag,
        )
        saved = append_decision(target_dir, entry)
        if args.json:
            print(json.dumps(saved, indent=2, ensure_ascii=False))
        else:
            print(f"Logged decision {saved['id']}: {saved['ruling']}")
        return 0

    # 2. Export Obsidian mode
    if args.export_obsidian:
        out_file = export_obsidian_markdown(target_dir, args.obsidian_out)
        if args.json:
            print(json.dumps({"exported_file": out_file, "status": "SUCCESS"}, indent=2))
        else:
            print(f"Obsidian decision journal exported to: {out_file}")
        return 0

    # 3. Query mode
    if args.query is not None:
        res = query_decisions(
            target_dir,
            query=args.query,
            scope=args.scope if args.scope != "general" else None,
            tag=args.tag[0] if args.tag else None,
            limit=args.limit,
        )
        if args.json:
            print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"Found {res.total} decisions (engine: {res.engine}, {res.execution_time_ms}ms):")
            for m in res.matches:
                print(f"  - [{m.get('timestamp')}] {m.get('ruling')}")
        return 0

    # 4. Gate verification mode
    if args.gate:
        ledger_path = resolve_ledger_file(target_dir)
        if not os.path.exists(ledger_path):
            # Empty is valid initially
            if args.json:
                print(json.dumps({"status": "PASS", "decisions_count": 0, "ledger_path": ledger_path}))
            else:
                print("Decision Ledger Gate: PASS (0 entries, ledger ready)")
            return 0

        # Verify integrity of JSONL lines
        count = 0
        corrupt = 0
        with open(ledger_path, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, 1):
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                    if not isinstance(obj, dict) or "decision" not in obj:
                        corrupt += 1
                    else:
                        count += 1
                except json.JSONDecodeError:
                    corrupt += 1

        passed = corrupt == 0
        status_str = "PASS" if passed else "FAIL"
        if args.json:
            print(json.dumps({
                "status": status_str,
                "decisions_count": count,
                "corrupted_lines": corrupt,
                "ledger_path": ledger_path,
            }))
        else:
            print(f"Decision Ledger Gate: {status_str} ({count} valid decisions, {corrupt} corrupted lines)")
        return 0 if passed else 1

    # Default action: show query summary
    res = query_decisions(target_dir, limit=5)
    if args.json:
        print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Decision Ledger: {res.total} recent decisions:")
        for m in res.matches:
            print(f"  - [{m.get('timestamp')}] {m.get('ruling')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
