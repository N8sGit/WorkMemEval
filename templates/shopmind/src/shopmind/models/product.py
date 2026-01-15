"""
Product and ProductVariant models.

Products have a base definition, while variants represent specific
purchasable items (e.g., "Blue T-Shirt, Size M").
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Numeric, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.promotions import PriceTier
    from shopmind.models.reviews import Review
    from shopmind.models.catalog import Category, Tag


class Product(Base, TimestampMixin):
    """
    Base product definition.

    Represents a product concept (e.g., "Classic T-Shirt") without
    specific variant details like size or color.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Base price before any variant modifiers
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # For simple products without variants, this tracks stock directly
    # For products with variants, this is ignored (stock tracked per variant)
    has_variants: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Soft delete support
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Rating aggregation (updated when reviews change)
    avg_rating: Mapped[Decimal | None] = mapped_column(
        Numeric(2, 1),
        nullable=True,
        default=None,
    )
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        secondary="product_categories",
        back_populates="products",
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="product_tags",
        back_populates="products",
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Product {self.name}>"


class ProductVariant(Base, TimestampMixin):
    """
    Specific purchasable variant of a product.

    Stores attributes like size/color as flexible JSONB, allowing
    different attribute types for different product categories.

    Examples:
        - {"size": "M", "color": "blue"}
        - {"capacity": "256GB", "color": "space gray"}
        - {"flavor": "vanilla", "weight": "1kg"}
    """

    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Unique identifier for inventory/fulfillment
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Flexible attributes stored as JSON
    # Schema validation happens at the application layer
    attributes: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Price adjustment from base product price (can be positive or negative)
    price_modifier: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Inventory tracking
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Threshold for low stock warnings
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Sale pricing (time-limited discounts)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    sale_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sale_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    price_tiers: Mapped[list["PriceTier"]] = relationship(
        "PriceTier",
        back_populates="variant",
        cascade="all, delete-orphan",
        order_by="PriceTier.min_quantity",
    )

    def __repr__(self) -> str:
        return f"<ProductVariant {self.sku}>"

    @property
    def is_on_sale(self) -> bool:
        """Check if variant is currently on sale."""
        if self.sale_price is None:
            return False

        now = datetime.now()

        if self.sale_start and now < self.sale_start:
            return False

        if self.sale_end and now > self.sale_end:
            return False

        return True

    @property
    def regular_price(self) -> Decimal:
        """Calculate the regular price (base + modifier)."""
        return self.product.base_price + self.price_modifier

    @property
    def final_price(self) -> Decimal:
        """Calculate the final price, considering sale price if active."""
        if self.is_on_sale and self.sale_price is not None:
            return self.sale_price
        return self.regular_price

    def get_tiered_price(self, quantity: int) -> Decimal:
        """Get price for a specific quantity (considers tiered pricing)."""
        if not self.price_tiers:
            return self.final_price

        # Find the best tier for this quantity
        applicable_tier = None
        for tier in self.price_tiers:
            if quantity >= tier.min_quantity:
                if tier.max_quantity is None or quantity <= tier.max_quantity:
                    applicable_tier = tier

        if applicable_tier:
            return applicable_tier.price

        return self.final_price

    @property
    def is_in_stock(self) -> bool:
        """Check if variant is available for purchase."""
        return self.stock_quantity > 0

    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below threshold."""
        return self.stock_quantity <= self.low_stock_threshold
