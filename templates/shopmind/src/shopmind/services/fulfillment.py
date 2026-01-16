"""
Fulfillment service.

Handles shipment creation, tracking, and order fulfillment status.
"""

from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from shopmind.models.shipments import Shipment, ShipmentStatus
from shopmind.models.order import Order, OrderItem, OrderStatus
from shopmind.schemas.shipments import (
    ShipmentCreate,
    ShipmentUpdate,
    ShipmentStatusUpdate,
    ShipmentItemResponse,
    OrderFulfillmentStatus,
    ShipmentListResponse,
)
from shopmind.events.base import event_bus, Event
from shopmind.services import orders as order_service
from dataclasses import dataclass


# --- Events ---


@dataclass
class ShipmentCreated(Event):
    """Emitted when a shipment is created."""
    shipment_id: int = 0
    order_id: int = 0


@dataclass
class ShipmentStatusChanged(Event):
    """Emitted when shipment status changes."""
    shipment_id: int = 0
    order_id: int = 0
    old_status: str = ""
    new_status: str = ""


@dataclass
class OrderFullyShipped(Event):
    """Emitted when all items in an order have been shipped."""
    order_id: int = 0


# --- Shipment CRUD ---


def get_shipment(db: Session, shipment_id: int) -> Shipment | None:
    """Get a shipment by ID."""
    return (
        db.query(Shipment)
        .options(joinedload(Shipment.order))
        .filter(Shipment.id == shipment_id)
        .first()
    )


def get_order_shipments(db: Session, order_id: int) -> list[Shipment]:
    """Get all shipments for an order."""
    return (
        db.query(Shipment)
        .filter(Shipment.order_id == order_id)
        .order_by(Shipment.created_at.desc())
        .all()
    )


def get_all_shipments(
    db: Session,
    status_filter: ShipmentStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Shipment], int]:
    """Get all shipments (admin). Optionally filter by status."""
    query = db.query(Shipment)
    if status_filter:
        query = query.filter(Shipment.status == status_filter)

    total = query.count()
    shipments = (
        query.order_by(Shipment.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return shipments, total


# --- Shipment Operations ---


def create_shipment(db: Session, shipment_data: ShipmentCreate) -> Shipment:
    """
    Create a new shipment for an order.

    Validates:
    - Order exists
    - Items belong to order
    - Quantities don't exceed remaining unshipped quantities
    """
    # Get order with items
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.shipments))
        .filter(Order.id == shipment_data.order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check order status (must be at least confirmed)
    if order.status not in (
        OrderStatus.CONFIRMED,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create shipment for order in {order.status.value} status",
        )

    # Build order item lookup
    order_items_map = {item.id: item for item in order.items}

    # Calculate already shipped quantities
    shipped_quantities: dict[int, int] = {}
    for existing_shipment in order.shipments:
        if existing_shipment.status.value not in ("returned", "failed"):
            for item in existing_shipment.items:
                item_id = item.get("order_item_id")
                qty = item.get("quantity", 0)
                shipped_quantities[item_id] = shipped_quantities.get(item_id, 0) + qty

    # Validate and prepare shipment items
    shipment_items = []
    for item in shipment_data.items:
        order_item = order_items_map.get(item.order_item_id)
        if not order_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order item {item.order_item_id} not found in order",
            )

        # Check remaining quantity
        already_shipped = shipped_quantities.get(item.order_item_id, 0)
        remaining = order_item.quantity - already_shipped

        if item.quantity > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot ship {item.quantity} of item {item.order_item_id}. Only {remaining} remaining.",
            )

        shipment_items.append({
            "order_item_id": item.order_item_id,
            "quantity": item.quantity,
        })

    # Create shipment
    shipment = Shipment(
        order_id=order.id,
        status=ShipmentStatus.PENDING,
        carrier=shipment_data.carrier,
        tracking_number=shipment_data.tracking_number,
        tracking_url=shipment_data.tracking_url,
        shipping_method_id=shipment_data.shipping_method_id,
        items=shipment_items,
        notes=shipment_data.notes,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    # Emit event
    event_bus.emit(ShipmentCreated(
        shipment_id=shipment.id,
        order_id=order.id,
    ))

    # Check if order is fully shipped and update status
    check_order_fulfillment(db, order)

    return shipment


def update_shipment(
    db: Session,
    shipment: Shipment,
    update_data: ShipmentUpdate,
) -> Shipment:
    """Update shipment details."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(shipment, field, value)

    db.commit()
    db.refresh(shipment)
    return shipment


def update_shipment_status(
    db: Session,
    shipment: Shipment,
    status_data: ShipmentStatusUpdate,
) -> Shipment:
    """Update shipment status."""
    old_status = shipment.status
    new_status = status_data.status

    # Validate transition
    if not is_valid_status_transition(old_status, new_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition: {old_status.value} -> {new_status.value}",
        )

    shipment.status = new_status

    # Set timestamps
    if new_status == ShipmentStatus.SHIPPED and not shipment.shipped_at:
        shipment.shipped_at = datetime.now()
    elif new_status == ShipmentStatus.DELIVERED and not shipment.delivered_at:
        shipment.delivered_at = datetime.now()

    # Add notes
    if status_data.notes:
        existing_notes = shipment.notes or ""
        shipment.notes = f"{existing_notes}\n[{new_status.value}] {status_data.notes}".strip()

    db.commit()
    db.refresh(shipment)

    # Emit event
    event_bus.emit(ShipmentStatusChanged(
        shipment_id=shipment.id,
        order_id=shipment.order_id,
        old_status=old_status.value,
        new_status=new_status.value,
    ))

    # Check order fulfillment status
    order = db.query(Order).filter(Order.id == shipment.order_id).first()
    if order:
        check_order_fulfillment(db, order)

    return shipment


def is_valid_status_transition(old: ShipmentStatus, new: ShipmentStatus) -> bool:
    """Check if shipment status transition is allowed."""
    valid_transitions = {
        ShipmentStatus.PENDING: {ShipmentStatus.SHIPPED, ShipmentStatus.FAILED},
        ShipmentStatus.SHIPPED: {ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERED, ShipmentStatus.RETURNED},
        ShipmentStatus.IN_TRANSIT: {ShipmentStatus.DELIVERED, ShipmentStatus.RETURNED, ShipmentStatus.FAILED},
        ShipmentStatus.DELIVERED: {ShipmentStatus.RETURNED},
        ShipmentStatus.RETURNED: set(),
        ShipmentStatus.FAILED: {ShipmentStatus.PENDING},  # Can retry
    }
    return new in valid_transitions.get(old, set())


# --- Order Fulfillment ---


def check_order_fulfillment(db: Session, order: Order) -> None:
    """
    Check and update order status based on shipment status.

    - Updates order to SHIPPED when first shipment ships
    - Updates order to DELIVERED when all items delivered
    - Emits OrderFullyShipped event when applicable
    """
    # Refresh order to get latest shipments
    db.refresh(order)

    # Get all non-failed/returned shipments
    active_shipments = [
        s for s in order.shipments
        if s.status.value not in ("returned", "failed")
    ]

    if not active_shipments:
        return

    # Check if any shipment has shipped
    has_shipped = any(
        s.status in (ShipmentStatus.SHIPPED, ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERED)
        for s in active_shipments
    )

    # Update order status if needed
    if has_shipped and order.status == OrderStatus.PROCESSING:
        order.status = OrderStatus.SHIPPED
        db.commit()

    # Check if fully shipped
    if order.is_fully_shipped:
        event_bus.emit(OrderFullyShipped(order_id=order.id))

        # Check if all delivered
        all_delivered = all(
            s.status == ShipmentStatus.DELIVERED
            for s in active_shipments
        )

        if all_delivered and order.status != OrderStatus.DELIVERED:
            order.status = OrderStatus.DELIVERED
            db.commit()


def get_order_fulfillment_status(db: Session, order_id: int) -> OrderFulfillmentStatus:
    """Get detailed fulfillment status for an order."""
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.shipments))
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Calculate totals
    total_items = sum(item.quantity for item in order.items)

    # Get shipped and delivered quantities
    shipped_quantities: dict[int, int] = {}
    delivered_quantities: dict[int, int] = {}

    for shipment in order.shipments:
        if shipment.status.value in ("returned", "failed"):
            continue

        for item in shipment.items:
            item_id = item.get("order_item_id")
            qty = item.get("quantity", 0)
            shipped_quantities[item_id] = shipped_quantities.get(item_id, 0) + qty

            if shipment.status == ShipmentStatus.DELIVERED:
                delivered_quantities[item_id] = delivered_quantities.get(item_id, 0) + qty

    shipped_items = sum(shipped_quantities.values())
    delivered_items = sum(delivered_quantities.values())

    # Build shipment summaries
    shipment_summaries = [
        ShipmentListResponse(
            id=s.id,
            order_id=s.order_id,
            status=s.status,
            carrier=s.carrier,
            tracking_number=s.tracking_number,
            item_count=s.item_count,
            shipped_at=s.shipped_at,
            created_at=s.created_at,
        )
        for s in order.shipments
    ]

    return OrderFulfillmentStatus(
        order_id=order.id,
        total_items=total_items,
        shipped_items=shipped_items,
        delivered_items=delivered_items,
        is_fully_shipped=shipped_items >= total_items,
        is_fully_delivered=delivered_items >= total_items,
        shipments=shipment_summaries,
    )
