# Playwright Python Clean POM Reference Suite

Reference **Playwright Python (`pytest-playwright`)** suite adhering strictly to Synapse Hub Clean POM, Smart Waits (`domcontentloaded` + `expect()` web-first assertions), dynamic identifiers (`BasePage.unique_code`), and environment-injected credentials.

## Structure

- `pages/base_page.py`: Shared `BasePage` encapsulation, dynamic data generator, and smart readiness waits.
- `pages/login_page.py`: Page Object encapsulating authentication selectors and explicit `expect()` assertions.
- `tests/test_login.py`: Clean POM test suite with positive, negative, and boundary test scenarios (zero raw selectors).

## Quick Verification

```bash
python tools/lint/infer_linter.py --strict --dir examples/playwright-python-suite
pytest examples/playwright-python-suite -q
```
