# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/swe_qa_aci.py (SWE-agent QA Agent-Computer Interface)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from swe_qa_aci import SweQaAci


@pytest.fixture
def temp_repo():
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_view_window_bounded(temp_repo):
    sample = os.path.join(temp_repo, "sample.ts")
    lines = [f"const line_{i} = {i};" for i in range(1, 101)]
    with open(sample, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    aci = SweQaAci(repo_root=temp_repo)
    res = aci.view_window("sample.ts", start_line=20, window_size=30)

    assert res["status"] == "PASS"
    assert res["start_line"] == 20
    assert res["end_line"] == 49
    assert res["window_size"] == 30
    assert res["total_lines"] == 100
    assert "  20 | const line_20 = 20;" in res["content"]
    assert "  49 | const line_49 = 49;" in res["content"]


def test_view_window_file_not_found():
    aci = SweQaAci()
    res = aci.view_window("non_existent_file.ts")
    assert res["status"] == "FAIL"
    assert "not found" in res["error"].lower()


def test_surgical_edit_success(temp_repo):
    sample = os.path.join(temp_repo, "LoginPage.ts")
    with open(sample, "w", encoding="utf-8") as f:
        f.write("\n".join([
            "export class LoginPage {",
            "  async login() {",
            "    await this.page.click('#old-btn');",
            "  }",
            "}"
        ]))

    aci = SweQaAci(repo_root=temp_repo)
    res = aci.surgical_edit(
        file_path="LoginPage.ts",
        target_chunk="await this.page.click('#old-btn');",
        replacement_chunk="await this.clickSafe(this.loginButton);",
        validate_syntax=True,
        enforce_clean_pom=True
    )

    assert res["status"] == "PASS"
    assert res["ast_validation"] == "SYNTAX_VALID"
    assert res["utf8_nobom_verified"] is True
    assert res["lines_replaced"]["start"] == 3
    assert res["lines_replaced"]["end"] == 3

    with open(sample, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert "await this.clickSafe(this.loginButton);" in new_content
    assert "#old-btn" not in new_content


def test_surgical_edit_syntax_rejection(temp_repo):
    sample = os.path.join(temp_repo, "util.py")
    with open(sample, "w", encoding="utf-8") as f:
        f.write("def calculate(x):\n    return x + 1\n")

    aci = SweQaAci(repo_root=temp_repo)
    res = aci.surgical_edit(
        file_path="util.py",
        target_chunk="return x + 1",
        replacement_chunk="return (x +",  # syntax error
        validate_syntax=True
    )

    assert res["status"] == "FAIL"
    assert res["ast_validation"] == "SYNTAX_INVALID"

    # Verify file was NOT modified
    with open(sample, "r", encoding="utf-8") as f:
        content = f.read()
    assert "return x + 1" in content


def test_surgical_edit_clean_pom_rejection(temp_repo):
    test_script = os.path.join(temp_repo, "tests", "checkout.spec.ts")
    os.makedirs(os.path.dirname(test_script), exist_ok=True)
    with open(test_script, "w", encoding="utf-8") as f:
        f.write("test('checkout', async () => {\n  await page.click('#pay');\n});\n")

    aci = SweQaAci(repo_root=temp_repo)
    res = aci.surgical_edit(
        file_path="tests/checkout.spec.ts",
        target_chunk="await page.click('#pay');",
        replacement_chunk="await page.locator('//button[@id=\"pay\"]').click();",  # raw xpath in test script
        enforce_clean_pom=True
    )

    assert res["status"] == "FAIL"
    assert "Clean POM violation" in res["error"]


def test_run_distilled_command():
    aci = SweQaAci()
    res = aci.run_distilled(command=[sys.executable, "-c", "for i in range(100): print(f'line {i}')"], max_lines=20)
    assert res["status"] == "PASS"
    assert res["total_lines"] == 100
    assert res["distilled_lines"] == 20
    assert "TRUNCATED" in res["distilled_output"]
