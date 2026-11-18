# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
Deprecated compatibility shim for tools.traffic_session_converter.
The canonical implementation has moved to tools.transpiler.traffic_session_converter.
"""

from tools.transpiler import traffic_session_converter as _canonical_module

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
