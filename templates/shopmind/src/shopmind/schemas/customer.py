"""
Pydantic schemas for customer features (Wishlist, Recently Viewed, Addresses).
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# --- Wishlist Schemas ---


class WishlistItemBase(BaseModel):
    """Base wishlist item fields."""

    variant_id: int
    notes: str | None = None


class WishlistItemCreate(WishlistItemBase):
    """Add item to wishlist."""

    pass


class WishlistItemUpdate(BaseModel):
    """Update wishlist item notes."""

    notes: str | None = None


class WishlistItemResponse(BaseModel):
    """Wishlist item in API responses."""

    id: int
    variant_id: int
    notes: str | None
    created_at: datetime

    # Denormalized product info for display
    product_id: int | None = None
    product_name: str | None = None
    product_slug: str | None = None
    variant_sku: str | None = None
    variant_attributes: dict | None = None
    price: Decimal | None = None
    is_in_stock: bool | None = None
    image_url: str | None = None

    model_config = {"from_attributes": True}


class WishlistResponse(BaseModel):
    """Full wishlist with items."""

    items: list[WishlistItemResponse]
    total_items: int


# --- Recently Viewed Schemas ---


class RecentlyViewedResponse(BaseModel):
    """Recently viewed product in API responses."""

    product_id: int
    product_name: str
    product_slug: str
    base_price: Decimal
    image_url: str | None = None
    viewed_at: datetime

    model_config = {"from_attributes": True}


class RecentlyViewedList(BaseModel):
    """List of recently viewed products."""

    items: list[RecentlyViewedResponse]


# --- Address Schemas ---


class AddressBase(BaseModel):
    """Base address fields."""

    label: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    is_default_shipping: bool = False
    is_default_billing: bool = False


class AddressCreate(AddressBase):
    """Create a new address."""

    pass


class AddressUpdate(BaseModel):
    """Update an existing address."""

    label: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address_line1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, min_length=1, max_length=20)
    country: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    is_default_shipping: bool | None = None
    is_default_billing: bool | None = None


class AddressResponse(AddressBase):
    """Address in API responses."""

    id: int
    created_at: datetime
    full_address: str

    model_config = {"from_attributes": True}


class AddressList(BaseModel):
    """List of user addresses."""

    addresses: list[AddressResponse]
    default_shipping_id: int | None = None
    default_billing_id: int | None = None


class SetDefaultAddress(BaseModel):
    """Set an address as default."""

    address_type: str = Field(..., pattern="^(shipping|billing)$")
