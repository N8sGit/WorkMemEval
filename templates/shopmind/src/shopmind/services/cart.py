"""
Cart service for managing shopping carts.

Carts can be:
- User-linked: Persistent cart for logged-in users
- Session-based: Temporary cart for anonymous users

Anonymous carts can be merged into user cart on login.
"""

from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from shopmind.models.order import Cart, CartItem
from shopmind.models.product import ProductVariant
from shopmind.models.user import User


def get_or_create_cart(
    db: Session,
    user: User | None = None,
    session_id: str | None = None,
) -> Cart:
    """
    Get existing cart or create a new one.

    For logged-in users, uses user_id.
    For anonymous users, uses session_id.
    """
    if user:
        cart = (
            db.query(Cart)
            .options(joinedload(Cart.items).joinedload(CartItem.variant).joinedload(ProductVariant.product))
            .filter(Cart.user_id == user.id)
            .first()
        )
        if not cart:
            cart = Cart(user_id=user.id)
            db.add(cart)
            db.commit()
            db.refresh(cart)
    elif session_id:
        cart = (
            db.query(Cart)
            .options(joinedload(Cart.items).joinedload(CartItem.variant).joinedload(ProductVariant.product))
            .filter(Cart.session_id == session_id)
            .first()
        )
        if not cart:
            cart = Cart(session_id=session_id)
            db.add(cart)
            db.commit()
            db.refresh(cart)
    else:
        raise ValueError("Either user or session_id must be provided")

    return cart


def get_cart(
    db: Session,
    user: User | None = None,
    session_id: str | None = None,
) -> Cart | None:
    """Get cart without creating if it doesn't exist."""
    if user:
        return (
            db.query(Cart)
            .options(joinedload(Cart.items).joinedload(CartItem.variant).joinedload(ProductVariant.product))
            .filter(Cart.user_id == user.id)
            .first()
        )
    elif session_id:
        return (
            db.query(Cart)
            .options(joinedload(Cart.items).joinedload(CartItem.variant).joinedload(ProductVariant.product))
            .filter(Cart.session_id == session_id)
            .first()
        )
    return None


def add_item(
    db: Session,
    cart: Cart,
    variant_id: int,
    quantity: int = 1,
) -> CartItem:
    """
    Add item to cart or update quantity if already exists.

    Validates that variant exists and is active.
    """
    # Validate variant
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant or not variant.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found",
        )

    if not variant.product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not available",
        )

    # Check if item already in cart
    existing_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.variant_id == variant_id)
        .first()
    )

    if existing_item:
        existing_item.quantity += quantity
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        cart_item = CartItem(
            cart_id=cart.id,
            variant_id=variant_id,
            quantity=quantity,
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        return cart_item


def update_item_quantity(
    db: Session,
    cart: Cart,
    item_id: int,
    quantity: int,
) -> CartItem | None:
    """
    Update cart item quantity.

    If quantity is 0, removes the item.
    Returns None if item was removed.
    """
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    if quantity <= 0:
        db.delete(item)
        db.commit()
        return None

    item.quantity = quantity
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, cart: Cart, item_id: int) -> None:
    """Remove item from cart."""
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found",
        )

    db.delete(item)
    db.commit()


def clear_cart(db: Session, cart: Cart) -> None:
    """Remove all items from cart."""
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()


def merge_carts(db: Session, user: User, session_id: str) -> Cart:
    """
    Merge anonymous cart into user cart on login.

    Items from session cart are added to user cart.
    Session cart is deleted after merge.
    """
    user_cart = get_or_create_cart(db, user=user)
    session_cart = get_cart(db, session_id=session_id)

    if not session_cart or not session_cart.items:
        return user_cart

    # Merge items
    for session_item in session_cart.items:
        existing = (
            db.query(CartItem)
            .filter(
                CartItem.cart_id == user_cart.id,
                CartItem.variant_id == session_item.variant_id,
            )
            .first()
        )

        if existing:
            # Combine quantities
            existing.quantity += session_item.quantity
        else:
            # Move item to user cart
            new_item = CartItem(
                cart_id=user_cart.id,
                variant_id=session_item.variant_id,
                quantity=session_item.quantity,
            )
            db.add(new_item)

    # Delete session cart
    db.delete(session_cart)
    db.commit()
    db.refresh(user_cart)

    return user_cart


def get_cart_summary(cart: Cart | None) -> dict:
    """Get lightweight cart summary for header display."""
    if not cart:
        return {"item_count": 0, "subtotal": Decimal("0.00")}

    return {
        "item_count": cart.item_count,
        "subtotal": cart.subtotal,
    }
