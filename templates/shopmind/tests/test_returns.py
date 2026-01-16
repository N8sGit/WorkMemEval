"""
Tests for Phase 9: Returns & Fulfillment features.

Tests return requests, approvals, stock restoration, and shipment tracking.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shopmind.models.returns import Return, ReturnStatus, ReturnReason
from shopmind.models.shipments import Shipment, ShipmentStatus
from shopmind.models.order import Order, OrderItem, OrderStatus, Cart, CartItem
from shopmind.models.product import Product, ProductVariant
from shopmind.models.user import User
from shopmind.services import returns as return_service
from shopmind.services import fulfillment as fulfillment_service
from shopmind.schemas.returns import (
    ReturnRequest,
    ReturnApproval,
    ReturnRejection,
    ReturnReceived,
)
from shopmind.schemas.shipments import ShipmentCreate, ShipmentItem, ShipmentStatusUpdate


# --- Fixtures ---


@pytest.fixture
def product_with_stock(db_session: Session) -> tuple[Product, ProductVariant]:
    """Create a test product with variant and stock."""
    product = Product(
        name="Test Product",
        slug="test-product-returns",
        base_price=Decimal("50.00"),
        is_active=True,
    )
    db_session.add(product)
    db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku="TEST-RETURN-001",
        price_modifier=Decimal("0.00"),
        stock_quantity=100,
        is_active=True,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(variant)
    return product, variant


@pytest.fixture
def delivered_order(
    db_session: Session, test_user: User, product_with_stock
) -> Order:
    """Create a delivered order for return testing."""
    product, variant = product_with_stock

    # Create order
    order = Order(
        user_id=test_user.id,
        status=OrderStatus.DELIVERED,
        subtotal=Decimal("100.00"),
        shipping_cost=Decimal("5.00"),
        tax=Decimal("8.00"),
        total=Decimal("113.00"),
        shipping_name="Test User",
        shipping_address="123 Test St",
        shipping_city="Testville",
        shipping_postal_code="12345",
        shipping_country="USA",
    )
    db_session.add(order)
    db_session.flush()

    # Create order items
    order_item = OrderItem(
        order_id=order.id,
        variant_id=variant.id,
        quantity=2,
        unit_price=Decimal("50.00"),
        product_name=product.name,
        variant_sku=variant.sku,
        variant_attributes="{}",
    )
    db_session.add(order_item)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture
def confirmed_order(
    db_session: Session, test_user: User, product_with_stock
) -> Order:
    """Create a confirmed order for shipment testing."""
    product, variant = product_with_stock

    # Reduce stock as if checkout happened
    variant.stock_quantity -= 3
    db_session.commit()

    # Create order
    order = Order(
        user_id=test_user.id,
        status=OrderStatus.CONFIRMED,
        subtotal=Decimal("150.00"),
        shipping_cost=Decimal("5.00"),
        tax=Decimal("12.00"),
        total=Decimal("167.00"),
        shipping_name="Test User",
        shipping_address="123 Test St",
        shipping_city="Testville",
        shipping_postal_code="12345",
        shipping_country="USA",
    )
    db_session.add(order)
    db_session.flush()

    # Create order items
    order_item = OrderItem(
        order_id=order.id,
        variant_id=variant.id,
        quantity=3,
        unit_price=Decimal("50.00"),
        product_name=product.name,
        variant_sku=variant.sku,
        variant_attributes="{}",
    )
    db_session.add(order_item)
    db_session.commit()
    db_session.refresh(order)
    return order


# --- Return Tests ---


class TestReturnModel:
    """Tests for Return model."""

    def test_return_status_flow(self, db_session: Session, delivered_order: Order):
        """Test return status transitions."""
        return_req = Return(
            order_id=delivered_order.id,
            order_item_id=delivered_order.items[0].id,
            user_id=delivered_order.user_id,
            status=ReturnStatus.REQUESTED,
            reason=ReturnReason.DEFECTIVE,
            quantity=1,
        )
        db_session.add(return_req)
        db_session.commit()

        # Test can_* properties
        assert return_req.can_approve is True
        assert return_req.can_reject is True
        assert return_req.can_receive is False
        assert return_req.can_refund is False
        assert return_req.can_cancel is True


class TestReturnService:
    """Tests for return service functions."""

    def test_create_return_request(
        self, db_session: Session, delivered_order: Order, test_user: User
    ):
        """Test creating a return request."""
        request_data = ReturnRequest(
            order_id=delivered_order.id,
            order_item_id=delivered_order.items[0].id,
            reason=ReturnReason.DEFECTIVE,
            reason_details="Product stopped working after one day",
            quantity=1,
        )

        return_req = return_service.create_return_request(
            db_session, request_data, test_user
        )

        assert return_req.id is not None
        assert return_req.status == ReturnStatus.REQUESTED
        assert return_req.reason == ReturnReason.DEFECTIVE
        assert return_req.quantity == 1

    def test_create_return_wrong_order(
        self, db_session: Session, delivered_order: Order
    ):
        """Test return request fails for wrong order."""
        # Create another user
        other_user = User(
            email="other@example.com",
            password_hash="hash",
            full_name="Other User",
        )
        db_session.add(other_user)
        db_session.commit()

        request_data = ReturnRequest(
            order_id=delivered_order.id,
            reason=ReturnReason.CHANGED_MIND,
            quantity=1,
        )

        with pytest.raises(Exception) as exc_info:
            return_service.create_return_request(db_session, request_data, other_user)

        assert "Access denied" in str(exc_info.value.detail)

    def test_approve_return(
        self, db_session: Session, delivered_order: Order, test_user: User
    ):
        """Test approving a return request."""
        # Create return request
        request_data = ReturnRequest(
            order_id=delivered_order.id,
            order_item_id=delivered_order.items[0].id,
            reason=ReturnReason.DEFECTIVE,
            quantity=1,
        )
        return_req = return_service.create_return_request(
            db_session, request_data, test_user
        )

        # Approve it
        approval_data = ReturnApproval(
            refund_amount=Decimal("50.00"),
            admin_notes="Approved - product defect confirmed",
        )
        approved = return_service.approve_return(db_session, return_req, approval_data)

        assert approved.status == ReturnStatus.APPROVED
        assert approved.refund_amount == Decimal("50.00")

    def test_reject_return(
        self, db_session: Session, delivered_order: Order, test_user: User
    ):
        """Test rejecting a return request."""
        request_data = ReturnRequest(
            order_id=delivered_order.id,
            reason=ReturnReason.CHANGED_MIND,
            quantity=1,
        )
        return_req = return_service.create_return_request(
            db_session, request_data, test_user
        )

        rejection_data = ReturnRejection(
            admin_notes="Return window has expired"
        )
        rejected = return_service.reject_return(db_session, return_req, rejection_data)

        assert rejected.status == ReturnStatus.REJECTED

    def test_refund_restores_stock(
        self, db_session: Session, delivered_order: Order, test_user: User, product_with_stock
    ):
        """Test that processing refund restores stock."""
        product, variant = product_with_stock
        initial_stock = variant.stock_quantity

        # Create and approve return
        request_data = ReturnRequest(
            order_id=delivered_order.id,
            order_item_id=delivered_order.items[0].id,
            reason=ReturnReason.DEFECTIVE,
            quantity=1,
        )
        return_req = return_service.create_return_request(
            db_session, request_data, test_user
        )

        approval_data = ReturnApproval(refund_amount=Decimal("50.00"))
        return_service.approve_return(db_session, return_req, approval_data)

        # Mark as received
        received_data = ReturnReceived()
        return_service.mark_return_received(db_session, return_req, received_data)

        # Process refund
        refunded = return_service.process_refund(db_session, return_req)

        assert refunded.status == ReturnStatus.REFUNDED
        assert refunded.stock_restored is True

        # Check stock was restored
        db_session.refresh(variant)
        assert variant.stock_quantity == initial_stock + 1


# --- Shipment Tests ---


class TestShipmentModel:
    """Tests for Shipment model."""

    def test_shipment_item_count(self, db_session: Session, confirmed_order: Order):
        """Test shipment item count calculation."""
        shipment = Shipment(
            order_id=confirmed_order.id,
            status=ShipmentStatus.PENDING,
            items=[
                {"order_item_id": confirmed_order.items[0].id, "quantity": 2},
            ],
        )
        db_session.add(shipment)
        db_session.commit()

        assert shipment.item_count == 2


class TestFulfillmentService:
    """Tests for fulfillment service functions."""

    def test_create_shipment(self, db_session: Session, confirmed_order: Order):
        """Test creating a shipment for an order."""
        # Update order status to allow shipment
        confirmed_order.status = OrderStatus.PROCESSING
        db_session.commit()

        shipment_data = ShipmentCreate(
            order_id=confirmed_order.id,
            items=[ShipmentItem(
                order_item_id=confirmed_order.items[0].id,
                quantity=2,
            )],
            carrier="FedEx",
            tracking_number="FX123456789",
        )

        shipment = fulfillment_service.create_shipment(db_session, shipment_data)

        assert shipment.id is not None
        assert shipment.status == ShipmentStatus.PENDING
        assert shipment.carrier == "FedEx"
        assert shipment.item_count == 2

    def test_create_shipment_exceeds_quantity(
        self, db_session: Session, confirmed_order: Order
    ):
        """Test shipment fails when exceeding order quantity."""
        confirmed_order.status = OrderStatus.PROCESSING
        db_session.commit()

        shipment_data = ShipmentCreate(
            order_id=confirmed_order.id,
            items=[ShipmentItem(
                order_item_id=confirmed_order.items[0].id,
                quantity=10,  # Order only has 3
            )],
        )

        with pytest.raises(Exception) as exc_info:
            fulfillment_service.create_shipment(db_session, shipment_data)

        assert "Cannot ship" in str(exc_info.value.detail)

    def test_partial_fulfillment(self, db_session: Session, confirmed_order: Order):
        """Test creating multiple shipments for partial fulfillment."""
        confirmed_order.status = OrderStatus.PROCESSING
        db_session.commit()

        # First shipment - 2 items
        shipment1_data = ShipmentCreate(
            order_id=confirmed_order.id,
            items=[ShipmentItem(
                order_item_id=confirmed_order.items[0].id,
                quantity=2,
            )],
        )
        shipment1 = fulfillment_service.create_shipment(db_session, shipment1_data)

        # Second shipment - remaining 1 item
        shipment2_data = ShipmentCreate(
            order_id=confirmed_order.id,
            items=[ShipmentItem(
                order_item_id=confirmed_order.items[0].id,
                quantity=1,
            )],
        )
        shipment2 = fulfillment_service.create_shipment(db_session, shipment2_data)

        assert shipment1.item_count == 2
        assert shipment2.item_count == 1

        # Try to create another shipment - should fail
        shipment3_data = ShipmentCreate(
            order_id=confirmed_order.id,
            items=[ShipmentItem(
                order_item_id=confirmed_order.items[0].id,
                quantity=1,
            )],
        )
        with pytest.raises(Exception):
            fulfillment_service.create_shipment(db_session, shipment3_data)

    def test_shipment_status_update(self, db_session: Session, confirmed_order: Order):
        """Test updating shipment status."""
        confirmed_order.status = OrderStatus.PROCESSING
        db_session.commit()

        shipment_data = ShipmentCreate(
            order_id=confirmed_order.id,
            items=[ShipmentItem(
                order_item_id=confirmed_order.items[0].id,
                quantity=3,
            )],
        )
        shipment = fulfillment_service.create_shipment(db_session, shipment_data)

        # Update to shipped
        status_data = ShipmentStatusUpdate(status=ShipmentStatus.SHIPPED)
        updated = fulfillment_service.update_shipment_status(
            db_session, shipment, status_data
        )

        assert updated.status == ShipmentStatus.SHIPPED
        assert updated.shipped_at is not None

    def test_order_status_updates_with_shipment(
        self, db_session: Session, confirmed_order: Order
    ):
        """Test order status updates when shipments progress."""
        confirmed_order.status = OrderStatus.PROCESSING
        db_session.commit()

        shipment_data = ShipmentCreate(
            order_id=confirmed_order.id,
            items=[ShipmentItem(
                order_item_id=confirmed_order.items[0].id,
                quantity=3,
            )],
        )
        shipment = fulfillment_service.create_shipment(db_session, shipment_data)

        # Mark as shipped
        status_data = ShipmentStatusUpdate(status=ShipmentStatus.SHIPPED)
        fulfillment_service.update_shipment_status(db_session, shipment, status_data)

        # Check order was updated
        db_session.refresh(confirmed_order)
        assert confirmed_order.status == OrderStatus.SHIPPED

        # Mark as delivered
        status_data = ShipmentStatusUpdate(status=ShipmentStatus.DELIVERED)
        fulfillment_service.update_shipment_status(db_session, shipment, status_data)

        db_session.refresh(confirmed_order)
        assert confirmed_order.status == OrderStatus.DELIVERED


# --- API Tests ---


class TestReturnAPI:
    """Tests for return API endpoints."""

    def test_create_return_request_endpoint(
        self, client: TestClient, user_token: str, delivered_order: Order
    ):
        """Test POST /api/returns endpoint."""
        response = client.post(
            "/api/returns",
            json={
                "order_id": delivered_order.id,
                "order_item_id": delivered_order.items[0].id,
                "reason": "defective",
                "reason_details": "Product is broken",
                "quantity": 1,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "requested"
        assert data["reason"] == "defective"

    def test_list_my_returns_endpoint(
        self, client: TestClient, user_token: str, db_session: Session, delivered_order: Order, test_user: User
    ):
        """Test GET /api/returns endpoint."""
        # Create a return first
        return_req = Return(
            order_id=delivered_order.id,
            user_id=test_user.id,
            status=ReturnStatus.REQUESTED,
            reason=ReturnReason.DEFECTIVE,
            quantity=1,
        )
        db_session.add(return_req)
        db_session.commit()

        response = client.get(
            "/api/returns",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_admin_approve_return_endpoint(
        self, client: TestClient, admin_token: str, db_session: Session, delivered_order: Order, test_user: User
    ):
        """Test POST /api/returns/admin/{id}/approve endpoint."""
        return_req = Return(
            order_id=delivered_order.id,
            order_item_id=delivered_order.items[0].id,
            user_id=test_user.id,
            status=ReturnStatus.REQUESTED,
            reason=ReturnReason.DEFECTIVE,
            quantity=1,
        )
        db_session.add(return_req)
        db_session.commit()
        db_session.refresh(return_req)

        response = client.post(
            f"/api/returns/admin/{return_req.id}/approve",
            json={
                "refund_amount": 50.00,
                "admin_notes": "Approved",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"


class TestShipmentAPI:
    """Tests for shipment API endpoints."""

    def test_create_shipment_endpoint(
        self, client: TestClient, admin_token: str, confirmed_order: Order, db_session: Session
    ):
        """Test POST /api/shipments/admin endpoint."""
        confirmed_order.status = OrderStatus.PROCESSING
        db_session.commit()

        response = client.post(
            "/api/shipments/admin",
            json={
                "order_id": confirmed_order.id,
                "items": [
                    {"order_item_id": confirmed_order.items[0].id, "quantity": 2}
                ],
                "carrier": "UPS",
                "tracking_number": "1Z999999999999999",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["carrier"] == "UPS"
        assert data["item_count"] == 2

    def test_get_order_fulfillment_status_endpoint(
        self, client: TestClient, user_token: str, confirmed_order: Order, db_session: Session
    ):
        """Test GET /api/shipments/order/{id}/status endpoint."""
        confirmed_order.status = OrderStatus.PROCESSING
        db_session.commit()

        # Create a shipment first
        shipment = Shipment(
            order_id=confirmed_order.id,
            status=ShipmentStatus.SHIPPED,
            items=[{"order_item_id": confirmed_order.items[0].id, "quantity": 2}],
        )
        db_session.add(shipment)
        db_session.commit()

        response = client.get(
            f"/api/shipments/order/{confirmed_order.id}/status",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 3
        assert data["shipped_items"] == 2
        assert data["is_fully_shipped"] is False

    def test_update_shipment_status_endpoint(
        self, client: TestClient, admin_token: str, confirmed_order: Order, db_session: Session
    ):
        """Test PATCH /api/shipments/admin/{id}/status endpoint."""
        confirmed_order.status = OrderStatus.PROCESSING
        db_session.commit()

        shipment = Shipment(
            order_id=confirmed_order.id,
            status=ShipmentStatus.PENDING,
            items=[{"order_item_id": confirmed_order.items[0].id, "quantity": 3}],
        )
        db_session.add(shipment)
        db_session.commit()
        db_session.refresh(shipment)

        response = client.patch(
            f"/api/shipments/admin/{shipment.id}/status",
            json={"status": "shipped"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shipped"
        assert data["shipped_at"] is not None
