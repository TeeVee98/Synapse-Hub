# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Build an offline, multi-perspective knowledge tree with verified citations."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
import sys

from tools.context.deep_research_engine import ResearchLearningDTO, SourceCurator


@dataclass(frozen=True)
class KnowledgeNodeDTO:
    node_id: str
    title: str
    path: tuple[str, ...]
    citation_ids: tuple[int, ...]
    summary: str
    children_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchPersona:
    name: str
    focus: str


@dataclass(frozen=True)
class InterviewSource:
    source_id: int
    url: str
    excerpt: str


@dataclass(frozen=True)
class ConversationTurn:
    persona: ResearchPersona
    question: str
    answer: str
    citation_ids: tuple[int, ...]


@dataclass(frozen=True)
class StormSynthesisDTO:
    persona_count: int
    node_count: int
    verified_citations: int
    report: str
    turns: tuple[ConversationTurn, ...]


@dataclass
class KnowledgeNode:
    title: str
    summary: str = ""
    citation_ids: tuple[int, ...] = ()
    children: dict[str, KnowledgeNode] = field(default_factory=dict)


_HEADING = re.compile(r"(#{1,6})[ \t]+(.+)")
_CITATION = re.compile(r"(?<!\\)\[([0-9]+)\]")
_WORD = re.compile(r"[^\W_]+")
_MAX_CITATION_DIGITS = 18


def _topic_title(topic: str) -> str:
    title = topic.strip()
    if not title or len(title.splitlines()) != 1:
        raise ValueError("The topic must be one non-empty line")
    return title


def _inline_ids(text: str) -> set[int]:
    citations = set()
    for label in _CITATION.findall(text):
        if len(label) > _MAX_CITATION_DIGITS:
            raise ValueError("An inline citation ID exceeds the supported range")
        citations.add(int(label))
    return citations


def _node_id(path: tuple[str, ...]) -> str:
    return hashlib.sha256(json.dumps(path).encode("utf-8")).hexdigest()[:16]


class KnowledgeBase:
    """Store, reorganize, and render a hierarchy of sourced knowledge."""

    def __init__(self, topic: str):
        self.root = KnowledgeNode(_topic_title(topic))
        self._sources: dict[int, str] = {}

    def register_source(self, source_id: int, url: str) -> None:
        if type(source_id) is not int or source_id < 1 or source_id >= 10**_MAX_CITATION_DIGITS:
            raise ValueError("Source IDs must be positive integers within the citation range")
        if not SourceCurator.credibility_score(url):
            raise ValueError("A source requires a valid HTTP or HTTPS URL")
        if source_id in self._sources and self._sources[source_id] != url:
            raise ValueError(f"Source ID {source_id} is already registered")
        self._sources[source_id] = url

    def insert_from_outline_string(self, outline: str) -> int:
        """Insert Markdown headings atomically and reject duplicate sibling titles."""
        lines = [line.strip() for line in outline.splitlines() if line.strip()]
        if not lines:
            return 0
        staging = deepcopy(self.root)
        first = _HEADING.fullmatch(lines[0])
        base = 1
        if first is not None:
            marks, title = first.groups()
            if marks == "#" and title.casefold() == self.root.title.casefold():
                lines = lines[1:]
                base = 2
            else:
                base = min(len(marks), 2)

        parents: list[tuple[int, KnowledgeNode]] = [(base - 1, staging)]
        added = 0
        for line in lines:
            parsed = _HEADING.fullmatch(line)
            if parsed is None:
                raise ValueError("An outline line must be a Markdown heading")
            marks, title = parsed.groups()
            level = len(marks)
            while len(parents) > 1 and parents[-1][0] >= level:
                parents.pop()
            prior_level, parent = parents[-1]
            if level != prior_level + 1:
                raise ValueError(f"Outline skips a heading level at {title}")
            key = title.casefold()
            if key in parent.children:
                raise ValueError(f"Duplicate outline section: {title}")
            node = KnowledgeNode(title)
            parent.children[key] = node
            parents.append((level, node))
            added += 1
        self.root = staging
        return added

    def insert_information(
        self, path: Sequence[str], summary: str, *, citation_ids: Sequence[int] = (),
    ) -> None:
        node = self.root
        for name in path:
            child = node.children.get(name.casefold())
            if child is None:
                raise ValueError(f"Unknown outline section: {name}")
            node = child
        if any(type(identifier) is not int or identifier < 1 for identifier in citation_ids):
            raise ValueError("Explicit citation IDs must be positive integers")
        node.summary = "\n\n".join(part for part in (node.summary, summary.strip()) if part)
        node.citation_ids = tuple(sorted(set(node.citation_ids).union(citation_ids)))

    def _walk(self) -> Iterator[tuple[tuple[str, ...], KnowledgeNode]]:
        stack = [((self.root.title,), self.root)]
        while stack:
            path, node = stack.pop()
            yield path, node
            stack.extend(((*path, child.title), child) for child in reversed(node.children.values()))

    def trim_empty_leaf_nodes(self) -> int:
        removed = 0
        for _, parent in reversed(tuple(self._walk())):
            for key, child in tuple(parent.children.items()):
                if not (child.children or child.summary or child.citation_ids or _CITATION.search(child.title)):
                    del parent.children[key]
                    removed += 1
        return removed

    def merge_single_child_nodes(self) -> int:
        merged = 0
        for _, parent in reversed(tuple(self._walk())):
            updated: dict[str, KnowledgeNode] = {}
            for key, node in parent.children.items():
                if len(node.children) == 1:
                    child = next(iter(node.children.values()))
                    title = f"{node.title} / {child.title}"
                    combined_key = title.casefold()
                    if combined_key not in parent.children and combined_key not in updated:
                        node = KnowledgeNode(
                            title,
                            "\n\n".join(part for part in (node.summary, child.summary) if part),
                            tuple(sorted(set(node.citation_ids).union(child.citation_ids))),
                            child.children,
                        )
                        key = combined_key
                        merged += 1
                updated[key] = node
            parent.children = updated
        return merged

    def reorganize(self) -> tuple[int, int]:
        """Prune empty leaves and combine related single-child headings."""
        return self.trim_empty_leaf_nodes(), self.merge_single_child_nodes()

    def to_nodes(self) -> tuple[KnowledgeNodeDTO, ...]:
        return tuple(
            KnowledgeNodeDTO(
                _node_id(path), node.title, path,
                tuple(sorted(set(node.citation_ids) | _inline_ids(node.title) | _inline_ids(node.summary))),
                node.summary,
                tuple(_node_id((*path, child.title)) for child in node.children.values()),
            )
            for path, node in self._walk()
        )

    def to_report(self) -> str:
        """Render headings and cited evidence after checking every inline source ID."""
        sections = []
        cited: set[int] = set()
        for path, node in self._walk():
            seen = _inline_ids(node.title) | _inline_ids(node.summary)
            missing_inline = sorted(set(node.citation_ids) - seen)
            cited.update(seen)
            cited.update(node.citation_ids)
            sections.append(f"{'#' * len(path)} {node.title}")
            supplements = " ".join(f"[{identifier}]" for identifier in missing_inline)
            body = " ".join(part for part in (node.summary, supplements) if part)
            if body:
                sections.append(body)
        dangling = sorted(cited - self._sources.keys())
        if dangling:
            raise ValueError(f"Unregistered citation IDs: {', '.join(map(str, dangling))}")
        if cited:
            sources = "\n".join(f"- [{identifier}] {self._sources[identifier]}" for identifier in sorted(cited))
            sections.extend(("## Sources", sources))
        return "\n\n".join(sections) + "\n"


_PERSONAS = (
    ResearchPersona("Security Auditor", "security access controls and authorization"),
    ResearchPersona("State/DB Architect", "state storage transactions and persistence"),
    ResearchPersona("Boundary QA", "boundary null empty and invalid inputs"),
    ResearchPersona("Reliability SRE", "reliability recovery availability and uptime"),
    ResearchPersona("End-User Advocate", "user outcomes visibility and ease of use"),
)


class PersonaGenerator:
    """Supply complementary QA perspectives for a research topic."""

    def generate(self, topic: str) -> tuple[ResearchPersona, ...]:
        _topic_title(topic)
        return _PERSONAS


class SimulatedExpertInterview:
    """Select supplied evidence for each perspective without synthesizing new claims."""

    def conduct(
        self, topic: str, personas: Sequence[ResearchPersona], sources: Sequence[InterviewSource],
    ) -> tuple[ConversationTurn, ...]:
        topic = _topic_title(topic)
        available = tuple(source for source in sources if source.excerpt.strip())
        turns = []
        for persona in personas:
            question = f"How does {topic} affect {persona.focus}?"
            if not available:
                turns.append(ConversationTurn(persona, question, "No supplied evidence addresses this question.", ()))
                continue
            focus_words = set(_WORD.findall(persona.focus.casefold())) - {"and", "of"}
            best = min(
                available,
                key=lambda source: (
                    -len(focus_words.intersection(_WORD.findall(source.excerpt.casefold()))), source.source_id,
                ),
            )
            turns.append(ConversationTurn(persona, question, f"{best.excerpt.strip()} [{best.source_id}]", (best.source_id,)))
        return tuple(turns)


class StormKnowledgeSynthesizer:
    """Compose perspective interviews and citation-checked outline sections."""

    def synthesize(
        self, topic: str, sources: Sequence[InterviewSource], *, outline: str = "",
    ) -> StormSynthesisDTO:
        knowledge = KnowledgeBase(topic)
        personas = PersonaGenerator().generate(topic)
        for source in sources:
            knowledge.register_source(source.source_id, source.url)
        if not outline.strip():
            outline = "\n".join(f"## {persona.name}" for persona in personas)
        knowledge.insert_from_outline_string(outline)
        paths = tuple((node.title,) for node in knowledge.root.children.values()) or ((),)
        turns = SimulatedExpertInterview().conduct(topic, personas, sources)
        for index, turn in enumerate(turns):
            knowledge.insert_information(
                paths[index % len(paths)], f"**{turn.question}**\n\n{turn.answer}", citation_ids=turn.citation_ids,
            )
        knowledge.reorganize()
        report = knowledge.to_report()
        nodes = knowledge.to_nodes()
        verified = {identifier for node in nodes for identifier in node.citation_ids}
        return StormSynthesisDTO(len(personas), len(nodes), len(verified), report, turns)

    def synthesize_from_learnings(
        self, topic: str, learnings: Sequence[ResearchLearningDTO], *, outline: str = "",
    ) -> StormSynthesisDTO:
        excerpts: dict[str, dict[str, None]] = {}
        for learning in learnings:
            text = learning.learning
            for url in reversed(learning.citations):
                text = text.removesuffix(f" [{url}]")
            for url in learning.citations:
                excerpts.setdefault(url, {})[text] = None
        sources = tuple(
            InterviewSource(index, url, " ".join(notes))
            for index, (url, notes) in enumerate(excerpts.items(), start=1)
        )
        return self.synthesize(topic, sources, outline=outline)


def _source_from_payload(source: object) -> InterviewSource:
    if not isinstance(source, dict) or type(source.get("source_id")) is not int:
        raise ValueError("Each source requires an integer source_id")
    if not all(isinstance(source.get(key), str) for key in ("url", "excerpt")):
        raise ValueError("Each source requires string url and excerpt fields")
    return InterviewSource(source["source_id"], source["url"], source["excerpt"])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the report and interview ledger as JSON")
    args = parser.parse_args(argv)
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict) or not isinstance(request.get("topic"), str):
            raise ValueError("Input requires a topic string")
        sources, outline = request.get("sources", []), request.get("outline", "")
        if not isinstance(sources, list) or not isinstance(outline, str):
            raise ValueError("sources must be an array and outline must be text")
        result = StormKnowledgeSynthesizer().synthesize(
            request["topic"], tuple(_source_from_payload(source) for source in sources), outline=outline,
        )
    except (ValueError, RecursionError) as error:
        print(json.dumps({"error": str(error)}) if args.json else str(error))
        return 2
    print(json.dumps(asdict(result)) if args.json else result.report.rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
