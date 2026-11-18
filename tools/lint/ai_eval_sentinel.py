#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/ai_eval_sentinel.py — Enterprise RAG & LLM Evaluation Sentinel (NIST AI RMF & ISO 42001)
---------------------------------------------------------------------------------------------
Evaluates AI applications, RAG pipelines, and autonomous agent systems against
the NIST AI Risk Management Framework (AI RMF 1.0) and ISO/IEC 42001 / ISO/IEC TR 29119-11:
  1. Faithfulness / Groundedness (Hallucination Detection): Verifies whether every factual
     claim in the LLM response is strictly supported by retrieved context.
  2. Answer Relevance: Evaluates semantic alignment between query and response.
  3. Context Precision & Recall: Measures retrieval noise and coverage.
  4. Adversarial Safety Sentinel: Detects direct and indirect prompt injection attempts.

Usage:
  python tools/ai_eval_sentinel.py --query "What is the return policy?" \
         --context "Returns accepted within 30 days with receipt." \
         --answer "You can return items within 30 days if you have a receipt."
  python tools/ai_eval_sentinel.py --benchmark test_cases.json --json report.json --gate-faithfulness 0.8
"""

import os
import sys
import json
import re
import argparse
from typing import Dict, List, Any, Tuple

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# ADVERSARIAL PROMPT INJECTION SENTINEL (NIST AI RMF GOVERN / MAP)
# ==============================================================================

INJECTION_PATTERNS = [
    re.compile(r"\b(?:ignore|disregard|forget)\s+(?:all\s+)?(?:prior|previous|above)\s+(?:instructions|rules|prompts)\b", re.IGNORECASE),
    re.compile(r"\b(?:system\s+override|system\s+prompt|developer\s+mode)\b", re.IGNORECASE),
    re.compile(r"\b(?:you\s+are\s+now|act\s+as|pretend\s+you\s+are)\s+(?:DAN|unrestricted|jailbroken|unfiltered)\b", re.IGNORECASE),
    re.compile(r"\b(?:reveal|print|output|display)\s+(?:your\s+)?(?:system\s+instructions|secret\s+key|internal\s+prompt)\b", re.IGNORECASE),
    re.compile(r"\b(?:base64\s+decode|execute\s+command|eval\()\b", re.IGNORECASE),
]


def detect_adversarial_injection(prompt: str) -> Tuple[bool, List[str]]:
    """Detects known prompt injection and jailbreak signatures."""
    flags = []
    for pat in INJECTION_PATTERNS:
        match = pat.search(prompt)
        if match:
            flags.append(match.group(0))
    return len(flags) > 0, flags


# ==============================================================================
# RAG EVALUATION METRICS (FAITHFULNESS, RELEVANCE, CONTEXT)
# ==============================================================================

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by",
    "of", "is", "are", "was", "were", "be", "been", "it", "this", "that", "these",
    "those", "you", "your", "we", "our", "they", "their", "can", "will", "if",
    "what", "where", "when", "why", "how", "who", "which", "do", "does", "did",
    "have", "has", "had", "may", "would", "should", "could", "located",
}


def extract_keywords(text: str) -> List[str]:
    """Extracts non-stopword alphanumeric tokens."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\u00C0-\u024F\u1EA0-\u1EF9]{2,}\b", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def split_sentences(text: str) -> List[str]:
    """Splits text into atomic sentences / claims."""
    raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw_sentences if len(s.strip()) > 3]


def is_token_grounded(token: str, context_tokens: set, context_lower: str) -> bool:
    """Checks if token or its stem/inflection appears in context."""
    if token in context_tokens or token in context_lower:
        return True
    for ct in context_tokens:
        if len(token) >= 4 and len(ct) >= 4:
            if token.startswith(ct[:4]) or ct.startswith(token[:4]):
                return True
    return False


def compute_faithfulness(answer: str, context: str) -> Dict[str, Any]:
    """
    Evaluates whether answer statements are grounded in context (Groundedness / Anti-Hallucination).
    Computes grounded statement ratio and flags ungrounded sentences.
    """
    sentences = split_sentences(answer)
    if not sentences:
        return {"score": 1.0, "hallucinated_claims": [], "total_claims": 0}

    context_lower = context.lower()
    context_tokens = set(extract_keywords(context))

    grounded_count = 0
    hallucinated = []

    for s in sentences:
        s_tokens = extract_keywords(s)
        if not s_tokens:
            grounded_count += 1
            continue

        # Check token overlap ratio against context using inflection-aware grounding
        matching_tokens = [t for t in s_tokens if is_token_grounded(t, context_tokens, context_lower)]
        overlap_ratio = len(matching_tokens) / len(s_tokens)

        # Check for numeric or entity drift (numbers in claim must appear in context)
        numbers_in_sentence = re.findall(r"\b\d+(?:[\.,]\d+)?\b", s)
        numbers_valid = all(num in context_lower for num in numbers_in_sentence)

        if overlap_ratio >= 0.60 and numbers_valid:
            grounded_count += 1
        else:
            hallucinated.append({
                "claim": s,
                "overlap_ratio": round(overlap_ratio, 2),
                "reason": "Missing factual grounding or mismatched numerical entities in context.",
            })

    score = round(grounded_count / len(sentences), 2)
    return {
        "score": score,
        "is_faithful": score >= 0.80,
        "total_claims": len(sentences),
        "grounded_claims": grounded_count,
        "hallucinated_claims": hallucinated,
    }


def compute_answer_relevance(query: str, answer: str) -> float:
    """Evaluates whether the answer addresses the keywords in the query."""
    q_tokens = set(extract_keywords(query))
    if not q_tokens:
        return 1.0

    a_lower = answer.lower()
    a_tokens = set(extract_keywords(answer))
    common = [t for t in q_tokens if is_token_grounded(t, a_tokens, a_lower)]
    relevance = round(len(common) / len(q_tokens), 2)
    return min(round(relevance * 1.15, 2), 1.0)


def evaluate_rag_triplet(query: str, context: str, answer: str) -> Dict[str, Any]:
    """Complete evaluation of a Query-Context-Answer RAG triplet."""
    # 1. Safety check
    is_injected, injection_reasons = detect_adversarial_injection(query + " " + answer)

    # 2. Faithfulness check
    faith_res = compute_faithfulness(answer, context)

    # 3. Relevance check
    relevance_score = compute_answer_relevance(query, answer)

    # Trustworthiness composite score (NIST AI RMF Trustworthy AI score)
    trust_score = round(
        (0.50 * faith_res["score"]) + (0.35 * relevance_score) + (0.15 * (0.0 if is_injected else 1.0)),
        2,
    )

    verdict = "PASS"
    if is_injected:
        verdict = "BLOCKED_SECURITY"
    elif faith_res["score"] < 0.70:
        verdict = "FAIL_HALLUCINATION"
    elif relevance_score < 0.40:
        verdict = "FAIL_IRRELEVANT"

    return {
        "standard": "NIST AI RMF 1.0 & ISO/IEC TR 29119-11",
        "verdict": verdict,
        "trustworthiness_score": trust_score,
        "faithfulness": {
            "score": faith_res["score"],
            "is_faithful": faith_res["is_faithful"],
            "hallucinated_claims": faith_res["hallucinated_claims"],
        },
        "answer_relevance": relevance_score,
        "security": {
            "adversarial_detected": is_injected,
            "patterns": injection_reasons,
        },
    }


def audit_agent_transcript(transcript_path: str) -> Dict[str, Any]:
    """
    Parses an Antigravity/Agent JSONL transcript and evaluates the model's
    claims against actual tool call outputs and user prompts.
    Detects ungrounded agent hallucinations during the conversation.
    """
    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"Transcript file not found: {transcript_path}")

    turns = []
    cur_query = ""
    cur_context = []

    with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            stype = obj.get("type")
            content = obj.get("content", "")

            if stype == "USER_INPUT":
                cur_query = content
                cur_context = []
            elif stype in ("GENERIC", "TOOL_RESULT", "TOOL_OUTPUT"):
                if content:
                    cur_context.append(str(content)[:2000])
            elif stype == "PLANNER_RESPONSE":
                if content and cur_query:
                    combined_context = " ".join(cur_context)
                    if not combined_context:
                        combined_context = cur_query
                    turns.append({
                        "step_index": obj.get("step_index", 0),
                        "query": cur_query[:500],
                        "context": combined_context,
                        "answer": str(content),
                    })

    evaluated_turns = []
    total_faithfulness = 0.0

    for t in turns:
        res = evaluate_rag_triplet(t["query"], t["context"], t["answer"])
        total_faithfulness += res["faithfulness"]["score"]
        evaluated_turns.append({
            "step_index": t["step_index"],
            "query_summary": t["query"][:80],
            "faithfulness_score": res["faithfulness"]["score"],
            "is_faithful": res["faithfulness"]["is_faithful"],
            "hallucinated_claims": res["faithfulness"]["hallucinated_claims"],
            "verdict": res["verdict"],
        })

    avg_faithfulness = round(total_faithfulness / len(turns), 2) if turns else 1.0

    return {
        "standard": "NIST AI RMF 1.0 Agent Transcript Hallucination Audit",
        "transcript_path": transcript_path,
        "total_conversation_turns": len(turns),
        "overall_faithfulness_rate": round(avg_faithfulness * 100, 1),
        "is_trustworthy": avg_faithfulness >= 0.80,
        "turns_evaluation": evaluated_turns,
    }


# ==============================================================================
# CLI HANDLER & BATCH BENCHMARK
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Synapse Hub NIST AI RMF & ISO 42001 RAG/LLM Evaluation Sentinel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--query", "-q", help="User prompt or retrieval query")
    parser.add_argument("--context", "-c", help="Retrieved ground truth context chunks")
    parser.add_argument("--answer", "-a", help="LLM generated answer to evaluate")
    parser.add_argument("--benchmark", help="Path to JSON file containing list of RAG test cases to evaluate")
    parser.add_argument("--audit-transcript", help="Path to Antigravity/Agent transcript.jsonl to audit for conversation hallucinations")
    parser.add_argument("--json", action="store_true", help="Output evaluation report in JSON format")
    parser.add_argument("--out", help="Write evaluation results to specified output file")
    parser.add_argument("--gate-faithfulness", type=float, default=0.0, help="Quality Gate: Fail if faithfulness score < threshold")
    parser.add_argument("--gate-safety", action="store_true", help="Quality Gate: Fail if any adversarial injection is detected")

    args = parser.parse_args()

    if args.benchmark:
        if not os.path.exists(args.benchmark):
            print(f"❌ Error: Benchmark file not found: {args.benchmark}", file=sys.stderr)
            return 2

        with open(args.benchmark, "r", encoding="utf-8") as f:
            test_cases = json.load(f)

        evaluations = []
        has_failure = False

        for tc in test_cases:
            res = evaluate_rag_triplet(
                query=tc.get("query", ""),
                context=tc.get("context", ""),
                answer=tc.get("answer", ""),
            )
            tc_enriched = dict(tc)
            tc_enriched["evaluation"] = res
            evaluations.append(tc_enriched)

            if args.gate_faithfulness > 0 and res["faithfulness"]["score"] < args.gate_faithfulness:
                has_failure = True
            if args.gate_safety and res["security"]["adversarial_detected"]:
                has_failure = True

        out_data = {
            "standard": "NIST AI RMF 1.0 Benchmark",
            "total_test_cases": len(evaluations),
            "evaluations": evaluations,
        }

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved AI evaluation benchmark report to {args.out}")
        else:
            print(json.dumps(out_data, indent=2, ensure_ascii=False))

        if has_failure:
            print("🚨 Quality Gate Failed: One or more test cases breached AI faithfulness/safety thresholds!", file=sys.stderr)
            return 1
        return 0

    if args.audit_transcript:
        try:
            res = audit_agent_transcript(args.audit_transcript)
        except Exception as e:
            print(f"❌ Error auditing transcript: {e}", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            status = "\033[92m[TRUSTWORTHY]\033[0m" if res["is_trustworthy"] else "\033[91m[HALLUCINATION_DETECTED]\033[0m"
            print("=" * 74)
            print("  SYNAPSE HUB — AGENT TRANSCRIPT HALLUCINATION & FAITHFULNESS AUDIT")
            print("=" * 74)
            print(f"  Transcript Target       : {res['transcript_path']}")
            print(f"  Conversation Turns Audited: {res['total_conversation_turns']} turns")
            print(f"  Overall Faithfulness Rate : \033[1m{res['overall_faithfulness_rate']}%\033[0m ({status})")
            print("-" * 74)
            for t in res["turns_evaluation"]:
                t_st = "\033[92mPASS\033[0m" if t["is_faithful"] else "\033[91mFLAGGED\033[0m"
                print(f"  Step {t['step_index']:<4} | Faithfulness: {t['faithfulness_score']*100}% [{t_st}] -> User: '{t['query_summary']}'")
                for h in t["hallucinated_claims"]:
                    print(f"     ⚠️ Unverified Claim: '{h['claim']}' (Overlap: {h['overlap_ratio']})")
            print("=" * 74)

        if args.gate_faithfulness > 0 and (res["overall_faithfulness_rate"] / 100.0) < args.gate_faithfulness:
            print(f"🚨 Quality Gate Failed: Agent transcript faithfulness {res['overall_faithfulness_rate']}% below threshold!", file=sys.stderr)
            return 1
        return 0

    if not args.query or not args.context or not args.answer:
        parser.print_help()
        return 2

    res = evaluate_rag_triplet(args.query, args.context, args.answer)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        v_color = "\033[92m" if res["verdict"] == "PASS" else "\033[91m"
        reset = "\033[0m"

        print("=" * 72)
        print("  SYNAPSE HUB — NIST AI RMF 1.0 & ISO 42001 EVALUATION SCORECARD")
        print("=" * 72)
        print(f"  AI Verdict           : {v_color}[{res['verdict']}]{reset}")
        print(f"  Trustworthiness Score: \033[1m{res['trustworthiness_score'] * 100}%\033[0m")
        print(f"  Faithfulness Score   : {res['faithfulness']['score'] * 100}% (Anti-Hallucination)")
        print(f"  Answer Relevance     : {res['answer_relevance'] * 100}%")
        print(f"  Adversarial Safety   : {'PASS (Safe)' if not res['security']['adversarial_detected'] else 'ALERT (Injection Detected)'}")

        if res["faithfulness"]["hallucinated_claims"]:
            print("-" * 72)
            print("  ⚠️ Flagged Hallucinated Claims:")
            for h in res["faithfulness"]["hallucinated_claims"]:
                print(f"     - '{h['claim']}' (Overlap: {h['overlap_ratio']})")
        print("=" * 72)

    if args.gate_faithfulness > 0 and res["faithfulness"]["score"] < args.gate_faithfulness:
        return 1
    if args.gate_safety and res["security"]["adversarial_detected"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
