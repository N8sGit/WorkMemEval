"""
Product catalog service.

Handles product and variant CRUD operations.
"""

from sqlalchemy.orm import Session, joinedload

from shopmind.models.product import Product, ProductVariant
from shopmind.schemas.product import (
    ProductCreate,
    ProductUpdate,
    VariantCreate,
    VariantUpdate,
)


# --- Product Operations ---

def get_product(db: Session, product_id: int) -> Product | None:
    """Get a product by ID with its variants."""
    return (
        db.query(Product)
        .options(joinedload(Product.variants))
        .filter(Product.id == product_id)
        .first()
    )


def get_product_by_slug(db: Session, slug: str) -> Product | None:
    """Get a product by slug with its variants."""
    return (
        db.query(Product)
        .options(joinedload(Product.variants))
        .filter(Product.slug == slug)
        .first()
    )


def list_products(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    active_only: bool = True,
) -> tuple[list[Product], int]:
    """
    List products with pagination.

    Returns:
        Tuple of (products, total_count)
    """
    query = db.query(Product)

    if active_only:
        query = query.filter(Product.is_active == True)

    total = query.count()
    products = (
        query.order_by(Product.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return products, total


def create_product(db: Session, product_data: ProductCreate) -> Product:
    """
    Create a new product with optional initial variants.

    Args:
        db: Database session
        product_data: Product creation data including optional variants

    Returns:
        Created product instance
    """
    # Create product
    product = Product(
        name=product_data.name,
        slug=product_data.slug,
        description=product_data.description,
        base_price=product_data.base_price,
        has_variants=product_data.has_variants or len(product_data.variants) > 0,
    )
    db.add(product)
    db.flush()  # Get product.id without committing

    # Create variants if provided
    for variant_data in product_data.variants:
        variant = ProductVariant(
            product_id=product.id,
            sku=variant_data.sku,
            attributes=variant_data.attributes,
            price_modifier=variant_data.price_modifier,
            stock_quantity=variant_data.stock_quantity,
            low_stock_threshold=variant_data.low_stock_threshold,
        )
        db.add(variant)

    db.commit()
    db.refresh(product)

    # TODO: Emit ProductCreated event
    # event_bus.emit(ProductCreated(product_id=product.id))

    return product


def update_product(db: Session, product: Product, update_data: ProductUpdate) -> Product:
    """Update an existing product."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product, hard_delete: bool = False) -> None:
    """
    Delete a product.

    Args:
        db: Database session
        product: Product to delete
        hard_delete: If True, permanently delete. If False, soft delete.
    """
    if hard_delete:
        db.delete(product)
    else:
        product.is_active = False

    db.commit()


# --- Variant Operations ---

def get_variant(db: Session, variant_id: int) -> ProductVariant | None:
    """Get a variant by ID."""
    return db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()


def get_variant_by_sku(db: Session, sku: str) -> ProductVariant | None:
    """Get a variant by SKU."""
    return db.query(ProductVariant).filter(ProductVariant.sku == sku).first()


def create_variant(
    db: Session,
    product_id: int,
    variant_data: VariantCreate,
) -> ProductVariant:
    """Create a new variant for a product."""
    variant = ProductVariant(
        product_id=product_id,
        sku=variant_data.sku,
        attributes=variant_data.attributes,
        price_modifier=variant_data.price_modifier,
        stock_quantity=variant_data.stock_quantity,
        low_stock_threshold=variant_data.low_stock_threshold,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)

    # Mark product as having variants
    product = db.query(Product).filter(Product.id == product_id).first()
    if product and not product.has_variants:
        product.has_variants = True
        db.commit()

    return variant


def update_variant(
    db: Session,
    variant: ProductVariant,
    update_data: VariantUpdate,
) -> ProductVariant:
    """Update an existing variant."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(variant, field, value)

    db.commit()
    db.refresh(variant)
    return variant


def update_stock(db: Session, variant: ProductVariant, quantity_delta: int) -> ProductVariant:
    """
    Adjust variant stock by a delta.

    Args:
        db: Database session
        variant: Variant to update
        quantity_delta: Amount to add (positive) or remove (negative)

    Returns:
        Updated variant

    Raises:
        ValueError: If adjustment would result in negative stock
    """
    new_quantity = variant.stock_quantity + quantity_delta

    if new_quantity < 0:
        raise ValueError(f"Insufficient stock. Current: {variant.stock_quantity}, requested: {-quantity_delta}")

    variant.stock_quantity = new_quantity
    db.commit()
    db.refresh(variant)

    # TODO: Emit LowStockWarning if below threshold
    # if variant.is_low_stock:
    #     event_bus.emit(LowStockWarning(variant_id=variant.id, quantity=new_quantity))

    return variant
