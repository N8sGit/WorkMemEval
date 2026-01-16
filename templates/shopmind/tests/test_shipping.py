"""
Tests for Phase 8: Advanced Checkout features.

Tests shipping methods, guest checkout, and gift orders.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shopmind.models.shipping import ShippingMethod
from shopmind.models.order import Order, Cart, CartItem, OrderStatus
from shopmind.models.product import Product, ProductVariant
from shopmind.models.user import User
from shopmind.services import shipping as shipping_service
from shopmind.services import orders as order_service
from shopmind.schemas.shipping import ShippingMethodCreate, ShippingMethodUpdate
from shopmind.schemas.order import CheckoutRequest, ShippingAddress, GuestInfo


# --- Fixtures ---


@pytest.fixture
def shipping_methods(db_session: Session) -> list[ShippingMethod]:
    """Create test shipping methods."""
    methods = [
        ShippingMethod(
            name="Standard Shipping",
            description="5-7 business days",
            carrier="USPS",
            estimated_days_min=5,
            estimated_days_max=7,
            base_cost=Decimal("5.99"),
            per_item_cost=Decimal("0.50"),
            free_threshold=Decimal("50.00"),
            sort_order=1,
            is_active=True,
        ),
        ShippingMethod(
            name="Express Shipping",
            description="2-3 business days",
            carrier="FedEx",
            estimated_days_min=2,
            estimated_days_max=3,
            base_cost=Decimal("12.99"),
            per_item_cost=Decimal("1.00"),
            free_threshold=None,
            sort_order=2,
            is_active=True,
        ),
        ShippingMethod(
            name="Overnight Shipping",
            description="Next business day",
            carrier="UPS",
            estimated_days_min=1,
            estimated_days_max=1,
            base_cost=Decimal("24.99"),
            per_item_cost=Decimal("2.00"),
            free_threshold=None,
            sort_order=3,
            is_active=True,
        ),
        ShippingMethod(
            name="Inactive Method",
            description="Not available",
            carrier="DHL",
            estimated_days_min=10,
            estimated_days_max=14,
            base_cost=Decimal("3.99"),
            per_item_cost=Decimal("0.25"),
            free_threshold=None,
            sort_order=4,
            is_active=False,
        ),
    ]
    for method in methods:
        db_session.add(method)
    db_session.commit()
    for method in methods:
        db_session.refresh(method)
    return methods


@pytest.fixture
def product_with_variant(db_session: Session) -> tuple[Product, ProductVariant]:
    """Create a test product with variant."""
    product = Product(
        name="Test Product",
        slug="test-product",
        base_price=Decimal("25.00"),
        is_active=True,
    )
    db_session.add(product)
    db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku="TEST-001",
        price_modifier=Decimal("0.00"),  # Final price = 25.00 + 0.00 = 25.00
        stock_quantity=100,
        is_active=True,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(variant)
    return product, variant


@pytest.fixture
def cart_with_items(db_session: Session, test_user: User, product_with_variant) -> Cart:
    """Create a cart with items for checkout testing."""
    product, variant = product_with_variant

    cart = Cart(user_id=test_user.id)
    db_session.add(cart)
    db_session.flush()

    cart_item = CartItem(
        cart_id=cart.id,
        variant_id=variant.id,
        quantity=2,
    )
    db_session.add(cart_item)
    db_session.commit()
    db_session.refresh(cart)
    return cart


@pytest.fixture
def guest_cart(db_session: Session, product_with_variant) -> Cart:
    """Create an anonymous cart for guest checkout testing."""
    product, variant = product_with_variant

    cart = Cart(session_id="test-session-123")
    db_session.add(cart)
    db_session.flush()

    cart_item = CartItem(
        cart_id=cart.id,
        variant_id=variant.id,
        quantity=3,
    )
    db_session.add(cart_item)
    db_session.commit()
    db_session.refresh(cart)
    return cart


# --- Shipping Method Tests ---


class TestShippingMethodModel:
    """Tests for ShippingMethod model."""

    def test_calculate_cost_base_only(self, db_session: Session, shipping_methods):
        """Test cost calculation with base cost only."""
        express = shipping_methods[1]  # Express has no free threshold
        cost = express.calculate_cost(Decimal("30.00"), item_count=2)
        # 12.99 + (1.00 * 2) = 14.99
        assert cost == Decimal("14.99")

    def test_calculate_cost_with_free_threshold(self, db_session: Session, shipping_methods):
        """Test cost becomes zero when above free threshold."""
        standard = shipping_methods[0]  # Free threshold at $50
        # Below threshold
        cost_below = standard.calculate_cost(Decimal("40.00"), item_count=2)
        assert cost_below == Decimal("6.99")  # 5.99 + 0.50*2

        # At threshold
        cost_at = standard.calculate_cost(Decimal("50.00"), item_count=2)
        assert cost_at == Decimal("0.00")

        # Above threshold
        cost_above = standard.calculate_cost(Decimal("100.00"), item_count=5)
        assert cost_above == Decimal("0.00")

    def test_estimated_delivery_property(self, db_session: Session, shipping_methods):
        """Test estimated delivery string generation."""
        standard = shipping_methods[0]
        assert standard.estimated_delivery == "5-7 business days"

        overnight = shipping_methods[2]
        assert overnight.estimated_delivery == "1 business days"


class TestShippingService:
    """Tests for shipping service functions."""

    def test_list_shipping_methods_active_only(self, db_session: Session, shipping_methods):
        """Test listing only active shipping methods."""
        methods = shipping_service.list_shipping_methods(db_session, active_only=True)
        assert len(methods) == 3
        assert all(m.is_active for m in methods)

    def test_list_shipping_methods_all(self, db_session: Session, shipping_methods):
        """Test listing all shipping methods including inactive."""
        methods = shipping_service.list_shipping_methods(db_session, active_only=False)
        assert len(methods) == 4

    def test_get_shipping_method(self, db_session: Session, shipping_methods):
        """Test retrieving a specific shipping method."""
        method = shipping_service.get_shipping_method(db_session, shipping_methods[0].id)
        assert method is not None
        assert method.name == "Standard Shipping"

    def test_get_shipping_method_not_found(self, db_session: Session):
        """Test retrieving non-existent shipping method."""
        method = shipping_service.get_shipping_method(db_session, 99999)
        assert method is None

    def test_create_shipping_method(self, db_session: Session):
        """Test creating a new shipping method."""
        data = ShippingMethodCreate(
            name="Economy Shipping",
            description="10-14 business days",
            carrier="USPS",
            estimated_days_min=10,
            estimated_days_max=14,
            base_cost=Decimal("2.99"),
            per_item_cost=Decimal("0.25"),
            free_threshold=Decimal("75.00"),
        )
        method = shipping_service.create_shipping_method(db_session, data)
        assert method.id is not None
        assert method.name == "Economy Shipping"
        assert method.free_threshold == Decimal("75.00")

    def test_update_shipping_method(self, db_session: Session, shipping_methods):
        """Test updating a shipping method."""
        method = shipping_methods[0]
        update_data = ShippingMethodUpdate(
            base_cost=Decimal("7.99"),
            free_threshold=Decimal("75.00"),
        )
        updated = shipping_service.update_shipping_method(db_session, method, update_data)
        assert updated.base_cost == Decimal("7.99")
        assert updated.free_threshold == Decimal("75.00")
        assert updated.name == "Standard Shipping"  # Unchanged

    def test_delete_shipping_method(self, db_session: Session, shipping_methods):
        """Test deleting a shipping method."""
        method = shipping_methods[3]  # Inactive method
        shipping_service.delete_shipping_method(db_session, method)
        deleted = shipping_service.get_shipping_method(db_session, method.id)
        assert deleted is None

    def test_get_shipping_options(self, db_session: Session, shipping_methods):
        """Test getting shipping options with calculated costs."""
        options = shipping_service.get_shipping_options(
            db_session, subtotal=Decimal("30.00"), item_count=2
        )
        assert len(options) == 3  # Only active methods

        # Find standard shipping option
        standard = next(o for o in options if o.name == "Standard Shipping")
        assert standard.cost == Decimal("6.99")  # 5.99 + 0.50*2
        assert not standard.is_free

    def test_get_shipping_options_free_shipping(self, db_session: Session, shipping_methods):
        """Test shipping options when eligible for free shipping."""
        options = shipping_service.get_shipping_options(
            db_session, subtotal=Decimal("60.00"), item_count=2
        )

        standard = next(o for o in options if o.name == "Standard Shipping")
        assert standard.cost == Decimal("0.00")
        assert standard.is_free

    def test_calculate_shipping_cost(self, db_session: Session, shipping_methods):
        """Test calculating shipping cost for a specific method."""
        express = shipping_methods[1]
        cost = shipping_service.calculate_shipping_cost(
            db_session, express.id, Decimal("30.00"), item_count=3
        )
        assert cost == Decimal("15.99")  # 12.99 + 1.00*3

    def test_calculate_shipping_cost_invalid_method(self, db_session: Session):
        """Test calculating shipping cost for invalid method raises error."""
        with pytest.raises(ValueError, match="Invalid shipping method"):
            shipping_service.calculate_shipping_cost(
                db_session, 99999, Decimal("30.00"), item_count=2
            )

    def test_calculate_shipping_cost_inactive_method(self, db_session: Session, shipping_methods):
        """Test calculating shipping cost for inactive method raises error."""
        inactive = shipping_methods[3]
        with pytest.raises(ValueError, match="Invalid shipping method"):
            shipping_service.calculate_shipping_cost(
                db_session, inactive.id, Decimal("30.00"), item_count=2
            )


# --- Guest Checkout Tests ---


class TestGuestCheckout:
    """Tests for guest checkout functionality."""

    def test_guest_checkout_success(
        self, db_session: Session, guest_cart: Cart, shipping_methods
    ):
        """Test successful guest checkout."""
        checkout_data = CheckoutRequest(
            shipping=ShippingAddress(
                name="John Guest",
                address="123 Guest St",
                city="Guestville",
                postal_code="12345",
                country="USA",
            ),
            shipping_method_id=shipping_methods[0].id,
            guest=GuestInfo(
                email="guest@example.com",
                name="John Guest",
            ),
        )

        order = order_service.checkout(db_session, guest_cart, checkout_data, user=None)

        assert order.id is not None
        assert order.user_id is None
        assert order.guest_email == "guest@example.com"
        assert order.guest_name == "John Guest"
        assert order.status == OrderStatus.PENDING
        assert order.shipping_method_name == "Standard Shipping"

    def test_guest_checkout_requires_guest_info(
        self, db_session: Session, guest_cart: Cart, shipping_methods
    ):
        """Test guest checkout fails without guest info."""
        checkout_data = CheckoutRequest(
            shipping=ShippingAddress(
                name="John Guest",
                address="123 Guest St",
                city="Guestville",
                postal_code="12345",
                country="USA",
            ),
            shipping_method_id=shipping_methods[0].id,
            guest=None,
        )

        with pytest.raises(Exception) as exc_info:
            order_service.checkout(db_session, guest_cart, checkout_data, user=None)

        assert "Guest information is required" in str(exc_info.value.detail)


# --- Authenticated Checkout with Shipping Tests ---


class TestAuthenticatedCheckout:
    """Tests for authenticated checkout with shipping methods."""

    def test_checkout_with_selected_shipping_method(
        self, db_session: Session, cart_with_items: Cart, test_user: User, shipping_methods
    ):
        """Test checkout with explicitly selected shipping method."""
        checkout_data = CheckoutRequest(
            shipping=ShippingAddress(
                name="Test User",
                address="456 Test Ave",
                city="Testtown",
                postal_code="54321",
                country="USA",
            ),
            shipping_method_id=shipping_methods[1].id,  # Express
        )

        order = order_service.checkout(db_session, cart_with_items, checkout_data, user=test_user)

        assert order.shipping_method_id == shipping_methods[1].id
        assert order.shipping_method_name == "Express Shipping"
        # 2 items * $25 = $50, Express: 12.99 + 1.00*2 = 14.99
        assert order.shipping_cost == Decimal("14.99")

    def test_checkout_auto_selects_cheapest_shipping(
        self, db_session: Session, cart_with_items: Cart, test_user: User, shipping_methods
    ):
        """Test checkout auto-selects cheapest shipping when not specified."""
        checkout_data = CheckoutRequest(
            shipping=ShippingAddress(
                name="Test User",
                address="456 Test Ave",
                city="Testtown",
                postal_code="54321",
                country="USA",
            ),
            # No shipping_method_id specified
        )

        order = order_service.checkout(db_session, cart_with_items, checkout_data, user=test_user)

        # Should select Standard (cheapest) - but at $50 subtotal, it's free!
        assert order.shipping_method_name == "Standard Shipping"
        assert order.shipping_cost == Decimal("0.00")  # Free threshold met

    def test_checkout_invalid_shipping_method(
        self, db_session: Session, cart_with_items: Cart, test_user: User
    ):
        """Test checkout fails with invalid shipping method."""
        checkout_data = CheckoutRequest(
            shipping=ShippingAddress(
                name="Test User",
                address="456 Test Ave",
                city="Testtown",
                postal_code="54321",
                country="USA",
            ),
            shipping_method_id=99999,
        )

        with pytest.raises(Exception) as exc_info:
            order_service.checkout(db_session, cart_with_items, checkout_data, user=test_user)

        assert "Invalid shipping method" in str(exc_info.value.detail)


# --- Gift Order Tests ---


class TestGiftOrders:
    """Tests for gift order functionality."""

    def test_checkout_with_gift_options(
        self, db_session: Session, cart_with_items: Cart, test_user: User, shipping_methods
    ):
        """Test checkout with gift message."""
        checkout_data = CheckoutRequest(
            shipping=ShippingAddress(
                name="Gift Recipient",
                address="789 Gift Lane",
                city="Giftville",
                postal_code="11111",
                country="USA",
            ),
            shipping_method_id=shipping_methods[0].id,
            is_gift=True,
            gift_message="Happy Birthday! Hope you enjoy this gift!",
        )

        order = order_service.checkout(db_session, cart_with_items, checkout_data, user=test_user)

        assert order.is_gift is True
        assert order.gift_message == "Happy Birthday! Hope you enjoy this gift!"

    def test_checkout_gift_false_ignores_message(
        self, db_session: Session, cart_with_items: Cart, test_user: User, shipping_methods
    ):
        """Test that gift_message is ignored when is_gift is False."""
        checkout_data = CheckoutRequest(
            shipping=ShippingAddress(
                name="Test User",
                address="456 Test Ave",
                city="Testtown",
                postal_code="54321",
                country="USA",
            ),
            shipping_method_id=shipping_methods[0].id,
            is_gift=False,
            gift_message="This should be ignored",
        )

        order = order_service.checkout(db_session, cart_with_items, checkout_data, user=test_user)

        assert order.is_gift is False
        assert order.gift_message is None


# --- Customer Notes Tests ---


class TestCustomerNotes:
    """Tests for customer notes functionality."""

    def test_checkout_with_customer_notes(
        self, db_session: Session, cart_with_items: Cart, test_user: User, shipping_methods
    ):
        """Test checkout with customer notes."""
        checkout_data = CheckoutRequest(
            shipping=ShippingAddress(
                name="Test User",
                address="456 Test Ave",
                city="Testtown",
                postal_code="54321",
                country="USA",
            ),
            shipping_method_id=shipping_methods[0].id,
            customer_notes="Please leave at back door. Ring bell twice.",
        )

        order = order_service.checkout(db_session, cart_with_items, checkout_data, user=test_user)

        assert order.customer_notes == "Please leave at back door. Ring bell twice."


# --- API Tests ---


class TestShippingAPI:
    """Tests for shipping API endpoints."""

    def test_get_shipping_options_endpoint(
        self, client: TestClient, shipping_methods
    ):
        """Test POST /api/shipping/options endpoint."""
        response = client.post(
            "/api/shipping/options",
            json={"subtotal": 30.00, "item_count": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert "options" in data
        assert len(data["options"]) == 3

    def test_list_shipping_methods_endpoint(
        self, client: TestClient, shipping_methods
    ):
        """Test GET /api/shipping/methods endpoint."""
        response = client.get("/api/shipping/methods")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # Only active

    def test_admin_list_all_methods(
        self, client: TestClient, admin_token: str, shipping_methods
    ):
        """Test admin can list all shipping methods including inactive."""
        response = client.get(
            "/api/shipping/admin/methods",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4  # Including inactive

    def test_admin_create_shipping_method(
        self, client: TestClient, admin_token: str
    ):
        """Test admin can create shipping method."""
        response = client.post(
            "/api/shipping/admin/methods",
            json={
                "name": "New Method",
                "description": "Test method",
                "carrier": "TestCarrier",
                "base_cost": 4.99,
                "per_item_cost": 0.50,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Method"
        assert data["id"] is not None

    def test_admin_update_shipping_method(
        self, client: TestClient, admin_token: str, shipping_methods
    ):
        """Test admin can update shipping method."""
        method_id = shipping_methods[0].id
        response = client.patch(
            f"/api/shipping/admin/methods/{method_id}",
            json={"base_cost": 8.99},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["base_cost"] == "8.99"

    def test_admin_delete_shipping_method(
        self, client: TestClient, admin_token: str, shipping_methods
    ):
        """Test admin can delete shipping method."""
        method_id = shipping_methods[3].id  # Inactive method
        response = client.delete(
            f"/api/shipping/admin/methods/{method_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204


class TestGuestCheckoutAPI:
    """Tests for guest checkout API endpoint."""

    def test_guest_checkout_endpoint(
        self, client: TestClient, db_session: Session, product_with_variant, shipping_methods
    ):
        """Test POST /api/orders/checkout/guest endpoint."""
        # Create a guest cart
        product, variant = product_with_variant
        cart = Cart(session_id="api-test-session")
        db_session.add(cart)
        db_session.flush()
        cart_item = CartItem(cart_id=cart.id, variant_id=variant.id, quantity=1)
        db_session.add(cart_item)
        db_session.commit()

        response = client.post(
            "/api/orders/checkout/guest",
            params={"session_id": "api-test-session"},
            json={
                "shipping": {
                    "name": "API Guest",
                    "address": "123 API St",
                    "city": "APICity",
                    "postal_code": "12345",
                    "country": "USA",
                },
                "shipping_method_id": shipping_methods[0].id,
                "guest": {
                    "email": "api-guest@example.com",
                    "name": "API Guest",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert data["status"] == "pending"

    def test_guest_checkout_requires_guest_info(
        self, client: TestClient, db_session: Session, product_with_variant, shipping_methods
    ):
        """Test guest checkout fails without guest info."""
        product, variant = product_with_variant
        cart = Cart(session_id="api-test-session-2")
        db_session.add(cart)
        db_session.flush()
        cart_item = CartItem(cart_id=cart.id, variant_id=variant.id, quantity=1)
        db_session.add(cart_item)
        db_session.commit()

        response = client.post(
            "/api/orders/checkout/guest",
            params={"session_id": "api-test-session-2"},
            json={
                "shipping": {
                    "name": "API Guest",
                    "address": "123 API St",
                    "city": "APICity",
                    "postal_code": "12345",
                    "country": "USA",
                },
                "shipping_method_id": shipping_methods[0].id,
                # No guest info
            },
        )
        assert response.status_code == 400
        assert "Guest information is required" in response.json()["detail"]
