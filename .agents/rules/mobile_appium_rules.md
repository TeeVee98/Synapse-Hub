---
trigger: on_demand
description: Mobile Automation standards, Screen Object Model (SOM), and Appium driver invariants for iOS/Android suites.
status: upcoming_extension
---

# Mobile Automation Standards & Appium Rules (Enterprise Extension)

> **Status:** Upcoming extension module for Appium / Mobile SOM architectures. Activated when mobile drivers or native iOS/Android test suites are mounted.  
> **Scope:** Applies to Mobile Automation using Appium, UIAutomator2 (Android), and XCUITest (iOS).  
> **Objective:** Deliver resilient, independent, flake-free mobile suites supporting parallel multi-device execution.

---

## 1. Native Locator Priority Hierarchy
1. **Accessibility ID / Content-Desc** (Top priority, cross-platform): `driver.findElement(AppiumBy.accessibilityId("btn_login"))`
2. **Resource-ID (Android Native):** `driver.findElement(AppiumBy.id("com.app:id/username"))`
3. **iOS Predicate String (iOS Native):** `driver.findElement(AppiumBy.iOSNsPredicateString("label == 'Sign In' AND visible == 1"))`
4. **iOS Class Chain:** `driver.findElement(AppiumBy.iOSClassChain("**/XCUIElementTypeButton[`label == 'Submit'`]"))`
5. **Dynamic XPath (Last Resort):** Relative XPath with attributes only. Absolute structural XPath is **FORBIDDEN**.

---

## 2. Strict Anti-Patterns & Prohibitions
- ❌ **FORBIDDEN:** Absolute hierarchy XPath (e.g., `//android.widget.FrameLayout[1]/.../Button[1]`).
- ❌ **FORBIDDEN:** Static delays (`Thread.sleep()`).
- ❌ **FORBIDDEN:** Interacting with off-screen elements without scrolling into view first.
- ❌ **FORBIDDEN:** Hardcoded device identifiers (UDID, device name must come from environment/profiles).

---

## 3. Screen Object Model (SOM) & Synchronization
- Screen classes end with `Screen` suffix (e.g., `LoginScreen.java`) extending `BaseScreen`.
- Encapsulate locators in Screen classes; test scripts call business actions only.
- **Smart Waits:** Always use `WebDriverWait` with explicit `Duration.ofSeconds(N)`.
- **Smart Scroll:** Use `UiScrollable(...).scrollIntoView(...)` or native iOS scroll gestures.

---

## 4. Mobile Lifecycle & Driver Invariants
- **Permissions:** Auto-grant system permissions via capabilities (`autoGrantPermissions: true`).
- **Resilience:** Validate backgrounding (`driver.runAppInBackground(...)`) and hide virtual keyboard before actions.
- **Driver Isolation:** Screen classes speak intent; platform drivers (UIAutomator2/XCUITest) encapsulate mechanics. Capabilities reside in profiles, never in scripts. Always explicitly quit sessions.
