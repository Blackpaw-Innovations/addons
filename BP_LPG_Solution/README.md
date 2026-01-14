# BP LPG Solution

## Purpose
BP LPG Solution adds LPG cylinder exchange and lifecycle tracking to Odoo 17 Community. Gas is treated as a consumable product, while cylinders remain tracked assets that must be accounted for across customers and warehouse locations.

## Supported Workflows
- First-time cylinder sale with gas refill (no return required)
- Cylinder exchange: deliver filled cylinder when an empty cylinder is returned
- Cylinder status tracking across warehouse, customer, and scrap locations
- Customer cylinder ledger showing currently assigned cylinders

## Cylinder Lifecycle
- Filled: cylinder delivered to a customer location
- Empty: cylinder returned to the warehouse
- Damaged: cylinder moved to a scrap location
- Maintenance: manual status for service or inspection

## Installation
1. Copy `BP_LPG_Solution` into your Odoo 17 addons path.
2. Update the Apps list.
3. Install the module.

## Odoo Compatibility
- Targeted and tested for Odoo 17.0 only.
- Uses Odoo 17 ORM, views, and inheritance best practices.
