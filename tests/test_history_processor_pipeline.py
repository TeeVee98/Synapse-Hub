# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Verify offline history compression and the additive submit review."""

import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.orchestration.swe_qa_aci import SweQaAci


MODULE = "tools.context.history_processor_pipeline"
TEST_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pipeline():
    """Locate the product module without turning a missing feature into a collection error."""
    assert importlib.util.find_spec(MODULE) is not None, "History compression module is unavailable"
    return importlib.import_module(MODULE)


def test_history_compression_and_submit_review(pipeline, tmp_path):
    """Positive compression preserves the active window, task, and recent traceback."""
    history = [
        {"role": "system", "content": "Keep DEBUG: task exactly"},
        {"role": "tool", "content": "old A\n" * 20, "file": "src/a.py", "kind": "window"},
        {"role": "tool", "content": "old B\n" * 20, "file": "src/b.py", "kind": "window"},
        {"role": "assistant", "content": "Inspect new windows"},
        {"role": "tool", "content": "long output\n" * 30},
        {"role": "tool", "content": "DEBUG: chatter\n\x1b[31mUseful\x1b[0m", "file": "src/a.py", "kind": "edit"},
        {"role": "assistant", "content": "Compare the two files"},
        {"role": "tool", "content": "latest B", "file": "src/b.py", "kind": "window"},
        {"role": "tool", "content": "Traceback: active error"},
        {"role": "assistant", "content": "Review the proposed patch"},
    ]
    aci = SweQaAci(repo_root=str(tmp_path))
    processed, receipt = aci.compress_history(history, keep_last=2, cache_breakpoints=2)
    assert receipt.original_turns == receipt.processed_turns == 10
    assert receipt.closed_windows_elided == 2
    assert receipt.elided_observations == 2
    assert receipt.cache_breakpoints_placed == 2
    assert 0 < receipt.estimated_tokens_after < receipt.estimated_tokens_before
    assert processed[0] == history[0]
    assert processed[9] == history[9]
    assert processed[1]["content"] == "Outdated file window: (20 lines omitted)"
    assert processed[2]["content"] == "Outdated file window: (20 lines omitted)"
    assert processed[4]["content"] == "Old environment output: (30 lines omitted)"
    assert processed[5]["content"] == "Old environment output: (1 lines omitted)"
    assert processed[7]["cache_control"] == processed[8]["cache_control"] == {"type": "ephemeral"}
    assert processed[8]["content"] == history[8]["content"]
    assert history[1]["content"] == "old A\n" * 20
    assert "cache_control" not in history[8]

    patch = {"src/b.py": "value = 5\n", "src/a.py": "value = (1 + 1)\n"}
    approved = aci.review_on_submit(patch, allowed_paths=["src/a.py", "src/b.py"])
    assert approved.approved and approved.syntax_valid and approved.clean_pom_valid
    assert approved.files_changed == ("src/a.py", "src/b.py")
    assert approved.blocking_reasons == ()
    assert not (tmp_path / "src").exists()


def test_negative_review_rejects_invalid_syntax_pom_scope_and_bom(tmp_path):
    aci = SweQaAci(repo_root=str(tmp_path))
    receipt = aci.review_on_submit({
        "bad.py": "def incomplete(:\n",
        "tests/test_ui.py": "selector = " + repr("x" + "path=" + "/" * 2 + "button"),
        "../out.py": "x = 1",
        "bom.py": "\ufeffx = 1",
        "bad.json": '{"foo":',
        "denied.py": "x = 2",
    }, allowed_paths=["bad.py", "tests/test_ui.py", "../out.py", "bom.py", "bad.json"])
    assert not receipt.approved
    assert not receipt.syntax_valid and not receipt.clean_pom_valid
    assert len(receipt.blocking_reasons) == 6
    assert all(any(label in reason for reason in receipt.blocking_reasons) for label in (
        "bad.py", "test_ui.py", "out.py", "bom.py", "bad.json", "denied.py",
    ))


def test_negative_review_rejects_symlink_escape_and_git_metadata(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "outside").symlink_to(tmp_path, target_is_directory=True)
    receipt = SweQaAci(repo_root=str(root)).review_on_submit({
        "outside/escape.py": "x = 1",
        ".git/config": "x = 2",
    })
    assert not receipt.approved
    assert len(receipt.blocking_reasons) == 2


def test_boundary_empty_single_turn_and_stale_breakpoints(pipeline, tmp_path):
    engine = pipeline.HistoryProcessorPipeline(keep_last=0, cache_breakpoints=0)
    assert engine.process([]) == ([], pipeline.HistoryCompressionReceiptDTO(0, 0, 0, 0, 0, 0, 0))
    system = {"role": "system", "content": "", "cache_control": {"type": "ephemeral"}}
    processed, receipt = engine.process([system])
    assert processed == [{"role": "system", "content": ""}]
    assert receipt.processed_turns == 1 and receipt.cache_breakpoints_placed == 0
    assert receipt.estimated_tokens_before == receipt.estimated_tokens_after == 0
    assert "cache_control" in system

    current = {"role": "tool", "content": "Traceback: keep it"}
    processed, receipt = engine.process([system, current])
    assert processed[-1] == current
    assert receipt.elided_observations == 0
    assert SweQaAci(repo_root=str(tmp_path)).review_on_submit({}).approved


@pytest.mark.parametrize("pattern", ["[", "^(a+)+$", r"^.*x$", "^x|y", "^x.*.*"])
def test_negative_noise_pattern_fails_explicitly(pipeline, pattern):
    with pytest.raises(ValueError, match="noise pattern"):
        pipeline.RegexNoiseFilterProcessor((pattern,))


def test_positive_noise_filter_bounds_lines_and_keeps_non_observations(pipeline):
    filtered = pipeline.RegexNoiseFilterProcessor((r"^TRACE: .*$",)).process([
        {"role": "system", "content": "TRACE: task"},
        {"role": "assistant", "content": "TRACE: explanation"},
        {"role": "tool", "content": "TRACE: discard\n\x1b[31mImportant\x1b[0m\nTRACE: " + "x" * 4097},
        {"role": "tool", "content": "TRACE: recent"},
    ], protected={0, 3})
    assert filtered[0]["content"] == "TRACE: task"
    assert filtered[1]["content"] == "TRACE: explanation"
    assert filtered[2]["content"] == "Important\nTRACE: " + "x" * 4097
    assert filtered[3]["content"] == "TRACE: recent"


def test_positive_trajectory_preselection_and_tie_order(pipeline):
    choice = pipeline.TrajectoryChooser().choose([0.8, 0.9, 0.8, 0.2], [0.4, 0.3, 0.4, 1.0], top_k=3)
    assert choice.chosen_index == 0
    assert choice.preselected_indices == (1, 0, 2)
    assert choice.scores == (0.4, 0.3, 0.4, 1.0)
    assert choice.rationale
    assert pipeline.TrajectoryChooser().choose([0.2, 0.7], [0.9, 0.3], top_k=1).chosen_index == 1
    for screening, final, top_k in (([], [], 1), ([0.2], [0.4, 0.7], 1), ([float("nan")], [0.4], 1), ([0.5], [0.5], 0)):
        with pytest.raises(ValueError):
            pipeline.TrajectoryChooser().choose(screening, final, top_k=top_k)


def test_cli_json_history_and_invalid_payload():
    command = [sys.executable, "-m", MODULE, "--json"]
    input_history = [{"role": "system", "content": "Task"}, {"role": "tool", "content": "Latest output"}]
    result = subprocess.run(
        command, cwd=TEST_ROOT, input=json.dumps(input_history), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["history"][0] == input_history[0]
    assert payload["history"][1]["content"] == "Latest output"
    assert payload["receipt"]["processed_turns"] == 2
    invalid = subprocess.run(
        command, cwd=TEST_ROOT, input='[{"role": "tool", "content": null}]', capture_output=True, text=True, check=False,
    )
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["error"]


def test_negative_receipts_and_optional_history_fields_are_enforced(pipeline):
    from dataclasses import FrozenInstanceError

    assert pipeline.HistoryTurn.__required_keys__ == {"role", "content"}
    assert {"file", "cache_control"} <= pipeline.HistoryTurn.__optional_keys__
    receipts = (
        (pipeline.HistoryCompressionReceiptDTO(0, 0, 0, 0, 0, 0, 0), "original_turns", 1),
        (pipeline.TrajectoryChoiceDTO(0, (0,), (1.0,), "Best"), "chosen_index", 1),
        (pipeline.SubmitReviewReceiptDTO(True, (), True, True), "approved", False),
    )
    for receipt, field, replacement in receipts:
        with pytest.raises(FrozenInstanceError):
            setattr(receipt, field, replacement)


def test_boundary_protected_and_non_window_turns(pipeline):
    system = {"role": "system", "message_type": "observation", "content": "Keep system observation"}
    demo = {"role": "tool", "is_demo": True, "content": "Keep demonstration"}
    window = {"role": "tool", "kind": "window", "file": "a.py", "content": "Real window"}
    records = [
        {"role": "user", "content": "Task"},
        system,
        demo,
        window,
        {"role": "assistant", "kind": "edit", "file": "a.py", "content": "Mention without tool action"},
        {"role": "tool", "kind": "read", "file": "a.py", "content": "Unrelated observation"},
        {"role": "tool", "kind": "edit", "content": "Edit with no file"},
        {"role": "tool", "kind": "window", "content": "Window with no file"},
        {"role": "tool", "content": "Active error"},
    ]
    processed, receipt = pipeline.HistoryProcessorPipeline(keep_last=1, cache_breakpoints=0).process(records)
    assert processed[1:3] == [system, demo]
    assert receipt.closed_windows_elided == 0
    assert pipeline.ClosedWindowElisionProcessor().process(records, {0}) == (records, set())


def test_negative_invalid_submit_path_and_json_have_independent_errors(tmp_path):
    aci = SweQaAci(repo_root=str(tmp_path))
    path_receipt = aci.review_on_submit({"invalid\0.py": "x = 1"})
    assert not path_receipt.approved
    assert len(path_receipt.blocking_reasons) == 1
    assert "invalid submit path" in path_receipt.blocking_reasons[0]
    json_receipt = aci.review_on_submit({"config.json": '{"key":'})
    assert not json_receipt.approved
    assert not json_receipt.syntax_valid
    assert json_receipt.clean_pom_valid
    content_receipt = aci.review_on_submit({"invalid.md": "\ud800", "null.py": None})
    assert not content_receipt.approved
    assert len(content_receipt.blocking_reasons) == 2
