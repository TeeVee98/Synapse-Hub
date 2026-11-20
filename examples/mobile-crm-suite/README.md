# Enterprise Mobile Automation Suite (Sprint 5)

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.  
> **Standards Alignment:** Conforms to **OWASP MASVS v2.0 (Mobile Application Security Verification Standard)**, **Apple Human Interface Guidelines (HIG)**, **Google Material Design 3**, and **ISTQB Mobile Application Testing**.

---

## 1. Overview & Architecture

This suite delivers an enterprise-grade mobile automation architecture for **Android (UIAutomator2)** and **iOS (XCUITest)**:
1. **Screen Object Model (SOM)** — Extends `BaseScreen` with 1-level flat inheritance. All locators, gestures, and smart waits are strictly encapsulated within Screen Classes in `pages/`.
2. **Zero Raw Locators in Test Scripts** — Test scripts in `tests/` contain zero `AppiumBy`, zero XPaths, and zero `driver.findElement` calls.
3. **OWASP MASVS Manifest Security Audit** — Validates `AndroidManifest.xml` and `Info.plist` against `MASVS-RESILIENCE-1` (debuggable), `MASVS-STORAGE-2` (allowBackup), and `MASVS-NETWORK-1` (cleartext traffic).
4. **Physical Hardware Interruption & Resilience** — Simulates incoming phone calls, SMS OTP alerts, low battery triggers, and app backgrounding session persistence.
5. **Declarative Maestro Flows** — Fast declarative `.yaml` flows for mobile smoke testing and fast CI feedback.

---

## 2. 5-Tier Native Mobile Locator Hierarchy

| Tier | Strategy | Target Platform | Example Syntax | Architectural Role |
| :---: | :--- | :--- | :--- | :--- |
| **Tier 1** | **Accessibility ID / Content-Desc** | Cross-Platform (Android & iOS) | `("accessibility id", "btn_sign_in")` | Top priority; resilient against UI rebuilds |
| **Tier 2** | **Resource-ID** | Android Native (UIAutomator2) | `("id", "com.synapse.crm:id/txt_email")` | Stable across locales and builds |
| **Tier 3** | **iOS Predicate String** | iOS Native (XCUITest) | `("predicate", "label == 'Save' AND visible == 1")` | High-speed Apple native predicate |
| **Tier 4** | **iOS Class Chain** | iOS Native (XCUITest) | `("class chain", "**/XCUIElementTypeButton[\`name == 'Submit'\`]")` | Hierarchical indexing |
| **Tier 5** | **Relative XPath** | Dynamic Fallback | `("xpath", "//android.widget.TextView[@text='Confirm']")` | Attribute-based only; 0 deep trees |

---

## 3. Test Suites & Coverage Matrix (18 Automated TCs)

| Suite File | Test Cases | Objective / Verification Target |
| :--- | :--- | :--- |
| `tests/test_mobile_auth.py` | **TC-MOB-01 – TC-MOB-05** | Happy Path login, blank credential error, masked password security, invalid login, Remember Me state. |
| `tests/test_mobile_customers.py` | **TC-MOB-06 – TC-MOB-12** | Customer list view, FAB customer creation, required company validation, email format error, keyword search, empty state banner, pull-to-refresh swipe. |
| `tests/test_mobile_resilience.py` | **TC-MOB-13 – TC-MOB-18** | Background app session persistence (5s), virtual keyboard safe dismissal, form cancel flow, incoming call ADB simulation, SMS OTP simulation, low battery interrupt. |

---

## 4. Quick Start & Execution

### 4.1 Running Mobile Suite with Pytest
```bash
# Run all 18 mobile test cases
pytest examples/mobile-crm-suite/tests -v

# Run smoke tests only
pytest examples/mobile-crm-suite/tests -m smoke -v

# Run with live Appium server
APPIUM_SERVER_URL="http://localhost:4723" pytest examples/mobile-crm-suite/tests -v
```

### 4.2 Auditing OWASP MASVS Manifests
```bash
python tools/perf/mobile_resilience_sentinel.py --audit-manifest examples/mobile-crm-suite/manifests/AndroidManifest.xml
python tools/perf/mobile_resilience_sentinel.py --audit-plist examples/mobile-crm-suite/manifests/Info.plist
```

### 4.3 Running Maestro Declarative Flows
```bash
# Run login flow
maestro test examples/mobile-crm-suite/maestro/01_login_flow.yaml

# Run customer creation flow
maestro test examples/mobile-crm-suite/maestro/02_create_customer_flow.yaml
```
