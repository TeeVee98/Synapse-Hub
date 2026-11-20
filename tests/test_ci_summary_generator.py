# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_ci_summary_generator.py
Unit tests verifying rigorous, unbypassable JUnit XML parsing and DoD summary evaluation
in tools/report/ci_summary_generator.py.
"""

import os
import tempfile
from tools.report.ci_summary_generator import parse_junit_file, generate_markdown_summary


def test_parse_junit_file_with_child_testsuite_failures():
    """Ensure failure in child <testsuite> is NEVER ignored even if root has tests attribute."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites tests="10" failures="0" errors="0">
    <testsuite name="suite1" tests="10" failures="4" errors="1">
        <testcase name="tc1"><failure message="failed">assert 1 == 0</failure></testcase>
        <testcase name="tc2"><error message="errored">ZeroDivisionError</error></testcase>
        <testcase name="tc3"/>
    </testsuite>
</testsuites>
"""
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
        f.write(xml_content)
        tmp_name = f.name

    try:
        total, fails, skipped = parse_junit_file(tmp_name)
        assert fails >= 5, f"Expected at least 5 failures/errors, got {fails}"
        assert total >= 3
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def test_parse_junit_file_direct_testcase_failures():
    """Ensure direct <testcase>/<failure> child elements are counted."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
    <testsuite name="subsuite" tests="2">
        <testcase name="tc1"><failure>fail</failure></testcase>
        <testcase name="tc2"><skipped>skip</skipped></testcase>
    </testsuite>
</testsuites>
"""
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
        f.write(xml_content)
        tmp_name = f.name

    try:
        total, fails, skipped = parse_junit_file(tmp_name)
        assert fails == 1
        assert skipped == 1
        assert total == 2
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def test_parse_junit_file_missing_file():
    """Non-existent XML file gracefully returns (0, 0, 0)."""
    assert parse_junit_file("non_existent_file_xyz_12345.xml") == (0, 0, 0)


def test_generate_markdown_summary_missing_artifacts():
    """When artifacts are missing, summary returns all_passed=False and reports MISSING."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        md, all_passed = generate_markdown_summary(artifacts_dir=tmp_dir)
        assert not all_passed
        assert "❌ QUALITY GATES FAILED" in md
        assert "❌ MISSING" in md


def test_generate_markdown_summary_catches_child_testsuite_failure():
    """Ensure generator does NOT certify DoD if child testsuite has failures."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a mock api_junit.xml with child failure
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites tests="10" failures="0" errors="0">
    <testsuite name="api" tests="10" failures="2" errors="0">
        <testcase name="tc1"><failure>AssertionError</failure></testcase>
    </testsuite>
</testsuites>
"""
        with open(os.path.join(tmp_dir, "api_junit.xml"), "w", encoding="utf-8") as f:
            f.write(xml_content)

        md, all_passed = generate_markdown_summary(artifacts_dir=tmp_dir)
        assert not all_passed, "Generator must NOT pass when API test has failures!"
        assert "❌ FAIL" in md
        assert "❌ QUALITY GATES FAILED" in md
