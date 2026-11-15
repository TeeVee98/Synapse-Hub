---
name: github-actions-templates
description: "Create production-ready GitHub Actions workflows for automated test suites and CI/CD. Use when wiring test pipelines, matrix shards, or quality gates into GitHub Actions."
category: architecture_and_analysis
version: "2.0.0"
policies:
  network: none
  shell: none
  filesystem: workspace-sandbox
---
# GitHub Actions CI/CD Patterns for Test Automation

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Use when configuring continuous integration pipelines, setting up multi-OS and multi-version test execution matrices, wiring quality gates into GitHub Actions, or generating automated test report artifacts.
- **Activation Scope:**
  - Automated test suites (Playwright, Pytest, Katalon, Newman).
  - Parallel matrix sharding across runners and execution stages.
  - Quality Gate Definition of Done (DoD) verification.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT use unpinned mutable tags (`@v4`, `@main`) for third-party actions; always pin to immutable 40-character commit SHAs.
  - Do NOT hardcode credentials or tokens in workflow files; inject secrets exclusively through repository secrets (`${{ secrets.TEST_TOKEN }}`).
  - Do NOT retain video and trace artifacts indefinitely; cap retention between 7 and 14 days.
- **Sibling Skill Boundaries:**
  - `verification-before-completion`: Enforces DoD evidence collection prior to declaring task completion.
  - `github-actions-templates` (this skill): Provides workflow blueprints, matrix sharding, and supply-chain-secure pipeline definitions.

---

## 3. Ordered Execution Workflow

### Phase 1: Workflow Configuration & Matrix Architecture

Author or update the CI/CD pipeline template (see reference `examples/matrix_test_pipeline.yml`).

<!-- classification: illustrative -->
```yaml
# Supply chain security: Pin actions to immutable full 40-character commit SHAs to mitigate tag hijacking and malicious upstream mutation risks.
name: Enterprise Automated E2E Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test-matrix:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        shard: [1/4, 2/4, 3/4, 4/4]

    steps:
      - name: Checkout Code
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - name: Setup Node.js
        uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a # v4.2.0
        with:
          node-version: 20
          cache: 'npm'

      - name: Install Dependencies
        run: npm ci

      - name: Install Playwright Browsers
        run: npx playwright install --with-deps chromium

      - name: Run Sharded Playwright Tests
        run: npx playwright test --shard=${{ matrix.shard }}

      - name: Upload Test Report & Screenshots
        if: always()
        uses: actions/upload-artifact@b4b15b8c7c6ac21ea08fcf65892d2ee8f75cf882 # v4.4.3
        with:
          name: playwright-report-shard-${{ strategy.job-index }}
          path: playwright-report/
          retention-days: 14
```

### Phase 2: Security & Supply Chain Invariants

1. **Dependency Pinning:** Pin all third-party GitHub Actions to 40-character commit SHAs with version comments to protect against compromised release tags.
2. **Secret Masking:** Never echo secrets into workflow steps; pass them as environment variables mapped from GitHub Secrets.
3. **Concurrency Governance:** Cancel stale runs on pull request updates:
   `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }`.

---

## 4. Verification Points & DoD

1. **Syntax Validation:** Workflow passes YAML linting and GitHub Actions schema checks.
2. **Commit SHA Pinning:** All `uses:` directives reference 40-character commit hashes with supply chain risk disclosures.
3. **Secret Protection:** 0 exposed secrets in step definitions, run scripts, or job logs.
4. **Execution Verification:** Pipeline successfully executes test matrix and uploads artifacts upon completion.

---

## 5. Handoff Protocol

- **Deliverables:** Production-ready `.github/workflows/*.yml` workflow definitions and example templates in `examples/`.
- **Next Subagent:** Pass to `test-runner` for local execution or `quality-gatekeeper` for CI/CD integration acceptance.
- **Output Format:** Valid GitHub Actions YAML syntax adhering to enterprise security baselines.
