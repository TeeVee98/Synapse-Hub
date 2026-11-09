#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_skill_vault.py — Unit Tests for SkillVault Lifelong Page Object Library
"""

import os
import sys
import unittest
import tempfile
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import skill_vault
from skill_vault import SkillVault, PageClassPrimitive, split_identifier, _expand_tokens_with_synonyms


class TestSkillVault(unittest.TestCase):
    """Tests SkillVault SQLite store, token parsing, and fuzzy semantic retrieval."""

    def test_split_identifier(self):
        self.assertEqual(split_identifier("loginWithSSO"), ["login", "with", "sso"])
        self.assertEqual(split_identifier("submit_order_form"), ["submit", "order", "form"])
        self.assertEqual(split_identifier("DataTablePagination"), ["data", "table", "pagination"])

    def test_synonym_expansion(self):
        expanded = _expand_tokens_with_synonyms(["login"])
        self.assertIn("auth", expanded)
        self.assertIn("signin", expanded)
        self.assertIn("credential", expanded)

    def test_vault_crud_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_vault.db")
            vault = SkillVault(db_path=db_path)

            primitive = PageClassPrimitive(
                skill_id="SKILL_AUTH_SSO",
                page_class="LoginPage",
                method_signature="loginWithSSO(username: str, token: str)",
                method_code="def loginWithSSO(username, token):\n    self.fill('#sso-user', username)\n",
                locator_tier=1,
                semantic_docstring="Authenticates user using corporate SSO token into admin dashboard",
                verified_on_url="https://aut.internal/login",
                mutation_score=92.5,
                tags="auth,sso,login"
            )

            # 1. Register primitive
            success = vault.register_primitive(primitive)
            self.assertTrue(success)

            # 2. Query with exact keyword
            results = vault.query_primitives("loginWithSSO", top_k=3)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["skill_id"], "SKILL_AUTH_SSO")

            # 3. Query with domain synonym ('credential')
            syn_results = vault.query_primitives("corporate credential signin", top_k=3)
            self.assertEqual(len(syn_results), 1)
            self.assertEqual(syn_results[0]["skill_id"], "SKILL_AUTH_SSO")

            # 4. Get primitive by ID
            fetched = vault.get_primitive("SKILL_AUTH_SSO")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["page_class"], "LoginPage")
            self.assertEqual(fetched["mutation_score"], 92.5)

            # 5. Export JSON
            vault_json = vault.export_vault_json()
            data = json.loads(vault_json)
            self.assertEqual(data["count"], 1)

            # 6. Delete primitive
            del_success = vault.delete_primitive("SKILL_AUTH_SSO")
            self.assertTrue(del_success)
            self.assertIsNone(vault.get_primitive("SKILL_AUTH_SSO"))


if __name__ == "__main__":
    unittest.main()
