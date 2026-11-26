#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Omni-Parser: Universal Polyglot AST & Structure Parser
------------------------------------------------------
Zero-Token deterministic parser supporting Java, TypeScript/JavaScript,
Python, Groovy (Katalon), and C#.
Extracts Page Classes, Locators, Action Methods, and Test Cases into
the Universal Intermediate Representation (universal_ir.ProjectIR).
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


import os
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from tools.transpiler.universal_ir import (
        ProjectIR, PageClassIR, TestCaseIR, MethodIR, StepIR, LocatorIR,
        ActionType, LocatorStrategy, AssertionType, WaitStrategy
    )
except ImportError:
    from universal_ir import (
        ProjectIR, PageClassIR, TestCaseIR, MethodIR, StepIR, LocatorIR,
        ActionType, LocatorStrategy, AssertionType, WaitStrategy
    )


def extract_quoted_string(match_groups: Tuple[Optional[str], Optional[str]]) -> str:
    """Helper to return the unescaped string from either double-quote or single-quote match."""
    g1, g2 = match_groups
    val = g1 if g1 else (g2 if g2 else "")
    return val.replace(r"\'", "'").replace(r'\"', '"')


class OmniParser:
    """Universal Zero-Token Polyglot Parser for Automation Codebases."""

    @staticmethod
    def detect_language_and_framework(file_path: str, content: str) -> Tuple[str, str]:
        ext = os.path.splitext(file_path)[1].lower()

        # Groovy / Katalon
        if ext == ".groovy":
            return "groovy", "katalon"

        # Java
        if ext == ".java":
            if "playwright" in content.lower():
                return "java", "playwright"
            if "restassured" in content.lower():
                return "java", "restassured"
            return "java", "selenium"

        # TypeScript / JavaScript
        if ext in [".ts", ".tsx", ".js", ".jsx"]:
            lang = "typescript" if "ts" in ext else "javascript"
            if "@playwright/test" in content or "page.locator" in content or "getByRole" in content:
                return lang, "playwright"
            if "cy." in content or "cypress" in content.lower():
                return lang, "cypress"
            if "webdriverio" in content.lower() or "browser.$" in content:
                return lang, "webdriverio"
            return lang, "playwright"

        # Python
        if ext == ".py":
            if "playwright" in content:
                return "python", "playwright"
            if "selenium" in content:
                return "python", "selenium"
            if "robot" in content.lower():
                return "python", "robot"
            return "python", "pytest"

        # C#
        if ext == ".cs":
            if "playwright" in content.lower():
                return "csharp", "playwright"
            return "csharp", "selenium"

        return "unknown", "generic"

    @classmethod
    def parse_code(cls, content: str, file_path: str = "virtual_file.ts") -> ProjectIR:
        """Parses in-memory automation code string into ProjectIR."""
        lang, framework = cls.detect_language_and_framework(file_path, content)
        basename = os.path.basename(file_path)
        raw_name = os.path.splitext(basename)[0]
        # Sanitize identifier: strip spec/test/e2e suffixes and invalid punctuation
        clean_name = re.sub(r'[\._-]?(?:e2e-spec|spec|test|cy)\b.*$', '', raw_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', clean_name).strip('_')
        if not clean_name:
            clean_name = "Generated"
        if clean_name[0].isdigit():
            clean_name = f"Mod_{clean_name}"
        sanitized_name = clean_name[0].upper() + clean_name[1:] if clean_name else "Generated"

        project = ProjectIR(
            name=sanitized_name,
            source_language=lang,
            source_framework=framework
        )

        if lang in ["typescript", "javascript"]:
            cls._parse_ts_js(content, project, framework)
        elif lang == "java":
            cls._parse_java(content, project, framework)
        elif lang == "groovy":
            cls._parse_groovy(content, project, framework)
        elif lang == "python":
            cls._parse_python(content, project, framework)
        elif lang == "csharp":
            cls._parse_csharp(content, project, framework)
        else:
            cls._parse_generic(content, project)

        return project

    @classmethod
    def parse_file(cls, file_path: str) -> ProjectIR:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return cls.parse_code(content, file_path)

    @staticmethod
    def _extract_brace_body(content: str, open_brace_idx: int) -> Tuple[str, int]:
        """Extracts a balanced `{ ... }` block skipping braces inside quotes and comments."""
        depth = 0
        n = len(content)
        in_single = False
        in_double = False
        in_backtick = False
        in_line_comment = False
        in_block_comment = False
        escaped = False
        i = open_brace_idx

        while i < n:
            ch = content[i]
            nxt = content[i + 1] if i + 1 < n else ""
            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                i += 1
                continue
            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if in_single or in_double or in_backtick:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif in_single and ch == "'":
                    in_single = False
                elif in_double and ch == '"':
                    in_double = False
                elif in_backtick and ch == "`":
                    in_backtick = False
                i += 1
                continue

            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if ch == "'":
                in_single = True
                i += 1
                continue
            if ch == '"':
                in_double = True
                i += 1
                continue
            if ch == "`":
                in_backtick = True
                i += 1
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return content[open_brace_idx + 1 : i], i
            i += 1
        return "", -1

    @staticmethod
    def _try_optional_tree_sitter(language: str, content: str) -> Optional[Any]:
        """Optional Tree-Sitter CST parse via pom_assertion_indexer when installed."""
        try:
            from tools.context.pom_assertion_indexer import load_optional_tree_sitter_parser

            parser = load_optional_tree_sitter_parser(language)
            if parser is not None:
                return parser.parse(content.encode("utf-8"))
        except Exception:
            return None
        return None

    @staticmethod
    def _extract_class_name_from_ts_tree(ts_tree: Any, content_bytes: bytes) -> Optional[str]:
        """Walks a Tree-Sitter CST root node to extract the primary class declaration identifier."""
        root = getattr(ts_tree, "root_node", None) if ts_tree is not None else None
        if root is None or getattr(root, "has_error", False):
            return None
        stack = list(reversed(getattr(root, "children", None) or []))
        while stack:
            node = stack.pop()
            if getattr(node, "type", "") in ("class_declaration", "abstract_class_declaration"):
                cbf = getattr(node, "child_by_field_name", None)
                name_node = cbf("name") if callable(cbf) else None
                if name_node is not None:
                    raw = content_bytes[int(name_node.start_byte) : int(name_node.end_byte)].decode(
                        "utf-8", errors="replace"
                    ).strip()
                    if raw:
                        return raw
            for ch in reversed(getattr(node, "children", None) or []):
                stack.append(ch)
        return None

    # -------------------------------------------------------------------------
    # TypeScript / JavaScript Parser
    # -------------------------------------------------------------------------
    @classmethod
    def _parse_ts_js(cls, content: str, project: ProjectIR, framework: str):
        ts_tree = cls._try_optional_tree_sitter("typescript", content)
        ast_cls_name = cls._extract_class_name_from_ts_tree(ts_tree, content.encode("utf-8"))
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?", content)
        page_name = ast_cls_name or (class_match.group(1) if class_match else f"{project.name}Page")
        base_class = class_match.group(2) if (class_match and class_match.group(2)) else "BasePage"

        page = PageClassIR(name=page_name, base_class=base_class)
        locators: Dict[str, LocatorIR] = {}

        # 1. Playwright getByRole
        role_matches = re.finditer(
            r"(?:readonly\s+)?(?:this\.)?([A-Za-z0-9_$]+)\s*=\s*(?:this\.)?page\.getByRole\(\s*(?:\"([^\"]*)\"|'([^']*)')(?:\s+as\s+[A-Za-z0-9_]+)?\s*,\s*\{\s*name:\s*(?:\"([^\"]*)\"|'([^']*)')\s*\}\s*\)",
            content
        )
        for m in role_matches:
            loc_name = m.group(1)
            role_type = extract_quoted_string((m.group(2), m.group(3)))
            acc_name = extract_quoted_string((m.group(4), m.group(5)))
            locators[loc_name] = LocatorIR(name=loc_name, strategy=LocatorStrategy.ROLE, value=f"{role_type}[name='{acc_name}']")

        # 2. Playwright getByTestId
        tid_matches = re.finditer(
            r"(?:readonly\s+)?(?:this\.)?([A-Za-z0-9_$]+)\s*=\s*(?:this\.)?page\.getByTestId\(\s*(?:\"([^\"]*)\"|'([^']*)')\s*\)",
            content
        )
        for m in tid_matches:
            loc_name = m.group(1)
            val = extract_quoted_string((m.group(2), m.group(3)))
            locators[loc_name] = LocatorIR(name=loc_name, strategy=LocatorStrategy.TEST_ID, value=val)

        # 3. Playwright getByLabel
        label_matches = re.finditer(
            r"(?:readonly\s+)?(?:this\.)?([A-Za-z0-9_$]+)\s*=\s*(?:this\.)?page\.getByLabel\(\s*(?:\"([^\"]*)\"|'([^']*)')\s*\)",
            content
        )
        for m in label_matches:
            loc_name = m.group(1)
            val = extract_quoted_string((m.group(2), m.group(3)))
            locators[loc_name] = LocatorIR(name=loc_name, strategy=LocatorStrategy.LABEL, value=val)

        # 4. Playwright page.locator('...')
        loc_matches = re.finditer(
            r"""(?:readonly\s+)?(?:this\.)?([A-Za-z0-9_$]+)\s*=\s*(?:this\.)?page\.locator\(\s*(?:\"((?:[^"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)')\s*\)""",
            content
        )
        for m in loc_matches:
            loc_name = m.group(1)
            selector = extract_quoted_string((m.group(2), m.group(3)))
            strat = LocatorStrategy.XPATH if selector.startswith(("//", "(//")) else LocatorStrategy.CSS
            locators[loc_name] = LocatorIR(name=loc_name, strategy=strat, value=selector)

        page.locators = list(locators.values())

        # Methods (brace-scoped multiline extraction supporting nested blocks)
        ts_method_re = re.compile(
            r"(?m)^[ \t]*(?:(?:public|private|protected|static|override)\s+)*(async\s+)?([A-Za-z0-9_$]+)\s*\(([^)]*)\)\s*(?::\s*[^\{;]+)?\s*\{"
        )
        ts_skip = {"constructor", "if", "for", "while", "switch", "catch", "function", "test", "it", "describe"}
        for m in ts_method_re.finditer(content):
            m_name = m.group(2)
            params_str = m.group(3)
            if m_name in ts_skip:
                continue
            open_idx = content.rfind("{", m.start(), m.end())
            body, _ = cls._extract_brace_body(content, open_idx)
            if not body:
                continue
            params = [p.strip().split(":")[0].strip() for p in params_str.split(",") if p.strip()]
            steps = cls._extract_steps_from_body(body)
            page.methods.append(MethodIR(name=m_name, parameters=params, steps=steps))

        project.pages.append(page)

        # Test cases (Playwright `test(...)` or Cypress / Mocha `it(...)`, brace-scoped)
        ts_test_re = re.compile(
            r"(?:test|it)(?:\.only|\.skip)?\s*\(\s*(?:\"([^\"]*)\"|'([^']*)')\s*,\s*(?:async\s*)?(?:\([^)]*\)|function\s*\([^)]*\))\s*=>?\s*\{"
        )
        for idx, tm in enumerate(ts_test_re.finditer(content), 1):
            t_title = tm.group(1) if tm.group(1) else tm.group(2)
            open_idx = content.rfind("{", tm.start(), tm.end())
            t_body, _ = cls._extract_brace_body(content, open_idx)
            steps = cls._extract_steps_from_body(t_body)
            project.test_cases.append(TestCaseIR(id=f"TC_{idx:03d}", title=t_title, steps=steps))

    # -------------------------------------------------------------------------
    # Java Parser (Selenium & Playwright)
    # -------------------------------------------------------------------------
    @classmethod
    def _parse_java(cls, content: str, project: ProjectIR, framework: str):
        cls._try_optional_tree_sitter("java", content)
        class_match = re.search(r"public\s+class\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?", content)
        page_name = class_match.group(1) if class_match else f"{project.name}Page"
        base_class = class_match.group(2) if (class_match and class_match.group(2)) else "BasePage"

        page = PageClassIR(name=page_name, base_class=base_class)
        locators: Dict[str, LocatorIR] = {}

        # 1. Selenium @FindBy annotations
        findby_matches = re.finditer(
            r"@FindBy\s*\(\s*([a-zA-Z0-9_]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')\s*\)\s*(?:(?:private|public|protected|static|final)\s+)*(?:WebElement|List<WebElement>)\s+([A-Za-z0-9_]+);",
            content
        )
        for m in findby_matches:
            by_type = m.group(1).lower()
            selector = extract_quoted_string((m.group(2), m.group(3)))
            var_name = m.group(4)
            strat = LocatorStrategy.XPATH if by_type == "xpath" else (LocatorStrategy.ID if by_type == "id" else LocatorStrategy.CSS)
            locators[var_name] = LocatorIR(name=var_name, strategy=strat, value=selector)

        # 2. By locators
        by_matches = re.finditer(
            r"(?:(?:private|public|protected|static|final)\s+)*By\s+([A-Za-z0-9_]+)\s*=\s*By\.([a-zA-Z0-9_]+)\s*\(\s*(?:\"([^\"]*)\"|'([^']*)')\s*\);",
            content
        )
        for m in by_matches:
            var_name = m.group(1)
            by_type = m.group(2).lower()
            selector = extract_quoted_string((m.group(3), m.group(4)))
            strat = LocatorStrategy.XPATH if "xpath" in by_type else (LocatorStrategy.ID if "id" in by_type else LocatorStrategy.CSS)
            locators[var_name] = LocatorIR(name=var_name, strategy=strat, value=selector)

        page.locators = list(locators.values())

        # 3. Methods (brace-scoped multiline extraction)
        java_method_re = re.compile(
            r"(?:public|protected|private)\s+([A-Za-z0-9_<>\s]+?)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(?:throws\s+[A-Za-z0-9_,\s]+)?\s*\{"
        )
        for m in java_method_re.finditer(content):
            ret_type = m.group(1)
            m_name = m.group(2)
            params_str = m.group(3)
            if m_name == page_name:
                continue
            open_idx = content.rfind("{", m.start(), m.end())
            body, _ = cls._extract_brace_body(content, open_idx)
            if not body:
                continue
            params = [p.strip().split()[-1] for p in params_str.split(",") if p.strip()]
            steps = cls._extract_steps_from_body(body)
            page.methods.append(MethodIR(name=m_name, parameters=params, return_type=ret_type.strip(), steps=steps))

        project.pages.append(page)

        # 4. TestNG / JUnit (brace-scoped)
        java_test_re = re.compile(r"@Test[^\n]*\s*(?:public|void|\s)+([A-Za-z0-9_]+)\s*\([^)]*\)[^{]*\{")
        for idx, tm in enumerate(java_test_re.finditer(content), 1):
            t_name = tm.group(1)
            open_idx = content.rfind("{", tm.start(), tm.end())
            t_body, _ = cls._extract_brace_body(content, open_idx)
            steps = cls._extract_steps_from_body(t_body)
            project.test_cases.append(TestCaseIR(id=f"TC_{idx:03d}", title=t_name, steps=steps))

    # -------------------------------------------------------------------------
    # Groovy / Katalon Parser (Clean POM Flat Architecture)
    # -------------------------------------------------------------------------
    @classmethod
    def _parse_groovy(cls, content: str, project: ProjectIR, framework: str):
        cls._try_optional_tree_sitter("groovy", content)
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?", content)
        page_name = class_match.group(1) if class_match else f"{project.name}Page"
        base_class = class_match.group(2) if (class_match and class_match.group(2)) else "BasePage"

        page = PageClassIR(name=page_name, base_class=base_class)
        locators: Dict[str, LocatorIR] = {}

        # Extract static final String XPaths
        xpath_matches = re.finditer(
            r"(?:(?:public|private|protected|static|final)\s+)*(?:String|def)\s+([A-Za-z0-9_]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')",
            content
        )
        for m in xpath_matches:
            var_name = m.group(1)
            selector = extract_quoted_string((m.group(2), m.group(3)))
            strat = LocatorStrategy.XPATH if selector.startswith(("//", "(//")) else LocatorStrategy.CSS
            locators[var_name] = LocatorIR(name=var_name, strategy=strat, value=selector)

        page.locators = list(locators.values())

        # Methods (brace-scoped multiline extraction)
        groovy_method_re = re.compile(
            r"(?m)^[ \t]*(?:(?:public|private|protected|def|static|void|[A-Za-z0-9_<>]+)\s+)+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*\{"
        )
        for m in groovy_method_re.finditer(content):
            m_name = m.group(1)
            params_str = m.group(2)
            if m_name in [page_name, "main", "if", "for", "while", "switch", "catch"]:
                continue
            open_idx = content.rfind("{", m.start(), m.end())
            body, _ = cls._extract_brace_body(content, open_idx)
            if not body:
                continue
            params = [p.strip().split()[-1] for p in params_str.split(",") if p.strip()]
            steps = cls._extract_steps_from_body(body)
            page.methods.append(MethodIR(name=m_name, parameters=params, steps=steps))

        project.pages.append(page)

        if not class_match:
            steps = cls._extract_steps_from_body(content)
            project.test_cases.append(TestCaseIR(id="TC_001", title=project.name, steps=steps))

    # -------------------------------------------------------------------------
    # Python Parser (Pytest / Playwright / Selenium)
    # -------------------------------------------------------------------------
    @classmethod
    def _parse_python(cls, content: str, project: ProjectIR, framework: str):
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)(?:\(([^)]+)\))?:", content)
        page_name = class_match.group(1) if class_match else f"{project.name}Page"
        base_class = class_match.group(2) if (class_match and class_match.group(2)) else "BasePage"

        page = PageClassIR(name=page_name, base_class=base_class)
        locators: Dict[str, LocatorIR] = {}

        loc_matches = re.finditer(
            r"self\.([a-zA-Z0-9_]+)\s*=\s*(?:self\.)?page\.locator\(\s*(?:\"([^\"]*)\"|'([^']*)')\s*\)",
            content
        )
        for m in loc_matches:
            name = m.group(1)
            sel = extract_quoted_string((m.group(2), m.group(3)))
            strat = LocatorStrategy.XPATH if sel.startswith(("//", "(//")) else LocatorStrategy.CSS
            locators[name] = LocatorIR(name=name, strategy=strat, value=sel)

        role_matches = re.finditer(
            r"self\.([a-zA-Z0-9_]+)\s*=\s*(?:self\.)?page\.get_by_role\(\s*(?:\"([^\"]*)\"|'([^']*)')\s*,\s*name=(?:\"([^\"]*)\"|'([^']*)')\s*\)",
            content
        )
        for m in role_matches:
            name = m.group(1)
            r_type = extract_quoted_string((m.group(2), m.group(3)))
            r_name = extract_quoted_string((m.group(4), m.group(5)))
            locators[name] = LocatorIR(name=name, strategy=LocatorStrategy.ROLE, value=f"{r_type}[name='{r_name}']")

        page.locators = list(locators.values())

        func_blocks = re.findall(r"def\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?:(.*?)(?=\n\s*def\s+|\Z)", content, re.DOTALL)
        for f_name, f_params, f_body in func_blocks:
            if f_name.startswith("test_"):
                steps = cls._extract_steps_from_body(f_body)
                project.test_cases.append(TestCaseIR(id=f"TC_{len(project.test_cases)+1:03d}", title=f_name, steps=steps))
            elif f_name != "__init__":
                params = [p.strip().split(":")[0].strip() for p in f_params.split(",") if p.strip() and p.strip() != "self"]
                steps = cls._extract_steps_from_body(f_body)
                page.methods.append(MethodIR(name=f_name, parameters=params, steps=steps))

        project.pages.append(page)

    # -------------------------------------------------------------------------
    # C# Parser (.NET Selenium / Playwright)
    # -------------------------------------------------------------------------
    @classmethod
    def _parse_csharp(cls, content: str, project: ProjectIR, framework: str):
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)(?:\s*:\s*([A-Za-z0-9_]+))?", content)
        page_name = class_match.group(1) if class_match else f"{project.name}Page"
        base_class = class_match.group(2) if (class_match and class_match.group(2)) else "BasePage"

        page = PageClassIR(name=page_name, base_class=base_class)
        project.pages.append(page)

    # -------------------------------------------------------------------------
    # Generic Fallback Parser
    # -------------------------------------------------------------------------
    @classmethod
    def _parse_generic(cls, content: str, project: ProjectIR):
        page = PageClassIR(name=f"{project.name}Page")
        steps = cls._extract_steps_from_body(content)
        project.test_cases.append(TestCaseIR(id="TC_001", title=project.name, steps=steps))
        project.pages.append(page)

    # -------------------------------------------------------------------------
    # Universal Step Extractor (With Async/Sync Bridge & Antipattern Sanitizer)
    # -------------------------------------------------------------------------
    @classmethod
    def _extract_steps_from_body(cls, body: str) -> List[StepIR]:
        steps: List[StepIR] = []
        # Unroll Cypress .then() closures into sequential lines
        normalized_body = re.sub(r"\.then\s*\(\s*\([^)]*\)\s*=>\s*\{?", "\n", body)

        for line in normalized_body.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith(("//", "#", "/*", "*")) or line_str in ["}", "});"]:
                continue

            # 0. Detect Hardcoded Sleep Antipatterns (Thread.sleep, WebUI.delay, cy.wait, time.sleep)
            sleep_m = re.search(r"(?:Thread\.sleep|WebUI\.delay|time\.sleep|cy\.wait)\s*\(\s*(\d+)\s*\)", line_str, re.IGNORECASE)
            if sleep_m:
                sleep_val = int(sleep_m.group(1))
                ms = sleep_val * 1000 if sleep_val <= 60 else sleep_val  # WebUI.delay(3) vs Thread.sleep(3000)
                steps.append(StepIR(
                    action=ActionType.WAIT,
                    wait_strategy=WaitStrategy.STATIC_SLEEP,
                    is_sanitized_wait=True,
                    timeout_ms=ms,
                    description=f"Auto-healed from static sleep {line_str}"
                ))
                continue

            # 1. Cypress Command Chaining: cy.get('selector').action(...)
            cy_chain = re.search(r"cy\.get\(\s*(?:\"([^\"]*)\"|'([^']*)')\s*\)\s*\.\s*(click|type|clear|should)\s*\(([^)]*)\)", line_str, re.IGNORECASE)
            if cy_chain:
                sel = extract_quoted_string((cy_chain.group(1), cy_chain.group(2)))
                cy_act = cy_chain.group(3).lower()
                cy_args = cy_chain.group(4)
                if cy_act == "click":
                    steps.append(StepIR(action=ActionType.CLICK, target=sel, description=f"Cypress click on {sel}"))
                elif cy_act in ["type", "clear"]:
                    m_type = re.search(r"(?:\"([^\"]*)\"|'([^']*)')", cy_args)
                    type_val = extract_quoted_string((m_type.group(1), m_type.group(2))) if m_type else ""
                    steps.append(StepIR(action=ActionType.FILL, target=sel, value=type_val, description=f"Cypress type on {sel}"))
                elif cy_act == "should":
                    steps.append(StepIR(action=ActionType.ASSERT, target=sel, assertion_type=AssertionType.VISIBLE, description=line_str))
                continue

            # 2. Navigation
            nav_m = re.search(r"(?:goto|navigate|openBrowser|navigateToUrl|visit|get)\s*\(\s*(?:\"([^\"]*)\"|'([^']*)')\s*\)", line_str, re.IGNORECASE)
            if nav_m:
                val = extract_quoted_string((nav_m.group(1), nav_m.group(2)))
                steps.append(StepIR(action=ActionType.GOTO, value=val, description=f"Navigate to {val}"))
                continue

            # 3. Click
            click_m = re.search(r"(?:click|clickJS)\s*\(\s*(?:(?:\"([^\"]*)\"|'([^']*)')|([A-Za-z0-9_$.]+))?\s*\)", line_str, re.IGNORECASE)
            if click_m:
                target = extract_quoted_string((click_m.group(1), click_m.group(2))) or click_m.group(3) or "element"
                target_clean = target.replace("this.", "").replace("self.", "")
                steps.append(StepIR(action=ActionType.CLICK, target=target_clean, description=f"Click on {target_clean}"))
                continue

            # 4. Fill
            fill_m = re.search(r"(?:fill|sendKeys|setText|type)\s*\(\s*(?:([A-Za-z0-9_$.]+)\s*,\s*)?(?:\"([^\"]*)\"|'([^']*)')\s*\)", line_str, re.IGNORECASE)
            if fill_m:
                target = fill_m.group(1) or "input"
                val = extract_quoted_string((fill_m.group(2), fill_m.group(3)))
                target_clean = target.replace("this.", "").replace("self.", "")
                steps.append(StepIR(action=ActionType.FILL, target=target_clean, value=val, description=f"Fill {val} into {target_clean}"))
                continue

            # 5. Assertions
            if any(k in line_str for k in ["expect", "Assert.", "verify", "should("]):
                if "visible" in line_str.lower() or "present" in line_str.lower():
                    steps.append(StepIR(action=ActionType.ASSERT, assertion_type=AssertionType.VISIBLE, description=line_str))
                elif "equal" in line_str.lower() or "match" in line_str.lower():
                    steps.append(StepIR(action=ActionType.ASSERT, assertion_type=AssertionType.EQUALS, description=line_str))
                else:
                    steps.append(StepIR(action=ActionType.ASSERT, description=line_str))
                continue

            if "(" in line_str and ")" in line_str:
                steps.append(StepIR(action=ActionType.CUSTOM_CALL, description=line_str))

        return steps
