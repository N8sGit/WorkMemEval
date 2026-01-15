"""
Order service for checkout and order management.

Key responsibilities:
- Checkout flow (cart -> order conversion)
- Stock reservation and deduction
- Order status management
- Order history
- Guest checkout support
"""

import json
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from shopmind.models.order import Order, OrderItem, OrderStatus, Cart, CartItem
from shopmind.models.product import ProductVariant
from shopmind.models.user import User
from shopmind.schemas.order import ShippingAddress, CheckoutRequest
from shopmind.events.base import event_bus, Event
from shopmind.services import promotions as promo_service
from shopmind.services import shipping as shipping_service
from dataclasses import dataclass


# --- Order Events ---

@dataclass
class OrderCreated(Event):
    """Emitted when a new order is created."""
    order_id: int = 0
    user_id: int = 0
    total: Decimal = Decimal("0.00")


@dataclass
class OrderStatusChanged(Event):
    """Emitted when order status changes."""
    order_id: int = 0
    old_status: str = ""
    new_status: str = ""


@dataclass
class StockReserved(Event):
    """Emitted when stock is reserved for an order."""
    order_id: int = 0
    variant_id: int = 0
    quantity: int = 0


# --- Checkout ---

def checkout(
    db: Session,
    cart: Cart,
    checkout_data: CheckoutRequest,
    user: User | None = None,
) -> Order:
    """
    Convert cart to order.

    Supports both authenticated and guest checkout.

    Process:
    1. Validate cart has items
    2. Validate guest info if not authenticated
    3. Check stock availability for all items
    4. Calculate totals with discounts
    5. Validate and apply coupon if provided
    6. Calculate shipping using selected method
    7. Create order with items
    8. Deduct stock
    9. Record coupon usage
    10. Clear cart

    Args:
        db: Database session
        cart: Shopping cart to convert
        checkout_data: Checkout parameters including shipping, guest info, etc.
        user: Authenticated user (None for guest checkout)

    Raises:
        HTTPException: If cart is empty, stock insufficient, coupon invalid,
                      or guest info missing for guest checkout
    """
    # Validate guest checkout
    if user is None:
        if not checkout_data.guest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guest information is required for guest checkout",
            )

    # Load cart items with variants and products (including categories for cart rules)
    cart = (
        db.query(Cart)
        .options(
            joinedload(Cart.items)
            .joinedload(CartItem.variant)
            .joinedload(ProductVariant.product)
        )
        .filter(Cart.id == cart.id)
        .first()
    )

    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    # Validate stock for all items
    stock_errors = []
    for item in cart.items:
        variant = item.variant
        if variant.stock_quantity < item.quantity:
            stock_errors.append({
                "sku": variant.sku,
                "requested": item.quantity,
                "available": variant.stock_quantity,
            })

    if stock_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Insufficient stock for some items",
                "items": stock_errors,
            },
        )

    # Calculate subtotal (sale prices already applied via variant.final_price)
    subtotal = sum(
        (item.variant.final_price * item.quantity for item in cart.items),
        Decimal("0.00"),
    )
    item_count = sum(item.quantity for item in cart.items)

    # Calculate all discounts (tiered pricing, cart rules, coupon)
    discount_summary = promo_service.calculate_cart_discounts(
        db, cart, checkout_data.coupon_code, user
    )
    discount_amount = discount_summary.total_discount

    # Validate coupon separately if provided (for error messaging)
    coupon = None
    coupon_discount = Decimal("0.00")
    if checkout_data.coupon_code:
        # Check if first order (only for authenticated users)
        is_first_order = False
        if user:
            prior_orders = db.query(Order).filter(Order.user_id == user.id).count()
            is_first_order = prior_orders == 0

        is_valid, coupon, error = promo_service.validate_coupon(
            db, checkout_data.coupon_code, user, subtotal, is_first_order
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid coupon: {error}",
            )
        coupon_discount = promo_service.calculate_coupon_discount(coupon, subtotal - discount_amount + coupon_discount)

    # Calculate final totals
    discounted_subtotal = subtotal - discount_amount

    # Calculate shipping cost using shipping method
    shipping_cost = Decimal("0.00")
    shipping_method = None
    shipping_method_name = None

    if checkout_data.shipping_method_id:
        # Use selected shipping method
        try:
            shipping_cost = shipping_service.calculate_shipping_cost(
                db, checkout_data.shipping_method_id, discounted_subtotal, item_count
            )
            shipping_method = shipping_service.get_shipping_method(
                db, checkout_data.shipping_method_id
            )
            if shipping_method:
                shipping_method_name = shipping_method.name
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    else:
        # Use cheapest available shipping option
        options = shipping_service.get_shipping_options(db, discounted_subtotal, item_count)
        if options:
            cheapest = min(options, key=lambda o: o.cost)
            shipping_cost = cheapest.cost
            shipping_method = shipping_service.get_shipping_method(db, cheapest.id)
            shipping_method_name = cheapest.name
        else:
            # Fallback to legacy calculation if no shipping methods configured
            shipping_cost = calculate_shipping(discounted_subtotal, checkout_data.shipping)

    # Check for free shipping coupon
    if coupon and coupon.discount_type == "free_shipping":
        shipping_cost = Decimal("0.00")

    tax = calculate_tax(discounted_subtotal, checkout_data.shipping)
    total = discounted_subtotal + shipping_cost + tax

    # Create order
    order = Order(
        user_id=user.id if user else None,
        guest_email=checkout_data.guest.email if checkout_data.guest else None,
        guest_name=checkout_data.guest.name if checkout_data.guest else None,
        status=OrderStatus.PENDING,
        subtotal=subtotal,
        discount_amount=discount_amount,
        shipping_cost=shipping_cost,
        tax=tax,
        total=total,
        coupon_code=checkout_data.coupon_code.upper() if checkout_data.coupon_code else None,
        coupon_id=coupon.id if coupon else None,
        shipping_name=checkout_data.shipping.name,
        shipping_address=checkout_data.shipping.address,
        shipping_city=checkout_data.shipping.city,
        shipping_postal_code=checkout_data.shipping.postal_code,
        shipping_country=checkout_data.shipping.country,
        shipping_method_id=shipping_method.id if shipping_method else None,
        shipping_method_name=shipping_method_name,
        customer_notes=checkout_data.customer_notes,
        is_gift=checkout_data.is_gift,
        gift_message=checkout_data.gift_message if checkout_data.is_gift else None,
    )
    db.add(order)
    db.flush()  # Get order.id

    # Create order items and deduct stock
    for cart_item in cart.items:
        variant = cart_item.variant
        product = variant.product

        order_item = OrderItem(
            order_id=order.id,
            variant_id=variant.id,
            quantity=cart_item.quantity,
            unit_price=variant.final_price,
            product_name=product.name,
            variant_sku=variant.sku,
            variant_attributes=json.dumps(variant.attributes),
        )
        db.add(order_item)

        # Deduct stock
        variant.stock_quantity -= cart_item.quantity

        # Emit stock event
        event_bus.emit(StockReserved(
            order_id=order.id,
            variant_id=variant.id,
            quantity=cart_item.quantity,
        ))

    # Record coupon usage if coupon was applied
    if coupon and user:
        # Find the coupon discount amount from the summary
        coupon_discount_amount = Decimal("0.00")
        for d in discount_summary.discounts:
            if d.source == "coupon":
                coupon_discount_amount = d.discount_amount
                break
        promo_service.record_coupon_usage(db, coupon, user, order.id, coupon_discount_amount)

    # Clear cart
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

    db.commit()
    db.refresh(order)

    # Emit order created event
    event_bus.emit(OrderCreated(
        order_id=order.id,
        user_id=user.id if user else 0,
        total=total,
    ))

    return order


def calculate_shipping(subtotal: Decimal, shipping: ShippingAddress) -> Decimal:
    """
    Calculate shipping cost.

    TODO: Implement real shipping calculation based on:
    - Destination country/region
    - Order weight/size
    - Shipping method selection
    """
    # Simple flat rate for now
    if subtotal >= Decimal("100.00"):
        return Decimal("0.00")  # Free shipping over $100
    return Decimal("9.99")


def calculate_tax(subtotal: Decimal, shipping: ShippingAddress) -> Decimal:
    """
    Calculate tax based on shipping destination.

    TODO: Implement real tax calculation based on:
    - Destination jurisdiction
    - Product categories
    - Tax exemptions
    """
    # Simple 8% tax for now
    return (subtotal * Decimal("0.08")).quantize(Decimal("0.01"))


# --- Order Management ---

def get_order(db: Session, order_id: int) -> Order | None:
    """Get order by ID with items."""
    return (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )


def get_user_orders(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Order], int]:
    """Get paginated orders for a user."""
    query = db.query(Order).filter(Order.user_id == user.id)
    total = query.count()
    orders = (
        query.order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return orders, total


def get_all_orders(
    db: Session,
    status_filter: OrderStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Order], int]:
    """Get all orders (admin). Optionally filter by status."""
    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)

    total = query.count()
    orders = (
        query.order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return orders, total


def update_order_status(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    notes: str | None = None,
) -> Order:
    """
    Update order status.

    Validates status transitions and handles side effects.
    """
    old_status = order.status

    # Validate transition
    if not is_valid_status_transition(old_status, new_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition: {old_status.value} -> {new_status.value}",
        )

    order.status = new_status
    if notes:
        existing_notes = order.notes or ""
        order.notes = f"{existing_notes}\n[{new_status.value}] {notes}".strip()

    db.commit()
    db.refresh(order)

    # Handle side effects
    if new_status == OrderStatus.CANCELLED:
        restore_stock(db, order)

    # Emit event
    event_bus.emit(OrderStatusChanged(
        order_id=order.id,
        old_status=old_status.value,
        new_status=new_status.value,
    ))

    return order


def is_valid_status_transition(old: OrderStatus, new: OrderStatus) -> bool:
    """Check if status transition is allowed."""
    # Define valid transitions
    valid_transitions = {
        OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
        OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
        OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
        OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
        OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
        OrderStatus.CANCELLED: set(),  # Terminal state
        OrderStatus.REFUNDED: set(),  # Terminal state
    }
    return new in valid_transitions.get(old, set())


def restore_stock(db: Session, order: Order) -> None:
    """Restore stock when order is cancelled."""
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order.id)
        .first()
    )

    for item in order.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if variant:
            variant.stock_quantity += item.quantity

    db.commit()
