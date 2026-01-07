import json
import os
import pytest

def test_batch_1_decisions():
    output_path = "decisions/batch_1.json"
    assert os.path.exists(output_path), "Output file decisions/batch_1.json not found"
    
    with open(output_path, 'r') as f:
        data = json.load(f)
    
    decisions = {item['id']: item for item in data.get('decisions', [])}
    
    # Rule 1.1: Standard Meal < $50 (No receipt needed) -> APPROVED
    assert decisions['exp_101']['status'] == 'APPROVED', "exp_101 should be APPROVED (Meal < $50)"
    
    # Rule 1.1: Standard Meal > $50 (No receipt) -> REJECTED
    assert decisions['exp_102']['status'] == 'REJECTED', "exp_102 should be REJECTED (Meal > $50 no receipt)"
    
    # Rule 1.2: NYC Meal < $75 (No receipt needed) -> APPROVED
    assert decisions['exp_103']['status'] == 'APPROVED', "exp_103 should be APPROVED (NYC Meal < $75)"
    
    # Rule 2.1: Rideshare Internal Project -> REJECTED
    assert decisions['exp_104']['status'] == 'REJECTED', "exp_104 should be REJECTED (Internal project code)"
    
    # Rule 2.1: Rideshare External Project -> APPROVED
    assert decisions['exp_105']['status'] == 'APPROVED', "exp_105 should be APPROVED (External project code)"
    
    # Rule 1.1: Alcohol -> REJECTED
    assert decisions['exp_106']['status'] == 'REJECTED', "exp_106 should be REJECTED (Alcohol prohibited)"
