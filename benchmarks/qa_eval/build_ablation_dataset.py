#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
QA Eval Ablation Benchmark Dataset Generator (Vectors 46 to 100)
---------------------------------------------------------------
Expands the deterministic benchmark corpus from 45 to 100 challenges,
providing realistic production failure scenarios across 11 QA domains.
Fully audited for Safety Firewall compliance and deterministic evaluation.
"""

import os
import sys
import json

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(SCRIPT_DIR, "dataset")

NEW_CHALLENGES = [
    # =========================================================================
    # DOMAIN 1: LOCATOR DRIFT & DOM SHIFTS (46 - 60)
    # =========================================================================
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-46",
            "name": "SVG Icon Action Button Lost Class & Semantic Shift",
            "category": "locator_drift",
            "difficulty": "MEDIUM",
            "description": "Dismiss icon changed from svg.icon-dismiss to an accessible button with aria-label.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "svg.icon-dismiss",
                "error_log": "ElementNotFoundException: Cannot locate 'svg.icon-dismiss'",
                "dom_snapshot": "<button type='button' aria-label='Dismiss Notice' data-testid='dismiss-notice-btn'><svg class='icon-v2-close' focusable='false'/></button>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='dismiss-notice-btn']",
                "fallback_locator": "button[aria-label='Dismiss Notice']",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.8,
                "max_token_cost": 300,
                "min_confidence_score": 0.90
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-47",
            "name": "Virtualized Infinite Scroll Row Index Shift",
            "category": "locator_drift",
            "difficulty": "HARD",
            "description": "Table row was selected by index tr:nth-child(5) which shifts dynamically during scroll.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "table.data-grid tr:nth-child(5) td.name",
                "error_log": "AssertionError: Expected 'Acme Corp' but found 'Beta LLC' at row 5",
                "dom_snapshot": "<div class='virtual-row' data-entity-id='ACME_101' data-testid='row-ACME_101'><span class='col-name'>Acme Corp</span></div>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='row-ACME_101'] .col-name",
                "fallback_locator": ".virtual-row:has-text('Acme Corp')",
                "strategy": "ID_AND_SEMANTIC_INTENT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.2,
                "max_token_cost": 360,
                "min_confidence_score": 0.88
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-48",
            "name": "Material-UI Autocomplete Dropdown Option Text Casing",
            "category": "locator_drift",
            "difficulty": "EASY",
            "description": "Dropdown option text converted to uppercase via CSS text-transform while DOM remains capitalized.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "//li[text()='ACTIVE']",
                "error_log": "TimeoutException: Timed out waiting for //li[text()='ACTIVE']",
                "dom_snapshot": "<ul class='MuiAutocomplete-listbox' role='listbox'><li class='MuiAutocomplete-option' role='option' data-testid='status-active'>Active</li></ul>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='status-active']",
                "fallback_locator": "li[role='option']:has-text('Active')",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.5,
                "max_token_cost": 280,
                "min_confidence_score": 0.95
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-49",
            "name": "React Portal Modal Dynamic ID Detachment",
            "category": "locator_drift",
            "difficulty": "MEDIUM",
            "description": "Modal rendered in React Portal with dynamic ID #modal-1701239.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "#modal-1701239 input#name",
                "error_log": "NoSuchElementException: No element '#modal-1701239' found in container",
                "dom_snapshot": "<div class='ReactModalPortal'><div role='dialog' aria-modal='true' aria-labelledby='modal-title'><input data-testid='customer-name-input' id='customer_name'/></div></div>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='customer-name-input']",
                "fallback_locator": "div[role='dialog'] input#customer_name",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.0,
                "max_token_cost": 320,
                "min_confidence_score": 0.92
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-50",
            "name": "Tailwind CSS v4 Arbitrary Class Refactor",
            "category": "locator_drift",
            "difficulty": "EASY",
            "description": "Brittle locator using Tailwind class .bg-[#1a202c] broke when refactored to theme variable.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "div.bg-\\[\\#1a202c\\] button",
                "error_log": "ElementNotFoundException: Cannot locate 'div.bg-\\[\\#1a202c\\] button'",
                "dom_snapshot": "<div class='bg-surface-primary dark:bg-surface-dark' data-testid='navbar-actions'><button data-testid='nav-login-btn' type='button'>Log In</button></div>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='nav-login-btn']",
                "fallback_locator": "button:has-text('Log In')",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.5,
                "max_token_cost": 290,
                "min_confidence_score": 0.94
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-51",
            "name": "Iframe Payment Element Container Piercing",
            "category": "locator_drift",
            "difficulty": "HARD",
            "description": "Card input mounted inside iframe without frame locator navigation.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "input#card-number",
                "error_log": "NoSuchElementException: 'input#card-number' not found in top-level document",
                "dom_snapshot": "<iframe name='card-frame' title='Secure Card Form'><input data-testid='card-number' id='card-number'/></iframe>"
            },
            "expected_resolution": {
                "healed_locator": "iframe[name='card-frame'] >> internal:control=enter-frame >> [data-testid='card-number']",
                "fallback_locator": "iframe[name='card-frame'] >> input#card-number",
                "strategy": "SHADOW_DOM_PIERCING"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.5,
                "max_token_cost": 380,
                "min_confidence_score": 0.89
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-52",
            "name": "Localized Date-Picker Cell Text Shift",
            "category": "locator_drift",
            "difficulty": "MEDIUM",
            "description": "Calendar day selector failed after switching browser locale from en-US to vi-VN.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "//span[text()='Monday, Nov 22']",
                "error_log": "ElementNotFoundException: Cannot locate XPath '//span[text()='Monday, Nov 22']'",
                "dom_snapshot": "<div class='calendar-grid'><button role='gridcell' data-date='2026-11-22' aria-label='22 tháng 11, 2026' data-testid='date-cell-2026-11-22'>22</button></div>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='date-cell-2026-11-22']",
                "fallback_locator": "button[data-date='2026-11-22']",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.8,
                "max_token_cost": 310,
                "min_confidence_score": 0.93
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-53",
            "name": "Canvas Accessibility Tree Overlay Mapping",
            "category": "locator_drift",
            "difficulty": "HARD",
            "description": "Click on high-chart data point failed because chart was drawn on HTML5 canvas with invisible AOM layer.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "canvas#sales-chart",
                "error_log": "InvalidCoordinatesException: Canvas click at (120, 45) missed interactive segment",
                "dom_snapshot": "<div class='chart-container'><canvas id='sales-chart'/><div class='aom-overlay' role='region' aria-label='Sales Chart'><button role='button' data-testid='chart-point-q4' aria-label='Q4 Sales: $1.2M'>Q4</button></div></div>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='chart-point-q4']",
                "fallback_locator": "button[aria-label*='Q4 Sales']",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.4,
                "max_token_cost": 370,
                "min_confidence_score": 0.88
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-54",
            "name": "Slotted Content Web Component Custom Element",
            "category": "locator_drift",
            "difficulty": "MEDIUM",
            "description": "Button slotted inside custom element <app-card> through <slot name='actions'>.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "app-card .btn-confirm",
                "error_log": "ElementNotFoundException: 'app-card .btn-confirm' not found",
                "dom_snapshot": "<app-card><button slot='actions' class='btn-confirm-action' data-testid='confirm-action-btn'>Confirm</button></app-card>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='confirm-action-btn']",
                "fallback_locator": "button[slot='actions']:has-text('Confirm')",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.7,
                "max_token_cost": 300,
                "min_confidence_score": 0.92
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-55",
            "name": "Ant Design Popconfirm Ok Button Shift",
            "category": "locator_drift",
            "difficulty": "MEDIUM",
            "description": "Ant Design modal ok button class changed from .ant-btn-primary to dynamic token wrapper.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": ".ant-popover .ant-btn-primary",
                "error_log": "TimeoutException: Timed out waiting for '.ant-popover .ant-btn-primary'",
                "dom_snapshot": "<div class='ant-popover-inner'><div class='ant-popover-buttons'><button type='button' class='ant-btn ant-btn-primary ant-btn-color-primary' data-testid='popconfirm-ok-btn'><span>OK</span></button></div></div>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='popconfirm-ok-btn']",
                "fallback_locator": "button:has-text('OK')",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.6,
                "max_token_cost": 310,
                "min_confidence_score": 0.94
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-56",
            "name": "BEM Methodology Modifier Class Transition",
            "category": "locator_drift",
            "difficulty": "EASY",
            "description": "Button class refactored from .c-button--secondary to .c-button--variant-neutral.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "button.c-button--secondary",
                "error_log": "ElementNotFoundException: 'button.c-button--secondary' not found",
                "dom_snapshot": "<button class='c-button c-button--variant-neutral' data-testid='reset-filter-btn' role='button'>Reset Filters</button>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='reset-filter-btn']",
                "fallback_locator": "button:has-text('Reset Filters')",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.4,
                "max_token_cost": 280,
                "min_confidence_score": 0.96
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-57",
            "name": "Web Component Custom Tag Renamed",
            "category": "locator_drift",
            "difficulty": "MEDIUM",
            "description": "Component <user-badge> was renamed to <profile-pill> across the component library.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "user-badge span.email",
                "error_log": "NoSuchElementException: No element 'user-badge' found",
                "dom_snapshot": "<profile-pill data-testid='user-profile-badge'><span class='email' data-testid='user-email-text'>john@example.com</span></profile-pill>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='user-email-text']",
                "fallback_locator": "profile-pill span.email",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.7,
                "max_token_cost": 300,
                "min_confidence_score": 0.93
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-58",
            "name": "Dynamic Timestamp Suffix in ID Removed",
            "category": "locator_drift",
            "difficulty": "EASY",
            "description": "Brittle locator #row-item-1704128913 failed on next test run with new timestamp.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "div#row-item-1704128913",
                "error_log": "ElementNotFoundException: Cannot locate 'div#row-item-1704128913'",
                "dom_snapshot": "<div id='row-item-1704129999' data-testid='cart-row-item' class='cart-item'><span class='title'>Wireless Mouse</span></div>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='cart-row-item']",
                "fallback_locator": "div.cart-item:has-text('Wireless Mouse')",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.5,
                "max_token_cost": 290,
                "min_confidence_score": 0.95
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-59",
            "name": "Wizard Stepper Step Label Progression",
            "category": "locator_drift",
            "difficulty": "MEDIUM",
            "description": "Step 2 title changed from 'Billing Info' to 'Payment Details' in checkout wizard.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "//div[@class='step-header'][contains(., 'Billing Info')]",
                "error_log": "TimeoutException: Timed out waiting for Step 'Billing Info'",
                "dom_snapshot": "<div class='step-header' data-testid='step-payment' aria-current='step'><span class='step-number'>2</span><span class='step-title'>Payment Details</span></div>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='step-payment']",
                "fallback_locator": ".step-header:has-text('Payment Details')",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.6,
                "max_token_cost": 310,
                "min_confidence_score": 0.94
            }
        }
    },
    {
        "category_dir": "locator_drift",
        "data": {
            "id": "QA-CHALLENGE-60",
            "name": "Sticky Header Mobile Viewport Menu Hidden",
            "category": "locator_drift",
            "difficulty": "HARD",
            "description": "Sidebar toggle button overlapped by fixed top app bar under 375px mobile viewport.",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "button#drawer-toggle",
                "error_log": "ElementClickInterceptedException: Element <button id='drawer-toggle'> is intercepted by <header class='fixed-top'>",
                "dom_snapshot": "<header class='fixed-top'><button class='mobile-hamburger' data-testid='mobile-menu-trigger' aria-label='Open Navigation'>Menu</button></header>"
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='mobile-menu-trigger']",
                "fallback_locator": "button[aria-label='Open Navigation']",
                "strategy": "AOM_ROLE_OR_TESTID"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.2,
                "max_token_cost": 340,
                "min_confidence_score": 0.90
            }
        }
    },

    # =========================================================================
    # DOMAIN 2: API & CONTRACT BREAKAGE (61 - 72)
    # =========================================================================
    {
        "category_dir": "api_contract_drift",
        "data": {
            "id": "QA-CHALLENGE-61",
            "name": "Pagination Envelope Response Object Nesting Drift",
            "category": "api_contract_drift",
            "difficulty": "MEDIUM",
            "description": "Root JSON array wrapped inside { data: { records: [...], total: 50 } }.",
            "failure_vector": {
                "type": "PAYLOAD_SCHEMA_MUTATION",
                "broken_assertion": "assert response.body.size() == 10",
                "error_log": "MissingPropertyException: No such property 'size' for class Map",
                "response_payload": "{\"data\": {\"records\": [{\"id\": 1}, {\"id\": 2}], \"total\": 50}}"
            },
            "expected_resolution": {
                "healed_assertion": "assert response.body.data.records.size() == 2 && response.body.data.total == 50",
                "strategy": "SCHEMA_ENVELOPE_MIGRATION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.5,
                "max_token_cost": 290,
                "min_confidence_score": 0.95
            }
        }
    },
    {
        "category_dir": "api_contract_drift",
        "data": {
            "id": "QA-CHALLENGE-62",
            "name": "ISO-8601 Millisecond Precision Drift in Timestamp",
            "category": "api_contract_drift",
            "difficulty": "EASY",
            "description": "Created_at timestamp format changed from YYYY-MM-DDTHH:mm:ssZ to milliseconds .000Z.",
            "failure_vector": {
                "type": "TIMESTAMP_FORMAT_MUTATION",
                "broken_assertion": "assert response.createdAt == '2026-11-22T10:00:00Z'",
                "error_log": "AssertionError: Expected '2026-11-22T10:00:00Z' but was '2026-11-22T10:00:00.000Z'",
                "response_payload": "{\"id\": 45, \"createdAt\": \"2026-11-22T10:00:00.000Z\"}"
            },
            "expected_resolution": {
                "healed_assertion": "assert response.createdAt.startsWith('2026-11-22T10:00:00')",
                "strategy": "ROBUST_DATETIME_PARSING"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.2,
                "max_token_cost": 250,
                "min_confidence_score": 0.98
            }
        }
    },
    {
        "category_dir": "api_contract_drift",
        "data": {
            "id": "QA-CHALLENGE-63",
            "name": "Currency Amount Float to Serialized String Drift",
            "category": "api_contract_drift",
            "difficulty": "MEDIUM",
            "description": "Price field serialized as string '99.99' instead of number 99.99 to preserve decimal precision.",
            "failure_vector": {
                "type": "DATA_TYPE_MUTATION",
                "broken_assertion": "assert response.amount > 50.0",
                "error_log": "ClassCastException: java.lang.String cannot be compared to java.lang.Double",
                "response_payload": "{\"currency\": \"USD\", \"amount\": \"99.99\"}"
            },
            "expected_resolution": {
                "healed_assertion": "assert Double.parseDouble(response.amount.toString()) > 50.0",
                "strategy": "DEFENSIVE_TYPE_CONVERSION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.4,
                "max_token_cost": 270,
                "min_confidence_score": 0.96
            }
        }
    },
    {
        "category_dir": "api_contract_drift",
        "data": {
            "id": "QA-CHALLENGE-64",
            "name": "Empty Search HTTP Status Shift (200 OK to 204 No Content)",
            "category": "api_contract_drift",
            "difficulty": "EASY",
            "description": "Search endpoint now returns HTTP 204 instead of 200 with empty list.",
            "failure_vector": {
                "type": "STATUS_CODE_SHIFT",
                "broken_assertion": "assert response.statusCode == 200 && response.body.isEmpty()",
                "error_log": "AssertionError: Expected status 200 but received 204",
                "response_payload": ""
            },
            "expected_resolution": {
                "healed_assertion": "assert response.statusCode in [200, 204]",
                "strategy": "PERMISSIBLE_STATUS_CODE_UNION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.2,
                "max_token_cost": 240,
                "min_confidence_score": 0.97
            }
        }
    },
    {
        "category_dir": "api_contract_drift",
        "data": {
            "id": "QA-CHALLENGE-65",
            "name": "OAuth2 Token Response expires_in Type Drift",
            "category": "api_contract_drift",
            "difficulty": "EASY",
            "description": "Auth server returned 'expires_in' as integer seconds 3600 instead of string '3600'.",
            "failure_vector": {
                "type": "DATA_TYPE_MUTATION",
                "broken_assertion": "assert response.expires_in == '3600'",
                "error_log": "AssertionError: Expected '3600' (String) but found 3600 (Integer)",
                "response_payload": "{\"access_token\": \"eyJ...\", \"expires_in\": 3600}"
            },
            "expected_resolution": {
                "healed_assertion": "assert response.expires_in.toString() == '3600'",
                "strategy": "STRING_COERCION_ASSERTION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.1,
                "max_token_cost": 230,
                "min_confidence_score": 0.98
            }
        }
    },
    {
        "category_dir": "api_contract_drift",
        "data": {
            "id": "QA-CHALLENGE-66",
            "name": "REST Endpoint Pluralization Migration (/user to /users)",
            "category": "api_contract_drift",
            "difficulty": "MEDIUM",
            "description": "RESTful convention upgrade changed POST /api/v1/user to POST /api/v1/users.",
            "failure_vector": {
                "type": "ENDPOINT_PATH_MIGRATION",
                "broken_code": "def res = client.post('/api/v1/user', body: userPayload); assert res.statusCode == 201",
                "error_log": "HTTP 404 Not Found: Cannot POST /api/v1/user",
                "api_spec": "POST /api/v1/users [201 Created]"
            },
            "expected_resolution": {
                "healed_code": "def res = client.post('/api/v1/users', body: userPayload); assert res.statusCode == 201",
                "strategy": "REST_URL_PLURALIZATION_HEALING"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.6,
                "max_token_cost": 290,
                "min_confidence_score": 0.95
            }
        }
    },
    {
        "category_dir": "contract",
        "data": {
            "id": "QA-CHALLENGE-67",
            "name": "OpenAPI 3.1 Nullable Property Disallowed",
            "category": "contract",
            "difficulty": "HARD",
            "description": "middle_name field in schema switched from nullable string to strictly non-null optional.",
            "failure_vector": {
                "type": "SCHEMA_VALIDATION_ERROR",
                "broken_code": "client.post('/customers', body: [first: 'John', middle: null, last: 'Doe'])",
                "error_log": "OpenAPIValidationError: 'middle' value cannot be null",
                "schema_diff": "properties.middle: { type: 'string' } (nullable: true removed)"
            },
            "expected_resolution": {
                "healed_code": "def payload = [first: 'John', last: 'Doe']; if (middle) payload.middle = middle; def res = client.post('/customers', body: payload); assert res.statusCode == 201;",
                "strategy": "OMIT_NULL_OPTIONAL_FIELDS"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.2,
                "max_token_cost": 360,
                "min_confidence_score": 0.90
            }
        }
    },
    {
        "category_dir": "contract",
        "data": {
            "id": "QA-CHALLENGE-68",
            "name": "GraphQL Error Extensions Structure Update",
            "category": "contract",
            "difficulty": "MEDIUM",
            "description": "GraphQL error response moved error code from errors[0].message to errors[0].extensions.code.",
            "failure_vector": {
                "type": "GRAPHQL_ERROR_SCHEMA_DRIFT",
                "broken_assertion": "assert response.errors[0].message == 'UNAUTHENTICATED'",
                "error_log": "AssertionError: Expected 'UNAUTHENTICATED' but was 'You must be logged in'",
                "graphql_response": "{\"errors\": [{\"message\": \"You must be logged in\", \"extensions\": {\"code\": \"UNAUTHENTICATED\"}}]}"
            },
            "expected_resolution": {
                "healed_assertion": "assert response.errors[0].extensions?.code == 'UNAUTHENTICATED' || response.errors[0].message == 'UNAUTHENTICATED'",
                "strategy": "GRAPHQL_EXTENSIONS_FALLBACK"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.7,
                "max_token_cost": 300,
                "min_confidence_score": 0.94
            }
        }
    },
    {
        "category_dir": "contract",
        "data": {
            "id": "QA-CHALLENGE-69",
            "name": "Rate-Limiting Header Standardization (IETF Drift)",
            "category": "contract",
            "difficulty": "EASY",
            "description": "Custom header X-RateLimit-Remaining changed to standard RateLimit-Remaining.",
            "failure_vector": {
                "type": "HEADER_NAME_DRIFT",
                "broken_assertion": "assert response.headers['X-RateLimit-Remaining'] != null",
                "error_log": "AssertionError: Header 'X-RateLimit-Remaining' is null",
                "response_headers": "{\"RateLimit-Remaining\": \"99\", \"RateLimit-Limit\": \"100\"}"
            },
            "expected_resolution": {
                "healed_assertion": "assert (response.headers['RateLimit-Remaining'] ?: response.headers['X-RateLimit-Remaining']) != null",
                "strategy": "HEADER_STANDARDIZATION_FALLBACK"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.3,
                "max_token_cost": 260,
                "min_confidence_score": 0.96
            }
        }
    },
    {
        "category_dir": "contract",
        "data": {
            "id": "QA-CHALLENGE-70",
            "name": "Pact CDC Query Parameter Case Sensitivity",
            "category": "contract",
            "difficulty": "MEDIUM",
            "description": "Provider API changed query param ?sortBy=date to ?sort_by=date, breaking Pact consumer contract.",
            "failure_vector": {
                "type": "CONSUMER_CONTRACT_PARAM_MISMATCH",
                "broken_code": "pact.given('orders exist').uponReceiving('get orders').withRequest(path: '/orders', query: [sortBy: 'date'])",
                "error_log": "PactVerificationException: Expected query 'sortBy' but actual was 'sort_by'",
                "provider_spec": "GET /orders?sort_by=date"
            },
            "expected_resolution": {
                "healed_code": "pact.given('orders exist').uponReceiving('get orders').withRequest(path: '/orders', query: [sort_by: 'date']); assert pact.verify();",
                "strategy": "PACT_PARAM_SYNCHRONIZATION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.9,
                "max_token_cost": 320,
                "min_confidence_score": 0.92
            }
        }
    },
    {
        "category_dir": "contract",
        "data": {
            "id": "QA-CHALLENGE-71",
            "name": "Protobuf gRPC-Gateway Field Naming Drift",
            "category": "contract",
            "difficulty": "HARD",
            "description": "gRPC gateway switched JSON serialization from original proto snake_case to lowerCamelCase.",
            "failure_vector": {
                "type": "GRPC_JSON_MAPPING_DRIFT",
                "broken_assertion": "assert response.order_tracking_number != null",
                "error_log": "AssertionError: Property 'order_tracking_number' was null",
                "grpc_json": "{\"orderTrackingNumber\": \"TRK-98124\", \"status\": \"IN_TRANSIT\"}"
            },
            "expected_resolution": {
                "healed_assertion": "assert (response.orderTrackingNumber ?: response.order_tracking_number) != null",
                "strategy": "CAMEL_SNAKE_DUAL_RESOLUTION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.0,
                "max_token_cost": 330,
                "min_confidence_score": 0.91
            }
        }
    },
    {
        "category_dir": "contract",
        "data": {
            "id": "QA-CHALLENGE-72",
            "name": "Webhook HMAC Signature Header Algorithm Migration",
            "category": "contract",
            "difficulty": "MEDIUM",
            "description": "Webhook signature header upgraded from X-Hub-Signature (SHA-1) to X-Hub-Signature-256 (SHA-256).",
            "failure_vector": {
                "type": "WEBHOOK_SECURITY_HEADER_DRIFT",
                "broken_assertion": "assert request.headers['X-Hub-Signature'] != null",
                "error_log": "AssertionError: Header 'X-Hub-Signature' missing from webhook request",
                "request_headers": "{\"X-Hub-Signature-256\": \"sha256=a8f9b...\"}"
            },
            "expected_resolution": {
                "healed_assertion": "assert (request.headers['X-Hub-Signature-256'] ?: request.headers['X-Hub-Signature']) != null",
                "strategy": "SHA256_HEADER_UPGRADE"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.5,
                "max_token_cost": 280,
                "min_confidence_score": 0.95
            }
        }
    },

    # =========================================================================
    # DOMAIN 3: ASYNC TIMING, RACE & BROWSER (73 - 84)
    # =========================================================================
    {
        "category_dir": "timing_and_race",
        "data": {
            "id": "QA-CHALLENGE-73",
            "name": "Debounced Search Input API Latency Spike",
            "category": "timing_and_race",
            "difficulty": "MEDIUM",
            "description": "Input has 400ms debounce; test asserts results after 300ms sleep causing flaky failure.",
            "failure_vector": {
                "type": "DEBOUNCE_RACE_CONDITION",
                "broken_code": "page.fill('#search', 'MacBook'); Thread.sleep(300); assert page.isVisible('.search-result')",
                "error_log": "ElementNotFoundException: '.search-result' not visible after 300ms",
                "debounce_ms": 400
            },
            "expected_resolution": {
                "healed_code": "page.fill('#search', 'MacBook'); page.waitForSelector('.search-result', timeout: 5000);",
                "strategy": "DYNAMIC_SMART_WAIT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.8,
                "max_token_cost": 300,
                "min_confidence_score": 0.93
            }
        }
    },
    {
        "category_dir": "timing_and_race",
        "data": {
            "id": "QA-CHALLENGE-74",
            "name": "Modal Backdrop Fade-in Animation Interception",
            "category": "timing_and_race",
            "difficulty": "MEDIUM",
            "description": "Modal close button clicked while backdrop is animating opacity, intercepting click.",
            "failure_vector": {
                "type": "ANIMATION_CLICK_INTERCEPT",
                "broken_code": "page.click('.btn-open-modal'); page.click('.btn-close-modal');",
                "error_log": "ElementClickInterceptedException: <button class='btn-close-modal'> is obscured by <div class='modal-backdrop fade'>",
                "animation_duration_ms": 300
            },
            "expected_resolution": {
                "healed_code": "page.click('.btn-open-modal'); page.waitForSelector('.modal-backdrop.show'); page.locator('.btn-close-modal').click();",
                "strategy": "DYNAMIC_SMART_WAIT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.0,
                "max_token_cost": 320,
                "min_confidence_score": 0.92
            }
        }
    },
    {
        "category_dir": "timing_and_race",
        "data": {
            "id": "QA-CHALLENGE-75",
            "name": "Server-Sent Events (SSE) Live Feed Stream Race",
            "category": "timing_and_race",
            "difficulty": "HARD",
            "description": "Test checked for live order update before EventSource onmessage event arrived.",
            "failure_vector": {
                "type": "SSE_ASYNC_RACE",
                "broken_code": "service.triggerOrder(); assert page.locator('#order-status').innerText() == 'PROCESSING'",
                "error_log": "AssertionError: Expected 'PROCESSING' but was 'PENDING'",
                "sse_interval_ms": 1200
            },
            "expected_resolution": {
                "healed_code": "service.triggerOrder(); page.waitForSelector('#order-status:has-text(\"PROCESSING\")', timeout: 10000);",
                "strategy": "DYNAMIC_SMART_WAIT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.4,
                "max_token_cost": 350,
                "min_confidence_score": 0.89
            }
        }
    },
    {
        "category_dir": "timing_and_race",
        "data": {
            "id": "QA-CHALLENGE-76",
            "name": "File Upload Progress Bar Premature Assertion",
            "category": "timing_and_race",
            "difficulty": "MEDIUM",
            "description": "Test checked for download link before multipart upload completed processing.",
            "failure_vector": {
                "type": "UPLOAD_ASYNC_RACE",
                "broken_code": "page.setInputFiles('#upload', file); assert page.isVisible('.download-link')",
                "error_log": "ElementNotFoundException: '.download-link' not present immediately after file input",
                "backend_processing_ms": 1500
            },
            "expected_resolution": {
                "healed_code": "page.setInputFiles('#upload', file); page.waitForSelector('.progress-bar-complete'); page.waitForSelector('.download-link');",
                "strategy": "DYNAMIC_SMART_WAIT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.9,
                "max_token_cost": 310,
                "min_confidence_score": 0.93
            }
        }
    },
    {
        "category_dir": "timing_and_race",
        "data": {
            "id": "QA-CHALLENGE-77",
            "name": "Service Worker Cache Invalidation Lag",
            "category": "timing_and_race",
            "difficulty": "HARD",
            "description": "Offline cache not updated before assertion due to background SW registration.",
            "failure_vector": {
                "type": "SERVICE_WORKER_LAG",
                "broken_code": "page.reload(); assert page.locator('.cached-badge').isVisible()",
                "error_log": "AssertionError: '.cached-badge' not visible after reload",
                "sw_state": "installing"
            },
            "expected_resolution": {
                "healed_code": "page.waitForLoadState('networkidle'); page.waitForSelector('.cached-badge', timeout: 8000);",
                "strategy": "DYNAMIC_SMART_WAIT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.3,
                "max_token_cost": 340,
                "min_confidence_score": 0.90
            }
        }
    },
    {
        "category_dir": "timing_and_race",
        "data": {
            "id": "QA-CHALLENGE-78",
            "name": "Multi-Tab Browser Context Switch Race",
            "category": "timing_and_race",
            "difficulty": "MEDIUM",
            "description": "Switching to popup window without waiting for popup page event or DOMContentLoaded.",
            "failure_vector": {
                "type": "MULTI_TAB_SWITCH_RACE",
                "broken_code": "page.click('#open-window'); def newPage = context.pages().get(1); newPage.click('#confirm')",
                "error_log": "IndexOutOfBoundsException: Index 1 out of bounds for context.pages() size 1",
                "popup_delay_ms": 500
            },
            "expected_resolution": {
                "healed_code": "def newPage = context.waitForPage { page.click('#open-window') }; newPage.waitForSelector('#confirm'); newPage.click('#confirm')",
                "strategy": "DYNAMIC_SMART_WAIT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.1,
                "max_token_cost": 330,
                "min_confidence_score": 0.92
            }
        }
    },
    {
        "category_dir": "timing_and_race",
        "data": {
            "id": "QA-CHALLENGE-79",
            "name": "Double-Click Submission Race Condition",
            "category": "timing_and_race",
            "difficulty": "EASY",
            "description": "Submit button disabled on first click; automated test called dblclick() causing 409 Conflict.",
            "failure_vector": {
                "type": "DOUBLE_CLICK_CONFLICT",
                "broken_code": "page.dblclick('#submit-order')",
                "error_log": "HTTP 409 Conflict: Order already submitted by concurrent request",
                "backend_lock": "IDEMPOTENT_SUBMIT_KEY"
            },
            "expected_resolution": {
                "healed_code": "page.click('#submit-order'); page.waitForSelector('#order-confirmation', timeout: 8000);",
                "strategy": "DYNAMIC_SMART_WAIT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.4,
                "max_token_cost": 270,
                "min_confidence_score": 0.96
            }
        }
    },
    {
        "category_dir": "browser",
        "data": {
            "id": "QA-CHALLENGE-80",
            "name": "Retina Display High-DPI Scaling Element Offset",
            "category": "browser",
            "difficulty": "HARD",
            "description": "Device scale factor 2.0 caused bounding box coordinate click to miss interactive target.",
            "failure_vector": {
                "type": "HIGH_DPI_CLICK_OFFSET",
                "broken_code": "page.mouse.click(250, 140)",
                "error_log": "AssertionError: Action at (250, 140) did not trigger expected button click",
                "deviceScaleFactor": 2.0
            },
            "expected_resolution": {
                "healed_code": "page.locator('[data-testid=\"checkout-cta\"]').scrollIntoView(); page.locator('[data-testid=\"checkout-cta\"]').click()",
                "strategy": "LOCATOR_BASED_DISPATCH"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.2,
                "max_token_cost": 340,
                "min_confidence_score": 0.90
            }
        }
    },
    {
        "category_dir": "browser",
        "data": {
            "id": "QA-CHALLENGE-81",
            "name": "WebKit WebFont Loading Layout Shift",
            "category": "browser",
            "difficulty": "MEDIUM",
            "description": "Custom web font loaded late, causing button to shift downwards by 30px during click.",
            "failure_vector": {
                "type": "FONT_LAYOUT_SHIFT",
                "broken_code": "page.click('#apply-coupon')",
                "error_log": "ElementClickInterceptedException: Element detached or moved during click action",
                "layout_shift_px": 30
            },
            "expected_resolution": {
                "healed_code": "page.waitForLoadState('networkidle'); page.locator('#apply-coupon').scrollIntoView(); page.locator('#apply-coupon').click()",
                "strategy": "LOCATOR_BASED_DISPATCH"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.8,
                "max_token_cost": 310,
                "min_confidence_score": 0.93
            }
        }
    },
    {
        "category_dir": "browser",
        "data": {
            "id": "QA-CHALLENGE-82",
            "name": "IndexedDB Asynchronous Write Commit Delay",
            "category": "browser",
            "difficulty": "HARD",
            "description": "Page navigated before IndexedDB transaction 'complete' event fired, losing offline state.",
            "failure_vector": {
                "type": "INDEXED_DB_ASYNC_RACE",
                "broken_code": "page.evaluate('saveCartOffline()'); page.goto('/cart'); assert page.locator('.cart-item').count() > 0",
                "error_log": "AssertionError: Expected cart item count > 0 but found 0",
                "idb_transaction": "READ_WRITE"
            },
            "expected_resolution": {
                "healed_code": "page.evaluate('await saveCartOffline()'); page.goto('/cart'); page.waitForSelector('.cart-item')",
                "strategy": "LOCATOR_BASED_DISPATCH"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.4,
                "max_token_cost": 360,
                "min_confidence_score": 0.89
            }
        }
    },
    {
        "category_dir": "browser",
        "data": {
            "id": "QA-CHALLENGE-83",
            "name": "Micro-Frontend Cross-Origin postMessage Barrier",
            "category": "browser",
            "difficulty": "MEDIUM",
            "description": "Parent app asserted child iframe state before postMessage handshake resolved.",
            "failure_vector": {
                "type": "POST_MESSAGE_HANDSHAKE_RACE",
                "broken_code": "page.click('#sync-profile'); assert page.locator('#profile-synced').isVisible()",
                "error_log": "ElementNotFoundException: '#profile-synced' not visible within 2000ms",
                "origin": "https://auth.enterprise.internal"
            },
            "expected_resolution": {
                "healed_code": "page.click('#sync-profile'); page.waitForSelector('#profile-synced', timeout: 8000)",
                "strategy": "LOCATOR_BASED_DISPATCH"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.9,
                "max_token_cost": 310,
                "min_confidence_score": 0.92
            }
        }
    },
    {
        "category_dir": "browser",
        "data": {
            "id": "QA-CHALLENGE-84",
            "name": "Virtual Scroll Batch Item Deletion Re-render",
            "category": "browser",
            "difficulty": "MEDIUM",
            "description": "Removing multiple items in virtual list detached DOM nodes before next remove click.",
            "failure_vector": {
                "type": "VIRTUAL_LIST_STALE_DETACH",
                "broken_code": "page.locator('.row-btn').all().each { it.click() }",
                "error_log": "StaleElementReferenceException: Element is not attached to the DOM document",
                "list_size": 100
            },
            "expected_resolution": {
                "healed_code": "while (page.locator('[data-testid=\"remove-row-btn\"]').count() > 0) { page.locator('[data-testid=\"remove-row-btn\"]').first().click(); page.waitForSelector('.table-updated'); }",
                "strategy": "LOCATOR_BASED_DISPATCH"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.1,
                "max_token_cost": 330,
                "min_confidence_score": 0.91
            }
        }
    },

    # =========================================================================
    # DOMAIN 4: CODE QUALITY, ANTI-TAUTOLOGY & POM (85 - 91)
    # =========================================================================
    {
        "category_dir": "fake_pass_tautology",
        "data": {
            "id": "QA-CHALLENGE-85",
            "name": "Unawaited Async Assertion in forEach Loop",
            "category": "fake_pass_tautology",
            "difficulty": "MEDIUM",
            "description": "async expect inside items.forEach(...) never waited, test exits green prematurely.",
            "failure_vector": {
                "type": "ASYNC_FOREACH_SILENT_PASS",
                "code_snippet": "items.forEach(async (item) => { expect(await item.isVisible()).toBeTruthy(); });",
                "detection_rule": "UNAWAITED_ASYNC_EXPECT"
            },
            "expected_resolution": {
                "healed_code": "for (const item of items) { await expect(item).toBeVisible(); }",
                "strategy": "AST_ASYNC_AWAIT_ENFORCEMENT"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.5,
                "max_token_cost": 270,
                "min_confidence_score": 0.96
            }
        }
    },
    {
        "category_dir": "fake_pass_tautology",
        "data": {
            "id": "QA-CHALLENGE-86",
            "name": "Assertion Guarded Inside Never-Executing if Branch",
            "category": "fake_pass_tautology",
            "difficulty": "EASY",
            "description": "Assertion placed inside 'if (data.hasErrors)' which is false, leading to 0 assertions executed.",
            "failure_vector": {
                "type": "CONDITIONAL_ASSERTION_BYPASS",
                "code_snippet": "def res = api.call(); if (res.hasErrors) { assert res.errorMessage == 'OK'; } // 0 asserts on success!",
                "detection_rule": "ZERO_ASSERTION_TEST"
            },
            "expected_resolution": {
                "healed_code": "def res = api.call(); assert !res.hasErrors && res.status == 200;",
                "strategy": "MUTATION_TESTING_KILLS_TAUTOLOGY"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.2,
                "max_token_cost": 240,
                "min_confidence_score": 0.98
            }
        }
    },
    {
        "category_dir": "fake_pass_tautology",
        "data": {
            "id": "QA-CHALLENGE-87",
            "name": "Tautological Boolean Logic (assert flag || true)",
            "category": "fake_pass_tautology",
            "difficulty": "EASY",
            "description": "Developer wrote assert result.isSuccess() || true to suppress flaky test.",
            "failure_vector": {
                "type": "TAUTOLOGY_OR_TRUE",
                "code_snippet": "assert result.isSuccess() || true;",
                "detection_rule": "TAUTOLOGY_PATTERN"
            },
            "expected_resolution": {
                "healed_code": "assert result.isSuccess() == true && result.errorCode == null;",
                "strategy": "MUTATION_TESTING_KILLS_TAUTOLOGY"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.1,
                "max_token_cost": 220,
                "min_confidence_score": 0.99
            }
        }
    },
    {
        "category_dir": "fake_pass_tautology",
        "data": {
            "id": "QA-CHALLENGE-88",
            "name": "Swallowed Timeout Exception with Dummy Boolean Return",
            "category": "fake_pass_tautology",
            "difficulty": "MEDIUM",
            "description": "catch (TimeoutException e) { return true; } swallowed real timeouts.",
            "failure_vector": {
                "type": "SWALLOWED_TIMEOUT_EXCEPTION",
                "code_snippet": "try { page.waitForSelector('#banner'); } catch (Exception e) { /* ignore */ } assert true;",
                "detection_rule": "EMPTY_CATCH_BLOCK"
            },
            "expected_resolution": {
                "healed_code": "page.waitForSelector('#banner', timeout: 10000); assert page.isVisible('#banner');",
                "strategy": "MUTATION_TESTING_KILLS_TAUTOLOGY"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.4,
                "max_token_cost": 260,
                "min_confidence_score": 0.97
            }
        }
    },
    {
        "category_dir": "stale_and_mutation",
        "data": {
            "id": "QA-CHALLENGE-89",
            "name": "GraphQL Mutation Re-hydration Stale DOM Node",
            "category": "stale_and_mutation",
            "difficulty": "MEDIUM",
            "description": "Apollo Client re-hydrated the entire DOM tree after mutation, invalidating held element reference.",
            "failure_vector": {
                "type": "DOM_REHYDRATION_STALE",
                "broken_code": "def submitBtn = page.locator('#save'); submitBtn.click(); page.waitForResponse('/graphql'); submitBtn.click()",
                "error_log": "StaleElementReferenceException: The element is not attached to the DOM document",
                "framework": "Apollo Client v3"
            },
            "expected_resolution": {
                "healed_code": "page.locator('#save').click(); page.waitForResponse('/graphql'); page.locator('#save').waitFor(); page.locator('#save').click()",
                "strategy": "ELIMINATE_STALE_TRAP"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.7,
                "max_token_cost": 290,
                "min_confidence_score": 0.94
            }
        }
    },
    {
        "category_dir": "test_design",
        "data": {
            "id": "QA-CHALLENGE-90",
            "name": "Leap Year Date Calculation Boundary Bug",
            "category": "test_design",
            "difficulty": "HARD",
            "description": "Test only tested 30/31 day months, missed February 29th leap year date picker behavior.",
            "failure_vector": {
                "type": "BOUNDARY_VALUE_OMISSION",
                "code_snippet": "@ParameterizedTest @ValueSource(strings = ['2026-01-31', '2026-03-31']) void testMonthEnd(String d) { ... }",
                "error_log": "Missing test case for leap year boundary '2028-02-29'",
                "boundary": "LEAP_YEAR_FEB_29"
            },
            "expected_resolution": {
                "healed_code": "@ParameterizedTest @ValueSource(strings = ['2026-01-31', '2026-03-31', '2028-02-29']) void testMonthEnd(String d) { ... assert validateDate(d); }",
                "strategy": "BOUNDARY_VALUE_ANALYSIS"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.0,
                "max_token_cost": 320,
                "min_confidence_score": 0.92
            }
        }
    },
    {
        "category_dir": "test_design",
        "data": {
            "id": "QA-CHALLENGE-91",
            "name": "FSM Invalid State Transition (Cancelled to Shipped)",
            "category": "test_design",
            "difficulty": "MEDIUM",
            "description": "Test attempted illegal transition in order state machine without testing transition rejection.",
            "failure_vector": {
                "type": "INVALID_STATE_TRANSITION",
                "code_snippet": "order.cancel(); order.ship(); assert order.status == 'SHIPPED';",
                "error_log": "IllegalStateException: Cannot transition from CANCELLED to SHIPPED",
                "fsm": "OrderLifecycleFSM"
            },
            "expected_resolution": {
                "healed_code": "order.cancel(); assertThrows(IllegalStateException) { order.ship() }; assert order.status == 'CANCELLED';",
                "strategy": "FSM_TRANSITION_VERIFICATION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.6,
                "max_token_cost": 280,
                "min_confidence_score": 0.95
            }
        }
    },

    # =========================================================================
    # DOMAIN 5: SECURITY, TRIAGE & NEGATIVE CONTROLS (92 - 100)
    # =========================================================================
    {
        "category_dir": "security",
        "data": {
            "id": "QA-CHALLENGE-92",
            "name": "Stored XSS in User Biography Field",
            "category": "security",
            "difficulty": "HARD",
            "description": "User bio renders unescaped HTML script tag in public profile preview.",
            "failure_vector": {
                "type": "STORED_XSS",
                "code_snippet": "page.fill('#bio', '<script>alert(1)</script>'); page.click('#save');",
                "error_log": "SecurityVulnerability: Unescaped raw HTML rendered in .bio-preview",
                "cwe": "CWE-79"
            },
            "expected_resolution": {
                "healed_code": "page.fill('#bio', '<script>alert(1)</script>'); page.click('#save'); assert !page.innerHTML('.bio-preview').contains('<script>');",
                "strategy": "XSS_SANITIZATION_GUARD"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.2,
                "max_token_cost": 340,
                "min_confidence_score": 0.91
            }
        }
    },
    {
        "category_dir": "security",
        "data": {
            "id": "QA-CHALLENGE-93",
            "name": "BOLA/IDOR Missing Tenant Isolation in PDF Export",
            "category": "security",
            "difficulty": "HARD",
            "description": "User in tenant A able to download invoice PDF of tenant B by tampering invoiceId.",
            "failure_vector": {
                "type": "BOLA_IDOR_VULNERABILITY",
                "code_snippet": "def res = client.get('/invoices/TENANT_B_99.pdf', headers: [Authorization: tokenTenantA]);",
                "error_log": "SecurityVulnerability: Received HTTP 200 instead of HTTP 403 Forbidden",
                "cwe": "CWE-639"
            },
            "expected_resolution": {
                "healed_code": "def res = client.get('/invoices/TENANT_B_99.pdf', headers: [Authorization: tokenTenantA]); assert res.statusCode == 403;",
                "strategy": "IDOR_AUTHORIZATION_ASSERTION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.3,
                "max_token_cost": 350,
                "min_confidence_score": 0.90
            }
        }
    },
    {
        "category_dir": "security",
        "data": {
            "id": "QA-CHALLENGE-94",
            "name": "Plaintext AWS Secret Access Key in Console Output",
            "category": "security",
            "difficulty": "MEDIUM",
            "description": "Test helper logged full exception object dumping raw AWS credentials.",
            "failure_vector": {
                "type": "SECRET_LEAKAGE",
                "code_snippet": "println('Config: ' + awsConfig); // Prints AWS_SECRET_ACCESS_KEY",
                "error_log": "SecurityViolation: Detected high-entropy secret in stdout logs",
                "cwe": "CWE-312"
            },
            "expected_resolution": {
                "healed_code": "println('Config loaded for region: ' + awsConfig.region); assert awsConfig.isValid();",
                "strategy": "SECRET_MASKING_GUARD"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.5,
                "max_token_cost": 270,
                "min_confidence_score": 0.96
            }
        }
    },
    {
        "category_dir": "security",
        "data": {
            "id": "QA-CHALLENGE-95",
            "name": "SSRF Cloud Metadata Callback Vulnerability",
            "category": "security",
            "difficulty": "HARD",
            "description": "Avatar URL downloader allows access to http://169.254.169.254/latest/meta-data/.",
            "failure_vector": {
                "type": "SSRF_VULNERABILITY",
                "code_snippet": "client.post('/avatar', body: [url: 'http://169.254.169.254/latest/meta-data/iam/']);",
                "error_log": "SecurityVulnerability: Internal link followed without IP whitelist validation",
                "cwe": "CWE-918"
            },
            "expected_resolution": {
                "healed_code": "def res = client.post('/avatar', body: [url: 'http://169.254.169.254/latest/meta-data/']); assert res.statusCode == 400;",
                "strategy": "SSRF_FIREWALL_GUARD"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.4,
                "max_token_cost": 360,
                "min_confidence_score": 0.89
            }
        }
    },
    {
        "category_dir": "triage",
        "data": {
            "id": "QA-CHALLENGE-96",
            "name": "Shared Database State Pollution from Previous Run",
            "category": "triage",
            "difficulty": "MEDIUM",
            "description": "Static user email 'test@example.com' collided with existing record from uncleaned previous suite.",
            "failure_vector": {
                "type": "DB_STATE_POLLUTION",
                "broken_code": "db.insertUser('test@example.com'); assert db.countUsers() == 1;",
                "error_log": "SQLIntegrityConstraintViolationException: Duplicate entry 'test@example.com' for key 'users.email'",
                "root_cause": "HARDCODED_STATIC_TEST_DATA"
            },
            "expected_resolution": {
                "healed_code": "def email = 'auto_' + System.currentTimeMillis() + '@example.com'; db.insertUser(email); addCleanup { db.cleanupFixture(email) };",
                "strategy": "IDEMPOTENT_DYNAMIC_TEST_DATA"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 1.7,
                "max_token_cost": 290,
                "min_confidence_score": 0.94
            }
        }
    },
    {
        "category_dir": "triage",
        "data": {
            "id": "QA-CHALLENGE-97",
            "name": "Cascading Downstream Service 503 Isolation",
            "category": "triage",
            "difficulty": "HARD",
            "description": "Payment gateway downtime threw 503, causing frontend 500 error; agent must pinpoint gateway 503.",
            "failure_vector": {
                "type": "CASCADING_SERVICE_FAILURE",
                "broken_code": "assert response.statusCode == 200;",
                "error_log": "HTTP 500 Internal Server Error (Caused by DownstreamGatewayTimeoutException: 503 Service Unavailable)",
                "root_cause": "DOWNSTREAM_DEPENDENCY_FAILURE"
            },
            "expected_resolution": {
                "healed_code": "def traceId = 'auto_' + System.currentTimeMillis(); assert response.statusCode in [200, 503]; addCleanup { log.info('Triaged ' + traceId) };",
                "strategy": "DOWNSTREAM_DEPENDENCY_ISOLATION"
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.1,
                "max_token_cost": 330,
                "min_confidence_score": 0.91
            }
        }
    },
    {
        "category_dir": "negative_control",
        "data": {
            "id": "QA-CHALLENGE-98",
            "name": "Genuine Inventory Underflow Defect (Negative Stock Allowed)",
            "category": "negative_control",
            "difficulty": "HARD",
            "description": "Application allows ordering 999 items when stock is 10, resulting in stock = -989. Agent must NOT fake pass.",
            "failure_vector": {
                "type": "GENUINE_BUSINESS_LOGIC_BUG",
                "broken_code": "orderService.checkout(itemId: 101, qty: 999); assert stockService.getStock(101) >= 0;",
                "error_log": "AssertionError: Expected stock >= 0 but was -989",
                "application_bug": "INVENTORY_UNDERFLOW"
            },
            "expected_resolution": {
                "strategy": "REPORT_AUT_DEFECT",
                "notes": "Truth Anchor: Reject healing. Report genuine AUT defect: inventory underflow allows negative stock."
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.0,
                "max_token_cost": 300,
                "min_confidence_score": 0.98
            }
        }
    },
    {
        "category_dir": "negative_control",
        "data": {
            "id": "QA-CHALLENGE-99",
            "name": "Genuine Authentication Bypass Allowing Guest Admin Access",
            "category": "negative_control",
            "difficulty": "HARD",
            "description": "Admin endpoint /admin/users accessible without session cookie. Agent must NOT patch test to accept 200.",
            "failure_vector": {
                "type": "GENUINE_SECURITY_DEFECT",
                "broken_code": "def res = client.get('/admin/users'); assert res.statusCode == 401;",
                "error_log": "AssertionError: Expected status 401 but received 200 OK without credentials",
                "application_bug": "UNAUTHENTICATED_ADMIN_ACCESS"
            },
            "expected_resolution": {
                "strategy": "REPORT_AUT_DEFECT",
                "notes": "Truth Anchor: Reject healing. Report critical security defect: unauthenticated access to /admin/users."
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.2,
                "max_token_cost": 320,
                "min_confidence_score": 0.99
            }
        }
    },
    {
        "category_dir": "negative_control",
        "data": {
            "id": "QA-CHALLENGE-100",
            "name": "Genuine Currency Conversion Rounding Defect in Cart",
            "category": "negative_control",
            "difficulty": "HARD",
            "description": "EUR to USD conversion truncates cents: 19.99 EUR * 1.08 = 21.58 USD, but app returns 21.00 USD.",
            "failure_vector": {
                "type": "GENUINE_CALCULATION_DEFECT",
                "broken_code": "assert cart.totalUsd == 21.58;",
                "error_log": "AssertionError: Expected 21.58 but received 21.00",
                "application_bug": "INTEGER_TRUNCATION_ROUNDING"
            },
            "expected_resolution": {
                "strategy": "REPORT_AUT_DEFECT",
                "notes": "Truth Anchor: Reject healing. Report financial calculation defect: integer truncation during currency conversion."
            },
            "benchmark_targets": {
                "max_heal_time_sec": 2.0,
                "max_token_cost": 310,
                "min_confidence_score": 0.98
            }
        }
    }
]


def build():
    total_written = 0
    for item in NEW_CHALLENGES:
        folder = os.path.join(DATASET_DIR, item["category_dir"])
        os.makedirs(folder, exist_ok=True)
        filename = f"{item['data']['id'].lower()}_{item['data']['category']}.json"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(item["data"], f, indent=2)
        total_written += 1

    print(f"✅ Generated {total_written} new Ablation Benchmark Challenges (46 to 100) in {DATASET_DIR}")


if __name__ == "__main__":
    build()
