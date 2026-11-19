#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit tests for Autonomous Production Journey Harvester
------------------------------------------------------
Verifies:
  - Telemetry event ingestion & session clustering
  - Frequency ranking of user paths
  - Clean POM code generation with dynamic smart waits and AST validity
"""

import ast
from tools.core.journey_harvester import JourneyHarvester


def test_journey_ingestion_and_clustering():
    """Verifies that user session paths are clustered and sorted by popularity."""
    harvester = JourneyHarvester()

    # Session 1: Login flow
    harvester.ingest_events([
        {"session_id": "s1", "action": "navigate", "target": "https://app.com/login"},
        {"session_id": "s1", "action": "fill", "target": "username_input", "value": "alice"},
        {"session_id": "s1", "action": "click", "target": "submit_button"},
    ])

    # Session 2: Identical login flow
    harvester.ingest_events([
        {"session_id": "s2", "action": "navigate", "target": "https://app.com/login"},
        {"session_id": "s2", "action": "fill", "target": "username_input", "value": "bob"},
        {"session_id": "s2", "action": "click", "target": "submit_button"},
    ])

    # Session 3: Direct search flow
    harvester.ingest_events([
        {"session_id": "s3", "action": "navigate", "target": "https://app.com/search"},
        {"session_id": "s3", "action": "click", "target": "search_button"},
    ])

    # Cluster journeys with min_frequency=2
    popular = harvester.cluster_journeys(min_frequency=2)
    assert len(popular) == 1
    assert popular[0].frequency == 2
    assert "login" in popular[0].signature

    # All journeys
    all_journeys = harvester.cluster_journeys(min_frequency=1)
    assert len(all_journeys) == 2
    assert all_journeys[0].frequency == 2
    assert all_journeys[1].frequency == 1


def test_clean_pom_synthesis_and_ast_validation():
    """Verifies that generated Clean POM code complies with AST and Clean POM invariants."""
    harvester = JourneyHarvester()
    harvester.ingest_events([
        {"session_id": "sess_order", "action": "navigate", "target": "https://store.com/checkout"},
        {"session_id": "sess_order", "action": "fill", "target": "card_number", "value": "4242"},
        {"session_id": "sess_order", "action": "click", "target": "pay_button"},
    ])

    journeys = harvester.cluster_journeys(min_frequency=1)
    assert len(journeys) == 1

    code = harvester.synthesize_clean_pom_suite(journeys[0], suite_name="CheckoutOrder")

    # Invariant 1: Valid Python AST
    parsed_ast = ast.parse(code)
    assert parsed_ast is not None

    # Invariant 2: Encapsulated Clean POM Page Class
    assert "class CheckoutOrderPage:" in code
    assert "def execute_journey_workflow(self):" in code
    assert "test_checkoutorder_flow" in code

    # Invariant 3: Dynamic smart wait (web-first expect visibility)
    assert "expect(self.card_number).to_be_visible()" in code
    assert "expect(self.pay_button).to_be_visible()" in code

    # Invariant 4: No static sleeps
    assert "sleep(" not in code
    assert "time." not in code


def test_smart_form_test_data_inference():
    """Verifies that JourneyHarvester infers realistic test data for regex-validated fields."""
    harvester = JourneyHarvester()
    harvester.ingest_events([
        {"session_id": "reg1", "action": "navigate", "target": "https://site.com/register"},
        {"session_id": "reg1", "action": "fill", "target": "user_email"},
        {"session_id": "reg1", "action": "fill", "target": "phone_number"},
        {"session_id": "reg1", "action": "fill", "target": "password_input"},
        {"session_id": "reg1", "action": "fill", "target": "dob_date"},
        {"session_id": "reg1", "action": "fill", "target": "credit_card"},
        {"session_id": "reg1", "action": "click", "target": "submit_btn"},
    ])

    journeys = harvester.cluster_journeys(min_frequency=1)
    code = harvester.synthesize_clean_pom_suite(journeys[0], suite_name="RegistrationForm")

    assert 'self.user_email.fill("user.test@example.com")' in code
    assert 'self.phone_number.fill("0912345678")' in code
    assert 'self.password_input.fill("P@ssw0rd!2026")' in code
    assert 'self.dob_date.fill("2026-01-15")' in code
    assert 'self.credit_card.fill("4242424242424242")' in code
    assert ast.parse(code) is not None
