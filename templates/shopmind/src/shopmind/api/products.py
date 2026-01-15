"""
Product catalog API endpoints.

Provides CRUD operations for products and variants.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shopmind.config import get_settings
from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.models.product import Product, ProductVariant
from shopmind.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    PaginatedProducts,
    VariantCreate,
    VariantUpdate,
    VariantResponse,
)
from shopmind.schemas.search import SearchResponse
from shopmind.services.auth import get_current_admin, get_current_user_optional
from shopmind.services import catalog
from shopmind.services import customer as customer_service
from shopmind.services import search as search_service

settings = get_settings()

router = APIRouter(prefix="/products", tags=["Products"])


# --- Product Endpoints ---

@router.get("", response_model=PaginatedProducts)
def list_products(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedProducts:
    """
    List all active products with pagination.

    - **page**: Page number (starting from 1)
    - **page_size**: Items per page (max 100)
    """
    skip = (page - 1) * page_size
    products, total = catalog.list_products(db, skip=skip, limit=page_size)

    return PaginatedProducts(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,  # Ceiling division
    )


@router.get("/search", response_model=SearchResponse)
def search_products(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(None, description="Text search query"),
    category_id: int | None = Query(None, description="Filter by category ID"),
    category: str | None = Query(None, description="Filter by category slug"),
    tags: str | None = Query(None, description="Filter by tag slugs (comma-separated)"),
    min_price: float | None = Query(None, ge=0, description="Minimum price"),
    max_price: float | None = Query(None, ge=0, description="Maximum price"),
    in_stock: bool | None = Query(None, description="Filter to in-stock products only"),
    on_sale: bool | None = Query(None, description="Filter to products on sale only"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    include_facets: bool = Query(True, description="Include facet counts in response"),
) -> SearchResponse:
    """
    Search and filter products.

    - **q**: Text search in product names and descriptions
    - **category_id** or **category**: Filter by category (ID or slug)
    - **tags**: Filter by tags (comma-separated slugs, products must have ALL tags)
    - **min_price** / **max_price**: Price range filter
    - **in_stock**: Only show products with available stock
    - **on_sale**: Only show products with active sale prices
    - **include_facets**: Include category/tag counts for building filter UI
    """
    from decimal import Decimal

    # Parse tags from comma-separated string
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    # Convert price to Decimal if provided
    min_price_decimal = Decimal(str(min_price)) if min_price is not None else None
    max_price_decimal = Decimal(str(max_price)) if max_price is not None else None

    return search_service.search_products(
        db=db,
        query=q,
        category_id=category_id,
        category_slug=category,
        tag_slugs=tag_list,
        min_price=min_price_decimal,
        max_price=max_price_decimal,
        in_stock=in_stock,
        on_sale=on_sale,
        page=page,
        page_size=page_size,
        include_facets=include_facets,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session_id: str | None = Query(None),
) -> Product:
    """Get a single product by ID with its variants."""
    product = catalog.get_product(db, product_id)

    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Track recently viewed
    customer_service.record_product_view(db, product.id, user, session_id)

    return product


@router.get("/slug/{slug}", response_model=ProductResponse)
def get_product_by_slug(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session_id: str | None = Query(None),
) -> Product:
    """Get a single product by slug with its variants."""
    product = catalog.get_product_by_slug(db, slug)

    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Track recently viewed
    customer_service.record_product_view(db, product.id, user, session_id)

    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Product:
    """
    Create a new product. **Admin only.**

    Can include initial variants in the request body.
    """
    # Check for duplicate slug
    if catalog.get_product_by_slug(db, product_data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with slug '{product_data.slug}' already exists",
        )

    return catalog.create_product(db, product_data)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    update_data: ProductUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Product:
    """Update a product. **Admin only.**"""
    product = catalog.get_product(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return catalog.update_product(db, product, update_data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete"),
) -> None:
    """Delete a product. **Admin only.**"""
    product = catalog.get_product(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    catalog.delete_product(db, product, hard_delete=hard_delete)


# --- Variant Endpoints ---

@router.post("/{product_id}/variants", response_model=VariantResponse, status_code=status.HTTP_201_CREATED)
def create_variant(
    product_id: int,
    variant_data: VariantCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ProductVariant:
    """Create a new variant for a product. **Admin only.**"""
    product = catalog.get_product(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check for duplicate SKU
    if catalog.get_variant_by_sku(db, variant_data.sku):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Variant with SKU '{variant_data.sku}' already exists",
        )

    return catalog.create_variant(db, product_id, variant_data)


@router.patch("/variants/{variant_id}", response_model=VariantResponse)
def update_variant(
    variant_id: int,
    update_data: VariantUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ProductVariant:
    """Update a variant. **Admin only.**"""
    variant = catalog.get_variant(db, variant_id)

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    return catalog.update_variant(db, variant, update_data)


@router.post("/variants/{variant_id}/stock", response_model=VariantResponse)
def adjust_stock(
    variant_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    quantity_delta: int = Query(..., description="Amount to add (positive) or remove (negative)"),
) -> ProductVariant:
    """
    Adjust variant stock quantity. **Admin only.**

    Use positive delta to add stock, negative to remove.
    """
    variant = catalog.get_variant(db, variant_id)

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    try:
        return catalog.update_stock(db, variant, quantity_delta)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
