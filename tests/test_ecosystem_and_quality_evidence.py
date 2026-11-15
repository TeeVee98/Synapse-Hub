#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_ecosystem_and_quality_evidence.py — Verification of Ecosystem & Quality Evidence Standards
Enforces:
1. Pinned Reference Agent Skills validator conformance (53 skills, frontmatter, progressive disclosure).
2. Host interoperability across 7 declared AI agent platforms.
3. Rigorous benchmark empirical evidence (30-50 challenges across 11 domains, paired comparison, rubric).
4. Truth Anchor: Zero unauthorized superlative ranking claims ("#1", "số 1", "best in class").
5. Precise adoption metrics disambiguation (installs vs active/repeat usage).
100% UTF-8 No BOM.
"""

import json
import os
import re
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from pathlib import Path
from validate_skills_schema import run_validation, validate_skill
from validate_host_interop import run_all_host_verifications, save_interop_reports


class TestSkillsSchemaAndProgressiveDisclosure(unittest.TestCase):
    """Enforces Agent Skills schema, file references, and progressive disclosure hierarchy."""

    def test_all_53_skills_conform_to_schema(self):
        skills_dir = Path(REPO_ROOT) / ".agents" / "skills"
        self.assertTrue(skills_dir.is_dir(), "Skills directory must exist")
        total_scanned, failures = run_validation(skills_dir, check_links=True)
        self.assertEqual(failures, {}, f"Skill schema validation failed: {failures}")
        self.assertEqual(total_scanned, 53, "Must validate exactly 53 skills")

    def test_negative_control_rejects_invalid_frontmatter(self):
        """Negative test: schema validator must reject missing required fields or invalid types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_skill_md = Path(tmpdir) / "SKILL.md"
            with open(bad_skill_md, "w", encoding="utf-8") as f:
                f.write("---\nname: bad-skill\n---\n# Missing description\n")
            errors = validate_skill(bad_skill_md, check_links=False)
            self.assertTrue(len(errors) > 0, "Validator must reject frontmatter missing description")


class TestMultiHostInteroperability(unittest.TestCase):
    """Enforces multi-host discovery and execution compatibility across 7 declared hosts."""

    def test_verify_all_declared_hosts(self):
        report = run_all_host_verifications(REPO_ROOT)
        self.assertTrue(report["all_passed"], f"Host verification failed: {report}")
        self.assertEqual(report["total_hosts_evaluated"], 7, "Must verify all 7 declared hosts")
        self.assertEqual(report["passed_hosts"], 7, "All 7 declared hosts must pass")

        host_names = [h["host_name"] for h in report["hosts"]]
        expected_hosts = [
            "Google Antigravity",
            "Claude Code",
            "Cursor IDE",
            "GitHub Copilot",
            "Windsurf",
            "Node.js / NPX CLI",
            "Python CLI",
        ]
        for expected in expected_hosts:
            self.assertIn(expected, host_names)

    def test_host_interop_reports_generated(self):
        json_report = os.path.join(REPO_ROOT, "reports", "host_interop_matrix.json")
        md_report = os.path.join(REPO_ROOT, "reports", "HOST_INTEROP_MATRIX.md")
        if not os.path.isfile(json_report) or not os.path.isfile(md_report):
            matrix = run_all_host_verifications(REPO_ROOT)
            save_interop_reports(matrix, os.path.join(REPO_ROOT, "reports"))
        self.assertTrue(os.path.isfile(json_report), "host_interop_matrix.json must exist")
        self.assertTrue(os.path.isfile(md_report), "HOST_INTEROP_MATRIX.md must exist")

        with open(json_report, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(data.get("all_passed"))
        self.assertEqual(len(data.get("hosts", [])), 7)


class TestQABenchmarkEmpiricalEvidence(unittest.TestCase):
    """Enforces empirical rigor, challenge count, and paired comparison in benchmark suite."""

    def setUp(self):
        self.results_path = os.path.join(REPO_ROOT, "benchmarks", "qa_eval", "reports", "eval_results.json")
        if not os.path.isfile(self.results_path):
            import subprocess
            runner = os.path.join(REPO_ROOT, "benchmarks", "qa_eval", "eval_runner.py")
            subprocess.run([sys.executable, runner], cwd=REPO_ROOT, check=True, capture_output=True)
        self.assertTrue(os.path.isfile(self.results_path), "eval_results.json must exist")
        with open(self.results_path, "r", encoding="utf-8") as f:
            self.results = json.load(f)

    def test_minimum_challenge_volume(self):
        """Benchmark must contain 30-50 curated evaluation challenges."""
        total = self.results.get("total_challenges", 0)
        self.assertGreaterEqual(total, 30, f"Benchmark suite must contain at least 30 challenges, got {total}")
        self.assertLessEqual(total, 50, f"Benchmark suite upper bound is 50 challenges, got {total}")

    def test_required_failure_domains_present(self):
        """Benchmark must cover essential QA failure modes."""
        categories = self.results.get("categories", {})
        required_domains = [
            "fake_pass_tautology",
            "locator_drift",
            "api_contract_drift",
            "security",
            "triage",
            "negative_control",
        ]
        for domain in required_domains:
            self.assertIn(domain, categories, f"Required failure domain '{domain}' must be present in categories")
            self.assertGreater(categories[domain].get("total", 0), 0, f"Domain '{domain}' must have >= 1 challenge")

    def test_paired_comparison_evidence(self):
        """Benchmark must provide paired comparison between baseline and assisted agent."""
        paired = self.results.get("paired_comparison", {})
        self.assertIn("resolution_gain_pct", paired)
        self.assertIn("false_pass_reduction_pct", paired)
        self.assertIn("token_reduction_pct", paired)
        self.assertIn("cost_savings_pct", paired)

        baseline = self.results.get("baseline", {})
        synapse = self.results.get("synapse", {})
        self.assertIn("resolution_rate_pct", baseline)
        self.assertIn("resolution_rate_pct", synapse)
        self.assertGreater(synapse["resolution_rate_pct"], baseline["resolution_rate_pct"])

    def test_benchmark_metadata_and_limitations(self):
        """Benchmark results must document methodology, rubric, and limitations."""
        meta = self.results.get("benchmark_metadata", {})
        self.assertIn("version", meta)
        self.assertIn("git_commit", meta)
        self.assertIn("rubric", meta)
        self.assertIn("known_technical_limitations", meta)
        self.assertIn("adoption_metrics_definitions", meta)


class TestTruthAnchorZeroUnverifiedClaims(unittest.TestCase):
    """Enforces Truth Anchor: zero unsupported superlatives or claims of being '#1'."""

    FORBIDDEN_PATTERNS = [
        re.compile(r"#1\s+(?:QA|testing|framework|hub|solution)", re.IGNORECASE),
        re.compile(r"số\s*1\s+(?:QA|kiểm thử|thế giới|Việt Nam)", re.IGNORECASE),
        re.compile(r"best[\s-]in[\s-]class", re.IGNORECASE),
        re.compile(r"the\s+best\s+agent\s+skill", re.IGNORECASE),
        re.compile(r"top\s+ranking\s+agent", re.IGNORECASE),
    ]

    DOCS_TO_SCAN = [
        os.path.join(REPO_ROOT, "README.md"),
        os.path.join(REPO_ROOT, "README.en.md"),
        os.path.join(REPO_ROOT, "docs", "ARCHITECTURE.md"),
        os.path.join(REPO_ROOT, "docs", "ARCHITECTURE.en.md"),
    ]

    def test_no_unsupported_superlative_claims(self):
        for doc_path in self.DOCS_TO_SCAN:
            if not os.path.isfile(doc_path):
                continue
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in self.FORBIDDEN_PATTERNS:
                matches = pattern.findall(content)
                self.assertEqual(
                    matches,
                    [],
                    f"Forbidden superlative ranking claim '{matches}' found in {os.path.basename(doc_path)}",
                )


class TestAdoptionMetricsDisambiguation(unittest.TestCase):
    """Ensures adoption documentation strictly distinguishes downloads/stars from active use."""

    def test_adoption_definitions_documented(self):
        readme_bench = os.path.join(REPO_ROOT, "benchmarks", "qa_eval", "README.md")
        with open(readme_bench, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Registry Downloads / Installs", content)
        self.assertIn("Active / Repeat Usage", content)
        self.assertIn("Prohibition", content)


if __name__ == "__main__":
    unittest.main()
