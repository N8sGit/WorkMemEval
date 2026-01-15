"""
Customer feature models: Wishlist, Recently Viewed, Saved Addresses.

Enhances user experience with personalization and convenience features.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopmind.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopmind.models.user import User
    from shopmind.models.product import Product, ProductVariant


class WishlistItem(Base, TimestampMixin):
    """
    Item saved to a user's wishlist.

    Users can save variants they're interested in for later purchase.
    """

    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "variant_id", name="uq_wishlist_user_variant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional note (e.g., "For mom's birthday")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wishlist_items")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")

    def __repr__(self) -> str:
        return f"<WishlistItem user={self.user_id} variant={self.variant_id}>"


class RecentlyViewed(Base, TimestampMixin):
    """
    Tracks products a user has recently viewed.

    Can be used for:
    - "Continue browsing" sections
    - Personalized recommendations
    - Analytics

    Supports both logged-in users and anonymous sessions.
    """

    __tablename__ = "recently_viewed"
    __table_args__ = (
        # Only one entry per user/product or session/product
        UniqueConstraint("user_id", "product_id", name="uq_recently_viewed_user_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # User (for logged-in users)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Session ID (for anonymous users)
    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When the product was last viewed (updated on repeat views)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="recently_viewed")
    product: Mapped["Product"] = relationship("Product")

    def __repr__(self) -> str:
        identifier = f"user={self.user_id}" if self.user_id else f"session={self.session_id[:8]}..."
        return f"<RecentlyViewed {identifier} product={self.product_id}>"


class Address(Base, TimestampMixin):
    """
    Saved address for a user.

    Users can save multiple addresses and set defaults for
    shipping and billing.
    """

    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Address label (e.g., "Home", "Work", "Mom's House")
    label: Mapped[str] = mapped_column(String(100), nullable=False)

    # Recipient name
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Address lines
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Location
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    # Contact
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Default flags
    is_default_shipping: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_default_billing: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="addresses")

    def __repr__(self) -> str:
        return f"<Address {self.label} for user={self.user_id}>"

    @property
    def full_address(self) -> str:
        """Format the full address as a string."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(f"{self.city}, {self.state or ''} {self.postal_code}".strip())
        parts.append(self.country)
        return "\n".join(parts)
