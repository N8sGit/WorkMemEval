"""Tests for subscription service integration."""

from decimal import Decimal

from shopmind.services import segments as segment_service


class TestSubscriptionRequirements:
    """Verify subscription business rules."""

    def test_subscription_frequencies(self):
        from shopmind.services import subscriptions

        assert subscriptions.ALLOWED_FREQUENCIES == ["weekly", "bi-weekly", "monthly"]

    def test_subscription_loyalty_multiplier(self):
        from shopmind.services import subscriptions

        assert subscriptions.SUBSCRIPTION_LOYALTY_MULTIPLIER == Decimal("1.5")

    def test_subscription_discount_rule_no_stacking(self, db_session, test_user):
        from shopmind.models.segments import CustomerSegment
        from shopmind.services import subscriptions

        segment = CustomerSegment(
            name="Wholesale",
            slug="wholesale",
            discount_percentage=Decimal("15.0"),
            priority=5,
            is_active=True,
        )
        db_session.add(segment)
        db_session.commit()
        db_session.refresh(segment)

        segment_service.assign_user_to_segment(db_session, test_user, segment.id)

        subtotal = Decimal("200.00")
        segment_discount, _ = segment_service.calculate_segment_discount(
            db_session, test_user, subtotal
        )
        coupon_discount = Decimal("20.00")

        total_discount = subscriptions.choose_best_discount(
            segment_discount, coupon_discount
        )

        assert total_discount == max(segment_discount, coupon_discount)

    def test_subscription_total_with_best_discount(self):
        from shopmind.services import subscriptions

        subtotal = Decimal("120.00")
        segment_discount = Decimal("12.00")
        coupon_discount = Decimal("20.00")

        total = subscriptions.apply_subscription_discount(
            subtotal, segment_discount, coupon_discount
        )

        assert total == subtotal - coupon_discount
