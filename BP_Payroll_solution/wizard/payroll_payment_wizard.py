from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PayrollPaymentWizard(models.TransientModel):
    _name = "bp.payroll.payment.wizard"
    _description = "Pay Payslips"

    journal_id = fields.Many2one(
        "account.journal",
        string="Payment Journal",
        required=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
    )
    payment_date = fields.Date(
        string="Payment Date", required=True, default=fields.Date.context_today
    )
    payslip_ids = fields.Many2many("hr.payslip", string="Payslips")
    run_id = fields.Many2one("hr.payslip.run", string="Batch")
    total_amount = fields.Monetary(string="Total Amount", compute="_compute_total_amount", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)

    @api.depends("payslip_ids")
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(slip.total_net for slip in wizard.payslip_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        
        if context.get("active_model") == "hr.payslip":
            res["payslip_ids"] = [(6, 0, context.get("active_ids", []))]
        elif context.get("active_model") == "hr.payslip.run":
            run_id = context.get("active_id")
            if run_id:
                res["run_id"] = run_id
                run = self.env["hr.payslip.run"].browse(run_id)
                # Filter slips that are ready to pay
                # We exclude 'cancel' (Rejected) and 'done'/'paid' (Already Paid)
                # We include 'draft', 'verify', 'approval', 'payment_ready'
                unpaid_slips = run.slip_ids.filtered(lambda s: s.state not in ("done", "paid", "cancel"))
                
                # Fallback: If no unpaid slips found, but slips exist, maybe they are all done?
                # We don't auto-select done slips.
                
                res["payslip_ids"] = [(6, 0, unpaid_slips.ids)]
        return res

    def action_confirm_payment(self):
        self.ensure_one()
        slips = self.payslip_ids.filtered(lambda s: s.state not in ["draft", "cancel", "done", "paid"])
        
        if not slips:
            raise UserError(_("No valid (unpaid) payslips selected for payment."))

        Payment = self.env["account.payment"]
        
        for slip in slips:
            if slip.total_net <= 0:
                continue

            partner = slip._bp_get_partner()

            # Create Payment
            payment_vals = {
                "payment_type": "outbound",
                "partner_type": "supplier", # Employees are suppliers in this context
                "partner_id": partner.id if partner else False,
                "amount": slip.total_net,
                "journal_id": self.journal_id.id,
                "date": self.payment_date,
                "ref": f"Salary Payment: {slip.name}",
                "company_id": slip.company_id.id,
            }
            
            # Fallback if no partner found (critical for payment)
            if not payment_vals["partner_id"]:
                 # Try to find a partner with the same name? Or raise error?
                 # Raising error is safer
                 raise UserError(_("Employee %s has no private address (Partner) defined.") % slip.employee_id.name)

            payment = Payment.create(payment_vals)
            payment.action_post()
            
            # Move slip to done state
            slip.action_set_paid()
        
        # Check if all slips in the run are now paid
        if self.run_id:
            all_paid = all(s.state in ("done", "paid", "cancel") for s in self.run_id.slip_ids)
            if all_paid:
                self.run_id._move_to_state("done")
            
        return {"type": "ir.actions.act_window_close"}
