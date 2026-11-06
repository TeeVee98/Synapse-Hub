// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

package com.synapse.mobile.pages;

import io.appium.java_client.AppiumBy;
import io.appium.java_client.AppiumDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.support.ui.ExpectedConditions;

/**
 * Screen Object Model implementation for Mobile Authentication.
 * Encapsulates all selectors using accessibilityId and resource-id hierarchy.
 */
public class LoginScreen extends BaseScreen {

    // Tier 1: Cross-platform Accessibility ID
    private final By usernameField = AppiumBy.accessibilityId("input_username");
    private final By passwordField = AppiumBy.accessibilityId("input_password");
    private final By loginButton = AppiumBy.accessibilityId("btn_sign_in");

    // Tier 2: Android Resource-ID fallback
    private final By errorMessageText = AppiumBy.id("com.synapse.qa:id/text_error_banner");

    public LoginScreen(AppiumDriver driver) {
        super(driver);
    }

    /**
     * Executes login action cleanly.
     */
    public LoginScreen performLogin(String username, String password) {
        enterTextSafe(usernameField, username);
        enterTextSafe(passwordField, password);
        clickSafe(loginButton);
        return this;
    }

    /**
     * Verifies error message displayed after invalid attempt.
     */
    public boolean isErrorMessageDisplayed() {
        return wait.until(ExpectedConditions.visibilityOfElementLocated(errorMessageText)).isDisplayed();
    }
}
