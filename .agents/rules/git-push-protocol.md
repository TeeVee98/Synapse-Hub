---
trigger: always_on
description: Clean Git Push Protocol for target projects and agent-skills Hub, pre-push verification gate, and zero-leakage commit rules.
---

# Clean Git Push Protocol & Repository Hygiene

## 1. Target Project Standard Push Protocol
When the user requests *"push"*, *"push code"*, *"push git"*, execute this standard workflow:

1. **Pre-Push Gate (DoD Verification):** Run verification before committing (`python tools/verify_all.py` or test runner). Never push unverified code or failing tests.
2. **Selective Staging:** Stage specifically changed project files (`git add <files>`). Never stage temporary artifacts (`Screenshots/`, `Reports/`, `*.log`). Avoid blind `git add -A` on target projects.
3. **Conventional Commit:** Create structured semantic commits: `git commit -m "<type>(<scope>): <summary>"`.
4. **User Confirmation Required:** Always ask user confirmation before running `git push origin <branch>`.
5. **Post-Analysis Artifact Sync:** When updating `PROJECT_HEALTH_REPORT.md` or `repo_map.txt`, stage and commit locally, then confirm with user before remote push.

## 2. Zero-Leakage & Repository Hygiene
- **Strict Decoupled Boundary:** Target project repos contain ONLY target business code/tests. The `.agents/` folder and skills reside solely in `agent-skills` Hub and must NEVER be copied or committed into target project repositories.
- **Gitignore Cleanliness:** Target project `.gitignore` must ignore scratch files (`Reports/`, `Screenshots/`, `*.log`, local caches).

## 3. Hub Repository (`agent-skills`) Push Protocol
When updating universal skills, rules, or tools inside the `agent-skills` repository itself:
```bash
git add -A
git commit -m "<type>(<scope>): <summary>"
git push origin <branch>
```
*(Always confirm with user before remote push).*
