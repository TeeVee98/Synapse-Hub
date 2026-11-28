# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_ci_summary_generator.py
Unit tests verifying rigorous, unbypassable JUnit XML parsing and DoD summary evaluation
in tools/report/ci_summary_generator.py.
"""

import dataclasses
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest
from tools.report.ci_summary_generator import (
    parse_junit_file,
    generate_markdown_summary,
)


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


def _write_junit(path: Path, name: str, cases: list[tuple[str, str]]) -> None:
    """Writes a minimal JUnit XML file with status in {'pass', 'fail', 'skip'}."""
    failures = sum(1 for _, st in cases if st == "fail")
    skipped = sum(1 for _, st in cases if st == "skip")
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<testsuite name="{name}" tests="{len(cases)}" failures="{failures}" errors="0" skipped="{skipped}">',
    ]
    for tc_name, st in cases:
        if st == "fail":
            lines.append(f'  <testcase name="{tc_name}"><failure>boom</failure></testcase>')
        elif st == "skip":
            lines.append(f'  <testcase name="{tc_name}"><skipped message="skipped"/></testcase>')
        else:
            lines.append(f'  <testcase name="{tc_name}"/>')
    lines.append("</testsuite>")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_valid_static_and_k6(root: Path, p95: float = 120.0, rate: float = 0.0, samples: int = 50) -> None:
    (root / "verify_all_report.json").write_text(
        json.dumps({"all_passed": True}),
        encoding="utf-8",
    )
    (root / "k6_summary.json").write_text(
        json.dumps(
            {
                "metrics": {
                    "http_req_duration": {"values": {"p(95)": p95}},
                    "http_req_failed": {"values": {"rate": rate}},
                    "http_reqs": {"values": {"count": samples}},
                }
            }
        ),
        encoding="utf-8",
    )


def test_evaluate_required_suite_passed_failed_and_incomplete():
    """Positive & Negative: RunEvidence evaluates passed, failed, and incomplete dispositions."""
    from tools.report.ci_summary_generator import RunEvidence, evaluate_required_suite

    good = RunEvidence(
        build_id="build-abc",
        run_id="run-1",
        suite="api",
        mode="staging",
        executed=10,
        failed=0,
        skipped=0,
        artifact_sha256="a" * 64,
    )
    assert evaluate_required_suite(good, "build-abc") == "passed"
    assert evaluate_required_suite(good, "build-other") == "incomplete"
    with pytest.raises(dataclasses.FrozenInstanceError):
        good.build_id = "mutated"  # type: ignore[misc]

    zero_exec = RunEvidence(
        build_id="build-abc",
        run_id="run-1",
        suite="api",
        mode="staging",
        executed=0,
        failed=0,
        skipped=3,
        artifact_sha256="a" * 64,
    )
    assert evaluate_required_suite(zero_exec, "build-abc") == "incomplete"

    failed_run = RunEvidence(
        build_id="build-abc",
        run_id="run-1",
        suite="api",
        mode="staging",
        executed=5,
        failed=1,
        skipped=0,
        artifact_sha256="a" * 64,
    )
    assert evaluate_required_suite(failed_run, "build-abc") == "failed"


def test_generate_markdown_summary_fully_executed_green_run():
    """Positive: Fully executed suites and finite k6 metrics with samples certify green."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        _write_junit(root / "api_junit.xml", "api", [("t1", "pass"), ("t2", "pass")])
        _write_junit(root / "web_junit.xml", "web", [("w1", "pass")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass"), ("m2", "skip")])

        md, all_passed = generate_markdown_summary(artifacts_dir=str(root))
        assert all_passed is True
        assert "DEFINITION OF DONE" in md
        assert "0 Warnings" not in md
        assert "all 204 tests" not in md
        assert "1 Skipped" in md


def test_generate_markdown_summary_rejects_all_skipped_junit_suites():
    """Negative: Three 1-case JUnit suites where every case is skipped must NOT certify."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        _write_junit(root / "api_junit.xml", "api", [("a1", "skip")])
        _write_junit(root / "web_junit.xml", "web", [("w1", "skip")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "skip")])

        md, all_passed = generate_markdown_summary(artifacts_dir=str(root))
        assert all_passed is False
        assert "DEFINITION OF DONE" not in md
        assert "0 Executed" in md or "0 Passed" in md


def test_generate_markdown_summary_rejects_empty_and_nan_k6_summary():
    """Negative: Empty k6 {}, zero-sample k6, bool/non-numeric, and NaN latency/rate block certification."""
    for payload in [
        "{}",
        json.dumps({"metrics": {"http_req_duration": {"values": {"p(95)": 10.0}}, "http_req_failed": {"values": {"rate": 0.0}}, "http_reqs": {"values": {"count": 0}}}}),
        json.dumps({"metrics": {"http_req_duration": {"values": {"p(95)": True}}, "http_req_failed": {"values": {"rate": 0.0}}, "http_reqs": {"values": {"count": 10}}}}),
        json.dumps({"metrics": {"http_req_duration": {"values": {"p(95)": float("nan")}}, "http_req_failed": {"values": {"rate": 0.0}}, "http_reqs": {"values": {"count": 10}}}}, allow_nan=True),
    ]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "verify_all_report.json").write_text(json.dumps({"all_passed": True}), encoding="utf-8")
            _write_junit(root / "api_junit.xml", "api", [("a1", "pass")])
            _write_junit(root / "web_junit.xml", "web", [("w1", "pass")])
            _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass")])
            (root / "k6_summary.json").write_text(payload, encoding="utf-8")

            md, all_passed = generate_markdown_summary(artifacts_dir=str(root))
            assert all_passed is False
            assert "QUALITY GATES FAILED" in md


def test_generate_markdown_summary_missing_shard_and_mismatched_build():
    """Negative: Missing expected shard or stale/mismatched candidate build exits blocked."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        _write_junit(root / "api_junit.xml", "api", [("a1", "pass")])
        _write_junit(root / "playwright-shard-1.xml", "web-1", [("w1", "pass")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass")])

        md_missing_shard, passed_shard = generate_markdown_summary(
            artifacts_dir=str(root),
            expected_shards=["playwright-shard-1", "playwright-shard-2"],
        )
        assert passed_shard is False
        assert "shard" in md_missing_shard.lower()

        (root / "playwright-shard-2.xml").write_text(
            (root / "playwright-shard-1.xml").read_text(encoding="utf-8").replace("w1", "w2"),
            encoding="utf-8",
        )
        (root / "candidate_manifest.json").write_text(
            json.dumps({"build_id": "old-sha-111"}),
            encoding="utf-8",
        )
        md_stale, passed_stale = generate_markdown_summary(
            artifacts_dir=str(root),
            candidate_build="new-sha-222",
            expected_shards=["playwright-shard-1", "playwright-shard-2"],
        )
        assert passed_stale is False
        assert "build" in md_stale.lower()


def test_generate_markdown_summary_mixed_skips_and_malformed_counters():
    """Boundary: Mixed skips show exact executed/skipped; malformed counters fail closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        _write_junit(root / "api_junit.xml", "api", [("a1", "pass"), ("a2", "pass"), ("a3", "skip")])
        _write_junit(root / "web_junit.xml", "web", [("w1", "pass")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass")])

        md, all_passed = generate_markdown_summary(artifacts_dir=str(root))
        assert all_passed is True
        assert "2 Passed, 0 Failed, 1 Skipped" in md

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        (root / "api_junit.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?><testsuite name="api" tests="1" failures="2" skipped="3"><testcase name="a1"/></testsuite>',
            encoding="utf-8",
        )
        _write_junit(root / "web_junit.xml", "web", [("w1", "pass")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass")])

        _, bad_passed = generate_markdown_summary(artifacts_dir=str(root))
        assert bad_passed is False


def test_ci_summary_cli_dedup_shards_and_exit_codes():
    """CLI & Resilience: Deduplicates identical shards and returns 0/1 CLI exit codes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        _write_junit(root / "api_junit.xml", "api", [("a1", "pass")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass")])

        sub1 = root / "shard1"
        sub2 = root / "shard1_copy"
        sub1.mkdir()
        sub2.mkdir()
        _write_junit(sub1 / "junit.xml", "web-shard-1", [("w1", "pass"), ("w2", "pass")])
        _write_junit(sub2 / "junit.xml", "web-shard-1", [("w1", "pass"), ("w2", "pass")])

        md, ok = generate_markdown_summary(artifacts_dir=str(root))
        assert ok is True
        assert "2 TCs" in md

        proc_ok = subprocess.run(
            [sys.executable, "tools/report/ci_summary_generator.py", "--artifacts-dir", str(root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc_ok.returncode == 0

        (root / "k6_summary.json").write_text("{}", encoding="utf-8")
        proc_fail = subprocess.run(
            [sys.executable, "tools/report/ci_summary_generator.py", "--artifacts-dir", str(root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc_fail.returncode == 1


def test_junit_detailed_missing_empty_and_suite_name_shards():
    """Boundary & Resilience: Missing/empty JUnit XML fails closed; root and child suite names satisfy shards."""
    from tools.report.ci_summary_generator import _parse_junit_detailed

    t, f, s, ok, names, digest = _parse_junit_detailed("definitely_missing_file_xyz.xml")
    assert (t, f, s, ok, digest) == (0, 0, 0, False, "")
    assert names == set()

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        (root / "api_junit.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?><testsuites></testsuites>',
            encoding="utf-8",
        )
        _write_junit(root / "web_junit.xml", "web", [("w1", "pass")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass")])
        _, passed_empty = generate_markdown_summary(artifacts_dir=str(root))
        assert passed_empty is False

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        _write_junit(root / "api_junit.xml", "root-api-shard", [("a1", "pass")])
        (root / "web_junit.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?><testsuites name="root-web-container"><testsuite name="child-web-shard" tests="1"><testcase name="w1"/></testsuite></testsuites>',
            encoding="utf-8",
        )
        _write_junit(root / "mobile_junit.xml", "mobile-shard", [("m1", "pass")])
        _, passed_named = generate_markdown_summary(
            artifacts_dir=str(root),
            expected_shards=["root-web-container", "child-web-shard"],
        )
        assert passed_named is True


def _write_rc_manifest(root: Path, overrides: dict | None = None) -> dict:
    manifest = {
        "build_id": "sha-rc-999",
        "run_id": "run-777",
        "environment": "staging",
        "lane": "release-candidate",
        "producers": {
            "api-suite": {"status": "success", "mode": "staging", "job": "rc-api-suite"},
            "e2e-crm-suite": {"status": "success", "mode": "staging", "job": "rc-e2e-suite"},
            "mobile-som-suite": {"status": "success", "mode": "device", "job": "rc-mobile-suite"},
            "perf-sla-sentinel": {"status": "success", "mode": "staging", "job": "rc-perf-suite"},
        },
    }
    if overrides:
        manifest.update(overrides)
    (root / "candidate_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_rc_candidate_manifest_valid_producers_certifies_green():
    """Positive: Valid candidate_manifest.json with matching SHA, run_id, environment, and live modes passes."""
    from tools.report.ci_summary_generator import validate_candidate_manifest

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        _write_junit(root / "api_junit.xml", "api", [("a1", "pass")])
        _write_junit(root / "web_junit.xml", "web", [("w1", "pass")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass")])
        manifest = _write_rc_manifest(root)

        ok, issues = validate_candidate_manifest(
            manifest,
            expected_build_id="sha-rc-999",
            expected_run_id="run-777",
            expected_environment="staging",
        )
        assert ok is True and issues == []

        md, all_passed = generate_markdown_summary(
            artifacts_dir=str(root),
            candidate_build="sha-rc-999",
        )
        assert all_passed is True
        assert "sha-rc-999" in md


def test_rc_rejects_cancelled_skipped_offline_substituted_and_replayed_artifacts(monkeypatch):
    """Negative: Cancelled producer, skipped job, offline-for-live substitution, or replayed run_id fails."""
    from tools.report.ci_summary_generator import validate_candidate_manifest

    base = {
        "build_id": "sha-rc-999",
        "run_id": "run-777",
        "environment": "staging",
        "lane": "release-candidate",
        "producers": {
            "api-suite": {"status": "success", "mode": "staging", "job": "rc-api"},
            "e2e-crm-suite": {"status": "success", "mode": "staging", "job": "rc-e2e"},
            "mobile-som-suite": {"status": "success", "mode": "device", "job": "rc-mob"},
            "perf-sla-sentinel": {"status": "success", "mode": "staging", "job": "rc-perf"},
        },
    }
    bad_cases = [
        {**base, "run_id": "run-old-replayed"},
        {**base, "producers": {**base["producers"], "api-suite": {"status": "cancelled", "mode": "staging"}}},
        {**base, "producers": {**base["producers"], "e2e-crm-suite": {"status": "skipped", "mode": "staging"}}},
        {**base, "producers": {**base["producers"], "api-suite": {"status": "success", "mode": "offline"}}},
        {**base, "producers": {k: v for k, v in base["producers"].items() if k != "mobile-som-suite"}},
    ]
    for bad in bad_cases:
        ok, issues = validate_candidate_manifest(
            bad,
            expected_build_id="sha-rc-999",
            expected_run_id="run-777",
            expected_environment="staging",
        )
        assert ok is False
        assert len(issues) >= 1

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        _write_junit(root / "api_junit.xml", "api", [("a1", "pass")])
        _write_junit(root / "web_junit.xml", "web", [("w1", "pass")])
        _write_junit(root / "mobile_junit.xml", "mobile", [("m1", "pass")])
        _write_rc_manifest(root, {"run_id": "run-replayed-1"})
        monkeypatch.setenv("SYNAPSE_CANDIDATE_BUILD", "sha-rc-999")
        monkeypatch.setenv("SYNAPSE_RUN_ID", "run-777")
        _, passed = generate_markdown_summary(artifacts_dir=str(root))
        assert passed is False


def test_ci_workflow_defines_release_candidate_lane_and_browser_matrix():
    """Boundary & CLI: ci_quality_gates.yml keeps offline PR lane and adds explicit release-candidate lane."""
    wf_path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci_quality_gates.yml"
    wf_text = wf_path.read_text(encoding="utf-8")
    assert "release_candidate" in wf_text
    assert "chromium firefox webkit" in wf_text
    assert "candidate_manifest.json" in wf_text
    assert 'SYNAPSE_API_OFFLINE: "1"' in wf_text
    assert "--expected-shards playwright-e2e-report-0,playwright-e2e-report-1,playwright-e2e-report-2,playwright-e2e-report-3" in wf_text
    assert '"producers"' in wf_text or "'producers'" in wf_text
    # RC lane must derive producer statuses from real suite runs & file hashes rather than hardcoding success
    rc_section = wf_text.split("rc-evidence-lane:", 1)[1].split("dod-acceptance:", 1)[0]
    assert 'PYTHONPATH="."' in rc_section or "PYTHONPATH=." in rc_section
    assert "with open(" in rc_section
    assert '"api-suite": {"status": "success"' not in rc_section
    assert "rc_api_junit.xml" in rc_section
    assert "rc_mobile_junit.xml" in rc_section


def test_rc_rejects_missing_or_empty_producers_and_producer_binding_drift():
    """Negative (TC-CI-01): RC manifest without producers, empty producers, or producer build/run drift fails closed."""
    from tools.report.ci_summary_generator import validate_candidate_manifest

    producerless_rc = {
        "build_id": "sha-rc-999",
        "run_id": "run-777",
        "environment": "staging",
        "lane": "release-candidate",
    }
    ok_missing, issues_missing = validate_candidate_manifest(
        producerless_rc,
        expected_build_id="sha-rc-999",
        expected_run_id="run-777",
        expected_environment="staging",
    )
    assert ok_missing is False
    assert any("producers" in msg.lower() for msg in issues_missing)

    empty_producers_rc = {**producerless_rc, "producers": {}}
    ok_empty, issues_empty = validate_candidate_manifest(
        empty_producers_rc,
        expected_build_id="sha-rc-999",
        expected_run_id="run-777",
        expected_environment="staging",
    )
    assert ok_empty is False
    assert any("producers" in msg.lower() for msg in issues_empty)

    ok_forced, issues_forced = validate_candidate_manifest(
        {"build_id": "sha-rc-999"},
        expected_build_id="sha-rc-999",
        require_producers=True,
    )
    assert ok_forced is False
    assert len(issues_forced) >= 1

    bad_binding_rc = {
        **producerless_rc,
        "producers": {
            "api-suite": {"status": "success", "mode": "staging", "build_id": "stale-sha", "run_id": "run-777"},
            "e2e-crm-suite": {"status": "success", "mode": "staging", "build_id": "sha-rc-999", "run_id": "wrong-run"},
            "mobile-som-suite": {"status": "success", "mode": "", "build_id": "sha-rc-999", "run_id": "run-777"},
            "perf-sla-sentinel": {"status": "success", "mode": "staging", "build_id": "sha-rc-999", "run_id": "run-777"},
        },
    }
    ok_bind, issues_bind = validate_candidate_manifest(
        bad_binding_rc,
        expected_build_id="sha-rc-999",
        expected_run_id="run-777",
        expected_environment="staging",
    )
    assert ok_bind is False
    assert len(issues_bind) >= 3


def test_shard_relative_directory_matching_cli_flag_and_unverified_empty_invariants():
    """Positive, Negative, Boundary & CLI (TC-CI-01): Relative shard dirs, --expected-shards CLI, and honest Unverified invariants."""
    # Boundary: empty directory never claims 100% verified invariants or present shards
    with tempfile.TemporaryDirectory() as empty_dir:
        empty_md, empty_ok = generate_markdown_summary(artifacts_dir=empty_dir)
        assert empty_ok is False
        assert "100% verified" not in empty_md
        assert "100% locators" not in empty_md
        assert "100% dynamic" not in empty_md
        assert "All expected shards present" not in empty_md
        assert "Not configured (unverified)" in empty_md
        assert "Unverified" in empty_md

    # Positive & Negative CLI: relative directory names match playwright-e2e-report-{0..3}
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        _write_valid_static_and_k6(root)
        (root / "api-test-report").mkdir()
        _write_junit(root / "api-test-report" / "api_junit.xml", "api", [("a1", "pass")])
        (root / "mobile-som-report").mkdir()
        _write_junit(root / "mobile-som-report" / "mobile_junit.xml", "mobile", [("m1", "pass")])

        for idx in range(4):
            shard_dir = root / f"playwright-e2e-report-{idx}"
            shard_dir.mkdir()
            _write_junit(shard_dir / "junit.xml", "e2e", [(f"crm_tc_{idx}", "pass")])

        shards_csv = "playwright-e2e-report-0,playwright-e2e-report-1,playwright-e2e-report-2,playwright-e2e-report-3"
        proc_ok = subprocess.run(
            [
                sys.executable,
                "tools/report/ci_summary_generator.py",
                "--artifacts-dir",
                str(root),
                "--expected-shards",
                shards_csv,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc_ok.returncode == 0, proc_ok.stdout + proc_ok.stderr
        assert "All expected shards present" in proc_ok.stdout
        assert "Unverified" not in proc_ok.stdout

        # Drop shard 2 -> must fail closed and pinpoint playwright-e2e-report-2
        (root / "playwright-e2e-report-2" / "junit.xml").unlink()
        proc_drop = subprocess.run(
            [
                sys.executable,
                "tools/report/ci_summary_generator.py",
                "--artifacts-dir",
                str(root),
                "--expected-shards",
                shards_csv,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc_drop.returncode == 1
        assert "playwright-e2e-report-2" in proc_drop.stdout
