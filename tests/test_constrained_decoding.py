# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_constrained_decoding.py — Unit & Integration Test Suite for Constrained Decoding (R1)
-------------------------------------------------------------------------------------------------
Validates two-phase decoding engine across 4 scenario classes:
  1. TestConstrainedDecodingPositive: Valid thoughts projected to JSON, AST, Patch, Schema.
  2. TestConstrainedDecodingNegative: Malformed, unparseable thoughts, schema errors handled gracefully.
  3. TestConstrainedDecodingBoundary: Empty, unicode, deeply nested, giant inputs, auto-repair pushdown.
  4. TestConstrainedDecodingCLIFlags: CLI argument parsing, flags (--text, --input, --schema, --mode, --output, --json).
"""

import os
import sys
import json
import ast
import subprocess
import tempfile
import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS_DIR = os.path.join(_REPO_ROOT, "tools")
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from reasoning.constrained_decoding import (
    ConstrainedDecoder,
)


class TestConstrainedDecodingPositive:
    """Valid thinking streams projected to JSON, AST, patch diffs, and schema enforcement."""

    def test_project_json_from_xml_thought_tags(self):
        decoder = ConstrainedDecoder()
        stream = (
            "<thought>\n"
            "Analyzing payment idempotency key requirements.\n"
            "We need a unique transaction code and an expiration window.\n"
            "</thought>\n"
            '{"transaction_id": "TXN_99182", "expires_in_secs": 3600, "idempotent": true}'
        )
        result = decoder.project_json(stream)

        assert isinstance(result, dict)
        assert result["transaction_id"] == "TXN_99182"
        assert result["expires_in_secs"] == 3600
        assert result["idempotent"] is True
        assert "Analyzing payment idempotency" in decoder.last_extracted_thought

    def test_project_json_with_auto_repair_common_slips(self):
        decoder = ConstrainedDecoder()
        # Contains unquoted keys, single quotes, Python boolean, trailing comma
        malformed = "{ status: 'active', retries: 3, verified: True, tags: ['qa', 'api',], }"
        result = decoder.project_json(malformed)

        assert result["status"] == "active"
        assert result["retries"] == 3
        assert result["verified"] is True
        assert result["tags"] == ["qa", "api"]
        assert len(decoder.last_repaired_errors) >= 3

    def test_project_json_with_schema_enforcement_and_type_coercion(self):
        decoder = ConstrainedDecoder()
        schema = {
            "type": "object",
            "required": ["endpoint", "timeout_ms", "max_concurrency", "enabled"],
            "properties": {
                "endpoint": {"type": "string"},
                "timeout_ms": {"type": "integer"},
                "max_concurrency": {"type": "integer"},
                "enabled": {"type": "boolean"},
            },
        }
        # timeout_ms is string "3000", max_concurrency is missing, enabled is "yes"
        input_stream = '{"endpoint": "/api/v2/checkout", "timeout_ms": "3000", "enabled": "yes"}'
        result = decoder.project_json(input_stream, schema=schema)

        assert result["endpoint"] == "/api/v2/checkout"
        assert result["timeout_ms"] == 3000
        assert isinstance(result["timeout_ms"], int)
        assert result["max_concurrency"] == 0  # Injected default
        assert result["enabled"] is True  # Coerced from "yes"
        assert any("Injected default value" in r for r in decoder.last_repaired_errors)

    def test_project_patch_from_diff_code_fence(self):
        decoder = ConstrainedDecoder()
        stream = (
            "<thought>Fixing timeout bug in checkout</thought>\n"
            "```diff\n"
            "--- a/checkout.py\n"
            "+++ b/checkout.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def checkout():\n"
            "-    return False\n"
            "+    return True\n"
            "```"
        )
        patch = decoder.project_patch(stream)

        assert patch.startswith("--- a/checkout.py\n+++ b/checkout.py\n")
        assert "-    return False" in patch
        assert "+    return True" in patch
        assert "@@ -1,2 +1,2 @@" in patch

    def test_project_patch_from_before_after_blocks(self):
        decoder = ConstrainedDecoder()
        stream = (
            "<thought>Propose replacement for login logic</thought>\n"
            "Before:\n"
            "```python\n"
            "def login(user):\n"
            "    return False\n"
            "```\n"
            "After:\n"
            "```python\n"
            "def login(user):\n"
            "    return True\n"
            "```"
        )
        patch = decoder.project_patch(stream, target_file="services/auth.py")

        assert "--- a/services/auth.py" in patch
        assert "+++ b/services/auth.py" in patch
        assert "-    return False" in patch
        assert "+    return True" in patch
        assert any("Synthesized unified diff" in r for r in decoder.last_repaired_errors)

    def test_project_ast_from_python_code(self):
        decoder = ConstrainedDecoder()
        stream = (
            "<thought>Let us define an exponential backoff helper</thought>\n"
            "```python\n"
            "def compute_backoff(attempt: int, base_delay: float = 1.0) -> float:\n"
            "    return base_delay * (2 ** attempt)\n"
            "```"
        )
        tree = decoder.project_ast(stream)

        assert isinstance(tree, ast.Module)
        assert len(tree.body) == 1
        func = tree.body[0]
        assert isinstance(func, ast.FunctionDef)
        assert func.name == "compute_backoff"
        assert len(func.args.args) == 2

    def test_extract_thought_stream_scratchpad_markdown(self):
        decoder = ConstrainedDecoder()
        stream = (
            "## Scratchpad\n"
            "We are investigating token bucket saturation.\n"
            "---\n"
            '{"algorithm": "token_bucket", "capacity": 100, "refill_rate": 10}'
        )
        result = decoder.project_json(stream)

        assert result["algorithm"] == "token_bucket"
        assert result["capacity"] == 100
        assert "token bucket saturation" in decoder.last_extracted_thought


class TestConstrainedDecodingNegative:
    """Malformed inputs, unparseable thoughts, and invalid schemas handled gracefully."""

    def test_project_json_unparseable_text_raises_value_error(self):
        decoder = ConstrainedDecoder()
        unparseable = "The weather today in Tokyo is sunny with light breeze and no JSON anywhere."

        with pytest.raises(ValueError) as exc_info:
            decoder.project_json(unparseable)
        assert "Failed to project valid JSON" in str(exc_info.value) or "No valid JSON" in str(exc_info.value)

    def test_project_patch_no_diff_indicators_raises_value_error(self):
        decoder = ConstrainedDecoder()
        text_without_patch = "No diff blocks, no hunk headers, and no Before/After tags here."

        with pytest.raises(ValueError) as exc_info:
            decoder.project_patch(text_without_patch)
        assert "No valid patch" in str(exc_info.value)

    def test_project_ast_invalid_python_raises_value_error(self):
        decoder = ConstrainedDecoder()
        invalid_code = "def 12345 invalid syntax @#$%^"

        with pytest.raises(ValueError) as exc_info:
            decoder.project_ast(invalid_code)
        assert "Unable to project text into valid AST" in str(exc_info.value)

    def test_project_json_invalid_schema_type_raises_value_error(self):
        decoder = ConstrainedDecoder()
        with pytest.raises(ValueError) as exc_info:
            decoder.project_json('{"key": "val"}', schema=["invalid_schema_format"])
        assert "Schema must be a dictionary object" in str(exc_info.value)

    def test_project_json_schema_type_mismatch_raises_value_error(self):
        decoder = ConstrainedDecoder()
        schema = {"type": "object", "properties": {"a": {"type": "string"}}}
        with pytest.raises(ValueError) as exc_info:
            decoder.project_json("[1, 2, 3]", schema=schema)
        assert "Schema violation: expected object" in str(exc_info.value)

    def test_cli_missing_input_file_gracefully_handled(self):
        result = subprocess.run(
            [sys.executable, "tools/reasoning/constrained_decoding.py", "--input", "nonexistent_file_xyz123.log", "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["status"] == "error"
        assert "not found" in data["error"].lower()

    def test_cli_missing_schema_file_gracefully_handled(self):
        result = subprocess.run(
            [
                sys.executable,
                "tools/reasoning/constrained_decoding.py",
                "--text",
                '{"a": 1}',
                "--schema",
                "nonexistent_schema_xyz123.json",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["status"] == "error"
        assert "schema file not found" in data["error"].lower()


class TestConstrainedDecodingBoundary:
    """Empty strings, unicode, whitespace-only, deeply nested structures, giant thoughts."""

    def test_empty_and_whitespace_input(self):
        decoder = ConstrainedDecoder()
        for empty_val in ("", "   ", "\n\t\n  "):
            with pytest.raises(ValueError) as exc_info:
                decoder.project_json(empty_val)
            assert "empty or whitespace-only" in str(exc_info.value)

            with pytest.raises(ValueError) as exc_patch:
                decoder.project_patch(empty_val)
            assert "empty or whitespace-only" in str(exc_patch.value)

            with pytest.raises(ValueError) as exc_ast:
                decoder.project_ast(empty_val)
            assert "empty or whitespace-only" in str(exc_ast.value)

    def test_unicode_and_vietnamese_characters(self):
        decoder = ConstrainedDecoder()
        stream = (
            "<thought>Kiểm thử tải với ký tự Tiếng Việt và biểu tượng cảm xúc 🚀</thought>\n"
            '{"tiêu_đề": "Báo cáo thử nghiệm hệ thống", "trạng_thái": "HOÀN_TẤT", "tỷ_lệ_đạt": "100%", "ký_hiệu": "α + β = γ"}'
        )
        result = decoder.project_json(stream)

        assert result["tiêu_đề"] == "Báo cáo thử nghiệm hệ thống"
        assert result["trạng_thái"] == "HOÀN_TẤT"
        assert result["tỷ_lệ_đạt"] == "100%"
        assert result["ký_hiệu"] == "α + β = γ"
        assert "Kiểm thử tải với ký tự Tiếng Việt" in decoder.last_extracted_thought

    def test_deeply_nested_structures_with_pushdown_unmatched_braces(self):
        decoder = ConstrainedDecoder()
        # 8 levels deep with unclosed braces at end of file
        unclosed_nested = (
            '{"level_1": {"level_2": {"level_3": {"level_4": {"level_5": '
            '{"level_6": {"level_7": {"level_8": {"target_value": 42'
        )
        result = decoder.project_json(unclosed_nested)

        curr = result
        for i in range(1, 9):
            curr = curr[f"level_{i}"]
        assert curr["target_value"] == 42
        assert any("Closed unmatched opening braces" in r for r in decoder.last_repaired_errors)

    def test_giant_thought_stream(self):
        decoder = ConstrainedDecoder()
        long_reasoning = "\n".join([f"Step {i}: validating invariant condition {i*2} under load." for i in range(500)])
        stream = f"<thought>\n{long_reasoning}\n</thought>\n" + '{"batch_size": 500, "verified": true}'

        assert len(stream) > 15000
        result = decoder.project_json(stream)
        assert result["batch_size"] == 500
        assert result["verified"] is True
        assert len(decoder.last_extracted_thought) > 10000

    def test_unclosed_string_literal_before_newline_repair(self):
        decoder = ConstrainedDecoder()
        # Unterminated string before newline
        broken = '{\n  "title": "Unclosed string literal\n, "count": 10\n}'
        result = decoder.project_json(broken)

        assert "Unclosed string literal" in result["title"]
        assert result["count"] == 10
        assert any("Repaired unterminated string" in r for r in decoder.last_repaired_errors)

    def test_missing_commas_between_elements(self):
        decoder = ConstrainedDecoder()
        broken = '{\n  "a": 100\n  "b": 200\n  "c": 300\n}'
        result = decoder.project_json(broken)

        assert result["a"] == 100
        assert result["b"] == 200
        assert result["c"] == 300
        assert any("Inserted missing comma" in r for r in decoder.last_repaired_errors)


class TestConstrainedDecodingCLIFlags:
    """CLI argument parsing and execution with various flags."""

    def test_cli_json_mode_with_text_and_json_flag(self):
        cmd = [
            sys.executable,
            "tools/reasoning/constrained_decoding.py",
            "--text",
            '<thought>Reasoning</thought> {"status": "ok", "retries": 3,}',
            "--mode",
            "json",
            "--json",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["status"] == "ok"
        assert data["mode"] == "json"
        assert data["projected_output"] == {"status": "ok", "retries": 3}
        assert isinstance(data["syntax_errors_repaired"], list)
        assert len(data["syntax_errors_repaired"]) >= 1

    def test_cli_input_file_flag(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tf:
            tf.write('<thought>Checking file input</thought>\n{"source": "temp_file", "id": 77}')
            tf_path = tf.name

        try:
            cmd = [
                sys.executable,
                "tools/reasoning/constrained_decoding.py",
                "--input",
                tf_path,
                "--mode",
                "json",
                "--json",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data["projected_output"]["source"] == "temp_file"
            assert data["projected_output"]["id"] == 77
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_cli_schema_flag(self):
        schema_dict = {
            "type": "object",
            "required": ["version", "env"],
            "properties": {"version": {"type": "integer"}, "env": {"type": "string"}},
        }
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as sf:
            json.dump(schema_dict, sf)
            sf_path = sf.name

        try:
            cmd = [
                sys.executable,
                "tools/reasoning/constrained_decoding.py",
                "--text",
                '{"version": "4", "env": "staging"}',
                "--schema",
                sf_path,
                "--json",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data["projected_output"]["version"] == 4
            assert isinstance(data["projected_output"]["version"], int)
            assert data["projected_output"]["env"] == "staging"
        finally:
            if os.path.exists(sf_path):
                os.remove(sf_path)

    def test_cli_mode_patch(self):
        diff_payload = "```diff\n--- a/module.py\n+++ b/module.py\n@@ -1,1 +1,1 @@\n-old_val\n+new_val\n```"
        cmd = [
            sys.executable,
            "tools/reasoning/constrained_decoding.py",
            "--text",
            diff_payload,
            "--mode",
            "patch",
            "--json",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["mode"] == "patch"
        assert "--- a/module.py" in data["projected_output"]
        assert "+new_val" in data["projected_output"]

    def test_cli_mode_ast(self):
        cmd = [
            sys.executable,
            "tools/reasoning/constrained_decoding.py",
            "--text",
            "x: int = 42\ny = x * 2",
            "--mode",
            "ast",
            "--json",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["mode"] == "ast"
        assert "Module(" in data["projected_output"]
        assert "AnnAssign(" in data["projected_output"]

    def test_cli_output_file_flag(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as out_f:
            out_path = out_f.name

        try:
            cmd = [
                sys.executable,
                "tools/reasoning/constrained_decoding.py",
                "--text",
                '{"export": "disk_test"}',
                "--output",
                out_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            assert result.returncode == 0
            with open(out_path, "r", encoding="utf-8") as f:
                content = json.load(f)
            assert content["export"] == "disk_test"
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)


class TestConstrainedDecodingRemediation:
    """Regression test suite for Iteration 2 Challenger-identified boundary defects."""

    def test_english_contractions_in_json_strings(self):
        decoder = ConstrainedDecoder()
        text = '{"msg": "User\'s items aren\'t available", "summary": "Don\'t stop", "reason": "It\'s important"}'
        result = decoder.project_json(text)

        assert isinstance(result, dict)
        assert result["msg"] == "User's items aren't available"
        assert result["summary"] == "Don't stop"
        assert result["reason"] == "It's important"

    def test_query_braces_in_json_strings(self):
        decoder = ConstrainedDecoder()
        text = '{"query": "SELECT * WHERE {foo: 1}", "filter": "{id: 123}"}'
        result = decoder.project_json(text)

        assert isinstance(result, dict)
        assert result["query"] == "SELECT * WHERE {foo: 1}"
        assert result["filter"] == "{id: 123}"

    def test_trailing_commas_inside_string_literals(self):
        decoder = ConstrainedDecoder()
        # The comma inside "items: ,}" must be preserved, while the outer trailing comma after "other": 1, must be removed.
        text = '{"pattern": "items: ,}", "other": 1,}'
        result = decoder.project_json(text)

        assert isinstance(result, dict)
        assert result["pattern"] == "items: ,}"
        assert result["other"] == 1

    def test_c_style_block_comments_in_json(self):
        decoder = ConstrainedDecoder()
        text = (
            "{\n"
            "  /* server configuration */\n"
            '  "port": 8080,\n'
            "  /* database configuration */\n"
            '  "host": "localhost"\n'
            "}"
        )
        result = decoder.project_json(text)

        assert isinstance(result, dict)
        assert result["port"] == 8080
        assert result["host"] == "localhost"
        assert any("comment" in r.lower() for r in decoder.last_repaired_errors)

    def test_multi_file_unified_diffs(self):
        decoder = ConstrainedDecoder()
        multi_diff = (
            "--- a/file1.py\n"
            "+++ b/file1.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-val1 = 1\n"
            "+val1 = 2\n"
            "--- a/file2.py\n"
            "+++ b/file2.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-val2 = 3\n"
            "+val2 = 4\n"
        )
        patch = decoder.project_patch(multi_diff)

        assert "--- a/file1.py" in patch
        assert "+++ b/file1.py" in patch
        assert "--- a/file2.py" in patch
        assert "+++ b/file2.py" in patch
        # Verify subsequent header was not swallowed into File 1's hunk (which would inflate line counts)
        assert "@@ -1,2 +1,2 @@" not in patch
        assert "@@ -1,3 +1,3 @@" not in patch
        assert patch.count("@@ -1,1 +1,1 @@") == 2

    def test_unfenced_raw_diff_hunks_without_headers(self):
        decoder = ConstrainedDecoder()
        raw_hunk = "@@ -1,2 +1,2 @@\n-old_logic()\n+new_logic()\n"
        patch = decoder.project_patch(raw_hunk, target_file="services/payment.py")

        assert "--- a/services/payment.py" in patch
        assert "+++ b/services/payment.py" in patch
        assert "-old_logic()" in patch
        assert "+new_logic()" in patch
        assert "@@ -1,1 +1,1 @@" in patch

    def test_ast_interleaved_delimiters_lifo_stack(self):
        decoder = ConstrainedDecoder()
        # Delimiters opened in order: ( [ ( -> must be closed in reverse order: ) ] )
        tree = decoder.project_ast("x = ([(")
        assert isinstance(tree, ast.Module)
        assert len(tree.body) == 1
        assign = tree.body[0]
        assert isinstance(assign, ast.Assign)
        assert isinstance(assign.value, ast.List)

        # Complex interleaved delimiters with dict and tuple: { [ (
        tree2 = decoder.project_ast('data = {"items": [(1, 2')
        assert isinstance(tree2, ast.Module)
        assert len(tree2.body) == 1

    def test_direct_json_parsing_fast_path(self):
        decoder = ConstrainedDecoder()
        valid_json = '{"system": "ready", "code": 200, "verified": true}'
        result = decoder.project_json(valid_json)

        assert result["system"] == "ready"
        assert result["code"] == 200
        assert result["verified"] is True
        # Fast path directly parsed valid JSON without applying repair heuristics
        assert len(decoder.last_repaired_errors) == 0

    def test_strip_comments_exact_escaped_quotes_and_repaired_flag(self):
        from tools.reasoning.constrained_decoding import JsonGrammarFSM

        # 1. Clean string without comments: repaired must be False
        text_clean = '{"key": "value"}'
        res, repaired = JsonGrammarFSM.strip_comments(text_clean)
        assert res == text_clean
        assert repaired is False

        # 2. String containing // comment: repaired must be True
        text_line_comment = '{"key": "value"} // trailing comment'
        res, repaired = JsonGrammarFSM.strip_comments(text_line_comment)
        assert res.strip() == '{"key": "value"}'
        assert repaired is True

        # 3. String containing /* block */ comment: repaired must be True
        text_block = '{"key": /* inline comment */ "value"}'
        res, repaired = JsonGrammarFSM.strip_comments(text_block)
        assert res.strip() == '{"key":  "value"}'
        assert repaired is True

        # 4. Escaped quotes inside double-quoted string: comments inside must NOT be stripped
        text_escaped_double = '{"msg": "escaped \\" // not a comment \\" end"}'
        res, repaired = JsonGrammarFSM.strip_comments(text_escaped_double)
        assert res == text_escaped_double
        assert repaired is False

        # 5. Escaped backslash before quote inside double-quoted string: comment after must be stripped
        text_backslash_double = '{"msg": "literal backslash \\\\" } // real comment'
        res, repaired = JsonGrammarFSM.strip_comments(text_backslash_double)
        assert res.strip() == '{"msg": "literal backslash \\\\" }'
        assert repaired is True

        # 6. Escaped quotes inside single-quoted string: comments inside must NOT be stripped
        text_escaped_single = "{\'msg\': \'escaped \\\' // not a comment \\\' end\'}"
        res, repaired = JsonGrammarFSM.strip_comments(text_escaped_single)
        assert res == text_escaped_single
        assert repaired is False

        # 7. Escaped backslash before quote inside single-quoted string
        text_backslash_single = "{\'msg\': \'literal backslash \\\\\' } // real comment"
        res, repaired = JsonGrammarFSM.strip_comments(text_backslash_single)
        assert res.strip() == "{\'msg\': \'literal backslash \\\\\' }"
        assert repaired is True

    def test_json_inside_thought_with_conversational_preamble_outside(self):
        decoder = ConstrainedDecoder()
        text = "Here is my thought: <thought>I should return {name: 'test', value: 42,}</thought>"
        res = decoder.project_json(text)
        assert isinstance(res, dict)
        assert res["name"] == "test"
        assert res["value"] == 42

    def test_diff_inside_thought_with_conversational_preamble_outside(self):
        decoder = ConstrainedDecoder()
        text = (
            "Here is my analysis:\n"
            "<thought>\n"
            "```diff\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-old\n"
            "+new\n"
            "```\n"
            "</thought>"
        )
        res = decoder.project_patch(text)
        assert "--- a/file.py" in res
        assert "+new" in res

    def test_ast_inside_thought_with_conversational_preamble_outside(self):
        decoder = ConstrainedDecoder()
        text = "Here is my reasoning: <thought>def calculate(x, y):\n    return x * y</thought>"
        tree = decoder.project_ast(text)
        assert isinstance(tree, ast.Module)
        assert isinstance(tree.body[0], ast.FunctionDef)
        assert tree.body[0].name == "calculate"
