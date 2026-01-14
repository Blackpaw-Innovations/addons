from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrPayslipStage(models.Model):
    _name = "hr.payslip.stage"
    _description = "Payslip Approval Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("verify", "HR Review"),
            ("approval", "Approval"),
            ("payment_ready", "Ready for Payment"),
            ("done", "Paid"),
            ("cancel", "Rejected"),
        ],
        string="Related State",
        required=True,
        help="The technical state this stage corresponds to."
    )
    responsible_user_ids = fields.Many2many(
        "res.users",
        string="Responsible Users",
        help="Users authorized to approve/move from this stage."
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    fold = fields.Boolean(string="Folded in Kanban")

    _sql_constraints = [
        ('state_company_uniq', 'unique (state, company_id)', 'Each state can only have one configuration per company.')
    ]
