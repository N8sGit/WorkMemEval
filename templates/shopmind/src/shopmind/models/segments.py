"""
Customer segment model for segment-based pricing.

Segments allow different customer groups to receive
automatic discounts at checkout.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.user import User


class CustomerSegment(Base, TimestampMixin):
    """
    Customer segment for group-based pricing.

    Examples:
    - "VIP" - 10% discount on all orders
    - "Wholesale" - 15% discount for business customers
    - "Employee" - 20% discount for staff
    - "Student" - 5% discount for students
    """

    __tablename__ = "customer_segments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Segment identification
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Discount percentage (0-100)
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Priority for when user has multiple segments (higher = applied first)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Minimum order amount to apply discount (optional)
    min_order_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Maximum discount amount (cap) - optional
    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="segment",
    )

    def __repr__(self) -> str:
        return f"<CustomerSegment {self.name} ({self.discount_percentage}%)>"

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        """
        Calculate discount amount for a given subtotal.

        Args:
            subtotal: Order subtotal before discount

        Returns:
            Discount amount (capped if max_discount_amount is set)
        """
        if not self.is_active:
            return Decimal("0.00")

        # Check minimum order amount
        if self.min_order_amount and subtotal < self.min_order_amount:
            return Decimal("0.00")

        # Calculate percentage discount
        discount = (subtotal * self.discount_percentage / 100).quantize(Decimal("0.01"))

        # Apply cap if set
        if self.max_discount_amount and discount > self.max_discount_amount:
            discount = self.max_discount_amount

        return discount
