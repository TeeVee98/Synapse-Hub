#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit tests for tools/security_coverage_ledger.py
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.security_coverage_ledger import CoverageLedgerManager


class TestSecurityCoverageLedger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger_file = Path(self.temp_dir.name) / "coverage-ledger.json"
        self.mgr = CoverageLedgerManager(self.ledger_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_canonical_id_generation_rfc3986(self):
        # 1. Standard identifiers
        cid1 = CoverageLedgerManager.canonical_id("web_api", "auth", "billing", "idor")
        self.assertEqual(cid1, "web_api::auth::billing::idor")

        # 2. Spaces and uppercase letters (RFC 3986 percent encoding)
        cid2 = CoverageLedgerManager.canonical_id("Web API", "Boundary Auth", "User Service", "IDOR")
        self.assertEqual(cid2, "Web%20API::Boundary%20Auth::User%20Service::IDOR")

        # 3. Special characters: slashes, colons, hashes, unicode
        cid3 = CoverageLedgerManager.canonical_id("api/v1", "oauth:jwt", "tenant#1", "prompt_injection", lifecycle="runtime")
        self.assertEqual(cid3, "api%2Fv1::oauth%3Ajwt::tenant%231::prompt_injection::runtime")

    def test_add_and_validate_planned_unit(self):
        unit = self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id=None,
            status="planned",
        )
        self.assertEqual(unit.status, "planned")
        self.assertIsNone(unit.agent_id)
        errors = self.mgr.validate()
        self.assertEqual(len(errors), 0)

    def test_validate_rejects_windows_device_names_in_agent_id(self):
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id="con",
            status="in_progress",
        )
        errors = self.mgr.validate()
        self.assertTrue(any("Windows reserved device name" in e for e in errors))

    def test_validate_rejects_invalid_status(self):
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            status="invalid_status",
        )
        errors = self.mgr.validate()
        self.assertTrue(any("Invalid status" in e for e in errors))

    def test_state_invariants_planned_rejects_agent_or_evidence(self):
        # Planned unit with assigned agent_id must fail
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id="hunter-1",
            status="planned",
        )
        errors = self.mgr.validate()
        self.assertTrue(any("Planned unit must be unassigned" in e for e in errors))

    def test_state_invariants_in_progress(self):
        # 1. in_progress without agent_id fails
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id=None,
            status="in_progress",
        )
        errors = self.mgr.validate()
        self.assertTrue(any("In-progress unit requires an assigned agent_id" in e for e in errors))

        # 2. in_progress with agent_id passes
        self.mgr.units.clear()
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id="hunter-01",
            status="in_progress",
        )
        errors = self.mgr.validate()
        self.assertEqual(len(errors), 0)

    def test_state_invariants_covered(self):
        # 1. Covered without evidence fails
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id="hunter-01",
            status="covered",
        )
        errors = self.mgr.validate()
        self.assertTrue(any("requires non-empty reviewed_paths" in e for e in errors))

        # 2. Covered with complete evidence passes
        self.mgr.units.clear()
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id="hunter-01",
            status="covered",
            reviewed_paths=["controllers/billing.py"],
            local_checks=["assert_tenant_isolation()"],
        )
        errors = self.mgr.validate()
        self.assertEqual(len(errors), 0)

    def test_state_invariants_candidate(self):
        # Candidate requires agent_id, evidence, and result_fingerprints
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id="hunter-01",
            status="candidate",
            reviewed_paths=["controllers/billing.py"],
            local_checks=["assert_tenant_isolation()"],
            result_fingerprints=["sha256:abcd1234efgh5678"],
        )
        errors = self.mgr.validate()
        self.assertEqual(len(errors), 0)

    def test_state_invariants_blocked(self):
        # Blocked requires agent_id, context evidence, and non-empty unresolved
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id="hunter-01",
            status="blocked",
            reviewed_paths=["controllers/billing.py"],
            local_checks=["check_credentials()"],
            unresolved=["Database seed fixture unavailable on CI"],
        )
        errors = self.mgr.validate()
        self.assertEqual(len(errors), 0)

    def test_state_invariants_deferred_and_out_of_scope(self):
        # Deferred must be unassigned and have unresolved explanation
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            status="deferred",
            unresolved=["Deferred to Phase 3 after SSO migration"],
        )
        errors = self.mgr.validate()
        self.assertEqual(len(errors), 0)

    def test_non_candidate_rejects_fingerprints(self):
        # Covered unit with result_fingerprints must be rejected
        self.mgr.add_unit(
            surface="web_api",
            boundary="auth",
            subsystem="billing",
            attack_class="idor",
            agent_id="hunter-01",
            status="covered",
            reviewed_paths=["src/auth.py"],
            local_checks=["check_jwt()"],
            result_fingerprints=["fingerprint_123"],
        )
        errors = self.mgr.validate()
        self.assertTrue(any("must have empty result_fingerprints" in e for e in errors))

    def test_dual_document_format_loading(self):
        # 1. Test top-level JSON array format (Cloudflare native)
        array_path = Path(self.temp_dir.name) / "ledger_array.json"
        array_data = [
            {
                "coverage_id": "surface1::bound1::sub1::idor",
                "surface": "surface1",
                "boundary": "bound1",
                "subsystem": "sub1",
                "attack_class": "idor",
                "status": "planned",
                "wave": 1,
            }
        ]
        array_path.write_text(json.dumps(array_data), encoding="utf-8")
        mgr_array = CoverageLedgerManager(array_path)
        self.assertEqual(len(mgr_array.units), 1)
        self.assertEqual(mgr_array.format, "array")

        # 2. Test object format with 'units' key (Synapse Hub native)
        object_path = Path(self.temp_dir.name) / "ledger_object.json"
        object_data = {
            "$schema": "synapse://schemas/v1/coverage-ledger.json",
            "total_units": 1,
            "units": array_data,
        }
        object_path.write_text(json.dumps(object_data), encoding="utf-8")
        mgr_object = CoverageLedgerManager(object_path)
        self.assertEqual(len(mgr_object.units), 1)
        self.assertEqual(mgr_object.format, "object")

    def test_mathematical_metrics_calculation(self):
        # 1 covered, 1 candidate, 1 blocked, 1 out_of_scope
        self.mgr.add_unit(
            surface="s1", boundary="b1", subsystem="sub1", attack_class="idor",
            agent_id="h1", status="covered", reviewed_paths=["a.py"], local_checks=["c1"]
        )
        self.mgr.add_unit(
            surface="s2", boundary="b2", subsystem="sub2", attack_class="sqli",
            agent_id="h1", status="candidate", reviewed_paths=["b.py"], local_checks=["c2"],
            result_fingerprints=["fp1"]
        )
        self.mgr.add_unit(
            surface="s3", boundary="b3", subsystem="sub3", attack_class="xss",
            agent_id="h1", status="blocked", reviewed_paths=["c.py"], local_checks=["c3"],
            unresolved=["blocked by auth mock"]
        )
        self.mgr.add_unit(
            surface="s4", boundary="b4", subsystem="sub4", attack_class="dos",
            status="out_of_scope", unresolved=["not testing rate limit in unit tier"]
        )

        metrics = self.mgr.get_metrics()
        self.assertEqual(metrics["total_units"], 4)
        self.assertEqual(metrics["in_scope_units"], 3)  # 4 - 1 out_of_scope
        self.assertEqual(metrics["audited_units"], 2)   # 1 covered + 1 candidate
        # 2 / 3 * 100 = 66.67%
        self.assertEqual(metrics["audited_coverage_pct"], 66.67)
        # 1 / 3 * 100 = 33.33%
        self.assertEqual(metrics["blocker_rate_pct"], 33.33)

    def test_cli_commands(self):
        script_path = Path(__file__).parent.parent / "tools" / "security_coverage_ledger.py"
        test_file = Path(self.temp_dir.name) / "cli_ledger.json"

        # 1. init
        res_init = subprocess.run(
            [sys.executable, str(script_path), "init", "-f", str(test_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res_init.returncode, 0)
        self.assertTrue(test_file.exists())

        # 2. add
        res_add = subprocess.run(
            [
                sys.executable, str(script_path), "add", "-f", str(test_file),
                "-s", "api", "-b", "auth", "--subsystem", "user", "-a", "idor",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res_add.returncode, 0)

        # 3. validate
        res_val = subprocess.run(
            [sys.executable, str(script_path), "validate", str(test_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res_val.returncode, 0)

        # 4. summary --json
        res_sum = subprocess.run(
            [sys.executable, str(script_path), "summary", str(test_file), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res_sum.returncode, 0)
        sum_data = json.loads(res_sum.stdout)
        self.assertEqual(sum_data["total_units"], 1)

    def test_omitted_coverage_id_auto_generates(self):
        """Units omitting coverage_id in JSON must auto-generate canonical IDs via __post_init__."""
        p = Path(self.temp_dir.name) / "auto_id.json"
        p.write_text(
            json.dumps([{"surface": "web", "boundary": "auth", "subsystem": "login", "attack_class": "sqli"}]),
            encoding="utf-8",
        )
        mgr = CoverageLedgerManager(p)
        self.assertEqual(len(mgr.units), 1)
        self.assertEqual(mgr.units[0].coverage_id, "web::auth::login::sqli")

    def test_hostile_json_resilience(self):
        """Hostile JSON arrays, non-list units, and malformed items should be handled gracefully without crashing."""
        # 1. Non-dict primitive items
        p1 = Path(self.temp_dir.name) / "hostile_primitives.json"
        p1.write_text(json.dumps([1, 2, "string", None]), encoding="utf-8")
        mgr1 = CoverageLedgerManager(p1)
        self.assertEqual(len(mgr1.units), 0)

        # 2. Non-list 'units' in object format
        p2 = Path(self.temp_dir.name) / "hostile_non_list.json"
        p2.write_text(json.dumps({"units": 42}), encoding="utf-8")
        mgr2 = CoverageLedgerManager(p2)
        self.assertEqual(len(mgr2.units), 0)

        # 3. Truncated items with missing fields
        p3 = Path(self.temp_dir.name) / "hostile_incomplete.json"
        p3.write_text(json.dumps([{"surface": "only_surface"}]), encoding="utf-8")
        mgr3 = CoverageLedgerManager(p3)
        self.assertEqual(len(mgr3.units), 1)

    def test_wave_validation(self):
        """Validation must reject wave values that are not integers >= 1."""
        u1 = self.mgr.add_unit(surface="s", boundary="b", subsystem="sub", attack_class="atk")
        self.mgr.validate()  # valid initial state

        # String wave
        u1.wave = "wave_one"  # type: ignore
        errors = self.mgr.validate()
        self.assertTrue(any("Wave must be an integer >= 1" in e for e in errors))

        # Wave < 1
        u1.wave = 0
        errors = self.mgr.validate()
        self.assertTrue(any("Wave must be an integer >= 1" in e for e in errors))

        # Boolean wave
        u1.wave = True  # type: ignore
        errors = self.mgr.validate()
        self.assertTrue(any("Wave must be an integer >= 1" in e for e in errors))

    def test_summary_safe_wave_formatting(self):
        """CLI summary must safely format string or mixed wave values without format code crashes."""
        p = Path(self.temp_dir.name) / "str_wave.json"
        p.write_text(
            json.dumps([
                {"coverage_id": "s::b::sub::atk", "surface": "s", "boundary": "b", "subsystem": "sub", "attack_class": "atk", "wave": "Phase 1"},
                {"coverage_id": "s::b::sub::xss", "surface": "s", "boundary": "b", "subsystem": "sub", "attack_class": "xss", "wave": 2},
            ]),
            encoding="utf-8",
        )
        script_path = Path(__file__).parent.parent / "tools" / "security_coverage_ledger.py"
        res = subprocess.run(
            [sys.executable, str(script_path), "summary", str(p)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Wave Phase 1", res.stdout)
        self.assertIn("Wave 2", res.stdout)

    def test_add_unit_updates_existing_unit(self):
        """Calling add_unit on an existing canonical ID should update non-default fields."""
        u = self.mgr.add_unit(
            surface="s1", boundary="b1", subsystem="sub1", attack_class="idor",
            status="planned", wave=1
        )
        self.assertEqual(u.status, "planned")
        self.assertIsNone(u.agent_id)

        # Update with new values
        updated = self.mgr.add_unit(
            surface="s1", boundary="b1", subsystem="sub1", attack_class="idor",
            status="covered", wave=2, agent_id="agent-01", reviewed_paths=["path1.ts"]
        )
        self.assertEqual(updated.status, "covered")
        self.assertEqual(updated.wave, 2)
        self.assertEqual(updated.agent_id, "agent-01")
        self.assertEqual(updated.reviewed_paths, ["path1.ts"])


if __name__ == "__main__":
    unittest.main()
