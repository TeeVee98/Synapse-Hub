# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/auto_heal_reflexion.py (AOM Semantic Reflexion Self-Healer)."""

import os
import sys
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from auto_heal_reflexion import (
    ClosedLoopHealer,
    prune_aom_tree,
    analyze_aom_semantic_discrepancy,
    generate_semantic_reflexion
)


def test_prune_aom_tree_token_budget():
    """Verifies that large AOM trees are pruned to under 500 tokens (< 1800 characters)."""
    large_tree = {
        "role": "application",
        "children": [
            {
                "role": "dialog",
                "name": f"Modal {i}",
                "children": [
                    {"role": "button", "name": f"Button {j}", "disabled": False}
                    for j in range(20)
                ]
            }
            for i in range(10)
        ]
    }
    pruned = prune_aom_tree(large_tree)
    pruned_str = json.dumps(pruned)
    assert len(pruned_str) <= 1800


def test_analyze_aom_semantic_discrepancy_resolved_node():
    """Verifies that matching node in AOM generates Clean POM getByRole locator."""
    aom = {
        "aom_nodes": [
            {"role": "button", "name": "Login", "testId": "btn-login", "disabled": False}
        ]
    }
    diagnosis = analyze_aom_semantic_discrepancy("#btn-login", aom)
    assert diagnosis["discrepancy_cause"] == "ACCESSIBLE_NAME_OR_ROLE_RESOLVED"
    assert "page.getByRole('button', { name: 'Login' })" in diagnosis["candidate_locators"]
    assert "page.getByTestId('btn-login')" in diagnosis["candidate_locators"]


def test_analyze_aom_semantic_discrepancy_disabled_node():
    """Verifies that disabled node in AOM is correctly diagnosed."""
    aom = {
        "aom_nodes": [
            {"role": "button", "name": "Submit", "disabled": True}
        ]
    }
    diagnosis = analyze_aom_semantic_discrepancy("button.submit-btn", aom)
    assert diagnosis["discrepancy_cause"] == "TARGET_ELEMENT_DISABLED"
    assert "disabled" in diagnosis["detail"]


def test_generate_semantic_reflexion_prompt_structure():
    """Verifies that LLM semantic reasoning prompt is generated with AOM context."""
    aom = [{"role": "textbox", "name": "Username", "disabled": False}]
    res = generate_semantic_reflexion(
        error_sig="TimeoutError: locator.fill() timed out",
        failing_selector="input#user_name",
        aom_tree=aom
    )
    assert "verbal_reflection" in res
    assert "recommended_patch" in res
    assert "prompt" in res
    prompt = res["prompt"]
    assert "Compact Accessibility Object Model (AOM) Subtree" in prompt
    assert "Username" in prompt
    assert "input#user_name" in prompt


def test_closed_loop_healer_backward_compatibility():
    """Verifies that existing error signatures without AOM work seamlessly."""
    healer = ClosedLoopHealer(max_trials=3)
    ref = healer.generate_reflection("ElementClickInterceptedException", "", "")
    assert "Click intercepted by fading overlay" in ref

    ref_auth = healer.generate_reflection("401 Unauthorized token expired", "", "")
    assert "Session auth token or cookie expired" in ref_auth


def test_closed_loop_healer_execute_loop_success():
    """Verifies successful healing loop execution within max trials."""
    healer = ClosedLoopHealer(max_trials=3)

    def mock_synth(test_name, reflection, history):
        if len(history) == 0:
            return "page.click('#btn')"
        return "page.getByRole('button', { name: 'Submit' }).click()"

    def mock_verifier(test_name, patch):
        if "getByRole" in patch:
            return True, ""
        return False, "ElementClickInterceptedException"

    aom = [{"role": "button", "name": "Submit", "disabled": False}]
    success, winning_patch, history = healer.execute_healing_loop(
        failing_test="SubmitTest",
        initial_error="ElementClickInterceptedException",
        patch_synthesizer=mock_synth,
        verifier=mock_verifier,
        aom_tree=aom,
        failing_selector="#btn"
    )

    assert success is True
    assert "getByRole" in winning_patch
    assert len(history) == 2
    assert history[0].is_passing is False
    assert history[1].is_passing is True


def test_prune_aom_tree_preserves_children_on_large_dict():
    """Verifies that large root dictionary snapshot retains children rather than returning empty nodes."""
    large_tree = {
        "role": "WebArea",
        "name": "Dashboard",
        "children": [
            {"role": "button", "name": f"Btn_{i}", "testId": f"id_{i}"}
            for i in range(80)
        ]
    }
    pruned = prune_aom_tree(large_tree, max_chars=500)
    assert len(json.dumps(pruned)) <= 1800
    assert "children" in pruned
    assert len(pruned["children"]) >= 1


def test_analyze_aom_semantic_discrepancy_avoids_generic_tag_collision():
    """Verifies that selector 'button.submit' matches 'Submit' rather than earlier 'Cancel' button."""
    aom = {
        "aom_nodes": [
            {"role": "button", "name": "Cancel", "testId": "btn-cancel"},
            {"role": "button", "name": "Submit", "testId": "btn-submit"}
        ]
    }
    res = analyze_aom_semantic_discrepancy("button.submit", aom)
    assert res["target_node"] is not None
    assert res["target_node"]["name"] == "Submit"
    assert "Submit" in res["recommended_patch"]

