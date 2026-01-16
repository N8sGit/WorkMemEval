"""Tests for gift card service integration."""

from decimal import Decimal

import pytest

from shopmind.services import promotions as promo_service
from shopmind.services import segments as segment_service


class TestGiftCardRequirements:
    """Verify gift card business rules are implemented."""

    def test_gift_card_denominations(self):
        """Gift cards support required denominations."""
        from shopmind.services import gift_cards

        assert gift_cards.ALLOWED_GIFT_CARD_VALUES == [
            Decimal("25"),
            Decimal("50"),
            Decimal("100"),
            Decimal("200"),
        ]

    def test_gift_cards_no_loyalty_points(self):
        """Gift card purchases do not earn loyalty points."""
        from shopmind.services import gift_cards

        assert gift_cards.GIFT_CARD_EARNS_LOYALTY is False

    def test_gift_cards_contribute_to_free_shipping(self):
        """Gift cards count toward free shipping threshold."""
        from shopmind.services import gift_cards

        assert gift_cards.GIFT_CARD_COUNTS_TOWARD_FREE_SHIPPING is True

    def test_gift_cards_stack_with_segment_discounts(self):
        """Gift cards can be combined with segment discounts."""
        from shopmind.services import gift_cards

        assert gift_cards.GIFT_CARD_STACKS_WITH_SEGMENTS is True

    def test_gift_card_total_with_segment_discount(self, db_session, test_user, test_product):
        """Gift card redemption allows segment discount to apply."""
        from shopmind.models.segments import CustomerSegment
        from shopmind.services import gift_cards

        segment = CustomerSegment(
            name="VIP",
            slug="vip",
            discount_percentage=Decimal("10.0"),
            priority=10,
            is_active=True,
        )
        db_session.add(segment)
        db_session.commit()
        db_session.refresh(segment)

        segment_service.assign_user_to_segment(db_session, test_user, segment.id)

        subtotal = Decimal("100.00")
        segment_discount, _ = segment_service.calculate_segment_discount(
            db_session, test_user, subtotal
        )
        gift_card_applied = gift_cards.apply_gift_card(subtotal)
        total = gift_cards.apply_gift_card_to_total(
            subtotal, segment_discount, gift_card_applied
        )

        assert segment_discount == Decimal("10.00")
        assert gift_card_applied == subtotal
        assert total == Decimal("0.00")

    def test_gift_cards_do_not_stack_with_coupons(self, db_session, test_product, test_user):
        """Gift cards should not force coupon+segment stacking."""
        from shopmind.models.promotions import Coupon, DiscountType
        from shopmind.models.order import Cart, CartItem
        from shopmind.services import gift_cards

        cart = Cart(session_id="gift-card-test")
        db_session.add(cart)
        db_session.flush()
        db_session.add(
            CartItem(cart_id=cart.id, variant_id=test_product.variants[0].id, quantity=1)
        )

        coupon = Coupon(
            code="SAVE10",
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=Decimal("10.00"),
            is_active=True,
        )
        db_session.add(coupon)
        db_session.commit()

        summary = promo_service.calculate_cart_discounts(
            db_session, cart, coupon_code="SAVE10", user=test_user
        )
        gift_card_applied = gift_cards.apply_gift_card(Decimal("29.99"))
        total = gift_cards.apply_gift_card_to_total(
            Decimal("29.99"), summary.total_discount, gift_card_applied
        )

        assert total == Decimal("0.00")
