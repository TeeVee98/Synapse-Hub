// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import pages.LoginPage
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

// Clean POM Test Script: Zero raw XPaths/CSS selectors
LoginPage loginPage = new LoginPage()

loginPage.navigate("https://app.enterprise-demo.com/login")
         .enterCredentials("qa_automation_user", "SecurePass123!")
         .submitLogin()

assert loginPage.isLoginSuccessful() == true
WebUI.closeBrowser()
