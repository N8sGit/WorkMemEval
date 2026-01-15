"""Tests for promotions: Coupons, Cart Rules, Price Tiers, Sale Prices."""

from datetime import datetime, timedelta
from decimal import Decimal
import pytest

from shopmind.models.promotions import Coupon, CartRule, PriceTier, DiscountType, CartRuleType


# --- Fixtures ---


@pytest.fixture
def test_coupon(db_session) -> Coupon:
    """Create a test coupon."""
    coupon = Coupon(
        code="SAVE20",
        description="20% off your order",
        discount_type=DiscountType.PERCENTAGE.value,
        discount_value=Decimal("20.00"),
        is_active=True,
    )
    db_session.add(coupon)
    db_session.commit()
    db_session.refresh(coupon)
    return coupon


@pytest.fixture
def fixed_coupon(db_session) -> Coupon:
    """Create a fixed amount coupon."""
    coupon = Coupon(
        code="FLAT10",
        description="$10 off your order",
        discount_type=DiscountType.FIXED_AMOUNT.value,
        discount_value=Decimal("10.00"),
        min_order_amount=Decimal("50.00"),
        is_active=True,
    )
    db_session.add(coupon)
    db_session.commit()
    db_session.refresh(coupon)
    return coupon


@pytest.fixture
def expired_coupon(db_session) -> Coupon:
    """Create an expired coupon."""
    coupon = Coupon(
        code="EXPIRED",
        discount_type=DiscountType.PERCENTAGE.value,
        discount_value=Decimal("10.00"),
        valid_until=datetime.now() - timedelta(days=1),
        is_active=True,
    )
    db_session.add(coupon)
    db_session.commit()
    db_session.refresh(coupon)
    return coupon


@pytest.fixture
def test_cart_rule(db_session) -> CartRule:
    """Create a test cart rule."""
    rule = CartRule(
        name="Spend $100 Get $10 Off",
        rule_type=CartRuleType.SPEND_X_GET_Y_OFF.value,
        conditions={"min_spend": 100.00},
        discount_type=DiscountType.FIXED_AMOUNT.value,
        discount_value=Decimal("10.00"),
        is_active=True,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


@pytest.fixture
def test_price_tier(db_session, test_variant) -> PriceTier:
    """Create a test price tier."""
    tier = PriceTier(
        variant_id=test_variant.id,
        min_quantity=5,
        price=Decimal("24.99"),
    )
    db_session.add(tier)
    db_session.commit()
    db_session.refresh(tier)
    return tier


# --- Coupon Tests ---


class TestCoupons:
    """Test coupon endpoints."""

    def test_list_coupons_empty(self, client, admin_headers):
        """Returns empty list when no coupons."""
        response = client.get("/api/coupons", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_coupons(self, client, admin_headers, test_coupon):
        """Returns all coupons."""
        response = client.get("/api/coupons", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "SAVE20"

    def test_list_coupons_requires_admin(self, client, auth_headers):
        """Regular users cannot list coupons."""
        response = client.get("/api/coupons", headers=auth_headers)
        assert response.status_code == 403

    def test_create_coupon(self, client, admin_headers):
        """Admins can create coupons."""
        response = client.post(
            "/api/coupons",
            headers=admin_headers,
            json={
                "code": "NEWCODE",
                "discount_type": "percentage",
                "discount_value": "15.00",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "NEWCODE"
        assert data["discount_value"] == "15.00"

    def test_create_coupon_uppercase(self, client, admin_headers):
        """Coupon codes are converted to uppercase."""
        response = client.post(
            "/api/coupons",
            headers=admin_headers,
            json={
                "code": "lowercase",
                "discount_type": "percentage",
                "discount_value": "10.00",
            },
        )
        assert response.status_code == 201
        assert response.json()["code"] == "LOWERCASE"

    def test_create_coupon_duplicate_code(self, client, admin_headers, test_coupon):
        """Cannot create coupon with existing code."""
        response = client.post(
            "/api/coupons",
            headers=admin_headers,
            json={
                "code": test_coupon.code,
                "discount_type": "percentage",
                "discount_value": "10.00",
            },
        )
        assert response.status_code == 400

    def test_update_coupon(self, client, admin_headers, test_coupon):
        """Admins can update coupons."""
        response = client.patch(
            f"/api/coupons/{test_coupon.id}",
            headers=admin_headers,
            json={"discount_value": "25.00"},
        )
        assert response.status_code == 200
        assert response.json()["discount_value"] == "25.00"

    def test_delete_coupon(self, client, admin_headers, test_coupon):
        """Admins can delete coupons."""
        response = client.delete(
            f"/api/coupons/{test_coupon.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

    def test_validate_coupon_valid(self, client, auth_headers, test_coupon, db_session, test_variant):
        """Can validate a valid coupon."""
        # Add item to cart first
        from shopmind.models.order import Cart, CartItem

        cart = Cart(session_id="test-session")
        db_session.add(cart)
        db_session.flush()
        db_session.add(CartItem(cart_id=cart.id, variant_id=test_variant.id, quantity=2))
        db_session.commit()

        response = client.post(
            "/api/coupons/validate",
            headers=auth_headers,
            json={"code": "SAVE20"},
            params={"session_id": "test-session"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["coupon"]["code"] == "SAVE20"

    def test_validate_coupon_invalid(self, client, auth_headers):
        """Returns error for invalid coupon."""
        response = client.post(
            "/api/coupons/validate",
            headers=auth_headers,
            json={"code": "NOTEXIST"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["error_message"] is not None

    def test_validate_coupon_expired(self, client, auth_headers, expired_coupon):
        """Returns error for expired coupon."""
        response = client.post(
            "/api/coupons/validate",
            headers=auth_headers,
            json={"code": "EXPIRED"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert "expired" in data["error_message"].lower()


# --- Cart Rule Tests ---


class TestCartRules:
    """Test cart rule endpoints."""

    def test_list_cart_rules_empty(self, client, admin_headers):
        """Returns empty list when no rules."""
        response = client.get("/api/cart-rules", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_cart_rules(self, client, admin_headers, test_cart_rule):
        """Returns all cart rules."""
        response = client.get("/api/cart-rules", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Spend $100 Get $10 Off"

    def test_create_cart_rule(self, client, admin_headers):
        """Admins can create cart rules."""
        response = client.post(
            "/api/cart-rules",
            headers=admin_headers,
            json={
                "name": "10% Off Electronics",
                "rule_type": "category_discount",
                "conditions": {"category_ids": [1]},
                "discount_type": "percentage",
                "discount_value": "10.00",
            },
        )
        assert response.status_code == 201
        assert response.json()["name"] == "10% Off Electronics"

    def test_update_cart_rule(self, client, admin_headers, test_cart_rule):
        """Admins can update cart rules."""
        response = client.patch(
            f"/api/cart-rules/{test_cart_rule.id}",
            headers=admin_headers,
            json={"name": "Updated Rule"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Rule"

    def test_delete_cart_rule(self, client, admin_headers, test_cart_rule):
        """Admins can delete cart rules."""
        response = client.delete(
            f"/api/cart-rules/{test_cart_rule.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204


# --- Price Tier Tests ---


class TestPriceTiers:
    """Test price tier endpoints."""

    def test_list_price_tiers_empty(self, client, test_variant):
        """Returns empty list when no tiers."""
        response = client.get(f"/api/variants/{test_variant.id}/price-tiers")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_price_tiers(self, client, test_variant, test_price_tier):
        """Returns price tiers for variant."""
        response = client.get(f"/api/variants/{test_variant.id}/price-tiers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["min_quantity"] == 5

    def test_create_price_tier(self, client, admin_headers, test_variant):
        """Admins can create price tiers."""
        response = client.post(
            "/api/price-tiers",
            headers=admin_headers,
            json={
                "variant_id": test_variant.id,
                "min_quantity": 10,
                "price": "19.99",
            },
        )
        assert response.status_code == 201
        assert response.json()["min_quantity"] == 10

    def test_set_price_tiers_bulk(self, client, admin_headers, test_variant):
        """Can replace all price tiers at once."""
        response = client.put(
            f"/api/variants/{test_variant.id}/price-tiers",
            headers=admin_headers,
            json={
                "variant_id": test_variant.id,
                "tiers": [
                    {"min_quantity": 5, "price": "27.99"},
                    {"min_quantity": 10, "price": "24.99"},
                    {"min_quantity": 20, "price": "19.99"},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_delete_price_tier(self, client, admin_headers, test_price_tier):
        """Admins can delete price tiers."""
        response = client.delete(
            f"/api/price-tiers/{test_price_tier.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204


# --- Sale Price Tests ---


class TestSalePrices:
    """Test sale price endpoints."""

    def test_set_sale_price(self, client, admin_headers, test_variant):
        """Admins can set sale price."""
        response = client.put(
            f"/api/variants/{test_variant.id}/sale-price",
            headers=admin_headers,
            json={
                "sale_price": "19.99",
                "sale_start": "2025-01-01T00:00:00",
                "sale_end": "2030-12-31T23:59:59",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sale_price"] == "19.99"
        assert data["is_on_sale"] is True

    def test_set_sale_price_future(self, client, admin_headers, test_variant):
        """Future sale is not active yet."""
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        response = client.put(
            f"/api/variants/{test_variant.id}/sale-price",
            headers=admin_headers,
            json={
                "sale_price": "19.99",
                "sale_start": future_date,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_on_sale"] is False

    def test_clear_sale_price(self, client, admin_headers, test_variant, db_session):
        """Admins can clear sale price."""
        # Set sale price first
        test_variant.sale_price = Decimal("19.99")
        db_session.commit()

        response = client.delete(
            f"/api/variants/{test_variant.id}/sale-price",
            headers=admin_headers,
        )
        assert response.status_code == 204

        # Verify cleared
        db_session.refresh(test_variant)
        assert test_variant.sale_price is None


# --- Cart Discounts Preview ---


class TestCartDiscounts:
    """Test cart discount preview endpoint."""

    def test_preview_cart_discounts_empty(self, client, auth_headers):
        """Returns empty discounts for empty cart."""
        response = client.get("/api/cart/discounts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["discounts"] == []
        assert data["total_discount"] == "0.00"

    def test_preview_cart_discounts_with_coupon(
        self, client, auth_headers, test_coupon, test_variant, db_session, test_user
    ):
        """Returns discount preview with coupon applied."""
        from shopmind.models.order import Cart, CartItem

        # Create cart for the authenticated user
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        db_session.flush()
        db_session.add(CartItem(cart_id=cart.id, variant_id=test_variant.id, quantity=2))
        db_session.commit()

        response = client.get(
            "/api/cart/discounts",
            headers=auth_headers,
            params={"coupon_code": "SAVE20"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["discounts"]) > 0
        assert Decimal(data["total_discount"]) > 0


# --- Checkout with Discounts ---


class TestCheckoutWithDiscounts:
    """Test checkout with discounts applied."""

    def test_checkout_with_coupon(
        self, client, auth_headers, test_coupon, test_variant, db_session, test_user
    ):
        """Checkout applies coupon discount."""
        from shopmind.models.order import Cart, CartItem

        # Create cart for the authenticated user
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        db_session.flush()
        db_session.add(CartItem(cart_id=cart.id, variant_id=test_variant.id, quantity=2))
        db_session.commit()

        response = client.post(
            "/api/orders/checkout",
            headers=auth_headers,
            json={
                "shipping": {
                    "name": "Test User",
                    "address": "123 Test St",
                    "city": "Test City",
                    "postal_code": "12345",
                    "country": "US",
                },
                "coupon_code": "SAVE20",
            },
        )
        assert response.status_code == 200

    def test_checkout_invalid_coupon_fails(
        self, client, auth_headers, test_variant, db_session, test_user
    ):
        """Checkout fails with invalid coupon."""
        from shopmind.models.order import Cart, CartItem

        # Create cart for the authenticated user
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        db_session.flush()
        db_session.add(CartItem(cart_id=cart.id, variant_id=test_variant.id, quantity=2))
        db_session.commit()

        response = client.post(
            "/api/orders/checkout",
            headers=auth_headers,
            json={
                "shipping": {
                    "name": "Test User",
                    "address": "123 Test St",
                    "city": "Test City",
                    "postal_code": "12345",
                    "country": "US",
                },
                "coupon_code": "INVALID",
            },
        )
        assert response.status_code == 400
        assert "coupon" in response.json()["detail"].lower()

    def test_checkout_expired_coupon_fails(
        self, client, auth_headers, expired_coupon, test_variant, db_session, test_user
    ):
        """Checkout fails with expired coupon."""
        from shopmind.models.order import Cart, CartItem

        # Create cart for the authenticated user
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        db_session.flush()
        db_session.add(CartItem(cart_id=cart.id, variant_id=test_variant.id, quantity=2))
        db_session.commit()

        response = client.post(
            "/api/orders/checkout",
            headers=auth_headers,
            json={
                "shipping": {
                    "name": "Test User",
                    "address": "123 Test St",
                    "city": "Test City",
                    "postal_code": "12345",
                    "country": "US",
                },
                "coupon_code": "EXPIRED",
            },
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
