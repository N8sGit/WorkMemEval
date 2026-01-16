"""
Shopping cart API endpoints.

Supports both authenticated users and anonymous sessions.
"""

from typing import Annotated
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.models.order import Cart
from shopmind.schemas.cart import (
    CartItemAdd,
    CartItemUpdate,
    CartResponse,
    CartItemResponse,
    CartSummary,
)
from shopmind.services.auth import get_current_user, get_current_user_optional
from shopmind.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["Cart"])


def get_session_id(x_session_id: str | None = Header(default=None)) -> str | None:
    """Extract session ID from header for anonymous carts."""
    return x_session_id


def build_cart_response(cart: Cart) -> CartResponse:
    """Convert cart model to response schema."""
    items = []
    for item in cart.items:
        variant = item.variant
        product = variant.product
        items.append(CartItemResponse(
            id=item.id,
            variant_id=variant.id,
            quantity=item.quantity,
            unit_price=variant.final_price,
            subtotal=variant.final_price * item.quantity,
            product_name=product.name,
            variant_sku=variant.sku,
            variant_attributes=variant.attributes,
        ))

    return CartResponse(
        id=cart.id,
        item_count=cart.item_count,
        subtotal=cart.subtotal if cart.items else Decimal("0.00"),
        items=items,
    )


@router.get("", response_model=CartResponse)
def get_cart(
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[str | None, Depends(get_session_id)] = None,
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CartResponse:
    """
    Get the current cart.

    For authenticated users, returns their cart.
    For anonymous users, requires X-Session-ID header.
    """
    cart = cart_service.get_cart(db, user=user, session_id=session_id)

    if not cart:
        # Return empty cart response
        return CartResponse(
            id=0,
            item_count=0,
            subtotal=Decimal("0.00"),
            items=[],
        )

    return build_cart_response(cart)


@router.get("/summary", response_model=CartSummary)
def get_cart_summary(
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[str | None, Depends(get_session_id)] = None,
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CartSummary:
    """Get lightweight cart summary for header display."""
    cart = cart_service.get_cart(db, user=user, session_id=session_id)
    summary = cart_service.get_cart_summary(cart)
    return CartSummary(**summary)


@router.post("/items", response_model=CartResponse)
def add_to_cart(
    item_data: CartItemAdd,
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[str | None, Depends(get_session_id)] = None,
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CartResponse:
    """
    Add item to cart.

    If item already exists, quantity is added to existing.
    """
    if not user and not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication or X-Session-ID header required",
        )

    cart = cart_service.get_or_create_cart(db, user=user, session_id=session_id)
    cart_service.add_item(db, cart, item_data.variant_id, item_data.quantity)

    # Reload cart with items
    cart = cart_service.get_cart(db, user=user, session_id=session_id)
    return build_cart_response(cart)


@router.patch("/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: int,
    item_data: CartItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[str | None, Depends(get_session_id)] = None,
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CartResponse:
    """
    Update cart item quantity.

    Set quantity to 0 to remove item.
    """
    cart = cart_service.get_cart(db, user=user, session_id=session_id)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )

    cart_service.update_item_quantity(db, cart, item_id, item_data.quantity)

    # Reload cart
    cart = cart_service.get_cart(db, user=user, session_id=session_id)
    return build_cart_response(cart)


@router.delete("/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[str | None, Depends(get_session_id)] = None,
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> CartResponse:
    """Remove item from cart."""
    cart = cart_service.get_cart(db, user=user, session_id=session_id)

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )

    cart_service.remove_item(db, cart, item_id)

    # Reload cart
    cart = cart_service.get_cart(db, user=user, session_id=session_id)
    return build_cart_response(cart)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[str | None, Depends(get_session_id)] = None,
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> None:
    """Clear all items from cart."""
    cart = cart_service.get_cart(db, user=user, session_id=session_id)

    if cart:
        cart_service.clear_cart(db, cart)


@router.post("/merge", response_model=CartResponse)
def merge_anonymous_cart(
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[str | None, Depends(get_session_id)],
    user: Annotated[User, Depends(get_current_user)],
) -> CartResponse:
    """
    Merge anonymous cart into user cart after login.

    Call this after user authenticates to preserve their anonymous cart.
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Session-ID header required",
        )

    cart = cart_service.merge_carts(db, user, session_id)
    return build_cart_response(cart)
