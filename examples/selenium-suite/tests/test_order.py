from pages.order_page import OrderPage


def test_order_creation_and_receipt():
    """Validates idempotent order checkout flow."""
    order_page = OrderPage()
    order_ref = order_page.create_order(sku="PROD_TEST_99", quantity=2)

    assert order_ref.startswith("ORD_")
    assert order_page.verify_order_placed(order_ref) is True
