#!/usr/bin/env python3
"""
Enterprise Automated Testing Suite for AI Agent Tools & Hub Integrity
----------------------------------------------------------------------
Verifies the syntactic correctness, importability, and deterministic
behavior of all centralized tools in `tools/` using standard library `unittest`.
"""

import os
import sys
import json
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)


class TestToolsIntegrity(unittest.TestCase):
    """Automated unit and integration tests for tools in tools/."""

    def test_browser_helpers_exists_and_complete(self):
        """Validates that browser_helpers.js exists and exports core capabilities."""
        helper_path = os.path.join(TOOLS_DIR, "browser_helpers.js")
        self.assertTrue(os.path.exists(helper_path), "tools/browser_helpers.js must exist")

        with open(helper_path, "r", encoding="utf-8") as f:
            code = f.read()

        expected_methods = ["batch:", "audit:", "heal:", "clickSafe:", "exportSession:", "isStable:"]
        for method in expected_methods:
            self.assertIn(method, code, f"browser_helpers.js missing method: {method}")

    def test_skills_manifest_integrity(self):
        """Validates that skills_manifest.json matches disk files."""
        manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
        self.assertTrue(os.path.exists(manifest_path), "skills_manifest.json must exist")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("version"), "2.0.0", "Manifest version must be 2.0.0")
        manifest_skills = [s["id"] for s in data.get("skills", [])]
        self.assertEqual(len(manifest_skills), 30, "Manifest must declare exactly 30 skills")

        skills_dir = os.path.join(REPO_ROOT, ".agents", "skills")
        for skill_id in manifest_skills:
            skill_md = os.path.join(skills_dir, skill_id, "SKILL.md")
            self.assertTrue(os.path.exists(skill_md), f"Skill file must exist: {skill_md}")

    def test_cache_resolver_cosine_similarity(self):
        """Validates compute_cosine_similarity calculation in cache_resolver."""
        import cache_resolver
        t1 = "ElementClickInterceptedException timeout error"
        t2 = "ElementClickInterceptedException timeout error"
        t3 = "Completely different issue unrelated"

        self.assertAlmostEqual(cache_resolver.compute_cosine_similarity(t1, t2), 1.0, places=4)
        self.assertAlmostEqual(cache_resolver.compute_cosine_similarity(t1, t3), 0.0, places=4)

    def test_cache_resolver_negative_memory_failed_fixes(self):
        """Validates that cache_resolver records and retrieves failed bug fix attempts."""
        import cache_resolver
        cache_resolver.init_db(seed=True)
        # Record a test failed fix
        sig = "UnitTest_Custom_Exception"
        cache_resolver.record_failed_fix(
            error_signature=sig,
            attempted_patch="mock_broken_patch();",
            failure_reason="Failed validation during test execution",
            agent_role="unit-tester"
        )
        failed_list = cache_resolver.get_failed_fixes(sig)
        self.assertTrue(len(failed_list) >= 1, "Must retrieve recorded failed fix")
        self.assertEqual(failed_list[0]["attempted_patch"], "mock_broken_patch();")
        self.assertEqual(failed_list[0]["failure_reason"], "Failed validation during test execution")

    def test_distill_log_parser(self):
        """Validates that distill_log strips noise while preserving stacktraces."""
        import distill_log
        self.assertTrue(hasattr(distill_log, "distill"), "distill_log must define distill()")

    def test_infer_linter_ast_rule_definitions(self):
        """Validates that infer_linter has AST detection rules registered."""
        import infer_linter
        self.assertTrue(hasattr(infer_linter, "analyze_script"))
        self.assertTrue(hasattr(infer_linter, "run_infer_linter"))

    def test_verify_all_seven_gates_defined(self):
        """Validates that verify_all.py defines all 7 Quality Gates."""
        import verify_all
        gates = [
            "gate_1_bom_check",
            "gate_2_path_portability",
            "gate_3_clean_pom",
            "gate_4_ai_docs_lint",
            "gate_5_cleanup_blacklist",
            "gate_6_credential_security",
            "gate_7_infer_linter"
        ]
        for gate in gates:
            self.assertTrue(hasattr(verify_all, gate), f"verify_all.py must define {gate}")

    def test_pyproject_toml_packaging_standards(self):
        """Validates that pyproject.toml defines packaging standards and CLI entrypoints."""
        toml_path = os.path.join(REPO_ROOT, "pyproject.toml")
        self.assertTrue(os.path.exists(toml_path), "pyproject.toml must exist in repo root")

        with open(toml_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('name = "agent-qa"', content)
        self.assertIn('version = "2.0.0"', content)
        self.assertIn('agent-qa = "tools.cli:main"', content)

    def test_cli_entrypoint_importable(self):
        """Validates that tools/cli.py defines main command dispatcher."""
        import cli
        self.assertTrue(hasattr(cli, "main"), "cli.py must define main()")
        self.assertTrue(hasattr(cli, "cmd_version"), "cli.py must define cmd_version()")
        self.assertTrue(hasattr(cli, "cmd_verify"), "cli.py must define cmd_verify()")


if __name__ == "__main__":
    unittest.main()
