---
name: bats-testing-patterns
description: "Test bash/sh scripts, CLI tools, and CI/CD pipelines with Bats. Use when writing Bash automation tests with the BATS framework."
category: test_automation_and_execution
version: "2.0.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Bats Testing Patterns (Bash Automated Testing System)

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Test bash/sh scripts, CLI tools, and CI/CD pipelines with Bats. Use when writing Bash automation tests with the BATS framework.
- **Activation Scope:** Domain workflows for `01-web-automation` involving `bats-testing-patterns`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT use BATS for deep browser UI testing; BATS is strictly for CLI, shell scripts, and system utilities.
- Do NOT rely on persistent local host environment state; all test fixtures must run in sandbox subshells.
- Do NOT suppress shell exit codes; assert on exact exit codes ($status) and command output ($output).
- **Sibling Skill Boundaries:**
  - katalon-cli-runner and playwright-webapp-testing handle web automation; bats-testing-patterns handles shell and CLI automation.

---

## 3. Ordered Execution Workflow

Comprehensive test engineering standard for validating shell scripts, CI/CD scripts (`.sh`), CLI wrappers, and DevOps automation using Bats-core.

---

### Core Principles

1. **Deterministic Exit Codes:** Every script assertion must explicitly assert `$status` (0 for success, non-zero for explicit failure vectors).
2. **Standard Output & Error Isolation:** Assert exact error strings in `${lines[@]}` or `$output`.
3. **Sandbox Filesystem:** Never mutate user home or production directories. Use `$BATS_TEST_TMPDIR` for all temporary files and fixtures.
4. **Mock External CLI Commands:** Intercept destructive CLI commands (`curl`, `docker`, `kubectl`, `git push`) by prepending a mock binary directory to `$PATH`.

---

### Standard Test Architecture & Setup

<!-- classification: illustrative -->
```bash
#!/usr/bin/env bats

setup() {
  # Load bats helper libraries if available
  load 'test_helper/bats-support/load' || true
  load 'test_helper/bats-assert/load' || true

  # Create an isolated sandbox directory per test
  TEST_DIR="$(mktemp -d "${BATS_TMPDIR}/bats_test.XXXXXX")"
  export TEST_DIR
  cd "$TEST_DIR"
}

teardown() {
  # Ensure clean sandbox teardown
  rm -rf "$TEST_DIR"
}
```

---

### Production Test Patterns

### Pattern A: Exit Code and Output Verification
<!-- classification: illustrative -->
```bash
@test "script fails gracefully when required parameter is missing" {
  run ./scripts/deploy.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "ERROR: Missing --target environment" ]]
}

@test "script outputs version correctly on --version flag" {
  run ./scripts/deploy.sh --version
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "deploy.sh version 2.4.0" ]
}
```

### Pattern B: Mocking Destructive CLI Tools
<!-- classification: illustrative -->
```bash
@test "mock curl API failure triggers automatic retry loop" {
  MOCK_DIR="${TEST_DIR}/bin"
  mkdir -p "$MOCK_DIR"

  # Create mock curl returning HTTP 503
  cat << 'EOF' > "${MOCK_DIR}/curl"
#!/bin/bash
echo "HTTP/1.1 503 Service Unavailable" >&2
exit 22
EOF
  chmod +x "${MOCK_DIR}/curl"

  # Prepend mock path
  PATH="${MOCK_DIR}:${PATH}" run ./scripts/sync_data.sh --retries 2
  [ "$status" -ne 0 ]
  [[ "$output" =~ "Retry attempt 2 failed" ]]
}
```

### Pattern C: File Creation & Mutation Verification
<!-- classification: illustrative -->
```bash
@test "script generates valid JSON report on completion" {
  run ./scripts/generate_report.sh --output "${TEST_DIR}/summary.json"
  [ "$status" -eq 0 ]
  [ -f "${TEST_DIR}/summary.json" ]
  run jq '.status' "${TEST_DIR}/summary.json"
  [ "$output" = '"SUCCESS"' ]
}
```

---

### CI/CD Pipeline Execution
<!-- classification: illustrative -->
```bash
# Execute full Bats test suite with JUnit report output for CI
bats test/*.bats --formatter junit > test-results.xml
```

---

## 4. Verification Points & DoD

1. All BATS test files (`.bats`) pass syntax check (`bats -c`).
2. Tests execute hermetically within temporary sandbox directories.
3. Exit status and stdout assertions validate real command behavior.

---

## 5. Handoff Protocol

- **Deliverables:** BATS test suites (`tests/*.bats`), helper libraries, and CI execution scripts.
- **Next Subagent:** test-runner / quality-gatekeeper
- **Output Format:** Executable `.bats` TAP test suites and CI shell assertion output.
