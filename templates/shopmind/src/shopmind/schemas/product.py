"""
Pydantic schemas for product-related API operations.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# --- Product Variant Schemas ---

class VariantCreate(BaseModel):
    """Schema for creating a product variant."""

    sku: str = Field(..., min_length=1, max_length=100)
    attributes: dict = Field(default_factory=dict, description="Flexible attributes like size, color")
    price_modifier: Decimal = Field(default=Decimal("0.00"), description="Price adjustment from base")
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)


class VariantUpdate(BaseModel):
    """Schema for updating a product variant."""

    attributes: dict | None = None
    price_modifier: Decimal | None = None
    stock_quantity: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class VariantResponse(BaseModel):
    """Schema for variant data in API responses."""

    id: int
    sku: str
    attributes: dict
    price_modifier: Decimal
    stock_quantity: int
    low_stock_threshold: int
    is_active: bool
    final_price: Decimal
    is_in_stock: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Product Schemas ---

class ProductCreate(BaseModel):
    """Schema for creating a product."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    base_price: Decimal = Field(..., gt=0, description="Base price must be positive")
    has_variants: bool = False

    # Optionally create initial variants inline
    variants: list[VariantCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    base_price: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    """Schema for product data in API responses."""

    id: int
    name: str
    slug: str
    description: str | None
    base_price: Decimal
    has_variants: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    variants: list[VariantResponse] = []

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    """Schema for product data in list endpoints (without variants)."""

    id: int
    name: str
    slug: str
    description: str | None
    base_price: Decimal
    has_variants: bool
    is_active: bool

    model_config = {"from_attributes": True}


# --- Pagination ---

class PaginatedProducts(BaseModel):
    """Paginated list of products."""

    items: list[ProductListResponse]
    total: int
    page: int
    page_size: int
    pages: int
