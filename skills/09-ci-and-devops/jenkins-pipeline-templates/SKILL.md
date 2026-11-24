---
name: jenkins-pipeline-templates
description: "Enterprise Jenkins Declarative Pipeline templates for test automation, parallel stages, Katalon KRE runner, JUnit reporting, and workspace hygiene. Use when configuring Jenkins pipelines or quality gates."
category: architecture_and_analysis
version: "1.0.0"
policies:
  network: none
  shell: read-only
  filesystem: workspace-sandbox
---
# Jenkins Pipeline Templates for Test Automation

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Use when creating or standardizing Jenkins Declarative Pipelines (`Jenkinsfile`), configuring parallel execution stages across agent nodes, integrating Katalon Runtime Engine (KRE), publishing JUnit/HTML test results, or implementing workspace cleanup routines.
- **Activation Scope:**
  - Automated test pipelines (Playwright, Cypress, Katalon, Pytest, Newman).
  - Parallel execution across Jenkins agent nodes.
  - Quality Gate Definition of Done (DoD) verification and post-build actions.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT use Scripted Pipeline syntax (`node { ... }`) when Declarative Pipeline (`pipeline { agent ... }`) meets the architectural requirement.
  - Do NOT commit plaintext passwords or credentials in `Jenkinsfile`; inject via `withCredentials([string(credentialsId: '...', variable: '...')])`.
  - Do NOT omit post-execution workspace cleanup; always invoke `cleanWs()` in `post { always { ... } }`.
- **Sibling Skill Boundaries:**
  - `github-actions-templates`: Owns GitHub Actions workflows.
  - `gitlab-ci-templates`: Owns GitLab CI/CD pipelines.
  - `jenkins-pipeline-templates` (this skill): Owns Jenkins Declarative Pipelines (`Jenkinsfile`).

---

## 3. Ordered Execution Workflow

### Phase 1: Declarative Pipeline Template

Author or update the `Jenkinsfile` Declarative Pipeline configuration.

<!-- classification: illustrative -->
```groovy
pipeline {
    agent any

    options {
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    environment {
        KATALON_API_KEY = credentials('katalon-kre-api-key')
        NODE_ENV = 'test'
    }

    stages {
        stage('Checkout & Setup') {
            steps {
                checkout scm
                sh 'npm ci'
            }
        }

        stage('Parallel Automated Testing') {
            parallel {
                stage('Playwright E2E Shard 1') {
                    steps {
                        sh 'npx playwright test --shard=1/2'
                    }
                }
                stage('Playwright E2E Shard 2') {
                    steps {
                        sh 'npx playwright test --shard=2/2'
                    }
                }
                stage('Katalon KRE Suite') {
                    when {
                        expression { env.RUN_KATALON == 'true' }
                    }
                    steps {
                        sh '''
                            katalonc -noSplash -runMode=console \
                              -projectPath="$(pwd)/project.prj" \
                              -retry=0 \
                              -testSuitePath="Test Suites/TS_Smoke" \
                              -browserType="Chrome (headless)" \
                              -executionProfile="default" \
                              -apiKey="${KATALON_API_KEY}"
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            junit testResults: '**/reports/*.xml, **/JUnit_Report.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'playwright-report/**, Screenshots/FAILED_*.png', allowEmptyArchive: true, fingerprint: true
            cleanWs deleteDirs: true, notFailBuild: true
        }
    }
}
```

### Phase 2: Pipeline Invariants & Hygiene

1. **Workspace Sanitization:** Always execute `cleanWs()` in the post-build block to prevent cross-build disk pollution and lingering lockfiles.
2. **Credential Masking:** Use Jenkins native `credentials()` helper to bind secrets securely; never echo or write credentials to workspace files.
3. **Artifact Retention:** Limit artifact history with `buildDiscarder(logRotator(numToKeepStr: '15', artifactNumToKeepStr: '10'))`.

---

## 4. Verification Points & DoD

1. **Syntax Validation:** `Jenkinsfile` adheres to Declarative Pipeline syntax and passes Jenkinsfile linter.
2. **Credential Binding:** Zero hardcoded secrets; 100% of credentials mapped via Jenkins credentials store.
3. **Report Publication:** Post-build actions configure `junit` result parsing and selective artifact archiving.
4. **Clean Teardown:** Post section enforces `cleanWs()` workspace sanitization.

---

## 5. Handoff Protocol

- **Deliverables:** Production-ready `Jenkinsfile` pipeline definitions and reusable stage libraries.
- **Next Subagent:** Pass to `test-runner` for local runner execution or `quality-gatekeeper` for CI/CD pipeline acceptance.
- **Output Format:** Valid Jenkins Declarative Pipeline Groovy syntax.
