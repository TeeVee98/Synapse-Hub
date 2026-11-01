# Katalon Studio Clean POM Reference Suite

Enterprise Katalon Studio web automation project adhering to Synapse Hub Clean POM & Flat Architecture standards.

## Architecture Guidelines Enforced:
1. **Flat Architecture:** All Page Classes reside in `Keywords/pages/` extending `BasePage`.
2. **Zero-Locator Scripts:** Test scripts in `Scripts/` contain only business method calls. Zero raw XPaths or CSS selectors.
3. **Smart Wait:** Prohibits static `Thread.sleep`. Uses dynamic smart waits.
4. **Idempotent Data:** Dynamic `BasePage.uniqueCode("AUTO_")` with timestamps.

## Validation via Synapse Hub:
```bash
# Validate Clean POM and 9 Quality Gates DoD:
npx synapse-hub verify --mode target

# Run AST Linter:
npx synapse-hub lint
```
