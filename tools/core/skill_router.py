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
    re.compile(r"^\s*(?:show|display|list|find|search|survey|diff)\b", re.IGNORECASE),
]

DIAGNOSTIC_PATTERNS = [
    re.compile(r"\b(?:audit|scan|doctor|diagnos(?:e|tic)|verify-all|check-invariants|lint|analyze|triage|health-check)\b", re.IGNORECASE),
    re.compile(r"\b(?:kiểm\s+tra|đo\s+lường|rà\s+soát|đánh\s+giá)\b", re.IGNORECASE),
]

ACTION_PATTERNS = [
    re.compile(r"\b(?:implement|create|refactor|fix|add|write|author|build|update|delete|modify|bump|publish|release)\b", re.IGNORECASE),
    re.compile(r"\b(?:thực\s+hiện|viết|sửa|tạo|nâng\s+cấp|triển\s+khai|chạy\s+thử|vá\s+lỗi)\b", re.IGNORECASE),
]

IMPERATIVE_ACTION_LEAD = re.compile(
    r"^\s*(?:please\s+|hãy\s+)?(?:implement|create|refactor|fix|add|write|author|build|update|delete|modify|bump|publish|release|thực\s+hiện|viết|sửa|tạo|vá\s+lỗi)\b",
    re.IGNORECASE,
)


def classify_intent(prompt: str) -> str:
    """Classifies user prompt intent into ACTION, DIAGNOSTIC, or INQUIRY."""
    p = (prompt or "").strip()
    if not p:
        return "INQUIRY"

    # 1. Explicit leading imperative mutation verb always routes to ACTION
    if IMPERATIVE_ACTION_LEAD.search(p):
        return "ACTION"

    # 2. Explicit conceptual/read-only inquiry framing takes precedence over incidental verbs
    if any(pat.search(p) for pat in INQUIRY_PATTERNS):
        if any(pat.search(p) for pat in DIAGNOSTIC_PATTERNS):
            return "DIAGNOSTIC"
        return "INQUIRY"

    # 3. General Action verbs
    if any(pat.search(p) for pat in ACTION_PATTERNS):
        return "ACTION"

    # 4. Diagnostic inspects without modifying
    if any(pat.search(p) for pat in DIAGNOSTIC_PATTERNS):
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
      }
    """
    intent = classify_intent(prompt)
    files = target_files or []

    # Exemption 1: Pure Inquiry
    if intent == "INQUIRY":
        return {
            "intent": intent,
            "is_triggered": False,
            "is_exempt": True,
            "exempt_reason": "Pure inquiry intent (read-only conceptual question or explanation)",
            "matched_domains": [],
            "matched_skills": [],
            "recommended_skill": None,
            "skill_md_path": None,
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
        }

    matched_domains = map_files_to_domains(files)
    skills_data = load_skills_index(repo_root)
    all_skills = skills_data.get("skills", [])

    matched_skills = []
    for s in all_skills:
        s_domain = s.get("domain", "")
        if s_domain in matched_domains:
            matched_skills.append(s)

    # Check if explicit skill keyword or ID is named in prompt
    explicit_skill = None
    prompt_lower = prompt.lower()
    for s in all_skills:
        sid = s.get("id", "")
        if sid in prompt_lower:
            explicit_skill = s
            if s not in matched_skills:
                matched_skills.append(s)
            break

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
        }

    # Triggered! Rank candidate skills by stack_triggers + prompt token overlap
    is_triggered = bool(matched_skills or explicit_skill or (not files and intent in ("ACTION", "DIAGNOSTIC")))

    normalized_prompt = prompt_lower
    if "page object" in normalized_prompt:
        normalized_prompt += " pom"
    if "end to end" in normalized_prompt or "end-to-end" in normalized_prompt:
        normalized_prompt += " e2e"
    prompt_words = set(re.findall(r"[a-z0-9]{2,}", normalized_prompt))

    def _skill_relevance(skill_entry: Dict[str, Any]) -> int:
        score = 0
        triggers = [t.lower() for t in skill_entry.get("stack_triggers", [])]
        for trig in triggers:
            if trig and trig in prompt_words:
                score += 4
        sid_tokens = [tok for tok in skill_entry.get("id", "").lower().split("-") if len(tok) > 2]
        for tok in sid_tokens:
            if tok in prompt_words:
                score += 3
        sum_words = set(re.findall(r"[a-z0-9]{3,}", skill_entry.get("summary", "").lower()))
        score += len(prompt_words & sum_words)
        return score

    if matched_skills:
        matched_skills.sort(key=_skill_relevance, reverse=True)

    recommended_skill = (explicit_skill or (matched_skills[0] if matched_skills else None))
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

    return {
        "intent": intent,
        "is_triggered": is_triggered,
        "is_exempt": not is_triggered,
        "exempt_reason": None if is_triggered else "No matching skill domain or trigger",
        "matched_domains": sorted(list(matched_domains)),
        "matched_skills": matched_skills,
        "recommended_skill": rec_id,
        "skill_md_path": skill_md_path,
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
