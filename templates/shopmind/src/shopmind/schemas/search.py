"""
Pydantic schemas for product search and filtering.
"""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel


# --- Facet Response Schemas ---


class CategoryFacet(BaseModel):
    """Category option with product count."""

    id: int
    name: str
    slug: str
    count: int


class TagFacet(BaseModel):
    """Tag option with product count."""

    id: int
    name: str
    slug: str
    count: int


class PriceRange(BaseModel):
    """Min/max price range for products."""

    min: Decimal
    max: Decimal


class FacetResponse(BaseModel):
    """Available filter options with counts."""

    categories: list[CategoryFacet] = []
    tags: list[TagFacet] = []
    price_range: PriceRange | None = None
    in_stock_count: int = 0
    on_sale_count: int = 0


# --- Search Result Schemas ---


class SearchProductVariant(BaseModel):
    """Variant summary for search results."""

    id: int
    sku: str
    final_price: Decimal
    is_in_stock: bool
    is_on_sale: bool = False

    model_config = {"from_attributes": True}


class SearchProductResult(BaseModel):
    """Product in search results."""

    id: int
    name: str
    slug: str
    description: str | None
    base_price: Decimal
    min_price: Decimal | None = None  # Lowest variant price
    max_price: Decimal | None = None  # Highest variant price
    is_in_stock: bool = False  # True if any variant in stock
    is_on_sale: bool = False  # True if any variant on sale
    category_ids: list[int] = []
    tag_slugs: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    """Search results with facets and pagination."""

    items: list[SearchProductResult]
    total: int
    page: int
    page_size: int
    pages: int
    facets: FacetResponse
    query: str | None = None  # Echo back the search query
