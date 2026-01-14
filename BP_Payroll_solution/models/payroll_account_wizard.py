from odoo import api, fields, models


class PayrollJournalWizard(models.TransientModel):
    _name = "bp.payroll.journal.wizard"
    _description = "Select Journal for Payroll Posting"

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', 'in', ['bank','cash','general']), ('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company.id
    )
    payslip_ids = fields.Many2many("hr.payslip", string="Payslips")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get("company_id") and self.env.company:
            res["company_id"] = self.env.company.id
        if not res.get("payslip_ids") and self.env.context.get("active_model") == "hr.payslip":
            res["payslip_ids"] = [(6, 0, self.env.context.get("active_ids", []))]
        return res

    def action_confirm(self):
        self.ensure_one()
        slips = self.payslip_ids
        for slip in slips:
            slip._bp_create_move(custom_journal=self.journal_id)
        return {"type": "ir.actions.act_window_close"}
