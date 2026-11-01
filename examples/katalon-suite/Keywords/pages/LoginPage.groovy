package pages

import com.kms.katalon.core.testobject.TestObject
import com.kms.katalon.core.testobject.ConditionType
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

/**
 * LoginPage adhering strictly to Clean POM Flat Architecture.
 * Encapsulates all DOM selectors and interaction methods.
 */
public class LoginPage extends BasePage {

    private TestObject txtUsername = makeTestObject("//input[@id='username']")
    private TestObject txtPassword = makeTestObject("//input[@id='password']")
    private TestObject btnLogin = makeTestObject("//button[@id='btn-login']")
    private TestObject msgSuccess = makeTestObject("//div[contains(@class, 'alert-success')]")

    private static TestObject makeTestObject(String xpath) {
        TestObject to = new TestObject()
        to.addProperty("xpath", ConditionType.EQUALS, xpath)
        return to
    }

    public LoginPage navigate(String url) {
        WebUI.openBrowser("")
        WebUI.navigateToUrl(url)
        waitForReady()
        return this
    }

    public LoginPage enterCredentials(String username, String password) {
        WebUI.setText(txtUsername, username)
        WebUI.setText(txtPassword, password)
        return this
    }

    public void submitLogin() {
        WebUI.click(btnLogin)
        waitForReady()
    }

    public boolean isLoginSuccessful() {
        return WebUI.verifyElementPresent(msgSuccess, 10)
    }
}
