# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Deprecated compatibility shim.
The canonical implementation has been renamed to tools.heal.ast_assertion_optimizer.
"""

from tools.heal.ast_assertion_optimizer import *  # noqa: F401, F403

if __name__ == "__main__":
    import sys
    from tools.heal.ast_assertion_optimizer import main
    sys.exit(main())
