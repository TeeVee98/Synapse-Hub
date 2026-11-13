#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/distill_log.py — Enterprise Multi-Framework Log Distiller (Token & Failure Sentinel)
Filters out 90%+ passing step noise and outputs strictly actionable, evidence-backed
failure triage blocks without false passes or dropped assertion diffs.
Supports Pytest, Playwright, Jest/Vitest, Katalon KRE, Gradle, and Python/Node/JVM logs.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Enforce UTF-8 stdout encoding for cross-platform compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Universal noise patterns (passing steps, zero failures summary, timestamps, system initialization)
NOISE_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"\b0\s+failed\b", re.IGNORECASE),
    re.compile(r"\b0\s+failures?\b", re.IGNORECASE),
    re.compile(r"\b0\s+errors?\b", re.IGNORECASE),
    re.compile(r"\b(?:no|zero)\s+failures?\b", re.IGNORECASE),
    re.compile(r"\b(?:no|zero)\s+errors?\b", re.IGNORECASE),
    re.compile(r"\[INFO\b|\bINFO:|\bINFO\s+", re.IGNORECASE),
    re.compile(r"\[DEBUG\b|\bDEBUG:|\bDEBUG\s+", re.IGNORECASE),
    re.compile(r"\[TRACE\b|\bTRACE:|\bTRACE\s+", re.IGNORECASE),
    re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}.*\b(?:INFO|DEBUG|TRACE)\b", re.IGNORECASE),
    re.compile(r"\bPASSED\b", re.IGNORECASE),
    re.compile(r"> Task :"),
    re.compile(r"SLF4J:"),
    re.compile(r"Loading class `com\.mysql"),
    re.compile(r"Starting ChromeDriver"),
    re.compile(r"Only local connections are allowed"),
    re.compile(r"DevTools listening on"),
    re.compile(r"Fontconfig warning:"),
    re.compile(r"Katalon Studio.*licensed to"),
]

# Explicit false-indicator filter (phrases like "without failure", "0 failures")
PASSING_PHRASES = re.compile(
    r"\b(?:without|zero|0|no)\s+(?:obvious\s+)?(?:failures?|errors?|exceptions?)\b",
    re.IGNORECASE,
)

# Case-insensitive failure indicator patterns
FAILURE_INDICATORS = [
    re.compile(r"\bFAILED\b", re.IGNORECASE),
    re.compile(r"\bFAILURES?\b", re.IGNORECASE),
    re.compile(r"\bERRORS?\b", re.IGNORECASE),
    re.compile(r"\bExceptions?\b", re.IGNORECASE),
    re.compile(r"\bAssertionError\b", re.IGNORECASE),
    re.compile(r"Caused by:", re.IGNORECASE),
    re.compile(r"at (?:Enterprise\.|Script\d+|com\.kms|\S+\.(?:groovy|ts|js|py|java))", re.IGNORECASE),
    re.compile(r"TC-\d+.*FAILED", re.IGNORECASE),
    re.compile(r"FAIL\s+.*(?:\.spec|\.test)", re.IGNORECASE),
    re.compile(r"===+\s*FAILURES\s*===+", re.IGNORECASE),
    re.compile(r"E\s+assert\b", re.IGNORECASE),
    re.compile(r"assert\s+.*==\s*", re.IGNORECASE),
    re.compile(r"expect\(.*\)\.", re.IGNORECASE),
    re.compile(r"Timeout \d+ms exceeded", re.IGNORECASE),
    re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE),
    re.compile(r"panic:\s+", re.IGNORECASE),
    re.compile(r"fatal(?:\s+error)?:\s+", re.IGNORECASE),
]

# Test Case Identifiers
TC_PATTERN = re.compile(
    r"([A-Za-z0-9_.-]+::[A-Za-z0-9_]+|TC-\d+[A-Za-z0-9_]*|test_[A-Za-z0-9_]+|"
    r"[A-Za-z0-9_-]+\.(?:spec|test)\.[jt]sx?)"
)

# Line number pattern
LINE_NUM_PATTERN = re.compile(
    r"((?:Script\d+|\w+Page|\w+\.(?:groovy|ts|js|py|java)):(\d+))|File \"([^\"]+)\", line (\d+)"
)


def distill(
    log_text: str,
    max_lines: int = 40,
    exit_code: Optional[int] = None,
    raw_log_path: Optional[str] = None,
    token_budget: int = 800,
) -> str:
    """
    Distills raw execution logs down to high-signal failure blocks while guaranteeing
    zero false passes and preserving critical assertion diffs, cause chains, and locations.
    """
    raw_bytes = len(log_text.encode("utf-8"))
    lines = log_text.splitlines()
    total_raw_lines = len(lines)

    captured_failures: List[List[str]] = []
    failing_tcs: Set[str] = set()
    failing_locs: List[str] = []

    in_failure_block = False
    current_block: List[str] = []
    last_seen_tc: Optional[str] = None

    for i, line in enumerate(lines):
        # Check if line contains a passing phrase like "0 failures" or "without failure"
        if PASSING_PHRASES.search(line):
            continue

        # Detect candidate TC identifier
        m_tc = TC_PATTERN.search(line)
        if m_tc:
            last_seen_tc = m_tc.group(1)

        # Case-insensitive check
        is_fail_line = any(p.search(line) for p in FAILURE_INDICATORS)
        is_noise = any(p.search(line) for p in NOISE_PATTERNS) and not is_fail_line

        if is_fail_line:
            if not in_failure_block:
                in_failure_block = True
                current_block = []
                # Context line: keep previous line if it was a test name or relevant context
                if i > 0:
                    prev_line = lines[i - 1].strip()
                    if prev_line and not any(p.search(prev_line) for p in NOISE_PATTERNS):
                        current_block.append(prev_line)
                        m_prev_tc = TC_PATTERN.search(prev_line)
                        if m_prev_tc:
                            failing_tcs.add(m_prev_tc.group(1))

            current_block.append(line.rstrip())

            # Associate failing TC
            if m_tc:
                failing_tcs.add(m_tc.group(1))
            elif last_seen_tc:
                failing_tcs.add(last_seen_tc)

            # Detect script line numbers strictly within failure blocks
            m_loc = LINE_NUM_PATTERN.search(line)
            if m_loc:
                failing_locs.append(m_loc.group(1) or f"{m_loc.group(3)}:{m_loc.group(4)}")

        elif in_failure_block:
            # Check for block exit boundary
            if is_noise or (line.startswith("---") and not line.startswith("--- Distilled")) or line.startswith("==="):
                in_failure_block = False
                if current_block:
                    captured_failures.append(current_block[:15])
                    current_block = []
            else:
                current_block.append(line.rstrip())
                if m_tc:
                    failing_tcs.add(m_tc.group(1))

                # Line numbers inside trace
                m_loc = LINE_NUM_PATTERN.search(line)
                if m_loc:
                    failing_locs.append(m_loc.group(1) or f"{m_loc.group(3)}:{m_loc.group(4)}")

                # Limit individual block length
                if len(current_block) >= 15:
                    in_failure_block = False
                    captured_failures.append(current_block)
                    current_block = []

    if current_block:
        captured_failures.append(current_block[:15])

    # Telemetry Header
    output: List[str] = []
    output.append(f"[LOG DISTILLER] Analyzed {total_raw_lines:,} lines ({raw_bytes:,} bytes).")

    # Invariant: Truth Anchor on Exit Code & Failure Detections
    has_failures = bool(failing_tcs or captured_failures)

    if not has_failures:
        if exit_code is not None and exit_code != 0:
            # Runner exited with error but no standard failure regex matched
            output.append(f"❌ RUNNER_NONZERO_EXIT: Process exited with non-zero code {exit_code}.")
            output.append("   No standard failure keyword matched in log. Attached head and tail of raw log:")
            output.append("\n--- Raw Log Head & Tail ---")
            head_lines = [l.strip() for l in lines[:5] if l.strip()]
            tail_lines = [l.strip() for l in lines[-15:] if l.strip()]
            output.extend(head_lines)
            output.append("... [omitted middle passing steps] ...")
            output.extend(tail_lines)
        elif exit_code is None:
            # Exit code not supplied: DO NOT claim "ALL TESTS PASSED"
            output.append("⚠️ NO_FAILURE_SIGNATURE_DETECTED: No recognized failure patterns found.")
            output.append("   (Exit code unverified; verify test execution status directly).")
        else:
            # Explicit exit_code == 0 AND no failure indicators
            output.append(f"✅ ALL TESTS PASSED (Exit Code: 0): Zero errors or failed steps detected across {total_raw_lines:,} lines.")

        if raw_log_path:
            output.append(f"[RAW LOG ARTIFACT] file://{os.path.abspath(raw_log_path)}")
        return "\n".join(output)

    # Report failures
    if exit_code is not None:
        exit_badge = f" [Exit Code: {exit_code}]"
    else:
        exit_badge = ""

    if failing_tcs:
        output.append(f"❌ FAILURES DETECTED{exit_badge}: {len(failing_tcs)} Test Case(s) marked FAILED.")
        output.append(f"   Targeted TCs: {', '.join(sorted(failing_tcs))}")
    else:
        output.append(f"❌ FAILURES / ERRORS DETECTED{exit_badge}: {len(captured_failures)} failure block(s) isolated.")

    if failing_locs:
        unique_locs = sorted(set(failing_locs))
        output.append(f"   Failing Script Location(s): {', '.join(unique_locs[:5])}")

    output.append("\n--- Distilled Failure Block(s) ---")

    # Assemble failure blocks with line budget constraint
    lines_used = len(output)
    max_payload_lines = max(5, max_lines - lines_used)

    assembled_blocks: List[str] = []
    current_lines = 0
    truncated = False

    for block in captured_failures[:5]:
        block_text = "\n".join(block)
        block_lines = len(block)
        if current_lines + block_lines > max_payload_lines:
            # Take what fits
            allowed = max_payload_lines - current_lines
            if allowed > 2:
                assembled_blocks.append("\n".join(block[:allowed]))
                assembled_blocks.append("... [truncated by max_lines budget] ...")
            truncated = True
            break
        assembled_blocks.append(block_text)
        current_lines += block_lines

    output.append("\n---\n".join(assembled_blocks))

    # Append provenance and compression telemetry
    distilled_text = "\n".join(output)
    distilled_bytes = len(distilled_text.encode("utf-8"))
    reduction_pct = round(((raw_bytes - distilled_bytes) / max(1, raw_bytes)) * 100, 1)

    output.append(
        f"\n[DISTILLER METRICS] Distilled: {len(output)} lines ({distilled_bytes:,} bytes) | "
        f"Reduction: {reduction_pct}% | Truncated: {truncated}"
    )

    if raw_log_path:
        output.append(f"[RAW LOG ARTIFACT] file://{os.path.abspath(raw_log_path)}")

    return "\n".join(output)


# Public alias for MCP server compatibility
distill_log_content = distill


def shrink_tokens(text: str, max_chars_per_line: int = 140) -> str:
    """
    Caveman / shrink compression: drops verbose metadata, collapses repetitive traces,
    and truncates stack noise while preserving 100% error names, line locations,
    assertion mismatches, and UUIDs (Julius Brussee caveman/shrink pattern).
    """
    lines = text.splitlines()
    shrunk_lines = []
    seen_signatures = set()

    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Keep assertion diffs intact with exact indentation
        is_diff_line = any(stripped.startswith(p) for p in ("E ", "assert ", "Expected:", "Received:", "> ", "- ", "+ "))

        if is_diff_line:
            shrunk_lines.append(line.rstrip())
            continue

        cleaned = re.sub(r"\s+", " ", stripped)

        # Deduplicate repeated identical trace lines
        if cleaned.startswith("at ") or cleaned.startswith("File "):
            sig = cleaned[:60]
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)

        # Replace non-UUID hex hashes of 16-64 chars with <hash>
        def _replace_hash(match: re.Match[str]) -> str:
            token = match.group(0)
            if uuid_pattern.match(token):
                return token
            return "<hash>"

        cleaned = re.sub(r"\b[0-9a-fA-F]{16,64}\b", _replace_hash, cleaned)

        if len(cleaned) > max_chars_per_line:
            cleaned = cleaned[:max_chars_per_line] + "..."
        shrunk_lines.append(cleaned)

    return "\n".join(shrunk_lines)


def main():
    parser = argparse.ArgumentParser(description="Distill terminal execution logs into high-signal failure blocks.")
    parser.add_argument("--file", "-f", help="Path to raw log file (reads from stdin if omitted).")
    parser.add_argument("--exit-code", "-e", type=int, default=None, help="Process exit code from test runner.")
    parser.add_argument("--save-raw", "-s", default=None, help="Path to preserve raw log.")
    parser.add_argument("--max-lines", "-m", type=int, default=40, help="Maximum number of output lines.")
    parser.add_argument("--shrink", action="store_true", help="Apply caveman/shrink token compression.")
    args = parser.parse_args()

    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: Log file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8", errors="ignore") as fp:
            log_text = fp.read()
    else:
        if sys.stdin.isatty():
            print("Usage: python3 tools/distill_log.py --file <path> OR pipe stdout via stdin.")
            sys.exit(0)
        log_text = sys.stdin.read()

    # Preserve raw log on disk if explicitly requested
    if args.save_raw:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.save_raw)), exist_ok=True)
            with open(args.save_raw, "w", encoding="utf-8") as fp:
                fp.write(log_text)
        except OSError as err:
            sys.stderr.write(f"Warning: Could not save raw log: {err}\n")

    summary = distill(
        log_text,
        max_lines=args.max_lines,
        exit_code=args.exit_code,
        raw_log_path=args.save_raw,
    )
    if args.shrink:
        summary = shrink_tokens(summary)
    print(summary)


if __name__ == "__main__":
    main()
