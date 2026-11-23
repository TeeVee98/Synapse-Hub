# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for OutputOffloader (tests/test_output_offloader.py).

Verifies threshold boundary, atomic offloading, context summary integrity,
and edge cases.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

import os
import shutil
import tempfile
import pytest

from tools.context.output_offloader import OutputOffloader, OffloadedArtifactRef


@pytest.fixture
def temp_offload_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_offload_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_small_output_not_offloaded(temp_offload_dir):
    offloader = OutputOffloader(storage_dir=temp_offload_dir, threshold_bytes=1024)
    small_text = "PASSED: test_login_flow (100ms)"

    was_offloaded, summary, ref = offloader.process_output(small_text, source_command="pytest")

    assert was_offloaded is False
    assert summary == small_text
    assert ref is None
    # Storage dir should be empty
    assert len(os.listdir(temp_offload_dir)) == 0


def test_large_output_offloaded_atomically(temp_offload_dir):
    threshold = 500
    offloader = OutputOffloader(storage_dir=temp_offload_dir, threshold_bytes=threshold)

    # Generate 50 lines of output (> 2KB)
    lines = [f"Line {i:03d}: verbose trace log output payload..." for i in range(50)]
    large_text = "\n".join(lines)

    was_offloaded, summary, ref = offloader.process_output(large_text, source_command="jmeter_run")

    assert was_offloaded is True
    assert isinstance(ref, OffloadedArtifactRef)
    assert os.path.isfile(ref.file_path)
    assert ref.total_lines == 50
    assert ref.total_bytes == len(large_text.encode("utf-8"))

    # Verify file content on disk is identical to original
    with open(ref.file_path, "r", encoding="utf-8") as f:
        saved_content = f.read()
    assert saved_content == large_text

    # Verify summary structure
    assert "[OFFLOADED_OUTPUT" in summary
    assert "Line 000" in summary  # head excerpt
    assert "Line 049" in summary  # tail excerpt


def test_boundary_empty_string(temp_offload_dir):
    offloader = OutputOffloader(storage_dir=temp_offload_dir, threshold_bytes=500)
    was_offloaded, summary, ref = offloader.process_output("", source_command="test")
    assert was_offloaded is False
    assert summary == ""
    assert ref is None


def test_boundary_exact_threshold(temp_offload_dir):
    threshold = 200
    offloader = OutputOffloader(storage_dir=temp_offload_dir, threshold_bytes=threshold)
    exact_text = "x" * threshold

    was_offloaded, summary, ref = offloader.process_output(exact_text, source_command="test")
    assert was_offloaded is False
    assert summary == exact_text
    assert ref is None

    # Exceed by 1 byte
    over_text = exact_text + "y"
    was_offloaded, summary, ref = offloader.process_output(over_text, source_command="test")
    assert was_offloaded is True
    assert ref is not None
    assert ref.total_bytes == threshold + 1
