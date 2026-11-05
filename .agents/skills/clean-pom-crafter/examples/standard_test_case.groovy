import com.enterprise.pages.BasePage
import com.enterprise.pages.LoginPage
import com.enterprise.pages.DataMiningPage
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

// Step 1: Ensure valid login session
LoginPage.ensureLoggedIn()

// Step 2: Navigate to target module
DataMiningPage.navigateToCumCongNghiep()

// Step 3: Prepare unique test data
String testCode = BasePage.uniqueCode("CCN_")
String testName = "Industrial Cluster " + testCode

// Step 4: Execute creation workflow
DataMiningPage.createCluster(testCode, testName, "Hanoi", "Active")

// Step 5: Two-phase search and verify by code
DataMiningPage.searchRecord(testCode)
DataMiningPage.verifyRecordExists(testCode)

// Step 6: Edit and verify update
String updatedName = testName + " [UPDATED]"
DataMiningPage.editRecord(testCode, updatedName)

// Step 7: Teardown cleanup (Delete & verify no longer exists)
DataMiningPage.deleteRecord(testCode)
