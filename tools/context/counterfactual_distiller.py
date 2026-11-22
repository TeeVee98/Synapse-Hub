#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/context/counterfactual_distiller.py — Tier 14 Boundary Counterfactual Few-Shot Distiller
----------------------------------------------------------------------------------------------
Implements Support-Vector Decision Boundary Distillation for Few-Shot Prompts:
  1. Near-Miss Counterfactual Database: Curated repository of subtle, near-boundary failure modes
     (race conditions, flaky locators, async unhandled rejections, off-by-one, type fallacies).
  2. Minimal Counterfactual Matching: Matches target task/code against decision boundaries,
     selecting STRICTLY 2 pairs of (near_miss_code, minimal_fix_code).
  3. Attention Sharpening: Eliminates 80-85% token bloat compared to 10-20 generic examples while
     locking the model's self-attention onto the exact decision boundary where bugs occur.

Usage:
  python3 tools/context/counterfactual_distiller.py --domain concurrency --snippet "lock.acquire()" --json
  python3 tools/context/counterfactual_distiller.py --task "Fix flaky dynamic locator in Playwright" --json
  python3 tools/context/counterfactual_distiller.py --benchmark --json
  python3 tools/context/counterfactual_distiller.py --gate
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


@dataclass
class CounterfactualPair:
    """Represents a near-miss flawed snippet and its minimal surgical fix."""

    pair_id: str
    domain: str
    decision_boundary: str
    subtle_flaw: str
    near_miss_code: str
    minimal_fix_code: str
    delta_loc: int
    keywords: List[str]


# Pre-computed curated boundary database
CURATED_PAIRS: List[CounterfactualPair] = [
    # 1. Concurrency / Race Condition
    CounterfactualPair(
        pair_id="CONC_001",
        domain="concurrency",
        decision_boundary="Non-reentrant Lock Acquisition within nested helper",
        subtle_flaw="Deadlock occurs when helper re-acquires standard threading.Lock",
        near_miss_code="lock = threading.Lock()\nwith lock:\n    update_user(user_id)\n    log_audit(user_id) # log_audit also calls with lock",
        minimal_fix_code="lock = threading.RLock()\nwith lock:\n    update_user(user_id)\n    log_audit(user_id)",
        delta_loc=1,
        keywords=["lock", "thread", "concurrency", "deadlock", "mutex", "rlock"],
    ),
    CounterfactualPair(
        pair_id="CONC_002",
        domain="concurrency",
        decision_boundary="Check-Then-Act Race Condition on shared resource",
        subtle_flaw="State changes between if-check and write operation",
        near_miss_code="if key not in cache:\n    time.sleep(0.01)\n    cache[key] = compute_value(key)",
        minimal_fix_code="cache.setdefault(key, None) or cache.update({key: compute_value(key)})",
        delta_loc=1,
        keywords=["cache", "race", "atomic", "check-then-act", "setnx"],
    ),
    # 2. Flaky Locator / Dynamic Wait (Clean POM)
    CounterfactualPair(
        pair_id="FLAKY_001",
        domain="flaky_locator",
        decision_boundary="Static sleep vs Web-first assertion polling",
        subtle_flaw="waitForTimeout(2000) fails in congested CI environments or wastes time",
        near_miss_code="await page.click('#submit-btn');\nawait page.waitForTimeout(3000);\nexpect(await page.isVisible('#success')).toBe(true);",
        minimal_fix_code="await page.click('#submit-btn');\nawait expect(page.locator('#success')).toBeVisible();",
        delta_loc=2,
        keywords=["waitfortimeout", "sleep", "flaky", "locator", "timeout", "isvisible"],
    ),
    CounterfactualPair(
        pair_id="FLAKY_002",
        domain="flaky_locator",
        decision_boundary="Fragile absolute XPath vs Semantic ARIA role locator",
        subtle_flaw="Broken by minor DOM restyling or CSS class renaming",
        near_miss_code="await page.click('//div[@id=\"app\"]/div[2]/form/div[3]/button');",
        minimal_fix_code="await page.getByRole('button', { name: 'Submit' }).click();",
        delta_loc=1,
        keywords=["xpath", "aria", "role", "locator", "getbyrole", "pom"],
    ),
    # 3. Async / Promise Unhandled Rejection
    CounterfactualPair(
        pair_id="ASYNC_001",
        domain="async_await",
        decision_boundary="Unawaited async function in Array.prototype.map",
        subtle_flaw="map does not await promises, causing unhandled background rejections",
        near_miss_code="items.map(async (item) => {\n  await processItem(item);\n});",
        minimal_fix_code="await Promise.all(items.map((item) => processItem(item)));",
        delta_loc=1,
        keywords=["async", "promise", "map", "unhandled", "await", "promise.all"],
    ),
    CounterfactualPair(
        pair_id="ASYNC_002",
        domain="async_await",
        decision_boundary="Missing return await inside try/catch block",
        subtle_flaw="Bare return promise bypasses catch handler when rejection occurs asynchronously",
        near_miss_code="try {\n  return fetchUserData(id);\n} catch (err) {\n  return fallbackUser;\n}",
        minimal_fix_code="try {\n  return await fetchUserData(id);\n} catch (err) {\n  return fallbackUser;\n}",
        delta_loc=1,
        keywords=["try", "catch", "return", "await", "rejection", "fallback"],
    ),
    # 4. Off-by-one / Boundary Conditions
    CounterfactualPair(
        pair_id="BOUND_001",
        domain="boundary",
        decision_boundary="Inclusive vs Exclusive end index in slice pagination",
        subtle_flaw="Truncates the final record on exact page boundary",
        near_miss_code="def get_page(items, page, size):\n    return items[(page - 1) * size : page * size - 1]",
        minimal_fix_code="def get_page(items, page, size):\n    return items[(page - 1) * size : page * size]",
        delta_loc=1,
        keywords=["page", "slice", "pagination", "off-by-one", "boundary", "index"],
    ),
    CounterfactualPair(
        pair_id="BOUND_002",
        domain="boundary",
        decision_boundary="Unvalidated zero or negative boundary in retry backoff",
        subtle_flaw="Zero multiplier leads to division by zero or infinite CPU tight loop",
        near_miss_code="backoff = base_delay * (2 ** retry_count)\ntime.sleep(backoff)",
        minimal_fix_code="backoff = max(0.1, min(max_delay, base_delay * (2 ** max(0, retry_count))))\ntime.sleep(backoff)",
        delta_loc=2,
        keywords=["backoff", "retry", "zero", "negative", "overflow", "loop"],
    ),
    # 5. Resource Leak / Unclosed Handles
    CounterfactualPair(
        pair_id="LEAK_001",
        domain="resource_leak",
        decision_boundary="Unmanaged file handle under exception",
        subtle_flaw="File descriptor leaks when parsing raises an exception before close()",
        near_miss_code="f = open('data.json', 'r')\ndata = json.loads(f.read())\nf.close()",
        minimal_fix_code="with open('data.json', 'r', encoding='utf-8') as f:\n    data = json.load(f)",
        delta_loc=2,
        keywords=["open", "file", "leak", "handle", "close", "descriptor"],
    ),
    # 6. SQL / Injection / Parameterization
    CounterfactualPair(
        pair_id="SEC_001",
        domain="security_injection",
        decision_boundary="Raw f-string SQL formatting vs Parameterized placeholder",
        subtle_flaw="Enables classic SQL injection via unescaped string concatenation",
        near_miss_code="cursor.execute(f\"SELECT * FROM users WHERE email = '{email}' AND tenant = '{tenant}'\")",
        minimal_fix_code="cursor.execute(\"SELECT * FROM users WHERE email = ? AND tenant = ?\", (email, tenant))",
        delta_loc=1,
        keywords=["sql", "injection", "cursor", "execute", "select", "query"],
    ),
    # 7. Type / Falsey Null Checks
    CounterfactualPair(
        pair_id="TYPE_001",
        domain="type_narrowing",
        decision_boundary="Falsey check vs Explicit None comparison for numeric/empty values",
        subtle_flaw="Bypasses valid zero (0), false (False), or empty string (\"\") as if unassigned",
        near_miss_code="def update_score(user_id, score=None):\n    if not score:\n        score = get_default_score()",
        minimal_fix_code="def update_score(user_id, score=None):\n    if score is None:\n        score = get_default_score()",
        delta_loc=1,
        keywords=["none", "falsey", "null", "falsy", "score", "type", "narrowing"],
    ),
]


class CounterfactualDistiller:
    """Selects and formats exactly 2 near-miss counterfactual pairs on the decision boundary."""

    def __init__(self, database: Optional[List[CounterfactualPair]] = None) -> None:
        self.db = database or CURATED_PAIRS

    def _score_pair(self, pair: CounterfactualPair, query_tokens: Set[str], domain_hint: Optional[str]) -> float:
        """Computes boundary relevance score between query and counterfactual pair."""
        score = 0.0
        if domain_hint and domain_hint.lower() == pair.domain.lower():
            score += 10.0

        for kw in pair.keywords:
            if kw.lower() in query_tokens:
                score += 2.0

        # Boundary description matching
        boundary_words = set(re.findall(r"\w+", pair.decision_boundary.lower()))
        overlap = query_tokens.intersection(boundary_words)
        score += len(overlap) * 1.5

        return score

    def distill(
        self,
        task_or_code: str,
        domain_hint: Optional[str] = None,
        exact_k: int = 2,
    ) -> List[CounterfactualPair]:
        """Retrieves exactly K (default 2) boundary counterfactual pairs closest to the query."""
        tokens = set(re.findall(r"\w+", task_or_code.lower()))
        scored: List[Tuple[float, CounterfactualPair]] = []

        for pair in self.db:
            score = self._score_pair(pair, tokens, domain_hint)
            scored.append((score, pair))

        scored.sort(key=lambda x: x[0], reverse=True)

        selected = [p for _, p in scored[:exact_k]]
        # If fewer than exact_k, fill from remaining
        if len(selected) < exact_k and len(self.db) >= exact_k:
            remaining = [p for p in self.db if p not in selected]
            selected.extend(remaining[: exact_k - len(selected)])

        return selected

    @staticmethod
    def format_distilled_prompt(pairs: List[CounterfactualPair]) -> str:
        """Formats the distilled pairs into an ultra-dense prompt block."""
        lines = ["### BOUNDARY COUNTERFACTUAL PAIRS (Focus Attention on Flaw vs Surgical Fix)"]
        for idx, p in enumerate(pairs, 1):
            lines.append(f"Pair {idx} [{p.pair_id}: {p.decision_boundary}]")
            lines.append(f"- Near-Miss (FLAW): {p.subtle_flaw}")
            lines.append(f"```\n{p.near_miss_code}\n```")
            lines.append(f"- Surgical Fix (+{p.delta_loc} LOC):")
            lines.append(f"```\n{p.minimal_fix_code}\n```")
        return "\n".join(lines)

    @staticmethod
    def calculate_token_savings(
        distilled_pairs: List[CounterfactualPair],
        standard_fewshot_count: int = 12,
    ) -> Dict[str, Any]:
        """Calculates token reduction vs standard 10-15 few-shot examples."""
        distilled_text = CounterfactualDistiller.format_distilled_prompt(distilled_pairs)
        distilled_tokens = max(1, math.ceil(len(distilled_text) / 4))

        # Standard few-shot: approx 150 tokens per example * count
        standard_tokens = standard_fewshot_count * 150
        savings_pct = round(((standard_tokens - distilled_tokens) / standard_tokens) * 100, 1)

        return {
            "distilled_tokens": distilled_tokens,
            "standard_tokens": standard_tokens,
            "token_reduction_pct": savings_pct,
            "pairs_selected": len(distilled_pairs),
        }


def run_benchmark() -> Dict[str, Any]:
    """Runs self-eval benchmark evaluating Tier 14 boundary distillation."""
    distiller = CounterfactualDistiller()
    task = "Investigate flaky test in Playwright where waitForTimeout was used instead of smart wait"

    pairs = distiller.distill(task, domain_hint="flaky_locator", exact_k=2)
    prompt_block = CounterfactualDistiller.format_distilled_prompt(pairs)
    savings = CounterfactualDistiller.calculate_token_savings(pairs)

    is_pass = (
        len(pairs) == 2
        and pairs[0].domain == "flaky_locator"
        and savings["token_reduction_pct"] >= 70.0
    )

    return {
        "status": "PASS" if is_pass else "FAIL",
        "task": task,
        "selected_pair_ids": [p.pair_id for p in pairs],
        "token_savings": savings,
        "sample_prompt": prompt_block,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tier 14 Boundary Counterfactual Few-Shot Distiller"
    )
    parser.add_argument("--task", help="Task description to match against decision boundaries")
    parser.add_argument("--snippet", help="Code snippet exhibiting potential edge-case flaws")
    parser.add_argument("--domain", help="Domain filter (concurrency, flaky_locator, async_await, boundary, resource_leak, security_injection, type_narrowing)")
    parser.add_argument("--database", help="Path to custom JSON file containing CounterfactualPair entries")
    parser.add_argument("--list-domains", action="store_true", help="List registered boundary domains")
    parser.add_argument("--benchmark", action="store_true", help="Run self-contained benchmark")
    parser.add_argument("--gate", action="store_true", help="Run DoD gate check")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    if args.gate:
        bench = run_benchmark()
        is_pass = bench["status"] == "PASS" and bench["token_savings"]["token_reduction_pct"] >= 70.0
        if args.json:
            print(json.dumps({"gate": "Tier 14 Counterfactual Distiller", "passed": is_pass, "details": bench}, indent=2))
        else:
            status_str = "[PASS]" if is_pass else "[FAIL]"
            print(f"{status_str} Tier 14 Counterfactual Distiller Gate verified ({bench['token_savings']['token_reduction_pct']}% token cut).")
        sys.exit(0 if is_pass else 1)

    if args.list_domains:
        domains = sorted(list({p.domain for p in CURATED_PAIRS}))
        payload = {"domains": domains, "total_pairs": len(CURATED_PAIRS)}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Registered Domains ({len(domains)}): {', '.join(domains)}")
        sys.exit(0)

    if args.benchmark:
        res = run_benchmark()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Status           : {res['status']}")
            print(f"Selected Pairs   : {res['selected_pair_ids']}")
            print(f"Token Reduction  : {res['token_savings']['token_reduction_pct']}%")
            print(f"\nPrompt Block:\n{res['sample_prompt']}")
        sys.exit(0 if res["status"] == "PASS" else 1)

    query = args.task or args.snippet
    if not query and not args.domain:
        print("Error: Provide --task, --snippet, or --domain", file=sys.stderr)
        sys.exit(1)

    custom_db = None
    if args.database and os.path.exists(args.database):
        try:
            with open(args.database, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
                custom_db = [CounterfactualPair(**item) for item in raw_list]
        except Exception as e:
            print(f"Warning: Failed to load custom database: {e}", file=sys.stderr)

    distiller = CounterfactualDistiller(database=custom_db)
    pairs = distiller.distill(query or "", domain_hint=args.domain, exact_k=2)
    prompt = CounterfactualDistiller.format_distilled_prompt(pairs)
    savings = CounterfactualDistiller.calculate_token_savings(pairs)

    output = {
        "status": "SUCCESS",
        "pairs": [asdict(p) for p in pairs],
        "token_savings": savings,
        "distilled_prompt": prompt,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"[DISTILLED 2 BOUNDARY PAIRS] ({savings['token_reduction_pct']}% token cut)")
        print(prompt)


if __name__ == "__main__":
    main()
