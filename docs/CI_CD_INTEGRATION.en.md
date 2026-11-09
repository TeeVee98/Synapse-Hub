# CI/CD Integration Guide — Synapse-Hub Enterprise QA

[🇻🇳 Tiếng Việt](CI_CD_INTEGRATION.md) | [🇬🇧 English Edition](CI_CD_INTEGRATION.en.md)

This guide explains how to integrate Synapse-Hub quality gates (`verify_all.py`, `infer_linter`, AST mutator, Clean POM checks) directly into target project CI/CD pipelines without local filesystem dependencies.

---

## 1. Zero-Install NPX Integration (Recommended)

Since `synapse-hub` is distributed via NPM Registry and GitHub Packages, target CI pipelines do not need to clone the hub repository manually. `npx` dynamically fetches and executes the CLI engine.

### GitHub Actions Workflow (`.github/workflows/synapse_qa.yml`)

```yaml
name: Synapse QA Quality Gate

on:
  push:
    branches: [ main, develop, master ]
  pull_request:
    branches: [ main, develop, master ]

jobs:
  quality-gate:
    name: 11 Quality Gates DoD Verification
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Project Source
        uses: actions/checkout@v4

      - name: Setup Node.js & Python
        uses: actions/setup-node@v4
        with:
          node-version: 20
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Verify 11 Quality Gates
        run: npx synapse-hub verify
```

### GitLab CI (`.gitlab-ci.yml`)

```yaml
synapse-qa-gate:
  stage: test
  image: node:20-bookworm
  before_script:
    - apt-get update && apt-get install -y python3 python3-pip
  script:
    - npx synapse-hub verify
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

---

## 2. Enterprise Docker Container Integration (All-in-One Image)

For zero-dependency CI/CD execution across air-gapped environments, Kubernetes, OpenShift, GitLab Runners, and Jenkins, use the official **Synapse-Hub All-in-One Container Image**:

- **Registry Image**: `ghcr.io/teevee998/synapse-hub:latest`
- **Bundled Runtimes**: Python 3.12, Node.js 20, OpenJDK Headless, Playwright/Chromium dependencies, Git, Bash.

### A. Standalone 1-Line Docker Execution

Mount your target test repository into `/workspace` and execute any Synapse Hub quality gate:

```bash
# Run 11 Quality Gates DoD Verification
docker run --rm -v $(pwd):/workspace ghcr.io/teevee998/synapse-hub verify

# Run Meta Infer-style AST Defect & Fake-Pass Linter
docker run --rm -v $(pwd):/workspace ghcr.io/teevee998/synapse-hub lint

# Run Comprehensive 5-in-1 Repository Health Audit
docker run --rm -v $(pwd):/workspace ghcr.io/teevee998/synapse-hub analyze
```

### B. GitLab CI (`.gitlab-ci.yml`) via Docker

```yaml
synapse-docker-gate:
  stage: test
  image:
    name: ghcr.io/teevee998/synapse-hub:latest
    entrypoint: [""]
  script:
    - synapse-hub verify
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### C. Jenkins Declarative Pipeline (`Jenkinsfile`)

```groovy
pipeline {
    agent {
        docker {
            image 'ghcr.io/teevee998/synapse-hub:latest'
            args '-v ${WORKSPACE}:/workspace'
        }
    }
    stages {
        stage('Quality Gate DoD') {
            steps {
                sh 'synapse-hub verify'
            }
        }
    }
}
```

### D. Docker Compose Developer Quickstart

Mount your local test project into `./target` and verify with zero host toolchain requirements:

```bash
# Run 11 Quality Gates DoD Verification
docker compose run --rm verify

# Run AST defect scanner
docker compose run --rm lint

# Launch interactive debugging shell
docker compose run --rm shell
```

---

## 3. Git Submodule Integration (For Air-Gapped / Private SCM)

If your enterprise network restricts public NPM registry access, mount `Synapse-Hub` as a Git Submodule inside the target repository:

```bash
# Add submodule into target project
git submodule add https://github.com/TeeVee998/Synapse-Hub.git .synapse-hub
```

In your CI pipeline:
```bash
git submodule update --init --recursive
python .synapse-hub/tools/verify_all.py
```

---

## 4. Python Git / Pip Package Integration

Target runners with Python 3.9+ can install `synapse-hub` directly from git:

```bash
pip install git+https://github.com/TeeVee998/Synapse-Hub.git
agent-qa verify
```

---

## 5. Available CI Subcommands

| NPX Command | Docker Command | Purpose | SLA / Exit Code |
| :--- | :--- | :--- | :--- |
| `npx synapse-hub verify` | `docker run --rm -v $(pwd):/workspace ghcr.io/teevee998/synapse-hub verify` | Executes all 11 Quality Gates DoD | Exits `0` if all PASS; non-zero if any FAIL. |
| `npx synapse-hub lint` | `docker run --rm -v $(pwd):/workspace ghcr.io/teevee998/synapse-hub lint` | Meta Infer-style static defect & fake-pass scan | Fails if 0-assert tests or empty catches exist. |
| `npx synapse-hub mutate --min-score 80` | `docker run --rm -v $(pwd):/workspace ghcr.io/teevee998/synapse-hub mutate --min-score 80` | Syntactic Micro-Mutation verification | Fails if test assertion score < 80%. |
| `npx synapse-hub analyze` | `docker run --rm -v $(pwd):/workspace ghcr.io/teevee998/synapse-hub analyze` | Comprehensive 5-in-1 health audit | Outputs health score and JSON/Markdown artifacts. |
