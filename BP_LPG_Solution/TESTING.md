# BP LPG Solution - Test Document

## Scope
Manual test plan for LPG cylinder exchange and lifecycle tracking in Odoo 17.

## Pre-Setup
- Odoo 17 Community running with `BP_LPG_Solution` installed.
- User has Sales and Inventory access.
- Create two stock locations:
  - Internal location: `WH/Stock`
  - Customer location: `Customers` (usage: Customer)
- Ensure a Scrap location is available.

## Test Data
- Product A: LPG Gas (set `LPG Gas`, `Requires Exchange` = True)
- Product B: LPG Cylinder (set `LPG Cylinder`, capacity set; tracking should be Serial)
- Create 2 cylinder serials for Product B: `CYL-001`, `CYL-002`
- Partner: `Test Customer`

## Test Cases

### 1) Product Configuration Rules
Steps:
1. Mark a product as LPG Cylinder.
2. Save.
3. Mark another product as LPG Gas.
4. Save.

Expected:
- Cylinder product tracking is `Serial`.
- Gas product tracking is `None`.
- Product cannot be both LPG Cylinder and LPG Gas.

### 2) Cylinder Status Updates on Stock Move
Steps:
1. Deliver `CYL-001` to `Test Customer` using a picking to customer location.
2. Return `CYL-001` back to warehouse (customer -> internal).
3. Move `CYL-001` to Scrap location.

Expected:
- After delivery: status = `Filled`, current customer = `Test Customer`.
- After return: status = `Empty`, current customer cleared.
- After scrap: status = `Damaged`, current customer cleared.

### 3) First-Time Sale (Cylinder + Gas)
Steps:
1. Create a Sales Order for `Test Customer`.
2. Add 1x LPG Gas line.
3. Add 1x LPG Cylinder line.
4. Confirm the order.

Expected:
- Order confirms without exchange errors.
- Delivery is allowed.

### 4) Exchange Sale (Gas Only)
Steps:
1. Create a Sales Order for `Test Customer`.
2. Add 1x LPG Gas line (requires exchange).
3. Set returned cylinder serial to `CYL-001` on the gas line.
4. Confirm the order.
5. Validate delivery.

Expected:
- Order confirms successfully.
- Delivery validates successfully.
- Exchange tracking fields show required/returned counts correctly.

### 5) Exchange Sale - Missing Return
Steps:
1. Create a Sales Order for `Test Customer`.
2. Add 1x LPG Gas line.
3. Do not select returned cylinder serial.
4. Try to confirm.

Expected:
- Confirmation is blocked with a validation error requesting returned serial.

### 6) Returned Cylinder Quantity Rule
Steps:
1. Create a Sales Order.
2. Add LPG Gas line with quantity > 1.
3. Try to confirm.

Expected:
- Confirmation is blocked with a validation error (each line must be qty 1 to select serial).

### 7) Partner Cylinder Ledger
Steps:
1. Deliver `CYL-002` to `Test Customer`.
2. Open partner form for `Test Customer`.

Expected:
- Cylinder ledger shows `CYL-002` with status `Filled`.
- Cylinder count reflects assigned cylinders.

## Notes
- All tests must be executed in Odoo 17.0.
- Use standard Odoo delivery flow; do not bypass stock moves.
