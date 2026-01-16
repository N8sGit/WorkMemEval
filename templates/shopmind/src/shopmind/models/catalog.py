"""
Catalog organization models: Categories, Tags, and Collections.

Categories: Hierarchical product organization (Electronics > Phones > Smartphones)
Tags: Flexible labeling (new-arrival, bestseller, sale)
Collections: Curated product groups (Summer Sale, Gift Ideas)
"""

from datetime import datetime
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    """
    Hierarchical product category.

    Uses adjacency list pattern for hierarchy (parent_id).
    Products can belong to multiple categories.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Hierarchy
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Display order within parent
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    products: Mapped[list["Product"]] = relationship(
        "Product",
        secondary="product_categories",
        back_populates="categories",
    )

    def __repr__(self) -> str:
        return f"<Category {self.slug}>"

    @property
    def full_path(self) -> str:
        """Get full category path (e.g., 'Electronics > Phones > Smartphones')."""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class Tag(Base, TimestampMixin):
    """
    Flexible product tag for labeling.

    Tag types allow grouping (e.g., 'badge' for visual badges,
    'feature' for product features, 'seasonal' for time-based).
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Optional grouping
    tag_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product",
        secondary="product_tags",
        back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<Tag {self.slug}>"


class Collection(Base, TimestampMixin):
    """
    Curated product collection.

    Collections can be time-limited (e.g., seasonal sales)
    and products within have a sort order.
    """

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Optional time limits
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships (through junction table with sort_order)
    product_associations: Mapped[list["CollectionProduct"]] = relationship(
        "CollectionProduct",
        back_populates="collection",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Collection {self.slug}>"

    @property
    def is_currently_active(self) -> bool:
        """Check if collection is active and within date range."""
        if not self.is_active:
            return False
        now = datetime.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


# --- Junction Tables ---

class ProductCategory(Base):
    """Junction table for Product <-> Category many-to-many."""

    __tablename__ = "product_categories"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )


class ProductTag(Base):
    """Junction table for Product <-> Tag many-to-many."""

    __tablename__ = "product_tags"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class CollectionProduct(Base, TimestampMixin):
    """
    Junction table for Collection <-> Product with sort order.

    Allows ordering products within a collection.
    """

    __tablename__ = "collection_products"
    __table_args__ = (
        UniqueConstraint("collection_id", "product_id", name="uq_collection_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    collection: Mapped["Collection"] = relationship(
        "Collection",
        back_populates="product_associations",
    )
    product: Mapped["Product"] = relationship("Product")


# Forward reference
from shopmind.models.product import Product
