from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    structure_id = fields.Many2one(
        "hr.payroll.structure",
        string="Payroll Structure",
        help="Structure used by the payroll engine.",
    )
    payroll_country_code = fields.Selection(
        selection=[("KE", "Kenya")],
        string="Payroll Country",
        default=lambda self: self._default_payroll_country(),
        help="Localization hint for payroll rules.",
    )

    @api.model
    def _default_payroll_country(self):
        country = self.env.company.country_id
        return "KE" if country and country.code == "KE" else False

    @api.onchange("company_id")
    def _onchange_company_id_payroll_country(self):
        country = self.company_id.country_id
        self.payroll_country_code = "KE" if country and country.code == "KE" else False
        if self.payroll_country_code == "KE" and not self.structure_id:
            ke_structure = self.env["hr.payroll.structure"].search(
                [("code", "=", "KE_BASIC_STRUCTURE")], limit=1
            )
            if ke_structure:
                self.structure_id = ke_structure

    # Kenya-specific allowances and benefits placeholders (monthly amounts)
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    pension_contribution = fields.Monetary(string="Pension Contribution (/month)", currency_field="currency_id")
    food_allowance = fields.Monetary(string="Food Allowance (/month)", currency_field="currency_id")
    airtime_allowance = fields.Monetary(string="Airtime Allowance (/month)", currency_field="currency_id")
    pension_allowance = fields.Monetary(string="Pension Allowance (/month)", currency_field="currency_id")
    insurance_premium = fields.Monetary(string="Insurance Premium (/month)", currency_field="currency_id")
    voluntary_medical_insurance = fields.Monetary(
        string="Voluntary Medical Insurance (/month)", currency_field="currency_id"
    )
    life_insurance = fields.Monetary(string="Life Insurance (/month)", currency_field="currency_id")
    education_benefit = fields.Monetary(string="Education (/month)", currency_field="currency_id")
    helb_deduction = fields.Monetary(string="HELB (/month)", currency_field="currency_id")
    equipment_recovery = fields.Monetary(string="Asset/Equipment Recovery (/month)", currency_field="currency_id")
    other_deduction = fields.Monetary(string="Other Deductions (/month)", currency_field="currency_id")
    mortgage_interest = fields.Monetary(string="Mortgage Interest (/month)", currency_field="currency_id")
    house_allowance = fields.Monetary(string="House Allowance (/month)", currency_field="currency_id")
    other_allowance = fields.Monetary(string="Other Allowance (/month)", currency_field="currency_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("payroll_country_code"):
                company = False
                if vals.get("company_id"):
                    company = self.env["res.company"].browse(vals["company_id"])
                company = company or self.env.company
                if company.country_id and company.country_id.code == "KE":
                    vals["payroll_country_code"] = "KE"
            if vals.get("payroll_country_code") == "KE" and not vals.get("structure_id"):
                ke_structure = self.env["hr.payroll.structure"].search(
                    [("code", "=", "KE_BASIC_STRUCTURE")], limit=1
                )
                if ke_structure:
                    vals["structure_id"] = ke_structure.id
        return super().create(vals_list)
