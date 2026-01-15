"""
Promotions API endpoints: Coupons, Cart Rules, Price Tiers.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from shopmind.database import get_db
from shopmind.models.user import User
from shopmind.models.product import ProductVariant
from shopmind.schemas.promotions import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    CouponValidation,
    ApplyCoupon,
    CartRuleCreate,
    CartRuleUpdate,
    CartRuleResponse,
    PriceTierCreate,
    PriceTierUpdate,
    PriceTierResponse,
    PriceTierBulkCreate,
    SalePriceSet,
    DiscountSummary,
)
from shopmind.services.auth import get_current_admin, get_current_user_optional
from shopmind.services import promotions as promo_service
from shopmind.services import cart as cart_service

router = APIRouter(tags=["Promotions"])


# --- Coupon Endpoints ---


@router.get("/coupons", response_model=list[CouponResponse])
def list_coupons(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list:
    """List all coupons. **Admin only.**"""
    return promo_service.list_coupons(db, active_only=active_only, skip=skip, limit=limit)


@router.get("/coupons/{coupon_id}", response_model=CouponResponse)
def get_coupon(
    coupon_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> CouponResponse:
    """Get a coupon by ID. **Admin only.**"""
    coupon = promo_service.get_coupon(db, coupon_id)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        )
    return coupon


@router.post("/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(
    coupon_data: CouponCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> CouponResponse:
    """Create a new coupon. **Admin only.**"""
    return promo_service.create_coupon(db, coupon_data)


@router.patch("/coupons/{coupon_id}", response_model=CouponResponse)
def update_coupon(
    coupon_id: int,
    update_data: CouponUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> CouponResponse:
    """Update a coupon. **Admin only.**"""
    coupon = promo_service.get_coupon(db, coupon_id)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        )
    return promo_service.update_coupon(db, coupon, update_data)


@router.delete("/coupons/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coupon(
    coupon_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """Delete a coupon. **Admin only.**"""
    coupon = promo_service.get_coupon(db, coupon_id)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        )
    promo_service.delete_coupon(db, coupon)


@router.post("/coupons/validate", response_model=CouponValidation)
def validate_coupon(
    apply_data: ApplyCoupon,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session_id: str | None = Query(None),
) -> CouponValidation:
    """
    Validate a coupon code.

    Returns validation result with discount preview if valid.
    """
    # Get cart to calculate subtotal
    cart = cart_service.get_or_create_cart(db, user, session_id)
    subtotal = Decimal("0.00")
    for item in cart.items:
        if item.variant:
            subtotal += item.variant.final_price * item.quantity

    # Check if first order
    is_first_order = True
    if user:
        from shopmind.models.order import Order
        prior_orders = db.query(Order).filter(Order.user_id == user.id).count()
        is_first_order = prior_orders == 0

    is_valid, coupon, error_message = promo_service.validate_coupon(
        db, apply_data.code, user, subtotal, is_first_order
    )

    if not is_valid or not coupon:
        return CouponValidation(
            is_valid=False,
            error_message=error_message,
        )

    discount_amount = promo_service.calculate_coupon_discount(coupon, subtotal)

    return CouponValidation(
        is_valid=True,
        coupon=coupon,
        discount_amount=discount_amount,
    )


# --- Cart Rule Endpoints ---


@router.get("/cart-rules", response_model=list[CartRuleResponse])
def list_cart_rules(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list:
    """List all cart rules. **Admin only.**"""
    return promo_service.list_cart_rules(db, active_only=active_only, skip=skip, limit=limit)


@router.get("/cart-rules/{rule_id}", response_model=CartRuleResponse)
def get_cart_rule(
    rule_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> CartRuleResponse:
    """Get a cart rule by ID. **Admin only.**"""
    rule = promo_service.get_cart_rule(db, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart rule not found",
        )
    return rule


@router.post("/cart-rules", response_model=CartRuleResponse, status_code=status.HTTP_201_CREATED)
def create_cart_rule(
    rule_data: CartRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> CartRuleResponse:
    """Create a new cart rule. **Admin only.**"""
    return promo_service.create_cart_rule(db, rule_data)


@router.patch("/cart-rules/{rule_id}", response_model=CartRuleResponse)
def update_cart_rule(
    rule_id: int,
    update_data: CartRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> CartRuleResponse:
    """Update a cart rule. **Admin only.**"""
    rule = promo_service.get_cart_rule(db, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart rule not found",
        )
    return promo_service.update_cart_rule(db, rule, update_data)


@router.delete("/cart-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart_rule(
    rule_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """Delete a cart rule. **Admin only.**"""
    rule = promo_service.get_cart_rule(db, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart rule not found",
        )
    promo_service.delete_cart_rule(db, rule)


# --- Price Tier Endpoints ---


@router.get("/variants/{variant_id}/price-tiers", response_model=list[PriceTierResponse])
def list_price_tiers(
    variant_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> list:
    """List all price tiers for a variant."""
    return promo_service.list_variant_price_tiers(db, variant_id)


@router.post("/price-tiers", response_model=PriceTierResponse, status_code=status.HTTP_201_CREATED)
def create_price_tier(
    tier_data: PriceTierCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> PriceTierResponse:
    """Create a new price tier. **Admin only.**"""
    return promo_service.create_price_tier(db, tier_data)


@router.put("/variants/{variant_id}/price-tiers", response_model=list[PriceTierResponse])
def set_price_tiers(
    variant_id: int,
    tier_data: PriceTierBulkCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> list:
    """Replace all price tiers for a variant. **Admin only.**"""
    # Verify variant exists
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    tiers = [t.model_dump() for t in tier_data.tiers]
    return promo_service.set_variant_price_tiers(db, variant_id, tiers)


@router.patch("/price-tiers/{tier_id}", response_model=PriceTierResponse)
def update_price_tier(
    tier_id: int,
    update_data: PriceTierUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> PriceTierResponse:
    """Update a price tier. **Admin only.**"""
    tier = promo_service.get_price_tier(db, tier_id)
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price tier not found",
        )
    return promo_service.update_price_tier(db, tier, update_data)


@router.delete("/price-tiers/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price_tier(
    tier_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """Delete a price tier. **Admin only.**"""
    tier = promo_service.get_price_tier(db, tier_id)
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price tier not found",
        )
    promo_service.delete_price_tier(db, tier)


# --- Sale Price Endpoints ---


@router.put("/variants/{variant_id}/sale-price", response_model=dict)
def set_sale_price(
    variant_id: int,
    sale_data: SalePriceSet,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Set sale price on a variant. **Admin only.**"""
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    variant = promo_service.set_sale_price(
        db, variant, sale_data.sale_price, sale_data.sale_start, sale_data.sale_end
    )

    return {
        "variant_id": variant.id,
        "sku": variant.sku,
        "regular_price": str(variant.regular_price),
        "sale_price": str(variant.sale_price),
        "sale_start": variant.sale_start.isoformat() if variant.sale_start else None,
        "sale_end": variant.sale_end.isoformat() if variant.sale_end else None,
        "is_on_sale": variant.is_on_sale,
        "final_price": str(variant.final_price),
    }


@router.delete("/variants/{variant_id}/sale-price", status_code=status.HTTP_204_NO_CONTENT)
def clear_sale_price(
    variant_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """Clear sale price from a variant. **Admin only.**"""
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    promo_service.clear_sale_price(db, variant)


# --- Cart Discounts Preview ---


@router.get("/cart/discounts", response_model=DiscountSummary)
def preview_cart_discounts(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session_id: str | None = Query(None),
    coupon_code: str | None = Query(None),
) -> DiscountSummary:
    """
    Preview all discounts that would apply to the current cart.

    Includes sale prices, tiered pricing, cart rules, and optional coupon.
    """
    cart = cart_service.get_or_create_cart(db, user, session_id)
    return promo_service.calculate_cart_discounts(db, cart, coupon_code, user)
