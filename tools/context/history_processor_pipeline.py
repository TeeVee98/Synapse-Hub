# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Compress agent observations and rank previously scored repair attempts."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import re
import sys
from typing import AbstractSet, Literal, Sequence, TypedDict


class _RequiredHistoryFields(TypedDict):
    role: str
    content: str


class HistoryTurn(_RequiredHistoryFields, total=False):
    message_type: str
    kind: str
    file: str
    is_demo: bool
    cache_control: dict[str, Literal["ephemeral"]]


@dataclass(frozen=True)
class HistoryCompressionReceiptDTO:
    original_turns: int
    processed_turns: int
    elided_observations: int
    closed_windows_elided: int
    cache_breakpoints_placed: int
    estimated_tokens_before: int
    estimated_tokens_after: int


@dataclass(frozen=True)
class TrajectoryChoiceDTO:
    chosen_index: int
    preselected_indices: tuple[int, ...]
    scores: tuple[float, ...]
    rationale: str


@dataclass(frozen=True)
class SubmitReviewReceiptDTO:
    approved: bool
    files_changed: tuple[str, ...]
    syntax_valid: bool
    clean_pom_valid: bool
    blocking_reasons: tuple[str, ...] = ()


def _is_observation(turn: HistoryTurn) -> bool:
    return turn["role"] == "tool" or turn.get("message_type") == "observation"


def _replace_content(turn: HistoryTurn, description: str) -> HistoryTurn:
    count = len(turn["content"].splitlines())
    updated = turn.copy()
    updated["content"] = f"{description}: ({count} lines omitted)"
    return updated


class LastNObservationsProcessor:
    """Omit older environment output outside the protected observations."""

    def __init__(self, keep_last: int = 3):
        self.keep_last = max(1, keep_last)

    def protected_indices(self, history: Sequence[HistoryTurn]) -> set[int]:
        observations = [index for index, turn in enumerate(history) if _is_observation(turn)]
        return {0, *observations[-self.keep_last:]} | {
            index for index, turn in enumerate(history) if turn["role"] == "system" or turn.get("is_demo", False)
        }

    def process(
        self, history: Sequence[HistoryTurn], protected: AbstractSet[int]
    ) -> tuple[list[HistoryTurn], int]:
        result = list(history)
        count = 0
        for index, turn in enumerate(history):
            if index not in protected and _is_observation(turn):
                result[index] = _replace_content(turn, "Old environment output")
                count += 1
        return result, count


class ClosedWindowElisionProcessor:
    """Omit superseded windows for a file reopened or edited later."""

    def process(
        self, history: Sequence[HistoryTurn], protected: AbstractSet[int]
    ) -> tuple[list[HistoryTurn], set[int]]:
        result = list(history)
        seen: set[str] = set()
        elided: set[int] = set()
        for index in reversed(range(len(history))):
            turn = history[index]
            path = turn.get("file")
            kind = turn.get("kind")
            if not path or not _is_observation(turn) or kind not in ("window", "edit"):
                continue
            if kind == "window" and path in seen and index not in protected:
                result[index] = _replace_content(turn, "Outdated file window")
                elided.add(index)
            seen.add(path)
        return result, elided


class CacheControlBreakpointProcessor:
    """Refresh ephemeral checkpoints on the most recent user and tool turns."""

    def __init__(self, count: int = 2):
        self.count = max(0, count)

    def process(self, history: Sequence[HistoryTurn]) -> tuple[list[HistoryTurn], int]:
        eligible = [index for index, turn in enumerate(history) if turn["role"] in ("user", "tool")]
        placed = set(eligible[-self.count:]) if self.count else set()
        result = []
        for index, turn in enumerate(history):
            updated = turn.copy()
            updated.pop("cache_control", None)
            if index in placed:
                updated["cache_control"] = {"type": "ephemeral"}
            result.append(updated)
        return result, len(placed)


_ANSI_SEQUENCE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_SAFE_NOISE_PATTERN = re.compile(r"\^[A-Za-z0-9 _:;,!/=-]+(?:\.\*)?\$?")


class RegexNoiseFilterProcessor:
    """Strip ANSI codes and filter log lines using bounded, anchored patterns."""

    def __init__(self, patterns: Sequence[str] = (r"^DEBUG: .*$",)):
        compiled = []
        for pattern in patterns:
            try:
                regex = re.compile(pattern)
            except re.error as error:
                raise ValueError(f"Invalid noise pattern: {error}") from error
            if _SAFE_NOISE_PATTERN.fullmatch(pattern) is None:
                raise ValueError("A noise pattern must start with an anchored literal prefix")
            compiled.append(regex)
        self.patterns = tuple(compiled)

    def process(self, history: Sequence[HistoryTurn], protected: AbstractSet[int]) -> list[HistoryTurn]:
        result = list(history)
        for index, turn in enumerate(history):
            if index in protected or not _is_observation(turn):
                continue
            lines = []
            for raw_line in turn["content"].splitlines(keepends=True):
                if len(raw_line) > 4096:
                    lines.append(raw_line)
                    continue
                line = _ANSI_SEQUENCE.sub("", raw_line)
                if not any(pattern.search(line) for pattern in self.patterns):
                    lines.append(line)
            updated = turn.copy()
            updated["content"] = "".join(lines)
            result[index] = updated
        return result


def _validate_history(history: object) -> None:
    if not isinstance(history, Sequence):
        raise ValueError("History must be a sequence of turns")
    for turn in history:
        if not isinstance(turn, dict) or not all(isinstance(turn.get(key), str) for key in ("role", "content")):
            raise ValueError("Each turn requires string role and content fields")
        for key in ("message_type", "kind", "file"):
            if key in turn and not isinstance(turn[key], str):
                raise ValueError(f"History field {key} must be a string")


def _estimated_tokens(history: Sequence[HistoryTurn]) -> int:
    return sum(math.ceil(len(turn["content"]) / 4) for turn in history)


class HistoryProcessorPipeline:
    """Compose noise filtering, window elision, observation retention, and checkpoints."""

    def __init__(
        self,
        keep_last: int = 3,
        cache_breakpoints: int = 2,
        noise_patterns: Sequence[str] = (r"^DEBUG: .*$",),
    ):
        self.observations = LastNObservationsProcessor(keep_last)
        self.windows = ClosedWindowElisionProcessor()
        self.breakpoints = CacheControlBreakpointProcessor(cache_breakpoints)
        self.noise = RegexNoiseFilterProcessor(noise_patterns)

    def process(self, history: Sequence[HistoryTurn]) -> tuple[list[HistoryTurn], HistoryCompressionReceiptDTO]:
        _validate_history(history)
        protected = self.observations.protected_indices(history)
        filtered = self.noise.process(history, protected)
        windows, closed = self.windows.process(filtered, protected)
        elided, observations = self.observations.process(windows, protected | closed)
        processed, checkpoints = self.breakpoints.process(elided)
        return processed, HistoryCompressionReceiptDTO(
            len(history), len(processed), observations, len(closed), checkpoints,
            _estimated_tokens(history), _estimated_tokens(processed),
        )


class TrajectoryChooser:
    """Screen attempts by preliminary score, then select by final verification score."""

    def choose(
        self, screening_scores: Sequence[float], scores: Sequence[float], *, top_k: int = 3
    ) -> TrajectoryChoiceDTO:
        if not scores or len(screening_scores) != len(scores) or top_k < 1:
            raise ValueError("Provide equally sized non-empty score lists and a positive top_k")
        if not all(math.isfinite(score) for score in (*screening_scores, *scores)):
            raise ValueError("Trajectory scores must be finite")

        ranked = sorted(range(len(scores)), key=lambda index: (-screening_scores[index], index))
        preselected = tuple(ranked[:top_k])
        chosen = min(preselected, key=lambda index: (-scores[index], index))
        return TrajectoryChoiceDTO(
            chosen, preselected, tuple(scores),
            "Highest final verification score in the preselection, with input order breaking ties.",
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-last", type=int, default=3)
    parser.add_argument("--cache-breakpoints", type=int, default=2)
    parser.add_argument("--json", action="store_true", help="Print compressed history and the receipt as JSON")
    args = parser.parse_args(argv)

    try:
        history = json.load(sys.stdin)
        processed, receipt = HistoryProcessorPipeline(args.keep_last, args.cache_breakpoints).process(history)
    except ValueError as error:
        print(json.dumps({"error": str(error)}) if args.json else str(error))
        return 2
    if args.json:
        print(json.dumps({"history": processed, "receipt": asdict(receipt)}))
    else:
        print(f"Processed {receipt.processed_turns} turns and elided {receipt.elided_observations} observations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
