#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-Scenario Unit Tests for tools/api/generate_api_matrix.py."""

import json
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.api.generate_api_matrix import generate_field_boundaries, parse_spec, to_markdown


class TestGenerateApiMatrix:
    def test_positive_parse_spec_and_markdown(self):
        spec = {
            "paths": {
                "/api/v1/orders": {
                    "post": {
                        "summary": "Create order",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "required": ["code"],
                                        "properties": {
                                            "code": {"type": "string", "minLength": 3, "maxLength": 12},
                                            "amount": {"type": "integer", "minimum": 1, "maximum": 100},
                                            "active": {"type": "boolean"},
                                        },
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }
        matrix = parse_spec(spec)
        types = {row["type"] for row in matrix}
        assert {"POSITIVE", "NEGATIVE", "BOUNDARY"}.issubset(types)
        assert any(r["expected_status"] == 201 and r["type"] == "POSITIVE" for r in matrix)
        assert any("Missing_code" in r["name"] and r["expected_status"] == 400 for r in matrix)
        assert any("..." in r["description"] for r in matrix)
        assert any("with value ''" in r["description"] for r in matrix)
        assert any("with value 'AA'" in r["description"] for r in matrix)

        md = to_markdown(matrix)
        assert "| ID | Method | Endpoint | Test Type |" in md
        assert "/api/v1/orders" in md

    def test_boundary_empty_spec_boolean_and_min_length_zero(self):
        assert parse_spec({}) == []
        bounds = generate_field_boundaries("note", {"type": "string", "minLength": 0, "maxLength": 5})
        assert any("Below MinLength" in b["scenario"] and b["expected"] == 200 for b in bounds)
        bool_bounds = generate_field_boundaries("active", {"type": "boolean"})
        assert len(bool_bounds) == 1 and bool_bounds[0]["value"] == "not_a_bool"
        assert generate_field_boundaries("obj", {"type": "object"}) == []

    def test_cli_sample_json_markdown_and_spec_output(self, tmp_path, monkeypatch, capsys):
        from tools.api.generate_api_matrix import main as matrix_main

        out_file = tmp_path / "matrix.json"
        monkeypatch.setattr(sys, "argv", ["generate_api_matrix.py", "--sample", "--format", "json", "--output", str(out_file)])
        matrix_main()
        assert out_file.is_file()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert len(data) > 0

        monkeypatch.setattr(sys, "argv", ["generate_api_matrix.py"])
        matrix_main()
        assert "| ID | Method | Endpoint | Test Type |" in capsys.readouterr().out

        unicode_spec = tmp_path / "uni_spec.json"
        unicode_spec.write_text(
            json.dumps({"paths": {"/vi": {"get": {"summary": "Kiểm tra Tiếng Việt"}}}}, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["generate_api_matrix.py", "--spec", str(unicode_spec), "--format", "json"])
        matrix_main()
        uni_out = capsys.readouterr().out
        assert "Kiểm tra Tiếng Việt" in uni_out
        assert "\\u1ec3" not in uni_out

        res_missing = subprocess.run(
            [sys.executable, os.path.join(ROOT_DIR, "tools", "api", "generate_api_matrix.py"), "--spec", str(tmp_path / "missing_spec.json")],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res_missing.returncode == 1
