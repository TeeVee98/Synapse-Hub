# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

import time


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

    def hydrate_auth_session(self, role: str = "admin") -> bool:
        """Injects pre-authenticated cookies from Synapse SessionVault to bypass login forms."""
        try:
            from tools.session_vault import SessionVault
            vault = SessionVault()
            session_state = vault.load_session(role)
            if not session_state or not self.driver:
                return False
            for cookie in session_state.get("cookies", []):
                cookie_dict = {"name": cookie["name"], "value": cookie["value"]}
                if "domain" in cookie:
                    cookie_dict["domain"] = cookie["domain"]
                if "path" in cookie:
                    cookie_dict["path"] = cookie["path"]
                try:
                    self.driver.add_cookie(cookie_dict)
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
            return True
        except ImportError:
            return False
