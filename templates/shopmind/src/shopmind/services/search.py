"""
Product search and filtering service.

Provides full-text search and faceted filtering for products.
Uses basic LIKE queries for SQLite compatibility; production would use PostgreSQL FTS.
"""

from decimal import Decimal
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from shopmind.models.product import Product, ProductVariant
from shopmind.models.catalog import Category, Tag, ProductCategory, ProductTag
from shopmind.schemas.search import (
    SearchResponse,
    SearchProductResult,
    FacetResponse,
    CategoryFacet,
    TagFacet,
    PriceRange,
)


def search_products(
    db: Session,
    query: str | None = None,
    category_id: int | None = None,
    category_slug: str | None = None,
    tag_slugs: list[str] | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
    on_sale: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    include_facets: bool = True,
) -> SearchResponse:
    """
    Search and filter products.

    Args:
        db: Database session
        query: Text search query (searches name and description)
        category_id: Filter by category ID
        category_slug: Filter by category slug (alternative to ID)
        tag_slugs: Filter by tag slugs (products must have ALL specified tags)
        min_price: Minimum base price
        max_price: Maximum base price
        in_stock: Filter to only products with stock
        on_sale: Filter to only products with active sale prices
        page: Page number (1-indexed)
        page_size: Results per page
        include_facets: Whether to calculate facet counts

    Returns:
        SearchResponse with products, pagination, and facets
    """
    # Base query - active products only
    base_query = db.query(Product).filter(Product.is_active == True)

    # Apply text search
    if query:
        search_term = f"%{query}%"
        base_query = base_query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
            )
        )

    # Apply category filter
    if category_id:
        base_query = base_query.join(ProductCategory).filter(
            ProductCategory.category_id == category_id
        )
    elif category_slug:
        category = db.query(Category).filter(Category.slug == category_slug).first()
        if category:
            base_query = base_query.join(ProductCategory).filter(
                ProductCategory.category_id == category.id
            )
        else:
            # Nonexistent category means no results
            base_query = base_query.filter(Product.id == -1)

    # Apply tag filters (must have ALL specified tags)
    if tag_slugs:
        for tag_slug in tag_slugs:
            tag = db.query(Tag).filter(Tag.slug == tag_slug).first()
            if tag:
                # Subquery: products that have this tag
                tag_subquery = select(ProductTag.product_id).where(ProductTag.tag_id == tag.id)
                base_query = base_query.filter(Product.id.in_(tag_subquery))
            else:
                # Nonexistent tag means no results
                base_query = base_query.filter(Product.id == -1)

    # Apply price filters
    if min_price is not None:
        base_query = base_query.filter(Product.base_price >= min_price)
    if max_price is not None:
        base_query = base_query.filter(Product.base_price <= max_price)

    # Apply stock filter
    if in_stock is True:
        # Products with at least one variant in stock
        in_stock_subquery = (
            select(ProductVariant.product_id)
            .where(ProductVariant.stock_quantity > 0, ProductVariant.is_active == True)
            .distinct()
        )
        base_query = base_query.filter(Product.id.in_(in_stock_subquery))

    # Apply sale filter
    if on_sale is True:
        now = datetime.now()
        on_sale_subquery = (
            select(ProductVariant.product_id)
            .where(
                ProductVariant.sale_price.isnot(None),
                ProductVariant.is_active == True,
                or_(ProductVariant.sale_start.is_(None), ProductVariant.sale_start <= now),
                or_(ProductVariant.sale_end.is_(None), ProductVariant.sale_end >= now),
            )
            .distinct()
        )
        base_query = base_query.filter(Product.id.in_(on_sale_subquery))

    # Get total count before pagination
    total = base_query.count()

    # Calculate pagination
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    skip = (page - 1) * page_size

    # Fetch products with eager loading
    products = (
        base_query.options(
            joinedload(Product.variants),
            joinedload(Product.categories),
            joinedload(Product.tags),
        )
        .order_by(Product.created_at.desc())
        .offset(skip)
        .limit(page_size)
        .all()
    )

    # Build search results
    items = [_build_search_result(p) for p in products]

    # Calculate facets if requested
    facets = _calculate_facets(db, base_query) if include_facets else FacetResponse()

    return SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        facets=facets,
        query=query,
    )


def _build_search_result(product: Product) -> SearchProductResult:
    """Build a search result from a product."""
    active_variants = [v for v in product.variants if v.is_active]

    # Calculate price range from variants
    prices = [v.final_price for v in active_variants] if active_variants else [product.base_price]
    min_price = min(prices) if prices else None
    max_price = max(prices) if prices else None

    # Check stock and sale status
    is_in_stock = any(v.is_in_stock for v in active_variants)
    is_on_sale = any(v.is_on_sale for v in active_variants)

    return SearchProductResult(
        id=product.id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        base_price=product.base_price,
        min_price=min_price,
        max_price=max_price,
        is_in_stock=is_in_stock,
        is_on_sale=is_on_sale,
        category_ids=[c.id for c in product.categories],
        tag_slugs=[t.slug for t in product.tags],
        created_at=product.created_at,
    )


def _calculate_facets(db: Session, base_query) -> FacetResponse:
    """
    Calculate facet counts for the current query.

    This runs additional queries to get counts for each facet option.
    """
    # Get product IDs from the base query
    product_ids_query = base_query.with_entities(Product.id)
    product_ids = [p.id for p in product_ids_query.all()]

    if not product_ids:
        return FacetResponse()

    # Category facets
    category_counts = (
        db.query(
            Category.id,
            Category.name,
            Category.slug,
            func.count(ProductCategory.product_id).label("count"),
        )
        .join(ProductCategory, ProductCategory.category_id == Category.id)
        .filter(ProductCategory.product_id.in_(product_ids))
        .filter(Category.is_active == True)
        .group_by(Category.id, Category.name, Category.slug)
        .order_by(func.count(ProductCategory.product_id).desc())
        .all()
    )
    categories = [
        CategoryFacet(id=c.id, name=c.name, slug=c.slug, count=c.count)
        for c in category_counts
    ]

    # Tag facets
    tag_counts = (
        db.query(
            Tag.id,
            Tag.name,
            Tag.slug,
            func.count(ProductTag.product_id).label("count"),
        )
        .join(ProductTag, ProductTag.tag_id == Tag.id)
        .filter(ProductTag.product_id.in_(product_ids))
        .group_by(Tag.id, Tag.name, Tag.slug)
        .order_by(func.count(ProductTag.product_id).desc())
        .all()
    )
    tags = [
        TagFacet(id=t.id, name=t.name, slug=t.slug, count=t.count)
        for t in tag_counts
    ]

    # Price range
    price_stats = (
        db.query(
            func.min(Product.base_price).label("min_price"),
            func.max(Product.base_price).label("max_price"),
        )
        .filter(Product.id.in_(product_ids))
        .first()
    )
    price_range = None
    if price_stats and price_stats.min_price is not None:
        price_range = PriceRange(
            min=price_stats.min_price,
            max=price_stats.max_price,
        )

    # In-stock count
    in_stock_count = (
        db.query(func.count(func.distinct(ProductVariant.product_id)))
        .filter(
            ProductVariant.product_id.in_(product_ids),
            ProductVariant.stock_quantity > 0,
            ProductVariant.is_active == True,
        )
        .scalar()
    ) or 0

    # On-sale count
    now = datetime.now()
    on_sale_count = (
        db.query(func.count(func.distinct(ProductVariant.product_id)))
        .filter(
            ProductVariant.product_id.in_(product_ids),
            ProductVariant.sale_price.isnot(None),
            ProductVariant.is_active == True,
            or_(ProductVariant.sale_start.is_(None), ProductVariant.sale_start <= now),
            or_(ProductVariant.sale_end.is_(None), ProductVariant.sale_end >= now),
        )
        .scalar()
    ) or 0

    return FacetResponse(
        categories=categories,
        tags=tags,
        price_range=price_range,
        in_stock_count=in_stock_count,
        on_sale_count=on_sale_count,
    )


def get_category_tree(db: Session, include_counts: bool = False) -> list[dict]:
    """
    Get full category tree structure.

    Args:
        db: Database session
        include_counts: Whether to include product counts per category

    Returns:
        Nested list of categories with children
    """
    # Get all active categories
    categories = (
        db.query(Category)
        .filter(Category.is_active == True)
        .order_by(Category.sort_order, Category.name)
        .all()
    )

    # Build count map
    count_map = {}

    if include_counts:
        counts = (
            db.query(
                ProductCategory.category_id,
                func.count(ProductCategory.product_id).label("count"),
            )
            .join(Product, Product.id == ProductCategory.product_id)
            .filter(Product.is_active == True)
            .group_by(ProductCategory.category_id)
            .all()
        )
        count_map = {c.category_id: c.count for c in counts}

    def build_node(category: Category) -> dict:
        return {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "image_url": category.image_url,
            "product_count": count_map.get(category.id, 0) if include_counts else None,
            "children": [
                build_node(child)
                for child in sorted(categories, key=lambda c: (c.sort_order, c.name))
                if child.parent_id == category.id
            ],
        }

    # Return only root categories (no parent)
    return [
        build_node(c)
        for c in sorted(categories, key=lambda c: (c.sort_order, c.name))
        if c.parent_id is None
    ]
