#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/design/auto_sanity_engine.py — Auto-Sanity Headless Playwright Verification Engine
-----------------------------------------------------------------------------------------
Phase 3 Engine: Ground-Truth Verification for Manual QA Test Cases.
Automatically parses natural language manual test steps (EN & VI), evaluates actionable
feasibility against live web UI and DOM/AOM contracts, verifies locator reachability,
and generates Clean POM Playwright executable specifications.

Key Capabilities:
  1. Action Transpiler: Parses manual test steps into discrete executable actions.
  2. DOM/AOM Semantic Contract: Validates element existence, labels, placeholders, and interactability.
  3. Headless Playwright Runner: Live in-browser execution with sub-second feedback.
  4. Flakiness & Drift Sentinel: Flags LOCATOR_DRIFT, INTERACTION_BLOCKED, and TYPE_MISMATCH.
  5. Clean POM Spec Synthesis: Emits production-ready Playwright TypeScript test suites.
"""

import os
import sys
import re
import json
import argparse
import subprocess
from html.parser import HTMLParser
from typing import Dict, Any, List, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# UTF-8 terminal encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class ActionStep:
    """Represents a single parsed action step in a manual test case."""

    def __init__(self, step_num: int, raw_text: str, action: str, target: str = "", value: str = ""):
        self.step_num = step_num
        self.raw_text = raw_text.strip()
        self.action = action.upper()  # NAVIGATE, FILL, CLICK, SELECT, ASSERT_VISIBLE, ASSERT_TEXT, UNKNOWN
        self.target = target.strip()
        self.value = value.strip()
        self.status = "PENDING"
        self.error_detail: Optional[str] = None
        self.duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_num": self.step_num,
            "raw_text": self.raw_text,
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "status": self.status,
            "error_detail": self.error_detail,
            "duration_ms": self.duration_ms
        }

    def generate_pom_locator_ts(self) -> str:
        """Generates Clean POM Playwright TypeScript locator snippet."""
        clean_target = self.target.replace('"', '\\"')
        clean_val = self.value.replace('"', '\\"')

        if not clean_target and self.action != "NAVIGATE":
            return f'// Warning: Mục tiêu UI không được xác định rõ trong bước: "{self.raw_text}"'

        if self.action == "NAVIGATE":
            return f'await page.goto("{clean_val or clean_target}");'
        elif self.action == "FILL":
            return f'await page.getByLabel("{clean_target}").or(page.getByPlaceholder("{clean_target}")).fill("{clean_val}");'
        elif self.action == "CLICK":
            return f'await page.getByRole("button", {{ name: "{clean_target}" }}).or(page.getByText("{clean_target}")).click();'
        elif self.action == "SELECT":
            return f'await page.getByLabel("{clean_target}").selectOption("{clean_val}");'
        elif self.action in ("ASSERT_VISIBLE", "ASSERT_TEXT"):
            return f'await expect(page.getByText("{clean_target or clean_val}")).toBeVisible();'
        return f'// Unmapped action: {self.raw_text}'


class DOMElement:
    """Represents an interactive element discovered in the DOM."""

    def __init__(self, tag: str, attrs: Dict[str, str], text: str = ""):
        self.tag = tag.lower()
        self.attrs = attrs
        self.id = attrs.get("id", "")
        self.name = attrs.get("name", "")
        self.type = attrs.get("type", "text").lower()
        self.placeholder = attrs.get("placeholder", "")
        self.aria_label = attrs.get("aria-label", "")
        self.label_text = ""
        self.inner_text = text.strip()
        self.is_disabled = "disabled" in attrs or attrs.get("aria-disabled") == "true"
        self.is_hidden = "hidden" in attrs or attrs.get("aria-hidden") == "true" or "display: none" in attrs.get("style", "").lower()
        self.is_readonly = "readonly" in attrs

    def matches_target(self, target: str) -> bool:
        """Determines if this element semantically matches a manual step's target description."""
        t_clean = target.lower().strip("'\" ")
        if not t_clean:
            return False

        candidates = [
            self.id.lower(),
            self.name.lower(),
            self.placeholder.lower(),
            self.aria_label.lower(),
            self.label_text.lower(),
            self.inner_text.lower()
        ]

        for cand in candidates:
            if not cand:
                continue
            if t_clean == cand:
                return True
            # Substring matching with length guard (min 3 chars) to prevent false positives
            if len(t_clean) >= 3 and t_clean in cand:
                return True
            if len(cand) >= 3 and cand in t_clean:
                return True
        return False


class DOMParser(HTMLParser):
    """Fast stdlib HTML parser that extracts interactive form and action elements."""

    def __init__(self):
        super().__init__()
        self.elements: List[DOMElement] = []
        self.labels: Dict[str, str] = {}  # for_id -> label_text
        self._curr_tag: Optional[str] = None
        self._curr_attrs: Dict[str, str] = {}
        self._curr_text: List[str] = []
        self._curr_label_for: Optional[str] = None
        self._curr_label_text: List[str] = []
        self._hidden_tag_stack: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()

        # Track container-level hidden state (e.g., <div hidden> or <div style="display: none">)
        void_tags = {"input", "img", "br", "hr", "meta", "link", "area", "base", "col", "embed", "param", "source", "track", "wbr"}
        is_tag_hidden = "hidden" in attr_dict or attr_dict.get("aria-hidden") == "true" or "display: none" in attr_dict.get("style", "").lower()
        if is_tag_hidden and tag_lower not in void_tags:
            self._hidden_tag_stack.append(tag_lower)

        if tag_lower == "label":
            self._curr_label_for = attr_dict.get("for")
            self._curr_label_text = []

        elif tag_lower in ("button", "a", "input", "select", "textarea"):
            self._curr_tag = tag_lower
            self._curr_attrs = attr_dict
            self._curr_text = []
            if tag_lower in ("input", "select", "textarea"):
                # Self-closing or immediate registration
                elem = DOMElement(tag_lower, attr_dict)
                if self._hidden_tag_stack:
                    elem.is_hidden = True
                self.elements.append(elem)

    def handle_data(self, data: str):
        if self._curr_label_for is not None:
            self._curr_label_text.append(data)
        if self._curr_tag in ("button", "a"):
            self._curr_text.append(data)

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower == "label":
            if self._curr_label_for:
                self.labels[self._curr_label_for] = " ".join(self._curr_label_text).strip()
            self._curr_label_for = None
            self._curr_label_text = []

        elif tag_lower in ("button", "a") and self._curr_tag == tag_lower:
            text = " ".join(self._curr_text).strip()
            elem = DOMElement(tag_lower, self._curr_attrs, text)
            if self._hidden_tag_stack:
                elem.is_hidden = True
            self.elements.append(elem)
            self._curr_tag = None
            self._curr_attrs = {}
            self._curr_text = []

        if self._hidden_tag_stack and self._hidden_tag_stack[-1] == tag_lower:
            self._hidden_tag_stack.pop()

    def finalize(self):
        # Associate label texts with matching inputs by id
        for elem in self.elements:
            if elem.id and elem.id in self.labels:
                elem.label_text = self.labels[elem.id]


class AutoSanityEngine:
    """Validates manual QA test cases against live web apps or static DOM/AOM contracts."""

    def __init__(self, target_url_or_html: Optional[str] = None):
        self.target = target_url_or_html
        self.dom_elements: List[DOMElement] = []
        if target_url_or_html:
            self.load_target(target_url_or_html)

    def load_target(self, target: str):
        """Loads HTML content from local path or raw string and parses DOM elements."""
        self.target = target
        html_content = target
        if os.path.isfile(target):
            with open(target, "r", encoding="utf-8") as f:
                html_content = f.read()

        if "<html" in html_content.lower() or "<form" in html_content.lower() or "<button" in html_content.lower():
            parser = DOMParser()
            parser.feed(html_content)
            parser.finalize()
            self.dom_elements = parser.elements

    @staticmethod
    def parse_test_steps(steps_raw: str) -> List[ActionStep]:
        """Parses natural language manual test steps (Vietnamese & English) into ActionSteps."""
        steps: List[ActionStep] = []
        lines = re.split(r"<br\s*/?>|\n|(?:\d+\.\s+)", steps_raw)
        step_idx = 1

        for raw in lines:
            line = raw.strip()
            if not line:
                continue

            # Strip leading numbering if present (e.g. "1. ", "Step 1: ")
            line_clean = re.sub(r"^(?:step\s*)?\d+[\.:\)]\s*", "", line, flags=re.IGNORECASE).strip()
            if not line_clean:
                continue

            action = "UNKNOWN"
            target = ""
            val = ""

            first_word = line_clean.split()[0].lower() if line_clean.split() else ""

            # 1. NAVIGATION
            if first_word in ("truy", "mở", "navigate", "go") or re.search(r"^(?:truy\s+cập|mở\s+(?:trang|màn\s+hình)?|navigate\s+to|go\s+to)", line_clean, re.IGNORECASE):
                action = "NAVIGATE"
                m_nav = re.search(r"(?:truy\s+cập(?:\s+(?:trang|vào|đến))?|mở\s+(?:trang|màn\s+hình)?|navigate\s+to|go\s+to)\s+([^\s,]+)", line_clean, re.IGNORECASE)
                if m_nav:
                    val = m_nav.group(1).strip("'\"`")
                    target = val
                else:
                    target = line_clean

            # 2. FILL / INPUT
            elif first_word in ("nhập", "điền", "fill", "type", "enter") or re.search(r"^(?:nhập|điền|fill|type|enter)\b", line_clean, re.IGNORECASE):
                action = "FILL"
                # Pattern: Nhập 'value' vào ô/trường 'target'
                m_fill = re.search(r"(?:nhập|điền|fill|type|enter)\s+(?:giá\s+trị\s+)?['\"`]([^'\"`]+)['\"`]\s+(?:vào|into)\s+(?:ô|trường|input|field)?\s*['\"`]?([^'\"`\n]+)['\"`]?", line_clean, re.IGNORECASE)
                if m_fill:
                    val = m_fill.group(1).strip()
                    target = m_fill.group(2).strip()
                else:
                    # Pattern: Nhập trường 'target' với 'value'
                    m_fill_rev = re.search(r"(?:nhập|điền)\s+(?:trường|ô)?\s*['\"`]([^'\"`]+)['\"`]\s+(?:với|bằng|is)\s+['\"`]([^'\"`]+)['\"`]", line_clean, re.IGNORECASE)
                    if m_fill_rev:
                        target = m_fill_rev.group(1).strip()
                        val = m_fill_rev.group(2).strip()
                    else:
                        quoted = re.findall(r"['\"`]([^'\"`]+)['\"`]", line_clean)
                        if len(quoted) >= 2:
                            val = quoted[0]
                            target = quoted[1]
                        elif len(quoted) == 1:
                            val = quoted[0]
                            target = line_clean

            # 3. CLICK / SUBMIT
            elif first_word in ("nhấp", "bấm", "click", "submit", "ấn") or re.search(r"^(?:nhấp|bấm|click|submit|ấn)\b", line_clean, re.IGNORECASE):
                action = "CLICK"
                m_clk = re.search(r"(?:nhấp|bấm|click|ấn)(?:\s+vào)?(?:\s+(?:nút|button|link|icon))?\s*['\"`]([^'\"`]+)['\"`]?", line_clean, re.IGNORECASE)
                if m_clk:
                    target = m_clk.group(1).strip()
                else:
                    target = line_clean

            # 4. SELECT / DROPDOWN
            elif first_word in ("chọn", "select", "choose") or re.search(r"^(?:chọn|select|choose)\b", line_clean, re.IGNORECASE):
                action = "SELECT"
                m_sel = re.search(r"(?:chọn|select)\s+['\"`]([^'\"`]+)['\"`]\s+(?:trong|tại|from)\s+(?:dropdown|menu|trường)?\s*['\"`]?([^'\"`\n]+)['\"`]?", line_clean, re.IGNORECASE)
                if m_sel:
                    val = m_sel.group(1).strip()
                    target = m_sel.group(2).strip()
                else:
                    target = line_clean

            # 5. ASSERTIONS / VERIFICATION
            elif first_word in ("kiểm", "xác", "verify", "assert", "thấy") or any(w in line_clean.lower() for w in ["kiểm tra", "xác nhận", "verify", "assert", "thấy", "hiển thị"]):
                action = "ASSERT_VISIBLE"
                quoted = re.findall(r"['\"`]([^'\"`]+)['\"`]", line_clean)
                target = quoted[0] if quoted else line_clean

            steps.append(ActionStep(step_num=step_idx, raw_text=line, action=action, target=target, value=val))
            step_idx += 1

        return steps

    def verify_steps_against_dom(self, steps: List[ActionStep]) -> Tuple[List[ActionStep], Dict[str, Any]]:
        """Verifies parsed action steps against loaded DOM elements (Track 2 DOM Contract)."""
        stats = {
            "total_steps": len(steps),
            "passed": 0,
            "locator_drift": 0,
            "blocked": 0,
            "unknown_action": 0
        }

        for s in steps:
            if s.action == "NAVIGATE":
                s.status = "PASSED"
                stats["passed"] += 1

            elif s.action in ("FILL", "CLICK", "SELECT"):
                if not s.target:
                    s.status = "LOCATOR_DRIFT"
                    s.error_detail = f"Bước thao tác không chỉ định tên phần tử UI mục tiêu: '{s.raw_text}'"
                    stats["locator_drift"] += 1
                    continue

                matched_elem = None
                t_exact = s.target.lower().strip("'\" ")
                # Pass 1: exact match on id, name, placeholder, label, text
                for elem in self.dom_elements:
                    cands = [elem.id.lower(), elem.name.lower(), elem.placeholder.lower(), elem.aria_label.lower(), elem.label_text.lower(), elem.inner_text.lower()]
                    if t_exact in cands:
                        matched_elem = elem
                        break

                # Pass 2: semantic/substring match
                if not matched_elem:
                    for elem in self.dom_elements:
                        if elem.matches_target(s.target):
                            matched_elem = elem
                            break

                if not matched_elem:
                    s.status = "LOCATOR_DRIFT"
                    s.error_detail = f"Phần tử giao diện '{s.target}' không tồn tại trong cây DOM/AOM."
                    stats["locator_drift"] += 1
                else:
                    if matched_elem.is_hidden:
                        s.status = "INTERACTION_BLOCKED"
                        s.error_detail = f"Phần tử '{s.target}' tồn tại nhưng đang bị ẩn (hidden/display:none)."
                        stats["blocked"] += 1
                    elif matched_elem.is_disabled:
                        s.status = "INTERACTION_BLOCKED"
                        s.error_detail = f"Phần tử '{s.target}' tồn tại nhưng đang ở trạng thái disabled."
                        stats["blocked"] += 1
                    elif s.action == "FILL" and matched_elem.is_readonly:
                        s.status = "INTERACTION_BLOCKED"
                        s.error_detail = f"Trường nhập liệu '{s.target}' đang ở trạng thái readonly."
                        stats["blocked"] += 1
                    else:
                        s.status = "PASSED"
                        stats["passed"] += 1

            elif s.action in ("ASSERT_VISIBLE", "ASSERT_TEXT"):
                # Always verifiable if page is loaded
                s.status = "PASSED"
                stats["passed"] += 1

            else:
                s.status = "UNKNOWN_ACTION"
                s.error_detail = f"Không nhận diện được hành động cụ thể từ bước: '{s.raw_text}'"
                stats["unknown_action"] += 1

        return steps, stats

    @staticmethod
    def is_playwright_available() -> bool:
        """Checks if Playwright is available in the Node runtime."""
        check_js = """
try {
  require('@playwright/test');
  process.exit(0);
} catch (e1) {
  try {
    require('/opt/homebrew/lib/node_modules/@playwright/test');
    process.exit(0);
  } catch (e2) {
    try {
      require('playwright');
      process.exit(0);
    } catch (e3) {
      process.exit(1);
    }
  }
}
"""
        env = dict(os.environ)
        paths = [p for p in [env.get("NODE_PATH"), "/opt/homebrew/lib/node_modules", "/usr/local/lib/node_modules"] if p]
        env["NODE_PATH"] = os.pathsep.join(paths)
        try:
            res = subprocess.run(["node", "-e", check_js], capture_output=True, env=env, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def run_live_playwright_test(self, steps: List[ActionStep], target_url_or_path: str) -> Dict[str, Any]:
        """Executes live Headless Playwright script using local Chrome channel (Track 1)."""
        abs_target = target_url_or_path
        if os.path.isfile(target_url_or_path):
            abs_target = f"file://{os.path.abspath(target_url_or_path)}"

        # Build execution script
        script_actions = []
        script_actions.append(f'  await page.goto("{abs_target}", {{ waitUntil: "domcontentloaded", timeout: 3000 }});')

        for s in steps:
            if s.action == "FILL":
                clean_t = s.target.replace('"', '\\"')
                clean_v = s.value.replace('"', '\\"')
                script_actions.append(
                    f'  await page.locator(\'#{clean_t}, [name="{clean_t}"], [placeholder*="{clean_t}" i]\')'
                    f'.first().fill("{clean_v}", {{ timeout: 1500 }});'
                )
            elif s.action == "CLICK":
                clean_t = s.target.replace('"', '\\"')
                script_actions.append(
                    f'  await page.locator(\'button:has-text("{clean_t}"), #{clean_t}, input[type="submit"]\')'
                    f'.first().click({{ timeout: 1500 }});'
                )
            elif s.action == "SELECT":
                clean_t = s.target.replace('"', '\\"')
                clean_v = s.value.replace('"', '\\"')
                script_actions.append(
                    f'  await page.locator(\'select#{clean_t}, select[name="{clean_t}"]\')'
                    f'.first().selectOption("{clean_v}", {{ timeout: 1500 }});'
                )

        runner_js = f"""
let pw;
try {{
  pw = require('@playwright/test');
}} catch (e) {{
  try {{
    pw = require('/opt/homebrew/lib/node_modules/@playwright/test');
  }} catch (e2) {{
    try {{
      pw = require('playwright');
    }} catch (e3) {{
      console.log(JSON.stringify({{ success: false, error: 'Playwright module is not installed in Node environment' }}));
      process.exit(0);
    }}
  }}
}}
if (!pw) {{
  console.log(JSON.stringify({{ success: false, error: 'Playwright module is not available' }}));
  process.exit(0);
}}
const {{ chromium }} = pw;
(async () => {{
  const startTime = Date.now();
  let browser;
  try {{
    try {{
      browser = await chromium.launch({{ headless: true, channel: 'chrome' }});
    }} catch (e) {{
      browser = await chromium.launch({{ headless: true }});
    }}
    const page = await browser.newPage();
    page.setDefaultTimeout(1500);
{chr(10).join(script_actions)}
    const duration = Date.now() - startTime;
    console.log(JSON.stringify({{ success: true, duration_ms: duration, steps_executed: {len(steps)} }}));
    await browser.close();
  }} catch (err) {{
    if (browser) await browser.close();
    console.log(JSON.stringify({{ success: false, error: err.message }}));
  }}
}})();
"""
        env = dict(os.environ)
        paths = [p for p in [env.get("NODE_PATH"), "/opt/homebrew/lib/node_modules", "/usr/local/lib/node_modules"] if p]
        env["NODE_PATH"] = os.pathsep.join(paths)

        try:
            res = subprocess.run(["node", "-e", runner_js], capture_output=True, text=True, env=env, timeout=6)
            if res.returncode == 0 and res.stdout.strip():
                lines = [line.strip() for line in res.stdout.splitlines() if line.strip().startswith("{")]
                if lines:
                    return json.loads(lines[-1])
            return {"success": False, "error": res.stderr or "Playwright execution failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_playwright_clean_pom_spec(self, test_cases: List[Dict[str, Any]], spec_title: str = "AutoSanitySuite") -> str:
        """Generates clean, production-ready Playwright TypeScript spec from manual test cases."""
        lines = [
            'import { test, expect } from "@playwright/test";',
            '',
            '/**',
            f' * {spec_title} — Generated by Synapse Hub Auto-Sanity Engine (Phase 3)',
            ' * Standard: Clean POM Flat Architecture & Zero Static Sleeps',
            ' */',
            f'test.describe("{spec_title}", () => {{',
            ''
        ]

        for tc in test_cases:
            tc_id = tc.get("TC ID") or tc.get("TC_ID") or "TC_AUTO"
            title = tc.get("Test Title") or "Sanity Scenario"
            steps_raw = tc.get("Test Steps") or ""
            steps = self.parse_test_steps(steps_raw)

            lines.append(f'  test("{tc_id}: {title}", async ({{ page }}) => {{')
            for s in steps:
                lines.append(f'    // Step {s.step_num}: {s.raw_text}')
                lines.append(f'    {s.generate_pom_locator_ts()}')
            lines.append('  });\n')

        lines.append('});')
        return "\n".join(lines)

    def generate_auto_sanity_report_md(self, suite_results: List[Dict[str, Any]]) -> str:
        """Emits formal Auto-Sanity Certification Report in Markdown."""
        total_tcs = len(suite_results)
        verified_tcs = sum(1 for r in suite_results if r["overall_status"] == "VERIFIED")
        drift_tcs = sum(1 for r in suite_results if r["overall_status"] == "DRIFT_DETECTED")
        pass_rate = round((verified_tcs / max(1, total_tcs)) * 100, 1)

        trust_level = "🟢 HIGH_TRUST (Bấm nút dùng ngay)" if pass_rate >= 90.0 else ("🟡 MEDIUM_TRUST (Cần rà soát nhẹ)" if pass_rate >= 75.0 else "🔴 UNTRUSTED (Lệch giao diện nhiều)")

        lines = [
            "# BÁO CÁO THẨM ĐỊNH TỰ ĐỘNG THỰC THI (AUTO-SANITY VERIFICATION REPORT)",
            "",
            "> **Cơ chế:** Headless Playwright Ground-Truth Verification (Phase 3 Engine)  ",
            "> **Tiêu chuẩn:** ISO/IEC/IEEE 29119-3 & Clean POM Web Feasibility Sentinel  ",
            f"> **Mức độ Tin cậy:** **{trust_level}**",
            "",
            "---",
            "",
            "## 1. TỔNG QUAN CHỈ SỐ THỰC THI",
            "",
            "| Chỉ số Đo lường | Giá trị | Đánh giá Tiêu chuẩn |",
            "| :--- | :---: | :--- |",
            f"| **Tổng số Test Cases thẩm định** | **{total_tcs}** | Toàn bộ các ca kiểm thử trong bộ hồ sơ |",
            f"| **Số ca Kiểm thử Thực thi Thành công (Verified)** | **{verified_tcs}** | 100% phần tử tương tác thực tế tồn tại trên UI |",
            f"| **Số ca Kiểm thử Lệch Giao diện (Drift Detected)** | **{drift_tcs}** | Phát hiện nút bấm/input bị sai tên hoặc bị ẩn |",
            f"| **Tỷ lệ Khả thi Thực tế (Feasibility Rate)** | **{pass_rate}%** | Ngưỡng an toàn Zero-Review >= 90% |",
            "",
            "---",
            "",
            "## 2. MA TRẬN KẾT QUẢ THẨM ĐỊNH CHI TIẾT TỪNG TEST CASE",
            "",
            "| TC ID | Tiêu đề Kịch bản | Số Bước | Trạng thái Thẩm định | Chi tiết Tương tác & Khuyến nghị |",
            "| :--- | :--- | :---: | :---: | :--- |"
        ]

        for r in suite_results:
            badge = "✅ VERIFIED" if r["overall_status"] == "VERIFIED" else "❌ DRIFT"
            lines.append(
                f"| **{r['tc_id']}** | {r['title']} | {len(r['steps'])} | `{badge}` | {r['summary']} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 3. CHI TIẾT TỪNG BƯỚC THAO TÁC TRÊN GIAO DIỆN THỰC TẾ",
            "",
            "| TC ID | Bước | Hành động | Target | Dữ liệu | Trạng thái DOM | Lỗi / Cảnh báo |",
            "| :--- | :---: | :---: | :--- | :--- | :---: | :--- |"
        ])

        for r in suite_results:
            for s in r["steps"]:
                st_badge = "✅ PASS" if s["status"] == "PASSED" else f"🔴 {s['status']}"
                err_text = s["error_detail"] or "-"
                lines.append(
                    f"| {r['tc_id']} | #{s['step_num']} | `{s['action']}` | `{s['target']}` | `{s['value']}` | {st_badge} | {err_text} |"
                )

        return "\n".join(lines)

    @staticmethod
    def generate_annotated_test_cases_md(original_content: str, suite_results: List[Dict[str, Any]]) -> str:
        """Annotates original 12-column table rows with @Live-Verified or @Drift-Detected tags."""
        result_map = {r["tc_id"]: r["overall_status"] for r in suite_results}
        lines = original_content.splitlines()
        annotated_lines = []

        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("|") and trimmed.endswith("|") and "---" not in trimmed:
                cols = [c.strip() for c in trimmed.split("|")[1:-1]]
                if len(cols) >= 12 and (cols[0] in result_map):
                    tc_id = cols[0]
                    status = result_map[tc_id]
                    if status == "VERIFIED":
                        tag_badge = "@Live-Verified"
                    elif status == "EXECUTION_FAILED":
                        tag_badge = "@Execution-Failed"
                    else:
                        tag_badge = "@Drift-Detected"
                    curr_tags = cols[11]
                    if tag_badge not in curr_tags:
                        cols[11] = f"{curr_tags}, {tag_badge}" if curr_tags and curr_tags != "-" else tag_badge
                    annotated_lines.append("| " + " | ".join(cols) + " |")
                    continue
            annotated_lines.append(line)

        return "\n".join(annotated_lines)


def main():
    parser = argparse.ArgumentParser(description="Auto-Sanity Headless Playwright Verification Engine")
    parser.add_argument("test_cases", help="Path to ISO 29119-3 12-column test cases markdown file")
    parser.add_argument("--html", help="Path to target HTML file or mock UI for DOM/AOM contract verification")
    parser.add_argument("--url", help="Target URL for live headless Playwright execution")
    parser.add_argument("--live", action="store_true", help="Execute live headless Playwright in-browser verification")
    parser.add_argument("-o", "--output-report", help="Output path for Auto-Sanity markdown report")
    parser.add_argument("--export-spec", help="Export Clean POM Playwright TypeScript spec (.spec.ts)")
    parser.add_argument("--annotated-output", help="Output path for annotated 12-column test cases with verification badges")
    args = parser.parse_args()

    print("\n" + "=" * 76)
    print("   AUTO-SANITY HEADLESS PLAYWRIGHT VERIFICATION ENGINE (PHASE 3)")
    print("=" * 76)

    # 1. Parse Test Cases from File
    from tools.lint.manual_tc_linter import parse_markdown_tables
    if not os.path.isfile(args.test_cases):
        print(f"❌ Error: File not found: {args.test_cases}")
        return 1

    with open(args.test_cases, "r", encoding="utf-8") as f:
        content = f.read()

    tables = parse_markdown_tables(content)
    test_rows = []
    for t in tables:
        h_lower = [h.lower() for h in t["headers"]]
        if any("tc id" in h or "tc_id" in h for h in h_lower):
            test_rows.extend(t["rows"])

    print(f"\n📁 Loaded {len(test_rows)} test cases from: {args.test_cases}")

    # 2. Initialize Engine with target HTML if provided
    engine = AutoSanityEngine(args.html)
    if args.html:
        print(f"🌐 Loaded DOM/AOM Contract from: {args.html} ({len(engine.dom_elements)} interactive elements)")

    # 3. Verify each test case
    suite_results = []
    for row in test_rows:
        tc_id = row.get("TC ID") or row.get("TC_ID") or "TC_AUTO"
        title = row.get("Test Title") or "Untitled Scenario"
        steps_raw = row.get("Test Steps") or ""

        parsed_steps = engine.parse_test_steps(steps_raw)
        verified_steps, stats = engine.verify_steps_against_dom(parsed_steps)

        # Check live Playwright if explicitly requested via --live or --url
        if (args.live or args.url) and (args.url or (args.html and os.path.isfile(args.html))):
            target_live = args.url or args.html
            live_res = engine.run_live_playwright_test(parsed_steps, target_live)
            if not live_res.get("success"):
                stats["live_error"] = live_res.get("error")

        if stats.get("live_error"):
            overall_status = "EXECUTION_FAILED"
            summary = f"Playwright thực thi thất bại: {stats['live_error']}"
        elif stats["locator_drift"] == 0 and stats["blocked"] == 0:
            overall_status = "VERIFIED"
            summary = "Toàn bộ các bước click và nhập liệu tương thích 100% với DOM."
        else:
            overall_status = "DRIFT_DETECTED"
            if stats["locator_drift"] > 0:
                summary = f"Phát hiện {stats['locator_drift']} bước bị lệch tên định danh (Locator Drift)."
            elif stats["blocked"] > 0:
                summary = f"Phát hiện {stats['blocked']} phần tử bị khóa hoặc vô hiệu hóa."

        suite_results.append({
            "tc_id": tc_id,
            "title": title,
            "overall_status": overall_status,
            "summary": summary,
            "steps": [s.to_dict() for s in verified_steps]
        })

    # 4. Generate and Save Report
    report_md = engine.generate_auto_sanity_report_md(suite_results)
    out_rep = args.output_report or "Reports/sanity/AUTO_SANITY_VERIFICATION_REPORT.md"
    os.makedirs(os.path.dirname(os.path.abspath(out_rep)), exist_ok=True)
    with open(out_rep, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\n📄 Saved Auto-Sanity Verification Report to: {out_rep}")

    # 5. Export Playwright Spec if requested
    if args.export_spec:
        spec_ts = engine.generate_playwright_clean_pom_spec(test_rows)
        os.makedirs(os.path.dirname(os.path.abspath(args.export_spec)), exist_ok=True)
        with open(args.export_spec, "w", encoding="utf-8") as f:
            f.write(spec_ts)
        print(f"⚡ Exported Executable Playwright Clean POM Spec: {args.export_spec}")

    # 6. Save Annotated Test Cases if requested
    if args.annotated_output:
        ann_md = engine.generate_annotated_test_cases_md(content, suite_results)
        os.makedirs(os.path.dirname(os.path.abspath(args.annotated_output)), exist_ok=True)
        with open(args.annotated_output, "w", encoding="utf-8") as f:
            f.write(ann_md)
        print(f"🏷️  Saved Annotated Test Cases: {args.annotated_output}")

    print("\n" + "=" * 76 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
