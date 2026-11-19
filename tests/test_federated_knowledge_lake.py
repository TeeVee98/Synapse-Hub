#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit tests for Federated Enterprise QA Knowledge Lake
-----------------------------------------------------
Verifies:
  - Multi-project knowledge publishing and querying
  - Cross-project consensus voting and conflict resolution
"""

from tools.core.federated_knowledge_lake import FederatedKnowledgeLake


def test_federated_publish_and_query():
    """Verifies that records from multiple projects can be published and queried."""
    with FederatedKnowledgeLake(db_path=":memory:") as lake:
        lake.publish(
            project_id="proj_auth",
            domain="locator_heal",
            key="login_submit_btn",
            action="getByRole('button', name='Sign in')",
            confidence=0.8,
            occurrences=3
        )
        lake.publish(
            project_id="proj_billing",
            domain="locator_heal",
            key="checkout_pay_btn",
            action="getByRole('button', name='Pay Now')",
            confidence=0.9,
            occurrences=5
        )

        all_records = lake.query(domain="locator_heal")
        assert len(all_records) == 2

        filtered = lake.query(domain="locator_heal", search_text="checkout")
        assert len(filtered) == 1
        assert filtered[0]["project_id"] == "proj_billing"


def test_federated_consensus_resolution():
    """
    Verifies that when multiple projects propose different healing actions,
    the consensus engine chooses the action with the highest weighted score.
    """
    with FederatedKnowledgeLake(db_path=":memory:") as lake:
        # Project 1: proposes getByRole with high confidence & occurrences
        lake.publish(
            project_id="proj_a",
            domain="locator_heal",
            key="search_input",
            action={"locator": "getByRole('searchbox')"},
            confidence=0.9,
            occurrences=10  # Score = 9.0
        )

        # Project 2: proposes fragile xpath with low occurrences
        lake.publish(
            project_id="proj_b",
            domain="locator_heal",
            key="search_input",
            action={"locator": "//input[@id='search']"},
            confidence=0.5,
            occurrences=2  # Score = 1.0
        )

        consensus = lake.resolve_consensus(domain="locator_heal", key="search_input")
        assert consensus is not None
        assert consensus["consensus_action"] == {"locator": "getByRole('searchbox')"}
        assert consensus["competing_actions"] == 2
        assert consensus["consensus_ratio"] >= 0.85
