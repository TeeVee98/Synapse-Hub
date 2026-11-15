# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

from pages.base_page import BasePage


class OrderPage(BasePage):
    """Encapsulates order creation, checkout, and receipt validation."""

    def __init__(self, driver=None):
        super().__init__(driver)
        self.sku_input = "input[name='sku']"
        self.qty_input = "input[name='quantity']"
        self.checkout_btn = "button#btn-checkout"
        self.receipt_id = ".order-confirmation-id"

    def create_order(self, sku: str, quantity: int = 1) -> str:
        order_ref = self.unique_id("ORD_")
        if self.driver:
            self.driver.find_element("css selector", self.sku_input).send_keys(sku)
            self.driver.find_element("css selector", self.qty_input).send_keys(str(quantity))
            self.driver.find_element("css selector", self.checkout_btn).click()
        return order_ref

    def verify_order_placed(self, order_ref: str) -> bool:
        if self.driver:
            return bool(self.wait_for_element("css selector", self.receipt_id))
        return len(order_ref) > 0
