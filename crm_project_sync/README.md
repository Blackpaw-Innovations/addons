# CRM Project Sync

## Overview

The `crm_project_sync` module provides seamless integration between Odoo's CRM and Project/Analytic Accounting applications. It ensures that analytic accounts (projects) set on CRM opportunities are automatically synchronized and used in related project and analytic workflows, enabling accurate project-based tracking and reporting from the opportunity stage.

## Key Features

- **Analytic Account on Opportunities:**  
  Adds an analytic account (project) field to CRM opportunities (`crm.lead`), allowing users to assign a project at the opportunity stage.

- **Automatic Project/Analytic Account Propagation:**  
  When project tasks, analytic entries, or related records are created from an opportunity, the analytic account set on the opportunity is automatically used, ensuring consistency across all project-related documents.

- **Improved Project Reporting:**  
  All project and analytic records linked to an opportunity will reference the same analytic account, supporting unified project-based financial and operational reporting.

## How It Works

1. **Assign Analytic Account:**  
   On the CRM opportunity form, select the relevant analytic account (project) using the provided field.

2. **Create Project/Analytic Records:**  
   When creating project tasks, analytic lines, or related records from the opportunity, the analytic account is automatically propagated to the new records.

3. **Consistent Project Tracking:**  
   All related project and analytic documents will reference the same analytic account, ensuring accurate project-based tracking and reporting.

## Technical Details

- Adds an `analytic_account_id` field to `crm.lead`.
- Inherits and extends views to display and manage the analytic account field.
- Ensures analytic account propagation in downstream project and analytic records.

## Installation

1. Copy the `crm_project_sync` folder into your Odoo addons directory.
2. Update the app list and install the module via the Odoo Apps menu.

## Usage

- Go to CRM > Opportunities, open or create an opportunity, and set the Analytic Account.
- Create project tasks or analytic records from the opportunity. The analytic account will be set automatically.

## Compatibility

- Designed for Odoo 17 Community Edition.
- Requires the `crm`, `project