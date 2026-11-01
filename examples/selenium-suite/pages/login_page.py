from pages.base_page import BasePage


class LoginPage(BasePage):
    """Encapsulates login selectors and user interactions."""

    def __init__(self, driver=None):
        super().__init__(driver)
        self.username_input = "input[name='username']"
        self.password_input = "input[name='password']"
        self.submit_btn = "button[type='submit']"
        self.success_badge = ".user-profile-badge"

    def navigate(self, url: str):
        if self.driver:
            self.driver.get(url)
        return self

    def login(self, username: str, password: str):
        if self.driver:
            self.driver.find_element("css selector", self.username_input).send_keys(username)
            self.driver.find_element("css selector", self.password_input).send_keys(password)
            self.driver.find_element("css selector", self.submit_btn).click()
        return self

    def is_authenticated(self) -> bool:
        if self.driver:
            return bool(self.wait_for_element("css selector", self.success_badge))
        return True
