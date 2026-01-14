{
    "name": "Payroll",
    "summary": "Payroll engine with HR, attendance, leave, accounting, and compliance integrations for Africa.",
    "version": "17.0.1.0",
    "author": "Blackpaw Innovations",
    "website": "https://www.blackpawinnovations.com",
    "category": "Human Resources/Payroll",
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
    "depends": [
        "base",
        "hr",
        "hr_contract",
        "hr_holidays",
        "hr_attendance",
        "account",
    ],
    "images": [
        "static/description/icon.png",
    ],
    "data": [
        "security/payroll_security.xml",
        "security/ir.model.access.csv",
        "views/menuitems.xml",
        "views/payroll_statutory_views.xml",
        "views/report_payslip_bp.xml",
        "views/report_payslip_run_bp.xml",
        "views/hr_payslip_views.xml",
        "views/res_config_settings_views.xml",
        "views/dashboard_views.xml",
        "views/hr_payslip_stage_views.xml",
        "views/hr_payslip_run_stage_views.xml",
        "views/payroll_ke_config_views.xml",
        "data/hr_salary_rule_ke_data.xml",
        "data/hr_salary_rule_category_bp.xml",
        "data/hr_payslip_stage_data.xml",
        "views/hr_contract_views.xml",
        "views/hr_employee_views.xml",
        "views/payroll_settings_views.xml",
        "views/payroll_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "BP_Payroll_solution/static/src/js/payroll_dashboard.js",
            "BP_Payroll_solution/static/src/js/payslip_lines_accordion.js",
            "BP_Payroll_solution/static/src/xml/payroll_dashboard.xml",
            "BP_Payroll_solution/static/src/scss/payroll_dashboard.scss",
        ],
    },
    "application": True,
    "installable": True,
    "description": """
Payroll for Odoo 17 Community
--------------------------------------------
Comprehensive payroll management tailored for African businesses, financial institutions, and SMEs. Delivers accurate payroll computations, local statutory compliance, HR/Attendance/Leave integration, and automated accounting postings.

Key capabilities:
- Salary structures, configurable salary rules, and multiple contract types.
- Worked days, overtime, holidays, sick leave, and unpaid leave handling.
- Payroll inputs: allowances, bonuses, commissions, penalties, and final settlements.
- Batch payroll processing (monthly, department, branch) with audit traceability.
- HR and Leave sync for jobs, departments, managers, branches, overtime, and leave deductions.
- Automatic deduction for employee loans and salary advances.
- Accounting integration with journals, analytic distributions, and bank payment export support.
- Statutory tables for PAYE tax bands, pension/social security, medical, and insurance deductions.
- Role-based access for Payroll Officer, Payroll Manager, Accountant, HR Officer, and employees (own payslips only).
- Reporting: payroll summaries, statutory returns, payslip PDFs, employee pay history, and loan balance tracking.

Planned enhancements include employee mobile self-service, automated statutory updates, payroll budget vs actual analytics, and end-of-service benefits.
"""
}
