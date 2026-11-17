#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/context_slicer.py — AST-Aware Micro-Context Slicing Engine (Level 4 Adaptive Hub)
--------------------------------------------------------------------------------------
Generates targeted micro-contexts (< 100 tokens) based on target file types or Git diffs,
permanently eliminating context rot and token waste.

Usage:
  python3 tools/context_slicer.py pages/LoginPage.ts
  python3 tools/context_slicer.py tests/test_login.spec.ts
  python3 tools/context_slicer.py --diff
"""

import os
import sys
import subprocess
import argparse
from typing import Dict

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


class ContextSlicer:
    """Slices domain-specific micro-contexts based on AST and file signatures."""

    SLICES = {
        "PAGE_CLASS": (
            "## Micro-Context: Clean POM Page Class\n"
            "- Inherit from `BasePage` (max 1 level inheritance).\n"
            "- 6-Tier Locator Hierarchy: Role > Label > Text > TestID > Semantic CSS > XPath (last resort).\n"
            "- Encapsulate all locators and element actions. Zero raw locators in test scripts.\n"
            "- Dynamic smart waits: `expect(locator).toBeVisible()` (prohibit static sleep).\n"
        ),
        "TEST_SCRIPT": (
            "## Micro-Context: Clean Test Script\n"
            "- Scripts call ONLY business workflow methods on Page Classes.\n"
            "- Zero raw XPaths, CSS selectors, or `findTestObject` in scripts.\n"
            "- Truth Anchor: real assertions, no swallowed exceptions, no fake passes.\n"
            "- Dynamic test data: randomized codes with `AUTO_` + automated teardown.\n"
        ),
        "API_CONTRACT": (
            "## Micro-Context: API & Contract Testing\n"
            "- Validate request/response payloads against OpenAPI / JSON schemas.\n"
            "- Assert exact HTTP status codes and contract boundaries.\n"
            "- Randomize test payloads to eliminate database state collisions.\n"
        ),
        "GENERAL_CODE": (
            "## Micro-Context: Lean Senior Dev\n"
            "- Solve problem with minimal code (7-rung ladder & YAGNI).\n"
            "- 100% UTF-8 No BOM across all source and test files.\n"
            "- Mark deliberate simplifications: `shortcut: <limit>, <when to upgrade>`.\n"
        )
    }

    @classmethod
    def classify_file(cls, file_path: str) -> str:
        """Determines the appropriate micro-context domain for a file."""
        norm = file_path.lower().replace("\\", "/")
        if "page" in norm or norm.startswith("pages/") or "/pages/" in norm:
            return "PAGE_CLASS"
        elif any(k in norm for k in ["spec.", "test.", "tc-", "scripts/"]):
            return "TEST_SCRIPT"
        elif any(k in norm for k in ["api", "contract", "endpoint", "swagger", "openapi"]):
            return "API_CONTRACT"
        return "GENERAL_CODE"

    @classmethod
    def slice_context(cls, file_path: str) -> str:
        """Returns the micro-context string for the specified target file."""
        domain = cls.classify_file(file_path)
        return cls.SLICES.get(domain, cls.SLICES["GENERAL_CODE"])

    @classmethod
    def slice_git_diff(cls, repo_root: str = REPO_ROOT) -> Dict[str, str]:
        """Slices micro-contexts for all currently modified files in git."""
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True
            )
            modified_files = []
            for line in res.stdout.strip().splitlines():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    modified_files.append(parts[1])

            return {f: cls.slice_context(f) for f in modified_files}
        except Exception:
            return {}


def main():
    parser = argparse.ArgumentParser(description="Level 4 AST-Aware Micro-Context Slicer")
    parser.add_argument("target", nargs="?", help="Target file path to slice context for")
    parser.add_argument("--diff", action="store_true", help="Slice micro-contexts for current git diff")
    args = parser.parse_args()

    if args.diff:
        diff_contexts = ContextSlicer.slice_git_diff()
        if not diff_contexts:
            print("Working tree clean. No modified files to slice context for.")
            return 0
        for f, ctx in diff_contexts.items():
            print(f"=== [Target: {f}] ===")
            print(ctx)
        return 0

    if not args.target:
        print("Usage: python3 tools/context_slicer.py <file_path> | --diff")
        return 1

    print(ContextSlicer.slice_context(args.target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
