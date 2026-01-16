"""
Shipment model for order fulfillment tracking.

Supports partial fulfillment where an order can have multiple shipments.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Integer, ForeignKey, JSON, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.order import Order


class ShipmentStatus(str, Enum):
    """Shipment lifecycle states."""

    PENDING = "pending"       # Shipment created, not yet shipped
    SHIPPED = "shipped"       # Handed to carrier
    IN_TRANSIT = "in_transit" # In transit to destination
    DELIVERED = "delivered"   # Delivered to customer
    RETURNED = "returned"     # Returned to sender
    FAILED = "failed"         # Delivery failed


class Shipment(Base, TimestampMixin):
    """
    Shipment record for order fulfillment.

    An order can have multiple shipments (partial fulfillment).
    Items field stores which order items/quantities are in this shipment.
    """

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Link to order
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Shipment status
    status: Mapped[ShipmentStatus] = mapped_column(
        SQLEnum(ShipmentStatus),
        default=ShipmentStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Carrier information
    carrier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Shipping method used
    shipping_method_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipping_methods.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Items in this shipment
    # Format: [{"order_item_id": 1, "quantity": 2}, {"order_item_id": 2, "quantity": 1}]
    items: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # Timestamps
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="shipments")

    def __repr__(self) -> str:
        return f"<Shipment {self.id} ({self.status.value})>"

    @property
    def item_count(self) -> int:
        """Total number of items in this shipment."""
        return sum(item.get("quantity", 0) for item in self.items)

    @property
    def is_complete(self) -> bool:
        """Check if shipment has been delivered."""
        return self.status == ShipmentStatus.DELIVERED
