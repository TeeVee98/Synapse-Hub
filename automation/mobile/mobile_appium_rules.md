---
trigger: on_demand
description: Full mobile automation rules for Appium iOS & Android, Screen Object Model (SOM), locator priority, capabilities, alerts, and context switching.
profiles: [mobile-appium, full]
---

# Mobile Automation Rules — Appium iOS & Android (Full Standard)

> Production-grade mobile automation standards for Appium supporting UIAutomator2 (Android) and XCUITest (iOS).

## 1. Screen Object Model (SOM)
* Encapsulate 100% of locators and screen interactions within `screens/` (maximum 1 level of inheritance from `BaseScreen`). Never write raw selectors or element locators directly inside `tests/`.
* Separate locators by platform when the UI tree diverges (`locators/ios/` and `locators/android/`).

## 2. Mobile Locator Hierarchy (Strict)
1. **Accessibility ID (Priority 1 — Cross-Platform):** `~accessibilityId` (iOS `accessibilityIdentifier` / Android `content-desc`).
2. **iOS Native (Priority 2 for iOS):** `-ios predicate string` (e.g., `label == "Login" AND visible == 1`) or `-ios class chain`.
3. **Android Native (Priority 3 for Android):** `id` / `resource-id` (`new UiSelector().resourceId(...)`).
4. **Strictly Prohibited:** XPaths containing numeric index predicates (e.g., `//XCUIElementTypeCell[3]`, `//android.widget.TextView[2]`) and hardcoded tap coordinates `tap(x, y)`.

## 3. Stability, Alerts & Context Switching
* **Capabilities:** Explicitly configure `automationName`, `newCommandTimeout`, and session isolation strategies (`noReset` / `fullReset`) to guarantee test idempotency and independence.
* **System Alerts & Keyboard:** Proactively handle OS system permission dialogs (Location, Camera, Notification) and invoke `hideKeyboard()` before interacting with obscured elements.
* **Smart Scroll & WebView:** Employ dynamic scrolling with bounded termination conditions when locating off-screen elements. For Hybrid / WebView interactions, inspect `getContexts()` and switch back to `NATIVE_APP` immediately upon completion.

## 4. PII & Credential Security Policy
* **Zero Signing Credentials in Git:** Strictly forbid committing Android keystores, iOS signing certificates, provisioning profiles, or private keys (`.keystore`, `.jks`, `.p12`, `.mobileprovision`) to the git repository.
* **Environment Injection:** Inject all build credentials, signing aliases, keystore passwords, and test account secrets dynamically via environment variables (`KEYSTORE_PASSWORD`, `APP_SIGNING_KEY`) or secure secret vaults.
* **PII Data Masking:** Never log or capture personal identifiable information (PII) such as unmasked user phone numbers, emails, passwords, credit card numbers, or authorization tokens in test logs, screenshots, or Appium execution traces.

## 5. Katalon Studio Mobile Framework Standard
* **Keyword Scope:** Use `Mobile.*` keywords strictly within Page Classes (`Keywords/<namespace>/pages/`). Never execute raw `Mobile.*` calls inside test scripts (`Scripts/`).
* **Object Repository Structure:** Encapsulate mobile test objects under `Object Repository/Mobile/<platform>/<screen>/`.
* **KRE Headless Mobile Execution:** Specify `-browserType="Android"` or `-browserType="iOS"` with dynamic `-deviceId` and `-appId` passed from CI/CD environment variables.
