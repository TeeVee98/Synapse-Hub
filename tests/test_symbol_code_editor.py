# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-scenario verification suite for M2: Serena SymbolCodeEditor & 6 additive MCP tools."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools.context.symbol_code_editor import (
    NamePathMatcher,
    SymbolCodeEditor,
    SymbolEditReceiptDTO,
    SymbolMatchDTO,
)
from tools.mcp import mcp_server


SAMPLE_PY = '''"""Sample module for symbol editing tests."""


class AuthService:
    def login(self, user: str) -> bool:
        return bool(user)

    def logout(self, user: str) -> str:
        return f"bye:{user}"


def helper_login(user: str) -> bool:
    svc = AuthService()
    return svc.login(user)
'''


def test_symbol_edit_rollback_and_mcp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Positive + Negative + MCP scenario: overview, find, references, replace, insert, rename, rollback, traversal, MCP."""
    src_file = tmp_path / "sample_auth.py"
    src_file.write_text(SAMPLE_PY, encoding="utf-8")

    editor = SymbolCodeEditor(repo_root=str(tmp_path))

    # 1. Overview with depth=1 vs depth=2
    top_only = editor.get_symbols_overview("sample_auth.py", depth=1)
    assert [s.name_path for s in top_only] == ["AuthService", "helper_login"]
    full_overview = editor.get_symbols_overview("sample_auth.py", depth=2)
    assert [s.name_path for s in full_overview] == [
        "AuthService",
        "AuthService/login",
        "AuthService/logout",
        "helper_login",
    ]
    assert all(isinstance(s, SymbolMatchDTO) for s in full_overview)
    with pytest.raises(FrozenInstanceError):
        full_overview[0].name_path = "hacked"  # type: ignore[misc]

    # 2. NamePathMatcher exact, relative, and leading-slash matching
    assert NamePathMatcher("AuthService/login").matches("AuthService/login") is True
    assert NamePathMatcher("/AuthService/login").matches("AuthService/login") is True
    assert NamePathMatcher("login").matches("AuthService/login") is True
    assert NamePathMatcher("/login").matches("AuthService/login") is False
    assert NamePathMatcher("AuthService/missing").matches("AuthService/login") is False

    # 3. find_symbol with body
    found = editor.find_symbol("AuthService/login", file_path="sample_auth.py", include_body=True)
    assert len(found) == 1
    assert found[0].symbol_kind == "method"
    assert found[0].body is not None and "def login" in found[0].body

    # 4. find_referencing_symbols across file
    refs = editor.find_referencing_symbols("AuthService", file_path="sample_auth.py")
    assert len(refs) >= 1
    assert any(r["caller_symbol"] == "helper_login" for r in refs)

    # 5. Valid replace_symbol_body
    new_login = "    def login(self, user: str) -> bool:\n        return len(user.strip()) > 0"
    rec = editor.replace_symbol_body("sample_auth.py", "AuthService/login", new_login)
    assert isinstance(rec, SymbolEditReceiptDTO)
    assert rec.applied is True
    assert rec.syntax_valid is True
    assert rec.rolled_back is False
    assert "len(user.strip()) > 0" in src_file.read_text(encoding="utf-8")
    with pytest.raises(FrozenInstanceError):
        rec.applied = False  # type: ignore[misc]

    # 6. Syntax-breaking replace_symbol_body -> atomic rollback!
    before_broken = src_file.read_text(encoding="utf-8")
    broken_rec = editor.replace_symbol_body("sample_auth.py", "AuthService/login", "    def login(self:\n        pass")
    assert broken_rec.applied is False
    assert broken_rec.syntax_valid is False
    assert broken_rec.rolled_back is True
    assert broken_rec.error != ""
    assert src_file.read_text(encoding="utf-8") == before_broken

    # 7. insert_before_symbol, insert_after_symbol, and rename_symbol
    ins_b = editor.insert_before_symbol("sample_auth.py", "helper_login", "# Marker before helper")
    assert ins_b.applied is True and ins_b.syntax_valid is True
    ins_a = editor.insert_after_symbol("sample_auth.py", "helper_login", "\ndef post_helper() -> int:\n    return 42")
    assert ins_a.applied is True and ins_a.syntax_valid is True
    ren = editor.rename_symbol("sample_auth.py", "helper_login", "run_auth_helper")
    assert ren.applied is True and ren.syntax_valid is True
    updated_src = src_file.read_text(encoding="utf-8")
    assert "def run_auth_helper(" in updated_src
    assert "def helper_login(" not in updated_src

    # 8. Path traversal & symlink escape blocked
    with pytest.raises(ValueError, match="outside"):
        editor.get_symbols_overview("../../etc/passwd")

    outside_file = tmp_path.parent / "outside_escape_test.py"
    outside_file.write_text("x = 1\n", encoding="utf-8")
    escape_link = tmp_path / "escape_link.py"
    try:
        os.symlink(str(outside_file), str(escape_link))
        with pytest.raises(ValueError, match="outside"):
            editor.get_symbols_overview("escape_link.py")
    finally:
        if escape_link.is_symlink():
            escape_link.unlink()
        if outside_file.exists():
            outside_file.unlink()

    # 9. Verify 6 additive MCP tools via JSON-RPC process_message without breaking existing 24 tools
    monkeypatch.setenv("SYNAPSE_PROJECT_ROOT", str(tmp_path))
    tools_resp = mcp_server.process_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert tools_resp is not None
    tool_names = {t["name"] for t in tools_resp["result"]["tools"]}
    for expected in (
        "symbol_overview",
        "find_symbol",
        "find_referencing_symbols",
        "replace_symbol_body",
        "temporal_graph_add_episode",
        "temporal_graph_query",
        "synapse_lint",
        "verify_all_gates",
    ):
        assert expected in tool_names

    ov_resp = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "symbol_overview",
                "arguments": {"repo_path": str(tmp_path), "file_path": str(src_file), "depth": 2},
            },
        }
    )
    assert ov_resp is not None and ov_resp["result"]["isError"] is False
    ov_data = json.loads(ov_resp["result"]["content"][0]["text"])
    assert any(s["name_path"] == "AuthService/logout" for s in ov_data["symbols"])

    # Temporal graph MCP round-trip
    tg_db = str(tmp_path / "mcp_tg.db")
    add_resp = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "temporal_graph_add_episode",
                "arguments": {
                    "db_path": tg_db,
                    "source": "mcp_test",
                    "content": "svc uses db_v2",
                    "reference_time": "2026-07-01T00:00:00Z",
                    "facts": [["svc", "uses", "db_v2", "Service uses db_v2"]],
                },
            },
        }
    )
    assert add_resp is not None and add_resp["result"]["isError"] is False

    q_resp = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "temporal_graph_query",
                "arguments": {
                    "db_path": tg_db,
                    "query": "svc",
                    "as_of": "2026-07-02T00:00:00Z",
                    "mode": "hybrid",
                },
            },
        }
    )
    assert q_resp is not None and q_resp["result"]["isError"] is False
    q_data = json.loads(q_resp["result"]["content"][0]["text"])
    assert len(q_data["edges"]) == 1 and q_data["edges"][0]["target_id"] == "db_v2"


def test_symbol_editor_negative_and_boundary(tmp_path: Path) -> None:
    """Negative & Boundary scenarios: empty file, empty pattern, missing file/symbol, invalid rename identifier."""
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("", encoding="utf-8")
    editor = SymbolCodeEditor(repo_root=str(tmp_path))

    assert editor.get_symbols_overview("empty.py") == []
    assert editor.find_symbol("Missing", file_path="empty.py") == []

    with pytest.raises(ValueError, match="non-empty"):
        NamePathMatcher("   ")
    assert NamePathMatcher("AuthService/login").matches("") is False
    assert NamePathMatcher("AuthService/login").matches("///") is False

    with pytest.raises(ValueError, match="repo_root"):
        SymbolCodeEditor("   ")

    with pytest.raises(ValueError, match="file_path"):
        editor.get_symbols_overview("   ")

    nested_fn = tmp_path / "nested_fn.py"
    nested_fn.write_text("def outer():\n    def inner():\n        return 1\n    return inner()\n", encoding="utf-8")
    assert [s.name_path for s in editor.get_symbols_overview("nested_fn.py", depth=2)] == ["outer"]

    with pytest.raises(FileNotFoundError):
        editor.get_symbols_overview("does_not_exist.py")

    sample = tmp_path / "mod.py"
    sample.write_text("def alpha():\n    return 1\n", encoding="utf-8")

    missing_rec = editor.replace_symbol_body("mod.py", "nonexistent", "def nonexistent():\n    return 0")
    assert missing_rec.applied is False
    assert "not found" in missing_rec.error.lower()

    bad_ident = editor.rename_symbol("mod.py", "alpha", "123-invalid")
    assert bad_ident.applied is False
    assert "identifier" in bad_ident.error.lower()


def test_symbol_editor_cli_json_contract(tmp_path: Path) -> None:
    """CLI scenario: overview and find-symbol via --json."""
    src = tmp_path / "cli_mod.py"
    src.write_text("class Box:\n    def size(self) -> int:\n        return 3\n", encoding="utf-8")
    worktree_root = Path(__file__).resolve().parents[1]
    script = str(worktree_root / "tools" / "context" / "symbol_code_editor.py")

    r = subprocess.run(
        [
            sys.executable,
            script,
            "--repo-root",
            str(tmp_path),
            "overview",
            "--file",
            "cli_mod.py",
            "--depth",
            "2",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["status"] == "ok"
    assert [s["name_path"] for s in data["symbols"]] == ["Box", "Box/size"]
