from pages.login_page import LoginPage


def test_login_success():
    """Validates successful authentication workflow adhering to Clean POM."""
    login_page = LoginPage()
    login_page.navigate("https://ecommerce-demo.local/login")
    login_page.login("automation_tester", "SecretPass2026!")

    assert login_page.is_authenticated() is True
