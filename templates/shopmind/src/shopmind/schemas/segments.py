"""
Pydantic schemas for customer segments.
"""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


# --- Request Schemas ---


class SegmentCreate(BaseModel):
    """Create a new customer segment."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    discount_percentage: Decimal = Field(..., ge=0, le=100)
    priority: int = Field(default=0)
    min_order_amount: Decimal | None = Field(None, ge=0)
    max_discount_amount: Decimal | None = Field(None, ge=0)
    is_active: bool = True


class SegmentUpdate(BaseModel):
    """Update a customer segment."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    discount_percentage: Decimal | None = Field(None, ge=0, le=100)
    priority: int | None = None
    min_order_amount: Decimal | None = None
    max_discount_amount: Decimal | None = None
    is_active: bool | None = None


class UserSegmentAssignment(BaseModel):
    """Assign a user to a segment."""

    user_id: int
    segment_id: int | None  # None to remove from segment


class BulkSegmentAssignment(BaseModel):
    """Assign multiple users to a segment."""

    user_ids: list[int]
    segment_id: int | None


# --- Response Schemas ---


class SegmentResponse(BaseModel):
    """Customer segment details."""

    id: int
    name: str
    slug: str
    description: str | None
    discount_percentage: Decimal
    priority: int
    min_order_amount: Decimal | None
    max_discount_amount: Decimal | None
    is_active: bool
    user_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SegmentListResponse(BaseModel):
    """Segment summary for list views."""

    id: int
    name: str
    slug: str
    discount_percentage: Decimal
    is_active: bool
    user_count: int = 0

    model_config = {"from_attributes": True}


class UserSegmentInfo(BaseModel):
    """User's segment information."""

    segment_id: int | None
    segment_name: str | None
    discount_percentage: Decimal


class SegmentDiscountPreview(BaseModel):
    """Preview segment discount for an order."""

    segment_name: str | None
    subtotal: Decimal
    discount_amount: Decimal
    discount_percentage: Decimal
    final_subtotal: Decimal
