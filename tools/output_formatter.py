#!/usr/bin/env python3
"""
Enterprise Standardized Output Formatter & Exit Code Specification
------------------------------------------------------------------
Provides centralized terminal styling, NO_COLOR standard compliance,
and deterministic exit codes across all Synapse Hub CLI tools.

Exit Code Standards:
  0: EXIT_SUCCESS           (Operation passed, DoD compliant)
  1: EXIT_FAILURE           (Test failure, linter defect, gate rejection)
  2: EXIT_USAGE_ERROR       (Invalid CLI arguments, syntax error)
  3: EXIT_SECURITY_BLOCK    (Destructive action blocked, secret leaked, MIT license altered)
  4: EXIT_ENVIRONMENT_ERROR (Missing required tool, incompatible runtime)
"""

import os
import sys
import json
from typing import Any

# Standard Exit Codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE_ERROR = 2
EXIT_SECURITY_BLOCK = 3
EXIT_ENVIRONMENT_ERROR = 4


def is_color_enabled() -> bool:
    """
    Determines if ANSI color codes should be rendered.
    Honors https://no-color.org specification (NO_COLOR env var).
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if os.environ.get("FORCE_COLOR") in ("1", "true", "TRUE"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class Colors:
    """ANSI color codes with dynamic NO_COLOR enforcement."""
    ESC = "\033"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @staticmethod
    def _c(code: str) -> str:
        return code if is_color_enabled() else ""

    @classmethod
    def cyan(cls, text: str) -> str:
        return f"{cls._c(cls.CYAN)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def green(cls, text: str) -> str:
        return f"{cls._c(cls.GREEN)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def yellow(cls, text: str) -> str:
        return f"{cls._c(cls.YELLOW)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def red(cls, text: str) -> str:
        return f"{cls._c(cls.RED)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def bold(cls, text: str) -> str:
        return f"{cls._c(cls.BOLD)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def dim(cls, text: str) -> str:
        return f"{cls._c(cls.DIM)}{text}{cls._c(cls.RESET)}"


class OutputFormatter:
    """Standardized console & machine-readable output renderer."""

    def __init__(self, quiet: bool = False, json_mode: bool = False):
        self.quiet = quiet
        self.json_mode = json_mode

    def header(self, title: str):
        if not self.quiet and not self.json_mode:
            border = "=" * 70
            print(f"\n{Colors.cyan(border)}")
            print(f"   {Colors.bold(title)}")
            print(f"{Colors.cyan(border)}\n")

    def step(self, current: int, total: int, title: str):
        if not self.quiet and not self.json_mode:
            print(f"{Colors.bold(f'[{current}/{total}]')} {title}")

    def pass_msg(self, message: str):
        if not self.json_mode:
            print(f"{Colors.green('✅ [PASS]')} {message}")

    def fail_msg(self, message: str):
        if not self.json_mode:
            print(f"{Colors.red('❌ [FAIL]')} {message}")

    def warn_msg(self, message: str):
        if not self.quiet and not self.json_mode:
            print(f"{Colors.yellow('⚠️  [WARN]')} {message}")

    def info_msg(self, message: str):
        if not self.quiet and not self.json_mode:
            print(f"{Colors.cyan('ℹ️  [INFO]')} {message}")

    def print_data(self, data: Any, format_type: str = "text"):
        if format_type == "json" or self.json_mode:
            if isinstance(data, (dict, list)):
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(str(data))
        else:
            print(str(data))


# Global default instance
console = OutputFormatter()
