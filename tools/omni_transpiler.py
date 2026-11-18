# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
Deprecated compatibility shim for tools.omni_transpiler.
The canonical implementation has moved to tools.transpiler.omni_transpiler.
"""

from tools.transpiler import omni_transpiler as _canonical_module

for _attr in dir(_canonical_module):
    if not _attr.startswith("__"):
        globals()[_attr] = getattr(_canonical_module, _attr)

if __name__ == "__main__":
    import sys
    try:
        main = getattr(_canonical_module, "main", None)
        if callable(main):
            sys.exit(main())
    except (ImportError, AttributeError):  # synapse-ignore: SWALLOWED_EXCEPTION
        pass
