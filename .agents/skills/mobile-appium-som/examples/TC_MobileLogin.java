// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

package com.synapse.mobile.tests;

import com.synapse.mobile.pages.BaseScreen;
import com.synapse.mobile.pages.LoginScreen;
import io.appium.java_client.AppiumDriver;
import org.testng.Assert;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

/**
 * TC-701: Clean SOM Mobile Login Test Case.
 * Contains zero raw locators; orchestrates Screen Object calls only.
 */
public class TC_MobileLogin {

    private AppiumDriver driver;

    @BeforeMethod
    public void setUp() {
        // Driver initialized via environment profile / factory
    }

    @Test
    public void testInvalidLoginShowsError() {
        String testUser = BaseScreen.uniqueCode("USR_");
        LoginScreen loginScreen = new LoginScreen(driver);

        loginScreen.performLogin(testUser, "InvalidSecret#2026");
        Assert.assertTrue(loginScreen.isErrorMessageDisplayed(), "Error banner must be visible on invalid login");
    }

    @AfterMethod(alwaysRun = true)
    public void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }
}
