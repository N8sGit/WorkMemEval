import json
import os
import pytest

def test_batch_3_decisions():
    output_path = "decisions/batch_3.json"
    assert os.path.exists(output_path), "Output file decisions/batch_3.json not found"
    
    with open(output_path, 'r') as f:
        data = json.load(f)
    
    decisions = {item['id']: item for item in data.get('decisions', [])}
    
    # PROBE: Update Robustness (Memo changed rules)
    
    # Update 1: NYC Threshold raised to $90
    # exp_301: Meal $85 NYC, No Receipt.
    # Old Rule ($75): REJECTED.
    # New Rule ($90): APPROVED.
    assert decisions['exp_301']['status'] == 'APPROVED', "exp_301 should be APPROVED (NYC limit raised to $90)"
    
    # Update 2: Lyft Terminated
    # exp_302: Lyft $45.
    # Old Rule: APPROVED.
    # New Rule: REJECTED.
    assert decisions['exp_302']['status'] == 'REJECTED', "exp_302 should be REJECTED (Lyft vendor terminated)"
    
    # exp_303: Uber $45 -> APPROVED (Uber still ok)
    assert decisions['exp_303']['status'] == 'APPROVED', "exp_303 should be APPROVED (Uber still valid)"
