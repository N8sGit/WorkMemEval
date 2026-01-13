import pytest
from legacy_processor import MonolithicProcessor

def test_initial_structure():
    """
    CP1: Verify that InventoryManager has been extracted and integrated.
    """
    # 1. Check for the new class definition in the file
    from legacy_processor import InventoryManager
    
    # 2. Test the new class in isolation
    inv = InventoryManager("mock_db")
    assert hasattr(inv, "check_stock")
    assert hasattr(inv, "update_batch")
    
    # 3. Verify logic preservation
    # The legacy code mocked 100 items.
    assert inv.check_stock("SKU123", 50) == True
    assert inv.check_stock("SKU123", 101) == False
    
    # 4. Verify Integration into MonolithicProcessor
    # The processor should now have an instance of InventoryManager
    mp = MonolithicProcessor("mock_db")
    assert hasattr(mp, "inventory_manager")
    assert isinstance(mp.inventory_manager, InventoryManager)

def test_legacy_order_flow_still_works():
    """Ensure we didn't break the main flow."""
    mp = MonolithicProcessor("mock_db")
    order = {
        "id": "123",
        "items": [{"sku": "ABC", "quantity": 1, "price": 10.0, "weight": 2}],
        "customer": {"email": "test@test.com", "state": "CA"},
        "payment_method": "credit_card",
        "payment_token": "tok_123"
    }
    # Should still return True
    assert mp.process_order(order) is True
