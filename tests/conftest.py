#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/conftest.py
-----------------
Pytest test harness configuration for Synapse Hub test suites.
Guarantees deterministic hermetic test execution with English fallback.
"""

import os

# Enforce deterministic English output during test execution across all environments
os.environ.setdefault("SYNAPSE_LANG", "en")
