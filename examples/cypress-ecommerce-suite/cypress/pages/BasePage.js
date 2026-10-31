/**
 * BasePage — Universal Cypress Base Page Object
 * Enforces dynamic idempotency, smart waiting, and common interactions.
 */
class BasePage {
  /**
   * Generates dynamic unique identifier for test data isolation.
   */
  static uniqueCode(prefix = 'AUTO_') {
    return `${prefix}${Date.now()}_${Math.floor(Math.random() * 1000)}`;
  }

  /**
   * Waits for loading spinner/overlay detachment.
   */
  waitForSpinnerDetached() {
    cy.get('.spinner-overlay, .loading-backdrop', { timeout: 10000 }).should('not.exist');
  }

  /**
   * Navigates to a relative path.
   */
  navigate(path = '/') {
    cy.visit(path);
    this.waitForSpinnerDetached();
  }
}

module.exports = BasePage;
