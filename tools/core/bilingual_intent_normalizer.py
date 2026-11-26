#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/bilingual_intent_normalizer.py — Zero-Token Bilingual (VI/EN) Intent Normalizer
------------------------------------------------------------------------------------------
Pure Python standard-library O(N) normalizer translating Vietnamese and colloquial QA
phrases, negation markers, and /slash commands into canonical English technical tokens.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import re
import sys
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple
import unicodedata

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

MAX_INPUT_CHARS: int = 8192

_VIETNAMESE_DIACRITIC_RE = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)

# Matches standalone /slash-skill commands; excludes URLs (https://...) and Unix paths (/usr/bin/...)
_SLASH_SKILL_RE = re.compile(
    r"(?:^|\s)/([a-z][a-z0-9_-]{1,48})(?=\s|$|[.,:;!?])",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")
_FOLDED_WORD_RE = re.compile(r"[a-z0-9]+")

# Inline negation replacements applied on folded text so downstream negation-aware parsers
# (e.g. super_plan_engine.check_ambiguities) detect negated options right before the target noun.
_VI_NEGATION_RE = re.compile(
    r"\b(?:khong\s+su\s+dung|khong\s+dung|khong\s+xai|khong\s+can|khong\s+chon|"
    r"tranh\s+su\s+dung|tranh\s+dung|bo\s+qua|dung\s+su\s+dung|dung\s+dung|dung\s+xai|dung\s+chon|"
    r"cam\s+su\s+dung|cam\s+dung|loai\s+tru|thay\s+vi)\b",
    re.IGNORECASE,
)

# Immutable bilingual QA & software architecture phrase lexicon (folded ASCII -> canonical EN tokens).
# Multi-word phrases avoid English word collisions while supporting both accented and unaccented Vietnamese.
_RAW_PHRASE_LEXICON: Dict[str, Tuple[str, ...]] = {
    # Concurrency / Race Conditions / Payments / Database Locks
    "thanh toan": ("payment", "transaction"),
    "giao dich": ("transaction", "atomic"),
    "bam dup": ("double", "double_click", "duplicate", "idempotent", "race", "condition"),
    "click dup": ("double", "double_click", "duplicate", "idempotent", "race", "condition"),
    "nhan dup": ("double", "double_click", "duplicate", "idempotent", "race", "condition"),
    "bam 2 lan": ("double", "double_click", "duplicate", "idempotent", "race", "condition"),
    "bam hai lan": ("double", "double_click", "duplicate", "idempotent", "race", "condition"),
    "nhan hai lan": ("double", "double_click", "duplicate", "idempotent", "race", "condition"),
    "tru tien 2 lan": ("payment", "double", "duplicate", "idempotent", "race", "transaction"),
    "tru tien hai lan": ("payment", "double", "duplicate", "idempotent", "race", "transaction"),
    "tru 2 lan": ("payment", "double", "duplicate", "idempotent", "race"),
    "tru hai lan": ("payment", "double", "duplicate", "idempotent", "race"),
    "mat tien": ("payment", "transaction", "integrity"),
    "dup tien": ("payment", "double", "duplicate", "idempotent", "race"),
    "cung luc": ("concurrency", "concurrent", "race", "parallel"),
    "dong loat": ("concurrency", "parallel", "load"),
    "ket cung": ("deadlock", "lock", "concurrency"),
    "treo cung": ("deadlock", "lock", "timeout"),
    "chong cheo": ("race", "concurrency", "conflict"),
    "ghi de": ("overwrite", "race", "concurrency", "lock"),
    "double click": ("double", "double_click", "duplicate", "idempotent", "race"),
    "trung lap": ("duplicate", "idempotent"),
    "lap giao dich": ("duplicate", "idempotent", "transaction"),
    "trung giao dich": ("duplicate", "idempotent", "transaction"),
    "dong thoi": ("concurrency", "concurrent", "race", "parallel"),
    "song song": ("parallel", "concurrency"),
    "nhieu luong": ("thread", "concurrency", "parallel", "race"),
    "da luong": ("thread", "concurrency", "parallel", "race"),
    "xung dot luong": ("race", "condition", "concurrency", "deadlock"),
    "tranh chap": ("race", "condition", "concurrency"),
    "dua tranh": ("race", "condition", "concurrency"),
    "khoa co so du lieu": ("database", "db", "lock", "deadlock", "transaction"),
    "khoa csdl": ("database", "db", "lock", "deadlock", "transaction"),
    "khoa db": ("database", "db", "lock", "deadlock", "transaction"),
    "khoa bang": ("database", "lock", "deadlock", "transaction"),
    "khoa cheo": ("deadlock", "lock", "race", "condition"),
    "be tac": ("deadlock", "lock"),
    "co so du lieu": ("database", "db", "sql", "schema"),
    "csdl": ("database", "db", "sql", "schema"),
    "bat dong bo": ("async", "concurrency"),
    "hang doi": ("queue", "async"),
    "hoan tac": ("rollback", "transaction"),
    "bo nho dem": ("cache", "storage"),
    "luu tru": ("storage", "persist"),
    # Authentication / Identity / Security
    "xac thuc": ("auth", "authentication", "security"),
    "dang nhap": ("login", "auth", "session"),
    "phan quyen": ("authorization", "permission", "auth", "security"),
    "quyen truy cap": ("permission", "authorization", "auth", "security"),
    "phien dang nhap": ("session", "auth", "cookie"),
    "phien lam viec": ("session", "auth"),
    "rot phien": ("session", "auth", "token", "refresh"),
    "vang ra": ("session", "auth", "logout"),
    "lam moi token": ("token", "refresh", "auth", "session", "jwt"),
    "cap lai token": ("token", "refresh", "auth", "session", "jwt"),
    "het han token": ("token", "refresh", "auth", "jwt"),
    "bao mat": ("security", "owasp", "dast"),
    "lo hong": ("security", "vulnerability", "owasp"),
    "tiem ma": ("injection", "security", "owasp"),
    "mat khau": ("credential", "secret", "auth"),
    "thong tin dang nhap": ("credential", "auth", "login"),
    # API / Contracts / Mocking
    "hop dong api": ("api", "contract", "openapi", "schema", "endpoint"),
    "dac ta api": ("api", "openapi", "swagger", "spec", "schema"),
    "ma tran kiem thu": ("matrix", "test", "boundary"),
    "kiem thu api": ("api", "endpoint", "contract", "test"),
    "goi api": ("api", "endpoint", "network"),
    "gia lap mang": ("mock", "intercept", "network", "route", "stub"),
    "gia lap api": ("mock", "intercept", "network", "api", "stub"),
    "gia lap": ("mock", "stub"),
    "chan mang": ("intercept", "network", "mock", "route"),
    "sai lech schema": ("schema", "drift", "contract", "api"),
    "luoc do": ("schema", "contract"),
    # Performance / Load / Latency / SLA
    "hieu nang": ("performance", "latency", "load", "sla"),
    "kiem thu tai": ("load", "stress", "performance", "k6", "jmeter"),
    "chiu tai": ("load", "stress", "performance", "saturation"),
    "tai cao": ("load", "stress", "throughput", "performance"),
    "do tre": ("latency", "slow", "performance"),
    "phan hoi cham": ("latency", "slow", "performance"),
    "bi cham": ("slow", "latency", "performance"),
    "nghen co chai": ("bottleneck", "saturation", "latency", "performance"),
    "qua tai": ("saturation", "backpressure", "load", "rate"),
    "gioi han toc do": ("rate", "limit", "backpressure", "throttling"),
    "het thoi gian cho": ("timeout", "latency"),
    # Testing / Flaky / Healing / Transpiler / Quality Gates / RCA
    "chap chon": ("flaky", "non_deterministic", "quarantine"),
    "khong on dinh": ("flaky", "non_deterministic", "quarantine"),
    "luc duoc luc khong": ("flaky", "non_deterministic", "quarantine"),
    "luc pass luc fail": ("flaky", "non_deterministic", "quarantine"),
    "hay bi fail": ("flaky", "non_deterministic", "quarantine"),
    "cho tinh": ("sleep", "wait", "flaky"),
    "ngu tinh": ("sleep", "wait", "flaky"),
    "tu sua locator": ("heal", "healing", "self_healing", "locator"),
    "tu phuc hoi": ("heal", "healing", "self_healing"),
    "chua lanh": ("heal", "healing"),
    "chon phan tu": ("locator", "selector", "dom", "aom"),
    "khong tim thay nut": ("locator", "self_healing", "dom", "aom"),
    "kiem thu tu dong": ("automation", "e2e", "test", "playwright"),
    "tu dong hoa": ("automation", "e2e", "test"),
    "mo hinh trang": ("pom", "page", "locator"),
    "lop trang": ("pom", "page", "locator"),
    "chuyen doi ma": ("transpile", "transpiler"),
    "bien dich cheo": ("transpile", "transpiler"),
    "chuyen doi kich ban": ("transpile", "transpiler"),
    "kiem thu dot bien": ("mutation", "mutant", "micro_mutator"),
    "dot bien": ("mutation", "mutant"),
    "nguyen nhan goc": ("root", "cause", "rca", "autopsy"),
    "phan tich nguyen nhan": ("root", "cause", "rca", "autopsy"),
    "kham nghiem loi": ("autopsy", "rca", "pinpoint"),
    "tai cau truc": ("refactor", "redesign", "architecture"),
    "thiet ke lai": ("redesign", "refactor", "architecture"),
    "kien truc": ("architecture", "design"),
    "lap ke hoach": ("plan", "roadmap", "design"),
    "len ke hoach": ("plan", "roadmap", "design"),
    "ke hoach": ("plan", "roadmap", "design"),
    "cong chat luong": ("gate", "verification", "verify_all", "dod"),
    "bat bien": ("invariant", "verification"),
    "kiem chung": ("verification", "verify"),
    "dinh dang": ("format", "lint"),
    "trang thai": ("status", "state"),
    "tro nang": ("accessibility", "wcag", "a11y"),
    "xuat excel": ("export", "excel"),
    "du lieu": ("data",),
    "don dep": ("teardown", "cleanup"),
    "tap tin": ("file", "files"),
    "do chi so": ("measure", "perf", "cwv"),
    "chi so": ("metrics",),
    "du lieu gia": ("synthetic", "data", "generator"),
    "tao du lieu": ("generate", "synthetic", "data"),
    "sua loi": ("fix", "heal"),
    "va loi": ("fix", "patch"),
    "ra soat": ("audit", "scan"),
    "kiem tra": ("check", "verify"),
    "thiet ke": ("design", "create"),
    "sinh ma tran": ("generate", "matrix"),
    "tao ma tran": ("generate", "matrix"),
}

PHRASE_LEXICON: Mapping[str, Tuple[str, ...]] = MappingProxyType(_RAW_PHRASE_LEXICON)
MAX_NGRAM_SIZE: int = max(len(k.split()) for k in _RAW_PHRASE_LEXICON)

# Pure Vietnamese multi-word signals used to detect unaccented Vietnamese prompts accurately
_UNACCENTED_VI_SIGNALS: frozenset[str] = frozenset(
    k for k in _RAW_PHRASE_LEXICON if k != "double click"
)

# Unambiguous Vietnamese folded words (excluding common English tokens) used to detect
# unaccented freeform Vietnamese prose when >= 2 markers co-occur.
_UNACCENTED_VI_MARKERS: frozenset[str] = frozenset({
    "khong", "duoc", "gium", "giup", "chinh", "nhieu", "nguoi", "muot", "giat",
    "chuyen", "kiem", "thiet", "khoa", "phien", "nhap", "thuc", "luong", "giao",
    "dich", "thanh", "toan", "nghen", "nguyen", "vuot", "quyen", "truoc", "chay",
    "sua", "lam", "phan", "doan", "cho", "viec", "thay", "tranh", "chua", "xong",
    "nhe", "nha", "vay", "hom", "gio", "hang", "chiu", "kho", "nhung", "cac",
    "cua", "nay", "cai", "loi", "sai", "treo", "cham", "qua", "tai", "sao",
})

# English domain anchors that disambiguate mixed VI/EN prompts even if Vietnamese words are colloquial
_KNOWN_EN_DOMAIN_TOKENS: frozenset[str] = frozenset({
    "api", "auth", "authentication", "authorization", "autopsy", "aom", "ast",
    "backpressure", "bdd", "cache", "concurrency", "concurrent", "contract",
    "cookie", "csv", "cwv", "cypress", "database", "dast", "db", "deadlock", "dom", "e2e",
    "endpoint", "excel", "file", "files", "flaky", "fuzz", "fuzzer", "gate", "gherkin", "graphql",
    "groovy", "har", "heal", "healing", "http", "idempotent", "invariant",
    "jmeter", "jmx", "jtl", "junit", "jwt", "k6", "katalon", "latency", "lcp", "lint",
    "linter", "load", "locator", "lock", "locust", "matrix", "migration", "mock",
    "mutant", "mutation", "mutex", "network", "newman", "oauth", "openapi",
    "owasp", "pact", "page", "payment", "pdf", "perf", "performance", "playwright",
    "pom", "postman", "pytest", "quarantine", "queue", "race", "rca", "redis",
    "refactor", "refresh", "rollback", "schema", "security", "selector",
    "selenium", "session", "sla", "sleep", "sqlite", "status", "stress", "stub",
    "swagger", "sync", "test", "thread", "throughput", "timeout", "token",
    "transaction", "transpile", "transpiler", "utf", "verify", "wcag", "xpath",
})

# English colloquial synonym expansions (kept narrow so pure English semantics never drift)
_EN_COLLOQUIAL_EXPANSIONS: Mapping[str, Tuple[str, ...]] = MappingProxyType({
    "double click": ("double", "double_click", "duplicate", "idempotent"),
    "page object": ("pom", "page", "locator"),
    "end to end": ("e2e",),
    "root cause": ("rca", "autopsy"),
    "same time": ("concurrency", "concurrent", "race", "condition", "parallel"),
    "at once": ("concurrency", "concurrent", "parallel"),
    "charged twice": ("payment", "double", "duplicate", "idempotent", "race", "condition", "transaction"),
    "billed twice": ("payment", "double", "duplicate", "idempotent", "race", "condition", "transaction"),
    "submitted twice": ("double", "duplicate", "idempotent", "race", "condition"),
    "clicked twice": ("double", "double_click", "duplicate", "idempotent", "race", "condition"),
    "hit twice": ("double", "duplicate", "idempotent", "race", "condition"),
    "concurrent requests": ("concurrency", "concurrent", "race", "parallel"),
    "deadlocked": ("deadlock", "lock", "concurrency"),
    "locks up": ("deadlock", "lock", "timeout"),
    "freezes": ("deadlock", "lock", "timeout", "saturation"),
    "hangs": ("deadlock", "lock", "timeout"),
    "data race": ("race", "condition", "concurrency"),
    "logged out": ("session", "auth", "token", "refresh"),
    "kicked out": ("session", "auth", "token", "refresh"),
    "session expired": ("session", "auth", "token", "refresh"),
    "token expired": ("token", "refresh", "auth", "jwt"),
    "unauthorized access": ("authorization", "security", "permission", "owasp"),
    "privilege escalation": ("authorization", "security", "permission", "owasp"),
    "pass sometimes": ("flaky", "non_deterministic", "quarantine"),
    "fail randomly": ("flaky", "non_deterministic", "quarantine"),
    "fails intermittently": ("flaky", "non_deterministic", "quarantine"),
    "intermittent failure": ("flaky", "non_deterministic", "quarantine"),
    "not deterministic": ("flaky", "non_deterministic", "quarantine"),
    "element not found": ("locator", "self_healing", "dom", "aom"),
    "button not found": ("locator", "self_healing", "dom", "aom"),
    "broken selector": ("locator", "self_healing", "selector"),
    "broken locator": ("locator", "self_healing", "locator"),
    "slow down": ("slow", "latency", "performance"),
    "timing out": ("timeout", "latency", "performance"),
    "high load": ("load", "stress", "saturation", "performance"),
    "memory leak": ("memory", "leak", "performance"),
    "too slow": ("slow", "latency", "performance"),
    "mock server": ("mock", "intercept", "network", "stub"),
    "stub api": ("mock", "api", "stub", "network"),
    "schema mismatch": ("schema", "drift", "contract", "api"),
})

_VAGUE_EN_PHRASE_RE = re.compile(
    r"\b(?:(?:that|this|the)\s+(?:broken|messy|weird|glitched|buggy|old|whole|entire)?\s*(?:thing|part|stuff|piece|spot|glitch)|"
    r"something\s+(?:is\s+)?(?:broken|wrong|weird|off)|"
    r"keeps\s+(?:breaking|glitching|acting\s+weird)|"
    r"from\s+(?:yesterday|earlier|last\s+time)|"
    r"make\s+it\s+(?:smoother|better|work))\b",
    re.IGNORECASE,
)


def build_clarification_questions(raw_text: str = "") -> Tuple[Dict[str, Any], ...]:
    """Builds structured domain-disambiguation MCQs when bilingual intent lacks technical anchors."""
    preview = (raw_text or "").strip()[:80]
    suffix = f" for '{preview}'" if preview else ""
    return (
        {
            "category": "context_clarification",
            "question": f"Which technical domain or layer is affected{suffix}?",
            "options": [
                "Backend concurrency, database locks, or payment/transaction state",
                "Web UI automation, flaky waits, or Page Object locators (Playwright/Selenium)",
                "API contract, OpenAPI schema, or network mocking",
                "Authentication, JWT/session refresh, or security audit",
                "Performance, load saturation, or latency SLA",
            ],
            "recommended": None,
            "resolved_by_invariant": False,
            "excluded_by_negation": [],
            "counter_arguments": {},
            "recommended_counter_argument": "",
        },
    )


@dataclass(frozen=True)
class NormalizedIntentDTO:
    """Immutable DTO representing a normalized bilingual user intent."""

    raw_text: str
    canonical_text: str
    canonical_tokens: Tuple[str, ...]
    slash_skill: Optional[str] = None
    has_vietnamese: bool = False
    matched_domain_tokens: Tuple[str, ...] = ()
    unmapped_vietnamese: bool = False
    unmapped_english: bool = False
    needs_clarification: bool = False
    clarifying_questions: Tuple[Dict[str, Any], ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "raw_text": self.raw_text,
            "canonical_text": self.canonical_text,
            "canonical_tokens": list(self.canonical_tokens),
            "slash_skill": self.slash_skill,
            "has_vietnamese": self.has_vietnamese,
            "matched_domain_tokens": list(self.matched_domain_tokens),
            "unmapped_vietnamese": self.unmapped_vietnamese,
            "unmapped_english": self.unmapped_english,
            "needs_clarification": self.needs_clarification,
            "clarifying_questions": list(self.clarifying_questions),
        }


def strip_vietnamese_diacritics(text: str) -> str:
    """Folds Vietnamese diacritics (including đ/Đ) into plain ASCII lowercase text in O(N)."""
    if not text:
        return ""
    replaced = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", replaced)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.lower()


def extract_slash_skill(text: str) -> Optional[str]:
    """Extracts the first explicit /slash-skill invocation, ignoring URLs and Unix paths."""
    if not text:
        return None
    match = _SLASH_SKILL_RE.search(text)
    if not match:
        return None
    return match.group(1).lower()


def normalize_bilingual_intent(text: str) -> NormalizedIntentDTO:
    """Maps Vietnamese & colloquial QA phrases into canonical English technical tokens in O(N) time with 0 LLM tokens."""
    if not isinstance(text, str):
        return NormalizedIntentDTO(
            raw_text="",
            canonical_text="",
            canonical_tokens=(),
            slash_skill=None,
            has_vietnamese=False,
        )

    bounded = text[:MAX_INPUT_CHARS]
    stripped = bounded.strip()
    if not stripped:
        return NormalizedIntentDTO(
            raw_text=text,
            canonical_text="",
            canonical_tokens=(),
            slash_skill=None,
            has_vietnamese=False,
        )

    slash_skill = extract_slash_skill(stripped)
    has_diacritics = bool(_VIETNAMESE_DIACRITIC_RE.search(stripped))
    folded = strip_vietnamese_diacritics(stripped)

    # Apply inline Vietnamese negation rewrite on folded text so downstream negation-aware
    # engines see "without <option>" directly adjacent to the negated noun.
    neg_rewritten_folded = _VI_NEGATION_RE.sub("without", folded)
    has_vi_negation = neg_rewritten_folded != folded

    words = _FOLDED_WORD_RE.findall(folded)
    matched_en_tokens: List[str] = []
    seen_en: set[str] = set()
    has_unaccented_vi = has_vi_negation

    n_words = len(words)
    for i in range(n_words):
        max_len = min(MAX_NGRAM_SIZE, n_words - i)
        for length in range(1, max_len + 1):
            ngram = " ".join(words[i : i + length])
            mapped = PHRASE_LEXICON.get(ngram)
            if mapped is not None:
                if ngram in _UNACCENTED_VI_SIGNALS:
                    has_unaccented_vi = True
                for tok in mapped:
                    if tok not in seen_en:
                        seen_en.add(tok)
                        matched_en_tokens.append(tok)
            colloq = _EN_COLLOQUIAL_EXPANSIONS.get(ngram)
            if colloq is not None:
                for tok in colloq:
                    if tok not in seen_en:
                        seen_en.add(tok)
                        matched_en_tokens.append(tok)

    if not has_unaccented_vi and sum(1 for w in words if w in _UNACCENTED_VI_MARKERS) >= 2:
        has_unaccented_vi = True

    has_vietnamese = has_diacritics or has_unaccented_vi

    # Compose canonical_text: preserve original text; if Vietnamese negation or canonical
    # English tokens were found, append cleanly without mutating ASCII English words.
    extra_parts: List[str] = []
    if has_vi_negation:
        extra_parts.append(neg_rewritten_folded)
    if matched_en_tokens:
        base_ascii_tokens = set(_TOKEN_RE.findall(stripped.lower()))
        new_tokens = [t for t in matched_en_tokens if t not in base_ascii_tokens]
        if new_tokens:
            extra_parts.append(" ".join(new_tokens))

    if extra_parts:
        canonical_text = f"{stripped} {' '.join(extra_parts)}"
    else:
        canonical_text = stripped

    # Extract deterministic, deduplicated canonical ASCII tokens
    tok_list: List[str] = []
    seen_tok: set[str] = set()
    for raw_tok in _TOKEN_RE.findall(canonical_text.lower()):
        if raw_tok not in seen_tok:
            seen_tok.add(raw_tok)
            tok_list.append(raw_tok)

    matched_domain_set = set(matched_en_tokens) | (set(tok_list) & _KNOWN_EN_DOMAIN_TOKENS)
    matched_domain_tokens = tuple(t for t in tok_list if t in matched_domain_set)
    unmapped_vietnamese = bool(
        has_vietnamese
        and not matched_domain_tokens
        and slash_skill is None
        and len(words) >= 2
    )
    unmapped_english = bool(
        not has_vietnamese
        and not matched_domain_tokens
        and slash_skill is None
        and len(words) >= 3
        and _VAGUE_EN_PHRASE_RE.search(stripped)
    )
    needs_clarification = unmapped_vietnamese or unmapped_english
    clarifying_questions = build_clarification_questions(stripped) if needs_clarification else ()

    return NormalizedIntentDTO(
        raw_text=text,
        canonical_text=canonical_text,
        canonical_tokens=tuple(tok_list),
        slash_skill=slash_skill,
        has_vietnamese=has_vietnamese,
        matched_domain_tokens=matched_domain_tokens,
        unmapped_vietnamese=unmapped_vietnamese,
        unmapped_english=unmapped_english,
        needs_clarification=needs_clarification,
        clarifying_questions=clarifying_questions,
    )


def normalize_bilingual_text(text: str) -> str:
    """Convenience helper returning canonical_text for a prompt."""
    return normalize_bilingual_intent(text).canonical_text


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Zero-Token Bilingual (VI/EN) Technical Intent Normalizer"
    )
    parser.add_argument("--text", type=str, required=True, help="Raw user prompt text to normalize")
    parser.add_argument("--json", action="store_true", help="Output JSON DTO")
    args = parser.parse_args(argv)

    dto = normalize_bilingual_intent(args.text)
    if args.json:
        print(json.dumps(dto.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"Has Vietnamese : {dto.has_vietnamese}")
        print(f"Slash Skill    : {dto.slash_skill}")
        print(f"Canonical Text : {dto.canonical_text}")
        print(f"Tokens ({len(dto.canonical_tokens)}): {', '.join(dto.canonical_tokens)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
