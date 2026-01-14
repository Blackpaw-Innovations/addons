from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PayrollTaxBand(models.Model):
    _name = "bp.payroll.tax.band"
    _description = "Payroll Tax Band"
    _order = "sequence, lower_bound"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    country_id = fields.Many2one("res.country", string="Country")
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    lower_bound = fields.Monetary(required=True)
    upper_bound = fields.Monetary()
    rate = fields.Float(string="Rate (%)", digits=(16, 4), required=True)
    quick_deduction = fields.Monetary(
        string="Quick Deduction", help="Amount to deduct from the computed tax."
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.constrains("lower_bound", "upper_bound")
    def _check_bounds(self):
        for band in self:
            if band.upper_bound and band.upper_bound <= band.lower_bound:
                raise ValidationError(
                    _("The upper bound must be greater than the lower bound.")
                )


class PayrollContribution(models.Model):
    _name = "bp.payroll.contribution"
    _description = "Payroll Contribution Rule"
    _order = "date_from desc, name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    country_id = fields.Many2one("res.country", string="Country")
    contribution_type = fields.Selection(
        [
            ("pension", "Pension / Social Security"),
            ("health", "Medical"),
            ("insurance", "Insurance"),
            ("other", "Other"),
        ],
        required=True,
        default="pension",
    )
    amount_type = fields.Selection(
        [("percentage", "Percentage of base"), ("fixed", "Fixed amount")],
        required=True,
        default="percentage",
    )
    base = fields.Selection(
        [
            ("gross", "Gross"),
            ("basic", "Basic"),
            ("net", "Net"),
            ("custom_category", "Custom Salary Rule Category"),
        ],
        required=True,
        default="gross",
    )
    rule_category_id = fields.Many2one(
        "hr.salary.rule.category",
        string="Category Base",
        help="If base = Custom Salary Rule Category, the contribution is computed on that category total.",
    )
    employee_rate = fields.Float(string="Employee Rate (%)", digits=(16, 4))
    employer_rate = fields.Float(string="Employer Rate (%)", digits=(16, 4))
    employee_fixed = fields.Monetary(string="Employee Fixed")
    employer_fixed = fields.Monetary(string="Employer Fixed")
    ceiling = fields.Monetary(string="Ceiling")
    floor = fields.Monetary(string="Floor")
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    description = fields.Text()

    @api.constrains("amount_type", "employee_rate", "employer_rate")
    def _check_rates(self):
        for rule in self:
            if rule.amount_type == "percentage" and not (
                rule.employee_rate or rule.employer_rate
            ):
                raise ValidationError(
                    _("Set at least one rate when amount type is percentage.")
                )
            if rule.amount_type == "fixed" and not (
                rule.employee_fixed or rule.employer_fixed
            ):
                raise ValidationError(
                    _("Set at least one fixed amount when amount type is fixed.")
                )

    @api.constrains("base", "rule_category_id")
    def _check_category_required(self):
        for rule in self:
            if rule.base == "custom_category" and not rule.rule_category_id:
                raise ValidationError(
                    _("Select a salary rule category when base is custom category.")
                )
            if rule.base != "custom_category" and rule.rule_category_id:
                raise ValidationError(
                    _("Remove category when base is not custom category.")
                )


class PayrollBenefitPolicy(models.Model):
    _name = "bp.payroll.benefit.policy"
    _description = "Payroll Benefit / Deduction Policy"
    _order = "date_from desc, name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    country_id = fields.Many2one("res.country", string="Country")
    policy_type = fields.Selection(
        [
            ("medical", "Medical"),
            ("insurance", "Insurance"),
            ("deduction", "Deduction"),
            ("allowance", "Allowance"),
        ],
        required=True,
        default="medical",
    )
    amount_type = fields.Selection(
        [("percentage", "Percentage"), ("fixed", "Fixed amount")],
        required=True,
        default="fixed",
    )
    employee_share = fields.Float(string="Employee Share (%)", digits=(16, 4))
    employer_share = fields.Float(string="Employer Share (%)", digits=(16, 4))
    employee_fixed = fields.Monetary(string="Employee Fixed")
    employer_fixed = fields.Monetary(string="Employer Fixed")
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    note = fields.Text()

    @api.constrains("amount_type", "employee_share", "employer_share")
    def _check_policy_amounts(self):
        for policy in self:
            if policy.amount_type == "percentage" and not (
                policy.employee_share or policy.employer_share
            ):
                raise ValidationError(
                    _("Set at least one percentage share for the policy.")
                )
            if policy.amount_type == "fixed" and not (
                policy.employee_fixed or policy.employer_fixed
            ):
                raise ValidationError(_("Set at least one fixed amount for the policy."))
