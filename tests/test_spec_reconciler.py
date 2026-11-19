#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit Tests for Phase 2: Ingestion Agent Đối Soát OpenAPI/Swagger + User Story
(tools/api/spec_reconciler.py)
"""

import os
import sys
import json
import subprocess
import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.api.spec_reconciler import SpecReconciler
from tools.lint.manual_tc_linter import lint_test_case_file


@pytest.fixture
def sample_spec():
    return {
        "openapi": "3.0.0",
        "info": {"title": "User API", "version": "1.0.0"},
        "paths": {
            "/api/v1/users": {
                "post": {
                    "summary": "Create User",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/UserInput"
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}}
                }
            }
        },
        "components": {
            "schemas": {
                "UserInput": {
                    "type": "object",
                    "required": ["username", "email"],
                    "properties": {
                        "username": {"type": "string", "minLength": 3, "maxLength": 20},
                        "email": {"type": "string", "format": "email", "maxLength": 100},
                        "phone": {"type": "string", "maxLength": 15},
                        "age": {"type": "integer", "minimum": 18, "maximum": 99}
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_story_with_conflicts():
    return """# User Story: Đăng ký thành viên mới (User Registration)
As a new visitor, I want to register a user account.
Acceptance Criteria:
- AC-01: User can enter username and email.
- AC-02: Phone number must be at most 10 digits.
- AC-03: User can optionally input fax number.
"""


def test_reconciler_initialization(sample_spec, sample_story_with_conflicts):
    reconciler = SpecReconciler(sample_spec, sample_story_with_conflicts)
    assert reconciler.spec["info"]["title"] == "User API"
    assert "Đăng ký" in reconciler.story_model["title"]


def test_extract_schema_properties(sample_spec, sample_story_with_conflicts):
    reconciler = SpecReconciler(sample_spec, sample_story_with_conflicts)
    schema, path, method = reconciler.get_primary_mutation_schema()
    assert path == "/api/v1/users"
    assert method == "POST"

    props = reconciler.extract_schema_constraints(schema)
    assert "username" in props
    assert props["username"]["required"] is True
    assert props["username"]["minLength"] == 3
    assert props["username"]["maxLength"] == 20
    assert props["email"]["format"] == "email"
    assert props["age"]["minimum"] == 18


def test_reconcile_detects_mismatches(sample_spec, sample_story_with_conflicts):
    reconciler = SpecReconciler(sample_spec, sample_story_with_conflicts)
    recon = reconciler.reconcile()

    assert recon["discrepancies_count"] >= 1
    disc_types = [d["type"] for d in recon["discrepancies"]]

    # Expect CONSTRAINT_MISMATCH on phone (story max 10 vs schema max 15)
    assert "CONSTRAINT_MISMATCH" in disc_types

    # Expect OMITTED_REQUIRED_IN_STORY for required fields not explicitly marked required
    assert any("OMITTED_REQUIRED_IN_STORY" in t for t in disc_types)


def test_generate_reconciliation_report_md(sample_spec, sample_story_with_conflicts):
    reconciler = SpecReconciler(sample_spec, sample_story_with_conflicts)
    recon = reconciler.reconcile()
    report = reconciler.generate_reconciliation_report_md(recon)

    assert "# BÁO CÁO ĐỐI SOÁT ĐẶC TẢ KỸ THUẬT" in report
    assert "DANH SÁCH BẤT ĐỒNG BỘ" in report
    assert "MA TRẬN RÀNG BUỘC KỸ THUẬT BACKEND" in report
    assert "phone" in report


def test_generate_12_column_test_suite_and_lint(sample_spec, sample_story_with_conflicts, tmp_path):
    reconciler = SpecReconciler(sample_spec, sample_story_with_conflicts)
    recon = reconciler.reconcile()
    test_suite_md = reconciler.generate_12_column_test_suite_md(recon, module_prefix="USR")

    # Verify 12-column header
    assert "| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |" in test_suite_md

    # Save to temp file and run manual_tc_linter
    out_file = tmp_path / "test_cases_reconciled.md"
    out_file.write_text(test_suite_md, encoding="utf-8")

    lint_res = lint_test_case_file(str(out_file))
    assert lint_res["passed"] is True, f"Linter failed with defects: {lint_res.get('defects')}"
    assert len(lint_res["defects"]) == 0
    assert lint_res["total_test_cases"] >= 8


def test_spec_reconciler_handles_all_of_composition():
    """Verify reconciler correctly handles allOf inheritance / composition."""
    spec_with_all_of = {
        "openapi": "3.0.0",
        "info": {"title": "Composite API", "version": "1.0.0"},
        "paths": {
            "/api/v1/accounts": {
                "post": {
                    "summary": "Create Account",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "allOf": [
                                        {"$ref": "#/components/schemas/BaseEntity"},
                                        {
                                            "type": "object",
                                            "required": ["account_number"],
                                            "properties": {
                                                "account_number": {"type": "string", "maxLength": 16},
                                                "balance": {"type": "number", "minimum": 0}
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "BaseEntity": {
                    "type": "object",
                    "required": ["created_by"],
                    "properties": {
                        "created_by": {"type": "string", "maxLength": 50}
                    }
                }
            }
        }
    }

    story = """# Story: Tạo tài khoản ngân hàng
Acceptance Criteria:
- created_by bắt buộc
- account_number bắt buộc, tối đa 16 số
- balance tối thiểu 0
"""
    reconciler = SpecReconciler(spec_with_all_of, story)
    schema, path, method = reconciler.get_primary_mutation_schema()
    props = reconciler.extract_schema_constraints(schema)

    # Both BaseEntity and subschema properties must be resolved
    assert "created_by" in props
    assert "account_number" in props
    assert "balance" in props
    assert props["created_by"]["required"] is True
    assert props["account_number"]["maxLength"] == 16


def test_spec_reconciler_parses_markdown_tables_in_story():
    """Verify reconciler can extract fields directly from Markdown tables in User Stories."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/api/v1/items": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["item_code", "unit_price"],
                                    "properties": {
                                        "item_code": {"type": "string", "maxLength": 10},
                                        "unit_price": {"type": "number", "minimum": 1}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    story_with_table = """# Story: Tạo danh mục mặt hàng
Chi tiết các trường thông tin:

| Field | Type | Required | Constraints |
| :--- | :--- | :---: | :--- |
| item_code | String | Có | Tối đa 10 ký tự |
| unit_price | Number | Có | Tối thiểu 1 |
| discount_rate | Number | Không | Tối đa 50 |
"""
    reconciler = SpecReconciler(spec, story_with_table)
    recon = reconciler.reconcile()

    # discount_rate should be flagged as GHOST_FIELD_IN_STORY since it's not in schema
    ghosts = [d for d in recon["discrepancies"] if d["type"] == "GHOST_FIELD_IN_STORY"]
    assert len(ghosts) >= 1
    assert any("discount_rate" in g["field"] for g in ghosts)


def test_spec_reconciler_detects_type_mismatch():
    """Verify reconciler flags TYPE_MISMATCH when Story and Schema disagree on data type."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/api/v1/profile": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "age": {"type": "integer", "minimum": 18}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    story = """# Story: Cập nhật Profile
Acceptance Criteria:
- Trường `age` là kiểu chuỗi văn bản (string), nhập số tuổi
"""
    reconciler = SpecReconciler(spec, story)
    recon = reconciler.reconcile()

    type_mismatches = [d for d in recon["discrepancies"] if d["type"] == "TYPE_MISMATCH"]
    assert len(type_mismatches) >= 1
    assert type_mismatches[0]["field"] == "age"


def test_spec_reconciler_cli_execution(tmp_path):
    """Verify CLI command line invocation executes without errors and creates outputs."""
    spec_path = tmp_path / "test_spec.json"
    spec_path.write_text(json.dumps({
        "openapi": "3.0.0",
        "paths": {
            "/api/v1/ping": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["message"],
                                    "properties": {
                                        "message": {"type": "string", "maxLength": 50}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }), encoding="utf-8")

    story_path = tmp_path / "test_story.md"
    story_path.write_text("""# Story: Ping Service
Acceptance Criteria:
- message bắt buộc, tối đa 50 ký tự
""", encoding="utf-8")

    out_tc = tmp_path / "out_tc.md"
    out_rep = tmp_path / "out_report.md"

    cmd = [
        sys.executable,
        os.path.join(_REPO_ROOT, "tools", "api", "spec_reconciler.py"),
        str(story_path),
        str(spec_path),
        "-o", str(out_tc),
        "--report", str(out_rep)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert out_tc.exists()
    assert out_rep.exists()
    assert "ISO 29119-3" in res.stdout
