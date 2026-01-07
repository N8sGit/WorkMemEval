# E-Commerce System Documentation
Version: 4.2.1 (Last Updated: 2022)

## Architecture Overview
The system relies on a central `MonolithicProcessor` class located in `legacy_processor.py`. This class is responsible for the entire order lifecycle.

## Core Workflows

### 1. Order Processing
The `process_order` method is the heart of the system.
- **Input**: Dictionary containing items, customer info, and payment details.
- **Validation**: Strict checks on customer existence.
- **Inventory**: Direct calls to the Oracle DB (mocked in dev).
- **Payment**: Primary is Gateway A (XML-RPC). Failover is Gateway B (REST).
- **Shipping**: Weight-based logic. Note: Holiday surcharge logic is technically deprecated but still active in code during December.

### 2. Inventory Management
Inventory is handled via `update_inventory_batch`.
- Critical: Negative quantity updates must be validated against current stock.
- Concurrency: The current implementation lacks proper row locking (Known Issue #492).

### 3. Reporting
Daily reports are generated via `generate_daily_report`. These are consumed by the Accounting subsystem via FTP.

## Refactoring Roadmap (The Task)
We want to break this monolith apart.
1.  **Extract Inventory**: Create a dedicated `InventoryManager` class.
2.  **Extract Payment**: Create a dedicated `PaymentProcessor` class with a Strategy pattern for the gateways.
3.  **Modernize Order**: Update `process_order` to use these new classes instead of the inline logic.

## Known Constraints
- You MUST preserve the tax rate logic (CA=9%, NY=8.5%, Default=8%).
- You MUST preserve the shipping weight tiers (0-5, 5-10, >10).
- Do not remove the logging statements; Ops uses them for Splunk.
