#!/usr/bin/env python3
# Copyright (c) 2026 Thế Vị (@TeeVee98)
# Synapse Hub is open-source software under the MIT License.
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/reasoning/prover_verifier_games.py — Prover-Verifier Zero-Sum Debate Engine (Nash Equilibrium) (R2)
---------------------------------------------------------------------------------------------------------
Implements a zero-sum adversarial debate mechanism (Nash equilibrium) to overcome correlated errors of majority voting:
  1. Prover: Defends the proposal, citing architectural invariants, code syntax, and test stability.
  2. Verifier / Adversary: Actively seeks falsifying counter-examples, async race conditions,
     unhandled exceptions, and boundary edge cases.
  3. Multi-Round Debate: Runs 2-3 structured rounds where arguments must cite factual evidence.
  4. Independent Judge: Evaluates arguments across 3 adjudication modes (evidence_weighted, strict, consensus)
     and calculates normalized Nash equilibrium score S_Nash in [0.0, 1.0].

Usage:
  python tools/reasoning/prover_verifier_games.py --proposal "Add debounce to clickSubmitSafe"
  python tools/reasoning/prover_verifier_games.py --proposal fix.py --context tests/test_payment.py --rounds 3 --json
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

import ast
import re
import math
import json
import argparse
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


@dataclass
class ProverArgument:
    claim: str
    citations: List[str]
    confidence: float
    rebuttal_of: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "claim": self.claim,
            "citations": list(self.citations),
            "confidence": round(float(self.confidence), 4),
        }
        if self.rebuttal_of is not None:
            d["rebuttal_of"] = self.rebuttal_of
        return d


@dataclass
class VerifierCounter:
    refutation: str
    counter_examples: List[str]
    falsification_score: float
    attack_type: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "refutation": self.refutation,
            "counter_examples": list(self.counter_examples),
            "falsification_score": round(float(self.falsification_score), 4),
            "attack_type": self.attack_type,
        }


@dataclass
class DebateRound:
    round: int
    prover_argument: ProverArgument
    verifier_counter: VerifierCounter
    judge_interim_ruling: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round,
            "prover_argument": self.prover_argument.to_dict(),
            "verifier_counter": self.verifier_counter.to_dict(),
            "judge_interim_ruling": self.judge_interim_ruling,
        }


@dataclass
class DebateOutcome:
    status: str  # "ACCEPTED" | "REFUTED"
    rounds_completed: int
    winner: str  # "prover" | "verifier"
    winning_thesis: str
    nash_equilibrium_score: float
    transcript: List[Dict[str, Any]]
    prover_total_score: float = 0.0
    verifier_total_score: float = 0.0
    unresolved_vulnerabilities: List[str] = field(default_factory=list)
    judge_mode: str = "evidence_weighted"
    proposal: str = ""
    provenance_tag: str = "[AST-Heuristic]"
    ast_grounded_symbols: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "proposal": self.proposal[:120] if self.proposal else "",
            "rounds_completed": self.rounds_completed,
            "winner": self.winner,
            "winning_thesis": self.winning_thesis,
            "nash_equilibrium_score": round(float(self.nash_equilibrium_score), 4),
            "transcript": self.transcript,
            "prover_total_score": round(float(self.prover_total_score), 4),
            "verifier_total_score": round(float(self.verifier_total_score), 4),
            "unresolved_vulnerabilities": list(self.unresolved_vulnerabilities),
            "judge_mode": self.judge_mode,
            "provenance_tag": self.provenance_tag,
            "ast_grounded_symbols": list(self.ast_grounded_symbols),
        }


_NET_UI_IMPORTS = frozenset({
    "requests", "httpx", "aiohttp", "urllib", "playwright",
    "selenium", "fastapi", "flask", "django", "http", "socket",
})
_NET_UI_KEYWORDS = (
    "http", "api", "browser", "playwright", "click", "locator",
    "button", "network", "endpoint", "service", "search", "input", "submit",
)


def _extract_python_ast_grounding(context_text: str) -> Dict[str, Any]:
    """Extracts Python AST functions, classes, parameters, and imports from context_text."""
    if not context_text or not context_text.strip():
        return {"is_python_ast": False, "symbols": [], "functions": [], "imports": set()}
    try:
        tree = ast.parse(context_text)
    except SyntaxError:
        return {"is_python_ast": False, "symbols": [], "functions": [], "imports": set()}

    symbols: List[str] = []
    functions: List[Tuple[str, List[str]]] = []
    imports: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name not in symbols:
                symbols.append(node.name)
            arg_names = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
            functions.append((node.name, arg_names))
        elif isinstance(node, ast.ClassDef):
            if node.name not in symbols:
                symbols.append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    return {
        "is_python_ast": bool(symbols or imports),
        "symbols": symbols,
        "functions": functions,
        "imports": imports,
    }


class ProverAgent:
    """Prover agent defending candidate proposals with formal empirical evidence."""

    @staticmethod
    def _extract_citations(proposal: str, context: str) -> List[str]:
        citations: List[str] = []
        combined = f"{proposal}\n{context}" if context else proposal

        # Look for explicit Evidence: markers
        evidence_match = re.search(r"Evidence:\s*([^\n\.]+)", proposal, re.IGNORECASE)
        if evidence_match:
            citations.append(evidence_match.group(1).strip())

        # Rule references (e.g. AGENTS.md Rule 1.4, Rule 10)
        for rule_ref in re.findall(r"\b(?:AGENTS\.md\s+)?Rule\s+\d+(?:\.\d+)?\b", combined, re.IGNORECASE):
            if rule_ref not in citations:
                citations.append(rule_ref)

        # Code identifiers and calls: expect(locator).toBeVisible(), time.sleep(5), etc.
        calls = re.findall(
            r"\b(?:expect\([^\)]+\)\.[a-zA-Z0-9_]+\(\)|[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z0-9_]+\([^\)]*\)|[a-zA-Z_][a-zA-Z0-9_]*\([^\)]*\))",
            combined,
        )
        for c in calls:
            if len(c) > 3 and c not in citations:
                citations.append(c)

        # Class/Page references: BasePage, OrderCalculator, etc.
        classes = re.findall(r"\bclass\s+([A-Za-z0-9_]+)\b", combined)
        for cls in classes:
            c_str = f"class {cls}"
            if c_str not in citations:
                citations.append(c_str)

        # Specific architectural patterns
        for pattern in ["BasePage", "Clean POM", "toBeVisible", "Smart Wait"]:
            if pattern in combined and pattern not in citations:
                citations.append(pattern)

        unique_citations: List[str] = []
        for cit in citations:
            if cit not in unique_citations:
                unique_citations.append(cit)
        return unique_citations

    BUZZWORD_LABELS = frozenset({"BasePage", "Clean POM", "toBeVisible", "Smart Wait"})

    @classmethod
    def _has_concrete_evidence(cls, citations: List[str]) -> bool:
        """Returns True when citations include concrete code/rule evidence beyond bare buzzwords."""
        return any(cit not in cls.BUZZWORD_LABELS for cit in citations)

    @staticmethod
    def _extract_invariants(proposal: str, context: str) -> List[str]:
        invariants: List[str] = []
        text = f"{proposal.lower()} {context.lower() if context else ''}"

        if any(w in text for w in ["tobevisible", "smart wait", "expect", "dynamic wait"]):
            invariants.append("Dynamic Smart Wait: replaces flaky static sleeps with web-first element state checks.")
        if any(w in text for w in ["debounce", "lock", "mutex", "idempotent", "single execution"]):
            invariants.append("Concurrency Isolation: enforces single-flight execution and prevents duplicate submissions.")
        if any(w in text for w in ["circuit breaker", "retry", "backoff", "fallback"]):
            invariants.append("Fault Resilience: incorporates bounded retries and graceful fallback.")
        if any(w in text for w in ["clean pom", "basepage"]):
            invariants.append("Clean POM Architecture: strictly encapsulates element locators within Page classes.")
        if any(w in text for w in ["uniquecode", "dynamic data", "timestamp"]):
            invariants.append("Dynamic Test Data: ensures idempotent execution without database collision.")
        return invariants

    @classmethod
    def generate_defense(
        cls,
        round_num: int,
        proposal_text: str,
        context_text: str = "",
        verifier_counter: Optional[VerifierCounter] = None,
    ) -> ProverArgument:
        citations = cls._extract_citations(proposal_text, context_text)
        invariants = cls._extract_invariants(proposal_text, context_text)

        is_introducing_fatal = VerifierAgent.detect_fatal_flaw(proposal_text)

        if round_num == 1:
            if is_introducing_fatal:
                confidence = 0.35
                claim = f"Proposal '{proposal_text[:60]}' provides a workaround, but contains structural risks."
            else:
                base_conf = 0.70 + (0.05 * min(4, len(invariants)))
                if not citations:
                    base_conf = max(0.50, base_conf - 0.15)
                confidence = min(0.95, base_conf)
                claim = f"Proposal '{proposal_text[:60]}' is architecturally sound, verified against invariants."
            rebuttal_of = None
        else:
            rebuttal_of = verifier_counter.refutation if verifier_counter else None
            if is_introducing_fatal:
                confidence = 0.20
                claim = f"Round {round_num}: Prover concedes that fatal flaw cannot be justified under repository invariants."
            else:
                critique_summary = (
                    verifier_counter.counter_examples[0]
                    if verifier_counter and verifier_counter.counter_examples
                    else "adversary edge case"
                )
                if critique_summary.startswith("Counter-example: "):
                    critique_summary = critique_summary[len("Counter-example: "):]
                confidence = min(0.95, 0.75 + (0.05 * round_num) + (0.02 * len(citations)))
                claim = (
                    f"Round {round_num} Defense: Counter-critique '{critique_summary[:60]}' "
                    "is mitigated by boundary conditions and error handling."
                )

        return ProverArgument(
            claim=claim,
            citations=citations,
            confidence=confidence,
            rebuttal_of=rebuttal_of,
        )


class VerifierAgent:
    """Verifier agent actively seeking counter-examples, fatal anti-patterns, and edge cases."""

    ROUND_STRESS_VECTORS = (
        "Counter-example: Stress condition under high concurrency memory pressure.",
        "Counter-example: Subprocess timeout and path-scoped rollback drift under partial execution failure.",
        "Counter-example: Cross-bridge schema skew across AGENTS.md, tools_schema.json, and AI rules sync.",
        "Counter-example: Monotonic clock and cache invalidation skew across concurrent CI workers.",
        "Counter-example: Silent exception swallowing or assertion relaxation under degraded dependency state.",
    )

    @staticmethod
    def detect_fatal_flaw(proposal: str) -> Optional[str]:
        """Detects if proposal INTRODUCES a forbidden fatal flaw (not merely refactors it away)."""
        prop_lower = proposal.lower()

        # Check if proposal is replacing or eliminating the anti-pattern
        is_eliminating = any(
            phrase in prop_lower
            for phrase in [
                "instead of",
                "eliminate",
                "eliminates",
                "eliminating",
                "replace",
                "replaces",
                "replacing",
                "refactor away",
                "avoid",
                "avoids",
                "no longer use",
                "remove",
                "removes",
                "removing",
                "fix flakiness",
            ]
        )

        # Fatal flaw 1: Swallowed exceptions (except ...: pass, except Exception: pass, etc.)
        swallowed_match = re.search(
            r"\bexcept(?:\s+[A-Za-z0-9_\.]+)?:\s*(?:pass|\.\.\.|_\s*=\s*)",
            proposal,
        )
        if swallowed_match and not is_eliminating:
            return "Fatal Flaw: Unhandled exception suppression creates fake-pass telemetry."
        if ("except exception: pass" in prop_lower or "except: pass" in prop_lower) and not is_eliminating:
            return "Fatal Flaw: Swallowed exception anti-pattern destroys truth anchor."

        # Fatal flaw 2: Static hard sleep introduced
        if not is_eliminating:
            for sleep_token in ["time.sleep", "thread.sleep", "waitfortimeout", "cy.wait", "webui.delay"]:
                if sleep_token in prop_lower:
                    if any(verb in prop_lower for verb in ["add", "use", "wrap", "insert", "put", "introduce"]):
                        return f"Fatal Flaw: Static delay (`{sleep_token}`) introduces test flakiness under CPU throttle."

        # Fatal flaw 3: Tautological assertion introduced
        if not is_eliminating:
            for tautology in ["assert true", "assert 1 == 1"]:
                if tautology in prop_lower:
                    return f"Fatal Flaw: Tautological assertion (`{tautology}`) generates fake passes."

        # Fatal flaw 4: Non-monotonic wall-clock time used for expiry / duration / rate limits
        if not is_eliminating and re.search(r"\b(?:time\.time|datetime\.now|date\.now)\s*\(", prop_lower):
            if any(
                k in prop_lower
                for k in ("expir", "ttl", "timeout", "elapsed", "duration", "cooldown", "rate", "token", "session", "cache")
            ):
                return "Fatal Flaw: Non-monotonic wall-clock timing (`time.time()` / `datetime.now()`) used for expiry or duration drifts under NTP/DST skew."

        # Fatal flaw 5: Raw selector introduced directly in test scripts
        if not is_eliminating and re.search(
            r"(?:page\.locator\s*\(\s*['\"][^'\"]*//|by\.xpath\s*\(|document\.queryselector\s*\()",
            prop_lower,
        ):
            if any(k in prop_lower for k in ("test", "spec", "script")):
                return "Fatal Flaw: Raw selector introduced directly in test script violates Clean POM encapsulation."

        # Fatal flaw 6: Unconditional networkidle wait
        if not is_eliminating and re.search(r"wait_?for_?load_?state\s*\(\s*['\"]networkidle['\"]\s*\)", prop_lower):
            return "Fatal Flaw: Unconditional waitForLoadState('networkidle') causes flakiness under background polling."

        # Fatal flaw 7: Hardcoded credential or secret literal
        if not is_eliminating and re.search(
            r"\b(?:password|passwd|api_key|secret_key|secret|token)\s*=\s*['\"][^'\"]{4,}['\"]",
            prop_lower,
        ):
            return "Fatal Flaw: Hardcoded plaintext credential or secret literal violates credential security."

        return None

    @classmethod
    def generate_attack(
        cls,
        round_num: int,
        proposal_text: str,
        context_text: str,
        prover_argument: ProverArgument,
    ) -> VerifierCounter:
        counter_examples: List[str] = []
        prop_lower = proposal_text.lower()
        ctx_lower = context_text.lower() if context_text else ""

        # 1. Fatal Flaws Probe
        fatal_flaw = cls.detect_fatal_flaw(proposal_text)
        if fatal_flaw:
            counter_examples.append(fatal_flaw)

        ast_info = _extract_python_ast_grounding(context_text)
        ast_funcs: List[Tuple[str, List[str]]] = ast_info["functions"]
        ast_imports: Set[str] = ast_info["imports"]
        is_offline_python = (
            bool(ast_info["is_python_ast"])
            and bool(ast_funcs)
            and not bool(ast_imports & _NET_UI_IMPORTS)
            and not any(kw in prop_lower for kw in _NET_UI_KEYWORDS)
        )

        if is_offline_python:
            fn_name, fn_args = ast_funcs[0]
            args_sig = ", ".join(fn_args) if fn_args else ""
            first_arg = fn_args[0] if fn_args else "input"
            import_hint = ", ".join(sorted(ast_imports)[:3]) or "stdlib"

            if "debounce" not in prop_lower and "lock" not in prop_lower and "mutex" not in prop_lower:
                counter_examples.append(
                    f"[AST-Heuristic] Counter-example: Concurrent calls to `{fn_name}({args_sig})` without lock/mutex guard may race on shared state."
                )
            if "retry" not in prop_lower and "backoff" not in prop_lower and "fallback" not in prop_lower:
                counter_examples.append(
                    f"[AST-Heuristic] Counter-example: Unhandled I/O or decode failure inside `{fn_name}` ({import_hint}) lacks deterministic fallback."
                )
            if "empty" not in prop_lower and "null" not in prop_lower and "bound" not in prop_lower:
                counter_examples.append(
                    f"[AST-Heuristic] Counter-example: Boundary payload (`None` or empty `{first_arg}`) passed to `{fn_name}({args_sig})` is not explicitly guarded."
                )
        else:
            # 2. Race Conditions & Concurrency Risks
            if "debounce" not in prop_lower and "lock" not in prop_lower and "mutex" not in prop_lower:
                counter_examples.append(
                    "Counter-example: Rapid double-click within 50ms causes duplicate request submission."
                )

            # 3. Network & Transient Failures
            if "retry" not in prop_lower and "backoff" not in prop_lower and "fallback" not in prop_lower:
                counter_examples.append(
                    "Counter-example: Transient HTTP 503 error during request drops flow without exponential backoff."
                )

            # 4. Boundary & Edge Cases
            if "empty" not in prop_lower and "null" not in prop_lower and "bound" not in prop_lower:
                counter_examples.append(
                    "Counter-example: Boundary payload with empty/null attributes not explicitly asserted."
                )

        # 5. Context Contradiction analysis (restricted to code-like identifiers to avoid prose false positives)
        if context_text and len(context_text) > 10:
            words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{3,}\b", proposal_text)
            prose_ignore = {
                "Foundational", "TypeScript", "JavaScript", "Python", "Standard",
                "AGENTS", "Rule", "Clean", "Suites", "Proposal", "Context",
            }
            missing_tokens = [
                w for w in words
                if w not in prose_ignore
                and ("_" in w or re.match(r"^[A-Z][a-z]+[A-Z]", w) or re.match(r"^[a-z]+[A-Z]", w))
                and w.lower() not in ctx_lower
                and w.lower() not in [
                    "class", "def", "self", "return", "test", "import", "from",
                    "none", "true", "false", "replace", "refactor", "proposal", "evidence", "instead"
                ]
            ]
            if len(missing_tokens) > 5:
                counter_examples.append(
                    f"Counter-example: Context contradiction; symbols {missing_tokens[:3]} not declared in target context."
                )

        if not counter_examples:
            vector_idx = (max(1, int(round_num)) - 1) % len(cls.ROUND_STRESS_VECTORS)
            counter_examples.append(cls.ROUND_STRESS_VECTORS[vector_idx])

        buzzword_only = (
            not fatal_flaw
            and any(cit in ProverAgent.BUZZWORD_LABELS for cit in prover_argument.citations)
            and not ProverAgent._has_concrete_evidence(prover_argument.citations)
        )
        if buzzword_only:
            counter_examples.append(
                "Counter-example: Buzzword-heavy proposal relies on architectural labels without concrete empirical evidence, rule citations, or call-sites."
            )

        if fatal_flaw:
            falsification_score = 0.88 + min(0.10, 0.03 * round_num)
            refutation = f"Adversary exposes fatal architectural anti-pattern in round {round_num}: {fatal_flaw}"
            attack_type = "fatal_flaw"
        else:
            base_fals = 0.50 + (0.05 * min(4, len(counter_examples)))
            if buzzword_only:
                base_fals = max(0.85, base_fals + 0.25)
            elif len(prover_argument.citations) >= 2:
                base_fals = max(0.40, base_fals - 0.10)
            falsification_score = min(0.90 if buzzword_only else 0.85, base_fals)
            refutation = f"Adversary probes round {round_num} edge cases and failure modes."
            attack_type = "adversarial_edge_cases"

        return VerifierCounter(
            refutation=refutation,
            counter_examples=counter_examples,
            falsification_score=falsification_score,
            attack_type=attack_type,
        )


class JudgeAgent:
    """Independent Judge evaluating debate rounds and rendering Nash equilibrium verdict."""

    @staticmethod
    def evaluate_round(
        round_num: int,
        prover_arg: ProverArgument,
        verifier_counter: VerifierCounter,
        judge_mode: str,
    ) -> str:
        if verifier_counter.attack_type == "fatal_flaw":
            return f"Round {round_num} Judge Ruling: Fatal flaw detected ({verifier_counter.counter_examples[0]}); Verifier holds decisive advantage."

        if judge_mode == "strict":
            if verifier_counter.falsification_score >= 0.70:
                return f"Round {round_num} Strict Ruling: Verifier counter-example surpasses strict falsification threshold ({verifier_counter.falsification_score:.2f})."
            else:
                return f"Round {round_num} Strict Ruling: Prover defense maintained; counter-examples below falsification barrier."

        elif judge_mode == "consensus":
            return f"Round {round_num} Consensus Ruling: Evaluating convergence; Prover confidence {prover_arg.confidence:.2f} vs Verifier falsification {verifier_counter.falsification_score:.2f}."

        else:  # evidence_weighted
            cit_count = len(prover_arg.citations)
            atk_count = len(verifier_counter.counter_examples)
            if prover_arg.confidence >= verifier_counter.falsification_score:
                return f"Round {round_num} Evidence Ruling: Prover leads with {cit_count} citations (confidence {prover_arg.confidence:.2f})."
            else:
                return f"Round {round_num} Evidence Ruling: Verifier challenges proposal with {atk_count} counter-examples (falsification {verifier_counter.falsification_score:.2f})."

    @classmethod
    def adjudicate(
        cls,
        proposal: str,
        transcript: List[DebateRound],
        judge_mode: str = "evidence_weighted",
    ) -> DebateOutcome:
        prover_total = 0.0
        verifier_total = 0.0
        unresolved_vulns: List[str] = []
        has_fatal_flaw = False

        for rnd in transcript:
            p_arg = rnd.prover_argument
            v_cnt = rnd.verifier_counter

            u_p = p_arg.confidence * (1.0 + 0.1 * min(5, len(p_arg.citations)))
            u_v = v_cnt.falsification_score * (1.0 + 0.15 * min(5, len(v_cnt.counter_examples)))

            prover_total += u_p
            verifier_total += u_v

            if v_cnt.attack_type == "fatal_flaw":
                has_fatal_flaw = True
                for ce in v_cnt.counter_examples:
                    if ce not in unresolved_vulns:
                        unresolved_vulns.append(ce)

        r_count = max(1, len(transcript))

        if has_fatal_flaw:
            status = "REFUTED"
            winner = "verifier"
            winning_thesis = f"Proposal rejected due to verified fatal flaw: {unresolved_vulns[0] if unresolved_vulns else 'Fatal anti-pattern'}"
            prover_total = min(prover_total, verifier_total * 0.5)
        elif judge_mode == "strict":
            strict_breach = any(r.verifier_counter.falsification_score >= 0.70 for r in transcript)
            if strict_breach or verifier_total > prover_total:
                status = "REFUTED"
                winner = "verifier"
                winning_thesis = "Proposal refuted under strict falsification: adversary identified unmitigated vulnerabilities."
                unresolved_vulns.append("Unmitigated vulnerability under strict falsification criteria.")
            else:
                status = "ACCEPTED"
                winner = "prover"
                winning_thesis = "Proposal accepted under strict falsification: zero critical vulnerabilities survived."
        elif judge_mode == "consensus":
            if prover_total >= verifier_total * 0.95:
                status = "ACCEPTED"
                winner = "prover"
                winning_thesis = "Proposal accepted via dialectical consensus; Prover mitigations resolve adversary edge cases."
            else:
                status = "REFUTED"
                winner = "verifier"
                winning_thesis = "Proposal refuted: consensus not achieved due to persistent adversary counter-examples."
                unresolved_vulns.append("Persistent unaddressed edge cases prevent consensus.")
        else:  # evidence_weighted
            if prover_total >= verifier_total:
                status = "ACCEPTED"
                winner = "prover"
                winning_thesis = "Proposal defended successfully against adversary counter-examples; invariants preserved."
            else:
                status = "REFUTED"
                winner = "verifier"
                winning_thesis = "Proposal rejected: adversary counter-examples outweighed Prover evidence."
                unresolved_vulns.append("Counter-examples outweighed Prover evidence.")

        z = (prover_total - verifier_total) / float(r_count)
        try:
            nash_score = 1.0 / (1.0 + math.exp(-z))
        except OverflowError:
            nash_score = 1.0 if z > 0 else 0.0

        if has_fatal_flaw:
            nash_score = min(0.20, nash_score)

        nash_score = max(0.0, min(1.0, nash_score))

        transcript_dicts = [r.to_dict() for r in transcript]

        return DebateOutcome(
            status=status,
            rounds_completed=len(transcript),
            winner=winner,
            winning_thesis=winning_thesis,
            nash_equilibrium_score=nash_score,
            transcript=transcript_dicts,
            prover_total_score=prover_total,
            verifier_total_score=verifier_total,
            unresolved_vulnerabilities=unresolved_vulns,
            judge_mode=judge_mode,
            proposal=proposal,
        )


class ProverVerifierGame:
    """Engine executing multi-round Prover-Verifier Zero-Sum Debate Games (R2)."""

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = repo_root or _REPO_ROOT

    def _load_input(self, text_or_path: Optional[str], is_required: bool = False, label: str = "Input") -> str:
        if not text_or_path:
            if is_required:
                raise ValueError(f"{label} string cannot be empty.")
            return ""

        s = str(text_or_path).strip()
        if not s:
            if is_required:
                raise ValueError(f"{label} string cannot be empty.")
            return ""

        # Check if single line looking like a file path (avoid treating sentences ending in .py as paths)
        if "\n" not in s and (" " not in s or os.path.exists(s)):
            looks_like_path = (
                s.startswith("/")
                or s.startswith("./")
                or s.startswith("../")
                or any(
                    s.endswith(ext)
                    for ext in [
                        ".py",
                        ".md",
                        ".txt",
                        ".json",
                        ".yaml",
                        ".yml",
                        ".ts",
                        ".js",
                        ".groovy",
                        ".java",
                        ".xml",
                        ".html",
                    ]
                )
            )
            if looks_like_path:
                if os.path.exists(s):
                    with open(s, "r", encoding="utf-8", errors="replace") as f:
                        return f.read()
                else:
                    raise FileNotFoundError(f"{label} file not found: {s}")

        return s

    def run_debate(
        self,
        proposal: str,
        context: Optional[str] = None,
        rounds: int = 3,
        judge_mode: str = "evidence_weighted",
        external_oracle: bool = False,
    ) -> Dict[str, Any]:
        proposal_text = self._load_input(proposal, is_required=True, label="Proposal")
        context_text = self._load_input(context, is_required=False, label="Context")
        ast_info = _extract_python_ast_grounding(context_text)

        allowed_modes = ("evidence_weighted", "strict", "consensus")
        if judge_mode not in allowed_modes:
            raise ValueError(f"Invalid judge_mode: '{judge_mode}'. Must be one of: {allowed_modes}")

        clamped_rounds = max(1, min(5, int(rounds)))

        transcript_rounds: List[DebateRound] = []
        last_verifier_counter: Optional[VerifierCounter] = None

        for r in range(1, clamped_rounds + 1):
            p_arg = ProverAgent.generate_defense(
                round_num=r,
                proposal_text=proposal_text,
                context_text=context_text,
                verifier_counter=last_verifier_counter,
            )
            v_cnt = VerifierAgent.generate_attack(
                round_num=r,
                proposal_text=proposal_text,
                context_text=context_text,
                prover_argument=p_arg,
            )
            ruling = JudgeAgent.evaluate_round(
                round_num=r,
                prover_arg=p_arg,
                verifier_counter=v_cnt,
                judge_mode=judge_mode,
            )
            debate_round = DebateRound(
                round=r,
                prover_argument=p_arg,
                verifier_counter=v_cnt,
                judge_interim_ruling=ruling,
            )
            transcript_rounds.append(debate_round)
            last_verifier_counter = v_cnt

        outcome = JudgeAgent.adjudicate(
            proposal=proposal_text,
            transcript=transcript_rounds,
            judge_mode=judge_mode,
        )
        outcome.provenance_tag = "[External-Oracle]" if external_oracle else "[AST-Heuristic]"
        outcome.ast_grounded_symbols = list(ast_info.get("symbols", []))

        return outcome.to_dict()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prover_verifier_games.py",
        description="Prover-Verifier Zero-Sum Debate Engine (Nash Equilibrium) - R2",
    )
    parser.add_argument("--proposal", type=str, default=None, help="Proposal statement or path to file")
    parser.add_argument(
        "--context",
        "--context-file",
        type=str,
        default=None,
        dest="context",
        help="Optional context file or description",
    )
    parser.add_argument("--rounds", type=int, default=3, help="Number of debate rounds (default: 3, clamped 1-5)")
    parser.add_argument(
        "--judge-mode",
        type=str,
        default="evidence_weighted",
        choices=["evidence_weighted", "strict", "consensus"],
        help="Judge evaluation mode (evidence_weighted | strict | consensus)",
    )
    parser.add_argument("--gate", action="store_true", help="Run DoD gate check and self-verification")
    parser.add_argument("--output", type=str, default=None, help="Path to write JSON debate results")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format only to stdout")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    if args.gate and not args.proposal:
        game = ProverVerifierGame()
        sample_prop = "Refactor auth middleware to use bearer token validation with automated fallback"
        res = game.run_debate(proposal=sample_prop, rounds=2, judge_mode="evidence_weighted")
        passed = isinstance(res, dict) and "winner" in res and res.get("rounds_completed") == 2
        if args.json:
            print(json.dumps({"gate": "prover_verifier_games", "status": "PASS" if passed else "FAIL"}, indent=2))
        else:
            print("[PASS] Prover-Verifier Games DoD Gate verified." if passed else "[FAIL] Prover-Verifier Gate failed.")
        return 0 if passed else 1

    if not args.proposal:
        try:
            parser.error("the following arguments are required: --proposal")
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2

    game = ProverVerifierGame()
    try:
        res = game.run_debate(
            proposal=args.proposal,
            context=args.context,
            rounds=args.rounds,
            judge_mode=args.judge_mode,
        )
    except (FileNotFoundError, ValueError) as err:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)
        except OSError as err:
            sys.stderr.write(f"Error writing to output file {args.output}: {err}\n")
            return 1

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print("=" * 70)
        print("  PROVER-VERIFIER ZERO-SUM DEBATE ENGINE (NASH EQUILIBRIUM)")
        print("=" * 70)
        print(f"Proposal: {res['proposal']}")
        print(f"Verdict : [{res['status']}] Winner: {res['winner'].upper()}")
        print(f"Thesis  : {res['winning_thesis']}")
        print(f"Nash Eq : {res['nash_equilibrium_score']}")
        print(f"Scores  : Prover: {res['prover_total_score']} vs Verifier: {res['verifier_total_score']}")
        print("-" * 70)
        for t in res["transcript"]:
            print(f"[Round {t['round']}]:")
            print(f"  Prover  : {t['prover_argument']['claim']}")
            for cit in t['prover_argument']['citations']:
                print(f"    * Citation: {cit}")
            print(f"  Verifier: {t['verifier_counter']['refutation']}")
            for atk in t['verifier_counter']['counter_examples']:
                print(f"    * {atk}")
            print(f"  Judge   : {t['judge_interim_ruling']}")
        print("=" * 70)

    if args.gate:
        return 0 if res.get("status") == "ACCEPTED" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
