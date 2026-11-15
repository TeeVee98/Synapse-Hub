# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

import time
from typing import Optional


class BasePage:
    """
    BasePage encapsulating Selenium WebDriver interactions with Clean POM discipline.
    Enforces dynamic smart waits and zero-locator test script policy.
    """

    def __init__(self, driver=None):
        self.driver = driver

    @staticmethod
    def unique_id(prefix: str = "AUTO_") -> str:
        """Generates dynamic unique timestamped string to prevent collisions."""
        return f"{prefix}{int(time.time() * 1000)}"

    def wait_for_element(self, by, locator: str, timeout: int = 10):
        """Simulates smart wait for element visibility without static time.sleep."""
        if self.driver is None:
            return True
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, locator))
        )
