const BasePage = require('./BasePage');

class CartPage extends BasePage {
  // Encapsulated locators
  get couponInput() {
    return cy.get('input[name="couponCode"]');
  }

  get applyCouponButton() {
    return cy.contains('button', 'Áp dụng');
  }

  get discountBadge() {
    return cy.get('[data-testid="discount-amount"]');
  }

  get errorMessageToast() {
    return cy.get('.toast-error, .notification-error');
  }

  get checkoutButton() {
    return cy.contains('button', 'Tiến hành đặt hàng');
  }

  // Business Action Methods
  openCart() {
    this.navigate('/cart');
  }

  applyCoupon(couponCode) {
    this.couponInput.clear().type(couponCode);
    this.applyCouponButton.click();
    this.waitForSpinnerDetached();
  }

  proceedToCheckout() {
    this.checkoutButton.click();
    this.waitForSpinnerDetached();
  }

  // Verification Methods
  verifyDiscountApplied(expectedDiscount) {
    this.discountBadge.should('be.visible').and('contain.text', expectedDiscount);
  }

  verifyCouponError(expectedError) {
    this.errorMessageToast.should('be.visible').and('contain.text', expectedError);
  }
}

module.exports = new CartPage();
