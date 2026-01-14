from odoo import api, fields, models


class Company(models.Model):
    _inherit = "res.company"

    payroll_journal_id = fields.Many2one(
        "account.journal",
        string="Payroll Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', id)]",
        help="Default journal for payroll postings.",
    )
    payroll_structure_id = fields.Many2one(
        "hr.payroll.structure",
        string="Default Payroll Structure",
        domain="[('company_id', '=', id)]",
    )
    payroll_requires_bank_account = fields.Boolean(
        string="Require Employee Bank Account",
        default=True,
        help="Pre-validation will fail when missing bank account details.",
    )
    payroll_auto_post = fields.Boolean(
        string="Auto Post Payroll Moves",
        default=False,
        help="Automatically post journal entries after payroll confirmation.",
    )
    payroll_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Default Analytic Account",
        help="Analytic account used for payroll accounting entries.",
    )
    bp_show_payslip_smart_button = fields.Boolean(
        string="Show Payslips Smart Button",
        default=True,
        help="Show the Payslips smart button on the Employee form.",
    )
    # payroll_analytic_tag_ids = fields.Many2many(
    #     "account.analytic.tag",
    #     "bp_payroll_company_analytic_tag_rel",
    #     "company_id",
    #     "tag_id",
    #     string="Default Payroll Analytic Tags",
    #     help="Analytic tags applied on payroll accounting entries.",
    # )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    payroll_journal_id = fields.Many2one(
        related="company_id.payroll_journal_id",
        string="Payroll Journal",
        readonly=False,
    )
    payroll_structure_id = fields.Many2one(
        related="company_id.payroll_structure_id",
        string="Default Payroll Structure",
        readonly=False,
    )
    payroll_requires_bank_account = fields.Boolean(
        related="company_id.payroll_requires_bank_account",
        string="Require Employee Bank Account",
        readonly=False,
    )
    payroll_auto_post = fields.Boolean(
        related="company_id.payroll_auto_post",
        string="Auto Post Payroll Moves",
        readonly=False,
    )
    payroll_analytic_account_id = fields.Many2one(
        related="company_id.payroll_analytic_account_id",
        string="Default Analytic Account",
        readonly=False,
    )
    bp_show_payslip_smart_button = fields.Boolean(
        related="company_id.bp_show_payslip_smart_button",
        string="Show Payslips Smart Button",
        readonly=False,
    )
    # payroll_analytic_tag_ids = fields.Many2many(
    #     related="company_id.payroll_analytic_tag_ids",
    #     string="Default Payroll Analytic Tags",
    #     readonly=False,
    # )
