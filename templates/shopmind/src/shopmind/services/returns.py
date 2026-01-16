"""
Returns service.

Handles return request processing, approval workflow, and stock restoration.
"""

from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from shopmind.models.returns import Return, ReturnStatus, ReturnReason
from shopmind.models.order import Order, OrderItem, OrderStatus
from shopmind.models.product import ProductVariant
from shopmind.models.user import User
from shopmind.schemas.returns import (
    ReturnRequest,
    ReturnApproval,
    ReturnRejection,
    ReturnReceived,
    ReturnRefund,
)
from shopmind.events.base import event_bus, Event
from dataclasses import dataclass


# --- Events ---


@dataclass
class ReturnRequested(Event):
    """Emitted when a return is requested."""
    return_id: int = 0
    order_id: int = 0
    user_id: int = 0


@dataclass
class ReturnStatusChanged(Event):
    """Emitted when return status changes."""
    return_id: int = 0
    old_status: str = ""
    new_status: str = ""


@dataclass
class StockRestored(Event):
    """Emitted when stock is restored from a return."""
    return_id: int = 0
    variant_id: int = 0
    quantity: int = 0


# --- Return CRUD ---


def get_return(db: Session, return_id: int) -> Return | None:
    """Get a return by ID."""
    return (
        db.query(Return)
        .options(joinedload(Return.order), joinedload(Return.order_item))
        .filter(Return.id == return_id)
        .first()
    )


def get_user_returns(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Return], int]:
    """Get paginated returns for a user."""
    query = db.query(Return).filter(Return.user_id == user.id)
    total = query.count()
    returns = (
        query.order_by(Return.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return returns, total


def get_order_returns(db: Session, order_id: int) -> list[Return]:
    """Get all returns for an order."""
    return (
        db.query(Return)
        .filter(Return.order_id == order_id)
        .order_by(Return.created_at.desc())
        .all()
    )


def get_all_returns(
    db: Session,
    status_filter: ReturnStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Return], int]:
    """Get all returns (admin). Optionally filter by status."""
    query = db.query(Return)
    if status_filter:
        query = query.filter(Return.status == status_filter)

    total = query.count()
    returns = (
        query.order_by(Return.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return returns, total


# --- Return Workflow ---


def create_return_request(
    db: Session,
    request_data: ReturnRequest,
    user: User | None = None,
) -> Return:
    """
    Create a new return request.

    Validates:
    - Order exists and is delivered
    - Item belongs to order (if specified)
    - No existing pending return for same item
    """
    # Get order with items
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == request_data.order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Verify user owns the order (if user provided)
    if user and order.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Check order status allows returns (must be delivered)
    if order.status not in (OrderStatus.DELIVERED, OrderStatus.SHIPPED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Returns are only allowed for delivered orders",
        )

    # Validate order item if specified
    order_item = None
    if request_data.order_item_id:
        order_item = next(
            (item for item in order.items if item.id == request_data.order_item_id),
            None,
        )
        if not order_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order item not found in this order",
            )

        # Validate quantity
        if request_data.quantity > order_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot return more than ordered quantity ({order_item.quantity})",
            )

        # Check for existing pending returns for this item
        existing_return = (
            db.query(Return)
            .filter(
                Return.order_item_id == request_data.order_item_id,
                Return.status.in_([
                    ReturnStatus.REQUESTED,
                    ReturnStatus.APPROVED,
                    ReturnStatus.RECEIVED,
                ]),
            )
            .first()
        )
        if existing_return:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A return request already exists for this item",
            )

    # Create return request
    return_request = Return(
        order_id=order.id,
        order_item_id=request_data.order_item_id,
        user_id=user.id if user else order.user_id,
        status=ReturnStatus.REQUESTED,
        reason=request_data.reason,
        reason_details=request_data.reason_details,
        quantity=request_data.quantity,
    )
    db.add(return_request)
    db.commit()
    db.refresh(return_request)

    # Emit event
    event_bus.emit(ReturnRequested(
        return_id=return_request.id,
        order_id=order.id,
        user_id=return_request.user_id or 0,
    ))

    return return_request


def approve_return(
    db: Session,
    return_request: Return,
    approval_data: ReturnApproval,
) -> Return:
    """Approve a return request."""
    if not return_request.can_approve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve return in {return_request.status.value} status",
        )

    old_status = return_request.status
    return_request.status = ReturnStatus.APPROVED
    return_request.refund_amount = approval_data.refund_amount
    return_request.restocking_fee = approval_data.restocking_fee
    if approval_data.admin_notes:
        return_request.admin_notes = approval_data.admin_notes

    db.commit()
    db.refresh(return_request)

    event_bus.emit(ReturnStatusChanged(
        return_id=return_request.id,
        old_status=old_status.value,
        new_status=return_request.status.value,
    ))

    return return_request


def reject_return(
    db: Session,
    return_request: Return,
    rejection_data: ReturnRejection,
) -> Return:
    """Reject a return request."""
    if not return_request.can_reject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject return in {return_request.status.value} status",
        )

    old_status = return_request.status
    return_request.status = ReturnStatus.REJECTED
    return_request.admin_notes = rejection_data.admin_notes

    db.commit()
    db.refresh(return_request)

    event_bus.emit(ReturnStatusChanged(
        return_id=return_request.id,
        old_status=old_status.value,
        new_status=return_request.status.value,
    ))

    return return_request


def mark_return_received(
    db: Session,
    return_request: Return,
    received_data: ReturnReceived,
) -> Return:
    """Mark a return as received at warehouse."""
    if not return_request.can_receive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot mark return as received in {return_request.status.value} status",
        )

    old_status = return_request.status
    return_request.status = ReturnStatus.RECEIVED
    if received_data.return_tracking_number:
        return_request.return_tracking_number = received_data.return_tracking_number
    if received_data.admin_notes:
        existing_notes = return_request.admin_notes or ""
        return_request.admin_notes = f"{existing_notes}\n[Received] {received_data.admin_notes}".strip()

    db.commit()
    db.refresh(return_request)

    event_bus.emit(ReturnStatusChanged(
        return_id=return_request.id,
        old_status=old_status.value,
        new_status=return_request.status.value,
    ))

    return return_request


def process_refund(
    db: Session,
    return_request: Return,
    refund_data: ReturnRefund | None = None,
) -> Return:
    """
    Process refund for a return.

    Also restores stock to inventory.
    """
    if not return_request.can_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process refund in {return_request.status.value} status",
        )

    old_status = return_request.status

    # Override refund amount if provided
    if refund_data and refund_data.refund_amount is not None:
        return_request.refund_amount = refund_data.refund_amount

    if refund_data and refund_data.admin_notes:
        existing_notes = return_request.admin_notes or ""
        return_request.admin_notes = f"{existing_notes}\n[Refund] {refund_data.admin_notes}".strip()

    # Restore stock if not already done
    if not return_request.stock_restored and return_request.order_item_id:
        restore_stock_for_return(db, return_request)

    return_request.status = ReturnStatus.REFUNDED

    db.commit()
    db.refresh(return_request)

    event_bus.emit(ReturnStatusChanged(
        return_id=return_request.id,
        old_status=old_status.value,
        new_status=return_request.status.value,
    ))

    return return_request


def cancel_return(db: Session, return_request: Return) -> Return:
    """Cancel a return request."""
    if not return_request.can_cancel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel return in {return_request.status.value} status",
        )

    old_status = return_request.status
    return_request.status = ReturnStatus.CANCELLED

    db.commit()
    db.refresh(return_request)

    event_bus.emit(ReturnStatusChanged(
        return_id=return_request.id,
        old_status=old_status.value,
        new_status=return_request.status.value,
    ))

    return return_request


# --- Stock Restoration ---


def restore_stock_for_return(db: Session, return_request: Return) -> None:
    """Restore stock to inventory for a return."""
    if return_request.stock_restored:
        return

    if not return_request.order_item_id:
        return

    # Get order item
    order_item = db.query(OrderItem).filter(
        OrderItem.id == return_request.order_item_id
    ).first()

    if not order_item:
        return

    # Get variant and restore stock
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == order_item.variant_id
    ).first()

    if variant:
        variant.stock_quantity += return_request.quantity
        return_request.stock_restored = True

        event_bus.emit(StockRestored(
            return_id=return_request.id,
            variant_id=variant.id,
            quantity=return_request.quantity,
        ))


# --- Utility Functions ---


def calculate_refund_amount(
    db: Session,
    order_item: OrderItem,
    quantity: int,
    restocking_fee_percent: Decimal = Decimal("0"),
) -> Decimal:
    """
    Calculate refund amount for a return.

    Args:
        order_item: The order item being returned
        quantity: Quantity being returned
        restocking_fee_percent: Percentage restocking fee (0-100)

    Returns:
        Calculated refund amount
    """
    item_total = order_item.unit_price * quantity
    restocking_fee = (item_total * restocking_fee_percent / 100).quantize(Decimal("0.01"))
    return item_total - restocking_fee
