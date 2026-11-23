#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_dod_receipt.py — Unit Tests for DoD Verification Receipt Engine.
"""

import json
import os
import tempfile
import time
from unittest.mock import patch

from tools.core.dod_receipt import (
    RECEIPT_REL_PATH,
    compute_receipt_signature,
    create_receipt,
    invalidate_receipt,
    verify_receipt,
)


class TestDoDReceiptEngine:
    """Validates the cryptographic DoD Verification Receipt lifecycle."""

    def test_signature_deterministic_and_unique(self):
        sig1 = compute_receipt_signature("abc1234", 2045, 11, "HUB")
        sig2 = compute_receipt_signature("abc1234", 2045, 11, "HUB")
        sig3 = compute_receipt_signature("abc1234", 2046, 11, "HUB")
        assert sig1 == sig2
        assert sig1 != sig3

    def test_create_and_verify_valid_receipt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            commit_sha = "1234567890abcdef1234567890abcdef12345678"
            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=True):
                path = create_receipt(tmpdir, commit_sha, tests_passed=2045, gates_passed=11, mode="HUB")
                assert path is not None
                assert os.path.exists(path)

                with patch("tools.core.dod_receipt.get_current_commit_sha", return_value=commit_sha):
                    valid, data, reason = verify_receipt(tmpdir, max_age_seconds=600)
                    assert valid is True
                    assert data is not None
                    assert data["git_commit"] == commit_sha
                    assert data["tests_passed"] == 2045
                    assert data["gates_passed"] == 11
                    assert "Valid" in reason

    def test_verify_rejects_dirty_working_tree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            commit_sha = "1234567890abcdef1234567890abcdef12345678"
            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=True):
                create_receipt(tmpdir, commit_sha, tests_passed=2045, gates_passed=11, mode="HUB")

            # When verifying, working tree is dirty
            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=False):
                with patch("tools.core.dod_receipt.get_current_commit_sha", return_value=commit_sha):
                    valid, data, reason = verify_receipt(tmpdir, max_age_seconds=600, require_clean=True)
                    assert valid is False
                    assert "dirty" in reason.lower() or "unstaged" in reason.lower()

    def test_verify_rejects_commit_sha_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            commit_sha = "1234567890abcdef1234567890abcdef12345678"
            other_sha = "9999999990abcdef1234567890abcdef12345678"
            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=True):
                create_receipt(tmpdir, commit_sha, tests_passed=2045, gates_passed=11, mode="HUB")

            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=True):
                with patch("tools.core.dod_receipt.get_current_commit_sha", return_value=other_sha):
                    valid, data, reason = verify_receipt(tmpdir, max_age_seconds=600)
                    assert valid is False
                    assert "mismatch" in reason.lower()

    def test_verify_rejects_tampered_signature(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            commit_sha = "1234567890abcdef1234567890abcdef12345678"
            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=True):
                path = create_receipt(tmpdir, commit_sha, tests_passed=2045, gates_passed=11, mode="HUB")

            # Tamper the file
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            doc["tests_passed"] = 9999
            with open(path, "w", encoding="utf-8") as f:
                json.dump(doc, f)

            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=True):
                with patch("tools.core.dod_receipt.get_current_commit_sha", return_value=commit_sha):
                    valid, data, reason = verify_receipt(tmpdir, max_age_seconds=600)
                    assert valid is False
                    assert "tampered" in reason.lower() or "signature" in reason.lower()

    def test_verify_rejects_expired_receipt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            commit_sha = "1234567890abcdef1234567890abcdef12345678"
            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=True):
                path = create_receipt(tmpdir, commit_sha, tests_passed=2045, gates_passed=11, mode="HUB")

            # Set epoch to past
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            doc["timestamp_epoch"] = time.time() - 10000
            # Recalculate signature to keep it authentic
            doc["signature"] = compute_receipt_signature(commit_sha, doc["tests_passed"], doc["gates_passed"], doc["mode"])
            with open(path, "w", encoding="utf-8") as f:
                json.dump(doc, f)

            with patch("tools.core.dod_receipt.is_git_working_tree_clean", return_value=True):
                with patch("tools.core.dod_receipt.get_current_commit_sha", return_value=commit_sha):
                    valid, data, reason = verify_receipt(tmpdir, max_age_seconds=60)
                    assert valid is False
                    assert "expired" in reason.lower()

    def test_invalidate_receipt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = os.path.join(tmpdir, RECEIPT_REL_PATH)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write("{}")

            assert os.path.exists(target_path)
            res = invalidate_receipt(tmpdir)
            assert res is True
            assert not os.path.exists(target_path)
