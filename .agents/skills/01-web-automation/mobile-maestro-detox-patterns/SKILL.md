---
name: mobile-maestro-detox-patterns
description: "Declarative mobile UI test patterns for Maestro flows and Detox gray-box automation on React Native and native mobile apps. Use when authoring declarative mobile flows or fast gray-box mobile tests."
category: test_automation_and_execution
version: "1.0.0"
policies:
  network: localhost-only
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Mobile Maestro & Detox Testing Patterns

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Use when authoring or executing declarative mobile UI test flows with Maestro (`.yaml`), configuring Detox gray-box automation for React Native applications (`.detoxrc.js`), establishing mobile test synchronization without flakiness, or running fast simulator/emulator smoke tests.
- **Activation Scope:**
  - Native iOS & Android mobile apps.
  - React Native and Flutter mobile applications.
  - Declarative Maestro automation flows (`.maestro/*.yaml`).
  - Detox gray-box E2E suites (`e2e/*.test.ts`).

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT use hardcoded coordinate taps (`tap: { x: 100, y: 200 }`); always target semantic labels, testIDs, or accessibility identifiers.
  - Do NOT use static sleeps in Maestro flows; rely on Maestro automatic element waiting and `extendedWaitUntil`.
  - Do NOT commit mobile app binaries (`.ipa`, `.apk`) to the git repository.
- **Sibling Skill Boundaries:**
  - `mobile-appium-som`: Handles enterprise Appium Screen Object Model (SOM) for iOS/Android.
  - `mobile-maestro-detox-patterns` (this skill): Handles declarative Maestro YAML flows and Detox gray-box testing.

---

## 3. Ordered Execution Workflow

### Phase 1: Maestro Declarative Flow Pattern

Maestro executes declarative YAML test flows with built-in tolerance for animations and network delays.

<!-- classification: illustrative -->
```yaml
# .maestro/login_checkout_flow.yaml
appId: com.example.app
---
- launchApp:
    clearState: true

# Assert initial screen state
- assertVisible: "Welcome Back"

# Input credentials using accessible labels or testIDs
- tapOn: "Email Address"
- inputText: "tester.auto@example.com"

- tapOn: "Password"
- inputText: "SecurePass123!"

- hideKeyboard

- tapOn:
    id: "btn_login"

# Dynamic smart synchronization
- extendedWaitUntil:
    visible: "Product Catalog"
    timeout: 10000

# Perform search and add to cart
- tapOn: "Search Products"
- inputText: "Wireless Headphones"
- tapOn: "Add to Cart"

- assertVisible: "Item added to cart"
```

### Phase 2: Detox Gray-Box Automation Pattern

Detox runs in-process synchronization with the React Native bridge to eliminate timing flakiness.

<!-- classification: illustrative -->
```typescript
// e2e/auth_flow.e2e.ts
import { by, device, element, expect } from 'detox';

describe('Authentication Journey', () => {
  beforeAll(async () => {
    await device.launchApp({ newInstance: true });
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  it('should authenticate user and display home dashboard', async () => {
    await expect(element(by.id('login_screen'))).toBeVisible();

    await element(by.id('input_email')).typeText('tester.auto@example.com');
    await element(by.id('input_password')).typeText('SecurePass123!\n');

    await element(by.id('btn_submit')).tap();

    await expect(element(by.text('Dashboard'))).toBeVisible();
  });
});
```

### Phase 3: Mobile Selector Hierarchy

1. **Test ID / Accessibility ID:** `id: "btn_submit"` (React Native `testID`, Android `content-desc`, iOS `accessibilityIdentifier`).
2. **Visible Text / Label:** `tapOn: "Complete Purchase"`.
3. **Regex Pattern:** `tapOn: { text: "Order #\\d+" }`.

---

## 4. Verification Points & DoD

1. **Declarative Syntax:** Maestro YAML flows and Detox specs pass syntax and linter checks.
2. **Accessibility-First:** 100% of selectors target testIDs, accessibility labels, or semantic text.
3. **Zero Static Sleeps:** Flow execution relies entirely on native gray-box synchronization or `extendedWaitUntil`.
4. **Idempotency:** Test runs start with isolated app state (`clearState: true` or `newInstance: true`).

---

## 5. Handoff Protocol

- **Deliverables:** Declarative `.maestro/*.yaml` flows, Detox E2E specs, and configuration blueprints.
- **Next Subagent:** Pass to `test-runner` for simulator/emulator execution or `quality-gatekeeper` for acceptance.
- **Output Format:** Clean YAML/TypeScript adhering to mobile automation standards.
