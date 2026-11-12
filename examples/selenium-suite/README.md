# Selenium WebDriver Clean POM Reference Suite

Enterprise Selenium WebDriver Python automation project adhering to Synapse Hub Clean POM & Flat Architecture standards.

## Architecture Guidelines:
1. **Flat Architecture:** Page Objects in `pages/` subclassing `BasePage`.
2. **Zero-Locator Tests:** `tests/` contains only business operations (`login_page.login(...)`).
3. **Smart Wait:** Prohibits static `time.sleep()`. Enforces `WebDriverWait` polling.
4. **Idempotency:** Dynamic `BasePage.unique_id("ORD_")` to prevent unique key collisions.

## Validation via Synapse Hub:
```bash
# Verify Clean POM and 10 Quality Gates:
npx synapse-hub verify --mode target

# Run AST Linter:
npx synapse-hub lint
```
