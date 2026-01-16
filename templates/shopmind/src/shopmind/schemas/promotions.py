"""
Pydantic schemas for promotions (Coupons, Cart Rules, Price Tiers).
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from shopmind.models.promotions import DiscountType, CartRuleType


# --- Coupon Schemas ---


class CouponBase(BaseModel):
    """Base coupon fields."""

    code: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z0-9_-]+$")
    description: str | None = None
    discount_type: DiscountType = DiscountType.PERCENTAGE
    discount_value: Decimal = Field(..., gt=0)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    max_discount_amount: Decimal | None = Field(default=None, gt=0)
    max_uses: int | None = Field(default=None, gt=0)
    per_user_limit: int | None = Field(default=None, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True
    restrictions: dict | None = None
    first_order_only: bool = False

    @field_validator("code", mode="before")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        """Convert coupon code to uppercase."""
        return v.upper() if isinstance(v, str) else v


class CouponCreate(CouponBase):
    """Create a new coupon."""

    pass


class CouponUpdate(BaseModel):
    """Update an existing coupon."""

    description: str | None = None
    discount_type: DiscountType | None = None
    discount_value: Decimal | None = Field(default=None, gt=0)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    max_discount_amount: Decimal | None = Field(default=None, gt=0)
    max_uses: int | None = Field(default=None, gt=0)
    per_user_limit: int | None = Field(default=None, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None
    restrictions: dict | None = None
    first_order_only: bool | None = None


class CouponResponse(CouponBase):
    """Coupon in API responses."""

    id: int
    uses_count: int
    created_at: datetime
    is_valid: bool
    remaining_uses: int | None

    model_config = {"from_attributes": True}


class CouponValidation(BaseModel):
    """Result of coupon validation."""

    is_valid: bool
    coupon: CouponResponse | None = None
    error_message: str | None = None
    discount_amount: Decimal | None = None


class ApplyCoupon(BaseModel):
    """Apply a coupon to cart/order."""

    code: str


# --- Cart Rule Schemas ---


class CartRuleBase(BaseModel):
    """Base cart rule fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    rule_type: CartRuleType
    conditions: dict = Field(default_factory=dict)
    discount_type: DiscountType = DiscountType.PERCENTAGE
    discount_value: Decimal = Field(..., gt=0)
    max_discount_amount: Decimal | None = Field(default=None, gt=0)
    priority: int = 0
    is_stackable: bool = True
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True


class CartRuleCreate(CartRuleBase):
    """Create a new cart rule."""

    pass


class CartRuleUpdate(BaseModel):
    """Update an existing cart rule."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    rule_type: CartRuleType | None = None
    conditions: dict | None = None
    discount_type: DiscountType | None = None
    discount_value: Decimal | None = Field(default=None, gt=0)
    max_discount_amount: Decimal | None = Field(default=None, gt=0)
    priority: int | None = None
    is_stackable: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None


class CartRuleResponse(CartRuleBase):
    """Cart rule in API responses."""

    id: int
    created_at: datetime
    is_valid: bool

    model_config = {"from_attributes": True}


# --- Price Tier Schemas ---


class PriceTierBase(BaseModel):
    """Base price tier fields."""

    min_quantity: int = Field(..., ge=1)
    price: Decimal = Field(..., gt=0)
    max_quantity: int | None = Field(default=None, ge=1)


class PriceTierCreate(PriceTierBase):
    """Create a new price tier."""

    variant_id: int


class PriceTierUpdate(BaseModel):
    """Update an existing price tier."""

    min_quantity: int | None = Field(default=None, ge=1)
    price: Decimal | None = Field(default=None, gt=0)
    max_quantity: int | None = Field(default=None, ge=1)


class PriceTierResponse(PriceTierBase):
    """Price tier in API responses."""

    id: int
    variant_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PriceTierBulkCreate(BaseModel):
    """Create multiple price tiers for a variant."""

    variant_id: int
    tiers: list[PriceTierBase]


# --- Sale Price Schemas ---


class SalePriceSet(BaseModel):
    """Set sale price on a variant."""

    sale_price: Decimal = Field(..., gt=0)
    sale_start: datetime | None = None
    sale_end: datetime | None = None


class SalePriceClear(BaseModel):
    """Clear sale price from a variant."""

    pass  # No fields needed


# --- Discount Calculation Results ---


class DiscountLine(BaseModel):
    """A single discount applied."""

    source: str  # "coupon", "cart_rule", "sale", "tier"
    source_id: int | None = None  # ID of coupon/rule if applicable
    source_name: str  # Human-readable name
    discount_amount: Decimal
    discount_type: DiscountType


class DiscountSummary(BaseModel):
    """Summary of all discounts applied to cart."""

    discounts: list[DiscountLine] = []
    total_discount: Decimal = Decimal("0.00")
    coupon_code: str | None = None

    @property
    def has_discounts(self) -> bool:
        return len(self.discounts) > 0


class CartWithDiscounts(BaseModel):
    """Cart totals with discounts applied."""

    subtotal: Decimal
    discount_summary: DiscountSummary
    shipping: Decimal
    total: Decimal
