#!/usr/bin/env python3
"""
Cross-Platform CLI Smoke Test Suite
-----------------------------------
Validates that centralized CLI tools and the primary agent-qa entrypoint
execute cleanly with --help and appropriate subcommands across platforms.
"""

import os
import sys
import subprocess
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORE_CLI_SCRIPTS = [
    "tools/cli.py",
    "tools/verify_all.py",
    "tools/analyze_project.py",
    "tools/check_env.py",
    "tools/check_version_sync.py",
    "tools/bump_version.py",
    "tools/count_tokens.py",
    "tools/dashboard_generator.py",
    "tools/skillspector.py",
    "tools/skill_collision_guard.py",
    "tools/skill_vault.py",
    "tools/matrix_sharder.py",
    "tools/omni_transpiler.py",
    "tools/omni_parser.py",
    "tools/infer_linter.py",
    "tools/lint_ai_docs.py",
    "tools/sync_agent_rules.py",
    "tools/tot_exploratory_tester.py",
    "tools/auto_heal.py",
    "tools/auto_heal_reflexion.py",
    "tools/agentless_patcher.py",
    "tools/api_fuzzer.py",
    "tools/api_drift_sentinel.py",
    "tools/config_decoupler.py",
    "tools/db_sandbox.py",
    "tools/debt_harvester.py",
    "tools/distill_log.py",
    "tools/heuristic_locator_matcher.py",
    "tools/interview_story.py",
    "tools/micro_mutator.py",
    "tools/output_formatter.py",
    "tools/pinpoint_failure.py",
    "tools/reversible_sandbox.py",
    "tools/safety_firewall.py",
    "tools/senior_code_review.py",
    "tools/setup_project.py",
    "tools/spec_drift_sentinel.py",
    "tools/swe_qa_aci.py",
    "tools/synapse_qa_bench.py",
    "tools/telemetry_correlator.py",
    "tools/test_impact.py",
    "tools/test_memory_os.py",
    "tools/textgrad_mutation_optimizer.py",
    "tools/tms_sync_bridge.py",
    "tools/trace_data_flow.py",
    "tools/traffic_session_converter.py",
    "tools/update_sentinel.py",
    "tools/validate_groovy_scripts.py",
    "tools/visual_diff_canvas.py",
    "tools/visual_som_helper.py",
    "tools/watch_mode.py",
    "tools/wcag_audit.py",
    "tools/welcome_page.py",
]


class TestCLISmokeMatrix(unittest.TestCase):
    """Executes cross-platform CLI smoke validation for tool entrypoints."""

    def test_main_cli_entrypoint_help(self):
        """Verifies that python tools/cli.py --help succeeds and lists commands."""
        res = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "tools", "cli.py"), "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=REPO_ROOT,
        )
        self.assertEqual(res.returncode, 0, f"tools/cli.py failed: {res.stderr}")
        self.assertIn("agent-qa", res.stdout.lower() + res.stderr.lower())

    def test_all_core_cli_scripts_help(self):
        """Verifies that all 53 primary CLI tools exit 0 on --help."""
        failures = []
        for script_rel in CORE_CLI_SCRIPTS:
            script_path = os.path.join(REPO_ROOT, script_rel)
            if not os.path.exists(script_path):
                failures.append(f"{script_rel}: file does not exist")
                continue

            env = os.environ.copy()
            env["PYTHONPATH"] = f"{REPO_ROOT}:{os.path.join(REPO_ROOT, 'tools')}"
            res = subprocess.run(
                [sys.executable, script_path, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=REPO_ROOT,
                env=env,
            )
            if res.returncode != 0:
                failures.append(f"{script_rel}: exit code {res.returncode}, stderr: {res.stderr.strip()[:120]}")

        self.assertEqual(len(failures), 0, f"CLI smoke failures ({len(failures)}):\\n" + "\\n".join(failures))


if __name__ == "__main__":
    unittest.main()
