#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
4-Scenario Parity & Fallback Certification Suite:
  bin/native-linter.js (Zero-Python Node.js >= 18 Engine) vs tools/lint/infer_linter.py.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_QA_JS = REPO_ROOT / "bin" / "agent-qa.js"
NATIVE_LINTER_JS = REPO_ROOT / "bin" / "native-linter.js"
INFER_LINTER_PY = REPO_ROOT / "tools" / "lint" / "infer_linter.py"
NODE_BIN = shutil.which("node")


def _require_node() -> str:
    if not NODE_BIN:
        pytest.skip("Node.js runtime not available on PATH")
    return NODE_BIN


def _make_pythonless_env(tmp_path: Path) -> Dict[str, str]:
    """Builds an isolated PATH containing ONLY the node executable (no python/python3/py)."""
    node_bin = _require_node()
    node_only_dir = tmp_path / "node_only_bin"
    node_only_dir.mkdir(parents=True, exist_ok=True)
    node_name = "node.exe" if os.name == "nt" else "node"
    link_target = node_only_dir / node_name
    if not link_target.exists():
        try:
            os.symlink(node_bin, link_target)
        except OSError:
            shutil.copy2(node_bin, link_target)
    env = dict(os.environ)
    env["PATH"] = str(node_only_dir)
    env["NO_COLOR"] = "1"
    return env


def _run_native_js(args: List[str], env: Dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    node_bin = _require_node()
    run_env = dict(os.environ) if env is None else dict(env)
    run_env["NO_COLOR"] = "1"
    return subprocess.run(
        [node_bin, str(AGENT_QA_JS), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=run_env,
        timeout=20,
    )


def _run_python_linter(target: Path, fmt: str = "json") -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [sys.executable, str(INFER_LINTER_PY), str(target), "--format", fmt],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=20,
    )


def _extract_defect_pairs(report: Dict[str, object]) -> Set[Tuple[str, str]]:
    all_defects = report.get("all_defects", [])
    assert isinstance(all_defects, list)
    pairs: Set[Tuple[str, str]] = set()
    for item in all_defects:
        assert isinstance(item, dict)
        fname = os.path.basename(str(item.get("file", "")))
        dtype = str(item.get("type", ""))
        pairs.add((fname, dtype))
    return pairs


def _write_clean_pom_project(root: Path) -> Path:
    pages = root / "pages"
    tests = root / "tests"
    pages.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)

    (pages / "CheckoutPage.ts").write_text(
        """
import { Page, expect } from '@playwright/test';

export class CheckoutPage {
  constructor(private readonly page: Page) {}

  async submitOrder(code: string) {
    await this.page.getByRole('textbox', { name: 'Code' }).fill(code);
    await this.page.getByRole('button', { name: 'Submit' }).click();
  }

  async verifyOrderConfirmed() {
    await expect(this.page.getByTestId('order-confirmed')).toBeVisible();
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (tests / "checkout.spec.ts").write_text(
        """
import { test } from '@playwright/test';
import { CheckoutPage } from '../pages/CheckoutPage';

test('TC-01: clean POM checkout order confirmation', async ({ page }) => {
  const checkoutPage = new CheckoutPage(page);
  await checkoutPage.submitOrder('ORD-1001');
  await checkoutPage.verifyOrderConfirmed();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return root


def _write_six_defect_fixtures(root: Path) -> Path:
    tests = root / "tests"
    tests.mkdir(parents=True, exist_ok=True)

    (tests / "d1_fake_pass.spec.ts").write_text(
        """
import { test } from '@playwright/test';

test('TC-D1: fake pass without assertion', async ({ page }) => {
  await page.goto('/dashboard');
  await page.click('#submit-btn');
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (tests / "d2_unawaited.spec.ts").write_text(
        """
import { test, expect } from '@playwright/test';

test('TC-D2: unawaited async assertion', async ({ page }) => {
  await page.goto('/dashboard');
  expect(page.getByTestId('welcome')).toBeVisible();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (tests / "d3_dangling.spec.ts").write_text(
        """
import { test, expect } from '@playwright/test';

test('TC-D3: dangling expect without matcher', async ({ page }) => {
  await page.goto('/dashboard');
  expect(page.getByTestId('welcome'));
  await expect(page.getByTestId('ok')).toBeVisible();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (tests / "d4_hard_delay.spec.ts").write_text(
        """
import { test, expect } from '@playwright/test';

test('TC-D4: excessive hard delay', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForTimeout(5000);
  await expect(page.getByTestId('welcome')).toBeVisible();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (tests / "d5_swallowed.spec.ts").write_text(
        """
import { test, expect } from '@playwright/test';

test('TC-D5: swallowed exception', async ({ page }) => {
  try {
    await page.goto('/dashboard');
  } catch (e) {}
  await expect(page.getByTestId('welcome')).toBeVisible();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (tests / "d6_tautology.spec.ts").write_text(
        """
import { test, expect } from '@playwright/test';

test('TC-D6: tautological assertion', async ({ page }) => {
  await page.goto('/dashboard');
  expect(true).toBe(true);
});
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------------------
# 1. POSITIVE SCENARIOS: 1:1 JS vs Python parity, Clean POM & --fix idempotency
# ---------------------------------------------------------------------------


def test_positive_native_js_python_1to1_parity_on_clean_pom_and_6_defects(tmp_path: Path) -> None:
    assert NATIVE_LINTER_JS.is_file(), "bin/native-linter.js must exist"

    clean_proj = _write_clean_pom_project(tmp_path / "clean_proj")
    js_clean = _run_native_js(["lint", str(clean_proj), "--engine", "native-js", "--json"])
    py_clean = _run_python_linter(clean_proj, fmt="json")

    assert js_clean.returncode == 0, js_clean.stderr
    assert py_clean.returncode == 0, py_clean.stderr

    js_clean_data = json.loads(js_clean.stdout)
    py_clean_data = json.loads(py_clean.stdout)
    assert js_clean_data["engine"] == "native-js"
    assert js_clean_data["critical_defects"] == 0
    assert js_clean_data["warnings"] == 0
    assert js_clean_data["clean_scripts"] == js_clean_data["total_scripts"]
    assert _extract_defect_pairs(js_clean_data) == _extract_defect_pairs(py_clean_data) == set()

    defect_proj = _write_six_defect_fixtures(tmp_path / "defect_proj")
    js_def = _run_native_js(["lint", str(defect_proj), "--engine", "native-js", "--json"])
    py_def = _run_python_linter(defect_proj, fmt="json")

    assert js_def.returncode == 1
    assert py_def.returncode == 1

    js_def_data = json.loads(js_def.stdout)
    py_def_data = json.loads(py_def.stdout)
    js_pairs = _extract_defect_pairs(js_def_data)
    py_pairs = _extract_defect_pairs(py_def_data)

    expected_pairs = {
        ("d1_fake_pass.spec.ts", "FAKE_PASS_NO_ASSERTION"),
        ("d2_unawaited.spec.ts", "UNAWAITED_ASYNC_ASSERTION"),
        ("d3_dangling.spec.ts", "DANGLING_ASSERTION_NO_MATCHER"),
        ("d4_hard_delay.spec.ts", "EXCESSIVE_HARD_DELAY"),
        ("d5_swallowed.spec.ts", "SWALLOWED_EXCEPTION"),
        ("d6_tautology.spec.ts", "TAUTOLOGICAL_ASSERTION"),
    }
    assert expected_pairs.issubset(js_pairs)
    assert js_pairs == py_pairs, f"JS vs Python parity drift: js={js_pairs} py={py_pairs}"


def test_positive_native_js_clean_crm_reference_and_autofix_idempotency(tmp_path: Path) -> None:
    crm_dir = REPO_ROOT / "examples" / "playwright-crm-suite"
    t0 = time.perf_counter()
    crm_res = _run_native_js(["lint", str(crm_dir), "--engine", "native-js", "--json"])
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert crm_res.returncode == 0, crm_res.stderr
    crm_data = json.loads(crm_res.stdout)
    assert crm_data["critical_defects"] == 0
    assert crm_data["warnings"] == 0
    assert crm_data["total_scripts"] >= 4
    assert elapsed_ms < 2000.0

    # Auto-fix idempotency check
    fixable_dir = tmp_path / "fixable" / "tests"
    fixable_dir.mkdir(parents=True)
    target_file = fixable_dir / "broken.spec.ts"
    target_file.write_text(
        """
import { test, expect } from '@playwright/test';

test('fixable defects', async ({ page }) => {
  await page.waitForTimeout(5000);
  expect(page.getByTestId('banner')).toBeVisible();
  expect(page.getByTestId('card'));
  try {
    await page.getByRole('button').click();
  } catch (err) {}
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    fix1 = _run_native_js(["fix", str(target_file), "--engine", "native-js"])
    assert fix1.returncode == 0, fix1.stderr
    after_first_fix = target_file.read_text(encoding="utf-8")
    assert "waitForTimeout" not in after_first_fix
    assert "await expect(page.getByTestId('banner')).toBeVisible();" in after_first_fix
    assert "expect(page.getByTestId('card')).toBeVisible();" in after_first_fix
    assert "throw err;" in after_first_fix

    # Second pass must be strictly idempotent (zero diffs)
    fix2 = _run_native_js(["fix", str(target_file), "--engine", "native-js"])
    assert fix2.returncode == 0, fix2.stderr
    assert target_file.read_text(encoding="utf-8") == after_first_fix

    # Clean POM raw XPath detection
    raw_xpath_file = fixable_dir / "raw_xpath.spec.ts"
    raw_xpath_file.write_text(
        """
import { test, expect } from '@playwright/test';

test('raw xpath test', async ({ page }) => {
  await expect(page.locator('//div[@id="hero"]')).toBeVisible();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )
    xpath_res = _run_native_js(["lint", str(raw_xpath_file), "--engine", "native-js", "--json"])
    xpath_data = json.loads(xpath_res.stdout)
    defect_types = {d["type"] for d in xpath_data["all_defects"]}
    assert "CLEAN_POM_VIOLATION" in defect_types


# ---------------------------------------------------------------------------
# 2. NEGATIVE SCENARIOS: Python-less PATH fallback & Python-only subcommand
# ---------------------------------------------------------------------------


def test_negative_pythonless_path_runs_native_commands_and_guides_python_only(tmp_path: Path) -> None:
    pyless_env = _make_pythonless_env(tmp_path)
    clean_proj = _write_clean_pom_project(tmp_path / "pyless_clean")

    # Supported zero-Python commands MUST succeed without python on PATH
    ver_res = _run_native_js(["version"], env=pyless_env)
    assert ver_res.returncode == 0, ver_res.stderr
    assert "Thế Vị (@TeeVee98)" in ver_res.stdout

    help_res = _run_native_js(["help"], env=pyless_env)
    assert help_res.returncode == 0, help_res.stderr
    assert "lint" in help_res.stdout and "native-js" in help_res.stdout

    doc_res = _run_native_js(["doctor", "--json"], env=pyless_env)
    assert doc_res.returncode == 0, doc_res.stderr
    doc_data = json.loads(doc_res.stdout)
    assert doc_data["engine"] == "native-js"
    assert doc_data["python_available"] is False
    assert doc_data["node_version"].startswith("v")

    lint_res = _run_native_js(["lint", str(clean_proj), "--json"], env=pyless_env)
    assert lint_res.returncode == 0, lint_res.stderr
    lint_data = json.loads(lint_res.stdout)
    assert lint_data["engine"] == "native-js"
    assert lint_data["critical_defects"] == 0

    fix_file = clean_proj / "tests" / "to_fix.spec.ts"
    fix_file.write_text(
        "import { test, expect } from '@playwright/test';\ntest('t', async ({ page }) => {\n  await page.waitForTimeout(4000);\n  await expect(page.getByTestId('x')).toBeVisible();\n});\n",
        encoding="utf-8",
    )
    fix_res = _run_native_js(["fix", str(fix_file)], env=pyless_env)
    assert fix_res.returncode == 0, fix_res.stderr
    assert "waitForTimeout" not in fix_file.read_text(encoding="utf-8")

    # Python-only subcommand (mutate) must exit non-zero with clear Python 3.10+ guidance
    mut_res = _run_native_js(["mutate"], env=pyless_env)
    assert mut_res.returncode != 0
    combined_err = mut_res.stderr + mut_res.stdout
    assert "Python 3.10+" in combined_err

    # Unauthorized flags (--py) and invalid --engine must still be blocked
    py_bypass = _run_native_js(["--py", "-c", "print(1)"], env=pyless_env)
    assert py_bypass.returncode != 0
    bad_engine = _run_native_js(["lint", str(clean_proj), "--engine", "invalid-engine"], env=pyless_env)
    assert bad_engine.returncode != 0


# ---------------------------------------------------------------------------
# 3. BOUNDARY SCENARIOS: Empty files, UTF-8 backticks, nonexistent path, node_modules pruning
# ---------------------------------------------------------------------------


def test_boundary_empty_utf8_backticks_nonexistent_and_node_modules_pruning(tmp_path: Path) -> None:
    proj = tmp_path / "boundary_proj"
    tests = proj / "tests"
    nm = proj / "node_modules" / "fake_pkg"
    tests.mkdir(parents=True)
    nm.mkdir(parents=True)

    # 0-byte empty test script
    (tests / "empty.spec.ts").write_text("", encoding="utf-8")

    # UTF-8 template literal containing defect-looking text must NOT trigger false positives
    (tests / "backticks.spec.ts").write_text(
        """
import { test, expect } from '@playwright/test';

test('UTF-8 backtick template literals are lexically stripped', async ({ page }) => {
  const sample = `
    // Kiểm thử tiếng Việt UTF-8
    await page.waitForTimeout(5000);
    expect(true).toBe(true);
    try { doSomething(); } catch (e) {}
  `;
  await expect(page.getByText(sample)).toBeVisible();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Defect inside node_modules MUST be pruned
    (nm / "ignored.spec.ts").write_text("await page.waitForTimeout(9000);\n", encoding="utf-8")

    js_res = _run_native_js(["lint", str(proj), "--engine", "native-js", "--json"])
    py_res = _run_python_linter(proj, fmt="json")

    js_data = json.loads(js_res.stdout)
    py_data = json.loads(py_res.stdout)
    assert js_data["total_scripts"] == 2
    assert _extract_defect_pairs(js_data) == {("empty.spec.ts", "EMPTY_TEST_SCRIPT")}
    assert _extract_defect_pairs(js_data) == _extract_defect_pairs(py_data)

    # Nonexistent path exits cleanly without crash
    missing = _run_native_js(["lint", str(tmp_path / "does_not_exist"), "--engine", "native-js", "--json"])
    assert missing.returncode == 0
    missing_data = json.loads(missing.stdout)
    assert missing_data["total_scripts"] == 0


# ---------------------------------------------------------------------------
# 4. CLI FLAGS: --engine native-js, --json, --sarif, --fix --dry-run
# ---------------------------------------------------------------------------


def test_cli_native_js_sarif_json_dry_run_and_strict_flags(tmp_path: Path) -> None:
    defect_proj = _write_six_defect_fixtures(tmp_path / "cli_flags_proj")

    sarif_res = _run_native_js(["lint", str(defect_proj), "--engine", "native-js", "--sarif"])
    assert sarif_res.returncode == 1
    sarif_doc = json.loads(sarif_res.stdout)
    assert sarif_doc["version"] == "2.1.0"
    assert len(sarif_doc["runs"]) == 1
    assert sarif_doc["runs"][0]["tool"]["driver"]["name"] == "synapse-native-js-linter"
    assert len(sarif_doc["runs"][0]["results"]) >= 6

    # --fix --dry-run must NOT mutate file on disk
    d4_file = defect_proj / "tests" / "d4_hard_delay.spec.ts"
    original_text = d4_file.read_text(encoding="utf-8")
    dry_res = _run_native_js(["lint", str(d4_file), "--engine", "native-js", "--fix", "--dry-run"])
    assert dry_res.returncode in (0, 1)
    assert d4_file.read_text(encoding="utf-8") == original_text
