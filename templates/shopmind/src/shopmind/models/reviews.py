"""
Review and Stock Notification models.

Reviews: Product ratings and reviews from customers
StockNotification: Back-in-stock notification subscriptions
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.user import User
    from shopmind.models.product import Product, ProductVariant
    from shopmind.models.order import Order


class Review(Base, TimestampMixin):
    """
    Product review from a customer.

    Reviews can be tied to an order (verified purchase) or standalone.
    Reviews require admin approval before being displayed.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        # One review per user per product
        UniqueConstraint("user_id", "product_id", name="uq_review_user_product"),
        # Rating must be 1-5
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link to order for verified purchase badge
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Rating 1-5 stars
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Review content
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verified purchase = user bought this product
    is_verified_purchase: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Moderation status
    is_approved: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reviews")
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    order: Mapped["Order | None"] = relationship("Order")

    def __repr__(self) -> str:
        return f"<Review user={self.user_id} product={self.product_id} rating={self.rating}>"


class StockNotification(Base, TimestampMixin):
    """
    Back-in-stock notification subscription.

    Users can subscribe to be notified when an out-of-stock variant
    becomes available again.
    """

    __tablename__ = "stock_notifications"
    __table_args__ = (
        # Prevent duplicate subscriptions
        UniqueConstraint("variant_id", "user_id", name="uq_stock_notif_variant_user"),
        UniqueConstraint("variant_id", "email", name="uq_stock_notif_variant_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Either user_id OR email (for guest notifications)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When notification was sent (null = not yet sent)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User | None"] = relationship("User")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")

    def __repr__(self) -> str:
        return f"<StockNotification variant={self.variant_id} user={self.user_id}>"
