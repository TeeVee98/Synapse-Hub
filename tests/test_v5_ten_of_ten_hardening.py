#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
4-Scenario TDD Hardening Suite for Synapse Hub 10/10 Upgrade:
  1. Compiler-grade Tree-Sitter CST/AST node walking (methods, classes, calls, test blocks)
  2. Receiver-qualified POM assertion resolution (preventing unqualified method collisions)
  3. Zero-disk-I/O in-memory linting & LSP RAM diagnostics preserving directory role context
  4. External wild-OSS repository FPR benchmark (--external-repo) & PyPI OIDC CI / 11-Gate hygiene
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class FakeTSNode:
    """Deterministic Tree-Sitter-compatible CST node for verifying real AST traversal."""

    type: str
    start_byte: int
    end_byte: int
    start_point: tuple[int, int] = (0, 0)
    end_point: tuple[int, int] = (0, 0)
    children: List["FakeTSNode"] = field(default_factory=list)
    fields: dict[str, "FakeTSNode"] = field(default_factory=dict)
    has_error: bool = False

    @property
    def is_named(self) -> bool:
        return True

    def child_by_field_name(self, name: str) -> Optional["FakeTSNode"]:
        return self.fields.get(name)


@dataclass
class FakeTSTree:
    root_node: FakeTSNode


# ---------------------------------------------------------------------------
# 1. POSITIVE: Real Tree-Sitter AST Node Traversal (Not Surface Parse-and-Discard)
# ---------------------------------------------------------------------------


def test_positive_real_tree_sitter_ast_node_walker_extracts_methods_and_blocks() -> None:
    """Tree-Sitter walker must traverse real AST nodes (class_declaration, method_definition, call_expression)."""
    from tools.context.pom_assertion_indexer import extract_tree_sitter_method_nodes
    from tools.lint.infer_linter import extract_tree_sitter_test_spans

    src = (
        "export class PaymentPage {\n"
        "  async verifyReceiptShown() {\n"
        "    await expect(this.page.locator('#rcpt')).toBeVisible();\n"
        "  }\n"
        "  async clickPay() {\n"
        "    await this.helperClick();\n"
        "  }\n"
        "}\n"
    )
    src_bytes = src.encode("utf-8")

    def _span(substr: str) -> tuple[int, int]:
        idx = src.index(substr)
        b_start = len(src[:idx].encode("utf-8"))
        b_end = b_start + len(substr.encode("utf-8"))
        return b_start, b_end

    cls_name_b = _span("PaymentPage")
    cls_name_node = FakeTSNode("type_identifier", cls_name_b[0], cls_name_b[1])

    m1_full = (
        "async verifyReceiptShown() {\n"
        "    await expect(this.page.locator('#rcpt')).toBeVisible();\n"
        "  }"
    )
    m1_b = _span(m1_full)
    m1_name_b = _span("verifyReceiptShown")
    m1_body_b = _span(
        "{\n    await expect(this.page.locator('#rcpt')).toBeVisible();\n  }"
    )
    m1_node = FakeTSNode(
        "method_definition",
        m1_b[0],
        m1_b[1],
        children=[],
        fields={
            "name": FakeTSNode("property_identifier", m1_name_b[0], m1_name_b[1]),
            "body": FakeTSNode("statement_block", m1_body_b[0], m1_body_b[1]),
        },
    )

    m2_full = "async clickPay() {\n    await this.helperClick();\n  }"
    m2_b = _span(m2_full)
    m2_name_b = _span("clickPay")
    m2_body_b = _span("{\n    await this.helperClick();\n  }")
    call_b = _span("this.helperClick()")
    callee_b = _span("helperClick")
    call_node = FakeTSNode(
        "call_expression",
        call_b[0],
        call_b[1],
        fields={
            "function": FakeTSNode(
                "member_expression",
                _span("this.helperClick")[0],
                _span("this.helperClick")[1],
                fields={"property": FakeTSNode("property_identifier", callee_b[0], callee_b[1])},
            )
        },
    )
    m2_body_node = FakeTSNode("statement_block", m2_body_b[0], m2_body_b[1], children=[call_node])
    m2_node = FakeTSNode(
        "method_definition",
        m2_b[0],
        m2_b[1],
        children=[m2_body_node],
        fields={
            "name": FakeTSNode("property_identifier", m2_name_b[0], m2_name_b[1]),
            "body": m2_body_node,
        },
    )

    cls_body_b = _span(src[src.index("{") :])
    cls_body = FakeTSNode("class_body", cls_body_b[0], cls_body_b[1], children=[m1_node, m2_node])
    cls_b = _span(src.strip())
    cls_node = FakeTSNode(
        "class_declaration",
        cls_b[0],
        cls_b[1],
        children=[cls_name_node, cls_body],
        fields={"name": cls_name_node, "body": cls_body},
    )
    root = FakeTSNode("program", 0, len(src_bytes), children=[cls_node])

    nodes = extract_tree_sitter_method_nodes(root, src_bytes, "pages/PaymentPage.ts", "typescript")
    by_key = {n.key: n for n in nodes}
    assert "PaymentPage.verifyReceiptShown" in by_key
    assert by_key["PaymentPage.verifyReceiptShown"].direct_assert is True
    assert "PaymentPage.clickPay" in by_key
    assert by_key["PaymentPage.clickPay"].direct_assert is False
    assert "helperClick" in by_key["PaymentPage.clickPay"].calls

    # Test block span extraction from Tree-Sitter call_expression nodes
    test_src = (
        "test('first case', async ({ page }) => {\n  await page.click('#a');\n});\n"
        "test('second case', async ({ page }) => {\n  await expect(page.locator('#b')).toBeVisible();\n});\n"
    )
    test_bytes = test_src.encode("utf-8")
    t1_end = test_src.index("});\n") + 3
    t2_start = test_src.index("test('second")
    t1_fn = FakeTSNode("identifier", 0, 4, start_point=(0, 0), end_point=(0, 4))
    t2_fn = FakeTSNode("identifier", t2_start, t2_start + 4, start_point=(3, 0), end_point=(3, 4))
    t1_call = FakeTSNode(
        "call_expression",
        0,
        t1_end,
        start_point=(0, 0),
        end_point=(2, 2),
        fields={"function": t1_fn},
    )
    t2_call = FakeTSNode(
        "call_expression",
        t2_start,
        len(test_bytes) - 1,
        start_point=(3, 0),
        end_point=(5, 2),
        fields={"function": t2_fn},
    )
    test_tree = FakeTSTree(FakeTSNode("program", 0, len(test_bytes), children=[t1_call, t2_call]))
    spans = extract_tree_sitter_test_spans(test_tree, test_bytes)
    assert len(spans) == 2
    assert spans[0][0] == 1
    assert "click('#a')" in spans[0][1]
    assert spans[1][0] == 4

    # Boundary & error-node guards for parse_with_tree_sitter and extract_tree_sitter_test_spans
    from types import SimpleNamespace
    from tools.lint import infer_linter

    assert extract_tree_sitter_test_spans(None, b"") == []
    assert extract_tree_sitter_test_spans(SimpleNamespace(root_node=None), b"abc") == []
    err_tree = FakeTSTree(FakeTSNode("program", 0, len(test_bytes), children=[t1_call], has_error=True))
    assert extract_tree_sitter_test_spans(err_tree, test_bytes) == []
    minimal_node = SimpleNamespace(type="program", start_byte=0, end_byte=len(test_bytes), children=[t1_call])
    assert len(extract_tree_sitter_test_spans(SimpleNamespace(root_node=minimal_node), test_bytes)) == 1

    orig_loader = infer_linter.load_optional_tree_sitter_parser
    try:
        infer_linter.load_optional_tree_sitter_parser = None
        assert infer_linter.parse_with_tree_sitter("sample.ts", "const x = 1;") is None
        infer_linter.load_optional_tree_sitter_parser = lambda _ext: None
        assert infer_linter.parse_with_tree_sitter("sample.ts", "const x = 1;") is None
        infer_linter.load_optional_tree_sitter_parser = lambda _ext: SimpleNamespace(
            parse=lambda b: FakeTSTree(FakeTSNode("program", 0, len(b)))
        )
        parsed_tree = infer_linter.parse_with_tree_sitter("sample.ts", "const x = 1;")
        assert parsed_tree is not None and parsed_tree.root_node.end_byte == 12
    finally:
        infer_linter.load_optional_tree_sitter_parser = orig_loader

    # Direct unit verification of receiver bindings & stem matching across TS, Java, Python
    bindings = infer_linter._extract_receiver_class_bindings(
        "function f(fx: FixturePage) {\n"
        "  const jsP = new CheckoutPage(page);\n"
        "  DashboardPage javaP = new DashboardPage();\n"
        "  py_p = OrderPage(driver)\n"
        "}"
    )
    assert bindings == {
        "fx": "FixturePage",
        "jsP": "CheckoutPage",
        "javaP": "DashboardPage",
        "py_p": "OrderPage",
    }
    assert infer_linter._extract_receiver_class_bindings("") == {}
    assert infer_linter._receiver_matches_class_stem("orderPage", "OrderPage") is True
    assert infer_linter._receiver_matches_class_stem("my_order_page", "OrderPage") is True
    assert infer_linter._receiver_matches_class_stem("stringUtil", "OrderPage") is False
    assert infer_linter._receiver_matches_class_stem("orderPage", "") is False
    assert infer_linter._receiver_matches_class_stem("", "OrderPage") is False


# ---------------------------------------------------------------------------
# 2. NEGATIVE: Receiver-Qualified POM Disambiguation (Prevent Collision Bypass)
# ---------------------------------------------------------------------------


def test_negative_unqualified_generic_method_collision_caught_as_fake_pass(tmp_path: Path) -> None:
    """Calling stringUtil.validate() must NOT inherit CheckoutPage.validate()'s assertion status."""
    from tools.context.pom_assertion_indexer import build_pom_assertion_index
    from tools.lint import infer_linter

    pages = tmp_path / "pages"
    helpers = tmp_path / "helpers"
    tests_dir = tmp_path / "tests"
    pages.mkdir()
    helpers.mkdir()
    tests_dir.mkdir()

    (pages / "CheckoutPage.ts").write_text(
        "import { expect, Page } from '@playwright/test';\n"
        "export class CheckoutPage {\n"
        "  constructor(private page: Page) {}\n"
        "  async validate() {\n"
        "    await expect(this.page.locator('#receipt')).toBeVisible();\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (helpers / "StringUtil.ts").write_text(
        "export class StringUtil {\n"
        "  validate(raw: string): boolean {\n"
        "    return raw.trim().length > 0;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    # Genuine clean test: binds CheckoutPage and calls p.validate()
    clean_test = tests_dir / "clean_checkout.spec.ts"
    clean_test.write_text(
        "import { test } from '@playwright/test';\n"
        "import { CheckoutPage } from '../pages/CheckoutPage';\n"
        "test('real pom validate', async ({ page }) => {\n"
        "  const p = new CheckoutPage(page);\n"
        "  await page.click('#buy');\n"
        "  await p.validate();\n"
        "});\n",
        encoding="utf-8",
    )

    # Collision trap: binds StringUtil (not CheckoutPage!) and calls util.validate() with 0 real UI assertions
    collision_test = tests_dir / "fake_pass_collision.spec.ts"
    collision_test.write_text(
        "import { test } from '@playwright/test';\n"
        "import { StringUtil } from '../helpers/StringUtil';\n"
        "test('collision fake pass', async ({ page }) => {\n"
        "  const util = new StringUtil();\n"
        "  util.validate('order-123');\n"
        "  await page.click('#buy');\n"
        "});\n",
        encoding="utf-8",
    )

    assertion_map = build_pom_assertion_index(str(tmp_path), max_depth=3, prefer_tree_sitter=False)
    res_clean = infer_linter.analyze_script(str(clean_test), assertion_map=assertion_map)
    assert res_clean["is_clean"] is True, f"Expected clean POM test, got: {res_clean['defects']}"

    res_collision = infer_linter.analyze_script(str(collision_test), assertion_map=assertion_map)
    defect_types = {d["type"] for d in res_collision["defects"]}
    assert "FAKE_PASS_NO_ASSERTION" in defect_types, (
        f"Unqualified method collision bypassed fake-pass check! Got: {res_collision}"
    )


# ---------------------------------------------------------------------------
# 3. BOUNDARY & PERFORMANCE: Zero-Disk-I/O In-Memory Linting & LSP Role Context
# ---------------------------------------------------------------------------


def test_boundary_in_memory_lint_and_lsp_zero_tempfiles_preserve_tests_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LSP didOpen/didChange must lint 100% in RAM without tempfile.mkdtemp and preserve tests/ role."""
    from tools.lint import infer_linter
    from tools.mcp.qa_lsp_server import QALanguageServer

    # File path inside tests/e2e/ WITHOUT .spec/.test suffix, and NOT written to disk!
    virtual_test_path = tmp_path / "tests" / "e2e" / "checkout_flow.ts"
    in_memory_code = (
        "import { test } from '@playwright/test';\n"
        "test('missing assert in unsaved buffer', async ({ page }) => {\n"
        "  await page.click('#submit');\n"
        "});\n"
    )

    # 1. Direct in-memory analyze_script without physical file on disk
    assert not virtual_test_path.exists()
    direct_report = infer_linter.analyze_script(
        str(virtual_test_path),
        source_content=in_memory_code,
    )
    assert direct_report["role"] == "TEST_SCRIPT"
    assert any(d["type"] == "FAKE_PASS_NO_ASSERTION" for d in direct_report["defects"])

    # 2. Forbid tempfile.mkdtemp during LSP didOpen / didChange
    def _forbid_mkdtemp(*args: object, **kwargs: object) -> str:
        raise RuntimeError("Disk tempfile.mkdtemp is forbidden during in-memory LSP linting!")

    monkeypatch.setattr(tempfile, "mkdtemp", _forbid_mkdtemp)

    server = QALanguageServer(workspace_root=str(tmp_path))
    _, notifs = server.handle_message(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": virtual_test_path.as_uri(),
                    "languageId": "typescript",
                    "version": 1,
                    "text": in_memory_code,
                }
            },
        }
    )
    assert len(notifs) == 1
    codes = {d["code"] for d in notifs[0]["params"]["diagnostics"]}
    assert "FAKE_PASS_NO_ASSERTION" in codes


# ---------------------------------------------------------------------------
# 4. CLI, EXTERNAL OSS BENCHMARK & RELEASE HYGIENE
# ---------------------------------------------------------------------------


def test_cli_external_repo_benchmark_and_release_hygiene(tmp_path: Path) -> None:
    """Verifies --external-repo benchmark mode, PyPI OIDC workflow, 11-Gate sync, and gitignore hygiene."""
    from benchmarks.real_world_fpr_runner import run_fpr_benchmark
    from tools.core import cli as core_cli

    # Create a realistic external Playwright repository structure outside Synapse Hub
    ext_repo = tmp_path / "external_oss_playwright_app"
    (ext_repo / "pages").mkdir(parents=True)
    (ext_repo / "tests").mkdir(parents=True)
    (ext_repo / "pages" / "AccountPage.ts").write_text(
        "import { expect, Page } from '@playwright/test';\n"
        "export class AccountPage {\n"
        "  constructor(private page: Page) {}\n"
        "  async assertProfileSaved() {\n"
        "    await expect(this.page.locator('#toast')).toHaveText('Saved');\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (ext_repo / "tests" / "profile.spec.ts").write_text(
        "import { test } from '@playwright/test';\n"
        "import { AccountPage } from '../pages/AccountPage';\n"
        "test('saves profile', async ({ page }) => {\n"
        "  const accountPage = new AccountPage(page);\n"
        "  await page.fill('#name', 'Ada');\n"
        "  await accountPage.assertProfileSaved();\n"
        "});\n",
        encoding="utf-8",
    )

    receipt = run_fpr_benchmark(
        str(REPO_ROOT),
        max_fpr_pct=5.0,
        max_p95_ms=50.0,
        include_adversarial_corpus=False,
        external_repo_paths=[str(ext_repo)],
    )
    assert receipt.passed is True
    assert receipt.false_positives == 0
    assert receipt.external_repos_evaluated == 1

    # CLI --external-repo fail-closed check on nonexistent directory
    script = REPO_ROOT / "benchmarks" / "real_world_fpr_runner.py"
    bad_proc = subprocess.run(
        [sys.executable, str(script), "--external-repo", str(tmp_path / "missing_oss_repo"), "--json"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert bad_proc.returncode != 0

    # Verify PyPI OIDC Trusted Publishing workflow exists and enforces 11 Quality Gates
    pypi_wf = REPO_ROOT / ".github" / "workflows" / "publish_pypi.yml"
    assert pypi_wf.is_file(), "Missing .github/workflows/publish_pypi.yml"
    wf_text = pypi_wf.read_text(encoding="utf-8")
    assert "id-token: write" in wf_text
    assert "pypa/gh-action-pypi-publish@" in wf_text
    assert "verify_all.py" in wf_text

    # Verify 11 Quality Gates parity in cli.cmd_release docstring and PROJECT_STATE.md
    assert "11 Quality Gates" in (core_cli.cmd_release.__doc__ or "")
    proj_state = (REPO_ROOT / "PROJECT_STATE.md").read_text(encoding="utf-8")
    assert "11 Quality Gates" in proj_state

    # Verify decisions.tsv is ignored by .gitignore
    gi_text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "decisions.tsv" in gi_text
