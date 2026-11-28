# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Find benchmark overlap and measure evaluator sensitivity to degraded evidence."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import json
import math
import re
import sys
from typing import Literal
import unicodedata


PerturbationKind = Literal["strip_citations", "drop_sources", "inject_contradiction", "truncate_context"]


@dataclass(frozen=True)
class ContaminationMatchDTO:
    source_id: str
    benchmark_id: str
    matched_ngrams: int
    overlap_ratio: float
    sample_ngram: str


@dataclass(frozen=True)
class PerturbationAuditDTO:
    perturbation_kind: PerturbationKind
    baseline_score: float
    degraded_scores: tuple[float, ...]
    is_monotonically_non_increasing: bool
    drop_magnitude: float


class BenchmarkDecontaminator:
    """Index distinct word n-grams and report their share of each benchmark."""

    def __init__(self, ngram_size: int = 8):
        if ngram_size < 5:
            raise ValueError("ngram_size must be at least five words")
        self.ngram_size = ngram_size

    @staticmethod
    def normalize_string(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text).casefold()
        return " ".join(re.findall(r"[^\W_]+", normalized))

    def word_ngrams(self, text: str) -> tuple[str, ...]:
        words = self.normalize_string(text).split()
        return tuple(
            " ".join(words[index:index + self.ngram_size])
            for index in range(len(words) - self.ngram_size + 1)
        )

    def detect_contamination(
        self, sources: Mapping[str, str], benchmarks: Mapping[str, str],
    ) -> tuple[ContaminationMatchDTO, ...]:
        lookup: dict[str, list[str]] = defaultdict(list)
        benchmark_sizes: dict[str, int] = {}
        for benchmark_id, text in benchmarks.items():
            grams = set(self.word_ngrams(text))
            benchmark_sizes[benchmark_id] = len(grams)
            for gram in grams:
                lookup[gram].append(benchmark_id)

        result = []
        for source_id, text in sorted(sources.items()):
            overlaps: dict[str, list[str]] = defaultdict(list)
            for gram in set(self.word_ngrams(text)):
                for benchmark_id in lookup.get(gram, ()):
                    overlaps[benchmark_id].append(gram)
            for benchmark_id, matches in sorted(overlaps.items()):
                result.append(ContaminationMatchDTO(
                    source_id, benchmark_id, len(matches), len(matches) / benchmark_sizes[benchmark_id],
                    min(matches),
                ))
        return tuple(result)


_KINDS: tuple[PerturbationKind, ...] = (
    "strip_citations", "drop_sources", "inject_contradiction", "truncate_context",
)
_REFERENCES = re.compile(r"^[ \t]*#{1,6}[ \t]+references[ \t]*$", re.IGNORECASE | re.MULTILINE)
_CITATION = re.compile(r"(?<!\\)\[(?P<label>[^\[\]\n]{1,160})\]\(https?://[^\s)]{1,2048}\)|(?<!\\)\[\d{1,9}\]")
_SCORE_TOLERANCE = 1e-9


def _strip_citations(report: str, fraction: float) -> str:
    references = _REFERENCES.search(report)
    body_end = references.start() if references else len(report)
    body = report[:body_end]
    matches = list(_CITATION.finditer(body))
    count = math.ceil(len(matches) * fraction)
    cursor = 0
    parts = []
    for match in matches[len(matches) - count:]:
        parts.extend((body[cursor:match.start()], match["label"] or ""))
        cursor = match.end()
    parts.append(report[cursor:])
    return "".join(parts)


def _degrade(
    report: str, sources: tuple[str, ...], kind: PerturbationKind, step: int, steps: int,
) -> tuple[str, tuple[str, ...]]:
    fraction = step / steps
    if kind == "strip_citations":
        return _strip_citations(report, fraction), sources
    if kind == "drop_sources":
        return report, sources[:len(sources) - math.ceil(len(sources) * fraction)]
    if kind == "inject_contradiction":
        addition = "\nContradiction: A preceding finding is false." * step if report.strip() else ""
        return report + addition, sources

    trimmed = []
    for source in sources:
        words = source.split()
        count = len(words) - math.ceil(len(words) * fraction)
        trimmed.append(" ".join(words[:count]))
    return report, tuple(trimmed)


Metric = Callable[[str, tuple[str, ...]], float]


def _score(metric: Metric, report: str, sources: tuple[str, ...]) -> float:
    measured = metric(report, sources)
    if not math.isfinite(measured):
        raise ValueError("Metric scores must be finite")
    return float(measured)


class MetricPerturbationSuite:
    """Independently degrade four inputs and measure a caller-supplied evaluator."""

    def audit(
        self, report: str, sources: Sequence[str], metric: Metric, *, steps: int = 3,
    ) -> tuple[PerturbationAuditDTO, ...]:
        if not 1 <= steps <= 20:
            raise ValueError("steps must be between 1 and 20")
        source_snapshot = tuple(sources)
        baseline = _score(metric, report, source_snapshot)
        audits = []
        for kind in _KINDS:
            scores = tuple(
                _score(metric, *_degrade(report, source_snapshot, kind, step, steps))
                for step in range(1, steps + 1)
            )
            earlier_scores = (baseline, *scores[:-1])
            monotone = all(
                earlier >= later - _SCORE_TOLERANCE for earlier, later in zip(earlier_scores, scores)
            )
            audits.append(PerturbationAuditDTO(kind, baseline, scores, monotone, baseline - scores[-1]))
        return tuple(audits)

    @staticmethod
    def proves_sensitivity(audits: Sequence[PerturbationAuditDTO]) -> bool:
        return (
            len(audits) == len(_KINDS)
            and {audit.perturbation_kind for audit in audits} == set(_KINDS)
            and all(audit.is_monotonically_non_increasing and audit.drop_magnitude > _SCORE_TOLERANCE
                    for audit in audits)
        )


def _read_corpus(value: object, field: str) -> Mapping[str, str]:
    if not isinstance(value, dict) or any(not isinstance(text, str) for text in value.values()):
        raise ValueError(f"{field} must be an object mapping identifiers to text")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngram-size", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Print matches as JSON")
    args = parser.parse_args(argv)
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ValueError("Input must be a corpus object")
        detector = BenchmarkDecontaminator(args.ngram_size)
        matches = detector.detect_contamination(
            _read_corpus(request.get("sources"), "sources"), _read_corpus(request.get("benchmarks"), "benchmarks"),
        )
    except ValueError as error:
        print(json.dumps({"error": str(error)}) if args.json else str(error))
        return 2
    if args.json:
        print(json.dumps({"contaminated_count": len(matches), "matches": [asdict(match) for match in matches]}))
    else:
        print(f"Source and benchmark overlaps: {len(matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
