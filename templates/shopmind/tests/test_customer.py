"""Tests for customer features: Wishlist, Recently Viewed, Addresses."""

import pytest
from decimal import Decimal

from shopmind.models.customer import WishlistItem, Address


# --- Fixtures ---


@pytest.fixture
def test_address(db_session, test_user) -> Address:
    """Create a test address."""
    address = Address(
        user_id=test_user.id,
        label="Home",
        name="Test User",
        address_line1="123 Main St",
        city="Test City",
        postal_code="12345",
        country="US",
        is_default_shipping=True,
        is_default_billing=True,
    )
    db_session.add(address)
    db_session.commit()
    db_session.refresh(address)
    return address


@pytest.fixture
def test_wishlist_item(db_session, test_user, test_variant) -> WishlistItem:
    """Create a test wishlist item."""
    item = WishlistItem(
        user_id=test_user.id,
        variant_id=test_variant.id,
        notes="Want this!",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


# --- Wishlist Tests ---


class TestWishlist:
    """Test wishlist endpoints."""

    def test_get_wishlist_empty(self, client, auth_headers):
        """Returns empty wishlist."""
        response = client.get("/api/wishlist", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_items"] == 0

    def test_get_wishlist(self, client, auth_headers, test_wishlist_item):
        """Returns wishlist with items."""
        response = client.get("/api/wishlist", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 1
        assert len(data["items"]) == 1

    def test_add_to_wishlist(self, client, auth_headers, test_variant):
        """Can add item to wishlist."""
        response = client.post(
            "/api/wishlist",
            headers=auth_headers,
            json={"variant_id": test_variant.id, "notes": "Birthday gift"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["variant_id"] == test_variant.id
        assert data["notes"] == "Birthday gift"

    def test_add_to_wishlist_duplicate(self, client, auth_headers, test_wishlist_item):
        """Adding duplicate updates notes instead of creating new."""
        response = client.post(
            "/api/wishlist",
            headers=auth_headers,
            json={"variant_id": test_wishlist_item.variant_id, "notes": "Updated notes"},
        )
        assert response.status_code == 201

        # Check only one item in wishlist
        response = client.get("/api/wishlist", headers=auth_headers)
        assert response.json()["total_items"] == 1

    def test_add_to_wishlist_invalid_variant(self, client, auth_headers):
        """Returns 404 for nonexistent variant."""
        response = client.post(
            "/api/wishlist",
            headers=auth_headers,
            json={"variant_id": 9999},
        )
        assert response.status_code == 404

    def test_update_wishlist_item(self, client, auth_headers, test_wishlist_item):
        """Can update wishlist item notes."""
        response = client.patch(
            f"/api/wishlist/{test_wishlist_item.id}",
            headers=auth_headers,
            json={"notes": "Changed my mind"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Changed my mind"

    def test_remove_from_wishlist(self, client, auth_headers, test_wishlist_item):
        """Can remove item from wishlist."""
        response = client.delete(
            f"/api/wishlist/{test_wishlist_item.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify removed
        response = client.get("/api/wishlist", headers=auth_headers)
        assert response.json()["total_items"] == 0

    def test_clear_wishlist(self, client, auth_headers, test_wishlist_item):
        """Can clear entire wishlist."""
        response = client.delete("/api/wishlist", headers=auth_headers)
        assert response.status_code == 204

        # Verify cleared
        response = client.get("/api/wishlist", headers=auth_headers)
        assert response.json()["total_items"] == 0

    def test_move_to_cart(self, client, auth_headers, test_wishlist_item):
        """Can move wishlist item to cart."""
        response = client.post(
            f"/api/wishlist/{test_wishlist_item.id}/move-to-cart",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify removed from wishlist
        response = client.get("/api/wishlist", headers=auth_headers)
        assert response.json()["total_items"] == 0

        # Verify in cart
        response = client.get("/api/cart", headers=auth_headers)
        assert response.json()["item_count"] == 1

    def test_check_in_wishlist(self, client, auth_headers, test_wishlist_item):
        """Can check if variant is in wishlist."""
        response = client.get(
            f"/api/wishlist/check/{test_wishlist_item.variant_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["in_wishlist"] is True
        assert data["wishlist_item_id"] == test_wishlist_item.id

    def test_check_not_in_wishlist(self, client, auth_headers, test_variant):
        """Returns false for variant not in wishlist."""
        response = client.get(
            f"/api/wishlist/check/{test_variant.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["in_wishlist"] is False
        assert data["wishlist_item_id"] is None

    def test_wishlist_requires_auth(self, client):
        """Wishlist endpoints require authentication."""
        response = client.get("/api/wishlist")
        assert response.status_code == 401


# --- Recently Viewed Tests ---


class TestRecentlyViewed:
    """Test recently viewed endpoints."""

    def test_get_recently_viewed_empty(self, client, auth_headers):
        """Returns empty list when no recently viewed."""
        response = client.get("/api/recently-viewed", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_product_view_tracked(self, client, auth_headers, test_product):
        """Viewing a product tracks it as recently viewed."""
        # View the product
        response = client.get(
            f"/api/products/{test_product.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Check recently viewed
        response = client.get("/api/recently-viewed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == test_product.id

    def test_product_view_tracked_anonymous(self, client, test_product):
        """Anonymous users can track recently viewed with session."""
        session_id = "anon-session-123"

        # View the product
        response = client.get(
            f"/api/products/{test_product.id}",
            params={"session_id": session_id},
        )
        assert response.status_code == 200

        # Check recently viewed
        response = client.get(
            "/api/recently-viewed",
            params={"session_id": session_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    def test_clear_recently_viewed(self, client, auth_headers, test_product):
        """Can clear recently viewed history."""
        # View a product first
        client.get(f"/api/products/{test_product.id}", headers=auth_headers)

        # Clear history
        response = client.delete("/api/recently-viewed", headers=auth_headers)
        assert response.status_code == 204

        # Verify cleared
        response = client.get("/api/recently-viewed", headers=auth_headers)
        assert response.json()["items"] == []


# --- Address Tests ---


class TestAddresses:
    """Test address endpoints."""

    def test_list_addresses_empty(self, client, auth_headers):
        """Returns empty list when no addresses."""
        response = client.get("/api/addresses", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["addresses"] == []
        assert data["default_shipping_id"] is None

    def test_list_addresses(self, client, auth_headers, test_address):
        """Returns all user addresses."""
        response = client.get("/api/addresses", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["addresses"]) == 1
        assert data["default_shipping_id"] == test_address.id

    def test_get_address(self, client, auth_headers, test_address):
        """Get a specific address."""
        response = client.get(
            f"/api/addresses/{test_address.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Home"
        assert data["city"] == "Test City"

    def test_get_address_not_found(self, client, auth_headers):
        """Returns 404 for nonexistent address."""
        response = client.get("/api/addresses/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_create_address(self, client, auth_headers):
        """Can create a new address."""
        response = client.post(
            "/api/addresses",
            headers=auth_headers,
            json={
                "label": "Work",
                "name": "Test User",
                "address_line1": "456 Office Blvd",
                "city": "Work City",
                "postal_code": "67890",
                "country": "US",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "Work"
        # First address should be default
        assert data["is_default_shipping"] is True

    def test_create_second_address(self, client, auth_headers, test_address):
        """Second address is not default by default."""
        response = client.post(
            "/api/addresses",
            headers=auth_headers,
            json={
                "label": "Work",
                "name": "Test User",
                "address_line1": "456 Office Blvd",
                "city": "Work City",
                "postal_code": "67890",
                "country": "US",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_default_shipping"] is False

    def test_update_address(self, client, auth_headers, test_address):
        """Can update an address."""
        response = client.patch(
            f"/api/addresses/{test_address.id}",
            headers=auth_headers,
            json={"label": "Old Home", "city": "New City"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Old Home"
        assert data["city"] == "New City"

    def test_delete_address(self, client, auth_headers, test_address):
        """Can delete an address."""
        response = client.delete(
            f"/api/addresses/{test_address.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify deleted
        response = client.get("/api/addresses", headers=auth_headers)
        assert len(response.json()["addresses"]) == 0

    def test_set_default_shipping(self, client, auth_headers, test_address, db_session, test_user):
        """Can set an address as default shipping."""
        # Create a second address
        second = Address(
            user_id=test_user.id,
            label="Work",
            name="Test User",
            address_line1="456 Work St",
            city="Work City",
            postal_code="67890",
            country="US",
        )
        db_session.add(second)
        db_session.commit()
        db_session.refresh(second)

        # Set second as default shipping
        response = client.post(
            f"/api/addresses/{second.id}/set-default",
            headers=auth_headers,
            json={"address_type": "shipping"},
        )
        assert response.status_code == 200
        assert response.json()["is_default_shipping"] is True

        # Verify first is no longer default
        db_session.refresh(test_address)
        assert test_address.is_default_shipping is False

    def test_addresses_require_auth(self, client):
        """Address endpoints require authentication."""
        response = client.get("/api/addresses")
        assert response.status_code == 401
