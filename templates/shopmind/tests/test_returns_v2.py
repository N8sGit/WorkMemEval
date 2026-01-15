"""Tests for updated return policy service (returns_v2)."""

from decimal import Decimal


class TestReturnPolicyUpdates:
    """Validate return window changes and condition ratings preservation."""

    def test_return_windows_updated(self):
        from shopmind.services import returns_v2

        assert returns_v2.STANDARD_RETURN_DAYS == 45
        assert returns_v2.VIP_RETURN_DAYS == 90
        assert returns_v2.DIGITAL_RETURN_DAYS == 14

    def test_restocking_fee_unchanged(self):
        from shopmind.services import returns_v2

        assert returns_v2.RESTOCKING_FEE_PERCENT == Decimal("15.00")

    def test_condition_rating_system_preserved(self):
        from shopmind.services import returns_v2

        expected = ["NEW", "LIKE_NEW", "GOOD", "FAIR", "POOR"]
        assert returns_v2.CONDITION_RATINGS == expected

    def test_refund_percentage_mapping_preserved(self):
        from shopmind.services import returns_v2

        assert returns_v2.CONDITION_REFUND_PERCENTAGES["NEW"] == Decimal("1.00")
        assert returns_v2.CONDITION_REFUND_PERCENTAGES["LIKE_NEW"] == Decimal("0.9")
        assert returns_v2.CONDITION_REFUND_PERCENTAGES["GOOD"] == Decimal("0.75")
        assert returns_v2.CONDITION_REFUND_PERCENTAGES["FAIR"] == Decimal("0.5")
        assert returns_v2.CONDITION_REFUND_PERCENTAGES["POOR"] == Decimal("0.0")
