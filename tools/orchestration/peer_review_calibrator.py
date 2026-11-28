# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Calibrate independent peer reviews, compare ADRs, and record bounded experiments."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
import json
import math
from pathlib import Path
import re
from statistics import fmean
from subprocess import CalledProcessError, TimeoutExpired
from typing import Literal, TypedDict, cast


ReviewDecision = Literal["Accept", "Reject"]
ExperimentStatus = Literal["TARGET_REACHED", "EXHAUSTED"]

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = _ROOT / "tools" / "catalogs" / "prompt_patterns_catalog.json"
DEFAULT_ADR_DIRECTORY = _ROOT / "docs" / "adr"


@dataclass(frozen=True)
class PeerReviewRubricDTO:
    reviewer_id: str
    originality: int
    quality: int
    clarity: int
    significance: int
    soundness: int
    presentation: int
    contribution: int
    overall: int
    confidence: int
    decision: ReviewDecision
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetaReviewReceiptDTO:
    reviewer_count: int
    mean_overall: float
    confidence_weighted_overall: float
    calibrated_decision: ReviewDecision
    dissent_detected: bool
    key_weaknesses: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdeaNoveltyReceiptDTO:
    idea_title: str
    is_novel: bool
    max_similarity: float
    closest_existing_id: str | None
    verdict_reason: str


@dataclass(frozen=True)
class ExperimentAttemptDTO:
    attempt: int
    score: float | None
    best_score: float | None
    stderr: str


@dataclass(frozen=True)
class ExperimentRepairReceiptDTO:
    status: ExperimentStatus
    best_score: float | None
    attempts: tuple[ExperimentAttemptDTO, ...]


_RUBRIC_LIMITS = {
    "originality": 4, "quality": 4, "clarity": 4, "significance": 4,
    "soundness": 4, "presentation": 4, "contribution": 4, "overall": 10, "confidence": 5,
}


class CalibratedPeerReviewer:
    """Apply rubric bounds and require a confidence-weighted acceptance majority."""

    def __init__(self, *, acceptance_threshold: float = 7.0, minimum_confidence: int = 3):
        if not 1 <= acceptance_threshold <= 10:
            raise ValueError("Acceptance threshold must be between 1 and 10")
        if type(minimum_confidence) is not int or not 1 <= minimum_confidence <= 5:
            raise ValueError("Minimum confidence must be an integer between 1 and 5")
        self.acceptance_threshold = acceptance_threshold
        self.minimum_confidence = minimum_confidence

    def calibrate(self, review: PeerReviewRubricDTO, *, clamp: bool = False) -> PeerReviewRubricDTO:
        if not isinstance(review.reviewer_id, str) or not review.reviewer_id.strip():
            raise ValueError("Reviewer ID must be non-empty text")
        if review.decision not in ("Accept", "Reject"):
            raise ValueError("Decision must be Accept or Reject")
        scores: dict[str, int] = {}
        for dimension, maximum in _RUBRIC_LIMITS.items():
            score = getattr(review, dimension)
            if type(score) is not int:
                raise ValueError(f"{dimension} must be an integer")
            if not clamp and not 1 <= score <= maximum:
                raise ValueError(f"{dimension} must be between 1 and {maximum}")
            scores[dimension] = min(maximum, max(1, score))

        accept = (
            review.decision == "Accept"
            and scores["overall"] >= self.acceptance_threshold
            and scores["confidence"] >= self.minimum_confidence
            and scores["soundness"] >= 2
        )
        return replace(review, **scores, decision="Accept" if accept else "Reject")

    def synthesize_meta_review(self, reviews: Sequence[PeerReviewRubricDTO]) -> MetaReviewReceiptDTO:
        if not reviews:
            raise ValueError("At least one review is required")
        calibrated = tuple(self.calibrate(review) for review in reviews)
        ids = {review.reviewer_id.strip().casefold() for review in calibrated}
        if len(ids) != len(calibrated):
            raise ValueError("Reviewer IDs must be unique")
        confidence_total = sum(review.confidence for review in calibrated)
        weighted = sum(review.overall * review.confidence for review in calibrated) / confidence_total
        accepted_weight = sum(review.confidence for review in calibrated if review.decision == "Accept")
        accept = weighted >= self.acceptance_threshold and accepted_weight * 2 > confidence_total
        overall = tuple(review.overall for review in calibrated)
        dissent = len({review.decision for review in calibrated}) > 1 or max(overall) - min(overall) >= 3
        weaknesses: dict[str, str] = {}
        for review in calibrated:
            for item in review.weaknesses:
                if cleaned := item.strip():
                    weaknesses.setdefault(cleaned.casefold(), cleaned)
        return MetaReviewReceiptDTO(
            len(calibrated), fmean(overall), weighted, "Accept" if accept else "Reject",
            dissent, tuple(weaknesses.values()),
        )


_ADR_ID = re.compile(r"ADR-\d+")
_ADR_TITLE = re.compile(r"^#[ \t]+(?:ADR-\d+[ \t]*[:\u2014-]?[ \t]*)?(.+)$", re.MULTILINE)
_ADR_CONTEXT = re.compile(r"^##[ \t]+(?:context|summary)\b[^\n]*\n(.*?)(?=^#{1,2}[ \t]|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
_WORD = re.compile(r"[^\W_]+")
_MAX_ADR_CHARS = 32768


def _read_adr(path: Path) -> tuple[str, str, str] | None:
    with path.open(encoding="utf-8") as stream:
        text = stream.read(_MAX_ADR_CHARS)
    identifier = _ADR_ID.match(path.stem)
    title = _ADR_TITLE.search(text)
    if identifier is None or title is None:
        return None
    context = _ADR_CONTEXT.search(text)
    return identifier[0], title[1].strip(), context[1].strip() if context else ""


class NoveltyCheckedIdeaGenerator:
    """Compare candidate titles and summaries with the local ADR archive."""

    def __init__(self, archive: Path = DEFAULT_ADR_DIRECTORY, *, threshold: float = 0.65, ngram_size: int = 3):
        if not 0 < threshold <= 1:
            raise ValueError("Novelty threshold must be in (0, 1]")
        if type(ngram_size) is not int or ngram_size < 1:
            raise ValueError("ngram_size must be a positive integer")
        self.archive = Path(archive)
        self.threshold = threshold
        self.ngram_size = ngram_size

    def _ngrams(self, text: str) -> set[tuple[str, ...]]:
        words = _WORD.findall(text.casefold())
        if not words:
            return set()
        width = min(len(words), self.ngram_size)
        return {tuple(words[index:index + width]) for index in range(len(words) - width + 1)}

    @staticmethod
    def _jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
        union = left | right
        return len(left & right) / len(union) if union else 0.0

    def evaluate(self, title: str, summary: str = "") -> IdeaNoveltyReceiptDTO:
        title = title.strip()
        if not title:
            raise ValueError("An idea requires a title")
        title_grams = self._ngrams(title)
        summary_grams = self._ngrams(summary)
        strongest, closest = 0.0, None
        for path in sorted(self.archive.glob("ADR-*.md")):
            record = _read_adr(path)
            if record is None:
                continue
            identifier, existing_title, existing_summary = record
            score = max(
                self._jaccard(title_grams, self._ngrams(existing_title)),
                self._jaccard(summary_grams, self._ngrams(existing_summary)),
            )
            if score > strongest:
                strongest, closest = score, identifier
        novel = strongest < self.threshold
        reason = (
            f"Similarity {strongest:.3f} is below the {self.threshold:.3f} threshold."
            if novel else f"Similarity {strongest:.3f} matches {closest} at the {self.threshold:.3f} threshold."
        )
        return IdeaNoveltyReceiptDTO(title, novel, strongest, closest, reason)


Experiment = Callable[[int, ExperimentAttemptDTO | None], tuple[float | None, str]]


def _error_stderr(error: CalledProcessError | TimeoutExpired | OSError) -> str:
    stderr = getattr(error, "stderr", None)
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace")
    return stderr if isinstance(stderr, str) and stderr else str(error)


class ExperimentRepairLoop:
    """Keep the best measured score and expose diagnostics to the next attempt."""

    MAX_RUNS = 5

    def __init__(self, max_runs: int = 3):
        if type(max_runs) is not int or max_runs < 1:
            raise ValueError("max_runs must be a positive integer")
        self.max_runs = min(max_runs, self.MAX_RUNS)

    def run(self, execute: Experiment, *, target_score: float) -> ExperimentRepairReceiptDTO:
        if not math.isfinite(target_score):
            raise ValueError("Target score must be finite")
        ledger: list[ExperimentAttemptDTO] = []
        best = None
        for attempt in range(1, self.max_runs + 1):
            try:
                score, stderr = execute(attempt, ledger[-1] if ledger else None)
            except (CalledProcessError, TimeoutExpired, OSError) as error:
                score, stderr = None, _error_stderr(error)
            if score is not None:
                if not math.isfinite(score):
                    raise ValueError("Experiment scores must be finite")
                best = score if best is None else max(best, score)
            ledger.append(ExperimentAttemptDTO(attempt, score, best, stderr))
            if best is not None and best >= target_score:
                return ExperimentRepairReceiptDTO("TARGET_REACHED", best, tuple(ledger))
        return ExperimentRepairReceiptDTO("EXHAUSTED", best, tuple(ledger))


class PromptPattern(TypedDict):
    id: str
    name: str
    when_to_use: str
    source_path: str


class PromptPatternsCatalog(TypedDict):
    schema_version: str
    patterns: list[PromptPattern]
    context_engineering: list[str]
    risk_mitigations: dict[str, str]


def load_prompt_patterns(path: Path = DEFAULT_CATALOG) -> PromptPatternsCatalog:
    """Load a versioned catalog and verify its core fields and unique pattern IDs."""
    with Path(path).open(encoding="utf-8") as stream:
        catalog = json.load(stream)
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "1.0.0":
        raise ValueError("Invalid pattern catalog schema version")
    patterns = catalog.get("patterns")
    if not isinstance(patterns, list) or len(patterns) != 18:
        raise ValueError("Pattern catalog must contain 18 entries")
    ids = set()
    for entry in patterns:
        fields = ("id", "name", "when_to_use", "source_path")
        if not isinstance(entry, dict) or not all(isinstance(entry.get(field), str) and entry[field].strip() for field in fields):
            raise ValueError("Each pattern requires non-empty id, name, when_to_use, and source_path")
        if entry["id"] in ids:
            raise ValueError(f"Duplicate pattern ID: {entry['id']}")
        ids.add(entry["id"])
    context = catalog.get("context_engineering")
    if not isinstance(context, list) or not context or not all(isinstance(item, str) and item.strip() for item in context):
        raise ValueError("Context engineering requires a non-empty checklist")
    risks = catalog.get("risk_mitigations")
    if not isinstance(risks, dict) or not risks or not all(isinstance(item, str) and item.strip() for item in risks.values()):
        raise ValueError("Risk mitigations require a non-empty mapping")
    return cast(PromptPatternsCatalog, catalog)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--adr-dir", type=Path, default=DEFAULT_ADR_DIRECTORY)
    parser.add_argument("--idea-title")
    parser.add_argument("--idea-summary", default="")
    parser.add_argument("--json", action="store_true", help="Print catalog and optional novelty receipt as JSON")
    args = parser.parse_args(argv)
    try:
        catalog = load_prompt_patterns(args.catalog)
        count = len(catalog["patterns"])
        output: dict[str, object] = {"pattern_count": count, "catalog": catalog}
        if args.idea_title is not None:
            generator = NoveltyCheckedIdeaGenerator(args.adr_dir)
            output["novelty"] = asdict(generator.evaluate(args.idea_title, args.idea_summary))
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({"error": str(error)}) if args.json else str(error))
        return 2
    print(json.dumps(output) if args.json else f"Loaded {count} prompt patterns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
