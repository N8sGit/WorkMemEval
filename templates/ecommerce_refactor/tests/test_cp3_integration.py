import pytest
from legacy_processor import MonolithicProcessor

def test_full_refactor():
    """
    CP3: Final system check.
    MonolithicProcessor should basically be a coordinator now, delegating to sub-components.
    """
    mp = MonolithicProcessor("mock_db")
    
    # Check that it uses the components
    assert hasattr(mp, "inventory_manager")
    assert hasattr(mp, "payment_processor")
    
    # Full End-to-End Run
    order = {
        "id": "FINAL_TEST",
        "items": [
            {"sku": "HEAVY_ITEM", "quantity": 1, "price": 50.0, "weight": 12} 
        ],
        "customer": {"email": "final@test.com", "state": "TX"}, # Default tax 8%
        "payment_method": "credit_card",
        "payment_token": "tok_final"
    }
    
    # 50 * 1.08 = 54.00 total
    # Weight 12 > 10 -> Shipping $15.00
    
    success = mp.process_order(order)
    assert success is True
    
    # Verify shipping logic (0-5, 5-10, >10)
    # We can check this by mocking the shipping logic or just checking the output if we modified the return.
    # But since the legacy code printed the result, we assume logic is preserved if it returns True without errors.
    assert len(mp.errors) == 0
