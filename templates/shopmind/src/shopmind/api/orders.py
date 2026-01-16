"""
Order API endpoints.

Handles checkout and order management.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.models.order import OrderStatus
from shopmind.schemas.order import (
    CheckoutRequest,
    CheckoutResponse,
    OrderResponse,
    OrderListResponse,
    OrderStatusUpdate,
    PaginatedOrders,
)
from shopmind.services.auth import get_current_user, get_current_admin
from shopmind.services import orders as order_service
from shopmind.services import cart as cart_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    checkout_data: CheckoutRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> CheckoutResponse:
    """
    Create an order from the current cart (authenticated users).

    Requires authentication. Validates stock availability,
    creates order, deducts stock, and clears cart.

    Supports:
    - Shipping method selection
    - Coupon codes
    - Customer notes
    - Gift options
    """
    cart = cart_service.get_cart(db, user=user)

    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    order = order_service.checkout(db, cart, checkout_data, user=user)

    return CheckoutResponse(
        order_id=order.id,
        status=order.status,
        total=order.total,
    )


@router.post("/checkout/guest", response_model=CheckoutResponse)
def guest_checkout(
    checkout_data: CheckoutRequest,
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> CheckoutResponse:
    """
    Create an order from a session cart (guest checkout).

    Does not require authentication. Guest info is required
    in the checkout_data.guest field.

    Supports:
    - Shipping method selection
    - Coupon codes
    - Customer notes
    - Gift options
    """
    if not checkout_data.guest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest information is required for guest checkout",
        )

    cart = cart_service.get_cart(db, session_id=session_id)

    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    order = order_service.checkout(db, cart, checkout_data, user=None)

    return CheckoutResponse(
        order_id=order.id,
        status=order.status,
        total=order.total,
    )


@router.get("", response_model=PaginatedOrders)
def list_my_orders(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedOrders:
    """Get current user's order history."""
    skip = (page - 1) * page_size
    orders, total = order_service.get_user_orders(db, user, skip=skip, limit=page_size)

    return PaginatedOrders(
        items=[
            OrderListResponse(
                id=order.id,
                status=order.status,
                total=order.total,
                item_count=len(order.items),
                created_at=order.created_at,
            )
            for order in orders
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> OrderResponse:
    """Get order details. Users can only view their own orders."""
    order = order_service.get_order(db, order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Non-admins can only view their own orders
    if order.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return order


# --- Admin Endpoints ---

@router.get("/admin/all", response_model=PaginatedOrders)
def list_all_orders(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    status_filter: OrderStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedOrders:
    """List all orders. **Admin only.**"""
    skip = (page - 1) * page_size
    orders, total = order_service.get_all_orders(
        db,
        status_filter=status_filter,
        skip=skip,
        limit=page_size,
    )

    return PaginatedOrders(
        items=[
            OrderListResponse(
                id=order.id,
                status=order.status,
                total=order.total,
                item_count=len(order.items),
                created_at=order.created_at,
            )
            for order in orders
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> OrderResponse:
    """
    Update order status. **Admin only.**

    Valid transitions:
    - pending -> confirmed, cancelled
    - confirmed -> processing, cancelled
    - processing -> shipped, cancelled
    - shipped -> delivered
    - delivered -> refunded
    """
    order = order_service.get_order(db, order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order_service.update_order_status(
        db,
        order,
        status_data.status,
        status_data.notes,
    )
