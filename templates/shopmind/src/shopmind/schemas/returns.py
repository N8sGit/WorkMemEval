"""
Pydantic schemas for returns/RMA operations.
"""

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

from shopmind.models.returns import ReturnStatus, ReturnReason


# --- Request Schemas ---


class ReturnRequest(BaseModel):
    """Customer request to return an item."""

    order_id: int
    order_item_id: int | None = None  # Optional: specific item to return
    reason: ReturnReason
    reason_details: str | None = Field(None, max_length=1000)
    quantity: int = Field(default=1, ge=1)


class ReturnApproval(BaseModel):
    """Admin approval of a return request."""

    refund_amount: Decimal = Field(..., ge=0)
    admin_notes: str | None = None
    restocking_fee: Decimal = Field(default=Decimal("0.00"), ge=0)


class ReturnRejection(BaseModel):
    """Admin rejection of a return request."""

    admin_notes: str = Field(..., min_length=1, max_length=1000)


class ReturnReceived(BaseModel):
    """Mark return as received at warehouse."""

    return_tracking_number: str | None = None
    admin_notes: str | None = None


class ReturnRefund(BaseModel):
    """Process refund for a return."""

    refund_amount: Decimal | None = None  # Override calculated amount
    admin_notes: str | None = None


# --- Response Schemas ---


class ReturnResponse(BaseModel):
    """Return details for API responses."""

    id: int
    order_id: int
    order_item_id: int | None
    user_id: int | None
    status: ReturnStatus
    reason: ReturnReason
    reason_details: str | None
    quantity: int
    refund_amount: Decimal | None
    restocking_fee: Decimal
    return_tracking_number: str | None
    stock_restored: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReturnListResponse(BaseModel):
    """Return summary for list views."""

    id: int
    order_id: int
    status: ReturnStatus
    reason: ReturnReason
    quantity: int
    refund_amount: Decimal | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedReturns(BaseModel):
    """Paginated list of returns."""

    items: list[ReturnListResponse]
    total: int
    page: int
    page_size: int
    pages: int
