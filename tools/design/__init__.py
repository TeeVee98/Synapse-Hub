# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — DESIGN Package (tools.design)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.design import break_ui_generator
from tools.design import mechanical_ui_gate
from tools.design import smart_visual_masker
from tools.design import visual_diff_canvas

__all__ = [
    "break_ui_generator",
    "mechanical_ui_gate",
    "smart_visual_masker",
    "visual_diff_canvas"
]
