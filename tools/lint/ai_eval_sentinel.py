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

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


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
    # Vietnamese grammar stopwords for multilingual transcript audits
    "là", "và", "của", "các", "những", "một", "có", "không", "được", "cho", "với",
    "trong", "trên", "tại", "từ", "đến", "theo", "bằng", "đã", "sẽ", "đang", "này",
    "đó", "khi", "nếu", "thì", "tôi", "bạn", "chúng", "cùng", "rất", "cũng", "để",
    "về", "vào", "ra", "lại", "hay", "hoặc", "nhưng", "mà", "bởi", "vì", "do", "nên",
    "qua", "hơn", "nhất", "cần", "phải", "chỉ", "mới", "trước", "sau", "đây", "đều",
    "tiếp", "toàn", "diện", "công", "cụ", "chuẩn", "câu", "kịch", "bản", "trên",
}


def extract_keywords(text: str) -> List[str]:
    """Extracts non-stopword alphanumeric tokens after normalizing markdown links."""
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    tokens = re.findall(r"\b[a-zA-Z0-9_\u00C0-\u024F\u1EA0-\u1EF9]{2,}\b", cleaned.lower())
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


_NUM_UNIT_RE = re.compile(r"(?<![A-Za-z0-9_.])\d+(?:[\.,]\d+)?(?=[A-Za-z%]*\b)")


def compute_faithfulness(answer: str, context: str) -> Dict[str, Any]:
    """
    Evaluates whether answer statements are grounded in context (Groundedness / Anti-Hallucination).
    Computes grounded statement ratio and flags ungrounded sentences.
    """
    sentences = split_sentences(answer)
    if not sentences:
        return {"score": 1.0, "is_faithful": True, "hallucinated_claims": [], "total_claims": 0}

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

        # Check for numeric or entity drift (handles unit-attached literals such as 1500ms, 5s, 50.0%)
        numbers_in_sentence = _NUM_UNIT_RE.findall(s)
        numbers_valid = all(
            re.search(rf"(?<![A-Za-z0-9_.]){re.escape(num)}(?=[A-Za-z%]*\b)", context_lower)
            for num in numbers_in_sentence
        )

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


def compute_context_metrics(query: str, context: str, answer: str) -> Tuple[float, float]:
    """Computes Context Precision (retrieval signal-to-noise) and Context Recall (answer coverage)."""
    ctx_chunks = split_sentences(context)
    if not ctx_chunks and context.strip():
        ctx_chunks = [context.strip()]

    qa_tokens = set(extract_keywords(query)) | set(extract_keywords(answer))
    if ctx_chunks and qa_tokens:
        relevant_chunks = 0
        for ch in ctx_chunks:
            ch_lower = ch.lower()
            ch_tokens = set(extract_keywords(ch))
            if any(is_token_grounded(t, ch_tokens, ch_lower) for t in qa_tokens):
                relevant_chunks += 1
        context_precision = round(relevant_chunks / len(ctx_chunks), 2)
    else:
        context_precision = 0.0

    ctx_lower = context.lower()
    ctx_tokens = set(extract_keywords(context))
    a_tokens = set(extract_keywords(answer))
    if a_tokens:
        covered = [t for t in a_tokens if is_token_grounded(t, ctx_tokens, ctx_lower)]
        context_recall = round(len(covered) / len(a_tokens), 2)
    else:
        context_recall = 1.0 if context.strip() else 0.0

    return context_precision, context_recall


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

    # 3. Relevance & Context Precision/Recall checks
    relevance_score = compute_answer_relevance(query, answer)
    context_precision, context_recall = compute_context_metrics(query, context, answer)

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
        "context_precision": context_precision,
        "context_recall": context_recall,
        "security": {
            "adversarial_detected": is_injected,
            "patterns": injection_reasons,
        },
    }


_ENVELOPE_TAG_PATTERNS = (
    re.compile(r"<ADDITIONAL_METADATA>[\s\S]*?</ADDITIONAL_METADATA>", re.IGNORECASE),
    re.compile(r"<USER_SETTINGS_CHANGE>[\s\S]*?</USER_SETTINGS_CHANGE>", re.IGNORECASE),
    re.compile(r"<SYSTEM_MESSAGE>[\s\S]*?</SYSTEM_MESSAGE>", re.IGNORECASE),
)
_USER_REQUEST_TAG_RE = re.compile(r"</?USER_REQUEST>", re.IGNORECASE)
_MAX_FULL_STEP_CHARS = 16384


def sanitize_user_query_envelope(raw_query: str) -> str:
    """Strips injected system metadata envelopes from USER_INPUT while preserving user request text."""
    if not raw_query or not isinstance(raw_query, str):
        return ""
    cleaned = raw_query
    for pat in _ENVELOPE_TAG_PATTERNS:
        cleaned = pat.sub(" ", cleaned)
    cleaned = _USER_REQUEST_TAG_RE.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def load_full_transcript_steps(transcript_path: str, needed_steps: set[int]) -> Dict[int, str]:
    """Streams sibling transcript_full.jsonl line-by-line, hydrating needed step_index records capped at 16 KB."""
    if not needed_steps:
        return {}
    abs_path = os.path.abspath(transcript_path)
    if os.path.basename(abs_path) == "transcript_full.jsonl":
        full_path = abs_path
    else:
        full_path = os.path.join(os.path.dirname(abs_path), "transcript_full.jsonl")
    if not os.path.exists(full_path):
        return {}

    hydrated: Dict[int, str] = {}
    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            step_idx = obj.get("step_index")
            if step_idx in needed_steps:
                parts: List[str] = []
                content = obj.get("content", "")
                if content:
                    parts.append(str(content))
                tool_calls = obj.get("tool_calls") or []
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            parts.append(f"{tc.get('name', '')} {json.dumps(tc.get('args', ''), ensure_ascii=False)}")
                combined = " ".join(parts).strip()
                if combined:
                    hydrated[step_idx] = combined[:_MAX_FULL_STEP_CHARS]
                if len(hydrated) == len(needed_steps):
                    break
    return hydrated


def audit_agent_transcript(transcript_path: str) -> Dict[str, Any]:
    """
    Parses an Antigravity/Agent JSONL transcript and evaluates the model's
    claims against actual tool call outputs, tool invocations, system messages,
    and user prompts. Enforces fail-closed security and 0-turn inconclusive verdicts.
    """
    if not os.path.exists(transcript_path):
        raise FileNotFoundError(f"Transcript file not found: {transcript_path}")

    events: List[Dict[str, Any]] = []
    needed_steps: set[int] = set()
    with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(obj, dict):
                continue
            events.append(obj)
            if obj.get("truncated_fields") and obj.get("step_index") is not None:
                needed_steps.add(obj["step_index"])

    full_steps = load_full_transcript_steps(transcript_path, needed_steps)

    turns = []
    cur_query = ""
    cur_context: List[str] = []
    system_context: List[str] = []

    for obj in events:
        stype = obj.get("type")
        step_idx = obj.get("step_index", 0)
        if obj.get("truncated_fields") and step_idx in full_steps:
            content = full_steps[step_idx]
        else:
            content = obj.get("content", "")

        if stype == "USER_INPUT":
            cleaned_q = sanitize_user_query_envelope(str(content))
            cur_query = cleaned_q
            cur_context = [cleaned_q[:2000]] if cleaned_q else []
        elif stype == "SYSTEM_MESSAGE":
            if content:
                system_context.append(str(content)[:4000])
        elif stype in ("GENERIC", "TOOL_RESULT", "TOOL_OUTPUT"):
            if content:
                cur_context.append(str(content)[:4000])
        elif stype == "PLANNER_RESPONSE":
            tool_calls = obj.get("tool_calls") or []
            has_tool_calls = isinstance(tool_calls, list) and len(tool_calls) > 0
            if has_tool_calls:
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        t_name = tc.get("name", "")
                        t_args = tc.get("args", "")
                        cur_context.append(f"{t_name} {json.dumps(t_args, ensure_ascii=False)[:1500]}")
            if content and cur_query:
                all_ctx = system_context + cur_context
                combined_context = " ".join(all_ctx) if all_ctx else cur_query
                turns.append({
                    "step_index": step_idx,
                    "query": cur_query[:500],
                    "context": combined_context,
                    "answer": str(content),
                    "has_tool_calls": has_tool_calls,
                })

    evaluated_turns = []
    total_faithfulness = 0.0
    security_blocked_turns = 0
    hallucination_turns = 0

    for t in turns:
        res = evaluate_rag_triplet(t["query"], t["context"], t["answer"])
        verdict = res["verdict"]
        if t["has_tool_calls"] and verdict == "FAIL_IRRELEVANT":
            verdict = "PASS"
        if verdict == "BLOCKED_SECURITY":
            security_blocked_turns += 1
        if verdict == "FAIL_HALLUCINATION" or not res["faithfulness"]["is_faithful"]:
            hallucination_turns += 1

        total_faithfulness += res["faithfulness"]["score"]
        evaluated_turns.append({
            "step_index": t["step_index"],
            "query_summary": t["query"][:80],
            "faithfulness_score": res["faithfulness"]["score"],
            "is_faithful": res["faithfulness"]["is_faithful"],
            "hallucinated_claims": res["faithfulness"]["hallucinated_claims"],
            "is_progress_turn": t["has_tool_calls"],
            "verdict": verdict,
        })

    if not turns:
        avg_faithfulness = 0.0
        overall_faithfulness_rate = 0.0
        is_trustworthy = False
        audit_status = "INCONCLUSIVE"
    else:
        avg_faithfulness = round(total_faithfulness / len(turns), 2)
        overall_faithfulness_rate = round(avg_faithfulness * 100, 1)
        is_trustworthy = (
            (avg_faithfulness >= 0.80)
            and (security_blocked_turns == 0)
            and (hallucination_turns == 0)
        )
        if is_trustworthy:
            audit_status = "PASS"
        elif security_blocked_turns > 0:
            audit_status = "BLOCKED_SECURITY"
        else:
            audit_status = "FAIL"

    return {
        "standard": "NIST AI RMF 1.0 Agent Transcript Hallucination Audit",
        "transcript_path": transcript_path,
        "audit_status": audit_status,
        "total_conversation_turns": len(turns),
        "overall_faithfulness_rate": overall_faithfulness_rate,
        "is_trustworthy": is_trustworthy,
        "security_blocked_turns": security_blocked_turns,
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
        if args.gate_safety and res.get("security_blocked_turns", 0) > 0:
            print(f"🚨 Quality Gate Failed: {res['security_blocked_turns']} adversarial injection turn(s) detected in transcript!", file=sys.stderr)
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
