# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — Universal Intermediate Representation (IR) Transpiler (tools.transpiler)
--------------------------------------------------------------------------------------
Domain package providing cross-language compilation between TypeScript,
Python, Groovy (Katalon), and Java test suites.
"""

from tools import (
    omni_emitter,
    omni_parser,
    omni_transpiler,
    universal_ir,
)

__all__ = [
    "omni_emitter",
    "omni_parser",
    "omni_transpiler",
    "universal_ir",
]
