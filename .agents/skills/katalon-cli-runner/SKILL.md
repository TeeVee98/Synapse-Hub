---
name: katalon-cli-runner
description: >-
  Adaptive test execution manager supporting both Licensed KRE CLI (headless automation)
  and No-License / Free Community mode (Katalon Studio GUI & Playwright Live verification),
  with Allure reporting and Telegram alerting.
---

# Katalon CLI & Adaptive Runner — Dual-Mode Execution Management

Specialized skill for managing, dispatching, and monitoring test runs across different licensing states (**License Available** or **No-License / Free Community**), integrated with Allure reporting and Telegram alerts.

---

## 1. Adaptive Dual-Mode Execution Strategy

| Licensing State | Recommended Mode | Response Time | Licensing Cost |
|---|---|:---:|:---:|
| **KRE License Available** | **Mode 1: Headless KRE CLI** (CI/CD or Terminal) | Batch-oriented | Licensed |
| **No License Available** | **Mode 2A: Katalon Studio GUI (Free Edition)** (Suite Acceptance) | 5–10 mins | **$0** |
| **No License Available** | **Mode 2B: Playwright Live Interaction** (Selector probing / logic check) | **< 200 ms** | **$0** |

---

## 2. Pre-Flight Quality Check

Run static integrity check before dispatching batch test suites:
```bash
python3 -c "
import os
for root, _, files in os.walk('.'):
    if '.git' in root: continue
    for f in files:
        if f.endswith(('.groovy', '.tc', '.ts', '.glbl', '.md', '.py', '.json', '.ps1')):
            p = os.path.join(root, f)
            with open(p, 'rb') as fp:
                assert fp.read(3) != b'\xef\xbb\xbf', f'BOM detected: {p}'
print('✅ Pre-flight passed: 100% UTF-8 No BOM')
"
```

---

## 3. License Recovery & Browser Crash Management

1. **License Expiration Symptoms:** `License quota exceeded` or `Trial expired`.
   * **AI Discipline:** Immediately halt CLI retries; switch to **Mode 2A** (Studio GUI) or **Mode 2B** (Playwright Live).
2. **Zombie Chromedriver Cleanup:**
   ```bash
   pkill -f chromedriver || true
   ```

---

## 4. Definition of Done (DoD)

1. **Exit Code = 0:** Runner completes without system crashes.
2. **Clean JUnit XML:** `<testsuite>` contains zero `<failure>` or `<error>` tags.
3. **Compile Allure Report:** `allure generate ./allure-results -o ./Reports/allure-report --clean`.
4. If failures occur, trigger Zero-Token Triad:
   ```bash
   python3 tools/pinpoint_failure.py
   # Or run targeted single TC: katalonc ... -testCasePath="Test Cases/TC-xxx"
   ```

---

## 5. Reference Documentation

- [**CLI Commands & 10 Suite Registry (`runner_commands.md`)**](references/runner_commands.md): KRE CLI commands for macOS, Linux, Windows PowerShell runner and lookup table for all 10 Test Suites.
