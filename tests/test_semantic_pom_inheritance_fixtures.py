#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
4-Scenario Verification Suite for M3:
  Semantic POM Graph — Multi-Level Inheritance (`extends`), Playwright
  `test.extend<Fixtures>`, Barrel `index.ts` Re-Exports & Aliased Imports.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from tools.context.pom_assertion_indexer import (
    _INDEX_CACHE,
    _extract_barrel_export_aliases,
    _extract_python_class_parents,
    build_pom_assertion_index,
    clear_index_cache,
    extract_playwright_fixture_bindings,
    resolve_class_inheritance_assertions,
)
from tools.lint.infer_linter import analyze_script


# ---------------------------------------------------------------------------
# 1. POSITIVE: 3-tier extends inheritance, test.extend<Fixtures>, barrel & alias
# ---------------------------------------------------------------------------


def test_positive_three_tier_inheritance_playwright_fixtures_and_barrel_alias(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    fixtures = tmp_path / "fixtures"
    tests = tmp_path / "tests"
    pages.mkdir()
    fixtures.mkdir()
    tests.mkdir()

    # Tier 1: BasePage owns direct assertion `verifyToastSuccess`
    (pages / "BasePage.ts").write_text(
        """
import { Page, expect } from '@playwright/test';

export class BasePage {
  constructor(protected readonly page: Page) {}

  async verifyToastSuccess() {
    await expect(this.page.getByTestId('toast-ok')).toBeVisible();
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Tier 2: MidCheckoutPage extends BasePage and adds `verifyCartTotals`
    (pages / "MidCheckoutPage.ts").write_text(
        """
import { expect } from '@playwright/test';
import { BasePage } from './BasePage';

export class MidCheckoutPage extends BasePage {
  async verifyCartTotals() {
    await expect(this.page.getByTestId('cart-total')).toHaveText('$99.00');
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Tier 3: VipCheckoutPage extends MidCheckoutPage with only interaction methods
    (pages / "VipCheckoutPage.ts").write_text(
        """
import { MidCheckoutPage } from './MidCheckoutPage';

export class VipCheckoutPage extends MidCheckoutPage {
  async applyVipCoupon(code: string) {
    await this.page.getByLabel('Coupon').fill(code);
    await this.page.getByRole('button', { name: 'Apply' }).click();
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Barrel index.ts re-exporting VipCheckoutPage under an alias
    (pages / "index.ts").write_text(
        """
export { BasePage } from './BasePage';
export { MidCheckoutPage } from './MidCheckoutPage';
export { VipCheckoutPage as VipPO } from './VipCheckoutPage';
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Playwright test.extend<Fixtures> binding destructured fixture `vipCheckout` -> VipCheckoutPage
    (fixtures / "test.ts").write_text(
        """
import { test as base } from '@playwright/test';
import { VipPO } from '../pages';

type AppFixtures = {
  vipCheckout: VipPO;
};

export const test = base.extend<AppFixtures>({
  vipCheckout: async ({ page }, use) => {
    await use(new VipPO(page));
  },
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Spec 1: Uses destructured Playwright fixture calling inherited BasePage method
    spec_fixture = tests / "vip_fixture.spec.ts"
    spec_fixture.write_text(
        """
import { test } from '../fixtures/test';

test('TC-VIP-01: inherited assertion via Playwright test.extend fixture', async ({ vipCheckout }) => {
  await vipCheckout.applyVipCoupon('VIP2026');
  await vipCheckout.verifyToastSuccess();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Spec 2: Uses aliased import `import { VipCheckoutPage as VCP }` calling inherited MidCheckoutPage method
    spec_alias = tests / "vip_alias.spec.ts"
    spec_alias.write_text(
        """
import { test } from '@playwright/test';
import { VipCheckoutPage as VCP } from '../pages/VipCheckoutPage';

test('TC-VIP-02: inherited assertion via aliased import', async ({ page }) => {
  const po = new VCP(page);
  await po.applyVipCoupon('VIP2026');
  await po.verifyCartTotals();
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    idx = build_pom_assertion_index(str(tmp_path), prefer_tree_sitter=False)
    assert "verifyToastSuccess" in idx.qualified_class_methods.get("VipCheckoutPage", set())
    assert "verifyCartTotals" in idx.qualified_class_methods.get("VipCheckoutPage", set())
    assert idx.class_parents.get("VipCheckoutPage") == ("MidCheckoutPage",)
    assert idx.class_parents.get("MidCheckoutPage") == ("BasePage",)
    assert idx.fixture_class_bindings.get("vipCheckout") == "VipCheckoutPage"

    res_fix = analyze_script(str(spec_fixture), assertion_map=idx)
    assert res_fix["is_clean"] is True, res_fix["defects"]
    assert res_fix["cross_file_assertions_resolved"] >= 1

    res_alias = analyze_script(str(spec_alias), assertion_map=idx)
    assert res_alias["is_clean"] is True, res_alias["defects"]
    assert res_alias["cross_file_assertions_resolved"] >= 1


# ---------------------------------------------------------------------------
# 2. NEGATIVE: Cyclic inheritance safety & non-asserting colliding fixture
# ---------------------------------------------------------------------------


def test_negative_cyclic_inheritance_and_colliding_non_asserting_fixture(tmp_path: Path) -> None:
    # Direct unit test of cycle safety on resolve_class_inheritance_assertions
    cyclic = resolve_class_inheritance_assertions(
        direct_and_call_methods={"AlphaPage": {"verifyBanner"}},
        class_parents={"AlphaPage": ("BetaPage",), "BetaPage": ("AlphaPage",)},
        max_inheritance_depth=5,
    )
    assert "verifyBanner" in cyclic.get("BetaPage", set())
    assert "verifyBanner" in cyclic.get("AlphaPage", set())

    # Full repo test: cyclic classes + colliding `validate()` on non-asserting StringUtil fixture
    pages = tmp_path / "pages"
    fixtures = tmp_path / "fixtures"
    tests = tmp_path / "tests"
    pages.mkdir()
    fixtures.mkdir()
    tests.mkdir()

    (pages / "CycleA.ts").write_text(
        "import { expect } from '@playwright/test';\nexport class CycleA extends CycleB { async validate() { await expect(this.el).toBeVisible(); } }\n",
        encoding="utf-8",
    )
    (pages / "CycleB.ts").write_text(
        "export class CycleB extends CycleA { async clickBtn() { await this.page.click('#go'); } }\n",
        encoding="utf-8",
    )
    (pages / "StringUtil.ts").write_text(
        "export class StringUtil { validate(input: string) { return input.trim().length > 0; } }\n",
        encoding="utf-8",
    )
    (fixtures / "test.ts").write_text(
        """
import { test as base } from '@playwright/test';
import { StringUtil } from '../pages/StringUtil';

export const test = base.extend<{ stringUtil: StringUtil }>({
  stringUtil: async ({}, use) => {
    await use(new StringUtil());
  },
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    bad_spec = tests / "fake_pass_colliding_fixture.spec.ts"
    bad_spec.write_text(
        """
import { test } from '../fixtures/test';

test('TC-NEG-01: non-asserting stringUtil.validate() must NOT mask fake pass', async ({ page, stringUtil }) => {
  await page.goto('/checkout');
  await page.click('#pay');
  stringUtil.validate('ORD-123');
});
""".strip()
        + "\n",
        encoding="utf-8",
    )

    idx = build_pom_assertion_index(str(tmp_path), prefer_tree_sitter=False)
    assert idx.fixture_class_bindings.get("stringUtil") == "StringUtil"
    assert "validate" in idx.qualified_class_methods.get("CycleB", set())
    assert "validate" not in idx.qualified_class_methods.get("StringUtil", set())

    res = analyze_script(str(bad_spec), assertion_map=idx)
    defect_types = {d["type"] for d in res["defects"]}
    assert "FAKE_PASS_NO_ASSERTION" in defect_types


# ---------------------------------------------------------------------------
# 3. BOUNDARY: Max inheritance depth cap, empty/malformed fixtures & P95 cache latency
# ---------------------------------------------------------------------------


def test_boundary_depth_cap_empty_inputs_and_mtime_cache_latency(tmp_path: Path) -> None:
    # Chain deeper than max_inheritance_depth=2 stops propagating beyond depth 2
    propagated = resolve_class_inheritance_assertions(
        direct_and_call_methods={"L0": {"verifyRoot"}},
        class_parents={"L1": ("L0",), "L2": ("L1",), "L3": ("L2",)},
        max_inheritance_depth=2,
    )
    assert "verifyRoot" in propagated.get("L1", set())
    assert "verifyRoot" in propagated.get("L2", set())
    assert "verifyRoot" not in propagated.get("L3", set())

    # Empty & malformed fixture inputs return empty dict cleanly
    assert extract_playwright_fixture_bindings("", "") == {}
    assert extract_playwright_fixture_bindings("test.extend<{ broken", "test.extend<{ broken") == {}

    # Python multi-level inheritance support
    (tmp_path / "base_page.py").write_text(
        "class BasePyPage:\n    def verify_ready(self):\n        assert self.status == 200\n",
        encoding="utf-8",
    )
    (tmp_path / "child_page.py").write_text(
        "class ChildPyPage(BasePyPage):\n    def click_save(self):\n        return True\n",
        encoding="utf-8",
    )

    idx1 = build_pom_assertion_index(str(tmp_path), prefer_tree_sitter=False)
    assert "verify_ready" in idx1.qualified_class_methods.get("ChildPyPage", set())

    # Second call hits mtime-keyed cache and runs well under 50ms
    t0 = time.perf_counter()
    idx2 = build_pom_assertion_index(str(tmp_path), prefer_tree_sitter=False)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert idx2.qualified_class_methods == idx1.qualified_class_methods
    assert elapsed_ms < 50.0
    assert len(_INDEX_CACHE) >= 1
    clear_index_cache()
    assert len(_INDEX_CACHE) == 0

    # Ignored Python bases (`object`) and duplicate bases are filtered out
    py_parents = _extract_python_class_parents("class A(object, BasePage, BasePage):\n    pass\n")
    assert py_parents == {"A": ("BasePage",)}

    # Barrel export filtering ignores `default`, lowercase helpers, and identity aliases
    aliases = _extract_barrel_export_aliases(
        "export { default as DefaultPage, helperFn as hAlias, SamePage as SamePage, RealPage as RP } from './p';"
    )
    assert aliases == {"RP": "RealPage"}


# ---------------------------------------------------------------------------
# 4. CLI CONTRACT: --root --json exposes class_parents & fixture_class_bindings
# ---------------------------------------------------------------------------


def test_cli_pom_indexer_json_exposes_semantic_graph_fields(tmp_path: Path) -> None:
    (tmp_path / "BasePage.ts").write_text(
        "export class BasePage { async verifyLoaded() { await expect(this.root).toBeVisible(); } }\n",
        encoding="utf-8",
    )
    (tmp_path / "ChildPage.ts").write_text(
        "export class ChildPage extends BasePage { async open() { await this.page.goto('/'); } }\n",
        encoding="utf-8",
    )
    (tmp_path / "fixtures.ts").write_text(
        "export const test = base.extend<{ childPage: ChildPage }>({ childPage: async ({ page }, use) => { await use(new ChildPage(page)); } });\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, "tools/context/pom_assertion_indexer.py", "--root", str(tmp_path), "--no-tree-sitter", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["class_parents"]["ChildPage"] == ["BasePage"]
    assert payload["fixture_class_bindings"]["childPage"] == "ChildPage"
    assert "verifyLoaded" in payload["qualified_class_methods"]["ChildPage"]
