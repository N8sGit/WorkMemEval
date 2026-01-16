"""
Service for managing categories, tags, and collections.
"""

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from shopmind.models.catalog import (
    Category,
    Tag,
    Collection,
    ProductCategory,
    ProductTag,
    CollectionProduct,
)
from shopmind.models.product import Product
from shopmind.schemas.catalog import (
    CategoryCreate,
    CategoryUpdate,
    TagCreate,
    TagUpdate,
    CollectionCreate,
    CollectionUpdate,
)


# --- Category Operations ---

def get_category(db: Session, category_id: int) -> Category | None:
    """Get a category by ID."""
    return db.query(Category).filter(Category.id == category_id).first()


def get_category_by_slug(db: Session, slug: str) -> Category | None:
    """Get a category by slug."""
    return db.query(Category).filter(Category.slug == slug).first()


def get_category_tree(db: Session, active_only: bool = True) -> list[Category]:
    """
    Get all root categories with children loaded.

    Returns a flat list of root categories; children are accessible via relationships.
    """
    query = db.query(Category).filter(Category.parent_id == None)
    if active_only:
        query = query.filter(Category.is_active == True)

    return query.options(joinedload(Category.children)).order_by(Category.sort_order).all()


def get_category_with_products(
    db: Session,
    category_id: int,
    include_subcategory_products: bool = False,
) -> Category | None:
    """Get a category with its products."""
    category = (
        db.query(Category)
        .options(joinedload(Category.products))
        .filter(Category.id == category_id)
        .first()
    )
    return category


def create_category(db: Session, category_data: CategoryCreate) -> Category:
    """Create a new category."""
    # Check for duplicate slug
    if get_category_by_slug(db, category_data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with slug '{category_data.slug}' already exists",
        )

    # Validate parent exists if specified
    if category_data.parent_id:
        parent = get_category(db, category_data.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found",
            )

    category = Category(**category_data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, update_data: CategoryUpdate) -> Category:
    """Update an existing category."""
    update_dict = update_data.model_dump(exclude_unset=True)

    # Check slug uniqueness if changing
    if "slug" in update_dict and update_dict["slug"] != category.slug:
        if get_category_by_slug(db, update_dict["slug"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{update_dict['slug']}' already exists",
            )

    # Prevent circular parent reference
    if "parent_id" in update_dict:
        if update_dict["parent_id"] == category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent",
            )

    for field, value in update_dict.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    """Delete a category. Children are set to have no parent."""
    db.delete(category)
    db.commit()


# --- Tag Operations ---

def get_tag(db: Session, tag_id: int) -> Tag | None:
    """Get a tag by ID."""
    return db.query(Tag).filter(Tag.id == tag_id).first()


def get_tag_by_slug(db: Session, slug: str) -> Tag | None:
    """Get a tag by slug."""
    return db.query(Tag).filter(Tag.slug == slug).first()


def list_tags(db: Session, tag_type: str | None = None) -> list[Tag]:
    """List all tags, optionally filtered by type."""
    query = db.query(Tag)
    if tag_type:
        query = query.filter(Tag.tag_type == tag_type)
    return query.order_by(Tag.name).all()


def create_tag(db: Session, tag_data: TagCreate) -> Tag:
    """Create a new tag."""
    if get_tag_by_slug(db, tag_data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag with slug '{tag_data.slug}' already exists",
        )

    tag = Tag(**tag_data.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag: Tag, update_data: TagUpdate) -> Tag:
    """Update an existing tag."""
    update_dict = update_data.model_dump(exclude_unset=True)

    if "slug" in update_dict and update_dict["slug"] != tag.slug:
        if get_tag_by_slug(db, update_dict["slug"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag with slug '{update_dict['slug']}' already exists",
            )

    for field, value in update_dict.items():
        setattr(tag, field, value)

    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag: Tag) -> None:
    """Delete a tag."""
    db.delete(tag)
    db.commit()


def assign_tags_to_product(db: Session, product: Product, tag_ids: list[int]) -> Product:
    """Replace product's tags with the given tag IDs."""
    # Clear existing tags
    db.query(ProductTag).filter(ProductTag.product_id == product.id).delete()

    # Add new tags
    for tag_id in tag_ids:
        tag = get_tag(db, tag_id)
        if tag:
            db.add(ProductTag(product_id=product.id, tag_id=tag_id))

    db.commit()
    db.refresh(product)
    return product


def assign_categories_to_product(db: Session, product: Product, category_ids: list[int]) -> Product:
    """Replace product's categories with the given category IDs."""
    # Clear existing categories
    db.query(ProductCategory).filter(ProductCategory.product_id == product.id).delete()

    # Add new categories
    for category_id in category_ids:
        category = get_category(db, category_id)
        if category:
            db.add(ProductCategory(product_id=product.id, category_id=category_id))

    db.commit()
    db.refresh(product)
    return product


# --- Collection Operations ---

def get_collection(db: Session, collection_id: int) -> Collection | None:
    """Get a collection by ID."""
    return db.query(Collection).filter(Collection.id == collection_id).first()


def get_collection_by_slug(db: Session, slug: str) -> Collection | None:
    """Get a collection by slug."""
    return db.query(Collection).filter(Collection.slug == slug).first()


def list_collections(db: Session, active_only: bool = True) -> list[Collection]:
    """List all collections."""
    query = db.query(Collection)
    if active_only:
        query = query.filter(Collection.is_active == True)
    return query.order_by(Collection.created_at.desc()).all()


def get_collection_with_products(db: Session, collection_id: int) -> Collection | None:
    """Get a collection with its products ordered by sort_order."""
    collection = (
        db.query(Collection)
        .options(
            joinedload(Collection.product_associations)
            .joinedload(CollectionProduct.product)
        )
        .filter(Collection.id == collection_id)
        .first()
    )
    return collection


def create_collection(db: Session, collection_data: CollectionCreate) -> Collection:
    """Create a new collection."""
    if get_collection_by_slug(db, collection_data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Collection with slug '{collection_data.slug}' already exists",
        )

    collection = Collection(**collection_data.model_dump())
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def update_collection(db: Session, collection: Collection, update_data: CollectionUpdate) -> Collection:
    """Update an existing collection."""
    update_dict = update_data.model_dump(exclude_unset=True)

    if "slug" in update_dict and update_dict["slug"] != collection.slug:
        if get_collection_by_slug(db, update_dict["slug"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Collection with slug '{update_dict['slug']}' already exists",
            )

    for field, value in update_dict.items():
        setattr(collection, field, value)

    db.commit()
    db.refresh(collection)
    return collection


def delete_collection(db: Session, collection: Collection) -> None:
    """Delete a collection."""
    db.delete(collection)
    db.commit()


def add_products_to_collection(
    db: Session,
    collection: Collection,
    product_ids: list[int],
) -> Collection:
    """Add products to a collection."""
    # Get current max sort_order
    max_order = (
        db.query(CollectionProduct.sort_order)
        .filter(CollectionProduct.collection_id == collection.id)
        .order_by(CollectionProduct.sort_order.desc())
        .first()
    )
    next_order = (max_order[0] + 1) if max_order else 0

    for product_id in product_ids:
        # Check if product exists and not already in collection
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            continue

        existing = (
            db.query(CollectionProduct)
            .filter(
                CollectionProduct.collection_id == collection.id,
                CollectionProduct.product_id == product_id,
            )
            .first()
        )
        if existing:
            continue

        db.add(CollectionProduct(
            collection_id=collection.id,
            product_id=product_id,
            sort_order=next_order,
        ))
        next_order += 1

    db.commit()
    db.refresh(collection)
    return collection


def remove_product_from_collection(
    db: Session,
    collection: Collection,
    product_id: int,
) -> None:
    """Remove a product from a collection."""
    db.query(CollectionProduct).filter(
        CollectionProduct.collection_id == collection.id,
        CollectionProduct.product_id == product_id,
    ).delete()
    db.commit()


def update_collection_product_order(
    db: Session,
    collection: Collection,
    product_id: int,
    sort_order: int,
) -> None:
    """Update a product's sort order within a collection."""
    assoc = (
        db.query(CollectionProduct)
        .filter(
            CollectionProduct.collection_id == collection.id,
            CollectionProduct.product_id == product_id,
        )
        .first()
    )
    if assoc:
        assoc.sort_order = sort_order
        db.commit()
