"""Tests for order and checkout endpoints."""

from decimal import Decimal


def add_to_cart(client, auth_headers, variant_id, quantity=1):
    """Helper to add item to cart."""
    return client.post(
        "/api/cart/items",
        headers=auth_headers,
        json={"variant_id": variant_id, "quantity": quantity},
    )


def checkout(client, auth_headers, shipping=None):
    """Helper to perform checkout."""
    if shipping is None:
        shipping = {
            "name": "Test User",
            "address": "123 Test St",
            "city": "Test City",
            "postal_code": "12345",
            "country": "USA",
        }
    return client.post(
        "/api/orders/checkout",
        headers=auth_headers,
        json={"shipping": shipping},
    )


class TestCheckout:
    """Test checkout flow."""

    def test_checkout_success(self, client, auth_headers, test_product, db_session):
        """Successful checkout creates order and clears cart."""
        variant = test_product.variants[0]
        initial_stock = variant.stock_quantity

        # Add to cart
        add_to_cart(client, auth_headers, variant.id, quantity=2)

        # Checkout
        response = checkout(client, auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["order_id"] > 0

        # Cart should be empty
        cart = client.get("/api/cart", headers=auth_headers).json()
        assert cart["item_count"] == 0

        # Stock should be reduced
        db_session.refresh(variant)
        assert variant.stock_quantity == initial_stock - 2

    def test_checkout_calculates_totals(self, client, auth_headers, test_product):
        """Checkout calculates subtotal, shipping, tax correctly."""
        # Add 2 items at $29.99 each = $59.98 subtotal
        add_to_cart(client, auth_headers, test_product.variants[0].id, quantity=2)

        response = checkout(client, auth_headers)
        assert response.status_code == 200

        # Get order details
        order_id = response.json()["order_id"]
        order = client.get(f"/api/orders/{order_id}", headers=auth_headers).json()

        assert Decimal(order["subtotal"]) == Decimal("59.98")
        assert Decimal(order["shipping_cost"]) == Decimal("9.99")  # Under $100
        assert Decimal(order["tax"]) == Decimal("4.80")  # 8% of subtotal
        assert Decimal(order["total"]) == Decimal("74.77")

    def test_checkout_free_shipping(self, client, auth_headers, test_product):
        """Free shipping for orders over $100."""
        # Add 4 items at $29.99 = $119.96 (over $100)
        add_to_cart(client, auth_headers, test_product.variants[0].id, quantity=4)

        response = checkout(client, auth_headers)
        order_id = response.json()["order_id"]
        order = client.get(f"/api/orders/{order_id}", headers=auth_headers).json()

        assert Decimal(order["shipping_cost"]) == Decimal("0.00")

    def test_checkout_empty_cart(self, client, auth_headers):
        """Checkout fails with empty cart."""
        response = checkout(client, auth_headers)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_checkout_insufficient_stock(self, client, auth_headers, test_product):
        """Checkout fails when stock insufficient."""
        # Variant has only 10 in stock
        variant = test_product.variants[0]
        add_to_cart(client, auth_headers, variant.id, quantity=20)

        response = checkout(client, auth_headers)
        assert response.status_code == 400
        assert "insufficient" in str(response.json()["detail"]).lower()

    def test_checkout_requires_auth(self, client, test_variant):
        """Checkout requires authentication."""
        response = client.post(
            "/api/orders/checkout",
            json={"shipping": {"name": "Test", "address": "123", "city": "C", "postal_code": "1", "country": "US"}},
        )
        assert response.status_code == 401


class TestOrderList:
    """Test order listing."""

    def test_list_user_orders(self, client, auth_headers, test_product):
        """Users see their own orders."""
        # Create an order
        add_to_cart(client, auth_headers, test_product.variants[0].id)
        checkout(client, auth_headers)

        response = client.get("/api/orders", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_list_orders_pagination(self, client, auth_headers, test_product):
        """Order list supports pagination."""
        # Create multiple orders
        for _ in range(3):
            add_to_cart(client, auth_headers, test_product.variants[0].id)
            checkout(client, auth_headers)

        response = client.get("/api/orders?page=1&page_size=2", headers=auth_headers)
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["pages"] == 2


class TestOrderDetail:
    """Test order detail retrieval."""

    def test_get_order(self, client, auth_headers, test_product):
        """Users can view their order details."""
        add_to_cart(client, auth_headers, test_product.variants[0].id, quantity=2)
        checkout_response = checkout(client, auth_headers)
        order_id = checkout_response.json()["order_id"]

        response = client.get(f"/api/orders/{order_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_id
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

    def test_get_order_not_found(self, client, auth_headers):
        """Returns 404 for nonexistent order."""
        response = client.get("/api/orders/999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_other_user_order(self, client, auth_headers, admin_headers, test_product):
        """Users cannot view other users' orders."""
        # Create order as admin
        add_to_cart(client, admin_headers, test_product.variants[0].id)
        checkout_response = checkout(client, admin_headers)
        order_id = checkout_response.json()["order_id"]

        # Try to view as regular user
        response = client.get(f"/api/orders/{order_id}", headers=auth_headers)
        assert response.status_code == 403

    def test_admin_can_view_any_order(self, client, auth_headers, admin_headers, test_product):
        """Admins can view any order."""
        # Create order as regular user
        add_to_cart(client, auth_headers, test_product.variants[0].id)
        checkout_response = checkout(client, auth_headers)
        order_id = checkout_response.json()["order_id"]

        # View as admin
        response = client.get(f"/api/orders/{order_id}", headers=admin_headers)
        assert response.status_code == 200


class TestOrderStatus:
    """Test order status management."""

    def test_update_order_status(self, client, admin_headers, auth_headers, test_product):
        """Admins can update order status."""
        # Create order
        add_to_cart(client, auth_headers, test_product.variants[0].id)
        order_id = checkout(client, auth_headers).json()["order_id"]

        # Update to confirmed
        response = client.patch(
            f"/api/orders/{order_id}/status",
            headers=admin_headers,
            json={"status": "confirmed", "notes": "Payment verified"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_invalid_status_transition(self, client, admin_headers, auth_headers, test_product):
        """Invalid status transitions are rejected."""
        # Create order (status: pending)
        add_to_cart(client, auth_headers, test_product.variants[0].id)
        order_id = checkout(client, auth_headers).json()["order_id"]

        # Try to skip to shipped (invalid: pending -> shipped)
        response = client.patch(
            f"/api/orders/{order_id}/status",
            headers=admin_headers,
            json={"status": "shipped"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_cancel_order_restores_stock(self, client, admin_headers, auth_headers, test_product, db_session):
        """Cancelling order restores stock."""
        variant = test_product.variants[0]
        initial_stock = variant.stock_quantity

        # Create order
        add_to_cart(client, auth_headers, variant.id, quantity=2)
        order_id = checkout(client, auth_headers).json()["order_id"]

        # Verify stock reduced
        db_session.refresh(variant)
        assert variant.stock_quantity == initial_stock - 2

        # Cancel order
        client.patch(
            f"/api/orders/{order_id}/status",
            headers=admin_headers,
            json={"status": "cancelled"},
        )

        # Stock should be restored
        db_session.refresh(variant)
        assert variant.stock_quantity == initial_stock

    def test_user_cannot_update_status(self, client, auth_headers, test_product):
        """Regular users cannot update order status."""
        add_to_cart(client, auth_headers, test_product.variants[0].id)
        order_id = checkout(client, auth_headers).json()["order_id"]

        response = client.patch(
            f"/api/orders/{order_id}/status",
            headers=auth_headers,
            json={"status": "confirmed"},
        )
        assert response.status_code == 403


class TestAdminOrderList:
    """Test admin order listing."""

    def test_admin_list_all_orders(self, client, admin_headers, auth_headers, test_product):
        """Admins can list all orders."""
        # Create orders as different users
        add_to_cart(client, auth_headers, test_product.variants[0].id)
        checkout(client, auth_headers)

        add_to_cart(client, admin_headers, test_product.variants[0].id)
        checkout(client, admin_headers)

        response = client.get("/api/orders/admin/all", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_admin_filter_by_status(self, client, admin_headers, auth_headers, test_product):
        """Admin can filter orders by status."""
        # Create order and confirm it
        add_to_cart(client, auth_headers, test_product.variants[0].id)
        order_id = checkout(client, auth_headers).json()["order_id"]
        client.patch(
            f"/api/orders/{order_id}/status",
            headers=admin_headers,
            json={"status": "confirmed"},
        )

        # Create another pending order
        add_to_cart(client, auth_headers, test_product.variants[0].id)
        checkout(client, auth_headers)

        # Filter by confirmed
        response = client.get("/api/orders/admin/all?status_filter=confirmed", headers=admin_headers)
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["status"] == "confirmed"
