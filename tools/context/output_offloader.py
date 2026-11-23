# -*- coding: utf-8 -*-
"""Output Offloader Engine (tools/context/output_offloader.py).

Inspired by AgentScope 2.0's offload protocol:
Automatically offloads large tool outputs, verbose test traces, and console
logs to local disk storage when size exceeds threshold, returning a structured
reference pointer and bounded head/tail excerpts to preserve LLM context budget.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

from __future__ import annotations

import hashlib
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass(frozen=True)
class OffloadedArtifactRef:
    """Immutable metadata descriptor pointing to an offloaded artifact on disk."""

    artifact_id: str
    file_path: str
    total_bytes: int
    total_lines: int
    head_excerpt: str
    tail_excerpt: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_context_summary(self) -> str:
        """Renders a compact, LLM-friendly context reference string."""
        return (
            f"[OFFLOADED_OUTPUT artifact_id='{self.artifact_id}']\n"
            f"Note: Output exceeded threshold ({self.total_bytes:,} bytes, {self.total_lines:,} lines).\n"
            f"Saved to: {self.file_path}\n"
            f"--- Head Excerpt (First 5 lines) ---\n"
            f"{self.head_excerpt}\n"
            f"--- Tail Excerpt (Last 5 lines) ---\n"
            f"{self.tail_excerpt}\n"
            f"--- Use context_slicer or read_file on file_path to inspect full details ---"
        )


class OutputOffloader:
    """Manages threshold detection and safe atomic offloading of tool outputs."""

    DEFAULT_THRESHOLD_BYTES: int = 2048  # 2 KB
    DEFAULT_STORAGE_DIR: str = "scratch/offload"

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        threshold_bytes: int = DEFAULT_THRESHOLD_BYTES,
    ) -> None:
        self.storage_dir = os.path.abspath(storage_dir or self.DEFAULT_STORAGE_DIR)
        self.threshold_bytes = max(128, threshold_bytes)
        os.makedirs(self.storage_dir, exist_ok=True)

    def should_offload(self, content: str) -> bool:
        """Determines whether content exceeds the threshold for inline inclusion."""
        return len(content.encode("utf-8", errors="replace")) > self.threshold_bytes

    def process_output(
        self,
        raw_output: str,
        source_command: str = "tool_execution",
    ) -> Tuple[bool, str, Optional[OffloadedArtifactRef]]:
        """Processes raw tool output.

        If size exceeds threshold, atomically saves to storage_dir and returns:
            (was_offloaded=True, context_summary, OffloadedArtifactRef)
        Otherwise returns:
            (was_offloaded=False, raw_output, None)
        """
        if not raw_output:
            return False, "", None

        raw_bytes = raw_output.encode("utf-8", errors="replace")
        if len(raw_bytes) <= self.threshold_bytes:
            return False, raw_output, None

        # Generate unique deterministic hash and artifact ID
        content_hash = hashlib.sha256(raw_bytes).hexdigest()[:12]
        unique_token = uuid.uuid4().hex[:6]
        safe_prefix = "".join(c if c.isalnum() or c in "-_" else "_" for c in source_command[:16]).strip("_")
        safe_prefix = safe_prefix or "cmd"

        artifact_id = f"offload_{safe_prefix}_{content_hash}_{unique_token}"
        file_name = f"{artifact_id}.log"
        target_path = os.path.join(self.storage_dir, file_name)
        temp_path = f"{target_path}.tmp.{uuid.uuid4().hex}"

        # Atomic write to prevent partial reads under concurrency
        with open(temp_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(raw_output)
        os.replace(temp_path, target_path)

        lines = raw_output.splitlines()
        total_lines = len(lines)
        head_lines = lines[:5]
        tail_lines = lines[-5:] if total_lines >= 5 else lines

        ref = OffloadedArtifactRef(
            artifact_id=artifact_id,
            file_path=target_path,
            total_bytes=len(raw_bytes),
            total_lines=total_lines,
            head_excerpt="\n".join(head_lines),
            tail_excerpt="\n".join(tail_lines),
        )

        return True, ref.to_context_summary(), ref
