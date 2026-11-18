# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_bm25_retriever.py — Unit tests for tools.core.bm25_retriever
"""

import os
import tempfile
from tools.core.bm25_retriever import (
    BM25Index,
    BM25Document,
    tokenize,
    index_directory,
)


def test_tokenize():
    tokens = tokenize("Testing the Clean POM architecture with 100% UTF-8!")
    assert "testing" in tokens
    assert "clean" in tokens
    assert "pom" in tokens
    # Synonym expansion
    assert "page" in tokens
    assert "object" in tokens
    assert "model" in tokens
    # Stopword filtered
    assert "the" not in tokens
    assert "with" not in tokens


def test_bm25_document_snippet():
    long_text = "word " * 100
    doc = BM25Document(doc_id="d1", title="Title", content=long_text)
    snippet = doc.snippet(max_len=50)
    assert len(snippet) <= 53
    assert snippet.endswith("...")


def test_bm25_index_search():
    index = BM25Index()
    index.add_document("doc1", "Clean POM", "All locators belong to Page Classes extending BasePage.")
    index.add_document("doc2", "Performance Testing", "JMeter and k6 load tests running against endpoints.")
    index.add_document("doc3", "Security Audit", "Scanning secrets and checking CWE-798 vulnerabilities.")
    index.build()

    results_pom = index.search("locators and BasePage", top_k=1)
    assert len(results_pom) == 1
    assert results_pom[0]["doc_id"] == "doc1"
    assert results_pom[0]["score"] > 0

    results_sec = index.search("security scan CWE", top_k=1)
    assert len(results_sec) == 1
    assert results_sec[0]["doc_id"] == "doc3"

    # Test Dual-Leg Hybrid Search with typo-tolerance
    results_hybrid = index.hybrid_search("locatr BasePage", top_k=1)
    assert len(results_hybrid) == 1
    assert results_hybrid[0]["doc_id"] == "doc1"
    assert "bm25_rank" in results_hybrid[0]
    assert "ngram_rank" in results_hybrid[0]


def test_index_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = os.path.join(tmpdir, "rule1.md")
        with open(f1, "w", encoding="utf-8") as fp:
            fp.write("# Rule One\nClean POM rules and smart wait.")

        f2 = os.path.join(tmpdir, "rule2.md")
        with open(f2, "w", encoding="utf-8") as fp:
            fp.write("# Rule Two\nPerformance SLA metrics and JMeter profiles.")

        index = index_directory(tmpdir)
        assert index.doc_count == 2
        results = index.search("smart wait Clean POM", top_k=1)
        assert len(results) == 1
        assert "rule1.md" in results[0]["doc_id"]
