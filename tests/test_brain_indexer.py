#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""Unit tests for tools/core/brain_indexer.py (4-Scenario Battery)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.core import brain_indexer
from tools.core.brain_indexer import BrainIndexReportDTO, build_brain_index


def test_build_brain_index_positive_with_wikilinks(tmp_path: Path) -> None:
    """Positive: indexes markdown vault and detects broken [[wikilinks]]."""
    brain_dir = tmp_path / "brain"
    (brain_dir / "principles").mkdir(parents=True)
    (brain_dir / "principles" / "boundary-discipline.md").write_text(
        "# Boundary Discipline\nSee [[index]] and [[missing-note]].\n",
        encoding="utf-8",
    )
    (brain_dir / "gotchas.md").write_text("# Gotchas\nSee [[boundary-discipline]].\n", encoding="utf-8")

    report = build_brain_index(str(brain_dir))
    assert isinstance(report, BrainIndexReportDTO)
    with pytest.raises(Exception):
        report.indexed_files = 99  # type: ignore[misc]
    assert report.indexed_files == 2
    assert (brain_dir / "index.md").is_file()
    index_text = (brain_dir / "index.md").read_text(encoding="utf-8")
    assert "[[principles/boundary-discipline]]" in index_text
    assert "[[gotchas]]" in index_text
    assert "missing-note" in report.broken_links


def test_negative_missing_brain_dir(tmp_path: Path) -> None:
    """Negative: raises FileNotFoundError when brain_dir does not exist."""
    with pytest.raises(FileNotFoundError):
        build_brain_index(str(tmp_path / "nonexistent_brain"))


def test_boundary_empty_dir_and_dry_run(tmp_path: Path) -> None:
    """Boundary: empty directory produces 0 indexed files; dry_run skips disk write."""
    empty_dir = tmp_path / "empty_brain"
    empty_dir.mkdir()
    report = build_brain_index(str(empty_dir), dry_run=True)
    assert report.indexed_files == 0
    assert report.broken_links == []
    assert not (empty_dir / "index.md").exists()


def test_cli_dry_run_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI: supports --dry-run --json flags and fails cleanly on missing --dir or nonexistent path."""
    brain_dir = tmp_path / "cli_brain"
    brain_dir.mkdir()
    (brain_dir / "note.md").write_text("# Note\nSee [[missing—ref]].\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["brain_indexer.py", "--dir", str(brain_dir), "--dry-run", "--json"])
    assert brain_indexer.main() == 0
    out = capsys.readouterr().out
    assert "missing—ref" in out
    payload = json.loads(out)
    assert payload["indexed_files"] == 1
    assert not (brain_dir / "index.md").exists()

    monkeypatch.setattr("sys.argv", ["brain_indexer.py"])
    with pytest.raises(SystemExit):
        brain_indexer.main()

    monkeypatch.setattr("sys.argv", ["brain_indexer.py", "--dir", str(tmp_path / "no_such_dir"), "--json"])
    assert brain_indexer.main() == 1
    err_out = capsys.readouterr().out
    assert "error" in json.loads(err_out)
