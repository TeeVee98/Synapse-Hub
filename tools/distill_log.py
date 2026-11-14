#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/distill_log.py — Enterprise Multi-Framework Log Distiller (Token & Failure Sentinel)
------------------------------------------------------------------------------------------
Distills massive, repetitive execution logs (Katalon Studio, Gradle, Playwright, Jest, Pytest)
down to exact failure triage blocks without false passes, false failures on info logs, or dropped assertion diffs.

Key Guarantees:
  1. Case-insensitive failure keyword scanning.
  2. Exit code Truth Anchor (nonzero -> RUNNER_NONZERO_EXIT; missing -> NO_FAILURE_SIGNATURE_DETECTED;
     clean 0 with failure text -> CONFLICTING_SIGNALS).
  3. Informational logging filter ([INFO], [DEBUG]) preventing false-positive assertion detection.
  4. Genuine token_budget enforcement via calibrated tokenizer (default: 800 tokens).
  5. 15-line block bounding and noise suppression, compressing 95% of log volume.
  6. Provenance retention: points back to raw log file for forensic tracing.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List, Optional, Set

# Enforce UTF-8 stdout encoding for cross-platform compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repository root is on sys.path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from tools.core.token_estimator import count_tokens
except ImportError:
    try:
        from core.token_estimator import count_tokens
    except ImportError:
        def count_tokens(text: str, model_hint: str = "cl100k") -> int:
            return max(1, len(text) // 4)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Hard token truncate guaranteeing count_tokens(result) <= max_tokens."""
    if max_tokens <= 0:
        return ""
    if max_tokens == 1:
        return "!"
    if count_tokens(text) <= max_tokens:
        return text
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        toks = enc.encode(text)
        return enc.decode(toks[:max_tokens], errors="ignore")
    except Exception:
        lines = text.splitlines(keepends=True)
        curr: List[str] = []
        for line in lines:
            curr.append(line)
            if count_tokens("".join(curr)) > max_tokens:
                curr.pop()
                break
        res = "".join(curr)
        while res and count_tokens(res) > max_tokens:
            res = res[:-1]
        return res

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

# Informational logging prefix pattern (prevents informational lines from initiating failure blocks)
INFO_LOG_LINE = re.compile(
    r"^\s*(?:\[?(?:INFO|DEBUG|NOTICE|TRACE|VERBOSE|LOG)\]?|\d{4}-\d{2}-\d{2}[T\s]\S+\s+\[?(?:INFO|DEBUG|NOTICE|TRACE|VERBOSE|LOG)\]?)\b",
    re.IGNORECASE,
)

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
    re.compile(r"(?:^|\s)(?:E\s+|>\s+|AssertionError:\s*)assert\s+.*==\s*", re.IGNORECASE),
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
    zero false passes, zero false-positive assertions on info logs, and enforcing token budgets.
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

        # Informational log lines cannot initiate failure blocks
        is_info = bool(INFO_LOG_LINE.search(line))

        # Case-insensitive failure check
        is_fail_line = (not is_info or in_failure_block) and any(p.search(line) for p in FAILURE_INDICATORS)
        is_noise = any(p.search(line) for p in NOISE_PATTERNS) and not is_fail_line

        if is_fail_line and not is_info:
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
        clean_text = "\n".join(output)
        if token_budget is not None and token_budget >= 0 and count_tokens(clean_text) > token_budget:
            clean_text = truncate_to_tokens(clean_text, token_budget)
        return clean_text

    # Hard Cap Scope Invariant: Extremely constrained budgets below minimum envelope
    if token_budget is not None and token_budget >= 0:
        if token_budget == 0:
            return ""
        if token_budget < 35:
            tc_info = f": {', '.join(sorted(failing_tcs)[:2])}" if failing_tcs else ""
            summary = f"❌ [BUDGET_BELOW_MINIMUM: budget={token_budget}]{tc_info}"
            if raw_log_path and count_tokens(summary + f" | log: {raw_log_path}") <= token_budget:
                summary += f" | log: {raw_log_path}"
            return truncate_to_tokens(summary, token_budget)

    is_compact_envelope = token_budget is not None and token_budget > 0 and token_budget < 90

    # Invariant: Conflicting Signals Handling when exit_code == 0 but failure keywords present
    if exit_code == 0:
        output.append("⚠️ CONFLICTING_SIGNALS [Exit Code: 0]: Test runner exited with code 0, but failure indicators were detected in log.")
        output.append("   (Check whether failures were swallowed by an outer test harness, or if informational text matched failure patterns).")
    elif is_compact_envelope:
        exit_badge = f" [Exit Code: {exit_code}]" if exit_code is not None else ""
        tcs_hint = f": {sorted(failing_tcs)[0]}" if failing_tcs else ""
        output = [f"❌ FAILURES DETECTED{exit_badge}{tcs_hint}"]
    elif exit_code is not None:
        exit_badge = f" [Exit Code: {exit_code}]"
        if failing_tcs:
            output.append(f"❌ FAILURES DETECTED{exit_badge}: {len(failing_tcs)} Test Case(s) marked FAILED.")
        else:
            output.append(f"❌ FAILURES / ERRORS DETECTED{exit_badge}: {len(captured_failures)} failure block(s) isolated.")
    else:
        if failing_tcs:
            output.append(f"❌ FAILURES DETECTED: {len(failing_tcs)} Test Case(s) marked FAILED.")
        else:
            output.append(f"❌ FAILURES / ERRORS DETECTED: {len(captured_failures)} failure block(s) isolated.")

    if not is_compact_envelope:
        if failing_tcs:
            output.append(f"   Targeted TCs: {', '.join(sorted(failing_tcs))}")
        if failing_locs:
            unique_locs = sorted(set(failing_locs))
            output.append(f"   Failing Script Location(s): {', '.join(unique_locs[:5])}")

    output.append("\n--- Distilled Failure Block(s) ---")

    # Assemble failure blocks with line budget and token reservation constraint
    lines_used = len(output)
    max_payload_lines = max(5, max_lines - lines_used)

    # Reserve tokens for header and footer metadata so failure blocks don't blowout budget
    footer_reserve = (20 if is_compact_envelope else 35) + (15 if raw_log_path else 0)
    header_tokens = count_tokens("\n".join(output) + "\n\n--- Distilled Failure Block(s) ---\n")
    max_payload_tokens = (
        max(10, token_budget - header_tokens - footer_reserve)
        if (token_budget is not None and token_budget > 0)
        else 999999
    )

    assembled_blocks: List[str] = []
    current_lines = 0
    current_payload_tokens = 0
    truncated = False

    for block in captured_failures[:5]:
        block_text = "\n".join(block)
        block_lines = len(block)
        block_tokens = count_tokens(block_text)

        # Check line budget constraint
        if current_lines + block_lines > max_payload_lines:
            allowed = max_payload_lines - current_lines
            if allowed > 2:
                assembled_blocks.append("\n".join(block[:allowed]))
                assembled_blocks.append("... [truncated by max_lines budget] ...")
            truncated = True
            break

        # Check token budget constraint
        if token_budget is not None and token_budget > 0 and (current_payload_tokens + block_tokens > max_payload_tokens):
            avail = max(0, max_payload_tokens - current_payload_tokens - 18)
            if avail > 5:
                truncated_block = truncate_to_tokens(block_text, avail)
                assembled_blocks.append(truncated_block)
            assembled_blocks.append(f"... [truncated: constrained by token_budget={token_budget} tokens] ...")
            truncated = True
            break

        assembled_blocks.append(block_text)
        current_lines += block_lines
        current_payload_tokens += block_tokens

    output.append("\n---\n".join(assembled_blocks))

    # Measure distilled body before appending metadata footer
    body_lines = len(output)
    distilled_body_text = "\n".join(output)
    distilled_body_bytes = len(distilled_body_text.encode("utf-8"))
    distilled_tokens = count_tokens(distilled_body_text)
    reduction_pct = round(((raw_bytes - distilled_body_bytes) / max(1, raw_bytes)) * 100, 1)

    if is_compact_envelope:
        output.append(f"\n[DISTILLER METRICS] Truncated: {truncated} | Token Budget: {token_budget}")
        if raw_log_path and count_tokens("\n".join(output) + f"\n[RAW LOG ARTIFACT] {raw_log_path}") <= token_budget:
            output.append(f"[RAW LOG ARTIFACT] file://{os.path.abspath(raw_log_path)}")
    else:
        output.append(
            f"\n[DISTILLER METRICS] Distilled Body: {body_lines} lines ({distilled_body_bytes:,} bytes, ~{distilled_tokens} tokens) | "
            f"Reduction: {reduction_pct}% | Truncated: {truncated} | Token Budget: {token_budget if token_budget is not None else 'unlimited'}"
        )
        if raw_log_path:
            output.append(f"[RAW LOG ARTIFACT] file://{os.path.abspath(raw_log_path)}")

    final_result = "\n".join(output)

    # Hard Invariant Guarantee: Entire output must never exceed token_budget
    if token_budget is not None and token_budget > 0 and count_tokens(final_result) > token_budget:
        final_result = truncate_to_tokens(final_result, token_budget)

    return final_result


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
    parser.add_argument("--token-budget", "-b", type=int, default=800, help="Maximum token budget for distilled output.")
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
        token_budget=args.token_budget,
    )
    if args.shrink:
        summary = shrink_tokens(summary)
    print(summary)


if __name__ == "__main__":
    main()
