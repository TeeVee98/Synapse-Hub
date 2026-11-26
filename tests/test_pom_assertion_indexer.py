#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""4-scenario test suite for tools/context/pom_assertion_indexer.py."""

from __future__ import annotations

import builtins
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# 1. POSITIVE SCENARIOS
# ---------------------------------------------------------------------------


def test_positive_cross_file_ts_java_python_groovy_pom_assertions(tmp_path: Path) -> None:
    """Transitive assertions across TS, Java, Python, and Groovy Page Objects resolve up to depth 3."""
    from tools.context.pom_assertion_indexer import (
        CrossFileAssertionMapDTO,
        PolyglotAstTreeResultDTO,
        build_pom_assertion_index,
        parse_polyglot_ast_summary,
    )

    pages = tmp_path / "pages"
    pages.mkdir()

    # TypeScript: BasePage -> CheckoutPage -> OrderFlowHelper (depth 2) + action-only clickSubmit
    (pages / "BasePage.ts").write_text(
        """
        import { expect, Page } from '@playwright/test';

        export class BasePage {
            constructor(protected page: Page) {}

            async assertBannerVisible(selector: string) {
                await expect(this.page.locator(selector)).toBeVisible();
            }

            async clickElement(selector: string) {
                await this.page.locator(selector).click();
            }
        }
        """,
        encoding="utf-8",
    )
    (pages / "CheckoutPage.ts").write_text(
        """
        import { BasePage } from './BasePage';

        export class CheckoutPage extends BasePage {
            async verifyOrderConfirmed() {
                await this.assertBannerVisible('#order-confirmed');
            }

            async confirmCheckoutComplete() {
                await this.verifyOrderConfirmed();
            }

            async clickSubmit() {
                await this.clickElement('#submit-btn');
            }
        }
        """,
        encoding="utf-8",
    )

    # Java Page Object
    (pages / "DashboardPage.java").write_text(
        """
        import static org.junit.jupiter.api.Assertions.assertTrue;

        public class DashboardPage {
            public void checkDashboardLoaded() {
                assertTrue(isHeaderVisible());
            }

            public void openSettings() {
                click("#settings");
            }
        }
        """,
        encoding="utf-8",
    )

    # Python Page Object
    (pages / "login_page.py").write_text(
        """
        class LoginPage:
            def ensure_logged_in(self, banner):
                assert banner.is_visible()

            def enter_email(self, email):
                self.email = email
        """,
        encoding="utf-8",
    )

    # Groovy Katalon Keyword
    (pages / "CommonKeywords.groovy").write_text(
        """
        class CommonKeywords {
            def verifyToastMessage(String expected) {
                WebUI.verifyElementText(findTestObject('toast'), expected)
            }

            def navigateHome() {
                WebUI.navigateToUrl('https://example.com')
            }
        }
        """,
        encoding="utf-8",
    )

    dto = build_pom_assertion_index(str(tmp_path), max_depth=3, prefer_tree_sitter=False)
    assert isinstance(dto, CrossFileAssertionMapDTO)
    assert dto.indexed_files_count == 5
    assert dto.max_call_depth == 3
    assert dto.used_tree_sitter is False

    # Direct & transitive assertion methods must be present
    assert "assertBannerVisible" in dto.assertion_methods
    assert "verifyOrderConfirmed" in dto.assertion_methods
    assert "confirmCheckoutComplete" in dto.assertion_methods
    assert "checkDashboardLoaded" in dto.assertion_methods
    assert "ensure_logged_in" in dto.assertion_methods
    assert "verifyToastMessage" in dto.assertion_methods

    # Qualified class mapping must be exact
    assert "verifyOrderConfirmed" in dto.qualified_class_methods.get("CheckoutPage", set())
    assert "confirmCheckoutComplete" in dto.qualified_class_methods.get("CheckoutPage", set())
    assert "checkDashboardLoaded" in dto.qualified_class_methods.get("DashboardPage", set())
    assert "ensure_logged_in" in dto.qualified_class_methods.get("LoginPage", set())
    assert "verifyToastMessage" in dto.qualified_class_methods.get("CommonKeywords", set())

    # Action-only helpers MUST NOT be misclassified as assertion methods
    for action_only in ("clickElement", "clickSubmit", "openSettings", "enter_email", "navigateHome"):
        assert action_only not in dto.assertion_methods

    # Polyglot AST summary check
    py_summary = parse_polyglot_ast_summary(
        str(pages / "login_page.py"),
        (pages / "login_page.py").read_text(encoding="utf-8"),
        prefer_tree_sitter=False,
    )
    assert isinstance(py_summary, PolyglotAstTreeResultDTO)
    assert py_summary.language == "python"
    assert py_summary.backend == "python_ast"
    assert py_summary.syntax_valid is True
    assert py_summary.to_dict()["language"] == "python"

    # Frozen immutability checks on all DTOs
    from dataclasses import FrozenInstanceError
    from tools.context.pom_assertion_indexer import MethodAssertionNode

    with pytest.raises(FrozenInstanceError):
        dto.indexed_files_count = 999  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        py_summary.syntax_valid = False  # type: ignore[misc]
    sample_node = MethodAssertionNode("A.m", "m", "A", "a.ts", True, ())
    with pytest.raises(FrozenInstanceError):
        sample_node.direct_assert = False  # type: ignore[misc]

    # Delimiter balance & JS/TS stdlib summary checks (valid, mismatched, unmatched closer, unclosed opener)
    ts_valid = parse_polyglot_ast_summary(
        "ok.ts",
        "test('a', () => { const arr = [1, 2]; expect(arr).toHaveLength(2); });",
        prefer_tree_sitter=False,
    )
    assert ts_valid.language == "typescript"
    assert ts_valid.backend == "stdlib_state_machine"
    assert ts_valid.test_blocks_count == 1
    assert ts_valid.syntax_valid is True

    ts_mismatch = parse_polyglot_ast_summary("bad1.ts", "function x() { const a = [1); }", prefer_tree_sitter=False)
    assert ts_mismatch.syntax_valid is False

    ts_extra_close = parse_polyglot_ast_summary("bad2.ts", "}", prefer_tree_sitter=False)
    assert ts_extra_close.syntax_valid is False

    ts_unclosed = parse_polyglot_ast_summary("bad3.ts", "function x() {", prefer_tree_sitter=False)
    assert ts_unclosed.syntax_valid is False

    # Python test_count check (both test_ prefix and _test suffix)
    py_tests = parse_polyglot_ast_summary(
        "test_mod.py",
        "def test_one():\n    assert 1 == 2\n\ndef two_test():\n    assert 2 == 3\n",
        prefer_tree_sitter=False,
    )
    assert py_tests.test_blocks_count == 2
    assert py_tests.syntax_valid is True


def test_positive_multiline_expect_and_depth_limit(tmp_path: Path) -> None:
    """Multiline chained expect() counts as a real assertion; depth cap is enforced strictly."""
    from tools.context.pom_assertion_indexer import build_pom_assertion_index

    (tmp_path / "ChainPage.ts").write_text(
        """
        export class ChainPage {
            async level0() {
                await expect(
                    this.page.locator('#total')
                )
                    .toHaveText('$42.00');
            }
            async level1() { await this.level0(); }
            async level2() { await this.level1(); }
            async level3() { await this.level2(); }
            async level4() { await this.level3(); }
        }
        """,
        encoding="utf-8",
    )

    dto = build_pom_assertion_index(str(tmp_path), max_depth=3, prefer_tree_sitter=False)
    assert {"level0", "level1", "level2", "level3"}.issubset(dto.assertion_methods)
    assert "level4" not in dto.assertion_methods


# ---------------------------------------------------------------------------
# 2. NEGATIVE SCENARIOS
# ---------------------------------------------------------------------------


def test_negative_cyclic_pom_graph_terminates_fast_without_recursion_error(tmp_path: Path) -> None:
    """Mutually recursive POM helpers terminate cleanly (< 100ms) and do not fabricate assertions."""
    from tools.context.pom_assertion_indexer import build_pom_assertion_index

    (tmp_path / "CycleA.ts").write_text(
        """
        export class CycleA {
            async helperA() {
                await this.helperB();
            }
            async helperB() {
                await this.helperA();
            }
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "CycleWithRealAssert.ts").write_text(
        """
        export class CycleWithRealAssert {
            async entryCheck() {
                await this.loopCheck();
            }
            async loopCheck() {
                if (false) { await this.entryCheck(); }
                await expect(this.page.locator('#ok')).toBeVisible();
            }
        }
        """,
        encoding="utf-8",
    )

    start = time.perf_counter()
    dto = build_pom_assertion_index(str(tmp_path), max_depth=3, prefer_tree_sitter=False)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert elapsed_ms < 100.0
    assert "helperA" not in dto.assertion_methods
    assert "helperB" not in dto.assertion_methods
    assert "entryCheck" in dto.assertion_methods
    assert "loopCheck" in dto.assertion_methods


def test_negative_tautology_dangling_and_missing_root(tmp_path: Path) -> None:
    """Tautological assertions, dangling expect(), comments, and missing directories are rejected safely."""
    from tools.context.pom_assertion_indexer import build_pom_assertion_index

    (tmp_path / "FakePage.ts").write_text(
        """
        export class FakePage {
            async fakeTautology() {
                expect(true).toBe(true);
            }
            async fakeDangling() {
                expect(this.page.locator('#id'));
            }
            async fakeCommented() {
                // await expect(this.page.locator('#id')).toBeVisible();
                await this.page.click('#btn');
            }
        }
        """,
        encoding="utf-8",
    )

    dto = build_pom_assertion_index(str(tmp_path), max_depth=3, prefer_tree_sitter=False)
    assert "fakeTautology" not in dto.assertion_methods
    assert "fakeDangling" not in dto.assertion_methods
    assert "fakeCommented" not in dto.assertion_methods

    missing_dto = build_pom_assertion_index(str(tmp_path / "does_not_exist"))
    assert missing_dto.indexed_files_count == 0
    assert missing_dto.assertion_methods == set()
    assert missing_dto.qualified_class_methods == {}


# ---------------------------------------------------------------------------
# 3. BOUNDARY & CONCURRENCY SCENARIOS
# ---------------------------------------------------------------------------


def test_boundary_missing_tree_sitter_pack_fallback_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When tree_sitter_language_pack is absent, loader returns None and stdlib fallback yields exact parity."""
    from tools.context import pom_assertion_indexer as idx_mod

    (tmp_path / "CartPage.ts").write_text(
        """
        export class CartPage {
            async verifyItemCount(n: number) {
                await expect(this.page.locator('.item')).toHaveCount(n);
            }
            async addItem() {
                await this.page.click('.add');
            }
        }
        """,
        encoding="utf-8",
    )

    real_import = builtins.__import__

    def _blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("tree_sitter"):
            raise ImportError("Simulated missing tree_sitter_language_pack")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    idx_mod.clear_parser_cache()
    assert idx_mod._PARSER_CACHE == {}

    assert idx_mod.load_optional_tree_sitter_parser("") is None
    assert idx_mod.load_optional_tree_sitter_parser("typescript") is None
    assert "typescript" in idx_mod._PARSER_CACHE
    assert idx_mod.load_optional_tree_sitter_parser("typescript") is None
    assert idx_mod.load_optional_tree_sitter_parser("unknown_lang") is None

    # Verify clear_parser_cache actually evicts cached entries
    idx_mod._PARSER_CACHE["typescript"] = "SENTINEL_PARSER"
    assert idx_mod.load_optional_tree_sitter_parser("typescript") == "SENTINEL_PARSER"
    idx_mod.clear_parser_cache()
    assert idx_mod.load_optional_tree_sitter_parser("typescript") is None

    # Verify fake tree-sitter parser integration path (valid and syntax-error root node)
    class _FakeRoot:
        def __init__(self, has_error: bool) -> None:
            self.has_error = has_error

    class _FakeTree:
        def __init__(self, has_error: bool) -> None:
            self.root_node = _FakeRoot(has_error)

    class _FakeParser:
        def __init__(self, has_error: bool = False) -> None:
            self._err = has_error

        def parse(self, data: bytes) -> _FakeTree:
            return _FakeTree(self._err)

    idx_mod._PARSER_CACHE["typescript"] = _FakeParser(has_error=False)
    ts_ast_ok = idx_mod.parse_polyglot_ast_summary("sample.ts", "test('ok', () => {});", prefer_tree_sitter=True)
    assert ts_ast_ok.backend == "tree_sitter"
    assert ts_ast_ok.syntax_valid is True
    assert ts_ast_ok.test_blocks_count == 1

    idx_mod._PARSER_CACHE["typescript"] = _FakeParser(has_error=True)
    ts_ast_bad = idx_mod.parse_polyglot_ast_summary("sample.ts", "function (", prefer_tree_sitter=True)
    assert ts_ast_bad.backend == "tree_sitter"
    assert ts_ast_bad.syntax_valid is False

    idx_mod.clear_parser_cache()

    dto_prefer = idx_mod.build_pom_assertion_index(str(tmp_path), prefer_tree_sitter=True)
    dto_stdlib = idx_mod.build_pom_assertion_index(str(tmp_path), prefer_tree_sitter=False)
    assert dto_prefer.used_tree_sitter is False
    assert dto_prefer.assertion_methods == dto_stdlib.assertion_methods == {"verifyItemCount"}
    assert dto_prefer.qualified_class_methods == dto_stdlib.qualified_class_methods


def test_boundary_empty_dir_zero_byte_files_and_concurrency(tmp_path: Path) -> None:
    """Empty repos, 0-byte files, syntax-broken Python, and concurrent indexing stay safe & deterministic."""
    from tools.context.pom_assertion_indexer import (
        build_pom_assertion_index,
        parse_polyglot_ast_summary,
    )

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    empty_dto = build_pom_assertion_index(str(empty_dir))
    assert empty_dto.indexed_files_count == 0
    assert empty_dto.assertion_methods == set()

    mixed_dir = tmp_path / "mixed"
    mixed_dir.mkdir()
    (mixed_dir / "zero.ts").write_text("", encoding="utf-8")
    (mixed_dir / "broken.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
    (mixed_dir / "good.py").write_text(
        "class OkPage:\n    def check_ok(self, x):\n        assert x == 1\n",
        encoding="utf-8",
    )

    broken_summary = parse_polyglot_ast_summary(
        str(mixed_dir / "broken.py"), "def broken(:\n    pass\n", prefer_tree_sitter=False
    )
    assert broken_summary.syntax_valid is False

    # Concurrency: 4 parallel index builds must yield identical deterministic results
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: build_pom_assertion_index(str(mixed_dir), prefer_tree_sitter=False), range(4))
        )
    for res in results:
        assert res.assertion_methods == {"check_ok"}
        assert res.qualified_class_methods == {"OkPage": {"check_ok"}}


# ---------------------------------------------------------------------------
# 4. CLI FLAGS & JSON CONTRACT SCENARIOS
# ---------------------------------------------------------------------------


def test_cli_flags_json_and_no_tree_sitter(tmp_path: Path) -> None:
    """CLI emits deterministic JSON contract with --root, --max-depth, --no-tree-sitter, --json."""
    (tmp_path / "OrderPage.ts").write_text(
        """
        export class OrderPage {
            async verifyReceipt() {
                await expect(this.page.locator('#receipt')).toBeVisible();
            }
        }
        """,
        encoding="utf-8",
    )

    script = REPO_ROOT / "tools" / "context" / "pom_assertion_indexer.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(tmp_path),
            "--max-depth",
            "3",
            "--no-tree-sitter",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    data = json.loads(proc.stdout)
    assert data["indexed_files_count"] == 1
    assert data["max_call_depth"] == 3
    assert data["used_tree_sitter"] is False
    assert "verifyReceipt" in data["assertion_methods"]
    assert data["qualified_class_methods"]["OrderPage"] == ["verifyReceipt"]
