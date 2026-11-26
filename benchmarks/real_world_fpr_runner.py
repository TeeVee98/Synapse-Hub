#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
Real-World False-Positive Rate (FPR <= 5.0%), Recall & Latency Benchmark Runner.

Evaluates Synapse Hub's Meta Infer static defect sentinel + Cross-File POM
Assertion Indexer across:
  1. All polyglot reference suites under `<repo_root>/examples/` (Playwright TS,
     Playwright Python, Cypress, Pytest API, Katalon Groovy, Selenium Java,
     Mobile CRM, Backend Perf).
  2. An isolated adversarial Clean POM & Known-Defect benchmark corpus verifying
     both 0 false positives on POM-encapsulated assertions and >= 95% recall on
     genuine fake-passes, unawaited async assertions, hard delays, and swallowed
     exceptions.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_CURRENT_DIR)
for _p in (_REPO_ROOT, os.path.join(_REPO_ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.context.pom_assertion_indexer import build_pom_assertion_index  # noqa: E402
from tools.lint import infer_linter  # noqa: E402

SUPPORTED_EXTS: Tuple[str, ...] = (".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".groovy")
IGNORED_PARTS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "test-results",
    "playwright-report",
    "allure-results",
    "reports",
    "practices",
    "plugins",
}


@dataclass(frozen=True)
class RealWorldBenchmarkReceiptDTO:
    """Immutable empirical benchmark receipt enforcing FPR, Recall, and P95 latency gates."""

    total_cases: int
    true_positives: int
    false_positives: int
    false_negatives: int
    false_positive_rate_pct: float
    recall_pct: float
    p95_scan_ms: float
    passed: bool
    external_repos_evaluated: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "false_positive_rate_pct": self.false_positive_rate_pct,
            "recall_pct": self.recall_pct,
            "p95_scan_ms": self.p95_scan_ms,
            "passed": self.passed,
            "external_repos_evaluated": self.external_repos_evaluated,
        }


def _compute_p95(samples: List[float]) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = int(0.95 * (len(ordered) - 1))
    return round(ordered[idx], 3)


def _scan_examples_corpus(repo_root: str) -> Tuple[int, int, List[float]]:
    """
    Scans reference suites under `<repo_root>/examples/` with cross-file POM indexing.
    Returns `(true_negatives, false_positives, per_file_latencies_ms)`.
    """
    examples_dir = os.path.join(os.path.abspath(repo_root), "examples")
    if not os.path.isdir(examples_dir):
        return 0, 0, []

    tn = 0
    fp = 0
    latencies: List[float] = []

    for suite_name in sorted(os.listdir(examples_dir)):
        if suite_name.lower() in IGNORED_PARTS:
            continue
        suite_path = os.path.join(examples_dir, suite_name)
        if not os.path.isdir(suite_path):
            continue

        assertion_map = build_pom_assertion_index(suite_path, max_depth=3, prefer_tree_sitter=True)
        for root, dirs, files in os.walk(suite_path):
            dirs[:] = sorted(d for d in dirs if d.lower() not in IGNORED_PARTS and not d.startswith("."))
            for fname in sorted(files):
                if os.path.splitext(fname)[1].lower() not in SUPPORTED_EXTS:
                    continue
                if fname in ("__init__.py", "setup.py"):
                    continue
                fpath = os.path.join(root, fname)
                t0 = time.perf_counter()
                res = infer_linter.analyze_script(fpath, assertion_map=assertion_map)
                latencies.append((time.perf_counter() - t0) * 1000.0)
                if res.get("role") == "CONFIG":
                    continue
                if res.get("is_clean", False):
                    tn += 1
                else:
                    fp += 1

    return tn, fp, latencies


def _run_adversarial_pom_corpus() -> Tuple[int, int, int, int, List[float]]:
    """
    Evaluates curated polyglot Clean POM & Known-Defect fixtures in an isolated temp workspace.
    Returns `(tn, fp, tp, fn, per_file_latencies_ms)`.
    """
    tmp_dir = tempfile.mkdtemp(prefix="synapse_fpr_corpus_")
    try:
        pages = os.path.join(tmp_dir, "pages")
        tests = os.path.join(tmp_dir, "tests")
        os.makedirs(pages, exist_ok=True)
        os.makedirs(tests, exist_ok=True)

        # Shared Page Objects (clean helpers + action-only helpers)
        with open(os.path.join(pages, "CheckoutPage.ts"), "w", encoding="utf-8") as f:
            f.write(
                "import { expect, Page } from '@playwright/test';\n"
                "export class CheckoutPage {\n"
                "  constructor(private page: Page) {}\n"
                "  async confirmOrderComplete() {\n"
                "    await expect(this.page.locator('#receipt')).toBeVisible();\n"
                "  }\n"
                "  async clickSubmit() {\n"
                "    await this.page.click('#submit');\n"
                "  }\n"
                "}\n"
            )
        with open(os.path.join(pages, "DashboardPage.java"), "w", encoding="utf-8") as f:
            f.write(
                "import static org.junit.jupiter.api.Assertions.assertTrue;\n"
                "public class DashboardPage {\n"
                "  public void ensureHeaderReady() {\n"
                "    assertTrue(isVisible());\n"
                "  }\n"
                "}\n"
            )

        clean_fixtures = {
            "clean_pom_ts.spec.ts": (
                "import { test } from '@playwright/test';\n"
                "import { CheckoutPage } from '../pages/CheckoutPage';\n"
                "test('pom assert', async ({ page }) => {\n"
                "  const p = new CheckoutPage(page);\n"
                "  await p.clickSubmit();\n"
                "  await p.confirmOrderComplete();\n"
                "});\n"
            ),
            "clean_multiline_ts.spec.ts": (
                "import { test, expect } from '@playwright/test';\n"
                "test('multiline expect', async ({ page }) => {\n"
                "  await page.click('#calc');\n"
                "  await expect(\n"
                "    page.locator('#total')\n"
                "  )\n"
                "    .toHaveText('$42.00');\n"
                "});\n"
            ),
            "CleanJavaPomTest.java": (
                "public class CleanJavaPomTest {\n"
                "  @Test public void testDash() {\n"
                "    dashboardPage.open();\n"
                "    dashboardPage.ensureHeaderReady();\n"
                "  }\n"
                "}\n"
            ),
            "clean_katalon.groovy": (
                "WebUI.click(findTestObject('btn_save'))\n"
                "WebUI.verifyElementPresent(findTestObject('toast_ok'), 5)\n"
            ),
            "test_clean_py.py": (
                "def test_calculation():\n"
                "    total = 20 + 22\n"
                "    assert total == 42\n"
            ),
        }

        defect_fixtures = {
            "defect_fake_pass_pom.spec.ts": (
                "import { test } from '@playwright/test';\n"
                "import { CheckoutPage } from '../pages/CheckoutPage';\n"
                "test('fake pass', async ({ page }) => {\n"
                "  const p = new CheckoutPage(page);\n"
                "  await p.clickSubmit();\n"
                "});\n"
            ),
            "defect_unawaited.spec.ts": (
                "import { test, expect } from '@playwright/test';\n"
                "test('unawaited', async ({ page }) => {\n"
                "  expect(page.locator('#banner')).toBeVisible();\n"
                "});\n"
            ),
            "defect_hard_delay.spec.ts": (
                "import { test, expect } from '@playwright/test';\n"
                "test('sleep', async ({ page }) => {\n"
                "  await page.waitForTimeout(5000);\n"
                "  await expect(page.locator('#ok')).toBeVisible();\n"
                "});\n"
            ),
            "test_defect_swallow.py": (
                "def test_swallow():\n"
                "    try:\n"
                "        run_checkout()\n"
                "    except Exception:\n"
                "        pass\n"
                "    assert result == 1\n"
            ),
            "defect_tautology.spec.ts": (
                "import { test, expect } from '@playwright/test';\n"
                "test('taut', async () => {\n"
                "  expect(true).toBe(true);\n"
                "});\n"
            ),
            "defect_dangling.spec.ts": (
                "import { test, expect } from '@playwright/test';\n"
                "test('dangling', async ({ page }) => {\n"
                "  expect(page.locator('#id'));\n"
                "});\n"
            ),
        }

        for name, code in {**clean_fixtures, **defect_fixtures}.items():
            with open(os.path.join(tests, name), "w", encoding="utf-8") as f:
                f.write(code)

        assertion_map = build_pom_assertion_index(tmp_dir, max_depth=3, prefer_tree_sitter=True)
        tn = fp = tp = fn = 0
        latencies: List[float] = []

        for name in sorted(clean_fixtures):
            fpath = os.path.join(tests, name)
            t0 = time.perf_counter()
            res = infer_linter.analyze_script(fpath, assertion_map=assertion_map)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            if res.get("is_clean", False):
                tn += 1
            else:
                fp += 1

        for name in sorted(defect_fixtures):
            fpath = os.path.join(tests, name)
            t0 = time.perf_counter()
            res = infer_linter.analyze_script(fpath, assertion_map=assertion_map)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            if not res.get("is_clean", True):
                tp += 1
            else:
                fn += 1

        return tn, fp, tp, fn, latencies
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _scan_external_repo(repo_path: str) -> Tuple[int, int, List[float]]:
    """
    Scans an external real-world OSS repository directory with cross-file POM indexing.
    Raises `FileNotFoundError` if `repo_path` is not an existing directory.
    """
    abs_ext = os.path.abspath(repo_path) if repo_path else ""
    if not abs_ext or not os.path.isdir(abs_ext):
        raise FileNotFoundError(f"External benchmark repository directory not found: {repo_path}")

    tn = 0
    fp = 0
    latencies: List[float] = []
    assertion_map = build_pom_assertion_index(abs_ext, max_depth=3, prefer_tree_sitter=True)
    for root, dirs, files in os.walk(abs_ext):
        dirs[:] = sorted(d for d in dirs if d.lower() not in IGNORED_PARTS and not d.startswith("."))
        for fname in sorted(files):
            if os.path.splitext(fname)[1].lower() not in SUPPORTED_EXTS:
                continue
            if fname in ("__init__.py", "setup.py"):
                continue
            fpath = os.path.join(root, fname)
            t0 = time.perf_counter()
            res = infer_linter.analyze_script(fpath, assertion_map=assertion_map)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            if res.get("role") == "CONFIG":
                continue
            if res.get("is_clean", False):
                tn += 1
            else:
                fp += 1
    return tn, fp, latencies


def run_fpr_benchmark(
    repo_root: str,
    max_fpr_pct: float = 5.0,
    max_p95_ms: float = 50.0,
    include_adversarial_corpus: bool = True,
    external_repo_paths: Optional[List[str]] = None,
) -> RealWorldBenchmarkReceiptDTO:
    """Executes false-positive, recall, and latency benchmarking across internal & external OSS POM suites."""
    ex_tn, ex_fp, ex_latencies = _scan_examples_corpus(repo_root)
    ext_count = 0
    for ext_path in external_repo_paths or ():
        r_tn, r_fp, r_lat = _scan_external_repo(ext_path)
        ex_tn += r_tn
        ex_fp += r_fp
        ex_latencies.extend(r_lat)
        ext_count += 1

    if include_adversarial_corpus:
        adv_tn, adv_fp, adv_tp, adv_fn, adv_latencies = _run_adversarial_pom_corpus()
    else:
        adv_tn = adv_fp = adv_tp = adv_fn = 0
        adv_latencies = []

    tn = ex_tn + adv_tn
    fp = ex_fp + adv_fp
    tp = adv_tp
    fn = adv_fn
    total = tn + fp + tp + fn
    all_latencies = ex_latencies + adv_latencies

    fpr_pct = round((fp / (fp + tn)) * 100.0, 2) if (fp + tn) > 0 else 0.0
    recall_pct = round((tp / (tp + fn)) * 100.0, 2) if (tp + fn) > 0 else 100.0
    p95_ms = _compute_p95(all_latencies)

    passed = (fpr_pct <= max_fpr_pct) and (recall_pct >= 95.0) and (p95_ms <= max_p95_ms)
    return RealWorldBenchmarkReceiptDTO(
        total_cases=total,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        false_positive_rate_pct=fpr_pct,
        recall_pct=recall_pct,
        p95_scan_ms=p95_ms,
        passed=passed,
        external_repos_evaluated=ext_count,
    )


def _format_markdown_receipt(receipt: RealWorldBenchmarkReceiptDTO) -> str:
    status = "PASSED" if receipt.passed else "FAILED"
    return (
        "# Synapse Hub Real-World False-Positive Benchmark Receipt\n\n"
        f"- **Verdict:** `{status}`\n"
        f"- **Total Evaluated Files:** `{receipt.total_cases}`\n"
        f"- **External OSS Repos Evaluated:** `{receipt.external_repos_evaluated}`\n"
        f"- **True Positives (Defects Caught):** `{receipt.true_positives}`\n"
        f"- **False Positives:** `{receipt.false_positives}`\n"
        f"- **False Negatives:** `{receipt.false_negatives}`\n"
        f"- **False-Positive Rate (FPR):** `{receipt.false_positive_rate_pct:.2f}%` (Gate: `<= 5.0%`)\n"
        f"- **Defect Recall:** `{receipt.recall_pct:.2f}%` (Gate: `>= 95.0%`)\n"
        f"- **P95 Per-File Scan Latency:** `{receipt.p95_scan_ms:.3f} ms` (Gate: `<= 50.0 ms`)\n"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Real-World False-Positive Rate (FPR <= 5.0%), Recall & Latency Benchmark Runner"
    )
    parser.add_argument("--root", default=_REPO_ROOT, help="Repository root containing examples/")
    parser.add_argument(
        "--external-repo",
        action="append",
        default=[],
        help="Optional path to an external OSS Playwright/Pytest/Selenium repository (repeatable)",
    )
    parser.add_argument("--max-fpr", type=float, default=5.0, help="Maximum allowed FPR percentage")
    parser.add_argument("--max-p95-ms", type=float, default=50.0, help="Maximum allowed P95 scan ms")
    parser.add_argument(
        "--no-adversarial",
        action="store_true",
        help="Scan only `<root>/examples/` without the embedded adversarial POM corpus",
    )
    parser.add_argument("--out", default=None, help="Optional output path (.json or .md receipt)")
    parser.add_argument("--json", action="store_true", help="Emit JSON receipt to stdout")
    args = parser.parse_args(argv)

    try:
        receipt = run_fpr_benchmark(
            repo_root=args.root,
            max_fpr_pct=args.max_fpr,
            max_p95_ms=args.max_p95_ms,
            include_adversarial_corpus=not args.no_adversarial,
            external_repo_paths=args.external_repo,
        )
    except FileNotFoundError as exc:
        err_payload = {"passed": False, "error": str(exc)}
        if args.json:
            print(json.dumps(err_payload, indent=2, sort_keys=True))
        else:
            sys.stderr.write(f"[ERROR] {exc}\n")
        return 2

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            if args.out.lower().endswith(".md"):
                handle.write(_format_markdown_receipt(receipt))
            else:
                handle.write(json.dumps(receipt.to_dict(), indent=2, sort_keys=True) + "\n")

    if args.json:
        print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
    else:
        print(_format_markdown_receipt(receipt))

    return 0 if receipt.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
