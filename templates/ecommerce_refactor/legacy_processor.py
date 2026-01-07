"""
LEGACY E-COMMERCE PROCESSOR
---------------------------
Copyright (c) 2018 LegacyCorp Inc.
All rights reserved.

This module handles EVERYTHING. Do not touch unless you know what you are doing.
"""

import json
import time
import random
from datetime import datetime

class MonolithicProcessor:
    def __init__(self, db_connection_string):
        self.db = db_connection_string
        self.cache = {}
        self.errors = []
        self.admin_email = "admin@legacycorp.com"
        
    def process_order(self, order_data):
        """
        Main entry point for order processing.
        Flow:
        1. Validate
        2. Check Inventory
        3. Payment
        4. Shipping
        5. Email
        """
        print(f"Processing order: {order_data.get('id')}")
        
        # Validation Logic (Do not change)
        if not order_data.get('items'):
            self.errors.append("No items")
            return False
            
        if not order_data.get('customer'):
            self.errors.append("No customer")
            return False
            
        # Inventory Check (Legacy system integration)
        # TODO: Move this to a separate service eventually
        for item in order_data['items']:
            sku = item['sku']
            qty = item['quantity']
            
            # Simulated DB lookup
            current_stock = self._get_stock_from_db(sku)
            if current_stock < qty:
                self.errors.append(f"OOS: {sku}")
                return False
                
        # Payment Processing (Gateway A)
        total = self._calculate_total(order_data)
        if order_data.get('payment_method') == 'credit_card':
            if not self._charge_gateway_a(total, order_data['payment_token']):
                # Retry with Gateway B
                if not self._charge_gateway_b(total, order_data['payment_token']):
                    return False
        
        # Shipping Calculation
        # Complex rules from 2019
        shipping_cost = 0
        weight = sum(i.get('weight', 0) for i in order_data['items'])
        if weight > 10:
            shipping_cost = 15.00
        elif weight > 5:
            shipping_cost = 10.00
        else:
            shipping_cost = 5.00
            
        # Holiday surcharge logic (deprecated but still in code)
        if datetime.now().month == 12:
            shipping_cost += 2.00
            
        # Email Notification
        self._send_email(order_data['customer']['email'], "Order Confirmed")
        
        return True

    def _get_stock_from_db(self, sku):
        # MOCK DB CALL
        # In production this connects to Oracle 11g
        return 100

    def _calculate_total(self, order_data):
        subtotal = sum(i['price'] * i['quantity'] for i in order_data['items'])
        # Tax rules
        tax_rate = 0.08
        if order_data['customer'].get('state') == 'CA':
            tax_rate = 0.09
        elif order_data['customer'].get('state') == 'NY':
            tax_rate = 0.085
            
        return subtotal * (1 + tax_rate)

    def _charge_gateway_a(self, amount, token):
        # Legacy Gateway A implementation
        # Connects via XML-RPC
        print(f"Charging {amount} via Gateway A")
        return True

    def _charge_gateway_b(self, amount, token):
        # Backup Gateway
        print(f"Charging {amount} via Gateway B")
        return True

    def _send_email(self, recipient, subject):
        # SMTP implementation
        print(f"Sending email to {recipient}: {subject}")

    def update_inventory_batch(self, updates):
        """
        Batch update inventory.
        Format: [{'sku': 'ABC', 'qty': 10}, ...]
        """
        results = []
        for update in updates:
            # Complex locking logic should go here
            success = True
            if update['qty'] < 0:
                # Stock reduction
                current = self._get_stock_from_db(update['sku'])
                if current + update['qty'] < 0:
                    success = False
            
            if success:
                # Write to DB
                pass
            results.append(success)
        return results

    def generate_daily_report(self, date):
        """
        Generates the big daily report for accounting.
        """
        # 50 lines of report generation logic...
        report = {
            "date": date,
            "total_orders": 0,
            "total_revenue": 0.0,
            "errors": len(self.errors)
        }
        return json.dumps(report)

    # ... 50 more utility methods below ...
    
    def validate_address(self, address):
        # USPS integration
        return True
        
    def check_fraud_score(self, customer_data):
        # 3rd party fraud check
        return 0.1
        
    def archive_old_orders(self, days=365):
        # Move to cold storage
        pass
