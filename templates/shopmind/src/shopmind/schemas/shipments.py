"""
Pydantic schemas for shipment/fulfillment operations.
"""

from datetime import datetime
from pydantic import BaseModel, Field

from shopmind.models.shipments import ShipmentStatus


# --- Request Schemas ---


class ShipmentItem(BaseModel):
    """Item in a shipment."""

    order_item_id: int
    quantity: int = Field(..., ge=1)


class ShipmentCreate(BaseModel):
    """Create a new shipment for an order."""

    order_id: int
    items: list[ShipmentItem]
    carrier: str | None = Field(None, max_length=50)
    tracking_number: str | None = Field(None, max_length=100)
    tracking_url: str | None = Field(None, max_length=500)
    shipping_method_id: int | None = None
    notes: str | None = None


class ShipmentUpdate(BaseModel):
    """Update shipment details."""

    carrier: str | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None
    notes: str | None = None


class ShipmentStatusUpdate(BaseModel):
    """Update shipment status."""

    status: ShipmentStatus
    notes: str | None = None


# --- Response Schemas ---


class ShipmentItemResponse(BaseModel):
    """Shipment item details."""

    order_item_id: int
    quantity: int


class ShipmentResponse(BaseModel):
    """Shipment details for API responses."""

    id: int
    order_id: int
    status: ShipmentStatus
    carrier: str | None
    tracking_number: str | None
    tracking_url: str | None
    shipping_method_id: int | None
    items: list[ShipmentItemResponse]
    shipped_at: datetime | None
    delivered_at: datetime | None
    notes: str | None
    item_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShipmentListResponse(BaseModel):
    """Shipment summary for list views."""

    id: int
    order_id: int
    status: ShipmentStatus
    carrier: str | None
    tracking_number: str | None
    item_count: int
    shipped_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedShipments(BaseModel):
    """Paginated list of shipments."""

    items: list[ShipmentListResponse]
    total: int
    page: int
    page_size: int
    pages: int


class OrderFulfillmentStatus(BaseModel):
    """Fulfillment status for an order."""

    order_id: int
    total_items: int
    shipped_items: int
    delivered_items: int
    is_fully_shipped: bool
    is_fully_delivered: bool
    shipments: list[ShipmentListResponse]
