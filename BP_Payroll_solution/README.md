# Payroll (Odoo 17)

Version: 17.0.1.0  
Author: Blackpaw Innovations  
Supported Edition: Odoo 17 Community

## Overview
Payroll is a comprehensive payroll management solution built for African businesses, financial institutions, and growth-focused SMEs. It delivers accurate payroll processing, local regulatory compliance, secure access control, and seamless integration with HR, Attendance, Leave, and Accounting.

## Key Features
- **Core Payroll Engine:** Salary structures, configurable salary rules (no code), multiple contract types, worked days, overtime, holidays, sick leave, unpaid leave, payroll inputs (allowances, bonuses, penalties, commissions), final settlement, and payroll batch processing by period/department/branch.
- **HR & Leave Integration:** Sync employee job/department/manager/branch, overtime from attendance/timesheet data, leave deductions per policy, automatic deductions for employee loans and salary advances.
- **Accounting Integration:** Automated payroll journal entries per batch, split net pay/statutory/employer contributions, analytic distribution by department/branch/project/cost center, bank payment exports for disbursement.
- **Statutory Compliance Ready:** Progressive PAYE income tax brackets, pension/social security rules, medical & insurance deductions, statutory return reports (CSV/Excel/PDF), full audit traceability of payslips and approvals.
- **Multi-Company / Multi-Country:** Company-specific payroll structures/parameters, localization-ready statutory configuration, flexible rule engine for international deployment.
- **Usability:** Guided payroll workflow (bulk compute → approve → confirm → post → pay), pre-validation of contracts/banks/missing data, clean payslip print format with company branding.
- **Reporting & Analytics:** Monthly payroll cost breakdown, employer contribution tracking, overtime/allowance trend analytics, employee salary history archive, Excel/CSV exports.
- **Role-Based Access & Confidentiality:** Roles for Payroll Officer, Payroll Manager, Accountant, HR Officer, and Employee (self), with controlled salary visibility and audit logs.

## Data Model Overview
- **Employee Contract (`hr.contract`):** Salary, allowances, schedule, payroll base.
- **Salary Structure (`hr.payroll.structure`):** Rule grouping for salary computation.
- **Salary Rules (`hr.salary.rule`):** Earnings, deductions, employer costs.
- **Payslip (`hr.payslip`):** Employee payroll document per period.
- **Payslip Batch (`hr.payslip.run`):** Mass payroll processing.
- **Worked Days (`hr.payslip.worked_days`):** Attendance/leave impact.
- **Payroll Inputs (`hr.payslip.input`):** Bonuses/commissions/penalties.
- **Loan Installments (`hr.loan.line`):** Salary deduction for loans.
- **Statutory Tables (custom models):** Tax bands and contribution rates.

## Payroll Processing Workflow
1. Validate attendance, worked days, and inputs.
2. Create payroll batch (draft payslips generated).
3. Compute payslips (salary rules applied).
4. Review and approve (validated payslips).
5. Confirm and post (accounting entries created).
6. Process payment (bank payroll export).
7. Distribute payslips (email / employee portal).

## Configuration Guide
- **Payroll Setup:** Payroll journal and accounts mapping; default structure per contract category; rule categories for financial mapping.
- **Statutory Setup:** Configure tax brackets with effective dates; set pension/social contribution rates; add medical/insurance deduction policies.
- **Security & Restrictions:** Assign payroll roles and record rules; restrict salary visibility by department; employee access limited to own payslips.
- **Accounting & Analytics:** Map rule categories to chart of accounts; enable analytic tags for payroll costing; prepare bank export templates if required by local banks.

## Reports Included
- Monthly Payroll Summary (Excel/PDF) for financial and HR review.
- Statutory Return Reports (CSV/Excel) for authority submission.
- Payslip Document (PDF) for employee notification.
- Employee Pay History (PDF/Pivot) for salary archive.
- Loan Balance Report (Excel/PDF) for repayment tracking.

## User Roles & Access Control
- **Payroll Officer:** Prepare and compute payroll.
- **Payroll Manager:** Approve and validate payroll.
- **Accountant:** Post payroll to accounts and manage payments.
- **HR Officer:** View contract details without salary fields.
- **Employee:** View only their own payslips.

Confidential salary information remains access-restricted at all times.

### Security & Data Visibility
- Employee self-service rule limits payslips to the logged-in employee only.
- Payroll Officer/Manager/Accountant rules restrict data to the user's companies.
- Use Odoo multi-company rules to separate branches/entities cleanly.

## Technical Specs
- **Odoo Version:** 17 Community
- **Multi-Company:** Supported
- **Multi-Country:** Supported
- **Rule Engine:** Configurable Python formulas
- **Performance:** Optimized for batch computations
- **Audit Trail:** Approval and manual adjustment log

### Architecture Note
This addon ships its own lightweight payroll engine (payslips, batches, salary rules/structures, inputs, worked days) and does not depend on Odoo Enterprise payroll modules. Extend the provided models for localization and statutory logic.

## Configuration Quick Start
1. Install the module and assign users to the Payroll Officer/Manager/Accountant groups.
2. In Company settings (`Settings → Companies → Payroll`), set the payroll journal, default structure, bank-account requirement, and analytic tags.
3. Configure statutory tables: Tax Bands, Contributions (pension/health/insurance), and Benefit/Deduction policies.
4. Create payroll batches, pre-validate (contracts, bank data, duplicates), compute, approve, confirm, post, and mark slips ready for payment.
5. Export payments using your preferred bank format (hook into `bp_payment_reference` when customizing exports).

## Developer Notes
- Models: `bp.payroll.tax.band`, `bp.payroll.contribution`, `bp.payroll.benefit.policy`.
- Extends: `hr.payslip` (payment/pre-validation helpers) and `hr.payslip.run` (department/analytic fields, totals, pre-validation, payment readiness).
- Configuration fields live on `res.company` for company-specific defaults.

## Planned Enhancements
- Employee mobile self-service (payslip viewer)
- Automated statutory table updates per region
- Payroll budget vs actual analytics dashboard
- End-of-service benefits engine

## Support
- Email: support@blackpawinnovations.com
- Web: https://www.blackpawinnovations.com
