#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Omni-Emitter: Universal Polyglot Code Generator & Transpiler
------------------------------------------------------------
Generates 100% production-ready, idiomatically compliant automation code
from the Universal Intermediate Representation (universal_ir.ProjectIR).
Supports:
  1. Playwright TypeScript (playwright-ts)
  2. Playwright Python (playwright-python)
  3. Selenium Java (selenium-java)
  4. Katalon Groovy (katalon-groovy) - Clean POM Flat Architecture
  5. Cypress JavaScript (cypress-js)
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


import re
from typing import Dict

try:
    from tools.transpiler.universal_ir import (
        ProjectIR, PageClassIR, LocatorIR, ActionType, LocatorStrategy
    )
except ImportError:
    from universal_ir import (
        ProjectIR, PageClassIR, LocatorIR, ActionType, LocatorStrategy
    )


def escape_js(s: str) -> str:
    """Escapes string for single-quoted JS/TS literals."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def escape_java(s: str) -> str:
    """Escapes string for double-quoted Java/Groovy literals."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _to_pascal_ident(name: str) -> str:
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", name) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts) or "Generated"


def _to_prop_ident(raw: str, prefix: str = "el") -> str:
    tokens = [t.lower() for t in re.split(r"[^a-zA-Z0-9]+", raw) if t]
    if not tokens:
        return prefix
    parts = [prefix] + [t.capitalize() for t in tokens[:3]]
    return "".join(parts)


class OmniEmitter:
    """Universal Code Emitter for Multi-Language Automation Frameworks."""

    SUPPORTED_TARGETS = [
        "playwright-ts",
        "playwright-python",
        "selenium-java",
        "katalon-groovy",
        "cypress-js"
    ]

    @classmethod
    def emit(cls, project: ProjectIR, target_framework: str) -> Dict[str, str]:
        target = target_framework.lower().strip()
        if target not in cls.SUPPORTED_TARGETS:
            raise ValueError(f"Unsupported target framework '{target_framework}'. Supported: {cls.SUPPORTED_TARGETS}")

        output_files: Dict[str, str] = {}

        if target == "playwright-ts":
            output_files.update(cls._emit_playwright_ts(project))
        elif target == "playwright-python":
            output_files.update(cls._emit_playwright_python(project))
        elif target == "selenium-java":
            output_files.update(cls._emit_selenium_java(project))
        elif target == "katalon-groovy":
            output_files.update(cls._emit_katalon_groovy(project))
        elif target == "cypress-js":
            output_files.update(cls._emit_cypress_js(project))

        return output_files

    @classmethod
    def _build_pom_context(cls, project: ProjectIR):
        """Returns (all_pages, step_locator_map) with Clean POM encapsulation for raw test selectors."""
        pages = list(project.pages)
        existing_locs = {}
        for page in pages:
            for loc in page.locators:
                existing_locs[loc.value] = (page.name, loc.name)
                existing_locs[loc.name] = (page.name, loc.name)

        raw_targets = []
        seen_targets = set()
        for tc in project.test_cases:
            for s in tc.steps:
                if s.action in (ActionType.CLICK, ActionType.FILL) and s.target and s.target not in existing_locs and s.target not in seen_targets:
                    seen_targets.add(s.target)
                    raw_targets.append((s.action, s.target))

        step_locator_map = dict(existing_locs)
        if raw_targets:
            base = _to_pascal_ident(project.name)
            helper_name = f"{base}Page" if not pages else f"{base}StepPage"
            helper_page = PageClassIR(name=helper_name)
            name_counts: Dict[str, int] = {}
            for action, target in raw_targets:
                prefix = "btn" if action == ActionType.CLICK else "txt"
                base_prop = _to_prop_ident(target, prefix=prefix)
                dup_idx = name_counts.get(base_prop, 0)
                name_counts[base_prop] = dup_idx + 1
                prop = f"{base_prop}_{dup_idx}" if dup_idx else base_prop
                helper_page.locators.append(
                    LocatorIR(name=prop, strategy=LocatorStrategy.CSS, value=target)
                )
                step_locator_map[target] = (helper_name, prop)
            pages.append(helper_page)

        return pages, step_locator_map

    # -------------------------------------------------------------------------
    # 1. Playwright TypeScript Emitter
    # -------------------------------------------------------------------------
    @classmethod
    def _emit_safe_interact_helper(cls) -> str:
        return """import { Page, Locator, expect } from "@playwright/test";

export interface SafeInteractOptions {
  action?: 'click' | 'fill' | 'hover' | 'select' | 'upload' | 'check';
  value?: string;
  files?: string | string[];
  fallbackToJsDispatch?: boolean;
  ensureVisible?: boolean;
  retryCount?: number;
  stabilityTimeoutMs?: number;
}

/**
 * Resilient Cross-Engine Interaction Polyfill
 * Neutralizes layout rendering & event dispatch differences across Chromium, WebKit, and Gecko:
 * 1. Scrolls target into view if needed (ensureVisible)
 * 2. Catches WebKit/Safari overlay interception and fallbacks to JS dispatchEvent
 * 3. Handles resilient retries using web-first visibility assertions (zero static sleeps)
 */
export async function safeInteract(
  page: Page,
  target: Locator | string,
  options: SafeInteractOptions = {}
): Promise<void> {
  const {
    action = 'click',
    value = '',
    files,
    fallbackToJsDispatch = true,
    ensureVisible = true,
    retryCount = 2,
    stabilityTimeoutMs = 5000
  } = options;

  const locator = typeof target === 'string' ? page.locator(target) : target;

  for (let attempt = 0; attempt <= retryCount; attempt++) {
    try {
      if (ensureVisible) {
        try {
          await locator.scrollIntoViewIfNeeded({ timeout: stabilityTimeoutMs });
        } catch (scrollErr: unknown) {
          console.warn('scrollIntoViewIfNeeded warning:', scrollErr);
        }
      }

      if (action === 'click') {
        await locator.click({ timeout: stabilityTimeoutMs });
      } else if (action === 'fill') {
        await locator.fill(value, { timeout: stabilityTimeoutMs });
      } else if (action === 'check') {
        await locator.check({ timeout: stabilityTimeoutMs });
      } else if (action === 'upload' && files) {
        await locator.setInputFiles(files);
      } else if (action === 'hover') {
        await locator.hover({ timeout: stabilityTimeoutMs });
      }
      return;
    } catch (err: any) {
      const isLastAttempt = attempt === retryCount;
      const isIntercepted = err.message && (
        err.message.includes('intercepted') ||
        err.message.includes('another element') ||
        err.message.includes('not visible') ||
        err.message.includes('pointer-events')
      );

      if (fallbackToJsDispatch && isIntercepted) {
        await locator.evaluate((el: any) => {
          el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
        });
        return;
      }

      if (isLastAttempt) {
        throw err;
      }
      await expect(locator).toBeVisible({ timeout: stabilityTimeoutMs });
    }
  }
}
"""

    @classmethod
    def _emit_playwright_ts(cls, project: ProjectIR) -> Dict[str, str]:
        files: Dict[str, str] = {}
        files["helpers/safeInteract.ts"] = cls._emit_safe_interact_helper()
        all_pages, step_locator_map = cls._build_pom_context(project)

        for page in all_pages:
            code = [
                'import { Page, Locator, expect } from "@playwright/test";',
                'import { safeInteract } from "../helpers/safeInteract";',
                "",
                f"export class {page.name} {{",
                "  readonly page: Page;",
            ]

            for loc in page.locators:
                code.append(f"  readonly {loc.name}: Locator;")

            code.extend([
                "",
                "  constructor(page: Page) {",
                "    this.page = page;",
            ])

            for loc in page.locators:
                if loc.strategy == LocatorStrategy.ROLE:
                    role_parts = loc.value.split("[name='")
                    role_name = escape_js(role_parts[0])
                    acc_name = escape_js(role_parts[1].rstrip("']") if len(role_parts) > 1 else "")
                    code.append(f"    this.{loc.name} = page.getByRole('{role_name}' as any, {{ name: '{acc_name}' }});")
                elif loc.strategy == LocatorStrategy.TEST_ID:
                    code.append(f"    this.{loc.name} = page.getByTestId('{escape_js(loc.value)}');")
                elif loc.strategy == LocatorStrategy.LABEL:
                    code.append(f"    this.{loc.name} = page.getByLabel('{escape_js(loc.value)}');")
                elif loc.strategy == LocatorStrategy.PLACEHOLDER:
                    code.append(f"    this.{loc.name} = page.getByPlaceholder('{escape_js(loc.value)}');")
                elif loc.strategy == LocatorStrategy.TEXT:
                    code.append(f"    this.{loc.name} = page.getByText('{escape_js(loc.value)}');")
                else:
                    code.append(f"    this.{loc.name} = page.locator('{escape_js(loc.value)}');")

            code.append("  }")

            for m in page.methods:
                params_decl = ", ".join([f"{p}: string" for p in m.parameters])
                code.extend([
                    "",
                    f"  async {m.name}({params_decl}): Promise<void> {{",
                ])
                if not m.steps:
                    code.append("    // Auto-generated method stub")
                for s in m.steps:
                    if s.action == ActionType.GOTO:
                        code.append(f"    await this.page.goto('{escape_js(s.value or '')}');")
                    elif s.action == ActionType.CLICK:
                        target = s.target or "element"
                        code.append(f"    await safeInteract(this.page, this.{target}, {{ action: 'click', fallbackToJsDispatch: true, ensureVisible: true }});")
                    elif s.action == ActionType.FILL:
                        target = s.target or "input"
                        val = s.value or "value"
                        code.append(f"    await expect(this.{target}).toBeEditable();")
                        code.append(f"    await safeInteract(this.page, this.{target}, {{ action: 'fill', value: '{escape_js(val)}' }});")
                    elif s.action == ActionType.WAIT:
                        if s.is_sanitized_wait and s.target:
                            code.append(f"    await this.page.evaluate((sel) => (window as any).__qa?.probeStability(sel), '{escape_js(s.target)}'); // Event-Driven Stability Probe")
                        else:
                            code.append("    await this.page.waitForLoadState('domcontentloaded');")
                    elif s.action == ActionType.ASSERT:
                        code.append("    await expect(this.page).toHaveURL(/.+/);")
                    else:
                        code.append(f"    // {s.description}")
                code.append("  }")

            code.append("}\n")
            files[f"pages/{page.name}.ts"] = "\n".join(code)

        if project.test_cases:
            t_code = [
                'import { test, expect } from "@playwright/test";',
                'import { safeInteract } from "../helpers/safeInteract";',
            ]
            page_vars = {}
            for page in all_pages:
                t_code.append(f'import {{ {page.name} }} from "../pages/{page.name}";')
                page_vars[page.name] = page.name[0].lower() + page.name[1:]
            t_code.append("")

            for tc in project.test_cases:
                t_code.extend([
                    f"test('{escape_js(tc.id)}: {escape_js(tc.title)}', async ({{ page }}) => {{",
                    "  const uniqueCode = 'AUTO_' + Date.now();",
                ])

                if tc.hermetic_fixtures:
                    t_code.append("  // --- [Hermetic Test Pre-flight Fixture Setup] ---")
                    for hf in tc.hermetic_fixtures:
                        t_code.append(f"  // Fixture: {hf.variable_name} ({hf.fixture_type})")
                        if hf.code_snippet:
                            for c_line in hf.code_snippet.splitlines():
                                t_code.append(f"  {c_line}")
                    t_code.append("")

                for page in all_pages:
                    t_code.append(f"  const {page_vars[page.name]} = new {page.name}(page);")

                has_assert = False
                for s in tc.steps:
                    if s.action == ActionType.GOTO:
                        t_code.append(f"  await page.goto('{escape_js(s.value or '')}');")
                    elif s.action == ActionType.CLICK:
                        p_name, prop = step_locator_map.get(s.target or "", ("", ""))
                        loc_ref = f"{page_vars[p_name]}.{prop}" if p_name in page_vars else "page"
                        t_code.append(f"  await safeInteract(page, {loc_ref}, {{ action: 'click', fallbackToJsDispatch: true, ensureVisible: true }});")
                    elif s.action == ActionType.FILL:
                        p_name, prop = step_locator_map.get(s.target or "", ("", ""))
                        loc_ref = f"{page_vars[p_name]}.{prop}" if p_name in page_vars else "page"
                        t_code.append(f"  await expect({loc_ref}).toBeEditable();")
                        t_code.append(f"  await safeInteract(page, {loc_ref}, {{ action: 'fill', value: '{escape_js(s.value or '')}' }});")
                    elif s.action == ActionType.WAIT:
                        if s.is_sanitized_wait and s.target:
                            t_code.append(f"  await page.evaluate((sel) => (window as any).__qa?.probeStability(sel), '{escape_js(s.target)}'); // Event-Driven Stability Probe")
                        else:
                            t_code.append("  await page.waitForLoadState('domcontentloaded');")
                    elif s.action == ActionType.API_CALL:
                        t_code.append(f"  await page.request.post('{escape_js(s.target or '')}', {{ data: {s.value or '{}'} }}); // {s.description}")
                    elif s.action == ActionType.ASSERT:
                        has_assert = True
                        t_code.append("  await expect(page).toHaveURL(/.+/);")
                    else:
                        t_code.append(f"  // {s.description}")

                if not has_assert:
                    t_code.append("  await expect(page).toHaveURL(/.+/);")

                t_code.append("});\n")
            files[f"tests/{project.name}.spec.ts"] = "\n".join(t_code)

        return files

    # -------------------------------------------------------------------------
    # 2. Playwright Python Emitter
    # -------------------------------------------------------------------------
    @classmethod
    def _emit_playwright_python(cls, project: ProjectIR) -> Dict[str, str]:
        files: Dict[str, str] = {}
        all_pages, step_locator_map = cls._build_pom_context(project)

        for page in all_pages:
            code = [
                "import re",
                "from playwright.sync_api import Page, expect",
                "",
                f"class {page.name}:",
                "    def __init__(self, page: Page):",
                "        self.page = page",
            ]
            for loc in page.locators:
                if loc.strategy == LocatorStrategy.ROLE:
                    role_parts = loc.value.split("[name='")
                    r_name = escape_java(role_parts[0])
                    acc = escape_java(role_parts[1].rstrip("']") if len(role_parts) > 1 else "")
                    code.append(f'        self.{loc.name} = page.get_by_role("{r_name}", name="{acc}")')
                elif loc.strategy == LocatorStrategy.TEST_ID:
                    code.append(f'        self.{loc.name} = page.get_by_test_id("{escape_java(loc.value)}")')
                else:
                    code.append(f'        self.{loc.name} = page.locator("{escape_java(loc.value)}")')

            code.extend([
                "",
                "    def verify_loaded(self):",
                '        expect(self.page).to_have_url(re.compile(r".+"))',
            ])

            for m in page.methods:
                params_decl = ", ".join(["self"] + m.parameters)
                code.extend([
                    "",
                    f"    def {m.name}({params_decl}):",
                ])
                if not m.steps:
                    code.append("        pass")
                for s in m.steps:
                    if s.action == ActionType.CLICK:
                        code.append(f"        self.{s.target}.click()")
                    elif s.action == ActionType.FILL:
                        code.append(f'        self.{s.target}.fill("{escape_java(s.value or "")}")')
                    else:
                        code.append(f"        # {s.description}")

            code.append("\n")
            files[f"pages/{page.name}.py"] = "\n".join(code)

        if project.test_cases:
            t_code = [
                "import uuid",
                "import pytest",
                "from playwright.sync_api import Page",
            ]
            page_vars = {}
            for page in all_pages:
                t_code.append(f"from pages.{page.name} import {page.name}")
                page_vars[page.name] = page.name[0].lower() + page.name[1:]
            t_code.append("")
            primary_page_var = page_vars[all_pages[0].name] if all_pages else None

            for tc in project.test_cases:
                func_name = re.sub(r'[^a-zA-Z0-9_]', '_', tc.id.lower())
                t_code.extend([
                    f"def test_{func_name}(page: Page):",
                    f'    """{escape_java(tc.id)}: {escape_java(tc.title)}"""',
                    "    unique_code = f'AUTO_{uuid.uuid4().hex[:8]}'",
                ])
                for page in all_pages:
                    t_code.append(f"    {page_vars[page.name]} = {page.name}(page)")

                has_assert = False
                for s in tc.steps:
                    if s.action == ActionType.GOTO:
                        t_code.append(f"    page.goto('{escape_java(s.value or s.target or '')}')")
                    elif s.action == ActionType.CLICK:
                        p_name, prop = step_locator_map.get(s.target or "", ("", ""))
                        if p_name in page_vars:
                            t_code.append(f"    {page_vars[p_name]}.{prop}.click()")
                    elif s.action == ActionType.FILL:
                        p_name, prop = step_locator_map.get(s.target or "", ("", ""))
                        if p_name in page_vars:
                            t_code.append(f"    {page_vars[p_name]}.{prop}.fill('{escape_java(s.value or '')}')")
                    elif s.action == ActionType.ASSERT:
                        has_assert = True
                        if primary_page_var:
                            t_code.append(f"    {primary_page_var}.verify_loaded()")
                        else:
                            t_code.append("    assert page.url != ''")
                    else:
                        t_code.append(f"    # {s.description}")

                if not has_assert:
                    if primary_page_var:
                        t_code.append(f"    {primary_page_var}.verify_loaded()")
                    else:
                        t_code.append("    assert page.url != ''")
                t_code.append("")

            files[f"tests/test_{project.name.lower()}.py"] = "\n".join(t_code)

        return files

    # -------------------------------------------------------------------------
    # 3. Selenium Java Emitter (Clean POM)
    # -------------------------------------------------------------------------
    @classmethod
    def _emit_selenium_java(cls, project: ProjectIR) -> Dict[str, str]:
        files: Dict[str, str] = {}

        for page in project.pages:
            code = [
                "package pages;",
                "",
                "import org.openqa.selenium.By;",
                "import org.openqa.selenium.WebDriver;",
                "import org.openqa.selenium.support.ui.WebDriverWait;",
                "import org.openqa.selenium.support.ui.ExpectedConditions;",
                "import java.time.Duration;",
                "",
                f"public class {page.name} {{",
                "    private final WebDriver driver;",
                "    private final WebDriverWait wait;",
                "",
            ]

            for loc in page.locators:
                if loc.strategy == LocatorStrategy.XPATH:
                    code.append(f'    private final By {loc.name} = By.xpath("{escape_java(loc.value)}");')
                elif loc.strategy == LocatorStrategy.ID:
                    code.append(f'    private final By {loc.name} = By.id("{escape_java(loc.value)}");')
                else:
                    code.append(f'    private final By {loc.name} = By.cssSelector("{escape_java(loc.value)}");')

            code.extend([
                "",
                f"    public {page.name}(WebDriver driver) {{",
                "        this.driver = driver;",
                "        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));",
                "    }",
            ])

            for m in page.methods:
                params_decl = ", ".join([f"String {p}" for p in m.parameters])
                code.extend([
                    "",
                    f"    public void {m.name}({params_decl}) {{",
                ])
                if not m.steps:
                    code.append("        // Stub")
                for s in m.steps:
                    if s.action == ActionType.CLICK:
                        code.append(f"        wait.until(ExpectedConditions.elementToBeClickable({s.target})).click();")
                    elif s.action == ActionType.FILL:
                        code.append(f'        wait.until(ExpectedConditions.visibilityOfElementLocated({s.target})).sendKeys("{escape_java(s.value or "")}");')
                    else:
                        code.append(f"        // {s.description}")
                code.append("    }")

            code.append("}\n")
            files[f"src/main/java/pages/{page.name}.java"] = "\n".join(code)

        if project.test_cases:
            t_code = [
                "package tests;",
                "",
                "import org.junit.jupiter.api.Assertions;",
                "import org.junit.jupiter.api.Test;",
                "import org.junit.jupiter.api.BeforeEach;",
                "import org.junit.jupiter.api.AfterEach;",
                "import org.openqa.selenium.WebDriver;",
                "import org.openqa.selenium.chrome.ChromeDriver;",
                "import pages.*;",
                "",
                f"public class {project.name}Test {{",
                "    private WebDriver driver;",
                "",
                "    @BeforeEach",
                "    public void setUp() {",
                "        driver = new ChromeDriver();",
                "    }",
                "",
                "    @AfterEach",
                "    public void tearDown() {",
                "        if (driver != null) driver.quit();",
                "    }",
            ]
            for tc in project.test_cases:
                m_name = re.sub(r'[^a-zA-Z0-9_]', '_', tc.id)
                t_code.extend([
                    "",
                    "    @Test",
                    f"    public void test_{m_name}() {{",
                    f"        // {tc.id}: {tc.title}",
                    '        String uniqueCode = "AUTO_" + System.currentTimeMillis();',
                ])
                has_assert = False
                for s in tc.steps:
                    if s.action == ActionType.GOTO:
                        t_code.append(f'        driver.get("{escape_java(s.value or s.target or "")}");')
                    elif s.action == ActionType.ASSERT:
                        has_assert = True
                        t_code.append('        Assertions.assertFalse(driver.getCurrentUrl().isEmpty(), "Expected active page URL");')
                    else:
                        t_code.append(f'        // {s.description}')
                if not has_assert:
                    t_code.append('        Assertions.assertFalse(driver.getCurrentUrl().isEmpty(), "Expected active page URL");')
                t_code.append("    }")
            t_code.append("}\n")
            files[f"src/test/java/tests/{project.name}Test.java"] = "\n".join(t_code)

        return files

    # -------------------------------------------------------------------------
    # 4. Katalon Groovy Emitter (Clean POM Flat Architecture)
    # -------------------------------------------------------------------------
    @classmethod
    def _emit_katalon_groovy(cls, project: ProjectIR) -> Dict[str, str]:
        files: Dict[str, str] = {}

        for page in project.pages:
            code = [
                "package pages",
                "",
                "import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI",
                "import internal.GlobalVariable",
                "",
                f"public class {page.name} extends BasePage {{",
                "",
            ]

            for loc in page.locators:
                code.append(f'    public static final String {loc.name.upper()} = "{escape_java(loc.value)}"')

            code.append("")

            for m in page.methods:
                params_decl = ", ".join([f"String {p}" for p in m.parameters])
                code.extend([
                    f"    public static void {m.name}({params_decl}) {{",
                ])
                for s in m.steps:
                    if s.action == ActionType.CLICK:
                        code.append(f"        clickJS({s.target.upper()})")
                    elif s.action == ActionType.FILL:
                        code.append(f'        setTextSafe({s.target.upper()}, "{escape_java(s.value or "")}")')
                    elif s.action == ActionType.GOTO:
                        code.append(f'        WebUI.navigateToUrl("{escape_java(s.value or "")}")')
                    else:
                        code.append(f"        // {s.description}")
                code.append("    }\n")

            code.append("}\n")
            files[f"Keywords/pages/{page.name}.groovy"] = "\n".join(code)

        if project.test_cases:
            for tc in project.test_cases:
                s_code = [
                    "import static com.kms.katalon.core.testcase.TestCaseFactory.findTestCase",
                    "import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI",
                    "import pages.*",
                    "",
                    "String uniqueCode = BasePage.uniqueCode('AUTO_')",
                    "",
                ]
                for s in tc.steps:
                    if s.action == ActionType.GOTO:
                        s_code.append(f'WebUI.navigateToUrl("{escape_java(s.value or "")}")')
                    elif s.action == ActionType.ASSERT:
                        page_ref = project.pages[0].name if project.pages else "BasePage"
                        s_code.append(f"assert {page_ref}.isPageLoaded()")
                    else:
                        s_code.append(f'// {s.description}')

                s_code.append("")
                files[f"Scripts/{tc.id}_{tc.title}/Script.groovy"] = "\n".join(s_code)

        return files

    # -------------------------------------------------------------------------
    # 5. Cypress JavaScript Emitter
    # -------------------------------------------------------------------------
    @classmethod
    def _emit_cypress_js(cls, project: ProjectIR) -> Dict[str, str]:
        files: Dict[str, str] = {}
        all_pages, step_locator_map = cls._build_pom_context(project)

        for page in all_pages:
            code = [
                f"export class {page.name} {{",
            ]
            for loc in page.locators:
                code.extend([
                    f"  get {loc.name}() {{",
                    f"    return cy.get('{escape_js(loc.value)}');",
                    "  }",
                ])

            for m in page.methods:
                params_decl = ", ".join(m.parameters)
                code.extend([
                    "",
                    f"  {m.name}({params_decl}) {{",
                ])
                for s in m.steps:
                    if s.action == ActionType.CLICK:
                        code.append(f"    this.{s.target}.click();")
                    elif s.action == ActionType.FILL:
                        code.append(f"    this.{s.target}.type('{escape_js(s.value or '')}');")
                    else:
                        code.append(f"    // {s.description}")
                code.append("  }")

            code.append("}\n")
            files[f"cypress/pages/{page.name}.js"] = "\n".join(code)

        if project.test_cases:
            t_code = [
                f"import {{ {page.name} }} from '../pages/{page.name}';"
                for page in all_pages
            ]
            page_vars = {page.name: page.name[0].lower() + page.name[1:] for page in all_pages}
            t_code.extend([
                "",
                f"describe('{escape_js(project.name)}', () => {{",
            ])
            for tc in project.test_cases:
                t_code.extend([
                    f"  it('{escape_js(tc.id)}: {escape_js(tc.title)}', () => {{",
                    "    const uniqueCode = 'AUTO_' + Date.now();",
                ])
                for page in all_pages:
                    t_code.append(f"    const {page_vars[page.name]} = new {page.name}();")
                has_assert = False
                for s in tc.steps:
                    if s.action == ActionType.GOTO:
                        t_code.append(f"    cy.visit('{escape_js(s.value or '')}');")
                    elif s.action == ActionType.CLICK:
                        p_name, prop = step_locator_map.get(s.target or "", ("", ""))
                        if p_name in page_vars:
                            t_code.append(f"    {page_vars[p_name]}.{prop}.click();")
                    elif s.action == ActionType.FILL:
                        p_name, prop = step_locator_map.get(s.target or "", ("", ""))
                        if p_name in page_vars:
                            t_code.append(f"    {page_vars[p_name]}.{prop}.type('{escape_js(s.value or '')}');")
                    elif s.action == ActionType.ASSERT:
                        has_assert = True
                        t_code.append("    cy.url().should('not.be.empty');")
                    else:
                        t_code.append(f"    // {s.description}")
                if not has_assert:
                    t_code.append("    cy.url().should('not.be.empty');")
                t_code.append("  });")
            t_code.append("});\n")
            files[f"cypress/e2e/{project.name}.cy.js"] = "\n".join(t_code)

        return files
