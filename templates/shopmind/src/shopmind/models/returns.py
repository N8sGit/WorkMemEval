"""
Return (RMA) model for handling product returns and refunds.

Status flow: requested → approved → received → refunded
"""

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Numeric, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.order import Order, OrderItem
    from shopmind.models.user import User


class ReturnStatus(str, Enum):
    """Return request lifecycle states."""

    REQUESTED = "requested"   # Customer initiated return
    APPROVED = "approved"     # Return approved by admin
    REJECTED = "rejected"     # Return rejected by admin
    RECEIVED = "received"     # Returned item received at warehouse
    REFUNDED = "refunded"     # Refund processed
    CANCELLED = "cancelled"   # Return cancelled by customer


class ReturnReason(str, Enum):
    """Standard return reasons."""

    DEFECTIVE = "defective"           # Product is defective
    WRONG_ITEM = "wrong_item"         # Received wrong item
    NOT_AS_DESCRIBED = "not_as_described"  # Product doesn't match description
    CHANGED_MIND = "changed_mind"     # Customer changed their mind
    DAMAGED_SHIPPING = "damaged_shipping"  # Damaged during shipping
    OTHER = "other"                   # Other reason


class Return(Base, TimestampMixin):
    """
    Return/RMA request record.

    Tracks the return process from customer request through refund.
    """

    __tablename__ = "returns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Link to order
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link to specific order item (for partial returns)
    order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    # User who requested the return
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Return status
    status: Mapped[ReturnStatus] = mapped_column(
        SQLEnum(ReturnStatus),
        default=ReturnStatus.REQUESTED,
        nullable=False,
        index=True,
    )

    # Return reason
    reason: Mapped[ReturnReason] = mapped_column(
        SQLEnum(ReturnReason),
        nullable=False,
    )

    # Customer's description of the issue
    reason_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quantity being returned (for partial returns)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Refund amount (set when approved/refunded)
    refund_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Admin notes (internal)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Return tracking number (if shipped back)
    return_tracking_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Restocking fee (if applicable)
    restocking_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Whether stock has been restored
    stock_restored: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order")
    order_item: Mapped["OrderItem | None"] = relationship("OrderItem")
    user: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Return {self.id} ({self.status.value})>"

    @property
    def can_approve(self) -> bool:
        """Check if return can be approved."""
        return self.status == ReturnStatus.REQUESTED

    @property
    def can_reject(self) -> bool:
        """Check if return can be rejected."""
        return self.status == ReturnStatus.REQUESTED

    @property
    def can_receive(self) -> bool:
        """Check if return can be marked as received."""
        return self.status == ReturnStatus.APPROVED

    @property
    def can_refund(self) -> bool:
        """Check if return can be refunded."""
        return self.status == ReturnStatus.RECEIVED

    @property
    def can_cancel(self) -> bool:
        """Check if return can be cancelled."""
        return self.status in (ReturnStatus.REQUESTED, ReturnStatus.APPROVED)
