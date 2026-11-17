#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Antigravity SessionStart Hook — Automated Upstream Drift & Update Sentinel
-------------------------------------------------------------------------
Invoked automatically by Antigravity on session initialization.
Checks upstream NPM registry / GitHub for newer Synapse Hub releases
and non-destructively synchronizes the agent environment.
Outputs strict JSON matching the Antigravity SessionStart hook contract.
"""

import os
import sys
import json

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
# Check both repo layout (.agents/hooks/..) and plugin layout
CANDIDATE_ROOTS = [
    os.path.abspath(os.path.join(CUR_DIR, "..", "..")),  # repo: root/tools/
    os.path.abspath(os.path.join(CUR_DIR, "..")),        # root/.agents/hooks
    os.path.abspath(CUR_DIR)
]

sentinel_found = False
for root in CANDIDATE_ROOTS:
    tools_dir = os.path.join(root, "tools")
    if os.path.isdir(tools_dir) and os.path.exists(os.path.join(tools_dir, "update_sentinel.py")):
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        try:
            import update_sentinel
            update_sentinel.run_auto_update_hook()
            sentinel_found = True
            break
        except Exception as err:
            sys.stderr.write(f"[session_start_hook] Error running update_sentinel: {err}\n")
            break

if not sentinel_found:
    # Failsafe fallback: output clean empty payload to never break Antigravity session
    print(json.dumps({"injectSteps": []}))
