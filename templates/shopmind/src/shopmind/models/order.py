"""
Order and Cart models for checkout flow.

Design decisions:
- Orders are immutable after creation (prices locked in)
- Carts can be anonymous (session-based) or user-linked
- Stock is reserved at checkout, not when adding to cart
"""

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Numeric, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.shipments import Shipment


class OrderStatus(str, Enum):
    """Order lifecycle states."""

    PENDING = "pending"           # Created, awaiting payment
    CONFIRMED = "confirmed"       # Payment received
    PROCESSING = "processing"     # Being prepared/picked
    SHIPPED = "shipped"           # Handed to carrier
    DELIVERED = "delivered"       # Customer received
    CANCELLED = "cancelled"       # Order cancelled
    REFUNDED = "refunded"         # Payment returned


class Order(Base, TimestampMixin):
    """
    Completed order record.

    Once created, order details are immutable to preserve history.
    Prices are captured at checkout time.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # User ID (nullable for guest checkout)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    # Guest checkout info (used when user_id is null)
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guest_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Order status
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Pricing (captured at checkout)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    tax: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Coupon tracking
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    coupon_id: Mapped[int | None] = mapped_column(
        ForeignKey("coupons.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Shipping info (denormalized for history)
    shipping_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipping_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    shipping_country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Shipping method reference
    shipping_method_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipping_methods.id", ondelete="SET NULL"),
        nullable=True,
    )
    shipping_method_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Payment reference (from external provider)
    payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Customer notes (visible to customer)
    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Gift order
    is_gift: Mapped[bool] = mapped_column(default=False, nullable=False)
    gift_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Internal notes (admin only)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    shipments: Mapped[list["Shipment"]] = relationship(
        "Shipment",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Order {self.id} ({self.status.value})>"

    @property
    def is_fully_shipped(self) -> bool:
        """Check if all items have been shipped."""
        if not self.shipments:
            return False

        # Get total shipped quantities per order item
        shipped_quantities: dict[int, int] = {}
        for shipment in self.shipments:
            if shipment.status.value not in ("returned", "failed"):
                for item in shipment.items:
                    item_id = item.get("order_item_id")
                    qty = item.get("quantity", 0)
                    shipped_quantities[item_id] = shipped_quantities.get(item_id, 0) + qty

        # Check all items are fully shipped
        for order_item in self.items:
            if shipped_quantities.get(order_item.id, 0) < order_item.quantity:
                return False

        return True


class OrderItem(Base, TimestampMixin):
    """
    Line item in an order.

    Prices are captured at checkout time to preserve order history
    even if product prices change later.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"),
        nullable=False,
    )

    # Quantity ordered
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Price at time of order (immutable)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Denormalized product info (in case product is deleted)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_sku: Mapped[str] = mapped_column(String(100), nullable=False)
    variant_attributes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")

    def __repr__(self) -> str:
        return f"<OrderItem {self.variant_sku} x{self.quantity}>"

    @property
    def subtotal(self) -> Decimal:
        """Calculate line item subtotal."""
        return self.unit_price * self.quantity


class Cart(Base, TimestampMixin):
    """
    Shopping cart for collecting items before checkout.

    Can be anonymous (session-based) or linked to a user.
    Anonymous carts can be merged into user cart on login.
    """

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Optional user link (null for anonymous carts)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    # Session ID for anonymous carts
    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="cart")
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        if self.user_id:
            return f"<Cart user={self.user_id}>"
        return f"<Cart session={self.session_id[:8]}...>"

    @property
    def item_count(self) -> int:
        """Total number of items in cart."""
        return sum(item.quantity for item in self.items)

    @property
    def subtotal(self) -> Decimal:
        """Calculate cart subtotal (before shipping/tax)."""
        return sum(item.subtotal for item in self.items)


class CartItem(Base, TimestampMixin):
    """Item in a shopping cart."""

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")

    def __repr__(self) -> str:
        return f"<CartItem variant={self.variant_id} x{self.quantity}>"

    @property
    def subtotal(self) -> Decimal:
        """Calculate line item subtotal using current variant price."""
        return self.variant.final_price * self.quantity


# Forward references for type hints
from shopmind.models.user import User
from shopmind.models.product import ProductVariant
