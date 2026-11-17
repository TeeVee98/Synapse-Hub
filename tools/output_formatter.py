#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

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
import logging
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
        """Wraps text with ANSI cyan color if color output is enabled."""
        return f"{cls._c(cls.CYAN)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def green(cls, text: str) -> str:
        """Wraps text with ANSI green color if color output is enabled."""
        return f"{cls._c(cls.GREEN)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def yellow(cls, text: str) -> str:
        """Wraps text with ANSI yellow color if color output is enabled."""
        return f"{cls._c(cls.YELLOW)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def red(cls, text: str) -> str:
        """Wraps text with ANSI red color if color output is enabled."""
        return f"{cls._c(cls.RED)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def bold(cls, text: str) -> str:
        """Wraps text with ANSI bold weight if color output is enabled."""
        return f"{cls._c(cls.BOLD)}{text}{cls._c(cls.RESET)}"

    @classmethod
    def dim(cls, text: str) -> str:
        """Wraps text with ANSI dim intensity if color output is enabled."""
        return f"{cls._c(cls.DIM)}{text}{cls._c(cls.RESET)}"


class OutputFormatter:
    """Standardized console & machine-readable output renderer."""

    def __init__(self, quiet: bool = False, json_mode: bool = False, verbose: bool = False):
        """Initializes the output formatter with verbosity and mode toggles."""
        self.quiet = quiet
        self.json_mode = json_mode
        self.verbose = verbose

    def debug(self, message: str):
        """Prints a debug message when verbose mode is active."""
        if self.verbose and not self.quiet and not self.json_mode:
            print(f"{Colors.dim('🔍 [DEBUG]')} {message}")

    def info(self, message: str):
        """Alias for info_msg printing informational text."""
        self.info_msg(message)

    def warn(self, message: str):
        """Alias for warn_msg printing warning text."""
        self.warn_msg(message)

    def error(self, message: str):
        """Alias for fail_msg printing failure/error text."""
        self.fail_msg(message)

    def success(self, message: str):
        """Alias for pass_msg printing passing/success text."""
        self.pass_msg(message)

    def header(self, title: str):
        """Renders an eye-catching framed header box for CLI stages."""
        if not self.quiet and not self.json_mode:
            border = "=" * 70
            print(f"\n{Colors.cyan(border)}")
            print(f"   {Colors.bold(title)}")
            print(f"{Colors.cyan(border)}\n")

    def step(self, current: int, total: int, title: str):
        """Prints a numbered step indicator for multi-phase operations."""
        if not self.quiet and not self.json_mode:
            print(f"{Colors.bold(f'[{current}/{total}]')} {title}")

    def pass_msg(self, message: str):
        """Prints a green checkmark pass badge with the given message."""
        if not self.json_mode:
            print(f"{Colors.green('✅ [PASS]')} {message}")

    def fail_msg(self, message: str):
        """Prints a red cross fail badge with the given message."""
        if not self.json_mode:
            print(f"{Colors.red('❌ [FAIL]')} {message}")

    def warn_msg(self, message: str):
        """Prints a yellow warning badge with the given message."""
        if not self.quiet and not self.json_mode:
            print(f"{Colors.yellow('⚠️  [WARN]')} {message}")

    def info_msg(self, message: str):
        """Prints a cyan informational badge with the given message."""
        if not self.quiet and not self.json_mode:
            print(f"{Colors.cyan('ℹ️  [INFO]')} {message}")

    def print_data(self, data: Any, format_type: str = "text"):
        """Formats and outputs data payload as either indented JSON or raw text."""
        if format_type == "json" or self.json_mode:
            if isinstance(data, (dict, list)):
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(str(data))
        else:
            print(str(data))


def get_logger(name: str = "synapse", verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """Creates or returns a standard logging.Logger configured with Synapse formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        fmt = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    if quiet:
        logger.setLevel(logging.ERROR)
    elif verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    return logger


# Global default instance
console = OutputFormatter()
