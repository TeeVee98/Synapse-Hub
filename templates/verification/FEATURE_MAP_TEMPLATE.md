<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Feature Map: `<Feature Name>`

> **Purpose:** Document user-facing verification paths from a cold-start user point of view. Never weaken a journey to make it pass; missing preconditions belong in **Gotchas**.

## Sub-features

- `<Sub-feature A>`: `<1-line observable behavior>`
- `<Sub-feature B>`: `<1-line observable behavior>`

## How to get to it (user POV)

1. Navigate from `<entry route / menu / command>` using user-visible controls.
2. Reach `<target state>` without calling internal setters or test-only endpoints.

## Driving it with `<harness>`

- Prefer stable handles (ARIA roles/labels, `data-testid`, route paths) over coordinates or CSS classes.
- Capture both the triggering action and the resulting observable state (DOM attributes, network/RPC log, file/DB side effects, or reload round-trip).
- Preserve proof artifacts outside temporary teardown directories.

## Gotchas

- `<Precondition, gated flag, or non-deterministic streaming note>`
