# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
Deprecated compatibility shim for tools.visual_som_helper.
The canonical implementation has moved to tools.heal.visual_som_helper.
"""

from tools.heal import visual_som_helper as _canonical_module

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
