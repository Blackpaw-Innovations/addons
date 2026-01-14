from odoo import fields, models


class HrPayslipRunStage(models.Model):
    _name = "hr.payslip.run.stage"
    _description = "Payslip Batch Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("verify", "In Progress"),
            ("finance_approve", "Finance Approval"),
            ("director_approve", "Director Approval"),
            ("payment_ready", "Payment Ready"),
            ("paid", "Paid"),
            ("done", "Done"),
        ],
        string="Related State",
        required=True,
        help="Technical state this stage is linked to for batch processing.",
    )
    responsible_user_ids = fields.Many2many(
        "res.users",
        string="Responsible Users",
        help="Users authorized to approve/move batches from this stage.",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    fold = fields.Boolean(string="Folded in Kanban")

    _sql_constraints = [
        (
            "state_company_batch_uniq",
            "unique (state, company_id)",
            "Each batch state can only have one configuration per company.",
        )
    ]
