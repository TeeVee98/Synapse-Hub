---
name: gitlab-ci-templates
description: "Production GitLab CI/CD pipeline blueprints for test automation, Playwright matrix sharding, Katalon KRE execution, and artifact retention governance. Use when wiring test pipelines or quality gates into GitLab CI."
category: architecture_and_analysis
version: "1.0.0"
policies:
  network: none
  shell: read-only
  filesystem: workspace-sandbox
---
# GitLab CI/CD Templates for Test Automation

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Use when configuring GitLab CI/CD pipelines (`.gitlab-ci.yml`), creating parallel test execution matrices, setting up Katalon Runtime Engine (KRE) jobs, configuring dependency caching, or establishing artifact retention policies for test reports.
- **Activation Scope:**
  - Automated test suites (Playwright, Cypress, Katalon, Pytest).
  - Parallel matrix sharding across GitLab runners.
  - Quality Gate Definition of Done (DoD) verification.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT hardcode credentials, private tokens, or license keys in `.gitlab-ci.yml`; inject exclusively via GitLab CI/CD masked/protected variables (`$KATALON_API_KEY`, `$CI_JOB_TOKEN`).
  - Do NOT configure unlimited artifact retention; always set `expire_in: 7 days` (or max 14 days) to avoid saturating runner storage.
  - Do NOT leave runner processes hanging; always specify job-level `timeout: 30m`.
- **Sibling Skill Boundaries:**
  - `github-actions-templates`: Owns GitHub Actions workflows (`.github/workflows/*.yml`).
  - `gitlab-ci-templates` (this skill): Owns GitLab CI/CD pipeline definitions (`.gitlab-ci.yml`).
  - `jenkins-pipeline-templates`: Owns Jenkins Declarative Pipelines (`Jenkinsfile`).

---

## 3. Ordered Execution Workflow

### Phase 1: Pipeline Configuration & Parallel Sharding

Author or update the `.gitlab-ci.yml` pipeline configuration.

<!-- classification: illustrative -->
```yaml
stages:
  - test
  - report

default:
  interruptible: true
  timeout: 30m

# Cache dependencies across pipeline runs
.npm-cache: &npm-cache
  cache:
    key:
      files:
        - package-lock.json
    paths:
      - .npm/
    policy: pull-push

# Playwright Parallel Matrix Sharding
test:playwright:
  stage: test
  image: mcr.microsoft.com/playwright:v1.49.0-noble
  <<: *npm-cache
  parallel: 4
  before_script:
    - npm ci --cache .npm --prefer-offline
  script:
    - npx playwright test --shard=${CI_NODE_INDEX}/${CI_NODE_TOTAL}
  artifacts:
    when: always
    expire_in: 7 days
    paths:
      - playwright-report/
      - test-results/
    reports:
      junit: test-results/results.xml

# Katalon Runtime Engine (KRE) Headless Execution
test:katalon:
  stage: test
  image: katalonstudio/katalon:latest
  rules:
    - if: '$KATALON_API_KEY'
  script:
    - katalonc -noSplash -runMode=console -projectPath="$(pwd)/project.prj" -retry=0 -testSuitePath="Test Suites/TS_Smoke" -browserType="Chrome (headless)" -executionProfile="default" -apiKey="$KATALON_API_KEY"
  artifacts:
    when: always
    expire_in: 7 days
    paths:
      - Reports/
    reports:
      junit: Reports/**/JUnit_Report.xml
```

### Phase 2: Artifact & Storage Governance

1. **Selective Artifact Retention:** Always set `artifacts.expire_in: 7 days` for test traces, screenshots, and videos.
2. **Native JUnit Integration:** Map test result XML to `artifacts.reports.junit` for GitLab native test report parsing and MR telemetry.
3. **Fail-Fast & Timeout Controls:** Enforce `default.interruptible: true` to auto-cancel stale pipelines on push, and set explicit job timeouts.

---

## 4. Verification Points & DoD

1. **Syntax Validation:** `.gitlab-ci.yml` passes GitLab CI Lint API validation.
2. **Secret Protection:** Zero hardcoded API keys, passwords, or personal access tokens in pipeline YAML.
3. **Artifact Expiry:** Every job publishing artifacts defines an explicit `expire_in` policy ($\le 14$ days).
4. **Clean Execution:** All jobs complete with exit code 0 or cleanly capture JUnit XML on test assertion failure.

---

## 5. Handoff Protocol

- **Deliverables:** Production-ready `.gitlab-ci.yml` definitions and reusable job templates.
- **Next Subagent:** Pass to `test-runner` for runner validation or `quality-gatekeeper` for CI/CD acceptance.
- **Output Format:** Valid GitLab CI/CD YAML specification adhering to enterprise security baselines.
