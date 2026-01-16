"""
Service for customer features: Wishlist, Recently Viewed, Addresses.
"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from shopmind.models.customer import WishlistItem, RecentlyViewed, Address
from shopmind.models.product import Product, ProductVariant
from shopmind.models.user import User
from shopmind.schemas.customer import (
    WishlistItemCreate,
    WishlistItemUpdate,
    WishlistItemResponse,
    AddressCreate,
    AddressUpdate,
    RecentlyViewedResponse,
)


# --- Wishlist Operations ---


def get_wishlist(db: Session, user: User) -> list[WishlistItem]:
    """Get user's wishlist with variant and product details."""
    return (
        db.query(WishlistItem)
        .options(
            joinedload(WishlistItem.variant)
            .joinedload(ProductVariant.product)
        )
        .filter(WishlistItem.user_id == user.id)
        .order_by(WishlistItem.created_at.desc())
        .all()
    )


def get_wishlist_item(db: Session, user: User, item_id: int) -> WishlistItem | None:
    """Get a specific wishlist item."""
    return (
        db.query(WishlistItem)
        .filter(
            WishlistItem.id == item_id,
            WishlistItem.user_id == user.id,
        )
        .first()
    )


def get_wishlist_item_by_variant(
    db: Session, user: User, variant_id: int
) -> WishlistItem | None:
    """Check if a variant is in the user's wishlist."""
    return (
        db.query(WishlistItem)
        .filter(
            WishlistItem.user_id == user.id,
            WishlistItem.variant_id == variant_id,
        )
        .first()
    )


def add_to_wishlist(
    db: Session, user: User, item_data: WishlistItemCreate
) -> WishlistItem:
    """Add an item to the wishlist."""
    # Check if variant exists
    variant = (
        db.query(ProductVariant)
        .options(joinedload(ProductVariant.product))
        .filter(ProductVariant.id == item_data.variant_id)
        .first()
    )
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    # Check if already in wishlist
    existing = get_wishlist_item_by_variant(db, user, item_data.variant_id)
    if existing:
        # Update notes if provided
        if item_data.notes:
            existing.notes = item_data.notes
            db.commit()
            db.refresh(existing)
        return existing

    # Add new item
    item = WishlistItem(
        user_id=user.id,
        variant_id=item_data.variant_id,
        notes=item_data.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_wishlist_item(
    db: Session, item: WishlistItem, update_data: WishlistItemUpdate
) -> WishlistItem:
    """Update wishlist item notes."""
    item.notes = update_data.notes
    db.commit()
    db.refresh(item)
    return item


def remove_from_wishlist(db: Session, item: WishlistItem) -> None:
    """Remove an item from the wishlist."""
    db.delete(item)
    db.commit()


def clear_wishlist(db: Session, user: User) -> None:
    """Clear all items from the wishlist."""
    db.query(WishlistItem).filter(WishlistItem.user_id == user.id).delete()
    db.commit()


def move_to_cart(db: Session, user: User, item: WishlistItem) -> None:
    """Move wishlist item to cart and remove from wishlist."""
    from shopmind.services import cart as cart_service

    # Add to cart
    cart = cart_service.get_or_create_cart(db, user=user)
    cart_service.add_item(db, cart, item.variant_id, quantity=1)

    # Remove from wishlist
    db.delete(item)
    db.commit()


def build_wishlist_response(item: WishlistItem) -> WishlistItemResponse:
    """Build a wishlist item response with product details."""
    variant = item.variant
    product = variant.product if variant else None

    return WishlistItemResponse(
        id=item.id,
        variant_id=item.variant_id,
        notes=item.notes,
        created_at=item.created_at,
        product_id=product.id if product else None,
        product_name=product.name if product else None,
        product_slug=product.slug if product else None,
        variant_sku=variant.sku if variant else None,
        variant_attributes=variant.attributes if variant else None,
        price=variant.final_price if variant else None,
        is_in_stock=variant.is_in_stock if variant else None,
        image_url=None,  # TODO: Add image support
    )


# --- Recently Viewed Operations ---


def record_product_view(
    db: Session,
    product_id: int,
    user: User | None = None,
    session_id: str | None = None,
) -> None:
    """Record a product view for recently viewed tracking."""
    if not user and not session_id:
        return  # Can't track without user or session

    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return

    # Look for existing record
    if user:
        existing = (
            db.query(RecentlyViewed)
            .filter(
                RecentlyViewed.user_id == user.id,
                RecentlyViewed.product_id == product_id,
            )
            .first()
        )
    else:
        existing = (
            db.query(RecentlyViewed)
            .filter(
                RecentlyViewed.session_id == session_id,
                RecentlyViewed.product_id == product_id,
            )
            .first()
        )

    if existing:
        # Update view time
        existing.viewed_at = datetime.now()
    else:
        # Create new record
        record = RecentlyViewed(
            user_id=user.id if user else None,
            session_id=session_id if not user else None,
            product_id=product_id,
            viewed_at=datetime.now(),
        )
        db.add(record)

    db.commit()


def get_recently_viewed(
    db: Session,
    user: User | None = None,
    session_id: str | None = None,
    limit: int = 10,
) -> list[RecentlyViewed]:
    """Get recently viewed products."""
    query = (
        db.query(RecentlyViewed)
        .options(joinedload(RecentlyViewed.product))
    )

    if user:
        query = query.filter(RecentlyViewed.user_id == user.id)
    elif session_id:
        query = query.filter(RecentlyViewed.session_id == session_id)
    else:
        return []

    return (
        query.order_by(RecentlyViewed.viewed_at.desc())
        .limit(limit)
        .all()
    )


def merge_recently_viewed(db: Session, user: User, session_id: str) -> None:
    """Merge anonymous recently viewed into user's list."""
    # Get session records
    session_records = (
        db.query(RecentlyViewed)
        .filter(RecentlyViewed.session_id == session_id)
        .all()
    )

    for record in session_records:
        # Check if user already has this product
        existing = (
            db.query(RecentlyViewed)
            .filter(
                RecentlyViewed.user_id == user.id,
                RecentlyViewed.product_id == record.product_id,
            )
            .first()
        )

        if existing:
            # Update timestamp if session view is more recent
            if record.viewed_at > existing.viewed_at:
                existing.viewed_at = record.viewed_at
            db.delete(record)
        else:
            # Transfer to user
            record.user_id = user.id
            record.session_id = None

    db.commit()


def clear_recently_viewed(
    db: Session,
    user: User | None = None,
    session_id: str | None = None,
) -> None:
    """Clear recently viewed history."""
    query = db.query(RecentlyViewed)

    if user:
        query = query.filter(RecentlyViewed.user_id == user.id)
    elif session_id:
        query = query.filter(RecentlyViewed.session_id == session_id)
    else:
        return

    query.delete()
    db.commit()


def build_recently_viewed_response(record: RecentlyViewed) -> RecentlyViewedResponse:
    """Build a recently viewed response."""
    product = record.product
    return RecentlyViewedResponse(
        product_id=product.id,
        product_name=product.name,
        product_slug=product.slug,
        base_price=product.base_price,
        image_url=None,  # TODO: Add image support
        viewed_at=record.viewed_at,
    )


# --- Address Operations ---


def get_addresses(db: Session, user: User) -> list[Address]:
    """Get all addresses for a user."""
    return (
        db.query(Address)
        .filter(Address.user_id == user.id)
        .order_by(Address.is_default_shipping.desc(), Address.created_at.desc())
        .all()
    )


def get_address(db: Session, user: User, address_id: int) -> Address | None:
    """Get a specific address."""
    return (
        db.query(Address)
        .filter(
            Address.id == address_id,
            Address.user_id == user.id,
        )
        .first()
    )


def get_default_shipping_address(db: Session, user: User) -> Address | None:
    """Get user's default shipping address."""
    return (
        db.query(Address)
        .filter(
            Address.user_id == user.id,
            Address.is_default_shipping == True,
        )
        .first()
    )


def get_default_billing_address(db: Session, user: User) -> Address | None:
    """Get user's default billing address."""
    return (
        db.query(Address)
        .filter(
            Address.user_id == user.id,
            Address.is_default_billing == True,
        )
        .first()
    )


def create_address(db: Session, user: User, address_data: AddressCreate) -> Address:
    """Create a new address."""
    # If this is the first address, make it default
    existing_count = db.query(Address).filter(Address.user_id == user.id).count()
    is_first = existing_count == 0

    # If setting as default, unset other defaults
    if address_data.is_default_shipping or is_first:
        db.query(Address).filter(
            Address.user_id == user.id,
            Address.is_default_shipping == True,
        ).update({"is_default_shipping": False})

    if address_data.is_default_billing or is_first:
        db.query(Address).filter(
            Address.user_id == user.id,
            Address.is_default_billing == True,
        ).update({"is_default_billing": False})

    address = Address(
        user_id=user.id,
        **address_data.model_dump(),
    )

    # First address is always default
    if is_first:
        address.is_default_shipping = True
        address.is_default_billing = True

    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def update_address(
    db: Session, user: User, address: Address, update_data: AddressUpdate
) -> Address:
    """Update an existing address."""
    update_dict = update_data.model_dump(exclude_unset=True)

    # If setting as default, unset other defaults
    if update_dict.get("is_default_shipping"):
        db.query(Address).filter(
            Address.user_id == user.id,
            Address.id != address.id,
            Address.is_default_shipping == True,
        ).update({"is_default_shipping": False})

    if update_dict.get("is_default_billing"):
        db.query(Address).filter(
            Address.user_id == user.id,
            Address.id != address.id,
            Address.is_default_billing == True,
        ).update({"is_default_billing": False})

    for field, value in update_dict.items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)
    return address


def delete_address(db: Session, user: User, address: Address) -> None:
    """Delete an address."""
    was_default_shipping = address.is_default_shipping
    was_default_billing = address.is_default_billing

    db.delete(address)
    db.commit()

    # If deleted address was default, set another as default
    if was_default_shipping:
        next_address = (
            db.query(Address)
            .filter(Address.user_id == user.id)
            .order_by(Address.created_at.desc())
            .first()
        )
        if next_address:
            next_address.is_default_shipping = True
            db.commit()

    if was_default_billing:
        next_address = (
            db.query(Address)
            .filter(Address.user_id == user.id)
            .order_by(Address.created_at.desc())
            .first()
        )
        if next_address:
            next_address.is_default_billing = True
            db.commit()


def set_default_address(
    db: Session, user: User, address: Address, address_type: str
) -> Address:
    """Set an address as default for shipping or billing."""
    if address_type == "shipping":
        # Unset other shipping defaults
        db.query(Address).filter(
            Address.user_id == user.id,
            Address.id != address.id,
            Address.is_default_shipping == True,
        ).update({"is_default_shipping": False})
        address.is_default_shipping = True
    elif address_type == "billing":
        # Unset other billing defaults
        db.query(Address).filter(
            Address.user_id == user.id,
            Address.id != address.id,
            Address.is_default_billing == True,
        ).update({"is_default_billing": False})
        address.is_default_billing = True

    db.commit()
    db.refresh(address)
    return address
