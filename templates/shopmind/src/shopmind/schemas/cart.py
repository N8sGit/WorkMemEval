"""
Pydantic schemas for cart operations.
"""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

from shopmind.schemas.product import VariantResponse


# --- Request Schemas ---

class CartItemAdd(BaseModel):
    """Add item to cart."""

    variant_id: int
    quantity: int = Field(default=1, ge=1, le=100)


class CartItemUpdate(BaseModel):
    """Update cart item quantity."""

    quantity: int = Field(..., ge=0, le=100)  # 0 = remove


# --- Response Schemas ---

class CartItemResponse(BaseModel):
    """Cart item with variant details."""

    id: int
    variant_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    # Denormalized variant info for display
    product_name: str
    variant_sku: str
    variant_attributes: dict

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    """Full cart with items."""

    id: int
    item_count: int
    subtotal: Decimal
    items: list[CartItemResponse]

    model_config = {"from_attributes": True}


class CartSummary(BaseModel):
    """Lightweight cart summary for header display."""

    item_count: int
    subtotal: Decimal
