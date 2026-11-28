# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Traverse offline research queries and collect bounded, cited evidence."""

from __future__ import annotations

import argparse
from collections import deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import date
import json
import re
import sys
from typing import Literal
from urllib.parse import urlsplit


MAX_CONTEXT_WORDS = 25000
MAX_DEPTH = 4
MAX_BREADTH = 5
MAX_QUERY_PAYLOAD_CHARS = 32768
UsefulnessLevel = Literal[0, 1, 2, 3]


@dataclass(frozen=True)
class EvidenceChunk:
    chunk_id: str
    source_url: str
    text: str
    published_at: date | None = None


@dataclass(frozen=True)
class ScoredEvidenceChunkDTO:
    chunk_id: str
    source_url: str
    text: str
    usefulness_level: UsefulnessLevel
    rubric_score: float
    credibility_score: float


@dataclass(frozen=True)
class ResearchLearningDTO:
    depth: int
    query: str
    learning: str
    citations: tuple[str, ...]
    usefulness_level: UsefulnessLevel


@dataclass(frozen=True)
class DeepResearchResultDTO:
    visited_queries: tuple[str, ...]
    learnings: tuple[ResearchLearningDTO, ...]
    kept_chunks: int
    words_used: int

    @property
    def learnings_count(self) -> int:
        return len(self.learnings)


_WORD = re.compile(r"[^\W_]+")
_FACT = re.compile(
    r"\b(?:\d+(?:[.,]\d+)?|defaults? to|requires?|supports?|measured|observed|increased|decreased)\b",
    re.IGNORECASE,
)
_STOPWORDS = {"a", "an", "at", "for", "how", "in", "is", "of", "on", "the", "to", "what", "when", "which", "with"}
_FENCED_QUERY_BLOCK = re.compile(r"\x60{3}(?:json)?[ \t]*\r?\n(.*?)\x60{3}", re.IGNORECASE | re.DOTALL)
_JSON_STRING_OR_COMMA = re.compile(r'"(?:[^"\\]|\\.)*"|,(?=\s*[}\]])')
_QUERY_LIST_ITEM = re.compile(r"^[ \t]*(?:[-*]|\d+\.)[ \t]+(.+)$", re.MULTILINE)
_DEFAULT_FACETS = ("evidence", "limitations", "implementation", "measurements", "tradeoffs")


def _distinct_queries(values: Iterable[object]) -> tuple[str, ...]:
    queries: dict[str, str] = {}
    for item in values:
        candidate = item.get("query") if isinstance(item, dict) else item
        if isinstance(candidate, str):
            query = " ".join(candidate.split())
            if query:
                queries.setdefault(query.casefold(), query)
    return tuple(queries.values())


def extract_queries(payload: str) -> tuple[str, ...]:
    """Read JSON query lists or Markdown bullets, repairing JSON trailing commas."""
    text = payload[:MAX_QUERY_PAYLOAD_CHARS].strip()
    for block in (*_FENCED_QUERY_BLOCK.findall(text), text):
        start = re.search(r"[\[{]", block)
        if start is None:
            continue
        candidate = _JSON_STRING_OR_COMMA.sub(lambda match: "" if match[0] == "," else match[0], block[start.start():])
        try:
            decoded, _ = json.JSONDecoder().raw_decode(candidate)
        except (ValueError, RecursionError):
            continue
        if isinstance(decoded, dict):
            decoded = decoded.get("queries", decoded.get("followUpQuestions"))
        if isinstance(decoded, list):
            return _distinct_queries(decoded)
    return _distinct_queries(_QUERY_LIST_ITEM.findall(text))


def _evidence_density(text: str) -> float:
    return len(_FACT.findall(text)) / max(1, len(text.split()))


class SourceCurator:
    """Rank web source metadata by credibility, publication date, and evidence density."""

    @staticmethod
    def credibility_score(url: str) -> float:
        try:
            parsed = urlsplit(url)
            host = parsed.hostname or ""
        except ValueError:
            return 0.0
        if parsed.scheme not in {"https", "http"} or not host or parsed.username is not None:
            return 0.0
        if any(character.isspace() for character in url):
            return 0.0
        host = host.rstrip(".").casefold()
        if parsed.scheme == "https" and host.endswith((".gov", ".edu", ".ac.uk")):
            return 1.0
        if parsed.scheme == "https" and host.endswith(".org"):
            return 0.75
        return 0.55 if parsed.scheme == "https" else 0.35

    def rank(self, chunks: Sequence[EvidenceChunk]) -> tuple[EvidenceChunk, ...]:
        return tuple(sorted(
            chunks,
            key=lambda chunk: (
                -self.credibility_score(chunk.source_url),
                -(chunk.published_at or date.min).toordinal(),
                -_evidence_density(chunk.text),
                chunk.source_url,
                chunk.chunk_id,
            ),
        ))


UsefulnessGateway = Callable[[str, EvidenceChunk], UsefulnessLevel]


class UsefulnessRubricFilter:
    """Grade chunks from unrelated material to direct factual answers."""

    def __init__(self, *, gateway: UsefulnessGateway | None = None, allow_gateway: bool = False):
        if allow_gateway and gateway is None:
            raise ValueError("An enabled gateway requires a scorer")
        self.gateway = gateway if allow_gateway else None

    @staticmethod
    def _offline_level(query: str, text: str) -> UsefulnessLevel:
        query_terms = set(_WORD.findall(query.casefold())) - _STOPWORDS
        evidence_terms = set(_WORD.findall(text.casefold()))
        shared = query_terms & evidence_terms
        if not shared:
            return 0
        if not _FACT.search(text):
            return 1
        return 3 if len(shared) / len(query_terms) >= 0.8 else 2

    def score(self, query: str, chunk: EvidenceChunk) -> ScoredEvidenceChunkDTO:
        level = self._offline_level(query, chunk.text) if self.gateway is None else self.gateway(query, chunk)
        if type(level) is not int or level not in (0, 1, 2, 3):
            raise ValueError("Usefulness must be an integer from 0 through 3")
        return ScoredEvidenceChunkDTO(
            chunk.chunk_id, chunk.source_url, chunk.text, level, level / 3,
            SourceCurator.credibility_score(chunk.source_url),
        )


Search = Callable[[str], Sequence[EvidenceChunk]]
Expand = Callable[[str, tuple[ResearchLearningDTO, ...]], Sequence[str] | str]


def _follow_ups(query: str, learnings: tuple[ResearchLearningDTO, ...], expand: Expand | None) -> tuple[str, ...]:
    if expand is None:
        words = set(query.casefold().split())
        return tuple(f"{query} {facet}" for facet in _DEFAULT_FACETS if facet not in words)
    supplied = expand(query, learnings)
    if isinstance(supplied, str):
        return extract_queries(supplied)
    if not isinstance(supplied, Sequence):
        raise ValueError("Expansion must return queries or a text payload")
    return _distinct_queries(supplied)


class DeepResearchTree:
    """Expand queries by level with a global budget and duplicate detection."""

    def __init__(self, rubric: UsefulnessRubricFilter | None = None, curator: SourceCurator | None = None):
        self.rubric = rubric or UsefulnessRubricFilter()
        self.curator = curator or SourceCurator()

    def research(
        self, query: str, search: Search, *, expand: Expand | None = None,
        depth: int = 2, breadth: int = 3, max_context_words: int = MAX_CONTEXT_WORDS,
    ) -> DeepResearchResultDTO:
        if min(depth, breadth, max_context_words) < 0:
            raise ValueError("Depth, breadth, and context limit must be non-negative")
        query = " ".join(query.split())
        if not query or not min(depth, breadth, max_context_words):
            return DeepResearchResultDTO((), (), 0, 0)
        depth = min(depth, MAX_DEPTH)
        breadth = min(breadth, MAX_BREADTH)
        budget = min(max_context_words, MAX_CONTEXT_WORDS)
        pending = deque([(query, 1)])
        scheduled = {query.casefold()}
        visited = []
        kept_ids: set[str] = set()
        learnings = []
        words_used = 0

        while pending and words_used < budget:
            current, level = pending.popleft()
            visited.append(current)
            ranked = self.curator.rank(search(current))
            scored = sorted(
                (self.rubric.score(current, chunk) for chunk in ranked),
                key=lambda chunk: -chunk.usefulness_level,
            )
            for chunk in scored:
                if chunk.usefulness_level < 2 or not chunk.credibility_score or chunk.chunk_id in kept_ids:
                    continue
                note = f"{chunk.text.strip()} [{chunk.source_url}]"
                words = len(note.split())
                if words_used + words > budget:
                    continue
                learnings.append(ResearchLearningDTO(level, current, note, (chunk.source_url,), chunk.usefulness_level))
                kept_ids.add(chunk.chunk_id)
                words_used += words

            if level < depth and words_used < budget:
                next_queries = (
                    candidate for candidate in _follow_ups(current, tuple(learnings), expand)
                    if candidate.casefold() not in scheduled
                )
                for child in tuple(next_queries)[:breadth]:
                    scheduled.add(child.casefold())
                    pending.append((child, level + 1))

        return DeepResearchResultDTO(tuple(visited), tuple(learnings), len(kept_ids), words_used)


def _read_chunk(raw: object) -> EvidenceChunk:
    required = ("chunk_id", "source_url", "text")
    if not isinstance(raw, dict) or not all(isinstance(raw.get(field), str) for field in required):
        raise ValueError("Each chunk requires string chunk_id, source_url, and text fields")
    published = raw.get("published_at")
    if published is not None and not isinstance(published, str):
        raise ValueError("published_at must be an ISO date")
    return EvidenceChunk(raw["chunk_id"], raw["source_url"], raw["text"], date.fromisoformat(published) if published else None)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the research report as JSON")
    args = parser.parse_args(argv)
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict) or not isinstance(request.get("query"), str):
            raise ValueError("Input requires a query string")
        records = request.get("chunks", [])
        if not isinstance(records, list):
            raise ValueError("chunks must be an array")
        limits = {name: request[name] for name in ("depth", "breadth", "max_context_words") if name in request}
        if any(type(value) is not int for value in limits.values()):
            raise ValueError("Research limits must be integers")
        chunks = tuple(_read_chunk(record) for record in records)
        result = DeepResearchTree().research(request["query"], lambda _query: chunks, **limits)
    except (ValueError, RecursionError) as error:
        print(json.dumps({"error": str(error)}) if args.json else str(error))
        return 2
    if args.json:
        print(json.dumps(asdict(result) | {"learnings_count": result.learnings_count}))
    else:
        print(f"Collected {result.learnings_count} cited learnings using {result.words_used} words.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
