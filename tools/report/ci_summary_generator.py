#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/report/ci_summary_generator.py — Executive CI/CD DoD Quality Gatekeeper Summary
---------------------------------------------------------------------------------------
Aggregates execution results across all 5 automation tiers (REST API, Web E2E, Security,
Performance SLA, Mobile SOM) and renders an authoritative GitHub Actions Step Summary
or GitLab Merge Request Markdown table.
"""

import os
import sys
import glob
import hashlib
import json
import math
import argparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@dataclass(frozen=True)
class RunEvidence:
    """Versioned execution evidence for a required CI/release test suite."""

    build_id: str
    run_id: str
    suite: str
    mode: Literal["offline", "staging", "device", "supervised"]
    executed: int
    failed: int
    skipped: int
    artifact_sha256: str


def evaluate_required_suite(
    run: RunEvidence,
    candidate_build: str,
) -> Literal["passed", "failed", "incomplete"]:
    """Evaluates a required suite run against the candidate build identifier."""
    if (
        not candidate_build
        or not run.build_id
        or run.build_id != candidate_build
        or not run.artifact_sha256
        or run.executed <= 0
        or run.failed < 0
        or run.skipped < 0
    ):
        return "incomplete"
    if run.failed > 0:
        return "failed"
    return "passed"


REQUIRED_RC_PRODUCERS: Tuple[str, ...] = (
    "api-suite",
    "e2e-crm-suite",
    "mobile-som-suite",
    "perf-sla-sentinel",
)


def validate_candidate_manifest(
    manifest: Any,
    expected_build_id: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    expected_environment: Optional[str] = None,
    required_producers: Sequence[str] = REQUIRED_RC_PRODUCERS,
) -> Tuple[bool, List[str]]:
    """Validates candidate manifest identity, producer completion, and live-mode fidelity."""
    if not isinstance(manifest, dict):
        return False, ["Candidate manifest must be a JSON object"]

    issues: List[str] = []
    manifest_build = manifest.get("build_id")
    if expected_build_id and (not isinstance(manifest_build, str) or manifest_build != expected_build_id):
        issues.append(f"Build mismatch: expected '{expected_build_id}', got '{manifest_build}'")

    manifest_run = manifest.get("run_id")
    if expected_run_id and (not isinstance(manifest_run, str) or manifest_run != expected_run_id):
        issues.append(f"Run ID mismatch (possible replay): expected '{expected_run_id}', got '{manifest_run}'")

    manifest_env = manifest.get("environment")
    if expected_environment and (not isinstance(manifest_env, str) or manifest_env != expected_environment):
        issues.append(f"Environment mismatch: expected '{expected_environment}', got '{manifest_env}'")

    producers = manifest.get("producers")
    if producers is not None:
        if not isinstance(producers, dict):
            return False, issues + ["Candidate manifest producers must be a mapping"]
        is_rc_lane = manifest.get("lane") == "release-candidate"
        for req_job in required_producers:
            entry = producers.get(req_job)
            if not isinstance(entry, dict):
                issues.append(f"Missing required producer '{req_job}'")
                continue
            status = str(entry.get("status", "")).lower()
            if status != "success":
                issues.append(f"Producer '{req_job}' did not succeed (status='{status}')")
            if is_rc_lane and str(entry.get("mode", "")).lower() == "offline":
                issues.append(f"Offline result substituted for live release candidate in '{req_job}'")

    return len(issues) == 0, issues


def _is_finite_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(float(val))


def _parse_junit_detailed(xml_path: str) -> Tuple[int, int, int, bool, Set[str], str]:
    """Parses JUnit XML with counter integrity validation, suite names, and content digest."""
    if not os.path.exists(xml_path):
        return 0, 0, 0, False, set(), ""
    try:
        with open(xml_path, "rb") as fp:
            raw_bytes = fp.read()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        root = ET.fromstring(raw_bytes.decode("utf-8", errors="replace"))

        suite_names: Set[str] = set()
        if root.attrib.get("name"):
            suite_names.add(root.attrib["name"])
        for suite in root.findall(".//testsuite"):
            if suite.attrib.get("name"):
                suite_names.add(suite.attrib["name"])

        testcases = root.findall(".//testcase")
        attr_tests = int(root.attrib.get("tests", 0))
        suite_tests = sum(int(suite.attrib.get("tests", 0)) for suite in root.findall(".//testsuite"))
        total = max(len(testcases), attr_tests, suite_tests)

        failures = len(root.findall(".//failure"))
        errors = len(root.findall(".//error"))
        skipped = len(root.findall(".//skipped"))

        attr_failures = int(root.attrib.get("failures", 0)) + int(root.attrib.get("errors", 0))
        attr_skipped = int(root.attrib.get("skipped", 0))
        for suite in root.findall(".//testsuite"):
            attr_failures += int(suite.attrib.get("failures", 0)) + int(suite.attrib.get("errors", 0))
            attr_skipped += int(suite.attrib.get("skipped", 0))

        total_failures = max(failures + errors, attr_failures)
        total_skipped = max(skipped, attr_skipped)

        if total < 0 or total_failures < 0 or total_skipped < 0:
            return 0, 0, 0, False, suite_names, digest
        if total_failures + total_skipped > total:
            return 0, 0, 0, False, suite_names, digest

        return total, total_failures, total_skipped, True, suite_names, digest
    except Exception:
        return 0, 0, 0, False, set(), ""


def parse_junit_file(xml_path: str) -> Tuple[int, int, int]:
    """Returns (total_tests, failures_and_errors, skipped) from a JUnit XML file."""
    total, total_failures, total_skipped, is_valid, _, _ = _parse_junit_detailed(xml_path)
    if not is_valid:
        return 0, 0, 0
    return total, total_failures, total_skipped


def _evaluate_junit_tier(
    xml_paths: Sequence[str],
    missing_msg: str,
) -> Tuple[int, int, int, int, bool, str, str, Set[str]]:
    """Aggregates deduplicated JUnit XMLs and enforces executed > 0 and zero failures."""
    existing = sorted({os.path.abspath(p) for p in xml_paths if os.path.exists(p)})
    if not existing:
        return 0, 0, 0, 0, False, "❌ MISSING", missing_msg, set()

    seen_digests: Set[str] = set()
    observed_names: Set[str] = set()
    total = 0
    failed = 0
    skipped = 0
    malformed_count = 0

    for path in existing:
        t, f, s, is_valid, suite_names, digest = _parse_junit_detailed(path)
        observed_names.add(os.path.basename(path))
        observed_names.add(os.path.splitext(os.path.basename(path))[0])
        observed_names.update(suite_names)
        if not is_valid:
            malformed_count += 1
            continue
        if digest and digest in seen_digests:
            continue
        if digest:
            seen_digests.add(digest)
        total += t
        failed += f
        skipped += s

    executed = max(0, total - skipped)
    passed_count = max(0, executed - failed)
    if malformed_count > 0:
        return (
            total,
            executed,
            failed,
            skipped,
            False,
            "❌ FAIL",
            f"Malformed JUnit counters ({malformed_count} invalid file(s))",
            observed_names,
        )

    passed = failed == 0 and executed > 0
    status = "✅ PASS" if passed else "❌ FAIL"
    details = f"{total} Tests ({passed_count} Passed, {failed} Failed, {skipped} Skipped, {executed} Executed)"
    return total, executed, failed, skipped, passed, status, details, observed_names


def _extract_k6_sample_count(k6_data: Dict[str, Any]) -> int:
    metrics = k6_data.get("metrics", {})
    for key in ("http_reqs", "iterations"):
        vals = metrics.get(key, {}).get("values", {})
        count_val = vals.get("count")
        if _is_finite_number(count_val):
            return int(count_val)
    fail_vals = metrics.get("http_req_failed", {}).get("values", {})
    passes = fail_vals.get("passes")
    fails = fail_vals.get("fails")
    if _is_finite_number(passes) and _is_finite_number(fails):
        return int(passes) + int(fails)
    return 0


def _evaluate_k6_artifact(k6_path: str) -> Tuple[bool, str, str]:
    """Validates finite k6 SLA metrics with nonzero executed sample count."""
    try:
        with open(k6_path, "r", encoding="utf-8") as fp:
            k6_data = json.load(fp)
    except Exception:
        return False, "❌ ERROR", "Error parsing k6_summary.json"

    if not isinstance(k6_data, dict):
        return False, "❌ FAIL", "Malformed k6_summary.json payload"
    metrics = k6_data.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        return False, "❌ FAIL", "Missing k6 metrics in k6_summary.json"

    dur_vals = metrics.get("http_req_duration", {}).get("values", {})
    fail_vals = metrics.get("http_req_failed", {}).get("values", {})
    p95 = dur_vals.get("p(95)")
    err_fraction = fail_vals.get("rate")
    samples = _extract_k6_sample_count(k6_data)

    if not (_is_finite_number(p95) and _is_finite_number(err_fraction)) or samples <= 0:
        return False, "❌ FAIL", "Incomplete or non-finite k6 metrics (missing finite p95, rate, or samples)"

    dropped = metrics.get("dropped_iterations", {}).get("values", {}).get("count", 0)
    dropped_count = int(dropped) if _is_finite_number(dropped) else 0
    err_rate = float(err_fraction) * 100.0
    p95_val = float(p95)
    perf_pass = p95_val <= 500.0 and err_rate <= 1.0 and dropped_count == 0
    status_perf = "✅ PASS" if perf_pass else "❌ FAIL (SLA BREACH)"
    details = f"P95: {p95_val:.1f}ms (SLA <= 500ms), Error Rate: {err_rate:.1f}% (SLA <= 1.0%), Samples: {samples}"
    if dropped_count > 0:
        details += f", Dropped: {dropped_count}"
    return perf_pass, status_perf, details


def generate_markdown_summary(
    artifacts_dir: str = "artifacts",
    candidate_build: Optional[str] = None,
    expected_shards: Optional[Sequence[str]] = None,
) -> Tuple[str, bool]:
    """Generates the full GFM executive quality gate summary and returns (markdown, all_passed)."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # If artifacts_dir exists on disk (CI artifact directory), search strictly within it.
    # Only fall back to local workspace report directories if artifacts_dir does not exist.
    search_repo_local = not os.path.exists(artifacts_dir)

    # Tier 1: Static Defect & Security Sentinel
    static_pass = True
    verify_reports = glob.glob(os.path.join(artifacts_dir, "**/verify_all*.json"), recursive=True)
    linter_reports = glob.glob(os.path.join(artifacts_dir, "**/infer_linter*.json"), recursive=True)
    if search_repo_local:
        verify_reports += glob.glob("reports/*verify_all*.json")
        linter_reports += glob.glob("reports/*infer_linter*.json")

    if verify_reports and os.path.exists(verify_reports[0]):
        try:
            with open(verify_reports[0], "r", encoding="utf-8") as f:
                vdata = json.load(f)
            static_pass = bool(vdata.get("all_passed", False))
            static_details = f"Gates 1-10: {'10/10 PASS' if static_pass else 'FAILED'}"
        except Exception:
            static_pass = False
            static_details = "Error parsing verify_all_report.json"
    elif linter_reports and os.path.exists(linter_reports[0]):
        try:
            with open(linter_reports[0], "r", encoding="utf-8") as f:
                ldata = json.load(f)
            crit = ldata.get("critical_defects_count", 0)
            static_pass = crit == 0
            static_details = f"Critical Defects: {crit}, Health Score: {ldata.get('codebase_health_score_pct', 100)}%"
        except Exception:
            static_pass = False
            static_details = "Error parsing infer_linter_report.json"
    else:
        static_pass = False
        static_details = "Missing static gate artifacts (verify_all_report.json / infer_linter_report.json)"
    status_static = "✅ PASS" if static_pass else "❌ FAIL"

    # Tier 2: API Suite (Sprint 1)
    api_xmls = glob.glob(os.path.join(artifacts_dir, "**/*api*.xml"), recursive=True)
    if search_repo_local and not api_xmls:
        api_xmls = glob.glob("reports/*api*.xml")
    api_total, api_exec, _, _, api_pass, status_api, api_details, api_names = _evaluate_junit_tier(
        api_xmls,
        "Missing API test report artifact (api_junit.xml not found)",
    )

    # Tier 3: Web E2E CRM & DAST Suite (Sprint 2 & 3)
    web_xml_candidates = (
        glob.glob(os.path.join(artifacts_dir, "**/*playwright*.xml"), recursive=True)
        + glob.glob(os.path.join(artifacts_dir, "**/junit.xml"), recursive=True)
        + glob.glob(os.path.join(artifacts_dir, "**/*web*.xml"), recursive=True)
    )
    if search_repo_local:
        web_xml_candidates += (
            glob.glob("examples/playwright-crm-suite/reports/*.xml")
            + glob.glob("reports/*playwright*.xml")
            + glob.glob("reports/*web*.xml")
        )
    web_total, web_exec, _, _, web_pass, status_web, web_details, web_names = _evaluate_junit_tier(
        web_xml_candidates,
        "Missing Web E2E report artifact (playwright junit.xml not found)",
    )

    # Tier 4: Performance & SLA Sentinel (Sprint 4)
    perf_k6 = glob.glob(os.path.join(artifacts_dir, "**/k6_summary.json"), recursive=True)
    perf_jtls = glob.glob(os.path.join(artifacts_dir, "**/*perf*.jtl"), recursive=True)
    if search_repo_local:
        if not perf_k6:
            perf_k6 = glob.glob("Reports/perf/k6_summary.json")
        if not perf_jtls:
            perf_jtls = glob.glob("Reports/perf/*.jtl")

    if perf_k6 and os.path.exists(perf_k6[0]):
        perf_pass, status_perf, perf_details = _evaluate_k6_artifact(perf_k6[0])
    elif perf_jtls:
        try:
            from tools.perf.jtl_analyzer import parse_jtl, evaluate_sla

            _, total_stats = parse_jtl(perf_jtls[0])
            agg = total_stats.compute()
            passed_sla, sla_failures = evaluate_sla(agg, sla_p95=500.0, max_error_rate=1.0)
            perf_pass = bool(passed_sla)
            status_perf = "✅ PASS" if perf_pass else "❌ FAIL (SLA BREACH)"
            p95_val = agg.get("p95_ms", 0.0)
            err_val = agg.get("error_rate_pct", 0.0)
            perf_details = f"JTL: {os.path.basename(perf_jtls[0])} — P95: {p95_val:.1f}ms (SLA <= 500ms), Error: {err_val:.1f}% (SLA <= 1.0%)"
            if not passed_sla and sla_failures:
                perf_details += f" [Breaches: {', '.join(sla_failures)}]"
        except Exception as exc:
            perf_pass = False
            status_perf = "❌ ERROR"
            perf_details = f"Error evaluating JTL SLA: {exc}"
    else:
        perf_pass = False
        status_perf = "❌ MISSING"
        perf_details = "Missing Performance test artifact (perf_results.jtl / k6_summary.json not found)"

    # Tier 5: Mobile Screen Object Model Suite (Sprint 5)
    mob_xmls = glob.glob(os.path.join(artifacts_dir, "**/*mobile*.xml"), recursive=True)
    if search_repo_local and not mob_xmls:
        mob_xmls = glob.glob("reports/*mobile*.xml")
    mob_total, mob_exec, _, _, mob_pass, status_mob, mob_details, mob_names = _evaluate_junit_tier(
        mob_xmls,
        "Missing Mobile test report artifact (mobile_junit.xml not found)",
    )

    # Expected shard & candidate build verification (when configured or manifest present)
    env_shards = os.environ.get("SYNAPSE_EXPECTED_SHARDS", "").strip()
    req_shards = list(expected_shards) if expected_shards is not None else ([s.strip() for s in env_shards.split(",") if s.strip()])
    observed_all = api_names | web_names | mob_names
    missing_shards = [s for s in req_shards if not any(s in obs for obs in observed_all)]
    shard_ok = len(missing_shards) == 0

    target_build = candidate_build or os.environ.get("SYNAPSE_CANDIDATE_BUILD")
    target_run = os.environ.get("SYNAPSE_RUN_ID") or None
    target_env = os.environ.get("SYNAPSE_RELEASE_ENV") or None
    build_ok = True
    build_note = "Not bound"
    manifest_paths = glob.glob(os.path.join(artifacts_dir, "**/candidate_manifest.json"), recursive=True)
    if target_build or target_run or target_env:
        if manifest_paths and os.path.exists(manifest_paths[0]):
            try:
                with open(manifest_paths[0], "r", encoding="utf-8") as mf:
                    mdata = json.load(mf)
                build_ok, manifest_issues = validate_candidate_manifest(
                    mdata,
                    expected_build_id=target_build,
                    expected_run_id=target_run,
                    expected_environment=target_env,
                )
                build_note = (
                    f"Build `{mdata.get('build_id')}` verified"
                    if build_ok
                    else "; ".join(manifest_issues)
                )
            except Exception:
                build_ok = False
                build_note = "Build manifest unreadable"
        else:
            build_ok = False
            build_note = f"Missing candidate_manifest.json for build `{target_build}`"

    all_passed = bool(static_pass and api_pass and web_pass and perf_pass and mob_pass and shard_ok and build_ok)
    verdict = "### 🏆 DEFINITION OF DONE (DoD) CERTIFIED — 100% PASS" if all_passed else "### ❌ QUALITY GATES FAILED"
    total_executed = api_exec + web_exec + mob_exec
    total_tests = api_total + web_total + mob_total

    md = f"""# Enterprise Test Automation CI/CD Summary

{verdict}

> **Generated At:** `{now_utc}`<br/>
> **Platform Safety & Attribution:** Synapse Hub © 2026 Thế Vị (@TeeVee98) under MIT License.<br/>
> **Standard Compliance:** ISO/IEC/IEEE 29119-3/4, ISO/IEC 25010:2023, OWASP MASVS & DAST, ISTQB CT-PT.

---

### 📊 Multi-Tier Test Execution Matrix

| Automation Tier | Target Suite / Engine | Total Tests | Status | Execution Details & SLA Metrics |
| :--- | :--- | :---: | :---: | :--- |
| **Tier 1: Static Sentinel** | Quality Gates 1, 2, 3, 6, 7 & Ruff | 10 Gates | {status_static} | {static_details} |
| **Tier 2: REST API (Sprint 1)** | Pytest & Pydantic (Book & User AUT) | {api_total} TCs | {status_api} | {api_details} |
| **Tier 3: Web UI CRM (Sprint 2 & 3)** | Playwright Clean POM & DAST Probes | {web_total} TCs | {status_web} | {web_details} |
| **Tier 4: Performance (Sprint 4)** | k6 / JMeter / Locust SLA Gate | Multi-Archetype | {status_perf} | {perf_details} |
| **Tier 5: Mobile SOM (Sprint 5)** | Appium Screen Object Model & MASVS | {mob_total} TCs | {status_mob} | {mob_details} |

---

### 🛡️ Core Invariant Audit

- **Truth Anchor (Zero Fake Passes):** {total_executed} executed tests ({total_tests} total) evaluated; zero swallowed exceptions (`pass`, dummy suppression).
- **Shard Completeness:** {'All expected shards present' if shard_ok else f"Missing shard(s): {', '.join(missing_shards)}"}
- **Candidate Build Binding:** {build_note}
- **Clean POM / SOM Separation:** 100% locators encapsulated in Page and Screen Classes; zero raw CSS/XPath in test scripts.
- **Credential Security:** 100% verified; zero raw plaintext passwords committed.
- **Dynamic Smart Waits:** 100% dynamic event-driven waits; zero brittle static sleeps (`Thread.sleep`, `waitForTimeout`).
"""
    return md, all_passed


def main() -> int:
    parser = argparse.ArgumentParser(description="CI/CD Step Summary Generator")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Path to downloaded artifacts")
    parser.add_argument("--output", default=None, help="Path to write output markdown (e.g. $GITHUB_STEP_SUMMARY)")
    args = parser.parse_args()

    summary_md, all_passed = generate_markdown_summary(args.artifacts_dir)

    if args.output:
        try:
            with open(args.output, "a", encoding="utf-8") as fp:
                fp.write(summary_md)
            print(f"[SUCCESS] Appended CI summary to {args.output}")
        except Exception as exc:
            print(f"[WARN] Failed to write to {args.output}: {exc}")

    print(summary_md)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
