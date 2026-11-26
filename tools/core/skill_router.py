#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/skill_router.py — Context-Aware Skill Router (Rule 7 Mechanical Sensor)
----------------------------------------------------------------------------------
Eliminates naive keyword-stuffing false positives in Invariant 7 (Skill-First Hard Blocker).
Instead of matching 27 raw keywords anywhere in the prompt text, this sensor evaluates:
  1. Intent Classification: ACTION vs DIAGNOSTIC vs INQUIRY.
  2. Scope Analysis: Maps targeted/touched file paths to registered skill domains.
  3. Micro-Fix Exemption: Verifies single-line hotfixes do not trigger unwanted context bloat.

Skill-First is triggered ONLY when:
  (Intent == ACTION or DIAGNOSTIC) AND (Touched Files match a Skill Domain OR Explicit Skill Invoked)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import re
import sys
import threading
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_ROOT = os.path.dirname(_SCRIPT_DIR)
_REPO_ROOT = os.path.abspath(os.path.join(_TOOLS_ROOT, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.core.bilingual_intent_normalizer import (
    build_clarification_questions,
    normalize_bilingual_intent,
    strip_vietnamese_diacritics,
)
from tools.core.vietnamese_nlp_utils import canonicalize_vietnamese_orthography
from tools.core.bm25_retriever import BM25Index, ScoreCalibrator, char_ngrams
from tools.core.skill_utterances_registry import SKILL_ROUTE_SPECS, SkillRouteSpec, get_skill_route_spec


@dataclass(frozen=True)
class BoundedRouteMatchDTO:
    """Bounded [0, 1] utterance similarity and calibrated probability for a skill route."""

    skill_id: str
    domain: str
    raw_bounded_score: float
    calibrated_confidence: float
    matched_utterances: Tuple[str, ...]


@dataclass(frozen=True)
class SkillRouteVerdictDTO:
    """Typed Skill-First routing verdict contract."""

    intent: str
    is_triggered: bool
    is_exempt: bool
    recommended_skill: Optional[str]
    skill_md_path: Optional[str]
    score: float = 0.0
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None
    calibrated_confidence: float = 0.0
    matched_utterances: Tuple[str, ...] = ()


MIN_FILELESS_CONFIDENCE_SCORE: int = 4
MIN_UTTERANCE_RAW_SCORE: float = 0.17

_UTTERANCE_INDEX_LOCK = threading.Lock()
_UTTERANCE_ROUTER_SINGLETON: Optional["CalibratedUtteranceRouterIndex"] = None


class CalibratedUtteranceRouterIndex:
    """Thread-safe in-memory bounded BM25 + char-ngram + Platt calibrated utterance index."""

    def __init__(self, specs: Sequence[SkillRouteSpec] = SKILL_ROUTE_SPECS) -> None:
        self.specs: Tuple[SkillRouteSpec, ...] = tuple(specs)
        self.spec_by_id: Dict[str, SkillRouteSpec] = {s.skill_id: s for s in self.specs}
        self.index = BM25Index(k1=1.2, b=0.5)
        self.doc_to_skill: Dict[str, str] = {}
        self.doc_to_utterance: Dict[str, str] = {}
        self.doc_ngrams: Dict[str, Set[str]] = {}

        for spec in self.specs:
            utterances = spec.utterances_en + spec.utterances_vi
            title = spec.skill_id.replace("-", " ")
            for idx, utt in enumerate(utterances):
                doc_id = f"{spec.skill_id}::{idx}"
                self.index.add_document(doc_id=doc_id, title=title, content=utt, source=spec.domain)
                self.doc_to_skill[doc_id] = spec.skill_id
                self.doc_to_utterance[doc_id] = utt
                self.doc_ngrams[doc_id] = char_ngrams(strip_vietnamese_diacritics(f"{title} {utt}"))

        self.index.build()
        # Deterministic Platt probability calibration anchored to bounded BM25+ngram score bands
        anchor_scores = (0.02, 0.05, 0.08, 0.11, 0.13, 0.16, 0.20, 0.26, 0.34, 0.44, 0.58, 0.75)
        anchor_labels = [1 if s >= 0.15 else 0 for s in anchor_scores]
        self.calibrator = ScoreCalibrator.fit(anchor_scores, anchor_labels, method="platt")

    def match_routes(self, query: str, top_k: int = 5) -> List[BoundedRouteMatchDTO]:
        """Scores bilingual routes in [0, 1] via top-k utterance aggregation + char-ngram typo leg."""
        if not (query or "").strip():
            return []
        bm25_hits = self.index.score_bounded(query)
        if not bm25_hits:
            return []

        q_ngrams = char_ngrams(strip_vietnamese_diacritics(query))
        per_skill: Dict[str, List[Tuple[float, str]]] = {}
        for doc_id, bm25_sc in bm25_hits:
            if bm25_sc <= 0.0:
                continue
            d_ng = self.doc_ngrams.get(doc_id, set())
            union = len(q_ngrams | d_ng)
            jaccard = (len(q_ngrams & d_ng) / union) if union else 0.0
            fused = min(max(0.80 * bm25_sc + 0.20 * jaccard, 0.0), 1.0)
            sid = self.doc_to_skill[doc_id]
            per_skill.setdefault(sid, []).append((fused, self.doc_to_utterance[doc_id]))

        matches: List[BoundedRouteMatchDTO] = []
        for sid, hits in per_skill.items():
            hits.sort(key=lambda item: item[0], reverse=True)
            top_hits = hits[: max(top_k, 1)]
            max_sc = top_hits[0][0]
            mean_sc = sum(h[0] for h in top_hits) / len(top_hits)
            agg_raw = round(min(max(0.75 * max_sc + 0.25 * mean_sc, 0.0), 1.0), 6)
            cal_conf = self.calibrator.predict_proba(agg_raw)
            spec = self.spec_by_id[sid]
            matched_utts = tuple(h[1] for h in top_hits[:2])
            matches.append(
                BoundedRouteMatchDTO(
                    skill_id=sid,
                    domain=spec.domain,
                    raw_bounded_score=agg_raw,
                    calibrated_confidence=cal_conf,
                    matched_utterances=matched_utts,
                )
            )
        matches.sort(key=lambda m: (-m.raw_bounded_score, m.skill_id))
        return matches


def get_utterance_router_index() -> CalibratedUtteranceRouterIndex:
    """Returns the thread-safe singleton CalibratedUtteranceRouterIndex."""
    global _UTTERANCE_ROUTER_SINGLETON
    if _UTTERANCE_ROUTER_SINGLETON is None:
        with _UTTERANCE_INDEX_LOCK:
            if _UTTERANCE_ROUTER_SINGLETON is None:
                _UTTERANCE_ROUTER_SINGLETON = CalibratedUtteranceRouterIndex()
    return _UTTERANCE_ROUTER_SINGLETON


# Path to domain mappings
DOMAIN_PATH_PATTERNS = {
    "01-web-automation": [
        re.compile(r"^(?:tests/e2e/|Scripts/|cypress/|playwright/|katalon/)", re.IGNORECASE),
        re.compile(r".*(?:page|screen|locator|pom|browser).*\.(?:py|ts|js|groovy)$", re.IGNORECASE),
    ],
    "02-test-design": [
        re.compile(r"^(?:tests/manual/|docs/test-design/|features/)", re.IGNORECASE),
        re.compile(r".*\.(?:feature|xlsx|csv)$", re.IGNORECASE),
    ],
    "03-api-and-contracts": [
        re.compile(r"^(?:tests/api/|swagger/|openapi/|pacts/)", re.IGNORECASE),
        re.compile(r".*(?:api|endpoint|contract|pact|fuzz).*\.(?:py|ts|json|yaml|yml)$", re.IGNORECASE),
    ],
    "04-performance-and-load": [
        re.compile(r"^(?:tests/perf/|Reports/perf/|jmeter/|k6/|locust/)", re.IGNORECASE),
        re.compile(r".*\.(?:jmx|jtl)$", re.IGNORECASE),
    ],
    "05-security-and-compliance": [
        re.compile(r"^(?:tests/security/|docs/security/)", re.IGNORECASE),
        re.compile(r".*(?:asvs|owasp|wcag|dast|security).*\.(?:py|ts|json)$", re.IGNORECASE),
    ],
    "06-healing-and-resilience": [
        re.compile(r"^(?:tools/heal/|tests/resilience/)", re.IGNORECASE),
        re.compile(r".*(?:flaky|heal|quarantine|reflexion).*\.py$", re.IGNORECASE),
    ],
    "07-data-and-state": [
        re.compile(r"^(?:fixtures/|tests/data/|migrations/)", re.IGNORECASE),
        re.compile(r".*(?:seed|fixture|database).*\.(?:sql|json|py)$", re.IGNORECASE),
    ],
    "08-code-quality": [
        re.compile(r"^(?:tools/lint/|skills/08-code-quality/)", re.IGNORECASE),
        re.compile(r".*(?:linter|ratchet|ast_parser|mutator).*\.py$", re.IGNORECASE),
    ],
    "09-ci-and-devops": [
        re.compile(r"^(?:\.github/workflows/|\.gitlab-ci|jenkins/|skills/09-ci-and-devops/)", re.IGNORECASE),
        re.compile(r".*(?:workflow|pipeline).*\.(?:ya?ml|groovy)$", re.IGNORECASE),
    ],
    "10-agent-orchestration": [
        re.compile(r"^(?:tools/orchestration/|skills/10-agent-orchestration/)", re.IGNORECASE),
        re.compile(r".*(?:swarm|orchestrat|fsm|super_plan|harvester).*\.py$", re.IGNORECASE),
    ],
    "11-ai-and-prompting": [
        re.compile(r"^(?:prompts/|templates/ai_bridges/|skills/11-ai-and-prompting/)", re.IGNORECASE),
        re.compile(r".*(?:prompt|mipro|meta_prompt).*\.(?:md|json)$", re.IGNORECASE),
    ],
}

INQUIRY_PATTERNS = [
    re.compile(r"\b(?:what\s+is|how\s+does|how\s+do|explain|tell\s+me\s+about|describe|where\s+is|why\s+is|read-only)\b", re.IGNORECASE),
    re.compile(r"\b(?:chưa\s*\?|đã\s+làm\s+chưa|là\s+gì|như\s+thế\s+nào|giải\s+thích|tại\s+sao)\b", re.IGNORECASE),
    re.compile(r"\b(?:chua\s*\?|da\s+lam\s+chua|la\s+gi|nhu\s+the\s+nao|giai\s+thich|tai\s+sao|hoat\s+dong\s+sao)\b", re.IGNORECASE),
    re.compile(r"^\s*(?:show|display|list|find|search|survey|diff)\b", re.IGNORECASE),
]

DIAGNOSTIC_PATTERNS = [
    re.compile(
        r"\b(?:audit|scan|doctor|diagnos(?:e|tic)|verify-all|verify|validate|check-invariants|lint|analyze|triage|health-check|"
        r"inspect|investigate|troubleshoot|debug|profile|measure|"
        r"(?:can|could|would|please)\s+(?:you\s+)?check|check\s+(?:why|if|whether|for))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:kiểm\s+tra|kiểm\s+chứng|đo\s+lường|đo|rà\s+soát|đánh\s+giá|phát\s+hiện|điều\s+tra|khám\s+nghiệm|phân\s+tích|quét|"
        r"kiem\s+tra|kiem\s+chung|do\s+luong|do\s+(?:chi\s+so|hieu\s+nang|toc\s+do)|ra\s+soat|danh\s+gia|"
        r"phat\s+hien|dieu\s+tra|kham\s+nghiem|phan\s+tich|quet)\b",
        re.IGNORECASE,
    ),
]

ACTION_PATTERNS = [
    re.compile(
        r"\b(?:implement|create|refactor|fix|add|write|author|build|update|delete|modify|bump|publish|release|execute|run|"
        r"generate|design|mock|heal|transpile|export|convert|redo|rework|improve|optimize|clean\s+up|patch|resolve|"
        r"configure|seed|quarantine|manage|make\s+(?:the|this|that|it))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:thực\s+hiện|viết|sửa|tạo|nâng\s+cấp|triển\s+khai|chạy|vá\s+lỗi|thiết\s+kế|sinh|giả\s+lập|chuyển\s+đổi|chuyển|xuất|tự\s+sửa|"
        r"xây\s+dựng|quản\s+lý|cấu\s+hình|làm\s+lại|làm\s+giùm|sửa\s+giùm|sửa\s+giúp|chỉnh\s+giúp|xử\s+lý|khắc\s+phục|tối\s+ưu|"
        r"thuc\s+hien|viet|sua|tao|nang\s+cap|trien\s+khai|chay|va\s+loi|thiet\s+ke|gia\s+lap|chuyen\s+doi|chuyen|xuat|tu\s+sua|"
        r"xay\s+dung|quan\s+ly|cau\s+hinh|lam\s+lai|lam\s+gium|sua\s+gium|sua\s+giup|chinh\s+giup|xu\s+ly|khac\s+phuc|toi\s+uu)\b",
        re.IGNORECASE,
    ),
]

IMPERATIVE_ACTION_LEAD = re.compile(
    r"^\s*(?:please\s+|hãy\s+|hay\s+)?(?:implement|create|refactor|fix|add|write|author|build|update|delete|modify|bump|publish|release|generate|design|mock|heal|transpile|export|convert|redo|rework|improve|"
    r"make\s+(?:the|this|that|it)|"
    r"thực\s+hiện|viết|sửa|tạo|vá\s+lỗi|thiết\s+kế|sinh|giả\s+lập|chuyển\s+đổi|chuyển|xuất|tự\s+sửa|làm\s+lại|làm\s+giùm|xử\s+lý|khắc\s+phục|tối\s+ưu|"
    r"thuc\s+hien|viet|sua|tao|va\s+loi|thiet\s+ke|gia\s+lap|chuyen\s+doi|chuyen|xuat|tu\s+sua|lam\s+lai|lam\s+gium|xu\s+ly|khac\s+phuc|toi\s+uu)\b",
    re.IGNORECASE,
)

_POLITE_VI_REQUEST_TAIL_RE = re.compile(
    r"(?:duoc\s+khong|gium\s+(?:minh|toi|em|voi)|giup\s+(?:minh|toi|em|voi)|voi|nhe|nha)\s*\?$",
    re.IGNORECASE,
)
_POLITE_EN_REQUEST_LEAD_RE = re.compile(
    r"^\s*(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:fix|redo|rework|update|improve|check|inspect|investigate|troubleshoot|debug|help)\b",
    re.IGNORECASE,
)
_VI_SYMPTOM_DIAGNOSTIC_RE = re.compile(
    r"\b(?:bi\s+(?:loi|rot|treo|vang|tru|hong|fail|crash|mat)|het\s+han|rot\s+phien|khong\s+tim\s+thay)\b",
    re.IGNORECASE,
)


def classify_intent(prompt: str) -> str:
    """Classifies user prompt intent into ACTION, DIAGNOSTIC, or INQUIRY."""
    p = (prompt or "").strip()
    if not p:
        return "INQUIRY"
    canonical_p = canonicalize_vietnamese_orthography(p).canonical_nfc_text or p
    folded = strip_vietnamese_diacritics(canonical_p)
    targets = (canonical_p, folded)

    # 1. Explicit leading imperative mutation verb always routes to ACTION
    if any(IMPERATIVE_ACTION_LEAD.search(t) for t in targets):
        return "ACTION"

    # 1b. Explicit /review or post-code review requests route to DIAGNOSTIC (read-only)
    if _REVIEW_INTENT_RE.search(p) and not _REVIEW_SPEC_GUARD_RE.search(p):
        return "DIAGNOSTIC"

    # 2. Explicit conceptual/read-only inquiry framing takes precedence over incidental verbs
    if any(pat.search(t) for t in targets for pat in INQUIRY_PATTERNS):
        if any(pat.search(t) for t in targets for pat in DIAGNOSTIC_PATTERNS):
            return "DIAGNOSTIC"
        return "INQUIRY"

    # 3. General Action verbs
    if any(pat.search(t) for t in targets for pat in ACTION_PATTERNS):
        return "ACTION"

    # 4. Diagnostic inspects without modifying (including explicit Vietnamese defect symptom reports)
    if any(pat.search(t) for t in targets for pat in DIAGNOSTIC_PATTERNS):
        return "DIAGNOSTIC"
    if not p.endswith("?") and _VI_SYMPTOM_DIAGNOSTIC_RE.search(folded):
        return "DIAGNOSTIC"

    # 5. Pure inquiry fallback
    return "INQUIRY"


def map_files_to_domains(target_files: List[str]) -> Set[str]:
    """Maps a list of relative or absolute file paths to skill domain IDs."""
    matched_domains: Set[str] = set()
    for fp in target_files:
        norm_fp = fp.replace("\\", "/").lstrip("./")
        for domain, patterns in DOMAIN_PATH_PATTERNS.items():
            if any(p.search(norm_fp) for p in patterns):
                matched_domains.add(domain)
    return matched_domains


def load_skills_index(repo_root: str = _REPO_ROOT) -> Dict[str, Any]:
    """Loads skills_index.json from repo root."""
    idx_path = os.path.join(repo_root, "skills_index.json")
    if os.path.isfile(idx_path):
        try:
            with open(idx_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass
    return {"skills": []}


META_WORKFLOW_SKILLS: List[Dict[str, Any]] = [
    {
        "id": "super-plan",
        "domain": "10-agent-orchestration",
        "path": ".agent/skills/super-plan/SKILL.md",
        "stack_triggers": ["super-plan", "plan", "roadmap", "dag", "architecture", "milestone"],
        "summary": "Deep Spec-Driven Planning Pipeline: Risk Routing, Ambiguity Gate, Execution DAG, Plan Mutation, and Harvesting",
    },
    {
        "id": "solo",
        "domain": "10-agent-orchestration",
        "path": ".agent/skills/solo/SKILL.md",
        "stack_triggers": ["solo", "tdd", "red", "green", "mutation", "purple", "from-plan"],
        "summary": "Single-Agent Verification Loop with 4 Pillars: Red QA -> Blue Dev -> Live Mutation -> Purple Auditor",
    },
    {
        "id": "review",
        "domain": "08-code-quality",
        "path": ".agent/skills/review/SKILL.md",
        "stack_triggers": ["review", "code-review", "diff", "pr", "simplify", "provenance"],
        "summary": "Closed-Loop Post-Code Adversarial Reviewer reconciling /solo diffs and HMAC receipts against /super-plan contracts",
    },
]

_SUPER_PLAN_INTENT_RE = re.compile(
    r"(?:/super-plan\b|\bsuper[-_\s]plan\b|\bimplementation[\s_-]plan\b|\bexecution\s+dag\b|\barchitectural\s+(?:plan|roadmap|blueprint)\b)",
    re.IGNORECASE,
)
_SOLO_INTENT_RE = re.compile(
    r"(?:/solo\b|\bsolo_runner\b|\bplan_dag_bridge\b|\b--from-plan\b|\bred\s*->\s*green\b|\bsingle[-_\s]agent\s+tdd\b)",
    re.IGNORECASE,
)
_REVIEW_SPEC_GUARD_RE = re.compile(
    r"(?:/review-spec\b|\breview[-_\s]spec\b|\.feature\b|\bgherkin\b|\bbrd\b|\buser\s+stor(?:y|ies)\b|\bspecification\b)",
    re.IGNORECASE,
)
_REVIEW_INTENT_RE = re.compile(
    r"(?:(?:^|\s)/review(?!-)\b|\bcode\s+review\b|\bpr\s+review\b|\breview\s+(?:diff|changes|code|commit|pr|pull\s+request|implementation|solo)\b|\bpost[-_\s]solo\s+review\b)",
    re.IGNORECASE,
)


def _detect_meta_workflow_skill(
    prompt: str,
    target_files: List[str],
    intent: str,
    repo_root: str = _REPO_ROOT,
) -> Optional[Dict[str, Any]]:
    """Detects explicit or scope-triggered /super-plan, /solo, and /review meta-skills."""
    p = prompt or ""
    by_id = {s["id"]: s for s in META_WORKFLOW_SKILLS}
    # Explicit slash commands take highest precedence over incidental file names (e.g. implementation_plan.md)
    if re.search(r"(?:^|\s)/solo\b", p, re.IGNORECASE):
        return by_id["solo"]
    if re.search(r"(?:^|\s)/super-plan\b", p, re.IGNORECASE):
        return by_id["super-plan"]
    if re.search(r"(?:^|\s)/review(?!-)\b", p, re.IGNORECASE):
        return by_id["review"]
    if _REVIEW_INTENT_RE.search(p) and not _REVIEW_SPEC_GUARD_RE.search(p):
        return by_id["review"]
    if _SOLO_INTENT_RE.search(p):
        return by_id["solo"]
    if _SUPER_PLAN_INTENT_RE.search(p):
        return by_id["super-plan"]
    # Multi-file TDD execution (> 2 runtime files) routes to /solo meta-skill
    if intent == "ACTION" and len(target_files) > 2:
        if any(
            f.replace("\\", "/").startswith(("tools/design/", "tools/orchestration/", "tools/lint/"))
            for f in target_files
        ):
            return by_id["solo"]
    return None


def _scan_local_agent_skills_dir(agent_skills_dir: str, by_id: Dict[str, Dict[str, Any]]) -> None:
    """Scans .agent/skills/* subdirectories and registers any uncatalogued local SKILL.md."""
    try:
        entries = sorted(os.listdir(agent_skills_dir))
    except OSError as exc:
        sys.stderr.write(f"[skill_router] Unable to scan .agent/skills directory: {exc}\n")
        return
    for entry in entries:
        skill_md = os.path.join(agent_skills_dir, entry, "SKILL.md")
        if os.path.isfile(skill_md) and entry not in by_id:
            by_id[entry] = {
                "id": entry,
                "domain": "10-agent-orchestration",
                "path": f".agent/skills/{entry}/SKILL.md",
                "stack_triggers": [entry, *entry.split("-")],
                "summary": f"Local agent workflow skill: {entry}",
            }


def load_agent_local_skills(repo_root: str = _REPO_ROOT) -> List[Dict[str, Any]]:
    """Loads .agent/skills/* metadata merged with META_WORKFLOW_SKILLS (deduplicated by id)."""
    by_id: Dict[str, Dict[str, Any]] = {s["id"]: dict(s) for s in META_WORKFLOW_SKILLS}
    agent_skills_dir = os.path.join(repo_root, ".agent", "skills")
    if os.path.isdir(agent_skills_dir):
        _scan_local_agent_skills_dir(agent_skills_dir, by_id)
    return list(by_id.values())


_GENERIC_SID_TOKENS: frozenset[str] = frozenset({
    "to", "in", "on", "of", "and", "or", "at", "by", "as", "for", "test", "tests", "testing",
})


def _build_exemption_result(
    intent: str,
    exempt_reason: str,
    needs_clarification: bool = False,
    clarification_reason: Optional[str] = None,
    clarifying_questions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Builds a backward-compatible exempt routing dictionary."""
    return {
        "intent": intent,
        "is_triggered": False,
        "is_exempt": True,
        "exempt_reason": exempt_reason,
        "matched_domains": [],
        "matched_skills": [],
        "recommended_skill": None,
        "skill_md_path": None,
        "score": 0.0,
        "calibrated_confidence": 0.0,
        "matched_utterances": [],
        "needs_clarification": needs_clarification,
        "clarification_reason": clarification_reason,
        "clarifying_questions": clarifying_questions or [],
        "ambiguous_context": False,
        "context_conflicts": [],
    }


def _collect_all_skills(repo_root: str) -> List[Dict[str, Any]]:
    """Loads and deduplicates indexed skills plus local .agent/skills metadata."""
    indexed = list(load_skills_index(repo_root).get("skills", []))
    seen_ids: Set[str] = {str(s.get("id", "")) for s in indexed}
    all_skills = list(indexed)
    for ls in load_agent_local_skills(repo_root):
        sid = str(ls.get("id", ""))
        if sid not in seen_ids:
            all_skills.append(ls)
            seen_ids.add(sid)
    return all_skills


def _find_explicit_skill(
    raw_prompt: str,
    slash_skill: Optional[str],
    all_skills: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Resolves explicit /slash skill or verbatim skill-id reference in prompt."""
    if slash_skill:
        for s in all_skills:
            if str(s.get("id", "")).lower() == slash_skill:
                return s
    prompt_lower = raw_prompt.lower()
    for s in all_skills:
        sid = str(s.get("id", ""))
        if not sid or sid in ("solo", "review"):
            continue
        if re.search(rf"(?<![a-z0-9\-]){re.escape(sid)}(?![a-z0-9\-])", prompt_lower):
            return s
    return None


def _build_prompt_word_sets(norm_dto: Any) -> Tuple[Set[str], Set[str]]:
    """Extracts base and plural-expanded word sets from normalized prompt."""
    normalized_prompt = norm_dto.canonical_text.lower()
    if "page object" in normalized_prompt:
        normalized_prompt += " pom"
    if "end to end" in normalized_prompt or "end-to-end" in normalized_prompt:
        normalized_prompt += " e2e"
    prompt_words = set(re.findall(r"[a-z0-9]{2,}", normalized_prompt)) | set(norm_dto.canonical_tokens)
    if "database" in prompt_words:
        prompt_words.add("db")
    expanded = set(prompt_words)
    for pw in prompt_words:
        if len(pw) > 3:
            expanded.add(pw + "s")
            if pw.endswith("s"):
                expanded.add(pw[:-1])
    return prompt_words, expanded


def _score_skill_lexical(skill_entry: Dict[str, Any], prompt_words: Set[str], expanded_words: Set[str]) -> int:
    """Computes lexical stack_triggers + skill-id + summary overlap score (nesting <= 2)."""
    triggers = [t.lower() for t in skill_entry.get("stack_triggers", []) if t]
    score = sum(4 for trig in triggers if trig in expanded_words)
    sid_tokens = [
        tok for tok in str(skill_entry.get("id", "")).lower().split("-")
        if len(tok) >= 2 and tok not in _GENERIC_SID_TOKENS
    ]
    for tok in sid_tokens:
        if tok in expanded_words:
            score += 3
        elif any(len(w) >= 4 and (tok.startswith(w) or w.startswith(tok)) for w in prompt_words):
            score += 2
    sum_words = set(re.findall(r"[a-z0-9]{3,}", str(skill_entry.get("summary", "")).lower()))
    return score + len(expanded_words & sum_words)


def _rank_fileless_candidates(
    all_skills: Sequence[Dict[str, Any]],
    prompt_words: Set[str],
    expanded_words: Set[str],
    route_by_id: Dict[str, BoundedRouteMatchDTO],
    context_conflicts: List[str],
) -> Tuple[List[Dict[str, Any]], float, float, List[str]]:
    """Ranks file-less skills by fusing lexical trigger scores with calibrated utterance matches."""
    if "app_validation_vs_qa_data" in context_conflicts:
        return [], 0.0, 0.0, []

    qualified: List[Tuple[float, int, float, Dict[str, Any], Optional[BoundedRouteMatchDTO]]] = []
    best_unqualified_conf = 0.0
    for s in all_skills:
        sid = str(s.get("id", ""))
        lex = _score_skill_lexical(s, prompt_words, expanded_words)
        rm = route_by_id.get(sid)
        spec = get_skill_route_spec(sid)
        threshold = spec.confidence_threshold if spec else 0.42
        conf = rm.calibrated_confidence if rm is not None else 0.0
        raw_utt = rm.raw_bounded_score if rm is not None else 0.0
        best_unqualified_conf = max(best_unqualified_conf, conf)

        utt_qualified = rm is not None and raw_utt >= MIN_UTTERANCE_RAW_SCORE and conf >= threshold
        if lex >= MIN_FILELESS_CONFIDENCE_SCORE or utt_qualified:
            fused_rank = float(lex) + (conf * 10.0 if utt_qualified else 0.0)
            qualified.append((fused_rank, lex, conf, s, rm))

    if not qualified:
        return [], 0.0, round(best_unqualified_conf, 6), []

    qualified.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    top_fused, top_lex, top_conf, top_skill, top_rm = qualified[0]
    if len(qualified) >= 2:
        _, sec_lex, _, sec_skill, _ = qualified[1]
        is_cross_domain_tie = (
            top_skill.get("domain") != sec_skill.get("domain")
            and top_lex > 0
            and abs(top_lex - sec_lex) <= 1
            and top_lex < 8
        )
        if is_cross_domain_tie and "close_cross_domain_skill_tie" not in context_conflicts:
            context_conflicts.append("close_cross_domain_skill_tie")

    effective_conf = max(top_conf, min(round(top_lex / 10.0, 6), 0.99)) if top_lex >= MIN_FILELESS_CONFIDENCE_SCORE else top_conf
    utts = list(top_rm.matched_utterances) if top_rm is not None else []
    return [item[3] for item in qualified[:5]], round(top_fused, 4), round(min(effective_conf, 1.0), 6), utts


def _resolve_skill_md_path(recommended_skill: Optional[Dict[str, Any]], repo_root: str) -> Optional[str]:
    """Resolves SKILL.md path from skills_index entry or falls back to skills_manifest.json."""
    if not recommended_skill:
        return None
    skill_md_path = recommended_skill.get("path")
    rec_id = recommended_skill.get("id")
    if skill_md_path or not rec_id:
        return skill_md_path
    manifest_path = os.path.join(repo_root, "skills_manifest.json")
    if not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path, "r", encoding="utf-8") as mf:
            items = json.load(mf).get("skills", [])
        return next((item.get("path") for item in items if item.get("id") == rec_id), None)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        return None


def _is_explicit_inquiry_prompt(raw_prompt: str) -> bool:
    """Determines whether a prompt is an explicit conceptual question (not a polite action request)."""
    stripped = raw_prompt.strip()
    folded = strip_vietnamese_diacritics(stripped)
    is_polite = bool(
        _POLITE_VI_REQUEST_TAIL_RE.search(folded) or _POLITE_EN_REQUEST_LEAD_RE.search(stripped)
    )
    if any(pat.search(t) for t in (stripped, folded) for pat in INQUIRY_PATTERNS):
        return True
    return bool(stripped.endswith("?") and not is_polite)


def evaluate_skill_first_trigger(
    prompt: str,
    target_files: Optional[List[str]] = None,
    is_single_line_hotfix: bool = False,
    repo_root: str = _REPO_ROOT,
) -> Dict[str, Any]:
    """Evaluates whether Rule 7 (Skill-First Hard Blocker) is mechanically triggered (nesting <= 3)."""
    raw_prompt = prompt or ""
    norm_dto = normalize_bilingual_intent(raw_prompt)
    intent = classify_intent(raw_prompt)
    files = target_files or []
    all_skills = _collect_all_skills(repo_root)

    slash_matched = (
        next((s for s in all_skills if str(s.get("id", "")).lower() == norm_dto.slash_skill), None)
        if norm_dto.slash_skill
        else None
    )
    meta_explicit = bool(
        _SUPER_PLAN_INTENT_RE.search(raw_prompt)
        or _SOLO_INTENT_RE.search(raw_prompt)
        or (_REVIEW_INTENT_RE.search(raw_prompt) and not _REVIEW_SPEC_GUARD_RE.search(raw_prompt))
        or slash_matched is not None
    )

    if intent == "INQUIRY" and not meta_explicit:
        if not _is_explicit_inquiry_prompt(raw_prompt) and not files and norm_dto.needs_clarification:
            return _build_exemption_result(
                intent=intent,
                exempt_reason="Underspecified prompt requires context clarification",
                needs_clarification=True,
                clarification_reason="Unmapped colloquial or underspecified prompt without target files or recognizable technical domain tokens.",
                clarifying_questions=list(norm_dto.clarifying_questions or build_clarification_questions(raw_prompt)),
            )
        return _build_exemption_result(
            intent=intent,
            exempt_reason="Pure inquiry intent (read-only conceptual question or explanation)",
        )

    if is_single_line_hotfix:
        return _build_exemption_result(
            intent=intent,
            exempt_reason="Single-line micro-fix exemption (no architectural boundary crossed)",
        )

    matched_domains = map_files_to_domains(files)
    matched_skills = [s for s in all_skills if s.get("domain", "") in matched_domains]
    explicit_skill = slash_matched or _find_explicit_skill(raw_prompt, None, all_skills)
    if explicit_skill is not None and explicit_skill not in matched_skills:
        matched_skills.insert(0, explicit_skill)
    if explicit_skill is not None and explicit_skill.get("domain"):
        matched_domains.add(str(explicit_skill["domain"]))

    meta_skill = _detect_meta_workflow_skill(raw_prompt, files, intent, repo_root)
    if meta_skill is not None:
        if meta_skill not in matched_skills:
            matched_skills.insert(0, meta_skill)
        matched_domains.add(meta_skill["domain"])
        explicit_skill = explicit_skill or meta_skill

    if files and not matched_domains and not explicit_skill:
        return _build_exemption_result(
            intent=intent,
            exempt_reason=f"Touched files ({len(files)} files) fall outside managed skill domains",
        )

    prompt_words, expanded_words = _build_prompt_word_sets(norm_dto)
    utterance_matches = get_utterance_router_index().match_routes(norm_dto.canonical_text, top_k=5)
    route_by_id: Dict[str, BoundedRouteMatchDTO] = {m.skill_id: m for m in utterance_matches}
    context_conflicts: List[str] = list(norm_dto.context_conflicts) if not files else []

    top_score = 0.0
    calibrated_conf = 0.0
    matched_utts: List[str] = []

    if not files and not matched_skills and not explicit_skill:
        matched_skills, top_score, calibrated_conf, matched_utts = _rank_fileless_candidates(
            all_skills, prompt_words, expanded_words, route_by_id, context_conflicts
        )
        if matched_skills and matched_skills[0].get("domain"):
            matched_domains.add(str(matched_skills[0]["domain"]))
    elif matched_skills:
        matched_skills.sort(key=lambda s: _score_skill_lexical(s, prompt_words, expanded_words), reverse=True)
        top_score = float(_score_skill_lexical(matched_skills[0], prompt_words, expanded_words))
        top_rm = route_by_id.get(str(matched_skills[0].get("id", "")))
        calibrated_conf = top_rm.calibrated_confidence if top_rm is not None else min(round(top_score / 10.0, 6), 0.99)
        matched_utts = list(top_rm.matched_utterances) if top_rm is not None else []

    recommended_skill = explicit_skill or (matched_skills[0] if matched_skills else None)
    if explicit_skill is not None:
        top_score = float(max(MIN_FILELESS_CONFIDENCE_SCORE, _score_skill_lexical(explicit_skill, prompt_words, expanded_words)))
        calibrated_conf = 1.0
        exp_rm = route_by_id.get(str(explicit_skill.get("id", "")))
        if exp_rm is not None:
            matched_utts = list(exp_rm.matched_utterances)

    is_triggered = recommended_skill is not None
    rec_id = recommended_skill.get("id") if recommended_skill else None
    skill_md_path = _resolve_skill_md_path(recommended_skill, repo_root)

    needs_clarification = bool(
        not is_triggered and not files and intent in ("ACTION", "DIAGNOSTIC") and norm_dto.needs_clarification
    )
    clarification_reason = (
        "Unmapped colloquial or underspecified prompt without target files or recognizable technical domain tokens."
        if needs_clarification
        else None
    )
    clarifying_questions = (
        list(norm_dto.clarifying_questions or build_clarification_questions(raw_prompt))
        if needs_clarification
        else []
    )

    return {
        "intent": intent,
        "is_triggered": is_triggered,
        "is_exempt": not is_triggered,
        "exempt_reason": None if is_triggered else "No matching skill above confidence threshold",
        "matched_domains": sorted(list(matched_domains)),
        "matched_skills": matched_skills,
        "recommended_skill": rec_id,
        "skill_md_path": skill_md_path,
        "score": top_score,
        "calibrated_confidence": round(min(max(calibrated_conf, 0.0), 1.0), 6),
        "matched_utterances": matched_utts,
        "needs_clarification": needs_clarification,
        "clarification_reason": clarification_reason,
        "clarifying_questions": clarifying_questions,
        "ambiguous_context": bool(context_conflicts),
        "context_conflicts": context_conflicts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Context-Aware Skill Router (Rule 7 Mechanical Sensor)")
    parser.add_argument("--prompt", required=True, help="User request or task prompt")
    parser.add_argument("--files", nargs="*", default=[], help="Target or touched file paths")
    parser.add_argument("--micro-fix", action="store_true", help="Flag as single-line micro-fix")
    parser.add_argument("--repo-root", default=_REPO_ROOT, help="Repository root path")
    parser.add_argument("--json", action="store_true", help="Output pure JSON")
    args = parser.parse_args()

    result = evaluate_skill_first_trigger(
        prompt=args.prompt,
        target_files=args.files,
        is_single_line_hotfix=args.micro_fix,
        repo_root=args.repo_root,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print("======================================================================")
    print("🎯 CONTEXT-AWARE SKILL ROUTER (RULE 7 SENSOR)")
    print("======================================================================")
    print(f"  Intent Detected    : {result['intent']}")
    print(f"  Skill-First Status : {'TRIGGERED' if result['is_triggered'] else 'EXEMPT'}")
    if result.get("needs_clarification"):
        print(f"  Clarification      : REQUIRED ({result.get('clarification_reason')})")
        for idx, q in enumerate(result.get("clarifying_questions", []), 1):
            print(f"    {idx}. {q.get('question')}")
    if result.get("ambiguous_context"):
        print(f"  Ambiguous Context  : YES ({', '.join(result.get('context_conflicts', []))})")
    if result["is_exempt"]:
        print(f"  Exemption Reason   : {result['exempt_reason']}")
    else:
        print(f"  Matched Domains    : {', '.join(result['matched_domains']) or 'General'}")
        print(f"  Recommended Skill  : {result['recommended_skill']}")
        print(f"  Required SKILL.md  : {result['skill_md_path']}")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
