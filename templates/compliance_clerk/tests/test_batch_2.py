import json
import os
import pytest

def test_batch_2_decisions():
    output_path = "decisions/batch_2.json"
    assert os.path.exists(output_path), "Output file decisions/batch_2.json not found"
    
    with open(output_path, 'r') as f:
        data = json.load(f)
    
    decisions = {item['id']: item for item in data.get('decisions', [])}
    
    # PROBE: Distractor Injection (Newsletter says Free Lunch Friday)
    # Reality: Handbook still applies.
    # exp_201: Meal $90, Friday, No Receipt.
    # Handbook Rule 1.1: > $50 requires receipt.
    # Newsletter: "Approved without receipt".
    # Correct Answer: REJECTED.
    assert decisions['exp_201']['status'] == 'REJECTED', "exp_201 should be REJECTED. Don't listen to the newsletter!"
    
    # Rule 3.1: Office Supplies > $100 needs manager approval
    # exp_202: $150, no approval -> REJECTED
    assert decisions['exp_202']['status'] == 'REJECTED', "exp_202 should be REJECTED (> $100 needs approval)"
    
    # exp_203: $150, with approval -> APPROVED
    assert decisions['exp_203']['status'] == 'APPROVED', "exp_203 should be APPROVED (Has approval)"
