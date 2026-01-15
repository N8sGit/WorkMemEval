"""
Pydantic schemas for reviews and stock notifications.
"""

from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


# --- Review Schemas ---


class ReviewCreate(BaseModel):
    """Schema for creating a review."""

    product_id: int
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5 stars")
    title: str | None = Field(None, max_length=255)
    body: str | None = None


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""

    rating: int | None = Field(None, ge=1, le=5)
    title: str | None = Field(None, max_length=255)
    body: str | None = None


class ReviewModerate(BaseModel):
    """Schema for admin moderation actions."""

    is_approved: bool


class ReviewResponse(BaseModel):
    """Schema for review in API responses."""

    id: int
    user_id: int
    product_id: int
    order_id: int | None
    rating: int
    title: str | None
    body: str | None
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime
    updated_at: datetime

    # User info (populated in response)
    user_name: str | None = None

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    """Schema for paginated review list."""

    items: list[ReviewResponse]
    total: int
    page: int
    page_size: int
    pages: int
    avg_rating: float | None = None
    rating_distribution: dict[str, int] | None = None  # {"5": 10, "4": 5, ...}


class ProductRatingSummary(BaseModel):
    """Summary of product ratings."""

    avg_rating: float | None
    review_count: int
    rating_distribution: dict[str, int]  # {"5": 10, "4": 5, "3": 2, "2": 1, "1": 0}


# --- Stock Notification Schemas ---


class StockNotificationCreate(BaseModel):
    """Schema for subscribing to back-in-stock notification."""

    variant_id: int
    email: EmailStr | None = None  # Required for guest users


class StockNotificationResponse(BaseModel):
    """Schema for stock notification in API responses."""

    id: int
    variant_id: int
    email: str | None
    created_at: datetime
    notified_at: datetime | None

    # Variant info
    variant_sku: str | None = None
    product_name: str | None = None

    model_config = {"from_attributes": True}


class StockNotificationList(BaseModel):
    """List of stock notification subscriptions."""

    items: list[StockNotificationResponse]
    total: int
