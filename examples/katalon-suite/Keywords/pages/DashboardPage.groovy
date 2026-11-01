package pages

import com.kms.katalon.core.testobject.TestObject
import com.kms.katalon.core.testobject.ConditionType
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

/**
 * DashboardPage displaying business KPIs and metrics.
 */
public class DashboardPage extends BasePage {

    private TestObject headerDashboard = makeTestObject("//h1[contains(text(), 'Dashboard')]")
    private TestObject cardActiveUsers = makeTestObject("//div[@data-testid='card-active-users']")

    private static TestObject makeTestObject(String xpath) {
        TestObject to = new TestObject()
        to.addProperty("xpath", ConditionType.EQUALS, xpath)
        return to
    }

    public boolean isDashboardLoaded() {
        waitForReady()
        return WebUI.verifyElementPresent(headerDashboard, 10)
    }

    public String getActiveUsersCount() {
        return WebUI.getText(cardActiveUsers)
    }
}
