from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KenyaPayrollConfig(models.Model):
    _name = "bp.payroll.ke.config"
    _description = "Kenya Payroll Configuration"
    _order = "company_id"

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        default=lambda self: self._default_country_ke(),
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    payroll_journal_id = fields.Many2one(
        "account.journal",
        string="Payroll Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
    )

    # Accounts
    account_basic_salary_id = fields.Many2one("account.account", string="Basic Salary Expense", domain="[('company_id', '=', company_id)]")
    account_net_pay_payable_id = fields.Many2one("account.account", string="Net Pay Payable", domain="[('company_id', '=', company_id)]")
    account_paye_payable_id = fields.Many2one("account.account", string="PAYE Payable", domain="[('company_id', '=', company_id)]")
    account_nssf_payable_id = fields.Many2one("account.account", string="NSSF Payable", domain="[('company_id', '=', company_id)]")
    account_shif_payable_id = fields.Many2one("account.account", string="SHIF Payable", domain="[('company_id', '=', company_id)]")
    account_housing_levy_payable_id = fields.Many2one("account.account", string="Housing Levy Payable", domain="[('company_id', '=', company_id)]")
    account_nita_payable_id = fields.Many2one("account.account", string="NITA Payable", domain="[('company_id', '=', company_id)]")
    
    account_nssf_expense_id = fields.Many2one("account.account", string="NSSF Employer Expense", domain="[('company_id', '=', company_id)]")
    account_housing_levy_expense_id = fields.Many2one("account.account", string="Housing Levy Employer Expense", domain="[('company_id', '=', company_id)]")
    account_nita_expense_id = fields.Many2one("account.account", string="NITA Employer Expense", domain="[('company_id', '=', company_id)]")

    # PAYE
    paye_band_1_limit = fields.Monetary(default=24000.0)
    paye_band_1_rate = fields.Float(default=10.0)
    paye_band_2_limit = fields.Monetary(default=32333.0)
    paye_band_2_rate = fields.Float(default=25.0)
    paye_band_3_limit = fields.Monetary(default=500000.0)
    paye_band_3_rate = fields.Float(default=30.0)
    paye_band_4_limit = fields.Monetary(default=800000.0)
    paye_band_4_rate = fields.Float(default=32.5)
    paye_band_5_rate = fields.Float(default=35.0)
    personal_relief = fields.Monetary(default=2400.0)
    paye_additional_relief = fields.Monetary(
        default=6300.0,
        help="Optional extra relief (e.g., insurance/housing relief) applied after PAYE bands. "
        "Set to 6,300 by default to mirror current insurance relief practice; adjust as rules change.",
    )
    paye_deduct_nssf = fields.Boolean(
        string="Deduct NSSF before PAYE",
        default=True,
        help="If enabled, NSSF employee contributions reduce taxable pay.",
    )
    paye_deduct_shif = fields.Boolean(
        string="Deduct SHIF before PAYE",
        default=True,
        help="If enabled, SHIF employee contributions reduce taxable pay.",
    )
    paye_deduct_housing_levy = fields.Boolean(
        string="Deduct Housing Levy before PAYE",
        default=True,
        help="If enabled, housing levy reduces taxable pay.",
    )

    # NSSF
    nssf_rate_employee = fields.Float(default=6.0)
    nssf_rate_employer = fields.Float(default=6.0)
    nssf_lower_earnings_limit = fields.Monetary(default=8000.0)
    nssf_upper_earnings_limit = fields.Monetary(default=72000.0)

    # SHIF
    shif_rate = fields.Float(default=2.75)
    shif_min_contribution = fields.Monetary(default=300.0)

    # Housing Levy
    housing_levy_rate = fields.Float(default=1.5, help="Rate (%) applied to the configured base.")
    housing_levy_base = fields.Selection(
        [
            ("gross", "Gross"),
            ("basic", "Basic"),
            ("taxable", "Taxable before PAYE"),
        ],
        default="gross",
        help="Base amount used to compute the housing levy.",
    )

    @api.constrains("company_id", "active")
    def _check_unique_active_per_company(self):
        for rec in self:
            if not rec.active:
                continue
            duplicates = self.search(
                [
                    ("id", "!=", rec.id),
                    ("company_id", "=", rec.company_id.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if duplicates:
                raise ValidationError(
                    _("Only one active Kenya payroll configuration is allowed per company.")
                )

    @api.model
    def _default_country_ke(self):
        return (
            self.env.ref("base.ke", raise_if_not_found=False)
            or self.env.company.country_id
            or False
        )

    def name_get(self):
        return [(rec.id, "%s - %s" % (rec.company_id.name, _("Kenya Config"))) for rec in self]
