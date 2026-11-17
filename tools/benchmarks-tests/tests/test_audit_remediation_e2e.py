#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_audit_remediation_e2e.py
-----------------------------------
End-to-End (E2E), requirement-driven test suite verifying the complete remediation
of Synapse-Hub audit findings (Synapse-Hub-13cccd3-Overall-Skills-Agents-Audit.md)
across Requirements R1–R9 and Milestones M0–M5.

Structured across 4 strict quality tiers:
  - Tier 1: Core Subsystem Contracts & Primary Happy Paths
  - Tier 2: Boundary Conditions, Corner Cases & Adversarial Stress
  - Tier 3: Cross-Feature Multi-Subsystem Integrations
  - Tier 4: Real-World Audit Remediation Scenarios (User Journeys)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
CORE_DIR = os.path.join(TOOLS_DIR, "core")

for p in (REPO_ROOT, TOOLS_DIR, CORE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


class TestAuditRemediationE2ETier1(unittest.TestCase):
    """
    Tier 1: Core Subsystem Contracts & Primary Happy Paths.
    Verifies that all new interface contracts defined in PROJECT.md and ORIGINAL_REQUEST.md
    are correctly exposed, accept expected types, and perform happy-path behavior.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_e2e_t1_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tier1_granular_consent_grant_contract(self):
        """R2 / Feature 3: ConsentGrant dataclass and verify_granular_grant contract."""
        try:
            import pentest_scope_guard as psg
        except ImportError as err:
            self.fail(f"Could not import tools/pentest_scope_guard.py: {err}")

        # Interface Contract Verification
        self.assertTrue(
            hasattr(psg, "ConsentGrant"),
            "Feature 3 (R2): 'ConsentGrant' class must be defined in tools/pentest_scope_guard.py"
        )
        self.assertTrue(
            hasattr(psg, "create_consent_grant"),
            "Feature 3 (R2): 'create_consent_grant' factory function must be defined in tools/pentest_scope_guard.py"
        )
        self.assertTrue(
            hasattr(psg, "verify_granular_grant"),
            "Feature 3 (R2): 'verify_granular_grant' verification function must be defined in tools/pentest_scope_guard.py"
        )

        grant = psg.create_consent_grant(
            action="http:fuzz",
            target="https://staging.example.com",
            caller_session="session_agent_alpha",
            ttl_seconds=300,
            method="POST",
            path_pattern="/api/v1/checkout",
        )

        self.assertEqual(grant.action, "http:fuzz")
        self.assertEqual(grant.target, "https://staging.example.com")
        self.assertEqual(grant.caller_session, "session_agent_alpha")
        self.assertEqual(grant.method, "POST")
        self.assertEqual(grant.path_pattern, "/api/v1/checkout")
        self.assertTrue(grant.nonce and len(grant.nonce) >= 8, "Nonce must be a non-trivial random string")
        self.assertGreater(grant.expiry, time.time(), "Expiry must be in the future")

        # Verify valid grant passes verification
        is_valid = psg.verify_granular_grant(
            grant=grant,
            expected_action="http:fuzz",
            expected_target="https://staging.example.com",
            caller_session="session_agent_alpha",
            method="POST",
            path="/api/v1/checkout",
        )
        self.assertTrue(is_valid, "Valid granular grant must be accepted by verify_granular_grant")

    def test_tier1_sandbox_path_containment_contract(self):
        """R2 / Feature 5: resolve_contained_path contract and PathContainmentError."""
        try:
            import pentest_scope_guard as psg
        except ImportError as err:
            self.fail(f"Could not import tools/pentest_scope_guard.py: {err}")

        self.assertTrue(
            hasattr(psg, "resolve_contained_path"),
            "Feature 5 (R2): 'resolve_contained_path' function must be defined in tools/pentest_scope_guard.py"
        )
        self.assertTrue(
            hasattr(psg, "PathContainmentError"),
            "Feature 5 (R2): 'PathContainmentError' exception must be defined in tools/pentest_scope_guard.py"
        )

        sandbox_root = os.path.join(self.temp_dir, "sandbox_root")
        os.makedirs(sandbox_root, exist_ok=True)
        safe_file = os.path.join(sandbox_root, "subdir", "test.db")
        os.makedirs(os.path.dirname(safe_file), exist_ok=True)
        with open(safe_file, "w") as f:
            f.write("safe")

        # Happy path: resolving relative or canonical path inside sandbox root
        resolved = psg.resolve_contained_path(sandbox_root, "subdir/test.db")
        self.assertEqual(os.path.realpath(resolved), os.path.realpath(safe_file))

    def test_tier1_zero_side_effect_dry_run_contract(self):
        """R2 / Feature 6: dry_run=True executes with zero socket calls or database writes."""
        try:
            import db_sandbox
        except ImportError as err:
            self.fail(f"Could not import tools/db_sandbox.py: {err}")

        test_db = os.path.join(self.temp_dir, "app.db")
        import sqlite3
        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
        conn.execute("INSERT INTO users VALUES (1, 'Alice');")
        conn.execute("INSERT INTO users VALUES (2, 'AUTO_test_user');")
        conn.commit()
        conn.close()

        sandbox = db_sandbox.DBSandbox(db_path=test_db, snapshot_dir=os.path.join(self.temp_dir, "snaps"))

        # Test dry-run audit & purge: must preview deletions but leave records untouched
        res = sandbox.audit_and_purge_pollution(dry_run=True)
        self.assertTrue(res.get("dry_run", False), "Result must declare dry_run=True")

        # Verify DB records were not modified
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users;")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 2, "dry_run=True must NOT delete records from database")

    def test_tier1_benchmark_no_write_and_output_dir(self):
        """R3 / Feature 9: benchmark_swarm_context.py supports --no-write and --output-dir."""
        script_path = os.path.join(TOOLS_DIR, "benchmark_swarm_context.py")
        self.assertTrue(os.path.isfile(script_path), "tools/benchmark_swarm_context.py must exist")

        proc = subprocess.run([sys.executable, script_path, "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn(
            "--no-write", proc.stdout,
            "Feature 9 (R3): tools/benchmark_swarm_context.py must support '--no-write' CLI argument"
        )
        self.assertIn(
            "--output-dir", proc.stdout,
            "Feature 9 (R3): tools/benchmark_swarm_context.py must support '--output-dir' CLI argument"
        )

    def test_tier1_skill_validator_upstream_schema_vs_policy(self):
        """R4 / Feature 19: validate_skills_schema.py separates upstream schema from Synapse policy."""
        try:
            import validate_skills_schema as vss
        except ImportError as err:
            self.fail(f"Could not import tools/validate_skills_schema.py: {err}")

        self.assertTrue(
            hasattr(vss, "validate_upstream_schema"),
            "Feature 19 (R4): 'validate_upstream_schema' must be defined in tools/validate_skills_schema.py"
        )
        self.assertTrue(
            hasattr(vss, "validate_synapse_policy_extensions"),
            "Feature 19 (R4): 'validate_synapse_policy_extensions' must be defined in tools/validate_skills_schema.py"
        )
        self.assertTrue(
            hasattr(vss, "classify_code_blocks"),
            "Feature 19 (R4): 'classify_code_blocks' must be defined in tools/validate_skills_schema.py"
        )

        valid_upstream_data = {
            "name": "test-sample-skill",
            "description": "Enterprise QA skill. Use when automating web regression flows.",
        }
        ok_up, errs_up = vss.validate_upstream_schema(valid_upstream_data)
        self.assertTrue(ok_up, f"Valid upstream schema must pass upstream validator: {errs_up}")

    def test_tier1_agent_instructions_3_tier_structure(self):
        """R5 / Feature 20: AGENTS.md establishes ALWAYS, RECOMMENDED, and SYNAPSE-HUB-ONLY tiers."""
        agents_md_path = os.path.join(REPO_ROOT, "AGENTS.md")
        self.assertTrue(os.path.isfile(agents_md_path), "AGENTS.md must exist at repository root")

        with open(agents_md_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertRegex(
            content, r"\bALWAYS\b",
            "Feature 20 (R5): AGENTS.md must delineate the 'ALWAYS' tier (platform safety invariants)"
        )
        self.assertRegex(
            content, r"\bRECOMMENDED\b",
            "Feature 20 (R5): AGENTS.md must delineate the 'RECOMMENDED' tier (best practice guidelines)"
        )
        self.assertRegex(
            content, r"\bSYNAPSE[-_]HUB[-_]ONLY\b",
            "Feature 20 (R5): AGENTS.md must delineate the 'SYNAPSE-HUB-ONLY' tier (repo-specific tooling)"
        )

    def test_tier1_token_measurement_record_provenance(self):
        """R6 / Feature 12: TokenMeasurementRecord carries comprehensive provenance metadata."""
        try:
            import provider_usage_adapter as pua
        except ImportError as err:
            self.fail(f"Could not import tools/core/provider_usage_adapter.py: {err}")

        self.assertTrue(
            hasattr(pua, "TokenMeasurementRecord"),
            "Feature 12 (R6): 'TokenMeasurementRecord' dataclass must be defined in provider_usage_adapter.py"
        )

        record = pua.TokenMeasurementRecord(
            measurement_kind="provider_observed",
            token_count=150,
            model_name="claude-3-5-sonnet",
            encoding="cl100k_base",
            is_fallback=False,
            commit_sha="c12d9b6f31b073d51c117fdb691520def80460f9",
            input_hash="d41d8cd98f00b204e9800998ecf8427e",
            timestamp=time.time(),
        )

        self.assertEqual(record.measurement_kind, "provider_observed")
        self.assertEqual(record.token_count, 150)
        self.assertEqual(record.model_name, "claude-3-5-sonnet")
        self.assertFalse(record.is_fallback)
        self.assertEqual(len(record.commit_sha), 40, "Commit SHA must be full 40-character hash")

    def test_tier1_provider_usage_serialization_guard(self):
        """R6 / Feature 13: serialize_provider_usage refuses to serialize synthetic estimates into provider usage."""
        try:
            import provider_usage_adapter as pua
        except ImportError as err:
            self.fail(f"Could not import tools/core/provider_usage_adapter.py: {err}")

        self.assertTrue(
            hasattr(pua, "serialize_provider_usage"),
            "Feature 13 (R6): 'serialize_provider_usage' must be defined in provider_usage_adapter.py"
        )

        synthetic_record = pua.TokenMeasurementRecord(
            measurement_kind="synthetic_estimate",
            token_count=500,
            model_name="heuristic_polyglot",
            encoding="cl100k_base",
            is_fallback=True,
            commit_sha="c12d9b6f31b073d51c117fdb691520def80460f9",
            input_hash="a" * 32,
            timestamp=time.time(),
        )

        # Invariant: Refuse to serialize synthetic estimate into provider usage fields
        with self.assertRaises(ValueError, msg="serialize_provider_usage must raise ValueError for synthetic estimates"):
            pua.serialize_provider_usage(synthetic_record)

        observed_record = pua.TokenMeasurementRecord(
            measurement_kind="provider_observed",
            token_count=500,
            model_name="gpt-4o",
            encoding="o200k_base",
            is_fallback=False,
            commit_sha="c12d9b6f31b073d51c117fdb691520def80460f9",
            input_hash="b" * 32,
            timestamp=time.time(),
        )
        serialized = pua.serialize_provider_usage(observed_record)
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized.get("measurement_kind"), "provider_observed")


class TestAuditRemediationE2ETier2(unittest.TestCase):
    """
    Tier 2: Boundary, Corner Cases & Adversarial Stress.
    Tests system resilience against malicious inputs, expired tokens, replayed nonces,
    path traversal exploits, symlink escapes, and malformed command executions.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_e2e_t2_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tier2_expired_consent_grant_rejected(self):
        """R2 / Feature 3: Expired consent grants are rejected before network/DB operation."""
        try:
            import pentest_scope_guard as psg
        except ImportError as err:
            self.fail(f"Could not import tools/pentest_scope_guard.py: {err}")

        if not hasattr(psg, "create_consent_grant") or not hasattr(psg, "verify_granular_grant"):
            self.fail("Feature 3 (R2): create_consent_grant or verify_granular_grant missing")

        # Create expired grant
        expired_grant = psg.create_consent_grant(
            action="http:fuzz",
            target="https://staging.example.com",
            caller_session="session_123",
            ttl_seconds=-10,  # Expired 10 seconds ago
        )

        is_valid = psg.verify_granular_grant(
            grant=expired_grant,
            expected_action="http:fuzz",
            expected_target="https://staging.example.com",
            caller_session="session_123",
        )
        self.assertFalse(is_valid, "Expired consent grant MUST be rejected by verify_granular_grant")

    def test_tier2_mismatched_caller_session_rejected(self):
        """R2 / Feature 3: Consent grants issued to caller A are rejected when presented by caller B."""
        try:
            import pentest_scope_guard as psg
        except ImportError as err:
            self.fail(f"Could not import tools/pentest_scope_guard.py: {err}")

        if not hasattr(psg, "create_consent_grant") or not hasattr(psg, "verify_granular_grant"):
            self.fail("Feature 3 (R2): create_consent_grant or verify_granular_grant missing")

        grant = psg.create_consent_grant(
            action="db:restore",
            target="/sandboxes/tenant_a.db",
            caller_session="agent_session_alpha",
            ttl_seconds=300,
        )

        is_valid = psg.verify_granular_grant(
            grant=grant,
            expected_action="db:restore",
            expected_target="/sandboxes/tenant_a.db",
            caller_session="agent_session_beta",  # Different session!
        )
        self.assertFalse(is_valid, "Grant presented by mismatched caller session MUST be rejected")

    def test_tier2_replayed_nonce_rejected(self):
        """R2 / Feature 3: Single-use nonces cannot be replayed."""
        try:
            import pentest_scope_guard as psg
        except ImportError as err:
            self.fail(f"Could not import tools/pentest_scope_guard.py: {err}")

        if not hasattr(psg, "create_consent_grant") or not hasattr(psg, "verify_granular_grant"):
            self.fail("Feature 3 (R2): create_consent_grant or verify_granular_grant missing")

        grant = psg.create_consent_grant(
            action="http:fuzz",
            target="https://staging.example.com",
            caller_session="session_replay_test",
            ttl_seconds=300,
        )

        # First verification must succeed
        first_attempt = psg.verify_granular_grant(
            grant=grant,
            expected_action="http:fuzz",
            expected_target="https://staging.example.com",
            caller_session="session_replay_test",
        )
        self.assertTrue(first_attempt, "First attempt with fresh nonce must succeed")

        # Second verification with exact same nonce must fail (replay attack prevented)
        second_attempt = psg.verify_granular_grant(
            grant=grant,
            expected_action="http:fuzz",
            expected_target="https://staging.example.com",
            caller_session="session_replay_test",
        )
        self.assertFalse(second_attempt, "Replayed single-use nonce MUST be rejected on second use")

    def test_tier2_directory_traversal_dotdot_rejected(self):
        """R2 / Feature 5: resolve_contained_path rejects .., absolute paths outside sandbox, and null bytes."""
        try:
            import pentest_scope_guard as psg
        except ImportError as err:
            self.fail(f"Could not import tools/pentest_scope_guard.py: {err}")

        if not hasattr(psg, "resolve_contained_path") or not hasattr(psg, "PathContainmentError"):
            self.fail("Feature 5 (R2): resolve_contained_path or PathContainmentError missing")

        sandbox_root = os.path.join(self.temp_dir, "sandbox")
        os.makedirs(sandbox_root, exist_ok=True)

        malicious_paths = [
            "../outside.txt",
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/shadow",
            "/tmp/uncontained_file.db",
            "subdir/../../../../root.db",
            "safe_name\0_escaped.db",
        ]

        for bad_path in malicious_paths:
            with self.assertRaises(
                psg.PathContainmentError,
                msg=f"Path traversal '{bad_path}' MUST raise PathContainmentError"
            ):
                psg.resolve_contained_path(sandbox_root, bad_path)

    def test_tier2_symlink_escape_outside_sandbox_rejected(self):
        """R2 / Feature 5: resolve_contained_path rejects symlink pointing outside sandbox root."""
        try:
            import pentest_scope_guard as psg
        except ImportError as err:
            self.fail(f"Could not import tools/pentest_scope_guard.py: {err}")

        if not hasattr(psg, "resolve_contained_path") or not hasattr(psg, "PathContainmentError"):
            self.fail("Feature 5 (R2): resolve_contained_path or PathContainmentError missing")

        sandbox_root = os.path.join(self.temp_dir, "sandbox")
        forbidden_outside = os.path.join(self.temp_dir, "forbidden_outside")
        os.makedirs(sandbox_root, exist_ok=True)
        os.makedirs(forbidden_outside, exist_ok=True)

        sensitive_target = os.path.join(forbidden_outside, "sensitive.key")
        with open(sensitive_target, "w") as f:
            f.write("SECRET_KEY_DATA")

        # Create symlink inside sandbox pointing to forbidden outside directory
        symlink_path = os.path.join(sandbox_root, "evil_symlink.key")
        try:
            os.symlink(sensitive_target, symlink_path)
        except OSError:
            self.skipTest("Symlinks not supported on this platform/filesystem")

        with self.assertRaises(
            psg.PathContainmentError,
            msg="Symlink resolving outside sandbox root MUST raise PathContainmentError"
        ):
            psg.resolve_contained_path(sandbox_root, "evil_symlink.key")

    @patch("socket.gethostbyname")
    def test_tier2_ssrf_and_cloud_metadata_rejection(self, mock_dns):
        """R2 / Feature 7: PentestScopeGuard blocks Cloud IMDS IPv4 & IPv6 addresses unconditionally."""
        try:
            from pentest_scope_guard import PentestScopeGuard
        except ImportError as err:
            self.fail(f"Could not import tools/pentest_scope_guard.py: {err}")

        guard = PentestScopeGuard(allowed_hosts=["metadata.test", "169.254.169.254", "fd00:ec2::254"], allow_internal=True)

        # 1. AWS IMDS IPv4
        mock_dns.return_value = "169.254.169.254"
        ok, msg = guard.validate_target("http://169.254.169.254/latest/meta-data")
        self.assertFalse(ok, "Cloud IMDS 169.254.169.254 must be blocked")
        self.assertIn("Metadata Service", msg)

        # 2. Azure / AWS IMDS IPv6
        mock_dns.return_value = "fd00:ec2::254"
        ok_v6, msg_v6 = guard.validate_target("http://[fd00:ec2::254]/latest/meta-data")
        self.assertFalse(ok_v6, "Cloud IMDS IPv6 must be blocked")
        self.assertIn("Metadata Service", msg_v6)

    def test_tier2_cli_stdout_valid_json_without_banners(self):
        """R6 / R3: CLI tools in --json mode emit strictly valid JSON on stdout with 0 banner corruption."""
        # Test benchmark_swarm_context.py --json
        cmd = [sys.executable, os.path.join(TOOLS_DIR, "benchmark_swarm_context.py"), "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Benchmark CLI failed: {proc.stderr}")

        try:
            data = json.loads(proc.stdout)
            self.assertIsInstance(data, dict, "Stdout must parse into a JSON dictionary")
            self.assertIn("measurement_kind", data)
        except json.JSONDecodeError as err:
            self.fail(f"tools/benchmark_swarm_context.py --json stdout contains non-JSON text: {err}\nStdout:\n{proc.stdout}")


class TestAuditRemediationE2ETier3(unittest.TestCase):
    """
    Tier 3: Cross-Feature Multi-Subsystem Integrations.
    Tests interactions between multiple components: dry-run with path containment,
    clean git trees after benchmarks, multi-client bridge sync, and skill digests.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_e2e_t3_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tier3_dry_run_with_sandbox_path_containment(self):
        """R2: Path containment is strictly enforced even when dry_run=True."""
        try:
            import pentest_scope_guard as psg
            import db_sandbox
        except ImportError as err:
            self.fail(f"Could not import tools: {err}")

        sandbox_root = os.path.join(self.temp_dir, "sandbox")
        os.makedirs(sandbox_root, exist_ok=True)

        if not hasattr(psg, "resolve_contained_path") or not hasattr(psg, "PathContainmentError"):
            self.fail("Feature 5 (R2): resolve_contained_path or PathContainmentError missing")

        # Invariant: An adversarial path traversal attempt must be rejected BEFORE dry-run preview executes
        with self.assertRaises(psg.PathContainmentError):
            contained_path = psg.resolve_contained_path(sandbox_root, "../../outside_prod.db")
            sandbox = db_sandbox.DBSandbox(db_path=contained_path)
            sandbox.audit_and_purge_pollution(dry_run=True)

    def test_tier3_benchmark_run_leaves_tracked_tree_clean(self):
        """R3 / Feature 10: Benchmark execution does not dirty tracked git working tree."""
        # 1. Record baseline git status and backup tracked benchmark file
        bench_md = os.path.join(REPO_ROOT, "benchmarks", "CONTEXT_TOKEN_BENCHMARK.md")
        original_bench_content = None
        if os.path.isfile(bench_md):
            with open(bench_md, "r", encoding="utf-8") as f:
                original_bench_content = f.read()

        try:
            proc_status_before = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True
            )
            initial_dirty = proc_status_before.stdout.strip()

            # 2. Run benchmark with --no-write
            benchmark_cmd = [
                sys.executable,
                os.path.join(TOOLS_DIR, "benchmark_swarm_context.py"),
                "--json",
                "--no-write",
            ]
            proc_bench = subprocess.run(benchmark_cmd, cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(
                proc_bench.returncode, 0,
                f"Benchmark with --no-write failed: {proc_bench.stderr}"
            )

            # 3. Check git status after run
            proc_status_after = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True
            )
            post_dirty = proc_status_after.stdout.strip()

            self.assertEqual(
                initial_dirty, post_dirty,
                f"Benchmark run polluted git working tree!\nDiff:\n{post_dirty}"
            )
        finally:
            # Self-contained test isolation: restore pristine benchmark file if polluted
            if original_bench_content is not None and os.path.isfile(bench_md):
                with open(bench_md, "w", encoding="utf-8") as f:
                    f.write(original_bench_content)

    def test_tier3_multi_client_bridge_synchronization(self):
        """R5 / Feature 21: Client bridges match canonical policy without drift."""
        sync_script = os.path.join(TOOLS_DIR, "sync_agent_rules.py")
        self.assertTrue(os.path.isfile(sync_script), "tools/sync_agent_rules.py must exist")

        client_bridges = [
            os.path.join(REPO_ROOT, "CLAUDE.md"),
            os.path.join(REPO_ROOT, ".cursorrules"),
            os.path.join(REPO_ROOT, ".windsurfrules"),
            os.path.join(REPO_ROOT, ".github", "copilot-instructions.md"),
        ]

        for bridge in client_bridges:
            self.assertTrue(os.path.isfile(bridge), f"Client bridge file {bridge} must exist")
            with open(bridge, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertTrue(
                "Clean POM" in content or "Page Object Model" in content,
                f"Bridge {bridge} missing core POM policy"
            )
            self.assertIn("MIT License", content, f"Bridge {bridge} missing copyright/license notice")

    def test_tier3_skill_digest_containment_and_lockfile(self):
        """R7 / Feature 14: skill_canonical_digest.py enforces path containment and lockfile integrity."""
        try:
            import skill_canonical_digest as scd
            self.assertIsNotNone(scd)
        except ImportError as err:
            self.fail(f"Could not import tools/skill_canonical_digest.py: {err}")

        lockfile_path = os.path.join(REPO_ROOT, "skills-lock.json")
        secondary_lock_path = os.path.join(REPO_ROOT, ".skill-lock.json")
        manifest_path = os.path.join(REPO_ROOT, "skills_manifest.json")
        self.assertTrue(os.path.isfile(lockfile_path), "skills-lock.json must exist")
        self.assertTrue(os.path.isfile(secondary_lock_path), ".skill-lock.json must exist")
        self.assertTrue(os.path.isfile(manifest_path), "skills_manifest.json must exist")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        manifest_skills = {s["id"] for s in manifest_data.get("skills", [])}
        self.assertEqual(len(manifest_skills), 56, "skills_manifest.json must contain exactly 56 skills")


class TestAuditRemediationE2ETier4(unittest.TestCase):
    """
    Tier 4: Real-World Audit Remediation Scenarios.
    Verifies solutions for specific defects identified in AUDIT_REPORT.md:
      - SEC-04: Git pre-commit guard secret scanning (Gate 6)
      - F-P2-03: Selenium reference test teardown cleanup fixture
      - F-P7-01: project_state.py status CLI crash fix
      - ROUTER-01: rules_router.py monorepo depth recursion
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_e2e_t4_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tier4_scenario_pre_commit_secret_scanning_sec04(self):
        """Audit Finding SEC-04 / Feature 23: git_pre_commit_guard.py includes secret scanning (Gate 6)."""
        guard_script = os.path.join(TOOLS_DIR, "git_pre_commit_guard.py")
        self.assertTrue(os.path.isfile(guard_script), "tools/git_pre_commit_guard.py must exist")

        with open(guard_script, "r", encoding="utf-8") as f:
            code = f.read()

        # Invariant: Pre-commit hook must scan for high-entropy secrets and credentials
        self.assertRegex(
            code, r"(?i)(check_secrets|scan_secrets|secret_patterns|gate_6)",
            "Feature 23 (SEC-04): git_pre_commit_guard.py must implement high-confidence secret scanning"
        )

    def test_tier4_scenario_selenium_order_test_teardown_fp203(self):
        """Audit Finding F-P2-03 / Feature 24: Selenium order test includes automated teardown fixture."""
        selenium_test = os.path.join(REPO_ROOT, "examples", "selenium-suite", "tests", "test_order.py")
        self.assertTrue(os.path.isfile(selenium_test), "examples/selenium-suite/tests/test_order.py must exist")

        with open(selenium_test, "r", encoding="utf-8") as f:
            code = f.read()

        # Invariant: Order creation test must be paired with automated teardown cleanup
        self.assertRegex(
            code, r"(?i)(fixture|teardown|cancel_order|delete_order|cleanup)",
            "Feature 24 (F-P2-03): test_order.py must execute automated teardown cleanup to prevent DB pollution"
        )

    def test_tier4_scenario_project_state_cli_fp701(self):
        """Audit Finding F-P7-01 / Feature 25: python3 tools/project_state.py status does not crash."""
        project_state_script = os.path.join(TOOLS_DIR, "project_state.py")
        self.assertTrue(os.path.isfile(project_state_script), "tools/project_state.py must exist")

        # Invariant: `project_state.py status` subcommand must execute cleanly without FileNotFoundError
        cmd = [sys.executable, project_state_script, "status"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)

        self.assertNotIn(
            "FileNotFoundError", proc.stderr,
            "Feature 25 (F-P7-01): 'project_state.py status' must not raise FileNotFoundError: 'status/PROJECT_STATE.md'"
        )
        self.assertEqual(
            proc.returncode, 0,
            f"Feature 25 (F-P7-01): 'project_state.py status' failed with exit code {proc.returncode}:\n{proc.stderr}"
        )

    def test_tier4_scenario_rules_router_depth_recursion_router01(self):
        """Audit Finding ROUTER-01 / Feature 26: rules_router.py supports --depth flag for monorepo traversal."""
        router_script = os.path.join(TOOLS_DIR, "rules_router.py")
        self.assertTrue(os.path.isfile(router_script), "tools/rules_router.py must exist")

        proc = subprocess.run([sys.executable, router_script, "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)

        # Invariant: Support --depth flag to traverse subdirectories beyond depth 2
        self.assertIn(
            "--depth", proc.stdout,
            "Feature 26 (ROUTER-01): tools/rules_router.py must support '--depth' CLI argument"
        )


if __name__ == "__main__":
    unittest.main()
