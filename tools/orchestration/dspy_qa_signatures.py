# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Deprecated compatibility shim.
The canonical implementation has been renamed to tools.orchestration.typed_prompt_signatures.
"""

from tools.orchestration.typed_prompt_signatures import *  # noqa: F401, F403

if __name__ == "__main__":
    import sys
    from tools.orchestration.typed_prompt_signatures import main
    sys.exit(main())
