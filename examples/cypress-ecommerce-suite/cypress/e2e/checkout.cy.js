const cartPage = require('../pages/CartPage');

describe('E-Commerce Cart & Discount Coupon Validation', () => {
  beforeEach(() => {
    cartPage.openCart();
  });

  it('TC-ECOM-01: Successfully apply 20% discount coupon to cart', () => {
    cartPage.applyCoupon('SAVE20');
    cartPage.verifyDiscountApplied('-20%');
  });

  it('TC-ECOM-02: Display error when applying invalid or expired coupon', () => {
    cartPage.applyCoupon('EXPIRED_COUPON_999');
    cartPage.verifyCouponError('Mã giảm giá không hợp lệ');
  });
});
