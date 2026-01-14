from odoo import fields, models


class HrSalaryRuleCategory(models.Model):
    _name = "hr.salary.rule.category"
    _description = "Salary Rule Category"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    note = fields.Text()
