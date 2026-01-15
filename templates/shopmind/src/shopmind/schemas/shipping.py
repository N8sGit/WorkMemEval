"""
Pydantic schemas for shipping methods.
"""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


# --- Shipping Method Schemas ---


class ShippingMethodCreate(BaseModel):
    """Schema for creating a shipping method (admin)."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    carrier: str | None = Field(None, max_length=50)
    estimated_days_min: int | None = Field(None, ge=0)
    estimated_days_max: int | None = Field(None, ge=0)
    base_cost: Decimal = Field(default=Decimal("0.00"), ge=0)
    per_item_cost: Decimal = Field(default=Decimal("0.00"), ge=0)
    free_threshold: Decimal | None = Field(None, ge=0)
    sort_order: int = 0
    is_active: bool = True


class ShippingMethodUpdate(BaseModel):
    """Schema for updating a shipping method (admin)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    carrier: str | None = None
    estimated_days_min: int | None = None
    estimated_days_max: int | None = None
    base_cost: Decimal | None = Field(None, ge=0)
    per_item_cost: Decimal | None = Field(None, ge=0)
    free_threshold: Decimal | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ShippingMethodResponse(BaseModel):
    """Schema for shipping method in API responses."""

    id: int
    name: str
    description: str | None
    carrier: str | None
    estimated_days_min: int | None
    estimated_days_max: int | None
    estimated_delivery: str | None
    base_cost: Decimal
    per_item_cost: Decimal
    free_threshold: Decimal | None
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ShippingOptionResponse(BaseModel):
    """Schema for a shipping option with calculated cost."""

    id: int
    name: str
    description: str | None
    carrier: str | None
    estimated_delivery: str | None
    cost: Decimal
    is_free: bool = False

    model_config = {"from_attributes": True}


class ShippingOptionsRequest(BaseModel):
    """Request to get shipping options for an order."""

    subtotal: Decimal = Field(..., ge=0)
    item_count: int = Field(..., ge=1)


class ShippingOptionsResponse(BaseModel):
    """Available shipping options for an order."""

    options: list[ShippingOptionResponse]
