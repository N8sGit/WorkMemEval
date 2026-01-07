import pytest
from legacy_processor import MonolithicProcessor

def test_payment_extraction():
    """
    CP2: Verify PaymentProcessor extraction.
    """
    # 1. Check for class
    from legacy_processor import PaymentProcessor
    
    # 2. Check methods
    pp = PaymentProcessor()
    assert hasattr(pp, "process_payment")
    assert hasattr(pp, "_charge_gateway_a")
    assert hasattr(pp, "_charge_gateway_b")
    
    # 3. Test Integration
    mp = MonolithicProcessor("mock_db")
    assert hasattr(mp, "payment_processor")
    
    # 4. Test logic preservation (Tax calculation was part of payment flow in legacy?)
    # Actually tax was in _calculate_total. The user might have moved it or kept it.
    # The requirement is to extract PAYMENT GATEWAY logic.
    
    order_total = 100.00
    assert pp.process_payment(order_total, "tok_123", "credit_card") is True

def test_tax_logic_preservation():
    """Ensure tax logic wasn't lost in the shuffle."""
    mp = MonolithicProcessor("mock_db")
    
    # CA Case (9%)
    order_ca = {
        "items": [{"sku": "A", "quantity": 1, "price": 100.0}],
        "customer": {"state": "CA"}
    }
    # 100 * 1.09 = 109
    assert abs(mp._calculate_total(order_ca) - 109.0) < 0.01

    # NY Case (8.5%)
    order_ny = {
        "items": [{"sku": "A", "quantity": 1, "price": 100.0}],
        "customer": {"state": "NY"}
    }
    # 100 * 1.085 = 108.5
    assert abs(mp._calculate_total(order_ny) - 108.5) < 0.01
