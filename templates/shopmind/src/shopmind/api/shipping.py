"""
Shipping API endpoints.

Handles shipping method management and cost calculation.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.schemas.shipping import (
    ShippingMethodCreate,
    ShippingMethodUpdate,
    ShippingMethodResponse,
    ShippingOptionResponse,
    ShippingOptionsRequest,
    ShippingOptionsResponse,
)
from shopmind.services.auth import get_current_admin
from shopmind.services import shipping as shipping_service

router = APIRouter(prefix="/shipping", tags=["Shipping"])


# --- Public Endpoints ---


@router.post("/options", response_model=ShippingOptionsResponse)
def get_shipping_options(
    request: ShippingOptionsRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ShippingOptionsResponse:
    """
    Get available shipping options with calculated costs.

    Calculates shipping cost based on order subtotal and item count.
    Returns all active shipping methods with their costs.
    """
    options = shipping_service.get_shipping_options(
        db, request.subtotal, request.item_count
    )
    return ShippingOptionsResponse(options=options)


@router.get("/methods", response_model=list[ShippingMethodResponse])
def list_shipping_methods(
    db: Annotated[Session, Depends(get_db)],
) -> list[ShippingMethodResponse]:
    """
    List active shipping methods.

    Returns public shipping method information for display.
    """
    methods = shipping_service.list_shipping_methods(db, active_only=True)
    return [ShippingMethodResponse.model_validate(m) for m in methods]


# --- Admin Endpoints ---


@router.get("/admin/methods", response_model=list[ShippingMethodResponse])
def list_all_shipping_methods(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> list[ShippingMethodResponse]:
    """
    List all shipping methods including inactive. **Admin only.**
    """
    methods = shipping_service.list_shipping_methods(db, active_only=False)
    return [ShippingMethodResponse.model_validate(m) for m in methods]


@router.post("/admin/methods", response_model=ShippingMethodResponse, status_code=201)
def create_shipping_method(
    method_data: ShippingMethodCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ShippingMethodResponse:
    """
    Create a new shipping method. **Admin only.**
    """
    method = shipping_service.create_shipping_method(db, method_data)
    return ShippingMethodResponse.model_validate(method)


@router.get("/admin/methods/{method_id}", response_model=ShippingMethodResponse)
def get_shipping_method(
    method_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ShippingMethodResponse:
    """
    Get a shipping method by ID. **Admin only.**
    """
    method = shipping_service.get_shipping_method(db, method_id)
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping method not found",
        )
    return ShippingMethodResponse.model_validate(method)


@router.patch("/admin/methods/{method_id}", response_model=ShippingMethodResponse)
def update_shipping_method(
    method_id: int,
    update_data: ShippingMethodUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> ShippingMethodResponse:
    """
    Update a shipping method. **Admin only.**
    """
    method = shipping_service.get_shipping_method(db, method_id)
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping method not found",
        )

    updated = shipping_service.update_shipping_method(db, method, update_data)
    return ShippingMethodResponse.model_validate(updated)


@router.delete("/admin/methods/{method_id}", status_code=204)
def delete_shipping_method(
    method_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """
    Delete a shipping method. **Admin only.**
    """
    method = shipping_service.get_shipping_method(db, method_id)
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping method not found",
        )

    shipping_service.delete_shipping_method(db, method)
