"""
Pydantic schemas for catalog organization (Categories, Tags, Collections).
"""

from datetime import datetime
from pydantic import BaseModel, Field

from shopmind.schemas.product import ProductListResponse


# --- Category Schemas ---

class CategoryBase(BaseModel):
    """Base category fields."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """Create a new category."""

    parent_id: int | None = None


class CategoryUpdate(BaseModel):
    """Update an existing category."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    image_url: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryResponse(CategoryBase):
    """Category in API responses."""

    id: int
    parent_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryWithChildren(CategoryResponse):
    """Category with nested children for tree view."""

    children: list["CategoryWithChildren"] = []

    model_config = {"from_attributes": True}


class CategoryWithProducts(CategoryResponse):
    """Category with its products."""

    products: list[ProductListResponse] = []
    full_path: str

    model_config = {"from_attributes": True}


# --- Tag Schemas ---

class TagBase(BaseModel):
    """Base tag fields."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    tag_type: str | None = Field(default=None, max_length=50)


class TagCreate(TagBase):
    """Create a new tag."""

    pass


class TagUpdate(BaseModel):
    """Update an existing tag."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    tag_type: str | None = None


class TagResponse(TagBase):
    """Tag in API responses."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TagAssignment(BaseModel):
    """Assign tags to a product."""

    tag_ids: list[int]


# --- Collection Schemas ---

class CollectionBase(BaseModel):
    """Base collection fields."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    image_url: str | None = None
    is_active: bool = True
    start_date: datetime | None = None
    end_date: datetime | None = None


class CollectionCreate(CollectionBase):
    """Create a new collection."""

    pass


class CollectionUpdate(BaseModel):
    """Update an existing collection."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    image_url: str | None = None
    is_active: bool | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class CollectionResponse(CollectionBase):
    """Collection in API responses."""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CollectionWithProducts(CollectionResponse):
    """Collection with its products."""

    products: list[ProductListResponse] = []
    is_currently_active: bool

    model_config = {"from_attributes": True}


class CollectionProductAdd(BaseModel):
    """Add products to a collection."""

    product_ids: list[int]


class CollectionProductUpdate(BaseModel):
    """Update product order in collection."""

    product_id: int
    sort_order: int


# --- List Responses ---

class CategoryTree(BaseModel):
    """Full category tree structure."""

    categories: list[CategoryWithChildren]


class TagList(BaseModel):
    """List of tags, optionally grouped by type."""

    tags: list[TagResponse]
    by_type: dict[str, list[TagResponse]] = {}
