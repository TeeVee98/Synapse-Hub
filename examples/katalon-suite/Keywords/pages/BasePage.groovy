package pages

import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI
import com.kms.katalon.core.model.FailureHandling

/**
 * BasePage encapsulating reusable Clean POM operations and smart synchronization.
 */
public class BasePage {

    public static String uniqueCode(String prefix = "AUTO_") {
        return prefix + System.currentTimeMillis()
    }

    public void waitForReady(int timeoutSec = 10) {
        // Smart wait: wait for page document state without static Thread.sleep
        WebUI.waitForPageLoad(timeoutSec, FailureHandling.OPTIONAL)
    }
}
