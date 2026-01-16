"""
Catalog organization API endpoints: Categories, Tags, Collections.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.models.catalog import Category, Tag, Collection, CollectionProduct
from shopmind.models.product import Product
from shopmind.schemas.catalog import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithChildren,
    CategoryWithProducts,
    TagCreate,
    TagUpdate,
    TagResponse,
    TagAssignment,
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionWithProducts,
    CollectionProductAdd,
)
from shopmind.schemas.product import ProductListResponse
from shopmind.services.auth import get_current_admin
from shopmind.services import categories as cat_service
from shopmind.services import catalog as product_service

router = APIRouter(tags=["Catalog"])


# --- Category Endpoints ---

@router.get("/categories", response_model=list[CategoryWithChildren])
def list_categories(
    db: Annotated[Session, Depends(get_db)],
    active_only: bool = Query(True),
) -> list[Category]:
    """
    Get category tree structure.

    Returns root categories with nested children.
    """
    return cat_service.get_category_tree(db, active_only=active_only)


@router.get("/categories/{category_id}", response_model=CategoryWithProducts)
def get_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> CategoryWithProducts:
    """Get a category with its products."""
    category = cat_service.get_category_with_products(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Build response with products
    products = [
        ProductListResponse.model_validate(p)
        for p in category.products
        if p.is_active
    ]

    return CategoryWithProducts(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        image_url=category.image_url,
        sort_order=category.sort_order,
        is_active=category.is_active,
        parent_id=category.parent_id,
        created_at=category.created_at,
        products=products,
        full_path=category.full_path,
    )


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Category:
    """Create a new category. **Admin only.**"""
    return cat_service.create_category(db, category_data)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    update_data: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Category:
    """Update a category. **Admin only.**"""
    category = cat_service.get_category(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return cat_service.update_category(db, category, update_data)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """Delete a category. **Admin only.**"""
    category = cat_service.get_category(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    cat_service.delete_category(db, category)


# --- Tag Endpoints ---

@router.get("/tags", response_model=list[TagResponse])
def list_tags(
    db: Annotated[Session, Depends(get_db)],
    tag_type: str | None = Query(None),
) -> list[Tag]:
    """List all tags, optionally filtered by type."""
    return cat_service.list_tags(db, tag_type=tag_type)


@router.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag_data: TagCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Tag:
    """Create a new tag. **Admin only.**"""
    return cat_service.create_tag(db, tag_data)


@router.patch("/tags/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    update_data: TagUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Tag:
    """Update a tag. **Admin only.**"""
    tag = cat_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    return cat_service.update_tag(db, tag, update_data)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """Delete a tag. **Admin only.**"""
    tag = cat_service.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    cat_service.delete_tag(db, tag)


@router.put("/products/{product_id}/tags", response_model=list[TagResponse])
def assign_product_tags(
    product_id: int,
    assignment: TagAssignment,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> list[Tag]:
    """Assign tags to a product. Replaces existing tags. **Admin only.**"""
    product = product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    product = cat_service.assign_tags_to_product(db, product, assignment.tag_ids)
    return product.tags


@router.put("/products/{product_id}/categories", response_model=list[CategoryResponse])
def assign_product_categories(
    product_id: int,
    category_ids: list[int],
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> list[Category]:
    """Assign categories to a product. Replaces existing. **Admin only.**"""
    product = product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    product = cat_service.assign_categories_to_product(db, product, category_ids)
    return product.categories


# --- Collection Endpoints ---

@router.get("/collections", response_model=list[CollectionResponse])
def list_collections(
    db: Annotated[Session, Depends(get_db)],
    active_only: bool = Query(True),
) -> list[Collection]:
    """List all collections."""
    return cat_service.list_collections(db, active_only=active_only)


@router.get("/collections/{slug}", response_model=CollectionWithProducts)
def get_collection(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
) -> CollectionWithProducts:
    """Get a collection with its products by slug."""
    collection = cat_service.get_collection_by_slug(db, slug)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    # Load products
    collection = cat_service.get_collection_with_products(db, collection.id)

    # Build products list sorted by sort_order
    sorted_assocs = sorted(collection.product_associations, key=lambda a: a.sort_order)
    products = [
        ProductListResponse.model_validate(assoc.product)
        for assoc in sorted_assocs
        if assoc.product.is_active
    ]

    return CollectionWithProducts(
        id=collection.id,
        name=collection.name,
        slug=collection.slug,
        description=collection.description,
        image_url=collection.image_url,
        is_active=collection.is_active,
        start_date=collection.start_date,
        end_date=collection.end_date,
        created_at=collection.created_at,
        products=products,
        is_currently_active=collection.is_currently_active,
    )


@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    collection_data: CollectionCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Collection:
    """Create a new collection. **Admin only.**"""
    return cat_service.create_collection(db, collection_data)


@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: int,
    update_data: CollectionUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Collection:
    """Update a collection. **Admin only.**"""
    collection = cat_service.get_collection(db, collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    return cat_service.update_collection(db, collection, update_data)


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """Delete a collection. **Admin only.**"""
    collection = cat_service.get_collection(db, collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    cat_service.delete_collection(db, collection)


@router.post("/collections/{collection_id}/products", response_model=CollectionResponse)
def add_products_to_collection(
    collection_id: int,
    products: CollectionProductAdd,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> Collection:
    """Add products to a collection. **Admin only.**"""
    collection = cat_service.get_collection(db, collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    return cat_service.add_products_to_collection(db, collection, products.product_ids)


@router.delete("/collections/{collection_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product_from_collection(
    collection_id: int,
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """Remove a product from a collection. **Admin only.**"""
    collection = cat_service.get_collection(db, collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    cat_service.remove_product_from_collection(db, collection, product_id)
