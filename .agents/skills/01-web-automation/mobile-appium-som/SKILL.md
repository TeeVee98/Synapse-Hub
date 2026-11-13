---
name: mobile-appium-som
description: "Enterprise Screen Object Model (SOM) and Appium mobile automation standards for iOS and Android. Use when authoring, refactoring, or executing native or hybrid mobile tests with Appium, UIAutomator2, or XCUITest."
---

# Mobile Appium Screen Object Model (SOM) — Enterprise Architecture Standards

Specialized skill for creating, refactoring, and maintaining enterprise mobile automation test suites across **Android (UIAutomator2)** and **iOS (XCUITest)** using the **Screen Object Model (SOM)** and Clean Architecture.

---

## 1. Core Architectural Invariants

1. **Screen Object Model (SOM):**
   - Screen classes end with the `Screen` suffix (e.g., `LoginScreen.java`, `HomeScreen.ts`, `CheckoutScreen.py`) and extend `BaseScreen`.
   - All mobile locators (`AppiumBy`), gesture interactions, and platform-specific synchronization belong inside Screen classes.
2. **Zero Raw Locators in Test Scripts:**
   - Test scripts (`TC-xxx_*.spec.ts`, `TC_*.java`, `test_*.py`) only orchestrate high-level business flows via Screen class methods. Raw `findElement`, `AppiumBy`, or XPath queries inside test scripts are strictly prohibited.
3. **Driver & Capability Isolation:**
   - Capabilities and device configurations reside in environment profiles or configuration files (e.g., `caps.json`), never hardcoded in test scripts or Screen classes.
   - Drivers are initialized in test fixtures/before-hooks and guaranteed to terminate via `driver.quit()` in teardown blocks.
4. **Mandatory 100% UTF-8 No BOM:**
   - All mobile source files must use UTF-8 encoding with zero Byte Order Mark (`0xEF, 0xBB, 0xBF`).

---

## 2. Native Mobile Locator Priority Hierarchy

All mobile Screen classes **MUST** adhere to this 5-tier selector priority:

| Tier | Selector Strategy | Target Platform | Syntax Example | Notes |
|:---:|---|---|---|---|
| **1** | **Accessibility ID / Content-Desc** | Cross-Platform (Android & iOS) | `AppiumBy.accessibilityId("btn_login")` | Top priority; resilient against UI refactoring |
| **2** | **Resource-ID** | Android Native (UIAutomator2) | `AppiumBy.id("com.example.app:id/input_user")` | Stable across locales and builds |
| **3** | **iOS Predicate String** | iOS Native (XCUITest) | `AppiumBy.iOSNsPredicateString("label == 'Sign In' AND visible == 1")` | Fast Apple native predicate query |
| **4** | **iOS Class Chain** | iOS Native (XCUITest) | `AppiumBy.iOSClassChain("**/XCUIElementTypeButton[\`label == 'Submit'\`]")` | Direct hierarchical indexing |
| **5** | **Relative XPath (Last Resort)** | Dynamic Fallback | `AppiumBy.xpath("//android.widget.TextView[@text='Confirm']")` | Attribute-based only; strictly avoid deep trees |

> 🚫 **FORBIDDEN:** Absolute structural XPaths (e.g., `//android.widget.FrameLayout[1]/android.widget.LinearLayout[1]/.../android.widget.Button[2]`).

---

## 3. Mobile Synchronization & Smart Scrolling

1. **Zero Static Delays:**
   - Static sleeps (`Thread.sleep()`, `time.sleep()`) are forbidden. Always use explicit dynamic waits via `WebDriverWait` with `ExpectedConditions` and defined timeout durations.
2. **Smart Scrolling (Scroll-to-View):**
   - Never interact with off-screen elements without first scrolling them into view.
   - **Android:** Utilize native `UiScrollable` via `AppiumBy.androidUIAutomator`:
     ```java
     String scrollExpr = "new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text(\"Target Item\"))";
     driver.findElement(AppiumBy.androidUIAutomator(scrollExpr));
     ```
   - **iOS:** Utilize native gesture commands:
     ```java
     Map<String, Object> params = new HashMap<>();
     params.put("direction", "down");
     params.put("predicateString", "label == 'Target Item'");
     driver.executeScript("mobile: scroll", params);
     ```
3. **Keyboard Management:**
   - Always dismiss the virtual on-screen keyboard prior to invoking taps or asserting UI state to avoid click interception:
     ```java
     if (driver.isKeyboardShown()) {
         driver.hideKeyboard();
     }
     ```

---

## 4. Mobile Lifecycle & Resilience

1. **System Permission Handling:**
   - Include `autoGrantPermissions: true` in Android capabilities to prevent unexpected system dialog popups from blocking automation pipelines.
2. **Backgrounding Validation:**
   - When testing background session persistence or token refresh, validate state using `driver.runAppInBackground(Duration.ofSeconds(5))`.
3. **Idempotent Test Data:**
   - Always randomize mobile test inputs using timestamps or UUIDs to avoid unique constraint collisions.
4. **Idempotent Teardown:**
   - Every entity created during a test case must be cleaned up in an automated teardown step.

---

## 5. Implementation References & Examples

- [**BaseScreen Standard Implementation**](examples/BaseScreen.java): Demonstrates explicit waits, `UiScrollable`, iOS gestures, keyboard dismissal, and safe click wrappers.
- [**LoginScreen Implementation**](examples/LoginScreen.java): Demonstrates SOM encapsulation with Tier 1 and Tier 2 locators.
- [**Standard Mobile Test Case**](examples/TC_MobileLogin.java): Demonstrates clean test script workflow without raw locators.
