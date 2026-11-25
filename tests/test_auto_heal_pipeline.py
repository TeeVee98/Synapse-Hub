#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_auto_heal_pipeline.py — Unit tests for Closed-Loop Auto-Healing Pipeline
----------------------------------------------------------------------------------
Verifies that heal_and_record_instinct:
  1. Validates proposed fix via Fact-Forcing Gate.
  2. Records and reinforces healed locators in QAInstinctVault.
  3. Triggers promotion upon repeated verified success.
"""

import logging
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from tools.core import project_state
from tools.core.federated_knowledge_lake import FederatedKnowledgeLake
from tools.core.qa_memory_os import QAMemoryOS
from tools.heal.ci_healing_hook import CIHealingHook
from tools.orchestration.auto_heal_pipeline import (
    heal_and_record_instinct,
    verify_fail_to_pass_sandbox,
)
from tools.orchestration.qa_instinct_vault import QAInstinctVault


class TestAutoHealPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_pipeline.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_heal_and_record_instinct(self):
        res1 = heal_and_record_instinct(
            project_dir="/workspace/sample_app",
            target_page_path="pages/login_page.py",
            broken_locator="button#submit",
            healed_locator="button[type='submit']",
            vault_db_path=self.db_path,
        )
        self.assertEqual(res1["status"], "HEALED_AND_LEARNED")
        self.assertEqual(res1["occurrences"], 1)

        # Second heal of the same locator triggers confidence reinforcement and promotion
        res2 = heal_and_record_instinct(
            project_dir="/workspace/sample_app",
            target_page_path="pages/login_page.py",
            broken_locator="button#submit",
            healed_locator="button[type='submit']",
            vault_db_path=self.db_path,
        )
        self.assertEqual(res2["status"], "HEALED_AND_LEARNED")
        self.assertEqual(res2["occurrences"], 2)
        self.assertGreater(res2["promoted_count"], 0)

    def test_verify_fail_to_pass_sandbox_success(self):
        def runner(code):
            return "healed" in code

        res = verify_fail_to_pass_sandbox(
            test_runner=runner,
            broken_snippet="btn = page.locator('#broken')",
            healed_snippet="btn = page.locator('#healed')"
        )
        self.assertEqual(res["status"], "FAIL_TO_PASS_VERIFIED")
        self.assertTrue(res["defect_reproduced"])
        self.assertTrue(res["repair_verified"])

    def test_verify_fail_to_pass_sandbox_rejects_tautology(self):
        # Runner always passes (tautology / defect not reproduced)
        def runner(_):
            return True

        res = verify_fail_to_pass_sandbox(
            test_runner=runner,
            broken_snippet="btn = page.locator('#broken')",
            healed_snippet="btn = page.locator('#healed')"
        )
        self.assertEqual(res["status"], "REJECTED_NO_FAILURE_REPRODUCED")


# ---------------------------------------------------------------------------
# Milestone 4: CIHealingHook -> auto_heal_pipeline + QAMemoryOS + Lake Wiring
# ---------------------------------------------------------------------------

def test_ci_healing_hook_positive_persists_all_stores_and_closes_connections(tmp_path):
    """Positive: Valid locator heal persists instinct, Tier-2 recall, Tier-3 archival, and federated lake."""
    project_dir = tmp_path / "sample_project"
    project_dir.mkdir()
    page_file = project_dir / "login_page.py"
    page_file.write_text("submit_btn = page.locator('#old_submit_btn')\n", encoding="utf-8")

    db_dir = tmp_path / "dbs"
    db_dir.mkdir()
    vault_db = str(db_dir / "qa_instincts.db")
    memory_db = str(db_dir / "qa_memory.db")
    lake_db = str(db_dir / "federated_qa_lake.db")

    mem_closes = []
    lake_closes = []
    orig_mem_close = QAMemoryOS.close
    orig_lake_close = FederatedKnowledgeLake.close

    def tracked_mem_close(self):
        mem_closes.append(self.db_path)
        return orig_mem_close(self)

    def tracked_lake_close(self):
        lake_closes.append(self.db_path)
        return orig_lake_close(self)

    with patch.object(QAMemoryOS, "close", tracked_mem_close), patch.object(
        FederatedKnowledgeLake, "close", tracked_lake_close
    ):
        result = CIHealingHook.evaluate_and_heal(
            file_path=str(page_file),
            failed_locator="#old_submit_btn",
            healed_locator="getByRole('button', name='Submit')",
            test_id="TC_HEAL_M4_01",
            confidence=0.92,
            project_dir=str(project_dir),
            vault_db_path=vault_db,
        )

    assert result["applied"] is True
    assert "getByRole('button', name='Submit')" in page_file.read_text(encoding="utf-8")
    assert "#old_submit_btn" not in page_file.read_text(encoding="utf-8")

    # Verify structured persistence metadata
    assert result["instinct_status"] == "HEALED_AND_LEARNED"
    assert isinstance(result["instinct_result"], dict)
    assert result["instinct_result"]["occurrences"] == 1
    assert isinstance(result["memory_os_event_id"], str)
    assert result["memory_os_event_id"].startswith("evt_")
    assert isinstance(result["memory_os_archival_id"], str)
    assert result["memory_os_archival_id"].startswith("arc_")
    assert isinstance(result["federated_record_id"], str)
    assert len(result["federated_record_id"]) > 0
    assert result["memory_sync_errors"] == []

    # Verify explicit SQLite close() calls
    assert len(mem_closes) == 1
    assert len(lake_closes) == 1

    # Verify QAInstinctVault persistence
    with QAInstinctVault(vault_db) as vault:
        instincts = vault.query_instincts(str(project_dir), domain="locator_heal")
    assert len(instincts) == 1
    assert instincts[0]["broken_locator"] == "#old_submit_btn"
    assert instincts[0]["healed_locator"] == "getByRole('button', name='Submit')"

    # Verify QAMemoryOS Tier-2 recall and Tier-3 archival persistence
    mem = QAMemoryOS(db_path=memory_db)
    try:
        recalls = mem.query_recall(event_type="locator_heal", limit=10)
        assert len(recalls) == 1
        assert recalls[0]["event_id"] == result["memory_os_event_id"]
        assert recalls[0]["details"]["old_locator"] == "#old_submit_btn"
        assert recalls[0]["details"]["new_locator"] == "getByRole('button', name='Submit')"
        assert recalls[0]["details"]["test_id"] == "TC_HEAL_M4_01"

        archivals = mem.query_archival("old_submit_btn", domain="locator_heal")
        assert len(archivals) == 1
        assert archivals[0]["id"] == result["memory_os_archival_id"]
        assert archivals[0]["action"]["healed_locator"] == "getByRole('button', name='Submit')"
        assert archivals[0]["confidence"] == 0.92
    finally:
        mem.close()

    # Verify FederatedKnowledgeLake persistence
    lake = FederatedKnowledgeLake(db_path=lake_db)
    try:
        records = lake.query(domain="locator_heal", search_text="old_submit_btn")
        assert len(records) == 1
        assert records[0]["id"] == result["federated_record_id"]
        assert records[0]["project_id"] == "sample_project"
        assert records[0]["key"] == "#old_submit_btn"
        assert records[0]["action"] == "getByRole('button', name='Submit')"
        assert records[0]["confidence"] == 0.92
    finally:
        lake.close()


def test_ci_healing_hook_backward_compatible_defaults_scoped_to_file_dir(tmp_path):
    """Positive: Calling evaluate_and_heal without project_dir/vault_db_path works and isolates DBs."""
    page_file = tmp_path / "checkout_page.ts"
    page_file.write_text("const pay = page.locator('.legacy-pay');\n", encoding="utf-8")

    result = CIHealingHook.evaluate_and_heal(
        file_path=str(page_file),
        failed_locator=".legacy-pay",
        healed_locator="[data-testid='pay-now']",
        test_id="TC_COMPAT_01",
        confidence=0.88,
    )

    assert result["applied"] is True
    assert result["instinct_status"] == "HEALED_AND_LEARNED"
    assert result["memory_sync_errors"] == []
    assert (tmp_path / ".agent_memory" / "qa_instincts.db").is_file()
    assert (tmp_path / ".agent_memory" / "qa_memory.db").is_file()
    assert (tmp_path / ".agent_memory" / "federated_qa_lake.db").is_file()


def test_ci_healing_hook_negative_missing_file_and_unmatched_locator(tmp_path):
    """Negative: Missing file or unmatched locator returns applied=False without DB writes or crash."""
    vault_db = str(tmp_path / "should_not_exist.db")
    missing_file = str(tmp_path / "nonexistent_page.py")

    res_missing = CIHealingHook.evaluate_and_heal(
        file_path=missing_file,
        failed_locator="#ghost",
        healed_locator="#real",
        vault_db_path=vault_db,
    )
    assert res_missing["applied"] is False
    assert res_missing["instinct_status"] == "SKIPPED"
    assert res_missing["instinct_result"] is None
    assert res_missing["memory_os_event_id"] is None
    assert res_missing["memory_os_archival_id"] is None
    assert res_missing["federated_record_id"] is None
    assert res_missing["memory_sync_errors"] == []
    assert not os.path.exists(vault_db)

    existing_file = tmp_path / "other_page.py"
    existing_file.write_text("btn = page.locator('#different')\n", encoding="utf-8")
    res_unmatched = CIHealingHook.evaluate_and_heal(
        file_path=str(existing_file),
        failed_locator="#not_found",
        healed_locator="#replacement",
        vault_db_path=vault_db,
    )
    assert res_unmatched["applied"] is False
    assert res_unmatched["instinct_status"] == "SKIPPED"
    assert existing_file.read_text(encoding="utf-8") == "btn = page.locator('#different')\n"
    assert not os.path.exists(vault_db)


def test_ci_healing_hook_negative_readonly_db_degrades_gracefully(tmp_path):
    """Negative: Read-only DB directory / sqlite errors do not crash healing and report sync errors."""
    page_file = tmp_path / "profile_page.py"
    page_file.write_text("btn = page.locator('#old_profile')\n", encoding="utf-8")

    ro_dir = tmp_path / "readonly_db_dir"
    ro_dir.mkdir()
    ro_vault_db = str(ro_dir / "vault.db")
    os.chmod(ro_dir, 0o555)
    try:
        if os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0):
            with patch("sqlite3.connect", side_effect=sqlite3.OperationalError("attempt to write a readonly database")):
                result = CIHealingHook.evaluate_and_heal(
                    file_path=str(page_file),
                    failed_locator="#old_profile",
                    healed_locator="#new_profile",
                    project_dir=str(tmp_path),
                    vault_db_path=ro_vault_db,
                )
        else:
            result = CIHealingHook.evaluate_and_heal(
                file_path=str(page_file),
                failed_locator="#old_profile",
                healed_locator="#new_profile",
                project_dir=str(tmp_path),
                vault_db_path=ro_vault_db,
            )
    finally:
        os.chmod(ro_dir, 0o755)

    assert result["applied"] is True
    assert "#new_profile" in page_file.read_text(encoding="utf-8")
    assert result["instinct_status"] == "ERROR"
    assert result["instinct_result"] is None
    assert result["memory_os_event_id"] is None
    assert result["memory_os_archival_id"] is None
    assert result["federated_record_id"] is None
    assert len(result["memory_sync_errors"]) == 3
    joined_errors = " ".join(result["memory_sync_errors"])
    assert "auto_heal_pipeline" in joined_errors
    assert "qa_memory_os" in joined_errors
    assert "federated_knowledge_lake" in joined_errors


def test_ci_healing_hook_boundary_empty_identical_directory_and_in_memory(tmp_path):
    """Boundary: Empty locator, identical locator, directory path, and :memory: vault DB."""
    page_file = tmp_path / "boundary_page.py"
    original = "btn = page.locator('#keep_me')\n"
    page_file.write_text(original, encoding="utf-8")

    # Empty failed_locator must not corrupt file
    res_empty = CIHealingHook.evaluate_and_heal(
        file_path=str(page_file),
        failed_locator="",
        healed_locator="#x",
        vault_db_path=str(tmp_path / "v.db"),
    )
    assert res_empty["applied"] is False
    assert page_file.read_text(encoding="utf-8") == original

    # Identical locators must be a no-op
    res_same = CIHealingHook.evaluate_and_heal(
        file_path=str(page_file),
        failed_locator="#keep_me",
        healed_locator="#keep_me",
        vault_db_path=str(tmp_path / "v.db"),
    )
    assert res_same["applied"] is False
    assert res_same["instinct_status"] == "SKIPPED"

    # Directory path instead of file must not raise IsADirectoryError
    res_dir = CIHealingHook.evaluate_and_heal(
        file_path=str(tmp_path),
        failed_locator="#a",
        healed_locator="#b",
        vault_db_path=str(tmp_path / "v.db"),
    )
    assert res_dir["applied"] is False

    # In-memory vault_db_path succeeds without writing DB files to disk
    res_mem = CIHealingHook.evaluate_and_heal(
        file_path=str(page_file),
        failed_locator="#keep_me",
        healed_locator="#healed_mem",
        project_dir=str(tmp_path),
        vault_db_path=":memory:",
    )
    assert res_mem["applied"] is True
    assert res_mem["instinct_status"] == "HEALED_AND_LEARNED"
    assert res_mem["memory_os_event_id"].startswith("evt_")
    assert res_mem["federated_record_id"] is not None
    assert res_mem["memory_sync_errors"] == []


# ---------------------------------------------------------------------------
# Milestone 4: project_state.update_state -> QAMemoryOS Core Sync & Tier 4 Cap
# ---------------------------------------------------------------------------

def test_project_state_update_syncs_memory_os_with_secret_scrubbing_and_close(tmp_path):
    """Positive: update_state mirrors core block + watchpoint recall to QAMemoryOS, scrubs secrets, closes DB."""
    mem_closes = []
    orig_close = QAMemoryOS.close

    def tracked_close(self):
        mem_closes.append(self.db_path)
        return orig_close(self)

    with patch.object(QAMemoryOS, "close", tracked_close):
        # Rely on default sync_memory_os=True to verify default behavior
        state_file = project_state.update_state(
            str(tmp_path),
            goal="Verify M4 sync with token=supersecret123456",
            completed_task="Implemented M4 wiring",
            watchpoint="Check auth header Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            gate_status="11/11 PASS",
        )

    assert os.path.isfile(state_file)
    assert len(mem_closes) == 1

    db_path = tmp_path / ".agent_memory" / "qa_memory.db"
    assert db_path.is_file()

    mem = QAMemoryOS(db_path=str(db_path))
    try:
        core = mem.get_core("project_state")
        assert core is not None
        assert core["project"] == tmp_path.name
        assert core["gate_status"] == "11/11 PASS"
        assert "supersecret123456" not in core["active_goal"]
        assert "[REDACTED_SECRET]" in core["active_goal"]
        assert len(core["watchpoints"]) == 1
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in core["watchpoints"][0]
        assert "[REDACTED_SECRET]" in core["watchpoints"][0]
        assert core["tasks_count"] >= 1

        recalls = mem.query_recall(event_type="state_watchpoint", limit=5)
        assert len(recalls) == 1
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in str(recalls[0]["details"])
        assert "[REDACTED_SECRET]" in str(recalls[0]["details"])
    finally:
        mem.close()


def test_project_state_update_opt_out_sync_memory_os_false(tmp_path):
    """Positive: sync_memory_os=False skips QAMemoryOS write while still updating MD and JSON state."""
    project_state.update_state(
        str(tmp_path),
        goal="Offline state update",
        watchpoint="Local only",
        sync_memory_os=False,
    )
    assert (tmp_path / "PROJECT_STATE.md").is_file()
    assert (tmp_path / "project_state.json").is_file()
    assert not (tmp_path / ".agent_memory" / "qa_memory.db").exists()


def test_project_state_update_negative_readonly_memory_dir_non_fatal(tmp_path, caplog):
    """Negative: Read-only .agent_memory dir causes non-fatal fallback; MD/JSON still succeed."""
    # First verify placeholder [None] watchpoints are filtered and _sync_memory_os_state returns True
    clean_dir = tmp_path / "clean_placeholder"
    clean_dir.mkdir()
    ok_sync = project_state._sync_memory_os_state(
        target_dir=str(clean_dir),
        project_name="clean_placeholder",
        timestamp="2026-11-24 00:00:00",
        goal="Placeholder watchpoint check",
        tasks=["- [x] Done"],
        watchpoints=["- Target Suite / Script: `[None]`", "- Failing Locator / Line: `[None]`", "-   "],
        gate_status="READY",
    )
    assert ok_sync is True
    clean_mem = QAMemoryOS(db_path=str(clean_dir / ".agent_memory" / "qa_memory.db"))
    try:
        core_clean = clean_mem.get_core("project_state")
        assert core_clean is not None
        assert core_clean["watchpoints"] == []
        assert clean_mem.query_recall(event_type="state_watchpoint") == []
    finally:
        clean_mem.close()

    # Now verify read-only .agent_memory dir returns False, logs debug message, and does not break update_state
    ro_proj = tmp_path / "ro_proj"
    ro_proj.mkdir()
    mem_dir = ro_proj / ".agent_memory"
    mem_dir.mkdir()
    os.chmod(mem_dir, 0o555)
    try:
        with caplog.at_level(logging.DEBUG, logger="tools.core.project_state"):
            if os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0):
                with patch(
                    "tools.core.qa_memory_os.QAMemoryOS",
                    side_effect=sqlite3.OperationalError("attempt to write a readonly database"),
                ):
                    failed_sync = project_state._sync_memory_os_state(
                        target_dir=str(ro_proj),
                        project_name="ro_proj",
                        timestamp="2026-11-24 00:00:00",
                        goal="RO Direct",
                        tasks=[],
                        watchpoints=[],
                        gate_status="READY",
                    )
                    sf = project_state.update_state(
                        str(ro_proj),
                        goal="Resilient Goal",
                        watchpoint="Readonly probe",
                        sync_memory_os=True,
                    )
            else:
                failed_sync = project_state._sync_memory_os_state(
                    target_dir=str(ro_proj),
                    project_name="ro_proj",
                    timestamp="2026-11-24 00:00:00",
                    goal="RO Direct",
                    tasks=[],
                    watchpoints=[],
                    gate_status="READY",
                )
                sf = project_state.update_state(
                    str(ro_proj),
                    goal="Resilient Goal",
                    watchpoint="Readonly probe",
                    sync_memory_os=True,
                )
    finally:
        os.chmod(mem_dir, 0o755)

    assert failed_sync is False
    assert any("QAMemoryOS state sync skipped" in rec.message for rec in caplog.records)
    assert os.path.isfile(sf)
    state_json = project_state.read_state_json(str(ro_proj))
    assert state_json is not None
    assert state_json["active_goal"] == "Resilient Goal"


def test_project_state_export_stateless_working_block_boundary_under_950_chars(tmp_path):
    """Boundary: export_stateless_working_block stays strictly < 950 chars even with huge goal/watchpoint."""
    # 1. Normal state is not truncated and stays < 950
    project_state.update_state(
        str(tmp_path),
        goal="Short Goal",
        watchpoint="Short Watchpoint",
        sync_memory_os=False,
    )
    normal_block = project_state.export_stateless_working_block(str(tmp_path))
    assert len(normal_block) < 950
    assert not normal_block.endswith("... [CAP]")
    assert "Short Goal" in normal_block

    # 2. Oversized state is deterministically capped strictly < 950 chars
    huge_dir = tmp_path / "huge"
    huge_dir.mkdir()
    project_state.update_state(
        str(huge_dir),
        goal="G" * 700,
        watchpoint="W" * 700,
        sync_memory_os=False,
    )
    capped_block = project_state.export_stateless_working_block(str(huge_dir))
    assert len(capped_block) < 950
    assert capped_block.endswith("... [CAP]")

    # 3. Real repo root working block remains strictly < 950 chars (read-only)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_block = project_state.export_stateless_working_block(repo_root)
    assert len(repo_block) < 950


if __name__ == "__main__":
    unittest.main()
