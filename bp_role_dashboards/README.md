# BP Role Dashboards

`bp_role_dashboards` adds role-focused intelligence dashboards for Blackpaw deployments on Odoo 19. It gives Finance, HR, Sales, Operations, and Fuel teams a fast executive-style view of the metrics, tables, and signals that matter most to each function.

## Included Dashboards

- Finance Intelligence Dashboard
- HR Intelligence Dashboard
- Sales Intelligence Dashboard
- Operations Intelligence Dashboard
- Fuel Station Intelligence Dashboard

## What The Module Does

- Adds OWL client dashboards for role-specific operational intelligence.
- Surfaces KPI cards, signal narratives, and supporting tables for each role.
- Places dashboards in relevant Odoo reporting menus and in a shared `Blackpaw Intelligence` menu.
- Uses live Odoo data from Accounting, HR, CRM, Sales, and optional Blackpaw vertical modules.

## Menu Placement

- Finance: `Accounting -> Reporting -> Finance Intelligence`
- HR: `Employees -> Reporting -> HR Intelligence`
- Sales: `Sales -> Reporting -> Sales Intelligence`
- Shared launcher: `Blackpaw Intelligence`

## Core Dependencies

The module depends on:

- `account`
- `hr`
- `hr_attendance`
- `crm`
- `sale`
- `web`

## Optional Integrations

Some dashboards become richer when related Blackpaw modules are available:

- Operations dashboard can read `bp.job.card` data from `bp_jobcards_app`.
- Fuel dashboard can read `fuel.operations.dashboard` data from the Blackpaw fuel stack.
- Where those optional models are missing, the dashboards degrade gracefully and show fallback intelligence or setup guidance.

## Dashboard Coverage

### Finance

- Revenue MTD
- Expenses MTD
- Gross profit and gross profit percent
- Cash in bank
- Accounts receivable outstanding
- Overdue receivables
- AR aging
- Revenue concentration by client
- Payables watchlist
- Six-month revenue and expense trend

### HR

- Headcount
- Employees on leave
- Open positions
- Overtime percent MTD
- Monthly payroll
- Attrition YTD
- Overtime trend
- Leave liability by department
- Attrition detail
- Appraisal backlog signals

### Sales

- Pipeline value
- Win rate
- Deals closed MTD
- Average deal size
- Proposals sent
- Churn risk
- Pipeline by stage
- Win rate trend
- Loss reasons
- Rep performance
- Stale proposal follow-up risk

### Operations

- Open jobs
- Active jobs
- Overdue jobs
- Completed jobs MTD
- Revenue MTD
- Gross margin estimate
- Active job detail
- Awaiting sign-off queue
- Fallback finance view when job card data is unavailable

### Fuel

- Open sessions
- Dispensed today
- Variance percent
- Wet stock days
- Float status
- QMS score
- Operational risk signals when fuel data is available
- Setup guidance when the fuel stack is not installed

## Installation

1. Add `bp_role_dashboards` to your Odoo addons path.
2. Update the apps list.
3. Install `Blackpaw Role Dashboards`.
4. Ensure users have normal internal user access to reach the dashboard menus.

## Technical Notes

- Backend assets are loaded from `static/src/js`, `static/src/xml`, and `static/src/scss`.
- Dashboard actions are defined in `views/bp_role_dashboards_actions.xml`.
- Data providers are implemented as transient models in `models/`.
- The module is intended as a role-facing intelligence layer, not a replacement for standard Odoo reports.

## Support

- Website: `https://www.blackpawinnovations.com`
- Support: `support@blackpawinnovations.com`
- Maintainer: Blackpaw Innovations
