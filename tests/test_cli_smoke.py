#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

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
    "tools/core/cli.py",
    "tools/core/verify_all.py",
    "tools/core/analyze_project.py",
    "tools/core/check_env.py",
    "tools/core/check_version_sync.py",
    "tools/core/bump_version.py",
    "tools/core/count_tokens.py",
    "tools/contrib/dashboard_generator.py",
    "tools/core/skillspector.py",
    "tools/lint/skill_collision_guard.py",
    "tools/core/skill_vault.py",
    "tools/orchestration/matrix_sharder.py",
    "tools/transpiler/omni_transpiler.py",
    "tools/transpiler/omni_parser.py",
    "tools/lint/infer_linter.py",
    "tools/core/init_config.py",
    "tools/lint/lint_ai_docs.py",
    "tools/core/sync_agent_rules.py",
    "tools/orchestration/tot_exploratory_tester.py",
    "tools/heal/auto_heal.py",
    "tools/heal/auto_heal_reflexion.py",
    "tools/heal/agentless_patcher.py",
    "tools/api/api_fuzzer.py",
    "tools/api/api_drift_sentinel.py",
    "tools/core/config_decoupler.py",
    "tools/core/db_sandbox.py",
    "tools/core/debt_harvester.py",
    "tools/core/distill_log.py",
    "tools/heal/heuristic_locator_matcher.py",
    "tools/contrib/interview_story.py",
    "tools/lint/micro_mutator.py",
    "tools/report/output_formatter.py",
    "tools/report/pinpoint_failure.py",
    "tools/heal/reversible_sandbox.py",
    "tools/security/safety_firewall.py",
    "tools/orchestration/senior_code_review.py",
    "tools/core/setup_project.py",
    "tools/api/spec_drift_sentinel.py",
    "tools/orchestration/swe_qa_aci.py",
    "tools/orchestration/synapse_qa_bench.py",
    "tools/report/telemetry_correlator.py",
    "tools/core/test_impact.py",
    "tools/core/test_memory_os.py",
    "tools/heal/ast_assertion_optimizer.py",
    "tools/orchestration/typed_prompt_signatures.py",
    "tools/heal/textgrad_mutation_optimizer.py",
    "tools/contrib/tms_sync_bridge.py",
    "tools/context/trace_data_flow.py",
    "tools/transpiler/traffic_session_converter.py",
    "tools/lint/update_sentinel.py",
    "tools/lint/validate_groovy_scripts.py",
    "tools/design/visual_diff_canvas.py",
    "tools/heal/visual_som_helper.py",
    "tools/core/watch_mode.py",
    "tools/contrib/wcag_audit.py",
    "tools/contrib/welcome_page.py",
    "tools/lint/pre_bash_guard.py",
    "tools/api/vcr_cassette_guard.py",
    "tools/perf/heap_leak_analyzer.py",
    "tools/perf/slow_test_profiler.py",
    "tools/orchestration/synapse_doctor.py",
]


class TestCLISmokeMatrix(unittest.TestCase):
    """Executes cross-platform CLI smoke validation for tool entrypoints."""

    def test_main_cli_entrypoint_help(self):
        """Verifies that python tools/cli.py --help succeeds and lists commands."""
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "tools", "core", "cli.py"), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            cwd=REPO_ROOT,
            env=env,
        )
        stdout = res.stdout or ""
        stderr = res.stderr or ""
        self.assertEqual(res.returncode, 0, f"tools/cli.py failed: {stderr}")
        self.assertIn("agent-qa", (stdout + stderr).lower())

    def test_all_core_cli_scripts_help(self):
        """Verifies that all 53 primary CLI tools exit 0 on --help."""
        failures = []
        for script_rel in CORE_CLI_SCRIPTS:
            script_path = os.path.join(REPO_ROOT, script_rel)
            if not os.path.exists(script_path):
                failures.append(f"{script_rel}: file does not exist")
                continue

            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join([REPO_ROOT, os.path.join(REPO_ROOT, "tools")])
            env["PYTHONIOENCODING"] = "utf-8"
            res = subprocess.run(
                [sys.executable, script_path, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=REPO_ROOT,
                env=env,
            )
            if res.returncode != 0:
                stderr_text = (res.stderr or "").strip()[:120]
                failures.append(f"{script_rel}: exit code {res.returncode}, stderr: {stderr_text}")

        self.assertEqual(len(failures), 0, f"CLI smoke failures ({len(failures)}):\n" + "\n".join(failures))

    def test_npm_launcher_blocks_py_bypass(self):
        """Security Regression (P0-2): bin/agent-qa.js must reject --py arbitrary Python pass-through."""
        import shutil
        if not shutil.which("node"):
            self.skipTest("node binary not available on PATH")
        res = subprocess.run(
            ["node", os.path.join(REPO_ROOT, "bin", "agent-qa.js"), "--py", "-c", "print(1)"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=REPO_ROOT,
        )
        self.assertNotEqual(res.returncode, 0, "bin/agent-qa.js must reject --py bypass with non-zero exit code")
        combined = (res.stdout or "") + (res.stderr or "")
        self.assertIn("Unauthorized top-level flag", combined)

    def test_phase2_infrastructure_cli_subcommands_registered_and_help_clean(self):
        """M6 Positive: Verifies all 11 Phase-2 infrastructure CLI commands register and exit 0 on --help."""
        from tools.core import cli

        parser = cli.build_parser("en")
        commands = cli.get_registered_commands(parser, "en")
        names = {c["name"] for c in commands}

        expected_cmds = [
            "cove",
            "memory-os",
            "harvest-plan",
            "dag-heal",
            "knowledge-lake",
            "cache-proxy",
            "harvest-journey",
            "grid",
            "schedule",
            "flow",
            "scaffold-tc",
        ]
        for cmd in expected_cmds:
            self.assertIn(cmd, names, f"Missing CLI subcommand: {cmd}")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        for cmd in expected_cmds:
            res = subprocess.run(
                [sys.executable, os.path.join(REPO_ROOT, "tools", "core", "cli.py"), cmd, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=REPO_ROOT,
                env=env,
            )
            self.assertEqual(res.returncode, 0, f"cli.py {cmd} --help failed: {res.stderr}")

    def test_phase2_infrastructure_cli_handlers_json_and_boundaries(self):
        """M6 Positive/Negative/Boundary: Validates JSON inspection handlers with zero daemon loops."""
        import argparse
        import io
        import json
        import tempfile
        from contextlib import redirect_stdout, redirect_stderr
        from tools.core import cli

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. knowledge-lake (--db-path :memory:, empty query boundary)
            buf = io.StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    cli.cmd_knowledge_lake(argparse.Namespace(db_path=":memory:", query="", json=True))
            self.assertEqual(cm.exception.code, 0)
            lake_payload = json.loads(buf.getvalue())
            self.assertEqual(lake_payload["status"], "OK")
            self.assertIsInstance(lake_payload["matches"], list)

            # 2. harvest-journey positive (inline empty events file) & negative (missing file)
            events_file = os.path.join(tmpdir, "events.json")
            with open(events_file, "w", encoding="utf-8") as ef:
                json.dump([{"session_id": "s1", "action": "navigate", "target": "/login"}], ef)
            buf = io.StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    cli.cmd_harvest_journey(argparse.Namespace(events_file=events_file, suite_name="Login", json=True))
            self.assertEqual(cm.exception.code, 0)
            jh_payload = json.loads(buf.getvalue())
            self.assertEqual(jh_payload["status"], "OK")
            self.assertGreaterEqual(jh_payload["journeys_count"], 1)

            err_buf = io.StringIO()
            with redirect_stderr(err_buf):
                with self.assertRaises(SystemExit) as cm_err:
                    cli.cmd_harvest_journey(
                        argparse.Namespace(events_file=os.path.join(tmpdir, "missing.json"), suite_name="Login", json=True)
                    )
            self.assertNotEqual(cm_err.exception.code, 0)

            # 3. grid status (--json)
            buf = io.StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    cli.cmd_grid(argparse.Namespace(workers=2, json=True))
            self.assertEqual(cm.exception.code, 0)
            grid_payload = json.loads(buf.getvalue())
            self.assertEqual(grid_payload["status"], "READY")
            self.assertEqual(grid_payload["max_workers"], 2)

            # 4. schedule status (--json, zero background loop)
            buf = io.StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    cli.cmd_schedule(argparse.Namespace(json=True))
            self.assertEqual(cm.exception.code, 0)
            sched_payload = json.loads(buf.getvalue())
            self.assertEqual(sched_payload["status"], "READY")
            self.assertIsInstance(sched_payload["tasks"], list)

            # 5. flow dry-run (--json)
            buf = io.StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    cli.cmd_flow(argparse.Namespace(json=True))
            self.assertEqual(cm.exception.code, 0)
            flow_payload = json.loads(buf.getvalue())
            self.assertEqual(flow_payload["status"], "OK")
            self.assertEqual(flow_payload["state"]["verified"], True)


if __name__ == "__main__":
    unittest.main()
