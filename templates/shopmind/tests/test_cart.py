"""Tests for shopping cart endpoints."""

from decimal import Decimal


class TestCartGet:
    """Test getting cart."""

    def test_get_empty_cart(self, client, auth_headers):
        """Returns empty cart when no items."""
        response = client.get("/api/cart", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 0
        assert Decimal(data["subtotal"]) == Decimal("0.00")
        assert data["items"] == []

    def test_get_cart_anonymous(self, client):
        """Anonymous users need session ID."""
        response = client.get("/api/cart", headers={"X-Session-ID": "test-session-123"})
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 0

    def test_cart_summary(self, client, auth_headers):
        """Summary endpoint returns lightweight data."""
        response = client.get("/api/cart/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "item_count" in data
        assert "subtotal" in data


class TestCartAdd:
    """Test adding items to cart."""

    def test_add_item_to_cart(self, client, auth_headers, test_variant):
        """Can add item to cart."""
        response = client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": test_variant.id, "quantity": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 2
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

    def test_add_item_increases_quantity(self, client, auth_headers, test_variant):
        """Adding same item increases quantity."""
        # Add 2
        client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": test_variant.id, "quantity": 2},
        )
        # Add 3 more
        response = client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": test_variant.id, "quantity": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 5
        assert data["items"][0]["quantity"] == 5

    def test_add_nonexistent_variant(self, client, auth_headers):
        """Adding nonexistent variant fails."""
        response = client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": 999, "quantity": 1},
        )
        assert response.status_code == 404

    def test_add_requires_auth_or_session(self, client, test_variant):
        """Adding without auth or session fails."""
        response = client.post(
            "/api/cart/items",
            json={"variant_id": test_variant.id, "quantity": 1},
        )
        assert response.status_code == 400

    def test_add_anonymous_with_session(self, client, test_variant):
        """Anonymous users can add with session ID."""
        response = client.post(
            "/api/cart/items",
            headers={"X-Session-ID": "anon-session-123"},
            json={"variant_id": test_variant.id, "quantity": 1},
        )
        assert response.status_code == 200
        assert response.json()["item_count"] == 1


class TestCartUpdate:
    """Test updating cart items."""

    def test_update_item_quantity(self, client, auth_headers, test_variant):
        """Can update item quantity."""
        # Add item
        client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": test_variant.id, "quantity": 2},
        )

        # Get cart to find item ID
        cart = client.get("/api/cart", headers=auth_headers).json()
        item_id = cart["items"][0]["id"]

        # Update quantity
        response = client.patch(
            f"/api/cart/items/{item_id}",
            headers=auth_headers,
            json={"quantity": 5},
        )
        assert response.status_code == 200
        assert response.json()["items"][0]["quantity"] == 5

    def test_update_to_zero_removes_item(self, client, auth_headers, test_variant):
        """Setting quantity to 0 removes item."""
        # Add item
        client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": test_variant.id, "quantity": 2},
        )

        cart = client.get("/api/cart", headers=auth_headers).json()
        item_id = cart["items"][0]["id"]

        # Set to 0
        response = client.patch(
            f"/api/cart/items/{item_id}",
            headers=auth_headers,
            json={"quantity": 0},
        )
        assert response.status_code == 200
        assert response.json()["item_count"] == 0

    def test_update_nonexistent_item(self, client, auth_headers):
        """Updating nonexistent item fails."""
        response = client.patch(
            "/api/cart/items/999",
            headers=auth_headers,
            json={"quantity": 5},
        )
        assert response.status_code == 404


class TestCartRemove:
    """Test removing cart items."""

    def test_remove_item(self, client, auth_headers, test_variant):
        """Can remove item from cart."""
        # Add item
        client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": test_variant.id, "quantity": 2},
        )

        cart = client.get("/api/cart", headers=auth_headers).json()
        item_id = cart["items"][0]["id"]

        # Remove
        response = client.delete(f"/api/cart/items/{item_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["item_count"] == 0

    def test_clear_cart(self, client, auth_headers, test_product):
        """Can clear entire cart."""
        # Add multiple items
        client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": test_product.variants[0].id, "quantity": 2},
        )
        client.post(
            "/api/cart/items",
            headers=auth_headers,
            json={"variant_id": test_product.variants[1].id, "quantity": 1},
        )

        # Verify cart has items
        cart = client.get("/api/cart", headers=auth_headers).json()
        assert cart["item_count"] == 3

        # Clear
        response = client.delete("/api/cart", headers=auth_headers)
        assert response.status_code == 204

        # Verify empty
        cart = client.get("/api/cart", headers=auth_headers).json()
        assert cart["item_count"] == 0


class TestCartMerge:
    """Test merging anonymous cart to user cart."""

    def test_merge_carts(self, client, auth_headers, test_variant, user_token):
        """Anonymous cart merges into user cart on login."""
        session_id = "merge-test-session"

        # Add item to anonymous cart
        client.post(
            "/api/cart/items",
            headers={"X-Session-ID": session_id},
            json={"variant_id": test_variant.id, "quantity": 3},
        )

        # Merge into user cart
        response = client.post(
            "/api/cart/merge",
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Session-ID": session_id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item_count"] == 3

        # Anonymous cart should be gone
        anon_cart = client.get(
            "/api/cart",
            headers={"X-Session-ID": session_id},
        ).json()
        assert anon_cart["item_count"] == 0
