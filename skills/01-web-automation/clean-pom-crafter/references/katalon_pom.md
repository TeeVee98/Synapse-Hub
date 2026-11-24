# Katalon Clean POM Architecture & Reference Guide

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Katalon Studio Directory Architecture & Flat Structure

Katalon Studio uses a keyword-driven engine where scripts and keywords reside in defined directories:

```
examples/katalon-suite/ (or Katalon Project Root)
├── Keywords/
│   └── <namespace>/
│       └── pages/
│           ├── BasePage.groovy          # Shared driver helpers, smart waits, uniqueCode
│           ├── LoginPage.groovy         # Authentication workflows
│           ├── DashboardPage.groovy     # Dashboard verification
│           └── PomPatterns.groovy       # Reusable table, dialog, and calendar patterns
├── Scripts/
│   ├── Auth/
│   │   └── TC_LoginSuccess/
│   │       └── Script*.groovy           # Test execution script
│   └── Dashboard/
│       └── TC_ViewSummary/
│           └── Script*.groovy
├── Test Cases/                          # Katalon test case descriptor XMLs
└── Test Suites/                         # Test suite collections
```

### Flat Directory Enforcement for Katalon
- **Keywords Layer:** All Page Classes reside directly in `Keywords/<namespace>/pages/*.groovy` without deeply nested sub-packages.
- **Scripts Layer:** Test scripts reside in `Scripts/**`, each executing a single business scenario.
- **Pure Code POM Discipline:** Synapse-Hub strictly enforces **Pure Code Clean POM** in Groovy over Katalon's binary/XML Object Repository (`Object Repository/`). This eliminates `findTestObject(...)` flakiness and git merge conflicts, ensuring locators are centralized in version-controlled Groovy Page Classes.

---

## 2. BasePage Inheritance & Dynamic Smart Waits

All Katalon Page Classes inherit directly from `BasePage` (maximum 1 level of inheritance).

### Core Responsibilities of BasePage
- **Driver Retrieval:** Obtains the active driver via `DriverFactory.getWebDriver()`.
- **Smart Waits:** Encapsulates dynamic waits (`waitForElementVisible`, `waitForElementClickable`, `waitForAngular`) with explicit timeouts.
- **Safe Interaction:** JavaScript-based input and clicks to avoid click-intercepted errors.

```groovy
package com.enterprise.pages

import org.openqa.selenium.By
import org.openqa.selenium.WebDriver
import org.openqa.selenium.WebElement
import org.openqa.selenium.support.ui.ExpectedConditions
import org.openqa.selenium.support.ui.WebDriverWait
import java.time.Duration
import com.kms.katalon.core.webui.driver.DriverFactory

public class BasePage {

    public static WebDriver getDriver() {
        return DriverFactory.getWebDriver()
    }

    public static WebElement waitForElementVisible(By locator, int timeoutSeconds = 10) {
        WebDriverWait wait = new WebDriverWait(getDriver(), Duration.ofSeconds(timeoutSeconds))
        return wait.until(ExpectedConditions.visibilityOfElementLocated(locator))
    }

    public static WebElement waitForElementClickable(By locator, int timeoutSeconds = 10) {
        WebDriverWait wait = new WebDriverWait(getDriver(), Duration.ofSeconds(timeoutSeconds))
        return wait.until(ExpectedConditions.elementToBeClickable(locator))
    }

    public static void clickSafe(By locator, int timeoutSeconds = 10) {
        WebElement element = waitForElementClickable(locator, timeoutSeconds)
        element.click()
    }

    public static String uniqueCode(String prefix = "AUTO_") {
        return prefix + System.currentTimeMillis() + "_" + UUID.randomUUID().toString().substring(0, 5).toUpperCase()
    }
}
```

---

## 3. Dynamic Test Data & Idempotency (`uniqueCode`)

To prevent database unique-constraint collisions during parallel or repeated runs, always generate unique test entity codes:

```groovy
// In test script or keyword method:
String categoryCode = BasePage.uniqueCode("CAT_")
String categoryName = "Automated Category " + categoryCode

// Pair every creation test case with an automated Teardown step:
try {
    CommonCategoryPage.createCategory(categoryCode, categoryName)
    CommonCategoryPage.verifyCategoryExists(categoryCode)
} finally {
    CommonCategoryPage.deleteCategory(categoryCode)
}
```

---

## 4. GPars Parallel Concurrency Pattern

When testing race conditions, high-throughput workflows, or parallel test suites in Katalon Studio, use Groovy's built-in **GPars** (`groovyx.gpars.GParsPool`):

```groovy
import groovyx.gpars.GParsPool
import com.kms.katalon.core.annotation.Keyword

public class ConcurrencyKeyword {

    /**
     * Executes a list of action closures simultaneously using a GPars thread pool.
     */
    @Keyword
    static List<Object> executeConcurrentActions(List<Closure> actions, int poolSize = 5) {
        List<Object> results = []
        GParsPool.withPool(poolSize) {
            results = actions.collectParallel { action ->
                try {
                    return [status: 'SUCCESS', result: action.call()]
                } catch (Exception ex) {
                    return [status: 'FAILED', error: ex.message]
                }
            }
        }
        return results
    }
}
```

### Usage Example for Double-Spend / Stock Contention
```groovy
def actionA = { OrderService.submitOrder("ITEM_001", "USER_A") }
def actionB = { OrderService.submitOrder("ITEM_001", "USER_B") }

def outcomes = ConcurrencyKeyword.executeConcurrentActions([actionA, actionB], 2)
assert outcomes.any { it.status == 'SUCCESS' }
assert outcomes.any { it.error?.contains("Conflict") || it.error?.contains("409") }
```

---

## 5. Implementation References & Links

- [**Standard Clean POM Groovy Methods (`pom_patterns.groovy`)**](pom_patterns.groovy): Reusable enterprise methods for two-phase search, edit, delete with confirmation dialogs, and Angular change detection.
- [**Standard Test Script Template (`../examples/standard_test_case.groovy`)**](../examples/standard_test_case.groovy): End-to-end 7-step test script demonstrating login, navigation, data preparation, creation, search, edit, and cleanup.
- [**Katalon CLI Runner Skill**](../../../katalon/katalon-cli-runner/SKILL.md): Headless Katalon execution, process management, and JUnit report processing.
- **Groovy Script Validator (`tools/lint/validate_groovy_scripts.py`):** Pre-check Groovy syntax, brackets, and lonely backslashes before CI execution.
