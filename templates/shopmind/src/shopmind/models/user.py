"""
User model for authentication and account management.
"""

from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.order import Order, Cart
    from shopmind.models.customer import WishlistItem, RecentlyViewed, Address
    from shopmind.models.reviews import Review
    from shopmind.models.segments import CustomerSegment


class User(Base, TimestampMixin):
    """
    User account model.

    Stores authentication credentials and basic profile info.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile fields
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Customer segment (for segment-based pricing)
    segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    segment: Mapped["CustomerSegment | None"] = relationship(
        "CustomerSegment",
        back_populates="users",
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    cart: Mapped["Cart | None"] = relationship(
        "Cart",
        back_populates="user",
        uselist=False,  # One cart per user
    )
    wishlist_items: Mapped[list["WishlistItem"]] = relationship(
        "WishlistItem",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    recently_viewed: Mapped[list["RecentlyViewed"]] = relationship(
        "RecentlyViewed",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    addresses: Mapped[list["Address"]] = relationship(
        "Address",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # TODO: Add email verification fields
    # email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<User {self.email}>"
