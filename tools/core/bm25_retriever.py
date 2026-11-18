#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/core/bm25_retriever.py — Zero-Dependency Pure Python BM25 Knowledge Retriever
Inspired by nextlevelbuilder/ui-ux-pro-max-skill core.py algorithm.
Enables instant sub-millisecond retrieval of guidelines, rules, and QA patterns
with zero external dependencies and guaranteed < 300 character truncation (targeted context reduction).
100% UTF-8 No BOM.
"""
from __future__ import annotations

import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from typing import Any, Dict, List, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

TRUNCATE_AT: int = 300

# Common English / QA stopwords
STOPWORDS: set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with",
    "by", "of", "from", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "this", "that", "these",
    "those", "it", "its", "as", "if", "each", "which", "into", "than", "then"
}

# Domain acronyms & synonym expansion mapping
SYNONYMS: Dict[str, List[str]] = {
    "pom": ["page", "object", "model", "locator"],
    "a11y": ["accessibility", "wcag", "aria", "contrast"],
    "perf": ["performance", "latency", "p95", "throughput", "jmeter", "k6"],
    "sec": ["security", "credential", "sarif", "cwe", "vuln"],
    "fsm": ["finite", "state", "machine", "stage", "lifecycle"],
    "dod": ["definition", "done", "gate", "verify", "quality"],
    "ast": ["abstract", "syntax", "tree", "mutation", "linter"],
}


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase alphanumeric tokens, filtering stopwords."""
    if not text:
        return []
    words = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    tokens: List[str] = []
    for w in words:
        if len(w) > 1 and w not in STOPWORDS:
            tokens.append(w)
            if w in SYNONYMS:
                tokens.extend(SYNONYMS[w])
    return tokens


def char_ngrams(text: str, n_sizes: Tuple[int, ...] = (3, 4)) -> set[str]:
    """Extracts character n-grams from text for dense typo-tolerant matching."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", " ", text.lower()).strip()
    ngrams: set[str] = set()
    for word in cleaned.split():
        if len(word) < 3:
            ngrams.add(word)
            continue
        for n in n_sizes:
            for i in range(len(word) - n + 1):
                ngrams.add(word[i:i + n])
    return ngrams


class BM25Document:
    """Represents an indexed document with precomputed tokens and character n-grams."""

    def __init__(self, doc_id: str, title: str, content: str, source: str = ""):
        self.doc_id = doc_id
        self.title = title
        self.content = content
        self.source = source
        self.tokens = tokenize(f"{title} {content}")
        self.length = len(self.tokens)
        self.term_freqs = Counter(self.tokens)
        self.ngrams = char_ngrams(f"{title} {content[:1000]}")

    def snippet(self, max_len: int = TRUNCATE_AT) -> str:
        """Returns a trimmed snippet bounded by max_len."""
        cleaned = re.sub(r"\s+", " ", self.content).strip()
        if len(cleaned) <= max_len:
            return cleaned
        return cleaned[:max_len].rstrip() + "..."


class BM25Index:
    """
    Rank BM25 search index using the Okapi BM25 formula:
    IDF(q) = ln((N - n(q) + 0.5) / (n(q) + 0.5) + 1)
    Score = sum(IDF(q) * (f(q, D) * (k1 + 1)) / (f(q, D) + k1 * (1 - b + b * (|D| / avgdl))))
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[BM25Document] = []
        self.doc_count: int = 0
        self.avg_doc_len: float = 0.0
        self.doc_freqs: Counter[str] = Counter()
        self.idf_cache: Dict[str, float] = {}

    def add_document(self, doc_id: str, title: str, content: str, source: str = "") -> None:
        """Adds a single document to the index."""
        doc = BM25Document(doc_id, title, content, source)
        self.documents.append(doc)
        self.doc_count = len(self.documents)

    def build(self) -> None:
        """Finalizes the index, computes average document length and IDF scores."""
        self.doc_freqs.clear()
        total_len = 0
        for doc in self.documents:
            total_len += doc.length
            for token in set(doc.tokens):
                self.doc_freqs[token] += 1

        self.avg_doc_len = (total_len / self.doc_count) if self.doc_count > 0 else 0.0

        # Precompute IDF
        self.idf_cache.clear()
        for token, df in self.doc_freqs.items():
            # Robertson-Spärck Jones IDF formula with +1 smoothing
            idf = math.log(((self.doc_count - df + 0.5) / (df + 0.5)) + 1.0)
            self.idf_cache[token] = max(idf, 0.0)

    def search(
        self, query: str, top_k: int = 3, truncate_at: int = TRUNCATE_AT
    ) -> List[Dict[str, Any]]:
        """Searches documents matching the query and returns top_k ranked results."""
        if not self.documents:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: List[Tuple[float, BM25Document]] = []
        for doc in self.documents:
            if doc.length == 0:
                continue
            score = 0.0
            doc_len_ratio = doc.length / self.avg_doc_len if self.avg_doc_len > 0 else 1.0
            len_norm = 1.0 - self.b + self.b * doc_len_ratio

            for q in query_tokens:
                if q in doc.term_freqs:
                    freq = doc.term_freqs[q]
                    idf = self.idf_cache.get(q, 0.0)
                    numerator = freq * (self.k1 + 1.0)
                    denominator = freq + self.k1 * len_norm
                    score += idf * (numerator / denominator)

            if score > 0.0:
                scores.append((score, doc))

        scores.sort(key=lambda x: x[0], reverse=True)

        results: List[Dict[str, Any]] = []
        for rank, (score, doc) in enumerate(scores[:top_k], start=1):
            results.append({
                "rank": rank,
                "score": round(score, 4),
                "doc_id": doc.doc_id,
                "title": doc.title,
                "snippet": doc.snippet(truncate_at),
                "source": doc.source,
            })
        return results

    def hybrid_search(
        self, query: str, top_k: int = 3, rrf_k: int = 60, truncate_at: int = TRUNCATE_AT
    ) -> List[Dict[str, Any]]:
        """
        Dual-Leg Hybrid Retrieval using Okapi BM25 and Character N-Gram Jaccard overlap,
        fused via Reciprocal Rank Fusion (RRF, default k=60).
        Inspired by ECC context-retrieval.js.
        """
        if not self.documents:
            return []

        # 1. Sparse BM25 Search Leg
        bm25_raw = self.search(query, top_k=len(self.documents), truncate_at=truncate_at)
        bm25_ranks: Dict[str, int] = {item["doc_id"]: item["rank"] for item in bm25_raw}

        # 2. Dense Character N-Gram Leg (typo-tolerant)
        query_ngrams = char_ngrams(query)
        ngram_scores: List[Tuple[float, BM25Document]] = []
        if query_ngrams:
            for doc in self.documents:
                if not doc.ngrams:
                    continue
                intersection = len(query_ngrams & doc.ngrams)
                union = len(query_ngrams | doc.ngrams)
                jaccard = (intersection / union) if union > 0 else 0.0
                if jaccard > 0.0:
                    ngram_scores.append((jaccard, doc))

        ngram_scores.sort(key=lambda x: x[0], reverse=True)
        ngram_ranks: Dict[str, int] = {doc.doc_id: rank for rank, (_, doc) in enumerate(ngram_scores, start=1)}

        # 3. Reciprocal Rank Fusion (RRF)
        all_doc_ids = set(bm25_ranks.keys()) | set(ngram_ranks.keys())
        rrf_scored: List[Tuple[float, str]] = []

        for did in all_doc_ids:
            score = 0.0
            if did in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[did])
            if did in ngram_ranks:
                score += 1.0 / (rrf_k + ngram_ranks[did])
            rrf_scored.append((score, did))

        rrf_scored.sort(key=lambda x: x[0], reverse=True)

        # 4. Format Results
        doc_map = {d.doc_id: d for d in self.documents}
        results: List[Dict[str, Any]] = []
        for rank, (score, did) in enumerate(rrf_scored[:top_k], start=1):
            doc = doc_map.get(did)
            if not doc:
                continue
            results.append({
                "rank": rank,
                "score": round(score, 6),
                "doc_id": doc.doc_id,
                "title": doc.title,
                "snippet": doc.snippet(truncate_at),
                "source": doc.source,
                "bm25_rank": bm25_ranks.get(did),
                "ngram_rank": ngram_ranks.get(did),
            })
        return results


def index_directory(dir_path: str, extensions: Tuple[str, ...] = (".md", ".txt")) -> BM25Index:
    """Indexes all files with matching extensions under dir_path."""
    index = BM25Index()
    if not os.path.exists(dir_path):
        return index

    for root, _, files in os.walk(dir_path):
        for f in files:
            if any(f.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, f)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as fp:
                        content = fp.read()
                    rel_path = os.path.relpath(full_path, dir_path)
                    title = f.replace(".md", "").replace("_", " ").title()
                    index.add_document(doc_id=rel_path, title=title, content=content, source=full_path)
                except OSError:
                    continue

    index.build()
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="BM25 Knowledge Retriever for Synapse Hub")
    parser.add_argument("--query", "-q", type=str, required=True, help="Search query string")
    parser.add_argument("--dir", "-d", type=str, default=".agents/rules", help="Directory to search (default: .agents/rules)")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of results to return (default: 3)")
    parser.add_argument("--hybrid", action="store_true", help="Enable Dual-Leg BM25 + Character N-Gram RRF hybrid search")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    index = index_directory(args.dir)
    if args.hybrid:
        results = index.hybrid_search(args.query, top_k=args.top_k)
    else:
        results = index.search(args.query, top_k=args.top_k)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"🔍 BM25 Search Results for: '{args.query}' in '{args.dir}' (Found: {len(results)})")
        for res in results:
            print(f"\n[#{res['rank']}] {res['title']} (Score: {res['score']}) -> {res['doc_id']}")
            print(f"   {res['snippet']}")


if __name__ == "__main__":
    main()
