# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
tools/core/codemod_tool_imports.py
==================================
AST / Regex Codemod tool to update all legacy `tools.<tool>` imports and hardcoded
`tools/<tool>.py` paths to their canonical domain locations `tools.<domain>.<tool>`
across test suites and tools.
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
import sys
import re
import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
TESTS_DIR = os.path.join(REPO_ROOT, "tests")

# Load mapping from tools/__init__.py
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
import tools  # noqa: E402

TOOL_DOMAIN_MAP = tools._TOOL_DOMAIN_MAP
DOMAINS = set(tools._DOMAINS)


def refactor_file(file_path: str, dry_run: bool = False) -> int:
    """Refactors a single python file, returning number of replacements made."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    changes = 0

    # 1. Refactor `from tools.<tool> import ...`
    def repl_from(m):
        nonlocal changes
        tool_name = m.group(1)
        rest = m.group(2)
        if tool_name in TOOL_DOMAIN_MAP and tool_name not in DOMAINS:
            domain = TOOL_DOMAIN_MAP[tool_name]
            changes += 1
            return f"from tools.{domain}.{tool_name} import {rest}"
        return m.group(0)

    content = re.sub(r"from\s+tools\.(\w+)\s+import\s+([^\n]+)", repl_from, content)

    # 2. Refactor `import tools.<tool> as ...` or `import tools.<tool>`
    def repl_import(m):
        nonlocal changes
        tool_name = m.group(1)
        as_clause = m.group(2) or ""
        if tool_name in TOOL_DOMAIN_MAP and tool_name not in DOMAINS:
            domain = TOOL_DOMAIN_MAP[tool_name]
            changes += 1
            if as_clause:
                return f"import tools.{domain}.{tool_name}{as_clause}"
            return f"import tools.{domain}.{tool_name}"
        return m.group(0)

    content = re.sub(r"import\s+tools\.(\w+)(\s+as\s+\w+)?", repl_import, content)

    if content != original_content and not dry_run:
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    return changes


def refactor_test_paths(file_path: str, dry_run: bool = False) -> int:
    """Refactors test file hardcoded paths like 'tools/xyz.py' -> 'tools/<domain>/xyz.py'."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    changes = 0

    # Pattern: "tools/name.py" or 'tools/name.py' (or backslash)
    def repl_path(m):
        nonlocal changes
        quote = m.group(1)
        sep = m.group(2)
        name = m.group(3)
        if name in TOOL_DOMAIN_MAP and name not in DOMAINS:
            domain = TOOL_DOMAIN_MAP[name]
            changes += 1
            return f"{quote}tools{sep}{domain}{sep}{name}.py{quote}"
        return m.group(0)

    content = re.sub(r"([\"'])tools([\\/])(\w+)\.py([\"'])", repl_path, content)

    # Handle os.path.join(..., "tools", "name.py")
    def repl_join(m):
        nonlocal changes
        prefix = m.group(1)
        quote = m.group(2)
        name = m.group(3)
        if name in TOOL_DOMAIN_MAP and name not in DOMAINS:
            domain = TOOL_DOMAIN_MAP[name]
            changes += 1
            return f"{prefix}\"tools\", \"{domain}\", {quote}{name}.py{quote}"
        return m.group(0)

    content = re.sub(r"(os\.path\.join\([^)]*\"tools\",\s*)([\"'])(\w+)\.py([\"'])", repl_join, content)

    if content != original_content and not dry_run:
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    return changes


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Codemod tool imports and paths to domains.")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing.")
    args = parser.parse_args()

    total_import_changes = 0
    total_path_changes = 0

    target_files = []
    # Collect tests
    for f in glob.glob(os.path.join(TESTS_DIR, "**", "*.py"), recursive=True):
        target_files.append((f, True))

    # Collect domain tools (skip root tools/*.py which will be deleted)
    for root, dirs, files in os.walk(TOOLS_DIR):
        rel = os.path.relpath(root, TOOLS_DIR)
        if rel != "." and not rel.startswith("."):
            for f in files:
                if f.endswith(".py"):
                    target_files.append((os.path.join(root, f), False))

    print(f"Scanning {len(target_files)} target files...")

    for f_path, is_test in target_files:
        rel = os.path.relpath(f_path, REPO_ROOT)
        imp_ch = refactor_file(f_path, dry_run=args.dry_run)
        path_ch = 0
        if is_test:
            # We only refactor paths in test files where tests assert on files
            path_ch = refactor_test_paths(f_path, dry_run=args.dry_run)

        if imp_ch > 0 or path_ch > 0:
            print(f"  {rel}: {imp_ch} import changes, {path_ch} path changes")
            total_import_changes += imp_ch
            total_path_changes += path_ch

    print(f"\n[DONE] Total import replacements: {total_import_changes}")
    print(f"[DONE] Total path replacements: {total_path_changes}")


if __name__ == "__main__":
    main()
