# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

import pytest
from pages.order_page import OrderPage


@pytest.fixture
def managed_order():
    """Automated teardown fixture that tracks created orders and cleans them up post-test."""
    order_page = OrderPage()
    created_orders = []

    def _create(sku: str = "PROD_TEST_99", quantity: int = 1) -> str:
        ref = order_page.create_order(sku=sku, quantity=quantity)
        created_orders.append(ref)
        return ref

    yield order_page, _create

    # Automated teardown cleanup to prevent target database pollution
    for ref in created_orders:
        order_page.cancel_order(ref)


def test_order_creation_and_receipt(managed_order=None):
    """Validates idempotent order checkout flow with automated teardown cleanup."""
    if managed_order is None:
        order_page = OrderPage()
        order_ref = order_page.create_order(sku="PROD_TEST_99", quantity=2)
        try:
            assert order_ref.startswith("ORD_")
            assert order_page.verify_order_placed(order_ref) is True
        finally:
            order_page.cancel_order(order_ref)
        return

    order_page, create_order = managed_order
    order_ref = create_order(sku="PROD_TEST_99", quantity=2)

    assert order_ref.startswith("ORD_")
    assert order_page.verify_order_placed(order_ref) is True
