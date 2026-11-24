#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Pocock Grilling Primitive & Requirements Interrogation Engine (Matt Pocock Pattern)
-----------------------------------------------------------------------------------
Calculates the prerequisite decision frontier for ambiguous user stories.
Batches structured multiple-choice questions with explicit (Recommended) defaults,
strictly adhering to the Fact/Decision boundary (never asking for facts ascertainable
directly from the codebase).

Reference:
  - Matt Pocock (The Grilling Primitive: Frontier Decision Interrogation).
  - Synapse-Hub Subsystem 6: Section 6.7 of agent_skill_training_analysis.md.
"""
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


import sys
import re
import json
import argparse
from typing import List, Dict, Any

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


MAX_STORY_CHARS = 50000

DOMAIN_TRIGGERS: Dict[str, str] = {
    "payment": r"\b(?:pay|payment|checkout|invoice|card|stripe|refund|currency|price|amount|billing)\b",
    "auth": r"\b(?:login|auth|password|token|jwt|oauth|mfa|otp|rbac|role|permission|session)\b",
    "upload": r"\b(?:upload|file|attachment|image|pdf|csv|xlsx|import|document)\b",
    "state_machine": r"\b(?:approve|reject|cancel|draft|pending|status|state|workflow|transition)\b",
    "concurrency": r"\b(?:concurrent|concurrency|stock|inventory|quota|voucher|slot|double|race|lock)\b",
}

DOMAIN_QUESTIONS: Dict[str, Dict[str, Any]] = {
    "payment": {
        "question": "Payment Idempotency & Currency Frontier: How should duplicate payment submissions and currency rounding be enforced?",
        "is_multi_select": False,
        "options": [
            "(Recommended) Require Idempotency-Key header, block double-submit UI clicks, and enforce integer minor-unit rounding",
            "Allow client retries without idempotency keys and rely on manual finance reconciliation",
            "Accept floating-point amounts and round only on display",
        ],
    },
    "auth": {
        "question": "Authorization & Session Frontier: What should happen on privilege escalation (IDOR) or expired session tokens?",
        "is_multi_select": False,
        "options": [
            "(Recommended) Enforce server-side RBAC/ownership checks returning 403 Forbidden and 401 on expired tokens",
            "Hide restricted actions only in the frontend UI",
            "Silently redirect unauthorized requests to the home dashboard with HTTP 200",
        ],
    },
    "upload": {
        "question": "File Upload Validation Frontier: Which server-side constraints govern uploaded artifacts?",
        "is_multi_select": False,
        "options": [
            "(Recommended) Validate MIME magic bytes, enforce max byte limit (413/400), and sanitize filenames",
            "Validate file extension only on the client input element",
            "Accept arbitrary file sizes and store original user filenames verbatim",
        ],
    },
    "state_machine": {
        "question": "State Transition Frontier: How must illegal or backward lifecycle transitions be handled?",
        "is_multi_select": False,
        "options": [
            "(Recommended) Enforce an explicit transition allowlist and reject illegal jumps with HTTP 409 Conflict",
            "Allow any state to overwrite any other state unconditionally",
            "Log a warning and mutate the status anyway",
        ],
    },
    "concurrency": {
        "question": "Resource Contention & Concurrency Frontier: How should simultaneous writes to limited inventory or shared records resolve?",
        "is_multi_select": False,
        "options": [
            "(Recommended) Enforce optimistic locking / atomic DB conditional update returning 409 Conflict to the losing request",
            "Use last-write-wins without version checks",
            "Queue requests without conflict feedback",
        ],
    },
}


class PocockGriller:
    """Interrogates user stories along the prerequisite decision frontier."""

    def __init__(self, target_framework: str = "Playwright_TS"):
        self.target_framework = target_framework

    def detect_domains(self, story_text: str) -> List[str]:
        """Detect risk-relevant requirement domains from bounded story text."""
        bounded = (story_text or "")[:MAX_STORY_CHARS]
        return [
            domain
            for domain, pattern in DOMAIN_TRIGGERS.items()
            if re.search(pattern, bounded, re.IGNORECASE)
        ]

    def generate_frontier_questions(self, story_text: str, grill_me: bool = False) -> List[Dict[str, Any]]:
        """
        Analyze requirement text and return batched English decision questions.
        Only generates questions for true decision forks, never for discoverable codebase facts.
        In grill_me mode (Matt Pocock pattern), aggressively probes boundary, race, and failure forks.
        """
        bounded = (story_text or "").strip()[:MAX_STORY_CHARS]
        domains = self.detect_domains(bounded)
        questions: List[Dict[str, Any]] = []

        # 1. Execution Scope Boundary
        questions.append({
            "question": f"Execution Scope Frontier ({self.target_framework}): Which verification layer should cover this story?",
            "is_multi_select": False,
            "options": [
                "(Recommended) End-to-End (E2E) UI Automation using Clean POM paired with API payload assertions",
                "Headless API Functional Suite only (no browser interaction)",
                "Minimal Happy Path Smoke check only",
            ],
        })

        # 2. Test Data Lifecycle & Idempotency
        if not re.search(r"\b(?:mock|stub|seed)\b", bounded, re.IGNORECASE):
            questions.append({
                "question": "Test Data Lifecycle Frontier: How should test entities be provisioned and cleaned up?",
                "is_multi_select": False,
                "options": [
                    "(Recommended) Generate unique runtime identifiers (uniqueCode) with automated teardown cleanup",
                    "Reuse static pre-seeded accounts from environment configuration",
                    "Intercept and mock network responses without mutating database state",
                ],
            })

        # 3. Assertion Boundary & Negative Vectors
        questions.append({
            "question": "Assertion & Negative Coverage Frontier: Which non-happy-path behaviors are required in acceptance criteria?",
            "is_multi_select": True,
            "options": [
                "(Recommended) Required-field validation errors and exact error feedback assertions",
                "(Recommended) Submit action disabled/guarded state while form inputs are invalid",
                "Network timeout and transient 5xx fault recovery behavior",
                "Unauthorized / Forbidden (401/403) access denial verification",
            ],
        })

        # 4. Story-Aware Domain Frontier Questions
        for domain in domains:
            questions.append(DOMAIN_QUESTIONS[domain])

        # 5. Matt Pocock Grilling Mode (Aggressive Boundary & Race Probing)
        if grill_me:
            if "concurrency" not in domains:
                questions.append({
                    "question": "Pocock Concurrency Frontier: How must double-submit clicks or concurrent edits on the same entity behave?",
                    "is_multi_select": False,
                    "options": [
                        "(Recommended) Enforce Idempotency-Key / UI debounce and return 409 Conflict on stale writes",
                        "Allow Last-Write-Wins overwrite without conflict error",
                        "Enqueue mutations sequentially without user feedback",
                    ],
                })
            questions.append({
                "question": "Pocock Fuzzing & Malformed Payload Frontier: What is the contract for empty, oversized, or special-character payloads?",
                "is_multi_select": False,
                "options": [
                    "(Recommended) Reject at client & server schema boundaries with explicit 400 Bad Request errors",
                    "Silently truncate oversized fields and persist partial input",
                    "Persist raw unvalidated payloads directly to storage",
                ],
            })

        return questions


def main():
    parser = argparse.ArgumentParser(description="Pocock Grilling Primitive Engine")
    parser.add_argument("story", nargs="?", default="", help="User story or requirement text")
    parser.add_argument("--story-file", default="", help="Path to a Markdown or text file containing the user story")
    parser.add_argument("--grill-me", action="store_true", help="Explicit grill-me mode (Matt Pocock pattern)")
    parser.add_argument("--json", action="store_true", help="Output questions in JSON format")
    args = parser.parse_args()

    story_source = "inline"
    if args.story_file:
        if not os.path.isfile(args.story_file):
            err_msg = f"Story file not found: {args.story_file}"
            if args.json:
                print(json.dumps({"status": "ERROR", "error": err_msg}), file=sys.stderr)
            else:
                print(err_msg, file=sys.stderr)
            return 1
        with open(args.story_file, "r", encoding="utf-8", errors="replace") as fh:
            story_text = fh.read(MAX_STORY_CHARS)
        story_source = args.story_file
    else:
        story_text = args.story or "User Story: As a registered user, I want to approve invoices with attached receipts."
        if not args.story:
            story_source = "default_sample"

    griller = PocockGriller()
    domains = griller.detect_domains(story_text)
    questions = griller.generate_frontier_questions(story_text, grill_me=args.grill_me)

    if args.json:
        print(json.dumps({
            "story": story_text[:500],
            "story_source": story_source,
            "detected_domains": domains,
            "questions": questions,
        }, indent=2))
        return 0

    print("\n" + "=" * 70)
    print("  POCOCK GRILLING PRIMITIVE (PREREQUISITE DECISION FRONTIER)")
    print("=" * 70)
    print(f"Story Source     : {story_source}")
    print(f"Detected Domains : {', '.join(domains) if domains else 'general'}")
    print(f"Target Story     : {story_text[:200]}\n")
    print(f"Generated {len(questions)} batched decision questions with recommended defaults:\n")

    for idx, q in enumerate(questions, 1):
        print(f"Q{idx}: {q['question']}")
        for opt in q["options"]:
            print(f"   - {opt}")
        print()
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
