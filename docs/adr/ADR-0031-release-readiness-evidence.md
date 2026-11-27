<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0031. Evidence for release readiness across QA domains

**Status:** Accepted. **Date:** 2026-11-27. **Decision owners:** Hub maintainer and QA lead.

## Context

At audit baseline 7eb7208, a required suite containing only skipped cases could contribute to a passing verdict. An empty k6 summary could also satisfy the performance gate. A locally packed npm distribution could install the 57 catalog skills while omitting the three workflow skills. These observations affect the meaning of a release verdict and the client's ability to reproduce it.

## Decision

Keep the current test runners, command names and offline development mode. For release candidates require explicit, versioned evidence from the named build and environment. Model each required result as passed, failed or incomplete. Both failed and incomplete required results prevent certification. Store the evidence beside the run and record its digest in a candidate manifest.

Test the tarball that will be published in a clean project. Classify native host discovery, real-device execution, staging load and supervised accessibility according to the environment in which each was observed. Use stable document revision, requirement, case, run and build identifiers to connect evidence to the customer's report. Use optional local SQLite for recoverable single-coordinator worker state.

## Alternatives and consequences

A minimal reporter patch can ship first and limits immediate blast radius. A separate service would add deployment and migration costs before the pilot establishes demand. Extending existing producers requires agreement on identifiers, custody of evidence and handling of missing observations. Offline contributors keep a fast feedback path. Release owners must provide suitable infrastructure and retain human evidence when the claim depends on it.

## Adoption and reversal

The release lead rehearses a passing and an incomplete candidate and signs the capability scorecard. Revert individual integrations through their prior checkpoints. Hold release certification whenever required observations are unavailable. Acceptance and indexing occur during implementation.

