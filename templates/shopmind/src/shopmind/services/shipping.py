"""
Shipping service.

Handles shipping method CRUD and cost calculation.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from shopmind.models.shipping import ShippingMethod
from shopmind.schemas.shipping import (
    ShippingMethodCreate,
    ShippingMethodUpdate,
    ShippingOptionResponse,
)


# --- Shipping Method CRUD ---


def get_shipping_method(db: Session, method_id: int) -> ShippingMethod | None:
    """Get a shipping method by ID."""
    return db.query(ShippingMethod).filter(ShippingMethod.id == method_id).first()


def list_shipping_methods(
    db: Session, active_only: bool = True
) -> list[ShippingMethod]:
    """List all shipping methods."""
    query = db.query(ShippingMethod)

    if active_only:
        query = query.filter(ShippingMethod.is_active == True)

    return query.order_by(ShippingMethod.sort_order, ShippingMethod.name).all()


def create_shipping_method(
    db: Session, method_data: ShippingMethodCreate
) -> ShippingMethod:
    """Create a new shipping method."""
    method = ShippingMethod(**method_data.model_dump())
    db.add(method)
    db.commit()
    db.refresh(method)
    return method


def update_shipping_method(
    db: Session, method: ShippingMethod, update_data: ShippingMethodUpdate
) -> ShippingMethod:
    """Update a shipping method."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(method, field, value)

    db.commit()
    db.refresh(method)
    return method


def delete_shipping_method(db: Session, method: ShippingMethod) -> None:
    """Delete a shipping method."""
    db.delete(method)
    db.commit()


# --- Shipping Cost Calculation ---


def get_shipping_options(
    db: Session, subtotal: Decimal, item_count: int
) -> list[ShippingOptionResponse]:
    """
    Get available shipping options with calculated costs.

    Args:
        db: Database session
        subtotal: Order subtotal before shipping
        item_count: Total number of items

    Returns:
        List of shipping options with costs
    """
    methods = list_shipping_methods(db, active_only=True)

    options = []
    for method in methods:
        cost = method.calculate_cost(subtotal, item_count)
        is_free = cost == Decimal("0.00") and method.free_threshold is not None

        options.append(
            ShippingOptionResponse(
                id=method.id,
                name=method.name,
                description=method.description,
                carrier=method.carrier,
                estimated_delivery=method.estimated_delivery,
                cost=cost,
                is_free=is_free,
            )
        )

    return options


def calculate_shipping_cost(
    db: Session, method_id: int, subtotal: Decimal, item_count: int
) -> Decimal:
    """
    Calculate shipping cost for a specific method.

    Args:
        db: Database session
        method_id: Shipping method ID
        subtotal: Order subtotal
        item_count: Total number of items

    Returns:
        Shipping cost

    Raises:
        ValueError: If shipping method not found or inactive
    """
    method = get_shipping_method(db, method_id)

    if not method or not method.is_active:
        raise ValueError("Invalid shipping method")

    return method.calculate_cost(subtotal, item_count)
