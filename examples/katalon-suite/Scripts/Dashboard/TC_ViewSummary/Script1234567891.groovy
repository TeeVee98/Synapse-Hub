// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import pages.LoginPage
import pages.DashboardPage
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

LoginPage loginPage = new LoginPage()
DashboardPage dashboardPage = new DashboardPage()

loginPage.navigate("https://app.enterprise-demo.com/login")
         .enterCredentials("qa_lead", "LeadSecret2026!")
         .submitLogin()

assert dashboardPage.isDashboardLoaded() == true
String userCount = dashboardPage.getActiveUsersCount()
assert userCount != null
WebUI.closeBrowser()
