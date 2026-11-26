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
from typing import Any, Dict, List, Optional, Set

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


MIN_FILELESS_CONFIDENCE_SCORE: int = 4


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
        r"\b(?:audit|scan|doctor|diagnos(?:e|tic)|verify-all|check-invariants|lint|analyze|triage|health-check|"
        r"inspect|investigate|troubleshoot|debug|profile|measure|"
        r"(?:can|could|would|please)\s+(?:you\s+)?check|check\s+(?:why|if|whether|for))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:kiểm\s+tra|đo\s+lường|đo|rà\s+soát|đánh\s+giá|kiem\s+tra|do\s+luong|do\s+(?:chi\s+so|hieu\s+nang|toc\s+do)|ra\s+soat|danh\s+gia)\b",
        re.IGNORECASE,
    ),
]

ACTION_PATTERNS = [
    re.compile(
        r"\b(?:implement|create|refactor|fix|add|write|author|build|update|delete|modify|bump|publish|release|execute|run|"
        r"generate|design|mock|heal|transpile|export|convert|redo|rework|improve|optimize|clean\s+up|patch|resolve|"
        r"make\s+(?:the|this|that|it))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:thực\s+hiện|viết|sửa|tạo|nâng\s+cấp|triển\s+khai|chạy\s+thử|vá\s+lỗi|thiết\s+kế|sinh|giả\s+lập|chuyển\s+đổi|chuyển|xuất|tự\s+sửa|"
        r"làm\s+lại|làm\s+giùm|sửa\s+giùm|sửa\s+giúp|chỉnh\s+giúp|xử\s+lý|khắc\s+phục|tối\s+ưu|"
        r"thuc\s+hien|viet|sua|tao|nang\s+cap|trien\s+khai|chay\s+thu|va\s+loi|thiet\s+ke|gia\s+lap|chuyen\s+doi|chuyen|xuat|tu\s+sua|"
        r"lam\s+lai|lam\s+gium|sua\s+gium|sua\s+giup|chinh\s+giup|xu\s+ly|khac\s+phuc|toi\s+uu)\b",
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


def classify_intent(prompt: str) -> str:
    """Classifies user prompt intent into ACTION, DIAGNOSTIC, or INQUIRY."""
    p = (prompt or "").strip()
    if not p:
        return "INQUIRY"
    folded = strip_vietnamese_diacritics(p)
    targets = (p, folded)

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

    # 4. Diagnostic inspects without modifying
    if any(pat.search(t) for t in targets for pat in DIAGNOSTIC_PATTERNS):
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


def load_agent_local_skills(repo_root: str = _REPO_ROOT) -> List[Dict[str, Any]]:
    """Loads .agent/skills/* metadata merged with META_WORKFLOW_SKILLS (deduplicated by id)."""
    by_id: Dict[str, Dict[str, Any]] = {s["id"]: dict(s) for s in META_WORKFLOW_SKILLS}
    agent_skills_dir = os.path.join(repo_root, ".agent", "skills")
    if os.path.isdir(agent_skills_dir):
        try:
            for entry in sorted(os.listdir(agent_skills_dir)):
                skill_md = os.path.join(agent_skills_dir, entry, "SKILL.md")
                if os.path.isfile(skill_md) and entry not in by_id:
                    rel_path = f".agent/skills/{entry}/SKILL.md"
                    by_id[entry] = {
                        "id": entry,
                        "domain": "10-agent-orchestration",
                        "path": rel_path,
                        "stack_triggers": [entry, *entry.split("-")],
                        "summary": f"Local agent workflow skill: {entry}",
                    }
        except OSError as exc:
            sys.stderr.write(f"[skill_router] Unable to scan .agent/skills directory: {exc}\n")
    return list(by_id.values())


def evaluate_skill_first_trigger(
    prompt: str,
    target_files: Optional[List[str]] = None,
    is_single_line_hotfix: bool = False,
    repo_root: str = _REPO_ROOT,
) -> Dict[str, Any]:
    """
    Evaluates whether Rule 7 (Skill-First Hard Blocker) is mechanically triggered.
    Returns:
      {
        "intent": str,
        "is_triggered": bool,
        "is_exempt": bool,
        "exempt_reason": Optional[str],
        "matched_domains": List[str],
        "matched_skills": List[Dict[str, Any]],
        "recommended_skill": Optional[str],
        "skill_md_path": Optional[str],
        "score": float,
      }
    """
    raw_prompt = prompt or ""
    norm_dto = normalize_bilingual_intent(raw_prompt)
    intent = classify_intent(raw_prompt)
    files = target_files or []

    skills_data = load_skills_index(repo_root)
    indexed_skills = list(skills_data.get("skills", []))
    local_agent_skills = load_agent_local_skills(repo_root)
    seen_skill_ids: Set[str] = {str(s.get("id", "")) for s in indexed_skills}
    all_skills = list(indexed_skills)
    for ls in local_agent_skills:
        if ls.get("id") not in seen_skill_ids:
            all_skills.append(ls)
            seen_skill_ids.add(str(ls.get("id", "")))

    # Resolve explicit /slash command against full 59-skill registry
    slash_matched_skill: Optional[Dict[str, Any]] = None
    if norm_dto.slash_skill:
        for s in all_skills:
            if str(s.get("id", "")).lower() == norm_dto.slash_skill:
                slash_matched_skill = s
                break

    # Exemption 1: Pure Inquiry (unless explicit /super-plan, /solo, /review, valid /<skill-id>, or unmapped non-question prose)
    meta_explicit = (
        _SUPER_PLAN_INTENT_RE.search(raw_prompt)
        or _SOLO_INTENT_RE.search(raw_prompt)
        or (_REVIEW_INTENT_RE.search(raw_prompt) and not _REVIEW_SPEC_GUARD_RE.search(raw_prompt))
        or slash_matched_skill is not None
    )
    stripped_prompt = raw_prompt.strip()
    folded_prompt = strip_vietnamese_diacritics(stripped_prompt)
    is_polite_request_q = bool(
        _POLITE_VI_REQUEST_TAIL_RE.search(folded_prompt)
        or _POLITE_EN_REQUEST_LEAD_RE.search(stripped_prompt)
    )
    is_explicit_inquiry = (
        any(pat.search(t) for t in (stripped_prompt, folded_prompt) for pat in INQUIRY_PATTERNS)
        or (stripped_prompt.endswith("?") and not is_polite_request_q)
    )
    if intent == "INQUIRY" and not meta_explicit:
        if not is_explicit_inquiry and not files and norm_dto.needs_clarification:
            return {
                "intent": intent,
                "is_triggered": False,
                "is_exempt": True,
                "exempt_reason": "Underspecified prompt requires context clarification",
                "matched_domains": [],
                "matched_skills": [],
                "recommended_skill": None,
                "skill_md_path": None,
                "score": 0.0,
                "needs_clarification": True,
                "clarification_reason": "Unmapped colloquial or underspecified prompt without target files or recognizable technical domain tokens.",
                "clarifying_questions": list(norm_dto.clarifying_questions or build_clarification_questions(raw_prompt)),
            }
        return {
            "intent": intent,
            "is_triggered": False,
            "is_exempt": True,
            "exempt_reason": "Pure inquiry intent (read-only conceptual question or explanation)",
            "matched_domains": [],
            "matched_skills": [],
            "recommended_skill": None,
            "skill_md_path": None,
            "score": 0.0,
            "needs_clarification": False,
            "clarification_reason": None,
            "clarifying_questions": [],
        }

    # Exemption 2: Single-line hotfix
    if is_single_line_hotfix:
        return {
            "intent": intent,
            "is_triggered": False,
            "is_exempt": True,
            "exempt_reason": "Single-line micro-fix exemption (no architectural boundary crossed)",
            "matched_domains": [],
            "matched_skills": [],
            "recommended_skill": None,
            "skill_md_path": None,
            "score": 0.0,
            "needs_clarification": False,
            "clarification_reason": None,
            "clarifying_questions": [],
        }

    matched_domains = map_files_to_domains(files)

    matched_skills: List[Dict[str, Any]] = []
    for s in all_skills:
        s_domain = s.get("domain", "")
        if s_domain in matched_domains:
            matched_skills.append(s)

    # Check if explicit /slash skill or skill ID is named in prompt
    explicit_skill: Optional[Dict[str, Any]] = slash_matched_skill
    prompt_lower = raw_prompt.lower()
    if explicit_skill is not None:
        if explicit_skill not in matched_skills:
            matched_skills.insert(0, explicit_skill)
        if explicit_skill.get("domain"):
            matched_domains.add(str(explicit_skill["domain"]))
    else:
        for s in all_skills:
            sid = s.get("id", "")
            if not sid or sid in ("solo", "review"):
                continue
            if re.search(rf"(?<![a-z0-9\-]){re.escape(sid)}(?![a-z0-9\-])", prompt_lower):
                explicit_skill = s
                if s not in matched_skills:
                    matched_skills.append(s)
                break

    # Meta-workflow routing: /super-plan and /solo (.agent/skills/{super-plan,solo}/SKILL.md)
    meta_skill = _detect_meta_workflow_skill(raw_prompt, files, intent, repo_root)
    if meta_skill is not None:
        if meta_skill not in matched_skills:
            matched_skills.insert(0, meta_skill)
        matched_domains.add(meta_skill["domain"])
        if explicit_skill is None:
            explicit_skill = meta_skill

    # Exemption 3: Action outside of managed skill domains without explicit skill call
    if files and not matched_domains and not explicit_skill:
        return {
            "intent": intent,
            "is_triggered": False,
            "is_exempt": True,
            "exempt_reason": f"Touched files ({len(files)} files) fall outside managed skill domains",
            "matched_domains": [],
            "matched_skills": [],
            "recommended_skill": None,
            "skill_md_path": None,
            "score": 0.0,
            "needs_clarification": False,
            "clarification_reason": None,
            "clarifying_questions": [],
        }

    normalized_prompt = norm_dto.canonical_text.lower()
    if "page object" in normalized_prompt:
        normalized_prompt += " pom"
    if "end to end" in normalized_prompt or "end-to-end" in normalized_prompt:
        normalized_prompt += " e2e"
    prompt_words = set(re.findall(r"[a-z0-9]{2,}", normalized_prompt)) | set(norm_dto.canonical_tokens)
    if "database" in prompt_words:
        prompt_words.add("db")
    expanded_prompt_words = set(prompt_words)
    for pw in prompt_words:
        if len(pw) > 3:
            expanded_prompt_words.add(pw + "s")
            if pw.endswith("s"):
                expanded_prompt_words.add(pw[:-1])

    _generic_sid_tokens = frozenset({
        "to", "in", "on", "of", "and", "or", "at", "by", "as", "for", "test", "tests", "testing",
    })

    def _skill_relevance(skill_entry: Dict[str, Any]) -> int:
        score = 0
        triggers = [t.lower() for t in skill_entry.get("stack_triggers", [])]
        for trig in triggers:
            if not trig:
                continue
            if trig in expanded_prompt_words:
                score += 4
        sid_tokens = [
            tok for tok in skill_entry.get("id", "").lower().split("-")
            if len(tok) >= 2 and tok not in _generic_sid_tokens
        ]
        for tok in sid_tokens:
            if tok in expanded_prompt_words:
                score += 3
            elif any(len(w) >= 4 and (tok.startswith(w) or w.startswith(tok)) for w in prompt_words):
                score += 2
        sum_words = set(re.findall(r"[a-z0-9]{3,}", skill_entry.get("summary", "").lower()))
        score += len(expanded_prompt_words & sum_words)
        return score

    # Turn-1 file-less global ranking across all 59 skills when target_files=[]
    top_score = 0.0
    if not files and not matched_skills and not explicit_skill:
        scored_global = [(s, _skill_relevance(s)) for s in all_skills]
        scored_global.sort(key=lambda item: item[1], reverse=True)
        qualified = [item for item in scored_global if item[1] >= MIN_FILELESS_CONFIDENCE_SCORE]
        if qualified:
            matched_skills = [item[0] for item in qualified[:5]]
            top_score = float(qualified[0][1])
            if qualified[0][0].get("domain"):
                matched_domains.add(str(qualified[0][0]["domain"]))
    elif matched_skills:
        matched_skills.sort(key=_skill_relevance, reverse=True)
        top_score = float(_skill_relevance(matched_skills[0]))

    recommended_skill = explicit_skill or (matched_skills[0] if matched_skills else None)
    if explicit_skill is not None and top_score < float(MIN_FILELESS_CONFIDENCE_SCORE):
        top_score = float(max(MIN_FILELESS_CONFIDENCE_SCORE, _skill_relevance(explicit_skill)))

    is_triggered = bool(recommended_skill is not None)
    rec_id = recommended_skill.get("id") if recommended_skill else None

    # Resolve SKILL.md path directly from skills_index.json (0-hop Turn-1 lookup), falling back to manifest
    skill_md_path = recommended_skill.get("path") if recommended_skill else None
    if rec_id and not skill_md_path:
        manifest_path = os.path.join(repo_root, "skills_manifest.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    m_data = json.load(mf)
                for item in m_data.get("skills", []):
                    if item.get("id") == rec_id:
                        skill_md_path = item.get("path")
                        break
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

    needs_clarification = bool(
        not is_triggered
        and not files
        and intent in ("ACTION", "DIAGNOSTIC")
        and norm_dto.needs_clarification
    )
    clarification_reason = (
        "Unmapped colloquial or underspecified prompt without target files or recognizable technical domain tokens."
        if needs_clarification
        else None
    )
    clarifying_questions = list(
        norm_dto.clarifying_questions or build_clarification_questions(raw_prompt)
    ) if needs_clarification else []

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
        "needs_clarification": needs_clarification,
        "clarification_reason": clarification_reason,
        "clarifying_questions": clarifying_questions,
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
