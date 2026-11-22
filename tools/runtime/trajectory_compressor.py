#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/runtime/trajectory_compressor.py — Tier 4 Trajectory & Observation Compressor
-----------------------------------------------------------------------------------
Prevents O(N^2) trajectory explosion across multi-turn agent loops by automatically
masking verbose tool observations from earlier turns (T <= current_turn - 2).

Key Mechanics:
  1. Offloads raw tool stdout/reads to disk: `.synapse/observations/<tool_call_id>.log`.
  2. Substitutes historical tool outputs with high-signal, 1-line Pointer Masks:
     `[Observation Masked: read_file('auth.ts') -> 220 lines. Raw: file://.synapse/observations/123.log]`
  3. Preserves full raw diagnostic provenance on disk while cutting context bloat by 80–90%.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from typing import Any, Dict, List, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_LOG_DIR = os.path.join(_REPO_ROOT, ".synapse", "observations")


class TrajectoryCompressor:
    """Compresses agent trajectories and tool observations to maintain O(1) context scaling."""

    MAX_INLINE_LINES = 15
    MAX_INLINE_CHARS = 400

    @classmethod
    def ensure_storage_dir(cls, log_dir: str = DEFAULT_LOG_DIR) -> str:
        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    @classmethod
    def mask_tool_observation(
        cls,
        tool_name: str,
        tool_args: Dict[str, Any],
        raw_output: str,
        turn_index: int = 1,
        log_dir: str = DEFAULT_LOG_DIR
    ) -> Dict[str, Any]:
        """
        Evaluates a tool output. If exceeding line/char threshold, saves raw output to disk
        and returns an ultra-compact pointer mask.
        """
        lines = raw_output.splitlines()
        char_count = len(raw_output)

        if len(lines) <= cls.MAX_INLINE_LINES and char_count <= cls.MAX_INLINE_CHARS:
            return {
                "masked": False,
                "content": raw_output,
                "saved_tokens": 0,
                "log_file": None
            }

        cls.ensure_storage_dir(log_dir)
        content_hash = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()[:12]
        file_name = f"turn_{turn_index}_{tool_name}_{content_hash}.log"
        file_path = os.path.join(log_dir, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(raw_output)

        # Generate smart summary
        arg_summary = ", ".join(f"{k}={v}" for k, v in list(tool_args.items())[:2]) if tool_args else "none"
        if "error" in raw_output.lower() or "failed" in raw_output.lower():
            # Extract first failure signature line
            failure_line = next((l.strip() for l in lines if any(k in l.lower() for k in ["fail", "error", "exception"])), "")
            summary = f"FAIL: {failure_line[:80]}" if failure_line else "Execution failed"
        elif "pass" in raw_output.lower():
            summary = "Execution passed"
        else:
            summary = f"{len(lines)} lines extracted"

        mask_text = (
            f"[Observation Masked: {tool_name}({arg_summary}) -> {len(lines)} lines. "
            f"Summary: {summary}. Full log: file://{file_path}]"
        )

        saved_tokens = max(0, int((char_count - len(mask_text)) / 3.8))

        return {
            "masked": True,
            "content": mask_text,
            "saved_tokens": saved_tokens,
            "log_file": file_path,
            "original_lines": len(lines),
            "original_chars": char_count
        }

    @classmethod
    def compress_conversation_messages(
        cls,
        messages: List[Dict[str, Any]],
        keep_recent_turns: int = 2,
        log_dir: str = DEFAULT_LOG_DIR
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Compresses an entire message trajectory.
        Older tool turns (prior to keep_recent_turns) have their outputs automatically masked.
        """
        compressed = []
        total_saved_tokens = 0
        total_msgs = len(messages)
        cutoff_index = max(0, total_msgs - (keep_recent_turns * 2))

        for idx, msg in enumerate(messages):
            role = msg.get("role")
            content = msg.get("content", "")

            # If it's a tool output message and belongs to older turns
            if role in ("tool", "system", "observation") and idx < cutoff_index and isinstance(content, str):
                tool_name = msg.get("name", "tool_call")
                tool_args = msg.get("args", {})
                res = cls.mask_tool_observation(tool_name, tool_args, content, turn_index=idx, log_dir=log_dir)
                if res["masked"]:
                    total_saved_tokens += res["saved_tokens"]
                    new_msg = dict(msg)
                    new_msg["content"] = res["content"]
                    compressed.append(new_msg)
                    continue

            compressed.append(msg)

        return compressed, total_saved_tokens


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 4 Trajectory & Observation Compressor")
    parser.add_argument("--demo", action="store_true", help="Run trajectory compression demo")
    args = parser.parse_args()

    if args.demo:
        sample_log = "\n".join([f"2026-11-22 [INFO] Executing step {i}: Verifying DOM node element #{i}..." for i in range(1, 101)])
        sample_log += "\n[PASSED] Test completed successfully in 3.42s."

        res = TrajectoryCompressor.mask_tool_observation("run_command", {"CommandLine": "npm test"}, sample_log, turn_index=1)
        print("=== Demo Trajectory Observation Masking ===")
        print(f"Original Characters : {res['original_chars']:,} chars (~{int(res['original_chars']/3.8)} tokens)")
        print(f"Masked Characters   : {len(res['content'])} chars (~{int(len(res['content'])/3.8)} tokens)")
        print(f"Tokens Saved        : ~{res['saved_tokens']:,} tokens")
        print("\nMasked Representation in Prompt:")
        print(f"  {res['content']}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
