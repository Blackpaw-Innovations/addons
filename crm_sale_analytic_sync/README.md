# CRM Sale Analytic Sync

## Overview

The `crm_sale_analytic_sync` module enhances the integration between Odoo's CRM and Sales/Analytic Accounting applications. It ensures that analytic accounts (projects) set on CRM opportunities are automatically synchronized and used in related sales and analytic processes, improving project-based reporting and financial tracking.

## Key Features

- **Analytic Account on Opportunities:**  
  Adds an analytic account (project) field to CRM opportunities (`crm.lead`), allowing users to assign a project at the opportunity stage.

- **Automatic Analytic Account Propagation:**  
  When sales or analytic records are created from an opportunity, the analytic account set on the opportunity is automatically used, ensuring consistency across related documents.

- **Seamless User Experience:**  
  The analytic account field is managed transparently, reducing manual data entry and minimizing errors in analytic/project assignment.

## How It Works

1. **Assign Analytic Account:**  
   On the CRM opportunity form, select the relevant analytic account (project) using the provided field.

2. **Create Sales/Analytic Records:**  
   When creating sales orders or analytic entries from the opportunity, the analytic account is automatically propagated to the new records.

3. **Consistent Analytic Tracking:**  
   All related sales and analytic documents will reference the same analytic account, ensuring accurate project-based reporting.

## Technical Details

- Adds an `analytic_account_id` field to `crm.lead`.
- Inherits and extends views to display and manage the analytic account field.
- Ensures analytic account propagation in downstream sales and analytic records.

## Installation

1. Copy the `crm_sale_analytic_sync` folder into your Odoo addons directory.
2. Update the app list and install the module via the Odoo Apps menu.

## Usage

- Go to CRM > Opportunities, open or create an opportunity, and set the Analytic Account.
- Create sales or analytic records from the opportunity. The analytic account will be set automatically.

## Compatibility

- Designed for Odoo 17 Community Edition.
- Requires the `crm` and `analytic` modules (and optionally `sale` if used with sales orders).

## Author

blackpaw innovations  
https://blackpawinnovations.com