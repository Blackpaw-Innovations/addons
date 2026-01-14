# CRM Purchase

## Overview

The `crm_purchase` module seamlessly integrates Odoo's CRM and Purchase applications, enabling users to link CRM opportunities directly with purchase orders. This integration streamlines the procurement process by allowing analytic accounts (projects) set on opportunities to automatically propagate to purchase order lines, ensuring accurate analytic tracking and reporting.

## Key Features

- **Link Opportunities to Purchase Orders:**  
  Each CRM opportunity (`crm.lead`) can be linked to multiple purchase orders via a dedicated field.

- **Automatic Analytic Account Assignment:**  
  When a purchase order is created and linked to an opportunity, the analytic account (project) set on the opportunity is automatically assigned to the analytic distribution of every purchase order line.

- **Quick Access to Related Purchases:**  
  Opportunities provide a smart action to quickly open and view all related purchase orders.

## How It Works

1. **Set Analytic Account on Opportunity:**  
   On the CRM opportunity form, select the relevant analytic account (project) using the "Analytic Account" field.

2. **Create or Link Purchase Orders:**  
   When a purchase order is created from the opportunity (or manually linked), the system will automatically assign the opportunity's analytic account to all order lines.

3. **Analytic Distribution on Order Lines:**  
   Each purchase order line will have its analytic distribution set to 100% for the opportunity's analytic account, ensuring all costs are tracked against the correct project.

## Technical Details

- Adds a `purchase_order_ids` One2many field to `crm.lead` for related purchase orders.
- Adds an `analytic_account_id` field to `crm.lead`.
- Extends `purchase.order` with a `crm_lead_id` field.
- Overrides the `create` method of `purchase.order` to set the analytic distribution on order lines based on the linked opportunity.

## Installation

1. Copy the `crm_purchase` folder into your Odoo addons directory.
2. Update the app list and install the module via the Odoo Apps menu.

## Usage

- Go to CRM > Opportunities, open or create an opportunity, and set the Analytic Account.
- Create a purchase order from the opportunity or link an existing one.
- Add products to the purchase order. The analytic distribution will be set automatically.

## Compatibility

- Designed for Odoo 17 Community Edition.
- Requires the `crm` and `purchase` modules.

## Author

blackpaw innovations