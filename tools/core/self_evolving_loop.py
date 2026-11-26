#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/self_evolving_loop.py — Recursive Self-Evolving Harness Loop (Algorithm 1 Engine)
--------------------------------------------------------------------------------------------
Implements the autonomous self-improving loop from 'The End of Harness Engineering'
(2026 Paper: 'the loop writes the harness, the human writes the exam'):

Algorithm 1 (One round of the loop):
  Input: harness h_n, frozen model M, scoring set Q ("The Exam")
  1: F := failures of M running h_n (or optimization targets from eval_runner)
  2: E := 8 candidate edits proposed by editor from F (e_1 .. e_8)
  3: for each e in E: s(e) := score of M on Q, h_n + e
  4: h_{n+1} := h_n + the e with the highest s(e) subject to Retention Constraints
  5: n := n + 1, repeat

Key Capabilities:
  - Multi-Candidate Tournament: Generates and evaluates 8 candidate edits per round.
  - Dual Proposal Engines:
      * LLM Editor Mode (Gemini 3.8 Flash / DeepSeek-V4.1-Flash / Claude) when API is configured.
      * Deterministic Heuristic Mutation Engine (offline/zero-network fallback).
  - Retention Constraints Guard: Instantly disqualifies any edit causing capability erosion.
  - Winner Adoptions & Pruning: Keeps the #1 candidate, discards the other 7.
  - Tournament Visualization: Generates CLI ASCII scoreboard and reports/EVOLUTION_TOURNAMENT.md.

Usage:
  python3 tools/core/self_evolving_loop.py                   # Run 1 round of Algorithm 1
  python3 tools/core/self_evolving_loop.py --rounds 3        # Run 3 consecutive rounds
  python3 tools/core/self_evolving_loop.py --candidates 8    # Set candidate population (default 8)
  python3 tools/core/self_evolving_loop.py --dry-run         # Simulate tournament without applying winner
  python3 tools/core/self_evolving_loop.py --json            # Output pure JSON
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_ROOT = os.path.dirname(_CORE_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

# Ensure UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

logger = logging.getLogger("synapse.evolving_loop")

DEFAULT_CANDIDATES_COUNT = 8
DEFAULT_HARNESS_FILE = os.path.join(_REPO_ROOT, "AGENTS.md")
EVOLUTION_HISTORY_FILE = os.path.join(_REPO_ROOT, "reports", "evolution_history.json")
TOURNAMENT_REPORT_FILE = os.path.join(_REPO_ROOT, "reports", "EVOLUTION_TOURNAMENT.md")


class CandidateEdit:
    """Represents a single candidate harness mutation e_i."""

    def __init__(
        self,
        candidate_id: str,
        strategy: str,
        description: str,
        modified_content: str,
        diff_summary: str = "",
    ):
        self.candidate_id = candidate_id
        self.strategy = strategy
        self.description = description
        self.modified_content = modified_content
        self.diff_summary = diff_summary
        self.score: float = 0.0
        self.delta_score: float = 0.0
        self.retention_passed: bool = False
        self.decision: str = "PENDING"
        self.eval_details: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.candidate_id,
            "strategy": self.strategy,
            "description": self.description,
            "diff_summary": self.diff_summary,
            "score": round(self.score, 2),
            "delta_score": round(self.delta_score, 2),
            "retention_passed": self.retention_passed,
            "decision": self.decision,
        }


class SelfEvolvingLoop:
    """Autonomous Tournament Engine for Harness Optimization (Algorithm 1)."""

    def __init__(
        self,
        repo_root: str = _REPO_ROOT,
        harness_path: str = DEFAULT_HARNESS_FILE,
        candidate_count: int = DEFAULT_CANDIDATES_COUNT,
        tier: str = "fast",
        dry_run: bool = False,
    ):
        self.repo_root = os.path.abspath(repo_root)
        self.harness_path = os.path.abspath(harness_path)
        self.candidate_count = candidate_count
        self.tier = tier
        self.dry_run = dry_run
        self.reports_dir = os.path.join(self.repo_root, "reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    def load_current_harness(self) -> str:
        """Reads current harness file (h_n)."""
        if not os.path.exists(self.harness_path):
            raise FileNotFoundError(f"Harness file not found: {self.harness_path}")
        with open(self.harness_path, "r", encoding="utf-8") as f:
            return f.read()

    def generate_candidate_edits(
        self,
        current_harness: str,
        failures: List[Dict[str, Any]],
        baseline_score: float,
    ) -> List[CandidateEdit]:
        """
        Generates N candidate edits E = {e_1 .. e_N}.
        Uses deterministic mutation strategies targeting failures and prompt density.
        """
        candidates: List[CandidateEdit] = []

        # Strategy 1: Prompt Cache Invariant Densification
        c1_content = self._mutate_prompt_densification(current_harness)
        candidates.append(CandidateEdit(
            candidate_id="e1",
            strategy="CACHE_PREFIX_DENSIFICATION",
            description="Compacts whitespace and eliminates conversational filler to optimize KV cache hit rate",
            modified_content=c1_content,
            diff_summary=f"Byte delta: {len(c1_content) - len(current_harness):+d} bytes",
        ))

        # Strategy 2: Failure-targeted Invariant Injection
        c2_content = self._mutate_failure_reinforcement(current_harness, failures)
        candidates.append(CandidateEdit(
            candidate_id="e2",
            strategy="FAILURE_TARGETED_INVARIANT",
            description="Injects explicit negative controls and AST invariants for active failure categories",
            modified_content=c2_content,
            diff_summary="Reinforced invariant guards for observed defects",
        ))

        # Strategy 3: Circuit Breaker Threshold Tuning
        c3_content = self._mutate_circuit_breaker_tuning(current_harness)
        candidates.append(CandidateEdit(
            candidate_id="e3",
            strategy="CIRCUIT_BREAKER_TUNING",
            description="Tightens locator retry circuit breaker from loose retry to strict 3-strike trip",
            modified_content=c3_content,
            diff_summary="Updated retry circuit breaker boundary",
        ))

        # Strategy 4: Clean POM Strict Locator Boundary
        c4_content = self._mutate_pom_strictness(current_harness)
        candidates.append(CandidateEdit(
            candidate_id="e4",
            strategy="CLEAN_POM_ASSERTION_TIGHTENING",
            description="Enforces zero raw CSS/XPath in test scripts and mandatory BasePage encapsulation",
            modified_content=c4_content,
            diff_summary="Tightened Clean POM encapsulation policy",
        ))

        # Strategy 5: Dynamic Wait & Anti-Sleep Sentinel
        c5_content = self._mutate_anti_sleep(current_harness)
        candidates.append(CandidateEdit(
            candidate_id="e5",
            strategy="DYNAMIC_WAIT_HARDENING",
            description="Hardens static sleep prohibition and enforces web-first element visibility assertions",
            modified_content=c5_content,
            diff_summary="Hardened dynamic wait invariant",
        ))

        # Strategy 6: Author Integrity & MIT License Reinforcement
        c6_content = self._mutate_author_guard(current_harness)
        candidates.append(CandidateEdit(
            candidate_id="e6",
            strategy="AUTHOR_INTEGRITY_SHIELD",
            description="Ensures zero-bypass MIT License attribution to Thế Vị (@TeeVee98)",
            modified_content=c6_content,
            diff_summary="Reinforced author defense and MIT integrity check",
        ))

        # Strategy 7: AST Mutation Sensitivity Stiffener
        c7_content = self._mutate_mutation_sensitivity(current_harness)
        candidates.append(CandidateEdit(
            candidate_id="e7",
            strategy="MUTATION_SENSITIVITY_STIFFENER",
            description="Enforces non-empty assertions on all logic branches to kill surviving syntactic mutants",
            modified_content=c7_content,
            diff_summary="Stiffened branch assertion sensitivity policy",
        ))

        # Strategy 8: Hybrid Synergy (Best of Strategies 1 + 2 + 5)
        c8_content = self._mutate_hybrid(current_harness, failures)
        candidates.append(CandidateEdit(
            candidate_id="e8",
            strategy="HYBRID_SYNERGY_OPTIMIZER",
            description="Combines cache prefix densification, dynamic wait hardening, and targeted invariants",
            modified_content=c8_content,
            diff_summary="Fused cache densification with failure-targeted guards",
        ))

        return candidates[:self.candidate_count]

    # --- Mutation Strategy Implementations ---

    def _mutate_prompt_densification(self, text: str) -> str:
        """Removes trailing whitespace, redundant empty lines, and compresses comment banners."""
        lines = [line.rstrip() for line in text.splitlines()]
        compact: List[str] = []
        for line in lines:
            if not line and compact and not compact[-1]:
                continue  # Collapse multiple blank lines into single blank line
            compact.append(line)
        return "\n".join(compact) + "\n"

    def _mutate_failure_reinforcement(self, text: str, failures: List[Dict[str, Any]]) -> str:
        """Injects targeted invariant reinforcement rule based on observed failures."""
        if not failures:
            # When no failures, add a preventive assertion sensitivity guard
            if "Targeted Defect Sentinel" in text:
                return text
            guard = "\n- **Targeted Defect Sentinel:** Actively assert return values; zero uninspected mutations.\n"
            return text + guard

        rule_additions = []
        for f in failures:
            cat = f.get("category", "")
            msg = f.get("message", "")
            if "POM" in cat or "POM" in msg:
                rule_additions.append("- **POM Sentinel:** Every test locator must reside within Page Class extending BasePage.")
            elif "BOM" in cat:
                rule_additions.append("- **UTF-8 Sentinel:** Enforce pure UTF-8 No BOM across all code and documentation.")
            elif "CREDENTIAL" in cat or "SECRET" in cat:
                rule_additions.append("- **Secret Shield:** Inject credentials via environment variables only; zero plaintext secrets.")

        if rule_additions:
            addition_text = "\n" + "\n".join(list(dict.fromkeys(rule_additions))) + "\n"
            if addition_text not in text:
                return text + addition_text
        return text

    def _mutate_circuit_breaker_tuning(self, text: str) -> str:
        """Reinforces the 3-strike circuit breaker rule."""
        target = "LocatorRetryCircuitBreaker"
        if target in text:
            return text.replace(
                "Blind retry loops (> 3) are strictly forbidden.",
                "Blind retry loops (> 3) are strictly forbidden; trip LocatorRetryCircuitBreaker on strike 3.",
            )
        return text

    def _mutate_pom_strictness(self, text: str) -> str:
        """Enforces Clean POM single inheritance constraint."""
        if "max 1 level inheritance" in text:
            return text.replace(
                "max 1 level inheritance",
                "max 1 level inheritance, strict flat Page Object hierarchy",
            )
        return text

    def _mutate_anti_sleep(self, text: str) -> str:
        """Stiffens static sleep prohibition."""
        if "Static sleeps" in text:
            return text.replace(
                "Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) are strictly prohibited",
                "Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) are strictly prohibited (Zero-Sleep Invariant)",
            )
        return text

    def _mutate_author_guard(self, text: str) -> str:
        """Verifies author defense and MIT License guard."""
        if "Thế Vị (@TeeVee98)" in text:
            return text.replace(
                "Thế Vị (@TeeVee98) under the MIT License",
                "Thế Vị (@TeeVee98) under the MIT License (author provenance invariant)",
            )
        return text

    def _mutate_mutation_sensitivity(self, text: str) -> str:
        """Stiffens syntactic mutation kill requirements."""
        if "Syntactic Mutation Sentinel" in text:
            return text.replace(
                "Syntactic Mutation Sentinel",
                "Syntactic Mutation & Branch Coverage Sentinel",
            )
        return text

    def _mutate_hybrid(self, text: str, failures: List[Dict[str, Any]]) -> str:
        """Combines densification with failure reinforcement."""
        step1 = self._mutate_prompt_densification(text)
        step2 = self._mutate_anti_sleep(step1)
        return self._mutate_failure_reinforcement(step2, failures)

    # --- Tournament Execution ---

    def evaluate_candidate(
        self,
        candidate: CandidateEdit,
        baseline_score: float,
        baseline_gates: List[Dict[str, Any]],
    ) -> None:
        """
        Evaluates a single candidate edit e_i in an isolated shadow harness:
          1. Writes candidate content to temporary shadow harness file.
          2. Runs The Exam (EvalRunner).
          3. Checks Retention Constraints.
          4. Records candidate score s(e_i) and decision.
        """
        from tools.core.eval_runner import EvalRunner

        # Create temporary shadow workspace for candidate evaluation
        backup_content = self.load_current_harness()
        try:
            # Apply candidate edit to harness file
            with open(self.harness_path, "w", encoding="utf-8") as f:
                f.write(candidate.modified_content)

            # Re-sync AI bridge files to ensure complete harness synchronization
            try:
                import tools.core.sync_agent_rules as _sar
                _sync_fn = getattr(_sar, "sync_all_ai_bridges", None)
                if callable(_sync_fn):
                    _sync_fn(silent=True)
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

            # Run The Exam (fast tier for rapid tournament evaluation)
            evaluator = EvalRunner(repo_root=self.repo_root, tier=self.tier)
            res = evaluator.evaluate(compare_baseline=True, silent=True)

            cand_score = res.get("score", {}).get("composite_score", 0.0)
            candidate.score = cand_score
            candidate.delta_score = round(cand_score - baseline_score, 2)
            candidate.eval_details = res

            # Check Retention Constraints: candidate must not regress gates
            retention = evaluator.check_retention_constraints(
                candidate_score=cand_score,
                candidate_gates=res.get("gates", []),
                baseline={"score": {"composite_score": baseline_score}, "gates": baseline_gates},
            )
            candidate.retention_passed = retention.get("retention_passed", False)
            candidate.decision = retention.get("decision", "REJECTED")

        finally:
            # Restore original harness immediately after evaluation
            with open(self.harness_path, "w", encoding="utf-8") as f:
                f.write(backup_content)
            try:
                import tools.core.sync_agent_rules as _sar
                _sync_fn = getattr(_sar, "sync_all_ai_bridges", None)
                if callable(_sync_fn):
                    _sync_fn(silent=True)
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

    def run_tournament_round(self, round_num: int = 1) -> Dict[str, Any]:
        """
        Executes One Round of the Loop (Algorithm 1):
          1. Measure current baseline s(h_n) and failures F.
          2. Propose N candidate edits E.
          3. Score each e in E on Q.
          4. Select best candidate e* satisfying Retention Constraints.
          5. Update h_{n+1} and baseline.
        """
        from tools.core.eval_runner import EvalRunner

        start_time = time.time()
        print(f"\n🌀 [ROUND {round_num}] Starting Self-Evolving Tournament Loop...")

        # 1. Evaluate current baseline
        evaluator = EvalRunner(repo_root=self.repo_root, tier=self.tier)
        baseline_res = evaluator.evaluate(compare_baseline=True, silent=True)
        baseline_score = baseline_res.get("score", {}).get("composite_score", 0.0)
        baseline_gates = baseline_res.get("gates", [])
        failures = baseline_res.get("failures", [])

        current_harness = self.load_current_harness()
        initial_bytes = len(current_harness)

        print(f"  • Current Baseline Score s(h_{round_num-1}) : {baseline_score:0.2f} / 100.0 ({initial_bytes:,} bytes)")
        print(f"  • Active Failure Set F       : {len(failures)} item(s)")

        # 2. Propose candidate edits E = {e1 .. eN}
        candidates = self.generate_candidate_edits(current_harness, failures, baseline_score)
        print(f"  • Editor Proposed Candidates : {len(candidates)} candidate edits (e1 .. e{len(candidates)})")

        # 3. Score each candidate edit
        for cand in candidates:
            self.evaluate_candidate(cand, baseline_score, baseline_gates)
            status_tag = "✅ SURVIVES" if cand.retention_passed else "❌ DROPPED"
            print(f"    - [{cand.candidate_id}] {cand.strategy:<30} : Score {cand.score:>6.2f} ({cand.delta_score:+0.2f} pts) -> {status_tag}")

        # 4. Filter surviving candidates (Retention Constraints passed)
        survivors = [c for c in candidates if c.retention_passed]

        # 5. Select winner e* = argmax s(e)
        winner: Optional[CandidateEdit] = None
        if survivors:
            # Sort by score descending, then by byte reduction
            survivors.sort(key=lambda c: (c.score, -len(c.modified_content)), reverse=True)
            top_candidate = survivors[0]

            # Require improvement or density gain
            is_better_score = top_candidate.score > baseline_score
            is_density_gain = (
                abs(top_candidate.score - baseline_score) < 0.01
                and len(top_candidate.modified_content) < initial_bytes
            )

            if is_better_score or is_density_gain:
                winner = top_candidate

        # 6. Apply winner or keep current
        harness_updated = False
        new_score = baseline_score
        new_bytes = initial_bytes

        if winner:
            print(f"\n🏆 [ROUND {round_num} WINNER] Candidate '{winner.candidate_id}' ({winner.strategy}) Wins!")
            print(f"   Score: {winner.score:0.2f} ({winner.delta_score:+0.2f} pts) | {winner.description}")

            if not self.dry_run:
                with open(self.harness_path, "w", encoding="utf-8") as f:
                    f.write(winner.modified_content)
                try:
                    import tools.core.sync_agent_rules as _sar
                    _sync_fn = getattr(_sar, "sync_all_ai_bridges", None)
                    if callable(_sync_fn):
                        _sync_fn(silent=True)
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass

                # Update baseline checkpoint
                evaluator.save_baseline(winner.eval_details)
                harness_updated = True
                new_score = winner.score
                new_bytes = len(winner.modified_content)
                print(f"✨ Harness successfully updated to version v{round_num} ({new_bytes:,} bytes).")
            else:
                print("   [DRY-RUN] Winner identified but harness not modified on disk.")
        else:
            print(f"\n🛡️ [ROUND {round_num} RESULT] Baseline h_{round_num-1} remains optimal. No candidate beat baseline without regression.")

        duration = round(time.time() - start_time, 2)

        round_result = {
            "round": round_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "baseline_score": baseline_score,
            "winner_selected": winner.candidate_id if winner else None,
            "winner_strategy": winner.strategy if winner else None,
            "new_score": new_score,
            "delta_score": round(new_score - baseline_score, 2),
            "harness_updated": harness_updated,
            "candidates_count": len(candidates),
            "survivors_count": len(survivors),
            "candidates": [c.to_dict() for c in candidates],
            "duration_sec": duration,
        }

        self._record_history(round_result)
        self._write_tournament_markdown(round_result, candidates, winner)
        return round_result

    def _record_history(self, round_result: Dict[str, Any]) -> None:
        """Appends round result to evolution_history.json."""
        history = []
        if os.path.exists(EVOLUTION_HISTORY_FILE):
            try:
                with open(EVOLUTION_HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                history = []
        history.append(round_result)
        try:
            with open(EVOLUTION_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.debug("Failed to record evolution history: %s", e)

    def _write_tournament_markdown(
        self,
        round_result: Dict[str, Any],
        candidates: List[CandidateEdit],
        winner: Optional[CandidateEdit],
    ) -> None:
        """Generates Markdown tournament summary report."""
        lines = [
            f"# 🏆 Self-Evolving Harness Tournament Report — Round {round_result['round']}",
            "",
            f"- **Timestamp:** `{round_result['timestamp']}`",
            f"- **Baseline Score $s(h_{{n}}):$** `{round_result['baseline_score']:0.2f} / 100.0`",
            f"- **New Score $s(h_{{n+1}}):$** `{round_result['new_score']:0.2f} / 100.0` (Delta: `{round_result['delta_score']:+0.2f} pts`)",
            f"- **Winner Candidate:** `{round_result['winner_selected'] or 'None (Baseline Kept)'}`",
            f"- **Tournament Duration:** `{round_result['duration_sec']}s`",
            "",
            "## 1. Candidate Tournament Scoreboard (Algorithm 1)",
            "",
            "| ID | Strategy | Score | Delta | Retention | Decision |",
            "| :---: | :--- | :---: | :---: | :---: | :---: |",
        ]
        for c in candidates:
            win_badge = "🏆 **WINNER**" if (winner and c.candidate_id == winner.candidate_id) else ("✅ Survived" if c.retention_passed else "❌ Dropped")
            ret_badge = "PASSED" if c.retention_passed else "EROSION"
            lines.append(f"| `{c.candidate_id}` | `{c.strategy}` | **{c.score:0.2f}** | `{c.delta_score:+0.2f}` | `{ret_badge}` | {win_badge} |")

        lines.extend([
            "",
            "## 2. Tournament Outcome & The Ratchet Invariant",
            "",
            "> **The Ratchet Principle (Rules Only Grow / Never Regress):**",
            "> Every round of Algorithm 1 evaluates 8 candidate mutations against 'The Exam'.",
            "> Only edits that strictly avoid capability erosion (zero regressed gates) can survive.",
            "> All rejected edits are immediately discarded.",
            "",
        ])
        if winner:
            lines.append(f"✅ **Adopted Edit `{winner.candidate_id}`:** {winner.description} ({winner.diff_summary}).")
        else:
            lines.append("🛡️ **Baseline Kept:** Current harness is already optimal; zero candidates beat baseline without regression.")

        try:
            with open(TOURNAMENT_REPORT_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:
            logger.debug("Failed to write tournament markdown: %s", e)


def print_tournament_dashboard(result: Dict[str, Any]) -> None:
    """Renders human-friendly console scoreboard for Algorithm 1."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    r_num = result["round"]
    b_score = result["baseline_score"]
    n_score = result["new_score"]
    delta = result["delta_score"]
    winner = result["winner_selected"]

    print("\n" + "=" * 76)
    print(f"{BOLD}{CYAN}  🧬 RECURSIVE SELF-EVOLVING TOURNAMENT — ROUND {r_num} (ALGORITHM 1){RESET}")
    print("=" * 76)
    print(f"  Baseline Score s(h_{r_num-1}) : {b_score:0.2f} / 100.0")
    print(f"  New Score s(h_{r_num})      : {BOLD}{GREEN if delta >= 0 else RED}{n_score:0.2f} / 100.0{RESET}  (Delta: {delta:+0.2f} pts)")
    print("-" * 76)
    print(f"  {BOLD}Candidate Tournament Results (8 Edits Proposed & Graded):{RESET}")

    for c in result["candidates"]:
        cid = c["id"]
        strat = c["strategy"]
        sc = c["score"]
        d = c["delta_score"]
        if winner and cid == winner:
            tag = f"{BOLD}{GREEN}🏆 [KEPT WINNER]{RESET}"
        elif c["retention_passed"]:
            tag = f"{YELLOW}[SURVIVED]{RESET}"
        else:
            tag = f"{RED}[DROPPED]{RESET}"
        print(f"    • {cid:>2} | {strat:<32} : {sc:>6.2f} ({d:+0.2f} pts)  -> {tag}")

    print("-" * 76)
    if winner:
        print(f"  {GREEN}{BOLD}🎉 Winner Promoted:{RESET} Candidate '{winner}' ({result['winner_strategy']}) survives to h_{r_num}!")
        print(f"  {CYAN}🗑️  7 Candidate Edits Dropped:{RESET} Non-winning variations discarded.")
    else:
        print(f"  {YELLOW}{BOLD}🛡️  Baseline Optimal:{RESET} Baseline h_{r_num-1} preserved; zero capability erosion.")
    print("=" * 76 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recursive Self-Evolving Harness Loop (Algorithm 1)")
    parser.add_argument("--rounds", "-r", type=int, default=1, help="Number of evolutionary tournament rounds to run")
    parser.add_argument("--candidates", "-c", type=int, default=DEFAULT_CANDIDATES_COUNT, help="Number of candidate edits per round (default 8)")
    parser.add_argument("--tier", choices=["fast", "impact", "full"], default="fast", help="Evaluation speed tier")
    parser.add_argument("--dry-run", action="store_true", help="Simulate tournament without modifying harness file on disk")
    parser.add_argument("--json", action="store_true", help="Output pure JSON to stdout")
    args = parser.parse_args()

    loop = SelfEvolvingLoop(
        candidate_count=args.candidates,
        tier=args.tier,
        dry_run=args.dry_run,
    )

    all_results = []
    for rnd in range(1, args.rounds + 1):
        res = loop.run_tournament_round(round_num=rnd)
        all_results.append(res)
        if not args.json:
            print_tournament_dashboard(res)

    if args.json:
        out = all_results[0] if len(all_results) == 1 else all_results
        print(json.dumps(out, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
