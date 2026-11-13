---
trigger: always_on
description: Clean Git Push Protocol for target projects and Synapse Hub, pre-push verification gate, and zero-leakage commit rules.
---

# Clean Git Push Protocol & Repository Hygiene

## 1. Target Project Standard Push Protocol
When mounted alongside a target project and the user requests *"push"*, *"push code"*, *"push git"*, or *"push lên"*, execute this standard workflow strictly on the **target project**:

> ⚠️ **Scope Isolation Invariant:** Only push to the target project. Absolutely never push or stage changes to the Hub repo (`Synapse-Hub` / `agent-skills`) unless the user explicitly requests *"push hub"* or *"push synapse-hub"*.

1. **Pre-Push Gate (DoD Verification):** Run verification before committing (if `tools/verify_all.py` exists, execute it; otherwise, execute target project native test runner `npm test`, `pytest`, `mvn test`). Never push unverified code or failing tests.
2. **Selective Staging:** Stage specifically changed project files (`git add <files>`). Never stage temporary artifacts (`Screenshots/`, `Reports/`, `*.log`). Avoid blind `git add -A` on target projects.
3. **Conventional Commit:** Create structured semantic commits: `git commit -m "<type>(<scope>): <summary>"`.
4. **User Confirmation Required:** Always ask user confirmation before running `git push origin <branch>`.
5. **Post-Analysis Artifact Sync:** When updating `PROJECT_HEALTH_REPORT.md` or `repo_map.txt`, stage and commit locally, then confirm with user before remote push.

## 2. Zero-Leakage & Repository Hygiene
- **Strict Decoupled Boundary:** Target project repos contain ONLY target business code/tests. The `.agents/` folder and skills reside solely in `Synapse-Hub` and must NEVER be copied or committed into target project repositories.
- **Gitignore Cleanliness:** Target project `.gitignore` must ignore scratch files (`Reports/`, `Screenshots/`, `*.log`, local caches).

## 3. Hub Repository (`Synapse-Hub`) Push Protocol
When working inside the Hub repository and the user requests *"push lên"*, *"push code"*, *"push hub"*, or *"publish hub"*, execute the autonomous release pipeline:
- **Mandatory Adaptive SemVer Bump Invariant:** Before pushing, inspect modified files and automatically bump the version accordingly via `python tools/bump_version.py <patch|minor|major>`:
  - `patch`: Bug fixes, small doc/tool corrections, test updates (`x.y.Z`).
  - `minor`: New features, subagent capabilities, new gates, API/backend abstractions (`x.Y.0`).
  - `major`: Breaking changes, major architectural redesigns (`X.0.0`).
- **5-Step Autonomous Release Pipeline:**
```bash
python tools/hub_publisher.py
```
*(Executes: 1. Push to main -> 2. Create & push tag vX.Y.Z -> 3. Create GitHub Release via API -> 4. Build GitHub Package -> 5. Publish & verify NPM registry).*
