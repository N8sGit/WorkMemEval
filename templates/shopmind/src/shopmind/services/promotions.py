"""
Service for managing promotions and calculating discounts.

Handles coupons, cart rules, price tiers, and discount calculations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from shopmind.models.promotions import (
    Coupon,
    CouponUsage,
    CartRule,
    PriceTier,
    DiscountType,
    CartRuleType,
)
from shopmind.models.order import Cart, CartItem
from shopmind.models.product import ProductVariant
from shopmind.models.user import User
from shopmind.schemas.promotions import (
    CouponCreate,
    CouponUpdate,
    CartRuleCreate,
    CartRuleUpdate,
    PriceTierCreate,
    PriceTierUpdate,
    DiscountLine,
    DiscountSummary,
)


# --- Coupon Operations ---


def get_coupon(db: Session, coupon_id: int) -> Coupon | None:
    """Get a coupon by ID."""
    return db.query(Coupon).filter(Coupon.id == coupon_id).first()


def get_coupon_by_code(db: Session, code: str) -> Coupon | None:
    """Get a coupon by code (case-insensitive)."""
    return db.query(Coupon).filter(Coupon.code == code.upper()).first()


def list_coupons(
    db: Session,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[Coupon]:
    """List all coupons."""
    query = db.query(Coupon)
    if active_only:
        query = query.filter(Coupon.is_active == True)
    return query.order_by(Coupon.created_at.desc()).offset(skip).limit(limit).all()


def create_coupon(db: Session, coupon_data: CouponCreate) -> Coupon:
    """Create a new coupon."""
    # Check for duplicate code
    if get_coupon_by_code(db, coupon_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coupon with code '{coupon_data.code}' already exists",
        )

    coupon = Coupon(**coupon_data.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


def update_coupon(db: Session, coupon: Coupon, update_data: CouponUpdate) -> Coupon:
    """Update an existing coupon."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(coupon, field, value)

    db.commit()
    db.refresh(coupon)
    return coupon


def delete_coupon(db: Session, coupon: Coupon) -> None:
    """Delete a coupon."""
    db.delete(coupon)
    db.commit()


def validate_coupon(
    db: Session,
    code: str,
    user: User | None,
    cart_subtotal: Decimal,
    is_first_order: bool = False,
) -> tuple[bool, Coupon | None, str | None]:
    """
    Validate a coupon for use.

    Returns: (is_valid, coupon, error_message)
    """
    coupon = get_coupon_by_code(db, code)

    if not coupon:
        return False, None, "Coupon not found"

    if not coupon.is_active:
        return False, None, "Coupon is not active"

    now = datetime.now()

    if coupon.valid_from and now < coupon.valid_from:
        return False, None, "Coupon is not yet valid"

    if coupon.valid_until and now > coupon.valid_until:
        return False, None, "Coupon has expired"

    if coupon.max_uses and coupon.uses_count >= coupon.max_uses:
        return False, None, "Coupon has reached maximum uses"

    if coupon.min_order_amount and cart_subtotal < coupon.min_order_amount:
        return (
            False,
            None,
            f"Minimum order amount of ${coupon.min_order_amount} required",
        )

    if coupon.first_order_only and not is_first_order:
        return False, None, "Coupon is for first-time customers only"

    # Check per-user limit if user is logged in
    if user and coupon.per_user_limit:
        user_usage_count = (
            db.query(CouponUsage)
            .filter(
                CouponUsage.coupon_id == coupon.id,
                CouponUsage.user_id == user.id,
            )
            .count()
        )
        if user_usage_count >= coupon.per_user_limit:
            return False, None, "You have already used this coupon"

    return True, coupon, None


def calculate_coupon_discount(
    coupon: Coupon,
    subtotal: Decimal,
) -> Decimal:
    """Calculate the discount amount for a coupon."""
    if coupon.discount_type == DiscountType.PERCENTAGE.value:
        discount = subtotal * (coupon.discount_value / Decimal("100"))
        # Apply max discount cap if set
        if coupon.max_discount_amount:
            discount = min(discount, coupon.max_discount_amount)
    elif coupon.discount_type == DiscountType.FIXED_AMOUNT.value:
        discount = min(coupon.discount_value, subtotal)
    elif coupon.discount_type == DiscountType.FREE_SHIPPING.value:
        # Handled separately in checkout
        discount = Decimal("0.00")
    else:
        discount = Decimal("0.00")

    return discount


def record_coupon_usage(
    db: Session,
    coupon: Coupon,
    user: User,
    order_id: int,
    discount_amount: Decimal,
) -> None:
    """Record a coupon usage and increment counter."""
    usage = CouponUsage(
        coupon_id=coupon.id,
        user_id=user.id,
        order_id=order_id,
        discount_amount=discount_amount,
    )
    db.add(usage)

    coupon.uses_count += 1
    db.commit()


# --- Cart Rule Operations ---


def get_cart_rule(db: Session, rule_id: int) -> CartRule | None:
    """Get a cart rule by ID."""
    return db.query(CartRule).filter(CartRule.id == rule_id).first()


def list_cart_rules(
    db: Session,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[CartRule]:
    """List all cart rules."""
    query = db.query(CartRule)
    if active_only:
        query = query.filter(CartRule.is_active == True)
    return query.order_by(CartRule.priority).offset(skip).limit(limit).all()


def create_cart_rule(db: Session, rule_data: CartRuleCreate) -> CartRule:
    """Create a new cart rule."""
    rule = CartRule(**rule_data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_cart_rule(
    db: Session, rule: CartRule, update_data: CartRuleUpdate
) -> CartRule:
    """Update an existing cart rule."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


def delete_cart_rule(db: Session, rule: CartRule) -> None:
    """Delete a cart rule."""
    db.delete(rule)
    db.commit()


def evaluate_cart_rules(
    db: Session,
    cart_items: list[CartItem],
    subtotal: Decimal,
) -> list[tuple[CartRule, Decimal]]:
    """
    Evaluate all active cart rules against the cart.

    Returns list of (rule, discount_amount) tuples for applicable rules.
    """
    applicable_rules: list[tuple[CartRule, Decimal]] = []

    # Get all valid rules, sorted by priority
    rules = (
        db.query(CartRule)
        .filter(CartRule.is_active == True)
        .order_by(CartRule.priority)
        .all()
    )

    for rule in rules:
        if not rule.is_valid:
            continue

        discount = _evaluate_single_rule(rule, cart_items, subtotal)
        if discount > 0:
            applicable_rules.append((rule, discount))

            # If this rule is not stackable, stop processing
            if not rule.is_stackable:
                break

    return applicable_rules


def _evaluate_single_rule(
    rule: CartRule,
    cart_items: list[CartItem],
    subtotal: Decimal,
) -> Decimal:
    """Evaluate a single cart rule and return the discount amount."""
    conditions = rule.conditions

    if rule.rule_type == CartRuleType.SPEND_X_GET_Y_OFF.value:
        min_spend = Decimal(str(conditions.get("min_spend", 0)))
        if subtotal >= min_spend:
            return _calculate_rule_discount(rule, subtotal)

    elif rule.rule_type == CartRuleType.CATEGORY_DISCOUNT.value:
        category_ids = set(conditions.get("category_ids", []))
        if not category_ids:
            return Decimal("0.00")

        # Calculate subtotal for items in these categories
        category_subtotal = Decimal("0.00")
        for item in cart_items:
            if item.variant and item.variant.product:
                item_categories = {c.id for c in item.variant.product.categories}
                if item_categories & category_ids:
                    category_subtotal += item.variant.final_price * item.quantity

        if category_subtotal > 0:
            return _calculate_rule_discount(rule, category_subtotal)

    elif rule.rule_type == CartRuleType.PRODUCT_DISCOUNT.value:
        product_ids = set(conditions.get("product_ids", []))
        if not product_ids:
            return Decimal("0.00")

        # Calculate subtotal for specific products
        product_subtotal = Decimal("0.00")
        for item in cart_items:
            if item.variant and item.variant.product_id in product_ids:
                product_subtotal += item.variant.final_price * item.quantity

        if product_subtotal > 0:
            return _calculate_rule_discount(rule, product_subtotal)

    elif rule.rule_type == CartRuleType.BUY_X_GET_Y_FREE.value:
        buy_qty = conditions.get("buy_quantity", 2)
        get_qty = conditions.get("get_quantity", 1)
        product_ids = set(conditions.get("product_ids", []))

        # Count qualifying items
        qualifying_qty = 0
        cheapest_price = None

        for item in cart_items:
            if not product_ids or (
                item.variant and item.variant.product_id in product_ids
            ):
                qualifying_qty += item.quantity
                item_price = item.variant.final_price if item.variant else Decimal("0")
                if cheapest_price is None or item_price < cheapest_price:
                    cheapest_price = item_price

        if qualifying_qty >= buy_qty + get_qty and cheapest_price:
            # Calculate how many free items they get
            sets = qualifying_qty // (buy_qty + get_qty)
            free_items = sets * get_qty
            return cheapest_price * free_items

    return Decimal("0.00")


def _calculate_rule_discount(rule: CartRule, applicable_subtotal: Decimal) -> Decimal:
    """Calculate discount amount based on rule type."""
    if rule.discount_type == DiscountType.PERCENTAGE.value:
        discount = applicable_subtotal * (rule.discount_value / Decimal("100"))
    elif rule.discount_type == DiscountType.FIXED_AMOUNT.value:
        discount = min(rule.discount_value, applicable_subtotal)
    else:
        discount = Decimal("0.00")

    # Apply max discount cap
    if rule.max_discount_amount:
        discount = min(discount, rule.max_discount_amount)

    return discount


# --- Price Tier Operations ---


def get_price_tier(db: Session, tier_id: int) -> PriceTier | None:
    """Get a price tier by ID."""
    return db.query(PriceTier).filter(PriceTier.id == tier_id).first()


def list_variant_price_tiers(db: Session, variant_id: int) -> list[PriceTier]:
    """List all price tiers for a variant."""
    return (
        db.query(PriceTier)
        .filter(PriceTier.variant_id == variant_id)
        .order_by(PriceTier.min_quantity)
        .all()
    )


def create_price_tier(db: Session, tier_data: PriceTierCreate) -> PriceTier:
    """Create a new price tier."""
    # Verify variant exists
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == tier_data.variant_id)
        .first()
    )
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    tier = PriceTier(**tier_data.model_dump())
    db.add(tier)
    db.commit()
    db.refresh(tier)
    return tier


def update_price_tier(
    db: Session, tier: PriceTier, update_data: PriceTierUpdate
) -> PriceTier:
    """Update an existing price tier."""
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        setattr(tier, field, value)

    db.commit()
    db.refresh(tier)
    return tier


def delete_price_tier(db: Session, tier: PriceTier) -> None:
    """Delete a price tier."""
    db.delete(tier)
    db.commit()


def set_variant_price_tiers(
    db: Session,
    variant_id: int,
    tiers: list[dict[str, Any]],
) -> list[PriceTier]:
    """Replace all price tiers for a variant."""
    # Delete existing tiers
    db.query(PriceTier).filter(PriceTier.variant_id == variant_id).delete()

    # Create new tiers
    new_tiers = []
    for tier_data in tiers:
        tier = PriceTier(
            variant_id=variant_id,
            min_quantity=tier_data["min_quantity"],
            price=tier_data["price"],
            max_quantity=tier_data.get("max_quantity"),
        )
        db.add(tier)
        new_tiers.append(tier)

    db.commit()
    for tier in new_tiers:
        db.refresh(tier)

    return new_tiers


# --- Sale Price Operations ---


def set_sale_price(
    db: Session,
    variant: ProductVariant,
    sale_price: Decimal,
    sale_start: datetime | None = None,
    sale_end: datetime | None = None,
) -> ProductVariant:
    """Set sale price on a variant."""
    variant.sale_price = sale_price
    variant.sale_start = sale_start
    variant.sale_end = sale_end
    db.commit()
    db.refresh(variant)
    return variant


def clear_sale_price(db: Session, variant: ProductVariant) -> ProductVariant:
    """Clear sale price from a variant."""
    variant.sale_price = None
    variant.sale_start = None
    variant.sale_end = None
    db.commit()
    db.refresh(variant)
    return variant


# --- Discount Engine ---


def calculate_cart_discounts(
    db: Session,
    cart: Cart,
    coupon_code: str | None = None,
    user: User | None = None,
) -> DiscountSummary:
    """
    Calculate all applicable discounts for a cart.

    Returns a DiscountSummary with all discount lines and totals.
    """
    discounts: list[DiscountLine] = []
    total_discount = Decimal("0.00")

    if not cart.items:
        return DiscountSummary(discounts=[], total_discount=Decimal("0.00"))

    # Calculate subtotal (already considers sale prices via variant.final_price)
    subtotal = Decimal("0.00")
    for item in cart.items:
        if item.variant:
            subtotal += item.variant.final_price * item.quantity

    # Apply tiered pricing discounts
    for item in cart.items:
        if item.variant and item.variant.price_tiers:
            regular_total = item.variant.final_price * item.quantity
            tiered_price = item.variant.get_tiered_price(item.quantity)
            tiered_total = tiered_price * item.quantity

            if tiered_total < regular_total:
                tier_discount = regular_total - tiered_total
                discounts.append(
                    DiscountLine(
                        source="tier",
                        source_id=None,
                        source_name=f"Quantity discount on {item.variant.sku}",
                        discount_amount=tier_discount,
                        discount_type=DiscountType.FIXED_AMOUNT,
                    )
                )
                total_discount += tier_discount

    # Apply cart rules
    applicable_rules = evaluate_cart_rules(db, cart.items, subtotal)
    for rule, discount_amount in applicable_rules:
        discounts.append(
            DiscountLine(
                source="cart_rule",
                source_id=rule.id,
                source_name=rule.name,
                discount_amount=discount_amount,
                discount_type=DiscountType(rule.discount_type),
            )
        )
        total_discount += discount_amount

    # Apply coupon if provided
    if coupon_code:
        # Check if user has prior orders for first_order_only coupons
        is_first_order = True
        if user:
            from shopmind.models.order import Order

            prior_orders = (
                db.query(Order).filter(Order.user_id == user.id).count()
            )
            is_first_order = prior_orders == 0

        is_valid, coupon, error = validate_coupon(
            db, coupon_code, user, subtotal - total_discount, is_first_order
        )

        if is_valid and coupon:
            coupon_discount = calculate_coupon_discount(
                coupon, subtotal - total_discount
            )
            if coupon_discount > 0:
                discounts.append(
                    DiscountLine(
                        source="coupon",
                        source_id=coupon.id,
                        source_name=f"Coupon: {coupon.code}",
                        discount_amount=coupon_discount,
                        discount_type=DiscountType(coupon.discount_type),
                    )
                )
                total_discount += coupon_discount

    return DiscountSummary(
        discounts=discounts,
        total_discount=total_discount,
        coupon_code=coupon_code if coupon_code else None,
    )
