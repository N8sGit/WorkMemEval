"""SQLAlchemy models for ShopMind."""

from shopmind.models.base import Base
from shopmind.models.user import User
from shopmind.models.product import Product, ProductVariant
from shopmind.models.order import Order, OrderItem, OrderStatus, Cart, CartItem
from shopmind.models.catalog import (
    Category,
    Tag,
    Collection,
    ProductCategory,
    ProductTag,
    CollectionProduct,
)
from shopmind.models.promotions import (
    Coupon,
    CouponUsage,
    CartRule,
    PriceTier,
    DiscountType,
    CartRuleType,
)
from shopmind.models.customer import (
    WishlistItem,
    RecentlyViewed,
    Address,
)
from shopmind.models.reviews import (
    Review,
    StockNotification,
)
from shopmind.models.shipping import ShippingMethod
from shopmind.models.returns import Return, ReturnStatus, ReturnReason
from shopmind.models.shipments import Shipment, ShipmentStatus
from shopmind.models.segments import CustomerSegment

__all__ = [
    "Base",
    "User",
    "Product",
    "ProductVariant",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Cart",
    "CartItem",
    "Category",
    "Tag",
    "Collection",
    "ProductCategory",
    "ProductTag",
    "CollectionProduct",
    "Coupon",
    "CouponUsage",
    "CartRule",
    "PriceTier",
    "DiscountType",
    "CartRuleType",
    "WishlistItem",
    "RecentlyViewed",
    "Address",
    "Review",
    "StockNotification",
    "ShippingMethod",
    "Return",
    "ReturnStatus",
    "ReturnReason",
    "Shipment",
    "ShipmentStatus",
    "CustomerSegment",
]
