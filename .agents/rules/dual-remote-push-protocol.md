---
trigger: always_on
description: Mandatory Dual Remote and Privacy Push Protocol strictly enforcing private assets isolation between personal GitHub and company SCM.
---

# DUAL REMOTE & PRIVACY PUSH PROTOCOL (MANDATORY RULE)

> **Purpose:** 100% intellectual property protection (AI Agents, Skills, Workflows, Prompts) owned by the author. Strictly prohibit leakage to company SCM.

---

## 1. Remote Repository Mapping

| Remote | Purpose | Scope / Permitted Content |
| :--- | :--- | :--- |
| `github` | **Author Personal Repository** | **FULL (100%)**: Entire `.agents/`, all AI markdown files (`AGENTS.md`, `PROJECT_STATE.md`, etc.), `tools/`, complete granular commit history. |
| `origin` | **Company SCM (DevOps / Enterprise)** | **CLEAN ONLY**: Pure test source code (Test Cases, Suites, Keywords, POM). **STRICTLY FORBIDDEN:** `.agents/`, any AI/Agent markdown files, or AI commit history. |

---

## 2. Documentation Whitelist for Company SCM

To guarantee zero leakage, only approved business documentation is allowed on company SCM:
1. `README.md` (Project overview & setup)
2. `HDSD.md` (User manual)
3. `FINAL_REPORT.md` (QA acceptance test report)
4. `POM_REFACTORING_PLAN.md` (Clean POM architecture)
5. `CICD_GUIDE.md` (CI/CD pipeline guide)
6. `ONBOARDING.md` (Environment setup)
7. `KNOWN_ISSUES.md` (Application defect log)

> [!CAUTION]
> **ALL OTHER `.md` FILES** (including `AGENTS.md`, `AI_*.md`, `FUTURE_*.md`, `PROJECT_STATE.md`, all `.md` files in `.agents/`, and draft prompts) are **Private Assets** and **AUTOMATICALLY EXCLUDED** from the company SCM branch.

---

## 3. Automatic Trigger Words

When the user gives commands such as:
- *"push up"*, *"push code"*, *"push git"*, *"push"*...

AI Agent **AUTOMATICALLY EXECUTES** the 3-step Dual Push workflow:

### Step 1: Commit & Push to Personal GitHub (`github`)
```powershell
git add -A
git commit -m "<conventional-commit-message>"
git push github main
```

### Step 2: Synchronize Clean Branch & Push to Company SCM (`origin`)
```powershell
# 1. Switch to clean branch
git checkout scm-clean

# 2. Sync test code files from main (excluding .agents and AI docs)
git checkout main -- "Test Cases" Scripts "Test Suites" Keywords Profiles Data\ Files Include settings .env.example .gitlab-ci.yml .github CICD_GUIDE.md HDSD.md ONBOARDING.md POM_REFACTORING_PLAN.md README.md FINAL_REPORT.md KNOWN_ISSUES.md *.prj build.gradle

# 3. Create clean commit inheriting directly from origin/main (no AI commit history)
$tree = (git write-tree).Trim()
$parent = (git rev-parse origin/main).Trim()
$cleanCommit = (git commit-tree $tree -p $parent -m "feat: sync latest automation test suite").Trim()
git reset --hard $cleanCommit

# 4. Push to company SCM
git push origin scm-clean:main
```

### Step 3: Return to Local `main` Branch
```powershell
git checkout main
```

---

## 4. Iron Discipline for Company SCM
1. **NEVER** run `git push origin main` from the `main` branch containing `.agents/`.
2. **NEVER** let `.agents/` files or references to Agents/Swarm/Skills leak into documents pushed to company SCM.
3. If user explicitly specifies:
   - *"push only to github"* -> Run Step 1 only.
   - *"push only to scm"* -> Run Steps 2 & 3 only.
   - *"push / push up"* (default) -> Automatically execute all 3 steps.
