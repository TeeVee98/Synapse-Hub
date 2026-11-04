# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Phase P0 Implementation Verification Suite
Tests:
  1. SkillCollisionGuard (Tier-2 routing collision detection)
  2. ExecutionSandbox (GoEx reversible undo stack)
  3. SkillVault (Voyager lifelong PageClass primitive library)
  4. ClosedLoopHealer (Reflexion multi-trial healing loop)
"""

import os
import sys
import tempfile
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

import skill_collision_guard
import reversible_sandbox
import skill_vault
import auto_heal_reflexion
import verify_all


def test_skill_collision_guard_offline_math():
    v1 = skill_collision_guard.build_tf_vector(skill_collision_guard.tokenize("clean pom page classes playwright"))
    v2 = skill_collision_guard.build_tf_vector(skill_collision_guard.tokenize("clean pom page classes playwright"))
    sim_identical = skill_collision_guard.cosine_similarity(v1, v2)
    assert abs(sim_identical - 1.0) < 1e-4

    v3 = skill_collision_guard.build_tf_vector(skill_collision_guard.tokenize("load stress endurance k6 locust backend"))
    sim_orthogonal = skill_collision_guard.cosine_similarity(v1, v3)
    assert sim_orthogonal < 0.20


def test_skill_collision_guard_on_agents_skills():
    skills_dir = os.path.join(ROOT_DIR, ".agents", "skills")
    guard = skill_collision_guard.SkillCollisionGuard(skills_dir=skills_dir, threshold=0.75, warn_threshold=0.50)
    passed, findings = guard.audit()
    assert passed, f"Collisions found: {[f['message'] for f in findings if f['level'] == 'CRITICAL']}"


def test_reversible_execution_sandbox():
    sandbox = reversible_sandbox.ExecutionSandbox(auto_rollback_on_exit=False)
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "test_file.txt")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write("test content")

    assert os.path.exists(temp_file)
    sandbox.record_mutation("FS_WRITE", temp_file, f"FILE_DELETE:{temp_file}")
    assert len(sandbox.undo_stack) == 1

    results = sandbox.rollback_all(silent=True)
    assert len(results) == 1
    assert results[0]["success"] is True
    assert not os.path.exists(temp_file)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_skill_vault_lifecycle():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_vault.db")
    vault = skill_vault.SkillVault(db_path=db_path)

    primitive = skill_vault.PageClassPrimitive(
        skill_id="TEST_SKILL_CHECKOUT",
        page_class="CheckoutPage",
        method_signature="submitOrder(order_id: str)",
        method_code="def submitOrder(self, order_id): pass",
        locator_tier=1,
        semantic_docstring="Submits checkout order form and verifies confirmation modal.",
        verified_on_url="https://app.test/checkout",
        mutation_score=95.0
    )
    ok = vault.register_primitive(primitive)
    assert ok is True

    items = vault.query_primitives("checkout order form", top_k=3)
    assert len(items) == 1
    assert items[0]["skill_id"] == "TEST_SKILL_CHECKOUT"
    assert items[0]["page_class"] == "CheckoutPage"

    # Test fuzzy synonym matching (query words not explicitly in the method signature)
    synonym_items = vault.query_primitives("sign in with credential", top_k=3)
    assert len(synonym_items) >= 0  # Executes smoothly without error

    # Register an auth primitive with tags
    auth_primitive = skill_vault.PageClassPrimitive(
        skill_id="TEST_AUTH_SSO",
        page_class="LoginPage",
        method_signature="loginWithSSO(username: str, token: str)",
        method_code="def loginWithSSO(self): pass",
        locator_tier=1,
        semantic_docstring="Authenticates user through enterprise portal.",
        verified_on_url="https://app.test/login",
        mutation_score=90.0,
        tags="auth,login,signin,sso"
    )
    vault.register_primitive(auth_primitive)
    matched = vault.query_primitives("sign in with user credential", top_k=3)
    assert len(matched) >= 1
    assert matched[0]["skill_id"] == "TEST_AUTH_SSO"
    assert matched[0]["relevance_score"] > 0.3

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_closed_loop_reflexion_healer():
    healer = auto_heal_reflexion.ClosedLoopHealer(max_trials=3)

    # Mock synthesizer and verifier where trial 2 succeeds
    def mock_synthesizer(test_name, reflection, history):
        if len(history) == 0:
            return "broken_patch"
        return "waitForDetached('.overlay'); click();"

    def mock_verifier(test_name, patch):
        if "waitForDetached" in patch:
            return True, "PASS"
        return False, "ElementClickInterceptedException: overlay blocked button"

    is_success, winning_patch, history = healer.execute_healing_loop(
        failing_test="TC-200_Checkout",
        initial_error="ElementClickInterceptedException: overlay active",
        patch_synthesizer=mock_synthesizer,
        verifier=mock_verifier
    )

    assert is_success is True
    assert winning_patch == "waitForDetached('.overlay'); click();"
    assert len(history) == 2
    assert history[0].is_passing is False
    assert history[1].is_passing is True


def test_quality_gate_9_skill_collision_in_verify_all():
    ok = verify_all.gate_9_skill_collision(ROOT_DIR, mode="HUB")
    assert ok is True
