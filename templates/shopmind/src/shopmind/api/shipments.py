"""
Shipments API endpoints.

Handles shipment creation, tracking, and fulfillment status.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.models.shipments import ShipmentStatus
from shopmind.schemas.shipments import (
    ShipmentCreate,
    ShipmentUpdate,
    ShipmentStatusUpdate,
    ShipmentResponse,
    ShipmentListResponse,
    PaginatedShipments,
    OrderFulfillmentStatus,
)
from shopmind.services.auth import get_current_user, get_current_admin
from shopmind.services import fulfillment as fulfillment_service

router = APIRouter(prefix="/shipments", tags=["Shipments"])


# --- Customer Endpoints ---


@router.get("/order/{order_id}", response_model=list[ShipmentListResponse])
def get_order_shipments(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ShipmentListResponse]:
    """
    Get shipments for an order.

    Users can only view shipments for their own orders.
    """
    # Get fulfillment status (includes validation)
    fulfillment_status = fulfillment_service.get_order_fulfillment_status(db, order_id)

    # Check if user owns the order
    from shopmind.services import orders as order_service
    order = order_service.get_order(db, order_id)
    if order and order.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return fulfillment_status.shipments


@router.get("/order/{order_id}/status", response_model=OrderFulfillmentStatus)
def get_order_fulfillment_status(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> OrderFulfillmentStatus:
    """
    Get detailed fulfillment status for an order.

    Shows shipped vs total items.
    """
    # Get fulfillment status
    fulfillment_status = fulfillment_service.get_order_fulfillment_status(db, order_id)

    # Check if user owns the order
    from shopmind.services import orders as order_service
    order = order_service.get_order(db, order_id)
    if order and order.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return fulfillment_status


@router.get("/{shipment_id}/track", response_model=ShipmentResponse)
def track_shipment(
    shipment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ShipmentResponse:
    """
    Get tracking information for a shipment.

    Users can only track shipments for their own orders.
    """
    shipment = fulfillment_service.get_shipment(db, shipment_id)

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    # Check if user owns the order
    from shopmind.services import orders as order_service
    order = order_service.get_order(db, shipment.order_id)
    if order and order.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return ShipmentResponse(
        id=shipment.id,
        order_id=shipment.order_id,
        status=shipment.status,
        carrier=shipment.carrier,
        tracking_number=shipment.tracking_number,
        tracking_url=shipment.tracking_url,
        shipping_method_id=shipment.shipping_method_id,
        items=[{"order_item_id": i["order_item_id"], "quantity": i["quantity"]} for i in shipment.items],
        shipped_at=shipment.shipped_at,
        delivered_at=shipment.delivered_at,
        notes=shipment.notes,
        item_count=shipment.item_count,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
    )


# --- Admin Endpoints ---


@router.get("/admin/all", response_model=PaginatedShipments)
def list_all_shipments(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    status_filter: ShipmentStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedShipments:
    """List all shipments. **Admin only.**"""
    skip = (page - 1) * page_size
    shipments, total = fulfillment_service.get_all_shipments(
        db,
        status_filter=status_filter,
        skip=skip,
        limit=page_size,
    )

    return PaginatedShipments(
        items=[
            ShipmentListResponse(
                id=s.id,
                order_id=s.order_id,
                status=s.status,
                carrier=s.carrier,
                tracking_number=s.tracking_number,
                item_count=s.item_count,
                shipped_at=s.shipped_at,
                created_at=s.created_at,
            )
            for s in shipments
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/admin", response_model=ShipmentResponse, status_code=201)
def create_shipment(
    shipment_data: ShipmentCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ShipmentResponse:
    """
    Create a new shipment for an order. **Admin only.**

    Validates that items belong to the order and quantities
    don't exceed unshipped quantities.
    """
    shipment = fulfillment_service.create_shipment(db, shipment_data)

    return ShipmentResponse(
        id=shipment.id,
        order_id=shipment.order_id,
        status=shipment.status,
        carrier=shipment.carrier,
        tracking_number=shipment.tracking_number,
        tracking_url=shipment.tracking_url,
        shipping_method_id=shipment.shipping_method_id,
        items=[{"order_item_id": i["order_item_id"], "quantity": i["quantity"]} for i in shipment.items],
        shipped_at=shipment.shipped_at,
        delivered_at=shipment.delivered_at,
        notes=shipment.notes,
        item_count=shipment.item_count,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
    )


@router.patch("/admin/{shipment_id}", response_model=ShipmentResponse)
def update_shipment(
    shipment_id: int,
    update_data: ShipmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ShipmentResponse:
    """Update shipment details. **Admin only.**"""
    shipment = fulfillment_service.get_shipment(db, shipment_id)

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    updated = fulfillment_service.update_shipment(db, shipment, update_data)

    return ShipmentResponse(
        id=updated.id,
        order_id=updated.order_id,
        status=updated.status,
        carrier=updated.carrier,
        tracking_number=updated.tracking_number,
        tracking_url=updated.tracking_url,
        shipping_method_id=updated.shipping_method_id,
        items=[{"order_item_id": i["order_item_id"], "quantity": i["quantity"]} for i in updated.items],
        shipped_at=updated.shipped_at,
        delivered_at=updated.delivered_at,
        notes=updated.notes,
        item_count=updated.item_count,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.patch("/admin/{shipment_id}/status", response_model=ShipmentResponse)
def update_shipment_status(
    shipment_id: int,
    status_data: ShipmentStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ShipmentResponse:
    """
    Update shipment status. **Admin only.**

    Valid transitions:
    - pending -> shipped, failed
    - shipped -> in_transit, delivered, returned
    - in_transit -> delivered, returned, failed
    - delivered -> returned
    - failed -> pending (retry)
    """
    shipment = fulfillment_service.get_shipment(db, shipment_id)

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )

    updated = fulfillment_service.update_shipment_status(db, shipment, status_data)

    return ShipmentResponse(
        id=updated.id,
        order_id=updated.order_id,
        status=updated.status,
        carrier=updated.carrier,
        tracking_number=updated.tracking_number,
        tracking_url=updated.tracking_url,
        shipping_method_id=updated.shipping_method_id,
        items=[{"order_item_id": i["order_item_id"], "quantity": i["quantity"]} for i in updated.items],
        shipped_at=updated.shipped_at,
        delivered_at=updated.delivered_at,
        notes=updated.notes,
        item_count=updated.item_count,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )
