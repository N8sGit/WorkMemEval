"""
Pydantic schemas for order operations.
"""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

from shopmind.models.order import OrderStatus


# --- Request Schemas ---

class ShippingAddress(BaseModel):
    """Shipping address for checkout."""

    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=1, max_length=100)


class GuestInfo(BaseModel):
    """Guest checkout information."""

    email: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)


class CheckoutRequest(BaseModel):
    """Request to create order from cart."""

    shipping: ShippingAddress
    shipping_method_id: int | None = None  # If not provided, uses cheapest option
    coupon_code: str | None = None

    # Guest checkout (required if not authenticated)
    guest: GuestInfo | None = None

    # Customer notes
    customer_notes: str | None = None

    # Gift options
    is_gift: bool = False
    gift_message: str | None = None


class OrderStatusUpdate(BaseModel):
    """Update order status (admin only)."""

    status: OrderStatus
    notes: str | None = None


# --- Response Schemas ---

class OrderItemResponse(BaseModel):
    """Order line item."""

    id: int
    variant_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    product_name: str
    variant_sku: str
    variant_attributes: str | None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    """Full order details."""

    id: int
    user_id: int | None
    status: OrderStatus
    subtotal: Decimal
    discount_amount: Decimal = Decimal("0.00")
    shipping_cost: Decimal
    tax: Decimal
    total: Decimal
    coupon_code: str | None = None

    # Shipping info
    shipping_name: str | None
    shipping_address: str | None
    shipping_city: str | None
    shipping_postal_code: str | None
    shipping_country: str | None
    shipping_method_name: str | None = None

    # Guest info
    guest_email: str | None = None
    guest_name: str | None = None

    # Notes and gift
    customer_notes: str | None = None
    is_gift: bool = False
    gift_message: str | None = None

    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Order summary for list views."""

    id: int
    status: OrderStatus
    total: Decimal
    item_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedOrders(BaseModel):
    """Paginated list of orders."""

    items: list[OrderListResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CheckoutResponse(BaseModel):
    """Response after successful checkout."""

    order_id: int
    status: OrderStatus
    total: Decimal
    message: str = "Order created successfully"
