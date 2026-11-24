# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Unit & Integration Tests for Append-Only Decision Ledger & Fast Search Engine."""

import json
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch

import pytest

from tools.core.decision_ledger import (
    DecisionQueryResultDTO,
    DecisionRecordDTO,
    _search_with_ripgrep,
    append_decision,
    export_obsidian_markdown,
    main as ledger_main,
    query_decisions,
    resolve_ledger_file,
)
from tools.core.project_state import init_state, read_state_json, record_decision


@pytest.fixture
def temp_workspace():
    """Provides an isolated clean temporary workspace directory."""
    temp_dir = tempfile.mkdtemp(prefix="synapse_ledger_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_dto_immutability():
    """Kills M1 & M2: Verifies frozen dataclass immutability contracts."""
    rec = DecisionRecordDTO(
        id="dec-test",
        timestamp="2026-11-24 10:00:00",
        decision="Test decision",
    )
    with pytest.raises(FrozenInstanceError):
        rec.id = "mutated-id"  # type: ignore

    res = DecisionQueryResultDTO(total=1, matches=[])
    with pytest.raises(FrozenInstanceError):
        res.total = 2  # type: ignore


def test_append_decision_positive_and_utf8(temp_workspace):
    """TC-01 & Kills M5: Verifies positive append, file locking, and UTF-8 non-ASCII preservation."""
    record = DecisionRecordDTO(
        id="dec-test-01",
        timestamp="2026-11-24 10:30:00",
        decision="Quyết định kiến trúc của Thế Vị (@TeeVee98)",
        why="VIF score exceeded threshold 10.0",
        cost_if_wrong="Model underfitting risk",
        scope="statistical_model",
        author="agent_researcher",
        evidence="run_log_#42",
        tags=["regression", "vif"],
    )

    saved = append_decision(temp_workspace, record)
    assert saved["id"] == "dec-test-01"
    assert "Ruling: Quyết định kiến trúc" in saved["ruling"]

    ledger_path = resolve_ledger_file(temp_workspace)
    assert os.path.isfile(ledger_path)

    with open(ledger_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Verifies ensure_ascii=False: Vietnamese characters must not be escaped to unicode entities
    assert "Quyết định kiến trúc của Thế Vị" in raw_text
    assert "\\u" not in raw_text

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["id"] == "dec-test-01"
    assert stored["scope"] == "statistical_model"
    assert stored["tags"] == ["regression", "vif"]


def test_query_decisions_keyword_and_limit(temp_workspace):
    """TC-02 & Kills M7: Verifies keyword query retrieval and limit bounding."""
    for i in range(5):
        append_decision(
            temp_workspace,
            {
                "id": f"dec-{i}",
                "decision": f"Decision {i} regarding regression optimization",
                "why": "p-value threshold exceeded",
                "cost_if_wrong": "Risk of regression drift",
            },
        )

    # Test limit strictly caps results
    res_limited = query_decisions(temp_workspace, query="regression", limit=2, use_fast_search=False)
    assert res_limited.total == 2
    assert len(res_limited.matches) == 2
    assert res_limited.matches[0]["id"] == "dec-4"
    assert res_limited.matches[1]["id"] == "dec-3"
    assert res_limited.execution_time_ms >= 0.0


def test_query_decisions_scope_and_tag(temp_workspace):
    """TC-03: Tests filtering by scope and specific tags."""
    append_decision(
        temp_workspace,
        {
            "id": "dec-a",
            "decision": "Use Playwright over Selenium",
            "scope": "web_automation",
            "tags": ["e2e", "browser"],
        },
    )
    append_decision(
        temp_workspace,
        {
            "id": "dec-b",
            "decision": "Use k6 for load testing",
            "scope": "performance",
            "tags": ["load", "k6"],
        },
    )

    res_scope = query_decisions(temp_workspace, scope="performance")
    assert res_scope.total == 1
    assert res_scope.matches[0]["id"] == "dec-b"

    res_tag = query_decisions(temp_workspace, tag="browser")
    assert res_tag.total == 1
    assert res_tag.matches[0]["id"] == "dec-a"


def test_fast_search_ripgrep_and_fallbacks(temp_workspace):
    """Kills M8, M11, M12, M13, M14: Exhaustive fast search branching and fallbacks."""
    ledger_path = resolve_ledger_file(temp_workspace)

    # M8: _search_with_ripgrep returns None if file missing
    with patch("shutil.which", return_value="/usr/local/bin/rg"):
        assert _search_with_ripgrep("/non/existent/path.jsonl", "query") is None

    # M8: _search_with_ripgrep returns None if rg is missing even if file exists
    append_decision(temp_workspace, {"id": "dec-test", "decision": "Sample"})
    with patch("shutil.which", return_value=None):
        assert _search_with_ripgrep(ledger_path, "query") is None

    # Append decisions
    for i in range(3):
        append_decision(
            temp_workspace,
            {
                "id": f"dec-rg-{i}",
                "decision": f"Optimization item {i} with ripgrep target",
                "scope": "optimization",
                "tags": ["fast"],
            },
        )

    # M13: Scope filter forces stream engine even if fast_search=True
    res_scoped = query_decisions(temp_workspace, query="ripgrep target", scope="optimization")
    assert res_scoped.engine == "stream"
    assert res_scoped.total == 3

    # M14: Tag filter forces stream engine even if fast_search=True
    res_tagged = query_decisions(temp_workspace, query="ripgrep target", tag="fast")
    assert res_tagged.engine == "stream"
    assert res_tagged.total == 3

    # Fast search explicitly disabled forces stream
    res_disabled = query_decisions(temp_workspace, query="ripgrep target", use_fast_search=False)
    assert res_disabled.engine == "stream"


def test_ripgrep_mocked_execution(temp_workspace):
    """Kills M9, M10, M11, M12, M15, M16: Verifies ripgrep execution and limit bounding via mock."""
    ledger_path = resolve_ledger_file(temp_workspace)
    append_decision(temp_workspace, {"id": "dec-1", "decision": "Alpha target 1"})
    append_decision(temp_workspace, {"id": "dec-2", "decision": "Alpha target 2"})

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = '{"id": "dec-1", "decision": "Alpha target 1"}\n{"id": "dec-2", "decision": "Alpha target 2"}\n'

    with patch("shutil.which", return_value="/usr/local/bin/rg"):
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            # 1. Direct ripgrep search with limit=1 (Kills M10: len(matches) >= limit)
            res_rg = _search_with_ripgrep(ledger_path, "Alpha target", limit=1)
            assert res_rg is not None
            assert len(res_rg) == 1
            assert res_rg[0]["id"] == "dec-2"  # reversed (newest first)
            # Kills M9: text=True check
            assert mock_run.call_args[1].get("text") is True

            # 2. Query decisions using ripgrep engine (Kills M11, M12, M15)
            res_query = query_decisions(temp_workspace, query="Alpha target", limit=2)
            assert res_query.engine == "ripgrep"
            assert res_query.total == 2
            assert res_query.matches[0]["id"] == "dec-2"
            assert res_query.matches[1]["id"] == "dec-1"

            # 3. Ripgrep failure code fallback to stream
            mock_proc_fail = MagicMock()
            mock_proc_fail.returncode = 2  # syntax error in rg
            mock_proc_fail.stdout = ""
            mock_run.return_value = mock_proc_fail
            res_fallback = query_decisions(temp_workspace, query="Alpha target")
            assert res_fallback.engine == "stream"
            assert res_fallback.total == 2


def test_boundary_empty_and_missing_ledger(temp_workspace):
    """TC-04: Boundary conditions: empty ledger, non-existent file, and blank queries."""
    res_none = query_decisions(temp_workspace, query="test")
    assert res_none.total == 0
    assert res_none.matches == []

    ledger_path = resolve_ledger_file(temp_workspace)
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write("\n")

    res_empty = query_decisions(temp_workspace, query="test")
    assert res_empty.total == 0
    assert res_empty.matches == []

    append_decision(temp_workspace, {"decision": "Sample decision"})
    res_all = query_decisions(temp_workspace, query="")
    assert res_all.total == 1


def test_concurrent_append_thread_safety(temp_workspace):
    """TC-05: Concurrency test verifying file locks prevent line interleave under parallel writes."""
    num_threads = 8
    num_writes_per_thread = 5

    def worker(worker_id):
        for j in range(num_writes_per_thread):
            append_decision(
                temp_workspace,
                {
                    "id": f"dec-w{worker_id}-{j}",
                    "decision": f"Worker {worker_id} decision {j}",
                    "why": f"Concurrent test workload {j}",
                },
            )

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        for f in futures:
            f.result()

    ledger_path = resolve_ledger_file(temp_workspace)
    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    assert len(lines) == num_threads * num_writes_per_thread
    for ln in lines:
        data = json.loads(ln)
        assert "id" in data
        assert "decision" in data


def test_export_obsidian_markdown(temp_workspace):
    """TC-06: Verifies Obsidian markdown export format, frontmatter, and wikilinks."""
    append_decision(
        temp_workspace,
        {
            "id": "dec-obsidian-01",
            "decision": "Adopt Clean POM over raw locators",
            "why": "Eliminate selector duplication across test scripts",
            "cost_if_wrong": "Maintenance overhead",
            "scope": "architecture",
            "tags": ["pom", "playwright"],
        },
    )

    out_file = export_obsidian_markdown(temp_workspace)
    assert os.path.isfile(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    assert "type: decision-log" in md_text
    assert "project: Synapse-Hub" in md_text
    assert "[[PROJECT_STATE]]" in md_text
    assert "[[docs/INVARIANTS]]" in md_text
    assert "> [!NOTE] Adopt Clean POM over raw locators" in md_text
    assert "#pom #playwright" in md_text


def test_project_state_dual_write_integration(temp_workspace):
    """TC-07: Integration test: record_decision updates rolling state and persistent ledger."""
    init_state(temp_workspace)

    for i in range(1, 6):
        record_decision(
            temp_workspace,
            decision=f"Decision {i}",
            why=f"Reason {i}",
            cost_if_wrong=f"Risk {i}",
            scope="qa",
            tags=[f"tag-{i}"],
        )

    state_json = read_state_json(temp_workspace)
    assert state_json is not None
    assert len(state_json.get("decisions", [])) == 3
    assert state_json["decisions"][-1]["decision"] == "Decision 5"
    assert state_json["decisions"][0]["decision"] == "Decision 3"

    ledger_path = resolve_ledger_file(temp_workspace)
    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    assert len(lines) == 5

    query_res = query_decisions(temp_workspace, query="Decision 1")
    assert query_res.total == 1
    assert query_res.matches[0]["decision"] == "Decision 1"


def test_cli_battery_and_gate_verification(temp_workspace, capsys, monkeypatch):
    """TC-08 & Kills M18, M19, M20: 4-Scenario CLI battery including corrupt gate failure."""
    # Scenario 1: CLI log with --json and UTF-8 characters (Kills MUT-0018)
    argv_log = [
        "tools/core/decision_ledger.py",
        "--dir", temp_workspace,
        "--log",
        "--decision", "Quyết định CLI của Thế Vị",
        "--why", "CLI test justification",
        "--cost", "CLI test risk",
        "--tag", "cli",
        "--json",
    ]
    monkeypatch.setattr("sys.argv", argv_log)
    rc = ledger_main()
    assert rc == 0
    captured = capsys.readouterr()
    log_data = json.loads(captured.out)
    assert log_data["decision"] == "Quyết định CLI của Thế Vị"
    assert "Quyết định CLI của Thế Vị" in captured.out
    assert "\\u" not in captured.out

    # Scenario 2: CLI query with --json
    argv_query = [
        "tools/core/decision_ledger.py",
        "--dir", temp_workspace,
        "--query", "Quyết định CLI",
        "--json",
    ]
    monkeypatch.setattr("sys.argv", argv_query)
    rc = ledger_main()
    assert rc == 0
    captured = capsys.readouterr()
    query_data = json.loads(captured.out)
    assert query_data["total"] == 1

    # Scenario 3: CLI export-obsidian
    argv_export = [
        "tools/core/decision_ledger.py",
        "--dir", temp_workspace,
        "--export-obsidian",
        "--json",
    ]
    monkeypatch.setattr("sys.argv", argv_export)
    rc = ledger_main()
    assert rc == 0
    captured = capsys.readouterr()
    export_data = json.loads(captured.out)
    assert export_data["status"] == "SUCCESS"

    # Scenario 4: CLI gate check PASS on clean ledger (Kills M19)
    argv_gate = [
        "tools/core/decision_ledger.py",
        "--dir", temp_workspace,
        "--gate",
        "--json",
    ]
    monkeypatch.setattr("sys.argv", argv_gate)
    rc_pass = ledger_main()
    assert rc_pass == 0
    captured = capsys.readouterr()
    gate_data = json.loads(captured.out)
    assert gate_data["status"] == "PASS"
    assert gate_data["decisions_count"] == 1

    # Scenario 5: CLI gate check FAIL on corrupted ledger line (Kills M18 & M20)
    ledger_path = resolve_ledger_file(temp_workspace)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write("{corrupt json line\n")

    monkeypatch.setattr("sys.argv", argv_gate)
    rc_fail = ledger_main()
    assert rc_fail == 1
    captured_fail = capsys.readouterr()
    gate_fail_data = json.loads(captured_fail.out)
    assert gate_fail_data["status"] == "FAIL"
    assert gate_fail_data["corrupted_lines"] == 1
