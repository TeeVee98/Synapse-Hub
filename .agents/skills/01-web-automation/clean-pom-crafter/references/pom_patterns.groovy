// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

package com.enterprise.pages

import org.openqa.selenium.By
import org.openqa.selenium.JavascriptExecutor
import org.openqa.selenium.Keys
import org.openqa.selenium.WebDriver
import org.openqa.selenium.WebElement
import com.kms.katalon.core.webui.driver.DriverFactory

/**
 * Enterprise Clean POM common methods reusable across Page Classes.
 * Inherits directly from BasePage.
 */
class PomPatterns extends BasePage {

    /**
     * Two-phase search behavior: Click Search -> Fill keyword -> Enter -> Wait for table update
     */
    public static void searchRecord(String keyword) {
        WebDriver driver = DriverFactory.getWebDriver()
        List<WebElement> inputs = driver.findElements(By.cssSelector("input.p-inputtext[placeholder*='Search'], input.p-inputtext[placeholder*='Tìm kiếm'], input[placeholder*='name'], input[placeholder*='code']"))
        if (inputs.isEmpty() || !inputs.get(0).isDisplayed()) {
            WebElement searchToggle = findElement(By.cssSelector("button.p-button-icon-only[icon*='search'], button[title*='Search'], button[title*='Tìm kiếm']"))
            searchToggle.click()
            waitForElementVisible(By.cssSelector("input.p-inputtext"), 5)
        }
        WebElement input = findElement(By.cssSelector("input.p-inputtext"))
        jsSetInput(input, keyword)
        input.sendKeys(Keys.ENTER)
        waitForAngular(5)
        waitForElementVisible(By.cssSelector("p-table table tbody tr"), 5)
    }

    /**
     * Edit record in the first row and verify updated name
     */
    public static void editRecord(String oldKeyword, String newName) {
        searchRecord(oldKeyword)
        WebElement editBtn = findElement(By.cssSelector("p-table tbody tr:first-child button[icon*='pencil'], p-table tbody tr:first-child button[icon*='edit']"))
        clickElement(editBtn)
        waitForElementVisible(By.cssSelector("input[formcontrolname='name'], input[name='name']"), 5)

        WebElement nameInput = findElement(By.cssSelector("input[formcontrolname='name'], input[name='name']"))
        jsSetInput(nameInput, newName)

        WebElement saveBtn = findElement(By.xpath("//button[@title='Save' or @title='Xác nhận' or contains(.,'Save') or contains(.,'Lưu') or contains(.,'Confirm')]"))
        clickElement(saveBtn)
        waitForAngular(5)

        searchRecord(newName)
        WebElement firstRow = findElement(By.cssSelector("p-table tbody tr:first-child"))
        assert firstRow.getText().contains(newName) : "Error: Record did not update with new name!"
    }

    /**
     * Delete record in the first row and confirm p-confirmdialog
     */
    public static void deleteRecord(String keyword) {
        WebDriver driver = DriverFactory.getWebDriver()
        searchRecord(keyword)
        WebElement deleteBtn = findElement(By.cssSelector("p-table tbody tr:first-child button.p-button-danger, p-table tbody tr:first-child button[icon*='trash']"))
        clickElement(deleteBtn)
        waitForElementVisible(By.xpath("//div[contains(@class,'p-dialog-footer') or contains(@class,'p-confirm-dialog')]//button[contains(@class,'p-confirm-dialog-accept') or contains(.,'Delete') or contains(.,'Xóa') or contains(.,'Confirm') or contains(.,'Yes')]"), 5)

        WebElement confirmBtn = findElement(By.xpath("//div[contains(@class,'p-dialog-footer') or contains(@class,'p-confirm-dialog')]//button[contains(@class,'p-confirm-dialog-accept') or contains(.,'Delete') or contains(.,'Xóa') or contains(.,'Confirm') or contains(.,'Yes')]"))
        clickElement(confirmBtn)
        waitForAngular(5)

        verifyRecordNotExists(keyword)
    }

    /**
     * Safely set date in p-calendar with Angular change detection
     */
    public static void setCalendarDate(WebElement element, String dateStr) {
        WebDriver driver = DriverFactory.getWebDriver()
        JavascriptExecutor js = (JavascriptExecutor) driver
        js.executeScript("""
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
        """, element, dateStr)
    }

    /**
     * Select multiple options in p-multiselect
     */
    public static void selectMultiOptions(WebElement multiSelectEl, List<String> optionTexts) {
        clickElement(multiSelectEl)
        waitForElementVisible(By.cssSelector(".p-multiselect-panel"), 5)
        WebDriver driver = DriverFactory.getWebDriver()
        for (String opt : optionTexts) {
            WebElement item = driver.findElement(By.xpath("//li[contains(@class, 'p-multiselect-item') and contains(., '" + opt + "')]"))
            clickElement(item)
        }
        WebElement closeBtn = driver.findElement(By.cssSelector(".p-multiselect-close"))
        if (closeBtn != null && closeBtn.isDisplayed()) {
            closeBtn.click()
        }
    }

    /**
     * Verify record exists in p-table
     */
    public static void verifyRecordExists(String keyword) {
        WebDriver driver = DriverFactory.getWebDriver()
        List<WebElement> rows = driver.findElements(By.cssSelector("p-table table tbody tr"))
        assert !rows.isEmpty() : "Error: Table contains no data!"
        String firstRowText = rows.get(0).getText()
        assert firstRowText.contains(keyword) : "Error: Keyword '${keyword}' not found in first row!"
    }

    /**
     * Verify record is completely removed from table
     */
    public static void verifyRecordNotExists(String keyword) {
        WebDriver driver = DriverFactory.getWebDriver()
        searchRecord(keyword)
        List<WebElement> rows = driver.findElements(By.cssSelector("p-table table tbody tr"))
        if (rows.isEmpty()) return
        String firstRowText = rows.get(0).getText()
        assert !firstRowText.contains(keyword) || firstRowText.contains("No data") || firstRowText.contains("Không có dữ liệu") : "Error: Record '${keyword}' still exists in table!"
    }

    /**
     * Safely set input value triggering Angular Change Detection
     */
    public static void jsSetInput(WebElement element, String value) {
        WebDriver driver = DriverFactory.getWebDriver()
        JavascriptExecutor js = (JavascriptExecutor) driver
        js.executeScript("""
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, element, value)
    }
}
