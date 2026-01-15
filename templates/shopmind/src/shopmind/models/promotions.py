"""
Promotions models: Coupons, Cart Rules, Price Tiers.

Handles various discount mechanisms for the e-commerce platform.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Numeric, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.product import ProductVariant


class DiscountType(str, Enum):
    """Type of discount calculation."""

    PERCENTAGE = "percentage"  # e.g., 10% off
    FIXED_AMOUNT = "fixed_amount"  # e.g., $5 off
    FREE_SHIPPING = "free_shipping"  # Waive shipping cost


class CartRuleType(str, Enum):
    """Type of automatic cart rule."""

    SPEND_X_GET_Y_OFF = "spend_x_get_y_off"  # Spend $100, get $10 off
    BUY_X_GET_Y_FREE = "buy_x_get_y_free"  # Buy 2, get 1 free
    CATEGORY_DISCOUNT = "category_discount"  # 20% off electronics
    PRODUCT_DISCOUNT = "product_discount"  # Specific product discount


class Coupon(Base, TimestampMixin):
    """
    Promotional coupon/discount code.

    Supports percentage and fixed amount discounts with various
    restrictions like minimum order amount, usage limits, and
    valid date ranges.
    """

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Unique coupon code (e.g., "SUMMER20", "WELCOME10")
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Human-readable description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Discount configuration
    discount_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DiscountType.PERCENTAGE.value
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )  # Percentage (e.g., 10.00) or fixed amount (e.g., 5.00)

    # Order restrictions
    min_order_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )  # Minimum cart subtotal required
    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )  # Cap on percentage discounts

    # Usage limits
    max_uses: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Total uses allowed (None = unlimited)
    uses_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Current usage count
    per_user_limit: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Uses per user (None = unlimited)

    # Validity period
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Optional restrictions (JSONB)
    # Format: {"category_ids": [1, 2], "product_ids": [5, 6], "exclude_sale_items": true}
    restrictions: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # First-time customer only
    first_order_only: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Track usage per user
    usage_records: Mapped[list["CouponUsage"]] = relationship(
        "CouponUsage",
        back_populates="coupon",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Coupon {self.code}>"

    @property
    def is_valid(self) -> bool:
        """Check if coupon is currently valid (active and within date range)."""
        if not self.is_active:
            return False

        now = datetime.utcnow()

        if self.valid_from and now < self.valid_from:
            return False

        if self.valid_until and now > self.valid_until:
            return False

        if self.max_uses and self.uses_count >= self.max_uses:
            return False

        return True

    @property
    def remaining_uses(self) -> int | None:
        """Number of uses remaining, or None if unlimited."""
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.uses_count)


class CouponUsage(Base, TimestampMixin):
    """Tracks coupon usage per user for per_user_limit enforcement."""

    __tablename__ = "coupon_usage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    coupon_id: Mapped[int] = mapped_column(
        ForeignKey("coupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    coupon: Mapped["Coupon"] = relationship("Coupon", back_populates="usage_records")


class CartRule(Base, TimestampMixin):
    """
    Automatic cart discount rules.

    Applied automatically when conditions are met, unlike coupons
    which require a code entry.
    """

    __tablename__ = "cart_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Rule type determines how conditions are evaluated
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Conditions for rule activation (JSONB)
    # Format depends on rule_type:
    # - spend_x_get_y_off: {"min_spend": 100.00}
    # - buy_x_get_y_free: {"buy_quantity": 2, "get_quantity": 1, "product_ids": [1, 2]}
    # - category_discount: {"category_ids": [1, 2]}
    # - product_discount: {"product_ids": [5, 6]}
    conditions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Discount configuration
    discount_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DiscountType.PERCENTAGE.value
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # Priority for stacking rules (lower = applied first)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Can this rule stack with other rules?
    is_stackable: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Validity period
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CartRule {self.name}>"

    @property
    def is_valid(self) -> bool:
        """Check if rule is currently valid."""
        if not self.is_active:
            return False

        now = datetime.utcnow()

        if self.valid_from and now < self.valid_from:
            return False

        if self.valid_until and now > self.valid_until:
            return False

        return True


class PriceTier(Base, TimestampMixin):
    """
    Quantity-based pricing tier.

    Allows volume discounts: buy more, pay less per unit.
    """

    __tablename__ = "price_tiers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Minimum quantity for this tier to apply
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Price per unit at this tier
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Optional: Maximum quantity for this tier (next tier takes over)
    max_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationship
    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="price_tiers"
    )

    def __repr__(self) -> str:
        return f"<PriceTier variant={self.variant_id} min_qty={self.min_quantity}>"
