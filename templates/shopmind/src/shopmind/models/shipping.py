"""
Shipping method model.

Defines available shipping options with pricing rules.
"""

from decimal import Decimal

from sqlalchemy import String, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from shopmind.models.base import Base, TimestampMixin


class ShippingMethod(Base, TimestampMixin):
    """
    Shipping method configuration.

    Supports various pricing models:
    - Flat rate (base_cost only)
    - Per-item (base_cost + per_item_cost * quantity)
    - Free shipping threshold (free if order exceeds threshold)
    """

    __tablename__ = "shipping_methods"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Display info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Carrier info (e.g., "USPS", "FedEx", "UPS")
    carrier: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Estimated delivery time
    estimated_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Pricing
    base_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    per_item_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Free shipping threshold (null = never free)
    free_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Sort order for display
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<ShippingMethod {self.name}>"

    def calculate_cost(self, subtotal: Decimal, item_count: int) -> Decimal:
        """
        Calculate shipping cost for an order.

        Args:
            subtotal: Order subtotal before shipping
            item_count: Total number of items in order

        Returns:
            Calculated shipping cost
        """
        # Check free shipping threshold
        if self.free_threshold is not None and subtotal >= self.free_threshold:
            return Decimal("0.00")

        # Calculate cost
        return self.base_cost + (self.per_item_cost * item_count)

    @property
    def estimated_delivery(self) -> str | None:
        """Human-readable delivery estimate."""
        if self.estimated_days_min is None and self.estimated_days_max is None:
            return None

        if self.estimated_days_min == self.estimated_days_max:
            return f"{self.estimated_days_min} business days"

        if self.estimated_days_min is None:
            return f"Up to {self.estimated_days_max} business days"

        if self.estimated_days_max is None:
            return f"{self.estimated_days_min}+ business days"

        return f"{self.estimated_days_min}-{self.estimated_days_max} business days"
