// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

package com.synapse.mobile.pages;

import io.appium.java_client.AppiumBy;
import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Abstract BaseScreen providing smart waits, native scroll gestures,
 * keyboard management, and cross-platform mobile helpers.
 */
public abstract class BaseScreen {

    protected final AppiumDriver driver;
    protected final WebDriverWait wait;
    protected static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(15);

    public BaseScreen(AppiumDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, DEFAULT_TIMEOUT);
    }

    /**
     * Smart wait for element visibility and click safely.
     */
    protected void clickSafe(By locator) {
        WebElement element = wait.until(ExpectedConditions.elementToBeClickable(locator));
        element.click();
    }

    /**
     * Smart wait, dismiss keyboard if needed, and enter text.
     */
    protected void enterTextSafe(By locator, String text) {
        WebElement element = wait.until(ExpectedConditions.visibilityOfElementLocated(locator));
        element.clear();
        element.sendKeys(text);
        hideKeyboardSafe();
    }

    /**
     * Safe keyboard dismissal across Android and iOS.
     */
    protected void hideKeyboardSafe() {
        try {
            driver.executeScript("mobile: hideKeyboard");
        } catch (Exception ignored) {
            // Virtual keyboard already hidden
        }
    }

    /**
     * Native Android UiScrollable scroll into view.
     */
    protected WebElement scrollToAndroid(String visibleText) {
        String uiScrollExpr = "new UiScrollable(new UiSelector().scrollable(true))"
                + ".scrollIntoView(new UiSelector().text(\"" + visibleText + "\"))";
        return driver.findElement(AppiumBy.androidUIAutomator(uiScrollExpr));
    }

    /**
     * Native iOS scroll gesture into view.
     */
    protected void scrollToIOS(String predicateLabel) {
        Map<String, Object> params = new HashMap<>();
        params.put("direction", "down");
        params.put("predicateString", "label == '" + predicateLabel + "'");
        driver.executeScript("mobile: scroll", params);
    }

    /**
     * Generates a unique test entity code for idempotent test data.
     */
    public static String uniqueCode(String prefix) {
        return prefix + UUID.randomUUID().toString().substring(0, 8);
    }
}
