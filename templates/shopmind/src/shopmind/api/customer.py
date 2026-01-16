"""
Customer feature API endpoints: Wishlist, Recently Viewed, Addresses.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.schemas.customer import (
    WishlistItemCreate,
    WishlistItemUpdate,
    WishlistItemResponse,
    WishlistResponse,
    RecentlyViewedResponse,
    RecentlyViewedList,
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    AddressList,
    SetDefaultAddress,
)
from shopmind.services.auth import get_current_user, get_current_user_optional
from shopmind.services import customer as customer_service

router = APIRouter(tags=["Customer"])


# --- Wishlist Endpoints ---


@router.get("/wishlist", response_model=WishlistResponse)
def get_wishlist(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> WishlistResponse:
    """Get current user's wishlist."""
    items = customer_service.get_wishlist(db, user)
    return WishlistResponse(
        items=[customer_service.build_wishlist_response(item) for item in items],
        total_items=len(items),
    )


@router.post("/wishlist", response_model=WishlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    item_data: WishlistItemCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> WishlistItemResponse:
    """Add an item to the wishlist."""
    item = customer_service.add_to_wishlist(db, user, item_data)
    # Reload with relationships
    item = customer_service.get_wishlist(db, user)
    wishlist_item = next((i for i in item if i.variant_id == item_data.variant_id), None)
    if wishlist_item:
        return customer_service.build_wishlist_response(wishlist_item)
    raise HTTPException(status_code=500, detail="Failed to add to wishlist")


@router.patch("/wishlist/{item_id}", response_model=WishlistItemResponse)
def update_wishlist_item(
    item_id: int,
    update_data: WishlistItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> WishlistItemResponse:
    """Update wishlist item notes."""
    item = customer_service.get_wishlist_item(db, user, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found",
        )
    item = customer_service.update_wishlist_item(db, item, update_data)
    # Reload with relationships
    items = customer_service.get_wishlist(db, user)
    wishlist_item = next((i for i in items if i.id == item_id), None)
    if wishlist_item:
        return customer_service.build_wishlist_response(wishlist_item)
    raise HTTPException(status_code=500, detail="Failed to update wishlist item")


@router.delete("/wishlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_wishlist(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Remove an item from the wishlist."""
    item = customer_service.get_wishlist_item(db, user, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found",
        )
    customer_service.remove_from_wishlist(db, item)


@router.delete("/wishlist", status_code=status.HTTP_204_NO_CONTENT)
def clear_wishlist(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Clear all items from the wishlist."""
    customer_service.clear_wishlist(db, user)


@router.post("/wishlist/{item_id}/move-to-cart", status_code=status.HTTP_200_OK)
def move_to_cart(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Move a wishlist item to cart."""
    item = customer_service.get_wishlist_item(db, user, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found",
        )
    customer_service.move_to_cart(db, user, item)
    return {"message": "Item moved to cart"}


@router.get("/wishlist/check/{variant_id}")
def check_in_wishlist(
    variant_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Check if a variant is in the user's wishlist."""
    item = customer_service.get_wishlist_item_by_variant(db, user, variant_id)
    return {
        "in_wishlist": item is not None,
        "wishlist_item_id": item.id if item else None,
    }


# --- Recently Viewed Endpoints ---


@router.get("/recently-viewed", response_model=RecentlyViewedList)
def get_recently_viewed(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session_id: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
) -> RecentlyViewedList:
    """Get recently viewed products."""
    records = customer_service.get_recently_viewed(db, user, session_id, limit)
    return RecentlyViewedList(
        items=[customer_service.build_recently_viewed_response(r) for r in records]
    )


@router.delete("/recently-viewed", status_code=status.HTTP_204_NO_CONTENT)
def clear_recently_viewed(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session_id: str | None = Query(None),
) -> None:
    """Clear recently viewed history."""
    customer_service.clear_recently_viewed(db, user, session_id)


# --- Address Endpoints ---


@router.get("/addresses", response_model=AddressList)
def list_addresses(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> AddressList:
    """Get all user addresses."""
    addresses = customer_service.get_addresses(db, user)

    default_shipping = next(
        (a.id for a in addresses if a.is_default_shipping), None
    )
    default_billing = next(
        (a.id for a in addresses if a.is_default_billing), None
    )

    return AddressList(
        addresses=addresses,
        default_shipping_id=default_shipping,
        default_billing_id=default_billing,
    )


@router.get("/addresses/{address_id}", response_model=AddressResponse)
def get_address(
    address_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> AddressResponse:
    """Get a specific address."""
    address = customer_service.get_address(db, user, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )
    return address


@router.post("/addresses", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    address_data: AddressCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> AddressResponse:
    """Create a new address."""
    return customer_service.create_address(db, user, address_data)


@router.patch("/addresses/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: int,
    update_data: AddressUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> AddressResponse:
    """Update an address."""
    address = customer_service.get_address(db, user, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )
    return customer_service.update_address(db, user, address, update_data)


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete an address."""
    address = customer_service.get_address(db, user, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )
    customer_service.delete_address(db, user, address)


@router.post("/addresses/{address_id}/set-default", response_model=AddressResponse)
def set_default_address(
    address_id: int,
    default_data: SetDefaultAddress,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> AddressResponse:
    """Set an address as default for shipping or billing."""
    address = customer_service.get_address(db, user, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )
    return customer_service.set_default_address(db, user, address, default_data.address_type)
